# PRD: Offline Semantic File Search — Improvements

## Overview
This is an AI-powered, fully offline semantic file search application.
- **Backend**: Python + FastAPI, FAISS vector index, Sentence-Transformers (`all-MiniLM-L6-v2`)
- **Frontend**: React + TypeScript + Vite, running on `localhost:3000`
- **Backend API**: FastAPI on `localhost:8000`

The agent should read tasks below, cross-reference `progress.txt` to see what is already done,
and complete exactly ONE incomplete task per iteration. Append progress to `progress.txt` — never
delete or modify it.

---

## Task 1: Improve Search Result Display — Open File Location
Add an "Open folder" or "Copy path" button to each search result card in `src/components/Dashboard.tsx`.
Users should be able to click a button on a result to copy the full file path to clipboard.
The button should appear on hover of the result row.

## Task 2: Add Result Count Summary
After a search, show a brief summary line above the results like:
`Found 12 results across 4 categories for "invoice"`.
This should be rendered between the search bar and the tab filters in `Dashboard.tsx`.

## Task 3: Improve Empty State UI
When the user has never searched and the API is connected, show a helpful "Getting Started" card
with 3 steps: (1) Index a directory, (2) Type a query, (3) Browse results.
Replace the blank area below the search bar. Implement in `Dashboard.tsx`.

## Task 4: Add Keyboard Shortcut for Search Focus
Pressing `/` anywhere on the page (when not typing in an input) should focus the search input.
Pressing `Escape` should blur/clear the search input. Implement in `Dashboard.tsx` using a
`useEffect` with a `keydown` listener.

## Task 5: Add Supported File Types to the Index Directory Panel
In the "Index a Directory" section of `Dashboard.tsx`, add a small info row below the path input
that lists the supported file types (`.txt`, `.md`, `.pdf`, `.docx`, and media files by name).
This helps users know what will be indexed.

## Task 6: Backend — Return File Size in Search Results
Modify `api.py` and `core/semantic_search.py` to include the file size in bytes for each search result.
Add `file_size_bytes: int` to the search result schema. Use `os.path.getsize()` to get the value.
Update the `SearchResult` type in `src/services/apiService.ts` to include `file_size_bytes?: number`.
Display the file size (human-readable, e.g., "2.3 MB") in the search result card in `Dashboard.tsx`.

## Task 7: Backend — Add /browse Endpoint
Add a `GET /browse?path=<dir>` endpoint to `api.py` that returns a JSON list of
subdirectory names inside the given path (non-recursive, one level only). This will later
be used for a directory browser UI. Return `{ "dirs": [...], "files": [...] }`.
Include basic error handling (path not found, not a directory, permission denied).

## Task 8: Frontend — Dark/Light Mode Toggle
Add a theme toggle button to the header in `Dashboard.tsx`. It should switch between
dark and light mode by toggling a `dark` class on the `<html>` element and persist
the preference to `localStorage`. Use a sun/moon icon from `lucide-react`.
