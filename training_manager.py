import logging
import os
import pickle
import json
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Tuple
from PyQt5.QtCore import QThread, pyqtSignal
from datetime import datetime

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logging.warning("torch 未安装，GPU检测功能将受限")

from config import Config
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


def check_gpu_memory() -> bool:
    """检查GPU内存是否足够进行BERT微调训练"""
    if not TORCH_AVAILABLE:
        logger.warning("torch未安装，无法检测GPU")
        return False
    
    try:
        if not torch.cuda.is_available():
            logger.info("CUDA不可用，将使用CPU训练")
            return True
        
        gpu_count = torch.cuda.device_count()
        for i in range(gpu_count):
            props = torch.cuda.get_device_properties(i)
            total_memory = props.total_memory / (1024 ** 3)
            reserved = torch.cuda.memory_reserved(i) / (1024 ** 3)
            allocated = torch.cuda.memory_allocated(i) / (1024 ** 3)
            free_memory = total_memory - reserved
            
            min_required_memory = 2.0
            
            logger.info(f"GPU {i}: {props.name}, 总显存: {total_memory:.2f}GB, "
                       f"已用: {allocated:.2f}GB, 空闲: {free_memory:.2f}GB")
            
            if free_memory >= min_required_memory:
                return True
        
        logger.warning("GPU显存不足，建议至少2GB空闲显存")
        return False
        
    except Exception as e:
        logger.error(f"GPU检测失败: {e}")
        return False


def check_transformers_available() -> bool:
    """检查transformers库是否可用"""
    try:
        import transformers
        logger.info(f"transformers版本: {transformers.__version__}")
        return True
    except ImportError:
        logger.warning("transformers库未安装")
        return False
    except Exception as e:
        logger.warning(f"transformers库检测异常: {e}")
        return False


def check_training_conditions() -> Tuple[bool, str]:
    """
    检查BERT微调训练条件是否满足
    
    Returns:
        Tuple[bool, str]: (是否可训练, 原因说明)
    """
    if not check_transformers_available():
        return False, "transformers库未安装或不可用，无法进行BERT微调训练"
    
    if not TORCH_AVAILABLE:
        return False, "torch库未安装，无法进行BERT微调训练"
    
    if not SKLEARN_AVAILABLE:
        return False, "scikit-learn库未安装，无法进行训练"
    
    if not check_gpu_memory():
        return False, "GPU显存不足（建议至少2GB空闲显存），BERT微调训练可能失败"
    
    return True, "训练条件满足，可以进行BERT微调训练"


