from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .batch import create_batch, preflight_batch, preflight_ok, run_batch
from .doctor import overall_ok, run_doctor
from .envfile import read_env_file, redact
from .mullvad import connect, login, redact_account_in_text, run_mullvad, set_lockdown, status
from .paths import PROJECT_ROOT
from .tools import find_ytdlp, install_ytdlp, run_tool


def print_check(name: str, ok: bool, detail: str) -> None:
    marker = "PASS" if ok else "FAIL"
    print(f"[{marker}] {name}: {detail}")


def cmd_doctor(args: argparse.Namespace) -> int:
    checks = run_doctor()
    for check in checks:
        print_check(check.name, check.ok, check.detail)
    return 0 if overall_ok(checks, require_connected=args.require_connected) else 1


def cmd_mullvad_status(args: argparse.Namespace) -> int:
    env = read_env_file(PROJECT_ROOT / ".env")
    account = env.get("MULLVAD_ACCOUNT_NUMBER")
    result = status(verbose=args.verbose)
    print(redact_account_in_text(result.raw or result.error or "", account))
    return 0 if result.available else 1


def cmd_mullvad_login(_: argparse.Namespace) -> int:
    env = read_env_file(PROJECT_ROOT / ".env")
    account = env.get("MULLVAD_ACCOUNT_NUMBER")
    if not account:
        print("MULLVAD_ACCOUNT_NUMBER is missing from .env", file=sys.stderr)
        return 2
    print(f"Logging into Mullvad account {redact(account)}")
    result = login(account)
    output = redact_account_in_text("\n".join(part for part in [result.stdout, result.stderr] if part), account)
    if output:
        print(output)
    return result.returncode


def cmd_mullvad_connect(_: argparse.Namespace) -> int:
    result = connect()
    output = "\n".join(part for part in [result.stdout, result.stderr] if part)
    if output:
        print(output)
    return result.returncode


def cmd_mullvad_lockdown(args: argparse.Namespace) -> int:
    result = set_lockdown(args.state == "on")
    output = "\n".join(part for part in [result.stdout, result.stderr] if part)
    if output:
        print(output)
    return result.returncode


def cmd_mullvad_raw(args: argparse.Namespace) -> int:
    env = read_env_file(PROJECT_ROOT / ".env")
    account = env.get("MULLVAD_ACCOUNT_NUMBER")
    result = run_mullvad(*args.args, timeout=args.timeout)
    output = redact_account_in_text("\n".join(part for part in [result.stdout, result.stderr] if part), account)
    if output:
        print(output)
    return result.returncode


def cmd_ytdlp_install(_: argparse.Namespace) -> int:
    path, actual, expected = install_ytdlp()
    print(f"Installed yt-dlp: {path}")
    print(f"SHA256: {actual}")
    if expected:
        print("SHA256 verified against official SHA2-256SUMS")
    info = find_ytdlp()
    if info.version:
        print(f"Version: {info.version}")
    return 0


def cmd_ytdlp_version(_: argparse.Namespace) -> int:
    info = find_ytdlp()
    if not info.path:
        print("yt-dlp not found. Run: python -m slayer_cli yt-dlp install", file=sys.stderr)
        return 1
    result = run_tool(info.path, "--version")
    print(result.stdout or result.stderr)
    return result.returncode


def cmd_plan(args: argparse.Namespace) -> int:
    try:
        paths = create_batch(url=args.url, rights_basis=args.rights, name=args.name, output_dir=args.output)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Batch created: {paths.root}")
    print(f"Manifest: {paths.manifest}")
    print(f"yt-dlp config: {paths.config}")
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    checks = preflight_batch(Path(args.manifest), require_connected=not args.no_require_connected)
    for check in checks:
        print_check(check.name, check.ok, check.detail)
    return 0 if preflight_ok(checks, require_connected=not args.no_require_connected) else 1


