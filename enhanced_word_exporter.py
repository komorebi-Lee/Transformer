import os
import logging
from typing import Dict, List, Any
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)


class EnhancedWordExporter:
    """增强的Word文档导出器 - 支持新的编号系统和超链接"""

    def __init__(self):
        self.document = None

    def export_structured_codes_with_hyperlinks(self, file_path: str,
                                                structured_codes: Dict[str, Any],
                                                combined_text: str,
                                                text_mapping: Dict[str, Any]) -> bool:
        """导出编码结构到Word文档，包含超链接和编号系统"""
        try:
            self.document = Document()

            # 设置文档属性
            self.document.core_properties.title = "扎根理论编码分析结果"
            self.document.core_properties.author = "扎根理论编码分析系统"
            self.document.core_properties.comments = "自动生成的扎根理论三级编码分析报告"

            # 添加标题
            title = self.document.add_heading('扎根理论编码分析结果', 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER

            # 添加导出信息
            self.document.add_paragraph(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # 统计编码数量
            total_third = len(structured_codes)
            total_second = sum(len(categories) for categories in structured_codes.values())
            total_first = sum(len(contents) for categories in structured_codes.values()
                              for contents in categories.values())

            self.document.add_paragraph(f"三阶编码数量: {total_third}")
            self.document.add_paragraph(f"二阶编码数量: {total_second}")
            self.document.add_paragraph(f"一阶编码数量: {total_first}")

            self.document.add_paragraph()  # 空行

            # 根据合并文本和句子来源构建文件顺序与一阶编码显示编号映射
            file_index_map = self._build_file_index_map_from_combined_text(combined_text)
            code_display_map = self._build_first_level_display_id_map(structured_codes, file_index_map)

            # 第一部分：三级编码表格
            self.add_coding_table_with_new_format(structured_codes, code_display_map)

            # 分页
            self.document.add_page_break()

            # 第二部分：合并文本与引用
            self.add_combined_text_with_numbered_references(combined_text, structured_codes, code_display_map)

            # 保存文档
            self.document.save(file_path)
            logger.info(f"Word文档已导出: {file_path}")
            return True

        except Exception as e:
            logger.error(f"导出Word文档失败: {e}")
            return False

    def add_coding_table_with_new_format(self, structured_codes: Dict[str, Any], code_display_map: Dict[str, str] = None):
        """添加编码表格 - 新编号格式"""
        if code_display_map is None:
            code_display_map = {}
        # 添加标题
        heading = self.document.add_heading('一、三级编码结构', level=1)

        # 创建表格
        table = self.document.add_table(rows=1, cols=3)
        table.style = 'Light Grid Accent 1'

        # 设置表头
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = '三阶编码'
        hdr_cells[1].text = '二阶编码'
        hdr_cells[2].text = '一阶编码'

        # 设置表头格式
        for cell in hdr_cells:
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    run.font.bold = True

        # 填充数据
        for third_category, second_categories in structured_codes.items():
            for second_category, first_contents in second_categories.items():
                for content_data in first_contents:
                    # 添加新行
                    row_cells = table.add_row().cells

                    # 三阶编码（只显示一次，避免重复）
                    row_cells[0].text = third_category

                    # 二阶编码（只显示一次，避免重复）
                    row_cells[1].text = second_category

                    display_text = ""
                    code_id = ""

                    # 一阶编码显示内容：使用新的 Ax-xx 格式 + 纯文本内容
                    if isinstance(content_data, dict):
                        code_id = content_data.get('code_id', '')
                        base_content = content_data.get('content', '') or content_data.get('numbered_content', '')
                        clean_content = self.clean_first_level_content(base_content) if base_content else ''

                        display_id = code_display_map.get(code_id, code_id)

                        if display_id and clean_content:
                            display_text = f"{display_id} {clean_content}"
                        elif base_content:
                            display_text = base_content
                        else:
                            display_text = content_data.get('numbered_content', '') or ''
                    else:
                        display_text = str(content_data)

                    row_cells[2].text = display_text

                    # 如果有编码ID，添加书签（仍然使用原始 code_id 作为锚点）
                    if code_id:
                        self.add_bookmark_to_paragraph(row_cells[2].paragraphs[0], f"code_{code_id}")

    def add_combined_text_with_numbered_references(self, combined_text: str,
                                                   structured_codes: Dict[str, Any],
                                                   code_display_map: Dict[str, str] = None):
        """添加合并文本和编号引用"""
        if code_display_map is None:
            code_display_map = {}
        # 添加标题
        heading = self.document.add_heading('二、原始文本与编码引用', level=1)

        # 添加说明
        self.document.add_paragraph("以下为所有访谈文本的合并内容，其中标记的文本对应上方的一阶编码。")
        self.document.add_paragraph("编号说明：")
        self.document.add_paragraph("  - A, B, C...: 三阶编码")
        self.document.add_paragraph("  - A1, A2, B1, B2...: 二阶编码")
        self.document.add_paragraph("  - A1-01, A1-02, A2-01...: 一阶编码（按访谈文件顺序和文件内顺序编号）")

        # 处理文本，添加引用标记
        text_paragraph = self.document.add_paragraph()

        # 收集所有编码位置
        code_references = self.extract_code_references(structured_codes)

        # 按位置排序（简化处理，按在文本中出现的顺序）
        processed_text = combined_text

        # 在文本中标记编码引用
        for code_id, reference_info in code_references.items():
            original_content = reference_info.get('original_content', '')
            marked_content = reference_info.get('marked_content', '')

            if original_content and marked_content and original_content in processed_text:
                processed_text = processed_text.replace(original_content, marked_content)

        # 添加处理后的文本
        text_paragraph.add_run(processed_text)

    def extract_code_references(self, structured_codes: Dict[str, Any]) -> Dict[str, Any]:
        """提取编码引用信息"""
        code_references = {}

        for third_category, second_categories in structured_codes.items():
            for second_category, first_contents in second_categories.items():
                for content_data in first_contents:
                    if isinstance(content_data, dict):
                        code_id = content_data.get('code_id', '')
                        sentence_details = content_data.get('sentence_details', [])

                        if code_id and sentence_details:
                            # 使用第一个句子的位置
                            first_sentence = sentence_details[0]
                            original_content = first_sentence.get('original_content', '')
                            marked_content = first_sentence.get('content', original_content)

                            if original_content:
                                code_references[code_id] = {
                                    'original_content': original_content,
                                    'marked_content': marked_content,
                                    'filename': first_sentence.get('filename', '')
                                }

        return code_references

    def _build_file_index_map_from_combined_text(self, combined_text: str) -> Dict[str, int]:
        """根据合并文本中出现的文件顺序构建文件索引映射。

        约定：combined_text 由 main_window.get_combined_text 构造，形如
        "\n\n=== 文件名1 ===\n\n...文本...\n\n=== 文件名2 ===\n\n..."。
        """
        import re

        file_index_map: Dict[str, int] = {}
        if not combined_text:
            return file_index_map

        pattern = r"===\s*(.+?)\s*==="
        matches = re.findall(pattern, combined_text)

        index = 1
        for name in matches:
            name = name.strip()
            if name and name not in file_index_map:
                file_index_map[name] = index
                index += 1

        return file_index_map

    def _build_first_level_display_id_map(self, structured_codes: Dict[str, Any],
                                          file_index_map: Dict[str, int]) -> Dict[str, str]:
        """基于文件顺序构建一阶编码显示编号映射。

        对每个一阶编码，根据其 sentence_details 中的 filename/file_path
        找到所属文件的索引 i（从1开始），并在该文件范围内按出现顺序
        赋予本地序号 j（从1开始），最终生成显示编号 A{i}-{j:02d}。
        """
        from collections import defaultdict

        display_map: Dict[str, str] = {}

        if not structured_codes or not file_index_map:
            return display_map

        per_file_counter: Dict[int, int] = defaultdict(int)

        for _, second_categories in structured_codes.items():
            for _, first_contents in second_categories.items():
                for content_data in first_contents:
                    if not isinstance(content_data, dict):
                        continue

                    code_id = content_data.get('code_id', '')
                    if not code_id or code_id in display_map:
                        # 跳过没有编号或已处理过的编码
                        continue

                    sentence_details = content_data.get('sentence_details', [])
                    if not sentence_details:
                        continue

                    first_sentence = sentence_details[0]
                    filename = first_sentence.get('filename', '')
                    if not filename:
                        file_path = first_sentence.get('file_path', '')
                        if file_path:
                            filename = os.path.basename(file_path)

                    if not filename:
                        continue

                    file_idx = file_index_map.get(filename)
                    if not file_idx:
                        continue

                    per_file_counter[file_idx] += 1
                    local_index = per_file_counter[file_idx]
                    display_map[code_id] = f"A{file_idx}-{local_index:02d}"

        return display_map

    def add_bookmark_to_paragraph(self, paragraph, bookmark_name: str):
        """添加书签到段落"""
        try:
            # 创建书签开始
            bookmark_start = OxmlElement('w:bookmarkStart')
            bookmark_start.set(qn('w:id'), '1')
            bookmark_start.set(qn('w:name'), bookmark_name)
            paragraph._p.append(bookmark_start)

            # 创建书签结束
            bookmark_end = OxmlElement('w:bookmarkEnd')
            bookmark_end.set(qn('w:id'), '1')
            bookmark_end.set(qn('w:name'), bookmark_name)
            paragraph._p.append(bookmark_end)
        except Exception as e:
            logger.warning(f"添加书签失败: {e}")

    def clean_category_name(self, name: str) -> str:
        """清理类别名称"""
        import re
        return re.sub(r'^[A-Z]\d*\s*', '', name.strip())

    def clean_first_level_content(self, content: str) -> str:
        """清理一阶编码内容"""
        import re
        return re.sub(r'^[A-Z]\d+\s*', '', content.strip())