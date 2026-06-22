# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述
zthree2 是基于 PyQt5 的扎根理论（Grounded Theory）多级编码桌面应用，用于社会科学质性研究。支持 1-6 阶编码、自动编码、手动编码、编码库管理、标准答案管理等功能。

## Python 环境
- **解释器：** `D:\anaconda3\envs\zthree5\python.exe`（conda 环境 zthree5）
- 启动应用：`D:\anaconda3\envs\zthree5\python.exe app_launcher.py`
- 运行训练：`D:\anaconda3\envs\zthree5\python.exe train_with_v11.py`
- 打包：`PyInstaller zthree2_simple.spec`

## 编码管线架构

数据流：原始文本 → `data_processor.py`（分句/清洗） → `enhanced_coding_generator.py`（自动编码核心） → `grounded_theory_coder.py`（三级结构组装/去重） → 编码树展示

### 核心模块
| 文件 | 用途 |
|------|------|
| `enhanced_coding_generator.py` | **自动编码生成器**，4500+ 行核心模块。一阶候选生成、语义匹配、RAG 检索、锚点接地评分 |
| `grounded_theory_coder.py` | 三级编码结构构建，去重，一阶编码质量检查（代词过滤、口语化检测、词性校验） |
| `manual_coding_dialog.py` | 手动编码对话框，支持树形编码编辑、多阶编码、Ctrl+Z 撤回、Ctrl+S 保存 |
| `main_window.py` | 主窗口，UI 布局、菜单、右键操作、自动编码触发 |
| `coding_library_manager.py` | 编码库（标准编码体系）的加载与查询 |
| `standard_answer_manager.py` | 标准答案版本管理、合并、增量保存 |
| `data_processor.py` | 文本导入、分句、清洗、编号、表格导出 |
| `model_manager.py` | BERT + sentence-transformer 模型加载、预测、抽象重排序 |
| `grounding_checker.py` | 编码接地检查：关键词保留、主语一致性、语义相似度、漂移审计 |
| `auto_code_merger.py` | **一阶编码自动合并器**，四层门控合并表达同一概念的重复一阶编码 |
| `config.py` | **全局配置**，所有阈值和开关的集中定义点 |
| `path_manager.py` | 统一路径管理，兼容开发模式和 PyInstaller 打包模式 |

### 支持模块
| 文件 | 用途 |
|------|------|
| `coding_decision_policy.py` | 编码决策策略（二阶/三阶阈值自适应调整） |
| `coding_pipeline_adapter.py` | 编码管线适配层 |
| `enhanced_word_exporter.py` | Word 文档导出（含书签超链接、多阶编码表格） |
| `knn_abstract_generator.py` | KNN 抽象编码生成 |
| `first_level_eval.py` | 一阶编码评估 |
| `build_anchor_index.py` / `build_anchor_hierarchy.py` | 锚点索引/层级构建 |

## 自动编码完整流程（详细）

### 触发链路

```
用户点击菜单 "编码" → "自动编码"
  → QAction.triggered → main_window.py:2140 generate_codes_auto()
```

### `generate_codes_auto()` 7 步编排

1. **文本编号** — 对所有导入文件运行 `numbering_manager.number_text()`，生成 `[1]`/`[2]` 等句子编号标记，用于双向链接（编码 ↔ 原文）
2. **数据处理** — `data_processor.process_multiple_files()` 将原始文本解析为统一的 `file_sentence_mapping` 结构
3. **编码生成** — `coding_generator.generate_grounded_theory_codes_multi_files()` 分发到两条路径之一：
   - **训练模型路径**：如果 UI 下拉框选了"训练模型编码"→ `generate_codes_with_trained_model()` 用 `model_manager.predict_categories()` 直接预测三层编码
   - **规则路径（默认）**：`generate_codes_with_rules()` 执行完整的多阶段管线（见下文）
4. **后处理：一阶自动合并** — 如果 `ENABLE_AUTO_MERGE=True`，`AutoCodeMerger.merge()` 基于四层语义门控合并表达同一概念的重复一阶编码
5. **结构构建** — `grounded_coder.build_coding_structure(raw_codes)` 组装编码树（质量过滤 + 编号 + 层级嵌套）
6. **基于树的验证** — `validate_and_filter_codes_by_tree()` 对照 `QTreeWidget` 状态二次验证
7. **缓存与 UI 刷新** — `save_auto_coding_to_cache()` 渲染带 `[A01]` 标记的文本 → `on_file_selected()` 刷新显示

