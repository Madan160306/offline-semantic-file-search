"""
core.embedder
~~~~~~~~~~~~~
Singleton wrapper around sentence-transformers for CPU-only
embedding. Uses the all-MiniLM-L6-v2 model (384-dim, fast, offline).
"""
from __future__ import annotations

import logging

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"


class Embedder:
    """
    Thread-safe singleton embedder.

    Loads the model once per process and reuses it for all subsequent
    encode calls.  Device is always **CPU** to support restricted
    environments (no CUDA required).
    """

    _instance: "Embedder | None" = None
    _model: SentenceTransformer | None = None

    def __new__(cls) -> "Embedder":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            logger.info("Loading embedding model: %s (CPU)", MODEL_NAME)
            cls._instance._model = SentenceTransformer(MODEL_NAME, device="cpu")
            logger.info("Embedding model loaded successfully.")
        return cls._instance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def encode_batch(self, texts: list[str], batch_size: int = 16) -> np.ndarray:
        """Return float32 embeddings for a list of strings."""
        return self._model.encode(  # type: ignore[union-attr]
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")

    def encode_query(self, query: str) -> np.ndarray:
        """Return a float32 embedding for a single query string."""
        return self._model.encode(  # type: ignore[union-attr]
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")
