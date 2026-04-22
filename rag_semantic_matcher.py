import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from rag_index import INDEX_VERSION, tokenize

logger = logging.getLogger(__name__)


class RAGSemanticMatcher:
    def __init__(
        self,
        index_dir: str,
        embedding_fn: Optional[Callable[[str], np.ndarray]] = None,
    ):
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
        meta_path = self.index_dir / "index_meta.json"
        if not docs_path.exists() or not token_path.exists() or not vector_path.exists() or not meta_path.exists():
            return

        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            documents = json.loads(docs_path.read_text(encoding="utf-8"))
            token_index = json.loads(token_path.read_text(encoding="utf-8"))
            embeddings = np.load(vector_path)["embeddings"].astype("float32", copy=False)
        except Exception as exc:
            logger.warning("Failed to load RAG semantic index: %s", exc)
            return

        if not isinstance(meta, dict):
            return
        if meta.get("index_version") != INDEX_VERSION or meta.get("invalidated") is not False:
            return
        if not isinstance(documents, list) or not isinstance(token_index, dict):
            return
        if not all(isinstance(document, dict) for document in documents):
            return
        if meta.get("document_count") != len(documents):
            return
        if len(embeddings.shape) != 2 or embeddings.shape[0] != len(documents):
            return

        self.documents = documents
        self.token_index = self._sanitize_token_index(token_index, len(documents))
        self.embeddings = embeddings

    def match_first_level_to_second_level(
        self,
        text: str,
        top_k: int = 5,
        token_top_k: int = 80,
    ) -> List[Dict[str, Any]]:
        if top_k <= 0 or token_top_k <= 0 or not self.documents:
            return []

        query_tokens = tokenize(text)
        candidate_indices = self._token_candidates(query_tokens, token_top_k)
        if not candidate_indices:
            candidate_indices = [
                index for index, document in enumerate(self.documents) if document.get("level") == "second"
            ]

        query_embedding = self._embed(text)
        results = self._score_second_level_candidates(candidate_indices, query_tokens, query_embedding)
        if not results:
            fallback_indices = [
                index for index, document in enumerate(self.documents) if document.get("level") == "second"
            ]
            results = self._score_second_level_candidates(fallback_indices, query_tokens, query_embedding)

        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:top_k]

    def second_code_name_map(self) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        for document in self.documents:
            if document.get("level") != "second":
                continue
            code_id = str(document.get("code_id", "")).strip()
            name = str(document.get("name", "")).strip()
            if code_id and name:
                mapping[code_id] = name
        return mapping

    def third_level_name_map(self) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        for document in self.documents:
            if document.get("level") != "third":
                continue
            third_level_id = document.get("code_id")
            third_level_name = document.get("name")
            if third_level_id is None or not third_level_name:
                continue
            normalized_id = str(third_level_id).strip()
            normalized_name = str(third_level_name).strip()
            if normalized_id and normalized_name:
                mapping[normalized_id] = normalized_name
        return mapping

    def _token_candidates(self, tokens: List[str], token_top_k: int) -> List[int]:
        counts: Dict[int, int] = {}
        for token in tokens:
            for index in self.token_index.get(token, []):
                if index < 0:
                    continue
                counts[index] = counts.get(index, 0) + 1

        ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
        return [index for index, _ in ranked[:token_top_k]]

    def _token_score(self, query_tokens: List[str], document_tokens: List[str]) -> float:
        if not query_tokens or not document_tokens:
            return 0.0
        query = set(query_tokens)
        document = set(document_tokens)
        return len(query & document) / max(1, len(query))

    def _embed(self, text: str) -> Optional[np.ndarray]:
        if not self.embedding_fn:
            return None
        try:
            vector = self.embedding_fn(text)
            if vector is None:
                return None
            return np.asarray(vector, dtype="float32").reshape(-1)
        except Exception as exc:
            logger.warning("RAG query embedding failed: %s", exc)
            return None

    def _vector_score(self, query_embedding: Optional[np.ndarray], index: int) -> float:
        if query_embedding is None or self.embeddings is None or index < 0 or index >= len(self.embeddings):
            return 0.0

        document_embedding = np.asarray(self.embeddings[index], dtype="float32").reshape(-1)
        if document_embedding.shape != query_embedding.shape:
            return 0.0

        denominator = np.linalg.norm(query_embedding) * np.linalg.norm(document_embedding)
        if denominator == 0:
            return 0.0
        return float(np.dot(query_embedding, document_embedding) / denominator)

    def _score_second_level_candidates(
        self,
        candidate_indices: List[int],
        query_tokens: List[str],
        query_embedding: Optional[np.ndarray],
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for index in candidate_indices:
            if index < 0 or index >= len(self.documents):
                continue
            document = self.documents[index]
            if document.get("level") != "second":
                continue

            document_tokens = document.get("tokens", [])
            if not isinstance(document_tokens, list):
                document_tokens = []
            token_score = self._token_score(query_tokens, document_tokens)
            vector_score = self._vector_score(query_embedding, index)
            score = 0.65 * vector_score + 0.35 * token_score
            results.append(
                {
                    "name": document.get("name", ""),
                    "score": score,
                    "token_score": token_score,
                    "vector_score": vector_score,
                    "code": document,
                }
            )
        return results

    def _sanitize_token_index(self, token_index: Dict[str, Any], document_count: int) -> Dict[str, List[int]]:
        sanitized: Dict[str, List[int]] = {}
        for token, postings in token_index.items():
            if not isinstance(token, str) or not isinstance(postings, list):
                continue
            valid_indices = sorted(
                {
                    index
                    for index in postings
                    if isinstance(index, int) and not isinstance(index, bool) and 0 <= index < document_count
                }
            )
            if valid_indices:
                sanitized[token] = valid_indices
        return sanitized
