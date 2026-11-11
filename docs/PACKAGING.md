# Packaging and Release Verification

Run the release readiness gate from the repository root:

```bash
python scripts/check_release.py
```

`scripts/check_release.py` verifies:

- required governance, recipe, asset, and router skill files
- version synchronization across `pyproject.toml`, `src/legends_ytdlp/__init__.py`, `CITATION.cff`, and `CHANGELOG.md`
- `skills/cto-legends/SKILL.md` router integrity and the One-Skill Rule
- PNG and WebP metadata chunk hygiene
- absence of forbidden shell wrappers, hidden-window flags, credential-store access, or private machine paths

To build standard Python wheel and source distributions (`dist/legends_yt_dlp-0.1.5-py3-none-any.whl` and `dist/legends_yt_dlp-0.1.5.tar.gz`):

```bash
python -m build
```

`MANIFEST.in` includes tracked source, docs, examples, scripts, tests, the router skill file, and legal/community files while excluding ignored local runtime state:

- `.env` and `.env.*`
- `.local/`
- `batches/`
- `reports/`
- `downloads/`
- `cache/`
- `secrets/`
- `cookies/`
- `.git/`

After installing, the first command for a user should be:

```powershell
legends-yt-dlp onboard
```

## Release Checklist

Before publishing a release:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p "test_*.py" -v
python -m compileall -q src tests
python scripts/check_release.py
git diff --check
```

Do not publish a package that contains account numbers, cookies, downloaded media, local `yt-dlp` binaries, batch outputs, client rights evidence, or untracked local experiment files.
