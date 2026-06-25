---
type: meta
title: "Hot Cache"
status: active
created: 2026-05-27
updated: 2026-06-24
tags: [hot-cache, meta]
---

# Hot Cache

## Last Updated

2026-06-24. v0.2.1 adds a yt-dlp freshness gate: managed builds older than 90 days fail readiness checks and point operators to `yt-dlp update`.

## Key Recent Facts

- Product boundary remains fixed: Mullvad is for privacy and leak prevention, not relay rotation to bypass throttling, captchas, login challenges, account controls, or blocks. Source-side controls pause and report.
- Mullvad lifecycle rule: `setup production` turns on the fail-closed posture before capture; terminal real `run --yes` calls shutdown by default unless `--keep-vpn` is passed.
- New `mullvad shutdown` command disables Lockdown before disconnecting with `--wait`, then verifies that Mullvad is no longer connected.
- Live Mullvad production posture is working: connected, Lockdown on, split tunneling off, LAN blocked, auto-connect on, Node JS runtime available.
- Official `yt-dlp.exe` is installed locally at `.local/bin` and reports `2026.06.09`.
- `doctor`, `onboard`, inventory, preflight, and production setup now fail managed `yt-dlp` builds older than 90 days, because stale extractors can break on fast-moving sites before the rest of production posture catches it.
- `slayer yt-dlp update` is an explicit alias for refreshing the managed official Windows binary with upstream checksum verification.
- A real user-provided YouTube video downloaded through Slayer into `C:\Users\rccol\Downloads\seedance20\...jK7ss4TvtcY.mp4`; ffprobe confirmed `1920x1080`, H.264, 30fps, 45.77s, 23,944,375 bytes.
- The broad `Downloads` output path exposed a verifier issue: old verifier counted unrelated local media. It is now hardened so `verify` counts ledger-scoped media and info JSON files only.
- Current `verify --no-probe` on the broad Downloads batch reports exactly 1 media file, 1 info JSON, 1 archive entry, 2 reports, and one downloaded ledger item.
- Folder policy now exists: `auto` puts direct multi-link plans into one named batch folder, keeps inventoried channel/playlist work grouped by uploader, and still allows explicit `batch`, `by-uploader`, or `flat`.
- The user-provided X status batch was flattened after download into `C:\Users\rccol\Downloads\x-status-videos-20260528`; ledger paths and manifest output were updated, and verify passes with 8 media files plus 8 info JSON sidecars.
- CrispASR/Parakeet is still the preferred ready-made ASR path. It runs locally without Codex/Claude token spend.
- `intelligence align nfa` now prepares NVIDIA NeMo Forced Aligner manifests, runs an external NeMo `align.py` when available, and imports NFA word CTM output into the existing word ledger.
- NFA import is strict: word count and normalized word sequence must match the existing ledger, or refinement fails for manual review. Successful imports create a `*.words.pre-nfa.jsonl` backup.
- Current local CrispASR binary is CPU-only: diagnostics report `ggml backends: cpu`. The machine has an RTX 4090, but this build is not GPU-enabled.
- Windows GPU build attempts found setup blockers, not application blockers: CUDA builds are blocked by the installed Visual Studio/CUDA host-compiler pairing, and Vulkan builds need the Vulkan SDK installed.
- New `intelligence doctor --require-gpu` and `intelligence transcribe --gpu-backend ... --require-gpu` gates prevent the product from claiming GPU readiness unless CrispASR diagnostics report CUDA/Vulkan/Metal-style support.
- Generated-speech and real downloaded-video intelligence smokes already proved transcript import, exact word search, clip planning/rendering, and vault export. Historical NASA evidence exists in the log, but new manual validation should use `smoke plan --url` with an operator-verified source.
- Standard SOP: consult user, inventory/plan, review ledger, production preflight, dry-run, explicit approval, real run, verify, refresh/review ledger. Run intelligence only when requested, clearly useful, or explicitly proposed and accepted.
- Full unit gate after latest hardening: 69 tests pass.

## Recent Changes

- Hardened `src/slayer_cli/ledger.py` and `src/slayer_cli/verify.py` around broad output folders.
- Added output folder policies to batch planning and inventory.
- Added CrispASR diagnostics parsing, GPU-required doctor/transcribe flags, docs, and regression tests.
- Added contradictory GPU flag rejection for `intelligence transcribe` so CPU-forced and GPU-required modes cannot be mixed.
- Added the NeMo Forced Aligner refinement bridge, docs, wiki runbook, and regression tests.
- Added default post-run Mullvad shutdown, `run --keep-vpn`, `mullvad shutdown`, docs, and regression tests.
- Updated README, CLI, and CrispASR/intelligence docs with CPU-vs-GPU truth gates.
- Added yt-dlp freshness checks, `yt-dlp update`, and v0.2.1 release/package docs.

## Active Threads

- Next technical gate: build or obtain a GPU-enabled CrispASR binary and confirm diagnostics report CUDA or Vulkan before calling the ASR path GPU-ready.
- Next alignment gate: validate `intelligence align nfa` against a real NeMo/CUDA environment and import a real CTM before describing local NFA runtime as verified.
- Legacy count-based smoke fixtures still exist for compatibility, but docs/onboarding now steer new validation to `smoke plan --url`.
- Current release gate: `0.2.1-alpha` package built under `dist/`; tag/release after final GitHub publish.
