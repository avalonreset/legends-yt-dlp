from __future__ import annotations

import os
from pathlib import Path

from .paths import MAX_ENV_BYTES, PROJECT_ROOT, assert_not_symlink, read_safe_text


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    assert_not_symlink(path)
    if not path.exists():
        return values

    text = read_safe_text(path, max_bytes=MAX_ENV_BYTES)
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def resolve_mullvad_account(*, env_reader=read_env_file) -> str | None:
    direct = os.environ.get("MULLVAD_ACCOUNT_NUMBER", "").strip()
    if direct:
        return direct
    custom_env = os.environ.get("LEGENDS_YTDLP_ENV_FILE", "").strip()
    if custom_env:
        candidate = Path(custom_env).expanduser()
        value = env_reader(candidate).get("MULLVAD_ACCOUNT_NUMBER")
        if value:
            return value
    cwd_env = Path.cwd() / ".env"
    if cwd_env.is_file() and not cwd_env.is_symlink():
        try:
            same_as_project = cwd_env.resolve() == (PROJECT_ROOT / ".env").resolve()
        except OSError:
            same_as_project = False
        if not same_as_project:
            value = env_reader(cwd_env).get("MULLVAD_ACCOUNT_NUMBER")
            if value:
                return value
    return env_reader(PROJECT_ROOT / ".env").get("MULLVAD_ACCOUNT_NUMBER")


def redact(value: str | None, *, visible_tail: int = 4) -> str:
    if not value:
        return "<missing>"
    if len(value) <= visible_tail:
        return "*" * len(value)
    return ("*" * (len(value) - visible_tail)) + value[-visible_tail:]


