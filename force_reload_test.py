"""
强制重新加载模块并测试
"""

import sys
import importlib

# 移除旧模块
if 'data_processor' in sys.modules:
    del sys.modules['data_processor']
if 'text_numbering' in sys.modules:
    del sys.modules['text_numbering']

sys.path.insert(0, r'D:\zthree2')

# 重新导入
from data_processor import DataProcessor
from text_numbering import TextNumberingManager

print('=' * 80)
print('强制重新加载模块并测试')
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

print('\n[2] 处理文件')
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
        print(f'  content: {sent.get("content", "")[:80]}')
        print(f'  original_content: {sent.get("original_content", "")[:80]}')
        print(f'  text_number: {sent.get("text_number")}')
        
        # 关键检查
        content_val = sent.get('content', '')
        original_val = sent.get('original_content', '')
        
        print(f'\n关键检查:')
        print(f'  content == original_content: {content_val == original_val}')
        print(f'  len(content): {len(content_val)}')
        print(f'  len(original_content): {len(original_val)}')
        
        if content_val == original_val:
            print(f'  ❌ 两者相同，修改未生效')
        else:
            print(f'  ✅ 两者不同，修改已生效')

print('\n' + '=' * 80)
print('测试完成')
print('=' * 80)
