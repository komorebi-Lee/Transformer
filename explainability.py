"""Research-grade Explainability — Priority 15.

Three subsystems:
  1. Full Theory Provenance Path — Theory → Theme → Anchor → Source Text
  2. Why-this-Theory Explanation — formation reason, merge/edge rationale
  3. Semantic Audit Mode — step-by-step audit trail for researcher review

Usage:
    D:\anaconda3\envs\zthree5\python.exe explainability.py          # build all explanations
    D:\anaconda3\envs\zthree5\python.exe explainability.py <theory> # audit one theory
"""

import json
import logging
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("explainability")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Inputs
PROVENANCE_PATH = os.path.join(BASE_DIR, "provenance_report.json")
HIERARCHY_PATH = os.path.join(BASE_DIR, "data", "anchor_hierarchy_stabilized.json")
NETWORK_PATH = os.path.join(BASE_DIR, "theory_network.json")
CONFIDENCE_PATH = os.path.join(BASE_DIR, "theory_confidence.json")
MERGE_PATH = os.path.join(BASE_DIR, "hierarchy_merge_provenance.json")
EVIDENCE_PATH = os.path.join(BASE_DIR, "theory_evidence.json")
CENTRALITY_PATH = os.path.join(BASE_DIR, "theory_centrality.json")
RELATIONS_PATH = os.path.join(BASE_DIR, "theory_relations.json")

# Outputs
PROVENANCE_PATHS_PATH = os.path.join(BASE_DIR, "theory_provenance_paths.json")
EXPLANATIONS_PATH = os.path.join(BASE_DIR, "theory_explanations.json")
AUDIT_PATH = os.path.join(BASE_DIR, "semantic_audit.json")


