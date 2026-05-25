"""
检查句子是否需要清理
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from data_processor import DataProcessor
from text_numbering import TextNumberingManager
import re

print('=' * 80)
print('检查句子是否需要清理')
print('=' * 80)

# 测试文件
test_file = r'C:\Users\33288\Downloads\新文本\润色后文件\陶阳里 非遗手艺人11.docx'

# 初始化
data_processor = DataProcessor()
numbering_manager = TextNumberingManager()

print('\n[1] 读取原始文件')
content = data_processor.read_file(test_file)

# 显示前500字符
print(f'前500字符:')
print(content[:500])

print('\n[2] 检查是否有需要清理的标记')
patterns = [
    (r'\[A\d+\]', '一阶编码标记'),
    (r'里弄管家\d+[：:]', '说话人标记'),
    (r'受访者\d*[：:]', '受访者标记'),
]

for pattern, name in patterns:
    matches = re.findall(pattern, content)
    if matches:
        print(f'  找到 {name}: {len(matches)} 个')
        print(f'    示例: {matches[:3]}')
    else:
        print(f'  未找到 {name}')

print('\n[3] 编号后的文本')
numbered_content, number_mapping = numbering_manager.number_text(content, 'test.docx')

# 显示前3个编号的文本
print(f'前3个编号的文本:')
for i, (num, text) in enumerate(list(number_mapping.items())[:3]):
    print(f'\n编号 {num}:')
    print(f'  {text}')
    
    # 检查是否有标记
    if re.search(r'\[A\d+\]', text):
        print(f'  ⚠️ 包含一阶编码标记')
    if re.search(r'里弄管家\d+[：:]', text):
        print(f'  ⚠️ 包含说话人标记')

print('\n' + '=' * 80)
print('检查完成')
print('=' * 80)
