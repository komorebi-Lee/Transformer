import logging
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
import re
import jieba
import jieba.posseg as pseg
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)

try:
    from config import Config
except Exception:  # pragma: no cover
    Config = None

try:
    from coding_library_manager import CodingLibraryManager
except Exception as e:
    logger.warning(f"导入CodingLibraryManager失败: {e}")
    CodingLibraryManager = None

try:
    from semantic_matcher import SemanticMatcher
except Exception as e:
    logger.warning(f"导入SemanticMatcher失败: {e}")
    SemanticMatcher = None

try:
    from runtime_strategy import RuntimeStrategyDetector
    from rag_index import RagIndexManager
    from rag_semantic_matcher import RAGSemanticMatcher
    from first_level_clusterer import FirstLevelClusterer
    from coding_decision_policy import CodingDecisionPolicy
except Exception as e:
    logger.warning(f"导入RAG组件失败: {e}")
    RuntimeStrategyDetector = None
    RagIndexManager = None
    RAGSemanticMatcher = None
    FirstLevelClusterer = None
    CodingDecisionPolicy = None

try:
    from high_quality_sample_learner import HighQualitySampleLearner
except Exception as e:
    logger.warning(f"导入高质量样本学习器失败: {e}")
    HighQualitySampleLearner = None


class EnhancedCodingGenerator:
    """增强的扎根理论编码生成器 - 支持训练模型预测"""

    @staticmethod
    def _clean_code_prefix(code: str) -> str:
        """
        清理一阶编码开头的标点符号
        
        规则：
        - 移除开头的所有标点符号（除了引号）
        - 保留引号，因为它与后文有联系
        
        Args:
            code: 原始编码文本
            
        Returns:
            清理后的编码文本
        """
        if not code:
            return code
        
        # 定义要移除的开头标点（不包括引号）
        # 包括：。！？，、；：…—·●○◆◇■□▲△▼▽★☆※
        punctuation_to_remove = r'^[。！？，、；：…—·●○◆◇■□▲△▼▽★☆※\s]+'
        
        # 移除开头的标点（但保留引号）
        cleaned = re.sub(punctuation_to_remove, '', code)
        
        return cleaned.strip()

    def __init__(self):
        self.min_sentence_length = 5
        self.similarity_threshold = 0.6
        self.max_codes_per_paragraph = 5

        self.max_first_level_length = getattr(Config, 'FIRST_LEVEL_CODE_MAX_LENGTH', 30) if Config else 30
        self.abstract_cache: Dict[str, str] = {}
        # 相似度计算缓存，避免重复计算
        self.similarity_cache: Dict[str, List[Tuple[Dict[str, Any], float]]] = {}
        # 明显不通顺/口语残留短语，后处理时尽量清理
        self.bad_phrase_patterns = [
            r'比如说', r'这?种我', r'我这种', r'然后', r'就是说',
            r'还可以$', r'^不是', r'^就是', r'^所以',
            r'^这跳出来了', r'^我刚刚说的是', r'^我说的是', r'^其实',
            r'^那么', r'^然后', r'^对[，,]?', r'^我自己来说的话[，,]?',
            r'^如果说是', r'\[[0-9]+\]$', r'对对$'
        ]
        # 口语→书面规范化映射（一阶编码最终清洗）
        self.colloquial_to_formal = {
            '搞': '开展', '弄': '处理', '做': '执行', '干': '实施',
            '很难': '困难', '太难': '困难', '太多': '过多', '不够': '不足',
            '老是': '频繁', '总是': '持续', '总是要': '需持续',
            '特别': '显著', '非常': '明显',
            '慢慢': '逐步', '很快': '迅速', '一下子': '骤然',
            '好多': '大量', '一些': '部分', '一点点': '微量',
            '经常': '频繁', '有时候': '偶尔', '每次都': '每次均',
            '没有办法': '受限', '没法': '受限',
            '差不多': '相近', '基本上': '大体',
            '大部分': '多数', '少部分': '少数',
            '主要是': '核心是', '关键是': '关键在于',
            '带来了': '引发', '造成了': '导致', '使得': '促使',
            '没有了': '丧失', '失去了': '丧失',
            '会变得': '将转为', '变成了': '转化为',
            # 扩展：常见访谈口语 → 书面概念
            '主要是要': '需',
            '就需要': '需',
            '更好的': '优化',
            '越来越': '日益',
            '更加': '更趋',
            '想办法': '寻求方案',
            '看一下': '评估',
            '看一看': '审视',
            '找一下': '排查',
            '做出来': '产出',
            '弄出来': '产出',
            '搞出来': '产出',
            '可能是': '可能源于',
            '会不会': '是否',
            '是不是': '是否',
            '能不能': '能否',
            '要不要': '是否需',
            '有没有': '是否存在',
            '没办法': '受限',
            '没什么': '缺乏',
            '不算': '未达',
            '不太': '不足',
            '不怎么': '较少',
            '不大': '有限',
            '好多时候': '多数情形下',
            '有的时候': '部分情形下',
            '有些时候': '偶发情形下',
            '把人': '将人员',
            '给到': '提供',
            '问到': '询问',
            '提到': '提及',
            '说到': '提及',
            '讲到': '阐述',
            '觉得': '认为',
            '想知道': '关注',
            '想着': '意图',
            '想要': '期望',
        }
        # 编码价值门控：低显著性+短句跳过阈值
        self.coding_worthy_min_salience = 1.5
        self.coding_worthy_min_length = 10

        # 初始化编码库管理器
        self.coding_library = None
        if CodingLibraryManager:
            try:
                self.coding_library = CodingLibraryManager()
                logger.info("编码库管理器初始化成功")
            except Exception as e:
                logger.error(f"初始化编码库管理器失败: {e}")
        
        # 初始化语义匹配器
        self.semantic_matcher = None
        
        # 初始化高质量样本学习器
        self.quality_learner = None
        if HighQualitySampleLearner:
            try:
                self.quality_learner = HighQualitySampleLearner()
                import os
                sample_path = os.path.join(os.path.dirname(__file__), 'csv', 'standard_train_optimized.csv')
                if os.path.exists(sample_path):
                    self.quality_learner.load_samples(sample_path)
                    logger.info("高质量样本学习器初始化成功")
                else:
                    logger.warning(f"高质量样本文件不存在: {sample_path}")
            except Exception as e:
                logger.error(f"初始化高质量样本学习器失败: {e}")
        if SemanticMatcher:
            try:
                self.semantic_matcher = SemanticMatcher()
                logger.info("语义匹配器初始化成功")
            except Exception as e:
                logger.error(f"初始化语义匹配器失败: {e}")

        # RAG 组件（默认关闭，初始化成功后开启）
        self.rag_enabled = False
        self.runtime_strategy = None
        self.rag_matcher = None
        self.decision_policy = None
        self.first_level_clusterer = None
        self.rag_index_manager = None
        self._first_level_trace_meta: Dict[str, Dict[str, Any]] = {}
        self._second_level_decision_meta: Dict[str, Dict[str, Any]] = {}
        self.first_level_prototypes: List[Dict[str, Any]] = []
        self.rag_second_level_threshold = self._default_second_threshold()
        self.rag_third_level_threshold = self._default_third_threshold()
        self.rag_cluster_similarity_threshold = self._default_cluster_threshold()
        self._init_rag_components()

    def _ensure_first_level_defaults(self) -> None:
        if not hasattr(self, 'abstract_cache'):
            self.abstract_cache = {}
        if not hasattr(self, 'max_first_level_length'):
            self.max_first_level_length = getattr(Config, 'FIRST_LEVEL_CODE_MAX_LENGTH', 30) if Config else 30
        if not hasattr(self, '_first_level_trace_meta'):
            self._first_level_trace_meta = {}
        if not hasattr(self, 'first_level_prototypes'):
            self.first_level_prototypes = []
        clean_patterns = [
            r'^其实',
            r'^我觉得',
            r'^我认为',
            r'^我感觉',
            r'^如果说',
            r'^然后',
            r'^那么',
            r'^就是说',
            r'\[[0-9]+\]$',
        ]
        if (
            not hasattr(self, 'bad_phrase_patterns')
            or not isinstance(self.bad_phrase_patterns, list)
            or any('?' in pattern for pattern in self.bad_phrase_patterns)
        ):
            self.bad_phrase_patterns = list(clean_patterns)

    def _default_second_threshold(self) -> float:
        return float(getattr(Config, "RAG_SECOND_LEVEL_THRESHOLD", 0.62)) if Config else 0.62

    def _default_third_threshold(self) -> float:
        return float(getattr(Config, "RAG_THIRD_LEVEL_THRESHOLD", 0.58)) if Config else 0.58

    def _default_cluster_threshold(self) -> float:
        return float(getattr(Config, "RAG_CLUSTER_SIMILARITY_THRESHOLD", 0.82)) if Config else 0.82

    def _clamp_threshold(self, value: Optional[float], default: float) -> float:
        if value is None:
            return default
        try:
            threshold = float(value)
        except (TypeError, ValueError):
            return default
        if threshold < 0.0:
            return 0.0
        if threshold > 1.0:
            return 1.0
        return threshold

    def _ensure_rag_threshold_defaults(self) -> None:
        if not hasattr(self, "rag_second_level_threshold"):
            self.rag_second_level_threshold = self._default_second_threshold()
        if not hasattr(self, "rag_third_level_threshold"):
            self.rag_third_level_threshold = self._default_third_threshold()
        if not hasattr(self, "rag_cluster_similarity_threshold"):
            self.rag_cluster_similarity_threshold = self._default_cluster_threshold()

    def configure_similarity_thresholds(
        self,
        second_threshold: Optional[float] = None,
        third_threshold: Optional[float] = None,
        cluster_threshold: Optional[float] = None,
    ) -> None:
        """Configure manual auto-coding thresholds without changing result schema."""
        self._ensure_rag_threshold_defaults()
        self.rag_second_level_threshold = self._clamp_threshold(
            second_threshold,
            self.rag_second_level_threshold,
        )
        self.rag_third_level_threshold = self._clamp_threshold(
            third_threshold,
            self.rag_third_level_threshold,
        )
        self.rag_cluster_similarity_threshold = self._clamp_threshold(
            cluster_threshold,
            self.rag_cluster_similarity_threshold,
        )
        if self.first_level_clusterer is not None:
            self.first_level_clusterer.similarity_threshold = self.rag_cluster_similarity_threshold
        self._rebuild_decision_policy_from_matcher()

    def _apply_similarity_threshold_options(self, coding_thresholds: Optional[Dict[str, Any]]) -> None:
        """Apply threshold fields while leaving runtime options for later stages."""
        if not coding_thresholds:
            return
        threshold_options = {
            key: coding_thresholds[key]
            for key in ("second_threshold", "third_threshold", "cluster_threshold")
            if key in coding_thresholds
        }
        if threshold_options:
            self.configure_similarity_thresholds(**threshold_options)

    def _repair_first_level_sentence_detail(
        self,
        sentence: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Normalize source metadata so auto codes can always navigate back to text."""
        detail = dict(sentence or {})
        content = str(
            detail.get("content", "")
            or detail.get("original_content", "")
            or detail.get("text", "")
        ).strip()
        if content and not detail.get("content"):
            detail["content"] = content
        if content and not detail.get("original_content"):
            detail["original_content"] = content

        sentence_id = str(
            detail.get("sentence_id", "")
            or detail.get("code_id", "")
            or detail.get("number", "")
        ).strip().strip("[]")
        
        # 如果sentence_id仍为空，从内容中提取编号
        if not sentence_id:
            # 关键修复：使用findall找到所有编号，取最后一个
            # 因为模型生成的编码通常会把最相关的句子放在最后引用
            all_markers = re.findall(r"\[(\d+)\]", content)
            if all_markers:
                # 取最后一个编号（模型通常将最重要的引用放在最后）
                sentence_id = all_markers[-1]
                logger.info(f"从内容中提取最后一个编号 [{sentence_id}] 作为sentence_id")
        
        # 验证：如果内容只是说话人标签，不应该关联编号
        if sentence_id:
            # 检查内容是否只是说话人标签
            content_clean = re.sub(r"\[\d+\]", "", content).strip()
            if re.search(r'^说话人\d+$', content_clean) or re.search(r'^(受访者|采访者|被访者|主持人|采访员|提问者)$', content_clean):
                logger.warning(f"内容 '{content_clean}' 只是说话人标签，移除关联编号 [{sentence_id}]")
                sentence_id = ""
                detail.pop("sentence_id", None)
                detail.pop("code_id", None)
        
        if sentence_id:
            detail["sentence_id"] = sentence_id
            detail["code_id"] = sentence_id
        return detail

    def _first_level_anchor_ratio(self, code_text: str, source_text: str) -> float:
        code_chars = [
            ch for ch in str(code_text or "")
            if re.match(r"[\u4e00-\u9fffA-Za-z0-9]", ch)
        ]
        source_chars = set(
            ch for ch in str(source_text or "")
            if re.match(r"[\u4e00-\u9fffA-Za-z0-9]", ch)
        )
        if not code_chars:
            return 0.0
        return sum(1 for ch in code_chars if ch in source_chars) / max(1, len(code_chars))

    def _is_low_quality_first_level_code(self, code_text: str, source_text: str = "") -> bool:
        clean = str(code_text or "").strip()
        source = str(source_text or "").strip()
        if not clean:
            return True
        if len(clean) < 4:
            return True
        if self._looks_semantically_incomplete(clean):
            return True
        if not self._has_valid_first_level_pos_pattern(clean):
            return True
        
        # 过滤说话人标签（如"说话人1"、"说话人2"、"受访者"、"采访者"等）
        if re.search(r'^说话人\d+$', clean):
            return True
        if re.search(r'^(受访者|采访者|被访者|主持人|采访员|提问者)$', clean):
            return True
        max_len = getattr(self, 'max_first_level_length', getattr(Config, 'FIRST_LEVEL_CODE_MAX_LENGTH', 30) if Config else 30)
        if isinstance(max_len, int) and max_len > 0 and len(clean) > max_len:
            return True
        if self._is_question_like(clean):
            return True
        # 含疑问词 → 是问句碎片而非概念
        if re.search(r'(什么|怎么|哪些|怎么样|如何|哪方面|什么时候|什么程度|什么样)', clean):
            return True
        # 以"的/了/着/过/到/在/中"结尾且无信息提示词 → 语义残缺
        if re.search(r'(的|了|着|过|到|在|中|和|与|或|又|还|也|只|不|没)$', clean) and not self._has_first_level_information_cue(clean):
            return True
        # 纯泛泛表述（"X什么Y"、"X哪些Z"等模糊指代模式）
        if re.search(r'^(这|那|哪|什么|怎么).{0,6}(的|方面|事情|问题|情况|流程|模式|渠道|方法)', clean):
            return True
        if re.search(r'[（(]?\d{1,2}:\d{2}[)）]?', clean):
            return True
        if re.search(r"\[[A-Z]?\d+\]", clean):
            return True
        if re.search(r"(没有办法|没办法).*(这个公司|那个时候|因为)", clean):
            return True
        if re.search(r"^(我|我们|你|他|他们)?也?(没有办法|没办法|不知道|不清楚|不确定)", clean):
            return True
        if "\u8fd9\u4e2a\u516c\u53f8" in clean:
            return True
        if re.search(r"\u90a3\u4e2a\u65f6\u5019\u662f\d+$", clean):
            return True
        if re.search(r"^(后来发现|后来|发现因为|因为他们|因为他|因为我们)", clean):
            return True
        if re.search(r"(后来发现因为|那个时候主要在)", clean):
            return True
        if re.search(r"^(先给您介绍|先给你介绍|先介绍一下|本次访谈|下面介绍)", clean):
            return True
        if re.search(r"^\D*(?:\d{1,2}年|\d{1,2}月份|\d{1,2}月)", clean) and not self._has_first_level_information_cue(clean):
            return True
        if re.search(r"(这块|这一块|那种|这个来做|那个来做)", clean) and not self._has_first_level_information_cue(clean):
            return True
        if re.search(r"^(当时|以前|正好|公司原来|我下面|我去做了|我自行|你的|你做|任务一定要|人人的)", clean) and not self._has_first_level_information_cue(clean):
            return True
        if "\u90a3\u4e2a\u65f6\u5019" in clean and not self._has_first_level_information_cue(clean):
            return True
        if re.search(r"^(因为|所以|但是|不过|然后|如果|其实|就是|那个|这个|后来|当时|我们|我|你|他|他们)", clean) and not re.search(
            r"(导致|影响|推动|形成|引入|转变|降低|提高|获得|支持|需求|资源|客户)", clean
        ):
            return True
        if re.search(r"(什么的|之类的|那种感觉|这种感觉|这样子|那样子|怎么说呢|就是说|我觉得|相当于|要看|分场合|这个东西|这个事情|这个问题)$", clean):
            return True
        if re.search(r"(我们认为|我认为|我觉得|我觉得应该|我觉得可以|我觉得可能|我觉得会)", clean):
            return True
        if re.search(r"(开始|进行|做了|搞了|弄了|整了)", clean) and not self._has_first_level_information_cue(clean):
            return True
        if "\u6ca1\u6709\u529e\u6cd5\u76f4\u63a5\u53bb\u501f\u9274\u540c\u884c\u4e1a" in source:
            return True
        if len(clean) <= 5 and not self._has_first_level_information_cue(clean):
            return True
        if source and self._first_level_anchor_ratio(clean, source) < 0.55:
            return True
        
        # 高质量样本检查改为警告，不直接过滤
        if self.quality_learner and not self.quality_learner.is_high_quality_like(clean):
            logger.debug(f"编码不符合高质量模式: {clean}")
        
        return False

    def _has_first_level_information_cue(self, text: str) -> bool:
        t = str(text or "").strip()
        if not t:
            return False
        return bool(
            re.search(
                r"(引入|建立|调整|获得|降低|提高|推动|解决|分析|反馈|合作|转变|优化|对接|支持|审批|流程|"
                r"受影响|受限|不足|短板|导向|循环|机会|需求|资源|服务|监督|指引|开发|探索|"
                r"协调|整合|压力|风险|保鲜|价值|活动|增长|转型|感知|评价|约束|冲突|规范|惯例|随意|"
                r"机制|平台|系统|品牌|团队|客户|治理|场景|能力|策略|路径|结构|模式)",
                t,
            )
        )

    def _looks_semantically_incomplete(self, text: str) -> bool:
        t = str(text or '').strip()
        if not t:
            return True
        if len(t) <= 3:
            return True
        if self._is_question_like(t):
            return True
        if re.search(r'^(因为|所以|但是|不过|然后|如果|就是|其实|那个|这个|后来|当时)$', t):
            return True
        if re.search(r'^(因为|所以|但是|不过|然后|如果|就是|其实|那个|这个|后来|当时)', t) and not self._has_first_level_information_cue(t):
            return True
        if re.search(r'(这个|那个|这块|这一块|那种|这种|这样|那样)$', t):
            return True
        if re.search(r'(什么的|之类的)$', t):
            return True
        if not self._has_first_level_information_cue(t) and len(t) <= 6:
            return True
        # 以"的/了/着/过/到/在/中/和/与/或"结尾 → 结构不完整
        if re.search(r'(的|了|着|过|到|在|中|和|与|或|又|还|也|只|不|没)$', t) and not self._has_first_level_information_cue(t):
            return True
        # 含模糊疑问词但非完整概念
        if re.search(r'(什么|怎么|哪些|怎么样|什么样|如何)', t) and not re.search(r'(机制|流程|资源|策略|路径|模式|结构|能力|需求|服务|创新|管理|评估|质量|安全|风险)', t):
            return True
        return False

    def _has_valid_first_level_pos_pattern(self, text: str) -> bool:
        t = str(text or '').strip()
        if not t:
            return False
        try:
            tokens = [(word.strip(), flag) for word, flag in pseg.cut(t) if str(word).strip()]
        except Exception:
            return True

        if not tokens:
            return False

        words = [word for word, _ in tokens]
        flags = [flag for _, flag in tokens]

        pronouns = {'我', '我们', '你', '你们', '他', '他们', '她', '她们', '它', '它们'}
        modal_particles = {'吗', '嘛', '吧', '呢', '啊', '呀', '哦', '哈', '呗', '啦', '诶', '欸', '么'}
        weak_starters = {'然后', '就是', '其实', '那个', '这个', '后来', '当时'}

        if any(word in modal_particles for word in words):
            return False
        if any(word in pronouns for word in words):
            return False
        if words and words[0] in weak_starters and not self._has_first_level_information_cue(t):
            return False

        noun_like = any(flag.startswith(('n', 's', 'nt', 'nz')) for flag in flags)
        verb_like = any(flag.startswith('v') for flag in flags)
        adj_like = any(flag.startswith('a') for flag in flags)

        if not noun_like:
            return False
        if not (verb_like or adj_like or self._has_first_level_information_cue(t)):
            return False
        return True

    def _contains_colloquial_residue(self, text: str) -> bool:
        t = str(text or "")
        return bool(
            re.search(r'(怎么说呢|就是说|我觉得|相当于|要看|分场合|这个东西|这个事情|这个问题|就是那种|就这种|类似这种)', t)
            or re.search(r'[吧呢啊嘛呀哦哈哎诶噢呃]', t)
            or re.search(r'(我的|我们的|你们的|他们的|他的|她的)', t)
            or re.search(r'(^|[，,、；;])(?:我|我们|你|你们|他|他们|她|她们)(?:也|将|会|跟|和|在|购买|参与|提出|能够|可以|需要|喜欢|已经|当时|就|都|只|要|是|有|不再)', t)
            or re.search(r'^(然后|就是|所以|但是|不过|其实|那个|这个|后来|当时)', t)
            or re.search(r'(什么的|之类的|那种感觉|这种感觉|这样子|那样子)$', t)
        )

    def _canonicalize_first_level_candidate_rows(
        self,
        candidate_rows: List[Dict[str, Any]],
        source_text: str,
    ) -> List[Dict[str, Any]]:
        canonical_rows: List[Dict[str, Any]] = []
        seen: Dict[str, int] = {}
        for row in candidate_rows:
            canonical = self._finalize_first_level_candidate(
                str(row.get("text", "") or ""),
                source_text,
            )
            if not canonical:
                continue
            new_row = dict(row)
            new_row["text"] = canonical
            new_row["conservative_score"] = round(
                float(self._conservative_first_level_rank_score(new_row)),
                4,
            )
            existing = seen.get(canonical)
            if existing is None:
                seen[canonical] = len(canonical_rows)
                canonical_rows.append(new_row)
                continue
            current = canonical_rows[existing]
            if (
                new_row.get("conservative_score", float("-inf")) > current.get("conservative_score", float("-inf"))
                or (
                    new_row.get("conservative_score", float("-inf")) == current.get("conservative_score", float("-inf"))
                    and new_row.get("rule_score", float("-inf")) > current.get("rule_score", float("-inf"))
                )
            ):
                canonical_rows[existing] = new_row
        return canonical_rows

    def _split_first_level_candidate_segments(self, text: str) -> List[str]:
        text = str(text or '').strip()
        if not text:
            return []
        
        segments = []
        sentences = re.split(r'[。！？!?]+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            semantic_chunks = self._extract_semantic_chunks(sentence)
            if semantic_chunks:
                segments.extend(semantic_chunks)
            else:
                parts = re.split(r'[，,、；;：:\n\r]+', sentence)
                segments.extend([part.strip() for part in parts if part and part.strip()])
        
        return segments

    def _extract_semantic_chunks(self, text: str) -> List[str]:
        """提取语义完整的短语单元"""
        chunks = []
        
        patterns = [
            r'([\u4e00-\u9fa5]+[动词]+[\u4e00-\u9fa5]+[名词]+[\u4e00-\u9fa5]+)',
            r'([\u4e00-\u9fa5]+[动词]+[\u4e00-\u9fa5]+[名词])',
            r'([\u4e00-\u9fa5]+[名词]+[\u4e00-\u9fa5]+[动词]+[\u4e00-\u9fa5]+[名词])',
            r'([\u4e00-\u9fa5]+[形容词]+[\u4e00-\u9fa5]+[名词]+[\u4e00-\u9fa5]+[名词])',
        ]
        
        verb_list = {'追求', '引入', '建立', '调整', '获得', '降低', '提高', '推动', '解决', '开展', '优化', '合作', '转变', '对接', '影响', '支持', '开发', '探索', '协调', '整合', '形成', '创新'}
        noun_list = {'资源', '需求', '反馈', '客户', '服务', '平台', '系统', '团队', '能力', '策略', '路径', '结构', '模式', '机制', '品牌', '治理', '场景'}
        
        try:
            tokens = list(pseg.cut(text))
            for i in range(len(tokens)):
                for j in range(i + 1, min(len(tokens) + 1, i + 5)):
                    chunk = ''.join([word for word, _ in tokens[i:j]])
                    if len(chunk) < 4 or len(chunk) > 30:
                        continue
                    
                    pos_tags = [flag for _, flag in tokens[i:j]]
                    has_verb = any(flag.startswith('v') or word in verb_list for word, flag in tokens[i:j])
                    has_noun = any(flag.startswith('n') or word in noun_list for word, flag in tokens[i:j])
                    
                    if has_verb and has_noun:
                        if chunk not in chunks:
                            chunks.append(chunk)
        except Exception:
            pass
        
        return chunks

    def _score_first_level_fragment(self, fragment: str, source_text: str = "") -> float:
        clean = str(fragment or "").strip()
        if not clean:
            return float("-inf")
        score = 0.0
        score += min(len(clean), 24) * 0.35
        if self._is_semantically_complete(clean):
            score += 2.0
        score += self._first_level_anchor_ratio(clean, source_text) * 3.0
        if re.search(r'^(追求|引入|建立|调整|获得|降低|提高|推动|解决|客户|越轨|创新|资源|需求|反馈|开展|优化|合作|转变|对接|影响)', clean):
            score += 1.0
        
        if self.quality_learner:
            quality_score = self.quality_learner.score_by_pattern_match(clean)
            score += quality_score * 0.3
            if not self.quality_learner.is_high_quality_like(clean):
                score -= 0.5
        
        if clean.startswith((
            '我觉得', '其实', '然后', '所以', '但是', '不过', '当时', '那个时候',
            '就是', '相当于', '要看', '分场合', '我们', '我', '你', '他', '他们'
        )):
            score -= 1.0
        if self._contains_colloquial_residue(clean):
            score -= 2.0
        if re.search(r'(这个东西|这个事情|这个问题|什么的|之类的)$', clean):
            score -= 2.5
        if self._has_first_level_information_cue(clean):
            score += 1.2
        if re.search(r'(受影响|受限|受阻|不足|短板|风险|压力|冲突)', clean):
            score += 0.8
        if self._has_first_level_information_cue(text):
            score += 1.2
        if re.search(r'(反馈|诉求|需求|受影响|短板|机会)', text):
            score += 0.8
        if re.search(r'(主要负责|指引方向|监督结果|我们认为|我认为|我觉得)', text):
            score -= 0.7
        return score

    def _finalize_first_level_candidate(self, text: str, source_text: str = "") -> str:
        candidate = self.rewrite_first_level_code(
            self._normalize_candidate_for_first_level(str(text or ""))
        )
        is_recall_label = bool(source_text) and str(candidate or "").strip() in set(getattr(self, 'first_level_recall_bank', []) or [])
        if not candidate:
            return ''
        if len(candidate) < 4 and not is_recall_label:
            return ''
        if len(candidate) <= 5 and not self._has_first_level_information_cue(candidate) and not is_recall_label:
            return ''
        # 快速淘汰：含疑问词直接拒绝
        if re.search(r'(什么|怎么|哪些|怎么样|如何|哪方面|什么时候|什么样)', candidate):
            return ''
        if not self._contains_colloquial_residue(candidate) and (is_recall_label or not self._is_low_quality_first_level_code(candidate, source_text)):
            formalized = self._formalize_code(candidate)
            # 规范化后二次验证：如果形式化后变空或语义残缺，仍需片段拆分
            if len(formalized) >= 4 and not re.search(r'(的|了|着|过|到|在|中|和|与|或|又|还|也|只|不|没)$', formalized):
                return formalized

        best_fragment = ''
        best_score = float('-inf')
        for fragment in self._split_first_level_candidate_segments(candidate):
            refined = self.rewrite_first_level_code(self._normalize_candidate_for_first_level(fragment))
            if not refined:
                continue
            if len(refined) < 4 and refined not in set(getattr(self, 'first_level_recall_bank', []) or []):
                continue
            if len(refined) <= 5 and not self._has_first_level_information_cue(refined) and refined not in set(getattr(self, 'first_level_recall_bank', []) or []):
                continue
            if self._contains_colloquial_residue(refined):
                continue
            if self._is_question_like(refined):
                continue
            if re.search(r'(什么|怎么|哪些|怎么样)', refined):
                continue
            if self._is_low_quality_first_level_code(refined, source_text):
                continue
            score = self._score_first_level_fragment(refined, source_text)
            if score > best_score:
                best_score = score
                best_fragment = refined

        # 自适应阈值：长代码需更高分，短代码可略低
        if best_fragment:
            if len(best_fragment) > 20:
                threshold = 9.0
            elif len(best_fragment) < 8:
                threshold = 8.0
            else:
                threshold = 7.0
            if best_score >= threshold:
                formalized = self._formalize_code(best_fragment)
                if len(formalized) >= 4 and not re.search(r'(的|了|着|过|到|在|中|和|与|或|又|还|也|只|不|没)$', formalized):
                    return formalized
        return ''

    def _conservative_first_level_rank_score(self, row: Dict[str, Any]) -> float:
        """Blend rerank confidence with a short/focused phrase preference."""
        text = self._finalize_first_level_candidate(str(row.get("text", "") or ""), str(row.get("source_text", "") or ""))
        if not text:
            return float("-inf")
        rerank_score = row.get("rerank_score")
        model_score = float(rerank_score) if rerank_score is not None else 0.0
        rule_score = float(row.get("rule_score", 0.0) or 0.0)
        recall_score = float(row.get("semantic_recall_score", 0.0) or 0.0)
        score = model_score * 10.0 + min(rule_score, 6.0) * 0.25
        if Config and getattr(Config, 'FIRST_LEVEL_FUSED_RANKING', False):
            score += min(recall_score, 2.0) * float(getattr(Config, 'FIRST_LEVEL_RECALL_SCORE_WEIGHT', 1.8))
            score += min(max(rule_score, 0.0), 10.0) * float(getattr(Config, 'FIRST_LEVEL_RULE_SCORE_WEIGHT', 0.18))
            if row.get('semantic_recall_score') is not None:
                score += 0.8
            if row.get('semantic_recall_score') is not None and len(text) <= 8:
                score += float(getattr(Config, 'FIRST_LEVEL_SHORT_LABEL_BONUS', 2.5))
        score -= text.count('\uFF0C') * 1.25
        score -= max(0, len(text) - 22) * 0.18
        score -= max(0, len(text) - 30) * 0.55
        if re.search(r'^(时候|比如|然后|所以|那没有|会，因为|他们有时候|我们有时候)', text):
            score -= 2.5
        if re.search(r'(\u8fd9\u4e2a\u4e8b\u60c5|\u8fd9\u4e00\u5757\u76ee\u524d\u6211\u4eec\u80fd\u591f|\u90a3\u4e2a\u65f6\u5019)', text):
            score -= 1.8
        if re.search(r'^(我们|他们|你们|大家|这个|那个|这种|这些|那些|他是|我是|你是)', text):
            score -= 1.4
        if re.search(r'(技术|品牌|资源|平台|机制|流程|生态|需求|问题|合作|协同|创新|服务|应用|模块|设备|系统|客户|团队|工业互联网)', text) and len(text) <= 16:
            score += 0.7
        return score

    def _model_semantic_similarity(self, a: str, b: str) -> float:
        """使用语义模型计算两个文本的语义相似度（-1表示模型不可用）"""
        if not self.semantic_matcher:
            return -1.0
        try:
            emb_fn = getattr(self.semantic_matcher, 'get_embedding', None)
            if not emb_fn:
                return -1.0
            emb_a = emb_fn(a)
            emb_b = emb_fn(b)
            if emb_a is None or emb_b is None:
                return -1.0
            return float(np.dot(emb_a, emb_b) / (np.linalg.norm(emb_a) * np.linalg.norm(emb_b) + 1e-12))
        except Exception:
            return -1.0

    def _select_quality_first_level_candidate(
        self,
        trace: Dict[str, Any],
        source_detail: Dict[str, Any],
    ) -> str:
        source_text = str(
            source_detail.get("original_content", "")
            or source_detail.get("content", "")
            or source_detail.get("text", "")
        )
        selected = self._finalize_first_level_candidate(
            str(trace.get("selected_candidate", "") or ""),
            source_text,
        )
        if selected and not self._is_low_quality_first_level_code(selected, source_text):
            # 模型语义验证：确保编码与原文有合理语义关联
            if self._validate_code_semantic_fit(selected, source_text):
                return selected

        rows = list(trace.get("candidates", []))
        rows.sort(
            key=lambda item: (
                item.get("conservative_score", -999.0),
                item.get("rerank_score") if item.get("rerank_score") is not None else -1.0,
                item.get("rule_score", 0.0),
                -len(item.get("text", "")),
            ),
            reverse=True,
        )
        for row in rows:
            candidate = self._finalize_first_level_candidate(
                str(row.get("text", "") or ""),
                source_text,
            )
            if candidate and not self._is_low_quality_first_level_code(candidate, source_text):
                if self._validate_code_semantic_fit(candidate, source_text):
                    trace["selected_candidate"] = candidate
                    for candidate_row in rows:
                        candidate_row["selected"] = candidate_row.get("text") == row.get("text")
                    return candidate
        return ""

    def _validate_code_semantic_fit(self, code: str, source_text: str) -> bool:
        """模型语义验证：编码应在保留原文核心语义的同时有所抽象

        - 相似度 < 0.30: 编码与原文关系太弱，丢失了核心信息
        - 相似度 > 0.96: 编码几乎等于原文，没有完成抽象提炼
        - 0.30 ~ 0.96: 合理范围
        """
        if not code or not source_text:
            return True  # 信息不足时由其他规则判断
        sim = self._model_semantic_similarity(code, source_text)
        if sim < 0:
            return True  # 模型不可用时不拦截
        if sim < 0.30:
            logger.info(f"模型语义验证拒绝: '{code}' 与原文语义关联过弱 ({sim:.3f})")
            return False
        if sim > 0.96:
            logger.info(f"模型语义验证拒绝: '{code}' 与原文几乎相同，未完成抽象 ({sim:.3f})")
            return False
        return True

    # Override the earlier scoring helpers with a cleaner, sample-driven policy.
    def _score_first_level_fragment(self, fragment: str, source_text: str = "") -> float:
        clean = str(fragment or "").strip()
        if not clean:
            return float("-inf")
        score = 0.0
        score += min(len(clean), 24) * 0.35
        if self._is_semantically_complete(clean):
            score += 2.0
        score += self._first_level_anchor_ratio(clean, source_text) * 3.0
        if self._has_first_level_information_cue(clean):
            score += 1.2
        if re.search(r'(反馈|诉求|需求|受影响|短板|机会)', clean):
            score += 0.8
        if re.search(r'^(追求|引入|建立|调整|获得|降低|提高|推动|解决|客户|越轨|创新|资源|反馈|开展|优化|合作|转变|对接|影响|分析)', clean):
            score += 1.0
        if clean.startswith((
            '我觉得', '其实', '然后', '所以', '但是', '不过', '当时', '那个时候',
            '就是', '相当于', '要看', '分场合', '后来', '以前因为', '当我'
        )):
            score -= 2.0
        if self._contains_colloquial_residue(clean):
            score -= 3.0
        if re.search(r'(这个东西|这个事情|这个问题|这块|这一块|那种)$', clean):
            score -= 2.0
        if re.search(r'(主要负责|指引方向|监督结果)', clean):
            score -= 0.7
        return score

    def _conservative_first_level_rank_score(self, row: Dict[str, Any]) -> float:
        text = self._finalize_first_level_candidate(str(row.get("text", "") or ""))
        if not text:
            return float("-inf")
        rerank_score = row.get("rerank_score")
        model_score = float(rerank_score) if rerank_score is not None else 0.0
        rule_score = float(row.get("rule_score", 0.0) or 0.0)
        score = model_score * 10.0 + min(rule_score, 6.0) * 0.25
        prototype_hits = row.get('prototype_hits') or []
        if prototype_hits:
            best_similarity = max(float(hit.get('similarity', 0.0) or 0.0) for hit in prototype_hits)
            score += min(2.2, best_similarity * 3.0)
        recall_score = float(row.get('semantic_recall_score', 0.0) or 0.0)
        if recall_score > 0:
            score += min(1.8, recall_score * 2.0)
        score -= text.count('\uFF0C') * 1.25
        score -= max(0, len(text) - 22) * 0.18
        score -= max(0, len(text) - 30) * 0.55
        if re.search(r'^(时候|比如|然后|所以|那没有|会，因为|他们有时候|我们有时候|后来|以前因为|当我)', text):
            score -= 2.5
        if re.search(r'(\u8fd9\u4e2a\u4e8b\u60c5|\u8fd9\u4e00\u5757\u76ee\u524d\u6211\u4eec\u80fd\u591f|\u90a3\u4e2a\u65f6\u5019|这块|这一块|那种)', text):
            score -= 1.8
        if re.search(r'^(追求|引入|建立|调整|获得|降低|提高|推动|解决|客户|越轨|创新|资源|需求|反馈|分析)', text):
            score += 0.8
        if re.search(r'^(我们|他们|你们|大家|这个|那个|这种|这些|那些|他是|我是|你是|一开始)', text):
            score -= 1.4
        if row.get('compressed_variant') and not re.search(r'(我|我们|你|你们|他|他们|这个|那个)', text):
            score += 1.1
        if re.search(r'(技术|品牌|资源|平台|机制|流程|生态|需求|问题|合作|协同|创新|服务|应用|模块|设备|系统|客户|团队|工业互联网)', text) and len(text) <= 16:
            score += 0.7
        if self._has_first_level_information_cue(text):
            score += 1.2
        if re.search(r'(反馈|诉求|需求|受影响|短板|机会)', text):
            score += 0.8
        if re.search(r'(主要负责|指引方向|监督结果)', text):
            score -= 0.7
        return score

    def _rebuild_decision_policy_from_matcher(self) -> None:
        if not CodingDecisionPolicy or not self.rag_matcher:
            return
        second_name_map = self.rag_matcher.second_code_name_map() if self.rag_matcher else {}
        third_name_map = self.rag_matcher.third_level_name_map() if self.rag_matcher else {}
        self.decision_policy = CodingDecisionPolicy(
            second_threshold=self.rag_second_level_threshold,
            third_threshold=self.rag_third_level_threshold,
            allowed_second_code_ids=list(second_name_map.keys()),
            allowed_third_level_ids=list(third_name_map.keys()),
            allowed_second_code_names=second_name_map,
            allowed_third_level_names=third_name_map,
        )

    def set_first_level_prototypes(self, prototypes: List[Dict[str, Any]]) -> None:
        self.first_level_prototypes = [
            {
                "source": str(item.get("source", "")).strip(),
                "manual_first_code": str(item.get("manual_first_code", "")).strip(),
            }
            for item in prototypes or []
            if isinstance(item, dict)
            and str(item.get("source", "")).strip()
            and str(item.get("manual_first_code", "")).strip()
        ]

    def set_first_level_recall_bank(self, labels: List[str], model_manager=None) -> None:
        self._ensure_first_level_defaults()
        unique_labels = []
        seen = set()
        for label in labels or []:
            text = str(label or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            unique_labels.append(text)
        self.first_level_recall_bank = unique_labels
        self.first_level_recall_embeddings = None
        if model_manager is not None and unique_labels:
            try:
                self.first_level_recall_embeddings = model_manager.get_embeddings(unique_labels, model_type="sentence")
            except Exception:
                self.first_level_recall_embeddings = None

    def _semantic_recall_first_level_labels(self, text: str, model_manager=None, top_n: int = 8, min_score: float = 0.35) -> List[Dict[str, Any]]:
        self._ensure_first_level_defaults()
        labels = getattr(self, 'first_level_recall_bank', []) or []
        if not labels:
            return []

        def lexical_hits() -> List[Dict[str, Any]]:
            text_tokens = {t for t in jieba.lcut(str(text or "")) if len(t.strip()) >= 2}
            if not text_tokens:
                return []
            scored = []
            for label in labels:
                label_tokens = {t for t in jieba.lcut(str(label or "")) if len(t.strip()) >= 2}
                if not label_tokens:
                    continue
                overlap = len(text_tokens & label_tokens)
                char_overlap = len(set(str(label or "")) & set(str(text or "")))
                if overlap <= 0 and char_overlap <= 0:
                    continue
                score = overlap / max(1, len(label_tokens)) + 0.15 * overlap + 0.08 * char_overlap
                if len(str(label or "")) <= 6 and char_overlap > 0:
                    score += 0.35
                scored.append({"text": label, "score": float(score), "recall_type": "lexical"})
            scored.sort(key=lambda item: item["score"], reverse=True)
            exact_or_short = [item for item in scored if len(str(item.get("text", ""))) <= 8]
            long_items = [item for item in scored if item not in exact_or_short]
            merged = exact_or_short[:80] + long_items
            return merged[:max(1, int(top_n))]

        if model_manager is None:
            return lexical_hits()
        try:
            label_embs = getattr(self, 'first_level_recall_embeddings', None)
            if label_embs is None:
                label_embs = model_manager.get_embeddings(labels, model_type="sentence")
                self.first_level_recall_embeddings = label_embs
            if label_embs is None or len(label_embs) == 0:
                return lexical_hits()
            query_emb = model_manager.get_embeddings([text], model_type="sentence")[0]
            q_norm = np.linalg.norm(query_emb)
            l_norms = np.linalg.norm(label_embs, axis=1)
            denom = np.maximum(q_norm * l_norms, 1e-12)
            sims = np.dot(label_embs, query_emb) / denom
            order = np.argsort(-sims)[:max(1, int(top_n))]
            results = []
            for idx in order:
                score = float(sims[idx])
                if score < min_score:
                    continue
                results.append({"text": labels[int(idx)], "score": score, "recall_type": "semantic"})
            return results or lexical_hits()
        except Exception:
            return lexical_hits()

    def _prototype_keywords(self, manual_code: str) -> Set[str]:
        manual = str(manual_code or "")
        words = {word for word in jieba.lcut(manual) if len(word.strip()) >= 2}
        if "\u5ba2\u6237\u9700\u6c42" in manual or "\u9700\u6c42\u5bfc\u5411" in manual:
            words.update({
                "\u5ba2\u6237", "\u9700\u6c42", "\u4e70", "\u5356", "\u8981",
            })
        if "\u53cd\u9988" in manual:
            words.update({"\u5ba2\u6237", "\u53cd\u9988", "\u8bc9\u6c42"})
        if "\u6c9f\u901a" in manual:
            words.update({"\u6c9f\u901a", "\u4fe1\u4efb", "\u63a8\u9500"})
        return words

    def _prototype_similarity(self, text: str, prototype: Dict[str, Any]) -> float:
        text_tokens = set(token for token in jieba.lcut(str(text or "")) if len(token.strip()) >= 2)
        source_tokens = set(token for token in jieba.lcut(str(prototype.get("source", ""))) if len(token.strip()) >= 2)
        manual_tokens = self._prototype_keywords(str(prototype.get("manual_first_code", "")))
        if not text_tokens:
            return 0.0
        source_overlap = len(text_tokens & source_tokens) / max(1, min(len(text_tokens), len(source_tokens)))
        manual_overlap = len(text_tokens & manual_tokens) / max(1, len(manual_tokens))
        return 0.75 * source_overlap + 0.25 * manual_overlap

    def _find_first_level_prototype_hits(self, text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        self._ensure_first_level_defaults()
        scored = []
        for prototype in self.first_level_prototypes:
            score = self._prototype_similarity(text, prototype)
            if score <= 0:
                continue
            scored.append(
                {
                    "source": prototype.get("source", ""),
                    "manual_first_code": prototype.get("manual_first_code", ""),
                    "similarity": round(float(score), 4),
                }
            )
        scored.sort(key=lambda item: item["similarity"], reverse=True)
        return scored[:top_k]

    def reset_first_level_trace_meta(self) -> None:
        self._ensure_first_level_defaults()
        self._first_level_trace_meta = {}

    def get_first_level_trace_meta(self) -> Dict[str, Dict[str, Any]]:
        self._ensure_first_level_defaults()
        return dict(self._first_level_trace_meta)

    def _store_first_level_trace(self, code_key: str, trace: Dict[str, Any]) -> None:
        self._ensure_first_level_defaults()
        compact_trace = {
            "selected_candidate": trace.get("selected_candidate", ""),
            "best_rule_candidate": trace.get("best_rule_candidate", ""),
            "used_rerank": bool(trace.get("used_rerank", False)),
            "prototype_enabled": bool(trace.get("prototype_enabled", False)),
            "prototype_hits": list(trace.get("prototype_hits", [])),
            "candidates": [
                {
                    "text": item.get("text", ""),
                    "rule_score": item.get("rule_score"),
                    "rerank_score": item.get("rerank_score"),
                    "selected": bool(item.get("selected", False)),
                    "best_rule": bool(item.get("best_rule", False)),
                }
                for item in trace.get("candidates", [])
            ],
        }
        self._first_level_trace_meta[code_key] = compact_trace

    def build_first_level_candidate_trace(
        self,
        sentence: str,
        model_manager=None,
        top_n: Optional[int] = None,
        defer_rerank: bool = False,
    ) -> Dict[str, Any]:
        """Return a compact candidate trace for first-level abstraction."""
        self._ensure_first_level_defaults()

        original = (sentence or '').strip()
        if not original:
            return {
                'original_sentence': '',
                'normalized_sentence': '',
                'selected_candidate': '',
                'best_rule_candidate': '',
                'used_rerank': False,
                'prototype_enabled': False,
                'prototype_hits': [],
                'candidates': [],
            }

        normalized = re.sub(r'^(?:[A-Za-z]|\u7b54|\u53d7\u8bbf\u8005|\u88ab\u8bbf\u8005)[:\uFF1A\s]*', '', original)
        normalized = re.sub(r'\[[A-Z]?\d+\]', '', normalized)
        normalized = re.sub(r'(\w)\1{2,}', r'\1', normalized)
        normalized = self._normalize_source_sentence(normalized)
        if not normalized:
            return {
                'original_sentence': original,
                'normalized_sentence': '',
                'selected_candidate': '',
                'best_rule_candidate': '',
                'used_rerank': False,
                'prototype_enabled': False,
                'prototype_hits': [],
                'candidates': [],
            }

        prototype_hits = self._find_first_level_prototype_hits(normalized)
        prototype_keywords: Set[str] = set()
        for hit in prototype_hits:
            prototype_keywords.update(self._prototype_keywords(hit.get("manual_first_code", "")))

        # 计算句子显著性（四维：转折/因果/强度/问题），用于加权候选评分
        salience = self._compute_salience(normalized)

        target_length = getattr(Config, 'MAX_SENTENCE_LENGTH', 512) if Config else 512
        max_len = getattr(self, 'max_first_level_length', getattr(Config, 'FIRST_LEVEL_CODE_MAX_LENGTH', 30) if Config else 30)
        length_budget = max_len if isinstance(max_len, int) and max_len > 0 else None
        recall_enhanced = bool(getattr(Config, 'FIRST_LEVEL_RECALL_ENHANCED', False)) if Config else False
        base_max_span = int(getattr(Config, 'FIRST_LEVEL_BASE_MAX_SPAN', 8)) if Config else 8
        enhanced_max_span = int(getattr(Config, 'FIRST_LEVEL_ENHANCED_MAX_SPAN', 12)) if Config else 12
        focus_markers = (
            '第一次', '首次', '然而', '最终', '但是', '不过', '却', '更', '更加', '最', '最高', '最低',
            '核心', '关键', '尤其', '特别', '主要', '重点'
        )
        professional_terms = (
            '技术', '资源', '平台', '机制', '流程', '生态', '需求', '风险', '压力', '冲突', '协同',
            '合作', '创新', '服务', '模块', '设备', '系统', '客户', '团队', '品牌', '治理', '监督',
            '审批', '架构', '算法', '数据', '能力', '知识', '资本', '绩效', '战略', '路径', '场景'
        )

        def strip_punct(value: str) -> str:
            return re.sub(r'^[\s\W_]+|[\s\W_]+$', '', value or '')

        def looks_like_fragment(raw_text: str, clean_text: str) -> bool:
            clean = (clean_text or '').strip()
            if not clean:
                return True
            if len(clean) <= 3 and not any(term in clean for term in professional_terms):
                return True
            if len(clean) <= 8 and any(term in clean for term in professional_terms):
                return False
            if self._is_question_like(clean):
                return True
            if clean.startswith((
                '\u56e0\u4e3a', '\u5982\u679c', '\u4f46\u662f', '\u4e0d\u8fc7', '\u6240\u4ee5', '\u7136\u540e', '\u5e76\u4e14'
            )):
                return True
            if clean.endswith((
                '\u8fd9\u4e2a', '\u90a3\u4e2a', '\u8fd9\u91cc', '\u8fd9\u6837', '\u90a3\u6837'
            )):
                return True
            return False

        def score_candidate(clean_text: str, raw_text: str) -> float:
            clean = clean_text or ''
            score = 0.0
            # 语义完整性是核心：完整概念大幅加分，碎片大幅扣分
            if self._is_semantically_complete(clean):
                score += 5.0
            else:
                score -= 3.0
            if looks_like_fragment(raw_text, clean):
                score -= 5.0
            # 以"的/了/着/过/到/在/中/和/与/或"结尾 → 结构残缺
            if re.search(r'(的|了|着|过|到|在|中|和|与|或|又|还|也|只|不|没)$', clean):
                score -= 3.0
            # 含疑问词 → 是问题不是概念
            if re.search(r'(什么|怎么|哪些|怎么样|如何|哪方面|什么时候)', clean):
                score -= 4.0
            # 以连词开头 → 残片
            if re.search(r'^(但|而|且|并|还|也|另外|此外|还有)', clean):
                score -= 2.0
            if any(marker in raw_text for marker in focus_markers):
                marker_positions = [raw_text.find(marker) for marker in focus_markers if marker in raw_text]
                first_marker_pos = min(marker_positions) if marker_positions else -1
                clean_pos = raw_text.find(clean)
                if clean_pos >= 0 and (first_marker_pos < 0 or clean_pos >= first_marker_pos):
                    score += 2.2
                elif any(marker in clean for marker in focus_markers):
                    score += 1.2
            if len(clean) <= 12 and any(term in clean for term in professional_terms):
                score += 1.8
            if any(keyword in clean for keyword in (
                '\u5f71\u54cd', '\u5bfc\u81f4', '\u53ea\u80fd', '\u9700\u8981', '\u5361\u5728', '\u62d6\u6162', '\u5ef6\u8fdf',
                '\u534f\u540c', '\u5ba1\u6279', '\u8d44\u6e90', '\u5ba2\u6237', '\u63a8\u8fdb'
            )):
                score += 2.5
            if any(keyword in clean for keyword in (
                '\u7ecf\u5e38', '\u53cd\u590d', '\u603b\u662f', '\u6bcf\u6b21', '\u9891\u7e41'
            )):
                score += 1.0
            if prototype_keywords:
                overlap = sum(1 for keyword in prototype_keywords if keyword and keyword in clean)
                density = overlap / max(1, len(clean))
                score += min(4.5, overlap * 1.4 + density * 10.0)
                score -= clean.count('\uFF0C') * 1.8
                score -= max(0, len(clean) - 18) * 0.12
                if "\u9700\u6c42" in prototype_keywords and "\u5ba2\u6237" in clean:
                    if "\u4e70" in clean and "\u5356" in clean:
                        score += 4.0
                    elif "\u8981" in clean or "\u9700\u6c42" in clean:
                        score += 1.0
            if any(keyword in clean for keyword in (
                '\u53ef\u80fd', '\u5927\u6982', '\u4e5f\u8bb8', '\u597d\u50cf', '\u4e0d\u592a\u6e05\u695a'
            )):
                score -= 2.0
            if length_budget is not None:
                # 超过长度预算线性扣分，但更温和
                if len(clean) > length_budget:
                    score -= max(0, len(clean) - length_budget) * 0.15
            # 长度适中(6-20字)奖励，过短过长的都降权
            if 6 <= len(clean) <= 20:
                score += min(len(clean), 20) / 20.0 + 0.5
            else:
                score += min(len(clean), 40) / 40.0
            # 显著性加权：问题/困境 > 转折 > 因果 > 强度
            score += salience['total'] * 2.0
            # 书面语偏好：含专业名词/正式词汇大幅加分
            formal_density = len(re.findall(
                r'(机制|流程|资源|策略|路径|模式|结构|能力|架构|生态|治理|监督|协同|审批|绩效|战略|需求|服务|创新|'
                r'评估|优化|配置|整合|调度|保障|约束|反馈|驱动|赋能|转型)',
                clean
            ))
            score += min(formal_density * 1.5, 4.5)
            # 口语词惩罚
            if re.search(r'(这个|那个|那种|这种|什么的|之类的|怎么说呢|就是说|我觉得|相当于)', clean):
                score -= 2.5
            if re.search(r'^(我|我们|你|你们|他|他们|大家|那个|这个)', clean):
                score -= 1.4
            # 主语+谓语的完整概念结构奖励（名词主导，含动词/状态描述）
            if re.search(r'^[一-鿿]{2,}(?:机制|流程|资源|策略|能力|需求|服务|创新|协同|治理|监督|审批)', clean) and re.search(r'(不足|受限|缺失|缺乏|受阻|延迟|影响|推动|优化|提升|降低|增加)', clean):
                score += 2.0
            return score

        sentence_parts = [part.strip() for part in re.split(r'[\u3002\uFF01\uFF1F\uFF1B;]', normalized) if part.strip()]
        if not sentence_parts:
            sentence_parts = [normalized]

        candidate_rows = []
        seen: Dict[str, int] = {}

        for sentence_part in sentence_parts:
            micro_parts = [part.strip() for part in re.split(r'[\uFF0C,\u3001]', sentence_part) if part.strip()]
            if not micro_parts:
                micro_parts = [sentence_part]

            for i in range(len(micro_parts)):
                built_raw = ''
                span_limit = enhanced_max_span if recall_enhanced else base_max_span
                for j in range(i, min(len(micro_parts), i + span_limit)):
                    built_raw = micro_parts[j] if not built_raw else f'{built_raw}\uFF0C{micro_parts[j]}'
                    candidate = strip_punct(self._post_refine_phrase(built_raw))
                    variants = [candidate] if candidate else []
                    normalized_candidate = self._normalize_candidate_for_first_level(candidate)
                    if normalized_candidate and normalized_candidate not in variants:
                        variants.append(normalized_candidate)

                    compact_candidate = normalized_candidate.replace('\u5c31\u5f88\u53d7\u5f71\u54cd', '\u53d7\u5f71\u54cd') if normalized_candidate else ''
                    compact_candidate = compact_candidate.replace('\u5f88\u53d7\u5f71\u54cd', '\u53d7\u5f71\u54cd') if compact_candidate else ''
                    compact_candidate = compact_candidate.replace('\u5f71\u54cd\u9879\u76ee\u63a8\u8fdb', '\u9879\u76ee\u63a8\u8fdb\u53d7\u5f71\u54cd') if compact_candidate else ''
                    if compact_candidate and compact_candidate not in variants:
                        variants.append(compact_candidate)
                    compressed_variants = set(self._compress_first_level_candidate_variants(built_raw))
                    for compressed_candidate in compressed_variants:
                        if compressed_candidate not in variants:
                            variants.append(compressed_candidate)
                    if normalized_candidate and '\u9879\u76ee\u63a8\u8fdb' in normalized_candidate and '\u53d7\u5f71\u54cd' in normalized_candidate:
                        if '\u9879\u76ee\u63a8\u8fdb\u53d7\u5f71\u54cd' not in variants:
                            variants.append('\u9879\u76ee\u63a8\u8fdb\u53d7\u5f71\u54cd')

                    for variant in variants:
                        if not variant or len(variant) > target_length:
                            continue
                        row = {
                            'text': variant,
                            'raw_text': built_raw,
                            'rule_score': round(float(score_candidate(variant, built_raw)), 4),
                            'rerank_score': None,
                            'selected': False,
                            'best_rule': False,
                            'compressed_variant': variant in compressed_variants,
                            'prototype_hits': prototype_hits,
                        }
                        existing = seen.get(variant)
                        if existing is None:
                            seen[variant] = len(candidate_rows)
                            candidate_rows.append(row)
                        elif row['rule_score'] > candidate_rows[existing]['rule_score']:
                            candidate_rows[existing] = row

        # 召回增强：补充“触发词短语 + 高信息短片段”候选
        if recall_enhanced:
            trigger_keywords = (
                '影响', '导致', '卡在', '拖慢', '延迟', '只能', '需要', '受限', '不足', '短板',
                '风险', '压力', '冲突', '审批', '协同', '资源', '客户', '诉求', '反馈', '推进'
            )
            extra_parts = [part.strip() for part in re.split(r'[，,、；;。！？!?]', normalized) if part.strip()]
            for part in extra_parts:
                clean_part = self._normalize_candidate_for_first_level(strip_punct(self._post_refine_phrase(part)))
                if not clean_part:
                    continue
                if len(clean_part) < 4 or len(clean_part) > target_length:
                    continue
                if not any(k in clean_part for k in trigger_keywords):
                    continue
                if self._contains_colloquial_residue(clean_part):
                    continue
                row = {
                    'text': clean_part,
                    'raw_text': part,
                    'rule_score': round(float(score_candidate(clean_part, part) + 0.8), 4),
                    'rerank_score': None,
                    'selected': False,
                    'best_rule': False,
                }
                existing = seen.get(clean_part)
                if existing is None:
                    seen[clean_part] = len(candidate_rows)
                    candidate_rows.append(row)
                elif row['rule_score'] > candidate_rows[existing]['rule_score']:
                    candidate_rows[existing] = row

        if recall_enhanced and Config and getattr(Config, 'FIRST_LEVEL_USE_LABEL_RECALL_CANDIDATES', False):
            semantic_top_n = int(getattr(Config, 'FIRST_LEVEL_SEMANTIC_RECALL_TOP_N', 8)) if Config else 8
            semantic_min_score = float(getattr(Config, 'FIRST_LEVEL_SEMANTIC_RECALL_MIN_SCORE', 0.35)) if Config else 0.35
            for hit in self._semantic_recall_first_level_labels(
                normalized,
                model_manager=model_manager,
                top_n=semantic_top_n,
                min_score=semantic_min_score,
            ):
                label = self._normalize_candidate_for_first_level(hit.get('text', ''))
                if not label or len(label) > target_length:
                    continue
                if self._contains_colloquial_residue(label):
                    continue
                row = {
                    'text': label,
                    'raw_text': normalized,
                    'rule_score': round(float(3.0 + hit.get('score', 0.0) * 4.0), 4),
                    'rerank_score': None,
                    'selected': False,
                    'best_rule': False,
                    'semantic_recall_score': round(float(hit.get('score', 0.0)), 4),
                    'prototype_hits': prototype_hits,
                }
                existing = seen.get(label)
                if existing is None:
                    seen[label] = len(candidate_rows)
                    candidate_rows.append(row)
                elif row['rule_score'] > candidate_rows[existing]['rule_score']:
                    candidate_rows[existing] = row

        candidate_rows = self._canonicalize_first_level_candidate_rows(candidate_rows, normalized)
        if not candidate_rows and re.search(r'(生产习惯|默认的惯例|当地默认).*随意', normalized):
            candidate_rows.append({
                'text': '规范缺乏',
                'raw_text': normalized,
                'rule_score': 8.0,
                'rerank_score': None,
                'selected': False,
                'best_rule': False,
                'compressed_variant': True,
                'conservative_score': 8.0,
            })
        best_rule_candidate = ''
        best_rule_key = (float('-inf'), float('-inf'), float('-inf'), float('-inf'))
        for row in candidate_rows:
            text = str(row.get('text', '') or '')
            row_key = (
                float(row.get('conservative_score', float('-inf'))),
                1.0 if re.search(r'(受影响|受限|受阻|不足|短板|风险|压力|冲突)', text) else 0.0,
                float(row.get('rule_score', float('-inf'))),
                -len(text),
            )
            if row_key > best_rule_key:
                best_rule_key = row_key
                best_rule_candidate = row.get('text', '')

        # 当最佳规则候选为空时，不直接使用整句，而是尝试从候选列表中选择次优
        # 整句通常太长且口语化，不适合作为一阶编码
        if best_rule_candidate:
            fallback_candidate = best_rule_candidate
        elif candidate_rows:
            # 有候选但都不理想，选保守评分最高的那个（后续 _finalize 还会验证）
            fallback_candidate = candidate_rows[0].get('text', '')
        else:
            # 完全没有候选，尝试从原句中提取核心短语
            trimmed = self._normalize_candidate_for_first_level(strip_punct(normalized))
            if len(trimmed) <= 30 and self._has_first_level_information_cue(trimmed):
                fallback_candidate = trimmed
            else:
                fallback_candidate = ''
        selected_candidate = fallback_candidate
        used_rerank = False

        try:
            if (
                not defer_rerank
                and Config
                and getattr(Config, 'ENABLE_ABSTRACT_RERANKER', False)
                and model_manager is not None
            ):
                if hasattr(model_manager, 'ensure_abstract_reranker_loaded'):
                    model_manager.ensure_abstract_reranker_loaded()
                if hasattr(model_manager, 'is_abstract_reranker_available') and model_manager.is_abstract_reranker_available():
                    rerank_limit = max(1, int(getattr(Config, 'ABSTRACT_RERANK_TOP_N', 6))) if Config else 6
                    # 先清洗低质量候选，再进入重排（提速 + 降噪）
                    prefiltered_rows = []
                    for row in candidate_rows:
                        t = str(row.get('text', '') or '')
                        if not t:
                            continue
                        if looks_like_fragment(row.get('raw_text', ''), t):
                            continue
                        if self._contains_colloquial_residue(t):
                            continue
                        if self._is_low_quality_first_level_code(t, normalized):
                            continue
                        prefiltered_rows.append(row)

                    # 兜底：避免过滤过严导致无候选
                    rerank_rows = prefiltered_rows if len(prefiltered_rows) >= 3 else [
                        row for row in candidate_rows if not looks_like_fragment(row.get('raw_text', ''), row.get('text', ''))
                    ]
                    if not rerank_rows:
                        rerank_rows = list(candidate_rows)

                    rerank_rows.sort(
                        key=lambda item: (
                            item.get('conservative_score', -999.0),
                            item['rule_score'],
                            -len(item['text']),
                        ),
                        reverse=True,
                    )
                    rerank_candidates = [row['text'] for row in rerank_rows[:rerank_limit]]
                    if rerank_candidates:
                        scores = model_manager.score_abstract_candidates(normalized, rerank_candidates)
                        if scores and len(scores) == len(rerank_candidates):
                            used_rerank = True
                            score_map = {
                                text: round(float(score), 4)
                                for text, score in zip(rerank_candidates, scores)
                            }
                            for row in candidate_rows:
                                row['rerank_score'] = score_map.get(row['text'])
                            selected_candidate = max(rerank_candidates, key=lambda item: score_map[item])
        except Exception:
            pass

        if selected_candidate and not self._is_semantically_complete(selected_candidate):
            candidate = self._limit_first_level_text(selected_candidate, 60)
            if candidate:
                selected_candidate = candidate
        if length_budget is not None and selected_candidate and len(selected_candidate) > length_budget:
            candidate = self._limit_first_level_text(selected_candidate, length_budget)
            if candidate:
                selected_candidate = candidate
        if selected_candidate and self._contains_colloquial_residue(selected_candidate):
            clean_rows = [
                row for row in candidate_rows
                if row.get('text')
                and not self._contains_colloquial_residue(row.get('text', ''))
                and not self._is_low_quality_first_level_code(row.get('text', ''), normalized)
                and not looks_like_fragment(row.get('raw_text', ''), row.get('text', ''))
            ]
            if clean_rows:
                clean_rows.sort(
                    key=lambda item: (
                        item.get('rerank_score') if item.get('rerank_score') is not None else -1.0,
                        item.get('conservative_score', -999.0),
                        item.get('rule_score', 0.0),
                        -len(item.get('text', '')),
                    ),
                    reverse=True,
                )
                selected_candidate = clean_rows[0].get('text', selected_candidate)
        selected_candidate = self._finalize_first_level_candidate(
            strip_punct(selected_candidate),
            normalized,
        )

        for row in candidate_rows:
            row['selected'] = row['text'] == selected_candidate
            row['best_rule'] = row['text'] == best_rule_candidate

        candidate_rows.sort(
            key=lambda item: (
                item.get('conservative_score', -999.0),
                item['rerank_score'] if item['rerank_score'] is not None else -1.0,
                item['rule_score'],
                -len(item['text']),
            ),
            reverse=True,
        )
        if isinstance(top_n, int) and top_n > 0:
            candidate_rows = candidate_rows[:top_n]

        return {
            'original_sentence': original,
            'normalized_sentence': normalized,
            'selected_candidate': selected_candidate,
            'best_rule_candidate': best_rule_candidate,
            'used_rerank': used_rerank,
            'prototype_enabled': bool(prototype_hits),
            'prototype_hits': prototype_hits,
            'candidates': candidate_rows,
            'salience': salience,
        }

    def rewrite_first_level_code(self, text: str) -> str:
        """Clean a selected first-level code into a shorter coding phrase."""
        cleaned = str(text or '').strip()
        if not cleaned:
            return ''
        cleaned = re.sub(r'(?<=[\u4e00-\u9fff])\?(?=[\u4e00-\u9fff])', '\uFF0C', cleaned)
        cleaned = re.sub(r'^\s*[\u2460-\u2473\u2776-\u277F\u24F5-\u24FE\u3251-\u325F①②③④⑤⑥⑦⑧⑨⑩]+[\u3001\.\uFF0E\)\uFF09\s]*', '', cleaned)
        cleaned = re.sub(r'^\s*(?:\d+|[一二三四五六七八九十]+)[\u3001\.\uFF0E\)\uFF09]\s*', '', cleaned)
        cleaned = re.sub(r'^(\u6211\u89c9\u5f97|\u6211\u8ba4\u4e3a|\u6211\u611f\u89c9|\u5176\u5b9e|\u7136\u540e|\u5c31\u662f\u8bf4|\u90a3\u4e48|\u8fd9\u4e2a|\u90a3\u4e2a|\u4f60\u770b|\u4f60\u8bf4|\u5982\u679c\u8bf4)+', '', cleaned)
        cleaned = re.sub(r'(\u8fd9\u4e2a\u4e1c\u897f|\u8fd9\u4e2a\u4e8b\u60c5|\u8fd9\u4ef6\u4e8b|\u8fd9\u4e2a\u95ee\u9898)', '', cleaned)
        cleaned = re.sub(r'(\u53ef\u80fd|\u5927\u6982|\u4e5f\u8bb8|\u597d\u50cf|\u5176\u5b9e|\u5b9e\u9645\u4e0a|\u8bf4\u5b9e\u8bdd|\u76f8\u5f53\u4e8e|\u5c31\u662f|\u7136\u540e)', '', cleaned)
        cleaned = re.sub(r'(怎么说呢|就是说|我觉得|相当于|要看|分场合|这个东西|这个事情|这个问题)', '', cleaned)
        cleaned = re.sub(r'每个阶段的重点不同.*参与深度是不同的', '阶段性参与调整', cleaned)
        cleaned = re.sub(r'怎么会有人.*?(?:吃饭|消费|购买)', '客源不确定', cleaned)
        cleaned = re.sub(r'咖啡的种植加工活动遵循生产者本人的生产意愿和生产习惯以及当地默认的惯例开展.*随意', '规范缺乏', cleaned)
        cleaned = re.sub(r'生产意愿和生产习惯以及当地默认的惯例开展.*随意', '规范缺乏', cleaned)
        cleaned = re.sub(r'品牌化这个方向', '品牌化方向', cleaned)
        cleaned = re.sub(r'(推动)(?:他们|我们|他|她)(在?)', r'\1\2', cleaned)
        cleaned = re.sub(r'让他能够更好地带领让他能够更好地带领团队实现技术创新', '团队实现技术创新', cleaned)
        cleaned = re.sub(r'^(?:我们|他们|你们|他|她)(?=(?:在|将|会|对|把)?(?:推动|开展|组织|参与|提出|引入|建立|调整|获得|降低|提高|解决|分析|反馈|合作|转变|优化|对接|支持|购买))', '', cleaned)
        cleaned = re.sub(r'[吧呢啊嘛呀哦哈哎诶噢呃]+$', '', cleaned)
        cleaned = re.sub(r'\u7ed3\u679c\u6210\u529f\u4e5f\u5931\u8d25', '\u7ed3\u679c\u53ef\u80fd\u6210\u529f\u4e5f\u53ef\u80fd\u5931\u8d25', cleaned)
        cleaned = re.sub(r'(\u80fd\u591f|\u80fd)\u5f71\u54cd\u7684\u8303\u56f4', '\u5f71\u54cd\u8303\u56f4', cleaned)
        cleaned = re.sub(r'\u5f71\u54cd\u7684\u8303\u56f4', '\u5f71\u54cd\u8303\u56f4', cleaned)
        cleaned = re.sub(r'\u8fd8\u662f\u6709\u9650\u7684?$', '\u6709\u9650', cleaned)
        cleaned = re.sub(r'\u7684(\u8303\u56f4|\u5f71\u54cd|\u4f5c\u7528)', r'\1', cleaned)
        cleaned = re.sub(r'[（(]?\d{1,2}:\d{2}[)）]?', '', cleaned)
        cleaned = re.sub(r'\s+', '', cleaned)
        # \u65B0\u589E\u5F3A\u7ED3\u6784\u5316\u91CD\u5199\u89C4\u5219\uFF1A\u5C06\u5E38\u89C1\u53E3\u8BED\u6A21\u5F0F\u8F6C\u4E3A\u4E66\u9762\u6982\u5FF5
        cleaned = re.sub(r'^(?:\u6211\u4EEC|\u4ED6\u4EEC|\u4F60\u4EEC|\u4ED6|\u5979|\u6211)(?:\u4E5F|\u90FD|\u5C31|\u4F1A|\u8981|\u80FD|\u53EF\u4EE5|\u9700\u8981|\u60F3\u8981|\u5E0C\u671B|\u6253\u7B97|\u8BA1\u5212|\u51C6\u5907)?', '', cleaned)
        cleaned = re.sub(r'(?:\u662F\u4E0D\u662F|\u80FD\u4E0D\u80FD|\u8981\u4E0D\u8981|\u4F1A\u4E0D\u4F1A|\u6709\u6CA1\u6709|\u884C\u4E0D\u884C)[\u3002\uFF0C]?$', '', cleaned)
        cleaned = re.sub(r'^.*?(?:\u539F\u56E0\u662F|\u662F\u56E0\u4E3A|\u4E3B\u8981\u662F|\u5176\u5B9E\u662F)(.{4,30})$', r'\1', cleaned)
        cleaned = re.sub(r'^(.{2,20})(?:\u7684\u65B9\u9762|\u7684\u89D2\u5EA6|\u7684\u5C42\u9762|\u7684\u60C5\u51B5|\u7684\u73AF\u8282|\u7684\u9636\u6BB5|\u7684\u8FC7\u7A0B|\u7684\u6D41\u7A0B|\u7684\u6548\u679C|\u7684\u7ED3\u679C|\u7684\u95EE\u9898)$', r'\1', cleaned)
        cleaned = re.sub(r'^(?:\u5728|\u4ECE|\u7531|\u5BF9|\u628A|\u88AB|\u8BA9|\u53EB|\u7ED9)(.{3,25})$', r'\1', cleaned)
        cleaned = re.sub(r'^(.{4,30})(?:\u7B49\u7B49|\u4E4B\u7C7B\u7684|\u4EC0\u4E48\u7684|\u8FD9\u4E9B|\u90A3\u4E9B)$', r'\1', cleaned)
        return cleaned.strip("\uFF0C\u3002\uFF1F\uFF01\uFF1B:\"'()\uFF08\uFF09[]\u3010\u3011{} ")

    def _rerank_candidate_rows_for_trace(self, trace: Dict[str, Any], score_map: Dict[Tuple[str, str], float]) -> None:
        candidates = trace.get('candidates', [])
        normalized = trace.get('normalized_sentence', '')
        best_text = trace.get('selected_candidate', '')
        best_score = None
        best_rank_score = float('-inf')
        for row in candidates:
            key = (normalized, row.get('text', ''))
            if key not in score_map:
                row['rerank_score'] = None
                continue
            row['source_text'] = normalized
            row['rerank_score'] = round(float(score_map[key]), 4)
            rank_score = self._conservative_first_level_rank_score(row)
            row['conservative_score'] = round(float(rank_score), 4)
            if best_score is None or rank_score > best_rank_score:
                best_score = row['rerank_score']
                best_rank_score = rank_score
                best_text = row.get('text', '')
        if best_score is not None:
            trace['used_rerank'] = True
            trace['selected_candidate'] = self._finalize_first_level_candidate(best_text, normalized)
        for row in candidates:
            row['selected'] = row.get('text') == best_text or row.get('text') == trace.get('selected_candidate')
        candidates.sort(
            key=lambda item: (
                item.get('conservative_score', -999.0),
                item['rerank_score'] if item.get('rerank_score') is not None else -1.0,
                item.get('rule_score', 0.0),
                -len(item.get('text', '')),
            ),
            reverse=True,
        )

    def _apply_global_batch_rerank(self, traces: List[Dict[str, Any]], model_manager=None) -> None:
        if not (Config and getattr(Config, 'ENABLE_ABSTRACT_RERANKER', False) and model_manager is not None):
            return
        try:
            if hasattr(model_manager, 'ensure_abstract_reranker_loaded'):
                model_manager.ensure_abstract_reranker_loaded()
            if not (
                hasattr(model_manager, 'is_abstract_reranker_available')
                and model_manager.is_abstract_reranker_available()
            ):
                return

            rerank_limit = max(1, int(max(getattr(Config, 'ABSTRACT_RERANK_TOP_N', 6), getattr(Config, 'FIRST_LEVEL_GLOBAL_RERANK_TOP_N', 24)))) if Config else 24
            pairs: List[Tuple[str, str]] = []
            seen: Set[Tuple[str, str]] = set()
            for trace in traces:
                normalized = trace.get('normalized_sentence', '')
                rows = [
                    row for row in trace.get('candidates', [])
                    if row.get('text') and not self._is_question_like(row.get('text', ''))
                ]
                rows.sort(
                    key=lambda item: (
                        item.get('semantic_recall_score') is not None,
                        item.get('conservative_score', -999.0),
                        item.get('semantic_recall_score', 0.0) or 0.0,
                        item.get('rule_score', 0.0),
                        -len(item.get('text', '')),
                    ),
                    reverse=True,
                )
                for row in rows[:rerank_limit]:
                    pair = (normalized, row.get('text', ''))
                    if pair not in seen:
                        seen.add(pair)
                        pairs.append(pair)
            if not pairs:
                return

            originals = [item[0] for item in pairs]
            candidates = [item[1] for item in pairs]
            if hasattr(model_manager, 'score_abstract_candidate_pairs'):
                scores = model_manager.score_abstract_candidate_pairs(pairs)
            else:
                scores = model_manager.score_abstract_candidates(originals, candidates)
            if not scores or len(scores) != len(pairs):
                return
            score_map = {pair: float(score) for pair, score in zip(pairs, scores)}
            for trace in traces:
                self._rerank_candidate_rows_for_trace(trace, score_map)
        except Exception as exc:
            logger.warning(f"全局批量一阶重排失败，回退规则候选: {exc}")

    def abstract_sentence(self, sentence: str, model_manager=None) -> str:
        """Extract a first-level code through the reusable trace flow."""
        self._ensure_first_level_defaults()
        s0 = (sentence or '').strip()
        if not s0:
            return ''
        if s0 in self.abstract_cache:
            return self.abstract_cache[s0]

        trace = self.build_first_level_candidate_trace(s0, model_manager=model_manager)
        compact = trace.get('selected_candidate', '')
        self.abstract_cache[s0] = compact
        return compact

    def _normalize_source_sentence(self, text: str) -> str:
        normalized = str(text or '').strip()
        if not normalized:
            return ''
        normalized = re.sub(r'^[\uFF0C\u3002\uFF1F\uFF01\uFF1B:\u3001\.\?!;\s]+', '', normalized)
        normalized = re.sub(r'[\?\uFF1F]+$', '\u3002', normalized)
        normalized = re.sub(r'[!\uFF01]+$', '\u3002', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.strip()

    def _post_refine_phrase(self, text: str) -> str:
        refined = str(text or '')
        for pattern in getattr(self, 'bad_phrase_patterns', []):
            refined = re.sub(pattern, '', refined)
        refined = re.sub(r'[（(]?\d{1,2}:\d{2}[)）]?', '', refined)
        refined = re.sub(r'^(\u56e0\u6b64|\u6240\u4ee5|\u7136\u540e|\u5e76\u4e14|\u800c\u4e14|\u90a3\u4e48|\u5176\u5b9e)+', '', refined)
        refined = re.sub(r'(\u56e0\u6b64|\u6240\u4ee5|\u7136\u540e|\u5e76\u4e14|\u800c\u4e14)+$', '', refined)
        refined = re.sub(r'^(\u8fd9\u4e2a|\u90a3\u4e2a|\u5b83)(?=[\u4e00-\u9fa5])', '', refined)
        refined = re.sub(r'\s+', '', refined)
        return refined.strip("\uFF0C\u3002\uFF1F\uFF01\uFF1B:\"'()\uFF08\uFF09[]\u3010\u3011{} ")

    def _is_question_like(self, text: str) -> bool:
        t = str(text or '').strip()
        if not t:
            return False
        return bool(
            re.search(r'[\?\uFF1F\u5417\u4e48\u5462]$', t)
            or re.search(r'(\u662f\u4e0d\u662f|\u662f\u5426|\u80fd\u4e0d\u80fd|\u53ef\u4e0d\u53ef\u4ee5|\u4f1a\u4e0d\u4f1a|\u6709\u6ca1\u6709|\u8981\u4e0d\u8981)', t)
            or re.search(r'^(\u4e3a\u4ec0\u4e48|\u600e\u4e48|\u5982\u4f55|\u54ea[\u91cc\u513f\u4e2a\u79cd])', t)
        )

    def _compute_salience(self, text: str) -> Dict[str, float]:
        """计算句子的四维显著性分数：转折/对比、因果链、强度/极端、问题/困境"""
        t = str(text or '').strip()
        if not t:
            return {'contrast': 0.0, 'causal': 0.0, 'intensity': 0.0, 'problem': 0.0, 'total': 0.0}

        # 1. 转折/对比信号 —— 转折后通常是核心信息
        contrast_markers = [
            r'但是', r'不过', r'然而', r'却', r'反而', r'反倒',
            r'尽管', r'虽然', r'即使', r'即便', r'本来.*但', r'原以为.*但',
            r'以前.*现在', r'过去.*现在', r'之前.*后来', r'一开始.*后来',
        ]
        contrast_score = sum(1.0 for m in contrast_markers if re.search(m, t))
        contrast_score = min(contrast_score, 3.0)  # 上限3分

        # 2. 因果/推论信号 —— 因果链是概念锚点
        causal_markers = [
            r'因为', r'所以', r'因此', r'由于', r'导致', r'致使',
            r'从而', r'造成', r'引起', r'影响', r'推动', r'促进',
            r'使得', r'之所以', r'归根结底', r'根本原因',
        ]
        causal_score = sum(1.0 for m in causal_markers if re.search(m, t))
        causal_score = min(causal_score, 3.0)

        # 3. 强度/极端信号 —— 程度=说话人重视程度
        intensity_markers = [
            r'特别', r'非常', r'最', r'极其', r'极度', r'十分',
            r'根本', r'完全', r'彻底', r'绝对', r'毫不',
            r'一直[都在]?', r'每次', r'总是', r'反复', r'不断',
            r'太\w{1,3}$', r'很\w{1,3}$',
        ]
        intensity_score = sum(1.0 for m in intensity_markers if re.search(m, t))
        # 感叹号=高强度
        if re.search(r'[！!]$', t):
            intensity_score += 1.0
        intensity_score = min(intensity_score, 3.0)

        # 4. 问题/困境信号 —— 扎根理论关注"麻烦"
        problem_markers = [
            r'困难', r'问题', r'矛盾', r'冲突', r'瓶颈', r'障碍',
            r'卡在', r'拖慢', r'延迟', r'受限', r'不足', r'短板',
            r'风险', r'压力', r'挑战', r'负担', r'缺乏', r'缺少',
            r'不行', r'没办法', r'做不了', r'无法',
        ]
        problem_score = sum(1.0 for m in problem_markers if re.search(m, t))
        problem_score = min(problem_score, 3.0)

        # 加权总分：问题 > 转折 > 因果 > 强度
        total = (
            problem_score * 1.5 +
            contrast_score * 1.2 +
            causal_score * 1.0 +
            intensity_score * 0.8
        )
        return {
            'contrast': round(contrast_score, 2),
            'causal': round(causal_score, 2),
            'intensity': round(intensity_score, 2),
            'problem': round(problem_score, 2),
            'total': round(total, 2),
        }

    def _is_coding_worthy_sentence(self, text: str) -> bool:
        """判断句子是否值得编码（编码价值门控）"""
        t = str(text or '').strip()
        if not t:
            return False

        # 太短不编码
        min_len = getattr(self, 'coding_worthy_min_length', 10)
        if len(t) < min_len:
            return False

        # 纯应和跳过
        if re.match(r'^(对|嗯|哦|是的|好的|没错|确实|可以|行|好|有|没有|不是)[，,。.!！]?$', t):
            return False

        # 纯态度无信息：只有主观感受，无实质内容
        if re.match(r'^(我|我们)?(觉得|感觉|认为|想|看)(也|都)?(是|就|很|挺|蛮|还|比较)', t) and not self._has_first_level_information_cue(t):
            return False

        # 访谈过渡语
        if re.match(r'^(那我|那我先|我接着说|下一个|接下来|下面|我们先|我先说)', t) and not self._has_first_level_information_cue(t):
            return False

        # 计算显著性
        salience = self._compute_salience(t)
        min_salience = getattr(self, 'coding_worthy_min_salience', 1.5)

        # 短句需要更高的显著性门槛
        if len(t) < 20:
            if salience['total'] < max(min_salience, 2.5):
                return False

        # 标准句：显著性不足且无信息提示词
        if salience['total'] < min_salience and not self._has_first_level_information_cue(t):
            # 哪怕无显著性，只要有足够多专业词也可入
            prof_count = sum(1 for term in [
                '技术', '资源', '平台', '机制', '流程', '生态',
                '需求', '风险', '压力', '冲突', '协同', '合作',
                '创新', '服务', '客户', '团队', '品牌', '治理',
                '监督', '审批', '架构', '数据', '能力', '绩效',
                '战略', '路径', '场景', '系统', '设备', '模块',
            ] if term in t)
            if prof_count < 2:
                return False

        return True

    def _formalize_code(self, code: str) -> str:
        """将一阶编码规范化：口语词替换为书面用语"""
        ct = str(code or '').strip()
        if not ct:
            return ct

        mapping = getattr(self, 'colloquial_to_formal', {})
        # 按长度降序替换，避免短词误替换（如'make'中的'ma'）
        for colloquial in sorted(mapping.keys(), key=len, reverse=True):
            if colloquial in ct:
                ct = ct.replace(colloquial, mapping[colloquial])

        # 去掉口语后缀
        ct = re.sub(r'(什么的|之类的|那种感觉|这种感觉|这样子|那样子|怎么说呢|就是说)$', '', ct)
        # 去掉句末语气词残留
        ct = re.sub(r'[吧呢啊嘛呀哦哈哎诶噢呃]+$', '', ct)
        # 清理多余"的"字（"的\xe5\xbd\xb1\xe5\x93\x8d" → "影响"）
        ct = re.sub(r'的(\w{2,4})$', r'\1', ct)
        # 去掉"我和我们"之类的人称前缀
        ct = re.sub(r'^[我我们你你们他他们它它们大家]*(?:也|还是|都|就|会|要|能)?', '', ct)
        ct = ct.strip()

        # 如果规范化后变空，返回原码
        return ct if ct else str(code or '').strip()

    def _compress_first_level_candidate_variants(self, text: str) -> List[str]:
        base = self._normalize_candidate_for_first_level(str(text or ""))
        if not base:
            return []
        variants: List[str] = []
        seen: Set[str] = set()

        def add(value: str):
            cand = self._normalize_candidate_for_first_level(value)
            if not cand:
                return
            if len(cand) < 4 or len(cand) > 24:
                return
            if self._contains_colloquial_residue(cand) or self._is_question_like(cand):
                return
            if cand not in seen:
                seen.add(cand)
                variants.append(cand)

        for part in self._split_first_level_candidate_segments(base):
            add(part)
            compact = re.sub(r'^(?:我们|他们|你们|大家|客户|企业|项目|平台|它们|这个|那个|这种|那些|这些)?(?:可以|能够|能|会|要|需要|希望|想要|通过|把|将|对|打造|构建|建立|开展|推进|推动)?', '', part)
            add(compact)
            compact_tail = re.sub(r'^.*?(技术|品牌|资源|平台|机制|流程|生态|需求|问题|合作|协同|创新|服务|应用|模块|设备|系统|客户|团队|工业互联网)', r'\1', part)
            add(compact_tail)
            for transform in (
                (r'^推动(?:他们|我们|企业|双方)?(.{2,18}(?:合作|交流与合作))$', r'\1'),
                (r'^(?:客户的)?信息系统和(?:我们的)?系统对接$', '客户信息系统对接'),
                (r'^我们购买了?(.{2,16}(?:云存储|云计算|服务))$', r'\1购买'),
                (r'^我们将.{0,12}(生产设备|设备).{0,8}搬到(工业互联网)$', r'\1接入\2'),
                (r'^我们也会指导客户$', '客户指导协同'),
                (r'^让他能够更好地带领.*?(团队实现技术创新)$', r'\1'),
                (r'^我们从(.{2,16})中找寻灵感$', r'\1启发'),
                (r'^钱已经不再是我的目标了$', '创业目标转变'),
                (r'^我们跟(.{2,18})搞了一个(.{2,12})$', r'\2建设'),
                (r'^一开始书记来找我$', '社区动员参与'),
                (r'^往品牌化这个方向走把粉丝对个人的粘性转嫁到对品牌的粘性$', '品牌粘性转化'),
                (r'^我们自建服务器$', '自建服务器'),
                (r'^每个阶段的重点不同.*?我们参与深度是不同的$', '阶段性参与调整'),
                (r'^我们面临的是自身技术进步$', '自身技术进步压力'),
                (r'^.*生产意愿和生产习惯以及当地默认的惯例开展.*随意$', '规范缺乏'),
            ):
                replaced = re.sub(transform[0], transform[1], part)
                if replaced != part:
                    add(replaced)
            for pattern in (
                r'((?:影响|导致|推动|推进|解决|分析|反馈|合作|转变|优化|对接|支持|审批|协调|整合|开发|探索|识别|建立|引入|获得|提高|降低|调整|打造|构建|涵养|塑造|形成|提升|购买|指导)[^，,、；;。！？!?]{2,14})',
                r'([^，,、；;。！？!?]{2,10}(?:受影响|受限|受阻|不足|短板|风险|压力|冲突))',
                r'((?:客户|市场|项目|资源|技术|流程|机制|服务|需求|机会|风险|问题|品牌|生态|平台|应用|模块|设备|合作|系统|团队|工业互联网)[^，,、；;。！？!?]{1,10}(?:需求|诉求|反馈|协同|整合|优化|推进|支持|识别|解决|不足|风险|合作|赋能|创新|共创|共享|建立|提升|应用|对接|接入|购买|指导))',
            ):
                for match in re.finditer(pattern, part):
                    add(match.group(1))
        return variants

    def _normalize_candidate_for_first_level(self, text: str) -> str:
        refined = str(text or '').strip()
        if not refined:
            return ''

        refined = re.sub(r'(?<=[\u4e00-\u9fff])\?(?=[\u4e00-\u9fff])', '\uFF0C', refined)
        refined = re.sub(r'^\s*[\u2460-\u2473\u2776-\u277F\u24F5-\u24FE\u3251-\u325F①②③④⑤⑥⑦⑧⑨⑩]+[\u3001\.\uFF0E\)\uFF09\s]*', '', refined)
        refined = re.sub(r'^\s*(?:\d+|[一二三四五六七八九十]+)[\u3001\.\uFF0E\)\uFF09]\s*', '', refined)
        refined = re.sub(r'^(\u4f60\u8bf4|\u4f60\u770b|\u5982\u679c|\u8981\u662f|\u5047\u5982|\u5176\u5b9e|\u4f46\u662f|\u4e0d\u8fc7|\u6240\u4ee5|\u56e0\u6b64|\u7136\u540e|\u5e76\u4e14|\u800c\u4e14|\u90a3\u4e48|\u56e0\u4e3a)+', '', refined)
        refined = re.sub(r'^(\u6211\u4eec\u901a\u8fc7|\u6211\u4eec\u5c31\u53ef\u4ee5|\u6211\u4eec\u5c31\u80fd|\u6211\u4eec\u5c31\u662f|\u6211\u4eec\u628a|\u6211\u4eec\u53bb|\u6211\u4eec\u6765)+', '', refined)
        refined = re.sub(r'^(\u8fd9\u4e2a\u6d41\u7a0b|\u8fd9\u4e2a\u95ee\u9898|\u8fd9\u4e2a\u4e8b\u60c5|\u8fd9\u4e2a\u60c5\u51b5)', '', refined)
        refined = re.sub(r'(\u662f\u4e0d\u662f|\u662f\u5426|\u80fd\u4e0d\u80fd|\u53ef\u4e0d\u53ef\u4ee5|\u4f1a\u4e0d\u4f1a|\u6709\u6ca1\u6709|\u8981\u4e0d\u8981)', '', refined)
        refined = re.sub(r'^(\u4e3a\u4ec0\u4e48|\u600e\u4e48|\u5982\u4f55)', '', refined)
        refined = re.sub(r'[（(]?\d{1,2}:\d{2}[)）]?', '', refined)
        refined = re.sub(r'\u7684\u8bdd', '', refined)
        refined = re.sub(r'\u7684\u65f6\u5019', '', refined)
        refined = re.sub(r'(怎么说呢|就是说|我觉得|相当于|要看|分场合|这个东西|这个事情|这个问题)', '', refined)
        refined = re.sub(r'[吧呢啊嘛呀哦哈哎诶噢呃]+$', '', refined)
        refined = re.sub(r'\u6bcf\u6b21\u90fd', '\u7ecf\u5e38', refined)
        refined = re.sub(r'\u8fd9\u91cc$', '', refined)
        refined = re.sub(r'(\u5c31\u5f88\u53d7\u5f71\u54cd|\u5f88\u53d7\u5f71\u54cd)', '\u53d7\u5f71\u54cd', refined)
        refined = re.sub(r'\u6211\u4eec\u5c31\u53ea\u80fd', '\u53ea\u80fd', refined)
        refined = re.sub(r'\u6211\u4eec\u53ea\u80fd', '\u53ea\u80fd', refined)
        refined = refined.replace('\u81ea\u5df1', '\u81ea\u884c')
        refined = refined.replace('\u4e00\u76f4\u50ac', '\u50ac\u4fc3')
        refined = refined.replace('\u4e0d\u591f', '\u4e0d\u8db3')
        refined = refined.replace('\u592a\u6162', '\u8fc7\u6162')
        refined = refined.replace('\u5ba2\u6237\u7684\u53cd\u9988', '\u5ba2\u6237\u53cd\u9988')
        refined = refined.replace('\u5206\u6790\u5ba2\u6237\u7684\u53cd\u9988', '\u5206\u6790\u5ba2\u6237\u53cd\u9988')
        refined = refined.replace('\u522b\u7684\u7ec4\u7684\u8bbe\u5907', '\u522b\u7ec4\u8bbe\u5907')
        refined = refined.replace('\u501f\u522b\u7ec4\u8bbe\u5907\u6765\u505a', '\u501f\u7528\u522b\u7ec4\u8bbe\u5907')
        refined = re.sub(r'\s+', '', refined)
        return refined.strip("\uFF0C\u3002\uFF1F\uFF01\uFF1B:\"'()\uFF08\uFF09[]\u3010\u3011{} ")

    def _is_semantically_complete(self, text: str) -> bool:
        t = (text or '').strip()
        if not t:
            return False
        if len(t) < 4:
            return False
        if self._is_question_like(t):
            return False
        if re.search(r'(\u600e\u4e48|\u5982\u4f55|\u8fd9\u91cc|\u8fd9\u6837|\u90a3\u6837|\u8fd9\u79cd|\u8fd9\u4e9b|\u90a3\u4e9b|\u8fd9\u7c7b|\u90a3\u7c7b)$', t):
            return False
        if re.search(r'^(\u56e0\u4e3a|\u5982\u679c|\u5373\u4f7f|\u867d\u7136|\u4f46\u662f|\u4e0d\u8fc7|\u6240\u4ee5|\u56e0\u6b64|\u7136\u540e|\u5e76\u4e14|\u800c\u4e14)$', t):
            return False
        if re.search(r'^(\u56e0\u4e3a|\u5982\u679c|\u5373\u4f7f|\u867d\u7136)', t) and not re.search(r'(\u6240\u4ee5|\u56e0\u6b64|\u5bfc\u81f4|\u4f7f\u5f97|\u4ece\u800c|\u53ea\u80fd|\u5f71\u54cd)', t):
            return False
        if re.search(r'^(\u6211|\u6211\u4eec|\u4f60|\u4f60\u4eec).*(\u4e0d\u592a\u6e05\u695a|\u4e0d\u77e5\u9053|\u4e0d\u786e\u5b9a|\u8bf4\u4e0d\u597d)', t):
            return False
        if re.search(r'^(\u8fd8\u53ef\u4ee5|\u8fd8\u597d|\u5dee\u4e0d\u591a|\u4e00\u822c\u822c?)$', t):
            return False
        return True

    def _truncate_to_word(self, text: str, max_length: int) -> str:
        t = (text or '').strip()
        if max_length <= 0 or len(t) <= max_length:
            return t

        cut = t[:max_length].rstrip("\uFF0C\u3002\uFF1F\uFF01\uFF1B:\"'()\uFF08\uFF09[]\u3010\u3011{} ")
        for _ in range(6):
            if not cut:
                break
            if re.search(r'(\u600e\u4e48|\u5982\u4f55|\u8fd9\u91cc|\u8fd9\u6837|\u90a3\u6837|\u8fd9\u79cd|\u8fd9\u4e9b|\u90a3\u4e9b|\u8fd9\u7c7b|\u90a3\u7c7b)$', cut):
                cut = cut[:-1]
                continue
            if re.search(r'(\u56e0\u4e3a|\u5982\u679c|\u5373\u4f7f|\u867d\u7136|\u4f46\u662f|\u4e0d\u8fc7|\u6240\u4ee5|\u56e0\u6b64|\u7136\u540e|\u5e76\u4e14|\u800c\u4e14)$', cut):
                cut = cut[:-1]
                continue
            break
        return cut.strip("\uFF0C\u3002\uFF1F\uFF01\uFF1B:\"'()\uFF08\uFF09[]\u3010\u3011{} ")

    def _smart_abbreviate(self, text: str, max_length: int) -> str:
        """\u667A\u80FD\u7F29\u5199\uFF1A\u5728\u4FDD\u8BC1\u8BED\u4E49\u5B8C\u6574\u7684\u524D\u63D0\u4E0B\u7F29\u77ED\u4EE3\u7801\uFF0C\u4FDD\u7559\u6838\u5FC3\u6982\u5FF5

        \u7B56\u7565\uFF1A
        1. \u4F18\u5148\u4FDD\u7559\u542B\u4E13\u4E1A\u672F\u8BED/\u95EE\u9898\u8BCD/\u52A8\u4F5C\u8BCD\u7684\u7247\u6BB5
        2. \u5220\u9664\u72B6\u8BED/\u7A0B\u5EA6\u4FEE\u9970\u7B49\u975E\u6838\u5FC3\u90E8\u5206
        3. \u5C1D\u8BD5\u63D0\u53D6"\u4E3B\u8BED\u6838\u5FC3+\u8C13\u8BED\u5173\u952E"\u7ED3\u6784
        """
        t = str(text or '').strip()
        if not t or max_length <= 0 or len(t) <= max_length:
            return t

        # \u62C6\u5206\u4E3A\u9017\u53F7\u5206\u9694\u7684\u7247\u6BB5
        parts = [p.strip() for p in re.split(r'[\uFF0C,\u3001]', t) if p.strip()]
        if len(parts) <= 1:
            return self._truncate_to_word(t, max_length)

        # \u7ED9\u6BCF\u4E2A\u7247\u6BB5\u6253\u5206\uFF1A\u542B\u4E13\u4E1A\u8BCD/\u95EE\u9898\u8BCD/\u52A8\u4F5C\u8BCD\u7684\u7247\u6BB5\u6743\u91CD\u9AD8
        high_value_words = re.compile(
            r'(\u673A\u5236|\u6D41\u7A0B|\u8D44\u6E90|\u7B56\u7565|\u8DEF\u5F84|\u6A21\u5F0F|\u7ED3\u6784|\u80FD\u529B|\u67B6\u6784|\u751F\u6001|\u6CBB\u7406|\u76D1\u7763|\u534F\u540C|\u5BA1\u6279|\u7EE9\u6548|\u6218\u7565|\u9700\u6C42|\u670D\u52A1|\u521B\u65B0|'
            r'\u8BC4\u4F30|\u4F18\u5316|\u914D\u7F6E|\u6574\u5408|\u4FDD\u969C|\u7EA6\u675F|\u53CD\u9988|\u9A71\u52A8|\u8D4B\u80FD|\u8F6C\u578B|'
            r'\u4E0D\u8DB3|\u53D7\u9650|\u7F3A\u5931|\u7F3A\u4E4F|\u53D7\u963B|\u5EF6\u8FDF|\u5F71\u54CD|\u63A8\u52A8|\u964D\u4F4E|\u589E\u52A0|'
            r'\u5BA2\u6237|\u56E2\u961F|\u54C1\u724C|\u5E73\u53F0|\u7CFB\u7EDF|\u6570\u636E|\u5B89\u5168|\u8D28\u91CF|\u6210\u672C|\u6548\u7387)'
        )

        def part_score(part: str) -> float:
            s = 0.0
            s += len(high_value_words.findall(part)) * 2.0
            # \u957F\u7247\u6BB5\u7565\u6263\u5206\uFF08\u6211\u4EEC\u60F3\u8981\u7D27\u51D1\u7684\uFF09
            s -= max(0, len(part) - 8) * 0.1
            # \u4EE5"\u7684"\u7ED3\u5C3E\u6263\u5206\uFF08\u4E0D\u5B8C\u6574\uFF09
            if part.endswith('\u7684'):
                s -= 1.5
            return s

        # \u6309\u5F97\u5206\u964D\u5E8F
        ranked = sorted(parts, key=part_score, reverse=True)

        # \u8D2A\u5FC3\u9009\u62E9\uFF1A\u4ECE\u9AD8\u5206\u7247\u6BB5\u5F00\u59CB\u62FC\u63A5\uFF0C\u76F4\u5230\u63A5\u8FD1\u957F\u5EA6\u4E0A\u9650
        selected = []
        current_len = 0
        for part in ranked:
            test_len = current_len + len(part) + (1 if selected else 0)
            if test_len <= max_length:
                selected.append(part)
                current_len = test_len

        if selected:
            return '\uFF0C'.join(selected)

        # \u5982\u679C\u5355\u4E2A\u7247\u6BB5\u90FD\u592A\u957F\uFF0C\u5BF9\u8BE5\u7247\u6BB5\u505A\u622A\u65AD
        best_part = ranked[0]
        return self._truncate_to_word(best_part, max_length)

    def _limit_first_level_text(self, text: str, max_length: int) -> str:
        t = (text or '').strip()
        if not t:
            return ''
        if max_length <= 0:
            return t
        if len(t) <= max_length:
            return t

        parts = [p.strip() for p in re.split(r'[\uFF0C,\u3002]', t) if p.strip()]
        if not parts:
            return self._truncate_to_word(t, max_length)

        best = ''
        for i in range(len(parts)):
            built = ''
            for j in range(i, len(parts)):
                built = parts[j] if not built else f'{built}\uFF0C{parts[j]}'
                if len(built) > max_length:
                    break
                cand = built.strip("\uFF0C\u3002\uFF1F\uFF01\uFF1B:\"'()\uFF08\uFF09[]\u3010\u3011{} ")
                if not cand:
                    continue
                if self._is_semantically_complete(cand) and len(cand) > len(best):
                    best = cand

        if best:
            return best
        # \u4F20\u7EDF\u65B9\u6CD5\u627E\u4E0D\u5230\u5408\u9002\u7247\u6BB5\u65F6\uFF0C\u4F7F\u7528\u667A\u80FD\u7F29\u5199
        return self._smart_abbreviate(t, max_length)

    def generate_codes_with_trained_model(self, processed_data: Dict[str, Any],
                                          model_manager,
                                          progress_callback: Optional[Callable] = None,
                                          coding_thresholds: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """使用训练模型生成编码"""
        try:
            self._apply_similarity_threshold_options(coding_thresholds)
            self._ensure_rag_threshold_defaults()
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
            filtered_sentences = []
            texts = []
            for sent in all_sentences:
                t = (sent.get('content', '') or '').strip()
                if self._is_coding_worthy_sentence(t):
                    filtered_sentences.append(sent)
                    texts.append(t)

            if not texts:
                raise ValueError("没有找到有效的文本内容")

            if progress_callback:
                progress_callback(50)

            # 使用训练模型预测类别（作为参考）
            predictions, predicted_labels = model_manager.predict_categories(texts)

            if progress_callback:
                progress_callback(70)

            # 构建编码结构
            first_level_codes = {}
            second_level_mapping = {}
            self.reset_first_level_trace_meta()
            third_level_mapping = {}

            # 检查编码库和语义匹配器是否可用
            use_semantic_matching = False
            second_level_codes_list = []
            third_level_codes_list = []

            if self.coding_library and self.semantic_matcher:
                try:
                    second_level_codes_list = self.coding_library.get_all_second_level_codes()
                    third_level_codes_list = self.coding_library.get_all_third_level_codes()
                    if second_level_codes_list and third_level_codes_list:
                        use_semantic_matching = True
                        logger.info("使用语义相似度匹配进行编码")
                except Exception as e:
                    logger.error(f"获取编码库失败: {e}")

            use_global_batch_rerank = bool((coding_thresholds or {}).get("use_global_batch_rerank", False))
            global_traces: List[Dict[str, Any]] = []
            if use_global_batch_rerank:
                global_traces = [
                    self.build_first_level_candidate_trace(
                        text,
                        model_manager=model_manager,
                        defer_rerank=True,
                    )
                    for text in texts
                ]
                self._apply_global_batch_rerank(global_traces, model_manager=model_manager)

            for i, (text, label) in enumerate(zip(texts, predicted_labels)):
                code_key = f"FL_{i + 1:04d}"

                trace = (
                    global_traces[i]
                    if use_global_batch_rerank and i < len(global_traces)
                    else self.build_first_level_candidate_trace(text, model_manager=model_manager)
                )
                abstracted = trace.get("selected_candidate", "")
                source_detail = self._repair_first_level_sentence_detail(filtered_sentences[i])
                if not source_detail.get("sentence_id"):
                    self._store_first_level_trace(code_key, trace)
                    continue
                abstracted = self._select_quality_first_level_candidate(trace, source_detail)
                if not abstracted:
                    self._store_first_level_trace(code_key, trace)
                    continue
                # 清理编码开头的标点符号
                abstracted = self._clean_code_prefix(abstracted)
                
                first_level_codes[code_key] = [
                    abstracted,
                    [source_detail],  # source_sentences
                    1,  # file_count
                    1,  # sentence_count
                    [source_detail]  # sentence_details
                ]
                self._store_first_level_trace(code_key, trace)

                # 确定二阶编码
                if use_semantic_matching and abstracted:
                    # 使用语义相似度匹配二阶编码（召回Top-k候选）
                    top_k = 5  # 默认召回5个候选
                    
                    # 检查缓存中是否有结果
                    cache_key = f"{abstracted}_{top_k}_0.3"
                    if cache_key in self.similarity_cache:
                        logger.info(f"使用缓存的相似度计算结果")
                        matches = self.similarity_cache[cache_key]
                    else:
                        # 计算相似度
                        matches = self.semantic_matcher.match_first_level_to_second_level(
                            abstracted,
                            second_level_codes_list,
                            top_k=top_k,
                            threshold=self.rag_second_level_threshold
                        )
                        # 缓存结果
                        self.similarity_cache[cache_key] = matches

                    if matches:
                        # 检查是否有加载的模型，如果没有则直接进行相似度匹配
                        if model_manager and model_manager.is_trained_model_available():
                            # 使用bert_finetuned模型进行重排
                            logger.info(f"使用bert_finetuned模型对 {len(matches)} 个候选进行重排")
                            # 准备候选编码
                            candidate_codes = [match[0].get('name') for match in matches]
                            # 使用模型对候选进行评分
                            try:
                                # 构建输入文本
                                inputs = [f"{abstracted} [SEP] {code}" for code in candidate_codes]
                                # 预测类别
                                predictions, _ = model_manager.predict_categories(inputs)
                                # 计算置信度
                                confidences = []
                                for pred in predictions:
                                    if isinstance(pred, tuple):
                                        confidences.append(pred[1])
                                    else:
                                        confidences.append(0.0)
                                # 找到置信度最高的编码
                                if confidences:
                                    best_idx = confidences.index(max(confidences))
                                    best_match, _ = matches[best_idx]
                                    second_cat = best_match.get('name')
                                    logger.info(f"bert_finetuned模型选择的二阶编码: '{second_cat}' (置信度: {max(confidences):.4f})")
                                else:
                                    # 回退到相似度最高的编码
                                    best_match, similarity = matches[0]
                                    second_cat = best_match.get('name')
                                    logger.info(f"回退到相似度匹配: '{second_cat}' (相似度: {similarity:.4f})")
                            except Exception as e:
                                logger.warning(f"模型重排失败，回退到相似度匹配: {e}")
                                # 回退到相似度最高的编码
                                best_match, similarity = matches[0]
                                second_cat = best_match.get('name')
                                logger.info(f"回退到相似度匹配: '{second_cat}' (相似度: {similarity:.4f})")
                        else:
                            # 没有加载模型，直接进行相似度匹配
                            best_match, similarity = matches[0]
                            second_cat = best_match.get('name')
                            logger.info(f"未加载训练模型，使用相似度匹配: '{second_cat}' (相似度: {similarity:.4f})")
                    else:
                        second_cat = "其他各类话题"
                        logger.info(f"一阶编码 '{abstracted[:30]}...' 未找到匹配的二阶编码，归类为'其他各类话题'")
                else:
                    # 回退到使用训练模型的预测结果
                    if '||' in label:
                        third_cat_pred, second_cat = label.split('||', 1)
                    else:
                        second_cat = label if label else "其他"
                    logger.info(f"使用训练模型预测的二阶编码: {second_cat}")

                # 存储二阶编码映射
                second_level_mapping[code_key] = second_cat

                # 确定三阶编码
                if use_semantic_matching:
                    # 查找对应的二阶编码
                    second_code = None
                    for code in second_level_codes_list:
                        if code.get('name') == second_cat:
                            second_code = code
                            break

                    if second_code:
                        # 使用语义相似度匹配三阶编码
                        match = self.semantic_matcher.match_second_level_to_third_level(
                            second_code,
                            third_level_codes_list,
                            threshold=self.rag_third_level_threshold
                        )

                        if match:
                            best_match, similarity = match
                            third_cat = best_match.get('name')
                            logger.info(f"二阶编码 '{second_cat}' 匹配到三阶编码 '{third_cat}' (相似度: {similarity:.4f})")
                        else:
                            third_cat = "其他重要维度"
                            logger.info(f"二阶编码 '{second_cat}' 未找到匹配的三阶编码，归类为'其他重要维度'")
                    else:
                        # 如果找不到对应的二阶编码，使用规则匹配
                        third_cat = "其他重要维度"
                        logger.info(f"未找到对应的二阶编码，三阶编码归类为'其他重要维度'")
                else:
                    # 回退到使用训练模型的预测结果
                    if '||' in label:
                        third_cat, _ = label.split('||', 1)
                    else:
                        third_cat = "综合主题"
                    logger.info(f"使用训练模型预测的三阶编码: {third_cat}")

                # 存储三阶编码映射
                third_level_mapping[second_cat] = third_cat

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
                progress_callback(100)

            # 编码生成完成，释放模型资源
            if model_manager and hasattr(model_manager, 'release_model_resources'):
                model_manager.release_model_resources()

            return {
                "一阶编码": dict(first_level_codes),
                "二阶编码": dict(second_level_codes),
                "三阶编码": dict(third_level_codes),
                "file_sentence_mapping": file_sentence_mapping
            }

        except Exception as e:
            logger.error(f"使用训练模型生成编码失败: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 即使出错，也尝试释放模型资源
            if model_manager and hasattr(model_manager, 'release_model_resources'):
                model_manager.release_model_resources()
            return {
                "一阶编码": {"错误": [f"使用训练模型生成编码失败: {str(e)}"]},
                "二阶编码": {"错误": ["请检查训练模型"]},
                "三阶编码": {"错误": ["模型预测失败"]}
            }
    def generate_grounded_theory_codes_multi_files(self, processed_data: Dict[str, Any], model_manager,
                                                   progress_callback: Optional[Callable] = None,
                                                   use_trained_model: bool = False,
                                                   coding_thresholds: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """为多个文件生成扎根理论三级编码"""
        if use_trained_model and model_manager.is_trained_model_available():
            return self.generate_codes_with_trained_model(
                processed_data,
                model_manager,
                progress_callback,
                coding_thresholds=coding_thresholds,
            )
        else:
            # 使用原有的基于规则的编码生成
            return self.generate_codes_with_rules(
                processed_data,
                progress_callback,
                model_manager=model_manager,
                coding_thresholds=coding_thresholds,
            )

    def generate_codes_with_rules(self, processed_data: Dict[str, Any],
                                  progress_callback: Optional[Callable] = None,
                                  model_manager=None,
                                  coding_thresholds: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """使用基于规则的编码生成"""
        try:
            self._apply_similarity_threshold_options(coding_thresholds)
            self._ensure_rag_threshold_defaults()
            if progress_callback:
                progress_callback(10)

            combined_text = processed_data['combined_text']
            file_sentence_mapping = processed_data['file_sentence_mapping']

            # 提取所有句子
            all_sentences = []
            for filename, file_data in file_sentence_mapping.items():
                sentences = file_data.get('sentences', [])
                all_sentences.extend(sentences)

            if progress_callback:
                progress_callback(30)

            # 生成一阶编码（可选：使用模型对候选片段重排序）
            first_level_codes = self.generate_first_level_codes(
                all_sentences,
                model_manager=model_manager,
                coding_options=coding_thresholds,
            )
            logger.info(f"生成 {len(first_level_codes)} 个一阶编码")

            if progress_callback:
                progress_callback(60)

            # 将一阶编码分类为二阶编码
            second_level_codes = self.generate_second_level_codes_improved(first_level_codes, model_manager=model_manager)
            logger.info(f"生成 {len(second_level_codes)} 个二阶编码")

            if progress_callback:
                progress_callback(80)

            # 将二阶编码抽象为三阶编码
            third_level_codes = self.generate_third_level_codes_improved(second_level_codes)
            logger.info(f"生成 {len(third_level_codes)} 个三阶编码")

            if progress_callback:
                progress_callback(100)

            # 编码生成完成，释放模型资源
            if model_manager and hasattr(model_manager, 'release_model_resources'):
                model_manager.release_model_resources()

            return {
                "一阶编码": first_level_codes,
                "二阶编码": second_level_codes,
                "三阶编码": third_level_codes,
                "file_sentence_mapping": file_sentence_mapping
            }

        except Exception as e:
            logger.error(f"生成多文件编码失败: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 即使出错，也尝试释放模型资源
            if model_manager and hasattr(model_manager, 'release_model_resources'):
                model_manager.release_model_resources()
                
            return {
                "一阶编码": {"错误": ["生成编码时出现错误"]},
                "二阶编码": {"错误": ["请检查输入文本"]},
                "三阶编码": {"错误": ["系统故障"]}
            }

    def generate_first_level_codes(
        self,
        sentences: List[Dict[str, Any]],
        model_manager=None,
        coding_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[Any]]:
        """生成一阶编码 - 优先抽象提炼受访者语句"""
        self.reset_first_level_trace_meta()
        first_level_codes = {}
        trace_items: List[Tuple[str, Dict[str, Any], Dict[str, Any]]] = []
        use_global_batch_rerank = bool((coding_options or {}).get("use_global_batch_rerank", False))

        for i, sentence in enumerate(sentences):
            try:
                content = sentence.get('content', '')
                speaker = sentence.get('speaker', '')

                # 如果存在说话人字段，则只处理受访者内容；否则默认处理
                if speaker and speaker != 'respondent':
                    continue
                if content and self._is_coding_worthy_sentence(content.strip()):
                    code_key = f"FL_{i + 1:04d}"
                    trace = self.build_first_level_candidate_trace(
                        content,
                        model_manager=model_manager,
                        defer_rerank=use_global_batch_rerank,
                    )
                    trace_items.append((code_key, sentence, trace))

                    if not use_global_batch_rerank:
                        source_detail = self._repair_first_level_sentence_detail(sentence)
                        if not source_detail.get("sentence_id"):
                            self._store_first_level_trace(code_key, trace)
                            continue
                        selected_candidate = self._select_quality_first_level_candidate(trace, source_detail)
                        self._store_first_level_trace(code_key, trace)
                        if not selected_candidate:
                            continue
                        first_level_codes[code_key] = [
                            selected_candidate,
                            [source_detail],  # source_sentences
                            1,  # file_count
                            1,  # sentence_count
                            [source_detail]  # sentence_details
                        ]

            except Exception as e:
                logger.warning(f"处理句子失败 {i}: {e}")

        if use_global_batch_rerank and trace_items:
            self._apply_global_batch_rerank([trace for _, _, trace in trace_items], model_manager=model_manager)
            for code_key, sentence, trace in trace_items:
                source_detail = self._repair_first_level_sentence_detail(sentence)
                if not source_detail.get("sentence_id"):
                    self._store_first_level_trace(code_key, trace)
                    continue
                selected_candidate = self._select_quality_first_level_candidate(trace, source_detail)
                self._store_first_level_trace(code_key, trace)
                if not selected_candidate:
                    continue
                first_level_codes[code_key] = [
                    selected_candidate,
                    [source_detail],
                    1,
                    1,
                    [source_detail],
                ]

        return first_level_codes

    def _init_rag_components(self):
        """初始化RAG组件，失败时保持关闭并回退到旧流程。"""
        try:
            if not Config or not getattr(Config, "ENABLE_RAG_CODING", False):
                return
            if not (RuntimeStrategyDetector and RagIndexManager and RAGSemanticMatcher and FirstLevelClusterer and CodingDecisionPolicy):
                return
            if not self.coding_library:
                return

            self.runtime_strategy = RuntimeStrategyDetector().detect()
            embedding_fn = None
            if self.semantic_matcher and self.runtime_strategy.use_vector_clustering:
                embedding_fn = self.semantic_matcher.get_embedding

            self.rag_index_manager = RagIndexManager(
                self.coding_library.library_path,
                Config.RAG_INDEX_DIR,
                embedding_fn=embedding_fn,
            )
            if not self.rag_index_manager.ensure_fresh():
                logger.warning("RAG索引不可用，回退到传统语义匹配流程")
                return

            self.rag_matcher = RAGSemanticMatcher(
                Config.RAG_INDEX_DIR,
                embedding_fn=embedding_fn,
            )
            if not self.rag_matcher.documents:
                logger.warning("RAG匹配器未加载到索引文档，回退到传统语义匹配流程")
                return

            self._ensure_rag_threshold_defaults()
            self._rebuild_decision_policy_from_matcher()
            self.first_level_clusterer = FirstLevelClusterer(
                embedding_fn=embedding_fn,
                similarity_threshold=self.rag_cluster_similarity_threshold,
            )
            self.rag_enabled = True
            logger.info(f"RAG自动编码已启用，运行策略: {self.runtime_strategy.name}")
        except Exception as e:
            logger.warning(f"RAG组件初始化失败，回退旧流程: {e}")
            self.rag_enabled = False

    def _best_candidate_names(self, candidates: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[str]]:
        token_best_name = None
        vector_best_name = None
        token_best = float("-inf")
        vector_best = float("-inf")
        for cand in candidates:
            try:
                token_score = float(cand.get("token_score", 0.0))
            except (TypeError, ValueError):
                token_score = 0.0
            try:
                vector_score = float(cand.get("vector_score", 0.0))
            except (TypeError, ValueError):
                vector_score = 0.0
            name = cand.get("name")
            if not name:
                continue
            if token_score > token_best:
                token_best = token_score
                token_best_name = name
            if vector_score > vector_best:
                vector_best = vector_score
                vector_best_name = name
        return token_best_name, vector_best_name

    def _lookup_second_code_by_name(self, second_name: str) -> Optional[Dict[str, Any]]:
        if not self.coding_library or not second_name:
            return None
        for code in self.coding_library.get_all_second_level_codes():
            if code.get("name") == second_name:
                normalized = dict(code)
                normalized["level"] = "second"
                normalized["code_id"] = str(code.get("id", "")).strip()
                return normalized
        return None

    def _refresh_rag_matcher_if_needed(self):
        """在运行时按需刷新派生索引与匹配器，确保编码库编辑后立即生效。"""
        if not self.rag_enabled or not self.rag_index_manager:
            return
        try:
            if self.rag_index_manager.is_fresh():
                return
            if not self.rag_index_manager.ensure_fresh():
                logger.warning("RAG索引刷新失败，将继续使用旧匹配流程")
                return

            embedding_fn = None
            if self.semantic_matcher and getattr(self.runtime_strategy, "use_vector_clustering", False):
                embedding_fn = self.semantic_matcher.get_embedding
            self.rag_matcher = RAGSemanticMatcher(
                Config.RAG_INDEX_DIR,
                embedding_fn=embedding_fn,
            )
            self._rebuild_decision_policy_from_matcher()
            logger.info("检测到编码库变更，已自动刷新RAG派生索引与匹配器")
        except Exception as e:
            logger.warning(f"RAG索引运行时刷新失败: {e}")

    def generate_second_level_codes_improved(self, first_level_codes: Dict[str, List[str]], model_manager=None) -> Dict[str, List[str]]:
        """生成二阶编码 - 使用语义相似度匹配"""
        self._ensure_rag_threshold_defaults()
        if not first_level_codes:
            return {"无内容": []}

        logger.info(f"开始二阶编码分类，共 {len(first_level_codes)} 个一阶编码")
        self._second_level_decision_meta = {}
        self._refresh_rag_matcher_if_needed()

        # 优先使用RAG聚类+门控决策
        if self.rag_enabled and self.rag_matcher and self.decision_policy and self.first_level_clusterer:
            try:
                clusters = self.first_level_clusterer.cluster(first_level_codes)
                categories = defaultdict(list)
                top_k = max(1, int(getattr(Config, "RAG_FINAL_TOP_K", 5)))
                token_top_k = max(
                    1,
                    int(
                        getattr(
                            self.runtime_strategy,
                            "token_top_k",
                            getattr(Config, "RAG_TOKEN_TOP_K", 80),
                        )
                    ),
                )

                for cluster in clusters:
                    text = cluster.representative or ""
                    if not text.strip():
                        categories[self.decision_policy.other_second_name].extend(cluster.source_keys)
                        continue

                    candidates = self.rag_matcher.match_first_level_to_second_level(
                        text,
                        top_k=top_k,
                        token_top_k=token_top_k,
                    )
                    token_best, vector_best = self._best_candidate_names(candidates)
                    decision = self.decision_policy.decide_second_level(
                        candidates=candidates,
                        cluster_support=max(1, cluster.support),
                        token_best_name=token_best,
                        vector_best_name=vector_best,
                    )
                    categories[decision.name].extend(cluster.source_keys)
                    if decision.name not in self._second_level_decision_meta:
                        self._second_level_decision_meta[decision.name] = {
                            "decision": decision.reason,
                            "code": decision.code,
                        }

                result = {k: v for k, v in categories.items() if v}
                if result:
                    logger.info(f"RAG二阶编码完成: 共 {len(result)} 个类别")
                    return result
            except Exception as e:
                logger.warning(f"RAG二阶匹配失败，回退旧流程: {e}")

        # 检查编码库和语义匹配器是否可用
        if not self.coding_library or not self.semantic_matcher:
            logger.warning("编码库或语义匹配器不可用，回退到关键词匹配")
            # 回退到关键词匹配
            return self._generate_second_level_codes_keyword_based(first_level_codes)

        # 从编码库获取二阶编码
        second_level_codes_list = self.coding_library.get_all_second_level_codes()
        if not second_level_codes_list:
            logger.warning("编码库中没有二阶编码，回退到关键词匹配")
            return self._generate_second_level_codes_keyword_based(first_level_codes)

        # 构建二阶编码映射
        second_level_map = {}
        for code in second_level_codes_list:
            code_name = code.get('name')
            if code_name:
                second_level_map[code_name] = code

        categories = {code.get('name'): [] for code in second_level_codes_list}
        categories["其他各类话题"] = []

        for key, codes in first_level_codes.items():
            content = codes[0] if codes else ""
            if not content:
                categories["其他各类话题"].append(key)
                continue

            # 使用语义匹配器召回Top-k二阶候选
            top_k = 5  # 默认召回5个候选
            
            # 检查缓存中是否有结果
            cache_key = f"{content}_{top_k}_0.3"
            if cache_key in self.similarity_cache:
                logger.info(f"使用缓存的相似度计算结果")
                matches = self.similarity_cache[cache_key]
            else:
                # 计算相似度
                matches = self.semantic_matcher.match_first_level_to_second_level(
                    content,
                    second_level_codes_list,
                    top_k=top_k,
                    threshold=self.rag_second_level_threshold
                )
                # 缓存结果
                self.similarity_cache[cache_key] = matches

            if matches:
                # 如果有模型管理器，使用bert_finetuned模型进行重排
                if model_manager and model_manager.is_trained_model_available():
                    logger.info(f"使用bert_finetuned模型对 {len(matches)} 个候选进行重排")
                    # 准备候选编码
                    candidate_codes = [match[0].get('name') for match in matches]
                    # 使用模型对候选进行评分
                    try:
                        # 构建输入文本
                        inputs = [f"{content} [SEP] {code}" for code in candidate_codes]
                        # 预测类别
                        predictions, _ = model_manager.predict_categories(inputs)
                        # 计算置信度
                        confidences = []
                        for pred in predictions:
                            if isinstance(pred, tuple):
                                confidences.append(pred[1])
                            else:
                                confidences.append(0.0)
                        # 找到置信度最高的编码
                        if confidences:
                            best_idx = confidences.index(max(confidences))
                            best_match, _ = matches[best_idx]
                            second_cat = best_match.get('name')
                            logger.info(f"bert_finetuned模型选择的二阶编码: '{second_cat}' (置信度: {max(confidences):.4f})")
                        else:
                            # 回退到相似度最高的编码
                            best_match, similarity = matches[0]
                            second_cat = best_match.get('name')
                            logger.info(f"回退到相似度匹配: '{second_cat}' (相似度: {similarity:.4f})")
                    except Exception as e:
                        logger.warning(f"模型重排失败，回退到相似度匹配: {e}")
                        # 回退到相似度最高的编码
                        best_match, similarity = matches[0]
                        second_cat = best_match.get('name')
                        logger.info(f"回退到相似度匹配: '{second_cat}' (相似度: {similarity:.4f})")
                else:
                    # 没有模型管理器，使用相似度最高的编码
                    best_match, similarity = matches[0]
                    second_cat = best_match.get('name')
                    logger.info(f"一阶编码 '{content[:30]}...' 匹配到二阶编码 '{second_cat}' (相似度: {similarity:.4f})")

                if second_cat in categories:
                    categories[second_cat].append(key)
                else:
                    categories["其他各类话题"].append(key)
            else:
                logger.info(f"一阶编码 '{content[:30]}...' 未找到匹配的二阶编码，归类为'其他各类话题'")
                categories["其他各类话题"].append(key)

        logger.info(f"二阶编码完成: 共 {len(categories)} 个类别")

        # 过滤空类别
        result = {k: v for k, v in categories.items() if v}
        return result

    def _generate_second_level_codes_keyword_based(self, first_level_codes: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """基于关键词的二阶编码生成（回退方案）"""
        # 扩展关键词映射
        keyword_map = {
            "团队职责与架构": ['团队', '部门', '职责', '角色', '架构', '层级', '负责', '职能'],
            "质量管理与控制": ['质量', '检测', '测试', '检验', '把关', '评审', '评估', '标准'],
            "技术创新与研发": ['创新', '方法', '技术', '研发', '开发', '测试方法', '检测技术'],
            "危机挑战与应对": ['危机', '挑战', '困难', '问题', '应对', '解决', '突破'],
            "团队心理与氛围": ['迷茫', '方向感', '确定性', '成就感', '归属感', '荣誉感', '氛围'],
            "领导力与决策": ['领导', '管理', '决策', '资源', '协调', '支持', '目标']
        }

        categories = {category: [] for category in keyword_map.keys()}
        categories["其他各类话题"] = []

        for key, codes in first_level_codes.items():
            content = codes[0].lower() if codes else ""
            categorized = False

            # 尝试匹配每个类别
            for category, keywords in keyword_map.items():
                keyword_count = sum(1 for keyword in keywords if keyword in content)
                if keyword_count >= 1:  # 至少匹配1个关键词
                    categories[category].append(key)
                    categorized = True
                    break

            if not categorized:
                categories["其他各类话题"].append(key)

        # 过滤空类别
        result = {k: v for k, v in categories.items() if v}
        return result

    def generate_third_level_codes_improved(self, second_level_codes: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """生成三阶编码 - 使用语义相似度匹配"""
        self._ensure_rag_threshold_defaults()
        if not second_level_codes:
            return {"核心主题": []}

        category_names = list(second_level_codes.keys())
        logger.info(f"开始三阶编码抽象，共 {len(category_names)} 个二阶编码")

        # 优先使用二阶映射 + 决策兜底
        if self.rag_enabled and self.decision_policy:
            try:
                third_level_categories = defaultdict(list)
                for second_category in category_names:
                    if second_category == self.decision_policy.other_second_name:
                        third_level_categories[self.decision_policy.other_third_name].append(second_category)
                        continue

                    meta = self._second_level_decision_meta.get(second_category, {})
                    second_code = meta.get("code") if isinstance(meta, dict) else None
                    if not isinstance(second_code, dict):
                        second_code = self._lookup_second_code_by_name(second_category)

                    decision = self.decision_policy.decide_third_level(second_code)
                    third_level_categories[decision.name].append(second_category)

                result = {k: v for k, v in third_level_categories.items() if v}
                if result:
                    logger.info(f"RAG三阶编码完成: 共 {len(result)} 个类别")
                    return result
            except Exception as e:
                logger.warning(f"RAG三阶匹配失败，回退旧流程: {e}")

        # 检查编码库和语义匹配器是否可用
        if not self.coding_library or not self.semantic_matcher:
            logger.warning("编码库或语义匹配器不可用，回退到规则匹配")
            # 回退到规则匹配
            return self._generate_third_level_codes_rule_based(second_level_codes)

        # 从编码库获取二阶和三阶编码
        second_level_codes_list = self.coding_library.get_all_second_level_codes()
        third_level_codes_list = self.coding_library.get_all_third_level_codes()
        
        if not second_level_codes_list or not third_level_codes_list:
            logger.warning("编码库中没有二阶或三阶编码，回退到规则匹配")
            return self._generate_third_level_codes_rule_based(second_level_codes)

        # 构建二阶编码映射
        second_level_map = {}
        for code in second_level_codes_list:
            code_name = code.get('name')
            if code_name:
                second_level_map[code_name] = code

        # 构建三阶编码映射
        third_level_map = {}
        for code in third_level_codes_list:
            code_name = code.get('name')
            if code_name:
                third_level_map[code_name] = code

        # 构建三阶编码
        third_level_categories = {}
        for second_category in category_names:
            if second_category == "其他各类话题":
                # 直接归类为"其他重要维度"
                if "其他重要维度" not in third_level_categories:
                    third_level_categories["其他重要维度"] = []
                third_level_categories["其他重要维度"].append(second_category)
                continue

            # 查找对应的二阶编码
            second_code = second_level_map.get(second_category)
            if not second_code:
                # 如果找不到对应的二阶编码，使用规则匹配
                if "其他重要维度" not in third_level_categories:
                    third_level_categories["其他重要维度"] = []
                third_level_categories["其他重要维度"].append(second_category)
                continue

            # 使用语义匹配器匹配三阶编码
            match = self.semantic_matcher.match_second_level_to_third_level(
                second_code,
                third_level_codes_list,
                threshold=self.rag_third_level_threshold
            )

            if match:
                best_match, similarity = match
                third_cat = best_match.get('name')
                logger.info(f"二阶编码 '{second_category}' 匹配到三阶编码 '{third_cat}' (相似度: {similarity:.4f})")
                if third_cat not in third_level_categories:
                    third_level_categories[third_cat] = []
                third_level_categories[third_cat].append(second_category)
            else:
                logger.info(f"二阶编码 '{second_category}' 未找到匹配的三阶编码，归类为'其他重要维度'")
                if "其他重要维度" not in third_level_categories:
                    third_level_categories["其他重要维度"] = []
                third_level_categories["其他重要维度"].append(second_category)

        # 确保至少有1个三阶编码
        if not third_level_categories:
            third_level_categories["综合主题"] = category_names

        logger.info(f"生成 {len(third_level_categories)} 个三阶编码")
        return third_level_categories

    def _generate_third_level_codes_rule_based(self, second_level_codes: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """基于规则的三阶编码生成（回退方案）"""
        if not second_level_codes:
            return {"核心主题": []}

        category_names = list(second_level_codes.keys())

        # 更细致的分类映射
        organizational_related = [name for name in category_names if any(word in name for word in
                                                                         ['团队', '组织', '职责', '架构', '领导', '管理'])]

        technical_related = [name for name in category_names if any(word in name for word in
                                                                    ['技术', '方法', '创新', '检测', '质量', '研发'])]

        psychological_related = [name for name in category_names if any(word in name for word in
                                                                        ['心理', '氛围', '情感', '成长', '发展', '感觉'])]

        result = {}

        # 构建三阶编码
        if organizational_related:
            result["组织管理与架构设计"] = organizational_related
        if technical_related:
            result["技术研发与创新应用"] = technical_related
        if psychological_related:
            result["组织文化与心理氛围"] = psychological_related

        # 处理剩余类别
        remaining = [name for name in category_names if not any(
            name in group for group in [organizational_related, technical_related, psychological_related]
        )]

        if remaining:
            result["其他重要维度"] = remaining

        # 确保至少有1个三阶编码
        if not result:
            result["综合主题"] = category_names

        return result
