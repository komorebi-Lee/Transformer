"""Semantic Density Monitor — Phase 3 semantic structure health metrics.

Measures:
- anchor_frequency: per-anchor usage count and proportion
- anchor_entropy: Shannon entropy of anchor distribution
- semantic_dispersion: how evenly anchors cover the concept space
- ontology_density: concentration of anchors at each hierarchy level

Usage:
    D:/anaconda3/envs/zthree5/python.exe semantic_density_monitor.py [--results-path PATH]
    D:/anaconda3/envs/zthree5/python.exe semantic_density_monitor.py --compare BEFORE.json AFTER.json
"""

import json
import logging
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("density_monitor")


def compute_metrics(results, label=""):
    """Compute all semantic density metrics from coding results."""
    coded = [r for r in results if r.get("code")]
    total = len(results)

    if not coded:
        return {"error": "no coded results", "label": label}

    # ── anchor_frequency ──
    freq = Counter(r["code"] for r in coded)
    n_unique = len(freq)
    top_anchor, top_count = freq.most_common(1)[0]
    top10 = freq.most_common(10)

    # ── anchor_entropy (Shannon) ──
    total_coded = len(coded)
    entropy = 0.0
    for count in freq.values():
        p = count / total_coded
        entropy -= p * math.log(p)
    max_entropy = math.log(n_unique)  # theoretical max
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0

    # ── semantic_dispersion ──
    # Gini coefficient of anchor distribution (0 = perfectly even, 1 = monopoly)
    sorted_counts = sorted(freq.values())
    n = len(sorted_counts)
    if n > 0 and sum(sorted_counts) > 0:
        index = list(range(1, n + 1))
        gini = (2 * sum(i * c for i, c in zip(index, sorted_counts)) /
                (n * sum(sorted_counts)) - (n + 1) / n)
    else:
        gini = 0

    # Concentration: what % of sentences use top-N anchors
    top1_pct = top_count / total_coded * 100
    top5_pct = sum(c for _, c in top10[:5]) / total_coded * 100
    top10_pct = sum(c for _, c in top10) / total_coded * 100

    # ── ontology_density ──
    # Measure how concentrated anchors are at each hierarchy level
    # Count anchors per second-category and per third-category
    len_dist = Counter(len(r["code"]) for r in coded)

    # ── semantic sink detection ──
    # Anchors with usage > 2% of total are "sinks"
    sink_threshold = max(0.02 * total_coded, 5)  # at least 5 occurrences
    sinks = [(name, count, count / total_coded * 100)
             for name, count in freq.most_common(50)
             if count >= sink_threshold]

    # ── Coverage analysis ──
    # How many anchors needed to cover 50%/80%/90% of sentences
    cumulative = 0
    p50_anchors = p80_anchors = p90_anchors = 0
    for i, (_, count) in enumerate(freq.most_common(), 1):
        cumulative += count
        if cumulative >= 0.50 * total_coded and p50_anchors == 0:
            p50_anchors = i
        if cumulative >= 0.80 * total_coded and p80_anchors == 0:
            p80_anchors = i
        if cumulative >= 0.90 * total_coded and p90_anchors == 0:
            p90_anchors = i

    return {
        "label": label,
        "total_sentences": total,
        "coded_sentences": total_coded,
        "coding_rate": total_coded / max(total, 1) * 100,
        "unique_anchors": n_unique,
        "anchor_frequency": {
            "top_anchor": top_anchor,
            "top_count": top_count,
            "top_pct": round(top1_pct, 2),
            "top5_pct": round(top5_pct, 2),
            "top10_pct": round(top10_pct, 2),
            "top10": [{"anchor": a, "count": c, "pct": round(c / total_coded * 100, 2)}
                      for a, c in top10],
        },
        "anchor_entropy": {
            "shannon": round(entropy, 4),
            "max_possible": round(max_entropy, 4),
            "normalized": round(normalized_entropy, 4),
            "interpretation": ("excellent" if normalized_entropy > 0.85 else
                              "good" if normalized_entropy > 0.70 else
                              "moderate" if normalized_entropy > 0.50 else
                              "low — risk of semantic collapse"),
        },
        "semantic_dispersion": {
            "gini_coefficient": round(gini, 4),
            "interpretation": ("even" if gini < 0.3 else
                              "moderate" if gini < 0.5 else
                              "concentrated" if gini < 0.7 else
                              "highly concentrated — semantic collapse risk"),
        },
        "ontology_density": {
            "length_distribution": {str(k): v for k, v in sorted(len_dist.items())},
            "avg_length": round(sum(len(r["code"]) for r in coded) / max(len(coded), 1), 1),
        },
        "semantic_sinks": [
            {"anchor": name, "count": count, "pct": round(pct, 2)}
            for name, count, pct in sinks[:20]
        ],
        "coverage": {
            "p50_anchors": p50_anchors,
            "p80_anchors": p80_anchors,
            "p90_anchors": p90_anchors,
        },
        # ── grounding_quality (Phase 4) ──
        "grounding_quality": (_grounding_stats := _compute_grounding_stats(coded, total_coded)),
        "health_score": _compute_health_score(
            normalized_entropy, gini, top1_pct, n_unique, total_coded,
            _grounding_stats),
    }


