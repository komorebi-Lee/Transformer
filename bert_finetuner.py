import copy
import json
import logging
import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset, random_split
from transformers import (
    AutoConfig,
    AutoModelForSequenceClassification,
    AutoTokenizer,
    EarlyStoppingCallback,
    Trainer,
    TrainerCallback,
    TrainingArguments,
    get_linear_schedule_with_warmup,
)

from config import Config

logger = logging.getLogger(__name__)


class TrainingHistory:
    """训练历史记录管理类"""

    def __init__(self, history_file: Optional[str] = None):
        """
        初始化训练历史记录

        Args:
            history_file: 历史记录文件路径，如果为None则不持久化
        """
        self.history_file = history_file
        self.records: List[Dict[str, Any]] = []
        self.data_versions: Dict[str, Dict[str, Any]] = {}

        if history_file and os.path.exists(history_file):
            self._load_history()

    def _load_history(self) -> bool:
        """从文件加载历史记录"""
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.records = data.get('records', [])
                self.data_versions = data.get('data_versions', {})
            logger.info(f"已加载训练历史记录: {len(self.records)} 条记录")
            return True
        except Exception as e:
            logger.warning(f"加载训练历史记录失败: {e}")
            return False

    def _save_history(self) -> bool:
        """保存历史记录到文件"""
        if not self.history_file:
            return True

        try:
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'records': self.records,
                    'data_versions': self.data_versions
                }, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存训练历史记录失败: {e}")
            return False

    def add_record(
        self,
        training_type: str,
        model_path: str,
        data_version: str,
        samples_count: int,
        epochs: int,
        learning_rate: float,
        metrics: Optional[Dict[str, float]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        添加训练记录

        Args:
            training_type: 训练类型 ('initial' 或 'incremental')
            model_path: 模型保存路径
            data_version: 数据版本标识
            samples_count: 训练样本数量
            epochs: 训练轮数
            learning_rate: 学习率
            metrics: 训练指标
            config: 训练配置

        Returns:
            是否添加成功
        """
        record = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'training_type': training_type,
            'model_path': model_path,
            'data_version': data_version,
            'samples_count': samples_count,
            'epochs': epochs,
            'learning_rate': learning_rate,
            'metrics': metrics or {},
            'config': config or {}
        }

        self.records.append(record)
        logger.info(f"添加训练记录: {training_type} - {data_version} - {samples_count} 样本")

        return self._save_history()

    def register_data_version(
        self,
        version: str,
        samples_count: int,
        label_count: int,
        source: str = 'unknown',
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        注册数据版本

        Args:
            version: 版本标识
            samples_count: 样本数量
            label_count: 标签数量
            source: 数据来源
            metadata: 其他元数据

        Returns:
            是否注册成功
        """
        self.data_versions[version] = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'samples_count': samples_count,
            'label_count': label_count,
            'source': source,
            'metadata': metadata or {}
        }

        logger.info(f"注册数据版本: {version} - {samples_count} 样本, {label_count} 标签")
        return self._save_history()

    def get_latest_record(self) -> Optional[Dict[str, Any]]:
        """获取最新的训练记录"""
        return self.records[-1] if self.records else None

    def get_records_by_type(self, training_type: str) -> List[Dict[str, Any]]:
        """获取指定类型的训练记录"""
        return [r for r in self.records if r.get('training_type') == training_type]

    def get_incremental_count(self) -> int:
        """获取增量训练次数"""
        return len(self.get_records_by_type('incremental'))

    def get_total_samples_trained(self) -> int:
        """获取总训练样本数"""
        return sum(r.get('samples_count', 0) for r in self.records)

    def get_data_version_info(self, version: str) -> Optional[Dict[str, Any]]:
        """获取数据版本信息"""
        return self.data_versions.get(version)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'records': self.records,
            'data_versions': self.data_versions,
            'summary': {
                'total_trainings': len(self.records),
                'incremental_count': self.get_incremental_count(),
                'total_samples': self.get_total_samples_trained()
            }
        }


