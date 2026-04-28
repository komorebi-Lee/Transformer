# RAG Auto Coding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local, hardware-adaptive RAG auto-coding pipeline that compresses first-level candidates before matching, keeps low-confidence results in fixed fallback categories, refreshes derived indexes after coding-library edits, and preserves the existing auto-coding to manual-coding workflow.

**Architecture:** Add focused modules for runtime strategy detection, derived RAG index management, hybrid semantic matching, first-level clustering, and coding decision policy. Integrate them behind config flags in `EnhancedCodingGenerator` while keeping the returned raw-code structure compatible with `GroundedTheoryCoder`, `MainWindow.start_manual_coding`, and `ManualCodingDialog`.

**Tech Stack:** Python, pytest, numpy, jieba, torch when available, existing local sentence-transformer model through `SemanticMatcher`.

---

## File Structure

- Create: `runtime_strategy.py` for hardware detection and batch-size/candidate-size policy.
- Create: `rag_index.py` for derived RAG document construction, token index, vector matrix persistence, and index invalidation.
- Create: `rag_semantic_matcher.py` for hybrid token/vector retrieval while reusing `SemanticMatcher` embeddings.
- Create: `first_level_clusterer.py` for duplicate removal and first-level semantic clustering.
- Create: `coding_decision_policy.py` for second-level and third-level confidence gates and fallback categories.
- Create: `tests/conftest.py` for small coding-library fixtures and fake embedding helpers.
- Create: `tests/test_runtime_strategy.py` for GPU/CPU/light/fallback strategy selection.
- Create: `tests/test_rag_index.py` for derived document construction, metadata, invalidation, and lazy rebuild checks.
- Create: `tests/test_rag_semantic_matcher.py` for token recall, vector ranking, conflict reporting, and fallback behavior.
- Create: `tests/test_first_level_clusterer.py` for one-level code compression and source preservation.
- Create: `tests/test_coding_decision_policy.py` for fallback to `其他各类话题` and `其他重要维度`.
- Create: `tests/test_rag_generator_integration.py` for generator output compatibility and no new second/third codes on low confidence.
- Create: `tests/test_manual_coding_compatibility.py` for preserving the auto-coding to manual-coding data contract.
- Modify: `config.py` to add RAG config flags and runtime strategy defaults.
- Modify: `semantic_matcher.py` only if small compatibility helpers are needed; prefer keeping existing behavior intact.
- Modify: `enhanced_coding_generator.py` to initialize and use the new RAG pipeline when enabled, with existing matching as fallback.
- Modify: `coding_library_manager.py` so successful saves invalidate the derived RAG index.
- Modify: `main_window.py` only if a regression test exposes a required progress or compatibility hook; otherwise leave it unchanged.

---

### Task 1: Test Fixtures And Config Flags

**Files:**
- Create: `tests/conftest.py`
- Modify: `config.py`
- Test: `tests/test_runtime_strategy.py`

- [ ] **Step 1: Write the failing fixture and config test**

Create `tests/test_runtime_strategy.py` with this initial test:

```python
from config import Config


def test_rag_config_defaults_exist():
    assert Config.ENABLE_RAG_CODING is True
    assert Config.RAG_INDEX_DIR.endswith("rag_index")
    assert Config.RAG_OTHER_SECOND_LEVEL_NAME == "其他各类话题"
    assert Config.RAG_OTHER_THIRD_LEVEL_NAME == "其他重要维度"
    assert Config.RAG_RUNTIME_STRATEGY == "auto"
    assert Config.RAG_LIGHT_BATCH_SIZE < Config.RAG_CPU_BATCH_SIZE < Config.RAG_GPU_BATCH_SIZE
```

Create `tests/conftest.py` with reusable fixtures:

```python
import json
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def small_coding_library_path(tmp_path: Path) -> Path:
    data = {
        "encoding_library": {
            "third_level_codes": [
                {
                    "id": 1,
                    "name": "个体动机与心理驱动",
                    "description": "描述员工为什么要进行越轨创新的内在原因",
                    "second_level_codes": [
                        {
                            "id": "1.1",
                            "name": "自我效能与成就感",
                            "description": "通过创新证明能力并获得心理满足",
                            "third_level": "个体动机与心理驱动",
                            "third_level_id": 1,
                        },
                        {
                            "id": "1.2",
                            "name": "任务紧急性倒逼",
                            "description": "时间紧迫导致绕开正式流程完成任务",
                            "third_level": "个体动机与心理驱动",
                            "third_level_id": 1,
                        },
                    ],
                },
                {
                    "id": 2,
                    "name": "资源与流程约束",
                    "description": "描述资源不足或流程限制带来的行动变化",
                    "second_level_codes": [
                        {
                            "id": "2.1",
                            "name": "流程审批阻滞",
                            "description": "审批链条太长或流程过慢影响推进",
                            "third_level": "资源与流程约束",
                            "third_level_id": 2,
                        }
                    ],
                },
            ]
        }
    }
    path = tmp_path / "coding_library.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture
def deterministic_embedding():
    vectors = {
        "审批": np.array([1.0, 0.0, 0.0]),
        "流程": np.array([0.9, 0.1, 0.0]),
        "成就": np.array([0.0, 1.0, 0.0]),
        "紧急": np.array([0.0, 0.0, 1.0]),
    }

    def embed(text: str):
        vec = np.array([0.0, 0.0, 0.0])
        for key, value in vectors.items():
            if key in text:
                vec = vec + value
        if not vec.any():
            vec = np.array([0.1, 0.1, 0.1])
        return vec

    return embed
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_runtime_strategy.py::test_rag_config_defaults_exist -v`

Expected: FAIL with an `AttributeError` for `Config.ENABLE_RAG_CODING`.

- [ ] **Step 3: Add minimal config flags**

Append these attributes inside `class Config` in `config.py` near the existing coding configuration:

```python
    # RAG auto-coding configuration
    ENABLE_RAG_CODING = True
    RAG_INDEX_DIR = os.path.join(BASE_DIR, "cache", "rag_index")
    RAG_TOKEN_TOP_K = 80
    RAG_VECTOR_TOP_K = 10
    RAG_FINAL_TOP_K = 5
    RAG_SECOND_LEVEL_THRESHOLD = 0.62
    RAG_SECOND_LEVEL_MARGIN = 0.08
    RAG_THIRD_LEVEL_THRESHOLD = 0.58
    RAG_THIRD_LEVEL_MARGIN = 0.06
    RAG_MIN_CLUSTER_SUPPORT = 2
    RAG_CLUSTER_SIMILARITY_THRESHOLD = 0.82
    RAG_MAX_EMBEDDING_CACHE_SIZE = 10000
    RAG_OTHER_SECOND_LEVEL_NAME = "其他各类话题"
    RAG_OTHER_THIRD_LEVEL_NAME = "其他重要维度"
    RAG_AUTO_REFRESH_INDEX = True
    RAG_INDEX_REBUILD_MODE = "lazy"
    RAG_RUNTIME_STRATEGY = "auto"
    RAG_GPU_BATCH_SIZE = 128
    RAG_CPU_BATCH_SIZE = 32
    RAG_LIGHT_BATCH_SIZE = 8
    RAG_LIGHT_TOKEN_TOP_K = 30
    RAG_LIGHT_VECTOR_TOP_K = 5
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_runtime_strategy.py::test_rag_config_defaults_exist -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add config.py tests/conftest.py tests/test_runtime_strategy.py
git commit -m "test: add RAG config defaults"
```

