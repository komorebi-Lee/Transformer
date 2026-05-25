"""
修改验证逻辑：在 update_coding_tree 之后调用
"""

with open(r'd:\zthree2\main_window.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找并替换旧的验证逻辑
old_code = """            # 构建编码结构
            self.structured_codes = self.grounded_coder.build_coding_structure(raw_codes)
            
            # 验证并过滤不匹配的编码
            if self.number_mappings:
                from code_validator import validate_and_filter_codes
                # 获取当前文件的 number_mapping
                for filename, number_mapping in self.number_mappings.items():
                    self.structured_codes = validate_and_filter_codes(
                        self.structured_codes,
                        number_mapping
                    )
                    break  # 只处理第一个文件的映射

            # 更新界面
            self.update_coding_tree()"""

new_code = """            # 构建编码结构
            self.structured_codes = self.grounded_coder.build_coding_structure(raw_codes)

            # 更新界面
            self.update_coding_tree()
            
            # 验证并过滤不匹配的编码（基于编码树的关联编号）
            if self.number_mappings:
                from code_validator_tree import validate_and_filter_codes_by_tree
                # 获取当前文件的 number_mapping
                for filename, number_mapping in self.number_mappings.items():
                    self.structured_codes = validate_and_filter_codes_by_tree(
                        self.coding_tree,
                        self.structured_codes,
                        number_mapping
                    )
                    break  # 只处理第一个文件的映射
                
                # 重新更新编码树（删除不匹配的编码后）
                self.update_coding_tree()"""

if old_code in content:
    content = content.replace(old_code, new_code)
    print('✅ 找到并替换了验证逻辑')
else:
    print('❌ 未找到要替换的代码')
    print('尝试查找部分代码...')
    
    # 尝试查找关键部分
    if 'from code_validator import validate_and_filter_codes' in content:
        print('  找到旧的 import 语句')
    if 'from code_validator_tree import' in content:
        print('  已经有新的 import 语句')

# 写回文件
with open(r'd:\zthree2\main_window.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('完成')
