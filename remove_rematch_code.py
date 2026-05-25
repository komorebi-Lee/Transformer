"""
删除重复的重新匹配代码
"""

with open(r'd:\zthree2\main_window.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 查找并删除所有 rematch_text_numbers_for_codes 相关的代码
new_lines = []
skip_until = -1

for i, line in enumerate(lines):
    # 如果在跳过范围内，继续跳过
    if i < skip_until:
        continue
    
    # 检查是否是重新匹配的开始
    if '# 重新匹配 text_number（使用一阶编码中的原始文本）' in line:
        # 跳过接下来的10行（整个重新匹配块）
        skip_until = i + 11
        print(f'Removed rematch block starting at line {i+1}')
        continue
    
    new_lines.append(line)

# 写回文件
with open(r'd:\zthree2\main_window.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f'Done. Removed {len(lines) - len(new_lines)} lines')