class TheoryExplainer:
    """Priority 15: Research-grade Explainability."""

    def __init__(self):
        self.provenance = {}
        self.hierarchy = {}
        self.nodes = []
        self.edges = []
        self.confidence = {}
        self.merges = {}
        self.evidence = {}
        self.centrality = {}
        self.relations = {}

        # Derived
        self.anchor_prov = {}
        self.theme_prov = {}
        self.theory_prov = {}
        self.full_chains = {}
        self.node_index = {}
        self.adjacency = defaultdict(list)
        self.edge_lookup = {}

        # Results
        self.provenance_paths = {}
        self.explanations = {}
        self.audit_trail = {}

    def load_data(self):
        """Load all input data."""
        with open(PROVENANCE_PATH, "r", encoding="utf-8") as f:
            self.provenance = json.load(f)

        with open(HIERARCHY_PATH, "r", encoding="utf-8") as f:
            self.hierarchy = json.load(f)

        with open(NETWORK_PATH, "r", encoding="utf-8") as f:
            nd = json.load(f)
            self.nodes = nd.get("nodes", [])
            self.edges = nd.get("edges", [])

        with open(CONFIDENCE_PATH, "r", encoding="utf-8") as f:
            self.confidence = json.load(f).get("scores", {})

        if os.path.exists(MERGE_PATH):
            with open(MERGE_PATH, "r", encoding="utf-8") as f:
                self.merges = json.load(f)

        if os.path.exists(EVIDENCE_PATH):
            with open(EVIDENCE_PATH, "r", encoding="utf-8") as f:
                self.evidence = json.load(f)

        if os.path.exists(CENTRALITY_PATH):
            with open(CENTRALITY_PATH, "r", encoding="utf-8") as f:
                self.centrality = json.load(f)

        if os.path.exists(RELATIONS_PATH):
            with open(RELATIONS_PATH, "r", encoding="utf-8") as f:
                self.relations = json.load(f)

        self.anchor_prov = self.provenance.get("anchor_provenance", {})
        self.theme_prov = self.provenance.get("theme_provenance", {})
        self.theory_prov = self.provenance.get("theory_provenance", {})
        self.full_chains = self.provenance.get("full_chains", {})

        # Build indices
        self.node_index = {n["id"]: n for n in self.nodes}
        for e in self.edges:
            s, t = e["source"], e["target"]
            self.adjacency[s].append((t, e))
            self.adjacency[t].append((s, e))

        logger.info("Loaded: %d nodes, %d edges, %d anchor prov records",
                     len(self.nodes), len(self.edges), len(self.anchor_prov))

    # ═══════════════════════════════════════════════════════════════
    # 1. Full Theory Provenance Path
    # ═══════════════════════════════════════════════════════════════

    def build_provenance_path(self, theory_name: str) -> dict:
        """Build complete provenance path for a single theory.

        Theory → L2 Themes → L1 Anchors → Source Text
        """
        tp = self.theory_prov.get(theory_name, {})
        node = self.node_index.get(theory_name, {})
        conf = self.confidence.get(theory_name, {})
        centrality = self.centrality.get("scores", {}).get(theory_name, {})

        # Get L2 themes
        theme_names = tp.get("supported_by_themes", [])
        if isinstance(theme_names, dict):
            theme_names = list(theme_names.keys())

        themes_detail = []
        all_anchors = {}

        for theme_name in theme_names:
            theme_data = self.theme_prov.get(theme_name, {})

            # Get anchors for this theme
            anchor_names = []
            if isinstance(theme_data, dict):
                for key in ["supported_by", "supporting_anchors", "anchors"]:
                    val = theme_data.get(key)
                    if isinstance(val, list) and val:
                        anchor_names = val
                        break

            anchors_detail = []
            for anchor_name in anchor_names:
                records = self.anchor_prov.get(anchor_name, [])
                source_texts = []
                for r in records[:5]:  # limit to 5 source texts per anchor
                    source_texts.append({
                        "text": r.get("source_text", "")[:200],
                        "source_file": r.get("source_file", ""),
                        "sentence_index": r.get("sentence_index", -1),
                        "grounding_score": r.get("grounding_score", 0),
                        "semantic_similarity": r.get("semantic_similarity", 0),
                    })

                anchors_detail.append({
                    "anchor": anchor_name,
                    "n_sources": len(records),
                    "avg_grounding": round(
                        np.mean([r.get("grounding_score", 0) for r in records])
                        if records else 0, 4),
                    "source_texts": source_texts,
                })
                all_anchors[anchor_name] = anchors_detail[-1]

            themes_detail.append({
                "theme": theme_name,
                "n_anchors": len(anchor_names),
                "anchors": anchors_detail,
            })

        # Build the path
        path = {
            "theory": theory_name,
            "confidence": round(conf.get("confidence", 0), 4),
            "role": centrality.get("role", "unknown"),
            "network_degree": centrality.get("degree", 0),
            "total_themes": len(themes_detail),
            "total_anchors": sum(t["n_anchors"] for t in themes_detail),
            "total_source_sentences": sum(
                sum(a["n_sources"] for a in t["anchors"]) for t in themes_detail),
            "hierarchy_path": {
                "l3_theory": theory_name,
                "l2_themes": themes_detail,
            },
        }

        return path

    def build_all_provenance_paths(self) -> dict:
        """Build provenance paths for all theories."""
        paths = {}
        for node in self.nodes:
            name = node["id"]
            paths[name] = self.build_provenance_path(name)

        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_theories": len(paths),
            "avg_themes_per_theory": round(
                np.mean([p["total_themes"] for p in paths.values()]), 1),
            "avg_anchors_per_theory": round(
                np.mean([p["total_anchors"] for p in paths.values()]), 1),
            "total_source_sentences": sum(p["total_source_sentences"] for p in paths.values()),
        }

        self.provenance_paths = {"summary": summary, "paths": paths}
        logger.info("Built %d provenance paths", len(paths))
        return self.provenance_paths

    # ═══════════════════════════════════════════════════════════════
    # 2. Why-this-Theory Explanation
    # ═══════════════════════════════════════════════════════════════

    def explain_theory(self, theory_name: str) -> dict:
        """Generate a comprehensive explanation for why a theory exists.

        Explains:
          - Why formed (formation rationale)
          - Why belongs to themes (parent theme mapping)
          - Why merge happened (merge rationale from provenance)
          - Why edge relations exist (network connection rationale)
        """
        conf = self.confidence.get(theory_name, {})
        components = conf.get("components", {})
        raw = conf.get("raw_metrics", {})
        path = self.build_provenance_path(theory_name)

        # 1. Formation rationale
        formation_reasons = []
        confidence_val = conf.get("confidence", 0)

        if confidence_val >= 0.7:
            formation_reasons.append(
                f"高置信度理论({confidence_val:.3f})，扎根证据充分且网络结构稳定")
        elif confidence_val >= 0.5:
            formation_reasons.append(
                f"中等置信度理论({confidence_val:.3f})，有一定证据支撑但需进一步验证")
        else:
            formation_reasons.append(
                f"低置信度理论({confidence_val:.3f})，证据支撑不足，建议人工审核")

        n_anchors = path["total_anchors"]
        n_themes = path["total_themes"]
        formation_reasons.append(
            f"由{n_anchors}个概念锚点通过{n_themes}个主题维度归纳形成")

        # Grounding quality
        grounding = components.get("grounding", 0)
        if grounding >= 0.7:
            formation_reasons.append(f"扎根质量优秀({grounding:.3f})，锚点与原文匹配度高")
        elif grounding >= 0.5:
            formation_reasons.append(f"扎根质量良好({grounding:.3f})")
        else:
            formation_reasons.append(f"扎根质量偏低({grounding:.3f})，建议检查锚点编码")

        # 2. Theme membership rationale
        theme_rationale = []
        for theme in path["hierarchy_path"]["l2_themes"][:5]:
            theme_name = theme["theme"]
            n_anchors_t = theme["n_anchors"]
            avg_g = np.mean([a["avg_grounding"] for a in theme["anchors"]]) if theme["anchors"] else 0
            theme_rationale.append({
                "theme": theme_name,
                "rationale": (
                    f"该理论通过{theme_name}主题归纳，包含{n_anchors_t}个锚点，"
                    f"平均扎根度{avg_g:.3f}"
                ),
            })

        # 3. Merge rationale (from merge provenance)
        merge_rationale = []
        l2_merges = self.merges.get("l2_merges", [])
        l3_merges = self.merges.get("l3_merges", [])

        # Check if this theory was involved in any merge
        for m in l3_merges:
            canonical = m.get("canonical", "")
            members = m.get("members", [])
            if theory_name == canonical or theory_name in members:
                others = [x for x in members if x != theory_name]
                merge_rationale.append({
                    "type": "l3_merge",
                    "merged_with": others,
                    "canonical_name": canonical,
                    "rationale": (
                        f"该理论在层级稳定化中{'吸收' if theory_name == canonical else '被合并至'}"
                        f"{canonical}，合并了{len(others)}个语义相近的理论"
                    ),
                })

        # 4. Network connection rationale
        edge_rationale = []
        neighbors = self.adjacency.get(theory_name, [])
        # Top 3 strongest connections
        neighbors_sorted = sorted(neighbors, key=lambda x: x[1].get("weight", 0), reverse=True)[:5]

        for nb_name, edge in neighbors_sorted:
            etype = edge.get("edge_type", "unknown")
            weight = edge.get("weight", 0)
            rel_key = "|||".join(sorted([theory_name, nb_name]))
            rel_type = self.relations.get("relations", {}).get(rel_key, {}).get("relation_type", etype)

            edge_rationale.append({
                "connected_to": nb_name,
                "edge_type": rel_type,
                "weight": round(weight, 4),
                "rationale": (
                    f"与'{nb_name}'形成{rel_type}关系(权重{weight:.3f})，"
                    f"共享L2主题{edge.get('shared_l2_count', 0)}个，"
                    f"语义相似度{edge.get('semantic_similarity', 0):.3f}"
                ),
            })

        # 5. Evidence assessment
        ev_data = self.evidence.get("metrics", {}).get(theory_name, {})
        ev_density = ev_data.get("density_score", 0)
        ev_diversity = self.evidence.get("diversity", {}).get("metrics", {}).get(
            theory_name, {}).get("diversity_score", 0)

        evidence_rationale = (
            f"证据密度{ev_density:.3f}，证据多样性{ev_diversity:.3f}，"
            f"来自{ev_data.get('source_file_count', 0)}个数据源，"
            f"共{path['total_source_sentences']}条原文句子支撑"
        )

        # Assemble full explanation
        explanation = {
            "theory": theory_name,
            "confidence": round(confidence_val, 4),
            "formation": {
                "rationale": formation_reasons,
                "evidence": evidence_rationale,
            },
            "theme_membership": theme_rationale,
            "merge_history": merge_rationale,
            "network_connections": edge_rationale,
            "summary": (
                f"理论'{theory_name}'是一个{self._confidence_label(confidence_val)}的理论，"
                f"由{path['total_anchors']}个锚点、{path['total_themes']}个主题维度支撑，"
                f"在网络中处于{conf.get('role', 'unknown')}位置。"
                f"{evidence_rationale}。"
            ),
        }

        return explanation

    @staticmethod
    def _confidence_label(conf: float) -> str:
        if conf >= 0.8:
            return "证据充分的核心"
        elif conf >= 0.65:
            return "较为可靠的"
        elif conf >= 0.5:
            return "有待验证的"
        else:
            return "需重点关注的薄弱"

    def build_all_explanations(self) -> dict:
        """Generate explanations for all theories."""
        explanations = {}
        for node in self.nodes:
            name = node["id"]
            explanations[name] = self.explain_theory(name)

        avg_conf = np.mean([e["confidence"] for e in explanations.values()])
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_explanations": len(explanations),
            "avg_confidence": round(float(avg_conf), 4),
        }

        self.explanations = {"summary": summary, "explanations": explanations}
        logger.info("Built %d theory explanations", len(explanations))
        return self.explanations

    # ═══════════════════════════════════════════════════════════════
    # 3. Semantic Audit Mode
    # ═══════════════════════════════════════════════════════════════

    def generate_audit_trail(self, theory_name: str) -> dict:
        """Generate a step-by-step audit trail for researcher review.

        Walk through:
          1. Grounding check
          2. Drift assessment
          3. Compression review
          4. Provenance verification
          5. Theory formation pathway
        """
        conf = self.confidence.get(theory_name, {})
        components = conf.get("components", {})
        raw = conf.get("raw_metrics", {})
        path = self.build_provenance_path(theory_name)
        expl = self.explanations.get("explanations", {}).get(theory_name,
                      self.explain_theory(theory_name))

        steps = []

        # Step 1: Grounding Check
        grounding = components.get("grounding", 0)
        steps.append({
            "step": 1,
            "title": "扎根度检查 (Grounding Check)",
            "finding": f"扎根度: {grounding:.3f}",
            "assessment": "PASS" if grounding >= 0.5 else "WARN" if grounding >= 0.35 else "FAIL",
            "detail": (
                f"该理论的平均锚点扎根度为{grounding:.3f}。"
                f"{'扎根质量良好，锚点与源文本语义匹配度高。' if grounding >= 0.5 else '扎根度偏低，建议检查锚点编码质量。'}"
            ),
            "evidence": {
                "avg_grounding": raw.get("avg_grounding", 0),
                "n_anchors": path["total_anchors"],
                "sample_anchors": [
                    {"anchor": list(a.keys())[0] if isinstance(a, dict) else str(a),
                     "grounding": a.get("avg_grounding", 0) if isinstance(a, dict) else 0}
                    for a in path["hierarchy_path"]["l2_themes"][:3]
                    for a in (a["anchors"][:2] if a.get("anchors") else [])
                ][:5],
            },
        })

        # Step 2: Support Diversity Check
        diversity = components.get("support_diversity", 0)
        steps.append({
            "step": 2,
            "title": "支撑多样性检查 (Support Diversity)",
            "finding": f"支撑多样性: {diversity:.3f}",
            "assessment": "PASS" if diversity >= 0.5 else "WARN" if diversity >= 0.3 else "FAIL",
            "detail": (
                f"该理论有{path['total_themes']}个L2主题和{path['total_anchors']}个L1锚点。"
                f"{'支撑结构多样化，避免了单一来源偏倚。' if diversity >= 0.5 else '支撑结构较为单一，可能存在偏倚风险。'}"
            ),
            "evidence": {
                "l2_count": path["total_themes"],
                "l1_count": path["total_anchors"],
            },
        })

        # Step 3: Provenance Depth Check
        provenance = components.get("provenance_depth", 0)
        steps.append({
            "step": 3,
            "title": "溯源深度检查 (Provenance Depth)",
            "finding": f"溯源深度: {provenance:.3f}",
            "assessment": "PASS" if provenance >= 0.4 else "WARN" if provenance >= 0.2 else "FAIL",
            "detail": (
                f"该理论有{path['total_source_sentences']}条原文句子支撑。"
                f"{'证据充足，溯源链完整。' if provenance >= 0.4 else '证据偏少，建议补充编码。'}"
            ),
            "evidence": {
                "total_sentences": path["total_source_sentences"],
                "sentences_per_anchor": (
                    path["total_source_sentences"] / max(path["total_anchors"], 1)),
            },
        })

        # Step 4: Network Stability Check
        stability = components.get("semantic_stability", 0)
        degree = raw.get("network_degree", 0)
        steps.append({
            "step": 4,
            "title": "网络稳定性检查 (Network Stability)",
            "finding": f"语义稳定性: {stability:.3f}, 网络度: {degree}",
            "assessment": "PASS" if stability >= 0.4 and degree >= 2 else "WARN",
            "detail": (
                f"该理论在网络中有{degree}个连接。"
                f"{'网络连接良好，理论位置稳定。' if degree >= 2 else '网络连接不足，理论可能处于边缘位置。'}"
            ),
            "evidence": {
                "network_degree": degree,
                "avg_edge_weight": raw.get("avg_edge_weight", 0),
                "strongest_connections": [
                    {"theory": nb, "weight": e.get("weight", 0)}
                    for nb, e in sorted(
                        self.adjacency.get(theory_name, []),
                        key=lambda x: x[1].get("weight", 0), reverse=True
                    )[:3]
                ],
            },
        })

        # Step 5: Merge History
        merge_info = expl.get("merge_history", [])
        steps.append({
            "step": 5,
            "title": "合并历史检查 (Merge History)",
            "finding": f"{'有合并记录' if merge_info else '无合并记录'}",
            "assessment": "INFO",
            "detail": (
                f"该理论{'在层级稳定化中经历了合并' if merge_info else '直接来源于v11训练数据映射，未经历合并'}。"
            ),
            "evidence": merge_info,
        })

        # Overall assessment
        assessments = [s["assessment"] for s in steps]
        fail_count = assessments.count("FAIL")
        warn_count = assessments.count("WARN")

        if fail_count > 0:
            overall = "NEEDS_REVIEW"
            overall_msg = f"{fail_count}项检查未通过，{warn_count}项警告，建议研究者重点审核"
        elif warn_count >= 2:
            overall = "CAUTION"
            overall_msg = f"{warn_count}项警告，建议研究者关注"
        else:
            overall = "HEALTHY"
            overall_msg = "各项指标正常，理论结构健康"

        audit = {
            "theory": theory_name,
            "timestamp": datetime.now().isoformat(),
            "overall_assessment": overall,
            "overall_message": overall_msg,
            "summary": expl.get("summary", ""),
            "steps": steps,
        }

        return audit

    def build_full_audit(self) -> dict:
        """Generate audit trail for all theories."""
        # Ensure explanations exist
        if not self.explanations:
            self.build_all_explanations()

        audits = {}
        for node in self.nodes:
            name = node["id"]
            audits[name] = self.generate_audit_trail(name)

        # Summary
        overall_counts = Counter(a["overall_assessment"] for a in audits.values())
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_audited": len(audits),
            "healthy": overall_counts.get("HEALTHY", 0),
            "caution": overall_counts.get("CAUTION", 0),
            "needs_review": overall_counts.get("NEEDS_REVIEW", 0),
        }

        self.audit_trail = {"summary": summary, "audits": audits}
        logger.info("Audit complete: %d healthy, %d caution, %d needs review",
                     summary["healthy"], summary["caution"], summary["needs_review"])
        return self.audit_trail

    # ── Saving ────────────────────────────────────────────────────

    def save_all(self):
        if self.provenance_paths:
            with open(PROVENANCE_PATHS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.provenance_paths, f, ensure_ascii=False, indent=2)
            logger.info("Provenance paths saved: %s", PROVENANCE_PATHS_PATH)

        if self.explanations:
            with open(EXPLANATIONS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.explanations, f, ensure_ascii=False, indent=2)
            logger.info("Explanations saved: %s", EXPLANATIONS_PATH)

        if self.audit_trail:
            with open(AUDIT_PATH, "w", encoding="utf-8") as f:
                json.dump(self.audit_trail, f, ensure_ascii=False, indent=2)
            logger.info("Audit trail saved: %s", AUDIT_PATH)

    # ── Full Pipeline ─────────────────────────────────────────────

    def run(self):
        self.load_data()

        print("\n" + "=" * 60)
        print("PRIORITY 15: RESEARCH-GRADE EXPLAINABILITY")
        print("=" * 60)

        print("\n[1/3] Full Theory Provenance Paths...")
        paths = self.build_all_provenance_paths()
        ps = paths["summary"]
        print(f"  Theories: {ps['total_theories']}")
        print(f"  Avg themes/theory: {ps['avg_themes_per_theory']}")
        print(f"  Avg anchors/theory: {ps['avg_anchors_per_theory']}")
        print(f"  Total source sentences traced: {ps['total_source_sentences']}")

        print("\n[2/3] Why-this-Theory Explanations...")
        explanations = self.build_all_explanations()
        es = explanations["summary"]
        print(f"  Explanations built: {es['total_explanations']}")
        print(f"  Avg confidence: {es['avg_confidence']:.4f}")

        print("\n[3/3] Semantic Audit Mode...")
        audit = self.build_full_audit()
        at = audit["summary"]
        print(f"  Audited: {at['total_audited']}")
        print(f"  Healthy: {at['healthy']}, Caution: {at['caution']}, "
              f"Needs Review: {at['needs_review']}")

        self.save_all()

        print(f"\n  Output: {PROVENANCE_PATHS_PATH}")
        print(f"  Output: {EXPLANATIONS_PATH}")
        print(f"  Output: {AUDIT_PATH}")

        return {"paths": paths, "explanations": explanations, "audit": audit}


