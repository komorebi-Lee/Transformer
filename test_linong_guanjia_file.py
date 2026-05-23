"""
测试"里弄管家"文件的自动编码
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
print('测试"里弄管家"文件的自动编码')
print('=' * 80)

# 测试文件
test_file = r'C:\Users\33288\Downloads\新文本\1\陶阳里 管理层3（里弄管家）.docx'

# 初始化
model_manager = EnhancedModelManager()
data_processor = DataProcessor()
numbering_manager = TextNumberingManager()
coding_generator = EnhancedCodingGenerator()
grounded_coder = GroundedTheoryCoder()

print('\n[1] 读取文件')
print('-' * 80)
content = data_processor.read_file(test_file)
print(f'文件长度: {len(content)} 字符')

# 显示前500字符
print(f'\n前500字符:')
print(content[:500])

# 检查说话人标记
print(f'\n检查说话人标记:')
speaker_patterns = [
    (r'里弄管家\d*[：:]', '里弄管家'),
    (r'受访者\d*[：:]', '受访者'),
    (r'采访者\d*[：:]', '采访者'),
]

for pattern, name in speaker_patterns:
    matches = re.findall(pattern, content)
    if matches:
        unique = list(set(matches))
        print(f'  {name}: {len(unique)} 种 - {unique[:5]}')

print('\n[2] 编号文本')
print('-' * 80)
numbered_content, number_mapping = numbering_manager.number_text(content, 'test.docx')
print(f'编号数量: {len(number_mapping)}')

print('\n[3] 处理文件')
print('-' * 80)
number_mappings = {'陶阳里 管理层3（里弄管家）.docx': number_mapping}
processed_data = data_processor.process_multiple_files([test_file], number_mappings=number_mappings)
print(f'提取句子数: {processed_data["total_sentences"]}')

# 检查提取的句子
file_sentence_mapping = processed_data['file_sentence_mapping']
for filename, data in file_sentence_mapping.items():
    sentences = data['sentences']
    
    print(f'\n前5个句子:')
    for i, sent in enumerate(sentences[:5]):
        content_text = sent.get('content', '')
        text_number = sent.get('text_number')
        print(f'\n  {i+1}. 编号 {text_number}:')
        print(f'     {content_text[:80]}...')
        
        # 检查是否包含说话人标记
        has_speaker = False
        for pattern, name in speaker_patterns:
            if re.search(pattern, content_text):
                print(f'     ❌ 包含 {name} 标记')
                has_speaker = True
                break
        if not has_speaker:
            print(f'     ✅ 无说话人标记')

print('\n[4] 生成编码')
print('-' * 80)
raw_codes = coding_generator.generate_grounded_theory_codes_multi_files(processed_data, model_manager)
print(f'一阶编码数量: {len(raw_codes["一阶编码"])}')

print('\n[5] 构建编码结构')
print('-' * 80)
structured_codes = grounded_coder.build_coding_structure(raw_codes)

# 查找前10个编码
print(f'\n前10个一阶编码:')
count = 0
for third_cat, second_cats in structured_codes.items():
    for second_cat, first_contents in second_cats.items():
        for first_content in first_contents:
            if count >= 10:
                break
            
            code_id = first_content.get('code_id')
            content_text = first_content.get('content', '')
            
            print(f'\n{count+1}. {code_id}: {content_text[:80]}...')
            
            # 检查是否包含说话人标记
            has_speaker = False
            for pattern, name in speaker_patterns:
                if re.search(pattern, content_text):
                    print(f'   ❌ 包含 {name} 标记')
                    has_speaker = True
                    break
            if not has_speaker:
                print(f'   ✅ 无说话人标记')
            
            count += 1
        if count >= 10:
            break
    if count >= 10:
        break

# 查找 A75
print(f'\n[6] 查找 A75 编码')
print('-' * 80)
found_a75 = False
for third_cat, second_cats in structured_codes.items():
    for second_cat, first_contents in second_cats.items():
        for first_content in first_contents:
            if first_content.get('code_id') == 'A75':
                found_a75 = True
                print(f'找到 A75:')
                print(f'  编码内容: {first_content.get("content")}')
                
                sentence_details = first_content.get('sentence_details', [])
                print(f'  句子数: {len(sentence_details)}')
                
                for j, sent in enumerate(sentence_details[:2]):
                    print(f'\n  句子 {j+1}:')
                    print(f'    content: {sent.get("content", "")[:100]}...')
                    print(f'    text_number: {sent.get("text_number")}')

if not found_a75:
    print('未找到 A75 编码')

print('\n' + '=' * 80)
print('测试完成')
print('=' * 80)
