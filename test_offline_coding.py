from enhanced_coding_generator import EnhancedCodingGenerator

# 创建编码生成器实例
coding_generator = EnhancedCodingGenerator()

# 测试文本数据
test_texts = [
    "我们团队最近在开发一个新的项目，需要协调多个部门的工作。",
    "公司的质量管理体系需要进一步优化，以提高产品质量。",
    "技术创新是企业发展的核心动力，我们需要不断探索新的技术方案。",
    "面对市场的挑战，我们需要制定更加灵活的应对策略。",
    "团队成员之间的沟通和协作对于项目的成功至关重要。"
]

# 准备测试数据结构
processed_data = {
    'combined_text': ' '.join(test_texts),
    'file_sentence_mapping': {
        'test_file.txt': {
            'sentences': [
                {'content': text, 'speaker': 'respondent'} for text in test_texts
            ]
        }
    }
}

print("开始测试离线编码功能...")
print("-" * 60)

# 生成离线编码结果
print("生成离线编码结果...")
offline_codes = coding_generator.generate_codes_with_rules(processed_data)

print(f"离线编码结果: ")
print(f"  一阶编码: {len(offline_codes.get('一阶编码', {}))} 个")
print(f"  二阶编码: {len(offline_codes.get('二阶编码', {}))} 个")
print(f"  三阶编码: {len(offline_codes.get('三阶编码', {}))} 个")

print("\n一阶编码内容:")
for code_key, code_info in offline_codes.get('一阶编码', {}).items():
    if isinstance(code_info, list) and len(code_info) > 0:
        print(f"  {code_key}: {code_info[0]}")

print("\n二阶编码分类:")
for category, codes in offline_codes.get('二阶编码', {}).items():
    print(f"  {category}: {len(codes)} 个一阶编码")

print("\n三阶编码分类:")
for category, second_level in offline_codes.get('三阶编码', {}).items():
    print(f"  {category}: {len(second_level)} 个二阶编码")

print("-" * 60)
print("测试完成!")
