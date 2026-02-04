import re
import logging
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)


class TextNumberingManager:
    """文本编号管理器 - 为文本中的句子添加编号"""

    def __init__(self):
        self.sentence_counter = 0
        self.reset()

    def reset(self):
        """重置计数器"""
        self.sentence_counter = 0

    def number_text(self, text: str, filename: str = "") -> Tuple[str, Dict[int, str]]:
        """
        为文本中的句子添加编号

        Args:
            text: 输入文本
            filename: 文件名（用于日志记录）

        Returns:
            tuple: (编号后的文本, 编号映射字典)
        """
        if not text:
            return "", {}

        # 按句子分割文本
        sentences = self.split_into_sentences(text)

        numbered_text = ""
        number_mapping = {}

        for sentence in sentences:
            if sentence.strip():  # 忽略空句子
                self.sentence_counter += 1
                numbered_sentence = f"{sentence} [{self.sentence_counter}]"

                if numbered_text:
                    numbered_text += "\n"
                numbered_text += numbered_sentence

                # 记录编号与原文的映射关系
                number_mapping[self.sentence_counter] = sentence.strip()

        logger.info(f"为文件 {filename} 中的 {len(sentences)} 个句子进行了编号")

        return numbered_text, number_mapping

    def split_into_sentences(self, text: str) -> List[str]:
        """将文本按句子分割"""
        # 使用中文句号、问号、感叹号分割句子
        # 保留分隔符
        sentences = re.split(r'([。！？!?])', text)

        result = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]  # 添加标点符号

            # 清理句子
            sentence = sentence.strip()
            if sentence:
                result.append(sentence)

        # 处理最后一部分（如果没有标点符号结尾）
        if len(sentences) % 2 == 1:
            last_part = sentences[-1].strip()
            if last_part:
                # 添加到最后一句
                if result:
                    result[-1] += last_part
                else:
                    result.append(last_part)

        return result

    def get_current_number(self) -> int:
        """获取当前句子编号"""
        return self.sentence_counter

    def set_start_number(self, start_num: int):
        """设置起始编号"""
        self.sentence_counter = start_num - 1  # 因为每次都会+1