from __future__ import annotations

import os
import re
import sys
from pathlib import Path


_CANDIDATE_REPO_ROOT = Path(__file__).resolve().parents[2]
IS_REPO_CHECKOUT = (_CANDIDATE_REPO_ROOT / ".legends-module").is_file()

MAX_ENV_BYTES = 64 * 1024
MAX_TEXT_FILE_BYTES = 25 * 1024 * 1024

_URL_SCHEME_RE = re.compile(r"^[a-zA-Z]{2,}[a-zA-Z0-9+.-]*:")
_MACOS_SYSTEM_SYMLINKS = {Path("/var"), Path("/tmp"), Path("/etc")}


def resolve_workspace_root() -> Path:
    env_workspace = os.environ.get("LEGENDS_YTDLP_WORKSPACE", "").strip()
    if env_workspace:
        return Path(env_workspace).expanduser().resolve()
    if IS_REPO_CHECKOUT:
        return _CANDIDATE_REPO_ROOT
    return Path.cwd().resolve()


def resolve_local_dir() -> Path:
    env_home = os.environ.get("LEGENDS_YTDLP_HOME", "").strip()
    if env_home:
        return Path(env_home).expanduser().resolve()
    if IS_REPO_CHECKOUT:
        return _CANDIDATE_REPO_ROOT / ".local"
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
        base = Path(local_app_data) if local_app_data else (Path.home() / "AppData" / "Local")
        return base / "LegendsYtDlp"
    xdg_data = os.environ.get("XDG_DATA_HOME", "").strip()
    base = Path(xdg_data) if xdg_data else (Path.home() / ".local" / "share")
    return base / "legends-yt-dlp"


PROJECT_ROOT = resolve_workspace_root()
LOCAL_DIR = resolve_local_dir()
LOCAL_BIN_DIR = LOCAL_DIR / "bin"
DOWNLOADS_DIR = PROJECT_ROOT / "downloads"
REPORTS_DIR = PROJECT_ROOT / "reports"


def assert_not_symlink(path: Path) -> None:
    if path.is_symlink():
        raise ValueError(f"Refusing symlink path: {path}")
    abs_path = Path(os.path.abspath(str(path)))
    for parent in abs_path.parents:
        if parent.is_symlink():
            if sys.platform == "darwin" and parent in _MACOS_SYSTEM_SYMLINKS:
                continue
            raise ValueError(f"Refusing symlink parent directory: {parent}")


def read_safe_text(path: Path, *, max_bytes: int = MAX_TEXT_FILE_BYTES) -> str:
    assert_not_symlink(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise ValueError(f"Path is not a regular file: {path}")
    size = path.stat().st_size
    if size > max_bytes:
        raise ValueError(f"File exceeds maximum allowed size ({max_bytes} bytes): {path}")
    return path.read_text(encoding="utf-8")


def write_safe_text(path: Path, content: str) -> None:
    assert_not_symlink(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    assert_not_symlink(path.parent)
    path.write_text(content, encoding="utf-8")


def validate_local_media_file(path: Path) -> Path:
    raw = str(path).strip()
    if not raw or any(ch in raw for ch in ("\r", "\n", "\0")):
        raise ValueError(f"Invalid media path: {path!r}")
    if raw.startswith("-") or path.name.startswith("-"):
        raise ValueError(f"Refusing option-like media path: {path}")
    if raw.startswith("\\\\") or raw.startswith("//"):
        raise ValueError(f"Refusing UNC media path: {path}")
    if _URL_SCHEME_RE.match(raw):
        raise ValueError(f"Refusing remote or protocol media URI: {path}")
    assert_not_symlink(path)
    if not path.exists():
        raise FileNotFoundError(f"media file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Media path is not a regular file: {path}")
    return path


