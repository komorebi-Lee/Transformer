import os
import logging

from config import Config
from standard_answer_manager import StandardAnswerManager
from model_manager import EnhancedModelManager
from bert_finetuner import BERTFineTuner
from bert_dataset import create_abstract_rerank_dataset_from_standard_answers

logger = logging.getLogger(__name__)


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


def main():
    logging.basicConfig(level=logging.INFO)

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

    print(f"抽象重排序模型已保存到: {output_dir}")


if __name__ == '__main__':
    main()
