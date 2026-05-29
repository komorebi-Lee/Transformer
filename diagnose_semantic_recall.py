"""Semantic recall diagnostic: checks if top-k results are SEMANTICALLY
close to the correct anchor (cosine similarity >= threshold), not just exact match.
"""

import json, os, sys, logging
import numpy as np

logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_anchor_index import ConceptAnchorIndex


def main():
    base = os.path.dirname(os.path.abspath(__file__))

    idx = ConceptAnchorIndex(
        model_path=os.path.join(base, "trained_models", "concept_anchor_v3"),
        library_path=os.path.join(base, "coding_library.json"),
        anchor_data_path=os.path.join(base, "data", "clean_anchor_pairs.json"),
    )

    model = idx.model
    index_concepts = set(idx.concepts)

    # Load heldout
    with open(os.path.join(base, "data", "heldout_anchor_pairs_v3.json"), "r", encoding="utf-8") as f:
        heldout = json.load(f)

    pairs = [(p["sentence"], p["anchor_code"]) for p in heldout["pairs"]]

    # Separate short vs long
    short_pairs = [(s, a) for s, a in pairs if len(s) <= 15]
    long_pairs = [(s, a) for s, a in pairs if len(s) > 15]

    SIM_THRESHOLD = 0.80

    def eval_semantic(name, subset):
        # Pre-encode all correct anchors
        correct_anchors = [a for _, a in subset if a in index_concepts]
        correct_sents = [s for s, a in subset if a in index_concepts]

        if not correct_anchors:
            return {}

        anchor_embs = model.encode(correct_anchors, normalize_embeddings=True,
                                   show_progress_bar=False, batch_size=64)

        exact_recall = {1: 0, 3: 0, 5: 0, 10: 0}
        semantic_recall = {1: 0, 3: 0, 5: 0, 10: 0}
        total = 0

        for i, (sentence, correct_anchor) in enumerate(subset):
            if not sentence or correct_anchor not in index_concepts:
                continue
            total += 1

            results = idx.search(sentence, top_k=10)

            # Exact match check
            exact_rank = None
            for rank, (concept, score, src) in enumerate(results, 1):
                if concept == correct_anchor:
                    exact_rank = rank
                    break

            if exact_rank is not None:
                for k in [1, 3, 5, 10]:
                    if exact_rank <= k:
                        exact_recall[k] += 1

            # Semantic match check: is any top-k result similar enough to the correct anchor?
            correct_emb = anchor_embs[i]
            top_texts = [c for c, _, _ in results]
            top_embs = model.encode(top_texts, normalize_embeddings=True,
                                    show_progress_bar=False, batch_size=len(top_texts))

            for k in [1, 3, 5, 10]:
                sims = np.dot(top_embs[:k], correct_emb)
                if np.max(sims) >= SIM_THRESHOLD:
                    semantic_recall[k] += 1
                    break  # Only count once for the largest k

        print(f"\n{'='*60}")
        print(f"  {name}: {total} pairs")
        print(f"{'='*60}")
        print(f"  {'':>12s}  {'Exact match':>12s}  {'Semantic (sim>={:.0f})':>20s}".format(SIM_THRESHOLD*100))
        for k in [1, 3, 5, 10]:
            e_rate = exact_recall[k] / max(total, 1) * 100
            s_rate = semantic_recall[k] / max(total, 1) * 100
            print(f"  recall@{k:2d}:      {exact_recall[k]:4d}/{total} = {e_rate:5.1f}%    "
                  f"{semantic_recall[k]:4d}/{total} = {s_rate:5.1f}%")

        e_miss = (1 - exact_recall[10] / max(total, 1)) * 100
        s_miss = (1 - semantic_recall[10] / max(total, 1)) * 100
        print(f"  candidate_miss (exact):   {e_miss:.1f}%")
        print(f"  candidate_miss (semantic): {s_miss:.1f}%")
        return {"exact_miss": e_miss, "semantic_miss": s_miss, "total": total,
                "exact": exact_recall, "semantic": semantic_recall}

    r_short = eval_semantic("SHORT sentences (<=15 chars, v11 abstracts)", short_pairs)
    r_long = eval_semantic("LONG sentences (>15 chars, full text)", long_pairs)

    # Combined
    if r_short and r_long:
        total = r_short["total"] + r_long["total"]
        for k in [1, 3, 5, 10]:
            e_total = r_short["exact"][k] + r_long["exact"][k]
            s_total = r_short["semantic"][k] + r_long["semantic"][k]
            print(f"  COMBINED recall@{k}: exact={e_total}/{total}={e_total/total*100:.1f}%  "
                  f"semantic={s_total}/{total}={s_total/total*100:.1f}%")
        print(f"  COMBINED candidate_miss: exact={(1-(r_short['exact'][10]+r_long['exact'][10])/total)*100:.1f}%  "
              f"semantic={(1-(r_short['semantic'][10]+r_long['semantic'][10])/total)*100:.1f}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
