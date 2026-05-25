"""
模型对比基准测试脚本 v2.0
==========================
四模型对比测试：
  - BERT 对比: bert-base-chinese (12层) vs custom_bert_4layer (4层)
  - Sentence 对比: MiniLM-L6-v2 vs bge-small-zh-v1.5

测试维度：
  1. CSV 标准测试：用已标注的 (编码名, 原文) 对做检索准确率测试
  2. 真实文档测试：用文本样本中的 docx 文件做"同文档检索"测试
     — 对每条句子，看模型能否找到同文档中的其他句子（测试语义聚类能力）

使用方式：
  python benchmark_models.py                          # 默认：CSV + 文档双重测试
  python benchmark_models.py --csv-only               # 仅 CSV 测试
  python benchmark_models.py --docx-only              # 仅文档测试
  python benchmark_models.py --docx-dir "d:/zthree2/文本样本"   # 指定文档目录
  python benchmark_models.py --skip-download          # 跳过新模型下载
"""

import os
import sys
import csv
import re
import time
import glob
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)

# =============================================================================
# 模型配置
# =============================================================================
# --- Sentence Transformer 模型 ---
OLD_SENT_MODEL_NAME = "paraphrase-multilingual-MiniLM-L6-v2"
OLD_SENT_MODEL_LOCAL = "sentence-transformer"

NEW_SENT_MODEL_NAME = "BAAI/bge-small-zh-v1.5"
NEW_SENT_MODEL_LOCAL = "bge-small-zh-v1.5"

# --- BERT 模型 (mean pooling) ---
OLD_BERT_MODEL_NAME = "bert-base-chinese"
OLD_BERT_MODEL_LOCAL = "bert-base-chinese"

NEW_BERT_MODEL_NAME = "custom_bert_4layer"
NEW_BERT_MODEL_LOCAL = "custom_bert_4layer"

LOCAL_MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_models")

# =============================================================================
# 1. CSV 标准测试数据加载
# =============================================================================

def load_csv_data(csv_path: str) -> List[Tuple[str, str]]:
    """从 CSV 加载 (编码名, 原始文本) 对"""
    pairs = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) < 2:
                continue
            code = row[0].strip()
            text = row[1].strip()
            if not code or not text or code == 'nan' or text == 'nan':
                continue
            pairs.append((code, text))
    logger.info(f"从 {csv_path} 加载 {len(pairs)} 条测试数据")
    return pairs


def load_all_csv_data(data_dir: str = None) -> List[Tuple[str, str]]:
    """加载所有 CSV 测试文件并去重"""
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "csv")
    all_pairs = []
    for fname in ["standard_test.csv", "standard_val.csv", "standard_train.csv"]:
        fpath = os.path.join(data_dir, fname)
        if os.path.exists(fpath):
            pairs = load_csv_data(fpath)
            all_pairs.extend(pairs)
            logger.info(f"  {fname}: {len(pairs)} 条")
    seen = set()
    unique_pairs = []
    for code, text in all_pairs:
        if text not in seen:
            seen.add(text)
            unique_pairs.append((code, text))
    logger.info(f"总计加载 {len(unique_pairs)} 条去重 CSV 测试数据")
    return unique_pairs


# =============================================================================
# 2. 真实文档测试数据加载
# =============================================================================

def _split_sentences(text: str, min_len: int = 5) -> List[str]:
    """
    中文句子切分。
    按 。！？!? ；; 和换行切分，但保留有一定长度的句子。
    """
    # 先按常见标点 + 换行切分
    raw_parts = re.split(r'[。！？!?\n；;]+', text)
    sentences = []
    for part in raw_parts:
        part = part.strip()
        # 去掉纯数字/纯标点等噪音
        if len(part) >= min_len:
            sentences.append(part)
    return sentences


