import logging
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
import re
import jieba
from collections import Counter, defaultdict

try:
    from config import Config
except Exception:  # pragma: no cover
    Config = None

logger = logging.getLogger(__name__)


class EnhancedCodingGenerator:
    """增强的扎根理论编码生成器 - 支持训练模型预测"""

    def __init__(self):
        self.min_sentence_length = 5
        self.similarity_threshold = 0.6
        self.max_codes_per_paragraph = 5

        self.max_first_level_length = getattr(Config, 'FIRST_LEVEL_CODE_MAX_LENGTH', 30) if Config else 30
        self.abstract_cache: Dict[str, str] = {}
        # 明显不通顺/口语残留短语，后处理时尽量清理
        self.bad_phrase_patterns = [
            r'比如说', r'这?种我', r'我这种', r'然后', r'就是说', r'那个', r'这个',
            r'还可以$', r'^不是', r'^就是', r'^所以',
            r'^这跳出来了', r'^我刚刚说的是', r'^我说的是', r'^其实',
            r'^那么', r'^然后', r'^对[，,]?', r'^我自己来说的话[，,]?',
            r'^如果说是', r'\[[0-9]+\]$', r'对对$'
        ]

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
            '嗯', '啊', '呃', '这个', '那个', '对吧', '对不对', '就是说',
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
                    if not cand:
                        continue
                    if len(cand) > target_length:
                        continue

                    # 收集候选（去重）
                    if cand not in collected_seen:
                        collected_seen.add(cand)
                        collected_candidates.append(cand)
                        collected_raw.append(built_raw)

                    s = span_score(cand, built_raw)
                    if (s > best_score) or (abs(s - best_score) < 1e-9 and len(cand) > len(best_candidate)):
                        best_score = s
                        best_candidate = cand

        compact = best_candidate or strip_punct(self._post_refine_phrase(abstracted))

        # 可选：用监督微调得到的“抽象重排序模型”在候选中再挑一次
        try:
            if Config and getattr(Config, 'ENABLE_ABSTRACT_RERANKER', False) and model_manager is not None:
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

        compact = strip_punct(compact)
        self.abstract_cache[s0] = compact
        return compact

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

    def _is_semantically_complete(self, text: str) -> bool:
        t = (text or '').strip()
        if not t:
            return False
        if len(t) < 4:
            return False
        if re.search(r'(对|怎么|会|在|到|里面|这里|这样|那样|这种|这些|那些|这类|那类)$', t):
            return False
        if re.search(r'^(因为|如果|即使|虽然|但是|不过|所以|因此|从而|然后|并且|而且|然而)$', t):
            return False
        if re.search(r'^(因为|如果|即使|虽然)', t) and not re.search(r'(所以|因此|导致|使得|从而|就|会|才)', t):
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

                # 构建一阶编码
                first_level_codes[code_key] = [
                    self.abstract_sentence(text, model_manager=model_manager),
                    [all_sentences[i]],  # source_sentences
                    1,  # file_count
                    1,  # sentence_count
                    [all_sentences[i]]  # sentence_details
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
                progress_callback(100)

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
            return self.generate_codes_with_rules(processed_data, progress_callback)

    def generate_codes_with_rules(self, processed_data: Dict[str, Any],
                                  progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
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

            # 生成一阶编码
            first_level_codes = self.generate_first_level_codes(all_sentences)
            logger.info(f"生成 {len(first_level_codes)} 个一阶编码")

            if progress_callback:
                progress_callback(60)

            # 将一阶编码分类为二阶编码
            second_level_codes = self.generate_second_level_codes_improved(first_level_codes)
            logger.info(f"生成 {len(second_level_codes)} 个二阶编码")

            if progress_callback:
                progress_callback(80)

            # 将二阶编码抽象为三阶编码
            third_level_codes = self.generate_third_level_codes_improved(second_level_codes)
            logger.info(f"生成 {len(third_level_codes)} 个三阶编码")

            if progress_callback:
                progress_callback(100)

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
            return {
                "一阶编码": {"错误": ["生成编码时出现错误"]},
                "二阶编码": {"错误": ["请检查输入文本"]},
                "三阶编码": {"错误": ["系统故障"]}
            }

    def generate_first_level_codes(self, sentences: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
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
                        self.abstract_sentence(content),
                        [sentence],  # source_sentences
                        1,  # file_count
                        1,  # sentence_count
                        [sentence]  # sentence_details
                    ]

            except Exception as e:
                logger.warning(f"处理句子失败 {i}: {e}")

        return first_level_codes

    def generate_second_level_codes_improved(self, first_level_codes: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """生成二阶编码"""
        if not first_level_codes:
            return {"无内容": []}

        logger.info(f"开始二阶编码分类，共 {len(first_level_codes)} 个一阶编码")

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

        logger.info(f"二阶编码完成: 共 {len(categories)} 个类别")

        # 过滤空类别
        result = {k: v for k, v in categories.items() if v}
        return result

    def generate_third_level_codes_improved(self, second_level_codes: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """生成三阶编码"""
        if not second_level_codes:
            return {"核心主题": []}

        category_names = list(second_level_codes.keys())
        logger.info(f"开始三阶编码抽象，共 {len(category_names)} 个二阶编码")

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

        logger.info(f"生成 {len(result)} 个三阶编码")
        return result