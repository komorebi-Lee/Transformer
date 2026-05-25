"""
修复定位问题：清理 content 字段中的编码ID标记
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from data_processor import DataProcessor
from enhanced_coding_generator import EnhancedCodingGenerator
from model_manager import EnhancedModelManager
from grounded_theory_coder import GroundedTheoryCoder
from text_numbering import TextNumberingManager
import re

print('=' * 80)
print('修复定位问题')
print('=' * 80)

# 测试文件
test_file = r'C:\Users\33288\Downloads\新文本\润色后文件\陶阳里 非遗手艺人11.docx'

# 初始化
model_manager = EnhancedModelManager()
data_processor = DataProcessor()
numbering_manager = TextNumberingManager()
coding_generator = EnhancedCodingGenerator()
grounded_coder = GroundedTheoryCoder()

print('\n[1] 读取文件并编号')
print('-' * 80)
content = data_processor.read_file(test_file)
numbered_content, number_mapping = numbering_manager.number_text(content, 'test.docx')

print('\n[2] 处理文件')
print('-' * 80)
number_mappings = {'陶阳里 非遗手艺人11.docx': number_mapping}
processed_data = data_processor.process_multiple_files([test_file], number_mappings=number_mappings)

print('\n[3] 生成编码')
print('-' * 80)
raw_codes = coding_generator.generate_grounded_theory_codes_multi_files(processed_data, model_manager)

print('\n[4] 构建编码结构')
print('-' * 80)
structured_codes = grounded_coder.build_coding_structure(raw_codes)

print('\n[5] 检查并修复 content 字段')
print('-' * 80)

fixed_count = 0
mismatch_count = 0

for third_cat, second_cats in structured_codes.items():
    for second_cat, first_contents in second_cats.items():
        for first_content in first_contents:
            code_id = first_content.get('code_id')
            sentence_details = first_content.get('sentence_details', [])
            
            for detail in sentence_details:
                content = detail.get('content', '')
                text_number = detail.get('text_number')
                
                # 检查 content 是否包含编码ID标记
                if re.search(r'\[A\d+\]', content):
                    # 移除编码ID标记
                    clean_content = re.sub(r'\s*\[A\d+\]', '', content).strip()
                    detail['content'] = clean_content
                    fixed_count += 1
                    
                    # 重新匹配 text_number
                    if text_number and text_number in number_mapping:
                        mapped_text = number_mapping[text_number]
                        
                        # 检查是否匹配
                        if clean_content not in mapped_text and mapped_text not in clean_content:
                            mismatch_count += 1
                            print(f'\n❌ {code_id} 编号 {text_number} 不匹配:')
                            print(f'   content: {clean_content[:50]}...')
                            print(f'   mapped:  {mapped_text[:50]}...')

print(f'\n修复统计:')
print(f'  清理编码ID标记: {fixed_count} 个')
print(f'  编号不匹配: {mismatch_count} 个')

if mismatch_count > 0:
    print(f'\n需要重新匹配编号的编码数: {mismatch_count}')
else:
    print(f'\n✅ 所有编码的编号都匹配正确')

print('\n' + '=' * 80)
print('修复完成')
print('=' * 80)
