#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动编码导出功能修复补丁
"""

def create_export_fix_patch():
    """创建导出功能修复补丁"""
    
    patch_content = '''diff --git a/manual_coding_dialog.py b/manual_coding_dialog.py
index xxxxxxx..yyyyyyy 100644
--- a/manual_coding_dialog.py
+++ b/manual_coding_dialog.py
@@ -3392,6 +3392,15 @@ def export_to_standard(self):
     def export_to_standard(self):
         """导出为标准答案"""
         # 调试输出当前状态
+        print("=" * 50)
+        print("DEBUG: 导出状态检查")
+        print("=" * 50)
+        print(f"current_codes 类型: {type(self.current_codes)}")
+        print(f"current_codes 内容: {self.current_codes}")
+        print(f"current_codes 长度: {len(self.current_codes)}")
+        print(f"coding_tree 项目数: {self.coding_tree.topLevelItemCount()}")
+        print(f"unclassified_first_codes: {len(self.unclassified_first_codes)}")
+        print("=" * 50)
         
         # 确保数据是最新的
         self.update_structured_codes_from_tree()
@@ -3399,10 +3408,20 @@ def export_to_standard(self):
         if not self.current_codes and not self.unclassified_first_codes:
             QMessageBox.warning(self, "警告", "没有编码数据可导出\\n\\n请先添加至少一个编码")
             return
         
+        # 额外检查：如果 current_codes 为空但有未分类编码，尝试重构数据
+        if not self.current_codes and self.unclassified_first_codes:
+            print("DEBUG: current_codes 为空但有未分类编码，正在重构数据...")
+            # 强制更新数据结构
+            self.update_structured_codes_from_tree()
+            if not self.current_codes:
+                # 如果仍然为空，创建基本结构
+                self.current_codes = {"未分类编码": {"未分类": self.unclassified_first_codes.copy()}}
+                print(f"DEBUG: 已创建基本结构: {self.current_codes}")
+        
         description, ok = QInputDialog.getText(self, "标准答案描述", "请输入本次标准答案的描述:")
         if ok:
             # 通过父窗口保存为标准答案
             parent = self.parent()
+            print(f"DEBUG: 父窗口类型: {type(parent)}")
             if hasattr(parent, 'standard_answer_manager'):
+                print("DEBUG: 找到 standard_answer_manager")
                 version_id = parent.standard_answer_manager.create_from_structured_codes(
                     self.current_codes, description
                 )
@@ -3411,6 +3430,8 @@ def export_to_standard(self):
                     self.accept()
                 else:
                     QMessageBox.critical(self, "错误", "导出失败")
+            else:
+                QMessageBox.critical(self, "错误", "父窗口缺少 standard_answer_manager\\n\\n请通过主界面启动手动编码功能")
 
     def add_first_level_direct(self):
         """直接添加一阶编码 - 添加到树的根部作为未分类"""
@@ -3485,6 +3506,9 @@ def add_first_level_direct(self):
             self.first_content_edit.clear()
 
             # 更新结构化编码数据
+            print("DEBUG: 添加编码后更新数据结构")
             self.update_structured_codes_from_tree()
+            print(f"DEBUG: 更新后 current_codes: {len(self.current_codes)} 个三阶编码")
+            print(f"DEBUG: 更新后 unclassified_first_codes: {len(self.unclassified_first_codes)} 个未分类编码")
 
             logger.info(f"添加一阶编码(未分类): {code_id} - {clean_content}")
             self.statusBar().showMessage(f"已添加一阶编码: {code_id} - {clean_content}") if hasattr(self,
'''

    return patch_content


def create_standalone_export_function():
    """创建独立的导出函数，可以在任何地方调用"""
    
    standalone_function = '''
    def export_to_standard_fixed(self):
        """修复版导出为标准答案功能"""
        print("=" * 60)
        print("手动编码导出功能 - 修复版")
        print("=" * 60)
        
        # 1. 强制更新数据结构
        print("步骤1: 更新编码数据结构...")
        self.update_structured_codes_from_tree()
        
        # 2. 详细状态检查
        print("\\n步骤2: 状态检查...")
        print(f"  - current_codes: {len(self.current_codes)} 个三阶编码")
        print(f"  - unclassified_first_codes: {len(self.unclassified_first_codes)} 个未分类编码")
        print(f"  - coding_tree 项目数: {self.coding_tree.topLevelItemCount()}")
        
        # 3. 数据完整性验证
        print("\\n步骤3: 数据完整性验证...")
        has_valid_data = False
        
        # 检查分类编码
        if self.current_codes:
            total_classified = 0
            for third_cat, second_cats in self.current_codes.items():
                for second_cat, first_codes in second_cats.items():
                    total_classified += len(first_codes)
            print(f"  - 分类编码总数: {total_classified}")
            if total_classified > 0:
                has_valid_data = True
        
        # 检查未分类编码
        if self.unclassified_first_codes:
            print(f"  - 未分类编码数: {len(self.unclassified_first_codes)}")
            has_valid_data = True
            
        # 4. 如果没有有效数据，给出明确提示
        if not has_valid_data:
            error_msg = """❌ 导出失败：没有有效的编码数据
            
