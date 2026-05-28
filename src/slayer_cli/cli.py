from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from .batch import (
    catalog_rows,
    classify_run_failure,
    classify_success,
    create_batch_from_urls,
    only_mullvad_connection_failed,
    preflight_batch,
    preflight_ok,
    read_url_file,
    run_batch,
    write_run_report,
)
from .doctor import overall_ok, run_doctor
from .envfile import read_env_file, redact
from .mullvad import (
    disconnect_refusal_reason,
    lockdown_setting,
    login,
    recover_connection,
    redact_account_in_text,
    run_mullvad,
    set_lockdown,
    status,
)
from .paths import PROJECT_ROOT
from .smoke import SMOKE_VIDEOS, create_smoke_batch
from .tools import find_ytdlp, install_ytdlp, run_tool
from .verify import verify_batch


def print_check(name: str, ok: bool, detail: str) -> None:
    marker = "PASS" if ok else "FAIL"
    print(f"[{marker}] {name}: {detail}")


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def env_account() -> str | None:
    return read_env_file(PROJECT_ROOT / ".env").get("MULLVAD_ACCOUNT_NUMBER")


def redacted_result_output(stdout: str, stderr: str) -> str:
    account = env_account()
    output = "\n".join(part for part in [stdout, stderr] if part)
    return redact_account_in_text(output, account)


def print_mullvad_result(args: list[str], *, timeout: int = 60) -> int:
    result = run_mullvad(*args, timeout=timeout)
    output = redacted_result_output(result.stdout, result.stderr)
    if output:
        print(output)
    return result.returncode


def cmd_doctor(args: argparse.Namespace) -> int:
    checks = run_doctor(production=args.production)
    for check in checks:
        print_check(check.name, check.ok, check.detail)
    return 0 if overall_ok(checks, require_connected=args.require_connected or args.production) else 1


def print_mullvad_step(label: str, mv_args: list[str], *, timeout: int = 120) -> int:
    print(f"## {label}")
    result = run_mullvad(*mv_args, timeout=timeout)
    output = redacted_result_output(result.stdout, result.stderr)
    if output:
        print(output)
    if result.returncode != 0:
        print(f"{label} failed.", file=sys.stderr)
    return result.returncode


def cmd_setup_production(args: argparse.Namespace) -> int:
    steps: list[tuple[str, list[str]]] = [
        ("Relay constraint", ["relay", "set", "location", *args.relay_location]),
        ("Lockdown mode", ["lockdown-mode", "set", "on"]),
        ("Auto-connect", ["auto-connect", "set", "on"]),
        ("LAN sharing", ["lan", "set", "block"]),
        ("Split tunnel", ["split-tunnel", "set", "off"]),
        ("Quantum-resistant tunnel", ["tunnel", "set", "quantum-resistant", "on"]),
        ("IPv6", ["tunnel", "set", "ipv6", "off"]),
    ]
    for label, mv_args in steps:
        exit_code = print_mullvad_step(label, mv_args)
        if exit_code != 0:
            return exit_code
    if not args.no_connect:
        recovery = recover_connection(attempts=args.attempts, wait_seconds=args.wait_seconds)
        print_recovery_messages(recovery.messages)
        if not recovery.ok:
            return 1
    checks = run_doctor(production=True)
    for check in checks:
        print_check(check.name, check.ok, check.detail)
    return 0 if overall_ok(checks, require_connected=True) else 1


def cmd_mullvad_status(args: argparse.Namespace) -> int:
    account = env_account()
    result = status(verbose=args.verbose)
    print(redact_account_in_text(result.raw or result.error or "", account))
    return 0 if result.available else 1


def cmd_mullvad_login(_: argparse.Namespace) -> int:
    account = env_account()
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
    return print_mullvad_result(["connect"], timeout=120)


def print_recovery_messages(messages: tuple[str, ...]) -> None:
    account = env_account()
    for message in messages:
        print(redact_account_in_text(message, account))


def cmd_mullvad_disconnect(args: argparse.Namespace) -> int:
    refusal = disconnect_refusal_reason(lockdown_setting(), force=args.force)
    if refusal:
        print(refusal, file=sys.stderr)
        print("For fail-closed testing, use: slayer mullvad disconnect-test --emergency-unlock", file=sys.stderr)
        return 2
    return print_mullvad_result(["disconnect"], timeout=120)


