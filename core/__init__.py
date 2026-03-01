"""
core — Shared engine for Offline Semantic File Search.

Provides a unified interface for document loading, chunking,
embedding, index management, and semantic search. All modules work
cross-platform (Windows / Linux / macOS / Docker) using pathlib.
"""
from core.semantic_search import SemanticSearch

__all__ = ["SemanticSearch"]
