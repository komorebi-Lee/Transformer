"""
诊断自动编码的三个问题：
1. 定位高亮错误（多定位了一句）
2. 关联编号错误
3. 角色分类定位不达标
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
print('诊断自动编码问题')
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

# 显示编号7附近的内容
print(f'\n编号7附近的内容:')
for i in range(5, 10):
    if i in number_mapping:
        text = number_mapping[i]
        print(f'  [{i}]: {text[:80]}...' if len(text) > 80 else f'  [{i}]: {text}')

print('\n[2] 识别段落（区分采访人和受访人）')
print('-' * 80)
paragraphs = data_processor.identify_interview_paragraphs(content, 'test.docx')
print(f'总段落数: {len(paragraphs)}')

# 统计角色
interviewer_count = sum(1 for p in paragraphs if p['speaker'] == 'interviewer')
respondent_count = sum(1 for p in paragraphs if p['speaker'] == 'respondent')
print(f'采访人段落: {interviewer_count}')
print(f'受访人段落: {respondent_count}')

# 显示前10个段落的角色
print(f'\n前10个段落的角色:')
for i, p in enumerate(paragraphs[:10]):
    content_preview = p['content'][:50].replace('\n', ' ')
    print(f'  {i+1}. {p["speaker"]}: {content_preview}...')

print('\n[3] 提取受访人句子')
print('-' * 80)
number_mappings = {'陶阳里 非遗手艺人11.docx': number_mapping}
processed_data = data_processor.process_multiple_files([test_file], number_mappings=number_mappings)

file_sentence_mapping = processed_data['file_sentence_mapping']
for filename, data in file_sentence_mapping.items():
    sentences = data['sentences']
    print(f'提取的句子数: {len(sentences)}')
    
    # 检查前10个句子的角色
    print(f'\n前10个句子:')
    for i, sent in enumerate(sentences[:10]):
        speaker = sent.get('speaker', 'unknown')
        text_number = sent.get('text_number')
        content = sent.get('content', '')[:50]
        print(f'  {i+1}. 角色={speaker}, 编号={text_number}, 内容={content}...')
    
    # 检查是否有采访人的句子
    interviewer_sentences = [s for s in sentences if s.get('speaker') == 'interviewer']
    if interviewer_sentences:
        print(f'\n❌ 发现 {len(interviewer_sentences)} 个采访人句子（不应该提取）:')
        for i, sent in enumerate(interviewer_sentences[:5]):
            text_number = sent.get('text_number')
            content = sent.get('content', '')[:50]
            print(f'  {i+1}. 编号={text_number}, 内容={content}...')
    else:
        print(f'\n✅ 没有采访人句子（正确）')

print('\n[4] 生成编码')
print('-' * 80)
optimized_pipeline = OptimizedCodingPipeline(model_manager=model_manager, use_qa_classifier=True)
adapter = FullyCompatibleCodingAdapter(optimized_pipeline)
raw_codes = adapter.generate_grounded_theory_codes_multi_files(processed_data, model_manager)

print(f'一阶编码数量: {len(raw_codes["一阶编码"])}')

# 查找编号7对应的编码
print(f'\n[5] 查找编号7对应的编码')
print('-' * 80)
for code_key, code_value in raw_codes['一阶编码'].items():
    sentence_details = code_value[4]
    for detail in sentence_details:
        if detail.get('text_number') == 7:
            print(f'找到编码: {code_key}')
            print(f'  编码内容: {code_value[0]}')
            print(f'  text_number: {detail.get("text_number")}')
            print(f'  numbered_sentence: {detail.get("numbered_sentence")}')
            print(f'  speaker: {detail.get("speaker")}')
            print(f'  content: {detail.get("content")[:100]}...')

print('\n[6] 构建编码结构')
print('-' * 80)
grounded_coder = GroundedTheoryCoder()
structured_codes = grounded_coder.build_coding_structure(raw_codes)

# 查找 A08
print(f'\n查找 A08:')
found_a08 = False
for third_cat, second_cats in structured_codes.items():
    for second_cat, first_contents in second_cats.items():
        for first_content in first_contents:
            if first_content.get('code_id') == 'A08':
                found_a08 = True
                print(f'找到 A08:')
                print(f'  三阶: {third_cat}')
                print(f'  二阶: {second_cat}')
                print(f'  内容: {first_content.get("content")[:100]}...')
                
                sentence_details = first_content.get('sentence_details', [])
                print(f'  句子数: {len(sentence_details)}')
                
                for i, detail in enumerate(sentence_details):
                    print(f'\n  句子 {i+1}:')
                    print(f'    text_number: {detail.get("text_number")}')
                    print(f'    speaker: {detail.get("speaker")}')
                    print(f'    content: {detail.get("content")[:80]}...')

if not found_a08:
    print('❌ 未找到 A08')

print('\n[7] 问题总结')
print('-' * 80)
print('问题1: 定位高亮错误（多定位了一句）')
print('  - 可能原因: 高亮定位逻辑使用了错误的编号或范围')
print('  - 需要检查: 主程序的高亮定位代码')

print('\n问题2: 关联编号错误')
print('  - 可能原因: text_number 匹配不准确')
print('  - 需要检查: _find_text_number 方法的匹配逻辑')

print('\n问题3: 角色分类定位不达标')
print('  - 可能原因: extract_respondent_sentences 提取了采访人的句子')
print('  - 需要检查: identify_interview_paragraphs 的角色识别准确率')

print('\n' + '=' * 80)
print('诊断完成')
print('=' * 80)
