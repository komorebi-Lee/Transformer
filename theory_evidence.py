"""Theory Evidence System — Priority 13.

Three components:
  1. Evidence Density — multi-anchor, multi-theme, multi-source support metrics
  2. Evidence Diversity — source entropy, anchor dispersion, prevent single-source bias
  3. Evidence-weighted Confidence — enhanced confidence with evidence multipliers

Usage:
    D:\anaconda3\envs\zthree5\python.exe theory_evidence.py
"""

import json
import logging
import os
import sys
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Set

import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("theory_evidence")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Inputs
PROVENANCE_PATH = os.path.join(BASE_DIR, "provenance_report.json")
HIERARCHY_PATH = os.path.join(BASE_DIR, "data", "anchor_hierarchy_stabilized.json")
CONFIDENCE_PATH = os.path.join(BASE_DIR, "theory_confidence.json")
NETWORK_PATH = os.path.join(BASE_DIR, "theory_network.json")

# Outputs
EVIDENCE_PATH = os.path.join(BASE_DIR, "theory_evidence.json")
EVIDENCE_CONFIDENCE_PATH = os.path.join(BASE_DIR, "theory_confidence.json")


def shannon_entropy(counts: List[float]) -> float:
    """Compute Shannon entropy, normalized to [0, 1]."""
    total = sum(counts)
    if total == 0:
        return 0.0
    probs = [c / total for c in counts if c > 0]
    if len(probs) <= 1:
        return 0.0
    max_entropy = np.log(len(probs))
    if max_entropy == 0:
        return 0.0
    entropy = -sum(p * np.log(p) for p in probs)
    return float(entropy / max_entropy)


