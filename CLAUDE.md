# zthree2 项目说明

## 项目概述
zthree2 是基于 PyQt5 的扎根理论（Grounded Theory）三级编码桌面应用，用于社会科学质性研究。

## Python 环境
- **Python 解释器：** `D:\anaconda3\envs\zthree5\python.exe`（conda 环境 zthree5）
- 启动应用：`D:\anaconda3\envs\zthree5\python.exe app_launcher.py`
- 运行训练：`D:\anaconda3\envs\zthree5\python.exe train_with_v11.py`

## 关键文件
| 文件 | 用途 |
|------|------|
| `enhanced_coding_generator.py` | 自动编码生成器（一阶编码核心） |
| `train_abstract_reranker.py` | 一阶抽象重排序模型训练 |
| `train_with_v11.py` | 使用 v11 标准答案训练 |
| `bert_dataset.py` | 训练数据集构建 |
| `bert_finetuner.py` | BERT 微调训练器 |
| `config.py` | 全局配置 |
| `model_manager.py` | 模型管理 |

## 编码质量标准（重要）
一阶编码必须：
1. **语义完整** — 不能截断或残缺
2. **书面化** — 正式、简洁，不能口语化
3. **不能简单删词** — 复杂句子应缩写而非删除关键信息

## 模型
- `local_models/custom_bert_4layer/` — 一阶候选评分 BERT（174MB）
- `local_models/bge-small-zh-v1.5/` — 语义嵌入模型（275MB）
- `trained_models/abstract_reranker_latest/` — 最新训练的抽象重排序模型
