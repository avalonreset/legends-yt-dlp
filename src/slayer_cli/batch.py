from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from .doctor import Check, overall_ok, run_doctor
from .paths import PROJECT_ROOT
from .process import CommandResult, run_command
from .tools import find_ytdlp


BATCHES_DIR = PROJECT_ROOT / "batches"


@dataclass(frozen=True)
class BatchPaths:
    root: Path
    manifest: Path
    urls: Path
    config: Path
    archive: Path
    output: Path
    temp: Path


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug[:60] or "batch"


def validate_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def make_batch_paths(name: str) -> BatchPaths:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    root = BATCHES_DIR / f"{stamp}-{slugify(name)}"
    return BatchPaths(
        root=root,
        manifest=root / "manifest.json",
        urls=root / "urls.txt",
        config=root / "yt-dlp.conf",
        archive=root / "archive.txt",
        output=root / "downloads",
        temp=root / "tmp",
    )


def create_batch(*, url: str, rights_basis: str, name: str | None = None, output_dir: str | None = None) -> BatchPaths:
    if not validate_url(url):
        raise ValueError("Batch URL must be an http(s) URL")
    if not rights_basis.strip():
        raise ValueError("A rights basis is required")

    parsed = urlparse(url)
    batch_name = name or parsed.netloc
    paths = make_batch_paths(batch_name)
    paths.root.mkdir(parents=True, exist_ok=False)
    paths.output.mkdir(parents=True, exist_ok=True)
    paths.temp.mkdir(parents=True, exist_ok=True)

    output_path = Path(output_dir).resolve() if output_dir else paths.output
    manifest = {
        "schema_version": 1,
        "created": datetime.now().isoformat(timespec="seconds"),
        "name": batch_name,
        "source_url": url,
        "rights_basis": rights_basis,
        "status": "planned",
        "paths": {
            "urls": str(paths.urls),
            "yt_dlp_config": str(paths.config),
            "download_archive": str(paths.archive),
            "output": str(output_path),
            "temp": str(paths.temp),
        },
        "policy": {
            "requires_mullvad_connected": True,
            "stop_on_throttle_or_block": True,
            "no_automatic_relay_rotation": True,
        },
    }
    paths.urls.write_text(url + "\n", encoding="utf-8")
    write_ytdlp_config(paths.config, paths.urls, paths.archive, output_path, paths.temp)
    paths.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return paths


def write_ytdlp_config(config: Path, urls: Path, archive: Path, output: Path, temp: Path) -> None:
    def ytdlp_path(path: Path) -> str:
        return path.resolve().as_posix()

    lines = [
        "--batch-file",
        ytdlp_path(urls),
        "--download-archive",
        ytdlp_path(archive),
        "--paths",
        f"home:{ytdlp_path(output)}",
        "--paths",
        f"temp:{ytdlp_path(temp)}",
        "--output",
        "%(uploader|Unknown)s/%(upload_date>%Y-%m-%d|NA)s - %(title).180B [%(id)s].%(ext)s",
        "--windows-filenames",
        "--continue",
        "--no-overwrites",
        "--retries",
        "10",
        "--fragment-retries",
        "10",
        "--retry-sleep",
        "http:exp=1:20",
        "--retry-sleep",
        "fragment:exp=1:20",
        "--sleep-requests",
        "1",
        "--sleep-interval",
        "15",
        "--max-sleep-interval",
        "45",
        "--skip-playlist-after-errors",
        "3",
        "--write-info-json",
        "--newline",
    ]
    config.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def preflight_batch(path: Path, *, require_connected: bool = True) -> list[Check]:
    manifest = load_manifest(path)
    checks = [
        Check("manifest", True, str(path)),
        Check("source url", validate_url(manifest.get("source_url", "")), manifest.get("source_url", "<missing>")),
        Check("rights basis", bool(manifest.get("rights_basis", "").strip()), "present" if manifest.get("rights_basis") else "missing"),
    ]
    for label, key in [
        ("urls file", "urls"),
        ("yt-dlp config", "yt_dlp_config"),
        ("download archive parent", "download_archive"),
        ("output path", "output"),
        ("temp path", "temp"),
    ]:
        value = manifest.get("paths", {}).get(key)
        if not value:
            checks.append(Check(label, False, "missing"))
            continue
        target = Path(value)
        exists = target.exists() if key not in {"download_archive"} else target.parent.exists()
        checks.append(Check(label, exists, str(target)))

    checks.extend(run_doctor())
    if not require_connected:
        return checks
    return checks


def preflight_ok(checks: list[Check], *, require_connected: bool = True) -> bool:
    return overall_ok(checks, require_connected=require_connected)


def run_batch(path: Path, *, dry_run: bool = True) -> CommandResult:
    manifest = load_manifest(path)
    config = Path(manifest["paths"]["yt_dlp_config"])
    tool = find_ytdlp()
    if not tool.path:
        return CommandResult(("yt-dlp",), 127, "", "yt-dlp not found")
    args = [tool.path, "--config-location", config]
    if dry_run:
        args.extend(["--simulate", "--dump-json"])
    return run_command(args, timeout=24 * 60 * 60)