def load_docx_sentences(docx_dir: str, max_sentences_per_file: int = 200) -> Dict[str, List[str]]:
    """
    从 docx 文件提取句子，按文档分组。

    Args:
        docx_dir: 文档目录
        max_sentences_per_file: 每个文件最多取多少句（控制总量）

    Returns:
        {filename: [sentence1, sentence2, ...]}
    """
    try:
        from docx import Document
    except ImportError:
        logger.error("python-docx 未安装，请运行: pip install python-docx")
        return {}

    all_files = glob.glob(os.path.join(docx_dir, "*.docx"))
    logger.info(f"在 {docx_dir} 找到 {len(all_files)} 个 docx 文件")

    docs = {}
    for fpath in sorted(all_files):
        fname = os.path.basename(fpath)
        try:
            doc = Document(fpath)
            full_text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
            sentences = _split_sentences(full_text)
            if len(sentences) > max_sentences_per_file:
                # 均匀采样
                step = len(sentences) / max_sentences_per_file
                sentences = [sentences[int(i * step)] for i in range(max_sentences_per_file)]
            if sentences:
                docs[fname] = sentences
        except Exception as e:
            logger.warning(f"读取 {fname} 失败: {e}")

    total_sentences = sum(len(v) for v in docs.values())
    logger.info(f"从 {len(docs)} 个文档中提取了 {total_sentences} 条句子")
    return docs


def evaluate_on_docx(model, docs: Dict[str, List[str]], model_name: str = "", batch_size: int = 64) -> Dict:
    """
    在真实文档上评估模型。

    任务：「同文档检索」— 对每条句子，在看所有文档中，
    模型找到的另一条句子的来源文档是否相同？

    指标：
      - same_doc_top1: Top-1 检索结果是否来自同一文档
      - same_doc_top3: Top-3 中是否有至少一个来自同一文档
      - intra_doc_sim: 同一文档内句子对的平均余弦相似度
      - inter_doc_sim: 不同文档间句子对的平均余弦相似度
      - separation: intra - inter (越高越好)

    Returns:
        评估结果字典
    """
    # 展平所有句子，记录来源文档索引
    all_sentences = []
    doc_ids = []  # 每条句子属于哪个文档
    doc_names = list(docs.keys())

    for doc_idx, (doc_name, sentences) in enumerate(docs.items()):
        for sent in sentences:
            all_sentences.append(sent)
            doc_ids.append(doc_idx)

    n = len(all_sentences)
    if n < 20:
        return {"error": f"句子数不足 ({n})，至少需要 20 条"}

    logger.info(f"[{model_name}] 文档测试: {len(doc_names)} 个文档, {n} 条句子")

    # 编码
    t0 = time.time()
    embeddings = model.encode(all_sentences, batch_size=batch_size,
                              show_progress_bar=True, normalize_embeddings=True)
    encode_time = time.time() - t0
    logger.info(f"[{model_name}] 编码 {n} 条句子耗时 {encode_time:.1f}s, 维度 {embeddings.shape[1]}")

    # 相似度矩阵 [n, n]
    sim_matrix = embeddings @ embeddings.T

    # =========================================================================
    # 1. 同文档检索准确率 (leave-self-out)
    # =========================================================================
    top1_same = 0
    top3_same = 0
    reciprocal_ranks = []

    for i in range(n):
        # 排除自身（相似度设为 -inf）
        sims = sim_matrix[i].copy()
        sims[i] = -float('inf')

        ranked = np.argsort(-sims)

        # Top-1/Top-3 是否来自同一文档
        my_doc = doc_ids[i]
        top1_doc = doc_ids[ranked[0]]
        top3_docs = [doc_ids[ranked[j]] for j in range(min(3, len(ranked)))]

        if top1_doc == my_doc:
            top1_same += 1
        if my_doc in top3_docs:
            top3_same += 1

        # MRR: 第一个同文档的排名
        for rank, idx in enumerate(ranked):
            if doc_ids[idx] == my_doc:
                reciprocal_ranks.append(1.0 / (rank + 1))
                break
        else:
            reciprocal_ranks.append(0.0)

    # =========================================================================
    # 2. 文档内/文档间相似度
    # =========================================================================
    intra_sims = []
    inter_sims = []
    # 只采样避免 O(n^2)
    sample_pairs = min(50000, n * 10)

    for _ in range(sample_pairs):
        i = np.random.randint(0, n)
        j = np.random.randint(0, n)
        if i == j:
            continue
        if doc_ids[i] == doc_ids[j]:
            intra_sims.append(sim_matrix[i, j])
        else:
            inter_sims.append(sim_matrix[i, j])

    avg_intra = float(np.mean(intra_sims)) if intra_sims else 0.0
    avg_inter = float(np.mean(inter_sims)) if inter_sims else 0.0
    separation = avg_intra - avg_inter

    return {
        "model": model_name,
        "num_docs": len(doc_names),
        "num_sentences": n,
        "encode_time_sec": round(encode_time, 1),
        "embedding_dim": embeddings.shape[1],
        "same_doc_top1": round(top1_same / n, 4),
        "same_doc_top3": round(top3_same / n, 4),
        "same_doc_mrr": round(np.mean(reciprocal_ranks), 4),
        "avg_intra_doc_sim": round(avg_intra, 4),
        "avg_inter_doc_sim": round(avg_inter, 4),
        "separation": round(separation, 4),
    }


