"""
分析原有 EnhancedCodingGenerator 的完整功能
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from data_processor import DataProcessor
from enhanced_coding_generator import EnhancedCodingGenerator
from model_manager import EnhancedModelManager
from grounded_theory_coder import GroundedTheoryCoder
import json

print('=' * 80)
print('原有 EnhancedCodingGenerator 完整功能分析')
print('=' * 80)

# 测试文件
test_file = r'C:\Users\33288\Downloads\新文本\润色后文件\陶阳里 非遗手艺人11.docx'

# 初始化
model_manager = EnhancedModelManager()
data_processor = DataProcessor()
coding_generator = EnhancedCodingGenerator()
grounded_coder = GroundedTheoryCoder()

print('\n[1] 处理文件')
print('-' * 80)
processed_data = data_processor.process_multiple_files([test_file])
print(f'提取句子数: {processed_data["total_sentences"]}')

print('\n[2] 生成编码')
print('-' * 80)
raw_codes = coding_generator.generate_grounded_theory_codes_multi_files(
    processed_data,
    model_manager
)

print(f'一阶编码数量: {len(raw_codes["一阶编码"])}')
print(f'二阶编码数量: {len(raw_codes["二阶编码"])}')
print(f'三阶编码数量: {len(raw_codes["三阶编码"])}')

# 分析第一个一阶编码的完整结构
if raw_codes['一阶编码']:
    first_key = list(raw_codes['一阶编码'].keys())[0]
    first_value = raw_codes['一阶编码'][first_key]
    
    print(f'\n[3] 第一个一阶编码完整结构 ({first_key})')
    print('-' * 80)
    print(f'类型: {type(first_value)}')
    print(f'长度: {len(first_value)}')
    
    print(f'\n[0] abstracted (编码内容):')
    print(f'  类型: {type(first_value[0])}')
    print(f'  值: {first_value[0][:100]}...' if len(str(first_value[0])) > 100 else f'  值: {first_value[0]}')
    
    print(f'\n[1] source_sentences:')
    print(f'  类型: {type(first_value[1])}')
    print(f'  长度: {len(first_value[1])}')
    if first_value[1]:
        sent = first_value[1][0]
        print(f'  第一个元素类型: {type(sent)}')
        if isinstance(sent, dict):
            print(f'  字段:')
            for key in sent.keys():
                value = sent[key]
                if isinstance(value, str) and len(value) > 50:
                    print(f'    {key}: {value[:50]}...')
                else:
                    print(f'    {key}: {value}')
    
    print(f'\n[2] file_count:')
    print(f'  类型: {type(first_value[2])}')
    print(f'  值: {first_value[2]}')
    
    print(f'\n[3] sentence_count:')
    print(f'  类型: {type(first_value[3])}')
    print(f'  值: {first_value[3]}')
    
    print(f'\n[4] sentence_details:')
    print(f'  类型: {type(first_value[4])}')
    print(f'  长度: {len(first_value[4])}')
    if first_value[4]:
        detail = first_value[4][0]
        print(f'  第一个元素类型: {type(detail)}')
        if isinstance(detail, dict):
            print(f'  字段:')
            for key in detail.keys():
                value = detail[key]
                if isinstance(value, str) and len(value) > 50:
                    print(f'    {key}: {value[:50]}...')
                else:
                    print(f'    {key}: {value}')

print('\n[4] 构建编码结构')
print('-' * 80)
structured_codes = grounded_coder.build_coding_structure(raw_codes)
print(f'三阶编码数量: {len(structured_codes)}')

if structured_codes:
    first_third = list(structured_codes.keys())[0]
    print(f'第一个三阶编码: {first_third}')
    
    second_cats = structured_codes[first_third]
    print(f'二阶编码数量: {len(second_cats)}')
    
    if second_cats:
        first_second = list(second_cats.keys())[0]
        print(f'第一个二阶编码: {first_second}')
        
        first_contents = second_cats[first_second]
        print(f'一阶编码数量: {len(first_contents)}')
        
        if first_contents:
            first_content = first_contents[0]
            print(f'\n第一个一阶编码结构:')
            print(f'  类型: {type(first_content)}')
            if isinstance(first_content, dict):
                print(f'  字段:')
                for key in first_content.keys():
                    value = first_content[key]
                    if isinstance(value, str) and len(value) > 50:
                        print(f'    {key}: {value[:50]}...')
                    elif isinstance(value, list):
                        print(f'    {key}: [列表，长度={len(value)}]')
                        if value and isinstance(value[0], dict):
                            print(f'      第一个元素字段: {list(value[0].keys())}')
                    else:
                        print(f'    {key}: {value}')

print('\n[5] 保存详细结构到文件')
print('-' * 80)

# 保存第一个编码的完整结构
if raw_codes['一阶编码']:
    first_key = list(raw_codes['一阶编码'].keys())[0]
    first_value = raw_codes['一阶编码'][first_key]
    
    # 转换为可序列化的格式
    serializable = {
        'key': first_key,
        'abstracted': first_value[0],
        'source_sentences': first_value[1],
        'file_count': first_value[2],
        'sentence_count': first_value[3],
        'sentence_details': first_value[4]
    }
    
    with open(r'd:\zthree2\original_code_structure.json', 'w', encoding='utf-8') as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)
    
    print('✅ 已保存到 original_code_structure.json')

# 保存 structured_codes 的第一个编码
if structured_codes:
    first_third = list(structured_codes.keys())[0]
    second_cats = structured_codes[first_third]
    if second_cats:
        first_second = list(second_cats.keys())[0]
        first_contents = second_cats[first_second]
        if first_contents:
            first_content = first_contents[0]
            
            with open(r'd:\zthree2\original_structured_code.json', 'w', encoding='utf-8') as f:
                json.dump(first_content, f, ensure_ascii=False, indent=2)
            
            print('✅ 已保存到 original_structured_code.json')

print('\n' + '=' * 80)
print('分析完成')
print('=' * 80)
