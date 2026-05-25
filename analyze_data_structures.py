"""
全面分析自动编码和手动编码的数据结构
"""

import sys
sys.path.insert(0, r'D:\zthree2')

import json
from data_processor import DataProcessor
from enhanced_coding_generator import EnhancedCodingGenerator
from fully_compatible_coding_adapter import FullyCompatibleCodingAdapter
from optimized_coding_pipeline import OptimizedCodingPipeline
from model_manager import EnhancedModelManager
from grounded_theory_coder import GroundedTheoryCoder

print('=' * 80)
print('数据结构全面分析')
print('=' * 80)

# 测试文件
test_file = r'C:\Users\33288\Downloads\新文本\润色后文件\陶阳里 非遗手艺人11.docx'

# 初始化
model_manager = EnhancedModelManager()
data_processor = DataProcessor()

print('\n[1] data_processor.process_multiple_files() 返回结构')
print('-' * 80)
processed_data = data_processor.process_multiple_files([test_file])

print(f'返回键: {list(processed_data.keys())}')
print(f'total_files: {processed_data["total_files"]}')
print(f'total_sentences: {processed_data["total_sentences"]}')

file_sentence_mapping = processed_data['file_sentence_mapping']
for filename, data in file_sentence_mapping.items():
    print(f'\nfile_sentence_mapping["{filename}"]:')
    print(f'  键: {list(data.keys())}')
    print(f'  sentences 数量: {len(data["sentences"])}')
    
    if data['sentences']:
        sent = data['sentences'][0]
        print(f'\n  第一个 sentence 结构:')
        for key, value in sent.items():
            if isinstance(value, str) and len(value) > 50:
                print(f'    {key}: {value[:50]}...')
            else:
                print(f'    {key}: {value}')

print('\n' + '=' * 80)
print('[2] EnhancedCodingGenerator.generate_grounded_theory_codes_multi_files() 返回结构')
print('-' * 80)

# 使用原有的编码生成器
original_generator = EnhancedCodingGenerator()
original_codes = original_generator.generate_grounded_theory_codes_multi_files(
    processed_data,
    model_manager
)

print(f'返回键: {list(original_codes.keys())}')
print(f'一阶编码数量: {len(original_codes["一阶编码"])}')
print(f'二阶编码数量: {len(original_codes["二阶编码"])}')
print(f'三阶编码数量: {len(original_codes["三阶编码"])}')

if original_codes['一阶编码']:
    first_key = list(original_codes['一阶编码'].keys())[0]
    first_value = original_codes['一阶编码'][first_key]
    print(f'\n第一个一阶编码 ({first_key}):')
    print(f'  类型: {type(first_value)}')
    print(f'  长度: {len(first_value)}')
    print(f'  [0] abstracted: {first_value[0][:50] if isinstance(first_value[0], str) else first_value[0]}')
    print(f'  [1] source_sentences 类型: {type(first_value[1])}')
    print(f'  [1] source_sentences 长度: {len(first_value[1])}')
    
    if first_value[1]:
        source_sent = first_value[1][0]
        print(f'\n  source_sentences[0] 结构:')
        if isinstance(source_sent, dict):
            for key, value in source_sent.items():
                if isinstance(value, str) and len(value) > 50:
                    print(f'    {key}: {value[:50]}...')
                else:
                    print(f'    {key}: {value}')
        else:
            print(f'    类型: {type(source_sent)}')
            print(f'    值: {source_sent}')
    
    print(f'  [2] file_count: {first_value[2]}')
    print(f'  [3] sentence_count: {first_value[3]}')
    print(f'  [4] sentence_details 类型: {type(first_value[4])}')
    print(f'  [4] sentence_details 长度: {len(first_value[4])}')
    
    if first_value[4]:
        detail = first_value[4][0]
        print(f'\n  sentence_details[0] 结构:')
        if isinstance(detail, dict):
            for key, value in detail.items():
                if isinstance(value, str) and len(value) > 50:
                    print(f'    {key}: {value[:50]}...')
                else:
                    print(f'    {key}: {value}')

print('\n' + '=' * 80)
print('[3] FullyCompatibleCodingAdapter.generate_grounded_theory_codes_multi_files() 返回结构')
print('-' * 80)

# 使用新的适配器
optimized_pipeline = OptimizedCodingPipeline(model_manager=model_manager, use_qa_classifier=True)
adapter = FullyCompatibleCodingAdapter(optimized_pipeline)
adapter_codes = adapter.generate_grounded_theory_codes_multi_files(
    processed_data,
    model_manager
)

