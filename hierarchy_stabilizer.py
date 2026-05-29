"""Hierarchy Stabilizer — Priority 8: stabilize L1/L2/L3 semantic hierarchy.

Fixes fragmentation issues identified in the hierarchy audit:
  1. Single-anchor L2 themes → merge into nearest sibling
  2. Single-child L3 theories → cluster and merge into broader categories
  3. Cross-level name collisions → resolve (promote/demote/rename)
  4. Low-confidence mappings → re-resolve via semantic fallback

All merges are recorded with provenance for auditability.

Usage:
    D:\anaconda3\envs\zthree5\python.exe hierarchy_stabilizer.py
"""

import json
import logging
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("hierarchy_stabilizer")

# ── Config ──────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HIERARCHY_PATH = os.path.join(BASE_DIR, "data", "anchor_hierarchy.json")
PROVENANCE_PATH = os.path.join(BASE_DIR, "provenance_report.json")
OUTPUT_HIERARCHY = os.path.join(BASE_DIR, "data", "anchor_hierarchy_stabilized.json")
OUTPUT_HEALTH = os.path.join(BASE_DIR, "hierarchy_health.json")
MERGE_PROVENANCE_PATH = os.path.join(BASE_DIR, "hierarchy_merge_provenance.json")

# Similarity thresholds
L2_MERGE_SIMILARITY = 0.62    # Min cosine similarity to merge single-anchor L2 (within same L3)
L2_CROSS_MERGE_SIMILARITY = 0.66  # Higher bar for cross-parent L2 merges
L3_CLUSTER_SIMILARITY = 0.58  # Min similarity for L3 clustering
UNMAPPED_FALLBACK_SIMILARITY = 0.50  # Min similarity for unmapped anchor fallback


