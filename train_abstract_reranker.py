import json
import os
import re
import logging
import argparse
from typing import Any, Dict, List, Tuple

import pandas as pd
import numpy as np

from config import Config
from standard_answer_manager import StandardAnswerManager
from model_manager import EnhancedModelManager
from bert_finetuner import BERTFineTuner
from bert_dataset import create_abstract_rerank_dataset_from_standard_answers

logger = logging.getLogger(__name__)


def _normalize_text(text: Any) -> str:
    return "".join(str(text or "").strip().split())


def _looks_garbled(text: Any) -> bool:
    t = str(text or "")
    if not t:
        return False
    bad_chars = set("����")
    bad_count = sum(1 for ch in t if ch in bad_chars)
    return (bad_count / max(1, len(t))) >= 0.08


def _read_csv_auto(path: str) -> Tuple[pd.DataFrame, str]:
    """Read CSV with best-effort encoding fallback and garble detection."""
    encodings = ["utf-8-sig", "utf-8", "gb18030", "gbk"]
    best_df = None
    best_enc = ""
    best_score = float("inf")

    for enc in encodings:
        try:
            df = pd.read_csv(path, encoding=enc)
            if df.empty:
                score = 1.0
            else:
                sample_vals = []
                take_rows = min(20, len(df))
                take_cols = min(2, df.shape[1])
                for r in range(take_rows):
                    for c in range(take_cols):
                        sample_vals.append(df.iat[r, c])
                garbled = sum(1 for v in sample_vals if _looks_garbled(v))
                score = garbled / max(1, len(sample_vals))

            if score < best_score:
                best_df, best_enc, best_score = df, enc, score

            if score == 0.0:
                break
        except Exception:
            continue

    if best_df is None:
        raise ValueError(f"CSV读取失败: {path}")

    if best_score > 0:
        logger.warning(f"CSV可能存在编码异常: {path}, chosen_encoding={best_enc}, garble_score={best_score:.3f}")
    return best_df, best_enc


def _build_standard_answers_from_csv(train_csv: str, val_csv: str = "") -> Dict[str, Any]:
    """Build standard_answers-like structure from CSV files.

    CSV schema: first column = target abstract, second column = original text.
    """
    train_df, train_enc = _read_csv_auto(train_csv)
    if train_df.shape[1] < 2:
        raise ValueError("训练CSV至少需要两列：一阶编码、原始文本")

    train_label_col, train_raw_col = train_df.columns[:2]
    train_df = train_df[[train_label_col, train_raw_col]].copy()
    train_df.columns = ["target_abstract", "original_content"]
    train_df["target_abstract"] = train_df["target_abstract"].fillna("").astype(str).str.strip()
    train_df["original_content"] = train_df["original_content"].fillna("").astype(str).str.strip()
    train_df = train_df[(train_df["target_abstract"] != "") & (train_df["original_content"] != "")]

    training_data: List[Dict[str, Any]] = []
    for _, row in train_df.iterrows():
        training_data.append(
            {
                "target_abstract": row["target_abstract"],
                "input_sentences": {"original_content": row["original_content"]},
            }
        )

    standard_answers: Dict[str, Any] = {
        "training_data": training_data,
        "metadata": {
            "source": "csv",
            "train_csv": os.path.normpath(train_csv),
            "train_csv_encoding": train_enc,
            "train_samples": len(training_data),
        },
    }

    if val_csv:
        val_df, val_enc = _read_csv_auto(val_csv)
        if val_df.shape[1] >= 2:
            c1, c2 = val_df.columns[:2]
            val_df = val_df[[c1, c2]].copy()
            val_df.columns = ["target_abstract", "original_content"]
            val_df["target_abstract"] = val_df["target_abstract"].fillna("").astype(str).str.strip()
            val_df["original_content"] = val_df["original_content"].fillna("").astype(str).str.strip()
            val_df = val_df[(val_df["target_abstract"] != "") & (val_df["original_content"] != "")]
            standard_answers["validation_data"] = [
                {
                    "target_abstract": r["target_abstract"],
                    "input_sentences": {"original_content": r["original_content"]},
                }
                for _, r in val_df.iterrows()
            ]
            standard_answers["metadata"]["val_csv"] = os.path.normpath(val_csv)
            standard_answers["metadata"]["val_csv_encoding"] = val_enc
            standard_answers["metadata"]["val_samples"] = len(standard_answers["validation_data"])

    return standard_answers


def _violation_rate(labels: List[str]) -> float:
    if not labels:
        return 0.0
    violations = 0
    for label in labels:
        t = str(label or "").strip()
        if not t:
            violations += 1
            continue
        if any(x in t for x in ["我", "我们", "你", "你们", "他", "他们", "吗", "?", "？", "啊", "呀", "吧", "呢", "嘛"]):
            violations += 1
    return round(violations / len(labels), 4)


