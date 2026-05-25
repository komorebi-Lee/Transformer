"""
修改 _find_text_number 方法，添加去除句号的匹配
"""

with open(r'd:\zthree2\data_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找并替换 _find_text_number 方法
import re

# 找到整个方法
pattern = r'(    def _find_text_number\(self.*?return None\n)'
match = re.search(pattern, content, re.DOTALL)

if match:
    old_method = match.group(0)
    
    # 新方法
    new_method = '''    def _find_text_number(self, text: str, text_number_mapping: Dict[int, str]) -> Optional[int]:
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
        
        # 去除句号后匹配（关键！）
        text_no_punct = text.rstrip('。！？!?')
        for num, mapped_text in text_number_mapping.items():
            mapped_no_punct = mapped_text.rstrip('。！？!?')
            if text_no_punct == mapped_no_punct:
                return num
        
        # 模糊匹配（去除空格和标点）
        text_clean = text.replace(' ', '').replace('\\n', '').replace('\\t', '').rstrip('。！？!?')
        for num, mapped_text in text_number_mapping.items():
            mapped_clean = mapped_text.replace(' ', '').replace('\\n', '').replace('\\t', '').rstrip('。！？!?')
            if text_clean == mapped_clean:
                return num
        
        # 包含匹配（文本是映射文本的一部分，或反之）
        if len(text_clean) > 10:
            for num, mapped_text in text_number_mapping.items():
                mapped_clean = mapped_text.replace(' ', '').replace('\\n', '').replace('\\t', '').rstrip('。！？!?')
                if text_clean in mapped_clean or mapped_clean in text_clean:
                    # 确保相似度足够高
                    similarity = len(set(text_clean) & set(mapped_clean)) / max(len(text_clean), len(mapped_clean))
                    if similarity > 0.8:
                        return num
        
        return None
'''
    
    content = content.replace(old_method, new_method)
    
    with open(r'd:\zthree2\data_processor.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print('✅ 已修改 _find_text_number 方法，添加去除句号的匹配')
else:
    print('❌ 未找到 _find_text_number 方法')

print('完成')
