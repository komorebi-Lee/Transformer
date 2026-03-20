import json
import logging
import os
from datetime import datetime
from itertools import product
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset, Subset
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import KFold

from config import Config

try:
    from bert_dataset import create_dataset_from_standard_answers
except ImportError:
    create_dataset_from_standard_answers = None

logger = logging.getLogger(__name__)

try:
    import optuna
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    logger.warning("optuna库未安装，贝叶斯优化功能不可用")


class HyperparameterOptimizer:
    """超参数自动寻优器"""

    def __init__(self, model_manager, config: Optional[Dict[str, Any]] = None):
        """
        初始化超参数优化器

        Args:
            model_manager: 模型管理器实例
            config: 配置字典，如果为None则使用默认配置
        """
        self.model_manager = model_manager
        self.config = config or {}
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.best_params: Dict[str, Any] = {}
        self.best_score: float = 0.0
        self.optimization_history: List[Dict[str, Any]] = []

        self._init_search_config()

        logger.info(f"HyperparameterOptimizer 初始化完成，设备: {self.device}")

    def _init_search_config(self):
        """初始化搜索配置"""
        self.search_config = {
            'search_space': self.config.get('search_space', Config.HYPERPARAM_SEARCH_SPACE),
            'cv_folds': self.config.get('cv_folds', Config.HYPERPARAM_CV_FOLDS),
            'metric': self.config.get('metric', 'f1'),
            'direction': self.config.get('direction', 'maximize'),
        }

        logger.info(f"搜索配置: {self.search_config}")

    def grid_search(
        self,
        dataset: Dataset,
        search_space: Optional[Dict[str, List[Any]]] = None,
        cv_folds: int = 3,
        progress_callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        网格搜索超参数

        Args:
            dataset: 训练数据集
            search_space: 搜索空间，如果为None则使用默认配置
            cv_folds: 交叉验证折数
            progress_callback: 进度回调函数 (current, total, current_params)

        Returns:
            最优参数组合和评估结果
        """
        try:
            if isinstance(dataset, dict):
                if create_dataset_from_standard_answers is None:
                    raise ValueError("bert_dataset模块不可用，无法处理训练数据")
                logger.info("检测到输入为dict，正在转换为Dataset...")
                dataset = create_dataset_from_standard_answers(dataset)
                logger.info(f"数据集转换完成，共 {len(dataset)} 个样本")

            if search_space is None:
                search_space = self.search_config['search_space']

            if cv_folds <= 0:
                cv_folds = self.search_config['cv_folds']

            actual_dataset_size = len(dataset)
            if cv_folds > actual_dataset_size:
                logger.warning(f"交叉验证折数({cv_folds})大于样本数量({actual_dataset_size})，自动调整为{actual_dataset_size}")
                cv_folds = actual_dataset_size

            param_names = list(search_space.keys())
            param_values = list(search_space.values())

            all_combinations = list(product(*param_values))
            total_combinations = len(all_combinations)

            logger.info(f"开始网格搜索，共 {total_combinations} 种参数组合")

            self.optimization_history = []
            best_score = 0.0
            best_params = {}

            for idx, combination in enumerate(all_combinations):
                params = dict(zip(param_names, combination))

                logger.info(f"评估参数组合 {idx + 1}/{total_combinations}: {params}")

                if progress_callback:
                    progress_callback(idx + 1, total_combinations, params)

                try:
                    score, metrics = self.cross_validate(dataset, params, cv_folds)

                    result = {
                        'params': params,
                        'score': score,
                        'metrics': metrics,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    self.optimization_history.append(result)

                    logger.info(f"参数组合 {idx + 1} 评估结果: score={score:.4f}, metrics={metrics}")

                    if score > best_score:
                        best_score = score
                        best_params = params.copy()
                        logger.info(f"发现更优参数: {best_params}, score={best_score:.4f}")

                except Exception as e:
                    logger.error(f"评估参数组合 {params} 失败: {e}")
                    continue

            self.best_params = best_params
            self.best_score = best_score

            result = {
                'best_params': best_params,
                'best_score': best_score,
                'total_combinations': total_combinations,
                'optimization_history': self.optimization_history,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            logger.info(f"网格搜索完成，最优参数: {best_params}, 最优分数: {best_score:.4f}")

            return result

        except Exception as e:
            logger.error(f"网格搜索失败: {e}")
            raise

    def bayesian_optimization(
        self,
        dataset: Dataset,
        n_trials: int = 20,
        search_space: Optional[Dict[str, List[Any]]] = None,
        progress_callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
        cv_folds: int = 3
    ) -> Dict[str, Any]:
        """
        贝叶斯优化超参数（使用Optuna）

        Args:
            dataset: 训练数据集
            n_trials: 搜索次数
            search_space: 搜索空间
            progress_callback: 进度回调函数
            cv_folds: 交叉验证折数

        Returns:
            最优参数组合和评估结果
        """
        if not OPTUNA_AVAILABLE:
            logger.error("optuna库未安装，无法使用贝叶斯优化")
            raise ImportError("optuna库未安装，请运行: pip install optuna")

        try:
            if isinstance(dataset, dict):
                if create_dataset_from_standard_answers is None:
                    raise ValueError("bert_dataset模块不可用，无法处理训练数据")
                logger.info("检测到输入为dict，正在转换为Dataset...")
                dataset = create_dataset_from_standard_answers(dataset)
                logger.info(f"数据集转换完成，共 {len(dataset)} 个样本")

            if search_space is None:
                search_space = self.search_config['search_space']

            if cv_folds <= 0:
                cv_folds = self.search_config['cv_folds']

            actual_dataset_size = len(dataset)
            if cv_folds > actual_dataset_size:
                logger.warning(f"交叉验证折数({cv_folds})大于样本数量({actual_dataset_size})，自动调整为{actual_dataset_size}")
                cv_folds = actual_dataset_size

            logger.info(f"开始贝叶斯优化，共 {n_trials} 次试验")

            self.optimization_history = []

            def objective(trial):
                params = self._suggest_params(trial, search_space)

                trial_idx = trial.number + 1
                logger.info(f"试验 {trial_idx}/{n_trials}: {params}")

                if progress_callback:
                    progress_callback(trial_idx, n_trials, params)

                try:
                    score, metrics = self.cross_validate(
                        dataset, params, cv_folds
                    )

                    result = {
                        'trial': trial_idx,
                        'params': params,
                        'score': score,
                        'metrics': metrics,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    self.optimization_history.append(result)

                    logger.info(f"试验 {trial_idx} 结果: score={score:.4f}")

                    return score

                except Exception as e:
                    logger.error(f"试验 {trial_idx} 失败: {e}")
                    return 0.0

            study = optuna.create_study(
                direction='maximize',
                study_name='hyperparameter_optimization'
            )

            study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

            self.best_params = study.best_params
            self.best_score = study.best_value

            result = {
                'best_params': study.best_params,
                'best_score': study.best_value,
                'n_trials': n_trials,
                'optimization_history': self.optimization_history,
                'study': study,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            logger.info(f"贝叶斯优化完成，最优参数: {study.best_params}, 最优分数: {study.best_value:.4f}")

            return result

        except Exception as e:
            logger.error(f"贝叶斯优化失败: {e}")
            raise

    def _suggest_params(self, trial, search_space: Dict[str, List[Any]]) -> Dict[str, Any]:
        """
        使用Optuna建议参数

        Args:
            trial: Optuna trial对象
            search_space: 搜索空间

        Returns:
            参数字典
        """
        params = {}

        for param_name, param_values in search_space.items():
            if not param_values:
                continue

            if param_name == 'learning_rate':
                params[param_name] = trial.suggest_categorical(
                    param_name, param_values
                )
            elif param_name == 'batch_size':
                params[param_name] = trial.suggest_categorical(
                    param_name, param_values
                )
            elif param_name == 'epochs':
                params[param_name] = trial.suggest_categorical(
                    param_name, param_values
                )
            elif param_name == 'dropout_rate':
                params[param_name] = trial.suggest_categorical(
                    param_name, param_values
                )
            else:
                params[param_name] = trial.suggest_categorical(
                    param_name, param_values
                )

        return params

    def cross_validate(
        self,
        dataset: Dataset,
        params: Dict[str, Any],
        cv_folds: int = 3
    ) -> Tuple[float, Dict[str, float]]:
        """
        交叉验证评估

        Args:
            dataset: 训练数据集
            params: 参数字典
            cv_folds: 交叉验证折数

        Returns:
            Tuple[平均分数, 详细指标字典]
        """
        try:
            kfold = KFold(n_splits=cv_folds, shuffle=True, random_state=42)

            all_metrics = {
                'accuracy': [],
                'f1': [],
                'precision': [],
                'recall': []
            }

            dataset_size = len(dataset)
            indices = list(range(dataset_size))

            for fold_idx, (train_idx, val_idx) in enumerate(kfold.split(indices)):
                logger.debug(f"交叉验证折 {fold_idx + 1}/{cv_folds}")

                train_subset = Subset(dataset, train_idx)
                val_subset = Subset(dataset, val_idx)

                fold_metrics = self._evaluate_fold(
                    train_subset, val_subset, params
                )

                for metric_name, value in fold_metrics.items():
                    if metric_name in all_metrics:
                        all_metrics[metric_name].append(value)

            avg_metrics = {
                metric_name: np.mean(values) if values else 0.0
                for metric_name, values in all_metrics.items()
            }

            metric = self.search_config.get('metric', 'f1')
            avg_score = avg_metrics.get(metric, 0.0)

            logger.debug(f"交叉验证完成，平均指标: {avg_metrics}")

            return avg_score, avg_metrics

        except Exception as e:
            logger.error(f"交叉验证失败: {e}")
            raise

    def _evaluate_fold(
        self,
        train_dataset: Dataset,
        val_dataset: Dataset,
        params: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        评估单个折

        Args:
            train_dataset: 训练数据集
            val_dataset: 验证数据集
            params: 参数字典

        Returns:
            评估指标字典
        """
        try:
            from bert_finetuner import BERTFineTuner

            temp_output_dir = os.path.join(
                Config.TRAINED_MODELS_DIR,
                f"temp_cv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            os.makedirs(temp_output_dir, exist_ok=True)

            finetuner = BERTFineTuner(self.model_manager, config=params)

            train_success = finetuner.train(
                train_dataset,
                temp_output_dir,
                progress_callback=None
            )

            if not train_success:
                logger.warning("折训练失败，返回零指标")
                return {'accuracy': 0.0, 'f1': 0.0, 'precision': 0.0, 'recall': 0.0}

            metrics = finetuner.evaluate(val_dataset)

            self._cleanup_temp_dir(temp_output_dir)

            return {
                'accuracy': metrics.get('eval_accuracy', 0.0),
                'f1': metrics.get('eval_f1', 0.0),
                'precision': metrics.get('eval_precision', 0.0),
                'recall': metrics.get('eval_recall', 0.0)
            }

        except Exception as e:
            logger.error(f"评估折失败: {e}")
            return {'accuracy': 0.0, 'f1': 0.0, 'precision': 0.0, 'recall': 0.0}

    def _cleanup_temp_dir(self, temp_dir: str):
        """
        清理临时目录

        Args:
            temp_dir: 临时目录路径
        """
        try:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.debug(f"已清理临时目录: {temp_dir}")
        except Exception as e:
            logger.warning(f"清理临时目录失败: {e}")

    def save_best_params(self, params: Dict[str, Any], output_file: str) -> bool:
        """
        保存最优参数到文件

        Args:
            params: 参数字典
            output_file: 输出文件路径

        Returns:
            保存是否成功
        """
        try:
            output_dir = os.path.dirname(output_file)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            save_data = {
                'best_params': params,
                'best_score': self.best_score,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'search_config': self.search_config
            }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            logger.info(f"最优参数已保存到: {output_file}")
            return True

        except Exception as e:
            logger.error(f"保存最优参数失败: {e}")
            return False

    def load_best_params(self, input_file: str) -> Dict[str, Any]:
        """
        从文件加载最优参数

        Args:
            input_file: 输入文件路径

        Returns:
            参数字典
        """
        try:
            if not os.path.exists(input_file):
                logger.error(f"参数文件不存在: {input_file}")
                return {}

            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.best_params = data.get('best_params', {})
            self.best_score = data.get('best_score', 0.0)

            if 'search_config' in data:
                self.search_config.update(data['search_config'])

            logger.info(f"已从 {input_file} 加载最优参数: {self.best_params}")

            return self.best_params

        except Exception as e:
            logger.error(f"加载最优参数失败: {e}")
            return {}

    def get_optimization_summary(self) -> Dict[str, Any]:
        """
        获取优化摘要

        Returns:
            优化摘要字典
        """
        return {
            'best_params': self.best_params,
            'best_score': self.best_score,
            'total_trials': len(self.optimization_history),
            'search_config': self.search_config,
            'device': str(self.device)
        }

    def get_top_n_params(self, n: int = 5) -> List[Dict[str, Any]]:
        """
        获取前N个最优参数组合

        Args:
            n: 返回的参数组合数量

        Returns:
            排序后的参数组合列表
        """
        if not self.optimization_history:
            logger.warning("没有优化历史记录")
            return []

        sorted_history = sorted(
            self.optimization_history,
            key=lambda x: x.get('score', 0.0),
            reverse=True
        )

        return sorted_history[:n]

    def quick_evaluate(
        self,
        dataset: Dataset,
        params: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        """
        快速评估单组参数（不使用交叉验证）

        Args:
            dataset: 数据集
            params: 参数字典

        Returns:
            Tuple[分数, 指标字典]
        """
        try:
            from bert_finetuner import BERTFineTuner
            from torch.utils.data import random_split

            total_size = len(dataset)
            train_size = int(total_size * 0.8)
            val_size = total_size - train_size

            train_dataset, val_dataset = random_split(
                dataset,
                [train_size, val_size],
                generator=torch.Generator().manual_seed(42)
            )

            temp_output_dir = os.path.join(
                Config.TRAINED_MODELS_DIR,
                f"temp_quick_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            os.makedirs(temp_output_dir, exist_ok=True)

            finetuner = BERTFineTuner(self.model_manager, config=params)

            train_success = finetuner.train(
                train_dataset,
                temp_output_dir,
                progress_callback=None
            )

            if not train_success:
                self._cleanup_temp_dir(temp_output_dir)
                return 0.0, {'accuracy': 0.0, 'f1': 0.0, 'precision': 0.0, 'recall': 0.0}

            metrics = finetuner.evaluate(val_dataset)

            self._cleanup_temp_dir(temp_output_dir)

            result_metrics = {
                'accuracy': metrics.get('eval_accuracy', 0.0),
                'f1': metrics.get('eval_f1', 0.0),
                'precision': metrics.get('eval_precision', 0.0),
                'recall': metrics.get('eval_recall', 0.0)
            }

            metric = self.search_config.get('metric', 'f1')
            score = result_metrics.get(metric, 0.0)

            return score, result_metrics

        except Exception as e:
            logger.error(f"快速评估失败: {e}")
            return 0.0, {'accuracy': 0.0, 'f1': 0.0, 'precision': 0.0, 'recall': 0.0}
