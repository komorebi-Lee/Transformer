"""
auto_code_merger 单元测试。

测试场景覆盖设计文档中的所有边界情况。
"""

import sys
import os
import unittest
import numpy as np


class TestKeywordFunctions(unittest.TestCase):
    """关键词提取和重叠计算测试（不需要模型）。"""

    def test_extract_keywords_basic(self):
        from auto_code_merger import _extract_keywords
        kw = _extract_keywords("产品质量问题需要改进和提升")
        self.assertIsInstance(kw, set)
        self.assertGreater(len(kw), 0)

    def test_extract_keywords_empty(self):
        from auto_code_merger import _extract_keywords
        kw = _extract_keywords("")
        self.assertEqual(kw, set())

    def test_extract_keywords_short(self):
        from auto_code_merger import _extract_keywords
        kw = _extract_keywords("好")
        self.assertIsInstance(kw, set)

    def test_keyword_overlap_identical(self):
        from auto_code_merger import _keyword_overlap
        kw1 = {"产品", "质量", "问题"}
        kw2 = {"产品", "质量", "问题"}
        self.assertAlmostEqual(_keyword_overlap(kw1, kw2), 1.0)

    def test_keyword_overlap_none(self):
        from auto_code_merger import _keyword_overlap
        kw1 = {"产品", "质量"}
        kw2 = {"服务", "态度"}
        self.assertAlmostEqual(_keyword_overlap(kw1, kw2), 0.0)

    def test_keyword_overlap_partial(self):
        from auto_code_merger import _keyword_overlap
        kw1 = {"产品", "质量", "问题"}
        kw2 = {"产品", "质量", "投诉"}
        self.assertAlmostEqual(_keyword_overlap(kw1, kw2), 2.0 / 4.0)

    def test_keyword_overlap_empty(self):
        from auto_code_merger import _keyword_overlap
        self.assertEqual(_keyword_overlap(set(), {"产品"}), 0.0)
        self.assertEqual(_keyword_overlap({"产品"}, set()), 0.0)


