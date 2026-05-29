"""Anchor Governance System: quality filter + canonical deduplication + clean index.

Phase 2 — Semantic Space Governance:
1. Anchor Quality Filter: score & filter low-quality anchors from v11 data
2. Canonical Anchor Layer: semantic deduplication via connected components
3. Alias Mapping: alias → canonical_anchor for non-canonical concepts
4. Clean Index Rebuild: FAISS index with only canonical anchors

Output:
- cache/anchor_index/concepts.json (clean canonical concepts)
- cache/anchor_index/anchor_index.faiss (clean FAISS index)
- cache/anchor_index/alias_map.json (alias → canonical)
- cache/anchor_index/governance_report.json (stats & merge details)
"""

import json
import logging
import os
import re
import sys
import numpy as np
from collections import defaultdict, Counter
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("anchor_governance")

# ── Quality scoring ──

# Nominalization indicators — concept-bearing noun suffixes
NOMINAL_PATTERNS = re.compile(
    r'(机制|流程|资源|策略|路径|模式|结构|能力|需求|服务|创新|管理|评估|质量|安全|风险|'
    r'种植|养殖|加工|收购|销售|市场|价格|成本|利润|工艺|技术|生产|标准|检验|认证|'
    r'审批|协调|整合|压力|约束|冲突|规范|培训|投资|收入|资金|设备|工具|原料|'
    r'制度|监督|治理|品牌|组织|团队|客户|绩效|渠道|运营|营销|供应链|'
    r'传承|保护|非遗|技艺|文创|文旅|景区|教育|医疗|社区|公益|'
    r'方式|方法|途径|手段|模式|体系|平台|系统|'
    r'关系|认知|意愿|意识|态度|行为|观念|价值|文化|氛围|环境|'
    r'网络|生态|空间|场域|场景|语境|情境|背景|条件|因素|'
    r'效应|作用|功能|属性|特征|特性|类型|形态|状态|阶段|'
    r'布局|分布|格局|趋势|走向|规律|逻辑|原理|机制|'
    r'动机|驱动|动力|障碍|瓶颈|困境|张力|冲突|矛盾|'
    r'身份|角色|地位|层级|差异|边界|规则|惯例|常规|'
    r'话语|叙事|框架|图式|脚本|模板|原型|范畴|概念)'
)

# Oral / non-concept markers — immediate disqualification
ORAL_PARTICLES = re.compile(r'[吧呢啊嘛呀哦哈哎诶噢呃]')
ORAL_PHRASES = re.compile(
    r'(怎么说呢|就是说|我觉得|相当于|这个东西|这个事情|这个问题|'
    r'什么的|之类的|那种感觉|这样子|那样子|那种|这种|'
    r'对不对|是不是|行不行|能不能|要不要|有没有|可不可以|会不会)'
)
FIRST_PERSON_START = re.compile(
    r'^(我|我们|你|你们|他|他们|大家|那个|这个|这些|那些)'
)
QUESTION_START = re.compile(
    r'^(什么|怎么|哪些|怎么样|如何|哪方面|什么时候|为什么|干嘛|为啥|多少|几个)'
)
FRAGMENT_END = re.compile(r'(的|了|着|过|到|在|中|和|与|或|又|还|也|只|不|没)$')
FRAGMENT_START = re.compile(
    r'^(因为|所以|但是|不过|然后|如果|就是|其实|后来|当时|而且|而|但|或者|还是|另外)'
)


