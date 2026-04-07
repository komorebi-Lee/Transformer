import json

# 读取提取的编码数据
with open('extracted_coding_data.json', 'r', encoding='utf-8') as f:
    coding_data = json.load(f)

# 按三阶编码分组
third_level_groups = {}
for item in coding_data:
    third_level = item['third_order']
    if third_level not in third_level_groups:
        third_level_groups[third_level] = {}
    
    second_level = item['second_order']
    if second_level not in third_level_groups[third_level]:
        third_level_groups[third_level][second_level] = []
    
    third_level_groups[third_level][second_level].append(item['first_order'])

# 生成描述信息
coding_with_descriptions = []

for third_level, second_levels in third_level_groups.items():
    # 分析三阶编码的含义
    third_level_description = f"描述{third_level}相关的内容"
    
    # 分析二阶编码的含义
    second_level_codes = []
    for second_level, first_orders in second_levels.items():
        # 生成二阶编码的描述
        second_level_description = f"包含：{', '.join(first_orders)}"
        
        second_level_codes.append({
            'name': second_level,
            'description': second_level_description
        })
    
    coding_with_descriptions.append({
        'third_level': third_level,
        'third_level_description': third_level_description,
        'second_level_codes': second_level_codes
    })

# 保存分析结果
with open('coding_with_descriptions.json', 'w', encoding='utf-8') as f:
    json.dump(coding_with_descriptions, f, ensure_ascii=False, indent=2)

print(f"分析完成，共分析 {len(coding_with_descriptions)} 个三阶编码")
