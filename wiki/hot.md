---
type: meta
title: "Hot Cache"
status: active
created: 2026-05-27
updated: 2026-05-28
tags: [hot-cache, meta]
---

# Hot Cache

## Last Updated

2026-05-28. Product hardening now has a professional operator path plus a fresh assessment of remaining release gaps.

## Key Recent Facts

- The workspace started empty and was not a git repo.
- The vault uses a combined Mode B/C/E structure: implementation architecture, project/community release planning, and research/compliance notes.
- The useful product core is a Windows-first yt-dlp orchestration layer with Mullvad VPN preflight checks, fail-closed networking, queue state, and operator reports.
- The explicit safety boundary is that Mullvad is for privacy and leak prevention, not IP rotation to bypass YouTube throttling, account controls, or blocks.
- Mullvad CLI was found at the installed app path and reports `mullvad-cli 2026.2`.
- Official `yt-dlp.exe` was installed locally to `.local/bin`, verified by SHA256, and reports version `2026.03.17`.
- The CLI now supports `doctor --production`, Mullvad wrappers, yt-dlp install/version, batch `plan`, `preflight`, and guarded `run`.
- GitHub repo `avalonreset-pro/legends-yt-dlp-slayer` is private on `main`, has no team grants, and has wiki/projects/forking disabled.
- Mullvad is logged in, Lockdown mode is on, auto-connect is on, LAN sharing is blocked, split tunneling is off, quantum resistance is on, IPv6 is off, and connected preflight passes.
- Added `mullvad inspect` plus first-class wrappers for account, relay, DNS, tunnel, LAN, auto-connect, split tunnel, anti-censorship, API access, and raw passthrough.
- Added `skills/legends-yt-dlp-slayer/SKILL.md` with references for commands, batch cataloging, safety/error policy, and Mullvad controls.
- Batch planning now supports multiple URLs and `--from-file`; `catalog` lists local batch manifests.
- Added safe VPN recovery: disconnected/tunnel/network failures can trigger Mullvad reconnect and retry, but source-side blocks still pause without relay/IP switching.
- Production preflight now requires Mullvad connected, Lockdown on, split tunneling off, LAN sharing blocked, and auto-connect on.
- Generated yt-dlp configs now force anonymous operation with `--ignore-config`, `--no-cookies`, and `--no-cookies-from-browser`.
- Production preflight rejects browser cookies, cookie files, username/password auth, `.netrc`, and other account-auth options.
- Fresh dry-run smoke testing passed through Mullvad with no yt-dlp ERROR/WARNING lines after fixing config quoting and enabling Node as the JavaScript runtime.
- Current live Mullvad posture is connected through a US relay constraint, with Lockdown mode on.
- A bounded authorized NASA smoke batch downloaded one item, wrote an archive entry, generated compact run reports, and reran idempotently without duplicating files.
- Deliberate disconnect testing confirmed Lockdown blocks internet access, production doctor/preflight/run fail closed, and `mullvad recover` reconnects successfully.
- `mullvad disconnect` now refuses by default when Lockdown is on; use `mullvad disconnect-test --emergency-unlock` for controlled fail-closed testing with automatic recovery.
- `setup production` applies the full Mullvad production posture and verifies production doctor.
- `smoke plan --count 5` creates a curated NASA Goddard validation batch.
- `verify` checks archive entries, reports, media files, info JSON sidecars, and ffprobe media readability.
- A five-video NASA Goddard smoke run completed with 5 archive entries, 5 MP4 files, 5 info JSON files, 19,173,401 media bytes, and clean idempotent rerun behavior.
- The smoke run exposed a successful-run YouTube 429 warning; classification now flags source-side warnings even when yt-dlp exits 0.
- [[Product Assessment 2026-05-28]] records that the next quality jump is structured per-item state, better run summaries, inventory-only planning, rights evidence, release packaging, and license/distribution polish.

## Recent Changes

- Created: [[Project Overview]], [[Architecture Overview]], [[Use Policy]], [[Roadmap]], [[Windows Operator Setup]], [[CLI Operator Commands]].
- Seeded source notes for Mullvad pricing, Mullvad CLI, and yt-dlp.
- Added templates and a vault health-check script.
- Added Python CLI scaffold under `src/slayer_cli`.
- Added GitHub-facing README, docs, changelog, and repository metadata.
- Added [[Mullvad Control Surface]] and evidence for the current CLI settings.
- Added the Codex skill suite and updated docs for catalog-style batch planning.
- Created [[Account Cookie Policy]] and updated the preflight/runbook docs for production privacy posture.
- Added bounded smoke-test options, compact run reports, guarded disconnect testing, production setup, smoke-pack planning, batch verification, and fixed recovery from explicit Mullvad disconnected state.
- Added [[Product Assessment 2026-05-28]] and expanded [[Roadmap]] with productization priorities.

## Active Threads

- Next release gate is a productization pass: item ledger, run summaries, inventory mode, rights evidence, and alpha packaging.
- Existing older manifests may fail production preflight until regenerated because they lack the newer anonymous-auth and limit policy flags.
- Next GitHub step is optional: create a first alpha tag after reviewing the pushed hardening commit.
