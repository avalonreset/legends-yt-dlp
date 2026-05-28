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
    load_manifest,
    only_mullvad_connection_failed,
    preflight_batch,
    preflight_ok,
    read_url_file,
    run_batch,
    write_run_report,
)
from .doctor import overall_ok, run_doctor
from .envfile import read_env_file, redact
from .inventory import create_batch_from_inventory
from .intelligence import (
    CRISPASR_ENGINE,
    build_vault,
    doctor_intelligence,
    import_crispasr_json,
    import_words as intelligence_import_words,
    init_intelligence,
    intelligence_status,
    make_clip_plan,
    render_clip_plan,
    search_words,
    transcribe_with_crispasr,
    write_search_results,
)
from .ledger import load_item_ledger, refresh_item_ledger, summarize_ledger
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
from .onboarding import onboarding_json, onboarding_text
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


def cmd_onboard(args: argparse.Namespace) -> int:
    require_connected = not args.basic
    checks = run_doctor(production=not args.basic)
    if args.json:
        print(onboarding_json(checks, require_connected=require_connected))
    else:
        print(onboarding_text(checks, require_connected=require_connected))
    if args.strict and not overall_ok(checks, require_connected=require_connected):
        return 1
    return 0


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
            rights_file=args.rights_file,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Batch created: {paths.root}")
    print(f"Manifest: {paths.manifest}")
    print(f"Item ledger: {paths.ledger}")
    print(f"yt-dlp config: {paths.config}")
    print(f"URL count: {len(urls)}")
    return 0


def cmd_inventory(args: argparse.Namespace) -> int:
    if not args.no_production:
        checks = run_doctor(production=True)
        if not overall_ok(checks, require_connected=True):
            for check in checks:
                print_check(check.name, check.ok, check.detail)
            print("Production doctor failed. Inventory did not start.", file=sys.stderr)
            return 1
    live_statuses = {value.lower() for value in args.live_status} if args.live_status else None
    try:
        paths, result = create_batch_from_inventory(
            source_url=args.source_url,
            rights_basis=args.rights,
            name=args.name,
            output_dir=args.output,
            max_height=args.max_height,
            max_downloads=args.max_downloads,
            max_filesize=args.max_filesize,
            max_items=args.max_items,
            live_statuses=live_statuses,
            rights_file=args.rights_file,
        )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"Inventory failed: {exc}", file=sys.stderr)
        return 1
    ledger_items = load_item_ledger(paths.ledger)
    summary = summarize_ledger(ledger_items)
    print(f"Inventory source: {result.source_url}")
    print(f"Inventory entries: {len(result.entries)}")
    print(f"Ledger items: {summary['items']}")
    print(f"Batch created: {paths.root}")
    print(f"Manifest: {paths.manifest}")
    print(f"Item ledger: {paths.ledger}")
    print(f"yt-dlp config: {paths.config}")
    if result.warnings:
        print("Warnings:")
        for warning in result.warnings[-10:]:
            print(f"- {warning}")
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
    print(f"Item ledger: {paths.ledger}")
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
    print(f"Ledger items: {summary.ledger_items}")
    print(f"Ledger statuses: {json.dumps(summary.ledger_statuses, sort_keys=True)}")
    print(f"Ledger warnings: {summary.ledger_warnings}")
    for check in checks:
        print_check(check.name, check.ok, check.detail)
    return 0 if all(check.ok for check in checks) else 1


def report_summary_lines(report_path: Path) -> list[str]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    ledger = report.get("ledger", {})
    lines = [
        f"Run report: {report_path}",
        f"Status: {report.get('status', 'unknown')}",
        f"Classification: {report.get('classification', 'unknown')}",
        f"Next action: {report.get('next_action', 'review report')}",
        f"Ledger: {ledger.get('items', 0)} item(s), statuses {json.dumps(ledger.get('statuses', {}), sort_keys=True)}",
    ]
    if report.get("diagnostic_tail"):
        lines.append(f"Diagnostics: {len(report['diagnostic_tail'])} line(s) in report")
    return lines


def print_run_summary(report_path: Path) -> None:
    try:
        lines = report_summary_lines(report_path)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Run report: {report_path}")
        print(f"Could not summarize report: {exc}", file=sys.stderr)
        return
    for line in lines:
        print(line)


