#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动编码导出问题诊断工具（命令行版）
"""

import json
import os
import re


def analyze_manual_coding_logic():
    """分析手动编码的导出逻辑"""
    print("=" * 60)
    print("手动编码导出为标准答案逻辑分析")
    print("=" * 60)
    
    # 1. 导出入口点分析
    print("\n1. 📌 导出功能入口点:")
    print("   文件: manual_coding_dialog.py")
    print("   方法: export_to_standard()")
    print("   位置: 第3392-3410行")
    
    export_logic = """
    def export_to_standard(self):
        '''导出为标准答案'''
        if not self.current_codes:                    # ← 关键检查点
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
    """
    
    print(export_logic)
    
    # 2. current_codes 数据来源分析
    print("\n2. 📊 current_codes 数据来源分析:")
    print("   current_codes 初始化位置:")
    print("   - 第76行: self.current_codes = {}")
    print("   - 第351行: 从现有编码复制: self.current_codes = self.existing_codes.copy()")
    print("   - 第2166行: 从导入数据恢复: self.current_codes = tree_data['current_codes']")
    print("   - 第2308行: 从编码数据恢复: self.current_codes = coding_data['current_codes']")
    print("   - 第2793行: 重置为空: self.current_codes = {}")
    
    # 3. update_structured_codes_from_tree 分析
    print("\n3. 🔧 update_structured_codes_from_tree() 方法分析:")
    print("   位置: 第2791-2873行")
    print("   功能: 从树形控件更新编码数据结构")
    
    update_method = """
    def update_structured_codes_from_tree(self):
        '''从树形结构更新编码数据'''
        self.current_codes = {}                          # ← 重置数据
        self.unclassified_first_codes = []
        
        for i in range(self.coding_tree.topLevelItemCount()):
            top_item = self.coding_tree.topLevelItem(i)
            item_data = top_item.data(0, Qt.UserRole)
            
            if not item_data:
                continue
                
            level = item_data.get("level")
            
            if level == 3:
                # 处理三阶编码
                third_display_name = top_item.text(0)
                self.current_codes[third_display_name] = {}
                
                # 遍历二阶编码...
                for j in range(top_item.childCount()):
                    second_item = top_item.child(j)
                    second_display_name = second_item.text(0)
                    self.current_codes[third_display_name][second_display_name] = []
                    
                    # 遍历一阶编码...
                    for k in range(second_item.childCount()):
                        first_item = second_item.child(k)
                        first_item_data = first_item.data(0, Qt.UserRole)
                        self.current_codes[third_display_name][second_display_name].append(first_item_data)
                        
            elif level == 1:
                # 处理未分类的一阶编码
                if not item_data.get("classified", True):
                    self.unclassified_first_codes.append(item_data)
    """
    
    print(update_method)
    
    # 4. 调用时机分析
    print("\n4. ⏰ update_structured_codes_from_tree() 调用时机:")
    
    call_points = [
        "第1182行: 添加三阶编码后",
        "第1277行: 添加二阶编码后", 
        "第1376行: 添加一阶编码到分类后",
        "第1504行: 修改三阶编码后",
        "第1626行: 修改二阶编码后",
        "第2114行: 保存编码时(build_tree_data)",
        "第2646行: 导入编码结果时",
        "第2695行: 导入编码结果时",
        "第2744行: 导入编码结果时",
        "第2788行: 导入编码树时",
        "第3488行: 直接添加一阶编码后",
        "第3906行: 移动编码后",
        "第3979行: 删除编码后",
        "第4026行: 清空编码后"
    ]
    
    for point in call_points:
        print(f"   - {point}")
    
    # 5. 常见问题分析
    print("\n5. ❌ 常见导致导出失败的原因:")
    
    problems = [
        "未添加任何编码就尝试导出",
        "添加编码后没有正确更新 current_codes",
        "编码树控件中有项目但数据结构不完整",
        "父窗口缺少 standard_answer_manager",
        "编码数据格式不符合标准答案要求"
    ]
    
    for i, problem in enumerate(problems, 1):
        print(f"   {i}. {problem}")
    
    # 6. 解决方案
    print("\n6. ✅ 解决方案:")
    
    solutions = [
        "确保添加至少一个编码后再导出",
        "在关键操作后手动调用 update_structured_codes_from_tree()",
        "检查 coding_tree 控件中是否有正确的项目",
        "验证 current_codes 数据结构是否正确",
        "确认父窗口正确初始化了 standard_answer_manager"
    ]
    
    for i, solution in enumerate(solutions, 1):
        print(f"   {i}. {solution}")


def create_debug_helper():
    """创建调试辅助函数"""
    print("\n7. 🔍 调试辅助代码:")
    
    debug_code = '''
# 在 manual_coding_dialog.py 中添加调试代码

def debug_export_status(self):
    """调试导出状态"""
    print("=" * 50)
    print("DEBUG: 导出状态检查")
    print("=" * 50)
    print(f"current_codes 类型: {type(self.current_codes)}")
    print(f"current_codes 内容: {self.current_codes}")
    print(f"current_codes 长度: {len(self.current_codes)}")
    print(f"coding_tree 项目数: {self.coding_tree.topLevelItemCount()}")
    print(f"unclassified_first_codes: {self.unclassified_first_codes}")
    print(f"父窗口有 standard_answer_manager: {hasattr(self.parent(), 'standard_answer_manager')}")
    print("=" * 50)

# 在 export_to_standard 方法开始处添加:
def export_to_standard(self):
    """导出为标准答案"""
    # 添加调试输出
    self.debug_export_status()
    
    if not self.current_codes:
        print("DEBUG: current_codes 为空，无法导出")
        QMessageBox.warning(self, "警告", "没有编码数据可导出")
        return
    
    # ... 其余代码
'''
    
    print(debug_code)


def show_expected_data_structure():
    """显示期望的数据结构"""
    print("\n8. 📋 期望的数据结构示例:")
    
    example = {
        "C01 工作挑战": {
            "B01 时间管理": [
                {
                    "content": "时间管理是最困难的，经常感觉时间不够用",
                    "code_id": "A01",
                    "sentence_details": [],
                    "sentence_count": 1
                }
            ],
            "B02 工作压力": [
                {
                    "content": "工作压力主要来自于 deadlines",
                    "code_id": "A02", 
                    "sentence_details": [],
                    "sentence_count": 1
                }
            ]
        },
        "C02 应对策略": {
            "B01 计划制定": [
                {
                    "content": "我会制定详细的计划",
                    "code_id": "A03",
                    "sentence_details": [],
                    "sentence_count": 1
                }
            ]
        }
    }
    
    print("标准格式 (current_codes):")
    print(json.dumps(example, ensure_ascii=False, indent=2))
    
    print("\n未分类编码格式 (unclassified_first_codes):")
    unclassified_example = [
        {
            "content": "团队协作很重要",
            "code_id": "A04",
            "classified": False,
            "sentence_details": [],
            "sentence_count": 1
        }
    ]
    print(json.dumps(unclassified_example, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    analyze_manual_coding_logic()
    create_debug_helper()
    show_expected_data_structure()
    
    print("\n" + "=" * 60)
    print("💡 总结: 导出失败通常是由于 current_codes 为空导致的")
    print("   解决方法是在导出前确保已添加编码并正确更新了数据结构")
    print("=" * 60)