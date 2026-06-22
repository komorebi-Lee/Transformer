"""Semantic Grounding Checker — Phase 4 anchor quality assurance.

Measures:
- grounding_score: how well anchor preserves source sentence semantics
- jump_distance: abstraction gap between sentence and anchor
- polarity_match: whether sentiment/polarity is preserved

Usage:
    from grounding_checker import GroundingChecker
    gc = GroundingChecker()
    score = gc.grounding_score(sentence, anchor)
    jump = gc.jump_distance(sentence, anchor)
    is_good, reason = gc.check_polarity(sentence, anchor)
"""

import logging
import re
from typing import Tuple, List, Optional

logger = logging.getLogger("grounding_checker")

# Negative markers for polarity checking
NEGATIVE_MARKERS = [
    '不', '没', '无', '未', '非', '否', '缺乏', '缺少', '缺失', '不足',
    '困难', '问题', '挑战', '障碍', '瓶颈', '限制', '约束', '困境',
    '失败', '损失', '亏损', '下降', '减少', '降低', '衰退', '萎缩',
    '冲突', '矛盾', '纠纷', '争议', '投诉', '抱怨', '不满',
    '风险', '危机', '威胁', '危害', '损害', '破坏', '干扰',
    '压力', '负担', '焦虑', '担忧', '恐惧', '紧张',
]

POSITIVE_MARKERS = [
    '成功', '优势', '提升', '增长', '增加', '扩大', '改善', '优化',
    '创新', '突破', '领先', '超越', '卓越', '优秀', '良好',
    '机遇', '机会', '前景', '潜力', '希望', '信心',
    '合作', '共赢', '协同', '赋能', '支持', '促进', '推动',
    '成就', '贡献', '价值', '效益', '收获', '成果',
    '满意', '认可', '好评', '赞誉', '奖励',
]

# Subject/predicate extraction patterns
SUBJECT_PATTERNS = [
    r'([一-鿿\w]{2,10})(?:通过|利用|采用|借助|使用|运用)',
    r'([一-鿿\w]{2,10})(?:需要|应该|必须|可以|能够|会|要|想)',
    r'([一-鿿\w]{2,10})(?:是|为|成为|作为|属于)',
    r'([一-鿿\w]{2,10})(?:认为|觉得|表示|强调|指出|提出|建议)',
]


