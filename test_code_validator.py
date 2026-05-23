"""
测试编码验证和过滤功能
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from data_processor import DataProcessor
from enhanced_coding_generator import EnhancedCodingGenerator
from model_manager import EnhancedModelManager
from grounded_theory_coder import GroundedTheoryCoder
from text_numbering import TextNumberingManager
from code_validator import validate_and_filter_codes

print('=' * 80)
print('测试编码验证和过滤功能')
print('=' * 80)

# 测试文件
test_file = r'C:\Users\33288\Downloads\新文本\润色后文件\陶阳里 非遗手艺人11.docx'

# 初始化
model_manager = EnhancedModelManager()
data_processor = DataProcessor()
numbering_manager = TextNumberingManager()
coding_generator = EnhancedCodingGenerator()
grounded_coder = GroundedTheoryCoder()

print('\n[1] 处理文件')
content = data_processor.read_file(test_file)
numbered_content, number_mapping = numbering_manager.number_text(content, 'test.docx')
number_mappings = {'陶阳里 非遗手艺人11.docx': number_mapping}
processed_data = data_processor.process_multiple_files([test_file], number_mappings=number_mappings)

print(f'提取句子数: {processed_data["total_sentences"]}')
print(f'number_mapping 大小: {len(number_mapping)}')

print('\n[2] 生成编码')
raw_codes = coding_generator.generate_grounded_theory_codes_multi_files(processed_data, model_manager)
print(f'一阶编码数量: {len(raw_codes["一阶编码"])}')

print('\n[3] 构建编码结构')
structured_codes = grounded_coder.build_coding_structure(raw_codes)

# 统计验证前的数量
before_count = 0
for third_cat, second_cats in structured_codes.items():
    for second_cat, first_contents in second_cats.items():
        before_count += len(first_contents)

print(f'\n验证前统计:')
print(f'  一阶编码总数: {before_count}')

print('\n[4] 验证并过滤不匹配的编码')
print('-' * 80)
structured_codes = validate_and_filter_codes(structured_codes, number_mapping)

# 统计验证后的数量
after_count = 0
for third_cat, second_cats in structured_codes.items():
    for second_cat, first_contents in second_cats.items():
        after_count += len(first_contents)

print(f'\n验证后统计:')
print(f'  一阶编码总数: {after_count}')
print(f'  删除数量: {before_count - after_count}')
print(f'  保留率: {after_count/before_count*100:.1f}%')

print('\n[5] 检查前5个保留的编码')
print('-' * 80)
count = 0
for third_cat, second_cats in structured_codes.items():
    for second_cat, first_contents in second_cats.items():
        for first_content in first_contents:
            if count >= 5:
                break
            
            code_id = first_content.get('code_id')
            sentence_details = first_content.get('sentence_details', [])
            
            if sentence_details:
                detail = sentence_details[0]
                content = detail.get('content', '')
                sentence_id = detail.get('sentence_id', '')
                
                print(f'\n{code_id}:')
                print(f'  content: {content[:60]}...')
                print(f'  sentence_id: {sentence_id}')
                
                # 验证是否在 number_mapping 中
                if sentence_id and sentence_id.isdigit():
                    text_number = int(sentence_id)
                    if text_number in number_mapping:
                        mapped_text = number_mapping[text_number]
                        print(f'  mapped_text: {mapped_text[:60]}...')
                        print(f'  ✅ 匹配')
                    else:
                        print(f'  ❌ 不在 number_mapping 中')
            
            count += 1
        if count >= 5:
            break
    if count >= 5:
        break

print('\n' + '=' * 80)
print('测试完成')
print('=' * 80)
