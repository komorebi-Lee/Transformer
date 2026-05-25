import os
import logging
from typing import Dict, Tuple

from config import Config

logger = logging.getLogger(__name__)


class ModelDownloader:
    """模型下载器 — 委托给 model_builder.py 构建/下载"""

    def __init__(self):
        self.local_models_dir = Config.LOCAL_MODELS_DIR
        self.trained_models_dir = Config.TRAINED_MODELS_DIR

    # =========================================================================
    # 兼容旧接口 — 全部委托给 model_builder
    # =========================================================================

    def download_bert_model(self) -> str:
        """兼容方法：构建部署用 BERT 模型"""
        from model_builder import build_all
        build_all()
        path = os.path.join(self.local_models_dir, Config.RERANKER_MODEL_NAME)
        return path if os.path.exists(path) else self.create_fallback_model()

    def download_sentence_transformer(self) -> str:
        """兼容方法：下载/构建 sentence 模型"""
        from model_builder import download_sentence_model
        return download_sentence_model()

    def download_mini_model(self) -> str:
        return self.download_bert_model()

    def download_all_models(self) -> bool:
        """构建/下载全部模型"""
        try:
            from model_builder import build_all
            build_all()
            return self.is_model_available("bert")
        except Exception as e:
            logger.error(f"模型构建失败: {e}")
            return False

    def create_fallback_model(self) -> str:
        """创建降级模型（当网络不可用时）"""
        fallback_path = os.path.join(self.local_models_dir, "fallback")
        os.makedirs(fallback_path, exist_ok=True)
        with open(os.path.join(fallback_path, "fallback.mode"), "w") as f:
            f.write("fallback_mode")
        logger.info("创建降级模式，将使用规则-based编码")
        return fallback_path

    # =========================================================================
    # 训练模型管理（不变）
    # =========================================================================

    def get_available_trained_models(self) -> list:
        """获取所有训练过的模型（支持PKL和BERT微调两种格式）"""
        models = []
        if os.path.exists(self.trained_models_dir):
            for item in os.listdir(self.trained_models_dir):
                item_path = os.path.join(self.trained_models_dir, item)
                if item.endswith('.pkl'):
                    models.append({
                        'name': item.replace('.pkl', ''),
                        'type': 'classifier',
                        'path': item_path
                    })
                elif os.path.isdir(item_path):
                    if self._is_bert_finetune_model(item_path):
                        models.append({
                            'name': item,
                            'type': 'bert_finetune',
                            'path': item_path
                        })
        return sorted(models, key=lambda x: x['name'], reverse=True)

    def _is_bert_finetune_model(self, model_dir: str) -> bool:
        """检查目录是否为BERT微调模型"""
        try:
            config_path = os.path.join(model_dir, 'config.json')
            model_safetensors_path = os.path.join(model_dir, 'model.safetensors')
            pytorch_model_path = os.path.join(model_dir, 'pytorch_model.bin')
            label_mapping_path = os.path.join(model_dir, 'label_mapping.json')

            has_config = os.path.exists(config_path)
            has_weights = os.path.exists(model_safetensors_path) or os.path.exists(pytorch_model_path)
            has_label_mapping = os.path.exists(label_mapping_path)

            return has_config and has_weights and has_label_mapping
        except Exception as e:
            logger.error(f"检查BERT微调模型时出错: {e}")
            return False

    def get_available_trained_model_names(self) -> list:
        """获取所有训练过的模型名称列表（用于UI显示）"""
        models = self.get_available_trained_models()
        return [f"{m['name']} ({'BERT微调' if m['type'] == 'bert_finetune' else '分类器'})" for m in models]

    def cleanup_old_models(self, keep_count: int = 5):
        """清理旧的训练模型，只保留最新的几个"""
        models = self.get_available_trained_models()
        if len(models) > keep_count:
            for model_info in models[keep_count:]:
                model_path = model_info['path']
                try:
                    if os.path.isdir(model_path):
                        import shutil
                        shutil.rmtree(model_path)
                    else:
                        os.remove(model_path)
                    logger.info(f"清理旧模型: {model_info['name']}")
                except Exception as e:
                    logger.error(f"清理模型失败 {model_info['name']}: {e}")

    def is_model_available(self, model_type: str = "bert") -> bool:
        """检查模型是否可用"""
        if model_type == "bert":
            model_path = os.path.join(self.local_models_dir, Config.RERANKER_MODEL_NAME)
            return os.path.exists(model_path)
        elif model_type == "sentence":
            for p in [
                os.path.join(self.local_models_dir, Config.SENTENCE_MODEL_NAME.replace('/', '_')),
                os.path.join(self.local_models_dir, "sentence-transformer"),
            ]:
                if os.path.exists(p):
                    return True
            return False
        return False