
import os

class Config:
    """应用程序配置 - 降级版本"""

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # 目录配置
    LOCAL_MODELS_DIR = os.path.join(BASE_DIR, "local_models")
    TRAINED_MODELS_DIR = os.path.join(BASE_DIR, "trained_models")
    STANDARD_ANSWERS_DIR = os.path.join(BASE_DIR, "standard_answers")
    DATA_DIR = os.path.join(BASE_DIR, "data")

    # 模型配置
    DEFAULT_MODEL_NAME = "bert-base-chinese"
    SENTENCE_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

    # 训练配置
    TRAINING_EPOCHS = 3
    BATCH_SIZE = 8
    LEARNING_RATE = 2e-5

    # 编码配置
    MAX_SENTENCE_LENGTH = 256
    SIMILARITY_THRESHOLD = 0.5
    MIN_SENTENCE_LENGTH = 5

    @classmethod
    def init_directories(cls):
        """初始化必要的目录"""
        directories = [
            cls.LOCAL_MODELS_DIR,
            cls.TRAINED_MODELS_DIR,
            cls.STANDARD_ANSWERS_DIR,
            cls.DATA_DIR
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"确保目录存在: {directory}")
