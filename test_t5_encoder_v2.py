"""Test t5 encoder embeddings on CSV-based labeled data (sentence → code pairs).

Compares t5-pegasus encoder vs bge-small-zh-v1.5 for retrieval on
high-quality first-level coding samples from D:\zthree2\csv.

Usage:
    D:\anaconda3\envs\zthree5\python.exe test_t5_encoder_v2.py
"""

import csv
import json
import logging
import os
import random
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_t5v2")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ------------------------------------------------------------------
# Data loading
# ------------------------------------------------------------------

def load_csv_pairs(csv_dir: str) -> List[Tuple[str, str]]:
    """Load (sentence, code) pairs from all CSV files in the directory."""
    file_encodings = {
        "standard.csv": "gbk",
        "standard2.csv": "utf-8",
        "standard_augmented.csv": "utf-8",
        "standard_train.csv": "utf-8",
        "standard_val.csv": "utf-8",
        "standard_test.csv": "utf-8",
    }
    pairs: List[Tuple[str, str]] = []
    seen: set = set()

    for fname, enc in file_encodings.items():
        path = os.path.join(csv_dir, fname)
        if not os.path.exists(path):
            continue
        count = 0
        with open(path, "r", encoding=enc, errors="replace") as fh:
            reader = csv.reader(fh)
            next(reader, None)  # skip header
            for row in reader:
                if len(row) < 2:
                    continue
                code = row[0].strip()
                text = row[1].strip()
                if not code or not text or code.lower() == "nan":
                    continue
                key = (text, code)
                if key in seen:
                    continue
                seen.add(key)
                pairs.append((text, code))
                count += 1
        logger.info("  %s: %d valid pairs", fname, count)

    logger.info("Total CSV pairs (deduplicated): %d", len(pairs))
    return pairs


def load_v11_pairs(v11_path: str) -> List[Tuple[str, str]]:
    """Load (sentence, abstract_code) pairs from v11 JSON."""
    with open(v11_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    training_data = data.get("training_data", [])
    pairs: List[Tuple[str, str]] = []
    seen: set = set()
    for item in training_data:
        sent = str(
            (item.get("input_sentences", {}) or {}).get("original_content", "")
        ).strip()
        abstract = str(item.get("target_abstract", "")).strip()
        if not sent or not abstract:
            continue
        key = (sent, abstract)
        if key in seen:
            continue
        seen.add(key)
        pairs.append((sent, abstract))
    logger.info("Total v11 pairs: %d", len(pairs))
    return pairs


# ------------------------------------------------------------------
# Encoder building
# ------------------------------------------------------------------

def build_t5_encoder():
    import jieba
    jieba.initialize()
    from bert4torch.models import build_transformer_model
    from bert4torch.tokenizers import Tokenizer
    import torch

    model_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "local_models", "chinese_t5_pegasus_base",
    )
    tokenizer = Tokenizer(
        os.path.join(model_dir, "vocab.txt"),
        do_lower_case=True,
        pre_tokenize=lambda s: list(jieba.cut(s, HMM=False)),
    )
    model = build_transformer_model(
        config_path=os.path.join(model_dir, "bert4torch_config.json"),
        checkpoint_path=os.path.join(model_dir, "pytorch_model.bin"),
        model="mt5.1.1",
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    n_params = sum(p.numel() for p in model.parameters())
    logger.info("t5 encoder loaded: %.1fM params on %s", n_params / 1e6, device)

    @torch.no_grad()
    def encode(text: str) -> np.ndarray:
        ids, _ = tokenizer.encode(text, maxlen=256)
        ids_tensor = torch.tensor([ids], dtype=torch.long).to(device)
        enc_out = model.encoder(ids_tensor)
        hidden = enc_out[0]  # [1, seq_len, 768]
        mask = (ids_tensor != 0).float().unsqueeze(-1).to(device)
        pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
        return pooled.cpu().numpy().astype("float32").reshape(-1)

    return encode, tokenizer


def build_bge_encoder():
    from sentence_transformers import SentenceTransformer
    bge_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "local_models", "bge-small-zh-v1.5",
    )
    model = SentenceTransformer(bge_path)
    logger.info("bge encoder loaded")

    def encode(text: str) -> np.ndarray:
        return model.encode(text, normalize_embeddings=True).astype("float32").reshape(-1)

    return encode


