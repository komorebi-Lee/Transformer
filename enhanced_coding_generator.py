import logging
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
import re
import jieba
from collections import Counter, defaultdict
from coding_library_manager import CodingLibraryManager
from semantic_matcher import SemanticMatcher

logger = logging.getLogger(__name__)


class EnhancedCodingGenerator:
    """增强的扎根理论编码生成器 - 支持训练模型预测"""

    def __init__(self):
        self.min_sentence_length = 5
        self.similarity_threshold = 0.6
        self.max_codes_per_paragraph = 5
        self.coding_library = CodingLibraryManager()
        # 初始化语义匹配器，使用本地模型
        self.semantic_matcher = SemanticMatcher(model_name="sentence-transformer")
        # 缓存机制
        self.abstract_cache = {}  # 缓存抽象提炼结果
        self.keyword_map_cache = None  # 缓存关键词映射
        self.second_to_third_map_cache = None  # 缓存二阶到三阶的映射

    def generate_codes_with_trained_model(self, processed_data: Dict[str, Any],
                                          model_manager,
                                          progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """使用训练模型生成编码"""
        try:
            if progress_callback:
                progress_callback(10)

            # 提取所有句子
            all_sentences = []
            file_sentence_mapping = processed_data.get('file_sentence_mapping', {})

            for filename, file_data in file_sentence_mapping.items():
                sentences = file_data.get('sentences', [])
                all_sentences.extend(sentences)

            if progress_callback:
                progress_callback(20)

            # 提取文本内容
            texts = [sentence.get('content', '') for sentence in all_sentences]
            texts = [text for text in texts if len(text.strip()) > 10]

            if not texts:
                raise ValueError("没有找到有效的文本内容")

            if progress_callback:
                progress_callback(30)

            # 加载编码库
            second_level_codes_list = self.coding_library.get_all_second_level_codes()
            third_level_codes_list = self.coding_library.get_all_third_level_codes()

            if not second_level_codes_list or not third_level_codes_list:
                raise ValueError("编码库加载失败，请检查编码库文件")

            if progress_callback:
                progress_callback(40)

            # 构建编码结构
            first_level_codes = {}
            second_level_mapping = {}
            third_level_mapping = {}

            total_texts = len(texts)
            for i, text in enumerate(texts):
                code_key = f"FL_{i + 1:04d}"

                # 抽象提炼内容
                abstracted_content = self.abstract_sentence(text)

                # 语义匹配：一阶编码 -> 二阶编码
                matches = self.semantic_matcher.match_first_level_to_second_level(
                    abstracted_content,
                    second_level_codes_list,
                    top_k=1,
                    threshold=0.5
                )

                if matches:
                    best_match, similarity = matches[0]
                    second_cat = best_match.get('name')
                    third_cat = best_match.get('third_level')
                    logger.info(f"一阶编码 '{abstracted_content[:30]}...' 匹配到二阶编码 '{second_cat}' (相似度: {similarity:.4f})")
                else:
                    second_cat = "其他"
                    third_cat = "综合主题"
                    logger.warning(f"一阶编码 '{abstracted_content[:30]}...' 未找到匹配的二阶编码")

                # 存储映射关系
                second_level_mapping[code_key] = second_cat
                third_level_mapping[second_cat] = third_cat

                # 构建一阶编码
                # 保存原始句子，以便在添加编码标记时使用
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

                # 更新进度
                if progress_callback:
                    progress = 40 + (i + 1) / total_texts * 40
                    progress_callback(min(80, int(progress)))

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
        """生成一阶编码 - 增强版，更好地抽象提炼受访者语句"""
        first_level_codes = {}

        for i, sentence in enumerate(sentences):
            try:
                content = sentence.get('content', '')
                speaker = sentence.get('speaker', '')

                # 只处理受访者的内容
                if speaker != 'respondent':
                    continue

                if content and len(content.strip()) > 10:
                    # 抽象提炼内容
                    abstracted_content = self.abstract_sentence(content)

                    code_key = f"FL_{i + 1:04d}"

                    first_level_codes[code_key] = [
                        abstracted_content,
                        [sentence],  # source_sentences
                        1,  # file_count
                        1,  # sentence_count
                        [sentence]  # sentence_details
                    ]

            except Exception as e:
                logger.warning(f"处理句子失败 {i}: {e}")

        return first_level_codes

    def abstract_sentence(self, sentence: str) -> str:
        """抽象提炼句子内容，生成15字以下的完整主谓宾句子"""
        # 检查缓存
        if sentence in self.abstract_cache:
            return self.abstract_cache[sentence]

        # 移除说话人标记（如 B：, 答：等）
        abstracted = re.sub(r'^(?:[Bb]|答|回答|受访|被访)[:：]\s*', '', sentence)

        # 移除一阶编码标记（如 [A1], [A2] 等）
        abstracted = re.sub(r'\s*\[A\d+\]', '', abstracted)

        # 移除口语化表达
        oral_expressions = ['我觉得', '我认为', '我感觉', '我想', '就是说', '然后',
                            '那个', '这个', '就是', '就是說', '嗯', '啊', '对不对',
                            '其实', '实际上', '事实上', '总的来说', '基本上', '大概',
                            '可能', '也许', '应该', '可以', '能够', '希望', '期望']

        for expr in oral_expressions:
            abstracted = abstracted.replace(expr, '')

        # 移除重复的词语
        abstracted = re.sub(r'(\w)\1{2,}', r'\1', abstracted)

        # 移除多余的空格
        abstracted = re.sub(r'\s+', ' ', abstracted).strip()

        # 按句号分割句子
        sentences = [s.strip() for s in abstracted.split('。') if s.strip()]
        if not sentences:
            # 缓存结果
            self.abstract_cache[sentence] = abstracted
            return abstracted

        # 选择最合适的句子（优先选择包含主谓宾结构的句子）
        best_sentence = sentences[0]
        max_score = 0

        for s in sentences:
            score = self._calculate_sentence_score(s)
            if score > max_score:
                max_score = score
                best_sentence = s

        abstracted = best_sentence

        # 确保句子长度在15字以下
        max_length = 15
        while len(abstracted) > max_length:
            # 尝试提取核心主谓宾结构
            abstracted = self._extract_core_sentence(abstracted)
            # 如果仍然超过长度，直接截断
            if len(abstracted) > max_length:
                abstracted = self._truncate_to_word(abstracted, max_length - 1)  # 留一个字符给句号
        
        # 确保句子以句号结尾
        if abstracted and abstracted[-1] not in '。？！':
            abstracted += '。'
        
        # 再次检查长度，确保不超过15字
        if len(abstracted) > max_length:
            abstracted = self._truncate_to_word(abstracted, max_length - 1) + '。'

        # 去除开头的标点符号
        abstracted = abstracted.lstrip('，。？！；："\'（）【】[]{}、')

        # 确保句子以句号结尾
        if abstracted and abstracted[-1] not in '。？！':
            abstracted += '。'

        # 缓存结果
        self.abstract_cache[sentence] = abstracted

        return abstracted

    def _calculate_sentence_score(self, sentence: str) -> int:
        """计算句子得分，优先选择包含主谓宾结构的句子"""
        score = 0
        
        # 检查是否包含关键动词（谓语）
        core_verbs = ['负责', '管理', '开发', '设计', '实现', '解决', '处理',
                      '优化', '改进', '创新', '合作', '协调', '沟通',
                      '规划', '执行', '监控', '评估', '分析', '研究',
                      '建立', '构建', '创建', '制定', '实施', '推动',
                      '提升', '增强', '提高', '降低', '减少', '增加',
                      '探索', '尝试', '实践', '应用', '推广', '普及']
        
        # 检查是否包含关键名词（主语或宾语）
        core_nouns = ['团队', '部门', '项目', '任务', '工作', '职责',
                     '流程', '制度', '标准', '规范', '方法', '技术',
                     '产品', '服务', '客户', '用户', '市场', '需求',
                     '问题', '挑战', '机会', '风险', '成果', '效果']
        
        # 检查是否包含主语标识
        subjects = ['我们', '我', '公司', '团队', '部门', '企业', '组织']
        
        # 计算得分
        for verb in core_verbs:
            if verb in sentence:
                score += 3  # 动词权重最高
                break
        
        noun_count = 0
        for noun in core_nouns:
            if noun in sentence:
                noun_count += 1
        score += noun_count * 2  # 名词权重次之
        
        for subject in subjects:
            if subject in sentence:
                score += 2  # 主语权重
                break
        
        # 长度得分（优先选择中等长度的句子）
        if 8 <= len(sentence) <= 15:
            score += 3
        elif 5 <= len(sentence) < 8:
            score += 2
        elif len(sentence) < 5:
            score += 1
        
        return score

    def _extract_core_sentence(self, sentence: str) -> str:
        """提取核心主谓宾结构"""
        # 优先提取包含关键动词的部分
        core_verbs = ['负责', '管理', '开发', '设计', '实现', '解决', '处理',
                      '优化', '改进', '创新', '合作', '协调', '沟通',
                      '规划', '执行', '监控', '评估', '分析', '研究',
                      '建立', '构建', '创建', '制定', '实施', '推动',
                      '提升', '增强', '提高', '降低', '减少', '增加',
                      '探索', '尝试', '实践', '应用', '推广', '普及']
        
        for verb in core_verbs:
            if verb in sentence:
                # 找到动词位置
                verb_index = sentence.find(verb)
                
                # 向前查找主语（寻找最近的名词或主语标识）
                subjects = ['我们', '我', '公司', '团队', '部门', '企业', '组织']
                start = 0
                for i in range(verb_index - 1, -1, -1):
                    if sentence[i] in '，。？！；：':
                        start = i + 1
                        break
                
                # 检查主语
                subject_found = False
                subject_start = start
                for subject in subjects:
                    if subject in sentence[start:verb_index]:
                        subject_found = True
                        subject_start = sentence.find(subject, start, verb_index)
                        break
                
                if not subject_found:
                    # 尝试找到名词作为主语
                    core_nouns = ['团队', '部门', '项目', '任务', '工作', '职责',
                                 '流程', '制度', '标准', '规范', '方法', '技术',
                                 '产品', '服务', '客户', '用户', '市场', '需求']
                    for noun in core_nouns:
                        if noun in sentence[start:verb_index]:
                            subject_found = True
                            subject_start = sentence.find(noun, start, verb_index)
                            break
                
                # 向后查找宾语
                end = len(sentence)
                for i in range(verb_index + len(verb), len(sentence)):
                    if sentence[i] in '，。？！；：':
                        end = i
                        break
                
                # 提取主谓宾结构
                core = sentence[subject_start:end].strip()
                if core:
                    # 确保长度不超过15字
                    if len(core) > 15:
                        # 尝试进一步简化
                        # 只保留主语和谓语，或者主语+谓语+简单宾语
                        # 找到第一个宾语
                        obj_start = verb_index + len(verb)
                        obj_end = end
                        for i in range(obj_start, end):
                            if sentence[i] in '，。？！；：':
                                obj_end = i
                                break
                        
                        # 尝试构建更简洁的句子
                        simple_core = sentence[subject_start:obj_end].strip()
                        if len(simple_core) <= 14:
                            return simple_core
                        else:
                            # 只保留主语和谓语
                            return sentence[subject_start:verb_index + len(verb)].strip()
                    return core
        
        # 如果没有找到关键动词，返回原句的前15字
        return self._truncate_to_word(sentence, 15)

    def _truncate_to_word(self, text: str, max_length: int) -> str:
        """截断文本到指定长度，确保是完整的词语"""
        if len(text) <= max_length:
            return text
        
        # 从开头截取到指定长度
        truncated = text[:max_length]
        
        # 找到最后一个完整的词语边界
        punctuation = '，。？！；："\'（）【】[]{}、'
        for i in range(len(truncated) - 1, -1, -1):
            if truncated[i] in punctuation:
                # 去除结尾的逗号
                if truncated[i] == '，':
                    return truncated[:i].strip()
                return truncated[:i+1].strip()
        
        # 如果没有标点，尝试找到最后一个词语的边界
        # 检查最后一个字符是否是汉字
        if truncated and '一' <= truncated[-1] <= '鿿':
            return truncated.strip()
        
        # 尝试向前查找词语边界
        for i in range(len(truncated) - 1, -1, -1):
            if '一' <= truncated[i] <= '鿿':
                return truncated[:i+1].strip()
        
        # 如果都不行，返回截断的文本
        return truncated.strip()

    def generate_second_level_codes_improved(self, first_level_codes: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """生成二阶编码"""
        if not first_level_codes:
            return {"无内容": []}

        logger.info(f"开始二阶编码分类，共 {len(first_level_codes)} 个一阶编码")

        # 检查缓存
        if self.keyword_map_cache is None:
            # 从编码库获取二阶编码信息
            second_level_codes_list = self.coding_library.get_all_second_level_codes()
            
            # 构建基于编码库的关键词映射
            keyword_map = {}
            for code in second_level_codes_list:
                code_name = code.get('name')
                code_desc = code.get('description', '')
                # 提取关键词：从名称和描述中提取
                keywords = []
                # 添加名称中的关键词
                if code_name:
                    keywords.extend([code_name])
                # 添加描述中的关键词
                if code_desc:
                    # 简单分词，提取主要词汇
                    words = jieba.cut(code_desc)
                    keywords.extend([word for word in words if len(word) > 1])
                # 去重
                keywords = list(set(keywords))
                if code_name and keywords:
                    keyword_map[code_name] = keywords

            # 保留原有的关键词映射作为 fallback
            if not keyword_map:
                keyword_map = {
                    "团队职责与架构": ['团队', '部门', '职责', '角色', '架构', '层级', '负责', '职能'],
                    "质量管理与控制": ['质量', '检测', '测试', '检验', '把关', '评审', '评估', '标准'],
                    "技术创新与研发": ['创新', '方法', '技术', '研发', '开发', '测试方法', '检测技术'],
                    "危机挑战与应对": ['危机', '挑战', '困难', '问题', '应对', '解决', '突破'],
                    "团队心理与氛围": ['迷茫', '方向感', '确定性', '成就感', '归属感', '荣誉感', '氛围'],
                    "领导力与决策": ['领导', '管理', '决策', '资源', '协调', '支持', '目标']
                }
            
            # 缓存关键词映射
            self.keyword_map_cache = keyword_map
        else:
            keyword_map = self.keyword_map_cache

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

        # 检查缓存
        if self.second_to_third_map_cache is None:
            # 从编码库获取二阶到三阶的映射
            second_level_codes_list = self.coding_library.get_all_second_level_codes()
            second_to_third_map = {}
            for code in second_level_codes_list:
                code_name = code.get('name')
                third_level = code.get('third_level')
                if code_name and third_level:
                    second_to_third_map[code_name] = third_level
            
            # 缓存二阶到三阶的映射
            self.second_to_third_map_cache = second_to_third_map
        else:
            second_to_third_map = self.second_to_third_map_cache

        # 构建三阶编码映射
        third_level_categories = {}
        for second_category in category_names:
            if second_category in second_to_third_map:
                third_category = second_to_third_map[second_category]
            else:
                # 如果编码库中没有映射，使用原有的逻辑
                if any(word in second_category for word in ['团队', '组织', '职责', '架构', '领导', '管理']):
                    third_category = "组织管理与架构设计"
                elif any(word in second_category for word in ['技术', '方法', '创新', '检测', '质量', '研发']):
                    third_category = "技术研发与创新应用"
                elif any(word in second_category for word in ['心理', '氛围', '情感', '成长', '发展', '感觉']):
                    third_category = "组织文化与心理氛围"
                else:
                    third_category = "其他重要维度"
            
            if third_category not in third_level_categories:
                third_level_categories[third_category] = []
            third_level_categories[third_category].append(second_category)

        # 确保至少有1个三阶编码
        if not third_level_categories:
            third_level_categories["综合主题"] = category_names

        logger.info(f"生成 {len(third_level_categories)} 个三阶编码")
        return third_level_categories