---

### Task 2: Runtime Strategy Detection

**Files:**
- Create: `runtime_strategy.py`
- Modify: `tests/test_runtime_strategy.py`

- [ ] **Step 1: Write failing runtime strategy tests**

Append to `tests/test_runtime_strategy.py`:

```python
from runtime_strategy import RuntimeStrategyDetector


class FakeCuda:
    def __init__(self, available, name="NVIDIA RTX", total_memory=8 * 1024**3):
        self._available = available
        self._name = name
        self._total_memory = total_memory

    def is_available(self):
        return self._available

    def get_device_name(self, index):
        return self._name

    def get_device_properties(self, index):
        class Props:
            pass
        props = Props()
        props.total_memory = self._total_memory
        return props


def test_runtime_strategy_uses_gpu_when_cuda_available(monkeypatch):
    detector = RuntimeStrategyDetector(cuda=FakeCuda(True), cpu_count_fn=lambda: 12, memory_gb_fn=lambda: 32)
    strategy = detector.detect()
    assert strategy.name == "gpu"
    assert strategy.device == "cuda"
    assert strategy.batch_size == 128
    assert strategy.vector_top_k == 10


def test_runtime_strategy_uses_cpu_when_cuda_unavailable(monkeypatch):
    detector = RuntimeStrategyDetector(cuda=FakeCuda(False), cpu_count_fn=lambda: 8, memory_gb_fn=lambda: 16)
    strategy = detector.detect()
    assert strategy.name == "cpu"
    assert strategy.device == "cpu"
    assert strategy.batch_size == 32
    assert strategy.token_top_k == 80


def test_runtime_strategy_uses_light_mode_for_low_memory_cpu(monkeypatch):
    detector = RuntimeStrategyDetector(cuda=FakeCuda(False), cpu_count_fn=lambda: 4, memory_gb_fn=lambda: 6)
    strategy = detector.detect()
    assert strategy.name == "light"
    assert strategy.device == "cpu"
    assert strategy.batch_size == 8
    assert strategy.token_top_k == 30
    assert strategy.vector_top_k == 5
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_runtime_strategy.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'runtime_strategy'`.

- [ ] **Step 3: Implement `runtime_strategy.py`**

Create `runtime_strategy.py`:

```python
import logging
import os
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuntimeStrategy:
    name: str
    device: str
    batch_size: int
    token_top_k: int
    vector_top_k: int
    use_vector_clustering: bool
    use_reranker: bool
    reason: str


class RuntimeStrategyDetector:
    def __init__(
        self,
        cuda=None,
        cpu_count_fn: Optional[Callable[[], int]] = None,
        memory_gb_fn: Optional[Callable[[], float]] = None,
    ):
        from config import Config

        self.config = Config
        self.cuda = cuda
        self.cpu_count_fn = cpu_count_fn or (lambda: os.cpu_count() or 1)
        self.memory_gb_fn = memory_gb_fn or self._detect_memory_gb

    def detect(self) -> RuntimeStrategy:
        configured = getattr(self.config, "RAG_RUNTIME_STRATEGY", "auto")
        if configured in {"gpu", "cpu", "light"}:
            return self._strategy_for_name(configured, f"configured strategy: {configured}")

        if self._cuda_available():
            return self._strategy_for_name("gpu", "CUDA GPU is available")

        cpu_count = self.cpu_count_fn()
        memory_gb = self.memory_gb_fn()
        if cpu_count >= 6 and memory_gb >= 8:
            return self._strategy_for_name("cpu", f"CPU resources are sufficient: {cpu_count} cores, {memory_gb:.1f} GB RAM")

        return self._strategy_for_name("light", f"limited resources: {cpu_count} cores, {memory_gb:.1f} GB RAM")

    def _strategy_for_name(self, name: str, reason: str) -> RuntimeStrategy:
        if name == "gpu":
            return RuntimeStrategy(
                name="gpu",
                device="cuda",
                batch_size=getattr(self.config, "RAG_GPU_BATCH_SIZE", 128),
                token_top_k=getattr(self.config, "RAG_TOKEN_TOP_K", 80),
                vector_top_k=getattr(self.config, "RAG_VECTOR_TOP_K", 10),
                use_vector_clustering=True,
                use_reranker=True,
                reason=reason,
            )
        if name == "cpu":
            return RuntimeStrategy(
                name="cpu",
                device="cpu",
                batch_size=getattr(self.config, "RAG_CPU_BATCH_SIZE", 32),
                token_top_k=getattr(self.config, "RAG_TOKEN_TOP_K", 80),
                vector_top_k=getattr(self.config, "RAG_VECTOR_TOP_K", 10),
                use_vector_clustering=True,
                use_reranker=True,
                reason=reason,
            )
        return RuntimeStrategy(
            name="light",
            device="cpu",
            batch_size=getattr(self.config, "RAG_LIGHT_BATCH_SIZE", 8),
            token_top_k=getattr(self.config, "RAG_LIGHT_TOKEN_TOP_K", 30),
            vector_top_k=getattr(self.config, "RAG_LIGHT_VECTOR_TOP_K", 5),
            use_vector_clustering=False,
            use_reranker=False,
            reason=reason,
        )

    def _cuda_available(self) -> bool:
        cuda = self.cuda
        if cuda is None:
            try:
                import torch
                cuda = torch.cuda
            except Exception as exc:
                logger.info("Torch CUDA unavailable: %s", exc)
                return False
        try:
            return bool(cuda.is_available())
        except Exception as exc:
            logger.warning("CUDA detection failed: %s", exc)
            return False

    def _detect_memory_gb(self) -> float:
        try:
            import psutil
            return psutil.virtual_memory().total / (1024 ** 3)
        except Exception:
            return 8.0
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_runtime_strategy.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add runtime_strategy.py tests/test_runtime_strategy.py
git commit -m "feat: add RAG runtime strategy detection"
```

---

### Task 3: Derived RAG Index Documents And Lifecycle

**Files:**
- Create: `rag_index.py`
- Create: `tests/test_rag_index.py`

- [ ] **Step 1: Write failing RAG index tests**

Create `tests/test_rag_index.py`:

```python
import json

from rag_index import RagIndexBuilder, RagIndexManager


def test_build_documents_enriches_second_level_with_parent_and_siblings(small_coding_library_path, tmp_path):
    builder = RagIndexBuilder(str(small_coding_library_path), str(tmp_path / "rag_index"))
    documents = builder.build_documents()

    second_doc = next(doc for doc in documents if doc["code_id"] == "1.1")
    assert second_doc["level"] == "second"
    assert second_doc["name"] == "自我效能与成就感"
    assert second_doc["third_level_id"] == 1
    assert "个体动机与心理驱动" in second_doc["text"]
    assert "任务紧急性倒逼" in second_doc["text"]
    assert "自我效能" in second_doc["text"]


def test_index_manager_invalidates_and_detects_stale_index(small_coding_library_path, tmp_path):
    index_dir = tmp_path / "rag_index"
    manager = RagIndexManager(str(small_coding_library_path), str(index_dir))
    manager.rebuild()
    assert manager.is_fresh()

    manager.invalidate()
    assert not manager.is_fresh()

    meta = json.loads((index_dir / "index_meta.json").read_text(encoding="utf-8"))
    assert meta["invalidated"] is True
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_rag_index.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'rag_index'`.

