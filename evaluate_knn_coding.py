"""Evaluate first-level coding with kNN abstract generation on test texts.

Usage:
    D:\anaconda3\envs\zthree5\python.exe evaluate_knn_coding.py
    D:\anaconda3\envs\zthree5\python.exe evaluate_knn_coding.py --max-samples 300
    D:\anaconda3\envs\zthree5\python.exe evaluate_knn_coding.py --full
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
logger = logging.getLogger("eval_knn")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from enhanced_coding_generator import EnhancedCodingGenerator
from model_manager import EnhancedModelManager
from knn_abstract_generator import KnnAbstractGenerator, create_knn_generator
from first_level_eval import (
    evaluate_first_level_full,
    analyze_first_level_errors,
    write_compact_eval_jsonl,
)


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


def evaluate(
    samples: List[Dict[str, Any]],
    generator: EnhancedCodingGenerator,
    model_manager,
    label: str,
) -> Dict[str, Any]:
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

    # Count how many predictions came from kNN
    knn_count = sum(
        1 for row in result["rows"]
        if row.get("knn_source") == "v11_abstract"
    )
    logger.info("  kNN-sourced preds:    %d (%.1f%%)", knn_count,
                100 * knn_count / max(1, s["sample_count"]))

    error = analyze_first_level_errors(result["rows"])
    logger.info("  Error ratios:")
    for bucket, ratio in sorted(error["bucket_ratios"].items()):
        if ratio > 0:
            logger.info("    %s: %.4f", bucket, ratio)

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-samples", type=int, default=300)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--v11-path", type=str,
                        default=r"C:\Users\Lenovo\Documents\xwechat_files\wxid_eo5dkcv3sf7522_8ac6\msg\file\2026-05\v11_20260428_164754.json")
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--knn-index-dir", type=str, default=None)
    args = parser.parse_args()

    max_samples = None if args.full else args.max_samples
    output_dir = args.output_dir or os.path.join(
        Config.BASE_DIR, "eval_results", "knn_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    )
    os.makedirs(output_dir, exist_ok=True)
    logger.info("Output: %s", output_dir)

    knn_index_dir = args.knn_index_dir or os.path.join(
        Config.BASE_DIR, "cache", "knn_combined_index"
    )

    # ---- Load data ----
    samples = load_samples(args.v11_path, max_samples=max_samples)

    # ---- Setup model manager ----
    model_manager = create_model_manager()

    # ---- Setup generator ----
    generator = EnhancedCodingGenerator()
    generator._ensure_first_level_defaults()

    logger.info("RAG enabled: %s", generator.rag_enabled)
    logger.info("Second threshold: %.4f", generator.rag_second_level_threshold)
    logger.info("Third threshold:  %.4f", generator.rag_third_level_threshold)

    # ================================================================
    # PHASE 1: Build kNN index from v11
    # ================================================================
    logger.info("")
    logger.info("PHASE 1: Building kNN abstract index from v11 ...")
    knn_gen = create_knn_generator(
        v11_path=args.v11_path,
        model_manager=model_manager,
        index_dir=knn_index_dir,
        max_samples=None,  # Use ALL v11 data
        csv_dir=os.path.join(Config.BASE_DIR, "csv"),
    )
    if knn_gen is None:
        logger.error("Failed to build kNN index, aborting")
        return 1

    logger.info("KNN index ready: %d pairs", knn_gen.pair_count)

    # ================================================================
    # PHASE 2: Baseline (no kNN)
    # ================================================================
    logger.info("")
    logger.info("PHASE 2: BASELINE (extractive candidates only)")
    generator.knn_abstract_generator = None
    baseline_result = evaluate(samples, generator, model_manager, "BASELINE")
    write_compact_eval_jsonl(
        os.path.join(output_dir, "baseline_knn_eval.jsonl.gz"), baseline_result["rows"]
    )

    # ================================================================
    # PHASE 3: +kNN (extractive + kNN abstract candidates)
    # ================================================================
    logger.info("")
    logger.info("PHASE 3: +kNN (extractive + v11 abstract retrieval)")
    generator.knn_abstract_generator = knn_gen
    knn_result = evaluate(samples, generator, model_manager, "+KNN")

    write_compact_eval_jsonl(
        os.path.join(output_dir, "knn_eval.jsonl.gz"), knn_result["rows"]
    )

    # ================================================================
    # PHASE 4: +Recall +kNN (all enhancements)
    # ================================================================
    logger.info("")
    logger.info("PHASE 4: +Recall +kNN (recall bank + kNN abstract)")

    recall_prev = bool(getattr(Config, 'FIRST_LEVEL_RECALL_ENHANCED', False))
    use_label_prev = bool(getattr(Config, 'FIRST_LEVEL_USE_LABEL_RECALL_CANDIDATES', False))
    if Config:
        Config.FIRST_LEVEL_RECALL_ENHANCED = True
        Config.FIRST_LEVEL_USE_LABEL_RECALL_CANDIDATES = True

    full_result = evaluate(samples, generator, model_manager, "+RECALL+KNN")
    write_compact_eval_jsonl(
        os.path.join(output_dir, "full_knn_eval.jsonl.gz"), full_result["rows"]
    )

    # Restore config
    if Config:
        Config.FIRST_LEVEL_RECALL_ENHANCED = recall_prev
        Config.FIRST_LEVEL_USE_LABEL_RECALL_CANDIDATES = use_label_prev

    # ================================================================
    # PHASE 5: Report
    # ================================================================
    bs = baseline_result["summary"]
    ks = knn_result["summary"]
    fs = full_result["summary"]

    lines = []
    lines.append("")
    lines.append("=" * 90)
    lines.append("FIRST-LEVEL CODING QUALITY — kNN ABSTRACT GENERATION EVALUATION")
    lines.append("=" * 90)
    lines.append(f"kNN index pairs: {knn_gen.pair_count}")
    lines.append(f"Test samples:    {bs['sample_count']}")
    lines.append("")
    lines.append(f"{'Metric':<24} {'Baseline':>10} {'+kNN':>10} {'+Recall+kNN':>10} {'B→kNN':>10}")
    lines.append("-" * 90)

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
        kv = ks.get(key, 0)
        fv = fs.get(key, 0)
        delta = kv - bv
        lines.append(f"{label:<24} {bv:>10.4f} {kv:>10.4f} {fv:>10.4f} {delta:>+10.4f}")

    lines.append("-" * 90)
    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append(f"Output: {output_dir}")

    report = "\n".join(lines)
    print(report)

    report_path = os.path.join(output_dir, "knn_comparison_report.txt")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(report)
    logger.info("Report saved: %s", report_path)

    logger.info("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
