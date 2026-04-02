# 训练优化指南

## 问题诊断结果

根据系统诊断，您的电脑存在以下问题：

### 🔴 严重问题
1. **内存严重不足**
   - 可用内存仅3.05GB（总内存15.19GB，已使用79.9%）
   - 训练时很容易耗尽内存导致系统崩溃

2. **GPU加速不可用**
   - PyTorch安装的是CPU版本（torch==2.8.0+cpu）
   - 无法使用NVIDIA RTX 4060 GPU加速
   - 所有计算都在CPU上进行，效率低且消耗更多内存

3. **缺少关键依赖**
   - sentence-transformers 未安装

---

## 立即解决方案

### 1. 释放内存
```powershell
# 关闭不必要的程序
# 清理内存
```

### 2. 优化训练参数
在配置文件中设置以下参数：

```python
# config.py 或训练配置文件

# 减小批次大小
BATCH_SIZE = 4  # 原来是16或更大

# 减少训练轮数
EPOCHS = 1  # 原来是3或更多

# 限制训练数据量
MAX_TRAINING_SAMPLES = 500  # 原来是全部数据

# 使用更小的模型
MODEL_NAME = "distilbert-base-uncased"  # 比bert-base-uncased小40%

# 启用梯度累积（模拟大批量训练）
GRADIENT_ACCUMULATION_STEPS = 4

# 使用混合精度训练（减少内存使用）
USE_FP16 = True
```

### 3. 修改代码使用内存监控

```python
from monitor_training import start_monitoring, stop_monitoring, get_memory_status

# 在训练开始前启动监控
start_monitoring(memory_threshold=85, check_interval=5)

try:
    # 你的训练代码
    model.fit(...)
finally:
    # 训练结束后停止监控
    stop_monitoring()
```

---

## 长期解决方案

### 方案1：安装GPU版PyTorch（推荐）

```bash
# 1. 卸载CPU版本
pip uninstall torch torchvision torchaudio

# 2. 安装GPU版本（CUDA 12.1）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 3. 验证安装
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### 方案2：安装缺失的依赖

```bash
pip install sentence-transformers
```

### 方案3：使用数据加载优化

```python
from torch.utils.data import DataLoader

# 使用较小的num_workers
DataLoader(
    dataset,
    batch_size=4,
    num_workers=0,  # 在Windows上设为0避免多进程问题
    pin_memory=False  # 减少内存使用
)
```

### 方案4：使用梯度检查点

```python
from torch.utils.checkpoint import checkpoint

# 在模型定义中启用梯度检查点
model.gradient_checkpointing_enable()
```

---

## 硬件升级建议

如果以上方案仍无法解决问题，建议：

1. **增加内存**
   - 建议至少32GB RAM
   - 您的笔记本可能支持内存升级

2. **使用云服务**
   - Google Colab（免费，有GPU）
   - AWS SageMaker
   - AutoDL（国内GPU云服务器）

---

## 安全训练检查清单

训练前检查：
- [ ] 关闭不必要的程序
- [ ] 检查可用内存 > 4GB
- [ ] 确认batch_size <= 8
- [ ] 启动内存监控

训练中监控：
- [ ] 内存使用率 < 90%
- [ ] 可用内存 > 1GB
- [ ] GPU温度 < 85°C

训练后：
- [ ] 保存模型和日志
- [ ] 检查训练结果
- [ ] 释放资源

---

## 紧急处理

如果训练过程中出现内存不足：

1. **立即按 Ctrl+C** 停止训练
2. **运行清理脚本**：
   ```python
   import gc
   import torch
   gc.collect()
   torch.cuda.empty_cache()  # 如果使用GPU
   ```
3. **重启Python内核** 或 **重启电脑**

---

## 联系支持

如果问题仍然存在，请提供：
1. `diagnostic_report_*.json` 文件
2. `training_monitor.log` 文件
3. 训练时的错误截图
