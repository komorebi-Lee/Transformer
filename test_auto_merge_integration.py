"""
自动合并集成测试 — 使用 陶溪川 真实数据验证 auto_code_merger。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

DATA_DIR = r"D:\c盘\新文本\润色后文件"
# 5 景漂 + 1 游客
TEST_FILES = [
    os.path.join(DATA_DIR, "陶溪川 景漂1.docx"),
    os.path.join(DATA_DIR, "陶溪川 景漂2.docx"),
    os.path.join(DATA_DIR, "陶溪川 景漂3.docx"),
    os.path.join(DATA_DIR, "陶溪川 景漂4.docx"),
    os.path.join(DATA_DIR, "陶溪川 景漂5.docx"),
    os.path.join(DATA_DIR, "陶溪川 游客1 大学生_润色版.docx"),
]


def main():
    from model_manager import EnhancedModelManager
    mm = EnhancedModelManager()
    mm.initialize_models()

    from data_processor import DataProcessor
    dp = DataProcessor()
    processed = dp.process_multiple_files(TEST_FILES)

    from enhanced_coding_generator import EnhancedCodingGenerator
    gen = EnhancedCodingGenerator()
    raw = gen.generate_grounded_theory_codes_multi_files(
        processed, mm, use_trained_model=False)

    fl = raw.get('first_level_codes', {})
    print(f"一阶编码数（合并前）: {len(fl)}")

    # 使用 config.py 中的默认阈值
    from config import Config
    bge = mm.models.get('sentence')
    concept = gen.concept_anchor_index.model if (
        hasattr(gen, 'concept_anchor_index') and gen.concept_anchor_index) else None

    if not bge or not concept:
        print(f"模型不可用: bge={bool(bge)}, concept={bool(concept)}")
        return

    from auto_code_merger import AutoCodeMerger
    merger = AutoCodeMerger(bge_model=bge, concept_model=concept)
    merged = merger.merge(dict(fl))
    reduction = len(fl) - len(merged)
    print(f"一阶编码数（合并后）: {len(merged)}")
    print(f"减少: {reduction} ({reduction/max(len(fl),1)*100:.1f}%)")

    # 显示合并示例
    removed = sorted(set(fl.keys()) - set(merged.keys()))
    if removed:
        print(f"\n被合并的编码 ({len(removed)} 个):")
        for rkey in removed[:20]:
            rc = fl[rkey][0][:35] if fl[rkey][0] else "(空)"
            print(f"  - {rkey}: {rc}")

    print(f"\n合并后编码数: {len(merged)}")
    print("完成")


if __name__ == '__main__':
    main()