# =============================================================================
# 模型加载 (Sentence Transformers)
# =============================================================================

def load_sentence_model(model_name: str, local_dir: str = None, use_mirror: bool = True) -> object:
    """
    加载 SentenceTransformer 模型。
    优先本地 → ModelScope → HF 镜像 → HF 官方
    """
    from sentence_transformers import SentenceTransformer

    if local_dir:
        full_path = os.path.join(LOCAL_MODELS_DIR, local_dir)
        if os.path.exists(full_path) and os.path.exists(os.path.join(full_path, "config.json")):
            logger.info(f"从本地加载模型: {full_path}")
            return SentenceTransformer(full_path)

    if local_dir:
        save_path = os.path.join(LOCAL_MODELS_DIR, local_dir)
        os.makedirs(save_path, exist_ok=True)

        # 策略 1：ModelScope
        if use_mirror:
            try:
                from modelscope import snapshot_download
                ms_id = model_name
                logger.info(f"从 ModelScope 下载: {ms_id}")
                downloaded_dir = snapshot_download(ms_id, cache_dir=save_path)
                logger.info(f"ModelScope 下载完成")
                model = SentenceTransformer(downloaded_dir)
                model.save(save_path)
                logger.info(f"模型已保存到 {save_path}")
                return model
            except ImportError:
                logger.warning("modelscope 未安装，尝试 HuggingFace 镜像...")
            except Exception as e:
                logger.warning(f"ModelScope 下载失败: {e}，尝试 HuggingFace 镜像...")

        # 策略 2：HuggingFace 镜像
        if use_mirror:
            hf_mirror = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com")
            logger.info(f"尝试 HF 镜像: {hf_mirror}")
            try:
                os.environ["HF_ENDPOINT"] = hf_mirror
                model = SentenceTransformer(model_name)
                model.save(save_path)
                logger.info(f"HF 镜像下载成功")
                return model
            except Exception as e:
                logger.warning(f"HF 镜像失败: {e}")

        # 策略 3：HuggingFace 官方
        logger.info(f"尝试 HF 官方下载 {model_name}...")
        model = SentenceTransformer(model_name)
        model.save(save_path)
        logger.info(f"已保存到 {save_path}")
        return model
    else:
        logger.info(f"加载模型: {model_name}")
        return SentenceTransformer(model_name)


# =============================================================================
# BERT 模型加载与 Mean Pooling 编码
# =============================================================================

