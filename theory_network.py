"""Theory Network Constructor — Priority 9: build L3 theory graph with edges and confidence.

Constructs a weighted directed graph over L3 theories where edges represent:
  1. Semantic similarity (concept_anchor_v6 cosine)
  2. Shared L2 themes (theories that share supporting categories)
  3. Shared L1 anchors (theories that draw from same concept anchors)
  4. Provenance overlap (theories grounded in similar source sentences)

Each theory gets a confidence score:
  grounding × support_diversity × semantic_stability × provenance_depth

Outputs:
  - theory_network.json: nodes + edges
  - theory_confidence.json: per-theory confidence breakdown
  - network_health.json: overall network health metrics

Usage:
    D:\anaconda3\envs\zthree5\python.exe theory_network.py
"""

import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("theory_network")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HIERARCHY_PATH = os.path.join(BASE_DIR, "data", "anchor_hierarchy_stabilized.json")
PROVENANCE_PATH = os.path.join(BASE_DIR, "provenance_report.json")
OUTPUT_NETWORK = os.path.join(BASE_DIR, "theory_network.json")
OUTPUT_CONFIDENCE = os.path.join(BASE_DIR, "theory_confidence.json")
OUTPUT_HEALTH = os.path.join(BASE_DIR, "network_health.json")

# Edge thresholds
SEMANTIC_EDGE_THRESHOLD = 0.30   # Min cosine sim for semantic edge
SHARED_L2_MIN = 0                 # Min shared L2 themes for structural edge
SHARED_L1_MIN = 0                 # Min shared L1 anchors for grounding edge
MAX_EDGES_PER_NODE = 10           # Keep top-K strongest edges per node


