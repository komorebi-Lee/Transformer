"""Supervised contrastive fine-tuning of bge-small-zh-v1.5 for concept anchoring.

Trains the embedding model to map colloquial sentences to stable concept anchors,
using MultipleNegativesRankingLoss with in-batch negatives.

Usage:
    D:/anaconda3/envs/zthree5/python.exe train_concept_anchor.py
    D:/anaconda3/envs/zthree5/python.exe train_concept_anchor.py --epochs 5 --batch-size 16
"""

import os as _os
_os.environ.setdefault("SENTENCE_TRANSFORMERS_NO_MODEL_CARD", "1")

import argparse
import json
import logging
import math
import os
import sys
from collections import defaultdict
from datetime import datetime
from typing import List, Tuple

import torch
from sentence_transformers import SentenceTransformer, InputExample, losses, evaluation
from torch.utils.data import DataLoader

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_anchor")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_training_data(data_path: str) -> List[InputExample]:
    """Load cleaned (sentence, anchor_code) pairs as contrastive examples."""
    with open(data_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    pairs = data.get("pairs", [])
    examples = []
    for item in pairs:
        sent = item["sentence"].strip()
        anchor = item["anchor_code"].strip()
        if sent and anchor:
            examples.append(InputExample(texts=[sent, anchor]))
    logger.info("Loaded %d training examples from %d pairs", len(examples), len(pairs))
    return examples


def load_coding_library_pairs(library_path: str) -> List[InputExample]:
    """Create (second_code_name, third_code_name) pairs from coding library.

    This teaches the model that second and third level codes live in the same space.
    """
    with open(library_path, "r", encoding="utf-8") as fh:
        lib = json.load(fh)

    examples = []
    enc = lib.get("encoding_library", lib)
    for third in enc.get("third_level_codes", []):
        third_name = third.get("name", "")
        for second in third.get("second_level_codes", []):
            second_name = second.get("name", "")
            if second_name and third_name:
                # Second-level code as anchor, third-level as context
                examples.append(InputExample(texts=[second_name, third_name]))
    logger.info("Loaded %d coding library pairs", len(examples))
    return examples


def build_evaluator(examples: List[InputExample], batch_size: int = 32):
    """Build a binary classification evaluator from held-out pairs."""
    if len(examples) < 20:
        return None

    # Take 10% for validation
    n_val = max(20, len(examples) // 10)
    val_examples = examples[-n_val:]

    # Build (sentence, anchor, label) triplets for binary evaluation
    # Positive: same anchor; Negative: different anchor (shuffled)
    import random
    random.seed(42)
    sentences1, sentences2, labels = [], [], []
    for i, ex in enumerate(val_examples):
        sentences1.append(ex.texts[0])
        sentences2.append(ex.texts[1])
        labels.append(1.0)  # positive pair
        # Negative: pair with a different anchor
        j = (i + random.randint(1, len(val_examples) - 1)) % len(val_examples)
        sentences1.append(ex.texts[0])
        sentences2.append(val_examples[j].texts[1])
        labels.append(0.0)

    return evaluation.BinaryClassificationEvaluator(
        sentences1, sentences2, labels,
        batch_size=batch_size,
        name="anchor-val",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-path", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "data", "clean_anchor_pairs.json"))
    parser.add_argument("--library-path", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "coding_library.json"))
    parser.add_argument("--base-model", type=str,
                        default="local_models/bge-small-zh-v1.5")
    parser.add_argument("--output-dir", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "trained_models", "concept_anchor"))
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--temperature", type=float, default=0.05)
    parser.add_argument("--warmup-steps", type=int, default=100)
    parser.add_argument("--eval-steps", type=int, default=200)
    parser.add_argument("--use-library-pairs", action="store_true",
                        help="Also include coding library hierarchy pairs")
    args = parser.parse_args()

    # ---- Load data ----
    train_examples = load_training_data(args.data_path)
    if args.use_library_pairs and os.path.exists(args.library_path):
        lib_examples = load_coding_library_pairs(args.library_path)
        train_examples.extend(lib_examples)
        logger.info("Total examples (with library): %d", len(train_examples))

    # Shuffle
    import random
    random.seed(42)
    random.shuffle(train_examples)

    # Build evaluator from held-out portion
    n_train = int(len(train_examples) * 0.9)
    train_set = train_examples[:n_train]
    evaluator = build_evaluator(train_examples, batch_size=args.batch_size)

    # ---- Load base model ----
    base_model_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        args.base_model,
    )
    logger.info("Loading base model: %s", base_model_path)
    model = SentenceTransformer(base_model_path, device="cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Model device: %s", model.device)
    logger.info("Base embedding dim: %d", model.get_sentence_embedding_dimension())

    # ---- Training setup ----
    train_dataloader = DataLoader(
        train_set,
        shuffle=True,
        batch_size=args.batch_size,
    )

    # MultipleNegativesRankingLoss: in-batch negatives
    # For each (sentence, anchor) pair in the batch, all other pairs' anchors
    # serve as negatives. Temperature controls the sharpness of the distribution.
    train_loss = losses.MultipleNegativesRankingLoss(
        model,
        scale=1.0 / args.temperature,  # temperature scaling
    )

    os.makedirs(args.output_dir, exist_ok=True)

    # ---- Train ----
    logger.info("Starting training: %d epochs, batch_size=%d, lr=%g, temperature=%.3f",
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
        "base_model": args.base_model,
        "training_pairs": len(train_set),
        "epochs": args.epochs,
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
        "管理制度不完善，缺乏监督机制",
        "大家都在摸鱼，没什么干劲",
    ]
    for sent in test_sentences:
        emb = model.encode(sent, normalize_embeddings=True)
        sim = model.similarity(
            model.encode(sent, normalize_embeddings=True),
            model.encode(sent, normalize_embeddings=True),
        )
        logger.info("  '%s'", sent[:50])

    return 0


if __name__ == "__main__":
    sys.exit(main())
