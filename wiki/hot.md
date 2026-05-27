---
type: meta
title: "Hot Cache"
status: active
created: 2026-05-27
updated: 2026-05-27
tags: [hot-cache, meta]
---

# Hot Cache

## Last Updated

2026-05-27. Initial vault scaffold is complete, the first Windows CLI control plane has been started, the private GitHub repository is live, and Mullvad is connected under CLI control.

## Key Recent Facts

- The workspace started empty and was not a git repo.
- The vault uses a combined Mode B/C/E structure: implementation architecture, project/community release planning, and research/compliance notes.
- The useful product core is a Windows-first yt-dlp orchestration layer with Mullvad VPN preflight checks, fail-closed networking, queue state, and operator reports.
- The explicit safety boundary is that Mullvad is for privacy and leak prevention, not IP rotation to bypass YouTube throttling, account controls, or blocks.
- Mullvad CLI was found at the installed app path and reports `mullvad-cli 2026.2`.
- Official `yt-dlp.exe` was installed locally to `.local/bin`, verified by SHA256, and reports version `2026.03.17`.
- The CLI now supports `doctor`, Mullvad wrappers, yt-dlp install/version, batch `plan`, `preflight`, and guarded `run`.
- GitHub repo `avalonreset-pro/legends-yt-dlp-slayer` is private on `main`, has no team grants, and has wiki/projects/forking disabled.
- Mullvad is logged in, Lockdown mode is on, auto-connect is on, LAN sharing is blocked, split tunneling is off, quantum resistance is on, IPv6 is off, and connected preflight passes.
- Added `mullvad inspect` plus first-class wrappers for account, relay, DNS, tunnel, LAN, auto-connect, split tunnel, anti-censorship, API access, and raw passthrough.

## Recent Changes

- Created: [[Project Overview]], [[Architecture Overview]], [[Use Policy]], [[Roadmap]], [[Windows Operator Setup]], [[CLI Operator Commands]].
- Seeded source notes for Mullvad pricing, Mullvad CLI, and yt-dlp.
- Added templates and a vault health-check script.
- Added Python CLI scaffold under `src/slayer_cli`.
- Added GitHub-facing README, docs, changelog, and repository metadata.
- Added [[Mullvad Control Surface]] and evidence for the current CLI settings.

## Active Threads

- Next blocker is a lawful user-provided test URL for a dry-run or real smoke test.
- Default preflight now passes when using an existing valid batch manifest.
- Next GitHub step is optional: create a first alpha tag only after a connected Mullvad smoke test passes.
