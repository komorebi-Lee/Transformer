"""
诊断一阶编码包含说话人名称的问题
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
print('诊断一阶编码包含说话人名称问题')
print('=' * 80)

# 测试文件
test_file = r'C:\Users\33288\Downloads\新文本\润色后文件\陶阳里 非遗手艺人11.docx'

# 初始化
model_manager = EnhancedModelManager()
data_processor = DataProcessor()
numbering_manager = TextNumberingManager()
coding_generator = EnhancedCodingGenerator()
grounded_coder = GroundedTheoryCoder()

print('\n[1] 读取原始文件')
print('-' * 80)
content = data_processor.read_file(test_file)

# 检查是否有说话人名称模式
speaker_patterns = [
    r'里弄管家\d+[：:]',
    r'受访者\d*[：:]',
    r'采访者\d*[：:]',
    r'[A-Z]\d*[：:]',
    r'\w+\d+[：:]',
]

print('检查原始文本中的说话人标记:')
for pattern in speaker_patterns:
    matches = re.findall(pattern, content)
    if matches:
        unique_matches = list(set(matches))
        print(f'  模式 {pattern}: 找到 {len(unique_matches)} 个')
        for match in unique_matches[:5]:
            print(f'    - {match}')

print('\n[2] 处理文件')
print('-' * 80)
numbered_content, number_mapping = numbering_manager.number_text(content, 'test.docx')
number_mappings = {'陶阳里 非遗手艺人11.docx': number_mapping}
processed_data = data_processor.process_multiple_files([test_file], number_mappings=number_mappings)

# 检查提取的句子是否包含说话人名称
file_sentence_mapping = processed_data['file_sentence_mapping']
for filename, data in file_sentence_mapping.items():
    sentences = data['sentences']
    
    print(f'\n检查提取的句子:')
    problem_sentences = []
    for sent in sentences:
        content = sent.get('content', '')
        # 检查是否包含说话人标记
        for pattern in speaker_patterns:
            if re.search(pattern, content):
                problem_sentences.append({
                    'content': content[:80],
                    'pattern': pattern,
                    'text_number': sent.get('text_number')
                })
                break
    
    if problem_sentences:
        print(f'  ❌ 发现 {len(problem_sentences)} 个包含说话人标记的句子:')
        for i, prob in enumerate(problem_sentences[:5]):
            print(f'\n  {i+1}. 编号 {prob["text_number"]}:')
            print(f'     内容: {prob["content"]}...')
            print(f'     匹配: {prob["pattern"]}')
    else:
        print(f'  ✅ 没有包含说话人标记的句子')

print('\n[3] 生成编码')
print('-' * 80)
raw_codes = coding_generator.generate_grounded_theory_codes_multi_files(processed_data, model_manager)

print('\n[4] 检查一阶编码')
print('-' * 80)
structured_codes = grounded_coder.build_coding_structure(raw_codes)

# 检查一阶编码是否包含说话人名称
problem_codes = []
for third_cat, second_cats in structured_codes.items():
    for second_cat, first_contents in second_cats.items():
        for first_content in first_contents:
            code_id = first_content.get('code_id')
            content = first_content.get('content', '')
            
            # 检查是否包含说话人标记
            for pattern in speaker_patterns:
                if re.search(pattern, content):
                    problem_codes.append({
                        'code_id': code_id,
                        'content': content[:80],
                        'pattern': pattern
                    })
                    break

if problem_codes:
    print(f'❌ 发现 {len(problem_codes)} 个包含说话人标记的一阶编码:')
    for i, prob in enumerate(problem_codes[:10]):
        print(f'\n{i+1}. {prob["code_id"]}:')
        print(f'   内容: {prob["content"]}...')
        print(f'   匹配: {prob["pattern"]}')
else:
    print(f'✅ 没有包含说话人标记的一阶编码')

print('\n[5] 总结')
print('-' * 80)
print(f'问题句子数: {len(problem_sentences)}')
print(f'问题编码数: {len(problem_codes)}')

if problem_sentences or problem_codes:
    print('\n需要修复:')
    print('  1. 在 extract_respondent_sentences 中清理说话人标记')
    print('  2. 改进一阶编码生成质量')
else:
    print('\n✅ 没有发现问题')

print('\n' + '=' * 80)
print('诊断完成')
print('=' * 80)
