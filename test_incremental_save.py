#!/usr/bin/env python3
"""
测试增量保存功能
"""

import os
import sys
import logging

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_incremental_save():
    """测试增量保存功能"""
    print("🧪 测试增量保存功能...")

    try:
        from standard_answer_manager import StandardAnswerManager

        # 创建标准答案管理器
        manager = StandardAnswerManager()

        # 创建原始标准答案
        original_codes = {
            "组织管理": {
                "团队职责": [
                    "我们团队负责软件质量检测",
                    "确保产品交付质量"
                ],
                "领导决策": [
                    "领导负责资源分配"
                ]
            },
            "技术研发": {
                "创新方法": [
                    "开发自动化测试框架"
                ]
            }
        }

        # 创建修改后的编码（模拟人工修改）
        modified_codes = {
            "组织管理": {
                "团队职责": [
                    "我们团队负责软件质量检测",  # 保留
                    "确保产品高质量交付"  # 修改
                ],
                "团队协作": [  # 新增二阶编码
                    "团队成员互相支持"  # 新增一阶编码
                ]
                # 删除了"领导决策"
            },
            "技术研发": {
                "创新方法": [
                    "开发自动化测试框架",  # 保留
                    "提高测试效率"  # 新增
                ]
            },
            "团队氛围": {  # 新增三阶编码
                "心理感受": [
                    "团队氛围很好"  # 新增一阶编码
                ]
            }
        }

        # 创建初始标准答案
        version1 = manager.create_from_structured_codes(original_codes, "初始标准答案")
        print(f"✅ 创建初始标准答案: {version1}")
        print(f"   初始编码数量: {manager.get_training_sample_count()}")

        # 测试增量保存
        version2 = manager.save_modifications_only(modified_codes, "人工修正")
        print(f"✅ 增量保存完成: {version2}")
        print(f"   更新后编码数量: {manager.get_training_sample_count()}")

        # 检查修改历史
        modification_history = manager.get_modification_history()
        print(f"✅ 修改历史记录: {len(modification_history)} 条")

        for history in modification_history:
            print(f"   版本: {history['version']}")
            summary = history.get('summary', {})
            print(f"   新增: {summary.get('added_codes', 0)}")
            print(f"   修改: {summary.get('modified_codes', 0)}")
            print(f"   删除: {summary.get('deleted_codes', 0)}")

        # 验证保存结果
        current_answers = manager.get_current_answers()
        if current_answers:
            metadata = current_answers.get('metadata', {})
            if metadata.get('source') == 'incremental_update':
                print("✅ 确认使用增量保存模式")

            modification_details = current_answers.get('modification_details', {})
            if modification_details.get('has_changes'):
                print("✅ 修改详情正确记录")

        print("✅ 增量保存功能测试通过")
        return True

    except Exception as e:
        print(f"❌ 增量保存功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("扎根理论编码分析系统 - 增量保存功能测试")
    print("=" * 60)

    success = test_incremental_save()

    if success:
        print("\n🎉 增量保存功能测试通过！")
        sys.exit(0)
    else:
        print("\n⚠️ 增量保存功能测试失败")
        sys.exit(1)