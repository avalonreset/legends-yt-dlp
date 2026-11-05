from __future__ import annotations

from dataclasses import dataclass

from .envfile import read_env_file, redact
from .mullvad import (
    auto_connect_setting,
    lan_setting,
    lockdown_setting,
    split_tunnel_setting,
    status as mullvad_status,
)
from .paths import PROJECT_ROOT
from .tools import ToolInfo, find_ffmpeg, find_js_runtime, find_mullvad, find_ytdlp


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = True


def tool_check(tool: ToolInfo, *, required: bool = True) -> Check:
    if not tool.ok or not tool.path:
        if not tool.path and not required:
            return Check(
                tool.name,
                True,
                f"{tool.detail} (optional external tool until live capture)",
                required=False,
            )
        return Check(tool.name, False, tool.detail, required=required)
    version = f" ({tool.version})" if tool.version else ""
    return Check(tool.name, True, f"{tool.path}{version}", required=required)


def mullvad_setting_check(name: str, raw: str, ok: bool, expected: str) -> Check:
    detail = raw.replace("\n", " | ")
    if not detail:
        detail = f"expected {expected}"
    return Check(name, ok, detail)


def run_doctor(
    *,
    production: bool = False,
    with_vpn: bool = False,
    offline: bool = False,
    require_tools: bool = False,
) -> list[Check]:
    need_tools = bool(production or require_tools)
    checks = [
        tool_check(find_ytdlp(), required=need_tools),
        tool_check(find_ffmpeg(), required=need_tools),
    ]
    if offline or not (with_vpn or production):
        return checks

    env = read_env_file(PROJECT_ROOT / ".env")
    account = env.get("MULLVAD_ACCOUNT_NUMBER")
    checks.extend([
        tool_check(find_mullvad(), required=True),
        Check(".env account", bool(account), f"MULLVAD_ACCOUNT_NUMBER={redact(account)}" if account else "missing"),
    ])

    mullvad = mullvad_status(verbose=True)
    if mullvad.available:
        checks.append(Check("mullvad connected", mullvad.connected, "connected" if mullvad.connected else "not connected"))
    else:
        checks.append(Check("mullvad connected", False, mullvad.error or "status unavailable"))

    if production:
        checks.append(tool_check(find_js_runtime(), required=True))
        for name, state in [
            ("mullvad lockdown", lockdown_setting()),
            ("mullvad split tunnel off", split_tunnel_setting()),
            ("mullvad LAN sharing blocked", lan_setting()),
            ("mullvad auto-connect", auto_connect_setting()),
        ]:
            checks.append(mullvad_setting_check(name, state.raw, state.ok, state.expected))

    return checks


def overall_ok(checks: list[Check], *, require_connected: bool = False) -> bool:
    for check in checks:
        if not require_connected and (check.name.startswith("mullvad") or check.name == ".env account"):
            continue
        if not check.required:
            continue
        if not check.ok:
            return False
    return True
