# 训练功能使用指南

本文档介绍扎根理论编码系统的训练功能，包括BERT微调训练、分类器训练、增量训练以及超参数寻优等功能。

## 目录

1. [新训练功能概述](#新训练功能概述)
2. [训练模式说明](#训练模式说明)
3. [超参数寻优使用说明](#超参数寻优使用说明)
4. [训练最佳实践指南](#训练最佳实践指南)
5. [常见问题解答](#常见问题解答)

---

## 新训练功能概述

本系统提供了完整的模型训练解决方案，支持以下核心功能：

### 功能特性

| 功能 | 描述 | 适用场景 |
|------|------|----------|
| BERT微调训练 | 对预训练BERT模型进行微调 | 数据量充足、精度要求高 |
| 分类器训练 | 基于嵌入向量的分类器训练 | 快速训练、资源受限 |
| 增量训练 | 在已有模型基础上继续训练 | 数据持续积累、模型迭代 |
| 超参数寻优 | 自动寻找最优训练参数 | 追求最佳模型性能 |

### 系统架构

```
训练流程架构图（文字描述）:

┌─────────────────────────────────────────────────────────────┐
│                      训练管理系统                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 数据准备模块 │  │ 模型训练模块 │  │ 评估优化模块 │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         ▼                ▼                ▼                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 数据集创建  │  │ BERT微调    │  │ 超参数寻优  │         │
│  │ 数据增强    │  │ 分类器训练  │  │ 交叉验证    │         │
│  │ 数据分割    │  │ 增量训练    │  │ 模型评估    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

---

## 训练模式说明

### 1. BERT微调训练

BERT微调训练是对预训练BERT模型进行端到端的微调，适用于数据量充足且对模型精度要求较高的场景。

#### 工作原理

```
BERT微调流程:

输入文本 → BERT编码器 → 分类头 → 预测结果
              ↓
         微调参数更新
```

#### 使用方法

```python
from bert_finetuner import BERTFineTuner
from bert_dataset import create_dataset_from_standard_answers

finetuner = BERTFineTuner(
    model_manager=model_manager,
    config={
        'learning_rate': 2e-5,
        'num_train_epochs': 3,
        'batch_size': 16,
        'warmup_ratio': 0.1,
        'weight_decay': 0.01,
        'early_stopping_patience': 3
    }
)

dataset = create_dataset_from_standard_answers(
    standard_answer_manager,
    max_length=512
)

success = finetuner.train(
    dataset=dataset,
    output_dir='./trained_models/my_model'
)

if success:
    print("训练完成！")
    metrics = finetuner.evaluate(dataset)
    print(f"评估结果: {metrics}")
```

#### 配置参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `learning_rate` | 2e-5 | 学习率，建议范围1e-5到5e-5 |
| `num_train_epochs` | 3 | 训练轮数，通常2-5轮足够 |
| `batch_size` | 16 | 批次大小，根据GPU显存调整 |
| `warmup_ratio` | 0.1 | 预热比例，学习率从0逐渐增加 |
| `weight_decay` | 0.01 | 权重衰减，防止过拟合 |
| `early_stopping_patience` | 3 | 早停耐心值，验证损失不再下降时停止 |
| `max_grad_norm` | 1.0 | 梯度裁剪阈值 |
| `dropout_rate` | 0.1 | Dropout比例 |

#### 硬件要求

- **GPU**: 建议NVIDIA GPU，显存至少2GB（推荐4GB以上）
- **内存**: 至少8GB RAM
- **存储**: 模型文件约400MB-1GB

### 2. 分类器训练

分类器训练使用预训练模型提取文本嵌入向量，然后训练一个轻量级分类器。适用于快速训练和资源受限的场景。

#### 工作原理

```
分类器训练流程:

输入文本 → 预训练编码器 → 固定嵌入向量 → 分类器 → 预测结果
                                         ↓
                                   分类器参数更新
```

#### 使用方法

```python
from training_manager import EnhancedTrainingManager

training_manager = EnhancedTrainingManager()
training_manager.set_standard_answer_manager(standard_answer_manager)

training_manager.train_grounded_theory_model(
    training_data=training_data,
    model_manager=model_manager,
    model_type='bert',
    training_mode='classifier',
    progress_callback=lambda progress: print(f"训练进度: {progress}%"),
    finished_callback=lambda success, msg: print(f"训练{'成功' if success else '失败'}: {msg}")
)
```

#### 优势

- 训练速度快，通常几秒到几分钟
- 硬件要求低，CPU即可运行
- 适合快速原型验证

### 3. 增量训练

增量训练允许在已有模型基础上继续训练，适用于数据持续积累的场景。

#### 工作原理

```
增量训练流程:

已有模型 → 加载模型参数 → 合并新旧数据 → 继续训练 → 更新后的模型
              ↓
         调整学习率（降低）
```

#### 使用方法

```python
from bert_finetuner import BERTFineTuner

finetuner = BERTFineTuner(model_manager)

success = finetuner.train_incremental(
    dataset=new_dataset,
    output_dir='./trained_models/incremental_model',
    existing_model_path='./trained_models/previous_model',
    old_data=old_dataset,
    update_mode='append',
    data_version='v_20240101'
)

if success:
    info = finetuner.get_incremental_info()
    print(f"增量训练次数: {info['incremental_count']}")
    print(f"总训练样本数: {info['total_samples_trained']}")
```

#### 数据更新模式

| 模式 | 说明 |
|------|------|
| `append` | 将新数据追加到旧数据后进行训练 |
| `update` | 用新数据更新旧数据中的重复样本 |
| `replace` | 完全使用新数据进行训练 |

#### 增量训练策略

```python
增量训练学习率调整策略:

原始学习率: 2e-5
增量学习率 = 原始学习率 × 0.5 = 1e-5

原因: 已训练模型已接近最优解，使用较小学习率避免破坏已学习的特征
```

---

## 超参数寻优使用说明

超参数寻优功能帮助自动寻找最优的训练参数组合，提升模型性能。

### 支持的优化方法

#### 1. 网格搜索 (Grid Search)

遍历所有参数组合，找到最优解。

```python
from hyperparameter_optimizer import HyperparameterOptimizer

optimizer = HyperparameterOptimizer(model_manager)

search_space = {
    'learning_rate': [1e-5, 2e-5, 5e-5],
    'batch_size': [8, 16, 32],
    'epochs': [2, 3, 5],
    'dropout_rate': [0.1, 0.2, 0.3]
}

result = optimizer.grid_search(
    dataset=dataset,
    search_space=search_space,
    cv_folds=3,
    progress_callback=lambda current, total, params: 
        print(f"进度: {current}/{total}, 当前参数: {params}")
)

print(f"最优参数: {result['best_params']}")
print(f"最优分数: {result['best_score']}")
```

#### 2. 贝叶斯优化 (Bayesian Optimization)

使用Optuna库进行智能参数搜索，效率更高。

```python
result = optimizer.bayesian_optimization(
    dataset=dataset,
    n_trials=20,
    search_space=search_space,
    progress_callback=lambda current, total, params:
        print(f"试验: {current}/{total}")
)

print(f"最优参数: {result['best_params']}")
print(f"最优分数: {result['best_score']}")
```

### 参数保存与加载

```python
optimizer.save_best_params(
    result['best_params'],
    './config/best_params.json'
)

loaded_params = optimizer.load_best_params(
    './config/best_params.json'
)
```

### 查看优化历史

```python
top_5_params = optimizer.get_top_n_params(n=5)

for i, record in enumerate(top_5_params, 1):
    print(f"第{i}名: 参数={record['params']}, 分数={record['score']}")
```

### 优化界面说明

```
超参数寻优界面（文字描述）:

┌─────────────────────────────────────────────────────────────┐
│  超参数寻优设置                                              │
├─────────────────────────────────────────────────────────────┤
│  搜索方法:  ○ 网格搜索  ● 贝叶斯优化                        │
│                                                             │
│  搜索空间:                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 学习率: [1e-5, 2e-5, 5e-5]                          │   │
│  │ 批次大小: [8, 16, 32]                               │   │
│  │ 训练轮数: [2, 3, 5]                                 │   │
│  │ Dropout: [0.1, 0.2, 0.3]                            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  交叉验证折数: [3]                                          │
│  贝叶斯优化试验次数: [20]                                    │
│                                                             │
│  [开始寻优]  [取消]                                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  优化进度                                                    │
├─────────────────────────────────────────────────────────────┤
│  当前进度: ████████████░░░░░░░░ 60% (12/20)                 │
│  当前最优分数: 0.85                                          │
│  当前最优参数: {learning_rate: 2e-5, batch_size: 16, ...}    │
└─────────────────────────────────────────────────────────────┘
```

---

## 训练最佳实践指南

### 数据准备建议

#### 1. 数据质量

```python
数据质量检查清单:

✓ 确保每个类别至少有5-10个样本
✓ 移除重复或高度相似的文本
✓ 检查标签一致性，避免同一文本不同标签
✓ 清理无效字符和格式问题
✓ 确保文本长度适中（建议10-500字符）
```

#### 2. 数据增强

```python
from bert_dataset import augment_text

original_text = "这是一个测试文本"
augmented_text = augment_text(original_text, augmentation_prob=0.3)

支持的增强方法:
- 同义词替换: "很好" → "非常好"
- 随机删除: 删除部分字符
- 随机交换: 交换字符位置
```

#### 3. 数据分割

```python
from bert_dataset import split_dataset

train_dataset, val_dataset = split_dataset(
    dataset,
    train_ratio=0.8,
    random_seed=42
)

推荐分割比例:
- 小数据集 (< 100样本): 80% 训练, 20% 验证
- 中等数据集 (100-1000样本): 70% 训练, 15% 验证, 15% 测试
- 大数据集 (> 1000样本): 60% 训练, 20% 验证, 20% 测试
```

### 参数调优建议

#### 1. 学习率选择

```
学习率选择指南:

数据量      推荐学习率
─────────────────────────
< 100样本    1e-5
100-500样本  2e-5
> 500样本    3e-5 到 5e-5

提示: 如果训练损失震荡，降低学习率
      如果训练收敛太慢，可适当提高学习率
```

#### 2. 批次大小选择

```
批次大小选择指南:

GPU显存      推荐批次大小
─────────────────────────
2GB          4-8
4GB          8-16
8GB          16-32
16GB+        32-64

提示: 较大批次通常训练更稳定，但可能降低泛化能力
```

#### 3. 训练轮数选择

```
训练轮数选择指南:

数据量      推荐轮数
─────────────────────────
< 50样本     5-10轮
50-200样本   3-5轮
> 200样本    2-3轮

提示: 使用早停机制避免过拟合
```

### 增量训练策略

#### 1. 增量训练时机

```
适合增量训练的场景:

✓ 新增数据量达到原有数据的10%以上
✓ 发现新的类别需要添加
✓ 模型在某些类别上表现不佳
✓ 定期模型更新维护

不适合增量训练的场景:

✗ 新增数据量很少 (< 10样本)
✗ 数据分布发生重大变化
✗ 需要添加大量新类别
```

#### 2. 增量训练最佳实践

```python
增量训练最佳实践代码示例:

def smart_incremental_training(finetuner, new_data, existing_model_path):
    if len(new_data) < 10:
        print("新增数据不足，建议积累更多数据后训练")
        return False
    
    previous_info = finetuner.get_incremental_info()
    if previous_info['incremental_count'] >= 5:
        print("增量训练次数过多，建议重新完整训练")
        return False
    
    success = finetuner.train_incremental(
        dataset=new_data,
        output_dir='./models/incremental',
        existing_model_path=existing_model_path,
        update_mode='append'
    )
    
    return success
```

### 性能优化建议

#### 1. GPU加速

```python
import torch

if torch.cuda.is_available():
    print(f"使用GPU: {torch.cuda.get_device_name(0)}")
    print(f"显存: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
else:
    print("使用CPU训练，速度较慢")

GPU训练优化技巧:
- 使用 fp16 混合精度训练（自动启用）
- 增加 batch_size 到显存允许的最大值
- 使用 gradient_accumulation_steps 模拟更大批次
```

#### 2. 内存优化

```python
内存优化配置:

config = {
    'per_device_train_batch_size': 8,
    'gradient_accumulation_steps': 2,
    'dataloader_num_workers': 0,
    'fp16': True
}

说明:
- gradient_accumulation_steps: 累积梯度，模拟更大批次
- dataloader_num_workers: 设为0减少内存占用
- fp16: 使用半精度浮点数，减少显存占用
```

#### 3. 训练监控

```python
训练监控示例:

def progress_callback(current_step, total_steps, loss):
    progress = current_step / total_steps * 100
    print(f"\r训练进度: {progress:.1f}%, 当前损失: {loss:.4f}", end="")

def finished_callback(success, message):
    if success:
        print(f"\n训练成功: {message}")
    else:
        print(f"\n训练失败: {message}")

finetuner.train(
    dataset=dataset,
    output_dir=output_dir,
    progress_callback=progress_callback,
    finished_callback=finished_callback
)
```

---

## 常见问题解答

### Q1: 训练时出现CUDA内存不足错误怎么办？

**A:** 尝试以下解决方案：

1. 减小 `batch_size`（如从16改为8或4）
2. 减小 `max_length`（如从512改为256）
3. 启用 `gradient_accumulation_steps`
4. 使用CPU训练（速度较慢但不会出现内存问题）

```python
config = {
    'batch_size': 4,
    'max_length': 256,
    'gradient_accumulation_steps': 4
}
```

### Q2: 训练损失不下降怎么办？

**A:** 可能的原因和解决方案：

| 原因 | 解决方案 |
|------|----------|
| 学习率过大 | 降低学习率到1e-5或更小 |
| 学习率过小 | 提高学习率到5e-5 |
| 数据问题 | 检查数据标签是否正确 |
| 模型问题 | 尝试不同的预训练模型 |

### Q3: 如何选择训练模式？

**A:** 选择指南：

```
训练模式选择决策树:

开始
  │
  ├─ 是否有GPU？
  │   ├─ 是 → 数据量 > 100？
  │   │        ├─ 是 → 使用BERT微调训练
  │   │        └─ 否 → 使用分类器训练
  │   └─ 否 → 使用分类器训练
  │
  └─ 是否已有训练好的模型？
      ├─ 是 → 新数据量 > 10？
      │        ├─ 是 → 使用增量训练
      │        └─ 否 → 积累更多数据
      └─ 否 → 从头开始训练
```

### Q4: 增量训练后模型效果变差怎么办？

**A:** 可能的原因：

1. **灾难性遗忘**: 增量训练导致模型忘记旧知识
   - 解决方案：降低学习率，增加旧数据比例

2. **数据分布变化**: 新数据分布与旧数据差异大
   - 解决方案：重新完整训练

3. **过拟合**: 新数据量太少
   - 解决方案：积累更多数据，使用数据增强

### Q5: 如何评估模型效果？

**A:** 使用以下指标：

```python
metrics = finetuner.evaluate(test_dataset)

print(f"准确率 (Accuracy): {metrics['eval_accuracy']:.4f}")
print(f"F1分数: {metrics['eval_f1']:.4f}")
print(f"精确率 (Precision): {metrics['eval_precision']:.4f}")
print(f"召回率 (Recall): {metrics['eval_recall']:.4f}")

指标说明:
- 准确率: 整体预测正确的比例
- F1分数: 精确率和召回率的调和平均
- 精确率: 预测为正的样本中实际为正的比例
- 召回率: 实际为正的样本中被预测为正的比例
```

### Q6: 训练需要多长时间？

**A:** 预估时间：

| 数据量 | GPU (RTX 3060) | CPU (i7) |
|--------|----------------|----------|
| 50样本 | 2-5分钟 | 10-30分钟 |
| 200样本 | 5-15分钟 | 30-60分钟 |
| 500样本 | 15-30分钟 | 1-3小时 |
| 1000样本 | 30-60分钟 | 3-6小时 |

### Q7: 如何处理类别不平衡？

**A:** 解决方案：

```python
类别不平衡处理方法:

1. 数据层面:
   - 过采样少数类
   - 欠采样多数类
   - 使用数据增强

2. 算法层面:
   - 设置类别权重
   - 使用F1分数作为优化目标

3. 评估层面:
   - 使用加权平均指标
   - 关注少数类的召回率
```

### Q8: 模型保存在哪里？

**A:** 模型保存路径：

```
默认保存路径结构:

trained_models/
├── grounded_theory_latest/
│   ├── pytorch_model.bin      # 模型权重
│   ├── config.json            # 模型配置
│   ├── tokenizer_config.json  # 分词器配置
│   ├── vocab.txt              # 词汇表
│   └── training_config.json   # 训练配置
├── training_history.json      # 训练历史
└── best_params.json           # 最优参数
```

---

## 附录

### A. 配置文件示例

```json
{
    "learning_rate": 2e-5,
    "num_train_epochs": 3,
    "batch_size": 16,
    "warmup_ratio": 0.1,
    "weight_decay": 0.01,
    "early_stopping_patience": 3,
    "max_grad_norm": 1.0,
    "dropout_rate": 0.1,
    "max_length": 512
}
```

### B. 错误代码参考

| 错误代码 | 说明 | 解决方案 |
|----------|------|----------|
| E001 | GPU显存不足 | 减小batch_size或max_length |
| E002 | 数据格式错误 | 检查数据格式是否符合要求 |
| E003 | 模型加载失败 | 检查模型路径是否正确 |
| E004 | 训练数据不足 | 确保至少有5个训练样本 |
| E005 | 标签数量不匹配 | 检查标签映射是否正确 |

### C. 相关文档链接

- [BERT模型介绍](https://huggingface.co/docs/transformers/model_doc/bert)
- [Transformers库文档](https://huggingface.co/docs/transformers/)
- [Optuna优化框架](https://optuna.readthedocs.io/)

---

*文档版本: 1.0.0*
*最后更新: 2024年*
