import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'url';

/**
 * Vite configuration for the Offline Semantic File Search UI.
 *
 * The dev server (npm run dev) proxies all /api/* and direct backend
 * requests to the Python FastAPI server running on :8000, so the
 * browser never needs cross-origin access during development.
 *
 * VITE_API_URL can be set in `.env` or at build time to target a
 * remote backend (e.g. EC2 or Docker).
 */
export default defineConfig({
  plugins: [react()],

  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },

  server: {
    port: 3000,
    strictPort: true,
    host: true,          // accessible on LAN / WSL / Docker bridge
    allowedHosts: true,  // allow all hosts (overridden by allowedHosts in prod)

    proxy: {
      // Forward /search, /reindex, /index, /stats, /health → FastAPI
      '/search': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/reindex': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/index': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/stats': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },

    },
  },
});