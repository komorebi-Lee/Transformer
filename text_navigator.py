import logging
from typing import Dict, List, Any, Optional
import re

logger = logging.getLogger(__name__)


class TextNavigator:
    """文本导航器 - 改进版，支持多文件编号导航"""

    def __init__(self):
        self.original_texts = {}  # 文件名 -> 原始文本
        self.numbered_texts = {}  # 文件名 -> 带编号文本
        self.sentence_mapping = {}  # 编号到原始句子的映射
        self.code_to_sentences = {}  # 编码ID到所有句子的映射

    def set_text(self, filename: str, text: str):
        """设置原始文本"""
        self.original_texts[filename] = text

    def set_numbered_text(self, filename: str, numbered_text: str):
        """设置带编号的文本"""
        self.numbered_texts[filename] = numbered_text

    def map_codes_to_text(self, structured_codes: Dict[str, Any]):
        """建立编码到文本的映射"""
        try:
            self.sentence_mapping = {}
            self.code_to_sentences = {}

            for third_category, second_categories in structured_codes.items():
                for second_category, first_contents in second_categories.items():
                    for content_data in first_contents:
                        if isinstance(content_data, dict) and "code_id" in content_data:
                            code_id = content_data["code_id"]
                            sentence_details = content_data.get("sentence_details", [])

                            # 存储所有句子详情
                            self.code_to_sentences[code_id] = sentence_details

                            # 存储第一个句子用于导航
                            if sentence_details:
                                first_sentence = sentence_details[0]
                                self.sentence_mapping[code_id] = {
                                    'content': first_sentence.get('content', ''),
                                    'filename': first_sentence.get('filename', ''),
                                    'line_number': first_sentence.get('line_number', 0)
                                }

            logger.info(f"建立了 {len(self.sentence_mapping)} 个编码的文本映射")

        except Exception as e:
            logger.error(f"建立编码映射失败: {e}")

    def navigate_to_code(self, code_id: str) -> Optional[tuple]:
        """导航到指定编码ID的位置"""
        try:
            if code_id not in self.sentence_mapping:
                logger.warning(f"未找到编码 {code_id} 的映射")
                return None

            sentence_info = self.sentence_mapping[code_id]
            filename = sentence_info['filename']
            content = sentence_info['content']

            if filename not in self.numbered_texts:
                logger.warning(f"未找到文件 {filename} 的编号文本")
                return None

            numbered_text = self.numbered_texts[filename]

            # 在带编号的文本中查找编码ID
            pattern = f"\\[{code_id}\\]"
            match = re.search(pattern, numbered_text)

            if match:
                start_pos = match.start()
                end_pos = match.end()
                logger.info(f"导航到编码 {code_id} 的位置: {start_pos}-{end_pos}")
                return (start_pos, end_pos, filename)
            else:
                # 如果没有编号，尝试直接搜索内容
                if content and content in numbered_text:
                    start_pos = numbered_text.find(content)
                    end_pos = start_pos + len(content)
                    return (start_pos, end_pos, filename)

            logger.warning(f"未找到编码 {code_id} 的位置")
            return None

        except Exception as e:
            logger.error(f"导航到编码失败: {e}")
            return None

    def get_sentences_by_code_id(self, code_id: str) -> List[Dict[str, Any]]:
        """根据编码ID获取所有原始句子"""
        return self.code_to_sentences.get(code_id, [])

    def get_text_by_filename(self, filename: str) -> Optional[str]:
        """根据文件名获取文本"""
        return self.numbered_texts.get(filename)