- [ ] **Step 3: Implement `rag_index.py`**

Create `rag_index.py`:

```python
import hashlib
import json
import logging
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import jieba
import numpy as np

logger = logging.getLogger(__name__)


INDEX_VERSION = "rag-index-v1"


def file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip().lower())


def tokenize(text: str) -> List[str]:
    tokens = []
    for token in jieba.lcut(text or ""):
        token = token.strip()
        if len(token) >= 2:
            tokens.append(token)
    return tokens


class RagIndexBuilder:
    def __init__(self, library_path: str, index_dir: str, embedding_fn: Optional[Callable[[str], np.ndarray]] = None):
        self.library_path = library_path
        self.index_dir = Path(index_dir)
        self.embedding_fn = embedding_fn

    def build_documents(self) -> List[Dict[str, Any]]:
        with open(self.library_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        documents: List[Dict[str, Any]] = []
        third_levels = data.get("encoding_library", {}).get("third_level_codes", [])
        for third in third_levels:
            third_id = third.get("id")
            third_name = third.get("name", "")
            third_description = third.get("description", "")
            second_codes = third.get("second_level_codes", []) or []
            sibling_names = [code.get("name", "") for code in second_codes if code.get("name")]

            third_text = self._compose_text(
                "三阶编码",
                third_id,
                third_name,
                third_description,
                "",
                "",
                sibling_names,
            )
            documents.append(
                {
                    "doc_id": f"third:{third_id}",
                    "level": "third",
                    "code_id": third_id,
                    "name": third_name,
                    "description": third_description,
                    "third_level_id": third_id,
                    "third_level": third_name,
                    "tokens": tokenize(third_text),
                    "text": third_text,
                }
            )

            for second in second_codes:
                second_id = second.get("id")
                second_name = second.get("name", "")
                second_description = second.get("description", "")
                second_text = self._compose_text(
                    "二阶编码",
                    second_id,
                    second_name,
                    second_description,
                    third_name,
                    third_description,
                    [name for name in sibling_names if name != second_name],
                )
                documents.append(
                    {
                        "doc_id": f"second:{second_id}",
                        "level": "second",
                        "code_id": second_id,
                        "name": second_name,
                        "description": second_description,
                        "third_level_id": second.get("third_level_id", third_id),
                        "third_level": second.get("third_level", third_name),
                        "tokens": tokenize(second_text),
                        "text": second_text,
                    }
                )
        return documents

    def rebuild(self) -> Dict[str, Any]:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        documents = self.build_documents()
        token_index = self.build_token_index(documents)

        (self.index_dir / "code_documents.json").write_text(
            json.dumps(documents, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (self.index_dir / "token_index.json").write_text(
            json.dumps(token_index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if self.embedding_fn:
            matrix = np.vstack([self.embedding_fn(doc["text"]) for doc in documents]).astype("float32")
        else:
            matrix = np.zeros((len(documents), 1), dtype="float32")
        np.savez_compressed(self.index_dir / "vector_embeddings.npz", embeddings=matrix)

        meta = {
            "index_version": INDEX_VERSION,
            "library_path": os.path.abspath(self.library_path),
            "library_hash": file_sha256(self.library_path),
            "document_count": len(documents),
            "built_at": datetime.now().isoformat(),
            "invalidated": False,
        }
        (self.index_dir / "index_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return meta

    def build_token_index(self, documents: List[Dict[str, Any]]) -> Dict[str, List[int]]:
        index: Dict[str, set] = defaultdict(set)
        for i, doc in enumerate(documents):
            for token in doc.get("tokens", []):
                index[token].add(i)
        return {token: sorted(values) for token, values in index.items()}

    def _compose_text(
        self,
        level: str,
        code_id: Any,
        name: str,
        description: str,
        third_name: str,
        third_description: str,
        sibling_names: List[str],
    ) -> str:
        siblings = "、".join([name for name in sibling_names if name])
        return "\n".join(
            [
                f"层级：{level}",
                f"编码ID：{code_id}",
                f"编码名称：{name}",
                f"定义：{description}",
                f"所属三阶：{third_name}",
                f"三阶定义：{third_description}",
                f"同组三阶下相关二阶：{siblings}",
                f"检索关键词：{'、'.join(tokenize(name + ' ' + description + ' ' + third_name + ' ' + third_description))}",
            ]
        )


class RagIndexManager:
    def __init__(self, library_path: str, index_dir: str, embedding_fn: Optional[Callable[[str], np.ndarray]] = None):
        self.library_path = library_path
        self.index_dir = Path(index_dir)
        self.embedding_fn = embedding_fn

    def is_fresh(self) -> bool:
        meta_path = self.index_dir / "index_meta.json"
        if not meta_path.exists():
            return False
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            return (
                meta.get("index_version") == INDEX_VERSION
                and meta.get("library_hash") == file_sha256(self.library_path)
                and meta.get("invalidated") is False
            )
        except Exception as exc:
            logger.warning("RAG index freshness check failed: %s", exc)
            return False

    def invalidate(self) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        meta_path = self.index_dir / "index_meta.json"
        meta = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
        meta.update({"invalidated": True, "invalidated_at": datetime.now().isoformat()})
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def rebuild(self) -> Dict[str, Any]:
        builder = RagIndexBuilder(self.library_path, str(self.index_dir), self.embedding_fn)
        return builder.rebuild()

    def ensure_fresh(self) -> bool:
        if self.is_fresh():
            return True
        self.rebuild()
        return self.is_fresh()
```

- [ ] **Step 4: Run the RAG index tests**

Run: `python -m pytest tests/test_rag_index.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add rag_index.py tests/test_rag_index.py
git commit -m "feat: add derived RAG index lifecycle"
```

---

### Task 4: Coding Decision Policy

**Files:**
- Create: `coding_decision_policy.py`
- Create: `tests/test_coding_decision_policy.py`

- [ ] **Step 1: Write failing decision policy tests**

Create `tests/test_coding_decision_policy.py`:

