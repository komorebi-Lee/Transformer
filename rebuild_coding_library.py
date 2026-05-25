"""
编码库全面重建工具 v2 — 基于语义嵌入去重
数据来源:
1. D:\c盘\新增编码库编码\*.csv (列1=一阶, 列2=二阶, 列3=三阶)
2. v11 训练数据 (training_data 中的二阶/三阶标注)
3. 现有 coding_library.json

策略:
- bge-small-zh-v1.5 语义嵌入聚类去重
- v11 数据优先作为权威来源
- 广泛覆盖, 不过于具体
- 目标: ~400-600 三阶, ~700-1000 二阶
"""

import json
import os
import re
import sys
import csv
import shutil
import numpy as np
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime

# ============================================================
# 配置
# ============================================================
CSV_DIR = r"D:\c盘\新增编码库编码"
V11_PATH = r"C:\Users\Lenovo\Documents\xwechat_files\wxid_eo5dkcv3sf7522_8ac6\msg\file\2026-05\v11_20260428_164754.json"
LIBRARY_PATH = "coding_library.json"
BACKUP_PATH_TEMPLATE = "coding_library_backup_{}.json"
LOCAL_MODELS_DIR = "local_models"
BGE_MODEL_DIR = "bge-small-zh-v1.5"

# 语义去重阈值 (降低了以更积极合并相似编码)
S3_SIMILARITY_THRESHOLD = 0.76   # 三阶聚类阈值
S2_SIMILARITY_THRESHOLD = 0.72   # 二阶聚类阈值

# 编码名称长度限制
MIN_NAME_LENGTH = 3
MAX_NAME_LENGTH = 12  # 更严格: 超过12字的通常太具体

# ============================================================
# 过于具体的编码模式
# ============================================================
OVERLY_SPECIFIC_PATTERNS = [
    re.compile(r'^\d{4}[-~]\d{4}$'),           # 年份范围: 1979-1994
    re.compile(r'^\d{4}年'),                     # 以年份开头: 2000年虚增利润
    re.compile(r'^\d{2,}[个项条种次位只]'),      # 数字+量词: 42个工贸公司
    re.compile(r'^\d{2,}[以之]?[前后]'),         # 数字+时间: 80年代
    re.compile(r'^\d+%'),                        # 百分比
    re.compile(r'^\d{2,}'),                      # 纯数字开头
    re.compile(r'^[A-Z]{2,}[-\s/]'),            # 英文缩写开头: B/S架构, CEO双元
    re.compile(r'^[A-Z][a-z]+[-\s]'),            # 英文单词开头
    re.compile(r'[A-Z]{3,}'),                    # 含3+大写字母缩写
    re.compile(r'^.{1,2}$'),                     # 1-2字的名称 (太短)
    re.compile(r'\d{4}'),                        # 含4位数字(年份)
    re.compile(r'^[路径模式阶段类型][A-Z一二三四五六七八九十]$'),  # 字母/数字编号: 路径A, 模式二
    re.compile(r'^[A-Z]$'),                      # 单个字母
    re.compile(r'[+/]'),                         # 含+/的复合编码: 生产制造+技术引进, AC/DC
    re.compile(r'^\d+[大类种方面维度层次]'),      # 2大类, 3个维度
    re.compile(r'^\d+[-~]\d+'),                  # 任何数字范围: 80-90
    re.compile(r'^第[一二三四五六七八九十\d]'),    # 第X阶段/第X类
]

# 需要过滤的专有名词 (太具体的案例)
OVERLY_SPECIFIC_KEYWORDS = [
    '华为', '腾讯', '阿里', '百度', '京东', '美团', '滴滴', '字节', '小米',
    '马云', '马化腾', '任正非', '雷军', '张一鸣', '王兴',
    '上海国资', '深圳', '北京', '广州', '杭州',
    '大股东', '控股股东', '跨国公司',
]

