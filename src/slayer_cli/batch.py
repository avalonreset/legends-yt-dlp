from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from .doctor import Check, overall_ok, run_doctor
from .ledger import planned_items_from_urls, refresh_item_ledger, write_item_ledger
from .paths import PROJECT_ROOT
from .process import CommandResult, run_command
from .tools import find_js_runtime, find_ytdlp


BATCHES_DIR = PROJECT_ROOT / "batches"
REPORTS_DIR = PROJECT_ROOT / "reports"

SOURCE_BLOCK_PATTERNS = (
    "captcha",
    "sign in",
    "signin",
    "login",
    "http error 429",
    "too many requests",
    "rate limit",
    "temporarily blocked",
    "forbidden",
    "access denied",
    "not available in your country",
    "private video",
    "drm",
)

TRANSIENT_NETWORK_PATTERNS = (
    "network is unreachable",
    "no route to host",
    "connection reset",
    "connection aborted",
    "connection refused",
    "timed out",
    "timeout",
    "temporary failure in name resolution",
    "dns",
    "tls",
    "ssl",
    "unable to download webpage",
    "remote end closed connection",
)

REQUIRED_AUTH_SAFETY_OPTIONS = (
    "--ignore-config",
    "--no-cookies",
    "--no-cookies-from-browser",
)

FOLDER_POLICIES = {"auto", "batch", "by-uploader", "flat"}
UPLOADER_OUTPUT_TEMPLATE = "%(uploader|Unknown)s/%(upload_date>%Y-%m-%d|NA)s - %(title).180B [%(id)s].%(ext)s"
FLAT_OUTPUT_TEMPLATE = "%(upload_date>%Y-%m-%d|NA)s - %(uploader|Unknown)s - %(title).180B [%(id)s].%(ext)s"

FORBIDDEN_AUTH_OPTIONS = {
    "--cookies",
    "--cookies-from-browser",
    "-u",
    "--username",
    "-p",
    "--password",
    "-n",
    "--netrc",
    "--netrc-location",
    "--netrc-cmd",
    "--video-password",
    "--ap-username",
    "--ap-password",
    "--client-certificate-password",
}


@dataclass(frozen=True)
class BatchPaths:
    root: Path
    manifest: Path
    urls: Path
    ledger: Path
    config: Path
    archive: Path
    output: Path
    temp: Path


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug[:60] or "batch"


def resolve_folder_policy(folder_policy: str, *, urls: list[str], items: list[dict] | None = None) -> str:
    normalized = folder_policy.strip().lower()
    if normalized not in FOLDER_POLICIES:
        raise ValueError(f"--folder-policy must be one of: {', '.join(sorted(FOLDER_POLICIES))}")
    if normalized != "auto":
        return normalized
    if items is not None:
        return "by-uploader"
    return "batch" if len(urls) > 1 else "by-uploader"


def output_template_for_policy(folder_policy: str) -> str:
    if folder_policy == "by-uploader":
        return UPLOADER_OUTPUT_TEMPLATE
    return FLAT_OUTPUT_TEMPLATE


def validate_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def read_url_file(path: Path) -> list[str]:
    urls: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def make_batch_paths(name: str) -> BatchPaths:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    root = BATCHES_DIR / f"{stamp}-{slugify(name)}"
    return BatchPaths(
        root=root,
        manifest=root / "manifest.json",
        urls=root / "urls.txt",
        ledger=root / "items.jsonl",
        config=root / "yt-dlp.conf",
        archive=root / "archive.txt",
        output=root / "downloads",
        temp=root / "tmp",
    )


def create_batch(*, url: str, rights_basis: str | None = None, name: str | None = None, output_dir: str | None = None) -> BatchPaths:
    return create_batch_from_urls(urls=[url], rights_basis=rights_basis, name=name, output_dir=output_dir)


