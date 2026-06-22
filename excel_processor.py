import os
import json
import logging
import pandas as pd
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                            QFileDialog, QProgressBar, QMessageBox, QListWidget, 
                            QListWidgetItem, QSplitter, QTextEdit, QGroupBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from typing import List, Dict, Any
from standard_answer_manager import StandardAnswerManager
from config import Config
from path_manager import PathManager

logger = logging.getLogger(__name__)


class ExcelProcessor:
    """Excel表格处理器"""

    def __init__(self):
        self.imported_files = []
        self.merged_data = None
        self.standard_answers_dir = PathManager.get_standard_answers_dir()
        
        # 创建标准答案目录
        PathManager.ensure_dir(self.standard_answers_dir)

    def import_excel_files(self, file_paths: List[str]) -> bool:
        """导入Excel文件"""
        try:
            self.imported_files = []
            
            for file_path in file_paths:
                if not file_path.endswith('.xlsx'):
                    logger.warning(f"跳过非Excel文件: {file_path}")
                    continue
                
                try:
                    # 读取Excel文件
                    df = pd.read_excel(file_path)
                    self.imported_files.append({
                        'path': file_path,
                        'data': df,
                        'name': os.path.basename(file_path)
                    })
                    logger.info(f"成功导入Excel文件: {file_path}")
                except Exception as e:
                    logger.error(f"导入Excel文件失败: {file_path}, 错误: {e}")
                    return False
            
            if not self.imported_files:
                logger.warning("没有成功导入任何Excel文件")
                return False
            
            return True
        except Exception as e:
            logger.error(f"导入Excel文件时出错: {e}")
            return False

    def merge_excel_files(self) -> pd.DataFrame:
        """合并Excel文件"""
        try:
            if not self.imported_files:
                raise ValueError("没有导入任何Excel文件")
            
            # 合并所有数据
            dfs = [item['data'] for item in self.imported_files]
            merged_df = pd.concat(dfs, ignore_index=True)
            
            # 处理列名差异
            # 这里可以根据实际需求进行更复杂的列名映射和处理
            
            # 实现复杂的合并逻辑：三阶相同则合并二阶一阶，三阶二阶均相同则合并一阶
            # 按照原始顺序从上往下合并，保持大致顺序不变
            # 从用户提供的截图来看，列名可能是：三阶编码、二阶编码、一阶编码
            sort_columns = []
            
            # 检查可能的列名
            possible_columns = [
                ['三阶编码', '二阶编码', '一阶编码'],
                ['类别', '子类别', '内容'],
                ['三级编码', '二级编码', '一级编码']
            ]
            
            for column_set in possible_columns:
                if all(col in merged_df.columns for col in column_set):
                    sort_columns = column_set
                    break
            
            # 如果找到合适的列名，进行基于原始顺序的合并
            if sort_columns:
                # 创建一个新的DataFrame来存储合并后的结果
                merged_result = []
                
                # 用于跟踪已经处理的行索引
                processed_indices = set()
                
                # 从上往下扫描数据
                for i in range(len(merged_df)):
                    if i in processed_indices:
                        continue
                    
                    # 获取当前行的编码
                    current_row = merged_df.iloc[i]
                    current_level3 = current_row[sort_columns[0]]
                    
                    # 将当前行添加到结果中
                    merged_result.append(current_row)
                    processed_indices.add(i)
                    
                    # 收集所有具有相同三阶编码的行
                    same_level3_rows = []
                    for j in range(i + 1, len(merged_df)):
                        if j in processed_indices:
                            continue
                        
                        next_row = merged_df.iloc[j]
                        next_level3 = next_row[sort_columns[0]]
                        
                        # 如果三阶编码相同，将其添加到临时列表中
                        if next_level3 == current_level3:
                            same_level3_rows.append((j, next_row))
                    
                    # 首先按二阶编码分组，并记录二阶编码的原始出现顺序
                    level2_groups = {}
                    level2_order = []
                    for j, row in same_level3_rows:
                        level2 = row[sort_columns[1]]
                        if level2 not in level2_groups:
                            level2_groups[level2] = []
                            level2_order.append(level2)
                        level2_groups[level2].append((j, row))
                    
                    # 按原始出现顺序处理每个二阶编码组
                    for level2 in level2_order:
                        for j, row in level2_groups[level2]:
                            merged_result.append(row)
                            processed_indices.add(j)
                
                # 转换回DataFrame
                merged_df = pd.DataFrame(merged_result)
                
                # 重置索引
                merged_df = merged_df.reset_index(drop=True)
                logger.info(f"已按原始顺序从上往下合并数据，使相同三阶编码的行相邻，保持了原始的大致顺序")
            
            self.merged_data = merged_df
            logger.info(f"成功合并 {len(self.imported_files)} 个Excel文件，共 {len(merged_df)} 行数据")
            return merged_df
        except Exception as e:
            logger.error(f"合并Excel文件时出错: {e}")
            raise

    def save_merged_to_excel(self, output_path: str) -> bool:
        """保存合并后的数据到Excel文件"""
        try:
            if self.merged_data is None:
                raise ValueError("没有合并的数据")
            
            self.merged_data.to_excel(output_path, index=False)
            logger.info(f"成功保存合并后的数据到: {output_path}")
            return True
        except Exception as e:
            logger.error(f"保存合并后的数据失败: {e}")
            
            # 尝试使用备选保存位置
            try:
                import os
                import ctypes.wintypes
                
                # 获取用户文档文件夹
                CSIDL_PERSONAL = 5  # My Documents
                SHGFP_TYPE_CURRENT = 0  # Get current, not default value
                
                buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
                ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
                documents_path = buf.value
                
                # 生成备选保存路径
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"merged_data_{timestamp}.xlsx"
                backup_path = os.path.join(documents_path, backup_filename)
                
                # 尝试保存到备选位置
                self.merged_data.to_excel(backup_path, index=False)
                logger.info(f"成功保存到备选位置: {backup_path}")
                return True
            except Exception as backup_error:
                logger.error(f"备选位置保存也失败: {backup_error}")
                return False

    def convert_to_standard_answers(self, output_json_path: str) -> bool:
        """将合并后的数据转换为标准答案JSON格式"""
        try:
            if self.merged_data is None:
                raise ValueError("没有合并的数据")
            
            # 转换为标准答案格式
            # 这里需要根据实际的标准答案格式进行调整
            standard_answers = []
            
            for _, row in self.merged_data.iterrows():
                answer_item = {
                    'content': str(row.get('内容', '')),
                    'category': str(row.get('类别', '')),
                    'subcategory': str(row.get('子类别', '')),
                    'code': str(row.get('编码', ''))
                }
                standard_answers.append(answer_item)
            
            # 保存为JSON文件
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(standard_answers, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功转换为标准答案并保存到: {output_json_path}")
            return True
        except Exception as e:
            logger.error(f"转换为标准答案时出错: {e}")
            return False


class ExcelImportThread(QThread):
    """Excel导入线程"""
    progress_updated = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, file_paths: List[str], excel_processor: ExcelProcessor):
        super().__init__()
        self.file_paths = file_paths
        self.excel_processor = excel_processor
    
    def run(self):
        try:
            total_files = len(self.file_paths)
            for i, file_path in enumerate(self.file_paths):
                # 模拟进度更新
                progress = int((i + 1) / total_files * 100)
                self.progress_updated.emit(progress)
                
                # 实际导入操作已在ExcelProcessor中实现
            
            success = self.excel_processor.import_excel_files(self.file_paths)
            if success:
                self.finished.emit(True, f"成功导入 {len(self.excel_processor.imported_files)} 个Excel文件")
            else:
                self.finished.emit(False, "导入Excel文件失败")
        except Exception as e:
            logger.error(f"导入线程出错: {e}")
            self.finished.emit(False, f"导入过程中出错: {str(e)}")


