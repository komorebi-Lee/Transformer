"""
诊断当前数据流：检查修改是否生效
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from data_processor import DataProcessor
from text_numbering import TextNumberingManager

print('=' * 80)
print('诊断当前数据流')
print('=' * 80)

# 测试文件
test_file = r'C:\Users\33288\Downloads\新文本\润色后文件\陶阳里 非遗手艺人11.docx'

# 初始化
data_processor = DataProcessor()
numbering_manager = TextNumberingManager()

print('\n[1] 读取文件并编号')
content = data_processor.read_file(test_file)
numbered_content, number_mapping = numbering_manager.number_text(content, 'test.docx')

print(f'编号数量: {len(number_mapping)}')
print(f'\n前3个编号:')
for i, (num, text) in enumerate(list(number_mapping.items())[:3]):
    print(f'  {num}: {text[:60]}...')

print('\n[2] 处理文件')
number_mappings = {'陶阳里 非遗手艺人11.docx': number_mapping}
processed_data = data_processor.process_multiple_files([test_file], number_mappings=number_mappings)

print(f'提取句子数: {processed_data["total_sentences"]}')

# 检查前3个句子
file_sentence_mapping = processed_data['file_sentence_mapping']
for filename, data in file_sentence_mapping.items():
    sentences = data['sentences']
    
    print(f'\n前3个句子的详细信息:')
    for i, sent in enumerate(sentences[:3]):
        print(f'\n句子 {i+1}:')
        print(f'  content: {sent.get("content", "")[:60]}...')
        print(f'  original_content: {sent.get("original_content", "")[:60]}...')
        print(f'  text_number: {sent.get("text_number")}')
        print(f'  numbered_sentence: {sent.get("numbered_sentence", "")[:60]}...')
        
        # 检查 content 和 original_content 是否相同
        if sent.get('content') == sent.get('original_content'):
            print(f'  ⚠️ content 和 original_content 相同')
        else:
            print(f'  ✅ content 和 original_content 不同')
        
        # 检查是否匹配
        text_number = sent.get('text_number')
        if text_number and text_number in number_mapping:
            mapped_text = number_mapping[text_number]
            original = sent.get('original_content', '')
            
            if original == mapped_text or original == mapped_text.strip():
                print(f'  ✅ original_content 精确匹配 mapped_text')
            elif original in mapped_text or mapped_text in original:
                print(f'  ⚠️ original_content 部分匹配 mapped_text')
            else:
                print(f'  ❌ original_content 不匹配 mapped_text')
                print(f'     original: {original[:60]}...')
                print(f'     mapped:   {mapped_text[:60]}...')

print('\n[3] 检查 _find_text_number 方法')
print('-' * 80)

# 测试 _find_text_number 方法
test_sentence = list(number_mapping.values())[0]
print(f'测试句子: {test_sentence[:60]}...')

result = data_processor._find_text_number(test_sentence, number_mapping)
print(f'匹配结果: {result}')

if result:
    print(f'✅ _find_text_number 方法工作正常')
else:
    print(f'❌ _find_text_number 方法有问题')

print('\n' + '=' * 80)
print('诊断完成')
print('=' * 80)
