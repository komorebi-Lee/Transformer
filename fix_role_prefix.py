"""
修改 extract_respondent_sentences，清理角色标记
"""

with open(r'd:\zthree2\data_processor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 查找 extract_respondent_sentences 方法中的 content = paragraph['content']
modified = False
for i, line in enumerate(lines):
    if "content = paragraph['content']" in line and i > 0:
        # 检查前面是否是 if paragraph['speaker'] == 'respondent':
        if "paragraph['speaker'] == 'respondent'" in lines[i-1]:
            # 在这一行后面添加清理角色标记的代码
            indent = ' ' * 16  # 保持缩进
            new_lines = [
                line,
                f'{indent}\n',
                f'{indent}# 清理角色标记（关键！）\n',
                f'{indent}content = content.replace("受访者：", "").replace("采访者：", "").strip()\n',
                f'{indent}\n'
            ]
            lines[i:i+1] = new_lines
            modified = True
            print(f'✅ 在第 {i+1} 行后添加了角色标记清理代码')
            break

if modified:
    with open(r'd:\zthree2\data_processor.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print('✅ 文件已更新')
else:
    print('❌ 未找到目标位置')

print('完成')
