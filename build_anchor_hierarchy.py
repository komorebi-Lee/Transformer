"""Build Anchor -> 二阶 -> 三阶 hierarchical mapping for Semantic Compression.

Uses v11 training data's target_abstract -> target_second_category -> target_third_category
as the authoritative bridge. For each governed canonical anchor, finds the most semantically
similar v11 target_abstract and inherits its second/third category mapping.

Output: data/anchor_hierarchy.json
"""

import json
import logging
import os
import sys
import numpy as np
from collections import Counter, defaultdict
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("anchor_hierarchy")


def load_governed_concepts(concepts_path, alias_map_path):
    """Load governed canonical anchors and alias map."""
    with open(concepts_path, "r", encoding="utf-8") as fh:
        concepts_data = json.load(fh)

    with open(alias_map_path, "r", encoding="utf-8") as fh:
        alias_map = json.load(fh)

    canonical_anchors = concepts_data.get("concepts", [])
    sources = concepts_data.get("sources", ["library"] * len(canonical_anchors))
    logger.info("Loaded %d canonical anchors (sources: %s)",
                len(canonical_anchors),
                dict(Counter(sources)))
    logger.info("Loaded %d alias mappings", len(alias_map))
    return canonical_anchors, sources, alias_map


def build_v11_mapping(v11_path, alias_map):
    """Extract (target_abstract, second_category, third_category) from v11 training data.

    Normalizes target_abstract through alias_map to canonical form.
    Returns:
        v11_abstracts: dict of {abstract_name: {"second": str, "third": str,
                                                  "second_dist": {...}, "third_dist": {...},
                                                  "count": int}}
    """
    with open(v11_path, "r", encoding="utf-8") as fh:
        v11 = json.load(fh)

    td = v11.get("training_data", [])
    logger.info("v11 training samples: %d", len(td))

    # Aggregate
    agg = defaultdict(lambda: {"seconds": Counter(), "thirds": Counter()})

    for item in td:
        raw_abstract = item.get("target_abstract", "").strip()
        second = item.get("target_second_category", "").strip()
        third = item.get("target_third_category", "").strip()
        if not raw_abstract or not second or not third:
            continue

        # Normalize through alias map to canonical form
        canonical = alias_map.get(raw_abstract, raw_abstract)
        agg[canonical]["seconds"][second] += 1
        agg[canonical]["thirds"][third] += 1

    # Build majority-vote mapping
    v11_mapping = {}
    for abstract, counts in agg.items():
        best_second = counts["seconds"].most_common(1)[0][0]
        best_third = counts["thirds"].most_common(1)[0][0]
        total = sum(counts["seconds"].values())
        second_ratio = counts["seconds"].most_common(1)[0][1] / total
        third_ratio = counts["thirds"].most_common(1)[0][1] / total

        v11_mapping[abstract] = {
            "second_category": best_second,
            "third_category": best_third,
            "second_conf": round(second_ratio, 3),
            "third_conf": round(third_ratio, 3),
            "count": total,
            "second_dist": dict(counts["seconds"].most_common(5)),
            "third_dist": dict(counts["thirds"].most_common(5)),
        }

    logger.info("v11 unique abstracts (after alias normalization): %d", len(v11_mapping))

    # Stats on confidence
    high_conf = sum(1 for v in v11_mapping.values() if v["second_conf"] >= 0.5)
    low_conf = len(v11_mapping) - high_conf
    logger.info("  High confidence (>=50%%): %d, Low confidence: %d", high_conf, low_conf)

    return v11_mapping


