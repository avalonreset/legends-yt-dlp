"""Offline resource discovery for wheel installs and source checkouts."""
from __future__ import annotations

import json
import os
import re
from hashlib import sha256
from importlib import resources as importlib_resources
from pathlib import Path, PureWindowsPath
from typing import Any

from . import __version__

DATA_PACKAGE = "legends_youtube._data"
KNOWLEDGE_RELATIVE = Path("knowledge")
PACK_MANIFEST_RELATIVE = Path("knowledge") / "youtube" / "pack.json"
VAULT_RELATIVE = Path("knowledge") / "youtube" / "vault"
PACK_SCHEMA = "legends.knowledge-pack/v1"
PACK_MODULE = "legends-youtube"
RECIPE_CANDIDATES = ("docs/AGENT-RECIPE.md", "docs/KNOWLEDGE-PACK.md")
LIST_LIMIT = 1000
MANIFEST_LIMIT_BYTES = 1024 * 1024
VAULT_FILE_LIMIT_BYTES = 8 * 1024 * 1024
VAULT_FILE_COUNT_LIMIT = 500


def _package_root() -> Path | None:
    try:
        base = importlib_resources.files(DATA_PACKAGE)
    except (ModuleNotFoundError, ImportError):
        return None
    try:
        path = Path(os.fspath(base))
    except TypeError:
        return None
    return path if path.is_dir() else None


def _checkout_root() -> Path | None:
    here = Path(__file__).resolve()
    for root in (here.parents[1], here.parents[2]):
        marker = root / "pyproject.toml"
        try:
            if not marker.is_file():
                continue
            text = marker.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            continue
        if "legends-youtube" in text:
            return root
    return None


def _read_manifest(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        raw = path.read_bytes()
    except OSError:
        return None, "pack manifest is unreadable"
    if len(raw) > MANIFEST_LIMIT_BYTES:
        return None, "pack manifest exceeds the size limit"
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError):
        return None, "pack manifest is not valid JSON"
    if not isinstance(data, dict):
        return None, "pack manifest must be a JSON object"
    return data, None


def _bounded_parts(value: Any) -> list[str] | None:
    if not isinstance(value, str) or not value or len(value) > 256:
        return None
    if "\\" in value or value.startswith("/") or ":" in value or "\x00" in value:
        return None
    if PureWindowsPath(value).drive:
        return None
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return None
    return parts


def _safe_join(base: Path, parts: list[str]) -> Path | None:
    node = base
    for part in parts:
        node = node / part
        if node.is_symlink():
            return None
    try:
        anchor = base.resolve()
        resolved = node.resolve()
    except OSError:
        return None
    if not resolved.is_relative_to(anchor):
        return None
    return node


def _sha256_of(path: Path) -> str | None:
    digest = sha256()
    total = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > VAULT_FILE_LIMIT_BYTES:
                return None
            digest.update(chunk)
    return digest.hexdigest()


def verify_pack(vault_dir: Path, manifest: dict[str, Any]) -> tuple[int, str | None]:
    if manifest.get("schema") != PACK_SCHEMA:
        return 0, "pack manifest schema mismatch"
    if manifest.get("module") != PACK_MODULE:
        return 0, "pack manifest module mismatch"
    if manifest.get("version") != __version__:
        return 0, "pack manifest version mismatch"
    entry = _bounded_parts(manifest.get("entrypoint"))
    if entry is None:
        return 0, "pack entrypoint is not a bounded relative path"
    entry_target = _safe_join(vault_dir, entry)
    if entry_target is None:
        return 0, "pack entrypoint escapes the vault"
    if not entry_target.is_file():
        return 0, "pack entrypoint is missing"
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        return 0, "pack manifest declares no files"
    if len(files) > VAULT_FILE_COUNT_LIMIT:
        return 0, "pack manifest declares too many files"
    seen: set[str] = set()
    for item in files:
        if not isinstance(item, dict):
            return 0, "pack manifest file entry is malformed"
        parts = _bounded_parts(item.get("path"))
        digest = item.get("sha256")
        if parts is None or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            return 0, "pack manifest file entry is malformed"
        key = "/".join(parts)
        if key in seen:
            return 0, "pack manifest declares a duplicate file"
        seen.add(key)
        target = _safe_join(vault_dir, parts)
        if target is None:
            return 0, f"pack file path escapes the vault: {key}"
        if not target.is_file():
            return 0, f"pack file is missing: {key}"
        try:
            actual = _sha256_of(target)
        except OSError:
            return 0, f"pack file is unreadable: {key}"
        if actual is None:
            return 0, f"pack file exceeds the size limit: {key}"
        if actual != digest.lower():
            return 0, f"pack file hash mismatch: {key}"
    if "/".join(entry) not in seen:
        return 0, "pack entrypoint is not a declared file"
    return len(files), None


