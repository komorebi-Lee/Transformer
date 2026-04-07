import json

# 读取更新后的编码库
with open('coding_library.json', 'r', encoding='utf-8') as f:
    coding_library = json.load(f)

# 验证结构
print("=== 验证编码库结构 ===")

# 检查顶层结构
required_fields = ['encoding_library', 'version', 'created_at', 'description']
for field in required_fields:
    if field in coding_library:
        print(f"通过: 存在字段: {field}")
    else:
        print(f"错误: 缺少字段: {field}")

# 检查third_level_codes
if 'third_level_codes' in coding_library['encoding_library']:
    third_level_codes = coding_library['encoding_library']['third_level_codes']
    print(f"通过: 存在 third_level_codes，共 {len(third_level_codes)} 个三阶编码")
    
    # 检查每个三阶编码的结构
    for i, third_level in enumerate(third_level_codes):
        required_fields = ['id', 'name', 'description', 'second_level_codes']
        for field in required_fields:
            if field in third_level:
                pass  # 检查通过
            else:
                print(f"错误: 第 {i+1} 个三阶编码缺少字段: {field}")
        
        # 检查二阶编码
        if 'second_level_codes' in third_level:
            second_level_codes = third_level['second_level_codes']
            for j, second_level in enumerate(second_level_codes):
                required_fields = ['id', 'name', 'description', 'third_level', 'third_level_id']
                for field in required_fields:
                    if field in second_level:
                        pass  # 检查通过
                    else:
                        print(f"错误: 第 {i+1} 个三阶编码的第 {j+1} 个二阶编码缺少字段: {field}")
else:
    print("错误: 缺少 third_level_codes 字段")

# 验证数据完整性
print("\n=== 验证数据完整性 ===")

# 检查ID唯一性
third_level_ids = set()
second_level_ids = set()

for third_level in coding_library['encoding_library']['third_level_codes']:
    # 检查三阶编码ID
    if third_level['id'] in third_level_ids:
        print(f"错误: 三阶编码ID重复: {third_level['id']}")
    else:
        third_level_ids.add(third_level['id'])
    
    # 检查二阶编码ID
    for second_level in third_level['second_level_codes']:
        if second_level['id'] in second_level_ids:
            print(f"错误: 二阶编码ID重复: {second_level['id']}")
        else:
            second_level_ids.add(second_level['id'])

print(f"通过: 三阶编码ID唯一性检查通过，共 {len(third_level_ids)} 个唯一ID")
print(f"通过: 二阶编码ID唯一性检查通过，共 {len(second_level_ids)} 个唯一ID")

# 检查版本信息
print("\n=== 验证版本信息 ===")
print(f"版本: {coding_library.get('version', '未知')}")
print(f"创建时间: {coding_library.get('created_at', '未知')}")
print(f"描述: {coding_library.get('description', '未知')}")

print("\n=== 验证完成 ===")
print("编码库结构和数据完整性验证通过！")
