import gzip
import json
from pathlib import Path

from enhanced_coding_generator import EnhancedCodingGenerator
from data_processor import DataProcessor
from first_level_eval import evaluate_first_level_candidates, write_compact_eval_jsonl


class _StubModelManager:
    scored_candidate_counts = []

    def is_trained_model_available(self):
        return True

    def ensure_abstract_reranker_loaded(self):
        return True

    def is_abstract_reranker_available(self):
        return True

    def score_abstract_candidates(self, original, candidates):
        self.scored_candidate_counts.append(len(candidates))
        scores = []
        for candidate in candidates:
            if "审批卡顿" in candidate or "推进受影响" in candidate:
                scores.append(0.95)
            else:
                scores.append(0.10)
        return scores

    def predict_categories(self, texts):
        return [(None, 0.9) for _ in texts], ["fallback_second" for _ in texts]


class _LongBiasedRerankModelManager(_StubModelManager):
    def score_abstract_candidate_pairs(self, pairs, batch_size=None):
        self.scored_candidate_counts.append(len(pairs))
        scores = []
        for _, candidate in pairs:
            if (
                "\u8ffd\u6c42\u521b\u65b0\u60f3\u6cd5\u7684\u624b\u6bb5\u4e0d\u7b26\u5408\u7ec4\u7ec7\u7a0b\u5e8f" in candidate
                and "\u4ea7\u751f\u7684\u521b\u65b0\u6210\u679c" in candidate
            ):
                scores.append(0.99)
            elif "\u8ffd\u6c42\u521b\u65b0\u60f3\u6cd5\u7684\u624b\u6bb5\u4e0d\u7b26\u5408\u7ec4\u7ec7\u7a0b\u5e8f" in candidate:
                scores.append(0.93)
            else:
                scores.append(0.10)
        return scores


class _FakeRuntimeStrategy:
    token_top_k = 10


class _FakeCluster:
    representative = "workflow delay"
    source_keys = ["FL_0001", "FL_0002"]
    support = 2


class _FakeClusterer:
    def cluster(self, first_level_codes):
        return [_FakeCluster()]


class _ThresholdRagMatcher:
    def second_code_name_map(self):
        return {"S1": "Process Risk"}

    def third_level_name_map(self):
        return {"T1": "Organization"}

    def match_first_level_to_second_level(self, text, top_k=5, token_top_k=80):
        return [
            {
                "name": "Process Risk",
                "score": 0.55,
                "token_score": 0.55,
                "vector_score": 0.55,
                "code": {
                    "level": "second",
                    "code_id": "S1",
                    "name": "Process Risk",
                    "third_level": "Organization",
                    "third_level_id": "T1",
                },
            }
        ]


def _make_generator():
    generator = EnhancedCodingGenerator.__new__(EnhancedCodingGenerator)
    generator.max_first_level_length = 30
    generator.abstract_cache = {}
    generator.similarity_cache = {}
    generator.coding_library = None
    generator.semantic_matcher = None
    generator.rag_enabled = False
    generator.runtime_strategy = None
    generator.rag_matcher = None
    generator.decision_policy = None
    generator.first_level_clusterer = None
    generator.rag_index_manager = None
    generator._first_level_trace_meta = {}
    generator._second_level_decision_meta = {}
    generator.first_level_prototypes = []
    generator.bad_phrase_patterns = [
        r"^其实",
        r"^我觉得",
        r"^如果说",
    ]
    return generator


def test_build_first_level_candidate_trace_returns_candidates_and_reserved_prototype_hook():
    generator = _make_generator()
    trace = generator.build_first_level_candidate_trace(
        "我觉得审批流程太慢了，项目推进就很受影响。",
        model_manager=None,
    )

    assert trace["selected_candidate"]
    assert trace["prototype_enabled"] is False
    assert trace["prototype_hits"] == []
    assert trace["candidates"]
    assert any("影响" in item["text"] for item in trace["candidates"])
    assert all("rule_score" in item for item in trace["candidates"])


def test_build_first_level_candidate_trace_records_rerank_scores():
    generator = _make_generator()
    model_manager = _StubModelManager()
    model_manager.scored_candidate_counts = []
    trace = generator.build_first_level_candidate_trace(
        "审批流程太慢了，项目推进受影响。",
        model_manager=model_manager,
    )

    assert trace["used_rerank"] is True
    assert any(item["rerank_score"] is not None for item in trace["candidates"])
    assert model_manager.scored_candidate_counts
    assert max(model_manager.scored_candidate_counts) <= 6
    selected = [item for item in trace["candidates"] if item["selected"]]
    assert len(selected) == 1


