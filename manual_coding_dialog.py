import os
import json
import re
from datetime import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QGroupBox, QTextEdit, QLineEdit, QPushButton, QWidget,
                             QListWidget, QListWidgetItem, QLabel, QMessageBox,
                             QTreeWidget, QTreeWidgetItem, QSplitter, QComboBox,
                             QInputDialog, QDialogButtonBox, QApplication, QMenu, QAction,
                             QCheckBox)
from PyQt5.QtCore import Qt, QMimeData, QTimer, QEvent, QRegularExpression
from PyQt5.QtGui import QTextDocument, QTextCursor
from PyQt5.QtGui import QFont, QColor, QDrag
import logging
from path_manager import PathManager
from code_library import CodeLibrary

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

    def __init__(self, parent=None, loaded_files=None, existing_codes=None, auto_coding_cache=None,
                 code_markers_map=None):
        super().__init__(parent)
        self.parent_window = parent  # 保存父窗口引用，用于访问data_processor
        self.loaded_files = loaded_files or {}
        self.existing_codes = existing_codes or {}
        self.auto_coding_cache = auto_coding_cache or {}
        self.code_markers_map = code_markers_map or {}
        self.current_codes = {}
        # 未分类的一阶编码临时存储
        self.unclassified_first_codes = []
        self.init_ui()
        self.load_existing_codes()

    def init_ui(self):
        self.setWindowTitle("手动编码工具 - 全屏版")
        self.setModal(False)  # 改为非模态，允许全屏显示

        # 添加系统标题栏缩小（最小化）按钮和最大化/还原按钮
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)

        # 设置为全屏或最大化
        screen_geometry = QApplication.desktop().availableGeometry()
        self.setGeometry(screen_geometry)
        self._is_half_screen = False  # 当前是否处于半屏状态
        self._handling_state_change = True  # 保护初始化时的 showMaximized 不被拦截
        self.showMaximized()
        self._handling_state_change = False

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

        def changeEvent(self, event):
            """拦截窗口状态变化：还原按鈕→半屏，最大化按鈕→全屏"""
            from PyQt5.QtCore import QEvent, QTimer
            if event.type() == QEvent.WindowStateChange:
                if not getattr(self, '_handling_state_change', False):
                    old_state = event.oldState()
                    new_state = self.windowState()
                    # 全屏 → 还原（点击还原按鈕）：改为半屏
                    if (old_state & Qt.WindowMaximized) and not (new_state & Qt.WindowMaximized) \
                            and not (new_state & Qt.WindowMinimized):
                        if not getattr(self, '_is_half_screen', False):
                            QTimer.singleShot(0, self._apply_half_screen)
                    # 半屏 → 最大化（点击最大化按鈕）：恢复全屏，清除标记
                    elif (new_state & Qt.WindowMaximized) and getattr(self, '_is_half_screen', False):
                        self._is_half_screen = False
            super().changeEvent(event)

        def _apply_half_screen(self):
            """将窗口设置为屏幕一半大小并居中"""
            self._handling_state_change = True
            screen = QApplication.desktop().availableGeometry()
            half_w = screen.width() // 2
            half_h = screen.height() // 2
            self.setGeometry(
                screen.x() + half_w // 2,
                screen.y() + half_h // 2,
                half_w,
                half_h
            )
            self._is_half_screen = True
            self._handling_state_change = False

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

        # 搜索框
        search_layout = QHBoxLayout()
        self.search_line_edit = QLineEdit()
        self.search_line_edit.setPlaceholderText("搜索一阶编码...")
        self.search_line_edit.setMinimumWidth(200)

        # 放大镜图标按钮
        search_button = QPushButton("🔍")
        search_button.setStyleSheet("QPushButton { border: none; padding: 0 5px; }")

        search_layout.addWidget(self.search_line_edit)
        search_layout.addWidget(search_button)
        structure_layout.addLayout(search_layout)

        # 连接搜索信号
        self.search_line_edit.returnPressed.connect(self.perform_search)
        search_button.clicked.connect(self.perform_search)

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
            # 1. 优先使用缓存中的自动编码内容
            if file_path in self.auto_coding_cache:
                cached_content = self.auto_coding_cache[file_path]
                if cached_content and cached_content != "文件内容为空":
                    logger.info(f"使用缓存中的自动编码内容: {os.path.basename(file_path)}")
                    return cached_content

            # 2. 优先使用带编码标记的内容
            content_with_marks = file_data.get('content_with_marks', '')
            if content_with_marks:
                logger.info(f"使用带编码标记的内容: {os.path.basename(file_path)}")
                return content_with_marks

            # 3. 使用已有的编号内容
            numbered_content = file_data.get('numbered_content', '')
            if numbered_content:
                logger.info(f"使用已有的编号内容: {os.path.basename(file_path)}")
                return numbered_content

            # 4. 获取原始内容并进行编号
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

            # 5. 内容为空的情况
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
                return

        except Exception as e:
            logger.error(f"选择句子失败: {e}")
            QMessageBox.critical(self, "错误", f"选择句子失败: {str(e)}")

    def add_code_marker_to_selection(self, cursor, code_id):
        """在选中的文本位置添加编码标记（只保留一阶编码对应的一阶编号，其余去除）"""
        try:
            # 获取选中文本的位置
            selection_start = cursor.selectionStart()
            selection_end = cursor.selectionEnd()
            selected_text = cursor.selectedText()

            # 清理选中文本中的一阶编码标记
            import re
            clean_text = re.sub(r'\s*\[A\d+\]', '', selected_text).strip()

            # 检查选中的文本后面是否已经有一阶编码标记
            current_text = self.text_display.toPlainText()
            check_pos = selection_end

            # 查找并移除后面的一阶编码标记
            marker_pos = current_text.find(" [A", check_pos)
            if marker_pos != -1 and marker_pos < check_pos + 100:  # 限制搜索范围，避免影响其他内容
                # 检查是否是完整的一阶编码标记
                marker_end = current_text.find("]", marker_pos)
                if marker_end != -1:
                    marker = current_text[marker_pos:marker_end + 1]
                    if re.match(r'\s*\[A\d+\]', marker):
                        # 移除一阶编码标记
                        remove_cursor = QTextCursor(cursor)
                        remove_cursor.setPosition(marker_pos)
                        remove_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(marker))
                        remove_cursor.removeSelectedText()
                        logger.info(f"已移除选中文本后的一阶编码标记: {marker}")

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
            # 尝试多种标记格式
            patterns = [
                f"[{code_id}]",  # [A13]
                f" [{code_id}]",  # [A13]
                f"[{code_id}]",  # [A13]
            ]

            mark_cursor = None
            for pattern in patterns:
                mark_cursor = document.find(pattern)
                if not mark_cursor.isNull():
                    break

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

            # 如果找不到标记，尝试基于内容搜索
            return self.search_by_content_fallback(code_id)

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

    def search_by_content_fallback(self, code_id):
        """基于内容的回退搜索"""
        try:
            # 获取编码对应的内容
            content = self.get_content_by_code_id(code_id)
            if not content:
                return False

            # 清理内容
            import re
            clean_content = re.sub(r'\s*\[A\d+\]', '', content)
            clean_content = re.sub(r'\s*\[\d+\]', '', clean_content).strip()

            # 尝试在文本中查找
            document = self.text_display.document()
            search_cursor = self.text_display.textCursor()
            search_cursor.movePosition(search_cursor.Start)

            # 使用宽松匹配
            if len(clean_content) > 10:
                # 尝试查找内容的一部分
                for i in range(0, len(clean_content) - 10, 5):
                    search_part = clean_content[i:i + 30]
                    found_cursor = document.find(search_part, search_cursor)
                    if not found_cursor.isNull():
                        # 高亮找到的部分
                        selection = QTextEdit.ExtraSelection()
                        selection.cursor = found_cursor
                        selection.format.setBackground(QColor(173, 216, 230))
                        selection.format.setForeground(QColor(0, 0, 139))
                        self.text_display.setExtraSelections([selection])

                        # 滚动到该位置
                        view_cursor = QTextCursor(found_cursor)
                        view_cursor.setPosition(found_cursor.selectionStart())
                        self.text_display.setTextCursor(view_cursor)
                        self.text_display.ensureCursorVisible()

                        return True

            return False

        except Exception as e:
            logger.error(f"内容回退搜索失败: {e}")
            return False

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

    def generate_second_code_id(self, third_letter="B", parent_node=None):
        """生成二阶编码ID：B01, B02, B03...（B开头，数字递增）

        Args:
            third_letter: 编码前缀，默认为"B"
            parent_node: 父节点（三阶编码），如果提供，则只统计该父节点下的二阶编码
        """
        # 统计已存在的二阶编码ID
        existing_second_numbers = []

        if parent_node:
            # 只统计指定父节点下的二阶编码
            for j in range(parent_node.childCount()):
                second_item = parent_node.child(j)
                second_data = second_item.data(0, Qt.UserRole)
                if second_data and second_data.get("level") == 2:
                    second_name = second_item.text(0)
                    # 检查二阶名称是否以B开头并有数字
                    if second_name.startswith('B'):
                        # 提取两位数字部分
                        import re
                        match = re.search(r'\d{2}', second_name)
                        if match:
                            existing_second_numbers.append(int(match.group()))
        else:
            # 统计所有已存在的二阶编码ID
            for i in range(self.coding_tree.topLevelItemCount()):
                top_item = self.coding_tree.topLevelItem(i)
                # 检查是否是三阶编码节点
                top_data = top_item.data(0, Qt.UserRole)
                if top_data and top_data.get("level") == 3:
                    # 统计该三阶编码下的二阶编码
                    for j in range(top_item.childCount()):
                        second_item = top_item.child(j)
                        second_data = second_item.data(0, Qt.UserRole)
                        if second_data and second_data.get("level") == 2:
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

    def reorder_unclassified_second_codes(self):
        """对未分类的二阶编码（没有父节点的二阶编码）进行重新编序，从B01开始依次递增编号"""
        try:
            # 收集所有未分类的二阶编码
            unclassified_second_items = []
            for i in range(self.coding_tree.topLevelItemCount()):
                top_item = self.coding_tree.topLevelItem(i)
                top_data = top_item.data(0, Qt.UserRole)
                if top_data and top_data.get("level") == 2:
                    unclassified_second_items.append(top_item)

            # 为未分类的二阶编码重新编号
            for i, item in enumerate(unclassified_second_items):
                # 生成新的二阶编码ID
                new_code_id = f"B{i + 1:02d}"

                # 更新二阶编码的显示名称
                item_data = item.data(0, Qt.UserRole)
                clean_name = item_data.get("name", "")
                new_numbered_name = f"{new_code_id} {clean_name}"
                item.setText(0, new_numbered_name)
                item.setText(5, new_code_id)  # 更新关联编号

                # 更新二阶编码的数据
                item_data["code_id"] = new_code_id
                item.setData(0, Qt.UserRole, item_data)

            logger.info(f"已为 {len(unclassified_second_items)} 个未分类二阶编码重新编序")
        except Exception as e:
            logger.error(f"重新编序未分类二阶编码失败: {e}")
            import traceback
            traceback.print_exc()

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

                # 生成二阶编码ID（使用B开头），传递父节点参数
                code_id = self.generate_second_code_id(parent_node=current_item)
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

            # 解析内容中的编号和对应的句子文本
            import re
            number_matches = re.findall(r'\[(\d+)\]', clean_content)

            sentence_id = code_id
            detail_text = clean_content

            if number_matches:
                tmng_number = number_matches[-1]
                sentence_id = tmng_number
                try:
                    pattern = r'(?:^|\]\s*)([^\[\]]*?\[' + re.escape(tmng_number) + r'\])'
                    match = re.search(pattern, clean_content, re.DOTALL)
                    if match:
                        detail_text = match.group(1).strip()
                except Exception as e:
                    logger.error(f"提取句子文本失败: {e}")
            else:
                tmng_number = code_id
                text_content = self.text_display.toPlainText()
                if text_content:
                    found_number = self.find_sentence_number_from_text(clean_content, text_content)
                    if found_number:
                        tmng_number = found_number
                        sentence_id = tmng_number

            # 尝试获取当前选中的文件路径
            current_file_path = ""
            current_filename = ""
            if hasattr(self, 'file_list') and self.file_list.currentItem():
                current_file_path = self.file_list.currentItem().data(Qt.UserRole)
                current_filename = os.path.basename(current_file_path)

            sentence_details = [{
                "text": detail_text,
                "code_id": sentence_id,
                "file_path": current_file_path,
                "filename": current_filename,
                "sentence_id": sentence_id
            }]

            # 7. 在文本中添加一阶编码标记
            cursor = self.text_display.textCursor()
            if cursor.hasSelection():
                selected_text = cursor.selectedText().strip()
                if selected_text in clean_content or clean_content in selected_text:
                    self.add_code_marker_to_text(selected_text, code_id)
            else:
                if str(tmng_number).isdigit():
                    doc = self.text_display.document()
                    search_cursor = self.text_display.textCursor()
                    search_cursor.movePosition(QTextCursor.Start)
                    target_marker = f"[{tmng_number}]"
                    found_cursor = doc.find(target_marker, search_cursor)

                    if not found_cursor.isNull():
                        current_text = self.text_display.toPlainText()
                        found_pos = found_cursor.position() + len(target_marker)

                        marker_pos = current_text.find(" [A", found_pos)
                        if marker_pos != -1 and marker_pos < found_pos + 100:
                            marker_end = current_text.find("]", marker_pos)
                            if marker_end != -1:
                                marker = current_text[marker_pos:marker_end + 1]
                                if re.match(r'\s*\[A\d+\]', marker):
                                    remove_cursor = QTextCursor(found_cursor)
                                    remove_cursor.setPosition(marker_pos)
                                    remove_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(marker))
                                    remove_cursor.removeSelectedText()

                        check_cursor = QTextCursor(found_cursor)
                        check_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(f" [{code_id}]"))
                        if check_cursor.selectedText() != f" [{code_id}]":
                            found_cursor.movePosition(QTextCursor.Right)
                            found_cursor.insertText(f" [{code_id}]")

            # 创建一阶节点
            first_item = QTreeWidgetItem(current_item)
            first_item.setText(0, numbered_content)
            first_item.setText(1, "一阶编码")
            first_item.setText(2, "1")
            first_item.setText(3, "1")  # 文件来源数，未合并前为1
            first_item.setText(4, "1")  # 句子来源数，未合并前为1
            first_item.setText(5, str(tmng_number))  # 关联编号

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
                "sentence_details": sentence_details,  # 初始化句子详情列表
                "sentence_count": 1
            })

            current_item.setExpanded(True)
            current_item.setText(2, str(current_item.childCount()))

            # 更新父节点计数
            if parent_item and parent_item.data(0, Qt.UserRole) and parent_item.data(0, Qt.UserRole).get("level") == 3:
                parent_item.setText(2, str(parent_item.childCount()))

            # 更新父节点的统计信息（包括句子来源数）
            self.update_statistics_for_item(current_item)

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

    def update_statistics_for_item(self, item):
        """更新节点及其所有祖先的统计信息（数量、句子来源等）"""
        if not item:
            return

        item_data = item.data(0, Qt.UserRole)
        if not item_data:
            return

        try:
            level = item_data.get("level")

            # 统计子节点数据
            child_count = item.childCount()
            sentence_count = 0

            if level == 2:  # 二阶编码
                # 数量 = 一阶子节点数
                item.setText(2, str(child_count))

                # 句子来源 = 所有子节点的句子来源之和
                for i in range(child_count):
                    child = item.child(i)
                    try:
                        s_count = int(child.text(4))
                    except:
                        s_count = 0
                    sentence_count += s_count
                item.setText(4, str(sentence_count))

                # 递归更新父节点（三阶）
                if item.parent():
                    self.update_statistics_for_item(item.parent())

            elif level == 3:  # 三阶编码
                # 数量 = 二阶子节点数
                item.setText(2, str(child_count))

                # 句子来源 = 所有二阶子节点的句子来源之和
                for i in range(child_count):
                    child = item.child(i)
                    try:
                        s_count = int(child.text(4))
                    except:
                        s_count = 0
                    sentence_count += s_count
                item.setText(4, str(sentence_count))
        except Exception as e:
            logger.error(f"更新统计信息失败: {e}")

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
                second_item.setText(4, "0")  # 句子来源数（稍后更新）
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

                # 更新统计信息（包括句子来源数）
                self.update_statistics_for_item(second_item)

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

                # 为新添加的二阶编码重新编号，确保每个三阶编码下的二阶编码都从 B01 开始递增
                for i, item in enumerate(second_level_items):
                    # 生成新的二阶编码ID
                    new_code_id = f"B{i + 1:02d}"

                    # 更新二阶编码的显示名称
                    item_data = item.data(0, Qt.UserRole)
                    clean_name = item_data.get("name", "")
                    new_numbered_name = f"{new_code_id} {clean_name}"
                    item.setText(0, new_numbered_name)
                    item.setText(5, new_code_id)  # 更新关联编号

                    # 更新二阶编码的数据
                    item_data["code_id"] = new_code_id
                    item.setData(0, Qt.UserRole, item_data)

                # 更新统计信息
                self.update_statistics_for_item(third_item)

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

    def move_first_to_new_parent_second(self):
        """修改一阶编码的父节点（二阶），允许移动到另一个二阶编码下"""
        try:
            selected_items = self.coding_tree.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "提示", "请先选中一个一阶编码")
                return

            # 只处理第一个选中的一阶编码（已分类或未分类均可）
            first_item = None
            for item in selected_items:
                item_data = item.data(0, Qt.UserRole)
                if item_data and item_data.get("level") == 1:
                    first_item = item
                    break

            if not first_item:
                QMessageBox.warning(self, "警告", "请选中一个一阶编码")
                return

            old_parent = first_item.parent()

            # 收集所有二阶编码（带三阶父节点信息）
            # 结构: [(third_item_or_None, [second_item, ...]), ...]
            third_second_list = []
            root_count = self.coding_tree.topLevelItemCount()
            orphan_seconds = []  # 没有三阶父节点的二阶编码
            for i in range(root_count):
                top = self.coding_tree.topLevelItem(i)
                top_data = top.data(0, Qt.UserRole)
                if not top_data:
                    continue
                if top_data.get("level") == 3:
                    children = []
                    for j in range(top.childCount()):
                        child = top.child(j)
                        child_data = child.data(0, Qt.UserRole)
                        if child_data and child_data.get("level") == 2:
                            children.append(child)
                    if children:
                        third_second_list.append((top, children))
                elif top_data.get("level") == 2:
                    # 顶层二阶视为“未分类二阶”
                    orphan_seconds.append(top)
            if orphan_seconds:
                third_second_list.append((None, orphan_seconds))

            if not third_second_list:
                QMessageBox.information(self, "提示", "当前没有可选的二阶编码")
                return

            # 弹出选择对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("修改一阶对应父节点(二阶)")
            dialog.resize(500, 450)
            layout = QVBoxLayout(dialog)

            label = QLabel(f"为一阶编码「{first_item.text(0)}」选择新的二阶父节点：\n（点击二阶编码行进行选择）")
            label.setWordWrap(True)
            layout.addWidget(label)

            from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem as _TWI
            tree = QTreeWidget()
            tree.setColumnCount(1)
            tree.setHeaderHidden(True)
            tree.setSelectionMode(QTreeWidget.SingleSelection)

            item_to_second_map = {}  # tree item → original coding_tree second-level item

            for third_node, second_list in third_second_list:
                if third_node is None:
                    parent_node = tree.invisibleRootItem()
                else:
                    t_item = _TWI(tree)
                    t_item.setText(0, third_node.text(0))
                    t_item.setFlags(t_item.flags() & ~Qt.ItemIsSelectable)
                    font = t_item.font(0)
                    font.setBold(True)
                    t_item.setFont(0, font)
                    parent_node = t_item
                    t_item.setExpanded(True)

                for sec in second_list:
                    if sec is old_parent:
                        continue  # 跳过当前父节点
                    s_item = _TWI(parent_node)
                    s_item.setText(0, "    " + sec.text(0))
                    item_to_second_map[id(s_item)] = sec

            tree.expandAll()
            layout.addWidget(tree)

            selected_second = [None]  # 用列表包装，方便闭包写入

            def on_selection_changed():
                sel = tree.selectedItems()
                if sel and id(sel[0]) in item_to_second_map:
                    selected_second[0] = item_to_second_map[id(sel[0])]

            tree.itemSelectionChanged.connect(on_selection_changed)

            btn_layout = QHBoxLayout()
            ok_btn = QPushButton("选择")
            cancel_btn = QPushButton("取消")
            btn_layout.addStretch()
            btn_layout.addWidget(ok_btn)
            btn_layout.addWidget(cancel_btn)
            layout.addLayout(btn_layout)

            def on_ok():
                if selected_second[0] is None:
                    QMessageBox.warning(dialog, "提示", "请先点击一个二阶编码")
                    return

                new_parent = selected_second[0]

                # 从旧父节点移除（如果本来就是未分类一阶，old_parent 可能为 None）
                if old_parent is not None:
                    old_parent.removeChild(first_item)
                else:
                    # 顶层未分类一阶：从顶层列表中删除
                    index = self.coding_tree.indexOfTopLevelItem(first_item)
                    if index >= 0:
                        self.coding_tree.takeTopLevelItem(index)

                # 添加到新父节点
                new_parent.addChild(first_item)

                # 更新一阶编码数据中的parent信息
                fd = first_item.data(0, Qt.UserRole)
                new_parent_data = new_parent.data(0, Qt.UserRole)
                fd["category"] = new_parent_data.get("name", new_parent.text(0))

                # 更新 core_category（三阶）
                grandparent = new_parent.parent()
                if grandparent:
                    gp_data = grandparent.data(0, Qt.UserRole)
                    if gp_data and gp_data.get("level") == 3:
                        import re as _re
                        parts = grandparent.text(0).split(' ', 1)
                        fd["core_category"] = parts[1] if len(parts) > 1 else grandparent.text(0)
                    else:
                        fd.pop("core_category", None)
                else:
                    fd.pop("core_category", None)

                first_item.setData(0, Qt.UserRole, fd)

                # 更新统计并全局重新编号
                if old_parent is not None:
                    self.update_statistics_for_item(old_parent)
                    old_parent_name = old_parent.text(0)
                else:
                    old_parent_name = "未分类"
                self.update_statistics_for_item(new_parent)
                self.renumber_all_codes()

                logger.info(f"已将一阶编码从「{old_parent_name}」移动到「{new_parent.text(0)}」")
                QMessageBox.information(self, "成功",
                                        f"已将一阶编码移动到：{new_parent.text(0)}")
                dialog.accept()

            ok_btn.clicked.connect(on_ok)
            cancel_btn.clicked.connect(dialog.reject)
            dialog.exec_()

        except Exception as e:
            logger.error(f"修改一阶对应父节点失败: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"操作失败:\n{str(e)}")

    def move_second_to_new_parent_third(self):
        """修改二阶编码的父节点（三阶），允许移动到另一个三阶编码下"""
        try:
            selected_items = self.coding_tree.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "提示", "请先选中一个二阶编码")
                return

            # 只处理第一个符合条件的二阶编码（已分类或未分类均可）
            second_item = None
            for item in selected_items:
                item_data = item.data(0, Qt.UserRole)
                if item_data and item_data.get("level") == 2:
                    second_item = item
                    break

            if not second_item:
                QMessageBox.warning(self, "警告", "请选中一个二阶编码")
                return

            old_parent = second_item.parent()

            # 收集所有三阶编码
            third_nodes = []
            root_count = self.coding_tree.topLevelItemCount()
            for i in range(root_count):
                top = self.coding_tree.topLevelItem(i)
                top_data = top.data(0, Qt.UserRole)
                if top_data and top_data.get("level") == 3 and top is not old_parent:
                    third_nodes.append(top)

            if not third_nodes:
                QMessageBox.information(self, "提示", "当前没有其他可选的三阶编码")
                return

            # 弹出选择对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("修改二阶对应父节点(三阶)")
            dialog.resize(500, 400)
            layout = QVBoxLayout(dialog)

            label = QLabel(f"为二阶编码「{second_item.text(0)}」选择新的三阶父节点：\n（点击三阶编码行进行选择）")
            label.setWordWrap(True)
            layout.addWidget(label)

            from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem as _TWI2
            tree = QTreeWidget()
            tree.setColumnCount(1)
            tree.setHeaderHidden(True)
            tree.setSelectionMode(QTreeWidget.SingleSelection)

            item_to_third_map = {}

            for third_node in third_nodes:
                t_item = _TWI2(tree)
                t_item.setText(0, third_node.text(0))
                item_to_third_map[id(t_item)] = third_node

            layout.addWidget(tree)

            selected_third = [None]

            def on_selection_changed():
                sel = tree.selectedItems()
                if sel and id(sel[0]) in item_to_third_map:
                    selected_third[0] = item_to_third_map[id(sel[0])]

            tree.itemSelectionChanged.connect(on_selection_changed)

            btn_layout = QHBoxLayout()
            ok_btn = QPushButton("选择")
            cancel_btn = QPushButton("取消")
            btn_layout.addStretch()
            btn_layout.addWidget(ok_btn)
            btn_layout.addWidget(cancel_btn)
            layout.addLayout(btn_layout)

            def on_ok():
                if selected_third[0] is None:
                    QMessageBox.warning(dialog, "提示", "请先点击一个三阶编码")
                    return

                new_parent = selected_third[0]
                new_parent_data = new_parent.data(0, Qt.UserRole)
                import re as _re
                parts = new_parent.text(0).split(' ', 1)
                new_third_name = parts[1] if len(parts) > 1 else new_parent.text(0)

                # 从旧父节点移除（未分类二阶时 old_parent 可能为 None）
                if old_parent is not None:
                    old_parent.removeChild(second_item)
                else:
                    index = self.coding_tree.indexOfTopLevelItem(second_item)
                    if index >= 0:
                        self.coding_tree.takeTopLevelItem(index)

                # 添加到新三阶下
                new_parent.addChild(second_item)

                # 更新二阶编码数据
                sd = second_item.data(0, Qt.UserRole)
                sd["parent"] = new_third_name
                second_item.setData(0, Qt.UserRole, sd)

                # 更新所有子一阶的 core_category
                for i in range(second_item.childCount()):
                    fi = second_item.child(i)
                    fd = fi.data(0, Qt.UserRole)
                    if fd:
                        fd["core_category"] = new_third_name
                        fi.setData(0, Qt.UserRole, fd)

                new_parent.setExpanded(True)

                # 更新统计并全局重新编号
                if old_parent is not None:
                    self.update_statistics_for_item(old_parent)
                    old_parent_name = old_parent.text(0)
                else:
                    old_parent_name = "未分类"
                self.update_statistics_for_item(new_parent)
                self.renumber_all_codes()

                logger.info(f"已将二阶编码从「{old_parent_name}」移动到「{new_parent.text(0)}」")
                QMessageBox.information(self, "成功",
                                        f"已将二阶编码移动到：{new_parent.text(0)}")
                dialog.accept()

            ok_btn.clicked.connect(on_ok)
            cancel_btn.clicked.connect(dialog.reject)
            dialog.exec_()

        except Exception as e:
            logger.error(f"修改二阶对应父节点失败: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"操作失败:\n{str(e)}")

    def renumber_all_codes(self):
        """对整棵编码树所有节点进行全局重新顺序编号：
        三阶 C01/C02...（顶层顺序），
        二阶 B01/B02...（各自三阶父节点内顺序），
        一阶 A01/A02...（全树从上到下全局顺序）"""
        try:
            import re

            def strip_prefix(text):
                """剥离编码前缀（如 A01: / B02  / C03 等），返回纯名称"""
                m = re.match(r'^[A-Z]\d+(?:[:：]\s*|\s+)', text)
                return text[m.end():] if m else text

            first_counter = [0]  # 全局一阶编号计数器（列表便于闭包修改）

            def assign_first(item, idata):
                first_counter[0] += 1
                new_id = f"A{first_counter[0]:02d}"
                pure = strip_prefix(item.text(0))
                item.setText(0, f"{new_id} {pure}")
                idata["code_id"] = new_id
                idata["numbered_content"] = f"{new_id} {pure}"
                item.setData(0, Qt.UserRole, idata)

            def process_second(sec_item, b_index):
                """给二阶节点编号并处理其子一阶"""
                new_id = f"B{b_index:02d}"
                pure = strip_prefix(sec_item.text(0))
                sec_item.setText(0, f"{new_id} {pure}")
                sec_item.setText(5, new_id)
                sd = sec_item.data(0, Qt.UserRole)
                if sd:
                    sd["code_id"] = new_id
                    if not sd.get("name"):
                        sd["name"] = pure
                    sec_item.setData(0, Qt.UserRole, sd)
                for k in range(sec_item.childCount()):
                    fi = sec_item.child(k)
                    fd = fi.data(0, Qt.UserRole)
                    if fd and fd.get("level") == 1:
                        assign_first(fi, fd)

            third_counter = 0
            for i in range(self.coding_tree.topLevelItemCount()):
                top = self.coding_tree.topLevelItem(i)
                td = top.data(0, Qt.UserRole)
                if not td:
                    continue
                lvl = td.get("level")

                if lvl == 3:
                    third_counter += 1
                    new_id = f"C{third_counter:02d}"
                    pure = strip_prefix(top.text(0))
                    top.setText(0, f"{new_id} {pure}")
                    top.setText(5, new_id)
                    td["code_id"] = new_id
                    if not td.get("name"):
                        td["name"] = pure
                    top.setData(0, Qt.UserRole, td)
                    b_idx = 1
                    for j in range(top.childCount()):
                        sec = top.child(j)
                        sd2 = sec.data(0, Qt.UserRole)
                        if sd2 and sd2.get("level") == 2:
                            process_second(sec, b_idx)
                            b_idx += 1
                        elif sd2 and sd2.get("level") == 1:
                            assign_first(sec, sd2)

                elif lvl == 2:
                    # 顶层二阶（无三阶父节点），只处理子一阶
                    for k in range(top.childCount()):
                        fi = top.child(k)
                        fd = fi.data(0, Qt.UserRole)
                        if fd and fd.get("level") == 1:
                            assign_first(fi, fd)

                elif lvl == 1:
                    # 顶层一阶（未分类）
                    assign_first(top, td)

            # 更新 last_code_number 以便下次新增编码时继续递增
            if first_counter[0] > 0:
                self.last_code_number = first_counter[0]
                self.last_code_letter = "A"

            self.update_structured_codes_from_tree()
            logger.info(f"全局重新编号完成：三阶共 {third_counter} 个，一阶共 {first_counter[0]} 个")

        except Exception as e:
            logger.error(f"renumber_all_codes 失败: {e}")
            import traceback
            traceback.print_exc()

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
        try:
            item_data = item.data(0, Qt.UserRole)
            if not item_data:
                return

            level = item_data.get("level")
            if level != 1:
                return

            content = item_data.get("name", "") or item_data.get("content", "")
            sentence_details = item_data.get("sentence_details", [])

            code_id = ""
            if sentence_details:
                first_detail = sentence_details[0]
                code_id = first_detail.get("code_id", "") or first_detail.get("sentence_id", "")

            if not code_id:
                code_id = item_data.get("code_id", "")

            if not code_id:
                current_item = self.coding_tree.currentItem()
                if current_item:
                    associated_number = current_item.text(5)
                    if associated_number:
                        associated_numbers_list = [num.strip() for num in associated_number.split(',') if num.strip()]
                        if associated_numbers_list:
                            code_id = associated_numbers_list[0]

            self.show_sentence_details_dialog(sentence_details, content, code_id)
        except Exception as e:
            logger.error(f"树节点双击事件处理失败: {e}")

    def on_tree_item_clicked(self, item, column):
        """树形项目点击事件 - 导航到对应句子并高亮"""
        try:
            item_data = item.data(0, Qt.UserRole)
            if not item_data:
                return

            level = item_data.get("level")
            if level == 1:  # 一阶编码
                # 获取内容，由于不同地方可能使用不同的键名，所以同时尝试 name 和 content
                content = item_data.get("name", "") or item_data.get("content", "")
                sentence_details = item_data.get("sentence_details", [])

                # 修复：正确获取一阶编码自身的编号
                code_id = ""
                # 优先从sentence_details第一项获取一阶编码自身的编号
                if sentence_details and len(sentence_details) > 0:
                    first_detail = sentence_details[0]
                    code_id = first_detail.get('code_id', '') or first_detail.get('sentence_id', '')
                    logger.info(f"从sentence_details获取一阶编码自身编号: {code_id}")

                # 如果上述方式失败，使用item_data中的code_id
                if not code_id:
                    code_id = item_data.get("code_id", "")
                    logger.info(f"从item_data获取编号: {code_id}")

                # 如果还是失败，尝试从关联编号中获取第一个
                if not code_id:
                    current_item = self.coding_tree.currentItem()
                    if current_item:
                        associated_number = current_item.text(5)  # 关联编号在第5列
                        if associated_number:
                            associated_numbers_list = [num.strip() for num in associated_number.split(',') if
                                                       num.strip()]
                            if associated_numbers_list:
                                code_id = associated_numbers_list[0]
                                logger.info(f"从关联编号获取第一个作为一阶编码自身编号: {code_id}")

                logger.info(f"最终确定的一阶编码编号: {code_id}")

                # 优先根据sentence_details中的文件信息切换到正确的文件
                if sentence_details and len(sentence_details) > 0:
                    first_detail = sentence_details[0]
                    target_file_path = first_detail.get('file_path')
                    target_filename = first_detail.get('filename')

                    # 定义一个尽量标准化的路径比较函数
                    def normalize_path(path):
                        return os.path.normpath(path).lower() if path else ""

                    if target_file_path:
                        # 检查当前文件是否已经是目标文件
                        current_file_item = self.file_list.currentItem()
                        current_path = current_file_item.data(Qt.UserRole) if current_file_item else ""

                        if normalize_path(current_path) != normalize_path(target_file_path):
                            # 寻找并切换文件
                            found_file = False
                            for i in range(self.file_list.count()):
                                list_item = self.file_list.item(i)
                                item_path = list_item.data(Qt.UserRole)
                                if normalize_path(item_path) == normalize_path(target_file_path):
                                    self.file_list.setCurrentItem(list_item)
                                    self.on_file_selected(list_item)
                                    QApplication.processEvents() # 确保UI刷新
                                    logger.info(f"根据一阶编码文件路径切换到文件: {target_file_path}")
                                    found_file = True
                                    break

                            if not found_file and target_filename:
                                # 如果路径不匹配（可能项目移动过），尝试文件名匹配
                                for i in range(self.file_list.count()):
                                    list_item = self.file_list.item(i)
                                    item_filename = os.path.basename(list_item.data(Qt.UserRole))
                                    if item_filename == target_filename:
                                        self.file_list.setCurrentItem(list_item)
                                        self.on_file_selected(list_item)
                                        QApplication.processEvents()
                                        logger.info(f"根据一阶编码文件名切换到文件: {target_filename}")
                                        break
                
                # 优先使用精确高亮方法（特别是对于手动选择片段的情况）
                success = False

                # 尝试精确高亮
                success = self.highlight_text_by_code_id_precise(code_id)
                if success:
                    logger.info(f"使用精确方式高亮了编码 {code_id}")

                # 如果精确高亮失败，尝试使用内容搜索
                if not success and code_id and content:
                    # 清理内容，移除可能存在的标记
                    import re
                    clean_content = re.sub(r'\s*\[A\d+\]', '', content).strip()
                    clean_content = re.sub(r'\s*\[\d+\]', '', clean_content).strip()

                    if clean_content:
                        # 尝试在所有文件中搜索内容
                        for file_path, file_data in self.loaded_files.items():
                            file_text = file_data.get('numbered_content', '') or file_data.get('content', '')
                            if clean_content in file_text:
                                # 切换到该文件
                                for i in range(self.file_list.count()):
                                    list_item = self.file_list.item(i)
                                    if list_item.data(Qt.UserRole) == file_path:
                                        self.file_list.setCurrentItem(list_item)
                                        QApplication.processEvents()
                                        # 尝试高亮
                                        search_cursor = self.text_display.textCursor()
                                        search_cursor.movePosition(search_cursor.Start)
                                        found_cursor = self.text_document.find(clean_content, search_cursor)
                                        if not found_cursor.isNull():
                                            # 设置高亮
                                            selection = QTextEdit.ExtraSelection()
                                            selection.cursor = found_cursor
                                            selection.format.setBackground(QColor(173, 216, 230))
                                            selection.format.setForeground(QColor(0, 0, 139))
                                            self.text_display.setExtraSelections([selection])

                                            # 定位到匹配位置
                                            new_cursor = self.text_display.textCursor()
                                            new_cursor.setPosition(found_cursor.selectionStart())
                                            self.text_display.setTextCursor(new_cursor)
                                            self.text_display.ensureCursorVisible()

                                            logger.info(f"通过内容搜索成功高亮编码 {code_id}")
                                            self.statusBar().showMessage(f"已高亮编码 {code_id} 的内容") if hasattr(self,
                                                                                                            'statusBar') else None
                                            success = True
                                            break
                                if success:
                                    break

                # 如果仍然失败，尝试使用编码ID直接搜索
                if not success and code_id:
                    success = self.highlight_text_by_code_id(code_id)
                    if success:
                        logger.info(f"使用编码ID搜索成功高亮编码 {code_id}")

                if not success:
                    logger.warning(f"未找到编码 {code_id} 对应的内容")
                    self.statusBar().showMessage(f"未找到编码 {code_id} 对应的内容") if hasattr(self, 'statusBar') else None

        except Exception as e:
            logger.error(f"点击树项目时出错: {e}")
            QMessageBox.warning(self, "错误", f"点击项目时发生错误: {str(e)}")

    def navigate_to_sentence_content(self, sentence_content, sentence_number="", file_path="", filename=""):
        """导航到句子内容并高亮显示 - 增强稳定性版 (支持先切换文件)"""
        try:
            logger.info(
                f"导航请求: Content='{sentence_content[:20] if sentence_content else 'None'}...', Number='{sentence_number}', File='{file_path}', Filename='{filename}'")

            # 策略0：如果提供了文件路径或文件名，优先切换文件
            target_file_path = ""
            if file_path:
                target_file_path = file_path
            elif filename:
                # 尝试根据文件名查找完整路径
                for loaded_fp in self.loaded_files.keys():
                    if os.path.basename(loaded_fp) == filename:
                        target_file_path = loaded_fp
                        break

            if target_file_path:
                current_file = ""
                if hasattr(self, 'file_list') and self.file_list.currentItem():
                    current_file = self.file_list.currentItem().data(Qt.UserRole)

                if current_file != target_file_path and target_file_path in self.loaded_files:
                    logger.info(f"导航前切换文件到: {target_file_path}")
                    # 在文件列表中查找并选中目标文件
                    for i in range(self.file_list.count()):
                        item = self.file_list.item(i)
                        if item.data(Qt.UserRole) == target_file_path:
                            self.file_list.setCurrentItem(item)
                            # 显式触发文件加载
                            self.on_file_selected(item)
                            # 等待文件显示更新
                            QApplication.processEvents()
                            break

            # 安全检查：确保UI组件存在
            if not hasattr(self, 'text_display') or self.text_display is None:
                logger.error("text_display 组件不存在")
                return

            # 获取文档内容 - 使用安全的方式
            try:
                current_text = self.text_display.toPlainText()
            except Exception as e:
                logger.error(f"获取文本内容失败: {e}")
                return

            if not current_text:
                logger.warning("文本内容为空")
                return

            import re
            found_pos = -1
            found_length = 0

            # 清理输入内容，处理可能的 None
            sentence_content = sentence_content if sentence_content else ""
            sentence_number = sentence_number if sentence_number else ""

            # === 策略 1: 精确匹配 (内容 + 编号) ===
            # 如果同时有内容和编号，这是最准确的定位方式
            if sentence_content and sentence_number:
                try:
                    # 查找所有该编号的出现位置
                    pattern = r'\[' + re.escape(sentence_number) + r'\]'
                    matches = list(re.finditer(pattern, current_text))

                    for match in matches:
                        num_start = match.start()
                        # 在编号前搜索内容
                        # 为了容错，搜索范围设为内容长度 + 200字符
                        search_range = len(sentence_content) + 200
                        search_start = max(0, num_start - search_range)
                        text_before = current_text[search_start:num_start]

                        # 检查内容是否在编号前的文本中
                        idx = text_before.rfind(sentence_content)
                        if idx != -1:
                            # 找到了！
                            found_pos = search_start + idx
                            found_length = len(sentence_content)
                            logger.info(f"策略1成功: 找到特定编号 [{sentence_number}] 前的内容")
                            break
                except Exception as e:
                    logger.error(f"策略1搜索出错: {e}")

            # === 策略 2: 内容精确匹配 ===
            # 如果策略1失败，尝试直接找内容
            if found_pos == -1 and sentence_content:
                try:
                    idx = current_text.find(sentence_content)
                    if idx != -1:
                        found_pos = idx
                        found_length = len(sentence_content)
                        logger.info("策略2成功: 内容精确匹配")
                except Exception as e:
                    logger.error(f"策略2搜索出错: {e}")

            # === 策略 3: 去除标点和空白后的模糊匹配 ===
            if found_pos == -1 and sentence_content:
                try:
                    # 获取句子的唯一标识（前20个字符 + 后10个字符）
                    # 这种方式比完全去空格更加鲁棒且快速
                    if len(sentence_content) > 30:
                        prefix = sentence_content[:20]
                        suffix = sentence_content[-10:]

                        # 查找前缀
                        start_idx = current_text.find(prefix)
                        if start_idx != -1:
                            # 验证后缀是否在合理距离内
                            # 允许内容长度有 +/- 20% 甚至更多的变化
                            expected_len = len(sentence_content)
                            max_dist = int(expected_len * 1.5) + 50

                            snippet = current_text[start_idx:start_idx + max_dist]
                            suffix_idx = snippet.find(suffix)

                            if suffix_idx != -1:
                                found_pos = start_idx
                                found_length = suffix_idx + len(suffix)
                                logger.info("策略3成功: 前后缀匹配")

                    # 备用：仅前缀匹配 (如果句子较短或没找到后缀)
                    elif len(sentence_content) > 5:
                        idx = current_text.find(sentence_content[:10])
                        if idx != -1:
                            found_pos = idx
                            found_length = len(sentence_content)
                            logger.info("策略3b成功: 短句前缀匹配")
                except Exception as e:
                    logger.error(f"策略3搜索出错: {e}")

            # === 策略 4: 仅编号匹配 (兜底) ===
            if found_pos == -1 and sentence_number:
                try:
                    pattern = r'\[' + re.escape(sentence_number) + r'\]'
                    match = re.search(pattern, current_text)
                    if match:
                        num_pos = match.start()
                        # 尝试向前选中一段文本作为一个句子 (寻找句末标点)
                        scan_start = max(0, num_pos - 200)
                        text_scan = current_text[scan_start:num_pos]

                        # 寻找最后一个句末标点
                        last_punct = -1
                        for p in ['。', '！', '？', '\n', '!', '?', '.']:
                            p_idx = text_scan.rfind(p)
                            if p_idx > last_punct:
                                last_punct = p_idx

                        if last_punct != -1:
                            found_pos = scan_start + last_punct + 1
                            found_length = num_pos - found_pos
                        else:
                            # 没找到标点，就默认选中前50个字
                            found_pos = max(0, num_pos - 50)
                            found_length = num_pos - found_pos

                        logger.info(f"策略4成功: 仅通过编号 [{sentence_number}] 估算位置")
                except Exception as e:
                    logger.error(f"策略4搜索出错: {e}")

            # 执行高亮与滚动
            if found_pos != -1:
                # 再次修正长度，防止越界
                if found_pos + found_length > len(current_text):
                    found_length = len(current_text) - found_pos

                if found_length > 0:
                    self._highlight_and_scroll_to_position(found_pos, found_length)
                    if hasattr(self, 'statusBar'):
                        self.statusBar().showMessage(f"已定位到内容 (位置: {found_pos})")
                else:
                    logger.warning("找到位置但长度无效")
            else:
                logger.warning(f"未找到句子: {sentence_content[:20]}... [{sentence_number}]")
                if hasattr(self, 'statusBar'):
                    self.statusBar().showMessage("在当前文本中未找到对应句子")

        except Exception as e:
            logger.error(f"导航过程发生严重错误: {e}")
            import traceback
            traceback.print_exc()

    def _highlight_and_scroll_to_position(self, start_pos, length):
        """在指定位置高亮文本并滚动到该位置"""
        try:
            # 验证参数
            if start_pos < 0 or length <= 0:
                logger.warning(f"无效的位置参数: start_pos={start_pos}, length={length}")
                return

            # 验证text_display是否存在
            if not hasattr(self, 'text_display') or self.text_display is None:
                logger.error("text_display不存在")
                return

            # 获取文本长度，确保不越界
            try:
                current_text = self.text_display.toPlainText()
                text_length = len(current_text)
            except Exception as e:
                logger.error(f"获取文本长度失败: {e}")
                return

            if start_pos >= text_length:
                logger.warning(f"起始位置超出文本范围: start_pos={start_pos}, text_length={text_length}")
                return

            # 调整长度，确保不越界
            if start_pos + length > text_length:
                length = text_length - start_pos
                logger.info(f"调整高亮长度以避免越界: new_length={length}")

            if length <= 0:
                logger.warning(f"调整后长度无效: {length}")
                return

            # 创建光标并设置选区
            cursor = self.text_display.textCursor()
            cursor.setPosition(start_pos)
            cursor.setPosition(start_pos + length, QTextCursor.KeepAnchor)

            # 设置高亮
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format.setBackground(QColor(173, 216, 230))  # 浅蓝色背景
            selection.format.setForeground(QColor(0, 0, 0))  # 黑色文字
            self.text_display.setExtraSelections([selection])

            # 将光标移动到选区开始位置
            cursor.setPosition(start_pos)
            self.text_display.setTextCursor(cursor)

            # 确保光标可见（滚动到该位置）
            self.text_display.ensureCursorVisible()

            logger.info(f"成功高亮位置: start={start_pos}, length={length}")

        except Exception as e:
            logger.error(f"高亮和滚动到位置时出错: {e}")
            import traceback
            traceback.print_exc()
            # 不要抛出异常，避免闪退
            # 不要抛出异常，避免闪退

    def clear_text_highlights(self):
        """清除文本高亮"""
        try:
            self.text_display.setExtraSelections([])
        except Exception as e:
            logger.error(f"清除文本高亮时出错: {e}")

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

            extra_selections = []

            # 首先高亮编码标记
            while search_count < max_searches:
                # 查找编码标记
                search_cursor = self.text_document.find(pattern, search_cursor, QTextDocument.FindCaseSensitively)
                if search_cursor.isNull():
                    break

                # 设置高亮格式 - 编码标记保持默认样式，不进行高亮
                # 我们改为使用ExtraSelection但不添加背景色
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

                        # 设置高亮格式（使用不同颜色区分）
                        selection = QTextEdit.ExtraSelection()
                        selection.cursor = content_cursor
                        selection.format.setBackground(QColor(173, 216, 230))  # 浅蓝色背景
                        selection.format.setForeground(QColor(0, 0, 139))  # 深蓝色文字
                        extra_selections.append(selection)

                        if first_match_cursor is None:
                            first_match_cursor = self.text_display.textCursor()
                            first_match_cursor.setPosition(content_cursor.selectionStart())

                        # 移动光标到找到的内容之后，防止重复匹配
                        content_cursor.movePosition(content_cursor.Right, content_cursor.MoveAnchor, len(clean_content))
                        content_search_count += 1

            # 安全检查：确保只有当文档内容与请求一致时才显示高亮
            # 否则可能会在错误的文档中高亮错误的位置
            if extra_selections:
                self.text_display.setExtraSelections(extra_selections)

            if found and first_match_cursor:
                # 滚动到第一个匹配项的位置
                self.text_display.setTextCursor(first_match_cursor)
                self.text_display.ensureCursorVisible()
                if hasattr(self, 'statusBar'):
                    self.statusBar().showMessage(f"已高亮编码 {code_id}")
            elif extra_selections:
                # 如果没有找到编码标记但找到了内容，也定位到内容
                first_sel = extra_selections[0]
                self.text_display.setTextCursor(first_sel.cursor)
                self.text_display.ensureCursorVisible()
                if hasattr(self, 'statusBar'):
                    self.statusBar().showMessage(f"已高亮编码 {code_id} 的内容")
            else:
                if hasattr(self, 'statusBar'):
                    self.statusBar().showMessage(f"未找到编码 {code_id} 的标记或内容")

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

                    if child_data:
                        if child_data.get("level") == 1:  # 一阶编码
                            if child_data.get("code_id") == code_id:
                                # 找到匹配的编码，返回其句子详情
                                sentence_details = child_data.get("sentence_details", [])
                                if sentence_details:
                                    # 确保每个sentence_details都有必要的字段
                                    for detail in sentence_details:
                                        if isinstance(detail, dict):
                                            # 确保detail有original_content字段
                                            if 'original_content' not in detail:
                                                # 尝试从其他字段获取原始内容
                                                detail['original_content'] = detail.get('content', '') or detail.get(
                                                    'text', '')
                                            # 确保detail有text字段
                                            if 'text' not in detail:
                                                # 尝试从其他字段获取文本
                                                detail['text'] = detail.get('content', '') or detail.get(
                                                    'original_content', '')
                                            # 确保detail有code_id字段
                                            if 'code_id' not in detail:
                                                detail['code_id'] = code_id
                                            # 确保detail有sentence_id字段
                                            if 'sentence_id' not in detail:
                                                # 尝试从text中提取编号
                                                import re
                                                number_match = re.search(r'\[(\d+)\]', detail.get('text', ''))
                                                if number_match:
                                                    detail['sentence_id'] = number_match.group(1)
                                        sentences.append(detail)
                                else:
                                    # 如果没有sentence_details，使用内容创建基本结构
                                    content = child_data.get("content", "")
                                    if content:
                                        # 从内容中提取可能的句子编号
                                        import re
                                        sentence_numbers = re.findall(r'\[(\d+)\]', content)
                                        if sentence_numbers:
                                            # 创建包含编号的句子详情
                                            sentences.append(
                                                {"text": content, "original_content": content, "code_id": code_id,
                                                 "sentence_id": sentence_numbers[0]})
                                        else:
                                            sentences.append(
                                                {"text": content, "original_content": content, "code_id": code_id})

                    # 递归搜索子节点
                    search_tree_for_sentences(child)

            # 遍历顶层项目
            for i in range(self.coding_tree.topLevelItemCount()):
                top_item = self.coding_tree.topLevelItem(i)
                search_tree_for_sentences(top_item)

            # 如果仍然没有找到，尝试从编码树的所有一阶编码中查找
            if not sentences:
                def find_all_first_level_codes(item):
                    for i in range(item.childCount()):
                        child = item.child(i)
                        child_data = child.data(0, Qt.UserRole)
                        if child_data and child_data.get("level") == 1:
                            if child_data.get("code_id") == code_id:
                                content = child_data.get("content", "")
                                if content:
                                    sentences.append({"text": content, "original_content": content, "code_id": code_id})
                        # 递归搜索子节点
                        find_all_first_level_codes(child)

                for i in range(self.coding_tree.topLevelItemCount()):
                    top_item = self.coding_tree.topLevelItem(i)
                    find_all_first_level_codes(top_item)

            # 去重处理，避免重复的句子
            seen_texts = set()
            unique_sentences = []
            for sentence in sentences:
                text = sentence.get('text', '')
                if text not in seen_texts:
                    seen_texts.add(text)
                    unique_sentences.append(sentence)

            logger.info(f"编码 {code_id} 找到 {len(unique_sentences)} 个句子")
            return unique_sentences

        except Exception as e:
            logger.error(f"获取句子详情失败: {e}")
            return []

    def highlight_text_by_code_id_precise(self, code_id: str):
        """通过编码ID精确高亮文本和对应内容（基于sentence_details）"""
        try:
            if not code_id:
                return False

            # 限制处理时间，避免长时间阻塞
            import time
            start_time = time.time()
            max_execution_time = 2.0  # 2秒超时

            # 清除之前的高亮
            self.clear_text_highlights()

            # 获取编码对应的精确句子内容
            sentences_to_highlight = self.get_sentences_by_code_id(code_id)

            if not sentences_to_highlight:
                self.statusBar().showMessage(f"未找到编码 {code_id} 的句子详情") if hasattr(self, 'statusBar') else None
                return False

            # 获取一阶编码的精确内容
            code_content = self.get_content_by_code_id(code_id)
            code_clean = ""
            import re
            if code_content:
                # 清理编码内容，移除可能存在的标记，例如 [A1], A1等
                code_clean = re.sub(r'\s*\[[A-Z]\d+\]', '', code_content)
                code_clean = re.sub(r'^[A-Z]\d+\s+', '', code_clean)
                code_clean = re.sub(r'\s*\[\d+\]', '', code_clean).strip()
                # 去除可能的关联编号前缀，例如 "1:"
                code_clean = re.sub(r'^\d+\s*:\s*', '', code_clean).strip()

            # 查找包含该句子的文件并切换显示
            target_file = None
            best_match_score = 0
            best_match_file = None
            best_match_sentence = None
            target_sentence_id = None  # 记录关联的句子ID

            # 策略0：优先检查sentence_details中是否直接包含file_path或filename
            # 这是最准确的定位方式：如果有明确的文件来源，直接使用该文件
            for sentence_info in sentences_to_highlight:
                fp = sentence_info.get('file_path')
                fn = sentence_info.get('filename')

                # 情况1: 直接有完整路径
                if fp and fp in self.loaded_files:
                    target_file = fp
                    logger.info(f"直接使用sentence_details中的文件路径: {target_file}")
                    break

                # 情况2: 只有文件名，需要在已加载文件中查找
                if fn:
                    for loaded_fp in self.loaded_files.keys():
                        if os.path.basename(loaded_fp) == fn:
                            target_file = loaded_fp
                            logger.info(f"根据文件名找到文件路径: {target_file}")
                            break
                    if target_file:
                        break

            # 如果策略0未找到文件，继续后续策略
            if not target_file:
                # 尝试从sentences_to_highlight中获取关联的句子ID
                for sentence_info in sentences_to_highlight:
                    if sentence_info.get('sentence_id'):
                        target_sentence_id = sentence_info.get('sentence_id')
                        break

                # 优先使用编码内容进行文件匹配
                if code_clean:
                    for file_path, file_data in self.loaded_files.items():
                        if time.time() - start_time > max_execution_time:
                            logger.warning("文件匹配超时")
                            return False

                        file_text = file_data.get('numbered_content', '') or file_data.get('content', '')
                        if not file_text:
                            continue

                        if code_clean in file_text:
                            target_file = file_path
                            break

            # 如果没找到，尝试通过句子ID匹配文件
            if not target_file and target_sentence_id:
                sentence_tag = f"[{target_sentence_id}]"
                for file_path, file_data in self.loaded_files.items():
                    file_text = file_data.get('numbered_content', '') or file_data.get('content', '')
                    if sentence_tag in file_text:
                        target_file = file_path
                        break

            # 如果没有找到，使用句子内容进行匹配
            if not target_file:
                for sentence_info in sentences_to_highlight:
                    if time.time() - start_time > max_execution_time:
                        logger.warning("句子匹配超时")
                        return False

                    # 优先使用原始内容，而不是抽象后的内容
                    sentence_content = sentence_info.get('text', '').strip()
                    if not sentence_content:
                        continue

                    # 清理句子内容
                    import re
                    sentence_clean = re.sub(r'\s*\[[A-Z]\d+\]', '', sentence_content)
                    sentence_clean = re.sub(r'^[A-Z]\d+\s+', '', sentence_clean)
                    sentence_clean = re.sub(r'\s*\[\d+\]', '', sentence_clean).strip()

                    # 在所有已加载的文件中查找，使用更精确的匹配
                    for file_path, file_data in self.loaded_files.items():
                        if time.time() - start_time > max_execution_time:
                            logger.warning("文件查找超时")
                            return False

                        file_text = file_data.get('numbered_content', '') or file_data.get('content', '')
                        if not file_text:
                            continue

                        # 计算匹配分数
                        score = 0
                        if sentence_clean in file_text:
                            score = 100  # 完全匹配
                        else:
                            # 计算关键词匹配
                            words = [word for word in sentence_clean.split() if len(word) > 2]
                            if len(words) > 5:
                                words = words[:5]  # 限制关键词数量
                            matched_words = 0
                            for word in words:
                                if word in file_text:
                                    matched_words += 1
                            if words:
                                score = (matched_words / len(words)) * 100

                        # 更新最佳匹配
                        if score > best_match_score:
                            best_match_score = score
                            best_match_file = file_path
                            best_match_sentence = sentence_info

                # 使用最佳匹配的文件
                if best_match_file and best_match_score > 30:  # 最低匹配分数阈值
                    target_file = best_match_file

            # 如果找到目标文件且不是当前显示的文件，切换文件
            if target_file:
                current_items = self.file_list.selectedItems()
                current_file = current_items[0].data(Qt.UserRole) if current_items else None

                if current_file != target_file:
                    # 在文件列表中查找并选中目标文件
                    for i in range(self.file_list.count()):
                        item = self.file_list.item(i)
                        if item.data(Qt.UserRole) == target_file:
                            self.file_list.setCurrentItem(item)
                            # 显式触发文件加载
                            self.on_file_selected(item)
                            # 等待文件显示更新
                            QApplication.processEvents()
                            break

            # 获取当前显示的文本
            current_text = self.text_display.toPlainText()
            if not current_text:
                return False

            # 移动光标到文本开始
            cursor = self.text_display.textCursor()
            cursor.movePosition(cursor.Start)
            self.text_display.setTextCursor(cursor)

            # 精确高亮一阶编码对应的短语
            found_count = 0
            first_match_position = None  # 记录第一个匹配项的位置
            extra_selections = []  # 用于存储临时高亮的选择

            # 优先高亮一阶编码的精确内容
            if code_clean:
                search_cursor = self.text_display.textCursor()
                search_cursor.movePosition(cursor.Start)

                # 策略1：直接查找编码内容
                found_cursor = self.text_document.find(code_clean, search_cursor)

                # 策略2：如果策略1失败，尝试使用正则表达式查找（忽略空白差异）
                if found_cursor.isNull():
                    # 限制正则表达式长度，避免性能问题
                    if len(code_clean) > 100:
                        code_clean = code_clean[:100]
                    # 转换为正则模式，将多个空白符视为一个
                    pattern = re.sub(r'\s+', r'\\s+', re.escape(code_clean))
                    regex = QRegularExpression(pattern)
                    found_cursor = self.text_document.find(regex, search_cursor)

                # 策略3：如果还失败，尝试查找关键词
                if found_cursor.isNull():
                    # 提取关键词
                    words = [word for word in code_clean.split() if len(word) > 2]
                    if words and len(words) <= 5:
                        # 尝试查找前几个关键词
                        keyword_pattern = r'\b' + r'\b.*\b'.join(words[:3]) + r'\b'
                        regex = QRegularExpression(keyword_pattern, QRegularExpression.CaseInsensitiveOption)
                        found_cursor = self.text_document.find(regex, search_cursor)

                if not found_cursor.isNull():
                    # 使用 ExtraSelection 进行临时高亮
                    selection = QTextEdit.ExtraSelection()
                    selection.cursor = found_cursor
                    selection.format.setBackground(QColor(173, 216, 230))  # 浅蓝色背景
                    selection.format.setForeground(QColor(0, 0, 139))  # 深蓝色文字
                    extra_selections.append(selection)

                    found_count += 1

                    # 记录第一个匹配项的位置用于滚动
                    if first_match_position is None:
                        first_match_position = found_cursor.selectionStart()
                        logger.info(f"记录第一个匹配位置: {first_match_position}")

            # 如果没有找到编码内容，尝试高亮句子内容
            if found_count == 0:
                # 尝试使用句子ID精确定位（针对自动编码产生的数字ID）
                # 这是最可靠的定位方式，特别是对于纯文本内容匹配失败的情况
                if sentences_to_highlight:
                    for sentence_info in sentences_to_highlight:
                        sentence_id = sentence_info.get('id', '')
                        if sentence_id:
                            # 构造精确的ID查找正则表达式 [ID]
                            id_pattern = r'\[' + re.escape(str(sentence_id)) + r'\]'
                            id_regex = QRegularExpression(id_pattern)
                            id_match = id_regex.match(current_text)

                            if id_match.hasMatch():
                                # 找到ID位置
                                match_start = id_match.capturedStart()
                                match_end = id_match.capturedEnd()

                                # 将光标移动到ID之后
                                cursor = self.text_display.textCursor()
                                cursor.setPosition(match_end)

                                # 尝试查找该句子的结束位置（下一个 [ID] 或段落结束）
                                next_id_pattern = r'\[\w+\d+\]|\[\d+\]'  # 匹配下一个ID标记
                                next_regex = QRegularExpression(next_id_pattern)
                                next_match = next_regex.match(current_text, match_end)

                                end_pos = -1
                                if next_match.hasMatch():
                                    end_pos = next_match.capturedStart()
                                else:
                                    # 如果没有下一个ID，则高亮到段落结束或一定长度
                                    block = cursor.block()
                                    end_pos = block.position() + block.length() - 1

                                    # 选中从ID结束到句子结束的文本
                                if end_pos > match_end:
                                    selection = QTextEdit.ExtraSelection()
                                    cursor.setPosition(match_end)
                                    cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
                                    selection.cursor = cursor
                                    selection.format.setBackground(QColor(173, 216, 230))
                                    selection.format.setForeground(QColor(0, 0, 139))
                                    extra_selections.append(selection)

                                    found_count += 1
                                    if first_match_position is None:
                                        first_match_position = match_start

                                    # 如果找到了，就跳出循环，避免重复处理
                                    break

                # 如果ID定位也失败，继续尝试原来的内容匹配逻辑
                if found_count == 0:
                    # 限制处理的句子数量
                    max_sentences = 3
                processed_sentences = 0

                for sentence_info in sentences_to_highlight:
                    if processed_sentences >= max_sentences:
                        break

                    if time.time() - start_time > max_execution_time:
                        logger.warning("句子高亮超时")
                        break

                    # 优先使用原始内容，而不是抽象后的内容
                    sentence_content = sentence_info.get('original_content', '') or sentence_info.get('text',
                                                                                                      '').strip()
                    if not sentence_content:
                        continue

                    # 清理句子内容：移除可能存在的编号标记
                    sentence_clean = re.sub(r'\s*\[[A-Z]\d+\]', '', sentence_content)
                    sentence_clean = re.sub(r'^[A-Z]\d+\s+', '', sentence_clean)
                    sentence_clean = re.sub(r'\s*\[\d+\]', '', sentence_clean).strip()

                    # 尝试从sentence_info中获取file_path，如果有的话
                    file_path = sentence_info.get('file_path', '')
                    if file_path and file_path in self.loaded_files:
                        # 如果指定了文件路径，确保当前显示的是该文件
                        current_items = self.file_list.selectedItems()
                        current_file = current_items[0].data(Qt.UserRole) if current_items else None
                        if current_file != file_path:
                            for i in range(self.file_list.count()):
                                item = self.file_list.item(i)
                                if item.data(Qt.UserRole) == file_path:
                                    self.file_list.setCurrentItem(item)
                                    QApplication.processEvents()
                                    current_text = self.text_display.toPlainText()
                                    break

                    # 在文本中查找并高亮这个精确句子
                    search_cursor = self.text_display.textCursor()
                    search_cursor.movePosition(cursor.Start)

                    # 策略1：直接查找清理后的文本
                    if len(sentence_clean) > 200:
                        sentence_clean = sentence_clean[:200]  # 限制搜索长度
                    found_cursor = self.text_document.find(sentence_clean, search_cursor)

                    # 策略2：如果策略1失败，尝试查找前50个字符
                    if found_cursor.isNull() and len(sentence_clean) > 50:
                        found_cursor = self.text_document.find(sentence_clean[:50], search_cursor)

                    # 策略3：如果还失败，尝试使用正则表达式查找（忽略空白差异）
                    if found_cursor.isNull():
                        # 限制正则表达式长度
                        if len(sentence_clean) > 100:
                            sentence_clean = sentence_clean[:100]
                        # 转换为正则模式，将多个空白符视为一个
                        pattern = re.sub(r'\s+', r'\\s+', re.escape(sentence_clean))
                        regex = QRegularExpression(pattern)
                        found_cursor = self.text_document.find(regex, search_cursor)

                    # 策略4：如果还失败，尝试查找关键词
                    if found_cursor.isNull():
                        # 提取关键词
                        words = [word for word in sentence_clean.split() if len(word) > 2]
                        if words and len(words) <= 5:
                            # 尝试查找前几个关键词
                            keyword_pattern = r'\b' + r'\b.*\b'.join(words[:3]) + r'\b'
                            regex = QRegularExpression(keyword_pattern, QRegularExpression.CaseInsensitiveOption)
                            found_cursor = self.text_document.find(regex, search_cursor)

                    if not found_cursor.isNull():
                        # 使用 ExtraSelection 进行临时高亮
                        selection = QTextEdit.ExtraSelection()
                        selection.cursor = found_cursor
                        selection.format.setBackground(QColor(173, 216, 230))  # 浅蓝色背景
                        selection.format.setForeground(QColor(0, 0, 139))  # 深蓝色文字
                        extra_selections.append(selection)

                        found_count += 1
                        processed_sentences += 1

                        # 记录第一个匹配项的位置用于滚动
                        if first_match_position is None:
                            first_match_position = found_cursor.selectionStart()
                            logger.info(f"记录第一个匹配位置: {first_match_position}")

            if found_count > 0 and first_match_position is not None:
                # 限制高亮数量，避免内存问题
                if len(extra_selections) > 5:
                    extra_selections = extra_selections[:5]

                # 应用临时高亮
                self.text_display.setExtraSelections(extra_selections)

                # 创建新的光标并定位到第一个匹配项的位置
                new_cursor = self.text_display.textCursor()
                new_cursor.setPosition(first_match_position)

                # 设置光标并确保可见
                self.text_display.setTextCursor(new_cursor)
                self.text_display.ensureCursorVisible()

                logger.info(f"已定位到位置: {first_match_position}")
                self.statusBar().showMessage(f"已高亮编码 {code_id} 的 {found_count} 个短语") if hasattr(self,
                                                                                                'statusBar') else None
                return True
            else:
                logger.warning(f"未找到编码 {code_id} 对应的内容")
                self.statusBar().showMessage(f"未找到编码 {code_id} 对应的内容") if hasattr(self, 'statusBar') else None
                return False

        except Exception as e:
            logger.error(f"精确高亮文本失败: {e}")
            import traceback
            traceback.print_exc()
            # 发生异常时确保清除高亮
            try:
                self.clear_text_highlights()
            except:
                pass
            self.statusBar().showMessage(f"高亮失败: {str(e)}") if hasattr(self, 'statusBar') else None
            return False

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
                            return child_data.get("content", "") or child_data.get("name", "")

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
                    return top_data.get("content", "") or top_data.get("name", "")

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

    def perform_search(self):
        """执行搜索"""
        search_text = self.search_line_edit.text().strip()
        if not search_text:
            return

        # 搜索一阶编码
        results = self.search_first_level_codes(search_text)
        if results:
            # 显示搜索结果弹窗
            self.show_search_results(results, search_text)

    def search_first_level_codes(self, search_text):
        """搜索一阶编码"""
        results = []

        # 遍历已分类编码
        for third_cat, second_cats in self.current_codes.items():
            for second_cat, first_contents in second_cats.items():
                for content in first_contents:
                    if isinstance(content, dict):
                        code_content = content.get('content', '')
                        code_id = content.get('code_id', '')
                        sentence_details = content.get('sentence_details', [])

                        # 检查是否包含搜索文本
                        if search_text in code_content:
                            # 提取TextNumbering编号
                            text_numbering = ""
                            if sentence_details:
                                first_detail = sentence_details[0]
                                text_numbering = first_detail.get('sentence_id', '') or first_detail.get('code_id', '')

                            results.append({
                                'content': code_content,
                                'code_id': code_id,
                                'text_numbering': text_numbering,
                                'third_cat': third_cat,
                                'second_cat': second_cat,
                                'content_obj': content
                            })
                    else:
                        # 处理字符串内容
                        code_content = str(content)
                        if search_text in code_content:
                            results.append({
                                'content': code_content,
                                'code_id': '',
                                'text_numbering': '',
                                'third_cat': third_cat,
                                'second_cat': second_cat,
                                'content_obj': content
                            })

        # 遍历未分类编码
        for item in self.unclassified_first_codes:
            if isinstance(item, dict):
                code_content = item.get('content', '')
                code_id = item.get('code_id', '')
                sentence_details = item.get('sentence_details', [])

                if search_text in code_content:
                    text_numbering = ""
                    if sentence_details:
                        first_detail = sentence_details[0]
                        text_numbering = first_detail.get('sentence_id', '') or first_detail.get('code_id', '')

                    results.append({
                        'content': code_content,
                        'code_id': code_id,
                        'text_numbering': text_numbering,
                        'third_cat': '未分类',
                        'second_cat': '未分类',
                        'content_obj': item
                    })
            else:
                code_content = str(item)
                if search_text in code_content:
                    results.append({
                        'content': code_content,
                        'code_id': '',
                        'text_numbering': '',
                        'third_cat': '未分类',
                        'second_cat': '未分类',
                        'content_obj': item
                    })

        # 按TextNumbering编号排序
        results.sort(key=lambda x: x['text_numbering'] if x['text_numbering'] else '')
        return results

    def show_search_results(self, results, search_text):
        """显示搜索结果弹窗"""
        dialog = QDialog(self)
        dialog.setWindowTitle("搜索结果")
        dialog.resize(400, 300)

        layout = QVBoxLayout(dialog)

        # 结果列表
        result_list = QListWidget()
        result_list.setSelectionMode(QListWidget.SingleSelection)

        # 添加结果项
        for i, result in enumerate(results):
            item_text = f"[{result['text_numbering']}] {result['content'][:100]}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, result)
            result_list.addItem(item)

        layout.addWidget(result_list)

        # 按钮
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")

        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(ok_btn)

        layout.addLayout(button_layout)

        # 连接信号
        def on_item_double_clicked(item):
            result = item.data(Qt.UserRole)
            self.navigate_to_search_result(result)
            dialog.accept()

        def on_ok_clicked():
            selected_items = result_list.selectedItems()
            if selected_items:
                result = selected_items[0].data(Qt.UserRole)
                self.navigate_to_search_result(result)
            dialog.accept()

        result_list.itemDoubleClicked.connect(on_item_double_clicked)

        ok_btn.clicked.connect(on_ok_clicked)
        cancel_btn.clicked.connect(lambda: dialog.reject())

        dialog.exec_()

    def navigate_to_search_result(self, result):
        """导航到搜索结果"""
        # 定位到编码树中的一阶编码
        self.locate_and_select_code(result)

        # 高亮文本内容
        self.highlight_search_result(result)

    def locate_and_select_code(self, result):
        """定位并选中编码树中的一阶编码"""
        # 展开所有节点
        self.coding_tree.expandAll()

        # 查找并选中对应的一阶编码
        self.find_and_select_first_level_code(result['third_cat'], result['second_cat'], result['content'])

    def find_and_select_first_level_code(self, third_cat, second_cat, content):
        """查找并选中一阶编码"""
        for i in range(self.coding_tree.topLevelItemCount()):
            third_item = self.coding_tree.topLevelItem(i)
            if third_item.text(0) == third_cat:
                for j in range(third_item.childCount()):
                    second_item = third_item.child(j)
                    if second_item.text(0) == second_cat:
                        for k in range(second_item.childCount()):
                            first_item = second_item.child(k)
                            if content in first_item.text(0):
                                self.coding_tree.setCurrentItem(first_item)
                                # 确保可见
                                self.coding_tree.scrollToItem(first_item)
                                return

    def highlight_search_result(self, result):
        """高亮搜索结果"""
        content = result['content']
        if content:
            self.highlight_text_content(content)

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

            extra_selections = []

            while search_count < max_searches:
                search_cursor = self.text_document.find(clean_content, search_cursor, QTextDocument.FindCaseSensitively)
                if search_cursor.isNull():
                    break

                # 设置高亮格式
                selection = QTextEdit.ExtraSelection()
                selection.cursor = search_cursor
                selection.format.setBackground(QColor(173, 216, 230))  # 浅蓝色背景
                selection.format.setForeground(QColor(0, 0, 139))  # 深蓝色文字

                # 应用高亮
                extra_selections.append(selection)
                found = True

                # 记录第一个匹配项的位置
                if first_match_cursor is None:
                    first_match_cursor = self.text_display.textCursor()
                    first_match_cursor.setPosition(search_cursor.selectionStart())

                # 移动光标到找到的内容之后，防止重复匹配
                search_cursor.movePosition(search_cursor.Right, search_cursor.MoveAnchor, len(clean_content))
                search_count += 1

            if extra_selections:
                self.text_display.setExtraSelections(extra_selections)

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
            save_dir = PathManager.get_manual_coding_tree_save_dir()
            PathManager.ensure_dir(save_dir)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"编码树_{timestamp}.json"
            file_path = PathManager.join(save_dir, filename)

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
            with PathManager.safe_open(file_path, 'w', encoding='utf-8') as f:
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
            import_dir = PathManager.get_manual_coding_tree_save_dir()
            PathManager.ensure_dir(import_dir)

            # 获取导入路径
            file_path, _ = QFileDialog.getOpenFileName(
                self, "导入编码树", import_dir, "JSON文件 (*.json);;所有文件 (*)"
            )

            if file_path:
                # 读取编码结构
                with PathManager.safe_open(file_path, 'r', encoding='utf-8') as f:
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
            import_dir = PathManager.get_manual_coding_save_dir()
            PathManager.ensure_dir(import_dir)

            # 获取导入路径
            file_path, _ = QFileDialog.getOpenFileName(
                self, "导入编码结果", import_dir, "JSON文件 (*.json);;所有文件 (*)"
            )

            if file_path:
                # 读取编码结果
                with PathManager.safe_open(file_path, 'r', encoding='utf-8') as f:
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
        """显示句子详情对话框 - 支持编辑功能，保持TextNumbering编号不变"""
        try:
            # 首先从当前选中的项目中获取关联编号（从编码树第5列获取）
            associated_number = ""
            current_item = self.coding_tree.currentItem()
            if current_item:
                associated_number = current_item.text(5)  # 关联编号在第5列

            # 获取一阶编码的完整内容（从编码树第0列获取）
            coding_tree_content = ""
            if current_item:
                coding_tree_content = current_item.text(0)

            # 从编码树内容中提取纯内容（去除 code_id 前缀）
            pure_content = coding_tree_content
            if code_id and pure_content.startswith(code_id):
                # 移除 code_id 前缀
                if pure_content.startswith(code_id + ': '):
                    pure_content = pure_content[len(code_id + ': '):]
                elif pure_content.startswith(code_id + ' '):
                    pure_content = pure_content[len(code_id + ' '):]

            # 对纯内容进行清理，移除可能的编号标记和编码标识符，获取不含编号的内容
            import re
            content_without_number = re.sub(r'\s*\[[A-Z]\d+\]', '', pure_content)
            content_without_number = re.sub(r'\s*\[\d+\]', '', content_without_number)
            # 修复：移除句子开头的编码标识符（如"A01 "、"B02 "等）
            content_without_number = re.sub(r'^[A-Z]\d+\s+', '', content_without_number)
            content_without_number = content_without_number.strip()

            # 从关联编号中解析出多个句子编号
            associated_numbers_list = []
            if associated_number:
                associated_numbers_list = [num.strip() for num in associated_number.split(',') if num.strip()]

            # 处理句子详情，获取所有句子
            sentences_list = []
            original_sentences_data = []  # 保存原始数据用于更新
            if sentence_details:
                for i, detail in enumerate(sentence_details):
                    if isinstance(detail, dict):
                        # 从各个可能的字段获取句子内容
                        sent_text = detail.get('text', '') or detail.get('content', '') or detail.get(
                            'original_content', '')
                        if sent_text:
                            # 清理内容，移除编号标记和编码标识符
                            clean_text = re.sub(r'\s*\[[A-Z]\d+\]', '', sent_text)
                            clean_text = re.sub(r'\s*\[\d+\]', '', clean_text)
                            # 修复：移除句子开头的编码标识符
                            clean_text = re.sub(r'^[A-Z]\d+\s+', '', clean_text)
                            clean_text = clean_text.strip()

                            # 优先使用句子详情中的编号
                            sent_number = detail.get('sentence_id', '') or detail.get('code_id', '')
                            # 如果没有，尝试从文本中提取
                            if not sent_number:
                                number_match = re.search(r'\[(\d+)\]', sent_text)
                                if number_match:
                                    sent_number = number_match.group(1)

                            sentences_list.append({
                                'text': clean_text,
                                'original_text': sent_text,
                                'number': str(sent_number) if sent_number else '',
                                'file_path': detail.get('file_path', ''),
                                'filename': detail.get('filename', '')  # 保存文件名
                            })
                            # 保存原始数据副本
                            original_sentences_data.append(dict(detail))

            # 确保至少有一个句子（显示一阶编码文本）
            if not sentences_list:
                # 添加句子1：一阶编码文本
                sentences_list.append({
                    'text': content_without_number,
                    'number': associated_numbers_list[0] if associated_numbers_list else '',
                    'file_path': '', # 默认为空
                    'filename': ''
                })

            # 修复 UnboundLocalError: 必须在使用前定义和赋值 first_code_number
            first_code_number = ""

            # 修复：正确获取一阶编码自身的句子编号（不是A01这种编码标识符）
            # 优先使用sentence_details中第一项的句子编号
            if sentence_details and len(sentence_details) > 0:
                first_detail = sentence_details[0]
                # 获取实际的句子编号，确保是数字编号而不是编码标识符
                first_code_number = first_detail.get('code_id', '') or first_detail.get('sentence_id', '')
                # 如果获取到的是编码标识符（如A01），则从关联编号中获取
                if first_code_number and not first_code_number.isdigit():
                    if associated_numbers_list:
                        first_code_number = associated_numbers_list[0]
                        logger.info(f"从关联编号获取一阶编码实际句子编号: {first_code_number}")
                else:
                    logger.info(f"从sentence_details获取一阶编码句子编号: {first_code_number}")

            # 确保正确设置sentences_list[0]的文件路径和编号
            if sentences_list:
                if not sentences_list[0].get('file_path'):
                    if sentence_details and len(sentence_details) > 0:
                        sentences_list[0]['file_path'] = sentence_details[0].get('file_path', '')
                if not sentences_list[0].get('number') and first_code_number and first_code_number.isdigit():
                    sentences_list[0]['number'] = first_code_number

            # 如果上述方式失败，使用关联编号列表中的第一个编号
            if not first_code_number or not first_code_number.isdigit():
                if associated_numbers_list:
                    first_code_number = associated_numbers_list[0]
                    logger.info(f"使用关联编号第一项作为一阶编码句子编号: {first_code_number}")

            logger.info(f"最终确定的一阶编码句子编号: {first_code_number}")
            logger.info(f"关联编号完整列表: {associated_numbers_list}")
            logger.info(f"sentence_details数量: {len(sentence_details) if sentence_details else 0}")

            # 为句子1填充缺失的文件路径（如果有的话）
            if sentences_list and not sentences_list[0].get('file_path'):
                if sentence_details and len(sentence_details) > 0:
                    sentences_list[0]['file_path'] = sentence_details[0].get('file_path', '')

            # 创建对话框
            dialog = QDialog(self)
            dialog.setWindowTitle(f"编辑一阶编码")
            dialog.resize(700, 600)

            layout = QVBoxLayout(dialog)

            # ========== 查看模式页面 ==========
            view_page = QWidget()
            view_layout = QVBoxLayout(view_page)

            # 创建 HTML 格式内容，严格按照用户要求的格式
            from PyQt5.QtWidgets import QTextBrowser

            text_display = QTextBrowser()
            text_display.setOpenExternalLinks(False)
            text_display.setOpenLinks(False)  # 禁止点击链接时自动跳转，防止内容被替换为空白

            # 保存对self的引用，避免闭包问题
            parent_dialog = self

            # 保存句子信息的字典，用于点击时查找
            sentence_data = {}

            def refresh_view_content():
                """刷新查看模式的内容显示"""
                # 首先构建一阶编码显示
                # 一阶编码标题始终使用A0X格式（code_id），而非TextNumbering编号
                display_html = f"""
                <div style='font-family: "Microsoft YaHei", Arial, sans-serif; font-size: 16px; line-height: 1.8;'>
                    <div style='font-weight: bold; font-size: 18px;'>一阶编码: {code_id}:</div>
                    <br>
                """

                # 一阶编码文本行显示纯内容和编号标记
                if first_code_number:
                    # 修复：确保显示的内容不包含编码标识符
                    first_code_content_with_number = re.sub(r'^[A-Z]\d+\s+', '', content_without_number).strip()
                    first_code_content_with_number += f" [{first_code_number}]"
                    display_html += f"<div>{first_code_content_with_number}</div><br>"
                else:
                    display_html += f"<div>{content_without_number}</div><br>"

                # 清空并重新填充句子数据
                sentence_data.clear()

                # 添加多个句子显示
                for i, sentence in enumerate(sentences_list, 1):
                    if i == 1:
                        # 句子1：显示一阶编码文本和对应的实际句子编号
                        # 修复：确保句子内容不包含编码标识符，以便正确导航
                        sentence_content = content_without_number
                        # 使用实际的句子编号而不是编码标识符(如A01)
                        sentence_number = first_code_number if first_code_number and first_code_number.isdigit() else ""
                        if not sentence_number:
                            sentence_number = sentences_list[0].get('number', '')
                        logger.info(f"弹出对话框句子1 - 编号: {sentence_number}, 内容前30字: {sentence_content[:30]}...")
                    else:
                        # 后续句子：显示拖拽的文本内容和对应的编号
                        sentence_content = sentence.get('text', content_without_number)
                        # 清理句子内容，移除编号标记和编码标识符
                        sentence_content = re.sub(r'\s*\[[A-Z]\d+\]', '', sentence_content)
                        sentence_content = re.sub(r'\s*\[\d+\]', '', sentence_content)
                        sentence_content = re.sub(r'^[A-Z]\d+\s+', '', sentence_content)  # 修复：移除开头编码标识符
                        sentence_content = sentence_content.strip()
                        sentence_number = sentence.get('number', '')
                        logger.info(f"弹出对话框句子{i} - 编号: {sentence_number}, 内容前30字: {sentence_content[:30]}...")

                    # 保存句子信息，使用句子编号或索引作为key
                    key = sentence_number if sentence_number else str(i)
                    sentence_data[key] = {
                        'content': sentence_content,
                        'number': sentence_number,
                        'index': i - 1,  # 保存索引用于编辑
                        'file_path': sentence.get('file_path', ''),  # 保存file_path
                        'filename': sentence.get('filename', '')  # 保存文件名
                    }

                    # 创建可点击的链接，只使用编号作为href，避免URL编码复杂问题
                    # HTML转义句子内容以防止XSS
                    safe_content = sentence_content.replace('&', '&amp;').replace('<', '&lt;').replace('>',
                                                                                                       '&gt;').replace(
                        '"', '&quot;').replace("'", '&#39;')
                    clickable_content = f"<a href='navigate:{key}' style='text-decoration: none; color: black; cursor: pointer;'>{safe_content}</a>"

                    display_html += f"""
                    <div style='font-weight: bold; font-size: 18px;'>句子 {i}:</div>
                    <br>
                    <div>编号: {sentence_number}</div>
                    <br>
                    <div>内容: {clickable_content}</div>
                    <br>
                    """

                display_html += "</div>"
                text_display.setHtml(display_html)

            # 初始刷新内容
            refresh_view_content()

            # 连接点击事件处理函数 - 保持原有导航高亮功能不变
            def handle_link_clicked(url):
                """处理句子内容点击事件 - 导航到对应句子并高亮"""
                try:
                    url_str = url.toString()
                    logger.info(f"点击了链接: {url_str}")

                    if url_str.startswith('navigate:'):
                        # 解析URL：navigate:key（编号或索引）
                        key = url_str[9:]  # 去掉 'navigate:' 前缀

                        logger.info(f"查找句子key: {key}")

                        # 从保存的字典中获取句子信息
                        if key in sentence_data:
                            sent_info = sentence_data[key]
                            sent_content = sent_info.get('content', '')
                            sent_number = sent_info.get('number', '')

                            logger.info(f"找到句子 - 编号: {sent_number}, 内容前50字: {sent_content[:50]}...")

                            # 执行导航和高亮 - 更新为支持文件路径
                            parent_dialog.navigate_to_sentence_content(
                                sent_content,
                                sent_number,
                                sent_info.get('file_path', ''),
                                sent_info.get('filename', '')
                            )
                        else:
                            logger.warning(f"未找到key为 {key} 的句子信息")

                except Exception as e:
                    logger.error(f"处理句子链接点击时出错: {e}")
                    import traceback
                    traceback.print_exc()
                    # 不要弹出错误对话框，避免影响用户体验

            text_display.anchorClicked.connect(handle_link_clicked)

            # ========== 右键菜单功能 ==========
            from PyQt5.QtWidgets import QMenu

            # 存储当前点击的句子信息
            current_sentence_key = None

            def show_context_menu(position):
                """显示右键菜单"""
                global current_sentence_key

                # 检查点击位置是否在链接上
                cursor = text_display.cursorForPosition(position)
                cursor.select(QTextCursor.WordUnderCursor)
                selected_text = cursor.selectedText()

                # 尝试获取链接信息
                char_format = cursor.charFormat()
                anchor = char_format.anchorHref()

                if anchor and anchor.startswith('navigate:'):
                    # 解析链接
                    current_sentence_key = anchor[9:]  # 去掉 'navigate:' 前缀

                    if current_sentence_key in sentence_data:
                        sent_info = sentence_data[current_sentence_key]
                        sent_index = sent_info.get('index', -1)

                        # 创建菜单
                        menu = QMenu()

                        # 编辑选项
                        edit_action = menu.addAction("编辑")
                        edit_action.triggered.connect(lambda: edit_sentence(current_sentence_key))

                        # 删除选项（句子1不能删除）
                        if sent_index > 0:
                            delete_action = menu.addAction("删除")
                            delete_action.triggered.connect(lambda: delete_sentence_context(current_sentence_key))

                        # 显示菜单
                        menu.exec_(text_display.mapToGlobal(position))

            def edit_sentence(key):
                """编辑句子内容"""
                try:
                    if key in sentence_data:
                        sent_info = sentence_data[key]
                        sent_content = sent_info.get('content', '')
                        sent_number = sent_info.get('number', '')
                        sent_index = sent_info.get('index', -1)

                        if sent_index >= 0 and sent_index < len(sentences_list):
                            # 创建编辑对话框
                            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox

                            edit_dialog = QDialog(dialog)
                            edit_dialog.setWindowTitle(f"编辑句子")
                            edit_dialog.resize(500, 200)

                            layout = QVBoxLayout(edit_dialog)

                            text_edit = QTextEdit()
                            text_edit.setPlainText(sent_content)
                            layout.addWidget(text_edit)

                            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                            buttons.accepted.connect(edit_dialog.accept)
                            buttons.rejected.connect(edit_dialog.reject)
                            layout.addWidget(buttons)

                            if edit_dialog.exec_() == QDialog.Accepted:
                                new_text = text_edit.toPlainText().strip()
                                if new_text:
                                    # 更新句子内容
                                    sentences_list[sent_index]['text'] = new_text

                                    # 构建新的sentence_details数据结构
                                    update_sentence_details()

                                    # 刷新查看模式内容
                                    refresh_view_content()

                                    logger.info(f"编辑句子 {sent_index + 1}: {new_text[:30]}...")
                                    QMessageBox.information(dialog, "成功", "句子编辑成功")

                except Exception as e:
                    logger.error(f"编辑句子失败: {e}")
                    QMessageBox.critical(dialog, "错误", f"编辑句子失败: {str(e)}")

            def delete_sentence_context(key):
                """删除句子"""
                try:
                    if key in sentence_data:
                        sent_info = sentence_data[key]
                        sent_content = sent_info.get('content', '')
                        sent_index = sent_info.get('index', -1)

                        if sent_index > 0 and sent_index < len(sentences_list):
                            # 确认删除
                            reply = QMessageBox.question(
                                dialog,
                                "确认删除",
                                f"确定要删除该句子吗？\n\n内容: {sent_content[:50]}...",
                                QMessageBox.Yes | QMessageBox.No
                            )

                            if reply == QMessageBox.Yes:
                                # 删除句子
                                deleted_sentence = sentences_list.pop(sent_index)

                                # 构建新的sentence_details数据结构
                                update_sentence_details()

                                # 刷新查看模式内容
                                refresh_view_content()

                                logger.info(f"删除句子 {sent_index + 1}: {deleted_sentence.get('text', '')[:30]}...")
                                QMessageBox.information(dialog, "成功", "句子删除成功")

                except Exception as e:
                    logger.error(f"删除句子失败: {e}")
                    QMessageBox.critical(dialog, "错误", f"删除句子失败: {str(e)}")

            def update_sentence_details():
                """更新sentence_details数据结构"""
                try:
                    # 构建新的sentence_details数据结构
                    new_sentence_details = []

                    # 句子1：一阶编码本身
                    if sentences_list:
                        first_sentence = sentences_list[0]
                        new_sentence_details.append({
                            'text': first_sentence['text'],
                            'code_id': first_code_number if first_code_number and first_code_number.isdigit() else
                            first_sentence['number'],
                            'sentence_id': first_code_number if first_code_number and first_code_number.isdigit() else
                            first_sentence['number'],
                            'original_content': first_sentence['text']
                        })

                    # 后续句子：关联的句子
                    for i in range(1, len(sentences_list)):
                        sentence = sentences_list[i]
                        new_sentence_details.append({
                            'text': sentence['text'],
                            'code_id': sentence['number'],
                            'sentence_id': sentence['number'],
                            'original_content': sentence['original_text'] if sentence['original_text'] else sentence[
                                'text']
                        })

                    # 更新当前选中项的数据
                    if current_item:
                        item_data = current_item.data(0, Qt.UserRole)
                        if item_data:
                            # 更新sentence_details
                            item_data['sentence_details'] = new_sentence_details
                            item_data['sentence_count'] = len(new_sentence_details)

                            # 更新内容（使用句子1的文本）
                            if sentences_list:
                                new_content = sentences_list[0]['text']
                                item_data['content'] = new_content
                                item_data['name'] = new_content

                            # 保存回树节点
                            current_item.setData(0, Qt.UserRole, item_data)

                            # 更新显示文本
                            display_text = f"{code_id} {sentences_list[0]['text']}" if sentences_list else f"{code_id}"
                            current_item.setText(0, display_text)

                            # 更新句子来源数
                            current_item.setText(4, str(len(new_sentence_details)))

                            # 更新关联编号
                            all_numbers = []
                            if first_code_number and first_code_number.isdigit():
                                all_numbers.append(first_code_number)
                            for i in range(1, len(sentences_list)):
                                num = sentences_list[i].get('number', '')
                                if num and num.isdigit() and num not in all_numbers:
                                    all_numbers.append(num)

                            if all_numbers:
                                all_numbers.sort(key=lambda x: int(x))
                                current_item.setText(5, ", ".join(all_numbers) + ",")

                    # 数据同步：更新整体数据结构
                    self.update_structured_codes_from_tree()

                except Exception as e:
                    logger.error(f"更新sentence_details失败: {e}")
                    import traceback
                    traceback.print_exc()

            # 设置右键菜单
            text_display.setContextMenuPolicy(Qt.CustomContextMenu)
            text_display.customContextMenuRequested.connect(show_context_menu)

            view_layout.addWidget(text_display)

            # 主按钮布局
            main_button_layout = QHBoxLayout()
            main_button_layout.addStretch()

            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(dialog.close)
            main_button_layout.addWidget(close_btn)

            layout.addLayout(main_button_layout)
            layout.addWidget(view_page)

            # 显示对话框（非模态）
            dialog.show()

        except Exception as e:
            logger.error(f"显示句子详情对话框时出错: {e}")
            import traceback
            traceback.print_exc()
            # 不弹出错误消息框，避免闪退
            try:
                QMessageBox.warning(self, "错误", f"显示句子详情时发生错误: {str(e)}")
            except:
                pass  # 如果连错误消息框都失败，也不要崩溃

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

        # 根据当前选中节点动态添加"修改父节点"选项
        clicked_item = self.coding_tree.itemAt(position)
        if clicked_item:
            clicked_data = clicked_item.data(0, Qt.UserRole)
            if clicked_data:
                clicked_level = clicked_data.get("level")
                clicked_parent = clicked_item.parent()

                # 一阶：无论是否已分类，都允许修改父二阶节点
                if clicked_level == 1:
                    menu.addSeparator()
                    move_first_action = QAction("修改一阶对应父节点(二阶)", self)
                    move_first_action.triggered.connect(self.move_first_to_new_parent_second)
                    menu.addAction(move_first_action)

                # 二阶：无论是否已分类，都允许修改父三阶节点
                elif clicked_level == 2:
                    menu.addSeparator()
                    move_second_action = QAction("修改二阶对应父节点(三阶)", self)
                    move_second_action.triggered.connect(self.move_second_to_new_parent_third)
                    menu.addAction(move_second_action)

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
            msg = f"确定要删除三阶编码 '{content}' 吗？\n删除后，其下的 {child_count} 个二阶编码将变为未分类状态。"
        elif level == 2:
            child_count = current_item.childCount()
            msg = f"确定要删除二阶编码 '{content}' 及其下的 {child_count} 个一阶编码吗？"
        else:
            msg = f"确定要删除一阶编码 '{content}' 吗？"

        reply = QMessageBox.question(self, "确认删除", msg, QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            parent = current_item.parent()

            # 处理三阶编码删除的情况：将其二阶子节点移到顶层
            if level == 3:
                # 收集所有二阶子节点
                second_level_items = []
                while current_item.childCount() > 0:
                    second_item = current_item.takeChild(0)
                    second_level_items.append(second_item)

                # 将二阶子节点移到顶层
                for item in second_level_items:
                    self.coding_tree.addTopLevelItem(item)

                # 为未分类的二阶编码重新编序
                self.reorder_unclassified_second_codes()

            # 移除当前节点
            if parent:
                parent.removeChild(current_item)
                # 更新父级节点的句子来源数
                self.update_statistics_for_item(parent)
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
                            # 注意：不要用关联编号（第5列）覆盖code_id，code_id应该是A01这样的编码ID
                            # 关联编号是句子编号列表（如"2538, 2539"），应该单独保存
                            if "code_id" not in first_item_data or not first_item_data["code_id"]:
                                # 只有当code_id不存在时才尝试从显示文本中提取
                                import re
                                first_display_text = first_item.text(0)
                                match = re.match(r'^(A\d+)', first_display_text)
                                if match:
                                    first_item_data["code_id"] = match.group(1)
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
                        # 注意：不要用关联编号（第5列）覆盖code_id
                        if "code_id" not in item_data or not item_data["code_id"]:
                            # 只有当code_id不存在时才尝试从显示文本中提取
                            import re
                            top_display_text = top_item.text(0)
                            match = re.match(r'^(A\d+)', top_display_text)
                            if match:
                                item_data["code_id"] = match.group(1)
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
                            # 优先使用content字段，其次使用name字段
                            if 'content' in content:
                                content_text = content.get('content', '')
                            elif 'name' in content:
                                content_text = content.get('name', '')
                            else:
                                # 如果都没有，使用字符串表示
                                content_text = str(content)
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
                        # 与自动编码界面保持一致，显示句子ID
                        associated_id = ""

                        # 收集所有可能的句子ID
                        all_ids = set()

                        # 从first_sentence_sources提取
                        all_ids.update(first_sentence_sources)

                        # 从sentence_details提取
                        if not all_ids and sentence_details:
                            for s in sentence_details:
                                if isinstance(s, dict) and s.get('sentence_id'):
                                    all_ids.add(str(s.get('sentence_id')))

                        # 方法：从sentence_details的原始内容提取（与主窗口相同的逻辑）
                        extracted_sentence_ids = []
                        if sentence_details:
                            for sentence in sentence_details:
                                if isinstance(sentence, dict):
                                    # 尝试从各个字段获取内容
                                    sent_content = sentence.get('original_content', '') or sentence.get('content', '')
                                    if not sent_content:
                                        continue

                                    # 清理内容：移除所有标记，只保留纯文本
                                    sent_content_clean = re.sub(r'\s*\[[A-Z]\d+\]', '', sent_content)
                                    sent_content_clean = re.sub(r'\s*\[\d+\]', '', sent_content_clean)
                                    sent_content_clean = sent_content_clean.strip()

                                    # 如果清理后的内容太短，跳过
                                    if len(sent_content_clean) < 5:
                                        continue

                                    # 在所有已加载文件的numbered_content中查找
                                    for file_path_iter, file_data_iter in self.loaded_files.items():
                                        file_numbered = file_data_iter.get('numbered_content', '')
                                        if not file_numbered:
                                            continue

                                        # 尝试查找句子内容
                                        # 方法1：直接查找
                                        pos = file_numbered.find(sent_content_clean)

                                        # 方法2：如果方法1失败，尝试查找前50个字符
                                        if pos < 0 and len(sent_content_clean) > 50:
                                            pos = file_numbered.find(sent_content_clean[:50])

                                        # 方法3：如果还失败，尝试去除所有空白后查找
                                        if pos < 0:
                                            sent_no_space = re.sub(r'\s+', '', sent_content_clean)
                                            file_no_space = re.sub(r'\s+', '', file_numbered)
                                            pos_no_space = file_no_space.find(sent_no_space)
                                            if pos_no_space >= 0:
                                                # 找到了，但需要转换回原始位置
                                                # 简化处理：直接在原文中用正则匹配
                                                pattern = re.escape(
                                                    sent_content_clean[:min(30, len(sent_content_clean))])
                                                match = re.search(pattern, file_numbered)
                                                if match:
                                                    pos = match.start()

                                        if pos >= 0:
                                            # 向后查找紧跟在句子后的编号 [N]
                                            text_after_start = pos + len(sent_content_clean)
                                            text_after = file_numbered[text_after_start:text_after_start + 100]

                                            # 查找紧跟的第一个 [数字]
                                            # 允许中间有标点符号
                                            match = re.search(r'^[。！？!?]?\s*\[(\d+)\]', text_after)
                                            if match:
                                                sentence_id = match.group(1)
                                                if sentence_id not in extracted_sentence_ids:
                                                    extracted_sentence_ids.append(sentence_id)
                                                break  # 找到了就不再查找其他文件

                        # 从提取的句子编号添加
                        if not all_ids:
                            all_ids.update(extracted_sentence_ids)

                        # 从numbered_content提取
                        if not all_ids and numbered_first_content:
                            import re
                            match = re.search(r'^\s*\[(\d+)\]', numbered_first_content.strip())
                            if match:
                                all_ids.add(match.group(1))

                        if all_ids:
                            # 格式化显示句子编号，纯数字格式（如 1, 2, 3）
                            ids = sorted(all_ids, key=lambda x: int(x) if x.isdigit() else float('inf'))
                            # 移除可能的括号，只保留数字
                            clean_ids = [sid.strip('[]') if isinstance(sid, str) else str(sid) for sid in ids]
                            associated_id = ", ".join(clean_ids)

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
                # 计算三阶编码的句子来源数：累加所有子二阶编码的句子来源数
                total_third_sentence_count = 0
                # 遍历该三阶编码下的所有二阶编码
                for j in range(third_item.childCount()):
                    second_child_item = third_item.child(j)
                    # 获取二阶编码的句子来源数（第4列）
                    second_sentence_count_str = second_child_item.text(4)
                    if second_sentence_count_str and second_sentence_count_str.isdigit():
                        total_third_sentence_count += int(second_sentence_count_str)

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
                    # 与自动编码界面保持一致，显示句子ID
                    associated_id = ""

                    # 收集所有可能的句子ID
                    all_ids = set()

                    # 从first_sentence_sources提取
                    all_ids.update(first_sentence_sources)

                    # 从sentence_details提取
                    if not all_ids and sentence_details:
                        for s in sentence_details:
                            if isinstance(s, dict) and s.get('sentence_id'):
                                all_ids.add(str(s.get('sentence_id')))

                    # 从numbered_content提取
                    if not all_ids and numbered_content:
                        import re
                        match = re.search(r'^\s*\[(\d+)\]', numbered_content.strip())
                        if match:
                            all_ids.add(match.group(1))

                    if all_ids:
                        # 格式化显示句子编号，纯数字格式（如 1, 2, 3）
                        ids = sorted(all_ids, key=lambda x: int(x) if x.isdigit() else float('inf'))
                        # 移除可能的括号，只保留数字
                        clean_ids = [sid.strip('[]') if isinstance(sid, str) else str(sid) for sid in ids]
                        associated_id = ", ".join(clean_ids)

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

    def generate_second_code_id(self, third_letter="B", parent_node=None):
        """生成二阶编码ID：B01, B02...（修复：独立二阶只在未分类中计数）"""
        existing_second_numbers = []
        import re

        if parent_node:
            # Case 1: 指定了父节点（三阶），统计该节点下的二阶
            for j in range(parent_node.childCount()):
                second_item = parent_node.child(j)
                second_data = second_item.data(0, Qt.UserRole)
                if second_data and second_data.get("level") == 2:
                    second_name = second_item.text(0)
                    # 兼容 B01 或 B01 维度名称
                    match = re.search(f"{third_letter}(\\d{{2}})", second_name)
                    if match:
                        existing_second_numbers.append(int(match.group(1)))
        else:
            # Case 2: 未指定父节点（独立二阶），只统计顶层的二阶
            # 关键修改：此时只统计同样是独立二阶（Top Level）的编码，不再统计三阶下的二阶
            for i in range(self.coding_tree.topLevelItemCount()):
                item = self.coding_tree.topLevelItem(i)
                item_data = item.data(0, Qt.UserRole)

                # 只检查 Level 2 的项
                if item_data and item_data.get("level") == 2:
                    second_name = item.text(0)
                    match = re.match(r'^([A-Z])(\d{2})', second_name.split(' ')[0])
                    if match:
                        letter = match.group(1)
                        number = int(match.group(2))
                        if letter == third_letter:
                            existing_second_numbers.append(number)

        # 找到下一个可用的编号
        if existing_second_numbers:
            next_number = max(existing_second_numbers) + 1
        else:
            next_number = 1

        return f"{third_letter}{next_number:02d}"

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
            save_dir = PathManager.get_manual_coding_save_dir()
            PathManager.ensure_dir(save_dir)

            # 获取当前编码进度信息
            progress_info = self.get_current_coding_progress()

            # 生成保存文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"手动编码_{timestamp}.json"
            file_path = PathManager.join(save_dir, filename)

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
            with PathManager.safe_open(file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            # 根据当前的三级编码结构，增量更新二阶三阶库
            try:
                if self.current_codes:
                    code_library = CodeLibrary("二阶三阶库.txt")
                    changed = code_library.update_with_structured_codes(self.current_codes)
                    if changed:
                        code_library.save()
                        logger.info("已根据手动编码结果更新二阶三阶库")
            except Exception as update_err:
                # 不阻断保存流程，仅记录日志
                logger.error(f"更新二阶三阶库失败: {update_err}")

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
            position_file = PathManager.get_last_position_file()
            PathManager.ensure_dir(os.path.dirname(position_file))

            with PathManager.safe_open(position_file, 'w', encoding='utf-8') as f:
                json.dump(progress_info, f, ensure_ascii=False, indent=2)

            logger.info("最后编码位置已保存")

        except Exception as e:
            logger.error(f"保存最后编码位置失败: {e}")

    def restore_last_coding_position(self):
        """恢复到上次编码的位置"""
        try:
            position_file = PathManager.get_last_position_file()
            if not PathManager.exists(position_file):
                return

            with PathManager.safe_open(position_file, 'r', encoding='utf-8') as f:
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
            position_file = PathManager.get_last_position_file()
            if not PathManager.exists(position_file):
                return  # 没有上次的进度文件

            with PathManager.safe_open(position_file, 'r', encoding='utf-8') as f:
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
        try:
            # 确保数据是最新的
            self.update_structured_codes_from_tree()

            # 更严格的检查条件
            if not self.current_codes and not self.unclassified_first_codes:
                QMessageBox.warning(self, "警告", "没有编码数据可导出\n\n请先添加至少一个编码")
                return

            # 准备导出数据
            export_data = {}

            # 处理已分类编码
            if self.current_codes:
                export_data = self._prepare_export_data(self.current_codes)

            # 处理未分类编码
            if not export_data and self.unclassified_first_codes:
                # 创建基本结构
                unclassified_data = []
                for item in self.unclassified_first_codes:
                    # 保留完整的一阶编码数据结构，包括sentence_details
                    if isinstance(item, dict):
                        # 确保content字段存在
                        if 'content' not in item and 'name' in item:
                            item['content'] = item['name']
                        unclassified_data.append(item)
                    else:
                        unclassified_data.append(str(item))
                export_data = {"未分类编码": {"未分类": unclassified_data}}

            # 检查导出数据是否有效
            if not export_data:
                QMessageBox.warning(self, "警告", "没有有效的编码数据可导出")
                return

            description, ok = QInputDialog.getText(self, "标准答案描述", "请输入本次标准答案的描述:")
            if ok:
                # 通过父窗口保存为标准答案
                parent = self.parent()
                if hasattr(parent, 'standard_answer_manager'):
                    try:
                        version_id = parent.standard_answer_manager.create_from_structured_codes(
                            export_data, description
                        )
                        if version_id:
                            # 重新加载刚创建的标准答案，确保编码树与标准答案完全一致
                            success = parent.standard_answer_manager.load_answers(f"{version_id}.json")
                            if success:
                                # 从标准答案管理器获取最新的编码数据
                                current_answers = parent.standard_answer_manager.get_current_answers()
                                if current_answers and "structured_codes" in current_answers:
                                    # 更新当前编码数据为标准答案中的数据
                                    self.current_codes = current_answers["structured_codes"]
                                    # 清空未分类编码，因为标准答案中不包含未分类编码
                                    self.unclassified_first_codes = []
                                    # 更新编码树显示，确保与标准答案完全一致
                                    self.update_coding_tree()
                                    # 显示成功消息
                                    QMessageBox.information(self, "成功", f"标准答案已导出: {version_id}\n编码树已更新为标准答案内容")
                                else:
                                    QMessageBox.warning(self, "警告", "标准答案数据格式不完整")
                            else:
                                QMessageBox.warning(self, "警告", "重新加载标准答案失败，编码树可能未完全更新")
                        else:
                            QMessageBox.critical(self, "错误", "导出失败")
                    except Exception as e:
                        logger.error(f"导出标准答案时出错: {e}")
                        QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
                else:
                    QMessageBox.critical(self, "错误", "父窗口缺少 standard_answer_manager\n\n请通过主界面启动手动编码功能")
        except Exception as e:
            logger.error(f"导出标准答案失败: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def _prepare_export_data(self, structured_codes):
        """准备导出数据，确保格式正确"""
        export_data = {}

        for third_cat, second_cats in structured_codes.items():
            export_data[third_cat] = {}

            for second_cat, first_contents in second_cats.items():
                export_data[third_cat][second_cat] = []

                for content in first_contents:
                    # 保留完整的一阶编码数据结构，包括sentence_details
                    if isinstance(content, dict):
                        # 确保content字段存在
                        if 'content' not in content and 'name' in content:
                            content['content'] = content['name']
                        export_data[third_cat][second_cat].append(content)
                    else:
                        # 直接使用字符串内容
                        export_data[third_cat][second_cat].append(str(content))

        return export_data

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
                # 如果没有找到编号，尝试从父窗口中的文本内容定位拖拽句子所在的完整句段
                text_content = self.text_display.toPlainText()
                if text_content:
                    found_number = self.find_sentence_number_from_text(clean_content, text_content)
                    if found_number:
                        tmng_number = found_number
                        sentence_id = tmng_number

            # 尝试获取当前选中的文件路径
            current_file_path = ""
            current_filename = ""
            if hasattr(self, 'file_list') and self.file_list.currentItem():
                current_file_path = self.file_list.currentItem().data(Qt.UserRole)
                if current_file_path:
                    current_filename = os.path.basename(current_file_path)

            # 创建句子详情
            sentence_details = [{
                "text": detail_text,
                "code_id": sentence_id,
                "file_path": current_file_path,
                "filename": current_filename,
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
                        # 找到了 [N]，检查后面是否已经有一阶编码标记
                        current_text = self.text_display.toPlainText()
                        found_pos = found_cursor.position() + len(target_marker)

                        # 查找 [N] 后面的一阶编码标记
                        marker_pos = current_text.find(" [A", found_pos)
                        if marker_pos != -1 and marker_pos < found_pos + 100:  # 限制搜索范围，避免影响其他内容
                            # 检查是否是完整的一阶编码标记
                            marker_end = current_text.find("]", marker_pos)
                            if marker_end != -1:
                                marker = current_text[marker_pos:marker_end + 1]
                                if re.match(r'\s*\[A\d+\]', marker):
                                    # 移除一阶编码标记
                                    remove_cursor = QTextCursor(found_cursor)
                                    remove_cursor.setPosition(marker_pos)
                                    remove_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(marker))
                                    remove_cursor.removeSelectedText()
                                    logger.info(f"已移除 [N] 后的一阶编码标记: {marker}")

                        # 检查后面是否已经有 [code_id]
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

            # 设置关联编号（不需要尾部逗号）
            item.setText(5, str(tmng_number) if str(tmng_number).isdigit() else "")  # 关联编号

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

    def find_sentence_number_from_text(self, sentence_text, full_text):
        """
        从父窗口中的文本内容定位拖拽句子所在的完整句段，并提取TextNumberingManager编号

        Args:
            sentence_text: 拖拽的句子文本
            full_text: 完整的文本内容（从text_display获取）

        Returns:
            str: 找到的句子编号，如果没找到则返回空字符串
        """
        try:
            import re

            # 清理输入文本，移除编号标记
            clean_sentence = re.sub(r'\s*\[\d+\]\s*', '', sentence_text).strip()
            clean_sentence = re.sub(r'\s+', ' ', clean_sentence)

            if not clean_sentence:
                return ""

            # 尝试多种方法查找句子，按优先级排序
            # 优先使用句子的后部分进行匹配，这样更准确
            search_text = clean_sentence[-min(50, len(clean_sentence)):] if len(clean_sentence) > 20 else clean_sentence

            # 在完整文本中查找匹配位置
            found_pos = full_text.find(search_text)

            if found_pos == -1:
                # 如果没找到，尝试使用完整句子匹配
                found_pos = full_text.find(clean_sentence)
                if found_pos == -1:
                    # 尝试使用部分匹配
                    if len(clean_sentence) > 10:
                        # 尝试使用句子的前半部分匹配
                        half_length = len(clean_sentence) // 2
                        search_text = clean_sentence[:half_length]
                        found_pos = full_text.find(search_text)
                        if found_pos == -1:
                            logger.warning(f"未在文本中找到句子: {clean_sentence[:50]}...")
                            return ""
                    else:
                        logger.warning(f"未在文本中找到句子: {clean_sentence[:50]}...")
                        return ""

            # 调整到句子开始位置
            start_pos = found_pos
            while start_pos > 0:
                if full_text[start_pos - 1] in ['。', '！', '？', '\n', '\u2029']:
                    break
                start_pos -= 1

            # 找到句子结束位置
            end_pos = found_pos + len(search_text)
            if len(search_text) < len(clean_sentence):
                # 如果使用了部分匹配，找到完整句子的结束
                temp_end = end_pos
                while temp_end < len(full_text):
                    if full_text[temp_end] in ['。', '！', '？', '\n', '\u2029']:
                        end_pos = temp_end + 1
                        break
                    temp_end += 1
            else:
                end_pos = found_pos + len(clean_sentence)

            # 向后查找编号，从句子结束位置开始
            temp_pos = end_pos
            total_len = len(full_text)

            # 跳过所有空格和换行，直到找到非空白字符
            while temp_pos < total_len:
                if full_text[temp_pos].isspace():
                    # 跳过所有空白字符，包括换行
                    temp_pos += 1
                else:
                    break

            # 检查是否有 [N] 编号
            if temp_pos < total_len and full_text[temp_pos] == '[':
                bracket_start = temp_pos
                temp_pos += 1
                number_str = ''
                while temp_pos < total_len and full_text[temp_pos].isdigit():
                    number_str += full_text[temp_pos]
                    temp_pos += 1
                if temp_pos < total_len and full_text[temp_pos] == ']' and number_str:
                    logger.info(f"找到句子编号: {number_str} for sentence: {clean_sentence[:30]}...")
                    return number_str

            # 如果在当前位置没找到，继续向后查找，直到找到编号或结束
            # 这是关键修复：继续向后查找，而不是立即放弃
            while temp_pos < total_len:
                # 查找下一个 [ 符号
                bracket_pos = full_text.find('[', temp_pos)
                if bracket_pos == -1:
                    break

                # 检查 [ 后面是否是数字
                temp_pos = bracket_pos + 1
                number_str = ''
                while temp_pos < total_len and full_text[temp_pos].isdigit():
                    number_str += full_text[temp_pos]
                    temp_pos += 1

                # 检查是否有对应的 ]
                if temp_pos < total_len and full_text[temp_pos] == ']' and number_str:
                    logger.info(f"向后找到句子编号: {number_str} for sentence: {clean_sentence[:30]}...")
                    return number_str

            # 如果还是没找到，尝试向前查找
            temp_pos = start_pos
            while temp_pos > 0:
                # 查找前一个 ] 符号
                bracket_pos = full_text.rfind(']', 0, temp_pos)
                if bracket_pos == -1:
                    break

                # 向前查找对应的 [ 符号
                open_bracket_pos = full_text.rfind('[', 0, bracket_pos)
                if open_bracket_pos == -1:
                    temp_pos = bracket_pos - 1
                    continue

                # 提取数字
                number_str = full_text[open_bracket_pos + 1:bracket_pos]
                if number_str.isdigit():
                    logger.info(f"向前找到句子编号: {number_str} for sentence: {clean_sentence[:30]}...")
                    return number_str

                temp_pos = open_bracket_pos - 1

            # 如果所有方法都没找到，返回空字符串
            logger.warning(f"无法提取句子编号: {clean_sentence[:50]}...")
            return ""

        except Exception as e:
            logger.error(f"从文本中查找句子编号时出错: {e}")
            return ""

    def update_parent_sentence_counts(self, item):
        """递归更新父级节点的句子来源数"""
        try:
            if not item:
                return

            parent = item.parent()
            if not parent:
                return

            parent_data = parent.data(0, Qt.UserRole)
            if not parent_data:
                return

            level = parent_data.get("level")

            if level == 2:
                # 父节点是二阶编码，计算所有子一阶编码的句子来源数总和
                total_count = 0
                for i in range(parent.childCount()):
                    child = parent.child(i)
                    child_sentence_count_str = child.text(4)  # 第4列是句子来源数
                    if child_sentence_count_str and child_sentence_count_str.isdigit():
                        total_count += int(child_sentence_count_str)

                parent.setText(4, str(total_count))
                logger.info(f"更新二阶编码 '{parent.text(0)}' 的句子来源数为: {total_count}")

                # 继续向上更新祖父节点（三阶编码）
                self.update_parent_sentence_counts(parent)

            elif level == 3:
                # 父节点是三阶编码，计算所有子二阶编码的句子来源数总和
                total_count = 0
                for i in range(parent.childCount()):
                    child = parent.child(i)
                    child_sentence_count_str = child.text(4)  # 第4列是句子来源数
                    if child_sentence_count_str and child_sentence_count_str.isdigit():
                        total_count += int(child_sentence_count_str)

                parent.setText(4, str(total_count))
                logger.info(f"更新三阶编码 '{parent.text(0)}' 的句子来源数为: {total_count}")

        except Exception as e:
            logger.error(f"更新父级句子来源数失败: {e}")
            import traceback
            traceback.print_exc()

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

                # 首先从拖拽的文本中提取编号
                import re
                current_text_content = self.text_display.toPlainText()

                for sentence in sentences:
                    sentence_stripped = sentence.strip()

                    # 从完整句子中提取编号 [N]
                    number_match = re.search(r'\[(\d+)\]', sentence_stripped)
                    if number_match:
                        sentence_number = number_match.group(1)
                        associated_code_ids.append(sentence_number)
                    else:
                        # 如果没有找到编号，从父窗口中的文本内容定位拖拽句子所在的完整句段
                        sentence_number = self.find_sentence_number_from_text(sentence_stripped, current_text_content)
                        associated_code_ids.append(sentence_number)

                # 获取目标项的当前数据
                target_item_data = item.data(0, Qt.UserRole)
                if target_item_data is None:
                    target_item_data = {}

                # 从目标项的显示文本中提取一阶编码文本内容和编号
                target_text = item.text(0)
                code_id = target_item_data.get('code_id', '')

                # 提取纯内容（去除 code_id 前缀）
                pure_content = target_text
                if code_id and pure_content.startswith(code_id):
                    if pure_content.startswith(code_id + ': '):
                        pure_content = pure_content[len(code_id + ': '):]
                    elif pure_content.startswith(code_id + ' '):
                        pure_content = pure_content[len(code_id + ' '):]

                # 清理纯内容，移除编号标记
                content_without_number = re.sub(r'\s*\[[A-Z]\d+\]', '', pure_content)
                content_without_number = re.sub(r'\s*\[\d+\]', '', content_without_number)
                content_without_number = content_without_number.strip()

                # 获取一阶编码文本的编号（一阶编码自身对应的句子编号）
                # 修复：优先从当前关联编号中获取一阶编码原有的句子编号
                first_code_number = ""
                existing_sentence_details = target_item_data.get("sentence_details", [])

                # 策略1：从当前显示的关联编号中获取（最可靠）
                current_code_ids = item.text(5)  # 关联编号列
                logger.info(f"拖拽前的关联编号: '{current_code_ids}'")
                if current_code_ids:
                    # 从当前关联编号中取第一个作为一阶编码自身的句子编号
                    ids = [id.strip() for id in current_code_ids.split(',') if id.strip() and id.strip().isdigit()]
                    if ids:
                        first_code_number = ids[0]  # 使用第一个作为一阶编码自身句子编号
                        logger.info(f"从当前关联编号获取一阶编码自身句子编号: {first_code_number} (全部编号: {ids})")

                # 策略2：如果没有关联编号，从sentence_details获取
                if not first_code_number and existing_sentence_details and len(existing_sentence_details) > 0:
                    first_detail = existing_sentence_details[0]
                    first_code_number = first_detail.get("code_id", "") or first_detail.get("sentence_id", "")
                    # 确保获取的是数字编号，不是编码标识符
                    if first_code_number and first_code_number.isdigit():
                        logger.info(f"从sentence_details获取一阶编码自身句子编号: {first_code_number}")
                    else:
                        first_code_number = ""  # 清空无效编号

                logger.info(f"最终确定的一阶编码自身句子编号: {first_code_number}")

                # 更新目标项的句子详情，添加拖拽的文本和编号
                # 先收集所有已有的句子编号，避免重复
                existing_numbers = set()
                if existing_sentence_details:
                    for detail in existing_sentence_details:
                        existing_num = detail.get('code_id', '')
                        if existing_num and existing_num.isdigit():
                            existing_numbers.add(existing_num)

                # 获取当前文本文档路径，用于关联拖拽的句子
                current_file_path = ""
                file_item = self.file_list.currentItem()
                if file_item:
                    current_file_path = file_item.data(Qt.UserRole)
                current_filename = os.path.basename(current_file_path) if current_file_path else ""

                # 为每个拖拽的句子创建详情
                new_sentences = []
                for i, sentence in enumerate(sentences):
                    code_id = associated_code_ids[i] if i < len(associated_code_ids) else ""
                    if code_id and code_id.isdigit() and code_id not in existing_numbers:
                        # 清理句子内容，移除编号标记
                        import re
                        clean_sentence = re.sub(r'\s*\[[A-Z]\d+\]', '', sentence)
                        clean_sentence = re.sub(r'\s*\[\d+\]', '', clean_sentence)
                        clean_sentence = clean_sentence.strip()

                        new_sentence_data = {
                            "text": clean_sentence,
                            "code_id": code_id,  # 使用TextNumberingManager生成的编号
                            "sentence_id": code_id,  # 设置sentence_id为文本编号
                            "file_path": current_file_path,  # 添加文件路径
                            "filename": current_filename     # 添加文件名
                        }

                        new_sentences.append(new_sentence_data)
                        existing_numbers.add(code_id)
                        logger.info(f"添加新拖拽句子: code_id={code_id}, text={clean_sentence[:30]}..., file={current_filename}")

                # 重新构建完整的句子详情列表
                # 确保第一项始终是一阶编码自身，后续是其他句子
                new_sentence_details = []

                # 1. 添加一阶编码自身（第一项）
                if existing_sentence_details and len(existing_sentence_details) > 0:
                    # 使用现有的第一项，但更新文本内容，确保保留原有的句子编号
                    first_item = existing_sentence_details[0].copy()
                    first_item["text"] = content_without_number
                    # 确保一阶编码自身的句子编号正确（不是A01这种编码标识符）
                    if not first_item.get("code_id", "") or not first_item.get("code_id", "").isdigit():
                        if first_code_number and first_code_number.isdigit():
                            first_item["code_id"] = first_code_number
                            first_item["sentence_id"] = first_code_number
                    new_sentence_details.append(first_item)
                    logger.info(f"保留现有第一项，句子编号: {first_item.get('code_id', 'N/A')}")
                else:
                    # 创建新的第一项，使用正确的句子编号
                    new_sentence_details.append({
                        "text": content_without_number,
                        "code_id": first_code_number if first_code_number and first_code_number.isdigit() else "",
                        "sentence_id": first_code_number if first_code_number and first_code_number.isdigit() else ""
                    })
                    logger.info(f"创建新的第一项，句子编号: {first_code_number}")

                # 2. 添加其他已存在的句子（跳过第一项）
                if existing_sentence_details and len(existing_sentence_details) > 1:
                    for detail in existing_sentence_details[1:]:
                        new_sentence_details.append(detail)

                # 3. 添加新拖拽的句子
                new_sentence_details.extend(new_sentences)

                # 4. 按句子编号排序（第一项保持不动）
                if len(new_sentence_details) > 1:
                    first_item = new_sentence_details[0]  # 保存第一项
                    other_items = new_sentence_details[1:]  # 其余项目排序
                    other_items.sort(key=lambda x: int(x.get('code_id', '0')) if x.get('code_id', '').isdigit() else 0)
                    new_sentence_details = [first_item] + other_items

                # 更新target_item_data
                target_item_data["sentence_details"] = new_sentence_details

                # 调试日志：输出完整的sentence_details
                logger.info(f"完整更新后的sentence_details (共{len(new_sentence_details)}个):")
                for idx, s in enumerate(new_sentence_details):
                    logger.info(f"  句子{idx + 1}: code_id={s.get('code_id', 'N/A')}, text={s.get('text', '')[:30]}...")

                # 更新目标项的句子来源数（第4列）
                total_sentences = len(new_sentence_details)
                item.setText(4, str(total_sentences))
                # 同时更新数据结构中的句子数
                target_item_data["sentence_count"] = total_sentences

                # 更新目标项的关联编号（第5列）
                # 修复：确保一阶编码自身的编号在关联编号的第一位
                if new_sentence_details and len(new_sentence_details) > 0:
                    # 一阶编码自身的编号（第一项）
                    first_level_code_id = new_sentence_details[0].get('code_id', '')

                    # 收集其他句子的编号（除了一阶编码自身）
                    other_ids = []
                    for detail in new_sentence_details[1:]:
                        code_id = detail.get('code_id', '')
                        if code_id and code_id.isdigit() and code_id not in other_ids:
                            other_ids.append(code_id)

                    # 对其他编号进行排序
                    other_ids.sort(key=lambda x: int(x))

                    # 组合编号：一阶编码自身编号 + 其他编号
                    all_ids = []
                    if first_level_code_id and first_level_code_id.isdigit():
                        all_ids.append(first_level_code_id)
                    all_ids.extend(other_ids)

                    updated_code_ids = ", ".join(all_ids) if all_ids else ""
                else:
                    updated_code_ids = ""

                item.setText(5, updated_code_ids)

                logger.info(
                    f"修复关联编号显示 - 一阶编码自身编号: {first_level_code_id if 'first_level_code_id' in locals() else 'N/A'}")
                logger.info(f"修复关联编号显示 - 其他编号: {other_ids if 'other_ids' in locals() else []}")
                logger.info(f"修复关联编号显示 - 最终关联编号: {updated_code_ids}")

                logger.info(f"更新关联编号: {updated_code_ids}")

                # 更新目标项的数据
                item.setData(0, Qt.UserRole, target_item_data)

                # 更新父级节点的句子来源数（二阶和三阶编码）
                self.update_parent_sentence_counts(item)

                self.update_structured_codes_from_tree()

                logger.info(
                    f"通过拖放将{len(new_sentences)}个句子关联到一阶编码: {item.text(0)}，关联编号: {', '.join(associated_code_ids)}")
                self.statusBar().showMessage(
                    f"通过拖放将{len(new_sentences)}个句子关联到一阶编码，关联编号: {', '.join(associated_code_ids)}") if hasattr(self,
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

                    # 更新父节点（二阶）及其祖先（三阶）的统计信息
                    self.update_statistics_for_item(item)

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
        """在文本中添加编码标记（只保留一阶编码对应的一阶编号，其余去除）"""
        try:
            current_text = self.text_display.toPlainText()

            # 清理文本中的一阶编码标记（如 [A1], [A2] 等）
            clean_text_to_mark = re.sub(r'\s*\[A\d+\]', '', text_to_mark).strip()

            # 查找清理后的文本在当前文档中的位置
            start_pos = current_text.find(clean_text_to_mark)
            if start_pos != -1:
                # 创建一个文本光标
                cursor = self.text_display.textCursor()

                # 选择找到的文本
                cursor.setPosition(start_pos)
                cursor.movePosition(cursor.Right, cursor.KeepAnchor, len(clean_text_to_mark))

                # 获取选中的文本以确认匹配
                if cursor.selectedText() == clean_text_to_mark:
                    # 检查选中的文本后面是否已经有一阶编码标记
                    check_cursor = QTextCursor(cursor)
                    check_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(f" [{code_id}]"))
                    if check_cursor.selectedText() != f" [{code_id}]":
                        # 清理选中的文本后面的一阶编码标记
                        next_pos = cursor.position() + len(clean_text_to_mark)
                        check_cursor2 = QTextCursor(cursor)
                        check_cursor2.setPosition(next_pos)

                        # 查找并移除后面的一阶编码标记
                        while True:
                            # 查找下一个一阶编码标记
                            marker_pos = current_text.find(" [A", next_pos)
                            if marker_pos == -1 or marker_pos > next_pos + 100:  # 限制搜索范围，避免影响其他内容
                                break

                            # 检查是否是完整的一阶编码标记
                            marker_end = current_text.find("]", marker_pos)
                            if marker_end != -1:
                                marker = current_text[marker_pos:marker_end + 1]
                                if re.match(r'\s*\[A\d+\]', marker):
                                    # 移除一阶编码标记
                                    remove_cursor = QTextCursor(cursor)
                                    remove_cursor.setPosition(marker_pos)
                                    remove_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(marker))
                                    remove_cursor.removeSelectedText()
                                    current_text = self.text_display.toPlainText()  # 更新当前文本
                                    break

                        # 在选中文本后添加一阶编码标记
                        cursor.insertText(f"{clean_text_to_mark} [{code_id}]")
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