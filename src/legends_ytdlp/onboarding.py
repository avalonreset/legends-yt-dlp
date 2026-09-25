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
    return f"powershell -ExecutionPolicy Bypass -File scripts\\legends-yt-dlp.ps1 {command}"


def readiness_summary(checks: list[Check], *, require_connected: bool = False) -> str:
    return "READY" if overall_ok(checks, require_connected=require_connected) else "ACTION REQUIRED"


def next_setup_steps(checks: list[Check], *, require_connected: bool = False, with_vpn: bool = False) -> list[str]:
    by_name = check_by_name(checks)
    steps: list[str] = []

    if with_vpn:
        if not by_name.get("mullvad", Check("mullvad", False, "")).ok:
            steps.append(f"Install Mullvad VPN for Windows: {MULLVAD_WINDOWS_DOWNLOAD_URL}")
        if not by_name.get(".env account", Check(".env account", False, "")).ok:
            steps.append("Copy .env.example to .env and set MULLVAD_ACCOUNT_NUMBER.")
            steps.append(f"Create or recover a Mullvad account: {MULLVAD_ACCOUNT_URL}")

    ytdlp_check = by_name.get("yt-dlp", Check("yt-dlp", False, ""))
    if not ytdlp_check.ok:
        command = "yt-dlp update" if "days old" in ytdlp_check.detail else "yt-dlp install"
        steps.append(command_line(command))
    if not by_name.get("ffmpeg", Check("ffmpeg", False, "")).ok:
        steps.append("Install ffmpeg and make ffmpeg/ffprobe available on PATH.")
    if not by_name.get("yt-dlp JS runtime", Check("yt-dlp JS runtime", True, "")).ok:
        steps.append("Install Node.js or Deno so yt-dlp can solve modern YouTube JavaScript challenges.")
    if with_vpn and not by_name.get("mullvad connected", Check("mullvad connected", not require_connected, "")).ok:
        steps.append(command_line("mullvad login"))
        steps.append(command_line("setup production"))

    production_names = {
        "mullvad lockdown",
        "mullvad split tunnel off",
        "mullvad LAN sharing blocked",
        "mullvad auto-connect",
    }
    if with_vpn and any(not check.ok for check in checks if check.name in production_names):
        steps.append(command_line("setup production"))

    vpn_hint = (
        "Optional: for VPN-guarded runs, install Mullvad VPN, set MULLVAD_ACCOUNT_NUMBER, "
        + command_line("setup production")
        + ", then pass --with-vpn to plan, preflight, and run."
    )
    if not steps:
        steps.extend(
            [
                command_line('smoke plan --url "<authorized-video-url>" --name first-smoke'),
                command_line('preflight "batches\\...\\manifest.json"'),
                command_line('run "batches\\...\\manifest.json" --dry-run'),
                command_line('run "batches\\...\\manifest.json" --yes'),
                command_line('verify "batches\\...\\manifest.json"'),
                command_line('ledger "batches\\...\\manifest.json" --refresh'),
            ]
        )
    if not with_vpn:
        steps.append(vpn_hint)
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
        "2. Remind them to use material only when they have rights, permission, fair use, or another lawful basis.",
        "3. Do they want to attach an optional rights note or evidence file with --rights/--rights-file?",
        "4. Should this start bounded with --max-items, --max-height, --max-filesize, or --max-downloads?",
        "5. Where should outputs go, if not the batch downloads folder?",
        "6. Should outputs use one batch folder, uploader folders, or a flat folder?",
        "7. Do you want inventory-only review before any media download?",
    ]


def first_batch_lines() -> list[str]:
    return [
        "Normal first batch flow:",
        command_line(
            'inventory "<channel-or-playlist-url>" --rights-file ".\\rights-evidence.md" '
            '--name "<batch-name>" --max-items 25'
        ),
        command_line('ledger "batches\\...\\manifest.json"'),
        command_line('preflight "batches\\...\\manifest.json"'),
        command_line('run "batches\\...\\manifest.json" --dry-run'),
        command_line('run "batches\\...\\manifest.json" --yes'),
        command_line('verify "batches\\...\\manifest.json"'),
        command_line('ledger "batches\\...\\manifest.json" --refresh'),
    ]


def onboarding_payload(checks: list[Check], *, require_connected: bool = False, with_vpn: bool = False) -> dict:
    return {
        "status": readiness_summary(checks, require_connected=require_connected),
        "checks": [{"name": check.name, "ok": check.ok, "detail": check.detail} for check in checks],
        "next_steps": next_setup_steps(checks, require_connected=require_connected, with_vpn=with_vpn),
        "docs": {
            "walkthrough": str(PROJECT_ROOT / "docs" / "WALKTHROUGH.md"),
            "sop": str(PROJECT_ROOT / "docs" / "SOP.md"),
            "safety": str(PROJECT_ROOT / "docs" / "SAFETY.md"),
            "examples": str(PROJECT_ROOT / "examples"),
        },
    }


def onboarding_text(checks: list[Check], *, require_connected: bool = False, with_vpn: bool = False) -> str:
    payload = onboarding_payload(checks, require_connected=require_connected, with_vpn=with_vpn)
    lines = [
        "Legends YT-DLP Onboarding",
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


def onboarding_json(checks: list[Check], *, require_connected: bool = False, with_vpn: bool = False) -> str:
    return json.dumps(onboarding_payload(checks, require_connected=require_connected, with_vpn=with_vpn), indent=2)