class BERTEncoder:
    """使用 mean pooling 从 HuggingFace BERT 模型获取句子向量"""

    def __init__(self, model_path: str):
        from transformers import AutoModel, AutoTokenizer
        logger.info(f"加载 BERT 模型: {model_path}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModel.from_pretrained(model_path)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        logger.info(f"BERT 模型已加载到 {self.device}")

    def encode(self, sentences: List[str], batch_size: int = 64,
               show_progress_bar: bool = True, normalize_embeddings: bool = True) -> np.ndarray:
        """Mean pooling 编码一组句子"""
        all_embeddings = []
        total = len(sentences)

        iterator = range(0, total, batch_size)
        if show_progress_bar:
            from tqdm import tqdm
            iterator = tqdm(iterator, desc="BERT encoding", total=(total + batch_size - 1) // batch_size)

        for start in iterator:
            batch = sentences[start:start + batch_size]
            encoded = self.tokenizer(
                batch, padding=True, truncation=True, max_length=512, return_tensors="pt"
            )
            encoded = {k: v.to(self.device) for k, v in encoded.items()}

            with torch.no_grad():
                outputs = self.model(**encoded)
                # Mean pooling: average last hidden states, accounting for attention mask
                attention_mask = encoded["attention_mask"]
                token_embeddings = outputs.last_hidden_state  # [B, L, D]
                input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
                sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, dim=1)
                sum_mask = torch.clamp(input_mask_expanded.sum(dim=1), min=1e-9)
                embeddings = sum_embeddings / sum_mask

            embeddings = embeddings.cpu().numpy()
            if normalize_embeddings:
                embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
            all_embeddings.append(embeddings)

        return np.vstack(all_embeddings)


def load_bert_model(local_dir: str) -> BERTEncoder:
    """从本地加载 BERT 模型"""
    full_path = os.path.join(LOCAL_MODELS_DIR, local_dir)
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"BERT 模型不存在: {full_path}")
    return BERTEncoder(full_path)


# =============================================================================
# CSV 评估逻辑
# =============================================================================

def evaluate_csv(model, test_pairs: List[Tuple[str, str]], model_name: str = "", batch_size: int = 64) -> Dict:
    """在 CSV 标注数据上评估检索准确率"""
    codes, texts = zip(*test_pairs)
    codes, texts = list(codes), list(texts)
    n = len(test_pairs)

    device = str(model.device) if hasattr(model, 'device') else "cpu"
    logger.info(f"[{model_name}] CSV 编码，设备: {device}, 样本数: {n}")

    t0 = time.time()
    code_emb = model.encode(codes, batch_size=batch_size, show_progress_bar=True, normalize_embeddings=True)
    text_emb = model.encode(texts, batch_size=batch_size, show_progress_bar=True, normalize_embeddings=True)
    encode_time = time.time() - t0

    # text → code
    t2c = _retrieval_metrics(text_emb, code_emb, n)
    # code → text
    c2t = _retrieval_metrics(code_emb, text_emb, n)

    diag_sim = np.sum(code_emb * text_emb, axis=1)
    shifted = (np.arange(n) + 1) % n
    random_sim = np.sum(code_emb * text_emb[shifted], axis=1)

    return {
        "model": model_name, "num_samples": n,
        "encode_time_sec": round(encode_time, 1),
        "embedding_dim": code_emb.shape[1],
        "avg_correct_sim": round(float(np.mean(diag_sim)), 4),
        "avg_random_sim": round(float(np.mean(random_sim)), 4),
        "separation": round(float(np.mean(diag_sim) - np.mean(random_sim)), 4),
        "text_to_code": t2c, "code_to_text": c2t,
    }


def _retrieval_metrics(queries: np.ndarray, corpus: np.ndarray, n: int) -> Dict:
    sim = queries @ corpus.T
    top1 = top3 = top5 = 0
    rrs = []
    for i in range(n):
        ranked = np.argsort(-sim[i])
        pos = int(np.where(ranked == i)[0][0]) + 1
        if pos <= 1: top1 += 1
        if pos <= 3: top3 += 1
        if pos <= 5: top5 += 1
        rrs.append(1.0 / pos)
    return {
        "top1": round(top1 / n, 4), "top3": round(top3 / n, 4),
        "top5": round(top5 / n, 4), "mrr": round(np.mean(rrs), 4),
    }


# =============================================================================
# 报告输出
# =============================================================================

SEP = "=" * 95


