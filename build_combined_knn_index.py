"""Build combined kNN index from v11 + CSV first-level coding data.

Sources:
  - v11 JSON: extracts (sentence, target_abstract) pairs (first-level coding)
  - final_standard.csv: GBK-encoded (一阶编码, 原始文本) pairs
  - Other CSV files with the same format (optional)

All pairs are combined, deduplicated, embedded with bge, and indexed with FAISS.

Usage:
    D:\anaconda3\envs\zthree5\python.exe build_combined_knn_index.py
    D:\anaconda3\envs\zthree5\python.exe build_combined_knn_index.py --include-all-csv
"""

import argparse
import csv
import json
import logging
import os
import sys
from typing import List, Tuple

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("build_knn")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_v11_pairs(v11_path: str) -> List[Tuple[str, str]]:
    """Extract (sentence, abstract_code) first-level coding pairs from v11."""
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
    logger.info("v11: %d unique (sentence, abstract_code) pairs", len(pairs))
    return pairs


def load_csv_pairs(csv_path: str, encoding: str = "gbk") -> List[Tuple[str, str]]:
    """Extract (text, first_level_code) pairs from a CSV file.

    Format: col 1 = first-level code, col 2 = original text.
    """
    pairs: List[Tuple[str, str]] = []
    seen: set = set()
    with open(csv_path, "r", encoding=encoding, errors="replace") as fh:
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
    logger.info("  %s: %d valid pairs", os.path.basename(csv_path), len(pairs))
    return pairs


def build_bge_encoder():
    from sentence_transformers import SentenceTransformer
    bge_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "local_models", "bge-small-zh-v1.5",
    )
    model = SentenceTransformer(bge_path)
    logger.info("bge-small-zh-v1.5 loaded")

    def encode(text: str) -> np.ndarray:
        return model.encode(text, normalize_embeddings=True).astype("float32")

    return encode


def build_and_save_index(
    pairs: List[Tuple[str, str]],
    encode_fn,
    output_dir: str,
) -> int:
    """Embed all text pairs, build FAISS index, save to disk."""
    import faiss
    os.makedirs(output_dir, exist_ok=True)

    sentences = [p[0] for p in pairs]
    codes = [p[1] for p in pairs]

    logger.info("Encoding %d sentences ...", len(sentences))
    embeddings_list: List[np.ndarray] = []
    batch_size = 64
    for i in range(0, len(sentences), batch_size):
        batch = sentences[i:i + batch_size]
        for text in batch:
            vec = encode_fn(text)
            embeddings_list.append(vec.reshape(-1))
        if i % 512 == 0 and i > 0:
            logger.info("  encoded %d/%d", i, len(sentences))

    embeddings = np.stack(embeddings_list, axis=0).astype("float32")

    # Already normalized by bge (normalize_embeddings=True), but double-check
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-9, norms)
    embeddings = embeddings / norms

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    logger.info("FAISS index built: %d vectors, dim=%d", len(sentences), dim)

    # Save
    np.savez_compressed(
        os.path.join(output_dir, "knn_embeddings.npz"),
        embeddings=embeddings,
    )
    with open(os.path.join(output_dir, "knn_sentences.json"), "w", encoding="utf-8") as fh:
        json.dump(
            {"sentences": sentences, "abstracts": codes},
            fh, ensure_ascii=False, indent=2,
        )
    faiss.write_index(index, os.path.join(output_dir, "knn_index.faiss"))
    logger.info("Index saved to %s (%d pairs)", output_dir, len(sentences))
    return len(sentences)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--v11-path", type=str,
                        default=r"C:\Users\Lenovo\Documents\xwechat_files\wxid_eo5dkcv3sf7522_8ac6\msg\file\2026-05\v11_20260428_164754.json")
    parser.add_argument("--csv-dir", type=str,
                        default=r"D:\zthree2\csv")
    parser.add_argument("--include-all-csv", action="store_true",
                        help="Include all CSV files in csv-dir, not just final_standard.csv")
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()

    output_dir = args.output_dir or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "cache", "knn_combined_index",
    )

    # ---- Load all data ----
    logger.info("=" * 60)
    logger.info("Loading data sources ...")

    # 1. v11 (first-level abstract codes)
    v11_pairs = load_v11_pairs(args.v11_path)

    # 2. final_standard.csv (primary CSV source)
    final_csv = os.path.join(args.csv_dir, "final_standard.csv")
    csv_pairs = []
    if os.path.exists(final_csv):
        csv_pairs = load_csv_pairs(final_csv, encoding="gbk")
    else:
        logger.warning("final_standard.csv not found at %s", final_csv)

    # 3. Optionally include other CSV files
    if args.include_all_csv:
        other_csv_files = {
            "standard_augmented.csv": "utf-8",
            "standard.csv": "gbk",
            "standard2.csv": "utf-8",
        }
        for fname, enc in other_csv_files.items():
            path = os.path.join(args.csv_dir, fname)
            if not os.path.exists(path) or fname == "final_standard.csv":
                continue
            extra = load_csv_pairs(path, encoding=enc)
            csv_pairs.extend(extra)

    # ---- Combine and deduplicate ----
    all_pairs = list(set(v11_pairs + csv_pairs))
    n_v11_only = sum(1 for p in all_pairs if p in set(v11_pairs) and p not in set(csv_pairs))
    n_csv_only = sum(1 for p in all_pairs if p in set(csv_pairs) and p not in set(v11_pairs))
    n_both = sum(1 for p in all_pairs if p in set(v11_pairs) and p in set(csv_pairs))

    logger.info("")
    logger.info("Data summary:")
    logger.info("  v11 pairs:            %d", len(v11_pairs))
    logger.info("  CSV pairs:            %d", len(csv_pairs))
    logger.info("  Combined unique:      %d", len(all_pairs))
    logger.info("  v11-only:             %d", n_v11_only)
    logger.info("  CSV-only:             %d", n_csv_only)
    logger.info("  Overlap (both):       %d", n_both)

    # ---- Statistics ----
    unique_texts = set(p[0] for p in all_pairs)
    unique_codes = set(p[1] for p in all_pairs)
    logger.info("  Unique texts:         %d", len(unique_texts))
    logger.info("  Unique codes:         %d", len(unique_codes))

    # ---- Build index ----
    logger.info("")
    logger.info("Building kNN index ...")
    encode_fn = build_bge_encoder()
    n_indexed = build_and_save_index(all_pairs, encode_fn, output_dir)

    logger.info("")
    logger.info("Done. Combined kNN index: %d pairs in %s", n_indexed, output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