def cmd_mullvad_reconnect(_: argparse.Namespace) -> int:
    return print_mullvad_result(["reconnect"], timeout=120)


def cmd_mullvad_recover(args: argparse.Namespace) -> int:
    result = recover_connection(attempts=args.attempts, wait_seconds=args.wait_seconds)
    print_recovery_messages(result.messages)
    return 0 if result.ok else 1


def cmd_mullvad_disconnect_test(args: argparse.Namespace) -> int:
    if args.relay_location:
        result = run_mullvad("relay", "set", "location", *args.relay_location, timeout=120)
        output = redacted_result_output(result.stdout, result.stderr)
        if output:
            print(output)
        if result.returncode != 0:
            return result.returncode

    lockdown = set_lockdown(True)
    output = redacted_result_output(lockdown.stdout, lockdown.stderr)
    if output:
        print(output)

    recovery = recover_connection(attempts=args.attempts, wait_seconds=args.wait_seconds)
    print_recovery_messages(recovery.messages)
    if not recovery.ok:
        if args.emergency_unlock:
            print("Emergency unlock: disabling Lockdown because initial VPN recovery failed.", file=sys.stderr)
            unlock = set_lockdown(False)
            output = redacted_result_output(unlock.stdout, unlock.stderr)
            if output:
                print(output)
        return 1

    test_ok = False
    try:
        disconnected = run_mullvad("disconnect", timeout=120)
        output = redacted_result_output(disconnected.stdout, disconnected.stderr)
        if output:
            print(output)
        time.sleep(args.settle_seconds)
        after_disconnect = status(verbose=True)
        print(redact_account_in_text(after_disconnect.raw or after_disconnect.error or "", env_account()))
        raw = (after_disconnect.raw or "").lower()
        test_ok = disconnected.ok and after_disconnect.available and not after_disconnect.connected and ("lockdown" in raw or "blocked" in raw)
        if test_ok:
            print("Disconnect test confirmed: Mullvad disconnected and Lockdown blocked internet access.")
        else:
            print("Disconnect test did not confirm the expected fail-closed state.", file=sys.stderr)
    finally:
        recovery = recover_connection(attempts=args.attempts, wait_seconds=args.wait_seconds)
        print_recovery_messages(recovery.messages)
        final = status(verbose=True)
        if final.connected:
            print("Recovery verified: Mullvad is connected.")
        elif args.emergency_unlock:
            print("Emergency unlock: disabling Lockdown after recovery failure.", file=sys.stderr)
            unlock = set_lockdown(False)
            output = redacted_result_output(unlock.stdout, unlock.stderr)
            if output:
                print(output)
        else:
            print("Recovery failed. Run slayer mullvad recover, or slayer mullvad lockdown off as a manual emergency rescue.", file=sys.stderr)

    return 0 if test_ok and status(verbose=True).connected else 1


def cmd_mullvad_lockdown(args: argparse.Namespace) -> int:
    if args.state == "get":
        return print_mullvad_result(["lockdown-mode", "get"])
    result = set_lockdown(args.state == "on")
    output = redacted_result_output(result.stdout, result.stderr)
    if output:
        print(output)
    return result.returncode


def cmd_mullvad_static(args: argparse.Namespace) -> int:
    return print_mullvad_result(list(args.mullvad_args), timeout=getattr(args, "timeout", 60))


def cmd_mullvad_relay_location(args: argparse.Namespace) -> int:
    return print_mullvad_result(["relay", "set", "location", *args.location], timeout=120)


def cmd_mullvad_relay_provider(args: argparse.Namespace) -> int:
    return print_mullvad_result(["relay", "set", "provider", *args.providers], timeout=120)


def cmd_mullvad_dns_default(args: argparse.Namespace) -> int:
    mv_args = ["dns", "set", "default"]
    for attr, flag in [
        ("block_ads", "--block-ads"),
        ("block_trackers", "--block-trackers"),
        ("block_malware", "--block-malware"),
        ("block_adult_content", "--block-adult-content"),
        ("block_gambling", "--block-gambling"),
        ("block_social_media", "--block-social-media"),
    ]:
        if getattr(args, attr):
            mv_args.append(flag)
    return print_mullvad_result(mv_args)


