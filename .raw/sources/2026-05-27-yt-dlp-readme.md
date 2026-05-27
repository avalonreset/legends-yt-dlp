---
type: raw-source
status: captured
created: 2026-05-27
updated: 2026-05-27
source_url: "https://github.com/yt-dlp/yt-dlp"
accessed: 2026-05-27
tags: [yt-dlp, source]
---

# yt-dlp README Snapshot

Source: https://github.com/yt-dlp/yt-dlp

Accessed on 2026-05-27.

## Captured Facts

- yt-dlp is a feature-rich command-line audio/video downloader.
- The project supports configuration files and large sets of command-line options.
- Operationally relevant options include download archives, retry sleep controls, request sleep controls, batch files, output templates, and error handling.

## Project Implications

- The orchestrator should wrap yt-dlp rather than reimplement downloading.
- Job state should use yt-dlp archive files plus an app-level queue database or manifest.
- The safest batch behavior is conservative pacing, resumability, and stop-on-block handling.

