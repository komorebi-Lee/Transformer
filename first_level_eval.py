import gzip
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


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

        rows.append(
            {
                "o": original,
                "g": gold,
                "p": pred,
                "m": match_type,
                "u": 1 if trace.get("used_rerank") else 0,
                "c": _compact_candidates(candidates, top_n=top_n),
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

