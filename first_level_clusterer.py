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
    def __init__(
        self,
        embedding_fn: Optional[Callable[[str], np.ndarray]] = None,
        similarity_threshold: Optional[float] = None,
    ):
        from config import Config

        self.embedding_fn = embedding_fn
        self.similarity_threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else Config.RAG_CLUSTER_SIMILARITY_THRESHOLD
        )

    def cluster(self, first_level_codes: Dict[str, List[Any]]) -> List[FirstLevelCluster]:
        clusters: List[FirstLevelCluster] = []
        for key, value in first_level_codes.items():
            entry = value if isinstance(value, (list, tuple)) else [value]
            text = self._coerce_text(entry[0] if entry else "")
            source_sentences = self._coerce_items(entry[1] if len(entry) > 1 else [])
            sentence_details = self._coerce_items(entry[4] if len(entry) > 4 else [])

            matched_cluster = self._find_cluster(text, clusters)
            if matched_cluster is None:
                clusters.append(
                    FirstLevelCluster(
                        representative=text,
                        source_keys=[key],
                        source_sentences=list(source_sentences),
                        sentence_details=list(sentence_details),
                    )
                )
                continue

            matched_cluster.source_keys.append(key)
            matched_cluster.source_sentences.extend(source_sentences)
            matched_cluster.sentence_details.extend(sentence_details)
            current_score = self._representative_score(matched_cluster.representative)
            next_score = self._representative_score(text)
            if next_score > current_score or (
                next_score == current_score
                and self._normalize(text) < self._normalize(matched_cluster.representative)
            ):
                matched_cluster.representative = text
        return clusters

    def _find_cluster(self, text: str, clusters: List[FirstLevelCluster]) -> Optional[FirstLevelCluster]:
        best_cluster: Optional[FirstLevelCluster] = None
        best_score = -1.0
        best_key = ""
        for cluster in clusters:
            score = self._match_score(text, cluster.representative)
            if score < 0:
                continue
            tie_key = self._normalize(cluster.representative)
            if score > best_score or (score == best_score and tie_key < best_key):
                best_cluster = cluster
                best_score = score
                best_key = tie_key
        return best_cluster

    def _match_score(self, text: str, representative: str) -> float:
        left = self._coerce_text(text)
        right = self._coerce_text(representative)
        if self._normalize(left) == self._normalize(right):
            return 1.0

        overlap = self._token_overlap(left, right)
        similarity = self._similarity(left, right)
        if overlap >= 0.5 or similarity >= self.similarity_threshold:
            return max(overlap, similarity)
        return -1.0

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", "", self._coerce_text(text).strip().lower())

    def _token_overlap(self, left: str, right: str) -> float:
        left_tokens = set(tokenize(left))
        right_tokens = set(tokenize(right))
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))

    def _similarity(self, left: str, right: str) -> float:
        if not self.embedding_fn:
            return 0.0
        left_vec = np.asarray(self.embedding_fn(left), dtype="float32").reshape(-1)
        right_vec = np.asarray(self.embedding_fn(right), dtype="float32").reshape(-1)
        if left_vec.shape != right_vec.shape:
            return 0.0
        denominator = np.linalg.norm(left_vec) * np.linalg.norm(right_vec)
        if denominator == 0:
            return 0.0
        return float(np.dot(left_vec, right_vec) / denominator)

    def _representative_score(self, text: str) -> int:
        return len(self._coerce_text(text))

    def _coerce_text(self, text: Any) -> str:
        if text is None:
            return ""
        return text if isinstance(text, str) else str(text)

    def _coerce_items(self, value: Any) -> List[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return list(value)
        if isinstance(value, tuple):
            return list(value)
        return [value]
