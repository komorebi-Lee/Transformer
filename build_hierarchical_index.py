"""Build a two-stage hierarchical FAISS index for concept anchor retrieval.

Uses similarity-threshold clustering: concepts with cosine >= threshold are
merged into the same semantic group. This creates semantically coherent clusters
without forcing a predetermined number.
"""

import argparse
import json
import logging
import os
import sys
from typing import List, Tuple, Optional

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hierarchical_index")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def greedy_similarity_cluster(embeddings: np.ndarray, threshold: float = 0.85):
    """Greedy clustering: assign each vector to the nearest cluster centroid
    if similarity >= threshold, otherwise create a new cluster.

    Returns: list of cluster_id for each vector, list of centroid vectors
    """
    n = len(embeddings)
    labels = np.full(n, -1, dtype=int)
    centroids = []

    for i in range(n):
        emb = embeddings[i]
        best_sim = -1.0
        best_cluster = -1

        for cid, centroid in enumerate(centroids):
            sim = float(np.dot(emb, centroid))
            if sim > best_sim:
                best_sim = sim
                best_cluster = cid

        if best_sim >= threshold:
            labels[i] = best_cluster
            # Update centroid as moving average
            old = centroids[best_cluster]
            n_members = np.sum(labels == best_cluster)
            centroids[best_cluster] = (old * n_members + emb) / (n_members + 1)
            centroids[best_cluster] /= (np.linalg.norm(centroids[best_cluster]) + 1e-8)
        else:
            labels[i] = len(centroids)
            centroids.append(emb.copy())

    return labels, np.array(centroids)


