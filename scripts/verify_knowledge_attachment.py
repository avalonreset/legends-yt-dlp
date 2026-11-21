"""Exercise this pack against an installed Empire source in a temporary vault."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile


def _discover_empire_source(explicit: Path | None, repo_root: Path) -> Path | None:
    if explicit is not None:
        return explicit.resolve()
    env_src = os.environ.get("LEGENDS_EMPIRE_SOURCE", "").strip()
    if env_src:
        cand = Path(env_src)
        if (cand / "claude_empire").is_dir():
            return cand.resolve()
    for sibling in (
        repo_root.parent / "legends-empire-public",
        repo_root.parent / "legends-empire",
        repo_root / ".integration" / "legends-empire-public",
    ):
        if (sibling / "claude_empire").is_dir():
            return sibling.resolve()
    return None


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    default_pack = repo_root / "knowledge" / "youtube" / "pack.json"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--empire-source", "--empire-repo", dest="empire_source", type=Path, required=False, default=None)
    parser.add_argument("--pack", type=Path, default=default_pack)
    args = parser.parse_args()
    discovered = _discover_empire_source(args.empire_source, repo_root)
    if discovered is not None:
        sys.path.insert(0, str(discovered))
    try:
        from claude_empire import __version__ as empire_version
        from claude_empire.knowledge import attachment_bundle, load_pack
        from claude_empire.transaction import TransactionError, apply_bundle, inspect_bundle
    except ImportError as exc:
        parser.error(
            f"Could not import claude_empire ({exc}). Pass --empire-source <path> or install claude-empire."
        )

    if os.name == "nt":
        try:
            version = tuple(int(part) for part in empire_version.split(".")[:3])
        except ValueError:
            parser.error("Cannot verify Empire version; native Windows requires 0.3.1+.")
        if version < (0, 3, 1):
            parser.error("Native Windows attachment requires Empire 0.3.1+; upgrade the engine.")

    with tempfile.TemporaryDirectory(prefix="legends-youtube-pack-") as temporary:
        root = Path(temporary).resolve()
        vault = root / "synthetic-vault"
        (vault / "wiki").mkdir(parents=True)
        (vault / ".raw").mkdir()
        source = root / "module"
        shutil.copytree(args.pack.resolve().parent, source)
        pack = source / "pack.json"
        original = json.loads(pack.read_text(encoding="utf-8"))
        load_pack(pack)
        shelf = vault / original["ontology"]["suggested_home"]
        checks = []

        def bundle(identity: str):
            return attachment_bundle(
                vault,
                pack,
                operation_id=identity,
                generated_at="2026-11-09T01:00:00Z",
            )

        def apply(candidate):
            approval = inspect_bundle(vault, candidate)["approval_sha256"]
            return apply_bundle(vault, candidate, approved_plan_sha256=approval)

        first = bundle("first-attach")
        inspect_bundle(vault, first)
        assert not shelf.exists(), "Preview changed the vault."
        checks.append("preview has no writes")
        apply(first)
        assert (shelf / "reference" / original["entrypoint"]).is_file()
        checks.append("fresh attachment")
        assert bundle("repeat-attach")["writes"] == []
        checks.append("repeat attachment is noop")
        index = shelf / "index.md"
        index.write_text("# User-owned index\n", encoding="utf-8")
        private = vault / "wiki" / "private-decisions.md"
        private.write_text("# Private choices\n", encoding="utf-8")
        changed = source / "vault" / original["entrypoint"]
        changed.write_text(changed.read_text(encoding="utf-8") + "\nSynthetic update.\n", encoding="utf-8")
        updated = json.loads(pack.read_text(encoding="utf-8"))
        version_parts = [int(part) for part in original["version"].split(".")]
        version_parts[-1] += 1
        updated["version"] = ".".join(str(part) for part in version_parts)
        for item in updated["files"]:
            item["sha256"] = hashlib.sha256((source / "vault" / item["path"]).read_bytes()).hexdigest()
        pack.write_text(json.dumps(updated), encoding="utf-8")
        apply(bundle("upstream-update"))
        assert index.read_text(encoding="utf-8") == "# User-owned index\n"
        assert private.read_text(encoding="utf-8") == "# Private choices\n"
        checks.append("upstream update preserves user index and private decisions")
        reference = shelf / "reference" / original["entrypoint"]
        reference.write_text("# Locally edited reference\n", encoding="utf-8")
        snapshot = {str(p.relative_to(vault)): p.read_bytes() for p in vault.rglob("*") if p.is_file()}
        try:
            bundle("conflicting-update")
        except TransactionError:
            checks.append("local edit refuses attachment before mutation")
        else:
            raise AssertionError("Edited reference was accepted for overwrite.")
        assert snapshot == {str(p.relative_to(vault)): p.read_bytes() for p in vault.rglob("*") if p.is_file()}
        print(
            json.dumps(
                {
                    "ok": True,
                    "checks": checks,
                    "scope": "synthetic vault only",
                    "platform": platform.system(),
                    "python": platform.python_version(),
                    "empire_version": empire_version,
                    "pack_version": original["version"],
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
