"""Smoke-verify installed legends-youtube resources.json outside the source checkout."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) > 1:
        target_path = Path(sys.argv[1])
        info = json.loads(target_path.read_text(encoding="utf-8-sig"))
    elif Path("resources.json").is_file():
        info = json.loads(Path("resources.json").read_text(encoding="utf-8-sig"))
    else:
        repo_root = Path(__file__).resolve().parents[1]
        for cand in (repo_root / "src", repo_root):
            if str(cand) not in sys.path:
                sys.path.insert(0, str(cand))
        from legends_youtube.resources import resolve

        info = resolve()
    assert info["source"] in ("package_data", "checkout"), info["source"]
    root = Path(info["root"])
    assert root.is_absolute(), info["root"]
    recipe = Path(info["recipe"])
    if not recipe.is_absolute():
        recipe = root / recipe
    assert recipe.is_file(), str(recipe)
    assert recipe.name == "AGENT-RECIPE.md", recipe.name
    pack_manifest = Path(info["pack_manifest"])
    assert pack_manifest.is_file(), str(pack_manifest)
    pack = json.loads(pack_manifest.read_text(encoding="utf-8-sig"))
    assert pack["schema"] == "legends.knowledge-pack/v1", pack.get("schema")
    for item in pack["files"]:
        target = pack_manifest.parent / "vault" / item["path"]
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        assert digest == item["sha256"], item["path"]
    print("resource smoke OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
