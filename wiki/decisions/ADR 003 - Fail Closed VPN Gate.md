---
type: decision
status: accepted
created: 2026-05-27
updated: 2026-05-27
date: 2026-05-27
tags: [decision, vpn, safety]
---

# ADR 003 - Fail Closed VPN Gate

## Context

The product promise depends on not accidentally running yt-dlp outside the VPN boundary.

## Decision

The runner must fail closed. If Mullvad state is missing, ambiguous, disconnected, or fails egress verification, yt-dlp must not start.

## Consequences

- Preflight output needs to be explicit and inspectable.
- The app should not attempt clever recovery before the MVP has trustworthy checks.
- Operator remediation steps belong in [[Blocked or Throttled SOP]] and [[Preflight Checklist]].

## Review Trigger

Review when the Mullvad CLI output parser is implemented and again after testing on a real Windows Mullvad install.

