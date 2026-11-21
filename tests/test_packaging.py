"""Mirror completeness: authored sources, membership links, wheel smoke."""
from __future__ import annotations

import posixpath
from importlib import metadata as importlib_metadata
from pathlib import Path
import re
import unittest
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
MAX_FILES = 4000
REQUIRED_DATA = [
    "legends_youtube/_data/README.md",
    "legends_youtube/_data/LICENSE",
    "legends_youtube/_data/NOTICE.md",
    "legends_youtube/_data/THIRD_PARTY_NOTICES.md",
    "legends_youtube/_data/SUPPORT.md",
    "legends_youtube/_data/CONTRIBUTING.md",
    "legends_youtube/_data/CODE_OF_CONDUCT.md",
    "legends_youtube/_data/AGENTS.md",
    "legends_youtube/_data/docs/AGENT-RECIPE.md",
    "legends_youtube/_data/docs/KNOWLEDGE-PACK.md",
    "legends_youtube/_data/knowledge/youtube/pack.json",
    "legends_youtube/_data/wiki/index.md",
    "legends_youtube/_data/references/sources.md",
    "legends_youtube/_data/templates/private-operation-receipt.md",
    "legends_youtube/_data/skills/cto-legends/SKILL.md",
    "legends_youtube/_data/SECURITY.md",
    "legends_youtube/_data/CHANGELOG.md",
]


def load_mirror():
    try:
        import setuptools  # noqa: F401
    except ImportError:
        raise unittest.SkipTest("setuptools is required to evaluate the data mirror")
    raw = (ROOT / "setup.py").read_text(encoding="utf-8")
    needle = "from setuptools import setup"
    assert needle in raw, "setup.py import shape changed; update the evaluation stub"
    source = raw.replace(needle, "# setup() call stubbed for evaluation", 1)
    namespace = {"setup": lambda *args, **kwargs: None, "__file__": str(ROOT / "setup.py")}
    exec(source, namespace)
    return namespace


def mirror_members() -> dict[str, Path]:
    namespace = load_mirror()
    members: dict[str, Path] = {}
    for source, relative in namespace["iter_mirror_sources"](ROOT):
        members[relative.as_posix()] = source
    return members


def local_target(raw: str) -> str | None:
    if raw.startswith(("https://", "http://", "mailto:", "#", "data:")):
        return None
    target = unquote(raw.split("#", 1)[0].split("?", 1)[0]).strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    return target or None


def check_membership(members: dict[str, Path]) -> list[str]:
    errors: list[str] = []
    pages = sorted(name for name in members if name.endswith(".md"))
    dirs = {"."}
    for name in members:
        parent = posixpath.dirname(name)
        while parent and parent != ".":
            dirs.add(parent)
            parent = posixpath.dirname(parent)
    for page in pages[:MAX_FILES]:
        try:
            text = members[page].read_text(encoding="utf-8-sig")
        except OSError:
            errors.append(f"Unreadable: {page}")
            continue
        for raw in LINK_RE.findall(text):
            target = local_target(raw)
            if target is None:
                continue
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(page), target))
            if resolved == "." or resolved.startswith(".."):
                errors.append(f"Escapes mirror: {page}: {raw}")
            elif resolved not in members and resolved not in dirs:
                errors.append(f"Dangling in mirror: {page}: {raw}")
    return errors


class MirrorSourceTests(unittest.TestCase):
    def test_mirror_contains_required_files_and_resolving_links(self) -> None:
        members = mirror_members()
        for req in REQUIRED_DATA:
            rel = req.removeprefix("legends_youtube/_data/")
            self.assertIn(rel, members, f"Missing from setup.py mirror: {rel}")
        self.assertEqual(check_membership(members), [])


class WheelSmoke(unittest.TestCase):
    def test_installed_distribution_if_present(self) -> None:
        try:
            dist = importlib_metadata.distribution("legends-youtube")
        except importlib_metadata.PackageNotFoundError:
            raise unittest.SkipTest("legends-youtube wheel not installed in environment")
        names = {str(entry).replace("\\", "/") for entry in (dist.files or [])}
        if not any(n.startswith("legends_youtube/_data/") for n in names):
            raise unittest.SkipTest("Editable checkout install; wheel _data mirror not active")
        missing = [name for name in REQUIRED_DATA if name not in names]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
