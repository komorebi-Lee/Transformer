"""
轻量级问答分类器
使用 MiniLM 或 DistilBERT 进行 Question/Answer/Other 三分类
"""

import logging
import torch
from typing import List, Dict, Tuple
import numpy as np

logger = logging.getLogger(__name__)

try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers 未安装，问答分类器不可用")


class QAClassifier:
    """
    轻量级问答分类器
    
    分类标签：
    - 0: Question (访谈员问句)
    - 1: Answer (受访者回答)
    - 2: Other (其他/不确定)
    """
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        """
        初始化分类器
        
        Args:
            model_name: 预训练模型名称
                - "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2" (推荐，118MB)
                - "distilbert-base-multilingual-cased" (更大，但效果更好)
        """
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.label_map = {0: 'question', 1: 'answer', 2: 'other'}
        
        # 是否已加载模型
        self.loaded = False
    
    def load_model(self, model_path: str = None):
        """
        加载模型
        
        Args:
            model_path: 微调后的模型路径（如果为None，使用预训练模型 + 规则）
        """
        if not TRANSFORMERS_AVAILABLE:
            logger.error("transformers 未安装，无法加载模型")
            return False
        
        try:
            if model_path:
                # 加载微调后的模型
                logger.info(f"加载微调模型: {model_path}")
                self.tokenizer = AutoTokenizer.from_pretrained(model_path)
                self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
            else:
                # 使用预训练模型（需要配合规则）
                logger.info(f"加载预训练模型: {self.model_name}")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                # 注意：预训练模型没有分类头，需要添加
                # 这里我们先用规则模式，等有标注数据后再微调
                logger.warning("预训练模型未微调，将使用规则辅助模式")
                self.model = None  # 标记为规则模式
            
            if self.model:
                self.model.to(self.device)
                self.model.eval()
            
            self.loaded = True
            logger.info("模型加载成功")
            return True
        
        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            return False
    
    def classify(self, text: str) -> Dict[str, any]:
        """
        单句分类（便捷方法）
        
        Args:
            text: 单个文本
            
        Returns:
            {
                'text': '原文',
                'label': 'answer',  # question / answer / other
                'confidence': 0.95,
                'scores': {'question': 0.02, 'answer': 0.95, 'other': 0.03}
            }
        """
        results = self.classify_batch([text])
        return results[0] if results else {
            'text': text,
            'label': 'other',
            'confidence': 0.5,
            'scores': {'question': 0.33, 'answer': 0.33, 'other': 0.34}
        }
    
    def classify_batch(self, texts: List[str]) -> List[Dict[str, any]]:
        """
        批量分类
        
        Args:
            texts: 文本列表
            
        Returns:
            [
                {
                    'text': '原文',
                    'label': 'answer',  # question / answer / other
                    'confidence': 0.95,
                    'scores': {'question': 0.02, 'answer': 0.95, 'other': 0.03}
                },
                ...
            ]
        """
        if not self.loaded:
            logger.warning("模型未加载，使用规则模式")
            return self._classify_by_rules(texts)
        
        if self.model is None:
            # 规则模式
            return self._classify_by_rules(texts)
        
        # 模型模式
        return self._classify_by_model(texts)
    
    def _classify_by_model(self, texts: List[str]) -> List[Dict[str, any]]:
        """使用模型分类"""
        results = []
        
        try:
            # Tokenize
            inputs = self.tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=128,
                return_tensors='pt'
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # 推理
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=-1)
            
            # 解析结果
            probs_np = probs.cpu().numpy()
            for i, text in enumerate(texts):
                prob = probs_np[i]
                label_id = int(np.argmax(prob))
                label = self.label_map[label_id]
                confidence = float(prob[label_id])
                
                results.append({
                    'text': text,
                    'label': label,
                    'confidence': confidence,
                    'scores': {
                        'question': float(prob[0]),
                        'answer': float(prob[1]),
                        'other': float(prob[2])
                    }
                })
        
        except Exception as e:
            logger.error(f"模型推理失败: {e}")
            # 降级到规则模式
            return self._classify_by_rules(texts)
        
        return results
    
    def _classify_by_rules(self, texts: List[str]) -> List[Dict[str, any]]:
        """
        使用规则分类（当模型不可用时的降级方案）
        
        规则：
        - 包含疑问词 + 问号结尾 = Question
        - 长句 + 陈述特征 = Answer
        - 其他 = Other
        """
        results = []
        
        question_indicators = [
            '什么', '如何', '怎么', '怎样', '为什么', '哪', '吗', '呢',
            '您觉得', '您认为', '您是', '请问', '想问'
        ]
        
        answer_indicators = [
            '我觉得', '我认为', '我们', '因为', '所以', '就是',
            '团队', '工作', '项目', '负责', '管理'
        ]
        
        for text in texts:
            text_clean = text.strip()
            
            # 判断是否为问句
            is_question = (
                text_clean.endswith(('？', '?')) and
                any(ind in text_clean for ind in question_indicators)
            )
            
            # 判断是否为回答
            is_answer = (
                len(text_clean) > 15 and
                any(ind in text_clean for ind in answer_indicators) and
                not text_clean.endswith(('？', '?'))
            )
            
            if is_question:
                label = 'question'
                confidence = 0.8
                scores = {'question': 0.8, 'answer': 0.1, 'other': 0.1}
            elif is_answer:
                label = 'answer'
                confidence = 0.7
                scores = {'question': 0.1, 'answer': 0.7, 'other': 0.2}
            else:
                # 既不是明确问句也不是明确回答 → other，不强行归类
                label = 'other'
                confidence = 0.5
                scores = {'question': 0.33, 'answer': 0.33, 'other': 0.34}
            
            results.append({
                'text': text,
                'label': label,
                'confidence': confidence,
                'scores': scores
            })
        
        return results
    
    def classify_single(self, text: str) -> Dict[str, any]:
        """单条分类"""
        return self.classify_batch([text])[0]


