"""Train contrastive alignment: different expressions → unified concept space.

Uses MultipleNegativesRankingLoss on (sent_a, sent_b) positive pairs where
both sentences share the same anchor code. This teaches the encoder to map
diverse surface expressions to the same concept region in embedding space.

Key difference from previous training:
- v3/v4/v5: trained on (sentence, anchor_code_name) pairs
- v6 (this): trains on (sentence_a, sentence_b) pairs — both are natural language
  expressions of the same underlying concept. This directly addresses the
  "semantic alignment" requirement: "能聚拢客源" ≈ "增加园区人流量" → same anchor.

Evaluation: sentence-to-sentence recall@k — given a query sentence, can the
model retrieve other sentences with the same anchor code?
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
from collections import defaultdict

import torch
from sentence_transformers import SentenceTransformer, InputExample, losses, evaluation
from torch.utils.data import DataLoader

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("contrastive_align")


def load_contrastive_pairs(data_path):
    """Load (sent_a, sent_b) positive pairs."""
    with open(data_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    examples = []
    for item in data.get("pairs", []):
        sent_a = item["sentence_a"].strip()
        sent_b = item["sentence_b"].strip()
        if sent_a and sent_b:
            examples.append(InputExample(texts=[sent_a, sent_b]))
    logger.info("Loaded %d contrastive pairs from %s", len(examples), data_path)
    return examples


def build_sentence_recall_evaluator(model, heldout_path, batch_size=64):
    """Evaluate sentence-to-sentence recall: query sent → retrieve sents with same anchor."""
    if not os.path.exists(heldout_path):
        return None

    with open(heldout_path, "r", encoding="utf-8") as fh:
        heldout = json.load(fh)

    # Build query → relevant sentences mapping
    anchor_to_sents = defaultdict(list)
    all_sentences = []
    sent_to_anchor = {}

    for item in heldout.get("pairs", []):
        anchor = item["anchor"]
        for sent_key in ["sentence_a", "sentence_b"]:
            sent = item.get(sent_key, "").strip()
            if sent and sent not in sent_to_anchor:
                sent_to_anchor[sent] = anchor
                anchor_to_sents[anchor].append(sent)
                all_sentences.append(sent)

    if len(all_sentences) < 20:
        return None

    unique_sents = list(sent_to_anchor.keys())

    class SentenceRecallEvaluator(evaluation.SentenceEvaluator):
        def __init__(self, model, unique_sents, sent_to_anchor, anchor_to_sents, bs=64):
            super().__init__()
            self.model = model
            self.sentences = unique_sents
            self.sent_to_anchor = sent_to_anchor
            self.anchor_to_sents = anchor_to_sents
            self.batch_size = bs
            self.best_recall10 = 0.0

        def __call__(self, score, epoch, steps, **kwargs):
            import faiss

            # Encode all sentences
            sent_embs = self.model.encode(
                self.sentences, normalize_embeddings=True,
                show_progress_bar=False, batch_size=self.batch_size,
            ).astype(np.float32)

            dim = sent_embs.shape[1]
            index = faiss.IndexFlatIP(dim)
            index.add(sent_embs)

            recall = {10: 0, 30: 0, 50: 0}
            total = 0

            for i, query_sent in enumerate(self.sentences):
                query_anchor = self.sent_to_anchor[query_sent]
                relevant = set(self.anchor_to_sents[query_anchor])
                relevant.discard(query_sent)
                if not relevant:
                    continue

                total += 1
                scores, indices = index.search(sent_embs[i].reshape(1, -1), 50)

                for rank, idx in enumerate(indices[0], 1):
                    if idx == i:  # skip self
                        continue
                    if self.sentences[idx] in relevant:
                        for k in recall:
                            if rank <= k:
                                recall[k] += 1
                        break

            log_parts = [f"Epoch {epoch}"]
            for k in [10, 30, 50]:
                r = recall[k] / max(total, 1) * 100
                log_parts.append(f"S2S-R@{k}={r:.1f}%")

            logger.info(" | ".join(log_parts))
            self.best_recall10 = max(self.best_recall10, recall[10] / max(total, 1))
            return recall[10] / max(total, 1)

    return SentenceRecallEvaluator(model, unique_sents, sent_to_anchor, anchor_to_sents, batch_size)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-path", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "data", "contrastive_pairs_train.json"))
    parser.add_argument("--heldout-path", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "data", "contrastive_pairs_heldout.json"))
    parser.add_argument("--checkpoint-dir", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "trained_models", "concept_anchor_v5"))
    parser.add_argument("--output-dir", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "trained_models", "concept_anchor_v6"))
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--batch-size", type=int, default=24)
    parser.add_argument("--lr", type=float, default=2e-6)
    parser.add_argument("--temperature", type=float, default=0.05)
    parser.add_argument("--warmup-steps", type=int, default=80)
    args = parser.parse_args()

    # Load data
    train_examples = load_contrastive_pairs(args.train_path)
    if not train_examples:
        logger.error("No training pairs found")
        return 1

    import random
    random.seed(42)
    random.shuffle(train_examples)

    # Load checkpoint model
    logger.info("Loading checkpoint: %s", args.checkpoint_dir)
    model = SentenceTransformer(args.checkpoint_dir, device="cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Model device: %s", model.device)

    # Build evaluator — pre-training baseline
    recall_evaluator = build_sentence_recall_evaluator(model, args.heldout_path, batch_size=64)
    if recall_evaluator:
        logger.info("=== Pre-training S2S recall baseline ===")
        recall_evaluator(None, "baseline", 0)

    # Training setup
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=args.batch_size)
    train_loss = losses.MultipleNegativesRankingLoss(model, scale=1.0 / args.temperature)

    os.makedirs(args.output_dir, exist_ok=True)

    logger.info("=== Contrastive Alignment Training ===")
    logger.info("  epochs: %d, batch: %d, lr: %g, temperature: %.3f",
                args.epochs, args.batch_size, args.lr, args.temperature)
    logger.info("  train pairs: %d", len(train_examples))

    steps_per_epoch = max(1, len(train_examples) // args.batch_size)

    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=args.epochs,
        warmup_steps=args.warmup_steps,
        optimizer_params={"lr": args.lr},
        output_path=args.output_dir,
        save_best_model=True,
        show_progress_bar=True,
    )

    # Post-training evaluation
    if recall_evaluator:
        logger.info("=== Post-training S2S recall ===")
        recall_evaluator(None, "final", 0)

    # Save metadata
    meta = {
        "base_model": "concept_anchor_v5",
        "training": "contrastive_alignment",
        "description": "Sentence-to-sentence MNR loss — different expressions → same anchor",
        "training_pairs": len(train_examples),
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
