"""
诊断定位错误问题
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from data_processor import DataProcessor
from enhanced_coding_generator import EnhancedCodingGenerator
from model_manager import EnhancedModelManager
from grounded_theory_coder import GroundedTheoryCoder
from text_numbering import TextNumberingManager
import json

print('=' * 80)
print('诊断定位错误问题')
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
print(f'编号映射数量: {len(number_mapping)}')
print(f'内容长度: {len(content)} 字符')
print(f'编号后内容长度: {len(numbered_content)} 字符')

print('\n[2] 处理文件')
print('-' * 80)
number_mappings = {'陶阳里 非遗手艺人11.docx': number_mapping}
processed_data = data_processor.process_multiple_files([test_file], number_mappings=number_mappings)
print(f'提取句子数: {processed_data["total_sentences"]}')

print('\n[3] 生成编码')
print('-' * 80)
raw_codes = coding_generator.generate_grounded_theory_codes_multi_files(processed_data, model_manager)
print(f'一阶编码数量: {len(raw_codes["一阶编码"])}')

print('\n[4] 构建编码结构')
print('-' * 80)
structured_codes = grounded_coder.build_coding_structure(raw_codes)

# 统计所有编码的 text_number
all_text_numbers = []
for third_cat, second_cats in structured_codes.items():
    for second_cat, first_contents in second_cats.items():
        for first_content in first_contents:
            code_id = first_content.get('code_id')
            sentence_details = first_content.get('sentence_details', [])
            
            for detail in sentence_details:
                text_number = detail.get('text_number')
                all_text_numbers.append({
                    'code_id': code_id,
                    'text_number': text_number,
                    'content': detail.get('content', '')[:50]
                })

print(f'总编码数: {len(all_text_numbers)}')

# 检查 text_number 的分布
none_count = sum(1 for item in all_text_numbers if item['text_number'] is None)
print(f'text_number 为 None: {none_count} 个')

if none_count > 0:
    print(f'\n前10个 text_number 为 None 的编码:')
    none_items = [item for item in all_text_numbers if item['text_number'] is None]
    for i, item in enumerate(none_items[:10]):
        print(f'  {i+1}. {item["code_id"]}: {item["content"]}...')

# 检查 text_number 的范围
valid_numbers = [item['text_number'] for item in all_text_numbers if item['text_number'] is not None]
if valid_numbers:
    print(f'\ntext_number 范围: {min(valid_numbers)} - {max(valid_numbers)}')
    print(f'number_mapping 范围: {min(number_mapping.keys())} - {max(number_mapping.keys())}')
    
    # 检查是否有超出范围的编号
    out_of_range = [n for n in valid_numbers if n not in number_mapping]
    if out_of_range:
        print(f'\n❌ 发现 {len(out_of_range)} 个超出范围的编号:')
        print(f'   {out_of_range[:10]}...')
    else:
        print(f'\n✅ 所有编号都在有效范围内')

print('\n[5] 检查定位数据完整性')
print('-' * 80)

# 随机检查几个编码的定位数据
import random
sample_codes = random.sample(all_text_numbers, min(10, len(all_text_numbers)))

print(f'随机抽样 {len(sample_codes)} 个编码:')
for i, item in enumerate(sample_codes):
    code_id = item['code_id']
    text_number = item['text_number']
    content = item['content']
    
    print(f'\n{i+1}. {code_id}:')
    print(f'   text_number: {text_number}')
    print(f'   content: {content}...')
    
    if text_number and text_number in number_mapping:
        mapped_text = number_mapping[text_number]
        print(f'   mapped_text: {mapped_text[:50]}...')
        
        # 检查是否匹配
        if content in mapped_text or mapped_text in content:
            print(f'   ✅ 匹配')
        else:
            print(f'   ❌ 不匹配')
    else:
        print(f'   ❌ 编号无效或不存在')

print('\n[6] 保存诊断结果')
print('-' * 80)

# 保存所有编码的定位信息
location_data = []
for item in all_text_numbers:
    location_data.append({
        'code_id': item['code_id'],
        'text_number': item['text_number'],
        'content': item['content'],
        'has_valid_number': item['text_number'] is not None and item['text_number'] in number_mapping
    })

with open(r'd:\zthree2\location_diagnosis.json', 'w', encoding='utf-8') as f:
    json.dump(location_data, f, ensure_ascii=False, indent=2)

print('✅ 已保存到 location_diagnosis.json')

print('\n[7] 总结')
print('-' * 80)
print(f'总编码数: {len(all_text_numbers)}')
print(f'有效编号: {len(valid_numbers)} ({len(valid_numbers)/len(all_text_numbers)*100:.1f}%)')
print(f'无效编号: {none_count} ({none_count/len(all_text_numbers)*100:.1f}%)')

if none_count == 0 and len(out_of_range) == 0:
    print('\n✅ 所有编码都有有效的定位编号')
else:
    print('\n❌ 存在定位问题，需要修复')

print('\n' + '=' * 80)
print('诊断完成')
print('=' * 80)