print(f'返回键: {list(adapter_codes.keys())}')
print(f'一阶编码数量: {len(adapter_codes["一阶编码"])}')
print(f'二阶编码数量: {len(adapter_codes["二阶编码"])}')
print(f'三阶编码数量: {len(adapter_codes["三阶编码"])}')

if adapter_codes['一阶编码']:
    first_key = list(adapter_codes['一阶编码'].keys())[0]
    first_value = adapter_codes['一阶编码'][first_key]
    print(f'\n第一个一阶编码 ({first_key}):')
    print(f'  类型: {type(first_value)}')
    print(f'  长度: {len(first_value)}')
    print(f'  [0] abstracted: {first_value[0][:50] if isinstance(first_value[0], str) else first_value[0]}')
    print(f'  [1] source_sentences 类型: {type(first_value[1])}')
    print(f'  [1] source_sentences 长度: {len(first_value[1])}')
    
    if first_value[1]:
        source_sent = first_value[1][0]
        print(f'\n  source_sentences[0] 结构:')
        if isinstance(source_sent, dict):
            for key, value in source_sent.items():
                if isinstance(value, str) and len(value) > 50:
                    print(f'    {key}: {value[:50]}...')
                else:
                    print(f'    {key}: {value}')
        else:
            print(f'    类型: {type(source_sent)}')
    
    print(f'  [2] file_count: {first_value[2]}')
    print(f'  [3] sentence_count: {first_value[3]}')
    print(f'  [4] sentence_details 类型: {type(first_value[4])}')
    print(f'  [4] sentence_details 长度: {len(first_value[4])}')
    
    if first_value[4]:
        detail = first_value[4][0]
        print(f'\n  sentence_details[0] 结构:')
        if isinstance(detail, dict):
            for key, value in detail.items():
                if isinstance(value, str) and len(value) > 50:
                    print(f'    {key}: {value[:50]}...')
                else:
                    print(f'    {key}: {value}')

print('\n' + '=' * 80)
print('[4] grounded_coder.build_coding_structure() 处理后的结构')
print('-' * 80)

grounded_coder = GroundedTheoryCoder()

# 处理原有编码生成器的结果
original_structured = grounded_coder.build_coding_structure(original_codes)
print(f'原有编码生成器 -> structured_codes:')
print(f'  三阶编码数量: {len(original_structured)}')
if original_structured:
    first_third = list(original_structured.keys())[0]
    print(f'  第一个三阶编码: {first_third}')
    second_cats = original_structured[first_third]
    print(f'  二阶编码数量: {len(second_cats)}')
    if second_cats:
        first_second = list(second_cats.keys())[0]
        print(f'  第一个二阶编码: {first_second}')
        first_contents = second_cats[first_second]
        print(f'  一阶编码数量: {len(first_contents)}')
        if first_contents:
            first_content = first_contents[0]
            print(f'\n  第一个一阶编码结构:')
            if isinstance(first_content, dict):
                for key, value in first_content.items():
                    if isinstance(value, str) and len(value) > 50:
                        print(f'    {key}: {value[:50]}...')
                    elif isinstance(value, list):
                        print(f'    {key}: [{len(value)} items]')
                    else:
                        print(f'    {key}: {value}')

# 处理新适配器的结果
adapter_structured = grounded_coder.build_coding_structure(adapter_codes)
print(f'\n新适配器 -> structured_codes:')
print(f'  三阶编码数量: {len(adapter_structured)}')
if adapter_structured:
    first_third = list(adapter_structured.keys())[0]
    print(f'  第一个三阶编码: {first_third}')
    second_cats = adapter_structured[first_third]
    print(f'  二阶编码数量: {len(second_cats)}')
    if second_cats:
        first_second = list(second_cats.keys())[0]
        print(f'  第一个二阶编码: {first_second}')
        first_contents = second_cats[first_second]
        print(f'  一阶编码数量: {len(first_contents)}')
        if first_contents:
            first_content = first_contents[0]
            print(f'\n  第一个一阶编码结构:')
            if isinstance(first_content, dict):
                for key, value in first_content.items():
                    if isinstance(value, str) and len(value) > 50:
                        print(f'    {key}: {value[:50]}...')
                    elif isinstance(value, list):
                        print(f'    {key}: [{len(value)} items]')
                    else:
                        print(f'    {key}: {value}')

print('\n' + '=' * 80)
print('分析完成')
print('=' * 80)
