import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from semantic_matcher import SemanticMatcher
from coding_library_manager import CodingLibraryManager


def test_incremental_learning():
    """测试增量学习功能"""
    print("=== 测试增量学习功能 ===")
    
    # 初始化语义匹配器
    matcher = SemanticMatcher()
    
    # 初始化编码库管理器
    library_manager = CodingLibraryManager(semantic_matcher=matcher)
    
    # 获取二阶编码列表
    second_level_codes = library_manager.get_all_second_level_codes()
    print(f"加载编码库成功，包含 {len(second_level_codes)} 个二阶编码")
    
    # 测试用例1：模拟用户反馈
    print("\n1. 测试用户反馈功能")
    
    # 模拟一阶编码文本
    test_cases = [
        ("员工为了快速完成任务，跳过了正常的审批流程", "4.1"),  # 审批流程 bypass
        ("员工出于好奇心，在工作时间尝试新的技术方案", "1.2"),  # 兴趣与好奇心驱动
        ("员工担心越轨行为会被领导批评", "7.1"),  # 职业惩罚恐惧
    ]
    
    for first_level_text, expected_code_id in test_cases:
        # 先进行匹配
        matches = matcher.match_first_level_to_second_level(first_level_text, second_level_codes)
        print(f"\n一阶编码: {first_level_text}")
        print("匹配结果:")
        for i, (code, similarity) in enumerate(matches):
            print(f"  {i+1}. {code['name']} (相似度: {similarity:.2f}, ID: {code['id']})")
        
        # 模拟用户反馈
        if matches:
            # 假设第一个匹配是正确的
            is_correct = matches[0]['id'] == expected_code_id
            matcher.record_feedback(first_level_text, matches[0], is_correct)
            print(f"反馈: {'正确' if is_correct else '错误'}")
    
    # 测试用例2：查看反馈统计
    print("\n2. 测试反馈统计功能")
    stats = matcher.get_feedback_stats()
    print(f"反馈统计: {stats}")
    
    # 测试用例3：测试增量训练
    print("\n3. 测试增量训练功能")
    if stats['total_feedback'] >= 10:
        success = matcher.incremental_train(epochs=2, batch_size=4)
        print(f"增量训练 {'成功' if success else '失败'}")
    else:
        print(f"反馈数据不足，需要至少10条反馈，当前有 {stats['total_feedback']} 条")
    
    # 测试用例4：测试编码库动态更新
    print("\n4. 测试编码库动态更新")
    # 尝试添加一个新的二阶编码
    new_code_id = "test.1"
    new_code_name = "测试编码"
    new_code_desc = "用于测试增量学习的编码"
    
    # 找到第一个三阶编码
    third_level_codes = library_manager.get_all_third_level_codes()
    if third_level_codes:
        third_level_id = third_level_codes[0]['id']
        success = library_manager.add_second_level_code(third_level_id, new_code_id, new_code_name, new_code_desc)
        print(f"添加新编码 {'成功' if success else '失败'}")
        
        # 再次测试匹配
        if success:
            test_text = "这是一个测试编码的示例文本"
            updated_codes = library_manager.get_all_second_level_codes()
            matches = matcher.match_first_level_to_second_level(test_text, updated_codes)
            print(f"\n测试新编码匹配:")
            for i, (code, similarity) in enumerate(matches):
                print(f"  {i+1}. {code['name']} (相似度: {similarity:.2f}, ID: {code['id']})")
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    test_incremental_learning()
