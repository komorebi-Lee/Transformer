# BERT 模型调用指南

本指南详细说明如何调用在 `./trained_models` 目录中保存的微调训练后的 BERT 模型。

## 一、模型保存位置

训练完成后，模型会保存在以下位置：
- **默认路径**：`./trained_models/` 目录下的子文件夹
- **文件夹结构**：每个训练任务会创建一个独立的子文件夹，包含完整的模型文件

## 二、模型文件结构

每个训练模型文件夹包含以下文件：

| 文件名称 | 描述 | 用途 |
|---------|------|------|
| `config.json` | 模型配置文件 | 包含模型的架构参数 |
| `pytorch_model.bin` | 模型权重文件 | 包含训练后的模型参数 |
| `tokenizer.json` | 分词器配置 | 用于文本预处理 |
| `tokenizer_config.json` | 分词器配置 | 分词器的详细配置 |
| `vocab.txt` | 词汇表 | 模型使用的词汇表 |
| `label_mapping.json` | 标签映射 | 保存标签到ID的映射关系 |
| `training_config.json` | 训练配置 | 保存训练时的超参数配置 |

## 三、调用模型的方法

### 方法一：使用 BERTFineTuner 类（推荐）

```python
from bert_finetuner import BERTFineTuner
from config import Config

# 创建 BERTFineTuner 实例
finetuner = BERTFineTuner(None)  # 传入 None 作为 model_manager

# 加载模型
model_dir = "./trained_models/your_model_folder"  # 替换为实际模型目录
finetuner.load_model(model_dir)

# 检查模型是否加载成功
if finetuner.is_model_loaded():
    print("模型加载成功！")
    print(f"标签数量: {finetuner.get_num_labels()}")
    print(f"标签映射: {finetuner.get_label_info()}")

# 预测文本
texts = ["这是一个测试文本"]
predicted_ids, predicted_labels, confidence_scores = finetuner.predict(texts)

# 打印结果
for text, label, confidence in zip(texts, predicted_labels, confidence_scores):
    print(f"文本: {text}")
    print(f"预测标签: {label}")
    print(f"置信度: {confidence:.4f}")
```

### 方法二：直接使用 Hugging Face API

```python
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import json

# 模型目录
model_dir = "./trained_models/your_model_folder"  # 替换为实际模型目录

# 加载标签映射
label_mapping_path = f"{model_dir}/label_mapping.json"
with open(label_mapping_path, 'r', encoding='utf-8') as f:
    mapping_data = json.load(f)
    label_to_id = mapping_data.get('label_to_id', {})
    id_to_label = {int(k): v for k, v in mapping_data.get('id_to_label', {}).items()}

# 加载 tokenizer
tokenizer = AutoTokenizer.from_pretrained(model_dir)

# 加载模型
model = AutoModelForSequenceClassification.from_pretrained(
    model_dir,
    num_labels=len(label_to_id),
    ignore_mismatched_sizes=True,
    problem_type="single_label_classification"
)

# 移至设备
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# 准备输入文本
texts = ["这是一个测试文本"]

# 编码文本
encodings = tokenizer(
    texts,
    truncation=True,
    padding=True,
    max_length=512,
    return_tensors='pt'
)

# 移至设备
encodings = {k: v.to(device) for k, v in encodings.items()}

# 进行预测
with torch.no_grad():
    outputs = model(**encodings)
    logits = outputs.logits
    probabilities = torch.softmax(logits, dim=-1)
    predictions = torch.argmax(logits, dim=-1)
    confidence_scores = torch.max(probabilities, dim=-1).values

# 转换结果
predicted_ids = predictions.cpu().numpy().tolist()
predicted_labels = [id_to_label.get(pid, "未知") for pid in predicted_ids]
confidence_scores = confidence_scores.cpu().numpy().tolist()

# 打印结果
for text, label, confidence in zip(texts, predicted_labels, confidence_scores):
    print(f"文本: {text}")
    print(f"预测标签: {label}")
    print(f"置信度: {confidence:.4f}")
```

