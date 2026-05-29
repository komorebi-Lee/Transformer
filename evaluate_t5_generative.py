"""Evaluate t5-pegasus generative coding vs extractive+kNN coding.

Uses the pretrained t5 model (no fine-tuning) to generate abstract code candidates
via beam search, then compares first-level coding quality:

  Phase 1: Extractive only (baseline)
  Phase 2: +kNN (extractive + v11+CSV memory bank)
  Phase 3: +kNN + t5 generative (extractive + kNN + t5 beam search)

Usage:
    D:\anaconda3\envs\zthree5\python.exe evaluate_t5_generative.py --max-samples 500
    D:\anaconda3\envs\zthree5\python.exe evaluate_t5_generative.py --full
"""

import argparse
import json
import logging
import os
import random
import sys
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eval_t5gen")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from enhanced_coding_generator import EnhancedCodingGenerator
from model_manager import EnhancedModelManager
from knn_abstract_generator import create_knn_generator
from first_level_eval import (
    evaluate_first_level_full,
    analyze_first_level_errors,
    write_compact_eval_jsonl,
)


# ------------------------------------------------------------------
# t5 generative candidate generator
# ------------------------------------------------------------------

class T5GenerativeCoder:
    """Use pretrained or LoRA-fine-tuned t5-pegasus to generate abstract code candidates."""

    def __init__(self, device="cuda", lora_weights_path: Optional[str] = None):
        import jieba
        jieba.initialize()
        from bert4torch.models import build_transformer_model
        from bert4torch.tokenizers import Tokenizer
        import torch

        model_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "local_models", "chinese_t5_pegasus_base",
        )
        self.tokenizer = Tokenizer(
            os.path.join(model_dir, "vocab.txt"),
            do_lower_case=True,
            pre_tokenize=lambda s: list(jieba.cut(s, HMM=False)),
        )
        self.model = build_transformer_model(
            config_path=os.path.join(model_dir, "bert4torch_config.json"),
            checkpoint_path=os.path.join(model_dir, "pytorch_model.bin"),
            model="mt5.1.1",
        )
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")

        self._lora_applied = False
        if lora_weights_path and os.path.exists(lora_weights_path):
            from train_t5_lora import apply_lora_to_t5
            n_lora = apply_lora_to_t5(self.model, r=8, alpha=16.0, dropout=0.05)
            lora_state = torch.load(lora_weights_path, map_location="cpu")
            model_state = self.model.state_dict()
            loaded = 0
            for key, val in lora_state.items():
                if key in model_state:
                    model_state[key].copy_(val)
                    loaded += 1
            logger.info("LoRA weights loaded: %d params from %s", loaded, lora_weights_path)
            self._lora_applied = True

        self.model.to(self.device)
        self.model.eval()
        self._torch = torch
        n_params = sum(p.numel() for p in self.model.parameters())
        trainable = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        tag = "LoRA" if self._lora_applied else "pretrained"
        logger.info("T5GenerativeCoder [%s]: %.1fM params (%.2fM trainable) on %s",
                    tag, n_params / 1e6, trainable / 1e6, self.device)

    @property
    def torch(self):
        return self._torch

    def generate(self, text: str, num_beams: int = 5, max_len: int = 32,
                 num_return: int = 5) -> List[Dict[str, Any]]:
        """Generate abstract code candidates via beam search.

        Returns list of {"text": code, "score": normalized_beam_score}
        """
        src_ids, _ = self.tokenizer.encode(text, maxlen=256)
        src_tensor = self.torch.tensor([src_ids], dtype=self.torch.long).to(self.device)

        try:
            outputs = self.model.generate(
                src_tensor,
                max_new_tokens=max_len,
                num_beams=num_beams * 2,
                num_return_sequences=min(num_return, num_beams * 2),
                eos_token_id=self.tokenizer._token_end_id,
                pad_token_id=self.tokenizer._token_pad_id,
                bos_token_id=self.tokenizer._token_start_id,
                output_scores=True,
                return_dict_in_generate=True,
            )
        except Exception:
            # Fallback: simpler generation without scores
            outputs = self.model.generate(
                src_tensor,
                max_new_tokens=max_len,
                num_beams=num_beams,
                eos_token_id=self.tokenizer._token_end_id,
                pad_token_id=self.tokenizer._token_pad_id,
                bos_token_id=self.tokenizer._token_start_id,
            )

        results: List[Dict[str, Any]] = []
        seen: set = set()

        seqs = outputs if isinstance(outputs, list) else (
            outputs.sequences if hasattr(outputs, 'sequences') else outputs
        )

        # Get beam scores if available
        scores_list = []
        if hasattr(outputs, 'sequences_scores'):
            scores_list = outputs.sequences_scores.cpu().tolist()

        for i, seq in enumerate(seqs):
            if hasattr(seq, 'tolist'):
                seq = seq.tolist()
            code = self.tokenizer.decode(seq).strip()
            if not code or code in seen:
                continue
            seen.add(code)
            score = float(scores_list[i]) if i < len(scores_list) else 0.0
            results.append({"text": code, "score": round(score, 4)})

        return results


