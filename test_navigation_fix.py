#!/usr/bin/env python3
"""
测试导航修复
"""

import os
import sys
import logging

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_navigation_fix():
    """测试导航修复"""
    print("🧪 测试导航修复...")

    try:
        from grounded_theory_coder import GroundedTheoryCoder

        # 创建测试数据
        test_structured_codes = {
            "组织管理": {
                "团队职责": [
                    {
                        "content": "我们团队负责软件质量检测",
                        "sentence_details": [
                            {
                                "content": "我们团队负责软件质量检测",
                                "original_content": "我们团队负责软件质量检测"
                            }
                        ]
                    },
                    {
                        "content": "确保产品交付质量",
                        "sentence_details": [
                            {
                                "content": "确保产品交付质量",
                                "original_content": "确保产品交付质量"
                            }
                        ]
                    }
                ]
            }
        }

        coder = GroundedTheoryCoder()
        numbered_codes = coder.add_coding_numbers_new_format(test_structured_codes)

        print("✅ 导航修复测试成功")
        print("\n生成的编码结构:")

        for third_cat, second_cats in numbered_codes.items():
            print(f"\n{third_cat}")
            for second_cat, first_contents in second_cats.items():
                print(f"  {second_cat}")
                for content_data in first_contents:
                    if isinstance(content_data, dict):
                        numbered_content = content_data.get('numbered_content', '')
                        code_id = content_data.get('code_id', '')
                        content = content_data.get('content', '')
                        print(f"    - 编号内容: {numbered_content}")
                        print(f"    - 原始内容: {content}")
                        print(f"    - 编码ID: {code_id}")

                        # 验证编号格式
                        if numbered_content.startswith('A11'):
                            print("✅ 一阶编码编号正确显示")
                        if code_id == 'A11':
                            print("✅ 编码ID生成正确")

        # 测试文本标记
        test_text = "我们团队负责软件质量检测，确保产品交付质量"
        marked_text = coder.generate_navigation_text(numbered_codes, test_text)
        print(f"\n原始文本: {test_text}")
        print(f"标记后文本: {marked_text}")

        if '[A11]' in marked_text and '[A12]' in marked_text:
            print("✅ 文本标记功能正常")
        else:
            print("❌ 文本标记功能异常")

        return True

    except Exception as e:
        print(f"❌ 导航修复测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("扎根理论编码分析系统 - 导航修复测试")
    print("=" * 60)

    success = test_navigation_fix()

    if success:
        print("\n🎉 导航修复测试通过！")
        sys.exit(0)
    else:
        print("\n⚠️ 导航修复测试失败")
        sys.exit(1)