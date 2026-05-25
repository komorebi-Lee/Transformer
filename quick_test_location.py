"""
快速测试定位修复
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from data_processor import DataProcessor
from enhanced_coding_generator import EnhancedCodingGenerator
from model_manager import EnhancedModelManager
from grounded_theory_coder import GroundedTheoryCoder
from text_numbering import TextNumberingManager

print('=' * 80)
print('快速测试定位修复')
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

print('\n[4] 检查前5个编码')
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
                marked_content = detail.get('marked_content', '')
                text_number = detail.get('text_number')
                
                print(f'\n{code_id}:')
                print(f'  content: {content[:60]}...')
                print(f'  marked_content: {marked_content[:60]}...')
                print(f'  text_number: {text_number}')
                
                # 检查 content 是否包含 [Axxx]
                if '[A' in content:
                    print(f'  ❌ content 包含编码ID')
                else:
                    print(f'  ✅ content 干净')
                
                # 检查是否有 marked_content
                if marked_content:
                    print(f'  ✅ 有 marked_content')
                else:
                    print(f'  ❌ 无 marked_content')
                
                count += 1
        if count >= 5:
            break
    if count >= 5:
        break

print('\n' + '=' * 80)
print('测试完成')
print('=' * 80)
