---
type: module
status: planned
created: 2026-05-27
updated: 2026-05-27
tags: [module, state, queue]
---

# Job Queue and State Store

## Purpose

Keep large archive jobs resumable and inspectable.

## Responsibilities

- Store batch metadata.
- Store per-item status.
- Track rights basis and source URL.
- Track yt-dlp archive file path.
- Track preflight evidence.
- Track stop condition history.

## Storage Options

- MVP: JSONL manifests plus yt-dlp archive files.
- Later: SQLite for queryable status and multi-batch dashboards.

## State Model

- planned
- preflight_failed
- ready
- running
- item_done
- item_failed
- blocked
- paused
- complete

