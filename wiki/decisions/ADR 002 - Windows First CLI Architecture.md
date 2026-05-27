---
type: decision
status: accepted
created: 2026-05-27
updated: 2026-05-27
date: 2026-05-27
tags: [decision, windows, cli]
---

# ADR 002 - Windows First CLI Architecture

## Context

The user wants a practical app that can control Mullvad and yt-dlp on Windows first. A GUI can come later, but the first risk is process orchestration, state, and preflight correctness.

## Decision

Build a Windows-first CLI MVP before any desktop UI. Use the official Mullvad CLI and yt-dlp executable as external tools.

## Consequences

- The first code milestone should be `slayer doctor`.
- The project can test the hard parts without committing to UI framework choices.
- The eventual GUI can wrap the same core modules.

## Review Trigger

Review after `doctor`, `plan`, `preflight`, and `run` work on fixture jobs.

