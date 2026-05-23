"""
修改 EnhancedCodingGenerator，清理一阶编码开头的标点符号
"""

import re

with open(r'd:\zthree2\enhanced_coding_generator.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 在类中添加清理方法
# 找到类定义后的第一个方法前插入
insert_pos = content.find('    def __init__(self')

if insert_pos > 0:
    # 在 __init__ 方法前插入清理方法
    clean_method = '''    @staticmethod
    def _clean_code_prefix(code: str) -> str:
        """
        清理一阶编码开头的标点符号
        
        规则：
        - 移除开头的所有标点符号（除了引号）
        - 保留引号，因为它与后文有联系
        
        Args:
            code: 原始编码文本
            
        Returns:
            清理后的编码文本
        """
        if not code:
            return code
        
        # 定义要移除的开头标点（不包括引号）
        # 包括：。！？，、；：…—·●○◆◇■□▲△▼▽★☆※
        punctuation_to_remove = r'^[。！？，、；：…—·●○◆◇■□▲△▼▽★☆※\s]+'
        
        # 移除开头的标点（但保留引号）
        cleaned = re.sub(punctuation_to_remove, '', code)
        
        return cleaned.strip()

'''
    
    content = content[:insert_pos] + clean_method + content[insert_pos:]
    print('OK: Added _clean_code_prefix method')
else:
    print('WARN: Could not find insertion point')

# 2. 在使用 abstracted 的地方应用清理
# 找到 first_level_codes[code_key] = [ abstracted, 这一行
old_assignment = '''                first_level_codes[code_key] = [
                    abstracted,'''

new_assignment = '''                # 清理编码开头的标点符号
                abstracted = self._clean_code_prefix(abstracted)
                
                first_level_codes[code_key] = [
                    abstracted,'''

if old_assignment in content:
    content = content.replace(old_assignment, new_assignment)
    print('OK: Applied cleaning to abstracted')
else:
    print('WARN: Could not find assignment location')

# 写回文件
with open(r'd:\zthree2\enhanced_coding_generator.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
