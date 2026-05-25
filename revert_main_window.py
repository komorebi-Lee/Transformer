"""
回退 main_window.py 的修改
"""

with open(r'd:\zthree2\main_window.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换修改的部分
old_code = """                    # 从sentence_details提取
                    if not all_ids and sentence_details:
                        for s in sentence_details:
                            if isinstance(s, dict):
                                # 优先使用 text_number
                                text_num = s.get('text_number')
                                if text_num:
                                    all_ids.add(str(text_num))
                                # 备选：sentence_id
                                elif s.get('sentence_id'):
                                    all_ids.add(str(s.get('sentence_id')))"""

new_code = """                    # 从sentence_details提取
                    if not all_ids and sentence_details:
                        for s in sentence_details:
                            if isinstance(s, dict) and s.get('sentence_id'):
                                all_ids.add(str(s.get('sentence_id')))"""

if old_code in content:
    content = content.replace(old_code, new_code)
    print('✅ 找到并替换了代码')
else:
    print('❌ 未找到要替换的代码')

# 写回文件
with open(r'd:\zthree2\main_window.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('完成')
