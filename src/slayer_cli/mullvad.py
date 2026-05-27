from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .envfile import redact
from .process import CommandResult, run_command
from .tools import find_mullvad


@dataclass(frozen=True)
class MullvadStatus:
    available: bool
    connected: bool
    raw: str
    error: str | None = None


def mullvad_path() -> Path | None:
    return find_mullvad().path


def run_mullvad(*args: str, timeout: int = 60) -> CommandResult:
    path = mullvad_path()
    if not path:
        return CommandResult(("mullvad", *args), 127, "", "Mullvad CLI not found")
    return run_command([path, *args], timeout=timeout)


def status(verbose: bool = False) -> MullvadStatus:
    args = ("status", "-v") if verbose else ("status",)
    result = run_mullvad(*args)
    raw = "\n".join(part for part in [result.stdout, result.stderr] if part).strip()
    if not result.ok:
        return MullvadStatus(False, False, raw, raw or "mullvad status failed")
    lowered = raw.lower()
    return MullvadStatus(True, lowered.startswith("connected"), raw)


def login(account_number: str) -> CommandResult:
    return run_mullvad("account", "login", account_number, timeout=120)


def connect() -> CommandResult:
    return run_mullvad("connect", timeout=120)


def set_lockdown(on: bool) -> CommandResult:
    return run_mullvad("lockdown-mode", "set", "on" if on else "off", timeout=60)


def redact_account_in_text(text: str, account_number: str | None) -> str:
    if not account_number:
        return text
    return text.replace(account_number, redact(account_number))