可能的原因：
1. 尚未添加任何编码
2. 编码数据结构损坏
3. 编码树显示异常

解决方法：
1. 确保已添加至少一个编码
2. 检查编码树是否正常显示
3. 尝试重新添加编码
"""
            print(error_msg)
            QMessageBox.warning(self, "导出失败", error_msg)
            return False
            
        # 5. 如果只有未分类编码，创建临时结构
        if not self.current_codes and self.unclassified_first_codes:
            print("  - 检测到未分类编码，创建临时结构...")
            self.current_codes = {
                "临时分类": {
                    "未分类编码": self.unclassified_first_codes.copy()
                }
            }
            
        # 6. 检查父窗口
        print("\\n步骤4: 检查导出环境...")
        parent = self.parent()
        if not hasattr(parent, 'standard_answer_manager'):
            error_msg = """❌ 导出环境错误
            
问题：父窗口缺少 standard_answer_manager
            
解决方法：
请通过主程序界面启动手动编码功能，而不是直接运行对话框。
"""
            print(error_msg)
            QMessageBox.critical(self, "环境错误", error_msg)
            return False
            
        print("  - ✓ 环境检查通过")
        
        # 7. 获取描述并导出
        print("\\n步骤5: 执行导出...")
        description, ok = QInputDialog.getText(
            self, 
            "标准答案描述", 
            "请输入本次标准答案的描述:",
            text=f"手动编码导出_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        if ok and description:
            try:
                version_id = parent.standard_answer_manager.create_from_structured_codes(
                    self.current_codes, description
                )
                
                if version_id:
                    success_msg = f"""✅ 导出成功！

标准答案版本: {version_id}
描述: {description}

文件已保存到: standard_answers/{version_id}.json

您可以：
1. 在主界面查看标准答案
2. 使用该标准答案进行模型训练
3. 导出为其他格式（Word、Excel等）
"""
                    print(success_msg)
                    QMessageBox.information(self, "导出成功", success_msg)
                    self.accept()  # 关闭对话框
                    return True
                else:
                    error_msg = "❌ 导出失败：标准答案管理器返回空版本号"
                    print(error_msg)
                    QMessageBox.critical(self, "导出失败", error_msg)
                    return False
                    
            except Exception as e:
                error_msg = f"❌ 导出过程中发生错误：\\n\\n{str(e)}"
                print(error_msg)
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "导出错误", error_msg)
                return False
        else:
            print("用户取消导出")
            return False
'''

    return standalone_function


def create_usage_guide():
    """创建使用指南"""
    
    guide = '''
使用说明：
=========

1. 正常使用流程：
   a. 启动主程序 (python app_launcher.py)
   b. 导入文本文件
   c. 点击"手动编码"按钮
   d. 在手动编码对话框中添加编码
   e. 点击"导出为标准答案"按钮

2. 如果遇到导出失败：
   a. 检查是否已添加编码
   b. 检查编码树是否正常显示
   c. 重新添加一个测试编码
   d. 再次尝试导出

3. 调试方法：
   在 manual_coding_dialog.py 中找到 export_to_standard 方法，
   将其替换为上面提供的修复版函数。

4. 常见问题解决：
   Q: 显示"没有编码数据可导出"
   A: 确保已添加至少一个编码，然后重新导出

   Q: 显示"父窗口缺少 standard_answer_manager"  
   A: 必须通过主程序启动手动编码，不能直接运行对话框

   Q: 导出后找不到文件
   A: 文件保存在 standard_answers 目录下，文件名为版本号.json
'''

    return guide


if __name__ == "__main__":
    print("手动编码导出功能修复方案")
    print("=" * 50)
    
    # 生成补丁内容
    patch = create_export_fix_patch()
    print("\\n📋 推荐补丁内容:")
    print(patch)
    
    # 生成独立函数
    standalone_func = create_standalone_export_function()
    print("\\n🔧 独立修复函数:")
    print(standalone_func)
    
    # 生成使用指南
    guide = create_usage_guide()
    print("\\n📖 使用指南:")
    print(guide)
    
    print("\\n" + "=" * 50)
    print("💡 建议：将修复后的 export_to_standard 方法替换原方法")
    print("=" * 50)