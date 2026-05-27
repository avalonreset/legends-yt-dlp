---
type: overview
status: active
created: 2026-05-27
updated: 2026-05-27
tags: [overview, project]
---

# Project Overview

Legends YT-DLP Slayer is a planned Windows-first archive orchestrator for people who need reliable, resumable video preservation workflows and do not want downloads to run outside a VPN privacy boundary.

The core product is not a downloader. yt-dlp already solves that. The product is the control plane around yt-dlp: preflight checks, Mullvad VPN state verification, lawful-use policy gates, batch planning, queue state, logs, reports, and operator-friendly recovery.

## Product Thesis

Most yt-dlp workflows fail in the boring places: messy command lines, accidental non-VPN traffic, lost progress, inconsistent folder names, unclear rights, weak logs, and brittle retry behavior. A polished orchestration layer can make legitimate archival jobs safer and easier without pretending platform blocks are something to bypass.

## MVP Shape

- Windows CLI first.
- Requires installed Mullvad VPN and yt-dlp.
- Requires VPN connected and Lockdown mode enabled before download work.
- Requires a rights basis for each batch.
- Runs yt-dlp with conservative sleep/retry/archive settings.
- Writes a batch manifest, per-item status, and final report.
- Stops for operator review on throttling, captchas, sign-in challenges, or block signals.

## Not the Product

This is not a bot for evading YouTube enforcement. It should not rotate IP addresses to keep grinding through source-side blocks. It should help operators do legitimate work carefully, with clean state and clear stop conditions.

