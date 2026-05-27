from __future__ import annotations

from dataclasses import dataclass

from .envfile import read_env_file, redact
from .mullvad import status as mullvad_status
from .paths import PROJECT_ROOT
from .tools import ToolInfo, find_ffmpeg, find_mullvad, find_ytdlp


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


def tool_check(tool: ToolInfo) -> Check:
    if not tool.ok or not tool.path:
        return Check(tool.name, False, tool.detail)
    version = f" ({tool.version})" if tool.version else ""
    return Check(tool.name, True, f"{tool.path}{version}")


def run_doctor() -> list[Check]:
    env = read_env_file(PROJECT_ROOT / ".env")
    account = env.get("MULLVAD_ACCOUNT_NUMBER")
    checks: list[Check] = [
        tool_check(find_mullvad()),
        tool_check(find_ytdlp()),
        tool_check(find_ffmpeg()),
        Check(".env account", bool(account), f"MULLVAD_ACCOUNT_NUMBER={redact(account)}" if account else "missing"),
    ]

    mullvad = mullvad_status(verbose=True)
    if mullvad.available:
        checks.append(Check("mullvad connected", mullvad.connected, "connected" if mullvad.connected else "not connected"))
    else:
        checks.append(Check("mullvad connected", False, mullvad.error or "status unavailable"))

    return checks


def overall_ok(checks: list[Check], *, require_connected: bool = False) -> bool:
    for check in checks:
        if check.name == "mullvad connected" and not require_connected:
            continue
        if not check.ok:
            return False
    return True

