---
type: runbook
status: draft
created: 2026-05-27
updated: 2026-05-27
tags: [runbook, throttling, safety]
---

# Blocked or Throttled SOP

## Goal

Handle source-side throttling or block signals without escalating into evasion behavior.

## Procedure

1. Pause the batch.
2. Record the exact yt-dlp error and item URL.
3. Confirm whether the issue is transient network failure or a source-side block signal.
4. If source-side throttling, captcha, login challenge, or block is present, stop the batch.
5. Wait, reduce scope, or use an authorized export path where available.
6. Resume only when the operator has a lawful reason and the source is no longer blocking normal access.

## Do Not

- Do not rotate VPN relays to continue through a block.
- Do not automate captcha or login-challenge handling.
- Do not hide repeated block signals in summary counts.

