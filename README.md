---
title: Offline Semantic File Search
emoji: 🔍
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# Offline Semantic File Search

AI-powered, fully offline semantic search over your local files.  
No cloud APIs. No telemetry. CPU-only. Works on Windows, Linux, macOS, and Docker.

---

## Mode Overview

| Feature | **Local Mode** | **Cloud / API Mode** |
|---|---|---|
| Command | `python main.py serve` | `python main.py api` |
| API port | `:8000` | `:8000` |
| Web UI | `localhost:3000` (React) | None |
| Bind host | `127.0.0.1` (local only) | `0.0.0.0` (all interfaces) |
| Docker | ✗ | ✅ Recommended |
| AWS EC2 | ✗ | ✅ |
| Path access | User's local filesystem | Server-side paths only |

---

## OS Compatibility

| OS | Local Mode | Cloud Mode | Docker |
|---|---|---|---|
| Windows 10/11 | ✅ | ✅ | via Docker Desktop |
| Ubuntu / Debian | ✅ | ✅ | ✅ |
| macOS 12+ | ✅ | ✅ | ✅ |
| AWS EC2 (Amazon Linux / Ubuntu) | — | ✅ | ✅ |

---

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** *(Local Mode UI only)*

Install Python dependencies:

```bash
pip install -r requirements.txt
```

---

## Local Desktop Mode (Windows / macOS / Linux)

### 1 — Start the backend

```bash
# Windows PowerShell
python main.py serve

# macOS / Linux
python main.py serve
```

The API starts on `http://localhost:8000`.

### 2 — Start the Web UI

In a second terminal:

```bash
npm install        # first time only
npm run dev        # starts UI on http://localhost:3000
```

Open <http://localhost:3000> in your browser.

### 3 — Index a directory

In the UI, enter the **absolute path** to any directory:

| OS | Example |
|---|---|
| Windows | `C:\Users\Name\Documents` |
| macOS | `/Users/name/documents` |
| Linux | `/home/name/documents` |

Or from the CLI:

```bash
python main.py index "/path/to/your/documents"
```

### 4 — Search

Type any natural-language query in the search bar, for example:

> `financial reports about machine learning`

Or from CLI:

```bash
python main.py search "machine learning reports"
```

---

## Cloud / AWS EC2 Mode

### EC2 setup

```bash
# 1. SSH into your instance
ssh -i key.pem ubuntu@<EC2-PUBLIC-IP>

# 2. Install Python 3.10+
sudo apt update && sudo apt install -y python3 python3-pip

# 3. Clone / upload the project
git clone <repo-url> && cd offline-semantic-file-search

# 4. Install dependencies
pip3 install -r requirements.txt

# 5. Start in cloud mode
MODE=cloud DATA_DIR=/srv/search/data python main.py api
```

> **Important:** Open port **8000** in your EC2 Security Group (inbound TCP).  
> Access the API at `http://<EC2-PUBLIC-IP>:8000`  
> **Do NOT use `localhost`** from your laptop — use the actual EC2 public IP.

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `MODE` | `local` | `local` or `cloud` |
| `PORT` | `8000` | FastAPI listen port |
| `DATA_DIR` | `./data` | Root data directory |
| `INDEX_DIR` | `./data/index` | FAISS index location |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Docker

### Build

```bash
docker build -t semantic-search .
```

### Run

```bash
docker run -d \
  --name semantic-search \
  -p 8000:8000 \
  -v /path/to/your/data:/app/data \
  -e DATA_DIR=/app/data \
  -e INDEX_DIR=/app/data/index \
  semantic-search
```

### Health check

```bash
curl http://localhost:8000/health
# {"status":"ok","mode":"cloud","indexed_chunks":1234,"index_size_mb":2.5}
```

### Index data using API

```bash
# The directory must exist inside the mounted /app/data volume
curl -X POST http://localhost:8000/reindex \
  -H "Content-Type: application/json" \
  -d '{"path": "/app/data/documents"}'
```

---

## REST API Reference

### `GET /health`

```bash
curl http://localhost:8000/health
```

```json
{"status": "ok", "mode": "local", "indexed_chunks": 512, "index_size_mb": 1.23}
```

### `POST /search`

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "reports about machine learning", "top_k": 5}'
```

```json
{
  "query": "reports about machine learning",
  "results": [
    {
      "file_path": "/home/user/docs/report.pdf",
      "text": "…relevant excerpt…",
      "score": 0.921,
      "start_idx": 0
    }
  ]
}
```

### `POST /reindex`

```bash
curl -X POST http://localhost:8000/reindex \
  -H "Content-Type: application/json" \
  -d '{"path": "/home/user/documents"}'
```

```json
{"message": "Indexing complete.", "files_indexed": 42, "total_chunks": 386}
```

### `GET /browse`

```bash
curl "http://localhost:8000/browse?path=/home/user/docs"
```

```json
{
  "dirs": ["work", "personal"],
  "files": ["report.pdf", "notes.txt"]
}
```
```

### `GET /stats` *(backwards-compat)*

```bash
curl http://localhost:8000/stats
```

### `POST /index` *(backwards-compat alias for /reindex)*

---

## CLI Reference

```
python main.py serve                     # Local mode — API on :8000
python main.py api                       # Cloud mode — API on :8000 (all interfaces)
python main.py index /path/to/dir        # Index a directory
python main.py search "your query"       # Run a search
python main.py search "query" --top 10   # Get top-10 results
python main.py stats                     # Print index stats
```

---

## Supported File Types

| Category | Extensions |
|---|---|
| **Text** | `.txt`, `.md`, `.pdf`, `.docx`, `.py`, `.js`, `.ts`, `.csv`, `.json`, `.xml`, `.html` |
| **Media** | `.mp4`, `.mkv`, `.avi`, `.mov`, `.mp3`, `.flac`, `.wav`, `.jpg`, `.png`, `.webp` |
| **Apps** | `.exe`, `.msi`, `.apk`, `.dmg` |

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Using `localhost:8000` from another machine | Use the server's actual IP or hostname |
| `API Offline` shown in the UI | Make sure `python main.py serve` is running first |
| `Path does not exist` on /reindex in cloud mode | The path must exist on the **server**, not your laptop |
| `Invalid directory path` | Use absolute paths, not relative |
| Cloud mode won't index outside DATA_DIR | Set `DATA_DIR` env var to the parent of the target directory |
| Port conflict | Change with `PORT=9000 python main.py serve` |

---

## Project Structure

```
├── core/                  # Shared engine (pathlib, CPU-only)
│   ├── document_loader.py # File scanning + text extraction
│   ├── chunker.py         # Text chunking
│   ├── embedder.py        # Sentence-Transformers singleton
│   ├── index_manager.py   # FAISS index persistence
│   └── semantic_search.py # Unified search/index facade
├── src/                   # React + TypeScript frontend
│   ├── components/
│   │   └── Dashboard.tsx  # Main UI
│   └── services/
│       └── apiService.ts  # HTTP client (dynamic base URL)
├── api.py                 # FastAPI application
├── main.py                # CLI entry point (serve / api / index / search / stats)
├── config.py              # Environment-driven configuration
├── Dockerfile             # Cloud-mode Docker image
├── .dockerignore
└── requirements.txt
```

---

## Model Information

Embedding model: **`all-MiniLM-L6-v2`** from `sentence-transformers`  
- Dimension: 384  
- Device: CPU (no GPU required)  
- Downloaded automatically on first run (~90 MB)  
- Stored in `~/.cache/huggingface` (or `%USERPROFILE%\.cache\huggingface` on Windows)
