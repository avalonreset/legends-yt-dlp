#!/usr/bin/env python3
"""Release readiness gate for legends-yt-dlp."""
from __future__ import annotations

import hashlib
import json
import os
import re
import struct
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SUPPORT.md",
    "CITATION.cff",
    "THIRD_PARTY_NOTICES.md",
    "AGENTS.md",
    "MANIFEST.in",
    "docs/AGENT-RECIPE.md",
    "docs/OPERATOR-ROUTING.md",
    ".legends-module",
    ".legends-router-pin",
    "skills/cto-legends/SKILL.md",
    "assets/banner.png",
    "assets/banner.webp",
    "assets/preview.png",
    "assets/social-preview.png",
    "assets/manifest.json",
]

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".local",
    "batches",
    "reports",
    "downloads",
    "cache",
    "secrets",
    "cookies",
}

TEXT_EXTS = {".py", ".md", ".toml", ".json", ".yml", ".yaml", ".cff", ".txt", ".in"}
FORBIDDEN_SCRIPT_EXTS = {".ps1", ".bat", ".cmd", ".vbs", ".ahk", ".sh", ".pem", ".key", ".p12", ".pfx"}

FORBIDDEN_PATTERNS = [
    r"(?i)[a-z]:\\{1,2}users\\{1,2}(?!\\|public\b|default\b|someone\b|you\b|<)",
    r"(?i)\.tail[a-z0-9]+\.ts\.net",
    r"(?i)nsec1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{30,}",
    r"(?i)sk_live_[a-z0-9]{12,}",
    r"(?i)rk_live_[a-z0-9]{12,}",
    r"gh[pousr]_[A-Za-z0-9]{20,}",
    r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----",
    r"CREATE_NO_WINDOW",
    r"0x08000000",
    r"(?i)-WindowStyle\s+Hidden",
    r"(?i)-ExecutionPolicy\s+Bypass",
    r"(?i)EncodedCommand",
    r"ctypes\.windll",
    r"(?i)CryptUnprotectData",
    r"(?i)GetAsyncKeyState",
    r"(?i)IndexedDB",
    r"shell\s*=\s*True",
]

REQUIRED_SKILL_PATTERNS = [
    r"^---\s*\nname:\s*cto-legends\s*\n",
    r"cto-legends handoff <module>",
    r"## Install law: suggest, never seize",
    r"Do not use em dashes",
]

CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ufffd]")


def check_png_chunks(path: Path, issues: list[str]) -> None:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        issues.append(f"{path.name}: invalid PNG header")
        return
    offset = 8
    while offset + 8 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8].decode("latin1", errors="replace")
        if chunk_type in {"tEXt", "zTXt", "iTXt", "eXIf"}:
            issues.append(f"{path.name}: forbidden metadata chunk {chunk_type}")
        if chunk_type == "IEND":
            break
        offset += 12 + length


def check_webp_chunks(path: Path, issues: list[str]) -> None:
    data = path.read_bytes()
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        issues.append(f"{path.name}: invalid WebP header")
        return
    offset = 12
    while offset + 8 <= len(data):
        tag = data[offset : offset + 4]
        length = struct.unpack("<I", data[offset + 4 : offset + 8])[0]
        if tag in {b"EXIF", b"XMP "}:
            issues.append(f"{path.name}: forbidden metadata marker {tag.decode('ascii').strip()}")
            break
        offset += 8 + length + (length % 2)


def check_asset_manifest(issues: list[str], expected_version: str | None) -> None:
    manifest = ROOT / "assets/manifest.json"
    if not manifest.is_file():
        return
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8-sig"))
    except ValueError as exc:
        issues.append(f"assets/manifest.json invalid: {exc}")
        return
    if expected_version and "version" in payload and payload["version"] != expected_version:
        issues.append(f"assets/manifest.json version mismatch: {payload['version']!r} != {expected_version!r}")
    if "files" in payload:
        for entry in payload["files"]:
            target = ROOT / "assets" / entry.get("name", "")
            if not target.is_file():
                issues.append(f"assets/manifest.json missing asset: {entry.get('name')}")
                continue
            raw = target.read_bytes()
            if len(raw) != entry.get("bytes"):
                issues.append(f"assets/manifest.json byte mismatch: {entry.get('name')}")
            if hashlib.sha256(raw).hexdigest() != entry.get("sha256"):
                issues.append(f"assets/manifest.json sha256 mismatch: {entry.get('name')}")
    elif "assets" in payload:
        for key, entry in payload["assets"].items():
            rel_path = entry.get("path", "")
            if not (ROOT / rel_path).is_file():
                issues.append(f"assets/manifest.json missing asset ({key}): {rel_path}")
    else:
        issues.append("assets/manifest.json missing 'files' or 'assets' section")


