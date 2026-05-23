"""
分析主程序中的原文本匹配逻辑
"""

import sys
sys.path.insert(0, r'D:\zthree2')

print('=' * 80)
print('分析主程序中的原文本匹配逻辑')
print('=' * 80)

print('\n[1] 查找主程序中与 text_number 相关的代码')
print('-' * 80)

with open(r'd:\zthree2\main_window.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 查找所有与 text_number 相关的行
text_number_lines = []
for i, line in enumerate(lines):
    if 'text_number' in line.lower() or 'textnumber' in line.lower():
        text_number_lines.append((i+1, line.strip()))

print(f'找到 {len(text_number_lines)} 行与 text_number 相关的代码:')
for line_num, line_content in text_number_lines[:20]:  # 只显示前20行
    print(f'  {line_num}: {line_content[:100]}')

print('\n[2] 查找定位和高亮相关的代码')
print('-' * 80)

# 查找定位相关的代码
locate_lines = []
for i, line in enumerate(lines):
    if '定位' in line or 'locate' in line.lower() or 'highlight' in line.lower() or '高亮' in line:
        locate_lines.append((i+1, line.strip()))

print(f'找到 {len(locate_lines)} 行与定位/高亮相关的代码:')
for line_num, line_content in locate_lines[:20]:
    print(f'  {line_num}: {line_content[:100]}')

print('\n[3] 查找双击编码时的处理逻辑')
print('-' * 80)

# 查找双击事件处理
for i, line in enumerate(lines):
    if 'itemDoubleClicked' in line or 'on_coding_tree_item_double_clicked' in line:
        print(f'找到双击事件处理函数:')
        print(f'  行 {i+1}: {line.strip()}')
        
        # 显示这个函数的内容
        print(f'\n函数内容:')
        for j in range(i, min(len(lines), i+50)):
            print(f'{j+1}: {lines[j]}', end='')
            if j > i and lines[j].strip() and not lines[j].strip().startswith('#') and lines[j][0] not in [' ', '\t']:
                break
        break

print('\n' + '=' * 80)
print('分析完成')
print('=' * 80)
