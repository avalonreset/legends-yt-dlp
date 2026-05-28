---
type: meta
status: active
created: 2026-05-27
updated: 2026-05-27
tags: [log, meta]
---

# Log

## 2026-05-28 - Product Assessment Filed

- Added [[Product Assessment 2026-05-28]] with current strengths, weak areas, and next product priorities.
- Updated [[Roadmap]] with Phase 5 productization priorities: item ledger, run summary UX, inventory-only planning, rights evidence, alpha packaging, license posture, and public docs polish.
- Updated [[hot]] and [[index]] so future sessions start from the current product-readiness view.

## 2026-05-28 - Product SOP and Five-Video Smoke Pack

- Added `setup production` to apply Mullvad production posture and verify production doctor in one command.
- Added `smoke plan --count 5` with a curated NASA Goddard validation pack.
- Added `verify` to check archive entries, reports, media files, info JSON sidecars, total media bytes, and ffprobe media readability.
- Real five-video smoke evidence: 5 archive entries, 5 MP4 files, 5 info JSON files, 19,173,401 media bytes, and ffprobe passed for all media.
- Rerunning the same five-video manifest stayed idempotent: file count remained 10 and all 5 YouTube IDs were skipped from `archive.txt`.
- Fixed Windows console Unicode output for media filenames.
- Made dry-runs suppress raw yt-dlp JSON unless `--show-output` is passed.
- Hardened successful-run diagnostics so source-side warnings such as HTTP 429 are surfaced in reports even when yt-dlp exits 0.

## 2026-05-28 - Guarded Disconnect Testing Added

- Added `mullvad disconnect-test` as the approved fail-closed test path.
- Made `mullvad disconnect` refuse by default when Lockdown is on unless `--force` is explicit.
- Defaulted guarded disconnect tests to a US relay constraint and added `--emergency-unlock` as a recovery-failure fallback.
- Live evidence: `mullvad disconnect-test --emergency-unlock --attempts 3 --wait-seconds 5 --settle-seconds 4` confirmed Lockdown blocked internet access after disconnect and recovered Mullvad on the first attempt before returning.
- Hardened recovery state detection so disconnected and disconnecting states use `connect` instead of `reconnect`.

## 2026-05-28 - Bounded NASA Smoke Download Passed

- Planned an authorized bounded NASA smoke batch for `https://www.youtube.com/watch?v=4HSFKwho7MQ` with `--max-downloads 1 --max-height 360 --max-filesize 30M`.
- Dry-run reached the configured download limit and wrote a compact run report.
- Real run downloaded one MP4 and one info JSON, wrote `youtube 4HSFKwho7MQ` to the archive, and wrote a compact run report.
- Rerunning the same manifest was idempotent: file count stayed unchanged and yt-dlp skipped the archived video.
- Deliberate disconnect testing confirmed production doctor, preflight, and run fail closed while Lockdown blocks internet access.

## 2026-05-27 - Dry-Run Smoke Test Hardened

- Found and fixed a generated yt-dlp config quoting bug that caused output-template fragments to be parsed as URLs.
- Added JavaScript runtime detection to production doctor.
- Added `--js-runtimes` to generated yt-dlp configs when Node or Deno is available.
- Reran a production dry-run smoke test through Mullvad; it exited 0 with no ERROR/WARNING lines and no media download.

## 2026-05-27 - Production Lockdown and Cookie Policy Hardened

- Added production posture checks for Mullvad Lockdown, split tunneling, LAN sharing, and auto-connect.
- Made real downloads refuse non-production mode.
- Made `mullvad recover` enable Lockdown before reconnect attempts.
- Updated generated yt-dlp configs to use `--ignore-config`, `--no-cookies`, and `--no-cookies-from-browser`.
- Added preflight rejection for browser cookies, cookie files, account credentials, `.netrc`, and related auth options.
- Created [[Account Cookie Policy]] and updated runbooks, docs, and skill references.

## 2026-05-27 - Safe VPN Recovery Added

- Added `mullvad recover` for connected-state recovery.
- Added default `run` recovery for Mullvad disconnected preflight failures and transient network-looking yt-dlp failures.
- Added failure classification so source-side throttles, captchas, login challenges, blocks, and rate limits pause instead of triggering relay/IP switching.
- Added tests for source-block versus transient-network classification.

## 2026-05-27 - Codex Skill Suite Created

- Added `skills/legends-yt-dlp-slayer/SKILL.md` as the Codex operating procedure for the project.
- Added skill references for commands, batch cataloging, safety/error policy, and Mullvad controls.
- Added skill UI metadata in `skills/legends-yt-dlp-slayer/agents/openai.yaml`.
- Extended batch planning to support multiple URLs and `--from-file` URL catalogs.
- Added `catalog` command to list local batch manifests.
- Preserved the safety boundary: reconnect/retry is allowed for tunnel or transient failures, but automatic relay/IP switching to bypass source-side blocks remains out of scope.

## 2026-05-27 - Mullvad CLI Control Surface Unlocked

- Logged into Mullvad using the ignored local `.env` account value.
- Enabled Lockdown mode and connected the VPN.
- Turned auto-connect on.
- Verified `doctor --require-connected` now passes.
- Enumerated the installed `mullvad-cli 2026.2` command surface.
- Added first-class Slayer CLI wrappers for account, status, inspect, relay, DNS, tunnel, LAN, auto-connect, split tunnel, anti-censorship, API access, and raw passthrough.
- Added [[Mullvad Control Surface]] with the proven current state and command list.

## 2026-05-27 - GitHub Repository Created

- Created private GitHub repository `avalonreset-pro/legends-yt-dlp-slayer`.
- Renamed the local branch to `main` and pushed the current history.
- Added GitHub-facing README, CLI docs, architecture docs, safety policy, and changelog.
- Verified repo settings: private, default branch `main`, wiki disabled, projects disabled, private forking disabled.
- Verified access posture: org default repository permission is `none`, members cannot create repos, and repo team grants are empty.

## 2026-05-27 - CLI Scaffold and yt-dlp Install

- Added Python CLI package with `slayer` / `printing-press` entry points.
- Added `scripts/slayer.ps1` launcher for local PowerShell operation.
- Added commands for `doctor`, Mullvad status/login/connect/lockdown/raw, yt-dlp install/version, batch `plan`, `preflight`, and guarded `run`.
- Installed official Windows `yt-dlp.exe` to `.local/bin`, verified SHA256 against upstream `SHA2-256SUMS`, and confirmed version `2026.03.17`.
- Confirmed Mullvad CLI path and version, but batch preflight remains blocked until Mullvad is logged in, funded, and connected.

## 2026-05-27 - Initial Scaffold

- Created the Legends YT-DLP Slayer Codex Obsidian development vault.
- Chose combined Mode B/C/E for architecture, project planning, and research/compliance.
- Captured the original product idea in `.raw/idea/2026-05-27-user-brief.md`.
- Seeded source snapshots for Mullvad pricing, Mullvad CLI, and yt-dlp.
- Established product boundary: VPN privacy and fail-closed checks are in scope; relay rotation to bypass platform controls is out of scope.