# ------------------------------------------------------------------
# Evaluation
# ------------------------------------------------------------------

def evaluate_retrieval(
    pairs: List[Tuple[str, str]],
    encode_fn,
    name: str,
    top_k_values: List[int] = [1, 3, 5, 10, 20],
) -> Dict:
    """Train/Test split, embed train set, evaluate top-k retrieval accuracy."""
    random.seed(42)
    indices = list(range(len(pairs)))
    random.shuffle(indices)
    split = int(len(pairs) * 0.8)
    train_idx = set(indices[:split])
    test_idx = indices[split:]

    train_sents = [pairs[i][0] for i in range(len(pairs)) if i in train_idx]
    train_labels = [pairs[i][1] for i in range(len(pairs)) if i in train_idx]
    test_pairs = [pairs[i] for i in test_idx]

    logger.info("[%s] Encoding %d train sentences ...", name, len(train_sents))
    train_embs = []
    batch = 64
    for i in range(0, len(train_sents), batch):
        batch_texts = train_sents[i:i + batch]
        batch_vecs = [encode_fn(t) for t in batch_texts]
        train_embs.extend(batch_vecs)
        if i % 256 == 0 and i > 0:
            logger.info("  [%s] encoded %d/%d", name, i, len(train_sents))
    train_embs = np.stack(train_embs, axis=0)
    norms = np.linalg.norm(train_embs, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-9, norms)
    train_embs = train_embs / norms

    logger.info("[%s] Evaluating %d test samples ...", name, len(test_pairs))
    correct = defaultdict(int)
    total = 0

    for sent, gold_label in test_pairs:
        query_vec = encode_fn(sent)
        norm = np.linalg.norm(query_vec)
        if norm > 0:
            query_vec = query_vec / norm

        scores = np.dot(train_embs, query_vec)
        ranked = np.argsort(-scores)

        for k in top_k_values:
            top_labels = [train_labels[int(i)] for i in ranked[:k]]
            if gold_label in top_labels:
                correct[k] += 1
        total += 1

    results = {"name": name, "total": total}
    for k in top_k_values:
        results[f"top{k}_acc"] = round(correct[k] / max(1, total), 4)
    return results