def print_csv_report(results: Dict[str, Dict]):
    """打印四模型 CSV 测试对比报告"""
    models = ["bert_old", "bert_new", "sent_old", "sent_new"]
    labels = ["BERT-12层", "BERT-4层", "MiniLM-L6", "bge-small"]
    valid = [(m, l) for m, l in zip(models, labels) if m in results]

    if len(valid) < 2:
        return

    print(f"\n{SEP}")
    print("                    📊 CSV 标准测试 — 四模型对比")
    print(SEP)

    # 表头
    header = f"\n{'指标':<32}"
    for _, label in valid:
        header += f" {label:>12}"
    header += f" {'最优':>12}"
    print(header)
    print("-" * (32 + 14 * len(valid) + 12))

    # 基础信息
    for key, label in [
        ("num_samples", "样本数"),
        ("encode_time_sec", "编码耗时(秒)"),
        ("embedding_dim", "向量维度"),
    ]:
        row = f"{label:<32}"
        values = [results[m][key] for m, _ in valid]
        for v in values:
            if isinstance(v, float):
                row += f" {v:>12.1f}"
            else:
                row += f" {v:>12}"
        if key == "encode_time_sec":
            best = min(values)
        elif key == "embedding_dim":
            best = min(values)
        else:
            best = values[0]
        row += f" {str(best):>12}"
        print(row)

    # 相似度
    print(f"\n  ── 相似度统计 ──")
    for key, label in [
        ("avg_correct_sim", "正确配对平均相似度"),
        ("avg_random_sim", "随机配对平均相似度"),
        ("separation", "分离度 (越高越好)"),
    ]:
        row = f"  {label:<30}"
        values = [results[m][key] for m, _ in valid]
        for v in values:
            row += f" {v:>12.4f}"
        best_val = max(values) if key in ("avg_correct_sim", "separation") else min(values)
        best_idx = values.index(best_val) if best_val in values else 0
        best_name = valid[best_idx][1] if best_idx < len(valid) else "—"
        row += f" {best_name:>12}"
        print(row)

    # 检索准确率
    for direction, dlabel in [("text_to_code", "原文→编码"), ("code_to_text", "编码→原文")]:
        print(f"\n  ── {dlabel} ──")
        print(f"  {'指标':<10}", end="")
        for _, label in valid:
            print(f" {label:>12}", end="")
        print(f" {'最优':>12}")
        print(f"  {'-'*40}")
        for key, l in [("top1", "Top-1"), ("top3", "Top-3"), ("top5", "Top-5"), ("mrr", "MRR")]:
            row = f"  {l:<10}"
            values = [results[m][direction][key] for m, _ in valid]
            for v in values:
                row += f" {v:>11.2%}"
            best_val = max(values)
            best_idx = values.index(best_val)
            best_name = valid[best_idx][1]
            row += f" {best_name:>12}"
            print(row)


def print_docx_report(results: Dict[str, Dict]):
    """打印四模型文档测试对比报告"""
    models = ["bert_old", "bert_new", "sent_old", "sent_new"]
    labels = ["BERT-12层", "BERT-4层", "MiniLM-L6", "bge-small"]
    valid = [(m, l) for m, l in zip(models, labels) if m in results]

    if len(valid) < 2:
        return

    print(f"\n{SEP}")
    print("                    📄 真实文档测试 — 四模型对比 (同文档检索)")
    print(SEP)

    # 表头
    header = f"\n{'指标':<32}"
    for _, label in valid:
        header += f" {label:>12}"
    header += f" {'最优':>12}"
    print(header)
    print("-" * (32 + 14 * len(valid) + 12))

    # 统计信息
    for key, label in [
        ("num_docs", "文档数"),
        ("num_sentences", "句子总数"),
        ("encode_time_sec", "编码耗时(秒)"),
        ("embedding_dim", "向量维度"),
    ]:
        row = f"{label:<32}"
        values = [results[m][key] for m, _ in valid]
        for v in values:
            row += f" {v:>12}"
        print(row)

    # 同文档检索
    print(f"\n  ── 同文档检索 ──")
    for key, label in [
        ("same_doc_top1", "Top-1 同文档命中"),
        ("same_doc_top3", "Top-3 同文档命中"),
        ("same_doc_mrr", "MRR"),
    ]:
        row = f"  {label:<30}"
        values = [results[m][key] for m, _ in valid]
        for v in values:
            row += f" {v:>11.2%}"
        best_val = max(values)
        best_idx = values.index(best_val)
        best_name = valid[best_idx][1]
        row += f" {best_name:>12}"
        print(row)

    # 文档内/间相似度
    print(f"\n  ── 文档内/间相似度 ──")
    for key, label in [
        ("avg_intra_doc_sim", "文档内平均相似度"),
        ("avg_inter_doc_sim", "文档间平均相似度"),
        ("separation", "分离度 (越高越好)"),
    ]:
        row = f"  {label:<30}"
        values = [results[m][key] for m, _ in valid]
        for v in values:
            row += f" {v:>12.4f}"
        best_val = max(values) if key != "avg_inter_doc_sim" else min(values)
        best_idx = values.index(best_val) if best_val in values else 0
        best_name = valid[best_idx][1] if best_idx < len(valid) else "—"
        row += f" {best_name:>12}"
        print(row)


