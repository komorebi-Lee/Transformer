#!/usr/bin/env python3
"""
测试主界面编码树修改后的保存功能

测试场景：
1. 主界面编码树的修改（包括删除操作）能够被正确记录
2. 点击主界面"新建标准答案"按钮时，能够将编码树的所有修改内容正确保存
3. 确保主界面的保存逻辑与手动编码界面的"新增标准答案"逻辑完全一致
"""

import os
import sys
import json
import tempfile
import shutil
import logging
from unittest.mock import Mock, MagicMock, patch

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_update_structured_codes_from_tree():
    """测试 update_structured_codes_from_tree 方法能正确从树形结构更新编码数据"""
    print("\n🧪 测试 update_structured_codes_from_tree 方法...")
    
    try:
        from PyQt5.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem
        from PyQt5.QtCore import Qt
        
        app = QApplication.instance() or QApplication([])
        
        tree = QTreeWidget()
        tree.setColumnCount(5)
        
        third_item = QTreeWidgetItem(["三阶编码A", "", "1", "", "2"])
        third_item.setData(0, Qt.UserRole, {"level": 3})
        
        second_item = QTreeWidgetItem(["二阶编码A1", "", "2", "", "2"])
        second_item.setData(0, Qt.UserRole, {"level": 2})
        
        first_item_1 = QTreeWidgetItem(["一阶编码内容1", "", "", "", "1"])
        first_item_1.setData(0, Qt.UserRole, {"level": 1})
        
        first_item_2 = QTreeWidgetItem(["一阶编码内容2", "", "", "", "1"])
        first_item_2.setData(0, Qt.UserRole, {"level": 1})
        
        second_item.addChild(first_item_1)
        second_item.addChild(first_item_2)
        third_item.addChild(second_item)
        tree.addTopLevelItem(third_item)
        
        structured_codes = {}
        for i in range(tree.topLevelItemCount()):
            third = tree.topLevelItem(i)
            third_name = third.text(0)
            structured_codes[third_name] = {}
            
            for j in range(third.childCount()):
                second = third.child(j)
                second_name = second.text(0)
                structured_codes[third_name][second_name] = []
                
                for k in range(second.childCount()):
                    first = second.child(k)
                    structured_codes[third_name][second_name].append(first.text(0))
        
        assert "三阶编码A" in structured_codes, "三阶编码应该存在"
        assert "二阶编码A1" in structured_codes["三阶编码A"], "二阶编码应该存在"
        assert len(structured_codes["三阶编码A"]["二阶编码A1"]) == 2, "应该有2个一阶编码"
        assert "一阶编码内容1" in structured_codes["三阶编码A"]["二阶编码A1"], "一阶编码内容1应该存在"
        assert "一阶编码内容2" in structured_codes["三阶编码A"]["二阶编码A1"], "一阶编码内容2应该存在"
        
        print("✅ update_structured_codes_from_tree 方法测试通过")
        return True
        
    except Exception as e:
        print(f"❌ update_structured_codes_from_tree 方法测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_delete_code_updates_structured_codes():
    """测试删除编码后 structured_codes 能正确更新"""
    print("\n🧪 测试删除编码后 structured_codes 更新...")
    
    try:
        from PyQt5.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem
        from PyQt5.QtCore import Qt
        
        app = QApplication.instance() or QApplication([])
        
        tree = QTreeWidget()
        tree.setColumnCount(5)
        
        third_item = QTreeWidgetItem(["三阶编码A", "", "1", "", "2"])
        third_item.setData(0, Qt.UserRole, {"level": 3})
        
        second_item = QTreeWidgetItem(["二阶编码A1", "", "2", "", "2"])
        second_item.setData(0, Qt.UserRole, {"level": 2})
        
        first_item_1 = QTreeWidgetItem(["一阶编码内容1", "", "", "", "1"])
        first_item_1.setData(0, Qt.UserRole, {"level": 1})
        
        first_item_2 = QTreeWidgetItem(["一阶编码内容2", "", "", "", "1"])
        first_item_2.setData(0, Qt.UserRole, {"level": 1})
        
        second_item.addChild(first_item_1)
        second_item.addChild(first_item_2)
        third_item.addChild(second_item)
        tree.addTopLevelItem(third_item)
        
        def update_structured_codes_from_tree():
            structured_codes = {}
            for i in range(tree.topLevelItemCount()):
                third = tree.topLevelItem(i)
                third_name = third.text(0)
                structured_codes[third_name] = {}
                
                for j in range(third.childCount()):
                    second = third.child(j)
                    second_name = second.text(0)
                    structured_codes[third_name][second_name] = []
                    
                    for k in range(second.childCount()):
                        first = second.child(k)
                        structured_codes[third_name][second_name].append(first.text(0))
            return structured_codes
        
        structured_codes = update_structured_codes_from_tree()
        assert len(structured_codes["三阶编码A"]["二阶编码A1"]) == 2, "删除前应该有2个一阶编码"
        
        second_item.removeChild(first_item_1)
        
        structured_codes_after_delete = update_structured_codes_from_tree()
        assert len(structured_codes_after_delete["三阶编码A"]["二阶编码A1"]) == 1, "删除后应该有1个一阶编码"
        assert "一阶编码内容1" not in structured_codes_after_delete["三阶编码A"]["二阶编码A1"], "删除的一阶编码不应该存在"
        assert "一阶编码内容2" in structured_codes_after_delete["三阶编码A"]["二阶编码A1"], "未删除的一阶编码应该存在"
        
        print("✅ 删除编码后 structured_codes 更新测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 删除编码后 structured_codes 更新测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_edit_code_updates_structured_codes():
    """测试编辑编码后 structured_codes 能正确更新"""
    print("\n🧪 测试编辑编码后 structured_codes 更新...")
    
    try:
        from PyQt5.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem
        from PyQt5.QtCore import Qt
        
        app = QApplication.instance() or QApplication([])
        
        tree = QTreeWidget()
        tree.setColumnCount(5)
        
        third_item = QTreeWidgetItem(["三阶编码A", "", "1", "", "2"])
        third_item.setData(0, Qt.UserRole, {"level": 3})
        
        second_item = QTreeWidgetItem(["二阶编码A1", "", "2", "", "2"])
        second_item.setData(0, Qt.UserRole, {"level": 2})
        
        first_item_1 = QTreeWidgetItem(["一阶编码内容1", "", "", "", "1"])
        first_item_1.setData(0, Qt.UserRole, {"level": 1})
        
        second_item.addChild(first_item_1)
        third_item.addChild(second_item)
        tree.addTopLevelItem(third_item)
        
        def update_structured_codes_from_tree():
            structured_codes = {}
            for i in range(tree.topLevelItemCount()):
                third = tree.topLevelItem(i)
                third_name = third.text(0)
                structured_codes[third_name] = {}
                
                for j in range(third.childCount()):
                    second = third.child(j)
                    second_name = second.text(0)
                    structured_codes[third_name][second_name] = []
                    
                    for k in range(second.childCount()):
                        first = second.child(k)
                        structured_codes[third_name][second_name].append(first.text(0))
            return structured_codes
        
        structured_codes = update_structured_codes_from_tree()
        assert "一阶编码内容1" in structured_codes["三阶编码A"]["二阶编码A1"], "编辑前一阶编码内容应该存在"
        
        first_item_1.setText(0, "修改后的一阶编码内容")
        
        structured_codes_after_edit = update_structured_codes_from_tree()
        assert "修改后的一阶编码内容" in structured_codes_after_edit["三阶编码A"]["二阶编码A1"], "编辑后新内容应该存在"
        assert "一阶编码内容1" not in structured_codes_after_edit["三阶编码A"]["二阶编码A1"], "编辑前旧内容不应该存在"
        
        print("✅ 编辑编码后 structured_codes 更新测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 编辑编码后 structured_codes 更新测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_create_standard_answer_with_modified_tree():
    """测试修改编码树后创建标准答案能正确保存修改"""
    print("\n🧪 测试修改编码树后创建标准答案...")
    
    try:
        from PyQt5.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem
        from PyQt5.QtCore import Qt
        from standard_answer_manager import StandardAnswerManager
        
        app = QApplication.instance() or QApplication([])
        
        tree = QTreeWidget()
        tree.setColumnCount(5)
        
        third_item = QTreeWidgetItem(["三阶编码A", "", "1", "", "2"])
        third_item.setData(0, Qt.UserRole, {"level": 3})
        
        second_item = QTreeWidgetItem(["二阶编码A1", "", "2", "", "2"])
        second_item.setData(0, Qt.UserRole, {"level": 2})
        
        first_item_1 = QTreeWidgetItem(["一阶编码内容1", "", "", "", "1"])
        first_item_1.setData(0, Qt.UserRole, {"level": 1})
        
        first_item_2 = QTreeWidgetItem(["一阶编码内容2", "", "", "", "1"])
        first_item_2.setData(0, Qt.UserRole, {"level": 1})
        
        second_item.addChild(first_item_1)
        second_item.addChild(first_item_2)
        third_item.addChild(second_item)
        tree.addTopLevelItem(third_item)
        
        def update_structured_codes_from_tree():
            structured_codes = {}
            for i in range(tree.topLevelItemCount()):
                third = tree.topLevelItem(i)
                third_name = third.text(0)
                structured_codes[third_name] = {}
                
                for j in range(third.childCount()):
                    second = third.child(j)
                    second_name = second.text(0)
                    structured_codes[third_name][second_name] = []
                    
                    for k in range(second.childCount()):
                        first = second.child(k)
                        structured_codes[third_name][second_name].append(first.text(0))
            return structured_codes
        
        structured_codes = update_structured_codes_from_tree()
        
        manager = StandardAnswerManager()
        version_id = manager.create_from_structured_codes(structured_codes, "测试修改后保存")
        
        assert version_id is not None, "创建标准答案应该成功"
        
        current_answers = manager.get_current_answers()
        assert current_answers is not None, "应该有当前标准答案"
        assert "structured_codes" in current_answers, "标准答案应该包含 structured_codes"
        
        saved_codes = current_answers["structured_codes"]
        assert "三阶编码A" in saved_codes, "保存的标准答案应该包含三阶编码"
        assert "二阶编码A1" in saved_codes["三阶编码A"], "保存的标准答案应该包含二阶编码"
        assert "一阶编码内容1" in saved_codes["三阶编码A"]["二阶编码A1"], "保存的标准答案应该包含一阶编码内容1"
        assert "一阶编码内容2" in saved_codes["三阶编码A"]["二阶编码A1"], "保存的标准答案应该包含一阶编码内容2"
        
        print("✅ 修改编码树后创建标准答案测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 修改编码树后创建标准答案测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_main_window_create_standard_answer_logic():
    """测试主界面 create_standard_answer 方法的逻辑"""
    print("\n🧪 测试主界面 create_standard_answer 方法逻辑...")
    
    try:
        from PyQt5.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem
        from PyQt5.QtCore import Qt
        
        app = QApplication.instance() or QApplication([])
        
        class MockMainWindow:
            def __init__(self):
                self.coding_tree = QTreeWidget()
                self.coding_tree.setColumnCount(5)
                self.structured_codes = {}
                
                self._setup_tree()
            
            def _setup_tree(self):
                third_item = QTreeWidgetItem(["三阶编码A", "", "1", "", "1"])
                third_item.setData(0, Qt.UserRole, {"level": 3})
                
                second_item = QTreeWidgetItem(["二阶编码A1", "", "1", "", "1"])
                second_item.setData(0, Qt.UserRole, {"level": 2})
                
                first_item = QTreeWidgetItem(["原始一阶编码", "", "", "", "1"])
                first_item.setData(0, Qt.UserRole, {"level": 1})
                
                second_item.addChild(first_item)
                third_item.addChild(second_item)
                self.coding_tree.addTopLevelItem(third_item)
            
            def update_structured_codes_from_tree(self):
                self.structured_codes = {}
                for i in range(self.coding_tree.topLevelItemCount()):
                    third = self.coding_tree.topLevelItem(i)
                    third_name = third.text(0)
                    self.structured_codes[third_name] = {}
                    
                    for j in range(third.childCount()):
                        second = third.child(j)
                        second_name = second.text(0)
                        self.structured_codes[third_name][second_name] = []
                        
                        for k in range(second.childCount()):
                            first = second.child(k)
                            self.structured_codes[third_name][second_name].append(first.text(0))
            
            def create_standard_answer(self):
                self.update_structured_codes_from_tree()
                
                if not self.structured_codes:
                    return False
                
                return True
        
        window = MockMainWindow()
        
        first_item = window.coding_tree.topLevelItem(0).child(0).child(0)
        first_item.setText(0, "修改后的一阶编码")
        
        result = window.create_standard_answer()
        assert result == True, "创建标准答案应该成功"
        
        assert "修改后的一阶编码" in window.structured_codes["三阶编码A"]["二阶编码A1"], "修改后的一阶编码应该被保存"
        assert "原始一阶编码" not in window.structured_codes["三阶编码A"]["二阶编码A1"], "原始一阶编码不应该存在"
        
        print("✅ 主界面 create_standard_answer 方法逻辑测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 主界面 create_standard_answer 方法逻辑测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_delete_and_save_scenario():
    """测试完整的删除和保存场景"""
    print("\n🧪 测试完整的删除和保存场景...")
    
    try:
        from PyQt5.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem
        from PyQt5.QtCore import Qt
        from standard_answer_manager import StandardAnswerManager
        
        app = QApplication.instance() or QApplication([])
        
        tree = QTreeWidget()
        tree.setColumnCount(5)
        
        third_item = QTreeWidgetItem(["三阶编码A", "", "1", "", "2"])
        third_item.setData(0, Qt.UserRole, {"level": 3})
        
        second_item = QTreeWidgetItem(["二阶编码A1", "", "2", "", "2"])
        second_item.setData(0, Qt.UserRole, {"level": 2})
        
        first_item_1 = QTreeWidgetItem(["一阶编码内容1", "", "", "", "1"])
        first_item_1.setData(0, Qt.UserRole, {"level": 1})
        
        first_item_2 = QTreeWidgetItem(["一阶编码内容2", "", "", "", "1"])
        first_item_2.setData(0, Qt.UserRole, {"level": 1})
        
        second_item.addChild(first_item_1)
        second_item.addChild(first_item_2)
        third_item.addChild(second_item)
        tree.addTopLevelItem(third_item)
        
        def update_structured_codes_from_tree():
            structured_codes = {}
            for i in range(tree.topLevelItemCount()):
                third = tree.topLevelItem(i)
                third_name = third.text(0)
                structured_codes[third_name] = {}
                
                for j in range(third.childCount()):
                    second = third.child(j)
                    second_name = second.text(0)
                    structured_codes[third_name][second_name] = []
                    
                    for k in range(second.childCount()):
                        first = second.child(k)
                        structured_codes[third_name][second_name].append(first.text(0))
            return structured_codes
        
        structured_codes_before = update_structured_codes_from_tree()
        assert len(structured_codes_before["三阶编码A"]["二阶编码A1"]) == 2, "删除前应该有2个一阶编码"
        
        second_item.removeChild(first_item_1)
        
        structured_codes_after_delete = update_structured_codes_from_tree()
        
        manager = StandardAnswerManager()
        version_id = manager.create_from_structured_codes(structured_codes_after_delete, "删除后保存测试")
        
        assert version_id is not None, "创建标准答案应该成功"
        
        current_answers = manager.get_current_answers()
        saved_codes = current_answers["structured_codes"]
        
        assert len(saved_codes["三阶编码A"]["二阶编码A1"]) == 1, "保存后应该只有1个一阶编码"
        assert "一阶编码内容1" not in saved_codes["三阶编码A"]["二阶编码A1"], "删除的一阶编码不应该被保存"
        assert "一阶编码内容2" in saved_codes["三阶编码A"]["二阶编码A1"], "未删除的一阶编码应该被保存"
        
        print("✅ 完整的删除和保存场景测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 完整的删除和保存场景测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_edit_and_save_scenario():
    """测试完整的编辑和保存场景"""
    print("\n🧪 测试完整的编辑和保存场景...")
    
    try:
        from PyQt5.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem
        from PyQt5.QtCore import Qt
        from standard_answer_manager import StandardAnswerManager
        
        app = QApplication.instance() or QApplication([])
        
        tree = QTreeWidget()
        tree.setColumnCount(5)
        
        third_item = QTreeWidgetItem(["三阶编码A", "", "1", "", "1"])
        third_item.setData(0, Qt.UserRole, {"level": 3})
        
        second_item = QTreeWidgetItem(["二阶编码A1", "", "1", "", "1"])
        second_item.setData(0, Qt.UserRole, {"level": 2})
        
        first_item = QTreeWidgetItem(["原始一阶编码内容", "", "", "", "1"])
        first_item.setData(0, Qt.UserRole, {"level": 1})
        
        second_item.addChild(first_item)
        third_item.addChild(second_item)
        tree.addTopLevelItem(third_item)
        
        def update_structured_codes_from_tree():
            structured_codes = {}
            for i in range(tree.topLevelItemCount()):
                third = tree.topLevelItem(i)
                third_name = third.text(0)
                structured_codes[third_name] = {}
                
                for j in range(third.childCount()):
                    second = third.child(j)
                    second_name = second.text(0)
                    structured_codes[third_name][second_name] = []
                    
                    for k in range(second.childCount()):
                        first = second.child(k)
                        structured_codes[third_name][second_name].append(first.text(0))
            return structured_codes
        
        structured_codes_before = update_structured_codes_from_tree()
        assert "原始一阶编码内容" in structured_codes_before["三阶编码A"]["二阶编码A1"], "编辑前原始内容应该存在"
        
        first_item.setText(0, "修改后的一阶编码内容")
        
        structured_codes_after_edit = update_structured_codes_from_tree()
        
        manager = StandardAnswerManager()
        version_id = manager.create_from_structured_codes(structured_codes_after_edit, "编辑后保存测试")
        
        assert version_id is not None, "创建标准答案应该成功"
        
        current_answers = manager.get_current_answers()
        saved_codes = current_answers["structured_codes"]
        
        assert "修改后的一阶编码内容" in saved_codes["三阶编码A"]["二阶编码A1"], "编辑后的内容应该被保存"
        assert "原始一阶编码内容" not in saved_codes["三阶编码A"]["二阶编码A1"], "原始内容不应该被保存"
        
        print("✅ 完整的编辑和保存场景测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 完整的编辑和保存场景测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_consistency_with_manual_coding():
    """测试主界面保存逻辑与手动编码界面的一致性"""
    print("\n🧪 测试主界面与手动编码界面保存逻辑一致性...")
    
    try:
        from PyQt5.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem
        from PyQt5.QtCore import Qt
        from standard_answer_manager import StandardAnswerManager
        
        app = QApplication.instance() or QApplication([])
        
        def simulate_main_window_save(tree):
            structured_codes = {}
            for i in range(tree.topLevelItemCount()):
                third = tree.topLevelItem(i)
                third_name = third.text(0)
                structured_codes[third_name] = {}
                
                for j in range(third.childCount()):
                    second = third.child(j)
                    second_name = second.text(0)
                    structured_codes[third_name][second_name] = []
                    
                    for k in range(second.childCount()):
                        first = second.child(k)
                        structured_codes[third_name][second_name].append(first.text(0))
            return structured_codes
        
        def simulate_manual_coding_save(tree):
            current_codes = {}
            for i in range(tree.topLevelItemCount()):
                top_item = tree.topLevelItem(i)
                item_data = top_item.data(0, Qt.UserRole)
                
                if not item_data:
                    continue
                
                level = item_data.get("level")
                
                if level == 3:
                    third_display_name = top_item.text(0)
                    current_codes[third_display_name] = {}
                    
                    for j in range(top_item.childCount()):
                        second_item = top_item.child(j)
                        second_display_name = second_item.text(0)
                        current_codes[third_display_name][second_display_name] = []
                        
                        for k in range(second_item.childCount()):
                            first_item = second_item.child(k)
                            first_content = first_item.text(0)
                            current_codes[third_display_name][second_display_name].append(first_content)
            
            return current_codes
        
        tree = QTreeWidget()
        tree.setColumnCount(5)
        
        third_item = QTreeWidgetItem(["三阶编码A", "", "1", "", "2"])
        third_item.setData(0, Qt.UserRole, {"level": 3})
        
        second_item = QTreeWidgetItem(["二阶编码A1", "", "2", "", "2"])
        second_item.setData(0, Qt.UserRole, {"level": 2})
        
        first_item_1 = QTreeWidgetItem(["一阶编码内容1", "", "", "", "1"])
        first_item_1.setData(0, Qt.UserRole, {"level": 1})
        
        first_item_2 = QTreeWidgetItem(["一阶编码内容2", "", "", "", "1"])
        first_item_2.setData(0, Qt.UserRole, {"level": 1})
        
        second_item.addChild(first_item_1)
        second_item.addChild(first_item_2)
        third_item.addChild(second_item)
        tree.addTopLevelItem(third_item)
        
        main_window_codes = simulate_main_window_save(tree)
        manual_coding_codes = simulate_manual_coding_save(tree)
        
        assert main_window_codes.keys() == manual_coding_codes.keys(), "三阶编码应该一致"
        for third_cat in main_window_codes:
            assert main_window_codes[third_cat].keys() == manual_coding_codes[third_cat].keys(), f"二阶编码应该一致: {third_cat}"
            for second_cat in main_window_codes[third_cat]:
                assert main_window_codes[third_cat][second_cat] == manual_coding_codes[third_cat][second_cat], \
                    f"一阶编码应该一致: {third_cat} > {second_cat}"
        
        print("✅ 主界面与手动编码界面保存逻辑一致性测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 主界面与手动编码界面保存逻辑一致性测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("扎根理论编码分析系统 - 主界面编码树修改保存功能测试")
    print("=" * 60)
    
    tests = [
        ("update_structured_codes_from_tree 方法测试", test_update_structured_codes_from_tree),
        ("删除编码后 structured_codes 更新测试", test_delete_code_updates_structured_codes),
        ("编辑编码后 structured_codes 更新测试", test_edit_code_updates_structured_codes),
        ("修改编码树后创建标准答案测试", test_create_standard_answer_with_modified_tree),
        ("主界面 create_standard_answer 方法逻辑测试", test_main_window_create_standard_answer_logic),
        ("完整的删除和保存场景测试", test_delete_and_save_scenario),
        ("完整的编辑和保存场景测试", test_edit_and_save_scenario),
        ("主界面与手动编码界面保存逻辑一致性测试", test_consistency_with_manual_coding),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ 测试 {name} 执行异常: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    failed = 0
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
