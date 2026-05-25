"""
修复 number_mappings 属性错误
"""

with open(r'd:\zthree2\main_window.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 在第1763行后添加保存为实例变量的代码
# 第1763行是: number_mappings[filename] = number_mapping

for i, line in enumerate(lines):
    if i == 1763:  # 第1764行（索引1763）
        # 检查下一行是否已经有保存语句
        if 'self.number_mappings = number_mappings' not in lines[i+1]:
            # 在空行之前插入
            lines.insert(i+1, '            \n')
            lines.insert(i+2, '            # 保存为实例变量，供后续验证使用\n')
            lines.insert(i+3, '            self.number_mappings = number_mappings\n')
            print('✅ 已添加 self.number_mappings = number_mappings')
        else:
            print('⚠️ 已存在，跳过')
        break

# 写回文件
with open(r'd:\zthree2\main_window.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('完成')