# ============================================================
# 训练脚本（需要标注数据）
# ============================================================

def prepare_training_data(annotated_file: str) -> Tuple[List[str], List[int]]:
    """
    准备训练数据
    
    Args:
        annotated_file: 标注文件路径（CSV格式）
            格式：text,label
            例如：
                "那您觉得景漂这个称呼对您意味着是什么呢？",question
                "那倒没有可能也就只是一个标签吧。",answer
    
    Returns:
        (texts, labels)
    """
    import pandas as pd
    
    df = pd.read_csv(annotated_file)
    
    label_to_id = {'question': 0, 'answer': 1, 'other': 2}
    
    texts = df['text'].tolist()
    labels = [label_to_id[label] for label in df['label']]
    
    return texts, labels


def train_qa_classifier(
    train_texts: List[str],
    train_labels: List[int],
    output_dir: str = './qa_classifier_model',
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    epochs: int = 3,
    batch_size: int = 16
):
    """
    训练问答分类器
    
    Args:
        train_texts: 训练文本
        train_labels: 训练标签 (0=question, 1=answer, 2=other)
        output_dir: 输出目录
        model_name: 预训练模型名称
        epochs: 训练轮数
        batch_size: 批次大小
    """
    if not TRANSFORMERS_AVAILABLE:
        raise ImportError("需要安装 transformers: pip install transformers")
    
    from transformers import (
        AutoTokenizer,
        AutoModelForSequenceClassification,
        TrainingArguments,
        Trainer,
        DataCollatorWithPadding
    )
    from datasets import Dataset
    
    # 加载预训练模型
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=3  # question, answer, other
    )
    
    # 准备数据集
    dataset = Dataset.from_dict({
        'text': train_texts,
        'label': train_labels
    })
    
    def tokenize_function(examples):
        return tokenizer(
            examples['text'],
            padding='max_length',
            truncation=True,
            max_length=128
        )
    
    tokenized_dataset = dataset.map(tokenize_function, batched=True)
    
    # 训练参数
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        warmup_steps=100,
        weight_decay=0.01,
        logging_dir=f'{output_dir}/logs',
        logging_steps=10,
        save_strategy='epoch',
        evaluation_strategy='no',
    )
    
    # 训练
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
    )
    
    logger.info("开始训练...")
    trainer.train()
    
    # 保存模型
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    logger.info(f"模型已保存到: {output_dir}")


# ============================================================
# 测试代码
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("测试问答分类器（规则模式）")
    print("=" * 60)
    
    classifier = QAClassifier()
    classifier.load_model()  # 规则模式
    
    test_texts = [
        "那您觉得景漂这个称呼对您意味着是什么呢？",
        "那倒没有可能也就只是一个标签吧。",
        "那您刚来的时候遇到的最大困难是什么呢？",
        "没钱哦。当时真的很困难。",
        "那如何解决这个困难呢？",
        "就是慢慢积累，一点一点做起来的。",
    ]
    
    results = classifier.classify_batch(test_texts)
    
    for i, result in enumerate(results):
        print(f"\n[{i+1}] {result['label'].upper()} (置信度: {result['confidence']:.2f})")
        print(f"    {result['text']}")
        print(f"    分数: Q={result['scores']['question']:.2f}, "
              f"A={result['scores']['answer']:.2f}, "
              f"O={result['scores']['other']:.2f}")
    
    print("\n" + "=" * 60)
    print("提取受访者回答:")
    print("=" * 60)
    
    answers = [r for r in results if r['label'] == 'answer']
    for i, ans in enumerate(answers):
        print(f"{i+1}. {ans['text']}")