# 太具体/技术性的关键词 (领域特定，不适合通用编码库)
DOMAIN_SPECIFIC_KEYWORDS = [
    'B/S架构', 'OEM', 'ODM', 'OBM', 'IBM', 'DM阶段', 'EM阶段', 'IT不成熟',
    'MPC模型', 'MOA框架', 'ESOP模式', 'CSO牵头', 'CEO双元',
    'AR/CAR', 'CAR显著', 'CAR为负', 'CAR衡量',
    '7天决策', '7天分权', '7天构型', '7天治理', '7天激励', '7天突变',
    '作业长制', '东掌制', '花红制',
    # 过于具体的组合模式
    '+监督', '+约束', '+激励', '+惩罚', '+治理',
    '//', '→', '——',
]

def is_overly_specific(name: str) -> bool:
    """判断编码名是否过于具体"""
    for pat in OVERLY_SPECIFIC_PATTERNS:
        if pat.search(name):
            return True
    for kw in OVERLY_SPECIFIC_KEYWORDS:
        if kw in name:
            return True
    for kw in DOMAIN_SPECIFIC_KEYWORDS:
        if kw in name:
            return True
    if len(name) < MIN_NAME_LENGTH:
        return True
    if len(name) > MAX_NAME_LENGTH:
        return True
    return False

def is_domain_specific_jargon(name: str) -> bool:
    """判断是否为领域特定术语"""
    for kw in DOMAIN_SPECIFIC_KEYWORDS:
        if kw in name:
            return True
    return False


# ============================================================
# 步骤1: 加载参考数据
# ============================================================
def load_csv_reference(csv_dir: str) -> List[Tuple[str, str]]:
    """从CSV文件加载 (二阶, 三阶) 配对"""
    pairs: List[Tuple[str, str]] = []
    if not os.path.exists(csv_dir):
        print(f"  [WARN] CSV目录不存在: {csv_dir}")
        return pairs

    for fname in sorted(os.listdir(csv_dir)):
        if not fname.endswith('.csv'):
            continue
        fpath = os.path.join(csv_dir, fname)
        for encoding in ['gbk', 'gb2312', 'gb18030', 'utf-8-sig', 'utf-8']:
            try:
                with open(fpath, 'r', encoding=encoding) as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) < 3:
                            continue
                        s2 = row[1].strip()
                        s3 = row[2].strip()
                        if not s2 or not s3:
                            continue
                        if s2 == '二阶主题' or s2 == '二阶编码':
                            continue
                        if not is_overly_specific(s2) and not is_overly_specific(s3):
                            pairs.append((s2, s3))
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

    # 去重
    return list(set(pairs))