def _compute_grounding_stats(coded, total_coded):
    """Compute grounding quality metrics if results have original sentence data."""
    # Check if results have original sentences for grounding assessment
    has_sentences = any(r.get("original") or r.get("sentence") for r in coded)
    if not has_sentences:
        return {"available": False, "note": "no original sentences in results"}

    try:
        from grounding_checker import GroundingChecker

        gc = GroundingChecker()
        pairs = []
        for r in coded:
            sent = r.get("original") or r.get("sentence") or ""
            anchor = r.get("code", "")
            if sent and anchor:
                pairs.append((sent, anchor))

        if not pairs:
            return {"available": False, "note": "no sentence-anchor pairs"}

        verdicts = [gc.grounding_verdict(s, a) for s, a in pairs]
        stats = gc.summary_stats(verdicts)

        # Add distribution details
        gs_list = [v["grounding_score"] for v in verdicts]
        gs_sorted = sorted(gs_list)

        stats["available"] = True
        stats["grounding_score_p10"] = round(gs_sorted[max(0, len(gs_sorted) // 10)], 3)
        stats["grounding_score_p25"] = round(gs_sorted[max(0, len(gs_sorted) // 4)], 3)
        stats["grounding_score_median"] = round(gs_sorted[len(gs_sorted) // 2], 3)
        stats["grounding_score_p75"] = round(gs_sorted[min(len(gs_sorted) - 1, 3 * len(gs_sorted) // 4)], 3)
        stats["grounding_score_p90"] = round(gs_sorted[min(len(gs_sorted) - 1, 9 * len(gs_sorted) // 10)], 3)

        # Bad grounding examples (lowest 5)
        worst = sorted(zip(gs_list, [v["jump_level"] for v in verdicts], pairs),
                       key=lambda x: x[0])[:5]
        stats["worst_grounded"] = [
            {"sentence": s[:80], "anchor": a, "score": gs, "level": lvl}
            for gs, lvl, (s, a) in worst
        ]

        return stats
    except Exception as e:
        return {"available": False, "error": str(e)}


def _compute_health_score(entropy, gini, top1_pct, n_unique, n_total,
                          grounding_stats=None):
    """Composite semantic health score (0-100)."""
    score = 100.0

    # Entropy penalty: below 0.7 is concerning
    if entropy < 0.5:
        score -= 30
    elif entropy < 0.7:
        score -= 15
    elif entropy < 0.8:
        score -= 5

    # Gini penalty: above 0.5 is concerning
    if gini > 0.7:
        score -= 30
    elif gini > 0.5:
        score -= 15
    elif gini > 0.3:
        score -= 5

    # Top-1 concentration penalty
    if top1_pct > 10:
        score -= 25
    elif top1_pct > 5:
        score -= 10
    elif top1_pct > 3:
        score -= 5

    # Diversity bonus
    diversity_ratio = n_unique / max(n_total, 1)
    if diversity_ratio < 0.05:
        score -= 15
    elif diversity_ratio < 0.10:
        score -= 5

    # Grounding penalty (Phase 4)
    if grounding_stats and grounding_stats.get("available"):
        well_grounded = grounding_stats.get("well_grounded_ratio", 1.0)
        violations = grounding_stats.get("polarity_violations", 0)
        viol_rate = grounding_stats.get("polarity_violation_rate", 0)

        if well_grounded < 0.30:
            score -= 20
        elif well_grounded < 0.50:
            score -= 10
        elif well_grounded < 0.60:
            score -= 5

        if viol_rate > 0.05:
            score -= 15
        elif violations > 0:
            score -= 5

    return max(0, round(score, 1))


def generate_report(metrics):
    """Generate a human-readable report string."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"  Semantic Density Report: {metrics.get('label', '')}")
    lines.append("=" * 70)
    lines.append(f"")
    lines.append(f"  Sentences: {metrics['total_sentences']} coded={metrics['coded_sentences']} "
                 f"({metrics['coding_rate']:.1f}%)")
    lines.append(f"  Unique anchors: {metrics['unique_anchors']}")
    lines.append(f"  Health score: {metrics['health_score']}/100")
    lines.append(f"")

    # Entropy
    ent = metrics["anchor_entropy"]
    lines.append(f"  ── Anchor Entropy ──")
    lines.append(f"    Shannon: {ent['shannon']} / {ent['max_possible']} "
                 f"(normalized: {ent['normalized']})")
    lines.append(f"    Status: {ent['interpretation']}")
    lines.append(f"")

    # Dispersion
    disp = metrics["semantic_dispersion"]
    lines.append(f"  ── Semantic Dispersion ──")
    lines.append(f"    Gini: {disp['gini_coefficient']} ({disp['interpretation']})")
    lines.append(f"")

    # Frequency
    freq = metrics["anchor_frequency"]
    lines.append(f"  ── Anchor Frequency ──")
    lines.append(f"    Top-1: {freq['top_anchor']} ({freq['top_count']}, {freq['top_pct']}%)")
    lines.append(f"    Top-5 coverage: {freq['top5_pct']}%")
    lines.append(f"    Top-10 coverage: {freq['top10_pct']}%")
    lines.append(f"    Top 10:")
    for item in freq["top10"]:
        bar = "#" * int(item["pct"] * 2)
        lines.append(f"      {item['anchor']}: {item['count']} ({item['pct']}%) {bar}")
    lines.append(f"")

    # Sinks
    sinks = metrics["semantic_sinks"]
    if sinks:
        lines.append(f"  ── Semantic Sinks (>2%) ──")
        for s in sinks[:10]:
            lines.append(f"    {s['anchor']}: {s['count']} ({s['pct']}%)")
    else:
        lines.append(f"  ── Semantic Sinks: NONE [OK] ──")
    lines.append(f"")

    # Coverage
    cov = metrics["coverage"]
    lines.append(f"  ── Coverage ──")
    lines.append(f"    50% covered by {cov['p50_anchors']} anchors")
    lines.append(f"    80% covered by {cov['p80_anchors']} anchors")
    lines.append(f"    90% covered by {cov['p90_anchors']} anchors")
    lines.append(f"")

    # Ontology
    ont = metrics["ontology_density"]
    lines.append(f"  ── Ontology Density ──")
    lines.append(f"    Avg length: {ont['avg_length']} chars")
    lines.append(f"    Length distribution:")
    for length, count in ont["length_distribution"].items():
        lines.append(f"      {length} chars: {count}")
    lines.append(f"")

    # Grounding Quality (Phase 4)
    gq = metrics.get("grounding_quality", {})
    if gq.get("available"):
        lines.append(f"  ── Grounding Quality ──")
        lines.append(f"    Well-grounded ratio: {gq['well_grounded_ratio']*100:.1f}% ({gq['health']})")
        lines.append(f"    Avg grounding score: {gq['avg_grounding_score']:.3f}")
        lines.append(f"    Avg jump distance:  {gq['avg_jump_distance']:.3f}")
        lines.append(f"    Polarity violations: {gq['polarity_violations']} ({gq['polarity_violation_rate']*100:.1f}%)")
        lines.append(f"    Jump distribution:")
        jd = gq.get("jump_level_distribution", {})
        for level in ["direct", "moderate", "significant", "extreme"]:
            count = jd.get(level, 0)
            bar = "#" * min(count, 50)
            lines.append(f"      {level}: {count} {bar}")
        lines.append(f"    Score percentiles: p10={gq.get('grounding_score_p10', '?')} "
                     f"p25={gq.get('grounding_score_p25', '?')} "
                     f"p50={gq.get('grounding_score_median', '?')} "
                     f"p75={gq.get('grounding_score_p75', '?')} "
                     f"p90={gq.get('grounding_score_p90', '?')}")
        worst = gq.get("worst_grounded", [])[:3]
        if worst:
            lines.append(f"    Worst grounded:")
            for w in worst:
                lines.append(f"      [{w['score']:.3f}] {w['anchor']} ← {w['sentence'][:60]}...")

    return "\n".join(lines)


def compare_reports(before_path, after_path):
    """Compare two coding result files and show deltas."""
    with open(before_path, "r", encoding="utf-8") as f:
        before_data = json.load(f)
    with open(after_path, "r", encoding="utf-8") as f:
        after_data = json.load(f)

    before_metrics = compute_metrics(before_data.get("results", []), "BEFORE")
    after_metrics = compute_metrics(after_data.get("results", []), "AFTER")

    print(generate_report(before_metrics))
    print()
    print(generate_report(after_metrics))

    # Delta summary
    print("=" * 70)
    print("  DELTA SUMMARY")
    print("=" * 70)
    delta_items = [
        ("Unique anchors", before_metrics["unique_anchors"], after_metrics["unique_anchors"]),
        ("Health score", before_metrics["health_score"], after_metrics["health_score"]),
        ("Normalized entropy", before_metrics["anchor_entropy"]["normalized"],
         after_metrics["anchor_entropy"]["normalized"]),
        ("Gini coefficient", before_metrics["semantic_dispersion"]["gini_coefficient"],
         after_metrics["semantic_dispersion"]["gini_coefficient"]),
        ("Top-1 pct", before_metrics["anchor_frequency"]["top_pct"],
         after_metrics["anchor_frequency"]["top_pct"]),
        ("Top-5 pct", before_metrics["anchor_frequency"]["top5_pct"],
         after_metrics["anchor_frequency"]["top5_pct"]),
    ]
    for name, b, a in delta_items:
        delta = a - b
        direction = "↑" if delta > 0 else "↓" if delta < 0 else "→"
        print(f"  {name}: {b} → {a} ({direction}{abs(delta):.2f})")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-path", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "coding_test_results.json"))
    parser.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"),
                        help="Compare two result files")
    parser.add_argument("--output", type=str, default=None,
                        help="Save report to file")
    args = parser.parse_args()

    if args.compare:
        compare_reports(args.compare[0], args.compare[1])
        return 0

    # Single-file analysis
    with open(args.results_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    metrics = compute_metrics(data.get("results", []),
                              label=os.path.basename(args.results_path))
    report = generate_report(metrics)
    print(report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info("Report saved to: %s", args.output)

    # Save metrics JSON
    metrics_path = os.path.join(os.path.dirname(args.results_path),
                                "semantic_health.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    logger.info("Metrics saved to: %s", metrics_path)

    # Exit code based on health
    health = metrics.get("health_score", 0)
    if health < 50:
        logger.warning("SEMANTIC HEALTH CRITICAL: %.1f/100 — immediate action needed", health)
        return 1
    elif health < 70:
        logger.warning("SEMANTIC HEALTH WARNING: %.1f/100 — monitor closely", health)
    else:
        logger.info("SEMANTIC HEALTH: %.1f/100 — good", health)
    return 0


if __name__ == "__main__":
    sys.exit(main())
