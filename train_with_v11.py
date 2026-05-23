"""
使用 v11 标准答案训练一阶抽象重排序模型。

用法: python train_with_v11.py
"""
import json
import logging
import os
import sys

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

V11_PATH = r"C:\Users\Lenovo\Documents\xwechat_files\wxid_eo5dkcv3sf7522_8ac6\msg\file\2026-05\v11_20260428_164754.json"


def main():
    # 1. 加载标准答案
    logger.info("加载 v11 标准答案...")
    with open(V11_PATH, 'r', encoding='utf-8') as f:
        standard_answers = json.load(f)

    training_data = standard_answers.get('training_data', [])
    logger.info(f"标准答案加载完成: {len(training_data)} 条训练数据")
    unique_abstracts = len(set(item['target_abstract'] for item in training_data))
    logger.info(f"唯一一阶编码数: {unique_abstracts}")

    # 2. 初始化模型管理器
    from model_manager import EnhancedModelManager
    logger.info("初始化模型管理器...")
    model_manager = EnhancedModelManager()

    # 3. 训练
    from train_abstract_reranker import train_abstract_reranker

    def progress_callback(cur, total, loss):
        if total:
            pct = int(cur / total * 100)
            logger.info(f"训练进度: {pct}% (step {cur}/{total}), loss={loss:.4f}")

    def finished_callback(success, message):
        logger.info(f"训练{'成功' if success else '失败'}: {message}")

    logger.info("开始训练抽象重排序模型...")
    ok, output_dir, message = train_abstract_reranker(
        standard_answers,
        model_manager,
        progress_callback=progress_callback,
        finished_callback=finished_callback,
    )

    if ok:
        logger.info(f"训练完成! 模型已保存到: {output_dir}")

        # 加载新模型
        if hasattr(model_manager, 'load_abstract_reranker_model'):
            model_manager.load_abstract_reranker_model(output_dir)
            logger.info("新模型已加载到内存")
    else:
        logger.error(f"训练失败: {message}")
        sys.exit(1)


if __name__ == '__main__':
    main()
