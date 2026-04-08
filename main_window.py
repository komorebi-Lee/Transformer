import os
import json
import logging
import re
import pickle
from datetime import datetime
from collections import Counter
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
import numpy as np
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

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
from excel_processor import ExcelProcessorDialog
from config import Config
from project_manager import ProjectManager
from bert_finetuner import BERTFineTuner
from bert_dataset import GroundedTheoryDataset, get_label_mapping
from hyperparameter_optimizer import HyperparameterOptimizer
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


class TrainingConfigDialog(QDialog):
    """训练配置对话框"""

    def __init__(self, parent=None, has_existing_model=False):
        super().__init__(parent)
        self.has_existing_model = has_existing_model
        self.setWindowTitle("训练配置")
        self.resize(550, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        training_mode_group = QGroupBox("训练模式")
        mode_layout = QVBoxLayout(training_mode_group)

        self.bert_finetune_radio = QRadioButton("BERT微调 - 完整微调BERT模型（推荐，效果最好）")
        self.classifier_radio = QRadioButton("分类器训练 - 仅训练分类器层（速度快）")
        self.incremental_radio = QRadioButton("增量训练 - 基于已有模型继续训练")

        self.bert_finetune_radio.setChecked(True)

        if not self.has_existing_model:
            self.incremental_radio.setEnabled(False)
            self.incremental_radio.setToolTip("需要已有训练模型才能使用增量训练")

        mode_layout.addWidget(self.bert_finetune_radio)
        mode_layout.addWidget(self.classifier_radio)
        mode_layout.addWidget(self.incremental_radio)
        layout.addWidget(training_mode_group)

        hyperparam_group = QGroupBox("超参数寻优")
        hyperparam_layout = QVBoxLayout(hyperparam_group)

        self.enable_optimization_check = QCheckBox("启用超参数自动寻优")
        self.enable_optimization_check.setToolTip("使用网格搜索或贝叶斯优化自动寻找最优超参数")
        hyperparam_layout.addWidget(self.enable_optimization_check)

        self.optimization_method_combo = QComboBox()
        self.optimization_method_combo.addItems(["网格搜索", "贝叶斯优化"])
        self.optimization_method_combo.setEnabled(False)
        hyperparam_layout.addWidget(QLabel("寻优方法:"))
        hyperparam_layout.addWidget(self.optimization_method_combo)

        self.cv_folds_spin = QComboBox()
        self.cv_folds_spin.addItems(["3", "5", "10"])
        self.cv_folds_spin.setCurrentIndex(1)
        self.cv_folds_spin.setEnabled(False)
        hyperparam_layout.addWidget(QLabel("交叉验证折数:"))
        hyperparam_layout.addWidget(self.cv_folds_spin)

        self.enable_optimization_check.toggled.connect(self.on_optimization_toggled)
        layout.addWidget(hyperparam_group)

        params_group = QGroupBox("训练参数")
        params_layout = QFormLayout(params_group)

        self.learning_rate_edit = QLineEdit("2e-5")
        self.learning_rate_edit.setToolTip("学习率，推荐范围: 1e-5 到 5e-5")
        params_layout.addRow("学习率:", self.learning_rate_edit)

        self.batch_size_combo = QComboBox()
        self.batch_size_combo.addItems(["8", "16", "32", "64"])
        self.batch_size_combo.setCurrentIndex(1)
        self.batch_size_combo.setToolTip("批次大小，较大的值需要更多显存")
        params_layout.addRow("批次大小:", self.batch_size_combo)

        self.epochs_spin = QComboBox()
        self.epochs_spin.addItems(["3", "5", "10", "20", "50"])
        self.epochs_spin.setCurrentIndex(1)
        self.epochs_spin.setToolTip("训练轮数，过多可能导致过拟合")
        params_layout.addRow("训练轮数:", self.epochs_spin)

        self.max_length_combo = QComboBox()
        self.max_length_combo.addItems(["128", "256", "512"])
        self.max_length_combo.setCurrentIndex(2)
        self.max_length_combo.setToolTip("最大序列长度，较长的文本需要更多显存")
        params_layout.addRow("最大序列长度:", self.max_length_combo)

        self.warmup_ratio_edit = QLineEdit("0.1")
        self.warmup_ratio_edit.setToolTip("预热比例，通常设为0.1")
        params_layout.addRow("预热比例:", self.warmup_ratio_edit)

        self.weight_decay_edit = QLineEdit("0.01")
        self.weight_decay_edit.setToolTip("权重衰减，用于防止过拟合")
        params_layout.addRow("权重衰减:", self.weight_decay_edit)

        layout.addWidget(params_group)

        advanced_group = QGroupBox("高级选项")
        advanced_layout = QVBoxLayout(advanced_group)

        self.early_stopping_check = QCheckBox("启用早停 (Early Stopping)")
        self.early_stopping_check.setChecked(True)
        advanced_layout.addWidget(self.early_stopping_check)

        self.save_best_model_check = QCheckBox("保存最佳模型")
        self.save_best_model_check.setChecked(True)
        advanced_layout.addWidget(self.save_best_model_check)

        layout.addWidget(advanced_group)

        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("开始训练")
        self.cancel_button = QPushButton("取消")
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        layout.addLayout(button_layout)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def on_optimization_toggled(self, checked):
        self.optimization_method_combo.setEnabled(checked)
        self.cv_folds_spin.setEnabled(checked)

        self.learning_rate_edit.setEnabled(not checked)
        self.batch_size_combo.setEnabled(not checked)
        self.epochs_spin.setEnabled(not checked)

    def get_config(self):
        training_mode = 'bert_finetune'
        if self.classifier_radio.isChecked():
            training_mode = 'classifier'
        elif self.incremental_radio.isChecked():
            training_mode = 'incremental'

        return {
            'training_mode': training_mode,
            'enable_optimization': self.enable_optimization_check.isChecked(),
            'optimization_method': 'grid' if self.optimization_method_combo.currentText() == '网格搜索' else 'bayesian',
            'cv_folds': int(self.cv_folds_spin.currentText()),
            'learning_rate': float(self.learning_rate_edit.text()),
            'batch_size': int(self.batch_size_combo.currentText()),
            'epochs': int(self.epochs_spin.currentText()),
            'max_length': int(self.max_length_combo.currentText()),
            'warmup_ratio': float(self.warmup_ratio_edit.text()),
            'weight_decay': float(self.weight_decay_edit.text()),
            'early_stopping': self.early_stopping_check.isChecked(),
            'save_best_model': self.save_best_model_check.isChecked()
        }


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

        # 自动编码缓存 - 用于存储自动编码生成的文本内容
        self.auto_coding_cache = {}
        # 编码标记映射 - 用于存储一阶编码与文本位置的映射
        self.code_markers_map = {}

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

        # 当前加载模型显示
        self.current_model_label = QLabel("当前加载模型: 无")
        self.current_model_label.setStyleSheet("color: #666; font-size: 9pt")
        model_layout.addWidget(self.current_model_label)

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

        self.visualize_training_btn = QPushButton("训练结果可视化")
        self.visualize_training_btn.clicked.connect(self.visualize_training_results)
        answer_layout.addWidget(self.visualize_training_btn)

        layout.addWidget(answer_group)

        # 编码库管理组
        coding_library_group = QGroupBox("编码库管理")
        coding_library_layout = QVBoxLayout(coding_library_group)

        self.coding_library_status_label = QLabel("编码库: 已加载")
        coding_library_layout.addWidget(self.coding_library_status_label)

        coding_library_buttons_layout = QHBoxLayout()
        self.view_coding_library_btn = QPushButton("查看编码库")
        self.view_coding_library_btn.clicked.connect(self.view_coding_library)
        self.edit_coding_library_btn = QPushButton("编辑编码库")
        self.edit_coding_library_btn.clicked.connect(self.edit_coding_library)

        coding_library_buttons_layout.addWidget(self.view_coding_library_btn)
        coding_library_buttons_layout.addWidget(self.edit_coding_library_btn)
        coding_library_layout.addLayout(coding_library_buttons_layout)

        layout.addWidget(coding_library_group)

        layout.addStretch()

        return panel

    # def convert_to_training_data(self):
    #     """将标准答案转换为训练数据"""
    #     try:
    #         # 检查是否已加载标准答案
    #         if not hasattr(self, 'structured_codes') or not self.structured_codes:
    #             QMessageBox.warning(self, "警告", "请先加载标准答案")
    #             return
    #
    #         # 显示转换开始提示
    #         self.statusBar().showMessage("正在转换标准答案为训练数据...")
    #
    #         # # 导入转换脚本
    #         # import sys
    #         # import os
    #         # sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
    #         # from scripts.convert_to_training_data import extract_training_data, save_training_data, get_statistics
    #
    #         # 获取当前加载的标准答案文件路径
    #         current_answers = self.standard_answer_manager.get_current_answers()
    #         if not current_answers:
    #             QMessageBox.warning(self, "警告", "无法获取当前标准答案数据")
    #             return
    #
    #         # 构建标准答案文件路径
    #         base_dir = os.path.abspath(self.standard_answer_manager.standard_answers_dir)
    #         current_version = self.standard_answer_manager.get_current_version()
    #         if not current_version:
    #             QMessageBox.warning(self, "警告", "无法获取当前标准答案版本")
    #             return
    #
    #         file_path = os.path.join(base_dir, current_version)
    #         if not file_path.endswith('.json'):
    #             file_path_json = file_path + '.json'
    #             if os.path.exists(file_path_json):
    #                 file_path = file_path_json
    #
    #         if not os.path.exists(file_path):
    #             QMessageBox.critical(self, "错误", f"标准答案文件不存在: {file_path}")
    #             return
    #
    #         # 提取训练数据
    #         self.statusBar().showMessage("正在提取训练数据...")
    #         training_data = extract_training_data(file_path)
    #
    #         if not training_data:
    #             QMessageBox.warning(self, "警告", "未提取到训练数据，请检查标准答案格式")
    #             return
    #
    #         # 保存训练数据
    #         self.statusBar().showMessage("正在保存训练数据...")
    #         from datetime import datetime
    #         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    #         output_dir = os.path.join(os.path.dirname(__file__), "training_data")
    #         os.makedirs(output_dir, exist_ok=True)
    #         output_path = os.path.join(output_dir, f"training_data_{timestamp}.json")
    #
    #         save_training_data(training_data, output_path)
    #
    #         # 获取统计信息
    #         stats = get_statistics(training_data)
    #
    #         # 显示成功消息
    #         success_message = f"转换成功！\n"\
    #                        f"训练数据已保存到: {output_path}\n"\
    #                        f"总样本数: {stats['total_samples']}\n"\
    #                        f"三级分类数: {stats['unique_third_categories']}\n"\
    #                        f"二级分类数: {stats['unique_second_categories']}\n"\
    #                        f"唯一抽象重点数: {stats['unique_abstracts']}"
    #
    #         QMessageBox.information(self, "成功", success_message)
    #         self.statusBar().showMessage(f"已成功转换标准答案为训练数据，保存至: {output_path}")
    #
    #     except Exception as e:
    #         error_message = f"转换失败: {str(e)}\n\n可能的原因:\n1. 标准答案格式错误\n2. 文件权限问题\n3. 磁盘空间不足"
    #         QMessageBox.critical(self, "错误", error_message)
    #         self.statusBar().showMessage(f"转换失败: {str(e)}")

    def view_coding_library(self):
        """查看编码库内容"""
        try:
            from coding_library_manager import CodingLibraryManager

            # 初始化编码库管理器
            coding_library = CodingLibraryManager()
            if not getattr(coding_library, 'load_success', True):
                raise RuntimeError(f"编码库加载失败，请检查文件: {coding_library.library_path}")

            # 获取编码库信息
            library_info = coding_library.get_library_info()
            second_level_codes = coding_library.get_all_second_level_codes()
            third_level_codes = coding_library.get_all_third_level_codes()

            # 构建显示内容
            content = f"编码库信息:\n"
            content += f"版本: {library_info.get('version', '1.0')}\n"
            content += f"创建时间: {library_info.get('created_at', '')}\n"
            content += f"描述: {library_info.get('description', '')}\n"
            content += f"三阶编码数: {library_info.get('third_level_count', 0)}\n"
            content += f"二阶编码数: {library_info.get('second_level_count', 0)}\n\n"

            content += "三阶编码:\n"
            for third_level in third_level_codes:
                content += f"- {third_level.get('name')}: {third_level.get('description')}\n"
                second_levels = coding_library.get_second_level_codes_by_third_level(third_level.get('name'))
                for second_level in second_levels:
                    content += f"  * {second_level.get('name')}: {second_level.get('description')}\n"
                content += "\n"

            # 显示编码库内容
            from PyQt5.QtWidgets import QTextEdit, QDialog, QVBoxLayout, QPushButton

            dialog = QDialog(self)
            dialog.setWindowTitle("编码库内容")
            dialog.setGeometry(100, 100, 800, 600)

            layout = QVBoxLayout(dialog)

            text_edit = QTextEdit()
            text_edit.setPlainText(content)
            text_edit.setReadOnly(True)
            layout.addWidget(text_edit)

            close_button = QPushButton("关闭")
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)

            dialog.exec_()

        except Exception as e:
            error_message = f"查看编码库失败: {str(e)}"
            QMessageBox.critical(self, "错误", error_message)
            self.statusBar().showMessage(f"查看编码库失败: {str(e)}")

    def edit_coding_library(self):
        """编辑编码库内容"""
        try:
            # 显示编辑编码库的对话框
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QTabWidget, QWidget, QFormLayout, QLineEdit, \
                QTextEdit, QComboBox, QListWidget, QHBoxLayout, QListWidgetItem

            dialog = QDialog(self)
            dialog.setWindowTitle("编辑编码库")
            dialog.setGeometry(100, 100, 900, 700)

            layout = QVBoxLayout(dialog)

            # 创建标签页
            tab_widget = QTabWidget()

            # 三阶编码标签页
            third_level_tab = QWidget()
            third_level_layout = QVBoxLayout(third_level_tab)

            third_level_list = QListWidget()
            third_level_layout.addWidget(third_level_list)

            third_level_form = QFormLayout()
            third_level_id_edit = QLineEdit()
            third_level_name_edit = QLineEdit()
            third_level_desc_edit = QTextEdit()
            third_level_desc_edit.setMinimumHeight(100)

            third_level_form.addRow("ID:", third_level_id_edit)
            third_level_form.addRow("名称:", third_level_name_edit)
            third_level_form.addRow("描述:", third_level_desc_edit)

            third_level_buttons = QHBoxLayout()
            add_third_level_btn = QPushButton("添加")
            update_third_level_btn = QPushButton("更新")
            delete_third_level_btn = QPushButton("删除")

            third_level_buttons.addWidget(add_third_level_btn)
            third_level_buttons.addWidget(update_third_level_btn)
            third_level_buttons.addWidget(delete_third_level_btn)

            third_level_layout.addLayout(third_level_form)
            third_level_layout.addLayout(third_level_buttons)

            tab_widget.addTab(third_level_tab, "三阶编码")

            # 二阶编码标签页
            second_level_tab = QWidget()
            second_level_layout = QVBoxLayout(second_level_tab)

            second_level_list = QListWidget()
            second_level_layout.addWidget(second_level_list)

            second_level_form = QFormLayout()
            second_level_id_edit = QLineEdit()
            second_level_name_edit = QLineEdit()
            second_level_desc_edit = QTextEdit()
            second_level_desc_edit.setMinimumHeight(100)
            third_level_combo = QComboBox()

            second_level_form.addRow("ID:", second_level_id_edit)
            second_level_form.addRow("名称:", second_level_name_edit)
            second_level_form.addRow("描述:", second_level_desc_edit)
            second_level_form.addRow("所属三阶编码:", third_level_combo)

            second_level_buttons = QHBoxLayout()
            add_second_level_btn = QPushButton("添加")
            update_second_level_btn = QPushButton("更新")
            delete_second_level_btn = QPushButton("删除")

            second_level_buttons.addWidget(add_second_level_btn)
            second_level_buttons.addWidget(update_second_level_btn)
            second_level_buttons.addWidget(delete_second_level_btn)

            second_level_layout.addLayout(second_level_form)
            second_level_layout.addLayout(second_level_buttons)

            tab_widget.addTab(second_level_tab, "二阶编码")

            layout.addWidget(tab_widget)

            # 关闭按钮
            close_button = QPushButton("关闭")
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)

            # 加载编码库数据
            from coding_library_manager import CodingLibraryManager
            coding_library = CodingLibraryManager()

            # 加载三阶编码
            third_level_codes = coding_library.get_all_third_level_codes()
            for code in third_level_codes:
                item = QListWidgetItem(f"{code.get('id')}: {code.get('name')}")
                item.setData(Qt.UserRole, code)
                third_level_list.addItem(item)
                third_level_combo.addItem(code.get('name'), code.get('id'))

            # 加载二阶编码
            second_level_codes = coding_library.get_all_second_level_codes()
            for code in second_level_codes:
                item = QListWidgetItem(f"{code.get('id')}: {code.get('name')} ({code.get('third_level')})")
                item.setData(Qt.UserRole, code)
                second_level_list.addItem(item)

            # 连接信号
            def on_third_level_selected(item):
                code = item.data(Qt.UserRole)
                third_level_id_edit.setText(str(code.get('id')))
                third_level_name_edit.setText(code.get('name'))
                third_level_desc_edit.setPlainText(code.get('description'))

            third_level_list.itemClicked.connect(on_third_level_selected)

            def on_second_level_selected(item):
                code = item.data(Qt.UserRole)
                second_level_id_edit.setText(code.get('id'))
                second_level_name_edit.setText(code.get('name'))
                second_level_desc_edit.setPlainText(code.get('description'))
                # 选择对应的三阶编码
                index = third_level_combo.findText(code.get('third_level'))
                if index != -1:
                    third_level_combo.setCurrentIndex(index)

            second_level_list.itemClicked.connect(on_second_level_selected)

            def add_third_level():
                try:
                    code_id = int(third_level_id_edit.text())
                    name = third_level_name_edit.text()
                    description = third_level_desc_edit.toPlainText()

                    if not name:
                        QMessageBox.warning(dialog, "警告", "请输入编码名称")
                        return

                    success = coding_library.add_third_level_code(code_id, name, description)
                    if success:
                        # 更新列表和下拉框
                        item = QListWidgetItem(f"{code_id}: {name}")
                        item.setData(Qt.UserRole, {'id': code_id, 'name': name, 'description': description})
                        third_level_list.addItem(item)
                        third_level_combo.addItem(name, code_id)
                        QMessageBox.information(dialog, "成功", "添加三阶编码成功")
                    else:
                        QMessageBox.warning(dialog, "警告", "添加三阶编码失败")
                except Exception as e:
                    QMessageBox.critical(dialog, "错误", f"添加三阶编码失败: {str(e)}")

            add_third_level_btn.clicked.connect(add_third_level)

            def add_second_level():
                try:
                    code_id = second_level_id_edit.text()
                    name = second_level_name_edit.text()
                    description = second_level_desc_edit.toPlainText()
                    third_level_id = third_level_combo.currentData()

                    if not name or not code_id or third_level_id is None:
                        QMessageBox.warning(dialog, "警告", "请填写完整信息")
                        return

                    success = coding_library.add_second_level_code(third_level_id, code_id, name, description)
                    if success:
                        # 更新列表
                        third_level_name = third_level_combo.currentText()
                        item = QListWidgetItem(f"{code_id}: {name} ({third_level_name})")
                        item.setData(Qt.UserRole, {'id': code_id, 'name': name, 'description': description,
                                                   'third_level': third_level_name})
                        second_level_list.addItem(item)
                        QMessageBox.information(dialog, "成功", "添加二阶编码成功")
                    else:
                        QMessageBox.warning(dialog, "警告", "添加二阶编码失败")
                except Exception as e:
                    QMessageBox.critical(dialog, "错误", f"添加二阶编码失败: {str(e)}")

            add_second_level_btn.clicked.connect(add_second_level)

            def delete_second_level():
                try:
                    selected_item = second_level_list.currentItem()
                    if not selected_item:
                        QMessageBox.warning(dialog, "警告", "请先选择要删除的二阶编码")
                        return

                    code = selected_item.data(Qt.UserRole)
                    code_id = code.get('id')
                    code_name = code.get('name')

                    # 确认删除
                    reply = QMessageBox.question(
                        dialog, "确认删除", f"确定要删除二阶编码 '{code_name}' 吗？",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )

                    if reply == QMessageBox.Yes:
                        success = coding_library.delete_second_level_code(code_id)
                        if success:
                            # 从列表中移除
                            second_level_list.takeItem(second_level_list.currentRow())
                            QMessageBox.information(dialog, "成功", "删除二阶编码成功")
                        else:
                            QMessageBox.warning(dialog, "警告", "删除二阶编码失败")
                except Exception as e:
                    QMessageBox.critical(dialog, "错误", f"删除二阶编码失败: {str(e)}")

            delete_second_level_btn.clicked.connect(delete_second_level)

            def delete_third_level():
                try:
                    selected_item = third_level_list.currentItem()
                    if not selected_item:
                        QMessageBox.warning(dialog, "警告", "请先选择要删除的三阶编码")
                        return

                    code = selected_item.data(Qt.UserRole)
                    code_id = code.get('id')
                    code_name = code.get('name')

                    # 检查是否有关联的二阶编码
                    second_levels = coding_library.get_second_level_codes_by_third_level(code_name)
                    if second_levels:
                        QMessageBox.warning(dialog, "警告", f"三阶编码 '{code_name}' 下还有 {len(second_levels)} 个二阶编码，无法删除")
                        return

                    # 确认删除
                    reply = QMessageBox.question(
                        dialog, "确认删除", f"确定要删除三阶编码 '{code_name}' 吗？",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )

                    if reply == QMessageBox.Yes:
                        success = coding_library.delete_third_level_code(code_id)
                        if success:
                            # 从列表中移除
                            third_level_list.takeItem(third_level_list.currentRow())
                            # 从下拉框中移除
                            index = third_level_combo.findText(code_name)
                            if index != -1:
                                third_level_combo.removeItem(index)
                            QMessageBox.information(dialog, "成功", "删除三阶编码成功")
                        else:
                            QMessageBox.warning(dialog, "警告", "删除三阶编码失败")
                except Exception as e:
                    QMessageBox.critical(dialog, "错误", f"删除三阶编码失败: {str(e)}")

            delete_third_level_btn.clicked.connect(delete_third_level)

            def update_second_level():
                try:
                    selected_item = second_level_list.currentItem()
                    if not selected_item:
                        QMessageBox.warning(dialog, "警告", "请先选择要更新的二阶编码")
                        return

                    code = selected_item.data(Qt.UserRole)
                    old_code_id = code.get('id')
                    new_code_id = second_level_id_edit.text()
                    name = second_level_name_edit.text()
                    description = second_level_desc_edit.toPlainText()
                    third_level_id = third_level_combo.currentData()

                    if not name or not new_code_id or third_level_id is None:
                        QMessageBox.warning(dialog, "警告", "请填写完整信息")
                        return

                    # 先删除旧编码
                    delete_success = coding_library.delete_second_level_code(old_code_id)
                    if not delete_success:
                        QMessageBox.warning(dialog, "警告", "更新失败: 无法删除旧编码")
                        return

                    # 再添加新编码
                    add_success = coding_library.add_second_level_code(third_level_id, new_code_id, name, description)
                    if add_success:
                        # 更新列表
                        third_level_name = third_level_combo.currentText()
                        selected_item.setText(f"{new_code_id}: {name} ({third_level_name})")
                        selected_item.setData(Qt.UserRole, {'id': new_code_id, 'name': name, 'description': description,
                                                            'third_level': third_level_name})
                        QMessageBox.information(dialog, "成功", "更新二阶编码成功")
                    else:
                        QMessageBox.warning(dialog, "警告", "更新失败: 无法添加新编码")
                except Exception as e:
                    QMessageBox.critical(dialog, "错误", f"更新二阶编码失败: {str(e)}")

            update_second_level_btn.clicked.connect(update_second_level)

            def update_third_level():
                try:
                    selected_item = third_level_list.currentItem()
                    if not selected_item:
                        QMessageBox.warning(dialog, "警告", "请先选择要更新的三阶编码")
                        return

                    code = selected_item.data(Qt.UserRole)
                    old_code_id = code.get('id')
                    new_code_id = int(third_level_id_edit.text())
                    name = third_level_name_edit.text()
                    description = third_level_desc_edit.toPlainText()

                    if not name:
                        QMessageBox.warning(dialog, "警告", "请输入编码名称")
                        return

                    # 检查是否有关联的二阶编码
                    second_levels = coding_library.get_second_level_codes_by_third_level(code.get('name'))
                    if second_levels:
                        QMessageBox.warning(dialog, "警告", "三阶编码下还有二阶编码，无法更新")
                        return

                    # 先删除旧编码
                    delete_success = coding_library.delete_third_level_code(old_code_id)
                    if not delete_success:
                        QMessageBox.warning(dialog, "警告", "更新失败: 无法删除旧编码")
                        return

                    # 再添加新编码
                    add_success = coding_library.add_third_level_code(new_code_id, name, description)
                    if add_success:
                        # 更新列表
                        selected_item.setText(f"{new_code_id}: {name}")
                        selected_item.setData(Qt.UserRole,
                                              {'id': new_code_id, 'name': name, 'description': description})
                        # 更新下拉框
                        index = third_level_combo.findText(code.get('name'))
                        if index != -1:
                            third_level_combo.setItemText(index, name)
                            third_level_combo.setItemData(index, new_code_id)
                        QMessageBox.information(dialog, "成功", "更新三阶编码成功")
                    else:
                        QMessageBox.warning(dialog, "警告", "更新失败: 无法添加新编码")
                except Exception as e:
                    QMessageBox.critical(dialog, "错误", f"更新三阶编码失败: {str(e)}")

            update_third_level_btn.clicked.connect(update_third_level)

            dialog.exec_()

        except Exception as e:
            error_message = f"编辑编码库失败: {str(e)}"
            QMessageBox.critical(self, "错误", error_message)
            self.statusBar().showMessage(f"编辑编码库失败: {str(e)}")

    def visualize_training_results(self):
        """读取训练模型并生成可视化结果图"""
        try:
            preferred_path = os.path.join("trained_models", "grounded_theory_latest.pkl")
            fallback_path = os.path.join("trained_models", "grounded_codong_latest.pkl")
            model_path = preferred_path if os.path.exists(preferred_path) else fallback_path
            if not os.path.exists(model_path):
                QMessageBox.warning(self, "文件不存在", f"未找到模型文件:\n{model_path}")
                return

            with open(model_path, "rb") as f:
                model_data = pickle.load(f)

            stats = self._extract_training_visual_stats(model_data)
            image_path = self._plot_and_save_training_visualization(stats, model_path)

            if not image_path:
                QMessageBox.warning(self, "可视化失败", "未能生成可视化图像")
                return

            # Windows 下直接打开图片，便于查看和保存
            try:
                os.startfile(image_path)
            except Exception:
                pass

            QMessageBox.information(
                self,
                "训练结果可视化",
                f"已生成可视化结果:\n{image_path}\n\n"
                f"模型类型: {stats.get('model_type', 'unknown')}\n"
                f"类别数: {stats.get('class_count', 0)}\n"
                f"样本数: {stats.get('sample_count', 0)}\n"
                f"准确率: {stats.get('accuracy_display', 'N/A')}"
            )

        except Exception as e:
            logger.error(f"训练结果可视化失败: {e}")
            QMessageBox.warning(
                self,
                "可视化失败",
                f"无法读取模型或生成图像:\n{str(e)}\n\n"
                "请确认当前环境与模型训练环境兼容（numpy/sklearn 版本）。"
            )

    def _extract_training_visual_stats(self, model_data):
        """从模型数据中提取可视化所需统计信息"""
        stats = {
            "model_type": "grounded_theory_coder",
            "sample_count": 0,
            "class_count": 0,
            "accuracy": None,
            "accuracy_display": "N/A",
            "class_labels": [],
            "class_distribution": {},
            "feature_importances": [],
            "training_time": "",
            "model_version": "",
        }

        if isinstance(model_data, dict):
            # 兼容 metadata
            metadata = model_data.get("metadata", {})
            if isinstance(metadata, dict):
                stats["model_type"] = metadata.get("model_type", stats["model_type"])
                stats["training_time"] = metadata.get("training_time", metadata.get("timestamp", ""))
                stats["model_version"] = metadata.get("version", "")
                if metadata.get("sample_count") is not None:
                    stats["sample_count"] = metadata.get("sample_count", 0)
                if metadata.get("class_count") is not None:
                    stats["class_count"] = metadata.get("class_count", 0)
                if metadata.get("accuracy") is not None:
                    stats["accuracy"] = metadata.get("accuracy")

            # 回退：部分历史模型把指标保存在顶层字段而不是 metadata
            if not stats["training_time"] and model_data.get("training_time"):
                stats["training_time"] = model_data.get("training_time")
            if not stats["model_version"] and model_data.get("version"):
                stats["model_version"] = model_data.get("version")
            if stats["sample_count"] == 0 and model_data.get("sample_count") is not None:
                stats["sample_count"] = model_data.get("sample_count", 0)
            if stats["class_count"] == 0 and model_data.get("class_count") is not None:
                stats["class_count"] = model_data.get("class_count", 0)
            if stats["accuracy"] is None and model_data.get("accuracy") is not None:
                stats["accuracy"] = model_data.get("accuracy")

            # labels 分布
            labels = model_data.get("labels", [])
            if labels is not None:
                try:
                    label_list = list(labels)
                    if label_list:
                        counts = Counter([str(x) for x in label_list])
                        stats["class_distribution"] = dict(counts)
                        stats["class_labels"] = list(counts.keys())
                        stats["sample_count"] = max(stats["sample_count"], len(label_list))
                        stats["class_count"] = max(stats["class_count"], len(counts))
                except Exception:
                    pass

            # classifier 特征重要性
            classifier = model_data.get("classifier")
            if classifier is not None:
                if hasattr(classifier, "classes_"):
                    try:
                        cls = [str(x) for x in list(classifier.classes_)]
                        if cls and not stats["class_labels"]:
                            stats["class_labels"] = cls
                            stats["class_count"] = max(stats["class_count"], len(cls))
                    except Exception:
                        pass

                if hasattr(classifier, "feature_importances_"):
                    try:
                        fi = list(classifier.feature_importances_)
                        if fi:
                            stats["feature_importances"] = fi
                    except Exception:
                        pass

        # accuracy 展示格式
        if isinstance(stats["accuracy"], (int, float)):
            stats["accuracy_display"] = f"{float(stats['accuracy']):.4f}"

        return stats

    def _plot_and_save_training_visualization(self, stats, model_path):
        """绘制并保存训练结果可视化图像"""
        output_dir = os.path.join("output", "training_visualizations")
        os.makedirs(output_dir, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_path = os.path.abspath(os.path.join(output_dir, f"training_visual_{ts}.png"))

        # 中文字体设置（Windows 优先），避免中文乱码和负号显示异常
        plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "Arial Unicode MS"]
        plt.rcParams["axes.unicode_minus"] = False

        fig, axes = plt.subplots(2, 2, figsize=(14, 9))
        fig.suptitle("模型训练结果可视化", fontsize=14)

        # 左上：摘要信息
        axes[0, 0].axis("off")
        summary_lines = [
            f"模型文件: {os.path.basename(model_path)}",
            f"模型类型: {stats.get('model_type', 'unknown')}",
            f"训练时间: {stats.get('training_time', '') or 'N/A'}",
            f"版本号: {stats.get('model_version', '') or 'N/A'}",
            f"样本数: {stats.get('sample_count', 0)}",
            f"类别数: {stats.get('class_count', 0)}",
            f"准确率: {stats.get('accuracy_display', 'N/A')}",
        ]
        axes[0, 0].text(0.02, 0.98, "\n".join(summary_lines), va="top", fontsize=10)

        # 右上：类别分布
        class_distribution = stats.get("class_distribution", {})
        if class_distribution:
            items = sorted(class_distribution.items(), key=lambda x: x[1], reverse=True)
            labels = [k for k, _ in items][:20]
            values = [v for _, v in items][:20]
            axes[0, 1].bar(range(len(values)), values)
            axes[0, 1].set_title("类别分布（Top20）")
            axes[0, 1].set_xticks(range(len(labels)))
            axes[0, 1].set_xticklabels(labels, rotation=60, ha="right", fontsize=8)
            axes[0, 1].set_ylabel("数量")
        else:
            axes[0, 1].axis("off")
            axes[0, 1].text(0.5, 0.5, "未找到标签分布数据", ha="center", va="center")

        # 左下：特征重要性 Top20
        feature_importances = stats.get("feature_importances", [])
        if feature_importances:
            fi = np.array(feature_importances)
            top_n = min(20, len(fi))
            idx = np.argsort(fi)[-top_n:][::-1]
            vals = fi[idx]
            axes[1, 0].bar(range(top_n), vals)
            axes[1, 0].set_title("特征重要性（Top20）")
            axes[1, 0].set_xlabel("特征排名")
            axes[1, 0].set_ylabel("重要性")
            axes[1, 0].set_xticks(range(top_n))
            axes[1, 0].set_xticklabels([str(i + 1) for i in range(top_n)], fontsize=8)
        else:
            axes[1, 0].axis("off")
            axes[1, 0].text(0.5, 0.5, "未找到特征重要性数据", ha="center", va="center")

        # 右下：类别数量统计
        axes[1, 1].bar(["样本数", "类别数"], [stats.get("sample_count", 0), stats.get("class_count", 0)])
        axes[1, 1].set_title("数据规模")
        axes[1, 1].set_ylabel("数量")

        plt.tight_layout(rect=[0, 0, 1, 0.96])
        fig.savefig(image_path, dpi=150)
        plt.close(fig)

        return image_path

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

        self.excel_processor_btn = QPushButton("Excel表格处理")
        self.excel_processor_btn.clicked.connect(self.open_excel_processor)

        project_buttons_layout.addWidget(self.save_project_btn)
        project_buttons_layout.addWidget(self.load_project_btn)
        project_buttons_layout.addWidget(self.import_coding_tree_btn)
        project_buttons_layout.addWidget(self.excel_processor_btn)

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
        coding_layout.addLayout(search_layout)

        # 连接搜索信号
        self.search_line_edit.returnPressed.connect(self.perform_search)
        search_button.clicked.connect(self.perform_search)

        self.coding_tree = QTreeWidget()
        self.coding_tree.setHeaderLabels(["编码内容", "类型", "数量", "文件来源数", "句子来源数", "关联编号"])
        self.coding_tree.setColumnWidth(0, 300)
        self.coding_tree.setColumnWidth(1, 80)
        self.coding_tree.setColumnWidth(2, 60)
        self.coding_tree.setColumnWidth(3, 80)
        self.coding_tree.setColumnWidth(4, 80)
        self.coding_tree.setColumnWidth(5, 120)
        # 支持多选
        self.coding_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        # 单击仅执行导航和高亮
        self.coding_tree.itemClicked.connect(self.on_tree_item_clicked)
        # 双击一阶编码时弹出句子详情对话框
        self.coding_tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)

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

        self.training_progress = QProgressBar()
        self.training_progress.setVisible(False)
        training_layout.addWidget(self.training_progress)

        self.training_metrics_label = QLabel("")
        self.training_metrics_label.setVisible(False)
        self.training_metrics_label.setStyleSheet("color: #666; font-size: 11px;")
        training_layout.addWidget(self.training_metrics_label)

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

        # 优先显示自动编码缓存的内容（带有一阶编码标记）
        if hasattr(self, 'auto_coding_cache') and file_path in self.auto_coding_cache:
            self.text_display.setText(self.auto_coding_cache[file_path])
            return

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

                # 确保有numbered_content字段
                if 'numbered_content' not in processed_file_data:
                    processed_file_data['numbered_content'] = processed_file_data.get('content', '')

                processed_files[file_path] = processed_file_data

            if not processed_files:
                QMessageBox.warning(self, "警告", "没有有效的文件内容可进行手动编码")
                return

            # 将缓存内容传递给 ManualCodingDialog
            dialog = ManualCodingDialog(self, processed_files, self.structured_codes,
                                        auto_coding_cache=self.auto_coding_cache,
                                        code_markers_map=self.code_markers_map)
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
                    numbered_content, number_mapping = self.data_processor.numbering_manager.number_text(content,
                                                                                                         filename)
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

            # 保存自动编码生成的文本内容到缓存
            self.save_auto_coding_to_cache()

            # 刷新当前显示
            if self.file_list.currentItem():
                self.on_file_selected(self.file_list.currentItem())

            self.statusBar().showMessage("自动编码生成完成")

        except Exception as e:
            self.progress_bar.setVisible(False)
            logger.error(f"自动生成编码失败: {e}")
            QMessageBox.critical(self, "生成错误", f"生成编码失败: {str(e)}")

    def update_progress(self, value):
        """更新进度"""
        self.progress_bar.setValue(value)

    def save_auto_coding_to_cache(self):
        """保存自动编码生成的文本内容到缓存"""
        try:
            # 清空缓存
            self.auto_coding_cache.clear()
            self.code_markers_map.clear()

            # 遍历所有加载的文件
            for file_path, file_data in self.loaded_files.items():
                # 获取文件的编号内容
                numbered_content = file_data.get('numbered_content', '')
                if not numbered_content:
                    continue

                # 复制编号内容作为基础
                content_with_markers = str(numbered_content)

                # 收集本文件相关的所有一阶编码
                first_level_codes = []
                target_filename = file_data.get('filename', os.path.basename(file_path))

                if self.structured_codes:
                    for third_cat, second_cats in self.structured_codes.items():
                        for second_cat, first_contents in second_cats.items():
                            for first_content in first_contents:
                                if isinstance(first_content, dict):
                                    code_id = first_content.get('code_id', '')
                                    if code_id and code_id.startswith('A'):
                                        sentence_details = first_content.get('sentence_details', [])

                                        # 遍历所有句子详情，查找属于当前文件的
                                        has_details = False
                                        for detail in sentence_details:
                                            if isinstance(detail, dict):
                                                has_details = True
                                                if detail.get('filename') == target_filename:
                                                    original_sentence = detail.get('original_content', '')
                                                    if original_sentence:
                                                        first_level_codes.append((code_id, original_sentence))

                                        # 如果没有 sentence_details (旧数据兼容)，尝试匹配内容
                                        if not has_details:
                                            original_sentence = first_content.get('content', '')
                                            if original_sentence:
                                                first_level_codes.append((code_id, original_sentence))

                # 为每个一阶编码添加标记
                import re
                for code_id, original_sentence in first_level_codes:
                    # 清理句子中的编码标记
                    clean_sentence = re.sub(r'\s*\[A\d+\]', '', original_sentence).strip()
                    if not clean_sentence:
                        continue

                    # 尝试多种匹配方式，从最严格到最宽松
                    match = None

                    # 1. 尝试精确匹配
                    sentence_pattern = re.escape(clean_sentence)
                    match = re.search(sentence_pattern, content_with_markers)

                    # 2. 如果精确匹配失败，尝试宽松匹配（忽略部分标点和空格）
                    if not match:
                        # 清理句子，移除标点和多余空格
                        clean_sentence_no_punct = re.sub(r'[，。！？；：、]', '', clean_sentence)
                        clean_sentence_no_punct = re.sub(r'\s+', ' ', clean_sentence_no_punct).strip()
                        if clean_sentence_no_punct:
                            # 创建宽松的正则表达式，允许单词之间有任意空格
                            words = clean_sentence_no_punct.split()
                            if words:
                                # 创建一个正则表达式，允许单词之间有任意数量的空格
                                loose_pattern = r'\s*'.join(re.escape(word) for word in words)
                                match = re.search(loose_pattern, content_with_markers)

                    # 3. 如果仍然失败，尝试匹配句子的核心部分
                    if not match and len(clean_sentence) > 10:
                        # 提取句子的核心部分（去掉开头和结尾的修饰语）
                        core_sentence = clean_sentence
                        # 移除常见的开头修饰语
                        start_modifiers = ['我觉得', '我认为', '我感觉', '我想', '就是说', '然后', '那个', '这个', '就是']
                        for modifier in start_modifiers:
                            if core_sentence.startswith(modifier):
                                core_sentence = core_sentence[len(modifier):].strip()
                                break
                        # 移除常见的结尾修饰语
                        end_modifiers = ['吧', '啊', '呀', '呢', '嘛', '的', '了', '啊']
                        for modifier in end_modifiers:
                            if core_sentence.endswith(modifier):
                                core_sentence = core_sentence[:-len(modifier)].strip()
                                break
                        # 尝试匹配核心部分
                        if len(core_sentence) > 5:
                            core_pattern = re.escape(core_sentence)
                            match = re.search(core_pattern, content_with_markers)

                    if match:
                        # 在句子后添加编码标记
                        start_pos = match.start()
                        end_pos = match.end()
                        modified_content = content_with_markers[:end_pos] + f" [{code_id}]" + content_with_markers[
                                                                                              end_pos:]
                        content_with_markers = modified_content

                        # 保存编码标记映射
                        if file_path not in self.code_markers_map:
                            self.code_markers_map[file_path] = []
                        self.code_markers_map[file_path].append({
                            'code_id': code_id,
                            'sentence': clean_sentence,
                            'start_pos': start_pos,
                            'end_pos': end_pos
                        })
                    else:
                        # 匹配失败，不记录警告
                        pass

                # 保存到缓存
                self.auto_coding_cache[file_path] = content_with_markers
                logger.info(f"已保存自动编码内容到缓存: {os.path.basename(file_path)}")

        except Exception as e:
            logger.error(f"保存自动编码缓存失败: {e}")

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
            # 暂时设置为0，后面会根据子二阶编码累加更新
            third_item.setText(4, "0")  # 句子来源数（稍后更新）

            # Extracts ID like "C01" from "C01 Category"
            third_id_match = re.match(r'^[A-Z]\d+', third_cat)
            third_id_display = third_id_match.group(0) if third_id_match else ""
            third_item.setText(5, third_id_display)  # 关联编号显示自身编号

            third_item.setData(0, Qt.UserRole, {"level": 3, "name": third_cat})

            # 用于累加三阶编码的句子来源数
            third_total_sentence_count = 0

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
                # 暂时设置为0，后面会根据子一阶编码累加更新
                second_item.setText(4, "0")  # 句子来源数（稍后更新）

                # Extracts ID like "B01" from "B01 Category"
                second_id_match = re.match(r'^[A-Z]\d+', second_cat)
                second_id_display = second_id_match.group(0) if second_id_match else ""
                second_item.setText(5, second_id_display)  # 关联编号显示自身编号

                second_item.setData(0, Qt.UserRole, {"level": 2, "name": second_cat, "parent": third_cat})

                # 用于累加二阶编码的句子来源数
                second_total_sentence_count = 0

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

                    # 累加到二阶编码的句子来源数
                    second_total_sentence_count += sentence_source_count

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

                # 更新二阶编码的句子来源数（所有子一阶编码的句子来源数之和）
                second_item.setText(4, str(second_total_sentence_count))
                # 累加到三阶编码的句子来源数
                third_total_sentence_count += second_total_sentence_count

            # 更新三阶编码的句子来源数（所有子二阶编码的句子来源数之和）
            third_item.setText(2, str(len(second_cats)))  # 二阶编码数量
            third_item.setText(4, str(third_total_sentence_count))  # 句子来源数

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
        """树形项目点击事件 - 使用精确高亮功能，仅高亮当前点击的一阶编码内容"""
        item_data = item.data(0, Qt.UserRole)
        if not item_data:
            return

        level = item_data.get("level")
        if level == 1:  # 一阶编码
            sentence_ids = item_data.get("sentence_ids", [])
            code_id = item_data.get("code_id", "")
            content = item_data.get("content", "")
            sentence_details = item_data.get("sentence_details", [])

            # 仅高亮当前点击的一阶编码内容（单一高亮），不再在单击时弹出详情对话框
            # 优先使用第一个句子编号和内容进行精确定位
            if sentence_details and len(sentence_details) > 0:
                # 获取第一个句子的内容和编号
                first_detail = sentence_details[0]
                sent_content = first_detail.get('original_content', '') or first_detail.get('text',
                                                                                            '') or first_detail.get(
                    'content', '')
                sent_number = first_detail.get('sentence_id', '') or first_detail.get('code_id', '')

                # 如果获取到的是编码标识符（如A01），则尝试从sentence_ids获取数字编号
                if sent_number and not sent_number.isdigit() and sentence_ids:
                    sent_number = str(sentence_ids[0]).strip('[]')

                if sent_content:
                    self.navigate_to_sentence_content(sent_content, sent_number)
            elif sentence_ids:
                # 降级方案：仅使用第一个句子编号
                self.highlight_single_sentence_by_id(
                    sentence_ids[0] if isinstance(sentence_ids, list) else sentence_ids)
            elif content:
                # 最后的降级方案：使用内容匹配
                self.navigate_to_sentence_content(content, "")

    def on_tree_item_double_clicked(self, item, column):
        """树节点双击事件 - 双击一阶编码时弹出句子详情对话框"""
        try:
            if not item:
                return

            item_data = item.data(0, Qt.UserRole)
            if not item_data:
                return

            level = item_data.get("level")
            if level != 1:
                # 仅对一阶编码弹出详情对话框
                return

            code_id = item_data.get("code_id", "")
            content = item_data.get("content", "")
            sentence_details = item_data.get("sentence_details", [])

            # 如果code_id缺失，尝试从 sentence_details 中补全
            if not code_id and sentence_details:
                first_detail = sentence_details[0]
                code_id = first_detail.get("code_id", "") or first_detail.get("sentence_id", "")

            self.show_sentence_details_dialog(sentence_details, content, code_id)

        except Exception as e:
            logger.error(f"主界面双击树项目时出错: {e}")

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
                            # 显式触发文件加载
                            self.on_file_selected(item)
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

    def highlight_single_sentence_by_id(self, sentence_id):
        """仅高亮单一句子编号对应的文本（单一高亮模式）"""
        try:
            if not sentence_id:
                return

            # 清理句子ID
            sid = str(sentence_id).strip('[]').strip()
            if not sid:
                return

            # 获取当前显示的文本
            current_text = self.text_display.toPlainText()
            if not current_text:
                return

            # 查找句子编号标记 [N]
            sentence_tag = f"[{sid}]"
            pos = current_text.find(sentence_tag)

            if pos < 0:
                self.statusBar().showMessage(f"未找到句子编号: {sid}")
                return

            # 清除之前的高亮
            self.clear_text_highlights()

            # 计算句子范围
            # 从编号位置向前查找句子开始
            sentence_start = 0
            text_before = current_text[:pos]
            prev_tags = list(re.finditer(r'\[(\d+)\]', text_before))
            if prev_tags:
                prev_end = prev_tags[-1].end()
                text_between = current_text[prev_end:pos]
                code_tags_match = re.match(r'^(\s*\[[A-Z]\d+\])+\s*', text_between)
                if code_tags_match:
                    sentence_start = prev_end + code_tags_match.end()
                else:
                    sentence_start = prev_end

            # 句子结束位置
            sentence_end = pos + len(sentence_tag)
            text_after = current_text[sentence_end:sentence_end + 20]
            code_match = re.match(r'^(\s*\[[A-Z]\d+\])+', text_after)
            if code_match:
                sentence_end += code_match.end()

            # 使用 ExtraSelection 进行单一高亮
            from PyQt5.QtWidgets import QTextEdit

            selection = QTextEdit.ExtraSelection()
            cursor = self.text_display.textCursor()
            cursor.setPosition(sentence_start)
            cursor.setPosition(sentence_end, QTextCursor.KeepAnchor)
            selection.cursor = cursor
            selection.format.setBackground(QColor(173, 216, 230))  # 浅蓝色背景
            selection.format.setForeground(QColor(0, 0, 0))  # 黑色文字

            # 应用单一高亮
            self.text_display.setExtraSelections([selection])

            # 定位到句子位置
            cursor.setPosition(sentence_start)
            self.text_display.setTextCursor(cursor)
            self.text_display.ensureCursorVisible()

            self.statusBar().showMessage(f"已高亮句子 [{sid}]")

        except Exception as e:
            logger.error(f"单一句子高亮失败: {e}", exc_info=True)
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
            # 清除 ExtraSelection 高亮
            self.text_display.setExtraSelections([])

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

        # 显示当前加载的模型信息
        model_info = self.model_manager.get_current_model_info()
        if model_info['name'] != '无':
            self.current_model_label.setText(f"当前加载模型: {model_info['name']} ({model_info['type']})")

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

        # 遍历编码树
        for third_cat, second_cats in self.structured_codes.items():
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

        # 高亮文本内容，优先使用original_content
        self.highlight_search_result_with_original_content(result)

    def locate_and_select_code(self, result):
        """定位并选中编码树中的一阶编码"""
        # 展开所有节点
        self.coding_tree.expandAll()

        # 查找并选中对应的一阶编码
        self.find_and_select_first_level_code(result['third_cat'], result['second_cat'], result['content'])

    def find_and_select_first_level_code(self, third_cat, second_cat, content):
        """查找并选中一阶编码"""

        # 遍历所有节点查找一阶编码
        def search_in_tree(item):
            if not item:
                return False

            # 检查当前节点是否为一阶编码
            item_data = item.data(0, Qt.UserRole)
            if item_data and item_data.get('level') == 1:
                # 检查内容是否匹配
                item_content = item_data.get('content', '')
                if item_content == content:
                    self.coding_tree.setCurrentItem(item)
                    # 确保可见
                    self.coding_tree.scrollToItem(item)
                    return True

            # 递归搜索子节点
            for i in range(item.childCount()):
                if search_in_tree(item.child(i)):
                    return True

            return False

        # 从根节点开始搜索
        for i in range(self.coding_tree.topLevelItemCount()):
            if search_in_tree(self.coding_tree.topLevelItem(i)):
                return

    def highlight_search_result(self, result):
        """高亮搜索结果 - 与手动编码界面一致的精确高亮"""
        content = result['content']
        if content:
            # 清理内容，移除编号标记
            import re
            clean_content = re.sub(r'\s*\[[A-Z]\d+\]', '', content)
            clean_content = re.sub(r'\s*\[\d+\]', '', clean_content)
            clean_content = re.sub(r'^[A-Z]\d+\s+', '', clean_content)
            clean_content = clean_content.strip()

            if clean_content:
                self.navigate_to_sentence_content(clean_content, "")

    def highlight_search_result_with_original_content(self, result):
        """高亮搜索结果，优先使用original_content"""
        # 尝试从content_obj中获取sentence_details，优先使用original_content
        content_obj = result.get('content_obj')
        if isinstance(content_obj, dict):
            sentence_details = content_obj.get('sentence_details', [])
            if sentence_details and len(sentence_details) > 0:
                first_detail = sentence_details[0]
                original_content = first_detail.get('text', '') or first_detail.get('original_content', '')
                if original_content:
                    # 清理内容
                    import re
                    clean_content = re.sub(r'\s*\[[A-Z]\d+\]', '', original_content)
                    clean_content = re.sub(r'\s*\[\d+\]', '', clean_content)
                    clean_content = re.sub(r'^[A-Z]\d+\s+', '', clean_content)
                    clean_content = clean_content.strip()

                    if clean_content:
                        self.navigate_to_sentence_content(clean_content, "")
                        return

        # 如果没有original_content，使用原始的高亮方法
        self.highlight_search_result(result)

    def highlight_text_content(self, content):
        """在文本中高亮内容 - 与手动编码界面一致的精确高亮"""
        if not content or len(content) < 2:
            return

        # 使用与手动编码界面相同的精确高亮方法
        self.navigate_to_sentence_content(content, "")

    def show_tree_context_menu(self, position):
        """显示树形控件上下文菜单"""
        from PyQt5.QtWidgets import QMenu, QAction

        menu = QMenu()

        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(self.edit_selected_code)
        menu.addAction(edit_action)

        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self.delete_selected_code)
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

                # 一阶且有二阶父节点 → 可修改父节点(二阶)
                if clicked_level == 1 and clicked_parent:
                    parent_data = clicked_parent.data(0, Qt.UserRole)
                    if parent_data and parent_data.get("level") == 2:
                        menu.addSeparator()
                        move_first_action = QAction("修改一阶对应父节点(二阶)", self)
                        move_first_action.triggered.connect(self.move_first_to_new_parent_second)
                        menu.addAction(move_first_action)
                # 一阶且无父节点（未分类）→ 也提供"修改一阶对应父节点(二阶)"功能
                elif clicked_level == 1 and not clicked_parent:
                    menu.addSeparator()
                    move_first_unclassified_action = QAction("修改一阶对应父节点(二阶)", self)
                    move_first_unclassified_action.triggered.connect(self.move_first_to_new_parent_second)
                    menu.addAction(move_first_unclassified_action)

                # 二阶且有三阶父节点 → 可修改父节点(三阶)
                elif clicked_level == 2 and clicked_parent:
                    parent_data = clicked_parent.data(0, Qt.UserRole)
                    if parent_data and parent_data.get("level") == 3:
                        menu.addSeparator()
                        move_second_action = QAction("修改二阶对应父节点(三阶)", self)
                        move_second_action.triggered.connect(self.move_second_to_new_parent_third)
                        menu.addAction(move_second_action)
                # 二阶且无父节点（未分类）→ 也提供"修改二阶对应父节点(三阶)"功能
                elif clicked_level == 2 and not clicked_parent:
                    menu.addSeparator()
                    move_second_unclassified_action = QAction("修改二阶对应父节点(三阶)", self)
                    move_second_unclassified_action.triggered.connect(self.move_second_to_new_parent_third)
                    menu.addAction(move_second_unclassified_action)

        menu.exec_(self.coding_tree.viewport().mapToGlobal(position))

    def edit_selected_code(self):
        """编辑选中的编码 - 增大弹窗"""
        current_items = self.coding_tree.selectedItems()
        if not current_items:
            QMessageBox.information(self, "提示", "请先选择一个编码")
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

    def delete_selected_code(self):
        """删除选中的编码 - 支持批量删除"""
        selected_items = self.coding_tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择一个或多个节点")
            return

        # 统计选中的编码类型
        level_counts = {1: 0, 2: 0, 3: 0}
        for item in selected_items:
            item_data = item.data(0, Qt.UserRole)
            if item_data:
                level = item_data.get("level")
                if level in level_counts:
                    level_counts[level] += 1

        # 构建确认消息
        msg_parts = []
        if level_counts[3] > 0:
            msg_parts.append(f"{level_counts[3]} 个三阶编码")
        if level_counts[2] > 0:
            msg_parts.append(f"{level_counts[2]} 个二阶编码")
        if level_counts[1] > 0:
            msg_parts.append(f"{level_counts[1]} 个一阶编码")

        msg = f"确定要删除选中的 {', '.join(msg_parts)} 吗？\n\n"
        msg += "删除三阶编码会将其下的二阶编码变为未分类状态\n"
        msg += "删除二阶编码会同时删除其下的一阶编码"

        reply = QMessageBox.question(self, "确认删除", msg, QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            # 批量处理删除操作
            for item in selected_items:
                item_data = item.data(0, Qt.UserRole)
                if not item_data:
                    continue

                level = item_data.get("level")

                # 处理三阶编码删除的情况：将其二阶子节点移到顶层
                if level == 3:
                    # 收集所有二阶子节点
                    second_level_items = []
                    while item.childCount() > 0:
                        second_item = item.takeChild(0)
                        second_level_items.append(second_item)

                    # 将二阶子节点移到顶层
                    for child_item in second_level_items:
                        self.coding_tree.addTopLevelItem(child_item)

                    # 为未分类的二阶编码重新编序
                    self.reorder_unclassified_second_codes()

                # 从界面删除项目
                parent = item.parent()
                if parent:
                    parent.removeChild(item)
                    # 更新父级节点的句子来源数
                    self.update_statistics_for_item(parent)
                else:
                    # 顶层项目
                    root = self.coding_tree.invisibleRootItem()
                    root.removeChild(item)

            # 仅更新数据结构，避免重建整个树
            self.update_structured_codes_from_tree()
            # 重新编号所有编码，确保编号递增
            self.renumber_all_codes()

            # 显示删除成功消息
            deleted_count = len(selected_items)
            self.statusBar().showMessage(f"已成功删除 {deleted_count} 个编码")
            logger.info(f"批量删除 {deleted_count} 个编码")

    def update_statistics_after_deletion(self, parent_item, deleted_level):
        """删除后更新统计信息，避免重建整个树"""
        if not parent_item:
            # 如果删除的是顶级项目，更新总体统计
            total_third = len(self.structured_codes)
            total_second = sum(len(cats) for cats in self.structured_codes.values())
            total_first = sum(len(contents) for cats in self.structured_codes.values() for contents in cats.values())
            self.statusBar().showMessage(f"编码结构: {total_third}三阶, {total_second}二阶, {total_first}一阶")

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
                else:
                    QMessageBox.warning(self, "警告", "请只选择一阶编码")
                    return

            if not first_level_items:
                QMessageBox.warning(self, "警告", "请选择至少一个一阶编码")
                return

            # 弹出对话框让用户输入二阶编码名称
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QDialogButtonBox, QComboBox, \
                QHBoxLayout

            dialog = QDialog(self)
            dialog.setWindowTitle("添加二阶编码作为父节点")
            dialog.resize(600, 500)

            layout = QVBoxLayout(dialog)

            label = QLabel(f"为 {len(first_level_items)} 个一阶编码添加二阶父节点")
            layout.addWidget(label)

            # 显示选中的一阶编码列表
            list_widget = QListWidget()
            for item in first_level_items:
                list_item = QListWidgetItem(item.text(0))
                list_widget.addItem(list_item)
            layout.addWidget(list_widget)

            # 二阶编码输入
            second_layout = QHBoxLayout()
            second_label = QLabel("二阶编码名称:")
            second_edit = QTextEdit()
            second_edit.setMinimumHeight(100)
            second_layout.addWidget(second_label)
            second_layout.addWidget(second_edit)
            layout.addLayout(second_layout)

            # 三阶编码选择
            third_layout = QHBoxLayout()
            third_label = QLabel("所属三阶编码:")
            third_combo = QComboBox()
            third_combo.setEditable(True)
            # 添加现有三阶编码
            for i in range(self.coding_tree.topLevelItemCount()):
                top_item = self.coding_tree.topLevelItem(i)
                top_data = top_item.data(0, Qt.UserRole)
                if top_data and top_data.get("level") == 3:
                    third_combo.addItem(top_item.text(0))
            third_layout.addWidget(third_label)
            third_layout.addWidget(third_combo)
            layout.addLayout(third_layout)

            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)

            if dialog.exec_() != QDialog.Accepted:
                return

            second_name = second_edit.toPlainText().strip()
            third_name = third_combo.currentText().strip()

            if not second_name:
                QMessageBox.warning(self, "警告", "二阶编码名称不能为空")
                return

            # 验证二阶编码名称
            is_valid, clean_second, error_msg = self.validate_category_name(second_name, "second")
            if not is_valid:
                QMessageBox.warning(self, "验证错误", error_msg)
                return

            # 验证三阶编码名称
            if third_name:
                is_valid, clean_third, error_msg = self.validate_category_name(third_name, "third")
                if not is_valid:
                    QMessageBox.warning(self, "验证错误", error_msg)
                    return
            else:
                clean_third = ""

            # 处理三阶编码
            third_item = None
            if clean_third:
                # 查找或创建三阶编码
                found = False
                for i in range(self.coding_tree.topLevelItemCount()):
                    top_item = self.coding_tree.topLevelItem(i)
                    top_data = top_item.data(0, Qt.UserRole)
                    if top_data and top_data.get("level") == 3 and top_item.text(0) == clean_third:
                        third_item = top_item
                        found = True
                        break
                if not found:
                    # 创建新的三阶编码
                    third_code_id = self.generate_third_code_id()
                    third_item = QTreeWidgetItem(self.coding_tree)
                    third_item.setText(0, f"{third_code_id} {clean_third}")
                    third_item.setText(1, "三阶编码")
                    third_item.setText(2, "0")
                    third_item.setText(3, "0")
                    third_item.setText(4, "0")
                    third_item.setText(5, third_code_id)
                    third_item.setData(0, Qt.UserRole, {"level": 3, "name": clean_third, "code_id": third_code_id})
            else:
                # 没有指定三阶编码，二阶编码将作为顶层项目
                pass

            # 处理二阶编码
            second_item = None
            if third_item:
                # 在三阶编码下查找或创建二阶编码
                found = False
                for i in range(third_item.childCount()):
                    child_item = third_item.child(i)
                    child_data = child_item.data(0, Qt.UserRole)
                    if child_data and child_data.get("level") == 2 and child_item.text(0) == clean_second:
                        second_item = child_item
                        found = True
                        break
                if not found:
                    # 创建新的二阶编码
                    second_code_id = self.generate_second_code_id(parent_node=third_item)
                    second_item = QTreeWidgetItem(third_item)
                    second_item.setText(0, f"{second_code_id} {clean_second}")
                    second_item.setText(1, "二阶编码")
                    second_item.setText(2, "0")
                    second_item.setText(3, "")
                    second_item.setText(4, "0")
                    second_item.setText(5, second_code_id)
                    second_item.setData(0, Qt.UserRole, {"level": 2, "name": clean_second, "code_id": second_code_id,
                                                         "parent": third_item.text(0)})
                    # 更新三阶编码的二阶编码数量
                    third_item.setText(2, str(third_item.childCount()))
            else:
                # 作为顶层二阶编码查找或创建
                found = False
                for i in range(self.coding_tree.topLevelItemCount()):
                    top_item = self.coding_tree.topLevelItem(i)
                    top_data = top_item.data(0, Qt.UserRole)
                    if top_data and top_data.get("level") == 2 and top_item.text(0) == clean_second:
                        second_item = top_item
                        found = True
                        break
                if not found:
                    # 创建新的顶层二阶编码
                    second_code_id = self.generate_second_code_id()
                    second_item = QTreeWidgetItem(self.coding_tree)
                    second_item.setText(0, f"{second_code_id} {clean_second}")
                    second_item.setText(1, "二阶编码")
                    second_item.setText(2, "0")
                    second_item.setText(3, "")
                    second_item.setText(4, "0")
                    second_item.setText(5, second_code_id)
                    second_item.setData(0, Qt.UserRole, {"level": 2, "name": clean_second, "code_id": second_code_id})

            # 将一阶编码移动到二阶编码下
            for first_item in first_level_items:
                # 从原位置移除
                parent = first_item.parent()
                if parent:
                    parent.removeChild(first_item)
                    # 更新原父节点的统计信息
                    self.update_statistics_for_item(parent)
                else:
                    index = self.coding_tree.indexOfTopLevelItem(first_item)
                    self.coding_tree.takeTopLevelItem(index)

                # 添加到新的二阶编码下
                second_item.addChild(first_item)
                # 更新一阶编码的父节点信息
                first_data = first_item.data(0, Qt.UserRole)
                if first_data:
                    first_data["parent"] = second_item.text(0)
                    if third_item:
                        first_data["core_category"] = third_item.text(0)
                    first_item.setData(0, Qt.UserRole, first_data)

                # 更新二阶编码的统计信息
                second_item.setText(2, str(second_item.childCount()))
                # 更新二阶编码的句子来源数
                self.update_statistics_for_item(second_item)

                logger.info(f"将一阶编码 '{first_item.text(0)}' 移动到二阶编码 '{second_item.text(0)}' 下")

            # 更新三阶编码的统计信息
            if third_item:
                self.update_statistics_for_item(third_item)

            # 更新编码结构
            self.update_structured_codes_from_tree()

            QMessageBox.information(self, "成功", f"已为 {len(first_level_items)} 个一阶编码添加父节点二阶编码 '{clean_second}'")

        except Exception as e:
            logger.error(f"添加父节点二阶编码失败: {e}")
            QMessageBox.critical(self, "错误", f"添加父节点失败: {str(e)}")

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
                else:
                    QMessageBox.warning(self, "警告", "请只选择二阶编码")
                    return

            if not second_level_items:
                QMessageBox.warning(self, "警告", "请选择至少一个二阶编码")
                return

            # 弹出对话框让用户输入三阶编码名称
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QDialogButtonBox

            dialog = QDialog(self)
            dialog.setWindowTitle("添加三阶编码作为父节点")
            dialog.resize(600, 500)

            layout = QVBoxLayout(dialog)

            label = QLabel(f"为 {len(second_level_items)} 个二阶编码添加三阶父节点")
            layout.addWidget(label)

            # 显示选中的二阶编码列表
            list_widget = QListWidget()
            for item in second_level_items:
                list_item = QListWidgetItem(item.text(0))
                list_widget.addItem(list_item)
            layout.addWidget(list_widget)

            # 三阶编码输入
            third_label = QLabel("三阶编码名称:")
            layout.addWidget(third_label)

            third_edit = QTextEdit()
            third_edit.setMinimumHeight(100)
            layout.addWidget(third_edit)

            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)

            if dialog.exec_() != QDialog.Accepted:
                return

            third_name = third_edit.toPlainText().strip()

            if not third_name:
                QMessageBox.warning(self, "警告", "三阶编码名称不能为空")
                return

            # 验证三阶编码名称
            is_valid, clean_third, error_msg = self.validate_category_name(third_name, "third")
            if not is_valid:
                QMessageBox.warning(self, "验证错误", error_msg)
                return

            # 查找或创建三阶编码
            third_item = None
            found = False
            for i in range(self.coding_tree.topLevelItemCount()):
                top_item = self.coding_tree.topLevelItem(i)
                top_data = top_item.data(0, Qt.UserRole)
                if top_data and top_data.get("level") == 3 and top_item.text(0) == clean_third:
                    third_item = top_item
                    found = True
                    break
            if not found:
                # 创建新的三阶编码
                third_code_id = self.generate_third_code_id()
                third_item = QTreeWidgetItem(self.coding_tree)
                third_item.setText(0, f"{third_code_id} {clean_third}")
                third_item.setText(1, "三阶编码")
                third_item.setText(2, "0")
                third_item.setText(3, "0")
                third_item.setText(4, "0")
                third_item.setText(5, third_code_id)
                third_item.setData(0, Qt.UserRole, {"level": 3, "name": clean_third, "code_id": third_code_id})

            # 将二阶编码移动到三阶编码下
            for second_item in second_level_items:
                # 从原位置移除
                parent = second_item.parent()
                if parent:
                    parent.removeChild(second_item)
                else:
                    index = self.coding_tree.indexOfTopLevelItem(second_item)
                    self.coding_tree.takeTopLevelItem(index)

                # 添加到新的三阶编码下
                third_item.addChild(second_item)
                # 更新二阶编码的父节点信息
                second_data = second_item.data(0, Qt.UserRole)
                if second_data:
                    second_data["parent"] = third_item.text(0)
                    second_item.setData(0, Qt.UserRole, second_data)

                # 更新三阶编码的二阶编码数量
                third_item.setText(2, str(third_item.childCount()))
                # 更新二阶编码的统计信息
                self.update_statistics_for_item(second_item)

                logger.info(f"将二阶编码 '{second_item.text(0)}' 移动到三阶编码 '{third_item.text(0)}' 下")

            # 更新三阶编码的统计信息
            self.update_statistics_for_item(third_item)

            # 更新编码结构
            self.update_structured_codes_from_tree()

            QMessageBox.information(self, "成功", f"已为 {len(second_level_items)} 个二阶编码添加父节点三阶编码 '{clean_third}'")

        except Exception as e:
            logger.error(f"添加父节点三阶编码失败: {e}")
            QMessageBox.critical(self, "错误", f"添加父节点失败: {str(e)}")

    def move_first_to_new_parent_second(self):
        """修改一阶编码的父节点（二阶），允许移动到另一个二阶编码下 - 支持批量操作"""
        try:
            selected_items = self.coding_tree.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "提示", "请先选中至少一个一阶编码")
                return

            # 收集所有选中的一阶编码
            first_level_items = []
            for item in selected_items:
                item_data = item.data(0, Qt.UserRole)
                if item_data and item_data.get("level") == 1:
                    first_level_items.append(item)

            if not first_level_items:
                QMessageBox.warning(self, "警告", "请选中至少一个一阶编码")
                return

            # 只需要获取第一个一阶编码的父节点作为参考
            old_parent = first_level_items[0].parent()

            # 收集所有二阶编码（带三阶父节点信息）
            # 结构: [(third_item_or_None, [second_item, ...]), ...]
            third_second_list = []
            orphan_seconds = []  # 没有三阶父节点的二阶编码
            for i in range(self.coding_tree.topLevelItemCount()):
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

            label = QLabel(f"为 {len(first_level_items)} 个一阶编码选择新的二阶父节点：\n（点击二阶编码行进行选择）")
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

                new_second_item = selected_second[0]

                # 处理所有选中的一阶编码
                for first_item in first_level_items:
                    # 先从原父节点移除
                    current_old_parent = first_item.parent()
                    if current_old_parent:
                        current_old_parent.removeChild(first_item)
                        # 更新原父节点的统计信息
                        self.update_statistics_for_item(current_old_parent)
                        # 检查原父节点是否有父节点（三阶），如果有则更新其统计信息
                        old_third_item = current_old_parent.parent()
                        if old_third_item:
                            self.update_statistics_for_item(old_third_item)
                    else:
                        # 从顶层移除
                        root = self.coding_tree.invisibleRootItem()
                        for i in range(root.childCount()):
                            if root.child(i) == first_item:
                                root.removeChild(first_item)
                                break

                    # 添加到新父节点
                    new_second_item.addChild(first_item)
                    # 更新一阶编码的父节点信息
                    first_data = first_item.data(0, Qt.UserRole)
                    if first_data:
                        first_data["parent"] = new_second_item.text(0)
                        # 检查新父节点是否有父节点（三阶）
                        new_third_item = new_second_item.parent()
                        if new_third_item:
                            first_data["core_category"] = new_third_item.text(0)
                        else:
                            first_data.pop("core_category", None)
                        first_item.setData(0, Qt.UserRole, first_data)

                # 更新新父节点的统计信息
                new_second_item.setText(2, str(new_second_item.childCount()))
                self.update_statistics_for_item(new_second_item)

                # 检查新父节点是否有父节点（三阶），如果有则更新其统计信息
                new_third_item = new_second_item.parent()
                if new_third_item:
                    self.update_statistics_for_item(new_third_item)

                # 更新编码结构
                self.update_structured_codes_from_tree()
                # 全局重新编号
                self.renumber_all_codes()

                QMessageBox.information(self, "成功", f"已将 {len(first_level_items)} 个一阶编码移动到：{new_second_item.text(0)}")
                dialog.accept()

            ok_btn.clicked.connect(on_ok)
            cancel_btn.clicked.connect(dialog.reject)
            dialog.exec_()

            return

        except Exception as e:
            logger.error(f"修改一阶编码父节点失败: {e}")
            QMessageBox.critical(self, "错误", f"修改父节点失败: {str(e)}")
            return

    def move_second_to_new_parent_third(self):
        """修改二阶编码的父节点（三阶），允许移动到另一个三阶编码下 - 支持批量操作"""
        try:
            selected_items = self.coding_tree.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "提示", "请先选中至少一个二阶编码")
                return

            # 收集所有选中的二阶编码
            second_level_items = []
            for item in selected_items:
                item_data = item.data(0, Qt.UserRole)
                if item_data and item_data.get("level") == 2:
                    second_level_items.append(item)

            if not second_level_items:
                QMessageBox.warning(self, "警告", "请选中至少一个二阶编码")
                return

            # 只需要获取第一个二阶编码的父节点作为参考
            old_parent = second_level_items[0].parent()

            # 收集所有三阶编码
            third_nodes = []
            root_count = self.coding_tree.topLevelItemCount()
            for i in range(root_count):
                top = self.coding_tree.topLevelItem(i)
                top_data = top.data(0, Qt.UserRole)
                # 允许从“未分类”状态移动到任意三阶，因此只排除当前已是父节点的情况
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

            label = QLabel(f"为 {len(second_level_items)} 个二阶编码选择新的三阶父节点：\n（点击三阶编码行进行选择）")
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

                new_third_item = selected_third[0]

                # 处理所有选中的二阶编码
                for second_item in second_level_items:
                    # 获取当前二阶编码的父节点
                    current_old_parent = second_item.parent()

                    # 如果原来有父节点，则先从旧父节点移除；
                    # 如果是未分类二阶（顶层节点），则从顶层列表中移除
                    if current_old_parent is not None:
                        current_old_parent.removeChild(second_item)
                        # 更新原父节点的统计信息
                        self.update_statistics_for_item(current_old_parent)
                    else:
                        # 尝试从顶层列表中取出该二阶节点
                        top_index = self.coding_tree.indexOfTopLevelItem(second_item)
                        if top_index >= 0:
                            self.coding_tree.takeTopLevelItem(top_index)

                    # 添加到新三阶下
                    new_third_item.addChild(second_item)

                    # 更新二阶编码数据
                    sd = second_item.data(0, Qt.UserRole)
                    sd["parent"] = new_third_item.text(0)
                    second_item.setData(0, Qt.UserRole, sd)

                    # 更新二阶编码的统计信息
                    self.update_statistics_for_item(second_item)

                # 更新新父节点的统计信息
                new_third_item.setText(2, str(new_third_item.childCount()))
                self.update_statistics_for_item(new_third_item)

                # 更新编码结构
                self.update_structured_codes_from_tree()
                # 全局重新编号
                self.renumber_all_codes()

                QMessageBox.information(self, "成功", f"已将 {len(second_level_items)} 个二阶编码移动到：{new_third_item.text(0)}")
                dialog.accept()

            ok_btn.clicked.connect(on_ok)
            cancel_btn.clicked.connect(dialog.reject)
            dialog.exec_()

            return

        except Exception as e:
            logger.error(f"修改二阶编码父节点失败: {e}")
            QMessageBox.critical(self, "错误", f"修改父节点失败: {str(e)}")
            return

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

    def reorder_unclassified_second_codes(self):
        """为未分类的二阶编码重新编序"""
        try:
            # 收集所有顶层的二阶编码
            second_level_items = []
            for i in range(self.coding_tree.topLevelItemCount()):
                item = self.coding_tree.topLevelItem(i)
                item_data = item.data(0, Qt.UserRole)
                if item_data and item_data.get("level") == 2:
                    second_level_items.append(item)

            # 按当前编号排序
            import re
            def get_second_code_number(item):
                text = item.text(0)
                match = re.match(r'^[A-Z](\d{2})', text.split(' ')[0])
                if match:
                    return int(match.group(1))
                return 999

            second_level_items.sort(key=get_second_code_number)

            # 重新编号
            for i, item in enumerate(second_level_items, 1):
                # 提取原始名称
                text = item.text(0)
                parts = text.split(' ', 1)
                if len(parts) > 1:
                    name = parts[1]
                else:
                    name = text

                # 生成新编号
                new_code_id = f"B{i:02d}"
                new_text = f"{new_code_id} {name}"
                item.setText(0, new_text)
                item.setText(5, new_code_id)

                # 更新数据
                item_data = item.data(0, Qt.UserRole)
                if item_data:
                    item_data["code_id"] = new_code_id
                    item.setData(0, Qt.UserRole, item_data)

            logger.info(f"已为 {len(second_level_items)} 个未分类二阶编码重新编序")

        except Exception as e:
            logger.error(f"重新编序未分类二阶编码失败: {e}")

    def update_statistics_for_item(self, item):
        """更新项目的统计信息"""
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
            logger.error(f"更新项目统计信息失败: {e}")
            return

    def update_parent_statistics(self, item):
        """更新指定项目及其父项目的统计信息"""
        if not item:
            return

        item_data = item.data(0, Qt.UserRole)
        if not item_data:
            return

        level = item_data.get("level", 0)

        if level == 2:  # 二阶编码
            # 重新统计一阶编码数量和句子来源数
            child_count = item.childCount()
            total_sentence_count = 0

            for i in range(child_count):
                child_item = item.child(i)
                sentence_count_text = child_item.text(4)
                try:
                    sentence_count = int(sentence_count_text) if sentence_count_text.isdigit() else 0
                    total_sentence_count += sentence_count
                except:
                    total_sentence_count += 1  # 默认值

            item.setText(2, str(child_count))  # 一阶编码数量
            item.setText(4, str(total_sentence_count))  # 句子来源数

            # 递归更新父项目（三阶编码）
            parent_item = item.parent()
            if parent_item:
                self.update_parent_statistics(parent_item)

        elif level == 3:  # 三阶编码
            # 重新统计二阶编码数量和句子来源数
            child_count = item.childCount()
            total_sentence_count = 0

            for i in range(child_count):
                child_item = item.child(i)
                sentence_count_text = child_item.text(4)
                try:
                    sentence_count = int(sentence_count_text) if sentence_count_text.isdigit() else 0
                    total_sentence_count += sentence_count
                except:
                    pass

            item.setText(2, str(child_count))  # 二阶编码数量
            item.setText(4, str(total_sentence_count))  # 句子来源数

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

            # 更新编码结构
            self.update_structured_codes_from_tree()
            logger.info(f"全局重新编号完成：三阶共 {third_counter} 个，一阶共 {first_counter[0]} 个")

        except Exception as e:
            logger.error(f"renumber_all_codes 失败: {e}")
            import traceback
            traceback.print_exc()

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
                    # 优先获取完整的数据结构（字典格式）
                    first_item_data = first_item.data(0, Qt.UserRole)
                    if first_item_data and isinstance(first_item_data, dict):
                        # 使用完整的数据结构
                        import copy
                        self.structured_codes[third_name][second_name].append(copy.deepcopy(first_item_data))
                    else:
                        # 后备方案：使用文本内容
                        first_content = first_item.text(0)
                        self.structured_codes[third_name][second_name].append(first_content)

        # 添加日志，方便调试
        logger.info(f"Updated structured codes from tree. Total third: {len(self.structured_codes)}")

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
            # 检查是否有已加载的模型，而不是检查文件是否存在
            has_existing_model = self.model_manager.is_trained_model_available()

            config_dialog = TrainingConfigDialog(self, has_existing_model=has_existing_model)
            if config_dialog.exec_() != QDialog.Accepted:
                return

            config = config_dialog.get_config()
            logger.info(f"训练配置: {config}")

            self.training_progress.setVisible(True)
            self.train_model_btn.setEnabled(False)
            self.training_progress.setFormat("准备训练数据... %p%")
            self.training_progress.setValue(0)

            if hasattr(self, 'training_metrics_label') and self.training_metrics_label:
                self.training_metrics_label.setVisible(True)
                self.training_metrics_label.setText("准备中...")

            training_data = self.standard_answer_manager.export_for_training()

            training_mode = config['training_mode']

            if training_mode == 'incremental':
                self._start_incremental_training(config, training_data)
            elif config['enable_optimization']:
                self._start_training_with_optimization(config, training_data)
            elif training_mode == 'bert_finetune':
                self._start_bert_finetune_training(config, training_data)
            else:
                self._start_classifier_training(config, training_data)

            mode_names = {
                'bert_finetune': 'BERT微调',
                'classifier': '分类器训练',
                'incremental': '增量训练'
            }
            self.statusBar().showMessage(f"开始训练模型... 模式: {mode_names.get(training_mode, training_mode)}")

        except Exception as e:
            logger.error(f"开始训练失败: {e}")
            QMessageBox.critical(self, "训练错误", f"开始训练失败: {str(e)}")
            self.train_model_btn.setEnabled(True)
            self.training_progress.setVisible(False)
            if hasattr(self, 'training_metrics_label') and self.training_metrics_label:
                self.training_metrics_label.setVisible(False)

    def _start_bert_finetune_training(self, config, training_data):
        """启动BERT微调训练"""
        try:
            self.training_progress.setFormat("BERT微调训练中... %p%")

            self.enhanced_training_manager.train_grounded_theory_model(
                training_data,
                self.model_manager,
                progress_callback=lambda v: self.update_training_progress_with_stage(v, "BERT微调"),
                finished_callback=self.on_training_finished,
                model_type='bert',
                training_mode='bert_finetune',
                training_config=config
            )
        except Exception as e:
            logger.error(f"BERT微调训练启动失败: {e}")
            raise

    def _start_classifier_training(self, config, training_data):
        """启动分类器训练"""
        try:
            self.training_progress.setFormat("分类器训练中... %p%")

            self.enhanced_training_manager.train_grounded_theory_model(
                training_data,
                self.model_manager,
                progress_callback=lambda v: self.update_training_progress_with_stage(v, "分类器训练"),
                finished_callback=self.on_training_finished,
                model_type='bert',
                training_mode='classifier',
                training_config=config
            )
        except Exception as e:
            logger.error(f"分类器训练启动失败: {e}")
            raise

    def _start_incremental_training(self, config, training_data):
        """启动增量训练"""
        try:
            self.training_progress.setFormat("增量训练中... %p%")

            # 使用BERT_FINETUNE模式进行增量训练，设置fallback_to_classifier为False
            self.enhanced_training_manager.train_grounded_theory_model(
                training_data,
                self.model_manager,
                progress_callback=lambda v: self.update_training_progress_with_stage(v, "增量训练"),
                finished_callback=self.on_training_finished,
                model_type='bert',
                training_mode=Config.TRAINING_MODE_BERT_FINETUNE,
                fallback_to_classifier=False,
                training_config=config,
                incremental=True
            )
        except Exception as e:
            logger.error(f"增量训练启动失败: {e}")
            raise

    def _start_training_with_optimization(self, config, training_data):
        """启动带超参数寻优的训练"""
        try:
            self.training_progress.setFormat("超参数寻优中... %p%")
            self.training_progress.setValue(0)

            optimizer = HyperparameterOptimizer(self.model_manager)

            def progress_callback(current, total, params):
                progress = int((current / total) * 100)
                self.training_progress.setValue(progress)
                self.training_progress.setFormat(f"寻优进度 {current}/{total}: {params}")
                QApplication.processEvents()

            if config['optimization_method'] == 'grid':
                best_params = optimizer.grid_search(
                    training_data,
                    cv_folds=config['cv_folds'],
                    progress_callback=progress_callback
                )
            else:
                best_params = optimizer.bayesian_optimization(
                    training_data,
                    n_trials=20,
                    cv_folds=config['cv_folds'],
                    progress_callback=progress_callback
                )

            if best_params:
                config.update(best_params)
                QMessageBox.information(
                    self,
                    "寻优完成",
                    f"找到最优参数:\n"
                    f"学习率: {best_params.get('learning_rate', 'N/A')}\n"
                    f"批次大小: {best_params.get('batch_size', 'N/A')}\n"
                    f"训练轮数: {best_params.get('epochs', 'N/A')}\n\n"
                    f"将使用最优参数开始训练..."
                )

                self._start_bert_finetune_training(config, training_data)
            else:
                raise Exception("超参数寻优失败，未找到有效参数")

        except Exception as e:
            logger.error(f"超参数寻优训练失败: {e}")
            raise

    def update_training_progress_with_stage(self, value, stage=""):
        """更新训练进度（带阶段信息）"""
        self.training_progress.setValue(value)
        if stage:
            self.training_progress.setFormat(f"{stage} - %p%")
        self.statusBar().showMessage(f"训练进度: {value}% - {stage}")

    def update_training_progress(self, value):
        """更新训练进度"""
        self.training_progress.setValue(value)

    def update_training_metrics(self, metrics: dict):
        """更新训练指标显示"""
        if hasattr(self, 'training_metrics_label') and self.training_metrics_label:
            metrics_text = []
            if 'loss' in metrics:
                metrics_text.append(f"Loss: {metrics['loss']:.4f}")
            if 'accuracy' in metrics:
                metrics_text.append(f"Acc: {metrics['accuracy']:.2%}")
            if 'f1' in metrics:
                metrics_text.append(f"F1: {metrics['f1']:.4f}")
            if 'epoch' in metrics:
                metrics_text.append(f"Epoch: {metrics['epoch']}")
            if 'eta' in metrics:
                metrics_text.append(f"ETA: {metrics['eta']}")

            self.training_metrics_label.setText(" | ".join(metrics_text))

    def on_training_finished(self, success, message):
        """训练完成"""
        self.train_model_btn.setEnabled(True)
        self.training_progress.setVisible(False)

        if hasattr(self, 'training_metrics_label') and self.training_metrics_label:
            self.training_metrics_label.setVisible(False)

        if success:
            self.statusBar().showMessage("模型训练完成")
            self.model_type_combo.setCurrentText("训练模型编码")
            QMessageBox.information(self, "训练完成", message)
        else:
            QMessageBox.critical(self, "训练失败", message)

    def save_corrections(self):
        """保存修正到标准答案 - 使用增量保存"""
        try:
            # 先从树形结构同步最新数据
            self.update_structured_codes_from_tree()

            if not self.structured_codes:
                QMessageBox.warning(self, "警告", "没有编码数据可保存")
                return

            confirmation_dialog = QDialog(self)
            confirmation_dialog.setWindowTitle("确认保存修改")
            confirmation_dialog.resize(500, 300)

            layout = QVBoxLayout(confirmation_dialog)

            if self.standard_answer_manager.current_answers:
                try:
                    # 调试：记录当前用于对比的标准答案版本
                    try:
                        meta = self.standard_answer_manager.current_answers.get("metadata", {})
                        logger.info(f"save_corrections 基线版本: {meta.get('version')}")
                    except Exception:
                        pass

                    current_codes = self.standard_answer_manager.current_answers.get("structured_codes", {})

                    # 调试：专门检查 A21/A22 所在路径的差异
                    try:
                        third = "组织管理与架构设计"
                        second = "团队职责与架构"
                        orig_list = current_codes.get(third, {}).get(second, [])
                        new_list = self.structured_codes.get(third, {}).get(second, [])

                        def _ids(lst):
                            ids = []
                            for it in lst:
                                if isinstance(it, dict):
                                    ids.append(it.get('code_id') or it.get('number') or it.get('id'))
                                else:
                                    ids.append(str(it)[:20])
                            return ids

                        logger.info(
                            "save_corrections 路径[%s > %s] 原始数量=%d, 新数量=%d, 原始ID前20=%s, 新ID前20=%s",
                            third, second,
                            len(orig_list), len(new_list),
                            _ids(orig_list)[:20], _ids(new_list)[:20],
                        )
                    except Exception as e:
                        logger.warning(f"save_corrections 差异调试失败: {e}")

                    modifications = self.standard_answer_manager._analyze_modifications(current_codes,
                                                                                        self.structured_codes)

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
                except Exception as e:
                    logger.error(f"分析修改内容失败: {e}")
                    stats_label = QLabel("无法分析修改统计，但可以继续保存")
                    layout.addWidget(stats_label)
            else:
                stats_label = QLabel("这将创建第一个标准答案版本")
                layout.addWidget(stats_label)

            desc_label = QLabel("修改描述:")
            layout.addWidget(desc_label)

            desc_edit = QTextEdit()
            desc_edit.setMaximumHeight(80)
            desc_edit.setPlaceholderText("请描述本次修改的内容...")
            layout.addWidget(desc_edit)

            options_group = QGroupBox("保存选项")
            options_layout = QVBoxLayout(options_group)

            incremental_radio = QRadioButton("增量保存（推荐）- 只保存修改和新增的内容")
            full_radio = QRadioButton("完整保存 - 保存全部编码内容")
            incremental_radio.setChecked(True)

            options_layout.addWidget(incremental_radio)
            options_layout.addWidget(full_radio)
            layout.addWidget(options_group)

            button_layout = QHBoxLayout()
            save_btn = QPushButton("保存")
            cancel_btn = QPushButton("取消")

            button_layout.addWidget(save_btn)
            button_layout.addWidget(cancel_btn)
            layout.addLayout(button_layout)

            def on_save():
                try:
                    description = desc_edit.toPlainText().strip() or "人工修正"

                    if incremental_radio.isChecked():
                        version_id = self.standard_answer_manager.save_modifications_only(
                            self.structured_codes, description
                        )
                    else:
                        version_id = self.standard_answer_manager.create_from_structured_codes(
                            self.structured_codes, description
                        )

                    if version_id:
                        self.update_training_data_label()

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
                except Exception as e:
                    logger.error(f"保存修正时发生错误: {e}", exc_info=True)
                    try:
                        QMessageBox.critical(self, "错误", f"保存修正失败: {str(e)}")
                    except:
                        pass

            def on_cancel():
                confirmation_dialog.reject()

            save_btn.clicked.connect(on_save)
            cancel_btn.clicked.connect(on_cancel)

            confirmation_dialog.exec_()

        except Exception as e:
            logger.error(f"保存修正功能发生错误: {e}", exc_info=True)
            try:
                QMessageBox.critical(self, "错误", f"保存修正失败: {str(e)}")
            except:
                pass

    def update_training_data_label(self):
        """更新训练数据标签"""
        sample_count = self.standard_answer_manager.get_training_sample_count()
        self.training_data_label.setText(f"训练样本: {sample_count} 个")

    def create_standard_answer(self):
        """创建标准答案"""
        self.update_structured_codes_from_tree()

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

            # 获取绝对路径，使用标准答案管理器的目录
            base_dir = os.path.abspath(self.standard_answer_manager.standard_answers_dir)
            file_path = os.path.join(base_dir, version)

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
        """加载训练模型（支持PKL分类器和BERT微调两种格式）"""
        models_info = self.model_downloader.get_available_trained_models()
        if not models_info:
            QMessageBox.information(self, "提示", "没有训练过的模型")
            return

        model_names = self.model_downloader.get_available_trained_model_names()
        model_name, ok = QInputDialog.getItem(
            self, "选择训练模型", "选择要加载的模型:", model_names, 0, False
        )

        if ok and model_name:
            selected_idx = model_names.index(model_name)
            selected_model = models_info[selected_idx]
            actual_name = selected_model['name']
            model_type = selected_model['type']

            success = self.model_manager.load_model_auto(actual_name, model_type)
            if success:
                type_display = "BERT微调模型" if model_type == "bert_finetune" else "分类器模型"
                self.model_type_combo.setCurrentText("训练模型编码")
                QMessageBox.information(self, "成功", f"已加载{type_display}: {actual_name}")
                # 更新当前加载模型显示
                self.current_model_label.setText(f"当前加载模型: {actual_name} ({type_display})")
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
                # 在保存前，将自动编码缓存中的内容也更新到loaded_files中
                if hasattr(self, 'auto_coding_cache') and self.auto_coding_cache:
                    for file_path, content in self.auto_coding_cache.items():
                        if file_path in self.loaded_files:
                            self.loaded_files[file_path]['full_marked_content'] = content

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

                    # 恢复自动编码缓存
                    if not hasattr(self, 'auto_coding_cache'):
                        self.auto_coding_cache = {}
                    else:
                        self.auto_coding_cache.clear()

                    for file_path, file_data in self.loaded_files.items():
                        filename = file_data.get('filename', os.path.basename(file_path))
                        item = QListWidgetItem(filename)
                        item.setData(Qt.UserRole, file_path)
                        self.file_list.addItem(item)

                        # 如果存在已保存的完整标记内容，恢复到缓存中
                        if 'full_marked_content' in file_data:
                            self.auto_coding_cache[file_path] = file_data['full_marked_content']

                    # 更新编码树
                    self.update_coding_tree()

                    # 自动选择第一个文件并显示
                    if self.file_list.count() > 0:
                        first_item = self.file_list.item(0)
                        self.file_list.setCurrentItem(first_item)
                        self.on_file_selected(first_item)

                    QMessageBox.information(self, "成功", f"项目 '{project_name}' 已加载")
                    self.statusBar().showMessage(f"项目已加载: {project_name}")

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
                                        # 优先使用原始句子内容，而不是抽象后的内容
                                        text = sent.get('original_content', '') or sent.get('content', '') or sent.get(
                                            'text', '')
                                        if text:
                                            # 创建规范化的句子对象
                                            normalized_sent = {
                                                'text': text,
                                                'code_id': code_id,
                                                'original': sent,  # 保留原始对象
                                                'original_content': sent.get('original_content', '')  # 保存原始内容
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
                                'number': str(sent_number) if sent_number else ''
                            })
                            # 保存原始数据副本
                            original_sentences_data.append(dict(detail))

            # 确保至少有一个句子（显示一阶编码文本）
            if not sentences_list:
                # 添加句子1：一阶编码文本
                sentences_list.append({
                    'text': content_without_number,
                    'number': associated_numbers_list[0] if associated_numbers_list else ''
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

            # 如果上述方式失败，使用关联编号列表中的第一个编号
            if not first_code_number or not first_code_number.isdigit():
                if associated_numbers_list:
                    first_code_number = associated_numbers_list[0]
                    logger.info(f"使用关联编号第一项作为一阶编码句子编号: {first_code_number}")

            logger.info(f"最终确定的一阶编码句子编号: {first_code_number}")
            logger.info(f"关联编号完整列表: {associated_numbers_list}")
            logger.info(f"sentence_details数量: {len(sentence_details) if sentence_details else 0}")

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
                        # 句子1：显示原始句子内容(original_content)和对应的实际句子编号
                        # 修复：确保句子内容是原始句子，而不是target_abstract
                        sentence_content = sentences_list[0].get('text', content_without_number)
                        # 清理句子内容，移除编号标记和编码标识符
                        sentence_content = re.sub(r'\s*\[[A-Z]\d+\]', '', sentence_content)
                        sentence_content = re.sub(r'\s*\[\d+\]', '', sentence_content)
                        sentence_content = re.sub(r'^[A-Z]\d+\s+', '', sentence_content)  # 修复：移除开头编码标识符
                        sentence_content = sentence_content.strip()
                        # 使用实际的句子编号而不是编码标识符(如A01)
                        sentence_number = first_code_number if first_code_number and first_code_number.isdigit() else ""
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
                        'index': i - 1  # 保存索引用于编辑
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

                            # 执行导航和高亮 - 与原有代码完全一致
                            parent_dialog.navigate_to_sentence_content(sent_content, sent_number)
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

    def update_current_codes_from_tree(self):
        """从树形结构更新 current_codes / 未分类编码

        注意：真正用于保存/导出的结构化编码仍然由前面的
        update_structured_codes_from_tree 填充 self.structured_codes。
        之前这里函数名重复，导致覆盖了前面的实现，
        使得保存修正时看不到树上的最新删除（比如 A21/A22）。
        """
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

    def navigate_to_sentence_content(self, sentence_content, sentence_number=""):
        """导航到句子内容并高亮显示 - 与手动编码界面完全一致的实现

        规范：
        1. 首先清除界面中所有已存在的高亮状态
        2. 仅高亮显示当前目标内容
        3. 自动滚动定位至目标位置
        """
        try:
            logger.info(
                f"导航请求: Content='{sentence_content[:20] if sentence_content else 'None'}...', Number='{sentence_number}'")

            # 安全检查：确保UI组件存在
            if not hasattr(self, 'text_display') or self.text_display is None:
                logger.error("text_display 组件不存在")
                return

            # 首先清除所有已存在的高亮状态（前置操作）
            self.clear_text_highlights()

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

            # 清理内容，移除编号标记
            clean_content = re.sub(r'\s*\[[A-Z]\d+\]', '', sentence_content)
            clean_content = re.sub(r'\s*\[\d+\]', '', clean_content)
            clean_content = re.sub(r'^[A-Z]\d+\s+', '', clean_content)
            clean_content = clean_content.strip()

            if not clean_content:
                return

            # 查找包含该内容的文件
            target_file = None
            for file_path, file_data in self.loaded_files.items():
                file_text = file_data.get('numbered_content', '') or file_data.get('content', '')
                if clean_content in file_text:
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
                            # 显式触发文件加载
                            self.on_file_selected(item)
                            # 等待文件显示更新
                            QApplication.processEvents()
                            break

            # 直接搜索编码对应的完整内容
            document = self.text_display.document()

            # 先尝试直接搜索原始内容
            search_content = clean_content.strip()
            logger.info(f"搜索内容: {search_content[:50]}...")

            # 尝试完整匹配
            content_cursor = document.find(search_content)

            if content_cursor.isNull():
                # 如果完整匹配失败，尝试清理内容后搜索
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
                    return self.highlight_multiple_sentences(sentences, "")

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

                logger.info("成功高亮编码内容")
                return True
            else:
                # 最后回退到基于编码标记的方法
                logger.info("直接内容搜索失败，回退到标记搜索")
                return self.fallback_highlight_by_marker("")

        except Exception as e:
            logger.error(f"导航到句子内容失败: {e}")
            import traceback
            traceback.print_exc()
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
                # 优先使用原始内容，而不是抽象后的内容
                sentence_content = sentence_info.get('original_content', '') or sentence_info.get('text', '').strip()
                if not sentence_content:
                    continue

                # 清理句子内容
                sentence_clean = re.sub(r'\s*\[[A-Z]\d+\]', '', sentence_content)
                sentence_clean = re.sub(r'^[A-Z]\d+\s+', '', sentence_clean)
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
                            # 显式触发文件加载
                            self.on_file_selected(item)
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
            extra_selections = []  # 用于存储临时高亮的选择

            # 获取一阶编码的精确内容
            code_content = self.get_content_by_code_id(code_id)
            code_clean = ""
            if code_content:
                # 清理编码内容，移除可能存在的标记，例如 [A1], A1等
                code_clean = re.sub(r'\s*\[[A-Z]\d+\]', '', code_content)
                code_clean = re.sub(r'^[A-Z]\d+\s+', '', code_clean)
                code_clean = re.sub(r'\s*\[\d+\]', '', code_clean).strip()
                # 去除可能的关联编号前缀，例如 "1:"
                code_clean = re.sub(r'^\d+\s*:\s*', '', code_clean).strip()

            # 优先高亮一阶编码的精确内容 (短语)
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

            if found_count == 0:
                for sentence_info in sentences_to_highlight:
                    # 优先使用原始内容，而不是抽象后的内容
                    sentence_content = sentence_info.get('original_content', '') or sentence_info.get('text',
                                                                                                      '').strip()
                    if not sentence_content:
                        continue

                    # 清理句子内容：移除可能存在的编号标记
                    sentence_clean = re.sub(r'\s*\[[A-Z]\d+\]', '', sentence_content)
                    sentence_clean = re.sub(r'^[A-Z]\d+\s+', '', sentence_clean)
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

            if found_count > 0 and first_match_position is not None:
                # 应用临时高亮
                self.text_display.setExtraSelections(extra_selections)

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

    def open_excel_processor(self):
        """打开Excel处理器对话框"""
        try:
            dialog = ExcelProcessorDialog(self)
            dialog.exec_()
        except Exception as e:
            logger.error(f"打开Excel处理器失败: {e}")
            QMessageBox.critical(self, "错误", f"打开Excel处理器失败: {str(e)}")