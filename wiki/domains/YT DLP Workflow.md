---
type: domain
status: active
created: 2026-05-27
updated: 2026-05-27
tags: [domain, yt-dlp, downloads]
---

# YT DLP Workflow

This domain covers how the app wraps yt-dlp for legitimate archival jobs.

## Core Pattern

1. Build or import a batch manifest.
2. Validate rights and policy.
3. Verify Mullvad state.
4. Run yt-dlp with archive, retry, sleep, output, and metadata settings.
5. Record item-level status.
6. Stop on source block signals.
7. Produce a final report.

## Useful yt-dlp Capabilities

- Batch files for URL sets.
- Download archive files for idempotence.
- Output templates for stable folder layouts.
- Sleep and retry controls for conservative operation.
- Error continuation controls when a single item fails.

## Linked Pages

- [[YT DLP Runner]]
- [[Authorized Channel Archive Flow]]
- [[yt-dlp Operational Notes 2026-05-27]]

