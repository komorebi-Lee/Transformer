"""
直接添加 _find_text_number 方法到 data_processor.py
"""

with open(r'd:\zthree2\data_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 检查是否已经有这个方法
if 'def _find_text_number(self' in content:
    print('⚠️ _find_text_number 方法已存在')
else:
    # 在文件末尾添加方法
    method_code = '''
    def _find_text_number(self, text: str, text_number_mapping: Dict[int, str]) -> Optional[int]:
        """
        查找文本对应的 TextNumbering 编号
        
        Args:
            text: 句子文本
            text_number_mapping: {number: text} 映射
        
        Returns:
            编号或None
        """
        if not text_number_mapping:
            return None
        
        # 精确匹配
        for num, mapped_text in text_number_mapping.items():
            if text == mapped_text or text == mapped_text.strip():
                return num
        
        # 模糊匹配（去除空格和标点）
        text_clean = text.replace(' ', '').replace('\\n', '').replace('\\t', '')
        for num, mapped_text in text_number_mapping.items():
            mapped_clean = mapped_text.replace(' ', '').replace('\\n', '').replace('\\t', '')
            if text_clean == mapped_clean:
                return num
        
        # 包含匹配（文本是映射文本的一部分，或反之）
        if len(text_clean) > 10:
            for num, mapped_text in text_number_mapping.items():
                mapped_clean = mapped_text.replace(' ', '').replace('\\n', '').replace('\\t', '')
                if text_clean in mapped_clean or mapped_clean in text_clean:
                    # 确保相似度足够高
                    similarity = len(set(text_clean) & set(mapped_clean)) / max(len(text_clean), len(mapped_clean))
                    if similarity > 0.8:
                        return num
        
        return None
'''
    
    # 添加到文件末尾
    content = content.rstrip() + '\n' + method_code + '\n'
    
    with open(r'd:\zthree2\data_processor.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print('✅ 已添加 _find_text_number 方法')

print('完成')
