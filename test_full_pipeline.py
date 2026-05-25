"""
完整测试主程序调用流程
模拟主程序的完整调用链
"""

import sys
sys.path.insert(0, r'D:\zthree2')

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

from data_processor import DataProcessor
from coding_pipeline_adapter import CodingPipelineAdapter
from optimized_coding_pipeline import OptimizedCodingPipeline
from grounded_theory_coder import GroundedTheoryCoder
from model_manager import EnhancedModelManager

print('=' * 80)
print('完整测试主程序调用流程')
print('=' * 80)

# 测试文件
test_files = [
    r'C:\Users\33288\Downloads\新文本\润色后文件\陶阳里 非遗手艺人11.docx'
]

print('\n[1/5] 初始化管理器')
model_manager = EnhancedModelManager()
data_processor = DataProcessor()

# 创建优化流水线和适配器
optimized_pipeline = OptimizedCodingPipeline(
    model_manager=model_manager,
    use_qa_classifier=True
)
coding_generator = CodingPipelineAdapter(optimized_pipeline)

grounded_coder = GroundedTheoryCoder()

print('✅ 管理器初始化完成')

print('\n[2/5] 处理文件数据')
processed_data = data_processor.process_multiple_files(test_files)
print(f'✅ 处理完成: {processed_data["total_files"]} 个文件')

print('\n[3/5] 生成编码')
raw_codes = coding_generator.generate_grounded_theory_codes_multi_files(
    processed_data,
    model_manager,
    progress_callback=None,
    use_trained_model=False,
    coding_thresholds=None
)

print(f'\n返回的 raw_codes 格式:')
print(f'  类型: {type(raw_codes)}')
print(f'  键: {list(raw_codes.keys())}')

if '一阶编码' in raw_codes:
    first_level = raw_codes['一阶编码']
    print(f'  一阶编码数量: {len(first_level)}')
    
    if first_level:
        # 显示第一条
        first_key = list(first_level.keys())[0]
        first_value = first_level[first_key]
        print(f'\n  第一条示例:')
        print(f'    键: {first_key}')
        print(f'    编码: {first_value[0][:40]}')
        print(f'    原文: {first_value[1][:50]}...')
    else:
        print(f'\n  ❌ 一阶编码为空！')
else:
    print(f'\n  ❌ 没有"一阶编码"键！')

print('\n[4/5] 构建编码结构')
try:
    structured_codes = grounded_coder.build_coding_structure(raw_codes)
    print(f'✅ 编码结构构建完成')
    print(f'  结构: {type(structured_codes)}')
    print(f'  键: {list(structured_codes.keys()) if isinstance(structured_codes, dict) else "非字典"}')
except Exception as e:
    print(f'❌ 构建失败: {e}')
    import traceback
    traceback.print_exc()

print('\n[5/5] 总结')
if '一阶编码' in raw_codes and len(raw_codes['一阶编码']) > 0:
    print('✅ 编码生成成功')
    print('✅ 格式转换正确')
    print('✅ 应该可以在主程序中显示')
else:
    print('❌ 编码生成失败或为空')

print('\n' + '=' * 80)
print('测试完成')
print('=' * 80)
