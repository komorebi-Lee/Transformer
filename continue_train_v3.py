"""Continue v3 concept_anchor training from checkpoint (epoch 5 → 8).

Loads the saved model and trains 3 more epochs with a lower learning rate,
then saves the final model.
"""

import os as _os
_os.environ.setdefault("SENTENCE_TRANSFORMERS_NO_MODEL_CARD", "1")

import argparse
import json
import logging
import os
import sys
from datetime import datetime

import torch
from sentence_transformers import SentenceTransformer, InputExample, losses, evaluation
from torch.utils.data import DataLoader

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("continue_train_v3")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_training_data(data_path: str):
    with open(data_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    pairs = data.get("pairs", [])
    examples = []
    for item in pairs:
        sent = item["sentence"].strip()
        anchor = item["anchor_code"].strip()
        if sent and anchor:
            examples.append(InputExample(texts=[sent, anchor]))
    logger.info("Loaded %d training examples", len(examples))
    return examples


def load_coding_library_pairs(library_path: str):
    with open(library_path, "r", encoding="utf-8") as fh:
        lib = json.load(fh)
    examples = []
    enc = lib.get("encoding_library", lib)
    for third in enc.get("third_level_codes", []):
        third_name = third.get("name", "")
        for second in third.get("second_level_codes", []):
            second_name = second.get("name", "")
            if second_name and third_name:
                examples.append(InputExample(texts=[second_name, third_name]))
    logger.info("Loaded %d coding library pairs", len(examples))
    return examples


def build_evaluator(examples, batch_size=32):
    if len(examples) < 20:
        return None
    n_val = max(20, len(examples) // 10)
    val_examples = examples[-n_val:]
    import random
    random.seed(42)
    sentences1, sentences2, labels = [], [], []
    for i, ex in enumerate(val_examples):
        sentences1.append(ex.texts[0])
        sentences2.append(ex.texts[1])
        labels.append(1.0)
        j = (i + random.randint(1, len(val_examples) - 1)) % len(val_examples)
        sentences1.append(ex.texts[0])
        sentences2.append(val_examples[j].texts[1])
        labels.append(0.0)
    return evaluation.BinaryClassificationEvaluator(
        sentences1, sentences2, labels,
        batch_size=batch_size,
        name="anchor-val-continue",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-path", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "data", "train_anchor_pairs_v3.json"))
    parser.add_argument("--library-path", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "coding_library.json"))
    parser.add_argument("--checkpoint-dir", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "trained_models", "concept_anchor_v3"))
    parser.add_argument("--output-dir", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "trained_models", "concept_anchor_v3"))
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-5)
    parser.add_argument("--temperature", type=float, default=0.05)
    parser.add_argument("--warmup-steps", type=int, default=50)
    parser.add_argument("--eval-steps", type=int, default=200)
    parser.add_argument("--use-library-pairs", action="store_true", default=True)
    args = parser.parse_args()

    # ---- Load data ----
    train_examples = load_training_data(args.data_path)
    if args.use_library_pairs and os.path.exists(args.library_path):
        lib_examples = load_coding_library_pairs(args.library_path)
        train_examples.extend(lib_examples)
        logger.info("Total examples (with library): %d", len(train_examples))

    import random
    random.seed(123)  # Different seed from initial training for fresh shuffle
    random.shuffle(train_examples)

    n_train = int(len(train_examples) * 0.9)
    train_set = train_examples[:n_train]
    evaluator = build_evaluator(train_examples, batch_size=args.batch_size)

    # ---- Load checkpoint model ----
    logger.info("Loading checkpoint: %s", args.checkpoint_dir)
    model = SentenceTransformer(args.checkpoint_dir, device="cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Model device: %s", model.device)

    # ---- Training setup ----
    train_dataloader = DataLoader(
        train_set, shuffle=True, batch_size=args.batch_size,
    )

    train_loss = losses.MultipleNegativesRankingLoss(
        model, scale=1.0 / args.temperature,
    )

    os.makedirs(args.output_dir, exist_ok=True)

    logger.info("Continuing training: %d epochs, batch_size=%d, lr=%g, temperature=%.3f",
                args.epochs, args.batch_size, args.lr, args.temperature)
    logger.info("Train examples: %d, Eval: %s", len(train_set),
                "yes" if evaluator else "no")

    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=args.epochs,
        warmup_steps=args.warmup_steps,
        optimizer_params={"lr": args.lr},
        evaluator=evaluator,
        evaluation_steps=args.eval_steps,
        output_path=args.output_dir,
        save_best_model=True,
        show_progress_bar=True,
    )

    # ---- Save metadata ----
    meta = {
        "base_model": "local_models/bge-small-zh-v1.5",
        "continued_from": args.checkpoint_dir,
        "training_pairs": len(train_set),
        "epochs_continued": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "temperature": args.temperature,
        "trained_at": datetime.now().isoformat(),
    }
    with open(os.path.join(args.output_dir, "training_meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)

    logger.info("Model saved to: %s", args.output_dir)

    # ---- Quick test ----
    logger.info("\n=== Quick test ===")
    test_sentences = [
        "刷视频看到别人都很厉害，我越来越不想打开书",
        "资源不够，审批流程太复杂",
        "培训不到位，员工能力参差不齐",
    ]
    for sent in test_sentences:
        emb = model.encode(sent, normalize_embeddings=True)
        logger.info("  '%s' -> norm=%.3f", sent[:50], float((emb ** 2).sum()))

    return 0


if __name__ == "__main__":
    sys.exit(main())
