"""Test t5 encoder embeddings vs bge for abstract code retrieval.

Evaluates whether the pretrained t5-pegasus encoder (without fine-tuning)
produces useful sentence representations for the first-level coding task.

Usage:
    D:\anaconda3\envs\zthree5\python.exe test_t5_encoder.py
    D:\anaconda3\envs\zthree5\python.exe test_t5_encoder.py --max-samples 500
"""

import argparse
import json
import logging
import os
import random
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_t5")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_data(v11_path: str, max_samples: Optional[int] = None):
    with open(v11_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    training_data = data.get("training_data", [])
    if max_samples and len(training_data) > max_samples:
        random.seed(42)
        training_data = random.sample(training_data, max_samples)
    pairs: List[Tuple[str, str]] = []
    seen = set()
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
    return pairs


def build_t5_encoder():
    """Load t5-pegasus and return an encode function using mean-pooled encoder output."""
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
    logger.info("t5 encoder loaded: %.1fM params", sum(p.numel() for p in model.parameters()) / 1e6)

    @torch.no_grad()
    def encode(text: str) -> np.ndarray:
        ids, _ = tokenizer.encode(text, maxlen=256)
        ids_tensor = torch.tensor([ids], dtype=torch.long).to(device)
        # encoder returns [hidden_states, attention_bias]
        enc_out = model.encoder(ids_tensor)
        hidden = enc_out[0]  # [1, seq_len, 768]
        # Mean pooling over sequence
        mask = (ids_tensor != 0).float().unsqueeze(-1).to(device)
        pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
        return pooled.cpu().numpy().astype("float32").reshape(-1)

    return encode, tokenizer


def build_bge_encoder():
    """Load bge-small-zh-v1.5 and return an encode function."""
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


def evaluate_retrieval(
    pairs: List[Tuple[str, str]],
    encode_fn,
    name: str,
    top_k_values: List[int] = [1, 3, 5, 10],
) -> Dict:
    """Split into train/retrieval and test sets, evaluate top-k accuracy."""
    n_train = int(len(pairs) * 0.8)
    random.seed(42)
    indices = list(range(len(pairs)))
    random.shuffle(indices)
    train_idx = set(indices[:n_train])
    test_idx = indices[n_train:]

    train_sents = [pairs[i][0] for i in range(len(pairs)) if i in train_idx]
    train_labels = [pairs[i][1] for i in range(len(pairs)) if i in train_idx]
    test_pairs = [pairs[i] for i in test_idx]

    # Encode train sentences
    logger.info("[%s] Encoding %d train sentences ...", name, len(train_sents))
    train_embs = []
    for sent in train_sents:
        vec = encode_fn(sent)
        train_embs.append(vec)
    train_embs = np.stack(train_embs, axis=0)
    # Normalize
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

        # Cosine similarity
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--v11-path", type=str,
                        default=r"C:\Users\Lenovo\Documents\xwechat_files\wxid_eo5dkcv3sf7522_8ac6\msg\file\2026-05\v11_20260428_164754.json")
    args = parser.parse_args()

    logger.info("Loading v11 data ...")
    pairs = load_data(args.v11_path, max_samples=args.max_samples)
    logger.info("Total pairs: %d", len(pairs))

    results_all = []

    # --- bge ---
    logger.info("=" * 60)
    logger.info("Evaluating bge-small-zh-v1.5 ...")
    bge_encode = build_bge_encoder()
    bge_result = evaluate_retrieval(pairs, bge_encode, "bge")
    results_all.append(bge_result)
    logger.info("bge: %s", {k: v for k, v in bge_result.items() if k != "name"})

    # --- t5 encoder (mean pooling) ---
    logger.info("=" * 60)
    logger.info("Evaluating t5 encoder (mean pooling) ...")
    t5_encode, _ = build_t5_encoder()
    t5_result = evaluate_retrieval(pairs, t5_encode, "t5_meanpool")
    results_all.append(t5_result)
    logger.info("t5:  %s", {k: v for k, v in t5_result.items() if k != "name"})

    # --- Comparison ---
    print("\n" + "=" * 70)
    print("RETRIEVAL COMPARISON: bge vs t5 encoder (pretrained, no fine-tuning)")
    print("=" * 70)
    header = f"{'Metric':<16}"
    for r in results_all:
        header += f" {r['name']:>16}"
    print(header)
    print("-" * 70)

    metrics = ["top1_acc", "top3_acc", "top5_acc", "top10_acc"]
    for m in metrics:
        line = f"{m:<16}"
        for r in results_all:
            line += f" {r[m]:>16.4f}"
        print(line)

    # --- Also test: if we encode abstract codes directly ---
    logger.info("=" * 60)
    logger.info("Evaluating abstract-code encoding (label → sentence retrieval) ...")
    unique_labels = list(set(p[1] for p in pairs))
    logger.info("Unique abstract codes: %d", len(unique_labels))

    # Encode all unique labels with t5 encoder
    label_embs_t5 = []
    for lbl in unique_labels:
        vec = t5_encode(lbl)
        label_embs_t5.append(vec)
    label_embs_t5 = np.stack(label_embs_t5, axis=0)
    norms = np.linalg.norm(label_embs_t5, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-9, norms)
    label_embs_t5 = label_embs_t5 / norms

    # Encode with bge
    label_embs_bge = []
    for lbl in unique_labels:
        vec = bge_encode(lbl)
        label_embs_bge.append(vec)
    label_embs_bge = np.stack(label_embs_bge, axis=0)
    norms = np.linalg.norm(label_embs_bge, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-9, norms)
    label_embs_bge = label_embs_bge / norms

    # For each test sentence, find best matching label directly
    n_test = int(len(pairs) * 0.2)
    test_pairs = pairs[-n_test:]

    def label_retrieval_score(label_embs, encode_fn, test_pairs, unique_labels):
        correct = {1: 0, 3: 0, 5: 0}
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
        return {k: round(v / max(1, len(test_pairs)), 4) for k, v in correct.items()}

    bge_label = label_retrieval_score(label_embs_bge, bge_encode, test_pairs, unique_labels)
    t5_label = label_retrieval_score(label_embs_t5, t5_encode, test_pairs, unique_labels)

    print("\n--- Direct label retrieval (sentence → label embedding) ---")
    print(f"bge: top1={bge_label[1]:.4f}, top3={bge_label[3]:.4f}, top5={bge_label[5]:.4f}")
    print(f"t5:  top1={t5_label[1]:.4f}, top3={t5_label[3]:.4f}, top5={t5_label[5]:.4f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
