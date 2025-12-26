#!/usr/bin/env python3
"""
测试新的编号系统
"""

import os
import sys
import logging

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_new_numbering_system():
    """测试新的编号系统"""
    print("🧪 测试新的编号系统...")

    try:
        from grounded_theory_coder import GroundedTheoryCoder

        # 创建测试数据
        test_structured_codes = {
            "组织管理": {
                "团队职责": [
                    {"content": "我们团队负责软件质量检测",
                     "sentence_details": [{"content": "我们团队负责软件质量检测", "original_content": "我们团队负责软件质量检测"}]},
                    {"content": "确保产品交付质量",
                     "sentence_details": [{"content": "确保产品交付质量", "original_content": "确保产品交付质量"}]}
                ],
                "领导决策": [
                    {"content": "领导负责资源分配",
                     "sentence_details": [{"content": "领导负责资源分配", "original_content": "领导负责资源分配"}]}
                ]
            },
            "技术研发": {
                "创新方法": [
                    {"content": "开发自动化测试框架",
                     "sentence_details": [{"content": "开发自动化测试框架", "original_content": "开发自动化测试框架"}]},
                    {"content": "提高测试效率", "sentence_details": [{"content": "提高测试效率", "original_content": "提高测试效率"}]}
                ]
            },
            "团队氛围": {
                "心理感受": [
                    {"content": "团队氛围很好", "sentence_details": [{"content": "团队氛围很好", "original_content": "团队氛围很好"}]},
                    {"content": "大家互相支持", "sentence_details": [{"content": "大家互相支持", "original_content": "大家互相支持"}]}
                ]
            }
        }

        coder = GroundedTheoryCoder()
        numbered_codes = coder.add_coding_numbers_new_format(test_structured_codes)

        print("✅ 编号系统测试成功")
        print("\n生成的编码结构:")

        for third_cat, second_cats in numbered_codes.items():
            print(f"\n{third_cat}")
            for second_cat, first_contents in second_cats.items():
                print(f"  {second_cat}")
                for content_data in first_contents:
                    if isinstance(content_data, dict):
                        numbered_content = content_data.get('numbered_content', '')
                        code_id = content_data.get('code_id', '')
                        print(f"    - {numbered_content} (ID: {code_id})")

        # 验证编号格式
        third_categories = list(numbered_codes.keys())
        if third_categories:
            first_third = third_categories[0]
            if first_third.startswith('A '):
                print("✅ 三阶编码编号正确: A, B, C...")

            second_categories = list(numbered_codes[first_third].keys())
            if second_categories:
                first_second = second_categories[0]
                if first_second.startswith('A1'):
                    print("✅ 二阶编码编号正确: A1, A2, B1, B2...")

                first_contents = numbered_codes[first_third][first_second]
                if first_contents:
                    first_content = first_contents[0]
                    if isinstance(first_content, dict):
                        code_id = first_content.get('code_id', '')
                        if code_id.startswith('A11'):
                            print("✅ 一阶编码编号正确: A11, A12, B21, B22...")

        return True

    except Exception as e:
        print(f"❌ 编号系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("扎根理论编码分析系统 - 编号系统测试")
    print("=" * 60)

    success = test_new_numbering_system()

    if success:
        print("\n🎉 编号系统测试通过！")
        sys.exit(0)
    else:
        print("\n⚠️ 编号系统测试失败")
        sys.exit(1)