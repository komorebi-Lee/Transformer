import gzip
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def _normalize_text(text: Any) -> str:
    return "".join(str(text or "").strip().split())


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
        trace = generator.build_first_level_candidate_trace(original, model_manager=model_manager, top_n=top_n)
        pred = trace.get("selected_candidate", "")
        candidates = trace.get("candidates", [])
        if trace.get("used_rerank"):
            rerank_used += 1

        gold_norm = _normalize_text(gold)
        pred_norm = _normalize_text(pred)
        candidate_norms = [_normalize_text(item.get("text", "")) for item in candidates]

        top1 = bool(pred_norm and pred_norm == gold_norm)
        topk = gold_norm in candidate_norms if gold_norm else False
        if top1:
            top1_hit += 1
        if topk:
            hit_at_k += 1

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
        "hit_at_{}".format(top_n): round(hit_at_k / sample_count, 4) if sample_count else 0.0,
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
