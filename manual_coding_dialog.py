import os
import json
import re
from datetime import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QGroupBox, QTextEdit, QLineEdit, QPushButton, QWidget,
                             QListWidget, QListWidgetItem, QLabel, QMessageBox,
                             QTreeWidget, QTreeWidgetItem, QSplitter, QComboBox,
                             QInputDialog, QDialogButtonBox, QApplication, QMenu, QAction)
from PyQt5.QtCore import Qt, QMimeData, QTimer, QEvent
from PyQt5.QtGui import QTextDocument, QTextCursor
from PyQt5.QtGui import QFont, QColor, QDrag
import logging

logger = logging.getLogger(__name__)


class DragDropTreeWidget(QTreeWidget):
    """支持拖放功能的树形控件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dialog = None  # 将由ManualCodingDialog设置
        # 启用内部拖放功能
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeWidget.InternalMove)

    def dragEnterEvent(self, event):
        """处理拖拽进入事件"""
        # 接受文本拖放（从文本区域拖拽）
        if event.mimeData().hasText():
            event.setDropAction(Qt.CopyAction)
            event.accept()
        # 接受内部拖放（编码节点之间的拖拽）
        elif event.source() == self:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """处理拖拽移动事件"""
        # 处理文本拖放
        if event.mimeData().hasText():
            event.setDropAction(Qt.CopyAction)
            event.accept()
        # 处理内部拖放
        elif event.source() == self:
            # 检查拖拽的项目是否可以放到目标位置
            item = self.itemAt(event.pos())
            if item:
                # 不允许将节点拖放到其子节点中，防止循环
                dragged_items = self.selectedItems()
                for dragged_item in dragged_items:
                    if self._is_ancestor(item, dragged_item):
                        event.ignore()
                        return
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """处理拖放释放事件"""
        # 处理文本拖放
        if event.mimeData().hasText():
            if self.dialog:
                event.setDropAction(Qt.CopyAction)
                self.dialog.handle_drop_on_tree(event)
                event.accept()
            else:
                event.ignore()
        # 处理内部拖放
        elif event.source() == self:
            # 调用父类的dropEvent处理内部移动
            super().dropEvent(event)
            # 拖放完成后更新编码结构
            if self.dialog:
                self.dialog.update_structured_codes_from_tree()
        else:
            event.ignore()

    def _is_ancestor(self, item, potential_ancestor):
        """检查item是否是potential_ancestor的祖先节点"""
        while potential_ancestor:
            if potential_ancestor == item:
                return True
            potential_ancestor = potential_ancestor.parent()
        return False


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

        import_coding_btn = QPushButton("导入编码结果")
        import_coding_btn.clicked.connect(self.import_coding_results)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.reject)

        button_layout.addWidget(save_btn)
        button_layout.addWidget(import_coding_btn)
        button_layout.addWidget(save_tree_btn)
        button_layout.addWidget(import_tree_btn)
        button_layout.addWidget(export_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        # 保存文本文档引用
        self.text_document = self.text_display.document()

        # 不再自动弹出恢复编码进度对话框，用户可以通过导入功能手动恢复
        # self.check_and_restore_last_coding_position()

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
        # 安装事件过滤器以处理点击事件
        self.text_display.installEventFilter(self)
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

        # 添加自动编码编辑功能
        auto_coding_layout = QHBoxLayout()
        auto_coding_label = QLabel("编辑自动编码:")
        auto_coding_btn = QPushButton("编辑自动编码")
        auto_coding_btn.clicked.connect(self.edit_auto_generated_codes)
        auto_coding_btn.setToolTip("快速编辑自动生成的编码，保持层级结构不变")
        auto_coding_layout.addWidget(auto_coding_label)
        auto_coding_layout.addWidget(auto_coding_btn)
        hierarchy_layout.addLayout(auto_coding_layout)

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
            # 增强对自动生成编码结构的解析
            self.current_codes = self.existing_codes.copy()

            # 为自动生成的编码添加标识，便于用户识别
            self._mark_auto_generated_codes()

            self.update_category_combos()
            # 只有当树形控件已经创建后才更新
            if hasattr(self, 'coding_tree'):
                self.update_coding_tree()

    def _mark_auto_generated_codes(self):
        """为自动生成的编码添加标识，便于用户识别"""
        try:
            # 遍历所有编码，为自动生成的编码添加标识
            for third_cat, second_cats in self.current_codes.items():
                for second_cat, first_contents in second_cats.items():
                    for i, content_data in enumerate(first_contents):
                        if isinstance(content_data, dict):
                            # 为自动生成的编码添加标识
                            if 'auto_generated' not in content_data:
                                content_data['auto_generated'] = True
                            if 'source' not in content_data:
                                content_data['source'] = 'auto'
        except Exception as e:
            logger.error(f"标记自动生成编码失败: {e}")

    def update_category_combos(self):
        """更新类别组合框（兼容方法）"""
        # 这个方法被调用但未定义，添加一个空实现以避免错误
        # 由于下拉框相关方法已弃用，这里不需要实际操作
        pass

    # 下拉框相关方法已弃用
    def on_file_selected(self, item):
        """文件选择事件 - 修复版本，支持编码标记持久化"""
        try:
            new_file_path = item.data(Qt.UserRole)
            logger.info(f"选择了文件: {new_file_path}")

            # 在切换文件前，先保存之前文件的编码标记状态
            self.save_previous_file_coding_marks(new_file_path)

            if new_file_path in self.loaded_files:
                file_data = self.loaded_files[new_file_path]
                logger.info(f"找到文件数据: {os.path.basename(new_file_path)}")

                # 按优先级获取显示内容
                display_content = self.get_file_display_content(file_data, new_file_path)

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
                logger.error(f"文件数据不存在: {new_file_path}")

        except Exception as e:
            logger.error(f"文件选择处理失败: {e}")
            self.text_display.setPlainText(f"加载文件失败: {str(e)}")
            self.select_sentence_btn.setEnabled(False)

    def save_previous_file_coding_marks(self, new_file_path):
        """保存之前文件的编码标记状态（在切换到新文件前）"""
        try:
            # 获取当前text_display显示的内容
            current_display_content = self.text_display.toPlainText()

            # 如果当前没有任何内容，跳过保存
            if not current_display_content.strip():
                return

            # 查找哪个文件对应当前显示的内容
            previous_file_path = None

            # 遍历所有加载的文件，找到之前显示的文件
            for file_path, file_data in self.loaded_files.items():
                if file_path == new_file_path:
                    continue  # 跳过即将切换到的文件

                # 检查当前显示内容是否来自这个文件
                if self.is_content_from_file(current_display_content, file_data):
                    previous_file_path = file_path
                    break

            if previous_file_path:
                # 检查是否包含编码标记
                import re
                has_coding_marks = bool(re.search(r'\[A\d+\]', current_display_content))

                if has_coding_marks:
                    # 保存带编码标记的内容
                    self.loaded_files[previous_file_path]['content_with_marks'] = current_display_content
                    logger.info(f"已保存文件的编码标记状态: {os.path.basename(previous_file_path)}")
                else:
                    # 如果没有编码标记，清除之前保存的标记内容
                    if 'content_with_marks' in self.loaded_files[previous_file_path]:
                        del self.loaded_files[previous_file_path]['content_with_marks']

        except Exception as e:
            logger.error(f"保存之前文件编码标记失败: {e}")

    def is_content_from_file(self, display_content, file_data):
        """判断显示的内容是否来自指定文件"""
        try:
            # 获取文件的原始内容或编号内容
            file_contents = [
                file_data.get('content_with_marks', ''),
                file_data.get('numbered_content', ''),
                file_data.get('content', ''),
                file_data.get('original_content', ''),
                file_data.get('original_text', '')
            ]

            # 移除编码标记后比较内容
            import re
            display_content_clean = re.sub(r'\s*\[A\d+\]', '', display_content)
            # 同时也移除句子编号，避免影响比较
            display_content_clean = re.sub(r'\s*\[\d+\]', '', display_content_clean)

            for file_content in file_contents:
                if not file_content:
                    continue

                file_content_clean = re.sub(r'\s*\[A\d+\]', '', file_content)
                # 同时也移除句子编号
                file_content_clean = re.sub(r'\s*\[\d+\]', '', file_content_clean)

                # 比较清理后的内容
                if display_content_clean.strip() == file_content_clean.strip():
                    return True

                # 也检查原始内容的相似度（去除空白字符）
                display_normalized = ''.join(display_content_clean.split())
                file_normalized = ''.join(file_content_clean.split())
                if display_normalized == file_normalized:
                    return True

            return False

        except Exception as e:
            logger.error(f"判断内容归属失败: {e}")
            return False

    def get_file_display_content(self, file_data, file_path):
        """按优先级获取文件的显示内容"""
        try:
            # 1. 优先使用带编码标记的内容
            content_with_marks = file_data.get('content_with_marks', '')
            if content_with_marks:
                logger.info(f"使用带编码标记的内容: {os.path.basename(file_path)}")
                return content_with_marks

            # 2. 使用已有的编号内容
            numbered_content = file_data.get('numbered_content', '')
            if numbered_content:
                logger.info(f"使用已有的编号内容: {os.path.basename(file_path)}")
                return numbered_content

            # 3. 获取原始内容并进行编号
            content = file_data.get('content', '') or file_data.get('original_content', '') or file_data.get(
                'original_text', '')
            if content:
                try:
                    from data_processor import DataProcessor
                    processor = DataProcessor()
                    filename = os.path.basename(file_path)
                    display_content, number_mapping = processor.numbering_manager.number_text(content, filename)
                    logger.info(f"对原始内容进行编号: {os.path.basename(file_path)}")
                    return display_content
                except Exception as e:
                    logger.error(f"内容编号失败: {e}")
                    return content  # 返回原始内容

            # 4. 内容为空的情况
            logger.warning(f"文件内容为空: {os.path.basename(file_path)}")
            return "文件内容为空"

        except Exception as e:
            logger.error(f"获取文件显示内容失败: {e}")
            return f"加载文件失败: {str(e)}"

    def save_current_file_coding_marks(self):
        """保存当前文件的编码标记状态（兼容性方法）"""
        try:
            # 获取当前text_display的内容（包含编码标记）
            current_content = self.text_display.toPlainText()

            # 如果没有内容，跳过
            if not current_content.strip():
                return

            # 查找哪个文件对应当前显示的内容
            current_file_path = None

            # 先尝试获取当前选中的文件
            current_item = self.file_list.currentItem()
            if current_item:
                potential_file_path = current_item.data(Qt.UserRole)
                if potential_file_path in self.loaded_files:
                    file_data = self.loaded_files[potential_file_path]
                    if self.is_content_from_file(current_content, file_data):
                        current_file_path = potential_file_path

            # 如果选中的文件不匹配当前内容，遍历所有文件查找
            if not current_file_path:
                for file_path, file_data in self.loaded_files.items():
                    if self.is_content_from_file(current_content, file_data):
                        current_file_path = file_path
                        break

            if current_file_path:
                # 检查是否包含编码标记（如[A01]、[A02]等）
                import re
                has_coding_marks = bool(re.search(r'\[A\d+\]', current_content))

                if has_coding_marks:
                    # 保存带编码标记的内容
                    self.loaded_files[current_file_path]['content_with_marks'] = current_content
                    logger.info(f"已保存文件的编码标记状态: {os.path.basename(current_file_path)}")
                else:
                    # 如果没有编码标记，清除之前保存的标记内容
                    if 'content_with_marks' in self.loaded_files[current_file_path]:
                        del self.loaded_files[current_file_path]['content_with_marks']
            else:
                logger.warning("无法确定当前显示内容对应的文件")

        except Exception as e:
            logger.error(f"保存当前文件编码标记失败: {e}")

    def get_current_file_path(self):
        """获取当前选中的文件路径"""
        try:
            current_item = self.file_list.currentItem()
            if current_item:
                return current_item.data(Qt.UserRole)
            return None
        except Exception as e:
            logger.error(f"获取当前文件路径失败: {e}")
            return None

    def eventFilter(self, source, event):
        """事件过滤器：处理点击文本自动选中句子"""
        if source == self.text_display and event.type() == QEvent.MouseButtonRelease:
            # 如果是鼠标左键释放，且没有选区（或者是点击操作）
            if event.button() == Qt.LeftButton:
                cursor = self.text_display.textCursor()
                if not cursor.hasSelection():
                    # 执行自动选中句子
                    mouse_pos = event.pos()
                    # 移动光标到点击位置
                    cursor_at_pos = self.text_display.cursorForPosition(mouse_pos)
                    self.text_display.setTextCursor(cursor_at_pos)

                    self.auto_select_sentence_at_cursor()
                    return True  # 消耗事件
        return super().eventFilter(source, event)

    def auto_select_sentence_at_cursor(self):
        """自动选中光标所在的句子（包括编号）"""
        try:
            cursor = self.text_display.textCursor()
            document = self.text_display.document()
            text_content = document.toPlainText()
            position = cursor.position()

            # 向前查找句子开始
            start_pos = position
            while start_pos > 0:
                char = text_content[start_pos - 1]
                if char in ['。', '！', '？', '\n', '\u2029']:
                    break
                start_pos -= 1

            # 向后查找句子结束
            end_pos = position
            total_len = len(text_content)
            while end_pos < total_len:
                char = text_content[end_pos]
                if char in ['。', '！', '？', '\n', '\u2029']:
                    end_pos += 1  # 包含标点
                    break
                end_pos += 1

            # 检查句子后面是否有编号 [数字]
            # 向后扫描，这可能跨越空格，但不应跨越换行
            temp_pos = end_pos
            potential_number_end = temp_pos

            # 首先跳过水平空格
            while temp_pos < total_len and text_content[temp_pos].isspace():
                if text_content[temp_pos] in ['\n', '\u2029']:
                    break  # 遇到换行，停止寻找编号
                temp_pos += 1

            # 检查是否有 [
            if temp_pos < total_len and text_content[temp_pos] == '[':
                bracket_start = temp_pos
                # 寻找对应的 ]
                while temp_pos < total_len:
                    if text_content[temp_pos] == ']':
                        potential_number_end = temp_pos + 1
                        # 检查中间是否是数字
                        inner_content = text_content[bracket_start + 1:temp_pos]
                        if inner_content.isdigit():
                            end_pos = potential_number_end
                        break
                    if text_content[temp_pos] in ['\n', '\u2029']:  # 换行符终止查找
                        break
                    temp_pos += 1

            # 设置选区
            # 跳过开始的空白字符
            while start_pos < end_pos and text_content[start_pos].isspace():
                start_pos += 1

            if start_pos < end_pos:
                cursor.setPosition(start_pos)
                cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
                self.text_display.setTextCursor(cursor)

                # 启用选择句子按钮
                self.select_sentence_btn.setEnabled(True)

        except Exception as e:
            logger.error(f"自动选中句子失败: {e}")

    def edit_auto_generated_codes(self):
        """快速编辑自动生成的编码，保持层级结构不变"""
        try:
            # 检查是否有自动生成的编码
            has_auto_codes = False
            for third_cat, second_cats in self.current_codes.items():
                for second_cat, first_contents in second_cats.items():
                    for content_data in first_contents:
                        if isinstance(content_data, dict) and content_data.get('auto_generated', False):
                            has_auto_codes = True
                            break
                    if has_auto_codes:
                        break
                if has_auto_codes:
                    break

            if not has_auto_codes:
                QMessageBox.information(self, "提示", "没有找到自动生成的编码")
                return

            # 提示用户如何编辑自动编码
            QMessageBox.information(self, "编辑自动编码",
                                    "请在右侧编码树中直接双击要编辑的编码进行修改。\n\n注意：\n1. 双击编码节点可以直接编辑内容\n2. 拖拽编码可以调整层级结构\n3. 右键菜单可以进行更多操作\n4. 编辑完成后点击'保存编码'按钮保存结果")

            # 自动展开编码树，方便用户编辑
            self.coding_tree.expandAll()

        except Exception as e:
            logger.error(f"编辑自动编码失败: {e}")
            QMessageBox.critical(self, "错误", f"编辑自动编码失败: {str(e)}")

    def closeEvent(self, event):
        """对话框关闭事件，保存编码标记状态"""
        try:
            # 保存当前文件的编码标记状态
            self.save_current_file_coding_marks()
            logger.info("对话框关闭时已保存编码标记状态")
        except Exception as e:
            logger.error(f"关闭时保存编码标记失败: {e}")

        # 调用父类的关闭事件
        super().closeEvent(event)

    def select_sentence_for_coding(self):
        """选择句子作为一阶编码 - 仅将文本复制到输入框"""
        try:
            cursor = self.text_display.textCursor()
            if cursor.hasSelection():
                selected_text = cursor.selectedText().strip()
                logger.info(f"选择了文本: {selected_text[:50]}...")

                if len(selected_text) > 0:  # 确保有意义的文本
                    # 仅将文本复制到编码输入框，不进行任何其他操作
                    self.first_content_edit.setPlainText(selected_text)

                    # 提示用户（可选，这里使用状态栏提示比较轻量）
                    self.statusBar().showMessage("文本已复制到输入框，请点击'添加一阶编码'按钮确认添加") if hasattr(self, 'statusBar') else None
                else:
                    QMessageBox.warning(self, "警告", "请选择有意义的文本（至少1个字符）")
            else:
                QMessageBox.information(self, "提示", "请先选择文本内容")

        except Exception as e:
            logger.error(f"选择句子失败: {e}")
            QMessageBox.critical(self, "错误", f"选择句子失败: {str(e)}")

    def add_code_marker_to_selection(self, cursor, code_id):
        """在选中的文本位置添加编码标记"""
        try:
            # 获取选中文本的位置
            selection_start = cursor.selectionStart()
            selection_end = cursor.selectionEnd()
            selected_text = cursor.selectedText()

            # 在选中文本后添加编码标记
            cursor.setPosition(selection_end)
            cursor.insertText(f" [{code_id}]")

            # 清除选择
            cursor.clearSelection()
            self.text_display.setTextCursor(cursor)

            logger.info(f"已在文本中添加编码标记: [{code_id}]")

            # 立即保存编码标记状态到当前文件
            self.save_current_file_coding_marks()

        except Exception as e:
            logger.error(f"添加编码标记失败: {e}")

    def create_first_code_item(self, content, code_id):
        """创建一阶编码项并添加到树中"""
        try:
            # 验证编码内容
            is_valid, clean_content, error_msg = self.validate_category_name(content, "first")
            if not is_valid:
                QMessageBox.warning(self, "验证错误", error_msg)
                return

            # 检查是否已存在
            if self.is_content_exists(clean_content):
                QMessageBox.warning(self, "警告", "该一阶编码已存在")
                return

            # 创建句子详情信息
            sentence_details = []
            current_file = None

            # 获取当前选中的文件信息
            if hasattr(self, 'file_list') and self.file_list.currentItem():
                current_file = self.file_list.currentItem().data(Qt.UserRole)

            # 提取内容中的句子编号
            import re
            sentence_numbers = re.findall(r'\[(\d+)\]', content)

            # 创建句子详情记录
            sentence_detail = {
                "text": clean_content,
                "code_id": code_id,
                "file_path": current_file if current_file else "未知文件",
                "sentence_id": ", ".join(sentence_numbers) if sentence_numbers else code_id
            }
            sentence_details.append(sentence_detail)

            # 添加到树根部（未分类状态）
            item = QTreeWidgetItem(self.coding_tree)
            item.setText(0, f"{code_id}: {clean_content}")
            item.setText(1, "一阶编码")
            item.setText(2, "1")
            item.setText(3, "1")  # 文件来源数
            item.setText(4, "1")  # 句子来源数
            item.setText(5, ", ".join(sentence_numbers) if sentence_numbers else code_id)  # 关联编号

            item.setData(0, Qt.UserRole, {
                "level": 1,
                "content": clean_content,
                "numbered_content": f"{code_id}: {clean_content}",  # 带编号的内容
                "code_id": code_id,
                "sentence_details": sentence_details,  # 包含实际句子详情
                "classified": False
            })

            # 展开树并选中新创建的项
            self.coding_tree.expandAll()
            self.coding_tree.setCurrentItem(item)

            logger.info(f"已创建一阶编码项: {code_id}: {clean_content}")

        except Exception as e:
            logger.error(f"创建一阶编码项失败: {e}")

    def navigate_and_highlight_sentence(self, code_id, content):
        """导航到编码对应的完整句子内容并高亮显示"""
        try:
            # 如果传入的是数字字符串，说明是点击了句子编号
            if str(code_id).isdigit() and content is None:
                return self.navigate_to_number(code_id)

            # 清除之前的高亮
            self.clear_text_highlights()

            if not content:
                logger.warning(f"编码 {code_id} 没有内容")
                return False

            # 直接搜索编码对应的完整内容
            document = self.text_display.document()

            # 先尝试直接搜索原始内容
            search_content = content.strip()
            logger.info(f"搜索内容: {search_content[:50]}...")

            # 尝试完整匹配
            content_cursor = document.find(search_content)

            if content_cursor.isNull():
                # 如果完整匹配失败，尝试清理内容后搜索
                import re
                # 移除可能的编号和引用标记
                clean_content = re.sub(r'\s*\[\d+\]\s*', ' ', search_content)  # 移除 [1] [2] 等
                clean_content = re.sub(r'^\s*[①②③④⑤⑥⑦⑧⑨⑩]\s*', '', clean_content)  # 移除开头编号
                clean_content = re.sub(r'\s+', ' ', clean_content).strip()  # 标准化空格

                if clean_content and clean_content != search_content:
                    logger.info(f"使用清理后的内容搜索: {clean_content[:50]}...")
                    content_cursor = document.find(clean_content)

            if content_cursor.isNull():
                # 如果还是找不到，尝试分句搜索
                sentences = self.split_into_sentences(search_content)
                if len(sentences) > 1:
                    return self.highlight_multiple_sentences(sentences, code_id)

            if not content_cursor.isNull():
                # 找到内容，创建高亮选择
                extra_selections = []
                selection = QTextEdit.ExtraSelection()
                selection.cursor = content_cursor
                selection.format.setBackground(QColor(173, 216, 230))  # 浅蓝色背景
                selection.format.setForeground(QColor(0, 0, 139))  # 深蓝色文字
                extra_selections.append(selection)

                self.text_display.setExtraSelections(extra_selections)

                # 滚动到该位置，但不选中（避免覆盖自定义高亮颜色）
                scroll_cursor = QTextCursor(content_cursor)
                scroll_cursor.setPosition(content_cursor.selectionStart())
                self.text_display.setTextCursor(scroll_cursor)
                self.text_display.ensureCursorVisible()

                logger.info(f"成功高亮编码 {code_id} 的内容")
                return True
            else:
                # 最后回退到基于编码标记的方法
                logger.info(f"直接内容搜索失败，回退到标记搜索")
                return self.fallback_highlight_by_marker(code_id)

        except Exception as e:
            logger.error(f"导航和高亮失败: {e}")
            return False

    def split_into_sentences(self, content):
        """将内容分割成句子"""
        import re
        # 按句号、问号、感叹号分割
        sentences = re.split(r'[。！？\n]', content)
        # 过滤空句子并去除前后空白
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    def highlight_multiple_sentences(self, sentences, code_id):
        """高亮多个句子"""
        try:
            document = self.text_display.document()
            extra_selections = []
            first_cursor = None
            found_count = 0

            for sentence in sentences:
                if len(sentence) < 3:  # 跳过太短的句子
                    continue

                # 清理句子
                import re
                clean_sentence = re.sub(r'\s*\[\d+\]\s*', ' ', sentence)
                clean_sentence = re.sub(r'^\s*[①②③④⑤⑥⑦⑧⑨⑩]\s*', '', clean_sentence)
                clean_sentence = clean_sentence.strip()

                if clean_sentence:
                    sentence_cursor = document.find(clean_sentence)
                    if not sentence_cursor.isNull():
                        selection = QTextEdit.ExtraSelection()
                        selection.cursor = sentence_cursor
                        selection.format.setBackground(QColor(173, 216, 230))
                        selection.format.setForeground(QColor(0, 0, 139))
                        extra_selections.append(selection)

                        if first_cursor is None:
                            first_cursor = sentence_cursor
                        found_count += 1

            if extra_selections:
                self.text_display.setExtraSelections(extra_selections)
                if first_cursor:
                    # 滚动到第一个位置，但不选中
                    scroll_cursor = QTextCursor(first_cursor)
                    scroll_cursor.setPosition(first_cursor.selectionStart())
                    self.text_display.setTextCursor(scroll_cursor)
                    self.text_display.ensureCursorVisible()
                logger.info(f"成功高亮 {found_count} 个句子片段")
                return True

            return False

        except Exception as e:
            logger.error(f"多句子高亮失败: {e}")
            return False

    def highlight_multiline_content(self, lines):
        """高亮多行内容"""
        try:
            document = self.text_display.document()
            extra_selections = []
            first_cursor = None

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # 清理行内容
                import re
                clean_line = re.sub(r'^\s*[①②③④⑤⑥⑦⑧⑨⑩]\s*', '', line)
                clean_line = re.sub(r'\s*\[\d+\]\s*', '', clean_line)
                clean_line = clean_line.strip()

                if clean_line:
                    line_cursor = document.find(clean_line)
                    if not line_cursor.isNull():
                        selection = QTextEdit.ExtraSelection()
                        selection.cursor = line_cursor
                        selection.format.setBackground(QColor(173, 216, 230))
                        selection.format.setForeground(QColor(0, 0, 139))
                        extra_selections.append(selection)

                        if first_cursor is None:
                            first_cursor = line_cursor

            if extra_selections:
                self.text_display.setExtraSelections(extra_selections)
                if first_cursor:
                    # 滚动到第一个位置，但不选中
                    scroll_cursor = QTextCursor(first_cursor)
                    scroll_cursor.setPosition(first_cursor.selectionStart())
                    self.text_display.setTextCursor(scroll_cursor)
                    self.text_display.ensureCursorVisible()
                return True

            return False

        except Exception as e:
            logger.error(f"多行高亮失败: {e}")
            return False

    def fallback_highlight_by_marker(self, code_id):
        """回退方法：基于编码标记进行高亮"""
        try:
            document = self.text_display.document()
            pattern = f"[{code_id}]"
            mark_cursor = document.find(pattern)

            if not mark_cursor.isNull():
                # 找到编码标记，向前查找句子内容
                mark_start = mark_cursor.selectionStart()
                sentence_start = self.find_sentence_start(mark_start)

                # 创建高亮选择：从句子开始到编码标记前
                highlight_cursor = QTextCursor(document)
                highlight_cursor.setPosition(sentence_start)
                highlight_cursor.setPosition(mark_start, QTextCursor.KeepAnchor)

                # 设置高亮格式
                extra_selections = []
                selection = QTextEdit.ExtraSelection()
                selection.cursor = highlight_cursor
                selection.format.setBackground(QColor(173, 216, 230))
                selection.format.setForeground(QColor(0, 0, 139))
                extra_selections.append(selection)

                self.text_display.setExtraSelections(extra_selections)

                # 滚动到该位置，但不选中
                view_cursor = QTextCursor(document)
                view_cursor.setPosition(sentence_start)
                self.text_display.setTextCursor(view_cursor)
                self.text_display.ensureCursorVisible()

                return True

            return False

        except Exception as e:
            logger.error(f"回退高亮方法失败: {e}")
            return False

    def find_sentence_start(self, mark_position):
        """从编码标记位置向前查找句子开始位置"""
        try:
            document = self.text_display.document()
            sentence_start = mark_position
            temp_cursor = QTextCursor(document)

            # 向前扫描查找句子开始
            while sentence_start > 0:
                temp_cursor.setPosition(sentence_start - 1)
                temp_cursor.setPosition(sentence_start, QTextCursor.KeepAnchor)
                char = temp_cursor.selectedText()

                # 遇到句子结束符或段落分隔符时停止
                if char in ['。', '！', '？', '\n', '\u2029']:
                    break

                # 遇到另一个编码标记的结束符时停止（避免跨编码）
                if char == ']':
                    # 继续向前找到对应的开始符 [
                    bracket_pos = sentence_start - 1
                    while bracket_pos > 0:
                        temp_cursor.setPosition(bracket_pos - 1)
                        temp_cursor.setPosition(bracket_pos, QTextCursor.KeepAnchor)
                        bracket_char = temp_cursor.selectedText()
                        if bracket_char == '[':
                            sentence_start = bracket_pos
                            break
                        bracket_pos -= 1
                    break

                sentence_start -= 1

            # 跳过开头的空白字符
            while sentence_start < mark_position:
                temp_cursor.setPosition(sentence_start)
                temp_cursor.setPosition(sentence_start + 1, QTextCursor.KeepAnchor)
                char = temp_cursor.selectedText()
                if char not in [' ', '\t', '\n', '\u2029', ']']:
                    break
                sentence_start += 1

            return sentence_start

        except Exception as e:
            logger.error(f"查找句子开始位置失败: {e}")
            return mark_position

    def highlight_content_before_mark(self, mark_cursor, code_id):
        """根据编码标记高亮前面的内容"""
        try:
            document = self.text_display.document()
            mark_start = mark_cursor.selectionStart()

            # 向前查找内容的开始位置
            content_start = mark_start
            temp_cursor = QTextCursor(document)

            # 向前扫描寻找内容开始（可能跨越多个句子）
            bracket_count = 0  # 计算遇到的编码标记数量
            while content_start > 0:
                temp_cursor.setPosition(content_start - 1)
                temp_cursor.setPosition(content_start, QTextCursor.KeepAnchor)
                char = temp_cursor.selectedText()

                # 检查是否遇到另一个编码标记的结束
                if char == ']':
                    bracket_count += 1
                elif char == '[' and bracket_count > 0:
                    bracket_count -= 1
                    if bracket_count == 0:
                        # 找到了前一个编码标记的开始，说明内容开始于此处之后
                        break
                elif bracket_count == 0 and char in ['。', '！', '？'] and content_start < mark_start - 50:
                    # 如果距离编码标记较远且遇到句号，可能是前一个句子的结束
                    break

                content_start -= 1

            # 跳过可能的空白字符和换行符
            while content_start < mark_start:
                temp_cursor.setPosition(content_start)
                temp_cursor.setPosition(content_start + 1, QTextCursor.KeepAnchor)
                char = temp_cursor.selectedText()
                if char not in [' ', '\t', '\n', '\u2029', ']']:
                    break
                content_start += 1

            # 找到编码标记前的位置（跳过空格）
            content_end = mark_start
            while content_end > content_start:
                temp_cursor.setPosition(content_end - 1)
                temp_cursor.setPosition(content_end, QTextCursor.KeepAnchor)
                char = temp_cursor.selectedText()
                if char not in [' ', '\t']:
                    break
                content_end -= 1

            # 创建高亮选择
            highlight_cursor = QTextCursor(document)
            highlight_cursor.setPosition(content_start)
            highlight_cursor.setPosition(content_end, QTextCursor.KeepAnchor)

            # 设置高亮格式
            extra_selections = []
            selection = QTextEdit.ExtraSelection()
            selection.cursor = highlight_cursor
            selection.format.setBackground(QColor(173, 216, 230))  # 浅蓝色背景
            selection.format.setForeground(QColor(0, 0, 139))  # 深蓝色文字
            extra_selections.append(selection)

            self.text_display.setExtraSelections(extra_selections)

            # 滚动到该位置
            view_cursor = QTextCursor(document)
            view_cursor.setPosition(content_start)
            self.text_display.setTextCursor(view_cursor)
            self.text_display.ensureCursorVisible()

        except Exception as e:
            logger.error(f"通过标记高亮内容失败: {e}")

    def validate_category_name(self, name, level):
        """验证编码名称"""
        if not name:
            return False, "", "编码名称不能为空"

        if level == "first":
            if len(name) > 300:
                return False, "", "一阶编码名称不能超过300个字符"
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
        # 如果有恢复的编码计数器，从那里继续
        if hasattr(self, 'last_code_number') and hasattr(self, 'last_code_letter'):
            next_number = self.last_code_number + 1
            new_id = f"{self.last_code_letter}{next_number:02d}"
            self.last_code_number = next_number
            return new_id

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

    def generate_second_code_id(self, third_letter="B"):
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
        """树形项目点击事件 - 导航到对应句子并高亮"""
        try:
            item_data = item.data(0, Qt.UserRole)
            if not item_data:
                return

            level = item_data.get("level")
            if level == 1:  # 一阶编码
                content = item_data.get("content", "")
                code_id = item_data.get("code_id", "")
                sentence_details = item_data.get("sentence_details", [])

                # 显示句子详情对话框
                self.show_sentence_details_dialog(sentence_details, content, code_id)

                # 导航并高亮对应的句子内容
                if code_id and content:
                    success = self.navigate_and_highlight_sentence(code_id, content)
                    if success:
                        logger.info(f"成功导航到编码: {code_id}")
                    else:
                        logger.warning(f"未找到编码 {code_id} 对应的内容")

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

    def get_sentences_by_code_id(self, code_id: str) -> list:
        """根据编码ID获取对应的句子详情列表"""
        try:
            sentences = []

            # 遍历编码树查找匹配的编码ID
            def search_tree_for_sentences(item):
                for i in range(item.childCount()):
                    child = item.child(i)
                    child_data = child.data(0, Qt.UserRole)

                    if child_data and child_data.get("level") == 1:  # 一阶编码
                        if child_data.get("code_id") == code_id:
                            # 找到匹配的编码，返回其句子详情
                            sentence_details = child_data.get("sentence_details", [])
                            if sentence_details:
                                return sentence_details
                            else:
                                # 如果没有sentence_details，使用内容创建基本结构
                                content = child_data.get("content", "")
                                if content:
                                    return [{"text": content, "code_id": code_id}]

                    # 递归搜索子节点
                    result = search_tree_for_sentences(child)
                    if result:
                        return result

                return []

            # 遍历顶层项目
            for i in range(self.coding_tree.topLevelItemCount()):
                top_item = self.coding_tree.topLevelItem(i)
                result = search_tree_for_sentences(top_item)
                if result:
                    sentences.extend(result)
                    break

            # 如果在层级结构中没找到，检查顶层未分类的一阶编码
            if not sentences:
                for i in range(self.coding_tree.topLevelItemCount()):
                    top_item = self.coding_tree.topLevelItem(i)
                    top_data = top_item.data(0, Qt.UserRole)
                    if top_data and top_data.get("level") == 1 and top_data.get("code_id") == code_id:
                        content = top_data.get("content", "")
                        if content:
                            sentences.append({"text": content, "code_id": code_id})
                        break

            logger.info(f"编码 {code_id} 找到 {len(sentences)} 个句子")
            return sentences

        except Exception as e:
            logger.error(f"获取句子详情失败: {e}")
            return []

    def highlight_text_by_code_id_precise(self, code_id: str):
        """通过编码ID精确高亮文本和对应内容（基于sentence_details）"""
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

            # 获取编码对应的精确句子内容
            sentences_to_highlight = self.get_sentences_by_code_id(code_id)

            if not sentences_to_highlight:
                self.statusBar().showMessage(f"未找到编码 {code_id} 的句子详情") if hasattr(self, 'statusBar') else None
                return

            # 精确高亮每个句子（简化版本）
            found_count = 0
            first_match_cursor = None

            for sentence_info in sentences_to_highlight:
                sentence_content = sentence_info.get('text', '').strip()
                if not sentence_content:
                    continue

                # 在文本中查找并高亮这个精确句子
                search_cursor = self.text_display.textCursor()
                search_cursor.movePosition(cursor.Start)

                # 使用文本查找
                found_cursor = self.text_document.find(sentence_content, search_cursor)
                if not found_cursor.isNull():
                    # 设置浅蓝色高亮格式
                    highlight_format = found_cursor.charFormat()
                    highlight_format.setBackground(QColor(173, 216, 230))  # 浅蓝色背景
                    highlight_format.setForeground(QColor(0, 0, 139))  # 深蓝色文字
                    found_cursor.mergeCharFormat(highlight_format)

                    found_count += 1

                    # 记录第一个匹配项的位置用于滚动
                    if first_match_cursor is None:
                        first_match_cursor = self.text_display.textCursor()
                        first_match_cursor.setPosition(found_cursor.selectionStart())

            if found_count > 0 and first_match_cursor:
                # 滚动到第一个匹配项的位置
                self.text_display.setTextCursor(first_match_cursor)
                self.text_display.ensureCursorVisible()
                self.statusBar().showMessage(f"已高亮编码 {code_id} 的 {found_count} 个句子") if hasattr(self,
                                                                                                'statusBar') else None
            else:
                self.statusBar().showMessage(f"未找到编码 {code_id} 对应的句子内容") if hasattr(self, 'statusBar') else None

        except Exception as e:
            logger.error(f"精确高亮文本失败: {e}")
            import traceback
            traceback.print_exc()

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

    def navigate_to_number(self, number_str):
        """导航到特定的句子编号 [N] 并选中前面的一整句"""
        try:
            self.clear_text_highlights()
            target_marker = f"[{number_str}]"

            # 在文档中搜索 [N]
            document = self.text_display.document()
            cursor = document.find(target_marker)

            if not cursor.isNull():
                # 策略：从 [N] 开始向前搜索，直到遇到句子结束符或较大的间隔
                # 这是一种启发式方法，因为我们没有严格的句子边界
                found_cursor = QTextCursor(cursor)
                end_pos = found_count = found_cursor.selectionEnd()

                # 向前搜索可能的句子开头
                # 我们可以尝试创建一个反向搜索的临时游标
                temp_cursor = QTextCursor(found_cursor)

                # 简单实现：向前查找直到遇到上一个 [M] 或 换行符
                # 或者，我们可以利用 document.find 配合 FindBackward 选项

                # 获取当前块（段落）的内容
                block = temp_cursor.block()
                text = block.text()
                # 计算 target_marker 在该块内的相对位置
                # cursor.position() 是文档绝对位置
                # block.position() 是块起始绝对位置
                marker_pos_in_block = cursor.selectionStart() - block.position()

                # 在 marker 之前寻找最近的句子终止符 (。！？) 或其它标记 (])
                limit_pos = 0  # 块内搜索限制

                # 搜索当前块内，marker之前的内容
                pre_text = text[:marker_pos_in_block]

                # 寻找最近的分割点
                import re
                # 匹配：句号/问号/感叹号，或者 ] 符号（上一个编号的结束）
                # 我们寻找最后一个匹配项
                matches = list(re.finditer(r'[。！？\n]|\]', pre_text))

                start_offset = 0
                if matches:
                    last_match = matches[-1]
                    start_offset = last_match.end()

                # 构建最终的选择游标
                range_cursor = QTextCursor(document)
                # 起始位置 = 块起始 + 偏移
                start_abs_pos = block.position() + start_offset
                range_cursor.setPosition(start_abs_pos)
                range_cursor.setPosition(end_pos, QTextCursor.KeepAnchor)

                # 额外清理：如果选区开头包含空白或特殊符号，修剪一下
                sel_text = range_cursor.selectedText()
                if sel_text and sel_text[0].strip() == '':
                    # 开头是空白
                    start_abs_pos += (len(sel_text) - len(sel_text.lstrip()))
                    range_cursor.setPosition(start_abs_pos)
                    range_cursor.setPosition(end_pos, QTextCursor.KeepAnchor)

                extra_selections = []
                selection = QTextEdit.ExtraSelection()
                selection.cursor = range_cursor
                selection.format.setBackground(QColor(173, 216, 230))  # 浅蓝色背景
                selection.format.setForeground(QColor(0, 0, 139))  # 深蓝色文字
                extra_selections.append(selection)

                self.text_display.setExtraSelections(extra_selections)

                # 滚动到可见区域，只移动光标位置不带选择
                scroll_cursor = QTextCursor(cursor)
                scroll_cursor.clearSelection()
                self.text_display.setTextCursor(scroll_cursor)
                self.text_display.ensureCursorVisible()

                # 居中显示
                cursor_rect = self.text_display.cursorRect(scroll_cursor)
                viewport_height = self.text_display.viewport().height()
                scrollbar = self.text_display.verticalScrollBar()
                if scrollbar:
                    target_val = scrollbar.value() + cursor_rect.top() - viewport_height // 2
                    scrollbar.setValue(int(target_val))

                return True
            else:
                logger.warning(f"未找到编号 {target_marker}")
                return False

        except Exception as e:
            logger.error(f"导航到编号失败: {e}")
            return False

    def clear_text_highlights(self):
        """清除文本高亮"""
        try:
            # 简单的清除方法：重置ExtraSelections
            self.text_display.setExtraSelections([])
            logger.debug("已清除文本高亮")
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
        """保存当前编码树到指定文件夹（包含文件编码标记状态）"""
        try:
            # 在保存前先保存当前文件的编码标记状态
            self.save_current_file_coding_marks()

            # 确保目录存在
            save_dir = os.path.join(os.getcwd(), "projects", "手动编码编码树保存")
            os.makedirs(save_dir, exist_ok=True)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"编码树_{timestamp}.json"
            file_path = os.path.join(save_dir, filename)

            # 从树形控件构建完整的数据结构
            tree_data = self.extract_tree_data()

            # 构建完整保存数据（包含文件编码标记状态）
            save_data = {
                "timestamp": datetime.now().isoformat(),
                "tree_data": tree_data,
                "files_with_marks": self.get_files_with_coding_marks(),  # 保存文件编码标记状态
                "current_codes": self.current_codes,
                "unclassified_first_codes": self.unclassified_first_codes
            }

            # 保存完整的编码结构和文件状态
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            QMessageBox.information(self, "成功", f"编码树已保存到: {file_path}\n\n包含了所有文件的编码标记状态")
            logger.info(f"编码树已保存: {file_path}")

        except Exception as e:
            logger.error(f"保存编码树失败: {e}")
            QMessageBox.critical(self, "错误", f"保存编码树失败: {str(e)}")

    def import_coding_tree(self):
        """从文件导入编码树 - 恢复完整的树形结构和文件编码标记"""
        try:
            from PyQt5.QtWidgets import QFileDialog

            # 设置导入路径为手动编码编码树保存文件夹
            import_dir = os.path.join(os.path.dirname(__file__), "projects", "手动编码编码树保存")
            os.makedirs(import_dir, exist_ok=True)

            # 获取导入路径
            file_path, _ = QFileDialog.getOpenFileName(
                self, "导入编码树", import_dir, "JSON文件 (*.json);;所有文件 (*)"
            )

            if file_path:
                # 读取编码结构
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_data = json.load(f)

                # 检查是新格式还是旧格式
                is_old_format = not isinstance(imported_data, dict) or 'tree_data' not in imported_data

                if is_old_format:
                    # 旧格式：直接是 tree_data
                    tree_data = imported_data
                    files_with_marks = None
                    format_info = "旧格式编码树（不包含文件编码标记）"
                else:
                    # 新格式：包含完整数据
                    tree_data = imported_data.get('tree_data', [])
                    files_with_marks = imported_data.get('files_with_marks', {})
                    format_info = f"新格式编码树（包含 {len(files_with_marks)} 个文件的编码标记）"

                # 询问用户是否确认导入编码树
                reply = QMessageBox.question(
                    self, "确认导入",
                    f"检测到 {format_info}\n\n确定要导入编码树吗？这将替换当前的编码结构。",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    # 使用导入的数据重建树形结构
                    self.rebuild_tree_from_data(tree_data)

                    # 恢复文件的编码标记状态（如果存在）
                    if files_with_marks:
                        self.restore_files_with_coding_marks(files_with_marks)
                        logger.info(f"已恢复 {len(files_with_marks)} 个文件的编码标记状态")

                    # 恢复相关的编码数据（如果存在）
                    if not is_old_format:
                        if 'current_codes' in imported_data:
                            self.current_codes = imported_data['current_codes']
                        if 'unclassified_first_codes' in imported_data:
                            self.unclassified_first_codes = imported_data['unclassified_first_codes']

                    # 刷新当前文件显示（以显示恢复的编码标记）
                    if files_with_marks:
                        # 如果有文件编码标记，刷新所有文件显示
                        self.refresh_all_files_display()
                    else:
                        # 如果没有编码标记，只刷新当前文件
                        current_item = self.file_list.currentItem()
                        if current_item:
                            self.refresh_current_file_display()

                    success_msg = f"编码树已从 {os.path.basename(file_path)} 导入"
                    if files_with_marks:
                        success_msg += f"\n\n已恢复 {len(files_with_marks)} 个文件的编码标记状态"

                    QMessageBox.information(self, "成功", success_msg)
                    logger.info(f"编码树已导入: {file_path}")

        except Exception as e:
            logger.error(f"导入编码树失败: {e}")
            QMessageBox.critical(self, "错误", f"导入编码树失败: {str(e)}")

    def import_coding_results(self):
        """导入之前保存的编码结果"""
        try:
            from PyQt5.QtWidgets import QFileDialog

            # 设置导入路径为手动编码保存编码文件夹
            import_dir = os.path.join(os.path.dirname(__file__), "projects", "手动编码保存编码")
            os.makedirs(import_dir, exist_ok=True)

            # 获取导入路径
            file_path, _ = QFileDialog.getOpenFileName(
                self, "导入编码结果", import_dir, "JSON文件 (*.json);;所有文件 (*)"
            )

            if file_path:
                # 读取编码结果
                with open(file_path, 'r', encoding='utf-8') as f:
                    coding_data = json.load(f)

                # 询问用户是否确认导入
                reply = QMessageBox.question(
                    self, "确认导入",
                    "确定要导入编码结果吗？这将加载之前的编码进度和状态。",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    # 恢复编码数据
                    if 'coding_progress' in coding_data:
                        progress = coding_data['coding_progress']
                        # 恢复文件选择状态
                        if 'current_file' in progress:
                            self.restore_file_selection(progress['current_file'])
                        # 恢复编码计数
                        if 'last_code_id' in progress:
                            self.restore_code_counter(progress['last_code_id'])

                    # 恢复编码树数据
                    if 'coding_data' in coding_data:
                        self.rebuild_tree_from_data(coding_data['coding_data'])

                    # 恢复current_codes和unclassified_first_codes
                    if 'current_codes' in coding_data:
                        self.current_codes = coding_data['current_codes']

                    if 'unclassified_first_codes' in coding_data:
                        self.unclassified_first_codes = coding_data['unclassified_first_codes']

                    # 恢复文件的编码标记状态
                    if 'files_with_marks' in coding_data:
                        self.restore_files_with_coding_marks(coding_data['files_with_marks'])
                        logger.info(f"恢复了文件的编码标记状态")

                    # 刷新所有文件显示（确保所有文件都能正确显示编码标记）
                    self.refresh_all_files_display()

                    QMessageBox.information(self, "成功",
                                            f"编码结果已从 {os.path.basename(file_path)} 导入\n\n编码进度已恢复，您可以从上次的位置继续编码。")
                    logger.info(f"编码结果已导入: {file_path}")

                    # 不自动恢复到最后编码位置，让用户手动选择文件
                    # self.restore_last_coding_position()

        except Exception as e:
            logger.error(f"导入编码结果失败: {e}")
            QMessageBox.critical(self, "错误", f"导入编码结果失败: {str(e)}")

    def show_sentence_details_dialog(self, sentence_details, content, code_id):
        """显示句子详情对话框"""
        try:
            if not sentence_details:
                # 如果没有句子详情，至少显示当前内容
                sentence_details = [{"text": content, "code_id": code_id}]

            # 处理句子详情：将合并的内容拆分为单独的句子显示
            # 先处理数据，以便闭包可以使用 processed_items
            processed_items = []
            seen_items = set()  # 去重集合
            import re

            for detail in sentence_details:
                raw_text = detail.get('text', '').strip()
                file_path = detail.get('file_path', '')

                # 尝试拆分包含多个 [N] 的文本
                matches = list(re.finditer(r'(.*?)(\[\d+\])', raw_text, re.DOTALL))

                if matches:
                    for match in matches:
                        part_content = match.group(0).strip()  # 包含编号的整句
                        number_str = match.group(2)  # [10]
                        number = number_str.strip('[]')

                        # 对内容去除空白，对路径取文件名进行去重
                        content_sig = "".join(part_content.split())
                        file_sig = os.path.basename(file_path) if file_path else ""

                        unique_key = (str(number), content_sig, file_sig)
                        if unique_key not in seen_items:
                            seen_items.add(unique_key)
                            processed_items.append({
                                'number': number,
                                'content': part_content,
                                'file_path': file_path
                            })

                    last_end = matches[-1].end()
                    if last_end < len(raw_text):
                        remainder = raw_text[last_end:].strip()
                        if remainder:
                            content_sig = "".join(remainder.split())
                            file_sig = os.path.basename(file_path) if file_path else ""
                            unique_key = ("?", content_sig, file_sig)
                            if unique_key not in seen_items:
                                seen_items.add(unique_key)
                                processed_items.append({
                                    'number': "?",
                                    'content': remainder,
                                    'file_path': file_path
                                })
                else:
                    item_id = detail.get('sentence_id', detail.get('code_id', code_id))

                    content_sig = "".join(raw_text.split())
                    file_sig = os.path.basename(file_path) if file_path else ""

                    unique_key = (str(item_id), content_sig, file_sig)

                    if unique_key not in seen_items:
                        seen_items.add(unique_key)
                        processed_items.append({
                            'number': item_id,
                            'content': raw_text,
                            'file_path': file_path
                        })

            # 按编号排序，数字编号优先
            def sort_key(item):
                n = item['number']
                if str(n).isdigit():
                    return int(n)
                return 999999

            processed_items.sort(key=sort_key)

            # 创建对话框
            dialog = QDialog(self)
            dialog.setWindowTitle(
                f"句子详情 - {code_id}: {content[:30]}..." if len(content) > 30 else f"句子详情 - {code_id}: {content}")
            dialog.resize(900, 700)  # 稍微加大窗口

            layout = QVBoxLayout(dialog)

            # 创建 HTML 格式内容
            from PyQt5.QtWidgets import QTextBrowser

            # 创建文本显示区域（使用 QTextBrowser 支持链接）
            text_display = QTextBrowser()
            text_display.setOpenExternalLinks(False)

            # 连接链接点击信号
            def link_clicked(url):
                try:
                    sentence_number = url.toString()
                    # 如果是有效的数字编号，进行导航
                    if sentence_number.isdigit():
                        dialog.close()

                        # 在 processed_items 中查找对应的文本内容
                        target_content = None
                        for item in processed_items:
                            if str(item['number']) == sentence_number:
                                target_content = item['content']
                                break

                        # 导航并高亮，传入具体内容以便全句高亮
                        # 即使找不到内容（target_content为None），也可以回退到只高亮编号
                        self.navigate_and_highlight_sentence(sentence_number, target_content)
                except Exception as e:
                    logger.error(f"导航到句子失败: {e}")

            text_display.anchorClicked.connect(link_clicked)

            # 构建显示内容
            # 使用简单的 div 和 style 确保字体一致性
            # 将 font-size 和 line-height 调大
            display_html = f"""
            <div style='font-family: "Microsoft YaHei", Arial, sans-serif; font-size: 18px; line-height: 1.8;'>
                <div style='font-weight: bold; margin-bottom: 5px; font-size: 20px;'>一阶编码: {code_id}:</div>
                <div style='margin-bottom: 15px; font-size: 18px;'>{content}</div>
                <hr>
            """

            for i, item in enumerate(processed_items, 1):
                number = item['number']
                content_text = item.get('content', '')
                file_path = item.get('file_path', '')
                file_name = os.path.basename(file_path) if file_path and file_path != "未知文件" else ""

                display_html += f"<div style='margin-top: 15px; margin-bottom: 5px; font-weight: bold; font-size: 18px;'>句子 {i}:</div>"
                display_html += f"<div style='font-size: 18px;'>编号: {number}</div>"
                if file_name:
                    display_html += f"<div style='font-size: 18px;'>文件: {file_name}</div>"

                # 将内容变成链接，如果它是有效的数字编号
                if str(number).isdigit():
                    display_html += f"<div style='font-size: 18px;'>内容: <a href='{number}' style='color: #000000; text-decoration: none; font-size: 18px;'>{content_text}</a></div><br>"
                else:
                    display_html += f"<div style='font-size: 18px;'>内容: {content_text}</div><br>"

            display_html += "</div>"

            text_display.setHtml(display_html)
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

    def merge_sentence_details(self, sentence_details):
        """智能合并句子详情"""
        try:
            if not sentence_details:
                return []

            merged = []
            current_group = None

            for detail in sentence_details:
                if isinstance(detail, dict):
                    text = detail.get('text', '').strip()
                    file_path = detail.get('file_path', '')

                    # 提取句子中的所有编号
                    numbers = re.findall(r'\[(\d+)\]', text)
                    numbers = [int(n) for n in numbers]

                    # 清理文本，保留编号标记用于合并判断
                    clean_text = text

                    if current_group is None:
                        # 开始新的分组
                        current_group = {
                            'numbers': numbers,
                            'content': clean_text,
                            'file_path': file_path,
                            'texts': [clean_text]
                        }
                    else:
                        # 检查是否应该与当前组合并
                        should_merge = False

                        # 检查编号连续性
                        if numbers and current_group['numbers']:
                            last_number = max(current_group['numbers'])
                            first_new_number = min(numbers)
                            # 如果编号连续或相邻，则合并
                            if abs(first_new_number - last_number) <= 2:
                                should_merge = True

                        # 检查文件是否相同
                        if file_path != current_group['file_path']:
                            should_merge = False

                        if should_merge:
                            # 合并到当前组
                            current_group['numbers'].extend(numbers)
                            current_group['numbers'] = sorted(list(set(current_group['numbers'])))
                            current_group['texts'].append(clean_text)
                            # 合并内容，移除重复的编号标记
                            merged_content = ""
                            for txt in current_group['texts']:
                                # 移除编号标记，保留纯文本
                                clean_txt = re.sub(r'\s*\[\d+\]\s*', '', txt).strip()
                                if clean_txt and clean_txt not in merged_content:
                                    if merged_content:
                                        merged_content += " "
                                    merged_content += clean_txt

                            # 重新添加编号标记
                            current_group['content'] = merged_content
                            for num in current_group['numbers']:
                                current_group['content'] += f" [{num}]"

                        else:
                            # 保存当前组并开始新组
                            merged.append(current_group)
                            current_group = {
                                'numbers': numbers,
                                'content': clean_text,
                                'file_path': file_path,
                                'texts': [clean_text]
                            }
                else:
                    # 处理字符串格式的详情
                    if current_group is None:
                        current_group = {
                            'numbers': [],
                            'content': str(detail),
                            'file_path': '',
                            'texts': [str(detail)]
                        }
                    else:
                        merged.append(current_group)
                        current_group = {
                            'numbers': [],
                            'content': str(detail),
                            'file_path': '',
                            'texts': [str(detail)]
                        }

            # 添加最后一个组
            if current_group is not None:
                merged.append(current_group)

            return merged

        except Exception as e:
            logger.error(f"合并句子详情失败: {e}")
            return sentence_details

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
        current_items = self.coding_tree.selectedItems()
        if not current_items:
            QMessageBox.information(self, "提示", "请先选择一个节点")
            return

        # 如果选择了多个节点，执行批量编辑
        if len(current_items) > 1:
            self.batch_edit_tree_items(current_items)
            return

        # 单个节点编辑
        current_item = current_items[0]

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

    def batch_edit_tree_items(self, items):
        """批量编辑多个选中的编码节点"""
        try:
            # 检查选中的节点是否都是同一层级
            levels = set()
            for item in items:
                item_data = item.data(0, Qt.UserRole)
                if item_data:
                    levels.add(item_data.get('level'))

            if len(levels) > 1:
                QMessageBox.warning(self, "警告", "只能批量编辑同一层级的编码节点")
                return

            if not levels:
                QMessageBox.warning(self, "警告", "选中的节点数据无效")
                return

            level = levels.pop()

            # 根据层级执行不同的批量编辑操作
            if level == 1:
                self._batch_edit_first_level(items)
            elif level == 2:
                self._batch_edit_second_level(items)
            elif level == 3:
                self._batch_edit_third_level(items)

        except Exception as e:
            logger.error(f"批量编辑失败: {e}")
            QMessageBox.critical(self, "错误", f"批量编辑失败: {str(e)}")

    def _batch_edit_first_level(self, items):
        """批量编辑一阶编码"""
        dialog = QDialog(self)
        dialog.setWindowTitle("批量编辑一阶编码")
        dialog.resize(600, 500)

        layout = QVBoxLayout(dialog)

        label = QLabel(f"批量编辑 {len(items)} 个一阶编码")
        layout.addWidget(label)

        # 显示选中的编码列表
        list_widget = QListWidget()
        for item in items:
            list_item = QListWidgetItem(item.text(0))
            list_widget.addItem(list_item)
        layout.addWidget(list_widget)

        # 批量操作选项
        operation_group = QGroupBox("批量操作")
        operation_layout = QVBoxLayout(operation_group)

        # 选项：移除自动生成标识
        remove_auto_checkbox = QCheckBox("移除自动生成标识")
        operation_layout.addWidget(remove_auto_checkbox)

        # 选项：更新来源为手动
        update_source_checkbox = QCheckBox("更新来源为手动")
        operation_layout.addWidget(update_source_checkbox)

        layout.addWidget(operation_group)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        def on_ok():
            changes = 0
            for item in items:
                item_data = item.data(0, Qt.UserRole)
                if not item_data:
                    continue

                # 移除自动生成标识
                if remove_auto_checkbox.isChecked() and item_data.get('auto_generated', False):
                    item_data['auto_generated'] = False
                    changes += 1

                # 更新来源为手动
                if update_source_checkbox.isChecked():
                    item_data['source'] = 'manual'
                    changes += 1

                # 应用更改
                if changes > 0:
                    item.setData(0, Qt.UserRole, item_data)

            if changes > 0:
                self.update_structured_codes_from_tree()
                QMessageBox.information(self, "成功", f"已完成批量编辑，共修改 {changes} 个编码")
            else:
                QMessageBox.information(self, "提示", "没有进行任何修改")

            dialog.accept()

        ok_button.clicked.connect(on_ok)
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec_()

    def _batch_edit_second_level(self, items):
        """批量编辑二阶编码"""
        dialog = QDialog(self)
        dialog.setWindowTitle("批量编辑二阶编码")
        dialog.resize(600, 500)

        layout = QVBoxLayout(dialog)

        label = QLabel(f"批量编辑 {len(items)} 个二阶编码")
        layout.addWidget(label)

        # 显示选中的编码列表
        list_widget = QListWidget()
        for item in items:
            list_item = QListWidgetItem(item.text(0))
            list_widget.addItem(list_item)
        layout.addWidget(list_widget)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        def on_ok():
            # 目前只支持显示列表，后续可以添加更多批量操作
            QMessageBox.information(self, "提示", "批量编辑二阶编码功能即将推出")
            dialog.accept()

        ok_button.clicked.connect(on_ok)
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec_()

    def _batch_edit_third_level(self, items):
        """批量编辑三阶编码"""
        dialog = QDialog(self)
        dialog.setWindowTitle("批量编辑三阶编码")
        dialog.resize(600, 500)

        layout = QVBoxLayout(dialog)

        label = QLabel(f"批量编辑 {len(items)} 个三阶编码")
        layout.addWidget(label)

        # 显示选中的编码列表
        list_widget = QListWidget()
        for item in items:
            list_item = QListWidgetItem(item.text(0))
            list_widget.addItem(list_item)
        layout.addWidget(list_widget)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        def on_ok():
            # 目前只支持显示列表，后续可以添加更多批量操作
            QMessageBox.information(self, "提示", "批量编辑三阶编码功能即将推出")
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

                        # 正确处理三阶-二阶-一阶结构中的一阶编码
                        if first_item_data and isinstance(first_item_data, dict):
                            # 更新一阶编码的统计数据
                            first_item_data["sentence_count"] = int(first_item.text(4)) if first_item.text(
                                4).isdigit() else 1
                            first_item_data["code_id"] = first_item.text(5) if first_item.text(
                                5) else first_item_data.get("code_id", "")
                            # 修复：应该添加到正确的嵌套结构中，而不是未分类编码
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

        # 调试输出
        print(f"DEBUG: 更新后 current_codes 结构:")
        for third_cat, second_cats in self.current_codes.items():
            print(f"  {third_cat}: {len(second_cats)} 个二阶编码")
            for second_cat, first_contents in second_cats.items():
                print(f"    {second_cat}: {len(first_contents)} 个一阶编码")
        print(f"DEBUG: 未分类一阶编码: {len(self.unclassified_first_codes)} 个")

    def update_coding_tree(self):
        """更新编码结构树"""
        try:
            # ---------------------------------------------------------
            # 自动修复编号：确保所有一阶编码都有A开头的规范编号
            # ---------------------------------------------------------
            existing_a_ids = set()
            
            # 1. 第一遍遍历：收集所有已存在的A开头有效编号
            # 检查已分类编码
            for third_cat, second_cats in self.current_codes.items():
                for second_cat, first_contents in second_cats.items():
                    for content in first_contents:
                        if isinstance(content, dict):
                            cid = str(content.get('code_id', ''))
                            if cid.startswith('A') and cid[1:].isdigit():
                                existing_a_ids.add(cid)
            
            # 检查未分类编码
            for item in self.unclassified_first_codes:
                if isinstance(item, dict):
                    cid = str(item.get('code_id', ''))
                    if cid.startswith('A') and cid[1:].isdigit():
                        existing_a_ids.add(cid)
            
            # 准备ID生成器
            next_num = 1
            while f"A{next_num:02d}" in existing_a_ids:
                next_num += 1
                
            # 2. 第二遍遍历：为没有规范编号的一阶编码分配新编号
            # 处理已分类编码
            for third_cat, second_cats in self.current_codes.items():
                for second_cat, first_contents in second_cats.items():
                    for i, content in enumerate(first_contents):
                        # 确保转换为字典
                        if not isinstance(content, dict):
                            content = {'content': str(content), 'code_id': ''}
                            first_contents[i] = content
                        
                        cid = str(content.get('code_id', ''))
                        # 如果没有编号，或者编号不是A开头（例如是纯数字句子编号）
                        if not (cid.startswith('A') and cid[1:].isdigit()):
                            # 尝试从内容开头提取现有编号（如果是Axx格式）
                            import re
                            content_text = content.get('content', '')
                            match = re.match(r'^(A\d+)', content_text)
                            
                            new_id = None
                            if match:
                                extracted_id = match.group(1)
                                if extracted_id not in existing_a_ids:
                                    new_id = extracted_id
                            
                            if not new_id:
                                new_id = f"A{next_num:02d}"
                                # 查找下一个可用编号
                                while f"A{next_num:02d}" in existing_a_ids or new_id in existing_a_ids:
                                    if new_id in existing_a_ids:
                                        # 如果刚生成的ID已被占用（比如通过内容提取占用了），递增重新生成
                                        pass
                                    next_num += 1
                                    new_id = f"A{next_num:02d}"
                            
                            content['code_id'] = new_id
                            existing_a_ids.add(new_id)

            # 处理未分类编码
            for i, item in enumerate(self.unclassified_first_codes):
                 if not isinstance(item, dict):
                     item = {'content': str(item), 'code_id': ''}
                     self.unclassified_first_codes[i] = item
                 
                 cid = str(item.get('code_id', ''))
                 if not (cid.startswith('A') and cid[1:].isdigit()):
                     # 尝试从内容提取
                     import re
                     content_text = item.get('content', '')
                     match = re.match(r'^(A\d+)', content_text)
                     
                     new_id = None
                     if match:
                         extracted_id = match.group(1)
                         if extracted_id not in existing_a_ids:
                             new_id = extracted_id
                     
                     if not new_id:
                         new_id = f"A{next_num:02d}"
                         while f"A{next_num:02d}" in existing_a_ids or new_id in existing_a_ids:
                             if new_id in existing_a_ids:
                                 pass
                             next_num += 1
                             new_id = f"A{next_num:02d}"
                             
                     item['code_id'] = new_id
                     existing_a_ids.add(new_id)
            # ---------------------------------------------------------

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

                        # 修复：将句子编号替换为所属一阶编码的编号
                        # 提取原始内容（去除可能的编号前缀）
                        if content_text.startswith(code_id + ': '):
                            original_content = content_text[len(code_id + ': '):]
                        elif content_text.startswith(code_id + ' '):
                            original_content = content_text[len(code_id + ' '):]
                        else:
                            original_content = content_text

                        # 额外修复：移除可能的句子编号前缀（如 "1, 58 ", "68 ", "[68] ", "1 " 等）
                        # 只有当原始内容以数字开头时才尝试清理，避免误伤
                        if original_content and (original_content[0].isdigit() or original_content.startswith('[')):
                            import re
                            # 移除 "1, 58 " 这种格式 (文件索引, 句子索引)
                            original_content = re.sub(r'^\d+\s*,\s*\d+\s*', '', original_content)
                            # 移除 "68 " 或 "[68] " 或 "1 " 这种格式
                            original_content = re.sub(r'^(?:\[\d+\]|\d+)\s+', '', original_content)

                        display_content = f"{code_id} {original_content}"
                        first_item.setText(0, display_content)
                        
                        # 重新定义 numbered_first_content 用于数据存储
                        numbered_first_content = display_content

                        first_item.setText(1, "一阶编码")
                        first_item.setText(2, "1")
                        first_item.setText(3, str(len(first_file_sources)) if first_file_sources else "1")  # 文件来源数
                        first_item.setText(4, str(len(
                            first_sentence_sources) if first_sentence_sources else sentence_count))  # 句子来源数
                        
                        # Fix: Determine what to show in "Associated ID" column
                        # If there are sentence details, show their IDs
                        associated_id = code_id if code_id else ""
                        if first_sentence_sources:
                            # If we have sentence sources, display them (e.g., "117" or "68, 117")
                            associated_id = ", ".join(sorted(first_sentence_sources, key=lambda x: int(x) if x.isdigit() else float('inf')))
                        
                        first_item.setText(5, associated_id)  # 关联编号
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
                    # 修复：二阶编码显示自己的编号(Bxx)而不是子节点编号
                    second_item.setText(5, second_code_id)  # 关联编号：显示二阶编码ID(Bxx)
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
                # 修复：三阶编码显示自己的编号(Cxx)而不是子节点编号
                third_item.setText(5, third_code_id)  # 关联编号：显示三阶编码ID(Cxx)

            # 添加未分类的一阶编码
            for first_code in self.unclassified_first_codes:
                first_item = QTreeWidgetItem(self.coding_tree)

                # 处理first_code，它可能是一个字典或字符串
                if isinstance(first_code, dict):
                    # 如果是字典，获取内容和编号
                    content_text = first_code.get('content', str(first_code))
                    code_id = first_code.get('code_id', '')
                    numbered_content = first_code.get('numbered_content',
                                                      f"{code_id} {content_text}" if code_id else content_text)
                    sentence_count = first_code.get('sentence_count', 1)
                    sentence_details = first_code.get('sentence_details', [])
                    
                    # Extract sentence IDs for unclassified codes as well
                    first_sentence_sources = set()
                    for sentence in sentence_details:
                        if isinstance(sentence, dict):
                            sentence_id = sentence.get('sentence_id', '')
                            if sentence_id:
                                first_sentence_sources.add(str(sentence_id))

                    first_item.setText(0, numbered_content)
                    first_item.setText(1, "一阶编码")
                    first_item.setText(2, "1")
                    first_item.setText(3, "1")  # 文件来源数
                    first_item.setText(4, str(sentence_count))  # 句子来源数
                    
                    # Fix: Show sentence IDs in "Associated ID" column if available
                    associated_id = code_id if code_id else ""
                    if first_sentence_sources:
                         associated_id = ", ".join(sorted(first_sentence_sources, key=lambda x: int(x) if x.isdigit() else float('inf')))
                    
                    first_item.setText(5, associated_id)  # 关联编号

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
            if len(name) > 300:
                return False, "", "一阶编码名称不能超过300个字符"
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
        """保存编码并记录编码进度"""
        try:
            # 保存当前文件的编码标记状态（重要！）
            self.save_current_file_coding_marks()

            # 确保目录存在
            save_dir = os.path.join(os.getcwd(), "projects", "手动编码保存编码")
            os.makedirs(save_dir, exist_ok=True)

            # 获取当前编码进度信息
            progress_info = self.get_current_coding_progress()

            # 生成保存文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"手动编码_{timestamp}.json"
            file_path = os.path.join(save_dir, filename)

            # 构建保存数据
            save_data = {
                "timestamp": datetime.now().isoformat(),
                "coding_progress": progress_info,
                "coding_data": self.build_tree_data(),
                "current_codes": self.current_codes,
                "unclassified_first_codes": self.unclassified_first_codes,
                "files_with_marks": self.get_files_with_coding_marks()  # 保存所有文件的编码标记状态
            }

            # 保存数据
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            # 保存最后编码位置信息（用于下次自动恢复）
            self.save_last_coding_position(progress_info)

            QMessageBox.information(self, "成功", f"编码已保存到: {file_path}\n\n编码进度已记录，下次打开将自动恢复到当前位置。")
            logger.info(f"编码已保存: {file_path}")
            return True

        except Exception as e:
            logger.error(f"保存编码失败: {e}")
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
            return False

    def get_current_coding_progress(self):
        """获取当前编码进度信息"""
        try:
            progress = {
                "current_file": None,
                "current_file_name": None,
                "current_position": 0,
                "last_code_id": None,
                "last_code_letter": None,
                "last_code_number": 0,
                "total_codes": 0,
                "files_info": []
            }

            # 获取当前选中的文件
            if hasattr(self, 'file_list') and self.file_list.currentItem():
                current_item = self.file_list.currentItem()
                progress["current_file"] = current_item.data(Qt.UserRole)
                progress["current_file_name"] = current_item.text()

            # 获取当前光标位置
            if hasattr(self, 'text_display'):
                cursor = self.text_display.textCursor()
                progress["current_position"] = cursor.position()

            # 获取当前编码计数器状态
            if hasattr(self, 'last_code_letter') and hasattr(self, 'last_code_number'):
                progress["last_code_letter"] = self.last_code_letter
                progress["last_code_number"] = self.last_code_number
                progress["last_code_id"] = f"{self.last_code_letter}{self.last_code_number:02d}"
            else:
                # 获取最大的编码ID
                max_code_number = 0
                last_code_id = None
                last_code_letter = 'A'  # 默认字母
                for i in range(self.coding_tree.topLevelItemCount()):
                    item = self.coding_tree.topLevelItem(i)
                    item_data = item.data(0, Qt.UserRole)
                    if item_data and item_data.get("code_id"):
                        code_id = item_data.get("code_id")
                        # 提取编号（如A01 -> A, 01）
                        import re
                        match = re.match(r'([A-Z])(\d+)', code_id)
                        if match:
                            code_letter = match.group(1)
                            code_number = int(match.group(2))
                            if code_number > max_code_number:
                                max_code_number = code_number
                                last_code_id = code_id
                                last_code_letter = code_letter

                progress["last_code_id"] = last_code_id
                progress["last_code_letter"] = last_code_letter
                progress["last_code_number"] = max_code_number

            progress["total_codes"] = self.coding_tree.topLevelItemCount()

            # 记录所有文件信息
            if hasattr(self, 'file_list'):
                for i in range(self.file_list.count()):
                    item = self.file_list.item(i)
                    progress["files_info"].append({
                        "file_path": item.data(Qt.UserRole),
                        "file_name": item.text()
                    })

            return progress

        except Exception as e:
            logger.error(f"获取编码进度失败: {e}")
            return {}

    def save_last_coding_position(self, progress_info):
        """保存最后编码位置（用于自动恢复）"""
        try:
            position_file = os.path.join(os.getcwd(), "projects", "last_coding_position.json")
            os.makedirs(os.path.dirname(position_file), exist_ok=True)

            with open(position_file, 'w', encoding='utf-8') as f:
                json.dump(progress_info, f, ensure_ascii=False, indent=2)

            logger.info("最后编码位置已保存")

        except Exception as e:
            logger.error(f"保存最后编码位置失败: {e}")

    def restore_last_coding_position(self):
        """恢复到上次编码的位置"""
        try:
            position_file = os.path.join(os.getcwd(), "projects", "last_coding_position.json")
            if not os.path.exists(position_file):
                return

            with open(position_file, 'r', encoding='utf-8') as f:
                progress_info = json.load(f)

            # 恢复文件选择
            current_file = progress_info.get("current_file")
            if current_file and hasattr(self, 'file_list'):
                for i in range(self.file_list.count()):
                    item = self.file_list.item(i)
                    if item.data(Qt.UserRole) == current_file:
                        self.file_list.setCurrentItem(item)
                        break

            # 获取最后编码的ID，用于定位
            last_code_id = progress_info.get("last_code_id")
            if last_code_id and hasattr(self, 'text_display'):
                # 在文本中查找最后的编码标记并高亮显示
                text_content = self.text_display.toPlainText()
                marker = f"[{last_code_id}]"
                position = text_content.find(marker)
                if position != -1:
                    # 创建一个文本光标并移动到该位置
                    cursor = self.text_display.textCursor()
                    cursor.setPosition(position)
                    self.text_display.setTextCursor(cursor)

                    # 滚动到该位置
                    self.text_display.ensureCursorVisible()

                    # 高亮显示该编码
                    self.highlight_last_coding(marker, position)

            logger.info(f"已恢复到上次编码位置: {progress_info.get('current_file_name', '未知文件')}, 最后编码: {last_code_id}")

        except Exception as e:
            logger.error(f"恢复上次编码位置失败: {e}")

    def check_and_restore_last_coding_position(self):
        """检查是否有可恢复的编码进度，并询问用户是否恢复"""
        try:
            position_file = os.path.join(os.getcwd(), "projects", "last_coding_position.json")
            if not os.path.exists(position_file):
                return  # 没有上次的进度文件

            with open(position_file, 'r', encoding='utf-8') as f:
                progress_info = json.load(f)

            # 检查是否有有效的进度信息
            last_code_id = progress_info.get("last_code_id")
            current_file_name = progress_info.get("current_file_name")
            total_codes = progress_info.get("total_codes", 0)

            if last_code_id and total_codes > 0:
                # 询问用户是否恢复
                msg = f"发现上次的编码进度：\n\n"
                msg += f"文件：{current_file_name or '未知文件'}\n"
                msg += f"最后编码：{last_code_id}\n"
                msg += f"总编码数：{total_codes}\n\n"
                msg += "是否要恢复到上次编码的位置继续工作？"

                reply = QMessageBox.question(
                    self, "恢复编码进度",
                    msg,
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes  # 默认选择恢复
                )

                if reply == QMessageBox.Yes:
                    self.restore_last_coding_position()
                    QMessageBox.information(
                        self, "已恢复",
                        f"编码进度已恢复！\n下个编码将从 {last_code_id} 后继续。"
                    )

        except Exception as e:
            logger.error(f"检查编码进度失败: {e}")

    def highlight_last_coding(self, marker, position):
        """高亮显示最后编码的位置"""
        try:
            extra_selections = []
            selection = QTextEdit.ExtraSelection()

            # 设置高亮颜色 (绿色背景表示恢复的位置)
            selection.format.setBackground(QColor(144, 238, 144))  # 浅绿色

            # 创建光标并选择标记
            cursor = self.text_display.textCursor()
            cursor.setPosition(position)
            cursor.setPosition(position + len(marker), QTextCursor.KeepAnchor)
            selection.cursor = cursor

            extra_selections.append(selection)
            self.text_display.setExtraSelections(extra_selections)

            # 3秒后清除高亮
            QTimer.singleShot(3000, lambda: self.text_display.setExtraSelections([]))

        except Exception as e:
            logger.error(f"高亮显示最后编码失败: {e}")

    def export_to_standard(self):
        """导出为标准答案 - 修复版"""
        # 调试输出当前状态
        print("=" * 50)
        print("DEBUG: 导出状态检查")
        print("=" * 50)
        print(f"current_codes 类型: {type(self.current_codes)}")
        print(f"current_codes 内容: {self.current_codes}")
        print(f"current_codes 长度: {len(self.current_codes)}")
        print(f"coding_tree 项目数: {self.coding_tree.topLevelItemCount()}")
        print(f"unclassified_first_codes: {len(self.unclassified_first_codes)}")
        print("=" * 50)

        # 确保数据是最新的
        self.update_structured_codes_from_tree()

        # 更严格的检查条件
        if not self.current_codes and not self.unclassified_first_codes:
            QMessageBox.warning(self, "警告", "没有编码数据可导出\n\n请先添加至少一个编码")
            return

        # 额外检查：如果 current_codes 为空但有未分类编码，尝试重构数据
        if not self.current_codes and self.unclassified_first_codes:
            print("DEBUG: current_codes 为空但有未分类编码，正在重构数据...")
            # 强制更新数据结构
            self.update_structured_codes_from_tree()
            if not self.current_codes:
                # 如果仍然为空，创建基本结构
                self.current_codes = {"未分类编码": {"未分类": self.unclassified_first_codes.copy()}}
                print(f"DEBUG: 已创建基本结构: {self.current_codes}")

        description, ok = QInputDialog.getText(self, "标准答案描述", "请输入本次标准答案的描述:")
        if ok:
            # 通过父窗口保存为标准答案
            parent = self.parent()
            print(f"DEBUG: 父窗口类型: {type(parent)}")
            if hasattr(parent, 'standard_answer_manager'):
                print("DEBUG: 找到 standard_answer_manager")
                version_id = parent.standard_answer_manager.create_from_structured_codes(
                    self.current_codes, description
                )
                if version_id:
                    # 简化修复：导出成功后更新编码树显示，不显示弹窗
                    print(f"DEBUG: 导出成功，版本号: {version_id}")
                    print("DEBUG: 正在更新编码树显示...")
                    
                    # 更新编码树显示，确保编号格式正确
                    self.update_coding_tree()
                    
                    # 不显示弹窗，只更新状态栏
                    self.statusBar().showMessage(f"导出成功: {version_id}")
                else:
                    QMessageBox.critical(self, "错误", "导出失败")
            else:
                QMessageBox.critical(self, "错误", "父窗口缺少 standard_answer_manager\n\n请通过主界面启动手动编码功能")

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

            # 解析内容中的编号和对应的句子文本
            import re
            number_matches = re.findall(r'\[(\d+)\]', clean_content)

            sentence_id = code_id
            detail_text = clean_content

            if number_matches:
                # 使用最后一个编号作为关联ID
                tmng_number = number_matches[-1]
                sentence_id = tmng_number

                # 尝试提取特定句子文本
                # 逻辑: 查找以 [ID] 结尾的句子片段
                # (?:^|\]\s*) : 匹配开头 或者 ]后跟空白
                # ([^\[\]]*?\[...\]) : 捕获组，非贪婪匹配内容，以 [ID] 结尾
                try:
                    pattern = r'(?:^|\]\s*)([^\[\]]*?\[' + re.escape(tmng_number) + r'\])'
                    match = re.search(pattern, clean_content, re.DOTALL)
                    if match:
                        detail_text = match.group(1).strip()
                except Exception as e:
                    logger.error(f"提取句子文本失败: {e}")
                    # 失败则使用全部内容
            else:
                tmng_number = code_id

            # 尝试获取当前选中的文件路径
            current_file_path = ""
            if hasattr(self, 'file_list') and self.file_list.currentItem():
                current_file_path = self.file_list.currentItem().data(Qt.UserRole)

            # 创建句子详情
            sentence_details = [{
                "text": detail_text,
                "code_id": sentence_id,
                "file_path": current_file_path,
                "sentence_id": sentence_id
            }]

            # 7. 在文本中添加一阶编码标记 (例如 [2] [A01])
            # 即使没有选中内容，我们也要尝试在文本中找到这句话并加上标记
            # 优先使用 text_display 的选择
            cursor = self.text_display.textCursor()
            if cursor.hasSelection():
                selected_text = cursor.selectedText().strip()
                # 确保选中的文本大概匹配我们的内容，防止误操作
                if selected_text in clean_content or clean_content in selected_text:
                    self.add_code_marker_to_text(selected_text, code_id)
            else:
                # 如果没有选中，尝试在文档中搜索并添加标记
                # 只有当关联编号存在时（tmng_number），我们可以更精确地定位 [N]
                if str(tmng_number).isdigit():
                    # 搜寻 [N]
                    doc = self.text_display.document()
                    # 使用 cursor 查找
                    search_cursor = self.text_display.textCursor()
                    search_cursor.movePosition(QTextCursor.Start)

                    # 查找形如 "[N]" 的标记
                    target_marker = f"[{tmng_number}]"
                    found_cursor = doc.find(target_marker, search_cursor)

                    if not found_cursor.isNull():
                        # 找到了 [N]，检查后面是否已经有 [code_id]
                        check_cursor = QTextCursor(found_cursor)
                        check_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(f" [{code_id}]"))
                        if check_cursor.selectedText() != f" [{code_id}]":
                            # 插入标记
                            found_cursor.movePosition(QTextCursor.Right)  # 移动到 [N] 后面
                            found_cursor.insertText(f" [{code_id}]")
                            logger.info(f"在 {target_marker} 后自动添加了一阶编码标记 [{code_id}]")

            # 添加到树根部（未分类状态）
            item = QTreeWidgetItem(self.coding_tree)
            # 在内容前加上编号
            item.setText(0, f"{code_id}: {clean_content}")
            item.setText(1, "一阶编码")
            item.setText(2, "1")
            item.setText(3, "1")  # 文件来源数
            item.setText(4, "1")  # 句子来源数

            # 设置关联编号
            item.setText(5, str(tmng_number))  # 关联编号

            item.setData(0, Qt.UserRole, {
                "level": 1,
                "content": clean_content,
                "numbered_content": f"{code_id}: {clean_content}",  # 带编号的内容
                "code_id": code_id,
                "sentence_details": sentence_details,  # 记录句子来源信息
                "classified": False
            })

            # 清空输入框
            self.first_content_edit.clear()

            # 更新结构化编码数据
            print("DEBUG: 添加编码后更新数据结构")
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
                            number_match = re.search(r'\[(\d+)\]', sentence.strip())
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
                self.statusBar().showMessage(
                    f"通过拖放将{len(sentences)}个句子关联到一阶编码，关联编号: {', '.join(associated_code_ids)}") if hasattr(self,
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

    def restore_code_counter(self, last_code_id):
        """恢复编码计数器，确保下次生成的编码ID能够接着上次的编号继续"""
        try:
            if last_code_id and isinstance(last_code_id, str):
                # 提取字母和数字部分 (如A01 -> A, 01)
                import re
                match = re.match(r'([A-Z])(\d+)', last_code_id)
                if match:
                    self.last_code_letter = match.group(1)
                    self.last_code_number = int(match.group(2))
                    logger.info(f"已恢复编码计数器: 字母={self.last_code_letter}, 编号={self.last_code_number}")

                    # 在状态栏显示恢复信息
                    if hasattr(self, 'show_message'):
                        self.show_message(f"已恢复编码进度，下个编码将是: {self.last_code_letter}{self.last_code_number + 1:02d}")

        except Exception as e:
            logger.error(f"恢复编码计数器失败: {e}")

    def restore_file_selection(self, current_file):
        """恢复文件选择状态"""
        try:
            if current_file and hasattr(self, 'file_list'):
                for i in range(self.file_list.count()):
                    item = self.file_list.item(i)
                    if item.data(Qt.UserRole) == current_file:
                        self.file_list.setCurrentItem(item)
                        logger.info(f"已恢复文件选择: {item.text()}")
                        break

        except Exception as e:
            logger.error(f"恢复文件选择失败: {e}")

    def restore_text_position(self, current_position):
        """恢复文本光标位置"""
        try:
            if current_position and hasattr(self, 'text_display'):
                cursor = self.text_display.textCursor()
                cursor.setPosition(current_position)
                self.text_display.setTextCursor(cursor)
                self.text_display.ensureCursorVisible()
                logger.info(f"已恢复文本位置: {current_position}")
        except Exception as e:
            logger.error(f"恢复文本位置失败: {e}")

    def show_message(self, message, timeout=3000):
        """显示状态消息"""
        try:
            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage(message, timeout)
            else:
                # 如果没有状态栏，可以在此处添加其他消息显示方式
                logger.info(f"状态消息: {message}")
        except Exception as e:
            logger.error(f"显示消息失败: {e}")

    def get_files_with_coding_marks(self):
        """获取所有文件的编码标记状态"""
        try:
            files_with_marks = {}

            for file_path, file_data in self.loaded_files.items():
                if 'content_with_marks' in file_data:
                    files_with_marks[file_path] = file_data['content_with_marks']

            logger.info(f"已获取 {len(files_with_marks)} 个文件的编码标记状态")
            return files_with_marks

        except Exception as e:
            logger.error(f"获取文件编码标记状态失败: {e}")
            return {}

    def restore_files_with_coding_marks(self, files_with_marks):
        """恢复所有文件的编码标记状态"""
        try:
            if not files_with_marks:
                logger.info("没有文件编码标记需要恢复")
                return

            restored_count = 0
            missing_files = []

            for file_path, content_with_marks in files_with_marks.items():
                if file_path in self.loaded_files:
                    self.loaded_files[file_path]['content_with_marks'] = content_with_marks
                    restored_count += 1

                    # 统计编码标记数量
                    import re
                    mark_count = len(re.findall(r'\[A\d+\]', content_with_marks))
                    logger.info(f"已恢复文件编码标记: {os.path.basename(file_path)} ({mark_count}个标记)")
                else:
                    missing_files.append(file_path)

            if missing_files:
                logger.warning(f"以下文件未找到，无法恢复编码标记: {[os.path.basename(f) for f in missing_files]}")

            logger.info(f"已恢复 {restored_count} 个文件的编码标记状态，跳过 {len(missing_files)} 个缺失文件")

        except Exception as e:
            logger.error(f"恢复文件编码标记状态失败: {e}")

    def refresh_current_file_display(self):
        """刷新当前文件的显示，确保显示最新的编码标记状态"""
        try:
            current_item = self.file_list.currentItem()
            if not current_item:
                return

            file_path = current_item.data(Qt.UserRole)
            if file_path not in self.loaded_files:
                return

            file_data = self.loaded_files[file_path]

            # 获取最新的显示内容（优先使用带编码标记的版本）
            display_content = self.get_file_display_content(file_data, file_path)

            # 更新文本显示
            if display_content and display_content != "文件内容为空":
                self.text_display.setPlainText(display_content)
                self.select_sentence_btn.setEnabled(True)
                logger.info(f"已刷新文件显示: {os.path.basename(file_path)}")
            else:
                self.text_display.setPlainText("文件内容为空")
                self.select_sentence_btn.setEnabled(False)

        except Exception as e:
            logger.error(f"刷新文件显示失败: {e}")

    def refresh_all_files_display(self):
        """刷新所有文件的显示，确保编码标记状态正确同步"""
        try:
            # 记录当前选中的文件
            current_item = self.file_list.currentItem()
            current_file_path = None
            if current_item:
                current_file_path = current_item.data(Qt.UserRole)

            # 为每个文件确保编码标记状态同步到file_data中
            files_refreshed = 0
            for i in range(self.file_list.count()):
                item = self.file_list.item(i)
                file_path = item.data(Qt.UserRole)

                if file_path in self.loaded_files:
                    # 确保文件数据中的 content_with_marks 是最新的
                    file_data = self.loaded_files[file_path]
                    if 'content_with_marks' in file_data:
                        # 如果这是当前显示的文件，更新显示内容
                        if file_path == current_file_path:
                            display_content = file_data['content_with_marks']
                            self.text_display.setPlainText(display_content)
                            if display_content and display_content != "文件内容为空":
                                self.select_sentence_btn.setEnabled(True)
                            else:
                                self.select_sentence_btn.setEnabled(False)
                            logger.info(f"已刷新当前文件的编码标记显示: {os.path.basename(file_path)}")
                        files_refreshed += 1

            logger.info(f"已刷新 {files_refreshed} 个文件的编码标记状态")

            # 如果没有当前选中文件，选择第一个有编码标记的文件
            if not current_item and files_refreshed > 0:
                for i in range(self.file_list.count()):
                    item = self.file_list.item(i)
                    file_path = item.data(Qt.UserRole)

                    if file_path in self.loaded_files and 'content_with_marks' in self.loaded_files[file_path]:
                        self.file_list.setCurrentItem(item)
                        self.refresh_current_file_display()
                        logger.info(f"自动选择了有编码标记的文件: {os.path.basename(file_path)}")
                        break

        except Exception as e:
            logger.error(f"刷新所有文件显示失败: {e}")