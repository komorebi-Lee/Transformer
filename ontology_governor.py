"""Autonomous Ontology Governance — Priority 12.

Three subsystems:
  1. Ontology Repair Engine — detect + suggest fixes for semantic issues
  2. Adaptive Compression — dynamic threshold based on density/entropy/drift
  3. Governance Policy Engine — rule-based semantic governance

Usage:
    D:\anaconda3\envs\zthree5\python.exe ontology_governor.py
"""

import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("ontology_governor")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Inputs
HIERARCHY_PATH = os.path.join(BASE_DIR, "data", "anchor_hierarchy_stabilized.json")
NETWORK_PATH = os.path.join(BASE_DIR, "theory_network.json")
CONFIDENCE_PATH = os.path.join(BASE_DIR, "theory_confidence.json")
PROVENANCE_PATH = os.path.join(BASE_DIR, "provenance_report.json")
DRIFT_PATH = os.path.join(BASE_DIR, "theory_drift_report.json")
STABILITY_PATH = os.path.join(BASE_DIR, "theory_stability.json")
HEALTH_PATH = os.path.join(BASE_DIR, "network_health.json")

# Outputs
REPAIR_REPORT_PATH = os.path.join(BASE_DIR, "ontology_repair_report.json")
COMPRESSION_CONFIG_PATH = os.path.join(BASE_DIR, "data", "adaptive_compression_config.json")
POLICY_PATH = os.path.join(BASE_DIR, "data", "governance_policy.json")
POLICY_REPORT_PATH = os.path.join(BASE_DIR, "policy_violation_report.json")

# Default thresholds for adaptive compression
DEFAULT_L2_MERGE_SIMILARITY = 0.62
DEFAULT_L3_CLUSTER_SIMILARITY = 0.58