class ProgressCallback(TrainerCallback):
    """自定义训练进度回调类"""

    def __init__(
        self,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ):
        """
        初始化进度回调

        Args:
            progress_callback: 进度更新回调函数 (current_step, total_steps, loss)
            log_callback: 日志记录回调函数 (message)
        """
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.current_step = 0
        self.total_steps = 0
        self.current_epoch = 0
        self.total_epochs = 0

    def on_train_begin(self, args, state, control, **kwargs):
        """训练开始时调用"""
        self.total_steps = state.max_steps
        self.total_epochs = args.num_train_epochs
        message = f"训练开始，总步数: {self.total_steps}, 总轮数: {self.total_epochs}"
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)

    def on_train_end(self, args, state, control, **kwargs):
        """训练结束时调用"""
        message = "训练完成"
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)

    def on_epoch_begin(self, args, state, control, **kwargs):
        """每个epoch开始时调用"""
        self.current_epoch = state.epoch
        message = f"开始第 {int(self.current_epoch) + 1}/{int(self.total_epochs)} 轮训练"
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)

    def on_epoch_end(self, args, state, control, **kwargs):
        """每个epoch结束时调用"""
        message = f"第 {int(self.current_epoch) + 1} 轮训练完成"
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)

    def on_step_begin(self, args, state, control, **kwargs):
        """每个step开始时调用"""
        pass

    def on_step_end(self, args, state, control, **kwargs):
        """每个step结束时调用"""
        self.current_step = state.global_step
        if self.progress_callback and self.total_steps > 0:
            loss = state.log_history[-1].get('loss', 0.0) if state.log_history else 0.0
            self.progress_callback(self.current_step, self.total_steps, loss)

    def on_log(self, args, state, control, logs=None, **kwargs):
        """日志记录时调用"""
        if logs and self.log_callback:
            loss = logs.get('loss', None)
            learning_rate = logs.get('learning_rate', None)
            epoch = logs.get('epoch', None)
            if loss is not None:
                message = f"Epoch: {epoch:.2f}, Loss: {loss:.4f}"
                if learning_rate is not None:
                    message += f", LR: {learning_rate:.2e}"
                self.log_callback(message)


