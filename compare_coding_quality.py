"""
Before/After comparison of first-level coding quality.

Three improvements from D:\\zthree2\\改进方向:
1. RAG document-level retrieval (QualCoder-inspired)
2. Dynamic threshold optimization (iQual-inspired)
3. Comprehensive evaluation metrics (F1/precision/recall)

Usage:
    D:\\anaconda3\\envs\\zthree5\\python.exe compare_coding_quality.py
    D:\\anaconda3\\envs\\zthree5\\python.exe compare_coding_quality.py --max-samples 200
    D:\\anaconda3\\envs\\zthree5\\python.exe compare_coding_quality.py --full
"""

import argparse
import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("compare")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from enhanced_coding_generator import EnhancedCodingGenerator
from model_manager import EnhancedModelManager
from first_level_eval import (
    evaluate_first_level_full,
    analyze_first_level_errors,
    write_compact_eval_jsonl,
)
from threshold_optimizer import ThresholdOptimizer
from rag_doc_retriever import RagDocRetriever


def load_samples(v11_path: str, max_samples: Optional[int] = None) -> List[Dict[str, Any]]:
    with open(v11_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    training_data = data.get("training_data", [])
    if not training_data:
        raise ValueError("No training_data in v11 JSON")
    if max_samples and len(training_data) > max_samples:
        random.seed(42)
        training_data = random.sample(training_data, max_samples)
    logger.info("Loaded %d samples", len(training_data))
    return training_data


def create_model_manager() -> Optional[EnhancedModelManager]:
    try:
        mgr = EnhancedModelManager()
        # Ensure abstract reranker is loaded before evaluation
        if not mgr.is_abstract_reranker_available():
            loaded = mgr.ensure_abstract_reranker_loaded()
            logger.info("Abstract reranker loaded: %s", loaded)
        if not mgr.is_trained_model_available():
            logger.warning("No trained models available, using rule-based only")
        else:
            logger.info("Trained model available")
        return mgr
    except Exception as e:
        logger.warning("Model manager creation failed: %s", e)
        return None


def load_recall_bank_labels() -> List[str]:
    """Load first-level recall labels from configured CSV files."""
    import pandas as pd

    names = list(getattr(Config, "FIRST_LEVEL_RECALL_BANK_FILES", []) or [])
    labels: List[str] = []
    seen = set()
    for name in names:
        if os.path.isabs(name):
            path = name
        else:
            path = os.path.join(Config.BASE_DIR, "csv", name)
        if not os.path.exists(path):
            continue
        try:
            encodings = ["utf-8-sig", "utf-8", "gb18030", "gbk"]
            for enc in encodings:
                try:
                    df = pd.read_csv(path, encoding=enc)
                    if df.shape[1] >= 1:
                        for label in df.iloc[:, 0].fillna("").astype(str).str.strip().tolist():
                            if label and label not in seen:
                                seen.add(label)
                                labels.append(label)
                    break
                except Exception:
                    continue
        except Exception:
            continue
    logger.info("Loaded %d recall bank labels from %d files", len(labels), len(names))
    return labels


def build_rag_index(
    samples: List[Dict[str, Any]],
    model_manager,
    index_dir: str,
) -> Optional[RagDocRetriever]:
    """Build QualCoder-style document FAISS index from training data sentences."""
    try:
        texts = [
            str((s.get("input_sentences", {}) or {}).get("original_content", "") or "").strip()
            for s in samples
            if str((s.get("input_sentences", {}) or {}).get("original_content", "") or "").strip()
        ]
        if not texts:
            return None

        embedding_fn = None
        if model_manager:
            try:
                model_manager.ensure_sentence_model_loaded()
                embedding_fn = model_manager.encode_sentence
            except Exception:
                pass

        retriever = RagDocRetriever(
            embedding_fn=embedding_fn,
            index_dir=index_dir,
            chunk_size=500,
            chunk_overlap=100,
        )
        count = retriever.index_texts(texts, source_label="v11")
        logger.info("RAG doc index: %d chunks from %d texts", count, len(texts))
        return retriever
    except Exception as e:
        logger.warning("RAG index build failed: %s", e)
        return None


def evaluate(
    samples: List[Dict[str, Any]],
    generator: EnhancedCodingGenerator,
    model_manager,
    label: str,
) -> Dict[str, Any]:
    """Run one evaluation pass and log summary."""
    logger.info("=" * 60)
    logger.info("%s evaluation ...", label)
    t0 = time.time()
    result = evaluate_first_level_full(samples, generator, model_manager=model_manager)
    elapsed = time.time() - t0

    s = result["summary"]
    logger.info("%s (%d samples, %.1fs):", label, s["sample_count"], elapsed)
    logger.info("  Top-1 Accuracy:      %.4f", s["top1_accuracy"])
    logger.info("  Top-1 Relaxed:        %.4f", s["top1_relaxed_accuracy"])
    logger.info("  Exact Micro F1:       %.4f", s["exact_micro_f1"])
    logger.info("  Exact Macro F1:       %.4f", s["exact_macro_f1"])
    logger.info("  Relaxed Precision:    %.4f", s["relaxed_precision"])
    logger.info("  Relaxed Recall:       %.4f", s["relaxed_recall"])
    logger.info("  Relaxed F1:           %.4f", s["relaxed_f1"])
    logger.info("  Unique gold/pred:     %d / %d", s["unique_gold_labels"], s["unique_pred_labels"])

    error = analyze_first_level_errors(result["rows"])
    logger.info("  Error ratios:")
    for bucket, ratio in sorted(error["bucket_ratios"].items()):
        if ratio > 0:
            logger.info("    %s: %.4f", bucket, ratio)

    return result


def print_report(
    before: Dict[str, Any],
    after: Dict[str, Any],
    output_dir: str,
    rag_used: bool,
    thresholds_optimized: bool,
) -> None:
    """Print and save side-by-side comparison report."""
    bs = before["summary"]
    as_ = after["summary"]

    metrics = [
        ("top1_accuracy", "Top-1 Accuracy"),
        ("top1_relaxed_accuracy", "Top-1 Relaxed Acc"),
        ("exact_micro_f1", "Exact Micro F1"),
        ("exact_macro_f1", "Exact Macro F1"),
        ("relaxed_precision", "Relaxed Precision"),
        ("relaxed_recall", "Relaxed Recall"),
        ("relaxed_f1", "Relaxed F1"),
    ]

    lines = []
    lines.append("")
    lines.append("=" * 75)
    lines.append("FIRST-LEVEL CODING QUALITY COMPARISON")
    lines.append("=" * 75)
    lines.append(f"RAG doc retrieval:  {'ON' if rag_used else 'OFF'}")
    lines.append(f"Thresholds optimized: {'YES' if thresholds_optimized else 'NO'}")
    lines.append("")
    lines.append(f"{'Metric':<24} {'Before':>10} {'After':>10} {'Delta':>10} {'Change':>10}")
    lines.append("-" * 75)

    for key, label in metrics:
        bv = bs.get(key, 0)
        av = as_.get(key, 0)
        delta = av - bv
        pct = (delta / max(1e-9, bv)) * 100 if bv else 0.0
        lines.append(f"{label:<24} {bv:>10.4f} {av:>10.4f} {delta:>+10.4f} {pct:>+9.1f}%")

    lines.append("-" * 75)
    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append(f"Output: {output_dir}")
    lines.append("")

    report = "\n".join(lines)
    print(report)

    path = os.path.join(output_dir, "comparison_report.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(report)
    logger.info("Report saved: %s", path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-samples", type=int, default=200)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--no-rag", action="store_true")
    parser.add_argument("--no-thresholds", action="store_true")
    parser.add_argument("--v11-path", type=str,
                        default=r"C:\Users\Lenovo\Documents\xwechat_files\wxid_eo5dkcv3sf7522_8ac6\msg\file\2026-05\v11_20260428_164754.json")
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()

    max_samples = None if args.full else args.max_samples
    output_dir = args.output_dir or os.path.join(
        Config.BASE_DIR, "eval_results", datetime.now().strftime("%Y%m%d_%H%M%S")
    )
    os.makedirs(output_dir, exist_ok=True)
    logger.info("Output: %s", output_dir)

    # ---- Load data ----
    samples = load_samples(args.v11_path, max_samples=max_samples)

    # ---- Setup generator ----
    generator = EnhancedCodingGenerator()
    generator._ensure_first_level_defaults()

    logger.info("RAG enabled: %s", generator.rag_enabled)
    logger.info("Second threshold: %.4f", generator.rag_second_level_threshold)
    logger.info("Third threshold:  %.4f", generator.rag_third_level_threshold)
    logger.info("Cluster threshold: %.4f", generator.rag_cluster_similarity_threshold)

    model_manager = create_model_manager()

    # ---- Load recall bank labels (cross-domain CSV) ----
    recall_labels = load_recall_bank_labels()
    generator.set_first_level_recall_bank(recall_labels, model_manager=model_manager)
    logger.info("Recall bank: %d labels loaded", len(getattr(generator, 'first_level_recall_bank', [])))

    os.makedirs(output_dir, exist_ok=True)

    # ================================================================
    # PHASE 1: BASELINE (no recall bank, no RAG doc)
    # ================================================================
    logger.info("")
    logger.info("PHASE 1: Baseline (rule-based candidates only)")
    before_result = evaluate(samples, generator, model_manager, "BASELINE")
    write_compact_eval_jsonl(
        os.path.join(output_dir, "baseline_eval.jsonl.gz"), before_result["rows"]
    )

    # ================================================================
    # PHASE 2: +RECALL BANK (semantic recall from cross-domain CSV)
    # ================================================================
    logger.info("")
    logger.info("PHASE 2: +Recall Bank (cross-domain labels, no RAG doc)")
    # Enable recall-enhanced mode in generator
    recall_prev = bool(getattr(Config, 'FIRST_LEVEL_RECALL_ENHANCED', False))
    use_label_prev = bool(getattr(Config, 'FIRST_LEVEL_USE_LABEL_RECALL_CANDIDATES', False))
    if Config:
        Config.FIRST_LEVEL_RECALL_ENHANCED = True
        Config.FIRST_LEVEL_USE_LABEL_RECALL_CANDIDATES = True
    recall_result = evaluate(samples, generator, model_manager, "+RECALL")
    write_compact_eval_jsonl(
        os.path.join(output_dir, "recall_eval.jsonl.gz"), recall_result["rows"]
    )

    # ================================================================
    # PHASE 3: +RAG DOC (recall bank + RAG doc retriever)
    # ================================================================
    rag_used = False
    if not args.no_rag:
        logger.info("")
        logger.info("PHASE 3: +Recall +RAG Doc (cross-domain labels + context retrieval)")
        rag_dir = os.path.join(output_dir, "rag_doc_index")
        retriever = build_rag_index(samples, model_manager, rag_dir)
        if retriever and retriever.is_loaded:
            generator.rag_doc_retriever = retriever
            rag_used = True
            logger.info("RAG doc retriever attached to generator")
        else:
            logger.info("RAG doc retriever unavailable (no embeddings)")

    rag_result = evaluate(samples, generator, model_manager, "+RECALL+RAG")
    write_compact_eval_jsonl(
        os.path.join(output_dir, "rag_eval.jsonl.gz"), rag_result["rows"]
    )

    # Restore config
    if Config:
        Config.FIRST_LEVEL_RECALL_ENHANCED = recall_prev
        Config.FIRST_LEVEL_USE_LABEL_RECALL_CANDIDATES = use_label_prev

    thresholds_optimized = False

    # ================================================================
    # PHASE 4: Three-way Report
    # ================================================================
    bs = before_result["summary"]
    rs = recall_result["summary"]
    rags = rag_result["summary"]

    lines = []
    lines.append("")
    lines.append("=" * 85)
    lines.append("FIRST-LEVEL CODING QUALITY COMPARISON (3-way)")
    lines.append("=" * 85)
    lines.append(f"Recall bank labels: {len(recall_labels)}")
    lines.append(f"RAG doc retrieval: {'ON' if rag_used else 'OFF'}")
    lines.append("")
    lines.append(f"{'Metric':<24} {'Baseline':>10} {'+Recall':>10} {'+RAG':>10} {'Rec→RAG':>10}")
    lines.append("-" * 85)

    metrics = [
        ("top1_accuracy", "Top-1 Accuracy"),
        ("top1_relaxed_accuracy", "Top-1 Relaxed Acc"),
        ("exact_micro_f1", "Exact Micro F1"),
        ("exact_macro_f1", "Exact Macro F1"),
        ("relaxed_precision", "Relaxed Precision"),
        ("relaxed_recall", "Relaxed Recall"),
        ("relaxed_f1", "Relaxed F1"),
    ]

    for key, label in metrics:
        bv = bs.get(key, 0)
        rv = rs.get(key, 0)
        ragv = rags.get(key, 0)
        delta = ragv - rv
        lines.append(f"{label:<24} {bv:>10.4f} {rv:>10.4f} {ragv:>10.4f} {delta:>+10.4f}")

    lines.append("-" * 85)
    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append(f"Output: {output_dir}")

    report = "\n".join(lines)
    print(report)

    report_path = os.path.join(output_dir, "comparison_report.txt")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(report)
    logger.info("Report saved: %s", report_path)

    logger.info("Done.")


if __name__ == "__main__":
    main()