def load_samples(v11_path: str, max_samples: Optional[int] = None) -> List[Dict[str, Any]]:
    with open(v11_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    training_data = data.get("training_data", [])
    if max_samples and len(training_data) > max_samples:
        random.seed(42)
        training_data = random.sample(training_data, max_samples)
    return training_data


# ------------------------------------------------------------------
# Evaluation with t5 generative candidates injected
# ------------------------------------------------------------------

def evaluate_with_t5(
    samples: List[Dict[str, Any]],
    generator: EnhancedCodingGenerator,
    model_manager,
    label: str,
) -> Dict[str, Any]:
    """Evaluate first-level coding with current generator configuration."""
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

    # Count source of predictions
    t5_count = sum(1 for row in result["rows"] if row.get("knn_source") == "t5_generated")
    knn_count = sum(1 for row in result["rows"] if row.get("knn_source") == "v11_abstract")
    logger.info("  t5-generated preds:   %d (%.1f%%)", t5_count,
                100 * t5_count / max(1, s["sample_count"]))
    logger.info("  kNN-sourced preds:    %d (%.1f%%)", knn_count,
                100 * knn_count / max(1, s["sample_count"]))

    error = analyze_first_level_errors(result["rows"])
    logger.info("  Error ratios:")
    for bucket, ratio in sorted(error["bucket_ratios"].items()):
        if ratio > 0:
            logger.info("    %s: %.4f", bucket, ratio)

    return result


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-samples", type=int, default=500)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--v11-path", type=str,
                        default=r"C:\Users\Lenovo\Documents\xwechat_files\wxid_eo5dkcv3sf7522_8ac6\msg\file\2026-05\v11_20260428_164754.json")
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--skip-t5", action="store_true",
                        help="Skip all t5 evaluation (only test baseline + kNN)")
    parser.add_argument("--test-pretrained-t5", action="store_true",
                        help="Also test pretrained t5 (without LoRA)")
    parser.add_argument("--lora-path", type=str,
                        default=r"D:\zthree2\trained_models\t5_lora_coding\lora_weights.pt",
                        help="Path to LoRA weights")
    args = parser.parse_args()

    max_samples = None if args.full else args.max_samples
    output_dir = args.output_dir or os.path.join(
        Config.BASE_DIR, "eval_results",
        "t5lora_" + datetime.now().strftime("%Y%m%d_%H%M%S"),
    )
    os.makedirs(output_dir, exist_ok=True)

    # ---- Load data ----
    samples = load_samples(args.v11_path, max_samples=max_samples)
    logger.info("Test samples: %d", len(samples))

    # ---- Setup ----
    model_manager = EnhancedModelManager()
    if not model_manager.is_abstract_reranker_available():
        model_manager.ensure_abstract_reranker_loaded()

    generator = EnhancedCodingGenerator()
    generator._ensure_first_level_defaults()

    # ---- Build kNN index ----
    knn_gen = create_knn_generator(
        v11_path=args.v11_path,
        model_manager=model_manager,
        csv_dir=os.path.join(Config.BASE_DIR, "csv"),
    )
    if knn_gen:
        generator.knn_abstract_generator = knn_gen
        logger.info("kNN index: %d pairs", knn_gen.pair_count)

    # ---- Load t5 coders ----
    t5_pretrained = None
    t5_lora = None
    if not args.skip_t5:
        if args.test_pretrained_t5:
            logger.info("Loading pretrained t5-pegasus ...")
            t5_pretrained = T5GenerativeCoder()
        logger.info("Loading LoRA-tuned t5-pegasus ...")
        t5_lora = T5GenerativeCoder(lora_weights_path=args.lora_path)

    # ================================================================
    # PHASE 1: Baseline (extractive only, no kNN)
    # ================================================================
    logger.info("")
    logger.info("PHASE 1: BASELINE (extractive only, no kNN)")
    generator.knn_abstract_generator = None
    generator.t5_generative_coder = None
    baseline = evaluate_with_t5(
        samples, generator, model_manager, "BASELINE"
    )
    write_compact_eval_jsonl(
        os.path.join(output_dir, "baseline.jsonl.gz"), baseline["rows"]
    )

    # ================================================================
    # PHASE 2: +kNN (current best)
    # ================================================================
    logger.info("")
    logger.info("PHASE 2: +kNN (extractive + v11+CSV memory bank)")
    generator.knn_abstract_generator = knn_gen
    generator.t5_generative_coder = None
    knn_result = evaluate_with_t5(
        samples, generator, model_manager, "+KNN"
    )
    write_compact_eval_jsonl(
        os.path.join(output_dir, "knn.jsonl.gz"), knn_result["rows"]
    )

    # ================================================================
    # PHASE 3: +kNN + pretrained t5 (optional)
    # ================================================================
    pretrained_result = None
    if t5_pretrained is not None:
        logger.info("")
        logger.info("PHASE 3: +kNN + pretrained t5 (extractive + kNN + pretrained t5 beam search)")
        generator.knn_abstract_generator = knn_gen
        generator.t5_generative_coder = t5_pretrained
        pretrained_result = evaluate_with_t5(
            samples, generator, model_manager, "+KNN+pretrained-T5"
        )
        write_compact_eval_jsonl(
            os.path.join(output_dir, "knn_pretrained_t5.jsonl.gz"), pretrained_result["rows"]
        )

    # ================================================================
    # PHASE 4: +kNN + LoRA-t5
    # ================================================================
    lora_result = None
    if t5_lora is not None:
        logger.info("")
        logger.info("PHASE 4: +kNN + LoRA-t5 (extractive + kNN + LoRA-tuned t5 beam search)")
        generator.knn_abstract_generator = knn_gen
        generator.t5_generative_coder = t5_lora
        lora_result = evaluate_with_t5(
            samples, generator, model_manager, "+KNN+LoRA-T5"
        )
        write_compact_eval_jsonl(
            os.path.join(output_dir, "knn_lora_t5.jsonl.gz"), lora_result["rows"]
        )

    # ================================================================
    # Report
    # ================================================================
    bs = baseline["summary"]
    ks = knn_result["summary"]

    lines = []
    lines.append("")
    lines.append("=" * 100)
    lines.append("FIRST-LEVEL CODING — LoRA-t5 vs BASELINE vs +kNN")
    lines.append("=" * 100)
    lines.append(f"KNN index pairs:  {knn_gen.pair_count if knn_gen else 0}")
    lines.append(f"Test samples:     {bs['sample_count']}")
    lines.append("")

    # Build table header
    ncols = 2  # Baseline, +kNN always present
    if pretrained_result:
        ncols += 1
    if lora_result:
        ncols += 2  # +kNN+LoRA-T5 and kNN→LoRA
    header = f"{'Metric':<24} {'Baseline':>10} {'+kNN':>10}"
    if pretrained_result:
        header += f" {'+kNN+preT5':>12}"
    if lora_result:
        header += f" {'+kNN+LoRA':>11} {'Δvs+kNN':>9}"
    lines.append(header)
    lines.append("-" * 100)

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
        row = f"{label:<24} {bv:>10.4f} {kv:>10.4f}"
        if pretrained_result:
            pv = pretrained_result["summary"].get(key, 0)
            row += f" {pv:>12.4f}"
        if lora_result:
            lv = lora_result["summary"].get(key, 0)
            delta = lv - kv
            row += f" {lv:>11.4f} {delta:>+9.4f}"
        lines.append(row)

    lines.append("-" * 100)

    # Source stats
    if lora_result:
        t5_count = sum(1 for row in lora_result["rows"] if row.get("knn_source") == "t5_generated")
        knn_count = sum(1 for row in lora_result["rows"] if row.get("knn_source") == "v11_abstract")
        lines.append(f"LoRA-t5: {t5_count} t5-generated preds ({100*t5_count/max(1,bs['sample_count']):.1f}%), "
                     f"{knn_count} kNN-sourced preds ({100*knn_count/max(1,bs['sample_count']):.1f}%)")

    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append(f"Output: {output_dir}")

    report = "\n".join(lines)
    print(report)

    report_path = os.path.join(output_dir, "t5_lora_report.txt")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(report)
    logger.info("Report saved: %s", report_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
