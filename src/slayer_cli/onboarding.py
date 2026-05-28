from __future__ import annotations

import json
from pathlib import Path

from .doctor import Check, overall_ok
from .paths import PROJECT_ROOT


MULLVAD_WINDOWS_DOWNLOAD_URL = "https://mullvad.net/en/download/vpn/windows"
MULLVAD_ACCOUNT_URL = "https://mullvad.net/en/account/create"


def check_by_name(checks: list[Check]) -> dict[str, Check]:
    return {check.name: check for check in checks}


def command_line(command: str) -> str:
    return f"powershell -ExecutionPolicy Bypass -File scripts\\slayer.ps1 {command}"


def readiness_summary(checks: list[Check], *, require_connected: bool = True) -> str:
    return "READY" if overall_ok(checks, require_connected=require_connected) else "ACTION REQUIRED"


def next_setup_steps(checks: list[Check], *, require_connected: bool = True) -> list[str]:
    by_name = check_by_name(checks)
    steps: list[str] = []

    if not by_name.get("mullvad", Check("mullvad", False, "")).ok:
        steps.append(f"Install Mullvad VPN for Windows: {MULLVAD_WINDOWS_DOWNLOAD_URL}")
    if not by_name.get(".env account", Check(".env account", False, "")).ok:
        steps.append("Copy .env.example to .env and set MULLVAD_ACCOUNT_NUMBER.")
        steps.append(f"Create or recover a Mullvad account: {MULLVAD_ACCOUNT_URL}")
    if not by_name.get("yt-dlp", Check("yt-dlp", False, "")).ok:
        steps.append(command_line("yt-dlp install"))
    if not by_name.get("ffmpeg", Check("ffmpeg", False, "")).ok:
        steps.append("Install ffmpeg and make ffmpeg/ffprobe available on PATH.")
    if not by_name.get("yt-dlp JS runtime", Check("yt-dlp JS runtime", True, "")).ok:
        steps.append("Install Node.js or Deno so yt-dlp can solve modern YouTube JavaScript challenges.")
    if not by_name.get("mullvad connected", Check("mullvad connected", not require_connected, "")).ok:
        steps.append(command_line("mullvad login"))
        steps.append(command_line("setup production"))

    production_names = {
        "mullvad lockdown",
        "mullvad split tunnel off",
        "mullvad LAN sharing blocked",
        "mullvad auto-connect",
    }
    if any(not check.ok for check in checks if check.name in production_names):
        steps.append(command_line("setup production"))

    if not steps:
        steps.extend(
            [
                command_line("smoke plan --count 1 --name first-smoke"),
                command_line('preflight "batches\\...\\manifest.json"'),
                command_line('run "batches\\...\\manifest.json" --dry-run'),
                command_line('run "batches\\...\\manifest.json" --yes'),
                command_line('verify "batches\\...\\manifest.json"'),
                command_line('ledger "batches\\...\\manifest.json" --refresh'),
            ]
        )
    return dedupe_preserve_order(steps)


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value not in seen:
            unique.append(value)
            seen.add(value)
    return unique


def operator_interview_lines() -> list[str]:
    return [
        "Ask the user these before a real batch:",
        "1. What exact channel, playlist, or video URLs should be archived?",
        "2. Do you own the content, have permission, or have a license/public-domain basis?",
        "3. Do you have a rights evidence file to attach with --rights-file?",
        "4. Should this start bounded with --max-items, --max-height, --max-filesize, or --max-downloads?",
        "5. Where should outputs go, if not the batch downloads folder?",
        "6. Do you want inventory-only review before any media download?",
    ]


def first_batch_lines() -> list[str]:
    return [
        "Normal first batch flow:",
        command_line(
            'inventory "<channel-or-playlist-url>" --rights "<owned or authorized reason>" '
            '--rights-file ".\\rights-evidence.md" --name "<batch-name>" --max-items 25'
        ),
        command_line('ledger "batches\\...\\manifest.json"'),
        command_line('preflight "batches\\...\\manifest.json"'),
        command_line('run "batches\\...\\manifest.json" --dry-run'),
        command_line('run "batches\\...\\manifest.json" --yes'),
        command_line('verify "batches\\...\\manifest.json"'),
        command_line('ledger "batches\\...\\manifest.json" --refresh'),
    ]


def onboarding_payload(checks: list[Check], *, require_connected: bool = True) -> dict:
    return {
        "status": readiness_summary(checks, require_connected=require_connected),
        "checks": [{"name": check.name, "ok": check.ok, "detail": check.detail} for check in checks],
        "next_steps": next_setup_steps(checks, require_connected=require_connected),
        "docs": {
            "walkthrough": str(PROJECT_ROOT / "docs" / "WALKTHROUGH.md"),
            "sop": str(PROJECT_ROOT / "docs" / "SOP.md"),
            "safety": str(PROJECT_ROOT / "docs" / "SAFETY.md"),
            "examples": str(PROJECT_ROOT / "examples"),
        },
    }


def onboarding_text(checks: list[Check], *, require_connected: bool = True) -> str:
    payload = onboarding_payload(checks, require_connected=require_connected)
    lines = [
        "Legends YT-DLP Slayer Onboarding",
        f"Status: {payload['status']}",
        "",
        "Readiness checks:",
    ]
    for check in checks:
        marker = "PASS" if check.ok else "FAIL"
        lines.append(f"[{marker}] {check.name}: {check.detail}")

    lines.extend(["", "Next safe steps:"])
    for index, step in enumerate(payload["next_steps"], start=1):
        lines.append(f"{index}. {step}")

    lines.extend(["", *operator_interview_lines(), "", *first_batch_lines()])
    lines.extend(
        [
            "",
            "Reference docs:",
            f"- {payload['docs']['walkthrough']}",
            f"- {payload['docs']['sop']}",
            f"- {payload['docs']['safety']}",
            f"- {payload['docs']['examples']}",
            "",
            "Safety boundary: stop on source-side throttles, captchas, login challenges, account controls, or blocks. Do not rotate relays or accounts to continue through them.",
        ]
    )
    return "\n".join(lines)


def onboarding_json(checks: list[Check], *, require_connected: bool = True) -> str:
    return json.dumps(onboarding_payload(checks, require_connected=require_connected), indent=2)
