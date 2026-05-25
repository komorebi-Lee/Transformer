"""
测试主程序集成后的一阶编码质量
评估标准：
1. 是否正确识别受访者
2. 一阶编码质量
3. 准确率统计
"""

import sys
sys.path.insert(0, r'D:\zthree2')

import logging
from pathlib import Path
from coding_pipeline_adapter import CodingPipelineAdapter
from optimized_coding_pipeline import OptimizedCodingPipeline
from model_manager import EnhancedModelManager

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 测试文件
test_files = [
    r'C:\Users\33288\Downloads\新文本\润色后文件\陶阳里 管理层3（里弄管家）.docx',
    r'C:\Users\33288\Downloads\新文本\润色后文件\陶阳里 非遗手艺人11.docx',
    r'C:\Users\33288\Downloads\新文本\润色后文件\陶阳里 非遗手艺人12.docx',
    r'C:\Users\33288\Downloads\新文本\润色后文件\陶溪川 游客8.docx',
    r'C:\Users\33288\Downloads\新文本\润色后文件\陶阳里 非遗人10.docx',
    r'C:\Users\33288\Downloads\新文本\润色后文件\陶阳里 非遗手艺人 9.docx',
    r'C:\Users\33288\Downloads\新文本\润色后文件\陶溪川 景漂6 广州美术学院_润色版.docx'
]

print('=' * 80)
print('主程序集成测试：一阶编码质量评估')
print('=' * 80)

# 模拟主程序初始化
print('\n[1/3] 初始化管理器（模拟主程序）')
model_manager = EnhancedModelManager()

# 创建优化流水线（与主程序相同）
optimized_pipeline = OptimizedCodingPipeline(
    model_manager=model_manager,
    use_qa_classifier=True  # 启用混合策略
)

# 创建适配器（与主程序相同）
coding_generator = CodingPipelineAdapter(optimized_pipeline)
print('✅ 管理器初始化完成')

# 生成编码（模拟主程序调用）
print('\n[2/3] 生成编码（模拟主程序调用）')
print('调用: coding_generator.generate_grounded_theory_codes_multi_files()')

results = coding_generator.generate_grounded_theory_codes_multi_files(
    test_files,
    adaptive=True  # 启用混合策略
)

print(f'✅ 编码生成完成')

# 评估质量
print('\n[3/3] 评估一阶编码质量')
print('=' * 80)

all_stats = []

for file_path in test_files:
    file_name = Path(file_path).name
    codes = results.get(file_name, [])
    
    if not codes:
        print(f'\n❌ {file_name}: 无编码结果')
        continue
    
    print(f'\n📄 {file_name}')
    print('-' * 80)
    
    # 统计
    total = len(codes)
    has_code = sum(1 for c in codes if c.get('code'))
    empty_code = total - has_code
    
    # 方法分布
    methods = {}
    for c in codes:
        m = c.get('method', 'unknown')
        methods[m] = methods.get(m, 0) + 1
    
    # 置信度统计
    confidences = [c.get('confidence', 0.0) for c in codes]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    high_conf = sum(1 for c in confidences if c >= 0.9)
    mid_conf = sum(1 for c in confidences if 0.7 <= c < 0.9)
    low_conf = sum(1 for c in confidences if c < 0.7)
    
    # 受访者识别评估
    # 检查是否所有编码都来自受访者（speaker字段或method字段）
    respondent_count = 0
    interviewer_count = 0
    unknown_count = 0
    
    for c in codes:
        speaker = c.get('speaker', '') or ''  # 处理None
        text = c.get('text', '')
        
        # 判断是否是受访者
        if 'respondent' in speaker.lower() or 'speaker_' in speaker:
            respondent_count += 1
        elif 'interviewer' in speaker.lower() or '采访者' in text[:20]:
            interviewer_count += 1
        else:
            # 根据method判断
            method = c.get('method', '')
            if method in ['rule_explicit', 'rule_inferred', 'rule_keyword', 'model_qa_classifier']:
                respondent_count += 1
            else:
                unknown_count += 1
    
    # 受访者识别准确率（应该100%是受访者）
    respondent_accuracy = (respondent_count / total * 100) if total > 0 else 0
    
    print(f'总提取: {total} 条')
    print(f'有编码: {has_code} 条 | 空编码: {empty_code} 条 ({empty_code/total*100:.1f}%)')
    print(f'平均置信度: {avg_conf:.2f}')
    print(f'置信度分布: 高(≥0.9):{high_conf} | 中(0.7-0.9):{mid_conf} | 低(<0.7):{low_conf}')
    
    print(f'\n受访者识别:')
    print(f'  受访者: {respondent_count} ({respondent_accuracy:.1f}%)')
    if interviewer_count > 0:
        print(f'  ⚠️ 采访者: {interviewer_count} ({interviewer_count/total*100:.1f}%) - 应该为0')
    if unknown_count > 0:
        print(f'  ⚠️ 未知: {unknown_count} ({unknown_count/total*100:.1f}%)')
    
    print(f'\n识别方法:')
    for method, count in sorted(methods.items()):
        print(f'  {method}: {count} ({count/total*100:.1f}%)')
    
    # 示例编码
    print(f'\n前3条示例:')
    for i, c in enumerate(codes[:3]):
        text = c.get('text', '')[:50]
        code = c.get('code', '')[:40]
        conf = c.get('confidence', 0.0)
        method = c.get('method', 'unknown')
        print(f'  [{i+1}] {method} | 置信度:{conf:.2f}')
        print(f'      原文: {text}...')
        print(f'      编码: {code}')
    
    # 保存统计
    all_stats.append({
        'file': file_name,
        'total': total,
        'has_code': has_code,
        'empty_code': empty_code,
        'avg_conf': avg_conf,
        'respondent_accuracy': respondent_accuracy,
        'interviewer_count': interviewer_count,
        'methods': methods
    })

