---
type: release-plan
status: draft
created: 2026-05-27
updated: 2026-05-27
tags: [release, v0.1.0]
---

# Release Plan v0.1.0

## Goal

Ship a private/community alpha that proves the safe orchestration loop.

## Scope

- Windows CLI.
- `doctor`, `plan`, `preflight`, `run`, `resume`, and `report`.
- Mullvad connected-state check.
- Lockdown mode check if exact command support is verified.
- yt-dlp generated config.
- JSONL batch manifest.
- Markdown final report.

## Not in Scope

- GUI.
- Multi-platform support.
- VPN relay automation for bypassing source blocks.
- Cookie management beyond explicit operator-provided paths and warnings.

## Release Gate

- Unit tests for command generation, policy checks, and state transitions.
- Live smoke test on Windows with a lawful sample URL.
- No secret or cookie files included in git.
- Community docs include [[Use Policy]].

