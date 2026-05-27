from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCAL_DIR = PROJECT_ROOT / ".local"
LOCAL_BIN_DIR = LOCAL_DIR / "bin"
DOWNLOADS_DIR = PROJECT_ROOT / "downloads"
REPORTS_DIR = PROJECT_ROOT / "reports"

