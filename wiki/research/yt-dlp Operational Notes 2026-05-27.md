---
type: research
status: summarized
created: 2026-05-27
updated: 2026-05-27
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

