"""
检查一阶编码的实际结构
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from data_processor import DataProcessor
from enhanced_coding_generator import EnhancedCodingGenerator
from model_manager import EnhancedModelManager
from text_numbering import TextNumberingManager
import os
import glob
import json

print('=' * 80)
print('检查一阶编码的实际结构')
print('=' * 80)

# 测试目录
test_dir = r'C:\Users\33288\Downloads\新文本\1'
files = glob.glob(os.path.join(test_dir, '*.docx'))
test_file = files[0]

# 初始化
model_manager = EnhancedModelManager()
data_processor = DataProcessor()
numbering_manager = TextNumberingManager()
coding_generator = EnhancedCodingGenerator()

# 处理文件
content = data_processor.read_file(test_file)
numbered_content, number_mapping = numbering_manager.number_text(content, os.path.basename(test_file))
number_mappings = {os.path.basename(test_file): number_mapping}
processed_data = data_processor.process_multiple_files([test_file], number_mappings=number_mappings)

print(f'提取句子数: {processed_data["total_sentences"]}')

# 生成编码
raw_codes = coding_generator.generate_grounded_theory_codes_multi_files(processed_data, model_manager)

print(f'\nraw_codes 的键: {list(raw_codes.keys())}')

first_codes_data = raw_codes.get("一阶编码", {})
print(f'\n一阶编码类型: {type(first_codes_data)}')
print(f'一阶编码数量: {len(first_codes_data)}')

# 查看第一个编码的结构
if isinstance(first_codes_data, dict):
    first_key = list(first_codes_data.keys())[0]
    first_value = first_codes_data[first_key]
    
    print(f'\n第一个编码的键: {first_key}')
    print(f'第一个编码的值类型: {type(first_value)}')
    print(f'第一个编码的值:')
    print(json.dumps(first_value, ensure_ascii=False, indent=2)[:500])

print('\n' + '=' * 80)
