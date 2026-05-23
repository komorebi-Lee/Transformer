"""
调整匹配策略：平衡准确性和样本量
"""

with open(r'd:\zthree2\data_processor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 查找 _find_text_number 方法
method_start = -1
for i, line in enumerate(lines):
    if 'def _find_text_number' in line:
        method_start = i
        break

if method_start >= 0:
    # 新的平衡策略
    new_method = '''    def _find_text_number(self, text: str, text_number_mapping: Dict[int, str]) -> Optional[int]:
        """
        查找文本对应的 TextNumbering 编号（平衡版：保证样本量的同时提高准确性）
        
        Args:
            text: 句子文本
            text_number_mapping: {number: text} 映射
        
        Returns:
            编号或None
        """
        if not text_number_mapping:
            return None
        
        # 1. 精确匹配
        for num, mapped_text in text_number_mapping.items():
            if text == mapped_text or text == mapped_text.strip():
                return num
        
        # 2. 去除句号后精确匹配
        text_no_punct = text.rstrip('。！？!?')
        for num, mapped_text in text_number_mapping.items():
            mapped_no_punct = mapped_text.rstrip('。！？!?')
            if text_no_punct == mapped_no_punct:
                return num
        
        # 3. 去除空格和标点后精确匹配
        text_clean = text.replace(' ', '').replace('\\n', '').replace('\\t', '').rstrip('。！？!?')
        for num, mapped_text in text_number_mapping.items():
            mapped_clean = mapped_text.replace(' ', '').replace('\\n', '').replace('\\t', '').rstrip('。！？!?')
            if text_clean == mapped_clean:
                return num
        
        # 4. 智能相似度匹配（平衡准确性和样本量）
        if len(text_clean) > 10:  # 降低最小长度要求
            best_match = None
            best_similarity = 0.0
            
            for num, mapped_text in text_number_mapping.items():
                mapped_clean = mapped_text.replace(' ', '').replace('\\n', '').replace('\\t', '').rstrip('。！？!?')
                
                if len(mapped_clean) > 0:
                    # 计算字符集合相似度
                    common_chars = len(set(text_clean) & set(mapped_clean))
                    total_chars = max(len(text_clean), len(mapped_clean))
                    char_similarity = common_chars / total_chars
                    
                    # 计算长度相似度
                    length_ratio = min(len(text_clean), len(mapped_clean)) / max(len(text_clean), len(mapped_clean))
                    
                    # 计算子串匹配度（新增）
                    substring_match = 0.0
                    if text_clean in mapped_clean:
                        substring_match = len(text_clean) / len(mapped_clean)
                    elif mapped_clean in text_clean:
                        substring_match = len(mapped_clean) / len(text_clean)
                    
                    # 综合评分（考虑多个因素）
                    # 如果有子串匹配，降低其他要求
                    if substring_match > 0.7:
                        # 子串匹配度高，说明很可能是正确的
                        if char_similarity > 0.7 and length_ratio > 0.6:
                            similarity = (char_similarity + length_ratio + substring_match) / 3
                            if similarity > best_similarity:
                                best_similarity = similarity
                                best_match = num
                    else:
                        # 没有明显子串匹配，要求更严格
                        if char_similarity > 0.85 and length_ratio > 0.75:
                            similarity = (char_similarity + length_ratio) / 2
                            if similarity > best_similarity:
                                best_similarity = similarity
                                best_match = num
            
            if best_match is not None:
                return best_match
        
        return None

'''
    
    # 找到方法结束位置
    method_end = -1
    for i in range(method_start + 1, len(lines)):
        if lines[i].strip() and not lines[i].strip().startswith('#') and lines[i].strip().startswith('def '):
            method_end = i
            break
    
    if method_end > 0:
        lines[method_start:method_end] = [new_method]
    else:
        # 找到下一个顶层定义
        for i in range(method_start + 1, len(lines)):
            if lines[i].strip() and lines[i][0] not in [' ', '\t']:
                method_end = i
                break
        
        if method_end > 0:
            lines[method_start:method_end] = [new_method]
        else:
            lines[method_start:] = [new_method]
    
    print(f'OK: Replaced method at line {method_start+1}')
else:
    print('WARN: Method not found')

# 写回文件
with open(r'd:\zthree2\data_processor.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Done')
