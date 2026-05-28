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
- `doctor`, `plan`, `inventory`, `ledger`, `preflight`, `run`, `verify`, and report summaries.
- Mullvad connected-state check.
- Lockdown mode check if exact command support is verified.
- yt-dlp generated config.
- JSON batch manifest plus JSONL item ledger.
- Optional copied rights evidence files.
- Markdown final report.

## Not in Scope

- GUI.
- Multi-platform support.
- VPN relay automation for bypassing source blocks.
- Cookie/account workflows for pushing through login, captcha, account-control, or block states.

## Release Gate

- Unit tests for command generation, policy checks, and state transitions.
- Live smoke test on Windows with a lawful sample URL.
- Channel or playlist inventory creates a reviewable item ledger before downloads.
- Real-run verification refreshes ledger state and reports ledger status counts.
- Rights evidence file copying is documented and verified.
- Source-side throttles, captchas, login challenges, account controls, and blocks stop the workflow without relay rotation.
- No secret or cookie files included in git.
- Community docs include [[Use Policy]].
