/**
 * apiService.ts
 *
 * HTTP client for the FastAPI backend.
 * Base URL priority:
 *   1. VITE_API_URL env var (build-time)
 *   2. Runtime window.location origin (same-host deployment)
 *   3. Fallback: http://localhost:8000
 */

const resolveApiBase = (): string => {
  const envUrl = import.meta.env.VITE_API_URL as string | undefined;
  if (envUrl && envUrl.trim()) return envUrl.trim().replace(/\/$/, '');
  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost') {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return 'http://localhost:8000';
};

const API_BASE = resolveApiBase();

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Stats {
  total_chunks: number;
  index_size_mb: number;
}

export interface SearchResult {
  file_path: string;
  file_name?: string;
  text: string;
  score: number;
  start_idx: number;
  file_size_bytes?: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
}

export interface IndexResponse {
  message: string;
  files_indexed: number;
  total_chunks: number;
}

export interface HealthResponse {
  status: string;
  mode: string;
  indexed_chunks: number;
  index_size_mb: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? body.message ?? detail;
    } catch (_) { /* ignore */ }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// File type helpers (client-side)
// ---------------------------------------------------------------------------

const VIDEO_EXT = new Set(['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.m4v', '.webm', '.3gp']);
const AUDIO_EXT = new Set(['.mp3', '.flac', '.wav', '.aac', '.ogg', '.m4a', '.wma', '.opus']);
const IMAGE_EXT = new Set(['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.svg', '.ico']);
const DOC_EXT = new Set(['.pdf', '.docx', '.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm']);
const APP_EXT = new Set(['.exe', '.msi', '.lnk', '.apk', '.dmg']);

export type FileCategory = 'video' | 'audio' | 'image' | 'document' | 'app' | 'code' | 'other';

export function getFileCategory(filePath: string): FileCategory {
  const ext = filePath.slice(filePath.lastIndexOf('.')).toLowerCase();
  if (VIDEO_EXT.has(ext)) return 'video';
  if (AUDIO_EXT.has(ext)) return 'audio';
  if (IMAGE_EXT.has(ext)) return 'image';
  if (DOC_EXT.has(ext)) return 'document';
  if (APP_EXT.has(ext)) return 'app';
  if (['.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs', '.java', '.cpp', '.c', '.cs'].includes(ext)) return 'code';
  return 'other';
}

// ---------------------------------------------------------------------------
// API surface
// ---------------------------------------------------------------------------

export const apiService = {
  async getHealth(): Promise<HealthResponse | null> {
    try {
      const res = await fetch(`${API_BASE}/health`);
      return handleResponse<HealthResponse>(res);
    } catch {
      return null;
    }
  },

  async getStats(): Promise<Stats> {
    const res = await fetch(`${API_BASE}/stats`);
    return handleResponse<Stats>(res);
  },

  async indexDirectory(path: string): Promise<IndexResponse> {
    const res = await fetch(`${API_BASE}/reindex`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    });
    return handleResponse<IndexResponse>(res);
  },

  async search(query: string, topK: number = 10): Promise<SearchResponse> {
    const res = await fetch(`${API_BASE}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, top_k: topK }),
    });
    return handleResponse<SearchResponse>(res);
  },

  async openFolder(path: string): Promise<void> {
    await fetch(`${API_BASE}/open-folder`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    });
  },
};

export { API_BASE };