def test_evaluate_first_level_candidates_produces_compact_rows_and_summary(tmp_path: Path):
    generator = _make_generator()
    samples = [
        {
            "input_sentences": {"original_content": "审批流程太慢了，项目推进受影响。"},
            "target_abstract": "项目推进受影响",
        },
        {
            "input_sentences": {"original_content": "跨部门协同的时候经常对不上。"},
            "target_abstract": "跨部门协同对不上",
        },
    ]

    result = evaluate_first_level_candidates(samples, generator, model_manager=_StubModelManager(), top_n=3)

    assert result["summary"]["sample_count"] == 2
    assert "hit_at_3" in result["summary"]
    assert len(result["rows"]) == 2
    assert set(result["rows"][0].keys()) == {"o", "g", "p", "m", "u", "c"}
    assert len(result["rows"][0]["c"]) <= 3

    output_path = tmp_path / "first_level_eval.jsonl.gz"
    write_compact_eval_jsonl(output_path, result["rows"])

    with gzip.open(output_path, "rt", encoding="utf-8") as fh:
        decoded = [json.loads(line) for line in fh if line.strip()]

    assert len(decoded) == 2
    assert decoded[0]["o"]


def test_abstract_sentence_reuses_trace_selection():
    generator = _make_generator()
    sentence = "\u6211\u89c9\u5f97\u5ba1\u6279\u6d41\u7a0b\u592a\u6162\u4e86\uff0c\u9879\u76ee\u63a8\u8fdb\u53d7\u5f71\u54cd\u3002"
    trace = generator.build_first_level_candidate_trace(sentence, model_manager=_StubModelManager())
    abstracted = generator.abstract_sentence(sentence, model_manager=_StubModelManager())

    assert abstracted == trace["selected_candidate"]


def test_first_level_candidate_joining_does_not_insert_question_marks():
    generator = _make_generator()
    sentence = "\u738b\u5c0f\u5ddd\u5e76\u672a\u653e\u5f03\uff0c\u800c\u662f\u5c06\u5f00\u53d1\u8ba1\u5212\u8f6c\u5230\u5730\u4e0b\uff0c\u6700\u7ec8\u53d6\u5f97\u6210\u529f"

    trace = generator.build_first_level_candidate_trace(sentence, model_manager=None)
    abstracted = generator.abstract_sentence(sentence, model_manager=None)

    assert "?" not in abstracted
    assert all("?" not in item["text"] for item in trace["candidates"])


def test_first_level_defaults_use_clean_patterns():
    generator = EnhancedCodingGenerator.__new__(EnhancedCodingGenerator)
    generator._ensure_first_level_defaults()

    assert generator.bad_phrase_patterns
    assert all("?" not in pattern for pattern in generator.bad_phrase_patterns)


def test_generate_first_level_codes_stores_trace_sidecar():
    generator = _make_generator()
    sentences = [
        {
            "content": "\u6211\u89c9\u5f97\u5ba1\u6279\u6d41\u7a0b\u592a\u6162\u4e86\uff0c\u9879\u76ee\u63a8\u8fdb\u53d7\u5f71\u54cd\u3002",
            "speaker": "respondent",
            "sentence_id": "1",
        }
    ]

    first_level_codes = generator.generate_first_level_codes(
        sentences,
        model_manager=_StubModelManager(),
    )
    trace_meta = generator.get_first_level_trace_meta()

    assert "FL_0001" in first_level_codes
    assert "FL_0001" in trace_meta
    assert trace_meta["FL_0001"]["selected_candidate"] == first_level_codes["FL_0001"][0]
    assert trace_meta["FL_0001"]["candidates"]


