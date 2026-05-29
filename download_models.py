#!/usr/bin/env python3
"""
模型预下载脚本
在启动主程序前先下载所有必要的模型
"""

import os
import sys
import logging
from transformers import AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class ModelPreDownloader:
    """模型预下载器"""

    def __init__(self):
        self.local_models_dir = "local_models"
        os.makedirs(self.local_models_dir, exist_ok=True)

    def download_bert_model(self):
        """下载BERT中文模型"""
        try:
            model_name = "bert-base-chinese"
            model_path = os.path.join(self.local_models_dir, model_name)

            if os.path.exists(model_path):
                logger.info("✅ BERT模型已存在，跳过下载")
                return True

            logger.info("📥 开始下载BERT中文模型...")
            print("正在下载BERT模型，这可能需要几分钟时间...")

            # 下载tokenizer和模型
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModel.from_pretrained(model_name)

            # 保存到本地
            tokenizer.save_pretrained(model_path)
            model.save_pretrained(model_path)

            logger.info(f"✅ BERT模型下载完成: {model_path}")
            return True

        except Exception as e:
            logger.error(f"❌ BERT模型下载失败: {e}")
            return False

    def download_sentence_transformer(self):
        """下载句子Transformer模型"""
        try:
            model_name = Config.SENTENCE_MODEL_NAME
            model_path = os.path.join(self.local_models_dir, Config.SENTENCE_MODEL_NAME.replace('/', '_') if '/' in Config.SENTENCE_MODEL_NAME else Config.SENTENCE_MODEL_NAME)

            if os.path.exists(model_path):
                logger.info("句子Transformer模型已存在，跳过下载")
                return True

            logger.info(f"开始下载句子Transformer模型: {model_name}")
            print(f"正在下载句子Transformer模型 ({model_name})，这可能需要几分钟时间...")

            model = SentenceTransformer(model_name)
            model.save(model_path)

            logger.info(f"✅ 句子Transformer模型下载完成: {model_path}")
            return True

        except Exception as e:
            logger.error(f"❌ 句子Transformer模型下载失败: {e}")
            return False

    def download_all_models(self):
        """下载所有必要的模型"""
        print("=" * 50)
        print("扎根理论编码分析系统 - 模型预下载")
        print("=" * 50)

        success_count = 0

        # 下载BERT模型
        if self.download_bert_model():
            success_count += 1

        # 下载句子Transformer模型
        if self.download_sentence_transformer():
            success_count += 1

        print("=" * 50)
        if success_count >= 1:
            print("✅ 模型下载完成！现在可以启动主程序。")
            return True
        else:
            print("❌ 模型下载失败，请检查网络连接后重试。")
            return False


def main():
    """主函数"""
    downloader = ModelPreDownloader()
    success = downloader.download_all_models()

    if success:
        print("\n🎉 所有模型已准备就绪！")
        print("现在可以运行: python app_launcher.py")
        return 0
    else:
        print("\n⚠️  模型下载失败，程序可能无法正常工作。")
        print("请检查网络连接后重新运行此脚本。")
        return 1


if __name__ == "__main__":
    sys.exit(main())