"""
main.py
~~~~~~~
Unified entry point for Offline Semantic File Search.

USAGE
-----
Local Desktop Mode (UI on localhost:3000, API on :8000):
    python main.py serve

Cloud / Server Mode (API-only on :8000):
    python main.py api
    uvicorn api:app --host 0.0.0.0 --port 8000

CLI operations (both modes):
    python main.py index  <path>          — index a directory
    python main.py search <query> [--top N]  — run a semantic query
    python main.py stats                  — print index stats
"""
from __future__ import annotations

import argparse
import os
import sys

from config import settings

settings.configure_logging()

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_uvicorn() -> None:
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        logger.error(
            "uvicorn is not installed. Run:  pip install uvicorn"
        )
        sys.exit(1)


def cmd_serve(args: argparse.Namespace) -> None:  # noqa: ARG001
    """LOCAL MODE — starts the FastAPI backend and prints UI instructions."""
    os.environ.setdefault("MODE", "local")
    _require_uvicorn()
    import uvicorn

    port = settings.PORT
    print(
        f"\n{'=' * 60}\n"
        f"  Offline Semantic File Search — LOCAL MODE\n"
        f"{'=' * 60}\n"
        f"  Backend API : http://localhost:{port}\n"
        f"  Health check: http://localhost:{port}/health\n"
        f"\n"
        f"  To start the Web UI (in a separate terminal):\n"
        f"    npm install   (first time only)\n"
        f"    npm run dev   (starts UI on http://localhost:3000)\n"
        f"{'=' * 60}\n"
    )
    uvicorn.run(
        "api:app",
        host="127.0.0.1",  # local only — not exposed to network
        port=port,
        reload=False,
        log_level=settings.LOG_LEVEL.lower(),
    )


def cmd_api(args: argparse.Namespace) -> None:  # noqa: ARG001
    """CLOUD MODE — starts the FastAPI backend exposed on all interfaces."""
    os.environ.setdefault("MODE", "cloud")
    _require_uvicorn()
    import uvicorn

    port = settings.PORT
    print(
        f"\n{'=' * 60}\n"
        f"  Offline Semantic File Search — CLOUD / API MODE\n"
        f"{'=' * 60}\n"
        f"  API listening on http://0.0.0.0:{port}\n"
        f"  Health check:  http://0.0.0.0:{port}/health\n"
        f"  Docs (Swagger): http://0.0.0.0:{port}/docs\n"
        f"{'=' * 60}\n"
    )
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level=settings.LOG_LEVEL.lower(),
    )


def cmd_index(args: argparse.Namespace) -> None:
    """CLI — index a local directory."""
    from pathlib import Path
    from core.semantic_search import SemanticSearch

    try:
        target = Path(args.path).resolve(strict=True)
    except FileNotFoundError:
        logger.error("Path does not exist: '%s'", args.path)
        sys.exit(1)

    if not target.is_dir():
        logger.error("'%s' is not a directory.", target)
        sys.exit(1)

    engine = SemanticSearch()
    summary = engine.index_directory(target)
    print(
        f"\n[+] Indexing complete.\n"
        f"    Files indexed : {summary['files_indexed']}\n"
        f"    Total chunks  : {summary['total_chunks']}\n"
        f"    Index dir     : {settings.INDEX_DIR}\n"
    )


def cmd_search(args: argparse.Namespace) -> None:
    """CLI — run a semantic search query."""
    from core.semantic_search import SemanticSearch

    engine = SemanticSearch()
    results = engine.search(args.query, top_k=args.top)

    if not results:
        print("\n[!] No results found. Is the index populated? Run: python main.py index <path>")
        return

    print(f"\n[*] Top {len(results)} semantic results for: '{args.query}'")
    print("-" * 70)
    for res in results:
        snippet = res["text"].replace("\n", " ").strip()[:120]
        print(f"  Score : {res['score']:.4f}")
        print(f"  File  : {res['file_path']}")
        print(f"  Chunk : {snippet}…")
        print("-" * 70)


def cmd_stats(args: argparse.Namespace) -> None:  # noqa: ARG001
    """CLI — show index statistics."""
    from core.semantic_search import SemanticSearch

    engine = SemanticSearch()
    print(
        f"\n[*] Index Statistics\n"
        f"    Total chunks : {engine.total_chunks}\n"
        f"    Disk usage   : {engine.index_size_mb:.2f} MB\n"
        f"    Index dir    : {settings.INDEX_DIR}\n"
    )


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="Offline Semantic File Search — cross-platform, CPU-only.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py serve                  # local desktop mode\n"
            "  python main.py api                    # cloud / EC2 / Docker mode\n"
            "  python main.py index /path/to/docs    # index a directory\n"
            "  python main.py search \"AI reports\"    # search the index\n"
            "  python main.py stats                  # show index stats\n"
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # serve
    sub.add_parser("serve", help="Start local mode (API on :8000 + UI instructions)")

    # api
    sub.add_parser("api", help="Start cloud/server mode (API on :8000, no UI)")

    # index
    idx = sub.add_parser("index", help="Index a directory for semantic search")
    idx.add_argument("path", help="Absolute or relative path to the directory to index")

    # search
    srch = sub.add_parser("search", help="Search the index with a natural-language query")
    srch.add_argument("query", help="Search query string")
    srch.add_argument("--top", type=int, default=5, metavar="N", help="Number of results (default: 5)")

    # stats
    sub.add_parser("stats", help="Display index statistics")

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "serve": cmd_serve,
        "api": cmd_api,
        "index": cmd_index,
        "search": cmd_search,
        "stats": cmd_stats,
    }

    if args.command in dispatch:
        dispatch[args.command](args)
    else:
        parser.print_help()
        sys.exit(0)