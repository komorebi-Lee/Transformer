"""kNN-based abstract code generator for first-level coding.

Builds a FAISS index from v11 training data (sentence → abstract label pairs),
then retrieves the most similar training sentences' abstract labels as
"generative" candidates for new sentences.

This bridges the extractive→abstractive gap: instead of trying to extract
abstract labels from text (impossible), we retrieve them from similar
training examples.

Usage:
    gen = KnnAbstractGenerator()
    gen.build_index(v11_path)
    candidates = gen.retrieve("某个访谈句子", top_k=5)
    # → [{"text": "资源不足", "score": 0.92, "source_text": "..."}, ...]
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False
    logger.warning("faiss not available, using numpy fallback")


class KnnAbstractGenerator:
    """Retrieve abstract codes from v11 training data via kNN."""

    def __init__(
        self,
        embedding_fn=None,
        index_path: Optional[str] = None,
    ):
        self.embedding_fn = embedding_fn  # (str) → np.ndarray
        self.index_path = index_path

        self._sentences: List[str] = []
        self._abstracts: List[str] = []
        self._embeddings: Optional[np.ndarray] = None
        self._faiss_index: Optional[Any] = None
        self._loaded = False

    # ------------------------------------------------------------------
    # Build index
    # ------------------------------------------------------------------

    def build_index(
        self,
        v11_path: str,
        max_samples: Optional[int] = None,
    ) -> int:
        """Build FAISS index from v11 training data.

        Args:
            v11_path: Path to v11 JSON file.
            max_samples: If set, cap the number of samples used.

        Returns:
            Number of indexed pairs.
        """
        if not self.embedding_fn:
            raise RuntimeError("embedding_fn is required to build index")

        with open(v11_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        training_data = data.get("training_data", [])
        if not training_data:
            raise ValueError("No training_data in v11 JSON")

        if max_samples and len(training_data) > max_samples:
            import random
            random.seed(42)
            training_data = random.sample(training_data, max_samples)

        sentences: List[str] = []
        abstracts: List[str] = []
        seen: set = set()

        for item in training_data:
            sent = str(
                (item.get("input_sentences", {}) or {}).get("original_content", "")
            ).strip()
            abstract = str(item.get("target_abstract", "")).strip()
            if not sent or not abstract:
                continue
            # Deduplicate by (sentence, abstract) pair
            key = (sent, abstract)
            if key in seen:
                continue
            seen.add(key)
            sentences.append(sent)
            abstracts.append(abstract)

        if not sentences:
            raise ValueError("No valid (sentence, abstract) pairs found")

        logger.info("Encoding %d v11 sentences ...", len(sentences))
        embeddings_list: List[np.ndarray] = []
        batch_size = 64
        for i in range(0, len(sentences), batch_size):
            batch = sentences[i : i + batch_size]
            batch_embs = []
            for text in batch:
                vec = self.embedding_fn(text)
                if vec is not None:
                    batch_embs.append(np.asarray(vec, dtype="float32").reshape(-1))
                else:
                    batch_embs.append(np.zeros(512, dtype="float32"))
            embeddings_list.extend(batch_embs)

        self._embeddings = np.stack(embeddings_list, axis=0).astype("float32")
        self._sentences = sentences
        self._abstracts = abstracts

        # Normalize for cosine similarity
        norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1e-9, norms)
        self._embeddings = self._embeddings / norms

        # Build FAISS index
        dim = self._embeddings.shape[1]
        if HAS_FAISS:
            self._faiss_index = faiss.IndexFlatIP(dim)  # inner product = cosine on normalized vectors
            self._faiss_index.add(self._embeddings)
            logger.info("FAISS index built: %d vectors, dim=%d", len(sentences), dim)
        else:
            logger.info("Numpy index built: %d vectors, dim=%d", len(sentences), dim)

        self._loaded = True

        if self.index_path:
            self.save(self.index_path)

        return len(sentences)

    # ------------------------------------------------------------------
    # Retrieve
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Retrieve top-k abstract codes for a query sentence.

        Args:
            query: The normalized interview sentence.
            top_k: Number of abstract candidates to return.
            min_score: Minimum cosine similarity threshold.

        Returns:
            List of {"text": abstract_label, "score": similarity, "source_text": v11_sentence}
        """
        if not self._loaded:
            return []

        query_vec = self._encode_query(query)
        if query_vec is None:
            return []

        # Cosine similarity search
        if self._faiss_index is not None:
            scores, indices = self._faiss_index.search(
                query_vec.reshape(1, -1).astype("float32"), min(top_k * 3, len(self._sentences))
            )
            scores = scores[0]
            indices = indices[0]
        else:
            # Numpy fallback
            scores = np.dot(self._embeddings, query_vec)
            if len(scores) <= top_k * 3:
                indices = np.argsort(scores)[::-1]
            else:
                k = min(top_k * 3, len(scores))
                part_indices = np.argpartition(-scores, k)[:k]
                indices = part_indices[np.argsort(-scores[part_indices])]
            scores = scores[indices]

        results: List[Dict[str, Any]] = []
        seen_abstracts: set = set()

        for idx, score in zip(indices, scores):
            score_f = float(score)
            if score_f < min_score:
                continue
            abstract = self._abstracts[int(idx)]
            if abstract in seen_abstracts:
                continue
            seen_abstracts.add(abstract)
            results.append({
                "text": abstract,
                "score": round(score_f, 4),
                "source_text": self._sentences[int(idx)],
            })
            if len(results) >= top_k:
                break

        return results

    def retrieve_and_merge(
        self,
        query: str,
        existing_candidates: List[Dict[str, Any]],
        top_k: int = 5,
        min_score: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Retrieve abstracts and merge with existing candidates.

        Existing candidates with the same text get their scores boosted.
        """
        knn_results = self.retrieve(query, top_k=top_k, min_score=min_score)

        # Build lookup of existing texts
        existing_texts: Dict[str, int] = {}
        for i, cand in enumerate(existing_candidates):
            t = str(cand.get("text", "")).strip()
            if t:
                existing_texts[t] = i

        merged = list(existing_candidates)
        for knn in knn_results:
            text = knn["text"]
            if text in existing_texts:
                # Boost existing candidate score
                idx = existing_texts[text]
                boost = knn["score"] * 3.0
                merged[idx]["rule_score"] = round(
                    float(merged[idx].get("rule_score", 0)) + boost, 4
                )
                merged[idx]["knn_boost"] = round(float(knn["score"]), 4)
            else:
                # Add as new candidate (high base score from v11 gold)
                merged.append({
                    "text": text,
                    "raw_text": query,
                    "rule_score": round(5.0 + knn["score"] * 4.0, 4),
                    "rerank_score": None,
                    "selected": False,
                    "best_rule": False,
                    "knn_source": "v11",
                    "knn_score": round(float(knn["score"]), 4),
                    "knn_source_text": knn.get("source_text", ""),
                })

        return merged

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Save index to disk."""
        os.makedirs(path, exist_ok=True)
        np.savez_compressed(
            os.path.join(path, "knn_embeddings.npz"),
            embeddings=self._embeddings,
        )
        with open(os.path.join(path, "knn_sentences.json"), "w", encoding="utf-8") as fh:
            json.dump(
                {"sentences": self._sentences, "abstracts": self._abstracts},
                fh, ensure_ascii=False, indent=2,
            )
        if self._faiss_index is not None and HAS_FAISS:
            faiss.write_index(self._faiss_index, os.path.join(path, "knn_index.faiss"))
        logger.info("KNN index saved to %s (%d pairs)", path, len(self._sentences))

    def load(self, path: str) -> bool:
        """Load index from disk."""
        emb_path = os.path.join(path, "knn_embeddings.npz")
        data_path = os.path.join(path, "knn_sentences.json")
        faiss_path = os.path.join(path, "knn_index.faiss")

        if not os.path.exists(emb_path) or not os.path.exists(data_path):
            return False

        try:
            self._embeddings = np.load(emb_path)["embeddings"].astype("float32", copy=False)
            with open(data_path, "r", encoding="utf-8") as fh:
                meta = json.load(fh)
            self._sentences = meta["sentences"]
            self._abstracts = meta["abstracts"]

            if HAS_FAISS and os.path.exists(faiss_path):
                self._faiss_index = faiss.read_index(faiss_path)
            self._loaded = True
            return True
        except Exception as exc:
            logger.warning("Failed to load KNN index: %s", exc)
            return False

    @property
    def is_loaded(self) -> bool:
        return self._loaded and len(self._sentences) > 0

    @property
    def pair_count(self) -> int:
        return len(self._sentences)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _encode_query(self, query: str) -> Optional[np.ndarray]:
        if not self.embedding_fn:
            return None
        try:
            vec = self.embedding_fn(query)
            if vec is None:
                return None
            vec = np.asarray(vec, dtype="float32").reshape(-1)
            # Normalize
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            return vec
        except Exception as exc:
            logger.warning("KNN encode failed: %s", exc)
            return None


# ------------------------------------------------------------------
# Factory
# ------------------------------------------------------------------

def create_knn_generator(
    v11_path: str,
    model_manager=None,
    index_dir: Optional[str] = None,
    max_samples: Optional[int] = None,
    csv_dir: Optional[str] = None,
) -> Optional[KnnAbstractGenerator]:
    """Create and build a KnnAbstractGenerator from v11 data + optional CSV data.

    Uses the bge-small-zh-v1.5 model from model_manager for embeddings.

    If csv_dir is provided, loads (一阶编码, 原始文本) pairs from all CSV files
    in that directory and combines with v11 data before building the index.
    """
    embedding_fn = None
    if model_manager:
        try:
            model_manager.ensure_sentence_model_loaded()
            embedding_fn = model_manager.encode_sentence
        except Exception:
            pass

    # Fallback: load bge directly
    if embedding_fn is None:
        try:
            from sentence_transformers import SentenceTransformer
            bge_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "local_models", "bge-small-zh-v1.5",
            )
            if os.path.exists(bge_path):
                bge_model = SentenceTransformer(bge_path)

                def _embed(text: str):
                    return bge_model.encode(text, normalize_embeddings=True)

                embedding_fn = _embed
                logger.info("Loaded bge-small-zh-v1.5 directly for KNN")
        except Exception as exc:
            logger.warning("Failed to load bge directly: %s", exc)

    if embedding_fn is None:
        logger.error("No embedding function available for KNN generator")
        return None

    # Try loading pre-built combined index first
    combined_dir = index_dir or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "cache", "knn_combined_index",
    )
    generator = KnnAbstractGenerator(
        embedding_fn=embedding_fn,
        index_path=combined_dir,
    )
    if os.path.exists(os.path.join(combined_dir, "knn_index.faiss")):
        if generator.load(combined_dir):
            logger.info("KNN generator loaded from combined index: %d pairs", generator.pair_count)
            return generator
        logger.warning("Failed to load combined index, will rebuild")

    # Load v11 pairs
    with open(v11_path, "r", encoding="utf-8") as fh:
        v11_data = json.load(fh)
    v11_training = v11_data.get("training_data", [])
    all_pairs: list = []

    import csv
    seen: set = set()
    for item in v11_training:
        sent = str(
            (item.get("input_sentences", {}) or {}).get("original_content", "")
        ).strip()
        abstract = str(item.get("target_abstract", "")).strip()
        if not sent or not abstract:
            continue
        key = (sent, abstract)
        if key in seen:
            continue
        seen.add(key)
        all_pairs.append((sent, abstract))
    logger.info("v11: %d unique pairs", len(all_pairs))

    # Load CSV pairs if csv_dir is provided
    if csv_dir and os.path.isdir(csv_dir):
        csv_files = [
            ("final_standard.csv", "gbk"),
            ("standard_augmented.csv", "utf-8"),
            ("standard.csv", "gbk"),
            ("standard2.csv", "utf-8"),
        ]
        for fname, enc in csv_files:
            path = os.path.join(csv_dir, fname)
            if not os.path.exists(path):
                continue
            count = 0
            with open(path, "r", encoding=enc, errors="replace") as fh:
                reader = csv.reader(fh)
                next(reader, None)
                for row in reader:
                    if len(row) < 2:
                        continue
                    code = row[0].strip()
                    text = row[1].strip()
                    if not code or not text or code.lower() == "nan":
                        continue
                    key = (text, code)
                    if key in seen:
                        continue
                    seen.add(key)
                    all_pairs.append((text, code))
                    count += 1
            logger.info("  %s: %d pairs", fname, count)

    # Build index from combined pairs
    sentences = [p[0] for p in all_pairs]
    abstracts = [p[1] for p in all_pairs]
    logger.info("Building KNN index: %d total pairs", len(all_pairs))

    # Embed all sentences
    embeddings_list = []
    import numpy as np
    for i in range(0, len(sentences), 64):
        batch = sentences[i:i + 64]
        for text in batch:
            vec = embedding_fn(text)
            if vec is not None:
                embeddings_list.append(np.asarray(vec, dtype="float32").reshape(-1))
            else:
                embeddings_list.append(np.zeros(512, dtype="float32"))

    embeddings = np.stack(embeddings_list, axis=0).astype("float32")
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-9, norms)
    embeddings = embeddings / norms

    # Build FAISS index
    import faiss
    dim = embeddings.shape[1]
    faiss_idx = faiss.IndexFlatIP(dim)
    faiss_idx.add(embeddings)
    logger.info("FAISS index built: %d vectors, dim=%d", len(sentences), dim)

    generator._sentences = sentences
    generator._abstracts = abstracts
    generator._embeddings = embeddings
    generator._faiss_index = faiss_idx
    generator._loaded = True

    if generator.index_path:
        generator.save(generator.index_path)

    logger.info("KNN generator built: %d pairs", len(sentences))
    return generator
