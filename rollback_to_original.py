"""
回退到集成前的状态 - 使用原有的 EnhancedCodingGenerator
"""

with open(r'd:\zthree2\main_window.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找并替换
old_code = '''        optimized_pipeline = OptimizedCodingPipeline(
            model_manager=self.model_manager,
            use_qa_classifier=True  # 启用混合策略
        )
        self.coding_generator = CodingPipelineAdapter(optimized_pipeline)
        logger.info("已启用优化流水线（混合策略，准确率92-97%）")
        # ===== 优化流水线集成完成 ====='''

new_code = '''        # ===== 使用原有的 EnhancedCodingGenerator =====
        self.coding_generator = EnhancedCodingGenerator()
        logger.info("使用原有的 EnhancedCodingGenerator")
        # ===== 回退完成 ====='''

if old_code in content:
    content = content.replace(old_code, new_code)
    print('✅ 已回退到 EnhancedCodingGenerator')
else:
    print('❌ 未找到目标代码')
    # 尝试查找变体
    if 'CodingPipelineAdapter' in content:
        print('⚠️ 找到 CodingPipelineAdapter，但格式不匹配')
    if 'EnhancedCodingGenerator' in content:
        print('⚠️ 可能已经是 EnhancedCodingGenerator')

# 写回文件
with open(r'd:\zthree2\main_window.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('完成')
