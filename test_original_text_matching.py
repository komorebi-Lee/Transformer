"""
测试使用原始文本匹配的效果
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from data_processor import DataProcessor
from enhanced_coding_generator import EnhancedCodingGenerator
from model_manager import EnhancedModelManager
from grounded_theory_coder import GroundedTheoryCoder
from text_numbering import TextNumberingManager

print('=' * 80)
print('测试使用原始文本匹配的效果')
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

# 检查前10个句子的匹配情况
file_sentence_mapping = processed_data['file_sentence_mapping']
for filename, data in file_sentence_mapping.items():
    sentences = data['sentences']
    
    print(f'\n前10个句子的匹配情况:')
    matched_count = 0
    unmatched_count = 0
    
    for i, sent in enumerate(sentences[:10]):
        content_text = sent.get('content', '')
        original_content = sent.get('original_content', '')
        text_number = sent.get('text_number')
        
        print(f'\n{i+1}. 编号 {text_number}:')
        print(f'   content: {content_text[:60]}...')
        print(f'   original: {original_content[:60]}...')
        
        if text_number:
            matched_count += 1
            print(f'   ✅ 匹配成功')
            
            # 验证匹配是否正确
            if text_number in number_mapping:
                mapped_text = number_mapping[text_number]
                if original_content in mapped_text or mapped_text in original_content:
                    print(f'   ✅ 验证正确')
                else:
                    print(f'   ❌ 验证失败')
                    print(f'   mapped: {mapped_text[:60]}...')
        else:
            unmatched_count += 1
            print(f'   ❌ 未匹配')
    
    print(f'\n匹配统计（前10个）:')
    print(f'  匹配成功: {matched_count}')
    print(f'  未匹配: {unmatched_count}')
    print(f'  匹配率: {matched_count/10*100:.1f}%')

print('\n[2] 生成编码')
raw_codes = coding_generator.generate_grounded_theory_codes_multi_files(processed_data, model_manager)
print(f'一阶编码数量: {len(raw_codes["一阶编码"])}')

print('\n[3] 构建编码结构')
structured_codes = grounded_coder.build_coding_structure(raw_codes)

# 统计所有编码的匹配情况
total_codes = 0
matched_codes = 0
unmatched_codes = 0

for third_cat, second_cats in structured_codes.items():
    for second_cat, first_contents in second_cats.items():
        for first_content in first_contents:
            total_codes += 1
            sentence_details = first_content.get('sentence_details', [])
            
            for detail in sentence_details:
                if detail.get('text_number'):
                    matched_codes += 1
                else:
                    unmatched_codes += 1

print(f'\n编码匹配统计:')
print(f'  总编码数: {total_codes}')
print(f'  匹配成功: {matched_codes}')
print(f'  未匹配: {unmatched_codes}')
if total_codes > 0:
    print(f'  匹配率: {matched_codes/total_codes*100:.1f}%')

print('\n' + '=' * 80)
print('测试完成')
print('=' * 80)
