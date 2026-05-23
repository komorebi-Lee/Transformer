"""
测试文本编号重新匹配器
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from data_processor import DataProcessor
from enhanced_coding_generator import EnhancedCodingGenerator
from model_manager import EnhancedModelManager
from grounded_theory_coder import GroundedTheoryCoder
from text_numbering import TextNumberingManager
from text_number_rematcher import rematch_text_numbers_for_codes

print('=' * 80)
print('测试文本编号重新匹配器')
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

print('\n[2] 生成编码')
raw_codes = coding_generator.generate_grounded_theory_codes_multi_files(processed_data, model_manager)
print(f'一阶编码数量: {len(raw_codes["一阶编码"])}')

print('\n[3] 构建编码结构')
structured_codes = grounded_coder.build_coding_structure(raw_codes)

# 统计匹配前
before_matched = 0
total_sentences = 0
for third_cat, second_cats in structured_codes.items():
    for second_cat, first_contents in second_cats.items():
        for first_content in first_contents:
            for detail in first_content.get('sentence_details', []):
                total_sentences += 1
                if detail.get('text_number'):
                    before_matched += 1

print(f'\n匹配前统计:')
print(f'  总句子数: {total_sentences}')
print(f'  已匹配: {before_matched}')
print(f'  未匹配: {total_sentences - before_matched}')
print(f'  匹配率: {before_matched/total_sentences*100:.1f}%')

print('\n[4] 重新匹配 text_number')
print('-' * 80)
structured_codes = rematch_text_numbers_for_codes(structured_codes, number_mapping)

# 统计匹配后
after_matched = 0
for third_cat, second_cats in structured_codes.items():
    for second_cat, first_contents in second_cats.items():
        for first_content in first_contents:
            for detail in first_content.get('sentence_details', []):
                if detail.get('text_number'):
                    after_matched += 1

print(f'\n匹配后统计:')
print(f'  总句子数: {total_sentences}')
print(f'  已匹配: {after_matched}')
print(f'  未匹配: {total_sentences - after_matched}')
print(f'  匹配率: {after_matched/total_sentences*100:.1f}%')
print(f'  提升: +{after_matched - before_matched} ({(after_matched - before_matched)/total_sentences*100:.1f}%)')

print('\n[5] 检查前5个编码')
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
                print(f'\n{code_id}:')
                print(f'  content: {detail.get("content", "")[:60]}...')
                print(f'  text_number: {detail.get("text_number")}')
                
                if detail.get('text_number'):
                    print(f'  ✅ 已匹配')
                else:
                    print(f'  ❌ 未匹配')
            
            count += 1
        if count >= 5:
            break
    if count >= 5:
        break

print('\n' + '=' * 80)
print('测试完成')
print('=' * 80)