### 规则路径管线阶段（`generate_codes_with_rules()`）

**Phase 0 — 批量前处理（`generate_first_level_codes` 内部）：**
- 所有句子通过 `_normalize_sentence_for_coding()` 一次性规范化（剥离说话人标签等）
- `concept_anchor_index.encode_batch()` 批量计算句子嵌入（GPU 加速）
- `concept_anchor_index.search_embeddings()` 批量检索 top-50 锚点候选
- KNN 训练索引同步批量检索

**Phase 0.5 — T5 批量补全（条件触发）：**
- 触发条件：FAISS top-3 锚点平均分 < 0.60
- 加载 `chinese_t5_pegasus_base` + LoRA 为弱匹配句子生成编码（beam search, num_beams=3, max 16 tokens）
- 生成编码标记为 `anchor_source='t5_generated'`

**Phase 1 — 逐句处理 `build_first_level_candidate_trace()`：**
- 概念锚点检索 → 若 max anchor_score ≥ 0.35 则跳过 n-gram 抽取，直接使用锚点编码
- 原型匹配 `_find_first_level_prototype_hits()` 匹配领域特化表达式
- N-gram 抽取（回退方案）：名词短语合并、从句分割、4-6 字符 n-gram
- **保守评分 `_conservative_first_level_rank_score()`**（混合评分，优先级：概念锚点 > 抽取式）：
  - FAISS 锚点候选：`4.0 + anchor_score * 13.0`
  - T5 生成锚点：`4.0 + anchor_score * 8.0`（权重较低，8.0 vs 13.0）
  - 抽取式候选：`base * 0.35 + rerank_score * 0.65 + concept_sim * 1.5`
  - 长度偏好：4-12 字符 +1.5 奖励，>30 字符 -6.0 惩罚
  - 锚点 IDF 惩罚：本批次过度使用的锚点被降权（防坍缩）
  - 极性检查违规 → 0.40x 惩罚
- 全局批量重排序 `_apply_global_batch_rerank()` 第 2 轮排序

**Phase 2 — 二阶 & 三阶层级构建：**
- **首选路径**：`generate_second_level_from_anchors()` / `generate_third_level_from_anchors()` 使用 `data/anchor_hierarchy.json` 的锚点层级映射
- **语义回退**：concept_anchor_v6 FAISS 最近邻嵌入搜索（相似度 > 0.65）
- **非锚点回退**：RAG 匹配 → 关键词匹配
- 二阶压缩：>20 个类别时 `SemanticCompressor.compress_second_level()` 合并相似类别

**Phase 3 — 后编码质量门控（按序执行）：**
1. `_validate_anchor_codes()` — 仅诊断日志，计算 grounding_score 和 drift_audit（不修改编码）
2. `_gate_extractive_codes()` — 对非锚点编码执行接地门槛检查：
   - 批量计算（句子, 编码）接地分数
   - 接地 < 0.45 → `_deep_extraction_fallback()` 尝试 3 种策略重抽取
   - 回退仍 < 0.45 → 编码被**删除**
   - 漂移审计：主题漂移、极性漂移、关键词丢失、语义发散
   - Zeta 分数（语义跳转距离 vs 全局分布），zeta > 2.5 → 升级为严重漂移
3. `_apply_parsimony_check()` — 批量编码所有一阶编码文本，成对余弦相似度 > 0.95 的编码按并查集分组，每组保留接地分数最高者
4. `_check_consistency()` — 仅监控，MMD 检测分布不稳定性

**Phase 4 — 对比验证：** 非破坏性，仅记录日志

**Phase 5 — 缓存清理：** 清除缓存、释放 grounding_checker 模型、`torch.cuda.empty_cache()`

### AutoCodeMerger 四层门控

在编码生成后、结构构建前执行。判定两个一阶编码是否表达同一概念：

| 层 | 门控 | 阈值（config.py） |
|----|------|-------------------|
| 1 | 编码 content ↔ content bge 相似度 | `AUTO_MERGE_BGE_CONCEPT_MIN = 0.75` |
| 2 | 句子 ↔ 句子 bge 相似度 | `AUTO_MERGE_BGE_SENT_MIN = 0.85` |
| 3 | 句子 ↔ 编码 content concept_anchor_v6 概念相似度 | `AUTO_MERGE_CONCEPT_SIM_MIN = 0.60` |
| 4 | 句子间 jieba 关键词重叠比例 | `AUTO_MERGE_KEYWORD_OVERLAP_MIN = 0.30` |

