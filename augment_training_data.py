"""Generate synthetic training pairs for library-only and sparse-v11 concepts.

Strategy for 571 library-only concepts + 324 sparse v11 concepts:
1. Same-category sentence sharing: sentences from v11 concepts in the same
   third-level category are shared with library-only concepts
2. Description sentence splitting: multi-sentence descriptions are split into
   individual training pairs
3. Category-context pairs: (third_level_category context, concept_name)

Output: augmented training pairs saved to data/train_anchor_pairs_v4.json
"""

import json
import logging
import os
import re
import sys
from collections import defaultdict, Counter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("augment_data")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_library(library_path):
    with open(library_path, "r", encoding="utf-8") as fh:
        lib = json.load(fh)
    enc = lib.get("encoding_library", lib)

    # Build mappings
    second_to_third = {}
    second_to_desc = {}
    third_to_seconds = defaultdict(list)

    for third in enc.get("third_level_codes", []):
        third_name = third.get("name", "").strip()
        for second in third.get("second_level_codes", []):
            name = second.get("name", "").strip()
            desc = second.get("description", "").strip()
            if name:
                second_to_third[name] = third_name
                second_to_desc[name] = desc
                third_to_seconds[third_name].append(name)

    return second_to_third, second_to_desc, third_to_seconds


