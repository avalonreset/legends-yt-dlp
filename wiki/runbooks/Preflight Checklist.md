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
- Mullvad CLI is available.
- Mullvad reports connected.
- Lockdown mode requirement is satisfied.
- Optional Mullvad connection-check endpoint passes.
- Batch manifest has been written.
- Stop conditions are understood.

If any item fails, the runner must not start.

