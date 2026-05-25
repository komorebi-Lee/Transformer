"""
修改 main_window.py 传递 number_mappings
"""

with open(r'd:\zthree2\main_window.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找并替换
old_code = '''            self.progress_bar.setValue(10)

            # 第二步：处理文件数据
            file_paths = list(self.loaded_files.keys())
            processed_data = self.data_processor.process_multiple_files(file_paths)'''

new_code = '''            self.progress_bar.setValue(10)

            # 第二步：处理文件数据（传递编号映射）
            file_paths = list(self.loaded_files.keys())
            
            # 构建编号映射字典
            number_mappings = {}
            for file_path, file_data in self.loaded_files.items():
                filename = file_data.get('filename', os.path.basename(file_path))
                number_mapping = file_data.get('number_mapping', {})
                if number_mapping:
                    number_mappings[filename] = number_mapping
            
            processed_data = self.data_processor.process_multiple_files(
                file_paths,
                number_mappings=number_mappings  # 传递编号映射
            )'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print('✅ 修改成功')
else:
    print('❌ 未找到目标代码，尝试查找变体...')
    
    # 尝试更宽松的匹配
    import re
    pattern = r'self\.progress_bar\.setValue\(10\).*?processed_data = self\.data_processor\.process_multiple_files\(file_paths\)'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        print(f'找到代码片段:\n{match.group(0)[:200]}...')
    else:
        print('完全未找到')

# 写回文件
with open(r'd:\zthree2\main_window.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ main_window.py 修改完成')
