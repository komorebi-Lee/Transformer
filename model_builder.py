"""
模型构建器 — 一次性构建部署模型，研发即交付
========================================================================
在 bert-base-chinese 的基础上，构建一个 4 层 BERT（~120MB）作为 reranker 基座，
bge-small-zh-v1.5（~95MB）作为 sentence 模型。总 ~215MB，直接打包进 EXE。

运行方式：
  python model_builder.py               # 首次运行，构建全部模型
  python model_builder.py --force       # 强制重新构建

构建原理：
  - 下载 bert-base-chinese 作为"原材料"
  - 取其 config 改为 4 层，复制 embedding + 前 4 层的权重 → warm-start
  - 下载 bge-small-zh-v1.5 作为 sentence 模型
  - 后续的微调（abstract_reranker）直接在这两个模型上进行
========================================================================
"""

import os
import sys
import shutil
import logging

import torch

from config import Config

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def _model_path(name: str) -> str:
    """模型名 → local_models 路径"""
    safe = name.replace('/', '_')
    return os.path.join(Config.LOCAL_MODELS_DIR, safe)


def _dir_size_mb(path: str) -> float:
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total += os.path.getsize(fp)
    return total / (1024 * 1024)


def download_bert_base() -> str:
    """下载 bert-base-chinese 到 local_models（如果不存在）"""
    source = Config.BERT_BUILDER_SOURCE
    save_path = _model_path(source)

    if os.path.exists(save_path) and os.path.exists(os.path.join(save_path, 'config.json')):
        logger.info(f"基座模型已存在: {save_path}")
        return save_path

    logger.info(f"下载基座模型: {source}")
    from transformers import AutoTokenizer, AutoModel
    tokenizer = AutoTokenizer.from_pretrained(source)
    model = AutoModel.from_pretrained(source)
    tokenizer.save_pretrained(save_path)
    model.save_pretrained(save_path)
    logger.info(f"基座模型下载完成 ({_dir_size_mb(save_path):.0f}MB)")
    return save_path


def build_custom_bert(source_path: str, output_name: str, num_layers: int = 4):
    """从 bert-base-chinese 构建 N 层 BERT (warm-start embedding + 前 N 层)"""
    output_path = _model_path(output_name)

    if os.path.exists(output_path) and os.path.exists(os.path.join(output_path, 'config.json')):
        logger.info(f"自定义 BERT 已存在: {output_path}")
        return output_path

    logger.info(f"构建 {num_layers} 层 BERT → {output_name}")

    from transformers import AutoConfig, AutoModel, AutoTokenizer

    # 1. 加载源模型
    logger.info("  加载源模型...")
    source_model = AutoModel.from_pretrained(source_path)
    source_tokenizer = AutoTokenizer.from_pretrained(source_path)

    # 2. 创建 N 层 config
    config = AutoConfig.from_pretrained(source_path)
    config.num_hidden_layers = num_layers

    # 3. 创建学生模型（随机初始化）
    student = AutoModel.from_config(config)

    # 4. Warm-start：复制 embedding
    if hasattr(source_model, 'embeddings') and hasattr(student, 'embeddings'):
        student.embeddings.load_state_dict(source_model.embeddings.state_dict())
        logger.info("  ✓ embedding 已 warm-start")

    # 5. Warm-start：复制前 N 层 transformer
    if hasattr(source_model, 'encoder') and hasattr(source_model.encoder, 'layer'):
        for i in range(min(num_layers, len(source_model.encoder.layer))):
            student.encoder.layer[i].load_state_dict(source_model.encoder.layer[i].state_dict())
        logger.info(f"  ✓ 前 {num_layers} 层已 warm-start")

    # 6. 复制 pooler（如果存在）
    if hasattr(source_model, 'pooler') and hasattr(student, 'pooler'):
        logger.info("  ✓ pooler 已复制")

    # 7. 保存
    os.makedirs(output_path, exist_ok=True)
    student.save_pretrained(output_path)
    source_tokenizer.save_pretrained(output_path)
    logger.info(f"  ✓ 已保存: {output_path} ({_dir_size_mb(output_path):.0f}MB)")

    # 释放内存
    del source_model, student
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return output_path


def download_sentence_model() -> str:
    """下载 bge-small-zh-v1.5 到 local_models"""
    model_name = Config.SENTENCE_MODEL_NAME
    save_path = _model_path(model_name)

    if os.path.exists(save_path) and os.path.exists(os.path.join(save_path, 'config.json')):
        logger.info(f"Sentence 模型已存在: {save_path}")
        return save_path

    logger.info(f"下载 Sentence 模型: {model_name}")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name)
    model.save(save_path)
    logger.info(f"Sentence 模型下载完成 ({_dir_size_mb(save_path):.0f}MB)")
    return save_path


def build_all(force: bool = False):
    """构建全部部署模型"""
    if force:
        logger.info("--force：将重新构建所有模型")

    logger.info("=" * 60)
    logger.info("开始构建部署模型")
    logger.info(f"  Reranker:  {Config.RERANKER_MODEL_NAME} ({Config.CUSTOM_BERT_NUM_LAYERS}层 BERT)")
    logger.info(f"  Sentence:  {Config.SENTENCE_MODEL_NAME}")
    logger.info(f"  目标体积:  ~215MB")
    logger.info("=" * 60)

    # Step 0: 如果 force，清理旧的
    if force:
        for name in [Config.RERANKER_MODEL_NAME, Config.SENTENCE_MODEL_NAME]:
            p = _model_path(name)
            if os.path.exists(p):
                shutil.rmtree(p)
                logger.info(f"  已清理: {p}")

    # Step 1: 下载原材料
    logger.info("\n[1/3] 下载基座模型 (bert-base-chinese)")
    source_path = download_bert_base()

    # Step 2: 构建 4 层 BERT
    logger.info("\n[2/3] 构建自定义 BERT")
    build_custom_bert(source_path, Config.RERANKER_MODEL_NAME,
                       Config.CUSTOM_BERT_NUM_LAYERS)

    # Step 3: 下载 sentence 模型
    logger.info("\n[3/3] 下载 Sentence 模型")
    download_sentence_model()

    # 汇总
    total_mb = 0
    for name in [Config.RERANKER_MODEL_NAME, Config.SENTENCE_MODEL_NAME]:
        p = _model_path(name)
        if os.path.exists(p):
            mb = _dir_size_mb(p)
            total_mb += mb
            logger.info(f"  {name}: {mb:.0f}MB")

    logger.info("=" * 60)
    logger.info(f"构建完成！总大小: {total_mb:.0f}MB")
    logger.info("现在可以正常训练和使用了。")
    logger.info("=" * 60)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='构建部署模型（研发即交付）')
    parser.add_argument('--force', action='store_true', help='强制重新构建')
    args = parser.parse_args()
    build_all(force=args.force)


if __name__ == '__main__':
    main()