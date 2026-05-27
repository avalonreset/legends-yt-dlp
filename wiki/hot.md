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

2026-05-27. Initial vault scaffold is complete and the first Windows CLI control plane has been started.

## Key Recent Facts

- The workspace started empty and was not a git repo.
- The vault uses a combined Mode B/C/E structure: implementation architecture, project/community release planning, and research/compliance notes.
- The useful product core is a Windows-first yt-dlp orchestration layer with Mullvad VPN preflight checks, fail-closed networking, queue state, and operator reports.
- The explicit safety boundary is that Mullvad is for privacy and leak prevention, not IP rotation to bypass YouTube throttling, account controls, or blocks.
- Mullvad CLI was found at the installed app path and reports `mullvad-cli 2026.2`.
- Official `yt-dlp.exe` was installed locally to `.local/bin`, verified by SHA256, and reports version `2026.03.17`.
- The CLI now supports `doctor`, Mullvad wrappers, yt-dlp install/version, batch `plan`, `preflight`, and guarded `run`.

## Recent Changes

- Created: [[Project Overview]], [[Architecture Overview]], [[Use Policy]], [[Roadmap]], [[Windows Operator Setup]], [[CLI Operator Commands]].
- Seeded source notes for Mullvad pricing, Mullvad CLI, and yt-dlp.
- Added templates and a vault health-check script.
- Added Python CLI scaffold under `src/slayer_cli`.

## Active Threads

- User is funding/logging into Mullvad.
- Next blocker is Mullvad connected state; default preflight exits nonzero until connected.
- After login, run `scripts\slayer.ps1 mullvad login`, `lockdown on`, `connect`, and `doctor --require-connected`.
