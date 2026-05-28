---
type: runbook
status: draft
created: 2026-05-27
updated: 2026-05-27
tags: [runbook, preflight]
---

# Preflight Checklist

Before any batch runs:

- Target URL is recorded.
- Rights basis is recorded.
- Output folder is selected.
- yt-dlp is available.
- ffmpeg is available if needed.
- A JavaScript runtime is available for YouTube extraction.
- Mullvad CLI is available.
- Mullvad reports connected.
- Lockdown mode is on.
- Split tunneling is off.
- LAN sharing is blocked.
- Auto-connect is on.
- Generated `yt-dlp` config ignores user config.
- Generated `yt-dlp` config disables cookie files and browser cookies.
- Generated `yt-dlp` config contains no account auth options.
- Batch manifest has been written.
- Stop conditions are understood.

If any item fails, the runner must not start.