# 总体统计
print('\n' + '=' * 80)
print('总体统计')
print('=' * 80)

total_files = len(all_stats)
total_codes = sum(s['total'] for s in all_stats)
total_has_code = sum(s['has_code'] for s in all_stats)
total_empty = sum(s['empty_code'] for s in all_stats)
avg_conf_all = sum(s['avg_conf'] * s['total'] for s in all_stats) / total_codes if total_codes > 0 else 0
avg_respondent_acc = sum(s['respondent_accuracy'] for s in all_stats) / total_files if total_files > 0 else 0

# 方法分布汇总
all_methods = {}
for s in all_stats:
    for method, count in s['methods'].items():
        all_methods[method] = all_methods.get(method, 0) + count

print(f'总文件: {total_files}')
print(f'总提取: {total_codes} 条')
print(f'有编码: {total_has_code} 条 | 空编码: {total_empty} 条 ({total_empty/total_codes*100:.1f}%)')
print(f'平均置信度: {avg_conf_all:.2f}')
print(f'受访者识别准确率: {avg_respondent_acc:.1f}%')

print(f'\n方法分布:')
for method, count in sorted(all_methods.items()):
    print(f'  {method}: {count} ({count/total_codes*100:.1f}%)')

# 问题检测
print(f'\n问题检测:')
issues = []
for s in all_stats:
    if s['interviewer_count'] > 0:
        issues.append(f"  ⚠️ {s['file']}: 包含{s['interviewer_count']}条采访者语句（应该为0）")
    if s['respondent_accuracy'] < 95:
        issues.append(f"  ⚠️ {s['file']}: 受访者识别准确率{s['respondent_accuracy']:.1f}%（应该≥95%）")

if issues:
    for issue in issues:
        print(issue)
else:
    print('  ✅ 无问题检测到')

# 质量评分
print(f'\n质量评分:')
score = 0

# 受访者识别准确率（40分）
if avg_respondent_acc >= 98:
    score += 40
    print(f'  受访者识别: 40/40 (准确率{avg_respondent_acc:.1f}%)')
elif avg_respondent_acc >= 95:
    score += 35
    print(f'  受访者识别: 35/40 (准确率{avg_respondent_acc:.1f}%)')
else:
    score += 30
    print(f'  受访者识别: 30/40 (准确率{avg_respondent_acc:.1f}%)')

# 编码覆盖率（30分）
coverage = (total_has_code / total_codes * 100) if total_codes > 0 else 0
if coverage >= 90:
    score += 30
    print(f'  编码覆盖率: 30/30 (覆盖率{coverage:.1f}%)')
elif coverage >= 85:
    score += 25
    print(f'  编码覆盖率: 25/30 (覆盖率{coverage:.1f}%)')
else:
    score += 20
    print(f'  编码覆盖率: 20/30 (覆盖率{coverage:.1f}%)')

# 置信度（30分）
if avg_conf_all >= 0.9:
    score += 30
    print(f'  平均置信度: 30/30 (置信度{avg_conf_all:.2f})')
elif avg_conf_all >= 0.8:
    score += 25
    print(f'  平均置信度: 25/30 (置信度{avg_conf_all:.2f})')
else:
    score += 20
    print(f'  平均置信度: 20/30 (置信度{avg_conf_all:.2f})')

print(f'\n总分: {score}/100')

if score >= 90:
    grade = 'A (优秀)'
elif score >= 80:
    grade = 'B (良好)'
elif score >= 70:
    grade = 'C (合格)'
else:
    grade = 'D (需改进)'

print(f'评级: {grade}')

print('\n' + '=' * 80)
print('测试完成')
print('=' * 80)
