# Standard Operating Procedure

This is the normal operator path for Legends YT-DLP Slayer. It is intentionally slow: consult the user, inventory sources, create an item ledger, preflight, dry-run, run only with explicit approval, verify, review the ledger, and stop on source blocks.

## 1. Consult The User

Start with the guided local readiness check:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 onboard
```

Before creating or running a batch:

- remind the user to use downloaded material only when they have rights, permission, a license, a valid fair-use basis, or another lawful basis
- the exact channel, playlist, or video URLs to inventory
- whether the job would benefit from an optional rights note or evidence file
- desired limits such as maximum items, height, filesize, or download count
- where outputs should go, if the default batch output folder is not enough
- whether outputs should use one batch folder, uploader folders, or a flat folder

## 2. Inventory Source URLs

For channel or playlist work, use inventory before downloads:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 inventory "https://www.youtube.com/@CHANNEL" --rights-file ".\rights-evidence.md" --name "client-or-project-name"
```

For a hand-curated URL list, create a URL file with one authorized URL per line:

```text
https://www.youtube.com/watch?v=...
https://www.youtube.com/watch?v=...
```

Then plan it:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan --from-file ".\urls.txt" --rights "optional permission/license/fair-use note" --rights-file ".\rights-evidence.md" --name "client-or-project-name"
```

The batch folder contains the manifest, URL list, `yt-dlp.conf`, copied rights evidence when provided, and `items.jsonl`. `--rights` and `--rights-file` are optional metadata fields, not hard gates.

Use folder policy deliberately:

- mixed ad hoc links: prefer `--folder-policy batch`, which keeps the whole request in one named folder under `--output`;
- channel, playlist, or multi-source archive work: prefer `--folder-policy by-uploader`, especially when the user will compare creators or source scopes;
- one-off local staging: use `--folder-policy flat` only when the output folder already represents the job.

`--folder-policy auto` applies those defaults: direct multi-link plans become one batch folder, while inventoried channel/playlist work stays grouped by uploader.

## 3. Review The Item Ledger

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 ledger "batches\...\manifest.json"
```

Review the source URL, item count, titles, statuses, limits, and any optional rights evidence with the user. Do not continue to a run if the inventory includes unexpected items or source-side block signals.

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

Production posture is for active capture. After a real batch reaches a terminal state, the default `run --yes` behavior is to turn Lockdown mode off, disconnect Mullvad with `--wait`, and verify the disconnected state.

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

Before invoking `yt-dlp`, `run --yes` prints a short legal-use notice reminding operators to download only when they have rights, permission, a license, fair use, or another lawful basis, and to follow applicable laws and platform terms.

After `yt-dlp` stops, `run --yes` shuts Mullvad down by default. Use `--keep-vpn` only when the operator intentionally wants to leave the tunnel and Lockdown running for more immediate capture work.

Reruns are expected to be idempotent. Completed video IDs are stored in `archive.txt`; rerunning the same manifest should skip completed IDs instead of duplicating files.

## 8. Ledger Review

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 ledger "batches\...\manifest.json" --refresh
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 ledger "batches\...\manifest.json" --status downloaded --limit 50
```

Check final item counts, downloaded or archived statuses, warnings, bytes, output paths, info JSON sidecars, and verification status. Preserve optional rights evidence files with the batch when the operator supplied them.

This is the stopping point for a plain download/archive request. Do not automatically transcribe every verified batch. Offer or run `slayer intelligence` only when the user asks for transcripts, exact search, clip extraction, a transcript vault, or when the job context clearly needs post-capture analysis.

## 9. Stop Conditions

Stop and review when any of these occur:

- source-side throttle, captcha, login challenge, account-control, block, or HTTP 429
- `verify` fails
- production doctor fails
- Mullvad recovery fails
- media probe fails

Do not rotate relays or accounts to continue through source-side throttles, captchas, login/account controls, or blocks. Relay/location controls are manual operator controls for connectivity posture, not a bypass mechanism.

## 10. Safe VPN Test

Use only the guarded command:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad disconnect-test --emergency-unlock
```

It verifies fail-closed Lockdown behavior and reconnects before returning. Raw `mullvad disconnect` refuses by default when Lockdown is on.

For normal end-of-work cleanup, use:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad shutdown
```

That command disables Lockdown before disconnecting, then verifies that Mullvad is no longer connected.
