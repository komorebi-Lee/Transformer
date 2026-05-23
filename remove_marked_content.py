"""
删除 marked_content，只保留纯净的 content
"""

with open(r'd:\zthree2\grounded_theory_coder.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 查找 add_code_id_to_sentences 方法
in_method = False
method_start = -1
method_end = -1
indent_level = 0

for i, line in enumerate(lines):
    if 'def add_code_id_to_sentences' in line:
        in_method = True
        method_start = i
        indent_level = len(line) - len(line.lstrip())
        continue
    
    if in_method:
        # 检查是否到达下一个方法
        if line.strip() and not line.strip().startswith('#'):
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= indent_level and line.strip().startswith('def '):
                method_end = i
                break

if method_start >= 0:
    # 替换整个方法
    new_method = '''    def add_code_id_to_sentences(self, sentence_details: List[Dict[str, Any]], code_id: str) -> List[Dict[str, Any]]:
        """为句子详情添加编码ID（不修改content，不添加marked_content）"""
        updated_details = []

        for sentence in sentence_details:
            if isinstance(sentence, dict):
                updated_sentence = sentence.copy()
                # 只添加 code_id 字段，不修改 content，不添加 marked_content
                updated_sentence['code_id'] = code_id
                updated_details.append(updated_sentence)
            else:
                updated_details.append(sentence)

        return updated_details

'''
    
    if method_end > 0:
        lines[method_start:method_end] = [new_method]
    else:
        # 如果是最后一个方法，替换到文件末尾
        lines[method_start:] = [new_method]
    
    print(f'OK: Replaced method at line {method_start+1}')
else:
    print('WARN: Method not found')

# 写回文件
with open(r'd:\zthree2\grounded_theory_coder.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Done')
