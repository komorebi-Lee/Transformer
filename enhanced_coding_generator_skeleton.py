import logging
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
import re
import jieba
from jieba.posseg import pseg
from collections import Counter, defaultdict
import os
import json

logger = logging.getLogger(__name__)

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
    from quality_learner import HighQualitySampleLearner
except Exception as e:
    logger.warning("导入HighQualitySampleLearner失败: " + str(e))
    HighQualitySampleLearner = None


class EnhancedCodingGenerator:
    """增强的扎根理论编码生成器 - 支持训练模型预测"""

    def _clean_code_prefix(code):
        """
            清理一阶编码开头的标点符号
            
            规则：
            - 移除开头的所有标点符号（除了引号）
            - 保留引号，因为它与后文有联系
            
            Args:
                code: 原始编码文本
                
      """
        pass

    def __init__(self):
        # Uses: min_sentence_length, similarity_threshold, max_codes_per_paragraph, Config, getattr, max_first_level_length, abstract_cache, similarity_cache, bad_phrase_patterns, colloquial_to_formal
        # Strings: ['FIRST_LEVEL_CODE_MAX_LENGTH', '总是要', '需持续']
        pass

    def _ensure_first_level_defaults(self):
        # Uses: hasattr, abstract_cache, Config, getattr, max_first_level_length, _first_level_trace_meta, first_level_prototypes, isinstance, bad_phrase_patterns, list
        # Strings: ['abstract_cache', 'max_first_level_length', 'FIRST_LEVEL_CODE_MAX_LENGTH']
        pass

    def _default_second_threshold(self):
        # Uses: Config, float, getattr
        # Strings: ['RAG_SECOND_LEVEL_THRESHOLD']
        pass

    def _default_third_threshold(self):
        # Uses: Config, float, getattr
        # Strings: ['RAG_THIRD_LEVEL_THRESHOLD']
        pass

    def _default_cluster_threshold(self):
        # Uses: Config, float, getattr
        # Strings: ['RAG_CLUSTER_SIMILARITY_THRESHOLD']
        pass

    def _clamp_threshold(self, value, default):
        # Uses: float, TypeError, ValueError
        pass

    def _ensure_rag_threshold_defaults(self):
        # Uses: hasattr, _default_second_threshold, rag_second_level_threshold, _default_third_threshold, rag_third_level_threshold, _default_cluster_threshold, rag_cluster_similarity_threshold
        # Strings: ['rag_second_level_threshold', 'rag_third_level_threshold', 'rag_cluster_similarity_threshold']
        pass

    def configure_similarity_thresholds(self, second_threshold, third_threshold, cluster_threshold):
        """Configure manual auto-coding thresholds without changing result schema."""
        pass

    def _apply_similarity_threshold_options(self, coding_thresholds):
        """Apply threshold fields while leaving runtime options for later stages."""
        pass

    def _repair_first_level_sentence_detail(self, sentence):
        """Normalize source metadata so auto codes can always navigate back to text."""
        pass

    def _first_level_anchor_ratio(self, code_text, source_text):
        # Uses: str, set, sum, max, len
        # Strings: ['EnhancedCodingGenerator._first_level_anchor_ratio.<locals>.<listcomp>', 'EnhancedCodingGenerator._first_level_anchor_ratio.<locals>.<genexpr>']
        pass

    def _is_low_quality_first_level_code(self, code_text, source_text, is_knn):
        # Uses: str, strip, len, _looks_semantically_incomplete, _has_valid_first_level_pos_pattern, re, search, getattr, Config, isinstance
        # Strings: ['^(?:说话人|讲话人)\\s*\\d+$', '^(受访者|采访者|被访者|主持人|采访员|提问者)$', 'max_first_level_length']
        pass

    def _has_first_level_information_cue(self, text):
        # Uses: str, strip, bool, re, search
        pass

    def _looks_semantically_incomplete(self, text):
        # Uses: str, strip, len, _is_question_like, re, search, _has_first_level_information_cue
        # Strings: ['^(因为|所以|但是|不过|然后|如果|就是|其实|那个|这个|后来|当时)$', '^(因为|所以|但是|不过|然后|如果|就是|其实|那个|这个|后来|当时)', '(这个|那个|这块|这一块|那种|这种|这样|那样)$']
        pass

    def _has_valid_first_level_pos_pattern(self, text):
        # Uses: str, strip, pseg, cut, Exception, any, _has_first_level_information_cue
        # Strings: ['EnhancedCodingGenerator._has_valid_first_level_pos_pattern.<locals>.<listcomp>', 'EnhancedCodingGenerator._has_valid_first_level_pos_pattern.<locals>.<genexpr>']
        pass

    def _contains_colloquial_residue(self, text):
        # Uses: str, bool, re, search
        # Strings: ['(怎么说呢|就是说|我觉得|相当于|要看|分场合|这个东西|这个事情|这个问题|就是那种|就这种|类似这种)', '[吧呢啊嘛呀哦哈哎诶噢呃]', '(我的|我们的|你们的|他们的|他的|她的)']
        pass

    def _canonicalize_first_level_candidate_rows(self, candidate_rows, source_text):
        # Uses: _finalize_first_level_candidate, str, get, bool, dict, round, float, _conservative_first_level_rank_score, len, append
        # Strings: ['text', 'knn_source', 'anchor_source']
        pass

    def _split_first_level_candidate_segments(self, text):
        # Uses: str, strip, re, split, _extract_semantic_chunks, extend
        # Strings: ['[。！？!?]+', '[，,、；;：:\\n\\r]+', 'EnhancedCodingGenerator._split_first_level_candidate_segments.<locals>.<listcomp>']
        pass

    def _extract_semantic_chunks(self, text):
        # Uses: list, pseg, cut, range, len, min, join, any, append, Exception
        # Strings: ['提取语义完整的短语单元', 'EnhancedCodingGenerator._extract_semantic_chunks.<locals>.<listcomp>', 'EnhancedCodingGenerator._extract_semantic_chunks.<locals>.<genexpr>']
        pass

    def _score_first_level_fragment(self, fragment, source_text):
        # Uses: str, strip, float, min, len, _is_semantically_complete, _first_level_anchor_ratio, re, search, quality_learner
        # Strings: ['-inf', '^(追求|引入|建立|调整|获得|降低|提高|推动|解决|客户|越轨|创新|资源|需求|反馈|开展|优化|合作|转变|对接|影响)', '(这个东西|这个事情|这个问题|什么的|之类的)$']
        pass

    def _finalize_first_level_candidate(self, text, source_text, is_knn):
        # Uses: rewrite_first_level_code, _normalize_candidate_for_first_level, str, bool, strip, set, getattr, len, _has_first_level_information_cue, re
        # Strings: ['first_level_recall_bank', '(什么|怎么|哪些|怎么样|如何|哪方面|什么时候|什么样)', '(的|了|着|过|到|在|中|和|与|或|又|还|也|只|不|没)$']
        pass

    def _conservative_first_level_rank_score(self, row):
        """Blend rerank confidence with a short/focused phrase preference."""
        pass

    def _model_semantic_similarity(self, a, b):
        """使用语义模型计算两个文本的语义相似度（-1表示模型不可用）"""
        pass

    def _select_quality_first_level_candidate(self, trace, source_detail):
        # Uses: str, get, _finalize_first_level_candidate, _is_low_quality_first_level_code, _validate_code_semantic_fit, list, sort
        # Strings: ['original_content', 'content', 'text']
        pass

    def _validate_code_semantic_fit(self, code, source_text):
        """模型语义验证：编码应在保留原文核心语义的同时有所抽象
    
            - 相似度 < 0.30: 编码与原文关系太弱，丢失了核心信息
            - 相似度 > 0.96: 编码几乎等于原文，没有完成抽象提炼
            - 0.30 ~ 0.96: 合理范围
            """
        pass

    def _score_first_level_fragment(self, fragment, source_text):
        # Uses: str, strip, float, min, len, _is_semantically_complete, _first_level_anchor_ratio, _has_first_level_information_cue, re, search
        # Strings: ['-inf', '(反馈|诉求|需求|受影响|短板|机会)', '^(追求|引入|建立|调整|获得|降低|提高|推动|解决|客户|越轨|创新|资源|反馈|开展|优化|合作|转变|对接|影响|分析)']
        pass

    def _conservative_first_level_rank_score(self, row):
        # Uses: bool, get, _finalize_first_level_candidate, str, float, min, re, search, finditer, group
        # Strings: ['knn_source', 'text', '-inf']
        pass

    def _rebuild_decision_policy_from_matcher(self):
        # Uses: CodingDecisionPolicy, rag_matcher, second_code_name_map, third_level_name_map, rag_second_level_threshold, rag_third_level_threshold, list, keys, decision_policy
        pass

    def set_first_level_prototypes(self, prototypes):
        # Uses: first_level_prototypes
        # Strings: ['EnhancedCodingGenerator.set_first_level_prototypes.<locals>.<listcomp>']
        pass

    def set_first_level_recall_bank(self, labels, model_manager):
        # Uses: _ensure_first_level_defaults, set, str, strip, add, append, first_level_recall_bank, first_level_recall_embeddings, get_embeddings, Exception
        # Strings: ['sentence']
        pass

    def _semantic_recall_first_level_labels(self, text, model_manager, top_n, min_score):
        # Uses: _ensure_first_level_defaults, getattr, List, Dict, str, Any, get_embeddings, first_level_recall_embeddings, len, np
        # Strings: ['first_level_recall_bank', 'return', 'EnhancedCodingGenerator._semantic_recall_first_level_labels.<locals>.lexical_hits']
        pass

    def _prototype_keywords(self, manual_code):
        # Uses: str, jieba, lcut, update
        # Strings: ['EnhancedCodingGenerator._prototype_keywords.<locals>.<setcomp>', '客户需求', '需求导向']
        pass

    def _prototype_similarity(self, text, prototype):
        # Uses: set, jieba, lcut, str, get, _prototype_keywords, len, max, min
        # Strings: ['EnhancedCodingGenerator._prototype_similarity.<locals>.<genexpr>', 'source', 'manual_first_code']
        pass

    def _find_first_level_prototype_hits(self, text, top_k):
        # Uses: _ensure_first_level_defaults, first_level_prototypes, _prototype_similarity, append, get, round, float, sort
        # Strings: ['source', 'manual_first_code', 'EnhancedCodingGenerator._find_first_level_prototype_hits.<locals>.<lambda>']
        pass

    def reset_first_level_trace_meta(self):
        # Uses: _ensure_first_level_defaults, _first_level_trace_meta
        pass

    def get_first_level_trace_meta(self):
        # Uses: _ensure_first_level_defaults, dict, _first_level_trace_meta
        pass

    def _store_first_level_trace(self, code_key, trace):
        # Uses: _ensure_first_level_defaults, get, bool, list, _first_level_trace_meta
        # Strings: ['selected_candidate', 'best_rule_candidate', 'used_rerank']
        pass

    def build_first_level_candidate_trace(self, sentence, model_manager, top_n, defer_rerank):
        """Return a compact candidate trace for first-level abstraction."""
        pass

    def rewrite_first_level_code(self, text):
        """Clean a selected first-level code into a shorter coding phrase."""
        pass

    def _rerank_candidate_rows_for_trace(self, trace, score_map):
        # Uses: get, float, round, _conservative_first_level_rank_score, _finalize_first_level_candidate, sort
        # Strings: ['candidates', 'normalized_sentence', 'selected_candidate']
        pass

    def _apply_global_batch_rerank(self, traces, model_manager):
        # Uses: Config, getattr, hasattr, ensure_abstract_reranker_loaded, is_abstract_reranker_available, max, int, set, get, sort
        # Strings: ['ENABLE_ABSTRACT_RERANKER', 'ensure_abstract_reranker_loaded', 'is_abstract_reranker_available']
        pass

    def abstract_sentence(self, sentence, model_manager):
        """Extract a first-level code through the reusable trace flow."""
        pass

    def _normalize_source_sentence(self, text):
        # Uses: str, strip, re, sub
        # Strings: ['^[\\uFF0C\\u3002\\uFF1F\\uFF01\\uFF1B:\\u3001\\.\\?!;\\s]+', '[\\?\\uFF1F]+$', '[!\\uFF01]+$']
        pass

    def _post_refine_phrase(self, text):
        # Uses: str, getattr, re, sub, replace, strip
        # Strings: ['bad_phrase_patterns', '[（(]?\\d{1,2}:\\d{2}[)）]?', '^(\\u56e0\\u6b64|\\u6240\\u4ee5|\\u7136\\u540e|\\u5e76\\u4e14|\\u800c\\u4e14|\\u90a3\\u4e48|\\u5176\\u5b9e)+']
        pass

    def _is_question_like(self, text):
        # Uses: str, strip, bool, re, search
        # Strings: ['[\\?\\uFF1F\\u5417\\u4e48\\u5462]$', '(\\u662f\\u4e0d\\u662f|\\u662f\\u5426|\\u80fd\\u4e0d\\u80fd|\\u53ef\\u4e0d\\u53ef\\u4ee5|\\u4f1a\\u4e0d\\u4f1a|\\u6709\\u6ca1\\u6709|\\u8981\\u4e0d\\u8981)', '^(\\u4e3a\\u4ec0\\u4e48|\\u600e\\u4e48|\\u5982\\u4f55|\\u54ea[\\u91cc\\u513f\\u4e2a\\u79cd])']
        pass

    def _compute_salience(self, text):
        """计算句子的四维显著性分数：转折/对比、因果链、强度/极端、问题/困境"""
        pass

    def _extract_domain_terms_from_text(text):
        """从给定文本中提取领域专业术语（用于RAG文档检索后的术语增强）。
    
            基于中文分词和关键词模式匹配，抽取对编码有用的专业概念词。
            """
        pass

    def _is_coding_worthy_sentence(self, text):
        # Uses: str, strip, getattr, len, re, match, _has_first_level_information_cue, _compute_salience, max, sum
        # Strings: ['判断句子是否值得编码（编码价值门控）', 'coding_worthy_min_length', '^(对|嗯|哦|是的|好的|没错|确实|可以|行|好|有|没有|不是)[，,。.!！]?$']
        pass

    def _should_skip_sentence_for_coding(self, text, salience):
        """句子级预过滤：判断句子本身是否不适合编码（问题、过渡语、元指令等）"""
        pass

    def _formalize_code(self, code):
        # Uses: str, strip, getattr, sorted, keys, len, replace, re, sub
        # Strings: ['将一阶编码规范化：口语词替换为书面用语', 'colloquial_to_formal', '(什么的|之类的|那种感觉|这种感觉|这样子|那样子|怎么说呢|就是说)$']
        pass

    def _compress_first_level_candidate_variants(self, text):
        # Uses: _normalize_candidate_for_first_level, str, set, _split_first_level_candidate_segments, re, sub, finditer, group
        # Strings: ['value', 'EnhancedCodingGenerator._compress_first_level_candidate_variants.<locals>.add', '^(?:我们|他们|你们|大家|客户|企业|项目|平台|它们|这个|那个|这种|那些|这些)?(?:可以|能够|能|会|要|需要|希望|想要|通过|把|将|对|打造|构建|建立|开展|推进|推动)?']
        pass

    def _normalize_candidate_for_first_level(self, text):
        # Uses: str, strip, re, sub, replace
        # Strings: ['(?<=[\\u4e00-\\u9fff])\\?(?=[\\u4e00-\\u9fff])', '^\\s*[\\u2460-\\u2473\\u2776-\\u277F\\u24F5-\\u24FE\\u3251-\\u325F①②③④⑤⑥⑦⑧⑨⑩]+[\\u3001\\.\\uFF0E\\)\\uFF09\\s]*', '^\\s*(?:\\d+|[一二三四五六七八九十]+)[\\u3001\\.\\uFF0E\\)\\uFF09]\\s*']
        pass

    def _is_semantically_complete(self, text):
        # Uses: strip, len, _is_question_like, re, search
        # Strings: ['(\\u600e\\u4e48|\\u5982\\u4f55|\\u8fd9\\u91cc|\\u8fd9\\u6837|\\u90a3\\u6837|\\u8fd9\\u79cd|\\u8fd9\\u4e9b|\\u90a3\\u4e9b|\\u8fd9\\u7c7b|\\u90a3\\u7c7b)$', '^(\\u56e0\\u4e3a|\\u5982\\u679c|\\u5373\\u4f7f|\\u867d\\u7136|\\u4f46\\u662f|\\u4e0d\\u8fc7|\\u6240\\u4ee5|\\u56e0\\u6b64|\\u7136\\u540e|\\u5e76\\u4e14|\\u800c\\u4e14)$', '^(\\u56e0\\u4e3a|\\u5982\\u679c|\\u5373\\u4f7f|\\u867d\\u7136)']
        pass

    def _detect_concessive_spans(self, text):
        """检测让步/条件从句的内容范围（就算是X/即使X/虽然X/如果只是X等），这些内容不是句子核心观点"""
        pass

    def _detect_negated_spans(self, text):
        """检测否定范围内的内容（对X不在意/不在乎X/不认为X等），这些内容表达了说话人否定的对象"""
        pass

    def _truncate_to_word(self, text, max_length):
        # Uses: strip, len, rstrip, range, re, search
        # Strings: ['，。？！；:"\'()（）[]【】{} ', '(\\u600e\\u4e48|\\u5982\\u4f55|\\u8fd9\\u91cc|\\u8fd9\\u6837|\\u90a3\\u6837|\\u8fd9\\u79cd|\\u8fd9\\u4e9b|\\u90a3\\u4e9b|\\u8fd9\\u7c7b|\\u90a3\\u7c7b)$', '(\\u56e0\\u4e3a|\\u5982\\u679c|\\u5373\\u4f7f|\\u867d\\u7136|\\u4f46\\u662f|\\u4e0d\\u8fc7|\\u6240\\u4ee5|\\u56e0\\u6b64|\\u7136\\u540e|\\u5e76\\u4e14|\\u800c\\u4e14)$']
        pass

    def _smart_abbreviate(self, text, max_length):
        """智能缩写：在保证语义完整的前提下缩短代码，保留核心概念
    
            策略：
            1. 优先保留含专业术语/问题词/动作词的片段
            2. 删除状语/程度修饰等非核心部分
            3. 尝试提取"主语核心+谓语关键"结构
            """
        pass

    def _limit_first_level_text(self, text, max_length):
        # Uses: strip, len, re, split, _truncate_to_word, range, _is_semantically_complete, _smart_abbreviate
        # Strings: ['EnhancedCodingGenerator._limit_first_level_text.<locals>.<listcomp>', '[\\uFF0C,\\u3002]', '，。？！；:"\'()（）[]【】{} ']
        pass

    def generate_codes_with_trained_model(self, processed_data, model_manager, progress_callback, coding_thresholds):
        # Uses: _apply_similarity_threshold_options, _ensure_rag_threshold_defaults, is_trained_model_available, ValueError, get, items, extend, strip, _is_coding_worthy_sentence, append
        # Strings: ['使用训练模型生成编码', '没有可用的训练模型，请先训练模型', 'file_sentence_mapping']
        pass

    def generate_grounded_theory_codes_multi_files(self, processed_data, model_manager, progress_callback, use_trained_model, coding_thresholds):
        # Uses: is_trained_model_available, generate_codes_with_trained_model, generate_codes_with_rules
        # Strings: ['为多个文件生成扎根理论三级编码']
        pass

    def generate_codes_with_rules(self, processed_data, progress_callback, model_manager, coding_thresholds):
        # Uses: _apply_similarity_threshold_options, _ensure_rag_threshold_defaults, items, get, extend, generate_first_level_codes, logger, info, len, generate_second_level_codes_improved
        # Strings: ['使用基于规则的编码生成', 'combined_text', 'file_sentence_mapping']
        pass

    def generate_first_level_codes(self, sentences, model_manager, coding_options):
        # Uses: reset_first_level_trace_meta, bool, get, enumerate, _is_coding_worthy_sentence, strip, build_first_level_candidate_trace, append, _repair_first_level_sentence_detail, _store_first_level_trace
        # Strings: ['生成一阶编码 - 优先抽象提炼受访者语句', 'use_global_batch_rerank', 'content']
        pass

    def _init_rag_components(self):
        """初始化RAG组件，失败时保持关闭并回退到旧流程。"""
        pass

    def _ensure_anchor_index(self):
        """懒加载概念锚点FAISS索引（改进7）。
    
            加载微调后的bge-small-zh-v1.5模型 + FAISS索引，
            用于将口语化句子映射到稳定的概念锚点。
    
            Returns:
                True if index is ready, False otherwise.
          """
        pass

    def _best_candidate_names(self, candidates):
        # Uses: float, get, TypeError, ValueError
        # Strings: ['-inf', 'token_score', 'vector_score']
        pass

    def _build_cluster_query(self, cluster):
        # Uses: representative
        # Strings: ['构建簇查询文本：使用簇代表编码文本。']
        pass

    def _try_keyword_second_match(self, text, candidates):
        """语义匹配被拒后的关键词回退：用jieba分词与候选名称做词级匹配。"""
        pass

    def _lookup_second_code_by_name(self, second_name):
        # Uses: coding_library, get_all_second_level_codes, get, dict, str, strip
        # Strings: ['name', 'second', 'level']
        pass

    def _refresh_rag_matcher_if_needed(self):
        """在运行时按需刷新派生索引与匹配器，确保编码库编辑后立即生效。"""
        pass

    def generate_second_level_codes_improved(self, first_level_codes, model_manager):
        # Uses: _ensure_rag_threshold_defaults, logger, info, len, _second_level_decision_meta, _refresh_rag_matcher_if_needed, rag_enabled, rag_matcher, decision_policy, first_level_clusterer
        # Strings: ['生成二阶编码 - 使用语义相似度匹配', '无内容', '开始二阶编码分类，共 ']
        pass

    def _generate_second_level_codes_keyword_based(self, first_level_codes):
        # Uses: keys, items, lower, sum, append
        # Strings: ['基于关键词的二阶编码生成（回退方案）', 'EnhancedCodingGenerator._generate_second_level_codes_keyword_based.<locals>.<dictcomp>', '其他各类话题']
        pass

    def generate_third_level_codes_improved(self, second_level_codes):
        # Uses: _ensure_rag_threshold_defaults, list, keys, logger, info, len, rag_enabled, decision_policy, defaultdict, other_second_name
        # Strings: ['生成三阶编码 - 使用语义相似度匹配', '核心主题', '开始三阶编码抽象，共 ']
        pass

    def _generate_third_level_codes_rule_based(self, second_level_codes):
        # Uses: list, keys
        # Strings: ['基于规则的三阶编码生成（回退方案）', '核心主题', 'EnhancedCodingGenerator._generate_third_level_codes_rule_based.<locals>.<listcomp>']
        pass
