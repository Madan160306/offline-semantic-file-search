"""
api.py
~~~~~~
FastAPI application for Offline Semantic File Search.

Works in both modes:
  • Local mode  → launched by ``python main.py serve``  (port 8000 + React UI on 3000)
  • Cloud mode  → launched by ``python main.py api`` or ``uvicorn api:app`` on EC2/Docker

Endpoints
---------
GET  /health   → liveness probe
POST /search   → semantic search
POST /reindex  → index a server-side directory
GET  /stats    → index statistics (backwards-compat alias)
POST /index    → backwards-compat alias for /reindex
"""
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from config import settings
from core.semantic_search import SemanticSearch

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
settings.configure_logging()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application-level search engine (initialised in lifespan)
# ---------------------------------------------------------------------------
_engine: Optional[SemanticSearch] = None


def get_resource_path(relative_path: str) -> Path:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(".").resolve()
    return base_path / relative_path


def get_engine() -> SemanticSearch:
    """Return the global SemanticSearch instance, raising if not ready."""
    if _engine is None:
        raise RuntimeError("Search engine not initialised. Check startup logs.")
    return _engine


# ---------------------------------------------------------------------------
# Lifespan: load index on startup, nothing to do on shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _engine
    logger.info("Starting Offline Semantic File Search API (mode=%s).", settings.MODE)
    settings.INDEX_DIR.mkdir(parents=True, exist_ok=True)
    _engine = SemanticSearch()
    logger.info(
        "Index loaded. chunks=%d  size=%.2f MB",
        _engine.total_chunks,
        _engine.index_size_mb,
    )
    yield
    logger.info("Shutting down API.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Offline Semantic File Search",
    description=(
        "CPU-only, fully-offline semantic search over local files.\n\n"
        f"Running in **{settings.MODE.upper()} mode** on port `{settings.PORT}`."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — permissive in local mode, locked down in cloud
_cors_origins = ["*"] if settings.is_local else (
    [f"http://localhost:{settings.PORT}"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# NOTE: Static file serving (SPA catch-all) is registered AFTER all API
# endpoints at the bottom of this file so that specific routes like
# /health, /search, /stats, etc. always take precedence.

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural-language search query.")
    top_k: int = Field(5, ge=1, le=50, description="Maximum number of results.")


class IndexRequest(BaseModel):
    path: str = Field(..., description="Absolute path to the directory to index.")


class SearchResultItem(BaseModel):
    file_path: str
    text: str
    score: float
    start_idx: int
    file_size_bytes: int


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]


class BrowseResponse(BaseModel):
    dirs: List[str]
    files: List[str]


class IndexResponse(BaseModel):
    message: str
    files_indexed: int
    total_chunks: int


class HealthResponse(BaseModel):
    status: str
    mode: str
    indexed_chunks: int
    index_size_mb: float


class StatsResponse(BaseModel):
    total_chunks: int
    index_size_mb: float




# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health() -> HealthResponse:
    """Liveness probe — returns 200 with index stats."""
    engine = get_engine()
    return HealthResponse(
        status="ok",
        mode=settings.MODE,
        indexed_chunks=engine.total_chunks,
        index_size_mb=round(engine.index_size_mb, 2),
    )


@app.post("/search", response_model=SearchResponse, tags=["Search"])
async def search(request: SearchRequest) -> SearchResponse:
    """Perform semantic search over the current index."""
    engine = get_engine()
    try:
        results = engine.search(request.query, top_k=request.top_k)
    except Exception as exc:
        logger.error("Search failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search error: {exc}") from exc

    return SearchResponse(
        query=request.query,
        results=[SearchResultItem(**r) for r in results],
    )


@app.get("/browse", response_model=BrowseResponse, tags=["Search"])
async def browse(path: str) -> BrowseResponse:
    """List subdirectories and files in a given path (non-recursive)."""
    target = Path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")

    try:
        dirs = []
        files = []
        for item in target.iterdir():
            try:
                if item.is_dir():
                    dirs.append(item.name)
                else:
                    files.append(item.name)
            except (PermissionError, OSError):
                continue
        return BrowseResponse(dirs=sorted(dirs), files=sorted(files))
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied: {path}")
    except Exception as exc:
        logger.error("Browse failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Browse error: {exc}")


@app.post("/open-folder", tags=["System"])
async def open_folder(request: IndexRequest):
    """Open a directory in the local OS file explorer (Local Mode only)."""
    if not settings.is_local:
        raise HTTPException(status_code=403, detail="Open folder is only available in Local Mode.")

    target = Path(request.path)
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail=f"Directory not found: {request.path}")

    try:
        import subprocess
        if sys.platform == "win32":
            os.startfile(target)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
        return {"message": f"Opened: {request.path}"}
    except Exception as exc:
        logger.error("Failed to open folder: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to open folder: {exc}")


@app.post("/reindex", response_model=IndexResponse, tags=["Indexing"])
async def reindex(request: IndexRequest) -> IndexResponse:
    """Index a directory on the server filesystem."""
    engine = get_engine()
    target = Path(request.path)
    if not target.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Path does not exist: {request.path}",
        )
    if not target.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Path is not a directory: {request.path}",
        )
    if settings.is_cloud:
        # In cloud mode, restrict to DATA_DIR sub-paths for safety
        try:
            target.resolve().relative_to(settings.DATA_DIR)
        except ValueError:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Cloud mode only allows indexing paths inside DATA_DIR "
                    f"({settings.DATA_DIR}). Set DATA_DIR env var to expand this."
                ),
            )
    try:
        summary = engine.index_directory(target)
    except Exception as exc:
        logger.error("Indexing failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Indexing error: {exc}") from exc

    return IndexResponse(
        message="Indexing complete.",
        files_indexed=summary["files_indexed"],
        total_chunks=summary["total_chunks"],
    )


# ---------------------------------------------------------------------------
# Backwards-compatibility aliases
# ---------------------------------------------------------------------------

@app.get("/stats", response_model=StatsResponse, tags=["System"])
async def get_stats() -> StatsResponse:
    """Backwards-compatible stats endpoint (original API contract)."""
    engine = get_engine()
    return StatsResponse(
        total_chunks=engine.total_chunks,
        index_size_mb=round(engine.index_size_mb, 2),
    )


@app.post("/index", response_model=IndexResponse, tags=["Indexing"])
async def index_directory(request: IndexRequest) -> IndexResponse:
    """Backwards-compatible alias for POST /reindex."""
    return await reindex(request)



# ---------------------------------------------------------------------------
# Static file serving — MUST be registered last so API routes take precedence
# ---------------------------------------------------------------------------

dist_path = get_resource_path("dist")
if dist_path.exists() and dist_path.is_dir():
    logger.info("Serving static files from: %s", dist_path)
    # Mount /assets explicitly so asset requests resolve before the catch-all
    app.mount("/assets", StaticFiles(directory=dist_path / "assets"), name="assets")

    @app.get("/{path_name:path}")
    async def serve_spa(path_name: str):
        """Serve the React SPA for all non-API routes."""
        local_file = dist_path / path_name
        if local_file.exists() and local_file.is_file():
            return FileResponse(local_file)
        return FileResponse(dist_path / "index.html")
else:
    logger.warning("Dist folder not found at %s. Static files will not be served.", dist_path)
