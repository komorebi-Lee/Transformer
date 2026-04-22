import hashlib
import json
import logging
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
    tokens: List[str] = []
    for token in jieba.lcut(text or ""):
        token = token.strip().lower()
        if len(token) >= 2:
            tokens.append(token)
    return tokens


class RagIndexBuilder:
    def __init__(
        self,
        library_path: str,
        index_dir: str,
        embedding_fn: Optional[Callable[[str], np.ndarray]] = None,
    ):
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
            third_name = str(third.get("name", "")).strip()
            third_description = str(third.get("description", "")).strip()
            second_codes = third.get("second_level_codes", []) or []
            sibling_names = [str(code.get("name", "")).strip() for code in second_codes if code.get("name")]

            third_text = self._compose_text(
                level_label="三阶编码",
                code_id=third_id,
                name=third_name,
                description=third_description,
                parent_name="",
                parent_description="",
                siblings=sibling_names,
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
                second_name = str(second.get("name", "")).strip()
                second_description = str(second.get("description", "")).strip()
                second_text = self._compose_text(
                    level_label="二阶编码",
                    code_id=second_id,
                    name=second_name,
                    description=second_description,
                    parent_name=third_name,
                    parent_description=third_description,
                    siblings=[name for name in sibling_names if name != second_name],
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

    def build_token_index(self, documents: List[Dict[str, Any]]) -> Dict[str, List[int]]:
        index: Dict[str, List[int]] = defaultdict(list)
        for i, document in enumerate(documents):
            for token in set(document.get("tokens", [])):
                index[token].append(i)
        return {token: sorted(postings) for token, postings in index.items()}

    def build_embeddings(self, documents: List[Dict[str, Any]]) -> np.ndarray:
        if not documents:
            return np.zeros((0, 1), dtype="float32")

        vectors = [self._safe_embedding(document.get("text", "")) for document in documents]
        dim = max((vector.shape[0] for vector in vectors), default=1)
        normalized = []
        for vector in vectors:
            if vector.shape[0] != dim:
                padded = np.zeros(dim, dtype="float32")
                padded[: vector.shape[0]] = vector
                vector = padded
            normalized.append(vector)
        return np.stack(normalized).astype("float32")

    def write(self) -> Dict[str, Any]:
        self.index_dir.mkdir(parents=True, exist_ok=True)

        documents = self.build_documents()
        token_index = self.build_token_index(documents)
        embeddings = self.build_embeddings(documents)

        (self.index_dir / "code_documents.json").write_text(
            json.dumps(documents, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (self.index_dir / "token_index.json").write_text(
            json.dumps(token_index, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        np.savez_compressed(self.index_dir / "vector_embeddings.npz", embeddings=embeddings)

        meta = {
            "index_version": INDEX_VERSION,
            "library_path": str(Path(self.library_path).resolve()),
            "library_hash": file_sha256(self.library_path),
            "document_count": len(documents),
            "built_at": datetime.now().isoformat(),
            "invalidated": False,
        }
        (self.index_dir / "index_meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return meta

    def _safe_embedding(self, text: str) -> np.ndarray:
        if not self.embedding_fn:
            # token 哈希向量，保证无模型情况下依然可工作
            return self._hashed_embedding(text)
        try:
            vector = self.embedding_fn(text)
            if vector is None:
                return self._hashed_embedding(text)
            vector = np.asarray(vector, dtype="float32").reshape(-1)
            if vector.size == 0:
                return self._hashed_embedding(text)
            return vector
        except Exception:
            return self._hashed_embedding(text)

    def _hashed_embedding(self, text: str, dim: int = 128) -> np.ndarray:
        vector = np.zeros(dim, dtype="float32")
        for token in tokenize(text):
            vector[hash(token) % dim] += 1.0
        norm = float(np.linalg.norm(vector))
        if norm > 0:
            vector /= norm
        return vector

    def _compose_text(
        self,
        level_label: str,
        code_id: Any,
        name: str,
        description: str,
        parent_name: str,
        parent_description: str,
        siblings: List[str],
    ) -> str:
        parts = [
            f"层级：{level_label}",
            f"编码ID：{code_id}",
            f"编码名称：{name}",
            f"定义：{description}",
        ]
        if parent_name:
            parts.append(f"所属三阶：{parent_name}")
        if parent_description:
            parts.append(f"三阶定义：{parent_description}")
        if siblings:
            parts.append(f"同组三阶下相关二阶：{'、'.join(siblings[:12])}")

        keywords = sorted(set(tokenize(f"{name} {description}")))
        if keywords:
            parts.append(f"检索关键词：{'、'.join(keywords[:20])}")
        return "\n".join(parts)


class RagIndexManager:
    def __init__(
        self,
        library_path: str,
        index_dir: str,
        embedding_fn: Optional[Callable[[str], np.ndarray]] = None,
    ):
        self.library_path = library_path
        self.index_dir = Path(index_dir)
        self.embedding_fn = embedding_fn

    def is_fresh(self) -> bool:
        if not self._artifacts_are_valid():
            return False
        try:
            meta = json.loads((self.index_dir / "index_meta.json").read_text(encoding="utf-8"))
        except Exception:
            return False
        if not isinstance(meta, dict):
            return False
        if meta.get("index_version") != INDEX_VERSION:
            return False
        if meta.get("invalidated") is not False:
            return False
        if str(Path(self.library_path).resolve()) != str(meta.get("library_path")):
            return False
        if meta.get("library_hash") != file_sha256(self.library_path):
            return False
        return True

    def _artifacts_are_valid(self) -> bool:
        required = [
            self.index_dir / "code_documents.json",
            self.index_dir / "token_index.json",
            self.index_dir / "vector_embeddings.npz",
            self.index_dir / "index_meta.json",
        ]
        return all(path.exists() for path in required)

    def invalidate(self) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        meta_path = self.index_dir / "index_meta.json"
        meta: Dict[str, Any] = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
        meta.update({"invalidated": True, "invalidated_at": datetime.now().isoformat()})
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def rebuild(self) -> Dict[str, Any]:
        return RagIndexBuilder(self.library_path, str(self.index_dir), self.embedding_fn).write()

    def ensure_fresh(self) -> bool:
        if self.is_fresh():
            return True
        try:
            self.rebuild()
        except Exception as exc:
            logger.warning("RAG index rebuild failed: %s", exc)
            return False
        return self.is_fresh()
