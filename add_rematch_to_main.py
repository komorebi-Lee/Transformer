"""
在主程序中添加重新匹配步骤
"""

with open(r'd:\zthree2\main_window.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 查找 build_coding_structure 这一行
for i, line in enumerate(lines):
    if 'self.structured_codes = self.grounded_coder.build_coding_structure(raw_codes)' in line:
        # 在这一行后面插入重新匹配的代码
        indent = ' ' * 12
        new_lines = [
            '\n',
            f'{indent}# 重新匹配 text_number（使用一阶编码中的原始文本）\n',
            f'{indent}if self.number_mappings:\n',
            f'{indent}    from text_number_rematcher import rematch_text_numbers_for_codes\n',
            f'{indent}    # 获取当前文件的 number_mapping\n',
            f'{indent}    for filename, number_mapping in self.number_mappings.items():\n',
            f'{indent}        self.structured_codes = rematch_text_numbers_for_codes(\n',
            f'{indent}            self.structured_codes,\n',
            f'{indent}            number_mapping\n',
            f'{indent}        )\n',
            f'{indent}        break  # 只处理第一个文件的映射\n',
        ]
        
        lines[i+1:i+1] = new_lines
        print(f'OK: Inserted rematch code after line {i+1}')
        break

# 写回文件
with open(r'd:\zthree2\main_window.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Done')
