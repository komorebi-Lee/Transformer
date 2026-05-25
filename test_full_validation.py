"""
测试完整的验证流程（模拟主程序）
"""

import sys
sys.path.insert(0, r'D:\zthree2')

from PyQt5.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import Qt

print('=' * 80)
print('测试完整的验证流程')
print('=' * 80)

# 创建 QApplication（必需）
app = QApplication(sys.argv)

# 创建模拟的编码树
coding_tree = QTreeWidget()
coding_tree.setColumnCount(6)

# 模拟 number_mapping
number_mapping = {
    3174: '今天就调到明天',
    3175: '这是另一个句子',
}

# 模拟 structured_codes
structured_codes = {
    'C01 三阶编码': {
        'B01 二阶编码': [
            {
                'code_id': 'A682',
                'content': '今天就调到明',
                'sentence_details': [
                    {
                        'content': '今天就调到明',
                        'sentence_id': '3174',
                    }
                ]
            }
        ]
    }
}

# 添加到编码树
third_item = QTreeWidgetItem(coding_tree)
third_item.setText(0, 'C01 三阶编码')
third_item.setData(0, Qt.UserRole, {'level': 3})

second_item = QTreeWidgetItem(third_item)
second_item.setText(0, 'B01 二阶编码')
second_item.setData(0, Qt.UserRole, {'level': 2})

first_item = QTreeWidgetItem(second_item)
first_item.setText(0, 'A682: 今天就调到明')
first_item.setText(5, '3174')  # 关联编号
first_item.setData(0, Qt.UserRole, {
    'level': 1,
    'code_id': 'A682',
    'sentence_details': [
        {
            'content': '今天就调到明',
            'sentence_id': '3174',
        }
    ]
})

print('\n[1] 编码树创建完成')
print(f'  一阶编码: A682')
print(f'  关联编号: {first_item.text(5)}')
print(f'  原始文本: 今天就调到明')

print('\n[2] 执行验证')
print('-' * 80)

try:
    from code_validator_tree import validate_and_filter_codes_by_tree
    
    filtered_codes = validate_and_filter_codes_by_tree(
        coding_tree,
        structured_codes,
        number_mapping
    )
    
    print('\n[3] 验证完成')
    print(f'  结果: {filtered_codes}')
    
    # 检查是否保留
    if 'C01 三阶编码' in filtered_codes:
        print('  ✅ A682 被保留（匹配成功）')
    else:
        print('  ❌ A682 被删除（匹配失败）')
    
except Exception as e:
    print(f'\n❌ 验证失败: {e}')
    import traceback
    traceback.print_exc()

print('\n' + '=' * 80)
print('测试完成')
print('=' * 80)
