"""
对比 numbering_manager 和 data_processor 的分句方式
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from data_processor import DataProcessor
from text_numbering import TextNumberingManager

# 测试文本
test_text = """非遗的技艺，就是我们从明朝、元朝、清朝开始一直传承下来的这种技艺。它包括的方面很多，有青花，有釉下彩，有五彩，还有后来清朝的祭红，到建国瓷厂时期的"三阳开泰"，这些都涉及颜色、釉色等很多方面。至于我们景德镇的全瓷，以前在我这一辈的时候，很多人都在景德镇十大瓷厂工作。"""

print('=' * 80)
print('分句方式对比')
print('=' * 80)

# 1. numbering_manager 的分句方式
print('\n[1] TextNumberingManager.split_into_sentences()')
print('-' * 80)
numbering_manager = TextNumberingManager()
sentences1 = numbering_manager.split_into_sentences(test_text)
print(f'句子数量: {len(sentences1)}')
for i, sent in enumerate(sentences1[:5]):
    print(f'{i+1}. {sent}')

# 2. data_processor 的分句方式
print('\n[2] DataProcessor.split_into_sentences()')
print('-' * 80)
data_processor = DataProcessor()
sentences2 = data_processor.split_into_sentences(test_text)
print(f'句子数量: {len(sentences2)}')
for i, sent in enumerate(sentences2[:5]):
    print(f'{i+1}. {sent}')

# 3. 对比
print('\n[3] 对比结果')
print('-' * 80)
if len(sentences1) == len(sentences2):
    print(f'✅ 句子数量相同: {len(sentences1)}')
    
    # 检查每个句子是否相同
    all_match = True
    for i, (s1, s2) in enumerate(zip(sentences1, sentences2)):
        if s1 != s2:
            print(f'\n❌ 句子 {i+1} 不同:')
            print(f'  numbering_manager: {s1}')
            print(f'  data_processor:    {s2}')
            all_match = False
    
    if all_match:
        print('✅ 所有句子完全相同')
else:
    print(f'❌ 句子数量不同:')
    print(f'  numbering_manager: {len(sentences1)}')
    print(f'  data_processor:    {len(sentences2)}')

print('\n[4] 分句逻辑分析')
print('-' * 80)
print('numbering_manager.split_into_sentences():')
print('  - 使用正则: r\'([。！？!? \\n\\r])\'')
print('  - 保留分隔符')
print('  - 处理奇偶索引')

print('\ndata_processor.split_into_sentences():')
print('  - 使用正则: r\'[。！？!?]\'')
print('  - 不保留分隔符')
print('  - 简单分割')

print('\n结论: 两种分句方式不同，导致句子不匹配！')

print('\n' + '=' * 80)
print('测试完成')
print('=' * 80)
