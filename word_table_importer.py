import os
import logging
from typing import Dict, List, Any, Optional
from docx import Document
import re

logger = logging.getLogger(__name__)


class WordTableImporter:
    """Word表格导入器 - 从Word表格导入标准答案"""

    def __init__(self):
        self.supported_formats = ['.docx']

    def import_from_word_table(self, file_path: str) -> Dict[str, Any]:
        """从Word表格导入标准答案"""
        try:
            if not file_path.endswith('.docx'):
                raise ValueError("只支持.docx格式的Word文档")

            doc = Document(file_path)
            structured_codes = {}

            # 查找表格
            for table in doc.tables:
                self._process_table(table, structured_codes)

            if not structured_codes:
                raise ValueError("未在文档中找到有效的编码表格")

            # 创建标准答案格式
            standard_answer = {
                "metadata": {
                    "version": f"imported_{os.path.basename(file_path)}",
                    "description": f"从Word表格导入: {os.path.basename(file_path)}",
                    "created_time": self.get_timestamp(),
                    "source": "word_table_import",
                    "code_statistics": self._calculate_statistics(structured_codes)
                },
                "structured_codes": structured_codes
            }

            logger.info(f"成功从Word表格导入: {len(structured_codes)}个三阶编码")
            return standard_answer

        except Exception as e:
            logger.error(f"导入Word表格失败: {e}")
            raise

    def _process_table(self, table, structured_codes: Dict[str, Any]):
        """处理单个表格"""
        # 假设表格结构：三阶编码 | 二阶编码 | 一阶编码
        for i, row in enumerate(table.rows):
            if i == 0:  # 跳过表头
                continue

            if len(row.cells) >= 3:
                third_cell = row.cells[0].text.strip()
                second_cell = row.cells[1].text.strip()
                first_cell = row.cells[2].text.strip()

                if third_cell and second_cell and first_cell:
                    # 清理编码名称
                    clean_third = self._clean_category_name(third_cell)
                    clean_second = self._clean_category_name(second_cell)
                    clean_first = self._clean_first_level_content(first_cell)

                    if clean_third not in structured_codes:
                        structured_codes[clean_third] = {}

                    if clean_second not in structured_codes[clean_third]:
                        structured_codes[clean_third][clean_second] = []

                    if clean_first not in structured_codes[clean_third][clean_second]:
                        structured_codes[clean_third][clean_second].append(clean_first)

    def _clean_category_name(self, name: str) -> str:
        """清理类别名称"""
        # 移除编号前缀如 "A1 ", "B " 等
        cleaned = re.sub(r'^[A-Z]\d*\s*', '', name.strip())
        return cleaned

    def _clean_first_level_content(self, content: str) -> str:
        """清理一阶编码内容"""
        cleaned = re.sub(r'^[A-Z]\d+\s*', '', content.strip())
        return cleaned

    def _calculate_statistics(self, structured_codes: Dict[str, Any]) -> Dict[str, Any]:
        """计算统计信息"""
        third_count = len(structured_codes)
        second_count = sum(len(categories) for categories in structured_codes.values())
        first_count = sum(
            len(contents)
            for categories in structured_codes.values()
            for contents in categories.values()
        )

        return {
            "third_level_codes": third_count,
            "second_level_codes": second_count,
            "first_level_codes": first_count,
            "total_codes": first_count
        }

    def get_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")