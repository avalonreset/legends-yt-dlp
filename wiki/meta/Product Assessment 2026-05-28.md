---
type: assessment
status: active
created: 2026-05-28
updated: 2026-05-28
tags: [product, assessment, roadmap, release]
---

# Product Assessment 2026-05-28

## Current Read

Legends YT-DLP has moved from proof-of-concept into a credible private alpha. The core loop is real: production posture, curated smoke validation, anonymous yt-dlp batch execution, compact reports, artifact verification, idempotent reruns, and a fail-closed VPN posture have all been implemented and tested on Windows.

The product is not yet a polished community release. It is strong enough for supervised operator use, but it still needs release packaging, clearer first-run ergonomics, richer per-item state, and a better public-facing product story before it should be handed to normal users.

## What Is Strong

- **Safety posture is coherent.** Real downloads require production VPN posture, Lockdown, anonymous yt-dlp config, no browser cookies, no account auth, and explicit `--yes`.
- **The failure boundary is defensible.** Tunnel/network problems can recover; source-side throttles, captchas, login challenges, and blocks pause instead of triggering relay rotation.
- **The workflow is now understandable.** `setup production`, `smoke plan`, `preflight`, `run`, and `verify` make a clear standard operating procedure.
- **The smoke path is real.** The five-video NASA Goddard pack downloaded 5 MP4 files, 5 info JSON files, wrote 5 archive entries, generated reports, passed ffprobe, and reran idempotently.
- **The vault is functioning as development memory.** Hot cache, log, SOP, runbooks, architecture, compliance notes, and roadmap are all present.

## Weak Areas

- **Per-item state is too thin.** `archive.txt` proves completed IDs, but the product should have a structured item ledger with URL, title, ID, status, attempts, output path, bytes, duration, warnings, and final disposition.
- **Successful-run warnings need more UX.** The runner now classifies source warnings, but operators need a clearer summary after a run: clean, completed with warnings, paused, failed, or needs review.
- **Install and release packaging are not finished.** A community user still needs repo checkout plus local prerequisites. There is no one-shot installer, release artifact, or versioned alpha package.
- **Rights workflow is honest but manual.** The CLI requires a rights basis, but it does not help users collect or preserve proof beyond a text string.
- **Channel-scale planning is not yet rich enough.** There is no inventory-only mode that expands a channel/playlist into a reviewed manifest before download.
- **No dashboard or operator TUI.** The CLI works, but larger jobs will want a readable status view over batches, reports, warnings, and remaining items.
- **Cross-platform story is deferred.** Windows-first is correct for this stage, but macOS/Linux support and Mullvad path differences remain open.
- **License/distribution posture is unresolved.** The repo says license is not finalized; a public/community release needs a clear license and upstream notices.

## Next Product Priorities

1. **Structured item ledger.** Add `items.jsonl` or `items.csv` per batch and update it after dry-run, real run, and verify.
2. **Run summary UX.** Print a concise final summary from reports: downloaded, skipped, failed, warnings, bytes, and next action.
3. **Inventory mode.** Add a safe `inventory` command that expands explicit URLs/playlists/channels into reviewable metadata without downloading.
4. **Rights evidence file.** Add optional `--rights-file` to attach notes, URLs, permission text, or license evidence to a batch.
5. **Alpha packaging.** Decide install shape: zip release, PowerShell setup script, or Python package with managed local binaries.
6. **Release checklist.** Turn the SOP into a `v0.1.0-alpha` gate with commands and expected outputs.
7. **Public docs polish.** Add screenshots or terminal transcript snippets so users understand the workflow without reading all internals.

## Product Judgment

The product is now useful, but the experience is still more "powerful operator tool" than "community-ready suite." The next big quality jump is not more VPN control. It is better state, better summaries, better release packaging, and better guardrails around what happened per video.

The system should feel like a careful archive appliance: it sets posture, plans work, proves rights, downloads slowly, records evidence, verifies outputs, and tells the operator exactly what is safe to do next.
