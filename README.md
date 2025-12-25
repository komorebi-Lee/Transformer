# Transformer Model

## 如何加载模型
```python
from transformers import AutoModel, AutoTokenizer

model = AutoModel.from_pretrained("your-username/Transformer")
tokenizer = AutoTokenizer.from_pretrained("your-username/Transformer")
