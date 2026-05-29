"""Theory Graph Intelligence — Priority 14.

Three subsystems:
  1. Cross-Theory Relation Typing — infer relation types between theory pairs
  2. Community Detection — Louvain-like modularity clustering
  3. Semantic Centrality — core/bridge/isolated classification

Usage:
    D:\anaconda3\envs\zthree5\python.exe graph_intelligence.py
"""

import json
import logging
import os
import sys
from collections import Counter, defaultdict, deque
from datetime import datetime
from typing import Dict, List, Tuple, Set, Optional

import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("graph_intelligence")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Inputs
NETWORK_PATH = os.path.join(BASE_DIR, "theory_network.json")
CONFIDENCE_PATH = os.path.join(BASE_DIR, "theory_confidence.json")
HIERARCHY_PATH = os.path.join(BASE_DIR, "data", "anchor_hierarchy_stabilized.json")
STABILITY_PATH = os.path.join(BASE_DIR, "theory_stability.json")

# Outputs
RELATIONS_PATH = os.path.join(BASE_DIR, "theory_relations.json")
COMMUNITIES_PATH = os.path.join(BASE_DIR, "theory_communities.json")
CENTRALITY_PATH = os.path.join(BASE_DIR, "theory_centrality.json")


class GraphIntelligence:
    """Priority 14: Theory Graph Intelligence."""

    def __init__(self):
        self.model = None
        self.nodes = []
        self.edges = []
        self.confidence = {}
        self.hierarchy = {}
        self.stability = {}

        # Derived
        self.node_ids = []
        self.node_index = {}
        self.adjacency = defaultdict(set)
        self.edge_lookup = {}  # (src, tgt) → edge_data
        self.embedding = None

        # Results
        self.relations = {}
        self.communities = {}
        self.centrality = {}

    def load_data(self):
        with open(NETWORK_PATH, "r", encoding="utf-8") as f:
            nd = json.load(f)
            self.nodes = nd.get("nodes", [])
            self.edges = nd.get("edges", [])

        with open(CONFIDENCE_PATH, "r", encoding="utf-8") as f:
            self.confidence = json.load(f).get("scores", {})

        with open(HIERARCHY_PATH, "r", encoding="utf-8") as f:
            self.hierarchy = json.load(f)

        if os.path.exists(STABILITY_PATH):
            with open(STABILITY_PATH, "r", encoding="utf-8") as f:
                self.stability = json.load(f).get("scores", {})

        # Build indices
        self.node_ids = [n["id"] for n in self.nodes]
        self.node_index = {n["id"]: n for n in self.nodes}

        for e in self.edges:
            s, t = e["source"], e["target"]
            self.adjacency[s].add(t)
            self.adjacency[t].add(s)
            key = tuple(sorted([s, t]))
            self.edge_lookup[key] = e

        logger.info("Loaded: %d nodes, %d edges", len(self.nodes), len(self.edges))

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
                logger.info("Loaded embedding model for graph intelligence")
        except Exception as e:
            logger.warning("Model load failed: %s", e)

    # ═══════════════════════════════════════════════════════════════
    # 1. Cross-Theory Relation Typing
    # ═══════════════════════════════════════════════════════════════

    def infer_relations(self) -> dict:
        """Infer relation types for connected theory pairs.

        Relation types:
          - support: strong semantic similarity + shared themes
          - dependency: one theory's anchors heavily overlap another's L2 themes
          - tension: connected but semantically very different
          - evolution: moderate similarity + shared parent in hierarchy
          - weak_association: low-weight connections
        """
        self._load_model()

        # Compute embeddings for all theories
        embeddings = None
        if self.model:
            embeddings = self.model.encode(
                self.node_ids, normalize_embeddings=True, show_progress_bar=False
            ).astype(np.float32)
        self.embeddings = embeddings

        # Build hierarchy index for shared parent detection
        mappings = self.hierarchy.get("mappings", {})
        anchor_to_l2l3 = {}
        for anchor, m in mappings.items():
            anchor_to_l2l3[anchor] = (m.get("second_category", ""), m.get("third_category", ""))

        # Collect L2 themes per L3 theory
        l3_to_l2s = defaultdict(set)
        l3_to_l1s = defaultdict(set)
        for anchor, (l2, l3) in anchor_to_l2l3.items():
            if l3:
                l3_to_l2s[l3].add(l2)
                l3_to_l1s[l3].add(anchor)

        relations = {}
        for edge in self.edges:
            s, t = edge["source"], edge["target"]
            pair_key = f"{s}|||{t}"
            sim = edge.get("semantic_similarity", 0)
            weight = edge.get("weight", 0)
            shared_l2 = edge.get("shared_l2_count", 0)
            shared_l1 = edge.get("shared_l1_count", 0)

            # Determine relation type
            l2s_s = l3_to_l2s.get(s, set())
            l2s_t = l3_to_l2s.get(t, set())
            l1s_s = l3_to_l1s.get(s, set())
            l1s_t = l3_to_l1s.get(t, set())

            l2_overlap = len(l2s_s & l2s_t)
            l1_overlap = len(l1s_s & l1s_t)

            if sim >= 0.55 and l2_overlap >= 2:
                rel_type = "support"
                confidence = 0.7 + sim * 0.3
            elif l2_overlap >= 3 or (l1_overlap >= 5 and sim >= 0.35):
                rel_type = "dependency"
                confidence = 0.6 + l2_overlap * 0.1
            elif sim < 0.20 and weight > 0.15:
                rel_type = "tension"
                confidence = 0.6
            elif l2_overlap >= 1 and sim >= 0.35:
                rel_type = "evolution"
                confidence = 0.5 + sim * 0.3
            else:
                rel_type = "weak_association"
                confidence = weight

            # Determine direction (if applicable)
            direction = "undirected"
            if rel_type == "dependency":
                # direction: from smaller to larger (larger supports smaller)
                if len(l1s_s) < len(l1s_t):
                    direction = "s_to_t"
                elif len(l1s_t) < len(l1s_s):
                    direction = "t_to_s"

            relations[pair_key] = {
                "source": s,
                "target": t,
                "relation_type": rel_type,
                "direction": direction,
                "confidence": round(min(confidence, 1.0), 4),
                "evidence": {
                    "semantic_similarity": round(sim, 4),
                    "shared_l2_count": l2_overlap,
                    "shared_l1_count": l1_overlap,
                    "edge_weight": round(weight, 4),
                },
            }

        # Summary
        type_counts = Counter(r["relation_type"] for r in relations.values())
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_relations": len(relations),
            "type_distribution": dict(type_counts),
        }

        self.relations = {"summary": summary, "relations": relations}

        logger.info("Relations typed: %s", dict(type_counts))
        return self.relations

    # ═══════════════════════════════════════════════════════════════
    # 2. Community Detection (Louvain-like modularity optimization)
    # ═══════════════════════════════════════════════════════════════

    def detect_communities(self, max_iterations: int = 20) -> dict:
        """Detect theory communities using modularity optimization.

        Each community represents a cluster of densely connected theories.
        """
        if not self.edges:
            return {"communities": {}, "summary": {"n_communities": 0}}

        n = len(self.node_ids)
        node_to_idx = {nid: i for i, nid in enumerate(self.node_ids)}
        idx_to_node = {i: nid for i, nid in enumerate(self.node_ids)}

        # Build adjacency matrix and degree vector
        adj = defaultdict(lambda: defaultdict(float))
        degrees = defaultdict(float)
        total_weight = 0.0

        for e in self.edges:
            s, t = e["source"], e["target"]
            w = e.get("weight", 0.1)
            si, ti = node_to_idx[s], node_to_idx[t]
            adj[si][ti] = w
            adj[ti][si] = w
            degrees[si] += w
            degrees[ti] += w
            total_weight += w * 2  # undirected, each edge counted twice in degrees

        if total_weight == 0:
            total_weight = 1.0

        # Initialize: each node in its own community
        communities = {i: i for i in range(n)}
        comm_nodes = defaultdict(set)
        for i in range(n):
            comm_nodes[i].add(i)

        # Compute community weights
        comm_degree = defaultdict(float)
        for i in range(n):
            comm_degree[i] = degrees[i]

        # Modularity optimization
        for iteration in range(max_iterations):
            moved = 0
            nodes_order = list(range(n))
            np.random.shuffle(nodes_order)

            for node in nodes_order:
                old_comm = communities[node]
                comm_nodes[old_comm].discard(node)
                if not comm_nodes[old_comm]:
                    del comm_nodes[old_comm]

                # Compute modularity gain for moving to each neighbor's community
                best_comm = old_comm
                best_gain = 0.0
                neighbor_comms = set()

                for nb in adj[node]:
                    neighbor_comms.add(communities[nb])

                for new_comm in neighbor_comms:
                    if new_comm == old_comm:
                        continue

                    # Modularity gain ≈ sum of weights to new_comm - degree*comm_degree/total_weight
                    w_to_comm = sum(adj[node].get(nb, 0) for nb in comm_nodes.get(new_comm, set()))
                    gain = w_to_comm - (degrees[node] * comm_degree.get(new_comm, 0)) / total_weight

                    if gain > best_gain:
                        best_gain = gain
                        best_comm = new_comm

                # Move node
                communities[node] = best_comm
                comm_nodes[best_comm].add(node)
                comm_degree[old_comm] -= degrees[node]
                comm_degree[best_comm] += degrees[node]

                if best_comm != old_comm:
                    moved += 1

            if moved == 0:
                break

        # Merge communities with single node into nearest community
        singleton_comms = [c for c, nodes in comm_nodes.items() if len(nodes) == 1]
        for sc in singleton_comms:
            if sc not in comm_nodes:
                continue
            node = next(iter(comm_nodes[sc]))
            best_comm = None
            best_w = 0
            for nb in adj[node]:
                nb_comm = communities[nb]
                if nb_comm != sc:
                    w = adj[node].get(nb, 0)
                    if w > best_w:
                        best_w = w
                        best_comm = nb_comm
            if best_comm is not None:
                communities[node] = best_comm
                comm_nodes[best_comm].add(node)
                del comm_nodes[sc]

        # Build output
        comm_results = defaultdict(list)
        for i in range(n):
            comm_results[communities[i]].append(idx_to_node[i])

        # Name communities by their central theory
        named_communities = {}
        for comm_id, members in comm_results.items():
            # Find best theory as community name
            best_member = max(members, key=lambda m: self.confidence.get(m, {}).get("confidence", 0))
            avg_conf = np.mean([self.confidence.get(m, {}).get("confidence", 0) for m in members])

            named_communities[f"community_{comm_id}"] = {
                "label": best_member,
                "size": len(members),
                "avg_confidence": round(float(avg_conf), 4),
                "members": sorted(members),
            }

        # Summary
        sizes = [c["size"] for c in named_communities.values()]
        summary = {
            "timestamp": datetime.now().isoformat(),
            "n_communities": len(named_communities),
            "avg_size": round(np.mean(sizes), 1) if sizes else 0,
            "max_size": max(sizes) if sizes else 0,
            "min_size": min(sizes) if sizes else 0,
            "modularity_quality": "high" if len(named_communities) >= 5 else "moderate",
        }

        self.communities = {"summary": summary, "communities": named_communities}

        logger.info("Communities detected: %d communities, avg size %.1f",
                     len(named_communities), summary["avg_size"])
        return self.communities

    # ═══════════════════════════════════════════════════════════════
    # 3. Semantic Centrality Analysis
    # ═══════════════════════════════════════════════════════════════

    def compute_centrality(self) -> dict:
        """Compute centrality metrics and classify theories.

        Categories: core, bridge, peripheral, isolated
        """
        n = len(self.node_ids)
        node_to_idx = {nid: i for i, nid in enumerate(self.node_ids)}

        if n == 0:
            return {}

        # Build adjacency matrix
        adj_matrix = np.zeros((n, n), dtype=np.float32)
        for e in self.edges:
            s, t = e["source"], e["target"]
            w = e.get("weight", 0.1)
            si, ti = node_to_idx[s], node_to_idx[t]
            adj_matrix[si, ti] = w
            adj_matrix[ti, si] = w

        # 1. Degree centrality
        degrees = adj_matrix.sum(axis=1)
        max_deg = float(degrees.max()) if degrees.max() > 0 else 1.0

        # 2. Eigenvector centrality (power iteration)
        eigenvector = np.ones(n, dtype=np.float64)
        for _ in range(50):
            prev = eigenvector.copy()
            eigenvector = adj_matrix.dot(eigenvector)
            norm = np.linalg.norm(eigenvector)
            if norm > 0:
                eigenvector /= norm
            if np.linalg.norm(eigenvector - prev) < 1e-6:
                break
        eigenvector = eigenvector / max(eigenvector.max(), 0.01)

        # 3. Betweenness centrality (approximate via shortest paths)
        betweenness = np.zeros(n)
        for src in range(n):
            if degrees[src] == 0:
                continue
            # BFS from src
            dist = np.full(n, -1, dtype=np.int32)
            dist[src] = 0
            n_paths = np.zeros(n)
            n_paths[src] = 1
            queue = deque([src])
            pred = defaultdict(list)

            while queue:
                v = queue.popleft()
                for nb in range(n):
                    if adj_matrix[v, nb] <= 0:
                        continue
                    if dist[nb] < 0:
                        dist[nb] = dist[v] + 1
                        queue.append(nb)
                    if dist[nb] == dist[v] + 1:
                        n_paths[nb] += n_paths[v]
                        pred[nb].append(v)

            # Backpropagate dependencies
            dependency = np.zeros(n)
            order = sorted(range(n), key=lambda x: dist[x], reverse=True)
            for v in order:
                if dist[v] <= 0:
                    continue
                for p in pred[v]:
                    if n_paths[v] > 0:
                        dependency[p] += (n_paths[p] / n_paths[v]) * (1 + dependency[v])
            betweenness += dependency

        betweenness = betweenness / max(betweenness.max(), 1.0)

        # Classify
        centrality_scores = {}
        for i, nid in enumerate(self.node_ids):
            deg_norm = float(degrees[i] / max_deg)
            ev = float(eigenvector[i])
            bw = float(betweenness[i])
            conf = self.confidence.get(nid, {}).get("confidence", 0.5)

            # Composite centrality
            composite = deg_norm * 0.30 + ev * 0.40 + bw * 0.30

            # Classify
            if degrees[i] == 0:
                role = "isolated"
            elif ev >= 0.6 and deg_norm >= 0.5:
                role = "core"
            elif bw >= 0.5 and ev >= 0.3:
                role = "bridge"
            elif deg_norm >= 0.3:
                role = "peripheral"
            else:
                role = "marginal"

            centrality_scores[nid] = {
                "theory": nid,
                "role": role,
                "degree_centrality": round(deg_norm, 4),
                "eigenvector_centrality": round(ev, 4),
                "betweenness_centrality": round(bw, 4),
                "composite_centrality": round(composite, 4),
                "confidence": round(conf, 4),
                "degree": int(degrees[i]),
            }

        # Summary
        role_counts = Counter(c["role"] for c in centrality_scores.values())
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_theories": n,
            "role_distribution": dict(role_counts),
            "avg_degree_centrality": round(float(np.mean([c["degree_centrality"] for c in centrality_scores.values()])), 4),
            "avg_eigenvector": round(float(np.mean([c["eigenvector_centrality"] for c in centrality_scores.values()])), 4),
            "avg_betweenness": round(float(np.mean([c["betweenness_centrality"] for c in centrality_scores.values()])), 4),
        }

        self.centrality = {"summary": summary, "scores": centrality_scores}

        logger.info("Centrality: %s", dict(role_counts))
        return self.centrality

    # ── Saving ────────────────────────────────────────────────────

    def save_all(self):
        if self.relations:
            with open(RELATIONS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.relations, f, ensure_ascii=False, indent=2)
            logger.info("Relations saved: %s", RELATIONS_PATH)

        if self.communities:
            with open(COMMUNITIES_PATH, "w", encoding="utf-8") as f:
                json.dump(self.communities, f, ensure_ascii=False, indent=2)
            logger.info("Communities saved: %s", COMMUNITIES_PATH)

        if self.centrality:
            with open(CENTRALITY_PATH, "w", encoding="utf-8") as f:
                json.dump(self.centrality, f, ensure_ascii=False, indent=2)
            logger.info("Centrality saved: %s", CENTRALITY_PATH)

    # ── Full Pipeline ─────────────────────────────────────────────

    def run(self):
        self.load_data()

        print("\n" + "=" * 60)
        print("PRIORITY 14: THEORY GRAPH INTELLIGENCE")
        print("=" * 60)

        print("\n[1/3] Cross-Theory Relation Typing...")
        relations = self.infer_relations()
        rs = relations["summary"]
        print(f"  Total relations: {rs['total_relations']}")
        print(f"  Types: {rs['type_distribution']}")

        print("\n[2/3] Community Detection...")
        communities = self.detect_communities()
        cs = communities["summary"]
        print(f"  Communities: {cs['n_communities']}")
        print(f"  Avg size: {cs['avg_size']}, Max: {cs['max_size']}, Min: {cs['min_size']}")

        # Show community labels
        for cname, cdata in sorted(communities["communities"].items(),
                                    key=lambda x: x[1]["size"], reverse=True)[:5]:
            print(f"    {cdata['label']}: {cdata['size']} members")

        print("\n[3/3] Semantic Centrality...")
        centrality = self.compute_centrality()
        ctr = centrality["summary"]
        print(f"  Roles: {ctr['role_distribution']}")
        print(f"  Avg degree centrality: {ctr['avg_degree_centrality']:.4f}")
        print(f"  Avg eigenvector: {ctr['avg_eigenvector']:.4f}")
        print(f"  Avg betweenness: {ctr['avg_betweenness']:.4f}")

        self.save_all()

        print(f"\n  Output: {RELATIONS_PATH}")
        print(f"  Output: {COMMUNITIES_PATH}")
        print(f"  Output: {CENTRALITY_PATH}")

        return {"relations": relations, "communities": communities, "centrality": centrality}


# ── CLI ──────────────────────────────────────────────────────────

def main():
    gi = GraphIntelligence()
    result = gi.run()

    print("\n" + "=" * 60)
    print("GRAPH INTELLIGENCE COMPLETE")
    print("=" * 60)

    c = result["centrality"]["scores"]
    core = [n for n, d in c.items() if d["role"] == "core"]
    bridge = [n for n, d in c.items() if d["role"] == "bridge"]
    isolated = [n for n, d in c.items() if d["role"] == "isolated"]

    print(f"\n  Core theories: {len(core)}")
    if core:
        for name in core[:5]:
            print(f"    ★ {name}")

    print(f"\n  Bridge theories: {len(bridge)}")
    if bridge:
        for name in bridge[:5]:
            print(f"    -> {name}")

    if isolated:
        print(f"\n  Isolated: {len(isolated)} — {', '.join(isolated[:5])}")


if __name__ == "__main__":
    main()