总开关：`ENABLE_AUTO_MERGE = True`

## 关键配置阈值（`config.py`）

一阶编码质量与生成相关的重要配置：
- `FIRST_LEVEL_CODE_MAX_LENGTH = 36` — 一阶编码最大字数
- `ENABLE_RAG_CODING = True` — RAG 自动编码总开关，`False` 时回退到基于关键词的编码库匹配
- `ENABLE_ABSTRACT_RERANKER = True` — 一阶抽象重排序开关
- `FIRST_LEVEL_CODING_BACKEND = "bert"` — 一阶编码后端："bert"（BERT 管线，默认）或 "llm"（qwen2.5-0.5b GGUF）
- `FIRST_LEVEL_RECALL_ENHANCED = False` — 一阶召回增强（更大 n-gram 跨度）
- `FIRST_LEVEL_FUSED_RANKING = False` — 规则分数与重排序分数融合
- `ENABLE_AUTO_MERGE = True` — 一阶编码自动合并总开关
- `AUTO_MERGE_BGE_CONCEPT_MIN = 0.75` — 自动合并第一层门控（编码↔编码 bge 相似度）
- `AUTO_MERGE_BGE_SENT_MIN = 0.85` — 自动合并第二层门控（句子↔句子 bge 相似度）
- `AUTO_MERGE_CONCEPT_SIM_MIN = 0.60` — 自动合并第三层门控（句子↔编码 concept_anchor 概念相似度）
- `AUTO_MERGE_KEYWORD_OVERLAP_MIN = 0.30` — 自动合并第四层门控（jieba 关键词重叠）
- `RAG_SECOND_LEVEL_THRESHOLD = 0.40` — 一阶→二阶匹配阈值
- `RAG_THIRD_LEVEL_THRESHOLD = 0.40` — 二阶→三阶匹配阈值
- `RAG_CLUSTER_SIMILARITY_THRESHOLD = 0.76` — 聚类相似度阈值

## 一阶编码质量标准（重要）

`grounded_theory_coder.py` 中的 `_check_first_level_quality` 方法会在编码进入最终展示前执行总闸过滤：
1. **语义完整** — 不能截断或残缺
2. **书面化** — 正式、简洁，不能口语化（过滤代词、语气词、口语残留）
3. **不能简单删词** — 复杂句子应缩写而非删除关键信息
4. **必须有关联句子编号** — 无故无关联的编码被过滤
5. **词性模式校验** — 必须有名词/动词/形容词等实质内容

## 模型

### 运行时模型（打包进 exe，2026-06-07 代码追踪确认）

| 模型 | 路径 | 大小 | 用途 | 使用位置 |
|------|------|------|------|----------|
| custom_bert_4layer | `local_models/custom_bert_4layer/` | 175MB | BERT 主模型，mean pooling 编码 | `model_manager.py:64` 始终加载 |
| abstract_reranker_latest | `trained_models/abstract_reranker_latest/` | 1.2GB | BERT 二分类：候选好坏判定，全局批量重排序 | `model_manager.py:320` 始终加载 |
| concept_anchor_v6 | `trained_models/concept_anchor_v6/` | 92MB | 统一语义模型（512-dim CLS pooling）：FAISS 锚点检索 + semantic_matcher + grounding 接地检查 + 层级 fallback | `enhanced_coding_generator.py:3707` / `semantic_matcher.py:33` / `grounding_checker.py:69` |

> **注意：** concept_anchor_v7 已训练完成（准确率 86.2%，见训练详解），但运行时当前使用 v6。切换需在 `enhanced_coding_generator.py` 中更新加载路径。

### 已废弃/不打包的模型

| 模型 | 原因 |
|------|------|
| bge-small-zh-v1.5 | 被 concept_anchor_v6 统一替代（同架构 512-dim，v6 是微调版） |
| sentence-transformer (482MB) | 死代码 — model_manager 加载后从未被查询 |
| chinese_t5_pegasus_base (1.1GB) | 条件触发（FAISS 弱匹配时），不打包 |
| bert-base-chinese (391MB) | 仅 model_builder.py 构建用，不打包 |
| bert_finetuned_latest (2.7GB) | 未使用 |
| t5_abstract_coding* (2.2GB) | T5 训练产物，不打包 |
| concept_anchor_v[1-5,7] | 仅 v6 被使用 |
| t5_lora_coding (9.6MB) | 未使用 |

