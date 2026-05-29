"""增强的扎根理论编码生成器 - 支持训练模型预测和概念锚点检索。

一阶编码管线（改进7 - 概念锚点门控）:
1. 句子标准化
2. 概念锚点FAISS检索 → 高分锚点直接入选，门控抽取式n-gram
3. 抽取式n-gram生成（仅锚点门控未触发时）
4. 候选评分 + 排序 + 精选
5. 重排序 + 最终选择

二阶/三阶编码使用语义相似度匹配编码库。
"""

import json
import logging
import math
import os
import re
import sys
from collections import Counter, defaultdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import jieba
import numpy as np
import jieba.posseg as pseg

logger = logging.getLogger(__name__)

# Optional imports
try:
    from config import Config
except Exception:
    Config = None

try:
    from coding_library_manager import CodingLibraryManager
except Exception as e:
    logger.warning("导入CodingLibraryManager失败: " + str(e))
    CodingLibraryManager = None

try:
    from semantic_matcher import SemanticMatcher
except Exception as e:
    logger.warning("导入SemanticMatcher失败: " + str(e))
    SemanticMatcher = None

try:
    from high_quality_sample_learner import HighQualitySampleLearner
except Exception as e:
    logger.warning("导入HighQualitySampleLearner失败: " + str(e))
    HighQualitySampleLearner = None


