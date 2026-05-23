"""
检查 text_number_mapping 中的文本
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from data_processor import DataProcessor
from text_numbering import TextNumberingManager

print('=' * 80)
print('检查 text_number_mapping 中的文本')
print('=' * 80)

# 测试文件
test_file = r'C:\Users\33288\Downloads\新文本\润色后文件\陶阳里 非遗手艺人11.docx'

# 初始化
data_processor = DataProcessor()
numbering_manager = TextNumberingManager()

print('\n[1] 读取原始文件')
content = data_processor.read_file(test_file)

print(f'原始文件前200字符:')
print(content[:200])

print('\n[2] TextNumbering 编号')
numbered_content, number_mapping = numbering_manager.number_text(content, 'test.docx')

print(f'\n编号后的文本前200字符:')
print(numbered_content[:200])

print(f'\n前5个编号的映射:')
for i, (num, text) in enumerate(list(number_mapping.items())[:5]):
    print(f'\n{num}: {text}')
    
    # 检查是否包含说话人标记
    if '受访者：' in text or '采访者：' in text:
        print(f'  ⚠️ 包含说话人标记')
    else:
        print(f'  ✅ 无说话人标记')

print('\n' + '=' * 80)
print('检查完成')
print('=' * 80)
