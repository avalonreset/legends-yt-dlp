# Standard Operating Procedure

This is the normal operator path for Legends YT-DLP Slayer. It is intentionally slow: consult the user, inventory sources, create an item ledger, preflight, dry-run, run only with explicit approval, verify, review the ledger, and stop on source blocks.

## 1. Consult The User

Start with the guided local readiness check:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 onboard
```

Before creating or running a batch, confirm:

- the user owns the videos, has permission, or has a license/public-domain basis
- the exact channel, playlist, or video URLs to inventory
- whether the job needs a rights evidence file
- desired limits such as maximum items, height, filesize, or download count
- where outputs should go, if the default batch output folder is not enough

If the rights basis is unclear, stop before inventory or planning.

## 2. Inventory Source URLs

For channel or playlist work, use inventory before downloads:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 inventory "https://www.youtube.com/@CHANNEL" --rights "owned or authorized" --rights-file ".\rights-evidence.md" --name "client-or-project-name"
```

For a hand-curated URL list, create a URL file with one authorized URL per line:

```text
https://www.youtube.com/watch?v=...
https://www.youtube.com/watch?v=...
```

Then plan it:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan --from-file ".\urls.txt" --rights "owned or authorized" --rights-file ".\rights-evidence.md" --name "client-or-project-name"
```

The batch folder contains the manifest, URL list, `yt-dlp.conf`, copied rights evidence when provided, and `items.jsonl`.

## 3. Review The Item Ledger

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 ledger "batches\...\manifest.json"
```

Review the source URL, item count, titles, statuses, limits, and rights evidence with the user. Do not continue to a run if the inventory includes unexpected items, unclear rights, or source-side block signals.

## 4. Set Production Posture

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 setup production
```

This sets Mullvad to a conservative Windows production posture:

- relay constraint defaults to `us`
- Lockdown mode on
- auto-connect on
- LAN sharing blocked
- split tunneling off
- quantum-resistant tunnel on
- IPv6 off
- VPN connected or recovered
- production doctor verified

## 5. Validate The Install

Create a small authorized smoke batch:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 smoke plan --url "https://www.youtube.com/watch?v=..." --name "first-smoke"
```

Then run the standard batch gate:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --dry-run
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --yes
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 verify "batches\...\manifest.json"
```

Dry-runs suppress raw `yt-dlp` JSON by default. Add `--show-output` only when debugging extractor output.

## 6. Preflight And Dry-Run

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --dry-run
```

For cautious first runs, create or inventory the batch with bounds such as `--max-height 360`, `--max-filesize 75M`, `--max-downloads 5`, or `--max-items 50`.

Review dry-run output and the run report. If the dry-run surfaces source-side throttling, captcha, login challenge, account-control, block, or repeated HTTP 429 signals, stop.

## 7. Real Run And Verify

Run only after the user approves the real download:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --yes
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 verify "batches\...\manifest.json"
```

Reruns are expected to be idempotent. Completed video IDs are stored in `archive.txt`; rerunning the same manifest should skip completed IDs instead of duplicating files.

## 8. Ledger Review

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 ledger "batches\...\manifest.json" --refresh
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 ledger "batches\...\manifest.json" --status downloaded --limit 50
```

Check final item counts, downloaded or archived statuses, warnings, bytes, output paths, info JSON sidecars, and verification status. Preserve the rights evidence file with the batch as part of the audit trail.

## 9. Stop Conditions

Stop and review when any of these occur:

- source-side throttle, captcha, login challenge, account-control, block, or HTTP 429
- `verify` fails
- production doctor fails
- Mullvad recovery fails
- media probe fails
- rights basis is unclear

Do not rotate relays or accounts to continue through source-side throttles, captchas, login/account controls, or blocks. Relay/location controls are manual operator controls for connectivity posture, not a bypass mechanism.

## 10. Safe VPN Test

Use only the guarded command:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad disconnect-test --emergency-unlock
```

It verifies fail-closed Lockdown behavior and reconnects before returning. Raw `mullvad disconnect` refuses by default when Lockdown is on.
