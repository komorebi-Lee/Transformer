import logging
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
import re
import jieba
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


class EnhancedCodingGenerator:
    """增强的扎根理论编码生成器 - 支持训练模型预测"""

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
        self._second_level_decision_meta: Dict[str, Dict[str, Any]] = {}
        self._init_rag_components()

    def abstract_sentence(self, sentence: str, model_manager=None) -> str:
        """抽象提炼句子内容：优先输出连续、语义完整的片段；可配置长度上限。"""
        # 兼容通过 __new__ 构造的测试调用，补齐必要默认属性
        if not hasattr(self, 'abstract_cache'):
            self.abstract_cache = {}
        if not hasattr(self, 'max_first_level_length'):
            self.max_first_level_length = getattr(Config, 'FIRST_LEVEL_CODE_MAX_LENGTH', 30) if Config else 30
        if not hasattr(self, 'bad_phrase_patterns'):
            self.bad_phrase_patterns = [
                r'比如说', r'这?种我', r'我这种', r'然后', r'就是说', r'那个', r'这个',
                r'还可以$', r'^不是', r'^就是', r'^所以',
                r'^这跳出来了', r'^我刚刚说的是', r'^我说的是', r'^其实',
                r'^那么', r'^然后', r'^对[，,]?', r'^我自己来说的话[，,]?',
                r'^如果说是', r'\[[0-9]+\]$', r'对对$'
            ]

        s0 = (sentence or '').strip()
        if not s0:
            return ''

        if s0 in self.abstract_cache:
            return self.abstract_cache[s0]

        # 安全上限：避免极端超长段落
        target_length = getattr(Config, 'MAX_SENTENCE_LENGTH', 512) if Config else 512

        # 移除说话人标记（如 B：, 答：等）
        abstracted = re.sub(r'^(?:[Bb]|答|回答|受访|被访)[:：]\s*', '', s0)
        # 移除一阶编码标记（如 [A1], [A2] 等）
        abstracted = re.sub(r'\s*[\[［【]A\d+[\]］】]', '', abstracted)

        # 温和去口语：只去掉明显语气词，保留关键语义词
        oral_expressions = [
            '嗯', '啊', '呃', '对吧', '对不对', '就是说',
            '然后呢', '总的来说', '某种程度上', '某种意义上',
            '我觉得', '我认为', '我感觉', '其实', '比如说'
        ]
        for expr in oral_expressions:
            abstracted = abstracted.replace(expr, ' ')

        # 常见口语错序与残句规整
        normalize_map = {
            '如果在是我': '如果是我',
            '如果在我': '如果我',
            '在是': '是',
            '百分之八九十': '80%-90%',
            '百分之九十': '90%',
        }
        for k, v in normalize_map.items():
            abstracted = abstracted.replace(k, v)

        abstracted = re.sub(r'(\w)\1{2,}', r'\1', abstracted)
        abstracted = re.sub(r'\s+', ' ', abstracted).strip()
        abstracted = self._normalize_source_sentence(abstracted)

        if not abstracted:
            self.abstract_cache[s0] = ''
            return ''

        max_len = getattr(self, 'max_first_level_length', getattr(Config, 'FIRST_LEVEL_CODE_MAX_LENGTH', 30) if Config else 30)
        length_budget = max_len if isinstance(max_len, int) and max_len > 0 else None

        def strip_punct(t: str) -> str:
            return (t or '').lstrip('，。？！；:"\'（）【】[]{}、').rstrip('，。？！；:"\'（）【】[]{}、')

        def looks_like_fragment(raw_span: str, cleaned_span: str) -> bool:
            raw = (raw_span or '').strip()
            c = (cleaned_span or '').strip()
            if not c:
                return True

            if re.search(r'^(因为|如果|即使|虽然|但是|不过|所以|因此|从而|然后|并且|而且|然而)', raw) or \
               re.search(r'^(因为|如果|即使|虽然|但是|不过|所以|因此|从而|然后|并且|而且|然而)', c):
                if ('，' not in c) and not re.search(r'(就|会|才|是|有|要|能|可以|需要|导致|使得|影响|说明|认为)', c):
                    return True

            if re.search(r'(对|怎么|会|在|到|里面|这里|这样|那样|这种|这些|那些|这类|那类)$', c):
                return True

            if len(c) <= 5 and not re.search(r'(影响|结果|标准|流程|审批|项目|销售|流量|资源|协同)', c):
                return True

            return False

        def span_score(cleaned_span: str, raw_span: str) -> float:
            c = cleaned_span or ''
            score = 0.0

            # 基础信息量：有动词/结构词加分
            if re.search(r'(影响|导致|使得|需要|可以|应当|应该|必须|难以|容易|提升|优化|推进|执行|协调|限制|支持)', c):
                score += 2.0
            if re.search(r'(项目|团队|部门|质量|标准|流程|审批|资源|流量|销售|客户|市场|实验|说明书|规程)', c):
                score += 1.5

            if self._is_semantically_complete(c):
                score += 6.0
            else:
                score -= 2.0

            if looks_like_fragment(raw_span, c):
                score -= 7.0

            if self._is_question_like(raw_span) or self._is_question_like(c):
                score -= 6.0

            # 低信息口语/犹豫表达惩罚
            if re.search(r'(不太清楚|不知道|不确定|可能|也许|好像|大概|说不好|不一定)', c):
                score -= 4.0
            if re.search(r'(还可以|还好|差不多|一般般?|就那样|也行)', c):
                score -= 3.0

            # 业务动作、限制、后果、频度信号加分
            if re.search(r'(只能|不得不|被迫|受影响|影响|导致|拖慢|拖延|卡在|推进|上线|返工|协调|协同|审批|资源|客户|催促|催|借用)', c):
                score += 2.5
            if re.search(r'(经常|反复|一直|总是|每次|频繁)', c):
                score += 1.2

            if re.search(r'^(没想过|可能没有|可能有|不知道|不清楚|算不算|有时候|大概|也许)', c):
                score -= 3.0

            if length_budget is not None:
                over = max(0, len(c) - length_budget)
                score -= over * 0.25

            score += min(len(c), 80) / 80.0
            return score

        # 先按句末标点切“句”
        sentences = [p.strip() for p in re.split(r'[。！？；;]', abstracted) if p.strip()]
        if not sentences:
            sentences = [abstracted]

        best_candidate = ''
        best_score = -1e18
        max_span_len = 8

        # 收集候选，便于可选的模型重排序
        collected_candidates: List[str] = []
        collected_raw: List[str] = []
        collected_seen = set()

        for sent in sentences:
            sent0 = strip_punct(sent)
            if not sent0:
                continue

            micro = [p.strip() for p in re.split(r'[，,、]', sent0) if p.strip()]
            if not micro:
                micro = [sent0]

            for i in range(len(micro)):
                built_raw = ''
                for j in range(i, min(len(micro), i + max_span_len)):
                    built_raw = micro[j] if not built_raw else f"{built_raw}，{micro[j]}"
                    if not built_raw:
                        continue

                    cand = strip_punct(self._post_refine_phrase(built_raw))
                    variants = []
                    if cand:
                        variants.append(cand)
                    normalized_cand = self._normalize_candidate_for_first_level(cand)
                    if normalized_cand and normalized_cand not in variants:
                        variants.append(normalized_cand)

                    for variant in variants:
                        if not variant:
                            continue
                        if len(variant) > target_length:
                            continue

                        # 收集候选（去重）
                        if variant not in collected_seen:
                            collected_seen.add(variant)
                            collected_candidates.append(variant)
                            collected_raw.append(built_raw)

                        s = span_score(variant, built_raw)
                        if (s > best_score) or (abs(s - best_score) < 1e-9 and len(variant) > len(best_candidate)):
                            best_score = s
                            best_candidate = variant

        compact = best_candidate or strip_punct(self._post_refine_phrase(abstracted))
        compact = self._normalize_candidate_for_first_level(compact)

        # 可选：用监督微调得到的“抽象重排序模型”在候选中再挑一次
        try:
            if Config and getattr(Config, 'ENABLE_ABSTRACT_RERANKER', False) and model_manager is not None:
                # 兜底：若启用但还没加载，尝试一次懒加载（只尝试一次，避免循环卡顿）
                if hasattr(model_manager, 'ensure_abstract_reranker_loaded'):
                    model_manager.ensure_abstract_reranker_loaded()
                if hasattr(model_manager, 'is_abstract_reranker_available') and model_manager.is_abstract_reranker_available():
                    # 过滤明显碎片候选，减少模型被“半句”干扰
                    filtered = []
                    for raw, cand in zip(collected_raw, collected_candidates):
                        if not cand:
                            continue
                        if len(cand) > target_length:
                            continue
                        if looks_like_fragment(raw, cand):
                            continue
                        filtered.append(cand)

                    if filtered:
                        scores = model_manager.score_abstract_candidates(abstracted, filtered)
                        if scores and len(scores) == len(filtered):
                            best_i = int(max(range(len(scores)), key=lambda i: scores[i]))
                            picked = filtered[best_i]
                            if picked:
                                compact = picked
        except Exception:
            # 模型可用性/推理失败时不影响规则抽取流程
            pass

        # 若仍不完整，尝试从更短、更完整的片段中挑一个
        if compact and not self._is_semantically_complete(compact):
            alt = self._limit_first_level_text(compact, 60)
            if alt and self._is_semantically_complete(alt):
                compact = alt

        # 最终长度限制：仅在启用长度限制时生效
        if length_budget is not None and compact and len(compact) > length_budget:
            limited = self._limit_first_level_text(compact, length_budget)
            if limited:
                compact = limited

        compact = self._normalize_candidate_for_first_level(strip_punct(compact))
        self.abstract_cache[s0] = compact
        return compact

    def _normalize_source_sentence(self, text: str) -> str:
        normalized = str(text or "").strip()
        if not normalized:
            return ""

        normalized = re.sub(r'^[，。？！；、,\.\?!;:\s]+', '', normalized)
        normalized = re.sub(r'(?:\s*[?？]+)$', '。', normalized)
        normalized = re.sub(r'(?:\s*[!！]+)$', '。', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.strip()

    def _post_refine_phrase(self, text: str) -> str:
        refined = (text or '')
        for p in getattr(self, 'bad_phrase_patterns', []):
            refined = re.sub(p, '', refined)

        refined = re.sub(r'^(因此|所以|然后|并且|而且|那么|其实)+', '', refined)
        refined = re.sub(r'(因此|所以|然后|并且|而且)+$', '', refined)
        refined = re.sub(r'^说(?=[\u4e00-\u9fa5])', '', refined)

        # 清理开头“这个/那个/它”等弱指代；避免误伤“这种/这些/那样”
        refined = re.sub(r'^(这个|那个|它)(?=[\u4e00-\u9fa5])', '', refined)
        refined = re.sub(r'^(这|那)(?![种些样类])(?=[\u4e00-\u9fa5])', '', refined)

        refined = re.sub(r'\s+', '', refined)
        refined = refined.strip('，。？！；:"\'（）【】[]{}、')
        return refined

    def _is_question_like(self, text: str) -> bool:
        t = str(text or "").strip()
        if not t:
            return False
        return bool(
            re.search(r'[?？吗呢么]$', t)
            or re.search(r'(是不是|是否|能不能|可不可以|会不会|有没有|要不要)', t)
            or re.search(r'^(为什么|怎么|咋|如何|哪|谁)', t)
        )

    def _normalize_candidate_for_first_level(self, text: str) -> str:
        refined = str(text or '').strip()
        if not refined:
            return ''

        refined = re.sub(r'^(你说|你看|如果说|如果|要是|假如|其实|但是|不过|所以|因此|然后|并且|而且|那么|不然)+', '', refined)
        refined = re.sub(r'^(这个流程|这个问题|这件事|这个事情|这个情况)', '', refined)
        refined = re.sub(r'，?(所以|因此|然后|不过|但是)', '，', refined)
        refined = re.sub(r'(是不是|是否)', '', refined)
        refined = re.sub(r'(能不能|可不可以|会不会|有没有|要不要)', '', refined)
        refined = re.sub(r'^(为什么|怎么|咋)', '', refined)
        refined = re.sub(r'的话', '', refined)
        refined = re.sub(r'的时候', '', refined)
        refined = re.sub(r'每次都', '经常', refined)
        refined = re.sub(r'这里$', '', refined)
        refined = re.sub(r'了(?=$|[，。？！；、])', '', refined)
        refined = re.sub(r'(就很受影响|很受影响)', '受影响', refined)
        refined = re.sub(r'我们就只能', '只能', refined)
        refined = re.sub(r'我们只能', '只能', refined)
        refined = re.sub(r'我们就', '', refined)
        refined = re.sub(r'我们', '', refined)
        refined = re.sub(r'只能先', '只能', refined)
        refined = re.sub(r'先上线再修', '先上线后修', refined)
        refined = re.sub(r'一直催', '催促', refined)
        refined = re.sub(r'不够', '不足', refined)
        refined = re.sub(r'太慢', '过慢', refined)
        refined = re.sub(r'别的组的设备', '别组设备', refined)
        refined = re.sub(r'借别组设备来做', '借用别组设备', refined)
        refined = re.sub(r'借别组设备', '借用别组设备', refined)
        refined = re.sub(r'来做$', '', refined)

        impact_match = re.match(r'^(.+?)，(.+?)受影响$', refined)
        if impact_match:
            left = impact_match.group(1).strip('，。？！；、')
            right = impact_match.group(2).strip('，。？！；、')
            if left and right:
                refined = f"{left}影响{right}"

        refined = re.sub(r'\s+', '', refined)
        refined = refined.strip('，。？！；:"\'（）【】[]{}、')
        return refined

    def _is_semantically_complete(self, text: str) -> bool:
        t = (text or '').strip()
        if not t:
            return False
        if len(t) < 4:
            return False
        if self._is_question_like(t):
            return False
        if re.search(r'(对|怎么|会|在|到|里面|这里|这样|那样|这种|这些|那些|这类|那类)$', t):
            return False
        if re.search(r'^(因为|如果|即使|虽然|但是|不过|所以|因此|从而|然后|并且|而且|然而)$', t):
            return False
        if re.search(r'^(因为|如果|即使|虽然)', t) and not re.search(r'(所以|因此|导致|使得|从而|就|会|才)', t):
            return False
        if re.search(r'^(我|我们|你|你们)(也)?(不太清楚|不知道|不确定|说不好)', t):
            return False
        if re.search(r'^(还可以|还好|差不多|一般般?)$', t):
            return False
        return True

    def _truncate_to_word(self, text: str, max_length: int) -> str:
        t = (text or '').strip()
        if max_length <= 0 or len(t) <= max_length:
            return t

        cut = t[:max_length].rstrip('，。？！；:"\'（）【】[]{}、')
        # 避免截到“挂尾词/连接词”
        for _ in range(6):
            if not cut:
                break
            if re.search(r'(对|怎么|会|在|到|里面|这里|这样|那样|这种|这些|那些|这类|那类)$', cut):
                cut = cut[:-1]
                continue
            if re.search(r'(因为|如果|即使|虽然|但是|不过|所以|因此|从而|然后|并且|而且|然而)$', cut):
                cut = cut[:-1]
                continue
            break
        return cut.strip('，。？！；:"\'（）【】[]{}、')

    def _limit_first_level_text(self, text: str, max_length: int) -> str:
        t = (text or '').strip()
        if not t:
            return ''
        if max_length <= 0:
            return t
        if len(t) <= max_length:
            return t

        parts = [p.strip() for p in re.split(r'[，,、]', t) if p.strip()]
        if not parts:
            return self._truncate_to_word(t, max_length)

        best = ''
        for i in range(len(parts)):
            built = ''
            for j in range(i, len(parts)):
                built = parts[j] if not built else f"{built}，{parts[j]}"
                if len(built) > max_length:
                    break
                cand = built.strip('，。？！；:"\'（）【】[]{}、')
                if not cand:
                    continue
                if self._is_semantically_complete(cand):
                    if len(cand) > len(best):
                        best = cand

        if best:
            return best
        return self._truncate_to_word(t, max_length)

    def generate_codes_with_trained_model(self, processed_data: Dict[str, Any],
                                          model_manager,
                                          progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
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
            filtered_sentences = []
            texts = []
            for sent in all_sentences:
                t = (sent.get('content', '') or '').strip()
                if len(t) > 10:
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

            for i, (text, label) in enumerate(zip(texts, predicted_labels)):
                code_key = f"FL_{i + 1:04d}"

                # 构建一阶编码
                abstracted = self.abstract_sentence(text, model_manager=model_manager)
                first_level_codes[code_key] = [
                    abstracted,
                    [filtered_sentences[i]],  # source_sentences
                    1,  # file_count
                    1,  # sentence_count
                    [filtered_sentences[i]]  # sentence_details
                ]

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
                            threshold=0.3  # 降低阈值以确保召回足够的候选
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
                            threshold=0.5
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
                                                   use_trained_model: bool = False) -> Dict[str, Any]:
        """为多个文件生成扎根理论三级编码"""
        if use_trained_model and model_manager.is_trained_model_available():
            return self.generate_codes_with_trained_model(processed_data, model_manager, progress_callback)
        else:
            # 使用原有的基于规则的编码生成
            return self.generate_codes_with_rules(processed_data, progress_callback, model_manager=model_manager)

    def generate_codes_with_rules(self, processed_data: Dict[str, Any],
                                  progress_callback: Optional[Callable] = None,
                                  model_manager=None) -> Dict[str, Any]:
        """使用基于规则的编码生成"""
        try:
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
            first_level_codes = self.generate_first_level_codes(all_sentences, model_manager=model_manager)
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

    def generate_first_level_codes(self, sentences: List[Dict[str, Any]], model_manager=None) -> Dict[str, List[Any]]:
        """生成一阶编码 - 优先抽象提炼受访者语句"""
        first_level_codes = {}

        for i, sentence in enumerate(sentences):
            try:
                content = sentence.get('content', '')
                speaker = sentence.get('speaker', '')

                # 如果存在说话人字段，则只处理受访者内容；否则默认处理
                if speaker and speaker != 'respondent':
                    continue
                if content and len(content.strip()) > 10:
                    code_key = f"FL_{i + 1:04d}"

                    first_level_codes[code_key] = [
                        self.abstract_sentence(content, model_manager=model_manager),
                        [sentence],  # source_sentences
                        1,  # file_count
                        1,  # sentence_count
                        [sentence]  # sentence_details
                    ]

            except Exception as e:
                logger.warning(f"处理句子失败 {i}: {e}")

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

            second_name_map = self.rag_matcher.second_code_name_map()
            third_name_map = self.rag_matcher.third_level_name_map()
            self.decision_policy = CodingDecisionPolicy(
                allowed_second_code_ids=list(second_name_map.keys()),
                allowed_third_level_ids=list(third_name_map.keys()),
                allowed_second_code_names=second_name_map,
                allowed_third_level_names=third_name_map,
            )
            self.first_level_clusterer = FirstLevelClusterer(
                embedding_fn=embedding_fn,
                similarity_threshold=getattr(Config, "RAG_CLUSTER_SIMILARITY_THRESHOLD", 0.82),
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
            second_name_map = self.rag_matcher.second_code_name_map() if self.rag_matcher else {}
            third_name_map = self.rag_matcher.third_level_name_map() if self.rag_matcher else {}
            self.decision_policy = CodingDecisionPolicy(
                allowed_second_code_ids=list(second_name_map.keys()),
                allowed_third_level_ids=list(third_name_map.keys()),
                allowed_second_code_names=second_name_map,
                allowed_third_level_names=third_name_map,
            )
            logger.info("检测到编码库变更，已自动刷新RAG派生索引与匹配器")
        except Exception as e:
            logger.warning(f"RAG索引运行时刷新失败: {e}")

    def generate_second_level_codes_improved(self, first_level_codes: Dict[str, List[str]], model_manager=None) -> Dict[str, List[str]]:
        """生成二阶编码 - 使用语义相似度匹配"""
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
                    threshold=0.3  # 降低阈值以确保召回足够的候选
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
                threshold=0.5
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
