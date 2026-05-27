---
type: decision
status: accepted
created: 2026-05-27
updated: 2026-05-27
date: 2026-05-27
tags: [decision, compliance]
---

# ADR 001 - Lawful Use Boundary

## Context

The original product idea aims to make large yt-dlp jobs reliable behind Mullvad VPN. The risky version would treat VPN relay changes as a way to continue through platform throttling or blocks.

## Decision

The project will support only lawful archival jobs where the operator owns, has permission to download, or otherwise has a documented lawful basis for preserving the videos. VPN controls are privacy and leak-prevention controls. They are not evasion controls.

## Consequences

- Every batch requires a rights basis.
- The tool stops on throttling, captchas, sign-in challenges, or source blocks.
- The community release must explain the boundary plainly.
- Any feature request that weakens this boundary must be rejected or redesigned.

## Review Trigger

Review this ADR before the first public release and whenever a new source platform is added.

