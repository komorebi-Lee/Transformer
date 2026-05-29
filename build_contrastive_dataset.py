"""Build contrastive dataset: different expressions → same Anchor.

Groups v11 training sentences by anchor code, generates positive pairs
(sentence_i, sentence_j) that share the same concept. Used for supervised
contrastive learning to align diverse expressions to a unified concept space.

Approach: SimCSE-style — positive pairs are different sentences sharing the
same anchor code. In-batch negatives are sentences from different anchors.
Trained with MultipleNegativesRankingLoss.

Output:
- data/contrastive_pairs_train.json — training positive pairs
- data/contrastive_pairs_heldout.json — heldout evaluation pairs
"""

import json
import logging
import os
import random
import sys
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("contrastive_data")


def build_contrastive_dataset(clean_train_path, min_examples=3, train_ratio=0.85,
                               max_pairs_per_anchor=50, random_seed=42):
    """Build positive pairs from anchor-grouped sentences.

    For each anchor with >= min_examples sentences, generates positive pairs
    by pairing different sentences that share the same anchor concept.

    Args:
        clean_train_path: path to train_anchor_pairs_clean.json
        min_examples: minimum sentences per anchor to include
        train_ratio: fraction of anchors for training vs heldout
        max_pairs_per_anchor: cap positive pairs per anchor to avoid imbalance

    Returns:
        train_pairs: list of {"sentence_a": str, "sentence_b": str, "anchor": str}
        heldout_pairs: same format for evaluation
    """
    with open(clean_train_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    # Group sentences by anchor
    anchor_sents = defaultdict(list)
    for item in data.get("pairs", []):
        anchor = item.get("anchor_code", "").strip()
        sent = item.get("sentence", "").strip()
        if anchor and sent and len(sent) >= 8:
            if sent not in anchor_sents[anchor]:
                anchor_sents[anchor].append(sent)

    # Filter to anchors with enough diverse expressions
    rich_anchors = {a: sents for a, sents in anchor_sents.items()
                    if len(sents) >= min_examples}
    logger.info("Anchors with >=%d expressions: %d (from %d total)",
                min_examples, len(rich_anchors), len(anchor_sents))

    # Split anchors into train/heldout
    rng = random.Random(random_seed)
    anchor_list = sorted(rich_anchors.keys())
    rng.shuffle(anchor_list)

    n_train_anchors = int(len(anchor_list) * train_ratio)
    train_anchors = set(anchor_list[:n_train_anchors])
    heldout_anchors = set(anchor_list[n_train_anchors:])

    logger.info("Train anchors: %d, Heldout anchors: %d",
                len(train_anchors), len(heldout_anchors))

    def generate_pairs(anchor_set):
        pairs = []
        for anchor in sorted(anchor_set):
            sents = rich_anchors[anchor]
            n_sents = len(sents)
            # Generate all unique pairs (i, j) where i < j
            all_pairs = []
            for i in range(n_sents):
                for j in range(i + 1, n_sents):
                    all_pairs.append((sents[i], sents[j]))

            # Cap to avoid over-representation of high-frequency anchors
            if len(all_pairs) > max_pairs_per_anchor:
                all_pairs = rng.sample(all_pairs, max_pairs_per_anchor)

            for sent_a, sent_b in all_pairs:
                pairs.append({
                    "sentence_a": sent_a,
                    "sentence_b": sent_b,
                    "anchor": anchor,
                })
        return pairs

    train_pairs = generate_pairs(train_anchors)
    heldout_pairs = generate_pairs(heldout_anchors)

    logger.info("Training pairs: %d", len(train_pairs))
    logger.info("Heldout pairs: %d", len(heldout_pairs))

    # Coverage stats
    train_anchor_lens = [len(rich_anchors[a]) for a in train_anchors]
    heldout_anchor_lens = [len(rich_anchors[a]) for a in heldout_anchors]
    logger.info("Train: %.1f expressions/anchor (max %d), Heldout: %.1f expressions/anchor (max %d)",
                sum(train_anchor_lens) / max(len(train_anchor_lens), 1),
                max(train_anchor_lens) if train_anchor_lens else 0,
                sum(heldout_anchor_lens) / max(len(heldout_anchor_lens), 1),
                max(heldout_anchor_lens) if heldout_anchor_lens else 0)

    return train_pairs, heldout_pairs


def save_pairs(pairs, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump({"pairs": pairs}, fh, ensure_ascii=False, indent=2)
    logger.info("Saved %d pairs to %s", len(pairs), output_path)


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    clean_path = os.path.join(base, "data", "train_anchor_pairs_clean.json")

    if not os.path.exists(clean_path):
        logger.error("Clean training data not found: %s", clean_path)
        logger.error("Run anchor_governance.py first to generate clean data")
        return 1

    train_pairs, heldout_pairs = build_contrastive_dataset(
        clean_path,
        min_examples=3,
        train_ratio=0.85,
        max_pairs_per_anchor=50,
    )

    train_output = os.path.join(base, "data", "contrastive_pairs_train.json")
    heldout_output = os.path.join(base, "data", "contrastive_pairs_heldout.json")

    save_pairs(train_pairs, train_output)
    save_pairs(heldout_pairs, heldout_output)

    # Print sample pairs
    rng = random.Random(42)
    samples = rng.sample(train_pairs, min(5, len(train_pairs)))
    print("\n=== Sample contrastive pairs ===")
    for i, sp in enumerate(samples):
        print(f"\n[{i+1}] Anchor: {sp['anchor']}")
        print(f"  A: {sp['sentence_a'][:100]}")
        print(f"  B: {sp['sentence_b'][:100]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