class HierarchicalAnchorIndex:
    """Two-stage FAISS concept anchor retrieval index."""

    def __init__(self, model_path: str, library_path: str, anchor_data_path: str,
                 sim_threshold: float = 0.82):
        import faiss
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_path, device="cuda")
        self._faiss = faiss

        # ---- Build concept vocabulary ----
        concepts: List[str] = []
        concept_sources: List[str] = []

        with open(library_path, "r", encoding="utf-8") as fh:
            lib = json.load(fh)
        enc = lib.get("encoding_library", lib)
        for third in enc.get("third_level_codes", []):
            for second in third.get("second_level_codes", []):
                name = second.get("name", "").strip()
                if name and name not in concepts:
                    concepts.append(name)
                    concept_sources.append("library")
        logger.info("Library concepts: %d", len(concepts))

        with open(anchor_data_path, "r", encoding="utf-8") as fh:
            anchor_data = json.load(fh)
        v11_concepts = set()
        for item in anchor_data.get("pairs", []):
            ac = item.get("anchor_code", "").strip()
            if ac and ac not in concepts:
                v11_concepts.add(ac)
        concepts.extend(sorted(v11_concepts))
        concept_sources.extend(["v11_anchor"] * len(v11_concepts))
        logger.info("v11 anchor concepts: %d", len(v11_concepts))

        _entity_keywords = [
            "苹果", "谷歌", "华为", "小米", "腾讯", "阿里", "百度", "京东",
            "淘宝", "天猫", "美团", "滴滴", "字节", "抖音", "快手", "微信",
            "微博", "苏宁", "顺丰", "比亚迪", "特斯拉", "蔚来", "理想",
            "拼多多", "网易", "携程", "去哪儿", "链家", "贝壳",
        ]
        _filtered = 0
        _kept_concepts = []
        _kept_sources = []
        for c, s in zip(concepts, concept_sources):
            if any(kw in c for kw in _entity_keywords):
                _filtered += 1
                continue
            _kept_concepts.append(c)
            _kept_sources.append(s)
        if _filtered:
            logger.info("Filtered %d entity-specific concepts", _filtered)
        concepts = _kept_concepts
        concept_sources = _kept_sources
        logger.info("Total concepts: %d", len(concepts))

        self.concepts = concepts
        self.concept_sources = concept_sources

        # ---- Build embeddings ----
        logger.info("Encoding %d concepts ...", len(concepts))
        embeddings = self.model.encode(
            concepts, normalize_embeddings=True, show_progress_bar=True, batch_size=64,
        ).astype(np.float32)

        # ---- Similarity-threshold clustering ----
        logger.info("Clustering with sim_threshold=%.2f ...", sim_threshold)
        labels, centroids = greedy_similarity_cluster(embeddings, sim_threshold)
        n_clusters = len(centroids)
        logger.info("Clusters: %d", n_clusters)

        # ---- Organize concepts into clusters ----
        cluster_to_concepts = {}
        for i, label in enumerate(labels):
            cluster_to_concepts.setdefault(int(label), []).append(i)

        self.cluster_ids = sorted(cluster_to_concepts.keys())
        self.cluster_members = {}
        self.cluster_centroids = {}
        cluster_sizes = []

        for cid in self.cluster_ids:
            member_indices = cluster_to_concepts[cid]
            self.cluster_members[cid] = member_indices
            self.cluster_centroids[cid] = centroids[cid].astype(np.float32)
            cluster_sizes.append(len(member_indices))

        logger.info("Cluster sizes: min=%d max=%d mean=%.1f median=%d",
                    min(cluster_sizes), max(cluster_sizes),
                    np.mean(cluster_sizes), int(np.median(cluster_sizes)))

        # Show top clusters
        sorted_sizes = sorted(cluster_sizes, reverse=True)
        logger.info("Top-10 clusters: %s", sorted_sizes[:10])

        # ---- Build coarse index ----
        centroids_matrix = np.stack(centroids).astype(np.float32)
        dim = centroids_matrix.shape[1]
        self.coarse_index = faiss.IndexFlatIP(dim)
        self.coarse_index.add(centroids_matrix)
        logger.info("Coarse index: %d vectors, dim=%d", self.coarse_index.ntotal, dim)

        # ---- Build fine indices ----
        self.fine_indices = {}
        for cid in self.cluster_ids:
            member_embs = embeddings[self.cluster_members[cid]]
            fine_idx = faiss.IndexFlatIP(dim)
            fine_idx.add(member_embs)
            self.fine_indices[cid] = fine_idx

        # ---- Full flat index for fallback ----
        self.full_index = faiss.IndexFlatIP(dim)
        self.full_index.add(embeddings)
        logger.info("Built %d fine indices + 1 full fallback", len(self.fine_indices))

        self._embeddings = embeddings
        self._n_clusters = n_clusters

    def search(self, query: str, top_k: int = 10,
               n_coarse: int = 3) -> List[Tuple[str, float, str]]:
        """Hierarchical search: coarse → fine."""
        q_emb = self.model.encode(
            [query], normalize_embeddings=True, show_progress_bar=False,
        ).astype(np.float32)

        coarse_scores, coarse_indices = self.coarse_index.search(q_emb, n_coarse)

        all_results = []
        seen_concepts = set()

        for c_score, c_idx in zip(coarse_scores[0], coarse_indices[0]):
            if c_idx < 0 or c_idx >= len(self.cluster_ids):
                continue
            cluster_id = self.cluster_ids[c_idx]
            fine_idx = self.fine_indices[cluster_id]
            member_indices = self.cluster_members[cluster_id]

            n_search = min(top_k * 2, len(member_indices))
            fine_scores, fine_positions = fine_idx.search(q_emb, n_search)

            for score, pos in zip(fine_scores[0], fine_positions[0]):
                if pos < 0 or pos >= len(member_indices):
                    continue
                concept_idx = member_indices[pos]
                concept = self.concepts[concept_idx]
                if concept not in seen_concepts:
                    seen_concepts.add(concept)
                    # Blend cluster relevance with member similarity
                    blended = float(score) * 0.7 + float(c_score) * 0.3
                    all_results.append((concept, blended,
                                       self.concept_sources[concept_idx]))

        all_results.sort(key=lambda x: x[1], reverse=True)
        return all_results[:top_k]

    def search_flat(self, query: str, top_k: int = 10) -> List[Tuple[str, float, str]]:
        """Flat FAISS search (baseline)."""
        q_emb = self.model.encode(
            [query], normalize_embeddings=True, show_progress_bar=False,
        ).astype(np.float32)
        scores, indices = self.full_index.search(q_emb, top_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.concepts):
                continue
            results.append((self.concepts[idx], float(score), self.concept_sources[idx]))
        return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "trained_models", "concept_anchor_v3"))
    parser.add_argument("--library-path", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "coding_library.json"))
    parser.add_argument("--anchor-data", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "data", "clean_anchor_pairs.json"))
    parser.add_argument("--output-dir", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "cache", "anchor_index_hierarchical"))
    parser.add_argument("--sim-threshold", type=float, default=0.82)
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    logger.info("Building hierarchical concept anchor index ...")
    idx = HierarchicalAnchorIndex(
        model_path=args.model_path,
        library_path=args.library_path,
        anchor_data_path=args.anchor_data,
        sim_threshold=args.sim_threshold,
    )

    # ---- Save ----
    os.makedirs(args.output_dir, exist_ok=True)
    import faiss

    faiss.write_index(idx.coarse_index,
                      os.path.join(args.output_dir, "coarse_index.faiss"))

    fine_dir = os.path.join(args.output_dir, "fine_indices")
    os.makedirs(fine_dir, exist_ok=True)
    for cid, fine_idx in idx.fine_indices.items():
        faiss.write_index(fine_idx,
                          os.path.join(fine_dir, f"cluster_{cid}.faiss"))

    serializable_members = {str(k): v for k, v in idx.cluster_members.items()}

    with open(os.path.join(args.output_dir, "index_meta.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "concepts": idx.concepts,
            "sources": idx.concept_sources,
            "cluster_ids": idx.cluster_ids,
            "cluster_members": serializable_members,
            "n_clusters": idx._n_clusters,
        }, fh, ensure_ascii=False, indent=2)

    np.save(os.path.join(args.output_dir, "centroids.npy"),
            np.stack([idx.cluster_centroids[cid] for cid in idx.cluster_ids]))

    logger.info("Index saved to %s", args.output_dir)

    # ---- Test ----
    if args.test:
        print("\n" + "=" * 60)
        print("Hierarchical vs Flat Search Comparison")
        print("=" * 60)

        test_queries = [
            "刷视频看到别人都很厉害，我越来越不想打开书",
            "资源不够，审批流程太复杂，一个项目要好几个月",
            "培训不到位，员工能力参差不齐",
            "管理制度不完善，缺乏监督机制",
            "大家都在摸鱼，没什么干劲",
            "老师傅退休了，年轻人不愿意学这个手艺",
            "产品卖不出去，市场上同类太多",
            "老板说了算，没什么规章制度",
        ]
        for query in test_queries:
            hier_results = idx.search(query, top_k=5)
            flat_results = idx.search_flat(query, top_k=5)
            print(f"\nQ: {query}")
            for label, results in [("Hierarchical", hier_results), ("Flat", flat_results)]:
                print(f"  --- {label} ---")
                for i, (c, s, src) in enumerate(results):
                    print(f"  {i+1}. [{src:8s}] {c:<16s} {s:.3f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
