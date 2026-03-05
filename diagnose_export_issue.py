#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断手动编码导出为标准答案的问题
"""

import sys
import os
import json
from PyQt5.QtWidgets import QApplication, QMessageBox
from manual_coding_dialog import ManualCodingDialog


def diagnose_export_issue():
    """诊断导出问题"""
    print("=" * 60)
    print("手动编码导出问题诊断工具")
    print("=" * 60)
    
    app = QApplication(sys.argv)
    
    # 创建测试文件
    test_file_path = "test_export_diagnosis.txt"
    test_content = """
A：您好，感谢您参与这次访谈。我想了解一下您对当前工作的看法。
B：好的，我很乐意分享我的想法。
A：您觉得工作中最有挑战性的部分是什么？
B：我觉得时间管理是最困难的，经常感觉时间不够用。
A：那您通常是如何应对这种挑战的呢？
B：我会制定详细的计划，并且尽量按照优先级来安排工作。
    """.strip()
    
    with open(test_file_path, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    try:
        # 加载测试文件
        loaded_files = {test_file_path: {'content': test_content}}
        
        # 创建手动编码对话框
        dialog = ManualCodingDialog(None, loaded_files, {})
        
        print("\n🔍 诊断步骤:")
        print("1. 检查初始状态...")
        print(f"   - current_codes: {dialog.current_codes}")
        print(f"   - unclassified_first_codes: {dialog.unclassified_first_codes}")
        print(f"   - coding_tree topLevelItemCount: {dialog.coding_tree.topLevelItemCount()}")
        
        # 模拟添加一些编码
        print("\n2. 添加测试编码...")
        
        # 直接添加一个未分类的一阶编码
        dialog.first_content_edit.setPlainText("时间管理困难")
        dialog.add_first_level_direct()
        
        print(f"   - 添加后 current_codes: {dialog.current_codes}")
        print(f"   - 添加后 unclassified_first_codes: {dialog.unclassified_first_codes}")
        print(f"   - 添加后 coding_tree topLevelItemCount: {dialog.coding_tree.topLevelItemCount()}")
        
        # 手动调用更新方法
        print("\n3. 手动更新结构化编码...")
        dialog.update_structured_codes_from_tree()
        
        print(f"   - 更新后 current_codes: {dialog.current_codes}")
        print(f"   - 更新后 unclassified_first_codes: {dialog.unclassified_first_codes}")
        
        # 检查导出条件
        print("\n4. 检查导出条件...")
        can_export = bool(dialog.current_codes)
        print(f"   - current_codes 非空: {can_export}")
        
        if can_export:
            print("✅ 导出条件满足，应该可以正常导出")
        else:
            print("❌ 导出条件不满足")
            
        # 尝试模拟导出过程
        print("\n5. 模拟导出过程...")
        if hasattr(dialog.parent(), 'standard_answer_manager'):
            print("   - 父窗口有 standard_answer_manager")
        else:
            print("   - 父窗口缺少 standard_answer_manager")
            
        # 显示诊断结果
        result_msg = f"""
诊断结果:

1. 初始状态:
   - current_codes: {dialog.current_codes}
   - coding_tree 项目数: {dialog.coding_tree.topLevelItemCount()}

2. 添加编码后:
   - current_codes: {dialog.current_codes}
   - unclassified_first_codes: {len(dialog.unclassified_first_codes)} 个项目

3. 导出可行性: {'✅ 可以导出' if can_export else '❌ 无法导出'}

建议:
"""
        
        if not can_export:
            result_msg += """
- 确保添加了至少一个编码
- 检查是否正确调用了 update_structured_codes_from_tree()
- 确认编码数据结构是否正确
"""
        else:
            result_msg += """
- 编码数据正常，应该可以导出
- 如果仍然失败，请检查 standard_answer_manager 是否正确初始化
"""
            
        print(result_msg)
        
        # 显示GUI消息框
        msg_box = QMessageBox()
        msg_box.setWindowTitle("导出问题诊断结果")
        msg_box.setText(result_msg)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
        
        return can_export
        
    except Exception as e:
        print(f"\n❌ 诊断过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # 清理测试文件
        if os.path.exists(test_file_path):
            os.remove(test_file_path)


def fix_export_issue():
    """提供修复建议"""
    print("\n🔧 修复建议:")
    print("""
1. 确保在添加编码后立即更新结构化数据:
   - 每次添加/修改编码后调用 update_structured_codes_from_tree()
   
2. 检查编码数据结构:
   - current_codes 应该是一个嵌套字典结构
   - 格式: {三阶编码: {二阶编码: [一阶编码列表]}}
   
3. 确保父窗口正确初始化:
   - 父窗口需要有 standard_answer_manager 属性
   - 该管理器负责实际的标准答案创建
   
4. 调试方法:
   - 在导出前打印 current_codes 内容
   - 检查 coding_tree 控件中的项目数
   - 确认 update_structured_codes_from_tree() 被正确调用
""")


if __name__ == "__main__":
    success = diagnose_export_issue()
    fix_export_issue()
    
    if success:
        print("\n🎉 诊断完成：编码数据正常")
    else:
        print("\n⚠️  诊断发现问题：编码数据为空")
    
    sys.exit(0)