class ExcelProcessorDialog(QDialog):
    """Excel处理器对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Excel表格处理")
        self.resize(800, 600)
        self.excel_processor = ExcelProcessor()
        self.standard_answer_manager = StandardAnswerManager()
        self.import_thread = None
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 顶部按钮区域
        button_layout = QHBoxLayout()
        
        self.import_btn = QPushButton("导入Excel文件")
        self.import_btn.clicked.connect(self.import_excel)
        button_layout.addWidget(self.import_btn)
        
        self.merge_btn = QPushButton("合并表格")
        self.merge_btn.clicked.connect(self.merge_excel)
        self.merge_btn.setEnabled(False)
        button_layout.addWidget(self.merge_btn)
        
        self.save_btn = QPushButton("保存合并结果")
        self.save_btn.clicked.connect(self.save_merged)
        self.save_btn.setEnabled(False)
        button_layout.addWidget(self.save_btn)
        
        self.standard_answers_btn = QPushButton("新建标准答案")
        self.standard_answers_btn.clicked.connect(self.create_standard_answers)
        self.standard_answers_btn.setEnabled(False)
        button_layout.addWidget(self.standard_answers_btn)
        
        layout.addLayout(button_layout)
        
        # 中间区域
        splitter = QSplitter(Qt.Vertical)
        
        # 导入文件列表
        file_list_group = QGroupBox("导入的文件")
        file_list_layout = QVBoxLayout(file_list_group)
        self.file_list = QListWidget()
        file_list_layout.addWidget(self.file_list)
        splitter.addWidget(file_list_group)
        
        # 日志输出
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        splitter.addWidget(log_group)
        
        splitter.setSizes([300, 300])
        layout.addWidget(splitter)
        
        # 底部进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
    
    def import_excel(self):
        """导入Excel文件"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择Excel文件", "", "Excel文件 (*.xlsx)"
        )
        
        if not file_paths:
            return
        
        # 清空之前的列表
        self.file_list.clear()
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 禁用按钮
        self.import_btn.setEnabled(False)
        
        # 启动导入线程
        self.import_thread = ExcelImportThread(file_paths, self.excel_processor)
        self.import_thread.progress_updated.connect(self.update_progress)
        self.import_thread.finished.connect(self.import_finished)
        self.import_thread.start()
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
    
    def import_finished(self, success, message):
        """导入完成"""
        self.progress_bar.setVisible(False)
        self.import_btn.setEnabled(True)
        
        if success:
            # 更新文件列表
            for item in self.excel_processor.imported_files:
                list_item = QListWidgetItem(item['name'])
                list_item.setData(Qt.UserRole, item['path'])
                self.file_list.addItem(list_item)
            
            # 启用合并按钮
            self.merge_btn.setEnabled(True)
            
            self.log_message(f"成功导入 {len(self.excel_processor.imported_files)} 个Excel文件")
        else:
            QMessageBox.warning(self, "导入失败", message)
            self.log_message(f"导入失败: {message}")
    
    def merge_excel(self):
        """合并Excel文件"""
        try:
            self.log_message("开始合并Excel文件...")
            self.excel_processor.merge_excel_files()
            self.log_message(f"成功合并 {len(self.excel_processor.imported_files)} 个Excel文件，共 {len(self.excel_processor.merged_data)} 行数据")
            
            # 启用保存和标准答案按钮
            self.save_btn.setEnabled(True)
            self.standard_answers_btn.setEnabled(True)
            
            QMessageBox.information(self, "合并成功", f"成功合并 {len(self.excel_processor.imported_files)} 个Excel文件，共 {len(self.excel_processor.merged_data)} 行数据")
        except Exception as e:
            logger.error(f"合并Excel文件失败: {e}")
            QMessageBox.critical(self, "合并失败", f"合并Excel文件失败: {str(e)}")
            self.log_message(f"合并失败: {str(e)}")
    
    def save_merged(self):
        """保存合并结果"""
        if self.excel_processor.merged_data is None:
            QMessageBox.warning(self, "警告", "没有合并的数据")
            return
        
        # 获取应用程序所在目录作为默认保存位置，确保用户一定有权限
        import os
        app_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 创建一个专门用于保存结果的目录
        save_dir = os.path.join(app_dir, "output")
        os.makedirs(save_dir, exist_ok=True)
        
        # 确保保存对话框使用用户一定有权限的默认位置
        output_path, _ = QFileDialog.getSaveFileName(
            self, "保存合并结果", os.path.join(save_dir, "merged_data.xlsx"), "Excel文件 (*.xlsx)"
        )
        
        if not output_path:
            return
        
        try:
            success = self.excel_processor.save_merged_to_excel(output_path)
            if success:
                QMessageBox.information(self, "保存成功", f"成功保存合并结果到: {output_path}")
                self.log_message(f"成功保存合并结果到: {output_path}")
            else:
                QMessageBox.critical(self, "保存失败", "保存合并结果失败")
                self.log_message("保存合并结果失败")
        except Exception as e:
            logger.error(f"保存合并结果失败: {e}")
            QMessageBox.critical(self, "保存失败", f"保存合并结果失败: {str(e)}")
            self.log_message(f"保存失败: {str(e)}")
    
    def create_standard_answers(self):
        """创建标准答案"""
        if self.excel_processor.merged_data is None:
            QMessageBox.warning(self, "警告", "没有合并的数据")
            return
        
        # 从合并数据中提取结构化编码
        structured_codes = self._extract_structured_codes()
        if not structured_codes:
            QMessageBox.warning(self, "警告", "无法从合并数据中提取编码结构")
            return
        
        # 弹出输入对话框，让用户输入标准答案描述
        from PyQt5.QtWidgets import QInputDialog
        description, ok = QInputDialog.getText(
            self, "创建标准答案", "请输入标准答案描述:"
        )

        if ok:
            # 调用StandardAnswerManager创建标准答案
            version_id = self.standard_answer_manager.create_from_structured_codes(
                structured_codes, description or "从Excel数据创建的标准答案"
            )

            if version_id:
                QMessageBox.information(self, "成功", f"标准答案已创建: {version_id}")
                self.log_message(f"成功创建标准答案: {version_id}")
            else:
                QMessageBox.critical(self, "错误", "创建标准答案失败")
                self.log_message("创建标准答案失败")
    
    def _extract_structured_codes(self) -> Dict[str, Any]:
        """从合并数据中提取结构化编码"""
        structured_codes = {}
        
        # 尝试不同的列名组合
        possible_columns = [
            ['三阶编码', '二阶编码', '一阶编码'],
            ['类别', '子类别', '内容'],
            ['三级编码', '二级编码', '一级编码']
        ]
        
        selected_columns = None
        for column_set in possible_columns:
            if all(col in self.excel_processor.merged_data.columns for col in column_set):
                selected_columns = column_set
                break
        
        if not selected_columns:
            return structured_codes
        
        # 提取数据
        for _, row in self.excel_processor.merged_data.iterrows():
            third_level = str(row[selected_columns[0]]).strip()
            second_level = str(row[selected_columns[1]]).strip()
            first_level = str(row[selected_columns[2]]).strip()
            
            if third_level and second_level and first_level:
                if third_level not in structured_codes:
                    structured_codes[third_level] = {}
                if second_level not in structured_codes[third_level]:
                    structured_codes[third_level][second_level] = []
                if first_level not in structured_codes[third_level][second_level]:
                    structured_codes[third_level][second_level].append(first_level)
        
        return structured_codes
    
    def log_message(self, message):
        """记录日志"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
