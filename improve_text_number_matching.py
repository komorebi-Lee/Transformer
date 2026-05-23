"""
改进 _find_text_number 方法，提高匹配准确性
"""

with open(r'd:\zthree2\data_processor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 查找并替换整个方法
method_start = -1
method_end = -1

for i, line in enumerate(lines):
    if 'def _find_text_number' in line:
        method_start = i
    elif method_start >= 0 and line.strip() and not line.strip().startswith('#') and line.strip().startswith('def '):
        method_end = i
        break

if method_start >= 0:
    # 新的改进方法
    new_method = '''    def _find_text_number(self, text: str, text_number_mapping: Dict[int, str]) -> Optional[int]:
        """
        查找文本对应的 TextNumbering 编号（改进版：更严格的匹配）
        
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
        
        # 4. 相似度匹配（只在文本足够长时使用，避免误匹配）
        if len(text_clean) > 15:  # 提高最小长度要求
            best_match = None
            best_similarity = 0.0
            
            for num, mapped_text in text_number_mapping.items():
                mapped_clean = mapped_text.replace(' ', '').replace('\\n', '').replace('\\t', '').rstrip('。！？!?')
                
                # 计算相似度
                if len(mapped_clean) > 0:
                    # 使用更严格的相似度计算
                    common_chars = len(set(text_clean) & set(mapped_clean))
                    total_chars = max(len(text_clean), len(mapped_clean))
                    similarity = common_chars / total_chars
                    
                    # 额外检查：文本长度差异不能太大
                    length_ratio = min(len(text_clean), len(mapped_clean)) / max(len(text_clean), len(mapped_clean))
                    
                    # 只有当相似度高且长度相近时才考虑
                    if similarity > 0.9 and length_ratio > 0.8:  # 提高阈值
                        if similarity > best_similarity:
                            best_similarity = similarity
                            best_match = num
            
            if best_match is not None:
                return best_match
        
        return None

'''
    
    if method_end > 0:
        lines[method_start:method_end] = [new_method]
    else:
        # 如果是最后一个方法，找到下一个非空行
        for i in range(method_start + 1, len(lines)):
            if lines[i].strip() and not lines[i].strip().startswith('#') and not lines[i].strip().startswith('return') and not lines[i].strip().startswith('for ') and not lines[i].strip().startswith('if '):
                if lines[i][0] not in [' ', '\t']:  # 找到下一个顶层定义
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