class GroundedTheoryTrainingThread(QThread):
    """扎根理论训练线程 - 修复版本"""

    progress_updated = pyqtSignal(int)
    training_finished = pyqtSignal(bool, str, dict)
    fallback_triggered = pyqtSignal(str)

    def __init__(self, training_data: Dict[str, Any], model_manager, standard_answers: Dict[str, Any], 
                 model_type: str = 'bert', training_mode: str = 'classifier', 
                 fallback_to_classifier: bool = True,
                 training_config: Optional[Dict[str, Any]] = None,
                 incremental: bool = False,
                 coding_processing_result: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.training_data = training_data
        self.model_manager = model_manager
        self.standard_answers = standard_answers
        self.model_type = model_type
        self.training_mode = training_mode
        self.fallback_to_classifier = fallback_to_classifier
        self.training_config = training_config or {}
        self.incremental = incremental
        self.coding_processing_result = coding_processing_result or {}
        self.trained_model_data = None
        self.actual_training_mode = training_mode

    def run(self):
        try:
            self.progress_updated.emit(0)
            logger.info(f"开始扎根理论模型训练，训练模式: {self.training_mode}, 增量训练: {self.incremental}")

            if self.training_mode == Config.TRAINING_MODE_BERT_FINETUNE:
                self._run_bert_finetune_training()
            else:
                self._run_classifier_training_internal()

        except Exception as e:
            logger.error(f"训练失败: {e}")
            self.training_finished.emit(False, f"训练失败: {str(e)}", self.coding_processing_result)

    def _run_bert_finetune_training(self):
        """运行BERT微调训练"""
        try:
            can_train, reason = check_training_conditions()
            if not can_train:
                if self.fallback_to_classifier:
                    fallback_reason = f"BERT微调训练条件不满足: {reason}，已自动降级到分类器模式"
                    logger.warning(fallback_reason)
                    self.actual_training_mode = Config.TRAINING_MODE_CLASSIFIER
                    self.fallback_triggered.emit(fallback_reason)
                    self._run_classifier_training_internal()
                    return
                else:
                    self.training_finished.emit(False, f"训练条件不满足: {reason}", self.coding_processing_result)
                    return



            self.progress_updated.emit(10)
            texts, labels, label_mapping = self.prepare_training_data()

            if len(texts) < 5:
                self.training_finished.emit(False, "训练数据不足，至少需要5个样本", self.coding_processing_result)
                return

            self.progress_updated.emit(20)
            logger.info(f"准备BERT微调训练数据: {len(texts)} 个样本, {len(label_mapping)} 个类别")

            from bert_finetuner import BERTFineTuner
            from bert_dataset import GroundedTheoryDataset
            from transformers import AutoTokenizer

            local_model_path = os.path.join(Config.LOCAL_MODELS_DIR, Config.DEFAULT_MODEL_NAME)
            if os.path.exists(local_model_path):
                tokenizer = AutoTokenizer.from_pretrained(local_model_path)
            else:
                tokenizer = AutoTokenizer.from_pretrained(Config.DEFAULT_MODEL_NAME)

            max_length = self.training_config.get('max_length', Config.MAX_SENTENCE_LENGTH)
            dataset = GroundedTheoryDataset(texts, labels, tokenizer, max_length)
            dataset.label_to_id = label_mapping
            dataset.id_to_label = {v: k for k, v in label_mapping.items()}

            self.progress_updated.emit(30)

            output_dir = os.path.join(Config.TRAINED_MODELS_DIR, "bert_finetuned_latest")
            
            finetuner = BERTFineTuner(self.model_manager, config=self.training_config)

            def progress_callback(current_step, total_steps, loss):
                if total_steps > 0:
                    progress = 30 + int((current_step / total_steps) * 60)
                    self.progress_updated.emit(progress)

            def finished_callback(success, message):
                if success:
                    self.progress_updated.emit(100)
                    
                    self.trained_model_data = {
                        "model_path": output_dir,
                        "label_mapping": label_mapping,
                        "training_time": self.get_timestamp(),
                        "sample_count": len(texts),
                        "class_count": len(label_mapping),
                        "model_type": "bert_finetune",
                        "embedding_model": "bert",
                        "training_mode": self.actual_training_mode,
                        "incremental": self.incremental
                    }
                    
                    msg = f"BERT微调训练完成！共训练 {len(texts)} 个样本，{len(label_mapping)} 个类别"
                    self.training_finished.emit(True, msg, self.coding_processing_result)
                else:
                    if self.fallback_to_classifier:
                        fallback_reason = f"BERT微调训练失败: {message}，已自动降级到分类器模式"
                        logger.warning(fallback_reason)
                        self.actual_training_mode = Config.TRAINING_MODE_CLASSIFIER
                        self.fallback_triggered.emit(fallback_reason)
                        self._run_classifier_training_internal()
                    else:
                        self.training_finished.emit(False, message, self.coding_processing_result)

            if self.incremental:
                # 增量训练
                success = finetuner.train_incremental(
                    dataset,
                    output_dir,
                    progress_callback=progress_callback,
                    finished_callback=finished_callback
                )
            else:
                # 首次训练
                success = finetuner.train(
                    dataset,
                    output_dir,
                    progress_callback=progress_callback,
                    finished_callback=finished_callback
                )

            if not success:
                if self.fallback_to_classifier:
                    fallback_reason = "BERT微调训练失败，已自动降级到分类器模式"
                    logger.warning(fallback_reason)
                    self.actual_training_mode = Config.TRAINING_MODE_CLASSIFIER
                    self.fallback_triggered.emit(fallback_reason)
                    self._run_classifier_training_internal()

        except Exception as e:
            logger.error(f"BERT微调训练失败: {e}")
            if self.fallback_to_classifier:
                try:
                    fallback_reason = f"BERT微调训练失败: {str(e)}，已自动降级到分类器模式"
                    logger.warning(fallback_reason)
                    self.actual_training_mode = Config.TRAINING_MODE_CLASSIFIER
                    self.fallback_triggered.emit(fallback_reason)
                    self._run_classifier_training_internal()
                    return
                except Exception as fallback_error:
                    logger.error(f"降级训练也失败: {fallback_error}")
                    self.training_finished.emit(False, f"训练失败: {str(e)}，降级训练也失败: {str(fallback_error)}", self.coding_processing_result)
                    return
            self.training_finished.emit(False, f"BERT微调训练失败: {str(e)}", self.coding_processing_result)

    def _run_classifier_training_internal(self):
        """内部方法：运行分类器训练（分类器模式和增量训练）"""
        try:
            self.progress_updated.emit(0)
            logger.info(f"开始分类器训练，增量训练: {self.incremental}")

            existing_model_data = None
            existing_label_mapping = None
            
            if self.incremental:
                logger.info("增量训练模式：尝试加载已有模型...")
                load_success = self.model_manager.load_trained_model("grounded_theory_latest")
                if load_success and self.model_manager.trained_model:
                    existing_model_data = self.model_manager.trained_model
                    existing_label_mapping = existing_model_data.get("label_mapping", {})
                    logger.info(f"已加载已有模型，包含 {len(existing_label_mapping)} 个标签")
                else:
                    logger.warning("增量训练模式但未找到已有模型，将执行首次训练")

            self.progress_updated.emit(10)
            texts, labels, label_mapping = self.prepare_training_data()

            if self.incremental and existing_label_mapping:
                logger.info(f"合并标签映射: 已有 {len(existing_label_mapping)} 个, 新数据 {len(label_mapping)} 个")
                max_id = max(existing_label_mapping.values()) if existing_label_mapping else -1
                merged_label_mapping = existing_label_mapping.copy()
                
                for label, _ in label_mapping.items():
                    if label not in merged_label_mapping:
                        max_id += 1
                        merged_label_mapping[label] = max_id
                        logger.info(f"添加新标签: {label} -> {max_id}")
                
                label_mapping = merged_label_mapping
                logger.info(f"合并后标签映射: {len(label_mapping)} 个标签")

            if len(texts) < 5:
                self.training_finished.emit(False, "训练数据不足，至少需要5个样本", self.coding_processing_result)
                return

            self.progress_updated.emit(30)

            embeddings = self.model_manager.get_embeddings(texts, model_type=self.model_type)
            if embeddings is None or len(embeddings) == 0:
                self.training_finished.emit(False, "生成嵌入向量失败", self.coding_processing_result)
                return

            self.progress_updated.emit(60)

            if self.incremental and existing_model_data:
                existing_texts = existing_model_data.get("texts", [])
                existing_labels = existing_model_data.get("labels", [])
                
                if existing_texts and existing_labels:
                    logger.info(f"合并训练数据: 已有 {len(existing_texts)} 个, 新数据 {len(texts)} 个")
                    existing_embeddings = self.model_manager.get_embeddings(existing_texts, model_type=self.model_type)
                    
                    if existing_embeddings is None or len(existing_embeddings) == 0:
                        logger.warning("生成已有数据嵌入向量失败，仅使用新数据训练")
                    else:
                        texts = existing_texts + texts
                        labels = existing_labels + labels
                        embeddings = np.vstack([existing_embeddings, embeddings]) if len(existing_embeddings) > 0 else embeddings
                        logger.info(f"合并后总数据: {len(texts)} 个样本")

            if SKLEARN_AVAILABLE:
                classifier, accuracy = self.train_classifier(embeddings, labels)
            else:
                classifier, accuracy = self.train_rule_based_classifier(embeddings, labels)

            self.progress_updated.emit(80)

            self.trained_model_data = {
                "classifier": classifier,
                "label_mapping": label_mapping,
                "texts": texts,
                "labels": labels,
                "training_time": self.get_timestamp(),
                "sample_count": len(texts),
                "class_count": len(label_mapping),
                "accuracy": accuracy,
                "model_type": "grounded_theory_coder",
                "embedding_model": self.model_type,
                "training_mode": self.actual_training_mode,
                "incremental": self.incremental
            }

            success = self.model_manager.save_trained_model(self.trained_model_data, "grounded_theory_latest")
            self.progress_updated.emit(100)

            if success:
                mode_info = f"（训练模式: {self.actual_training_mode}）" if self.actual_training_mode != self.training_mode else ""
                incremental_info = " [增量训练]" if self.incremental else ""
                message = f"模型训练完成！共训练 {len(texts)} 个样本，{len(label_mapping)} 个类别，准确率: {accuracy:.3f}{incremental_info}{mode_info}"
                self.training_finished.emit(True, message, self.coding_processing_result)
            else:
                self.training_finished.emit(False, "模型保存失败", self.coding_processing_result)

        except Exception as e:
            logger.error(f"分类器训练失败: {e}")
            self.training_finished.emit(False, f"分类器训练失败: {str(e)}", self.coding_processing_result)

    def prepare_training_data(self) -> Tuple[List[str], List[int], Dict[str, int]]:
        """准备训练数据"""
        texts = []
        labels = []
        label_mapping = {}
        current_label_id = 0

        # 首先尝试从standard_answers中获取training_data
        training_data = self.standard_answers.get("training_data", {})

        structured_codes = {}
        
        if training_data:
            # 使用training_data准备训练样本
            logger.info(f"从training_data中提取训练数据")
            
            # 检查training_data的结构
            if isinstance(training_data, dict):
                # 处理不同格式的training_data
                if "structured_codes" in training_data:
                    # 如果training_data中包含structured_codes，使用它
                    structured_codes = training_data["structured_codes"]
                else:
                    # 尝试直接处理training_data
                    structured_codes = training_data
            elif isinstance(training_data, list):
                # 如果training_data是列表，从列表中构建structured_codes
                logger.info(f"training_data是列表，包含 {len(training_data)} 个样本")
                for item in training_data:
                    if isinstance(item, dict):
                        third_level = item.get("target_third_category")
                        second_level = item.get("target_second_category")
                        target_abstract = item.get("target_abstract", "")
                        if third_level and second_level and target_abstract:
                            if third_level not in structured_codes:
                                structured_codes[third_level] = {}
                            if second_level not in structured_codes[third_level]:
                                structured_codes[third_level][second_level] = []
                            structured_codes[third_level][second_level].append(target_abstract)
        else:
            # 如果没有training_data，尝试从standard_answers中获取structured_codes
            structured_codes = self.standard_answers.get("structured_codes", {})
            
            if not structured_codes:
                # 最后尝试从self.training_data中获取structured_codes
                structured_codes = self.training_data.get("structured_codes", {})

        logger.info(f"从训练数据中提取样本，共 {len(structured_codes)} 个三阶编码")

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
        self._fallback_callback = None

    def set_standard_answer_manager(self, manager):
        """设置标准答案管理器"""
        self.standard_answer_manager = manager

    def set_fallback_callback(self, callback: Callable[[str], None]):
        """设置降级回调函数"""
        self._fallback_callback = callback

    def handle_fallback(self, reason: str) -> None:
        """
        处理降级，显示弹窗提示用户
        
        Args:
            reason: 降级原因说明
        """
        logger.warning(f"训练降级: {reason}")
        
        if self._fallback_callback:
            self._fallback_callback(reason)
        else:
            from PyQt5.QtWidgets import QMessageBox
            try:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("训练模式降级提示")
                msg.setText("训练模式已自动降级")
                msg.setInformativeText(f"由于以下问题，已自动降级到分类器模式训练：\n\n{reason}")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec_()
            except Exception as e:
                logger.error(f"显示降级弹窗失败: {e}")

    def train_grounded_theory_model(self, training_data: Dict[str, Any], model_manager,
                                    progress_callback: Optional[Callable] = None,
                                    finished_callback: Optional[Callable] = None,
                                    model_type: str = 'bert',
                                    training_mode: str = 'classifier',
                                    fallback_to_classifier: bool = True,
                                    training_config: Optional[Dict[str, Any]] = None,
                                    incremental: bool = False):
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

        # 增量训练时先检查是否有已加载的模型
        if incremental and training_mode == Config.TRAINING_MODE_BERT_FINETUNE:
            # 检查模型是否已经加载
            if not model_manager.is_trained_model_available():
                if finished_callback:
                    finished_callback(False, "请加载最新模型")
                return
            
            # 检查是否有可用的BERT微调模型文件
            try:
                from bert_finetuner import BERTFineTuner
                finetuner = BERTFineTuner(model_manager, config=training_config)
                latest_model_path = finetuner._find_latest_model()
                if not latest_model_path or not os.path.exists(latest_model_path):
                    if finished_callback:
                        finished_callback(False, "请加载最新模型")
                    return
            except Exception as e:
                logger.error(f"检查模型失败: {e}")
                if finished_callback:
                    finished_callback(False, "请加载最新模型")
                return

        # 训练前创建编码库备份
        try:
            from enhanced_manual_coding import EnhancedManualCoding
            enhanced_coding = EnhancedManualCoding()
            # 创建编码库备份
            backup_path = enhanced_coding.coding_library_manager.create_backup("训练前备份")
            if backup_path:
                logger.info(f"训练前编码库备份成功: {backup_path}")
            else:
                logger.warning("训练前编码库备份失败")
        except Exception as e:
            logger.error(f"创建编码库备份失败: {e}")

        # 集成人工编码增强功能 - 确保所有训练模式都会更新编码库
        coding_processing_result = {}
        try:
            from enhanced_manual_coding import EnhancedManualCoding
            enhanced_coding = EnhancedManualCoding()
            # 处理标准答案中的编码信息
            integration_result = enhanced_coding.integrate_with_model_training(standard_answers)
            if integration_result["success"]:
                coding_processing_result = integration_result.get("processing_result", {})
                logger.info("编码处理成功，继续模型训练")
            else:
                logger.warning(f"人工编码增强功能集成失败: {integration_result['message']}")
        except Exception as e:
            logger.error(f"集成人工编码增强功能失败: {e}")

        if self.training_thread and self.training_thread.isRunning():
            self.training_thread.terminate()
            self.training_thread.wait()

        self.training_thread = GroundedTheoryTrainingThread(
            training_data, model_manager, standard_answers, model_type,
            training_mode=training_mode, 
            fallback_to_classifier=fallback_to_classifier,
            training_config=training_config,
            incremental=incremental,
            coding_processing_result=coding_processing_result
        )

        if progress_callback:
            self.training_thread.progress_updated.connect(progress_callback)

        if finished_callback:
            # 包装finished_callback，添加编码更新结果显示
            def wrapped_finished_callback(success, message, coding_processing_result):
                # 只有训练成功时才显示编码更新结果
                if success:
                    self._show_coding_update_result(coding_processing_result)
                # 调用原始回调
                finished_callback(success, message)
            self.training_thread.training_finished.connect(wrapped_finished_callback)

        self.training_thread.fallback_triggered.connect(self.handle_fallback)

        training_record = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'sample_count': self.standard_answer_manager.get_training_sample_count(),
            'model_type': model_type,
            'training_mode': training_mode,
            'status': 'started'
        }
        self.training_history.append(training_record)

        self.training_thread.start()

    def get_training_history(self) -> List[Dict[str, Any]]:
        """获取训练历史"""
        return self.training_history

    def _show_coding_update_result(self, coding_processing_result: Dict[str, Any]):
        """
        显示编码更新结果弹窗

        Args:
            coding_processing_result: 编码处理结果
        """
        try:
            from PyQt5.QtWidgets import QMessageBox
            
            # 提取编码更新信息
            added_third = coding_processing_result.get("added_third_level_codes", [])
            updated_third = coding_processing_result.get("updated_third_level_codes", [])
            added_second = coding_processing_result.get("added_second_level_codes", [])
            updated_second = coding_processing_result.get("updated_second_level_codes", [])
            
            # 构建弹窗内容
            content = "编码库更新结果：\n\n"
            
            if added_third:
                content += f"新增三阶编码 ({len(added_third)} 个):\n" + "\n".join([f"- {code}" for code in added_third[:10]])
                if len(added_third) > 10:
                    content += f"\n... 等 {len(added_third) - 10} 个编码"
                content += "\n\n"
            else:
                content += "新增三阶编码: 无\n\n"
            
            if updated_third:
                content += f"更新三阶编码 ({len(updated_third)} 个):\n" + "\n".join([f"- {code}" for code in updated_third[:10]])
                if len(updated_third) > 10:
                    content += f"\n... 等 {len(updated_third) - 10} 个编码"
                content += "\n\n"
            else:
                content += "更新三阶编码: 无\n\n"
            
            if added_second:
                content += f"新增二阶编码 ({len(added_second)} 个):\n" + "\n".join([f"- {code}" for code in added_second[:10]])
                if len(added_second) > 10:
                    content += f"\n... 等 {len(added_second) - 10} 个编码"
                content += "\n\n"
            else:
                content += "新增二阶编码: 无\n\n"
            
            if updated_second:
                content += f"更新二阶编码 ({len(updated_second)} 个):\n" + "\n".join([f"- {code}" for code in updated_second[:10]])
                if len(updated_second) > 10:
                    content += f"\n... 等 {len(updated_second) - 10} 个编码"
            else:
                content += "更新二阶编码: 无"
            
            # 显示弹窗
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("编码库更新结果")
            msg.setText("编码库更新完成")
            msg.setInformativeText(content)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            
        except Exception as e:
            logger.error(f"显示编码更新结果弹窗失败: {e}")