"""
查找包含"里弄管家"的编码
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from data_processor import DataProcessor
from enhanced_coding_generator import EnhancedCodingGenerator
from model_manager import EnhancedModelManager
from grounded_theory_coder import GroundedTheoryCoder
from text_numbering import TextNumberingManager

print('=' * 80)
print('查找包含"里弄管家"的编码')
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

print('\n[2] 生成编码')
raw_codes = coding_generator.generate_grounded_theory_codes_multi_files(processed_data, model_manager)

print('\n[3] 构建编码结构')
structured_codes = grounded_coder.build_coding_structure(raw_codes)

print('\n[4] 查找包含"里弄管家"的编码')
print('-' * 80)

found_codes = []
for third_cat, second_cats in structured_codes.items():
    for second_cat, first_contents in second_cats.items():
        for first_content in first_contents:
            code_id = first_content.get('code_id')
            content = first_content.get('content', '')
            
            if '里弄管家' in content or '里弄' in content:
                sentence_details = first_content.get('sentence_details', [])
                found_codes.append({
                    'code_id': code_id,
                    'content': content,
                    'sentence_count': len(sentence_details),
                    'sentences': sentence_details
                })

if found_codes:
    print(f'找到 {len(found_codes)} 个包含"里弄管家"的编码:')
    for i, code in enumerate(found_codes):
        print(f'\n{i+1}. {code["code_id"]}:')
        print(f'   编码内容: {code["content"]}')
        print(f'   句子数: {code["sentence_count"]}')
        
        for j, sent in enumerate(code['sentences'][:3]):
            print(f'\n   句子 {j+1}:')
            print(f'     content: {sent.get("content", "")[:100]}...')
            print(f'     text_number: {sent.get("text_number")}')
            print(f'     speaker: {sent.get("speaker")}')
else:
    print('没有找到包含"里弄管家"的编码')

# 查找 A75
print('\n[5] 查找 A75 编码')
print('-' * 80)
for third_cat, second_cats in structured_codes.items():
    for second_cat, first_contents in second_cats.items():
        for first_content in first_contents:
            if first_content.get('code_id') == 'A75':
                print(f'找到 A75:')
                print(f'  编码内容: {first_content.get("content")}')
                
                sentence_details = first_content.get('sentence_details', [])
                print(f'  句子数: {len(sentence_details)}')
                
                for j, sent in enumerate(sentence_details[:3]):
                    print(f'\n  句子 {j+1}:')
                    print(f'    content: {sent.get("content", "")}')
                    print(f'    text_number: {sent.get("text_number")}')

print('\n' + '=' * 80)
print('查找完成')
print('=' * 80)
