"""Dynamic threshold optimization for first-level coding.

iQual-inspired: grid-search over threshold values to find F1-optimal
settings from labeled training data.

Usage:
    optimizer = ThresholdOptimizer(generator, model_manager)
    results = optimizer.optimize_all(samples)
    optimizer.apply_best(results)
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from first_level_eval import evaluate_first_level_full

logger = logging.getLogger(__name__)


class ThresholdOptimizer:
    """Grid-search optimal thresholds using v11 labeled data."""

    def __init__(self, generator, model_manager=None):
        self.generator = generator
        self.model_manager = model_manager

    # ------------------------------------------------------------------
    # Single-threshold search
    # ------------------------------------------------------------------

    def optimize(
        self,
        samples: List[Dict[str, Any]],
        threshold_key: str,
        search_range: Tuple[float, float, float] = (0.25, 0.75, 0.05),
        metric: str = "exact_micro_f1",

    ) -> Dict[str, Any]:
        """Search for best value of a single threshold parameter.

        Args:
            samples: List of labeled samples from v11 training_data.
            threshold_key: Config attribute name (e.g. "second_threshold").
            search_range: (start, end, step).
            metric: Which evaluation metric to maximize.

        Returns:
            Dict with best_threshold, best_score, and full search curve.
        """
        original = self._get_threshold(threshold_key)
        start, end, step = search_range
        results: List[Dict[str, Any]] = []

        threshold_val = start
        while threshold_val <= end + 1e-9:
            self._set_threshold(threshold_key, threshold_val)
            eval_result = evaluate_first_level_full(
                samples, self.generator, model_manager=self.model_manager,
            )
            score = eval_result["summary"].get(metric, 0.0)
            results.append({
                "threshold": round(threshold_val, 4),
                "score": round(score, 4),
                "top1_accuracy": eval_result["summary"].get("top1_accuracy", 0.0),
                "relaxed_f1": eval_result["summary"].get("relaxed_f1", 0.0),
            })
            threshold_val += step

        # Restore original
        if original is not None:
            self._set_threshold(threshold_key, original)

        results.sort(key=lambda r: r["score"], reverse=True)
        best = results[0] if results else {}

        logger.info(
            "ThresholdOptimizer: %s best=%.4f (score=%.4f), original=%.4f",
            threshold_key,
            best.get("threshold", 0),
            best.get("score", 0),
            original or 0,
        )
        return {
            "threshold_key": threshold_key,
            "best_threshold": best.get("threshold"),
            "best_score": best.get("score"),
            "original_threshold": original,
            "metric": metric,
            "search_results": results,
        }

    # ------------------------------------------------------------------
    # Multi-threshold optimization
    # ------------------------------------------------------------------

    def optimize_all(
        self,
        samples: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Optimize all relevant thresholds sequentially.

        The thresholds are independent enough that sequential search is
        sufficient (no combinatorial explosion).
        """
        threshold_configs = [
            ("second_threshold", (0.25, 0.70, 0.05)),
            ("third_threshold", (0.25, 0.70, 0.05)),
            ("cluster_threshold", (0.55, 0.95, 0.05)),
        ]

        all_results: Dict[str, Any] = {}
        for key, search_range in threshold_configs:
            logger.info("Optimizing %s in range %s ...", key, search_range)
            result = self.optimize(samples, key, search_range=search_range)
            all_results[key] = result

        # Summary
        summary_lines = []
        for key, result in all_results.items():
            orig = result.get("original_threshold", "N/A")
            best = result.get("best_threshold", "N/A")
            best_score = result.get("best_score", 0)
            changed = "CHANGED" if orig != best else "unchanged"
            summary_lines.append(
                f"  {key}: {orig} → {best} (F1={best_score:.4f}) [{changed}]"
            )

        logger.info("Threshold optimization complete:\n%s", "\n".join(summary_lines))
        return {
            "results": all_results,
            "summary": summary_lines,
            "optimized_at": datetime.now().isoformat(),
        }

    def apply_best(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Apply the optimized thresholds to the generator."""
        applied: Dict[str, Any] = {}
        for key, result in results.get("results", {}).items():
            best = result.get("best_threshold")
            if best is not None:
                self._set_threshold(key, best)
                applied[key] = best
        return applied

    def save_report(self, results: Dict[str, Any], path: str) -> None:
        """Save optimization results to JSON."""
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=2)
        logger.info("Threshold optimization report saved to %s", path)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_threshold(self, key: str) -> Optional[float]:
        attr_map = {
            "second_threshold": "rag_second_level_threshold",
            "third_threshold": "rag_third_level_threshold",
            "cluster_threshold": "rag_cluster_similarity_threshold",
        }
        attr = attr_map.get(key, key)
        return getattr(self.generator, attr, None)

    def _set_threshold(self, key: str, value: float) -> None:
        self.generator.configure_similarity_thresholds(**{key: value})


def optimize_from_v11(
    v11_path: str,
    generator,
    model_manager=None,
    max_samples: int = 500,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Convenience: load v11 data, optimize thresholds, optionally save report.

    Args:
        v11_path: Path to v11 JSON file.
        generator: EnhancedCodingGenerator instance.
        model_manager: Optional model manager.
        max_samples: Max samples to use (for speed).
        output_path: If set, save JSON report to this path.

    Returns:
        Optimization results dict.
    """
    with open(v11_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    training_data = data.get("training_data", [])
    if not training_data:
        raise ValueError("No training_data found in v11 JSON")

    # Use a subset for speed
    if max_samples and len(training_data) > max_samples:
        import random
        random.seed(42)
        training_data = random.sample(training_data, max_samples)
        logger.info("Using %d samples for threshold optimization", max_samples)

    optimizer = ThresholdOptimizer(generator, model_manager=model_manager)
    results = optimizer.optimize_all(training_data)

    if output_path:
        optimizer.save_report(results, output_path)

    return results


def compare_optimal_vs_current(
    v11_path: str,
    generator,
    model_manager=None,
    max_samples: int = 500,
) -> Dict[str, Any]:
    """Full before/after comparison with threshold optimization.

    1. Evaluate with current (before) thresholds
    2. Find optimal thresholds
    3. Apply optimal thresholds
    4. Evaluate with optimal (after) thresholds
    5. Return diff report
    """
    with open(v11_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    training_data = data.get("training_data", [])
    if not training_data:
        raise ValueError("No training_data found")

    if max_samples and len(training_data) > max_samples:
        import random
        random.seed(42)
        training_data = random.sample(training_data, max_samples)

    # Before
    before_eval = evaluate_first_level_full(
        training_data, generator, model_manager=model_manager,
    )
    before_summary = before_eval["summary"]

    # Optimize
    optimizer = ThresholdOptimizer(generator, model_manager=model_manager)
    opt_results = optimizer.optimize_all(training_data)
    optimizer.apply_best(opt_results)

    # After
    after_eval = evaluate_first_level_full(
        training_data, generator, model_manager=model_manager,
    )
    after_summary = after_eval["summary"]

    # Diff
    diff = {
        "top1_accuracy": {
            "before": before_summary["top1_accuracy"],
            "after": after_summary["top1_accuracy"],
            "delta": round(after_summary["top1_accuracy"] - before_summary["top1_accuracy"], 4),
        },
        "exact_micro_f1": {
            "before": before_summary["exact_micro_f1"],
            "after": after_summary["exact_micro_f1"],
            "delta": round(after_summary["exact_micro_f1"] - before_summary["exact_micro_f1"], 4),
        },
        "relaxed_f1": {
            "before": before_summary["relaxed_f1"],
            "after": after_summary["relaxed_f1"],
            "delta": round(after_summary["relaxed_f1"] - before_summary["relaxed_f1"], 4),
        },
        "relaxed_precision": {
            "before": before_summary["relaxed_precision"],
            "after": after_summary["relaxed_precision"],
            "delta": round(after_summary["relaxed_precision"] - before_summary["relaxed_precision"], 4),
        },
        "relaxed_recall": {
            "before": before_summary["relaxed_recall"],
            "after": after_summary["relaxed_recall"],
            "delta": round(after_summary["relaxed_recall"] - before_summary["relaxed_recall"], 4),
        },
        "optimized_thresholds": {
            k: {"before": v["original_threshold"], "after": v["best_threshold"]}
            for k, v in opt_results["results"].items()
        },
    }

    return {
        "before_summary": before_summary,
        "after_summary": after_summary,
        "diff": diff,
        "opt_results": opt_results,
        "sample_count": len(training_data),
    }
