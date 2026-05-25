"""
测试 TextNumbering 编号是否正确关联
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from data_processor import DataProcessor
from fully_compatible_coding_adapter import FullyCompatibleCodingAdapter
from optimized_coding_pipeline import OptimizedCodingPipeline
from model_manager import EnhancedModelManager
from grounded_theory_coder import GroundedTheoryCoder
from text_numbering import TextNumberingManager

print('=' * 80)
print('测试 TextNumbering 编号关联')
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
print(f'文件内容长度: {len(content)} 字符')

# 编号
numbered_content, number_mapping = numbering_manager.number_text(content, 'test.docx')
print(f'编号后内容长度: {len(numbered_content)} 字符')
print(f'编号映射数量: {len(number_mapping)} 个')

# 显示前3个编号
print(f'\n前3个编号:')
for i in range(1, min(4, len(number_mapping) + 1)):
    if i in number_mapping:
        text = number_mapping[i]
        print(f'  [{i}]: {text[:50]}...' if len(text) > 50 else f'  [{i}]: {text}')

print('\n[2] 处理文件（传递编号映射）')
print('-' * 80)

# 构建编号映射字典
number_mappings = {
    '陶阳里 非遗手艺人11.docx': number_mapping
}

processed_data = data_processor.process_multiple_files(
    [test_file],
    number_mappings=number_mappings  # ← 传递编号映射
)

file_sentence_mapping = processed_data['file_sentence_mapping']
for filename, data in file_sentence_mapping.items():
    sentences = data['sentences']
    print(f'文件: {filename}')
    print(f'提取句子数: {len(sentences)}')
    
    # 检查前3个句子是否有编号
    print(f'\n前3个句子的编号信息:')
    for i, sent in enumerate(sentences[:3]):
        print(f'\n  句子 {i+1}:')
        print(f'    content: {sent.get("content", "")[:50]}...')
        print(f'    text_number: {sent.get("text_number")}')  # ← 检查编号
        print(f'    numbered_sentence: {sent.get("numbered_sentence", "")[:60]}...')  # ← 检查带编号的句子
        
        if sent.get('text_number'):
            print(f'    ✅ 有编号')
        else:
            print(f'    ❌ 无编号')

print('\n[3] 生成编码')
print('-' * 80)

optimized_pipeline = OptimizedCodingPipeline(model_manager=model_manager, use_qa_classifier=True)
adapter = FullyCompatibleCodingAdapter(optimized_pipeline)

raw_codes = adapter.generate_grounded_theory_codes_multi_files(
    processed_data,
    model_manager
)

print(f'一阶编码数量: {len(raw_codes["一阶编码"])}')

# 检查第一个编码的 sentence_details
if raw_codes['一阶编码']:
    first_key = list(raw_codes['一阶编码'].keys())[0]
    first_value = raw_codes['一阶编码'][first_key]
    
    print(f'\n第一个编码 ({first_key}):')
    print(f'  编码内容: {first_value[0][:50]}...')
    
    if first_value[4]:  # sentence_details
        detail = first_value[4][0]
        print(f'\n  sentence_details[0]:')
        print(f'    content: {detail.get("content", "")[:50]}...')
        print(f'    text_number: {detail.get("text_number")}')  # ← 检查编号
        print(f'    numbered_sentence: {detail.get("numbered_sentence", "")[:60]}...')  # ← 检查带编号的句子
        
        if detail.get('text_number'):
            print(f'    ✅ 编号已传递')
        else:
            print(f'    ❌ 编号未传递')

print('\n[4] 构建编码结构')
print('-' * 80)

grounded_coder = GroundedTheoryCoder()
structured_codes = grounded_coder.build_coding_structure(raw_codes)

print(f'三阶编码数量: {len(structured_codes)}')

if structured_codes:
    first_third = list(structured_codes.keys())[0]
    second_cats = structured_codes[first_third]
    if second_cats:
        first_second = list(second_cats.keys())[0]
        first_contents = second_cats[first_second]
        if first_contents:
            first_content = first_contents[0]
            
            print(f'\n第一个一阶编码:')
            print(f'  numbered_content: {first_content.get("numbered_content", "")[:50]}...')
            
            if first_content.get('sentence_details'):
                detail = first_content['sentence_details'][0]
                print(f'\n  sentence_details[0]:')
                print(f'    content: {detail.get("content", "")[:50]}...')
                print(f'    text_number: {detail.get("text_number")}')  # ← 检查编号
                print(f'    numbered_sentence: {detail.get("numbered_sentence", "")[:60]}...')  # ← 检查带编号的句子
                
                if detail.get('text_number'):
                    print(f'    ✅ 编号保持完整')
                else:
                    print(f'    ❌ 编号丢失')

print('\n' + '=' * 80)
print('测试完成')
print('=' * 80)
