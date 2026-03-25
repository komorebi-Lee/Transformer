import json
import os
from enhanced_coding_generator import EnhancedCodingGenerator
from model_manager import EnhancedModelManager

# 创建编码生成器实例
coding_generator = EnhancedCodingGenerator()

# 创建模型管理器实例
model_manager = EnhancedModelManager()

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

print("开始测试编码结果一致性...")
print("-" * 60)

# 生成离线编码结果
print("生成离线编码结果...")
offline_codes = coding_generator.generate_codes_with_rules(processed_data)
print(f"离线编码结果: 一阶编码 {len(offline_codes.get('一阶编码', {}))} 个, 二阶编码 {len(offline_codes.get('二阶编码', {}))} 个, 三阶编码 {len(offline_codes.get('三阶编码', {}))} 个")

# 生成训练模型编码结果
print("\n生成训练模型编码结果...")
if model_manager.is_trained_model_available():
    model_codes = coding_generator.generate_codes_with_trained_model(processed_data, model_manager)
    print(f"训练模型编码结果: 一阶编码 {len(model_codes.get('一阶编码', {}))} 个, 二阶编码 {len(model_codes.get('二阶编码', {}))} 个, 三阶编码 {len(model_codes.get('三阶编码', {}))} 个")
else:
    print("警告: 训练模型不可用，跳过训练模型编码测试")
    model_codes = None

print("-" * 60)

# 计算编码结果相似度
if model_codes:
    print("计算编码结果相似度...")
    
    # 提取一阶编码内容
    offline_first_level = set(offline_codes.get('一阶编码', {}).values())
    model_first_level = set(model_codes.get('一阶编码', {}).values())
    
    # 计算一阶编码相似度
    if offline_first_level and model_first_level:
        intersection = offline_first_level & model_first_level
        union = offline_first_level | model_first_level
        similarity = len(intersection) / len(union) if union else 0
        print(f"一阶编码相似度: {similarity:.4f}")
    else:
        print("无法计算一阶编码相似度: 编码结果为空")
    
    # 提取二阶编码类别
    offline_second_level = set(offline_codes.get('二阶编码', {}).keys())
    model_second_level = set(model_codes.get('二阶编码', {}).keys())
    
    # 计算二阶编码相似度
    if offline_second_level and model_second_level:
        intersection = offline_second_level & model_second_level
        union = offline_second_level | model_second_level
        similarity = len(intersection) / len(union) if union else 0
        print(f"二阶编码相似度: {similarity:.4f}")
    else:
        print("无法计算二阶编码相似度: 编码结果为空")
    
    # 提取三阶编码类别
    offline_third_level = set(offline_codes.get('三阶编码', {}).keys())
    model_third_level = set(model_codes.get('三阶编码', {}).keys())
    
    # 计算三阶编码相似度
    if offline_third_level and model_third_level:
        intersection = offline_third_level & model_third_level
        union = offline_third_level | model_third_level
        similarity = len(intersection) / len(union) if union else 0
        print(f"三阶编码相似度: {similarity:.4f}")
    else:
        print("无法计算三阶编码相似度: 编码结果为空")
else:
    print("无法计算编码结果相似度: 训练模型不可用")

print("-" * 60)
print("测试完成!")