### 训练样本集

一阶编码训练数据共有 **4类来源**，按时间顺序：

| # | 数据源 | 路径 | 条数 | 格式 |
|---|--------|------|------|------|
| 1 | v11标准答案 | `standard_answers/v11_20260428_164754.json` | 3167 | `{original_content, target_abstract, target_second_category, target_third_category}` |
| 2 | LLM DeepSeek锚点 | `data/llm_anchors_raw.json` | 3283 | `{code, original, file}` |
| 3 | 概念锚点对v4 | `data/train_anchor_pairs_v4.json` | 12823 | `{sentence, anchor_code}`（数据增强后） |
| 4 | LLM增强锚点对v5 | `data/train_anchor_pairs_v5.json` | 15830 | v4 + 3007 LLM锚点 |
| 5 | v12合并标准答案 | `standard_answers/v12_llm_merged.json` | 6128 | v11(3167) + LLM(2961) 合并 |
| 6 | v12纯LLM标准答案 | `standard_answers/v12_llm_only.json` | 2961 | 仅LLM锚点 |

### 模型训练详解

#### 1. concept_anchor: 对比学习训练句子→锚点语义匹配

```
训练数据: data/train_anchor_pairs_v5.json (15830对)
原始格式: {"sentence": "...", "anchor_code": "..."}
  ↓ InputExample(texts=[sentence, anchor_code])
  ↓ MultipleNegativesRankingLoss (批次内其他锚点作为负样本)
  ↓ 基座: bge-small-zh-v1.5 (275MB, 512维)
  ↓ 输出: concept_anchor_v7 (准确率86.2%, F1 86.3%, AP 94.3%)

训练脚本: train_concept_anchor.py
训练命令: D:\anaconda3\envs\zthree5\python.exe train_concept_anchor.py --data-path data/train_anchor_pairs_v5.json --epochs 5 --batch-size 32 --output trained_models/concept_anchor_v7

管道角色: 核心检索模型
  - Phase 0: 批量编码所有句子，FAISS检索top-50相似锚点
  - 锚点候选注入候选池参与保守评分竞争
  - 也被grounding_checker用于接地评分(grounding_score)
```

**训练机制**: 同一句子对应的锚点编码为正样本，批次内其他句子的锚点为负样本。模型学习将句子嵌入和对应锚点嵌入拉近，与其他锚点推开。

#### 2. abstract_reranker: BERT二分类判定候选质量

```
训练数据: standard_answers/v12_llm_merged.json (6128条)
原始格式: {original_content, target_abstract}
  ↓ _build_micro_span_candidates(): 按标点切分句子生成候选片段
  ↓ _focus_score(): 正样本=与target_abstract最匹配的候选片段(label=1)
  ↓ 负样本=随机其他候选片段(label=0, 每正样本采样4个)
  ↓ TextPairBinaryDataset: (text_a=原句, text_b=候选片段, label)
  ↓ 基座: bert-base-chinese
  ↓ AutoModelForSequenceClassification(num_labels=2)
  ↓ 输出: trained_models/abstract_reranker_latest/ (准确率82.1%, F1 80.5%)

训练脚本: train_abstract_reranker.py (底层: bert_finetuner.py + bert_dataset.py)
训练命令: D:\anaconda3\envs\zthree5\python.exe train_abstract_reranker.py --train-csv data/v12_reranker_train.csv

管道角色: 全局批量重排序 + 质量门控
  - Phase 2(_apply_global_batch_rerank): 对所有(句子,候选)对打分，设置rerank_score
  - 保守评分(_conservative_first_level_rank_score): 抽取式候选利用rerank_score计算得分
  - 质量门控: rerank_score < 1.5(sim<0.15)→0.40x, <2.5→0.65x, <3.5→0.85x
```

**训练机制**: 将标准答案中的一阶编码作为"正样本"，通过文本片段匹配找到原文中与target_abstract最接近的片段。BERT学习区分"好的编码候选"(贴近标准答案)和"差的编码候选"(随机文本片段)。

#### 3. T5 LoRA: 参数高效微调生成锚点

