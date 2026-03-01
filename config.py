"""
config.py
~~~~~~~~~
Centralised, environment-driven configuration for Offline Semantic File Search.

All settings are read from environment variables with safe defaults so
the application runs out-of-the-box on any OS without extra setup.

Environment variables
---------------------
MODE        "local" | "cloud"   (default: "local")
PORT        int                  (default: 8000)
INDEX_DIR   file system path    (default: ./data/index)
DATA_DIR    file system path    (default: ./data)
LOG_LEVEL   "DEBUG"|"INFO"|…    (default: "INFO")

Usage
-----
    from config import settings

    print(settings.MODE)       # "local" or "cloud"
    print(settings.PORT)       # 8000
    print(settings.INDEX_DIR)  # Path("./data/index")
"""
from __future__ import annotations

import logging
import os
from pathlib import Path


class Settings:
    """
    Read-once configuration loaded from environment variables.
    Immutable after construction.
    """

    MODE: str
    PORT: int
    INDEX_DIR: Path
    DATA_DIR: Path
    LOG_LEVEL: str

    def __init__(self) -> None:
        raw_mode = os.getenv("MODE", "local").strip().lower()
        if raw_mode not in {"local", "cloud"}:
            raise ValueError(
                f"Invalid MODE='{raw_mode}'. Must be 'local' or 'cloud'."
            )
        self.MODE = raw_mode

        try:
            self.PORT = int(os.getenv("PORT", "8000"))
        except ValueError:
            raise ValueError("PORT must be an integer (e.g. PORT=8000).")

        self.DATA_DIR = Path(os.getenv("DATA_DIR", "data")).resolve()
        self.INDEX_DIR = Path(os.getenv("INDEX_DIR", str(self.DATA_DIR / "index"))).resolve()

        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def is_local(self) -> bool:
        return self.MODE == "local"

    @property
    def is_cloud(self) -> bool:
        return self.MODE == "cloud"

    def configure_logging(self) -> None:
        """Apply log level to the root logger (call once at startup)."""
        logging.basicConfig(
            level=self.LOG_LEVEL,
            format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def __repr__(self) -> str:
        return (
            f"Settings(MODE={self.MODE!r}, PORT={self.PORT}, "
            f"INDEX_DIR={self.INDEX_DIR}, DATA_DIR={self.DATA_DIR}, "
            f"LOG_LEVEL={self.LOG_LEVEL!r})"
        )


# Singleton instance used everywhere
settings = Settings()