class EnhancedCodingGenerator:
    """增强的扎根理论编码生成器 - 支持训练模型预测"""

    def __init__(self):
        self.min_sentence_length = 5
        self.similarity_threshold = 0.6
        self.max_codes_per_paragraph = 5

        # Config-driven defaults
        self.max_first_level_length = getattr(Config, 'FIRST_LEVEL_CODE_MAX_LENGTH', 30) if Config else 30

        # Caches
        self.abstract_cache = {}
        self.similarity_cache = {}
        self.bad_phrase_patterns = [
            r'[（(]?\d{1,2}:\d{2}[)）]?',
        ]

        # Colloquial-to-formal mapping
        self.colloquial_to_formal = {}

        # Coding quality thresholds
        self.coding_worthy_min_salience = 0.15
        self.coding_worthy_min_length = 6

        # Coding library
        self.coding_library = None
        try:
            if CodingLibraryManager:
                self.coding_library = CodingLibraryManager()
                logger.info("编码库加载成功")
        except Exception as e:
            logger.error("编码库加载失败: " + str(e))

        # Semantic matcher
        self.semantic_matcher = None
        try:
            if SemanticMatcher:
                self.semantic_matcher = SemanticMatcher()
        except Exception as e:
            logger.warning("语义匹配器加载失败: " + str(e))

        # Quality learner
        self.quality_learner = None
        try:
            if HighQualitySampleLearner:
                sample_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          'data', 'quality_samples.json')
                if os.path.exists(sample_path):
                    self.quality_learner = HighQualitySampleLearner()
                    self.quality_learner.load_samples(sample_path)
        except Exception as e:
            logger.warning("质量学习器加载失败: " + str(e))

        # RAG components (lazy init)
        self.rag_enabled = False
        self.runtime_strategy = 'legacy'
        self.rag_matcher = None
        self.decision_policy = None
        self.first_level_clusterer = None
        self.rag_index_manager = None
        self.rag_doc_retriever = None
        self.knn_abstract_generator = None
        self.t5_generative_coder = None

        # Trace/decision metadata
        self._first_level_trace_meta = {}
        self._second_level_decision_meta = {}

        # First-level prototypes and recall bank
        self.first_level_prototypes = []
        self.first_level_recall_bank = {}

        # RAG thresholds
        self.rag_second_level_threshold = self._default_second_threshold()
        self.rag_third_level_threshold = self._default_third_threshold()
        self.rag_cluster_similarity_threshold = self._default_cluster_threshold()

        # Concept anchor index (改进7 - lazy load)
        self.concept_anchor_index = None

        # Anchor frequency tracker for dynamic anti-collapse penalty (Phase 3)
        # Reset per coding session; penalizes over-used anchors via IDF weighting
        self._anchor_frequency = defaultdict(int)
        self._anchor_sentence_count = 0  # total sentences coded in this session

        # Training-data KNN index for concept-aware recall
        # Replaces extractive n-gram generation with embedding-based concept retrieval
        self.knn_train_index = None  # FAISS index over training sentence embeddings
        self.knn_train_anchors = []  # anchor_code for each indexed sentence

        # Alias → canonical anchor mapping (Phase 2 governance)
        self._alias_map = {}  # Loaded from cache/anchor_index/alias_map.json

        # Grounding checker (Phase 4 — anchor quality assurance)
        self.grounding_checker = None  # Lazy-loaded from grounding_checker module

        # Semantic compressor & abstraction controller (Phase 4)
        self._semantic_compressor = None
        self._abstraction_controller = None

        # Contrastive validator (Phase 4 — post-coding quality audit)
        self._contrastive_validator = None

        # Anchor → 二阶 → 三阶 hierarchy mapping (Phase 2 semantic compression)
        self._anchor_hierarchy = {}  # Loaded from data/anchor_hierarchy.json
        self._hierarchy_anchor_names = []  # Keys for semantic fallback lookup
        self._hierarchy_faiss = None  # Lazy-built FAISS index over hierarchy anchors
        self._hierarchy_model = None  # Lazy-loaded bge-small-zh-v1.5 for fallback encoding

        # Load standalone JSON files early — no model dependencies
        self._load_alias_map()
        self._load_anchor_hierarchy()

        # Try to init RAG components
        self._init_rag_components()

    # ── Static utility ──────────────────────────────────────────────────

    @staticmethod
    def _clean_code_prefix(code: str) -> str:
        """Remove leading punctuation from a code string."""
        punctuation_to_remove = "，。！？；：""''（）【】《》　 "
        cleaned = code
        while cleaned and cleaned[0] in punctuation_to_remove:
            cleaned = cleaned[1:]
        return cleaned.strip()

    # ── Default value helpers ───────────────────────────────────────────

    def _ensure_first_level_defaults(self):
        """Ensure first-level coding defaults are set."""
        if not hasattr(self, 'abstract_cache'):
            self.abstract_cache = {}
        if not hasattr(self, 'max_first_level_length'):
            self.max_first_level_length = getattr(Config, 'FIRST_LEVEL_CODE_MAX_LENGTH', 30) if Config else 30
        if not hasattr(self, '_first_level_trace_meta'):
            self._first_level_trace_meta = {}
        if not hasattr(self, 'first_level_prototypes'):
            self.first_level_prototypes = []
        if not hasattr(self, 'bad_phrase_patterns'):
            self.bad_phrase_patterns = [
                r'[（(]?\d{1,2}:\d{2}[)）]?',
            ]
        # Ensure bad_phrase_patterns is a list
        if isinstance(self.bad_phrase_patterns, str):
            self.bad_phrase_patterns = [self.bad_phrase_patterns]
        # Convert items that are sets to lists
        self.bad_phrase_patterns = [
            list(p) if isinstance(p, set) else p
            for p in self.bad_phrase_patterns
        ]

    def _default_second_threshold(self) -> float:
        return float(getattr(Config, 'RAG_SECOND_LEVEL_THRESHOLD', 0.55)) if Config else 0.55

    def _default_third_threshold(self) -> float:
        return float(getattr(Config, 'RAG_THIRD_LEVEL_THRESHOLD', 0.45)) if Config else 0.45

    def _default_cluster_threshold(self) -> float:
        return float(getattr(Config, 'RAG_CLUSTER_SIMILARITY_THRESHOLD', 0.70)) if Config else 0.70

    def _clamp_threshold(self, value, default: float) -> float:
        threshold = float(value) if value is not None else default
        return threshold

    def _ensure_rag_threshold_defaults(self):
        if not hasattr(self, 'rag_second_level_threshold') or self.rag_second_level_threshold is None:
            self.rag_second_level_threshold = self._default_second_threshold()
        if not hasattr(self, 'rag_third_level_threshold') or self.rag_third_level_threshold is None:
            self.rag_third_level_threshold = self._default_third_threshold()
        if not hasattr(self, 'rag_cluster_similarity_threshold') or self.rag_cluster_similarity_threshold is None:
            self.rag_cluster_similarity_threshold = self._default_cluster_threshold()

    def configure_similarity_thresholds(self, second_threshold=None, third_threshold=None,
                                         cluster_threshold=None):
        """Configure manual auto-coding thresholds without changing result schema."""
        self._ensure_rag_threshold_defaults()
        self.rag_second_level_threshold = self._clamp_threshold(
            second_threshold, self._default_second_threshold())
        self.rag_third_level_threshold = self._clamp_threshold(
            third_threshold, self._default_third_threshold())
        self.rag_cluster_similarity_threshold = self._clamp_threshold(
            cluster_threshold, self._default_cluster_threshold())
        if hasattr(self, 'first_level_clusterer') and self.first_level_clusterer:
            self.first_level_clusterer.similarity_threshold = self.rag_cluster_similarity_threshold
        self._rebuild_decision_policy_from_matcher()

    def _apply_similarity_threshold_options(self, coding_thresholds: Dict[str, Any]):
        """Apply threshold fields while leaving runtime options for later stages."""
        threshold_options = {k: v for k, v in (coding_thresholds or {}).items()
                            if k in ('second_level_threshold', 'third_level_threshold', 'cluster_threshold')}
        if threshold_options:
            self.configure_similarity_thresholds(**threshold_options)

    # ── Sentence repair / metadata normalization ────────────────────────

    def _repair_first_level_sentence_detail(self, sentence: dict) -> dict:
        """Normalize source metadata so auto codes can always navigate back to text."""
        detail = dict(sentence) if isinstance(sentence, dict) else {'content': str(sentence)}
        content = str(detail.get('content', detail.get('original_content', '')))
        
        # 从多个字段获取sentence_id
        sentence_id = str(detail.get('sentence_id', '') or detail.get('id', '') or detail.get('text_number', '')).strip()
        
        all_markers = ['sentence_id', 'id', 'content', 'original_content',
                       'speaker', 'source_file', 'source_sheet', 'paragraph_index',
                       'sentence_index', 'manual_first_code', 'text_number']
        content_clean = content.strip()
        detail['content'] = content_clean
        if 'original_content' not in detail:
            detail['original_content'] = content_clean
        
        # 如果sentence_id仍为空，尝试从内容中提取编号（如 [2345]）
        if not sentence_id:
            all_markers_in_content = re.findall(r"\[(\d+)\]", content)
            if all_markers_in_content:
                sentence_id = all_markers_in_content[-1]
                logger.info(f"从内容 '{content[:30]}...' 中提取编号 [{sentence_id}]")
        
        if sentence_id:
            detail['sentence_id'] = sentence_id
            detail['code_id'] = sentence_id
        return detail

    def _first_level_anchor_ratio(self, code_text: str, source_text: str) -> float:
        """Calculate the ratio of characters in code_text sourced from source_text."""
        source_chars = set(source_text)
        code_chars = set(code_text)
        if not code_chars:
            return 0.0
        return len(code_chars & source_chars) / max(1, len(code_chars))

    # ── Quality checks ──────────────────────────────────────────────────

    def _is_low_quality_first_level_code(self, code_text: str, source_text: str = '',
                                          is_knn: bool = False) -> bool:
        """Check if a first-level code is low quality."""
        if not code_text or len(code_text.strip()) < 2:
            return True

        clean = code_text.strip()

        # Length checks
        max_len = getattr(self, 'max_first_level_length', 30)
        if len(clean) > max_len + 5:
            return True
        if len(clean) < 2:
            return True

        # Numeric-only patterns
        if re.match(r'^(?:也就是说|就是说)\s*\d+$', clean):
            return True
        if re.match(r'^(能不能|可不可以|会不会|能不能够|可不可以)', clean):
            return True

        # KNN candidates have less strict anchor ratio requirement
        if not is_knn:
            anchor_ratio = self._first_level_anchor_ratio(clean, source_text)
            if anchor_ratio < 0.4:
                return True

        # Punctuation-only
        if re.match(r'^[\W_]+$', clean):
            return True

        return False

    def _has_first_level_information_cue(self, text: str) -> bool:
        """Check if text contains information-bearing cues."""
        return len(text) >= 4 and not re.match(r'^[嗯啊哦呃哎]+$', text)

    def _looks_semantically_incomplete(self, text: str) -> bool:
        """Check if text looks semantically incomplete."""
        t = text.strip()
        if not t:
            return True
        if re.match(r'^(因为|所以|但是|不过|然后|如果|而且|其实|那个|这个|还是|只是)$', t):
            return True
        if re.match(r'^(因为|所以|但是|不过|然后|如果|而且|其实|那个|这个|还是|只是)', t) and len(t) < 6:
            return True
        if re.search(r'(这个|那个|这个|哪一个|一样|那种|那种|那种)$', t) and len(t) < 8:
            return True
        return False

    def _has_valid_first_level_pos_pattern(self, text: str) -> bool:
        """Check if text has a valid POS pattern for a first-level code."""
        if not text or len(text) < 4:
            return len(text) >= 2 and bool(re.match(r'^[一-鿿]+$', text))

        words = list(pseg.cut(text))
        if not words:
            return False

        # Check for noun phrases
        has_noun = any(
            'n' in (getattr(w, 'flag', '') if hasattr(w, 'flag') else '')
            for w in words
        )
        has_verb = any(
            'v' in (getattr(w, 'flag', '') if hasattr(w, 'flag') else '')
            for w in words
        )

        if has_noun:
            return True
        if has_verb and len(words) >= 2:
            return True
        return False

    def _contains_colloquial_residue(self, text: str) -> bool:
        """Check if text contains colloquial expressions."""
        colloquial_patterns = [
            r'(怎么说呢|就是说|我觉得|相当|要么|非常|挺多的|挺不错的|挺厉害的|挺方便的|挺难的|挺简单的)',
            r'[啦啊吧呀哦唷嗯哎嘿]',
            r'(我的|他们的|我们的|你们的|那种|这种)',
        ]
        for pattern in colloquial_patterns:
            if re.search(pattern, text):
                return True
        return False

    # ── Candidate canonicalization ───────────────────────────────────────

    def _canonicalize_first_level_candidate_rows(self, candidate_rows: List[Dict],
                                                  source_text: str) -> List[Dict]:
        """Canonicalize and filter candidate rows."""
        canonical = []
        seen = set()
        for row in candidate_rows:
            label = row.get('text', '').strip()
            if not label:
                continue
            if label in seen:
                continue
            seen.add(label)

            is_knn = bool(row.get('knn_source') or row.get('anchor_source'))
            is_anchor = bool(row.get('anchor_source'))

            if not is_knn:
                if self._is_low_quality_first_level_code(label, source_text, is_knn=False):
                    continue
                if self._looks_semantically_incomplete(label):
                    continue
                if not self._has_valid_first_level_pos_pattern(label):
                    continue

            canonical.append(row)

        return canonical

    def _split_first_level_candidate_segments(self, text: str) -> List[str]:
        """Split text into candidate segments."""
        parts = re.split(r'[，,。；;：:\n\r]+', text)
        return [p.strip() for p in parts if len(p.strip()) >= 2]

    def _extract_semantic_chunks(self, text: str) -> List[str]:
        """Extract semantic chunk units from text."""
        text = text.strip()
        if not text:
            return []

        # Split by sentence-ending punctuation
        parts = re.split(r'[。！？；，、]', text)
        chunks = [p.strip() for p in parts if len(p.strip()) >= 3]
        if not chunks:
            chunks = [text]
        return chunks

    def _score_first_level_fragment(self, fragment: str, source_text: str) -> float:
        """Score a text fragment for first-level coding suitability."""
        if not fragment or len(fragment.strip()) < 2:
            return -float('inf')

        clean = fragment.strip()
        score = 0.0

        # Length bonus
        if 4 <= len(clean) <= 15:
            score += 2.0
        elif 16 <= len(clean) <= 25:
            score += 1.0

        # Information density
        if self._has_valid_first_level_pos_pattern(clean):
            score += 1.5

        # Action/process patterns
        action_pattern = r'^(追求|推动|加强|提升|完善|优化|实施|制定|执行|监督|协调|统筹|推进|整合|保障|支持|拓展|深化|开展|增强|改进|转变|对接|影响)$'
        if re.match(action_pattern, clean):
            score += 1.0

        # Penalize fragments that end with trailing function words
        if re.search(r'(的事情|的问题|的东西|什么的|之类的)$', clean):
            score -= 2.0

        return score

    def _finalize_first_level_candidate(self, text: str, source_text: str = '',
                                         is_knn: bool = False) -> Optional[str]:
        """Finalize a first-level candidate code."""
        if not text or len(text.strip()) < 2:
            return None

        clean = text.strip()
        clean = self._normalize_candidate_for_first_level(clean)

        if not is_knn:
            if self._is_low_quality_first_level_code(clean, source_text, is_knn=False):
                return None

        # Remove question-like patterns
        if re.search(r'(什么|怎么|哪些|怎么样|如何|的方式|什么时候|什么样)', clean):
            if len(clean) < 8:
                return None

        # Remove trailing particles
        clean = re.sub(r'(了|的|地|得|着|过|在|与|和|及|也|只|就|没)$', '', clean)
        clean = clean.strip()

        if not clean:
            return None

        return clean

    # ── Interpretive Code layer (研究层) ──

    def _generate_interpretive_code(self, anchor_code: str, source_sentence: str) -> str:
        """Generate a human-readable interpretive code (研究层) from an anchor code.

        Per the GOAL architecture:
        - Anchor Code (机器层): short, stable, used for FAISS retrieval/clustering
        - Interpretive Code (研究层): contextualized for human understanding, NOT used for retrieval

        The interpretive code enriches the anchor with key contextual signals from the
        source sentence, forming a bridge between machine concept and human reading.
        """
        if not anchor_code or not source_sentence:
            return anchor_code

        try:
            # Extract key content-bearing words from source sentence
            words = list(jieba.cut(source_sentence))
            _stop = {
                '这个', '那个', '我们', '他们', '你们', '就是', '所以',
                '因为', '但是', '虽然', '如果', '然后', '可以', '需要', '应该',
                '什么', '怎么', '哪些', '怎么样', '如何', '还是', '不过',
                '已经', '而且', '或者', '只有', '只要', '必须', '可能',
                '的', '了', '在', '是', '有', '和', '与', '及', '或',
                '这', '那', '我', '你', '他', '她', '它', '们',
                '吗', '呢', '吧', '啊', '呀', '哦', '哈',
                '不', '没', '都', '也', '就', '才', '还', '又', '再',
            }
            content_words = [w for w in words if len(w) >= 2 and w not in _stop]

            anchor_parts = set(jieba.cut(anchor_code))
            novel_words = [w for w in content_words if w not in anchor_parts]

            if not novel_words:
                return anchor_code

            # Build interpretive: anchor (concept core) + context (situational detail)
            # Use 1-2 most distinctive novel words as context
            context = ''.join(novel_words[:2])
            combined = anchor_code + '：' + context

            # Cap length for display; anchor should dominate
            if len(combined) <= 20:
                return combined
            elif len(anchor_code + '：' + novel_words[0]) <= 16:
                return anchor_code + '：' + novel_words[0]
            else:
                return anchor_code

        except Exception:
            return anchor_code

    def _get_anchor_idf_penalty(self, anchor_name: str) -> float:
        """Dynamic IDF penalty for anti-collapse (Phase 3).

        Penalizes high-frequency anchors so they don't become semantic sinks.
        score = semantic_similarity × idf(anchor) × diversity_penalty

        idf_penalty = max(0.25, 1.0 / (1.0 + alpha * log(1 + freq)))
        where alpha = 0.5 controls penalty strength.

        freq=0 → 1.0 (no penalty), freq=10 → 0.46, freq=324 → 0.26
        Floor at 0.25 prevents complete suppression.
        """
        if not anchor_name:
            return 1.0
        freq = self._anchor_frequency.get(anchor_name, 0)
        if freq <= 0:
            return 1.0
        import math
        alpha = 0.5
        penalty = 1.0 / (1.0 + alpha * math.log(1 + freq))
        return max(0.25, penalty)

    def _ensure_grounding_checker(self):
        """Lazy-init the grounding checker with the embedding model."""
        if self.grounding_checker is not None:
            return
        try:
            from grounding_checker import GroundingChecker
            self.grounding_checker = GroundingChecker()
            # Use semantic_matcher model if available, else try concept_anchor_index
            if hasattr(self, 'semantic_matcher') and self.semantic_matcher:
                self.grounding_checker._set_model(self.semantic_matcher.model)
            elif self.concept_anchor_index is not None:
                self.grounding_checker._set_model(self.concept_anchor_index.model)
        except Exception as e:
            logger.debug("GroundingChecker init skipped: %s", e)

    def _ensure_contrastive_validator(self):
        """Lazy-init the contrastive validator for post-coding quality audit."""
        if self._contrastive_validator is not None:
            return
        try:
            from contrastive_validator import ContrastiveValidator
            self._contrastive_validator = ContrastiveValidator()
            logger.info("ContrastiveValidator loaded for post-coding audit")
        except Exception as e:
            logger.debug("ContrastiveValidator init skipped: %s", e)

    def _run_contrastive_validation(self, first_level_codes: Dict[str, List]) -> dict:
        """Run post-coding contrastive validation on first-level results.

        Validates interpretability, semantic drift, and adsorption risk.
        Returns a validation report dict; empty dict if validator unavailable.
        """
        self._ensure_contrastive_validator()
        if self._contrastive_validator is None:
            return {}

        # Convert first_level_codes dict to flat results list with 'code' and 'original'
        results = []
        for second_name, items in first_level_codes.items():
            for item in items:
                if isinstance(item, dict):
                    sent = item.get('original') or item.get('sentence') or item.get('text') or ''
                    code = item.get('code') or ''
                    candidates = item.get('top3_candidates') or item.get('candidates') or []
                elif isinstance(item, str):
                    sent = item
                    code = ''
                else:
                    continue
                if sent and code:
                    results.append({
                        'code': code,
                        'original': sent,
                        'top3_candidates': candidates,
                    })

        if not results:
            logger.info("Contrastive validation: no sentence-anchor pairs to validate")
            return {}

        try:
            validation = self._contrastive_validator.validate_results(results)
            report = self._contrastive_validator.generate_report(validation)
            logger.info("Contrastive validation complete:\n%s", report)
            return validation
        except Exception as e:
            logger.warning("Contrastive validation failed: %s", e)
            return {}

    def _conservative_first_level_rank_score(self, row: Dict) -> float:
        """Blend rerank confidence with a short/focused phrase preference.

        Anchor candidates (from FAISS concept_anchor retrieval) use the
        fine-tuned model's similarity score as the primary component.
        Extractive n-gram candidates have keyword-counting weight reduced
        to prevent fragment inflation from outscoring semantic anchors.
        """
        text = row.get('text', '').strip()
        source_text = row.get('source_text', row.get('raw_text', ''))

        if not text:
            return -float('inf')

        is_anchor = bool(row.get('anchor_source'))
        anchor_score = row.get('anchor_score')

        # ── Anchor candidates: FAISS concept-model similarity is primary ──
        if is_anchor and anchor_score is not None and anchor_score > 0:
            # Steeper slope: weak anchors (0.35) compete fairly with extractive
            # candidates (~6.5); strong anchors (0.70+) still dominate (11.7+).
            score = 4.0 + anchor_score * 11.0
            L = len(text)
            if 4 <= L <= 12:
                score += 1.5
            elif 13 <= L <= 20:
                score += 0.5
            # Phase 3: Dynamic IDF penalty to prevent semantic collapse
            idf_penalty = self._get_anchor_idf_penalty(text)
            if idf_penalty < 1.0:
                score = score * idf_penalty
            # Phase 4: Grounding & polarity checks
            if source_text and text:
                self._ensure_grounding_checker()
                if self.grounding_checker is not None:
                    gs = self.grounding_checker.grounding_score(source_text, text)
                    is_pol_violation, _ = self.grounding_checker.check_polarity(source_text, text)
                    # Grounding penalty: poorly grounded anchors lose up to 30% score
                    if gs < 0.40:
                        score *= 0.70
                    elif gs < 0.55:
                        score *= 0.85
                    elif gs < 0.70:
                        score *= 0.95
                    # Polarity violation: severe penalty
                    if is_pol_violation:
                        score *= 0.40
                # Proportional penalty for anchors below gating threshold (0.55).
                # Anchors near 0.40 get heavy penalty → extractive candidates win.
                # Anchors near 0.55 get light penalty → still competitive.
                if anchor_score is not None and anchor_score < 0.55:
                    # 0.40 → 0.45x,  0.475 → 0.725x,  0.55 → 1.0x
                    penalty = 0.45 + (anchor_score - 0.40) / 0.15 * 0.55
                    score *= max(0.45, min(1.0, penalty))
            return round(score, 4)

        # ── Extractive / recall candidates ──
        base = float(row.get('rule_score', 6.0))
        rerank = row.get('rerank_score')
        concept_sim = row.get('concept_sim')

        if rerank is not None and rerank > 0:
            score = base * 0.35 + float(rerank) * 0.65
        else:
            score = base * 0.5

        # Concept-model semantic similarity: penalizes fragments, rewards concepts
        if concept_sim is not None and concept_sim > 0:
            score += concept_sim * 5.0

        # Length bonus: prefer compact codes
        L = len(text)
        if 4 <= L <= 12:
            score += 1.5
        elif 13 <= L <= 20:
            score += 0.5
        elif L > 30:
            score -= 2.0

        # Anchor ratio bonus (reduced weight — concept codes naturally
        # have lower n-gram overlap with source text)
        if source_text:
            anchor_ratio = self._first_level_anchor_ratio(text, source_text)
            score += anchor_ratio * 2.0

        # KNN / recall-label bonus
        is_knn = bool(row.get('knn_source') or row.get('anchor_source'))
        if is_knn:
            score += 1.0

        return round(score, 4)

    def _model_semantic_similarity(self, a: str, b: str) -> float:
        """Calculate semantic similarity between two strings using the model."""
        if not hasattr(self, 'semantic_matcher') or self.semantic_matcher is None:
            return -1.0
        try:
            emb_a = self.semantic_matcher.get_embedding(a)
            emb_b = self.semantic_matcher.get_embedding(b)
            if emb_a is None or emb_b is None:
                return -1.0
            return float(np.dot(emb_a, emb_b) / (np.linalg.norm(emb_a) * np.linalg.norm(emb_b) + 1e-8))
        except Exception:
            return -1.0

    def _concept_model_similarity(self, a: str, b: str) -> float:
        """Semantic similarity using the fine-tuned concept_anchor model.

        The concept_anchor model was trained with contrastive learning
        (MultipleNegativesRankingLoss) specifically to score concept-label
        relevance to sentences — it discriminates correct vs incorrect
        codes far better than the base bge-small-zh-v1.5 model.
        """
        try:
            if self.concept_anchor_index is None:
                return -1.0
            model = self.concept_anchor_index.model
            emb_a = model.encode([a], normalize_embeddings=True, show_progress_bar=False)[0]
            emb_b = model.encode([b], normalize_embeddings=True, show_progress_bar=False)[0]
            return float(np.dot(emb_a, emb_b))
        except Exception:
            return -1.0

    def _select_quality_first_level_candidate(self, trace: Dict,
                                               source_detail: Dict) -> Optional[str]:
        """Select the best quality first-level candidate from trace."""
        candidates = trace.get('candidates', [])
        if not candidates:
            return None

        original_content = source_detail.get('original_content',
                                              source_detail.get('content', ''))

        # Sort by conservative_score
        scored = []
        for c in candidates:
            text = str(c.get('text', '')).strip()
            if not text or len(text) < 2:
                continue
            cons = c.get('conservative_score', c.get('rule_score', 0))
            scored.append((cons, text, c))

        scored.sort(key=lambda x: x[0], reverse=True)

        if not scored:
            return None

        # Take the highest scoring candidate
        best_cons, best_text, best_row = scored[0]

        # Validate semantic fit
        if original_content and len(original_content) > 5:
            if not self._validate_code_semantic_fit(best_text, original_content):
                # Try next best
                for alt_cons, alt_text, alt_row in scored[1:4]:
                    if self._validate_code_semantic_fit(alt_text, original_content):
                        return alt_text

        return self._finalize_first_level_candidate(best_text, original_content,
                                                     is_knn=bool(best_row.get('knn_source') or best_row.get('anchor_source')))

    def _validate_code_semantic_fit(self, code: str, source_text: str) -> bool:
        """Validate that a code semantically fits the source text."""
        similarity = self._model_semantic_similarity(code, source_text)
        if similarity < 0:
            return True  # Model unavailable, accept by default
        if similarity < 0.25:
            logger.info("模型验证拒绝: '%s' 与原句相似度不足 (%.3f)", code, similarity)
            return False
        return True

    # ── Prototypes and recall ────────────────────────────────────────────

    def _rebuild_decision_policy_from_matcher(self):
        """Rebuild decision policy from current matcher state."""
        pass  # Implemented when RAG matcher is active

    def set_first_level_prototypes(self, prototypes: List[Dict]):
        """Set first-level prototype codes."""
        self.first_level_prototypes = [
            p for p in prototypes
            if p.get('manual_first_code', '').strip()
        ]

    def set_first_level_recall_bank(self, labels: List[Dict], model_manager=None):
        """Set the recall bank for semantic recall."""
        self.first_level_recall_bank = {}
        for item in (labels or []):
            sentence = item.get('sentence', item.get('content', ''))
            code = item.get('manual_first_code', item.get('code', ''))
            if sentence and code:
                if sentence not in self.first_level_recall_bank:
                    self.first_level_recall_bank[sentence] = []
                self.first_level_recall_bank[sentence].append(code)

    def _semantic_recall_first_level_labels(self, text: str, model_manager=None,
                                             top_n: int = 5,
                                             min_score: float = 0.55) -> List[str]:
        """Semantically recall first-level labels from the recall bank."""
        if not self.first_level_recall_bank or model_manager is None:
            return []

        def lexical_hits():
            """Fast keyword-based recall."""
            text_lower = text.lower()
            # Build keyword sets from recall bank
            recall_keywords = set()
            for sentence in self.first_level_recall_bank:
                for w in jieba.cut(sentence):
                    if len(w) >= 2:
                        recall_keywords.add(w)

            text_keywords = set(w for w in jieba.cut(text) if len(w) >= 2)

            # Find matching sentences
            matches = []
            for sentence, codes in self.first_level_recall_bank.items():
                sent_words = set(w for w in jieba.cut(sentence) if len(w) >= 2)
                overlap = len(text_keywords & sent_words)
                if overlap >= 2:
                    for code in codes:
                        matches.append((overlap, code))
            matches.sort(key=lambda x: x[0], reverse=True)
            return [code for _, code in matches[:top_n]]

        hits = lexical_hits()
        return list(dict.fromkeys(hits))[:top_n]

    def _prototype_keywords(self, manual_code: str) -> Set[str]:
        """Extract keywords from a prototype manual code."""
        return set(w for w in jieba.cut(manual_code) if len(w) >= 2)

    def _prototype_similarity(self, text: str, prototype: Dict) -> float:
        """Calculate similarity between text and a prototype."""
        source = prototype.get('source', prototype.get('sentence', ''))
        manual_code = prototype.get('manual_first_code', '')
        if not source or not manual_code:
            return 0.0

        if hasattr(self, 'semantic_matcher') and self.semantic_matcher:
            try:
                emb_text = self.semantic_matcher.get_embedding(text)
                emb_proto = self.semantic_matcher.get_embedding(manual_code)
                if emb_text is not None and emb_proto is not None:
                    return float(np.dot(emb_text, emb_proto) /
                                (np.linalg.norm(emb_text) * np.linalg.norm(emb_proto) + 1e-8))
            except Exception:
                pass
        return 0.0

    def _find_first_level_prototype_hits(self, text: str, top_k: int = 3) -> List[Dict]:
        """Find prototype hits for a text."""
        if not self.first_level_prototypes:
            return []

        scored = []
        for proto in self.first_level_prototypes:
            sim = self._prototype_similarity(text, proto)
            if sim > 0.3:
                scored.append({
                    'prototype': proto,
                    'similarity': sim,
                    'manual_first_code': proto.get('manual_first_code', ''),
                    'source': proto.get('source', proto.get('sentence', '')),
                })

        scored.sort(key=lambda x: x['similarity'], reverse=True)
        return scored[:top_k]

    # ── Trace metadata management ──────────────────────────────────────

    def reset_first_level_trace_meta(self):
        self._ensure_first_level_defaults()
        self._first_level_trace_meta = {}

    def get_first_level_trace_meta(self):
        self._ensure_first_level_defaults()
        return dict(self._first_level_trace_meta)

    def _store_first_level_trace(self, code_key: str, trace: Dict):
        self._ensure_first_level_defaults()
        compact = {}
        for key in ('selected_candidate', 'interpretive_code', 'best_rule_candidate',
                     'used_rerank', 'anchor_selected', 'anchor_source', 'candidates',
                     'grounding', 'provenance', 'hierarchy'):
            if key in trace:
                v = trace[key]
                if key == 'candidates':
                    v = [
                        {
                            'text': c.get('text', ''),
                            'rule_score': c.get('rule_score'),
                            'conservative_score': c.get('conservative_score'),
                            'rerank_score': c.get('rerank_score'),
                            'anchor_source': c.get('anchor_source', ''),
                            'anchor_score': c.get('anchor_score'),
                            'selected': c.get('selected', False),
                        }
                        for c in (v or [])
                    ]
                compact[key] = v
        self._first_level_trace_meta[code_key] = compact

    # ── Core: first-level candidate trace building ─────────────────────

    def _normalize_sentence_for_coding(self, sentence) -> tuple:
        """Normalize a sentence for first-level coding.

        Returns (normalized_text, original_text) or (None, original_text) if too short.
        Extracted from build_first_level_candidate_trace for reuse in batch pre-encoding.
        """
        if not isinstance(sentence, dict):
            original = str(sentence).strip()
        else:
            original = str(sentence.get('content', sentence.get('original_content', ''))).strip()

        if not original or len(original) < 3:
            return None, original

        normalized = original
        # Strip speaker labels
        normalized = re.sub(
            r'^(?:[A-Za-z]|受访者|采访者|访谈员|说话人\s*\d+|弄管家\s*\d*|游客\s*\d*|'
            r'非遗手艺人\s*\d*|非遗人\s*\d*|管理层\s*\d*|景漂\s*\d*|老师\s*\d*|'
            r'主持人|记者|受访者|嘉宾|专家|居民\s*\d*|商户\s*\d*|'
            r'手艺人\s*\d*|学徒\s*\d*|传承人\s*\d*|问|答|Q|A)\s*[：:]?\s*',
            '', normalized)

        # Clean artifact markers and character repetitions
        normalized = re.sub(r'\[[A-Z]?\d+\]', '', normalized)
        normalized = re.sub(r'(\w)\1{2,}', r'\1', normalized)
        normalized = self._normalize_source_sentence(normalized)

        if not normalized or len(normalized) < 3:
            return None, original

        return normalized, original

    def build_first_level_candidate_trace(self, sentence, model_manager,
                                           top_n: int = 8,
                                           defer_rerank: bool = False,
                                           cached_embedding=None,
                                           cached_anchor_results=None,
                                           cached_knn_results=None) -> Dict:
        """Return a compact candidate trace for first-level abstraction.

        Implements concept anchor gating (改进7):
        1. Run FAISS anchor retrieval on the normalized sentence
        2. If max anchor score >= 0.35, skip extractive n-gram generation
        3. Otherwise, fall back to extractive n-gram pipeline

        When cached_embedding / cached_anchor_results / cached_knn_results are
        provided (from batch pre-encoding), the per-sentence model.encode()
        calls are skipped — this gives ~100x speedup for multi-file coding.
        """
        self._ensure_first_level_defaults()

        # ── Normalize sentence ──
        normalized, original = self._normalize_sentence_for_coding(sentence)
        if normalized is None:
            return {}

        # ── Prototype hits ──
        prototype_hits = self._find_first_level_prototype_hits(normalized)
        prototype_keywords = set()
        for hit in prototype_hits:
            prototype_keywords.update(
                self._prototype_keywords(hit.get('manual_first_code', '')))

        # ── Salience ──
        salience = self._compute_salience(normalized)

        # ── RAG context terms ──
        rag_context_terms = []
        if hasattr(self, 'rag_doc_retriever') and self.rag_doc_retriever is not None:
            try:
                rag_chunks = self.rag_doc_retriever.retrieve(normalized, 3, 0.5)
                for chunk in rag_chunks:
                    chunk_terms = self._extract_domain_terms_from_text(
                        chunk.get('text', ''))
                    rag_context_terms.extend(chunk_terms)
                if rag_context_terms:
                    rag_context_terms = list(dict.fromkeys(rag_context_terms))
            except Exception:
                pass

        # ── Should skip? ──
        if self._should_skip_sentence_for_coding(normalized, salience):
            return {}

        # ── Config ──
        target_length = getattr(Config, 'MAX_SENTENCE_LENGTH', 512) if Config else 512
        max_len = getattr(self, 'max_first_level_length',
                          getattr(Config, 'FIRST_LEVEL_CODE_MAX_LENGTH', 30) if Config else 30)
        if not isinstance(max_len, int) or max_len <= 0:
            max_len = 30
        length_budget = min(max_len * 2, 35)

        recall_enhanced = bool(getattr(Config, 'FIRST_LEVEL_RECALL_ENHANCED', True)) if Config else True
        base_max_span = int(getattr(Config, 'FIRST_LEVEL_BASE_MAX_SPAN', 8)) if Config else 8
        enhanced_max_span = int(getattr(Config, 'FIRST_LEVEL_ENHANCED_MAX_SPAN', 12)) if Config else 12

        # Focus markers and professional terms
        focus_markers = (
            '第一次', '首次', '然而', '最终', '但是', '不过', '却',
            '更', '更加', '最', '最高', '最低', '核心', '关键',
            '尤其', '特别', '主要', '重点',
        )
        professional_terms = (
            '技术', '资源', '平台', '机制', '流程', '生态', '需求', '风险',
            '压力', '冲突', '协同', '合作', '创新', '服务', '模块', '设备',
            '系统', '客户', '团队', '品牌', '治理', '监督', '审批', '架构',
            '算法', '数据', '能力', '知识', '资本', '绩效', '战略', '路径',
            '场景', '农业', '农村', '种植', '养殖', '灌溉', '施肥', '收割',
            '农机', '农产品', '粮食', '果蔬', '畜牧', '渔业', '农户', '合作社',
            '产量', '品种', '有机', '绿色食品', '非遗', '手艺', '技艺', '传承人',
            '工匠', '作坊', '文创', '手工艺', '陶艺', '织造', '雕刻', '刺绣',
            '民俗', '古建筑', '修缮', '文保', '文物', '医疗', '诊疗', '康复',
            '护理', '患者', '医保', '药品', '临床', '公共卫生', '基层医疗',
            '健康管理', '中医', '慢病', '教育', '教学', '课程', '师资', '学员',
            '教材', '考核', '素质教育', '职业教育', '技能培训', '校企合作',
            '在线教育', '社区', '公益', '民生', '基层', '社会组织', '志愿服务',
            '公共空间', '社区营造', '城市更新', '旧改', '可持续', '赋能',
            '电商', '直播', '流量', '运营', '供应链', '渠道', '营销', '转化',
            '复购', '文旅', '景区', '游客', '民宿', '网红', '文旅融合', '打卡',
        )

        # ── Nested helper functions ──

        def strip_punct(value: str) -> str:
            return value.strip().strip('，。！？；：""''（）【】《》　 ')

        def looks_like_fragment(raw_text: str, clean_text: str) -> bool:
            if len(clean_text) < 3:
                return True
            if re.search(r'(尤其是|比如|就像|如同|好像|似乎|看上去|好像)', raw_text):
                return True
            return False

        def score_candidate(clean_text: str, raw_text: str) -> float:
            if not clean_text or len(clean_text) < 2:
                return -float('inf')

            score = 6.0  # base

            # Length bonus
            L = len(clean_text)
            if 4 <= L <= 12:
                score += 2.5
            elif 13 <= L <= 20:
                score += 1.5
            elif L > 35:
                score -= 3.0

            # Professional terms
            prof_hits = sum(1 for t in professional_terms if t in clean_text)
            score += min(prof_hits * 1.5, 4.5)

            # Focus markers
            focus_hits = sum(1 for m in focus_markers if m in clean_text)
            score += min(focus_hits * 1.0, 2.0)

            # Prototype keywords
            proto_hits = sum(1 for kw in prototype_keywords if kw in clean_text)
            score += min(proto_hits * 0.8, 2.0)

            # RAG context
            rag_hits = sum(1 for term in rag_context_terms if term in clean_text)
            score += min(rag_hits * 1.5, 3.0)

            # POS check
            if self._has_valid_first_level_pos_pattern(clean_text):
                score += 1.5

            # Fragment check
            if looks_like_fragment(raw_text, clean_text):
                score -= 2.5

            # Colloquial check
            if self._contains_colloquial_residue(clean_text):
                score -= 2.0

            # Anchor ratio
            score += self._first_level_anchor_ratio(clean_text, normalized) * 2.0

            return round(score, 4)

        # ── Concessive/negated span detection ──
        concessive_spans = self._detect_concessive_spans(normalized)
        negated_spans = self._detect_negated_spans(normalized)

        # ═══════════════════════════════════════════════════════════════
        # 改进7: CONCEPT ANCHOR GATING
        # Run anchor retrieval BEFORE extractive n-gram generation.
        # If we get a strong anchor match (>= 0.35), skip extractive.
        # ═══════════════════════════════════════════════════════════════

        anchor_gated = False
        anchor_max_score = 0.0
        _anchor_candidates: List[Tuple[str, float, str]] = []

        # Use cached anchor results from batch pre-encoding when available
        if cached_anchor_results is not None:
            _anchor_candidates = cached_anchor_results
            if _anchor_candidates:
                anchor_max_score = _anchor_candidates[0][1]
                anchor_gated = anchor_max_score >= 0.42
        elif self._ensure_anchor_index() and self.concept_anchor_index is not None:
            try:
                _anchor_candidates = self.concept_anchor_index.search(normalized, top_k=50)
                if _anchor_candidates:
                    anchor_max_score = _anchor_candidates[0][1]
                    # Only gate when anchors are genuinely strong (0.55+).
                    # Medium anchors (0.40-0.55) compete fairly with
                    # extractive candidates from the source text.
                    anchor_gated = anchor_max_score >= 0.55
            except Exception:
                pass

        # ── Split into sentence parts ──
        sentence_parts = [p.strip() for p in re.split(r'[。！？;；]', normalized) if len(p.strip()) >= 3]
        if not sentence_parts:
            sentence_parts = [normalized]

        candidate_rows: List[Dict] = []
        seen: Dict[str, int] = {}

        # ── Phase 1: Inject anchor candidates ──
        _anchors_injected = 0
        for concept_name, anchor_score, anchor_source in _anchor_candidates:
            if anchor_score < 0.40:
                continue
            label = self._normalize_candidate_for_first_level(concept_name)
            if not label or len(label) < 2:
                continue
            # Normalize to canonical anchor (Phase 2 governance)
            canonical = self._alias_map.get(concept_name, concept_name)
            if canonical != concept_name:
                label = self._normalize_candidate_for_first_level(canonical)
                if not label or len(label) < 2:
                    continue
            _anchors_injected += 1

            anchor_rule = round(6.5 + anchor_score * 4.5, 4)
            anchor_cons = round(min(anchor_rule, 12.0) * 0.5 + anchor_score * 2.0, 4)

            row = {
                'text': label,
                'raw_text': normalized,
                'rule_score': anchor_rule,
                'rerank_score': None,
                'conservative_score': anchor_cons,
                'selected': False,
                'best_rule': False,
                'anchor_source': anchor_source,
                'anchor_score': round(anchor_score, 4),
                'prototype_hits': prototype_hits,
            }

            existing = seen.get(label)
            if existing is None:
                seen[label] = len(candidate_rows)
                candidate_rows.append(row)
            elif row['rule_score'] > candidate_rows[existing]['rule_score']:
                candidate_rows[existing] = row

        # If too few anchors survived filtering, un-gate to allow extractive backup.
        # With top_k=50, insufficient quality anchors means concepts are weak for this sentence.
        if anchor_gated and _anchors_injected < 5:
            anchor_gated = False

        # ── Phase 2: Concept-aware KNN expansion (complements extractive n-grams) ──
        # When FAISS anchors are weak, find similar training sentences via embedding
        # KNN and retrieve their anchor codes as concept candidates.
        # Extractive candidates are now generated in Phase 2b below (not replaced).
        if not anchor_gated:
            if self._ensure_knn_train_index() and self.knn_train_index is not None:
                try:
                    # Use cached embedding / KNN results from batch pre-encoding
                    if cached_knn_results is not None:
                        knn_scores, knn_indices = cached_knn_results
                        knn_scores = np.array([knn_scores]) if knn_scores.ndim == 1 else knn_scores
                        knn_indices = np.array([knn_indices]) if knn_indices.ndim == 1 else knn_indices
                    elif cached_embedding is not None:
                        knn_scores, knn_indices = self.knn_train_index.search(
                            cached_embedding, 10)
                    else:
                        q_emb = self.concept_anchor_index.model.encode(
                            [normalized], normalize_embeddings=True,
                            show_progress_bar=False).astype(np.float32)
                        knn_scores, knn_indices = self.knn_train_index.search(q_emb, 10)

                    _knn_added = 0
                    for score, idx in zip(knn_scores[0], knn_indices[0]):
                        if idx < 0 or idx >= len(self.knn_train_anchors):
                            continue
                        if float(score) < 0.30:
                            continue
                        anchor = self.knn_train_anchors[idx]
                        if not anchor or anchor in seen:
                            continue

                        # Normalize to canonical anchor (Phase 2 governance)
                        anchor = self._alias_map.get(anchor, anchor)

                        label = self._normalize_candidate_for_first_level(anchor)
                        if not label or len(label) < 2:
                            continue

                        knn_rule = round(6.0 + float(score) * 4.0, 4)
                        knn_cons = round(min(knn_rule, 12.0) * 0.5 + float(score) * 1.5, 4)

                        row = {
                            'text': label,
                            'raw_text': normalized,
                            'rule_score': knn_rule,
                            'rerank_score': None,
                            'conservative_score': knn_cons,
                            'selected': False,
                            'best_rule': False,
                            'anchor_source': 'knn_recall',
                            'anchor_score': round(float(score), 4),
                            'prototype_hits': prototype_hits,
                        }

                        seen[label] = len(candidate_rows)
                        candidate_rows.append(row)
                        _knn_added += 1

                    if _knn_added > 0:
                        logger.debug("KNN concept recall: %d candidates", _knn_added)
                except Exception as e:
                    logger.debug("KNN concept recall failed: %s", e)

        # ── Phase 2b: Extractive candidates from source text ──
        # Generate candidates from the sentence text itself to maintain
        # connection to original text. These complement anchor/KNN candidates
        # and participate in the same scoring/selection pipeline.
        # Runs regardless of anchor_gated to ensure text-derived candidates
        # always compete alongside external knowledge sources.
        _extractive_added = 0
        _extractive_max = 15  # per-sentence cap to avoid bloat
        for sentence_part in sentence_parts:
            if _extractive_added >= _extractive_max:
                break
            segments = self._split_first_level_candidate_segments(sentence_part)
            for seg in segments:
                if _extractive_added >= _extractive_max:
                    break
                if seg in seen or len(seg) < 2:
                    continue
                label = self._normalize_candidate_for_first_level(seg)
                if not label or len(label) < 2 or label in seen:
                    continue
                if self._contains_colloquial_residue(label):
                    continue

                frag_score = self._score_first_level_fragment(label, normalized)
                if frag_score <= 0:
                    continue

                # Map fragment score to comparable rule_score range.
                # Slightly lower base than anchors to compensate for the
                # concept_sim boost extractive candidates receive later.
                extractive_rule = round(5.0 + frag_score * 0.8, 4)
                # Bonus for prototype keyword overlap — rewards candidates that
                # match known concepts while keeping text-derived phrasing.
                proto_hits = sum(1 for kw in prototype_keywords if kw in label)
                extractive_rule += min(proto_hits * 0.6, 2.0)
                extractive_cons = round(min(extractive_rule, 12.0) * 0.55, 4)

                row = {
                    'text': label,
                    'raw_text': normalized,
                    'rule_score': extractive_rule,
                    'rerank_score': None,
                    'conservative_score': extractive_cons,
                    'selected': False,
                    'best_rule': False,
                    'anchor_source': None,
                    'anchor_score': None,
                    'prototype_hits': prototype_hits,
                }

                seen[label] = len(candidate_rows)
                candidate_rows.append(row)
                _extractive_added += 1

        if _extractive_added > 0:
            logger.debug("Extractive recall: %d candidates from source text", _extractive_added)

        # ── Canonicalize ──
        candidate_rows = self._canonicalize_first_level_candidate_rows(
            candidate_rows, normalized)

        if not candidate_rows:
            return {}

        # ── Batch concept-model similarity for extractive candidates ──
        # Use the fine-tuned concept_anchor model to score every candidate
        # against the source sentence. This penalizes sentence fragments
        # ("主要是", "获得3张") that have low semantic relevance and rewards
        # concept-like candidates even if they come from extractive n-grams.
        _non_anchor_indices = [
            i for i, r in enumerate(candidate_rows)
            if not r.get('anchor_source') and not r.get('anchor_score')
        ]
        if _non_anchor_indices and hasattr(self, 'concept_anchor_index') and self.concept_anchor_index is not None:
            try:
                _non_anchor_texts = [candidate_rows[i]['text'] for i in _non_anchor_indices]
                _all_encode = [normalized] + _non_anchor_texts
                _embs = self.concept_anchor_index.model.encode(
                    _all_encode, normalize_embeddings=True,
                    show_progress_bar=False, batch_size=len(_all_encode))
                _source_emb = _embs[0]
                _cand_embs = _embs[1:]
                for j, i in enumerate(_non_anchor_indices):
                    sim = float(np.dot(_source_emb, _cand_embs[j]))
                    candidate_rows[i]['concept_sim'] = round(sim, 4)
            except Exception:
                pass

        # ── Recompute conservative scores ──
        for row in candidate_rows:
            row['conservative_score'] = self._conservative_first_level_rank_score(row)

        # ── Re-rank ──
        if not defer_rerank:
            candidate_rows = self._rerank_candidate_rows_for_trace(
                candidate_rows, normalized)

        # Recompute conservative scores now that rerank_score is populated
        for row in candidate_rows:
            row['conservative_score'] = self._conservative_first_level_rank_score(row)

        # ── Sort by conservative score ──
        candidate_rows.sort(key=lambda r: r.get('conservative_score', 0), reverse=True)

        # ── Select the top candidate by blended conservative_score ──
        if candidate_rows:
            selected_candidate = candidate_rows[0].get('text', '')
        else:
            selected_candidate = ''

        if not selected_candidate:
            return {}

        # ── Concept-model semantic validation ──
        # If the top candidate is an extractive fragment (not an anchor),
        # verify it truly matches the source sentence using the fine-tuned
        # concept_anchor model. If similarity is low, scan alternatives
        # for a better semantic fit. Uses pre-computed concept_sim from
        # the batch encoding step above.
        _top_row = candidate_rows[0]
        if not _top_row.get('anchor_source'):
            try:
                _top_sim = _top_row.get('concept_sim', 0)
                if _top_sim < 0.35:
                    for _alt in candidate_rows[1:min(8, len(candidate_rows))]:
                        _alt_text = _alt.get('text', '')
                        if not _alt_text:
                            continue
                        _alt_sim = _alt.get('concept_sim', 0)
                        if _alt_sim > _top_sim + 0.05:
                            logger.debug(
                                "Concept validation: replaced '%s' (sim=%.3f) → '%s' (sim=%.3f)",
                                selected_candidate, _top_sim, _alt_text, _alt_sim)
                            selected_candidate = _alt_text
                            _top_row = _alt
                            break
            except Exception:
                pass

        # Mark selected
        for row in candidate_rows:
            if row.get('text') == selected_candidate:
                row['selected'] = True
                row['best_rule'] = True
                break

        # Track anchor selection
        _selected_row = next((r for r in candidate_rows if r.get('text') == selected_candidate), None)
        _selected_is_knn = bool(
            (_selected_row.get('knn_source') if _selected_row else False) or
            (_selected_row.get('anchor_source') if _selected_row else False)
        )
        _selected_is_anchor = bool(_selected_row.get('anchor_source')) if _selected_row else False
        _anchor_selected = _selected_is_anchor
        _anchor_source = (_selected_row.get('anchor_source', '') if _selected_row else '')

        # Finalize
        selected_candidate = self._finalize_first_level_candidate(
            selected_candidate, normalized, is_knn=_selected_is_knn)

        if not selected_candidate:
            return {}

        # Phase 3: Update anchor frequency for anti-collapse IDF penalty
        self._anchor_frequency[selected_candidate] += 1
        self._anchor_sentence_count += 1

        # Phase 4: Grounding assessment + Provenance Chain for observability
        _grounding_verdict = None
        _provenance_chain = None
        _top_candidate_names = [r.get('text', '') for r in candidate_rows[:5]]
        self._ensure_grounding_checker()
        if self.grounding_checker is not None:
            _grounding_verdict = self.grounding_checker.grounding_verdict(
                normalized, selected_candidate)
            # Priority 1.4: Full provenance chain for auditability
            _provenance_chain = self.grounding_checker.provenance_chain(
                normalized, selected_candidate, _top_candidate_names)

        # Phase 4: Hierarchy enrichment — look up L2/L3 from anchor_hierarchy
        _hierarchy = self._enrich_with_hierarchy(selected_candidate)

        # ── Build trace ──
        # Generate interpretive code (研究层) for human readability
        _interpretive = self._generate_interpretive_code(selected_candidate, normalized)

        trace = {
            'selected_candidate': selected_candidate,
            'interpretive_code': _interpretive,
            'best_rule_candidate': selected_candidate,
            'used_rerank': bool((candidate_rows[0].get('rerank_score') or 0) > 0) if candidate_rows else False,
            'anchor_selected': _anchor_selected,
            'anchor_source': _anchor_source,
            'candidates': candidate_rows[:(top_n if top_n else 15)],
            'normalized': normalized,
            'salience': salience,
            'grounding': _grounding_verdict,  # Phase 4: grounding quality assessment
            'provenance': _provenance_chain,  # Phase 4: full provenance chain (Priority 1.4)
            'hierarchy': _hierarchy,  # Priority 7: L2 theme + L3 theory mapping
        }

        return trace

    # ── Code rewriting ─────────────────────────────────────────────────

    def rewrite_first_level_code(self, text: str) -> str:
        """Clean a selected first-level code into a shorter coding phrase."""
        if not text:
            return ''

        clean = text.strip()

        # Remove embedded question marks within Chinese text
        clean = re.sub(r'(?<=[一-鿿])\?(?=[一-鿿])', '', clean)

        # Remove leading numbered markers
        clean = re.sub(
            r'^\s*[①-⑳❶-❿⓵-⓾㉑-㉟①②③④⑤⑥⑦⑧⑨⑩]\s*',
            '', clean)
        clean = re.sub(r'^\s*(?:\d+|[一二三四五六七八九十]+)[、\.．\)]\s*', '', clean)

        # Remove casual endings
        clean = re.sub(r'(什么的|之类的|那种感觉|这种感觉|这样子|那样子|怎么说呢|就是说)$', '', clean)
        clean = re.sub(r'[吧呢啊嘛呀哦哈哎诶噢呃]+$', '', clean)
        clean = re.sub(r'的(\w{2,4})$', r'\1', clean)

        # Fix verb-induced fragments
        clean = re.sub(r'把(.{2,12})(?:聚集|聚拢|吸引)(?:过来|过去|来)', r'吸引\1', clean)

        # Remove leading pronouns
        clean = re.sub(r'^[我我们你你们他他们它它们大家]*(?:也|还是|都|就|会|要|能)?', '', clean)
        clean = clean.strip()

        if not clean:
            clean = text.strip()

        return clean

    # ── Re-ranking ─────────────────────────────────────────────────────

    def _rerank_candidate_rows_for_trace(self, candidates: List[Dict],
                                          normalized_sentence: str) -> List[Dict]:
        """Re-rank candidate rows using the fine-tuned concept_anchor model.

        Falls back to base bge model (semantic_matcher) if the fine-tuned
        model is not loaded. The concept_anchor model was trained with
        contrastive learning to discriminate correct vs incorrect concept
        labels for a given sentence.
        """
        if not candidates:
            return candidates

        # Prefer fine-tuned concept_anchor model; fall back to base bge
        use_concept_model = (hasattr(self, 'concept_anchor_index')
                            and self.concept_anchor_index is not None)
        if not use_concept_model:
            if not hasattr(self, 'semantic_matcher') or not self.semantic_matcher:
                return candidates

        try:
            texts = [c.get('text', '') for c in candidates]
            if not any(texts):
                return candidates

            for i, row in enumerate(candidates):
                text = row.get('text', '')
                if text and len(text) >= 2:
                    if use_concept_model:
                        sim = self._concept_model_similarity(text, normalized_sentence)
                    else:
                        sim = self._model_semantic_similarity(text, normalized_sentence)
                    if sim > 0:
                        row['rerank_score'] = round(sim * 10.0, 4)
        except Exception:
            pass

        return candidates

    def _apply_global_batch_rerank(self, traces: Dict[str, Dict],
                                    model_manager=None) -> Dict[str, Dict]:
        """Apply global batch re-ranking if abstract reranker is available."""
        if not Config or not getattr(Config, 'ENABLE_ABSTRACT_RERANKER', False):
            return traces

        if not model_manager:
            return traces

        try:
            if hasattr(model_manager, 'ensure_abstract_reranker_loaded'):
                model_manager.ensure_abstract_reranker_loaded()

            if not hasattr(model_manager, 'is_abstract_reranker_available'):
                return traces
            if not model_manager.is_abstract_reranker_available():
                return traces

            # Collect all candidates
            all_pairs = []
            pair_map = {}
            for code_key, trace in traces.items():
                candidates = trace.get('candidates', [])
                if not candidates:
                    continue
                norm = trace.get('normalized', '')
                for c in candidates:
                    text = c.get('text', '')
                    if text and norm and len(text) >= 2:
                        all_pairs.append((norm, text))
                        key = (norm, text)
                        if key not in pair_map:
                            pair_map[key] = []
                        pair_map[key].append((code_key, c))

            if not all_pairs:
                return traces

            # Batch rerank
            norm_texts = [p[0] for p in all_pairs]
            cand_texts = [p[1] for p in all_pairs]
            scores = model_manager.batch_abstract_rerank(norm_texts, cand_texts)

            # Apply scores
            for (norm, cand_text), score in zip(all_pairs, scores):
                for code_key, c in pair_map.get((norm, cand_text), []):
                    c['rerank_score'] = round(score * 10.0, 4)

        except Exception:
            pass

        return traces

    # ── Sentence abstraction / normalization ───────────────────────────

    def abstract_sentence(self, sentence: str, model_manager=None) -> str:
        """Extract a first-level code through the reusable trace flow."""
        if not isinstance(sentence, dict):
            detail = {'content': str(sentence)}
        else:
            detail = self._repair_first_level_sentence_detail(sentence)

        trace = self.build_first_level_candidate_trace(detail, model_manager)
        if not trace:
            return detail.get('content', str(sentence))[:30]

        selected = trace.get('selected_candidate', '')
        if selected:
            return selected
        return detail.get('content', str(sentence))[:30]

    def _normalize_source_sentence(self, text: str) -> str:
        """Normalize a source sentence for coding."""
        if not text:
            return ''
        normalized = text.strip()
        # Remove leading punctuation
        normalized = re.sub(r'^[，。？！；：、\.\?!;\s]+', '', normalized)
        # Remove trailing question marks
        normalized = re.sub(r'[?？]+$', '', normalized)
        normalized = re.sub(r'[!！]+$', '', normalized)
        return normalized.strip()

    def _post_refine_phrase(self, text: str) -> str:
        """Post-refine a phrase by removing bad patterns."""
        if not text:
            return ''

        for pattern in self.bad_phrase_patterns:
            if isinstance(pattern, str):
                text = re.sub(pattern, '', text)

        # Remove leading conjunctions
        text = re.sub(
            r'^(因此|所以|然后|并且|而且|不过|但是|然而|因为|虽然|如果|总之|'
            r'总而言之|综上|此外|另外|还有|特别是|尤其是|'
            r'再加上|再加上说|其实是|其实是说|'
            r'在这里|在那里|在这样的|在此|'
            r'总之来说|我想说的是|可以这么说|可以说)',
            '', text)

        text = text.strip()
        return text

    def _is_question_like(self, text: str) -> bool:
        """Check if text looks like a question."""
        if re.search(r'[?？吗么呢]$', text):
            return True
        if re.match(r'^(为什么|怎么|如何|哪[里些个]|谁|啥|几时|几点|多少|什么样|怎么样|什么时候)', text):
            return True
        return False

    def _compute_salience(self, text: str) -> float:
        """Compute the salience score of a sentence for coding worthiness."""
        if not text or len(text) < 5:
            return 0.0

        salience = 0.0
        clean = text.strip()

        # Length component
        length = len(clean)
        if length < 10:
            salience -= 0.2
        elif length > 15:
            salience += 0.1

        # Strong contrast/change indicators
        contrast_markers = ['但是', '然而', '却', '反而', '不过', '可是', '虽然', '尽管', '即使']
        change_markers = ['转变', '转型', '调整', '变革', '改造', '改变', '变成', '成了', '变得']
        emphasis_markers = ['尤其', '特别', '关键', '核心', '重要', '主要', '重点']

        for m in contrast_markers:
            if m in clean:
                salience += 0.15
                break
        for m in change_markers:
            if m in clean:
                salience += 0.12
                break
        for m in emphasis_markers:
            if m in clean:
                salience += 0.10
                break

        # Exclamation/question bonus
        if re.search(r'[！!]$', clean):
            salience += 0.08

        return round(max(0.0, min(1.0, salience + 0.3)), 4)

    def _extract_domain_terms_from_text(self, text: str) -> List[str]:
        """Extract domain-specific terms for RAG document augmentation."""
        if not text:
            return []

        terms = []
        # Use jieba with POS tagging to find key terms
        for w, flag in pseg.cut(text):
            if len(w) >= 2 and flag.startswith('n'):
                # Filter out pure digits/punctuation
                if not re.match(r'^[\d\W_]+$', w):
                    terms.append(w)

        return list(dict.fromkeys(terms))

    def _is_coding_worthy_sentence(self, text: str) -> bool:
        """Judge if a sentence is worth coding (quality gate)."""
        if not text or len(text.strip()) < self.coding_worthy_min_length:
            return False

        clean = text.strip()

        # Skip very short reactive responses
        if re.match(r'^(嗯|哦|是的|对的|好的|没有|确实|可以|行|对|不对|没有|不行)[了，,。.!！]?$', clean):
            return False

        # Skip pure punctuation/questions
        if re.match(r'^[\W]+$', clean):
            return False

        return True

    def _should_skip_sentence_for_coding(self, text: str, salience: float = 0.0) -> bool:
        """Pre-filter: decide if a sentence is unsuitable for coding."""
        if not text or len(text.strip()) < 4:
            return True

        clean = text.strip()

        # Pure interjection
        if re.match(r'^[啊嗯哦哎呀嘿哈呵喔噢哟呃]+[了?]?$', clean):
            return True

        # Pure question
        if re.match(r'^(什么|怎么|为什么|如何|哪些|哪种|什么样|是不是|能不能|要不要|'
                     r'有没有|可不可以|会不会)', clean) and len(clean) < 8:
            return True

        # Salience gating
        if salience < 0.1 and len(clean) < 8:
            return True

        return False

    # ── Code formalization ─────────────────────────────────────────────

    def _formalize_code(self, code: str) -> str:
        """Formalize a first-level code by replacing colloquialisms."""
        if not code:
            return code

        ct = code.strip()

        # Apply colloquial-to-formal mapping
        mapping = getattr(self, 'colloquial_to_formal', {})
        for colloquial in sorted(mapping.keys(), key=len, reverse=True):
            if colloquial in ct:
                ct = ct.replace(colloquial, mapping[colloquial])

        # Remove colloquial endings
        ct = re.sub(r'(什么的|之类的|那种感觉|这种感觉|这样子|那样子|怎么说呢|就是说)$', '', ct)
        ct = re.sub(r'[吧呢啊嘛呀哦哈哎诶噢呃]+$', '', ct)
        ct = re.sub(r'的(\w{2,4})$', r'\1', ct)

        # Fix common patterns
        ct = re.sub(r'把(.{2,12})(?:聚集|聚拢|吸引)(?:过来|过去|来)', r'吸引\1', ct)
        ct = re.sub(r'^[我我们你你们他他们它它们大家]*(?:也|还是|都|就|会|要|能)?', '', ct)
        ct = ct.strip()

        if not ct:
            return code.strip()
        return ct

    def _compress_first_level_candidate_variants(self, text: str) -> List[str]:
        """Generate compressed variants of a candidate text."""
        if not text:
            return []

        base = str(text).strip()
        if not base:
            return []

        base = self._normalize_candidate_for_first_level(base)
        variants = []
        seen = set()

        def add(value: str):
            value = value.strip()
            if value and value not in seen and len(value) >= 2:
                seen.add(value)
                variants.append(value)

        # Original
        add(base)

        # Compressed variants
        parts = self._split_first_level_candidate_segments(base)
        for part in parts:
            add(part)

        # Strip common prefixes
        compact = re.sub(
            r'^(?:我们|他们|你们|大家|客户|企业|项目|平台|它们|'
            r'这个|那个|这种|那些|这些)?'
            r'(?:可以|能够|能|会|要|需要|希望|想要|'
            r'通过|把|将|对|打造|构建|建立|开展|推进|推动)?',
            '', base)
        add(compact)

        # Strip common suffixes
        compact_tail = re.sub(
            r'^.*?(技术|品牌|资源|平台|机制|流程|生态|需求|问题|'
            r'合作|协同|创新|服务|应用|模块|设备|系统|客户|团队|工业互联网)',
            r'\1', base)
        add(compact_tail)

        return variants

    def _normalize_candidate_for_first_level(self, text: str) -> str:
        """Normalize a candidate for first-level coding."""
        if not text:
            return ''

        clean = text.strip()

        # Remove embedded question marks
        clean = re.sub(r'(?<=[一-鿿])\?(?=[一-鿿])', '', clean)

        # Remove leading numbered markers
        clean = re.sub(
            r'^\s*[①-⑳❶-❿⓵-⓾㉑-㉟①②③④⑤⑥⑦⑧⑨⑩]\s*',
            '', clean)
        clean = re.sub(r'^\s*(?:\d+|[一二三四五六七八九十]+)[、\.．\)]\s*', '', clean)

        # Remove speaker marks
        clean = re.sub(r'^[（(]\d+[）)]', '', clean)
        clean = re.sub(r'^[A-Za-z]\s*[：:]\s*', '', clean)

        # Trim
        clean = clean.strip()

        # Remove if too short
        if len(clean) < 2:
            return ''

        return clean

    def _is_semantically_complete(self, text: str) -> bool:
        """Check if text is semantically complete."""
        t = text.strip()
        if not t:
            return False

        # Prefix-only (incomplete)
        if re.match(r'^(因为|如果|即使|虽然)', t) and len(t) < 8:
            return False

        # Suffix-only (incomplete)
        if re.search(r'(所以|因此|导致|使得|从而|进而|结果)$', t) and len(t) < 8:
            return False

        # Vague starters
        if re.match(r'^(还可以|还好|差不多|一般来说|基本上|'
                     r'相对来说|相对而言|大多数|'
                     r'大体上|大体来说|整体而言)', t) and len(t) < 10:
            return False

        return True

    # ── Span detection ─────────────────────────────────────────────────

    def _detect_concessive_spans(self, text: str) -> List[str]:
        """Detect concessive/conditional clause texts to exclude from coding."""
        spans = []
        patterns = [
            r'虽然.{0,30}(?:但是|但|不过|然而|却|可是|还是|仍然)',
            r'即使.{0,30}(?:也|还是|仍然|依然)',
            r'尽管.{0,30}(?:但是|但|不过|却|还是|仍然)',
            r'如果.{0,30}(?:的话|就|那|那么)',
            r'无论.{0,30}(?:都|也|还是)',
        ]
        for pat in patterns:
            for m in re.finditer(pat, text):
                spans.append(m.group())
        return spans

    def _detect_negated_spans(self, text: str) -> List[str]:
        """Detect negated content texts to exclude from coding."""
        spans = []
        patterns = [
            r'不(?:是|会|能|可以|应该|需要|存在|属于|等于|代表|意味着).{0,30}',
            r'没(?:有|能|办法|法|机会).{0,30}',
            r'并非.{0,20}',
            r'不等于.{0,20}',
        ]
        for pat in patterns:
            for m in re.finditer(pat, text):
                spans.append(m.group())
        return spans

    # ── Text truncation / abbreviation ──────────────────────────────────

    def _truncate_to_word(self, text: str, max_length: int) -> str:
        """Truncate text to max_length at a word boundary."""
        if len(text) <= max_length:
            return text

        truncate_chars = set('，。！？；：""''（）【】《》　 ')
        truncated = text[:max_length]
        for i in range(len(truncated) - 1, max_length // 2, -1):
            if truncated[i] in truncate_chars:
                truncated = truncated[:i]
                break

        return truncated.strip()

    def _smart_abbreviate(self, text: str, max_length: int) -> str:
        """Smart abbreviation of text."""
        if not text or len(text) <= max_length:
            return text

        # Try splitting by comma/semicolon and taking the most important parts
        parts = re.split(r'[，,、]', text)
        if len(parts) <= 1:
            return self._truncate_to_word(text, max_length)

        def part_score(part: str) -> float:
            s = 0.0
            if len(part) >= 3:
                s += 1.0
            if any(t in part for t in ['技术', '资源', '平台', '机制', '流程', '创新', '服务',
                                          '管理', '制度', '监督', '培训', '合作', '发展', '战略']):
                s += 2.0
            return s

        scored = [(part_score(p), p.strip()) for p in parts]
        scored.sort(key=lambda x: x[0], reverse=True)

        result = ''
        for _, part in scored:
            test = (result + '，' + part).strip('，') if result else part
            if len(test) <= max_length:
                result = test
            else:
                break

        if not result:
            result = self._truncate_to_word(text, max_length)

        return result.strip()

    def _limit_first_level_text(self, text: str, max_length: int) -> str:
        """Limit first-level code text to max_length."""
        if not text:
            return ''

        text = text.strip()
        if len(text) <= max_length:
            return text

        # Try splitting by comma
        parts = re.split(r'[，,]', text)
        if len(parts) > 1:
            result = ''
            for part in parts:
                test = (result + '，' + part).strip('，') if result else part
                if len(test) <= max_length:
                    result = test
                else:
                    break
            if result:
                return result

        # Fallback: truncate at word boundary
        return self._truncate_to_word(text, max_length)

    # ── Trained model coding ──────────────────────────────────────────

    def generate_codes_with_trained_model(self, processed_data: Dict[str, Any],
                                           model_manager,
                                           progress_callback: Optional[Callable] = None,
                                           coding_thresholds: Optional[Dict] = None) -> Dict[str, Any]:
        """使用训练模型生成编码"""
        try:
            if progress_callback:
                progress_callback(10)

            if not model_manager.is_trained_model_available():
                raise ValueError("没有可用的训练模型，请先训练模型")

            # 提取所有句子
            all_sentences = []
            file_sentence_mapping = processed_data.get('file_sentence_mapping', {})

            for filename, file_data in file_sentence_mapping.items():
                sentences = file_data.get('sentences', [])
                all_sentences.extend(sentences)

            if progress_callback:
                progress_callback(30)

            # 提取文本内容
            texts = [sentence.get('content', '') for sentence in all_sentences]
            texts = [text for text in texts if len(text.strip()) > 10]

            if not texts:
                raise ValueError("没有找到有效的文本内容")

            if progress_callback:
                progress_callback(50)

            # 使用训练模型预测类别
            predictions, predicted_labels = model_manager.predict_categories(texts)

            if progress_callback:
                progress_callback(70)

            # 构建编码结构
            first_level_codes = {}
            second_level_mapping = {}
            third_level_mapping = {}

            for i, (text, label) in enumerate(zip(texts, predicted_labels)):
                code_key = f"FL_{i + 1:04d}"

                # 解析标签格式：三阶编码||二阶编码
                if '||' in label:
                    third_cat, second_cat = label.split('||', 1)
                else:
                    third_cat = "综合主题"
                    second_cat = label if label else "其他"

                # 存储映射关系
                second_level_mapping[code_key] = second_cat
                third_level_mapping[second_cat] = third_cat

                # 抽象提炼内容
                abstracted_content = self.abstract_sentence(text, model_manager)

                # 构建一阶编码
                original_sentence = all_sentences[i].copy() if isinstance(all_sentences[i], dict) else {}
                if isinstance(original_sentence, dict):
                    original_sentence['original_content'] = text

                first_level_codes[code_key] = [
                    abstracted_content,
                    [all_sentences[i]],  # source_sentences
                    1,  # file_count
                    1,  # sentence_count
                    [original_sentence]  # sentence_details
                ]

            if progress_callback:
                progress_callback(85)

            # 构建二阶编码
            second_level_codes = defaultdict(list)
            for code_key, second_cat in second_level_mapping.items():
                second_level_codes[second_cat].append(code_key)

            # 构建三阶编码
            third_level_codes = defaultdict(list)
            for second_cat, third_cat in third_level_mapping.items():
                third_level_codes[third_cat].append(second_cat)

            if progress_callback:
                progress_callback(95)

            result = {
                'first_level_codes': dict(first_level_codes),
                'second_level_codes': dict(second_level_codes),
                'third_level_codes': dict(third_level_codes),
            }

            if progress_callback:
                progress_callback(100)

            return result

        except Exception as e:
            logger.error("训练模型编码生成失败: %s", e, exc_info=True)
            raise

    def generate_grounded_theory_codes_multi_files(self, processed_data: Dict[str, Any],
                                                     model_manager,
                                                     progress_callback: Optional[Callable] = None,
                                                     use_trained_model: bool = False,
                                                     coding_thresholds: Optional[Dict] = None) -> Dict[str, Any]:
        """为多个文件生成扎根理论编码"""
        if use_trained_model:
            return self.generate_codes_with_trained_model(
                processed_data, model_manager, progress_callback, coding_thresholds)
        else:
            return self.generate_codes_with_rules(
                processed_data, progress_callback, model_manager, coding_thresholds)

    def generate_codes_with_rules(self, processed_data: Dict[str, Any],
                                   progress_callback: Optional[Callable] = None,
                                   model_manager=None,
                                   coding_thresholds: Optional[Dict] = None) -> Dict[str, Any]:
        """使用基于规则的编码生成"""
        self._apply_similarity_threshold_options(coding_thresholds or {})

        file_sentence_mapping = processed_data.get('file_sentence_mapping', {})

        # Collect all sentences
        all_sentences = []
        for filename, file_data in file_sentence_mapping.items():
            sentences = file_data.get('sentences', [])
            all_sentences.extend(sentences)

        if progress_callback:
            progress_callback(10)

        # Generate first-level codes using the improved pipeline
        first_level_codes = self.generate_first_level_codes(
            all_sentences, model_manager, coding_thresholds or {})

        if progress_callback:
            progress_callback(60)

        # Generate second-level codes
        second_level_codes = self.generate_second_level_codes_improved(
            first_level_codes, model_manager)

        if progress_callback:
            progress_callback(80)

        # Generate third-level codes
        third_level_codes = self.generate_third_level_codes_improved(
            second_level_codes)

        if progress_callback:
            progress_callback(95)

        # Phase 4: Run contrastive validation post-coding
        cv_result = self._run_contrastive_validation(first_level_codes)

        result = {
            'first_level_codes': first_level_codes,
            'second_level_codes': second_level_codes,
            'third_level_codes': third_level_codes,
            'contrastive_validation': cv_result if cv_result else None,
        }
        return result

    def generate_first_level_codes(self, sentences: List[Dict],
                                    model_manager=None,
                                    coding_options: Optional[Dict] = None) -> Dict[str, List]:
        """生成一阶编码 — 批量预编码所有句子，消除逐句 model.encode() 瓶颈。

        Phase 0: 预标准化所有句子 → 批量编码 → 批量FAISS检索
        Phase 1: 逐句处理（使用缓存的embedding/检索结果，跳过重复编码）
        """
        self._ensure_first_level_defaults()

        # Phase 3: Reset anchor frequency for anti-collapse IDF penalty
        self._anchor_frequency.clear()
        self._anchor_sentence_count = 0

        coding_opts = coding_options or {}
        use_global_batch_rerank = coding_opts.get('use_global_batch_rerank', True)

        # ═══════════════════════════════════════════════════════════════
        # Phase 0: Pre-batch — normalize, encode, and search all sentences
        # ═══════════════════════════════════════════════════════════════

        # Map: batch_idx → (original_index, code_key, sentence, detail)
        batch_items = []
        batch_norms = []

        has_anchor = self._ensure_anchor_index() and self.concept_anchor_index is not None
        has_knn = self._ensure_knn_train_index() and self.knn_train_index is not None

        for i, sentence in enumerate(sentences):
            code_key = f"FL_{i + 1:04d}"
            detail = self._repair_first_level_sentence_detail(sentence)
            content = detail.get('content', '')
            if not content or len(content.strip()) < 4:
                # Short content — will still be processed inline
                pass
            normalized, _ = self._normalize_sentence_for_coding(detail)
            if normalized:
                batch_norms.append(normalized)
                batch_items.append((i, code_key, sentence, detail, normalized))

        # Batch encode + search
        all_embs = None
        all_anchor_results = None
        all_knn_results = None

        if has_anchor and batch_norms:
            try:
                gpu_batch_size = coding_opts.get('gpu_batch_size', 32)
                all_embs = self.concept_anchor_index.encode_batch(
                    batch_norms, batch_size=gpu_batch_size)
                all_anchor_results = self.concept_anchor_index.search_embeddings(
                    all_embs, top_k=50)
                if has_knn:
                    knn_scores, knn_indices = self.knn_train_index.search(all_embs, 10)
                    all_knn_results = (knn_scores, knn_indices)
            except Exception as e:
                logger.warning("Batch pre-encoding failed: %s, falling back to per-sentence", e)
                all_embs = None
                all_anchor_results = None
                all_knn_results = None

        # ═══════════════════════════════════════════════════════════════
        # Phase 1: Per-sentence processing
        # ═══════════════════════════════════════════════════════════════

        first_level_codes = {}
        traces = {}
        batch_idx = 0

        for i, sentence in enumerate(sentences):
            code_key = f"FL_{i + 1:04d}"
            detail = self._repair_first_level_sentence_detail(sentence)
            content = detail.get('content', '')

            if not content or len(content.strip()) < 4:
                first_level_codes[code_key] = [
                    content.strip()[:20] if content else '',
                    [sentence],
                    1, 1,
                    [detail]
                ]
                continue

            # Look up cached data for this sentence
            cached_emb = None
            cached_anchor = None
            cached_knn = None

            if all_embs is not None and batch_idx < len(batch_items):
                bi, bk, bs, bd, bn = batch_items[batch_idx]
                if bi == i:
                    cached_emb = all_embs[batch_idx:batch_idx + 1]
                    if all_anchor_results is not None:
                        cached_anchor = all_anchor_results[batch_idx]
                    if all_knn_results is not None:
                        cached_knn = (
                            all_knn_results[0][batch_idx],
                            all_knn_results[1][batch_idx],
                        )
                    batch_idx += 1

            # Build candidate trace (pass cached data to skip model.encode)
            trace = self.build_first_level_candidate_trace(
                detail, model_manager, top_n=8, defer_rerank=use_global_batch_rerank,
                cached_embedding=cached_emb,
                cached_anchor_results=cached_anchor,
                cached_knn_results=cached_knn)

            if trace:
                traces[code_key] = trace
                selected = trace.get('selected_candidate', content.strip()[:30])
            else:
                selected = content.strip()[:30]

            first_level_codes[code_key] = [
                selected,
                [sentence],
                1, 1,
                [detail]
            ]

        # Global batch rerank
        if use_global_batch_rerank and len(traces) >= 2:
            traces = self._apply_global_batch_rerank(traces, model_manager)

            # Update selected candidates after rerank
            for code_key, trace in traces.items():
                candidates = trace.get('candidates', [])
                if not candidates:
                    continue
                # Re-sort by conservative score
                for row in candidates:
                    row['conservative_score'] = self._conservative_first_level_rank_score(row)
                candidates.sort(key=lambda r: r.get('conservative_score', 0), reverse=True)

                best = candidates[0]
                new_selected = best.get('text', '')
                if new_selected:
                    trace['selected_candidate'] = new_selected
                    if code_key in first_level_codes:
                        first_level_codes[code_key][0] = new_selected

        # Store traces
        for code_key, trace in traces.items():
            self._store_first_level_trace(code_key, trace)

        return first_level_codes

    # ── RAG initialization ────────────────────────────────────────────

    def _init_rag_components(self):
        """初始化RAG组件，失败时安全关闭并退回到传统匹配路径。"""
        if not Config or not getattr(Config, 'ENABLE_RAG_CODING', False):
            self.rag_enabled = False
            self.runtime_strategy = 'legacy'
            logger.info("RAG编码未启用，退回到传统匹配路径")
            return

        try:
            # Lazy import RAG components
            from semantic_matcher import SemanticMatcher
            from decision_policy import DecisionPolicy
            from first_level_clusterer import FirstLevelClusterer
            from rag_index_manager import RAGIndexManager

            if self.semantic_matcher is None:
                self.semantic_matcher = SemanticMatcher()

            self.rag_matcher = self.semantic_matcher
            self.decision_policy = DecisionPolicy(self.rag_matcher)
            self.first_level_clusterer = FirstLevelClusterer(
                similarity_threshold=self.rag_cluster_similarity_threshold)
            self.rag_index_manager = RAGIndexManager()

            self.rag_enabled = True
            self.runtime_strategy = 'rag_hybrid'

            # Try to load KNN abstract generator
            try:
                from knn_abstract_generator import KNNAbstractGenerator
                self.knn_abstract_generator = KNNAbstractGenerator()
            except Exception:
                self.knn_abstract_generator = None

            # Try to load doc retriever
            try:
                from rag_doc_retriever import RAGDocRetriever
                self.rag_doc_retriever = RAGDocRetriever()
            except Exception:
                self.rag_doc_retriever = None

            logger.info("RAG组件初始化成功")

        except Exception as e:
            self.rag_enabled = False
            self.runtime_strategy = 'legacy'
            logger.warning("RAG组件初始化失败: %s，退回到传统匹配路径", e)

    def _ensure_anchor_index(self) -> bool:
        """加载概念锚点FAISS索引（改进7——微调bge-small-zh-v1.5模型 + FAISS检索）。

        用于将口语化句子映射到稳定的概念锚点。
        """
        # Already loaded
        if self.concept_anchor_index is not None:
            return True

        try:
            import os as _os

            _anchor_dir = _os.path.join(
                _os.path.dirname(_os.path.abspath(__file__)),
                'cache', 'anchor_index')
            _faiss_path = _os.path.join(_anchor_dir, 'anchor_index.faiss')
            _concepts_path = _os.path.join(_anchor_dir, 'concepts.json')

            # Check if index files exist
            if not _os.path.exists(_faiss_path) or not _os.path.exists(_concepts_path):
                logger.info("概念锚点索引未构建，跳过概念锚点检索")
                return False

            # Import and create anchor index
            from build_anchor_index import ConceptAnchorIndex

            _model_path = _os.path.join(
                _os.path.dirname(_os.path.abspath(__file__)),
                'trained_models', 'concept_anchor_v6')
            _library_path = _os.path.join(
                _os.path.dirname(_os.path.abspath(__file__)),
                'coding_library.json')
            _anchor_data = _os.path.join(
                _os.path.dirname(_os.path.abspath(__file__)),
                'data', 'clean_anchor_pairs.json')

            if not _os.path.exists(_model_path):
                logger.info("微调锚点模型不存在，跳过概念锚点检索")
                return False

            self.concept_anchor_index = ConceptAnchorIndex(
                model_path=_model_path,
                library_path=_library_path,
                anchor_data_path=_anchor_data,
                governed_concepts_path=_concepts_path,
            )

            # Load alias → canonical map (Phase 2 governance)
            _alias_path = _os.path.join(_anchor_dir, 'alias_map.json')
            if _os.path.exists(_alias_path):
                import json
                with open(_alias_path, "r", encoding="utf-8") as _af:
                    _alias_data = json.load(_af)
                self._alias_map = _alias_data.get("mappings", {})
                if self._alias_map:
                    logger.info("Alias map loaded: %d mappings", len(self._alias_map))

            # Load anchor → 二阶 → 三阶 hierarchy (Phase 2 semantic compression)
            self._load_anchor_hierarchy()

            logger.info("概念锚点FAISS索引加载成功，%d个概念",
                        len(self.concept_anchor_index.concepts))
            return True

        except Exception as e:
            logger.warning("概念锚点索引加载失败: " + str(e))
            self.concept_anchor_index = None
            return False

    def _ensure_knn_train_index(self) -> bool:
        """Build FAISS index over v11 training sentence embeddings for KNN concept recall.

        Replaces extractive n-gram generation: when FAISS anchor retrieval is weak,
        find similar training sentences via embedding KNN and retrieve their anchor codes.
        """
        if self.knn_train_index is not None:
            return True

        try:
            import os as _os
            import json
            import numpy as np
            import faiss

            # Prefer clean governed data, fall back to v3
            _clean_path = _os.path.join(
                _os.path.dirname(_os.path.abspath(__file__)),
                'data', 'train_anchor_pairs_clean.json')
            _v3_path = _os.path.join(
                _os.path.dirname(_os.path.abspath(__file__)),
                'data', 'train_anchor_pairs_v3.json')
            _train_path = _clean_path if _os.path.exists(_clean_path) else _v3_path
            if not _os.path.exists(_train_path):
                logger.info("v11训练数据不存在，跳过KNN概念召回")
                return False

            # Need the concept_anchor model for embeddings
            if not self._ensure_anchor_index() or self.concept_anchor_index is None:
                return False

            with open(_train_path, "r", encoding="utf-8") as fh:
                train_data = json.load(fh)

            model = self.concept_anchor_index.model

            # Collect unique (sentence, anchor_code) pairs
            seen_pairs = set()
            train_sentences = []
            train_anchors = []
            for item in train_data.get("pairs", []):
                sent = item.get("sentence", "").strip()
                anchor = item.get("anchor_code", "").strip()
                if sent and anchor and (sent, anchor) not in seen_pairs:
                    seen_pairs.add((sent, anchor))
                    train_sentences.append(sent)
                    train_anchors.append(anchor)

            if len(train_sentences) < 10:
                return False

            logger.info("Building KNN recall index: %d training sentences", len(train_sentences))

            # Encode all training sentences
            train_embs = model.encode(
                train_sentences, normalize_embeddings=True,
                show_progress_bar=True, batch_size=64,
            ).astype(np.float32)

            # Build FAISS index
            dim = train_embs.shape[1]
            self.knn_train_index = faiss.IndexFlatIP(dim)
            self.knn_train_index.add(train_embs)
            self.knn_train_anchors = train_anchors

            logger.info("KNN recall index ready: %d vectors, dim=%d",
                        self.knn_train_index.ntotal, dim)
            return True

        except Exception as e:
            logger.warning("KNN训练索引构建失败: %s", e)
            self.knn_train_index = None
            self.knn_train_anchors = []
            return False

    # ── Second-level coding ────────────────────────────────────────────

    def _best_candidate_names(self, candidates: List[Dict]) -> List[str]:
        """Get best candidate names for second-level matching."""
        if not candidates:
            return []

        scored = []
        for c in candidates:
            text = c.get('text', '').strip()
            if not text:
                continue
            token_score = float(c.get('token_score', 0))
            vector_score = float(c.get('vector_score', 0))
            total = token_score * 0.3 + vector_score * 0.7
            scored.append((total, text))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [text for _, text in scored[:5]]

    def _build_cluster_query(self, cluster: List[str]) -> str:
        """构建聚类查询文本，使用簇中代表性文本。"""
        if not cluster:
            return ''
        return ' '.join(cluster[:3])

    def _try_keyword_second_match(self, text: str, candidates: List[Dict]) -> Optional[str]:
        """关键词匹配被激活后，用jieba分词然后做词语级别匹配。"""
        if not text or not candidates:
            return None

        text_words = set(w for w in jieba.cut(text) if len(w) >= 2)

        best = None
        best_score = 0
        for c in candidates:
            name = c.get('name', '').strip()
            if not name:
                continue
            name_words = set(w for w in jieba.cut(name) if len(w) >= 2)
            if not name_words:
                continue
            overlap = len(text_words & name_words)
            if overlap > best_score:
                best_score = overlap
                best = name

        if best and best_score >= 2:
            return best
        return None

    def _load_alias_map(self):
        """Load alias → canonical anchor mapping for governance normalization."""
        try:
            import os as _os, json
            _alias_path = _os.path.join(
                _os.path.dirname(_os.path.abspath(__file__)),
                "cache", "anchor_index", "alias_map.json")
            if _os.path.exists(_alias_path):
                with open(_alias_path, "r", encoding="utf-8") as _af:
                    _alias_data = json.load(_af)
                _mappings = _alias_data.get("mappings", {})
                if isinstance(_mappings, dict) and _mappings:
                    self._alias_map = _mappings
                    logger.info("Alias map loaded: %d mappings", len(self._alias_map))
        except Exception as e:
            logger.debug("Alias map load skipped: %s", e)

    def _enrich_with_hierarchy(self, anchor_name: str) -> dict:
        """Priority 7: Enrich an anchor with its L2 theme and L3 theory mapping.

        Returns a dict with second_category, third_category, source, and confidence,
        or an empty dict if no mapping is found.
        """
        second, third, source, conf = self._get_second_third_for_anchor(anchor_name)
        if second and third:
            return {
                "second_category": second,
                "third_category": third,
                "source": source,
                "confidence": round(conf, 4),
            }
        return {}

    def _load_anchor_hierarchy(self):
        """Load anchor → 二阶 → 三阶 hierarchy mapping for semantic compression."""
        try:
            import os as _os, json
            _hier_path = _os.path.join(
                _os.path.dirname(_os.path.abspath(__file__)),
                "data", "anchor_hierarchy.json")
            if _os.path.exists(_hier_path):
                with open(_hier_path, "r", encoding="utf-8") as _hf:
                    _hier_data = json.load(_hf)
                self._anchor_hierarchy = _hier_data.get("mappings", {})
                # Store list of known anchor names for semantic fallback
                self._hierarchy_anchor_names = list(self._anchor_hierarchy.keys())
                self._hierarchy_faiss = None  # lazy-built
                _stats = _hier_data.get("stats", {})
                if self._anchor_hierarchy:
                    logger.info("Anchor hierarchy loaded: %d anchors mapped (%.0f%% coverage)",
                                len(self._anchor_hierarchy),
                                _stats.get("v11_direct", 0) + _stats.get("semantic_inherited", 0))
        except Exception as e:
            logger.warning("Anchor hierarchy load failed: %s", e)
            self._anchor_hierarchy = {}
            self._hierarchy_anchor_names = []
            self._hierarchy_faiss = None

    def _get_second_third_for_anchor(self, anchor_name: str):
        """Look up second/third category for an anchor code using the hierarchy mapping.

        Returns (second_category, third_category, source, confidence) or (None, None, None, 0).
        Mappings with confidence < 0.2 are treated as unreliable and return None.

        Phase 3 semantic fallback: if anchor not in hierarchy, uses embedding similarity
        to find the nearest known hierarchy anchor and inherits its mapping.
        """
        if not self._anchor_hierarchy or not anchor_name:
            return None, None, None, 0

        _MIN_CONFIDENCE = 0.2
        _FALLBACK_SIM_THRESHOLD = 0.65

        # Try direct lookup first, then alias-normalized lookup
        for candidate in (anchor_name, self._alias_map.get(anchor_name, "")):
            if candidate and candidate in self._anchor_hierarchy:
                entry = self._anchor_hierarchy[candidate]
                second = entry.get("second_category")
                third = entry.get("third_category")
                conf = entry.get("confidence", 0)
                if second and third and conf >= _MIN_CONFIDENCE:
                    return (second, third,
                            entry.get("source", "unknown"),
                            conf)

        # Phase 3: semantic fallback — find nearest hierarchy anchor via embedding.
        # Search k neighbours, skip self-matches and entries with null/low-confidence
        # categories, and inherit the first valid mapping.
        if self._hierarchy_anchor_names:
            try:
                import numpy as np

                # Lazy-load bge-small-zh-v1.5 for hierarchy fallback encoding
                if not hasattr(self, '_hierarchy_model') or self._hierarchy_model is None:
                    from sentence_transformers import SentenceTransformer
                    import os as _os
                    _model_path = _os.path.join(
                        _os.path.dirname(_os.path.abspath(__file__)),
                        "local_models", "bge-small-zh-v1.5")
                    self._hierarchy_model = SentenceTransformer(_model_path)

                # Lazy-build FAISS index over hierarchy anchor embeddings
                if self._hierarchy_faiss is None:
                    import faiss
                    _hier_embs = self._hierarchy_model.encode(
                        self._hierarchy_anchor_names, normalize_embeddings=True,
                        show_progress_bar=False, batch_size=256).astype(np.float32)
                    _dim = _hier_embs.shape[1]
                    self._hierarchy_faiss = faiss.IndexFlatIP(_dim)
                    self._hierarchy_faiss.add(_hier_embs)
                    logger.info("Hierarchy FAISS index built: %d anchors", len(self._hierarchy_anchor_names))

                # Encode query anchor and search k neighbours
                _k = 10
                _query_emb = self._hierarchy_model.encode(
                    [anchor_name], normalize_embeddings=True,
                    show_progress_bar=False).astype(np.float32)
                _sims, _idxs = self._hierarchy_faiss.search(_query_emb, _k)

                for _rank in range(_k):
                    _sim = float(_sims[0][_rank])
                    if _sim < _FALLBACK_SIM_THRESHOLD:
                        break
                    _neighbor = self._hierarchy_anchor_names[_idxs[0][_rank]]
                    # Skip self-match (anchor already failed direct lookup)
                    if _neighbor == anchor_name:
                        continue
                    entry = self._anchor_hierarchy[_neighbor]
                    second = entry.get("second_category")
                    third = entry.get("third_category")
                    conf = entry.get("confidence", 0)
                    if second and third and conf >= _MIN_CONFIDENCE:
                        return (second, third, "semantic_fallback",
                                round(conf * _sim, 3))
            except Exception as e:
                logger.debug("Hierarchy semantic fallback failed: %s", e)

        return None, None, None, 0

    def generate_second_level_from_anchors(self, first_level_codes: Dict[str, List]) -> Dict[str, List[str]]:
        """Build second-level codes directly from anchor hierarchy mapping.

        This is the preferred path for semantic compression: each anchor code
        maps to its canonical 二阶 category via the v11-trained hierarchy.
        """
        if not first_level_codes or not self._anchor_hierarchy:
            return {}

        second_level = defaultdict(list)
        unmapped_count = 0

        for key, val in first_level_codes.items():
            anchor_text = val[0] if isinstance(val, list) and val else str(val)
            anchor_text = anchor_text.strip()
            if not anchor_text or len(anchor_text) < 2:
                continue

            second, third, source, conf = self._get_second_third_for_anchor(anchor_text)
            if second:
                second_level[second].append(key)
            else:
                unmapped_count += 1
                second_level['其他'].append(key)

        total_assigned = sum(len(v) for v in second_level.values())
        mapped = total_assigned - unmapped_count
        logger.info("Hierarchy-based 二阶: %d categories, %d/%d anchors mapped (%.0f%%)",
                    len(second_level), mapped, total_assigned,
                    mapped / max(total_assigned, 1) * 100)

        # Phase 4: Semantic compression — merge similar second-level categories
        result = dict(second_level)
        if len(result) > 20:
            try:
                if self._semantic_compressor is None:
                    from semantic_compressor import SemanticCompressor
                    self._semantic_compressor = SemanticCompressor()
                result, _merge_map = self._semantic_compressor.compress_second_level(result)
            except Exception as e:
                logger.debug("Second-level compression skipped: %s", e)

        return result

    def generate_third_level_from_anchors(self, second_level_codes: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Build third-level codes from second-level categories using hierarchy mapping.

        Given second-level codes aggregated by generate_second_level_from_anchors,
        looks up each second category's third-level parent.
        """
        if not second_level_codes or not self._anchor_hierarchy:
            return {}

        # Build second→third lookup from hierarchy
        second_to_third = {}
        for anchor_name, entry in self._anchor_hierarchy.items():
            s = entry.get("second_category")
            t = entry.get("third_category")
            if s and t:
                if s not in second_to_third:
                    second_to_third[s] = t

        third_level = defaultdict(list)
        for second_cat, keys in second_level_codes.items():
            third = second_to_third.get(second_cat, '综合主题')
            third_level[third].append(second_cat)

        logger.info("Hierarchy-based 三阶: %d categories", len(third_level))

        # Phase 4: Semantic compression for third-level
        result = dict(third_level)
        if len(result) > 15:
            try:
                if self._semantic_compressor is None:
                    from semantic_compressor import SemanticCompressor
                    self._semantic_compressor = SemanticCompressor()
                result, _merge_map = self._semantic_compressor.compress_third_level(result)
            except Exception as e:
                logger.debug("Third-level compression skipped: %s", e)

        return result

    def _lookup_second_code_by_name(self, second_name: str) -> Optional[Dict]:
        """Look up a second-level code by name in the coding library."""
        if not second_name or not self.coding_library:
            return None

        try:
            lib = self.coding_library
            enc = lib.get('encoding_library', lib)
            for third in enc.get('third_level_codes', []):
                for second in third.get('second_level_codes', []):
                    if second.get('name', '').strip() == second_name.strip():
                        result = dict(second)
                        result['third_level'] = third.get('name', '')
                        return result
        except Exception:
            pass
        return None

    def _refresh_rag_matcher_if_needed(self):
        """必要时刷新RAG匹配器状态，确保编码库编辑后立即生效。"""
        if not self.rag_enabled or self.rag_matcher is None:
            return

        try:
            if hasattr(self.rag_matcher, 'refresh_index'):
                self.rag_matcher.refresh_index()
        except Exception:
            logger.warning("RAG匹配器刷新失败，继续使用旧匹配器")

    def generate_second_level_codes_improved(self, first_level_codes: Dict[str, List],
                                              model_manager=None) -> Dict[str, List[str]]:
        """生成二阶编码 — 优先使用Anchor层级映射，回退到语义/关键词匹配"""
        self._ensure_rag_threshold_defaults()

        if not first_level_codes:
            return {}

        # Primary: use anchor hierarchy mapping (Phase 2 semantic compression)
        if self._anchor_hierarchy:
            logger.info("使用Anchor层级映射生成二阶编码")
            return self.generate_second_level_from_anchors(first_level_codes)

        # Fallback: collect first-level code texts and use RAG/keyword matching
        code_texts = {}
        for key, val in first_level_codes.items():
            text = val[0] if isinstance(val, list) and val else str(val)
            if text and len(text) >= 2:
                code_texts[key] = text

        if not code_texts:
            return {'其他': list(first_level_codes.keys())}

        second_level_codes = defaultdict(list)
        matched_keys = set()

        matched_count = 0

        # Try RAG matcher with correct method signature
        if self.rag_enabled and self.rag_matcher is not None and self.coding_library:
            try:
                lib = self.coding_library
                enc = lib.get('encoding_library', lib)
                second_codes = []
                for third in enc.get('third_level_codes', []):
                    for second in third.get('second_level_codes', []):
                        second_codes.append(second)

                for code_key, text in code_texts.items():
                    matches = self.rag_matcher.match_first_level_to_second_level(
                        text, second_codes, top_k=1,
                        threshold=self.rag_second_level_threshold)
                    if matches:
                        match_name = matches[0][0].get('name', '')
                        if match_name:
                            second_level_codes[match_name].append(code_key)
                            matched_keys.add(code_key)
                            matched_count += 1
            except Exception:
                pass

        logger.info("开始二阶编码聚类，共 %d 个一阶编码", len(code_texts))
        if matched_count:
            logger.info("RAG匹配完成: %d/%d", matched_count, len(code_texts))

        # Keyword-based fallback for unmatched
        remaining = {k: v for k, v in code_texts.items() if k not in matched_keys}
        if remaining:
            kw_second = self._generate_second_level_codes_keyword_based(remaining)
            for second_cat, keys in kw_second.items():
                second_level_codes[second_cat].extend(keys)
                matched_keys.update(keys)

        # Ensure all keys are assigned
        for key in code_texts:
            if key not in matched_keys:
                second_level_codes['其他'].append(key)

        logger.info("二阶编码完成，共 %d 个类别", len(second_level_codes))
        return dict(second_level_codes)

    def _generate_second_level_codes_keyword_based(self,
                                                     first_level_codes: Dict[str, str]) -> Dict[str, List[str]]:
        """基于关键词的二阶编码生成（后备方法）。"""
        if not first_level_codes or not self.coding_library:
            return {}

        keyword_map = {}
        try:
            lib = self.coding_library
            enc = lib.get('encoding_library', lib)
            for third in enc.get('third_level_codes', []):
                for second in third.get('second_level_codes', []):
                    name = second.get('name', '').strip()
                    keywords = second.get('keywords', [])
                    if name and keywords:
                        keyword_map[name] = keywords
        except Exception:
            pass

        second_level = defaultdict(list)
        for key, text in first_level_codes.items():
            matched = self._try_keyword_second_match(
                text,
                [{'name': n, 'keywords': kw} for n, kw in keyword_map.items()]
            )
            if matched:
                second_level[matched].append(key)
            else:
                second_level['其他各类话题'].append(key)

        if not second_level:
            second_level['其他各类话题'] = list(first_level_codes.keys())

        return dict(second_level)

    # ── Third-level coding ────────────────────────────────────────────

    def generate_third_level_codes_improved(self, second_level_codes: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """生成三阶编码 — 优先使用Anchor层级映射，回退到语义/规则匹配"""
        self._ensure_rag_threshold_defaults()

        if not second_level_codes:
            return {}

        # Primary: use anchor hierarchy mapping (Phase 2 semantic compression)
        if self._anchor_hierarchy:
            logger.info("使用Anchor层级映射生成三阶编码")
            return self.generate_third_level_from_anchors(second_level_codes)

        third_level_codes = defaultdict(list)

        if self.rag_enabled and self.rag_matcher is not None and self.coding_library:
            try:
                lib = self.coding_library
                enc = lib.get('encoding_library', lib)
                third_codes = []
                for third in enc.get('third_level_codes', []):
                    third_codes.append(third)

                for second_cat in second_level_codes:
                    # match_second_level_to_third_level expects a dict, not string
                    second_dict = self._lookup_second_code_by_name(second_cat) or {"name": second_cat}
                    result = self.rag_matcher.match_second_level_to_third_level(
                        second_dict, third_codes,
                        threshold=self.rag_third_level_threshold)
                    if result:
                        match_name = result[0].get('name', '')
                        if match_name:
                            third_level_codes[match_name].append(second_cat)
                        else:
                            third_level_codes['综合主题'].append(second_cat)
                    else:
                        third_level_codes['综合主题'].append(second_cat)
            except Exception:
                pass
        else:
            logger.info("开始三阶编码聚合，共 %d 个二阶类别", len(second_level_codes))

        # Rule-based fallback
        if not third_level_codes:
            third_level_codes = self._generate_third_level_codes_rule_based(second_level_codes)

        return dict(third_level_codes)

    def _generate_third_level_codes_rule_based(self,
                                                 second_level_codes: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """基于规则的三阶编码生成（后备方法）。"""
        if not second_level_codes or not self.coding_library:
            third = defaultdict(list)
            for second_cat in second_level_codes:
                third['综合主题'].append(second_cat)
            return dict(third)

        third_level = defaultdict(list)
        try:
            lib = self.coding_library
            enc = lib.get('encoding_library', lib)

            # Build lookup: second_name -> third_name
            second_to_third = {}
            for third_item in enc.get('third_level_codes', []):
                third_name = third_item.get('name', '')
                for second_item in third_item.get('second_level_codes', []):
                    second_name = second_item.get('name', '').strip()
                    if second_name:
                        second_to_third[second_name] = third_name

            # Match
            for second_cat in second_level_codes:
                if second_cat in second_to_third:
                    third_level[second_to_third[second_cat]].append(second_cat)
                else:
                    # Try fuzzy match
                    matched = False
                    for lib_name, third_name in second_to_third.items():
                        if lib_name in second_cat or second_cat in lib_name:
                            third_level[third_name].append(second_cat)
                            matched = True
                            break
                    if not matched:
                        third_level['综合主题'].append(second_cat)

        except Exception:
            third_level = defaultdict(list)
            for second_cat in second_level_codes:
                third_level['综合主题'].append(second_cat)

        if not third_level:
            third_level['综合主题'] = list(second_level_codes.keys())

        return dict(third_level)
