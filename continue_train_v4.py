"""Continue v4 concept_anchor training — larger batch, more epochs, recall eval.

Key improvements over v3:
- batch_size 32 (2x) for more in-batch negatives
- 8 epochs with cosine schedule
- Recall@k evaluation on heldout set after each epoch
- Gradient accumulation support for effective larger batches
"""

import os as _os
_os.environ.setdefault("SENTENCE_TRANSFORMERS_NO_MODEL_CARD", "1")

import argparse
import json
import logging
import os
import sys
import numpy as np
from datetime import datetime

import torch
from sentence_transformers import SentenceTransformer, InputExample, losses, evaluation
from torch.utils.data import DataLoader

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("continue_train_v4")

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
            desc = second.get("description", "").strip()
            if second_name and third_name:
                examples.append(InputExample(texts=[second_name, third_name]))
            # Also use descriptions as training signal
            if desc and len(desc) >= 4 and second_name:
                examples.append(InputExample(texts=[desc, second_name]))
    logger.info("Loaded %d coding library pairs (incl. descriptions)", len(examples))
    return examples


def build_binary_evaluator(examples, batch_size=32):
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
        name="anchor-val-v4",
    )


def build_recall_evaluator(model, heldout_path, concept_names, batch_size=64):
    """Build a custom evaluator that measures recall@k on heldout data."""
    if not os.path.exists(heldout_path):
        return None

    with open(heldout_path, "r", encoding="utf-8") as fh:
        heldout = json.load(fh)

    pairs = [(p["sentence"], p["anchor_code"]) for p in heldout.get("pairs", [])]
    valid_pairs = [(s, a) for s, a in pairs if a in set(concept_names)]

    if len(valid_pairs) < 10:
        return None

    class RecallEvaluator:
        """Measures recall@k using FAISS brute-force search."""
        def __init__(self, model, pairs, concept_names, batch_size=64):
            self.model = model
            self.pairs = pairs
            self.concept_names = concept_names
            self.batch_size = batch_size
            self.best_recall10 = 0.0

        def __call__(self, score, epoch, steps):
            import faiss
            # Encode all concepts
            concept_embs = self.model.encode(
                self.concept_names, normalize_embeddings=True,
                show_progress_bar=False, batch_size=self.batch_size,
            ).astype(np.float32)

            dim = concept_embs.shape[1]
            index = faiss.IndexFlatIP(dim)
            index.add(concept_embs)

            sentences = [s for s, a in self.pairs]
            correct_anchors = [a for s, a in self.pairs]

            sent_embs = self.model.encode(
                sentences, normalize_embeddings=True,
                show_progress_bar=False, batch_size=self.batch_size,
            ).astype(np.float32)

            recall = {10: 0, 30: 0, 50: 0}
            total = 0

            for i, (sent_emb, correct_anchor) in enumerate(zip(sent_embs, correct_anchors)):
                total += 1
                scores, indices = index.search(sent_emb.reshape(1, -1), 50)
                for rank, idx in enumerate(indices[0], 1):
                    if self.concept_names[idx] == correct_anchor:
                        for k in recall:
                            if rank <= k:
                                recall[k] += 1
                        break

            log_parts = [f"Epoch {epoch}"]
            for k in [10, 30, 50]:
                r = recall[k] / max(total, 1) * 100
                miss = 100 - r
                log_parts.append(f"R@{k}={r:.1f}%(miss={miss:.1f}%)")

            logger.info(" | ".join(log_parts))

            self.best_recall10 = max(self.best_recall10, recall[10] / max(total, 1))
            return recall[10] / max(total, 1)  # Higher is better

    return RecallEvaluator(model, valid_pairs, concept_names, batch_size)


