from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .batch import REPORTS_DIR, load_manifest
from .doctor import Check
from .ledger import load_item_ledger, refresh_item_ledger, summarize_ledger
from .process import run_command
from .tools import find_ffprobe


MEDIA_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}
INFO_SUFFIX = ".info.json"


@dataclass(frozen=True)
class VerifySummary:
    manifest: Path
    batch_name: str
    status: str
    url_count: int
    expected_downloads: int
    archive_entries: int
    media_files: int
    info_json_files: int
    report_files: int
    total_media_bytes: int
    ledger_items: int
    ledger_statuses: dict[str, int]
    ledger_warnings: int


def media_files_under(output: Path) -> list[Path]:
    if not output.exists():
        return []
    return sorted(path for path in output.rglob("*") if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS)


def info_json_files_under(output: Path) -> list[Path]:
    if not output.exists():
        return []
    return sorted(path for path in output.rglob("*") if path.is_file() and path.name.endswith(INFO_SUFFIX))


def archive_entries(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def report_files_for(manifest_path: Path) -> list[Path]:
    report_dir = REPORTS_DIR / manifest_path.parent.name
    if not report_dir.exists():
        return []
    return sorted(path for path in report_dir.glob("*.json") if path.is_file())


def expected_download_count(manifest: dict) -> int:
    url_count = int(manifest.get("url_count") or len(manifest.get("source_urls", [])) or 1)
    max_downloads = manifest.get("limits", {}).get("max_downloads")
    if isinstance(max_downloads, int) and max_downloads > 0:
        return min(url_count, max_downloads)
    return url_count


def summarize_batch(manifest_path: Path) -> VerifySummary:
    manifest = load_manifest(manifest_path)
    output = Path(manifest["paths"]["output"])
    archive = Path(manifest["paths"]["download_archive"])
    media = media_files_under(output)
    reports = report_files_for(manifest_path)
    ledger_path = manifest.get("paths", {}).get("item_ledger")
    ledger_summary = {"items": 0, "statuses": {}, "warnings": 0}
    if ledger_path:
        ledger_summary = summarize_ledger(load_item_ledger(Path(ledger_path)))
    return VerifySummary(
        manifest=manifest_path,
        batch_name=str(manifest.get("name", manifest_path.parent.name)),
        status=str(manifest.get("status", "unknown")),
        url_count=int(manifest.get("url_count") or len(manifest.get("source_urls", [])) or 1),
        expected_downloads=expected_download_count(manifest),
        archive_entries=len(archive_entries(archive)),
        media_files=len(media),
        info_json_files=len(info_json_files_under(output)),
        report_files=len(reports),
        total_media_bytes=sum(path.stat().st_size for path in media),
        ledger_items=int(ledger_summary.get("items", 0)),
        ledger_statuses=dict(ledger_summary.get("statuses", {})),
        ledger_warnings=int(ledger_summary.get("warnings", 0)),
    )


def probe_media(path: Path) -> Check:
    tool = find_ffprobe()
    if not tool.path:
        return Check(f"media probe {path.name}", False, "ffprobe not found")
    result = run_command(
        [
            tool.path,
            "-v",
            "error",
            "-show_entries",
            "format=duration,size,format_name",
            "-of",
            "default=noprint_wrappers=1:nokey=0",
            path,
        ],
        timeout=60,
    )
    output = "\n".join(part for part in [result.stdout, result.stderr] if part)
    return Check(f"media probe {path.name}", result.ok and bool(result.stdout), output or "no ffprobe output")


def verify_batch(manifest_path: Path, *, allow_empty: bool = False, probe: bool = True) -> tuple[VerifySummary, list[Check]]:
    summary = summarize_batch(manifest_path)
    manifest = load_manifest(manifest_path)
    output = Path(manifest["paths"]["output"])
    archive = Path(manifest["paths"]["download_archive"])
    media = media_files_under(output)
    ledger_path = manifest.get("paths", {}).get("item_ledger")
    if ledger_path:
        refresh_item_ledger(manifest)
        summary = summarize_batch(manifest_path)
    checks = [
        Check("manifest", manifest_path.exists(), str(manifest_path)),
        Check("output path", output.exists(), str(output)),
        Check("archive file", archive.exists() or allow_empty, str(archive)),
        Check("run reports", summary.report_files > 0 or allow_empty, f"{summary.report_files} report(s)"),
        Check("archive entries", summary.archive_entries >= summary.expected_downloads or allow_empty, f"{summary.archive_entries}/{summary.expected_downloads}"),
        Check("media files", summary.media_files >= summary.expected_downloads or allow_empty, f"{summary.media_files}/{summary.expected_downloads}"),
        Check("info json files", summary.info_json_files >= summary.expected_downloads or allow_empty, f"{summary.info_json_files}/{summary.expected_downloads}"),
    ]
    if ledger_path:
        checks.append(Check("item ledger", Path(ledger_path).exists(), str(ledger_path)))
        checks.append(Check("ledger items", summary.ledger_items >= summary.expected_downloads or allow_empty, f"{summary.ledger_items}/{summary.expected_downloads}"))
    if probe:
        checks.extend(probe_media(path) for path in media)
    return summary, checks
