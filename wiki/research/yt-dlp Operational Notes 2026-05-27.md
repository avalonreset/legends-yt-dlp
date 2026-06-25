---
type: research
status: summarized
created: 2026-05-27
updated: 2026-06-24
source_url: "https://github.com/yt-dlp/yt-dlp"
tags: [research, yt-dlp]
---

# yt-dlp Operational Notes 2026-05-27

Source: [[yt-dlp GitHub README]]

## Findings

- yt-dlp is a mature command-line downloader with broad option coverage.
- It supports config files, batch input, download archives, retries, sleep controls, and output templates.
- Those primitives are enough for a first orchestration MVP without forking yt-dlp.

## Project Implications

- Treat yt-dlp as an engine dependency.
- Use generated configs and process execution rather than constructing huge one-line commands.
- Keep app-level state separate from yt-dlp's download archive.
- For the Windows MVP, prefer the official standalone `yt-dlp.exe` release and verify it against upstream checksums.
- Fail readiness checks for managed `yt-dlp` builds older than 90 days and refresh with `slayer yt-dlp update`.

## Current Local Install

- Version: `2026.06.09`
- Path: `.local/bin/yt-dlp.exe`
- SHA256: recorded in `.local/bin/SHA2-256SUMS` after each managed install/update; `.local` stays ignored and is not packaged.