def print_final_summary(csv_results: Dict[str, Dict], docx_results: Dict[str, Dict]):
    """四模型综合总结"""
    print(f"\n{SEP}")
    print("                    🏆 综合结论")
    print(SEP)

    # =========================================================================
    # BERT 对比
    # =========================================================================
    bert_ok = "bert_old" in csv_results or "bert_old" in docx_results
    if bert_ok:
        print("\n  【BERT 对比: 12层 vs 4层】")
        bert_improvements = []

        for r, label in [(csv_results, "CSV"), (docx_results, "文档")]:
            if "bert_old" in r and "bert_new" in r:
                o, n = r["bert_old"], r["bert_new"]
                if label == "CSV":
                    d = n["text_to_code"]["top1"] - o["text_to_code"]["top1"]
                    bert_improvements.append(f"CSV Top-1: {d:+.2%}")
                    d3 = n["text_to_code"]["top3"] - o["text_to_code"]["top3"]
                    bert_improvements.append(f"CSV Top-3: {d3:+.2%}")
                    sep_d = n["separation"] - o["separation"]
                    bert_improvements.append(f"CSV 分离度: {sep_d:+.4f}")
                else:
                    d = n["same_doc_top1"] - o["same_doc_top1"]
                    bert_improvements.append(f"文档 Top-1: {d:+.2%}")
                    d_sep = n["separation"] - o["separation"]
                    bert_improvements.append(f"文档分离度: {d_sep:+.4f}")

        if bert_improvements:
            print("    BERT-4层 vs BERT-12层:")
            for imp in bert_improvements:
                print(f"      - {imp}")

        # 速度/大小
        if "bert_old" in csv_results and "bert_new" in csv_results:
            old_t = csv_results["bert_old"]["encode_time_sec"]
            new_t = csv_results["bert_new"]["encode_time_sec"]
            if old_t > 0:
                print(f"      - 编码速度: BERT-4层 {old_t/new_t:.1f}x {'更快' if new_t < old_t else '更慢'}")
            old_dim = csv_results["bert_old"]["embedding_dim"]
            new_dim = csv_results["bert_new"]["embedding_dim"]
            print(f"      - 向量维度: {old_dim} → {new_dim} ({new_dim/old_dim:.0%})")

    # =========================================================================
    # Sentence 对比
    # =========================================================================
    sent_ok = "sent_old" in csv_results or "sent_old" in docx_results
    if sent_ok:
        print("\n  【Sentence 对比: MiniLM-L6 vs bge-small-zh】")
        sent_improvements = []

        for r, label in [(csv_results, "CSV"), (docx_results, "文档")]:
            if "sent_old" in r and "sent_new" in r:
                o, n = r["sent_old"], r["sent_new"]
                if label == "CSV":
                    d = n["text_to_code"]["top1"] - o["text_to_code"]["top1"]
                    sent_improvements.append(f"CSV Top-1: {d:+.2%}")
                    sep_d = n["separation"] - o["separation"]
                    sent_improvements.append(f"CSV 分离度: {sep_d:+.4f}")
                else:
                    d = n["same_doc_top1"] - o["same_doc_top1"]
                    sent_improvements.append(f"文档 Top-1: {d:+.2%}")
                    d_sep = n["separation"] - o["separation"]
                    sent_improvements.append(f"文档分离度: {d_sep:+.4f}")

        if sent_improvements:
            print("    bge-small-zh vs MiniLM-L6:")
            for imp in sent_improvements:
                print(f"      - {imp}")

        # 速度/大小
        if "sent_old" in csv_results and "sent_new" in csv_results:
            old_t = csv_results["sent_old"]["encode_time_sec"]
            new_t = csv_results["sent_new"]["encode_time_sec"]
            if old_t > 0:
                print(f"      - 编码速度: bge {old_t/new_t:.1f}x {'更快' if new_t < old_t else '更慢'}")
            old_dim = csv_results["sent_old"]["embedding_dim"]
            new_dim = csv_results["sent_new"]["embedding_dim"]
            print(f"      - 向量维度: {old_dim} → {new_dim}")

    # =========================================================================
    # 总体建议
    # =========================================================================
    print(f"\n  📦 当前配置: BERT-4层 + bge-small-zh-v1.5")
    print(f"     模型路径: {LOCAL_MODELS_DIR}")
    print(SEP + "\n")


