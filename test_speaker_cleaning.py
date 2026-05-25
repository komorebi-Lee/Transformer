"""
测试说话人标记清理
"""
import re

# 测试各种情况
test_cases = [
    '说话人2：这是一个测试句子',
    '说话人2这是一个测试句子',  # 无冒号
    '说话人2 这是一个测试句子',  # 空格
    '说话人2: 这是一个测试句子',  # 英文冒号
]

pattern = r'^[\w\u4e00-\u9fa5]+\d+[：:]?\s*'

print('测试当前的清理逻辑:')
print('=' * 60)

for text in test_cases:
    result = re.sub(pattern, '', text)
    success = '说话人2' not in result
    print(f'原文: {text}')
    print(f'清理后: {result}')
    print(f'成功: {success}')
    print()
