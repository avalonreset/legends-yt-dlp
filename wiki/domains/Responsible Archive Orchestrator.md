---
type: domain
status: active
created: 2026-05-27
updated: 2026-05-27
tags: [domain, archive, orchestration]
---

# Responsible Archive Orchestrator

This domain defines the product as a controlled archival workflow rather than a raw scraping loop.

## Responsibilities

- Convert a channel, playlist, or URL list into an explicit batch plan.
- Require a rights basis before a batch can run.
- Verify network safety before yt-dlp starts.
- Keep state so retries and resumes are clean.
- Produce completion evidence operators can inspect.

## Design Principles

- Wrap proven tools instead of rebuilding them.
- Fail closed when privacy or policy checks fail.
- Prefer slow, resumable, auditable operation over aggressive throughput.
- Treat block signals as stop conditions, not obstacles to work around.

## Linked Pages

- [[CLI Control Plane]]
- [[Policy Engine]]
- [[Batch Archive SOP]]
- [[Use Policy]]

