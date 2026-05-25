"""
诊断定位+高亮+关联编号错误
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from data_processor import DataProcessor
from enhanced_coding_generator import EnhancedCodingGenerator
from model_manager import EnhancedModelManager
from grounded_theory_coder import GroundedTheoryCoder
from text_numbering import TextNumberingManager

print('=' * 80)
print('诊断定位+高亮+关联编号错误')
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

print('\n[4] 查找包含"今天就调到明"或"辩明"的编码')
print('-' * 80)

target_texts = ['今天就调到明', '辩明', '学术资料']

for third_cat, second_cats in structured_codes.items():
    for second_cat, first_contents in second_cats.items():
        for first_content in first_contents:
            code_id = first_content.get('code_id')
            content_text = first_content.get('content', '')
            
            # 检查是否包含目标文本
            if any(text in content_text for text in target_texts):
                print(f'\n找到 {code_id}:')
                print(f'  编码内容: {content_text}')
                
                sentence_details = first_content.get('sentence_details', [])
                print(f'  句子数: {len(sentence_details)}')
                
                for j, sent in enumerate(sentence_details):
                    sent_content = sent.get('content', '')
                    text_number = sent.get('text_number')
                    numbered_sentence = sent.get('numbered_sentence', '')
                    
                    print(f'\n  句子 {j+1}:')
                    print(f'    content: {sent_content}')
                    print(f'    text_number: {text_number}')
                    print(f'    numbered_sentence: {numbered_sentence}')
                    
                    # 检查 text_number 是否正确
                    if text_number and text_number in number_mapping:
                        mapped_text = number_mapping[text_number]
                        print(f'    mapped_text: {mapped_text}')
                        
                        # 检查匹配
                        if sent_content in mapped_text:
                            print(f'    ✅ content 在 mapped_text 中')
                        elif mapped_text in sent_content:
                            print(f'    ⚠️ mapped_text 在 content 中（反向匹配）')
                        else:
                            print(f'    ❌ 不匹配')
                            
                            # 查找正确的编号
                            print(f'\n    尝试查找正确的编号:')
                            found = False
                            for num, text in number_mapping.items():
                                if sent_content in text or text in sent_content:
                                    print(f'      可能的编号: {num}')
                                    print(f'      文本: {text}')
                                    found = True
                                    if found:
                                        break
                            
                            if not found:
                                print(f'      ❌ 未找到匹配的编号')
                    else:
                        print(f'    ❌ text_number 无效或不存在')

print('\n[5] 检查 _find_text_number 方法的匹配逻辑')
print('-' * 80)
print('当前匹配逻辑可能的问题:')
print('  1. 使用 "in" 操作符匹配，可能匹配到错误的编号')
print('  2. 没有考虑文本相似度')
print('  3. 没有优先匹配最相似的编号')

print('\n' + '=' * 80)
print('诊断完成')
print('=' * 80)
