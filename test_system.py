#!/usr/bin/env python3
"""
系统测试脚本
测试完整的扎根理论编码流程
"""

import os
import sys
import logging
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_complete_workflow():
    """测试完整的工作流程"""
    print("🧪 开始测试完整的工作流程...")

    try:
        # 导入必要的模块
        from data_processor import DataProcessor
        from enhanced_coding_generator import EnhancedCodingGenerator
        from grounded_theory_coder import GroundedTheoryCoder
        from model_manager import EnhancedModelManager
        from standard_answer_manager import StandardAnswerManager

        # 初始化管理器
        data_processor = DataProcessor()
        coding_generator = EnhancedCodingGenerator()
        grounded_coder = GroundedTheoryCoder()
        model_manager = EnhancedModelManager()
        standard_manager = StandardAnswerManager()

        print("✅ 管理器初始化成功")

        # 创建测试数据
        test_text = """
        访谈记录示例：

        采访者：请您介绍一下团队的主要职责？
        受访者：我们团队主要负责软件质量检测和测试工作，确保产品交付质量。

        采访者：在质量管理方面有什么创新吗？
        受访者：我们开发了一套新的自动化测试框架，大大提高了测试效率。

        采访者：团队面临的主要挑战是什么？
        受访者：最大的挑战是技术更新快，需要不断学习新的测试方法。

        采访者：团队氛围怎么样？
        受访者：团队氛围很好，大家互相支持，有很强的归属感。
        """

        # 保存测试文件
        test_file = "test_interview.txt"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_text)

        print("✅ 测试文件创建成功")

        # 处理文件
        processed_data = data_processor.process_multiple_files([test_file])
        print(f"✅ 文件处理成功，提取 {processed_data['total_sentences']} 个句子")

        # 生成编码（基于规则）
        raw_codes = coding_generator.generate_grounded_theory_codes_multi_files(
            processed_data, model_manager, use_trained_model=False
        )

        # 构建编码结构
        structured_codes = grounded_coder.build_coding_structure(raw_codes)

        print(f"✅ 编码生成成功:")
        print(f"   - 三阶编码: {len(structured_codes)} 个")
        total_second = sum(len(categories) for categories in structured_codes.values())
        total_first = sum(len(contents) for categories in structured_codes.values() for contents in categories.values())
        print(f"   - 二阶编码: {total_second} 个")
        print(f"   - 一阶编码: {total_first} 个")

        # 显示部分编码结果
        for third_cat, second_cats in list(structured_codes.items())[:2]:
            print(f"\n三阶编码: {third_cat}")
            for second_cat, first_contents in list(second_cats.items())[:2]:
                print(f"  二阶编码: {second_cat}")
                for content_data in first_contents[:2]:
                    if isinstance(content_data, dict):
                        content = content_data.get('content', '')[:50] + "..."
                        print(f"    - {content}")

        # 保存为标准答案
        version_id = standard_manager.create_from_structured_codes(
            structured_codes, "测试标准答案"
        )

        print(f"✅ 标准答案保存成功: {version_id}")

        # 清理测试文件
        if os.path.exists(test_file):
            os.remove(test_file)

        print("\n🎉 完整工作流程测试通过！")
        return True

    except Exception as e:
        print(f"❌ 工作流程测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("扎根理论编码分析系统 - 完整流程测试")
    print("=" * 60)

    success = test_complete_workflow()

    if success:
        print("\n🎊 所有测试通过！系统可以正常使用。")
        print("下一步：运行 python app_launcher.py 启动图形界面")
        sys.exit(0)
    else:
        print("\n⚠️ 测试失败，请检查上述错误信息")
        sys.exit(1)