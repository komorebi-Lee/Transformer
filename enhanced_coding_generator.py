import logging
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
import re
import jieba
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)


class EnhancedCodingGenerator:
    """增强的扎根理论编码生成器 - 支持训练模型预测"""

    def __init__(self):
        self.min_sentence_length = 5
        self.similarity_threshold = 0.6
        self.max_codes_per_paragraph = 5

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
                    text,
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
        """生成一阶编码"""
        first_level_codes = {}

        for i, sentence in enumerate(sentences):
            try:
                content = sentence.get('content', '')
                if content and len(content.strip()) > 10:
                    code_key = f"FL_{i + 1:04d}"

                    first_level_codes[code_key] = [
                        content,
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