"""
使用原始文本进行匹配 - 最简单最准确的方案
"""

with open(r'd:\zthree2\data_processor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 查找句子构建的位置
for i, line in enumerate(lines):
    if "sentence_info = {" in line:
        # 找到这个位置，向上查找原始句子
        # 需要在清理之前保存原始文本
        
        # 向上查找 for sentence in sentences 循环
        for j in range(i-1, max(0, i-30), -1):
            if 'for sentence in sentences:' in lines[j]:
                # 在这个循环开始后立即保存原始句子
                # 在 j+1 位置插入保存原始文本的代码
                
                # 找到 if self.is_meaningful_sentence(sentence): 这一行
                for k in range(j+1, i):
                    if 'if self.is_meaningful_sentence(sentence):' in lines[k]:
                        # 在这一行之后插入保存原始文本
                        indent = ' ' * 24
                        new_line = f'{indent}original_sentence = sentence  # 保存原始文本（未清理）\\n'
                        
                        # 检查是否已经存在
                        if 'original_sentence = sentence' not in lines[k+1]:
                            lines.insert(k+1, new_line)
                            print(f'OK: Inserted original_sentence at line {k+2}')
                        break
                break
        
        # 修改 sentence_info 中的 original_content
        for j in range(i, min(len(lines), i+20)):
            if "'original_content': clean_sentence" in lines[j]:
                lines[j] = lines[j].replace("'original_content': clean_sentence", "'original_content': original_sentence")
                print(f'OK: Updated original_content at line {j+1}')
                break
        
        break

# 写回文件
with open(r'd:\zthree2\data_processor.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Done')
