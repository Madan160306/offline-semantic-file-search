"""
core.semantic_search
~~~~~~~~~~~~~~~~~~~~
Unified high-level interface for indexing directories and searching.

This is the single facade that both the CLI (main.py) and the FastAPI
server (api.py) use — so both modes share identical behaviour without
duplicating logic.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from tqdm import tqdm

from config import settings
from core.chunker import Chunker
from core.document_loader import extract_text, scan_directory
from core.embedder import Embedder
from core.index_manager import IndexManager

logger = logging.getLogger(__name__)


class SemanticSearch:
    """
    Facade that wires together document loading, chunking, embedding
    and vector index management.

    Parameters
    ----------
    index_dir: Path | None
        Override the index storage directory.  Defaults to
        ``settings.INDEX_DIR`` when *None*.
    chunk_size: int
        Character window per chunk (default 500).
    overlap: int
        Overlap between consecutive chunks (default 50).
    batch_size: int
        Embedding batch size (default 16).
    """

    def __init__(
        self,
        index_dir: Path | None = None,
        chunk_size: int = 500,
        overlap: int = 50,
        batch_size: int = 16,
    ) -> None:
        resolved = Path(index_dir) if index_dir is not None else settings.INDEX_DIR
        self._index = IndexManager(index_dir=resolved)
        self._embedder = Embedder()
        self._chunker = Chunker(chunk_size=chunk_size, overlap=overlap)
        self._batch_size = batch_size

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def index_directory(self, path: Path | str) -> dict:
        """
        Scan *path* recursively, extract text, chunk and embed every
        document, then persist the updated index to disk.

        Returns
        -------
        dict
            ``{"files_indexed": int, "total_chunks": int}``
        """
        root = Path(path)
        if not root.exists():
            raise FileNotFoundError(f"Directory not found: {root}")
        if not root.is_dir():
            raise ValueError(f"Path is not a directory: {root}")

        file_paths = list(scan_directory(root))
        if not file_paths:
            logger.warning("No supported files found in %s", root)
            return {"files_indexed": 0, "total_chunks": 0}

        logger.info("Found %d files in %s. Indexing…", len(file_paths), root)
        files_indexed = 0

        for fp in tqdm(file_paths, desc="Indexing", unit="file"):
            text = extract_text(fp)
            if not text:
                continue
            chunks = self._chunker.chunk_text(text, fp)
            if not chunks:
                continue
            embeddings = self._embedder.encode_batch(
                [c["text"] for c in chunks], batch_size=self._batch_size
            )
            self._index.add(embeddings, chunks)
            files_indexed += 1

        self._index.save()
        logger.info(
            "Indexing complete. files=%d  chunks=%d",
            files_indexed,
            self._index.total_chunks,
        )
        return {
            "files_indexed": files_indexed,
            "total_chunks": self._index.total_chunks,
        }

    def search(self, query: str, top_k: int = 5) -> List[dict]:
        """
        Encode *query* and return up to *top_k* semantically similar
        chunks, deduplicated by file_path (best score per file).

        Returns
        -------
        List[dict]
            Each dict has keys: ``file_path``, ``text``, ``start_idx``,
            ``score``.
        """
        if not query.strip():
            return []

        query_vec = self._embedder.encode_query(query)
        raw = self._index.search(query_vec, top_k * 3)  # over-fetch before dedup

        # Deduplicate by file: keep highest-scoring chunk per file
        seen: dict[str, dict] = {}
        for result in raw:
            fp = result["file_path"]
            if fp not in seen or result["score"] > seen[fp]["score"]:
                # Add file size to the result
                path_obj = Path(fp)
                result["file_size_bytes"] = path_obj.stat().st_size if path_obj.exists() else 0
                seen[fp] = result

        deduped = sorted(seen.values(), key=lambda r: r["score"], reverse=True)
        return deduped[:top_k]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @property
    def total_chunks(self) -> int:
        return self._index.total_chunks

    @property
    def index_size_mb(self) -> float:
        return self._index.index_size_mb