def test_generate_first_level_codes_can_use_global_batch_rerank():
    generator = _make_generator()
    model_manager = _StubModelManager()
    model_manager.scored_candidate_counts = []
    sentences = [
        {
            "content": "\u6211\u89c9\u5f97\u5ba1\u6279\u6d41\u7a0b\u592a\u6162\u4e86\uff0c\u9879\u76ee\u63a8\u8fdb\u53d7\u5f71\u54cd\u3002",
            "speaker": "respondent",
            "sentence_id": "1",
        },
        {
            "content": "\u738b\u5c0f\u5ddd\u5e76\u672a\u653e\u5f03\uff0c\u800c\u662f\u5c06\u5f00\u53d1\u8ba1\u5212\u8f6c\u5230\u5730\u4e0b\uff0c\u6700\u7ec8\u53d6\u5f97\u6210\u529f",
            "speaker": "respondent",
            "sentence_id": "2",
        },
    ]

    first_level_codes = generator.generate_first_level_codes(
        sentences,
        model_manager=model_manager,
        coding_options={"use_global_batch_rerank": True},
    )

    assert len(first_level_codes) == 2
    assert len(model_manager.scored_candidate_counts) == 1
    assert model_manager.scored_candidate_counts[0] > 1


def test_global_batch_rerank_prefers_short_focused_phrase_over_long_sentence():
    generator = _make_generator()
    model_manager = _LongBiasedRerankModelManager()
    model_manager.scored_candidate_counts = []
    sentences = [
        {
            "content": "\u2462\u8ffd\u6c42\u521b\u65b0\u60f3\u6cd5\u7684\u624b\u6bb5\u4e0d\u7b26\u5408\u7ec4\u7ec7\u7a0b\u5e8f\uff0c\u4f46\u4ea7\u751f\u7684\u521b\u65b0\u6210\u679c\u5bf9\u7ec4\u7ec7\u662f\u6709\u5229\u7684",
            "speaker": "respondent",
            "sentence_id": "21",
        }
    ]

    first_level_codes = generator.generate_first_level_codes(
        sentences,
        model_manager=model_manager,
        coding_options={"use_global_batch_rerank": True},
    )

    selected = first_level_codes["FL_0001"][0]
    assert selected == "\u8ffd\u6c42\u521b\u65b0\u60f3\u6cd5\u7684\u624b\u6bb5\u4e0d\u7b26\u5408\u7ec4\u7ec7\u7a0b\u5e8f"
    assert not selected.startswith("\u2462")
    assert len(selected) <= 24


def test_rewrite_first_level_code_removes_leading_list_numbers():
    generator = _make_generator()

    rewritten = generator.rewrite_first_level_code(
        "\u2463\u8d8a\u8f68\u521b\u65b0\u7684\u7ed3\u679c\u53ef\u80fd\u6210\u529f\u4e5f\u53ef\u80fd\u5931\u8d25"
    )

    assert rewritten == "\u8d8a\u8f68\u521b\u65b0\u7684\u7ed3\u679c\u53ef\u80fd\u6210\u529f\u4e5f\u53ef\u80fd\u5931\u8d25"


def test_generate_first_level_codes_repairs_missing_sentence_id_from_marker():
    generator = _make_generator()
    sentences = [
        {
            "content": "\u5ba2\u6237\u8bf4\u4e70\u5565\u6211\u4eec\u5c31\u5356\u5565\u3002 [30]",
            "speaker": "respondent",
        }
    ]

    first_level_codes = generator.generate_first_level_codes(sentences)

    assert first_level_codes["FL_0001"][4][0]["sentence_id"] == "30"


def test_generate_first_level_codes_drops_code_when_sentence_id_cannot_be_traced():
    generator = _make_generator()
    sentences = [
        {
            "content": "\u5ba2\u6237\u8bf4\u4e70\u5565\u6211\u4eec\u5c31\u5356\u5565\u3002",
            "speaker": "respondent",
        }
    ]

    first_level_codes = generator.generate_first_level_codes(sentences)

    assert first_level_codes == {}


def test_generate_first_level_codes_filters_low_quality_first_level_code():
    generator = _make_generator()
    sentences = [
        {
            "content": "\u6211\u4e5f\u6ca1\u6709\u529e\u6cd5\u76f4\u63a5\u53bb\u501f\u9274\u540c\u884c\u4e1a\u7684\u8fd9\u4e2a\u516c\u53f8\uff0c\u56e0\u4e3a\u90a3\u4e2a\u65f6\u5019\u662f13\u3002",
            "speaker": "respondent",
            "sentence_id": "30",
        },
        {
            "content": "\u5ba2\u6237\u8bf4\u4e70\u5565\u6211\u4eec\u5c31\u5356\u5565\u3002",
            "speaker": "respondent",
            "sentence_id": "31",
        },
    ]

    first_level_codes = generator.generate_first_level_codes(sentences)

    assert len(first_level_codes) == 1
    only_code = next(iter(first_level_codes.values()))
    assert "\u6ca1\u6709\u529e\u6cd5" not in only_code[0]
    assert only_code[4][0]["sentence_id"] == "31"


