import json
import logging
import os
import pickle
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import torch
from torch.utils.data import Dataset

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class MockTokenizer:
    """Mock Tokenizer for testing"""
    
    def __init__(self):
        self.vocab_size = 10000
        self.pad_token_id = 0
        
    def __call__(self, texts, **kwargs):
        if isinstance(texts, str):
            texts = [texts]
        batch_size = len(texts)
        max_length = kwargs.get('max_length', 512)
        return {
            'input_ids': torch.randint(1, 1000, (batch_size, max_length)),
            'attention_mask': torch.ones(batch_size, max_length, dtype=torch.long)
        }
    
    def save_pretrained(self, path):
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, 'tokenizer_config.json'), 'w') as f:
            json.dump({'vocab_size': self.vocab_size}, f)
    
    @classmethod
    def from_pretrained(cls, path, **kwargs):
        return cls()


class MockModel:
    """Mock Model for testing"""
    
    def __init__(self, num_labels=2):
        self.num_labels = num_labels
        self.config = Mock()
        self.config.num_labels = num_labels
        
    def to(self, device):
        return self
    
    def eval(self):
        return self
    
    def save_pretrained(self, path):
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, 'config.json'), 'w') as f:
            json.dump({'num_labels': self.num_labels}, f)
        torch.save({}, os.path.join(path, 'pytorch_model.bin'))
    
    @classmethod
    def from_pretrained(cls, path, **kwargs):
        num_labels = kwargs.get('num_labels', 2)
        return cls(num_labels=num_labels)


