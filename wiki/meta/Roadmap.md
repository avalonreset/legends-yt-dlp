---
type: roadmap
status: active
created: 2026-05-27
updated: 2026-05-28
tags: [roadmap, meta]
---

# Roadmap

## Phase 0 - Vault and Product Boundary

- Create development vault.
- Capture user brief.
- Seed source notes.
- Define lawful-use boundary.
- Define MVP architecture.

## Phase 1 - CLI Skeleton

- Choose implementation language.
- Create package scaffold.
- Implement command parser.
- Implement config paths.
- Implement structured logging.

## Phase 2 - Doctor and Preflight

- Detect Mullvad CLI.
- Detect yt-dlp.
- Detect ffmpeg.
- Verify output paths.
- Implement rights-basis validation.
- Produce preflight report.

## Phase 3 - Batch Execution

- Create batch manifest format.
- Generate yt-dlp config.
- Run yt-dlp as a child process.
- Track item status.
- Support resume.
- Stop on block signals.

## Phase 4 - Community Alpha

- Write install docs.
- Package for Windows with `scripts/package-alpha.ps1`.
- Run lawful sample smoke tests.
- Publish alpha release notes after user review.

## Phase 5 - Productization Priorities

- Confirm and harden the structured per-item ledger with URL, ID, title, status, attempts, warnings, output path, bytes, and duration.
- Add a concise run summary that reports downloaded, skipped, failed, warning, and verification counts.
- Confirm and harden inventory-only planning for channels and playlists before any download.
- Keep optional rights evidence files for permission/license proof attached to each batch.
- Keep the product SOP centered on consult user, inventory, ledger review, preflight, dry-run, approved real run, verify, and final ledger review.
- Preserve stop-on-source-block behavior: no relay rotation to continue through throttles, captchas, login/account controls, or blocks.
- Current v0.1.0-alpha packaging choice: source zip plus SHA256 generated under `dist/`.
- License/upstream notice posture is now MIT plus `NOTICE`; continue to avoid bundling yt-dlp or Mullvad binaries.
- Improve public docs with a complete smoke-pack transcript and expected outputs before a wider community announcement.