def create_batch_from_urls(
    *,
    urls: list[str],
    rights_basis: str | None = None,
    name: str | None = None,
    output_dir: str | None = None,
    max_height: int | None = None,
    max_downloads: int | None = None,
    max_filesize: str | None = None,
    items: list[dict] | None = None,
    rights_file: str | None = None,
    folder_policy: str = "auto",
) -> BatchPaths:
    if not urls:
        raise ValueError("At least one URL is required")
    invalid = [url for url in urls if not validate_url(url)]
    if invalid:
        raise ValueError(f"Invalid URL: {invalid[0]}")
    if max_height is not None and max_height <= 0:
        raise ValueError("--max-height must be greater than 0")
    if max_downloads is not None and max_downloads <= 0:
        raise ValueError("--max-downloads must be greater than 0")
    rights_evidence_path: Path | None = None
    if rights_file:
        source = Path(rights_file)
        if not source.exists() or not source.is_file():
            raise ValueError(f"Rights evidence file not found: {rights_file}")

    parsed = urlparse(urls[0])
    batch_name = name or parsed.netloc
    effective_folder_policy = resolve_folder_policy(folder_policy, urls=urls, items=items)
    paths = make_batch_paths(batch_name)
    paths.root.mkdir(parents=True, exist_ok=False)
    paths.output.mkdir(parents=True, exist_ok=True)
    paths.temp.mkdir(parents=True, exist_ok=True)
    if rights_file:
        source = Path(rights_file).resolve()
        rights_dir = paths.root / "rights"
        rights_dir.mkdir(parents=True, exist_ok=True)
        rights_evidence_path = rights_dir / source.name
        shutil.copy2(source, rights_evidence_path)

    output_base = Path(output_dir).resolve() if output_dir else paths.output
    output_path = output_base / slugify(batch_name) if output_dir and effective_folder_policy == "batch" else output_base
    if output_path.exists() and not output_path.is_dir():
        raise ValueError(f"Output path is not a directory: {output_path}")
    output_path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 1,
        "created": datetime.now().isoformat(timespec="seconds"),
        "name": batch_name,
        "source_url": urls[0],
        "source_urls": urls,
        "url_count": len(urls),
        "rights_basis": rights_basis.strip() if rights_basis else None,
        "status": "planned",
        "paths": {
            "urls": str(paths.urls),
            "item_ledger": str(paths.ledger),
            "yt_dlp_config": str(paths.config),
            "download_archive": str(paths.archive),
            "output": str(output_path),
            "temp": str(paths.temp),
        },
        "rights_evidence": str(rights_evidence_path) if rights_evidence_path else None,
        "limits": {
            "max_height": max_height,
            "max_downloads": max_downloads,
            "max_filesize": max_filesize,
        },
        "folder_policy": {
            "requested": folder_policy,
            "effective": effective_folder_policy,
            "output_template": output_template_for_policy(effective_folder_policy),
        },
        "policy": {
            "requires_mullvad_connected": True,
            "requires_mullvad_lockdown": True,
            "requires_anonymous_ytdlp": True,
            "ignore_user_ytdlp_config": True,
            "no_browser_cookies": True,
            "no_account_auth": True,
            "stop_on_throttle_or_block": True,
            "no_automatic_relay_rotation": True,
        },
    }
    paths.urls.write_text("\n".join(urls) + "\n", encoding="utf-8")
    write_item_ledger(paths.ledger, items or planned_items_from_urls(urls))
    write_ytdlp_config(
        paths.config,
        paths.urls,
        paths.archive,
        output_path,
        paths.temp,
        max_height=max_height,
        max_downloads=max_downloads,
        max_filesize=max_filesize,
        output_template=output_template_for_policy(effective_folder_policy),
    )
    paths.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return paths


