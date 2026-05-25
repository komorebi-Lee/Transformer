"""
测试优化流水线的编码生成
"""

import sys
sys.path.insert(0, r'D:\zthree2')

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from optimized_coding_pipeline import OptimizedCodingPipeline
from model_manager import EnhancedModelManager

# 测试文件
test_file = r'C:\Users\33288\Downloads\新文本\润色后文件\陶阳里 非遗手艺人11.docx'

print('=' * 80)
print('测试优化流水线编码生成')
print('=' * 80)

# 创建流水线
model_manager = EnhancedModelManager()
pipeline = OptimizedCodingPipeline(
    model_manager=model_manager,
    use_qa_classifier=True
)

print('\n处理文件...')
results = pipeline.process_file(test_file, adaptive=True)

print(f'\n结果统计:')
print(f'  总提取: {len(results)} 条')

has_code = sum(1 for r in results if r.get('selected_candidate'))
print(f'  有编码: {has_code} 条')
print(f'  空编码: {len(results) - has_code} 条')

if has_code > 0:
    print(f'\n✅ 编码生成成功')
    print(f'\n前3条示例:')
    for i, r in enumerate(results[:3]):
        if r.get('selected_candidate'):
            print(f'  [{i+1}] {r.get("method")}')
            print(f'      原文: {r.get("text", "")[:50]}...')
            print(f'      编码: {r.get("selected_candidate", "")[:40]}')
else:
    print(f'\n❌ 编码生成失败 - 所有编码都是空的')
    print(f'\n调试信息:')
    if results:
        r = results[0]
        print(f'  text: {r.get("text", "")[:50]}')
        print(f'  speaker: {r.get("speaker")}')
        print(f'  method: {r.get("method")}')
        print(f'  selected_candidate: {r.get("selected_candidate")}')
        print(f'  candidates: {r.get("candidates", [])}')
