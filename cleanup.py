# 创建一个清理脚本 cleanup.py
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def cleanup_corrupted_models():
    """清理损坏的训练模型文件"""
    trained_models_dir = "trained_models"

    if not os.path.exists(trained_models_dir):
        logger.info("trained_models 目录不存在")
        return

    model_files = [f for f in os.listdir(trained_models_dir) if f.endswith('.pkl')]

    for model_file in model_files:
        file_path = os.path.join(trained_models_dir, model_file)
        file_size = os.path.getsize(file_path)

        if file_size == 0:
            logger.info(f"删除空文件: {model_file}")
            os.remove(file_path)
        else:
            logger.info(f"保留文件: {model_file} (大小: {file_size} bytes)")


if __name__ == "__main__":
    cleanup_corrupted_models()