def write_ytdlp_config(
    config: Path,
    urls: Path,
    archive: Path,
    output: Path,
    temp: Path,
    *,
    max_height: int | None = None,
    max_downloads: int | None = None,
    max_filesize: str | None = None,
    output_template: str = UPLOADER_OUTPUT_TEMPLATE,
) -> None:
    def ytdlp_path(path: Path) -> str:
        return path.resolve().as_posix()

    def quote_config_value(value: str) -> str:
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'

    lines = [
        "--ignore-config",
        "--no-cookies",
        "--no-cookies-from-browser",
        "--batch-file",
        quote_config_value(ytdlp_path(urls)),
        "--download-archive",
        quote_config_value(ytdlp_path(archive)),
        "--paths",
        quote_config_value(f"home:{ytdlp_path(output)}"),
        "--paths",
        quote_config_value(f"temp:{ytdlp_path(temp)}"),
        "--output",
        quote_config_value(output_template),
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
    js_runtime = find_js_runtime()
    if js_runtime.path:
        runtime_value = f"{js_runtime.detail}:{js_runtime.path.resolve().as_posix()}"
        lines[3:3] = ["--js-runtimes", quote_config_value(runtime_value)]
    if max_height:
        format_selector = f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/best"
        lines.extend(["--format", quote_config_value(format_selector), "--merge-output-format", "mp4"])
    if max_downloads:
        lines.extend(["--max-downloads", str(max_downloads)])
    if max_filesize:
        lines.extend(["--max-filesize", quote_config_value(max_filesize)])
    config.write_text("\n".join(lines) + "\n", encoding="utf-8")


def js_runtime_args() -> list[str]:
    js_runtime = find_js_runtime()
    if not js_runtime.path:
        return []
    runtime_value = f"{js_runtime.detail}:{js_runtime.path.resolve().as_posix()}"
    return ["--js-runtimes", runtime_value]


def read_config_options(config: Path) -> list[str]:
    options: list[str] = []
    for raw_line in config.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        token = line.split(maxsplit=1)[0].split("=", 1)[0].lower()
        options.append(token)
    return options


def auth_policy_check(config: Path) -> Check:
    try:
        options = read_config_options(config)
    except OSError as exc:
        return Check("yt-dlp auth policy", False, f"config unreadable: {exc}")

    violations = sorted(option for option in set(options) if option in FORBIDDEN_AUTH_OPTIONS)
    if violations:
        return Check("yt-dlp auth policy", False, f"forbidden auth/cookie options: {', '.join(violations)}")

    missing = [option for option in REQUIRED_AUTH_SAFETY_OPTIONS if option not in options]
    if missing:
        return Check("yt-dlp auth policy", False, f"missing safety options: {', '.join(missing)}")

    return Check("yt-dlp auth policy", True, "anonymous mode: no cookies, no browser cookies, user configs ignored")


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def find_batch_manifests() -> list[Path]:
    if not BATCHES_DIR.exists():
        return []
    return sorted(BATCHES_DIR.glob("*/manifest.json"), key=lambda path: path.stat().st_mtime, reverse=True)


def catalog_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for manifest_path in find_batch_manifests():
        try:
            manifest = load_manifest(manifest_path)
        except (OSError, json.JSONDecodeError):
            continue
        rows.append(
            {
                "created": str(manifest.get("created", "")),
                "name": str(manifest.get("name", manifest_path.parent.name)),
                "status": str(manifest.get("status", "unknown")),
                "urls": str(manifest.get("url_count", len(manifest.get("source_urls", [])) or 1)),
                "manifest": str(manifest_path),
            }
        )
    return rows


def preflight_batch(path: Path, *, require_connected: bool = True, production: bool = True) -> list[Check]:
    manifest = load_manifest(path)
    policy = manifest.get("policy", {})
    checks = [
        Check("manifest", True, str(path)),
        Check("source url", validate_url(manifest.get("source_url", "")), manifest.get("source_url", "<missing>")),
    ]
    if production:
        for label, key in [
            ("policy requires Mullvad", "requires_mullvad_connected"),
            ("policy requires Lockdown", "requires_mullvad_lockdown"),
            ("policy anonymous yt-dlp", "requires_anonymous_ytdlp"),
            ("policy ignores user yt-dlp config", "ignore_user_ytdlp_config"),
            ("policy no browser cookies", "no_browser_cookies"),
            ("policy no account auth", "no_account_auth"),
        ]:
            checks.append(Check(label, policy.get(key) is True, "enabled" if policy.get(key) is True else "missing or false"))

    config_path: Path | None = None
    for label, key in [
        ("urls file", "urls"),
        ("item ledger", "item_ledger"),
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
        if key == "yt_dlp_config":
            config_path = target
        exists = target.exists() if key not in {"download_archive"} else target.parent.exists()
        checks.append(Check(label, exists, str(target)))

    if production and config_path is not None:
        checks.append(auth_policy_check(config_path))

    checks.extend(run_doctor(production=production))
    if not require_connected:
        return checks
    return checks


def preflight_ok(checks: list[Check], *, require_connected: bool = True) -> bool:
    return overall_ok(checks, require_connected=require_connected)


def only_mullvad_connection_failed(checks: list[Check]) -> bool:
    failed = [check for check in checks if not check.ok]
    recoverable = {"mullvad connected", "mullvad lockdown"}
    return bool(failed) and all(check.name in recoverable for check in failed)


def classify_run_failure(result: CommandResult) -> str:
    if result.returncode == 101:
        return "limit-reached"
    output = diagnostic_output(result).lower()
    if any(pattern in output for pattern in SOURCE_BLOCK_PATTERNS):
        return "source-block"
    if any(pattern in output for pattern in TRANSIENT_NETWORK_PATTERNS):
        return "transient-network"
    return "unknown"


def diagnostic_output(result: CommandResult) -> str:
    lines = [line for line in result.stderr.splitlines() if line.strip()]
    lines.extend(line for line in result.stdout.splitlines() if line.lower().startswith(("error:", "warning:")))
    return "\n".join(lines)


def classify_success(result: CommandResult) -> str:
    output = diagnostic_output(result).lower()
    if any(pattern in output for pattern in SOURCE_BLOCK_PATTERNS):
        return "source-warning"
    if any(pattern in output for pattern in TRANSIENT_NETWORK_PATTERNS):
        return "network-warning"
    return "ok"


def run_status(*, dry_run: bool, returncode: int, category: str) -> str:
    if returncode == 0:
        if category == "source-warning":
            return "completed_with_source_warnings"
        if category == "network-warning":
            return "completed_with_network_warnings"
        return "dry_run_passed" if dry_run else "completed"
    if category == "limit-reached":
        return "limit_reached"
    if category == "source-block":
        return "paused_source_block"
    if category == "transient-network":
        return "paused_network_failure"
    return "failed"


def next_action_for_status(status: str, category: str) -> str:
    if status == "dry_run_passed":
        return "Review the plan, then run with --yes when ready."
    if status == "completed":
        return "Run verify on the manifest."
    if status == "completed_with_source_warnings":
        return "Review diagnostics before scaling this source."
    if status == "completed_with_network_warnings":
        return "Review network diagnostics and rerun verify."
    if status == "limit_reached":
        return "Configured limit reached; inspect ledger before continuing."
    if status == "paused_source_block":
        return "Pause. Do not rotate relays to continue through source-side blocks."
    if status == "paused_network_failure":
        return "Recover Mullvad/network posture, then rerun preflight."
    return f"Investigate {category} failure before retrying."


def write_run_report(
    manifest_path: Path,
    *,
    dry_run: bool,
    result: CommandResult,
    category: str,
    started: str,
    ended: str,
) -> Path:
    manifest = load_manifest(manifest_path)
    status = run_status(dry_run=dry_run, returncode=result.returncode, category=category)
    report_dir = REPORTS_DIR / manifest_path.parent.name
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-run-report.json"
    stderr_lines = [line for line in result.stderr.splitlines() if line.strip()]
    diagnostic_lines = [line for line in diagnostic_output(result).splitlines() if line.strip()]
    report = {
        "schema_version": 1,
        "batch": manifest.get("name", manifest_path.parent.name),
        "manifest": str(manifest_path),
        "dry_run": dry_run,
        "started": started,
        "ended": ended,
        "returncode": result.returncode,
        "classification": category,
        "status": status,
        "next_action": next_action_for_status(status, category),
        "stdout_bytes": len(result.stdout.encode("utf-8", errors="replace")),
        "stderr_bytes": len(result.stderr.encode("utf-8", errors="replace")),
        "stderr_tail": stderr_lines[-20:],
        "diagnostic_tail": diagnostic_lines[-20:],
    }
    ledger_summary = refresh_item_ledger(manifest)
    report["ledger"] = ledger_summary
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    manifest["status"] = status
    manifest["last_run"] = {
        "dry_run": dry_run,
        "ended": ended,
        "returncode": result.returncode,
        "classification": category,
        "report": str(report_path),
        "ledger": ledger_summary,
    }
    save_manifest(manifest_path, manifest)
    return report_path


def run_batch(path: Path, *, dry_run: bool = True) -> CommandResult:
    manifest = load_manifest(path)
    config = Path(manifest["paths"]["yt_dlp_config"])
    tool = find_ytdlp()
    if not tool.path:
        return CommandResult(("yt-dlp",), 127, "", "yt-dlp not found")
    args = [tool.path, "--ignore-config", *js_runtime_args(), "--config-location", config]
    if dry_run:
        args.extend(["--simulate", "--dump-json"])
    return run_command(args, timeout=24 * 60 * 60)