def cmd_run(args: argparse.Namespace) -> int:
    manifest = Path(args.manifest)
    checks = preflight_batch(manifest, require_connected=not args.no_require_connected)
    if not preflight_ok(checks, require_connected=not args.no_require_connected):
        for check in checks:
            print_check(check.name, check.ok, check.detail)
        print("Preflight failed. Batch did not start.", file=sys.stderr)
        return 1
    if not args.dry_run and not args.yes:
        print("Refusing real download without --yes. Use --dry-run first.", file=sys.stderr)
        return 2
    result = run_batch(manifest, dry_run=args.dry_run)
    output = "\n".join(part for part in [result.stdout, result.stderr] if part)
    if output:
        print(output)
    return result.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="slayer", description="Legends YT-DLP Slayer control CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Check local prerequisites")
    doctor.add_argument("--require-connected", action="store_true", help="Fail if Mullvad is not connected")
    doctor.set_defaults(func=cmd_doctor)

    mullvad = sub.add_parser("mullvad", help="Operate Mullvad through the official CLI")
    mullvad_sub = mullvad.add_subparsers(dest="mullvad_command", required=True)

    mv_status = mullvad_sub.add_parser("status", help="Show Mullvad status")
    mv_status.add_argument("-v", "--verbose", action="store_true")
    mv_status.set_defaults(func=cmd_mullvad_status)

    mv_login = mullvad_sub.add_parser("login", help="Login using MULLVAD_ACCOUNT_NUMBER from .env")
    mv_login.set_defaults(func=cmd_mullvad_login)

    mv_connect = mullvad_sub.add_parser("connect", help="Connect Mullvad")
    mv_connect.set_defaults(func=cmd_mullvad_connect)

    mv_lockdown = mullvad_sub.add_parser("lockdown", help="Set Mullvad Lockdown mode")
    mv_lockdown.add_argument("state", choices=["on", "off"])
    mv_lockdown.set_defaults(func=cmd_mullvad_lockdown)

    mv_raw = mullvad_sub.add_parser("raw", help="Pass raw args to Mullvad CLI")
    mv_raw.add_argument("args", nargs=argparse.REMAINDER)
    mv_raw.add_argument("--timeout", type=int, default=60)
    mv_raw.set_defaults(func=cmd_mullvad_raw)

    ytdlp = sub.add_parser("yt-dlp", help="Manage yt-dlp")
    ytdlp_sub = ytdlp.add_subparsers(dest="ytdlp_command", required=True)

    ytdlp_install = ytdlp_sub.add_parser("install", help="Download official stable Windows yt-dlp.exe")
    ytdlp_install.set_defaults(func=cmd_ytdlp_install)

    ytdlp_version = ytdlp_sub.add_parser("version", help="Show yt-dlp version")
    ytdlp_version.set_defaults(func=cmd_ytdlp_version)

    plan = sub.add_parser("plan", help="Create a rights-aware batch manifest")
    plan.add_argument("url", help="Source URL to archive")
    plan.add_argument("--rights", required=True, help="Documented rights basis for this batch")
    plan.add_argument("--name", help="Batch name")
    plan.add_argument("--output", help="Output directory override")
    plan.set_defaults(func=cmd_plan)

    preflight = sub.add_parser("preflight", help="Check a batch before running")
    preflight.add_argument("manifest", help="Path to batch manifest.json")
    preflight.add_argument("--no-require-connected", action="store_true", help="Do not fail solely because Mullvad is disconnected")
    preflight.set_defaults(func=cmd_preflight)

    run = sub.add_parser("run", help="Run or dry-run a batch")
    run.add_argument("manifest", help="Path to batch manifest.json")
    run.add_argument("--dry-run", action="store_true", help="Simulate yt-dlp without downloading")
    run.add_argument("--yes", action="store_true", help="Allow real downloads after preflight")
    run.add_argument("--no-require-connected", action="store_true", help="Do not fail solely because Mullvad is disconnected")
    run.set_defaults(func=cmd_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
