import os
import json
import logging
import re
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
                             QPushButton, QTextEdit, QLabel, QMessageBox, QRadioButton,
                             QProgressBar, QFileDialog, QListWidget,
                             QListWidgetItem, QToolBar, QStatusBar, QAction,
                             QTreeWidget, QTreeWidgetItem, QInputDialog,
                             QGroupBox, QSplitter, QMenu, QDialog, QDialogButtonBox,
                             QLineEdit, QFormLayout, QComboBox, QCheckBox, QTabWidget,
                             QApplication)
from PyQt5.QtCore import Qt, QSettings, QThread, pyqtSignal, QTimer, QRegularExpression
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
from project_manager import ProjectManager
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

        # 初始化项目管理器
        self.project_manager = ProjectManager()

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

        self.number_all_text_btn = QPushButton("给所有文本编号")
        self.number_all_text_btn.clicked.connect(self.number_all_imported_text)

        self.clear_coding_btn = QPushButton("清空编码")
        self.clear_coding_btn.clicked.connect(self.clear_codes)

        coding_buttons_layout.addWidget(self.manual_coding_btn)
        coding_buttons_layout.addWidget(self.auto_coding_btn)
        coding_buttons_layout.addWidget(self.number_all_text_btn)
        coding_buttons_layout.addWidget(self.clear_coding_btn)

        coding_layout.addLayout(coding_buttons_layout)

        # 项目管理按钮
        project_buttons_layout = QHBoxLayout()

        self.save_project_btn = QPushButton("保存项目")
        self.save_project_btn.clicked.connect(self.save_project)

        self.load_project_btn = QPushButton("加载项目")
        self.load_project_btn.clicked.connect(self.load_project)

        self.import_coding_tree_btn = QPushButton("导入编码树")
        self.import_coding_tree_btn.clicked.connect(self.import_coding_tree)

        project_buttons_layout.addWidget(self.save_project_btn)
        project_buttons_layout.addWidget(self.load_project_btn)
        project_buttons_layout.addWidget(self.import_coding_tree_btn)

        coding_layout.addLayout(project_buttons_layout)

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
            # 优先显示编号内容，如果存在的话
            if 'numbered_content' in file_data and file_data['numbered_content']:
                self.text_display.setText(file_data['numbered_content'])
            else:
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
                    # 比较手动编码结果与自动编码结构的差异
                    if self.structured_codes:
                        # 有自动编码结构，提供选择性保存选项
                        auto_codes_count = self._count_codes(self.structured_codes)
                        manual_codes_count = self._count_codes(coding_result)

                        # 显示差异比较信息
                        msg = f"自动编码: {auto_codes_count['third']}三阶, {auto_codes_count['second']}二阶, {auto_codes_count['first']}一阶\n"
                        msg += f"手动编辑: {manual_codes_count['third']}三阶, {manual_codes_count['second']}二阶, {manual_codes_count['first']}一阶\n\n"
                        msg += "选择保存方式:"

                        # 提供保存选项
                        from PyQt5.QtWidgets import QMessageBox
                        reply = QMessageBox.question(
                            self, "保存编码结果", msg,
                            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                            QMessageBox.Yes
                        )

                        if reply == QMessageBox.Yes:
                            # 完全替换自动编码
                            self.structured_codes = coding_result
                            self.update_coding_tree()
                            QMessageBox.information(self, "成功", "手动编码已完全替换自动编码")
                        elif reply == QMessageBox.No:
                            # 合并编码结果（保留自动编码，添加手动编码）
                            merged_codes = self._merge_coding_results(self.structured_codes, coding_result)
                            self.structured_codes = merged_codes
                            self.update_coding_tree()
                            QMessageBox.information(self, "成功", "手动编码已与自动编码合并")
                        else:
                            # 取消保存
                            QMessageBox.information(self, "取消", "编码结果未保存")
                            return
                    else:
                        # 没有自动编码结构，直接保存
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

            # 第一步：为所有导入的文件进行编号
            self.data_processor.numbering_manager.reset()
            for file_path, file_data in self.loaded_files.items():
                content = file_data.get('content', '')
                if content:
                    filename = file_data.get('filename', os.path.basename(file_path))
                    numbered_content, number_mapping = self.data_processor.numbering_manager.number_text(content, filename)
                    file_data['numbered_content'] = numbered_content
                    file_data['numbered_mapping'] = number_mapping

            self.progress_bar.setValue(10)

            # 第二步：处理文件数据
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

    def _count_codes(self, coding_structure):
        """统计编码结构中的三阶、二阶和一阶编码数量"""
        count = {
            'third': 0,
            'second': 0,
            'first': 0
        }

        if coding_structure:
            count['third'] = len(coding_structure)
            for third_cat, second_cats in coding_structure.items():
                count['second'] += len(second_cats)
                for second_cat, first_contents in second_cats.items():
                    count['first'] += len(first_contents)

        return count

    def _merge_coding_results(self, auto_codes, manual_codes):
        """合并手动编码结果和自动编码结构，保留自动编码，添加手动编码"""
        merged_codes = auto_codes.copy()

        # 遍历手动编码结果，添加到自动编码结构中
        for third_cat, second_cats in manual_codes.items():
            if third_cat not in merged_codes:
                merged_codes[third_cat] = {}

            for second_cat, first_contents in second_cats.items():
                if second_cat not in merged_codes[third_cat]:
                    merged_codes[third_cat][second_cat] = []

                # 添加新的一阶编码，避免重复
                existing_contents = [content.get('content', '') for content in merged_codes[third_cat][second_cat] if
                                     isinstance(content, dict)]
                for first_content in first_contents:
                    if isinstance(first_content, dict):
                        content_str = first_content.get('content', '')
                        if content_str not in existing_contents:
                            merged_codes[third_cat][second_cat].append(first_content)
                            existing_contents.append(content_str)
                    else:
                        # 处理非字典格式的内容
                        if first_content not in existing_contents:
                            merged_codes[third_cat][second_cat].append(first_content)
                            existing_contents.append(first_content)

        return merged_codes

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
            
            # Extracts ID like "C01" from "C01 Category"
            third_id_match = re.match(r'^[A-Z]\d+', third_cat)
            third_id_display = third_id_match.group(0) if third_id_match else ""
            third_item.setText(5, third_id_display)  # 关联编号显示自身编号

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
                
                # Extracts ID like "B01" from "B01 Category"
                second_id_match = re.match(r'^[A-Z]\d+', second_cat)
                second_id_display = second_id_match.group(0) if second_id_match else ""
                second_item.setText(5, second_id_display)  # 关联编号显示自身编号
                
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

                    # 修复：将句子编号替换为所属一阶编码的编号
                    if code_id and numbered_content:
                        # 提取原始内容（去除编号前缀）
                        content_text = numbered_content
                        # 移除现有的 Code ID 前缀
                        if content_text.startswith(code_id + ': '):
                            original_content = content_text[len(code_id + ': '):]
                        elif content_text.startswith(code_id + ' '):
                            original_content = content_text[len(code_id + ' '):]
                        else:
                            original_content = content_text

                        # 移除可能的类似 A1, A01 的前缀
                        original_content = re.sub(r'^[A-Z]\d+\s+', '', original_content)
                        # 移除 "1, 58 " 这种格式 (文件索引, 句子索引)
                        original_content = re.sub(r'^\d+\s*,\s*\d+\s*', '', original_content)
                        # 移除 "68 " 或 "[68] " 或 "1 " 这种格式
                        original_content = re.sub(r'^(?:\[\d+\]|\d+)\s+', '', original_content)

                        # 使用一阶编码编号作为前缀
                        display_content = f"{code_id} {original_content}"
                    else:
                        display_content = numbered_content
                        
                    # 在树中显示带编号的内容
                    first_item.setText(0, display_content)
                    first_item.setText(1, "一阶编码")
                    first_item.setText(2, "1")
                    
                    # 提取句子编号用于关联编号列
                    extracted_sentence_ids = []
                    
                    # 方法1：从sentence_details的原始内容提取
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
                                        pattern = re.escape(sent_content_clean[:min(30, len(sent_content_clean))])
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
                    
                    # 方法2：如果方法1失败，尝试从numbered_content开头提取
                    if not extracted_sentence_ids and numbered_content:
                        match = re.search(r'^\s*\[(\d+)\]', numbered_content.strip())
                        if match:
                            extracted_sentence_ids.append(match.group(1))

                    # 修复：确保文件来源和句子来源至少为1（自动编码时）
                    file_source_count = len(first_file_sources) if first_file_sources else 1
                    sentence_source_count = len(first_sentence_sources) if first_sentence_sources else 1
                    first_item.setText(3, str(file_source_count))  # 文件来源数
                    first_item.setText(4, str(sentence_source_count))  # 句子来源数
                    
                    # 修复：关联编号显示句子ID（如 [1]）而不是 Code ID
                    associated_id_display = ""
                    
                    # 收集所有可能的句子ID
                    all_ids = set()
                    
                    # 从first_sentence_sources提取
                    all_ids.update(first_sentence_sources)
                    
                    # 从sentence_details提取
                    if not all_ids and sentence_details:
                         for s in sentence_details:
                             if isinstance(s, dict) and s.get('sentence_id'):
                                 all_ids.add(str(s.get('sentence_id')))
                    
                    # 从提取的句子编号添加
                    if not all_ids:
                        all_ids.update(extracted_sentence_ids)
                        
                    if all_ids:
                         # 格式化显示句子编号，纯数字格式（如 1, 2, 3）
                         ids = sorted(all_ids, key=lambda x: int(x) if x.isdigit() else float('inf'))
                         # 移除可能的括号，只保留数字
                         clean_ids = [sid.strip('[]') if isinstance(sid, str) else str(sid) for sid in ids]
                         associated_id_display = ", ".join(clean_ids)

                    first_item.setText(5, associated_id_display)  # 关联编号
                    
                    first_item.setData(0, Qt.UserRole, {
                        "level": 1,
                        "content": content,  # 原始内容，用于搜索
                        "numbered_content": numbered_content,  # 带编号的内容
                        "code_id": code_id,  # 编码ID
                        "category": second_cat,
                        "core_category": third_cat,
                        "sentence_details": sentence_details,
                        "sentence_ids": list(all_ids)  # 存储句子编号列表，用于导航
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
                # 如果没有选中文件，选中第一个文件
                if self.file_list.count() > 0:
                    first_item = self.file_list.item(0)
                    self.file_list.setCurrentItem(first_item)
                    current_items = [first_item]
                else:
                    return

            current_item = current_items[0]
            file_path = current_item.data(Qt.UserRole)

            if file_path not in self.loaded_files:
                return

            # 优先使用已编号的内容，已保留句子编号 [1]
            file_data = self.loaded_files[file_path]
            marked_text = file_data.get('numbered_content', '')
            
            # 如果没有编号内容，尝试现有的 content（可能已经带编号）或生成编号
            if not marked_text:
                original_text = file_data.get('content', '')
                if not original_text:
                    return
                
                # 检查 content 是否包含编号
                if re.search(r'\[\d+\]', original_text):
                     marked_text = original_text
                else:
                     # 尝试自动编号
                     try:
                         filename = file_data.get('filename', os.path.basename(file_path))
                         marked_text, _ = self.data_processor.numbering_manager.number_text(original_text, filename)
                         # 保存编号后的内容
                         self.loaded_files[file_path]['numbered_content'] = marked_text
                     except Exception as e:
                         # 降级：使用原始内容
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

                                    # 清理可能已有的标记（编码标记和句子编号都清理，得到纯文本）
                                    original_content_clean = re.sub(r'\s*\[[A-Z]\d+\]', '', original_content)
                                    original_content_clean = re.sub(r'\s*\[\d+\]', '', original_content_clean)
                                    original_content_clean = original_content_clean.strip()

                                    if original_content_clean and code_id:
                                        all_code_marks.append({
                                            'clean_content': original_content_clean,
                                            'code_id': code_id
                                        })

            # 按内容长度排序
            all_code_marks.sort(key=lambda x: len(x['clean_content']), reverse=True)

            # 应用所有标记
            for mark in all_code_marks:
                clean = mark['clean_content']
                code_tag = f"[{mark['code_id']}]"
                
                # 使用转义来匹配文本
                escaped_clean = re.escape(clean)
                
                # 策略1：匹配 "纯文本[标点]? [句子编号]" 的模式（最理想情况）
                # 允许句子和编号之间有标点符号（。！？）
                pattern1 = f"({escaped_clean}[。！？!?]?\\s*\\[\\d+\\])((?:\\s*\\[[A-Z]\\d+\\])*)(\\s*)"
                
                # 策略2：如果没有句子编号，直接匹配纯文本（可能带标点）
                pattern2 = f"({escaped_clean}[。！？!?]?)((?:\\s*\\[[A-Z]\\d+\\])*)(\\s*)"
                
                def replace_func(match):
                    full_match = match.group(0)
                    part1 = match.group(1)  # 内容 [N] 或 纯内容
                    existing_tags = match.group(2)  # 已有的编码标记
                    whitespace = match.group(3)  # 后面的空白
                    
                    # 检查是否已经有了这个标记
                    if code_tag in existing_tags:
                         return full_match
                    
                    # 追加编码标记
                    return f"{part1}{existing_tags} {code_tag}{whitespace}"

                try:
                    # 先尝试策略1（带句子编号）
                    new_text = re.sub(pattern1, replace_func, marked_text)
                    if new_text != marked_text:
                        marked_text = new_text
                    else:
                        # 如果策略1没有匹配，尝试策略2（纯文本）
                        marked_text = re.sub(pattern2, replace_func, marked_text)
                except Exception as e:
                    logger.warning(f"正则替换失败: {e}，尝试简单替换")
                    # 如果正则失败，回退到简单替换
                    if clean in marked_text and code_tag not in marked_text:
                         marked_text = marked_text.replace(clean, f"{clean} {code_tag}")

            # 更新文本显示
            self.text_display.setPlainText(marked_text)

        except Exception as e:
            logger.error(f"更新文本显示失败: {e}")

    def on_tree_item_clicked(self, item, column):
        """树形项目点击事件 - 使用精确高亮功能"""
        item_data = item.data(0, Qt.UserRole)
        if not item_data:
            return

        level = item_data.get("level")
        if level == 1:  # 一阶编码
            sentence_ids = item_data.get("sentence_ids", [])
            code_id = item_data.get("code_id", "")
            
            # 优先使用句子编号导航（更准确）
            if sentence_ids:
                self.highlight_text_by_sentence_ids(sentence_ids)
            elif code_id:
                # 降级方案：使用编码ID
                self.highlight_text_by_code_id_precise(code_id)
            else:
                # 最后的降级方案：使用内容匹配
                content = item_data.get("content", "")
                if content:
                    self.highlight_text_content(content)

    def highlight_text_by_sentence_ids(self, sentence_ids: list):
        """通过句子编号列表高亮文本并导航"""
        try:
            if not sentence_ids:
                return
            
            # 清理句子ID，确保是纯数字
            clean_ids = []
            for sid in sentence_ids:
                if isinstance(sid, str):
                    sid = sid.strip('[]').strip()
                clean_ids.append(str(sid))
            
            if not clean_ids:
                return
            
            # 查找包含这些句子编号的文件
            target_file = None
            for file_path, file_data in self.loaded_files.items():
                file_text = file_data.get('numbered_content', '') or file_data.get('content', '')
                # 检查文件是否包含第一个句子编号
                if f"[{clean_ids[0]}]" in file_text:
                    target_file = file_path
                    break
            
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
                            # 等待文件显示更新
                            QApplication.processEvents()
                            break
            
            # 获取当前显示的文本
            current_text = self.text_display.toPlainText()
            if not current_text:
                return
            
            # 清除之前的高亮
            self.clear_text_highlights()
            
            # 查找并高亮所有匹配的句子编号
            found_count = 0
            first_match_position = None
            
            for sid in clean_ids:
                # 查找句子编号标记 [N]
                sentence_tag = f"[{sid}]"
                
                # 从文本开始查找
                search_pos = 0
                while True:
                    pos = current_text.find(sentence_tag, search_pos)
                    if pos < 0:
                        break
                    
                    # 找到句子编号，现在需要高亮整个句子
                    # 从编号位置向前查找句子开始（前一个句子的结束位置）
                    sentence_start = 0
                    # 向前查找上一个 [数字] 标记
                    text_before = current_text[:pos]
                    prev_tags = list(re.finditer(r'\[(\d+)\]', text_before))
                    if prev_tags:
                        # 从上一个标记的结束位置开始
                        prev_end = prev_tags[-1].end()
                        # 跳过前一句可能的编码标记 [Axx], [Bxx] 等
                        text_between = current_text[prev_end:pos]
                        code_tags_match = re.match(r'^(\s*\[[A-Z]\d+\])+\s*', text_between)
                        if code_tags_match:
                            sentence_start = prev_end + code_tags_match.end()
                        else:
                            sentence_start = prev_end
                    
                    # 句子结束位置：编号标记之后（可能还有编码标记 [Axx]）
                    sentence_end = pos + len(sentence_tag)
                    # 查找编号后是否有编码标记
                    text_after = current_text[sentence_end:sentence_end + 20]
                    code_match = re.match(r'^(\s*\[[A-Z]\d+\])+', text_after)
                    if code_match:
                        sentence_end += code_match.end()
                    
                    # 创建光标并选择这段文本
                    cursor = self.text_display.textCursor()
                    cursor.setPosition(sentence_start)
                    cursor.setPosition(sentence_end, QTextCursor.KeepAnchor)
                    
                    # 设置浅蓝色高亮
                    highlight_format = cursor.charFormat()
                    highlight_format.setBackground(QColor(173, 216, 230))  # 浅蓝色背景
                    highlight_format.setForeground(QColor(0, 0, 139))  # 深蓝色文字
                    cursor.mergeCharFormat(highlight_format)
                    
                    found_count += 1
                    
                    # 记录第一个匹配位置
                    if first_match_position is None:
                        first_match_position = sentence_start
                    
                    # 移动搜索位置
                    search_pos = sentence_end
            
            if found_count > 0 and first_match_position is not None:
                # 定位到第一个匹配位置
                cursor = self.text_display.textCursor()
                cursor.setPosition(first_match_position)
                self.text_display.setTextCursor(cursor)
                self.text_display.ensureCursorVisible()
                
                self.statusBar().showMessage(f"已高亮 {found_count} 个句子")
            else:
                self.statusBar().showMessage(f"未找到句子编号: {', '.join(clean_ids)}")
        
        except Exception as e:
            logger.error(f"按句子编号高亮失败: {e}", exc_info=True)
            self.statusBar().showMessage(f"高亮失败: {str(e)}")

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
        """树形项目点击事件 - 使用精确高亮功能"""
        item_data = item.data(0, Qt.UserRole)
        if not item_data:
            return

        level = item_data.get("level")
        if level == 1:  # 一阶编码
            content = item_data.get("content", "")
            code_id = item_data.get("code_id", "")
            sentence_details = item_data.get("sentence_details", [])

            # 使用精确高亮功能
            if code_id:
                self.highlight_text_by_code_id_precise(code_id)
            elif content:
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
            # 模型选择对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("选择训练模型")
            dialog.resize(400, 200)

            layout = QVBoxLayout(dialog)

            # 添加说明
            label = QLabel("请选择用于训练的嵌入模型:")
            layout.addWidget(label)

            # 模型选择
            model_group = QGroupBox("模型选择")
            model_layout = QVBoxLayout(model_group)

            bert_radio = QRadioButton("BERT 模型 (默认)")
            sentence_radio = QRadioButton("Sentence-Transformer 模型")
            bert_radio.setChecked(True)

            # 检查 Sentence-Transformer 模型是否可用
            sentence_available = 'sentence' in self.model_manager.models
            if not sentence_available:
                sentence_radio.setEnabled(False)
                sentence_radio.setToolTip("Sentence-Transformer 模型未加载")

            model_layout.addWidget(bert_radio)
            model_layout.addWidget(sentence_radio)
            layout.addWidget(model_group)

            # 按钮
            button_layout = QHBoxLayout()
            ok_button = QPushButton("确定")
            cancel_button = QPushButton("取消")

            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            # 连接信号
            selected_model = 'bert'  # 默认值

            def on_ok():
                nonlocal selected_model
                if bert_radio.isChecked():
                    selected_model = 'bert'
                elif sentence_radio.isChecked():
                    selected_model = 'sentence'
                dialog.accept()

            def on_cancel():
                dialog.reject()

            ok_button.clicked.connect(on_ok)
            cancel_button.clicked.connect(on_cancel)

            # 显示对话框
            if dialog.exec_() != QDialog.Accepted:
                return

            self.training_progress.setVisible(True)
            self.train_model_btn.setEnabled(False)

            # 准备训练数据
            training_data = self.standard_answer_manager.export_for_training()

            # 开始训练
            self.enhanced_training_manager.train_grounded_theory_model(
                training_data,
                self.model_manager,
                progress_callback=self.update_training_progress,
                finished_callback=self.on_training_finished,
                model_type=selected_model
            )

            self.statusBar().showMessage(f"开始训练模型... 使用 {selected_model} 模型")

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
            # 检查文件是否存在
            import os

            # 获取绝对路径
            base_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(base_dir, "standard_answers", version)

            # 检查是否需要添加 .json 扩展名
            if not file_path.endswith('.json'):
                file_path_json = file_path + '.json'
                if os.path.exists(file_path_json):
                    file_path = file_path_json

            # 打印路径信息用于调试
            print(f"检查文件路径: {file_path}")
            print(f"文件是否存在: {os.path.exists(file_path)}")

            if not os.path.exists(file_path):
                # 列出目录内容用于调试
                dir_path = os.path.join(base_dir, "standard_answers")
                if os.path.exists(dir_path):
                    files = os.listdir(dir_path)
                    print(f"目录内容: {files}")

                QMessageBox.critical(self, "错误", f"标准答案文件不存在: {version}\n检查路径: {file_path}\n请检查 standard_answers 目录")
                return

            if os.path.getsize(file_path) == 0:
                QMessageBox.critical(self, "错误", f"标准答案文件为空: {version}")
                return

            # 使用正确的文件名（包含 .json 扩展名）
            actual_filename = os.path.basename(file_path)
            success = self.standard_answer_manager.load_answers(actual_filename)
            if success:
                current_answers = self.standard_answer_manager.get_current_answers()
                if current_answers and "structured_codes" in current_answers:
                    self.structured_codes = current_answers["structured_codes"]
                    self.update_coding_tree()
                    self.answer_status_label.setText(f"标准答案: {actual_filename}")
                    self.update_training_data_label()
                    self.statusBar().showMessage(f"已加载标准答案: {actual_filename}")
                else:
                    QMessageBox.warning(self, "警告", "标准答案数据格式不完整，缺少 structured_codes 字段")
            else:
                QMessageBox.critical(self, "错误",
                                     f"加载标准答案失败: {actual_filename}\n可能的原因:\n1. 文件格式错误\n2. 文件编码错误\n3. 文件内容损坏")

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

    def number_all_imported_text(self):
        """给所有导入的文本进行编号"""
        if not self.loaded_files:
            QMessageBox.warning(self, "警告", "请先导入文本文件")
            return

        try:
            # 重置编号管理器以确保编号从1开始
            self.data_processor.numbering_manager.reset()

            # 遍历所有已加载的文件并为它们编号
            for file_path, file_data in self.loaded_files.items():
                content = file_data.get('content', '')
                if content:
                    # 使用DataProcessor的编号管理器为文本编号
                    numbered_content, number_mapping = self.data_processor.numbering_manager.number_text(content,
                                                                                                         os.path.basename(
                                                                                                             file_path))

                    # 更新文件数据中的编号内容
                    file_data['numbered_content'] = numbered_content
                    file_data['numbered_mapping'] = number_mapping

            # 如果当前有选中的文件，更新显示
            current_items = self.file_list.selectedItems()
            if current_items:
                current_item = current_items[0]
                file_path = current_item.data(Qt.UserRole)
                if file_path in self.loaded_files:
                    file_data = self.loaded_files[file_path]
                    if 'numbered_content' in file_data:
                        self.text_display.setText(file_data['numbered_content'])

            self.statusBar().showMessage(f"已为 {len(self.loaded_files)} 个文件的文本进行编号")

        except Exception as e:
            logger.error(f"编号所有文本失败: {e}")
            QMessageBox.critical(self, "错误", f"编号所有文本失败: {str(e)}")

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

    def save_project(self):
        """保存项目"""
        if not self.loaded_files:
            QMessageBox.warning(self, "警告", "没有可保存的文件")
            return

        # 弹出对话框获取项目名称
        project_name, ok = QInputDialog.getText(self, "保存项目", "请输入项目名称:")

        if ok and project_name.strip():
            try:
                success = self.project_manager.save_project(project_name.strip(), self.loaded_files,
                                                            self.structured_codes)
                if success:
                    QMessageBox.information(self, "成功", f"项目 '{project_name}' 已保存")
                    self.statusBar().showMessage(f"项目已保存: {project_name}")
                else:
                    QMessageBox.critical(self, "错误", "项目保存失败")
            except Exception as e:
                logger.error(f"保存项目失败: {e}")
                QMessageBox.critical(self, "错误", f"项目保存失败: {str(e)}")

    def load_project(self):
        """加载项目"""
        try:
            projects = self.project_manager.get_projects_list()

            if not projects:
                QMessageBox.information(self, "提示", "没有可加载的项目")
                return

            # 创建项目选择对话框
            project_names = [proj["name"] for proj in projects]
            project_name, ok = QInputDialog.getItem(self, "加载项目", "请选择要加载的项目:", project_names, 0, False)

            if ok and project_name:
                loaded_files, structured_codes = self.project_manager.load_project(project_name)

                if loaded_files is not None and structured_codes is not None:
                    # 清空当前数据
                    self.loaded_files = loaded_files
                    self.structured_codes = structured_codes

                    # 更新文件列表
                    self.file_list.clear()
                    for file_path, file_data in self.loaded_files.items():
                        filename = file_data.get('filename', os.path.basename(file_path))
                        item = QListWidgetItem(filename)
                        item.setData(Qt.UserRole, file_path)
                        self.file_list.addItem(item)

                    # 更新编码树
                    self.update_coding_tree()

                    # 如果有选中的文件，显示其内容
                    if self.file_list.count() > 0:
                        first_item = self.file_list.item(0)
                        self.on_file_selected(first_item)

                    QMessageBox.information(self, "成功", f"项目 '{project_name}' 已加载")
                    self.statusBar().showMessage(f"项目已加载: {project_name}")
                else:
                    QMessageBox.critical(self, "错误", "项目加载失败")

        except Exception as e:
            logger.error(f"加载项目失败: {e}")
            QMessageBox.critical(self, "错误", f"项目加载失败: {str(e)}")

    def import_coding_tree(self):
        """导入编码树 - 从项目文件中导入完整的编码结构"""
        try:
            projects = self.project_manager.get_projects_list()

            if not projects:
                QMessageBox.information(self, "提示", "没有可导入编码树的项目")
                return

            # 创建项目选择对话框
            project_names = [proj["name"] for proj in projects]
            project_name, ok = QInputDialog.getItem(self, "导入编码树", "请选择要导入编码树的项目:", project_names, 0, False)

            if ok and project_name:
                # 只加载项目的编码结构，不覆盖文件数据
                _, structured_codes = self.project_manager.load_project(project_name)

                if structured_codes is not None:
                    # 询问用户是否确认导入编码树
                    reply = QMessageBox.question(
                        self, "确认导入",
                        f"确定要导入项目 '{project_name}' 的编码树吗？这将替换当前的编码结构。",
                        QMessageBox.Yes | QMessageBox.No
                    )

                    if reply == QMessageBox.Yes:
                        # 保存当前文件数据
                        current_loaded_files = self.loaded_files

                        # 更新编码结构
                        self.structured_codes = structured_codes

                        # 恢复文件数据
                        self.loaded_files = current_loaded_files

                        # 更新编码树界面
                        self.update_coding_tree()

                        QMessageBox.information(self, "成功", f"编码树已从项目 '{project_name}' 导入")
                        self.statusBar().showMessage(f"编码树已导入: {project_name}")
                else:
                    QMessageBox.critical(self, "错误", "编码树导入失败")

        except Exception as e:
            logger.error(f"导入编码树失败: {e}")
            QMessageBox.critical(self, "错误", f"导入编码树失败: {str(e)}")

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
                                # 规范化句子对象，确保有 text 字段
                                normalized_sentences = []
                                for sent in sentence_details:
                                    if isinstance(sent, dict):
                                        # 尝试从多个字段获取文本内容
                                        text = sent.get('text', '') or sent.get('content', '') or sent.get('original_content', '')
                                        if text:
                                            # 创建规范化的句子对象
                                            normalized_sent = {
                                                'text': text,
                                                'code_id': code_id,
                                                'original': sent  # 保留原始对象
                                            }
                                            normalized_sentences.append(normalized_sent)
                                return normalized_sentences
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

            # 获取编码对应的精确句子内容
            sentences_to_highlight = self.get_sentences_by_code_id(code_id)

            if not sentences_to_highlight:
                self.statusBar().showMessage(f"未找到编码 {code_id} 的句子详情")
                return

            # 查找包含该句子的文件并切换显示
            target_file = None
            for sentence_info in sentences_to_highlight:
                sentence_content = sentence_info.get('text', '').strip()
                if not sentence_content:
                    continue
                
                # 清理句子内容
                sentence_clean = re.sub(r'\s*\[[A-Z]\d+\]', '', sentence_content)
                sentence_clean = re.sub(r'\s*\[\d+\]', '', sentence_clean).strip()
                
                # 在所有已加载的文件中查找
                for file_path, file_data in self.loaded_files.items():
                    file_text = file_data.get('numbered_content', '') or file_data.get('content', '')
                    if sentence_clean in file_text:
                        target_file = file_path
                        break
                
                if target_file:
                    break
            
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
                            # 等待文件显示更新
                            QApplication.processEvents()
                            break

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

            # 精确高亮每个句子
            found_count = 0
            first_match_position = None  # 记录第一个匹配项的位置

            for sentence_info in sentences_to_highlight:
                sentence_content = sentence_info.get('text', '').strip()
                if not sentence_content:
                    continue

                # 清理句子内容：移除可能存在的编号标记
                sentence_clean = re.sub(r'\s*\[[A-Z]\d+\]', '', sentence_content)
                sentence_clean = re.sub(r'\s*\[\d+\]', '', sentence_clean).strip()

                # 在文本中查找并高亮这个精确句子
                search_cursor = self.text_display.textCursor()
                search_cursor.movePosition(cursor.Start)

                # 策略1：直接查找清理后的文本
                found_cursor = self.text_document.find(sentence_clean, search_cursor)
                
                # 策略2：如果策略1失败，尝试查找前50个字符
                if found_cursor.isNull() and len(sentence_clean) > 50:
                    found_cursor = self.text_document.find(sentence_clean[:50], search_cursor)
                
                # 策略3：如果还失败，尝试使用正则表达式查找（忽略空白差异）
                if found_cursor.isNull():
                    # 转换为正则模式，将多个空白符视为一个
                    pattern = re.sub(r'\s+', r'\\s+', re.escape(sentence_clean))
                    regex = QRegularExpression(pattern)
                    found_cursor = self.text_document.find(regex, search_cursor)

                if not found_cursor.isNull():
                    # 设置浅蓝色高亮格式
                    highlight_format = found_cursor.charFormat()
                    highlight_format.setBackground(QColor(173, 216, 230))  # 浅蓝色背景
                    highlight_format.setForeground(QColor(0, 0, 139))  # 深蓝色文字
                    found_cursor.mergeCharFormat(highlight_format)

                    found_count += 1

                    # 记录第一个匹配项的位置用于滚动
                    if first_match_position is None:
                        first_match_position = found_cursor.selectionStart()
                        logger.info(f"记录第一个匹配位置: {first_match_position}")

            if found_count > 0 and first_match_position is not None:
                # 创建新的光标并定位到第一个匹配项的位置
                new_cursor = self.text_display.textCursor()
                new_cursor.setPosition(first_match_position)

                # 设置光标并确保可见
                self.text_display.setTextCursor(new_cursor)
                self.text_display.ensureCursorVisible()

                logger.info(f"已定位到位置: {first_match_position}")
                self.statusBar().showMessage(f"已高亮编码 {code_id} 的 {found_count} 个句子")
            else:
                logger.warning(f"未找到编码 {code_id} 对应的句子内容")
                self.statusBar().showMessage(f"未找到编码 {code_id} 对应的句子内容")

        except Exception as e:
            logger.error(f"精确高亮文本失败: {e}", exc_info=True)
            self.statusBar().showMessage(f"高亮失败: {str(e)}")