class BERTFineTuner:
    """BERT微调训练器"""

    def __init__(self, model_manager, config: Optional[Dict[str, Any]] = None):
        """
        初始化BERT微调训练器

        Args:
            model_manager: 模型管理器实例
            config: 训练配置字典，如果为None则使用默认配置
        """
        self.model_manager = model_manager
        self.config = config or {}
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.model = None
        self.tokenizer = None
        self.label_to_id: Dict[str, int] = {}
        self.id_to_label: Dict[int, str] = {}
        self.trainer: Optional[Trainer] = None
        self.training_args: Optional[TrainingArguments] = None

        self._init_training_config()
        self._init_training_history()

        logger.info(f"BERTFineTuner 初始化完成，设备: {self.device}")

    def _init_training_history(self):
        """初始化训练历史记录"""
        history_file = os.path.join(Config.TRAINED_MODELS_DIR, 'training_history.json')
        self.training_history = TrainingHistory(history_file)
        self.current_data_version: Optional[str] = None
        self.previous_model_path: Optional[str] = None

    def _init_training_config(self):
        """初始化训练配置"""
        self.training_config = {
            'learning_rate': self.config.get('learning_rate', Config.FINETUNE_LEARNING_RATE),
            'num_train_epochs': self.config.get('num_train_epochs', Config.FINETUNE_EPOCHS),
            'per_device_train_batch_size': self.config.get('batch_size', Config.FINETUNE_BATCH_SIZE),
            'per_device_eval_batch_size': self.config.get('batch_size', Config.FINETUNE_BATCH_SIZE),
            'warmup_ratio': self.config.get('warmup_ratio', Config.FINETUNE_WARMUP_RATIO),
            'weight_decay': self.config.get('weight_decay', Config.FINETUNE_WEIGHT_DECAY),
            'early_stopping_patience': self.config.get('early_stopping_patience', Config.FINETUNE_EARLY_STOP_PATIENCE),
            'max_grad_norm': self.config.get('max_grad_norm', Config.FINETUNE_MAX_GRAD_NORM),
            'dropout_rate': self.config.get('dropout_rate', Config.FINETUNE_DROPOUT_RATE),
            'max_length': self.config.get('max_length', Config.MAX_SENTENCE_LENGTH),
            'evaluation_strategy': self.config.get('evaluation_strategy', 'epoch'),
            'save_strategy': self.config.get('save_strategy', 'epoch'),
            'load_best_model_at_end': self.config.get('load_best_model_at_end', True),
            'metric_for_best_model': self.config.get('metric_for_best_model', 'eval_f1'),
            'greater_is_better': self.config.get('greater_is_better', True),
        }

        logger.info(f"训练配置: {self.training_config}")

    def _prepare_model(self, num_labels: int, model_path: Optional[str] = None):
        """
        准备模型

        Args:
            num_labels: 标签数量
            model_path: 预训练模型路径，如果为None则使用默认模型
        """
        try:
            if model_path and os.path.exists(model_path):
                logger.info(f"从路径加载模型: {model_path}")
                self.tokenizer = AutoTokenizer.from_pretrained(model_path)
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    model_path,
                    num_labels=num_labels,
                    ignore_mismatched_sizes=True,
                    problem_type="single_label_classification"
                )
            else:
                local_model_path = os.path.join(Config.LOCAL_MODELS_DIR, Config.DEFAULT_MODEL_NAME)
                if os.path.exists(local_model_path):
                    logger.info(f"加载本地模型: {local_model_path}")
                    self.tokenizer = AutoTokenizer.from_pretrained(local_model_path)
                    self.model = AutoModelForSequenceClassification.from_pretrained(
                        local_model_path,
                        num_labels=num_labels,
                        problem_type="single_label_classification"
                    )
                else:
                    logger.info(f"加载预训练模型: {Config.DEFAULT_MODEL_NAME}")
                    self.tokenizer = AutoTokenizer.from_pretrained(Config.DEFAULT_MODEL_NAME)
                    self.model = AutoModelForSequenceClassification.from_pretrained(
                        Config.DEFAULT_MODEL_NAME,
                        num_labels=num_labels,
                        problem_type="single_label_classification"
                    )

            self.model.to(self.device)
            logger.info(f"模型已加载到设备: {self.device}")

        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            raise

    def _prepare_dataset(
        self,
        dataset: Dataset,
        train_ratio: float = 0.8
    ) -> Tuple[Dataset, Dataset]:
        """
        准备训练和验证数据集

        Args:
            dataset: 原始数据集
            train_ratio: 训练集比例

        Returns:
            Tuple[train_dataset, eval_dataset]
        """
        total_size = len(dataset)
        train_size = int(total_size * train_ratio)
        eval_size = total_size - train_size

        train_dataset, eval_dataset = random_split(
            dataset,
            [train_size, eval_size],
            generator=torch.Generator().manual_seed(42)
        )

        logger.info(f"数据集分割: 训练集 {train_size} 样本, 验证集 {eval_size} 样本")
        return train_dataset, eval_dataset

    def _compute_metrics(self, eval_pred) -> Dict[str, float]:
        """
        计算评估指标

        Args:
            eval_pred: 评估预测结果

        Returns:
            评估指标字典
        """
        from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=1)

        accuracy = accuracy_score(labels, predictions)
        f1 = f1_score(labels, predictions, average='weighted', zero_division=0)
        precision = precision_score(labels, predictions, average='weighted', zero_division=0)
        recall = recall_score(labels, predictions, average='weighted', zero_division=0)

        return {
            'accuracy': accuracy,
            'f1': f1,
            'precision': precision,
            'recall': recall
        }

    def merge_training_data(
        self,
        old_data: Union[Dataset, Dict[str, Any]],
        new_data: Union[Dataset, Dict[str, Any]],
        update_mode: str = 'append'
    ) -> Dataset:
        """
        合并新旧训练数据

        Args:
            old_data: 旧训练数据（Dataset 或包含 texts/labels 的字典）
            new_data: 新训练数据（Dataset 或包含 texts/labels 的字典）
            update_mode: 更新模式
                - 'append': 增量添加新样本
                - 'update': 更新已有样本的标签（基于文本匹配）
                - 'replace': 用新数据替换旧数据

        Returns:
            合并后的 Dataset
        """
        try:
            old_texts, old_labels = self._extract_texts_labels(old_data)
            new_texts, new_labels = self._extract_texts_labels(new_data)

            if update_mode == 'replace':
                logger.info(f"替换模式: 使用新数据 ({len(new_texts)} 样本)")
                return self._create_dataset_from_texts_labels(new_texts, new_labels)

            if update_mode == 'append':
                merged_texts = old_texts + new_texts
                merged_labels = old_labels + new_labels
                logger.info(f"追加模式: 旧数据 {len(old_texts)} + 新数据 {len(new_texts)} = {len(merged_texts)} 样本")
                return self._create_dataset_from_texts_labels(merged_texts, merged_labels)

            if update_mode == 'update':
                text_to_label: Dict[str, int] = {}
                for text, label in zip(old_texts, old_labels):
                    text_to_label[text] = label

                updated_count = 0
                added_count = 0
                for text, label in zip(new_texts, new_labels):
                    if text in text_to_label:
                        if text_to_label[text] != label:
                            text_to_label[text] = label
                            updated_count += 1
                    else:
                        text_to_label[text] = label
                        added_count += 1

                merged_texts = list(text_to_label.keys())
                merged_labels = list(text_to_label.values())
                logger.info(f"更新模式: 更新 {updated_count} 条, 新增 {added_count} 条, 总计 {len(merged_texts)} 样本")
                return self._create_dataset_from_texts_labels(merged_texts, merged_labels)

            raise ValueError(f"未知的更新模式: {update_mode}")

        except Exception as e:
            logger.error(f"合并训练数据失败: {e}")
            raise

    def _extract_texts_labels(self, data: Union[Dataset, Dict[str, Any]]) -> Tuple[List[str], List[int]]:
        """
        从数据中提取文本和标签

        Args:
            data: Dataset 或包含 texts/labels 的字典

        Returns:
            Tuple[texts, labels]
        """
        if isinstance(data, dict):
            texts = data.get('texts', [])
            labels = data.get('labels', [])
            if not texts or not labels:
                raise ValueError("字典数据必须包含 'texts' 和 'labels' 键")
            return list(texts), list(labels)

        if hasattr(data, 'texts') and hasattr(data, 'labels'):
            return list(data.texts), list(data.labels)

        if hasattr(data, '__len__') and hasattr(data, '__getitem__'):
            texts = []
            labels = []
            for i in range(len(data)):
                item = data[i]
                if isinstance(item, dict):
                    if 'input_ids' in item and 'labels' in item:
                        if hasattr(data, 'texts'):
                            texts.append(data.texts[i])
                        else:
                            texts.append(f"sample_{i}")
                        labels.append(item['labels'].item() if hasattr(item['labels'], 'item') else item['labels'])
                    else:
                        raise ValueError(f"无法从数据集项中提取文本和标签: {item.keys()}")
                else:
                    raise ValueError(f"不支持的数据集项类型: {type(item)}")
            return texts, labels

        raise ValueError(f"不支持的数据类型: {type(data)}")

    def _create_dataset_from_texts_labels(self, texts: List[str], labels: List[int]) -> Dataset:
        """
        从文本和标签创建 Dataset

        Args:
            texts: 文本列表
            labels: 标签列表

        Returns:
            Dataset 实例
        """
        from bert_dataset import GroundedTheoryDataset

        if self.tokenizer is None:
            local_model_path = os.path.join(Config.LOCAL_MODELS_DIR, Config.DEFAULT_MODEL_NAME)
            if os.path.exists(local_model_path):
                self.tokenizer = AutoTokenizer.from_pretrained(local_model_path)
            else:
                self.tokenizer = AutoTokenizer.from_pretrained(Config.DEFAULT_MODEL_NAME)

        max_length = self.training_config.get('max_length', Config.MAX_SENTENCE_LENGTH)
        dataset = GroundedTheoryDataset(texts, labels, self.tokenizer, max_length)

        dataset.label_to_id = self.label_to_id
        dataset.id_to_label = self.id_to_label

        return dataset

    def train(
        self,
        dataset: Dataset,
        output_dir: str,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        finished_callback: Optional[Callable[[bool, str], None]] = None
    ) -> bool:
        """
        训练模型

        Args:
            dataset: 训练数据集
            output_dir: 输出目录
            progress_callback: 进度回调函数 (current_step, total_steps, loss)
            finished_callback: 完成回调函数 (success, message)

        Returns:
            训练是否成功
        """
        try:
            os.makedirs(output_dir, exist_ok=True)

            # 处理 Subset 包装器
            underlying_dataset = dataset
            while hasattr(underlying_dataset, 'dataset'):
                underlying_dataset = underlying_dataset.dataset

            # 增量训练时保留已有标签映射，只添加新标签
            if self.model is not None and self.label_to_id:
                logger.info(f"增量训练模式：保留已有标签映射 ({len(self.label_to_id)} 个标签)")
                # 从新数据中提取标签，添加新标签到已有映射
                if hasattr(underlying_dataset, 'label_to_id'):
                    new_label_to_id = underlying_dataset.label_to_id
                elif hasattr(underlying_dataset, 'labels'):
                    unique_labels = set(underlying_dataset.labels)
                    new_label_to_id = {label: i for i, label in enumerate(sorted(unique_labels))}
                else:
                    all_labels = []
                    for i in range(len(dataset)):
                        item = dataset[i]
                        if isinstance(item, dict) and 'labels' in item:
                            all_labels.append(item['labels'].item() if hasattr(item['labels'], 'item') else item['labels'])
                    unique_labels = set(all_labels)
                    new_label_to_id = {label: i for i, label in enumerate(sorted(unique_labels))}
                
                # 合并新标签到已有映射
                max_id = max(self.label_to_id.values()) if self.label_to_id else -1
                for label, _ in new_label_to_id.items():
                    if label not in self.label_to_id:
                        max_id += 1
                        self.label_to_id[label] = max_id
                        logger.info(f"添加新标签: {label} -> {max_id}")
                self.id_to_label = {v: k for k, v in self.label_to_id.items()}
            else:
                # 首次训练，从数据集提取标签
                if hasattr(underlying_dataset, 'label_to_id'):
                    self.label_to_id = underlying_dataset.label_to_id
                    self.id_to_label = {v: k for k, v in self.label_to_id.items()}
                elif hasattr(underlying_dataset, 'labels'):
                    unique_labels = set(underlying_dataset.labels)
                    self.label_to_id = {label: i for i, label in enumerate(sorted(unique_labels))}
                    self.id_to_label = {i: label for label, i in self.label_to_id.items()}
                else:
                    all_labels = []
                    for i in range(len(dataset)):
                        item = dataset[i]
                        if isinstance(item, dict) and 'labels' in item:
                            all_labels.append(item['labels'].item() if hasattr(item['labels'], 'item') else item['labels'])
                    unique_labels = set(all_labels)
                    self.label_to_id = {label: i for i, label in enumerate(sorted(unique_labels))}
                    self.id_to_label = {i: label for label, i in self.label_to_id.items()}

            num_labels = len(self.label_to_id)
            logger.info(f"标签数量: {num_labels}")

            # 只有在模型未加载时才准备模型（增量训练时已加载）
            if self.model is None:
                logger.info("模型未加载，准备新模型")
                self._prepare_model(num_labels)
            else:
                logger.info("使用已加载的模型进行训练（增量训练模式）")

            if hasattr(underlying_dataset, 'tokenizer'):
                self.tokenizer = underlying_dataset.tokenizer

            train_dataset, eval_dataset = self._prepare_dataset(dataset)

            training_args = TrainingArguments(
                output_dir=output_dir,
                learning_rate=self.training_config['learning_rate'],
                num_train_epochs=self.training_config['num_train_epochs'],
                per_device_train_batch_size=self.training_config['per_device_train_batch_size'],
                per_device_eval_batch_size=self.training_config['per_device_eval_batch_size'],
                warmup_ratio=self.training_config['warmup_ratio'],
                weight_decay=self.training_config['weight_decay'],
                max_grad_norm=self.training_config['max_grad_norm'],
                eval_strategy=self.training_config['evaluation_strategy'],
                save_strategy=self.training_config['save_strategy'],
                load_best_model_at_end=self.training_config['load_best_model_at_end'],
                metric_for_best_model=self.training_config['metric_for_best_model'],
                greater_is_better=self.training_config['greater_is_better'],
                logging_dir=os.path.join(output_dir, 'logs'),
                logging_steps=10,
                save_total_limit=2,
                fp16=torch.cuda.is_available(),
                gradient_accumulation_steps=1,
                dataloader_num_workers=0,
                remove_unused_columns=False,
            )
            self.training_args = training_args

            progress_cb = ProgressCallback(progress_callback=progress_callback)

            early_stopping = EarlyStoppingCallback(
                early_stopping_patience=self.training_config['early_stopping_patience']
            )

            self.trainer = Trainer(
                model=self.model,
                args=training_args,
                train_dataset=train_dataset,
                eval_dataset=eval_dataset,
                compute_metrics=self._compute_metrics,
                callbacks=[progress_cb, early_stopping],
            )

            logger.info("开始训练...")
            train_result = self.trainer.train()

            self.model = self.trainer.model

            metrics = train_result.metrics
            logger.info(f"训练完成，指标: {metrics}")

            self.save_model(output_dir)

            data_version = f"v_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.current_data_version = data_version

            self.training_history.register_data_version(
                version=data_version,
                samples_count=len(dataset),
                label_count=len(self.label_to_id),
                source='initial_training'
            )

            self.training_history.add_record(
                training_type='initial',
                model_path=output_dir,
                data_version=data_version,
                samples_count=len(dataset),
                epochs=self.training_config['num_train_epochs'],
                learning_rate=self.training_config['learning_rate'],
                metrics=metrics,
                config=self.training_config
            )

            if finished_callback:
                finished_callback(True, "训练完成")

            return True

        except Exception as e:
            error_msg = f"训练失败: {e}"
            logger.error(error_msg, exc_info=True)
            if finished_callback:
                finished_callback(False, error_msg)
            return False

    def train_incremental(
        self,
        dataset: Dataset,
        output_dir: str,
        existing_model_path: Optional[str] = None,
        old_data: Optional[Union[Dataset, Dict[str, Any]]] = None,
        update_mode: str = 'append',
        data_version: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        finished_callback: Optional[Callable[[bool, str], None]] = None
    ) -> bool:
        """
        增量训练（从已有模型继续训练）

        Args:
            dataset: 新训练数据集
            output_dir: 输出目录
            existing_model_path: 已有模型路径，如果为None则尝试加载最新模型
            old_data: 旧训练数据（用于合并），如果为None则只使用新数据
            update_mode: 数据更新模式 ('append', 'update', 'replace')
            data_version: 数据版本标识，如果为None则自动生成
            progress_callback: 进度回调函数
            finished_callback: 完成回调函数

        Returns:
            训练是否成功
        """
        try:
            if len(dataset) < Config.INCREMENTAL_MIN_SAMPLES:
                warning_msg = f"增量训练样本数不足: {len(dataset)} < {Config.INCREMENTAL_MIN_SAMPLES}"
                logger.warning(warning_msg)
                if finished_callback:
                    finished_callback(False, warning_msg)
                return False

            model_path = existing_model_path or self._find_latest_model()
            if model_path and os.path.exists(model_path):
                logger.info(f"从已有模型继续训练: {model_path}")
                self.previous_model_path = model_path
                self.load_model(model_path)
            else:
                logger.info("未找到已有模型，将进行首次训练")

            if old_data is not None:
                logger.info(f"合并训练数据，模式: {update_mode}")
                merged_dataset = self.merge_training_data(old_data, dataset, update_mode)
                logger.info(f"合并后数据集大小: {len(merged_dataset)} 样本")
            else:
                merged_dataset = dataset
                logger.info(f"使用新数据集: {len(merged_dataset)} 样本")

            incremental_config = copy.deepcopy(self.training_config)
            original_learning_rate = incremental_config.get('learning_rate', Config.FINETUNE_LEARNING_RATE)
            adjusted_learning_rate = original_learning_rate * Config.INCREMENTAL_LEARNING_RATE_RATIO
            incremental_config['learning_rate'] = adjusted_learning_rate
            logger.info(f"增量训练学习率调整: {original_learning_rate} -> {adjusted_learning_rate} (比例: {Config.INCREMENTAL_LEARNING_RATE_RATIO})")

            incremental_config['num_train_epochs'] = max(
                1,
                int(self.training_config.get('num_train_epochs', Config.FINETUNE_EPOCHS) * 0.5)
            )
            logger.info(f"增量训练轮数: {incremental_config['num_train_epochs']}")

            original_config = self.training_config
            self.training_config = incremental_config

            if data_version is None:
                data_version = f"v_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.current_data_version = data_version

            self.training_history.register_data_version(
                version=data_version,
                samples_count=len(merged_dataset),
                label_count=len(self.label_to_id) if self.label_to_id else 0,
                source='incremental_training',
                metadata={
                    'update_mode': update_mode,
                    'previous_model': self.previous_model_path,
                    'new_samples': len(dataset)
                }
            )

            def internal_finished_callback(success: bool, message: str):
                if success:
                    self.training_history.add_record(
                        training_type='incremental',
                        model_path=output_dir,
                        data_version=data_version,
                        samples_count=len(merged_dataset),
                        epochs=incremental_config['num_train_epochs'],
                        learning_rate=adjusted_learning_rate,
                        metrics={'new_samples': len(dataset)},
                        config=incremental_config
                    )
                    logger.info(f"增量训练历史已记录: {data_version}")

                self.training_config = original_config

                if finished_callback:
                    finished_callback(success, message)

            result = self.train(
                merged_dataset,
                output_dir,
                progress_callback=progress_callback,
                finished_callback=internal_finished_callback
            )

            if not result:
                self.training_config = original_config

            return result

        except Exception as e:
            error_msg = f"增量训练失败: {e}"
            logger.error(error_msg, exc_info=True)
            if finished_callback:
                finished_callback(False, error_msg)
            return False

    def _find_latest_model(self) -> Optional[str]:
        """
        查找最新的训练模型

        Returns:
            最新模型路径，如果不存在则返回 None
        """
        try:
            trained_models_dir = Config.TRAINED_MODELS_DIR
            if not os.path.exists(trained_models_dir):
                return None

            model_dirs = []
            for item in os.listdir(trained_models_dir):
                item_path = os.path.join(trained_models_dir, item)
                if os.path.isdir(item_path):
                    config_path = os.path.join(item_path, 'config.json')
                    if os.path.exists(config_path):
                        model_dirs.append((item_path, os.path.getmtime(item_path)))

            if not model_dirs:
                return None

            model_dirs.sort(key=lambda x: x[1], reverse=True)
            latest_model_path = model_dirs[0][0]
            logger.info(f"找到最新模型: {latest_model_path}")
            return latest_model_path

        except Exception as e:
            logger.warning(f"查找最新模型失败: {e}")
            return None

    def get_training_history(self) -> Dict[str, Any]:
        """
        获取训练历史记录

        Returns:
            训练历史字典
        """
        return self.training_history.to_dict()

    def get_incremental_info(self) -> Dict[str, Any]:
        """
        获取增量训练信息

        Returns:
            增量训练信息字典
        """
        return {
            'incremental_count': self.training_history.get_incremental_count(),
            'total_samples_trained': self.training_history.get_total_samples_trained(),
            'current_data_version': self.current_data_version,
            'previous_model_path': self.previous_model_path,
            'latest_record': self.training_history.get_latest_record()
        }

    def evaluate(self, dataset: Dataset) -> Dict[str, float]:
        """
        评估模型

        Args:
            dataset: 评估数据集

        Returns:
            评估指标字典
        """
        if self.trainer is None or self.model is None:
            raise ValueError("模型未训练或未加载")

        try:
            metrics = self.trainer.evaluate(dataset)
            logger.info(f"评估结果: {metrics}")
            return metrics

        except Exception as e:
            logger.error(f"评估失败: {e}")
            raise

    def save_model(self, output_dir: str) -> bool:
        """
        保存模型

        Args:
            output_dir: 输出目录

        Returns:
            保存是否成功
        """
        try:
            os.makedirs(output_dir, exist_ok=True)

            if self.model is not None:
                self.model.save_pretrained(output_dir)
                logger.info(f"模型已保存到: {output_dir}")

            if self.tokenizer is not None:
                self.tokenizer.save_pretrained(output_dir)
                logger.info(f"Tokenizer已保存到: {output_dir}")

            label_mapping_path = os.path.join(output_dir, 'label_mapping.json')
            with open(label_mapping_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'label_to_id': self.label_to_id,
                    'id_to_label': {str(k): v for k, v in self.id_to_label.items()}
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"标签映射已保存到: {label_mapping_path}")

            config_path = os.path.join(output_dir, 'training_config.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'training_config': self.training_config,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'device': str(self.device),
                    'num_labels': len(self.label_to_id)
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"训练配置已保存到: {config_path}")

            return True

        except Exception as e:
            logger.error(f"保存模型失败: {e}")
            return False

    def load_model(self, model_dir: str) -> bool:
        """
        加载模型

        Args:
            model_dir: 模型目录

        Returns:
            加载是否成功
        """
        try:
            if not os.path.exists(model_dir):
                logger.error(f"模型目录不存在: {model_dir}")
                return False

            label_mapping_path = os.path.join(model_dir, 'label_mapping.json')
            if os.path.exists(label_mapping_path):
                with open(label_mapping_path, 'r', encoding='utf-8') as f:
                    mapping_data = json.load(f)
                    self.label_to_id = mapping_data.get('label_to_id', {})
                    id_to_label_str = mapping_data.get('id_to_label', {})
                    self.id_to_label = {int(k): v for k, v in id_to_label_str.items()}
                logger.info(f"标签映射已加载: {len(self.label_to_id)} 个标签")

            num_labels = len(self.label_to_id) if self.label_to_id else 2

            self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_dir,
                num_labels=num_labels,
                ignore_mismatched_sizes=True,
                problem_type="single_label_classification"
            )
            self.model.to(self.device)

            config_path = os.path.join(model_dir, 'training_config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    self.training_config.update(saved_config.get('training_config', {}))
                logger.info("训练配置已加载")

            logger.info(f"模型已从 {model_dir} 加载到设备 {self.device}")
            return True

        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            return False

    def predict(self, texts: List[str], batch_size: int = 4) -> Tuple[List[int], List[str], List[float]]:
        """
        预测文本类别

        Args:
            texts: 文本列表
            batch_size: 批处理大小，默认为4，可根据内存情况调整

        Returns:
            Tuple[predicted_ids, predicted_labels, confidence_scores]
        """
        if self.model is None or self.tokenizer is None:
            raise ValueError("模型未加载")

        try:
            self.model.eval()

            # 批处理预测
            all_predicted_ids = []
            all_predicted_labels = []
            all_confidence_scores = []

            # 将文本分成批次
            total_batches = (len(texts) + batch_size - 1) // batch_size
            logger.info(f"开始预测，共 {len(texts)} 个文本，分 {total_batches} 批处理，每批 {batch_size} 个")

            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                batch_start = i + 1
                batch_end = min(i + batch_size, len(texts))
                logger.debug(f"处理批次 {batch_start}-{batch_end}/{len(texts)}")
                
                encodings = self.tokenizer(
                    batch_texts,
                    truncation=True,
                    padding=True,
                    max_length=self.training_config.get('max_length', 512),  # 恢复默认max_length
                    return_tensors='pt'
                )

                encodings = {k: v.to(self.device) for k, v in encodings.items()}

                with torch.no_grad():
                    outputs = self.model(**encodings)
                    logits = outputs.logits
                    probabilities = torch.softmax(logits, dim=-1)
                    predictions = torch.argmax(logits, dim=-1)
                    confidence_scores = torch.max(probabilities, dim=-1).values

                batch_predicted_ids = predictions.cpu().numpy().tolist()
                batch_predicted_labels = [self.id_to_label.get(pid, "未知") for pid in batch_predicted_ids]
                batch_confidence_scores = confidence_scores.cpu().numpy().tolist()

                all_predicted_ids.extend(batch_predicted_ids)
                all_predicted_labels.extend(batch_predicted_labels)
                all_confidence_scores.extend(batch_confidence_scores)

                # 清理内存
                del encodings, outputs, logits, probabilities, predictions, confidence_scores
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                else:
                    # 对于CPU，强制进行垃圾回收
                    import gc
                    gc.collect()

            logger.info(f"预测完成，共处理 {len(all_predicted_ids)} 个文本")
            return all_predicted_ids, all_predicted_labels, all_confidence_scores

        except Exception as e:
            logger.error(f"预测失败: {e}")
            raise

    def get_training_progress(self) -> Dict[str, Any]:
        """
        获取训练进度信息

        Returns:
            进度信息字典
        """
        if self.trainer is None:
            return {
                'status': 'not_started',
                'current_step': 0,
                'total_steps': 0,
                'current_epoch': 0,
                'total_epochs': 0
            }

        state = self.trainer.state
        return {
            'status': 'training' if state.is_world_process_zero else 'running',
            'current_step': state.global_step,
            'total_steps': state.max_steps,
            'current_epoch': state.epoch,
            'total_epochs': self.training_config['num_train_epochs'],
            'loss_history': state.log_history
        }

    def is_model_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.model is not None and self.tokenizer is not None

    def get_num_labels(self) -> int:
        """获取标签数量"""
        return len(self.label_to_id) if self.label_to_id else 0

    def get_label_info(self) -> Dict[str, Any]:
        """获取标签信息"""
        return {
            'num_labels': len(self.label_to_id),
            'label_to_id': self.label_to_id,
            'id_to_label': self.id_to_label
        }