```python
from coding_decision_policy import CodingDecisionPolicy


def test_second_level_low_score_falls_back_to_other_topic():
    policy = CodingDecisionPolicy(second_threshold=0.62, second_margin=0.08, min_cluster_support=2)
    decision = policy.decide_second_level(
        candidates=[
            {"name": "流程审批阻滞", "score": 0.55, "token_score": 0.4, "vector_score": 0.6},
        ],
        cluster_support=3,
        token_best_name="流程审批阻滞",
        vector_best_name="流程审批阻滞",
    )
    assert decision.accepted is False
    assert decision.name == "其他各类话题"
    assert decision.reason == "second_score_below_threshold"


def test_second_level_small_margin_falls_back_to_other_topic():
    policy = CodingDecisionPolicy(second_threshold=0.62, second_margin=0.08, min_cluster_support=2)
    decision = policy.decide_second_level(
        candidates=[
            {"name": "流程审批阻滞", "score": 0.71},
            {"name": "任务紧急性倒逼", "score": 0.68},
        ],
        cluster_support=4,
        token_best_name="流程审批阻滞",
        vector_best_name="流程审批阻滞",
    )
    assert decision.name == "其他各类话题"
    assert decision.reason == "second_margin_too_small"


def test_second_level_conflict_falls_back_to_other_topic():
    policy = CodingDecisionPolicy()
    decision = policy.decide_second_level(
        candidates=[{"name": "流程审批阻滞", "score": 0.9}],
        cluster_support=3,
        token_best_name="任务紧急性倒逼",
        vector_best_name="流程审批阻滞",
    )
    assert decision.name == "其他各类话题"
    assert decision.reason == "token_vector_conflict"


def test_third_level_missing_mapping_falls_back_to_other_dimension():
    policy = CodingDecisionPolicy()
    decision = policy.decide_third_level(second_code={})
    assert decision.accepted is False
    assert decision.name == "其他重要维度"
    assert decision.reason == "third_mapping_missing"


def test_third_level_uses_reliable_second_mapping():
    policy = CodingDecisionPolicy()
    decision = policy.decide_third_level(second_code={"third_level": "资源与流程约束", "third_level_id": 2})
    assert decision.accepted is True
    assert decision.name == "资源与流程约束"
    assert decision.reason == "third_from_second_mapping"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_coding_decision_policy.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'coding_decision_policy'`.

- [ ] **Step 3: Implement `coding_decision_policy.py`**

Create `coding_decision_policy.py`:

```python
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class CodingDecision:
    accepted: bool
    name: str
    reason: str
    score: float = 0.0
    code: Optional[Dict[str, Any]] = None


class CodingDecisionPolicy:
    def __init__(
        self,
        second_threshold: float = None,
        second_margin: float = None,
        third_threshold: float = None,
        third_margin: float = None,
        min_cluster_support: int = None,
        other_second_name: str = None,
        other_third_name: str = None,
    ):
        from config import Config

        self.second_threshold = second_threshold if second_threshold is not None else Config.RAG_SECOND_LEVEL_THRESHOLD
        self.second_margin = second_margin if second_margin is not None else Config.RAG_SECOND_LEVEL_MARGIN
        self.third_threshold = third_threshold if third_threshold is not None else Config.RAG_THIRD_LEVEL_THRESHOLD
        self.third_margin = third_margin if third_margin is not None else Config.RAG_THIRD_LEVEL_MARGIN
        self.min_cluster_support = min_cluster_support if min_cluster_support is not None else Config.RAG_MIN_CLUSTER_SUPPORT
        self.other_second_name = other_second_name or Config.RAG_OTHER_SECOND_LEVEL_NAME
        self.other_third_name = other_third_name or Config.RAG_OTHER_THIRD_LEVEL_NAME

    def decide_second_level(
        self,
        candidates: List[Dict[str, Any]],
        cluster_support: int,
        token_best_name: Optional[str],
        vector_best_name: Optional[str],
    ) -> CodingDecision:
        if not candidates:
            return CodingDecision(False, self.other_second_name, "second_no_candidates")

        if cluster_support < self.min_cluster_support:
            return CodingDecision(False, self.other_second_name, "second_cluster_support_too_low")

        if token_best_name and vector_best_name and token_best_name != vector_best_name:
            return CodingDecision(False, self.other_second_name, "token_vector_conflict")

        ordered = sorted(candidates, key=lambda item: item.get("score", 0.0), reverse=True)
        best = ordered[0]
        best_score = float(best.get("score", 0.0))
        if best_score < self.second_threshold:
            return CodingDecision(False, self.other_second_name, "second_score_below_threshold", best_score, best.get("code"))

        if len(ordered) > 1:
            second_score = float(ordered[1].get("score", 0.0))
            if best_score - second_score < self.second_margin:
                return CodingDecision(False, self.other_second_name, "second_margin_too_small", best_score, best.get("code"))

        return CodingDecision(True, best.get("name", self.other_second_name), "second_high_confidence", best_score, best.get("code"))

    def decide_third_level(
        self,
        second_code: Dict[str, Any],
        fallback_candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> CodingDecision:
        mapped_name = second_code.get("third_level")
        mapped_id = second_code.get("third_level_id")
        if mapped_name and mapped_id is not None:
            return CodingDecision(True, mapped_name, "third_from_second_mapping", 1.0, second_code)

        if not fallback_candidates:
            return CodingDecision(False, self.other_third_name, "third_mapping_missing")

        ordered = sorted(fallback_candidates, key=lambda item: item.get("score", 0.0), reverse=True)
        best = ordered[0]
        best_score = float(best.get("score", 0.0))
        if best_score < self.third_threshold:
            return CodingDecision(False, self.other_third_name, "third_score_below_threshold", best_score, best.get("code"))

        if len(ordered) > 1 and best_score - float(ordered[1].get("score", 0.0)) < self.third_margin:
            return CodingDecision(False, self.other_third_name, "third_margin_too_small", best_score, best.get("code"))

        return CodingDecision(True, best.get("name", self.other_third_name), "third_high_confidence", best_score, best.get("code"))
```

- [ ] **Step 4: Run decision policy tests**

Run: `python -m pytest tests/test_coding_decision_policy.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add coding_decision_policy.py tests/test_coding_decision_policy.py
git commit -m "feat: add coding decision policy"
```

---

### Task 5: RAG Semantic Matcher Hybrid Retrieval

**Files:**
- Create: `rag_semantic_matcher.py`
- Create: `tests/test_rag_semantic_matcher.py`

- [ ] **Step 1: Write failing hybrid retrieval tests**

Create `tests/test_rag_semantic_matcher.py`:

```python
import numpy as np

from rag_index import RagIndexManager
from rag_semantic_matcher import RAGSemanticMatcher


def test_hybrid_retrieval_prefers_token_and_vector_agreement(small_coding_library_path, tmp_path, deterministic_embedding):
    index_dir = tmp_path / "rag_index"
    RagIndexManager(str(small_coding_library_path), str(index_dir), deterministic_embedding).rebuild()

    matcher = RAGSemanticMatcher(str(index_dir), embedding_fn=deterministic_embedding)
    result = matcher.match_first_level_to_second_level("审批流程太慢影响项目推进", top_k=3)

    assert result
    assert result[0]["name"] == "流程审批阻滞"
    assert result[0]["score"] > 0.6
    assert result[0]["token_score"] > 0
    assert result[0]["vector_score"] > 0


def test_hybrid_retrieval_returns_empty_when_index_missing(tmp_path, deterministic_embedding):
    matcher = RAGSemanticMatcher(str(tmp_path / "missing"), embedding_fn=deterministic_embedding)
    assert matcher.match_first_level_to_second_level("审批流程太慢") == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_rag_semantic_matcher.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'rag_semantic_matcher'`.

- [ ] **Step 3: Implement `rag_semantic_matcher.py`**

Create `rag_semantic_matcher.py`:

