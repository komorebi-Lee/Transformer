import os
from datetime import datetime

import torch
import logging
import numpy as np
import pickle
from typing import Dict, List, Any, Optional, Tuple
from config import Config

# 先导入pyarrow，确保它被正确加载
try:
    import pyarrow
    from pyarrow import PyExtensionType

    logging.info(f"pyarrow {pyarrow.__version__} 导入成功")
except ImportError as e:
    logging.warning(f"pyarrow导入失败: {e}")

# 尝试导入transformers，失败时使用降级模式
try:
    from transformers import AutoTokenizer, AutoModel

    TRANSFORMERS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"transformers库导入失败: {e}")
    TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger(__name__)


class EnhancedModelManager:
    """增强的模型管理器 - 修复版本"""

    def __init__(self):
        self.models = {}
        self.tokenizers = {}
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.local_model_dir = Config.LOCAL_MODELS_DIR
        self.trained_model_dir = Config.TRAINED_MODELS_DIR

        # 创建目录
        os.makedirs(self.trained_model_dir, exist_ok=True)
        os.makedirs(self.local_model_dir, exist_ok=True)

        # 训练模型状态
        self.trained_model = None
        self.is_model_loaded = False

        # 抽象重排序模型
        self._abstract_reranker_model = None
        self._abstract_reranker_tokenizer = None

        logger.info(f"使用设备: {self.device}")

    def initialize_models(self) -> bool:
        """初始化所有需要的模型"""
        try:
            # 加载BERT模型
            bert_path = os.path.join(self.local_model_dir, Config.DEFAULT_MODEL_NAME)
            if os.path.exists(bert_path):
                logger.info("加载本地BERT模型")
                self.tokenizers['bert'] = AutoTokenizer.from_pretrained(bert_path)
                self.models['bert'] = AutoModel.from_pretrained(bert_path).to(self.device)
                self.is_model_loaded = True
                logger.info("BERT模型初始化成功")
            else:
                logger.error("BERT模型不存在，请先运行 download_models.py")
                return False

            # 加载sentence-transformer模型（使用bge-small-zh-v1.5，与SemanticMatcher共享）
            sentence_model_path = os.path.join(self.local_model_dir, Config.SENTENCE_MODEL_NAME)
            if os.path.exists(sentence_model_path):
                try:
                    from sentence_transformers import SentenceTransformer
                    logger.info("加载sentence-transformer模型: %s", Config.SENTENCE_MODEL_NAME)
                    self.models['sentence'] = SentenceTransformer(sentence_model_path).to(self.device)
                    self.is_model_loaded = True
                    logger.info("sentence-transformer初始化成功")
                except Exception as e:
                    logger.warning(f"sentence-transformer模型加载失败: {e}")

            logger.info("模型初始化完成")
            return True

        except Exception as e:
            logger.error(f"模型初始化失败: {e}")
            return False

    def get_embeddings(self, texts: List[str], model_type: str = 'bert') -> np.ndarray:
        """获取文本嵌入"""
        try:
            if model_type == 'sentence' and 'sentence' in self.models:
                # 使用sentence-transformer模型，无需加载tokenizer
                model = self.models['sentence']
                embeddings = model.encode(texts, show_progress_bar=False)
                return embeddings

            # 默认使用BERT模型
            if not self.is_model_loaded:
                logger.warning("模型未加载，使用降级模式")
                return self.get_simple_embeddings(texts)

            tokenizer = self.tokenizers['bert']
            model = self.models['bert']

            inputs = tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=Config.MAX_SENTENCE_LENGTH,
                return_tensors="pt"
            ).to(self.device)

            with torch.no_grad():
                outputs = model(**inputs)
                embeddings = self.mean_pooling(outputs, inputs['attention_mask'])

            return embeddings.cpu().numpy()

        except Exception as e:
            logger.error(f"获取嵌入失败: {e}")
            return self.get_simple_embeddings(texts)

    def mean_pooling(self, model_output, attention_mask):
        """平均池化"""
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

    def save_trained_model(self, model_data: Dict[str, Any], version: str = None) -> bool:
        """保存训练过的模型"""
        try:
            # 确保训练模型目录存在
            os.makedirs(self.trained_model_dir, exist_ok=True)

            if version is None:
                # 安全地获取目录中的文件数量
                try:
                    model_files = [f for f in os.listdir(self.trained_model_dir) if f.endswith('.pkl')]
                    version = f"model_{len(model_files) + 1}"
                except Exception as dir_error:
                    logger.error(f"读取训练模型目录失败: {dir_error}")
                    version = f"model_{int(datetime.now().timestamp())}"

            # 规范化模型文件路径
            model_file = os.path.join(self.trained_model_dir, f"{version}.pkl")
            model_file = os.path.normpath(model_file)

            # 添加元数据
            model_data['metadata'] = {
                'version': version,
                'timestamp': self.get_timestamp(),
                'model_type': 'grounded_theory_coder',
                'sample_count': model_data.get('sample_count', 0),
                'class_count': model_data.get('class_count', 0),
                'training_time': model_data.get('training_time', ''),
                'accuracy': model_data.get('accuracy', None),
                'model_path': model_file
            }

            # 确保目录存在
            os.makedirs(os.path.dirname(model_file), exist_ok=True)

            with open(model_file, 'wb') as f:
                pickle.dump(model_data, f)

            logger.info(f"训练模型已保存: {model_file}")
            self.trained_model = model_data
            return True

        except Exception as e:
            logger.error(f"保存训练模型失败: {e}")
            return False

    def load_trained_model(self, version: str = None) -> bool:
        """加载训练过的模型"""
        try:
            # 确保训练模型目录存在
            os.makedirs(self.trained_model_dir, exist_ok=True)

            if version is None:
                # 加载最新的模型
                try:
                    model_files = [f for f in os.listdir(self.trained_model_dir) if f.endswith('.pkl')]
                    if not model_files:
                        logger.info("没有找到训练模型文件")
                        return False
                    # 按文件名排序，确保最新的模型被加载
                    model_files.sort(reverse=True)
                    version = model_files[0].replace('.pkl', '')
                except Exception as dir_error:
                    logger.error(f"读取训练模型目录失败: {dir_error}")
                    return False

            # 规范化模型文件路径
            model_file = os.path.join(self.trained_model_dir, f"{version}.pkl")
            model_file = os.path.normpath(model_file)

            if os.path.exists(model_file):
                file_size = os.path.getsize(model_file)
                if file_size == 0:
                    logger.warning(f"训练模型文件为空: {model_file}")
                    return False

                try:
                    with open(model_file, 'rb') as f:
                        self.trained_model = pickle.load(f)
                except pickle.UnpicklingError as pickle_error:
                    logger.error(f"模型文件解析失败: {pickle_error}")
                    return False
                except Exception as load_error:
                    logger.error(f"加载模型文件失败: {load_error}")
                    return False

                logger.info(f"训练模型已加载: {version} 路径: {model_file}")
                return True

            logger.warning(f"训练模型文件不存在: {model_file}")
            return False

        except Exception as e:
            logger.error(f"加载训练模型失败: {e}")
            return False

    def predict_categories(self, texts: List[str]) -> Tuple[np.ndarray, List[str]]:
        """使用训练模型预测类别"""
        if self.trained_model is None:
            raise ValueError("没有训练过的模型可用")

        try:
            # 获取嵌入
            embeddings = self.get_embeddings(texts)

            # 使用训练好的分类器预测
            classifier = self.trained_model.get('classifier')
            if classifier is None:
                raise ValueError("训练模型中缺少分类器")

            predictions = classifier.predict(embeddings)

            # 转换回标签
            label_mapping = self.trained_model.get('label_mapping', {})
            reverse_mapping = {v: k for k, v in label_mapping.items()}

            predicted_labels = [reverse_mapping.get(pred, "未知") for pred in predictions]

            return predictions, predicted_labels

        except Exception as e:
            logger.error(f"预测类别失败: {e}")
            raise

    def get_simple_embeddings(self, texts: List[str]) -> np.ndarray:
        """简单的嵌入生成（降级模式）"""
        embeddings = []
        for text in texts:
            embedding = np.zeros(768, dtype=np.float32)
            text_hash = hash(text) % 10000
            np.random.seed(text_hash)
            base_vector = np.random.randn(768) * 0.1
            base_vector[0] = min(len(text), 100) / 100.0
            embeddings.append(base_vector)
        return np.array(embeddings)

    def is_trained_model_available(self) -> bool:
        """检查是否有可用的训练模型"""
        return self.trained_model is not None

    def get_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_model_type(self) -> str:
        """获取当前加载的模型类型"""
        if hasattr(self, '_bert_finetuner') and self._bert_finetuner is not None:
            return "bert_finetune"
        elif self.trained_model is not None:
            return "classifier"
        else:
            return "none"

    def get_current_model_info(self) -> dict:
        """获取当前加载的模型信息"""
        model_type = self.get_model_type()
        if model_type == "bert_finetune":
            finetuner = getattr(self, '_bert_finetuner', None)
            if finetuner:
                return {
                    'type': 'BERT微调模型',
                    'name': 'bert_finetuned_latest'
                }
        elif model_type == "classifier":
            if self.trained_model:
                metadata = self.trained_model.get('metadata', {})
                return {
                    'type': '分类器模型',
                    'name': metadata.get('version', 'unknown')
                }
        return {'type': '无', 'name': '无'}

    def load_abstract_reranker_model(self, model_dir: str = None) -> bool:
        """加载一阶抽象重排序模型（BERT微调二分类）"""
        try:
            if self.is_abstract_reranker_available():
                return True

            if not TRANSFORMERS_AVAILABLE:
                return False

            if model_dir is None:
                model_dir = os.path.join(self.trained_model_dir, getattr(Config, 'ABSTRACT_RERANKER_DIRNAME', 'abstract_reranker_latest'))
            model_dir = os.path.normpath(model_dir)

            if not os.path.exists(model_dir):
                return False

            from transformers import AutoTokenizer, AutoModelForSequenceClassification

            self._abstract_reranker_tokenizer = AutoTokenizer.from_pretrained(model_dir)
            self._abstract_reranker_model = AutoModelForSequenceClassification.from_pretrained(model_dir).to(self.device)
            self._abstract_reranker_model.eval()
            return True

        except Exception as e:
            logger.error(f"加载抽象重排序模型失败: {e}")
            return False

    def is_abstract_reranker_available(self) -> bool:
        return self._abstract_reranker_model is not None and self._abstract_reranker_tokenizer is not None

    def ensure_abstract_reranker_loaded(self):
        """确保抽象重排序模型已加载（懒加载入口）"""
        if not self.is_abstract_reranker_available():
            self.load_abstract_reranker_model()

    def batch_abstract_rerank(self, norm_texts: List[str], cand_texts: List[str]) -> List[float]:
        """批量抽象重排序：对(句子,候选)对打分，返回正类置信度"""
        if not self.is_abstract_reranker_available():
            return [0.5] * len(norm_texts)

        tokenizer = self._abstract_reranker_tokenizer
        model = self._abstract_reranker_model
        scores = []
        batch_size = getattr(Config, 'ABSTRACT_RERANK_BATCH_SIZE', 128) if Config else 128

        for i in range(0, len(norm_texts), batch_size):
            batch_norms = norm_texts[i:i + batch_size]
            batch_cands = cand_texts[i:i + batch_size]
            inputs = tokenizer(
                batch_norms, batch_cands,
                padding=True, truncation=True,
                max_length=getattr(Config, 'MAX_SENTENCE_LENGTH', 512) if Config else 512,
                return_tensors='pt'
            ).to(self.device)
            with torch.no_grad():
                logits = model(**inputs).logits
                probs = torch.softmax(logits, dim=-1)
                scores.extend(probs[:, 1].cpu().tolist())

        return scores