class TheoryNetworkBuilder:
    """Construct and analyze the L3 theory network."""

    def __init__(self):
        self.model = None
        self.mappings = {}
        self.anchor_prov = {}
        self.theme_prov = {}
        self.theory_prov = {}

        # Derived structures
        self.l3_names = []
        self.l3_to_l2s = defaultdict(set)
        self.l3_to_l1s = defaultdict(set)
        self.l3_embeddings = None

        # Output
        self.nodes = []
        self.edges = []
        self.confidence_scores = {}

    def _load_model(self):
        if self.model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            v6_path = os.path.join(BASE_DIR, "trained_models", "concept_anchor_v6")
            if os.path.exists(v6_path):
                self.model = SentenceTransformer(v6_path)
                logger.info("Loaded concept_anchor_v6 for theory network")
            else:
                bge_path = os.path.join(BASE_DIR, "local_models", "bge-small-zh-v1.5")
                if os.path.exists(bge_path):
                    self.model = SentenceTransformer(bge_path)
        except Exception as e:
            logger.warning("Model load failed: %s", e)

    def load_data(self):
        """Load stabilized hierarchy and provenance."""
        with open(HIERARCHY_PATH, "r", encoding="utf-8") as f:
            ah = json.load(f)
        self.mappings = ah.get("mappings", {})

        with open(PROVENANCE_PATH, "r", encoding="utf-8") as f:
            pr = json.load(f)
        self.anchor_prov = pr.get("anchor_provenance", {})
        self.theme_prov = pr.get("theme_provenance", {})
        self.theory_prov = pr.get("theory_provenance", {})

        # Build L3→L2 and L3→L1 indices
        for anchor, m in self.mappings.items():
            l2 = m.get("second_category", "")
            l3 = m.get("third_category", "")
            if l3 and l2:
                self.l3_to_l2s[l3].add(l2)
            if l3:
                self.l3_to_l1s[l3].add(anchor)

        self.l3_names = sorted(self.l3_to_l2s.keys())
        logger.info("Loaded: %d L3 theories, %d anchors, %d L2 themes",
                     len(self.l3_names), len(self.mappings),
                     len(set(m.get("second_category", "") for m in self.mappings.values())))

    # ── Node construction ──────────────────────────────────────────

    def build_nodes(self):
        """Construct theory nodes with metadata."""
        self.nodes = []
        for l3_name in self.l3_names:
            l2s = self.l3_to_l2s.get(l3_name, set())
            l1s = self.l3_to_l1s.get(l3_name, set())

            # Compute grounding stats for all anchors under this theory
            grounding_scores = []
            for anchor in l1s:
                records = self.anchor_prov.get(anchor, [])
                for r in records:
                    gs = r.get("grounding_score", 0)
                    if gs and gs > 0:
                        grounding_scores.append(gs)

            avg_grounding = (sum(grounding_scores) / max(len(grounding_scores), 1)
                           if grounding_scores else 0)

            # Provenance depth: how many sentences support this theory
            total_sentences = sum(
                len(self.anchor_prov.get(a, [])) for a in l1s)

            node = {
                "id": l3_name,
                "name": l3_name,
                "l2_count": len(l2s),
                "l1_count": len(l1s),
                "sentence_count": total_sentences,
                "avg_grounding": round(avg_grounding, 4),
                "support_l2": sorted(l2s),
            }
            self.nodes.append(node)

        logger.info("Built %d theory nodes", len(self.nodes))

    # ── Edge construction ──────────────────────────────────────────

    def build_edges(self):
        """Construct weighted edges between theories."""
        self._load_model()
        if self.model is None or len(self.l3_names) <= 1:
            self.edges = []
            return

        import numpy as np

        # Encode all L3 names
        self.l3_embeddings = self.model.encode(
            self.l3_names, normalize_embeddings=True, show_progress_bar=False
        ).astype(np.float32)

        n = len(self.l3_names)
        all_edges = []

        for i in range(n):
            for j in range(i + 1, n):
                l3_i = self.l3_names[i]
                l3_j = self.l3_names[j]

                # 1. Semantic similarity
                sem_sim = float(np.dot(self.l3_embeddings[i], self.l3_embeddings[j]))

                # 2. Shared L2 themes (Jaccard)
                l2_i = self.l3_to_l2s.get(l3_i, set())
                l2_j = self.l3_to_l2s.get(l3_j, set())
                l2_union = len(l2_i | l2_j)
                l2_shared = len(l2_i & l2_j)
                l2_jaccard = l2_shared / max(l2_union, 1)

                # 3. Shared L1 anchors (Jaccard)
                l1_i = self.l3_to_l1s.get(l3_i, set())
                l1_j = self.l3_to_l1s.get(l3_j, set())
                l1_union = len(l1_i | l1_j)
                l1_shared = len(l1_i & l1_j)
                l1_jaccard = l1_shared / max(l1_union, 1)

                # Composite edge weight (weighted combination)
                weight = (sem_sim * 0.50 + l2_jaccard * 0.25 +
                         l1_jaccard * 0.15 + min(l2_shared, 3) / 3 * 0.10)

                # Filter: need at least some semantic OR structural connection
                if sem_sim < SEMANTIC_EDGE_THRESHOLD and l2_shared <= SHARED_L2_MIN and l1_shared < SHARED_L1_MIN:
                    continue

                all_edges.append({
                    "source": l3_i,
                    "target": l3_j,
                    "weight": round(weight, 4),
                    "semantic_similarity": round(sem_sim, 4),
                    "shared_l2_count": l2_shared,
                    "shared_l1_count": l1_shared,
                    "l2_jaccard": round(l2_jaccard, 4),
                    "l1_jaccard": round(l1_jaccard, 4),
                    "edge_type": self._classify_edge(sem_sim, l2_shared, l1_shared),
                })

        # Sort by weight and keep top-K per node
        node_edge_count = defaultdict(int)
        all_edges.sort(key=lambda e: e["weight"], reverse=True)

        self.edges = []
        for edge in all_edges:
            src, tgt = edge["source"], edge["target"]
            if node_edge_count[src] < MAX_EDGES_PER_NODE and node_edge_count[tgt] < MAX_EDGES_PER_NODE:
                self.edges.append(edge)
                node_edge_count[src] += 1
                node_edge_count[tgt] += 1

        logger.info("Built %d edges between %d theories", len(self.edges), n)

    @staticmethod
    def _classify_edge(sem_sim: float, shared_l2: int, shared_l1: int) -> str:
        if shared_l2 >= 2 and shared_l1 >= 3:
            return "strong_structural"
        elif sem_sim >= 0.50:
            return "semantic"
        elif shared_l2 >= 1:
            return "structural"
        elif shared_l1 >= 1:
            return "grounding"
        else:
            return "weak_semantic"

    # ── Confidence scoring ─────────────────────────────────────────

    def compute_confidence(self):
        """Compute confidence score for each theory.

        confidence = grounding × support_diversity × semantic_stability × provenance_depth
        Each component normalized to [0, 1].
        """
        if not self.nodes:
            self.build_nodes()

        # Collect raw values for normalization
        all_grounding = []
        all_l2_diversity = []
        all_l1_diversity = []
        all_sentences = []
        node_lookup = {n["id"]: n for n in self.nodes}

        for node in self.nodes:
            all_grounding.append(node["avg_grounding"])
            # Support diversity: how many distinct L2 categories per L1 anchor
            l2_count = max(node["l2_count"], 1)
            l1_count = max(node["l1_count"], 1)
            all_l2_diversity.append(l2_count / max(l1_count, 1))
            all_l1_diversity.append(l1_count)
            all_sentences.append(max(node["sentence_count"], 1))

        max_grounding = max(all_grounding) if all_grounding else 1
        max_l2_div = max(all_l2_diversity) if all_l2_diversity else 1
        max_l1_div = max(all_l1_diversity) if all_l1_diversity else 1
        max_sentences = max(all_sentences) if all_sentences else 1

        # Build edge lookup for stability score
        edge_degree = defaultdict(int)
        edge_weight_sum = defaultdict(float)
        for edge in self.edges:
            edge_degree[edge["source"]] += 1
            edge_degree[edge["target"]] += 1
            edge_weight_sum[edge["source"]] += edge["weight"]
            edge_weight_sum[edge["target"]] += edge["weight"]

        self.confidence_scores = {}
        for node in self.nodes:
            name = node["id"]
            l2_count = max(node["l2_count"], 1)
            l1_count = max(node["l1_count"], 1)

            # 1. Grounding component
            grounding = node["avg_grounding"] / max(max_grounding, 0.01)

            # 2. Support diversity: how rich is the L2 structure
            l2_diversity = min(l2_count / 5, 1.0)  # 5+ L2 categories = full marks
            l1_to_l2_ratio = l2_count / max(l1_count, 1)
            support_diversity = (l2_diversity * 0.6 + min(l1_to_l2_ratio, 1.0) * 0.4)

            # 3. Semantic stability: how well-connected in the network
            degree = edge_degree.get(name, 0)
            avg_edge_weight = (edge_weight_sum.get(name, 0) / max(degree, 1))
            stability = min(degree / 5, 1.0) * 0.5 + min(avg_edge_weight, 1.0) * 0.5

            # 4. Provenance depth: how much source evidence
            provenance = min(node["sentence_count"] / 50, 1.0)  # 50+ sentences = full marks

            # Composite confidence
            confidence = round(
                grounding * 0.35 +
                support_diversity * 0.25 +
                stability * 0.20 +
                provenance * 0.20, 4)

            self.confidence_scores[name] = {
                "confidence": confidence,
                "components": {
                    "grounding": round(grounding, 4),
                    "support_diversity": round(support_diversity, 4),
                    "semantic_stability": round(stability, 4),
                    "provenance_depth": round(provenance, 4),
                },
                "raw_metrics": {
                    "avg_grounding": node["avg_grounding"],
                    "l2_count": l2_count,
                    "l1_count": l1_count,
                    "sentence_count": node["sentence_count"],
                    "network_degree": degree,
                    "avg_edge_weight": round(avg_edge_weight, 4),
                },
            }

        logger.info("Computed confidence for %d theories", len(self.confidence_scores))

    # ── Network health ─────────────────────────────────────────────

    def compute_health(self) -> dict:
        """Compute overall network health metrics."""
        if not self.edges:
            return {"error": "no edges computed"}

        n_nodes = len(self.nodes)
        n_edges = len(self.edges)

        # Degree distribution
        degrees = defaultdict(int)
        for e in self.edges:
            degrees[e["source"]] += 1
            degrees[e["target"]] += 1

        deg_values = list(degrees.values())
        isolated = sum(1 for n in self.nodes if degrees.get(n["id"], 0) == 0)

        # Edge type distribution
        edge_types = defaultdict(int)
        for e in self.edges:
            edge_types[e["edge_type"]] += 1

        # Weight distribution
        weights = [e["weight"] for e in self.edges]
        avg_weight = sum(weights) / max(len(weights), 1)

        # Confidence distribution
        conf_values = [c["confidence"] for c in self.confidence_scores.values()]
        avg_conf = sum(conf_values) / max(len(conf_values), 1)

        # Weak nodes: low confidence + low degree
        weak_nodes = []
        for node in self.nodes:
            name = node["id"]
            conf = self.confidence_scores.get(name, {}).get("confidence", 0)
            deg = degrees.get(name, 0)
            if conf < 0.3 or (deg == 0 and conf < 0.5):
                weak_nodes.append({
                    "theory": name,
                    "confidence": round(conf, 4),
                    "degree": deg,
                    "l1_count": node["l1_count"],
                    "avg_grounding": node["avg_grounding"],
                })

        # Orphan nodes (no edges)
        orphans = [n["id"] for n in self.nodes if degrees.get(n["id"], 0) == 0]

        # Compute overall health score
        connectivity_score = max(0, 1 - isolated / max(n_nodes, 1)) * 40
        weight_score = min(avg_weight * 50, 25)
        confidence_score = min(avg_conf * 35, 25)
        orphan_penalty = min(len(orphans) / max(n_nodes, 1) * 30, 15)

        health = round(connectivity_score + weight_score + confidence_score - orphan_penalty, 1)

        return {
            "timestamp": datetime.now().isoformat(),
            "health_score": health,
            "topology": {
                "total_nodes": n_nodes,
                "total_edges": n_edges,
                "density": round(n_edges / max(n_nodes * (n_nodes - 1) / 2, 1), 5),
                "isolated_nodes": isolated,
                "orphan_ratio": round(isolated / max(n_nodes, 1), 3),
                "avg_degree": round(sum(deg_values) / max(len(deg_values), 1), 1),
                "max_degree": max(deg_values) if deg_values else 0,
            },
            "edge_quality": {
                "avg_weight": round(avg_weight, 4),
                "max_weight": max(weights) if weights else 0,
                "type_distribution": dict(edge_types),
            },
            "confidence": {
                "avg_confidence": round(avg_conf, 4),
                "max_confidence": max(conf_values) if conf_values else 0,
                "weak_nodes_count": len(weak_nodes),
                "weak_nodes": weak_nodes[:20],
            },
            "orphan_theories": orphans[:30],
            "interpretation": self._interpret_health(health),
        }

    @staticmethod
    def _interpret_health(score: float) -> str:
        if score >= 75:
            return "excellent — theory network is well-connected and confident"
        elif score >= 60:
            return "good — network is functional, some isolated nodes"
        elif score >= 45:
            return "moderate — significant fragmentation, needs attention"
        elif score >= 30:
            return "poor — high fragmentation, weak confidence"
        else:
            return "critical — network structure is severely degraded"

    # ── Full pipeline ──────────────────────────────────────────────

    def build(self) -> dict:
        """Run full theory network construction pipeline."""
        self.load_data()
        self.build_nodes()
        self.build_edges()
        self.compute_confidence()
        health = self.compute_health()

        return {
            "network": {
                "nodes": self.nodes,
                "edges": self.edges,
            },
            "confidence": self.confidence_scores,
            "health": health,
        }

    def save(self, result: dict):
        """Save all outputs."""
        # 1. Theory network (nodes + edges)
        network_data = {
            "metadata": {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "total_nodes": len(result["network"]["nodes"]),
                "total_edges": len(result["network"]["edges"]),
            },
            "nodes": result["network"]["nodes"],
            "edges": result["network"]["edges"],
        }
        with open(OUTPUT_NETWORK, "w", encoding="utf-8") as f:
            json.dump(network_data, f, ensure_ascii=False, indent=2)
        logger.info("Theory network saved: %s", OUTPUT_NETWORK)

        # 2. Theory confidence
        confidence_data = {
            "metadata": {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
            },
            "scores": result["confidence"],
        }
        with open(OUTPUT_CONFIDENCE, "w", encoding="utf-8") as f:
            json.dump(confidence_data, f, ensure_ascii=False, indent=2)
        logger.info("Theory confidence saved: %s", OUTPUT_CONFIDENCE)

        # 3. Network health
        with open(OUTPUT_HEALTH, "w", encoding="utf-8") as f:
            json.dump(result["health"], f, ensure_ascii=False, indent=2)
        logger.info("Network health saved: %s", OUTPUT_HEALTH)


# ── CLI ────────────────────────────────────────────────────────────────

def main():
    builder = TheoryNetworkBuilder()
    result = builder.build()
    builder.save(result)

    h = result["health"]
    print("\n" + "=" * 60)
    print("THEORY NETWORK CONSTRUCTION COMPLETE")
    print("=" * 60)
    print(f"  Nodes:  {h['topology']['total_nodes']}")
    print(f"  Edges:  {h['topology']['total_edges']}")
    print(f"  Density: {h['topology']['density']}")
    print(f"  Isolated: {h['topology']['isolated_nodes']}")
    print(f"  Avg degree: {h['topology']['avg_degree']}")
    print(f"  Avg confidence: {h['confidence']['avg_confidence']}")
    print(f"  Weak nodes: {h['confidence']['weak_nodes_count']}")
    print(f"  Network health: {h['health_score']}/100 — {h['interpretation']}")
    print(f"  Output: {OUTPUT_NETWORK}")
    print(f"  Output: {OUTPUT_CONFIDENCE}")
    print(f"  Output: {OUTPUT_HEALTH}")


if __name__ == "__main__":
    main()
