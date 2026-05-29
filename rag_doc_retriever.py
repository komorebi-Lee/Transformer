"""Document-level RAG retriever for interview text chunks.

QualCoder-inspired: builds a FAISS vector index of document chunks,
then retrieves semantically similar context before first-level coding.

Usage:
    retriever = RagDocRetriever(embedding_fn)
    retriever.index_documents(texts_or_processed_data)
    context_chunks = retriever.retrieve(query_sentence, top_k=3)
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

DOC_INDEX_VERSION = "rag-doc-v1"


def _file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class RagDocRetriever:
    """Builds and queries a FAISS-like vector index of document chunks."""

    def __init__(
        self,
        embedding_fn: Optional[Callable[[str], np.ndarray]] = None,
        index_dir: Optional[str] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
    ):
        self.embedding_fn = embedding_fn
        self.index_dir = Path(index_dir) if index_dir else None
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Internal state
        self._documents: List[Dict[str, Any]] = []
        self._embeddings: Optional[np.ndarray] = None
        self._loaded = False

    # ------------------------------------------------------------------
    # Build index
    # ------------------------------------------------------------------

    def index_documents(
        self,
        processed_data: Dict[str, Any],
        source_label: str = "",
    ) -> int:
        """Index all interview text chunks from processed_data.

        Args:
            processed_data: Output of DataProcessor, with file_sentence_mapping.
            source_label: Optional label for tracking document source.

        Returns:
            Number of chunks indexed.
        """
        chunks = self._extract_chunks(processed_data, source_label)
        if not chunks:
            logger.warning("RagDocRetriever: no chunks extracted")
            return 0

        texts = [chunk["text"] for chunk in chunks]
        self._embeddings = self._embed_batch(texts)
        self._documents = chunks
        self._loaded = True

        if self.index_dir:
            self._persist(chunks, self._embeddings)

        logger.info("RagDocRetriever indexed %d document chunks (dim=%d)",
                     len(chunks), self._embeddings.shape[1] if self._embeddings.size else 0)
        return len(chunks)

    def index_texts(self, texts: List[str], source_label: str = "") -> int:
        """Index plain text strings as chunks."""
        chunks: List[Dict[str, Any]] = []
        for i, text in enumerate(texts):
            sub_chunks = self._split_text(text)
            for j, sub in enumerate(sub_chunks):
                chunks.append({
                    "chunk_id": f"chunk_{i}_{j}",
                    "text": sub,
                    "source": source_label,
                    "char_offset": j * (self.chunk_size - self.chunk_overlap),
                })

        if not chunks:
            return 0

        self._embeddings = self._embed_batch([c["text"] for c in chunks])
        self._documents = chunks
        self._loaded = True
        return len(chunks)

    # ------------------------------------------------------------------
    # Retrieve
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Retrieve top_k most similar document chunks for a query sentence.

        Returns:
            List of {"text": str, "score": float, "chunk_id": str, "source": str}
        """
        if not self._loaded or self._embeddings is None or len(self._documents) == 0:
            return []

        query_vec = self._embed_single(query)
        if query_vec is None:
            return []

        # Cosine similarity against all chunks
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return []

        doc_norms = np.linalg.norm(self._embeddings, axis=1)
        doc_norms = np.where(doc_norms == 0, 1e-9, doc_norms)

        scores = np.dot(self._embeddings, query_vec) / (doc_norms * query_norm)

        # Top-k by score
        if len(scores) <= top_k:
            top_indices = np.argsort(scores)[::-1]
        else:
            top_indices = np.argpartition(-scores, top_k)[:top_k]
            top_indices = top_indices[np.argsort(-scores[top_indices])]

        results: List[Dict[str, Any]] = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < min_score:
                continue
            doc = self._documents[int(idx)]
            results.append({
                "text": doc["text"],
                "score": round(score, 4),
                "chunk_id": doc.get("chunk_id", ""),
                "source": doc.get("source", ""),
            })
            if len(results) >= top_k:
                break

        return results

    def retrieve_with_context(
        self,
        query: str,
        top_k: int = 3,
        context_radius: int = 1,
    ) -> List[Dict[str, Any]]:
        """Retrieve chunks and include neighboring chunks for context."""
        hits = self.retrieve(query, top_k=top_k)
        enriched: List[Dict[str, Any]] = []
        seen: set = set()
        for hit in hits:
            chunk_id = hit["chunk_id"]
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            enriched.append(hit)

            # Find and add neighbors
            for doc in self._documents:
                neighbor_id = doc.get("chunk_id", "")
                if neighbor_id in seen:
                    continue
                # Parse chunk IDs like "chunk_i_j" to find adjacent chunks
                if self._are_adjacent(chunk_id, neighbor_id, context_radius):
                    seen.add(neighbor_id)
                    enriched.append({
                        "text": doc["text"],
                        "score": hit["score"] * 0.8,  # Slightly lower confidence for neighbors
                        "chunk_id": neighbor_id,
                        "source": doc.get("source", ""),
                    })
        return enriched

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Optional[str] = None) -> str:
        target = Path(path) if path else self.index_dir
        if not target:
            raise ValueError("No path specified for saving index")
        target = Path(target)
        target.mkdir(parents=True, exist_ok=True)

        (target / "documents.json").write_text(
            json.dumps(self._documents, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        np.savez_compressed(target / "doc_embeddings.npz", embeddings=self._embeddings)

        meta = {
            "version": DOC_INDEX_VERSION,
            "document_count": len(self._documents),
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "built_at": datetime.now().isoformat(),
            "embedding_dim": int(self._embeddings.shape[1]) if self._embeddings is not None and self._embeddings.size else 0,
        }
        (target / "doc_meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8",
        )

        logger.info("RagDocRetriever saved %d documents to %s", len(self._documents), target)
        return str(target)

    def load(self, path: Optional[str] = None) -> bool:
        target = Path(path) if path else self.index_dir
        if not target or not target.exists():
            return False

        docs_path = target / "documents.json"
        emb_path = target / "doc_embeddings.npz"
        meta_path = target / "doc_meta.json"

        if not docs_path.exists() or not emb_path.exists():
            return False

        try:
            self._documents = json.loads(docs_path.read_text(encoding="utf-8"))
            self._embeddings = np.load(emb_path)["embeddings"].astype("float32", copy=False)
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if meta.get("version") != DOC_INDEX_VERSION:
                    logger.warning("Doc index version mismatch, rebuild recommended")
            self._loaded = True
            return True
        except Exception as exc:
            logger.warning("Failed to load doc index: %s", exc)
            return False

    @property
    def is_loaded(self) -> bool:
        return self._loaded and len(self._documents) > 0

    @property
    def document_count(self) -> int:
        return len(self._documents)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _extract_chunks(
        self,
        processed_data: Dict[str, Any],
        source_label: str,
    ) -> List[Dict[str, Any]]:
        chunks: List[Dict[str, Any]] = []
        file_sentence_mapping = processed_data.get("file_sentence_mapping", {})

        for filename, file_data in file_sentence_mapping.items():
            sentences = file_data.get("sentences", [])
            texts = [
                (s.get("content", "") or "").strip()
                for s in sentences
                if (s.get("content", "") or "").strip()
            ]
            if not texts:
                continue

            # Build long text for chunking
            combined = "\n".join(texts)
            sub_chunks = self._split_text(combined)

            label = source_label or filename
            for j, sub in enumerate(sub_chunks):
                chunks.append({
                    "chunk_id": f"chunk_{label}_{j}",
                    "text": sub,
                    "source": label,
                    "char_offset": j * (self.chunk_size - self.chunk_overlap),
                })
        return chunks

    def _split_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks, respecting sentence boundaries."""
        if len(text) <= self.chunk_size:
            return [text]

        chunks: List[str] = []
        # Split on Chinese sentence delimiters for cleaner boundaries
        import re
        sentences = re.split(r'(?<=[。！？\n])', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        current = ""
        for sent in sentences:
            if len(current) + len(sent) <= self.chunk_size:
                current += sent
            else:
                if current:
                    chunks.append(current)
                # If a single sentence exceeds chunk_size, add it as-is
                if len(sent) > self.chunk_size:
                    if current:
                        chunks.append(current)
                    chunks.append(sent)
                    current = ""
                else:
                    # Overlap: keep last few chars of previous chunk
                    overlap_text = current[-self.chunk_overlap:] if current and self.chunk_overlap > 0 else ""
                    current = overlap_text + sent

        if current:
            chunks.append(current)

        return chunks

    def _embed_single(self, text: str) -> Optional[np.ndarray]:
        if not self.embedding_fn:
            return None
        try:
            vec = self.embedding_fn(text)
            if vec is None:
                return None
            return np.asarray(vec, dtype="float32").reshape(-1)
        except Exception as exc:
            logger.warning("RagDocRetriever embedding failed: %s", exc)
            return None

    def _embed_batch(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 1), dtype="float32")
        if not self.embedding_fn:
            return np.zeros((len(texts), 1), dtype="float32")

        vectors: List[np.ndarray] = []
        for text in texts:
            vec = self._embed_single(text)
            if vec is not None:
                vectors.append(vec)

        if not vectors:
            return np.zeros((len(texts), 1), dtype="float32")

        dim = vectors[0].shape[0]
        result = np.zeros((len(texts), dim), dtype="float32")
        for i, vec in enumerate(vectors):
            if vec.shape[0] == dim:
                result[i] = vec
        return result

    def _are_adjacent(self, chunk_id_a: str, chunk_id_b: str, radius: int) -> bool:
        """Check if two chunks are within `radius` of each other."""
        try:
            parts_a = chunk_id_a.rsplit("_", 1)
            parts_b = chunk_id_b.rsplit("_", 1)
            if parts_a[0] != parts_b[0]:
                return False
            idx_a = int(parts_a[1])
            idx_b = int(parts_b[1])
            return abs(idx_a - idx_b) <= radius
        except (ValueError, IndexError):
            return False

    def _persist(self, documents: List[Dict[str, Any]], embeddings: np.ndarray) -> None:
        if not self.index_dir:
            return
        self.index_dir.mkdir(parents=True, exist_ok=True)
        try:
            (self.index_dir / "documents.json").write_text(
                json.dumps(documents, ensure_ascii=False, indent=2), encoding="utf-8",
            )
            np.savez_compressed(self.index_dir / "doc_embeddings.npz", embeddings=embeddings)
            meta = {
                "version": DOC_INDEX_VERSION,
                "document_count": len(documents),
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "built_at": datetime.now().isoformat(),
                "embedding_dim": int(embeddings.shape[1]) if embeddings.size else 0,
            }
            (self.index_dir / "doc_meta.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Failed to persist doc index: %s", exc)