class TheoryEvidenceSystem:
    """Priority 13: Theory Evidence System."""

    def __init__(self):
        self.provenance = {}
        self.hierarchy = {}
        self.confidence = {}
        self.nodes = []

        # Derived
        self.anchor_prov = {}
        self.theme_prov = {}
        self.theory_prov = {}
        self.full_chains = {}

        # Results
        self.evidence_metrics = {}
        self.evidence_confidence = {}

    def load_data(self):
        with open(PROVENANCE_PATH, "r", encoding="utf-8") as f:
            self.provenance = json.load(f)

        with open(HIERARCHY_PATH, "r", encoding="utf-8") as f:
            self.hierarchy = json.load(f)

        with open(CONFIDENCE_PATH, "r", encoding="utf-8") as f:
            self.confidence = json.load(f).get("scores", {})

        with open(NETWORK_PATH, "r", encoding="utf-8") as f:
            self.nodes = json.load(f).get("nodes", [])

        self.anchor_prov = self.provenance.get("anchor_provenance", {})
        self.theme_prov = self.provenance.get("theme_provenance", {})
        self.theory_prov = self.provenance.get("theory_provenance", {})
        self.full_chains = self.provenance.get("full_chains", {})

        logger.info("Loaded provenance: %d anchors, %d themes, %d theories",
                     len(self.anchor_prov), len(self.theme_prov), len(self.theory_prov))

    # ═══════════════════════════════════════════════════════════════
    # 1. Evidence Density
    # ═══════════════════════════════════════════════════════════════

    ANCHOR_LIST_KEYS = ["supported_by", "supporting_anchors", "anchors"]

    def _get_anchors_for_theme(self, theme_name: str) -> List[str]:
        """Get list of anchor names for a theme from theme_provenance."""
        theme_data = self.theme_prov.get(theme_name, {})
        if not isinstance(theme_data, dict):
            return []
        for key in self.ANCHOR_LIST_KEYS:
            val = theme_data.get(key)
            if isinstance(val, list) and val:
                return val
        return []
    def compute_evidence_density(self) -> dict:
        """Compute evidence density metrics for each L3 theory.

        Measures:
          - source_file_count: number of distinct source files
          - sentence_count: total supporting sentences
          - anchor_count: number of distinct L1 anchors
          - theme_count: number of L2 themes
          - evidence_per_anchor: sentences per anchor
          - evidence_per_theme: sentences per theme
          - source_concentration: Gini-like measure of source distribution
        """
        metrics = {}

        for node in self.nodes:
            name = node["id"]
            tp = self.theory_prov.get(name, {})

            if not tp:
                metrics[name] = {
                    "source_file_count": 0,
                    "sentence_count": 0,
                    "anchor_count": node.get("l1_count", 0),
                    "theme_count": node.get("l2_count", 0),
                    "evidence_per_anchor": 0,
                    "density_score": 0,
                    "source_concentration": 0,
                }
                continue

            # Collect source files for all anchors under this theory
            source_files: Set[str] = set()
            anchor_sentence_counts = defaultdict(int)
            supported_themes = tp.get("supported_by_themes", [])

            # supported_by_themes is a list of theme names (strings)
            theme_names = supported_themes if isinstance(supported_themes, list) else list(supported_themes.keys())

            for theme_name in theme_names:
                # Get anchors for this theme from theme_provenance
                anchors = self._get_anchors_for_theme(theme_name)

                for anchor in anchors:
                    anchor_name = anchor if isinstance(anchor, str) else anchor.get("anchor", str(anchor))
                    records = self.anchor_prov.get(anchor_name, [])
                    anchor_sentence_counts[anchor_name] = len(records)
                    for r in records:
                        sf = r.get("source_file", "")
                        if sf:
                            source_files.add(sf)

            total_sentences = tp.get("total_sentences", sum(anchor_sentence_counts.values()))
            total_anchors = tp.get("total_anchors", len(anchor_sentence_counts))
            total_themes = tp.get("theme_count", len(supported_themes))

            # Density: how many sentences support each anchor on average
            evidence_per_anchor = total_sentences / max(total_anchors, 1)

            # Source concentration (how evenly distributed across sources)
            source_counts = Counter()
            for theme_name in theme_names:
                anchors = self._get_anchors_for_theme(theme_name)
                if not anchors:
                    continue
                for anchor in anchors:
                    anchor_name = anchor if isinstance(anchor, str) else anchor.get("anchor", str(anchor))
                    for r in self.anchor_prov.get(anchor_name, []):
                        sf = r.get("source_file", "")
                        if sf:
                            source_counts[sf] += 1

            source_entropy = shannon_entropy(list(source_counts.values())) if source_counts else 0
            source_concentration = 1.0 - source_entropy  # 0 = diverse, 1 = concentrated

            # Density score: normalized composite
            density_score = min(
                (total_sentences / max(total_anchors * 10, 1)) * 0.4 +
                (len(source_files) / max(total_anchors * 0.3, 1)) * 0.3 +
                (source_entropy * 0.3),
                1.0
            )

            metrics[name] = {
                "source_file_count": len(source_files),
                "sentence_count": total_sentences,
                "anchor_count": total_anchors,
                "theme_count": total_themes,
                "evidence_per_anchor": round(evidence_per_anchor, 2),
                "density_score": round(density_score, 4),
                "source_distribution": {sf: c for sf, c in source_counts.most_common(10)},
                "source_entropy": round(source_entropy, 4),
                "source_concentration": round(source_concentration, 4),
            }

        # Summary
        all_density = [m.get("density_score", 0) for m in metrics.values()]
        all_epa = [m.get("evidence_per_anchor", 0) for m in metrics.values()]

        summary = {
            "avg_density_score": round(np.mean(all_density), 4) if all_density else 0,
            "avg_evidence_per_anchor": round(np.mean(all_epa), 2) if all_epa else 0,
            "high_density": sum(1 for d in all_density if d >= 0.6),
            "medium_density": sum(1 for d in all_density if 0.3 <= d < 0.6),
            "low_density": sum(1 for d in all_density if d < 0.3),
        }

        logger.info("Evidence density: avg=%.4f, high=%d, med=%d, low=%d",
                     summary["avg_density_score"],
                     summary["high_density"],
                     summary["medium_density"],
                     summary["low_density"])

        return {"metrics": metrics, "summary": summary}

    # ═══════════════════════════════════════════════════════════════
    # 2. Evidence Diversity
    # ═══════════════════════════════════════════════════════════════

    def compute_evidence_diversity(self, density_metrics: dict = None) -> dict:
        """Compute evidence diversity metrics.

        Measures how evenly evidence is distributed across:
          - Source files
          - L1 anchors
          - L2 themes
        """
        if density_metrics is None:
            density_metrics = self.compute_evidence_density()

        dm = density_metrics.get("metrics", density_metrics)
        diversity = {}

        for node in self.nodes:
            name = node["id"]
            dm_entry = dm.get(name, {})

            # Anchor-level diversity: check spread across L2 themes
            tp = self.theory_prov.get(name, {})
            supported_themes = tp.get("supported_by_themes", [])
            theme_names = supported_themes if isinstance(supported_themes, list) else list(supported_themes.keys())
            theme_anchor_counts = []

            for theme_name in theme_names:
                anchors = self._get_anchors_for_theme(theme_name)
                theme_anchor_counts.append(len(anchors))

            # Theme entropy: how evenly are anchors distributed across themes?
            theme_entropy = shannon_entropy([float(c) for c in theme_anchor_counts])

            # Source entropy (from density metrics)
            source_entropy = dm_entry.get("source_entropy", 0)

            # Anchor evenness: within each theme, are some anchors dominant?
            anchor_entropies = []
            for theme_name in theme_names:
                anchors = self._get_anchors_for_theme(theme_name)
                if not anchors:
                    continue
                anchor_sent_counts = []
                for anchor in anchors:
                    anchor_name = anchor if isinstance(anchor, str) else anchor.get("anchor", str(anchor))
                    anchor_sent_counts.append(len(self.anchor_prov.get(anchor_name, [])))
                if anchor_sent_counts:
                    anchor_entropies.append(shannon_entropy([float(c) for c in anchor_sent_counts]))

            avg_anchor_entropy = np.mean(anchor_entropies) if anchor_entropies else 0

            # Composite diversity score
            diversity_score = (
                source_entropy * 0.35 +
                theme_entropy * 0.35 +
                avg_anchor_entropy * 0.30
            )

            # Bias detection
            biases = []
            if source_entropy < 0.3 and dm_entry.get("source_file_count", 0) <= 2:
                biases.append("single_source_bias")
            if theme_entropy < 0.3 and len(theme_anchor_counts) > 1:
                biases.append("theme_concentration")
            if avg_anchor_entropy < 0.3 and dm_entry.get("anchor_count", 0) > 3:
                biases.append("anchor_dominance")

            diversity[name] = {
                "theory": name,
                "diversity_score": round(diversity_score, 4),
                "source_entropy": round(source_entropy, 4),
                "theme_entropy": round(theme_entropy, 4),
                "anchor_entropy": round(avg_anchor_entropy, 4),
                "biases": biases,
                "interpretation": self._diversity_interpretation(diversity_score, biases),
            }

        all_div = [d["diversity_score"] for d in diversity.values()]
        summary = {
            "avg_diversity": round(np.mean(all_div), 4) if all_div else 0,
            "high_diversity": sum(1 for d in all_div if d >= 0.6),
            "medium_diversity": sum(1 for d in all_div if 0.35 <= d < 0.6),
            "low_diversity": sum(1 for d in all_div if d < 0.35),
            "biased_theories": sum(1 for d in diversity.values() if d["biases"]),
        }

        logger.info("Evidence diversity: avg=%.4f, biased=%d",
                     summary["avg_diversity"], summary["biased_theories"])

        return {"metrics": diversity, "summary": summary}

    @staticmethod
    def _diversity_interpretation(score: float, biases: List[str]) -> str:
        if score >= 0.7:
            base = "证据来源丰富，多源支撑"
        elif score >= 0.4:
            base = "证据来源较多样"
        else:
            base = "证据来源单一"
        if biases:
            base += f" — 检测到偏倚: {', '.join(biases)}"
        return base

    # ═══════════════════════════════════════════════════════════════
    # 3. Evidence-weighted Confidence
    # ═══════════════════════════════════════════════════════════════

    def compute_evidence_weighted_confidence(self) -> dict:
        """Update theory confidence with evidence density and diversity multipliers.

        New formula:
          evidence_confidence = base_confidence × (1 + evidence_density_weight × 0.25)
                                × (1 + evidence_diversity_weight × 0.20)

        This adds evidence as a positive booster (not a penalty).
        """
        density_data = self.compute_evidence_density()
        diversity_data = self.compute_evidence_diversity(density_data)

        dm = density_data.get("metrics", density_data)
        div = diversity_data.get("metrics", diversity_data)

        updated = {}
        for node in self.nodes:
            name = node["id"]
            base = self.confidence.get(name, {})
            base_conf = base.get("confidence", 0.5)
            comps = base.get("components", {})
            raw = base.get("raw_metrics", {})

            d_entry = dm.get(name, {})
            div_entry = div.get(name, {})

            # Evidence weights
            density = d_entry.get("density_score", 0.3)
            diversity = div_entry.get("diversity_score", 0.3)

            # Boost formula: evidence adds up to 25%+20% = 45% max boost
            evidence_boost = (1.0 + density * 0.25) * (1.0 + diversity * 0.20)
            evidence_boost = min(evidence_boost, 1.5)  # cap at 50% boost

            evidence_confidence = base_conf * evidence_boost

            updated[name] = {
                "confidence": round(min(evidence_confidence, 1.0), 4),
                "base_confidence": round(base_conf, 4),
                "evidence_multiplier": round(evidence_boost, 4),
                "components": {
                    "grounding": comps.get("grounding", 0),
                    "support_diversity": comps.get("support_diversity", 0),
                    "semantic_stability": comps.get("semantic_stability", 0),
                    "provenance_depth": comps.get("provenance_depth", 0),
                    "evidence_density": round(density, 4),
                    "evidence_diversity": round(diversity, 4),
                },
                "raw_metrics": raw,
                "evidence": {
                    "density_score": round(density, 4),
                    "diversity_score": round(diversity, 4),
                    "sources": d_entry.get("source_file_count", 0),
                    "sentences": d_entry.get("sentence_count", 0),
                    "biases": div_entry.get("biases", []),
                },
            }

        # Summary
        all_conf = [c["confidence"] for c in updated.values()]
        all_boost = [c["evidence_multiplier"] for c in updated.values()]

        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_theories": len(updated),
            "avg_confidence": round(np.mean(all_conf), 4),
            "avg_base_confidence": round(np.mean([c["base_confidence"] for c in updated.values()]), 4),
            "avg_evidence_multiplier": round(np.mean(all_boost), 4),
            "max_multiplier": round(max(all_boost), 4),
            "confidence_gain": round(np.mean(all_conf) - np.mean([c["base_confidence"] for c in updated.values()]), 4),
        }

        self.evidence_confidence = {
            "metadata": {
                "version": "2.0",
                "created_at": datetime.now().isoformat(),
                "formula": "evidence_confidence = base_confidence × (1 + density×0.25) × (1 + diversity×0.20)",
            },
            "summary": summary,
            "scores": updated,
        }

        logger.info("Evidence-weighted confidence: avg=%.4f (base=%.4f, +%.4f gain)",
                     summary["avg_confidence"],
                     summary["avg_base_confidence"],
                     summary["confidence_gain"])
        return self.evidence_confidence

    def save_evidence_report(self, density: dict, diversity: dict):
        """Save full evidence report."""
        report = {
            "metadata": {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
            },
            "density": density,
            "diversity": diversity,
        }
        with open(EVIDENCE_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info("Evidence report saved: %s", EVIDENCE_PATH)

    def save_evidence_confidence(self):
        """Save evidence-weighted confidence (updates theory_confidence.json)."""
        if not self.evidence_confidence:
            self.compute_evidence_weighted_confidence()

        with open(EVIDENCE_CONFIDENCE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.evidence_confidence, f, ensure_ascii=False, indent=2)
        logger.info("Evidence-weighted confidence saved: %s", EVIDENCE_CONFIDENCE_PATH)

    # ── Full Pipeline ─────────────────────────────────────────────

    def run(self):
        self.load_data()

        print("\n" + "=" * 60)
        print("PRIORITY 13: THEORY EVIDENCE SYSTEM")
        print("=" * 60)

        print("\n[1/3] Evidence Density...")
        density = self.compute_evidence_density()
        ds = density["summary"]
        print(f"  Avg density: {ds['avg_density_score']:.4f}")
        print(f"  High: {ds['high_density']}, Med: {ds['medium_density']}, Low: {ds['low_density']}")

        print("\n[2/3] Evidence Diversity...")
        diversity = self.compute_evidence_diversity(density)
        div_s = diversity["summary"]
        print(f"  Avg diversity: {div_s['avg_diversity']:.4f}")
        print(f"  Biased theories: {div_s['biased_theories']}")

        self.save_evidence_report(density, diversity)

        print("\n[3/3] Evidence-weighted Confidence...")
        ew_conf = self.compute_evidence_weighted_confidence()
        self.save_evidence_confidence()
        s = ew_conf["summary"]
        print(f"  Avg base confidence: {s['avg_base_confidence']:.4f}")
        print(f"  Avg evidence confidence: {s['avg_confidence']:.4f}")
        print(f"  Avg gain: +{s['confidence_gain']:.4f}")
        print(f"  Avg multiplier: {s['avg_evidence_multiplier']:.4f}")

        print(f"\n  Output: {EVIDENCE_PATH}")
        print(f"  Output: {EVIDENCE_CONFIDENCE_PATH}")

        return {"density": density, "diversity": diversity, "confidence": ew_conf}


# ── CLI ──────────────────────────────────────────────────────────

def main():
    system = TheoryEvidenceSystem()
    result = system.run()

    print("\n" + "=" * 60)
    print("THEORY EVIDENCE SYSTEM COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
