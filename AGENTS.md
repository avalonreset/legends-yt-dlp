# Agent Instructions (`legends-youtube`)

1. Use the `legends-youtube` CLI (`python -m legends_youtube`) for all YouTube Data API v3, YouTube Analytics API v2, metadata, quota, link-audit, chapter-lint, quiz-lint, thumbnail, idea-radar, and private-draft operations.
2. Use `legends-yt-dlp` (`python -m legends_ytdlp` or `legends-youtube yt-dlp <args>`) for preview-first `yt-dlp` channel/playlist metadata probing (`inventory`), SHA-256-guarded anonymous media capture (`plan`, `preflight`, `run`, `verify`), optional `--with-vpn` Mullvad Lockdown lifecycle, and post-capture GPU word ledgers and FFmpeg clip plans (`intelligence`).
3. Follow [docs/AGENT-RECIPE.md](docs/AGENT-RECIPE.md), [docs/OPERATOR-ROUTING.md](docs/OPERATOR-ROUTING.md), and [wiki/index.md](wiki/index.md).
4. **Safety and EDR Guardrails:**
   - Default to read-only inspection (`doctor`, `quota-plan`, `channel-inventory`, `video-inspect`, `public-readback`, `channel-outliers`, `score-idea`, `metadata-plan`, `links-audit`, `analytics-audit`, `packaging-audit`, `chapters-lint`, `quiz-lint`, `thumbnail-check`, `draft-freeze`, and `legends-yt-dlp doctor --offline` / `inventory` / `preflight` / `run --dry-run`).
   - Never execute `metadata-apply --confirm`, `draft-upload --apply`, or `legends-yt-dlp run --yes` without explicit user approval.
   - Never spawn hidden consoles, execution-policy bypass shell wrappers, or background localhost daemons.
   - Never read local browser profile databases, DPAPI stores, cookie stores, or third-party credential stores. Read YouTube API credentials strictly from explicit environment variables, `--dotenv`, or `--token-file`, and run `yt-dlp` strictly with `--ignore-config`, `--no-cookies`, and `--no-cookies-from-browser`.
   - Never print raw OAuth tokens, client secrets, API keys, or Mullvad account numbers to stdout, logs, or Markdown receipts.
