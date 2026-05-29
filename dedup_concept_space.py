"""Deduplicate concept space using connected-components clustering and rebuild FAISS index.

Uses transitive semantic similarity: if concept A ≈ B and B ≈ C, then A, B, C
are all merged into one group. Selects the best representative for each group.
"""

import json
import logging
import os
import sys
import numpy as np
from scipy.sparse.csgraph import connected_components
from scipy.sparse import csr_matrix

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("dedup_concepts")


def load_concepts_and_embeddings(model_path, library_path, anchor_data_path):
    """Load concepts and their v3 model embeddings."""
    from sentence_transformers import SentenceTransformer

    concepts = []
    concept_sources = []
    concept_descriptions = []

    # Library concepts
    with open(library_path, "r", encoding="utf-8") as fh:
        lib = json.load(fh)
    enc = lib.get("encoding_library", lib)
    for third in enc.get("third_level_codes", []):
        for second in third.get("second_level_codes", []):
            name = second.get("name", "").strip()
            desc = second.get("description", "").strip()
            if name and name not in concepts:
                concepts.append(name)
                concept_sources.append("library")
                concept_descriptions.append(desc)

    # v11 anchor concepts
    with open(anchor_data_path, "r", encoding="utf-8") as fh:
        anchor_data = json.load(fh)
    for item in anchor_data.get("pairs", []):
        ac = item.get("anchor_code", "").strip()
        if ac and ac not in concepts:
            concepts.append(ac)
            concept_sources.append("v11_anchor")
            concept_descriptions.append("")

    # Filter entity-specific
    _entity_keywords = [
        "苹果", "谷歌", "华为", "小米", "腾讯", "阿里", "百度", "京东",
        "淘宝", "天猫", "美团", "滴滴", "字节", "抖音", "快手", "微信",
        "微博", "苏宁", "顺丰", "比亚迪", "特斯拉", "蔚来", "理想",
        "拼多多", "网易", "携程", "去哪儿", "链家", "贝壳",
    ]
    filtered_concepts = []
    filtered_sources = []
    filtered_descs = []
    for c, s, d in zip(concepts, concept_sources, concept_descriptions):
        if any(kw in c for kw in _entity_keywords):
            continue
        filtered_concepts.append(c)
        filtered_sources.append(s)
        filtered_descs.append(d)

    logger.info("Concepts loaded: %d (after entity filter)", len(filtered_concepts))

    model = SentenceTransformer(model_path, device="cuda")
    embeddings = model.encode(
        filtered_concepts, normalize_embeddings=True,
        show_progress_bar=True, batch_size=64,
    ).astype(np.float32)

    return filtered_concepts, filtered_sources, filtered_descs, embeddings, model


def compute_merge_groups(concepts, embeddings, threshold=0.74):
    """Compute connected components at given similarity threshold."""
    sim_matrix = np.dot(embeddings, embeddings.T)
    adj = (sim_matrix >= threshold).astype(np.int32)
    np.fill_diagonal(adj, 0)

    n_components, labels = connected_components(
        csgraph=csr_matrix(adj), directed=False, return_labels=True)

    groups = {}
    for i, label in enumerate(labels):
        groups.setdefault(int(label), []).append(i)

    return groups, sim_matrix


def select_representative(members, concepts, sources, descs, sim_matrix,
                          v11_preferred_names):
    """Select the best representative for a merged group.

    Criteria (in order):
    1. Appears in v11 training data as anchor_code
    2. Shorter name (2-8 chars preferred per GOAL)
    3. From coding library (has descriptions and context)
    4. Has highest average similarity to other group members
    """
    if len(members) == 1:
        return members[0], concepts[members[0]]

    def score(idx):
        name = concepts[idx]
        s = 0.0

        # v11 preference
        if name in v11_preferred_names:
            s += 100.0

        # Length preference (2-8 chars ideal)
        L = len(name)
        if 2 <= L <= 8:
            s += 50.0
        elif 9 <= L <= 12:
            s += 30.0
        elif 13 <= L <= 16:
            s += 10.0

        # Library source preference
        if sources[idx] == "library":
            s += 20.0

        # Has description
        if descs[idx]:
            s += 10.0

        # Average similarity to other members
        if len(members) > 1:
            other_sims = [sim_matrix[idx, j] for j in members if j != idx]
            s += np.mean(other_sims) * 30.0

        return s

    best_idx = max(members, key=score)
    return best_idx, concepts[best_idx]


