"""
编码库优化脚本：语义去重 + v11 训练数据扩展

功能：
1. 加载 coding_library.json 和 v11 训练数据
2. 用 bge-small-zh-v1.5 做语义去重（相似度 >= 0.85 视为重复）
3. 每组重复保留最优代表（优先 v11 来源、有描述、名称质量好）
4. v11 的三阶归属优先于库中原有三阶
5. 重建并保存优化后的库

用法:
  # 干跑（仅分析不写文件）
  D:\anaconda3\envs\zthree5\python.exe optimize_coding_library.py --dry-run

  # 正式运行
  D:\anaconda3\envs\zthree5\python.exe optimize_coding_library.py

  # 自定义相似度阈值
  D:\anaconda3\envs\zthree5\python.exe optimize_coding_library.py --threshold 0.80
"""
import json
import os
import re
import sys
import shutil
import argparse
from collections import Counter, defaultdict
from datetime import datetime
from typing import List, Dict, Any, Tuple, Set, Optional

import numpy as np

# ── 路径配置 ────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIBRARY_PATH = os.path.join(BASE_DIR, "coding_library.json")
BACKUP_PATH = os.path.join(BASE_DIR, f"coding_library_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
V11_PATH = os.path.join(BASE_DIR, "standard_answers", "v11_20260428_164754.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "coding_library.json")  # 直接覆盖（已备份）

# ── 常量 ─────────────────────────────────────────────────
SPECIAL_CODES = {"其他各类话题", "其他重要维度"}  # 不参与去重的兜底编码


def load_library() -> Tuple[Dict, List[Dict]]:
    """加载当前编码库，返回 (原始数据, 扁平化的二阶编码列表)"""
    with open(LIBRARY_PATH, 'r', encoding='utf-8') as f:
        lib = json.load(f)

    all_s2 = []
    for tc in lib['encoding_library']['third_level_codes']:
        t3_name = tc['name']
        t3_id = tc['id']
        t3_desc = tc.get('description', '')
        for sc in tc.get('second_level_codes', []):
            all_s2.append({
                'id': sc['id'],
                'name': sc['name'],
                'desc': sc.get('description', ''),
                'third_name': t3_name,
                'third_id': t3_id,
                'third_desc': t3_desc,
                '_source': 'library',
            })
    return lib, all_s2


def load_v11() -> Tuple[List[Dict], Dict[str, str], Dict[Tuple[str, str], Counter]]:
    """加载 v11 训练数据，返回 (训练数据列表, 二阶→三阶映射, 完整配对统计)"""
    with open(V11_PATH, 'r', encoding='utf-8') as f:
        v11 = json.load(f)

    td = v11.get('training_data', [])

    # 统计每个二阶对应的三阶频率
    pair_counts = defaultdict(Counter)
    for entry in td:
        s2 = entry.get('target_second_category', '').strip()
        s3 = entry.get('target_third_category', '').strip()
        if s2 and s3:
            pair_counts[s2][s3] += 1

    # 多数投票：二阶 → 最频繁的三阶
    s2_to_s3 = {}
    for s2, s3_counts in pair_counts.items():
        s2_to_s3[s2] = s3_counts.most_common(1)[0][0]

    return td, s2_to_s3, pair_counts


def load_embedder():
    """加载 sentence-transformer 模型"""
    from sentence_transformers import SentenceTransformer
    sys.path.insert(0, BASE_DIR)
    from config import Config
    model_path = os.path.join(Config.LOCAL_MODELS_DIR, Config.SENTENCE_MODEL_NAME)
    print(f"加载嵌入模型: {model_path}")
    return SentenceTransformer(model_path)


def build_embed_text(code: Dict) -> str:
    """构造用于语义比较的文本（名称 + 描述）"""
    name = code.get('name', '')
    desc = code.get('desc', '')
    if desc and len(desc) > 3:
        return f"{name}: {desc}"
    return name


def find_duplicate_groups(
    codes: List[Dict],
    embeddings: np.ndarray,
    threshold: float,
    v11_s2_names: Set[str],
) -> List[List[int]]:
    """
    语义去重：v11 优先的贪心聚类。

    策略：
    1. v11 编码作为"锚点"——优先处理，非 v11 编码可合并到 v11 组
    2. v11 编码之间绝不合并（每个 v11 编码代表独立概念）
    3. 非 v11 编码之间按阈值合并
    4. 特殊编码（兜底类）不参与去重

    返回 groups，每个 group 是编码索引列表。
    """
    n = len(codes)
    assigned = set()
    groups = []
    sims_cache = np.dot(embeddings, embeddings.T)  # full similarity matrix

    # Phase A: 每个 v11 编码作为独立锚点，吸纳相似的 non-v11 编码
    v11_indices = [i for i, c in enumerate(codes) if c['name'] in v11_s2_names]
    for i in v11_indices:
        if i in assigned:
            continue
        group = [i]
        assigned.add(i)
        for j in range(n):
            if j in assigned:
                continue
            if codes[j]['name'] in SPECIAL_CODES:
                continue
            if codes[j]['name'] in v11_s2_names:
                continue  # 不把 v11 编码合并到其他 v11 组
            if sims_cache[i][j] >= threshold:
                group.append(j)
                assigned.add(j)
        groups.append(group)

    # Phase B: 剩余 non-v11 编码之间做贪心聚类
    for i in range(n):
        if i in assigned:
            continue
        name_i = codes[i]['name']
        if name_i in SPECIAL_CODES:
            groups.append([i])
            assigned.add(i)
            continue

        group = [i]
        assigned.add(i)
        for j in range(i + 1, n):
            if j in assigned:
                continue
            if codes[j]['name'] in SPECIAL_CODES:
                continue
            if codes[j]['name'] in v11_s2_names:
                continue
            if sims_cache[i][j] >= threshold:
                group.append(j)
                assigned.add(j)
        groups.append(group)

    return groups


def score_code_quality(code: Dict, v11_s2_to_s3: Dict[str, str], v11_pair_counts: Dict) -> float:
    """
    评分编码质量，分数越高越好。
    考虑因素：v11 来源、描述质量、名称长度、v11 训练频率
    """
    score = 0.0
    name = code.get('name', '')
    desc = code.get('desc', '')

    # 1. v11 来源加分（最高优先）
    if name in v11_s2_to_s3:
        freq = sum(v11_pair_counts.get(name, Counter()).values())
        score += 10.0 + min(freq, 50) * 0.2  # 最多 +10

    # 2. 描述质量
    if desc and len(desc) > 10:
        score += 3.0
        # 非自动生成描述加分
        if not desc.startswith('包含：') and '自动' not in desc:
            score += 2.0

    # 3. 名称长度（4-16 字最佳）
    name_len = len(name)
    if 6 <= name_len <= 16:
        score += 4.0
    elif 4 <= name_len <= 5:
        score += 2.0
    elif name_len <= 3:
        score -= 3.0  # 太短惩罚
    elif name_len > 16:
        score += 1.0

    # 4. 名称内无特殊字符
    if not re.search(r'[a-zA-Z0-9]{3,}', name):
        score += 1.0  # 纯中文加分

    return score


def select_representative(
    group_indices: List[int],
    codes: List[Dict],
    v11_s2_to_s3: Dict[str, str],
    v11_pair_counts: Dict,
) -> Tuple[int, str, List[int]]:
    """
    从一组重复编码中选择最优代表。
    返回 (代表索引, 选择理由, 移除索引列表)
    """
    if len(group_indices) == 1:
        return group_indices[0], "唯一编码", []

    # v11 编码绝对优先：若组内有 v11 编码，直接选它
    v11_in_group = []
    non_v11 = []
    for idx in group_indices:
        if codes[idx]['name'] in v11_s2_to_s3:
            v11_in_group.append(idx)
        else:
            non_v11.append(idx)

    if v11_in_group:
        # 多个 v11 编码选质量最高的（罕见：仅当 v11 本身有重复名称）
        if len(v11_in_group) > 1:
            v11_in_group.sort(
                key=lambda idx: score_code_quality(codes[idx], v11_s2_to_s3, v11_pair_counts),
                reverse=True
            )
        best_idx = v11_in_group[0]
        return best_idx, "v11绝对优先", [idx for idx in group_indices if idx != best_idx]

    # 非 v11 组内按质量评分选择
    group = [(idx, codes[idx]) for idx in group_indices]
    group.sort(key=lambda x: score_code_quality(x[1], v11_s2_to_s3, v11_pair_counts), reverse=True)

    best_idx, best_code = group[0]
    removed = [idx for idx, _ in group[1:]]

    # 生成理由
    reasons = []
    if best_code['name'] in v11_s2_to_s3:
        reasons.append("v11来源")
    desc = best_code.get('desc', '')
    if desc and len(desc) > 10:
        reasons.append("有描述")
    if 4 <= len(best_code['name']) <= 16:
        reasons.append(f"名称长度适中({len(best_code['name'])}字)")
    if not reasons:
        reasons.append("ID最小")

    return best_idx, "; ".join(reasons), removed


def rebuild_library(
    canonical_codes: List[Dict],
    original_library: Dict,
    v11_s2_to_s3: Dict[str, str],
) -> Dict:
    """
    用去重后的编码重建库结构。
    三阶归属以 v11 为准（若冲突则用 v11 的），
    不存在的三阶自动创建。
    """
    # 按三阶名称分组
    grouped: Dict[str, List[Dict]] = defaultdict(list)
    for code in canonical_codes:
        # 优先用 v11 的三阶归属
        if code['name'] in v11_s2_to_s3:
            t3_name = v11_s2_to_s3[code['name']]
            # 如果与原有不同，记录修正
            if t3_name != code.get('third_name', ''):
                pass  # 将在报告中统计
        else:
            t3_name = code.get('third_name', '')
        grouped[t3_name].append(code)

    # 确保兜底编码存在
    if "其他重要维度" not in grouped:
        grouped["其他重要维度"] = []
    if "其他各类话题" not in grouped:
        # 这是二阶兜底，需要确保在三阶中存在
        pass

    # 获取原有三阶信息（描述等）
    old_t3_info = {}
    for tc in original_library['encoding_library']['third_level_codes']:
        old_t3_info[tc['name']] = {
            'id': tc['id'],
            'desc': tc.get('description', ''),
        }

    # 重建三阶列表
    new_t3_list = []
    next_t3_id = 1
    next_s2_id = 1

    for t3_name in sorted(grouped.keys()):
        s2_list = grouped[t3_name]

        # 获取或分配三阶 ID
        if t3_name in old_t3_info:
            t3_id = old_t3_info[t3_name]['id']
            t3_desc = old_t3_info[t3_name]['desc']
        else:
            # 新三阶
            t3_id = 9000 + next_t3_id  # 用高 ID 区分新增
            t3_desc = ""
            next_t3_id += 1

        # 构建二阶列表
        new_s2_list = []
        used_names = set()
        for code in sorted(s2_list, key=lambda c: str(c.get('id', ''))):
            name = code['name']
            # 跳过同组内的名称重复
            if name in used_names:
                continue
            used_names.add(name)

            new_s2_list.append({
                'id': f"{t3_id}.{next_s2_id}",
                'name': name,
                'description': code.get('desc', ''),
                'third_level': t3_name,
                'third_level_id': t3_id,
            })
            next_s2_id += 1

        new_t3_list.append({
            'id': t3_id,
            'name': t3_name,
            'description': t3_desc,
            'second_level_codes': new_s2_list,
        })

    # 重新分配连续 ID
    for i, tc in enumerate(new_t3_list):
        tc['id'] = i + 1
        for j, sc in enumerate(tc['second_level_codes']):
            sc['id'] = f"{i + 1}.{j + 1}"
            sc['third_level_id'] = i + 1

    new_lib = {
        'encoding_library': {
            'third_level_codes': new_t3_list,
        },
        'version': original_library.get('version', '1.0') + '-optimized',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'description': f"优化版编码库：语义去重 + v11训练数据扩展。原始{original_library.get('description', '')}",
        'optimization_stats': {
            'original_second_count': sum(
                len(tc.get('second_level_codes', []))
                for tc in original_library['encoding_library']['third_level_codes']
            ),
            'optimized_second_count': sum(
                len(tc['second_level_codes']) for tc in new_t3_list
            ),
            'original_third_count': len(original_library['encoding_library']['third_level_codes']),
            'optimized_third_count': len(new_t3_list),
        },
    }

    return new_lib


def dedup_exact_names(codes: List[Dict], v11_s2_to_s3: Dict, v11_pair_counts: Dict) -> List[Dict]:
    """Phase 1: 精确名称去重。同名的只保留最优的一个。"""
    name_groups = defaultdict(list)
    for i, code in enumerate(codes):
        if code['name'] in SPECIAL_CODES:
            # 特殊编码单独保留
            name_groups[code['name'] + '__special__' + str(i)].append((i, code))
        else:
            name_groups[code['name']].append((i, code))

    kept = []
    removed_count = 0
    for name, group in name_groups.items():
        if len(group) == 1:
            kept.append(group[0][1])
        else:
            indices = [g[0] for g in group]
            codes_in_group = [g[1] for g in group]
            best_idx, reason, _ = select_representative(
                indices, codes, v11_s2_to_s3, v11_pair_counts
            )
            kept.append(codes[best_idx])
            removed_count += len(group) - 1

    return kept


def run_optimization(
    threshold: float = 0.85,
    dry_run: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """主优化流程"""
    print("=" * 60)
    print("编码库优化：精确去重 + 语义去重 + v11 扩展")
    print(f"语义相似度阈值: {threshold}")
    print("=" * 60)

    # ── 1. 加载数据 ──
    print("\n[1/6] 加载数据...")
    lib, all_s2 = load_library()
    td, v11_s2_to_s3, v11_pair_counts = load_v11()

    s2_name_counts = Counter(s['name'] for s in all_s2)
    dupes = {k: v for k, v in s2_name_counts.items() if v > 1}
    print(f"  原始二阶编码: {len(all_s2)} 个")
    print(f"  原始三阶编码: {len(lib['encoding_library']['third_level_codes'])} 个")
    print(f"  相同名称重复: {len(dupes)} 个名称 (共 {sum(dupes.values()) - len(dupes)} 个冗余)")
    print(f"  唯一名称: {len(s2_name_counts)} 个")
    print(f"  v11 二阶编码: {len(v11_s2_to_s3)} 个")

    # ── 2. Phase 1: 精确名称去重 ──
    print(f"\n[2/6] Phase 1: 精确名称去重...")
    after_name_dedup = dedup_exact_names(all_s2, v11_s2_to_s3, v11_pair_counts)
    removed_by_name = len(all_s2) - len(after_name_dedup)
    print(f"  精确去重后: {len(after_name_dedup)} 个二阶编码 (移除 {removed_by_name} 个同名重复)")

    # ── 3. Phase 2: 语义去重 ──
    print(f"\n[3/6] Phase 2: 语义去重 (threshold={threshold})...")
    embedder = load_embedder()

    texts = [build_embed_text(s) for s in after_name_dedup]
    print(f"  计算 {len(texts)} 个编码的嵌入向量...")
    embeddings = embedder.encode(texts, normalize_embeddings=True, show_progress_bar=True)

    v11_s2_names = set(v11_s2_to_s3.keys())
    groups = find_duplicate_groups(after_name_dedup, embeddings, threshold, v11_s2_names)
    group_sizes = [len(g) for g in groups]
    print(f"  语义去重后组数: {len(groups)}")
    if group_sizes:
        print(f"  最大组大小: {max(group_sizes)}")
        print(f"  平均组大小: {sum(group_sizes)/len(group_sizes):.2f}")

    # ── 4. 选择代表 ──
    print(f"\n[4/6] 选择每组最优代表...")
    canonical_codes = []
    total_removed = 0
    v11_wins = 0
    desc_wins = 0
    unique_wins = 0

    for group in groups:
        best_idx, reason, removed = select_representative(
            group, after_name_dedup, v11_s2_to_s3, v11_pair_counts
        )
        best_code = after_name_dedup[best_idx]
        canonical_codes.append({
            **best_code,
            '_selection_reason': reason,
            '_group_size': len(group),
        })

        total_removed += len(removed)
        if 'v11' in reason:
            v11_wins += 1
        elif '描述' in reason:
            desc_wins += 1
        else:
            unique_wins += 1

    print(f"  保留: {len(canonical_codes)} 个二阶编码")
    print(f"  移除: {total_removed} 个语义重复编码")
    print(f"  选择依据: v11={v11_wins}, 描述={desc_wins}, 唯一={unique_wins}")

    # ── 5. v11 缺失编码扩展 ──
    print(f"\n[5/8] v11 缺失编码扩展...")
    existing_s2_names = {code['name'] for code in canonical_codes}
    missing_v11 = {
        s2: s3 for s2, s3 in v11_s2_to_s3.items()
        if s2 not in existing_s2_names
    }
    print(f"  v11 缺失编码: {len(missing_v11)} 个")
    added_count = 0
    for s2_name, s3_name in sorted(missing_v11.items()):
        freq = sum(v11_pair_counts.get(s2_name, Counter()).values())
        canonical_codes.append({
            'name': s2_name,
            'desc': f"{s2_name}（v11权威标注，{freq}次）",
            'third_name': s3_name,
            'third_id': -1,
            'third_desc': '',
            'id': f"v11_{s2_name}",
            '_source': 'v11_expansion',
            '_selection_reason': 'v11新增',
            '_group_size': 1,
        })
        added_count += 1
    print(f"  已添加: {added_count} 个 v11 二阶编码到库中")

    # ── 6. v11 三阶修正 ──
    print(f"\n[6/8] v11 三阶归属修正...")
    corrections = 0
    corrected_to_new_t3 = 0
    for code in canonical_codes:
        name = code['name']
        if name in v11_s2_to_s3:
            v11_t3 = v11_s2_to_s3[name]
            if v11_t3 != code['third_name']:
                corrections += 1
                # 检查 v11_t3 是否在旧库中存在
                old_t3_names = {
                    tc['name'] for tc in lib['encoding_library']['third_level_codes']
                }
                if v11_t3 not in old_t3_names:
                    corrected_to_new_t3 += 1
                code['third_name'] = v11_t3
                if verbose:
                    print(f"  修正: \"{name}\" {code['third_name']} → {v11_t3}")

    print(f"  三阶归属修正: {corrections} 个 (其中 {corrected_to_new_t3} 指向新三阶)")

    # ── 7. 重建库 ──
    print(f"\n[7/8] 重建编码库...")
    new_lib = rebuild_library(canonical_codes, lib, v11_s2_to_s3)
    stats = new_lib['optimization_stats']
    print(f"  新二阶编码: {stats['optimized_second_count']} 个")
    print(f"  新三阶编码: {stats['optimized_third_count']} 个")
    print(f"  压缩率: {stats['optimized_second_count']/max(stats['original_second_count'],1)*100:.1f}%")

    # ── 8. 验证 ──
    print(f"\n[8/8] 验证...")

    # 检查 v11 覆盖率
    new_s2_names = set()
    for tc in new_lib['encoding_library']['third_level_codes']:
        for sc in tc['second_level_codes']:
            new_s2_names.add(sc['name'])

    v11_covered = sum(1 for s2 in v11_s2_to_s3 if s2 in new_s2_names)
    v11_coverage = v11_covered / max(len(v11_s2_to_s3), 1) * 100
    print(f"  v11 二阶覆盖率: {v11_coverage:.1f}% ({v11_covered}/{len(v11_s2_to_s3)})")

    # 检查无重复名称
    new_name_counts = Counter()
    for tc in new_lib['encoding_library']['third_level_codes']:
        for sc in tc['second_level_codes']:
            new_name_counts[sc['name']] += 1
    new_dupes = {k: v for k, v in new_name_counts.items() if v > 1}
    if new_dupes:
        print(f"  [WARN] Still {len(new_dupes)} duplicate names")
        for name, count in sorted(new_dupes.items(), key=lambda x: -x[1])[:5]:
            print(f"    \"{name}\" x{count}")
    else:
        print(f"  [OK] No duplicate names")

    # Check v11 pair correctness
    pair_mismatch = 0
    for tc in new_lib['encoding_library']['third_level_codes']:
        for sc in tc['second_level_codes']:
            name = sc['name']
            if name in v11_s2_to_s3:
                expected_t3 = v11_s2_to_s3[name]
                if expected_t3 != tc['name']:
                    pair_mismatch += 1
    print(f"  v11 pair mismatches: {pair_mismatch}")

    # ── 保存 ──
    result = {
        'original_stats': {
            'second_count': stats['original_second_count'],
            'third_count': stats['original_third_count'],
            'unique_names': len(s2_name_counts),
            'duplicate_names': len(dupes),
        },
        'optimized_stats': {
            'second_count': stats['optimized_second_count'],
            'third_count': stats['optimized_third_count'],
            'groups': len(groups),
            'removed': total_removed,
            'v11_corrections': corrections,
            'v11_added': added_count,
            'v11_coverage': v11_coverage,
        },
        'new_library': new_lib,
    }

    if dry_run:
        print(f"\n[DRY RUN] Not writing files")
        print(f"  目标文件: {OUTPUT_PATH}")
        print(f"  相似度阈值: {threshold}")
    else:
        # 备份
        shutil.copy2(LIBRARY_PATH, BACKUP_PATH)
        print(f"\n[OK] Backed up: {BACKUP_PATH}")

        # Save
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(new_lib, f, ensure_ascii=False, indent=2)
        print(f"[OK] Saved: {OUTPUT_PATH}")

    print(f"\n{'=' * 60}")
    print(f"优化完成")
    print(f"  二阶: {stats['original_second_count']} → {stats['optimized_second_count']} (减少 {stats['original_second_count'] - stats['optimized_second_count']})")
    print(f"  三阶: {stats['original_third_count']} → {stats['optimized_third_count']} (减少 {stats['original_third_count'] - stats['optimized_third_count']})")
    print(f"  v11 覆盖率: {v11_coverage:.1f}%")
    print(f"  三阶修正: {corrections}")
    print(f"{'=' * 60}")

    return result


def main():
    parser = argparse.ArgumentParser(description='编码库优化工具')
    parser.add_argument('--dry-run', action='store_true', help='干跑模式，不写文件')
    parser.add_argument('--threshold', type=float, default=0.85,
                        help='语义去重相似度阈值 (默认 0.85)')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    args = parser.parse_args()

    run_optimization(
        threshold=args.threshold,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


if __name__ == '__main__':
    main()