```
训练数据: standard_answers/v12_llm_only.json (2961条纯LLM锚点)
原始格式: {original_content, target_abstract}
  ↓ CombinedCodingDataset: (sentence, abstract_code)对
  ↓ 基座: chinese_t5_pegasus_base (275M参数)
  ↓ apply_lora_to_t5(): 在所有SelfAttention的q,v投影上注入LoRA(r=8,alpha=16)
  ↓ 仅训练~3M参数(LoRA A/B矩阵), 冻结其余272M参数
  ↓ 输出: trained_models/t5_lora_coding/checkpoint.pt (val_loss=5.80, 15 epoch无过拟合)

训练脚本: train_t5_lora.py
训练命令: D:\anaconda3\envs\zthree5\python.exe train_t5_lora.py --v11-path standard_answers/v12_llm_only.json --epochs 15 --batch-size 8

管道角色: Phase 0.5 弱锚点生成(补充FAISS检索不足时)
  - 触发条件: FAISS top3平均分 < 0.60
  - 生成锚点标记为 anchor_source='t5_generated'
  - 保守评分乘数 8.0(低于FAISS library的13.0，跳过接地门)
```

**训练机制**: LoRA(Low-Rank Adaptation)在冻结的预训练权重上注入可训练的秩分解矩阵(A和B)。仅训练~1%参数，通过CrossEntropyLoss学习从句子生成对应的锚点编码文本。比全量微调抗过拟合(15 epoch val_loss持续下降)，显存仅需~1GB(全量微调需4GB+且epoch 1后过拟合)。

#### 4. 训练数据流全景

```
DeepSeek API 批处理
  ↓
llm_anchors_raw.json (3283 句子→锚点对)
  ├→ data/train_anchor_pairs_v5.json (+3007对) → concept_anchor_v7 (对比学习)
  ├→ standard_answers/v12_llm_merged.json (+2961条) → abstract_reranker (BERT二分类)
  └→ standard_answers/v12_llm_only.json (2961条) → t5_lora_coding (LoRA seq2seq)

v11标准答案 (3167条人工标注)
  ├→ data/train_anchor_pairs_v4.json (12823对, 数据增强) → concept_anchor_v6
  └→ standard_answers/v11_*.json → abstract_reranker (v11版本, 准确率83.3%)

所有模型共享同一个概念库: cache/anchor_index/concepts.json (4423个锚点概念)
```

### 模型在自动编码管道中的位置

```
Phase 0: concept_anchor_v6 → 批量编码句子（CLS pooling, GPU），FAISS检索锚点
Phase 0.5: chinese_t5_pegasus_base（条件触发，未打包）
Phase 1: concept_anchor_v6 → 计算candidate→sentence的concept_sim
Phase 2: abstract_reranker_latest → 全局批量重排序候选（BERT 二分类）
Phase 3: grounding_checker(concept_anchor_v6) → 接地门质量检查
二阶/三阶: semantic_matcher(concept_anchor_v6) + anchor_hierarchy.json
保守评分: concept_anchor + abstract_reranker 联合打分
```

## 多阶编码结构（1-6阶）

编码支持最多 6 阶层级。编码树使用 `QTreeWidget` 展示，数据以嵌套 `{"text": ..., "data": {"level": N}, "children": [...]}` 结构存储。高阶编码（4/5/6阶）通过 `higher_level_data` 参数在各模块间传递，在 Word/表格导出时以额外列呈现。

## 注意事项
- 项目使用 `PathManager` 处理所有文件路径，避免直接使用 `os.path.join` 或相对路径
- 远程仓库 `git@github.com:komorebi-Lee/Transformer.git`，本地有大型模型文件（`local_models/`、`trained_models/`）在 `.gitignore` 之外，需手动管理
- 存在大量 `_cleaned.py`、`_fixed.py`、`_recovered.py`、`_skeleton.py`、`_v2.py` 后缀的派生文件，它们是原始文件的变体/修复版本，编辑前需确认目标文件是正确的版本
- `.gitignore` 仅包含 `.env`，大文件/模型文件未被排除
- 一阶编码质量标准详见 `FIRST_LEVEL_CODING_STANDARD.md`（五条标准：语义完整、重点提取、书面化表达、概念化、关联句子）

