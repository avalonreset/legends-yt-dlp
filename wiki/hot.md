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

2026-05-28. Item-ledger/inventory planning, clean-clone install, resume behavior, legal/community files, packaging, GitHub metadata, first-run onboarding, and the first post-capture intelligence MVP are now hardened enough for alpha planning.

## Key Recent Facts

- Product boundary: Mullvad is for privacy and leak prevention, not IP rotation to bypass YouTube throttling, captchas, login challenges, account controls, or blocks. Source-side block signals pause and report.
- Mullvad CLI was found at the installed app path and reports `mullvad-cli 2026.2`.
- Official `yt-dlp.exe` was installed locally to `.local/bin`, verified by SHA256, and reports version `2026.03.17`.
- GitHub repo `avalonreset-pro/legends-yt-dlp-slayer` is private on `main`, has no team grants, and has wiki/projects/forking disabled.
- Current live Mullvad posture verified with `doctor --production`: connected, Lockdown on, split tunneling off, LAN blocked, auto-connect on, Node JS runtime available.
- CLI now supports `plan`, `inventory`, `ledger`, `preflight`, `run`, `verify`, `catalog`, `setup production`, curated `smoke plan`, Mullvad wrappers, and yt-dlp install/version.
- Every new batch now writes `items.jsonl`; preflight checks it; run reports include ledger counts and next action; `verify` refreshes ledger state from archive/info-json/media artifacts.
- `inventory` expands a channel/playlist/source into a batch without media downloads and pauses if source-side warnings are detected.
- `--rights-file` copies permission/license evidence into the batch `rights` folder.
- Standard SOP: consult user, inventory source URLs, review ledger, production preflight, dry-run, explicit approval, real run, verify, refresh/review ledger.
- Live inventory smoke passed on `https://www.youtube.com/@NASAGoddard/videos` with `--max-items 1`, creating one inventoried ledger item.
- Live real smoke passed on curated NASA video `LeUcjqqhNxM`: dry-run passed, real run downloaded 1 MP4, wrote 1 archive entry and 1 info JSON, `verify` passed ffprobe, and ledger refreshed to `downloaded: 1`.
- Clean-clone test passed from a temp clone: local `yt-dlp.exe` install/checksum, production doctor, smoke plan, preflight, and dry-run.
- Resume/interruption harness passed: first run stopped after one fake item, ledger showed one downloaded and one planned, rerun skipped archived first item, completed second item, verify passed with two downloaded ledger items.
- Legal/community layer added: MIT `LICENSE`, `NOTICE`, `SECURITY.md`, `CITATION.cff`, `CONTRIBUTING.md`, code of conduct, issue templates, PR template, and release config.
- Packaging added: `scripts/package-alpha.ps1` builds `dist/legends-yt-dlp-slayer-0.1.0-alpha.zip` plus SHA256 and excludes secrets/runtime outputs.
- First-run onboarding added: `slayer onboard` prints readiness, missing setup steps, the user interview checklist, reference docs, and the next safe commands without mutating state.
- Walkthrough/examples added: `docs/WALKTHROUGH.md`, `examples/batch-intake.md`, `examples/rights-evidence-template.md`, and `examples/urls.txt`.
- Live GitHub metadata updated: stronger description, discussions enabled, topics expanded for `yt-dlp`, Mullvad VPN, digital preservation, privacy tools, and operator tooling.
- New post-capture intelligence research now recommends a ready-made Parakeet-first path: CrispASR with Parakeet TDT v3 GGUF as the preferred local CLI backend, with NeMo/Parakeet kept as the upstream/reference fallback.
- The intelligence module should store a structured word ledger, not plain transcript text, so exact word/phrase search can return FFmpeg-ready clip spans.
- `slayer intelligence` now has an MVP command surface for workspace init, doctor/status, CrispASR transcription/import, timestamped word import, exact word/phrase search, clip-plan generation, optional FFmpeg rendering, and Obsidian transcript vault export.
- Local CrispASR build succeeded in ignored `.local` with MinGW/Ninja and is discoverable at `.local/bin/crispasr.exe`.
- End-to-end generated speech smoke passed: Parakeet transcript import produced 6 token-timed word rows; exact search, clip plan/render, and transcript vault export all worked.
- Real downloaded-video smoke passed on NASA Goddard `Venus in a Minute`: production preflight, dry-run, real download, verify, ledger refresh, CrispASR/Parakeet transcription, exact search, clip montage rendering, and vault export all worked.
- Unit gate: 50 tests pass; compileall passes; package inspection passes; vault health/secret scan are part of the final gate.

## Recent Changes

- Added `src/slayer_cli/ledger.py`, `src/slayer_cli/inventory.py`, `src/slayer_cli/onboarding.py`, alpha packaging, examples, and GitHub legal/community files.
- Updated README, CLI docs, SOP, architecture, safety policy, legal/packaging docs, skill reference, roadmap, release plan, changelog, and tests.

## Active Threads

- Next release gate is deciding whether to tag/publish `v0.1.0-alpha` with the generated zip after user review.
- New product track for the next development slice: package the CrispASR install/build helper and decide how much of the ignored local backend smoke should become a repeatable documented operator test.
- Existing older manifests may fail production preflight until regenerated because they lack the newer anonymous-auth and limit policy flags.
- Next GitHub step is optional: create a first alpha tag after reviewing the pushed hardening commit.