def train_abstract_reranker(
    standard_answers,
    model_manager,
    progress_callback=None,
    finished_callback=None,
    training_config=None,
):
    """训练“一阶抽象候选重排序”模型（text-pair 二分类）。

    该函数可被 GUI/训练线程直接调用；CLI 入口会复用它。

    Args:
        standard_answers: 标准答案 dict（包含 training_data）
        model_manager: EnhancedModelManager 实例
        progress_callback: (cur, total, loss) -> None
        finished_callback: (success, message) -> None
        training_config: 可选训练配置 dict（优先覆盖 Config 默认值）

    Returns:
        (success: bool, output_dir: str, message: str)
    """
    training_config = training_config or {}

    dataset = create_abstract_rerank_dataset_from_standard_answers(
        standard_answers,
        tokenizer=None,
        max_length=min(256, training_config.get('max_length', getattr(Config, 'MAX_SENTENCE_LENGTH', 512))),
        max_span_len=training_config.get('abstract_rerank_max_span_len', getattr(Config, 'ABSTRACT_RERANK_MAX_SPAN_LEN', 8)),
        negative_samples=training_config.get('abstract_rerank_negative_samples', getattr(Config, 'ABSTRACT_RERANK_NEGATIVE_SAMPLES', 4)),
    )

    output_dir = os.path.join(
        Config.TRAINED_MODELS_DIR,
        training_config.get('abstract_reranker_dirname', getattr(Config, 'ABSTRACT_RERANKER_DIRNAME', 'abstract_reranker_latest')),
    )
    os.makedirs(output_dir, exist_ok=True)

    finetuner = BERTFineTuner(model_manager, config=training_config)

    def _progress_callback(cur, total, loss):
        if progress_callback:
            progress_callback(cur, total, loss)
        elif total:
            pct = int(cur / total * 100)
            logger.info(f"抽象重排序训练进度 {pct}% loss={loss:.4f}")

    def _finished_callback(success, message):
        if finished_callback:
            finished_callback(success, message)
        else:
            logger.info(f"抽象重排序训练完成: success={success}, message={message}")

    ok = finetuner.train(
        dataset,
        output_dir,
        progress_callback=_progress_callback,
        finished_callback=_finished_callback,
    )

    msg = "抽象重排序模型训练完成" if ok else "抽象重排序模型训练失败"
    return bool(ok), output_dir, msg


def _load_first_level_recall_labels(test_csv: str, train_only: bool = False) -> List[str]:
    base_dir = os.path.dirname(test_csv)
    if train_only:
        names = ["standard_train.csv"]
    else:
        names = list(getattr(Config, "FIRST_LEVEL_RECALL_BANK_FILES", []) or [])
        if not names:
            names = ["standard_train.csv"]

    labels: List[str] = []
    seen = set()
    for name in names:
        if os.path.isabs(name):
            path = name
        else:
            path = os.path.join(base_dir, name)
            if not os.path.exists(path):
                project_csv_path = os.path.join(Config.BASE_DIR, "csv", name)
                if os.path.exists(project_csv_path):
                    path = project_csv_path
        if not os.path.exists(path):
            continue
        try:
            df, _ = _read_csv_auto(path)
        except Exception:
            continue
        if df.shape[1] < 1:
            continue
        for label in df.iloc[:, 0].fillna("").astype(str).str.strip().tolist():
            if not label or label in seen:
                continue
            seen.add(label)
            labels.append(label)
    return labels


def _load_first_level_prototypes(test_csv: str) -> List[Dict[str, str]]:
    base_dir = os.path.dirname(test_csv)
    names = list(getattr(Config, "FIRST_LEVEL_PROTOTYPE_FILES", []) or [])
    prototypes: List[Dict[str, str]] = []
    seen = set()
    for name in names:
        if os.path.isabs(name):
            path = name
        else:
            path = os.path.join(base_dir, name)
            if not os.path.exists(path):
                for sub in ("csv", "data", ""):
                    alt = os.path.join(Config.BASE_DIR, sub, name) if sub else os.path.join(Config.BASE_DIR, name)
                    if os.path.exists(alt):
                        path = alt
                        break
        if not os.path.exists(path):
            continue
        if path.endswith(".json"):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    items = json.load(fh)
                if isinstance(items, list):
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        label = str(item.get("manual_first_code", "")).strip()
                        source = str(item.get("source", "")).strip()
                        if not label or not source:
                            continue
                        key = (label, source)
                        if key in seen:
                            continue
                        seen.add(key)
                        prototypes.append({"manual_first_code": label, "source": source})
            except Exception:
                continue
        else:
            try:
                df, _ = _read_csv_auto(path)
            except Exception:
                continue
            if df.shape[1] < 2:
                continue
            c1, c2 = df.columns[:2]
            for _, row in df[[c1, c2]].iterrows():
                label = str(row[c1] or "").strip()
                source = str(row[c2] or "").strip()
                if not label or not source:
                    continue
                key = (label, source)
                if key in seen:
                    continue
                seen.add(key)
                prototypes.append({"manual_first_code": label, "source": source})
    return prototypes


