"""
core.index_manager
~~~~~~~~~~~~~~~~~~
Manages FAISS flat-IP index and chunk metadata persistence.

Paths are resolved from settings so the index can be stored in any
location specified via the INDEX_DIR environment variable. The module
is fully cross-platform (pathlib only, no OS-specific strings).
"""
from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import List

import faiss
import numpy as np

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 dimensionality


class IndexManager:
    """
    Persist and query a FAISS IndexFlatIP index alongside chunk metadata.

    Parameters
    ----------
    index_dir: Path
        Directory where ``index.faiss`` and ``metadata.pkl`` are stored.
        Created automatically if it does not exist.
    dimension: int
        Embedding dimensionality. Must match the Embedder's model output.
    """

    def __init__(self, index_dir: Path, dimension: int = EMBEDDING_DIM) -> None:
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.index_dir / "index.faiss"
        self.meta_path = self.index_dir / "metadata.pkl"
        self.dimension = dimension
        self._load_or_create()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_or_create(self) -> None:
        """Load existing index from disk or create a fresh one."""
        if self.index_path.exists() and self.meta_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
                with self.meta_path.open("rb") as fh:
                    self.metadata: List[dict] = pickle.load(fh)
                logger.info(
                    "Loaded FAISS index from %s (%d chunks).",
                    self.index_path,
                    self.index.ntotal,
                )
                return
            except Exception as exc:
                logger.warning(
                    "Failed to load existing index (%s). Creating fresh index.", exc
                )
        # IndexFlatIP is appropriate for normalised embeddings (cosine similarity)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []
        logger.info("Created new FAISS index (dimension=%d).", self.dimension)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, embeddings: np.ndarray, chunks_meta: List[dict]) -> None:
        """Add *embeddings* and their corresponding *chunks_meta* to the index."""
        self.index.add(embeddings.astype("float32"))
        self.metadata.extend(chunks_meta)

    def save(self) -> None:
        """Persist index and metadata to disk atomically."""
        tmp_index = self.index_path.with_suffix(".faiss.tmp")
        tmp_meta = self.meta_path.with_suffix(".pkl.tmp")
        try:
            faiss.write_index(self.index, str(tmp_index))
            with tmp_meta.open("wb") as fh:
                pickle.dump(self.metadata, fh, protocol=pickle.HIGHEST_PROTOCOL)
            tmp_index.replace(self.index_path)
            tmp_meta.replace(self.meta_path)
            logger.info(
                "Saved FAISS index to %s (%d chunks).", self.index_path, self.index.ntotal
            )
        except Exception as exc:
            # Clean up temp files on failure
            tmp_index.unlink(missing_ok=True)
            tmp_meta.unlink(missing_ok=True)
            raise RuntimeError(f"Failed to save index: {exc}") from exc

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[dict]:
        """
        Perform inner-product (cosine) search and return annotated results.

        Each result dict contains all chunk metadata plus a ``score`` field
        (higher is more similar for normalised embeddings).
        """
        if self.index.ntotal == 0:
            return []
        scores, indices = self.index.search(query_vector, top_k)
        results: List[dict] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1 and idx < len(self.metadata):
                result = self.metadata[idx].copy()
                result["score"] = float(score)
                results.append(result)
        return results

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def total_chunks(self) -> int:
        return self.index.ntotal

    @property
    def index_size_mb(self) -> float:
        if self.index_path.exists():
            return self.index_path.stat().st_size / (1024 * 1024)
        return 0.0