```python
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from rag_index import tokenize

logger = logging.getLogger(__name__)


class RAGSemanticMatcher:
    def __init__(self, index_dir: str, embedding_fn: Optional[Callable[[str], np.ndarray]] = None):
        self.index_dir = Path(index_dir)
        self.embedding_fn = embedding_fn
        self.documents: List[Dict[str, Any]] = []
        self.token_index: Dict[str, List[int]] = {}
        self.embeddings: Optional[np.ndarray] = None
        self._load()

    def _load(self) -> None:
        docs_path = self.index_dir / "code_documents.json"
        token_path = self.index_dir / "token_index.json"
        vector_path = self.index_dir / "vector_embeddings.npz"
        if not docs_path.exists() or not token_path.exists() or not vector_path.exists():
            return
        self.documents = json.loads(docs_path.read_text(encoding="utf-8"))
        self.token_index = json.loads(token_path.read_text(encoding="utf-8"))
        self.embeddings = np.load(vector_path)["embeddings"]

    def match_first_level_to_second_level(self, text: str, top_k: int = 5, token_top_k: int = 80) -> List[Dict[str, Any]]:
        if not self.documents:
            return []

        query_tokens = tokenize(text)
        candidate_indices = self._token_candidates(query_tokens, token_top_k)
        if not candidate_indices:
            candidate_indices = [i for i, doc in enumerate(self.documents) if doc.get("level") == "second"]

        query_embedding = self._embed(text)
        results = []
        for index in candidate_indices:
            doc = self.documents[index]
            if doc.get("level") != "second":
                continue
            token_score = self._token_score(query_tokens, doc.get("tokens", []))
            vector_score = self._vector_score(query_embedding, index)
            score = 0.65 * vector_score + 0.35 * token_score
            results.append(
                {
                    "name": doc.get("name", ""),
                    "score": score,
                    "token_score": token_score,
                    "vector_score": vector_score,
                    "code": doc,
                }
            )
        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:top_k]

    def _token_candidates(self, tokens: List[str], token_top_k: int) -> List[int]:
        counts: Dict[int, int] = {}
        for token in tokens:
            for index in self.token_index.get(token, []):
                counts[index] = counts.get(index, 0) + 1
        ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
        return [index for index, _ in ranked[:token_top_k]]

    def _token_score(self, query_tokens: List[str], doc_tokens: List[str]) -> float:
        if not query_tokens or not doc_tokens:
            return 0.0
        query = set(query_tokens)
        doc = set(doc_tokens)
        return len(query & doc) / max(1, len(query))

    def _embed(self, text: str) -> Optional[np.ndarray]:
        if not self.embedding_fn:
            return None
        return self.embedding_fn(text)

    def _vector_score(self, query_embedding: Optional[np.ndarray], index: int) -> float:
        if query_embedding is None or self.embeddings is None or len(self.embeddings) <= index:
            return 0.0
        doc_embedding = self.embeddings[index]
        denominator = np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
        if denominator == 0:
            return 0.0
        return float(np.dot(query_embedding, doc_embedding) / denominator)
```

- [ ] **Step 4: Run hybrid matcher tests**

Run: `python -m pytest tests/test_rag_semantic_matcher.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add rag_semantic_matcher.py tests/test_rag_semantic_matcher.py
git commit -m "feat: add hybrid RAG semantic matcher"
```

---

### Task 6: First-Level Clustering

**Files:**
- Create: `first_level_clusterer.py`
- Create: `tests/test_first_level_clusterer.py`

- [ ] **Step 1: Write failing clustering tests**

Create `tests/test_first_level_clusterer.py`:

```python
from first_level_clusterer import FirstLevelClusterer


def test_clusterer_merges_duplicate_and_similar_first_level_codes(deterministic_embedding):
    first_level_codes = {
        "FL_0001": ["审批流程慢", [{"content": "审批流程慢"}], 1, 1, [{"content": "审批流程慢"}]],
        "FL_0002": ["流程审批太慢", [{"content": "流程审批太慢"}], 1, 1, [{"content": "流程审批太慢"}]],
        "FL_0003": ["获得成就感", [{"content": "获得成就感"}], 1, 1, [{"content": "获得成就感"}]],
    }
    clusterer = FirstLevelClusterer(embedding_fn=deterministic_embedding, similarity_threshold=0.8)
    clusters = clusterer.cluster(first_level_codes)

    assert len(clusters) == 2
    approval_cluster = next(cluster for cluster in clusters if "审批" in cluster.representative)
    assert approval_cluster.support == 2
    assert set(approval_cluster.source_keys) == {"FL_0001", "FL_0002"}


def test_clusterer_preserves_sentence_details(deterministic_embedding):
    first_level_codes = {
        "FL_0001": ["审批流程慢", [{"content": "审批流程慢"}], 1, 1, [{"content": "审批流程慢", "file": "a.docx"}]],
    }
    clusterer = FirstLevelClusterer(embedding_fn=deterministic_embedding)
    clusters = clusterer.cluster(first_level_codes)
    assert clusters[0].sentence_details[0]["file"] == "a.docx"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_first_level_clusterer.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'first_level_clusterer'`.

- [ ] **Step 3: Implement `first_level_clusterer.py`**

Create `first_level_clusterer.py`:

```python
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from rag_index import tokenize


@dataclass
class FirstLevelCluster:
    representative: str
    source_keys: List[str] = field(default_factory=list)
    source_sentences: List[Any] = field(default_factory=list)
    sentence_details: List[Any] = field(default_factory=list)

    @property
    def support(self) -> int:
        return len(self.source_keys)


class FirstLevelClusterer:
    def __init__(self, embedding_fn: Optional[Callable[[str], np.ndarray]] = None, similarity_threshold: float = None):
        from config import Config

        self.embedding_fn = embedding_fn
        self.similarity_threshold = similarity_threshold if similarity_threshold is not None else Config.RAG_CLUSTER_SIMILARITY_THRESHOLD

    def cluster(self, first_level_codes: Dict[str, List[Any]]) -> List[FirstLevelCluster]:
        clusters: List[FirstLevelCluster] = []
        for key, value in first_level_codes.items():
            text = value[0] if value else ""
            source_sentences = value[1] if len(value) > 1 else []
            sentence_details = value[4] if len(value) > 4 else []
            matched = self._find_cluster(text, clusters)
            if matched is None:
                clusters.append(
                    FirstLevelCluster(
                        representative=text,
                        source_keys=[key],
                        source_sentences=list(source_sentences),
                        sentence_details=list(sentence_details),
                    )
                )
            else:
                matched.source_keys.append(key)
                matched.source_sentences.extend(source_sentences)
                matched.sentence_details.extend(sentence_details)
                if self._representative_score(text) > self._representative_score(matched.representative):
                    matched.representative = text
        return clusters

    def _find_cluster(self, text: str, clusters: List[FirstLevelCluster]) -> Optional[FirstLevelCluster]:
        normalized = self._normalize(text)
        for cluster in clusters:
            if normalized == self._normalize(cluster.representative):
                return cluster
            if self._token_overlap(text, cluster.representative) >= 0.5:
                return cluster
            if self._similarity(text, cluster.representative) >= self.similarity_threshold:
                return cluster
        return None

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", "", (text or "").strip().lower())

    def _token_overlap(self, left: str, right: str) -> float:
        left_tokens = set(tokenize(left))
        right_tokens = set(tokenize(right))
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))

    def _similarity(self, left: str, right: str) -> float:
        if not self.embedding_fn:
            return 0.0
        left_vec = self.embedding_fn(left)
        right_vec = self.embedding_fn(right)
        denominator = np.linalg.norm(left_vec) * np.linalg.norm(right_vec)
        if denominator == 0:
            return 0.0
        return float(np.dot(left_vec, right_vec) / denominator)

    def _representative_score(self, text: str) -> int:
        return len(text or "")
```