def score_anchor_quality(name: str) -> tuple[float, list[str]]:
    """Score an anchor name on 5 dimensions. Returns (score, reasons).

    Dimensions:
    1. Nominalization — is it noun-like?
    2. Standalone meaning — can it be understood independently?
    3. Conceptuality — does it name a concept vs a phrase/sentence?
    4. Cross-text reusability — would it apply across different texts?
    5. Semantic boundary stability — does it have clear scope?
    """
    score = 0.0
    reasons = []

    # ── Hard disqualifiers (any one = dirty) ──
    if ORAL_PARTICLES.search(name):
        reasons.append('ORAL_PARTICLE')
        score -= 40.0
    if ORAL_PHRASES.search(name):
        reasons.append('ORAL_PHRASE')
        score -= 40.0
    if QUESTION_START.search(name):
        reasons.append('QUESTION_FORM')
        score -= 35.0

    # ── Structural issues ──
    if FIRST_PERSON_START.search(name):
        reasons.append('FIRST_PERSON')
        score -= 20.0
    if FRAGMENT_START.search(name):
        reasons.append('FRAGMENT_START')
        score -= 20.0
    if FRAGMENT_END.search(name) and len(name) <= 6:
        reasons.append('FRAGMENT_END')
        score -= 15.0

    # Non-concept characters
    if re.search(r'[0-9０-９]', name):
        reasons.append('DIGITS')
        score -= 10.0

    # ── Length appropriateness ──
    L = len(name)
    if L < 2:
        reasons.append('TOO_SHORT')
        score -= 40.0
    elif L < 3:
        reasons.append('VERY_SHORT')
        score -= 15.0
    elif 3 <= L <= 8:
        score += 10.0  # Ideal anchor length
    elif 9 <= L <= 12:
        score += 3.0
    elif 13 <= L <= 16:
        score -= 5.0
    else:
        reasons.append('TOO_LONG')
        score -= 15.0

    # ── Nominalization (concept-ness) ──
    if NOMINAL_PATTERNS.search(name):
        score += 15.0
    else:
        # Check if it has any concept-bearing structure
        # Verb-only phrases without nominal anchors score lower
        if re.search(r'(缺乏|缺少|不足|受限|导致|影响|推动|降低|提高|开展|进行|建立|引入|获得)', name):
            score += 5.0  # Has action concept
        else:
            score -= 5.0  # Neither nominal nor action — likely weak concept

    # ── Cross-text reusability heuristics ──
    # Entity-specific anchors (company names, person names) are less reusable
    entity_kw = ['苹果', '谷歌', '华为', '小米', '腾讯', '阿里', '百度', '京东',
                 '淘宝', '天猫', '美团', '滴滴', '字节', '抖音', '快手', '微信',
                 '微博', '苏宁', '顺丰', '比亚迪', '特斯拉', '蔚来', '理想',
                 '拼多多', '网易', '携程', '链家', '贝壳']
    if any(kw in name for kw in entity_kw):
        reasons.append('ENTITY_SPECIFIC')
        score -= 20.0

    return score, reasons


QUALITY_THRESHOLD = -10.0  # Anchors scoring below this are filtered out


# ── Canonical deduplication ──

def compute_canonical_groups(concepts, embeddings, threshold=0.85):
    """Cluster semantically equivalent concepts via connected components."""
    from scipy.sparse.csgraph import connected_components
    from scipy.sparse import csr_matrix

    sim_matrix = np.dot(embeddings, embeddings.T)
    adj = (sim_matrix >= threshold).astype(np.int32)
    np.fill_diagonal(adj, 0)

    n_components, labels = connected_components(
        csgraph=csr_matrix(adj), directed=False, return_labels=True)

    groups = defaultdict(list)
    for i, label in enumerate(labels):
        groups[int(label)].append(i)

    return groups, sim_matrix


def select_canonical(members, concepts, sources, sim_matrix, v11_counts):
    """Select the best canonical representative for a group.

    Priority:
    1. From coding library (has descriptions, curated context)
    2. Highest v11 training frequency (most validated by annotators)
    3. Best length (3-8 chars ideal for anchor)
    4. Highest average similarity to group members
    """
    if len(members) == 1:
        return members[0], concepts[members[0]]

    def score(idx):
        name = concepts[idx]
        s = 0.0

        # Library source preference (curated, has description)
        if sources[idx] == "library":
            s += 30.0
        elif sources[idx] == "v11_anchor":
            s += 10.0

        # v11 frequency — more annotated = more validated
        v11_freq = v11_counts.get(name, 0)
        s += min(v11_freq, 50) * 0.5

        # Length preference for anchors (3-8 chars)
        L = len(name)
        if 3 <= L <= 8:
            s += 20.0
        elif 9 <= L <= 12:
            s += 5.0

        # Average similarity to other group members
        if len(members) > 1:
            other_sims = [sim_matrix[idx, j] for j in members if j != idx]
            s += np.mean(other_sims) * 20.0

        return s

    best_idx = max(members, key=score)
    return best_idx, concepts[best_idx]


# ── Training data cleanup ──

