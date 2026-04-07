import os
import json
from datetime import datetime

import torch
import logging
import numpy as np
import pickle
from typing import Dict, List, Any, Optional, Tuple
from config import Config
from bert_finetuner import BERTFineTuner
from bert_dataset import get_label_mapping

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

            # 加载sentence-transformer模型
            sentence_model_path = os.path.join(self.local_model_dir, "sentence-transformer")
            if os.path.exists(sentence_model_path):
                try:
                    from sentence_transformers import SentenceTransformer
                    logger.info("加载本地sentence-transformer模型")
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

                self._bert_finetuner = None
                self.is_model_loaded = True
                logger.info(f"训练模型已加载: {version} 路径: {model_file}")
                return True

            logger.warning(f"训练模型文件不存在: {model_file}")
            return False

        except Exception as e:
            logger.error(f"加载训练模型失败: {e}")
            return False

    def load_model_auto(self, model_name: str, model_type: str = None) -> bool:
        """
        自动检测并加载模型（支持PKL分类器和BERT微调两种格式）
        
        Args:
            model_name: 模型名称
            model_type: 模型类型 ('classifier' 或 'bert_finetune')，如果为None则自动检测
            
        Returns:
            加载是否成功
        """
        try:
            model_path = os.path.join(self.trained_model_dir, model_name)
            
            if model_type is None:
                model_type = self.detect_model_format(model_path)
            
            logger.info(f"加载模型: {model_name}, 类型: {model_type}")
            
            if model_type == "bert_finetune":
                return self._load_bert_finetune_model(model_path)
            else:
                return self.load_trained_model(model_name)
                
        except Exception as e:
            logger.error(f"自动加载模型失败: {e}")
            return False

    def _load_bert_finetune_model(self, model_dir: str) -> bool:
        """
        加载BERT微调模型
        
        Args:
            model_dir: 模型目录路径
            
        Returns:
            加载是否成功
        """
        try:
            if not os.path.exists(model_dir):
                logger.error(f"模型目录不存在: {model_dir}")
                return False
            
            from bert_finetuner import BERTFineTuner
            
            finetuner = BERTFineTuner(self)
            success = finetuner.load_model(model_dir)
            
            if not success:
                logger.error("加载BERT微调模型失败")
                return False
            
            self._bert_finetuner = finetuner
            self._model_type = "bert_finetune"
            
            label_mapping_path = os.path.join(model_dir, 'label_mapping.json')
            if os.path.exists(label_mapping_path):
                with open(label_mapping_path, 'r', encoding='utf-8') as f:
                    mapping_data = json.load(f)
                    self._bert_label_mapping = mapping_data.get('label_to_id', {})
                    self._bert_id_to_label = {int(k): v for k, v in mapping_data.get('id_to_label', {}).items()}
                logger.info(f"BERT微调模型标签映射已加载: {len(self._bert_label_mapping)} 个标签")
            
            self.is_model_loaded = True
            logger.info(f"BERT微调模型已从 {model_dir} 加载成功")
            return True
            
        except Exception as e:
            logger.error(f"加载BERT微调模型失败: {e}")
            return False

    def get_model_type(self) -> str:
        """获取当前加载的模型类型"""
        if hasattr(self, '_bert_finetuner') and self._bert_finetuner is not None:
            return "bert_finetune"
        elif self.trained_model is not None:
            return "classifier"
        else:
            return "none"
    
    def get_current_model_info(self) -> Dict[str, Any]:
        """获取当前加载的模型信息"""
        model_type = self.get_model_type()
        if model_type == "bert_finetune":
            finetuner = getattr(self, '_bert_finetuner', None)
            if finetuner:
                # 尝试获取BERT微调模型的名称
                # 这里可以根据实际情况获取模型名称
                # 暂时返回类型信息
                return {
                    'type': 'BERT微调模型',
                    'name': 'bert_finetuned_latest'  # 这里可以根据实际情况获取
                }
        elif model_type == "classifier":
            if self.trained_model:
                metadata = self.trained_model.get('metadata', {})
                return {
                    'type': '分类器模型',
                    'name': metadata.get('version', 'unknown')
                }
        return {'type': '无', 'name': '无'}

    def predict_with_loaded_model(self, texts: List[str]) -> Tuple[np.ndarray, List[str]]:
        """
        使用已加载的模型进行预测（自动选择模型类型）
        
        Args:
            texts: 待预测的文本列表
            
        Returns:
            Tuple[predictions, predicted_labels]
        """
        model_type = self.get_model_type()
        
        if model_type == "bert_finetune":
            return self.predict_with_finetuned_bert(texts)
        elif model_type == "classifier":
            return self.predict_categories(texts)
        else:
            raise ValueError("没有加载任何模型")

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
        # 检查分类器模型
        if self.trained_model is not None:
            return True
        # 检查BERT微调模型
        finetuner = getattr(self, '_bert_finetuner', None)
        if finetuner is not None and finetuner.is_model_loaded():
            return True
        # 检查trained_models目录中是否存在训练模型文件
        try:
            if os.path.exists(self.trained_model_dir):
                # 检查是否有.pkl文件（分类器模型）
                pkl_files = [f for f in os.listdir(self.trained_model_dir) if f.endswith('.pkl')]
                if pkl_files:
                    return True
                # 检查是否有目录（BERT微调模型）
                dirs = [d for d in os.listdir(self.trained_model_dir) if os.path.isdir(os.path.join(self.trained_model_dir, d))]
                for dir_name in dirs:
                    dir_path = os.path.join(self.trained_model_dir, dir_name)
                    # 检查是否是BERT微调模型目录
                    if self.detect_model_format(dir_path) == "bert_finetune":
                        return True
        except Exception as e:
            logger.debug(f"检查训练模型目录时出错: {e}")
        return False

    def get_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def save_finetuned_bert(
        self,
        model_dir: str,
        metadata: Dict[str, Any],
        label_mapping: Dict[str, int]
    ) -> bool:
        """
        保存微调后的BERT模型

        Args:
            model_dir: 模型保存目录
            metadata: 训练元数据（训练时间、样本数、准确率等）
            label_mapping: 标签映射关系

        Returns:
            保存是否成功
        """
        try:
            os.makedirs(model_dir, exist_ok=True)

            finetuner = getattr(self, '_bert_finetuner', None)
            if finetuner is None or finetuner.model is None:
                logger.error("没有可保存的微调BERT模型")
                return False

            finetuner.save_model(model_dir)

            metadata_path = os.path.join(model_dir, 'training_metadata.json')
            metadata_with_timestamp = metadata.copy()
            metadata_with_timestamp['timestamp'] = self.get_timestamp()
            metadata_with_timestamp['model_type'] = 'bert_finetune'
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata_with_timestamp, f, ensure_ascii=False, indent=2)
            logger.info(f"训练元数据已保存到: {metadata_path}")

            label_mapping_path = os.path.join(model_dir, 'label_mapping.json')
            id_to_label = {str(v): k for k, v in label_mapping.items()}
            with open(label_mapping_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'label_to_id': label_mapping,
                    'id_to_label': id_to_label
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"标签映射已保存到: {label_mapping_path}")

            logger.info(f"微调BERT模型已保存到: {model_dir}")
            return True

        except Exception as e:
            logger.error(f"保存微调BERT模型失败: {e}")
            return False

    def load_finetuned_bert(self, model_dir: str) -> Tuple[Optional[Any], Optional[Dict[str, int]]]:
        """
        加载已微调的BERT模型

        Args:
            model_dir: 模型目录

        Returns:
            Tuple[加载的模型, 标签映射]: 返回模型和标签映射，失败返回 (None, None)
        """
        try:
            if not os.path.exists(model_dir):
                logger.error(f"模型目录不存在: {model_dir}")
                return None, None

            model_format = self.detect_model_format(model_dir)
            if model_format != "bert_finetune":
                logger.error(f"模型格式不正确，期望 bert_finetune，实际为: {model_format}")
                return None, None

            finetuner = BERTFineTuner(self)
            success = finetuner.load_model(model_dir)

            if not success:
                logger.error("加载微调BERT模型失败")
                return None, None

            self._bert_finetuner = finetuner

            label_mapping_path = os.path.join(model_dir, 'label_mapping.json')
            label_mapping = None
            if os.path.exists(label_mapping_path):
                with open(label_mapping_path, 'r', encoding='utf-8') as f:
                    mapping_data = json.load(f)
                    label_mapping = mapping_data.get('label_to_id', {})
                logger.info(f"标签映射已加载: {len(label_mapping)} 个标签")

            logger.info(f"微调BERT模型已从 {model_dir} 加载成功")
            return finetuner, label_mapping

        except Exception as e:
            logger.error(f"加载微调BERT模型失败: {e}")
            return None, None

    def predict_with_finetuned_bert(self, texts: List[str]) -> Tuple[np.ndarray, List[str]]:
        """
        使用微调后的BERT模型进行预测

        Args:
            texts: 待预测的文本列表

        Returns:
            Tuple[predictions, predicted_labels]: 预测结果数组和预测标签列表
        """
        try:
            finetuner = getattr(self, '_bert_finetuner', None)
            if finetuner is None or not finetuner.is_model_loaded():
                raise ValueError("微调BERT模型未加载，请先调用 load_finetuned_bert()")

            predicted_ids, predicted_labels, confidence_scores = finetuner.predict(texts)

            predictions = np.array(predicted_ids)

            return predictions, predicted_labels

        except Exception as e:
            logger.error(f"使用微调BERT模型预测失败: {e}")
            raise

    def is_finetuned_model_available(self) -> bool:
        """
        检查是否有可用的微调BERT模型

        Returns:
            是否有可用的微调模型
        """
        finetuner = getattr(self, '_bert_finetuner', None)
        if finetuner is not None and finetuner.is_model_loaded():
            return True

        try:
            model_files = [f for f in os.listdir(self.trained_model_dir)
                          if os.path.isdir(os.path.join(self.trained_model_dir, f))]
            for model_dir in model_files:
                full_path = os.path.join(self.trained_model_dir, model_dir)
                if self.detect_model_format(full_path) == "bert_finetune":
                    return True
        except Exception as e:
            logger.debug(f"检查微调模型时出错: {e}")

        return False

    def detect_model_format(self, model_dir: str) -> str:
        """
        检测模型格式（区分分类器模型和BERT微调模型）

        Args:
            model_dir: 模型目录

        Returns:
            模型格式: "bert_finetune" 或 "classifier"
        """
        try:
            if not os.path.exists(model_dir):
                logger.warning(f"模型目录不存在: {model_dir}")
                return "classifier"

            config_path = os.path.join(model_dir, 'config.json')
            pytorch_model_path = os.path.join(model_dir, 'pytorch_model.bin')
            model_safetensors_path = os.path.join(model_dir, 'model.safetensors')
            label_mapping_path = os.path.join(model_dir, 'label_mapping.json')
            training_config_path = os.path.join(model_dir, 'training_config.json')

            has_bert_config = os.path.exists(config_path)
            has_bert_weights = os.path.exists(pytorch_model_path) or os.path.exists(model_safetensors_path)
            has_label_mapping = os.path.exists(label_mapping_path)
            has_training_config = os.path.exists(training_config_path)

            if has_bert_config and has_bert_weights and has_label_mapping:
                if has_training_config:
                    with open(training_config_path, 'r', encoding='utf-8') as f:
                        training_config = json.load(f)
                        if 'training_config' in training_config:
                            return "bert_finetune"

                return "bert_finetune"

            pkl_files = [f for f in os.listdir(model_dir) if f.endswith('.pkl')]
            if pkl_files:
                return "classifier"

            if os.path.isfile(model_dir) and model_dir.endswith('.pkl'):
                return "classifier"

            return "classifier"

        except Exception as e:
            logger.error(f"检测模型格式失败: {e}")
            return "classifier"