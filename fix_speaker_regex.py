"""
改进说话人标记清理逻辑 - 处理无冒号情况
"""

import re

with open(r'd:\zthree2\data_processor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 查找并替换清理逻辑
for i, line in enumerate(lines):
    if '# 2. 清理数字编号的说话人标记' in line:
        # 找到这一行，替换下一行
        if i+1 < len(lines) and 'content = re.sub' in lines[i+1]:
            # 替换正则表达式，处理有冒号和无冒号的情况
            lines[i+1] = '                content = re.sub(r\'^[\\w\\u4e00-\\u9fa5]+\\d+[：:]?\\s*\', \'\', content)\n'
            print(f'OK: Updated regex at line {i+2}')
            break

# 写回文件
with open(r'd:\zthree2\data_processor.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Done')
