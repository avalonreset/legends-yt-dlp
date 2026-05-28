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

2026-05-28. Real user download, ledger-scoped verification, and Parakeet/CrispASR GPU truth-gating are the latest hardening slice.

## Key Recent Facts

- Product boundary remains fixed: Mullvad is for privacy and leak prevention, not relay rotation to bypass throttling, captchas, login challenges, account controls, or blocks. Source-side controls pause and report.
- Live Mullvad production posture is working: connected, Lockdown on, split tunneling off, LAN blocked, auto-connect on, Node JS runtime available.
- Official `yt-dlp.exe` is installed locally at `.local/bin` and reports `2026.03.17`.
- A real user-provided YouTube video downloaded through Slayer into `C:\Users\rccol\Downloads\seedance20\...jK7ss4TvtcY.mp4`; ffprobe confirmed `1920x1080`, H.264, 30fps, 45.77s, 23,944,375 bytes.
- The broad `Downloads` output path exposed a verifier issue: old verifier counted unrelated local media. It is now hardened so `verify` counts ledger-scoped media and info JSON files only.
- Current `verify --no-probe` on the broad Downloads batch reports exactly 1 media file, 1 info JSON, 1 archive entry, 2 reports, and one downloaded ledger item.
- Folder policy now exists: `auto` puts direct multi-link plans into one named batch folder, keeps inventoried channel/playlist work grouped by uploader, and still allows explicit `batch`, `by-uploader`, or `flat`.
- The user-provided X status batch was flattened after download into `C:\Users\rccol\Downloads\x-status-videos-20260528`; ledger paths and manifest output were updated, and verify passes with 8 media files plus 8 info JSON sidecars.
- CrispASR/Parakeet is still the preferred ready-made ASR path. It runs locally without Codex/Claude token spend.
- Current local CrispASR binary is CPU-only: diagnostics report `ggml backends: cpu`. The machine has an RTX 4090, but this build is not GPU-enabled.
- Windows GPU build attempts found setup blockers, not application blockers: CUDA builds are blocked by the installed Visual Studio/CUDA host-compiler pairing, and Vulkan builds need the Vulkan SDK installed.
- New `intelligence doctor --require-gpu` and `intelligence transcribe --gpu-backend ... --require-gpu` gates prevent the product from claiming GPU readiness unless CrispASR diagnostics report CUDA/Vulkan/Metal-style support.
- Generated-speech and real downloaded-video intelligence smokes already proved transcript import, exact word search, clip planning/rendering, and vault export. Historical NASA evidence exists in the log, but new manual validation should use `smoke plan --url` with an operator-verified source.
- Standard SOP: consult user, inventory/plan, review ledger, production preflight, dry-run, explicit approval, real run, verify, refresh/review ledger, then optionally run intelligence.
- Full unit gate after latest hardening: 54 tests pass; compileall, diff check, and vault health pass.

## Recent Changes

- Hardened `src/slayer_cli/ledger.py` and `src/slayer_cli/verify.py` around broad output folders.
- Added output folder policies to batch planning and inventory.
- Added CrispASR diagnostics parsing, GPU-required doctor/transcribe flags, docs, and regression tests.
- Added contradictory GPU flag rejection for `intelligence transcribe` so CPU-forced and GPU-required modes cannot be mixed.
- Updated README, CLI, and CrispASR/intelligence docs with CPU-vs-GPU truth gates.

## Active Threads

- Next technical gate: build or obtain a GPU-enabled CrispASR binary and confirm diagnostics report CUDA or Vulkan before calling the ASR path GPU-ready.
- Legacy count-based smoke fixtures still exist for compatibility, but docs/onboarding now steer new validation to `smoke plan --url`.
- Optional release gate after more review: package/tag `v0.1.0-alpha`.