def cmd_ledger(args: argparse.Namespace) -> int:
    try:
        manifest = load_manifest(Path(args.manifest))
        if args.refresh:
            refresh_item_ledger(manifest)
        ledger_path = Path(manifest["paths"]["item_ledger"])
        items = load_item_ledger(ledger_path)
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"Could not read item ledger: {exc}", file=sys.stderr)
        return 1
    statuses = {status.lower() for status in args.status} if args.status else None
    selected = [item for item in items if not statuses or str(item.get("status", "")).lower() in statuses]
    summary = summarize_ledger(items)
    if args.json:
        payload = {"manifest": str(Path(args.manifest)), "summary": summary, "items": selected[: args.limit]}
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print(f"Item ledger: {ledger_path}")
    print(f"Items: {summary['items']}")
    print(f"Statuses: {json.dumps(summary['statuses'], sort_keys=True)}")
    print(f"Downloaded: {summary['downloaded']}")
    print(f"Archived: {summary['archived']}")
    print(f"Warnings: {summary['warnings']}")
    print(f"Bytes: {summary['bytes']}")
    for item in selected[: args.limit]:
        position = item.get("position", "?")
        status = item.get("status", "unknown")
        title = item.get("title") or item.get("url") or item.get("id") or "<untitled>"
        print(f"{position}. {status} | {title}")
    if len(selected) > args.limit:
        print(f"... {len(selected) - args.limit} more item(s)")
    return 0


def cmd_intelligence_init(args: argparse.Namespace) -> int:
    try:
        target = init_intelligence(Path(args.manifest))
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"Could not initialize intelligence workspace: {exc}", file=sys.stderr)
        return 1
    print(f"Intelligence workspace initialized: {target.parent}")
    print(f"Manifest: {target}")
    return 0


def cmd_intelligence_doctor(args: argparse.Namespace) -> int:
    checks = doctor_intelligence(Path(args.manifest))
    for check in checks:
        print_check(check.name, check.ok, check.detail)
    return 0 if all(check.ok for check in checks) else 1


def cmd_intelligence_status(args: argparse.Namespace) -> int:
    status_payload = intelligence_status(Path(args.manifest))
    if args.json:
        print(json.dumps(status_payload, indent=2, ensure_ascii=False))
        return 0
    print(f"Intelligence root: {status_payload['root']}")
    print(f"Word files: {status_payload['word_files']}")
    print(f"Words: {status_payload['words']}")
    print(f"Search result files: {status_payload['search_files']}")
    print(f"Clip plans: {status_payload['clip_plans']}")
    print(f"Vault exists: {status_payload['vault_exists']}")
    return 0


