---
type: module
status: planned
created: 2026-05-27
updated: 2026-05-27
tags: [module, cli]
---

# CLI Control Plane

## Purpose

Provide the operator interface for planning, preflighting, running, resuming, and reporting archive jobs.

## Candidate Commands

- `legends-yt-dlp init`
- `legends-yt-dlp doctor`
- `legends-yt-dlp plan --url <url> --rights "<basis>"`
- `legends-yt-dlp preflight <batch>`
- `legends-yt-dlp run <batch>`
- `legends-yt-dlp resume <batch>`
- `legends-yt-dlp status`
- `legends-yt-dlp report <batch>`

## Responsibilities

- Parse commands and config.
- Print clear pass/fail preflight output.
- Never hide stop conditions.
- Route work to modules instead of embedding logic in command handlers.

## Tests

- Command parsing.
- Config validation.
- Exit codes for pass, fail, blocked, and partial-complete states.

