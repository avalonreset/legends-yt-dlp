---
type: research
status: summarized
created: 2026-05-27
updated: 2026-05-27
source_urls:
  - "https://github.com/yt-dlp/yt-dlp"
  - "https://github.com/yt-dlp/yt-dlp/releases/tag/2026.03.17"
  - "https://pypi.org/project/yt-dlp/"
tags: [research, yt-dlp, windows]
---

# yt-dlp Deep Research 2026-05-27

## Finding

The official project for this app is `yt-dlp/yt-dlp` on GitHub. It is the maintained fork lineage relevant to this project, not legacy `youtube-dl` or inactive `youtube-dlc`.

## Current Release

- Latest stable observed on 2026-05-27: `2026.03.17`.
- PyPI lists the corresponding package version as `2026.3.17`.
- The official README marks `yt-dlp.exe` as the recommended Windows standalone x64 binary.

## Installation Decision

Use official GitHub release binaries for the Windows MVP:

- Download `yt-dlp.exe` from GitHub Releases.
- Download `SHA2-256SUMS`.
- Verify the executable hash.
- Store the binary in ignored local project tooling at `.local/bin/yt-dlp.exe`.

## Wrapper Guidance

The app should treat yt-dlp as a child-process dependency and avoid parsing unstable human-oriented output when structured output is available. Use generated config files, `--dump-json`, `--print`, `--newline`, and eventually progress templates where needed.

## Operational Options for This Project

Useful defaults:

- `--batch-file`
- `--download-archive`
- `--paths`
- `--output`
- `--windows-filenames`
- `--continue`
- `--no-overwrites`
- `--retries`
- `--fragment-retries`
- `--retry-sleep`
- `--sleep-requests`
- `--sleep-interval`
- `--max-sleep-interval`
- `--skip-playlist-after-errors`
- `--write-info-json`

Avoid defaulting to proxy, geo, impersonation, or bypass-style options. Those belong behind explicit policy gates, if ever.

## Linked Pages

- [[yt-dlp]]
- [[YT DLP Runner]]
- [[Batch Archive SOP]]

