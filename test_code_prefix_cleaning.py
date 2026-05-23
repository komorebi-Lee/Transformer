"""
测试一阶编码开头标点符号清理
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from enhanced_coding_generator import EnhancedCodingGenerator

print('=' * 80)
print('测试一阶编码开头标点符号清理')
print('=' * 80)

# 测试清理方法
test_cases = [
    '●初级阶段的问题，那些都会作为问题的',
    '○这是一个测试',
    '、开头有顿号',
    '。开头有句号',
    '"引号开头的内容"应该保留',
    '"这是引号"后面的内容',
    '   前面有空格',
    '正常的编码内容',
    '●○◆多个符号',
]

print('\n测试 _clean_code_prefix 方法:')
print('-' * 80)

for i, test in enumerate(test_cases):
    cleaned = EnhancedCodingGenerator._clean_code_prefix(test)
    status = '✅' if cleaned != test else '→'
    print(f'{i+1}. {status}')
    print(f'   原始: {test}')
    print(f'   清理: {cleaned}')
    print()

print('=' * 80)
print('测试完成')
print('=' * 80)
