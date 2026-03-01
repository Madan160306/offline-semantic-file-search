"""
core.chunker
~~~~~~~~~~~~
Splits extracted text into fixed-size, overlapping windows suitable
for embedding. File paths are stored as POSIX strings so that chunk
metadata is portable across operating systems.
"""
from __future__ import annotations

from pathlib import Path
from typing import List


class Chunker:
    """Split text into overlapping chunks and annotate with source metadata."""

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str, file_path: Path | str) -> List[dict]:
        """
        Split *text* into chunks and return a list of metadata dicts.

        Each dict has the keys:
          - ``text``       : the chunk body
          - ``file_path``  : POSIX-style path string (cross-platform)
          - ``start_idx``  : character offset in the original document
        """
        if isinstance(file_path, Path):
            # Store as POSIX for cross-OS JSON compatibility
            fp_str = file_path.as_posix()
        else:
            fp_str = Path(file_path).as_posix()

        text = text.strip()
        if not text:
            return []

        chunks: List[dict] = []
        step = self.chunk_size - self.overlap
        text_len = len(text)
        start = 0

        while start < text_len:
            end = start + self.chunk_size
            chunks.append(
                {
                    "text": text[start:end],
                    "file_path": fp_str,
                    "start_idx": start,
                }
            )
            if end >= text_len:
                break
            start += step

        return chunks