# ── CLI ──────────────────────────────────────────────────────────

def main():
    explainer = TheoryExplainer()

    if len(sys.argv) > 1:
        # Audit a specific theory
        theory_name = sys.argv[1]
        explainer.load_data()
        print(f"\n{'=' * 60}")
        print(f"SEMANTIC AUDIT: {theory_name}")
        print(f"{'=' * 60}")

        audit = explainer.generate_audit_trail(theory_name)
        for step in audit["steps"]:
            status_icon = {"PASS": "[OK]", "WARN": "[!!]", "FAIL": "[XX]", "INFO": "[ii]"}[step["assessment"]]
            print(f"\n{status_icon} Step {step['step']}: {step['title']}")
            print(f"   Finding: {step['finding']}")
            print(f"   {step['detail']}")

        print(f"\n{'=' * 60}")
        print(f"OVERALL: {audit['overall_assessment']} — {audit['overall_message']}")
    else:
        result = explainer.run()

        at = result["audit"]["summary"]
        print("\n" + "=" * 60)
        print("EXPLAINABILITY SYSTEM COMPLETE")
        print("=" * 60)
        print(f"  Provenance paths: {result['paths']['summary']['total_theories']}")
        print(f"  Explanations: {result['explanations']['summary']['total_explanations']}")
        print(f"  Audit: {at['healthy']} healthy, {at['caution']} caution, "
              f"{at['needs_review']} needs review")


if __name__ == "__main__":
    main()