- [ ] **Step 4: Run clustering tests**

Run: `python -m pytest tests/test_first_level_clusterer.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add first_level_clusterer.py tests/test_first_level_clusterer.py
git commit -m "feat: add first-level code clustering"
```

---

### Task 7: Integrate RAG Pipeline In EnhancedCodingGenerator

**Files:**
- Modify: `enhanced_coding_generator.py`
- Create: `tests/test_rag_generator_integration.py`

- [ ] **Step 1: Write failing generator integration tests**

Create `tests/test_rag_generator_integration.py`:

```python
from collections import defaultdict

from enhanced_coding_generator import EnhancedCodingGenerator


class FakeCodingLibrary:
    def get_all_second_level_codes(self):
        return [
            {
                "id": "2.1",
                "name": "流程审批阻滞",
                "description": "审批链条太长或流程过慢影响推进",
                "third_level": "资源与流程约束",
                "third_level_id": 2,
            }
        ]

    def get_all_third_level_codes(self):
        return [
            {
                "id": 2,
                "name": "资源与流程约束",
                "description": "描述资源不足或流程限制带来的行动变化",
                "second_level_codes": [],
            }
        ]


class FakeRagMatcher:
    def match_first_level_to_second_level(self, text, top_k=5, token_top_k=80):
        if "审批" in text:
            return [
                {
                    "name": "流程审批阻滞",
                    "score": 0.91,
                    "token_score": 1.0,
                    "vector_score": 0.9,
                    "code": {
                        "id": "2.1",
                        "name": "流程审批阻滞",
                        "third_level": "资源与流程约束",
                        "third_level_id": 2,
                    },
                }
            ]
        return []


def test_rag_pipeline_keeps_generator_output_shape(monkeypatch, deterministic_embedding):
    generator = EnhancedCodingGenerator.__new__(EnhancedCodingGenerator)
    generator.coding_library = FakeCodingLibrary()
    generator.semantic_matcher = None
    generator.similarity_cache = {}
    generator.rag_matcher = FakeRagMatcher()
    generator.rag_enabled = True

    first_level_codes = {
        "FL_0001": ["审批流程慢", [], 1, 1, [{"content": "审批流程慢"}]],
        "FL_0002": ["流程审批太慢", [], 1, 1, [{"content": "流程审批太慢"}]],
    }
    second_level_codes = generator.generate_second_level_codes_improved(first_level_codes)
    third_level_codes = generator.generate_third_level_codes_improved(second_level_codes)

    assert second_level_codes == {"流程审批阻滞": ["FL_0001", "FL_0002"]}
    assert third_level_codes == {"资源与流程约束": ["流程审批阻滞"]}


def test_low_confidence_uses_fixed_fallback(monkeypatch):
    generator = EnhancedCodingGenerator.__new__(EnhancedCodingGenerator)
    generator.coding_library = FakeCodingLibrary()
    generator.semantic_matcher = None
    generator.similarity_cache = {}
    generator.rag_matcher = FakeRagMatcher()
    generator.rag_enabled = True

    first_level_codes = {
        "FL_0001": ["模糊表达", [], 1, 1, [{"content": "模糊表达"}]],
    }
    second_level_codes = generator.generate_second_level_codes_improved(first_level_codes)
    third_level_codes = generator.generate_third_level_codes_improved(second_level_codes)

    assert second_level_codes == {"其他各类话题": ["FL_0001"]}
    assert third_level_codes == {"其他重要维度": ["其他各类话题"]}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_rag_generator_integration.py -v`

Expected: FAIL because `EnhancedCodingGenerator` does not yet use `rag_matcher` or fixed RAG decision policy.

- [ ] **Step 3: Add RAG initialization with safe fallback**

In `enhanced_coding_generator.py`, update `__init__` after `self.semantic_matcher` initialization:

```python
        self.rag_enabled = False
        self.runtime_strategy = None
        self.rag_matcher = None
        self.decision_policy = None
        try:
            from config import Config
            if getattr(Config, 'ENABLE_RAG_CODING', False):
                from runtime_strategy import RuntimeStrategyDetector
                from coding_decision_policy import CodingDecisionPolicy
                from rag_index import RagIndexManager
                from rag_semantic_matcher import RAGSemanticMatcher

                self.runtime_strategy = RuntimeStrategyDetector().detect()
                self.decision_policy = CodingDecisionPolicy()

                if self.semantic_matcher and self.coding_library:
                    index_manager = RagIndexManager(
                        self.coding_library.library_path,
                        Config.RAG_INDEX_DIR,
                        embedding_fn=self.semantic_matcher.get_embedding,
                    )
                    index_manager.ensure_fresh()
                    self.rag_matcher = RAGSemanticMatcher(
                        Config.RAG_INDEX_DIR,
                        embedding_fn=self.semantic_matcher.get_embedding,
                    )
                    self.rag_enabled = True
                    logger.info(f"RAG自动编码已启用，运行策略: {self.runtime_strategy.name}")
        except Exception as e:
            logger.warning(f"RAG自动编码初始化失败，回退到原流程: {e}")
            self.rag_enabled = False
```

- [ ] **Step 4: Route second-level matching through the policy**

In `generate_second_level_codes_improved`, before the existing `self.semantic_matcher.match_first_level_to_second_level` path, add:

```python
            if getattr(self, 'rag_enabled', False) and getattr(self, 'rag_matcher', None):
                from coding_decision_policy import CodingDecisionPolicy
                policy = getattr(self, 'decision_policy', None) or CodingDecisionPolicy()
                token_top_k = getattr(getattr(self, 'runtime_strategy', None), 'token_top_k', 80)
                matches = self.rag_matcher.match_first_level_to_second_level(
                    content,
                    top_k=top_k,
                    token_top_k=token_top_k,
                )
                token_best = matches[0]['name'] if matches else None
                vector_best = matches[0]['name'] if matches else None
                decision = policy.decide_second_level(
                    matches,
                    cluster_support=1,
                    token_best_name=token_best,
                    vector_best_name=vector_best,
                )
                second_cat = decision.name
                if second_cat in categories:
                    categories[second_cat].append(key)
                else:
                    categories.setdefault(policy.other_second_name, []).append(key)
                continue
```

Use `cluster_support=1` only for this compatibility step. Task 8 will replace it with actual clustered support.

- [ ] **Step 5: Route third-level mapping through the policy**

In `generate_third_level_codes_improved`, when `second_code` exists, before semantic third-level matching, add:

```python
            from coding_decision_policy import CodingDecisionPolicy
            policy = getattr(self, 'decision_policy', None) or CodingDecisionPolicy()
            if getattr(self, 'rag_enabled', False):
                decision = policy.decide_third_level(second_code)
                third_cat = decision.name
                if third_cat not in third_level_categories:
                    third_level_categories[third_cat] = []
                third_level_categories[third_cat].append(second_category)
                continue
```

