import os
import logging
from transformers import AutoTokenizer, AutoModel
import torch
from sentence_transformers import SentenceTransformer
from config import Config

logger = logging.getLogger(__name__)


class ModelDownloader:
    """模型下载器 - 修复版本"""

    def __init__(self):
        self.local_models_dir = Config.LOCAL_MODELS_DIR
        self.trained_models_dir = Config.TRAINED_MODELS_DIR

    def download_bert_model(self) -> str:
        """下载BERT中文模型"""
        try:
            model_name = Config.DEFAULT_MODEL_NAME
            model_path = os.path.join(self.local_models_dir, model_name)

            if os.path.exists(model_path):
                logger.info("BERT模型已存在，跳过下载")
                return model_path

            logger.info("开始下载BERT中文模型...")

            # 下载tokenizer和模型
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModel.from_pretrained(model_name)

            # 保存到本地
            tokenizer.save_pretrained(model_path)
            model.save_pretrained(model_path)

            logger.info(f"BERT模型下载完成: {model_path}")
            return model_path

        except Exception as e:
            logger.error(f"BERT模型下载失败: {e}")
            return self.create_fallback_model()

    def download_sentence_transformer(self) -> str:
        """下载句子Transformer模型"""
        try:
            model_name = Config.SENTENCE_MODEL_NAME
            model_path = os.path.join(self.local_models_dir, "sentence-transformer")

            if os.path.exists(model_path):
                logger.info("句子Transformer模型已存在")
                return model_path

            logger.info("开始下载句子Transformer模型...")
            # 设置较小的超时时间，避免卡住
            model = SentenceTransformer(model_name)
            model.save(model_path)

            logger.info(f"句子Transformer模型下载完成: {model_path}")
            return model_path

        except Exception as e:
            logger.error(f"句子Transformer模型下载失败: {e}")
            return None

    def download_mini_model(self) -> str:
        """下载轻量级模型 - 兼容性方法"""
        return self.download_bert_model()

    def download_all_models(self) -> bool:
        """下载所有必要的模型"""
        try:
            success_count = 0

            # 下载BERT模型
            bert_path = self.download_bert_model()
            if bert_path and "fallback" not in bert_path:
                success_count += 1
                logger.info("BERT模型下载成功")
            else:
                logger.warning("BERT模型下载失败，使用降级模式")

            # 尝试下载句子Transformer模型（可选，不是必需的）
            try:
                st_path = self.download_sentence_transformer()
                if st_path:
                    success_count += 1
                    logger.info("句子Transformer模型下载成功")
                else:
                    logger.warning("句子Transformer模型下载失败，将继续使用BERT模型")
            except Exception as e:
                logger.warning(f"句子Transformer模型下载失败，将继续使用BERT模型: {e}")

            # 只要BERT模型成功就返回True
            return bert_path and "fallback" not in bert_path

        except Exception as e:
            logger.error(f"下载模型失败: {e}")
            return False

    def create_fallback_model(self) -> str:
        """创建降级模型（当网络不可用时）"""
        fallback_path = os.path.join(self.local_models_dir, "fallback")
        os.makedirs(fallback_path, exist_ok=True)

        # 创建标记文件表示这是降级模式
        with open(os.path.join(fallback_path, "fallback.mode"), "w") as f:
            f.write("fallback_mode")

        logger.info("创建降级模式，将使用规则-based编码")
        return fallback_path

    def get_available_trained_models(self) -> list:
        """获取所有训练过的模型"""
        models = []
        if os.path.exists(self.trained_models_dir):
            for file in os.listdir(self.trained_models_dir):
                if file.endswith('.pkl'):
                    models.append(file.replace('.pkl', ''))
        return sorted(models, reverse=True)

    def cleanup_old_models(self, keep_count: int = 5):
        """清理旧的训练模型，只保留最新的几个"""
        models = self.get_available_trained_models()
        if len(models) > keep_count:
            for model_name in models[keep_count:]:
                model_path = os.path.join(self.trained_models_dir, f"{model_name}.pkl")
                try:
                    os.remove(model_path)
                    logger.info(f"清理旧模型: {model_name}")
                except Exception as e:
                    logger.error(f"清理模型失败 {model_name}: {e}")

    def is_model_available(self, model_type: str = "bert") -> bool:
        """检查模型是否可用"""
        if model_type == "bert":
            model_path = os.path.join(self.local_models_dir, Config.DEFAULT_MODEL_NAME)
            return os.path.exists(model_path)
        elif model_type == "sentence":
            model_path = os.path.join(self.local_models_dir, "sentence-transformer")
            return os.path.exists(model_path)
        return False