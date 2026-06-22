"""WorkspacePage — 扎根理论编码工作台 v4.0

用户日常编码分析界面，通过 QStackedWidget 与 DeveloperPage 并列。
所有数据和方法通过 self.mw (MainWindow 实例) 访问。
"""

import logging
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QTextEdit,
    QToolBar, QAction, QStatusBar, QShortcut,
    QPushButton, QMenu, QMenuBar, QMessageBox, QLineEdit,
    QLabel, QFrame, QApplication, QHeaderView, QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData
from PyQt5.QtGui import QFont, QKeySequence, QColor, QTextCursor, QIcon

logger = logging.getLogger(__name__)


class WorkspacePage(QWidget):
    """工作台页面 — 简洁的日常编码分析界面"""

    switch_to_developer_requested = pyqtSignal()

    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self._init_ui()
        self._setup_shortcuts()

    def _init_ui(self):
        """构建 Workspace 布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 全局主题
        self._apply_theme()

        # 菜单栏（作为属性保存，供 MainWindow 切换用）
        self.menu_bar = self._create_menu_bar()

        # 工具栏
        main_layout.addWidget(self._create_toolbar())

        # 三栏分割器
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setStyleSheet(
            "QSplitter::handle { background-color: #D9D0C1; margin: 0 2px; }"
        )

        self.file_tree = self._create_file_tree()
        self.splitter.addWidget(self.file_tree)

        self.text_display = self._create_text_area()
        self.splitter.addWidget(self.text_display)

        coding_panel = self._create_coding_panel()
        self.splitter.addWidget(coding_panel)

        self.splitter.setSizes([220, 800, 620])
        main_layout.addWidget(self.splitter, 1)

    def _apply_theme(self):
        """应用 'Editorial Scholar' 视觉主题"""
        self.setStyleSheet("""
            /* === 全局底色 === */
            QWidget {
                background-color: #F5F1EC;
                color: #2C2416;
                font-family: "Microsoft YaHei", "SimSun", sans-serif;
                font-size: 16px;
            }

            /* === 菜单栏 === */
            QMenuBar {
                background-color: #2C2416;
                color: #F5F1EC;
                padding: 2px 8px;
                border-bottom: 1px solid #1B4332;
            }
            QMenuBar::item {
                padding: 4px 12px;
                border-radius: 3px;
            }
            QMenuBar::item:selected {
                background-color: #1B4332;
            }
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #D9D0C1;
                padding: 4px;
            }
            QMenu::item {
                padding: 5px 28px 5px 14px;
            }
            QMenu::item:selected {
                background-color: #E8E0D5;
                color: #1B4332;
            }
            QMenu::separator {
                height: 1px;
                background: #D9D0C1;
                margin: 4px 8px;
            }

            /* === 树控件 === */
            QTreeWidget {
                background-color: #F5F1EC;
                border: 1px solid #D9D0C1;
                border-radius: 4px;
                alternate-background-color: #F0EBE4;
                padding: 2px;
            }
            QTreeWidget::item {
                padding: 6px 8px;
                font-size: 21px;
            }
            QTreeWidget::item:selected {
                background-color: #1B4332;
                color: #FFFFFF;
            }
            QTreeWidget::item:hover:!selected {
                background-color: #E8E0D5;
            }
            QHeaderView::section {
                background-color: #F5F1EC;
                color: #5C5344;
                border: none;
                border-bottom: 2px solid #1B4332;
                padding: 7px 8px;
                font-weight: bold;
                font-size: 18px;
            }

            /* === 搜索输入框 === */
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #D9D0C1;
                border-radius: 12px;
                padding: 5px 10px;
                min-height: 28px;
                font-size: 16px;
            }
            QLineEdit:focus {
                border-color: #1B4332;
            }

            /* === 标签 === */
            QLabel {
                color: #5C5344;
                font-size: 16px;
                font-weight: bold;
                padding: 5px 2px;
            }

            /* === 通用按钮 === */
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #D9D0C1;
                border-radius: 4px;
                padding: 6px 14px;
                color: #2C2416;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #E8E0D5;
                border-color: #1B4332;
            }
            QPushButton:pressed {
                background-color: #D9D0C1;
            }

            /* === GroupBox === */
            QGroupBox {
                font-weight: bold;
                color: #2C2416;
                border: 1px solid #D9D0C1;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                font-size: 16px;
            }
        """)

    # ===== Task 3: File Tree Panel =====

    def _create_file_tree(self):
        """创建文件树 — 支持拖拽导入、右键菜单"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        label = QLabel("文件列表")
        label.setStyleSheet(
            "QLabel {"
            "  color: #2C2416;"
            "  font-size: 16px;"
            "  font-weight: bold;"
            "}"
        )
        layout.addWidget(label)

        tree = QTreeWidget()
        tree.setHeaderLabels(["文件名"])
        tree.setColumnWidth(0, 180)
        tree.setAcceptDrops(True)
        tree.setDragEnabled(True)
        tree.setContextMenuPolicy(Qt.CustomContextMenu)
        tree.customContextMenuRequested.connect(
            lambda pos: self._on_file_tree_context_menu(tree, pos)
        )
        tree.itemClicked.connect(self._on_file_tree_clicked)

        # 支持拖拽导入文件
        tree.dragEnterEvent = self._make_file_tree_drag_enter(tree)
        tree.dropEvent = self._make_file_tree_drop(tree)

        layout.addWidget(tree, 1)
        return widget

    def _make_file_tree_drag_enter(self, tree):
        """生成 dragEnterEvent 处理器"""
        original = tree.dragEnterEvent

        def handler(event):
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
            else:
                original(event)

        return handler

    def _make_file_tree_drop(self, tree):
        """生成 dropEvent 处理器 — 从外部拖入文件"""
        original = tree.dropEvent

        def handler(event):
            if event.mimeData().hasUrls():
                from pathlib import Path
                paths = []
                for url in event.mimeData().urls():
                    p = url.toLocalFile()
                    if Path(p).exists():
                        paths.append(p)
                if paths:
                    self.mw._import_files_from_paths(paths)
                    self.refresh_file_tree()
                event.acceptProposedAction()
            else:
                original(event)

        return handler

    def _on_file_tree_clicked(self, item):
        """点击文件 — 在文本区显示内容"""
        if not item:
            return
        file_path = item.data(0, Qt.UserRole)
        if not file_path:
            return

        if hasattr(self.mw, 'auto_coding_cache') and file_path in self.mw.auto_coding_cache:
            self.text_display.setText(self.mw.auto_coding_cache[file_path])
            return

        if file_path in self.mw.loaded_files:
            file_data = self.mw.loaded_files[file_path]
            if 'numbered_content' in file_data and file_data['numbered_content']:
                self.text_display.setText(file_data['numbered_content'])
            else:
                self.text_display.setText(file_data['content'])

    def _on_file_tree_context_menu(self, tree, pos):
        """文件树右键菜单"""
        item = tree.itemAt(pos)
        menu = QMenu()
        if item:
            delete_action = menu.addAction("删除文件")
            copy_action = menu.addAction("复制文件名")
            jump_action = menu.addAction("跳转到文本位置")
            action = menu.exec_(tree.viewport().mapToGlobal(pos))
            if action == delete_action:
                self._delete_file(item)
            elif action == copy_action:
                QApplication.clipboard().setText(item.text(0))
            elif action == jump_action:
                tree.setCurrentItem(item)
                self._on_file_tree_clicked(item)
        else:
            import_action = menu.addAction("导入文件")
            if menu.exec_(tree.viewport().mapToGlobal(pos)) == import_action:
                self._on_import_files()

    def _delete_file(self, item):
        """删除文件"""
        file_path = item.data(0, Qt.UserRole)
        if file_path and file_path in self.mw.loaded_files:
            del self.mw.loaded_files[file_path]
            if file_path in self.mw.auto_coding_cache:
                del self.mw.auto_coding_cache[file_path]
            self.refresh_file_tree()
            self.text_display.clear()

    def refresh_file_tree(self):
        """刷新文件树"""
        logger.info("[WS-PAGE] refresh_file_tree START")
        tree = self.file_tree.findChild(QTreeWidget)
        if tree:
            tree.clear()
            for fp in self.mw.loaded_files:
                item = QTreeWidgetItem(tree)
                item.setText(0, os.path.basename(fp))
                item.setData(0, Qt.UserRole, fp)

    # ===== Task 4: Text Area & Coding Panel =====

    def _create_text_area(self):
        """创建文本工作区"""
        text = QTextEdit()
        text.setPlaceholderText("选择文件查看文本内容...")
        text.setAcceptDrops(False)
        text.setUndoRedoEnabled(False)  # 禁用文本区自带撤销，让 Ctrl+Z 传给 MainWindow
        text.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        # 自动选句事件过滤器在 MainWindow 完成初始化后延迟安装
        # （__init__ 期间 self.mw 的 text_display 尚未就绪会导致原生崩溃）
        # 用 stylesheet 覆盖全局 QWidget font-size，确保字体生效
        text.setStyleSheet(
            "QTextEdit {"
            "  font-family: SimSun;"
            "  font-size: 25px;"
            "  background-color: #F5F1EC;"
            "  border: 1px solid #D9D0C1;"
            "  border-radius: 4px;"
            "  padding: 8px;"
            "}"
        )

        # 右键菜单 — 选中文本添加一阶编码
        text.setContextMenuPolicy(Qt.CustomContextMenu)
        text.customContextMenuRequested.connect(self._on_text_context_menu)
        return text

    def _on_text_context_menu(self, pos):
        """文本区右键菜单"""
        menu = QMenu()
        if self.text_display.textCursor().hasSelection():
            add_code_action = menu.addAction("添加一阶编码")
            if menu.exec_(self.text_display.viewport().mapToGlobal(pos)) == add_code_action:
                self._on_add_first_level_code()

    def _create_coding_panel(self):
        """创建编码结构区 — 复用 DragDropTreeWidget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # 编码树 — 先创建，后续按钮需引用
        import main_window as mw_module
        DragDropTreeWidget = mw_module.DragDropTreeWidget
        self.coding_tree = DragDropTreeWidget()
        self.coding_tree.main_window = self.mw
        self.coding_tree.setHeaderLabels(["编码内容", "类型", "数量", "文件来源数", "句子来源数", "关联编号"])
        self.coding_tree.setColumnWidth(0, 450)
        self.coding_tree.setColumnWidth(1, 60)
        self.coding_tree.setColumnWidth(2, 60)
        self.coding_tree.setColumnWidth(3, 120)
        self.coding_tree.setColumnWidth(4, 120)
        self.coding_tree.setColumnWidth(5, 120)
        self.coding_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.coding_tree.itemClicked.connect(self._on_coding_tree_clicked)
        self.coding_tree.itemDoubleClicked.connect(self._on_coding_tree_double_clicked)
        self.coding_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.coding_tree.customContextMenuRequested.connect(
            self.mw.show_tree_context_menu
        )
        header = self.coding_tree.header()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setStyleSheet(
            "QHeaderView::section {"
            "  font-size: 20px;"
            "  padding: 6px 8px;"
            "}"
        )

        # 标题栏 + 展开/折叠按钮（同一行）
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("编码结构")
        title.setStyleSheet(
            "QLabel {"
            "  color: #2C2416;"
            "  font-size: 16px;"
            "  font-weight: bold;"
            "}"
        )
        header_layout.addWidget(title)
        header_layout.addStretch()

        tree_btn_style = (
            "QPushButton {"
            "  background-color: #FFFFFF;"
            "  color: #5C5344;"
            "  border: 1px solid #D9D0C1;"
            "  border-radius: 4px;"
            "  padding: 5px 12px;"
            "  font-size: 16px;"
            "}"
            "QPushButton:hover {"
            "  background-color: #E8E0D5;"
            "  border-color: #1B4332;"
            "  color: #1B4332;"
            "}"
        )
        expand_btn = QPushButton("展开全部")
        expand_btn.setStyleSheet(tree_btn_style)
        expand_btn.clicked.connect(self.coding_tree.expandAll)
        header_layout.addWidget(expand_btn)

        collapse_btn = QPushButton("折叠全部")
        collapse_btn.setStyleSheet(tree_btn_style)
        collapse_btn.clicked.connect(self.coding_tree.collapseAll)
        header_layout.addWidget(collapse_btn)

        layout.addLayout(header_layout)

        # 搜索栏
        search_layout = QHBoxLayout()
        search_layout.setSpacing(6)
        search_layout.setContentsMargins(0, 0, 0, 0)
        self.code_search_input = QLineEdit()
        self.code_search_input.setPlaceholderText("搜索一阶编码...")
        self.code_search_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.code_search_input.setStyleSheet(
            "QLineEdit {"
            "  font-size: 25px;"
            "  min-height: 40px;"
            "  padding: 6px 12px;"
            "}"
        )
        search_btn = QPushButton("\U0001f50d")
        search_btn.setFixedSize(50, 50)
        search_btn.setStyleSheet(
            "QPushButton {"
            "  border: 1px solid #D9D0C1;"
            "  border-radius: 15px;"
            "  background-color: #FFFFFF;"
            "  font-size: 28px;"
            "}"
            "QPushButton:hover {"
            "  background-color: #E8E0D5;"
            "}"
        )
        search_layout.addWidget(self.code_search_input)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)

        self.code_search_input.returnPressed.connect(self._on_search_code)
        search_btn.clicked.connect(self._on_search_code)

        layout.addWidget(self.coding_tree, 1)

        return widget

    def _on_coding_tree_clicked(self, item, column):
        """点击编码树节点 — 复用 MainWindow 的高亮逻辑，并同步左侧文件树"""
        # 1. 文本区高亮（通过临时替换 text_display 实现）
        saved_text_display = self.mw.text_display
        self.mw.text_display = self.text_display
        try:
            self.mw.on_tree_item_clicked(item, column)
        finally:
            self.mw.text_display = saved_text_display

        # 2. 同步左侧文件树 — MainWindow 只同步了它的 file_list (QListWidget)，
        #    而开发者界面的 file_tree (QTreeWidget) 需要独立同步
        self._sync_file_tree_to_coding_item(item)

    def _sync_file_tree_to_coding_item(self, item):
        """根据编码树点击的 item，在左侧文件树中高亮并定位对应文件"""
        import re
        item_data = item.data(0, Qt.UserRole)
        if not item_data or item_data.get("level") != 1:
            return

        # 提取句子内容 (与 main_window.on_tree_item_clicked 保持一致)
        content = None
        sentence_details = item_data.get("sentence_details", [])
        if sentence_details:
            first = sentence_details[0]
            content = first.get('original_content', '') or first.get('text', '') or first.get('content', '')
        if not content:
            content = item_data.get("content", "")
        if not content:
            return

        # 清理内容（去掉编号标记）
        clean_content = re.sub(r'\s*\[[A-Z]\d+\]', '', content)
        clean_content = re.sub(r'\s*\[\d+\]', '', clean_content)
        clean_content = re.sub(r'^[A-Z]\d+\s+', '', clean_content).strip()
        if not clean_content:
            return

        # 查找包含该内容的文件（使用正则匹配，允许标签出现在任意位置）
        target_file = None
        # 构建正则模式：在 clean_content 的每个字符之间插入可选的标签匹配
        pattern_parts = [re.escape(c) for c in clean_content if c.strip()]
        if not pattern_parts:
            return
        tag_pattern = r'(?:\s*(?:\[[A-Z]\d+\]|\[\d+\])?\s*)'
        regex_pattern = tag_pattern.join(pattern_parts)

        for file_path, file_data in self.mw.loaded_files.items():
            file_text = file_data.get('numbered_content', '') or file_data.get('content', '')
            if re.search(regex_pattern, file_text, re.DOTALL):
                target_file = file_path
                break

        if not target_file:
            # 降级方案：尝试使用前 20 个字符匹配
            short_content = clean_content[:20].strip()
            if len(short_content) > 5:
                short_pattern_parts = [re.escape(c) for c in short_content if c.strip()]
                short_regex = tag_pattern.join(short_pattern_parts)
                for file_path, file_data in self.mw.loaded_files.items():
                    file_text = file_data.get('numbered_content', '') or file_data.get('content', '')
                    if re.search(short_regex, file_text, re.DOTALL):
                        target_file = file_path
                        break

        if not target_file:
            return

        # 在 file_tree 中找到对应 item 并选中
        tree = self.file_tree.findChild(QTreeWidget)
        if not tree:
            return
        for i in range(tree.topLevelItemCount()):
            tree_item = tree.topLevelItem(i)
            if tree_item.data(0, Qt.UserRole) == target_file:
                tree.setCurrentItem(tree_item)
                break

    def _on_coding_tree_double_clicked(self, item, column):
        """双击编码树节点 — 显示详情"""
        self.mw.on_tree_item_double_clicked(item, column)

    def refresh_coding_tree(self):
        """刷新编码树"""
        logger.info("[WS-PAGE] refresh_coding_tree START")
        saved_tree = self.mw.coding_tree
        self.mw.coding_tree = self.coding_tree
        try:
            logger.info("[WS-PAGE] calling mw.update_coding_tree")
            self.mw.update_coding_tree(target_tree=self.coding_tree)
            logger.info("[WS-PAGE] mw.update_coding_tree DONE")
        finally:
            self.mw.coding_tree = saved_tree

    # ===== Task 5: Toolbar, Menus, Shortcuts =====

    def _create_toolbar(self):
        """创建工具栏 — 5个高频操作 + 开发者界面切换"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setStyleSheet(
            "QToolBar {"
            "  background-color: #2C2416;"
            "  spacing: 6px;"
            "  padding: 6px 10px;"
            "  border-bottom: 2px solid #1B4332;"
            "}"
        )

        btn_style = (
            "QPushButton {"
            "  background-color: #3D3529;"
            "  color: #FFF4E4;"
            "  border: 1px solid #5C5344;"
            "  border-radius: 5px;"
            "  padding: 11px 24px;"
            "  font-size: 18px;"
            "  font-weight: 500;"
            "}"
            "QPushButton:hover {"
            "  background-color: #4A4032;"
            "  border-color: #8B7E6B;"
            "  color: #FFFFFF;"
            "}"
            "QPushButton:pressed {"
            "  background-color: #1B4332;"
            "  color: #FFFFFF;"
            "}"
        )
        primary_btn_style = (
            "QPushButton {"
            "  background-color: #1B4332;"
            "  color: #FFFFFF;"
            "  border: none;"
            "  border-radius: 5px;"
            "  padding: 11px 26px;"
            "  font-size: 18px;"
            "  font-weight: bold;"
            "}"
            "QPushButton:hover {"
            "  background-color: #2D5A3F;"
            "}"
            "QPushButton:pressed {"
            "  background-color: #153629;"
            "}"
        )
        dev_btn_style = (
            "QPushButton {"
            "  background-color: #2A251E;"
            "  color: #FFECCF;"
            "  border: 1px solid #8B7E6B;"
            "  border-radius: 5px;"
            "  padding: 10px 22px;"
            "  font-size: 17px;"
            "}"
            "QPushButton:hover {"
            "  background-color: #4A4032;"
            "  color: #FFFFFF;"
            "  border-color: #C1B59F;"
            "}"
        )

        import_btn = QPushButton("\U0001f4c2  导入")
        import_btn.setStyleSheet(btn_style)
        import_btn.clicked.connect(self._on_import_files)
        import_btn.setMinimumHeight(40)

        auto_btn = QPushButton("⚡  自动编码")
        auto_btn.setStyleSheet(primary_btn_style)
        auto_btn.clicked.connect(self._on_auto_code)
        auto_btn.setMinimumHeight(40)

        add_btn = QPushButton("➕  添加编码")
        add_btn.setStyleSheet(btn_style)
        add_btn.clicked.connect(self._on_add_first_level_code)
        add_btn.setMinimumHeight(40)

        load_btn = QPushButton("\U0001f4e5  加载")
        load_btn.setStyleSheet(btn_style)
        load_btn.clicked.connect(lambda: self.mw.import_coding_result())
        load_btn.setMinimumHeight(40)

        self._export_btn = QPushButton("\U0001f4e4  导出")
        self._export_btn.setStyleSheet(btn_style)
        self._export_btn.clicked.connect(self._on_export)
        self._export_btn.setMinimumHeight(40)

        dev_btn = QPushButton("⚙  开发者界面")
        dev_btn.setStyleSheet(dev_btn_style)
        dev_btn.clicked.connect(self.switch_to_developer_requested.emit)
        dev_btn.setMinimumHeight(40)

        button_bar = QWidget()
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(10, 0, 10, 0)
        button_layout.setSpacing(8)

        buttons = [
            import_btn,
            auto_btn,
            add_btn,
            load_btn,
            self._export_btn,
            dev_btn,
        ]
        button_layout.addStretch(2)
        for index, btn in enumerate(buttons):
            button_layout.addWidget(btn)
            button_layout.addStretch(2)

        toolbar.addWidget(button_bar)

        return toolbar

    def _on_import_files(self):
        """导入文件 — 委托给 MainWindow"""
        self.mw.import_files()
        self.refresh_file_tree()
        self.mw._update_status_bar()

    def _on_auto_code(self):
        """自动编码 — 委托给 MainWindow"""
        self.mw.generate_codes_auto()
        self.refresh_coding_tree()
        self.mw._update_status_bar()

    def _on_add_first_level_code(self):
        """添加一阶编码 — 委托给 MainWindow"""
        self.mw.select_sentence_for_coding()

    def _on_search_code(self):
        """搜索一阶编码"""
        search_text = self.code_search_input.text().strip()
        if not search_text:
            return
        results = self.mw.search_first_level_codes(search_text)
        if results:
            self.mw.show_search_results(results, search_text)

    def _on_export(self):
        """导出结果 — 弹出导出格式选择菜单"""
        from PyQt5.QtWidgets import QMenu as QMenuLocal
        menu = QMenuLocal()
        json_action = menu.addAction("导出 JSON")
        word_action = menu.addAction("导出 Word")
        excel_action = menu.addAction("导出 Excel")
        menu.addSeparator()
        standard_answer_action = menu.addAction("导出为标准答案")
        action = menu.exec_(self._export_btn.mapToGlobal(
            self._export_btn.rect().bottomLeft()
        ))
        if action == json_action:
            self.mw.export_to_json()
        elif action == word_action:
            self.mw.export_to_word()
        elif action == excel_action:
            self.mw.export_to_excel()
        elif action == standard_answer_action:
            self.mw.create_standard_answer()

    def _create_menu_bar(self):
        """创建菜单栏 — 精简版（文件/编码/标准答案/导出/帮助）"""
        menubar = QMenuBar()
        self._rebuild_menu_bar(menubar)
        return menubar

    def _rebuild_menu_bar(self, menubar):
        """在给定的 menubar 上重建工作台菜单（用于切换回 Workspace 时恢复菜单）"""

        # === 文件 ===
        file_menu = menubar.addMenu("文件")
        import_action = QAction("导入文件", self)
        import_action.setShortcut(QKeySequence("Ctrl+O"))
        import_action.triggered.connect(self._on_import_files)
        file_menu.addAction(import_action)

        export_action = QAction("导出结果", self)
        export_action.setShortcut(QKeySequence("Ctrl+Shift+E"))
        export_action.triggered.connect(self._on_export_all)
        file_menu.addAction(export_action)

        file_menu.addSeparator()
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(QApplication.quit)
        file_menu.addAction(exit_action)

        # === 编码 ===
        coding_menu = menubar.addMenu("编码")
        manual_action = QAction("手动编码", self)
        manual_action.triggered.connect(self.mw.start_manual_coding)
        coding_menu.addAction(manual_action)

        auto_action = QAction("自动编码", self)
        auto_action.setShortcut(QKeySequence("Ctrl+E"))
        auto_action.triggered.connect(self._on_auto_code)
        coding_menu.addAction(auto_action)

        save_action = QAction("保存编码 (Ctrl+S)", self)
        save_action.triggered.connect(self.mw.save_coding)
        coding_menu.addAction(save_action)

        import_coding_action = QAction("导入编码结果 (Ctrl+A)", self)
        import_coding_action.triggered.connect(self.mw.import_coding_result)
        coding_menu.addAction(import_coding_action)

        # === 标准答案 ===
        answer_menu = menubar.addMenu("标准答案")
        create_action = QAction("新建标准答案", self)
        create_action.triggered.connect(self.mw.create_standard_answer)
        answer_menu.addAction(create_action)

        load_action = QAction("加载标准答案", self)
        load_action.triggered.connect(self.mw.load_standard_answer)
        answer_menu.addAction(load_action)

        merge_action = QAction("合并标准答案", self)
        merge_action.triggered.connect(self.mw.merge_standard_answers)
        answer_menu.addAction(merge_action)

        stats_action = QAction("查看统计", self)
        stats_action.triggered.connect(self._show_answer_stats)
        answer_menu.addAction(stats_action)

        # === 导出 ===
        export_menu = menubar.addMenu("导出")
        json_action = QAction("导出 JSON", self)
        json_action.triggered.connect(self.mw.export_to_json)
        export_menu.addAction(json_action)

        word_action = QAction("导出 Word", self)
        word_action.triggered.connect(self.mw.export_to_word)
        export_menu.addAction(word_action)

        excel_action = QAction("导出 Excel", self)
        excel_action.triggered.connect(self.mw.export_to_excel)
        export_menu.addAction(excel_action)
        
        standard_answer_action = QAction("导出为标准答案", self)
        standard_answer_action.triggered.connect(self.mw.create_standard_answer)
        export_menu.addAction(standard_answer_action)

        # === 帮助 ===
        help_menu = menubar.addMenu("帮助")
        shortcuts_action = QAction("快捷键说明", self)
        shortcuts_action.triggered.connect(self._show_shortcuts)
        help_menu.addAction(shortcuts_action)

        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        return menubar

    def _setup_shortcuts(self):
        """Workspace 独立快捷键 — 仅在 Workspace 可见时生效"""
        # Ctrl+S: 保存编码 — ApplicationShortcut 绕过文本区拦截
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.setContext(Qt.ApplicationShortcut)
        save_shortcut.activated.connect(self._on_save_coding)

        # Ctrl+A: 导入编码结果
        import_shortcut = QShortcut(QKeySequence("Ctrl+A"), self)
        import_shortcut.setContext(Qt.ApplicationShortcut)
        import_shortcut.activated.connect(self._on_import_coding)

        # Ctrl+Z: 撤回操作
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.setContext(Qt.ApplicationShortcut)
        undo_shortcut.activated.connect(self._on_undo_operation)

        # Ctrl+N: 添加一阶编码
        add_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        add_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        add_shortcut.activated.connect(self._on_add_first_level_code)

        # Ctrl+F: 搜索一阶编码
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        search_shortcut.activated.connect(lambda: self.code_search_input.setFocus())

    def keyPressEvent(self, event):
        """键盘事件处理 - 确保快捷键优先处理"""
        if event.matches(QKeySequence.Undo):
            self._on_undo_operation()
            event.accept()
            return
        elif event.matches(QKeySequence.New):
            self._on_add_first_level_code()
            event.accept()
            return
        super().keyPressEvent(event)

    def _is_workspace_visible(self):
        """ApplicationShortcut 守卫 — 仅在工作台可见时响应"""
        return self.mw.stacked_widget.currentWidget() is self

    def _on_save_coding(self):
        if self._is_workspace_visible():
            self.mw.save_coding()

    def _on_import_coding(self):
        if self._is_workspace_visible():
            self.mw.import_coding_result()

    def _on_undo_operation(self):
        """执行撤回操作 - 委托给 MainWindow"""
        if self._is_workspace_visible():
            self.mw.undo_operation()

    def _on_export_all(self):
        """导出结果（菜单项触发 — 弹出子菜单）"""
        from PyQt5.QtWidgets import QMenu as QMenuLocal
        menu = QMenuLocal()
        json_action = menu.addAction("导出 JSON")
        word_action = menu.addAction("导出 Word")
        excel_action = menu.addAction("导出 Excel")
        action = menu.exec_(self.mapToGlobal(self.rect().topLeft()))
        if action == json_action:
            self.mw.export_to_json()
        elif action == word_action:
            self.mw.export_to_word()
        elif action == excel_action:
            self.mw.export_to_excel()

    def _show_shortcuts(self):
        """显示快捷键说明 — 延迟避免菜单事件冲突"""
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, lambda: QMessageBox.information(
            self, "快捷键说明",
            "Ctrl+O         导入文件\n"
            "Ctrl+E         自动编码\n"
            "Ctrl+N         添加一阶编码\n"
            "Ctrl+F         搜索一阶编码\n"
            "Ctrl+S         保存编码\n"
            "Ctrl+A         导入编码结果\n"
            "Ctrl+Z         撤回操作\n"
            "Ctrl+Shift+E   导出结果"
        ))

    def _show_about(self):
        """显示关于 — 使用说明 — 延迟避免菜单事件冲突"""
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, lambda: QMessageBox.information(
            self, "关于 扎根理论编码分析系统",
            "使用流程：\n"
            "1. 导入文件 — 加载访谈文本\n"
            "2. 自动编码 — AI 生成一阶/二阶/三阶编码\n"
            "3. 手动编码修正 — 选中文本添加/调整编码\n"
            "4. 标准答案管理 — 新建/加载/合并标准答案\n"
            "5. 导出结果 — 导出为 JSON/Word/Excel\n\n"
            "编码完成后请导出为标准答案传给技术人员。"
        ))

    def _show_answer_stats(self):
        """显示标准答案统计 — 延迟到下一事件循环避免菜单事件冲突"""
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, lambda: self.mw.show_answer_statistics())

    # ===== Public API =====

    def refresh_all(self):
        """刷新全部 — 切换回 Workspace 时调用"""
        logger.info("[WS-PAGE] refresh_all START")
        self.refresh_file_tree()
        logger.info("[WS-PAGE] refresh_file_tree DONE, starting coding_tree")
        self.refresh_coding_tree()
        logger.info("[WS-PAGE] refresh_all DONE")