def evaluate_label_retrieval(
    pairs: List[Tuple[str, str]],
    encode_fn,
    name: str,
) -> Dict:
    """Direct sentence → label embedding similarity retrieval.

    Encode all unique labels, then for each test sentence,
    find the closest label directly.
    """
    random.seed(42)
    indices = list(range(len(pairs)))
    random.shuffle(indices)
    split = int(len(pairs) * 0.8)

    unique_labels = list(set(p[1] for p in pairs))
    logger.info("[%s] Encoding %d unique labels ...", name, len(unique_labels))
    label_embs = []
    for lbl in unique_labels:
        vec = encode_fn(lbl)
        label_embs.append(vec)
    label_embs = np.stack(label_embs, axis=0)
    norms = np.linalg.norm(label_embs, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-9, norms)
    label_embs = label_embs / norms

    test_pairs = [pairs[i] for i in indices[split:]]
    correct = {1: 0, 3: 0, 5: 0, 10: 0}
    for sent, gold_label in test_pairs:
        q = encode_fn(sent)
        norm = np.linalg.norm(q)
        if norm > 0:
            q = q / norm
        scores = np.dot(label_embs, q)
        ranked = np.argsort(-scores)
        for k in correct:
            top_labels = [unique_labels[int(i)] for i in ranked[:k]]
            if gold_label in top_labels:
                correct[k] += 1

    total = len(test_pairs)
    return {
        "name": name + "_label",
        "total": total,
        "top1_acc": round(correct[1] / total, 4),
        "top3_acc": round(correct[3] / total, 4),
        "top5_acc": round(correct[5] / total, 4),
        "top10_acc": round(correct[10] / total, 4),
    }


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    csv_dir = r"D:\zthree2\csv"
    v11_path = r"C:\Users\Lenovo\Documents\xwechat_files\wxid_eo5dkcv3sf7522_8ac6\msg\file\2026-05\v11_20260428_164754.json"

    # ---- Load data ----
    logger.info("=" * 60)
    logger.info("Loading CSV data ...")
    csv_pairs = load_csv_pairs(csv_dir)

    logger.info("Loading v11 data ...")
    v11_pairs = load_v11_pairs(v11_path)

    # Only use unique (sentence, code) pairs within each source,
    # and also deduplicate across sources
    all_pairs = list(set(csv_pairs + v11_pairs))
    logger.info("Combined unique pairs: %d", len(all_pairs))

    # ---- Build encoders ----
    bge_encode = build_bge_encoder()
    t5_encode, _ = build_t5_encoder()

    results_all = []

    # ---- Test 1: CSV only ----
    logger.info("\n" + "=" * 60)
    logger.info("TEST 1: CSV data only (%d pairs)", len(csv_pairs))
    bge_csv = evaluate_retrieval(csv_pairs, bge_encode, "bge_csv")
    t5_csv = evaluate_retrieval(csv_pairs, t5_encode, "t5_csv")
    results_all.extend([bge_csv, t5_csv])

    # ---- Test 2: v11 only ----
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: v11 data only (%d pairs)", len(v11_pairs))
    bge_v11 = evaluate_retrieval(v11_pairs, bge_encode, "bge_v11")
    t5_v11 = evaluate_retrieval(v11_pairs, t5_encode, "t5_v11")
    results_all.extend([bge_v11, t5_v11])

    # ---- Test 3: Combined CSV + v11 ----
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Combined CSV + v11 (%d pairs)", len(all_pairs))
    bge_all = evaluate_retrieval(all_pairs, bge_encode, "bge_all")
    t5_all = evaluate_retrieval(all_pairs, t5_encode, "t5_all")
    results_all.extend([bge_all, t5_all])

    # ---- Test 4: Label retrieval (sentence → label directly) ----
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Direct label retrieval (sentence → code embedding)")
    bge_label_csv = evaluate_label_retrieval(csv_pairs, bge_encode, "bge_csv")
    t5_label_csv = evaluate_label_retrieval(csv_pairs, t5_encode, "t5_csv")
    bge_label_all = evaluate_label_retrieval(all_pairs, bge_encode, "bge_all")
    t5_label_all = evaluate_label_retrieval(all_pairs, t5_encode, "t5_all")
    results_all.extend([bge_label_csv, t5_label_csv, bge_label_all, t5_label_all])

    # ---- Print results ----
    print("\n" + "=" * 90)
    print("FULL RETRIEVAL COMPARISON: bge vs t5-pegasus encoder")
    print("=" * 90)

    # Sentence→Sentence retrieval
    print("\n--- Sentence-to-Sentence Retrieval (kNN-style) ---")
    header = f"{'Metric':<16}"
    for r in results_all:
        if "_label" not in r["name"]:
            header += f" {r['name']:>14}"
    print(header)
    print("-" * (16 + 14 * 6))

    metrics = ["top1_acc", "top3_acc", "top5_acc", "top10_acc"]
    for m in metrics:
        line = f"{m:<16}"
        for r in results_all:
            if "_label" not in r["name"]:
                line += f" {r[m]:>14.4f}"
        print(line)

    # Label→Label retrieval
    print("\n--- Direct Label Retrieval (sentence → code embedding) ---")
    header = f"{'Metric':<16}"
    for r in results_all:
        if "_label" in r["name"]:
            header += f" {r['name']:>14}"
    print(header)
    print("-" * (16 + 14 * 4))

    for m in metrics:
        line = f"{m:<16}"
        for r in results_all:
            if "_label" in r["name"]:
                line += f" {r[m]:>14.4f}"
        print(line)

    # ---- Summary ----
    print("\n--- Summary ---")
    print(f"CSV data source:  {len(csv_pairs)} unique pairs")
    print(f"v11 data source:  {len(v11_pairs)} unique pairs")
    print(f"Combined total:   {len(all_pairs)} unique pairs")

    return 0


if __name__ == "__main__":
    sys.exit(main())