def clean_training_data(v11_path, alias_map, quality_anchors):
    """Rewrite v11 training pairs: filter dirty anchors, apply canonical names."""
    with open(v11_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    clean_pairs = []
    removed = 0
    remapped = 0

    for item in data.get("pairs", []):
        anchor = item.get("anchor_code", "").strip()
        sentence = item.get("sentence", "").strip()
        third = item.get("third_category", "").strip()

        if not anchor or not sentence:
            continue

        # Filter: remove dirty anchors
        if anchor not in quality_anchors:
            removed += 1
            continue

        # Remap: alias → canonical
        canonical = alias_map.get(anchor, anchor)
        if canonical != anchor:
            remapped += 1

        clean_pairs.append({
            "sentence": sentence,
            "anchor_code": canonical,
            "third_category": third,
        })

    logger.info("Training data cleanup: %d → %d pairs (removed=%d, remapped=%d)",
                len(data.get("pairs", [])), len(clean_pairs), removed, remapped)
    return clean_pairs


# ── Main ──

def main():
    import argparse
    import faiss
    from sentence_transformers import SentenceTransformer

    parser = argparse.ArgumentParser(description="Anchor Governance System")
    parser.add_argument("--model-path", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "trained_models", "concept_anchor_v5"))
    parser.add_argument("--library-path", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "coding_library.json"))
    parser.add_argument("--v11-path", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "data", "train_anchor_pairs_v3.json"))
    parser.add_argument("--anchor-data", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "data", "clean_anchor_pairs.json"))
    parser.add_argument("--index-dir", type=str,
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            "cache", "anchor_index"))
    parser.add_argument("--dedup-threshold", type=float, default=0.85)
    parser.add_argument("--quality-threshold", type=float, default=-10.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # ── Step 1: Load all data ──
    logger.info("=== Anchor Governance System ===")

    # Library concepts
    with open(args.library_path, "r", encoding="utf-8") as fh:
        lib = json.load(fh)
    enc = lib.get("encoding_library", lib)

    lib_concepts = []
    lib_descs = []
    lib_thirds = []
    for third in enc.get("third_level_codes", []):
        third_name = third.get("name", "").strip()
        for second in third.get("second_level_codes", []):
            name = second.get("name", "").strip()
            desc = second.get("description", "").strip()
            if name:
                lib_concepts.append(name)
                lib_descs.append(desc)
                lib_thirds.append(third_name)

    logger.info("Library concepts: %d", len(lib_concepts))

    # v11 anchor concepts
    v11_concepts = []
    v11_counts = Counter()
    if os.path.exists(args.anchor_data):
        with open(args.anchor_data, "r", encoding="utf-8") as fh:
            anchor_data = json.load(fh)
        for item in anchor_data.get("pairs", []):
            ac = item.get("anchor_code", "").strip()
            if ac:
                v11_counts[ac] += 1
                if ac not in v11_concepts:
                    v11_concepts.append(ac)
    logger.info("v11 anchor concepts: %d unique", len(v11_concepts))

    # Merge all concepts (deduplicate by name)
    all_concepts = list(lib_concepts)
    all_sources = ["library"] * len(lib_concepts)
    all_descs = list(lib_descs)
    all_thirds = list(lib_thirds)

    for ac in v11_concepts:
        if ac not in all_concepts:
            all_concepts.append(ac)
            all_sources.append("v11_anchor")
            all_descs.append("")
            all_thirds.append("")

    # Filter entity-specific
    entity_kw = ['苹果', '谷歌', '华为', '小米', '腾讯', '阿里', '百度', '京东',
                 '淘宝', '天猫', '美团', '滴滴', '字节', '抖音', '快手', '微信',
                 '微博', '苏宁', '顺丰', '比亚迪', '特斯拉', '蔚来', '理想',
                 '拼多多', '网易', '携程', '链家', '贝壳']
    filtered = []
    for i, c in enumerate(all_concepts):
        if not any(kw in c for kw in entity_kw):
            filtered.append(i)

    all_concepts = [all_concepts[i] for i in filtered]
    all_sources = [all_sources[i] for i in filtered]
    all_descs = [all_descs[i] for i in filtered]
    all_thirds = [all_thirds[i] for i in filtered]

    n_before = len(filtered)
    logger.info("Total concepts (after entity filter): %d", n_before)

    # ── Step 2: Quality filter ──
    logger.info("=== Quality Filter ===")
    quality_scores = []
    quality_reasons = {}
    passed_indices = []

    for i, c in enumerate(all_concepts):
        s, reasons = score_anchor_quality(c)
        quality_scores.append(s)
        if reasons:
            quality_reasons[c] = (s, reasons)
        if s >= args.quality_threshold:
            passed_indices.append(i)

    n_filtered = n_before - len(passed_indices)
    logger.info("Passed quality filter: %d / %d (removed %d)",
                len(passed_indices), n_before, n_filtered)

    # Report worst anchors
    worst = sorted(quality_reasons.items(), key=lambda x: x[1][0])[:30]
    if worst:
        logger.info("Worst quality anchors:")
        for name, (s, reasons) in worst[:15]:
            logger.info("  [%+.0f] %s — %s", s, name, reasons)

    # Apply filter
    quality_concepts = [all_concepts[i] for i in passed_indices]
    quality_sources = [all_sources[i] for i in passed_indices]
    quality_descs = [all_descs[i] for i in passed_indices]
    quality_thirds = [all_thirds[i] for i in passed_indices]

    # ── Step 3: Semantic deduplication ──
    logger.info("=== Canonical Deduplication ===")
    logger.info("Encoding %d concepts...", len(quality_concepts))

    model = SentenceTransformer(args.model_path, device="cuda")
    embeddings = model.encode(
        quality_concepts, normalize_embeddings=True,
        show_progress_bar=True, batch_size=64,
    ).astype(np.float32)

    groups, sim_matrix = compute_canonical_groups(
        quality_concepts, embeddings, args.dedup_threshold)

    n_singleton = sum(1 for g in groups.values() if len(g) == 1)
    n_multi = sum(1 for g in groups.values() if len(g) > 1)
    n_in_multi = sum(len(g) for g in groups.values() if len(g) > 1)
    logger.info("Groups: %d total (%d singletons, %d multi-member with %d concepts)",
                len(groups), n_singleton, n_multi, n_in_multi)

    # Select canonicals
    canonical_concepts = []
    canonical_sources = []
    alias_map = {}  # original_name → canonical_name

    for gid in sorted(groups.keys()):
        members = groups[gid]
        best_idx, canonical_name = select_canonical(
            members, quality_concepts, quality_sources, sim_matrix, v11_counts)

        canonical_concepts.append(canonical_name)
        canonical_sources.append(quality_sources[best_idx])

        for mi in members:
            original = quality_concepts[mi]
            if original != canonical_name:
                alias_map[original] = canonical_name

    n_canonical = len(canonical_concepts)
    reduction = len(quality_concepts) - n_canonical
    logger.info("Canonical anchors: %d (reduction: %d, %.1f%%)",
                n_canonical, reduction,
                reduction / max(len(quality_concepts), 1) * 100)
    logger.info("Alias mappings: %d", len(alias_map))

    # Show top merge groups
    multi_groups = sorted(
        [(gid, members) for gid, members in groups.items() if len(members) > 1],
        key=lambda x: -len(x[1]))
    if multi_groups:
        logger.info("Top merge groups:")
        for gid, members in multi_groups[:20]:
            canonical = canonical_concepts[gid] if gid < len(canonical_concepts) else "?"
            members_str = " ← ".join([quality_concepts[i] for i in members])
            logger.info("  [%s] %s", canonical, members_str)

    # ── Step 4: Training data cleanup ──
    logger.info("=== Training Data Cleanup ===")
    quality_set = set(quality_concepts)
    clean_pairs = clean_training_data(args.v11_path, alias_map, quality_set)

    # ── Step 5: Rebuild FAISS index ──
    logger.info("=== Rebuild Clean Index ===")
    logger.info("Encoding %d canonical concepts...", n_canonical)

    canonical_embeddings = model.encode(
        canonical_concepts, normalize_embeddings=True,
        show_progress_bar=True, batch_size=64,
    ).astype(np.float32)

    dim = canonical_embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(canonical_embeddings)

    # ── Step 6: Save (or dry-run) ──
    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN — no files written")
        print("=" * 60)
        print(f"Original concepts:       {n_before}")
        print(f"After quality filter:   {len(quality_concepts)} (-{n_filtered})")
        print(f"After deduplication:    {n_canonical} (-{reduction})")
        print(f"Total reduction:        {n_before - n_canonical} ({(n_before - n_canonical)/max(n_before,1)*100:.1f}%)")
        print(f"Alias mappings:         {len(alias_map)}")
        print(f"Training pairs:         {len(clean_pairs)} (original: {sum(1 for _ in open(args.v11_path, encoding='utf-8'))})")
        print(f"Dedup threshold:        {args.dedup_threshold}")
        print(f"Quality threshold:      {args.quality_threshold}")
        return 0

    os.makedirs(args.index_dir, exist_ok=True)

    # Backup
    concepts_file = os.path.join(args.index_dir, "concepts.json")
    if os.path.exists(concepts_file):
        backup = os.path.join(args.index_dir, "concepts.json.bak")
        os.replace(concepts_file, backup)
        logger.info("Backed up concepts to %s", backup)

    # Save clean concepts
    with open(concepts_file, "w", encoding="utf-8") as fh:
        json.dump({
            "concepts": canonical_concepts,
            "sources": canonical_sources,
            "n_original": n_before,
            "n_canonical": n_canonical,
            "quality_filtered": n_filtered,
            "dedup_reduction": reduction,
            "dedup_threshold": args.dedup_threshold,
            "quality_threshold": args.quality_threshold,
            "governed_at": datetime.now().isoformat(),
        }, fh, ensure_ascii=False, indent=2)

    # Save FAISS index
    faiss.write_index(index, os.path.join(args.index_dir, "anchor_index.faiss"))
    logger.info("Saved clean FAISS index: %d vectors → %s",
                index.ntotal, args.index_dir)

    # Save alias map
    with open(os.path.join(args.index_dir, "alias_map.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "description": "alias → canonical_anchor mapping for concept normalization",
            "mappings": alias_map,
            "n_mappings": len(alias_map),
        }, fh, ensure_ascii=False, indent=2)

    # Save merge details
    merge_info = []
    for gid, members in multi_groups:
        canonical = canonical_concepts[gid] if gid < len(canonical_concepts) else "?"
        merge_info.append({
            "canonical": canonical,
            "members": [quality_concepts[i] for i in members],
            "n_members": len(members),
        })
    with open(os.path.join(args.index_dir, "merge_map.json"), "w", encoding="utf-8") as fh:
        json.dump(merge_info, fh, ensure_ascii=False, indent=2)

    # Save clean training data
    clean_train_path = os.path.join(
        os.path.dirname(args.v11_path),
        "train_anchor_pairs_clean.json")
    with open(clean_train_path, "w", encoding="utf-8") as fh:
        json.dump({"pairs": clean_pairs}, fh, ensure_ascii=False, indent=2)
    logger.info("Saved clean training data: %d pairs → %s",
                len(clean_pairs), clean_train_path)

    # Save governance report
    report = {
        "governed_at": datetime.now().isoformat(),
        "model": args.model_path,
        "dedup_threshold": args.dedup_threshold,
        "quality_threshold": args.quality_threshold,
        "original_concepts": n_before,
        "after_quality_filter": len(quality_concepts),
        "quality_filtered_out": n_filtered,
        "after_deduplication": n_canonical,
        "dedup_reduction": reduction,
        "total_reduction": n_before - n_canonical,
        "reduction_pct": round((n_before - n_canonical) / max(n_before, 1) * 100, 1),
        "alias_mappings": len(alias_map),
        "merge_groups": len(multi_groups),
        "training_pairs_original": len(json.load(open(args.v11_path, encoding="utf-8")).get("pairs", [])),
        "training_pairs_clean": len(clean_pairs),
        "worst_anchors": [
            {"name": name, "score": s, "reasons": r}
            for name, (s, r) in worst[:20]
        ],
    }
    with open(os.path.join(args.index_dir, "governance_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    # ── Summary ──
    logger.info("=" * 60)
    logger.info("Governance complete")
    logger.info("  Original:           %d", n_before)
    logger.info("  After quality:      %d (-%d)", len(quality_concepts), n_filtered)
    logger.info("  After dedup:        %d (-%d)", n_canonical, reduction)
    logger.info("  Final reduction:    %d → %d (%.1f%%)",
                n_before, n_canonical,
                (n_before - n_canonical) / max(n_before, 1) * 100)
    logger.info("  Alias mappings:     %d", len(alias_map))
    logger.info("  Clean training:     %d pairs", len(clean_pairs))
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
