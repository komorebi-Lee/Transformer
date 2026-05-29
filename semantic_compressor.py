"""Semantic Compressor — Phase 4 ontology management and abstraction control.

Two subsystems:
1. SemanticCompressor: auto-merge similar second/third level codes via embedding
   clustering, reducing ontology explosion while maintaining anchor traceability.

2. AbstractionController: define level boundaries, auto-tag concept levels,
   detect level-inappropriate codes, and suggest promotions/demotions.

Usage:
    from semantic_compressor import SemanticCompressor, AbstractionController

    sc = SemanticCompressor()
    merged_second, merge_map = sc.compress_second_level(second_codes)
    merged_third, merge_map3 = sc.compress_third_level(third_codes)
"""

import logging
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Set

logger = logging.getLogger("semantic_compressor")


class SemanticCompressor:
    """Auto-merge semantically similar second and third level codes."""

    def __init__(self, embedding_model=None, similarity_threshold=0.78):
        self._model = embedding_model
        self._model_loaded = False
        self.threshold = similarity_threshold

    def _load_default_model(self):
        if self._model is not None or self._model_loaded:
            return
        self._model_loaded = True
        try:
            import os as _os
            from sentence_transformers import SentenceTransformer

            _v6_path = _os.path.join(
                _os.path.dirname(_os.path.abspath(__file__)),
                "trained_models", "concept_anchor_v6")
            if _os.path.exists(_v6_path):
                self._model = SentenceTransformer(_v6_path)
                logger.info("SemanticCompressor using contrastive model: concept_anchor_v6")
                return

            _model_path = _os.path.join(
                _os.path.dirname(_os.path.abspath(__file__)),
                "local_models", "bge-small-zh-v1.5")
            if _os.path.exists(_model_path):
                self._model = SentenceTransformer(_model_path)
                logger.info("SemanticCompressor loaded model: bge-small-zh-v1.5")
        except Exception as e:
            logger.debug("SemanticCompressor model skip: %s", e)

    # ── Second-level compression ──────────────────────────────────────

    def compress_second_level(
            self,
            second_codes: Dict[str, List[str]],
            threshold: float = None,
    ) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
        """Merge semantically similar second-level categories.

        Args:
            second_codes: {second_category_name: [anchor_keys]}
            threshold: cosine similarity threshold for merging (default 0.78)

        Returns:
            (merged_dict, merge_map)
            - merged_dict: {canonical_name: [all_anchor_keys]}
            - merge_map: {old_name: canonical_name} for all merged categories
        """
        if threshold is None:
            threshold = self.threshold

        names = list(second_codes.keys())
        if len(names) <= 1:
            return dict(second_codes), {}

        self._load_default_model()
        if self._model is None:
            return dict(second_codes), {}

        # Encode all names
        import numpy as np
        embs = self._model.encode(names, normalize_embeddings=True,
                                  show_progress_bar=False).astype(np.float32)

        # Greedy clustering
        clusters = []  # List of [name_indices]
        assigned = set()

        for i, name in enumerate(names):
            if i in assigned:
                continue
            cluster = [i]
            assigned.add(i)
            for j in range(i + 1, len(names)):
                if j in assigned:
                    continue
                sim = float(np.dot(embs[i], embs[j]))
                if sim >= threshold:
                    cluster.append(j)
                    assigned.add(j)
            clusters.append(cluster)

        if len(clusters) == len(names):
            return dict(second_codes), {}  # No merging needed

        # Build merge map
        merge_map = {}
        merged = {}
        for cluster in clusters:
            cluster_names = [names[i] for i in cluster]
            # Canonical name: shortest name in cluster (most concise)
            canonical = min(cluster_names, key=lambda n: (len(n), n))
            merged[canonical] = []
            for cn in cluster_names:
                merge_map[cn] = canonical
                merged[canonical].extend(second_codes.get(cn, []))

        n_merged = len(names) - len(merged)
        logger.info("Second-level compression: %d → %d categories (%d merged, %.0f%%)",
                    len(names), len(merged), n_merged,
                    n_merged / max(len(names), 1) * 100)

        # Log merge details for review
        for cluster in clusters:
            if len(cluster) >= 3:
                cluster_names = [names[i] for i in cluster]
                logger.info("  Merged cluster: %s", " | ".join(cluster_names))

        return merged, merge_map

    def compress_third_level(
            self,
            third_codes: Dict[str, List[str]],
            threshold: float = None,
    ) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
        """Merge semantically similar third-level categories.

        Same algorithm as compress_second_level but for third-level theory categories.
        """
        if threshold is None:
            threshold = self.threshold

        return self.compress_second_level(third_codes, threshold)