class MockDataset(Dataset):
    """Mock Dataset for testing"""
    
    def __init__(self, texts: List[str], labels: List[int], tokenizer=None, max_length: int = 128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer or MockTokenizer()
        self.max_length = max_length
        self.label_to_id = {str(label): label for label in set(labels)}
        self.id_to_label = {label: str(label) for label in set(labels)}
        
        if len(texts) != len(labels):
            raise ValueError(f"文本数量({len(texts)})与标签数量({len(labels)})不匹配")
    
    def __len__(self) -> int:
        return len(self.texts)
    
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        encoding = self.tokenizer(
            self.texts[idx],
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        return {
            'input_ids': encoding['input_ids'].squeeze(0),
            'attention_mask': encoding['attention_mask'].squeeze(0),
            'labels': torch.tensor(self.labels[idx], dtype=torch.long)
        }


class MockModelManager:
    """Mock ModelManager for testing"""
    
    def __init__(self):
        self.models = {}
        self.tokenizers = {}
        self.device = torch.device("cpu")
        self.trained_model = None
        self._bert_finetuner = None
        
    def get_embeddings(self, texts: List[str], model_type: str = 'bert') -> np.ndarray:
        np.random.seed(42)
        return np.random.randn(len(texts), 768).astype(np.float32)
    
    def save_trained_model(self, model_data: Dict[str, Any], version: str = None) -> bool:
        self.trained_model = model_data
        return True
    
    def load_trained_model(self, version: str = None) -> bool:
        return self.trained_model is not None
    
    def save_finetuned_bert(self, model_dir: str, metadata: Dict[str, Any], label_mapping: Dict[str, int]) -> bool:
        os.makedirs(model_dir, exist_ok=True)
        with open(os.path.join(model_dir, 'training_metadata.json'), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        with open(os.path.join(model_dir, 'label_mapping.json'), 'w', encoding='utf-8') as f:
            json.dump({'label_to_id': label_mapping, 'id_to_label': {str(v): k for k, v in label_mapping.items()}}, 
                     f, ensure_ascii=False, indent=2)
        return True
    
    def load_finetuned_bert(self, model_dir: str):
        if not os.path.exists(model_dir):
            return None, None
        label_mapping_path = os.path.join(model_dir, 'label_mapping.json')
        if os.path.exists(label_mapping_path):
            with open(label_mapping_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return Mock(), data.get('label_to_id', {})
        return None, None
    
    def detect_model_format(self, model_dir: str) -> str:
        if not os.path.exists(model_dir):
            return "classifier"
        config_path = os.path.join(model_dir, 'config.json')
        pytorch_model_path = os.path.join(model_dir, 'pytorch_model.bin')
        label_mapping_path = os.path.join(model_dir, 'label_mapping.json')
        
        if os.path.exists(config_path) and (os.path.exists(pytorch_model_path) or os.path.exists(os.path.join(model_dir, 'model.safetensors'))) and os.path.exists(label_mapping_path):
            return "bert_finetune"
        return "classifier"
    
    def check_gpu_memory(self) -> Dict[str, Any]:
        return {
            'available': False,
            'memory_total': 0,
            'memory_free': 0,
            'memory_used': 0
        }
    
    def check_training_conditions(self) -> Dict[str, Any]:
        return {
            'can_train': True,
            'gpu_available': False,
            'memory_sufficient': True,
            'warnings': []
        }


class TestBERTFineTunerInit(unittest.TestCase):
    """测试BERTFineTuner初始化"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.model_manager = MockModelManager()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_bert_finetuner_init(self):
        with patch('bert_finetuner.AutoTokenizer') as mock_tokenizer, \
             patch('bert_finetuner.AutoModelForSequenceClassification') as mock_model, \
             patch('bert_finetuner.Config') as mock_config:
            
            mock_config.TRAINED_MODELS_DIR = self.temp_dir
            mock_config.LOCAL_MODELS_DIR = self.temp_dir
            mock_config.DEFAULT_MODEL_NAME = "bert-base-chinese"
            mock_config.FINETUNE_LEARNING_RATE = 2e-5
            mock_config.FINETUNE_EPOCHS = 3
            mock_config.FINETUNE_BATCH_SIZE = 16
            mock_config.FINETUNE_WARMUP_RATIO = 0.1
            mock_config.FINETUNE_WEIGHT_DECAY = 0.01
            mock_config.FINETUNE_EARLY_STOP_PATIENCE = 3
            mock_config.FINETUNE_MAX_GRAD_NORM = 1.0
            mock_config.FINETUNE_DROPOUT_RATE = 0.1
            mock_config.MAX_SENTENCE_LENGTH = 512
            
            from bert_finetuner import BERTFineTuner
            
            finetuner = BERTFineTuner(self.model_manager)
            
            self.assertIsNotNone(finetuner)
            self.assertIsNotNone(finetuner.training_config)
            self.assertIn('learning_rate', finetuner.training_config)
            self.assertIn('num_train_epochs', finetuner.training_config)
    
    def test_bert_finetuner_init_with_custom_config(self):
        with patch('bert_finetuner.Config') as mock_config:
            mock_config.TRAINED_MODELS_DIR = self.temp_dir
            mock_config.LOCAL_MODELS_DIR = self.temp_dir
            mock_config.DEFAULT_MODEL_NAME = "bert-base-chinese"
            mock_config.FINETUNE_LEARNING_RATE = 2e-5
            mock_config.FINETUNE_EPOCHS = 3
            mock_config.FINETUNE_BATCH_SIZE = 16
            mock_config.FINETUNE_WARMUP_RATIO = 0.1
            mock_config.FINETUNE_WEIGHT_DECAY = 0.01
            mock_config.FINETUNE_EARLY_STOP_PATIENCE = 3
            mock_config.FINETUNE_MAX_GRAD_NORM = 1.0
            mock_config.FINETUNE_DROPOUT_RATE = 0.1
            mock_config.MAX_SENTENCE_LENGTH = 512
            
            from bert_finetuner import BERTFineTuner
            
            custom_config = {
                'learning_rate': 1e-5,
                'num_train_epochs': 5,
                'batch_size': 32
            }
            
            finetuner = BERTFineTuner(self.model_manager, config=custom_config)
            
            self.assertEqual(finetuner.training_config['learning_rate'], 1e-5)
            self.assertEqual(finetuner.training_config['num_train_epochs'], 5)
            self.assertEqual(finetuner.training_config['per_device_train_batch_size'], 32)


class TestDatasetCreation(unittest.TestCase):
    """测试数据集创建"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.tokenizer = MockTokenizer()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_dataset(self):
        texts = ["这是测试文本1", "这是测试文本2", "这是测试文本3"]
        labels = [0, 1, 0]
        
        dataset = MockDataset(texts, labels, self.tokenizer)
        
        self.assertEqual(len(dataset), 3)
        self.assertEqual(dataset.texts, texts)
        self.assertEqual(dataset.labels, labels)
    
    def test_create_dataset_with_label_mapping(self):
        texts = ["文本A", "文本B", "文本C"]
        labels = [0, 1, 2]
        
        dataset = MockDataset(texts, labels, self.tokenizer)
        
        self.assertIn(0, dataset.label_to_id.values())
        self.assertIn(1, dataset.label_to_id.values())
        self.assertIn(2, dataset.label_to_id.values())
    
    def test_create_dataset_mismatched_lengths(self):
        texts = ["文本1", "文本2"]
        labels = [0, 1, 2]
        
        with self.assertRaises(ValueError):
            MockDataset(texts, labels, self.tokenizer)
    
    def test_dataset_getitem(self):
        texts = ["测试文本"]
        labels = [1]
        
        dataset = MockDataset(texts, labels, self.tokenizer)
        item = dataset[0]
        
        self.assertIn('input_ids', item)
        self.assertIn('attention_mask', item)
        self.assertIn('labels', item)
        self.assertEqual(item['labels'].item(), 1)


class TestTrainAndSave(unittest.TestCase):
    """测试训练和保存模型"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.model_manager = MockModelManager()
        self.tokenizer = MockTokenizer()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_train_and_save(self):
        with patch('bert_finetuner.AutoTokenizer') as mock_tokenizer_cls, \
             patch('bert_finetuner.AutoModelForSequenceClassification') as mock_model_cls, \
             patch('bert_finetuner.Trainer') as mock_trainer_cls, \
             patch('bert_finetuner.TrainingArguments') as mock_args_cls, \
             patch('bert_finetuner.Config') as mock_config:
            
            mock_config.TRAINED_MODELS_DIR = self.temp_dir
            mock_config.LOCAL_MODELS_DIR = self.temp_dir
            mock_config.DEFAULT_MODEL_NAME = "bert-base-chinese"
            mock_config.FINETUNE_LEARNING_RATE = 2e-5
            mock_config.FINETUNE_EPOCHS = 1
            mock_config.FINETUNE_BATCH_SIZE = 2
            mock_config.FINETUNE_WARMUP_RATIO = 0.1
            mock_config.FINETUNE_WEIGHT_DECAY = 0.01
            mock_config.FINETUNE_EARLY_STOP_PATIENCE = 3
            mock_config.FINETUNE_MAX_GRAD_NORM = 1.0
            mock_config.FINETUNE_DROPOUT_RATE = 0.1
            mock_config.MAX_SENTENCE_LENGTH = 128
            
            mock_tokenizer_cls.from_pretrained.return_value = self.tokenizer
            mock_model = Mock()
            mock_model.to.return_value = mock_model
            mock_model_cls.from_pretrained.return_value = mock_model
            
            mock_trainer = Mock()
            mock_trainer.train.return_value = Mock(metrics={'train_loss': 0.5})
            mock_trainer.model = mock_model
            mock_trainer_cls.return_value = mock_trainer
            
            from bert_finetuner import BERTFineTuner
            
            finetuner = BERTFineTuner(self.model_manager, config={'num_train_epochs': 1})
            
            texts = ["文本1", "文本2", "文本3", "文本4"]
            labels = [0, 1, 0, 1]
            dataset = MockDataset(texts, labels, self.tokenizer)
            
            output_dir = os.path.join(self.temp_dir, "test_model")
            
            with patch.object(finetuner, 'save_model') as mock_save:
                mock_save.return_value = True
                result = finetuner.train(dataset, output_dir)
            
            self.assertTrue(result)


class TestLoadAndPredict(unittest.TestCase):
    """测试加载模型和预测"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.model_manager = MockModelManager()
        self.tokenizer = MockTokenizer()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_and_predict(self):
        with patch('bert_finetuner.AutoTokenizer') as mock_tokenizer_cls, \
             patch('bert_finetuner.AutoModelForSequenceClassification') as mock_model_cls, \
             patch('bert_finetuner.Config') as mock_config:
            
            mock_config.TRAINED_MODELS_DIR = self.temp_dir
            mock_config.LOCAL_MODELS_DIR = self.temp_dir
            mock_config.DEFAULT_MODEL_NAME = "bert-base-chinese"
            mock_config.FINETUNE_LEARNING_RATE = 2e-5
            mock_config.FINETUNE_EPOCHS = 3
            mock_config.FINETUNE_BATCH_SIZE = 16
            mock_config.FINETUNE_WARMUP_RATIO = 0.1
            mock_config.FINETUNE_WEIGHT_DECAY = 0.01
            mock_config.FINETUNE_EARLY_STOP_PATIENCE = 3
            mock_config.FINETUNE_MAX_GRAD_NORM = 1.0
            mock_config.FINETUNE_DROPOUT_RATE = 0.1
            mock_config.MAX_SENTENCE_LENGTH = 512
            
            mock_tokenizer_cls.from_pretrained.return_value = self.tokenizer
            
            mock_model = Mock()
            mock_model.eval.return_value = mock_model
            mock_model.to.return_value = mock_model
            mock_model.return_value = Mock(logits=torch.randn(1, 2))
            mock_model_cls.from_pretrained.return_value = mock_model
            
            from bert_finetuner import BERTFineTuner
            
            finetuner = BERTFineTuner(self.model_manager)
            
            model_dir = os.path.join(self.temp_dir, "test_model")
            os.makedirs(model_dir, exist_ok=True)
            
            with open(os.path.join(model_dir, 'label_mapping.json'), 'w', encoding='utf-8') as f:
                json.dump({
                    'label_to_id': {'类别A': 0, '类别B': 1},
                    'id_to_label': {'0': '类别A', '1': '类别B'}
                }, f)
            
            with open(os.path.join(model_dir, 'config.json'), 'w') as f:
                json.dump({'num_labels': 2}, f)
            
            torch.save({}, os.path.join(model_dir, 'pytorch_model.bin'))
            
            result = finetuner.load_model(model_dir)
            self.assertTrue(result)
    
    def test_predict_without_model(self):
        with patch('bert_finetuner.Config') as mock_config:
            mock_config.TRAINED_MODELS_DIR = self.temp_dir
            mock_config.LOCAL_MODELS_DIR = self.temp_dir
            mock_config.DEFAULT_MODEL_NAME = "bert-base-chinese"
            mock_config.FINETUNE_LEARNING_RATE = 2e-5
            mock_config.FINETUNE_EPOCHS = 3
            mock_config.FINETUNE_BATCH_SIZE = 16
            mock_config.FINETUNE_WARMUP_RATIO = 0.1
            mock_config.FINETUNE_WEIGHT_DECAY = 0.01
            mock_config.FINETUNE_EARLY_STOP_PATIENCE = 3
            mock_config.FINETUNE_MAX_GRAD_NORM = 1.0
            mock_config.FINETUNE_DROPOUT_RATE = 0.1
            mock_config.MAX_SENTENCE_LENGTH = 512
            
            from bert_finetuner import BERTFineTuner
            
            finetuner = BERTFineTuner(self.model_manager)
            
            with self.assertRaises(ValueError):
                finetuner.predict(["测试文本"])


class TestIncrementalTraining(unittest.TestCase):
    """测试增量训练"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.model_manager = MockModelManager()
        self.tokenizer = MockTokenizer()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_incremental_training(self):
        with patch('bert_finetuner.AutoTokenizer') as mock_tokenizer_cls, \
             patch('bert_finetuner.AutoModelForSequenceClassification') as mock_model_cls, \
             patch('bert_finetuner.Config') as mock_config:
            
            mock_config.TRAINED_MODELS_DIR = self.temp_dir
            mock_config.LOCAL_MODELS_DIR = self.temp_dir
            mock_config.DEFAULT_MODEL_NAME = "bert-base-chinese"
            mock_config.FINETUNE_LEARNING_RATE = 2e-5
            mock_config.FINETUNE_EPOCHS = 3
            mock_config.FINETUNE_BATCH_SIZE = 16
            mock_config.FINETUNE_WARMUP_RATIO = 0.1
            mock_config.FINETUNE_WEIGHT_DECAY = 0.01
            mock_config.FINETUNE_EARLY_STOP_PATIENCE = 3
            mock_config.FINETUNE_MAX_GRAD_NORM = 1.0
            mock_config.FINETUNE_DROPOUT_RATE = 0.1
            mock_config.MAX_SENTENCE_LENGTH = 512
            mock_config.INCREMENTAL_MIN_SAMPLES = 10
            mock_config.INCREMENTAL_LEARNING_RATE_RATIO = 0.5
            
            mock_tokenizer_cls.from_pretrained.return_value = self.tokenizer
            mock_model = Mock()
            mock_model.to.return_value = mock_model
            mock_model_cls.from_pretrained.return_value = mock_model
            
            from bert_finetuner import BERTFineTuner
            
            finetuner = BERTFineTuner(self.model_manager)
            
            texts = [f"新文本{i}" for i in range(15)]
            labels = [i % 3 for i in range(15)]
            new_dataset = MockDataset(texts, labels, self.tokenizer)
            
            output_dir = os.path.join(self.temp_dir, "incremental_model")
            
            with patch.object(finetuner, 'train') as mock_train:
                mock_train.return_value = True
                result = finetuner.train_incremental(
                    new_dataset,
                    output_dir,
                    existing_model_path=None
                )
            
            self.assertTrue(result)
    
    def test_incremental_training_insufficient_samples(self):
        with patch('bert_finetuner.Config') as mock_config:
            mock_config.TRAINED_MODELS_DIR = self.temp_dir
            mock_config.LOCAL_MODELS_DIR = self.temp_dir
            mock_config.DEFAULT_MODEL_NAME = "bert-base-chinese"
            mock_config.FINETUNE_LEARNING_RATE = 2e-5
            mock_config.FINETUNE_EPOCHS = 3
            mock_config.FINETUNE_BATCH_SIZE = 16
            mock_config.FINETUNE_WARMUP_RATIO = 0.1
            mock_config.FINETUNE_WEIGHT_DECAY = 0.01
            mock_config.FINETUNE_EARLY_STOP_PATIENCE = 3
            mock_config.FINETUNE_MAX_GRAD_NORM = 1.0
            mock_config.FINETUNE_DROPOUT_RATE = 0.1
            mock_config.MAX_SENTENCE_LENGTH = 512
            mock_config.INCREMENTAL_MIN_SAMPLES = 10
            
            from bert_finetuner import BERTFineTuner
            
            finetuner = BERTFineTuner(self.model_manager)
            
            texts = [f"文本{i}" for i in range(5)]
            labels = [0, 1, 0, 1, 0]
            small_dataset = MockDataset(texts, labels, self.tokenizer)
            
            output_dir = os.path.join(self.temp_dir, "test_model")
            
            result = finetuner.train_incremental(small_dataset, output_dir)
            self.assertFalse(result)


class TestTrainingHistory(unittest.TestCase):
    """测试训练历史记录"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_training_history(self):
        from bert_finetuner import TrainingHistory
        
        history_file = os.path.join(self.temp_dir, "history.json")
        history = TrainingHistory(history_file)
        
        history.add_record(
            training_type='initial',
            model_path='/path/to/model',
            data_version='v1',
            samples_count=100,
            epochs=3,
            learning_rate=2e-5,
            metrics={'accuracy': 0.9},
            config={}
        )
        
        self.assertEqual(len(history.records), 1)
        self.assertEqual(history.records[0]['training_type'], 'initial')
        self.assertEqual(history.records[0]['samples_count'], 100)
    
    def test_training_history_persistence(self):
        from bert_finetuner import TrainingHistory
        
        history_file = os.path.join(self.temp_dir, "history.json")
        
        history1 = TrainingHistory(history_file)
        history1.add_record(
            training_type='initial',
            model_path='/path/to/model',
            data_version='v1',
            samples_count=100,
            epochs=3,
            learning_rate=2e-5
        )
        
        history2 = TrainingHistory(history_file)
        self.assertEqual(len(history2.records), 1)
        self.assertEqual(history2.records[0]['training_type'], 'initial')
    
    def test_get_incremental_count(self):
        from bert_finetuner import TrainingHistory
        
        history = TrainingHistory()
        
        history.add_record('initial', '/path1', 'v1', 100, 3, 2e-5)
        history.add_record('incremental', '/path2', 'v2', 50, 2, 1e-5)
        history.add_record('incremental', '/path3', 'v3', 30, 1, 1e-5)
        
        self.assertEqual(history.get_incremental_count(), 2)
    
    def test_get_total_samples_trained(self):
        from bert_finetuner import TrainingHistory
        
        history = TrainingHistory()
        
        history.add_record('initial', '/path1', 'v1', 100, 3, 2e-5)
        history.add_record('incremental', '/path2', 'v2', 50, 2, 1e-5)
        
        self.assertEqual(history.get_total_samples_trained(), 150)


class TestMergeTrainingData(unittest.TestCase):
    """测试数据合并"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.model_manager = MockModelManager()
        self.tokenizer = MockTokenizer()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_merge_training_data_append(self):
        with patch('bert_finetuner.AutoTokenizer') as mock_tokenizer_cls, \
             patch('bert_finetuner.Config') as mock_config:
            
            mock_config.TRAINED_MODELS_DIR = self.temp_dir
            mock_config.LOCAL_MODELS_DIR = self.temp_dir
            mock_config.DEFAULT_MODEL_NAME = "bert-base-chinese"
            mock_config.FINETUNE_LEARNING_RATE = 2e-5
            mock_config.FINETUNE_EPOCHS = 3
            mock_config.FINETUNE_BATCH_SIZE = 16
            mock_config.FINETUNE_WARMUP_RATIO = 0.1
            mock_config.FINETUNE_WEIGHT_DECAY = 0.01
            mock_config.FINETUNE_EARLY_STOP_PATIENCE = 3
            mock_config.FINETUNE_MAX_GRAD_NORM = 1.0
            mock_config.FINETUNE_DROPOUT_RATE = 0.1
            mock_config.MAX_SENTENCE_LENGTH = 512
            
            mock_tokenizer_cls.from_pretrained.return_value = self.tokenizer
            
            from bert_finetuner import BERTFineTuner
            
            finetuner = BERTFineTuner(self.model_manager)
            finetuner.tokenizer = self.tokenizer
            finetuner.label_to_id = {'A': 0, 'B': 1}
            finetuner.id_to_label = {0: 'A', 1: 'B'}
            
            old_data = {
                'texts': ['文本1', '文本2'],
                'labels': [0, 1]
            }
            new_data = {
                'texts': ['文本3', '文本4'],
                'labels': [0, 1]
            }
            
            merged = finetuner.merge_training_data(old_data, new_data, 'append')
            
            self.assertEqual(len(merged), 4)
    
    def test_merge_training_data_replace(self):
        with patch('bert_finetuner.Config') as mock_config:
            mock_config.TRAINED_MODELS_DIR = self.temp_dir
            mock_config.LOCAL_MODELS_DIR = self.temp_dir
            mock_config.DEFAULT_MODEL_NAME = "bert-base-chinese"
            mock_config.FINETUNE_LEARNING_RATE = 2e-5
            mock_config.FINETUNE_EPOCHS = 3
            mock_config.FINETUNE_BATCH_SIZE = 16
            mock_config.FINETUNE_WARMUP_RATIO = 0.1
            mock_config.FINETUNE_WEIGHT_DECAY = 0.01
            mock_config.FINETUNE_EARLY_STOP_PATIENCE = 3
            mock_config.FINETUNE_MAX_GRAD_NORM = 1.0
            mock_config.FINETUNE_DROPOUT_RATE = 0.1
            mock_config.MAX_SENTENCE_LENGTH = 512
            
            from bert_finetuner import BERTFineTuner
            
            finetuner = BERTFineTuner(self.model_manager)
            finetuner.tokenizer = self.tokenizer
            finetuner.label_to_id = {'A': 0, 'B': 1}
            finetuner.id_to_label = {0: 'A', 1: 'B'}
            
            old_data = {'texts': ['旧文本1', '旧文本2'], 'labels': [0, 1]}
            new_data = {'texts': ['新文本1', '新文本2', '新文本3'], 'labels': [0, 1, 0]}
            
            merged = finetuner.merge_training_data(old_data, new_data, 'replace')
            
            self.assertEqual(len(merged), 3)
    
    def test_merge_training_data_update(self):
        with patch('bert_finetuner.Config') as mock_config:
            mock_config.TRAINED_MODELS_DIR = self.temp_dir
            mock_config.LOCAL_MODELS_DIR = self.temp_dir
            mock_config.DEFAULT_MODEL_NAME = "bert-base-chinese"
            mock_config.FINETUNE_LEARNING_RATE = 2e-5
            mock_config.FINETUNE_EPOCHS = 3
            mock_config.FINETUNE_BATCH_SIZE = 16
            mock_config.FINETUNE_WARMUP_RATIO = 0.1
            mock_config.FINETUNE_WEIGHT_DECAY = 0.01
            mock_config.FINETUNE_EARLY_STOP_PATIENCE = 3
            mock_config.FINETUNE_MAX_GRAD_NORM = 1.0
            mock_config.FINETUNE_DROPOUT_RATE = 0.1
            mock_config.MAX_SENTENCE_LENGTH = 512
            
            from bert_finetuner import BERTFineTuner
            
            finetuner = BERTFineTuner(self.model_manager)
            finetuner.tokenizer = self.tokenizer
            finetuner.label_to_id = {'A': 0, 'B': 1}
            finetuner.id_to_label = {0: 'A', 1: 'B'}
            
            old_data = {'texts': ['文本1', '文本2'], 'labels': [0, 1]}
            new_data = {'texts': ['文本1', '文本3'], 'labels': [1, 0]}
            
            merged = finetuner.merge_training_data(old_data, new_data, 'update')
            
            self.assertEqual(len(merged), 3)


class TestGridSearch(unittest.TestCase):
    """测试网格搜索"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.model_manager = MockModelManager()
        self.tokenizer = MockTokenizer()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_grid_search(self):
        from hyperparameter_optimizer import HyperparameterOptimizer
        
        optimizer = HyperparameterOptimizer(self.model_manager)
        
        texts = [f"文本{i}" for i in range(20)]
        labels = [i % 2 for i in range(20)]
        dataset = MockDataset(texts, labels, self.tokenizer)
        
        search_space = {
            'learning_rate': [1e-5, 2e-5],
            'batch_size': [8]
        }
        
        with patch.object(optimizer, 'cross_validate') as mock_cv:
            mock_cv.return_value = (0.8, {'accuracy': 0.8, 'f1': 0.75})
            
            result = optimizer.grid_search(dataset, search_space=search_space, cv_folds=2)
        
        self.assertIn('best_params', result)
        self.assertIn('best_score', result)
        self.assertIn('total_combinations', result)


class TestCrossValidate(unittest.TestCase):
    """测试交叉验证"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.model_manager = MockModelManager()
        self.tokenizer = MockTokenizer()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cross_validate(self):
        with patch('hyperparameter_optimizer.Config') as mock_config:
            mock_config.TRAINED_MODELS_DIR = self.temp_dir
            mock_config.LOCAL_MODELS_DIR = self.temp_dir
            mock_config.HYPERPARAM_CV_FOLDS = 2
            mock_config.DEFAULT_MODEL_NAME = "bert-base-chinese"
            mock_config.FINETUNE_LEARNING_RATE = 2e-5
            mock_config.FINETUNE_EPOCHS = 1
            mock_config.FINETUNE_BATCH_SIZE = 8
            mock_config.FINETUNE_WARMUP_RATIO = 0.1
            mock_config.FINETUNE_WEIGHT_DECAY = 0.01
            mock_config.FINETUNE_EARLY_STOP_PATIENCE = 3
            mock_config.FINETUNE_MAX_GRAD_NORM = 1.0
            mock_config.FINETUNE_DROPOUT_RATE = 0.1
            mock_config.MAX_SENTENCE_LENGTH = 128
            
            from hyperparameter_optimizer import HyperparameterOptimizer
            
            optimizer = HyperparameterOptimizer(self.model_manager)
            
            texts = [f"文本{i}" for i in range(20)]
            labels = [i % 2 for i in range(20)]
            dataset = MockDataset(texts, labels, self.tokenizer)
            
            params = {'learning_rate': 2e-5, 'batch_size': 8}
            
            with patch.object(optimizer, '_evaluate_fold') as mock_eval:
                mock_eval.return_value = {'accuracy': 0.8, 'f1': 0.75, 'precision': 0.78, 'recall': 0.76}
                
                score, metrics = optimizer.cross_validate(dataset, params, cv_folds=2)
            
            self.assertIsInstance(score, float)
            self.assertIn('accuracy', metrics)
            self.assertIn('f1', metrics)


class TestSaveLoadParams(unittest.TestCase):
    """测试参数保存和加载"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.model_manager = MockModelManager()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_load_params(self):
        with patch('hyperparameter_optimizer.Config') as mock_config:
            mock_config.TRAINED_MODELS_DIR = self.temp_dir
            mock_config.LOCAL_MODELS_DIR = self.temp_dir
            mock_config.HYPERPARAM_SEARCH_SPACE = {'learning_rate': [1e-5, 2e-5]}
            mock_config.HYPERPARAM_CV_FOLDS = 3
            mock_config.DEFAULT_MODEL_NAME = "bert-base-chinese"
            mock_config.FINETUNE_LEARNING_RATE = 2e-5
            mock_config.FINETUNE_EPOCHS = 3
            mock_config.FINETUNE_BATCH_SIZE = 16
            mock_config.FINETUNE_WARMUP_RATIO = 0.1
            mock_config.FINETUNE_WEIGHT_DECAY = 0.01
            mock_config.FINETUNE_EARLY_STOP_PATIENCE = 3
            mock_config.FINETUNE_MAX_GRAD_NORM = 1.0
            mock_config.FINETUNE_DROPOUT_RATE = 0.1
            mock_config.MAX_SENTENCE_LENGTH = 512
            
            from hyperparameter_optimizer import HyperparameterOptimizer
            
            optimizer = HyperparameterOptimizer(self.model_manager)
            
            optimizer.best_params = {'learning_rate': 2e-5, 'batch_size': 16}
            optimizer.best_score = 0.85
            
            params_file = os.path.join(self.temp_dir, 'best_params.json')
            with open(params_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'best_params': optimizer.best_params,
                    'best_score': optimizer.best_score
                }, f)
            
            with open(params_file, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            
            self.assertEqual(loaded['best_params'], {'learning_rate': 2e-5, 'batch_size': 16})
            self.assertEqual(loaded['best_score'], 0.85)


class TestSaveFinetunedBERT(unittest.TestCase):
    """测试保存BERT模型"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.model_manager = MockModelManager()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_finetuned_bert(self):
        model_dir = os.path.join(self.temp_dir, "test_bert_model")
        os.makedirs(model_dir, exist_ok=True)
        
        metadata = {
            'training_time': '2024-01-01 12:00:00',
            'samples_count': 100,
            'accuracy': 0.9
        }
        label_mapping = {'类别A': 0, '类别B': 1}
        
        result = self.model_manager.save_finetuned_bert(model_dir, metadata, label_mapping)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(os.path.join(model_dir, 'training_metadata.json')))
        self.assertTrue(os.path.exists(os.path.join(model_dir, 'label_mapping.json')))
    
    def test_save_finetuned_bert_with_existing_dir(self):
        model_dir = os.path.join(self.temp_dir, "existing_model")
        os.makedirs(model_dir, exist_ok=True)
        
        metadata = {'accuracy': 0.85}
        label_mapping = {'A': 0, 'B': 1, 'C': 2}
        
        result = self.model_manager.save_finetuned_bert(model_dir, metadata, label_mapping)
        
        self.assertTrue(result)


class TestLoadFinetunedBERT(unittest.TestCase):
    """测试加载BERT模型"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.model_manager = MockModelManager()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_finetuned_bert(self):
        model_dir = os.path.join(self.temp_dir, "test_model")
        os.makedirs(model_dir, exist_ok=True)
        
        with open(os.path.join(model_dir, 'config.json'), 'w') as f:
            json.dump({'num_labels': 2}, f)
        
        torch.save({}, os.path.join(model_dir, 'pytorch_model.bin'))
        
        with open(os.path.join(model_dir, 'label_mapping.json'), 'w', encoding='utf-8') as f:
            json.dump({
                'label_to_id': {'类别A': 0, '类别B': 1},
                'id_to_label': {'0': '类别A', '1': '类别B'}
            }, f, ensure_ascii=False)
        
        with open(os.path.join(model_dir, 'training_config.json'), 'w', encoding='utf-8') as f:
            json.dump({'training_config': {'learning_rate': 2e-5}}, f)
        
        model, label_mapping = self.model_manager.load_finetuned_bert(model_dir)
        
        self.assertIsNotNone(label_mapping)
        self.assertIn('类别A', label_mapping)
        self.assertIn('类别B', label_mapping)
    
    def test_load_finetuned_bert_nonexistent(self):
        model, label_mapping = self.model_manager.load_finetuned_bert("/nonexistent/path")
        
        self.assertIsNone(model)
        self.assertIsNone(label_mapping)


class TestDetectModelFormat(unittest.TestCase):
    """测试模型格式检测"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.model_manager = MockModelManager()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_detect_model_format_bert_finetune(self):
        model_dir = os.path.join(self.temp_dir, "bert_model")
        os.makedirs(model_dir, exist_ok=True)
        
        with open(os.path.join(model_dir, 'config.json'), 'w') as f:
            json.dump({'num_labels': 2}, f)
        
        torch.save({}, os.path.join(model_dir, 'pytorch_model.bin'))
        
        with open(os.path.join(model_dir, 'label_mapping.json'), 'w', encoding='utf-8') as f:
            json.dump({'label_to_id': {'A': 0}}, f)
        
        format_type = self.model_manager.detect_model_format(model_dir)
        
        self.assertEqual(format_type, "bert_finetune")
    
    def test_detect_model_format_classifier(self):
        model_dir = os.path.join(self.temp_dir, "classifier_model")
        os.makedirs(model_dir, exist_ok=True)
        
        pkl_file = os.path.join(model_dir, "model.pkl")
        with open(pkl_file, 'wb') as f:
            pickle.dump({'classifier': {'type': 'mock_classifier', 'data': 'test'}}, f)
        
        format_type = self.model_manager.detect_model_format(model_dir)
        
        self.assertEqual(format_type, "classifier")
    
    def test_detect_model_format_nonexistent(self):
        format_type = self.model_manager.detect_model_format("/nonexistent/path")
        
        self.assertEqual(format_type, "classifier")


class TestCheckGPUMemory(unittest.TestCase):
    """测试GPU内存检查"""
    
    def setUp(self):
        self.model_manager = MockModelManager()
        
    def test_check_gpu_memory(self):
        result = self.model_manager.check_gpu_memory()
        
        self.assertIn('available', result)
        self.assertIn('memory_total', result)
        self.assertIn('memory_free', result)
        self.assertIn('memory_used', result)
    
    def test_check_gpu_memory_no_gpu(self):
        result = self.model_manager.check_gpu_memory()
        
        self.assertFalse(result['available'])


class TestCheckTrainingConditions(unittest.TestCase):
    """测试训练条件检查"""
    
    def setUp(self):
        self.model_manager = MockModelManager()
        
    def test_check_training_conditions(self):
        result = self.model_manager.check_training_conditions()
        
        self.assertIn('can_train', result)
        self.assertIn('gpu_available', result)
        self.assertIn('memory_sufficient', result)
        self.assertIn('warnings', result)
    
    def test_check_training_conditions_can_train(self):
        result = self.model_manager.check_training_conditions()
        
        self.assertTrue(result['can_train'])


class TestFallbackToClassifier(unittest.TestCase):
    """测试降级到分类器"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.model_manager = MockModelManager()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_fallback_to_classifier(self):
        texts = ["文本1", "文本2", "文本3"]
        embeddings = self.model_manager.get_embeddings(texts)
        
        self.assertIsNotNone(embeddings)
        self.assertEqual(embeddings.shape[0], 3)
        self.assertEqual(embeddings.shape[1], 768)
    
    def test_fallback_classifier_format_detection(self):
        model_dir = os.path.join(self.temp_dir, "fallback_model")
        os.makedirs(model_dir, exist_ok=True)
        
        format_type = self.model_manager.detect_model_format(model_dir)
        
        self.assertEqual(format_type, "classifier")


class TestTrainingHistoryAdvanced(unittest.TestCase):
    """测试训练历史记录高级功能"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_register_data_version(self):
        from bert_finetuner import TrainingHistory
        
        history = TrainingHistory()
        
        history.register_data_version(
            version='v1',
            samples_count=100,
            label_count=5,
            source='initial_training'
        )
        
        self.assertIn('v1', history.data_versions)
        self.assertEqual(history.data_versions['v1']['samples_count'], 100)
    
    def test_get_records_by_type(self):
        from bert_finetuner import TrainingHistory
        
        history = TrainingHistory()
        
        history.add_record('initial', '/path1', 'v1', 100, 3, 2e-5)
        history.add_record('incremental', '/path2', 'v2', 50, 2, 1e-5)
        history.add_record('incremental', '/path3', 'v3', 30, 1, 1e-5)
        
        initial_records = history.get_records_by_type('initial')
        incremental_records = history.get_records_by_type('incremental')
        
        self.assertEqual(len(initial_records), 1)
        self.assertEqual(len(incremental_records), 2)
    
    def test_get_latest_record(self):
        from bert_finetuner import TrainingHistory
        
        history = TrainingHistory()
        
        self.assertIsNone(history.get_latest_record())
        
        history.add_record('initial', '/path1', 'v1', 100, 3, 2e-5)
        history.add_record('incremental', '/path2', 'v2', 50, 2, 1e-5)
        
        latest = history.get_latest_record()
        
        self.assertIsNotNone(latest)
        self.assertEqual(latest['training_type'], 'incremental')
    
    def test_to_dict(self):
        from bert_finetuner import TrainingHistory
        
        history = TrainingHistory()
        
        history.add_record('initial', '/path1', 'v1', 100, 3, 2e-5)
        history.register_data_version('v1', 100, 5, 'initial')
        
        result = history.to_dict()
        
        self.assertIn('records', result)
        self.assertIn('data_versions', result)
        self.assertIn('summary', result)
        self.assertEqual(result['summary']['total_trainings'], 1)


class TestHyperparameterOptimizerAdvanced(unittest.TestCase):
    """测试超参数优化器高级功能"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.model_manager = MockModelManager()
        self.tokenizer = MockTokenizer()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_optimization_summary(self):
        with patch('hyperparameter_optimizer.Config') as mock_config:
            mock_config.TRAINED_MODELS_DIR = self.temp_dir
            mock_config.LOCAL_MODELS_DIR = self.temp_dir
            mock_config.HYPERPARAM_SEARCH_SPACE = {'learning_rate': [1e-5, 2e-5]}
            mock_config.HYPERPARAM_CV_FOLDS = 3
            mock_config.DEFAULT_MODEL_NAME = "bert-base-chinese"
            mock_config.FINETUNE_LEARNING_RATE = 2e-5
            mock_config.FINETUNE_EPOCHS = 3
            mock_config.FINETUNE_BATCH_SIZE = 16
            mock_config.FINETUNE_WARMUP_RATIO = 0.1
            mock_config.FINETUNE_WEIGHT_DECAY = 0.01
            mock_config.FINETUNE_EARLY_STOP_PATIENCE = 3
            mock_config.FINETUNE_MAX_GRAD_NORM = 1.0
            mock_config.FINETUNE_DROPOUT_RATE = 0.1
            mock_config.MAX_SENTENCE_LENGTH = 512
            
            from hyperparameter_optimizer import HyperparameterOptimizer
            
            optimizer = HyperparameterOptimizer(self.model_manager)
            optimizer.best_params = {'learning_rate': 2e-5}
            optimizer.best_score = 0.85
            
            summary = optimizer.get_optimization_summary()
            
            self.assertIn('best_params', summary)
            self.assertIn('best_score', summary)
            self.assertIn('device', summary)
    
    def test_get_top_n_params(self):
        with patch('hyperparameter_optimizer.Config') as mock_config:
            mock_config.TRAINED_MODELS_DIR = self.temp_dir
            mock_config.LOCAL_MODELS_DIR = self.temp_dir
            mock_config.HYPERPARAM_SEARCH_SPACE = {'learning_rate': [1e-5, 2e-5]}
            mock_config.HYPERPARAM_CV_FOLDS = 3
            mock_config.DEFAULT_MODEL_NAME = "bert-base-chinese"
            mock_config.FINETUNE_LEARNING_RATE = 2e-5
            mock_config.FINETUNE_EPOCHS = 3
            mock_config.FINETUNE_BATCH_SIZE = 16
            mock_config.FINETUNE_WARMUP_RATIO = 0.1
            mock_config.FINETUNE_WEIGHT_DECAY = 0.01
            mock_config.FINETUNE_EARLY_STOP_PATIENCE = 3
            mock_config.FINETUNE_MAX_GRAD_NORM = 1.0
            mock_config.FINETUNE_DROPOUT_RATE = 0.1
            mock_config.MAX_SENTENCE_LENGTH = 512
            
            from hyperparameter_optimizer import HyperparameterOptimizer
            
            optimizer = HyperparameterOptimizer(self.model_manager)
            
            optimizer.optimization_history = [
                {'params': {'lr': 1e-5}, 'score': 0.7},
                {'params': {'lr': 2e-5}, 'score': 0.9},
                {'params': {'lr': 5e-5}, 'score': 0.8}
            ]
            
            top_params = optimizer.get_top_n_params(2)
            
            self.assertEqual(len(top_params), 2)
            self.assertEqual(top_params[0]['score'], 0.9)
            self.assertEqual(top_params[1]['score'], 0.8)


if __name__ == '__main__':
    import pickle
    unittest.main(verbosity=2)
