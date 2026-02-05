import os
import json
import re
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QGroupBox, QTextEdit, QLineEdit, QPushButton, QWidget,
                             QListWidget, QListWidgetItem, QLabel, QMessageBox,
                             QTreeWidget, QTreeWidgetItem, QSplitter, QComboBox,
                             QInputDialog, QDialogButtonBox, QApplication)
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QTextDocument
from PyQt5.QtGui import QFont, QColor, QDrag
import logging

logger = logging.getLogger(__name__)

class DragDropTreeWidget(QTreeWidget):
    """支持拖放功能的树形控件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dialog = None  # 将由ManualCodingDialog设置

    def dragEnterEvent(self, event):
        """拖放进入事件"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """拖放移动事件"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """拖放释放事件"""
        if self.dialog:
            # 明确设置为复制操作，防止源文本被删除
            event.setDropAction(Qt.CopyAction)
            self.dialog.handle_drop_on_tree(event)
            event.accept()
        else:
            event.ignore()

    def dragEnterEvent(self, event):
        """处理拖拽进入事件，明确接受复制操作"""
        if event.mimeData().hasText():
            # 接受复制操作，不接受移动操作
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """处理拖拽移动事件，确保操作类型正确"""
        if event.mimeData().hasText():
            # 确保是复制操作
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

class ManualCodingDialog(QDialog):
    """手动编码对话框 - 修复文件选择显示问题"""

    def __init__(self, parent=None, loaded_files=None, existing_codes=None):
        super().__init__(parent)
        self.parent_window = parent  # 保存父窗口引用，用于访问data_processor
        self.loaded_files = loaded_files or {}
        self.existing_codes = existing_codes or {}
        self.current_codes = {}
        # 未分类的一阶编码临时存储
        self.unclassified_first_codes = []
        self.init_ui()
        self.load_existing_codes()

    def init_ui(self):
        self.setWindowTitle("手动编码工具 - 全屏版")
        self.setModal(False)  # 改为非模态，允许全屏显示

        # 设置为全屏或最大化
        screen_geometry = QApplication.desktop().availableGeometry()
        self.setGeometry(screen_geometry)
        self.showMaximized()

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
        splitter.setSizes([300, 600, 500])  # 与主窗口相似的分割比例
        layout.addWidget(splitter)

        # 按钮
        button_layout = QHBoxLayout()

        save_btn = QPushButton("保存编码")
        save_btn.clicked.connect(self.save_coding)

        export_btn = QPushButton("导出为标准答案")
        export_btn.clicked.connect(self.export_to_standard)

        save_tree_btn = QPushButton("保存编码树")
        save_tree_btn.clicked.connect(self.save_coding_tree)

        import_tree_btn = QPushButton("导入编码树")
        import_tree_btn.clicked.connect(self.import_coding_tree)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.reject)

        button_layout.addWidget(save_btn)
        button_layout.addWidget(export_btn)
        button_layout.addWidget(save_tree_btn)
        button_layout.addWidget(import_tree_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        # 保存文本文档引用
        self.text_document = self.text_display.document()

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
        # 设置拖放模式为拖拽（DragDrop），确保拖拽操作为复制模式，不删除原文本
        self.text_display.setAcceptDrops(False)  # 不接受拖放，但允许拖出
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

        # 一阶编码输入
        first_group = QGroupBox("添加一阶编码")
        first_layout = QVBoxLayout(first_group)

        # 一阶编码内容
        self.first_content_edit = QTextEdit()
        self.first_content_edit.setMinimumHeight(120)  # 增加最小高度
        self.first_content_edit.setMaximumHeight(200)  # 设置最大高度，防止过大
        self.first_content_edit.setPlaceholderText("输入一阶编码内容或从左侧文本中选择...")
        first_layout.addWidget(self.first_content_edit)

        # 添加一阶编码按钮
        add_first_btn = QPushButton("添加一阶编码（未分类）")
        add_first_btn.clicked.connect(self.add_first_level_direct)
        add_first_btn.setToolTip("添加一阶编码到根部，稍后可组织层级")
        first_layout.addWidget(add_first_btn)

        layout.addWidget(first_group)

        # 层级节点操作
        hierarchy_group = QGroupBox("层级节点操作")
        hierarchy_layout = QVBoxLayout(hierarchy_group)

        # 添加二阶按钮
        add_second_layout = QHBoxLayout()
        add_second_label = QLabel("在选中的三阶下添加二阶:")
        add_second_btn = QPushButton("添加二阶编码")
        add_second_btn.clicked.connect(self.add_second_to_selected_third)
        add_second_btn.setToolTip("在右侧树中选中一个三阶节点，然后点击此按钮添加二阶")
        add_second_layout.addWidget(add_second_label)
        add_second_layout.addWidget(add_second_btn)
        hierarchy_layout.addLayout(add_second_layout)

        # 添加一阶到二阶按钮
        add_first_to_second_layout = QHBoxLayout()
        add_first_to_second_label = QLabel("在选中的二阶下添加一阶:")
        add_first_to_second_btn = QPushButton("添加一阶到二阶")
        add_first_to_second_btn.clicked.connect(self.add_first_to_selected_second)
        add_first_to_second_btn.setToolTip("在右侧树中选中一个二阶节点，然后点击此按钮添加一阶")
        add_first_to_second_layout.addWidget(add_first_to_second_label)
        add_first_to_second_layout.addWidget(add_first_to_second_btn)
        hierarchy_layout.addLayout(add_first_to_second_layout)

        # 添加独立三阶按钮
        add_third_layout = QHBoxLayout()
        add_third_label = QLabel("创建新的三阶节点:")
        add_third_btn = QPushButton("添加三阶编码")
        add_third_btn.clicked.connect(self.add_third_category)
        add_third_btn.setToolTip("创建一个新的三阶编码节点")
        add_third_layout.addWidget(add_third_label)
        add_third_layout.addWidget(add_third_btn)
        hierarchy_layout.addLayout(add_third_layout)

        layout.addWidget(hierarchy_group)

        # 编码规则说明
        rules_label = QLabel("工作流程: 1.添加所有一阶 → 2.为一阶添加父节点(二阶) → 3.为二阶添加父节点(三阶)")
        rules_label.setStyleSheet("color: #666; font-size: 9pt; font-style: italic; padding: 10px;")
        rules_label.setWordWrap(True)
        layout.addWidget(rules_label)

        return panel

    def create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 编码结构显示（使用树形结构）
        structure_group = QGroupBox("编码结构")
        structure_layout = QVBoxLayout(structure_group)

        # 树形控件
        self.coding_tree = DragDropTreeWidget()
        self.coding_tree.dialog = self  # 设置对话框引用
        self.coding_tree.setHeaderLabels(["编码内容", "类型", "数量", "文件来源数", "句子来源数", "关联编号"])
        self.coding_tree.setColumnWidth(0, 300)
        self.coding_tree.setColumnWidth(1, 80)
        self.coding_tree.setColumnWidth(2, 60)
        self.coding_tree.setColumnWidth(3, 80)
        self.coding_tree.setColumnWidth(4, 80)
        self.coding_tree.setColumnWidth(5, 120)
        self.coding_tree.setSelectionMode(QTreeWidget.ExtendedSelection)  # 支持多选
        self.coding_tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        self.coding_tree.itemClicked.connect(self.on_tree_item_clicked)  # 添加点击事件

        # 设置上下文菜单
        self.coding_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.coding_tree.customContextMenuRequested.connect(self.show_tree_context_menu)

        # 启用拖放功能
        self.coding_tree.setAcceptDrops(True)
        self.coding_tree.setDragEnabled(False)  # 树本身不能拖出
        self.coding_tree.setDropIndicatorShown(True)
        self.coding_tree.viewport().setAcceptDrops(True)

        structure_layout.addWidget(self.coding_tree)

        # 树形操作按钮
        tree_buttons_layout = QHBoxLayout()

        expand_btn = QPushButton("展开全部")
        expand_btn.clicked.connect(self.coding_tree.expandAll)

        collapse_btn = QPushButton("折叠全部")
        collapse_btn.clicked.connect(self.coding_tree.collapseAll)

        self.edit_code_btn = QPushButton("编辑编码")
        self.edit_code_btn.clicked.connect(self.edit_tree_item)

        tree_buttons_layout.addWidget(expand_btn)
        tree_buttons_layout.addWidget(collapse_btn)
        tree_buttons_layout.addWidget(self.edit_code_btn)

        structure_layout.addLayout(tree_buttons_layout)

        # 层级操作按钮
        hierarchy_buttons_layout = QHBoxLayout()

        add_parent_second_btn = QPushButton("为一阶添加父节点(二阶)")
        add_parent_second_btn.clicked.connect(self.add_parent_second_for_first)
        add_parent_second_btn.setToolTip("选中多个一阶编码，为其添加共同的父节点二阶编码")

        add_parent_third_btn = QPushButton("为二阶添加父节点(三阶)")
        add_parent_third_btn.clicked.connect(self.add_parent_third_for_second)
        add_parent_third_btn.setToolTip("选中多个二阶编码，为其添加共同的父节点三阶编码")

        hierarchy_buttons_layout.addWidget(add_parent_second_btn)
        hierarchy_buttons_layout.addWidget(add_parent_third_btn)

        structure_layout.addLayout(hierarchy_buttons_layout)

        # 编辑和删除按钮
        edit_buttons_layout = QHBoxLayout()

        edit_btn = QPushButton("编辑选中")
        edit_btn.clicked.connect(self.edit_tree_item)

        delete_btn = QPushButton("删除选中")
        delete_btn.clicked.connect(self.delete_tree_item)

        edit_buttons_layout.addWidget(edit_btn)
        edit_buttons_layout.addWidget(delete_btn)

        structure_layout.addLayout(edit_buttons_layout)

        layout.addWidget(structure_group)

        return panel

    def load_existing_codes(self):
        """加载现有编码"""
        if self.existing_codes:
            self.current_codes = self.existing_codes.copy()
            self.update_category_combos()
            # 只有当树形控件已经创建后才更新
            if hasattr(self, 'coding_tree'):
                self.update_coding_tree()

    # 下拉框相关方法已弃用
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
                    content = file_data.get('numbered_content', '')
                if not content:
                    content = file_data.get('original_text', '')

                # 检查是否有预先编号的内容
                numbered_content = file_data.get('numbered_content', '')

                if numbered_content:
                    # 如果已有编号内容，直接使用
                    display_content = numbered_content
                    logger.info("使用已有的编号内容")
                elif content:
                    # 如果没有编号内容但有原始内容，进行编号
                    from data_processor import DataProcessor
                    processor = DataProcessor()
                    filename = os.path.basename(file_path)
                    display_content, number_mapping = processor.numbering_manager.number_text(content, filename)
                    logger.info("对原始内容进行编号")
                else:
                    display_content = "文件内容为空"
                    logger.warning("文件内容为空")

                if display_content and display_content != "文件内容为空":
                    self.text_display.setPlainText(display_content)
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

                if len(selected_text) > 0:  # 确保有意义的文本
                    self.first_content_edit.setPlainText(selected_text)
                    logger.info("文本已复制到一阶编码输入框")
                else:
                    QMessageBox.warning(self, "警告", "请选择有意义的文本（至少1个字符）")
            else:
                QMessageBox.information(self, "提示", "请先选择文本内容")

        except Exception as e:
            logger.error(f"选择句子失败: {e}")
            QMessageBox.critical(self, "错误", f"选择句子失败: {str(e)}")

    def validate_category_name(self, name, level):
        """验证编码名称"""
        if not name:
            return False, "", "编码名称不能为空"

        if level == "first":
            if len(name) > 100:
                return False, "", "一阶编码名称不能超过100个字符"
        elif level == "second":
            if len(name) > 100:
                return False, "", "二阶编码名称不能超过100个字符"
        elif level == "third":
            if len(name) > 100:
                return False, "", "三阶编码名称不能超过100个字符"

        clean_name = name.strip()
        return True, clean_name.strip(), ""

    def generate_first_code_id(self):
        """生成一阶编码ID：A01, A02, A03...（A开头，数字递增）"""
        # 统计所有已存在的编码ID，找到最大的编号
        existing_ids = set()

        # 遍历整个树形结构，查找所有一阶编码节点
        def search_tree_for_first_level(item):
            for i in range(item.childCount()):
                child = item.child(i)
                child_data = child.data(0, Qt.UserRole)

                if child_data and child_data.get("level") == 1:
                    # 检查是否为一阶编码
                    code_id = child_data.get("code_id", "")
                    if code_id and code_id.startswith('A'):  # 只统计A开头的编号
                        existing_ids.add(code_id)

                # 递归搜索子节点
                search_tree_for_first_level(child)

        # 遍历顶层项目
        for i in range(self.coding_tree.topLevelItemCount()):
            top_item = self.coding_tree.topLevelItem(i)
            top_data = top_item.data(0, Qt.UserRole)

            if top_data and top_data.get("level") == 1:
                # 顶层直接是一阶编码的情况
                code_id = top_data.get("code_id", "")
                if code_id and code_id.startswith('A'):  # 只统计A开头的编号
                    existing_ids.add(code_id)

            # 搜索子节点
            search_tree_for_first_level(top_item)

        # 提取所有A开头的编号的数字部分
        numbers = []
        for code_id in existing_ids:
            if len(code_id) >= 2 and code_id.startswith('A') and code_id[1:].isdigit():
                number = int(code_id[1:])
                numbers.append(number)

        # 找到下一个可用的数字
        if numbers:
            next_number = max(numbers) + 1
        else:
            next_number = 1

        return f"A{next_number:02d}"

    def generate_second_code_id(self, third_letter):
        """生成二阶编码ID：B01, B02, B03...（B开头，数字递增）"""
        # 统计所有已存在的二阶编码ID，找到最大的编号
        existing_second_numbers = []
        for i in range(self.coding_tree.topLevelItemCount()):
            top_item = self.coding_tree.topLevelItem(i)
            for j in range(top_item.childCount()):
                second_item = top_item.child(j)
                second_data = second_item.data(0, Qt.UserRole)
                if second_data:
                    second_name = second_item.text(0)
                    # 检查二阶名称是否以B开头并有数字
                    if second_name.startswith('B'):
                        # 提取两位数字部分
                        import re
                        match = re.search(r'\d{2}', second_name)
                        if match:
                            existing_second_numbers.append(int(match.group()))

        # 找到下一个可用的编号
        existing_second_numbers = list(set(existing_second_numbers))  # 去重
        if existing_second_numbers:
            next_number = max(existing_second_numbers) + 1
        else:
            next_number = 1

        return f"B{next_number:02d}"

    def add_third_category(self):
        """添加三阶编码"""
        try:
            # 使用自定义对话框，包含更大的文本编辑框
            dialog = QDialog(self)
            dialog.setWindowTitle("添加三阶编码")
            dialog.resize(600, 500)  # 增大对话框尺寸

            layout = QVBoxLayout(dialog)

            label = QLabel("添加三阶编码 (输入内容):")
            layout.addWidget(label)

            text_edit = QTextEdit()
            text_edit.setMinimumHeight(250)  # 增加最小高度
            text_edit.setMaximumHeight(350)  # 设置最大高度
            text_edit.setPlaceholderText("输入三阶编码内容...")
            layout.addWidget(text_edit)

            button_layout = QHBoxLayout()
            ok_button = QPushButton("确定")
            cancel_button = QPushButton("取消")
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            def on_ok():
                name = text_edit.toPlainText().strip()
                if not name:
                    QMessageBox.warning(dialog, "警告", "三阶编码名称不能为空")
                    return

                is_valid, clean_name, error_msg = self.validate_category_name(name, "third")
                if not is_valid:
                    QMessageBox.warning(dialog, "验证错误", error_msg)
                    return

                # 生成三阶编码ID
                code_id = self.generate_third_code_id()
                numbered_name = f"{code_id} {clean_name}"

                # 检查是否已存在（检查带编号的完整名称）
                for i in range(self.coding_tree.topLevelItemCount()):
                    top_item = self.coding_tree.topLevelItem(i)
                    item_data = top_item.data(0, Qt.UserRole)
                    if item_data and item_data.get("level") == 3 and top_item.text(0) == numbered_name:
                        QMessageBox.warning(dialog, "警告", "该三阶编码已存在")
                        return

                # 创建三阶节点
                third_item = QTreeWidgetItem(self.coding_tree)
                third_item.setText(0, numbered_name)
                third_item.setText(1, "三阶编码")
                third_item.setText(2, "0")
                third_item.setText(3, "0")  # 文件来源数
                third_item.setText(4, "0")  # 句子来源数
                third_item.setText(5, code_id)  # 关联编号
                third_item.setData(0, Qt.UserRole, {"level": 3, "name": clean_name, "code_id": code_id})

                self.update_structured_codes_from_tree()
                logger.info(f"添加三阶编码: {clean_name}")
                QMessageBox.information(self, "成功", f"已添加三阶编码: {clean_name}")
                dialog.accept()

            ok_button.clicked.connect(on_ok)
            cancel_button.clicked.connect(dialog.reject)

            dialog.exec_()
        except Exception as e:
            logger.error(f"添加三阶编码失败: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"添加三阶编码失败:\n{str(e)}")

    # 此方法已被 add_second_to_selected_third 替代

    def add_second_to_selected_third(self):
        """在选中的三阶节点下添加二阶编码"""
        try:
            current_item = self.coding_tree.currentItem()
            if not current_item:
                QMessageBox.information(self, "提示", "请先在右侧树中选择一个三阶节点")
                return

            item_data = current_item.data(0, Qt.UserRole)
            if not item_data or item_data.get("level") != 3:
                QMessageBox.warning(self, "警告", "请选择一个三阶编码节点！")
                return

            third_name = current_item.text(0)

            # 输入二阶编码名称
            # 使用自定义对话框，包含更大的文本编辑框
            dialog = QDialog(self)
            dialog.setWindowTitle("添加二阶编码")
            dialog.resize(600, 500)  # 增大对话框尺寸

            layout = QVBoxLayout(dialog)

            label = QLabel(f"在三阶'{third_name}'下添加二阶编码 (输入内容):")
            layout.addWidget(label)

            text_edit = QTextEdit()
            text_edit.setMinimumHeight(250)  # 增加最小高度
            text_edit.setMaximumHeight(350)  # 设置最大高度
            text_edit.setPlaceholderText("输入二阶编码内容...")
            layout.addWidget(text_edit)

            button_layout = QHBoxLayout()
            ok_button = QPushButton("确定")
            cancel_button = QPushButton("取消")
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            def on_ok():
                second_name = text_edit.toPlainText().strip()
                if not second_name:
                    QMessageBox.warning(dialog, "警告", "二阶编码名称不能为空")
                    return

                is_valid, clean_name, error_msg = self.validate_category_name(second_name, "second")
                if not is_valid:
                    QMessageBox.warning(dialog, "验证错误", error_msg)
                    return

                # 生成二阶编码ID（使用B开头）
                code_id = self.generate_second_code_id()
                numbered_name = f"{code_id} {clean_name}"

                # 检查是否已存在（检查带编号的完整名称）
                for i in range(current_item.childCount()):
                    if current_item.child(i).text(0) == numbered_name:
                        QMessageBox.warning(dialog, "警告", "该二阶编码已存在")
                        return

                # 创建二阶节点
                second_item = QTreeWidgetItem(current_item)
                second_item.setText(0, numbered_name)
                second_item.setText(1, "二阶编码")
                second_item.setText(2, "0")
                second_item.setText(3, "")  # 二阶编码不显示文件来源数
                second_item.setText(4, "0")  # 句子来源数
                second_item.setText(5, code_id)  # 关联编号
                second_item.setData(0, Qt.UserRole, {
                    "level": 2,
                    "name": clean_name,
                    "code_id": code_id,
                    "parent": third_name
                })

                current_item.setExpanded(True)
                current_item.setText(2, str(current_item.childCount()))

                self.update_structured_codes_from_tree()
                logger.info(f"在三阶'{third_name}'下添加二阶编码: {clean_name}")
                QMessageBox.information(self, "成功", f"已添加二阶编码: {clean_name}")
                dialog.accept()

            ok_button.clicked.connect(on_ok)
            cancel_button.clicked.connect(dialog.reject)

            dialog.exec_()

        except Exception as e:
            logger.error(f"添加二阶编码失败: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"添加失败:\n{str(e)}")

    def add_first_to_selected_second(self):
        """在选中的二阶节点下添加一阶编码"""
        try:
            current_item = self.coding_tree.currentItem()
            if not current_item:
                QMessageBox.information(self, "提示", "请先在右侧树中选择一个二阶节点")
                return

            item_data = current_item.data(0, Qt.UserRole)
            if not item_data or item_data.get("level") != 2:
                QMessageBox.warning(self, "警告", "请选择一个二阶编码节点！")
                return

            second_name = current_item.text(0)

            # 获取一阶编码内容
            first_content = self.first_content_edit.toPlainText().strip()
            if not first_content:
                QMessageBox.warning(self, "警告", "请先在左侧输入一阶编码内容")
                return

            is_valid, clean_content, error_msg = self.validate_category_name(first_content, "first")
            if not is_valid:
                QMessageBox.warning(self, "验证错误", error_msg)
                return

            # 检查是否已存在
            if self.is_content_exists(clean_content):
                QMessageBox.warning(self, "警告", "该一阶编码已存在")
                return

            # 生成一阶编码ID（使用A开头）
            code_id = self.generate_first_code_id()
            numbered_content = f"{code_id} {clean_content}"

            # 创建一阶节点
            first_item = QTreeWidgetItem(current_item)
            first_item.setText(0, numbered_content)
            first_item.setText(1, "一阶编码")
            first_item.setText(2, "1")
            first_item.setText(3, "1")  # 文件来源数，未合并前为1
            first_item.setText(4, "1")  # 句子来源数，未合并前为1
            first_item.setText(5, code_id)  # 关联编号

            # 获取父节点信息
            parent_item = current_item.parent()
            third_name = ""
            if parent_item and parent_item.data(0, Qt.UserRole) and parent_item.data(0, Qt.UserRole).get("level") == 3:
                # 提取三阶编码的原始名称（去掉编号）
                import re
                parts = parent_item.text(0).split(' ', 1)
                if len(parts) > 1:
                    third_name = parts[1]
                else:
                    third_name = parent_item.text(0)

            # 提取二阶编码的原始名称（去掉编号）
            second_parts = current_item.text(0).split(' ', 1)
            if len(second_parts) > 1:
                second_clean_name = second_parts[1]
            else:
                second_clean_name = current_item.text(0)

            first_item.setData(0, Qt.UserRole, {
                "level": 1,
                "content": clean_content,
                "numbered_content": numbered_content,
                "code_id": code_id,
                "category": second_clean_name,  # 使用清理后的二阶名称
                "core_category": third_name,  # 使用清理后的三阶名称
                "classified": True,
                "sentence_details": [],  # 初始化句子详情列表
                "sentence_count": 1
            })

            current_item.setExpanded(True)
            current_item.setText(2, str(current_item.childCount()))

            # 更新父节点计数
            if parent_item and parent_item.data(0, Qt.UserRole) and parent_item.data(0, Qt.UserRole).get("level") == 3:
                parent_item.setText(2, str(parent_item.childCount()))

            self.first_content_edit.clear()
            self.update_structured_codes_from_tree()

            logger.info(f"在二阶'{second_name}'下添加一阶编码: {clean_content}")
            QMessageBox.information(self, "成功", f"已添加一阶编码: {clean_content}")

        except Exception as e:
            logger.error(f"添加一阶编码失败: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"添加失败:\n{str(e)}")

    def update_filter_combos(self):
        """更新过滤下拉框（已弃用，调用update_coding_tree代替）"""
        self.update_coding_tree()

    def add_parent_second_for_first(self):
        """为选中的一阶编码添加父节点二阶编码"""
        try:
            selected_items = self.coding_tree.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "提示", "请先选中至少一个一阶编码")
                return

            # 验证选中的都是一阶编码
            first_level_items = []
            for item in selected_items:
                item_data = item.data(0, Qt.UserRole)
                if item_data and item_data.get("level") == 1:
                    # 检查一阶编码是否已经有父节点
                    if item.parent():
                        parent_data = item.parent().data(0, Qt.UserRole)
                        if parent_data and parent_data.get("level") == 2:
                            QMessageBox.warning(self, "警告",
                                                f"一阶编码 '{item.text(0)}' 已经有父节点二阶编码 '{item.parent().text(0)}'\n\n一阶只能对应一个二阶！")
                            return
                    first_level_items.append(item)

            if not first_level_items:
                QMessageBox.warning(self, "警告", "请选中一阶编码！")
                return

            # 输入二阶编码名称
            # 使用自定义对话框，包含更大的文本编辑框
            dialog = QDialog(self)
            dialog.setWindowTitle("添加二阶编码")
            dialog.resize(600, 500)  # 增大对话框尺寸

            layout = QVBoxLayout(dialog)

            label = QLabel(f"为 {len(first_level_items)} 个一阶编码添加父节点二阶编码 (输入内容):")
            layout.addWidget(label)

            text_edit = QTextEdit()
            text_edit.setMinimumHeight(250)  # 增加最小高度
            text_edit.setMaximumHeight(350)  # 设置最大高度
            text_edit.setPlaceholderText("输入二阶编码内容...")
            layout.addWidget(text_edit)

            button_layout = QHBoxLayout()
            ok_button = QPushButton("确定")
            cancel_button = QPushButton("取消")
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            def on_ok():
                second_name = text_edit.toPlainText().strip()
                if not second_name:
                    QMessageBox.warning(dialog, "警告", "二阶编码名称不能为空")
                    return

                is_valid, clean_name, error_msg = self.validate_category_name(second_name, "second")
                if not is_valid:
                    QMessageBox.warning(dialog, "验证错误", error_msg)
                    return

                # 生成二阶编码ID（使用B开头）
                code_id = self.generate_second_code_id()
                numbered_name = f"{code_id} {clean_name}"

                # 创建二阶节点
                second_item = QTreeWidgetItem(self.coding_tree)
                second_item.setText(0, numbered_name)
                second_item.setText(1, "二阶编码")
                second_item.setText(3, "")  # 二阶编码不显示文件来源数
                second_item.setText(4, "0")  # 句子来源数
                second_item.setText(5, code_id)  # 关联编号
                second_item.setData(0, Qt.UserRole, {
                    "level": 2,
                    "name": clean_name,
                    "code_id": code_id
                })

                # 移动一阶编码到二阶下
                for item in first_level_items:
                    # 从原位置移除
                    parent = item.parent()
                    if parent:
                        parent.removeChild(item)
                    else:
                        index = self.coding_tree.indexOfTopLevelItem(item)
                        self.coding_tree.takeTopLevelItem(index)

                    # 添加到新的二阶下
                    second_item.addChild(item)

                    # 更新一阶的数据
                    item_data = item.data(0, Qt.UserRole)
                    item_data["classified"] = True
                    item_data["category"] = clean_name

                    # 如果三阶父节点存在，更新核心类别
                    grandparent = second_item.parent()
                    if grandparent and grandparent.data(0, Qt.UserRole) and grandparent.data(0, Qt.UserRole).get(
                            "level") == 3:
                        grandparent_text = grandparent.text(0)
                        import re
                        parts = grandparent_text.split(' ', 1)
                        if len(parts) > 1:
                            item_data["core_category"] = parts[1]
                        else:
                            item_data["core_category"] = grandparent_text

                    item.setData(0, Qt.UserRole, item_data)

                second_item.setText(2, str(len(first_level_items)))
                second_item.setExpanded(True)

                self.update_structured_codes_from_tree()
                logger.info(f"为 {len(first_level_items)} 个一阶编码添加了父节点二阶编码: {clean_name}")
                QMessageBox.information(self, "成功", f"已为 {len(first_level_items)} 个一阶编码添加二阶编码: {clean_name}")
                dialog.accept()

            ok_button.clicked.connect(on_ok)
            cancel_button.clicked.connect(dialog.reject)

            dialog.exec_()

        except Exception as e:
            logger.error(f"添加父节点二阶编码失败: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"添加失败:\n{str(e)}")

    def add_parent_third_for_second(self):
        """为选中的二阶编码添加父节点三阶编码"""
        try:
            selected_items = self.coding_tree.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "提示", "请先选中至少一个二阶编码")
                return

            # 验证选中的都是二阶编码
            second_level_items = []
            for item in selected_items:
                item_data = item.data(0, Qt.UserRole)
                if item_data and item_data.get("level") == 2:
                    # 检查二阶编码是否已经有父节点
                    if item.parent():
                        parent_data = item.parent().data(0, Qt.UserRole)
                        if parent_data and parent_data.get("level") == 3:
                            QMessageBox.warning(self, "警告",
                                                f"二阶编码 '{item.text(0)}' 已经有父节点三阶编码 '{item.parent().text(0)}'\n\n二阶只能对应一个三阶！")
                            return
                    second_level_items.append(item)

            if not second_level_items:
                QMessageBox.warning(self, "警告", "请选中二阶编码！")
                return

            # 输入三阶编码名称
            # 使用自定义对话框，包含更大的文本编辑框
            dialog = QDialog(self)
            dialog.setWindowTitle("添加三阶编码")
            dialog.resize(600, 500)  # 增大对话框尺寸

            layout = QVBoxLayout(dialog)

            label = QLabel(f"为 {len(second_level_items)} 个二阶编码添加父节点三阶编码 (输入内容):")
            layout.addWidget(label)

            text_edit = QTextEdit()
            text_edit.setMinimumHeight(250)  # 增加最小高度
            text_edit.setMaximumHeight(350)  # 设置最大高度
            text_edit.setPlaceholderText("输入三阶编码内容...")
            layout.addWidget(text_edit)

            button_layout = QHBoxLayout()
            ok_button = QPushButton("确定")
            cancel_button = QPushButton("取消")
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            def on_ok():
                third_name = text_edit.toPlainText().strip()
                if not third_name:
                    QMessageBox.warning(dialog, "警告", "三阶编码名称不能为空")
                    return

                is_valid, clean_name, error_msg = self.validate_category_name(third_name, "third")
                if not is_valid:
                    QMessageBox.warning(dialog, "验证错误", error_msg)
                    return

                # 生成三阶编码ID
                code_id = self.generate_third_code_id()
                numbered_name = f"{code_id} {clean_name}"

                # 创建三阶节点
                third_item = QTreeWidgetItem(self.coding_tree)
                third_item.setText(0, numbered_name)  # 显示带编号的名称
                third_item.setText(1, "三阶编码")
                third_item.setText(3, "0")  # 文件来源数
                third_item.setText(4, "0")  # 句子来源数
                third_item.setText(5, code_id)  # 关联编号
                third_item.setData(0, Qt.UserRole, {
                    "level": 3,
                    "name": clean_name,
                    "code_id": code_id  # 添加编号ID
                })

                # 移动二阶编码到三阶下
                for item in second_level_items:
                    # 从原位置移除
                    parent = item.parent()
                    if parent:
                        parent.removeChild(item)
                    else:
                        index = self.coding_tree.indexOfTopLevelItem(item)
                        self.coding_tree.takeTopLevelItem(index)

                    # 添加到新的三阶下
                    third_item.addChild(item)

                    # 更新二阶的数据
                    item_data = item.data(0, Qt.UserRole)
                    item_data["parent"] = clean_name
                    item.setData(0, Qt.UserRole, item_data)

                    # 更新所有一阶子节点的core_category
                    for i in range(item.childCount()):
                        first_item = item.child(i)
                        first_data = first_item.data(0, Qt.UserRole)
                        first_data["core_category"] = clean_name
                        first_item.setData(0, Qt.UserRole, first_data)

                third_item.setText(2, str(len(second_level_items)))
                third_item.setExpanded(True)

                self.update_structured_codes_from_tree()
                logger.info(f"为 {len(second_level_items)} 个二阶编码添加了父节点三阶编码: {clean_name}")
                QMessageBox.information(self, "成功", f"已为 {len(second_level_items)} 个二阶编码添加三阶编码: {clean_name}")
                dialog.accept()

            ok_button.clicked.connect(on_ok)
            cancel_button.clicked.connect(dialog.reject)

            dialog.exec_()

        except Exception as e:
            logger.error(f"添加父节点三阶编码失败: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"添加失败:\n{str(e)}")

    def update_first_codes_display(self):
        """更新一阶编码列表显示（已弃用，调用update_coding_tree代替）"""
        self.update_coding_tree()

    def is_content_exists(self, content):
        """检查内容是否已存在"""
        # 检查未分类列表
        if content in self.unclassified_first_codes:
            return True

        # 检查已分类编码
        for third_cat, second_cats in self.current_codes.items():
            for second_cat, first_codes in second_cats.items():
                if content in first_codes:
                    return True

        return False

    def on_tree_item_double_clicked(self, item, column):
        """树节点双击事件"""
        self.edit_tree_item()

    def on_tree_item_clicked(self, item, column):
        """树形项目点击事件 - 修复导航定位"""
        try:
            item_data = item.data(0, Qt.UserRole)
            if not item_data:
                return

            level = item_data.get("level")
            if level == 1:  # 一阶编码
                content = item_data.get("content", "")
                code_id = item_data.get("code_id", "")
                sentence_details = item_data.get("sentence_details", [])

                # 显示所有关联句子的详细信息
                self.show_sentence_details_dialog(sentence_details, content, code_id)

                # 优先使用编码ID进行导航
                if code_id:
                    self.highlight_text_by_code_id(code_id)
                elif content:
                    self.highlight_text_content(content)
        except Exception as e:
            logger.error(f"点击树项目时出错: {e}")
            QMessageBox.warning(self, "错误", f"点击项目时发生错误: {str(e)}")

    def highlight_text_by_code_id(self, code_id: str):
        """通过编码ID高亮文本和对应内容"""
        try:
            if not code_id:
                return

            # 获取当前显示的文本
            current_text = self.text_display.toPlainText()
            if not current_text:
                return

            # 移动光标到文本开始
            cursor = self.text_display.textCursor()
            cursor.movePosition(cursor.Start)
            self.text_display.setTextCursor(cursor)

            # 清除之前的高亮
            self.clear_text_highlights()

            # 查找编码标记： [A11], [B22] 等
            pattern = f"[{code_id}]"
            found = False
            first_match_cursor = None  # 记录第一个匹配项的光标位置
            search_cursor = self.text_display.textCursor()
            search_cursor.movePosition(cursor.Start)

            # 使用while循环查找所有匹配项，但添加安全计数器防止无限循环
            search_count = 0
            max_searches = 100  # 设置最大搜索次数防止无限循环

            # 首先高亮编码标记
            while search_count < max_searches:
                # 查找编码标记
                search_cursor = self.text_document.find(pattern, search_cursor, QTextDocument.FindCaseSensitively)
                if search_cursor.isNull():
                    break

                # 设置高亮格式 - 编码标记保持默认样式，不进行高亮
                highlight_format = search_cursor.charFormat()
                highlight_format.setBackground(QColor(255, 255, 255))  # 白色背景
                highlight_format.setForeground(QColor(0, 0, 0))  # 黑色文字
                search_cursor.mergeCharFormat(highlight_format)
                #
                # 保持编码标记的默认样式，不进行任何高亮
                found = True

                # 记录第一个匹配项的位置
                if first_match_cursor is None:
                    first_match_cursor = self.text_display.textCursor()
                    first_match_cursor.setPosition(search_cursor.selectionStart())

                # 移动光标到找到的内容之后，防止重复匹配
                search_cursor.movePosition(search_cursor.Right, search_cursor.MoveAnchor, len(pattern))
                search_count += 1

            # 然后高亮与编码ID相关的一阶编码内容
            # 遍历树形结构，找到对应编码ID的一阶编码内容
            content_to_highlight = self.get_content_by_code_id(code_id)
            if content_to_highlight:
                # 清理内容，移除可能存在的标记
                clean_content = re.sub(r'\s*\[[A-Z]\d+\]', '', content_to_highlight).strip()
                if clean_content:
                    content_cursor = self.text_display.textCursor()
                    content_cursor.movePosition(content_cursor.Start)

                    content_search_count = 0
                    while content_search_count < max_searches:
                        content_cursor = self.text_document.find(clean_content, content_cursor,
                                                                 QTextDocument.FindCaseSensitively)
                        if content_cursor.isNull():
                            break

                        # 检查是否与编码标记重叠，避免重复高亮
                        # 设置高亮格式（使用不同颜色区分）
                        content_highlight_format = content_cursor.charFormat()
                        content_highlight_format.setBackground(QColor(173, 216, 230))  # 浅蓝色背景
                        content_highlight_format.setForeground(QColor(0, 0, 139))  # 深蓝色文字

                        # 应用高亮
                        content_cursor.mergeCharFormat(content_highlight_format)

                        # 移动光标到找到的内容之后，防止重复匹配
                        content_cursor.movePosition(content_cursor.Right, content_cursor.MoveAnchor, len(clean_content))
                        content_search_count += 1

            if found and first_match_cursor:
                # 滚动到第一个匹配项的位置
                self.text_display.setTextCursor(first_match_cursor)
                self.text_display.ensureCursorVisible()  # 确保光标位置可见
                self.statusBar().showMessage(f"已高亮编码 {code_id} 及其对应内容，定位到第一个匹配项") if hasattr(self,
                                                                                             'statusBar') else None
            else:
                self.statusBar().showMessage(f"未找到编码 {code_id} 的标记") if hasattr(self, 'statusBar') else None
        except Exception as e:
            logger.error(f"高亮编码ID时出错: {e}")
            QMessageBox.warning(self, "错误", f"高亮编码时发生错误: {str(e)}")

    def get_content_by_code_id(self, code_id: str) -> str:
        """根据编码ID获取对应的一阶编码内容"""
        try:
            # 遍历树形结构查找匹配的编码ID
            def search_tree_item(item):
                for i in range(item.childCount()):
                    child = item.child(i)
                    child_data = child.data(0, Qt.UserRole)

                    if child_data:
                        # 检查当前节点是否匹配
                        if child_data.get("code_id") == code_id:
                            return child_data.get("content", "")

                        # 递归搜索子节点
                        result = search_tree_item(child)
                        if result:
                            return result

                return ""

            # 遍历顶层项目
            for i in range(self.coding_tree.topLevelItemCount()):
                top_item = self.coding_tree.topLevelItem(i)
                result = search_tree_item(top_item)
                if result:
                    return result

            # 如果在层级结构中没找到，检查顶层未分类的一阶编码
            for i in range(self.coding_tree.topLevelItemCount()):
                top_item = self.coding_tree.topLevelItem(i)
                top_data = top_item.data(0, Qt.UserRole)
                if top_data and top_data.get("level") == 1 and top_data.get("code_id") == code_id:
                    return top_data.get("content", "")

            return ""
        except Exception as e:
            logger.error(f"获取编码内容时出错: {e}")
            return ""

    def get_code_id_by_content(self, content: str) -> str:
        """根据内容获取对应的编码ID"""
        try:
            # 清理内容以进行匹配
            clean_content = re.sub(r'\s*\[[A-Z]\d+\]', '', content).strip()
            if not clean_content:
                return ""

            # 遍历树形结构查找匹配的内容
            def search_tree_item(item):
                for i in range(item.childCount()):
                    child = item.child(i)
                    child_data = child.data(0, Qt.UserRole)

                    if child_data:
                        # 检查当前节点的内容是否匹配
                        child_content = re.sub(r'\s*\[[A-Z]\d+\]', '', child_data.get("content", "")).strip()
                        if child_content == clean_content:
                            return child_data.get("code_id", "")

                        # 递归搜索子节点
                        result = search_tree_item(child)
                        if result:
                            return result

                return ""

            # 遍历顶层项目
            for i in range(self.coding_tree.topLevelItemCount()):
                top_item = self.coding_tree.topLevelItem(i)
                result = search_tree_item(top_item)
                if result:
                    return result

            # 如果在层级结构中没找到，检查顶层未分类的一阶编码
            for i in range(self.coding_tree.topLevelItemCount()):
                top_item = self.coding_tree.topLevelItem(i)
                top_data = top_item.data(0, Qt.UserRole)
                if top_data and top_data.get("level") == 1:
                    top_content = re.sub(r'\s*\[[A-Z]\d+\]', '', top_data.get("content", "")).strip()
                    if top_content == clean_content:
                        return top_data.get("code_id", "")

            return ""
        except Exception as e:
            logger.error(f"获取编码ID时出错: {e}")
            return ""

    def highlight_text_content(self, content: str):
        """在文本中高亮内容"""
        try:
            if not content or len(content) < 2:  # 减少最小长度要求
                return

            # 获取当前显示的文本
            current_text = self.text_display.toPlainText()
            if not current_text:
                return

            # 移动光标到文本开始
            cursor = self.text_display.textCursor()
            cursor.movePosition(cursor.Start)
            self.text_display.setTextCursor(cursor)

            # 清除之前的高亮
            self.clear_text_highlights()

            # 查找文本
            found = False
            first_match_cursor = None  # 记录第一个匹配项的光标位置
            search_cursor = self.text_display.textCursor()
            search_cursor.movePosition(cursor.Start)

            # 清理内容，移除可能存在的标记
            clean_content = re.sub(r'\s*\[[A-Z]\d+\]', '', content).strip()

            # 检查清理后的内容是否为空
            if not clean_content:
                return

            # 使用while循环查找所有匹配项，但添加安全计数器防止无限循环
            search_count = 0
            max_searches = 100  # 设置最大搜索次数防止无限循环

            while search_count < max_searches:
                search_cursor = self.text_document.find(clean_content, search_cursor, QTextDocument.FindCaseSensitively)
                if search_cursor.isNull():
                    break

                # 设置高亮格式
                highlight_format = search_cursor.charFormat()
                highlight_format.setBackground(QColor(173, 216, 230))  # 浅蓝色背景
                highlight_format.setForeground(QColor(0, 0, 139))  # 深蓝色文字

                # 应用高亮
                search_cursor.mergeCharFormat(highlight_format)
                found = True

                # 记录第一个匹配项的位置
                if first_match_cursor is None:
                    first_match_cursor = self.text_display.textCursor()
                    first_match_cursor.setPosition(search_cursor.selectionStart())

                # 移动光标到找到的内容之后，防止重复匹配
                search_cursor.movePosition(search_cursor.Right, search_cursor.MoveAnchor, len(clean_content))
                search_count += 1

            # 如果内容与某个编码相关，也高亮编码标记
            code_id = self.get_code_id_by_content(clean_content)
            if code_id:
                pattern = f"[{code_id}]"
                code_cursor = self.text_display.textCursor()
                code_cursor.movePosition(code_cursor.Start)

                code_search_count = 0
                while code_search_count < max_searches:
                    code_cursor = self.text_document.find(pattern, code_cursor, QTextDocument.FindCaseSensitively)
                    if code_cursor.isNull():
                        break

                    # 设置编码标记的高亮格式 - 保持默认样式，不进行高亮
                    # code_highlight_format = code_cursor.charFormat()
                    # code_highlight_format.setBackground(QColor(255, 255, 255))  # 白色背景
                    # code_highlight_format.setForeground(QColor(0, 0, 0))  # 黑色文字
                    # code_cursor.mergeCharFormat(code_highlight_format)

                    # 保持编码标记的默认样式，不进行任何高亮

                    # 移动光标到找到的内容之后，防止重复匹配
                    code_cursor.movePosition(code_cursor.Right, code_cursor.MoveAnchor, len(pattern))
                    code_search_count += 1

            if found and first_match_cursor:
                # 滚动到第一个匹配项的位置
                self.text_display.setTextCursor(first_match_cursor)
                self.text_display.ensureCursorVisible()  # 确保光标位置可见
                self.statusBar().showMessage(f"已高亮内容: {clean_content[:50]}...，并定位到第一个匹配项") if hasattr(self,
                                                                                                      'statusBar') else None
            else:
                self.statusBar().showMessage(f"未找到内容: {clean_content[:50]}...") if hasattr(self, 'statusBar') else None
        except Exception as e:
            logger.error(f"高亮文本内容时出错: {e}")
            QMessageBox.warning(self, "错误", f"高亮文本时发生错误: {str(e)}")

    def clear_text_highlights(self):
        """清除文本高亮"""
        try:
            # 获取整个文档
            cursor = self.text_display.textCursor()
            cursor.select(cursor.Document)

            # 重置格式
            format = cursor.charFormat()
            format.setBackground(QColor(255, 255, 255))  # 白色背景
            format.setForeground(QColor(0, 0, 0))  # 黑色文字
            cursor.mergeCharFormat(format)

            # 取消选择
            cursor.clearSelection()
            self.text_display.setTextCursor(cursor)

        except Exception as e:
            logger.error(f"清除高亮失败: {e}")

    def get_coding_result(self):
        """获取编码结果"""
        return self.current_codes

    def build_tree_data(self):
        """构建完整的树形结构数据用于保存"""
        # 先更新内部数据结构以确保是最新的
        self.update_structured_codes_from_tree()

        tree_data = {
            "current_codes": self.current_codes,
            "unclassified_first_codes": self.unclassified_first_codes,
            "tree_structure": self.capture_tree_state()
        }
        return tree_data

    def extract_tree_data(self):
        """从树形控件提取完整数据结构"""
        # 为了向后兼容，调用新方法
        return self.build_tree_data()

    def capture_tree_state(self):
        """捕获当前树的状态"""

        def capture_item(item):
            item_data = item.data(0, Qt.UserRole)
            children = []

            for i in range(item.childCount()):
                child = item.child(i)
                children.append(capture_item(child))

            # 返回包含文本、数据和子项的完整信息
            return {
                "texts": [item.text(col) for col in range(min(item.columnCount(), 6))],  # 只保留前6列
                "data": item_data,
                "children": children
            }

        root_items = []
        for i in range(self.coding_tree.topLevelItemCount()):
            item = self.coding_tree.topLevelItem(i)
            root_items.append(capture_item(item))

        return root_items

    def serialize_tree(self):
        """序列化树形结构"""
        # 为了向后兼容，调用新方法
        return self.capture_tree_state()

    def rebuild_tree_from_data(self, tree_data):
        """从数据重建树形结构"""
        try:
            # 清空当前树
            self.coding_tree.clear()

            # 恢复数据
            if "current_codes" in tree_data:
                self.current_codes = tree_data["current_codes"]
            if "unclassified_first_codes" in tree_data:
                self.unclassified_first_codes = tree_data["unclassified_first_codes"]

            # 从序列化的树结构重建树
            if "tree_structure" in tree_data:
                tree_structure = tree_data["tree_structure"]
                self.restore_tree_state(tree_structure)
            else:
                # 如果没有树结构数据，使用旧方法更新
                self.update_coding_tree()

        except Exception as e:
            logger.error(f"重建树形结构失败: {e}")
            import traceback
            traceback.print_exc()
            # 回退到使用update_coding_tree方法
            self.update_coding_tree()

    def restore_tree_state(self, tree_structure):
        """恢复树的状态"""

        def restore_item(item_dict):
            item = QTreeWidgetItem()

            # 设置列文本
            for col_idx, text in enumerate(item_dict["texts"]):
                item.setText(col_idx, text)

            # 设置数据
            item.setData(0, Qt.UserRole, item_dict["data"])

            # 递归添加子项
            for child_dict in item_dict["children"]:
                child_item = restore_item(child_dict)
                item.addChild(child_item)

            return item

        # 清空树并重建根项
        for item_dict in tree_structure:
            root_item = restore_item(item_dict)
            self.coding_tree.addTopLevelItem(root_item)

    def deserialize_tree(self, tree_structure):
        """反序列化树形结构"""
        # 为了向后兼容，调用新方法
        self.restore_tree_state(tree_structure)

    def update_coding_tree(self):
        """更新编码结构树"""

    def save_coding_tree(self):
        """保存当前编码树到文件 - 保存完整的树形结构"""
        try:
            from PyQt5.QtWidgets import QFileDialog

            # 获取保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存编码树", "", "JSON文件 (*.json);;所有文件 (*)"
            )

            if file_path:
                # 从树形控件构建完整的数据结构
                tree_data = self.extract_tree_data()

                # 保存完整的编码结构
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(tree_data, f, ensure_ascii=False, indent=2)

                QMessageBox.information(self, "成功", f"编码树已保存到: {file_path}")
                logger.info(f"编码树已保存: {file_path}")

        except Exception as e:
            logger.error(f"保存编码树失败: {e}")
            QMessageBox.critical(self, "错误", f"保存编码树失败: {str(e)}")

    def import_coding_tree(self):
        """从文件导入编码树 - 恢复完整的树形结构"""
        try:
            from PyQt5.QtWidgets import QFileDialog

            # 获取导入路径
            file_path, _ = QFileDialog.getOpenFileName(
                self, "导入编码树", "", "JSON文件 (*.json);;所有文件 (*)"
            )

            if file_path:
                # 读取编码结构
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_tree_data = json.load(f)

                # 询问用户是否确认导入编码树
                reply = QMessageBox.question(
                    self, "确认导入",
                    "确定要导入编码树吗？这将替换当前的编码结构。",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    # 使用导入的数据重建树形结构
                    self.rebuild_tree_from_data(imported_tree_data)

                    QMessageBox.information(self, "成功", f"编码树已从 {file_path} 导入")
                    logger.info(f"编码树已导入: {file_path}")

        except Exception as e:
            logger.error(f"导入编码树失败: {e}")
            QMessageBox.critical(self, "错误", f"导入编码树失败: {str(e)}")

    def show_sentence_details_dialog(self, sentence_details, content, code_id):
        """显示句子详情对话框"""
        try:
            if not sentence_details:
                # 如果没有句子详情，至少显示当前内容
                sentence_details = [{"text": content, "code_id": code_id}]

            # 创建对话框
            dialog = QDialog(self)
            dialog.setWindowTitle(
                f"句子详情 - {code_id}: {content[:30]}..." if len(content) > 30 else f"句子详情 - {code_id}: {content}")
            dialog.resize(800, 600)

            layout = QVBoxLayout(dialog)

            # 创建文本显示区域
            text_display = QTextEdit()
            text_display.setReadOnly(True)

            # 构建显示内容
            display_text = f"一阶编码: {code_id}: {content}\n"
            display_text += "=" * 50 + "\n\n"

            for i, detail in enumerate(sentence_details, 1):
                if isinstance(detail, dict):
                    text = detail.get('text', '')
                    detail_code_id = detail.get('code_id', '')
                    file_path = detail.get('file_path', '')
                    sentence_id = detail.get('sentence_id', '')

                    display_text += f"句子 {i}:\n"
                    if detail_code_id:
                        # 从文本中提取所有句子编号（例如 [2018][2028] 格式)
                        sentence_number_matches = re.findall(r"\[(\d+)\]", text)
                        if sentence_number_matches:
                            # 如果有多个编号，显示所有编号
                            all_numbers = ", ".join(sentence_number_matches)
                            display_text += f"  编号: {all_numbers}\n"
                        else:
                            # 如果没有找到编号，使用原来的sentence_id
                            display_text += f"  编号: {sentence_id}\n"
                    else:
                        display_text += f"  编号: {sentence_id}\n"
                    if file_path:
                        display_text += f"  文件: {file_path}\n"
                    if sentence_id:
                        display_text += f"  句子ID: {sentence_id}\n"
                    # 清理内容显示，去除多余引号和格式化
                    clean_text = str(text).strip().strip("'").strip('"')
                    # 将换行符替换为可视化的分隔符
                    clean_text = clean_text.replace('\n', ' | ')
                    display_text += f"  内容: {clean_text}\n\n"
                else:
                    # 如果是字符串或其他格式
                    display_text += f"句子 {i}:\n"
                    display_text += f"  内容: {detail}\n\n"

            text_display.setPlainText(display_text)
            layout.addWidget(text_display)

            # 添加按钮
            button_layout = QHBoxLayout()
            button_layout.addStretch()

            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(dialog.close)
            button_layout.addWidget(close_btn)

            layout.addLayout(button_layout)

            # 显示对话框（非模态）
            dialog.show()

        except Exception as e:
            logger.error(f"显示句子详情对话框时出错: {e}")
            QMessageBox.warning(self, "错误", f"显示句子详情时发生错误: {str(e)}")

    def show_tree_context_menu(self, position):
        """显示树形控件上下文菜单"""
        from PyQt5.QtWidgets import QMenu, QAction

        menu = QMenu()

        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(self.edit_tree_item)
        menu.addAction(edit_action)

        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self.delete_tree_item)
        menu.addAction(delete_action)

        menu.addSeparator()

        add_second_action = QAction("为一阶添加父节点(二阶)", self)
        add_second_action.triggered.connect(self.add_parent_second_for_first)
        menu.addAction(add_second_action)

        add_third_action = QAction("为二阶添加父节点(三阶)", self)
        add_third_action.triggered.connect(self.add_parent_third_for_second)
        menu.addAction(add_third_action)

        menu.exec_(self.coding_tree.viewport().mapToGlobal(position))

    def edit_tree_item(self):
        """编辑树节点"""
        current_item = self.coding_tree.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择一个节点")
            return

        item_data = current_item.data(0, Qt.UserRole)
        if not item_data:
            return

        level = item_data.get("level")
        old_content = current_item.text(0)

        if level == 1:
            dialog = QDialog(self)
            dialog.setWindowTitle("编辑一阶编码")
            dialog.resize(600, 600)  # 增大对话框尺寸

            layout = QVBoxLayout(dialog)

            label = QLabel(f"编辑一阶编码 (当前: {old_content[:20]}{'...' if len(old_content) > 20 else ''}):")
            layout.addWidget(label)

            text_edit = QTextEdit()
            text_edit.setPlainText(old_content)
            text_edit.setMinimumHeight(250)
            text_edit.setMaximumHeight(350)
            layout.addWidget(text_edit)

            button_layout = QHBoxLayout()
            ok_button = QPushButton("确定")
            cancel_button = QPushButton("取消")
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            def on_ok():
                new_content = text_edit.toPlainText().strip()
                if not new_content:
                    QMessageBox.warning(dialog, "警告", "一阶编码内容不能为空")
                    return

                is_valid, clean_content, error_msg = self.validate_category_name(new_content, "first")
                if not is_valid:
                    QMessageBox.warning(dialog, "验证错误", error_msg)
                    return

                if clean_content != old_content:
                    current_item.setText(0, clean_content)
                    item_data["content"] = clean_content
                    item_data["numbered_content"] = clean_content  # 更新带编号的内容
                    current_item.setData(0, Qt.UserRole, item_data)
                    self.update_structured_codes_from_tree()
                    logger.info(f"修改一阶编码: {old_content} → {clean_content}")

                dialog.accept()

            ok_button.clicked.connect(on_ok)
            cancel_button.clicked.connect(dialog.reject)

            dialog.exec_()

        elif level == 2:
            # 编辑二阶编码
            dialog = QDialog(self)
            dialog.setWindowTitle("编辑二阶编码")
            dialog.resize(600, 500)  # 增大对话框尺寸

            layout = QVBoxLayout(dialog)

            label = QLabel(f"编辑二阶编码 (当前: {old_content[:20]}{'...' if len(old_content) > 20 else ''}):")
            layout.addWidget(label)

            text_edit = QTextEdit()
            text_edit.setPlainText(old_content)
            text_edit.setMinimumHeight(250)  # 增加最小高度
            text_edit.setMaximumHeight(350)  # 设置最大高度
            layout.addWidget(text_edit)

            button_layout = QHBoxLayout()
            ok_button = QPushButton("确定")
            cancel_button = QPushButton("取消")
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            def on_ok():
                new_name = text_edit.toPlainText().strip()
                if not new_name:
                    QMessageBox.warning(dialog, "警告", "二阶编码名称不能为空")
                    return

                is_valid, clean_name, error_msg = self.validate_category_name(new_name, "second")
                if not is_valid:
                    QMessageBox.warning(dialog, "验证错误", error_msg)
                    return

                if clean_name != old_content:
                    current_item.setText(0, clean_name)
                    item_data["name"] = clean_name
                    current_item.setData(0, Qt.UserRole, item_data)
                    self.update_structured_codes_from_tree()
                    logger.info(f"修改二阶编码: {old_content} → {clean_name}")

                dialog.accept()

            ok_button.clicked.connect(on_ok)
            cancel_button.clicked.connect(dialog.reject)

            dialog.exec_()

        elif level == 3:
            # 编辑三阶编码
            dialog = QDialog(self)
            dialog.setWindowTitle("编辑三阶编码")
            dialog.resize(600, 500)  # 增大对话框尺寸

            layout = QVBoxLayout(dialog)

            label = QLabel(f"编辑三阶编码 (当前: {old_content[:20]}{'...' if len(old_content) > 20 else ''}):")
            layout.addWidget(label)

            text_edit = QTextEdit()
            text_edit.setPlainText(old_content)
            text_edit.setMinimumHeight(250)  # 增加最小高度
            text_edit.setMaximumHeight(350)  # 设置最大高度
            layout.addWidget(text_edit)

            button_layout = QHBoxLayout()
            ok_button = QPushButton("确定")
            cancel_button = QPushButton("取消")
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            def on_ok():
                new_name = text_edit.toPlainText().strip()
                if not new_name:
                    QMessageBox.warning(dialog, "警告", "三阶编码名称不能为空")
                    return

                is_valid, clean_name, error_msg = self.validate_category_name(new_name, "third")
                if not is_valid:
                    QMessageBox.warning(dialog, "验证错误", error_msg)
                    return

                if clean_name != old_content:
                    current_item.setText(0, clean_name)
                    item_data["name"] = clean_name
                    current_item.setData(0, Qt.UserRole, item_data)
                    self.update_structured_codes_from_tree()
                    logger.info(f"修改三阶编码: {old_content} → {clean_name}")

                dialog.accept()

            ok_button.clicked.connect(on_ok)
            cancel_button.clicked.connect(dialog.reject)

            dialog.exec_()

    def delete_tree_item(self):
        """删除树节点"""
        current_item = self.coding_tree.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择一个节点")
            return

        item_data = current_item.data(0, Qt.UserRole)
        if not item_data:
            return

        level = item_data.get("level")
        content = current_item.text(0)

        # 确认删除
        if level == 3:
            child_count = current_item.childCount()
            msg = f"确定要删除三阶编码 '{content}' 及其下的 {child_count} 个二阶编码吗？"
        elif level == 2:
            child_count = current_item.childCount()
            msg = f"确定要删除二阶编码 '{content}' 及其下的 {child_count} 个一阶编码吗？"
        else:
            msg = f"确定要删除一阶编码 '{content}' 吗？"

        reply = QMessageBox.question(self, "确认删除", msg, QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            parent = current_item.parent()
            if parent:
                parent.removeChild(current_item)
            else:
                index = self.coding_tree.indexOfTopLevelItem(current_item)
                self.coding_tree.takeTopLevelItem(index)

            self.update_structured_codes_from_tree()
            logger.info(f"删除{level}阶编码: {content}")

    def update_structured_codes_from_tree(self):
        """从树形结构更新编码数据"""
        self.current_codes = {}
        self.unclassified_first_codes = []

        for i in range(self.coding_tree.topLevelItemCount()):
            top_item = self.coding_tree.topLevelItem(i)
            item_data = top_item.data(0, Qt.UserRole)

            if not item_data:
                continue

            level = item_data.get("level")

            if level == 3:
                # 三阶编码
                third_display_name = top_item.text(0)
                # 解析显示名称，获取原始名称（去掉编号）
                import re
                third_parts = third_display_name.split(' ', 1)
                if len(third_parts) > 1 and re.match(r'^[A-Z]\d{2}$', third_parts[0]):
                    third_name = third_parts[1]
                else:
                    third_name = third_display_name

                self.current_codes[third_display_name] = {}

                for j in range(top_item.childCount()):
                    second_item = top_item.child(j)
                    second_display_name = second_item.text(0)
                    # 解析二阶编码名称，获取原始名称（去掉编号）
                    import re
                    second_parts = second_display_name.split(' ', 1)
                    if len(second_parts) > 1 and re.match(r'^[A-Z]\d{2}$', second_parts[0]):
                        second_name = second_parts[1]
                    else:
                        second_name = second_display_name

                    self.current_codes[third_display_name][second_display_name] = []

                    for k in range(second_item.childCount()):
                        first_item = second_item.child(k)
                        # 获取原始内容，优先使用完整数据结构
                        first_item_data = first_item.data(0, Qt.UserRole)

                        # 如果是字典格式，更新统计数据
                        if first_item_data and isinstance(first_item_data, dict):
                            # 更新一阶编码的统计数据
                            first_item_data["sentence_count"] = int(first_item.text(4)) if first_item.text(
                                4).isdigit() else 1
                            first_item_data["code_id"] = first_item.text(5) if first_item.text(
                                5) else first_item_data.get("code_id", "")

                            # 处理句子详情，确保包含所有相关信息
                            sentence_details = first_item_data.get("sentence_details", [])
                            if not sentence_details:
                                # 如果没有句子详情，创建一个基本结构
                                sentence_details = [{
                                    "text": first_item.text(0),
                                    "code_id": first_item_data.get("code_id", ""),
                                    "file_path": "",
                                    "sentence_id": ""
                                }]
                            first_item_data["sentence_details"] = sentence_details

                            self.current_codes[third_display_name][second_display_name].append(first_item_data)
                        else:
                            # 后备方案：使用文本内容
                            first_content = first_item.text(0)
                            self.current_codes[third_display_name][second_display_name].append(first_content)

            elif level == 1:
                # 未分类的一阶编码
                if not item_data.get("classified", True):
                    # 尝试获取完整数据结构，否则使用文本内容
                    if isinstance(item_data, dict):
                        # 更新未分类一阶编码的统计数据
                        item_data["sentence_count"] = int(top_item.text(4)) if top_item.text(4).isdigit() else 1
                        item_data["code_id"] = top_item.text(5) if top_item.text(5) else item_data.get("code_id", "")
                        self.unclassified_first_codes.append(item_data)
                    else:
                        content = top_item.text(0)
                        self.unclassified_first_codes.append(content)

    def update_coding_tree(self):
        """更新编码结构树"""
        try:
            self.coding_tree.clear()

            # 添加三阶编码及其子节点
            for third_cat, second_cats in self.current_codes.items():
                # 解析三阶编码名称，提取编号和内容
                import re
                third_parts = third_cat.split(' ', 1)
                if len(third_parts) > 1 and re.match(r'^[A-Z]\d{2}$', third_parts[0]):
                    third_code_id = third_parts[0]
                    third_name = third_parts[1]
                else:
                    third_code_id = "C01"  # 默认ID
                    third_name = third_cat

                third_item = QTreeWidgetItem(self.coding_tree)
                third_item.setText(0, third_cat)  # 显示带编号的名称
                third_item.setText(1, "三阶编码")
                third_item.setData(0, Qt.UserRole, {"level": 3, "name": third_name, "code_id": third_code_id})

                second_count = 0
                first_count = 0

                # 计算三阶编码的统计数据
                third_file_sources = set()
                third_sentence_sources = set()
                third_code_ids = []

                for second_cat, first_contents in second_cats.items():
                    # 解析二阶编码名称，提取编号和内容
                    import re
                    second_parts = second_cat.split(' ', 1)
                    if len(second_parts) > 1 and re.match(r'^[A-Z]\d{2}$', second_parts[0]):
                        second_code_id = second_parts[0]
                        second_name = second_parts[1]
                    else:
                        second_code_id = "B01"  # 默认ID
                        second_name = second_cat

                    second_item = QTreeWidgetItem(third_item)
                    second_item.setText(0, second_cat)  # 显示带编号的名称
                    second_item.setText(1, "二阶编码")
                    second_item.setData(0, Qt.UserRole, {
                        "level": 2,
                        "name": second_name,
                        "code_id": second_code_id,
                        "parent": third_cat
                    })

                    # 计算二阶编码的统计数据
                    second_file_sources = set()
                    second_sentence_sources = set()
                    second_code_ids = []

                    for content in first_contents:
                        first_item = QTreeWidgetItem(second_item)
                        if isinstance(content, dict):
                            content_text = content.get('content', str(content))
                            code_id = content.get('code_id', '')
                            sentence_details = content.get('sentence_details', [])
                            sentence_count = content.get('sentence_count', 1)
                        else:
                            content_text = str(content)
                            code_id = ""
                            sentence_details = []
                            sentence_count = 1

                        # 计算一阶编码的统计数据
                        first_file_sources = set()
                        first_sentence_sources = set()

                        for sentence in sentence_details:
                            if isinstance(sentence, dict):
                                file_path = sentence.get('file_path', '')
                                sentence_id = sentence.get('sentence_id', '')

                                if file_path:
                                    first_file_sources.add(file_path)
                                    second_file_sources.add(file_path)  # 添加到二阶文件来源
                                    third_file_sources.add(file_path)
                                if sentence_id:
                                    first_sentence_sources.add(str(sentence_id))
                                    second_sentence_sources.add(str(sentence_id))
                                    third_sentence_sources.add(str(sentence_id))

                        # 添加编码ID
                        if code_id:
                            second_code_ids.append(code_id)
                            third_code_ids.append(code_id)

                        # 设置文本显示
                        # 如果内容已经有编号，则直接使用，否则使用编号格式
                        if code_id:
                            numbered_first_content = f"{code_id} {content_text}"
                            first_item.setText(0, numbered_first_content)
                        else:
                            first_item.setText(0, content_text)

                        first_item.setText(1, "一阶编码")
                        first_item.setText(2, "1")
                        first_item.setText(3, str(len(first_file_sources)) if first_file_sources else "1")  # 文件来源数
                        first_item.setText(4, str(len(
                            first_sentence_sources) if first_sentence_sources else sentence_count))  # 句子来源数
                        first_item.setText(5, code_id if code_id else "")  # 关联编号
                        first_item.setData(0, Qt.UserRole, {
                            "level": 1,
                            "name": content_text,
                            "numbered_content": numbered_first_content if code_id else content_text,
                            "parent": second_cat,
                            "code_id": code_id,
                            "sentence_details": sentence_details,
                            "sentence_count": sentence_count
                        })
                        first_count += 1

                    second_item.setText(2, str(first_count))
                    second_item.setText(3, str(len(second_file_sources)) if second_file_sources else "0")  # 文件来源数
                    # 计算二阶编码的句子来源数：累加所有子一阶编码的句子数
                    total_sentence_count = 0
                    for content in first_contents:
                        if isinstance(content, dict):
                            sentence_count = content.get('sentence_count', 1)
                            sentence_details = content.get('sentence_details', [])
                            # 使用句子详情的数量或sentence_count中的较大值
                            content_sentence_count = max(len(sentence_details), sentence_count)
                        else:
                            content_sentence_count = 1
                        total_sentence_count += content_sentence_count

                    second_item.setText(4, str(total_sentence_count))  # 句子来源数
                    second_item.setText(5, ", ".join(second_code_ids) if second_code_ids else "")  # 关联编号
                    second_count += 1

                third_item.setText(2, str(second_count))
                third_item.setText(3, str(len(third_file_sources)) if third_file_sources else "0")  # 文件来源数
                # 计算三阶编码的句子来源数：累加所有子一阶编码的句子数
                total_third_sentence_count = 0
                for second_cat, first_contents in second_cats.items():
                    for content in first_contents:
                        if isinstance(content, dict):
                            sentence_count = content.get('sentence_count', 1)
                            sentence_details = content.get('sentence_details', [])
                            # 使用句子详情的数量或sentence_count中的较大值
                            content_sentence_count = max(len(sentence_details), sentence_count)
                        else:
                            content_sentence_count = 1
                        total_third_sentence_count += content_sentence_count

                third_item.setText(4, str(total_third_sentence_count))  # 句子来源数
                third_item.setText(5, ", ".join(third_code_ids) if third_code_ids else "")  # 关联编号

            # 添加未分类的一阶编码
            for first_code in self.unclassified_first_codes:
                first_item = QTreeWidgetItem(self.coding_tree)

                # 处理first_code，它可能是一个字典或字符串
                if isinstance(first_code, dict):
                    # 如果是字典，获取内容和编号
                    content_text = first_code.get('content', str(first_code))
                    code_id = first_code.get('code_id', '')
                    numbered_content = first_code.get('numbered_content',
                                                      f"{code_id}: {content_text}" if code_id else content_text)
                    sentence_count = first_code.get('sentence_count', 1)
                    sentence_details = first_code.get('sentence_details', [])

                    first_item.setText(0, numbered_content)
                    first_item.setText(1, "一阶编码")
                    first_item.setText(2, "1")
                    first_item.setText(3, "1")  # 文件来源数
                    first_item.setText(4, str(sentence_count))  # 句子来源数
                    first_item.setText(5, code_id if code_id else "")  # 关联编号

                    first_item.setData(0, Qt.UserRole, first_code)
                else:
                    # 如果是字符串，可能是带编号的或不带编号的
                    first_item.setText(0, str(first_code))
                    first_item.setText(1, "一阶编码")
                    first_item.setText(2, "1")
                    first_item.setText(3, "1")  # 文件来源数
                    first_item.setText(4, "1")  # 句子来源数
                    first_item.setText(5, "")  # 关联编号

                    first_item.setData(0, Qt.UserRole, {
                        "level": 1,
                        "name": str(first_code),
                        "classified": False
                    })

            self.coding_tree.expandAll()

        except Exception as e:
            logger.error(f"更新编码结构树时出错: {e}")
            QMessageBox.critical(self, "错误", f"更新编码结构树时出错: {e}")

    def validate_category_name(self, name, level):
        """验证编码名称"""
        if not name:
            return False, "", "编码名称不能为空"

        if level == "first":
            if len(name) > 100:
                return False, "", "一阶编码名称不能超过100个字符"
        elif level == "second":
            if len(name) > 100:
                return False, "", "二阶编码名称不能超过100个字符"
        elif level == "third":
            if len(name) > 100:
                return False, "", "三阶编码名称不能超过100个字符"

        clean_name = name.strip()
        return True, clean_name.strip(), ""

    def generate_second_code_id(self, third_letter="B"):
        """生成二阶编码ID：B01, B02, B03...（B开头，数字递增）"""
        # 统计所有已存在的二阶编码ID，找到最大的编号
        existing_second_numbers = []
        for i in range(self.coding_tree.topLevelItemCount()):
            top_item = self.coding_tree.topLevelItem(i)
            for j in range(top_item.childCount()):
                second_item = top_item.child(j)
                second_data = second_item.data(0, Qt.UserRole)
                if second_data and second_data.get("level") == 2:
                    second_name = second_item.text(0)
                    # 提取编号部分
                    import re
                    parts = second_name.split(' ', 1)
                    if len(parts) > 0:
                        code_part = parts[0]
                        # 检查编号是否以字母开头并有两位数字
                        match = re.match(r'^([A-Z])(\d{2})$', code_part)
                        if match:
                            letter_part = match.group(1)
                            number_part = match.group(2)
                            # 如果是B开头的编号，则记录数字
                            if letter_part == 'B':
                                existing_second_numbers.append(int(number_part))

        # 找到下一个可用的编号
        if existing_second_numbers:
            next_number = max(existing_second_numbers) + 1
        else:
            next_number = 1

        return f"B{next_number:02d}"

    def generate_third_code_id(self):
        """生成三阶编码ID：C01, C02, C03...（C开头，数字递增）"""
        # 统计所有已存在的三阶编码ID，找到最大的编号
        existing_numbers = []
        for i in range(self.coding_tree.topLevelItemCount()):
            top_item = self.coding_tree.topLevelItem(i)
            top_data = top_item.data(0, Qt.UserRole)
            if top_data and top_data.get("level") == 3:
                top_text = top_item.text(0)
                # 提取开头的字母
                if top_text and len(top_text) > 0:
                    # 分割显示名称，获取编号部分
                    import re
                    parts = top_text.split(' ', 1)
                    if len(parts) > 0:
                        code_part = parts[0]
                        # 检查编号是否以字母开头并有两位数字
                        match = re.match(r'^([A-Z])(\d{2})$', code_part)
                        if match:
                            letter_part = match.group(1)
                            number_part = match.group(2)
                            # 如果是C开头的编号，则记录数字
                            if letter_part == 'C':
                                existing_numbers.append(int(number_part))

        # 找到下一个可用的编号
        if existing_numbers:
            next_number = max(existing_numbers) + 1
        else:
            next_number = 1  # 从1开始

        return f"C{next_number:02d}"

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

    def add_first_level_direct(self):
        """直接添加一阶编码 - 添加到树的根部作为未分类"""
        try:
            # 获取一阶编码内容
            first_content = self.first_content_edit.toPlainText().strip()

            if not first_content:
                QMessageBox.warning(self, "警告", "请输入一阶编码内容")
                return

            # 验证编码内容
            is_valid, clean_content, error_msg = self.validate_category_name(first_content, "first")
            if not is_valid:
                QMessageBox.warning(self, "验证错误", error_msg)
                return

            # 检查是否已存在
            if self.is_content_exists(clean_content):
                QMessageBox.warning(self, "警告", "该一阶编码已存在")
                return

            # 生成编码ID - 使用A开头的一阶编码系统
            code_id = self.generate_first_code_id()

            # 添加到树根部（未分类状态）
            item = QTreeWidgetItem(self.coding_tree)
            # 在内容前加上编号
            item.setText(0, f"{code_id}: {clean_content}")
            item.setText(1, "一阶编码")
            item.setText(2, "1")
            item.setText(3, "1")  # 文件来源数
            item.setText(4, "1")  # 句子来源数
            # 检查当前文本是否有选中的内容，并尝试从中提取TextNumberingManager的编号
            cursor = self.text_display.textCursor()
            selected_text = ""
            if cursor.hasSelection():
                selected_text = cursor.selectedText().strip()
            
            import re
            number_matches = re.findall(r'\[(\d+)\]', selected_text)
            if number_matches:
                # 使用最后一个匹配的数字编号作为来自TextNumberingManager的编号
                tmng_number = number_matches[-1]
                item.setText(5, tmng_number)  # 关联编号设置为来自TextNumberingManager的编号
            else:
                # 如果没有选中内容或没有找到TextNumberingManager编号，则使用code_id
                item.setText(5, code_id)  # 关联编号
            item.setData(0, Qt.UserRole, {
                "level": 1,
                "content": clean_content,
                "numbered_content": f"{code_id}: {clean_content}",  # 带编号的内容
                "code_id": code_id,
                "sentence_details": [],  # 记录句子来源信息
                "classified": False
            })

            # 如果当前文本中有选中的内容，尝试将其标记
            cursor = self.text_display.textCursor()
            if cursor.hasSelection():
                selected_text = cursor.selectedText().strip()
                if selected_text:
                    # 添加编码标记到选中文本
                    self.add_code_marker_to_text(selected_text, code_id)

            # 如果需要记录句子详情，可以从其他途径获取，而不是依赖选中的文本
            # 这里保持句子详情为空列表，因为我们不再从选中文本获取内容
            # item_data = item.data(0, Qt.UserRole)
            # item_data["sentence_details"].append({
            #     "text": selected_text,
            #     "code_id": code_id
            # })
            # item.setData(0, Qt.UserRole, item_data)

            self.first_content_edit.clear()

            # 更新结构化编码数据
            self.update_structured_codes_from_tree()

            logger.info(f"添加一阶编码(未分类): {code_id} - {clean_content}")
            self.statusBar().showMessage(f"已添加一阶编码: {code_id} - {clean_content}") if hasattr(self,
                                                                                             'statusBar') else None

        except Exception as e:
            logger.error(f"添加一阶编码失败: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"添加一阶编码失败:\n{str(e)}")

    def edit_first_level_direct(self):
        """修改一阶编码"""
        current_item = self.first_codes_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先在列表中选择一阶编码")
            return

        item_data = current_item.data(Qt.UserRole)
        if not item_data:
            return

        # 获取当前编码信息
        old_content = item_data.get("content", "")
        item_type = item_data.get("type")
        third_name = item_data.get("third", "")
        parent_name = item_data.get("second", "")

        # 创建编辑对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("修改一阶编码")
        dialog.resize(600, 400)

        layout = QVBoxLayout(dialog)

        # 显示路径信息
        if item_type == "unclassified":
            path_label = QLabel("编码状态: 未分类")
            path_label.setStyleSheet("color: #ff6600; font-weight: bold;")
        else:
            path_label = QLabel(f"编码路径: {third_name} → {parent_name}")
            path_label.setStyleSheet("color: #0066cc; font-weight: bold;")
        layout.addWidget(path_label)

        label = QLabel("请输入新的一阶编码内容:")
        layout.addWidget(label)

        text_edit = QTextEdit()
        text_edit.setPlainText(old_content)
        text_edit.setMinimumHeight(250)
        text_edit.setMaximumHeight(350)
        layout.addWidget(text_edit)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        def on_ok():
            new_content = text_edit.toPlainText().strip()
            if not new_content:
                QMessageBox.warning(dialog, "警告", "一阶编码内容不能为空")
                return

            # 验证内容
            is_valid, clean_content, error_msg = self.validate_category_name(new_content, "first")
            if not is_valid:
                QMessageBox.warning(dialog, "验证错误", error_msg)
                return

            if clean_content != old_content:
                if item_type == "unclassified":
                    # 更新未分类列表
                    if old_content in self.unclassified_first_codes:
                        index = self.unclassified_first_codes.index(old_content)
                        self.unclassified_first_codes[index] = clean_content
                        self.update_first_codes_display()
                        logger.info(f"修改未分类一阶编码: {old_content} → {clean_content}")
                else:
                    # 检查新内容是否已存在
                    if (third_name in self.current_codes and
                            parent_name in self.current_codes[third_name] and
                            clean_content in self.current_codes[third_name][parent_name]):
                        QMessageBox.warning(dialog, "警告", "该编码内容已存在")
                        return

                    # 更新编码
                    if (third_name in self.current_codes and
                            parent_name in self.current_codes[third_name] and
                            old_content in self.current_codes[third_name][parent_name]):
                        index = self.current_codes[third_name][parent_name].index(old_content)
                        self.current_codes[third_name][parent_name][index] = clean_content
                        self.update_first_codes_display()
                        logger.info(f"修改一阶编码: {old_content} → {clean_content}")

            dialog.accept()

        def on_cancel():
            dialog.reject()

        ok_button.clicked.connect(on_ok)
        cancel_button.clicked.connect(on_cancel)

        dialog.exec_()

    def delete_first_level_direct(self):
        """删除一阶编码"""
        current_item = self.first_codes_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先在列表中选择一阶编码")
            return

        item_data = current_item.data(Qt.UserRole)
        if not item_data:
            return

        # 获取编码信息
        content = item_data.get("content", "")
        item_type = item_data.get("type")
        third_name = item_data.get("third", "")
        parent_name = item_data.get("second", "")

        # 确认删除
        if item_type == "unclassified":
            msg = f"确定要删除以下未分类一阶编码吗？\n\n内容: {content}"
        else:
            msg = f"确定要删除以下一阶编码吗？\n\n路径: {third_name} → {parent_name}\n\n内容: {content}"

        reply = QMessageBox.question(self, "确认删除", msg, QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            if item_type == "unclassified":
                # 删除未分类编码
                if content in self.unclassified_first_codes:
                    self.unclassified_first_codes.remove(content)
                    self.update_first_codes_display()
                    logger.info(f"删除未分类一阶编码: {content}")
                    QMessageBox.information(self, "成功", "一阶编码已删除")
            else:
                # 删除已分类编码
                if (third_name in self.current_codes and
                        parent_name in self.current_codes[third_name] and
                        content in self.current_codes[third_name][parent_name]):
                    self.current_codes[third_name][parent_name].remove(content)
                    self.update_first_codes_display()
                    logger.info(f"删除一阶编码: {content} (在 {third_name}/{parent_name} 下)")
                    QMessageBox.information(self, "成功", "一阶编码已删除")

    def assign_first_code_category(self):
        """为未分类的一阶编码分配归属"""
        current_item = self.first_codes_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先在列表中选择要分配的一阶编码")
            return

        item_data = current_item.data(Qt.UserRole)
        if not item_data:
            return

        if item_data.get("type") != "unclassified":
            QMessageBox.information(self, "提示", "该编码已分配归属")
            return

        content = item_data.get("content", "")

        # 弹出对话框让用户选择归属
        dialog = QDialog(self)
        dialog.setWindowTitle(f"分配编码归属 - {content[:20]}...")
        dialog.resize(600, 600)  # 增大对话框尺寸以容纳更大的文本框

        layout = QVBoxLayout(dialog)

        # 说明
        info_label = QLabel(f"为一阶编码分配三阶和二阶归属：")
        info_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        layout.addWidget(info_label)

        # 显示编码内容
        content_label = QLabel(f"编码内容: {content}")
        content_label.setStyleSheet(
            "color: #666; font-style: italic; padding: 10px; background-color: #f0f0f0; border-radius: 3px;")
        layout.addWidget(content_label)

        # 三阶编码选择/输入
        third_layout = QHBoxLayout()
        third_label = QLabel("三阶编码:")
        third_combo = QComboBox()
        third_combo.setEditable(True)
        for third_cat in self.current_codes.keys():
            third_combo.addItem(third_cat)
        third_layout.addWidget(third_label)
        third_layout.addWidget(third_combo)
        layout.addLayout(third_layout)

        # 二阶编码选择/输入
        second_layout = QHBoxLayout()
        second_label = QLabel("二阶编码:")
        second_combo = QComboBox()
        second_combo.setEditable(True)

        def update_second_options():
            second_combo.clear()
            selected_third = third_combo.currentText().strip()
            if selected_third and selected_third in self.current_codes:
                for second_cat in self.current_codes[selected_third].keys():
                    second_combo.addItem(second_cat)

        third_combo.currentTextChanged.connect(update_second_options)
        update_second_options()

        second_layout.addWidget(second_label)
        second_layout.addWidget(second_combo)
        layout.addLayout(second_layout)

        # 添加一个文本框用于输入备注
        note_layout = QVBoxLayout()
        note_label = QLabel("备注信息 (可选):")
        note_text = QTextEdit()
        note_text.setMinimumHeight(120)  # 增加最小高度
        note_text.setMaximumHeight(200)
        note_layout.addWidget(note_label)
        note_layout.addWidget(note_text)
        layout.addLayout(note_layout)

        # 按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        def on_ok():
            third_category = third_combo.currentText().strip()
            second_category = second_combo.currentText().strip()

            if not third_category:
                QMessageBox.warning(dialog, "警告", "请输入三阶编码")
                return

            if not second_category:
                QMessageBox.warning(dialog, "警告", "请输入二阶编码")
                return

            # 验证三阶编码
            is_valid_third, clean_third, error_msg = self.validate_category_name(third_category, "third")
            if not is_valid_third:
                QMessageBox.warning(dialog, "验证错误", f"三阶编码: {error_msg}")
                return

            # 验证二阶编码
            is_valid_second, clean_second, error_msg = self.validate_category_name(second_category, "second")
            if not is_valid_second:
                QMessageBox.warning(dialog, "验证错误", f"二阶编码: {error_msg}")
                return

            # 确保路径存在
            if clean_third not in self.current_codes:
                self.current_codes[clean_third] = {}
                logger.info(f"自动创建三阶编码: {clean_third}")

            if clean_second not in self.current_codes[clean_third]:
                self.current_codes[clean_third][clean_second] = []
                logger.info(f"自动创建二阶编码: {clean_second} (在 {clean_third} 下)")

            # 从未分类列表移除
            if content in self.unclassified_first_codes:
                self.unclassified_first_codes.remove(content)

            # 添加到指定位置
            if content not in self.current_codes[clean_third][clean_second]:
                self.current_codes[clean_third][clean_second].append(content)
                self.update_category_combos()
                self.update_coding_tree()
                logger.info(f"分配一阶编码归属: {content} → {clean_third}/{clean_second}")
                dialog.accept()
                QMessageBox.information(self, "成功", f"已分配编码归属\n\n路径: {clean_third} → {clean_second} → {content}")
            else:
                QMessageBox.warning(dialog, "警告", "该编码已存在于目标位置")

        def on_cancel():
            dialog.reject()

        ok_button.clicked.connect(on_ok)
        cancel_button.clicked.connect(on_cancel)

        dialog.exec_()

    def handle_drop_on_tree(self, event):
        """处理拖放到树形控件的事件"""
        try:
            # 获取拖放的数据
            mime_data = event.mimeData()
            if not mime_data.hasText():
                event.ignore()
                return

            dropped_text = mime_data.text()

            # 获取拖放位置的项
            item = self.coding_tree.itemAt(event.pos())
            if not item:
                event.ignore()
                return

            # 获取目标项的数据
            item_data = item.data(0, Qt.UserRole)
            if not item_data:
                event.ignore()
                return

            # 检查目标项是否为一阶编码（即可以添加到的项）
            level = item_data.get("level")

            if level == 1:
                # 如果拖到一阶编码上，不再创建新的同级一阶编码，
                # 而是将目标一阶编码与拖拽句子的编号进行关联
                
                # 处理可能的多句拖拽：按换行符分割文本
                sentences = [s.strip() for s in dropped_text.split('\n') if s.strip()]
                if not sentences:
                    sentences = [dropped_text.strip()]  # 如果没有换行符，当作单句处理
                
                # 为每句话提取对应的TextNumberingManager编号
                associated_code_ids = []
                
                # 从父窗口获取data_processor和numbering_manager
                if self.parent_window and hasattr(self.parent_window, 'data_processor'):
                    numbering_manager = self.parent_window.data_processor.numbering_manager
                    if numbering_manager:
                        # 为每个句子提取编号
                        for sentence in sentences:
                            import re
                            number_match = re.search(r'\[(\d+)\]$', sentence.strip())
                            if number_match:
                                sentence_number = number_match.group(1)
                                associated_code_ids.append(sentence_number)
                            else:
                                # 如果没有找到编号，使用当前编号计数器的值
                                associated_code_ids.append(str(numbering_manager.get_current_number()))
                    else:
                        # 如果没有numbering_manager，使用默认编号
                        for sentence in sentences:
                            default_id = f"SN{self.generate_first_code_id()[1:] if self.generate_first_code_id().startswith('A') else '01'}"
                            associated_code_ids.append(default_id)
                else:
                    # 如果没有父窗口的data_processor，使用默认编号
                    for sentence in sentences:
                        associated_code_ids.append("SN01")

                # 获取目标项的当前数据
                target_item_data = item.data(0, Qt.UserRole)
                if target_item_data is None:
                    target_item_data = {}

                # 更新目标项的句子详情，添加拖拽的文本和编号
                target_sentence_details = target_item_data.get("sentence_details", [])
                # 为每个句子添加详情
                for i, sentence in enumerate(sentences):
                    code_id = associated_code_ids[i] if i < len(associated_code_ids) else "SN01"
                    target_sentence_details.append({
                        "text": sentence,
                        "code_id": code_id  # 使用TextNumberingManager生成的编号
                    })
                target_item_data["sentence_details"] = target_sentence_details

                # 更新目标项的句子来源数（第4列）
                current_sentence_count = int(item.text(4)) if item.text(4).isdigit() else 0
                item.setText(4, str(current_sentence_count + len(sentences)))
                # 同时更新数据结构中的句子数
                target_item_data["sentence_count"] = current_sentence_count + len(sentences)

                # 更新目标项的关联编号（第5列）
                # 包含一阶编码自身的来自TextNumberingManager的编号和拖拽文本的自动编号
                current_code_ids = item.text(5)
                
                # 获取一阶编码自身的来自TextNumberingManager的编号
                # 这应该从一阶编码的code_id中获取，如果它是来自TextNumberingManager的编号
                self_tmng_id = None
                item_code_id = item_data.get("code_id", "")
                if item_code_id.isdigit():  # 如果code_id是纯数字，表示它来自TextNumberingManager
                    self_tmng_id = item_code_id
                else:
                    # 如果不是纯数字，尝试从文本中提取可能的TextNumberingManager编号
                    item_text = item.text(0)
                    # 尝试从文本中查找[数字]格式的编号，这可能表示TextNumberingManager编号
                    import re
                    matches = re.findall(r'\[(\d+)\]', item_text)
                    if matches:
                        self_tmng_id = matches[-1]  # 使用最后一个匹配的编号
                
                # 解析当前关联编号，保留所有编号
                all_ids = []
                if current_code_ids:
                    ids = [id.strip() for id in current_code_ids.split(',')]
                    for id in ids:
                        if id and id not in all_ids:
                            all_ids.append(id)
                
                # 添加一阶编码自身的来自TextNumberingManager的编号
                if self_tmng_id and self_tmng_id not in all_ids:
                    all_ids.append(self_tmng_id)
                
                # 添加所有拖拽句子的自动编号（来自TextNumberingManager的纯数字编号）
                for code_id in associated_code_ids:
                    if code_id.isdigit() and code_id not in all_ids:
                        all_ids.append(code_id)
                
                updated_code_ids = ", ".join(all_ids) if all_ids else associated_code_id
                item.setText(5, updated_code_ids)

                # 更新目标项的数据
                item.setData(0, Qt.UserRole, target_item_data)

                self.update_structured_codes_from_tree()

                logger.info(f"通过拖放将{len(sentences)}个句子关联到一阶编码: {item.text(0)}，关联编号: {', '.join(associated_code_ids)}")
                self.statusBar().showMessage(f"通过拖放将{len(sentences)}个句子关联到一阶编码，关联编号: {', '.join(associated_code_ids)}") if hasattr(self,
                                                                                                    'statusBar') else None

                # 明确设置为复制操作并接受，确保不删除源文本
                event.setDropAction(Qt.CopyAction)
                event.accept()
            else:
                # 如果拖到二阶或三阶编码上，创建新的子项
                if level == 2:
                    # 拖到二阶编码上，添加为一阶子项
                    second_name = item.text(0)
                    grandparent = item.parent()
                    third_name = grandparent.text(0) if grandparent else ""

                    is_valid, clean_content, error_msg = self.validate_category_name(dropped_text, "first")
                    if not is_valid:
                        QMessageBox.warning(self, "验证错误", error_msg)
                        event.ignore()
                        return

                    # 检查是否已存在
                    if self.is_content_exists(clean_content):
                        QMessageBox.warning(self, "警告", "该一阶编码已存在")
                        event.ignore()
                        return

                    # 添加为二阶的子项
                    # 生成新的编号
                    new_code_id = self.generate_first_code_id()

                    new_item = QTreeWidgetItem(item)
                    # 在内容前加上编号
                    new_item.setText(0, f"{new_code_id}: {clean_content}")
                    new_item.setText(1, "一阶编码")
                    new_item.setText(2, "1")
                    new_item.setText(3, "1")  # 文件来源数
                    new_item.setText(4, "1")  # 句子来源数
                    # 从dropped_text中尝试提取TextNumberingManager的编号
                    import re
                    number_matches = re.findall(r'\[(\d+)\]', dropped_text)
                    if number_matches:
                        # 使用最后一个匹配的数字编号作为来自TextNumberingManager的编号
                        tmng_number = number_matches[-1]
                        new_item.setText(5, tmng_number)  # 关联编号设置为来自TextNumberingManager的编号
                    else:
                        # 如果没有找到TextNumberingManager编号，则使用new_code_id
                        new_item.setText(5, new_code_id)  # 关联编号

                    new_item.setData(0, Qt.UserRole, {
                        "level": 1,
                        "content": clean_content,
                        "numbered_content": f"{new_code_id}: {clean_content}",
                        "category": second_name,
                        "core_category": third_name,
                        "classified": True,
                        "code_id": new_code_id,
                        "sentence_details": [{"text": dropped_text, "code_id": new_code_id}]  # 添加拖拽的句子详情
                    })

                    # 不再向文本中添加编码标记，保持原始文本不变
                    # self.add_code_marker_to_text(dropped_text, new_code_id)

                    # 更新父节点计数
                    item.setText(2, str(item.childCount()))

                    # 更新祖父节点计数
                    if grandparent:
                        grandparent.setText(2, str(grandparent.childCount()))

                    self.update_structured_codes_from_tree()

                    logger.info(f"通过拖放添加一阶编码到二阶'{second_name}': {clean_content}")
                    self.statusBar().showMessage(f"通过拖放添加一阶编码到二阶'{second_name}': {clean_content}") if hasattr(self,
                                                                                                              'statusBar') else None

                    event.acceptProposedAction()
                elif level == 3:
                    # 拖到三阶编码上，添加为二阶子项
                    third_name = item.text(0)
                    
                    is_valid, clean_content, error_msg = self.validate_category_name(dropped_text, "second")
                    if not is_valid:
                        QMessageBox.warning(self, "验证错误", error_msg)
                        event.ignore()
                        return
                    
                    # 生成二阶编码ID
                    new_code_id = self.generate_second_code_id()
                    numbered_content = f"{new_code_id} {clean_content}"
                    
                    # 检查是否已存在
                    if self.is_second_content_exists(clean_content, item):
                        QMessageBox.warning(self, "警告", "该二阶编码在此三阶编码下已存在")
                        event.ignore()
                        return
                    
                    # 添加为三阶的子项（二阶编码）
                    new_item = QTreeWidgetItem(item)
                    new_item.setText(0, numbered_content)
                    new_item.setText(1, "二阶编码")
                    new_item.setText(2, "0")  # 初始子项数
                    new_item.setText(3, "")  # 二阶编码不显示文件来源数
                    new_item.setText(4, "0")  # 句子来源数
                    new_item.setText(5, new_code_id)  # 关联编号

                    new_item.setData(0, Qt.UserRole, {
                        "level": 2,
                        "name": clean_content,
                        "code_id": new_code_id,
                        "parent": third_name,
                        "sentence_details": []
                    })
                    
                    # 更新父节点计数
                    item.setText(2, str(item.childCount()))
                    
                    self.update_structured_codes_from_tree()
                    
                    logger.info(f"通过拖放添加二阶编码到三阶'{third_name}': {clean_content}")
                    self.statusBar().showMessage(f"通过拖放添加二阶编码到三阶'{third_name}': {clean_content}") if hasattr(self,
                                                                                                          'statusBar') else None
                    
                    event.acceptProposedAction()
                else:
                    # 其他情况，忽略
                    event.ignore()
        except Exception as e:
            logger.error(f"处理拖放事件失败: {e}")
            import traceback
            traceback.print_exc()
            event.ignore()

    def add_code_marker_to_text(self, text_to_mark, code_id):
        """在文本中添加编码标记"""
        try:
            current_text = self.text_display.toPlainText()

            # 查找文本在当前文档中的位置
            start_pos = current_text.find(text_to_mark)
            if start_pos != -1:
                # 创建一个文本光标
                cursor = self.text_display.textCursor()

                # 选择找到的文本
                cursor.setPosition(start_pos)
                cursor.movePosition(cursor.Right, cursor.KeepAnchor, len(text_to_mark))

                # 获取选中的文本以确认匹配
                if cursor.selectedText() == text_to_mark:
                    # 在选中文本后添加编码标记
                    cursor.insertText(f"{text_to_mark} [{code_id}]")

                    logger.info(f"已为文本添加编码标记: [{code_id}]")

        except Exception as e:
            logger.error(f"添加编码标记失败: {e}")
            import traceback
            traceback.print_exc()

    def get_coding_result(self):
        """获取编码结果"""
        return self.current_codes