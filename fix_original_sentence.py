"""
修复 original_sentence 的保存
"""

with open(r'd:\zthree2\data_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找并替换错误的行
old_line = "original_sentence = sentence  # 保存原始文本（未清理）\\n"
new_line = "original_sentence = sentence  # 保存原始文本（未清理）\n"

if old_line in content:
    content = content.replace(old_line, new_line)
    print('OK: Fixed newline character')
else:
    print('WARN: Pattern not found, trying alternative')
    
    # 尝试其他可能的模式
    import re
    # 查找包含 original_sentence 的行
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'original_sentence = sentence' in line and '\\n' in line:
            lines[i] = line.replace('\\n', '')
            print(f'OK: Fixed line {i+1}')
            content = '\n'.join(lines)
            break

# 写回文件
with open(r'd:\zthree2\data_processor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
