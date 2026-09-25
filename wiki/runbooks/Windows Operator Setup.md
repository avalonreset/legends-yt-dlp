---
type: runbook
status: draft
created: 2026-05-27
updated: 2026-05-27
tags: [runbook, windows, setup]
---

# Windows Operator Setup

## Goal

Prepare a Windows machine to run Legends YT-DLP safely.

## Prerequisites

- Mullvad VPN installed.
- Active Mullvad account.
- yt-dlp installed.
- ffmpeg installed.
- Output drive with enough free space.

## Procedure

1. Install Mullvad and log in.
2. Enable Lockdown mode if available.
3. Confirm `mullvad` is available from PowerShell or Command Prompt.
4. Install or locate yt-dlp.
5. Install or locate ffmpeg.
6. Run the future `legends-yt-dlp doctor` command.
7. Fix all failed checks before running any batch.

## Verification

- `mullvad status` reports connected.
- yt-dlp version command succeeds.
- ffmpeg version command succeeds.
- Output directory is writable.

## Stop Conditions

- Mullvad unavailable.
- Lockdown mode cannot be verified.
- yt-dlp unavailable.
- No documented rights basis for the intended batch.

