import os
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import json

class SimpleModelInference:
    """简单模型推理类"""
    
    def __init__(self):
        """初始化模型推理"""
        self.model = None
        self.tokenizer = None
        self.label_to_id = {}
        self.id_to_label = {}
    
    def find_latest_model(self):
        """
        查找最新的训练模型
        
        Returns:
            str: 最新模型目录路径，如果不存在则返回None
        """
        trained_models_dir = "trained_models"
        if not os.path.exists(trained_models_dir):
            print(f"训练模型目录不存在: {trained_models_dir}")
            return None
        
        # 查找最新的模型目录
        model_dirs = []
        for item in os.listdir(trained_models_dir):
            item_path = os.path.join(trained_models_dir, item)
            if os.path.isdir(item_path):
                config_path = os.path.join(item_path, 'config.json')
                if os.path.exists(config_path):
                    model_dirs.append((item_path, os.path.getmtime(item_path)))
        
        if not model_dirs:
            print("没有找到训练好的模型")
            return None
        
        # 按修改时间排序，获取最新的模型
        model_dirs.sort(key=lambda x: x[1], reverse=True)
        return model_dirs[0][0]
    
    def load_model(self, model_dir=None):
        """
        加载训练好的模型
        
        Args:
            model_dir: 模型目录路径，如果为None则使用最新模型
        """
        if not model_dir:
            model_dir = self.find_latest_model()
            if not model_dir:
                return False
        
        print(f"正在加载模型: {model_dir}")
        
        try:
            # 加载标签映射
            label_mapping_path = os.path.join(model_dir, 'label_mapping.json')
            if os.path.exists(label_mapping_path):
                with open(label_mapping_path, 'r', encoding='utf-8') as f:
                    mapping_data = json.load(f)
                    self.label_to_id = mapping_data.get('label_to_id', {})
                    id_to_label_str = mapping_data.get('id_to_label', {})
                    self.id_to_label = {int(k): v for k, v in id_to_label_str.items()}
                print(f"标签映射已加载: {len(self.label_to_id)} 个标签")
            
            # 加载tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
            print("Tokenizer加载成功")
            
            # 加载模型
            num_labels = len(self.label_to_id) if self.label_to_id else 2
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_dir,
                num_labels=num_labels,
                ignore_mismatched_sizes=True,
                problem_type="single_label_classification"
            )
            
            # 移至设备
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(device)
            print(f"模型已加载到设备: {device}")
            
            return True
        except Exception as e:
            print(f"加载模型失败: {e}")
            return False
    
    def predict(self, texts):
        """
        预测文本类别
        
        Args:
            texts: 文本列表
        """
        if not self.model or not self.tokenizer:
            print("模型未加载，请先加载模型！")
            return
        
        print("\n开始预测...")
        try:
            # 编码文本
            encodings = self.tokenizer(
                texts,
                truncation=True,
                padding=True,
                max_length=512,
                return_tensors='pt'
            )
            
            # 移至设备
            device = next(self.model.parameters()).device
            encodings = {k: v.to(device) for k, v in encodings.items()}
            
            # 进行预测
            with torch.no_grad():
                outputs = self.model(**encodings)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)
                predictions = torch.argmax(logits, dim=-1)
                confidence_scores = torch.max(probabilities, dim=-1).values
            
            # 转换结果
            predicted_ids = predictions.cpu().numpy().tolist()
            predicted_labels = [self.id_to_label.get(pid, "未知") for pid in predicted_ids]
            confidence_scores = confidence_scores.cpu().numpy().tolist()
            
            # 打印结果
            for text, label, confidence in zip(texts, predicted_labels, confidence_scores):
                print(f"\n文本: {text}")
                print(f"预测标签: {label}")
                print(f"置信度: {confidence:.4f}")
        except Exception as e:
            print(f"预测失败: {e}")

if __name__ == "__main__":
    # 创建推理实例
    inference = SimpleModelInference()
    
    # 加载模型
    if inference.load_model():
        # 测试文本
        test_texts = [
            "这是一个测试文本，用于演示模型推理",
            "另一个测试句子，看看模型会如何分类",
            "这里是第三个测试案例"
        ]
        
        # 进行预测
        inference.predict(test_texts)
    else:
        print("无法加载模型，演示结束")
