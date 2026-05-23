"""
测试完全兼容的优化流水线
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from data_processor import DataProcessor
from fully_compatible_coding_adapter import FullyCompatibleCodingAdapter
from optimized_coding_pipeline import OptimizedCodingPipeline
from model_manager import EnhancedModelManager
from grounded_theory_coder import GroundedTheoryCoder
from text_numbering import TextNumberingManager
import json

print('=' * 80)
print('测试完全兼容的优化流水线')
print('=' * 80)

# 测试文件
test_file = r'C:\Users\33288\Downloads\新文本\润色后文件\陶阳里 非遗手艺人11.docx'

# 初始化
model_manager = EnhancedModelManager()
data_processor = DataProcessor()
numbering_manager = TextNumberingManager()

print('\n[1] 读取文件并编号')
print('-' * 80)
content = data_processor.read_file(test_file)
numbered_content, number_mapping = numbering_manager.number_text(content, 'test.docx')
print(f'编号映射数量: {len(number_mapping)}')

print('\n[2] 处理文件（传递编号映射）')
print('-' * 80)
number_mappings = {'陶阳里 非遗手艺人11.docx': number_mapping}
processed_data = data_processor.process_multiple_files([test_file], number_mappings=number_mappings)
print(f'提取句子数: {processed_data["total_sentences"]}')

# 检查第一个句子
file_sentence_mapping = processed_data['file_sentence_mapping']
for filename, data in file_sentence_mapping.items():
    sentences = data['sentences']
    if sentences:
        sent = sentences[0]
        print(f'\n第一个句子:')
        print(f'  content: {sent.get("content", "")[:50]}...')
        print(f'  text_number: {sent.get("text_number")}')
        print(f'  numbered_sentence: {sent.get("numbered_sentence", "")[:60]}...')

print('\n[3] 使用优化流水线生成编码')
print('-' * 80)
optimized_pipeline = OptimizedCodingPipeline(model_manager=model_manager, use_qa_classifier=True)
adapter = FullyCompatibleCodingAdapter(optimized_pipeline)

raw_codes = adapter.generate_grounded_theory_codes_multi_files(processed_data, model_manager)

print(f'一阶编码数量: {len(raw_codes["一阶编码"])}')
print(f'二阶编码数量: {len(raw_codes["二阶编码"])}')
print(f'三阶编码数量: {len(raw_codes["三阶编码"])}')

# 检查编码键格式
if raw_codes['一阶编码']:
    first_key = list(raw_codes['一阶编码'].keys())[0]
    print(f'\n第一个编码键: {first_key}')
    print(f'  格式检查: {"✅ FL_xxxx 格式" if first_key.startswith("FL_") else "❌ 格式不对"}')
    
    first_value = raw_codes['一阶编码'][first_key]
    print(f'\n第一个编码结构:')
    print(f'  [0] abstracted: {first_value[0][:50]}...')
    print(f'  [1] source_sentences 长度: {len(first_value[1])}')
    print(f'  [2] file_count: {first_value[2]}')
    print(f'  [3] sentence_count: {first_value[3]}')
    print(f'  [4] sentence_details 长度: {len(first_value[4])}')
    
    if first_value[4]:
        detail = first_value[4][0]
        print(f'\n  sentence_details[0]:')
        print(f'    text_number: {detail.get("text_number")}')
        print(f'    numbered_sentence: {detail.get("numbered_sentence", "")[:60]}...')
        print(f'    sentence_id: {detail.get("sentence_id")}')
        print(f'    code_id: {detail.get("code_id")}')

# 检查二阶和三阶编码
print(f'\n二阶编码:')
for key, value in raw_codes['二阶编码'].items():
    print(f'  {key}: {len(value)} 个一阶编码')

print(f'\n三阶编码:')
for key, value in raw_codes['三阶编码'].items():
    print(f'  {key}: {value}')

print('\n[4] 构建编码结构')
print('-' * 80)
grounded_coder = GroundedTheoryCoder()
structured_codes = grounded_coder.build_coding_structure(raw_codes)

print(f'三阶编码数量: {len(structured_codes)}')
if structured_codes:
    first_third = list(structured_codes.keys())[0]
    print(f'第一个三阶编码: {first_third}')
    
    second_cats = structured_codes[first_third]
    if second_cats:
        first_second = list(second_cats.keys())[0]
        print(f'第一个二阶编码: {first_second}')
        
        first_contents = second_cats[first_second]
        print(f'一阶编码数量: {len(first_contents)}')
        
        if first_contents:
            first_content = first_contents[0]
            print(f'\n第一个一阶编码:')
            print(f'  code_id: {first_content.get("code_id")}')
            print(f'  格式检查: {"✅ Axx 格式" if first_content.get("code_id", "").startswith("A") else "❌ 格式不对"}')
            
            if first_content.get('sentence_details'):
                detail = first_content['sentence_details'][0]
                print(f'\n  sentence_details[0]:')
                print(f'    text_number: {detail.get("text_number")}')
                print(f'    numbered_sentence: {detail.get("numbered_sentence", "")[:60]}...')

print('\n[5] 保存测试结果')
print('-' * 80)

# 保存第一个编码
if raw_codes['一阶编码']:
    first_key = list(raw_codes['一阶编码'].keys())[0]
    first_value = raw_codes['一阶编码'][first_key]
    
    serializable = {
        'key': first_key,
        'abstracted': first_value[0],
        'source_sentences': first_value[1],
        'file_count': first_value[2],
        'sentence_count': first_value[3],
        'sentence_details': first_value[4]
    }
    
    with open(r'd:\zthree2\optimized_code_structure.json', 'w', encoding='utf-8') as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)
    
    print('✅ 已保存到 optimized_code_structure.json')

print('\n' + '=' * 80)
print('测试完成')
print('=' * 80)
