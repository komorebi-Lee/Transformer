"""Contrastive Validator — Phase 4 interpretability and drift validation.

Measures:
- interpretability_score: how traceable is the anchor from the source sentence
- semantic_drift: meaning loss/gain from source to anchor (0=none, 1=complete shift)
- candidate_recall: what fraction of ground-truth anchors are retrieved
- drift_adsorption_risk: anchors that attract semantically unrelated sentences

Usage:
    D:/anaconda3/envs/zthree5/python.exe contrastive_validator.py --results coding_test_results.json
    D:/anaconda3/envs/zthree5/python.exe contrastive_validator.py --compare BEFORE.json AFTER.json
"""

import json
import logging
import os
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("contrastive_validator")


class ContrastiveValidator:
    """Validate anchor interpretability, drift, and recall quality."""

    def __init__(self, embedding_model=None):
        self._model = embedding_model
        self._model_loaded = False

    def _load_default_model(self):
        if self._model is not None or self._model_loaded:
            return
        self._model_loaded = True
        try:
            import os as _os
            from sentence_transformers import SentenceTransformer

            # Prefer contrastively trained concept_anchor_v6 for precise
            # concept-level similarity (same expressions → same concept space)
            _v6_path = _os.path.join(
                _os.path.dirname(_os.path.abspath(__file__)),
                "trained_models", "concept_anchor_v6")
            if _os.path.exists(_v6_path):
                self._model = SentenceTransformer(_v6_path)
                logger.info("Validator using contrastive model: concept_anchor_v6")
                return

            # Fallback to generic embedding model
            _bge_path = _os.path.join(
                _os.path.dirname(_os.path.abspath(__file__)),
                "local_models", "bge-small-zh-v1.5")
            if _os.path.exists(_bge_path):
                self._model = SentenceTransformer(_bge_path)
                logger.info("Validator using fallback: bge-small-zh-v1.5")
        except Exception as e:
            logger.debug("Validator model skip: %s", e)

    # ── Interpretability ──────────────────────────────────────────────

    def interpretability_score(
            self,
            sentence: str,
            anchor: str,
            candidates: List[str] = None,
    ) -> dict:
        """Measure how interpretable/traceable an anchor is from its source.

        Returns:
            {
                "score": 0-1 (higher = more interpretable),
                "semantic_overlap": embedding similarity,
                "keyword_bridge": words shared between sentence and anchor,
                "candidate_rank": rank of selected anchor among candidates (if provided),
                "verdict": "clear" | "moderate" | "opaque"
            }
        """
        self._load_default_model()
        import numpy as np

        result = {"score": 0.0, "keyword_bridge": [], "candidate_rank": None}

        # Keyword bridge: words that connect sentence to anchor
        sent_words = set()
        anchor_words = set()
        import re
        for w in re.findall(r'[一-鿿]{2,}', sentence):
            sent_words.add(w)
        for w in re.findall(r'[一-鿿]{2,}', anchor):
            anchor_words.add(w)

        bridge = sent_words & anchor_words
        result["keyword_bridge"] = list(bridge)[:10]

        # Semantic overlap
        if self._model:
            emb_s = self._model.encode([sentence], normalize_embeddings=True,
                                       show_progress_bar=False)[0]
            emb_a = self._model.encode([anchor], normalize_embeddings=True,
                                       show_progress_bar=False)[0]
            sim = float(np.dot(emb_s, emb_a))
            result["semantic_overlap"] = round(sim, 4)
            # Interpretability: combination of semantic match + keyword bridge
            kw_score = min(1.0, len(bridge) / max(len(anchor_words), 1) * 2)
            result["score"] = round(sim * 0.65 + kw_score * 0.35, 4)
        else:
            result["score"] = min(1.0, len(bridge) / max(len(anchor_words), 1) * 1.5)

        # Candidate rank
        if candidates and anchor in candidates:
            result["candidate_rank"] = candidates.index(anchor) + 1

        # Verdict
        if result["score"] >= 0.65:
            result["verdict"] = "clear"
        elif result["score"] >= 0.45:
            result["verdict"] = "moderate"
        else:
            result["verdict"] = "opaque"

        return result

    # ── Semantic Drift ────────────────────────────────────────────────

    def semantic_drift(
            self,
            sentence: str,
            anchor: str,
            neighbors: List[str] = None,
    ) -> dict:
        """Measure how much meaning was lost or changed from source to anchor.

        Drift = 1.0 - grounding_score. High drift means anchor meaning
        has shifted significantly from the original sentence.

        Also checks if anchor is "adsorbing" unrelated sentences.
        """
        from grounding_checker import GroundingChecker
        gc = GroundingChecker(self._model)
        gs = gc.grounding_score(sentence, anchor)

        result = {
            "drift_score": round(1.0 - gs, 4),
            "grounding_score": round(gs, 4),
            "jump_distance": round(gc.jump_distance(sentence, anchor), 4),
            "jump_level": gc.jump_level(gc.jump_distance(sentence, anchor)),
            "polarity_violation": gc.check_polarity(sentence, anchor)[0],
        }

        if result["drift_score"] < 0.3:
            result["drift_verdict"] = "low"
        elif result["drift_score"] < 0.5:
            result["drift_verdict"] = "moderate"
        else:
            result["drift_verdict"] = "high — risk of semantic drift"

        return result

    # ── Candidate Recall ──────────────────────────────────────────────

    def candidate_recall(
            self,
            sentence: str,
            selected_anchor: str,
            candidate_list: List[str],
            ground_truth_anchors: List[str] = None,
    ) -> dict:
        """Measure recall of relevant anchors among candidates.

        If ground_truth_anchors is provided, checks how many are in candidate_list.
        Otherwise, checks if selected_anchor is in candidate_list and at what rank.
        """
        result = {
            "selected_in_candidates": selected_anchor in candidate_list,
            "selected_rank": None,
            "total_candidates": len(candidate_list),
        }

        if selected_anchor in candidate_list:
            result["selected_rank"] = candidate_list.index(selected_anchor) + 1

        if ground_truth_anchors:
            recalled = [a for a in ground_truth_anchors if a in candidate_list]
            result["ground_truth_recall"] = round(
                len(recalled) / max(len(ground_truth_anchors), 1), 4)
            result["recalled_anchors"] = recalled
            result["missed_anchors"] = [
                a for a in ground_truth_anchors if a not in candidate_list]

        return result

    # ── Drift Adsorption Risk ─────────────────────────────────────────

    def adsorption_risk(
            self,
            anchor: str,
            assigned_sentences: List[str],
            similarity_threshold: float = 0.45,
    ) -> dict:
        """Detect anchors that are 'adsorbing' semantically unrelated sentences.

        High variance in sentence-anchor similarities suggests the anchor
        is too generic and catching sentences from different semantic clusters.
        """
        import numpy as np

        if len(assigned_sentences) < 3 or not self._model:
            return {"risk": "unknown", "details": "insufficient data"}

        embs = self._model.encode(
            assigned_sentences + [anchor],
            normalize_embeddings=True, show_progress_bar=False).astype(np.float32)

        anchor_emb = embs[-1]
        sentence_embs = embs[:-1]

        sims = [float(np.dot(anchor_emb, se)) for se in sentence_embs]
        avg_sim = sum(sims) / len(sims)
        std_sim = float(np.std(sims))

        # Unrelated fraction: sentences with similarity below threshold
        unrelated = sum(1 for s in sims if s < similarity_threshold)

        if unrelated > len(assigned_sentences) * 0.3:
            risk = "high"
        elif unrelated > 0 or std_sim > 0.15:
            risk = "moderate"
        else:
            risk = "low"

        return {
            "risk": risk,
            "avg_similarity": round(avg_sim, 4),
            "std_similarity": round(std_sim, 4),
            "min_similarity": round(min(sims), 4),
            "max_similarity": round(max(sims), 4),
            "unrelated_fraction": round(unrelated / len(assigned_sentences), 4),
            "total_sentences": len(assigned_sentences),
        }

    # ── Neighborhood Stability (Priority 5.3) ────────────────────────

    def neighborhood_snapshot(
            self,
            results: List[dict],
            k: int = 10,
    ) -> dict:
        """Take a snapshot of each anchor's semantic neighborhood.

        Returns {anchor_name: {neighbors: [...], embedding_hash: str}}
        that can be compared with later snapshots to detect drift.
        """
        import numpy as np

        # Group anchors and their sentences
        anchor_sent_map = defaultdict(list)
        for r in results:
            code = r.get("code", "")
            sent = r.get("original") or r.get("sentence") or ""
            if code and sent:
                anchor_sent_map[code].append(sent)

        if not anchor_sent_map:
            return {}

        self._load_default_model()

        # Compute anchor embeddings (average of all assigned sentences)
        anchor_embs = {}
        anchor_names = []
        emb_list = []

        for anchor, sents in anchor_sent_map.items():
            if self._model:
                sent_embs = self._model.encode(
                    sents, normalize_embeddings=True, show_progress_bar=False).astype(np.float32)
                anchor_emb = sent_embs.mean(axis=0)
                anchor_emb = anchor_emb / (np.linalg.norm(anchor_emb) + 1e-8)
            else:
                anchor_emb = None

            anchor_embs[anchor] = anchor_emb
            if anchor_emb is not None:
                anchor_names.append(anchor)
                emb_list.append(anchor_emb)

        if not emb_list:
            return {a: {"neighbors": [], "stability": "no_model"} for a in anchor_sent_map}

        # Build FAISS index
        try:
            import faiss
            embs_array = np.array(emb_list, dtype=np.float32)
            dim = embs_array.shape[1]
            index = faiss.IndexFlatIP(dim)
            index.add(embs_array)
            k_search = min(k + 1, len(anchor_names))
            scores, indices = index.search(embs_array, k_search)
        except Exception:
            return {a: {"neighbors": [], "stability": "index_error"} for a in anchor_sent_map}

        snapshot = {}
        for i, anchor in enumerate(anchor_names):
            neighbors = []
            for j in range(1, k_search):  # Skip self (index 0)
                n_idx = indices[i][j]
                n_name = anchor_names[n_idx]
                n_sim = float(scores[i][j])
                if n_sim > 0:
                    neighbors.append({"name": n_name, "similarity": round(n_sim, 4)})

            snapshot[anchor] = {
                "neighbors": neighbors,
                "embedding_hash": None,  # set externally for comparison
            }

        return snapshot

    def neighborhood_stability(
            self,
            before_snapshot: dict,
            after_snapshot: dict,
            k: int = 10,
    ) -> dict:
        """Compare two neighborhood snapshots to measure stability.

        Returns per-anchor stability scores and overall drift indicators.
        """
        common_anchors = set(before_snapshot.keys()) & set(after_snapshot.keys())
        if not common_anchors:
            return {"error": "no common anchors between snapshots"}

        stability_scores = {}
        unstable_anchors = []
        new_anchors = set(after_snapshot.keys()) - set(before_snapshot.keys())
        vanished_anchors = set(before_snapshot.keys()) - set(after_snapshot.keys())

        for anchor in common_anchors:
            before_neighbors = {n["name"] for n in before_snapshot[anchor].get("neighbors", [])}
            after_neighbors = {n["name"] for n in after_snapshot[anchor].get("neighbors", [])}

            if not before_neighbors or not after_neighbors:
                stability_scores[anchor] = 1.0  # Can't measure, assume stable
                continue

            # Jaccard stability: what fraction of neighbors stayed the same
            intersection = before_neighbors & after_neighbors
            union = before_neighbors | after_neighbors
            jaccard = len(intersection) / max(len(union), 1)

            stability_scores[anchor] = round(jaccard, 4)

            if jaccard < 0.3:
                unstable_anchors.append({
                    "anchor": anchor,
                    "stability": jaccard,
                    "before_neighbors": list(before_neighbors)[:5],
                    "after_neighbors": list(after_neighbors)[:5],
                    "vanished": list(before_neighbors - after_neighbors)[:3],
                    "new_neighbors": list(after_neighbors - before_neighbors)[:3],
                })

        scores = list(stability_scores.values())
        avg_stability = sum(scores) / max(len(scores), 1)

        return {
            "total_anchors": len(common_anchors),
            "avg_stability": round(avg_stability, 4),
            "unstable_count": len(unstable_anchors),
            "unstable_anchors": sorted(unstable_anchors, key=lambda x: x["stability"])[:10],
            "new_anchors": len(new_anchors),
            "vanished_anchors": len(vanished_anchors),
            "stability_health": ("stable" if avg_stability >= 0.80 else
                                "moderate" if avg_stability >= 0.60 else
                                "drifting — semantic space decay detected"),
        }

    # ── Full Validation ───────────────────────────────────────────────

    def validate_results(
            self,
            results: List[dict],
            candidate_key: str = "top3_candidates",
    ) -> dict:
        """Run full validation on coding results.

        Each result should have:
          - 'code' (anchor)
          - 'original' or 'sentence' (source text)
          - optionally: candidate_key field with top candidate list
        """
        valid_pairs = []
        for r in results:
            sent = r.get("original") or r.get("sentence") or ""
            code = r.get("code", "")
            if sent and code:
                valid_pairs.append(r)

        if not valid_pairs:
            return {"error": "no valid sentence-anchor pairs"}

        interp_scores = []
        drift_scores = []
        opaque_examples = []
        high_drift_examples = []

        for r in valid_pairs:
            sent = r.get("original") or r.get("sentence") or ""
            code = r.get("code", "")
            candidates = r.get(candidate_key, [])

            # Interpretability
            interp = self.interpretability_score(sent, code, candidates)
            interp_scores.append(interp["score"])

            # Drift
            drift = self.semantic_drift(sent, code)
            drift_scores.append(drift["drift_score"])

            if interp["verdict"] == "opaque":
                opaque_examples.append({
                    "sentence": sent[:100],
                    "anchor": code,
                    "score": interp["score"],
                    "keyword_bridge": interp.get("keyword_bridge", []),
                })
            if drift["drift_verdict"].startswith("high"):
                high_drift_examples.append({
                    "sentence": sent[:100],
                    "anchor": code,
                    "drift": drift["drift_score"],
                    "grounding": drift["grounding_score"],
                })

        # Adsorption check for top anchors
        anchor_to_sents = defaultdict(list)
        for r in valid_pairs:
            anchor_to_sents[r["code"]].append(
                r.get("original") or r.get("sentence") or "")

        freq = Counter(r["code"] for r in valid_pairs)
        adsorption_risks = {}
        for anchor, _ in freq.most_common(15):
            sents = anchor_to_sents.get(anchor, [])
            if len(sents) >= 3:
                adsorption_risks[anchor] = self.adsorption_risk(anchor, sents)

        high_adsorption = {
            a: ar for a, ar in adsorption_risks.items()
            if ar.get("risk") == "high"
        }

        # Overall scores
        n = len(interp_scores)
        avg_interp = sum(interp_scores) / max(n, 1)
        avg_drift = sum(drift_scores) / max(n, 1)

        return {
            "total_pairs": n,
            "interpretability": {
                "avg_score": round(avg_interp, 4),
                "clear_ratio": round(sum(1 for s in interp_scores if s >= 0.65) / n, 4),
                "moderate_ratio": round(sum(1 for s in interp_scores if 0.45 <= s < 0.65) / n, 4),
                "opaque_ratio": round(sum(1 for s in interp_scores if s < 0.45) / n, 4),
                "opaque_examples": opaque_examples[:5],
            },
            "semantic_drift": {
                "avg_drift": round(avg_drift, 4),
                "avg_grounding": round(1.0 - avg_drift, 4),
                "high_drift_examples": high_drift_examples[:5],
            },
            "adsorption": {
                "high_risk_anchors": [
                    {"anchor": a, **ar}
                    for a, ar in high_adsorption.items()
                ][:5],
                "total_checked": len(adsorption_risks),
                "high_risk_count": len(high_adsorption),
            },
        }

    def generate_report(self, validation: dict) -> str:
        """Generate human-readable validation report."""
        lines = []
        lines.append("=" * 70)
        lines.append("  Contrastive Validation Report")
        lines.append("=" * 70)
        lines.append(f"")
        lines.append(f"  Total pairs validated: {validation.get('total_pairs', 0)}")
        lines.append(f"")

        interp = validation.get("interpretability", {})
        lines.append(f"  ── Interpretability ──")
        lines.append(f"    Avg score: {interp.get('avg_score', '?')}")
        lines.append(f"    Clear:      {interp.get('clear_ratio', 0)*100:.1f}%")
        lines.append(f"    Moderate:   {interp.get('moderate_ratio', 0)*100:.1f}%")
        lines.append(f"    Opaque:     {interp.get('opaque_ratio', 0)*100:.1f}%")
        for ex in interp.get("opaque_examples", [])[:3]:
            lines.append(f"    [Opaque] {ex['anchor']}: {ex['sentence'][:60]}...")
        lines.append(f"")

        drift = validation.get("semantic_drift", {})
        lines.append(f"  ── Semantic Drift ──")
        lines.append(f"    Avg drift:     {drift.get('avg_drift', '?')}")
        lines.append(f"    Avg grounding: {drift.get('avg_grounding', '?')}")
        for ex in drift.get("high_drift_examples", [])[:3]:
            lines.append(f"    [High Drift] {ex['anchor']} (drift={ex['drift']}): {ex['sentence'][:60]}...")
        lines.append(f"")

        adsorption = validation.get("adsorption", {})
        lines.append(f"  ── Adsorption Risk ──")
        lines.append(f"    High risk anchors: {adsorption.get('high_risk_count', 0)}/{adsorption.get('total_checked', 0)}")
        for ar in adsorption.get("high_risk_anchors", [])[:3]:
            lines.append(f"    {ar['anchor']}: {ar.get('unrelated_fraction', '?')*100:.0f}% unrelated, std={ar.get('std_similarity', '?')}")
        lines.append(f"")

        # Overall health
        avg_interp = interp.get('avg_score', 0)
        avg_drift = drift.get('avg_drift', 1)
        if avg_interp >= 0.60 and avg_drift <= 0.35:
            lines.append(f"  Overall: GOOD — anchors are interpretable with low drift")
        elif avg_interp >= 0.45 and avg_drift <= 0.50:
            lines.append(f"  Overall: MODERATE — some anchors need grounding improvement")
        else:
            lines.append(f"  Overall: NEEDS WORK — significant interpretability or drift issues")

        return "\n".join(lines)


