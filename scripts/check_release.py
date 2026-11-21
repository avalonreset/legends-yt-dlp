#!/usr/bin/env python3
"""Offline release checks for links, private residue, EDR hygiene, versions, and required artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKIP = {
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
    ".integration",
    "batches",
    "reports",
    "downloads",
    "cache",
    "secrets",
    "cookies",
}
REQUIRED = [
    "README.md",
    "LICENSE",
    "NOTICE",
    "NOTICE.md",
    "THIRD_PARTY_NOTICES.md",
    "CITATION.cff",
    ".legends-module",
    ".legends-router-pin",
    "AGENTS.md",
    "SECURITY.md",
    "SUPPORT.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "CHANGELOG.md",
    "MANIFEST.in",
    "setup.py",
    "wiki/index.md",
    "references/sources.md",
    "docs/AGENT-RECIPE.md",
    "docs/OPERATOR-ROUTING.md",
    "docs/KNOWLEDGE-PACK.md",
    "docs/RELEASE.md",
    "docs/catalog-entry.candidate.json",
    "docs/router-provenance.json",
    "templates/private-operation-receipt.md",
    "skills/cto-legends/SKILL.md",
    "knowledge/youtube/pack.json",
    "assets/banner.png",
    "assets/banner.webp",
    "assets/preview.png",
    "assets/social-preview.png",
    "assets/manifest.json",
]
TEXT_SUFFIXES = {".md", ".py", ".json", ".toml", ".yml", ".yaml", ".in", ".txt", ".cfg", ".ini", ".cff"}
FORBIDDEN = [
    r"(?i)[a-z]:\\{1,2}users\\{1,2}(?!\\|public\b|default\b|someone\b|you\b|<)",
    r"(?i)\.tail[a-z0-9]+\.ts\.net",
    r"(?i)nsec1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{30,}",
    r"(?i)sk_live_[a-z0-9]{12,}",
    r"(?i)rk_live_[a-z0-9]{12,}",
    r"gh[pousr]_[A-Za-z0-9]{20,}",
    r"ya29\.[A-Za-z0-9._-]{16,}",
    r"1//[A-Za-z0-9._-]{20,}",
    r"AIza[0-9A-Za-z_-]{20,}",
    r"GOCSPX-[A-Za-z0-9_-]{16,}",
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
FORBIDDEN_FILES = {".pem", ".key", ".p12", ".pfx", ".ps1", ".bat", ".cmd", ".vbs", ".ahk", ".sh"}
PNG_METADATA_CHUNKS = {"tEXt", "iTXt", "zTXt", "eXIf"}
WEBP_METADATA_CHUNKS = {b"EXIF", b"XMP "}
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ufffd]")
REQUIRED_SKILL_PATTERNS = [
    r"^---\s*\nname:\s*cto-legends\s*\n",
    r"cto-legends handoff <module>",
    r"## Install law: suggest, never seize",
    r"Do not use em dashes",
]


def image_metadata_issues(path: Path) -> list[str]:
    """Flag raster metadata chunks that can carry authoring residue."""
    try:
        raw = path.read_bytes()
    except OSError:
        return [f"Cannot read image: {path}"]
    issues: list[str] = []
    suffix = path.suffix.lower()
    if suffix == ".png":
        if raw[:8] != b"\x89PNG\r\n\x1a\n":
            return [f"Not a PNG file: {path}"]
        offset = 8
        while offset + 8 <= len(raw):
            length = struct.unpack(">I", raw[offset : offset + 4])[0]
            chunk = raw[offset + 4 : offset + 8]
            try:
                name = chunk.decode("latin1")
            except UnicodeError:
                break
            if name in PNG_METADATA_CHUNKS:
                issues.append(f"Image metadata chunk {name} in {path.name}; strip authoring residue.")
            if name == "IEND":
                break
            offset += 12 + length
    elif suffix == ".webp":
        if raw[:4] != b"RIFF" or raw[8:12] != b"WEBP":
            return [f"Not a WebP file: {path}"]
        offset = 12
        while offset + 8 <= len(raw):
            tag = raw[offset : offset + 4]
            length = struct.unpack("<I", raw[offset + 4 : offset + 8])[0]
            if tag in WEBP_METADATA_CHUNKS:
                issues.append(f"Image metadata chunk {tag!r} in {path.name}; strip authoring residue.")
                break
            offset += 8 + length + (length % 2)
    return issues


def check(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for name in REQUIRED:
        if not (root / name).is_file():
            errors.append(f"Missing required file: {name}")

    if (root / ".legends-module").is_file():
        mod = (root / ".legends-module").read_text(encoding="utf-8").strip()
        if mod != "legends-youtube":
            errors.append(f".legends-module mismatch: {mod!r}")

    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8") if (root / "pyproject.toml").is_file() else ""
    yt_init = (
        (root / "src/legends_youtube/__init__.py").read_text(encoding="utf-8")
        if (root / "src/legends_youtube/__init__.py").is_file()
        else ""
    )
    ytdlp_init = (
        (root / "src/legends_ytdlp/__init__.py").read_text(encoding="utf-8")
        if (root / "src/legends_ytdlp/__init__.py").is_file()
        else ""
    )
    citation = (root / "CITATION.cff").read_text(encoding="utf-8") if (root / "CITATION.cff").is_file() else ""
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8") if (root / "CHANGELOG.md").is_file() else ""

    m_py = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
    m_yt = re.search(r'^__version__\s*=\s*"([^"]+)"', yt_init, re.M)
    m_ytdlp = re.search(r'^__version__\s*=\s*"([^"]+)"', ytdlp_init, re.M)
    m_cit = re.search(r'^version:\s*"?([^"\n]+)"?', citation, re.M)
    m_chg = re.search(r"^##\s+\[?v?(\d+\.\d+\.\d+)\]?", changelog, re.M)

    versions = {
        "pyproject.toml": m_py.group(1) if m_py else None,
        "legends_youtube.__init__": m_yt.group(1) if m_yt else None,
        "legends_ytdlp.__init__": m_ytdlp.group(1) if m_ytdlp else None,
        "CITATION.cff": m_cit.group(1).strip() if m_cit else None,
        "CHANGELOG.md": m_chg.group(1) if m_chg else None,
    }
    if len(set(versions.values())) != 1 or None in versions.values():
        errors.append(f"Version mismatch across files: {versions}")
    expected_version = versions.get("pyproject.toml")

    manifest = root / "assets" / "manifest.json"
    if manifest.is_file():
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8-sig"))
            entries = payload["files"]
            if expected_version and "version" in payload and payload["version"] != expected_version:
                errors.append(f"assets/manifest.json version mismatch: {payload['version']!r} != {expected_version!r}")
        except (ValueError, KeyError):
            errors.append("assets/manifest.json is not a manifest with files.")
            entries = []
        for entry in entries:
            target = root / "assets" / entry.get("name", "")
            try:
                raw = target.read_bytes()
            except OSError:
                errors.append(f"Manifest asset missing: {entry.get('name')}")
                continue
            if len(raw) != entry.get("bytes"):
                errors.append(f"Manifest byte mismatch: {entry.get('name')}")
            if hashlib.sha256(raw).hexdigest() != entry.get("sha256"):
                errors.append(f"Manifest hash mismatch: {entry.get('name')}")

    pack_path = root / "knowledge" / "youtube" / "pack.json"
    if pack_path.is_file():
        try:
            pack = json.loads(pack_path.read_text(encoding="utf-8-sig"))
            if expected_version and pack.get("version") != expected_version:
                errors.append(f"knowledge/youtube/pack.json version mismatch: {pack.get('version')!r} != {expected_version!r}")
            vault_dir = pack_path.parent / "vault"
            for f_entry in pack.get("files", []):
                rel_p = str(f_entry.get("path", ""))
                v_target = vault_dir / rel_p
                if not v_target.is_file():
                    errors.append(f"Pack file missing: {rel_p}")
                    continue
                if hashlib.sha256(v_target.read_bytes()).hexdigest() != f_entry.get("sha256"):
                    errors.append(f"Pack file hash mismatch: {rel_p}")
                if rel_p.startswith("templates/"):
                    src_file = root / rel_p
                else:
                    src_file = root / "wiki" / rel_p
                if not src_file.is_file():
                    errors.append(f"Authored mirror source missing for vault file: {rel_p}")
                else:
                    src_text = src_file.read_text(encoding="utf-8-sig")
                    if rel_p == "index.md":
                        src_text = src_text.replace("](../templates/", "](templates/")
                    vault_text = v_target.read_text(encoding="utf-8-sig")
                    if src_text != vault_text:
                        errors.append(f"Vault file out of sync with authored source: {rel_p}")
                    if rel_p == "sources.md":
                        ref_sources = root / "references" / "sources.md"
                        if ref_sources.is_file() and ref_sources.read_text(encoding="utf-8-sig") != vault_text:
                            errors.append("references/sources.md out of sync with knowledge/youtube/vault/sources.md")
        except Exception as exc:
            errors.append(f"Invalid knowledge/youtube/pack.json: {exc}")

    skill_files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP and not d.endswith(".egg-info")]
        for fn in filenames:
            path = Path(dirpath) / fn
            rel = path.relative_to(root).as_posix()
            if fn == "SKILL.md":
                skill_files.append(rel)
            if path.suffix.lower() in FORBIDDEN_FILES:
                errors.append(f"Forbidden file extension must not ship: {rel}")
                continue
            if path.suffix.lower() in {".png", ".webp"}:
                errors.extend(f"{rel}: {issue}" for issue in image_metadata_issues(path))
                continue
            if path.suffix not in TEXT_SUFFIXES and path.name not in {"LICENSE", "NOTICE", ".legends-module", ".legends-router-pin"}:
                continue
            try:
                text = path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                errors.append(f"Non-UTF-8 file: {rel}")
                continue
            if CONTROL_CHAR_RE.search(text):
                errors.append(f"Control character or replacement character U+FFFD in {rel}")
            if path.name != "check_release.py":
                for pattern in FORBIDDEN:
                    if re.search(pattern, text):
                        errors.append(f"Possible private or EDR-sensitive residue ({pattern}): {rel}")
            if path.suffix != ".md":
                continue
            if "\u2014" in text or "\u2013" in text or "\u2011" in text:
                errors.append(f"Disallowed dash in copy: {rel}")
            for target_link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
                if target_link.startswith(("https://", "http://", "mailto:", "#")):
                    continue
                cleaned = unquote(target_link.split("#", 1)[0].split("?", 1)[0])
                resolved = (path.parent / cleaned).resolve()
                if not resolved.is_relative_to(root.resolve()) or not resolved.exists():
                    errors.append(f"Broken or external local link: {rel}: {target_link}")

    if skill_files != ["skills/cto-legends/SKILL.md"]:
        errors.append(f"One-Skill Rule violation: found SKILL.md at {skill_files}")
    else:
        skill_text = (root / "skills/cto-legends/SKILL.md").read_text(encoding="utf-8")
        for pat in REQUIRED_SKILL_PATTERNS:
            if not re.search(pat, skill_text, re.M):
                errors.append(f"skills/cto-legends/SKILL.md missing required router content: {pat}")

    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Offline release checks.")
    parser.add_argument("--root", type=Path, default=ROOT)
    options = parser.parse_args()
    failures = check(options.root)
    for failure in failures:
        print(failure)
    print(f"Release checks: {'FAIL' if failures else 'PASS'} ({len(failures)} issues)")
    sys.exit(bool(failures))
