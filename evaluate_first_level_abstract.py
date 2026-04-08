import os
import random
import difflib
from typing import Any, Dict, List, Tuple

from config import Config
from standard_answer_manager import StandardAnswerManager
from model_manager import EnhancedModelManager
from enhanced_coding_generator import EnhancedCodingGenerator


def _sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, (a or ""), (b or "")).ratio()


def _extract_pairs(answers: Dict[str, Any]) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    training_data = (answers or {}).get("training_data", [])
    if not isinstance(training_data, list):
        return pairs

    for item in training_data:
        if not isinstance(item, dict):
            continue
        input_sentences = item.get("input_sentences", {}) or {}
        original = (input_sentences.get("original_content") or item.get("text") or "").strip()
        target = (item.get("target_abstract") or "").strip()
        if len(original) >= 6 and len(target) >= 2:
            pairs.append((original, target))
    return pairs


def evaluate(sample_limit: int = 300, seed: int = 42, show_examples: int = 10) -> None:
    """对比：未启用 reranker vs 启用 reranker 的一阶抽取质量。

    评测数据来自 standard_answers 最新版本的 training_data（original_content/target_abstract）。

    输出：
    - baseline（纯规则）平均相似度
    - reranked（规则+候选打分重排）平均相似度（若模型可用）
    - 提升比例与示例对照
    """

    mgr = StandardAnswerManager()
    answers = mgr.get_current_answers() or {}
    pairs = _extract_pairs(answers)

    if not pairs:
        raise SystemExit("没有可用的 (original_content, target_abstract) 对；请先加载/生成包含 training_data 的标准答案")

    rng = random.Random(seed)
    if sample_limit and len(pairs) > sample_limit:
        pairs = rng.sample(pairs, sample_limit)

    generator = EnhancedCodingGenerator()
    model_manager = EnhancedModelManager()

    # Baseline：强制关闭 reranker
    old_flag = getattr(Config, "ENABLE_ABSTRACT_RERANKER", False)
    try:
        Config.ENABLE_ABSTRACT_RERANKER = False
        baseline_preds: List[str] = [generator.abstract_sentence(o, model_manager=None) for o, _ in pairs]
    finally:
        Config.ENABLE_ABSTRACT_RERANKER = old_flag

    baseline_scores = [_sim(pred, tgt) for pred, (_, tgt) in zip(baseline_preds, pairs)]

    # NOTE: “抽象重排序/打分模型（reranker）”功能已从主流程移除，此处仅评测规则抽取基线。

    def _avg(xs: List[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    print(f"samples={len(pairs)}")
    print(f"baseline_avg_sim={_avg(baseline_scores):.4f}")

    print("reranker: removed (skip)")
    return


if __name__ == "__main__":
    evaluate()