def compare_validations(before_path, after_path):
    """Compare two coding result files for interpretability and drift deltas."""
    with open(before_path, "r", encoding="utf-8") as f:
        before_data = json.load(f)
    with open(after_path, "r", encoding="utf-8") as f:
        after_data = json.load(f)

    v = ContrastiveValidator()
    before_val = v.validate_results(before_data.get("results", []))
    after_val = v.validate_results(after_data.get("results", []))

    print(v.generate_report(before_val))
    print()
    print(v.generate_report(after_val))

    # Deltas
    print("=" * 70)
    print("  DELTA SUMMARY")
    print("=" * 70)
    bi = before_val.get("interpretability", {})
    ai = after_val.get("interpretability", {})
    bd = before_val.get("semantic_drift", {})
    ad = after_val.get("semantic_drift", {})

    deltas = [
        ("Avg interpretability", bi.get("avg_score", 0), ai.get("avg_score", 0)),
        ("Clear ratio", bi.get("clear_ratio", 0), ai.get("clear_ratio", 0)),
        ("Opaque ratio", bi.get("opaque_ratio", 0), ai.get("opaque_ratio", 0)),
        ("Avg drift", bd.get("avg_drift", 0), ad.get("avg_drift", 0)),
        ("Avg grounding", bd.get("avg_grounding", 0), ad.get("avg_grounding", 0)),
    ]
    for name, b, a in deltas:
        delta = a - b
        direction = "+" if delta > 0 else "-" if delta < 0 else "="
        print(f"  {name}: {b:.3f} → {a:.3f} ({direction}{abs(delta):.3f})")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "coding_test_results.json"))
    parser.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"),
                        help="Compare two result files")
    parser.add_argument("--output", type=str, default=None,
                        help="Save report to file")
    args = parser.parse_args()

    if args.compare:
        compare_validations(args.compare[0], args.compare[1])
        return 0

    with open(args.results, "r", encoding="utf-8") as f:
        data = json.load(f)

    v = ContrastiveValidator()
    validation = v.validate_results(data.get("results", []))
    report = v.generate_report(validation)
    print(report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info("Report saved to: %s", args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