class HierarchyStabilizer:
    """Analyze and repair hierarchy fragmentation."""

    def __init__(self):
        self.model = None
        self.mappings = {}       # {anchor: {second_category, third_category, ...}}
        self.anchor_prov = {}    # {anchor: [records]}
        self.theme_prov = {}     # {theme: {supported_by, anchor_count}}
        self.theory_prov = {}    # {theory: {supported_by_themes, theme_count}}

        # Merge provenance records
        self.l2_merges = []      # Single-anchor L2 merges
        self.l3_merges = []      # Single-child L3 merges
        self.collision_fixes = []  # Cross-level collision resolutions
        self.re_mappings = []    # Low-confidence → confidence upgrades

    # ── Loading ──────────────────────────────────────────────────────

    def _load_model(self):
        """Lazy-load concept_anchor_v6 for semantic similarity."""
        if self.model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            v6_path = os.path.join(BASE_DIR, "trained_models", "concept_anchor_v6")
            if os.path.exists(v6_path):
                self.model = SentenceTransformer(v6_path)
                logger.info("Loaded concept_anchor_v6 for hierarchy stabilization")
            else:
                bge_path = os.path.join(BASE_DIR, "local_models", "bge-small-zh-v1.5")
                if os.path.exists(bge_path):
                    self.model = SentenceTransformer(bge_path)
                    logger.info("Loaded bge-small-zh-v1.5 (fallback)")
        except Exception as e:
            logger.warning("Model load failed: %s", e)

    def load_data(self):
        """Load hierarchy and provenance data."""
        with open(HIERARCHY_PATH, "r", encoding="utf-8") as f:
            ah = json.load(f)
        self.mappings = ah.get("mappings", {})
        self.hierarchy_stats = ah.get("stats", {})

        with open(PROVENANCE_PATH, "r", encoding="utf-8") as f:
            pr = json.load(f)
        self.anchor_prov = pr.get("anchor_provenance", {})
        self.theme_prov = pr.get("theme_provenance", {})
        self.theory_prov = pr.get("theory_provenance", {})

        logger.info("Loaded: %d anchors, %d themes, %d theories",
                     len(self.mappings), len(self.theme_prov), len(self.theory_prov))

    # ── Audit ────────────────────────────────────────────────────────

    def audit(self) -> dict:
        """Run full hierarchy audit. Returns structured issues report."""
        # Build reverse indices
        theme_to_anchors = defaultdict(set)
        theory_to_themes = defaultdict(set)
        theory_to_anchors = defaultdict(set)

        for anchor, m in self.mappings.items():
            l2 = m.get("second_category", "")
            l3 = m.get("third_category", "")
            if l2:
                theme_to_anchors[l2].add(anchor)
            if l3 and l2:
                theory_to_themes[l3].add(l2)
                theory_to_anchors[l3].add(anchor)

        # 1. Single-anchor L2 themes
        single_anchor_l2 = []
        for theme, anchors in sorted(theme_to_anchors.items()):
            if len(anchors) <= 1:
                # Find parent L3
                parent_l3s = [t for t, themes in theory_to_themes.items() if theme in themes]
                single_anchor_l2.append({
                    "theme": theme,
                    "anchor_count": len(anchors),
                    "anchors": list(anchors),
                    "parent_theories": parent_l3s,
                })

        # 2. Single-child L3 theories
        single_child_l3 = []
        for theory, themes in sorted(theory_to_themes.items()):
            if len(themes) <= 1:
                single_child_l3.append({
                    "theory": theory,
                    "theme_count": len(themes),
                    "themes": list(themes),
                    "total_anchors": len(theory_to_anchors.get(theory, set())),
                })

        # 3. Cross-level name collisions
        l2_names = set(theme_to_anchors.keys())
        l3_names = set(theory_to_themes.keys())
        l2_l3_collisions = sorted(l2_names & l3_names)

        # 4. Low-confidence mappings
        low_conf = []
        for anchor, m in self.mappings.items():
            conf = m.get("confidence", 0)
            if conf < 0.3:
                low_conf.append({
                    "anchor": anchor,
                    "confidence": conf,
                    "source": m.get("source", ""),
                    "l2": m.get("second_category", ""),
                    "l3": m.get("third_category", ""),
                })
        low_conf.sort(key=lambda x: x["confidence"])

        # 5. Unmapped anchors (in provenance but not in hierarchy)
        mapped_set = set(self.mappings.keys())
        prov_set = set(self.anchor_prov.keys())
        unmapped = sorted(prov_set - mapped_set)

        report = {
            "timestamp": datetime.now().isoformat(),
            "totals": {
                "anchors": len(self.mappings),
                "themes": len(l2_names),
                "theories": len(l3_names),
                "prov_anchors": len(prov_set),
            },
            "single_anchor_l2": {
                "count": len(single_anchor_l2),
                "ratio": round(len(single_anchor_l2) / max(len(l2_names), 1), 3),
                "items": single_anchor_l2,
            },
            "single_child_l3": {
                "count": len(single_child_l3),
                "ratio": round(len(single_child_l3) / max(len(l3_names), 1), 3),
                "items": single_child_l3,
            },
            "cross_level_collisions": {
                "count": len(l2_l3_collisions),
                "items": l2_l3_collisions,
            },
            "low_confidence_mappings": {
                "count": len(low_conf),
                "items": low_conf,
            },
            "unmapped_anchors": {
                "count": len(unmapped),
                "items": unmapped,
            },
            "distribution": {
                "anchors_per_theme": self._percentiles(
                    [len(v) for v in theme_to_anchors.values()]),
                "themes_per_theory": self._percentiles(
                    [len(v) for v in theory_to_themes.values()]),
            },
        }

        # Calculate health score (weighted by severity, normalized to 0-100)
        # Penalize fragmentation: each single-node item costs points proportional to ratio
        single_l2_penalty = (len(single_anchor_l2) / max(len(l2_names), 1)) * 40
        single_l3_penalty = (len(single_child_l3) / max(len(l3_names), 1)) * 35
        collision_penalty = min(len(l2_l3_collisions) * 2, 15)
        low_conf_penalty = min((len(low_conf) / max(len(self.mappings), 1)) * 20, 10)
        health = max(0, round(100 - single_l2_penalty - single_l3_penalty - collision_penalty - low_conf_penalty, 1))
        report["health_score"] = health

        return report

    @staticmethod
    def _percentiles(values: List[int]) -> dict:
        sv = sorted(values)
        n = len(sv)
        if n == 0:
            return {}
        return {
            "min": sv[0], "p25": sv[n // 4], "median": sv[n // 2],
            "p75": sv[3 * n // 4], "max": sv[-1],
            "mean": round(sum(sv) / n, 1),
        }

    # ── Repair: Single-anchor L2 merge ───────────────────────────────

    def repair_single_anchor_l2(self, audit_report: dict, dry_run: bool = False) -> dict:
        """Merge single-anchor L2 themes into most similar sibling."""
        self._load_model()
        if self.model is None:
            logger.warning("No model available for L2 merge — skipping")
            return {"merged": 0, "skipped": len(audit_report["single_anchor_l2"]["items"])}

        import numpy as np

        # Build theme → parent L3 map
        theme_to_l3 = defaultdict(list)
        for theory, tdata in self.theory_prov.items():
            for theme in tdata.get("supported_by_themes", []):
                theme_to_l3[theme].append(theory)

        # Build anchor counts per theme
        theme_anchor_counts = {}
        for tname, tdata in self.theme_prov.items():
            theme_anchor_counts[tname] = tdata.get("anchor_count", 0)

        single_items = audit_report["single_anchor_l2"]["items"]
        merged_count = 0
        merge_records = []

        for item in single_items:
            theme_name = item["theme"]
            parent_l3s = item["parent_theories"]
            anchors_to_move = item["anchors"]

            if not anchors_to_move:
                continue

            # Find siblings: other L2s under same L3 parent
            siblings = []
            for l3 in parent_l3s:
                for sib in self.theory_prov.get(l3, {}).get("supported_by_themes", []):
                    if sib != theme_name and theme_anchor_counts.get(sib, 0) >= 1:
                        siblings.append((sib, l3))

            if not siblings:
                # Cross-parent fallback: search all L2 themes for best match
                all_l2_names = list(theme_anchor_counts.keys())
                if len(all_l2_names) <= 1:
                    continue
                cross_candidates = [n for n in all_l2_names
                                   if n != theme_name and theme_anchor_counts.get(n, 0) >= 1]
                if not cross_candidates:
                    continue
                all_names = [theme_name] + cross_candidates
                embs = self.model.encode(
                    all_names, normalize_embeddings=True, show_progress_bar=False)
                query_emb = embs[0]
                best_sim = -1
                best_sib = None
                best_l3 = None
                for j in range(1, len(all_names)):
                    sim = float(np.dot(query_emb, embs[j]))
                    if sim > best_sim:
                        best_sim = sim
                        best_sib = cross_candidates[j - 1]
                        # Find parent L3 of cross-candidate
                        best_l3 = theme_to_l3.get(best_sib, [None])[0]
                if best_sim < L2_CROSS_MERGE_SIMILARITY:
                    continue
                merge_type = "cross_parent"
            else:
                # Find best sibling via embedding similarity
                candidate_names = [theme_name] + [s[0] for s in siblings]
                embs = self.model.encode(
                    candidate_names, normalize_embeddings=True, show_progress_bar=False)
                query_emb = embs[0]

                best_sim = -1
                best_sib = None
                best_l3 = None
                for j in range(1, len(candidate_names)):
                    sim = float(np.dot(query_emb, embs[j]))
                    if sim > best_sim:
                        best_sim = sim
                        best_sib = siblings[j - 1][0]
                        best_l3 = siblings[j - 1][1]

                if best_sim < L2_MERGE_SIMILARITY:
                    continue  # Not similar enough
                merge_type = "same_parent"

            if not dry_run:
                # Update mappings: reassign anchors from old L2 to best sibling L2
                for anchor in anchors_to_move:
                    if anchor in self.mappings:
                        self.mappings[anchor]["second_category"] = best_sib

            merge_records.append({
                "merged_theme": theme_name,
                "into_theme": best_sib,
                "parent_theory": best_l3,
                "similarity": round(best_sim, 4),
                "anchors_moved": anchors_to_move,
                "n_anchors": len(anchors_to_move),
                "type": merge_type,
            })
            merged_count += 1
            logger.info("  L2 merge: '%s' → '%s' (sim=%.3f, %d anchors)",
                        theme_name, best_sib, best_sim, len(anchors_to_move))

        self.l2_merges = merge_records
        return {"merged": merged_count, "records": merge_records,
                "skipped": len(single_items) - merged_count}

    # ── Repair: Single-child L3 merge ────────────────────────────────

    def repair_single_child_l3(self, audit_report: dict, dry_run: bool = False) -> dict:
        """Cluster and merge single-child L3 theories into broader categories."""
        self._load_model()
        if self.model is None:
            logger.warning("No model available for L3 clustering — skipping")
            return {"merged": 0, "skipped": len(audit_report["single_child_l3"]["items"])}

        import numpy as np

        single_items = audit_report["single_child_l3"]["items"]
        if len(single_items) <= 1:
            return {"merged": 0, "records": [], "skipped": len(single_items)}

        # Get names and their embeddings
        names = [item["theory"] for item in single_items]
        embs = self.model.encode(
            names, normalize_embeddings=True, show_progress_bar=False).astype(np.float32)

        # Greedy clustering
        clusters = []
        assigned = set()
        for i in range(len(names)):
            if i in assigned:
                continue
            cluster = [i]
            assigned.add(i)
            for j in range(i + 1, len(names)):
                if j in assigned:
                    continue
                sim = float(np.dot(embs[i], embs[j]))
                if sim >= L3_CLUSTER_SIMILARITY:
                    cluster.append(j)
                    assigned.add(j)
            clusters.append(cluster)

        merge_records = []
        merged_count = 0

        for cluster in clusters:
            if len(cluster) <= 1:
                continue

            cluster_names = [names[i] for i in cluster]
            # Canonical name: shortest (most concise)
            canonical = min(cluster_names, key=lambda n: (len(n), n))

            if dry_run:
                merge_records.append({
                    "canonical": canonical,
                    "members": cluster_names,
                    "size": len(cluster),
                })
                merged_count += len(cluster) - 1
                continue

            # Reassign: all mappings pointing to merged L3s now point to canonical
            for member in cluster_names:
                if member == canonical:
                    continue
                for anchor, m in self.mappings.items():
                    if m.get("third_category") == member:
                        m["third_category"] = canonical

            merge_records.append({
                "canonical": canonical,
                "members": [n for n in cluster_names if n != canonical],
                "size": len(cluster),
                "similarities": {
                    m: round(float(np.dot(embs[names.index(canonical)],
                                         embs[names.index(m)])), 4)
                    for m in cluster_names if m != canonical
                },
            })
            merged_count += len(cluster) - 1
            logger.info("  L3 merge: %d theories → '%s'",
                        len(cluster), canonical)

        self.l3_merges = merge_records
        return {"merged": merged_count, "records": merge_records,
                "clusters": len([c for c in clusters if len(c) > 1]),
                "skipped": len(single_items) - merged_count}

    # ── Repair: Cross-level collisions ───────────────────────────────

    def repair_cross_level_collisions(self, audit_report: dict, dry_run: bool = False) -> dict:
        """Resolve L2-L3 name collisions."""
        collisions = audit_report["cross_level_collisions"]["items"]
        fixes = []

        # Build updated theme/theory sets (accounting for prior merges)
        for colliding_name in collisions:
            # How many anchors under this L2 name?
            l2_anchors = set()
            for anchor, m in self.mappings.items():
                if m.get("second_category") == colliding_name:
                    l2_anchors.add(anchor)

            # How many themes under this L3 name?
            l3_themes = set()
            for anchor, m in self.mappings.items():
                if m.get("third_category") == colliding_name:
                    l3_themes.add(m.get("second_category", ""))

            l2_count = len(l2_anchors)
            l3_count = len(l3_themes)

            if l3_count >= 2 and l2_count >= 2:
                # Both have substantial support — rename the L2
                new_l2_name = colliding_name + "(主题)"
                if not dry_run:
                    for anchor in l2_anchors:
                        self.mappings[anchor]["second_category"] = new_l2_name
                fixes.append({
                    "collision": colliding_name,
                    "action": "rename_l2",
                    "new_name": new_l2_name,
                    "reason": f"both levels well-supported (L2:{l2_count} anchors, L3:{l3_count} themes)",
                })
            elif l3_count <= 1 and l2_count >= 1:
                # L3 is fragile — merge L3 into its single child's peers
                # (handled by L3 merge separately, but rename L2 to avoid confusion)
                new_l2_name = colliding_name + "(主题)"
                if not dry_run:
                    for anchor in l2_anchors:
                        self.mappings[anchor]["second_category"] = new_l2_name
                fixes.append({
                    "collision": colliding_name,
                    "action": "rename_l2_to_disambiguate",
                    "new_name": new_l2_name,
                    "reason": f"L3 fragile ({l3_count} themes), disambiguated L2",
                })
            elif l2_count <= 1:
                # L2 is fragile — merge into nearest sibling (handled by L2 merge)
                fixes.append({
                    "collision": colliding_name,
                    "action": "defer_to_l2_merge",
                    "reason": f"L2 fragile ({l2_count} anchors), will be merged by L2 repair",
                })
            else:
                fixes.append({
                    "collision": colliding_name,
                    "action": "keep",
                    "reason": "acceptable overlap",
                })

            logger.info("  Collision '%s': %s", colliding_name, fixes[-1]["action"])

        self.collision_fixes = fixes
        return {"resolved": len(fixes), "fixes": fixes}

    # ── Repair: Low-confidence → semantic fallback ──────────────────

    def repair_low_confidence(self, audit_report: dict, dry_run: bool = False) -> dict:
        """Re-resolve low-confidence mappings via embedding fallback to nearest high-conf anchor."""
        self._load_model()
        if self.model is None:
            return {"upgraded": 0}

        import numpy as np

        low_conf_items = audit_report["low_confidence_mappings"]["items"]
        # Only target those with confidence < 0.2 (truly broken)
        broken = [item for item in low_conf_items if item["confidence"] < 0.2]

        if not broken:
            return {"upgraded": 0}

        # Build reference set: high-confidence mappings
        high_conf_anchors = []
        high_conf_l2 = []
        high_conf_l3 = []
        for anchor, m in self.mappings.items():
            if m.get("confidence", 0) >= 0.3:
                high_conf_anchors.append(anchor)
                high_conf_l2.append(m.get("second_category", ""))
                high_conf_l3.append(m.get("third_category", ""))

        if not high_conf_anchors:
            return {"upgraded": 0}

        ref_embs = self.model.encode(
            high_conf_anchors, normalize_embeddings=True, show_progress_bar=False)

        upgraded = 0
        upgrades = []
        for item in broken:
            anchor = item["anchor"]
            try:
                query_emb = self.model.encode(
                    [anchor], normalize_embeddings=True, show_progress_bar=False)[0]
                sims = np.dot(ref_embs, query_emb)
                best_idx = int(np.argmax(sims))
                best_sim = float(sims[best_idx])

                if best_sim >= UNMAPPED_FALLBACK_SIMILARITY and not dry_run:
                    self.mappings[anchor] = {
                        "second_category": high_conf_l2[best_idx],
                        "third_category": high_conf_l3[best_idx],
                        "source": "stabilized_fallback",
                        "confidence": round(best_sim, 4),
                        "nearest_anchor": high_conf_anchors[best_idx],
                        "nearest_similarity": round(best_sim, 4),
                    }
                    upgraded += 1
                    upgrades.append({
                        "anchor": anchor,
                        "old_confidence": item["confidence"],
                        "new_confidence": round(best_sim, 4),
                        "new_l2": high_conf_l2[best_idx],
                        "new_l3": high_conf_l3[best_idx],
                        "nearest_anchor": high_conf_anchors[best_idx],
                    })
            except Exception:
                pass

        logger.info("  Upgraded %d low-confidence mappings via semantic fallback", upgraded)
        self.re_mappings = upgrades
        return {"upgraded": upgraded, "records": upgrades}

    # ── Full pipeline ────────────────────────────────────────────────

    def stabilize(self, dry_run: bool = False) -> dict:
        """Run full hierarchy stabilization pipeline.

        Order matters: L2 merge first (clean up single-anchor themes),
        then L3 merge (cluster single-child theories),
        then collision resolution, finally low-confidence upgrade.
        """
        self.load_data()
        audit_before = self.audit()
        logger.info("Pre-stabilization health: %.1f/100", audit_before["health_score"])
        logger.info("Issues: %d single-anchor L2, %d single-child L3, %d collisions, %d low-conf",
                     audit_before["single_anchor_l2"]["count"],
                     audit_before["single_child_l3"]["count"],
                     audit_before["cross_level_collisions"]["count"],
                     audit_before["low_confidence_mappings"]["count"])

        results = {}

        # Step 1: Merge single-anchor L2s
        logger.info("Step 1: Merging single-anchor L2 themes...")
        results["l2_merge"] = self.repair_single_anchor_l2(audit_before, dry_run)

        # Step 2: Cluster single-child L3s
        logger.info("Step 2: Clustering single-child L3 theories...")
        results["l3_merge"] = self.repair_single_child_l3(audit_before, dry_run)

        # Step 3: Resolve cross-level collisions
        logger.info("Step 3: Resolving cross-level collisions...")
        results["collisions"] = self.repair_cross_level_collisions(audit_before, dry_run)

        # Step 4: Upgrade low-confidence mappings
        logger.info("Step 4: Re-resolving low-confidence mappings...")
        results["re_mappings"] = self.repair_low_confidence(audit_before, dry_run)

        # Re-audit
        if not dry_run:
            audit_after = self.audit()
            logger.info("Post-stabilization health: %.1f/100", audit_after["health_score"])
        else:
            audit_after = audit_before

        # Build merge provenance
        merge_provenance = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "l2_merges": self.l2_merges,
            "l3_merges": self.l3_merges,
            "collision_fixes": self.collision_fixes,
            "re_mappings": self.re_mappings,
            "summary": {
                "l2_merged": results["l2_merge"].get("merged", 0),
                "l3_merged": results["l3_merge"].get("merged", 0),
                "collisions_resolved": results["collisions"].get("resolved", 0),
                "mappings_upgraded": results["re_mappings"].get("upgraded", 0),
            },
        }

        return {
            "audit_before": audit_before,
            "audit_after": audit_after,
            "results": results,
            "merge_provenance": merge_provenance,
        }

    # ── Output ──────────────────────────────────────────────────────

    def save(self, report: dict):
        """Save stabilized hierarchy and health report."""
        # 1. Updated hierarchy
        new_hierarchy = {
            "version": "2.0-stabilized",
            "created_at": datetime.now().isoformat(),
            "parent_version": "1.0",
            "description": "Stabilized anchor hierarchy — single-anchor L2s merged, "
                          "single-child L3s clustered, collisions resolved",
            "stats": self._compute_new_stats(),
            "mappings": self.mappings,
        }

        os.makedirs(os.path.dirname(OUTPUT_HIERARCHY), exist_ok=True)
        with open(OUTPUT_HIERARCHY, "w", encoding="utf-8") as f:
            json.dump(new_hierarchy, f, ensure_ascii=False, indent=2)
        logger.info("Stabilized hierarchy saved: %s", OUTPUT_HIERARCHY)

        # 2. Health report
        health = {
            "timestamp": datetime.now().isoformat(),
            "before": report["audit_before"],
            "after": report["audit_after"],
            "changes": report["merge_provenance"]["summary"],
        }
        with open(OUTPUT_HEALTH, "w", encoding="utf-8") as f:
            json.dump(health, f, ensure_ascii=False, indent=2)
        logger.info("Health report saved: %s", OUTPUT_HEALTH)

        # 3. Merge provenance
        with open(MERGE_PROVENANCE_PATH, "w", encoding="utf-8") as f:
            json.dump(report["merge_provenance"], f, ensure_ascii=False, indent=2)
        logger.info("Merge provenance saved: %s", MERGE_PROVENANCE_PATH)

    def _compute_new_stats(self) -> dict:
        """Compute stats for the stabilized hierarchy."""
        l2_set = set()
        l3_set = set()
        l2_counts = defaultdict(int)
        l3_counts = defaultdict(int)
        sources = defaultdict(int)

        for anchor, m in self.mappings.items():
            l2 = m.get("second_category", "")
            l3 = m.get("third_category", "")
            src = m.get("source", "unknown")
            if l2:
                l2_set.add(l2)
                l2_counts[l2] += 1
            if l3:
                l3_set.add(l3)
                l3_counts[l3] += 1
            sources[src] += 1

        return {
            "total_anchors": len(self.mappings),
            "total_l2_themes": len(l2_set),
            "total_l3_theories": len(l3_set),
            "l2_reduction": f"{len(self.theme_prov)} → {len(l2_set)}",
            "l3_reduction": f"{len(self.theory_prov)} → {len(l3_set)}",
            "avg_anchors_per_l2": round(len(self.mappings) / max(len(l2_set), 1), 1),
            "avg_l2_per_l3": round(len(l2_set) / max(len(l3_set), 1), 1),
            "mapping_sources": dict(sources),
        }


# ── CLI ────────────────────────────────────────────────────────────────

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Hierarchy Stabilizer — Priority 8")
    ap.add_argument("--dry-run", action="store_true",
                    help="Audit only, no writes")
    ap.add_argument("--audit-only", action="store_true",
                    help="Run audit only, print report")
    args = ap.parse_args()

    stabilizer = HierarchyStabilizer()

    if args.audit_only:
        stabilizer.load_data()
        audit = stabilizer.audit()
        print(json.dumps(audit, ensure_ascii=False, indent=2))
        return

    report = stabilizer.stabilize(dry_run=args.dry_run)

    if not args.dry_run:
        stabilizer.save(report)

    # Print summary
    summary = report["merge_provenance"]["summary"]
    print("\n" + "=" * 60)
    print("HIERARCHY STABILIZATION COMPLETE")
    print("=" * 60)
    print(f"  Health before: {report['audit_before']['health_score']:.1f}")
    print(f"  Health after:  {report['audit_after']['health_score']:.1f}")
    print(f"  L2 themes merged:   {summary['l2_merged']}")
    print(f"  L3 theories merged: {summary['l3_merged']}")
    print(f"  Collisions fixed:   {summary['collisions_resolved']}")
    print(f"  Mappings upgraded:  {summary['mappings_upgraded']}")
    print(f"  Output: {OUTPUT_HIERARCHY}")
    print(f"  Output: {OUTPUT_HEALTH}")


if __name__ == "__main__":
    main()
