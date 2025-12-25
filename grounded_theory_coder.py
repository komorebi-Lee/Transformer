import logging
from typing import Dict, List, Any, Tuple
import re

logger = logging.getLogger(__name__)


class GroundedTheoryCoder:
    """扎根理论编码器 - 改进版，支持新的编号系统和导航标记"""

    def __init__(self):
        self.used_second_categories = set()
        self.used_first_contents = set()
        self.code_counter = {
            'third': 0,
            'second': {},
            'first': {}
        }

    def build_coding_structure(self, raw_codes: Dict[str, Any]) -> Dict[str, Any]:
        """构建三级编码结构并自动编号，去除重复编码"""
        try:
            # 重置计数器
            self.code_counter = {
                'third': 0,
                'second': {},
                'first': {}
            }
            self.used_second_categories.clear()
            self.used_first_contents.clear()

            structured_codes = {}

            first_level_codes = raw_codes.get("一阶编码", {})
            second_level_codes = raw_codes.get("二阶编码", {})
            third_level_codes = raw_codes.get("三阶编码", {})

            logger.info(
                f"开始构建编码结构: 一阶{len(first_level_codes)}, 二阶{len(second_level_codes)}, 三阶{len(third_level_codes)}")

            # 构建完整映射
            for third_category, second_categories in third_level_codes.items():
                structured_codes[third_category] = {}

                for second_category in second_categories:
                    if second_category in second_level_codes:
                        first_level_keys = second_level_codes[second_category]

                        first_level_contents = []
                        for key in first_level_keys:
                            if key in first_level_codes:
                                contents = first_level_codes[key]
                                if isinstance(contents, list) and len(contents) >= 5:
                                    content_str = contents[0]

                                    # 检查一阶编码是否重复
                                    if content_str not in self.used_first_contents:
                                        self.used_first_contents.add(content_str)

                                        first_level_contents.append({
                                            "content": content_str,
                                            "original_sentence": contents[1],
                                            "original_key": key,
                                            "file_count": contents[2],
                                            "sentence_count": contents[3],
                                            "sentence_details": contents[4]
                                        })

                        if first_level_contents:
                            # 检查二阶编码是否重复
                            clean_second = self.clean_category_name(second_category)
                            if clean_second not in self.used_second_categories:
                                self.used_second_categories.add(clean_second)
                                structured_codes[third_category][clean_second] = first_level_contents

            # 为编码结构自动编号
            numbered_structured_codes = self.add_coding_numbers_new_format(structured_codes)

            logger.info(f"构建了扎根理论编码结构: {len(numbered_structured_codes)}个三阶编码")
            return numbered_structured_codes

        except Exception as e:
            logger.error(f"构建编码结构失败: {e}")
            return {"错误": {"构建失败": [{"content": f"构建失败: {str(e)}", "original_sentence": "", "original_key": "error"}]}}

    def add_coding_numbers_new_format(self, structured_codes: Dict[str, Any]) -> Dict[str, Any]:
        """为编码结构添加新的自动编号格式：A, A1, A11, B, B1, B11等"""
        numbered_codes = {}

        # 三阶编码编号：A, B, C, D...
        third_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
                         'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']

        third_index = 0
        for third_category, second_categories in structured_codes.items():
            if third_index < len(third_letters):
                third_letter = third_letters[third_index]
            else:
                # 如果超过26个，使用A1, A2等格式
                third_letter = f"A{third_index - 25}"

            # 清理三阶编码名称
            clean_third = self.clean_category_name(third_category)
            numbered_third_category = f"{third_letter} {clean_third}"
            numbered_codes[numbered_third_category] = {}

            # 二阶编码编号：A1, A2, A3...
            second_categories_list = list(second_categories.items())
            for j, (second_category, first_contents) in enumerate(second_categories_list):
                second_number = j + 1
                numbered_second_category = f"{third_letter}{second_number} {self.clean_category_name(second_category)}"
                numbered_codes[numbered_third_category][numbered_second_category] = []

                # 一阶编码编号：A11, A12, A13...
                for k, first_content in enumerate(first_contents):
                    first_number = k + 1
                    code_id = f"{third_letter}{second_number}{first_number}"

                    if isinstance(first_content, dict) and 'content' in first_content:
                        # 获取原始内容（不简化）
                        original_content = first_content['content']

                        # 构建带编号的一阶编码内容 - 显示完整编号
                        numbered_first_content = f"{code_id} {original_content}"

                        # 更新原始句子，添加编号标记
                        updated_sentence_details = self.add_code_id_to_sentences(
                            first_content.get('sentence_details', []),
                            code_id
                        )

                        numbered_codes[numbered_third_category][numbered_second_category].append({
                            "numbered_content": numbered_first_content,  # 带编号的完整内容
                            "content": original_content,  # 原始内容
                            "original_sentence": first_content.get('original_sentence', ''),
                            "original_key": first_content.get('original_key', ''),
                            "code_id": code_id,
                            "file_count": first_content.get('file_count', 1),
                            "sentence_count": first_content.get('sentence_count', 1),
                            "sentence_details": updated_sentence_details
                        })

            third_index += 1

        logger.info(f"自动编号完成: 共{third_index}个三阶编码")
        return numbered_codes

    def add_coding_numbers(self, structured_codes: Dict[str, Any]) -> Dict[str, Any]:
        """为编码结构添加自动编号（兼容旧版本）"""
        return self.add_coding_numbers_new_format(structured_codes)

    def add_code_id_to_sentences(self, sentence_details: List[Dict[str, Any]], code_id: str) -> List[Dict[str, Any]]:
        """为句子详情添加编码ID标记"""
        updated_details = []

        for sentence in sentence_details:
            if isinstance(sentence, dict):
                # 在句子内容中添加编号标记
                original_content = sentence.get('content', '')
                marked_content = f"{original_content} [{code_id}]"

                updated_sentence = sentence.copy()
                updated_sentence['content'] = marked_content
                updated_sentence['code_id'] = code_id
                updated_details.append(updated_sentence)
            else:
                updated_details.append(sentence)

        return updated_details

    def clean_category_name(self, category_name: str) -> str:
        """清理类别名称，移除编号前缀"""
        # 移除所有可能的编号格式：A, A1, A11等
        cleaned = re.sub(r'^[A-Z]\d*\s*', '', category_name.strip())
        return cleaned

    def simplify_content_intelligent(self, content: str) -> str:
        """智能内容简化方法 - 保留核心信息"""
        if not content:
            return ""

        # 移除编号前缀（如果有）
        content = re.sub(r'^[A-Z]\d+\s*', '', content.strip())

        # 如果内容本身已经很简洁，直接返回
        if len(content) <= 25:
            return content

        # 移除口语词但保持内容完整
        oral_words = ['我觉得', '我认为', '我感觉', '我想', '就是说', '然后',
                      '那个', '这个', '就是', '就是說', '嗯', '啊', '对不对']

        cleaned = content
        for word in oral_words:
            cleaned = cleaned.replace(word, '')

        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # 智能截断
        if len(cleaned) > 30:
            # 在30个字符附近找合适的截断点
            for i in range(25, min(35, len(cleaned))):
                if cleaned[i] in '，。；;！!?？':
                    return cleaned[:i].strip()
            return cleaned[:30].strip() + "..."

        return cleaned

    def generate_navigation_text(self, structured_codes: Dict[str, Any], original_text: str) -> str:
        """生成带导航标记的文本"""
        try:
            navigation_text = original_text

            # 收集所有编码位置信息
            code_positions = []

            for third_cat, second_cats in structured_codes.items():
                for second_cat, first_contents in second_cats.items():
                    for content_data in first_contents:
                        if isinstance(content_data, dict):
                            code_id = content_data.get('code_id', '')
                            sentence_details = content_data.get('sentence_details', [])

                            for sentence in sentence_details:
                                if isinstance(sentence, dict):
                                    original_content = sentence.get('original_content', '')  # 原始内容（无标记）
                                    marked_content = sentence.get('content', '')  # 带标记的内容

                                    if original_content and code_id:
                                        # 在原始文本中查找并替换为带标记的内容
                                        if original_content in navigation_text:
                                            navigation_text = navigation_text.replace(
                                                original_content,
                                                marked_content
                                            )

            return navigation_text

        except Exception as e:
            logger.error(f"生成导航文本失败: {e}")
            return original_text