class OntologyGovernor:
    """Priority 12: Autonomous Ontology Governance."""

    def __init__(self):
        self.model = None
        self.hierarchy = {}
        self.nodes = []
        self.edges = []
        self.confidence = {}
        self.provenance = {}
        self.drift = {}
        self.stability = {}

        # Derived
        self.l3_theories = {}  # name → {l2s, l1s, anchors}
        self.l2_themes = {}    # name → {l3s, anchors}
        self.anchor_map = {}   # anchor → {l2, l3}
        self.embeddings = None
        self.l3_names = []

        # Results
        self.repair_suggestions = []
        self.compression_config = {}
        self.policy_violations = []

    # ── Data Loading ──────────────────────────────────────────────

    def load_data(self):
        """Load all input data."""
        with open(HIERARCHY_PATH, "r", encoding="utf-8") as f:
            self.hierarchy = json.load(f)

        with open(NETWORK_PATH, "r", encoding="utf-8") as f:
            nd = json.load(f)
            self.nodes = nd.get("nodes", [])
            self.edges = nd.get("edges", [])

        with open(CONFIDENCE_PATH, "r", encoding="utf-8") as f:
            self.confidence = json.load(f).get("scores", {})

        with open(PROVENANCE_PATH, "r", encoding="utf-8") as f:
            self.provenance = json.load(f)

        if os.path.exists(DRIFT_PATH):
            with open(DRIFT_PATH, "r", encoding="utf-8") as f:
                self.drift = json.load(f)

        if os.path.exists(STABILITY_PATH):
            with open(STABILITY_PATH, "r", encoding="utf-8") as f:
                self.stability = json.load(f)

        # Build hierarchy indices
        mappings = self.hierarchy.get("mappings", {})
        for anchor, m in mappings.items():
            l2 = m.get("second_category", "")
            l3 = m.get("third_category", "")
            self.anchor_map[anchor] = {"l2": l2, "l3": l3}

            if l3:
                if l3 not in self.l3_theories:
                    self.l3_theories[l3] = {"l2s": set(), "anchors": set()}
                self.l3_theories[l3]["anchors"].add(anchor)
                if l2:
                    self.l3_theories[l3]["l2s"].add(l2)

            if l2:
                if l2 not in self.l2_themes:
                    self.l2_themes[l2] = {"l3s": set(), "anchors": set()}
                self.l2_themes[l2]["anchors"].add(anchor)
                if l3:
                    self.l2_themes[l2]["l3s"].add(l3)

        # Convert sets to sorted lists for serialization
        for t in self.l3_theories.values():
            t["l2s"] = sorted(t["l2s"])
            t["anchors"] = sorted(t["anchors"])
        for t in self.l2_themes.values():
            t["l3s"] = sorted(t["l3s"])
            t["anchors"] = sorted(t["anchors"])

        self.l3_names = sorted(self.l3_theories.keys())

        logger.info("Loaded: %d L3 theories, %d L2 themes, %d anchors",
                     len(self.l3_theories), len(self.l2_themes), len(self.anchor_map))

    def _load_model(self):
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
                logger.info("Loaded embedding model for ontology governance")
        except Exception as e:
            logger.warning("Model load failed: %s", e)

    # ═══════════════════════════════════════════════════════════════
    # SUBSYSTEM 1: Ontology Repair Engine
    # ═══════════════════════════════════════════════════════════════

    def detect_duplicate_theories(self, sim_threshold: float = 0.78) -> List[dict]:
        """Detect L3 theory pairs with very high semantic similarity."""
        self._load_model()
        if self.model is None or len(self.l3_names) <= 1:
            return []

        embeddings = self.model.encode(
            self.l3_names, normalize_embeddings=True, show_progress_bar=False
        ).astype(np.float32)
        self.embeddings = embeddings

        duplicates = []
        n = len(self.l3_names)
        for i in range(n):
            for j in range(i + 1, n):
                sim = float(np.dot(embeddings[i], embeddings[j]))
                if sim >= sim_threshold:
                    ni, nj = self.l3_names[i], self.l3_names[j]
                    # Check if they also share anchors
                    shared_anchors = (
                        set(self.l3_theories.get(ni, {}).get("anchors", [])) &
                        set(self.l3_theories.get(nj, {}).get("anchors", []))
                    )
                    duplicates.append({
                        "type": "duplicate_theories",
                        "theory_a": ni,
                        "theory_b": nj,
                        "semantic_similarity": round(sim, 4),
                        "shared_anchors": len(shared_anchors),
                        "suggested_action": "merge",
                        "priority": "high" if sim >= 0.85 else "medium",
                        "rationale": f"语义相似度{sim:.3f}，共享{len(shared_anchors)}个锚点",
                    })

        duplicates.sort(key=lambda d: d["semantic_similarity"], reverse=True)
        return duplicates

    def detect_semantic_overlap(self, overlap_threshold: float = 0.25) -> List[dict]:
        """Detect L3 theories with significant anchor overlap."""
        overlaps = []
        names = sorted(self.l3_theories.keys())

        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                ni, nj = names[i], names[j]
                anchors_i = set(self.l3_theories.get(ni, {}).get("anchors", []))
                anchors_j = set(self.l3_theories.get(nj, {}).get("anchors", []))
                union = len(anchors_i | anchors_j)
                intersection = len(anchors_i & anchors_j)
                if union > 0:
                    jaccard = intersection / union
                    if jaccard >= overlap_threshold:
                        overlaps.append({
                            "type": "semantic_overlap",
                            "theory_a": ni,
                            "theory_b": nj,
                            "anchor_jaccard": round(jaccard, 4),
                            "shared_anchors": intersection,
                            "suggested_action": "review_merge_or_split",
                            "priority": "high" if jaccard >= 0.4 else "medium",
                            "rationale": f"锚点Jaccard相似度{jaccard:.3f}，共{intersection}个共享锚点",
                        })

        overlaps.sort(key=lambda o: o["anchor_jaccard"], reverse=True)
        return overlaps

    def detect_dead_branches(self) -> List[dict]:
        """Detect dead branches: L2 themes with single anchor that don't contribute."""
        dead = []
        for l2_name, info in self.l2_themes.items():
            n_anchors = len(info["anchors"])
            n_l3s = len(info["l3s"])

            if n_anchors <= 1:
                severity = "critical" if n_anchors == 0 else "warning"
                dead.append({
                    "type": "dead_branch",
                    "l2_theme": l2_name,
                    "n_anchors": n_anchors,
                    "parent_l3s": info["l3s"],
                    "suggested_action": "merge_into_sibling" if n_anchors == 1 else "remove",
                    "priority": severity,
                    "rationale": f"L2主题'{l2_name}'仅有{n_anchors}个锚点支撑",
                })

        dead.sort(key=lambda d: d["n_anchors"])
        return dead

    def detect_sparse_categories(self, min_anchors: int = 2, min_l2s: int = 1) -> List[dict]:
        """Detect L3 theories that are too sparse."""
        sparse = []
        for l3_name, info in self.l3_theories.items():
            n_anchors = len(info["anchors"])
            n_l2s = len(info["l2s"])
            conf = self.confidence.get(l3_name, {}).get("confidence", 0)

            if n_anchors <= min_anchors or n_l2s <= min_l2s:
                severity = "critical" if n_anchors <= 1 else "warning"
                sparse.append({
                    "type": "sparse_category",
                    "l3_theory": l3_name,
                    "n_anchors": n_anchors,
                    "n_l2s": n_l2s,
                    "confidence": round(conf, 4),
                    "suggested_action": "merge_into_nearest",
                    "priority": severity,
                    "rationale": f"L3理论'{l3_name}'仅{n_anchors}个锚点、{n_l2s}个L2主题",
                })

        sparse.sort(key=lambda s: (s["n_anchors"], s["n_l2s"]))
        return sparse

    def detect_hierarchy_imbalance(self) -> List[dict]:
        """Detect theories that are over-merged or under-developed."""
        imbalances = []
        all_anchor_counts = [len(info["anchors"]) for info in self.l3_theories.values()]
        if not all_anchor_counts:
            return []

        mean_anchors = np.mean(all_anchor_counts)
        std_anchors = np.std(all_anchor_counts)

        for l3_name, info in self.l3_theories.items():
            n_anchors = len(info["anchors"])
            n_l2s = len(info["l2s"])
            conf = self.confidence.get(l3_name, {}).get("confidence", 0)

            # Over-merged: > mean + 2*std anchors but low confidence
            if n_anchors > mean_anchors + 2 * std_anchors:
                imbalances.append({
                    "type": "over_merged",
                    "l3_theory": l3_name,
                    "n_anchors": n_anchors,
                    "mean_anchors": round(mean_anchors, 1),
                    "std_anchors": round(std_anchors, 1),
                    "confidence": round(conf, 4),
                    "suggested_action": "split_candidate",
                    "priority": "high" if conf < 0.5 else "medium",
                    "rationale": f"锚点数{n_anchors}远超均值{mean_anchors:.0f}(+{std_anchors:.0f})",
                })

            # Under-developed: far below mean, high l2 diversity relative to anchors
            if n_anchors < max(mean_anchors - std_anchors, 3) and n_anchors <= 3:
                if n_l2s >= n_anchors:  # more L2s than anchors = spread too thin
                    imbalances.append({
                        "type": "under_developed",
                        "l3_theory": l3_name,
                        "n_anchors": n_anchors,
                        "n_l2s": n_l2s,
                        "confidence": round(conf, 4),
                        "suggested_action": "consolidate_or_merge",
                        "priority": "medium",
                        "rationale": f"锚点数{n_anchors}少于L2主题数{n_l2s}，结构分散",
                    })

        imbalances.sort(key=lambda x: x.get("n_anchors", 0))
        return imbalances

    def run_repair_engine(self) -> dict:
        """Run full repair engine and generate suggestions."""
        print("\n--- Ontology Repair Engine ---")

        duplicates = self.detect_duplicate_theories()
        print(f"  Duplicate theories: {len(duplicates)}")
        if duplicates:
            for d in duplicates[:5]:
                print(f"    [{d['priority']}] {d['theory_a']} ≈ {d['theory_b']} "
                      f"(sim={d['semantic_similarity']:.3f}) → {d['suggested_action']}")

        overlaps = self.detect_semantic_overlap()
        print(f"  Semantic overlaps: {len(overlaps)}")
        if overlaps:
            for o in overlaps[:5]:
                print(f"    [{o['priority']}] {o['theory_a']} ∩ {o['theory_b']} "
                      f"(jaccard={o['anchor_jaccard']:.3f}) → {o['suggested_action']}")

        dead = self.detect_dead_branches()
        print(f"  Dead branches: {len(dead)}")

        sparse = self.detect_sparse_categories()
        print(f"  Sparse categories: {len(sparse)}")

        imbalances = self.detect_hierarchy_imbalance()
        print(f"  Hierarchy imbalances: {len(imbalances)}")

        all_suggestions = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "duplicate_theories": len(duplicates),
                "semantic_overlaps": len(overlaps),
                "dead_branches": len(dead),
                "sparse_categories": len(sparse),
                "hierarchy_imbalances": len(imbalances),
                "total_issues": len(duplicates) + len(overlaps) + len(dead) +
                               len(sparse) + len(imbalances),
            },
            "duplicate_theories": duplicates,
            "semantic_overlaps": overlaps,
            "dead_branches": dead,
            "sparse_categories": sparse,
            "hierarchy_imbalances": imbalances,
        }

        self.repair_suggestions = all_suggestions
        return all_suggestions

    def save_repair_report(self):
        """Save repair suggestions to disk."""
        if not self.repair_suggestions:
            self.run_repair_engine()

        with open(REPAIR_REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(self.repair_suggestions, f, ensure_ascii=False, indent=2)
        logger.info("Repair report saved: %s", REPAIR_REPORT_PATH)

    # ═══════════════════════════════════════════════════════════════
    # SUBSYSTEM 2: Adaptive Compression
    # ═══════════════════════════════════════════════════════════════

    def compute_adaptive_thresholds(self) -> dict:
        """Compute adaptive compression thresholds based on current ontology state.

        Higher density → raise thresholds (merge less aggressively)
        Higher drift → lower thresholds (allow more merging to stabilize)
        Higher entropy → moderate thresholds
        """
        # 1. Ontology density
        total_anchors = len(self.anchor_map)
        total_l2 = len(self.l2_themes)
        total_l3 = len(self.l3_theories)

        l1_per_l2 = total_anchors / max(total_l2, 1)
        l2_per_l3 = total_l2 / max(total_l3, 1)
        density_score = (l1_per_l2 / 10 + l2_per_l3 / 5) / 2
        density_score = min(max(density_score, 0.5), 1.5)

        # 2. Semantic entropy (dispersion of L3 embedding distribution)
        entropy_score = 1.0
        if self.embeddings is not None and len(self.embeddings) > 1:
            centroid = np.mean(self.embeddings, axis=0)
            centroid_norm = centroid / (np.linalg.norm(centroid) + 1e-8)
            similarities = np.dot(self.embeddings, centroid_norm)
            # Higher avg similarity = lower entropy (more concentrated)
            avg_sim = float(np.mean(similarities))
            entropy_score = 1.0 - avg_sim  # convert to entropy-like scale
            entropy_score = min(max(entropy_score, 0.3), 1.5)

        # 3. Drift level
        drift_score = 1.0
        if self.drift:
            ds = self.drift.get("drift_summary", {})
            total = max(ds.get("total_theories", 1), 1)
            high_drift = ds.get("high_drift", 0)
            moderate_drift = ds.get("moderate_drift", 0)
            drift_ratio = (high_drift * 1.0 + moderate_drift * 0.5) / total
            drift_score = 1.0 - drift_ratio * 0.5  # 0.5 to 1.0 range

        # Compute adaptive thresholds
        l2_threshold = DEFAULT_L2_MERGE_SIMILARITY
        l3_threshold = DEFAULT_L3_CLUSTER_SIMILARITY

        # Density adjustment: denser → raise thresholds
        l2_threshold += (density_score - 1.0) * 0.08
        l3_threshold += (density_score - 1.0) * 0.06

        # Entropy adjustment: higher entropy → lower thresholds (allow more merging)
        l2_threshold -= (entropy_score - 0.5) * 0.05
        l3_threshold -= (entropy_score - 0.5) * 0.04

        # Drift adjustment: more drift → lower thresholds
        l2_threshold -= (1.0 - drift_score) * 0.10
        l3_threshold -= (1.0 - drift_score) * 0.08

        # Clamp
        l2_threshold = round(min(max(l2_threshold, 0.50), 0.75), 4)
        l3_threshold = round(min(max(l3_threshold, 0.45), 0.70), 4)

        config = {
            "timestamp": datetime.now().isoformat(),
            "current_state": {
                "total_anchors": total_anchors,
                "total_l2_themes": total_l2,
                "total_l3_theories": total_l3,
                "l1_per_l2": round(l1_per_l2, 2),
                "l2_per_l3": round(l2_per_l3, 2),
                "density_score": round(density_score, 4),
                "entropy_score": round(entropy_score, 4),
                "drift_score": round(drift_score, 4),
            },
            "adaptive_thresholds": {
                "l2_merge_similarity": l2_threshold,
                "l3_cluster_similarity": l3_threshold,
                "unmapped_fallback_similarity": round(l2_threshold - 0.12, 4),
                "l2_cross_merge_similarity": round(l2_threshold + 0.04, 4),
            },
            "recommendation": self._threshold_recommendation(density_score, entropy_score, drift_score),
        }

        self.compression_config = config
        logger.info("Adaptive thresholds: L2=%.4f, L3=%.4f (density=%.2f, entropy=%.2f, drift=%.2f)",
                     l2_threshold, l3_threshold, density_score, entropy_score, drift_score)
        return config

    @staticmethod
    def _threshold_recommendation(density: float, entropy: float, drift: float) -> str:
        if drift < 0.7:
            return "high_drift_detected — 建议降低阈值以允许更多合并，稳定网络结构"
        elif density > 1.3:
            return "high_density — 层级过于紧凑，建议提高阈值减少过度合并"
        elif entropy > 1.2:
            return "high_entropy — 理论分布分散，建议适度降低阈值"
        else:
            return "balanced — 当前参数合理，保持稳定"

    def save_compression_config(self):
        """Save adaptive compression config to disk."""
        if not self.compression_config:
            self.compute_adaptive_thresholds()

        os.makedirs(os.path.dirname(COMPRESSION_CONFIG_PATH), exist_ok=True)
        with open(COMPRESSION_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.compression_config, f, ensure_ascii=False, indent=2)
        logger.info("Adaptive compression config saved: %s", COMPRESSION_CONFIG_PATH)

    # ═══════════════════════════════════════════════════════════════
    # SUBSYSTEM 3: Governance Policy Engine
    # ═══════════════════════════════════════════════════════════════

    DEFAULT_POLICY = {
        "version": "1.0",
        "description": "语义治理策略 — Semantic Governance Rules",
        "rules": {
            "hierarchy": {
                "max_depth": 4,
                "min_anchors_per_l2": 2,
                "min_l2_per_l3": 1,
                "max_anchors_per_l3": 40,
                "max_l2_per_l3": 15,
            },
            "quality": {
                "min_grounding_score": 0.35,
                "min_confidence": 0.30,
                "max_semantic_overlap": 0.35,
                "min_provenance_density": 3.0,  # sentences per anchor
            },
            "network": {
                "min_degree": 1,
                "max_degree": 12,
                "min_avg_edge_weight": 0.10,
                "max_isolated_ratio": 0.10,
            },
            "stability": {
                "min_stability_score": 0.30,
                "max_drift_ratio": 0.15,
                "max_stale_ratio": 0.10,
            },
        },
    }

    def load_or_create_policy(self) -> dict:
        """Load existing policy or create default."""
        if os.path.exists(POLICY_PATH):
            with open(POLICY_PATH, "r", encoding="utf-8") as f:
                policy = json.load(f)
            logger.info("Loaded existing governance policy")
            return policy

        os.makedirs(os.path.dirname(POLICY_PATH), exist_ok=True)
        with open(POLICY_PATH, "w", encoding="utf-8") as f:
            json.dump(self.DEFAULT_POLICY, f, ensure_ascii=False, indent=2)
        logger.info("Created default governance policy")
        return self.DEFAULT_POLICY

    def validate_policy(self, policy: dict = None) -> dict:
        """Validate current ontology state against governance policy."""
        if policy is None:
            policy = self.load_or_create_policy()

        rules = policy.get("rules", {})
        violations = []

        # ── Hierarchy rules ──
        hr = rules.get("hierarchy", {})
        max_depth = hr.get("max_depth", 4)
        min_anchors_l2 = hr.get("min_anchors_per_l2", 2)
        max_anchors_l3 = hr.get("max_anchors_per_l3", 40)

        for l2_name, info in self.l2_themes.items():
            n = len(info["anchors"])
            if n < min_anchors_l2:
                violations.append({
                    "rule": "hierarchy.min_anchors_per_l2",
                    "target": l2_name,
                    "target_type": "l2_theme",
                    "value": n,
                    "threshold": min_anchors_l2,
                    "severity": "warning",
                    "message": f"L2主题'{l2_name}'仅有{n}个锚点(要求≥{min_anchors_l2})",
                })

        for l3_name, info in self.l3_theories.items():
            n = len(info["anchors"])
            if n > max_anchors_l3:
                violations.append({
                    "rule": "hierarchy.max_anchors_per_l3",
                    "target": l3_name,
                    "target_type": "l3_theory",
                    "value": n,
                    "threshold": max_anchors_l3,
                    "severity": "warning",
                    "message": f"L3理论'{l3_name}'有{n}个锚点(限制≤{max_anchors_l3})",
                })

        # ── Quality rules ──
        qr = rules.get("quality", {})
        min_grounding = qr.get("min_grounding_score", 0.35)
        min_conf = qr.get("min_confidence", 0.30)

        for node in self.nodes:
            name = node["id"]
            grounding = node.get("avg_grounding", 0)
            conf = self.confidence.get(name, {}).get("confidence", 0)

            if grounding < min_grounding:
                violations.append({
                    "rule": "quality.min_grounding_score",
                    "target": name,
                    "target_type": "l3_theory",
                    "value": round(grounding, 4),
                    "threshold": min_grounding,
                    "severity": "warning",
                    "message": f"理论'{name}'扎根度{grounding:.3f}低于阈值(≥{min_grounding})",
                })

            if conf < min_conf:
                violations.append({
                    "rule": "quality.min_confidence",
                    "target": name,
                    "target_type": "l3_theory",
                    "value": round(conf, 4),
                    "threshold": min_conf,
                    "severity": "critical",
                    "message": f"理论'{name}'置信度{conf:.3f}低于阈值(≥{min_conf})",
                })

        # ── Network rules ──
        nr = rules.get("network", {})
        min_deg = nr.get("min_degree", 1)
        max_deg = nr.get("max_degree", 12)
        min_avg_w = nr.get("min_avg_edge_weight", 0.10)

        node_degrees = defaultdict(int)
        node_weights = defaultdict(list)
        for e in self.edges:
            node_degrees[e["source"]] += 1
            node_degrees[e["target"]] += 1
            node_weights[e["source"]].append(e.get("weight", 0))
            node_weights[e["target"]].append(e.get("weight", 0))

        for node in self.nodes:
            name = node["id"]
            deg = node_degrees.get(name, 0)
            if deg < min_deg:
                violations.append({
                    "rule": "network.min_degree",
                    "target": name,
                    "target_type": "l3_theory",
                    "value": deg,
                    "threshold": min_deg,
                    "severity": "critical",
                    "message": f"理论'{name}'度为{deg}(要求≥{min_deg})，网络孤立",
                })

            if deg > max_deg:
                violations.append({
                    "rule": "network.max_degree",
                    "target": name,
                    "target_type": "l3_theory",
                    "value": deg,
                    "threshold": max_deg,
                    "severity": "warning",
                    "message": f"理论'{name}'度为{deg}(限制≤{max_deg})，可能为中心化枢纽",
                })

            avg_w = np.mean(node_weights.get(name, [0])) if node_weights.get(name) else 0
            if avg_w < min_avg_w and deg > 0:
                violations.append({
                    "rule": "network.min_avg_edge_weight",
                    "target": name,
                    "target_type": "l3_theory",
                    "value": round(avg_w, 4),
                    "threshold": min_avg_w,
                    "severity": "warning",
                    "message": f"理论'{name}'平均边权重{avg_w:.3f}低于阈值(≥{min_avg_w})",
                })

        # ── Stability rules ──
        sr = rules.get("stability", {})
        min_stab = sr.get("min_stability_score", 0.30)

        stab_scores = self.stability.get("scores", {})
        for name, s in stab_scores.items():
            if isinstance(s, dict):
                stab = s.get("stability", 1.0)
                if stab < min_stab:
                    violations.append({
                        "rule": "stability.min_stability_score",
                        "target": name,
                        "target_type": "l3_theory",
                        "value": round(stab, 4),
                        "threshold": min_stab,
                        "severity": "critical",
                        "message": f"理论'{name}'稳定性{stab:.3f}低于阈值(≥{min_stab})",
                    })

        # Sort by severity then target
        violations.sort(key=lambda v: (0 if v["severity"] == "critical" else 1, v["target"]))

        self.policy_violations = violations

        report = {
            "timestamp": datetime.now().isoformat(),
            "policy_version": policy.get("version", "1.0"),
            "summary": {
                "total_violations": len(violations),
                "critical": sum(1 for v in violations if v["severity"] == "critical"),
                "warning": sum(1 for v in violations if v["severity"] == "warning"),
            },
            "violations": violations,
        }

        logger.info("Policy validation: %d violations (%d critical, %d warning)",
                     len(violations),
                     sum(1 for v in violations if v["severity"] == "critical"),
                     sum(1 for v in violations if v["severity"] == "warning"))
        return report

    def save_policy_report(self, report: dict = None):
        """Save policy violation report to disk."""
        if report is None:
            report = self.validate_policy()

        with open(POLICY_REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info("Policy violation report saved: %s", POLICY_REPORT_PATH)

    # ── Full Pipeline ─────────────────────────────────────────────

    def run(self):
        """Run full ontology governance pipeline."""
        self.load_data()

        print("\n" + "=" * 60)
        print("PRIORITY 12: AUTONOMOUS ONTOLOGY GOVERNANCE")
        print("=" * 60)

        # 1. Repair engine
        print("\n[1/3] Ontology Repair Engine...")
        self.run_repair_engine()
        self.save_repair_report()

        # 2. Adaptive compression
        print("\n[2/3] Adaptive Compression...")
        config = self.compute_adaptive_thresholds()
        self.save_compression_config()
        at = config["adaptive_thresholds"]
        print(f"  L2 merge threshold: {at['l2_merge_similarity']:.4f}")
        print(f"  L3 cluster threshold: {at['l3_cluster_similarity']:.4f}")
        print(f"  Recommendation: {config['recommendation']}")

        # 3. Policy engine
        print("\n[3/3] Governance Policy Engine...")
        policy_report = self.validate_policy()
        self.save_policy_report(policy_report)
        ps = policy_report["summary"]
        print(f"  Violations: {ps['total_violations']} ({ps['critical']} critical, {ps['warning']} warning)")

        print(f"\n  Output: {REPAIR_REPORT_PATH}")
        print(f"  Output: {COMPRESSION_CONFIG_PATH}")
        print(f"  Output: {POLICY_PATH}")
        print(f"  Output: {POLICY_REPORT_PATH}")

        return {
            "repair_suggestions": self.repair_suggestions,
            "compression_config": config,
            "policy_report": policy_report,
        }


# ── CLI ──────────────────────────────────────────────────────────

def main():
    governor = OntologyGovernor()
    result = governor.run()

    suggestions = result["repair_suggestions"]
    s = suggestions.get("summary", {})
    violations = result["policy_report"]["summary"]

    print("\n" + "=" * 60)
    print("ONTOLOGY GOVERNANCE COMPLETE")
    print("=" * 60)
    print(f"  Issues found: {s.get('total_issues', 0)}")
    print(f"  Duplicates: {s.get('duplicate_theories', 0)}")
    print(f"  Overlaps: {s.get('semantic_overlaps', 0)}")
    print(f"  Dead branches: {s.get('dead_branches', 0)}")
    print(f"  Sparse: {s.get('sparse_categories', 0)}")
    print(f"  Imbalances: {s.get('hierarchy_imbalances', 0)}")
    print(f"  Policy violations: {violations['total_violations']} "
          f"({violations['critical']} critical)")


if __name__ == "__main__":
    main()
