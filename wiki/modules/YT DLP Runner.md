---
type: module
status: planned
created: 2026-05-27
updated: 2026-05-27
tags: [module, yt-dlp]
---

# YT DLP Runner

## Purpose

Wrap yt-dlp as an external process with generated config files, stable output paths, and structured event capture.

## Responsibilities

- Locate yt-dlp and ffmpeg.
- Generate per-batch yt-dlp config files.
- Use download archives to avoid duplicate work.
- Use conservative sleep/retry settings.
- Capture stdout/stderr and classify outcomes.
- Detect stop conditions such as throttling, captcha, sign-in challenges, access denial, or repeated HTTP failures.

## Initial Config Ideas

- Download archive per batch.
- Output template by source, upload date, title, id, and extension.
- Metadata and thumbnail capture as optional profile flags.
- Conservative sleep and retry defaults.
- Explicit merge format when ffmpeg is present.

## Tests

- Dry-run command construction.
- Process timeout handling.
- Classification of representative yt-dlp error lines.
- Resume behavior against a fixture archive file.