When `second_category == policy.other_second_name`, map it directly to `policy.other_third_name`.

- [ ] **Step 6: Run integration tests**

Run: `python -m pytest tests/test_rag_generator_integration.py -v`

Expected: PASS.

- [ ] **Step 7: Run existing focused tests**

Run: `python -m pytest tests/test_rag_index.py tests/test_rag_semantic_matcher.py tests/test_coding_decision_policy.py -v`

Expected: PASS.

- [ ] **Step 8: Commit**

Run:

```bash
git add enhanced_coding_generator.py tests/test_rag_generator_integration.py
git commit -m "feat: integrate RAG matching in generator"
```

---

### Task 8: Use First-Level Clustering In Generator

**Files:**
- Modify: `enhanced_coding_generator.py`
- Modify: `tests/test_rag_generator_integration.py`

- [ ] **Step 1: Add failing integration test for clustering support**

Append to `tests/test_rag_generator_integration.py`:

```python
def test_rag_pipeline_clusters_similar_first_level_codes_before_matching(deterministic_embedding):
    generator = EnhancedCodingGenerator.__new__(EnhancedCodingGenerator)
    generator.coding_library = FakeCodingLibrary()
    generator.semantic_matcher = None
    generator.similarity_cache = {}
    generator.rag_matcher = FakeRagMatcher()
    generator.rag_enabled = True
    generator.first_level_embedding_fn = deterministic_embedding

    first_level_codes = {
        "FL_0001": ["审批流程慢", [], 1, 1, [{"content": "审批流程慢"}]],
        "FL_0002": ["流程审批太慢", [], 1, 1, [{"content": "流程审批太慢"}]],
        "FL_0003": ["获得成就感", [], 1, 1, [{"content": "获得成就感"}]],
    }

    clustered = generator._cluster_first_level_codes_for_rag(first_level_codes)

    assert len(clustered) == 2
    assert clustered["FL_0001"][3] == 2
    assert "FL_0002" not in clustered
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_rag_generator_integration.py::test_rag_pipeline_clusters_similar_first_level_codes_before_matching -v`

Expected: FAIL with `AttributeError: 'EnhancedCodingGenerator' object has no attribute '_cluster_first_level_codes_for_rag'`.

- [ ] **Step 3: Add clustering helper to `EnhancedCodingGenerator`**

Add this method to `EnhancedCodingGenerator`:

```python
    def _cluster_first_level_codes_for_rag(self, first_level_codes: Dict[str, List[Any]]) -> Dict[str, List[Any]]:
        if not getattr(self, 'rag_enabled', False):
            return first_level_codes
        try:
            from first_level_clusterer import FirstLevelClusterer
            embedding_fn = getattr(self, 'first_level_embedding_fn', None)
            if embedding_fn is None and getattr(self, 'semantic_matcher', None):
                embedding_fn = self.semantic_matcher.get_embedding
            clusterer = FirstLevelClusterer(embedding_fn=embedding_fn)
            clusters = clusterer.cluster(first_level_codes)
            clustered_codes = {}
            for cluster in clusters:
                key = cluster.source_keys[0]
                original = first_level_codes[key]
                clustered_codes[key] = [
                    cluster.representative,
                    cluster.source_sentences,
                    original[2] if len(original) > 2 else 1,
                    cluster.support,
                    cluster.sentence_details,
                ]
            return clustered_codes
        except Exception as e:
            logger.warning(f"一阶编码聚类失败，回退到原一阶候选: {e}")
            return first_level_codes
```

- [ ] **Step 4: Use the helper before second-level generation**

In `generate_codes_with_rules`, after `first_level_codes = self.generate_first_level_codes(...)`, add:

```python
            first_level_codes = self._cluster_first_level_codes_for_rag(first_level_codes)
```

In `generate_codes_with_trained_model`, after building `first_level_codes` and before creating `second_level_mapping`, call the same helper and use the clustered dictionary for mapping.

- [ ] **Step 5: Pass actual cluster support to decision policy**

In the RAG branch of `generate_second_level_codes_improved`, replace `cluster_support=1` with:

```python
                    cluster_support = codes[3] if len(codes) > 3 and isinstance(codes[3], int) else 1
```

Use `cluster_support=cluster_support` in `policy.decide_second_level(...)`.

- [ ] **Step 6: Run clustering and integration tests**

Run: `python -m pytest tests/test_first_level_clusterer.py tests/test_rag_generator_integration.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add enhanced_coding_generator.py tests/test_rag_generator_integration.py
git commit -m "feat: cluster first-level codes before RAG matching"
```

---

### Task 9: Coding Library Edit Invalidates RAG Index

**Files:**
- Modify: `coding_library_manager.py`
- Create: `tests/test_coding_library_rag_invalidation.py`

- [ ] **Step 1: Write failing invalidation test**

Create `tests/test_coding_library_rag_invalidation.py`:

```python
from coding_library_manager import CodingLibraryManager


class RecordingIndexManager:
    def __init__(self):
        self.invalidated = 0

    def invalidate(self):
        self.invalidated += 1


def test_save_library_invalidates_rag_index(small_coding_library_path):
    manager = CodingLibraryManager(str(small_coding_library_path))
    index_manager = RecordingIndexManager()
    manager.rag_index_manager = index_manager

    assert manager.save_library() is True
    assert index_manager.invalidated == 1
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_coding_library_rag_invalidation.py -v`

Expected: FAIL because `CodingLibraryManager.save_library()` does not invalidate `rag_index_manager`.

- [ ] **Step 3: Initialize optional index manager in `CodingLibraryManager`**

In `CodingLibraryManager.__init__`, after `self.semantic_matcher = semantic_matcher`, add:

```python
        self.rag_index_manager = None
        try:
            from config import Config
            if getattr(Config, 'RAG_AUTO_REFRESH_INDEX', False):
                from rag_index import RagIndexManager
                self.rag_index_manager = RagIndexManager(self.library_path, Config.RAG_INDEX_DIR)
        except Exception as e:
            logger.debug(f"RAG索引管理器初始化跳过: {e}")
```

- [ ] **Step 4: Invalidate after successful save**

In the effective `save_library` method, after the JSON write and before `return True`, add:

```python
            if getattr(self, 'rag_index_manager', None):
                try:
                    self.rag_index_manager.invalidate()
                    logger.info("派生RAG索引已标记失效")
                except Exception as e:
                    logger.warning(f"派生RAG索引失效标记失败: {e}")
```

Important: `coding_library_manager.py` currently contains duplicated method names. Apply the invalidation to the save method that is executed at runtime by importing the class and checking `CodingLibraryManager.save_library.__code__.co_firstlineno`.

- [ ] **Step 5: Run invalidation test**

Run: `python -m pytest tests/test_coding_library_rag_invalidation.py -v`

Expected: PASS.

- [ ] **Step 6: Run index lifecycle tests**

Run: `python -m pytest tests/test_rag_index.py tests/test_coding_library_rag_invalidation.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add coding_library_manager.py tests/test_coding_library_rag_invalidation.py
git commit -m "feat: invalidate RAG index after coding library saves"
```

---

### Task 10: Manual Coding Compatibility Regression

