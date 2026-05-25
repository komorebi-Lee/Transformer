"""
深入分析编号匹配失败的原因
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from data_processor import DataProcessor
from text_numbering import TextNumberingManager

print('=' * 80)
print('分析编号匹配失败')
print('=' * 80)

# 测试文件
test_file = r'C:\Users\33288\Downloads\新文本\润色后文件\陶阳里 非遗手艺人11.docx'

# 初始化
data_processor = DataProcessor()
numbering_manager = TextNumberingManager()

print('\n[1] 读取文件并编号')
print('-' * 80)
content = data_processor.read_file(test_file)
numbered_content, number_mapping = numbering_manager.number_text(content, 'test.docx')

# 查找编号20附近的内容
print(f'\n编号18-22的内容:')
for i in range(18, 23):
    if i in number_mapping:
        text = number_mapping[i]
        print(f'[{i}]: {text}')

print('\n[2] 处理文件')
print('-' * 80)
number_mappings = {'陶阳里 非遗手艺人11.docx': number_mapping}
processed_data = data_processor.process_multiple_files([test_file], number_mappings=number_mappings)

file_sentence_mapping = processed_data['file_sentence_mapping']
for filename, data in file_sentence_mapping.items():
    sentences = data['sentences']
    
    # 查找 text_number 为 None 的句子
    none_sentences = [s for s in sentences if s.get('text_number') is None]
    print(f'\ntext_number 为 None 的句子数: {len(none_sentences)}')
    
    if none_sentences:
        print(f'\n前5个 text_number 为 None 的句子:')
        for i, sent in enumerate(none_sentences[:5]):
            content = sent.get('content', '')
            print(f'\n句子 {i+1}:')
            print(f'  content: {content}')
            print(f'  长度: {len(content)}')
            
            # 尝试在 number_mapping 中查找
            print(f'\n  尝试匹配:')
            
            # 1. 精确匹配
            found = False
            for num, mapped_text in number_mapping.items():
                if content == mapped_text or content == mapped_text.strip():
                    print(f'    ✅ 精确匹配到编号 {num}')
                    found = True
                    break
            
            if not found:
                # 2. 去除句号后匹配
                content_no_punct = content.rstrip('。！？!?')
                for num, mapped_text in number_mapping.items():
                    mapped_no_punct = mapped_text.rstrip('。！？!?')
                    if content_no_punct == mapped_no_punct:
                        print(f'    ✅ 去除句号后匹配到编号 {num}')
                        found = True
                        break
            
            if not found:
                # 3. 检查是否包含"受访者："前缀
                if content.startswith('受访者：') or content.startswith('采访者：'):
                    print(f'    ⚠️ 内容包含角色前缀')
                    
                    # 尝试去除前缀后匹配
                    clean_content = content.replace('受访者：', '').replace('采访者：', '').strip()
                    print(f'    去除前缀后: {clean_content[:50]}...')
                    
                    for num, mapped_text in number_mapping.items():
                        if clean_content in mapped_text or mapped_text in clean_content:
                            print(f'    ⚠️ 去除前缀后可能匹配到编号 {num}')
                            print(f'       mapped_text: {mapped_text[:50]}...')
                            break
                
                # 4. 显示最相似的几个
                print(f'\n    最相似的编号:')
                content_clean = content.replace(' ', '').replace('\n', '').replace('\t', '').rstrip('。！？!?')
                similarities = []
                for num, mapped_text in number_mapping.items():
                    mapped_clean = mapped_text.replace(' ', '').replace('\n', '').replace('\t', '').rstrip('。！？!?')
                    if len(content_clean) > 10 and len(mapped_clean) > 10:
                        similarity = len(set(content_clean) & set(mapped_clean)) / max(len(content_clean), len(mapped_clean))
                        if similarity > 0.5:
                            similarities.append((num, similarity, mapped_text))
                
                similarities.sort(key=lambda x: x[1], reverse=True)
                for num, sim, text in similarities[:3]:
                    print(f'      [{num}] 相似度={sim:.2f}: {text[:50]}...')

print('\n[3] 问题分析')
print('-' * 80)
print('问题1: 内容包含"受访者："前缀')
print('  - 原因: extract_respondent_sentences 没有清理角色标记')
print('  - 解决: 在提取时去除"受访者："和"采访者："前缀')

print('\n问题2: 编号匹配失败')
print('  - 原因: 句子内容与 number_mapping 中的文本不匹配')
print('  - 解决: 改进 _find_text_number 的匹配逻辑')

print('\n' + '=' * 80)
print('分析完成')
print('=' * 80)
