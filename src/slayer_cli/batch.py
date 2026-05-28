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
from .tools import find_js_runtime, find_ytdlp


BATCHES_DIR = PROJECT_ROOT / "batches"

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
        config=root / "yt-dlp.conf",
        archive=root / "archive.txt",
        output=root / "downloads",
        temp=root / "tmp",
    )


def create_batch(*, url: str, rights_basis: str, name: str | None = None, output_dir: str | None = None) -> BatchPaths:
    return create_batch_from_urls(urls=[url], rights_basis=rights_basis, name=name, output_dir=output_dir)


def create_batch_from_urls(
    *,
    urls: list[str],
    rights_basis: str,
    name: str | None = None,
    output_dir: str | None = None,
) -> BatchPaths:
    if not urls:
        raise ValueError("At least one URL is required")
    invalid = [url for url in urls if not validate_url(url)]
    if invalid:
        raise ValueError(f"Invalid URL: {invalid[0]}")
    if not rights_basis.strip():
        raise ValueError("A rights basis is required")

    parsed = urlparse(urls[0])
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
        "source_url": urls[0],
        "source_urls": urls,
        "url_count": len(urls),
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
    write_ytdlp_config(paths.config, paths.urls, paths.archive, output_path, paths.temp)
    paths.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return paths


def write_ytdlp_config(config: Path, urls: Path, archive: Path, output: Path, temp: Path) -> None:
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
        quote_config_value("%(uploader|Unknown)s/%(upload_date>%Y-%m-%d|NA)s - %(title).180B [%(id)s].%(ext)s"),
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
    config.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
        Check("rights basis", bool(manifest.get("rights_basis", "").strip()), "present" if manifest.get("rights_basis") else "missing"),
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
    output = (result.stderr or result.stdout).lower()
    if any(pattern in output for pattern in SOURCE_BLOCK_PATTERNS):
        return "source-block"
    if any(pattern in output for pattern in TRANSIENT_NETWORK_PATTERNS):
        return "transient-network"
    return "unknown"


def run_batch(path: Path, *, dry_run: bool = True) -> CommandResult:
    manifest = load_manifest(path)
    config = Path(manifest["paths"]["yt_dlp_config"])
    tool = find_ytdlp()
    if not tool.path:
        return CommandResult(("yt-dlp",), 127, "", "yt-dlp not found")
    args = [tool.path, "--ignore-config", "--config-location", config]
    if dry_run:
        args.extend(["--simulate", "--dump-json"])
    return run_command(args, timeout=24 * 60 * 60)
