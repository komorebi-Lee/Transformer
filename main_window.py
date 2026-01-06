import os
import json
import logging
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
                             QPushButton, QTextEdit, QLabel, QMessageBox, QRadioButton,
                             QProgressBar, QFileDialog, QListWidget,
                             QListWidgetItem, QToolBar, QStatusBar, QAction,
                             QTreeWidget, QTreeWidgetItem, QInputDialog,
                             QGroupBox, QSplitter, QMenu, QDialog, QDialogButtonBox,
                             QLineEdit, QFormLayout, QComboBox, QCheckBox, QTabWidget,
                             QApplication)
from PyQt5.QtCore import Qt, QSettings, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QTextCursor, QIcon
from typing import Dict, List, Any, Optional
import traceback

from model_manager import EnhancedModelManager
from data_processor import DataProcessor
from enhanced_coding_generator import EnhancedCodingGenerator
from standard_answer_manager import StandardAnswerManager
from training_manager import EnhancedTrainingManager
from text_navigator import TextNavigator
from grounded_theory_coder import GroundedTheoryCoder
from word_exporter import WordExporter
from model_downloader import ModelDownloader
from manual_coding_dialog import ManualCodingDialog
from config import Config
import re

logger = logging.getLogger(__name__)


class ModelInitializationThread(QThread):
    """模型初始化线程"""

    progress_updated = pyqtSignal(str)
    initialization_finished = pyqtSignal(bool, str)

    def __init__(self, model_downloader, model_manager):
        super().__init__()
        # self.settings = settings

        # 添加自定义信号
        from PyQt5.QtCore import pyqtSignal
        self._update_model_status_signal = pyqtSignal(bool, str)
        self._update_model_status_signal.connect(self._on_model_initialization_finished)

        self.setup_managers()
        self.init_ui()
        self.load_settings()
        self.setup_connections()

    def run(self):
        try:
            self.progress_updated.emit("正在初始化模型...")

            # 初始化模型管理器
            model_success = self.model_manager.initialize_models()

            if model_success:
                self.initialization_finished.emit(True, "模型初始化成功")
            else:
                self.progress_updated.emit("正在下载模型...")
                # 尝试下载模型
                download_success = self.model_downloader.download_all_models()
                if download_success:
                    model_success = self.model_manager.initialize_models()
                    if model_success:
                        self.initialization_finished.emit(True, "模型下载并初始化成功")
                    else:
                        self.initialization_finished.emit(False, "模型下载成功但初始化失败")
                else:
                    self.initialization_finished.emit(False, "模型下载失败")

        except Exception as e:
            logger.error(f"模型初始化线程失败: {e}")
            self.initialization_finished.emit(False, f"初始化失败: {str(e)}")


