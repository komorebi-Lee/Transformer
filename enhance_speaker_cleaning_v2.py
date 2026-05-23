"""
加强说话人标记清理逻辑
"""

import re

with open(r'd:\zthree2\data_processor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 查找并替换第565行
for i, line in enumerate(lines):
    if i == 564 and 'content.replace("受访者："' in line:
        # 替换这一行及后面的空行
        new_lines = [
            '                # 1. 清理标准标记\n',
            '                content = content.replace("受访者：", "").replace("采访者：", "").strip()\n',
            '                \n',
            '                # 2. 清理数字编号的说话人标记（如：里弄管家4：、受访者1：）\n',
            '                content = re.sub(r\'^[\\w\\u4e00-\\u9fa5]+\\d+[：:]\\s*\', \'\', content)\n',
            '                \n',
            '                # 3. 清理其他常见说话人标记\n',
            '                content = re.sub(r\'^(问|答|Q|A)[：:]\\s*\', \'\', content)\n',
            '                \n',
            '                content = content.strip()\n',
        ]
        
        lines[i:i+1] = new_lines
        print(f'OK: Replaced line {i+1}')
        break

# 写回文件
with open(r'd:\zthree2\data_processor.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Done')