def _list_files(pack_dir: Path) -> tuple[list[str], bool]:
    found: list[str] = []
    truncated = False
    stack = [pack_dir]
    visited = 0
    while stack:
        node = stack.pop()
        visited += 1
        if visited > 5000:
            return sorted(found), True
        try:
            children = sorted(node.iterdir(), key=lambda entry: entry.name)
        except OSError:
            return sorted(found), True
        for child in children:
            name = child.name
            if not name or name.startswith(".") or child.is_symlink():
                continue
            if child.is_dir():
                stack.append(child)
            elif child.is_file():
                found.append(str(child))
                if len(found) >= LIST_LIMIT:
                    return sorted(found), True
    return sorted(found), truncated


def _resolve_recipe(root: Path, manifest: dict[str, Any] | None) -> Path | None:
    candidates: list[str] = []
    if isinstance(manifest, dict) and isinstance(manifest.get("recipe"), str):
        candidates.append(manifest["recipe"])
    candidates.extend(RECIPE_CANDIDATES)
    for candidate in candidates:
        parts = _bounded_parts(candidate)
        if parts is None:
            continue
        path = _safe_join(root, parts)
        if path is not None and path.is_file():
            return path
    return None


def resolve() -> dict[str, Any]:
    root = _package_root()
    source = "package_data"
    if root is None:
        root = _checkout_root()
        source = "checkout"
    if root is None:
        return {
            "source": "missing",
            "root": None,
            "recipe": None,
            "pack_dir": None,
            "pack_manifest": None,
            "pack_files": [],
            "truncated": False,
            "manifest": None,
            "verified_files": 0,
            "complete": False,
            "note": None,
        }
    manifest_path = root / PACK_MANIFEST_RELATIVE
    manifest, note = (None, None)
    pack_manifest = None
    if manifest_path.is_file() and not manifest_path.is_symlink():
        pack_manifest = str(manifest_path)
        manifest, note = _read_manifest(manifest_path)
    pack_dir = root / KNOWLEDGE_RELATIVE
    pack_dir_out = str(pack_dir) if pack_dir.is_dir() else None
    pack_files, truncated = _list_files(pack_dir) if pack_dir_out else ([], False)
    recipe = _resolve_recipe(root, manifest)
    verified = 0
    if pack_manifest is not None and manifest is not None and pack_dir_out:
        verified, verify_note = verify_pack(pack_dir / "youtube" / "vault", manifest)
        if verify_note is not None:
            note = verify_note
    if note is None and pack_manifest is None:
        note = "pack manifest not found"
    if note is None and recipe is None:
        note = "entry recipe not found"
    return {
        "source": source,
        "root": str(root),
        "recipe": str(recipe) if recipe else None,
        "pack_dir": pack_dir_out,
        "pack_manifest": pack_manifest,
        "pack_files": pack_files,
        "truncated": truncated,
        "manifest": manifest,
        "verified_files": verified,
        "complete": note is None,
        "note": note,
    }


def status() -> dict[str, Any]:
    try:
        found = resolve()
    except OSError:
        return {"status": "unreadable", "source": "unknown"}
    if found["complete"]:
        return {
            "status": "available",
            "source": found["source"],
            "pack_files": len(found["pack_files"]),
            "verified_files": found["verified_files"],
        }
    if found["source"] == "missing":
        return {"status": "missing", "source": "missing"}
    return {"status": "incomplete", "source": found["source"]}
