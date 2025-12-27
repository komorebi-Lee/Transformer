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
        # 未分类的一阶编码临时存储
        self.unclassified_first_codes = []
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

        # 一阶编码输入
        first_group = QGroupBox("添加一阶编码")
        first_layout = QVBoxLayout(first_group)
        
        # 一阶编码内容
        self.first_content_edit = QTextEdit()
        self.first_content_edit.setMaximumHeight(100)
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
        self.coding_tree = QTreeWidget()
        self.coding_tree.setHeaderLabels(["编码内容", "类型", "数量"])
        self.coding_tree.setColumnWidth(0, 300)
        self.coding_tree.setColumnWidth(1, 80)
        self.coding_tree.setColumnWidth(2, 60)
        self.coding_tree.setSelectionMode(QTreeWidget.ExtendedSelection)  # 支持多选
        self.coding_tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        
        # 设置上下文菜单
        self.coding_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.coding_tree.customContextMenuRequested.connect(self.show_tree_context_menu)
        
        structure_layout.addWidget(self.coding_tree)

        # 树形操作按钮
        tree_buttons_layout = QHBoxLayout()
        
        expand_btn = QPushButton("展开全部")
        expand_btn.clicked.connect(self.coding_tree.expandAll)
        
        collapse_btn = QPushButton("折叠全部")
        collapse_btn.clicked.connect(self.coding_tree.collapseAll)
        
        tree_buttons_layout.addWidget(expand_btn)
        tree_buttons_layout.addWidget(collapse_btn)
        
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

    def validate_category_name(self, name: str, level: str) -> tuple:
        """验证编码名称是否符合规则
        
        Args:
            name: 编码名称
            level: 编码级别 (third/second/first)
            
        Returns:
            (is_valid, clean_name, error_message)
        """
        import re
        
        name = name.strip()
        if not name:
            return False, "", "名称不能为空"
        
        # 移除可能的编号前缀
        if level == "third":
            # 三阶编码: 移除 A, B, C 等前缀
            clean_name = re.sub(r'^[A-Z]\s+', '', name)
            if not clean_name:
                clean_name = name
        elif level == "second":
            # 二阶编码: 移除 A1, B2 等前缀
            clean_name = re.sub(r'^[A-Z]\d+\s+', '', name)
            if not clean_name:
                clean_name = name
        elif level == "first":
            # 一阶编码: 移除 A11, B22 等前缀
            clean_name = re.sub(r'^[A-Z]\d{2}\s+', '', name)
            if not clean_name:
                clean_name = name
        else:
            clean_name = name
        
        return True, clean_name.strip(), ""
    
    def add_third_category(self):
        """添加三阶编码"""
        try:
            name, ok = QInputDialog.getText(self, "添加三阶编码", "请输入三阶编码名称:")
            if ok and name.strip():
                is_valid, clean_name, error_msg = self.validate_category_name(name, "third")
                if not is_valid:
                    QMessageBox.warning(self, "验证错误", error_msg)
                    return
                
                # 检查是否已存在
                for i in range(self.coding_tree.topLevelItemCount()):
                    top_item = self.coding_tree.topLevelItem(i)
                    item_data = top_item.data(0, Qt.UserRole)
                    if item_data and item_data.get("level") == 3 and top_item.text(0) == clean_name:
                        QMessageBox.warning(self, "警告", "该三阶编码已存在")
                        return
                
                # 创建三阶节点
                third_item = QTreeWidgetItem(self.coding_tree)
                third_item.setText(0, clean_name)
                third_item.setText(1, "三阶编码")
                third_item.setText(2, "0")
                third_item.setData(0, Qt.UserRole, {"level": 3, "name": clean_name})
                
                self.update_structured_codes_from_tree()
                logger.info(f"添加三阶编码: {clean_name}")
                QMessageBox.information(self, "成功", f"已添加三阶编码: {clean_name}")
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
            second_name, ok = QInputDialog.getText(self, "添加二阶编码", 
                                                    f"在三阶'{third_name}'下添加二阶编码，请输入名称:")
            if not ok or not second_name.strip():
                return
            
            is_valid, clean_name, error_msg = self.validate_category_name(second_name, "second")
            if not is_valid:
                QMessageBox.warning(self, "验证错误", error_msg)
                return
            
            # 检查是否已存在
            for i in range(current_item.childCount()):
                if current_item.child(i).text(0) == clean_name:
                    QMessageBox.warning(self, "警告", "该二阶编码已存在")
                    return
            
            # 创建二阶节点
            second_item = QTreeWidgetItem(current_item)
            second_item.setText(0, clean_name)
            second_item.setText(1, "二阶编码")
            second_item.setText(2, "0")
            second_item.setData(0, Qt.UserRole, {
                "level": 2,
                "name": clean_name,
                "parent": third_name
            })
            
            current_item.setExpanded(True)
            current_item.setText(2, str(current_item.childCount()))
            
            self.update_structured_codes_from_tree()
            logger.info(f"在三阶'{third_name}'下添加二阶编码: {clean_name}")
            QMessageBox.information(self, "成功", f"已添加二阶编码: {clean_name}")
            
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
            
            # 创建一阶节点
            first_item = QTreeWidgetItem(current_item)
            first_item.setText(0, clean_content)
            first_item.setText(1, "一阶编码")
            first_item.setText(2, "1")
            
            # 获取父节点信息
            parent_item = current_item.parent()
            third_name = parent_item.text(0) if parent_item else ""
            
            first_item.setData(0, Qt.UserRole, {
                "level": 1,
                "content": clean_content,
                "category": second_name,
                "core_category": third_name,
                "classified": True
            })
            
            current_item.setExpanded(True)
            current_item.setText(2, str(current_item.childCount()))
            
            # 更新父节点计数
            if parent_item:
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
                            QMessageBox.warning(self, "警告", f"一阶编码 '{item.text(0)}' 已经有父节点二阶编码 '{item.parent().text(0)}'\n\n一阶只能对应一个二阶！")
                            return
                    first_level_items.append(item)
            
            if not first_level_items:
                QMessageBox.warning(self, "警告", "请选中一阶编码！")
                return
            
            # 输入二阶编码名称
            second_name, ok = QInputDialog.getText(self, "添加二阶编码", 
                                                    f"为 {len(first_level_items)} 个一阶编码添加父节点二阶编码，请输入二阶编码名称:")
            
            if not ok or not second_name.strip():
                return
            
            is_valid, clean_name, error_msg = self.validate_category_name(second_name, "second")
            if not is_valid:
                QMessageBox.warning(self, "验证错误", error_msg)
                return
            
            # 创建二阶节点
            second_item = QTreeWidgetItem(self.coding_tree)
            second_item.setText(0, clean_name)
            second_item.setText(1, "二阶编码")
            second_item.setData(0, Qt.UserRole, {
                "level": 2,
                "name": clean_name
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
                item.setData(0, Qt.UserRole, item_data)
            
            second_item.setText(2, str(len(first_level_items)))
            second_item.setExpanded(True)
            
            self.update_structured_codes_from_tree()
            logger.info(f"为 {len(first_level_items)} 个一阶编码添加了父节点二阶编码: {clean_name}")
            QMessageBox.information(self, "成功", f"已为 {len(first_level_items)} 个一阶编码添加二阶编码: {clean_name}")
            
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
                            QMessageBox.warning(self, "警告", f"二阶编码 '{item.text(0)}' 已经有父节点三阶编码 '{item.parent().text(0)}'\n\n二阶只能对应一个三阶！")
                            return
                    second_level_items.append(item)
            
            if not second_level_items:
                QMessageBox.warning(self, "警告", "请选中二阶编码！")
                return
            
            # 输入三阶编码名称
            third_name, ok = QInputDialog.getText(self, "添加三阶编码", 
                                                   f"为 {len(second_level_items)} 个二阶编码添加父节点三阶编码，请输入三阶编码名称:")
            
            if not ok or not third_name.strip():
                return
            
            is_valid, clean_name, error_msg = self.validate_category_name(third_name, "third")
            if not is_valid:
                QMessageBox.warning(self, "验证错误", error_msg)
                return
            
            # 创建三阶节点
            third_item = QTreeWidgetItem(self.coding_tree)
            third_item.setText(0, clean_name)
            third_item.setText(1, "三阶编码")
            third_item.setData(0, Qt.UserRole, {
                "level": 3,
                "name": clean_name
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
            # 编辑一阶编码
            dialog = QDialog(self)
            dialog.setWindowTitle("编辑一阶编码")
            dialog.resize(600, 400)
            
            layout = QVBoxLayout(dialog)
            
            label = QLabel("请输入新的一阶编码内容:")
            layout.addWidget(label)
            
            text_edit = QTextEdit()
            text_edit.setPlainText(old_content)
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
                    current_item.setData(0, Qt.UserRole, item_data)
                    self.update_structured_codes_from_tree()
                    logger.info(f"修改一阶编码: {old_content} → {clean_content}")
                
                dialog.accept()
            
            ok_button.clicked.connect(on_ok)
            cancel_button.clicked.connect(dialog.reject)
            
            dialog.exec_()
        
        elif level == 2:
            # 编辑二阶编码
            new_name, ok = QInputDialog.getText(self, "编辑二阶编码", "请输入新的二阶编码名称:", text=old_content)
            if ok and new_name.strip():
                is_valid, clean_name, error_msg = self.validate_category_name(new_name, "second")
                if not is_valid:
                    QMessageBox.warning(self, "验证错误", error_msg)
                    return
                
                if clean_name != old_content:
                    current_item.setText(0, clean_name)
                    item_data["name"] = clean_name
                    current_item.setData(0, Qt.UserRole, item_data)
                    self.update_structured_codes_from_tree()
                    logger.info(f"修改二阶编码: {old_content} → {clean_name}")
        
        elif level == 3:
            # 编辑三阶编码
            new_name, ok = QInputDialog.getText(self, "编辑三阶编码", "请输入新的三阶编码名称:", text=old_content)
            if ok and new_name.strip():
                is_valid, clean_name, error_msg = self.validate_category_name(new_name, "third")
                if not is_valid:
                    QMessageBox.warning(self, "验证错误", error_msg)
                    return
                
                if clean_name != old_content:
                    current_item.setText(0, clean_name)
                    item_data["name"] = clean_name
                    current_item.setData(0, Qt.UserRole, item_data)
                    self.update_structured_codes_from_tree()
                    logger.info(f"修改三阶编码: {old_content} → {clean_name}")
    
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
                third_name = top_item.text(0)
                self.current_codes[third_name] = {}
                
                for j in range(top_item.childCount()):
                    second_item = top_item.child(j)
                    second_name = second_item.text(0)
                    self.current_codes[third_name][second_name] = []
                    
                    for k in range(second_item.childCount()):
                        first_item = second_item.child(k)
                        first_content = first_item.text(0)
                        self.current_codes[third_name][second_name].append(first_content)
            
            elif level == 1:
                # 未分类的一阶编码
                if not item_data.get("classified", True):
                    content = top_item.text(0)
                    self.unclassified_first_codes.append(content)
    
    def update_coding_tree(self):
        """更新编码结构树"""
        try:
            self.coding_tree.clear()
            
            # 添加三阶编码及其子节点
            for third_cat, second_cats in self.current_codes.items():
                third_item = QTreeWidgetItem(self.coding_tree)
                third_item.setText(0, third_cat)
                third_item.setText(1, "三阶编码")
                third_item.setData(0, Qt.UserRole, {"level": 3, "name": third_cat})
                
                second_count = 0
                first_count = 0
                
                for second_cat, first_contents in second_cats.items():
                    second_item = QTreeWidgetItem(third_item)
                    second_item.setText(0, second_cat)
                    second_item.setText(1, "二阶编码")
                    second_item.setData(0, Qt.UserRole, {
                        "level": 2,
                        "name": second_cat,
                        "parent": third_cat
                    })
                    
                    for content in first_contents:
                        first_item = QTreeWidgetItem(second_item)
                        if isinstance(content, dict):
                            content_text = content.get('content', str(content))
                        else:
                            content_text = str(content)
                        
                        first_item.setText(0, content_text)
                        first_item.setText(1, "一阶编码")
                        first_item.setText(2, "1")
                        first_item.setData(0, Qt.UserRole, {
                            "level": 1,
                            "content": content_text,
                            "category": second_cat,
                            "core_category": third_cat,
                            "classified": True
                        })
                        first_count += 1
                    
                    second_item.setText(2, str(len(first_contents)))
                    second_count += 1
                
                third_item.setText(2, str(second_count))
            
            # 添加未分类的一阶编码
            for content in self.unclassified_first_codes:
                item = QTreeWidgetItem(self.coding_tree)
                item.setText(0, content)
                item.setText(1, "一阶编码")
                item.setText(2, "1")
                item.setData(0, Qt.UserRole, {
                    "level": 1,
                    "content": content,
                    "classified": False
                })
            
            self.coding_tree.expandAll()
            
        except Exception as e:
            logger.error(f"更新编码树失败: {e}")
            import traceback
            traceback.print_exc()



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
            
            # 添加到树根部（未分类状态）
            item = QTreeWidgetItem(self.coding_tree)
            item.setText(0, clean_content)
            item.setText(1, "一阶编码")
            item.setText(2, "1")
            item.setData(0, Qt.UserRole, {
                "level": 1,
                "content": clean_content,
                "classified": False
            })
            
            self.first_content_edit.clear()
            
            logger.info(f"添加一阶编码(未分类): {clean_content}")
            self.statusBar().showMessage(f"已添加一阶编码: {clean_content}") if hasattr(self, 'statusBar') else None
            
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
        dialog.setWindowTitle("分配编码归属")
        dialog.resize(500, 300)
        
        layout = QVBoxLayout(dialog)
        
        # 说明
        info_label = QLabel(f"为一阶编码分配三阶和二阶归属：")
        info_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        layout.addWidget(info_label)
        
        # 显示编码内容
        content_label = QLabel(f"编码内容: {content}")
        content_label.setStyleSheet("color: #666; font-style: italic; padding: 10px; background-color: #f0f0f0; border-radius: 3px;")
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
    
    def get_coding_result(self):
        """获取编码结果"""
        return self.current_codes