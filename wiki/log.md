---
type: meta
status: active
created: 2026-05-27
updated: 2026-05-28
tags: [log, meta]
---

# Log

## 2026-05-28 - First-Run Walkthrough Added

- Added `slayer onboard` as a non-mutating first-run guide that prints readiness, missing setup steps, interview prompts, reference docs, and the next safe commands.
- Added JSON/strict onboarding modes for automation and machine-readable setup status.
- Added `docs/WALKTHROUGH.md`, batch intake template, rights evidence template, and example URL file.
- Updated README, CLI docs, SOP, architecture notes, skill command reference, changelog, roadmap, and hot cache around the onboarding workflow.

## 2026-05-28 - Alpha Packaging and GitHub Presence Hardened

- Added MIT license, `NOTICE`, `SECURITY.md`, `CITATION.cff`, `CONTRIBUTING.md`, code of conduct, issue templates, PR template, and release config.
- Added `scripts/package-alpha.ps1`, `docs/PACKAGING.md`, and `docs/LEGAL.md`; package output includes source/docs/scripts/tests/skill/legal files while excluding `.env`, `.local`, batches, reports, media, cookies, caches, secrets, and git metadata.
- Verified upstream license posture with GitHub API: `yt-dlp/yt-dlp` reports Unlicense and `mullvad/mullvadvpn-app` reports GPL-3.0; current package does not bundle either binary.
- Clean-clone test passed from a temp clone: `yt-dlp install`, checksum verification, `doctor --production`, smoke planning, preflight, and dry-run all succeeded, then the temp clone was deleted.
- Resume/interruption harness passed: a fake yt-dlp interrupted after one item, ledger refreshed to one downloaded/one planned, rerun skipped the archived item and completed the second, and `verify --no-probe` passed with two downloaded ledger items.
- Updated live GitHub metadata: stronger description, discussions enabled, and topics expanded for yt-dlp, Mullvad VPN, digital preservation, privacy tools, Codex skill, and operator tooling.

## 2026-05-28 - Item Ledger and Inventory Implemented

- Added first-class item ledger support: every new batch writes `items.jsonl`, preflight checks it, run reports include ledger counts, and `verify` refreshes ledger state from archive entries, info JSON sidecars, and media files.
- Added `inventory` to expand a channel, playlist, or source URL into a reviewable batch without downloading media; source-side warnings pause without creating a batch.
- Added `ledger` to summarize, filter, refresh, and JSON-export item ledger state.
- Added optional `--rights-file` copying into batch `rights/` folders.
- Live production evidence: `doctor --production` passed with Mullvad connected and Lockdown on; NASA Goddard inventory smoke created 1 inventoried ledger item; curated NASA real smoke downloaded 1 MP4, wrote 1 archive entry and 1 info JSON, passed `verify`/ffprobe, and refreshed ledger to `downloaded: 1`.
- Verification: 39 unit tests passed, compileall passed, vault health passed, and the Mullvad account secret scan found no committed leakage outside ignored files.

## 2026-05-28 - Item Ledger and Inventory SOP Productized

- Updated README, CLI docs, SOP, and Codex skill reference around the standard item-ledger workflow.
- Documented channel/playlist `inventory`, `items.jsonl`, `ledger --refresh`, and `--rights-file` as the reviewable planning path before real downloads.
- Reaffirmed the safety boundary: no relay rotation, account switching, captcha/login automation, or continuation through source-side throttles, account controls, or blocks.
- Updated roadmap/release surfaces to make inventory planning, rights evidence, verification, and ledger review part of the v0.1.0 operating story.

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

## 2026-05-28 - Post-Capture Intelligence Research Added

- Researched timestamp precision, forced alignment, diarization, and clip extraction for a lawful local video intelligence module.
- Ranked NVIDIA NeMo + Parakeet as the default ASR path because current primary sources document local Parakeet word/segment timestamps and commercial/non-commercial use for v2/v3 model cards.
- Ranked NeMo Forced Aligner as the precision/refinement path for compatible CTC or hybrid CTC models, with CTM/ASS output suited to a Slayer word ledger.
- Ranked pyannote.audio as optional diarization and WhisperX/stable-ts/MFA/ctc-segmentation as fallback or advanced paths.
- Added [[Local Transcription and Clip Extraction Stack 2026-05-28]] and updated research index, hot cache, and roadmap.
- Verification after filing: 41 unit tests passed, vault health passed, and `git diff --check` passed.

## 2026-05-28 - Post-Capture Intelligence MVP Added

- Added `src/slayer_cli/intelligence.py` as the standard-library intelligence core.
- Added `slayer intelligence init`, `doctor`, `status`, `ingest-words`/`import-words`, `search`, `clips plan`, `clips render`, and `vault build` commands.
- The MVP accepts timestamped JSONL or JSON word input, normalizes it into `intelligence/words/*.words.jsonl`, exact-searches contiguous normalized tokens, writes search results, generates reviewable FFmpeg clip plans, and exports transcript vault pages.
- Added `docs/INTELLIGENCE.md`, `examples/intelligence-words.jsonl`, tests, and updated README/CLI/architecture/NOTICE/skill docs.
- Preserved the boundary: intelligence analyzes already-downloaded lawful local media only and does not download, call yt-dlp, operate Mullvad, rotate relays, or continue through source-side controls.
- Verification after implementation: 46 unit tests passed, compileall passed, vault health passed, and `git diff --check` passed.

## 2026-05-28 - CrispASR Parakeet Backend Selected

- Researched ready-made Parakeet transcription tools and selected CrispASR with Parakeet TDT v3 GGUF as the preferred backend for Slayer intelligence.
- Added `find_crispasr`, `slayer intelligence transcribe`, and `slayer intelligence import-crispasr` so Slayer can call an external CrispASR executable or ingest its full JSON output.
- Added robust CrispASR JSON parsing into normalized Slayer word ledgers, preserving exact search and clip-plan behavior.
- Added `docs/CRISPASR.md` and updated intelligence docs, CLI docs, README, architecture, NOTICE, roadmap, skill reference, and tests.
- NeMo remains the upstream/reference route, but the product path is now a ready-made local CLI instead of a custom ASR runner.
- Local backend evidence: cloned CrispASR into ignored `.local`, built `crispasr.exe` with MinGW/Ninja using `_WIN32_WINNT=0x0601`, copied it to `.local/bin`, and confirmed Slayer discovers it.
- End-to-end intelligence smoke passed on a generated local speech WAV: CrispASR/Parakeet produced 6 token-timed word rows, exact search found `agentic workflow`, clip plan/render succeeded, and vault export wrote the transcript page.
- Real downloaded-video evidence: planned, preflighted, dry-ran, downloaded, verified, and ledger-refreshed NASA Goddard `Venus in a Minute` through Slayer with Mullvad production posture on. CrispASR/Parakeet produced 153 token-timed word rows, exact search found 5 `venus` hits and 1 `oceans of water` hit, FFmpeg rendered a 5-clip `venus` montage, and vault export wrote the transcript page.
- The real-video smoke caught a transcript filename bug in `transcribe_with_crispasr`; fixed the wrapper to expect `<video>.crispasr.json` and added regression coverage.

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