def evaluate_reranker_from_csv(
    test_csv: str,
    model_manager: EnhancedModelManager,
    top_k: int = 5,
) -> Dict[str, Any]:
    """Evaluate abstract reranker on CSV and report Top1/Hit@K/violation_rate."""
    test_df, test_enc = _read_csv_auto(test_csv)
    if test_df.shape[1] < 2:
        raise ValueError("测试CSV至少需要两列：一阶编码、原始文本")

    c1, c2 = test_df.columns[:2]
    test_df = test_df[[c1, c2]].copy()
    test_df.columns = ["target_abstract", "original_content"]
    test_df["target_abstract"] = test_df["target_abstract"].fillna("").astype(str).str.strip()
    test_df["original_content"] = test_df["original_content"].fillna("").astype(str).str.strip()
    test_df = test_df[(test_df["target_abstract"] != "") & (test_df["original_content"] != "")]

    eval_samples = [
        {
            "target_abstract": row["target_abstract"],
            "input_sentences": {"original_content": row["original_content"]},
        }
        for _, row in test_df.iterrows()
    ]

    from enhanced_coding_generator import EnhancedCodingGenerator
    from first_level_eval import evaluate_first_level_candidates, analyze_first_level_errors

    generator = EnhancedCodingGenerator()
    train_only_recall = bool(getattr(Config, "FIRST_LEVEL_EVAL_TRAIN_ONLY_RECALL", False))
    train_labels = _load_first_level_recall_labels(test_csv, train_only=train_only_recall)

    if False and os.path.exists(train_csv):
        train_df, _ = _read_csv_auto(train_csv)
        if train_df.shape[1] >= 1:
            train_labels = train_df.iloc[:, 0].fillna("").astype(str).str.strip().tolist()
    if hasattr(generator, "set_first_level_recall_bank"):
        generator.set_first_level_recall_bank(train_labels, model_manager=model_manager)
    if hasattr(generator, "set_first_level_prototypes"):
        generator.set_first_level_prototypes(_load_first_level_prototypes(test_csv))
    eval_result = evaluate_first_level_candidates(
        eval_samples,
        generator,
        model_manager=model_manager,
        top_n=top_k,
    )

    preds = [str(row.get("p", "") or "") for row in eval_result.get("rows", [])]
    summary = eval_result.get("summary", {})
    summary["test_csv_encoding"] = test_enc
    summary["violation_rate"] = _violation_rate(preds)
    summary["error_analysis"] = analyze_first_level_errors(eval_result.get("rows", []), top_n_examples=3)
    return {"summary": summary, "rows": eval_result.get("rows", [])}


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 1e-12:
        return 0.0
    return float(np.dot(a, b) / denom)