## 测试
- 测试文件分布在项目根目录（`test_*.py`）和 `tests/` 子目录
- 运行单个测试：`D:\anaconda3\envs\zthree5\python.exe test_first_level_coding.py`
- 关键测试文件：`tests/test_first_level_candidate_eval.py`（一阶候选评估）、`tests/test_llm_first_level_coder.py`（LLM一阶编码）、`tests/test_speaker_continuation.py`（说话人识别）、`test_full_pipeline.py`（全管线集成测试）

## 其他脚本
| 脚本 | 用途 |
|------|------|
| `scripts/deepseek_client.py` | DeepSeek API 客户端，LLM 调用基础模块 |
| `scripts/llm_anchor_coding.py` | LLM 锚点编码生成 |
| `scripts/import_llm_anchors.py` | 审查后导入 LLM 锚点 |
| `scripts/llm_l2l3_coding.py` | LLM 二阶/三阶编码生成 |
| `scripts/merge_l2l3_coding.py` | 合并 L2+L3 编码结果 |
| `scripts/import_l2l3.py` | 导入 L2+L3 到编码库 |
| `scripts/compare_coding_quality.py` | 编码质量对比（holdout 测试集） |
| `scripts/export_llm_gguf.py` | GGUF 导出（LoRA 合并 + Q4_K_M 量化） |
| `scripts/prepare_llm_sft_data.py` | LLM SFT 训练数据准备 |
| `scripts/train_llm_first_level.py` | LLM 一阶编码训练 |

## LLM 一阶编码训练数据（2026-06）

### 数据管线总览

```
DeepSeek API（数据蒸馏）
  ├─ v12_llm_only.json (2961条) — 医疗/生物科技访谈→一阶编码
  ├─ llm_anchors_mgmt_world.json (15132条) — 管理世界论文→Anchor
  │     ↓ 质量过滤 + 虚拟访谈生成 → 保留2193条（4%）
  ├─ 清洗后合并.csv (2115条) — 人工标注，保留1923条
  └─ llm_anchors_taoxichuan.json (3373条) — 陶溪川/景漂访谈→一阶编码 ← 最新
        ↓ 质量过滤 → 保留3191条（95%）

当前训练集: v12(2961) + CSV(1923) + VI过滤(2193) + 陶溪川(3191) = 10180条
  train=8144, val=2036
```

### 训练数据源明细

| 数据源 | 路径 | 原始条数 | 一阶合格率 | 过滤后 | 说明 |
|--------|------|----------|-----------|--------|------|
| v12 DeepSeek访谈编码 | `standard_answers/v12_llm_only.json` | 2,961 | 93% | 2,961 | 医疗/生物科技行业访谈 |
| CSV人工标注 | `D:\4\清洗后合并.csv` | 2,115 | 91% | 1,923 | 一阶概念+合并后句子 |
| 虚拟访谈(VI) | `data/virtual_interviews.json` | 55,257 | 4% | 2,193 | 管理世界→Anchor→虚拟口述，严格过滤 |
| **陶溪川DeepSeek编码** | `data/llm_anchors_taoxichuan.json` | 3,373 | **95%** | 3,191 | 陶溪川/景漂/手艺人/游客访谈，使用llm_anchor_coding.py同款prompt |
| **当前训练集** | `data/train_llm_first_level.json` | | | **10,180** | train=8144, val=2036 |

### 陶溪川编码脚本