class MainWindow(QMainWindow):
    """主窗口 - 扎根理论编码分析系统"""

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.setup_managers()
        self.init_ui()
        self.load_settings()
        self.setup_connections()

        # 启动模型初始化
        self.initialize_models_async()

    def setup_managers(self):
        """设置管理器"""
        self.model_manager = EnhancedModelManager()
        self.data_processor = DataProcessor()
        self.coding_generator = EnhancedCodingGenerator()  # 使用新的编码生成器
        self.text_navigator = TextNavigator()
        self.grounded_coder = GroundedTheoryCoder()
        self.standard_answer_manager = StandardAnswerManager()
        self.enhanced_training_manager = EnhancedTrainingManager()
        self.word_exporter = WordExporter()
        self.model_downloader = ModelDownloader()

        # 设置训练管理器的标准答案管理器
        self.enhanced_training_manager.set_standard_answer_manager(self.standard_answer_manager)

        # 数据存储
        self.loaded_files = {}
        self.structured_codes = {}
        self.current_model_type = "offline"
        self.model_initialized = False

    def create_left_panel(self):
        """创建左侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 文件管理组
        file_group = QGroupBox("文件管理")
        file_layout = QVBoxLayout(file_group)

        # 文件列表
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.on_file_selected)
        file_layout.addWidget(self.file_list)

        # 文件操作按钮
        file_buttons_layout = QHBoxLayout()
        self.import_btn = QPushButton("导入文件")
        self.import_btn.clicked.connect(self.import_files)
        self.remove_file_btn = QPushButton("移除文件")
        self.remove_file_btn.clicked.connect(self.remove_selected_file)

        file_buttons_layout.addWidget(self.import_btn)
        file_buttons_layout.addWidget(self.remove_file_btn)
        file_layout.addLayout(file_buttons_layout)

        layout.addWidget(file_group)

        # 模型设置组
        model_group = QGroupBox("模型设置")
        model_layout = QVBoxLayout(model_group)

        # 模型状态显示
        self.model_status_label = QLabel("模型状态: 未初始化")
        model_layout.addWidget(self.model_status_label)

        # 模型类型选择
        model_type_layout = QHBoxLayout()
        model_type_layout.addWidget(QLabel("编码模式:"))

        self.model_type_combo = QComboBox()
        self.model_type_combo.addItems(["离线编码", "训练模型编码"])
        self.model_type_combo.currentTextChanged.connect(self.on_model_type_changed)
        model_type_layout.addWidget(self.model_type_combo)

        model_layout.addLayout(model_type_layout)

        # 模型操作按钮
        model_buttons_layout = QHBoxLayout()
        self.init_model_btn = QPushButton("初始化模型")
        self.init_model_btn.clicked.connect(self.initialize_models_async)
        self.load_model_btn = QPushButton("加载训练模型")
        self.load_model_btn.clicked.connect(self.load_trained_model)

        model_buttons_layout.addWidget(self.init_model_btn)
        model_buttons_layout.addWidget(self.load_model_btn)
        model_layout.addLayout(model_buttons_layout)

        layout.addWidget(model_group)

        # 标准答案管理组
        answer_group = QGroupBox("标准答案管理")
        answer_layout = QVBoxLayout(answer_group)

        self.answer_status_label = QLabel("标准答案: 无")
        answer_layout.addWidget(self.answer_status_label)

        # 训练数据统计
        self.training_data_label = QLabel("训练样本: 0 个")
        answer_layout.addWidget(self.training_data_label)

        answer_buttons_layout = QHBoxLayout()
        self.create_answer_btn = QPushButton("新建标准答案")
        self.create_answer_btn.clicked.connect(self.create_standard_answer)
        self.load_answer_btn = QPushButton("加载标准答案")
        self.load_answer_btn.clicked.connect(self.load_standard_answer)

        answer_buttons_layout.addWidget(self.create_answer_btn)
        answer_buttons_layout.addWidget(self.load_answer_btn)
        answer_layout.addLayout(answer_buttons_layout)

        layout.addWidget(answer_group)

        layout.addStretch()

        return panel

    def create_center_panel(self):
        """创建中间面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 文本显示区域
        text_group = QGroupBox("文本内容")
        text_layout = QVBoxLayout(text_group)

        self.text_display = QTextEdit()
        self.text_display.setPlaceholderText("选择文件查看文本内容...")
        font = QFont("SimSun", 10)
        self.text_display.setFont(font)
        text_layout.addWidget(self.text_display)

        layout.addWidget(text_group)

        # 编码控制区域
        coding_group = QGroupBox("编码控制")
        coding_layout = QVBoxLayout(coding_group)

        # 编码按钮
        coding_buttons_layout = QHBoxLayout()

        self.manual_coding_btn = QPushButton("手动编码")
        self.manual_coding_btn.clicked.connect(self.start_manual_coding)

        self.auto_coding_btn = QPushButton("自动生成编码")
        self.auto_coding_btn.clicked.connect(self.generate_codes_auto)

        self.clear_coding_btn = QPushButton("清空编码")
        self.clear_coding_btn.clicked.connect(self.clear_codes)

        coding_buttons_layout.addWidget(self.manual_coding_btn)
        coding_buttons_layout.addWidget(self.auto_coding_btn)
        coding_buttons_layout.addWidget(self.clear_coding_btn)

        coding_layout.addLayout(coding_buttons_layout)

        layout.addWidget(coding_group)

        return panel

    def create_right_panel(self):
        """创建右侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 编码结构显示
        coding_structure_group = QGroupBox("编码结构")
        coding_layout = QVBoxLayout(coding_structure_group)

        self.coding_tree = QTreeWidget()
        self.coding_tree.setHeaderLabels(["编码内容", "类型", "数量", "文件来源数", "句子来源数", "关联编号"])
        self.coding_tree.setColumnWidth(0, 300)
        self.coding_tree.setColumnWidth(1, 80)
        self.coding_tree.setColumnWidth(2, 60)
        self.coding_tree.setColumnWidth(3, 80)
        self.coding_tree.setColumnWidth(4, 80)
        self.coding_tree.setColumnWidth(5, 120)
        self.coding_tree.itemClicked.connect(self.on_tree_item_clicked)

        # 设置上下文菜单
        self.coding_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.coding_tree.customContextMenuRequested.connect(self.show_tree_context_menu)

        coding_layout.addWidget(self.coding_tree)

        # 树形控件操作按钮
        tree_buttons_layout = QHBoxLayout()

        self.expand_all_btn = QPushButton("展开全部")
        self.expand_all_btn.clicked.connect(self.coding_tree.expandAll)

        self.collapse_all_btn = QPushButton("折叠全部")
        self.collapse_all_btn.clicked.connect(self.coding_tree.collapseAll)

        self.edit_code_btn = QPushButton("编辑编码")
        self.edit_code_btn.clicked.connect(self.edit_selected_code)

        tree_buttons_layout.addWidget(self.expand_all_btn)
        tree_buttons_layout.addWidget(self.collapse_all_btn)
        tree_buttons_layout.addWidget(self.edit_code_btn)

        coding_layout.addLayout(tree_buttons_layout)

        layout.addWidget(coding_structure_group)

        # 训练管理组
        training_group = QGroupBox("训练管理")
        training_layout = QVBoxLayout(training_group)

        # 训练按钮
        training_buttons_layout = QHBoxLayout()

        self.train_model_btn = QPushButton("训练模型")
        self.train_model_btn.clicked.connect(self.start_training)

        self.save_correction_btn = QPushButton("保存修正")
        self.save_correction_btn.clicked.connect(self.save_corrections)

        training_buttons_layout.addWidget(self.train_model_btn)
        training_buttons_layout.addWidget(self.save_correction_btn)

        training_layout.addLayout(training_buttons_layout)

        # 训练进度
        self.training_progress = QProgressBar()
        self.training_progress.setVisible(False)
        training_layout.addWidget(self.training_progress)

        layout.addWidget(training_group)

        # 导出组
        export_group = QGroupBox("导出结果")
        export_layout = QVBoxLayout(export_group)

        export_buttons_layout = QHBoxLayout()

        self.export_json_btn = QPushButton("导出JSON")
        self.export_json_btn.clicked.connect(self.export_to_json)

        self.export_word_btn = QPushButton("导出Word")
        self.export_word_btn.clicked.connect(self.export_to_word)

        self.export_excel_btn = QPushButton("导出Excel")
        self.export_excel_btn.clicked.connect(self.export_to_excel)

        export_buttons_layout.addWidget(self.export_json_btn)
        export_buttons_layout.addWidget(self.export_word_btn)
        export_buttons_layout.addWidget(self.export_excel_btn)

        export_layout.addLayout(export_buttons_layout)

        layout.addWidget(export_group)

        return panel

    def create_menus(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu('文件')

        import_action = QAction('导入文件', self)
        import_action.triggered.connect(self.import_files)
        file_menu.addAction(import_action)

        export_action = QAction('导出结果', self)
        export_action.triggered.connect(self.export_results)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 编码菜单
        coding_menu = menubar.addMenu('编码')

        manual_coding_action = QAction('手动编码', self)
        manual_coding_action.triggered.connect(self.start_manual_coding)
        coding_menu.addAction(manual_coding_action)

        auto_coding_action = QAction('自动编码', self)
        auto_coding_action.triggered.connect(self.generate_codes_auto)
        coding_menu.addAction(auto_coding_action)

        # 训练菜单
        training_menu = menubar.addMenu('训练')

        train_action = QAction('训练模型', self)
        train_action.triggered.connect(self.start_training)
        training_menu.addAction(train_action)

        # 帮助菜单
        help_menu = menubar.addMenu('帮助')

        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_connections(self):
        """设置信号连接"""
        # 更新训练数据标签
        self.update_training_data_label()

    def initialize_models_async(self):
        """异步初始化模型 - 修复版本"""
        try:
            self.model_status_label.setText("模型状态: 初始化中...")
            self.init_model_btn.setEnabled(False)

            # 使用QTimer延迟初始化，避免阻塞UI
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, self._do_model_initialization)

        except Exception as e:
            logger.error(f"启动模型初始化失败: {e}")
            self.model_status_label.setText("模型状态: 初始化失败")
            self.init_model_btn.setEnabled(True)

    def _do_model_initialization(self):
        """执行模型初始化"""
        try:
            # 尝试初始化模型
            model_success = self.model_manager.initialize_models()

            if model_success:
                self.model_initialized = True
                self.model_status_label.setText("模型状态: 已就绪")
                self.statusBar().showMessage("模型初始化成功")
                logger.info("模型初始化成功")
            else:
                # 模型初始化失败，尝试下载
                self.statusBar().showMessage("模型不存在，尝试下载...")
                self._download_models_async()

        except Exception as e:
            logger.error(f"模型初始化异常: {e}")
            self.model_status_label.setText("模型状态: 初始化异常")
            self.init_model_btn.setEnabled(True)
            self.statusBar().showMessage(f"模型初始化异常: {str(e)}")

    def _download_models_async(self):
        """异步下载模型"""
        try:
            from PyQt5.QtCore import QThread, pyqtSignal
            import threading

            def download_in_thread():
                try:
                    logger.info("开始下载模型...")
                    success = self.model_downloader.download_all_models()
                    if success:
                        # 下载成功后重新初始化
                        model_success = self.model_manager.initialize_models()
                        if model_success:
                            # 使用信号更新UI
                            self._update_model_status_signal.emit(True, "模型下载并初始化成功")
                        else:
                            self._update_model_status_signal.emit(False, "模型下载成功但初始化失败")
                    else:
                        self._update_model_status_signal.emit(False, "模型下载失败")
                except Exception as e:
                    self._update_model_status_signal.emit(False, f"模型下载异常: {str(e)}")

            # 创建线程下载
            download_thread = threading.Thread(target=download_in_thread)
            download_thread.daemon = True
            download_thread.start()

        except Exception as e:
            logger.error(f"启动模型下载失败: {e}")
            self.model_status_label.setText("模型状态: 下载失败")
            self.init_model_btn.setEnabled(True)

    # 添加信号处理
    def _on_model_initialization_finished(self, success, message):
        """模型初始化完成"""
        self.init_model_btn.setEnabled(True)
        if success:
            self.model_status_label.setText("模型状态: 已就绪")
            self.model_initialized = True
            self.statusBar().showMessage("模型初始化成功")
        else:
            self.model_status_label.setText("模型状态: 初始化失败")
            self.statusBar().showMessage(f"模型初始化失败: {message}")
            # 不显示警告框，避免阻塞
            logger.warning(f"模型初始化失败: {message}")

    def on_model_initialization_finished(self, success, message):
        """模型初始化完成"""
        self.init_model_btn.setEnabled(True)
        if success:
            self.model_status_label.setText("模型状态: 已就绪")
            self.model_initialized = True
            self.statusBar().showMessage("模型初始化成功")
        else:
            self.model_status_label.setText("模型状态: 初始化失败")
            self.statusBar().showMessage(f"模型初始化失败: {message}")
            QMessageBox.warning(self, "模型初始化失败", message)

    def update_status(self, message):
        """更新状态"""
        self.statusBar().showMessage(message)

    def import_files(self):
        """导入文件"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择文本文件", "",
            "文本文件 (*.txt);;Word文档 (*.docx *.doc);;所有文件 (*)"
        )

        if not file_paths:
            return

        for file_path in file_paths:
            try:
                # 读取文件
                file_lower = file_path.lower()
                if file_lower.endswith('.docx') or file_lower.endswith('.doc'):
                    content = self.data_processor.read_word_file(file_path)
                else:
                    content = self.data_processor.read_text_file(file_path)

                filename = os.path.basename(file_path)

                # 存储文件数据
                self.loaded_files[file_path] = {
                    'filename': filename,
                    'file_path': file_path,
                    'content': content,
                    'file_type': 'docx' if file_path.lower().endswith('.docx') else 'doc' if file_path.lower().endswith(
                        '.doc') else 'txt'
                }

                # 添加到文件列表
                item = QListWidgetItem(filename)
                item.setData(Qt.UserRole, file_path)
                self.file_list.addItem(item)

                logger.info(f"成功导入文件: {filename}")

            except Exception as e:
                logger.error(f"导入文件失败 {file_path}: {e}")
                QMessageBox.critical(self, "导入错误", f"导入文件失败: {str(e)}")

        self.statusBar().showMessage(f"成功导入 {len(file_paths)} 个文件")

    def remove_selected_file(self):
        """移除选中的文件"""
        current_item = self.file_list.currentItem()
        if not current_item:
            return

        file_path = current_item.data(Qt.UserRole)
        if file_path in self.loaded_files:
            del self.loaded_files[file_path]

        self.file_list.takeItem(self.file_list.currentRow())
        self.text_display.clear()

        self.statusBar().showMessage("文件已移除")

    def on_file_selected(self, item):
        """文件选择事件"""
        file_path = item.data(Qt.UserRole)
        if file_path in self.loaded_files:
            file_data = self.loaded_files[file_path]
            self.text_display.setText(file_data['content'])

    def on_model_type_changed(self, model_type):
        """模型类型改变"""
        if model_type == "训练模型编码":
            if not self.model_manager.is_trained_model_available():
                QMessageBox.warning(self, "警告", "没有训练过的模型可用，请先训练模型")
                self.model_type_combo.setCurrentText("离线编码")
            else:
                self.statusBar().showMessage("切换到训练模型编码模式")
        else:
            self.statusBar().showMessage("切换到离线编码模式")

    def start_manual_coding(self):
        """开始手动编码 - 修复文件数据传递"""
        if not self.loaded_files:
            QMessageBox.warning(self, "警告", "请先导入文本文件")
            return

        try:
            # 确保文件数据包含必要的内容字段
            processed_files = {}
            for file_path, file_data in self.loaded_files.items():
                processed_file_data = file_data.copy()

                # 确保有content字段
                if 'content' not in processed_file_data:
                    # 尝试从其他字段获取内容
                    if 'original_content' in processed_file_data:
                        processed_file_data['content'] = processed_file_data['original_content']
                    elif 'numbered_text' in processed_file_data:
                        processed_file_data['content'] = processed_file_data['numbered_text']
                    elif 'original_text' in processed_file_data:
                        processed_file_data['content'] = processed_file_data['original_text']
                    else:
                        # 如果都没有，重新读取文件
                        try:
                            file_lower = file_path.lower()
                            if file_lower.endswith('.docx') or file_lower.endswith('.doc'):
                                content = self.data_processor.read_word_file(file_path)
                            else:
                                content = self.data_processor.read_text_file(file_path)
                            processed_file_data['content'] = content
                        except Exception as e:
                            logger.error(f"重新读取文件失败 {file_path}: {e}")
                            continue

                processed_files[file_path] = processed_file_data

            if not processed_files:
                QMessageBox.warning(self, "警告", "没有有效的文件内容可进行手动编码")
                return

            dialog = ManualCodingDialog(self, processed_files, self.structured_codes)
            if dialog.exec_() == QDialog.Accepted:
                coding_result = dialog.get_coding_result()
                if coding_result:
                    self.structured_codes = coding_result
                    self.update_coding_tree()
                    QMessageBox.information(self, "成功", "手动编码已完成")

        except Exception as e:
            logger.error(f"启动手动编码失败: {e}")
            QMessageBox.critical(self, "错误", f"启动手动编码失败: {str(e)}")

    def generate_codes_auto(self):
        """自动生成编码"""
        if not self.loaded_files:
            QMessageBox.warning(self, "警告", "请先导入文本文件")
            return

        if not self.model_initialized:
            QMessageBox.warning(self, "警告", "模型未初始化，请先初始化模型")
            return

        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)

            # 处理文件数据
            file_paths = list(self.loaded_files.keys())
            processed_data = self.data_processor.process_multiple_files(file_paths)

            self.progress_bar.setValue(30)

            # 生成编码
            use_trained_model = (self.model_type_combo.currentText() == "训练模型编码")
            raw_codes = self.coding_generator.generate_grounded_theory_codes_multi_files(
                processed_data, self.model_manager,
                progress_callback=self.update_progress,
                use_trained_model=use_trained_model
            )

            self.progress_bar.setValue(70)

            # 构建编码结构
            self.structured_codes = self.grounded_coder.build_coding_structure(raw_codes)

            # 更新界面
            self.update_coding_tree()

            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)

            self.statusBar().showMessage("自动编码生成完成")

        except Exception as e:
            self.progress_bar.setVisible(False)
            logger.error(f"自动生成编码失败: {e}")
            QMessageBox.critical(self, "生成错误", f"生成编码失败: {str(e)}")

    def update_progress(self, value):
        """更新进度"""
        self.progress_bar.setValue(value)

    def update_coding_tree(self):
        """更新编码树 - 修复版本，显示完整编号和统计信息"""
        self.coding_tree.clear()

        if not self.structured_codes:
            return

        for third_cat, second_cats in self.structured_codes.items():
            third_item = QTreeWidgetItem(self.coding_tree)
            third_item.setText(0, third_cat)
            third_item.setText(1, "三阶编码")

            # 计算三阶编码的统计数据
            third_first_count = 0
            third_file_sources = set()
            third_sentence_sources = set()
            third_code_ids = []

            for second_cat, first_contents in second_cats.items():
                for content_data in first_contents:
                    third_first_count += 1

                    if isinstance(content_data, dict):
                        code_id = content_data.get('code_id', '')
                        sentence_details = content_data.get('sentence_details', [])

                        # 添加编码ID
                        if code_id:
                            third_code_ids.append(code_id)

                        # 添加文件来源和句子来源
                        for sentence in sentence_details:
                            if isinstance(sentence, dict):
                                file_path = sentence.get('file_path', '')
                                sentence_id = sentence.get('sentence_id', '')

                                if file_path:
                                    third_file_sources.add(file_path)
                                if sentence_id:
                                    third_sentence_sources.add(str(sentence_id))
                    else:
                        # 处理非字典格式的内容
                        third_code_ids.append("")

            # 设置三阶编码的统计信息
            third_item.setText(2, str(len(second_cats)))  # 二阶编码数量
            third_item.setText(3, str(len(third_file_sources)))  # 文件来源数
            third_item.setText(4, str(len(third_sentence_sources)))  # 句子来源数
            third_item.setText(5,
                               ", ".join(third_code_ids[:5]) + ("..." if len(third_code_ids) > 5 else ""))  # 关联编号，限制显示
            third_item.setData(0, Qt.UserRole, {"level": 3, "name": third_cat})

            for second_cat, first_contents in second_cats.items():
                second_item = QTreeWidgetItem(third_item)
                second_item.setText(0, second_cat)
                second_item.setText(1, "二阶编码")

                # 计算二阶编码的统计数据
                second_first_count = len(first_contents)
                second_file_sources = set()
                second_sentence_sources = set()
                second_code_ids = []

                for content_data in first_contents:
                    if isinstance(content_data, dict):
                        code_id = content_data.get('code_id', '')
                        sentence_details = content_data.get('sentence_details', [])

                        # 添加编码ID
                        if code_id:
                            second_code_ids.append(code_id)

                        # 添加文件来源和句子来源
                        for sentence in sentence_details:
                            if isinstance(sentence, dict):
                                file_path = sentence.get('file_path', '')
                                sentence_id = sentence.get('sentence_id', '')

                                if file_path:
                                    second_file_sources.add(file_path)
                                if sentence_id:
                                    second_sentence_sources.add(str(sentence_id))
                    else:
                        # 处理非字典格式的内容
                        second_code_ids.append("")

                # 设置二阶编码的统计信息
                second_item.setText(2, str(second_first_count))  # 一阶编码数量
                second_item.setText(3, "")  # 二阶编码不显示文件来源数
                second_item.setText(4, str(len(second_sentence_sources)))  # 句子来源数
                second_item.setText(5, ", ".join(second_code_ids[:5]) + (
                    "..." if len(second_code_ids) > 5 else ""))  # 关联编号，限制显示
                second_item.setData(0, Qt.UserRole, {"level": 2, "name": second_cat, "parent": third_cat})

                for content_data in first_contents:
                    first_item = QTreeWidgetItem(second_item)

                    if isinstance(content_data, dict):
                        # 显示带编号的完整内容
                        numbered_content = content_data.get('numbered_content', '')
                        content = content_data.get('content', '')
                        code_id = content_data.get('code_id', '')
                        sentence_details = content_data.get('sentence_details', [])
                    else:
                        numbered_content = str(content_data)
                        content = str(content_data)
                        code_id = ""
                        sentence_details = []

                    # 计算一阶编码的统计数据
                    first_file_sources = set()
                    first_sentence_sources = set()

                    for sentence in sentence_details:
                        if isinstance(sentence, dict):
                            file_path = sentence.get('file_path', '')
                            sentence_id = sentence.get('sentence_id', '')

                            if file_path:
                                first_file_sources.add(file_path)
                            if sentence_id:
                                first_sentence_sources.add(str(sentence_id))

                    # 在树中显示带编号的内容
                    first_item.setText(0, numbered_content)
                    first_item.setText(1, "一阶编码")
                    first_item.setText(2, "1")
                    first_item.setText(3, str(len(first_file_sources)))  # 文件来源数
                    first_item.setText(4, str(len(first_sentence_sources)))  # 句子来源数
                    first_item.setText(5, code_id)  # 关联编号
                    first_item.setData(0, Qt.UserRole, {
                        "level": 1,
                        "content": content,  # 原始内容，用于搜索
                        "numbered_content": numbered_content,  # 带编号的内容
                        "code_id": code_id,  # 编码ID
                        "category": second_cat,
                        "core_category": third_cat,
                        "sentence_details": sentence_details
                    })

            third_item.setText(2, str(len(second_cats)))  # 二阶编码数量

        self.coding_tree.expandAll()

        # 更新统计
        total_third = len(self.structured_codes)
        total_second = sum(len(cats) for cats in self.structured_codes.values())
        total_first = sum(len(contents) for cats in self.structured_codes.values() for contents in cats.values())

        self.statusBar().showMessage(f"编码结构: {total_third}三阶, {total_second}二阶, {total_first}一阶")

        # 更新文本显示，添加编号标记
        self.update_text_display_with_codes()

    def update_text_display_with_codes(self):
        """更新文本显示，添加编码编号标记"""
        if not self.structured_codes or not self.loaded_files:
            return

        try:
            # 获取当前选中的文件
            current_items = self.file_list.selectedItems()
            if not current_items:
                return

            current_item = current_items[0]
            file_path = current_item.data(Qt.UserRole)

            if file_path not in self.loaded_files:
                return

            # 获取原始文本内容
            original_text = self.loaded_files[file_path].get('content', '')
            if not original_text:
                return

            # 创建带编号标记的文本
            marked_text = original_text

            # 收集所有编码标记
            all_code_marks = []

            for third_cat, second_cats in self.structured_codes.items():
                for second_cat, first_contents in second_cats.items():
                    for content_data in first_contents:
                        if isinstance(content_data, dict):
                            code_id = content_data.get('code_id', '')
                            sentence_details = content_data.get('sentence_details', [])

                            for sentence in sentence_details:
                                if isinstance(sentence, dict):
                                    original_content = sentence.get('original_content', '')
                                    if not original_content:
                                        original_content = sentence.get('content', '')

                                    # 清理可能已有的标记
                                    original_content_clean = re.sub(r'\s*\[[A-Z]\d+\]', '', original_content)

                                    if original_content_clean and code_id:
                                        # 创建带标记的内容
                                        marked_content = f"{original_content_clean} [{code_id}]"

                                        # 记录标记信息
                                        all_code_marks.append({
                                            'original': original_content_clean,
                                            'marked': marked_content,
                                            'code_id': code_id
                                        })

            # 按内容长度排序，先替换长的内容，避免嵌套替换问题
            all_code_marks.sort(key=lambda x: len(x['original']), reverse=True)

            # 应用所有标记
            for mark in all_code_marks:
                if mark['original'] in marked_text:
                    marked_text = marked_text.replace(mark['original'], mark['marked'])

            # 更新文本显示
            self.text_display.setPlainText(marked_text)

        except Exception as e:
            logger.error(f"更新文本显示失败: {e}")

    def on_tree_item_clicked(self, item, column):
        """树形项目点击事件 - 修复导航定位"""
        item_data = item.data(0, Qt.UserRole)
        if not item_data:
            return

        level = item_data.get("level")
        if level == 1:  # 一阶编码
            content = item_data.get("content", "")
            code_id = item_data.get("code_id", "")
            sentence_details = item_data.get("sentence_details", [])

            # 优先使用编码ID进行导航
            if code_id:
                self.highlight_text_by_code_id(code_id)
            elif content:
                self.highlight_text_content(content)

    def highlight_text_by_code_id(self, code_id: str):
        """通过编码ID高亮文本"""
        if not code_id:
            return

        # 获取当前显示的文本
        current_text = self.text_display.toPlainText()
        if not current_text:
            return

        # 查找编码标记模式： [A11], [B22] 等
        pattern = f"\\[{code_id}\\]"

        # 移动光标到文本开始
        cursor = self.text_display.textCursor()
        cursor.movePosition(cursor.Start)
        self.text_display.setTextCursor(cursor)

        # 清除之前的高亮
        self.clear_text_highlights()

        # 查找并高亮所有匹配项
        found = False
        search_cursor = self.text_display.textCursor()
        search_cursor.movePosition(cursor.Start)

        # 使用while循环查找所有匹配项，但添加安全计数器防止无限循环
        search_count = 0
        max_searches = 100  # 设置最大搜索次数防止无限循环
        
        # 首先高亮编码标记
        while search_count < max_searches:
            # 查找编码标记
            search_cursor = self.text_document.find(pattern, search_cursor)
            if search_cursor.isNull():
                break

            # 设置高亮格式
            highlight_format = search_cursor.charFormat()
            highlight_format.setBackground(QColor(255, 255, 0))  # 黄色背景
            highlight_format.setForeground(QColor(255, 0, 0))  # 红色文字

            # 应用高亮
            search_cursor.mergeCharFormat(highlight_format)
            found = True
            
            # 记录第一个匹配项的位置
            if search_count == 0:  # 第一次匹配
                self.text_display.setTextCursor(search_cursor)

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
                    content_cursor = self.text_document.find(clean_content, content_cursor)
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

        if found:
            self.text_display.ensureCursorVisible()  # 确保光标位置可见
            self.statusBar().showMessage(f"已高亮编码 {code_id} 及其对应内容")
        else:
            self.statusBar().showMessage(f"未找到编码 {code_id} 的标记")

    def highlight_text_content(self, content: str):
        """在文本中高亮内容"""
        if not content or len(content) < 5:
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
        search_cursor = self.text_display.textCursor()
        search_cursor.movePosition(cursor.Start)

        # 清理内容，移除可能存在的标记
        clean_content = re.sub(r'\s*\[[A-Z]\d+\]', '', content)

        while True:
            search_cursor = self.text_document.find(clean_content, search_cursor)
            if search_cursor.isNull():
                break

            # 设置高亮格式
            highlight_format = search_cursor.charFormat()
            highlight_format.setBackground(QColor(255, 255, 0))  # 黄色背景
            highlight_format.setForeground(QColor(255, 0, 0))  # 红色文字

            # 应用高亮
            search_cursor.mergeCharFormat(highlight_format)
            found = True

            # 如果是第一个匹配项，滚动到该位置
            if not found:
                self.text_display.setTextCursor(search_cursor)
                found = True

        if found:
            self.statusBar().showMessage(f"已高亮内容: {clean_content[:50]}...")
        else:
            self.statusBar().showMessage(f"未找到内容: {clean_content[:50]}...")

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
    
    # 在 init_ui 方法中添加文本文档引用
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("扎根理论编码分析系统 v3.0")
        self.setGeometry(100, 100, 1400, 800)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)

        # 左侧面板 - 文件管理和模型设置
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # 中间面板 - 文本显示和编码控制
        center_panel = self.create_center_panel()
        splitter.addWidget(center_panel)

        # 右侧面板 - 编码结构和训练管理
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        # 设置分割比例
        splitter.setSizes([300, 600, 500])
        main_layout.addWidget(splitter)

        # 创建菜单栏
        self.create_menus()

        # 创建状态栏
        self.statusBar().showMessage("就绪")

        # 初始化进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress_bar)

        # 保存文本文档引用
        self.text_document = self.text_display.document()

    def on_tree_item_clicked(self, item, column):
        """树形项目点击事件"""
        item_data = item.data(0, Qt.UserRole)
        if not item_data:
            return

        level = item_data.get("level")
        if level == 1:  # 一阶编码
            content = item_data.get("content", "")
            self.highlight_text_content(content)

    def highlight_text_content(self, content):
        """在文本中高亮内容"""
        if not content or len(content) < 5:
            return

        # 简单的文本高亮
        cursor = self.text_display.textCursor()
        self.text_display.moveCursor(QTextCursor.Start)

        # 查找文本
        while self.text_display.find(content):
            # 设置高亮格式
            cursor = self.text_display.textCursor()
            format = cursor.charFormat()
            format.setBackground(QColor(255, 255, 0))  # 黄色背景
            cursor.mergeCharFormat(format)

    def show_tree_context_menu(self, position):
        """显示树形控件上下文菜单"""
        item = self.coding_tree.itemAt(position)
        if not item:
            return

        menu = QMenu(self)

        edit_action = menu.addAction("编辑")
        delete_action = menu.addAction("删除")

        action = menu.exec_(self.coding_tree.mapToGlobal(position))

        if action == edit_action:
            self.edit_selected_code()
        elif action == delete_action:
            self.delete_selected_code()

    def edit_selected_code(self):
        """编辑选中的编码 - 增大弹窗"""
        current_item = self.coding_tree.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择一个编码")
            return

        item_data = current_item.data(0, Qt.UserRole)
        if not item_data:
            return

        level = item_data.get("level")
        old_content = current_item.text(0)

        if level == 1:
            # 创建更大的编辑对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("编辑一阶编码")
            dialog.resize(600, 400)  # 增大对话框尺寸

            layout = QVBoxLayout(dialog)

            # 添加说明
            label = QLabel("请输入一阶编码内容:")
            layout.addWidget(label)

            # 使用更大的文本编辑框
            text_edit = QTextEdit()
            text_edit.setPlainText(old_content)
            text_edit.setMinimumHeight(200)  # 设置最小高度
            layout.addWidget(text_edit)

            # 按钮布局
            button_layout = QHBoxLayout()
            ok_button = QPushButton("确定")
            cancel_button = QPushButton("取消")

            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            # 连接信号
            def on_ok():
                new_content = text_edit.toPlainText().strip()
                if new_content and new_content != old_content:
                    current_item.setText(0, new_content)
                    self.update_structured_codes_from_tree()
                dialog.accept()

            def on_cancel():
                dialog.reject()

            ok_button.clicked.connect(on_ok)
            cancel_button.clicked.connect(on_cancel)

            # 显示对话框
            result = dialog.exec_()

        elif level == 2:
            # 编辑二阶编码
            dialog = QDialog(self)
            dialog.setWindowTitle("编辑二阶编码")
            dialog.resize(500, 200)

            layout = QVBoxLayout(dialog)

            label = QLabel("请输入二阶编码名称:")
            layout.addWidget(label)

            line_edit = QLineEdit()
            line_edit.setText(old_content)
            layout.addWidget(line_edit)

            button_layout = QHBoxLayout()
            ok_button = QPushButton("确定")
            cancel_button = QPushButton("取消")

            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            def on_ok():
                new_content = line_edit.text().strip()
                if new_content and new_content != old_content:
                    current_item.setText(0, new_content)
                    self.update_structured_codes_from_tree()
                dialog.accept()

            def on_cancel():
                dialog.reject()

            ok_button.clicked.connect(on_ok)
            cancel_button.clicked.connect(on_cancel)

            result = dialog.exec_()

        elif level == 3:
            # 编辑三阶编码
            dialog = QDialog(self)
            dialog.setWindowTitle("编辑三阶编码")
            dialog.resize(500, 200)

            layout = QVBoxLayout(dialog)

            label = QLabel("请输入三阶编码名称:")
            layout.addWidget(label)

            line_edit = QLineEdit()
            line_edit.setText(old_content)
            layout.addWidget(line_edit)

            button_layout = QHBoxLayout()
            ok_button = QPushButton("确定")
            cancel_button = QPushButton("取消")

            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            def on_ok():
                new_content = line_edit.text().strip()
                if new_content and new_content != old_content:
                    current_item.setText(0, new_content)
                    self.update_structured_codes_from_tree()
                dialog.accept()

            def on_cancel():
                dialog.reject()

            ok_button.clicked.connect(on_ok)
            cancel_button.clicked.connect(on_cancel)

            result = dialog.exec_()

    def delete_selected_code(self):
        """删除选中的编码"""
        current_item = self.coding_tree.currentItem()
        if not current_item:
            return

        item_data = current_item.data(0, Qt.UserRole)
        if not item_data:
            return

        level = item_data.get("level")
        content = current_item.text(0)

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除这个{level}阶编码吗？\n{content}",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            parent = current_item.parent()
            if parent:
                parent.removeChild(current_item)
            else:
                index = self.coding_tree.indexOfTopLevelItem(current_item)
                self.coding_tree.takeTopLevelItem(index)

            self.update_structured_codes_from_tree()
            self.statusBar().showMessage(f"已删除{level}阶编码")

    def update_structured_codes_from_tree(self):
        """从树形结构更新编码数据"""
        self.structured_codes = {}

        for i in range(self.coding_tree.topLevelItemCount()):
            third_item = self.coding_tree.topLevelItem(i)
            third_name = third_item.text(0)
            self.structured_codes[third_name] = {}

            for j in range(third_item.childCount()):
                second_item = third_item.child(j)
                second_name = second_item.text(0)
                self.structured_codes[third_name][second_name] = []

                for k in range(second_item.childCount()):
                    first_item = second_item.child(k)
                    first_content = first_item.text(0)
                    self.structured_codes[third_name][second_name].append(first_content)

    def start_training(self):
        """开始训练模型"""
        if not self.standard_answer_manager.get_current_answers():
            QMessageBox.warning(self, "警告", "请先创建或加载标准答案")
            return

        sample_count = self.standard_answer_manager.get_training_sample_count()
        if sample_count < 5:
            QMessageBox.warning(self, "警告", f"训练样本不足，当前只有 {sample_count} 个样本，至少需要 5 个")
            return

        try:
            self.training_progress.setVisible(True)
            self.train_model_btn.setEnabled(False)

            # 准备训练数据
            training_data = self.standard_answer_manager.export_for_training()

            # 开始训练
            self.enhanced_training_manager.train_grounded_theory_model(
                training_data,
                self.model_manager,
                progress_callback=self.update_training_progress,
                finished_callback=self.on_training_finished
            )

            self.statusBar().showMessage("开始训练模型...")

        except Exception as e:
            logger.error(f"开始训练失败: {e}")
            QMessageBox.critical(self, "训练错误", f"开始训练失败: {str(e)}")
            self.train_model_btn.setEnabled(True)
            self.training_progress.setVisible(False)

    def update_training_progress(self, value):
        """更新训练进度"""
        self.training_progress.setValue(value)

    def on_training_finished(self, success, message):
        """训练完成"""
        self.train_model_btn.setEnabled(True)
        self.training_progress.setVisible(False)

        if success:
            self.statusBar().showMessage("模型训练完成")
            self.model_type_combo.setCurrentText("训练模型编码")
            QMessageBox.information(self, "训练完成", message)
        else:
            QMessageBox.critical(self, "训练失败", message)

    def save_corrections(self):
        """保存修正到标准答案 - 使用增量保存"""
        if not self.structured_codes:
            QMessageBox.warning(self, "警告", "没有编码数据可保存")
            return

        # 显示修改确认对话框
        confirmation_dialog = QDialog(self)
        confirmation_dialog.setWindowTitle("确认保存修改")
        confirmation_dialog.resize(500, 300)

        layout = QVBoxLayout(confirmation_dialog)

        # 显示修改统计
        if self.standard_answer_manager.current_answers:
            current_codes = self.standard_answer_manager.current_answers.get("structured_codes", {})
            modifications = self.standard_answer_manager._analyze_modifications(current_codes, self.structured_codes)

            if not modifications["has_changes"]:
                QMessageBox.information(self, "提示", "没有检测到修改，无需保存")
                return

            summary = modifications["summary"]
            stats_text = f"""
    修改统计:
    • 新增编码: {summary['added_codes']} 个
    • 修改编码: {summary['modified_codes']} 个  
    • 删除编码: {summary['deleted_codes']} 个
            """.strip()

            stats_label = QLabel(stats_text)
            layout.addWidget(stats_label)
        else:
            stats_label = QLabel("这将创建第一个标准答案版本")
            layout.addWidget(stats_label)

        # 描述输入
        desc_label = QLabel("修改描述:")
        layout.addWidget(desc_label)

        desc_edit = QTextEdit()
        desc_edit.setMaximumHeight(80)
        desc_edit.setPlaceholderText("请描述本次修改的内容...")
        layout.addWidget(desc_edit)

        # 保存选项
        options_group = QGroupBox("保存选项")
        options_layout = QVBoxLayout(options_group)

        incremental_radio = QRadioButton("增量保存（推荐）- 只保存修改和新增的内容")
        full_radio = QRadioButton("完整保存 - 保存全部编码内容")
        incremental_radio.setChecked(True)

        options_layout.addWidget(incremental_radio)
        options_layout.addWidget(full_radio)
        layout.addWidget(options_group)

        # 按钮
        button_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")

        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        def on_save():
            description = desc_edit.toPlainText().strip() or "人工修正"

            if incremental_radio.isChecked():
                # 增量保存
                version_id = self.standard_answer_manager.save_modifications_only(
                    self.structured_codes, description
                )
            else:
                # 完整保存
                version_id = self.standard_answer_manager.create_from_structured_codes(
                    self.structured_codes, description
                )

            if version_id:
                self.update_training_data_label()

                # 显示保存成功信息
                success_dialog = QMessageBox(self)
                success_dialog.setWindowTitle("保存成功")
                success_dialog.setText(f"修改已保存: {version_id}")

                if incremental_radio.isChecked():
                    success_dialog.setInformativeText("已使用增量保存模式，只保存了修改和新增的内容。")
                else:
                    success_dialog.setInformativeText("已使用完整保存模式，保存了全部编码内容。")

                success_dialog.exec_()
                confirmation_dialog.accept()
            else:
                QMessageBox.critical(self, "错误", "保存修正失败")

        def on_cancel():
            confirmation_dialog.reject()

        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(on_cancel)

        confirmation_dialog.exec_()

    def update_training_data_label(self):
        """更新训练数据标签"""
        sample_count = self.standard_answer_manager.get_training_sample_count()
        self.training_data_label.setText(f"训练样本: {sample_count} 个")

    def create_standard_answer(self):
        """创建标准答案"""
        if not self.structured_codes:
            QMessageBox.warning(self, "警告", "没有编码数据可保存")
            return

        description, ok = QInputDialog.getText(
            self, "创建标准答案", "请输入标准答案描述:"
        )

        if ok:
            version_id = self.standard_answer_manager.create_from_structured_codes(
                self.structured_codes, description or "初始标准答案"
            )

            if version_id:
                self.answer_status_label.setText(f"标准答案: {version_id}")
                self.update_training_data_label()
                QMessageBox.information(self, "成功", f"标准答案已创建: {version_id}")
            else:
                QMessageBox.critical(self, "错误", "创建标准答案失败")

    def load_standard_answer(self):
        """加载标准答案"""
        version_history = self.standard_answer_manager.get_version_history()
        if not version_history:
            QMessageBox.information(self, "提示", "没有可用的标准答案")
            return

        versions = [v["version"] for v in version_history]
        version, ok = QInputDialog.getItem(
            self, "选择标准答案", "选择要加载的版本:", versions, 0, False
        )

        if ok and version:
            success = self.standard_answer_manager.load_answers(version)
            if success:
                current_answers = self.standard_answer_manager.get_current_answers()
                if current_answers and "structured_codes" in current_answers:
                    self.structured_codes = current_answers["structured_codes"]
                    self.update_coding_tree()
                    self.answer_status_label.setText(f"标准答案: {version}")
                    self.update_training_data_label()
                    self.statusBar().showMessage(f"已加载标准答案: {version}")
                else:
                    QMessageBox.warning(self, "警告", "标准答案数据格式错误")
            else:
                QMessageBox.critical(self, "错误", "加载标准答案失败")

    def load_trained_model(self):
        """加载训练模型"""
        available_models = self.model_downloader.get_available_trained_models()
        if not available_models:
            QMessageBox.information(self, "提示", "没有训练过的模型")
            return

        model_name, ok = QInputDialog.getItem(
            self, "选择训练模型", "选择要加载的模型:", available_models, 0, False
        )

        if ok and model_name:
            success = self.model_manager.load_trained_model(model_name)
            if success:
                self.model_type_combo.setCurrentText("训练模型编码")
                QMessageBox.information(self, "成功", f"已加载训练模型: {model_name}")
            else:
                QMessageBox.critical(self, "错误", "加载训练模型失败")

    def export_to_json(self):
        """导出为JSON"""
        if not self.structured_codes:
            QMessageBox.warning(self, "警告", "没有编码数据可导出")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出JSON", "扎根理论编码.json", "JSON文件 (*.json)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.structured_codes, f, ensure_ascii=False, indent=2)

                QMessageBox.information(self, "成功", f"JSON文件已导出: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出错误", f"导出失败: {str(e)}")

    def export_to_word(self):
        """导出为Word文档"""
        if not self.structured_codes:
            QMessageBox.warning(self, "警告", "没有编码数据可导出")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出Word文档", "扎根理论编码分析.docx", "Word文档 (*.docx)"
        )

        if file_path:
            try:
                # 获取合并文本
                combined_text = self.get_combined_text()

                # 使用增强的导出器
                from enhanced_word_exporter import EnhancedWordExporter
                exporter = EnhancedWordExporter()

                success = exporter.export_structured_codes_with_hyperlinks(
                    file_path, self.structured_codes, combined_text, {}
                )

                if success:
                    QMessageBox.information(self, "成功", f"Word文档已导出: {file_path}")
                else:
                    QMessageBox.critical(self, "错误", "Word文档导出失败")

            except Exception as e:
                QMessageBox.critical(self, "导出错误", f"导出失败: {str(e)}")

    def export_to_excel(self):
        """导出为Excel"""
        if not self.structured_codes:
            QMessageBox.warning(self, "警告", "没有编码数据可导出")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出Excel", "扎根理论编码.xlsx", "Excel文件 (*.xlsx)"
        )

        if file_path:
            try:
                success = self.data_processor.export_structured_codes_to_table(
                    file_path, self.structured_codes
                )

                if success:
                    QMessageBox.information(self, "成功", f"Excel文件已导出: {file_path}")
                else:
                    QMessageBox.critical(self, "错误", "Excel文件导出失败")

            except Exception as e:
                QMessageBox.critical(self, "导出错误", f"导出失败: {str(e)}")

    def export_results(self):
        """导出结果（综合）"""
        self.export_to_word()

    def get_combined_text(self):
        """获取合并的文本"""
        combined_text = ""
        for file_data in self.loaded_files.values():
            combined_text += f"\n\n=== {file_data['filename']} ===\n\n"
            combined_text += file_data['content']
        return combined_text

    def clear_codes(self):
        """清空编码"""
        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空所有编码吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.structured_codes = {}
            self.coding_tree.clear()
            self.statusBar().showMessage("编码已清空")

    def show_about(self):
        """显示关于信息"""
        about_text = """
        <h2>扎根理论编码分析系统 v3.0</h2>
        <p>基于人工智能的扎根理论三级编码分析工具</p>
        <p>主要功能：</p>
        <ul>
        <li>支持多文件导入（TXT、Word）</li>
        <li>手动和自动编码生成</li>
        <li>模型训练和优化</li>
        <li>标准答案管理</li>
        <li>多种格式导出</li>
        </ul>
        <p>© 2025 质性研究实验室</p>
        """
        QMessageBox.about(self, "关于", about_text)

    def load_settings(self):
        """加载设置"""
        try:
            self.restoreGeometry(self.settings.value("geometry", bytes()))
            self.restoreState(self.settings.value("windowState", bytes()))
        except:
            pass

    def closeEvent(self, event):
        """关闭事件"""
        try:
            self.settings.setValue("geometry", self.saveGeometry())
            self.settings.setValue("windowState", self.saveState())
        except:
            pass
        event.accept()