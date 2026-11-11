from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


_ACCOUNT_RE = re.compile(r"\b\d{16}\b")


def redact_sensitive_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return _ACCOUNT_RE.sub(lambda match: ("*" * 12) + match.group(0)[-4:], str(value))


@dataclass(frozen=True)
class CommandResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def run_command(args: Iterable[str | Path], *, timeout: int = 60) -> CommandResult:
    normalized = tuple(str(arg) for arg in args)
    safe_args = tuple(redact_sensitive_text(arg) for arg in normalized)
    try:
        completed = subprocess.run(
            normalized,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        out = redact_sensitive_text(exc.stdout).strip()
        err = redact_sensitive_text(exc.stderr).strip()
        timeout_msg = f"Command timed out after {timeout}s"
        stderr = f"{err}\n{timeout_msg}".strip() if err else timeout_msg
        return CommandResult(
            args=safe_args,
            returncode=124,
            stdout=out,
            stderr=stderr,
        )
    return CommandResult(
        args=safe_args,
        returncode=completed.returncode,
        stdout=redact_sensitive_text(completed.stdout).strip(),
        stderr=redact_sensitive_text(completed.stderr).strip(),
    )


