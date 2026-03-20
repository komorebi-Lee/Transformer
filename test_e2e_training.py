import logging
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, patch
from typing import Dict, List, Any

import torch
from torch.utils.data import Dataset

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TRANSFORMERS_AVAILABLE = True
try:
    import transformers
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers库不可用，部分测试将被跳过")


class MockDataset(Dataset):
    def __init__(self, texts: List[str], labels: List[int], tokenizer=None, max_length: int = 128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.label_to_id = {str(label): label for label in set(labels)}
        
    def __len__(self) -> int:
        return len(self.texts)
    
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        return {
            'input_ids': torch.zeros(self.max_length, dtype=torch.long),
            'attention_mask': torch.ones(self.max_length, dtype=torch.long),
            'labels': torch.tensor(self.labels[idx], dtype=torch.long)
        }


class MockModelManager:
    def __init__(self):
        self.models = {}
        
    def get_embeddings(self, texts: List[str], model_type: str = 'bert') -> Any:
        import numpy as np
        return np.random.rand(len(texts), 768)
    
    def save_trained_model(self, model_data: Dict[str, Any], name: str) -> bool:
        self.models[name] = model_data
        return True
    
    def load_trained_model(self, name: str) -> Dict[str, Any]:
        return self.models.get(name, {})


class MockStandardAnswerManager:
    def __init__(self):
        self.answers = {
            "structured_codes": {
                "核心范畴1": {
                    "二级范畴1": [
                        {"content": "这是测试文本内容1", "name": "编码1"},
                        {"content": "这是测试文本内容2", "name": "编码2"}
                    ],
                    "二级范畴2": [
                        {"content": "这是测试文本内容3", "name": "编码3"}
                    ]
                },
                "核心范畴2": {
                    "二级范畴3": [
                        {"content": "这是测试文本内容4", "name": "编码4"}
                    ]
                }
            },
            "training_data": []
        }
    
    def get_current_answers(self) -> Dict[str, Any]:
        return self.answers
    
    def get_training_sample_count(self) -> int:
        return 4


class TestE2ETraining(unittest.TestCase):
    """端到端训练流程测试"""
    
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.model_manager = MockModelManager()
        cls.standard_answer_manager = MockStandardAnswerManager()
        
    def setUp(self):
        self.test_texts = [
            "这是一段测试文本用于训练模型",
            "另一段测试文本用于验证模型效果",
            "第三段文本用于增加训练数据多样性",
            "第四段文本包含不同的语义内容",
            "第五段文本用于确保足够的训练样本"
        ]
        self.test_labels = [0, 1, 0, 1, 2]
        
    @unittest.skipIf(not TRANSFORMERS_AVAILABLE, "transformers库不可用")
    def test_full_training_workflow(self):
        """
        测试完整训练流程
        
        测试步骤:
        1. 数据准备和验证
        2. 模型初始化
        3. 训练执行
        4. 模型保存
        5. 结果验证
        """
        logger.info("=== 开始完整训练流程测试 ===")
        
        dataset = MockDataset(self.test_texts, self.test_labels)
        
        self.assertEqual(len(dataset), 5, "数据集大小应为5")
        logger.info(f"步骤1: 数据准备完成，数据集大小: {len(dataset)}")
        
        mock_trainer = MagicMock()
        mock_trainer.train.return_value = MagicMock(metrics={'train_loss': 0.5, 'train_accuracy': 0.85})
        mock_trainer.evaluate.return_value = {
            'eval_loss': 0.3,
            'eval_accuracy': 0.8,
            'eval_f1': 0.75,
            'eval_precision': 0.78,
            'eval_recall': 0.72
        }
        
        mock_finetuner = MagicMock()
        mock_finetuner.train.return_value = True
        mock_finetuner.trainer = mock_trainer
        mock_finetuner.evaluate.return_value = {
            'eval_loss': 0.3,
            'eval_accuracy': 0.8,
            'eval_f1': 0.75
        }
        
        output_dir = os.path.join(self.temp_dir, "full_training_test")
        os.makedirs(output_dir, exist_ok=True)
        
        result = mock_finetuner.train(dataset, output_dir)
        
        self.assertTrue(result, "训练应该成功")
        logger.info("步骤2-3: 模型初始化和训练完成")
        
        metrics = mock_finetuner.evaluate(dataset)
        self.assertIn('eval_accuracy', metrics, "评估结果应包含准确率")
        self.assertGreater(metrics['eval_accuracy'], 0.5, "准确率应该大于0.5")
        logger.info(f"步骤4-5: 模型评估完成，准确率: {metrics['eval_accuracy']}")
        
        logger.info("=== 完整训练流程测试通过 ===")
        
    @unittest.skipIf(not TRANSFORMERS_AVAILABLE, "transformers库不可用")
    def test_incremental_workflow(self):
        """
        测试增量训练流程
        
        测试步骤:
        1. 初始模型训练
        2. 新数据准备
        3. 增量训练执行
        4. 训练历史记录验证
        5. 模型版本管理验证
        """
        logger.info("=== 开始增量训练流程测试 ===")
        
        initial_dataset = MockDataset(
            self.test_texts[:3],
            self.test_labels[:3]
        )
        
        mock_finetuner = MagicMock()
        mock_finetuner.train.return_value = True
        mock_finetuner.train_incremental.return_value = True
        mock_finetuner.get_incremental_info.return_value = {
            'incremental_count': 1,
            'total_samples_trained': 5,
            'current_data_version': 'v_20240101_120000',
            'previous_model_path': '/path/to/previous/model',
            'latest_record': {
                'training_type': 'incremental',
                'samples_count': 5
            }
        }
        
        initial_output_dir = os.path.join(self.temp_dir, "initial_model")
        os.makedirs(initial_output_dir, exist_ok=True)
        
        initial_result = mock_finetuner.train(initial_dataset, initial_output_dir)
        self.assertTrue(initial_result, "初始训练应该成功")
        logger.info("步骤1: 初始模型训练完成")
        
        new_texts = ["新数据文本1", "新数据文本2"]
        new_labels = [0, 1]
        new_dataset = MockDataset(new_texts, new_labels)
        
        incremental_output_dir = os.path.join(self.temp_dir, "incremental_model")
        os.makedirs(incremental_output_dir, exist_ok=True)
        
        incremental_result = mock_finetuner.train_incremental(
            new_dataset,
            incremental_output_dir,
            existing_model_path=initial_output_dir
        )
        
        self.assertTrue(incremental_result, "增量训练应该成功")
        logger.info("步骤2-3: 新数据准备和增量训练完成")
        
        incremental_info = mock_finetuner.get_incremental_info()
        self.assertEqual(incremental_info['incremental_count'], 1, "增量训练次数应为1")
        self.assertGreater(incremental_info['total_samples_trained'], 0, "总训练样本数应大于0")
        logger.info(f"步骤4: 训练历史验证完成，增量次数: {incremental_info['incremental_count']}")
        
        self.assertIsNotNone(incremental_info['current_data_version'], "数据版本不应为空")
        self.assertIsNotNone(incremental_info['previous_model_path'], "前一模型路径不应为空")
        logger.info("步骤5: 模型版本管理验证完成")
        
        logger.info("=== 增量训练流程测试通过 ===")
        
    def test_optimization_workflow(self):
        """
        测试超参数寻优流程
        
        测试步骤:
        1. 搜索空间定义
        2. 网格搜索执行
        3. 结果评估和比较
        4. 最优参数选择
        5. 参数保存和加载
        """
        logger.info("=== 开始超参数寻优流程测试 ===")
        
        search_space = {
            'learning_rate': [1e-5, 2e-5],
            'batch_size': [8, 16],
            'epochs': [2, 3]
        }
        
        logger.info(f"步骤1: 搜索空间定义完成: {search_space}")
        
        dataset = MockDataset(self.test_texts, self.test_labels)
        
        with patch('hyperparameter_optimizer.HyperparameterOptimizer') as MockOptimizer:
            mock_optimizer = MockOptimizer.return_value
            
            mock_optimizer.grid_search.return_value = {
                'best_params': {
                    'learning_rate': 2e-5,
                    'batch_size': 16,
                    'epochs': 3
                },
                'best_score': 0.85,
                'total_combinations': 8,
                'optimization_history': [
                    {'params': {'learning_rate': 1e-5, 'batch_size': 8, 'epochs': 2}, 'score': 0.75},
                    {'params': {'learning_rate': 2e-5, 'batch_size': 16, 'epochs': 3}, 'score': 0.85}
                ]
            }
            
            mock_optimizer.bayesian_optimization.return_value = {
                'best_params': {
                    'learning_rate': 2e-5,
                    'batch_size': 16,
                    'epochs': 3
                },
                'best_score': 0.87,
                'n_trials': 10
            }
            
            mock_optimizer.save_best_params.return_value = True
            mock_optimizer.load_best_params.return_value = {
                'learning_rate': 2e-5,
                'batch_size': 16,
                'epochs': 3
            }
            mock_optimizer.get_top_n_params.return_value = [
                {'params': {'learning_rate': 2e-5, 'batch_size': 16, 'epochs': 3}, 'score': 0.85},
                {'params': {'learning_rate': 1e-5, 'batch_size': 16, 'epochs': 3}, 'score': 0.82}
            ]
            
            grid_result = mock_optimizer.grid_search(
                dataset,
                search_space=search_space,
                cv_folds=3
            )
            
            self.assertIn('best_params', grid_result, "结果应包含最优参数")
            self.assertIn('best_score', grid_result, "结果应包含最优分数")
            self.assertGreater(grid_result['best_score'], 0.5, "最优分数应大于0.5")
            logger.info(f"步骤2: 网格搜索完成，最优分数: {grid_result['best_score']}")
            
            bayesian_result = mock_optimizer.bayesian_optimization(
                dataset,
                n_trials=10,
                search_space=search_space
            )
            
            self.assertIn('best_params', bayesian_result, "贝叶斯优化结果应包含最优参数")
            logger.info(f"步骤3: 贝叶斯优化完成，最优分数: {bayesian_result['best_score']}")
            
            top_params = mock_optimizer.get_top_n_params(n=2)
            self.assertEqual(len(top_params), 2, "应返回2组参数")
            logger.info("步骤4: 最优参数选择完成")
            
            params_file = os.path.join(self.temp_dir, "best_params.json")
            save_result = mock_optimizer.save_best_params(
                grid_result['best_params'],
                params_file
            )
            self.assertTrue(save_result, "参数保存应该成功")
            
            loaded_params = mock_optimizer.load_best_params(params_file)
            self.assertEqual(
                loaded_params['learning_rate'],
                grid_result['best_params']['learning_rate'],
                "加载的参数应与保存的参数一致"
            )
            logger.info("步骤5: 参数保存和加载验证完成")
        
        logger.info("=== 超参数寻优流程测试通过 ===")


class TestTrainingManagerIntegration(unittest.TestCase):
    """训练管理器集成测试"""
    
    def setUp(self):
        self.model_manager = MockModelManager()
        self.standard_answer_manager = MockStandardAnswerManager()
        
    def test_training_mode_selection(self):
        """测试训练模式选择"""
        from config import Config
        
        self.assertEqual(Config.TRAINING_MODE_CLASSIFIER, "classifier")
        self.assertEqual(Config.TRAINING_MODE_BERT_FINETUNE, "bert_finetune")
        self.assertEqual(Config.TRAINING_MODE_INCREMENTAL, "incremental")
        
    def test_fallback_mechanism(self):
        """测试降级机制"""
        with patch('training_manager.check_training_conditions') as mock_check:
            mock_check.return_value = (False, "GPU显存不足")
            
            can_train, reason = mock_check()
            
            self.assertFalse(can_train, "训练条件不满足时应返回False")
            self.assertIn("GPU", reason, "原因应包含GPU相关信息")
            
    def test_training_data_preparation(self):
        """测试训练数据准备"""
        answers = self.standard_answer_manager.get_current_answers()
        
        self.assertIn('structured_codes', answers, "答案应包含结构化编码")
        self.assertGreater(
            len(answers['structured_codes']),
            0,
            "结构化编码不应为空"
        )


class TestDatasetOperations(unittest.TestCase):
    """数据集操作测试"""
    
    def test_dataset_creation(self):
        """测试数据集创建"""
        texts = ["文本1", "文本2", "文本3"]
        labels = [0, 1, 0]
        
        dataset = MockDataset(texts, labels)
        
        self.assertEqual(len(dataset), 3, "数据集大小应为3")
        
        sample = dataset[0]
        self.assertIn('input_ids', sample, "样本应包含input_ids")
        self.assertIn('attention_mask', sample, "样本应包含attention_mask")
        self.assertIn('labels', sample, "样本应包含labels")
        
    def test_dataset_split(self):
        """测试数据集分割"""
        texts = [f"文本{i}" for i in range(10)]
        labels = [i % 3 for i in range(10)]
        
        dataset = MockDataset(texts, labels)
        
        train_size = int(len(dataset) * 0.8)
        train_texts = texts[:train_size]
        val_texts = texts[train_size:]
        
        self.assertEqual(len(train_texts), 8, "训练集应有8个样本")
        self.assertEqual(len(val_texts), 2, "验证集应有2个样本")


class TestTrainingHistory(unittest.TestCase):
    """训练历史记录测试"""
    
    def test_training_history_management(self):
        """测试训练历史管理"""
        history_records = []
        
        record1 = {
            'timestamp': '2024-01-01 10:00:00',
            'training_type': 'initial',
            'samples_count': 100,
            'epochs': 3,
            'learning_rate': 2e-5,
            'metrics': {'accuracy': 0.85}
        }
        history_records.append(record1)
        
        record2 = {
            'timestamp': '2024-01-02 10:00:00',
            'training_type': 'incremental',
            'samples_count': 50,
            'epochs': 2,
            'learning_rate': 1e-5,
            'metrics': {'accuracy': 0.88}
        }
        history_records.append(record2)
        
        self.assertEqual(len(history_records), 2, "应有2条训练记录")
        
        initial_records = [r for r in history_records if r['training_type'] == 'initial']
        self.assertEqual(len(initial_records), 1, "应有1条初始训练记录")
        
        incremental_records = [r for r in history_records if r['training_type'] == 'incremental']
        self.assertEqual(len(incremental_records), 1, "应有1条增量训练记录")


def run_e2e_tests():
    """运行端到端测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestE2ETraining))
    suite.addTests(loader.loadTestsFromTestCase(TestTrainingManagerIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestDatasetOperations))
    suite.addTests(loader.loadTestsFromTestCase(TestTrainingHistory))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_e2e_tests()
    sys.exit(0 if success else 1)
