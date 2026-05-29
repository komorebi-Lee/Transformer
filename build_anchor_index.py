"""Build FAISS concept anchor index from coding library + fine-tuned anchor model.

After fine-tuning bge-small-zh-v1.5 with contrastive learning, this script:
1. Loads the fine-tuned model
2. Encodes all 987 second-level codes + 258 v11 anchor codes as the concept space
3. Builds a FAISS flat IP index for fast cosine retrieval
4. Provides a lookup: raw sentence -> top-k concept anchors with scores

Usage:
    D:/anaconda3/envs/zthree5/python.exe build_anchor_index.py
    D:/anaconda3/envs/zthree5/python.exe build_anchor_index.py --test
"""

import argparse
import json
import logging
import os
import sys
from typing import List, Tuple, Optional

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("anchor_index")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class ConceptAnchorIndex:
    """FAISS-based concept anchor retrieval index."""

    def __init__(self, model_path: str, library_path: str, anchor_data_path: str,
                 governed_concepts_path: str = None):
        import faiss
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_path, device="cuda")
        self._faiss = faiss

        concepts: List[str] = []
        concept_sources: List[str] = []

        # Check for governed (Phase 2) concepts first — single source of truth
        _governed_path = governed_concepts_path
        if _governed_path and os.path.exists(_governed_path):
            with open(_governed_path, "r", encoding="utf-8") as fh:
                gov_data = json.load(fh)
            concepts = gov_data.get("concepts", [])
            concept_sources = gov_data.get("sources", ["library"] * len(concepts))
            logger.info("Loaded governed concepts: %d (Phase 2 canonical anchors)", len(concepts))
        else:
            # ---- Build concept vocabulary from source files ----
            # 1. Coding library second-level names
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

            # 2. v11 anchor codes
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

            # ---- Filter out entity-specific concepts ----
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
            logger.info("Total concepts in index: %d", len(concepts))

        self.concepts = concepts
        self.concept_sources = concept_sources

        # ---- Build embeddings ----
        logger.info("Encoding %d concepts ...", len(concepts))
        embeddings = self.model.encode(
            concepts,
            normalize_embeddings=True,
            show_progress_bar=True,
            batch_size=64,
        ).astype(np.float32)

        # ---- Build FAISS index ----
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)  # inner product = cosine for normalized vectors
        self.index.add(embeddings)
        logger.info("FAISS index: %d vectors, dim=%d", self.index.ntotal, dim)

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float, str]]:
        """Return [(concept_name, similarity_score, source), ...] for a query sentence."""
        q_emb = self.model.encode(
            [query], normalize_embeddings=True, show_progress_bar=False,
        ).astype(np.float32)
        scores, indices = self.index.search(q_emb, top_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.concepts):
                continue
            results.append((self.concepts[idx], float(score), self.concept_sources[idx]))
        return results

    def search_batch(self, queries: List[str], top_k: int = 10) -> List[List[Tuple[str, float, str]]]:
        """Batch search for multiple queries."""
        q_embs = self.model.encode(
            queries, normalize_embeddings=True, show_progress_bar=True, batch_size=32,
        ).astype(np.float32)
        scores_batch, indices_batch = self.index.search(q_embs, top_k)
        all_results = []
        for scores, indices in zip(scores_batch, indices_batch):
            results = []
            for score, idx in zip(scores, indices):
                if idx < 0 or idx >= len(self.concepts):
                    continue
                results.append((self.concepts[idx], float(score), self.concept_sources[idx]))
            all_results.append(results)
        return all_results

    def encode_batch(self, queries: List[str], batch_size: int = 32,
                     show_progress_bar: bool = True) -> "np.ndarray":
        """Batch-encode queries and return normalized embeddings.

        Callers that need to search multiple FAISS indices with the same
        embeddings can use this + search_embeddings() to avoid re-encoding.
        """
        return self.model.encode(
            queries, normalize_embeddings=True,
            show_progress_bar=show_progress_bar, batch_size=batch_size,
        ).astype(np.float32)

    def search_embeddings(self, embeddings: "np.ndarray", top_k: int = 10
                          ) -> List[List[Tuple[str, float, str]]]:
        """Search the FAISS index with pre-computed embeddings.

        Args:
            embeddings: (N, dim) float32 array of normalized query vectors.
            top_k: Number of results per query.

        Returns:
            List of N result-lists, each containing (concept_name, score, source).
        """
        scores_batch, indices_batch = self.index.search(embeddings, top_k)
        all_results = []
        for scores, indices in zip(scores_batch, indices_batch):
            results = []
            for score, idx in zip(scores, indices):
                if idx < 0 or idx >= len(self.concepts):
                    continue
                results.append((self.concepts[idx], float(score), self.concept_sources[idx]))
            all_results.append(results)
        return all_results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "trained_models", "concept_anchor"))
    parser.add_argument("--library-path", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "coding_library.json"))
    parser.add_argument("--anchor-data", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "data", "clean_anchor_pairs.json"))
    parser.add_argument("--output-dir", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "cache", "anchor_index"))
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    # ---- Build index ----
    logger.info("Building concept anchor index ...")
    anchor_idx = ConceptAnchorIndex(
        model_path=args.model_path,
        library_path=args.library_path,
        anchor_data_path=args.anchor_data,
    )

    # ---- Save ----
    os.makedirs(args.output_dir, exist_ok=True)
    import faiss
    faiss.write_index(anchor_idx.index, os.path.join(args.output_dir, "anchor_index.faiss"))
    with open(os.path.join(args.output_dir, "concepts.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "concepts": anchor_idx.concepts,
            "sources": anchor_idx.concept_sources,
        }, fh, ensure_ascii=False, indent=2)
    logger.info("Index saved to %s", args.output_dir)

    # ---- Test ----
    if args.test:
        logger.info("\n" + "=" * 60)
        logger.info("Concept Anchor Lookup Test")
        logger.info("=" * 60)

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
            results = anchor_idx.search(query, top_k=5)
            print(f"\nQuery: {query}")
            for i, (concept, score, source) in enumerate(results):
                bar = "█" * int(score * 20)
                print(f"  {i+1}. [{source:8s}] {concept:<12s} {score:.3f} {bar}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
