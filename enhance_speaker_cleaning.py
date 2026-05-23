"""
加强说话人标记清理逻辑
"""

with open(r'd:\zthree2\data_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找并替换清理逻辑
old_clean = '''                # 清理角色标记（关键！）
                content = content.replace('受访者：', '').replace('采访者：', '').strip()'''

new_clean = '''                # 清理角色标记（关键！）
                # 1. 清理标准标记
                content = content.replace('受访者：', '').replace('采访者：', '').strip()
                
                # 2. 清理数字编号的说话人标记（如：里弄管家4：、受访者1：）
                import re
                content = re.sub(r'^[\w\u4e00-\u9fa5]+\d+[：:]\s*', '', content)
                
                # 3. 清理其他常见说话人标记
                content = re.sub(r'^(问|答|Q|A)[：:]\s*', '', content)
                
                content = content.strip()'''

if old_clean in content:
    content = content.replace(old_clean, new_clean)
    print('OK: Enhanced speaker name cleaning')
else:
    print('WARN: Pattern not found')

# 写回文件
with open(r'd:\zthree2\data_processor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
