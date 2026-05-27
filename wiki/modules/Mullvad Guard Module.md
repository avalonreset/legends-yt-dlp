---
type: module
status: planned
created: 2026-05-27
updated: 2026-05-27
tags: [module, mullvad, vpn]
---

# Mullvad Guard Module

## Purpose

Guarantee that no yt-dlp network work starts unless the machine is in an approved Mullvad VPN state.

## Responsibilities

- Locate the `mullvad` CLI.
- Parse `mullvad status` and `mullvad status -v`.
- Confirm connected state.
- Confirm Lockdown mode requirement once exact CLI support is verified.
- Optionally verify egress through Mullvad's connection-check endpoint.
- Return structured preflight evidence to [[Telemetry and Reports]].

## Non-Responsibilities

- It must not rotate relays to bypass throttling, captchas, account controls, or source blocks.
- It must not mask a failed policy check.

## Failure Behavior

If any VPN check is ambiguous, fail closed and instruct the operator to fix Mullvad manually before retrying.

