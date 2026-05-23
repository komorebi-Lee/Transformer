"""
测试一阶编码质量
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from data_processor import DataProcessor
from enhanced_coding_generator import EnhancedCodingGenerator
from model_manager import EnhancedModelManager
from text_numbering import TextNumberingManager
import os
import glob

print('=' * 80)
print('测试一阶编码质量')
print('=' * 80)

# 测试目录
test_dir = r'C:\Users\33288\Downloads\新文本\1'

# 获取所有文件
files = glob.glob(os.path.join(test_dir, '*.docx'))
print(f'\n找到 {len(files)} 个文件')

# 只测试第一个文件
test_file = files[0]
print(f'测试文件: {os.path.basename(test_file)}')

# 初始化
model_manager = EnhancedModelManager()
data_processor = DataProcessor()
numbering_manager = TextNumberingManager()
coding_generator = EnhancedCodingGenerator()

print('\n[1] 处理文件')
content = data_processor.read_file(test_file)
print(f'文件长度: {len(content)} 字符')

numbered_content, number_mapping = numbering_manager.number_text(content, os.path.basename(test_file))
number_mappings = {os.path.basename(test_file): number_mapping}

processed_data = data_processor.process_multiple_files([test_file], number_mappings=number_mappings)
print(f'提取句子数: {processed_data["total_sentences"]}')

print('\n[2] 生成一阶编码')
print('-' * 80)

raw_codes = coding_generator.generate_grounded_theory_codes_multi_files(processed_data, model_manager)

# 检查一阶编码的结构
first_codes_data = raw_codes.get("一阶编码", [])
print(f'一阶编码类型: {type(first_codes_data)}')

# 转换为列表
if isinstance(first_codes_data, dict):
    first_codes = list(first_codes_data.values())
elif isinstance(first_codes_data, list):
    first_codes = first_codes_data
else:
    first_codes = []

print(f'一阶编码总数: {len(first_codes)}')

# 分析前5个一阶编码的质量
print('\n[3] 分析一阶编码质量（前5个）')
print('-' * 80)

for i, code_data in enumerate(first_codes[:5]):
    # 获取编码内容
    if isinstance(code_data, dict):
        code = code_data.get('content', '') or code_data.get('code', '') or str(code_data)
    else:
        code = str(code_data)
    
    print(f'\n编码 {i+1}:')
    print(f'  内容: {code[:100]}...')
    
    # 检查质量问题
    issues = []
    
    # 1. 检查长度
    if len(code) < 10:
        issues.append('太短')
    elif len(code) > 200:
        issues.append('太长')
    
    # 2. 检查特殊符号
    special_chars = ['●', '○', '◆', '◇', '■', '□', '▲', '△']
    for char in special_chars:
        if char in code:
            issues.append(f'包含特殊符号: {char}')
            break
    
    # 3. 检查说话人标记
    speaker_marks = ['受访者：', '采访者：', '问：', '答：']
    for mark in speaker_marks:
        if mark in code:
            issues.append(f'包含说话人标记: {mark}')
            break
    
    # 4. 检查编号标记
    import re
    if re.search(r'\[A\d+\]', code):
        issues.append('包含编号标记')
    
    # 5. 检查是否包含时间戳
    if re.search(r'\d{2}:\d{2}', code):
        issues.append('包含时间戳')
    
    if issues:
        print(f'  ⚠️ 质量问题: {", ".join(issues)}')
    else:
        print(f'  ✅ 质量良好')

print('\n' + '=' * 80)
print('测试完成')
print('=' * 80)
