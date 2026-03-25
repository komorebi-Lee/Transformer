import logging
from bert_finetuner import BERTFineTuner
from model_manager import ModelManager

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

def test_bert_prediction():
    """测试 BERT 模型预测功能"""
    try:
        # 初始化模型管理器
        model_manager = ModelManager()
        
        # 加载微调模型
        logger.info("正在加载微调BERT模型...")
        success = model_manager.load_finetuned_bert()
        if not success:
            logger.error("加载模型失败")
            return False
        
        # 准备测试文本
        test_texts = [
            "这是一个测试文本，用于验证BERT模型的预测功能",
            "另一个测试文本，确保模型能够正确处理",
            "第三个测试文本，测试批量预测",
            "第四个测试文本，检查内存使用情况",
            "第五个测试文本，验证模型的稳定性"
        ]
        
        # 测试预测
        logger.info("开始预测...")
        predictions, predicted_labels = model_manager.predict_with_loaded_model(test_texts)
        
        logger.info("预测结果:")
        for text, label in zip(test_texts, predicted_labels):
            logger.info(f"文本: {text[:50]}... -> 预测标签: {label}")
        
        logger.info("测试成功！")
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        return False

if __name__ == "__main__":
    test_bert_prediction()