def main():
    import argparse
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
    parser.add_argument("--v11-data", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "data", "train_anchor_pairs_v3.json"))
    parser.add_argument("--output-dir", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "cache", "anchor_index"))
    parser.add_argument("--threshold", type=float, default=0.74)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Load v11 preferred names
    v11_preferred = set()
    if os.path.exists(args.v11_data):
        with open(args.v11_data, "r", encoding="utf-8") as fh:
            v11 = json.load(fh)
        for p in v11.get("pairs", []):
            v11_preferred.add(p.get("anchor_code", "").strip())
    logger.info("v11 preferred names: %d", len(v11_preferred))

    # Load concepts and embeddings
    concepts, sources, descs, embeddings, model = load_concepts_and_embeddings(
        args.model_path, args.library_path, args.anchor_data)

    # Compute merge groups
    groups, sim_matrix = compute_merge_groups(concepts, embeddings, args.threshold)

    # Select representatives and build mapping
    n_original = len(concepts)
    merged_concepts = []
    merged_sources = []
    old_to_new = {}  # old index -> new index

    for gid in sorted(groups.keys()):
        members = groups[gid]
        best_idx, rep_name = select_representative(
            members, concepts, sources, descs, sim_matrix, v11_preferred)
        merged_concepts.append(rep_name)
        merged_sources.append(sources[best_idx])
        for mi in members:
            old_to_new[mi] = len(merged_concepts) - 1

    n_merged = len(merged_concepts)
    reduction = n_original - n_merged

    # Log merge details
    multi_member_groups = [(gid, members) for gid, members in groups.items()
                           if len(members) > 1]
    logger.info("Merged: %d → %d concepts (-%d, -%.1f%%)",
                n_original, n_merged, reduction, reduction/n_original*100)
    logger.info("Multi-member groups: %d (total merged concepts: %d)",
                len(multi_member_groups),
                sum(len(m) for _, m in multi_member_groups))

    if args.dry_run:
        print("\n=== Dry run — not writing files ===")
        print(f"Original: {n_original} concepts")
        print(f"Merged:   {n_merged} concepts")
        print(f"Reduction: {reduction} ({reduction/n_original*100:.1f}%)")
        print(f"\nMulti-member groups: {len(multi_member_groups)}")
        for gid, members in sorted(multi_member_groups, key=lambda x: -len(x[1]))[:10]:
            rep_idx = old_to_new[members[0]]
            rep_name = merged_concepts[rep_idx]
            member_names = [concepts[i] for i in members]
            print(f"  {rep_name} ← {member_names}")
        return 0

    # ---- Rebuild FAISS index ----
    logger.info("Encoding %d merged concepts ...", n_merged)
    merged_embeddings = model.encode(
        merged_concepts, normalize_embeddings=True,
        show_progress_bar=True, batch_size=64,
    ).astype(np.float32)

    import faiss
    dim = merged_embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(merged_embeddings)

    # ---- Save ----
    os.makedirs(args.output_dir, exist_ok=True)

    # Backup old concepts
    old_concepts_path = os.path.join(args.output_dir, "concepts.json")
    if os.path.exists(old_concepts_path):
        backup_path = os.path.join(args.output_dir, "concepts.json.bak")
        os.replace(old_concepts_path, backup_path)
        logger.info("Backed up old concepts to %s", backup_path)

    faiss.write_index(index, os.path.join(args.output_dir, "anchor_index.faiss"))
    with open(old_concepts_path, "w", encoding="utf-8") as fh:
        json.dump({
            "concepts": merged_concepts,
            "sources": merged_sources,
            "n_original": n_original,
            "n_merged": n_merged,
            "merge_threshold": args.threshold,
        }, fh, ensure_ascii=False, indent=2)

    # Save merge mapping for debugging
    with open(os.path.join(args.output_dir, "merge_map.json"), "w", encoding="utf-8") as fh:
        merge_info = []
        for gid, members in sorted(groups.items(), key=lambda x: -len(x[1])):
            if len(members) > 1:
                rep_name = merged_concepts[old_to_new[members[0]]]
                merge_info.append({
                    "representative": rep_name,
                    "members": [concepts[i] for i in members],
                })
        json.dump(merge_info, fh, ensure_ascii=False, indent=2)

    logger.info("Saved merged FAISS index: %d vectors → %s",
                index.ntotal, args.output_dir)
    logger.info("Merge map saved: %d groups", len(merge_info))

    return 0


if __name__ == "__main__":
    sys.exit(main())