def build_mappings(canonical_anchors, sources, v11_mapping, model, threshold=0.70,
                   min_confidence=0.30):
    """Build anchor -> (second, third) mappings for all governed anchors.

    For each canonical anchor:
    1. If exact match in v11_mapping, use directly (confidence >= min_confidence)
    2. Otherwise, find most similar v11 abstract via embedding, inherit if sim >= threshold
    3. Otherwise, mark as unmapped
    """
    from sentence_transformers import SentenceTransformer

    logger.info("Loading embedding model: %s", model)
    encoder = SentenceTransformer(model)
    logger.info("Model device: %s", encoder.device)

    # Encode all v11 abstracts
    v11_names = list(v11_mapping.keys())
    logger.info("Encoding %d v11 abstracts...", len(v11_names))
    v11_embs = encoder.encode(v11_names, normalize_embeddings=True,
                              show_progress_bar=True, batch_size=128).astype(np.float32)

    # Build FAISS index
    import faiss
    dim = v11_embs.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(v11_embs)

    # Encode governed anchors
    logger.info("Encoding %d governed anchors...", len(canonical_anchors))
    anchor_embs = encoder.encode(canonical_anchors, normalize_embeddings=True,
                                 show_progress_bar=True, batch_size=128).astype(np.float32)

    # Search
    logger.info("Searching nearest v11 abstracts...")
    scores, indices = index.search(anchor_embs, 1)

    # Build mappings
    mappings = {}
    hierarchy = defaultdict(lambda: defaultdict(list))
    stats = {"total_anchors": len(canonical_anchors),
             "v11_direct": 0, "semantic_inherited": 0, "unmapped": 0,
             "low_confidence": 0}

    for i, anchor in enumerate(canonical_anchors):
        sim = float(scores[i][0])
        best_idx = indices[i][0]
        best_v11_name = v11_names[best_idx]
        v11_info = v11_mapping[best_v11_name]

        if anchor in v11_mapping:
            # Direct match — only if confidence is sufficient
            info = v11_mapping[anchor]
            if info.get("second_conf", 0) >= min_confidence:
                source = "v11_direct"
                stats["v11_direct"] += 1
            else:
                # Low-confidence match — try semantic inheritance instead
                source = None
        else:
            source = None

        if source is None and sim >= threshold:
            # Semantic inheritance from nearest v11 abstract
            info = v11_info
            source = "semantic_inherited"
            stats["semantic_inherited"] += 1
        elif source is None:
            # Truly unmapped — no v11 match and no close neighbor
            source = "unmapped"
            stats["unmapped"] += 1
            mappings[anchor] = {
                "second_category": None,
                "third_category": None,
                "source": "unmapped",
                "confidence": 0.0,
                "nearest_v11_abstract": best_v11_name,
                "nearest_similarity": round(sim, 4),
            }
            continue

        confidence = info["second_conf"]
        if confidence < 0.5:
            stats["low_confidence"] += 1

        mappings[anchor] = {
            "second_category": info["second_category"],
            "third_category": info["third_category"],
            "source": source,
            "confidence": round(confidence, 3),
            "nearest_v11_abstract": best_v11_name if source == "semantic_inherited" else None,
            "nearest_similarity": round(sim, 4) if source == "semantic_inherited" else None,
        }

        # Build hierarchy
        hierarchy[info["third_category"]][info["second_category"]].append(anchor)

    # Convert hierarchy defaultdicts to regular dicts
    hierarchy_dict = {t: {s: list(anchors) for s, anchors in sec.items()}
                      for t, sec in hierarchy.items()}

    logger.info("Mapping complete: v11_direct=%d, semantic_inherited=%d, unmapped=%d, low_confidence=%d",
                stats["v11_direct"], stats["semantic_inherited"],
                stats["unmapped"], stats["low_confidence"])

    return mappings, hierarchy_dict, stats


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Build Anchor→二阶→三阶 hierarchy")
    ap.add_argument("--threshold", type=float, default=0.70,
                    help="Semantic inheritance similarity threshold (default: 0.70)")
    ap.add_argument("--min-confidence", type=float, default=0.30,
                    help="Minimum v11 mapping confidence (default: 0.30)")
    ap.add_argument("--model", type=str, default=None,
                    help="Embedding model path (default: local_models/bge-small-zh-v1.5)")
    ap.add_argument("--output", type=str, default=None,
                    help="Output path (default: data/anchor_hierarchy.json)")
    args = ap.parse_args()

    base = os.path.dirname(os.path.abspath(__file__))

    concepts_path = os.path.join(base, "cache", "anchor_index", "concepts.json")
    alias_path = os.path.join(base, "cache", "anchor_index", "alias_map.json")
    v11_path = os.path.join(base, "standard_answers", "v11_20260428_164754.json")
    output_path = args.output or os.path.join(base, "data", "anchor_hierarchy.json")
    model_path = args.model or os.path.join(base, "local_models", "bge-small-zh-v1.5")

    # Load data
    canonical_anchors, sources, alias_map = load_governed_concepts(concepts_path, alias_path)
    v11_mapping = build_v11_mapping(v11_path, alias_map)

    # Build mappings
    mappings, hierarchy, stats = build_mappings(
        canonical_anchors, sources, v11_mapping, model_path,
        threshold=args.threshold, min_confidence=args.min_confidence)

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    output = {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "description": "Anchor -> 二阶主题 -> 三阶理论 语义压缩层级映射",
        "stats": stats,
        "mappings": mappings,
        "hierarchy": hierarchy,
    }

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)

    logger.info("Saved to: %s", output_path)

    # Summary report
    print(f"\n{'='*60}")
    print(f"Semantic Compression: Anchor -> 二阶 -> 三阶")
    print(f"{'='*60}")
    print(f"  Governed anchors:      {stats['total_anchors']}")
    print(f"  v11 direct match:      {stats['v11_direct']} ({stats['v11_direct']/stats['total_anchors']*100:.1f}%)")
    print(f"  Semantic inherited:    {stats['semantic_inherited']} ({stats['semantic_inherited']/stats['total_anchors']*100:.1f}%)")
    print(f"  Unmapped:              {stats['unmapped']} ({stats['unmapped']/stats['total_anchors']*100:.1f}%)")
    print(f"  Low confidence (<50%): {stats['low_confidence']}")
    print(f"")
    print(f"  Coverage: {stats['v11_direct']+stats['semantic_inherited']}/{stats['total_anchors']} "
          f"({(stats['v11_direct']+stats['semantic_inherited'])/stats['total_anchors']*100:.1f}%)")

    # Sample mappings
    print(f"\n  Sample mappings:")
    sample_anchors = list(mappings.keys())[:10]
    for anchor in sample_anchors:
        m = mappings[anchor]
        print(f"    {anchor} -> [{m['third_category']}] / [{m['second_category']}] "
              f"(src={m['source']}, conf={m['confidence']})")

    # Unmapped anchors
    unmapped = [(a, m) for a, m in mappings.items() if m["source"] == "unmapped"]
    if unmapped:
        print(f"\n  Unmapped anchors ({len(unmapped)}):")
        for a, m in unmapped[:10]:
            print(f"    {a} (nearest: {m['nearest_v11_abstract']}, sim={m['nearest_similarity']})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