def load_v11_reference(v11_path: str) -> Tuple[List[Tuple[str, str]], Dict[Tuple[str, str], int]]:
    """从v11训练数据加载 (二阶, 三阶) 配对, 返回去重列表和频率字典"""
    pair_counts: Dict[Tuple[str, str], int] = defaultdict(int)
    if not os.path.exists(v11_path):
        print(f"  [WARN] v11文件不存在: {v11_path}")
        return [], pair_counts

    try:
        with open(v11_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        training_data = data.get('training_data', [])
        for item in training_data:
            s2 = item.get('target_second_category', '').strip()
            s3 = item.get('target_third_category', '').strip()
            if not s2 or not s3:
                continue
            # 排除二阶=三阶的退化情况 和 过于具体的
            if s2 == s3:
                continue
            if is_overly_specific(s2) or is_overly_specific(s3):
                continue
            if is_domain_specific_jargon(s2) or is_domain_specific_jargon(s3):
                continue
            pair_counts[(s2, s3)] += 1
    except Exception as e:
        print(f"  [WARN] v11加载失败: {e}")

    # 只保留出现>=2次的配对 (过滤噪声)
    pairs = [(s2, s3) for (s2, s3), cnt in pair_counts.items() if cnt >= 2]
    return pairs, dict(pair_counts)


def load_existing_library(lib_path: str) -> Tuple[List[Tuple[str, str]], List[Dict]]:
    """加载现有编码库, 返回 (二阶,三阶)配对 和 原三阶列表"""
    pairs: List[Tuple[str, str]] = []
    third_codes: List[Dict] = []

    if not os.path.exists(lib_path):
        print(f"  [WARN] 库文件不存在: {lib_path}")
        return pairs, third_codes

    with open(lib_path, 'r', encoding='utf-8') as f:
        lib = json.load(f)

    el = lib.get('encoding_library', {})
    for tc in el.get('third_level_codes', []):
        tc_name = tc.get('name', '').strip()
        if not tc_name or is_overly_specific(tc_name):
            continue
        for sc in tc.get('second_level_codes', []):
            sc_name = sc.get('name', '').strip()
            if not sc_name or is_overly_specific(sc_name):
                continue
            pairs.append((sc_name, tc_name))
        # 保留三阶的描述信息
        third_codes.append({
            'name': tc_name,
            'description': tc.get('description', ''),
        })

    return pairs, third_codes


# ============================================================
# 步骤2: 语义嵌入和聚类
# ============================================================
def load_embedding_model():
    """加载 bge-small-zh-v1.5 模型"""
    from sentence_transformers import SentenceTransformer

    local_path = os.path.join(LOCAL_MODELS_DIR, BGE_MODEL_DIR)
    if os.path.exists(local_path) and os.path.exists(os.path.join(local_path, "config.json")):
        print(f"  从本地加载模型: {local_path}")
        return SentenceTransformer(local_path)
    else:
        print(f"  从HF加载模型: BAAI/bge-small-zh-v1.5")
        model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
        os.makedirs(local_path, exist_ok=True)
        model.save(local_path)
        return model


def compute_embeddings(texts: List[str], model, batch_size: int = 128) -> np.ndarray:
    """批量计算文本嵌入"""
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return embeddings


def greedy_cluster(
    names: List[str],
    embeddings: np.ndarray,
    threshold: float,
) -> Dict[int, List[int]]:
    """
    贪心聚类: 遍历每个元素，将其归入第一个相似度>=阈值的已有簇
    返回 {簇中心索引: [成员索引列表]}
    """
    if len(names) == 0:
        return {}

    n = len(names)
    # 按名称长度排序 (倾向选择较短的作为中心，因为更通用)
    order = sorted(range(n), key=lambda i: len(names[i]))

    clusters: Dict[int, List[int]] = {}  # center_idx -> [member_indices]
    assigned = set()

    for idx in order:
        if idx in assigned:
            continue
        # 尝试归入已有簇
        matched = False
        for center_idx in clusters:
            sim = float(np.dot(embeddings[idx], embeddings[center_idx]))
            if sim >= threshold:
                clusters[center_idx].append(idx)
                assigned.add(idx)
                matched = True
                break
        if not matched:
            # 创建新簇
            clusters[idx] = [idx]
            assigned.add(idx)

    return clusters


# ============================================================
# 步骤3: 选择最佳代表
# ============================================================
def select_representatives(
    clusters: Dict[int, List[int]],
    names: List[str],
    v11_s2_names: Set[str],
    v11_s3_names: Set[str],
    v11_pair_map: Dict[str, str],
    existing_descriptions: Dict[str, str],
    level: str,
) -> Dict[int, str]:
    """
    为每个簇选择最佳代表名称
    优先级: v11中存在 > 有描述 > 名称长度适中(4-12字) > 最短
    """
    representatives: Dict[int, str] = {}
    v11_names = v11_s3_names if level == 'third' else v11_s2_names

    for center_idx, member_indices in clusters.items():
        # 收集所有候选名称
        candidates = [(idx, names[idx]) for idx in member_indices]

        # 评分: v11=100, 有描述=50, 长度适中=20, 长度惩罚=length_penalty
        def score(idx: int, name: str) -> Tuple[int, int, int, int, int]:
            in_v11 = 100 if name in v11_names else 0
            has_desc = 50 if name in existing_descriptions and existing_descriptions[name] else 0
            length_ok = 20 if 4 <= len(name) <= 12 else 0
            length_penalty = -abs(len(name) - 6)
            # 惩罚含+/的复合名称
            compound_penalty = -200 if ('+' in name or '/' in name) else 0
            return (in_v11, has_desc, length_ok, length_penalty, compound_penalty)

        best_idx, best_name = max(candidates, key=lambda x: score(x[0], x[1]))
        representatives[center_idx] = best_name

    return representatives


# ============================================================
# 步骤4: 合并配对并解决冲突
# ============================================================
def build_consolidated_pairs(
    csv_pairs: List[Tuple[str, str]],
    v11_pairs: List[Tuple[str, str]],
    v11_freq: Dict[Tuple[str, str], int],
    existing_pairs: List[Tuple[str, str]],
    s2_representatives: Dict[str, str],
    s3_representatives: Dict[str, str],
) -> Dict[str, str]:
    """
    合并所有来源的配对，应用语义去重映射，解决冲突
    权重: v11高频 > v11低频 > existing > csv
    返回 {二阶名称 -> 三阶名称}
    """
    # 应用去重映射
    def map_s2(name: str) -> str:
        return s2_representatives.get(name, name)

    def map_s3(name: str) -> str:
        return s3_representatives.get(name, name)

    # 统计每个 (去重后二阶 -> 去重后三阶) 的加权频率
    pair_weight: Dict[Tuple[str, str], float] = defaultdict(float)

    for s2, s3 in existing_pairs:
        ms2, ms3 = map_s2(s2), map_s3(s3)
        pair_weight[(ms2, ms3)] += 1.0

    for s2, s3 in csv_pairs:
        ms2, ms3 = map_s2(s2), map_s3(s3)
        pair_weight[(ms2, ms3)] += 0.5  # CSV权重最低

    for s2, s3 in v11_pairs:
        ms2, ms3 = map_s2(s2), map_s3(s3)
        freq = v11_freq.get((s2, s3), 1)
        # v11高频(>=5次)权重很高, 低频中等权重
        v11_weight = min(freq, 10) * 1.5
        pair_weight[(ms2, ms3)] += v11_weight

    # 为每个二阶选择最佳三阶
    s2_to_candidates: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for (s2, s3), weight in pair_weight.items():
        s2_to_candidates[s2][s3] += weight

    result: Dict[str, str] = {}
    for s2, s3_weights in s2_to_candidates.items():
        # 选择权重最高的三阶
        best_s3 = max(s3_weights, key=s3_weights.get)
        result[s2] = best_s3

    return result


# ============================================================
# 步骤5: 生成描述
# ============================================================
def generate_description(code_name: str, parent_name: str = "") -> str:
    """为编码生成描述文本"""
    domain_hints = {
        '技术': '与技术研发、技术创新、技术应用相关的内容',
        '管理': '与组织管理、人员管理、流程管理相关的内容',
        '市场': '与市场策略、营销、客户、销售相关的内容',
        '资源': '与资源配置、资源获取、资源整合相关的内容',
        '创新': '与创新方法、创新机制、创新成果相关的内容',
        '服务': '与服务流程、服务质量、客户服务相关的内容',
        '质量': '与质量标准、质量控制、质量改进相关的内容',
        '团队': '与团队协作、团队建设、团队文化相关的内容',
        '战略': '与战略规划、战略执行、战略调整相关的内容',
        '文化': '与企业文化、组织文化、价值观念相关的内容',
        '制度': '与制度建设、制度执行、制度完善相关的内容',
        '风险': '与风险识别、风险评估、风险应对相关的内容',
        '合作': '与合作关系、合作模式、合作效果相关的内容',
        '知识': '与知识管理、知识共享、知识传承相关的内容',
        '权力': '与权力分配、权力运行、权力制衡相关的内容',
        '关系': '与关系网络、关系维护、关系协调相关的内容',
        '传承': '与技艺传承、文化传承、代际传承相关的内容',
        '手工': '与手工技艺、手工制作、手工艺传承相关的内容',
        '设计': '与设计理念、设计创新、设计方法相关的内容',
        '品牌': '与品牌建设、品牌传播、品牌价值相关的内容',
        '渠道': '与渠道建设、渠道管理、渠道拓展相关的内容',
        '供应链': '与供应链管理、供应链优化、供应链协同相关的内容',
        '生产': '与生产工艺、生产流程、生产效率相关的内容',
        '产品': '与产品开发、产品设计、产品质量相关的内容',
        '学习': '与学习过程、学习机制、知识获取相关的内容',
        '制度': '与制度建设、制度执行、制度完善相关的内容',
        '治理': '与组织治理、治理结构、治理机制相关的内容',
        '组织': '与组织结构、组织变革、组织能力相关的内容',
        '绩效': '与绩效评估、绩效管理、绩效改进相关的内容',
        '激励': '与激励制度、激励方式、激励效果相关的内容',
    }

    parts = [code_name]
    if parent_name and parent_name != code_name:
        parts.append(f"属于{parent_name}类别")

    for keyword, hint in domain_hints.items():
        if keyword in code_name:
            parts.append(hint)
            break

    return '。'.join(parts)


# ============================================================
# 步骤6: 重建库结构
# ============================================================
def rebuild_library(
    s2_to_s3: Dict[str, str],
    existing_third_codes: List[Dict],
    s3_representatives: Dict[str, str],
) -> Dict:
    """重建编码库 JSON 结构"""
    # 构建 三阶 -> [二阶列表]
    s3_to_s2: Dict[str, List[str]] = defaultdict(list)
    for s2, s3 in s2_to_s3.items():
        if s2 and s3 and s2 != s3:
            s3_to_s2[s3].append(s2)

    # 从现有库中获取三阶编码的描述信息
    existing_s3_desc: Dict[str, str] = {}
    for tc in existing_third_codes:
        name = tc.get('name', '').strip()
        desc = tc.get('description', '').strip()
        if name and desc:
            existing_s3_desc[name] = desc
            # 也将去重映射后的名称关联上
            mapped = s3_representatives.get(name, name)
            if mapped != name and not existing_s3_desc.get(mapped):
                existing_s3_desc[mapped] = desc

    # 排序: 包含更多二阶编码的三阶排在前面
    sorted_s3 = sorted(s3_to_s2.items(), key=lambda x: len(x[1]), reverse=True)

    third_level_codes = []
    s3_id = 1
    s2_id_counter = 1

    for s3_name, s2_names in sorted_s3:
        desc = existing_s3_desc.get(s3_name, '') or generate_description(s3_name)

        second_codes = []
        for s2_name in sorted(s2_names):
            second_codes.append({
                'id': f"{s3_id}.{s2_id_counter}",
                'name': s2_name,
                'description': generate_description(s2_name, s3_name),
                'third_level': s3_name,
                'third_level_id': s3_id,
            })
            s2_id_counter += 1

        third_level_codes.append({
            'id': s3_id,
            'name': s3_name,
            'description': desc,
            'second_level_codes': second_codes,
        })
        s3_id += 1

    total_s2 = sum(len(tc['second_level_codes']) for tc in third_level_codes)

    return {
        'encoding_library': {
            'third_level_codes': third_level_codes,
        },
        'version': '4.0-rebuilt-semantic',
        'created_at': datetime.now().isoformat(),
        'description': '基于语义嵌入去重重建，v11权威优先，广泛覆盖',
        'optimization_stats': {
            'third_level_count': len(third_level_codes),
            'second_level_count': total_s2,
            'unique_pairs': len(s2_to_s3),
        }
    }


# ============================================================
# 主流程
# ============================================================
def main():
    dry_run = '--dry-run' in sys.argv

    print("=" * 60)
    print("编码库全面重建工具 v2 (语义嵌入去重)")
    if dry_run:
        print("[DRY RUN] 只分析，不写入")
    print("=" * 60)

    # Step 1: 加载所有数据源
    print("\n[1/6] 加载参考数据...")
    csv_pairs = load_csv_reference(CSV_DIR)
    print(f"  CSV参考数据: {len(csv_pairs)} 个有效配对 (过滤过于具体后)")

    v11_pairs, v11_freq = load_v11_reference(V11_PATH)
    print(f"  v11训练数据: {len(v11_pairs)} 个高频配对 (>=2次出现, 已过滤)")

    existing_pairs, existing_third = load_existing_library(LIBRARY_PATH)
    print(f"  现有编码库: {len(existing_pairs)} 个配对, {len(existing_third)} 个三阶")

    # Step 2: 收集所有唯一名称和配对
    print("\n[2/6] 语义去重 — 生成嵌入向量...")

    all_s2_names = set()
    all_s3_names = set()
    for s2, s3 in csv_pairs + v11_pairs + existing_pairs:
        all_s2_names.add(s2)
        all_s3_names.add(s3)

    # v11权威名称集合
    v11_s2_names = {s2 for s2, s3 in v11_pairs}
    v11_s3_names = {s3 for s2, s3 in v11_pairs}
    # v11配对映射
    v11_pair_map = {s2: s3 for s2, s3 in v11_pairs}

    # 现有描述
    existing_descriptions = {tc['name']: tc['description'] for tc in existing_third if tc.get('description')}

    print(f"  去重前: {len(all_s2_names)} 个二阶, {len(all_s3_names)} 个三阶")

    # 加载模型
    model = load_embedding_model()

    # 三阶去重
    s3_list = list(all_s3_names)
    if s3_list:
        print(f"  计算三阶嵌入 ({len(s3_list)} 个)...")
        s3_embeddings = compute_embeddings(s3_list, model)
        s3_clusters = greedy_cluster(s3_list, s3_embeddings, S3_SIMILARITY_THRESHOLD)
        print(f"  三阶聚类: {len(s3_clusters)} 个簇 (从 {len(s3_list)} 去重)")
        s3_repr = select_representatives(
            s3_clusters, s3_list, v11_s2_names, v11_s3_names,
            v11_pair_map, existing_descriptions, level='third'
        )
        # 构建映射: 被合并的名称 -> 代表名称
        s3_remap: Dict[str, str] = {}
        for center_idx, member_indices in s3_clusters.items():
            representative = s3_repr[center_idx]
            for idx in member_indices:
                s3_remap[s3_list[idx]] = representative
    else:
        s3_remap = {}

    # 二阶去重
    s2_list = list(all_s2_names)
    if s2_list:
        print(f"  计算二阶嵌入 ({len(s2_list)} 个)...")
        s2_embeddings = compute_embeddings(s2_list, model)
        s2_clusters = greedy_cluster(s2_list, s2_embeddings, S2_SIMILARITY_THRESHOLD)
        print(f"  二阶聚类: {len(s2_clusters)} 个簇 (从 {len(s2_list)} 去重)")
        s2_repr = select_representatives(
            s2_clusters, s2_list, v11_s2_names, v11_s3_names,
            v11_pair_map, existing_descriptions, level='second'
        )
        s2_remap: Dict[str, str] = {}
        for center_idx, member_indices in s2_clusters.items():
            representative = s2_repr[center_idx]
            for idx in member_indices:
                s2_remap[s2_list[idx]] = representative
    else:
        s2_remap = {}

    unique_s2 = len(set(s2_remap.values()))
    unique_s3 = len(set(s3_remap.values()))
    print(f"  去重后: {unique_s2} 个二阶, {unique_s3} 个三阶")

    # 显示一些聚类示例
    print("\n  聚类示例 (三阶):")
    shown = 0
    for center_idx, member_indices in sorted(s3_clusters.items(), key=lambda x: -len(x[1])):
        if len(member_indices) >= 2 and shown < 8:
            members = [s3_list[i] for i in member_indices]
            if len(members) > 5:
                members_str = ', '.join(members[:5]) + f' ... (+{len(members)-5})'
            else:
                members_str = ', '.join(members)
            print(f"    {s3_repr[center_idx]} ← {members_str}")
            shown += 1

    print("\n  聚类示例 (二阶):")
    shown = 0
    for center_idx, member_indices in sorted(s2_clusters.items(), key=lambda x: -len(x[1])):
        if len(member_indices) >= 2 and shown < 8:
            members = [s2_list[i] for i in member_indices]
            if len(members) > 5:
                members_str = ', '.join(members[:5]) + f' ... (+{len(members)-5})'
            else:
                members_str = ', '.join(members)
            print(f"    {s2_repr[center_idx]} ← {members_str}")
            shown += 1

    # Step 3: 合并配对
    print("\n[3/6] 合并配对并解决冲突...")
    consolidated = build_consolidated_pairs(
        csv_pairs, v11_pairs, v11_freq, existing_pairs, s2_remap, s3_remap
    )
    print(f"  最终配对: {len(consolidated)}")

    # Step 4: 覆盖范围分析
    print("\n[4/6] 覆盖范围分析...")
    s3_counts = Counter(consolidated.values())
    s3_final = len(s3_counts)
    s2_final = len(consolidated)

    print(f"  最终二阶编码: {s2_final}")
    print(f"  最终三阶编码: {s3_final}")

    counts = list(s3_counts.values())
    if counts:
        print(f"  平均每个三阶含二阶数: {sum(counts)/len(counts):.1f}")
        print(f"  最多: {max(counts)}, 最少: {min(counts)}")
        print(f"  含1个二阶的三阶数: {sum(1 for c in counts if c == 1)}")
        print(f"  含2-3个二阶的三阶数: {sum(1 for c in counts if 2 <= c <= 3)}")
        print(f"  含4+个二阶的三阶数: {sum(1 for c in counts if c >= 4)}")

    # v11覆盖率
    v11_s2_covered = sum(1 for s2 in v11_s2_names if s2_remap.get(s2, s2) in consolidated)
    print(f"  v11二阶覆盖率: {v11_s2_covered}/{len(v11_s2_names)} ({100*v11_s2_covered/max(1,len(v11_s2_names)):.0f}%)")

    # 示例
    print("\n  示例二阶->三阶对应:")
    samples = list(consolidated.items())[:15]
    for s2, s3 in samples:
        print(f"    {s2} -> {s3}")

    if dry_run:
        print("\n[DRY RUN] 完成。不写入文件。")
        return

    # Step 5: 重建库
    print("\n[5/6] 重建编码库...")
    new_lib = rebuild_library(consolidated, existing_third, s3_remap)

    # 备份原库
    backup_path = BACKUP_PATH_TEMPLATE.format(datetime.now().strftime('%Y%m%d_%H%M%S'))
    if os.path.exists(LIBRARY_PATH):
        shutil.copy2(LIBRARY_PATH, backup_path)
        print(f"  已备份原库到: {backup_path}")

    # 写入新库
    with open(LIBRARY_PATH, 'w', encoding='utf-8') as f:
        json.dump(new_lib, f, ensure_ascii=False, indent=2)

    stats = new_lib['optimization_stats']
    print(f"  新库已写入: {LIBRARY_PATH}")
    print(f"  三阶编码: {stats['third_level_count']}")
    print(f"  二阶编码: {stats['second_level_count']}")

    # Step 6: 清理RAG索引
    print("\n[6/6] 清理RAG索引...")
    rag_dir = "cache/rag_index"
    if os.path.exists(rag_dir):
        shutil.rmtree(rag_dir)
        print(f"  已清理RAG索引缓存: {rag_dir} (下次运行自动重建)")

    print("\n[OK] 编码库重建完成!")
    print("请重新启动应用以加载新的编码库和RAG索引。")


if __name__ == '__main__':
    main()
