import logging
import os
import pickle
import json
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Tuple
from PyQt5.QtCore import QThread, pyqtSignal
from datetime import datetime
# 修复 sklearn 导入

logger = logging.getLogger(__name__)
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score
    from sklearn.cluster import KMeans
    import sklearn
    SKLEARN_AVAILABLE = True
    logger.info("scikit-learn 版本: %s", sklearn.__version__)
except ImportError as e:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn 未安装，训练功能将受限: %s", e)
except Exception as e:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn 导入异常: %s", e)

logger = logging.getLogger(__name__)


class GroundedTheoryTrainingThread(QThread):
    """扎根理论训练线程 - 修复版本"""

    progress_updated = pyqtSignal(int)
    training_finished = pyqtSignal(bool, str)

    def __init__(self, training_data: Dict[str, Any], model_manager, standard_answers: Dict[str, Any]):
        super().__init__()
        self.training_data = training_data
        self.model_manager = model_manager
        self.standard_answers = standard_answers
        self.trained_model_data = None

    def run(self):
        try:
            self.progress_updated.emit(0)
            logger.info("开始扎根理论模型训练...")

            # 准备训练数据
            self.progress_updated.emit(10)
            texts, labels, label_mapping = self.prepare_training_data()

            if len(texts) < 5:
                self.training_finished.emit(False, "训练数据不足，至少需要5个样本")
                return

            self.progress_updated.emit(30)

            # 生成嵌入向量
            embeddings = self.model_manager.get_embeddings(texts)
            if embeddings is None or len(embeddings) == 0:
                self.training_finished.emit(False, "生成嵌入向量失败")
                return

            self.progress_updated.emit(60)

            # 训练分类器
            if SKLEARN_AVAILABLE:
                classifier, accuracy = self.train_classifier(embeddings, labels)
            else:
                classifier, accuracy = self.train_rule_based_classifier(embeddings, labels)

            self.progress_updated.emit(80)

            # 准备模型数据
            self.trained_model_data = {
                "classifier": classifier,
                "label_mapping": label_mapping,
                "embeddings": embeddings,
                "texts": texts,
                "labels": labels,
                "training_time": self.get_timestamp(),
                "sample_count": len(texts),
                "class_count": len(label_mapping),
                "accuracy": accuracy,
                "model_type": "grounded_theory_coder"
            }

            # 保存模型
            success = self.model_manager.save_trained_model(self.trained_model_data, "grounded_theory_latest")
            self.progress_updated.emit(100)

            if success:
                message = f"模型训练完成！共训练 {len(texts)} 个样本，{len(label_mapping)} 个类别，准确率: {accuracy:.3f}"
                self.training_finished.emit(True, message)
            else:
                self.training_finished.emit(False, "模型保存失败")

        except Exception as e:
            logger.error(f"训练失败: {e}")
            self.training_finished.emit(False, f"训练失败: {str(e)}")

    def prepare_training_data(self) -> Tuple[List[str], List[int], Dict[str, int]]:
        """准备训练数据"""
        texts = []
        labels = []
        label_mapping = {}
        current_label_id = 0

        # 从标准答案中提取训练数据
        structured_codes = self.standard_answers.get("structured_codes", {})

        if not structured_codes:
            # 尝试从training_data中提取
            structured_codes = self.training_data.get("structured_codes", {})

        logger.info(f"从结构化编码中提取训练数据，共 {len(structured_codes)} 个三阶编码")

        for third_cat, second_cats in structured_codes.items():
            for second_cat, first_contents in second_cats.items():
                # 创建唯一的标签ID
                label_id = f"{third_cat}||{second_cat}"
                if label_id not in label_mapping:
                    label_mapping[label_id] = current_label_id
                    current_label_id += 1

                label_num = label_mapping[label_id]

                for content in first_contents:
                    if isinstance(content, dict):
                        text_content = content.get('content', '')
                    else:
                        text_content = str(content)

                    if text_content and len(text_content.strip()) > 5:
                        texts.append(text_content.strip())
                        labels.append(label_num)

        logger.info(f"准备训练数据: {len(texts)} 个样本, {len(label_mapping)} 个类别")
        return texts, labels, label_mapping

    def train_classifier(self, embeddings: np.ndarray, labels: List[int]) -> Tuple[Any, float]:
        """训练分类器并返回准确率"""
        try:
            # 使用随机森林分类器
            classifier = RandomForestClassifier(
                n_estimators=100,
                max_depth=20,
                random_state=42,
                min_samples_split=5,
                min_samples_leaf=2
            )

            # 训练模型
            classifier.fit(embeddings, labels)

            # 计算训练准确率
            predictions = classifier.predict(embeddings)
            accuracy = accuracy_score(labels, predictions)

            logger.info(f"分类器训练完成，训练准确率: {accuracy:.3f}")
            return classifier, accuracy

        except Exception as e:
            logger.error(f"分类器训练失败: {e}")
            # 降级到简单规则分类器
            return self.train_rule_based_classifier(embeddings, labels)

    def train_rule_based_classifier(self, embeddings: np.ndarray, labels: List[int]) -> Tuple[Dict[str, Any], float]:
        """训练基于规则的分类器（降级模式）"""
        logger.info("使用基于规则的分类器")

        if not SKLEARN_AVAILABLE:
            logger.error("sklearn未安装，无法使用规则分类器")
            return {}, 0.0

        # 简单的基于聚类的分类器
        unique_labels = list(set(labels))
        n_clusters = min(len(unique_labels), len(embeddings))

        if n_clusters < 2:
            n_clusters = 2

        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        cluster_labels = kmeans.fit_predict(embeddings)

        # 建立聚类到标签的映射
        cluster_to_label = {}
        accuracy_count = 0
        total_count = 0

        for cluster_id in range(n_clusters):
            cluster_indices = [i for i, cl in enumerate(cluster_labels) if cl == cluster_id]
            if cluster_indices:
                # 找到该聚类中最常见的标签
                label_counts = {}
                for idx in cluster_indices:
                    label = labels[idx]
                    label_counts[label] = label_counts.get(label, 0) + 1

                if label_counts:
                    most_common_label, count = max(label_counts.items(), key=lambda x: x[1])
                    cluster_to_label[cluster_id] = most_common_label
                    accuracy_count += count
                    total_count += len(cluster_indices)

        accuracy = accuracy_count / total_count if total_count > 0 else 0.0

        classifier_data = {
            'kmeans': kmeans,
            'cluster_to_label': cluster_to_label,
            'model_type': 'rule_based'
        }

        logger.info(f"规则分类器训练完成，准确率: {accuracy:.3f}")
        return classifier_data, accuracy

    def get_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class EnhancedTrainingManager:
    """增强的训练管理器"""

    def __init__(self):
        self.training_thread = None
        self.standard_answer_manager = None
        self.training_history = []

    def set_standard_answer_manager(self, manager):
        """设置标准答案管理器"""
        self.standard_answer_manager = manager

    def train_grounded_theory_model(self, training_data: Dict[str, Any], model_manager,
                                    progress_callback: Optional[Callable] = None,
                                    finished_callback: Optional[Callable] = None):
        """训练扎根理论模型"""
        if self.standard_answer_manager is None:
            if finished_callback:
                finished_callback(False, "标准答案管理器未设置")
            return

        standard_answers = self.standard_answer_manager.get_current_answers()
        if not standard_answers:
            if finished_callback:
                finished_callback(False, "没有标准答案数据")
            return

        # 停止之前的训练线程
        if self.training_thread and self.training_thread.isRunning():
            self.training_thread.terminate()
            self.training_thread.wait()

        self.training_thread = GroundedTheoryTrainingThread(
            training_data, model_manager, standard_answers
        )

        if progress_callback:
            self.training_thread.progress_updated.connect(progress_callback)

        if finished_callback:
            self.training_thread.training_finished.connect(finished_callback)

        # 记录训练历史
        training_record = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'sample_count': self.standard_answer_manager.get_training_sample_count(),
            'status': 'started'
        }
        self.training_history.append(training_record)

        self.training_thread.start()

    def get_training_history(self) -> List[Dict[str, Any]]:
        """获取训练历史"""
        return self.training_history