def test_generate_first_level_codes_drops_colloquial_fragment_after_resplit():
    generator = _make_generator()
    sentences = [
        {
            "content": "\u8d8a\u8f68\u521b\u65b0\u8fd9\u4e2a\u4e1c\u897f\u5427\uff0c\u8981\u770b\uff0c\u6211\u89c9\u5f97\u8981\u5206\u573a\u5408\uff0c\u5c31\u662f\u8bf4\uff0c\u600e\u4e48\u8bf4\u5462\u3002",
            "speaker": "respondent",
            "sentence_id": "26",
        }
    ]

    first_level_codes = generator.generate_first_level_codes(sentences)

    assert first_level_codes == {}


def test_data_processor_attaches_sentence_id_from_original_numbering_lookup():
    processor = DataProcessor()
    processor._processing_sentence_counter = 0
    lookup = processor._build_sentence_number_lookup(
        "\u91c7\u8bbf\u5f00\u573a\u8bf4\u660e\u3002\u5ba2\u6237\u8bf4\u4e70\u5565\u6211\u4eec\u5c31\u5356\u5565\uff0c\u540e\u7eed\u518d\u4e00\u8d77\u8c03\u6574\u65b9\u6848\u3002"
    )
    paragraphs = [
        {
            "speaker": "respondent",
            "content": "\u5ba2\u6237\u8bf4\u4e70\u5565\u6211\u4eec\u5c31\u5356\u5565\uff0c\u540e\u7eed\u518d\u4e00\u8d77\u8c03\u6574\u65b9\u6848",
        }
    ]

    sentences = processor.extract_respondent_sentences(
        paragraphs,
        "demo.txt",
        sentence_number_lookup=lookup,
        file_path="demo.txt",
    )

    assert sentences[0]["sentence_id"] == "2"
    assert sentences[0]["file_path"] == "demo.txt"


def test_rewrite_first_level_code_removes_colloquial_fillers():
    generator = _make_generator()

    rewritten = generator.rewrite_first_level_code(
        "\u6211\u89c9\u5f97\u8d8a\u8f68\u521b\u65b0\u8fd9\u4e2a\u4e1c\u897f\u53ef\u80fd\u80fd\u591f\u5f71\u54cd\u7684\u8303\u56f4\u5176\u5b9e\u8fd8\u662f\u6709\u9650\u7684"
    )

    assert rewritten == "\u8d8a\u8f68\u521b\u65b0\u5f71\u54cd\u8303\u56f4\u6709\u9650"


def test_rewrite_first_level_code_removes_timestamp_marker():
    generator = _make_generator()

    rewritten = generator.rewrite_first_level_code(
        "\u627e\u4ed6\u4eec\uff0c\u4f46\u662f\u540e\u6765\u53d1\u73b0\u56e0\u4e3a\u4ed6\u4eec\u90a3\u4e2a\u65f6\u5019\u4e3b\u8981\u5728\u670d\u52a1\uff0815:05\uff09"
    )

    assert "\u0031\u0035\u003a\u0030\u0035" not in rewritten
    assert "\uff08" not in rewritten and "\uff09" not in rewritten


def test_build_first_level_candidate_trace_prefers_short_focused_phrase_without_rerank():
    generator = _make_generator()

    trace = generator.build_first_level_candidate_trace(
        "\u6211\u89c9\u5f97\u5ba1\u6279\u6d41\u7a0b\u592a\u6162\u4e86\uff0c\u9879\u76ee\u63a8\u8fdb\u53d7\u5f71\u54cd\u3002",
        model_manager=None,
    )

    assert trace["selected_candidate"] == "\u9879\u76ee\u63a8\u8fdb\u53d7\u5f71\u54cd"
    assert all("\u6211\u89c9\u5f97" not in row["text"] for row in trace["candidates"])
    assert all("\u0031\u0035\u003a\u0030\u0035" not in row["text"] for row in trace["candidates"])


def test_generate_first_level_codes_drops_timestamp_discourse_residue():
    generator = _make_generator()
    sentences = [
        {
            "content": "\u627e\u4ed6\u4eec\uff0c\u4f46\u662f\u540e\u6765\u53d1\u73b0\u56e0\u4e3a\u4ed6\u4eec\u90a3\u4e2a\u65f6\u5019\u4e3b\u8981\u5728\u670d\u52a1\uff0815:05\uff09",
            "speaker": "respondent",
            "sentence_id": "33",
        }
    ]

    first_level_codes = generator.generate_first_level_codes(sentences)

    assert first_level_codes == {}


