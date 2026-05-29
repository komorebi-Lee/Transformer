# Recovered and cleaned from bytecode
# Auto-generated - may need manual fixes

import logging
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
import re
import jieba
from jieba.posseg import pseg
from collections import Counter, defaultdict
import os

logger = logging.getLogger(__name__)

# Optional imports - may fail gracefully
try:
    from config import Config
except Exception:
    Config = None  # type: ignore

try:
    from coding_library_manager import CodingLibraryManager
except Exception as e:
    logger.warning('导入CodingLibraryManager失败: ' + str(e))
    CodingLibraryManager = None  # type: ignore

try:
    from semantic_matcher import SemanticMatcher
except Exception as e:
    logger.warning('导入SemanticMatcher失败: ' + str(e))
    SemanticMatcher = None  # type: ignore

try:
    from quality_learner import HighQualitySampleLearner
except Exception as e:
    logger.warning('导入HighQualitySampleLearner失败: ' + str(e))
    HighQualitySampleLearner = None  # type: ignore

class EnhancedCodingGenerator:
    # FIXME: needs manual fix
    __module__ = None
    __qualname__ = 'EnhancedCodingGenerator'
    __doc__ = '增强的扎根理论编码生成器 - 支持训练模型预测'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    'return'
    _clean_code_prefix = (<?>, <?>, <?>, <?>)(<function 'EnhancedCodingGenerator._clean_code_prefix'>)
    __init__ = <function 'EnhancedCodingGenerator.__init__'>
    _ensure_first_level_defaults = <function 'EnhancedCodingGenerator._ensure_first_level_defaults'>
    # FIXME: needs manual fix
    _default_second_threshold = <function 'EnhancedCodingGenerator._default_second_threshold'>
    # FIXME: needs manual fix
    (<?>, <?>) ; 'return'
    _default_third_threshold = <function 'EnhancedCodingGenerator._default_third_threshold'>
    # FIXME: needs manual fix
    (<?>, <?>) ; 'return'
    _default_cluster_threshold = <function 'EnhancedCodingGenerator._default_cluster_threshold'>
    # FIXME: needs manual fix
    (<?>, <?>) ; 'value'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[<?>] ; 'default'
    # FIXME: needs manual fix
    'return'
    _clamp_threshold = <function 'EnhancedCodingGenerator._clamp_threshold'>
    _ensure_rag_threshold_defaults = <function 'EnhancedCodingGenerator._ensure_rag_threshold_defaults'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>) ; ('return', None) ; (None, None, None) ; 'second_threshold'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[<?>] ; 'third_threshold'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[<?>] ; 'cluster_threshold'
    # FIXME: needs manual fix
    configure_similarity_thresholds = <function 'EnhancedCodingGenerator.configure_similarity_thresholds'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>[<?>], 'return', None) ; 'coding_thresholds'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    _apply_similarity_threshold_options = <function 'EnhancedCodingGenerator._apply_similarity_threshold_options'>
    # FIXME: needs manual fix
    (<?>, <?>[<?>[(<?>, <?>)]], 'return', None) ; 'sentence'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[(<?>, <?>)] ; 'return'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    _repair_first_level_sentence_detail = <function 'EnhancedCodingGenerator._repair_first_level_sentence_detail'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>[(<?>, <?>)]) ; 'code_text'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    'return'
    _first_level_anchor_ratio = <function 'EnhancedCodingGenerator._first_level_anchor_ratio'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>) ; ('', False) ; 'code_text'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    'return'
    _is_low_quality_first_level_code = <function 'EnhancedCodingGenerator._is_low_quality_first_level_code'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>, <?>, <?>) ; 'text'
    # FIXME: needs manual fix
    'return'
    _has_first_level_information_cue = <function 'EnhancedCodingGenerator._has_first_level_information_cue'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>) ; 'text'
    # FIXME: needs manual fix
    'return'
    _looks_semantically_incomplete = <function 'EnhancedCodingGenerator._looks_semantically_incomplete'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>) ; 'text'
    # FIXME: needs manual fix
    'return'
    _has_valid_first_level_pos_pattern = <function 'EnhancedCodingGenerator._has_valid_first_level_pos_pattern'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>) ; 'text'
    # FIXME: needs manual fix
    'return'
    _contains_colloquial_residue = <function 'EnhancedCodingGenerator._contains_colloquial_residue'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>) ; 'candidate_rows'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[<?>[(<?>, <?>)]] ; 'source_text'
    # FIXME: needs manual fix
    'return'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    _canonicalize_first_level_candidate_rows = <function 'EnhancedCodingGenerator._canonicalize_first_level_candidate_rows'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>[<?>[(<?>, <?>)]]) ; 'text'
    # FIXME: needs manual fix
    'return'
    # FIXME: needs manual fix
    _split_first_level_candidate_segments = <function 'EnhancedCodingGenerator._split_first_level_candidate_segments'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>[<?>]) ; 'text'
    # FIXME: needs manual fix
    'return'
    # FIXME: needs manual fix
    _extract_semantic_chunks = <function 'EnhancedCodingGenerator._extract_semantic_chunks'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>[<?>]) ; ('',) ; 'fragment'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    'return'
    _score_first_level_fragment = <function 'EnhancedCodingGenerator._score_first_level_fragment'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>) ; ('', False) ; 'text'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    'return'
    _finalize_first_level_candidate = <function 'EnhancedCodingGenerator._finalize_first_level_candidate'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>, <?>, <?>) ; 'row'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[(<?>, <?>)] ; 'return'
    _conservative_first_level_rank_score = <function 'EnhancedCodingGenerator._conservative_first_level_rank_score'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>) ; 'a'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    'return'
    _model_semantic_similarity = <function 'EnhancedCodingGenerator._model_semantic_similarity'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>) ; 'trace'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[(<?>, <?>)] ; 'source_detail'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[(<?>, <?>)] ; 'return'
    _select_quality_first_level_candidate = <function 'EnhancedCodingGenerator._select_quality_first_level_candidate'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>) ; 'code'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    'return'
    _validate_code_semantic_fit = <function 'EnhancedCodingGenerator._validate_code_semantic_fit'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>) ; ('',) ; 'fragment'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    'return'
    _score_first_level_fragment = <function 'EnhancedCodingGenerator._score_first_level_fragment'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>) ; 'row'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[(<?>, <?>)] ; 'return'
    _conservative_first_level_rank_score = <function 'EnhancedCodingGenerator._conservative_first_level_rank_score'>
    _rebuild_decision_policy_from_matcher = <function 'EnhancedCodingGenerator._rebuild_decision_policy_from_matcher'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>) ; ('return', None) ; 'prototypes'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    set_first_level_prototypes = <function 'EnhancedCodingGenerator.set_first_level_prototypes'>
    # FIXME: needs manual fix
    (<?>, <?>[<?>[(<?>, <?>)]], 'return', None) ; (None,) ; 'labels'
    # FIXME: needs manual fix
    set_first_level_recall_bank = <function 'EnhancedCodingGenerator.set_first_level_recall_bank'>
    # FIXME: needs manual fix
    (<?>, <?>[<?>], 'return', None) ; (None, 8, 0.35) ; 'text'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    'return'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    _semantic_recall_first_level_labels = <function 'EnhancedCodingGenerator._semantic_recall_first_level_labels'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>, <?>, <?>[<?>[(<?>, <?>)]]) ; 'manual_code'
    # FIXME: needs manual fix
    'return'
    # FIXME: needs manual fix
    _prototype_keywords = <function 'EnhancedCodingGenerator._prototype_keywords'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>[<?>]) ; 'text'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[(<?>, <?>)] ; 'return'
    _prototype_similarity = <function 'EnhancedCodingGenerator._prototype_similarity'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>) ; (3,) ; 'text'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    'return'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    _find_first_level_prototype_hits = <function 'EnhancedCodingGenerator._find_first_level_prototype_hits'>
    reset_first_level_trace_meta = <function 'EnhancedCodingGenerator.reset_first_level_trace_meta'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>[<?>[(<?>, <?>)]]) ; ('return', None) ; 'return'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    get_first_level_trace_meta = <function 'EnhancedCodingGenerator.get_first_level_trace_meta'>
    # FIXME: needs manual fix
    (<?>, <?>[(<?>, <?>[(<?>, <?>)])]) ; 'code_key'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    _store_first_level_trace = <function 'EnhancedCodingGenerator._store_first_level_trace'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>[(<?>, <?>)], 'return', None) ; (None, None, False) ; 'sentence'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[<?>] ; 'defer_rerank'
    # FIXME: needs manual fix
    'return'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    build_first_level_candidate_trace = <function 'EnhancedCodingGenerator.build_first_level_candidate_trace'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>, <?>, <?>[(<?>, <?>)]) ; 'text'
    # FIXME: needs manual fix
    'return'
    rewrite_first_level_code = <function 'EnhancedCodingGenerator.rewrite_first_level_code'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>) ; 'trace'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[(<?>, <?>)] ; 'score_map'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[(<?>, <?>)]
    _rerank_candidate_rows_for_trace = <function 'EnhancedCodingGenerator._rerank_candidate_rows_for_trace'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>[(<?>, <?>)], 'return', None) ; (None,) ; 'traces'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    _apply_global_batch_rerank = <function 'EnhancedCodingGenerator._apply_global_batch_rerank'>
    # FIXME: needs manual fix
    (<?>, <?>[<?>[(<?>, <?>)]], 'return', None) ; (None,) ; 'sentence'
    # FIXME: needs manual fix
    'return'
    abstract_sentence = <function 'EnhancedCodingGenerator.abstract_sentence'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>) ; 'text'
    # FIXME: needs manual fix
    'return'
    _normalize_source_sentence = <function 'EnhancedCodingGenerator._normalize_source_sentence'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>) ; 'text'
    # FIXME: needs manual fix
    'return'
    _post_refine_phrase = <function 'EnhancedCodingGenerator._post_refine_phrase'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>) ; 'text'
    # FIXME: needs manual fix
    'return'
    _is_question_like = <function 'EnhancedCodingGenerator._is_question_like'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>) ; 'text'
    # FIXME: needs manual fix
    'return'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    _compute_salience = <function 'EnhancedCodingGenerator._compute_salience'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>[(<?>, <?>)])
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    'return'
    # FIXME: needs manual fix
    _extract_domain_terms_from_text = (<?>, <?>, <?>, <?>[<?>])(<function 'EnhancedCodingGenerator._extract_domain_terms_from_text'>)
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    'return'
    _is_coding_worthy_sentence = <function 'EnhancedCodingGenerator._is_coding_worthy_sentence'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>) ; (None,) ; 'text'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[<?>[(<?>, <?>)]] ; 'return'
    _should_skip_sentence_for_coding = <function 'EnhancedCodingGenerator._should_skip_sentence_for_coding'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>) ; 'code'
    # FIXME: needs manual fix
    'return'
    _formalize_code = <function 'EnhancedCodingGenerator._formalize_code'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>) ; 'text'
    # FIXME: needs manual fix
    'return'
    # FIXME: needs manual fix
    _compress_first_level_candidate_variants = <function 'EnhancedCodingGenerator._compress_first_level_candidate_variants'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>[<?>]) ; 'text'
    # FIXME: needs manual fix
    'return'
    _normalize_candidate_for_first_level = <function 'EnhancedCodingGenerator._normalize_candidate_for_first_level'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>) ; 'text'
    # FIXME: needs manual fix
    'return'
    _is_semantically_complete = <function 'EnhancedCodingGenerator._is_semantically_complete'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>) ; 'text'
    # FIXME: needs manual fix
    'return'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    _detect_concessive_spans = <function 'EnhancedCodingGenerator._detect_concessive_spans'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>[<?>[(<?>, <?>)]]) ; 'text'
    # FIXME: needs manual fix
    'return'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    _detect_negated_spans = <function 'EnhancedCodingGenerator._detect_negated_spans'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>[<?>[(<?>, <?>)]]) ; 'text'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    'return'
    _truncate_to_word = <function 'EnhancedCodingGenerator._truncate_to_word'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>) ; 'text'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    'return'
    _smart_abbreviate = <function 'EnhancedCodingGenerator._smart_abbreviate'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>) ; 'text'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    'return'
    _limit_first_level_text = <function 'EnhancedCodingGenerator._limit_first_level_text'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>) ; (None, None) ; 'processed_data'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[(<?>, <?>)] ; 'progress_callback'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[<?>] ; 'coding_thresholds'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[<?>[(<?>, <?>)]] ; 'return'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    generate_codes_with_trained_model = <function 'EnhancedCodingGenerator.generate_codes_with_trained_model'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>, <?>, <?>[(<?>, <?>)]) ; (None, False, None) ; 'processed_data'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[(<?>, <?>)] ; 'progress_callback'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[<?>] ; 'use_trained_model'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[<?>[(<?>, <?>)]] ; 'return'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    generate_grounded_theory_codes_multi_files = <function 'EnhancedCodingGenerator.generate_grounded_theory_codes_multi_files'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>, <?>, <?>, <?>, <?>[(<?>, <?>)]) ; (None, None, None) ; 'processed_data'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[(<?>, <?>)] ; 'progress_callback'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[<?>] ; 'coding_thresholds'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[<?>[(<?>, <?>)]] ; 'return'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    generate_codes_with_rules = <function 'EnhancedCodingGenerator.generate_codes_with_rules'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>, <?>, <?>[(<?>, <?>)]) ; (None, None) ; 'sentences'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[<?>[(<?>, <?>)]] ; 'coding_options'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[<?>[(<?>, <?>)]] ; 'return'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    generate_first_level_codes = <function 'EnhancedCodingGenerator.generate_first_level_codes'>
    _init_rag_components = <function 'EnhancedCodingGenerator._init_rag_components'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>[(<?>, <?>[<?>])]) ; 'return'
    _ensure_anchor_index = <function 'EnhancedCodingGenerator._ensure_anchor_index'>
    # FIXME: needs manual fix
    (<?>, <?>) ; 'candidates'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[<?>[(<?>, <?>)]] ; 'return'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[<?>]
    # FIXME: needs manual fix
    _best_candidate_names = <function 'EnhancedCodingGenerator._best_candidate_names'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>[(<?>, <?>[<?>])]) ; 'return'
    _build_cluster_query = <function 'EnhancedCodingGenerator._build_cluster_query'>
    # FIXME: needs manual fix
    (<?>, <?>) ; 'text'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[<?>[(<?>, <?>)]] ; 'return'
    # FIXME: needs manual fix
    _try_keyword_second_match = <function 'EnhancedCodingGenerator._try_keyword_second_match'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>, <?>, <?>[<?>]) ; 'second_name'
    # FIXME: needs manual fix
    'return'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    _lookup_second_code_by_name = <function 'EnhancedCodingGenerator._lookup_second_code_by_name'>
    _refresh_rag_matcher_if_needed = <function 'EnhancedCodingGenerator._refresh_rag_matcher_if_needed'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>[<?>[(<?>, <?>)]]) ; (None,) ; 'first_level_codes'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[(<?>, <?>[<?>])] ; 'return'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    generate_second_level_codes_improved = <function 'EnhancedCodingGenerator.generate_second_level_codes_improved'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>[(<?>, <?>[<?>])]) ; 'first_level_codes'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[(<?>, <?>[<?>])] ; 'return'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    _generate_second_level_codes_keyword_based = <function 'EnhancedCodingGenerator._generate_second_level_codes_keyword_based'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>[(<?>, <?>[<?>])]) ; 'second_level_codes'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[(<?>, <?>[<?>])] ; 'return'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    generate_third_level_codes_improved = <function 'EnhancedCodingGenerator.generate_third_level_codes_improved'>
    # FIXME: needs manual fix
    (<?>, <?>, <?>, <?>[(<?>, <?>[<?>])]) ; 'second_level_codes'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    <?>[(<?>, <?>[<?>])] ; 'return'
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    # FIXME: needs manual fix
    _generate_third_level_codes_rule_based = <function 'EnhancedCodingGenerator._generate_third_level_codes_rule_based'>
    (<?>, <?>, <?>, <?>[(<?>, <?>[<?>])])

    def _clean_code_prefix(code):
        if code: goto 8
        return code
        punctuation_to_remove = '^[。！？，、；：…—·●○◆◇■□▲△▼▽★☆※\\s]+'
        cleaned = re.sub(punctuation_to_remove, '', code)
        return cleaned.strip()

    def __init__(self):
        5.min_sentence_length = self
        0.6.similarity_threshold = self
        5.max_codes_per_paragraph = self
        if not Config: goto 34
        # FIXME: needs manual fix
        getattr(Config, 'FIRST_LEVEL_CODE_MAX_LENGTH', 30)
        30.max_first_level_length = self
        {}.abstract_cache = self
        {}.similarity_cache = self
        # FIXME: needs manual fix
        [] ; ('比如说', '这?种我', '我这种', '然后', '就是说', '还可以$', '^不是', '^就是', '^所以', '^这跳出来了', '^我刚刚说的是', '^我说的是', '^其实', '^那么', '^然后', '^对[，,]?', '^我自己来说的话[，,]?', '^如果说是', '\\[[0-9]+\\]$', '对对$')
        bad_phrase_patterns = self
        {}.colloquial_to_formal = self
        1.0.coding_worthy_min_salience = self
        8.coding_worthy_min_length = self
        None.coding_library = self
        if not CodingLibraryManager: goto 710
        # try:
        CodingLibraryManager().coding_library = self
        logger.info('编码库管理器初始化成功')
        {} ; '搞': '开展' ; '弄': '处理' ; '做': '执行' ; '干': '实施' ; '很难': '困难' ; '太难': '困难' ; '太多': '过多' ; '不够': '不足' ; '老是': '频繁' ; '总是': '持续' ; '总是要': '需持续' ; '特别': '显著' ; '非常': '明显' ; '慢慢': '逐步' ; '很快': '迅速' ; '一下子': '骤然' ; '好多': '大量' ; {} ; '一些': '部分' ; '一点点': '微量' ; '经常': '频繁' ; '有时候': '偶尔' ; '每次都': '每次均' ; '没有办法': '受限' ; '没法': '受限' ; '差不多': '相近' ; '基本上': '大体' ; '大部分': '多数' ; '少部分': '少数' ; '关键是': '关键在于' ; '带来了': '引发' ; '造成了': '导致' ; '使得': '促使' ; '没有了': '丧失' ; '失去了': '丧失' ; {} ; '会变得': '将转为' ; '变成了': '转化为' ; '主要是要': '需' ; '就需要': '需' ; '更好的': '优化' ; '越来越': '日益' ; '更加': '更趋' ; '想办法': '寻求方案' ; '看一下': '评估' ; '看一看': '审视' ; '找一下': '排查' ; '做出来': '产出' ; '弄出来': '产出' ; '搞出来': '产出' ; '可能是': '可能源于' ; '会不会': '是否' ; '是不是': '是否' ; {} ; '能不能': '能否' ; '要不要': '是否需' ; '有没有': '是否存在' ; '没办法': '受限' ; '没什么': '缺乏' ; '不算': '未达' ; '不太': '不足' ; '不怎么': '较少' ; '不大': '有限' ; '好多时候': '多数情形下' ; '有的时候': '部分情形下' ; '有些时候': '偶发情形下' ; '把人': '将人员' ; '给到': '提供' ; '问到': '询问' ; '提到': '提及' ; '说到': '提及' ; {} ; '讲到': '阐述' ; '觉得': '认为' ; '想知道': '关注' ; '想着': '意图' ; '想要': '期望' ; '卖': '销售' ; '买': '购买' ; '聚拢': '吸引' ; '拉来': '引入' ; '带过来': '引入' ; '主要是做': '从事' ; '主要是为了': '旨在' ; '主要是把': '将' ; '为了卖': '以销售' ; '为了买': '以购买' ; '就是为了': '旨在' ; '就是为了卖': '以销售为核心'
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        e = None
        # try:
        logger.error('初始化编码库管理器失败: ' + str(e))
        # except
        del e
        # FIXME: needs manual fix
        del e
        raise
        raise
        None.semantic_matcher = self
        None.quality_learner = self
        if not HighQualitySampleLearner: goto 882
        # try:
        HighQualitySampleLearner().quality_learner = self
        os = os
        sample_path = os.path.join(os.path.dirname(__file__), 'csv', 'standard_train_optimized.csv')
        if not os.path.exists(sample_path): goto 808
        self.quality_learner.load_samples(sample_path)
        logger.info('高质量样本学习器初始化成功')
        # FIXME: needs manual fix
        logger.warning('高质量样本文件不存在: ' + str(sample_path))
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        e = None
        # try:
        logger.error('初始化高质量样本学习器失败: ' + str(e))
        # except
        del e
        # FIXME: needs manual fix
        del e
        raise
        raise
        if not SemanticMatcher: goto 966
        # try:
        SemanticMatcher().semantic_matcher = self
        logger.info('语义匹配器初始化成功')
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        e = None
        # try:
        logger.error('初始化语义匹配器失败: ' + str(e))
        # except
        del e
        # FIXME: needs manual fix
        del e
        raise
        raise
        False.rag_enabled = self
        None.runtime_strategy = self
        None.rag_matcher = self
        None.decision_policy = self
        None.first_level_clusterer = self
        None.rag_index_manager = self
        {}._first_level_trace_meta = self
        {}._second_level_decision_meta = self
        [].first_level_prototypes = self
        self._default_second_threshold().rag_second_level_threshold = self
        self._default_third_threshold().rag_third_level_threshold = self
        self._default_cluster_threshold().rag_cluster_similarity_threshold = self
        None.rag_doc_retriever = self
        None.knn_abstract_generator = self
        None.t5_generative_coder = self
        None
        self._init_rag_components()

    def _ensure_first_level_defaults(self):
        if hasattr(self, 'abstract_cache'): goto 16
        {}.abstract_cache = self
        if hasattr(self, 'max_first_level_length'): goto 48
        if not Config: goto 42
        # FIXME: needs manual fix
        getattr(Config, 'FIRST_LEVEL_CODE_MAX_LENGTH', 30)
        30.max_first_level_length = self
        if hasattr(self, '_first_level_trace_meta'): goto 64
        {}._first_level_trace_meta = self
        if hasattr(self, 'first_level_prototypes'): goto 80
        [].first_level_prototypes = self
        # FIXME: needs manual fix
        [] ; ('^其实', '^我觉得', '^我认为', '^我感觉', '^如果说', '^然后', '^那么', '^就是说', '\\[[0-9]+\\]$')
        clean_patterns = None
        if not hasattr(self, 'bad_phrase_patterns'): goto 130
        if not isinstance(self.bad_phrase_patterns, list): goto 130
        if not any(<function 'EnhancedCodingGenerator._ensure_first_level_defaults.<locals>.<genexpr>'>(iter(self.bad_phrase_patterns))): goto 144
        list(clean_patterns).bad_phrase_patterns = self
            # <genexpr>
                # FIXME: for loop)
                pattern = .0
                yield ('?' in pattern)
                <generator>
                # FIXME: needs manual fix

    def _default_second_threshold(self):
        if not Config: goto 20
        return float(getattr(Config, 'RAG_SECOND_LEVEL_THRESHOLD', 0.4))
        return 0.4

    def _default_third_threshold(self):
        if not Config: goto 20
        return float(getattr(Config, 'RAG_THIRD_LEVEL_THRESHOLD', 0.4))
        return 0.4

    def _default_cluster_threshold(self):
        if not Config: goto 20
        return float(getattr(Config, 'RAG_CLUSTER_SIMILARITY_THRESHOLD', 0.76))
        return 0.76

    def _clamp_threshold(self, value, default):
        if not (value is None): goto 12
        return default
        # try:
        threshold = float(value)
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        default
        # except
        raise
        if not (threshold < 0.0): goto 64
        return 0.0
        if not (threshold > 1.0): goto 76
        return 1.0
        return threshold

    def _ensure_rag_threshold_defaults(self):
        if hasattr(self, 'rag_second_level_threshold'): goto 20
        self._default_second_threshold().rag_second_level_threshold = self
        if hasattr(self, 'rag_third_level_threshold'): goto 40
        self._default_third_threshold().rag_third_level_threshold = self
        if hasattr(self, 'rag_cluster_similarity_threshold'): goto 64
        self._default_cluster_threshold().rag_cluster_similarity_threshold = self

    def configure_similarity_thresholds(self, second_threshold, third_threshold, cluster_threshold):
        self._ensure_rag_threshold_defaults()
        self._clamp_threshold(second_threshold, self.rag_second_level_threshold).rag_second_level_threshold = self
        self._clamp_threshold(third_threshold, self.rag_third_level_threshold).rag_third_level_threshold = self
        self._clamp_threshold(cluster_threshold, self.rag_cluster_similarity_threshold).rag_cluster_similarity_threshold = self
        if not (self.first_level_clusterer is not None): goto 76
        self.rag_cluster_similarity_threshold.similarity_threshold = self.first_level_clusterer
        self._rebuild_decision_policy_from_matcher()

    def _apply_similarity_threshold_options(self, coding_thresholds):
        if coding_thresholds: goto 8
        threshold_options = <function 'EnhancedCodingGenerator._apply_similarity_threshold_options.<locals>.<dictcomp>'>(iter(('second_threshold', 'third_threshold', 'cluster_threshold')))
        if not threshold_options: goto 50
        # FIXME: needs manual fix
        (coding_thresholds) ; self.configure_similarity_thresholds ; () ; {**{}, **threshold_options}
            # <dictcomp>
                # FIXME: for loop)
                key = .0
                if not (key in coding_thresholds): goto 4
                # FIXME: needs manual fix
                {} ; key: coding_thresholds[key]

    def _repair_first_level_sentence_detail(self, sentence):
        if sentence: goto 8
        detail = sentence({})
        if detail.get('content', ''): goto 48
        if detail.get('original_content', ''): goto 48
        content = detail.get('original_content', '')(detail.get('text', '')).strip()
        if not content: goto 78
        if detail.get('content'): goto 78
        content[detail] = 'content'
        if not content: goto 100
        if detail.get('original_content'): goto 100
        content[detail] = 'original_content'
        if detail.get('sentence_id', ''): goto 136
        if detail.get('code_id', ''): goto 136
        sentence_id = detail.get('code_id', '')(detail.get('number', '')).strip().strip('[]')
        if sentence_id: goto 196
        all_markers = re.findall('\\[(\\d+)\\]', content)
        if not all_markers: goto 196
        sentence_id = all_markers[-1]
        logger.info('从内容中提取最后一个编号 [' + str(sentence_id) + '] 作为sentence_id')
        dict ; str ; detail.get('content', '') ; str ; detail.get('sentence_id', '')
        if not sentence_id: goto 294
        content_clean = re.sub('\\[\\d+\\]', '', content).strip()
        if re.search('^(?:说话人|讲话人)\\s*\\d+$', content_clean): goto 242
        if not re.search('^(受访者|采访者|被访者|主持人|采访员|提问者)$', content_clean): goto 294
        logger.warning("内容 '" + str(content_clean) + "' 只是说话人标签，移除关联编号 [" + str(sentence_id) + ']')
        sentence_id = ''
        detail.pop('sentence_id', None)
        detail.pop('code_id', None)
        if not sentence_id: goto 314
        sentence_id[detail] = 'sentence_id'
        sentence_id[detail] = 'code_id'
        return detail

    def _first_level_anchor_ratio(self, code_text, source_text):
        if code_text: goto 14
        code_chars = str(iter(code_text('')))
        if source_text: goto 38
        source_chars = <function 'EnhancedCodingGenerator._first_level_anchor_ratio.<locals>.<genexpr>'>(str(iter(source_text(''))))
        if code_chars: goto 56
        return 0.0
        <function 'EnhancedCodingGenerator._first_level_anchor_ratio.<locals>.<listcomp>'> ; set
        return ((source_chars)(<function 'EnhancedCodingGenerator._first_level_anchor_ratio.<locals>.<genexpr>'>(iter(code_chars))) / max(1, len(code_chars)))
        sum
            # <listcomp>
                # FIXME: for loop)
                ch = .0
                if not re.match('[\\u4e00-\\u9fffA-Za-z0-9]', ch): goto 4
                # FIXME: needs manual fix
                [] ; ch
            # <genexpr>
                # FIXME: for loop)
                ch = .0
                if not re.match('[\\u4e00-\\u9fffA-Za-z0-9]', ch): goto 4
                yield ch
                <generator>
                # FIXME: needs manual fix
            # <genexpr>
                # FIXME: for loop)
                ch = .0
                if not (ch in source_chars): goto 4
                yield 1
                <generator>
                # FIXME: needs manual fix

    def _is_low_quality_first_level_code(self, code_text, source_text, is_knn):
        if code_text: goto 8
        clean = code_text.strip()
        if source_text: goto 24
        source = source_text.strip()
        if clean: goto 40
        return True
        str ; str
        if not (len(clean) < 4): goto 56
        return True
        if not self._looks_semantically_incomplete(clean): goto 70
        return True
        if self._has_valid_first_level_pos_pattern(clean): goto 84
        return True
        if not re.search('^(?:说话人|讲话人)\\s*\\d+$', clean): goto 100
        return True
        if not re.search('^(受访者|采访者|被访者|主持人|采访员|提问者)$', clean): goto 116
        return True
        if not Config: goto 138
        # FIXME: needs manual fix
        getattr ; self ; 'max_first_level_length' ; getattr(Config, 'FIRST_LEVEL_CODE_MAX_LENGTH', 30)
        max_len = None(<?>, <?>, 30)
        if not isinstance(max_len, int): goto 178
        if not (max_len > 0): goto 178
        if not (len(clean) > max_len): goto 178
        return True
        if not self._is_question_like(clean): goto 192
        return True
        if not re.search('(什么|怎么|哪些|怎么样|如何|哪方面|什么时候|什么程度|什么样)', clean): goto 208
        return True
        if not re.search('(的|了|着|过|到|在|中|和|与|或|并|又|还|也|只|不|没)$', clean): goto 234
        if self._has_first_level_information_cue(clean): goto 234
        return True
        if not re.search('^(这|那|哪|什么|怎么).{0,6}(的|方面|事情|问题|情况|流程|模式|渠道|方法)', clean): goto 250
        return True
        if not re.search('[（(]?\\d{1,2}:\\d{2}[)）]?', clean): goto 266
        return True
        if not re.search('\\[[A-Z]?\\d+\\]', clean): goto 282
        return True
        if not re.search('(没有办法|没办法).*(这个公司|那个时候|因为)', clean): goto 298
        return True
        if not re.search('^(我|我们|你|他|他们)?也?(没有办法|没办法|不知道|不清楚|不确定)', clean): goto 314
        return True
        if not ('这个公司' in clean): goto 326
        return True
        if not re.search('\\u90a3\\u4e2a\\u65f6\\u5019\\u662f\\d+$', clean): goto 342
        return True
        if not re.search('^(后来发现|后来|发现因为|因为他们|因为他|因为我们)', clean): goto 358
        return True
        if not re.search('(后来发现因为|那个时候主要在)', clean): goto 374
        return True
        if not re.search('^(先给您介绍|先给你介绍|先介绍一下|本次访谈|下面介绍)', clean): goto 390
        return True
        if not re.search('^\\D*(?:\\d{1,2}年|\\d{1,2}月份|\\d{1,2}月)', clean): goto 416
        if self._has_first_level_information_cue(clean): goto 416
        return True
        if not re.search('(这块|这一块|那种|这个来做|那个来做)', clean): goto 442
        if self._has_first_level_information_cue(clean): goto 442
        return True
        if not re.search('^(当时|以前|正好|公司原来|我下面|我去做了|我自行|你的|你做|任务一定要|人人的)', clean): goto 468
        if self._has_first_level_information_cue(clean): goto 468
        return True
        if not ('那个时候' in clean): goto 490
        if self._has_first_level_information_cue(clean): goto 490
        return True
        if not re.search('^(因为|所以|但是|不过|然后|如果|其实|就是|那个|这个|后来|当时|我们|我|你|他|他们)', clean): goto 522
        if re.search('(导致|影响|推动|形成|引入|转变|降低|提高|获得|支持|需求|资源|客户)', clean): goto 522
        return True
        if not re.search('(什么的|之类的|那种感觉|这种感觉|这样子|那样子|怎么说呢|就是说|我觉得|相当于|要看|分场合|这个东西|这个事情|这个问题)$', clean): goto 540
        return True
        if not re.search('(我们认为|我认为|我觉得|我觉得应该|我觉得可以|我觉得可能|我觉得会)', clean): goto 558
        return True
        if not re.search('(开始|进行|做了|搞了|弄了|整了)', clean): goto 588
        if self._has_first_level_information_cue(clean): goto 588
        return True
        if not ('没有办法直接去借鉴同行业' in source): goto 602
        return True
        if not (len(clean) <= 5): goto 632
        if self._has_first_level_information_cue(clean): goto 632
        return True
        if not source: goto 666
        if is_knn: goto 666
        if not (self._first_level_anchor_ratio(clean, source) < 0.4): goto 666
        return True
        if not ('您' in clean): goto 692
        if self._has_first_level_information_cue(clean): goto 692
        return True
        if not re.search('^(是|在|从|对|把|被|让|给|叫|和|与|或|的)', clean): goto 736
        if not (len(clean) <= 6): goto 736
        if self._has_first_level_information_cue(clean): goto 736
        return True
        if not clean.startswith('的'): goto 766
        if not (len(clean) <= 8): goto 766
        return True
        if not re.search('(对不对|是不是|行不行|能不能|有没有|要不要)', clean): goto 784
        return True
        if not re.search('^(以下|以上|这边|那边|前面|后面)', clean): goto 802
        return True
        if not (len(clean) > 24): goto 836
        if not (clean.count('，') >= 1): goto 836
        return True
        if not re.search('[出对在到各每较\\d]$', clean): goto 880
        if not (len(clean) <= 8): goto 880
        if self._has_first_level_information_cue(clean): goto 880
        return True
        if not re.search('(外面|里面|后面|前面|上面|下面)$', clean): goto 910
        if self._has_first_level_information_cue(clean): goto 910
        return True
        if not self.quality_learner: goto 948
        if self.quality_learner.is_high_quality_like(clean): goto 948
        logger.debug('编码不符合高质量模式: ' + str(clean))
        return False

    def _has_first_level_information_cue(self, text):
        if text: goto 8
        t = text.strip()
        if t: goto 24
        return False
        return bool(re.search('(引入|建立|调整|获得|降低|提高|推动|解决|分析|反馈|合作|转变|优化|对接|支持|审批|流程|受影响|受限|不足|短板|导向|循环|机会|需求|资源|服务|监督|指引|开发|探索|协调|整合|压力|风险|保鲜|价值|活动|增长|转型|感知|评价|约束|冲突|规范|惯例|随意|机制|平台|系统|品牌|团队|客户|治理|场景|能力|策略|路径|结构|模式|种植|养殖|加工|收购|销售|土地|农田|灌溉|施肥|收割|品种|产量|品质|有机|绿色|市场|价格|成本|利润|收入|投资|资金|贷款|保险|补贴|税收|消费|购买|供应链|贸易|工艺|手工|技术|传承|培训|制作|原料|工具|设备|标准|质量|检验|认证|生产|优点|好处|优势|缺点|缺陷|问题|关键|核心|重要|主要|根本|本质|特色|亮点|突破|诊疗|康复|护理|患者|医保|药品|临床|公共卫生|健康管理|中医|慢病|教学|课程|师资|学员|教材|职业教育|技能培训|素质教育|在线教育|社区|公益|民生|基层|志愿服务|社区营造|城市更新|旧改|可持续|赋能|非遗|手艺|技艺|传承人|工匠|文创|手工艺|陶艺|织造|雕刻|民俗|古建筑|修缮|文物|文旅|景区|民宿|电商|直播|流量|运营|营销|转化|复购|渠道|粉丝)', t))

    def _looks_semantically_incomplete(self, text):
        if text: goto 8
        t = text.strip()
        if t: goto 24
        return True
        if not (len(t) <= 3): goto 40
        return True
        if not self._is_question_like(t): goto 54
        return True
        if not re.search('^(因为|所以|但是|不过|然后|如果|就是|其实|那个|这个|后来|当时)$', t): goto 70
        return True
        if not re.search('^(因为|所以|但是|不过|然后|如果|就是|其实|那个|这个|后来|当时)', t): goto 96
        if self._has_first_level_information_cue(t): goto 96
        return True
        if not re.search('(这个|那个|这块|这一块|那种|这种|这样|那样)$', t): goto 112
        return True
        if not re.search('(什么的|之类的)$', t): goto 128
        return True
        if self._has_first_level_information_cue(t): goto 154
        if not (len(t) <= 6): goto 154
        return True
        if not re.search('(的|了|着|过|到|在|中|和|与|或|又|还|也|只|不|没)$', t): goto 180
        if self._has_first_level_information_cue(t): goto 180
        return True
        if not re.search('(什么|怎么|哪些|怎么样|什么样|如何)', t): goto 208
        if re.search('(机制|流程|资源|策略|路径|模式|结构|能力|需求|服务|创新|管理|评估|质量|安全|风险)', t): goto 208
        return True
        if not re.search('^(是|对|把|被|让|给|从|由|和|与|的)', t): goto 246
        if not (len(t) <= 6): goto 246
        if self._has_first_level_information_cue(t): goto 246
        return True
        if not re.search('(的比较|会比较|较为)$', t): goto 272
        if self._has_first_level_information_cue(t): goto 272
        return True
        if not (len(t) <= 3): goto 298
        if self._has_first_level_information_cue(t): goto 298
        return True
        if not ('您' in t): goto 320
        if self._has_first_level_information_cue(t): goto 320
        return True
        return False

    def _has_valid_first_level_pos_pattern(self, text):
        if text: goto 8
        t = text.strip()
        if t: goto 24
        return False
        # try:
        tokens = <function 'EnhancedCodingGenerator._has_valid_first_level_pos_pattern.<locals>.<listcomp>'>(iter(pseg.cut(t)))
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        # except
        return True
        raise
        if tokens: goto 78
        return False
        words = <function 'EnhancedCodingGenerator._has_valid_first_level_pos_pattern.<locals>.<listcomp>'>(iter(tokens))
        flags = <function 'EnhancedCodingGenerator._has_valid_first_level_pos_pattern.<locals>.<listcomp>'>(iter(tokens))
        # FIXME: needs manual fix
        {} ; {'他', '他们', '你', '你们', '她', '她们', '它', '它们', '我', '我们'}
        pronouns = None
        # FIXME: needs manual fix
        {} ; {'么', '吗', '吧', '呀', '呗', '呢', '哈', '哦', '啊', '啦', '嘛', '欸', '诶'}
        modal_particles = None
        # FIXME: needs manual fix
        {} ; {'其实', '后来', '就是', '当时', '然后', '这个', '那个'}
        weak_starters = None
        if not (modal_particles)(<function 'EnhancedCodingGenerator._has_valid_first_level_pos_pattern.<locals>.<genexpr>'>(iter(words))): goto 156
        return False
        any
        if not (pronouns)(<function 'EnhancedCodingGenerator._has_valid_first_level_pos_pattern.<locals>.<genexpr>'>(iter(words))): goto 182
        return False
        any
        if not words: goto 212
        if not (words[0] in weak_starters): goto 212
        if self._has_first_level_information_cue(t): goto 212
        return False
        noun_like = any(<function 'EnhancedCodingGenerator._has_valid_first_level_pos_pattern.<locals>.<genexpr>'>(iter(flags)))
        verb_like = any(<function 'EnhancedCodingGenerator._has_valid_first_level_pos_pattern.<locals>.<genexpr>'>(iter(flags)))
        adj_like = any(<function 'EnhancedCodingGenerator._has_valid_first_level_pos_pattern.<locals>.<genexpr>'>(iter(flags)))
        if noun_like: goto 274
        return False
        if verb_like: goto 296
        if adj_like: goto 296
        if self._has_first_level_information_cue(t): goto 296
        return False
        return True
            # <listcomp>
                # FIXME: for loop)
                word = <unpack_2>
                flag = .0
                if not str(word).strip(): goto 4
                # FIXME: needs manual fix
                [] ; (word.strip(), flag)
            # <listcomp>
                # FIXME: for loop)
                word = <unpack_2>
                _ = .0
                # FIXME: needs manual fix
                [] ; word
            # <listcomp>
                # FIXME: for loop)
                _ = <unpack_2>
                flag = .0
                # FIXME: needs manual fix
                [] ; flag
            # <genexpr>
                # FIXME: for loop)
                word = .0
                yield (word in modal_particles)
                <generator>
                # FIXME: needs manual fix
            # <genexpr>
                # FIXME: for loop)
                word = .0
                yield (word in pronouns)
                <generator>
                # FIXME: needs manual fix
            # <genexpr>
                # FIXME: for loop)
                flag = .0
                yield flag.startswith(('n', 's', 'nt', 'nz'))
                <generator>
                # FIXME: needs manual fix
            # <genexpr>
                # FIXME: for loop)
                flag = .0
                yield flag.startswith('v')
                <generator>
                # FIXME: needs manual fix
            # <genexpr>
                # FIXME: for loop)
                flag = .0
                yield flag.startswith('a')
                <generator>
                # FIXME: needs manual fix

    def _contains_colloquial_residue(self, text):
        if text: goto 8
        t = text('')
        if re.search('(怎么说呢|就是说|我觉得|相当于|要看|分场合|这个东西|这个事情|这个问题|就是那种|就这种|类似这种)', t): goto 84
        if re.search('[吧呢啊嘛呀哦哈哎诶噢呃]', t): goto 84
        if re.search('(我的|我们的|你们的|他们的|他的|她的)', t): goto 84
        if re.search('(^|[，,、；;])(?:我|我们|你|你们|他|他们|她|她们)(?:也|将|会|跟|和|在|购买|参与|提出|能够|可以|需要|喜欢|已经|当时|就|都|只|要|是|有|不再)', t): goto 84
        if re.search('^(然后|就是|所以|但是|不过|其实|那个|这个|后来|当时)', t): goto 84
        return re.search('^(然后|就是|所以|但是|不过|其实|那个|这个|后来|当时)', t)(re.search('(什么的|之类的|那种感觉|这种感觉|这样子|那样子)$', t))
        str ; bool ; re.search('(怎么说呢|就是说|我觉得|相当于|要看|分场合|这个东西|这个事情|这个问题|就是那种|就这种|类似这种)', t) ; re.search('[吧呢啊嘛呀哦哈哎诶噢呃]', t) ; re.search('(我的|我们的|你们的|他们的|他的|她的)', t) ; re.search('(^|[，,、；;])(?:我|我们|你|你们|他|他们|她|她们)(?:也|将|会|跟|和|在|购买|参与|提出|能够|可以|需要|喜欢|已经|当时|就|都|只|要|是|有|不再)', t)

    def _canonicalize_first_level_candidate_rows(self, candidate_rows, source_text):
        canonical_rows = []
        seen = {}
        # FIXME: for loop)
        row = iter(candidate_rows)
        if row.get('text', ''): goto 36
        if row.get('knn_source'): goto 60
        canonical = row.get('text', '')(source_text, bool, row.get('knn_source')(row.get('anchor_source')))
        if canonical: goto 74
        # FIXME: needs manual fix
        self._finalize_first_level_candidate ; str
        new_row = dict(row)
        canonical[new_row] = 'text'
        round(float(self._conservative_first_level_rank_score(new_row)), 4)[new_row] = 'conservative_score'
        existing = seen.get(canonical)
        if not (existing is None): goto 156
        len(canonical_rows)[seen] = canonical
        canonical_rows.append(new_row)
        # FIXME: needs manual fix
        current = canonical_rows[existing]
        if (new_row.get('conservative_score', float('-inf')) > current.get('conservative_score', float('-inf'))): goto 260
        if not (new_row.get('conservative_score', float('-inf')) == current.get('conservative_score', float('-inf'))): goto 268
        if not (new_row.get('rule_score', float('-inf')) > current.get('rule_score', float('-inf'))): goto 268
        new_row[canonical_rows] = existing
        # FIXME: needs manual fix
        return canonical_rows

    def _split_first_level_candidate_segments(self, text):
        if text: goto 8
        text = text.strip()
        if text: goto 24
        return []
        segments = []
        sentences = re.split('[。！？!?]+', text)
        # FIXME: for loop)
        sentence = iter(sentences)
        sentence = sentence.strip()
        if sentence: goto 62
        # FIXME: needs manual fix
        semantic_chunks = self._extract_semantic_chunks(sentence)
        if not semantic_chunks: goto 88
        segments.extend(semantic_chunks)
        # FIXME: needs manual fix
        parts = re.split('[，,、；;：:\\n\\r]+', sentence)
        segments.extend(<function 'EnhancedCodingGenerator._split_first_level_candidate_segments.<locals>.<listcomp>'>(iter(parts)))
        # FIXME: needs manual fix
        return segments
            # <listcomp>
                # FIXME: for loop)
                part = .0
                if not part: goto 4
                if not part.strip(): goto 4
                # FIXME: needs manual fix
                [] ; part.strip()

    def _extract_semantic_chunks(self, text):
        chunks = []
        # FIXME: needs manual fix
        [] ; ('([\\u4e00-\\u9fa5]+[动词]+[\\u4e00-\\u9fa5]+[名词]+[\\u4e00-\\u9fa5]+)', '([\\u4e00-\\u9fa5]+[动词]+[\\u4e00-\\u9fa5]+[名词])', '([\\u4e00-\\u9fa5]+[名词]+[\\u4e00-\\u9fa5]+[动词]+[\\u4e00-\\u9fa5]+[名词])', '([\\u4e00-\\u9fa5]+[形容词]+[\\u4e00-\\u9fa5]+[名词]+[\\u4e00-\\u9fa5]+[名词])')
        patterns = None
        # FIXME: needs manual fix
        {} ; {'优化', '创新', '协调', '合作', '对接', '建立', '开发', '开展', '引入', '形成', '影响', '探索', '推动', '提高', '支持', '整合', '获得', '解决', '调整', '转变', '追求', '降低'}
        verb_list = None
        # FIXME: needs manual fix
        {} ; {'反馈', '品牌', '团队', '场景', '客户', '平台', '服务', '机制', '模式', '治理', '策略', '系统', '结构', '能力', '资源', '路径', '需求'}
        noun_list = None
        # try:
        tokens = list(pseg.cut(text))
        # FIXME: for loop)
        i = iter(range(len(tokens)))
        # FIXME: for loop)
        j = iter(range((i + 1), min((len(tokens) + 1), (i + 5))))
        chunk = ''.join(<function 'EnhancedCodingGenerator._extract_semantic_chunks.<locals>.<listcomp>'>(iter(tokens[slice(i, j)])))
        if (len(chunk) < 4): goto 148
        if not (len(chunk) > 30): goto 150
        # FIXME: needs manual fix
        pos_tags = <function 'EnhancedCodingGenerator._extract_semantic_chunks.<locals>.<listcomp>'>(iter(tokens[slice(i, j)]))
        has_verb = (verb_list)(<function 'EnhancedCodingGenerator._extract_semantic_chunks.<locals>.<genexpr>'>(iter(tokens[slice(i, j)])))
        has_noun = (noun_list)(<function 'EnhancedCodingGenerator._extract_semantic_chunks.<locals>.<genexpr>'>(iter(tokens[slice(i, j)])))
        if not has_verb: goto 258
        if not has_noun: goto 258
        if not (chunk not in chunks): goto 258
        chunks.append(chunk)
        any ; any
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        return chunks
        # FIXME: needs manual fix
        # except
        return chunks
        raise
            # <listcomp>
                # FIXME: for loop)
                word = <unpack_2>
                _ = .0
                # FIXME: needs manual fix
                [] ; word
            # <listcomp>
                # FIXME: for loop)
                _ = <unpack_2>
                flag = .0
                # FIXME: needs manual fix
                [] ; flag
            # <genexpr>
                # FIXME: for loop)
                word = <unpack_2>
                flag = .0
                if flag.startswith('v'): goto 28
                yield (word in verb_list)
                flag.startswith('v')
                <generator>
                # FIXME: needs manual fix
            # <genexpr>
                # FIXME: for loop)
                word = <unpack_2>
                flag = .0
                if flag.startswith('n'): goto 28
                yield (word in noun_list)
                flag.startswith('n')
                <generator>
                # FIXME: needs manual fix

    def _score_first_level_fragment(self, fragment, source_text):
        if fragment: goto 8
        clean = fragment.strip()
        if clean: goto 28
        return float('-inf')
        score = 0.0
        # FIXME: needs manual fix
        score ; (min(len(clean), 24) * 0.35)
        score = None
        if not self._is_semantically_complete(clean): goto 72
        # FIXME: needs manual fix
        score ; 2.0
        score = None
        # FIXME: needs manual fix
        score ; (self._first_level_anchor_ratio(clean, source_text) * 3.0)
        score = None
        if not re.search('^(追求|引入|建立|调整|获得|降低|提高|推动|解决|客户|越轨|创新|资源|需求|反馈|开展|优化|合作|转变|对接|影响)', clean): goto 112
        # FIXME: needs manual fix
        score ; 1.0
        score = None
        if not self.quality_learner: goto 162
        quality_score = self.quality_learner.score_by_pattern_match(clean)
        # FIXME: needs manual fix
        score ; (quality_score * 0.3)
        score = None
        if self.quality_learner.is_high_quality_like(clean): goto 162
        # FIXME: needs manual fix
        score ; 0.5
        score = None
        if not clean.startswith(('我觉得', '其实', '然后', '所以', '但是', '不过', '当时', '那个时候', '就是', '相当于', '要看', '分场合', '我们', '我', '你', '他', '他们')): goto 180
        # FIXME: needs manual fix
        score ; 1.0
        score = None
        if not self._contains_colloquial_residue(clean): goto 198
        # FIXME: needs manual fix
        score ; 2.0
        score = None
        if not re.search('(这个东西|这个事情|这个问题|什么的|之类的)$', clean): goto 218
        # FIXME: needs manual fix
        score ; 2.5
        score = None
        if not self._has_first_level_information_cue(clean): goto 236
        # FIXME: needs manual fix
        score ; 1.2
        score = None
        if not re.search('(受影响|受限|受阻|不足|短板|风险|压力|冲突)', clean): goto 256
        # FIXME: needs manual fix
        score ; 0.8
        score = None
        if not self._has_first_level_information_cue(text): goto 274
        # FIXME: needs manual fix
        score ; 1.2
        score = None
        if not re.search('(反馈|诉求|需求|受影响|短板|机会)', text): goto 294
        # FIXME: needs manual fix
        score ; 0.8
        score = None
        if not re.search('(主要负责|指引方向|监督结果|我们认为|我认为|我觉得)', text): goto 314
        # FIXME: needs manual fix
        score ; 0.7
        score = None
        return score

    def _finalize_first_level_candidate(self, text, source_text, is_knn):
        if text: goto 16
        candidate = self._normalize_candidate_for_first_level(str(text('')))
        if not bool(source_text): goto 66
        if candidate: goto 40
        if getattr(self, 'first_level_recall_bank', []): goto 62
        is_recall_label = (set in getattr(self, 'first_level_recall_bank', [])([]))
        if is_recall_label: goto 74
        is_external = is_knn
        if candidate: goto 84
        return ''
        self.rewrite_first_level_code ; bool(source_text) ; str ; candidate.strip() ; is_recall_label
        if not (len(candidate) < 4): goto 104
        if is_external: goto 104
        return ''
        if not (len(candidate) <= 5): goto 134
        if self._has_first_level_information_cue(candidate): goto 134
        if is_external: goto 134
        return ''
        if not re.search('(什么|怎么|哪些|怎么样|如何|哪方面|什么时候|什么样)', candidate): goto 150
        return ''
        if self._contains_colloquial_residue(candidate): goto 218
        if is_external: goto 180
        if self._is_low_quality_first_level_code(candidate, source_text, is_knn): goto 218
        formalized = self._formalize_code(candidate)
        if not (len(formalized) >= 4): goto 218
        if re.search('(的|了|着|过|到|在|中|和|与|或|又|还|也|只|不|没)$', formalized): goto 218
        return formalized
        best_fragment = ''
        best_score = float('-inf')
        # FIXME: for loop)
        fragment = iter(self._split_first_level_candidate_segments(candidate))
        refined = self.rewrite_first_level_code(self._normalize_candidate_for_first_level(fragment))
        if refined: goto 266
        # FIXME: needs manual fix
        if not (len(refined) < 4): goto 304
        if getattr(self, 'first_level_recall_bank', []): goto 296
        if not (set not in getattr(self, 'first_level_recall_bank', [])([])): goto 304
        # FIXME: needs manual fix
        refined
        if not (len(refined) <= 5): goto 352
        if self._has_first_level_information_cue(refined): goto 352
        if getattr(self, 'first_level_recall_bank', []): goto 344
        if not (set not in getattr(self, 'first_level_recall_bank', [])([])): goto 352
        # FIXME: needs manual fix
        refined
        if not self._contains_colloquial_residue(refined): goto 364
        # FIXME: needs manual fix
        if not self._is_question_like(refined): goto 376
        # FIXME: needs manual fix
        if not re.search('(什么|怎么|哪些|怎么样)', refined): goto 390
        # FIXME: needs manual fix
        if not self._is_low_quality_first_level_code(refined, source_text): goto 404
        # FIXME: needs manual fix
        score = self._score_first_level_fragment(refined, source_text)
        if not (score > best_score): goto 432
        best_score = score
        best_fragment = refined
        # FIXME: needs manual fix
        if not best_fragment: goto 532
        if not (len(best_fragment) > 20): goto 458
        threshold = 7.5
        # FIXME: needs manual fix
        if not (len(best_fragment) < 8): goto 476
        threshold = 6.5
        # FIXME: needs manual fix
        threshold = 5.5
        if not (best_score >= threshold): goto 532
        formalized = self._formalize_code(best_fragment)
        if not (len(formalized) >= 4): goto 532
        if re.search('(的|了|着|过|到|在|中|和|与|或|又|还|也|只|不|没)$', formalized): goto 532
        return formalized
        return ''

    def _conservative_first_level_rank_score(self, row):
        if row.get('text', ''): goto 20
        if row.get('source_text', ''): goto 38
        text = row.get('text', '')(str, row.get('source_text', ''))
        if text: goto 56
        return float('-inf')
        self._finalize_first_level_candidate ; str
        rerank_score = row.get('rerank_score')
        if not (rerank_score is not None): goto 82
        # FIXME: needs manual fix
        float(rerank_score)
        model_score = 0.0
        if row.get('rule_score', 0.0): goto 102
        rule_score = row.get('rule_score', 0.0)(0.0)
        if row.get('semantic_recall_score', 0.0): goto 122
        recall_score = row.get('semantic_recall_score', 0.0)(0.0)
        score = ((model_score * 10.0) + (min(rule_score, 6.0) * 0.25))
        if not Config: goto 298
        if not getattr(Config, 'FIRST_LEVEL_FUSED_RANKING', False): goto 298
        # FIXME: needs manual fix
        float ; float ; score ; (min(recall_score, 2.0) * float(getattr(Config, 'FIRST_LEVEL_RECALL_SCORE_WEIGHT', 1.8)))
        score = None
        # FIXME: needs manual fix
        score ; (min(max(rule_score, 0.0), 10.0) * float(getattr(Config, 'FIRST_LEVEL_RULE_SCORE_WEIGHT', 0.18)))
        score = None
        if not (row.get('semantic_recall_score') is not None): goto 252
        # FIXME: needs manual fix
        score ; 0.8
        score = None
        if not (row.get('semantic_recall_score') is not None): goto 298
        if not (len(text) <= 8): goto 298
        # FIXME: needs manual fix
        score ; float(getattr(Config, 'FIRST_LEVEL_SHORT_LABEL_BONUS', 2.5))
        score = None
        # FIXME: needs manual fix
        score ; (text.count('，') * 1.25)
        score = None
        # FIXME: needs manual fix
        score ; (max(0, (len(text) - 22)) * 0.18)
        score = None
        # FIXME: needs manual fix
        score ; (max(0, (len(text) - 30)) * 0.55)
        score = None
        if not re.search('^(时候|比如|然后|所以|那没有|会，因为|他们有时候|我们有时候)', text): goto 388
        # FIXME: needs manual fix
        score ; 2.5
        score = None
        if not re.search('(\\u8fd9\\u4e2a\\u4e8b\\u60c5|\\u8fd9\\u4e00\\u5757\\u76ee\\u524d\\u6211\\u4eec\\u80fd\\u591f|\\u90a3\\u4e2a\\u65f6\\u5019)', text): goto 408
        # FIXME: needs manual fix
        score ; 1.8
        score = None
        if not re.search('^(我们|他们|你们|大家|这个|那个|这种|这些|那些|他是|我是|你是)', text): goto 428
        # FIXME: needs manual fix
        score ; 1.4
        score = None
        if not re.search('(技术|品牌|资源|平台|机制|流程|生态|需求|问题|合作|协同|创新|服务|应用|模块|设备|系统|客户|团队|工业互联网)', text): goto 460
        if not (len(text) <= 16): goto 460
        # FIXME: needs manual fix
        score ; 0.7
        score = None
        return score

    def _model_semantic_similarity(self, a, b):
        if self.semantic_matcher: goto 10
        return -1.0
        # try:
        emb_fn = getattr(self.semantic_matcher, 'get_embedding', None)
        if emb_fn: goto 36
        return -1.0
        emb_a = emb_fn(a)
        emb_b = emb_fn(b)
        if (emb_a is None): goto 68
        if not (emb_b is None): goto 74
        return -1.0
        return float((np.dot(emb_a, emb_b) / ((np.linalg.norm(emb_a) * np.linalg.norm(emb_b)) + 1e-12)))
        # FIXME: needs manual fix
        # except
        return -1.0
        raise

    def _select_quality_first_level_candidate(self, trace, source_detail):
        if source_detail.get('original_content', ''): goto 36
        if source_detail.get('content', ''): goto 36
        source_text = source_detail.get('content', '')(source_detail.get('text', ''))
        if trace.get('selected_candidate', ''): goto 60
        selected = str(trace.get('selected_candidate', ''), source_text)
        if not selected: goto 100
        if self._is_low_quality_first_level_code(selected, source_text): goto 100
        if not self._validate_code_semantic_fit(selected, source_text): goto 100
        return selected
        str ; source_detail.get('original_content', '') ; self._finalize_first_level_candidate
        rows = list(trace.get('candidates', []))
        rows.sort(<function 'EnhancedCodingGenerator._select_quality_first_level_candidate.<locals>.<lambda>'>, True)
        # FIXME: for loop)
        row = iter(rows)
        if row.get('text', ''): goto 162
        candidate = str(row.get('text', ''), source_text)
        if not candidate: goto 248
        if self._is_low_quality_first_level_code(candidate, source_text): goto 248
        if not self._validate_code_semantic_fit(candidate, source_text): goto 248
        candidate[trace] = 'selected_candidate'
        # FIXME: for loop)
        candidate_row = iter(rows)
        (candidate_row.get('text') == row.get('text'))[candidate_row] = 'selected'
        # FIXME: needs manual fix
        self._finalize_first_level_candidate
        candidate
        # FIXME: needs manual fix
        return ''
                if not (item.get('rerank_score') is not None): goto 34
                # FIXME: needs manual fix
                item.get('conservative_score', -999.0) ; item.get('rerank_score')
                return (<?>, -1.0, item.get('rule_score', 0.0), -len(item.get('text', '')))

    def _validate_code_semantic_fit(self, code, source_text):
        if not code: goto 8
        if source_text: goto 12
        return True
        sim = self._model_semantic_similarity(code, source_text)
        if not (sim < 0): goto 36
        return True
        if not (sim < 0.3): goto 74
        "模型语义验证拒绝: '"(str(code) + "' 与原文语义关联过弱 (" + sim + format('.3f') + ')')
        logger.info
        return False
        if not (sim > 0.96): goto 112
        "模型语义验证拒绝: '"(str(code) + "' 与原文几乎相同，未完成抽象 (" + sim + format('.3f') + ')')
        logger.info
        return False
        return True

    def _score_first_level_fragment(self, fragment, source_text):
        if fragment: goto 8
        clean = fragment.strip()
        if clean: goto 28
        return float('-inf')
        score = 0.0
        # FIXME: needs manual fix
        score ; (min(len(clean), 24) * 0.35)
        score = None
        if not self._is_semantically_complete(clean): goto 72
        # FIXME: needs manual fix
        score ; 2.0
        score = None
        # FIXME: needs manual fix
        score ; (self._first_level_anchor_ratio(clean, source_text) * 3.0)
        score = None
        if not self._has_first_level_information_cue(clean): goto 110
        # FIXME: needs manual fix
        score ; 1.2
        score = None
        if not re.search('(反馈|诉求|需求|受影响|短板|机会)', clean): goto 130
        # FIXME: needs manual fix
        score ; 0.8
        score = None
        if not re.search('^(追求|引入|建立|调整|获得|降低|提高|推动|解决|客户|越轨|创新|资源|反馈|开展|优化|合作|转变|对接|影响|分析)', clean): goto 150
        # FIXME: needs manual fix
        score ; 1.0
        score = None
        if not clean.startswith(('我觉得', '其实', '然后', '所以', '但是', '不过', '当时', '那个时候', '就是', '相当于', '要看', '分场合', '后来', '以前因为', '当我')): goto 168
        # FIXME: needs manual fix
        score ; 2.0
        score = None
        if not self._contains_colloquial_residue(clean): goto 186
        # FIXME: needs manual fix
        score ; 3.0
        score = None
        if not re.search('(这个东西|这个事情|这个问题|这块|这一块|那种)$', clean): goto 206
        # FIXME: needs manual fix
        score ; 2.0
        score = None
        if not re.search('(主要负责|指引方向|监督结果)', clean): goto 226
        # FIXME: needs manual fix
        score ; 0.7
        score = None
        return score

    def _conservative_first_level_rank_score(self, row):
        _knn = bool(row.get('knn_source'))
        if row.get('text', ''): goto 34
        text = str(row.get('text', ''), _knn)
        if text: goto 56
        return float('-inf')
        self._finalize_first_level_candidate
        rerank_score = row.get('rerank_score')
        if not (rerank_score is not None): goto 82
        # FIXME: needs manual fix
        float(rerank_score)
        model_score = 0.0
        if row.get('rule_score', 0.0): goto 102
        rule_score = row.get('rule_score', 0.0)(0.0)
        score = ((model_score * 6.0) + (min(rule_score, 12.0) * 0.5))
        if row.get('source_text', ''): goto 144
        source_text = row.get('source_text', '')
        if not source_text: goto 272
        if not re.search('(不|没有|无需|从未|并未|毫不)', source_text): goto 272
        if re.search('(不|没有|无需|从未|并未|毫不)', text): goto 272
        # FIXME: for loop)
        m = iter(re.finditer('(不|没有|无需|从未|并未|毫不)(.{1,10})', source_text))
        positive_part = m.group(2)
        if not (len(positive_part) >= 2): goto 270
        common = (positive_part)(<function 'EnhancedCodingGenerator._conservative_first_level_rank_score.<locals>.<genexpr>'>(iter(text)))
        if not (common >= min((len(text) * 0.5), 3)): goto 270
        # FIXME: needs manual fix
        float ; str ; sum ; score ; 5.0
        score = None
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        semantic_cues = '(优点|好处|优势|缺点|缺陷|问题|关键|核心|重要|主要|根本|本质|特色|亮点|突破|创新)'
        if not source_text: goto 312
        if not re.search(semantic_cues, source_text): goto 312
        if not re.search(semantic_cues, text): goto 312
        # FIXME: needs manual fix
        score ; 2.5
        score = None
        if row.get('prototype_hits'): goto 324
        prototype_hits = []
        if not prototype_hits: goto 366
        best_similarity = max(<function 'EnhancedCodingGenerator._conservative_first_level_rank_score.<locals>.<genexpr>'>(iter(prototype_hits)))
        # FIXME: needs manual fix
        row.get('prototype_hits') ; score ; min(2.2, (best_similarity * 3.0))
        score = None
        if row.get('semantic_recall_score', 0.0): goto 382
        recall_score = row.get('semantic_recall_score', 0.0)(0.0)
        if not (recall_score > 0): goto 412
        # FIXME: needs manual fix
        float ; score ; min(1.8, (recall_score * 2.0))
        score = None
        if row.get('knn_score', 0.0): goto 428
        knn_score_val = row.get('knn_score', 0.0)(0.0)
        if not row.get('knn_source'): goto 466
        if not (knn_score_val > 0): goto 466
        # FIXME: needs manual fix
        float ; score ; (3.5 + (knn_score_val * 3.0))
        score = None
        # FIXME: needs manual fix
        score ; (text.count('，') * 1.0)
        score = None
        # FIXME: needs manual fix
        score ; (max(0, (len(text) - 28)) * 0.12)
        score = None
        # FIXME: needs manual fix
        score ; (max(0, (len(text) - 36)) * 0.4)
        score = None
        if not re.search('^(时候|比如|然后|所以|那没有|会，因为|他们有时候|我们有时候|后来|以前因为|当我)', text): goto 558
        # FIXME: needs manual fix
        score ; 2.5
        score = None
        if not re.search('(\\u8fd9\\u4e2a\\u4e8b\\u60c5|\\u8fd9\\u4e00\\u5757\\u76ee\\u524d\\u6211\\u4eec\\u80fd\\u591f|\\u90a3\\u4e2a\\u65f6\\u5019|这块|这一块|那种)', text): goto 580
        # FIXME: needs manual fix
        score ; 1.8
        score = None
        if not re.search('^(追求|引入|建立|调整|获得|降低|提高|推动|解决|客户|越轨|创新|资源|需求|反馈|分析)', text): goto 602
        # FIXME: needs manual fix
        score ; 0.8
        score = None
        if not re.search('^(我们|他们|你们|大家|这个|那个|这种|这些|那些|他是|我是|你是|一开始)', text): goto 624
        # FIXME: needs manual fix
        score ; 1.4
        score = None
        if not row.get('compressed_variant'): goto 658
        if re.search('(我|我们|你|你们|他|他们|这个|那个)', text): goto 658
        # FIXME: needs manual fix
        score ; 1.1
        score = None
        if not re.search('(技术|品牌|资源|平台|机制|流程|生态|需求|问题|合作|协同|创新|服务|应用|模块|设备|系统|客户|团队|工业互联网)', text): goto 694
        if not (len(text) <= 16): goto 694
        # FIXME: needs manual fix
        score ; 0.7
        score = None
        if not self._has_first_level_information_cue(text): goto 714
        # FIXME: needs manual fix
        score ; 1.2
        score = None
        if not re.search('(反馈|诉求|需求|受影响|短板|机会)', text): goto 736
        # FIXME: needs manual fix
        score ; 0.8
        score = None
        if not re.search('(主要负责|指引方向|监督结果)', text): goto 758
        # FIXME: needs manual fix
        score ; 0.7
        score = None
        return score
            # <genexpr>
                # FIXME: for loop)
                c = .0
                if not (c in positive_part): goto 4
                yield 1
                <generator>
                # FIXME: needs manual fix
            # <genexpr>
                # FIXME: for loop)
                hit = .0
                if hit.get('similarity', 0.0): goto 24
                yield hit.get('similarity', 0.0)(0.0)
                <generator>
                # FIXME: needs manual fix

    def _rebuild_decision_policy_from_matcher(self):
        if not CodingDecisionPolicy: goto 10
        if self.rag_matcher: goto 14
        if not self.rag_matcher: goto 30
        # FIXME: needs manual fix
        self.rag_matcher.second_code_name_map()
        second_name_map = {}
        if not self.rag_matcher: goto 50
        # FIXME: needs manual fix
        self.rag_matcher.third_level_name_map()
        third_name_map = {}
        CodingDecisionPolicy(self.rag_second_level_threshold, self.rag_third_level_threshold, list(second_name_map.keys()), list(third_name_map.keys()), second_name_map, third_name_map).decision_policy = self

    def set_first_level_prototypes(self, prototypes):
        if prototypes: goto 12
        prototypes(iter([])).first_level_prototypes = self
        <function 'EnhancedCodingGenerator.set_first_level_prototypes.<locals>.<listcomp>'>
            # <listcomp>
                # FIXME: for loop)
                item = .0
                if not isinstance(item, dict): goto 4
                if not str(item.get('source', '')).strip(): goto 4
                if not str(item.get('manual_first_code', '')).strip(): goto 4
                # FIXME: needs manual fix
                [] ; {}

    def set_first_level_recall_bank(self, labels, model_manager):
        self._ensure_first_level_defaults()
        unique_labels = []
        seen = set()
        if labels: goto 24
        # FIXME: for loop)
        label = iter([])
        if label: goto 38
        text = label.strip()
        if not text: goto 58
        if not (text in seen): goto 60
        # FIXME: needs manual fix
        labels ; str
        seen.add(text)
        unique_labels.append(text)
        # FIXME: needs manual fix
        unique_labels.first_level_recall_bank = self
        None.first_level_recall_embeddings = self
        if not (model_manager is not None): goto 156
        if not unique_labels: goto 160
        # try:
        model_manager.get_embeddings(unique_labels, 'sentence').first_level_recall_embeddings = self
        # FIXME: needs manual fix
        None.first_level_recall_embeddings = self
        # except
        raise

    def _semantic_recall_first_level_labels(self, text, model_manager, top_n, min_score):
        self._ensure_first_level_defaults()
        if getattr(self, 'first_level_recall_bank', []): goto 22
        labels = []
        if labels: goto 32
        return []
        getattr(self, 'first_level_recall_bank', [])
        lexical_hits = <function 'EnhancedCodingGenerator._semantic_recall_first_level_labels.<locals>.lexical_hits'>
        if not (model_manager is None): goto 80
        return lexical_hits()
        # try:
        label_embs = getattr(self, 'first_level_recall_embeddings', None)
        if not (label_embs is None): goto 122
        label_embs = model_manager.get_embeddings(labels, 'sentence')
        label_embs.first_level_recall_embeddings = self
        if (label_embs is None): goto 142
        if not (len(label_embs) == 0): goto 150
        return lexical_hits()
        query_emb = model_manager.get_embeddings([text], 'sentence')[0]
        q_norm = np.linalg.norm(query_emb)
        l_norms = np.linalg.norm(label_embs, 1)
        denom = np.maximum((q_norm * l_norms), 1e-12)
        sims = (np.dot(label_embs, query_emb) / denom)
        order = np.argsort(-sims)[slice(None, max(1, int(top_n)))]
        results = []
        # FIXME: for loop)
        idx = iter(order)
        score = float(sims[idx])
        if not (score < min_score): goto 294
        # FIXME: needs manual fix
        results.append({})
        # FIXME: needs manual fix
        if results: goto 330
        return lexical_hits()
        results
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        lexical_hits()
        # except
        raise

        def lexical_hits():
            if text: goto 18
            text_tokens = jieba.lcut(iter(str(text(''))))
            if text_tokens: goto 36
            return []
            <function 'EnhancedCodingGenerator._semantic_recall_first_level_labels.<locals>.lexical_hits.<locals>.<setcomp>'>
            scored = []
            # FIXME: for loop)
            label = iter(labels)
            if label: goto 66
            label_tokens = jieba.lcut(iter(str(label(''))))
            if label_tokens: goto 82
            # FIXME: needs manual fix
            <function 'EnhancedCodingGenerator._semantic_recall_first_level_labels.<locals>.lexical_hits.<locals>.<setcomp>'>
            # FIXME: needs manual fix
            len ; text_tokens ; label_tokens
            overlap = None(<?>)
            if label: goto 106
            if text: goto 120
            # FIXME: needs manual fix
            len ; set ; str(label('')) ; set ; str(text(''))
            char_overlap = None(<?>)
            if not (overlap <= 0): goto 148
            if not (char_overlap <= 0): goto 148
            # FIXME: needs manual fix
            score = (((overlap / max(1, len(label_tokens))) + (0.15 * overlap)) + (0.08 * char_overlap))
            if label: goto 192
            if not (str(label('')) <= 6): goto 218
            if not (char_overlap > 0): goto 218
            # FIXME: needs manual fix
            len ; score ; 0.35
            score = None
            scored.append({})
            # FIXME: needs manual fix
            scored.sort(<function 'EnhancedCodingGenerator._semantic_recall_first_level_labels.<locals>.lexical_hits.<locals>.<lambda>'>, True)
            exact_or_short = <function 'EnhancedCodingGenerator._semantic_recall_first_level_labels.<locals>.lexical_hits.<locals>.<listcomp>'>(iter(scored))
            long_items = <function 'EnhancedCodingGenerator._semantic_recall_first_level_labels.<locals>.lexical_hits.<locals>.<listcomp>'>(iter(scored))
            merged = (exact_or_short[slice(None, 80)] + long_items)
            return merged[slice(None, max(1, int(top_n)))]
                # <setcomp>
                    # FIXME: for loop)
                    t = .0
                    if not (len(t.strip()) >= 2): goto 4
                    # FIXME: needs manual fix
                    {} ; t
                # <setcomp>
                    # FIXME: for loop)
                    t = .0
                    if not (len(t.strip()) >= 2): goto 4
                    # FIXME: needs manual fix
                    {} ; t
                    return item['score']
                # <listcomp>
                    # FIXME: for loop)
                    item = .0
                    if not (len(str(item.get('text', ''))) <= 8): goto 4
                    # FIXME: needs manual fix
                    [] ; item
                # <listcomp>
                    # FIXME: for loop)
                    item = .0
                    if not (item not in exact_or_short): goto 4
                    # FIXME: needs manual fix
                    [] ; item

    def _prototype_keywords(self, manual_code):
        if manual_code: goto 8
        manual = manual_code('')
        words = <function 'EnhancedCodingGenerator._prototype_keywords.<locals>.<setcomp>'>(iter(jieba.lcut(manual)))
        if ('客户需求' in manual): goto 48
        if not ('需求导向' in manual): goto 62
        # FIXME: needs manual fix
        str ; words.update ; {} ; {'买', '卖', '客户', '要', '需求'}
        <?>(<?>)
        if not ('反馈' in manual): goto 84
        # FIXME: needs manual fix
        words.update ; {} ; {'反馈', '客户', '诉求'}
        <?>(<?>)
        if not ('沟通' in manual): goto 106
        # FIXME: needs manual fix
        words.update ; {} ; {'信任', '推销', '沟通'}
        <?>(<?>)
        return words
            # <setcomp>
                # FIXME: for loop)
                word = .0
                if not (len(word.strip()) >= 2): goto 4
                # FIXME: needs manual fix
                {} ; word

    def _prototype_similarity(self, text, prototype):
        if text: goto 20
        text_tokens = <function 'EnhancedCodingGenerator._prototype_similarity.<locals>.<genexpr>'>(jieba.lcut(iter(str(text('')))))
        source_tokens = set(<function 'EnhancedCodingGenerator._prototype_similarity.<locals>.<genexpr>'>(iter(jieba.lcut(str(prototype.get('source', ''))))))
        manual_tokens = self._prototype_keywords(str(prototype.get('manual_first_code', '')))
        if text_tokens: goto 98
        return 0.0
        # FIXME: needs manual fix
        len ; text_tokens ; source_tokens
        source_overlap = (<?>(<?>) / max(1, min(len(text_tokens), len(source_tokens))))
        # FIXME: needs manual fix
        len ; text_tokens ; manual_tokens
        manual_overlap = (<?>(<?>) / max(1, len(manual_tokens)))
        return ((0.75 * source_overlap) + (0.25 * manual_overlap))
            # <genexpr>
                # FIXME: for loop)
                token = .0
                if not (len(token.strip()) >= 2): goto 4
                yield token
                <generator>
                # FIXME: needs manual fix
            # <genexpr>
                # FIXME: for loop)
                token = .0
                if not (len(token.strip()) >= 2): goto 4
                yield token
                <generator>
                # FIXME: needs manual fix

    def _find_first_level_prototype_hits(self, text, top_k):
        self._ensure_first_level_defaults()
        scored = []
        # FIXME: for loop)
        prototype = iter(self.first_level_prototypes)
        score = self._prototype_similarity(text, prototype)
        if not (score <= 0): goto 44
        # FIXME: needs manual fix
        scored.append({})
        # FIXME: needs manual fix
        scored.sort(<function 'EnhancedCodingGenerator._find_first_level_prototype_hits.<locals>.<lambda>'>, True)
        return scored[slice(None, top_k)]
                return item['similarity']

    def reset_first_level_trace_meta(self):
        self._ensure_first_level_defaults()
        {}._first_level_trace_meta = self

    def get_first_level_trace_meta(self):
        self._ensure_first_level_defaults()
        return dict(self._first_level_trace_meta)

    def _store_first_level_trace(self, code_key, trace):
        self._ensure_first_level_defaults()
        compact_trace = {}
        compact_trace[self._first_level_trace_meta] = code_key
            # <listcomp>
                # FIXME: for loop)
                item = .0
                # FIXME: needs manual fix
                [] ; {}

    def build_first_level_candidate_trace(self, sentence, model_manager, top_n, defer_rerank):
        self._ensure_first_level_defaults()
        if sentence: goto 14
        original = ''.strip()
        if original: goto 46
        return {}
        sentence
        normalized = re.sub('^(?:[A-Za-z]|\\u7b54|\\u53d7\\u8bbf\\u8005|\\u88ab\\u8bbf\\u8005)[:\\uFF1A\\s]*', '', original)
        _speaker_label = '(?:\\u53d7\\u8bbf\\u8005|\\u91c7\\u8bbf\\u8005|\\u8bbf\\u8c08\\u5458|\\u8bf4\\u8bdd\\u4eba\\s*\\d+|\\u91cc\\u5f04\\u7ba1\\u5bb6\\s*\\d*|\\u6e38\\u5ba2\\s*\\d*|\\u975e\\u9057\\u624b\\u827a\\u4eba\\s*\\d*|\\u975e\\u9057\\u4eba\\s*\\d*|\\u7ba1\\u7406\\u5c42\\s*\\d*|\\u666f\\u6f02\\s*\\d*|\\u8001\\u5e08\\s*\\d*|\\u4e3b\\u6301\\u4eba|\\u8bb0\\u8005|\\u88ab\\u8bbf\\u8005|\\u5609\\u5bbe|\\u4e13\\u5bb6|\\u5c45\\u6c11\\s*\\d*|\\u5546\\u6237\\s*\\d*|\\u624b\\u827a\\u4eba\\s*\\d*|\\u5b66\\u5f92\\s*\\d*|\\u4f20\\u627f\\u4eba\\s*\\d*|\\u95ee|\\u7b54|Q|A)'
        normalized = re.sub('^' + str(_speaker_label) + '\\s*[\\uFF1A:]?\\s*', '', normalized)
        normalized = re.sub('\\[[A-Z]?\\d+\\]', '', normalized)
        normalized = re.sub('(\\w)\\1{2,}', '\\1', normalized)
        normalized = self._normalize_source_sentence(normalized)
        if normalized: goto 150
        return {}
        prototype_hits = self._find_first_level_prototype_hits(normalized)
        prototype_keywords = set()
        # FIXME: for loop)
        hit = iter(prototype_hits)
        prototype_keywords.update(self._prototype_keywords(hit.get('manual_first_code', '')))
        # FIXME: needs manual fix
        salience = self._compute_salience(normalized)
        rag_context_terms = []
        if not hasattr(self, 'rag_doc_retriever'): goto 332
        if not (self.rag_doc_retriever is not None): goto 332
        # try:
        rag_chunks = self.rag_doc_retriever.retrieve(normalized, 3, 0.5)
        # FIXME: for loop)
        chunk = iter(rag_chunks)
        chunk_terms = self._extract_domain_terms_from_text(chunk.get('text', ''))
        rag_context_terms.extend(chunk_terms)
        # FIXME: needs manual fix
        if not rag_context_terms: goto 310
        rag_context_terms = list(dict.fromkeys(rag_context_terms))
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        # except
        # FIXME: needs manual fix
        raise
        if not self._should_skip_sentence_for_coding(normalized, salience): goto 372
        return {}
        if not Config: goto 388
        # FIXME: needs manual fix
        getattr(Config, 'MAX_SENTENCE_LENGTH', 512)
        target_length = 512
        if not Config: goto 414
        # FIXME: needs manual fix
        getattr ; self ; 'max_first_level_length' ; getattr(Config, 'FIRST_LEVEL_CODE_MAX_LENGTH', 30)
        max_len = None(<?>, <?>, 30)
        if not isinstance(max_len, int): goto 442
        if not (max_len > 0): goto 442
        # FIXME: needs manual fix
        max_len
        length_budget = None
        if not Config: goto 466
        # FIXME: needs manual fix
        bool(getattr(Config, 'FIRST_LEVEL_RECALL_ENHANCED', False))
        recall_enhanced = False
        if not Config: goto 490
        # FIXME: needs manual fix
        int(getattr(Config, 'FIRST_LEVEL_BASE_MAX_SPAN', 8))
        base_max_span = 8
        if not Config: goto 516
        # FIXME: needs manual fix
        int(getattr(Config, 'FIRST_LEVEL_ENHANCED_MAX_SPAN', 12))
        enhanced_max_span = 12
        focus_markers = ('第一次', '首次', '然而', '最终', '但是', '不过', '却', '更', '更加', '最', '最高', '最低', '核心', '关键', '尤其', '特别', '主要', '重点')
        professional_terms = ('技术', '资源', '平台', '机制', '流程', '生态', '需求', '风险', '压力', '冲突', '协同', '合作', '创新', '服务', '模块', '设备', '系统', '客户', '团队', '品牌', '治理', '监督', '审批', '架构', '算法', '数据', '能力', '知识', '资本', '绩效', '战略', '路径', '场景', '农业', '农村', '种植', '养殖', '灌溉', '施肥', '收割', '农机', '农产品', '粮食', '果蔬', '畜牧', '渔业', '农户', '合作社', '产量', '品种', '有机', '绿色食品', '非遗', '手艺', '技艺', '传承人', '工匠', '作坊', '文创', '手工艺', '陶艺', '织造', '雕刻', '刺绣', '民俗', '古建筑', '修缮', '文保', '文物', '医疗', '诊疗', '康复', '护理', '患者', '医保', '药品', '临床', '公共卫生', '基层医疗', '健康管理', '中医', '慢病', '教育', '教学', '课程', '师资', '学员', '教材', '考核', '素质教育', '职业教育', '技能培训', '校企合作', '在线教育', '社区', '公益', '民生', '基层', '社会组织', '志愿服务', '公共空间', '社区营造', '城市更新', '旧改', '可持续', '赋能', '电商', '直播', '流量', '运营', '供应链', '渠道', '营销', '转化', '复购', '文旅', '景区', '游客', '民宿', '网红', '文旅融合', '打卡')
        strip_punct = <function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.strip_punct'>
        looks_like_fragment = <function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.looks_like_fragment'>
        score_candidate = <function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.score_candidate'>
        concessive_spans = self._detect_concessive_spans(normalized)
        negated_spans = self._detect_negated_spans(normalized)
        sentence_parts = <function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<listcomp>'>(iter(re.split('[\\u3002\\uFF01\\uFF1F\\uFF1B;]', normalized)))
        if sentence_parts: goto 674
        sentence_parts = [normalized]
        candidate_rows = []
        seen = {}
        # FIXME: for loop)
        sentence_part = iter(sentence_parts)
        micro_parts = <function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<listcomp>'>(iter(re.split('[\\uFF0C,\\u3001]', sentence_part)))
        if micro_parts: goto 726
        micro_parts = [sentence_part]
        # FIXME: for loop)
        i = iter(range(len(micro_parts)))
        built_raw = ''
        if not recall_enhanced: goto 756
        # FIXME: needs manual fix
        span_limit = base_max_span
        # FIXME: for loop)
        j = iter(range(i, min(len(micro_parts), (i + span_limit))))
        if built_raw: goto 802
        # FIXME: needs manual fix
        micro_parts[j]
        built_raw = str(built_raw) + '，' + str(micro_parts[j])
        candidate = strip_punct(self._post_refine_phrase(built_raw))
        if not candidate: goto 846
        # FIXME: needs manual fix
        [candidate]
        variants = []
        normalized_candidate = self._normalize_candidate_for_first_level(candidate)
        if not normalized_candidate: goto 886
        if not (normalized_candidate not in variants): goto 886
        variants.append(normalized_candidate)
        if not normalized_candidate: goto 904
        # FIXME: needs manual fix
        normalized_candidate.replace('就很受影响', '受影响')
        compact_candidate = ''
        if not compact_candidate: goto 926
        # FIXME: needs manual fix
        compact_candidate.replace('很受影响', '受影响')
        compact_candidate = ''
        if not compact_candidate: goto 948
        # FIXME: needs manual fix
        compact_candidate.replace('影响项目推进', '项目推进受影响')
        compact_candidate = ''
        if not compact_candidate: goto 978
        if not (compact_candidate not in variants): goto 978
        variants.append(compact_candidate)
        compressed_variants = set(self._compress_first_level_candidate_variants(built_raw))
        # FIXME: for loop)
        compressed_candidate = iter(compressed_variants)
        if not (compressed_candidate not in variants): goto 1020
        variants.append(compressed_candidate)
        # FIXME: needs manual fix
        if not normalized_candidate: goto 1070
        if not ('项目推进' in normalized_candidate): goto 1070
        if not ('受影响' in normalized_candidate): goto 1070
        if not ('项目推进受影响' not in variants): goto 1070
        variants.append('项目推进受影响')
        # FIXME: for loop)
        variant = iter(variants)
        if not variant: goto 1098
        if not (len(variant) > target_length): goto 1102
        # FIXME: needs manual fix
        row = {}
        existing = seen.get(variant)
        if not (existing is None): goto 1190
        len(candidate_rows)[seen] = variant
        candidate_rows.append(row)
        # FIXME: needs manual fix
        if not (row['rule_score'] > candidate_rows[existing]['rule_score']): goto 1220
        row[candidate_rows] = existing
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        if not recall_enhanced: goto 1500
        trigger_keywords = ('影响', '导致', '卡在', '拖慢', '延迟', '只能', '需要', '受限', '不足', '短板', '风险', '压力', '冲突', '审批', '协同', '资源', '客户', '诉求', '反馈', '推进')
        extra_parts = <function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<listcomp>'>(iter(re.split('[，,、；;。！？!?]', normalized)))
        # FIXME: for loop)
        part = iter(extra_parts)
        clean_part = self._normalize_candidate_for_first_level(strip_punct(self._post_refine_phrase(part)))
        if clean_part: goto 1306
        # FIXME: needs manual fix
        if (len(clean_part) < 4): goto 1334
        if not (len(clean_part) > target_length): goto 1338
        # FIXME: needs manual fix
        if (clean_part)(<function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<genexpr>'>(iter(trigger_keywords))): goto 1366
        # FIXME: needs manual fix
        any
        if not self._contains_colloquial_residue(clean_part): goto 1382
        # FIXME: needs manual fix
        row = {}
        existing = seen.get(clean_part)
        if not (existing is None): goto 1466
        len(candidate_rows)[seen] = clean_part
        candidate_rows.append(row)
        # FIXME: needs manual fix
        if not (row['rule_score'] > candidate_rows[existing]['rule_score']): goto 1496
        row[candidate_rows] = existing
        # FIXME: needs manual fix
        if not recall_enhanced: goto 1804
        if not Config: goto 1804
        if not getattr(Config, 'FIRST_LEVEL_USE_LABEL_RECALL_CANDIDATES', False): goto 1804
        if not Config: goto 1548
        # FIXME: needs manual fix
        int(getattr(Config, 'FIRST_LEVEL_SEMANTIC_RECALL_TOP_N', 8))
        semantic_top_n = 8
        if not Config: goto 1574
        # FIXME: needs manual fix
        float(getattr(Config, 'FIRST_LEVEL_SEMANTIC_RECALL_MIN_SCORE', 0.35))
        semantic_min_score = 0.35
        # FIXME: for loop)
        hit = iter(self._semantic_recall_first_level_labels(normalized, model_manager, semantic_top_n, semantic_min_score))
        label = self._normalize_candidate_for_first_level(hit.get('text', ''))
        if not label: goto 1638
        if not (len(label) > target_length): goto 1642
        # FIXME: needs manual fix
        if not self._contains_colloquial_residue(label): goto 1658
        # FIXME: needs manual fix
        row = {}
        existing = seen.get(label)
        if not (existing is None): goto 1770
        len(candidate_rows)[seen] = label
        candidate_rows.append(row)
        # FIXME: needs manual fix
        if not (row['rule_score'] > candidate_rows[existing]['rule_score']): goto 1800
        row[candidate_rows] = existing
        # FIXME: needs manual fix
        if not hasattr(self, 'knn_abstract_generator'): goto 2088
        if not (self.knn_abstract_generator is not None): goto 2088
        # try:
        knn_candidates = self.knn_abstract_generator.retrieve(normalized, 5, 0.55)
        # FIXME: for loop)
        knn = iter(knn_candidates)
        label = self._normalize_candidate_for_first_level(knn.get('text', ''))
        if not label: goto 1894
        if not (len(label) > target_length): goto 1898
        # FIXME: needs manual fix
        if not self._contains_colloquial_residue(label): goto 1914
        # FIXME: needs manual fix
        knn_score = float(knn.get('score', 0.0))
        row = {}
        existing = seen.get(label)
        if not (existing is None): goto 2030
        len(candidate_rows)[seen] = label
        candidate_rows.append(row)
        # FIXME: needs manual fix
        if not (row['rule_score'] > candidate_rows[existing]['rule_score']): goto 2060
        row[candidate_rows] = existing
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        # except
        # FIXME: needs manual fix
        raise
        if not self._ensure_anchor_index(): goto 2372
        if not (self.concept_anchor_index is not None): goto 2372
        # try:
        anchor_results = self.concept_anchor_index.search(normalized, 8)
        # FIXME: for loop)
        concept_name = <unpack_3>
        anchor_score = iter(anchor_results)
        anchor_source = None
        if not (anchor_score < 0.3): goto 2156
        # FIXME: needs manual fix
        label = self._normalize_candidate_for_first_level(concept_name)
        if not label: goto 2186
        if not (len(label) < 2): goto 2190
        # FIXME: needs manual fix
        anchor_rule = round((6.5 + (anchor_score * 4.5)), 4)
        anchor_cons = round(((min(anchor_rule, 12.0) * 0.5) + (anchor_score * 2.0)), 4)
        row = {}
        existing = seen.get(label)
        if not (existing is None): goto 2314
        len(candidate_rows)[seen] = label
        candidate_rows.append(row)
        # FIXME: needs manual fix
        if not (row['rule_score'] > candidate_rows[existing]['rule_score']): goto 2344
        row[candidate_rows] = existing
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        # except
        # FIXME: needs manual fix
        raise
        _best_non_t5_score = 0.0
        # FIXME: for loop)
        _r = iter(candidate_rows)
        if not (_r.get('knn_source') != 't5_generated'): goto 2418
        _best_non_t5_score = max(_best_non_t5_score, _r.get('rule_score', 0.0))
        # FIXME: needs manual fix
        if not hasattr(self, 't5_generative_coder'): goto 2762
        if not (self.t5_generative_coder is not None): goto 2762
        # try:
        t5_candidates = self.t5_generative_coder.generate(normalized, 5, 5)
        # FIXME: for loop)
        tc = iter(t5_candidates)
        label = self._normalize_candidate_for_first_level(tc.get('text', ''))
        if not label: goto 2512
        if not (len(label) > target_length): goto 2516
        # FIXME: needs manual fix
        if not self._contains_colloquial_residue(label): goto 2532
        # FIXME: needs manual fix
        t5_score = float(tc.get('score', 0.0))
        if not (_best_non_t5_score < 7.0): goto 2588
        t5_rule = round(max((4.5 + (t5_score * 0.5)), (_best_non_t5_score - 0.3)), 4)
        # FIXME: needs manual fix
        t5_rule = round((4.0 + (t5_score * 0.5)), 4)
        t5_cons = round((min(t5_rule, 12.0) * 0.5), 4)
        row = {}
        existing = seen.get(label)
        if not (existing is None): goto 2704
        len(candidate_rows)[seen] = label
        candidate_rows.append(row)
        # FIXME: needs manual fix
        if not (row['rule_score'] > candidate_rows[existing]['rule_score']): goto 2734
        row[candidate_rows] = existing
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        # except
        # FIXME: needs manual fix
        raise
        candidate_rows = self._canonicalize_first_level_candidate_rows(candidate_rows, normalized)
        if candidate_rows: goto 2822
        if not re.search('(生产习惯|默认的惯例|当地默认).*随意', normalized): goto 2822
        candidate_rows.append({})
        best_rule_candidate = ''
        best_rule_key = (float('-inf'), float('-inf'), float('-inf'), float('-inf'))
        # FIXME: for loop)
        row = iter(candidate_rows)
        if row.get('text', ''): goto 2880
        text = row.get('text', '')
        if not re.search('(受影响|受限|受阻|不足|短板|风险|压力|冲突)', text): goto 2920
        # FIXME: needs manual fix
        str ; float(row.get('conservative_score', float('-inf'))) ; 1.0
        row_key = (<?>, 0.0, float(row.get('rule_score', float('-inf'))), -len(text))
        if not (row_key > best_rule_key): goto 2978
        best_rule_key = row_key
        best_rule_candidate = row.get('text', '')
        # FIXME: needs manual fix
        if not best_rule_candidate: goto 2994
        fallback_candidate = best_rule_candidate
        # FIXME: needs manual fix
        if not candidate_rows: goto 3018
        fallback_candidate = candidate_rows[0].get('text', '')
        # FIXME: needs manual fix
        trimmed = self._normalize_candidate_for_first_level(strip_punct(normalized))
        if not (len(trimmed) <= 30): goto 3064
        if not self._has_first_level_information_cue(trimmed): goto 3064
        fallback_candidate = trimmed
        # FIXME: needs manual fix
        fallback_candidate = ''
        selected_candidate = fallback_candidate
        _selected_is_knn = False
        used_rerank = False
        if not (best_rule_key[2] > float('-inf')): goto 3106
        # FIXME: needs manual fix
        best_rule_key[2]
        best_rule_score = float('-inf')
        if not selected_candidate: goto 3146
        if not (best_rule_score < 1.5): goto 3146
        if concessive_spans: goto 3142
        if not negated_spans: goto 3146
        selected_candidate = ''
        # try:
        if defer_rerank: goto 3742
        if not Config: goto 3742
        if not getattr(Config, 'ENABLE_ABSTRACT_RERANKER', False): goto 3742
        if not (model_manager is not None): goto 3742
        if not hasattr(model_manager, 'ensure_abstract_reranker_loaded'): goto 3206
        model_manager.ensure_abstract_reranker_loaded()
        if not hasattr(model_manager, 'is_abstract_reranker_available'): goto 3742
        if not model_manager.is_abstract_reranker_available(): goto 3742
        if not Config: goto 3256
        # FIXME: needs manual fix
        max(1, int(getattr(Config, 'ABSTRACT_RERANK_TOP_N', 6)))
        rerank_limit = 6
        prefiltered_rows = []
        # FIXME: for loop)
        row = iter(candidate_rows)
        if row.get('text', ''): goto 3290
        t = row.get('text', '')
        if t: goto 3304
        # FIXME: needs manual fix
        is_anchor = bool(row.get('anchor_source'))
        if is_anchor: goto 3348
        if not looks_like_fragment(row.get('raw_text', ''), t): goto 3348
        # FIXME: needs manual fix
        if not self._contains_colloquial_residue(t): goto 3364
        # FIXME: needs manual fix
        if is_anchor: goto 3402
        if not self._is_low_quality_first_level_code(t, normalized, bool(row.get('knn_source'))): goto 3402
        # FIXME: needs manual fix
        prefiltered_rows.append(row)
        # FIXME: needs manual fix
        if not (len(prefiltered_rows) >= 3): goto 3434
        # FIXME: needs manual fix
        prefiltered_rows
        rerank_rows = <function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<listcomp>'>(iter(candidate_rows))
        if rerank_rows: goto 3466
        rerank_rows = list(candidate_rows)
        source_semantic_cues = '(优点|好处|优势|缺点|缺陷|问题|关键|核心|重要|主要|根本|本质|特色|亮点|突破|创新)'
        source_has_cues = bool(re.search(source_semantic_cues, normalized))
        (source_has_cues, source_semantic_cues)(<function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<lambda>'>, True)
        (looks_like_fragment) ; rerank_rows.sort
        rerank_candidates = <function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<listcomp>'>(iter(rerank_rows[slice(None, rerank_limit)]))
        if not rerank_candidates: goto 3742
        scores = model_manager.score_abstract_candidates(normalized, rerank_candidates)
        if not scores: goto 3742
        if not (len(scores) == len(rerank_candidates)): goto 3742
        used_rerank = True
        score_map = <function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<dictcomp>'>(iter(zip(rerank_candidates, scores)))
        # FIXME: for loop)
        row = iter(candidate_rows)
        score_map.get(row['text'])[row] = 'rerank_score'
        normalized[row] = 'source_text'
        round(float(self._conservative_first_level_rank_score(row)), 4)[row] = 'conservative_score'
        # FIXME: needs manual fix
        best_reranked = max(<function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<listcomp>'>(iter(candidate_rows)), <function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<lambda>'>, None)
        if not (best_reranked is not None): goto 3738
        selected_candidate = best_reranked.get('text', selected_candidate)
        if best_reranked.get('knn_source'): goto 3732
        _selected_is_knn = best_reranked.get('knn_source')(best_reranked.get('anchor_source'))
        # FIXME: needs manual fix
        _selected_is_knn = False
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        # except
        # FIXME: needs manual fix
        raise
        if not selected_candidate: goto 3806
        if self._is_semantically_complete(selected_candidate): goto 3806
        candidate = self._limit_first_level_text(selected_candidate, 60)
        if not candidate: goto 3806
        selected_candidate = candidate
        if not (length_budget is not None): goto 3858
        if not selected_candidate: goto 3858
        if not (len(selected_candidate) > length_budget): goto 3858
        candidate = self._limit_first_level_text(selected_candidate, length_budget)
        if not candidate: goto 3858
        selected_candidate = candidate
        if not selected_candidate: goto 3938
        if not self._contains_colloquial_residue(selected_candidate): goto 3938
        clean_rows = <function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<listcomp>'>(iter(candidate_rows))
        if not clean_rows: goto 3938
        clean_rows.sort(<function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<lambda>'>, True)
        selected_candidate = clean_rows[0].get('text', selected_candidate)
        _selected_is_anchor = (selected_candidate)(<function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<genexpr>'>(iter(candidate_rows)))
        if _selected_is_knn: goto 3980
        selected_candidate = strip_punct(selected_candidate)(normalized, _selected_is_knn, _selected_is_anchor)
        # FIXME: for loop)
        row = iter(candidate_rows)
        (row['text'] == selected_candidate)[row] = 'selected'
        (row['text'] == best_rule_candidate)[row] = 'best_rule'
        # FIXME: needs manual fix
        any ; self._finalize_first_level_candidate
        candidate_rows.sort(<function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<lambda>'>, True)
        if not isinstance(top_n, int): goto 4082
        if not (top_n > 0): goto 4082
        candidate_rows = candidate_rows[slice(None, top_n)]
        _selected_row = (selected_candidate)(<function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.<genexpr>'>(iter(candidate_rows)), None)
        if not _selected_row: goto 4126
        # FIXME: needs manual fix
        next ; bool(_selected_row.get('anchor_source'))
        _anchor_selected = False
        if not _selected_row: goto 4148
        # FIXME: needs manual fix
        _selected_row.get('anchor_source', '')
        _anchor_source = ''
        return {}

        def strip_punct(value):
            if value: goto 14
            return '^[\\s\\W_]+|[\\s\\W_]+$'('', value, '')
            re.sub

        def looks_like_fragment(raw_text, clean_text):
            if clean_text: goto 6
            clean = ''.strip()
            if clean: goto 20
            return True
            clean_text
            if not (len(clean) <= 3): goto 58
            if (clean)(<function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.looks_like_fragment.<locals>.<genexpr>'>(iter(professional_terms))): goto 58
            return True
            any
            if not (len(clean) <= 8): goto 96
            if not (clean)(<function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.looks_like_fragment.<locals>.<genexpr>'>(iter(professional_terms))): goto 96
            return False
            any
            if not self._is_question_like(clean): goto 110
            return True
            if not clean.startswith(('因为', '如果', '但是', '不过', '所以', '然后', '并且')): goto 124
            return True
            if not clean.endswith(('这个', '那个', '这里', '这样', '那样')): goto 138
            return True
            return False
                # <genexpr>
                    # FIXME: for loop)
                    term = .0
                    yield (term in clean)
                    <generator>
                    # FIXME: needs manual fix
                # <genexpr>
                    # FIXME: for loop)
                    term = .0
                    yield (term in clean)
                    <generator>
                    # FIXME: needs manual fix

        def score_candidate(clean_text, raw_text):
            if clean_text: goto 6
            clean = ''
            score = 0.0
            if not self._is_semantically_complete(clean): goto 32
            # FIXME: needs manual fix
            clean_text ; score ; 5.0
            score = None
            # FIXME: needs manual fix
            # FIXME: needs manual fix
            score ; 3.0
            score = None
            if not looks_like_fragment(raw_text, clean): goto 58
            # FIXME: needs manual fix
            score ; 5.0
            score = None
            if not re.search('(的|了|着|过|到|在|中|和|与|或|又|还|也|只|不|没)$', clean): goto 78
            # FIXME: needs manual fix
            score ; 3.0
            score = None
            if not re.search('(什么|怎么|哪些|怎么样|如何|哪方面|什么时候)', clean): goto 98
            # FIXME: needs manual fix
            score ; 4.0
            score = None
            if not re.search('^(但|而|且|并|还|也|另外|此外|还有)', clean): goto 118
            # FIXME: needs manual fix
            score ; 2.0
            score = None
            if not (raw_text)(<function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.score_candidate.<locals>.<genexpr>'>(iter(focus_markers))): goto 248
            marker_positions = <function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.score_candidate.<locals>.<listcomp>'>(iter(focus_markers))
            if not marker_positions: goto 170
            # FIXME: needs manual fix
            any ; (raw_text) ; min(marker_positions)
            first_marker_pos = -1
            clean_pos = raw_text.find(clean)
            if not (clean_pos >= 0): goto 218
            if (first_marker_pos < 0): goto 208
            if not (clean_pos >= first_marker_pos): goto 218
            # FIXME: needs manual fix
            score ; 2.2
            score = None
            # FIXME: needs manual fix
            if not (clean)(<function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.score_candidate.<locals>.<genexpr>'>(iter(focus_markers))): goto 248
            # FIXME: needs manual fix
            any ; score ; 1.2
            score = None
            if not (len(clean) <= 12): goto 290
            if not (clean)(<function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.score_candidate.<locals>.<genexpr>'>(iter(professional_terms))): goto 290
            # FIXME: needs manual fix
            any ; score ; 1.8
            score = None
            if not (clean)(<function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.score_candidate.<locals>.<genexpr>'>(iter(('影响', '导致', '只能', '需要', '卡在', '拖慢', '延迟', '协同', '审批', '资源', '客户', '推进')))): goto 320
            # FIXME: needs manual fix
            any ; score ; 2.5
            score = None
            if not (clean)(<function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.score_candidate.<locals>.<genexpr>'>(iter(('经常', '反复', '总是', '每次', '频繁')))): goto 350
            # FIXME: needs manual fix
            any ; score ; 1.0
            score = None
            if not rag_context_terms: goto 402
            rag_match_count = (clean)(<function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.score_candidate.<locals>.<genexpr>'>(iter(rag_context_terms)))
            if not (rag_match_count > 0): goto 402
            # FIXME: needs manual fix
            sum ; score ; min(3.0, (rag_match_count * 1.2))
            score = None
            if not prototype_keywords: goto 596
            overlap = (clean)(<function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.score_candidate.<locals>.<genexpr>'>(iter(prototype_keywords)))
            density = (overlap / max(1, len(clean)))
            # FIXME: needs manual fix
            sum ; score ; min(4.5, ((overlap * 1.4) + (density * 10.0)))
            score = None
            # FIXME: needs manual fix
            score ; (clean.count('，') * 1.8)
            score = None
            # FIXME: needs manual fix
            score ; (max(0, (len(clean) - 18)) * 0.12)
            score = None
            if not ('需求' in prototype_keywords): goto 596
            if not ('客户' in clean): goto 596
            if not ('买' in clean): goto 568
            if not ('卖' in clean): goto 568
            # FIXME: needs manual fix
            score ; 4.0
            score = None
            # FIXME: needs manual fix
            if ('要' in clean): goto 588
            if not ('需求' in clean): goto 596
            # FIXME: needs manual fix
            score ; 1.0
            score = None
            if not (clean)(<function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.score_candidate.<locals>.<genexpr>'>(iter(('可能', '大概', '也许', '好像', '不太清楚')))): goto 628
            # FIXME: needs manual fix
            any ; score ; 2.0
            score = None
            if not (length_budget is not None): goto 678
            if not (len(clean) > length_budget): goto 678
            # FIXME: needs manual fix
            score ; (max(0, (len(clean) - length_budget)) * 0.15)
            score = None
            if not (6 <= len(clean)): goto 706
            if not (len(clean) <= 20): goto 738
            # FIXME: needs manual fix
            # FIXME: needs manual fix
            # FIXME: needs manual fix
            score ; ((min(len(clean), 20) / 20.0) + 0.5)
            score = None
            # FIXME: needs manual fix
            if not (len(clean) < 6): goto 854
            has_meaning = (clean)(<function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.score_candidate.<locals>.<genexpr>'>(iter(professional_terms)))
            if has_meaning: goto 796
            has_meaning = bool(re.search('(成本|市场|价格|利润|收入|投资|资金|贷款|工艺|手工|技术|质量|标准|检验|认证|生产|种植|养殖|加工|收购|销售|培训|机制|流程|资源|策略|能力|需求|服务|创新|协同|治理|监督|品牌|团队|客户|管理|供应链|贸易|消费|购买|非遗|手艺|技艺|文创|陶艺|织造|雕刻|民俗|古建筑|修缮|文物|诊疗|康复|护理|患者|医保|药品|临床|健康管理|中医|慢病|教学|课程|师资|学员|教材|素质教育|职业教育|技能培训|社区|公益|民生|基层|志愿服务|社区营造|城市更新|旧改|电商|直播|流量|运营|渠道|营销|文旅|景区|民宿|可持续|赋能|有机|绿色|合作社|农户|粮食|果蔬|畜牧|渔业)', clean))
            if has_meaning: goto 818
            if not self._has_first_level_information_cue(clean): goto 818
            has_meaning = True
            if has_meaning: goto 832
            # FIXME: needs manual fix
            any ; score ; 3.0
            score = None
            # FIXME: needs manual fix
            score ; ((len(clean) / 6.0) * 0.3)
            score = None
            # FIXME: needs manual fix
            # FIXME: needs manual fix
            score ; (min(len(clean), 40) / 40.0)
            score = None
            verb_indicators = '(缺乏|缺少|不足|受限|导致|影响|推动|降低|提高|优化|开展|进行|建立|引入|获得|调整|转变|对接|合作|协调|整合|增加|减少|传承|保护|弘扬|培育|扶持|带动|促进|改善|保障|修复|修缮|诊疗|康复|护理|教学|培训|赋能|转型|运营|营销)'
            noun_indicators = '(机制|流程|资源|策略|能力|需求|服务|创新|协同|治理|监督|审批|绩效|战略|路径|场景|平台|系统|客户|团队|品牌|非遗|技艺|工艺|文创|文物|古建筑|医保|患者|课程|师资|社区|民生|公益|电商|文旅|景区|民宿|供应链|可持续)'
            if not re.search(verb_indicators, clean): goto 920
            if not re.search(noun_indicators, clean): goto 920
            # FIXME: needs manual fix
            score ; 2.0
            score = None
            domain_terms = '(种植|养殖|加工|收购|销售|市场|价格|成本|利润|收入|投资|资金|贷款|保险|补贴|税收|消费|购买|供应链|贸易|工艺|手工|技术|传承|培训|制作|原料|工具|设备|标准|质量|检验|认证|生产|非遗|手艺|技艺|文创|陶艺|织造|雕刻|刺绣|民俗|古建筑|修缮|文物|文保|诊疗|康复|护理|患者|医保|药品|临床|公共卫生|健康管理|教学|课程|师资|学员|教材|考核|素质教育|职业教育|技能培训|社区|公益|民生|基层|志愿服务|社区营造|城市更新|旧改|电商|直播|流量|运营|渠道|营销|文旅|景区|民宿|可持续|赋能|转型|有机|绿色|合作社|农户|粮食|果蔬|畜牧|渔业|中医|慢病)'
            domain_count = len(re.findall(domain_terms, clean))
            # FIXME: needs manual fix
            score ; min((domain_count * 1.0), 3.0)
            score = None
            # FIXME: needs manual fix
            score ; (salience['total'] * 2.0)
            score = None
            formal_density = len(re.findall('(机制|流程|资源|策略|路径|模式|结构|能力|架构|生态|治理|监督|协同|审批|绩效|战略|需求|服务|创新|评估|优化|配置|整合|调度|保障|约束|反馈|驱动|赋能|转型|传承|保护|非遗|技艺|工艺|文创|文物|修缮|修复|文保|诊疗|康复|护理|医保|健康管理|公共卫生|基层医疗|教学|课程|师资|教材|职业教育|技能培训|素质教育|社区|公益|民生|基层|志愿服务|社区营造|城市更新|旧改|电商|直播|运营|营销|供应链|文旅|景区|民宿|可持续|低碳|绿色)', clean))
            # FIXME: needs manual fix
            score ; min((formal_density * 1.5), 4.5)
            score = None
            if not re.search('(这个|那个|那种|这种|什么的|之类的|怎么说呢|就是说|我觉得|相当于)', clean): goto 1030
            # FIXME: needs manual fix
            score ; 2.5
            score = None
            if not re.search('^(我|我们|你|你们|他|他们|大家|那个|这个)', clean): goto 1052
            # FIXME: needs manual fix
            score ; 1.4
            score = None
            if not re.search('^[一-\u9fff]{2,}(?:机制|流程|资源|策略|能力|需求|服务|创新|协同|治理|监督|审批)', clean): goto 1088
            if not re.search('(不足|受限|缺失|缺乏|受阻|延迟|影响|推动|优化|提升|降低|增加)', clean): goto 1088
            # FIXME: needs manual fix
            score ; 2.0
            score = None
            if not re.search('(不|没有|无需|从未|并未|毫不)', normalized): goto 1218
            if re.search('(不|没有|无需|从未|并未|毫不)', clean): goto 1218
            # FIXME: for loop)
            m = iter(re.finditer('(不|没有|无需|从未|并未|毫不)(.{1,10})', normalized))
            positive_part = m.group(2)
            if not (len(positive_part) >= 2): goto 1214
            common = (positive_part)(<function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.score_candidate.<locals>.<genexpr>'>(iter(clean)))
            if not (common >= min((len(clean) * 0.5), 3)): goto 1214
            # FIXME: needs manual fix
            sum ; score ; 5.0
            score = None
            # FIXME: needs manual fix
            # FIXME: needs manual fix
            if not concessive_spans: goto 1310
            # FIXME: for loop)
            cs_start = <unpack_2>
            cs_end = iter(concessive_spans)
            concessive_text = normalized[slice(cs_start, cs_end)]
            common = (concessive_text)(<function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.score_candidate.<locals>.<genexpr>'>(iter(clean)))
            if not (common >= min((len(clean) * 0.5), 2)): goto 1306
            # FIXME: needs manual fix
            sum ; score ; 6.0
            score = None
            # FIXME: needs manual fix
            # FIXME: needs manual fix
            if not negated_spans: goto 1402
            # FIXME: for loop)
            ns_start = <unpack_2>
            ns_end = iter(negated_spans)
            negated_text = normalized[slice(ns_start, ns_end)]
            common = (negated_text)(<function 'EnhancedCodingGenerator.build_first_level_candidate_trace.<locals>.score_candidate.<locals>.<genexpr>'>(iter(clean)))
            if not (common >= min((len(clean) * 0.4), 2)): goto 1398
            # FIXME: needs manual fix
            sum ; score ; 6.0
            score = None
            # FIXME: needs manual fix
            # FIXME: needs manual fix
            semantic_cues = '(优点|好处|优势|缺点|缺陷|问题|关键|核心|重要|主要|根本|本质|特色|亮点|突破|创新)'
            if not re.search(semantic_cues, normalized): goto 1442
            if not re.search(semantic_cues, clean): goto 1442
            # FIXME: needs manual fix
            score ; 3.0
            score = None
            return score
                # <genexpr>
                    # FIXME: for loop)
                    marker = .0
                    yield (marker in raw_text)
                    <generator>
                    # FIXME: needs manual fix
                # <listcomp>
                    # FIXME: for loop)
                    marker = .0
                    if not (marker in raw_text): goto 4
                    # FIXME: needs manual fix
                    [] ; raw_text.find(marker)
                # <genexpr>
                    # FIXME: for loop)
                    marker = .0
                    yield (marker in clean)
                    <generator>
                    # FIXME: needs manual fix
                # <genexpr>
                    # FIXME: for loop)
                    term = .0
                    yield (term in clean)
                    <generator>
                    # FIXME: needs manual fix
                # <genexpr>
                    # FIXME: for loop)
                    keyword = .0
                    yield (keyword in clean)
                    <generator>
                    # FIXME: needs manual fix
                # <genexpr>
                    # FIXME: for loop)
                    keyword = .0
                    yield (keyword in clean)
                    <generator>
                    # FIXME: needs manual fix
                # <genexpr>
                    # FIXME: for loop)
                    term = .0
                    if not term: goto 4
                    if not (term in clean): goto 4
                    yield 1
                    <generator>
                    # FIXME: needs manual fix
                # <genexpr>
                    # FIXME: for loop)
                    keyword = .0
                    if not keyword: goto 4
                    if not (keyword in clean): goto 4
                    yield 1
                    <generator>
                    # FIXME: needs manual fix
                # <genexpr>
                    # FIXME: for loop)
                    keyword = .0
                    yield (keyword in clean)
                    <generator>
                    # FIXME: needs manual fix
                # <genexpr>
                    # FIXME: for loop)
                    term = .0
                    yield (term in clean)
                    <generator>
                    # FIXME: needs manual fix
                # <genexpr>
                    # FIXME: for loop)
                    c = .0
                    if not (c in positive_part): goto 4
                    yield 1
                    <generator>
                    # FIXME: needs manual fix
                # <genexpr>
                    # FIXME: for loop)
                    c = .0
                    if not (c in concessive_text): goto 4
                    yield 1
                    <generator>
                    # FIXME: needs manual fix
                # <genexpr>
                    # FIXME: for loop)
                    c = .0
                    if not (c in negated_text): goto 4
                    yield 1
                    <generator>
                    # FIXME: needs manual fix
            # <listcomp>
                # FIXME: for loop)
                part = .0
                if not part.strip(): goto 4
                # FIXME: needs manual fix
                [] ; part.strip()
            # <listcomp>
                # FIXME: for loop)
                part = .0
                if not part.strip(): goto 4
                # FIXME: needs manual fix
                [] ; part.strip()
            # <listcomp>
                # FIXME: for loop)
                part = .0
                if not part.strip(): goto 4
                # FIXME: needs manual fix
                [] ; part.strip()
            # <genexpr>
                # FIXME: for loop)
                k = .0
                yield (k in clean_part)
                <generator>
                # FIXME: needs manual fix
            # <listcomp>
                # FIXME: for loop)
                row = .0
                if looks_like_fragment(row.get('raw_text', ''), row.get('text', '')): goto 4
                # FIXME: needs manual fix
                [] ; row
                if not source_has_cues: goto 36
                if item.get('text', ''): goto 26
                if not source_semantic_cues(str, item.get('text', '')): goto 36
                # FIXME: needs manual fix
                re.search ; 1
                return (0, item.get('conservative_score', -999.0), item['rule_score'], -len(item['text']))
            # <listcomp>
                # FIXME: for loop)
                row = .0
                # FIXME: needs manual fix
                [] ; row['text']
            # <dictcomp>
                # FIXME: for loop)
                text = <unpack_2>
                score = .0
                # FIXME: needs manual fix
                {} ; text: round(float(score), 4)
            # <listcomp>
                # FIXME: for loop)
                r = .0
                if not (r.get('rerank_score') is not None): goto 4
                # FIXME: needs manual fix
                [] ; r
                return r.get('conservative_score', -999.0)
            # <listcomp>
                # FIXME: for loop)
                row = .0
                if not row.get('text'): goto 4
                if self._contains_colloquial_residue(row.get('text', '')): goto 4
                if self._is_low_quality_first_level_code(row.get('text', ''), normalized, bool(row.get('knn_source'))): goto 4
                if looks_like_fragment(row.get('raw_text', ''), row.get('text', '')): goto 4
                # FIXME: needs manual fix
                [] ; row
                if not (item.get('rerank_score') is not None): goto 24
                # FIXME: needs manual fix
                item.get('rerank_score')
                return (-1.0, item.get('conservative_score', -999.0), item.get('rule_score', 0.0), -len(item.get('text', '')))
            # <genexpr>
                # FIXME: for loop)
                r = .0
                if not (r.get('text') == selected_candidate): goto 30
                yield r.get('anchor_source')
                (r.get('text') == selected_candidate)
                <generator>
                # FIXME: needs manual fix
                if not (item['rerank_score'] is not None): goto 30
                # FIXME: needs manual fix
                item.get('conservative_score', -999.0) ; item['rerank_score']
                return (<?>, -1.0, item['rule_score'], -len(item['text']))
            # <genexpr>
                # FIXME: for loop)
                r = .0
                if not (r.get('text') == selected_candidate): goto 4
                yield r
                <generator>
                # FIXME: needs manual fix

    def rewrite_first_level_code(self, text):
        if text: goto 8
        cleaned = text.strip()
        if cleaned: goto 24
        return ''
        cleaned = re.sub('(?<=[\\u4e00-\\u9fff])\\?(?=[\\u4e00-\\u9fff])', '，', cleaned)
        cleaned = re.sub('^\\s*[\\u2460-\\u2473\\u2776-\\u277F\\u24F5-\\u24FE\\u3251-\\u325F①②③④⑤⑥⑦⑧⑨⑩]+[\\u3001\\.\\uFF0E\\)\\uFF09\\s]*', '', cleaned)
        cleaned = re.sub('^\\s*(?:\\d+|[一二三四五六七八九十]+)[\\u3001\\.\\uFF0E\\)\\uFF09]\\s*', '', cleaned)
        cleaned = re.sub('^(\\u6211\\u89c9\\u5f97|\\u6211\\u8ba4\\u4e3a|\\u6211\\u611f\\u89c9|\\u5176\\u5b9e|\\u7136\\u540e|\\u5c31\\u662f\\u8bf4|\\u90a3\\u4e48|\\u8fd9\\u4e2a|\\u90a3\\u4e2a|\\u4f60\\u770b|\\u4f60\\u8bf4|\\u5982\\u679c\\u8bf4)+', '', cleaned)
        cleaned = re.sub('(\\u8fd9\\u4e2a\\u4e1c\\u897f|\\u8fd9\\u4e2a\\u4e8b\\u60c5|\\u8fd9\\u4ef6\\u4e8b|\\u8fd9\\u4e2a\\u95ee\\u9898)', '', cleaned)
        cleaned = re.sub('(\\u53ef\\u80fd|\\u5927\\u6982|\\u4e5f\\u8bb8|\\u597d\\u50cf|\\u5176\\u5b9e|\\u5b9e\\u9645\\u4e0a|\\u8bf4\\u5b9e\\u8bdd|\\u76f8\\u5f53\\u4e8e|\\u5c31\\u662f|\\u7136\\u540e)', '', cleaned)
        cleaned = re.sub('(怎么说呢|就是说|我觉得|相当于|要看|分场合|这个东西|这个事情|这个问题)', '', cleaned)
        cleaned = re.sub('每个阶段的重点不同.*参与深度是不同的', '阶段性参与调整', cleaned)
        cleaned = re.sub('怎么会有人.*?(?:吃饭|消费|购买)', '客源不确定', cleaned)
        cleaned = re.sub('咖啡的种植加工活动遵循生产者本人的生产意愿和生产习惯以及当地默认的惯例开展.*随意', '规范缺乏', cleaned)
        cleaned = re.sub('生产意愿和生产习惯以及当地默认的惯例开展.*随意', '规范缺乏', cleaned)
        cleaned = re.sub('品牌化这个方向', '品牌化方向', cleaned)
        cleaned = re.sub('(推动)(?:他们|我们|他|她)(在?)', '\\1\\2', cleaned)
        cleaned = re.sub('让他能够更好地带领让他能够更好地带领团队实现技术创新', '团队实现技术创新', cleaned)
        cleaned = re.sub('^(?:我们|他们|你们|他|她)(?=(?:在|将|会|对|把)?(?:推动|开展|组织|参与|提出|引入|建立|调整|获得|降低|提高|解决|分析|反馈|合作|转变|优化|对接|支持|购买))', '', cleaned)
        cleaned = re.sub('[吧呢啊嘛呀哦哈哎诶噢呃]+$', '', cleaned)
        cleaned = re.sub('\\u7ed3\\u679c\\u6210\\u529f\\u4e5f\\u5931\\u8d25', '结果可能成功也可能失败', cleaned)
        cleaned = re.sub('(\\u80fd\\u591f|\\u80fd)\\u5f71\\u54cd\\u7684\\u8303\\u56f4', '影响范围', cleaned)
        cleaned = re.sub('\\u5f71\\u54cd\\u7684\\u8303\\u56f4', '影响范围', cleaned)
        cleaned = re.sub('\\u8fd8\\u662f\\u6709\\u9650\\u7684?$', '有限', cleaned)
        cleaned = re.sub('\\u7684(\\u8303\\u56f4|\\u5f71\\u54cd|\\u4f5c\\u7528)', '\\1', cleaned)
        cleaned = re.sub('[（(]?\\d{1,2}:\\d{2}[)）]?', '', cleaned)
        cleaned = re.sub('\\s+', '', cleaned)
        cleaned = re.sub('^(?:\\u6211\\u4EEC|\\u4ED6\\u4EEC|\\u4F60\\u4EEC|\\u4ED6|\\u5979|\\u6211)(?:\\u4E5F|\\u90FD|\\u5C31|\\u4F1A|\\u8981|\\u80FD|\\u53EF\\u4EE5|\\u9700\\u8981|\\u60F3\\u8981|\\u5E0C\\u671B|\\u6253\\u7B97|\\u8BA1\\u5212|\\u51C6\\u5907)?', '', cleaned)
        cleaned = re.sub('(?:\\u662F\\u4E0D\\u662F|\\u80FD\\u4E0D\\u80FD|\\u8981\\u4E0D\\u8981|\\u4F1A\\u4E0D\\u4F1A|\\u6709\\u6CA1\\u6709|\\u884C\\u4E0D\\u884C)[\\u3002\\uFF0C]?$', '', cleaned)
        cleaned = re.sub('(?:\\u539F\\u56E0\\u662F|\\u662F\\u56E0\\u4E3A|\\u4E3B\\u8981\\u662F|\\u5176\\u5B9E\\u662F)(.{4,30})$', '\\1', cleaned)
        cleaned = re.sub('\\u65B9\\u9762\\u7684(?:\\u4E1C\\u897F|\\u4E8B\\u60C5|\\u6D3B|\\u5185\\u5BB9|\\u5DE5\\u4F5C|\\u95EE\\u9898)$', '', cleaned)
        cleaned = re.sub('^(.{2,20})(?:\\u7684\\u65B9\\u9762|\\u7684\\u89D2\\u5EA6|\\u7684\\u5C42\\u9762|\\u7684\\u60C5\\u51B5|\\u7684\\u73AF\\u8282|\\u7684\\u9636\\u6BB5|\\u7684\\u8FC7\\u7A0B|\\u7684\\u6D41\\u7A0B|\\u7684\\u6548\\u679C|\\u7684\\u7ED3\\u679C|\\u7684\\u95EE\\u9898)$', '\\1', cleaned)
        cleaned = re.sub('^(?:\\u5728|\\u4ECE|\\u7531|\\u5BF9|\\u628A|\\u88AB|\\u8BA9|\\u53EB|\\u7ED9)(.{3,25})$', '\\1', cleaned)
        cleaned = re.sub('^(.{4,30})(?:\\u7B49\\u7B49|\\u4E4B\\u7C7B\\u7684|\\u4EC0\\u4E48\\u7684|\\u8FD9\\u4E9B|\\u90A3\\u4E9B)$', '\\1', cleaned)
        return cleaned.strip('，。？！；:"\'()（）[]【】{} ')

    def _rerank_candidate_rows_for_trace(self, trace, score_map):
        candidates = trace.get('candidates', [])
        normalized = trace.get('normalized_sentence', '')
        best_text = trace.get('selected_candidate', '')
        best_score = None
        best_rank_score = float('-inf')
        # FIXME: for loop)
        row = iter(candidates)
        key = (normalized, row.get('text', ''))
        if not (key not in score_map): goto 90
        None[row] = 'rerank_score'
        # FIXME: needs manual fix
        normalized[row] = 'source_text'
        round(float(score_map[key]), 4)[row] = 'rerank_score'
        rank_score = self._conservative_first_level_rank_score(row)
        round(float(rank_score), 4)[row] = 'conservative_score'
        if (best_score is None): goto 164
        if not (rank_score > best_rank_score): goto 188
        best_score = row['rerank_score']
        best_rank_score = rank_score
        best_text = row.get('text', '')
        # FIXME: needs manual fix
        if not (best_score is not None): goto 222
        True[trace] = 'used_rerank'
        self._finalize_first_level_candidate(best_text, normalized)[trace] = 'selected_candidate'
        # FIXME: for loop)
        row = iter(candidates)
        if (row.get('text') == best_text): goto 262
        (row.get('text') == trace.get('selected_candidate'))[row] = 'selected'
        # FIXME: needs manual fix
        (row.get('text') == best_text)
        candidates.sort(<function 'EnhancedCodingGenerator._rerank_candidate_rows_for_trace.<locals>.<lambda>'>, True)
                if not (item.get('rerank_score') is not None): goto 32
                # FIXME: needs manual fix
                item.get('conservative_score', -999.0) ; item['rerank_score']
                return (<?>, -1.0, item.get('rule_score', 0.0), -len(item.get('text', '')))

    def _apply_global_batch_rerank(self, traces, model_manager):
        if not Config: goto 24
        if not getattr(Config, 'ENABLE_ABSTRACT_RERANKER', False): goto 24
        if (model_manager is not None): goto 28
        # try:
        if not hasattr(model_manager, 'ensure_abstract_reranker_loaded'): goto 48
        model_manager.ensure_abstract_reranker_loaded()
        if not hasattr(model_manager, 'is_abstract_reranker_available'): goto 66
        if model_manager.is_abstract_reranker_available(): goto 72
        if not Config: goto 112
        # FIXME: needs manual fix
        max(1, int(max(getattr(Config, 'ABSTRACT_RERANK_TOP_N', 6), getattr(Config, 'FIRST_LEVEL_GLOBAL_RERANK_TOP_N', 24))))
        rerank_limit = 24
        pairs = []
        seen = set()
        # FIXME: for loop)
        trace = iter(traces)
        normalized = trace.get('normalized_sentence', '')
        rows = <function 'EnhancedCodingGenerator._apply_global_batch_rerank.<locals>.<listcomp>'>(iter(trace.get('candidates', [])))
        rows.sort(<function 'EnhancedCodingGenerator._apply_global_batch_rerank.<locals>.<lambda>'>, True)
        # FIXME: for loop)
        row = iter(rows[slice(None, rerank_limit)])
        pair = (normalized, row.get('text', ''))
        if not (pair not in seen): goto 250
        seen.add(pair)
        pairs.append(pair)
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        if pairs: goto 264
        originals = <function 'EnhancedCodingGenerator._apply_global_batch_rerank.<locals>.<listcomp>'>(iter(pairs))
        candidates = <function 'EnhancedCodingGenerator._apply_global_batch_rerank.<locals>.<listcomp>'>(iter(pairs))
        if not hasattr(model_manager, 'score_abstract_candidate_pairs'): goto 314
        scores = model_manager.score_abstract_candidate_pairs(pairs)
        # FIXME: needs manual fix
        scores = model_manager.score_abstract_candidates(originals, candidates)
        if not scores: goto 346
        if not (len(scores) != len(pairs)): goto 352
        score_map = <function 'EnhancedCodingGenerator._apply_global_batch_rerank.<locals>.<dictcomp>'>(iter(zip(pairs, scores)))
        # FIXME: for loop)
        trace = iter(traces)
        self._rerank_candidate_rows_for_trace(trace, score_map)
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        exc = None
        # try:
        logger.warning('全局批量一阶重排失败，回退规则候选: ' + str(exc))
        # except
        exc = None
        del exc
        exc = None
        del exc
        raise
        raise
            # <listcomp>
                # FIXME: for loop)
                row = .0
                if not row.get('text'): goto 4
                if self._is_question_like(row.get('text', '')): goto 4
                # FIXME: needs manual fix
                [] ; row
                if item.get('semantic_recall_score', 0.0): goto 36
                return (item.get('conservative_score', -999.0), item.get('semantic_recall_score', 0.0), 0.0, item.get('rule_score', 0.0), -len(item.get('text', '')))
                (item.get('semantic_recall_score') is not None)
            # <listcomp>
                # FIXME: for loop)
                item = .0
                # FIXME: needs manual fix
                [] ; item[0]
            # <listcomp>
                # FIXME: for loop)
                item = .0
                # FIXME: needs manual fix
                [] ; item[1]
            # <dictcomp>
                # FIXME: for loop)
                pair = <unpack_2>
                score = .0
                # FIXME: needs manual fix
                {} ; pair: float(score)

    def abstract_sentence(self, sentence, model_manager):
        self._ensure_first_level_defaults()
        if sentence: goto 14
        s0 = ''.strip()
        if s0: goto 28
        return ''
        sentence
        if not (s0 in self.abstract_cache): goto 48
        return self.abstract_cache[s0]
        trace = self.build_first_level_candidate_trace(s0, model_manager)
        compact = trace.get('selected_candidate', '')
        compact[self.abstract_cache] = s0
        return compact

    def _normalize_source_sentence(self, text):
        if text: goto 8
        normalized = text.strip()
        if normalized: goto 24
        return ''
        normalized = re.sub('^[\\uFF0C\\u3002\\uFF1F\\uFF01\\uFF1B:\\u3001\\.\\?!;\\s]+', '', normalized)
        normalized = re.sub('[\\?\\uFF1F]+$', '。', normalized)
        normalized = re.sub('[!\\uFF01]+$', '。', normalized)
        normalized = re.sub('\\s+', ' ', normalized)
        return normalized.strip()

    def _post_refine_phrase(self, text):
        if text: goto 8
        refined = text('')
        # FIXME: for loop)
        pattern = iter(getattr(self, 'bad_phrase_patterns', []))
        refined = re.sub(pattern, '', refined)
        # FIXME: needs manual fix
        refined = re.sub('[（(]?\\d{1,2}:\\d{2}[)）]?', '', refined)
        refined = re.sub('^(\\u56e0\\u6b64|\\u6240\\u4ee5|\\u7136\\u540e|\\u5e76\\u4e14|\\u800c\\u4e14|\\u90a3\\u4e48|\\u5176\\u5b9e)+', '', refined)
        refined = re.sub('(\\u56e0\\u6b64|\\u6240\\u4ee5|\\u7136\\u540e|\\u5e76\\u4e14|\\u800c\\u4e14)+$', '', refined)
        refined = re.sub('^(\\u8fd9\\u4e2a|\\u90a3\\u4e2a|\\u5b83)(?=[\\u4e00-\\u9fa5])', '', refined)
        refined = re.sub('\\s+', '', refined)
        refined = refined.replace('“', '').replace('”', '').replace('‘', '').replace('’', '')
        return refined.strip('，。？！；:"\'()（）[]【】{}“”‘’ ')

    def _is_question_like(self, text):
        if text: goto 8
        t = text.strip()
        if t: goto 24
        return False
        if re.search('[\\?\\uFF1F\\u5417\\u4e48\\u5462]$', t): goto 60
        if re.search('(\\u662f\\u4e0d\\u662f|\\u662f\\u5426|\\u80fd\\u4e0d\\u80fd|\\u53ef\\u4e0d\\u53ef\\u4ee5|\\u4f1a\\u4e0d\\u4f1a|\\u6709\\u6ca1\\u6709|\\u8981\\u4e0d\\u8981)', t): goto 60
        return re.search('(\\u662f\\u4e0d\\u662f|\\u662f\\u5426|\\u80fd\\u4e0d\\u80fd|\\u53ef\\u4e0d\\u53ef\\u4ee5|\\u4f1a\\u4e0d\\u4f1a|\\u6709\\u6ca1\\u6709|\\u8981\\u4e0d\\u8981)', t)(re.search('^(\\u4e3a\\u4ec0\\u4e48|\\u600e\\u4e48|\\u5982\\u4f55|\\u54ea[\\u91cc\\u513f\\u4e2a\\u79cd])', t))
        bool ; re.search('[\\?\\uFF1F\\u5417\\u4e48\\u5462]$', t)

    def _compute_salience(self, text):
        if text: goto 8
        t = text.strip()
        if t: goto 36
        return {}
        # FIXME: needs manual fix
        [] ; ('但是', '不过', '然而', '却', '反而', '反倒', '尽管', '虽然', '即使', '即便', '本来.*但', '原以为.*但', '以前.*现在', '过去.*现在', '之前.*后来', '一开始.*后来')
        contrast_markers = None
        contrast_score = (t)(<function 'EnhancedCodingGenerator._compute_salience.<locals>.<genexpr>'>(iter(contrast_markers)))
        contrast_score = min(contrast_score, 3.0)
        # FIXME: needs manual fix
        sum ; [] ; ('因为', '所以', '因此', '由于', '导致', '致使', '从而', '造成', '引起', '影响', '推动', '促进', '使得', '之所以', '归根结底', '根本原因')
        causal_markers = None
        causal_score = (t)(<function 'EnhancedCodingGenerator._compute_salience.<locals>.<genexpr>'>(iter(causal_markers)))
        causal_score = min(causal_score, 3.0)
        # FIXME: needs manual fix
        sum ; [] ; ('特别', '非常', '最', '极其', '极度', '十分', '根本', '完全', '彻底', '绝对', '毫不', '一直[都在]?', '每次', '总是', '反复', '不断', '太\\w{1,3}$', '很\\w{1,3}$')
        intensity_markers = None
        intensity_score = (t)(<function 'EnhancedCodingGenerator._compute_salience.<locals>.<genexpr>'>(iter(intensity_markers)))
        if not re.search('[！!]$', t): goto 166
        # FIXME: needs manual fix
        sum ; intensity_score ; 1.0
        intensity_score = None
        intensity_score = min(intensity_score, 3.0)
        # FIXME: needs manual fix
        [] ; ('困难', '问题', '矛盾', '冲突', '瓶颈', '障碍', '卡在', '拖慢', '延迟', '受限', '不足', '短板', '风险', '压力', '挑战', '负担', '缺乏', '缺少', '不行', '没办法', '做不了', '无法')
        problem_markers = None
        problem_score = (t)(<function 'EnhancedCodingGenerator._compute_salience.<locals>.<genexpr>'>(iter(problem_markers)))
        problem_score = min(problem_score, 3.0)
        total = ((((problem_score * 1.5) + (contrast_score * 1.2)) + (causal_score * 1.0)) + (intensity_score * 0.8))
        return {}
        sum
            # <genexpr>
                # FIXME: for loop)
                m = .0
                if not re.search(m, t): goto 4
                yield 1.0
                <generator>
                # FIXME: needs manual fix
            # <genexpr>
                # FIXME: for loop)
                m = .0
                if not re.search(m, t): goto 4
                yield 1.0
                <generator>
                # FIXME: needs manual fix
            # <genexpr>
                # FIXME: for loop)
                m = .0
                if not re.search(m, t): goto 4
                yield 1.0
                <generator>
                # FIXME: needs manual fix
            # <genexpr>
                # FIXME: for loop)
                m = .0
                if not re.search(m, t): goto 4
                yield 1.0
                <generator>
                # FIXME: needs manual fix

    def _extract_domain_terms_from_text(text):
        if text: goto 8
        return []
        terms = []
        domain_patterns = ['(?:机制|流程|资源|策略|路径|模式|结构|能力|架构|生态|治理|监督|协同|审批|绩效|战略|需求|服务|创新|评估|优化|配置|整合|调度|保障|约束|反馈|驱动|赋能|转型|传承|保护|非遗|技艺|工艺|文创|文物|修缮|修复|文保|诊疗|康复|护理|医保|健康管理|公共卫生|基层医疗|教学|课程|师资|教材|职业教育|技能培训|素质教育|社区|公益|民生|基层|志愿服务|社区营造|城市更新|旧改|电商|直播|运营|营销|供应链|文旅|景区|民宿|可持续|低碳|绿色|种植|养殖|加工|收购|销售|市场|价格|成本|利润|品牌|质量|标准|有机|合作社|农户|粮食|果蔬|畜牧|渔业|中医|慢病|手工|手艺|织造|雕刻|刺绣|民俗|古建|文物|客户|团队|渠道|产品|数据|平台|系统|设备|算法|培训|考核|认证|检验|补贴|保险|贷款|投资|贸易|消费)']
        # FIXME: for loop)
        pattern = iter(domain_patterns)
        matches = re.findall(pattern, text)
        # FIXME: for loop)
        m = iter(matches)
        if not (m not in terms): goto 76
        if not (len(m) >= 2): goto 76
        terms.append(m)
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        # try:
        from jieba.posseg import posseg
        pseg = jieba.posseg
        words = pseg.cut(text)
        # FIXME: for loop)
        word = <unpack_2>
        flag = iter(words)
        if not flag.startswith('n'): goto 168
        if not (len(word) >= 2): goto 168
        if not (word not in terms): goto 168
        if re.match('^[\\d\\W_]+$', word): goto 168
        terms.append(word)
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        # except
        # FIXME: needs manual fix
        raise
        return terms[slice(None, 20)]

    def _is_coding_worthy_sentence(self, text):
        if text: goto 8
        t = text.strip()
        if t: goto 24
        return False
        min_len = getattr(self, 'coding_worthy_min_length', 10)
        if not (len(t) < min_len): goto 52
        return False
        if not re.match('^(对|嗯|哦|是的|好的|没错|确实|可以|行|好|有|没有|不是)[，,。.!！]?$', t): goto 68
        return False
        if not re.match('^(我|我们)?(觉得|感觉|认为|想|看)(也|都)?(是|就|很|挺|蛮|还|比较)', t): goto 94
        if self._has_first_level_information_cue(t): goto 94
        return False
        if not re.match('^(那我|那我先|我接着说|下一个|接下来|下面|我们先|我先说)', t): goto 120
        if self._has_first_level_information_cue(t): goto 120
        return False
        salience = self._compute_salience(t)
        min_salience = getattr(self, 'coding_worthy_min_salience', 1.5)
        if not (len(t) < 20): goto 176
        if not (salience['total'] < max(min_salience, 1.8)): goto 176
        return False
        if not (salience['total'] < min_salience): goto 232
        if self._has_first_level_information_cue(t): goto 232
        prof_count = (t)(<function 'EnhancedCodingGenerator._is_coding_worthy_sentence.<locals>.<genexpr>'>(iter(('技术', '资源', '平台', '机制', '流程', '生态', '需求', '风险', '压力', '冲突', '协同', '合作', '创新', '服务', '客户', '团队', '品牌', '治理', '监督', '审批', '架构', '数据', '能力', '绩效', '战略', '路径', '场景', '系统', '设备', '模块', '种植', '养殖', '灌溉', '农机', '农产品', '粮食', '合作社', '农户', '非遗', '手艺', '技艺', '传承人', '工匠', '文创', '手工艺', '陶艺', '诊疗', '康复', '护理', '患者', '医保', '药品', '临床', '公共卫生', '教学', '课程', '师资', '学员', '教材', '职业教育', '技能培训', '社区', '公益', '民生', '基层', '志愿服务', '社区营造', '城市更新', '电商', '直播', '运营', '营销', '文旅', '景区', '民宿', '可持续'))))
        if not (prof_count < 2): goto 232
        return False
        sum
        return True
            # <genexpr>
                # FIXME: for loop)
                term = .0
                if not (term in t): goto 4
                yield 1
                <generator>
                # FIXME: needs manual fix

    def _should_skip_sentence_for_coding(self, text, salience):
        if text: goto 8
        t = text.strip()
        if not t: goto 32
        if not (len(t) < 10): goto 36
        return True
        if not re.search('[吗呢呀嘛啊][？?]?$', t): goto 52
        return True
        if not re.search('^(什么|怎么|为什么|如何|哪些|哪方面|什么样|是不是|能不能|要不要|有没有|可不可以|会不会)', t): goto 68
        return True
        if not re.search('^(先给您|先给你|我先|下面我|接下来|首先|本次访谈|这个访谈|刚才|刚刚|旁边|您看|你看|就是说|怎么说)', t): goto 84
        return True
        if not re.match('^(对|嗯|哦|是的|好的|没错|确实|可以|行|好|有|没有|不是)[，,。.!！]?$', t): goto 100
        return True
        if not re.match('^(那我|那我先|我接着说|下一个|接下来|下面|我们先|我先说|你刚刚|你说|你讲)', t): goto 116
        return True
        if not salience: goto 162
        if not (salience.get('total', 0) < 1.0): goto 162
        if self._has_first_level_information_cue(t): goto 162
        if not (len(t) < 30): goto 162
        return True
        if not re.match('^[\\d\\s\\.\\,\\;\\:\\-\\+\\%\\(\\)（）①②③④⑤⑥⑦⑧⑨⑩]+$', t): goto 178
        return True
        return False

    def _formalize_code(self, code):
        if code: goto 8
        ct = code.strip()
        if ct: goto 24
        return ct
        mapping = getattr(self, 'colloquial_to_formal', {})
        # FIXME: for loop)
        colloquial = iter(sorted(mapping.keys(), len, True))
        if not (colloquial in ct): goto 82
        ct = ct.replace(colloquial, mapping[colloquial])
        # FIXME: needs manual fix
        ct = re.sub('(什么的|之类的|那种感觉|这种感觉|这样子|那样子|怎么说呢|就是说)$', '', ct)
        ct = re.sub('[吧呢啊嘛呀哦哈哎诶噢呃]+$', '', ct)
        ct = re.sub('的(\\w{2,4})$', '\\1', ct)
        ct = re.sub('把(.{2,12})(?:聚集|聚拢|吸引)(?:过来|过去|来)', '吸引\\1', ct)
        ct = re.sub('^[我我们你你们他他们它它们大家]*(?:也|还是|都|就|会|要|能)?', '', ct)
        ct = ct.strip()
        if not ct: goto 170
        return ct
        if code: goto 178
        return code.strip()

    def _compress_first_level_candidate_variants(self, text):
        if text: goto 12
        base = str(text(''))
        if base: goto 26
        return []
        self._normalize_candidate_for_first_level
        variants = []
        seen = set()
        add = <function 'EnhancedCodingGenerator._compress_first_level_candidate_variants.<locals>.add'>
        # FIXME: for loop)
        part = iter(self._split_first_level_candidate_segments(base))
        add(part)
        compact = re.sub('^(?:我们|他们|你们|大家|客户|企业|项目|平台|它们|这个|那个|这种|那些|这些)?(?:可以|能够|能|会|要|需要|希望|想要|通过|把|将|对|打造|构建|建立|开展|推进|推动)?', '', part)
        add(compact)
        compact_tail = re.sub('^.*?(技术|品牌|资源|平台|机制|流程|生态|需求|问题|合作|协同|创新|服务|应用|模块|设备|系统|客户|团队|工业互联网)', '\\1', part)
        add(compact_tail)
        # FIXME: for loop)
        transform = iter((('^推动(?:他们|我们|企业|双方)?(.{2,18}(?:合作|交流与合作))$', '\\1'), ('^(?:客户的)?信息系统和(?:我们的)?系统对接$', '客户信息系统对接'), ('^我们购买了?(.{2,16}(?:云存储|云计算|服务))$', '\\1购买'), ('^我们将.{0,12}(生产设备|设备).{0,8}搬到(工业互联网)$', '\\1接入\\2'), ('^我们也会指导客户$', '客户指导协同'), ('^让他能够更好地带领.*?(团队实现技术创新)$', '\\1'), ('^我们从(.{2,16})中找寻灵感$', '\\1启发'), ('^钱已经不再是我的目标了$', '创业目标转变'), ('^我们跟(.{2,18})搞了一个(.{2,12})$', '\\2建设'), ('^一开始书记来找我$', '社区动员参与'), ('^往品牌化这个方向走把粉丝对个人的粘性转嫁到对品牌的粘性$', '品牌粘性转化'), ('^我们自建服务器$', '自建服务器'), ('^每个阶段的重点不同.*?我们参与深度是不同的$', '阶段性参与调整'), ('^我们面临的是自身技术进步$', '自身技术进步压力'), ('^.*生产意愿和生产习惯以及当地默认的惯例开展.*随意$', '规范缺乏')))
        replaced = re.sub(transform[0], transform[1], part)
        if not (replaced != part): goto 170
        add(replaced)
        # FIXME: needs manual fix
        # FIXME: for loop)
        pattern = iter(('((?:影响|导致|推动|推进|解决|分析|反馈|合作|转变|优化|对接|支持|审批|协调|整合|开发|探索|识别|建立|引入|获得|提高|降低|调整|打造|构建|涵养|塑造|形成|提升|购买|指导)[^，,、；;。！？!?]{2,14})', '([^，,、；;。！？!?]{2,10}(?:受影响|受限|受阻|不足|短板|风险|压力|冲突))', '((?:客户|市场|项目|资源|技术|流程|机制|服务|需求|机会|风险|问题|品牌|生态|平台|应用|模块|设备|合作|系统|团队|工业互联网)[^，,、；;。！？!?]{1,10}(?:需求|诉求|反馈|协同|整合|优化|推进|支持|识别|解决|不足|风险|合作|赋能|创新|共创|共享|建立|提升|应用|对接|接入|购买|指导))'))
        # FIXME: for loop)
        match = iter(re.finditer(pattern, part))
        add(match.group(1))
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        return variants

        def add(value):
            cand = self._normalize_candidate_for_first_level(value)
            if cand: goto 18
            if (len(cand) < 4): goto 42
            if not (len(cand) > 24): goto 46
            if self._contains_colloquial_residue(cand): goto 66
            if not self._is_question_like(cand): goto 70
            if not (cand not in seen): goto 102
            seen.add(cand)
            variants.append(cand)

    def _normalize_candidate_for_first_level(self, text):
        if text: goto 8
        refined = text.strip()
        if refined: goto 24
        return ''
        refined = re.sub('(?<=[\\u4e00-\\u9fff])\\?(?=[\\u4e00-\\u9fff])', '，', refined)
        refined = re.sub('^\\s*[\\u2460-\\u2473\\u2776-\\u277F\\u24F5-\\u24FE\\u3251-\\u325F①②③④⑤⑥⑦⑧⑨⑩]+[\\u3001\\.\\uFF0E\\)\\uFF09\\s]*', '', refined)
        refined = re.sub('^\\s*(?:\\d+|[一二三四五六七八九十]+)[\\u3001\\.\\uFF0E\\)\\uFF09]\\s*', '', refined)
        refined = re.sub('^(\\u4f60\\u8bf4|\\u4f60\\u770b|\\u5982\\u679c|\\u8981\\u662f|\\u5047\\u5982|\\u5176\\u5b9e|\\u4f46\\u662f|\\u4e0d\\u8fc7|\\u6240\\u4ee5|\\u56e0\\u6b64|\\u7136\\u540e|\\u5e76\\u4e14|\\u800c\\u4e14|\\u90a3\\u4e48|\\u56e0\\u4e3a)+', '', refined)
        refined = re.sub('^(\\u6211\\u4eec\\u901a\\u8fc7|\\u6211\\u4eec\\u5c31\\u53ef\\u4ee5|\\u6211\\u4eec\\u5c31\\u80fd|\\u6211\\u4eec\\u5c31\\u662f|\\u6211\\u4eec\\u628a|\\u6211\\u4eec\\u53bb|\\u6211\\u4eec\\u6765)+', '', refined)
        refined = re.sub('^(\\u8fd9\\u4e2a\\u6d41\\u7a0b|\\u8fd9\\u4e2a\\u95ee\\u9898|\\u8fd9\\u4e2a\\u4e8b\\u60c5|\\u8fd9\\u4e2a\\u60c5\\u51b5)', '', refined)
        refined = re.sub('(\\u662f\\u4e0d\\u662f|\\u662f\\u5426|\\u80fd\\u4e0d\\u80fd|\\u53ef\\u4e0d\\u53ef\\u4ee5|\\u4f1a\\u4e0d\\u4f1a|\\u6709\\u6ca1\\u6709|\\u8981\\u4e0d\\u8981)', '', refined)
        refined = re.sub('^(\\u4e3a\\u4ec0\\u4e48|\\u600e\\u4e48|\\u5982\\u4f55)', '', refined)
        refined = re.sub('[（(]?\\d{1,2}:\\d{2}[)）]?', '', refined)
        refined = re.sub('\\u7684\\u8bdd', '', refined)
        refined = re.sub('\\u7684\\u65f6\\u5019', '', refined)
        refined = re.sub('(怎么说呢|就是说|我觉得|相当于|要看|分场合|这个东西|这个事情|这个问题)', '', refined)
        refined = re.sub('[吧呢啊嘛呀哦哈哎诶噢呃]+$', '', refined)
        refined = re.sub('\\u6bcf\\u6b21\\u90fd', '经常', refined)
        refined = re.sub('\\u8fd9\\u91cc$', '', refined)
        refined = re.sub('(\\u5c31\\u5f88\\u53d7\\u5f71\\u54cd|\\u5f88\\u53d7\\u5f71\\u54cd)', '受影响', refined)
        refined = re.sub('\\u6211\\u4eec\\u5c31\\u53ea\\u80fd', '只能', refined)
        refined = re.sub('\\u6211\\u4eec\\u53ea\\u80fd', '只能', refined)
        refined = refined.replace('自己', '自行')
        refined = refined.replace('一直催', '催促')
        refined = refined.replace('不够', '不足')
        refined = refined.replace('太慢', '过慢')
        refined = refined.replace('客户的反馈', '客户反馈')
        refined = refined.replace('分析客户的反馈', '分析客户反馈')
        refined = refined.replace('别的组的设备', '别组设备')
        refined = refined.replace('借别组设备来做', '借用别组设备')
        refined = re.sub('\\s+', '', refined)
        refined = refined.replace('“', '').replace('”', '').replace('‘', '').replace('’', '')
        return refined.strip('，。？！；:"\'()（）[]【】{}“”‘’ ')

    def _is_semantically_complete(self, text):
        if text: goto 6
        t = ''.strip()
        if t: goto 20
        return False
        text
        if not (len(t) < 4): goto 36
        return False
        if not self._is_question_like(t): goto 50
        return False
        if not re.search('(\\u600e\\u4e48|\\u5982\\u4f55|\\u8fd9\\u91cc|\\u8fd9\\u6837|\\u90a3\\u6837|\\u8fd9\\u79cd|\\u8fd9\\u4e9b|\\u90a3\\u4e9b|\\u8fd9\\u7c7b|\\u90a3\\u7c7b)$', t): goto 66
        return False
        if not re.search('^(\\u56e0\\u4e3a|\\u5982\\u679c|\\u5373\\u4f7f|\\u867d\\u7136|\\u4f46\\u662f|\\u4e0d\\u8fc7|\\u6240\\u4ee5|\\u56e0\\u6b64|\\u7136\\u540e|\\u5e76\\u4e14|\\u800c\\u4e14)$', t): goto 82
        return False
        if not re.search('^(\\u56e0\\u4e3a|\\u5982\\u679c|\\u5373\\u4f7f|\\u867d\\u7136)', t): goto 110
        if re.search('(\\u6240\\u4ee5|\\u56e0\\u6b64|\\u5bfc\\u81f4|\\u4f7f\\u5f97|\\u4ece\\u800c|\\u53ea\\u80fd|\\u5f71\\u54cd)', t): goto 110
        return False
        if not re.search('^(\\u6211|\\u6211\\u4eec|\\u4f60|\\u4f60\\u4eec).*(\\u4e0d\\u592a\\u6e05\\u695a|\\u4e0d\\u77e5\\u9053|\\u4e0d\\u786e\\u5b9a|\\u8bf4\\u4e0d\\u597d)', t): goto 126
        return False
        if not re.search('^(\\u8fd8\\u53ef\\u4ee5|\\u8fd8\\u597d|\\u5dee\\u4e0d\\u591a|\\u4e00\\u822c\\u822c?)$', t): goto 142
        return False
        return True

    def _detect_concessive_spans(self, text):
        # FIXME: needs manual fix
        [] ; ('\\u5c31\\u7b97(?:\\u662f)?', '\\u5373\\u4fbf(?:\\u662f)?', '\\u5373\\u4f7f(?:\\u662f)?', '\\u54ea\\u6015(?:\\u662f)?', '\\u5c3d\\u7ba1(?:\\u662f)?', '\\u867d\\u7136(?:\\u662f)?', '\\u65e0\\u8bba(?:\\u662f|\\u5982\\u4f55|\\u600e\\u6837)?', '\\u4e0d\\u7ba1(?:\\u662f|\\u5982\\u4f55|\\u600e\\u6837)?', '\\u7eb5\\u4f7f(?:\\u662f)?', '\\u4efb\\u51ed(?:\\u662f)?', '\\u5982\\u679c\\u53ea\\u662f', '\\u5982\\u679c\\u4ec5\\u4ec5', '\\u5982\\u679c\\u5149', '\\u5982\\u679c\\u5149\\u5149', '\\u5047\\u5982\\u53ea\\u662f', '\\u5047\\u5982\\u4ec5\\u4ec5', '\\u8981\\u662f\\u53ea\\u662f', '\\u8981\\u662f\\u4ec5\\u4ec5')
        concessive_starters = None
        clause_end_pattern = re.compile('[\\uff0c,\\u3002\\uff01!\\uff1f?\\uff1b;]|\\u4f46(?:\\u662f)?|\\u4e0d\\u8fc7|\\u7136\\u800c|\\u5374|\\u53ef(?:\\u662f)?|\\u5176\\u5b9e|\\u5b9e\\u9645\\u4e0a|\\u7684\\u8bdd')
        spans = []
        # FIXME: for loop)
        starter = iter(concessive_starters)
        # FIXME: for loop)
        m = iter(re.finditer(starter, text))
        content_start = m.end()
        rest = text[slice(content_start, None)]
        end_match = clause_end_pattern.search(rest)
        if not end_match: goto 94
        content_end = (content_start + end_match.start())
        # FIXME: needs manual fix
        content_end = len(text)
        if not (content_end > content_start): goto 124
        spans.append((content_start, content_end))
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        return spans

    def _detect_negated_spans(self, text):
        spans = []
        pattern1 = re.compile('\\u5bf9(.{2,40}?)(?:\\u5e76?\\u4e0d(?:\\u662f|\\u592a|\\u7279\\u522b|\\u600e\\u4e48|\\u662f\\u5f88)?|\\u5e76\\u975e|\\u6ca1(?:\\u6709)?)(?:.{0,20})(?:\\u5728\\u610f|\\u5728\\u4e4e|\\u5173\\u5fc3|\\u91cd\\u89c6|\\u611f\\u5174\\u8da3|\\u770b\\u91cd|\\u8981\\u6c42|\\u5f3a\\u6c42|\\u7ea0\\u7ed3|\\u8ba1\\u8f83|\\u770b\\u5f97\\u591a\\u91cd|\\u5f88\\u5927\\u5173\\u7cfb|\\u7279\\u610f|\\u4ecb\\u610f|\\u6240\\u8c13)')
        # FIXME: for loop)
        m = iter(pattern1.finditer(text))
        spans.append((m.start(1), m.end(1)))
        # FIXME: needs manual fix
        pattern2 = re.compile('(?:\\u4e0d\\u5728\\u4e4e|\\u4e0d\\u5728\\u610f|\\u4e0d\\u5173\\u5fc3|\\u4e0d\\u91cd\\u8981|\\u65e0\\u6240\\u8c13|\\u6ca1\\u5173\\u7cfb|\\u4e0d\\u770b\\u91cd|\\u4e0d\\u600e\\u4e48\\u770b\\u91cd|\\u4e0d\\u662f\\u7279\\u522b\\u5728\\u610f|\\u4e0d\\u592a\\u5728\\u610f|\\u5e76\\u4e0d\\u5728\\u610f)(.{2,25}?)(?:[\\uff0c,\\u3002\\uff01!\\uff1f?\\uff1b;]|\\u4f46|\\u5176\\u5b9e|$)')
        # FIXME: for loop)
        m = iter(pattern2.finditer(text))
        spans.append((m.start(1), m.end(1)))
        # FIXME: needs manual fix
        pattern3 = re.compile('(?:\\u4e0d\\u89c9\\u5f97|\\u4e0d\\u8ba4\\u4e3a|\\u6ca1\\u89c9\\u5f97|\\u4e0d\\u4f1a\\u89c9\\u5f97)(.{2,30}?)(?:[\\uff0c,\\u3002\\uff01!\\uff1f?\\uff1b;]|$)')
        # FIXME: for loop)
        m = iter(pattern3.finditer(text))
        spans.append((m.start(1), m.end(1)))
        # FIXME: needs manual fix
        return spans

    def _truncate_to_word(self, text, max_length):
        if text: goto 6
        t = ''.strip()
        if (max_length <= 0): goto 32
        if not (len(t) <= max_length): goto 36
        return t
        text
        cut = t[slice(None, max_length)].rstrip('，。？！；:"\'()（）[]【】{} ')
        # FIXME: for loop)
        _ = iter(range(6))
        if cut: goto 74
        # FIXME: needs manual fix
        if not re.search('(\\u600e\\u4e48|\\u5982\\u4f55|\\u8fd9\\u91cc|\\u8fd9\\u6837|\\u90a3\\u6837|\\u8fd9\\u79cd|\\u8fd9\\u4e9b|\\u90a3\\u4e9b|\\u8fd9\\u7c7b|\\u90a3\\u7c7b)$', cut): goto 100
        cut = cut[slice(None, -1)]
        # FIXME: needs manual fix
        if not re.search('(\\u56e0\\u4e3a|\\u5982\\u679c|\\u5373\\u4f7f|\\u867d\\u7136|\\u4f46\\u662f|\\u4e0d\\u8fc7|\\u6240\\u4ee5|\\u56e0\\u6b64|\\u7136\\u540e|\\u5e76\\u4e14|\\u800c\\u4e14)$', cut): goto 126
        cut = cut[slice(None, -1)]
        # FIXME: needs manual fix
        return cut.strip('，。？！；:"\'()（）[]【】{} ')

    def _smart_abbreviate(self, text, max_length):
        if text: goto 8
        t = text.strip()
        if not t: goto 40
        if (max_length <= 0): goto 40
        if not (len(t) <= max_length): goto 44
        return t
        parts = <function 'EnhancedCodingGenerator._smart_abbreviate.<locals>.<listcomp>'>(iter(re.split('[\\uFF0C,\\u3001]', t)))
        if not (len(parts) <= 1): goto 90
        return self._truncate_to_word(t, max_length)
        high_value_words = re.compile('(\\u673A\\u5236|\\u6D41\\u7A0B|\\u8D44\\u6E90|\\u7B56\\u7565|\\u8DEF\\u5F84|\\u6A21\\u5F0F|\\u7ED3\\u6784|\\u80FD\\u529B|\\u67B6\\u6784|\\u751F\\u6001|\\u6CBB\\u7406|\\u76D1\\u7763|\\u534F\\u540C|\\u5BA1\\u6279|\\u7EE9\\u6548|\\u6218\\u7565|\\u9700\\u6C42|\\u670D\\u52A1|\\u521B\\u65B0|\\u8BC4\\u4F30|\\u4F18\\u5316|\\u914D\\u7F6E|\\u6574\\u5408|\\u4FDD\\u969C|\\u7EA6\\u675F|\\u53CD\\u9988|\\u9A71\\u52A8|\\u8D4B\\u80FD|\\u8F6C\\u578B|\\u4E0D\\u8DB3|\\u53D7\\u9650|\\u7F3A\\u5931|\\u7F3A\\u4E4F|\\u53D7\\u963B|\\u5EF6\\u8FDF|\\u5F71\\u54CD|\\u63A8\\u52A8|\\u964D\\u4F4E|\\u589E\\u52A0|\\u5BA2\\u6237|\\u56E2\\u961F|\\u54C1\\u724C|\\u5E73\\u53F0|\\u7CFB\\u7EDF|\\u6570\\u636E|\\u5B89\\u5168|\\u8D28\\u91CF|\\u6210\\u672C|\\u6548\\u7387)')
        part_score = <function 'EnhancedCodingGenerator._smart_abbreviate.<locals>.part_score'>
        ranked = sorted(parts, part_score, True)
        selected = []
        current_len = 0
        # FIXME: for loop)
        part = iter(ranked)
        if not selected: goto 170
        # FIXME: needs manual fix
        test_len = (<?> + 0)
        if not (test_len <= max_length): goto 198
        selected.append(part)
        current_len = test_len
        # FIXME: needs manual fix
        if not selected: goto 214
        return '，'.join(selected)
        best_part = ranked[0]
        return self._truncate_to_word(best_part, max_length)
            # <listcomp>
                # FIXME: for loop)
                p = .0
                if not p.strip(): goto 4
                # FIXME: needs manual fix
                [] ; p.strip()

        def part_score(part):
            s = 0.0
            # FIXME: needs manual fix
            s ; (len(high_value_words.findall(part)) * 2.0)
            s = None
            # FIXME: needs manual fix
            s ; (max(0, (len(part) - 8)) * 0.1)
            s = None
            if not part.endswith('的'): goto 70
            # FIXME: needs manual fix
            s ; 1.5
            s = None
            return s

    def _limit_first_level_text(self, text, max_length):
        if text: goto 6
        t = ''.strip()
        if t: goto 20
        return ''
        text
        if not (max_length <= 0): goto 32
        return t
        if not (len(t) <= max_length): goto 48
        return t
        parts = <function 'EnhancedCodingGenerator._limit_first_level_text.<locals>.<listcomp>'>(iter(re.split('[\\uFF0C,\\u3002]', t)))
        if parts: goto 86
        return self._truncate_to_word(t, max_length)
        best = ''
        # FIXME: for loop)
        i = iter(range(len(parts)))
        built = ''
        # FIXME: for loop)
        j = iter(range(i, len(parts)))
        if built: goto 140
        # FIXME: needs manual fix
        parts[j]
        built = str(built) + '，' + str(parts[j])
        if not (len(built) > max_length): goto 174
        # FIXME: needs manual fix
        cand = built.strip('，。？！；:"\'()（）[]【】{} ')
        if cand: goto 190
        # FIXME: needs manual fix
        if not self._is_semantically_complete(cand): goto 220
        if not (len(cand) > len(best)): goto 220
        best = cand
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        if not best: goto 232
        return best
        return self._smart_abbreviate(t, max_length)
            # <listcomp>
                # FIXME: for loop)
                p = .0
                if not p.strip(): goto 4
                # FIXME: needs manual fix
                [] ; p.strip()

    def generate_codes_with_trained_model(self, processed_data, model_manager, progress_callback, coding_thresholds):
        # try:
        self._apply_similarity_threshold_options(coding_thresholds)
        self._ensure_rag_threshold_defaults()
        if not progress_callback: goto 34
        progress_callback(10)
        if model_manager.is_trained_model_available(): goto 50
        raise ValueError('没有可用的训练模型，请先训练模型')
        all_sentences = []
        file_sentence_mapping = processed_data.get('file_sentence_mapping', {})
        # FIXME: for loop)
        filename = <unpack_2>
        file_data = iter(file_sentence_mapping.items())
        sentences = file_data.get('sentences', [])
        all_sentences.extend(sentences)
        # FIXME: needs manual fix
        if not progress_callback: goto 118
        progress_callback(30)
        filtered_sentences = []
        texts = []
        # FIXME: for loop)
        sent = iter(all_sentences)
        if sent.get('content', ''): goto 148
        t = ''.strip()
        if not self._is_coding_worthy_sentence(t): goto 184
        filtered_sentences.append(sent)
        sent.get('content', '')
        texts.append(t)
        # FIXME: needs manual fix
        if texts: goto 198
        raise ValueError('没有找到有效的文本内容')
        if not progress_callback: goto 210
        progress_callback(50)
        predictions = <unpack_2>
        predicted_labels = model_manager.predict_categories(texts)
        if not progress_callback: goto 236
        progress_callback(70)
        first_level_codes = {}
        second_level_mapping = {}
        self.reset_first_level_trace_meta()
        third_level_mapping = {}
        use_semantic_matching = False
        second_level_codes_list = []
        third_level_codes_list = []
        if not self.coding_library: goto 380
        if not self.semantic_matcher: goto 380
        # try:
        second_level_codes_list = self.coding_library.get_all_second_level_codes()
        third_level_codes_list = self.coding_library.get_all_third_level_codes()
        if not second_level_codes_list: goto 324
        if not third_level_codes_list: goto 324
        use_semantic_matching = True
        logger.info('使用语义相似度匹配进行编码')
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        e = None
        # try:
        logger.error('获取编码库失败: ' + str(e))
        # except
        del e
        # FIXME: needs manual fix
        del e
        raise
        raise
        if coding_thresholds: goto 388
        use_global_batch_rerank = coding_thresholds({}.get('use_global_batch_rerank', False))
        global_traces = []
        if not use_global_batch_rerank: goto 442
        global_traces = <function 'EnhancedCodingGenerator.generate_codes_with_trained_model.<locals>.<listcomp>'>(iter(texts))
        self._apply_global_batch_rerank(global_traces, model_manager)
        bool ; (model_manager, self)
        # FIXME: for loop)
        i = <unpack_2>
        text = <unpack_2>
        label = iter(enumerate(zip(texts, predicted_labels)))
        code_key = (i + 1) + format('04d')
        if not use_global_batch_rerank: goto 510
        if not (i < len(global_traces)): goto 510
        # FIXME: needs manual fix
        trace = self.build_first_level_candidate_trace(text, model_manager)
        abstracted = trace.get('selected_candidate', '')
        source_detail = self._repair_first_level_sentence_detail(filtered_sentences[i])
        if source_detail.get('sentence_id'): goto 576
        self._store_first_level_trace(code_key, trace)
        # FIXME: needs manual fix
        abstracted = self._select_quality_first_level_candidate(trace, source_detail)
        if abstracted: goto 608
        self._store_first_level_trace(code_key, trace)
        # FIXME: needs manual fix
        abstracted = self._clean_code_prefix(abstracted)
        [abstracted, [source_detail], 1, 1, [source_detail]][first_level_codes] = code_key
        self._store_first_level_trace(code_key, trace)
        if not use_semantic_matching: goto 1208
        if not abstracted: goto 1208
        top_k = 5
        cache_key = str(abstracted) + '_' + str(top_k) + '_0.3'
        if not (cache_key in self.similarity_cache): goto 718
        logger.info('使用缓存的相似度计算结果')
        matches = self.similarity_cache[cache_key]
        # FIXME: needs manual fix
        matches = self.semantic_matcher.match_first_level_to_second_level(abstracted, second_level_codes_list, top_k, self.rag_second_level_threshold)
        matches[self.similarity_cache] = cache_key
        if not matches: goto 1176
        if not model_manager: goto 1126
        if not model_manager.is_trained_model_available(): goto 1126
        logger.info('使用bert_finetuned模型对 ' + str(len(matches)) + ' 个候选进行重排')
        candidate_codes = <function 'EnhancedCodingGenerator.generate_codes_with_trained_model.<locals>.<listcomp>'>(iter(matches))
        # try:
        inputs = <function 'EnhancedCodingGenerator.generate_codes_with_trained_model.<locals>.<listcomp>'>(iter(candidate_codes))
        predictions = <unpack_2>
        _ = model_manager.predict_categories(inputs)
        confidences = []
        # FIXME: for loop)
        pred = iter(predictions)
        if not isinstance(pred, tuple): goto 884
        confidences.append(pred[1])
        # FIXME: needs manual fix
        confidences.append(0.0)
        # FIXME: needs manual fix
        if not confidences: goto 972
        best_idx = confidences.index(max(confidences))
        best_match = <unpack_2>
        _ = matches[best_idx]
        second_cat = best_match.get('name')
        "bert_finetuned模型选择的二阶编码: '"(str(second_cat) + "' (置信度: " + max(confidences) + format('.4f') + ')')
        logger.info
        # FIXME: needs manual fix
        best_match = <unpack_2>
        similarity = matches[0]
        second_cat = best_match.get('name')
        "回退到相似度匹配: '"(str(second_cat) + "' (相似度: " + similarity + format('.4f') + ')')
        logger.info
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        e = None
        # try:
        logger.warning('模型重排失败，回退到相似度匹配: ' + str(e))
        best_match = <unpack_2>
        similarity = matches[0]
        second_cat = best_match.get('name')
        "回退到相似度匹配: '"(str(second_cat) + "' (相似度: " + similarity + format('.4f') + ')')
        logger.info
        # except
        del e
        # FIXME: needs manual fix
        del e
        raise
        raise
        best_match = <unpack_2>
        similarity = matches[0]
        second_cat = best_match.get('name')
        "未加载训练模型，使用相似度匹配: '"(str(second_cat) + "' (相似度: " + similarity + format('.4f') + ')')
        logger.info
        # FIXME: needs manual fix
        second_cat = '其他各类话题'
        logger.info("一阶编码 '" + str(abstracted[slice(None, 30)]) + "...' 未找到匹配的二阶编码，归类为'其他各类话题'")
        # FIXME: needs manual fix
        if not ('||' in label): goto 1236
        third_cat_pred = <unpack_2>
        second_cat = label.split('||', 1)
        # FIXME: needs manual fix
        if not label: goto 1246
        # FIXME: needs manual fix
        label
        second_cat = '其他'
        logger.info('使用训练模型预测的二阶编码: ' + str(second_cat))
        second_cat[second_level_mapping] = code_key
        if not use_semantic_matching: goto 1444
        second_code = None
        # FIXME: for loop)
        code = iter(second_level_codes_list)
        if not (code.get('name') == second_cat): goto 1316
        second_code = code
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        if not second_code: goto 1428
        match = self.semantic_matcher.match_second_level_to_third_level(second_code, third_level_codes_list, self.rag_third_level_threshold)
        if not match: goto 1404
        best_match = <unpack_2>
        similarity = match
        third_cat = best_match.get('name')
        "二阶编码 '"(str(second_cat) + "' 匹配到三阶编码 '" + str(third_cat) + "' (相似度: " + similarity + format('.4f') + ')')
        logger.info
        # FIXME: needs manual fix
        third_cat = '其他重要维度'
        logger.info("二阶编码 '" + str(second_cat) + "' 未找到匹配的三阶编码，归类为'其他重要维度'")
        # FIXME: needs manual fix
        third_cat = '其他重要维度'
        logger.info("未找到对应的二阶编码，三阶编码归类为'其他重要维度'")
        # FIXME: needs manual fix
        if not ('||' in label): goto 1472
        third_cat = <unpack_2>
        _ = label.split('||', 1)
        # FIXME: needs manual fix
        third_cat = '综合主题'
        logger.info('使用训练模型预测的三阶编码: ' + str(third_cat))
        third_cat[third_level_mapping] = second_cat
        # FIXME: needs manual fix
        if not progress_callback: goto 1516
        progress_callback(85)
        second_level_codes = defaultdict(list)
        # FIXME: for loop)
        code_key = <unpack_2>
        second_cat = iter(second_level_mapping.items())
        second_level_codes[second_cat].append(code_key)
        # FIXME: needs manual fix
        third_level_codes = defaultdict(list)
        # FIXME: for loop)
        second_cat = <unpack_2>
        third_cat = iter(third_level_mapping.items())
        third_level_codes[third_cat].append(second_cat)
        # FIXME: needs manual fix
        if not progress_callback: goto 1614
        progress_callback(100)
        if not model_manager: goto 1640
        if not hasattr(model_manager, 'release_model_resources'): goto 1640
        model_manager.release_model_resources()
        return {}
        # FIXME: needs manual fix
        e = None
        # try:
        logger.error('使用训练模型生成编码失败: ' + str(str(e)))
        traceback = traceback
        traceback.print_exc()
        if not model_manager: goto 1746
        if not hasattr(model_manager, 'release_model_resources'): goto 1746
        model_manager.release_model_resources()
        # FIXME: needs manual fix
        '错误' ; ['使用训练模型生成编码失败: ' + str(str(e))] ; {} ; '错误' ; ['请检查训练模型'] ; {} ; {}
        # except
        del e
        e = None
        del e
        raise
        raise
            # <listcomp>
                # FIXME: for loop)
                text = .0
                # FIXME: needs manual fix
                [] ; self.build_first_level_candidate_trace(text, model_manager, True)
            # <listcomp>
                # FIXME: for loop)
                match = .0
                # FIXME: needs manual fix
                [] ; match[0].get('name')
            # <listcomp>
                # FIXME: for loop)
                code = .0
                # FIXME: needs manual fix
                [] ; str(abstracted) + ' [SEP] ' + str(code)

    def generate_grounded_theory_codes_multi_files(self, processed_data, model_manager, progress_callback, use_trained_model, coding_thresholds):
        if not use_trained_model: goto 30
        if not model_manager.is_trained_model_available(): goto 30
        return self.generate_codes_with_trained_model(processed_data, model_manager, progress_callback, coding_thresholds)
        return self.generate_codes_with_rules(processed_data, progress_callback, model_manager, coding_thresholds)

    def generate_codes_with_rules(self, processed_data, progress_callback, model_manager, coding_thresholds):
        # try:
        self._apply_similarity_threshold_options(coding_thresholds)
        self._ensure_rag_threshold_defaults()
        if not progress_callback: goto 32
        progress_callback(10)
        combined_text = processed_data['combined_text']
        file_sentence_mapping = processed_data['file_sentence_mapping']
        all_sentences = []
        # FIXME: for loop)
        filename = <unpack_2>
        file_data = iter(file_sentence_mapping.items())
        sentences = file_data.get('sentences', [])
        all_sentences.extend(sentences)
        # FIXME: needs manual fix
        if not progress_callback: goto 104
        progress_callback(30)
        first_level_codes = self.generate_first_level_codes(all_sentences, model_manager, coding_thresholds)
        logger.info('生成 ' + str(len(first_level_codes)) + ' 个一阶编码')
        if not progress_callback: goto 154
        progress_callback(60)
        second_level_codes = self.generate_second_level_codes_improved(first_level_codes, model_manager)
        logger.info('生成 ' + str(len(second_level_codes)) + ' 个二阶编码')
        if not progress_callback: goto 202
        progress_callback(80)
        third_level_codes = self.generate_third_level_codes_improved(second_level_codes)
        logger.info('生成 ' + str(len(third_level_codes)) + ' 个三阶编码')
        if not progress_callback: goto 246
        progress_callback(100)
        if not model_manager: goto 268
        if not hasattr(model_manager, 'release_model_resources'): goto 268
        model_manager.release_model_resources()
        return {}
        # FIXME: needs manual fix
        e = None
        # try:
        logger.error('生成多文件编码失败: ' + str(str(e)))
        traceback = traceback
        traceback.print_exc()
        if not model_manager: goto 356
        if not hasattr(model_manager, 'release_model_resources'): goto 356
        model_manager.release_model_resources()
        # FIXME: needs manual fix
        # except
        del e
        e = None
        del e
        raise
        raise

    def generate_first_level_codes(self, sentences, model_manager, coding_options):
        self.reset_first_level_trace_meta()
        first_level_codes = {}
        trace_items = []
        if coding_options: goto 24
        use_global_batch_rerank = coding_options({}.get('use_global_batch_rerank', False))
        # FIXME: for loop)
        i = <unpack_2>
        sentence = iter(enumerate(sentences))
        # try:
        content = sentence.get('content', '')
        speaker = sentence.get('speaker', '')
        if not speaker: goto 94
        if not (speaker != 'respondent'): goto 94
        # FIXME: needs manual fix
        if not content: goto 254
        if not self._is_coding_worthy_sentence(content.strip()): goto 254
        code_key = (i + 1) + format('04d')
        trace = self.build_first_level_candidate_trace(content, model_manager, use_global_batch_rerank)
        trace_items.append((code_key, sentence, trace))
        if use_global_batch_rerank: goto 254
        source_detail = self._repair_first_level_sentence_detail(sentence)
        if source_detail.get('sentence_id'): goto 200
        self._store_first_level_trace(code_key, trace)
        # FIXME: needs manual fix
        selected_candidate = self._select_quality_first_level_candidate(trace, source_detail)
        self._store_first_level_trace(code_key, trace)
        if selected_candidate: goto 232
        # FIXME: needs manual fix
        [selected_candidate, [source_detail], 1, 1, [source_detail]][first_level_codes] = code_key
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        e = None
        # try:
        logger.warning('处理句子失败 ' + str(i) + ': ' + str(e))
        # except
        del e
        # FIXME: needs manual fix
        del e
        raise
        raise
        if not use_global_batch_rerank: goto 450
        if not trace_items: goto 450
        self._apply_global_batch_rerank(<function 'EnhancedCodingGenerator.generate_first_level_codes.<locals>.<listcomp>'>(iter(trace_items)), model_manager)
        # FIXME: for loop)
        code_key = <unpack_3>
        sentence = iter(trace_items)
        trace = None
        source_detail = self._repair_first_level_sentence_detail(sentence)
        if source_detail.get('sentence_id'): goto 396
        self._store_first_level_trace(code_key, trace)
        # FIXME: needs manual fix
        selected_candidate = self._select_quality_first_level_candidate(trace, source_detail)
        self._store_first_level_trace(code_key, trace)
        if selected_candidate: goto 426
        # FIXME: needs manual fix
        [selected_candidate, [source_detail], 1, 1, [source_detail]][first_level_codes] = code_key
        # FIXME: needs manual fix
        return first_level_codes
            # <listcomp>
                # FIXME: for loop)
                _ = <unpack_3>
                _ = .0
                trace = []
                # FIXME: needs manual fix
                trace

    def _init_rag_components(self):
        # try:
        if not Config: goto 18
        if getattr(Config, 'ENABLE_RAG_CODING', False): goto 24
        if not RuntimeStrategyDetector: goto 44
        if not RagIndexManager: goto 44
        if not RAGSemanticMatcher: goto 44
        if not FirstLevelClusterer: goto 44
        if CodingDecisionPolicy: goto 50
        if self.coding_library: goto 62
        RuntimeStrategyDetector().detect().runtime_strategy = self
        embedding_fn = None
        if not self.semantic_matcher: goto 100
        if not self.runtime_strategy.use_vector_clustering: goto 100
        embedding_fn = self.semantic_matcher.get_embedding
        RagIndexManager(self.coding_library.library_path, Config.RAG_INDEX_DIR, embedding_fn).rag_index_manager = self
        if self.rag_index_manager.ensure_fresh(): goto 148
        logger.warning('RAG索引不可用，回退到传统语义匹配流程')
        RAGSemanticMatcher(Config.RAG_INDEX_DIR, embedding_fn).rag_matcher = self
        if self.rag_matcher.documents: goto 188
        logger.warning('RAG匹配器未加载到索引文档，回退到传统语义匹配流程')
        self._ensure_rag_threshold_defaults()
        self._rebuild_decision_policy_from_matcher()
        FirstLevelClusterer(embedding_fn, self.rag_cluster_similarity_threshold).first_level_clusterer = self
        True.rag_enabled = self
        logger.info('RAG自动编码已启用，运行策略: ' + str(self.runtime_strategy.name))
        # FIXME: needs manual fix
        e = None
        # try:
        logger.warning('RAG组件初始化失败，回退旧流程: ' + str(e))
        False.rag_enabled = self
        # except
        del e
        e = None
        del e
        raise
        raise

    def _ensure_anchor_index(self):
        if not (self.concept_anchor_index is not None): goto 14
        return True
        # try:
        _os = os
        _anchor_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'cache', 'anchor_index')
        _faiss_path = _os.path.join(_anchor_dir, 'anchor_index.faiss')
        _concepts_path = _os.path.join(_anchor_dir, 'concepts.json')
        if not _os.path.exists(_faiss_path): goto 108
        if _os.path.exists(_concepts_path): goto 124
        logger.info('概念锚点索引未构建，跳过概念锚点检索')
        return False
        from build_anchor_index import ConceptAnchorIndex
        ConceptAnchorIndex = build_anchor_index
        _model_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'trained_models', 'concept_anchor')
        _library_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'coding_library.json')
        _anchor_data = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'data', 'clean_anchor_pairs.json')
        if _os.path.exists(_model_path): goto 258
        logger.info('微调锚点模型不存在，跳过概念锚点检索')
        return False
        ConceptAnchorIndex(_model_path, _library_path, _anchor_data)
        logger.info('概念锚点FAISS索引加载成功，%d个概念', len(self.concept_anchor_index.concepts))
        return True
        # FIXME: needs manual fix
        e = None
        # try:
        logger.warning('概念锚点索引加载失败: ' + str(e))
        None
        # except
        del e
        return False
        del e
        raise
        raise

    def _best_candidate_names(self, candidates):
        token_best_name = None
        vector_best_name = None
        token_best = float('-inf')
        vector_best = float('-inf')
        # FIXME: for loop)
        cand = iter(candidates)
        # try:
        token_score = float(cand.get('token_score', 0.0))
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        token_score = 0.0
        # except
        # FIXME: needs manual fix
        raise
        # try:
        vector_score = float(cand.get('vector_score', 0.0))
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        vector_score = 0.0
        # except
        # FIXME: needs manual fix
        raise
        name = cand.get('name')
        if name: goto 144
        # FIXME: needs manual fix
        if not (token_score > token_best): goto 160
        token_best = token_score
        token_best_name = name
        if not (vector_score > vector_best): goto 176
        vector_best = vector_score
        vector_best_name = name
        # FIXME: needs manual fix
        return (token_best_name, vector_best_name)

    def _build_cluster_query(self, cluster):
        if cluster.representative: goto 8
        return ''
        cluster.representative

    def _try_keyword_second_match(self, text, candidates):
        if not text: goto 8
        if candidates: goto 12
        query_tokens = set(jieba.lcut(text))
        if query_tokens: goto 34
        best_name = None
        best_overlap = 0
        # FIXME: for loop)
        cand = iter(candidates)
        name = cand.get('name', '')
        if name: goto 68
        # FIXME: needs manual fix
        name_tokens = set(jieba.lcut(name))
        if name_tokens: goto 88
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        len ; query_tokens ; name_tokens
        overlap = (<?>(<?>) / max(1, len(query_tokens)))
        if not (overlap > best_overlap): goto 130
        best_overlap = overlap
        best_name = name
        # FIXME: needs manual fix
        if not (best_overlap >= 0.4): goto 148
        if not best_name: goto 148
        return best_name

    def _lookup_second_code_by_name(self, second_name):
        if not self.coding_library: goto 10
        if second_name: goto 14
        # FIXME: for loop)
        code = iter(self.coding_library.get_all_second_level_codes())
        if not (code.get('name') == second_name): goto 90
        normalized = dict(code)
        'second'[normalized] = 'level'
        str(code.get('id', '')).strip()[normalized] = 'code_id'
        normalized
        # FIXME: needs manual fix

    def _refresh_rag_matcher_if_needed(self):
        if not self.rag_enabled: goto 12
        if self.rag_index_manager: goto 16
        # try:
        if not self.rag_index_manager.is_fresh(): goto 34
        if self.rag_index_manager.ensure_fresh(): goto 60
        logger.warning('RAG索引刷新失败，将继续使用旧匹配流程')
        embedding_fn = None
        if not self.semantic_matcher: goto 92
        if not getattr(self.runtime_strategy, 'use_vector_clustering', False): goto 92
        embedding_fn = self.semantic_matcher.get_embedding
        RAGSemanticMatcher(Config.RAG_INDEX_DIR, embedding_fn).rag_matcher = self
        self._rebuild_decision_policy_from_matcher()
        logger.info('检测到编码库变更，已自动刷新RAG派生索引与匹配器')
        # FIXME: needs manual fix
        e = None
        # try:
        logger.warning('RAG索引运行时刷新失败: ' + str(e))
        # except
        del e
        e = None
        del e
        raise
        raise

    def generate_second_level_codes_improved(self, first_level_codes, model_manager):
        self._ensure_rag_threshold_defaults()
        if first_level_codes: goto 20
        return {}
        logger.info('开始二阶编码分类，共 ' + str(len(first_level_codes)) + ' 个一阶编码')
        {}._second_level_decision_meta = self
        self._refresh_rag_matcher_if_needed()
        if not self.rag_enabled: goto 480
        if not self.rag_matcher: goto 480
        if not self.decision_policy: goto 480
        if not self.first_level_clusterer: goto 480
        # try:
        clusters = self.first_level_clusterer.cluster(first_level_codes)
        categories = defaultdict(list)
        top_k = max(1, int(getattr(Config, 'RAG_FINAL_TOP_K', 5)))
        token_top_k = max(1, int(getattr(self.runtime_strategy, 'token_top_k', getattr(Config, 'RAG_TOKEN_TOP_K', 80))))
        # FIXME: for loop)
        cluster = iter(clusters)
        text = self._build_cluster_query(cluster)
        if text.strip(): goto 204
        categories[self.decision_policy.other_second_name].extend(cluster.source_keys)
        # FIXME: needs manual fix
        candidates = self.rag_matcher.match_first_level_to_second_level(text, top_k, token_top_k)
        token_best = <unpack_2>
        vector_best = self._best_candidate_names(candidates)
        decision = self.decision_policy.decide_second_level(candidates, max(1, cluster.support), token_best, vector_best)
        if not (decision.name == self.decision_policy.other_second_name): goto 320
        if not candidates: goto 320
        keyword_name = self._try_keyword_second_match(text, candidates)
        if not keyword_name: goto 320
        decision = CodingDecision(True, keyword_name, 'second_keyword_fallback', 0.35, self._lookup_second_code_by_name(keyword_name))
        categories[decision.name].extend(cluster.source_keys)
        if not (decision.name not in self._second_level_decision_meta): goto 372
        {}[self._second_level_decision_meta] = decision.name
        # FIXME: needs manual fix
        result = <function 'EnhancedCodingGenerator.generate_second_level_codes_improved.<locals>.<dictcomp>'>(iter(categories.items()))
        if not result: goto 424
        logger.info('RAG二阶编码完成: 共 ' + str(len(result)) + ' 个类别')
        return result
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        e = None
        # try:
        logger.warning('RAG二阶匹配失败，回退旧流程: ' + str(e))
        # except
        del e
        # FIXME: needs manual fix
        del e
        raise
        raise
        if not self.coding_library: goto 494
        if self.semantic_matcher: goto 514
        logger.warning('编码库或语义匹配器不可用，回退到关键词匹配')
        return self._generate_second_level_codes_keyword_based(first_level_codes)
        second_level_codes_list = self.coding_library.get_all_second_level_codes()
        if second_level_codes_list: goto 550
        logger.warning('编码库中没有二阶编码，回退到关键词匹配')
        return self._generate_second_level_codes_keyword_based(first_level_codes)
        second_level_map = {}
        # FIXME: for loop)
        code = iter(second_level_codes_list)
        code_name = code.get('name')
        if not code_name: goto 586
        code[second_level_map] = code_name
        # FIXME: needs manual fix
        if not Config: goto 608
        # FIXME: needs manual fix
        getattr(Config, 'RAG_OTHER_SECOND_LEVEL_NAME', '其他各类话题')
        other_second = '其他各类话题'
        categories = <function 'EnhancedCodingGenerator.generate_second_level_codes_improved.<locals>.<dictcomp>'>(iter(second_level_codes_list))
        [][categories] = other_second
        # FIXME: for loop)
        key = <unpack_2>
        codes = iter(first_level_codes.items())
        if not codes: goto 666
        # FIXME: needs manual fix
        codes[0]
        content = ''
        if content: goto 694
        categories[other_second].append(key)
        # FIXME: needs manual fix
        top_k = 5
        cache_key = str(content) + '_' + str(top_k) + '_0.3'
        if not (cache_key in self.similarity_cache): goto 748
        logger.info('使用缓存的相似度计算结果')
        matches = self.similarity_cache[cache_key]
        # FIXME: needs manual fix
        matches = self.semantic_matcher.match_first_level_to_second_level(content, second_level_codes_list, top_k, self.rag_second_level_threshold)
        matches[self.similarity_cache] = cache_key
        if not matches: goto 1264
        if not model_manager: goto 1156
        if not model_manager.is_trained_model_available(): goto 1156
        logger.info('使用bert_finetuned模型对 ' + str(len(matches)) + ' 个候选进行重排')
        candidate_codes = <function 'EnhancedCodingGenerator.generate_second_level_codes_improved.<locals>.<listcomp>'>(iter(matches))
        # try:
        inputs = <function 'EnhancedCodingGenerator.generate_second_level_codes_improved.<locals>.<listcomp>'>(iter(candidate_codes))
        predictions = <unpack_2>
        _ = model_manager.predict_categories(inputs)
        confidences = []
        # FIXME: for loop)
        pred = iter(predictions)
        if not isinstance(pred, tuple): goto 914
        confidences.append(pred[1])
        # FIXME: needs manual fix
        confidences.append(0.0)
        # FIXME: needs manual fix
        if not confidences: goto 1002
        best_idx = confidences.index(max(confidences))
        best_match = <unpack_2>
        _ = matches[best_idx]
        second_cat = best_match.get('name')
        "bert_finetuned模型选择的二阶编码: '"(str(second_cat) + "' (置信度: " + max(confidences) + format('.4f') + ')')
        logger.info
        # FIXME: needs manual fix
        best_match = <unpack_2>
        similarity = matches[0]
        second_cat = best_match.get('name')
        "回退到相似度匹配: '"(str(second_cat) + "' (相似度: " + similarity + format('.4f') + ')')
        logger.info
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        e = None
        # try:
        logger.warning('模型重排失败，回退到相似度匹配: ' + str(e))
        best_match = <unpack_2>
        similarity = matches[0]
        second_cat = best_match.get('name')
        "回退到相似度匹配: '"(str(second_cat) + "' (相似度: " + similarity + format('.4f') + ')')
        logger.info
        # except
        del e
        # FIXME: needs manual fix
        del e
        raise
        raise
        best_match = <unpack_2>
        similarity = matches[0]
        second_cat = best_match.get('name')
        "一阶编码 '"(str(content[slice(None, 30)]) + "...' 匹配到二阶编码 '" + str(second_cat) + "' (相似度: " + similarity + format('.4f') + ')')
        logger.info
        if not (second_cat in categories): goto 1246
        categories[second_cat].append(key)
        # FIXME: needs manual fix
        categories[other_second].append(key)
        # FIXME: needs manual fix
        logger.info("一阶编码 '" + str(content[slice(None, 30)]) + "...' 未找到匹配的二阶编码，归类为'" + str(other_second) + "'")
        categories[other_second].append(key)
        # FIXME: needs manual fix
        logger.info('二阶编码完成: 共 ' + str(len(categories)) + ' 个类别')
        result = <function 'EnhancedCodingGenerator.generate_second_level_codes_improved.<locals>.<dictcomp>'>(iter(categories.items()))
        return result
            # <dictcomp>
                # FIXME: for loop)
                k = <unpack_2>
                v = .0
                if not v: goto 4
                # FIXME: needs manual fix
                {} ; k: v
            # <dictcomp>
                # FIXME: for loop)
                code = .0
                # FIXME: needs manual fix
                {} ; code.get('name'): []
            # <listcomp>
                # FIXME: for loop)
                match = .0
                # FIXME: needs manual fix
                [] ; match[0].get('name')
            # <listcomp>
                # FIXME: for loop)
                code = .0
                # FIXME: needs manual fix
                [] ; str(content) + ' [SEP] ' + str(code)
            # <dictcomp>
                # FIXME: for loop)
                k = <unpack_2>
                v = .0
                if not v: goto 4
                # FIXME: needs manual fix
                {} ; k: v

    def _generate_second_level_codes_keyword_based(self, first_level_codes):
        # FIXME: needs manual fix
        [] ; ('团队', '部门', '职责', '角色', '架构', '层级', '负责', '职能')
        # FIXME: needs manual fix
        [] ; ('质量', '检测', '测试', '检验', '把关', '评审', '评估', '标准')
        # FIXME: needs manual fix
        [] ; ('创新', '方法', '技术', '研发', '开发', '测试方法', '检测技术')
        # FIXME: needs manual fix
        [] ; ('危机', '挑战', '困难', '问题', '应对', '解决', '突破')
        # FIXME: needs manual fix
        [] ; ('迷茫', '方向感', '确定性', '成就感', '归属感', '荣誉感', '氛围')
        # FIXME: needs manual fix
        [] ; ('领导', '管理', '决策', '资源', '协调', '支持', '目标')
        keyword_map = {}
        categories = <function 'EnhancedCodingGenerator._generate_second_level_codes_keyword_based.<locals>.<dictcomp>'>(iter(keyword_map.keys()))
        [][categories] = '其他各类话题'
        # FIXME: for loop)
        key = <unpack_2>
        codes = iter(first_level_codes.items())
        if not codes: goto 100
        # FIXME: needs manual fix
        codes[0].lower()
        content = ''
        categorized = False
        # FIXME: for loop)
        category = <unpack_2>
        keywords = iter(keyword_map.items())
        keyword_count = (content)(<function 'EnhancedCodingGenerator._generate_second_level_codes_keyword_based.<locals>.<genexpr>'>(iter(keywords)))
        if not (keyword_count >= 1): goto 176
        categories[category].append(key)
        sum
        categorized = True
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        if categorized: goto 196
        categories['其他各类话题'].append(key)
        # FIXME: needs manual fix
        result = <function 'EnhancedCodingGenerator._generate_second_level_codes_keyword_based.<locals>.<dictcomp>'>(iter(categories.items()))
        return result
            # <dictcomp>
                # FIXME: for loop)
                category = .0
                # FIXME: needs manual fix
                {} ; category: []
            # <genexpr>
                # FIXME: for loop)
                keyword = .0
                if not (keyword in content): goto 4
                yield 1
                <generator>
                # FIXME: needs manual fix
            # <dictcomp>
                # FIXME: for loop)
                k = <unpack_2>
                v = .0
                if not v: goto 4
                # FIXME: needs manual fix
                {} ; k: v

    def generate_third_level_codes_improved(self, second_level_codes):
        self._ensure_rag_threshold_defaults()
        if second_level_codes: goto 20
        return {}
        category_names = list(second_level_codes.keys())
        logger.info('开始三阶编码抽象，共 ' + str(len(category_names)) + ' 个二阶编码')
        if not self.rag_enabled: goto 310
        if not self.decision_policy: goto 310
        # try:
        third_level_categories = defaultdict(list)
        # FIXME: for loop)
        second_category = iter(category_names)
        if not (second_category == self.decision_policy.other_second_name): goto 116
        third_level_categories[self.decision_policy.other_third_name].append(second_category)
        # FIXME: needs manual fix
        meta = self._second_level_decision_meta.get(second_category, {})
        if not isinstance(meta, dict): goto 150
        # FIXME: needs manual fix
        meta.get('code')
        second_code = None
        if isinstance(second_code, dict): goto 174
        second_code = self._lookup_second_code_by_name(second_category)
        decision = self.decision_policy.decide_third_level(second_code)
        third_level_categories[decision.name].append(second_category)
        # FIXME: needs manual fix
        result = <function 'EnhancedCodingGenerator.generate_third_level_codes_improved.<locals>.<dictcomp>'>(iter(third_level_categories.items()))
        if not result: goto 254
        logger.info('RAG三阶编码完成: 共 ' + str(len(result)) + ' 个类别')
        return result
        # FIXME: needs manual fix
        # FIXME: needs manual fix
        e = None
        # try:
        logger.warning('RAG三阶匹配失败，回退旧流程: ' + str(e))
        # except
        del e
        # FIXME: needs manual fix
        del e
        raise
        raise
        if not self.coding_library: goto 322
        if self.semantic_matcher: goto 342
        logger.warning('编码库或语义匹配器不可用，回退到规则匹配')
        return self._generate_third_level_codes_rule_based(second_level_codes)
        if not Config: goto 358
        # FIXME: needs manual fix
        getattr(Config, 'RAG_OTHER_SECOND_LEVEL_NAME', '其他各类话题')
        other_second = '其他各类话题'
        if not Config: goto 378
        # FIXME: needs manual fix
        getattr(Config, 'RAG_OTHER_THIRD_LEVEL_NAME', '其他重要维度')
        other_third = '其他重要维度'
        second_level_codes_list = self.coding_library.get_all_second_level_codes()
        third_level_codes_list = self.coding_library.get_all_third_level_codes()
        if not second_level_codes_list: goto 410
        if third_level_codes_list: goto 430
        logger.warning('编码库中没有二阶或三阶编码，回退到规则匹配')
        return self._generate_third_level_codes_rule_based(second_level_codes)
        second_level_map = {}
        # FIXME: for loop)
        code = iter(second_level_codes_list)
        code_name = code.get('name')
        if not code_name: goto 464
        code[second_level_map] = code_name
        # FIXME: needs manual fix
        third_level_map = {}
        # FIXME: for loop)
        code = iter(third_level_codes_list)
        code_name = code.get('name')
        if not code_name: goto 500
        code[third_level_map] = code_name
        # FIXME: needs manual fix
        third_level_categories = {}
        # FIXME: for loop)
        second_category = iter(category_names)
        if not (second_category == other_second): goto 558
        if not (other_third not in third_level_categories): goto 542
        [][third_level_categories] = other_third
        third_level_categories[other_third].append(second_category)
        # FIXME: needs manual fix
        second_code = second_level_map.get(second_category)
        if second_code: goto 608
        if not (other_third not in third_level_categories): goto 592
        [][third_level_categories] = other_third
        third_level_categories[other_third].append(second_category)
        # FIXME: needs manual fix
        match = self.semantic_matcher.match_second_level_to_third_level(second_code, third_level_codes_list, self.rag_third_level_threshold)
        if not match: goto 718
        best_match = <unpack_2>
        similarity = match
        third_cat = best_match.get('name')
        "二阶编码 '"(str(second_category) + "' 匹配到三阶编码 '" + str(third_cat) + "' (相似度: " + similarity + format('.4f') + ')')
        logger.info
        if not (third_cat not in third_level_categories): goto 702
        [][third_level_categories] = third_cat
        third_level_categories[third_cat].append(second_category)
        # FIXME: needs manual fix
        logger.info("二阶编码 '" + str(second_category) + "' 未找到匹配的三阶编码，归类为'" + str(other_third) + "'")
        if not (other_third not in third_level_categories): goto 760
        [][third_level_categories] = other_third
        third_level_categories[other_third].append(second_category)
        # FIXME: needs manual fix
        if third_level_categories: goto 790
        category_names[third_level_categories] = '综合主题'
        logger.info('生成 ' + str(len(third_level_categories)) + ' 个三阶编码')
        return third_level_categories
            # <dictcomp>
                # FIXME: for loop)
                k = <unpack_2>
                v = .0
                if not v: goto 4
                # FIXME: needs manual fix
                {} ; k: v

    def _generate_third_level_codes_rule_based(self, second_level_codes):
        if second_level_codes: goto 12
        return {}
        category_names = list(second_level_codes.keys())
        organizational_related = <function 'EnhancedCodingGenerator._generate_third_level_codes_rule_based.<locals>.<listcomp>'>(iter(category_names))
        technical_related = <function 'EnhancedCodingGenerator._generate_third_level_codes_rule_based.<locals>.<listcomp>'>(iter(category_names))
        psychological_related = <function 'EnhancedCodingGenerator._generate_third_level_codes_rule_based.<locals>.<listcomp>'>(iter(category_names))
        result = {}
        if not organizational_related: goto 82
        organizational_related[result] = '组织管理与架构设计'
        if not technical_related: goto 94
        technical_related[result] = '技术研发与创新应用'
        if not psychological_related: goto 106
        psychological_related[result] = '组织文化与心理氛围'
        remaining = <function 'EnhancedCodingGenerator._generate_third_level_codes_rule_based.<locals>.<listcomp>'>(iter(category_names))
        if not remaining: goto 140
        remaining[result] = '其他重要维度'
        if result: goto 152
        category_names[result] = '综合主题'
        return result
            # <listcomp>
                # FIXME: for loop)
                name = .0
                if not (name)(<function 'EnhancedCodingGenerator._generate_third_level_codes_rule_based.<locals>.<listcomp>.<genexpr>'>(iter(('团队', '组织', '职责', '架构', '领导', '管理')))): goto 4
                # FIXME: needs manual fix
                [] ; any ; name
            # <listcomp>
                # FIXME: for loop)
                name = .0
                if not (name)(<function 'EnhancedCodingGenerator._generate_third_level_codes_rule_based.<locals>.<listcomp>.<genexpr>'>(iter(('技术', '方法', '创新', '检测', '质量', '研发')))): goto 4
                # FIXME: needs manual fix
                [] ; any ; name
            # <listcomp>
                # FIXME: for loop)
                name = .0
                if not (name)(<function 'EnhancedCodingGenerator._generate_third_level_codes_rule_based.<locals>.<listcomp>.<genexpr>'>(iter(('心理', '氛围', '情感', '成长', '发展', '感觉')))): goto 4
                # FIXME: needs manual fix
                [] ; any ; name
            # <listcomp>
                # FIXME: for loop)
                name = .0
                if (name)(<function 'EnhancedCodingGenerator._generate_third_level_codes_rule_based.<locals>.<listcomp>.<genexpr>'>(iter((organizational_related, technical_related, psychological_related)))): goto 4
                # FIXME: needs manual fix
                [] ; any ; name