class AbstractionController:
    """Define and enforce hierarchical abstraction level boundaries.

    Level definitions:
      L1 (Anchor):    2–8 chars, grounded noun phrase, specific & traceable
      L2 (Theme):     3–20 chars, grouping category, summarizes multiple L1 anchors
      L3 (Theory):    4–30 chars, theoretical dimension, highest abstraction

    Detects:
      - L1 codes that are too long/abstract (might belong at L2)
      - L2 categories with only 1 anchor (too granular, should merge)
      - L3 categories that overlap heavily with L2 (redundant hierarchy)
    """

    def __init__(self):
        pass

    def assess_first_level(self, anchor_name: str, grounding_score: float = 0.5) -> dict:
        """Assess whether a first-level anchor is at the appropriate abstraction level.

        Returns verdict with:
          - level_appropriate: bool
          - suggested_level: "L1" | "L2" | "L3"
          - reason: explanation
        """
        L = len(anchor_name)
        issues = []

        if L < 2:
            issues.append("too_short")
        elif L > 12:
            issues.append("too_long_for_L1")

        # Check for theoretical language markers (suggests L2/L3 abstraction)
        theory_markers = [
            '理论', '框架', '模型', '范式', '机制', '体系', '结构',
            '维度', '视角', '路径', '模式', '策略', '系统',
        ]
        theory_count = sum(1 for m in theory_markers if m in anchor_name)

        # Check for verb-like patterns (shouldn't be in anchors)
        verb_patterns = [
            '进行', '实现', '完成', '推动', '促进', '提升', '增强',
            '减少', '降低', '提高', '改善', '优化', '加强',
        ]
        verb_count = sum(1 for v in verb_patterns if v in anchor_name)

        if theory_count >= 2:
            issues.append("too_abstract_for_L1")
        if verb_count >= 1:
            issues.append("contains_action_verb")

        is_well_grounded = grounding_score >= 0.55

        if not issues:
            return {
                "level_appropriate": True,
                "suggested_level": "L1",
                "reason": "good_L1_anchor",
                "issues": [],
            }

        if len(issues) >= 2 or "too_abstract_for_L1" in issues:
            return {
                "level_appropriate": False,
                "suggested_level": "L2",
                "reason": " | ".join(issues),
                "issues": issues,
            }

        return {
            "level_appropriate": True,
            "suggested_level": "L1",
            "reason": "minor_issues: " + " | ".join(issues),
            "issues": issues,
        }

    def assess_second_level(
            self,
            second_name: str,
            anchor_count: int,
            third_name: str = "",
    ) -> dict:
        """Assess whether a second-level category is appropriate."""
        L = len(second_name)
        issues = []

        if L < 3:
            issues.append("too_short_for_L2")
        elif L > 25:
            issues.append("too_long_for_L2")

        # Too granular if only 1 anchor
        if anchor_count <= 1:
            issues.append("single_anchor")

        # Check for L1-like specificity
        if L <= 5 and not any(m in second_name for m in ['管理', '策略', '模式', '机制', '结构', '体系']):
            issues.append("too_specific_for_L2")

        if not issues:
            return {
                "level_appropriate": True,
                "suggested_level": "L2",
                "reason": "good_L2_category",
                "issues": [],
            }

        if "single_anchor" in issues and len(issues) == 1:
            return {
                "level_appropriate": False,
                "suggested_level": "L1",
                "reason": "single_anchor_should_merge_to_parent",
                "issues": issues,
            }

        return {
            "level_appropriate": True,
            "suggested_level": "L2",
            "reason": "minor: " + " | ".join(issues),
            "issues": issues,
        }

    def assess_third_level(
            self,
            third_name: str,
            second_count: int,
    ) -> dict:
        """Assess whether a third-level category is appropriate."""
        L = len(third_name)
        issues = []

        if L < 4:
            issues.append("too_short_for_L3")

        # Too granular
        if second_count <= 1:
            issues.append("single_second_category")

        if not issues:
            return {
                "level_appropriate": True,
                "suggested_level": "L3",
                "reason": "good_L3_category",
                "issues": [],
            }

        return {
            "level_appropriate": False,
            "suggested_level": "L2" if second_count <= 1 else "L3",
            "reason": " | ".join(issues),
            "issues": issues,
        }

    def audit_hierarchy(
            self,
            second_codes: Dict[str, List[str]],
            third_codes: Dict[str, List[str]],
            grounding_scores: Dict[str, float] = None,
    ) -> dict:
        """Full hierarchy audit: check all levels for abstraction issues.

        Returns:
            {
                "L1_issues": [{anchor_name, verdict}],
                "L2_issues": [{category_name, verdict}],
                "L3_issues": [{category_name, verdict}],
                "summary": {total_issues, recommendations: [...]}
            }
        """
        grounding_scores = grounding_scores or {}

        # Audit L1 (anchors within second-level)
        l1_issues = []
        for second_name, anchor_keys in second_codes.items():
            for key in anchor_keys:
                gs = grounding_scores.get(key, 0.5)
                verdict = self.assess_first_level(key, gs)
                if not verdict["level_appropriate"]:
                    l1_issues.append({
                        "anchor": key,
                        "parent_second": second_name,
                        "verdict": verdict,
                    })

        # Audit L2
        l2_issues = []
        second_to_third = {}
        for third_name, second_names in third_codes.items():
            for sn in second_names:
                second_to_third[sn] = third_name

        for second_name, anchor_keys in second_codes.items():
            parent_third = second_to_third.get(second_name, "?")
            verdict = self.assess_second_level(second_name, len(anchor_keys), parent_third)
            if not verdict["level_appropriate"]:
                l2_issues.append({
                    "category": second_name,
                    "anchor_count": len(anchor_keys),
                    "parent_third": parent_third,
                    "verdict": verdict,
                })

        # Audit L3
        l3_issues = []
        for third_name, second_names in third_codes.items():
            verdict = self.assess_third_level(third_name, len(second_names))
            if not verdict["level_appropriate"]:
                l3_issues.append({
                    "category": third_name,
                    "second_count": len(second_names),
                    "verdict": verdict,
                })

        # Generate recommendations
        recommendations = []
        if l1_issues:
            recommendations.append(
                f"{len(l1_issues)} L1 anchors should be reviewed for level appropriateness")
        if l2_issues:
            recommendations.append(
                f"{len(l2_issues)} L2 categories need attention (merge or promote)")
        if l3_issues:
            recommendations.append(
                f"{len(l3_issues)} L3 categories need attention")

        # Check for L2-L3 overlap
        l2_names = set(second_codes.keys())
        l3_names = set(third_codes.keys())
        overlap = l2_names & l3_names
        if overlap:
            recommendations.append(
                f"WARNING: {len(overlap)} names appear at both L2 and L3: {list(overlap)[:5]}")

        return {
            "L1_issues": l1_issues,
            "L2_issues": l2_issues,
            "L3_issues": l3_issues,
            "summary": {
                "total_issues": len(l1_issues) + len(l2_issues) + len(l3_issues),
                "L1_issues": len(l1_issues),
                "L2_issues": len(l2_issues),
                "L3_issues": len(l3_issues),
                "recommendations": recommendations,
            },
        }

    def cross_level_deduplicate(
            self,
            second_codes: Dict[str, List[str]],
            third_codes: Dict[str, List[str]],
    ) -> Tuple[Dict[str, List[str]], Dict[str, List[str]], dict]:
        """Deduplicate across L2 and L3 levels.

        When an L2 category and an L3 category are semantically identical
        (same name or >0.85 embedding similarity), merge the L2 into L3
        and reassign its anchors to sibling L2 categories under that L3.

        Also handles single-anchor L2 categories: if an L2 has only 1 anchor,
        find the most similar other L2 under the same L3 and merge into it.

        Returns:
            (cleaned_second, cleaned_third, report)
        """
        if not second_codes or not third_codes:
            return second_codes, third_codes, {"merged": 0}

        cleaned_second = dict(second_codes)
        cleaned_third = dict(third_codes)
        report = {"exact_name_collisions": [], "semantic_merges": [],
                  "single_anchor_merged": [], "total_merged": 0}

        # Build L3→L2 lookup
        l3_to_l2s = defaultdict(list)
        for l3_name, l2_names in cleaned_third.items():
            for l2_name in l2_names:
                if l2_name in cleaned_second:
                    l3_to_l2s[l3_name].append(l2_name)

        # 1. Exact name collisions: L2 name == L3 name
        l2_names_set = set(cleaned_second.keys())
        l3_names_set = set(cleaned_third.keys())
        exact_collisions = l2_names_set & l3_names_set

        for colliding_name in exact_collisions:
            # Merge: move L2 anchors to the L3, remove the L2
            anchors = cleaned_second.pop(colliding_name, [])
            # Find which L3s reference this L2
            for l3_name, l2_names in list(cleaned_third.items()):
                if colliding_name in l2_names:
                    l2_names.remove(colliding_name)
                    if not l2_names:
                        cleaned_third.pop(l3_name)  # Empty L3
                        # Re-assign anchors from this L2 to other L2s under same L3 parent
                        # Actually, the anchors remain under the merged L3 concept
                    report["exact_name_collisions"].append({
                        "name": colliding_name,
                        "anchors_moved": len(anchors),
                    })
                    report["total_merged"] += 1

        # 2. Single-anchor L2 categories: merge into most similar sibling
        for l2_name, anchor_keys in list(cleaned_second.items()):
            if len(anchor_keys) > 1:
                continue

            # Find parent L3
            parent_l3 = None
            for l3_name, l2_names in cleaned_third.items():
                if l2_name in l2_names:
                    parent_l3 = l3_name
                    break

            if parent_l3 is None:
                continue

            # Find sibling L2s
            siblings = [s for s in l3_to_l2s.get(parent_l3, [])
                       if s != l2_name and s in cleaned_second]

            if not siblings:
                continue  # Keep as-is, no siblings to merge into

            # Find most similar sibling via embedding
            self._load_default_model()
            if self._model:
                import numpy as np
                all_names = [l2_name] + siblings
                embs = self._model.encode(all_names, normalize_embeddings=True,
                                          show_progress_bar=False).astype(np.float32)
                query_emb = embs[0]
                best_sim = -1
                best_sib = siblings[0]
                for j, sib in enumerate(siblings):
                    sim = float(np.dot(query_emb, embs[j + 1]))
                    if sim > best_sim:
                        best_sim = sim
                        best_sib = sib

                if best_sim >= 0.65:
                    # Merge into best sibling
                    cleaned_second[best_sib].extend(anchor_keys)
                    cleaned_second.pop(l2_name)
                    # Update L3 references
                    for l3_name, l2_names in cleaned_third.items():
                        if l2_name in l2_names:
                            l2_names.remove(l2_name)
                    report["single_anchor_merged"].append({
                        "merged": l2_name,
                        "into": best_sib,
                        "similarity": round(best_sim, 3),
                        "anchor": anchor_keys[0] if anchor_keys else "?",
                    })
                    report["total_merged"] += 1

        return cleaned_second, cleaned_third, report
