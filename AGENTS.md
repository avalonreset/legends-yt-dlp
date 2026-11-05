# Development Notes (`legends-yt-dlp`)

Repository-local engineering and verification reference for contributors and coding agents working inside this checkout. End-user and agent routing go through `cto-legends`; the vendored router copy lives at [skills/cto-legends/SKILL.md](skills/cto-legends/SKILL.md) and the module operator recipe is [docs/AGENT-RECIPE.md](docs/AGENT-RECIPE.md).

## Commands

```bash
pip install -e .
python -m unittest discover -s tests -v
python scripts/check_release.py
legends-yt-dlp doctor --offline
```

## Architecture & Key Paths

- `src/legends_ytdlp/cli.py` - CLI parser and command handlers (`legends-yt-dlp` and `python -m legends_ytdlp`).
- `src/legends_ytdlp/doctor.py` - Readiness diagnostics (`doctor`, `--offline`, `--require-tools`, `--production`).
- `src/legends_ytdlp/batch.py` - Batch manifest planning, anonymous `yt-dlp.conf` generation, preflight checks, and execution.
- `src/legends_ytdlp/inventory.py` and `src/legends_ytdlp/ledger.py` - Channel/playlist inventory expansion and JSONL item ledger tracking.
- `src/legends_ytdlp/intelligence.py` - Post-capture local word-ledger import, CrispASR Parakeet wrapper, NFA forced-alignment bridge, exact phrase search, FFmpeg clip planning, and Obsidian vault export.
- `src/legends_ytdlp/mullvad.py` - Optional Mullvad VPN CLI integration (`--with-vpn`), fail-closed lockdown checks, and post-run shutdown.
- `docs/AGENT-RECIPE.md` and `docs/OPERATOR-ROUTING.md` - Operator recipes loaded by `cto-legends handoff legends-yt-dlp`.
- `scripts/check_release.py` - Automated release gate verifying version parity, asset integrity, link resolution, and security guardrails.

## EDR and Security Guardrails

- Never spawn background shells, hidden console windows, or execution-policy bypass shell wrappers.
- Never bundle `.ps1`, `.bat`, `.cmd`, `.vbs`, or `.ahk` files in the repository or wheel/sdist artifacts.
- Never read local browser profile databases, DPAPI stores, cookie databases, or third-party credential stores; all `yt-dlp` configurations must enforce `--ignore-config`, `--no-cookies`, and `--no-cookies-from-browser`.
- Never automate VPN relay rotation to bypass source-side rate limits, captchas, login prompts, or blocks; pause and report source-side controls immediately.
- Keep `skills/cto-legends/SKILL.md` as the only `SKILL.md` in the repository.