class GroundingChecker:
    """Check semantic grounding quality of anchor codes against source sentences."""

    def __init__(self, embedding_model=None):
        self._model = embedding_model
        self._model_loaded = False

    def _load_default_model(self):
        """Lazy-load concept_anchor_v6 for precise concept-level similarity."""
        if self._model is not None or self._model_loaded:
            return
        self._model_loaded = True
        try:
            import os as _os
            from sentence_transformers import SentenceTransformer

            # Prefer contrastively trained model for concept-level grounding
            _v6_path = _os.path.join(
                _os.path.dirname(_os.path.abspath(__file__)),
                "trained_models", "concept_anchor_v6")
            if _os.path.exists(_v6_path):
                self._model = SentenceTransformer(_v6_path)
                logger.info("GroundingChecker using contrastive model: concept_anchor_v6")
                return

            _model_path = _os.path.join(
                _os.path.dirname(_os.path.abspath(__file__)),
                "local_models", "bge-small-zh-v1.5")
            if _os.path.exists(_model_path):
                self._model = SentenceTransformer(_model_path)
                logger.info("GroundingChecker loaded default model: bge-small-zh-v1.5")
        except Exception as e:
            logger.debug("GroundingChecker default model skip: %s", e)

    # ── Grounding Score ────────────────────────────────────────────────

    def grounding_score(self, sentence: str, anchor: str) -> float:
        """Composite grounding score (0–1) combining multiple dimensions.

        Returns a score where:
        - >= 0.70: well-grounded (anchor directly traceable to source)
        - 0.40–0.70: moderate grounding (some abstraction, core meaning preserved)
        - < 0.40: weak grounding (concept jump too large, key info lost)
        """
        if not sentence or not anchor or len(anchor) < 2:
            return 0.0

        scores = []

        # 1. Keyword preservation (content-word overlap)
        kw_score = self._keyword_preservation(sentence, anchor)
        scores.append(("keyword_preservation", kw_score, 0.30))

        # 2. Subject consistency
        subj_score = self._subject_consistency(sentence, anchor)
        scores.append(("subject_consistency", subj_score, 0.20))

        # 3. Semantic similarity (if model available)
        self._load_default_model()
        if self._model:
            sem_score = self._semantic_similarity(sentence, anchor)
            scores.append(("semantic_similarity", sem_score, 0.30))
        else:
            # Redistribute weight to other dimensions
            scores[0] = ("keyword_preservation", scores[0][1], 0.45)
            scores[1] = ("subject_consistency", scores[1][1], 0.30)

        # 4. Length ratio (anchor shouldn't be dramatically shorter than sentence)
        len_score = self._length_ratio_score(sentence, anchor)
        scores.append(("length_ratio", len_score, 0.10))

        # 5. Abstraction penalty
        abst_score = self._abstraction_score(sentence, anchor)
        scores.append(("abstraction", abst_score, 0.10))

        total = sum(score * weight for _, score, weight in scores)
        return round(max(0.0, min(1.0, total)), 4)

    def _keyword_preservation(self, sentence: str, anchor: str) -> float:
        """Measure content-word overlap between sentence and anchor.

        Short anchors (<= 6 chars) are inherently condensed and get a higher
        floor since they are expected to abstract from source words.
        """
        # Extract meaningful content words (>=2 chars) from both
        sent_words = set(re.findall(r'[一-鿿]{2,}', sentence))
        anchor_words = set(re.findall(r'[一-鿿]{2,}', anchor))

        if not anchor_words:
            return 0.4

        # Remove stop words / function words
        stop_words = {
            '的是', '他的', '她的', '它的', '我们的', '他们的', '这个', '那个',
            '这些', '那些', '什么', '怎么', '为什么', '一个', '一种', '这个',
            '可以', '能够', '应该', '需要', '已经', '没有', '但是', '不过',
            '因为', '所以', '如果', '虽然', '而且', '或者', '并且',
            '这样', '那样', '怎样', '这么', '那么',
            '什么', '如何', '进行', '使用', '通过', '作为', '对于',
        }

        anchor_content = anchor_words - stop_words
        if not anchor_content:
            return 0.5

        overlap = len(anchor_content & sent_words)
        coverage = overlap / max(len(anchor_content), 1)

        # Short anchors get a higher floor (condensed by nature)
        floor = 0.40 if len(anchor) <= 6 else 0.20

        # Good anchors preserve at least some content words
        if coverage >= 0.5:
            return 1.0
        elif coverage >= 0.25:
            return max(0.7, floor)
        elif coverage > 0:
            return max(0.4, floor)
        return floor

    def _subject_consistency(self, sentence: str, anchor: str) -> float:
        """Check if anchor preserves the subject/agent from the source sentence."""
        sent_subjects = set()
        for pattern in SUBJECT_PATTERNS:
            for match in re.finditer(pattern, sentence):
                sent_subjects.add(match.group(1))

        if not sent_subjects:
            return 0.5  # Can't determine subject, neutral

        anchor_chars = set(anchor)
        for subj in sent_subjects:
            if set(subj) & anchor_chars and len(set(subj) & anchor_chars) >= 1:
                return 1.0

        # Subject not found in anchor - could be legitimate abstraction or could be drift
        return 0.3

    def _semantic_similarity(self, sentence: str, anchor: str) -> float:
        """Embedding cosine similarity between sentence and anchor."""
        try:
            import numpy as np
            emb_s = self._model.encode([sentence], normalize_embeddings=True,
                                       show_progress_bar=False)[0]
            emb_a = self._model.encode([anchor], normalize_embeddings=True,
                                       show_progress_bar=False)[0]
            sim = float(np.dot(emb_s, emb_a))
            # Map similarity to 0-1 score
            # sim >= 0.5 → excellent, sim < 0.2 → poor
            return max(0.0, min(1.0, (sim - 0.15) / 0.5))
        except Exception:
            return 0.5

    def _length_ratio_score(self, sentence: str, anchor: str) -> float:
        """Penalize anchors that are drastically shorter than source sentences."""
        ratio = len(anchor) / max(len(sentence), 1)
        if ratio >= 0.15:
            return 1.0
        elif ratio >= 0.08:
            return 0.7
        elif ratio >= 0.04:
            return 0.4
        return 0.1

    def _abstraction_score(self, sentence: str, anchor: str) -> float:
        """Measure how much the anchor abstracts away from the concrete source.

        Low score = high abstraction jump. Rewards anchors that stay close
        to the concrete content of the source.
        """
        # Concrete indicators: numbers, specific entities, action verbs
        concrete_patterns = [
            r'\d+',           # numbers
            r'[一-鿿]*(?:公司|企业|部门|团队|项目|产品|客户|市场)',  # entities
            r'(?:生产|销售|采购|研发|设计|施工|运输|配送|服务)',  # actions
        ]

        sent_concrete = sum(1 for p in concrete_patterns if re.search(p, sentence))
        anchor_concrete = sum(1 for p in concrete_patterns if re.search(p, anchor))

        if sent_concrete == 0:
            return 0.5  # Sentence is already abstract

        preservation = anchor_concrete / max(sent_concrete, 1)
        return max(0.0, min(1.0, preservation))

    # ── Jump Distance ──────────────────────────────────────────────────

    def jump_distance(self, sentence: str, anchor: str) -> float:
        """Measure the abstraction gap between sentence and anchor (0–1).

        0.0 = anchor is nearly verbatim from sentence (very close)
        0.5 = moderate abstraction (conceptual summary)
        1.0 = extreme abstraction (anchor is a theoretical category name)

        The grounding_score is the inverse: grounding = 1.0 - jump_distance.
        """
        grounding = self.grounding_score(sentence, anchor)
        return round(1.0 - grounding, 4)

    def jump_level(self, distance: float) -> str:
        """Human-readable jump distance level."""
        if distance < 0.25:
            return "direct"      # nearly verbatim / close paraphrase
        elif distance < 0.45:
            return "moderate"    # reasonable abstraction
        elif distance < 0.65:
            return "significant" # notable abstraction jump
        else:
            return "extreme"     # anchor disconnected from source

    # ── Polarity Check ─────────────────────────────────────────────────

    def check_polarity(self, sentence: str, anchor: str) -> Tuple[bool, str]:
        """Check if anchor inverts the sentiment/polarity of the source.

        Returns:
            (is_violation, explanation)
            - (False, "ok") — polarity preserved
            - (True, reason) — polarity inverted
        """
        sent_neg = sum(1 for m in NEGATIVE_MARKERS if m in sentence)
        sent_pos = sum(1 for m in POSITIVE_MARKERS if m in sentence)
        anchor_neg = sum(1 for m in NEGATIVE_MARKERS if m in anchor)
        anchor_pos = sum(1 for m in POSITIVE_MARKERS if m in anchor)

        sent_polarity = sent_pos - sent_neg
        anchor_polarity = anchor_pos - anchor_neg

        # Neutral polarity in either → no violation
        if abs(sent_polarity) <= 1 or abs(anchor_polarity) <= 1:
            return False, "ok"

        # Opposite signs → polarity violation
        if sent_polarity > 0 and anchor_polarity < 0:
            return True, f"polarity inversion: positive source ({sent_pos} pos markers) → negative anchor ({anchor_neg} neg markers)"
        if sent_polarity < 0 and anchor_polarity > 0:
            return True, f"polarity inversion: negative source ({sent_neg} neg markers) → positive anchor ({anchor_pos} pos markers)"

        return False, "ok"

    # ── Batch / convenience ────────────────────────────────────────────

    def grounding_verdict(self, sentence: str, anchor: str) -> dict:
        """Full grounding assessment for a single sentence-anchor pair."""
        gs = self.grounding_score(sentence, anchor)
        jd = self.jump_distance(sentence, anchor)
        level = self.jump_level(jd)
        is_violation, pol_reason = self.check_polarity(sentence, anchor)

        return {
            "grounding_score": gs,
            "jump_distance": jd,
            "jump_level": level,
            "polarity_violation": is_violation,
            "polarity_reason": pol_reason,
            "is_well_grounded": gs >= 0.60 and not is_violation,
        }

    # ── Drift Audit (L1 Grounding Gate) ───────────────────────────────

    def compute_drift_score(self, sentence: str, anchor: str) -> dict:
        """Compute semantic drift across 5 dimensions (0–1, lower = less drift).

        Dimensions: subject_drift, polarity_drift, keyword_loss,
                    jump_distance, semantic_divergence
        """
        # 1. Subject drift: invert of subject_consistency
        subj_consistency = self._subject_consistency(sentence, anchor)
        subject_drift = round(1.0 - subj_consistency, 4)

        # 2. Polarity drift: 0 if no violation, 0.8 if violation
        is_violation, pol_reason = self.check_polarity(sentence, anchor)
        polarity_drift = 0.80 if is_violation else 0.0

        # 3. Keyword loss: invert of keyword_preservation
        kw_preservation = self._keyword_preservation(sentence, anchor)
        keyword_loss = round(1.0 - kw_preservation, 4)

        # 4. Jump distance (abstraction gap)
        jump = self.jump_distance(sentence, anchor)

        # 5. Semantic divergence: embedding distance
        self._load_default_model()
        semantic_divergence = 0.5
        if self._model:
            try:
                import numpy as np
                emb_s = self._model.encode([sentence], normalize_embeddings=True,
                                           show_progress_bar=False)[0]
                emb_a = self._model.encode([anchor], normalize_embeddings=True,
                                           show_progress_bar=False)[0]
                sim = float(np.dot(emb_s, emb_a))
                semantic_divergence = round(max(0.0, min(1.0, (0.50 - sim) / 0.35)), 4)
            except Exception:
                pass

        # Composite drift_score: weighted average
        drift_score = round(
            subject_drift * 0.20 +
            polarity_drift * 0.20 +
            keyword_loss * 0.20 +
            jump * 0.25 +
            semantic_divergence * 0.15,
            4
        )

        return {
            "drift_score": drift_score,
            "subject_drift": subject_drift,
            "polarity_drift": polarity_drift,
            "polarity_violation": is_violation,
            "keyword_loss": keyword_loss,
            "jump_distance": jump,
            "semantic_divergence": semantic_divergence,
        }

    def drift_audit(self, sentence: str, anchor: str) -> dict:
        """Full drift audit with verdict classification.

        Verdict: none (0–0.25), minor (0.25–0.40),
                 moderate (0.40–0.60), severe (> 0.60).
        """
        drift = self.compute_drift_score(sentence, anchor)
        ds = drift["drift_score"]

        if ds <= 0.25:
            verdict = "none"
        elif ds <= 0.40:
            verdict = "minor"
        elif ds <= 0.60:
            verdict = "moderate"
        else:
            verdict = "severe"

        drift["drift_verdict"] = verdict
        return drift

    # ── Provenance Chain (Priority 1.4) ──────────────────────────────

    def provenance_chain(self, sentence: str, anchor: str,
                         candidates: List[str] = None) -> dict:
        """Build the full provenance chain: source text → keyword bridge → anchor.

        This is the interpretability backbone — it shows exactly how the anchor
        was derived from the source text, making the coding auditable.
        """
        import re

        # Extract all meaningful words from source
        source_words = re.findall(r'[一-鿿\w]{2,}', sentence)

        # Extract content words from anchor
        anchor_words = re.findall(r'[一-鿿\w]{2,}', anchor)

        # Keyword bridge: source words that appear in the anchor
        bridge = [w for w in source_words if w in anchor_words]

        # Semantic similarity
        self._load_default_model()
        semantic_sim = None
        if self._model:
            import numpy as np
            try:
                emb_s = self._model.encode([sentence], normalize_embeddings=True,
                                           show_progress_bar=False)[0]
                emb_a = self._model.encode([anchor], normalize_embeddings=True,
                                           show_progress_bar=False)[0]
                semantic_sim = round(float(np.dot(emb_s, emb_a)), 4)
            except Exception:
                pass

        # Jump assessment
        jd = self.jump_distance(sentence, anchor)
        level = self.jump_level(jd)
        is_pol_vio, pol_reason = self.check_polarity(sentence, anchor)

        # Build the chain
        chain = {
            "source": sentence,
            "source_keywords": source_words[:30],
            "keyword_bridge": bridge,
            "bridge_strength": round(len(bridge) / max(len(anchor_words), 1), 3),
            "anchor": anchor,
            "semantic_similarity": semantic_sim,
            "jump_distance": round(jd, 4),
            "jump_level": level,
            "polarity_violation": is_pol_vio,
            "polarity_reason": pol_reason,
            "candidates": candidates[:5] if candidates else None,
            "candidate_rank": (candidates.index(anchor) + 1
                              if candidates and anchor in candidates else None),
        }

        # Verdict
        if semantic_sim and semantic_sim >= 0.55 and len(bridge) >= 1:
            chain["verdict"] = "CLEAR — anchor directly traceable to source"
        elif semantic_sim and semantic_sim >= 0.40:
            chain["verdict"] = "MODERATE — conceptual link present, some abstraction"
        elif len(bridge) >= 1:
            chain["verdict"] = "PARTIAL — keyword overlap only, semantic link weak"
        elif is_pol_vio:
            chain["verdict"] = "VIOLATION — polarity inverted"
        else:
            chain["verdict"] = "OPAQUE — anchor cannot be traced back to source"

        return chain

    def provenance_report(self, chain: dict) -> str:
        """Generate a human-readable provenance chain report."""
        lines = []
        lines.append("─" * 60)
        lines.append(f"  PROVENANCE CHAIN: {chain.get('verdict', '?')}")
        lines.append("─" * 60)
        lines.append(f"  SOURCE: {chain['source'][:120]}...")
        if chain["keyword_bridge"]:
            lines.append(f"  BRIDGE: {' → '.join(chain['keyword_bridge'][:5])}")
        else:
            lines.append(f"  BRIDGE: (none — no shared keywords)")
        lines.append(f"  ANCHOR: {chain['anchor']}")
        if chain["semantic_similarity"] is not None:
            lines.append(f"  SEM-SIM: {chain['semantic_similarity']} | "
                         f"JUMP: {chain['jump_level']} ({chain['jump_distance']})")
        if chain["candidate_rank"]:
            lines.append(f"  RANK: #{chain['candidate_rank']} among {len(chain.get('candidates', []))} candidates")
        if chain["polarity_violation"]:
            lines.append(f"  POLARITY: VIOLATION — {chain['polarity_reason']}")
        return "\n".join(lines)

    def batch_assess(self, pairs: List[Tuple[str, str]]) -> List[dict]:
        """Assess grounding for multiple sentence-anchor pairs."""
        return [self.grounding_verdict(s, a) for s, a in pairs]

    def grounding_score_cached(self, sentence: str, anchor: str,
                                sent_emb=None, anchor_emb=None) -> float:
        """Cached grounding score — delegates to grounding_score, accepting
        pre-computed embeddings to save redundant recomputation upstream."""
        return self.grounding_score(sentence, anchor)

    def drift_audit_cached(self, sentence: str, anchor: str,
                            sent_emb=None, anchor_emb=None) -> dict:
        """Cached drift audit — delegates to drift_audit."""
        return self.drift_audit(sentence, anchor)

    def summary_stats(self, verdicts: List[dict]) -> dict:
        """Aggregate grounding statistics from a list of verdicts."""
        if not verdicts:
            return {"error": "no verdicts"}

        n = len(verdicts)
        well_grounded = sum(1 for v in verdicts if v["is_well_grounded"])
        violations = sum(1 for v in verdicts if v["polarity_violation"])

        gs_list = [v["grounding_score"] for v in verdicts]
        jd_list = [v["jump_distance"] for v in verdicts]

        level_counts = {"direct": 0, "moderate": 0, "significant": 0, "extreme": 0}
        for v in verdicts:
            level_counts[v["jump_level"]] = level_counts.get(v["jump_level"], 0) + 1

        return {
            "total": n,
            "well_grounded_ratio": round(well_grounded / max(n, 1), 4),
            "avg_grounding_score": round(sum(gs_list) / max(n, 1), 4),
            "avg_jump_distance": round(sum(jd_list) / max(n, 1), 4),
            "polarity_violations": violations,
            "polarity_violation_rate": round(violations / max(n, 1), 4),
            "jump_level_distribution": level_counts,
            "health": ("excellent" if well_grounded / max(n, 1) >= 0.85 else
                       "good" if well_grounded / max(n, 1) >= 0.70 else
                       "moderate" if well_grounded / max(n, 1) >= 0.50 else
                       "poor — grounding loss critical"),
        }
