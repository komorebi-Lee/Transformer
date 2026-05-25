"""
修改 data_processor.py 添加 TextNumbering 编号支持
"""

with open(r'd:\zthree2\data_processor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 修改 extract_respondent_sentences 的签名
old_sig = '''    def extract_respondent_sentences(
        self,
        paragraphs: List[Dict[str, Any]],
        filename: str,
        sentence_number_lookup: Optional[List[Tuple[int, str]]] = None,
        file_path: Optional[str] = None,
    ) -> List[Dict[str, Any]]:'''

new_sig = '''    def extract_respondent_sentences(
        self,
        paragraphs: List[Dict[str, Any]],
        filename: str,
        sentence_number_lookup: Optional[List[Tuple[int, str]]] = None,
        file_path: Optional[str] = None,
        text_number_mapping: Optional[Dict[int, str]] = None,
    ) -> List[Dict[str, Any]]:'''

if old_sig in content:
    content = content.replace(old_sig, new_sig)
    print('✅ 1. 修改了方法签名')
else:
    print('❌ 1. 未找到方法签名')

# 2. 在 sentence_info 构建前添加编号查找
old_code = '''                        if clean_sentence and len(clean_sentence) >= 5:
                            sentence_info = {
                                'content': clean_sentence,
                                'original_content': clean_sentence,  # 保存清理后的内容
                                'paragraph_content': content[:100] + '...' if len(content) > 100 else content,
                                'filename': filename,
                                'speaker': 'respondent',
                                'start_position': 0,
                                'end_position': len(clean_sentence)
                            }'''

new_code = '''                        if clean_sentence and len(clean_sentence) >= 5:
                            # 查找对应的 TextNumbering 编号
                            text_number = None
                            numbered_sentence = clean_sentence
                            if text_number_mapping:
                                text_number = self._find_text_number(clean_sentence, text_number_mapping)
                                if text_number:
                                    numbered_sentence = f"{clean_sentence} [{text_number}]"
                            
                            sentence_info = {
                                'content': clean_sentence,
                                'original_content': clean_sentence,  # 保存清理后的内容
                                'paragraph_content': content[:100] + '...' if len(content) > 100 else content,
                                'filename': filename,
                                'speaker': 'respondent',
                                'start_position': 0,
                                'end_position': len(clean_sentence),
                                'text_number': text_number,  # TextNumbering 编号
                                'numbered_sentence': numbered_sentence,  # 带编号的句子
                            }'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print('✅ 2. 添加了编号查找逻辑')
else:
    print('❌ 2. 未找到sentence_info构建代码')

# 3. 在文件末尾添加 _find_text_number 方法
find_method = '''
    
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

# 检查是否已经存在这个方法
if '_find_text_number' not in content:
    content = content.rstrip() + find_method
    print('✅ 3. 添加了 _find_text_number 方法')
else:
    print('⚠️ 3. _find_text_number 方法已存在')

# 写回文件
with open(r'd:\zthree2\data_processor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('\n✅ data_processor.py 修改完成')
