# Transformer Model

## 如何加载模型
```python
from transformers import AutoModel, AutoTokenizer

model = AutoModel.from_pretrained("komorebi-Lee/Transformer")
tokenizer = AutoTokenizer.from_pretrained("komorebi-Lee/Transformer")
