import json
import os
import sys
from enhanced_manual_coding import EnhancedManualCoding
from coding_library_manager import CodingLibraryManager

# 创建测试数据
test_training_data = {
    "training_data": [
        {
            "target_third_category": "测试三阶编码1",
            "target_second_category": "测试二阶编码1",
            "target_abstract": "测试一阶编码1"
        },
        {
            "target_third_category": "测试三阶编码1",
            "target_second_category": "测试二阶编码2",
            "target_abstract": "测试一阶编码2"
        },
        {
            "target_third_category": "测试三阶编码2",
            "target_second_category": "测试二阶编码3",
            "target_abstract": "测试一阶编码3"
        }
    ]
}

print("测试开始：编码库更新功能优化")
print("=" * 50)

# 测试1：从training_data获取编码信息并更新编码库
print("\n测试1：从training_data获取编码信息并更新编码库")
enhanced_coding = EnhancedManualCoding()
result = enhanced_coding.process_standard_answer(test_training_data)
print(f"处理结果: {result['success']}")
if result['success']:
    print(f"新增三阶编码: {result['result']['added_third_level_codes']}")
    print(f"更新三阶编码: {result['result']['updated_third_level_codes']}")
    print(f"新增二阶编码: {result['result']['added_second_level_codes']}")
    print(f"更新二阶编码: {result['result']['updated_second_level_codes']}")

# 测试2：验证二阶编码ID格式
print("\n测试2：验证二阶编码ID格式")
coding_library_manager = CodingLibraryManager()
second_level_codes = coding_library_manager.get_all_second_level_codes()
print(f"编码库中的二阶编码数量: {len(second_level_codes)}")
print("二阶编码ID和名称:")
for code in second_level_codes:
    code_id = code.get('id')
    name = code.get('name')
    third_level = code.get('third_level')
    third_level_id = code.get('third_level_id')
    print(f"- ID: {code_id}, 名称: {name}, 所属三阶: {third_level}, 三阶ID: {third_level_id}")
    # 验证ID格式
    if code_id and '.' in code_id:
        parts = code_id.split('.')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            print(f"  OK ID格式正确: {code_id}")
        else:
            print(f"  ERROR ID格式错误: {code_id}")
    else:
        print(f"  ERROR ID格式错误: {code_id}")

# 测试3：验证重复编码判断
print("\n测试3：验证重复编码判断")
# 再次处理相同的训练数据，应该不会重复添加
result2 = enhanced_coding.process_standard_answer(test_training_data)
print(f"处理结果: {result2['success']}")
if result2['success']:
    print(f"新增三阶编码: {result2['result']['added_third_level_codes']}")
    print(f"更新三阶编码: {result2['result']['updated_third_level_codes']}")
    print(f"新增二阶编码: {result2['result']['added_second_level_codes']}")
    print(f"更新二阶编码: {result2['result']['updated_second_level_codes']}")

print("\n测试完成！")
print("=" * 50)