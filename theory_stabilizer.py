"""Theory Stabilizer — Priority 11: Theory Stabilization.

Four subsystems:
  1. Theory Drift Tracking — centroid/neighborhood/confidence/migration
  2. Weak Theory Governance — auto-identify + classify + suggest remedies
  3. Semantic Aging System — staleness tracking + aging penalty
  4. Theory Stability Score — confidence × consistency × density × temporal

First run establishes baseline. Subsequent runs detect drift vs baseline.

Usage:
    D:\anaconda3\envs\zthree5\python.exe theory_stabilizer.py
"""

import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Set

import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("theory_stabilizer")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Inputs
NETWORK_PATH = os.path.join(BASE_DIR, "theory_network.json")
CONFIDENCE_PATH = os.path.join(BASE_DIR, "theory_confidence.json")
PROVENANCE_PATH = os.path.join(BASE_DIR, "provenance_report.json")
HIERARCHY_PATH = os.path.join(BASE_DIR, "data", "anchor_hierarchy_stabilized.json")

# Outputs
BASELINE_PATH = os.path.join(BASE_DIR, "data", "theory_baseline.json")
DRIFT_REPORT_PATH = os.path.join(BASE_DIR, "theory_drift_report.json")
STABILITY_PATH = os.path.join(BASE_DIR, "theory_stability.json")


