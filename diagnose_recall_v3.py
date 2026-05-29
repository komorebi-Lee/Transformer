"""Recall diagnostic v2 — splits heldout by sentence length and checks coverage."""

import json
import os
import sys
import logging

logging.basicConfig(level=logging.WARNING)  # Suppress noisy logs
logger = logging.getLogger("recall_v2")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_anchor_index import ConceptAnchorIndex


def main():
    base = os.path.dirname(os.path.abspath(__file__))

    idx = ConceptAnchorIndex(
        model_path=os.path.join(base, "trained_models", "concept_anchor_v3"),
        library_path=os.path.join(base, "coding_library.json"),
        anchor_data_path=os.path.join(base, "data", "clean_anchor_pairs.json"),
    )

    # Build set of concepts in the index for coverage check
    index_concepts = set(idx.concepts)

    with open(os.path.join(base, "data", "heldout_anchor_pairs_v3.json"), "r", encoding="utf-8") as fh:
        heldout = json.load(fh)

    pairs = heldout["pairs"]

    # Split by length
    short_pairs = [(p["sentence"], p["anchor_code"]) for p in pairs if len(p["sentence"]) <= 15]
    long_pairs = [(p["sentence"], p["anchor_code"]) for p in pairs if len(p["sentence"]) > 15]

    def eval_subset(name, subset):
        recall_at = {1: 0, 3: 0, 5: 0, 10: 0}
        not_in_index = 0
        total = 0

        for sentence, correct_anchor in subset:
            if not sentence or not correct_anchor:
                continue
            total += 1

            # Check if correct anchor is even in the index
            if correct_anchor not in index_concepts:
                not_in_index += 1
                continue

            results = idx.search(sentence, top_k=10)
            for rank, (concept, score, source) in enumerate(results, 1):
                if concept == correct_anchor:
                    for k in [1, 3, 5, 10]:
                        if rank <= k:
                            recall_at[k] += 1
                    break

        print(f"\n{'='*60}")
        print(f"  {name}: {total} pairs, {not_in_index} anchors NOT in index ({not_in_index/total*100:.1f}%)")
        print(f"{'='*60}")
        for k in [1, 3, 5, 10]:
            rate = recall_at[k] / max(total, 1) * 100
            print(f"  recall@{k:2d}: {recall_at[k]:4d}/{total} = {rate:.1f}%")
        miss_rate = (1 - recall_at[10] / max(total, 1)) * 100
        print(f"  candidate_miss: {miss_rate:.1f}%")

        return total, recall_at, not_in_index

    tot_short, r_short, miss_idx_short = eval_subset("SHORT sentences (<=15 chars, v11 abstracts)", short_pairs)
    tot_long, r_long, miss_idx_long = eval_subset("LONG sentences (>15 chars, full text)", long_pairs)

    # Combined
    combined_recall = {k: r_short[k] + r_long[k] for k in [1, 3, 5, 10]}
    total_all = tot_short + tot_long
    total_miss_idx = miss_idx_short + miss_idx_long
    total_in_index = total_all - total_miss_idx

    print(f"\n{'='*60}")
    print(f"  COMBINED: {total_all} total, {total_miss_idx} anchors missing from index")
    print(f"  Effective total (anchors in index): {total_in_index}")
    print(f"{'='*60}")
    for k in [1, 3, 5, 10]:
        rate = combined_recall[k] / max(total_all, 1) * 100
        eff_rate = combined_recall[k] / max(total_in_index, 1) * 100
        print(f"  recall@{k:2d}: {combined_recall[k]:4d}/{total_all} = {rate:.1f}%  (of in-index: {eff_rate:.1f}%)")
    miss_rate = (1 - combined_recall[10] / max(total_all, 1)) * 100
    eff_miss = (1 - combined_recall[10] / max(total_in_index, 1)) * 100
    print(f"  candidate_miss (of all): {miss_rate:.1f}%")
    print(f"  candidate_miss (of in-index): {eff_miss:.1f}%")
    print(f"  target: 43.6%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