def check_knowledge_pack(issues: list[str]) -> None:
    pack_path = ROOT / "knowledge/pack.json"
    if not pack_path.is_file():
        return
    try:
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
    except Exception as exc:
        issues.append(f"knowledge/pack.json invalid JSON: {exc}")
        return
    for entry in pack.get("files", []):
        rel_path = entry.get("path", "")
        expected_sha = entry.get("sha256", "")
        target = ROOT / rel_path
        if not target.is_file():
            issues.append(f"knowledge/pack.json missing tracked file: {rel_path}")
            continue
        actual_sha = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual_sha != expected_sha:
            issues.append(
                f"knowledge/pack.json sha256 mismatch for {rel_path}: "
                f"expected {expected_sha}, got {actual_sha}"
            )


def main() -> int:
    issues: list[str] = []

    for rel in REQUIRED_FILES:
        if not (ROOT / rel).is_file():
            issues.append(f"Missing required file: {rel}")

    if (ROOT / ".legends-module").is_file():
        mod = (ROOT / ".legends-module").read_text(encoding="utf-8").strip()
        if mod != "legends-yt-dlp":
            issues.append(f".legends-module mismatch: {mod!r}")

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    init_py = (ROOT / "src/legends_ytdlp/__init__.py").read_text(encoding="utf-8")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    m_py = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
    m_init = re.search(r'^__version__\s*=\s*"([^"]+)"', init_py, re.M)
    m_cit = re.search(r'^version:\s*"?([^"\n]+)"?', citation, re.M)
    m_chg = re.search(r"^##\s+\[?v?(\d+\.\d+\.\d+)\]?", changelog, re.M)

    versions = {
        "pyproject.toml": m_py.group(1) if m_py else None,
        "__init__.py": m_init.group(1) if m_init else None,
        "CITATION.cff": m_cit.group(1).strip() if m_cit else None,
        "CHANGELOG.md": m_chg.group(1) if m_chg else None,
    }
    if len(set(versions.values())) != 1 or None in versions.values():
        issues.append(f"Version mismatch across files: {versions}")

    skill_files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.endswith(".egg-info")]
        for fn in filenames:
            path = Path(dirpath) / fn
            rel = path.relative_to(ROOT).as_posix()
            if fn == "SKILL.md":
                skill_files.append(rel)
            if path.suffix.lower() in FORBIDDEN_SCRIPT_EXTS:
                issues.append(f"Forbidden script extension in repo: {rel}")
            if path.suffix.lower() in TEXT_EXTS or fn in {"LICENSE", "NOTICE", ".legends-module", ".legends-router-pin"}:
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    issues.append(f"Non-UTF-8 file: {rel}")
                    continue
                if CONTROL_CHAR_RE.search(text):
                    issues.append(f"Control character or replacement character U+FFFD in {rel}")
                if path.suffix.lower() == ".md":
                    if "\u2014" in text or "\u2013" in text:
                        issues.append(f"Em/en-dash found in markdown file: {rel}")
                    for target_link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
                        if target_link.startswith(("https://", "http://", "mailto:", "#")):
                            continue
                        cleaned = unquote(target_link.split("#", 1)[0].split("?", 1)[0])
                        resolved = (path.parent / cleaned).resolve()
                        if not resolved.is_relative_to(ROOT.resolve()) or not resolved.exists():
                            issues.append(f"Broken or external local link in {rel}: {target_link}")
                if rel != "scripts/check_release.py":
                    for pat in FORBIDDEN_PATTERNS:
                        if re.search(pat, text):
                            issues.append(f"Forbidden pattern {pat!r} matched in {rel}")

    if skill_files != ["skills/cto-legends/SKILL.md"]:
        issues.append(f"One-Skill Rule violation: found SKILL.md at {skill_files}")
    else:
        skill_text = (ROOT / "skills/cto-legends/SKILL.md").read_text(encoding="utf-8")
        for pat in REQUIRED_SKILL_PATTERNS:
            if not re.search(pat, skill_text, re.M):
                issues.append(f"skills/cto-legends/SKILL.md missing required router content: {pat}")

    check_asset_manifest(issues, versions.get("pyproject.toml"))
    check_knowledge_pack(issues)

    for png in ("assets/banner.png", "assets/preview.png", "assets/social-preview.png"):
        p = ROOT / png
        if p.is_file():
            check_png_chunks(p, issues)
    webp = ROOT / "assets/banner.webp"
    if webp.is_file():
        check_webp_chunks(webp, issues)

    if issues:
        for issue in issues:
            print(f"ERROR: {issue}")
        return 1

    print("Release checks: PASS (0 issues)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