class TheoryStabilizer:
    """Priority 11: Full theory stabilization pipeline."""

    def __init__(self):
        self.model = None
        self.nodes = []
        self.edges = []
        self.confidence = {}
        self.provenance = {}
        self.hierarchy = {}

        # Derived
        self.node_index = {}
        self.embeddings = None
        self.adjacency = defaultdict(set)
        self.edge_weights = defaultdict(dict)

        # Results
        self.baseline = None
        self.drift_report = {}
        self.stability_scores = {}
        self.aging_report = {}
        self.weak_theories = []

    # ── Data Loading ──────────────────────────────────────────────

    def load_data(self):
        """Load all input data."""
        with open(NETWORK_PATH, "r", encoding="utf-8") as f:
            nd = json.load(f)
        self.nodes = nd.get("nodes", [])
        self.edges = nd.get("edges", [])

        with open(CONFIDENCE_PATH, "r", encoding="utf-8") as f:
            tc = json.load(f)
        self.confidence = tc.get("scores", {})

        with open(PROVENANCE_PATH, "r", encoding="utf-8") as f:
            pr = json.load(f)
        self.provenance = pr

        with open(HIERARCHY_PATH, "r", encoding="utf-8") as f:
            hh = json.load(f)
        self.hierarchy = hh

        # Build indices
        self.node_index = {n["id"]: n for n in self.nodes}
        for e in self.edges:
            s, t = e["source"], e["target"]
            self.adjacency[s].add(t)
            self.adjacency[t].add(s)
            self.edge_weights[s][t] = e.get("weight", 0)
            self.edge_weights[t][s] = e.get("weight", 0)

        logger.info("Loaded: %d nodes, %d edges, %d confidence scores",
                     len(self.nodes), len(self.edges), len(self.confidence))

    def _load_model(self):
        """Load embedding model for theory encoding."""
        if self.model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            v6_path = os.path.join(BASE_DIR, "trained_models", "concept_anchor_v6")
            if os.path.exists(v6_path):
                self.model = SentenceTransformer(v6_path)
            else:
                bge_path = os.path.join(BASE_DIR, "local_models", "bge-small-zh-v1.5")
                if os.path.exists(bge_path):
                    self.model = SentenceTransformer(bge_path)
            if self.model:
                logger.info("Loaded embedding model for theory stabilization")
        except Exception as e:
            logger.warning("Model load failed: %s", e)

    # ═══════════════════════════════════════════════════════════════
    # SUBSYSTEM 1: Theory Drift Tracking
    # ═══════════════════════════════════════════════════════════════

    def establish_baseline(self) -> dict:
        """Establish baseline state for future drift comparison."""
        self._load_model()

        names = [n["id"] for n in self.nodes]
        embeddings = None
        if self.model:
            embeddings = self.model.encode(
                names, normalize_embeddings=True, show_progress_bar=False
            ).astype(np.float32)

        baseline = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "theories": {},
        }

        for i, node in enumerate(self.nodes):
            name = node["id"]
            conf = self.confidence.get(name, {})
            neighbors = sorted(self.adjacency.get(name, set()))
            neighbor_weights = [self.edge_weights[name].get(nb, 0) for nb in neighbors]

            entry = {
                "name": name,
                "embedding": embeddings[i].tolist() if embeddings is not None else None,
                "centroid": embeddings[i].tolist() if embeddings is not None else None,
                "confidence": conf.get("confidence", 0),
                "neighbors": neighbors,
                "neighbor_weights": neighbor_weights,
                "avg_neighbor_weight": np.mean(neighbor_weights) if neighbor_weights else 0,
                "degree": len(neighbors),
                "l1_count": node.get("l1_count", 0),
                "l2_count": node.get("l2_count", 0),
                "sentence_count": node.get("sentence_count", 0),
                "avg_grounding": node.get("avg_grounding", 0),
            }
            baseline["theories"][name] = entry

        # Save baseline
        os.makedirs(os.path.dirname(BASELINE_PATH), exist_ok=True)
        with open(BASELINE_PATH, "w", encoding="utf-8") as f:
            json.dump(baseline, f, ensure_ascii=False, indent=2)
        logger.info("Baseline established: %d theories saved to %s",
                     len(baseline["theories"]), BASELINE_PATH)

        self.baseline = baseline
        return baseline

    def detect_drift(self) -> dict:
        """Detect drift by comparing current state to baseline."""
        # Load baseline if not already loaded
        if self.baseline is None:
            if os.path.exists(BASELINE_PATH):
                with open(BASELINE_PATH, "r", encoding="utf-8") as f:
                    self.baseline = json.load(f)
                logger.info("Loaded existing baseline from %s", BASELINE_PATH)
            else:
                logger.info("No baseline found, establishing new baseline")
                self.establish_baseline()
                return {
                    "status": "baseline_established",
                    "timestamp": self.baseline["timestamp"],
                    "message": "First run — baseline established, no drift to report",
                    "drift_summary": {},
                    "drifted_theories": [],
                }

        self._load_model()
        baseline_theories = self.baseline.get("theories", {})

        # Compute current embeddings
        names = [n["id"] for n in self.nodes]
        current_embeddings = None
        if self.model:
            current_embeddings = self.model.encode(
                names, normalize_embeddings=True, show_progress_bar=False
            ).astype(np.float32)

        name_to_idx = {name: i for i, name in enumerate(names)}

        drift_results = []
        for i, node in enumerate(self.nodes):
            name = node["id"]
            bl = baseline_theories.get(name)
            if bl is None:
                # New theory, no baseline
                drift_results.append({
                    "theory": name,
                    "status": "new",
                    "centroid_drift": None,
                    "neighborhood_drift": None,
                    "confidence_drift": None,
                    "semantic_migration": None,
                })
                continue

            # 1. Centroid drift (cosine distance from baseline embedding)
            centroid_drift = None
            if (current_embeddings is not None and bl.get("centroid")
                    and bl["centroid"] is not None):
                bl_emb = np.array(bl["centroid"], dtype=np.float32)
                cur_emb = current_embeddings[i]
                centroid_drift = float(1.0 - np.dot(bl_emb, cur_emb))

            # 2. Neighborhood drift (Jaccard distance)
            cur_neighbors = set(self.adjacency.get(name, set()))
            bl_neighbors = set(bl.get("neighbors", []))
            union = len(cur_neighbors | bl_neighbors)
            intersection = len(cur_neighbors & bl_neighbors)
            neighborhood_drift = 1.0 - (intersection / max(union, 1))

            # 3. Confidence drift
            cur_conf = self.confidence.get(name, {}).get("confidence", 0)
            bl_conf = bl.get("confidence", 0)
            confidence_drift = cur_conf - bl_conf  # positive = gained confidence

            # 4. Semantic migration (has nearest neighbor changed?)
            semantic_migration = None
            if (current_embeddings is not None and bl.get("embedding")
                    and bl["embedding"] is not None):
                cur_emb = current_embeddings[i]
                bl_emb = np.array(bl["embedding"], dtype=np.float32)

                # Find current nearest neighbor (excluding self)
                cur_sims = np.dot(current_embeddings, cur_emb)
                cur_sims[i] = -1  # exclude self
                cur_nearest_idx = int(np.argmax(cur_sims))
                cur_nearest_name = names[cur_nearest_idx]

                bl_nearest = bl.get("nearest_neighbor")
                if bl_nearest and bl_nearest != cur_nearest_name:
                    semantic_migration = {
                        "from": bl_nearest,
                        "to": cur_nearest_name,
                        "similarity_change": float(cur_sims[cur_nearest_idx] -
                                                   bl.get("nearest_neighbor_sim", 0)),
                    }

            # Classify drift severity
            total_drift = 0
            if centroid_drift is not None:
                total_drift += centroid_drift
            total_drift += neighborhood_drift
            if abs(confidence_drift) > 0.1:
                total_drift += abs(confidence_drift)

            if total_drift > 0.5:
                severity = "high"
            elif total_drift > 0.25:
                severity = "moderate"
            elif total_drift > 0.05:
                severity = "low"
            else:
                severity = "stable"

            drift_results.append({
                "theory": name,
                "status": severity,
                "centroid_drift": round(centroid_drift, 5) if centroid_drift is not None else None,
                "neighborhood_drift": round(neighborhood_drift, 4),
                "confidence_drift": round(confidence_drift, 4),
                "semantic_migration": semantic_migration,
            })

        # Summarize
        drifted = [d for d in drift_results if d["status"] not in ("stable", "new")]
        new_theories = [d for d in drift_results if d["status"] == "new"]
        high_drift = [d for d in drift_results if d["status"] == "high"]

        summary = {
            "total_theories": len(drift_results),
            "stable": sum(1 for d in drift_results if d["status"] == "stable"),
            "low_drift": sum(1 for d in drift_results if d["status"] == "low"),
            "moderate_drift": sum(1 for d in drift_results if d["status"] == "moderate"),
            "high_drift": len(high_drift),
            "new_theories": len(new_theories),
        }

        report = {
            "timestamp": datetime.now().isoformat(),
            "baseline_timestamp": self.baseline.get("timestamp"),
            "drift_summary": summary,
            "drifted_theories": drifted,
            "high_drift_alerts": [
                {"theory": d["theory"],
                 "centroid_drift": d["centroid_drift"],
                 "neighborhood_drift": d["neighborhood_drift"]}
                for d in high_drift
            ],
        }

        self.drift_report = report
        return report

    def save_drift_report(self):
        """Save drift report to disk."""
        if not self.drift_report:
            self.detect_drift()
        with open(DRIFT_REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(self.drift_report, f, ensure_ascii=False, indent=2)
        logger.info("Drift report saved: %s", DRIFT_REPORT_PATH)

    # ═══════════════════════════════════════════════════════════════
    # SUBSYSTEM 2: Weak Theory Governance
    # ═══════════════════════════════════════════════════════════════

    def identify_weak_theories(self) -> List[dict]:
        """Identify and classify weak theories."""
        weak = []

        for node in self.nodes:
            name = node["id"]
            conf = self.confidence.get(name, {})
            comps = conf.get("components", {})
            raw = conf.get("raw_metrics", {})
            confidence_val = conf.get("confidence", 0)
            degree = raw.get("network_degree", 0)
            l1_count = node.get("l1_count", 0)
            l2_count = node.get("l2_count", 0)
            grounding = node.get("avg_grounding", 0)
            sentence_count = node.get("sentence_count", 0)
            avg_edge_w = raw.get("avg_edge_weight", 0)

            issues = []
            severity = "ok"

            # Check 1: low confidence
            if confidence_val < 0.35:
                issues.append("low_confidence")
                severity = "critical"
            elif confidence_val < 0.45:
                issues.append("borderline_confidence")
                if severity != "critical":
                    severity = "warning"

            # Check 2: low support (few anchors)
            if l1_count <= 2:
                issues.append("low_support")
                if severity == "ok":
                    severity = "warning"

            # Check 3: sparse grounding
            if grounding < 0.45:
                issues.append("weak_grounding")
                if severity == "ok":
                    severity = "warning"

            # Check 4: over-connected hub (potential semantic hub)
            if degree >= 7 and avg_edge_w < 0.2:
                issues.append("unstable_hub")
                if severity == "ok":
                    severity = "warning"

            # Check 5: over-merged (many anchors, low confidence suggests forced merge)
            if l1_count > 15 and confidence_val < 0.5:
                issues.append("possible_over_merge")
                if severity != "critical":
                    severity = "warning"

            # Check 6: isolated
            if degree == 0:
                issues.append("isolated")
                severity = "critical"

            # Check 7: low provenance depth
            if sentence_count < 10 and l1_count > 3:
                issues.append("thin_evidence")
                if severity == "ok":
                    severity = "warning"

            # Check 8: single L2 dependency (fragile structure)
            if l2_count == 1 and l1_count >= 3:
                issues.append("fragile_structure")

            if issues:
                suggested_actions = self._suggest_remedies(name, issues, confidence_val,
                                                           l1_count, degree, grounding)
                weak.append({
                    "theory": name,
                    "severity": severity,
                    "issues": issues,
                    "confidence": round(confidence_val, 4),
                    "l1_count": l1_count,
                    "l2_count": l2_count,
                    "degree": degree,
                    "avg_grounding": round(grounding, 4),
                    "avg_edge_weight": round(avg_edge_w, 4),
                    "sentence_count": sentence_count,
                    "suggested_actions": suggested_actions,
                })

        # Sort by severity (critical first) then by confidence
        severity_order = {"critical": 0, "warning": 1, "ok": 2}
        weak.sort(key=lambda w: (severity_order.get(w["severity"], 3), w["confidence"]))

        self.weak_theories = weak
        logger.info("Identified %d weak theories (%d critical, %d warning)",
                     len(weak),
                     sum(1 for w in weak if w["severity"] == "critical"),
                     sum(1 for w in weak if w["severity"] == "warning"))
        return weak

    def _suggest_remedies(self, name: str, issues: List[str], confidence: float,
                          l1_count: int, degree: int, grounding: float) -> List[str]:
        """Suggest remediation actions for a weak theory."""
        actions = []

        for issue in issues:
            if issue in ("low_confidence", "borderline_confidence"):
                actions.append("review_provenance: 检查该理论的源文支撑是否充分")
                if l1_count <= 3:
                    actions.append("consider_merge: 考虑合并到最近的同族理论")
                else:
                    actions.append("recluster_check: 检查L1锚点聚类是否合理")

            if issue == "low_support":
                actions.append("merge_candidate: 锚点<3，建议合并到语义最接近的理论")
                actions.append("find_nearest_parent: 搜索最近的高置信度理论作为合并目标")

            if issue == "weak_grounding":
                actions.append("grounding_review: 该理论锚点扎根度低，检查编码质量")

            if issue == "unstable_hub":
                actions.append("hub_prune: 考虑移除此节点或拆分其连接")
                actions.append("edge_quality_review: 检查低权重边是否需要移除")

            if issue == "possible_over_merge":
                actions.append("split_candidate: 锚点数>15且置信度<0.5，可能是强制合并，建议聚类拆分")

            if issue == "isolated":
                actions.append("urgent_connect: 孤立节点，需要建立至少1条边或重新归类")

            if issue == "thin_evidence":
                actions.append("evidence_review: 证据句数不足，检查覆盖是否充分")

            if issue == "fragile_structure":
                actions.append("structure_review: 仅1个L2主题，结构脆弱")

        return actions

    # ═══════════════════════════════════════════════════════════════
    # SUBSYSTEM 3: Semantic Aging System
    # ═══════════════════════════════════════════════════════════════

    def compute_semantic_age(self) -> dict:
        """Compute semantic age/staleness for each theory.

        A theory is 'stale' if it hasn't received new provenance evidence.
        Since we don't have historical timestamps per theory, we use the
        provenance report timestamp as the last evidence date.
        """
        # Get base timestamp
        prov_ts = self.provenance.get("metadata", {}).get("created_at",
                   self.provenance.get("metadata", {}).get("timestamp",
                   datetime.now().isoformat()))
        try:
            base_date = datetime.fromisoformat(prov_ts)
        except (ValueError, TypeError):
            base_date = datetime.now()

        now = datetime.now()
        days_since_base = max((now - base_date).days, 1)

        aging = {}
        theory_prov = self.provenance.get("theory_provenance", {})

        for node in self.nodes:
            name = node["id"]
            tp = theory_prov.get(name, {})
            total_sentences = tp.get("total_sentences", node.get("sentence_count", 0))
            conf = self.confidence.get(name, {}).get("confidence", 0.5)

            # Freshness: how much evidence relative to other theories
            all_sentences = [
                theory_prov.get(n["id"], {}).get("total_sentences", 0)
                for n in self.nodes
            ]
            max_sentences = max(all_sentences) if all_sentences else 1
            evidence_freshness = min(total_sentences / max(max_sentences * 0.5, 1), 1.0)

            # Age factor: theories with low evidence density age faster
            density = total_sentences / max(node.get("l1_count", 1), 1)
            if density < 5:
                age_multiplier = 2.0  # ages 2x faster
            elif density < 15:
                age_multiplier = 1.0
            else:
                age_multiplier = 0.5  # ages slower with rich evidence

            effective_age_days = days_since_base * age_multiplier

            # Aging penalty: sigmoid curve
            aging_penalty = 1.0 / (1.0 + np.exp(-(effective_age_days - 30) / 10))

            # Staleness classification
            if effective_age_days > 90:
                staleness = "stale"
            elif effective_age_days > 45:
                staleness = "aging"
            elif effective_age_days > 14:
                staleness = "maturing"
            else:
                staleness = "fresh"

            aging[name] = {
                "theory": name,
                "effective_age_days": round(effective_age_days, 1),
                "aging_penalty": round(aging_penalty, 4),
                "staleness": staleness,
                "evidence_freshness": round(evidence_freshness, 4),
                "total_sentences": total_sentences,
                "evidence_density": round(density, 1),
            }

        self.aging_report = {
            "timestamp": now.isoformat(),
            "base_evidence_date": base_date.isoformat(),
            "days_since_base": days_since_base,
            "summary": {
                "fresh": sum(1 for a in aging.values() if a["staleness"] == "fresh"),
                "maturing": sum(1 for a in aging.values() if a["staleness"] == "maturing"),
                "aging": sum(1 for a in aging.values() if a["staleness"] == "aging"),
                "stale": sum(1 for a in aging.values() if a["staleness"] == "stale"),
            },
            "theories": aging,
        }

        logger.info("Semantic aging: %d fresh, %d maturing, %d aging, %d stale",
                     self.aging_report["summary"]["fresh"],
                     self.aging_report["summary"]["maturing"],
                     self.aging_report["summary"]["aging"],
                     self.aging_report["summary"]["stale"])
        return self.aging_report

    # ═══════════════════════════════════════════════════════════════
    # SUBSYSTEM 4: Theory Stability Score
    # ═══════════════════════════════════════════════════════════════

    def compute_stability(self) -> dict:
        """Compute Theory Stability Score for each theory.

        Stability = confidence × neighborhood_consistency × provenance_density × temporal_stability
        """
        if not self.aging_report:
            self.compute_semantic_age()

        scores = {}
        raw_vals = {"confidence": [], "neighborhood": [], "provenance": [], "temporal": []}

        for node in self.nodes:
            name = node["id"]
            conf = self.confidence.get(name, {}).get("confidence", 0.5)
            raw = self.confidence.get(name, {}).get("raw_metrics", {})

            # 1. Confidence component (already computed)
            confidence_comp = conf

            # 2. Neighborhood consistency
            degree = raw.get("network_degree", 0)
            avg_edge_w = raw.get("avg_edge_weight", 0)
            if degree > 0:
                # Check edge weight variance
                nb_weights = [self.edge_weights[name].get(nb, 0)
                              for nb in self.adjacency.get(name, [])]
                weight_var = np.var(nb_weights) if len(nb_weights) > 1 else 0
                consistency = avg_edge_w / max(weight_var + 0.1, 0.01)
                neighborhood_comp = min(consistency / 2, 1.0)
            else:
                neighborhood_comp = 0.0

            # 3. Provenance density
            l1_count = max(node.get("l1_count", 1), 1)
            sentence_count = max(node.get("sentence_count", 1), 1)
            density = sentence_count / l1_count
            provenance_comp = min(density / 20, 1.0)  # 20 sentences per anchor = full marks

            # 4. Temporal stability (inverse of aging penalty)
            aging_info = self.aging_report.get("theories", {}).get(name, {})
            aging_penalty = aging_info.get("aging_penalty", 0)
            temporal_comp = 1.0 - aging_penalty

            # Composite stability
            stability = (
                confidence_comp * 0.30 +
                neighborhood_comp * 0.25 +
                provenance_comp * 0.25 +
                temporal_comp * 0.20
            )

            raw_vals["confidence"].append(confidence_comp)
            raw_vals["neighborhood"].append(neighborhood_comp)
            raw_vals["provenance"].append(provenance_comp)
            raw_vals["temporal"].append(temporal_comp)

            scores[name] = {
                "theory": name,
                "stability": round(stability, 4),
                "confidence": round(confidence_comp, 4),
                "neighborhood_consistency": round(neighborhood_comp, 4),
                "provenance_density": round(provenance_comp, 4),
                "temporal_stability": round(temporal_comp, 4),
                "staleness": aging_info.get("staleness", "unknown"),
            }

        self.stability_scores = scores

        # Summary
        all_stab = [s["stability"] for s in scores.values()]
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_theories": len(scores),
            "avg_stability": round(np.mean(all_stab), 4),
            "min_stability": round(np.min(all_stab), 4),
            "max_stability": round(np.max(all_stab), 4),
            "std_stability": round(np.std(all_stab), 4),
            "stable_count": sum(1 for s in all_stab if s >= 0.6),
            "moderate_count": sum(1 for s in all_stab if 0.35 <= s < 0.6),
            "unstable_count": sum(1 for s in all_stab if s < 0.35),
            "component_averages": {
                "confidence": round(np.mean(raw_vals["confidence"]), 4),
                "neighborhood_consistency": round(np.mean(raw_vals["neighborhood"]), 4),
                "provenance_density": round(np.mean(raw_vals["provenance"]), 4),
                "temporal_stability": round(np.mean(raw_vals["temporal"]), 4),
            },
        }
        self.stability_scores["_summary"] = summary

        logger.info("Stability scores: avg=%.4f, %d stable, %d moderate, %d unstable",
                     summary["avg_stability"], summary["stable_count"],
                     summary["moderate_count"], summary["unstable_count"])
        return scores

    def save_stability(self):
        """Save stability scores to disk."""
        if not self.stability_scores:
            self.compute_stability()

        output = {
            "metadata": {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "total_theories": self.stability_scores["_summary"]["total_theories"],
            },
            "summary": self.stability_scores["_summary"],
            "scores": {k: v for k, v in self.stability_scores.items() if k != "_summary"},
        }
        with open(STABILITY_PATH, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        logger.info("Stability scores saved: %s", STABILITY_PATH)

    # ── Full Pipeline ─────────────────────────────────────────────

    def run(self):
        """Run full theory stabilization pipeline."""
        self.load_data()

        print("\n" + "=" * 60)
        print("PRIORITY 11: THEORY STABILIZATION")
        print("=" * 60)

        # 1. Drift tracking
        print("\n[1/4] Drift Tracking...")
        drift = self.detect_drift()
        self.save_drift_report()
        ds = drift.get("drift_summary", {})
        status = drift.get("status", "")
        if status == "baseline_established":
            print(f"  Status: Baseline established (first run)")
        else:
            print(f"  Stable: {ds.get('stable', 0)}")
            print(f"  Low drift: {ds.get('low_drift', 0)}")
            print(f"  Moderate drift: {ds.get('moderate_drift', 0)}")
            print(f"  High drift: {ds.get('high_drift', 0)}")

        # 2. Weak theory governance
        print("\n[2/4] Weak Theory Governance...")
        weak = self.identify_weak_theories()
        critical = [w for w in weak if w["severity"] == "critical"]
        warning = [w for w in weak if w["severity"] == "warning"]
        print(f"  Critical: {len(critical)}")
        print(f"  Warning: {len(warning)}")
        if critical:
            print(f"  Top critical issues:")
            for w in critical[:5]:
                print(f"    - {w['theory']}: {', '.join(w['issues'])}")

        # 3. Semantic aging
        print("\n[3/4] Semantic Aging...")
        aging = self.compute_semantic_age()
        sa = aging["summary"]
        print(f"  Fresh: {sa['fresh']}, Maturing: {sa['maturing']}, "
              f"Aging: {sa['aging']}, Stale: {sa['stale']}")

        # 4. Stability scores
        print("\n[4/4] Stability Scoring...")
        self.compute_stability()
        self.save_stability()
        ss = self.stability_scores["_summary"]
        print(f"  Avg stability: {ss['avg_stability']:.4f}")
        print(f"  Stable (>=0.6): {ss['stable_count']}")
        print(f"  Moderate (0.35-0.6): {ss['moderate_count']}")
        print(f"  Unstable (<0.35): {ss['unstable_count']}")

        print(f"\n  Output: {DRIFT_REPORT_PATH}")
        print(f"  Output: {STABILITY_PATH}")
        print(f"  Baseline: {BASELINE_PATH}")

        return {
            "drift": drift,
            "weak_theories": weak,
            "aging": aging,
            "stability": self.stability_scores,
        }


# ── CLI ──────────────────────────────────────────────────────────

def main():
    stabilizer = TheoryStabilizer()
    result = stabilizer.run()

    print("\n" + "=" * 60)
    print("THEORY STABILIZATION COMPLETE")
    print("=" * 60)

    weak = result["weak_theories"]
    critical = [w for w in weak if w["severity"] == "critical"]
    if critical:
        print(f"\n⚠  {len(critical)} theories need immediate attention:")
        for w in critical[:10]:
            print(f"  [{w['severity'].upper()}] {w['theory']} (conf={w['confidence']:.3f})")
            for action in w.get("suggested_actions", [])[:2]:
                print(f"    → {action}")


if __name__ == "__main__":
    main()
