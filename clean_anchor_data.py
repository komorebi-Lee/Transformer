"""Clean v11 training data to extract high-quality (sentence, anchor_code) pairs.

Filters out:
  - Direct substrings (extractive, not abstractive)
  - Function-word endings (的, 了, 就, 只, ...)
  - Speaker labels and pronouns
  - Too-short abstracts (<4 chars)

Output: clean_anchor_pairs.json — high-quality concept anchor training data.
"""

import json
import os
import re
import sys
from collections import defaultdict


# ------------------------------------------------------------------
# Quality filters
# ------------------------------------------------------------------

FUNCTION_WORD_ENDS = set('的了是就只不也都个这那来去说看到在着过中和与或又还')
SPEAKER_PRONOUN_KW = {'讲话人', '发言者', '我们', '他们', '你们', '咱们', '这个', '那个',
                      '采访者', '主持人', '记者', '受访者', '笔者'}


def is_direct_substring(abstract: str, sentence: str) -> bool:
    """Check if abstract is a direct continuous substring of the sentence."""
    return len(abstract) >= 3 and abstract in sentence


def ends_with_function_word(abstract: str) -> bool:
    """Check if abstract ends with a Chinese function word."""
    return len(abstract) > 0 and abstract[-1] in FUNCTION_WORD_ENDS


def contains_speaker_or_pronoun(abstract: str) -> bool:
    """Check if abstract contains speaker labels or conversational pronouns."""
    return any(kw in abstract for kw in SPEAKER_PRONOUN_KW)


def is_pure_number_unit(abstract: str) -> bool:
    """Check if abstract is just numbers/units, not a concept."""
    return bool(re.match(r'^[\d.]+[个只条张次元%％倍年月日天周]$', abstract))


def has_balanced_structure(abstract: str) -> bool:
    """Concept anchors should be self-contained noun phrases, not partial phrases."""
    # Reject if it starts with common sentence-continuation patterns
    bad_starts = {'然后', '所以', '但是', '而且', '因为', '如果', '虽然',
                  '不过', '并且', '因此', '那么', '于是', '接着', '之后'}
    for bs in bad_starts:
        if abstract.startswith(bs):
            return False
    return True


def is_quality_anchor(abstract: str, sentence: str) -> tuple[bool, str]:
    """Return (is_quality, reason)."""
    if not abstract or len(abstract) < 4:
        return False, 'too_short'
    if len(abstract) > 12:
        return False, 'too_long'
    if is_direct_substring(abstract, sentence):
        return False, 'direct_substring'
    if ends_with_function_word(abstract):
        return False, 'function_word_end'
    if contains_speaker_or_pronoun(abstract):
        return False, 'speaker_or_pronoun'
    if is_pure_number_unit(abstract):
        return False, 'number_unit'
    if not has_balanced_structure(abstract):
        return False, 'bad_structure'
    return True, 'ok'


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    v11_path = r"C:\Users\Lenovo\Documents\xwechat_files\wxid_eo5dkcv3sf7522_8ac6\msg\file\2026-05\v11_20260428_164754.json"
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "data", "clean_anchor_pairs.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(v11_path, "r", encoding="utf-8") as fh:
        v11 = json.load(fh)

    training_data = v11.get("training_data", [])
    print(f"Total v11 pairs: {len(training_data)}")

    # ---- Pass 1: filter ----
    good: list[dict] = []
    bad_reasons: dict[str, int] = defaultdict(int)
    bad_samples: dict[str, list[dict]] = defaultdict(list)

    for item in training_data:
        sent = str((item.get("input_sentences", {}) or {}).get("original_content", "")).strip()
        abstract = str(item.get("target_abstract", "")).strip()
        if not sent or not abstract:
            bad_reasons['empty'] += 1
            continue

        ok, reason = is_quality_anchor(abstract, sent)
        if ok:
            good.append({
                "sentence": sent,
                "anchor_code": abstract,
                "second_category": item.get("target_second_category", ""),
                "third_category": item.get("target_third_category", ""),
            })
        else:
            bad_reasons[reason] += 1
            if len(bad_samples[reason]) < 5:
                bad_samples[reason].append({
                    "sentence": sent[:80],
                    "abstract": abstract,
                    "reason": reason,
                })

    print(f"\nQuality anchors: {len(good)} ({len(good)/len(training_data)*100:.1f}%)")
    print(f"Rejected:        {len(training_data) - len(good)} "
          f"({(len(training_data)-len(good))/len(training_data)*100:.1f}%)")
    print("\nRejection reasons:")
    for reason, count in sorted(bad_reasons.items(), key=lambda x: -x[1]):
        print(f"  {reason}: {count}")
        for s in bad_samples.get(reason, [])[:3]:
            print(f"    [{s['abstract']}] <- {s['sentence']}")

    # ---- Pass 2: deduplicate by unique anchor_code ----
    anchor_groups: dict[str, list[str]] = defaultdict(list)
    for item in good:
        anchor_groups[item["anchor_code"]].append(item["sentence"])

    unique_anchors = len(anchor_groups)
    print(f"\nUnique anchor codes: {unique_anchors}")

    # Show anchor distribution
    support_counts = sorted([len(v) for v in anchor_groups.values()], reverse=True)
    print(f"Sentences per anchor: min=1, max={support_counts[0]}, "
          f"avg={sum(support_counts)/len(support_counts):.1f}")

    # Top anchors by support
    top_anchors = sorted(anchor_groups.items(), key=lambda x: -len(x[1]))[:15]
    print("\nTop anchor codes by sentence count:")
    for anchor, sents in top_anchors:
        print(f"  [{len(sents)}x] {anchor}")

    # ---- Save ----
    output = {
        "description": "Cleaned (sentence, anchor_code) pairs from v11 training data",
        "total_pairs": len(good),
        "unique_anchor_codes": unique_anchors,
        "pairs": good,
    }
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)
    print(f"\nSaved: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
