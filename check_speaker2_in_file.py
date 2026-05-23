"""
检查实际文件中"说话人2"的情况
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from data_processor import DataProcessor

print('=' * 80)
print('检查实际文件中"说话人2"的情况')
print('=' * 80)

# 测试文件（根据截图，应该是"陶阳里 非遗手艺人11.docx"）
test_file = r'C:\Users\33288\Downloads\新文本\润色后文件\陶阳里 非遗手艺人11.docx'

# 初始化
data_processor = DataProcessor()

print('\n[1] 读取原始文件')
content = data_processor.read_file(test_file)

# 查找"说话人2"
import re
matches = re.findall(r'说话人\d+[：:]?[^\n]{0,50}', content)

if matches:
    print(f'\n找到 {len(matches)} 个"说话人X"标记:')
    for i, match in enumerate(matches[:10]):  # 只显示前10个
        print(f'  {i+1}. {match}')
else:
    print('\n未找到"说话人X"标记')

# 查找其他可能的说话人标记
other_patterns = [
    (r'受访者\d*[：:]', '受访者'),
    (r'采访者\d*[：:]', '采访者'),
    (r'里弄管家\d*[：:]', '里弄管家'),
]

for pattern, name in other_patterns:
    matches = re.findall(pattern, content)
    if matches:
        print(f'\n找到 {len(matches)} 个"{name}"标记')

print('\n' + '=' * 80)
print('检查完成')
print('=' * 80)
