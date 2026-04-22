import math
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
        second_threshold: Optional[float] = None,
        second_margin: Optional[float] = None,
        third_threshold: Optional[float] = None,
        third_margin: Optional[float] = None,
        min_cluster_support: Optional[int] = None,
        other_second_name: Optional[str] = None,
        other_third_name: Optional[str] = None,
        allowed_second_code_ids: Optional[List[Any]] = None,
        allowed_third_level_ids: Optional[List[Any]] = None,
        allowed_second_code_names: Optional[Dict[Any, str]] = None,
        allowed_third_level_names: Optional[Dict[Any, str]] = None,
    ):
        from config import Config

        self.second_threshold = (
            second_threshold if second_threshold is not None else Config.RAG_SECOND_LEVEL_THRESHOLD
        )
        self.second_margin = second_margin if second_margin is not None else Config.RAG_SECOND_LEVEL_MARGIN
        self.third_threshold = third_threshold if third_threshold is not None else Config.RAG_THIRD_LEVEL_THRESHOLD
        self.third_margin = third_margin if third_margin is not None else Config.RAG_THIRD_LEVEL_MARGIN
        self.min_cluster_support = (
            min_cluster_support if min_cluster_support is not None else Config.RAG_MIN_CLUSTER_SUPPORT
        )
        self.other_second_name = other_second_name or Config.RAG_OTHER_SECOND_LEVEL_NAME
        self.other_third_name = other_third_name or Config.RAG_OTHER_THIRD_LEVEL_NAME
        self.allowed_second_code_names = self._normalize_allowed_name_map(allowed_second_code_names)
        self.allowed_third_level_names = self._normalize_allowed_name_map(allowed_third_level_names)
        self.allowed_second_code_ids = self._normalize_allowed_ids(allowed_second_code_ids) | set(
            self.allowed_second_code_names
        )
        self.allowed_third_level_ids = self._normalize_allowed_ids(allowed_third_level_ids) | set(
            self.allowed_third_level_names
        )

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

        ordered = sorted(candidates, key=self._candidate_score, reverse=True)
        best = ordered[0]
        best_score = self._candidate_score(best)
        if best_score < self.second_threshold:
            return CodingDecision(
                False,
                self.other_second_name,
                "second_score_below_threshold",
                best_score,
                best.get("code"),
            )

        best_name = best.get("name")
        if not self._has_candidate_name(best_name):
            return CodingDecision(
                False,
                self.other_second_name,
                "second_candidate_name_missing",
                best_score,
                best.get("code"),
            )

        best_code = best.get("code")
        if not self._is_library_second_code(best_code):
            return CodingDecision(
                False,
                self.other_second_name,
                "second_candidate_code_missing",
                best_score,
                best_code if isinstance(best_code, dict) else None,
            )
        canonical_name = self._canonical_name(best_code.get("code_id"), self.allowed_second_code_names)
        if not canonical_name:
            return CodingDecision(
                False,
                self.other_second_name,
                "second_candidate_code_missing",
                best_score,
                best_code,
            )

        if len(ordered) > 1:
            second_score = self._candidate_score(ordered[1])
            if best_score - second_score < self.second_margin:
                return CodingDecision(
                    False,
                    self.other_second_name,
                    "second_margin_too_small",
                    best_score,
                    best.get("code"),
                )

        return CodingDecision(
            True,
            canonical_name,
            "second_high_confidence",
            best_score,
            best_code,
        )

    def decide_third_level(
        self,
        second_code: Dict[str, Any],
        fallback_candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> CodingDecision:
        if not isinstance(second_code, dict):
            return CodingDecision(False, self.other_third_name, "third_mapping_missing")

        mapped_name = second_code.get("third_level")
        mapped_id = second_code.get("third_level_id")
        if (
            self._is_library_second_code(second_code)
            and self._has_candidate_name(mapped_name)
            and self._is_allowed_identifier(mapped_id, self.allowed_third_level_ids)
        ):
            canonical_name = self._canonical_name(mapped_id, self.allowed_third_level_names)
            if canonical_name:
                return CodingDecision(True, canonical_name, "third_from_second_mapping", 1.0, second_code)

        return CodingDecision(False, self.other_third_name, "third_mapping_missing")

    def _candidate_score(self, candidate: Dict[str, Any]) -> float:
        try:
            score = float(candidate.get("score", 0.0))
        except (TypeError, ValueError):
            return 0.0
        if not math.isfinite(score):
            return 0.0
        return score

    def _has_candidate_name(self, name: Any) -> bool:
        return isinstance(name, str) and bool(name.strip())

    def _is_library_second_code(self, code: Any) -> bool:
        return (
            isinstance(code, dict)
            and code.get("level") == "second"
            and self._is_allowed_identifier(code.get("code_id"), self.allowed_second_code_ids)
        )

    def _is_allowed_identifier(self, identifier: Any, allowed_ids: set) -> bool:
        normalized = self._normalize_identifier(identifier)
        return bool(normalized and normalized in allowed_ids)

    def _normalize_allowed_ids(self, values: Optional[List[Any]]) -> set:
        if not values:
            return set()
        return {
            normalized
            for normalized in (self._normalize_identifier(value) for value in values)
            if normalized
        }

    def _normalize_identifier(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    def _normalize_allowed_name_map(self, values: Optional[Dict[Any, str]]) -> Dict[str, str]:
        if not values:
            return {}
        normalized: Dict[str, str] = {}
        for key, name in values.items():
            normalized_key = self._normalize_identifier(key)
            if normalized_key and self._has_candidate_name(name):
                normalized[normalized_key] = name.strip()
        return normalized

    def _canonical_name(self, identifier: Any, names: Dict[str, str]) -> Optional[str]:
        normalized = self._normalize_identifier(identifier)
        if not normalized:
            return None
        return names.get(normalized)