def load_v11_pairs(data_path):
    with open(data_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    pairs = []
    anchor_to_sentences = defaultdict(list)
    third_to_sentences = defaultdict(list)
    anchor_counts = Counter()

    for item in data.get("pairs", []):
        sent = item["sentence"].strip()
        anchor = item["anchor_code"].strip()
        third = item.get("third_category", "").strip()
        if sent and anchor:
            pairs.append({"sentence": sent, "anchor_code": anchor, "third_category": third})
            anchor_to_sentences[anchor].append(sent)
            anchor_counts[anchor] += 1
            if third:
                third_to_sentences[third].append(sent)

    return pairs, anchor_to_sentences, third_to_sentences, anchor_counts


def split_description_sentences(desc):
    """Split a description into individual usable sentences."""
    if not desc:
        return []
    # Split on Chinese punctuation
    parts = re.split(r'[。！？；;]', desc)
    sentences = []
    for part in parts:
        part = part.strip()
        # Remove parenthetical references like "（v11权威标注，1次）"
        part = re.sub(r'[（(][^)）]*[)）]', '', part).strip()
        # Need at least 6 meaningful characters
        if len(part) >= 6 and not re.match(r'^[\d\s\.\,，、]+$', part):
            sentences.append(part)
    return sentences


def generate_category_context_pairs(concept_name, third_name, desc):
    """Generate context-based training pairs using third-level category."""
    pairs = []
    # Use description as-is (main signal)
    if desc and len(desc) >= 4:
        clean_desc = re.sub(r'[（(][^)）]*[)）]', '', desc).strip()
        if len(clean_desc) >= 4:
            pairs.append({"sentence": clean_desc, "anchor_code": concept_name,
                          "third_category": third_name, "source": "description"})

    # Category context templates
    templates = [
        "{third}方面的问题",
        "涉及{third}的内容",
        "关于{third}的讨论",
        "{third}相关议题",
    ]
    for tmpl in templates:
        context_sent = tmpl.format(third=third_name)
        pairs.append({"sentence": context_sent, "anchor_code": concept_name,
                      "third_category": third_name, "source": "category_context"})

    return pairs


def main():
    base = os.path.dirname(os.path.abspath(__file__))

    library_path = os.path.join(base, "coding_library.json")
    v11_path = os.path.join(base, "data", "train_anchor_pairs_v3.json")
    output_path = os.path.join(base, "data", "train_anchor_pairs_v4.json")

    # Load data
    second_to_third, second_to_desc, third_to_seconds = load_library(library_path)
    v11_pairs, anchor_to_sentences, third_to_sentences, anchor_counts = load_v11_pairs(v11_path)

    v11_anchors = set(anchor_counts.keys())
    lib_anchors = set(second_to_third.keys())

    # Identify target concepts
    library_only = lib_anchors - v11_anchors
    sparse_v11 = {a for a, c in anchor_counts.items() if c <= 3}

    logger.info("Library-only concepts (no v11 sentences): %d", len(library_only))
    logger.info("Sparse v11 concepts (<=3 examples): %d", len(sparse_v11))
    logger.info("Total target concepts: %d", len(library_only | sparse_v11))

    # ---- Phase 1: Same-category sentence sharing ----
    # For each target concept, borrow sentences from v11 concepts in the same third-level category
    shared_pairs = []
    for concept in (library_only | sparse_v11):
        third = second_to_third.get(concept, "")
        if not third:
            continue

        # Get sentences from v11 concepts in the same third-level category
        category_sentences = third_to_sentences.get(third, [])
        if not category_sentences:
            continue

        # Take up to 5 diverse sentences from the category
        import random
        random.seed(hash(concept) % 10000)
        n_take = min(5, len(category_sentences))
        sampled = random.sample(category_sentences, n_take)
        for sent in sampled:
            shared_pairs.append({
                "sentence": sent,
                "anchor_code": concept,
                "third_category": third,
                "source": "category_sharing",
            })

    logger.info("Category-sharing pairs: %d", len(shared_pairs))

    # ---- Phase 2: Description splitting ----
    desc_pairs = []
    for concept in (library_only | sparse_v11):
        desc = second_to_desc.get(concept, "")
        third = second_to_third.get(concept, "")
        if not desc:
            continue

        # Split description into sentences
        desc_sentences = split_description_sentences(desc)
        for sent in desc_sentences:
            desc_pairs.append({
                "sentence": sent,
                "anchor_code": concept,
                "third_category": third,
                "source": "description_split",
            })

    logger.info("Description-split pairs: %d", len(desc_pairs))

    # ---- Phase 3: Category context templates ----
    context_pairs = []
    for concept in (library_only | sparse_v11):
        third = second_to_third.get(concept, "")
        desc = second_to_desc.get(concept, "")
        ctx = generate_category_context_pairs(concept, third, desc)
        context_pairs.extend(ctx)

    logger.info("Category-context pairs: %d", len(context_pairs))

    # ---- Combine with original v11 pairs ----
    all_pairs = list(v11_pairs)  # Original v11 pairs
    existing_set = set()
    for p in all_pairs:
        key = (p["sentence"], p["anchor_code"])
        existing_set.add(key)

    # Add new pairs (deduplicate)
    new_pairs = []
    for pair_list in [shared_pairs, desc_pairs, context_pairs]:
        for p in pair_list:
            key = (p["sentence"], p["anchor_code"])
            if key not in existing_set:
                existing_set.add(key)
                new_pairs.append(p)

    logger.info("New unique pairs: %d", len(new_pairs))
    logger.info("Total pairs: %d (original: %d + new: %d)",
                len(all_pairs) + len(new_pairs), len(all_pairs), len(new_pairs))

    # ---- Stats ----
    all_concept_counts = Counter()
    for p in all_pairs:
        all_concept_counts[p["anchor_code"]] += 1
    for p in new_pairs:
        all_concept_counts[p["anchor_code"]] += 1

    # How many sparse concepts now have >= 5 examples?
    improved = 0
    for concept in library_only | sparse_v11:
        old_count = anchor_counts.get(concept, 0)
        new_count = all_concept_counts.get(concept, 0)
        if new_count > old_count:
            improved += 1

    logger.info("Concepts with increased examples: %d/%d", improved,
                len(library_only | sparse_v11))

    still_sparse = sum(1 for c in (library_only | sparse_v11)
                       if all_concept_counts.get(c, 0) <= 3)
    logger.info("Still sparse (<=3) after augmentation: %d", still_sparse)

    # ---- Save ----
    output = {"pairs": all_pairs + new_pairs}
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)

    logger.info("Saved augmented training data to: %s", output_path)
    logger.info("Original pairs: %d, New pairs: %d, Total: %d",
                len(all_pairs), len(new_pairs), len(output["pairs"]))

    return 0


if __name__ == "__main__":
    sys.exit(main())