`scripts/llm_anchor_coding_v2.py` — 复用 llm_anchor_coding.py 的 prompt（93%→95%合格率）
- 输入：`D:\c盘\新文本\润色后文件\` (82个docx)
- 支持 5+ 种文件格式（内联说话人/时间戳分离/无标签交替问答/发言者编号/讲话人编号）
- 自动识别受访者（问句少的=受访者），跳过采访者问句
- prompt核心："最小语义跳跃"、"贴近原文行为/事件/态度"、"2-10字"

### 关键发现：prompt决定一阶编码质量

| | 管理世界 Anchor prompt | 陶溪川 prompt | v12 prompt |
|------|------|------|------|
| 关键词 | "行为逻辑/决策逻辑/约束条件" | "最小语义跳跃/贴近行为事件/2-10字" | 同陶溪川 |
| 合格率 | 20% | **95%** | 93% |
| 示例 | "通过专利布局阻碍竞争企业获取核心技术"(30字) | "比较摊位产品"(6字) | "做PPT进行市场分析"(8字) |

**结论**："行为逻辑/决策逻辑"等抽象归类导致 LLM 输出二阶编码；"最小语义跳跃"约束 LLM 贴近原文。

### 当前模型状态与方向

- **采用方案：Qwen2.5-0.5B-Instruct + LoRA + SFT**（2026-06 确认）。1.5B 基座输出偏好太强、LoRA 压不住（偏长/带学术腔），改用 0.5B（输出天然短）后质量可用。
- **后处理是质量关键**：原始 LLM 输出在长访谈句/元数据行上会跑飞（复读、幻觉、空格分隔多子句）。`llm_first_level_coder._parse_response` 的清洗链把实测脏输出大幅压低（含斜杠 3→0，含分号 1→0）。其中**取首个空白前片段**这一刀贡献最大。
- **已完成**：0.5B 训练（3 epoch，loss≈0.96）→ 合并 → GGUF → **真 Q4_K_M 量化（379MB）**→ 接入 `enhanced_coding_generator`，路径解析/加载/推理 smoke 测通过。`FIRST_LEVEL_CODING_BACKEND` 仍默认 `"bert"`，切 `"llm"` 即启用。
- **可选后续**：DPO 对比优化进一步压缩长度；对超长输入句先截断再编码。

### 训练参数

```
基座: Qwen2.5-0.5B-Instruct (FP16, ~1GB)  路径见 scripts/train_llm_first_level.py MODEL_NAME
方法: LoRA (r=16, alpha=32) + SFT
Epochs: 3
Batch: 2 × grad_accum 4 = effective 8
LR: 2e-4, cosine schedule
显存: ~3-4 GB / 8GB
训练时间: ~50 min (10K样本)
产出: ~35MB LoRA adapter → merge FP16 → GGUF → Q4_K_M (379MB)
System prompt: "你是扎根理论编码助手。任务：根据访谈文本生成高质量一阶编码（Level 1），严格贴近原文。规则：1.保留主体、动作、对象 2.禁止心理推断、解释性词汇、抽象概念和理论名词 3.优先使用原文词汇。输出：只输出一条一阶编码。不超过10字。不输出分号。不输出斜杠。不输出多个编码。不输出解释。"
```

### 推理集成

- `llm_first_level_coder.py`: `LLMFirstLevelCoder` 类，llama-cpp-python 加载 GGUF。**Windows 注意**：CUDA 构建的 `ggml-cuda.dll` 依赖 torch 分发的 CUDA 运行时，必须先 `import torch` 再 `from llama_cpp import Llama`，否则 DLL 加载失败。
- 生成参数：`temperature=0.1`, `top_p=0.9`, `max_tokens=48`, **`repeat_penalty=1.3`**（抑制小模型退化式复读）。
- 后处理 `_parse_response`：取首行 → 取首个空白前片段 → 复读折叠(`_collapse_repetition`) → 去句尾标点与冗余解释尾巴(`_strip_trailing_noise`)。
- `config.py`: `FIRST_LEVEL_CODING_BACKEND = "bert"` (默认) | `"llm"`；`LLM_FIRST_LEVEL_MODEL_NAME = "qwen2.5-0.5b-coding-Q4_K_M.gguf"`；`LLM_MAX_TOKENS=48`；`LLM_REPEAT_PENALTY=1.3`。
- `enhanced_coding_generator.py`: `_first_level_code_via_llm()` 分支，`_init_llm_coder()` 按 config 加载。
- 量化：pip 版 llama-cpp-python 不带 quantize 二进制，用其 `llama_model_quantize` Python 绑定量化（见 `scripts/quantize_gguf_q4km.py` 与 `scripts/export_llm_gguf.py:quantize_gguf`）。

### 已保存模型版本

| 版本 | 路径 | 训练数据 | 状态 |
|------|------|----------|------|
| v1 (含全部VI) | `lora_adapter_final` (已覆盖) | 60K (含不合格VI) | 废弃 — 输出管理学术语 |
| v2 (v12+CSV) | `lora_v12_csv_backup/` | 5K | 保留 — 可回退，贴地但领域不匹配 |
| v3 1.5B (v12+CSV+VI过滤) | (已覆盖) | 7K | 废弃 — 1.5B 输出偏长 |
| v4 0.5B (含陶溪川) | `lora_adapter_final/` (当前) | 10180 | **当前** — GGUF: `local_models/llm_first_level_coder/qwen2.5-0.5b-coding-Q4_K_M.gguf` (379MB) |

## 说话人身份标签识别与受访者语句抽取

在访谈文本进入一阶编码前，先通过身份标签识别系统过滤出**非采访者**语句（受访者+同伴+顾客等），剔除采访者问句。身份标签是预处理过滤器，**不作为一阶编码内容本身**。

支持多人对话场景（2-6人），先扫描文件统计说话人数目，通过采样式说话人画像确定每个说话人的文件级角色。

**设计文档：** `docs/superpowers/specs/2026-06-06-speaker-profile-sampling-design.md`

### 核心模块
| 文件 | 用途 |
|------|------|
| `speaker_role_extractor.py` | **身份标签识别核心**。`SpeakerRoleExtractor` 类：规则匹配（采访者/受访者/A:/B:模式）、智能分段（`_segment_by_ab_labels`/`_segment_by_speaker`/`_smart_segment_qa_mixed`）、采样式说话人画像（`_build_speaker_profiles`：随机抽取3个相邻对话块聚合打分，确定文件级角色）、多策略角色判定（显式标注→画像映射→内容评分→上下文增强→QA分类器→启发式回退） |
| `interview_coding_pipeline.py` | 批量访谈一阶编码流水线：提取受访者语句 → 逐句一阶编码 → 输出 CSV/JSON trace |
| `optimized_coding_pipeline.py` | 6阶段优化流水线。身份抽取在阶段2（规则抽取）和阶段3（模型辅助判断） |
| `qa_classifier_integration.py` | `SpeakerRoleExtractorV2`：用 QA 分类模型替代复杂规则进行身份判定 |
| `enhanced_docx_reader.py` | 读取 docx 时检测时间戳+说话人标签格式，统一转化为标准 `speaker_label: content` |
| `scripts/merge_speaker_data.py` | 说话人数据合并脚本 |
| `scripts/unified_speaker_pipeline.py` | 统一说话人流水线脚本 |

### 身份标签处理流程

```
原始文本 → _segment_by_speaker() 分段
           ├─ 策略0: A:/B: 标签 → 角色已知
           ├─ 策略1: 显式标签(受访者:/说话人N:) → 角色已知或待判定
           └─ 策略2: _smart_segment_qa_mixed → 无标签智能分段
         → _build_speaker_profiles() ★ 采样式画像
           ├─ 按speaker_label分组
           ├─ 每组随机抽3个块(每块2-3条连续语句)聚合打分
           └─ 多数投票 → {说话人N: interviewer|non-interviewer}
         → _identify_role() 逐段判定(优先查画像映射表)
         → 过滤：排除 interviewer，保留所有非采访者
         → enhanced_coding_generator._normalize_sentence_for_coding()
            (正则剥离所有说话人标签前缀，共20+种)
         → 清洗后的纯文本进入一阶编码生成
