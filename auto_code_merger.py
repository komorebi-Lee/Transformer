"""
一阶编码自动归类合并模块。

在自动编码后处理阶段，基于语义相似度和关键词匹配，自动将
表达同一概念的多个一阶编码合并为一个编码，减少重复编码。
"""

import logging
import numpy as np
from collections import defaultdict
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class AutoCodeMerger:
    """一阶编码自动合并器。

    四层门控判定两段文本是否表达同一概念：
    1. 编码 content ↔ content bge 相似度（防大类误合并）
    2. 句子 ↔ 句子 bge 相似度
    3. 句子 ↔ 编码 content concept_anchor_v6 概念相似度
    4. 句子间关键词重叠比例
    """

    def __init__(self, bge_model, concept_model, config: Dict = None):
        """
        Args:
            bge_model: SentenceTransformer (bge-small-zh-v1.5)，用于句子间语义相似度
            concept_model: SentenceTransformer (concept_anchor_v6)，用于句子→概念确认
            config: 可选阈值覆盖 dict，键名对应 config.py 中的 AUTO_MERGE_* 变量。
                    不传则直接从 config 模块读取。
        """
        self.bge = bge_model
        self.concept = concept_model
        self._cfg = config or {}
        self._all_sent_texts = []
        self._sent_to_entry = []

    def _get_threshold(self, name: str, default: float) -> float:
        if name in self._cfg:
            return self._cfg[name]
        try:
            from config import Config
            return getattr(Config, name, default)
        except Exception:
            return default

    @property
    def threshold_bge_concept(self) -> float:
        return self._get_threshold('AUTO_MERGE_BGE_CONCEPT_MIN', 0.75)

    @property
    def threshold_bge_sent(self) -> float:
        return self._get_threshold('AUTO_MERGE_BGE_SENT_MIN', 0.85)

    @property
    def threshold_concept_sim(self) -> float:
        return self._get_threshold('AUTO_MERGE_CONCEPT_SIM_MIN', 0.60)

    @property
    def threshold_keyword_overlap(self) -> float:
        return self._get_threshold('AUTO_MERGE_KEYWORD_OVERLAP_MIN', 0.30)

    # ── 公开入口 ──

    def merge(self, first_level_codes: Dict) -> Dict:
        """对一阶编码执行自动归类合并。

        Args:
            first_level_codes: {code_key: [content, [sentence_dict], file_count,
                                           sentence_count, [sentence_detail_dict]]}

        Returns:
            合并后的同结构 dict。若无合并，返回原 dict。
        """
        if len(first_level_codes) <= 1:
            return first_level_codes

        entries = self._collect_entries(first_level_codes)
        n = len(entries)

        # 1. 批量编码
        code_embs, sent_embs, sent_v6_embs, code_v6_embs = self._batch_encode(entries)

        # 2. 提取所有句子的关键词
        keywords_list = [_extract_keywords(s) for s in self._all_sent_texts]

        # 3. 查找所有句子级匹配对
        sentence_matches = self._find_sentence_matches(
            entries, code_embs, sent_embs, sent_v6_embs, code_v6_embs, keywords_list)

        # 4. 从句子级匹配推导编码级合并候选（按得分排序）
        merge_pairs = self._build_merge_graph(sentence_matches)

        # 5. 贪心合并：逐对处理，每个编码最多参与一次合并
        merged = self._execute_merges(first_level_codes, entries, merge_pairs)

        return merged

    # ── 内部步骤 ──

    def _collect_entries(self, first_level_codes: Dict) -> List[dict]:
        """收集所有编码条目，提取 content 和句子文本列表。"""
        entries = []
        for key, contents in first_level_codes.items():
            code_text = contents[0] if contents[0] else ""
            details = contents[4] if len(contents) > 4 else []

            sent_texts = []
            for d in details:
                text = d.get('content') or d.get('text') or d.get('original_content', '')
                if text.strip():
                    sent_texts.append(text.strip())

            if not sent_texts:
                sent_texts = [code_text]

            entries.append({
                'key': key,
                'content': code_text.strip(),
                'sent_texts': sent_texts,
                'details': details,
                'file_count': contents[2] if len(contents) > 2 else 1,
                'sentence_count': contents[3] if len(contents) > 3 else len(details),
            })
        return entries

    def _batch_encode(self, entries: List[dict]):
        """批量编码所有 code content 和句子文本。"""
        code_texts = [e['content'] for e in entries]

        # bge 编码：code content
        code_embs = self.bge.encode(code_texts, normalize_embeddings=True,
                                     show_progress_bar=False).astype(np.float32)

        # 收集所有句子文本并记录归属
        self._all_sent_texts = []
        self._sent_to_entry = []
        for ei, e in enumerate(entries):
            for st in e['sent_texts']:
                self._all_sent_texts.append(st)
                self._sent_to_entry.append(ei)

        # bge 编码：所有句子
        sent_embs = self.bge.encode(self._all_sent_texts, normalize_embeddings=True,
                                     show_progress_bar=False).astype(np.float32)

        # concept_anchor_v6 编码：所有句子
        sent_v6_embs = self.concept.encode(self._all_sent_texts, normalize_embeddings=True,
                                            show_progress_bar=False).astype(np.float32)

        # concept_anchor_v6 编码：code content
        code_v6_embs = self.concept.encode(code_texts, normalize_embeddings=True,
                                            show_progress_bar=False).astype(np.float32)

        return code_embs, sent_embs, sent_v6_embs, code_v6_embs

    def _find_sentence_matches(self, entries, code_embs, sent_embs,
                                sent_v6_embs, code_v6_embs, keywords_list):
        """查找所有通过四层门控的句子级匹配对。

        Returns:
            List of (from_entry_idx, to_entry_idx, sent_idx, score)
        """
        n_entries = len(entries)
        n_sents = len(self._all_sent_texts)

        # 预计算 code-code bge 相似度矩阵
        code_sim = code_embs @ code_embs.T

        # 预计算 sent-sent bge 相似度（分批防 OOM）
        sent_sim = self._batched_cosine(sent_embs, sent_embs, 2000)

        # 预计算 sent→code concept_sim
        sent_code_v6_sim = sent_v6_embs @ code_v6_embs.T

        matches = []

        for si in range(n_sents):
            from_ei = self._sent_to_entry[si]
            for sj in range(n_sents):
                to_ej = self._sent_to_entry[sj]
                if from_ei == to_ej:
                    continue

                # Layer 1: code-concept gate
                if code_sim[from_ei, to_ej] < self.threshold_bge_concept:
                    continue

                # Layer 2: sent-sent bge gate
                sim_val = float(sent_sim[si, sj])
                if sim_val < self.threshold_bge_sent:
                    continue

                # Layer 3: sent→target code concept gate
                if float(sent_code_v6_sim[si, to_ej]) < self.threshold_concept_sim:
                    continue

                # Layer 4: keyword overlap
                kw_overlap = _keyword_overlap(keywords_list[si], keywords_list[sj])
                if kw_overlap < self.threshold_keyword_overlap:
                    continue

                matches.append((from_ei, to_ej, si, sim_val))

        return matches

    def _batched_cosine(self, a: np.ndarray, b: np.ndarray,
                         batch_size: int) -> np.ndarray:
        """分批计算余弦相似度矩阵，防止大矩阵 OOM。"""
        n_a = a.shape[0]
        result = np.zeros((n_a, b.shape[0]), dtype=np.float32)
        for i in range(0, n_a, batch_size):
            end = min(i + batch_size, n_a)
            result[i:end] = a[i:end] @ b.T
        return result

    def _build_merge_graph(self, sentence_matches):
        """从句子级匹配构建编码级合并图。

        使用直接边（非传递闭包）。每对编码之间只记录得分最高的句子对。
        返回 [(from_idx, to_idx, max_score, match_count)] 按分数降序排列。
        """
        # 聚合同一对编码间的所有句子匹配
        pair_scores = defaultdict(list)
        for from_ei, to_ej, si, score in sentence_matches:
            pair_scores[(from_ei, to_ej)].append(score)

        # 每对编码取最高分 + 匹配句对数
        pairs = []
        for (from_ei, to_ej), scores in pair_scores.items():
            pairs.append((from_ei, to_ej, max(scores), len(scores)))

        # 按匹配句对数降序，同数按最高分降序
        pairs.sort(key=lambda x: (x[3], x[2]), reverse=True)
        return pairs

    def _execute_merges(self, first_level_codes, entries, merge_pairs):
        """执行合并：贪心逐对合并，已合并的编码不再参与其他合并。"""
        result = dict(first_level_codes)
        merged_out = set()  # 已被合并到其他编码的 idx
        merged_in = defaultdict(set)  # primary_idx → set of secondary indices

        for from_ei, to_ej, max_score, match_count in merge_pairs:
            # 跳过已被合并的
            if from_ei in merged_out or to_ej in merged_out:
                continue
            # from 不能已经是 primary（吸收了其他编码）
            if from_ei in merged_in:
                continue

            # 确定主/从
            from_count = len(entries[from_ei]['details'])
            to_count = len(entries[to_ej]['details'])

            if from_count > to_count:
                primary_idx, sec_idx = from_ei, to_ej
            elif to_count > from_count:
                primary_idx, sec_idx = to_ej, from_ei
            else:
                # 平局：bge 平均语义相似度高的为主
                if self._avg_bge_sim(entries, from_ei) >= self._avg_bge_sim(entries, to_ej):
                    primary_idx, sec_idx = from_ei, to_ej
                else:
                    primary_idx, sec_idx = to_ej, from_ei

            merged_out.add(sec_idx)
            merged_in[primary_idx].add(sec_idx)

        # 执行合并
        for primary_idx, sec_indices in merged_in.items():
            primary_key = entries[primary_idx]['key']
            for sec_idx in sec_indices:
                sec_key = entries[sec_idx]['key']
                if sec_key in result and primary_key in result:
                    self._merge_into(result[primary_key], result[sec_key])
                    del result[sec_key]

        return result

    def _avg_bge_sim(self, entries, idx):
        """计算某编码 content 与其所有句子的平均 bge 相似度。"""
        e = entries[idx]
        if not e['sent_texts']:
            return 0.0
        content_emb = self.bge.encode([e['content']], normalize_embeddings=True,
                                       show_progress_bar=False).astype(np.float32)
        sent_embs = self.bge.encode(e['sent_texts'], normalize_embeddings=True,
                                     show_progress_bar=False).astype(np.float32)
        sims = content_emb @ sent_embs.T
        return float(sims.mean())

    def _merge_into(self, primary_contents: List, secondary_contents: List):
        """将 secondary 的 sentence_details 合并到 primary。

        去重依据：sentence_detail 中的 content/text/original_content 文本。
        更新 file_count 和 sentence_count。
        """
        primary_details = primary_contents[4] if len(primary_contents) > 4 else []
        secondary_details = secondary_contents[4] if len(secondary_contents) > 4 else []

        existing_texts = set()
        for d in primary_details:
            text = d.get('content') or d.get('text') or d.get('original_content', '')
            if text.strip():
                existing_texts.add(text.strip())

        for d in secondary_details:
            text = d.get('content') or d.get('text') or d.get('original_content', '')
            if text.strip() and text.strip() not in existing_texts:
                existing_texts.add(text.strip())
                primary_details.append(d)

        primary_contents[4] = primary_details
        primary_contents[3] = len(primary_details)

        file_paths = set()
        for d in primary_details:
            fp = d.get('file_path', '')
            if fp:
                file_paths.add(fp)
        p_fc = primary_contents[2] if len(primary_contents) > 2 else 1
        s_fc = secondary_contents[2] if len(secondary_contents) > 2 else 1
        primary_contents[2] = max(len(file_paths), p_fc, s_fc) if file_paths else max(p_fc, s_fc)


# ── 关键词工具函数 ──

def _extract_keywords(text: str, top_k: int = None) -> Set[str]:
    """提取字符级 bigram 作为关键词集合。

    中文文本中使用字符 bigram 比 jieba 分词更稳健——避免因分词粒度
    不一致（如"产品质量" vs "质量"）导致的关键词零重叠问题。
    """
    if not text or len(text.strip()) < 2:
        return set()
    chars = text.strip()
    bigrams = set()
    for i in range(len(chars) - 1):
        bigrams.add(chars[i:i + 2])
    return bigrams


def _keyword_overlap(kw1: Set[str], kw2: Set[str]) -> float:
    """计算两个关键词集合的 Jaccard 重叠比例。"""
    if not kw1 or not kw2:
        return 0.0
    intersection = kw1 & kw2
    union = kw1 | kw2
    return len(intersection) / len(union) if union else 0.0