def cmd_mullvad_dns_custom(args: argparse.Namespace) -> int:
    return print_mullvad_result(["dns", "set", "custom", *args.servers])


def cmd_mullvad_split_app(args: argparse.Namespace) -> int:
    mv_args = ["split-tunnel", "app", args.action]
    if args.action != "clear":
        if not args.path:
            print(f"split-tunnel app {args.action} requires an application path", file=sys.stderr)
            return 2
        mv_args.append(args.path)
    return print_mullvad_result(mv_args)


def cmd_mullvad_inspect(_: argparse.Namespace) -> int:
    commands: list[tuple[str, list[str]]] = [
        ("version", ["version"]),
        ("account", ["account", "get"]),
        ("status", ["status", "-v"]),
        ("lockdown", ["lockdown-mode", "get"]),
        ("auto-connect", ["auto-connect", "get"]),
        ("lan", ["lan", "get"]),
        ("relay", ["relay", "get"]),
        ("dns", ["dns", "get"]),
        ("tunnel", ["tunnel", "get"]),
        ("split-tunnel", ["split-tunnel", "get"]),
        ("anti-censorship", ["anti-censorship", "get"]),
        ("api-access", ["api-access", "get"]),
        ("custom-lists", ["custom-list", "list"]),
    ]
    exit_code = 0
    for label, mv_args in commands:
        print(f"\n## {label}")
        result = run_mullvad(*mv_args, timeout=60)
        output = redacted_result_output(result.stdout, result.stderr)
        if output:
            print(output)
        if result.returncode != 0:
            exit_code = result.returncode
    return exit_code


