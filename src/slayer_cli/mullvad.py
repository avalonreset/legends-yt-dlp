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


@dataclass(frozen=True)
class MullvadSetting:
    available: bool
    raw: str
    expected: str

    @property
    def value(self) -> str:
        for line in self.raw.splitlines():
            if ":" not in line:
                continue
            value = line.rsplit(":", 1)[1].strip().lower()
            if value:
                return value
        return self.raw.strip().lower()

    @property
    def ok(self) -> bool:
        return self.available and self.value == self.expected.lower()


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


def setting(*args: str, expected: str) -> MullvadSetting:
    result = run_mullvad(*args)
    raw = "\n".join(part for part in [result.stdout, result.stderr] if part).strip()
    return MullvadSetting(result.ok, raw or "unavailable", expected)


def lockdown_setting() -> MullvadSetting:
    return setting("lockdown-mode", "get", expected="on")


def split_tunnel_setting() -> MullvadSetting:
    return setting("split-tunnel", "get", expected="off")


def lan_setting() -> MullvadSetting:
    return setting("lan", "get", expected="block")


def auto_connect_setting() -> MullvadSetting:
    return setting("auto-connect", "get", expected="on")


def disconnect_refusal_reason(lockdown: MullvadSetting, *, force: bool = False) -> str | None:
    if force:
        return None
    if not lockdown.available:
        return "Refusing to disconnect because the Lockdown setting could not be verified. Use --force to override."
    if lockdown.ok:
        return "Refusing to disconnect while Lockdown is on. Use mullvad disconnect-test or --force."
    return None


def recovery_action_for_status(status: MullvadStatus) -> str:
    if not status.available:
        return "connect"
    if "disconnect" in status.raw.lower():
        return "connect"
    return "reconnect"


def recover_connection(*, attempts: int = 2, wait_seconds: float = 5.0) -> RecoveryResult:
    messages: list[str] = []
    lockdown = set_lockdown(True)
    lockdown_output = "\n".join(part for part in [lockdown.stdout, lockdown.stderr] if part).strip()
    if lockdown_output:
        messages.append(lockdown_output)
    current = status(verbose=True)
    if current.connected:
        messages.append("Mullvad already connected.")
        return RecoveryResult(True, 0, tuple(messages))

    for attempt in range(1, attempts + 1):
        action_name = recovery_action_for_status(current)
        action = reconnect() if action_name == "reconnect" else connect()
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