**Files:**
- Create: `tests/test_manual_coding_compatibility.py`
- Modify: `enhanced_coding_generator.py` only if the tests expose a structure incompatibility.
- Modify: `main_window.py` only if the tests expose a manual dialog contract break.

- [ ] **Step 1: Write failing or guarding compatibility tests**

Create `tests/test_manual_coding_compatibility.py`:

```python
from enhanced_coding_generator import EnhancedCodingGenerator
from grounded_theory_coder import GroundedTheoryCoder


class MinimalModelManager:
    def is_trained_model_available(self):
        return False

    def release_model_resources(self):
        return None


def test_rag_raw_codes_can_be_numbered_for_manual_coding(monkeypatch):
    generator = EnhancedCodingGenerator.__new__(EnhancedCodingGenerator)
    generator.min_sentence_length = 5
    generator.max_first_level_length = 30
    generator.abstract_cache = {}
    generator.bad_phrase_patterns = []
    generator.coding_library = None
    generator.semantic_matcher = None
    generator.similarity_cache = {}
    generator.rag_enabled = False

    processed_data = {
        "combined_text": "审批流程太慢影响推进。",
        "file_sentence_mapping": {
            "a.docx": {
                "sentences": [
                    {"content": "审批流程太慢影响推进。", "speaker": "respondent", "file": "a.docx"}
                ]
            }
        },
    }

    raw_codes = generator.generate_grounded_theory_codes_multi_files(
        processed_data,
        MinimalModelManager(),
        use_trained_model=False,
    )
    structured = GroundedTheoryCoder().build_coding_structure(raw_codes)

    assert isinstance(structured, dict)
    assert structured
    first_item = next(iter(next(iter(next(iter(structured.values())).values()))))
    assert "code_id" in first_item
    assert "sentence_details" in first_item


def test_manual_coding_dialog_contract_keys_are_preserved():
    raw_codes = {
        "一阶编码": {
            "FL_0001": ["审批流程慢", [], 1, 1, [{"content": "审批流程慢"}]],
        },
        "二阶编码": {
            "其他各类话题": ["FL_0001"],
        },
        "三阶编码": {
            "其他重要维度": ["其他各类话题"],
        },
        "file_sentence_mapping": {
            "a.docx": {"sentences": [{"content": "审批流程慢"}]},
        },
    }
    structured = GroundedTheoryCoder().build_coding_structure(raw_codes)

    assert isinstance(structured, dict)
    assert "C01 其他重要维度" in structured
    assert "B01 其他各类话题" in structured["C01 其他重要维度"]
```

- [ ] **Step 2: Run compatibility tests**

Run: `python -m pytest tests/test_manual_coding_compatibility.py -v`

Expected: PASS if the structure is already compatible; if FAIL, fix only the returned raw-code shape, not the manual dialog flow.

- [ ] **Step 3: If needed, preserve raw-code shape in generator**

If tests fail because RAG metadata leaked into raw-code values, strip internal metadata before returning:

```python
    def _strip_internal_rag_metadata(self, raw_codes: Dict[str, Any]) -> Dict[str, Any]:
        clean = dict(raw_codes)
        clean.pop("_rag_clusters", None)
        clean.pop("_rag_decisions", None)
        return clean
```

Call this helper immediately before `return` in both `generate_codes_with_rules` and `generate_codes_with_trained_model`.

- [ ] **Step 4: Run compatibility and generator tests**

Run: `python -m pytest tests/test_manual_coding_compatibility.py tests/test_rag_generator_integration.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add tests/test_manual_coding_compatibility.py enhanced_coding_generator.py main_window.py
git commit -m "test: preserve manual coding compatibility"
```

Only include `enhanced_coding_generator.py` or `main_window.py` if they actually changed.

---

### Task 11: Full Verification And Documentation Notes

**Files:**
- Modify: `docs/superpowers/plans/2026-04-22-rag-auto-coding.md` only if implementation reveals plan corrections.
- No production file changes unless verification reveals a defect.

- [ ] **Step 1: Run the focused RAG test suite**

Run:

```bash
python -m pytest tests/test_runtime_strategy.py tests/test_rag_index.py tests/test_rag_semantic_matcher.py tests/test_first_level_clusterer.py tests/test_coding_decision_policy.py tests/test_rag_generator_integration.py tests/test_coding_library_rag_invalidation.py tests/test_manual_coding_compatibility.py -v
```

Expected: PASS.

- [ ] **Step 2: Run a broader available test pass**

Run:

```bash
python -m pytest tests -v
```

Expected: PASS for available tests. If unrelated legacy tests fail because they are deleted or missing in the current worktree, record the exact failure and run the focused RAG suite as the required gate.

- [ ] **Step 3: Run import smoke tests**

Run:

```bash
@'
from runtime_strategy import RuntimeStrategyDetector
from rag_index import RagIndexBuilder, RagIndexManager
from rag_semantic_matcher import RAGSemanticMatcher
from first_level_clusterer import FirstLevelClusterer
from coding_decision_policy import CodingDecisionPolicy
from enhanced_coding_generator import EnhancedCodingGenerator
from coding_library_manager import CodingLibraryManager
print("imports ok")
'@ | python -
```

Expected: `imports ok`.

- [ ] **Step 4: Inspect staged diff**

Run:

```bash
git diff --stat
git diff --check
```

Expected: no whitespace errors and only intended files changed.

- [ ] **Step 5: Commit final verification fixes if any**

If verification required a small fix, run:

```bash
git add runtime_strategy.py rag_index.py rag_semantic_matcher.py first_level_clusterer.py coding_decision_policy.py enhanced_coding_generator.py coding_library_manager.py config.py tests/conftest.py tests/test_runtime_strategy.py tests/test_rag_index.py tests/test_rag_semantic_matcher.py tests/test_first_level_clusterer.py tests/test_coding_decision_policy.py tests/test_rag_generator_integration.py tests/test_coding_library_rag_invalidation.py tests/test_manual_coding_compatibility.py
git commit -m "fix: complete RAG auto coding verification"
```

If no fixes were required, do not create an empty commit.

---

## Execution Notes

- Keep `coding_library.json` unchanged unless the user explicitly asks to edit the library content.
- Do not persist analyzed interview text in `cache/rag_index`; only derived coding-library documents belong there.
- Preserve `MainWindow.generate_codes_auto -> GroundedTheoryCoder.build_coding_structure -> MainWindow.save_auto_coding_to_cache -> MainWindow.start_manual_coding` as the compatibility path.
- If GPU detection or sentence-transformer loading fails, log the reason and continue with CPU, light, token, or existing rule-based fallback.
- Use `apply_patch` for manual edits and avoid touching unrelated dirty files in the current worktree.

## Self-Review

- Spec coverage: the plan covers derived RAG index, one-level clustering, hybrid retrieval, confidence fallback, index refresh after library edits, hardware-adaptive runtime, and manual-coding compatibility.
- Placeholder scan: no task contains unresolved placeholder markers or unspecified implementation details.
- Type consistency: `RuntimeStrategy`, `CodingDecision`, `FirstLevelCluster`, and matcher result dictionaries are defined before later tasks use them.
- Scope check: the plan implements the confirmed first version without automatic coding-library merge/delete/rename behavior.
