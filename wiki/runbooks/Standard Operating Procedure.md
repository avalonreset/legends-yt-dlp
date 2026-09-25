---
type: runbook
status: active
created: 2026-05-28
updated: 2026-05-28
tags: [runbook, sop, operator]
---

# Standard Operating Procedure

## Production Setup

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 setup production
```

This applies the expected Mullvad posture and verifies `doctor --production`.

## Install Validation

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 smoke plan --url "<authorized-video-url>" --name first-smoke
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 preflight "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 run "batches\...\manifest.json" --dry-run
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 run "batches\...\manifest.json" --yes
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 verify "batches\...\manifest.json"
```

Current live evidence includes historical bundled smoke tests and a user-provided 1080p single-video download. Future manual validation should use operator-provided authorized smoke URLs.

## Real Batch

1. Create a URL file with one authorized URL per line.
2. Plan with a specific rights basis.
3. Run preflight.
4. Run dry-run.
5. Run real download with `--yes`.
6. Run `verify`.
7. Rerun only when needed; archive entries should skip completed IDs.

## Stop Conditions

- source-side throttle, captcha, login challenge, block, or HTTP 429
- production doctor failure
- preflight failure
- verify failure
- Mullvad recovery failure
- unclear rights basis

Do not rotate relays to continue through source-side blocks.
