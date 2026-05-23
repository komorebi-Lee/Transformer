"""
简化测试：只测试验证逻辑
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from code_validator import validate_and_filter_codes

print('=' * 80)
print('测试编码验证逻辑')
print('=' * 80)

# 模拟 number_mapping
number_mapping = {
    1: '这是第一个句子的内容',
    2: '这是第二个句子的内容',
    3: '这是第三个句子的内容',
    100: '这是一个完全不同的句子',
}

# 模拟 structured_codes
structured_codes = {
    'C01 三阶编码1': {
        'B01 二阶编码1': [
            {
                'code_id': 'A01',
                'content': '这是第一个句子的内容',
                'sentence_details': [
                    {
                        'content': '这是第一个句子的内容',
                        'sentence_id': '1',  # 匹配
                    }
                ]
            },
            {
                'code_id': 'A02',
                'content': '这是第二个句子的内容',
                'sentence_details': [
                    {
                        'content': '这是第二个句子的内容',
                        'sentence_id': '2',  # 匹配
                    }
                ]
            },
            {
                'code_id': 'A03',
                'content': '这是一个错误的内容',
                'sentence_details': [
                    {
                        'content': '这是一个错误的内容',
                        'sentence_id': '1',  # 不匹配！内容与编号1对应的文本不同
                    }
                ]
            },
            {
                'code_id': 'A04',
                'content': '这是第三个句子的内容',
                'sentence_details': [
                    {
                        'content': '这是第三个句子的内容',
                        'sentence_id': '999',  # 编号不存在
                    }
                ]
            },
        ]
    }
}

print('\n[1] 验证前:')
print(f'  一阶编码数量: 4')
print(f'  A01: sentence_id=1, 应该匹配 ✅')
print(f'  A02: sentence_id=2, 应该匹配 ✅')
print(f'  A03: sentence_id=1, 但内容不匹配，应该删除 ❌')
print(f'  A04: sentence_id=999, 编号不存在，应该删除 ❌')

print('\n[2] 执行验证')
print('-' * 80)
filtered_codes = validate_and_filter_codes(structured_codes, number_mapping)

print('\n[3] 验证后:')
count = 0
for third_cat, second_cats in filtered_codes.items():
    for second_cat, first_contents in second_cats.items():
        count += len(first_contents)
        print(f'  保留的编码:')
        for fc in first_contents:
            code_id = fc.get('code_id')
            detail = fc.get('sentence_details', [{}])[0]
            sentence_id = detail.get('sentence_id', '')
            content = detail.get('content', '')
            print(f'    {code_id}: sentence_id={sentence_id}, content={content[:30]}...')

print(f'\n  总数: {count}')
print(f'  预期: 2 (A01, A02)')
print(f'  结果: {"✅ 正确" if count == 2 else "❌ 错误"}')

print('\n' + '=' * 80)
print('测试完成')
print('=' * 80)