def cmd_intelligence_import_words(args: argparse.Namespace) -> int:
    try:
        target, count = intelligence_import_words(
            Path(args.manifest),
            Path(args.input),
            video_id=args.video_id,
            item_id=args.item_id,
            media_path=args.media_path,
            engine=args.engine,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Could not import word ledger: {exc}", file=sys.stderr)
        return 1
    print(f"Imported words: {count}")
    print(f"Word ledger: {target}")
    return 0


def cmd_intelligence_import_crispasr(args: argparse.Namespace) -> int:
    try:
        target, count = import_crispasr_json(
            Path(args.manifest),
            Path(args.input),
            video_id=args.video_id,
            item_id=args.item_id,
            media_path=args.media_path,
            engine=args.engine,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Could not import CrispASR transcript: {exc}", file=sys.stderr)
        return 1
    print(f"Imported CrispASR words: {count}")
    print(f"Word ledger: {target}")
    return 0


def transcription_targets(args: argparse.Namespace) -> list[dict]:
    targets: list[dict] = []
    if args.media:
        media_path = Path(args.media)
        targets.append(
            {
                "id": args.video_id or args.item_id or media_path.stem,
                "item_id": args.item_id or args.video_id or media_path.stem,
                "output_path": str(media_path),
                "status": "manual",
            }
        )
    if args.all:
        manifest = load_manifest(Path(args.manifest))
        statuses = {status.lower() for status in args.status}
        ledger_path = Path(manifest["paths"]["item_ledger"])
        for item in load_item_ledger(ledger_path):
            media_path = item.get("output_path")
            status = str(item.get("status", "")).lower()
            if not media_path or status not in statuses:
                continue
            if not Path(str(media_path)).exists():
                continue
            targets.append(item)
    if args.limit is not None:
        targets = targets[: args.limit]
    return targets


def cmd_intelligence_transcribe(args: argparse.Namespace) -> int:
    if not args.media and not args.all:
        print("Choose --media for one file or --all for downloaded ledger items.", file=sys.stderr)
        return 2
    try:
        targets = transcription_targets(args)
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"Could not load transcription targets: {exc}", file=sys.stderr)
        return 1
    if not targets:
        print("No local media targets found for transcription.", file=sys.stderr)
        return 1

    manifest = Path(args.manifest)
    failures = 0
    for index, item in enumerate(targets, start=1):
        media_path = Path(str(item["output_path"]))
        video_id = args.video_id if args.media else str(item.get("id") or media_path.stem)
        item_id = args.item_id if args.media else str(item.get("id") or video_id)
        print(f"[{index}/{len(targets)}] Transcribing {video_id}: {media_path}")
        try:
            audio, transcript, words, count, results = transcribe_with_crispasr(
                manifest,
                media_path,
                video_id=video_id,
                item_id=item_id,
                model=args.model,
                backend=args.backend,
                threads=args.threads,
                vad=not args.no_vad,
                crispasr_path=Path(args.crispasr) if args.crispasr else None,
                timeout=args.timeout,
            )
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            failures += 1
            print(f"CrispASR transcription failed: {exc}", file=sys.stderr)
            continue
        failed = [result for result in results if not result.ok]
        if failed:
            failures += 1
            result = failed[-1]
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            print(f"Transcription command failed with exit code {result.returncode}", file=sys.stderr)
            continue
        print(f"Audio: {audio}")
        print(f"Transcript: {transcript}")
        print(f"Word ledger: {words}")
        print(f"Words: {count}")
    return 0 if failures == 0 else 1


def cmd_intelligence_search(args: argparse.Namespace) -> int:
    try:
        matches = search_words(
            Path(args.manifest),
            args.query,
            pad_start=args.pad_before,
            pad_end=args.pad_after,
            context_window=args.context,
        )
        results_path = write_search_results(Path(args.manifest), args.query, matches)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Intelligence search failed: {exc}", file=sys.stderr)
        return 1
    payload = {"query": args.query, "matches": matches[: args.limit], "match_count": len(matches), "results": str(results_path)}
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print(f"Query: {args.query}")
    print(f"Matches: {len(matches)}")
    print(f"Results: {results_path}")
    for match in matches[: args.limit]:
        print(
            f"{match['video_id']} {match['start']:.3f}-{match['end']:.3f} "
            f"(clip {match['clip_start']:.3f}-{match['clip_end']:.3f}) | {match['context']}"
        )
    if len(matches) > args.limit:
        print(f"... {len(matches) - args.limit} more match(es)")
    return 0


def cmd_intelligence_clips_plan(args: argparse.Namespace) -> int:
    try:
        plan_path, plan = make_clip_plan(Path(args.manifest), args.query, pad_start=args.pad_before, pad_end=args.pad_after)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Could not create clip plan: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return 0
    print(f"Clip plan: {plan_path}")
    print(f"Clips: {plan['clip_count']}")
    print(f"Montage output: {plan['montage_output']}")
    return 0


def cmd_intelligence_clips_render(args: argparse.Namespace) -> int:
    if not args.yes:
        print("Refusing to render media without --yes. Review the clip plan first.", file=sys.stderr)
        return 2
    try:
        results, montage = render_clip_plan(Path(args.plan))
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"Could not render clip plan: {exc}", file=sys.stderr)
        return 1
    for result in results:
        if not result.ok:
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            print(f"FFmpeg failed with exit code {result.returncode}", file=sys.stderr)
            return result.returncode or 1
    print(f"Rendered clips: {max(0, len(results) - 1)}")
    if montage:
        print(f"Montage: {montage}")
    return 0