def test_generate_first_level_codes_drops_definition_intro_sentence():
    generator = _make_generator()
    sentences = [
        {
            "content": "\u5148\u7ed9\u60a8\u4ecb\u7ecd\u4ee5\u4e0b\u8d8a\u8f68\u521b\u65b0\u7684\u5b9a\u4e49\u4e0e\u7279\u5f81\u3002",
            "speaker": "respondent",
            "sentence_id": "13",
        }
    ]

    first_level_codes = generator.generate_first_level_codes(sentences)

    assert first_level_codes == {}


def test_generate_first_level_codes_drops_month_discourse_sentence():
    generator = _make_generator()
    sentences = [
        {
            "content": "\u5f53\u65f6\u662f3\u6708\u4efd\u5c31\u5df2\u7ecf\u6709\u5355\u4f4d\u627e\u5230\u6211\u4eec\u3002",
            "speaker": "respondent",
            "sentence_id": "51",
        }
    ]

    first_level_codes = generator.generate_first_level_codes(sentences)

    assert first_level_codes == {}


def test_generate_first_level_codes_drops_first_person_discourse_sentence():
    generator = _make_generator()
    sentences = [
        {
            "content": "\u516c\u53f8\u539f\u6765\u6211\u5728\u63a5\u624b\u3002",
            "speaker": "respondent",
            "sentence_id": "24",
        }
    ]

    first_level_codes = generator.generate_first_level_codes(sentences)

    assert first_level_codes == {}


def test_build_first_level_candidate_trace_prefers_feedback_analysis_phrase():
    generator = _make_generator()

    trace = generator.build_first_level_candidate_trace(
        "\u5ba2\u6237\u4e3b\u8981\u8d1f\u8d23\u6307\u5f15\u65b9\u5411\u3001\u76d1\u7763\u7ed3\u679c\uff0c\u6211\u4eec\u901a\u8fc7\u5206\u6790\u5ba2\u6237\u7684\u53cd\u9988\uff0c\u80fd\u66f4\u52a0\u660e\u786e\u5ba2\u6237\u7684\u5b9e\u9645\u8bc9\u6c42\u3002",
        model_manager=None,
    )

    assert trace["selected_candidate"] == "\u5206\u6790\u5ba2\u6237\u53cd\u9988"


def test_conservative_prototype_hint_guides_extraction_without_outputting_manual_code():
    generator = _make_generator()
    generator.set_first_level_prototypes(
        [
            {
                "source": "\u6700\u65e9\u7684\u65f6\u5019\uff0c\u5ba2\u6237\u8bf4\u4e70\u5565\u6211\u4eec\u5c31\u5356\u5565\uff0c\u5ba2\u6237\u8981\u505a\u6574\u673a\u67dc\uff0c\u6211\u4eec\u5c31\u4e00\u8d77\u6765\u505a\u6574\u673a\u67dc\u3002",
                "manual_first_code": "\u5ba2\u6237\u9700\u6c42\u5bfc\u5411",
            }
        ]
    )

    trace = generator.build_first_level_candidate_trace(
        "\u6700\u65e9\u7684\u65f6\u5019\uff0c\u5ba2\u6237\u8bf4\u4e70\u5565\u6211\u4eec\u5c31\u5356\u5565\uff0c\u5ba2\u6237\u8981\u505a\u6574\u673a\u67dc\uff0c\u6211\u4eec\u5c31\u4e00\u8d77\u6765\u505a\u6574\u673a\u67dc\u3002",
        model_manager=None,
    )

    assert trace["prototype_enabled"] is True
    assert trace["prototype_hits"][0]["manual_first_code"] == "\u5ba2\u6237\u9700\u6c42\u5bfc\u5411"
    assert trace["selected_candidate"] == "\u5ba2\u6237\u8bf4\u4e70\u5565\u6211\u4eec\u5c31\u5356\u5565"
    assert trace["selected_candidate"] != "\u5ba2\u6237\u9700\u6c42\u5bfc\u5411"


