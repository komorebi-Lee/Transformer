import json

# 读取现有编码库
with open('coding_library.json', 'r', encoding='utf-8') as f:
    existing_library = json.load(f)

# 读取带有描述信息的编码数据
with open('coding_with_descriptions.json', 'r', encoding='utf-8') as f:
    coding_data = json.load(f)

# 获取当前最大的三阶编码ID
current_max_id = 0
for third_level in existing_library['encoding_library']['third_level_codes']:
    if third_level['id'] > current_max_id:
        current_max_id = third_level['id']

print(f"当前最大三阶编码ID: {current_max_id}")

# 转换数据为编码库格式
new_third_level_codes = []
new_id = current_max_id + 1

# 去重：记录已添加的三阶编码名称
added_third_levels = set()

for item in coding_data:
    third_level = item['third_level']
    
    # 去重检查
    if third_level in added_third_levels:
        continue
    added_third_levels.add(third_level)
    
    # 构建二阶编码
    second_level_codes = []
    second_level_id = 1
    
    for second_level_item in item['second_level_codes']:
        second_level_codes.append({
            'id': f"{new_id}.{second_level_id}",
            'name': second_level_item['name'],
            'description': second_level_item['description'],
            'third_level': third_level,
            'third_level_id': new_id
        })
        second_level_id += 1
    
    # 构建三阶编码
    new_third_level_codes.append({
        'id': new_id,
        'name': third_level,
        'description': item['third_level_description'],
        'second_level_codes': second_level_codes
    })
    
    new_id += 1

# 将新编码添加到现有编码库
updated_library = existing_library.copy()
updated_library['encoding_library']['third_level_codes'].extend(new_third_level_codes)

# 更新版本信息
updated_library['version'] = "2.1"
updated_library['created_at'] = "2026-04-07"
updated_library['description'] = "员工越轨创新行为分层编码库，包含6大核心维度、24个主范畴及其详细定义，新增市场竞争和企业发展相关编码，以及从新增编码库编码文件夹中提取的编码"

# 保存更新后的编码库
with open('updated_coding_library.json', 'w', encoding='utf-8') as f:
    json.dump(updated_library, f, ensure_ascii=False, indent=2)

print(f"转换完成，新增 {len(new_third_level_codes)} 个三阶编码")
print(f"更新后的编码库已保存到 updated_coding_library.json")
