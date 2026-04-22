from dataclasses import dataclass
from typing import Callable, Optional
import os

from config import Config


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
        self.config = Config
        self.cuda = cuda
        self.cpu_count_fn = cpu_count_fn or (lambda: os.cpu_count() or 1)
        self.memory_gb_fn = memory_gb_fn or self._detect_memory_gb

    def detect(self) -> RuntimeStrategy:
        configured = str(getattr(self.config, "RAG_RUNTIME_STRATEGY", "auto")).strip().lower()
        if configured == "gpu":
            if self._cuda_available():
                return self._strategy_for_name("gpu", "configured strategy: gpu")
            return self._auto_cpu_or_light("configured gpu unavailable")
        if configured == "cpu":
            return self._auto_cpu_or_light("configured strategy: cpu")
        if configured == "light":
            return self._strategy_for_name("light", "configured strategy: light")

        if self._cuda_available():
            return self._strategy_for_name("gpu", "CUDA GPU is available")

        return self._auto_cpu_or_light("auto strategy without CUDA")

    def _auto_cpu_or_light(self, reason_prefix: str) -> RuntimeStrategy:
        cpu_count = self.cpu_count_fn()
        try:
            memory_gb = self.memory_gb_fn()
        except Exception:
            memory_gb = 0.0

        if cpu_count >= 6 and memory_gb >= 8:
            return self._strategy_for_name(
                "cpu",
                f"{reason_prefix}; CPU resources are sufficient: {cpu_count} cores, {memory_gb:.1f} GB RAM",
            )

        return self._strategy_for_name(
            "light",
            f"{reason_prefix}; limited resources: {cpu_count} cores, {memory_gb:.1f} GB RAM",
        )

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
            except Exception:
                return False
        try:
            return bool(cuda.is_available())
        except Exception:
            return False

    def _detect_memory_gb(self) -> float:
        try:
            import psutil

            return float(psutil.virtual_memory().total) / (1024**3)
        except Exception:
            return 0.0
