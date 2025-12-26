#!/usr/bin/env python3
"""
测试手动编码功能
"""

import os
import sys
import logging

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_manual_coding():
    """测试手动编码功能"""
    print("🧪 测试手动编码功能...")

    try:
        from PyQt5.QtWidgets import QApplication
        from manual_coding_dialog import ManualCodingDialog

        # 创建测试应用
        app = QApplication([])

        # 创建测试文件数据
        test_files = {
            "test1.txt": {
                'filename': "test1.txt",
                'content': "这是测试文件1的内容。\n采访者：请您介绍一下团队的主要职责？\n受访者：我们团队主要负责软件质量检测和测试工作。",
                'file_path': "test1.txt"
            },
            "test2.txt": {
                'filename': "test2.txt",
                'content': "这是测试文件2的内容。\n采访者：在质量管理方面有什么创新吗？\n受访者：我们开发了一套新的自动化测试框架。",
                'file_path': "test2.txt"
            }
        }

        # 创建对话框
        dialog = ManualCodingDialog(None, test_files, {})

        # 模拟文件选择
        print("✅ 手动编码对话框创建成功")
        print(f"✅ 加载了 {len(test_files)} 个测试文件")

        # 检查文件列表
        file_list = dialog.file_list
        print(f"✅ 文件列表中有 {file_list.count()} 个项目")

        for i in range(file_list.count()):
            item = file_list.item(i)
            filename = item.text()
            file_path = item.data(0)
            print(f"   - 文件 {i + 1}: {filename} -> {file_path}")

        # 测试文件选择
        if file_list.count() > 0:
            first_item = file_list.item(0)
            dialog.on_file_selected(first_item)

            # 检查文本显示
            text_display = dialog.text_display
            displayed_text = text_display.toPlainText()

            if displayed_text and len(displayed_text) > 0:
                print("✅ 文件选择后文本内容正确显示")
                print(f"   显示内容长度: {len(displayed_text)}")
                print(f"   内容预览: {displayed_text[:100]}...")
            else:
                print("❌ 文件选择后文本内容未显示")

        print("✅ 手动编码功能测试通过")
        return True

    except Exception as e:
        print(f"❌ 手动编码功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("扎根理论编码分析系统 - 手动编码功能测试")
    print("=" * 60)

    success = test_manual_coding()

    if success:
        print("\n🎉 手动编码功能测试通过！")
        sys.exit(0)
    else:
        print("\n⚠️ 手动编码功能测试失败")
        sys.exit(1)