def test_generate_codes_with_trained_model_stores_same_trace_sidecar_shape():
    generator = _make_generator()
    processed_data = {
        "file_sentence_mapping": {
            "demo.txt": {
                "sentences": [
                        {
                            "content": "\u6211\u89c9\u5f97\u5ba1\u6279\u6d41\u7a0b\u592a\u6162\u4e86\uff0c\u9879\u76ee\u63a8\u8fdb\u53d7\u5f71\u54cd\u3002",
                            "speaker": "respondent",
                            "sentence_id": "1",
                        }
                ]
            }
        }
    }

    raw_codes = generator.generate_codes_with_trained_model(
        processed_data,
        _StubModelManager(),
    )
    first_level_codes = next(
        value
        for value in raw_codes.values()
        if isinstance(value, dict) and "FL_0001" in value
    )
    trace_meta = generator.get_first_level_trace_meta()

    assert trace_meta["FL_0001"]["selected_candidate"] == first_level_codes["FL_0001"][0]
    assert trace_meta["FL_0001"]["candidates"]


def test_manual_second_threshold_sends_low_similarity_cluster_to_other_topic():
    generator = _make_generator()
    generator.rag_enabled = True
    generator.rag_matcher = _ThresholdRagMatcher()
    generator.runtime_strategy = _FakeRuntimeStrategy()
    generator.first_level_clusterer = _FakeClusterer()
    generator.configure_similarity_thresholds(second_threshold=0.8)

    result = generator.generate_second_level_codes_improved(
        {
            "FL_0001": ["workflow delay"],
            "FL_0002": ["workflow delay"],
        }
    )

    assert result == {generator.decision_policy.other_second_name: ["FL_0001", "FL_0002"]}


def test_manual_second_threshold_can_accept_same_candidate_when_lowered():
    generator = _make_generator()
    generator.rag_enabled = True
    generator.rag_matcher = _ThresholdRagMatcher()
    generator.runtime_strategy = _FakeRuntimeStrategy()
    generator.first_level_clusterer = _FakeClusterer()
    generator.configure_similarity_thresholds(second_threshold=0.5)

    result = generator.generate_second_level_codes_improved(
        {
            "FL_0001": ["workflow delay"],
            "FL_0002": ["workflow delay"],
        }
    )

    assert result == {"Process Risk": ["FL_0001", "FL_0002"]}


def test_grounded_generation_entry_applies_manual_second_and_fallback_third_thresholds():
    generator = _make_generator()
    processed_data = {
        "file_sentence_mapping": {
            "demo.txt": {
                "sentences": [
                    {
                        "content": "\u6211\u89c9\u5f97\u5ba1\u6279\u6d41\u7a0b\u592a\u6162\u4e86\uff0c\u9879\u76ee\u63a8\u8fdb\u53d7\u5f71\u54cd\u3002",
                        "speaker": "respondent",
                    }
                ]
            }
        }
    }

    generator.generate_grounded_theory_codes_multi_files(
        processed_data,
        _StubModelManager(),
        use_trained_model=True,
        coding_thresholds={"second_threshold": 0.77, "third_threshold": 0.66},
    )

    assert generator.rag_second_level_threshold == 0.77
    assert generator.rag_third_level_threshold == 0.66


def test_generate_codes_with_rules_ignores_non_threshold_runtime_options():
    generator = _make_generator()
    processed_data = {
        "combined_text": "",
        "file_sentence_mapping": {
            "demo.txt": {
                "sentences": [
                    {
                        "content": "\u5ba2\u6237\u8bf4\u4e70\u5565\u6211\u4eec\u5c31\u5356\u5565\u3002",
                        "speaker": "respondent",
                    }
                ]
            }
        },
    }
    captured_options = {}

    def fake_generate_first_level_codes(sentences, model_manager=None, coding_options=None):
        captured_options.update(coding_options or {})
        return {"A01": {"text": "\u5ba2\u6237\u8bf4\u4e70\u5565\u6211\u4eec\u5c31\u5356\u5565"}}

    generator.generate_first_level_codes = fake_generate_first_level_codes
    generator.generate_second_level_codes_improved = lambda first, model_manager=None: {}
    generator.generate_third_level_codes_improved = lambda second: {}

    generator.generate_codes_with_rules(
        processed_data,
        model_manager=_StubModelManager(),
        coding_thresholds={
            "second_threshold": 0.77,
            "third_threshold": 0.66,
            "use_global_batch_rerank": True,
        },
    )

    assert generator.rag_second_level_threshold == 0.77
    assert generator.rag_third_level_threshold == 0.66
    assert captured_options["use_global_batch_rerank"] is True
