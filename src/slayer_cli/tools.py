from __future__ import annotations

import hashlib
import os
import shutil
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .paths import LOCAL_BIN_DIR
from .process import CommandResult, run_command


YTDLP_STABLE_EXE_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
YTDLP_STABLE_SHA256_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/SHA2-256SUMS"


@dataclass(frozen=True)
class ToolInfo:
    name: str
    path: Path | None
    version: str | None
    ok: bool
    detail: str


def _candidate_from_env(name: str) -> Path | None:
    value = os.environ.get(name)
    if not value:
        return None
    path = Path(value)
    return path if path.exists() else None


def find_executable(name: str, *, env_var: str | None = None, extra_candidates: list[Path] | None = None) -> Path | None:
    if env_var:
        env_candidate = _candidate_from_env(env_var)
        if env_candidate:
            return env_candidate

    candidates = extra_candidates or []
    for candidate in candidates:
        if candidate.exists():
            return candidate

    found = shutil.which(name)
    return Path(found) if found else None


def version_for(path: Path, *args: str) -> str | None:
    result = run_command([path, *args], timeout=30)
    output = result.stdout or result.stderr
    return output.splitlines()[0].strip() if output else None


def find_mullvad() -> ToolInfo:
    candidates = [
        Path(r"C:\Program Files\Mullvad VPN\resources\mullvad.exe"),
        Path(r"C:\Program Files\Mullvad VPN\mullvad.exe"),
        Path(r"C:\Program Files (x86)\Mullvad VPN\resources\mullvad.exe"),
    ]
    path = find_executable("mullvad", env_var="MULLVAD_CLI", extra_candidates=candidates)
    if not path:
        return ToolInfo("mullvad", None, None, False, "Mullvad CLI not found")
    version = version_for(path, "--version")
    return ToolInfo("mullvad", path, version, True, "Mullvad CLI found")


def find_ytdlp() -> ToolInfo:
    candidates = [LOCAL_BIN_DIR / "yt-dlp.exe"]
    path = find_executable("yt-dlp", env_var="YTDLP_CLI", extra_candidates=candidates)
    if not path:
        return ToolInfo("yt-dlp", None, None, False, "yt-dlp not found")
    version = version_for(path, "--version")
    return ToolInfo("yt-dlp", path, version, True, "yt-dlp found")


def find_ffmpeg() -> ToolInfo:
    path = find_executable("ffmpeg", env_var="FFMPEG_CLI")
    if not path:
        return ToolInfo("ffmpeg", None, None, False, "ffmpeg not found")
    version = version_for(path, "-version")
    return ToolInfo("ffmpeg", path, version, True, "ffmpeg found")


def find_js_runtime() -> ToolInfo:
    for runtime, env_var in [("deno", "DENO_CLI"), ("node", "NODE_CLI")]:
        path = find_executable(runtime, env_var=env_var)
        if path:
            version = version_for(path, "--version")
            return ToolInfo("yt-dlp JS runtime", path, version, True, runtime)
    return ToolInfo("yt-dlp JS runtime", None, None, False, "deno or node not found")


def download_file(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    with urllib.request.urlopen(url, timeout=120) as response:
        tmp.write_bytes(response.read())
    tmp.replace(target)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_sha256_from_sums(sums_text: str, filename: str) -> str | None:
    for raw_line in sums_text.splitlines():
        parts = raw_line.strip().split()
        if len(parts) < 2:
            continue
        digest, listed = parts[0], parts[-1].lstrip("*")
        if listed == filename:
            return digest.lower()
    return None


def install_ytdlp() -> tuple[Path, str, str | None]:
    target = LOCAL_BIN_DIR / "yt-dlp.exe"
    sums_target = LOCAL_BIN_DIR / "SHA2-256SUMS"
    download_file(YTDLP_STABLE_EXE_URL, target)
    download_file(YTDLP_STABLE_SHA256_URL, sums_target)

    actual = sha256_file(target)
    expected = expected_sha256_from_sums(sums_target.read_text(encoding="utf-8"), "yt-dlp.exe")
    if expected and expected != actual:
        target.unlink(missing_ok=True)
        raise RuntimeError(f"yt-dlp.exe SHA256 mismatch: expected {expected}, got {actual}")
    return target, actual, expected


def run_tool(path: Path, *args: str, timeout: int = 60) -> CommandResult:
    return run_command([path, *args], timeout=timeout)
