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

2026-05-28. Item-ledger and inventory planning are now implemented, documented, and live-smoke verified under production Mullvad posture.

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
- Unit gate: 39 tests pass; compileall passes; vault health passes; secret scan found no Mullvad account leakage outside ignored files.

## Recent Changes

- Added `src/slayer_cli/ledger.py` and `src/slayer_cli/inventory.py`.
- Updated README, CLI docs, SOP, safety policy, skill reference, roadmap, release plan, changelog, and tests around the inventory/ledger workflow.

## Active Threads

- Next release gate is alpha packaging and license/upstream notice review.
- Existing older manifests may fail production preflight until regenerated because they lack the newer anonymous-auth and limit policy flags.
- Next GitHub step is optional: create a first alpha tag after reviewing the pushed hardening commit.
