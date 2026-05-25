"""
修改匹配调用：使用原始文本而不是清理后的文本
"""

with open(r'd:\zthree2\data_processor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 查找并替换 _find_text_number 的调用
for i, line in enumerate(lines):
    if 'text_number = self._find_text_number(clean_sentence, text_number_mapping)' in line:
        # 替换为使用 original_sentence
        lines[i] = line.replace('clean_sentence', 'original_sentence')
        print(f'OK: Updated _find_text_number call at line {i+1}')
        print(f'   From: {line.strip()}')
        print(f'   To:   {lines[i].strip()}')

# 写回文件
with open(r'd:\zthree2\data_processor.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Done')