```

- `speaker_role_extractor.py` — `_build_speaker_profiles()`：采样式文件级说话人画像，参数 `PROFILE_SAMPLE_BLOCKS=3`（采样块数）、`PROFILE_BLOCK_SIZE=3`（每块连续条数）、`INTERVIEWER_THRESHOLD=0.5`
- `speaker_role_extractor.py` — `_context_enhance_role()`：上下文增强 fallback，取前后各1条拼接重新打分
- `enhanced_coding_generator.py:1419-1424` — `_normalize_sentence_for_coding()` 中剥离说话人标签的正则，覆盖 20+ 种说话人角色前缀
- 身份元数据（`speaker_label`, `speaker_confidence`, `speaker_method`）存储在编码 trace 中，但不参与编码内容生成
- `grounded_theory_coder.py` 完全不使用身份信息，仅处理清洗后的纯文本

### 支持的身份标签类型
- 访谈双方：`采访者`/`访谈员`/`访员`/`主持人`/`记者` vs `受访者`/`被访者`/`嘉宾`/`专家`
- 编号说话人：`说话人N`/`讲话人N`/`里弄管家N`/`游客N`/`非遗手艺人N`/`管理层N`/`景漂N`/`老师N`/`居民N`/`商户N`/`手艺人N`/`学徒N`/`传承人N`
- 问答格式：`A:`/`B:`/`Q:`/`问:`/`答:`
- 无标注混合文本：通过问号检测+内容评分+QA分类器推断角色
- 时间戳交替格式：按说话交替区分，2人问答

