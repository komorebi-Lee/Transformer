"""
回退到集成前的状态 - 使用原有的 EnhancedCodingGenerator
"""

with open(r'd:\zthree2\main_window.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找并替换
old_code1 = '''        # ===== 使用优化流水线（完全兼容原有格式）=====
        from optimized_coding_pipeline import OptimizedCodingPipeline
        from fully_compatible_coding_adapter import FullyCompatibleCodingAdapter
        
        optimized_pipeline = OptimizedCodingPipeline(
            model_manager=self.model_manager,
            use_qa_classifier=True  # 启用混合策略
        )
        self.coding_generator = FullyCompatibleCodingAdapter(optimized_pipeline)
        logger.info("已启用优化流水线（完全兼容原有格式，准确率92-97%）")
        # ===== 集成完成 ====='''

new_code1 = '''        # ===== 使用原有的 EnhancedCodingGenerator =====
        self.coding_generator = EnhancedCodingGenerator()
        logger.info("使用原有的 EnhancedCodingGenerator")
        # ===== 回退完成 ====='''

if old_code1 in content:
    content = content.replace(old_code1, new_code1)
    print('OK: Rollback to EnhancedCodingGenerator')
else:
    print('WARN: Code not found, checking alternatives')
    if 'EnhancedCodingGenerator' in content:
        print('INFO: Already using EnhancedCodingGenerator')
    if 'FullyCompatibleCodingAdapter' in content:
        print('INFO: Found FullyCompatibleCodingAdapter')

# 写回文件
with open(r'd:\zthree2\main_window.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