## 四、使用示例脚本

### 1. 使用 test_model_inference.py

```bash
# 运行示例脚本
python test_model_inference.py

# 或者指定模型目录
python test_model_inference.py --model_dir ./trained_models/your_model_folder
```

### 2. 使用 simple_model_inference.py

```bash
# 运行简单示例脚本
python simple_model_inference.py
```

## 五、常见问题解决

### 1. 模型目录不存在

- 确保模型已经成功训练并保存
- 检查 `./trained_models` 目录是否存在
- 确认训练过程中没有错误

### 2. 依赖问题

如果遇到依赖错误（如 `ImportError: cannot import name 'GGUF_CONFIG_MAPPING'`），请更新 transformers 库：

```bash
pip install --upgrade transformers
```

### 3. 预测结果不准确

- 确保输入文本格式与训练时一致
- 检查模型是否使用了正确的标签映射
- 考虑模型可能需要更多的训练数据

## 六、模型管理

### 查找最新模型

```python
def find_latest_model():
    """查找最新的训练模型"""
    trained_models_dir = "./trained_models"
    if not os.path.exists(trained_models_dir):
        return None
    
    model_dirs = []
    for item in os.listdir(trained_models_dir):
        item_path = os.path.join(trained_models_dir, item)
        if os.path.isdir(item_path):
            config_path = os.path.join(item_path, 'config.json')
            if os.path.exists(config_path):
                model_dirs.append((item_path, os.path.getmtime(item_path)))
    
    if not model_dirs:
        return None
    
    # 按修改时间排序，获取最新的模型
    model_dirs.sort(key=lambda x: x[1], reverse=True)
    return model_dirs[0][0]
```

### 模型评估

```python
# 使用 BERTFineTuner 评估模型
metrics = finetuner.evaluate(eval_dataset)
print(f"评估结果: {metrics}")
```

## 七、注意事项

1. **设备选择**：模型会自动使用 GPU（如果可用），否则使用 CPU
2. **输入长度**：默认最大输入长度为 512  tokens，超过会被截断
3. **批量预测**：可以一次输入多个文本进行批量预测
4. **置信度**：预测结果包含置信度分数，可以用于过滤低置信度的预测
5. **标签映射**：确保使用与训练时相同的标签映射，否则预测结果会不正确

## 八、完整示例

### 示例 1：基本预测

```python
from bert_finetuner import BERTFineTuner

# 初始化并加载模型
finetuner = BERTFineTuner(None)
model_dir = "./trained_models/20240101_120000"  # 示例模型目录
finetuner.load_model(model_dir)

# 预测
texts = ["这是一个测试句子", "另一个需要分类的文本"]
predicted_ids, predicted_labels, confidence_scores = finetuner.predict(texts)

# 输出结果
for i, (text, label, conf) in enumerate(zip(texts, predicted_labels, confidence_scores)):
    print(f"示例 {i+1}:")
    print(f"文本: {text}")
    print(f"预测标签: {label}")
    print(f"置信度: {conf:.4f}")
    print()
```

### 示例 2：批量预测

```python
from bert_finetuner import BERTFineTuner

# 初始化并加载模型
finetuner = BERTFineTuner(None)
model_dir = "./trained_models/latest_model"  # 替换为实际模型目录
finetuner.load_model(model_dir)

# 批量预测
batch_texts = [
    "客户对产品质量非常满意",
    "服务态度有待改进",
    "价格合理，性价比高",
    "物流速度太慢了"
]

# 预测结果
ids, labels, scores = finetuner.predict(batch_texts)

# 处理结果
for text, label, score in zip(batch_texts, labels, scores):
    print(f"文本: {text}")
    print(f"情感: {label}")
    print(f"置信度: {score:.4f}")
    print()
```

---

通过以上方法，您可以轻松调用训练好的 BERT 模型进行文本分类任务。如果在使用过程中遇到任何问题，请检查模型文件是否完整，以及依赖库是否正确安装。