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

    @classmethod
    def init_directories(cls):
        """初始化必要的目录"""
        PathManager.init_all_directories()