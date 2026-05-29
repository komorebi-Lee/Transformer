import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np


def _normalize_text(text: Any) -> str:
    return "".join(str(text or "").strip().split())


def _relaxed_match(pred_norm: str, gold_norm: str) -> bool:
    if not pred_norm or not gold_norm:
        return False
    return pred_norm == gold_norm or pred_norm in gold_norm or gold_norm in pred_norm


def _compact_candidates(candidates: List[Dict[str, Any]], top_n: Optional[int] = None) -> List[Dict[str, Any]]:
    items = candidates[:top_n] if isinstance(top_n, int) and top_n > 0 else candidates
    compact_rows: List[Dict[str, Any]] = []
    for item in items:
        compact_rows.append(
            {
                "t": item.get("text", ""),
                "rs": item.get("rule_score"),
                "rr": item.get("rerank_score"),
                "s": 1 if item.get("selected") else 0,
                "h": 1 if item.get("best_rule") else 0,
            }
        )
    return compact_rows


def evaluate_first_level_candidates(
    samples: Iterable[Dict[str, Any]],
    generator,
    model_manager=None,
    top_n: int = 5,
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    sample_count = 0
    hit_at_k = 0
    top1_hit = 0
    top1_relaxed_hit = 0
    hit_at_k_relaxed = 0
    rerank_used = 0

    for sample in samples:
        if not isinstance(sample, dict):
            continue
        source = sample.get("input_sentences", {}) or {}
        original = str(source.get("original_content") or sample.get("text") or "").strip()
        gold = str(sample.get("target_abstract") or "").strip()
        if not original or not gold:
            continue

        sample_count += 1
        trace = generator.build_first_level_candidate_trace(original, model_manager=model_manager, top_n=None)
        pred = trace.get("selected_candidate", "")
        candidates = trace.get("candidates", [])
        if trace.get("used_rerank"):
            rerank_used += 1

        gold_norm = _normalize_text(gold)
        pred_norm = _normalize_text(pred)
        candidate_norms = [_normalize_text(item.get("text", "")) for item in candidates]

        top1 = bool(pred_norm and pred_norm == gold_norm)
        top1_relaxed = _relaxed_match(pred_norm, gold_norm)
        topk = gold_norm in candidate_norms if gold_norm else False
        topk_relaxed = any(_relaxed_match(cn, gold_norm) for cn in candidate_norms) if gold_norm else False
        if top1:
            top1_hit += 1
        if top1_relaxed:
            top1_relaxed_hit += 1
        if topk:
            hit_at_k += 1
        if topk_relaxed:
            hit_at_k_relaxed += 1

        if top1:
            match_type = "top1_hit"
        elif topk:
            match_type = "recall_hit_rerank_miss"
        else:
            match_type = "candidate_miss"

        # Determine knn_source from the selected candidate
        _knn_src = None
        for cand in candidates:
            if cand.get("text") == pred and cand.get("knn_source"):
                _knn_src = cand.get("knn_source")
                break

        rows.append(
            {
                "o": original,
                "g": gold,
                "p": pred,
                "m": match_type,
                "u": 1 if trace.get("used_rerank") else 0,
                "c": _compact_candidates(candidates, top_n=top_n),
                "knn_source": _knn_src,
            }
        )

    summary = {
        "sample_count": sample_count,
        "top1_accuracy": round(top1_hit / sample_count, 4) if sample_count else 0.0,
        "top1_relaxed_accuracy": round(top1_relaxed_hit / sample_count, 4) if sample_count else 0.0,
        "hit_at_{}".format(top_n): round(hit_at_k / sample_count, 4) if sample_count else 0.0,
        "hit_at_{}_relaxed".format(top_n): round(hit_at_k_relaxed / sample_count, 4) if sample_count else 0.0,
        "rerank_used_ratio": round(rerank_used / sample_count, 4) if sample_count else 0.0,
    }
    return {"summary": summary, "rows": rows}


def write_compact_eval_jsonl(output_path: Path, rows: List[Dict[str, Any]]) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if path.suffix == ".gz" or path.name.endswith(".jsonl.gz") else open
    mode = "wt"
    with opener(path, mode, encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def evaluate_first_level_full(
    samples: Iterable[Dict[str, Any]],
    generator,
    model_manager=None,
    top_n: int = 5,
) -> Dict[str, Any]:
    """Comprehensive evaluation with precision/recall/F1/confusion matrix.

    Treats each (gold_code, pred_code) pair as a classification instance.
    Computes exact match and relaxed match variants.
    """
    rows: List[Dict[str, Any]] = []
    y_true: List[str] = []
    y_pred: List[str] = []
    sample_count = 0
    hit_at_k = 0
    top1_hit = 0
    top1_relaxed_hit = 0
    hit_at_k_relaxed = 0
    rerank_used = 0

    for sample in samples:
        if not isinstance(sample, dict):
            continue
        source = sample.get("input_sentences", {}) or {}
        original = str(source.get("original_content") or sample.get("text") or "").strip()
        gold = str(sample.get("target_abstract") or "").strip()
        if not original or not gold:
            continue

        sample_count += 1
        trace = generator.build_first_level_candidate_trace(original, model_manager=model_manager, top_n=None)
        pred = trace.get("selected_candidate", "")
        candidates = trace.get("candidates", [])
        if trace.get("used_rerank"):
            rerank_used += 1

        gold_norm = _normalize_text(gold)
        pred_norm = _normalize_text(pred)
        y_true.append(gold_norm)
        y_pred.append(pred_norm)

        candidate_norms = [_normalize_text(item.get("text", "")) for item in candidates]

        top1 = bool(pred_norm and pred_norm == gold_norm)
        top1_relaxed = _relaxed_match(pred_norm, gold_norm)
        topk = gold_norm in candidate_norms if gold_norm else False
        topk_relaxed = any(_relaxed_match(cn, gold_norm) for cn in candidate_norms) if gold_norm else False
        if top1:
            top1_hit += 1
        if top1_relaxed:
            top1_relaxed_hit += 1
        if topk:
            hit_at_k += 1
        if topk_relaxed:
            hit_at_k_relaxed += 1

        if top1:
            match_type = "top1_hit"
        elif topk:
            match_type = "recall_hit_rerank_miss"
        else:
            match_type = "candidate_miss"

        # Determine knn_source from the selected candidate
        _knn_src = None
        for cand in candidates:
            if cand.get("text") == pred and cand.get("knn_source"):
                _knn_src = cand.get("knn_source")
                break

        rows.append(
            {
                "o": original,
                "g": gold,
                "p": pred,
                "m": match_type,
                "u": 1 if trace.get("used_rerank") else 0,
                "c": _compact_candidates(candidates, top_n=top_n),
                "knn_source": _knn_src,
            }
        )

    # Build per-class metrics
    all_labels = sorted(set(y_true) | set(y_pred))
    per_class: Dict[str, Dict[str, Any]] = {}
    cm_exact: Dict[str, Dict[str, int]] = {}

    for label in all_labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        f1 = 2 * precision * recall / max(1e-9, precision + recall)
        per_class[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": tp + fn,
        }

    # Confusion matrix (top-N by frequency)
    label_freq = Counter(y_true)
    top_labels = [label for label, _ in label_freq.most_common(50)]
    for true_label in top_labels:
        cm_exact[true_label] = {}
        for pred_label in top_labels:
            cm_exact[true_label][pred_label] = sum(
                1 for t, p in zip(y_true, y_pred) if t == true_label and p == pred_label
            )

    # Micro/macro averages
    micro_tp = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    micro_precision = micro_tp / max(1, sample_count)
    micro_recall = micro_tp / max(1, sample_count)
    micro_f1 = micro_tp / max(1, sample_count)

    macro_precision = np.mean([v["precision"] for v in per_class.values()]) if per_class else 0.0
    macro_recall = np.mean([v["recall"] for v in per_class.values()]) if per_class else 0.0
    macro_f1 = np.mean([v["f1"] for v in per_class.values()]) if per_class else 0.0

    # Relaxed (subset-based) F1
    relaxed_tp = sum(1 for t, p in zip(y_true, y_pred) if _relaxed_match(p, t))
    relaxed_precision = relaxed_tp / max(1, sum(1 for p in y_pred if p))
    relaxed_recall = relaxed_tp / max(1, sum(1 for t in y_true if t))
    relaxed_f1 = 2 * relaxed_precision * relaxed_recall / max(1e-9, relaxed_precision + relaxed_recall)

    summary = {
        "sample_count": sample_count,
        "top1_accuracy": round(top1_hit / sample_count, 4) if sample_count else 0.0,
        "top1_relaxed_accuracy": round(top1_relaxed_hit / sample_count, 4) if sample_count else 0.0,
        f"hit_at_{top_n}": round(hit_at_k / sample_count, 4) if sample_count else 0.0,
        f"hit_at_{top_n}_relaxed": round(hit_at_k_relaxed / sample_count, 4) if sample_count else 0.0,
        "rerank_used_ratio": round(rerank_used / sample_count, 4) if sample_count else 0.0,
        # New comprehensive metrics
        "exact_micro_precision": round(micro_precision, 4),
        "exact_micro_recall": round(micro_recall, 4),
        "exact_micro_f1": round(micro_f1, 4),
        "exact_macro_precision": round(float(macro_precision), 4),
        "exact_macro_recall": round(float(macro_recall), 4),
        "exact_macro_f1": round(float(macro_f1), 4),
        "relaxed_precision": round(relaxed_precision, 4),
        "relaxed_recall": round(relaxed_recall, 4),
        "relaxed_f1": round(relaxed_f1, 4),
        "unique_gold_labels": len(set(y_true)),
        "unique_pred_labels": len(set(y_pred)),
    }
    return {
        "summary": summary,
        "rows": rows,
        "per_class": per_class,
        "confusion_matrix": cm_exact,
    }


def calibrate_threshold(
    samples: List[Dict[str, Any]],
    generator,
    model_manager=None,
    threshold_key: str = "second_threshold",
    search_range: Tuple[float, float, float] = (0.25, 0.70, 0.05),
) -> Dict[str, Any]:
    """Grid-search optimal threshold from labeled data (iQual BinaryThresholder pattern).

    threshold_key: one of "second_threshold", "third_threshold", "cluster_threshold"
    """
    start, end, step = search_range
    candidates = []
    best_threshold = None
    best_f1 = -1.0
    results: List[Dict[str, Any]] = []

    threshold_val = start
    while threshold_val <= end + 1e-9:
        generator.configure_similarity_thresholds(**{threshold_key: threshold_val})
        eval_result = evaluate_first_level_full(samples, generator, model_manager=model_manager)
        f1 = eval_result["summary"].get("exact_micro_f1", 0.0)
        results.append({
            "threshold": round(threshold_val, 4),
            "f1": f1,
            "top1_accuracy": eval_result["summary"].get("top1_accuracy", 0.0),
            "relaxed_f1": eval_result["summary"].get("relaxed_f1", 0.0),
        })
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = round(threshold_val, 4)
        threshold_val += step

    # Restore original threshold
    results.sort(key=lambda r: r["f1"], reverse=True)
    return {
        "threshold_key": threshold_key,
        "best_threshold": best_threshold,
        "best_f1": best_f1,
        "search_results": results,
    }


def compare_before_after(
    before_path: str,
    after_path: str,
) -> Dict[str, Any]:
    """Compare two eval JSONL files and produce a diff report."""
    def _load(path: str) -> List[Dict[str, Any]]:
        rows = []
        opener = gzip.open if path.endswith(".gz") else open
        with opener(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    before_rows = _load(before_path)
    after_rows = _load(after_path)

    before_hits = sum(1 for r in before_rows if r.get("m") == "top1_hit")
    after_hits = sum(1 for r in after_rows if r.get("m") == "top1_hit")
    before_count = len(before_rows)
    after_count = len(after_rows)

    # Track transitions
    fixed = 0   # was miss, now hit
    broken = 0  # was hit, now miss
    for br, ar in zip(before_rows, after_rows):
        b_hit = br.get("m") == "top1_hit"
        a_hit = ar.get("m") == "top1_hit"
        if not b_hit and a_hit:
            fixed += 1
        if b_hit and not a_hit:
            broken += 1

    before_acc = before_hits / max(1, before_count)
    after_acc = after_hits / max(1, after_count)

    return {
        "before_samples": before_count,
        "after_samples": after_count,
        "before_accuracy": round(before_acc, 4),
        "after_accuracy": round(after_acc, 4),
        "accuracy_delta": round(after_acc - before_acc, 4),
        "fixed_count": fixed,
        "broken_count": broken,
        "net_improvement": fixed - broken,
    }


def analyze_first_level_errors(rows: List[Dict[str, Any]], top_n_examples: int = 5) -> Dict[str, Any]:
    """Bucket first-level failures for quick diagnosis."""
    def _is_empty(v: Any) -> bool:
        return not str(v or "").strip()

    def _len(s: Any) -> int:
        return len(str(s or "").strip())

    bucket_counts = {
        "top1_hit": 0,
        "candidate_miss": 0,
        "rerank_miss": 0,
        "empty_prediction": 0,
        "too_long_prediction": 0,
        "low_rerank_confidence": 0,
        "contains_pronoun_or_modal": 0,
    }
    examples = {k: [] for k in bucket_counts.keys()}

    for row in rows or []:
        m = str(row.get("m", "") or "")
        p = str(row.get("p", "") or "")
        g = str(row.get("g", "") or "")
        cands = row.get("c", []) or []

        if m == "top1_hit":
            bucket_counts["top1_hit"] += 1
            continue

        if m == "candidate_miss":
            bucket_counts["candidate_miss"] += 1
            if len(examples["candidate_miss"]) < top_n_examples:
                examples["candidate_miss"].append({"g": g, "p": p, "c": cands[:3]})
        elif m == "recall_hit_rerank_miss":
            bucket_counts["rerank_miss"] += 1
            if len(examples["rerank_miss"]) < top_n_examples:
                examples["rerank_miss"].append({"g": g, "p": p, "c": cands[:3]})

        if _is_empty(p):
            bucket_counts["empty_prediction"] += 1
            if len(examples["empty_prediction"]) < top_n_examples:
                examples["empty_prediction"].append({"g": g, "p": p})

        if _len(p) > 30:
            bucket_counts["too_long_prediction"] += 1
            if len(examples["too_long_prediction"]) < top_n_examples:
                examples["too_long_prediction"].append({"g": g, "p": p})

        if any(x in p for x in ["我", "我们", "你", "你们", "他", "他们", "吗", "?", "？", "啊", "呀", "吧", "呢", "嘛"]):
            bucket_counts["contains_pronoun_or_modal"] += 1
            if len(examples["contains_pronoun_or_modal"]) < top_n_examples:
                examples["contains_pronoun_or_modal"].append({"g": g, "p": p})

        if cands:
            selected_rr = None
            best_rr = None
            selected_text = p
            for c in cands:
                rr = c.get("rr")
                t = str(c.get("t", "") or "")
                if rr is None:
                    continue
                rr = float(rr)
                if best_rr is None or rr > best_rr:
                    best_rr = rr
                if t == selected_text or c.get("s") == 1:
                    selected_rr = rr
            if selected_rr is not None and selected_rr < 0.55:
                bucket_counts["low_rerank_confidence"] += 1
                if len(examples["low_rerank_confidence"]) < top_n_examples:
                    examples["low_rerank_confidence"].append({
                        "g": g,
                        "p": p,
                        "selected_rr": round(selected_rr, 4),
                        "best_rr": round(best_rr, 4) if best_rr is not None else None,
                    })

    total = len(rows or [])
    ratios = {k: round(v / total, 4) if total else 0.0 for k, v in bucket_counts.items()}
    return {"total": total, "bucket_counts": bucket_counts, "bucket_ratios": ratios, "examples": examples}

