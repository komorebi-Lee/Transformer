import json
import os
import sys
from enhanced_manual_coding import EnhancedManualCoding
from training_manager import EnhancedTrainingManager

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

print("测试开始：编码库更新逻辑优化")
print("=" * 50)

# 测试1：从training_data获取编码信息
print("\n测试1：从training_data获取编码信息")
enhanced_coding = EnhancedManualCoding()
result = enhanced_coding.process_standard_answer(test_training_data)
print(f"处理结果: {result['success']}")
if result['success']:
    print(f"新增三阶编码: {result['result']['added_third_level_codes']}")
    print(f"更新三阶编码: {result['result']['updated_third_level_codes']}")
    print(f"新增二阶编码: {result['result']['added_second_level_codes']}")
    print(f"更新二阶编码: {result['result']['updated_second_level_codes']}")

# 测试2：验证编码库更新
print("\n测试2：验证编码库更新")
with open('coding_library.json', 'r', encoding='utf-8') as f:
    library_data = json.load(f)

third_level_codes = library_data.get('encoding_library', {}).get('third_level_codes', [])
print(f"编码库中的三阶编码数量: {len(third_level_codes)}")
print("三阶编码名称:")
for code in third_level_codes:
    print(f"- {code['name']}")
    second_level_codes = code.get('second_level_codes', [])
    print(f"  包含二阶编码数量: {len(second_level_codes)}")
    for second_code in second_level_codes[:2]:  # 只显示前2个
        print(f"  - {second_code['name']}")
    if len(second_level_codes) > 2:
        print(f"  ... 等 {len(second_level_codes) - 2} 个编码")

print("\n测试完成！")
print("=" * 50)