def cmd_mullvad_raw(args: argparse.Namespace) -> int:
    result = run_mullvad(*args.args, timeout=args.timeout)
    output = redacted_result_output(result.stdout, result.stderr)
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
    urls = list(args.urls)
    if args.from_file:
        try:
            urls.extend(read_url_file(Path(args.from_file)))
        except OSError as exc:
            print(f"Could not read URL file: {exc}", file=sys.stderr)
            return 2
    try:
        paths = create_batch_from_urls(
            urls=urls,
            rights_basis=args.rights,
            name=args.name,
            output_dir=args.output,
            max_height=args.max_height,
            max_downloads=args.max_downloads,
            max_filesize=args.max_filesize,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Batch created: {paths.root}")
    print(f"Manifest: {paths.manifest}")
    print(f"yt-dlp config: {paths.config}")
    print(f"URL count: {len(urls)}")
    return 0


def cmd_smoke_plan(args: argparse.Namespace) -> int:
    try:
        paths = create_smoke_batch(
            count=args.count,
            name=args.name,
            output_dir=args.output,
            max_height=args.max_height,
            max_filesize=args.max_filesize,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Smoke batch created: {paths.root}")
    print(f"Manifest: {paths.manifest}")
    print(f"yt-dlp config: {paths.config}")
    print(f"URL count: {args.count}")
    for video in SMOKE_VIDEOS[: args.count]:
        print(f"- {video.duration_seconds}s | {video.title} | {video.url}")
    return 0


def cmd_catalog(_: argparse.Namespace) -> int:
    rows = catalog_rows()
    if not rows:
        print("No batch manifests found.")
        return 0
    for row in rows:
        print(f"{row['created']} | {row['status']} | {row['urls']} URLs | {row['name']}")
        print(f"  {row['manifest']}")
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    production = not args.no_production and not args.no_require_connected
    checks = preflight_batch(Path(args.manifest), require_connected=not args.no_require_connected, production=production)
    for check in checks:
        print_check(check.name, check.ok, check.detail)
    return 0 if preflight_ok(checks, require_connected=not args.no_require_connected) else 1


def cmd_verify(args: argparse.Namespace) -> int:
    try:
        summary, checks = verify_batch(Path(args.manifest), allow_empty=args.allow_empty, probe=not args.no_probe)
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"Could not verify batch: {exc}", file=sys.stderr)
        return 1
    print(f"Batch: {summary.batch_name}")
    print(f"Status: {summary.status}")
    print(f"URLs: {summary.url_count}")
    print(f"Expected downloads: {summary.expected_downloads}")
    print(f"Archive entries: {summary.archive_entries}")
    print(f"Media files: {summary.media_files}")
    print(f"Info JSON files: {summary.info_json_files}")
    print(f"Reports: {summary.report_files}")
    print(f"Media bytes: {summary.total_media_bytes}")
    for check in checks:
        print_check(check.name, check.ok, check.detail)
    return 0 if all(check.ok for check in checks) else 1


def cmd_run(args: argparse.Namespace) -> int:
    if not args.dry_run and (args.no_production or args.no_require_connected):
        print("Refusing real download without production VPN posture. Remove --no-production/--no-require-connected.", file=sys.stderr)
        return 2
    manifest = Path(args.manifest)
    production = not args.no_production and not args.no_require_connected
    checks = preflight_batch(manifest, require_connected=not args.no_require_connected, production=production)
    if not preflight_ok(checks, require_connected=not args.no_require_connected):
        if args.recover_vpn and not args.no_require_connected and only_mullvad_connection_failed(checks):
            recovery = recover_connection(attempts=args.vpn_recovery_attempts, wait_seconds=args.vpn_recovery_wait)
            for message in recovery.messages:
                print(redact_account_in_text(message, env_account()))
            checks = preflight_batch(manifest, require_connected=True, production=True)
            if preflight_ok(checks, require_connected=True):
                print("Preflight passed after Mullvad recovery.")
            else:
                for check in checks:
                    print_check(check.name, check.ok, check.detail)
                print("Preflight failed after Mullvad recovery. Batch did not start.", file=sys.stderr)
                return 1
        else:
            for check in checks:
                print_check(check.name, check.ok, check.detail)
            print("Preflight failed. Batch did not start.", file=sys.stderr)
            return 1
    if not args.dry_run and not args.yes:
        print("Refusing real download without --yes. Use --dry-run first.", file=sys.stderr)
        return 2
    for attempt in range(0, args.vpn_recovery_attempts + 1):
        started = datetime.now().isoformat(timespec="seconds")
        result = run_batch(manifest, dry_run=args.dry_run)
        ended = datetime.now().isoformat(timespec="seconds")
        output = "\n".join(part for part in [result.stdout, result.stderr] if part)
        if output and (args.show_output or not args.dry_run or result.returncode != 0):
            print(output)
        elif output:
            byte_count = len(output.encode("utf-8", errors="replace"))
            print(f"yt-dlp output suppressed ({byte_count} bytes). Use --show-output to print it.")
        if result.returncode == 0:
            category = classify_success(result)
            report = write_run_report(manifest, dry_run=args.dry_run, result=result, category=category, started=started, ended=ended)
            if category == "source-warning":
                print("Source-side warning detected in a successful run. Review the run report before scaling this source.", file=sys.stderr)
            elif category == "network-warning":
                print("Network warning detected in a successful run. Review the run report before scaling this source.", file=sys.stderr)
            print(f"Run report: {report}")
            return 0
        category = classify_run_failure(result)
        if category == "limit-reached":
            report = write_run_report(manifest, dry_run=args.dry_run, result=result, category=category, started=started, ended=ended)
            print("Configured download limit reached.")
            print(f"Run report: {report}")
            return 0
        if not args.recover_vpn or category != "transient-network" or attempt >= args.vpn_recovery_attempts:
            if category == "source-block":
                print("Source-side block/throttle/login signal detected. Pausing without VPN relay/IP switching.", file=sys.stderr)
            report = write_run_report(manifest, dry_run=args.dry_run, result=result, category=category, started=started, ended=ended)
            print(f"Run report: {report}")
            return result.returncode
        print(f"Transient network failure detected. Recovering Mullvad before retry {attempt + 1}.", file=sys.stderr)
        recovery = recover_connection(attempts=1, wait_seconds=args.vpn_recovery_wait)
        for message in recovery.messages:
            print(redact_account_in_text(message, env_account()))
        if not recovery.ok:
            print("Mullvad recovery failed. Batch paused.", file=sys.stderr)
            return result.returncode
    return result.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="slayer", description="Legends YT-DLP Slayer control CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Check local prerequisites")
    doctor.add_argument("--require-connected", action="store_true", help="Fail if Mullvad is not connected")
    doctor.add_argument("--production", action="store_true", help="Require connected Mullvad, Lockdown, split tunnel off, LAN blocked, and auto-connect on")
    doctor.set_defaults(func=cmd_doctor)

    setup = sub.add_parser("setup", help="Configure local production posture")
    setup_sub = setup.add_subparsers(dest="setup_command", required=True)
    setup_production = setup_sub.add_parser("production", help="Set safe Mullvad defaults and verify production doctor")
    setup_production.add_argument("--relay-location", nargs="+", default=["us"], help="Mullvad relay constraint; defaults to us")
    setup_production.add_argument("--attempts", type=int, default=3)
    setup_production.add_argument("--wait-seconds", type=float, default=5.0)
    setup_production.add_argument("--no-connect", action="store_true", help="Apply settings without connecting/recovering Mullvad")
    setup_production.set_defaults(func=cmd_setup_production)

    mullvad = sub.add_parser("mullvad", help="Operate Mullvad through the official CLI")
    mullvad_sub = mullvad.add_subparsers(dest="mullvad_command", required=True)

    mv_status = mullvad_sub.add_parser("status", help="Show Mullvad status")
    mv_status.add_argument("-v", "--verbose", action="store_true")
    mv_status.set_defaults(func=cmd_mullvad_status)

    mv_login = mullvad_sub.add_parser("login", help="Login using MULLVAD_ACCOUNT_NUMBER from .env")
    mv_login.set_defaults(func=cmd_mullvad_login)

    mv_connect = mullvad_sub.add_parser("connect", help="Connect Mullvad")
    mv_connect.set_defaults(func=cmd_mullvad_connect)

    mv_disconnect = mullvad_sub.add_parser("disconnect", help="Disconnect Mullvad; refuses by default if Lockdown is on")
    mv_disconnect.add_argument("--force", action="store_true", help="Allow disconnect even when Lockdown is on")
    mv_disconnect.set_defaults(func=cmd_mullvad_disconnect)

    mv_disconnect_test = mullvad_sub.add_parser("disconnect-test", help="Safely test fail-closed disconnect and automatic recovery")
    mv_disconnect_test.add_argument("--attempts", type=int, default=3)
    mv_disconnect_test.add_argument("--wait-seconds", type=float, default=5.0)
    mv_disconnect_test.add_argument("--settle-seconds", type=float, default=3.0)
    mv_disconnect_test.add_argument("--relay-location", nargs="+", default=["us"], help="Relay location constraint for the test; defaults to us")
    mv_disconnect_test.add_argument(
        "--emergency-unlock",
        action="store_true",
        help="Disable Lockdown only if recovery fails, restoring operator connectivity at the cost of native-IP exposure",
    )
    mv_disconnect_test.set_defaults(func=cmd_mullvad_disconnect_test)

    mv_reconnect = mullvad_sub.add_parser("reconnect", help="Reconnect Mullvad")
    mv_reconnect.set_defaults(func=cmd_mullvad_reconnect)

    mv_recover = mullvad_sub.add_parser("recover", help="Recover Mullvad connection for tunnel/network failures")
    mv_recover.add_argument("--attempts", type=int, default=2)
    mv_recover.add_argument("--wait-seconds", type=float, default=5.0)
    mv_recover.set_defaults(func=cmd_mullvad_recover)

    mv_lockdown = mullvad_sub.add_parser("lockdown", help="Set Mullvad Lockdown mode")
    mv_lockdown.add_argument("state", choices=["get", "on", "off"])
    mv_lockdown.set_defaults(func=cmd_mullvad_lockdown)

    mv_inspect = mullvad_sub.add_parser("inspect", help="Show safe Mullvad settings snapshot")
    mv_inspect.set_defaults(func=cmd_mullvad_inspect)

    mv_account = mullvad_sub.add_parser("account", help="Read account/device information")
    mv_account_sub = mv_account.add_subparsers(dest="account_command", required=True)
    mv_account_get = mv_account_sub.add_parser("get", help="Show current account")
    mv_account_get.set_defaults(func=cmd_mullvad_static, mullvad_args=("account", "get"))
    mv_account_devices = mv_account_sub.add_parser("devices", help="List account devices")
    mv_account_devices.set_defaults(func=cmd_mullvad_static, mullvad_args=("account", "list-devices"))

    mv_version = mullvad_sub.add_parser("version", help="Show Mullvad version and update state")
    mv_version.set_defaults(func=cmd_mullvad_static, mullvad_args=("version",))

    mv_auto = mullvad_sub.add_parser("auto-connect", help="Control auto-connect")
    mv_auto_sub = mv_auto.add_subparsers(dest="auto_command", required=True)
    mv_auto_get = mv_auto_sub.add_parser("get")
    mv_auto_get.set_defaults(func=cmd_mullvad_static, mullvad_args=("auto-connect", "get"))
    mv_auto_set = mv_auto_sub.add_parser("set")
    mv_auto_set.add_argument("state", choices=["on", "off"])
    mv_auto_set.set_defaults(func=lambda a: print_mullvad_result(["auto-connect", "set", a.state]))

    mv_lan = mullvad_sub.add_parser("lan", help="Control local network sharing")
    mv_lan_sub = mv_lan.add_subparsers(dest="lan_command", required=True)
    mv_lan_get = mv_lan_sub.add_parser("get")
    mv_lan_get.set_defaults(func=cmd_mullvad_static, mullvad_args=("lan", "get"))
    mv_lan_set = mv_lan_sub.add_parser("set")
    mv_lan_set.add_argument("state", choices=["allow", "block"])
    mv_lan_set.set_defaults(func=lambda a: print_mullvad_result(["lan", "set", a.state]))

    mv_relay = mullvad_sub.add_parser("relay", help="Manage relay constraints")
    mv_relay_sub = mv_relay.add_subparsers(dest="relay_command", required=True)
    mv_relay_get = mv_relay_sub.add_parser("get")
    mv_relay_get.set_defaults(func=cmd_mullvad_static, mullvad_args=("relay", "get"))
    mv_relay_list = mv_relay_sub.add_parser("list")
    mv_relay_list.set_defaults(func=cmd_mullvad_static, mullvad_args=("relay", "list"), timeout=120)
    mv_relay_update = mv_relay_sub.add_parser("update")
    mv_relay_update.set_defaults(func=cmd_mullvad_static, mullvad_args=("relay", "update"), timeout=120)
    mv_relay_location = mv_relay_sub.add_parser("location", help="Set country/city/hostname relay location")
    mv_relay_location.add_argument("location", nargs="+")
    mv_relay_location.set_defaults(func=cmd_mullvad_relay_location)
    mv_relay_ownership = mv_relay_sub.add_parser("ownership")
    mv_relay_ownership.add_argument("state", choices=["any", "owned", "rented"])
    mv_relay_ownership.set_defaults(func=lambda a: print_mullvad_result(["relay", "set", "ownership", a.state]))
    mv_relay_provider = mv_relay_sub.add_parser("provider")
    mv_relay_provider.add_argument("providers", nargs="+")
    mv_relay_provider.set_defaults(func=cmd_mullvad_relay_provider)
    mv_relay_multihop = mv_relay_sub.add_parser("multihop")
    mv_relay_multihop.add_argument("state", choices=["on", "off"])
    mv_relay_multihop.set_defaults(func=lambda a: print_mullvad_result(["relay", "set", "multihop", a.state]))

    mv_dns = mullvad_sub.add_parser("dns", help="Manage DNS settings")
    mv_dns_sub = mv_dns.add_subparsers(dest="dns_command", required=True)
    mv_dns_get = mv_dns_sub.add_parser("get")
    mv_dns_get.set_defaults(func=cmd_mullvad_static, mullvad_args=("dns", "get"))
    mv_dns_default = mv_dns_sub.add_parser("default")
    mv_dns_default.add_argument("--block-ads", action="store_true")
    mv_dns_default.add_argument("--block-trackers", action="store_true")
    mv_dns_default.add_argument("--block-malware", action="store_true")
    mv_dns_default.add_argument("--block-adult-content", action="store_true")
    mv_dns_default.add_argument("--block-gambling", action="store_true")
    mv_dns_default.add_argument("--block-social-media", action="store_true")
    mv_dns_default.set_defaults(func=cmd_mullvad_dns_default)
    mv_dns_custom = mv_dns_sub.add_parser("custom")
    mv_dns_custom.add_argument("servers", nargs="+")
    mv_dns_custom.set_defaults(func=cmd_mullvad_dns_custom)

    mv_tunnel = mullvad_sub.add_parser("tunnel", help="Manage tunnel settings")
    mv_tunnel_sub = mv_tunnel.add_subparsers(dest="tunnel_command", required=True)
    mv_tunnel_get = mv_tunnel_sub.add_parser("get")
    mv_tunnel_get.set_defaults(func=cmd_mullvad_static, mullvad_args=("tunnel", "get"))
    mv_tunnel_qr = mv_tunnel_sub.add_parser("quantum-resistant")
    mv_tunnel_qr.add_argument("state", choices=["on", "off"])
    mv_tunnel_qr.set_defaults(func=lambda a: print_mullvad_result(["tunnel", "set", "quantum-resistant", a.state]))
    mv_tunnel_ipv6 = mv_tunnel_sub.add_parser("ipv6")
    mv_tunnel_ipv6.add_argument("state", choices=["on", "off"])
    mv_tunnel_ipv6.set_defaults(func=lambda a: print_mullvad_result(["tunnel", "set", "ipv6", a.state]))
    mv_tunnel_rotate = mv_tunnel_sub.add_parser("rotate-key")
    mv_tunnel_rotate.set_defaults(func=cmd_mullvad_static, mullvad_args=("tunnel", "set", "rotate-key"))

    mv_split = mullvad_sub.add_parser("split-tunnel", help="Manage split tunneling")
    mv_split_sub = mv_split.add_subparsers(dest="split_command", required=True)
    mv_split_get = mv_split_sub.add_parser("get")
    mv_split_get.set_defaults(func=cmd_mullvad_static, mullvad_args=("split-tunnel", "get"))
    mv_split_set = mv_split_sub.add_parser("set")
    mv_split_set.add_argument("state", choices=["on", "off"])
    mv_split_set.set_defaults(func=lambda a: print_mullvad_result(["split-tunnel", "set", a.state]))
    mv_split_app = mv_split_sub.add_parser("app")
    mv_split_app.add_argument("action", choices=["add", "remove", "clear"])
    mv_split_app.add_argument("path", nargs="?")
    mv_split_app.set_defaults(func=cmd_mullvad_split_app)

    mv_ac = mullvad_sub.add_parser("anti-censorship", help="Manage anti-censorship settings")
    mv_ac_sub = mv_ac.add_subparsers(dest="anti_censorship_command", required=True)
    mv_ac_get = mv_ac_sub.add_parser("get")
    mv_ac_get.set_defaults(func=cmd_mullvad_static, mullvad_args=("anti-censorship", "get"))
    mv_ac_mode = mv_ac_sub.add_parser("mode")
    mv_ac_mode.add_argument("mode", choices=["auto", "off", "wireguard-port", "udp2tcp", "shadowsocks", "quic", "lwo"])
    mv_ac_mode.set_defaults(func=lambda a: print_mullvad_result(["anti-censorship", "set", "mode", a.mode]))

    mv_api = mullvad_sub.add_parser("api-access", help="Inspect Mullvad API access method")
    mv_api_sub = mv_api.add_subparsers(dest="api_access_command", required=True)
    mv_api_get = mv_api_sub.add_parser("get")
    mv_api_get.set_defaults(func=cmd_mullvad_static, mullvad_args=("api-access", "get"))
    mv_api_list = mv_api_sub.add_parser("list")
    mv_api_list.set_defaults(func=cmd_mullvad_static, mullvad_args=("api-access", "list"))

    mv_raw = mullvad_sub.add_parser("raw", help="Pass raw args to Mullvad CLI")
    mv_raw.add_argument("--timeout", type=int, default=60)
    mv_raw.add_argument("args", nargs=argparse.REMAINDER)
    mv_raw.set_defaults(func=cmd_mullvad_raw)

    ytdlp = sub.add_parser("yt-dlp", help="Manage yt-dlp")
    ytdlp_sub = ytdlp.add_subparsers(dest="ytdlp_command", required=True)

    ytdlp_install = ytdlp_sub.add_parser("install", help="Download official stable Windows yt-dlp.exe")
    ytdlp_install.set_defaults(func=cmd_ytdlp_install)

    ytdlp_version = ytdlp_sub.add_parser("version", help="Show yt-dlp version")
    ytdlp_version.set_defaults(func=cmd_ytdlp_version)

    plan = sub.add_parser("plan", help="Create a rights-aware batch manifest")
    plan.add_argument("urls", nargs="*", help="Source URL(s) to archive")
    plan.add_argument("--from-file", help="Text file with one source URL per line")
    plan.add_argument("--rights", required=True, help="Documented rights basis for this batch")
    plan.add_argument("--name", help="Batch name")
    plan.add_argument("--output", help="Output directory override")
    plan.add_argument("--max-height", type=int, help="Limit selected video height, for example 360 for smoke tests")
    plan.add_argument("--max-downloads", type=int, help="Stop after this many downloads")
    plan.add_argument("--max-filesize", help="Skip files larger than this yt-dlp size expression, for example 50M")
    plan.set_defaults(func=cmd_plan)

    smoke = sub.add_parser("smoke", help="Create and run curated validation batches")
    smoke_sub = smoke.add_subparsers(dest="smoke_command", required=True)
    smoke_plan = smoke_sub.add_parser("plan", help="Create the curated NASA Goddard smoke-test batch")
    smoke_plan.add_argument("--count", type=int, default=5)
    smoke_plan.add_argument("--name", default="nasa-goddard-smoke-pack")
    smoke_plan.add_argument("--output", help="Output directory override")
    smoke_plan.add_argument("--max-height", type=int, default=360)
    smoke_plan.add_argument("--max-filesize", default="75M")
    smoke_plan.set_defaults(func=cmd_smoke_plan)

    catalog = sub.add_parser("catalog", help="List known local batch manifests")
    catalog.set_defaults(func=cmd_catalog)

    preflight = sub.add_parser("preflight", help="Check a batch before running")
    preflight.add_argument("manifest", help="Path to batch manifest.json")
    preflight.add_argument("--no-require-connected", action="store_true", help="Do not fail solely because Mullvad is disconnected")
    preflight.add_argument("--no-production", action="store_true", help="Local harness only: skip production posture and anonymous-auth policy checks")
    preflight.set_defaults(func=cmd_preflight)

    verify = sub.add_parser("verify", help="Verify batch artifacts, reports, archive entries, and media files")
    verify.add_argument("manifest", help="Path to batch manifest.json")
    verify.add_argument("--allow-empty", action="store_true", help="Allow dry-run or planned batches with no artifacts yet")
    verify.add_argument("--no-probe", action="store_true", help="Skip ffprobe media validation")
    verify.set_defaults(func=cmd_verify)

    run = sub.add_parser("run", help="Run or dry-run a batch")
    run.add_argument("manifest", help="Path to batch manifest.json")
    run.add_argument("--dry-run", action="store_true", help="Simulate yt-dlp without downloading")
    run.add_argument("--show-output", action="store_true", help="Print raw yt-dlp output; dry-runs suppress it by default")
    run.add_argument("--yes", action="store_true", help="Allow real downloads after preflight")
    run.add_argument("--no-require-connected", action="store_true", help="Do not fail solely because Mullvad is disconnected")
    run.add_argument("--no-production", action="store_true", help="Diagnostics only. Real downloads refuse this flag.")
    run.add_argument("--recover-vpn", dest="recover_vpn", action="store_true", default=True, help="Recover Mullvad on tunnel/network failures")
    run.add_argument("--no-recover-vpn", dest="recover_vpn", action="store_false", help="Disable Mullvad recovery")
    run.add_argument("--vpn-recovery-attempts", type=int, default=2)
    run.add_argument("--vpn-recovery-wait", type=float, default=5.0)
    run.set_defaults(func=cmd_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    configure_console()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
