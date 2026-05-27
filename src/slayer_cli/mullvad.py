from __future__ import annotations

import time
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


@dataclass(frozen=True)
class RecoveryResult:
    ok: bool
    attempts: int
    messages: tuple[str, ...]


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


def reconnect() -> CommandResult:
    return run_mullvad("reconnect", timeout=120)


def set_lockdown(on: bool) -> CommandResult:
    return run_mullvad("lockdown-mode", "set", "on" if on else "off", timeout=60)


def recover_connection(*, attempts: int = 2, wait_seconds: float = 5.0) -> RecoveryResult:
    messages: list[str] = []
    current = status(verbose=True)
    if current.connected:
        return RecoveryResult(True, 0, ("Mullvad already connected.",))

    for attempt in range(1, attempts + 1):
        action = reconnect() if current.available else connect()
        output = "\n".join(part for part in [action.stdout, action.stderr] if part).strip()
        if output:
            messages.append(output)
        time.sleep(wait_seconds)
        current = status(verbose=True)
        if current.connected:
            messages.append(f"Mullvad connected after recovery attempt {attempt}.")
            return RecoveryResult(True, attempt, tuple(messages))
        messages.append(f"Mullvad still not connected after recovery attempt {attempt}.")

    return RecoveryResult(False, attempts, tuple(messages))


def redact_account_in_text(text: str, account_number: str | None) -> str:
    if not account_number:
        return text
    return text.replace(account_number, redact(account_number))
