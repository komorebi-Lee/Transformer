"""Apply first-level coding with kNN enhancement to test interview texts.

Reads all .docx files from D:\zthree2\文本样本, processes each sentence,
and outputs the first-level codes with kNN source info.

Usage:
    D:\anaconda3\envs\zthree5\python.exe code_test_texts.py
    D:\anaconda3\envs\zthree5\python.exe code_test_texts.py --output results.json
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("code_texts")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from data_processor import DataProcessor
from enhanced_coding_generator import EnhancedCodingGenerator
from model_manager import EnhancedModelManager
from knn_abstract_generator import create_knn_generator


def process_test_texts(
    generator: EnhancedCodingGenerator,
    model_manager,
    text_dir: str,
) -> List[Dict[str, Any]]:
    """Process all docx files and return coding results."""
    processor = DataProcessor()
    all_results: List[Dict[str, Any]] = []

    docx_files = sorted([
        f for f in os.listdir(text_dir)
        if f.lower().endswith('.docx') and not f.startswith('~')
    ])

    logger.info("Found %d .docx files in %s", len(docx_files), text_dir)

    for filename in docx_files:
        filepath = os.path.join(text_dir, filename)
        logger.info("Processing: %s", filename)
        try:
            # Read document
            text_content = processor.read_word_file(filepath)
            if not text_content:
                logger.warning("  Empty content: %s", filename)
                continue

            # Split into sentences
            sentences = processor.split_into_sentences(text_content)
            logger.info("  %d sentences extracted", len(sentences))

            file_results = []
            knn_count = 0
            for sent_text in sentences:
                sent_text = str(sent_text or "").strip()
                if not sent_text or len(sent_text) < 4:
                    continue

                trace = generator.build_first_level_candidate_trace(
                    sent_text, model_manager=model_manager
                )
                code = trace.get("selected_candidate", "")
                candidates = trace.get("candidates", [])

                # Check if selected candidate is kNN-sourced
                is_knn = False
                knn_score = 0.0
                for cand in candidates:
                    if cand.get("text") == code and cand.get("knn_source"):
                        is_knn = True
                        knn_score = float(cand.get("knn_score", 0))
                        break

                if is_knn:
                    knn_count += 1

                file_results.append({
                    "sentence": sent_text[:200],
                    "code": code,
                    "is_knn": is_knn,
                    "knn_score": round(knn_score, 4) if is_knn else None,
                    "candidate_count": len(candidates),
                })

            all_results.append({
                "file": filename,
                "sentence_count": len(sentences),
                "coded_count": len([r for r in file_results if r["code"]]),
                "knn_sourced_count": knn_count,
                "results": file_results,
            })

            # Print summary for this file
            coded = len([r for r in file_results if r["code"]])
            logger.info("  Coded: %d/%d (%.1f%%), kNN-sourced: %d (%.1f%%)",
                        coded, len(file_results),
                        100 * coded / max(1, len(file_results)),
                        knn_count,
                        100 * knn_count / max(1, coded))

        except Exception as e:
            logger.error("  Error processing %s: %s", filename, e)
            continue

    return all_results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--text-dir", type=str, default=r"D:\zthree2\文本样本")
    parser.add_argument("--v11-path", type=str,
                        default=r"C:\Users\Lenovo\Documents\xwechat_files\wxid_eo5dkcv3sf7522_8ac6\msg\file\2026-05\v11_20260428_164754.json")
    args = parser.parse_args()

    output_path = args.output or os.path.join(
        Config.BASE_DIR, "eval_results",
        "test_texts_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
    )

    logger.info("Output: %s", output_path)
    logger.info("Text dir: %s", args.text_dir)

    # ---- Setup ----
    model_manager = EnhancedModelManager()
    if not model_manager.is_abstract_reranker_available():
        model_manager.ensure_abstract_reranker_loaded()
    logger.info("Abstract reranker: %s", model_manager.is_abstract_reranker_available())

    generator = EnhancedCodingGenerator()
    generator._ensure_first_level_defaults()

    # ---- Build kNN index ----
    logger.info("Building kNN abstract index ...")
    knn_gen = create_knn_generator(
        v11_path=args.v11_path,
        model_manager=model_manager,
        max_samples=None,  # Use ALL v11 + CSV data
        csv_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "csv"),
    )
    if knn_gen:
        generator.knn_abstract_generator = knn_gen
        logger.info("kNN index ready: %d pairs", knn_gen.pair_count)
    else:
        logger.warning("kNN index unavailable, using extractive only")

    # ---- Process texts ----
    t0 = time.time()
    results = process_test_texts(generator, model_manager, args.text_dir)
    elapsed = time.time() - t0

    # ---- Summary ----
    total_sentences = sum(r["sentence_count"] for r in results)
    total_coded = sum(r["coded_count"] for r in results)
    total_knn = sum(r["knn_sourced_count"] for r in results)

    logger.info("=" * 60)
    logger.info("SUMMARY: %d files, %d sentences, %.1fs",
                len(results), total_sentences, elapsed)
    logger.info("  Total coded: %d (%.1f%%)",
                total_coded, 100 * total_coded / max(1, total_sentences))
    logger.info("  kNN-sourced: %d (%.1f%% of coded)",
                total_knn, 100 * total_knn / max(1, total_coded))

    # ---- Save ----
    output = {
        "generated": datetime.now().isoformat(),
        "text_dir": args.text_dir,
        "knn_pairs": knn_gen.pair_count if knn_gen else 0,
        "summary": {
            "total_files": len(results),
            "total_sentences": total_sentences,
            "total_coded": total_coded,
            "total_knn_sourced": total_knn,
            "coding_rate": round(total_coded / max(1, total_sentences), 4),
            "knn_rate": round(total_knn / max(1, total_coded), 4) if total_coded else 0,
            "elapsed_seconds": round(elapsed, 1),
        },
        "files": results,
    }

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)
    logger.info("Results saved: %s", output_path)

    # ---- Print per-file breakdown ----
    print("\n" + "=" * 80)
    print("PER-FILE CODING RESULTS")
    print("=" * 80)
    print(f"{'File':<30} {'Sentences':>10} {'Coded':>10} {'Rate':>8} {'kNN':>8}")
    print("-" * 80)
    for r in results:
        rate = 100 * r["coded_count"] / max(1, r["sentence_count"])
        print(f"{r['file']:<30} {r['sentence_count']:>10} {r['coded_count']:>10} {rate:>7.1f}% {r['knn_sourced_count']:>8}")
    print("-" * 80)
    print(f"{'TOTAL':<30} {total_sentences:>10} {total_coded:>10} "
          f"{100*total_coded/max(1,total_sentences):>7.1f}% {total_knn:>8}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
