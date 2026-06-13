# Changelog

## Unreleased

- No unreleased changes yet.

## 0.1.0 - 2026-06-13

- Created the initial private development vault and repository scaffold.
- Added the first Python CLI control plane.
- Added Mullvad CLI detection and wrappers.
- Added official `yt-dlp.exe` download and checksum verification.
- Added batch planning, preflight, and guarded run commands.
- Added GitHub-facing documentation.
- Added the Codex skill suite under `skills/legends-yt-dlp-slayer`.
- Added multi-URL / URL-file batch planning and batch catalog listing.
- Added safe VPN recovery for disconnected Mullvad/tunnel/network failures.
- Added production Lockdown/auth-cookie hardening.
- Added JavaScript runtime detection/configuration for YouTube dry-runs.
- Fixed yt-dlp config quoting for output templates and paths with spaces.
- Added bounded smoke-job limits and compact run reports.
- Added guarded Mullvad disconnect testing with automatic recovery and an emergency unlock fallback.
- Added `setup production`, curated `smoke plan`, and batch `verify` commands.
- Added media verification through ffprobe and Unicode-safe console output.
- Made dry-runs suppress raw yt-dlp JSON unless `--show-output` is passed.
- Added channel/playlist `inventory` planning that creates reviewable item ledgers before downloads.
- Added `items.jsonl` per-item ledgers, `ledger` inspection/refresh commands, and ledger summaries in run reports and verification.
- Added optional `--rights-file` evidence copying into batch folders.
- Made inventory pause on source-side warning signals instead of turning questionable sources into batches.
- Added MIT license, NOTICE, SECURITY.md, CITATION.cff, contribution/community templates, issue templates, and pull request template.
- Added alpha packaging script and packaging/legal docs.
- Added `onboard` first-run guidance command, walkthrough docs, and batch intake/rights evidence examples.
- Added `slayer intelligence` MVP for post-download word-ledger import, exact phrase search, FFmpeg clip planning/rendering, and Obsidian transcript vault export.
- Added CrispASR/Parakeet as the preferred ready-made transcription backend with `intelligence transcribe` and `import-crispasr`.
- Added `intelligence align nfa` for NVIDIA NeMo Forced Aligner manifest prep, word CTM import, and strict word-ledger timing refinement.
- Fixed CrispASR transcript artifact naming after a real downloaded-video smoke test and added regression coverage.
- Hardened `verify` to count ledger-scoped media/info artifacts so broad output folders such as `Downloads` do not inflate batch verification.
- Added CrispASR diagnostics parsing plus GPU-required doctor/transcribe gates for honest CPU-vs-GPU Parakeet operation.
- Made `intelligence transcribe` reject contradictory GPU flags before launching ASR.
- Added `smoke plan --url` so new validation can use operator-provided authorized smoke sources instead of the legacy built-in fixtures.
- Added output folder policies so direct multi-link plans can land in one named batch folder while channel/playlist inventory can remain grouped by uploader.
- Clarified that transcription/intelligence is an optional post-capture workflow, not mandatory for every download.
- Added the WebP README banner and updated the public-facing project positioning around creator source capture and clip-building.
- Hardened alpha packaging so local work folders, release experiments, and media artifacts stay out of distribution zips.