def cmd_intelligence_vault_build(args: argparse.Namespace) -> int:
    try:
        vault, pages = build_vault(Path(args.manifest))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not build transcript vault: {exc}", file=sys.stderr)
        return 1
    print(f"Vault: {vault}")
    print(f"Transcript pages: {pages}")
    print(f"Index: {vault / 'index.md'}")
    return 0


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
            print_run_summary(report)
            return 0
        category = classify_run_failure(result)
        if category == "limit-reached":
            report = write_run_report(manifest, dry_run=args.dry_run, result=result, category=category, started=started, ended=ended)
            print("Configured download limit reached.")
            print_run_summary(report)
            return 0
        if not args.recover_vpn or category != "transient-network" or attempt >= args.vpn_recovery_attempts:
            if category == "source-block":
                print("Source-side block/throttle/login signal detected. Pausing without VPN relay/IP switching.", file=sys.stderr)
            report = write_run_report(manifest, dry_run=args.dry_run, result=result, category=category, started=started, ended=ended)
            print_run_summary(report)
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

    onboard = sub.add_parser("onboard", help="Show first-run setup status and next safe commands")
    onboard.add_argument("--basic", action="store_true", help="Skip production posture checks and only inspect basic dependencies")
    onboard.add_argument("--strict", action="store_true", help="Return non-zero until the shown readiness checks pass")
    onboard.add_argument("--json", action="store_true", help="Print machine-readable onboarding status")
    onboard.set_defaults(func=cmd_onboard)

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
    plan.add_argument("--rights-file", help="Optional local evidence file copied into the batch rights folder")
    plan.set_defaults(func=cmd_plan)

    inventory = sub.add_parser("inventory", help="Inventory a channel, playlist, or URL into a batch item ledger")
    inventory.add_argument("source_url", help="Channel, playlist, or source URL to inventory")
    inventory.add_argument("--rights", required=True, help="Documented rights basis for this batch")
    inventory.add_argument("--rights-file", help="Optional local evidence file copied into the batch rights folder")
    inventory.add_argument("--name", help="Batch name")
    inventory.add_argument("--output", help="Output directory override")
    inventory.add_argument("--max-items", type=int, help="Limit inventory collection, useful for smoke tests")
    inventory.add_argument("--live-status", action="append", default=[], help="Keep only entries with this yt-dlp live_status; repeatable")
    inventory.add_argument("--max-height", type=int, help="Limit selected video height when the batch later runs")
    inventory.add_argument("--max-downloads", type=int, help="Stop the later run after this many downloads")
    inventory.add_argument("--max-filesize", help="Skip files larger than this yt-dlp size expression, for example 50M")
    inventory.add_argument("--no-production", action="store_true", help="Diagnostics only: skip production Mullvad posture before inventory")
    inventory.set_defaults(func=cmd_inventory)

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

    ledger = sub.add_parser("ledger", help="Inspect or refresh a batch item ledger")
    ledger.add_argument("manifest", help="Path to batch manifest.json")
    ledger.add_argument("--refresh", action="store_true", help="Refresh ledger status from archive, info JSON, and media files")
    ledger.add_argument("--status", action="append", default=[], help="Show only items with this status; repeatable")
    ledger.add_argument("--limit", type=int, default=20, help="Maximum item rows to print")
    ledger.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    ledger.set_defaults(func=cmd_ledger)

    intelligence = sub.add_parser("intelligence", help="Analyze already-downloaded local media with word ledgers and clip plans")
    intelligence_sub = intelligence.add_subparsers(dest="intelligence_command", required=True)

    intelligence_init = intelligence_sub.add_parser("init", help="Create the intelligence workspace for a batch")
    intelligence_init.add_argument("manifest", help="Path to batch manifest.json")
    intelligence_init.set_defaults(func=cmd_intelligence_init)

    intelligence_doctor = intelligence_sub.add_parser("doctor", help="Check local intelligence prerequisites and workspace state")
    intelligence_doctor.add_argument("manifest", help="Path to batch manifest.json")
    intelligence_doctor.set_defaults(func=cmd_intelligence_doctor)

    intelligence_status_parser = intelligence_sub.add_parser("status", help="Summarize intelligence artifacts for a batch")
    intelligence_status_parser.add_argument("manifest", help="Path to batch manifest.json")
    intelligence_status_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    intelligence_status_parser.set_defaults(func=cmd_intelligence_status)

    for command_name in ["ingest-words", "import-words"]:
        import_words_parser = intelligence_sub.add_parser(command_name, help="Import a timestamped word JSONL/JSON file")
        import_words_parser.add_argument("manifest", help="Path to batch manifest.json")
        import_words_parser.add_argument("--input", required=True, help="JSONL file or JSON object/list containing timestamped words")
        import_words_parser.add_argument("--video-id", help="Video id to attach to imported words")
        import_words_parser.add_argument("--item-id", help="Item id to attach to imported words")
        import_words_parser.add_argument("--media-path", help="Local media path to attach to imported words")
        import_words_parser.add_argument("--engine", default="imported", help="Source engine label")
        import_words_parser.set_defaults(func=cmd_intelligence_import_words)

    import_crispasr = intelligence_sub.add_parser("import-crispasr", help="Import CrispASR full JSON output into the Slayer word ledger")
    import_crispasr.add_argument("manifest", help="Path to batch manifest.json")
    import_crispasr.add_argument("--input", required=True, help="CrispASR -ojf JSON output")
    import_crispasr.add_argument("--video-id", help="Video id to attach to imported words")
    import_crispasr.add_argument("--item-id", help="Item id to attach to imported words")
    import_crispasr.add_argument("--media-path", help="Local media path to attach to imported words")
    import_crispasr.add_argument("--engine", default=CRISPASR_ENGINE, help="Source engine label")
    import_crispasr.set_defaults(func=cmd_intelligence_import_crispasr)

    transcribe = intelligence_sub.add_parser("transcribe", help="Run the ready-made CrispASR Parakeet backend on local media")
    transcribe.add_argument("manifest", help="Path to batch manifest.json")
    target_group = transcribe.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--media", help="Transcribe one local media file")
    target_group.add_argument("--all", action="store_true", help="Transcribe all downloaded ledger items with local media files")
    transcribe.add_argument("--video-id", help="Video id for --media mode")
    transcribe.add_argument("--item-id", help="Item id for --media mode")
    transcribe.add_argument("--status", action="append", default=["downloaded", "archived", "verified"], help="Ledger status to include with --all; repeatable")
    transcribe.add_argument("--limit", type=int, help="Maximum number of media files to transcribe")
    transcribe.add_argument("--crispasr", help="Path to crispasr.exe; defaults to CRISPASR_CLI, .local/bin, or PATH")
    transcribe.add_argument("--model", default="auto", help="CrispASR model path or auto")
    transcribe.add_argument("--backend", default="parakeet", help="CrispASR backend name")
    transcribe.add_argument("--threads", type=int, help="Worker threads for CrispASR")
    transcribe.add_argument("--no-vad", action="store_true", help="Do not pass --vad to CrispASR")
    transcribe.add_argument("--timeout", type=int, default=60 * 60 * 4, help="Per-file ASR timeout in seconds")
    transcribe.set_defaults(func=cmd_intelligence_transcribe)

    intelligence_search = intelligence_sub.add_parser("search", help="Exact word/phrase search over imported word ledgers")
    intelligence_search.add_argument("manifest", help="Path to batch manifest.json")
    intelligence_search.add_argument("query", help="Exact word or phrase to find")
    intelligence_search.add_argument("--pad-before", type=float, default=0.5, help="Clip padding before each match in seconds")
    intelligence_search.add_argument("--pad-after", type=float, default=0.75, help="Clip padding after each match in seconds")
    intelligence_search.add_argument("--context", type=int, default=8, help="Context words to show around each match")
    intelligence_search.add_argument("--limit", type=int, default=20, help="Maximum rows to print")
    intelligence_search.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    intelligence_search.set_defaults(func=cmd_intelligence_search)

    intelligence_clips = intelligence_sub.add_parser("clips", help="Plan or render clips from word-ledger matches")
    intelligence_clips_sub = intelligence_clips.add_subparsers(dest="clips_command", required=True)
    clips_plan = intelligence_clips_sub.add_parser("plan", help="Create a reviewable FFmpeg clip plan")
    clips_plan.add_argument("manifest", help="Path to batch manifest.json")
    clips_plan.add_argument("--query", required=True, help="Exact word or phrase to clip")
    clips_plan.add_argument("--pad-before", type=float, default=0.5, help="Clip padding before each match in seconds")
    clips_plan.add_argument("--pad-after", type=float, default=0.75, help="Clip padding after each match in seconds")
    clips_plan.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    clips_plan.set_defaults(func=cmd_intelligence_clips_plan)

    clips_render = intelligence_clips_sub.add_parser("render", help="Render a reviewed clip plan with FFmpeg")
    clips_render.add_argument("plan", help="Path to clip-plan.json")
    clips_render.add_argument("--yes", action="store_true", help="Allow local media writes")
    clips_render.set_defaults(func=cmd_intelligence_clips_render)

    intelligence_vault = intelligence_sub.add_parser("vault", help="Build transcript vault pages from word ledgers")
    intelligence_vault_sub = intelligence_vault.add_subparsers(dest="vault_command", required=True)
    for command_name in ["build", "export"]:
        vault_build = intelligence_vault_sub.add_parser(command_name, help="Build Obsidian-compatible transcript pages")
        vault_build.add_argument("manifest", help="Path to batch manifest.json")
        vault_build.set_defaults(func=cmd_intelligence_vault_build)

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
