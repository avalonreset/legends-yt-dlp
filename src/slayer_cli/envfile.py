from __future__ import annotations

from pathlib import Path


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def redact(value: str | None, *, visible_tail: int = 4) -> str:
    if not value:
        return "<missing>"
    if len(value) <= visible_tail:
        return "*" * len(value)
    return ("*" * (len(value) - visible_tail)) + value[-visible_tail:]