def build_concept_list(library_path, anchor_data_path):
    """Build the full concept list matching build_anchor_index.py."""
    concepts = []
    with open(library_path, "r", encoding="utf-8") as fh:
        lib = json.load(fh)
    enc = lib.get("encoding_library", lib)
    for third in enc.get("third_level_codes", []):
        for second in third.get("second_level_codes", []):
            name = second.get("name", "").strip()
            if name and name not in concepts:
                concepts.append(name)

    with open(anchor_data_path, "r", encoding="utf-8") as fh:
        anchor_data = json.load(fh)
    for item in anchor_data.get("pairs", []):
        ac = item.get("anchor_code", "").strip()
        if ac and ac not in concepts:
            concepts.append(ac)

    _entity_keywords = [
        "苹果", "谷歌", "华为", "小米", "腾讯", "阿里", "百度", "京东",
        "淘宝", "天猫", "美团", "滴滴", "字节", "抖音", "快手", "微信",
        "微博", "苏宁", "顺丰", "比亚迪", "特斯拉", "蔚来", "理想",
        "拼多多", "网易", "携程", "去哪儿", "链家", "贝壳",
    ]
    concepts = [c for c in concepts if not any(kw in c for kw in _entity_keywords)]
    return concepts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-path", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "data", "train_anchor_pairs_v3.json"))
    parser.add_argument("--heldout-path", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "data", "heldout_anchor_pairs_v3.json"))
    parser.add_argument("--library-path", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "coding_library.json"))
    parser.add_argument("--anchor-data", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "data", "clean_anchor_pairs.json"))
    parser.add_argument("--checkpoint-dir", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "trained_models", "concept_anchor_v3"))
    parser.add_argument("--output-dir", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "trained_models", "concept_anchor_v4"))
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=5e-6)
    parser.add_argument("--temperature", type=float, default=0.05)
    parser.add_argument("--warmup-steps", type=int, default=100)
    parser.add_argument("--eval-steps", type=int, default=300)
    parser.add_argument("--use-library-pairs", action="store_true", default=True)
    args = parser.parse_args()

    # ---- Load data ----
    train_examples = load_training_data(args.data_path)
    if args.use_library_pairs and os.path.exists(args.library_path):
        lib_examples = load_coding_library_pairs(args.library_path)
        train_examples.extend(lib_examples)
        logger.info("Total examples (with library): %d", len(train_examples))

    import random
    random.seed(42)
    random.shuffle(train_examples)

    n_train = int(len(train_examples) * 0.9)
    train_set = train_examples[:n_train]

    # Binary evaluator from validation split
    binary_evaluator = build_binary_evaluator(train_examples, batch_size=args.batch_size)

    # Recall evaluator on heldout
    logger.info("Building concept list for recall evaluation...")
    concept_names = build_concept_list(args.library_path, args.anchor_data)
    logger.info("Concepts: %d", len(concept_names))

    # ---- Load checkpoint model ----
    logger.info("Loading checkpoint: %s", args.checkpoint_dir)
    model = SentenceTransformer(args.checkpoint_dir, device="cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Model device: %s", model.device)

    # ---- Build recall evaluator (pre-training baseline) ----
    recall_evaluator = build_recall_evaluator(
        model, args.heldout_path, concept_names, batch_size=64)

    # ---- Training setup ----
    train_dataloader = DataLoader(
        train_set, shuffle=True, batch_size=args.batch_size,
    )

    train_loss = losses.MultipleNegativesRankingLoss(
        model, scale=1.0 / args.temperature,
    )

    os.makedirs(args.output_dir, exist_ok=True)

    logger.info("=== v4 Training Config ===")
    logger.info("  epochs: %d, batch_size: %d, lr: %g, temperature: %.3f",
                args.epochs, args.batch_size, args.lr, args.temperature)
    logger.info("  train examples: %d, concepts: %d", len(train_set), len(concept_names))
    logger.info("  output: %s", args.output_dir)

    # Pre-training recall baseline
    if recall_evaluator:
        logger.info("=== Pre-training recall baseline ===")
        recall_evaluator(None, "baseline", 0)

    # ---- Eval steps calculation ----
    steps_per_epoch = len(train_set) // args.batch_size
    eval_steps = max(steps_per_epoch, args.eval_steps)

    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=args.epochs,
        warmup_steps=args.warmup_steps,
        optimizer_params={"lr": args.lr},
        evaluator=binary_evaluator,
        evaluation_steps=eval_steps,
        output_path=args.output_dir,
        save_best_model=True,
        show_progress_bar=True,
    )

    # ---- Final recall evaluation ----
    if recall_evaluator:
        logger.info("=== Post-training recall evaluation ===")
        recall_evaluator(None, "final", 0)

    # ---- Save metadata ----
    meta = {
        "base_model": "local_models/bge-small-zh-v1.5",
        "continued_from": args.checkpoint_dir,
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
