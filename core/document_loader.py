"""
core.document_loader
~~~~~~~~~~~~~~~~~~~~
Recursively scans directories for supported file types and extracts
their text content. All paths are handled via pathlib.Path so the
module is OS-independent.

Supported text formats : .txt  .md  .pdf  .docx  .py  .csv  .json  .html
Supported media formats: .mp4  .mkv  .avi  .mov  .wmv  .flv  .m4v  .webm
                         .mp3  .flac .wav  .aac  .ogg  .m4a
                         .jpg  .jpeg .png  .gif  .bmp  .webp
                         .exe  .msi  .lnk  .apk
(For binary/media files the filename stem is used as the searchable text.)
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Generator, List

logger = logging.getLogger(__name__)

# Text formats — full content is extracted
_TEXT_EXTENSIONS: frozenset[str] = frozenset({
    ".txt", ".md", ".pdf", ".docx",
    ".py", ".js", ".ts", ".csv", ".json", ".xml", ".html", ".htm",
    ".log", ".ini", ".yaml", ".yml", ".toml", ".cfg", ".rst",
})

# Binary/media formats — indexed by filename only
_MEDIA_EXTENSIONS: frozenset[str] = frozenset({
    # Video
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".m4v", ".webm", ".ts", ".3gp",
    # Audio
    ".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a", ".wma", ".opus",
    # Images
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".svg", ".ico",
    # Apps / packages
    ".exe", ".msi", ".lnk", ".apk", ".dmg",
})

SUPPORTED_EXTENSIONS: frozenset[str] = _TEXT_EXTENSIONS | _MEDIA_EXTENSIONS


def scan_directory(root: Path, extensions: frozenset[str] = SUPPORTED_EXTENSIONS) -> Generator[Path, None, None]:
    """Recursively yield file paths whose extension is in *extensions*."""
    if not root.is_dir():
        raise ValueError(f"Path is not a directory or does not exist: {root}")
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in extensions:
            yield path


def extract_text(file_path: Path) -> str:
    """
    Extract plain text from a file identified by *file_path*.

    For text-based formats, the content is parsed and returned.
    For binary/media formats (video, audio, images, apps), the filename
    stem is returned so the file is findable by its name.

    Returns an empty string if extraction fails, logging a warning.
    """
    suffix = file_path.suffix.lower()
    try:
        if suffix in {".txt", ".md", ".py", ".js", ".ts", ".log",
                      ".ini", ".yaml", ".yml", ".toml", ".cfg", ".rst",
                      ".csv", ".json", ".xml"}:
            return file_path.read_text(encoding="utf-8", errors="ignore")

        if suffix in {".html", ".htm"}:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            return re.sub(r"<[^>]+>", " ", text)

        if suffix == ".pdf":
            from pypdf import PdfReader  # lazy import
            reader = PdfReader(str(file_path))
            parts: List[str] = []
            for page in reader.pages:
                content = page.extract_text()
                if content:
                    parts.append(content)
            return "\n".join(parts)

        if suffix == ".docx":
            from docx import Document  # lazy import
            doc = Document(str(file_path))
            return "\n".join(p.text for p in doc.paragraphs)

        if suffix in _MEDIA_EXTENSIONS:
            # For binary media files, index by filename so users can find
            # "Inception.mp4" by searching "Inception"
            return file_path.stem.replace(".", " ").replace("_", " ").replace("-", " ")

    except Exception as exc:
        logger.warning("Failed to extract text from %s: %s", file_path, exc)

    return ""