class TestMergeLogic(unittest.TestCase):
    """合并逻辑测试（不需要模型，mock 模型输出）。"""

    def setUp(self):
        from auto_code_merger import AutoCodeMerger
        self.merger = AutoCodeMerger(
            bge_model=_MockBGE(),
            concept_model=_MockConcept(),
            config={
                'AUTO_MERGE_BGE_CONCEPT_MIN': 0.75,
                'AUTO_MERGE_BGE_SENT_MIN': 0.85,
                'AUTO_MERGE_CONCEPT_SIM_MIN': 0.60,
                'AUTO_MERGE_KEYWORD_OVERLAP_MIN': 0.05,
            }
        )

    def _make_code(self, key, content, sent_texts):
        """构造一个 first_level_codes 条目。"""
        details = [{'content': t, 'text_number': str(i + 1),
                     'sentence_id': str(i + 1), 'code_id': str(i + 1)}
                   for i, t in enumerate(sent_texts)]
        return {
            'key': key,
            'contents': [content, [{'content': t} for t in sent_texts],
                         1, len(sent_texts), details],
        }

    def test_single_code_no_merge(self):
        """单编码：直接返回原数据。"""
        codes = {'FL_0001': ['产品质量问题', [{'content': '产品质量问题'}], 1, 1,
                             [{'content': '产品质量问题', 'sentence_id': '1'}]]}
        result = self.merger.merge(codes)
        self.assertEqual(len(result), 1)
        self.assertIn('FL_0001', result)

    def test_empty_input(self):
        """空输入：返回空 dict。"""
        result = self.merger.merge({})
        self.assertEqual(len(result), 0)

    def test_two_similar_codes_merge(self):
        """两个语义相近的编码应合并为一个。"""
        entry1 = self._make_code('FL_0001', '产品质量投诉',
                                 ['产品质量太差了，经常出问题'])
        entry2 = self._make_code('FL_0002', '产品质量问题',
                                 ['这个东西质量不行'])
        codes = {
            entry1['key']: entry1['contents'],
            entry2['key']: entry2['contents'],
        }
        result = self.merger.merge(codes)
        self.assertEqual(len(result), 1, "两个语义相近的编码应合并为 1 个")

    def test_merged_code_has_combined_sentence_details(self):
        """合并后主编码应包含从编码的所有 sentence_details。"""
        entry1 = self._make_code('FL_0001', '产品质量投诉',
                                 ['产品质量太差了', '经常出问题'])
        entry2 = self._make_code('FL_0002', '产品质量问题',
                                 ['这个东西质量不行'])
        codes = {
            entry1['key']: entry1['contents'],
            entry2['key']: entry2['contents'],
        }
        result = self.merger.merge(codes)
        self.assertEqual(len(result), 1)
        primary_key = list(result.keys())[0]
        details = result[primary_key][4]
        self.assertEqual(len(details), 3,
                         f"合并后应有 3 条 sentence_details，实际 {len(details)} 条")

    def test_dissimilar_codes_stay_separate(self):
        """两个语义不同的编码不应合并。"""
        from auto_code_merger import AutoCodeMerger

        strict_merger = AutoCodeMerger(
            bge_model=_MockBGE(),
            concept_model=_MockConcept(),
            config={
                'AUTO_MERGE_BGE_CONCEPT_MIN': 0.75,
                'AUTO_MERGE_BGE_SENT_MIN': 0.85,
                'AUTO_MERGE_CONCEPT_SIM_MIN': 0.60,
                'AUTO_MERGE_KEYWORD_OVERLAP_MIN': 0.30,
            }
        )
        entry1 = self._make_code('FL_0001', '产品质量投诉',
                                 ['产品质量太差了，经常出问题'])
        entry2 = self._make_code('FL_0002', '员工福利待遇',
                                 ['我们的福利待遇还不错'])
        codes = {
            entry1['key']: entry1['contents'],
            entry2['key']: entry2['contents'],
        }
        result = strict_merger.merge(codes)
        self.assertEqual(len(result), 2, "语义不同的编码不应合并")

    def test_primary_selection_by_sentence_count(self):
        """句子来源数多的应保留为主编码。"""
        entry1 = self._make_code('FL_0001', '产品质量投诉',
                                 ['产品质量差', '经常出问题', '投诉很多'])
        entry2 = self._make_code('FL_0002', '产品质量问题',
                                 ['这个东西质量不行'])
        codes = {
            entry1['key']: entry1['contents'],
            entry2['key']: entry2['contents'],
        }
        result = self.merger.merge(codes)
        self.assertEqual(len(result), 1)
        primary_key = list(result.keys())[0]
        self.assertEqual(primary_key, 'FL_0001',
                         "句子来源数多的 FL_0001 应保留为主编码")


class _MockBGE:
    """Mock bge 模型：所有文本返回相同 embedding（模拟高度相似场景）。"""
    def encode(self, texts, normalize_embeddings=True, show_progress_bar=False,
               batch_size=32):
        if isinstance(texts, str):
            texts = [texts]
        emb = np.zeros((len(texts), 512), dtype=np.float32)
        emb[:, 0] = 1.0
        if normalize_embeddings:
            norms = np.linalg.norm(emb, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            emb = emb / norms
        if len(texts) == 1:
            return emb[0]
        return emb


class _MockConcept:
    """Mock concept_anchor_v6 模型：行为同 MockBGE。"""
    def encode(self, texts, normalize_embeddings=True, show_progress_bar=False,
               batch_size=32):
        if isinstance(texts, str):
            texts = [texts]
        emb = np.zeros((len(texts), 512), dtype=np.float32)
        emb[:, 0] = 1.0
        if normalize_embeddings:
            norms = np.linalg.norm(emb, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            emb = emb / norms
        if len(texts) == 1:
            return emb[0]
        return emb


if __name__ == '__main__':
    unittest.main()