def evaluate_reranker_generation_from_csv(
    test_csv: str,
    model_manager: EnhancedModelManager,
    top_k: int = 5,
) -> Dict[str, Any]:
    """Generation-oriented first-level evaluation with semantic metrics."""
    base = evaluate_reranker_from_csv(test_csv=test_csv, model_manager=model_manager, top_k=top_k)
    rows = base.get("rows", [])
    summary = base.get("summary", {})

    sample_count = len(rows)
    if sample_count == 0:
        summary.update(
            {
                "source_anchor_ratio": 0.0,
                "length_compliance_ratio": 0.0,
                "semantic_top1": 0.0,
                f"semantic_hit_at_{top_k}": 0.0,
                "semantic_avg_top1": 0.0,
            }
        )
        return {"summary": summary, "rows": rows}

    max_len = int(getattr(Config, "FIRST_LEVEL_CODE_MAX_LENGTH", 30))
    source_anchor = 0
    length_ok = 0
    colloquial_free = 0
    focused_phrase = 0

    for row in rows:
        p = str(row.get("p", "") or "")
        o = str(row.get("o", "") or "")
        if p and _normalize_text(p) in _normalize_text(o):
            source_anchor += 1
        if p and len(p) <= max_len:
            length_ok += 1
        if p and not re.search(r'(我|我们|你|你们|他|他们|这个|那个|怎么说呢|就是说|我觉得|相当于|吧|呢|啊|嘛|呀|哦|哈)', p):
            colloquial_free += 1
        if p and re.search(r'(影响|导致|需要|只能|受限|不足|短板|风险|压力|冲突|审批|协同|资源|客户|诉求|反馈|推进|识别|整合|建立|引入|优化|开发|支持|合作|转型|创新|需求|机会|机制|流程)', p):
            focused_phrase += 1

    summary["source_anchor_ratio"] = round(source_anchor / sample_count, 4)
    summary["length_compliance_ratio"] = round(length_ok / sample_count, 4)
    summary["colloquial_free_ratio"] = round(colloquial_free / sample_count, 4)
    summary["focused_phrase_ratio"] = round(focused_phrase / sample_count, 4)
    summary["extractive_quality_score"] = round(
        0.35 * summary["source_anchor_ratio"]
        + 0.25 * summary["length_compliance_ratio"]
        + 0.25 * summary["colloquial_free_ratio"]
        + 0.15 * summary["focused_phrase_ratio"],
        4,
    )

    semantic_top1_hit = 0
    semantic_hitk = 0
    semantic_top1_scores: List[float] = []
    sim_threshold = float(getattr(Config, "ABSTRACT_SEMANTIC_HIT_THRESHOLD", 0.78))

    for row in rows:
        gold = str(row.get("g", "") or "").strip()
        pred = str(row.get("p", "") or "").strip()
        cand_texts = [str(c.get("t", "") or "").strip() for c in (row.get("c", []) or [])]

        if not gold or not pred:
            semantic_top1_scores.append(0.0)
            continue

        emb_gp = model_manager.get_embeddings([gold, pred], model_type="sentence")
        sim_top1 = _cosine_similarity(emb_gp[0], emb_gp[1])
        semantic_top1_scores.append(sim_top1)
        if sim_top1 >= sim_threshold:
            semantic_top1_hit += 1

        if cand_texts:
            emb_all = model_manager.get_embeddings([gold] + cand_texts, model_type="sentence")
            g = emb_all[0]
            sims = [_cosine_similarity(g, emb_all[i]) for i in range(1, emb_all.shape[0])]
            if sims and max(sims) >= sim_threshold:
                semantic_hitk += 1

    summary["semantic_top1"] = round(semantic_top1_hit / sample_count, 4)
    summary[f"semantic_hit_at_{top_k}"] = round(semantic_hitk / sample_count, 4)
    summary["semantic_avg_top1"] = round(float(np.mean(semantic_top1_scores)), 4)
    summary["semantic_threshold"] = sim_threshold

    return {"summary": summary, "rows": rows}


def main():
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Train abstract reranker from standard answers or CSV splits")
    parser.add_argument("--train-csv", type=str, default="", help="训练集CSV路径（第一列一阶编码，第二列原始文本）")
    parser.add_argument("--val-csv", type=str, default="", help="验证集CSV路径（可选）")
    parser.add_argument("--test-csv", type=str, default="", help="测试集CSV路径（可选，训练后评估）")
    parser.add_argument("--top-k", type=int, default=5, help="评估Hit@K的K值")
    args = parser.parse_args()

    if args.train_csv:
        current_answers = _build_standard_answers_from_csv(args.train_csv, args.val_csv)
    else:
        manager = StandardAnswerManager()
        current_answers = manager.get_current_answers()

    if not current_answers:
        raise SystemExit("没有可用的标准答案，请先生成/加载标准答案")

    model_manager = EnhancedModelManager()

    def progress_callback(cur, total, loss):
        if total:
            pct = int(cur / total * 100)
            logger.info(f"抽象重排序训练进度 {pct}% loss={loss:.4f}")

    def finished_callback(success, message):
        logger.info(f"抽象重排序训练完成: success={success}, message={message}")

    ok, output_dir, message = train_abstract_reranker(
        current_answers,
        model_manager,
        progress_callback=progress_callback,
        finished_callback=finished_callback,
    )

    if not ok:
        raise SystemExit("抽象重排序模型训练失败")

    if hasattr(model_manager, "load_abstract_reranker_model"):
        model_manager.load_abstract_reranker_model(output_dir)

    print(f"抽象重排序模型已保存到: {output_dir}")

    if args.test_csv:
        result = evaluate_reranker_from_csv(args.test_csv, model_manager=model_manager, top_k=max(1, int(args.top_k)))
        print("评估结果(严格匹配):", result.get("summary", {}))

        gen_result = evaluate_reranker_generation_from_csv(
            args.test_csv,
            model_manager=model_manager,
            top_k=max(1, int(args.top_k)),
        )
        print("评估结果(生成质量):", gen_result.get("summary", {}))


if __name__ == '__main__':
    main()
