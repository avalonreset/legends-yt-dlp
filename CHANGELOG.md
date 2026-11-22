# Changelog

## 0.2.1 (2026-11-22)

- Sync vendored `cto-legends` router skill pin (`69ddc4f68faa`), enforce LF line endings via `.gitattributes`, and standardize release artifact checksums.

## 0.2.0 (2026-11-21)

- Unified `legends-youtube` (`legends_youtube`) and `legends-yt-dlp` (`legends_ytdlp`) into a single first-class YouTube Studio, Data API v3, Analytics API v2, and verified `yt-dlp` media archiving and GPU word-ledger package (`legends-youtube 0.2.0`).
- Exposed all console script entrypoints (`legends-youtube`, `legends-yt-dlp`, `legends-ytdlp`, `slayer`, `printing-press`) and added direct subcommand forwarding inside `legends-youtube` (`legends-youtube yt-dlp|archive|pull|transcribe|clips <args>`).
- Rendered the unified 7-card `r1` outlined Legends Font SVG suite (`assets/cards/r1/`) and updated the evergreen README, agent recipe, and attachable 18-file `legends.knowledge-pack/v1` YouTube Operations Vault (`knowledge/youtube/pack.json`).

## 0.1.6 (2026-11-21)

- Added `scripts/render_cards.py` and the 7 outlined Legends Font `r1` SVG design cards under `assets/cards/r1/`, and rewrote `README.md` to the evergreen CTO Legends architecture and reference standard.
- Included `assets/**/*.svg` in `MANIFEST.in` and synchronized version metadata across `pyproject.toml`, `CITATION.cff`, `assets/manifest.json`, and `SECURITY.md`.

## 0.1.5 (2026-11-11)

- Hardened `batch.py` against config and URL newline injection, validated `--max-filesize`, enforced a strict `yt-dlp.conf` option allowlist (blocking `--exec*`, `--alias`, `--plugin-dirs`, `--config-location*`, `--load-info-json`, `--print-to-file`, and `--proxy`), and enforced SHA-256 config verification inside both `preflight` and `run_batch()`.
- Validated `source_url` and inserted `"--"` before the positional URL argument in `inventory.py:run_ytdlp_inventory()`.
- Hardened `tools.py` upstream `yt-dlp` release checks and binary downloads with HTTPS-only host allowlisting, `ProxyHandler({})`, TLS 1.2+ context, bounded chunked reads, symlink refusal, and cross-platform binary selection (`yt-dlp.exe`, `yt-dlp_macos`, `yt-dlp_linux`).
- Hardened `render_clip_plan()`, `verify.py:probe_media()`, `extract_audio()`, `run_nfa_alignment()`, `mullvad.py`, and `process.py` with symlink refusal, output path containment, fail-closed `--overwrite` semantics, `-i` media flags, Hydra override validation, and 16-digit Mullvad account number validation.

## 0.1.1 (2026-11-21)

- Added outlined Legends Font `r1` SVG architecture, capability, operator prompt-chain, and comparison cards (`assets/cards/r1/`) for `legends-youtube` with `.svg` wheel data mirroring in `setup.py` and `MANIFEST.in`.

## 0.1.0 (2026-11-09)

- Initial release of `legends-youtube` and `legends-yt-dlp` for the `cto-legends` Studio stack: pure-stdlib YouTube Data API v3, Resumable Upload API, and Analytics API v2 client, deterministic `quota-plan` calculator, 2-unit-per-50-video `channel-inventory`, 0-quota `public-readback` and `channel-outliers`, Perfect Video Score `score-idea`, lossless `If-Match` ETag `metadata-plan`/`metadata-apply`, `chapters-lint`, `quiz-lint`, `thumbnail-check`, `draft-freeze`/`draft-upload`, preview-first `yt-dlp` batch archiving, `ffprobe` stream verification, local GPU CrispASR Parakeet word ledgers, FFmpeg clip plans, and the 18-file YouTube Operations Vault (`knowledge/youtube/pack.json`).
