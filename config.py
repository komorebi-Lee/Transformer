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

    # =========================================================================
    # 模型配置 — 研发即交付：直接在轻量架构上训练，跳过蒸馏
    # =========================================================================
    # 策略：用 bert-base-chinese 的 embedding + 前4层构建轻量 BERT，直接微调；
    #       sentence 用 bge-small-zh-v1.5，中文语义更强、推理更快。
    #       model_builder.py 负责一次性构建这些模型。
    # -----------------------------------------------------------------
    RERANKER_MODEL_NAME = "custom_bert_4layer"          # 4 层 BERT（~120MB）
    SENTENCE_MODEL_NAME  = "bge-small-zh-v1.5"          # BGE 中文小模型（~95MB）
    # 构建 4 层 BERT 时用的基座（仅用于提取 config + embedding + 前 N 层）
    BERT_BUILDER_SOURCE = "bert-base-chinese"
    CUSTOM_BERT_NUM_LAYERS = 4
    # -----------------------------------------------------------------
    # 向下兼容
    # -----------------------------------------------------------------
    DEFAULT_MODEL_NAME = RERANKER_MODEL_NAME
    # 蒸馏相关配置（保留但不再使用，仅防旧代码引用崩溃）
    MODEL_TIER = "standard"
    ENHANCED_RERANKER_MODEL = RERANKER_MODEL_NAME
    ENHANCED_SENTENCE_MODEL = SENTENCE_MODEL_NAME
    STANDARD_RERANKER_MODEL = RERANKER_MODEL_NAME
    STANDARD_SENTENCE_MODEL = SENTENCE_MODEL_NAME
    LIGHT_RERANKER_MODEL = RERANKER_MODEL_NAME
    LIGHT_SENTENCE_MODEL = SENTENCE_MODEL_NAME
    DISTILL_STUDENT_LAYERS = 3
    DISTILL_TEMPERATURE = 4.0
    DISTILL_ALPHA = 0.7
    DISTILL_EPOCHS = 5
    DISTILL_BATCH_SIZE = 16
    DISTILL_LEARNING_RATE = 3e-5
    DISTILL_OUTPUT_DIRNAME = "distilled_models"

    # 训练配置
    TRAINING_EPOCHS = 10
    BATCH_SIZE = 16
    LEARNING_RATE = 2e-5

    # 编码配置
    MAX_SENTENCE_LENGTH = 512
    SIMILARITY_THRESHOLD = 0.6
    MIN_SENTENCE_LENGTH = 5
    # 一阶编码最大长度：默认30；设为0表示不限制长度（便于对比是否仍出现断句）
    FIRST_LEVEL_CODE_MAX_LENGTH = 36
    # ── 句子切分模式 ──
    # "punctuation": 按句号/叹号/问号切分（原行为）
    # "speaker_block": 按说话人块切分，合并同说话人连续段落
    SENTENCE_SPLIT_MODE = "speaker_block"
    # speaker_block 模式下最大句子字符数，超过则兜底切分
    SENTENCE_MAX_LENGTH = 500
    # RAG 自动编码配置
    ENABLE_RAG_CODING = True
    RAG_INDEX_DIR = os.path.join(BASE_DIR, "cache", "rag_index")
    RAG_TOKEN_TOP_K = 80
    RAG_VECTOR_TOP_K = 10
    RAG_FINAL_TOP_K = 5
    RAG_SECOND_LEVEL_THRESHOLD = 0.40
    RAG_SECOND_LEVEL_MARGIN = 0.03
    RAG_THIRD_LEVEL_THRESHOLD = 0.40
    RAG_THIRD_LEVEL_MARGIN = 0.03
    RAG_MIN_CLUSTER_SUPPORT = 1
    RAG_CLUSTER_SIMILARITY_THRESHOLD = 0.76
    RAG_MAX_EMBEDDING_CACHE_SIZE = 10000
    RAG_OTHER_SECOND_LEVEL_NAME = "其他各类话题"
    RAG_OTHER_THIRD_LEVEL_NAME = "其他重要维度"
    RAG_AUTO_REFRESH_INDEX = True
    RAG_INDEX_REBUILD_MODE = "lazy"
    RAG_RUNTIME_STRATEGY = "auto"
    RAG_GPU_BATCH_SIZE = 128
    RAG_CPU_BATCH_SIZE = 32
    RAG_LIGHT_BATCH_SIZE = 8
    RAG_LIGHT_TOKEN_TOP_K = 30
    RAG_LIGHT_VECTOR_TOP_K = 5

    # ── 一阶编码自动归类合并 ──
    # 基于景漂/游客真实数据集校准（~5%减少率，保守优先）
    ENABLE_AUTO_MERGE = True                          # 总开关：False 时完全跳过合并
    AUTO_MERGE_BGE_CONCEPT_MIN = 0.58                 # 编码 content ↔ content bge 余弦相似度阈值（第一层门控）
    AUTO_MERGE_BGE_SENT_MIN = 0.63                    # 句子 ↔ 句子 bge 余弦相似度阈值（第二层）
    AUTO_MERGE_CONCEPT_SIM_MIN = 0.40                 # 句子 ↔ 编码 content 的 concept_anchor_v6 余弦相似度阈值（第三层）
    AUTO_MERGE_KEYWORD_OVERLAP_MIN = 0.045            # 字符 bigram Jaccard 重叠比例阈值（第四层）

    # ── 一阶编码后端选择 ──
    # "bert": 使用当前BERT管线（默认）
    # "llm":  使用LLM管线（需先训练模型）
    FIRST_LEVEL_CODING_BACKEND = "bert"

    # LLM 一阶编码模型路径（GGUF格式）
    LLM_FIRST_LEVEL_MODEL_NAME = "qwen2.5-0.5b-coding-Q4_K_M.gguf"
    LLM_FIRST_LEVEL_MODEL_DIRNAME = "llm_first_level_coder"

    # LLM推理参数
    LLM_TEMPERATURE = 0.1
    LLM_TOP_P = 0.9
    LLM_MAX_TOKENS = 48
    LLM_REPEAT_PENALTY = 1.3  # >1 抑制小模型退化式复读
    LLM_N_GPU_LAYERS = -1  # -1=全部GPU, 0=仅CPU

    # 一阶抽象（抽取式）重排序模型配置
    # 该模型用于在“候选子句片段”中选择最接近人工抽象的一段（不负责改写）
    ENABLE_ABSTRACT_RERANKER = True
    ABSTRACT_RERANKER_DIRNAME = "abstract_reranker_latest"
    ABSTRACT_RERANK_MAX_SPAN_LEN = 12
    ABSTRACT_RERANK_TOP_N = 6
    ABSTRACT_RERANK_BATCH_SIZE = 128
    ABSTRACT_RERANK_NEGATIVE_SAMPLES = 4
    # 一阶召回增强（A/B 开关）
    FIRST_LEVEL_RECALL_ENHANCED = False
    FIRST_LEVEL_USE_LABEL_RECALL_CANDIDATES = False
    FIRST_LEVEL_BASE_MAX_SPAN = 8
    FIRST_LEVEL_ENHANCED_MAX_SPAN = 12
    FIRST_LEVEL_SEMANTIC_RECALL_TOP_N = 300
    FIRST_LEVEL_SEMANTIC_RECALL_MIN_SCORE = 0.35
    FIRST_LEVEL_RECALL_BANK_FILES = ["standard_train_optimized.csv", "standard.csv", "standard2.csv", "standard_train.csv", "first_level_recall_bank_cross_domain.csv"]
    # 一阶原型样本：默认关闭；如需项目域适配，可临时设置为辅助样本文件
    FIRST_LEVEL_PROTOTYPE_FILES = ["data/first_level_prototypes.json"]
    FIRST_LEVEL_FUSED_RANKING = False
    FIRST_LEVEL_RECALL_SCORE_WEIGHT = 1.8
    FIRST_LEVEL_RULE_SCORE_WEIGHT = 0.18
    FIRST_LEVEL_GLOBAL_RERANK_TOP_N = 24
    FIRST_LEVEL_SHORT_LABEL_BONUS = 2.5
    # ── 一阶锚点检索门控（F2 抬阈值 / F3 接地门）──
    # 默认值=当前行为；抬高 MIN_SCORE 让弱锚点回退抽取式，GROUNDING_MIN>0 拒绝抽象/零重叠锚点
    FIRST_LEVEL_ANCHOR_MIN_SCORE = 0.50       # 锚点直接当一阶码的最低 FAISS 相似度
    FIRST_LEVEL_ANCHOR_GROUNDING_MIN = 0.30   # 锚点字符在句子中的占比下限（接地门）
    # 抽象重排序训练策略：默认仅在模型缺失时训练（可大幅减少重复训练耗时）
    ABSTRACT_RERANKER_ALWAYS_RETRAIN = True

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
        "learning_rate": [1e-5, 3e-5],  # 使用范围搜索
        "batch_size": [16, 32],  # 减少批大小选项
        "epochs": [3],  # 固定训练轮数
        "dropout_rate": [0.1, 0.2]  # 减少dropout选项
    }
    HYPERPARAM_SEARCH_METHOD = "bayesian"
    HYPERPARAM_CV_FOLDS = 2  # 减少交叉验证折数
    HYPERPARAM_OPTIMIZATION_ALGORITHM = "tpe"  # 默认优化算法

    # 增量训练配置
    INCREMENTAL_LEARNING_RATE_RATIO = 0.5
    INCREMENTAL_MIN_SAMPLES = 10

    @classmethod
    def init_directories(cls):
        """初始化必要的目录"""
        PathManager.init_all_directories()

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
