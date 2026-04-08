import os
import sys
import logging
from typing import Dict, Any
from path_manager import PathManager


class Config:
    """应用程序配置"""

    # 基础路径 - 使用 PathManager 统一管理
    BASE_DIR = PathManager.get_base_dir()

    # 目录配置 - 使用 PathManager 获取路径
    LOCAL_MODELS_DIR = PathManager.get_local_models_dir()
    TRAINED_MODELS_DIR = PathManager.get_trained_models_dir()
    STANDARD_ANSWERS_DIR = PathManager.get_standard_answers_dir()
    DATA_DIR = PathManager.get_data_dir()
    PROJECTS_DIR = PathManager.get_projects_dir()

    # 模型配置
    DEFAULT_MODEL_NAME = "bert-base-chinese"
    SENTENCE_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

    # 训练配置
    TRAINING_EPOCHS = 10
    BATCH_SIZE = 16
    LEARNING_RATE = 2e-5

    # 编码配置
    MAX_SENTENCE_LENGTH = 512
    SIMILARITY_THRESHOLD = 0.6
    MIN_SENTENCE_LENGTH = 5
    # 一阶编码最大长度：默认30；设为0表示不限制长度（便于对比是否仍出现断句）
    FIRST_LEVEL_CODE_MAX_LENGTH = 30

    # 一阶抽象（抽取式）重排序模型配置
    # 该模型用于在“候选子句片段”中选择最接近人工抽象的一段（不负责改写）
    ENABLE_ABSTRACT_RERANKER = True
    ABSTRACT_RERANKER_DIRNAME = "abstract_reranker_latest"
    ABSTRACT_RERANK_MAX_SPAN_LEN = 8
    ABSTRACT_RERANK_NEGATIVE_SAMPLES = 4
    # 抽象重排序训练策略：默认仅在模型缺失时训练（可大幅减少重复训练耗时）
    ABSTRACT_RERANKER_ALWAYS_RETRAIN = False

    # BERT微调配置
    FINETUNE_LEARNING_RATE = 2e-5
    FINETUNE_EPOCHS = 3
    FINETUNE_BATCH_SIZE = 16
    FINETUNE_WARMUP_RATIO = 0.1
    FINETUNE_WEIGHT_DECAY = 0.01
    FINETUNE_EARLY_STOP_PATIENCE = 3
    FINETUNE_MAX_GRAD_NORM = 1.0
    FINETUNE_DROPOUT_RATE = 0.1

    # 训练模式
    TRAINING_MODE_CLASSIFIER = "classifier"
    TRAINING_MODE_BERT_FINETUNE = "bert_finetune"
    TRAINING_MODE_INCREMENTAL = "incremental"

    # 超参数寻优配置
    HYPERPARAM_SEARCH_SPACE = {
        "learning_rate": [1e-5, 2e-5, 5e-5],
        "batch_size": [8, 16, 32],
        "epochs": [2, 3, 5],
        "dropout_rate": [0.1, 0.2, 0.3]
    }
    HYPERPARAM_SEARCH_METHOD = "grid"
    HYPERPARAM_CV_FOLDS = 3

    # 增量训练配置
    INCREMENTAL_LEARNING_RATE_RATIO = 0.5
    INCREMENTAL_MIN_SAMPLES = 10

    @classmethod
    def init_directories(cls):
        """初始化必要的目录"""
        PathManager.init_all_directories()