# =============================================================================
# 主流程
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="四模型对比基准测试")
    parser.add_argument("--csv-only", action="store_true", help="仅 CSV 测试")
    parser.add_argument("--docx-only", action="store_true", help="仅文档测试")
    parser.add_argument("--docx-dir", type=str, default=None,
                        help=f"文档目录 (默认: {os.path.join(os.path.dirname(os.path.abspath(__file__)), '文本样本')})")
    parser.add_argument("--test-file", type=str, default=None, help="指定单个 CSV 文件")
    parser.add_argument("--batch-size", type=int, default=64, help="编码批大小")
    parser.add_argument("--no-mirror", action="store_true", help="不使用国内镜像")
    parser.add_argument("--hf-mirror", type=str, default="https://hf-mirror.com", help="HF 镜像地址")
    parser.add_argument("--max-sentences", type=int, default=150,
                        help="每个文档最多取多少句 (默认150)")
    parser.add_argument("--bert-only", action="store_true", help="仅测试 BERT 模型")
    parser.add_argument("--sent-only", action="store_true", help="仅测试 Sentence 模型")
    args = parser.parse_args()

    run_csv = not args.docx_only
    run_docx = not args.csv_only
    run_bert = not args.sent_only
    run_sent = not args.bert_only

    print(SEP)
    print("                    四模型对比基准测试 v2.0")
    print(f"  BERT 对比:  bert-base-chinese (12层) vs custom_bert_4layer (4层)")
    print(f"  Sent 对比:  MiniLM-L6-v2 vs bge-small-zh-v1.5")
    print(f"  测试项: {'CSV ' if run_csv else ''}{'文档' if run_docx else ''}")
    print(SEP)

    use_mirror = not args.no_mirror
    if use_mirror:
        os.environ["HF_ENDPOINT"] = args.hf_mirror

    csv_results = {}
    docx_results = {}

    # =========================================================
    # Step 1: CSV 测试
    # =========================================================
    if run_csv:
        print("\n[CSV] 加载测试数据...")
        if args.test_file:
            test_pairs = load_csv_data(args.test_file)
        else:
            test_pairs = load_all_csv_data()

        if len(test_pairs) < 10:
            logger.error(f"CSV 数据不足 ({len(test_pairs)} 条)")
        else:
            batch_size = args.batch_size

            # --- BERT 模型 ---
            if run_bert:
                print("\n[CSV] 评估 BERT-12层 (bert-base-chinese)...")
                try:
                    bert_old = load_bert_model(OLD_BERT_MODEL_LOCAL)
                    csv_results["bert_old"] = evaluate_csv(bert_old, test_pairs, "BERT-12层", batch_size)
                    del bert_old
                    if torch.cuda.is_available(): torch.cuda.empty_cache()
                except Exception as e:
                    logger.error(f"BERT-12层 评估失败: {e}")

                print(f"\n[CSV] 评估 BERT-4层 (custom_bert_4layer)...")
                try:
                    bert_new = load_bert_model(NEW_BERT_MODEL_LOCAL)
                    csv_results["bert_new"] = evaluate_csv(bert_new, test_pairs, "BERT-4层", batch_size)
                    del bert_new
                    if torch.cuda.is_available(): torch.cuda.empty_cache()
                except Exception as e:
                    logger.error(f"BERT-4层 评估失败: {e}")

            # --- Sentence 模型 ---
            if run_sent:
                print(f"\n[CSV] 评估 MiniLM-L6 (旧)...")
                try:
                    sent_old = load_sentence_model(OLD_SENT_MODEL_NAME, OLD_SENT_MODEL_LOCAL)
                    csv_results["sent_old"] = evaluate_csv(sent_old, test_pairs, "MiniLM-L6", batch_size)
                    del sent_old
                    if torch.cuda.is_available(): torch.cuda.empty_cache()
                except Exception as e:
                    logger.error(f"MiniLM-L6 评估失败: {e}")

                print(f"\n[CSV] 评估 bge-small-zh (新)...")
                try:
                    sent_new = load_sentence_model(NEW_SENT_MODEL_NAME, NEW_SENT_MODEL_LOCAL, use_mirror)
                    csv_results["sent_new"] = evaluate_csv(sent_new, test_pairs, "bge-small-zh", batch_size)
                    del sent_new
                    if torch.cuda.is_available(): torch.cuda.empty_cache()
                except Exception as e:
                    logger.error(f"bge-small-zh 评估失败: {e}")

    # =========================================================
    # Step 2: 文档测试
    # =========================================================
    if run_docx:
        docx_dir = args.docx_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "文本样本")
        if not os.path.exists(docx_dir):
            logger.warning(f"文档目录不存在: {docx_dir}，跳过文档测试")
        else:
            print(f"\n[文档] 从 {docx_dir} 提取句子...")
            docs = load_docx_sentences(docx_dir, max_sentences_per_file=args.max_sentences)

            if len(docs) < 2:
                logger.warning(f"文档数不足 ({len(docs)})，跳过文档测试")
            else:
                batch_size = args.batch_size

                # --- BERT 模型 ---
                if run_bert:
                    print(f"\n[文档] 评估 BERT-12层...")
                    try:
                        bert_old = load_bert_model(OLD_BERT_MODEL_LOCAL)
                        docx_results["bert_old"] = evaluate_on_docx(bert_old, docs, "BERT-12层", batch_size)
                        del bert_old
                        if torch.cuda.is_available(): torch.cuda.empty_cache()
                    except Exception as e:
                        logger.error(f"BERT-12层 文档评估失败: {e}")

                    print(f"\n[文档] 评估 BERT-4层...")
                    try:
                        bert_new = load_bert_model(NEW_BERT_MODEL_LOCAL)
                        docx_results["bert_new"] = evaluate_on_docx(bert_new, docs, "BERT-4层", batch_size)
                        del bert_new
                        if torch.cuda.is_available(): torch.cuda.empty_cache()
                    except Exception as e:
                        logger.error(f"BERT-4层 文档评估失败: {e}")

                # --- Sentence 模型 ---
                if run_sent:
                    print(f"\n[文档] 评估 MiniLM-L6...")
                    try:
                        sent_old = load_sentence_model(OLD_SENT_MODEL_NAME, OLD_SENT_MODEL_LOCAL)
                        docx_results["sent_old"] = evaluate_on_docx(sent_old, docs, "MiniLM-L6", batch_size)
                        del sent_old
                        if torch.cuda.is_available(): torch.cuda.empty_cache()
                    except Exception as e:
                        logger.error(f"MiniLM-L6 文档评估失败: {e}")

                    print(f"\n[文档] 评估 bge-small-zh...")
                    try:
                        sent_new = load_sentence_model(NEW_SENT_MODEL_NAME, NEW_SENT_MODEL_LOCAL, use_mirror)
                        docx_results["sent_new"] = evaluate_on_docx(sent_new, docs, "bge-small-zh", batch_size)
                        del sent_new
                        if torch.cuda.is_available(): torch.cuda.empty_cache()
                    except Exception as e:
                        logger.error(f"bge-small-zh 文档评估失败: {e}")

    # =========================================================
    # 报告
    # =========================================================
    if csv_results:
        print_csv_report(csv_results)
    if docx_results:
        print_docx_report(docx_results)
    if csv_results or docx_results:
        print_final_summary(csv_results, docx_results)
    else:
        print("\n⚠️  无有效测试结果，无法生成对比报告")


if __name__ == "__main__":
    main()