import os
import json
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QGroupBox, QTextEdit, QLineEdit, QPushButton,QWidget,
                             QListWidget, QListWidgetItem, QLabel, QMessageBox,
                             QTreeWidget, QTreeWidgetItem, QSplitter, QComboBox,
                             QInputDialog, QDialogButtonBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import logging

logger = logging.getLogger(__name__)


class ManualCodingDialog(QDialog):
    """手动编码对话框 - 修复文件选择显示问题"""

    def __init__(self, parent=None, loaded_files=None, existing_codes=None):
        super().__init__(parent)
        self.loaded_files = loaded_files or {}
        self.existing_codes = existing_codes or {}
        self.current_codes = {}
        self.init_ui()
        self.load_existing_codes()

    def init_ui(self):
        self.setWindowTitle("手动编码工具")
        self.setModal(True)
        self.resize(1200, 800)

        layout = QVBoxLayout(self)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：文本浏览和选择
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # 中间：编码操作
        center_panel = self.create_center_panel()
        splitter.addWidget(center_panel)

        # 右侧：编码结构显示
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        # 设置分割比例
        splitter.setSizes([400, 400, 400])
        layout.addWidget(splitter)

        # 按钮
        button_layout = QHBoxLayout()

        save_btn = QPushButton("保存编码")
        save_btn.clicked.connect(self.save_coding)

        export_btn = QPushButton("导出为标准答案")
        export_btn.clicked.connect(self.export_to_standard)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.reject)

        button_layout.addWidget(save_btn)
        button_layout.addWidget(export_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 文件选择
        file_group = QGroupBox("选择文本文件")
        file_layout = QVBoxLayout(file_group)

        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.on_file_selected)
        file_layout.addWidget(self.file_list)

        # 加载文件到列表
        for file_path, file_data in self.loaded_files.items():
            filename = file_data.get('filename', os.path.basename(file_path))
            item = QListWidgetItem(filename)
            item.setData(Qt.UserRole, file_path)
            self.file_list.addItem(item)

        layout.addWidget(file_group)

        # 文本显示
        text_group = QGroupBox("文本内容")
        text_layout = QVBoxLayout(text_group)

        self.text_display = QTextEdit()
        self.text_display.setPlaceholderText("选择文件查看文本内容...")
        font = QFont("SimSun", 10)
        self.text_display.setFont(font)
        text_layout.addWidget(self.text_display)

        # 文本选择按钮
        select_buttons_layout = QHBoxLayout()
        self.select_sentence_btn = QPushButton("选择句子作为一阶编码")
        self.select_sentence_btn.clicked.connect(self.select_sentence_for_coding)
        self.select_sentence_btn.setEnabled(False)

        select_buttons_layout.addWidget(self.select_sentence_btn)
        text_layout.addLayout(select_buttons_layout)

        layout.addWidget(text_group)

        return panel

    def create_center_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 三级编码输入
        coding_group = QGroupBox("三级编码输入")
        coding_layout = QFormLayout(coding_group)

        # 三阶编码
        self.third_category_combo = QComboBox()
        self.third_category_combo.setEditable(True)
        self.third_category_combo.currentTextChanged.connect(self.on_third_category_changed)
        coding_layout.addRow("三阶编码:", self.third_category_combo)

        # 二阶编码
        self.second_category_combo = QComboBox()
        self.second_category_combo.setEditable(True)
        self.second_category_combo.currentTextChanged.connect(self.on_second_category_changed)
        coding_layout.addRow("二阶编码:", self.second_category_combo)

        # 一阶编码内容
        self.first_content_edit = QTextEdit()
        self.first_content_edit.setMaximumHeight(100)
        self.first_content_edit.setPlaceholderText("输入一阶编码内容或从左侧文本中选择...")
        coding_layout.addRow("一阶编码:", self.first_content_edit)

        # 添加编码按钮
        add_code_btn = QPushButton("添加编码")
        add_code_btn.clicked.connect(self.add_manual_code)
        coding_layout.addRow("", add_code_btn)

        layout.addWidget(coding_group)

        # 管理编码类别
        manage_group = QGroupBox("管理编码类别")
        manage_layout = QVBoxLayout(manage_group)

        manage_buttons_layout = QHBoxLayout()

        add_third_btn = QPushButton("添加三阶编码")
        add_third_btn.clicked.connect(self.add_third_category)

        add_second_btn = QPushButton("添加二阶编码")
        add_second_btn.clicked.connect(self.add_second_category)

        manage_buttons_layout.addWidget(add_third_btn)
        manage_buttons_layout.addWidget(add_second_btn)

        manage_layout.addLayout(manage_buttons_layout)

        layout.addWidget(manage_group)

        return panel

    def create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 编码结构显示
        structure_group = QGroupBox("当前编码结构")
        structure_layout = QVBoxLayout(structure_group)

        self.coding_tree = QTreeWidget()
        self.coding_tree.setHeaderLabels(["编码内容", "类型", "数量", "文件来源数", "句子来源数", "关联编号"])
        self.coding_tree.setColumnWidth(0, 300)
        self.coding_tree.setColumnWidth(1, 80)
        self.coding_tree.setColumnWidth(2, 60)
        self.coding_tree.setColumnWidth(3, 80)
        self.coding_tree.setColumnWidth(4, 80)
        self.coding_tree.setColumnWidth(5, 120)
        self.coding_tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        # 启用多选模式
        self.coding_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        structure_layout.addWidget(self.coding_tree)

        # 树形控件操作按钮
        tree_buttons_layout = QHBoxLayout()

        edit_btn = QPushButton("编辑选中")
        edit_btn.clicked.connect(self.edit_selected_code)

        delete_btn = QPushButton("删除选中")
        delete_btn.clicked.connect(self.delete_selected_code)
        
        create_parent_btn = QPushButton("创建父级")
        create_parent_btn.clicked.connect(self.create_parent_node)

        tree_buttons_layout.addWidget(edit_btn)
        tree_buttons_layout.addWidget(delete_btn)
        tree_buttons_layout.addWidget(create_parent_btn)

        structure_layout.addLayout(tree_buttons_layout)

        layout.addWidget(structure_group)

        return panel

    def load_existing_codes(self):
        """加载现有编码"""
        if self.existing_codes:
            self.current_codes = self.existing_codes.copy()
            self.update_category_combos()
            self.update_coding_tree()

    def update_category_combos(self):
        """更新类别下拉框"""
        # 保存当前选择
        current_third = self.third_category_combo.currentText()
        current_second = self.second_category_combo.currentText()

        # 清空下拉框
        self.third_category_combo.clear()
        self.second_category_combo.clear()

        # 添加三阶编码
        for third_cat in self.current_codes.keys():
            self.third_category_combo.addItem(third_cat)

        # 恢复选择或选择第一个
        if current_third and self.third_category_combo.findText(current_third) >= 0:
            self.third_category_combo.setCurrentText(current_third)
        elif self.third_category_combo.count() > 0:
            self.third_category_combo.setCurrentIndex(0)

    def on_third_category_changed(self, third_category):
        """三阶编码改变事件"""
        self.second_category_combo.clear()

        if third_category and third_category in self.current_codes:
            for second_cat in self.current_codes[third_category].keys():
                self.second_category_combo.addItem(second_cat)

            if self.second_category_combo.count() > 0:
                self.second_category_combo.setCurrentIndex(0)

    def on_second_category_changed(self, second_category):
        """二阶编码改变事件"""
        pass  # 可以在这里添加相关逻辑

    def generate_code_number(self, prefix, existing_codes):
        """生成编码编号，例如A01, A02, B01, B02, C01, C02等"""
        # 从现有编码中提取已使用的编号
        used_numbers = []
        for code in existing_codes:
            # 如果code是完整的一阶编码（包含内容和编号），需要先提取编号部分
            if ' ' in code:  # 如果包含空格，说明是"内容 编号"格式
                parts = code.split()
                if len(parts) >= 2:
                    actual_code = parts[-1]  # 编号在最后
                else:
                    actual_code = code
            else:
                actual_code = code
            
            # 检查是否是目标前缀的编号
            if actual_code.startswith(prefix) and len(actual_code) > len(prefix):
                try:
                    # 提取编号部分，例如从"A01"中提取"01"
                    number_part = actual_code[len(prefix):]
                    if number_part.isdigit():
                        used_numbers.append(int(number_part))
                except:
                    continue
        
        # 找到下一个可用编号
        next_number = 1
        while next_number in used_numbers:
            next_number += 1
        
        # 格式化编号，保持两位数格式
        return f"{prefix}{next_number:02d}"

    def on_file_selected(self, item):
        """文件选择事件 - 修复版本"""
        try:
            file_path = item.data(Qt.UserRole)
            logger.info(f"选择了文件: {file_path}")

            if file_path in self.loaded_files:
                file_data = self.loaded_files[file_path]

                # 尝试获取不同的文本字段
                content = file_data.get('content', '')
                if not content:
                    content = file_data.get('original_content', '')
                if not content:
                    content = file_data.get('numbered_text', '')
                if not content:
                    content = file_data.get('original_text', '')

                logger.info(f"文件内容长度: {len(content)}")

                if content:
                    self.text_display.setPlainText(content)
                    self.select_sentence_btn.setEnabled(True)
                    logger.info("文本内容显示成功")
                else:
                    self.text_display.setPlainText("文件内容为空")
                    self.select_sentence_btn.setEnabled(False)
                    logger.warning("文件内容为空")
            else:
                self.text_display.setPlainText("文件数据不存在")
                self.select_sentence_btn.setEnabled(False)
                logger.error(f"文件数据不存在: {file_path}")

        except Exception as e:
            logger.error(f"文件选择处理失败: {e}")
            self.text_display.setPlainText(f"加载文件失败: {str(e)}")
            self.select_sentence_btn.setEnabled(False)

    def select_sentence_for_coding(self):
        """选择句子作为一阶编码"""
        try:
            cursor = self.text_display.textCursor()
            if cursor.hasSelection():
                selected_text = cursor.selectedText().strip()
                logger.info(f"选择了文本: {selected_text[:50]}...")

                if len(selected_text) > 5:  # 确保有意义的文本
                    self.first_content_edit.setPlainText(selected_text)
                    logger.info("文本已复制到一阶编码输入框")
                else:
                    QMessageBox.warning(self, "警告", "请选择有意义的文本（至少5个字符）")
            else:
                QMessageBox.information(self, "提示", "请先选择文本内容")

        except Exception as e:
            logger.error(f"选择句子失败: {e}")
            QMessageBox.critical(self, "错误", f"选择句子失败: {str(e)}")

    def add_third_category(self):
        """添加三阶编码"""
        name, ok = QInputDialog.getText(self, "添加三阶编码", "请输入三阶编码名称:")
        if ok and name.strip():
            # 生成三阶编码编号（C开头）
            existing_codes = []
            for third_cat, second_cats in self.current_codes.items():
                if third_cat.startswith("C") and len(third_cat) > 1 and third_cat[1:].isdigit():
                    existing_codes.append(third_cat)
            
            if name.strip().startswith("C"):
                # 如果用户输入了C开头的编号，直接使用
                third_code = name.strip()
            else:
                # 自动生成C开头的编号
                third_code = self.generate_code_number("C", existing_codes)
                name = f"{name.strip()} {third_code}"
            
            if name not in self.current_codes:
                self.current_codes[name] = {}
                self.update_category_combos()
                self.third_category_combo.setCurrentText(name)
                self.update_coding_tree()

    def add_second_category(self):
        """添加二阶编码"""
        current_third = self.third_category_combo.currentText()
        if not current_third:
            QMessageBox.warning(self, "警告", "请先选择或创建三阶编码")
            return

        name, ok = QInputDialog.getText(self, "添加二阶编码", "请输入二阶编码名称:")
        if ok and name.strip():
            # 生成二阶编码编号（B开头）
            existing_codes = []
            for second_cat, first_contents in self.current_codes[current_third].items():
                if second_cat.startswith("B") and len(second_cat) > 1 and second_cat[1:].isdigit():
                    existing_codes.append(second_cat)
            
            if name.strip().startswith("B"):
                # 如果用户输入了B开头的编号，直接使用
                second_code = name.strip()
            else:
                # 自动生成B开头的编号
                second_code = self.generate_code_number("B", existing_codes)
                name = f"{name.strip()} {second_code}"
            
            if name not in self.current_codes[current_third]:
                self.current_codes[current_third][name] = []
                self.update_category_combos()
                self.second_category_combo.setCurrentText(name)
                self.update_coding_tree()

    def add_manual_code(self):
        """添加手动编码 - 支持直接添加一阶编码"""
        third_category = self.third_category_combo.currentText().strip()
        second_category = self.second_category_combo.currentText().strip()
        first_content = self.first_content_edit.toPlainText().strip()

        if not first_content:
            QMessageBox.warning(self, "警告", "请输入一阶编码内容")
            return

        # 如果没有三阶编码，创建一个默认的
        if not third_category:
            third_category = "未分类三阶"
            if third_category not in self.current_codes:
                self.current_codes[third_category] = {}

        # 如果没有二阶编码，创建一个默认的
        if not second_category:
            second_category = "未分类二阶"
            if second_category not in self.current_codes[third_category]:
                self.current_codes[third_category][second_category] = []

        # 确保三阶编码存在
        if third_category not in self.current_codes:
            self.current_codes[third_category] = {}

        # 确保二阶编码存在
        if second_category not in self.current_codes[third_category]:
            self.current_codes[third_category][second_category] = []

        # 生成一阶编码编号（A开头）
        first_code = self.generate_code_number("A", self.current_codes[third_category][second_category])
        first_content_with_code = f"{first_content} {first_code}"

        # 添加一阶编码
        if first_content_with_code not in self.current_codes[third_category][second_category]:
            self.current_codes[third_category][second_category].append(first_content_with_code)
            self.first_content_edit.clear()
            self.update_coding_tree()
            QMessageBox.information(self, "成功", f"编码已添加: {first_code}")
        else:
            QMessageBox.warning(self, "警告", "该编码内容已存在")

    def update_coding_tree(self):
        """更新编码树形结构"""
        self.coding_tree.clear()

        for third_cat, second_cats in self.current_codes.items():
            # 计算三阶编码的累加数据
            total_files = 0
            total_sentences = 0
            all_codes = []
            
            for second_cat, first_contents in second_cats.items():
                total_sentences += len(first_contents)
                # 假设每个一阶编码来自一个文件（实际中可能需要根据具体文件信息计算）
                total_files += 1  # 每个二阶编码至少包含一个文件
                
                for content in first_contents:
                    # 提取编号（假设编号在内容末尾，以空格分隔）
                    parts = content.split()
                    if len(parts) >= 2 and (parts[-1].startswith('A') or parts[-1].startswith('B') or parts[-1].startswith('C')) and parts[-1][1:].isdigit():
                        all_codes.append(parts[-1])

            third_item = QTreeWidgetItem(self.coding_tree)
            third_item.setText(0, third_cat)
            third_item.setText(1, "三阶编码")
            third_item.setText(2, str(len(second_cats)))
            third_item.setText(3, str(total_files))  # 文件来源数
            third_item.setText(4, str(total_sentences))  # 句子来源数
            third_item.setText(5, ", ".join(all_codes))  # 关联编号
            third_item.setData(0, Qt.UserRole, {"type": "third", "name": third_cat})

            for second_cat, first_contents in second_cats.items():
                # 计算二阶编码的累加数据
                second_total_sentences = len(first_contents)
                second_total_files = 1  # 每个二阶编码至少来自一个文件
                second_codes = []
                
                for content in first_contents:
                    # 提取编号（假设编号在内容末尾，以空格分隔）
                    parts = content.split()
                    if len(parts) >= 2 and (parts[-1].startswith('A') or parts[-1].startswith('B') or parts[-1].startswith('C')) and parts[-1][1:].isdigit():
                        second_codes.append(parts[-1])

                second_item = QTreeWidgetItem(third_item)
                second_item.setText(0, second_cat)
                second_item.setText(1, "二阶编码")
                second_item.setText(2, str(len(first_contents)))
                second_item.setText(3, "")  # 二阶的文件来源数不显示
                second_item.setText(4, str(second_total_sentences))  # 句子来源数
                second_item.setText(5, ", ".join(second_codes))  # 关联编号
                second_item.setData(0, Qt.UserRole, {"type": "second", "name": second_cat, "parent": third_cat})

                for content in first_contents:
                    # 提取一阶编码的编号
                    code = ""
                    parts = content.split()
                    if len(parts) >= 2 and (parts[-1].startswith('A') or parts[-1].startswith('B') or parts[-1].startswith('C')) and parts[-1][1:].isdigit():
                        code = parts[-1]

                    first_item = QTreeWidgetItem(second_item)
                    first_item.setText(0, content)
                    first_item.setText(1, "一阶编码")
                    first_item.setText(2, "1")
                    first_item.setText(3, "1")  # 文件来源数
                    first_item.setText(4, "1")  # 句子来源数
                    first_item.setText(5, code)  # 关联编号
                    first_item.setData(0, Qt.UserRole, {"type": "first", "content": content, "parent": second_cat})

        self.coding_tree.expandAll()

    def on_tree_item_double_clicked(self, item, column):
        """树形项目双击事件"""
        item_data = item.data(0, Qt.UserRole)
        if item_data:
            item_type = item_data.get("type")
            if item_type == "third":
                self.third_category_combo.setCurrentText(item_data.get("name", ""))
            elif item_type == "second":
                self.third_category_combo.setCurrentText(item_data.get("parent", ""))
                self.second_category_combo.setCurrentText(item_data.get("name", ""))
            elif item_type == "first":
                self.first_content_edit.setPlainText(item_data.get("content", ""))
                # 找到对应的父级
                parent_item = item.parent()
                if parent_item:
                    parent_data = parent_item.data(0, Qt.UserRole)
                    if parent_data and parent_data.get("type") == "second":
                        grand_parent_item = parent_item.parent()
                        if grand_parent_item:
                            grand_parent_data = grand_parent_item.data(0, Qt.UserRole)
                            if grand_parent_data and grand_parent_data.get("type") == "third":
                                self.third_category_combo.setCurrentText(grand_parent_data.get("name", ""))
                                self.second_category_combo.setCurrentText(parent_data.get("name", ""))

    def edit_selected_code(self):
        """编辑选中的编码 - 增大弹窗版本"""
        current_item = self.coding_tree.currentItem()
        if not current_item:
            return

        item_data = current_item.data(0, Qt.UserRole)
        if not item_data:
            return

        item_type = item_data.get("type")
        old_name = item_data.get("name") or item_data.get("content", "")

        if item_type == "third":
            # 编辑三阶编码
            dialog = QDialog(self)
            dialog.setWindowTitle("编辑三阶编码")
            dialog.resize(500, 200)

            layout = QVBoxLayout(dialog)

            label = QLabel("请输入三阶编码名称:")
            layout.addWidget(label)

            line_edit = QLineEdit()
            line_edit.setText(old_name)
            layout.addWidget(line_edit)

            button_layout = QHBoxLayout()
            ok_button = QPushButton("确定")
            cancel_button = QPushButton("取消")

            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            def on_ok():
                new_name = line_edit.text().strip()
                if new_name and new_name != old_name:
                    # 更新三阶编码名称
                    if old_name in self.current_codes:
                        self.current_codes[new_name] = self.current_codes.pop(old_name)
                        self.update_category_combos()
                        self.update_coding_tree()
                dialog.accept()

            def on_cancel():
                dialog.reject()

            ok_button.clicked.connect(on_ok)
            cancel_button.clicked.connect(on_cancel)

            dialog.exec_()

        elif item_type == "second":
            parent_name = item_data.get("parent")
            # 编辑二阶编码
            dialog = QDialog(self)
            dialog.setWindowTitle("编辑二阶编码")
            dialog.resize(500, 200)

            layout = QVBoxLayout(dialog)

            label = QLabel("请输入二阶编码名称:")
            layout.addWidget(label)

            line_edit = QLineEdit()
            line_edit.setText(old_name)
            layout.addWidget(line_edit)

            button_layout = QHBoxLayout()
            ok_button = QPushButton("确定")
            cancel_button = QPushButton("取消")

            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            def on_ok():
                new_name = line_edit.text().strip()
                if new_name and new_name != old_name and parent_name in self.current_codes:
                    if old_name in self.current_codes[parent_name]:
                        self.current_codes[parent_name][new_name] = self.current_codes[parent_name].pop(old_name)
                        self.update_category_combos()
                        self.update_coding_tree()
                dialog.accept()

            def on_cancel():
                dialog.reject()

            ok_button.clicked.connect(on_ok)
            cancel_button.clicked.connect(on_cancel)

            dialog.exec_()

        elif item_type == "first":
            parent_name = item_data.get("parent")
            grand_parent_item = current_item.parent().parent()
            if grand_parent_item:
                grand_parent_data = grand_parent_item.data(0, Qt.UserRole)
                if grand_parent_data and grand_parent_data.get("type") == "third":
                    third_name = grand_parent_data.get("name")
                    # 编辑一阶编码 - 使用大对话框
                    dialog = QDialog(self)
                    dialog.setWindowTitle("编辑一阶编码")
                    dialog.resize(600, 400)

                    layout = QVBoxLayout(dialog)

                    label = QLabel("请输入一阶编码内容:")
                    layout.addWidget(label)

                    text_edit = QTextEdit()
                    text_edit.setPlainText(old_name)
                    text_edit.setMinimumHeight(200)
                    layout.addWidget(text_edit)

                    button_layout = QHBoxLayout()
                    ok_button = QPushButton("确定")
                    cancel_button = QPushButton("取消")

                    button_layout.addWidget(ok_button)
                    button_layout.addWidget(cancel_button)
                    layout.addLayout(button_layout)

                    def on_ok():
                        new_content = text_edit.toPlainText().strip()
                        if new_content and new_content != old_name:
                            if (third_name in self.current_codes and
                                    parent_name in self.current_codes[third_name] and
                                    old_name in self.current_codes[third_name][parent_name]):
                                index = self.current_codes[third_name][parent_name].index(old_name)
                                self.current_codes[third_name][parent_name][index] = new_content
                                self.update_coding_tree()
                        dialog.accept()

                    def on_cancel():
                        dialog.reject()

                    ok_button.clicked.connect(on_ok)
                    cancel_button.clicked.connect(on_cancel)

                    dialog.exec_()

    def delete_selected_code(self):
        """删除选中的编码"""
        current_item = self.coding_tree.currentItem()
        if not current_item:
            return

        item_data = current_item.data(0, Qt.UserRole)
        if not item_data:
            return

        item_type = item_data.get("type")
        name = item_data.get("name") or item_data.get("content", "")

        reply = QMessageBox.question(self, "确认删除", f"确定要删除这个{item_type}编码吗？\n{name}")
        if reply == QMessageBox.Yes:
            if item_type == "third":
                if name in self.current_codes:
                    del self.current_codes[name]
                    self.update_category_combos()
                    self.update_coding_tree()

            elif item_type == "second":
                parent_name = item_data.get("parent")
                if parent_name in self.current_codes and name in self.current_codes[parent_name]:
                    del self.current_codes[parent_name][name]
                    self.update_category_combos()
                    self.update_coding_tree()

            elif item_type == "first":
                parent_name = item_data.get("parent")
                grand_parent_item = current_item.parent().parent()
                if grand_parent_item:
                    grand_parent_data = grand_parent_item.data(0, Qt.UserRole)
                    if grand_parent_data and grand_parent_data.get("type") == "third":
                        third_name = grand_parent_data.get("name")
                        if (third_name in self.current_codes and
                                parent_name in self.current_codes[third_name] and
                                name in self.current_codes[third_name][parent_name]):
                            self.current_codes[third_name][parent_name].remove(name)
                            self.update_coding_tree()

    def save_coding(self):
        """保存编码"""
        try:
            # 这里可以添加保存到文件的逻辑
            QMessageBox.information(self, "成功", "编码已保存")
            return True
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
            return False

    def export_to_standard(self):
        """导出为标准答案"""
        if not self.current_codes:
            QMessageBox.warning(self, "警告", "没有编码数据可导出")
            return

        description, ok = QInputDialog.getText(self, "标准答案描述", "请输入本次标准答案的描述:")
        if ok:
            # 通过父窗口保存为标准答案
            parent = self.parent()
            if hasattr(parent, 'standard_answer_manager'):
                version_id = parent.standard_answer_manager.create_from_structured_codes(
                    self.current_codes, description
                )
                if version_id:
                    QMessageBox.information(self, "成功", f"已导出为标准答案: {version_id}")
                    self.accept()
                else:
                    QMessageBox.critical(self, "错误", "导出失败")

    def create_parent_node(self):
        """创建父级节点 - 支持选中一阶编码创建二阶父节点，选中二阶编码创建三阶父节点，支持多选"""
        # 获取所有选中的项目
        selected_items = self.coding_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个或多个编码节点")
            return

        # 检查选中的项目是否都是同一种类型
        item_types = set()
        for item in selected_items:
            item_data = item.data(0, Qt.UserRole)
            if item_data:
                item_types.add(item_data.get("type", ""))
        
        if len(item_types) > 1:
            QMessageBox.warning(self, "警告", "请选择相同类型的编码节点")
            return
        
        if len(item_types) == 0:
            return

        item_type = list(item_types)[0]
        
        if item_type == "first":
            # 选中一阶编码，创建二阶父节点
            parent_name, ok = QInputDialog.getText(self, "创建二阶编码", "请输入二阶编码名称:")
            if ok and parent_name.strip():
                parent_name = parent_name.strip()
                
                # 生成二阶编码编号（B开头）
                third_names = set()
                for item in selected_items:
                    item_data = item.data(0, Qt.UserRole)
                    if item_data:
                        grand_parent_item = item.parent()
                        if grand_parent_item:
                            grand_parent_data = grand_parent_item.data(0, Qt.UserRole)
                            if grand_parent_data and grand_parent_data.get("type") == "second":
                                third_names.add(grand_parent_data.get("name"))
                
                # 为所有相关的三阶编码收集现有的二阶编码
                existing_codes = []
                for third_name in third_names:
                    if third_name in self.current_codes:
                        for second_cat in self.current_codes[third_name].keys():
                            if second_cat.startswith("B") and len(second_cat) > 1 and second_cat[1:].isdigit():
                                existing_codes.append(second_cat)
                
                if parent_name.startswith("B"):
                    # 如果用户输入了B开头的编号，直接使用
                    second_code = parent_name
                else:
                    # 自动生成B开头的编号
                    second_code = self.generate_code_number("B", existing_codes)
                    parent_name = f"{parent_name} {second_code}"
                
                # 如果选中的编码来自不同的三阶编码，需要确认操作
                if len(third_names) > 1:
                    reply = QMessageBox.question(self, "确认操作", 
                        f"选中的编码来自{len(third_names)}个不同的三阶编码，确定要将它们都移动到新的二阶编码 '{parent_name}' 下吗？",
                        QMessageBox.Yes | QMessageBox.No)
                    if reply != QMessageBox.Yes:
                        return
                
                # 检查二阶编码是否已存在（在所有相关的三阶编码中）
                all_third_names = list(third_names)
                can_create = True
                for third_name in all_third_names:
                    if parent_name in self.current_codes.get(third_name, {}):
                        QMessageBox.warning(self, "警告", f"二阶编码 '{parent_name}' 在三阶编码 '{third_name}' 下已存在")
                        can_create = False
                        break
                
                if not can_create:
                    return
                
                # 创建新的二阶编码并移动所有选中的一阶编码
                for third_name in all_third_names:
                    if third_name not in self.current_codes:
                        self.current_codes[third_name] = {}
                    
                    if parent_name not in self.current_codes[third_name]:
                        self.current_codes[third_name][parent_name] = []
                
                # 移动选中的一阶编码
                for item in selected_items:
                    item_data = item.data(0, Qt.UserRole)
                    if item_data:
                        # 获取当前一阶编码的详细信息
                        first_content = item_data.get("content", "")
                        
                        # 获取当前一阶编码的父级（二阶）和祖父级（三阶）
                        parent_item = item.parent()
                        grand_parent_item = parent_item.parent() if parent_item else None
                        
                        if parent_item:
                            parent_data = parent_item.data(0, Qt.UserRole)
                            if parent_data and parent_data.get("type") == "second":
                                original_second_name = parent_data.get("name", "")
                                
                                if grand_parent_item:
                                    grand_parent_data = grand_parent_item.data(0, Qt.UserRole)
                                    if grand_parent_data and grand_parent_data.get("type") == "third":
                                        original_third_name = grand_parent_data.get("name", "")
                                        
                                        # 确保目标二阶编码存在
                                        if parent_name not in self.current_codes[original_third_name]:
                                            self.current_codes[original_third_name][parent_name] = []
                                        # 添加一阶编码到新的二阶编码
                                        self.current_codes[original_third_name][parent_name].append(first_content)
                                        
                                        # 从原二阶编码中删除该一阶编码
                                        if (original_third_name in self.current_codes and 
                                            original_second_name in self.current_codes[original_third_name] and
                                            first_content in self.current_codes[original_third_name][original_second_name]):
                                            self.current_codes[original_third_name][original_second_name].remove(first_content)
                                            
                                            # 如果原二阶编码下没有其他项目了，删除该二阶编码
                                            if len(self.current_codes[original_third_name][original_second_name]) == 0:
                                                del self.current_codes[original_third_name][original_second_name]
                
                self.update_category_combos()
                self.update_coding_tree()
                QMessageBox.information(self, "成功", f"已创建二阶编码 '{parent_name}' 并将{len(selected_items)}个一阶编码移入")
        
        elif item_type == "second":
            # 选中二阶编码，创建三阶父节点
            parent_name, ok = QInputDialog.getText(self, "创建三阶编码", "请输入三阶编码名称:")
            if ok and parent_name.strip():
                parent_name = parent_name.strip()
                
                # 生成三阶编码编号（C开头）
                existing_codes = []
                for third_cat, second_cats in self.current_codes.items():
                    if third_cat.startswith("C") and len(third_cat) > 1 and third_cat[1:].isdigit():
                        existing_codes.append(third_cat)
                
                if parent_name.startswith("C"):
                    # 如果用户输入了C开头的编号，直接使用
                    third_code = parent_name
                else:
                    # 自动生成C开头的编号
                    third_code = self.generate_code_number("C", existing_codes)
                    parent_name = f"{parent_name} {third_code}"
                
                # 获取当前二阶编码的三阶父级
                original_third_names = set()
                for item in selected_items:
                    item_data = item.data(0, Qt.UserRole)
                    if item_data:
                        parent_item = item.parent()
                        if parent_item:
                            parent_data = parent_item.data(0, Qt.UserRole)
                            if parent_data and parent_data.get("type") == "third":
                                original_third_names.add(parent_data.get("name"))
                
                # 检查三阶编码是否已存在
                if parent_name in self.current_codes:
                    QMessageBox.warning(self, "警告", f"三阶编码 '{parent_name}' 已存在")
                    return
                
                # 创建新的三阶编码结构
                if parent_name not in self.current_codes:
                    self.current_codes[parent_name] = {}
                
                # 将所有选中的二阶编码移动到新的三阶编码下
                for item in selected_items:
                    item_data = item.data(0, Qt.UserRole)
                    if item_data:
                        second_name = item_data.get("name", "")
                        
                        # 获取当前二阶编码的父级（三阶）
                        parent_item = item.parent()
                        if parent_item:
                            parent_data = parent_item.data(0, Qt.UserRole)
                            if parent_data and parent_data.get("type") == "third":
                                original_third_name = parent_data.get("name", "")
                                
                                # 将当前二阶编码移动到新的三阶编码下
                                if second_name in self.current_codes[original_third_name]:
                                    self.current_codes[parent_name][second_name] = self.current_codes[original_third_name][second_name]
                                    
                                    # 从原三阶编码中删除该二阶编码
                                    del self.current_codes[original_third_name][second_name]
                                    
                                    # 如果原三阶编码下没有其他二阶编码了，删除该三阶编码
                                    if original_third_name in self.current_codes and len(self.current_codes[original_third_name]) == 0:
                                        del self.current_codes[original_third_name]
                
                self.update_category_combos()
                self.update_coding_tree()
                QMessageBox.information(self, "成功", f"已创建三阶编码 '{parent_name}' 并将{len(selected_items)}个二阶编码移入")

    def get_coding_result(self):
        """获取编码结果"""
        return self.current_codes