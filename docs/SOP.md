# Standard Operating Procedure

This is the normal operator path for Legends YT-DLP Slayer.

## 1. Set Production Posture

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

## 2. Validate The Install

Create the curated five-video NASA Goddard smoke batch:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 smoke plan --count 5
```

Then run the standard batch gate:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --dry-run
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --yes
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 verify "batches\...\manifest.json"
```

Dry-runs suppress raw `yt-dlp` JSON by default. Add `--show-output` only when debugging extractor output.

## 3. Plan A Real Batch

Create a URL file with one authorized URL per line:

```text
https://www.youtube.com/watch?v=...
https://www.youtube.com/watch?v=...
```

Plan the batch with a specific rights basis:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan --from-file ".\urls.txt" --rights "owned or authorized" --name "client-or-project-name"
```

For cautious first runs, add bounds:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan --from-file ".\urls.txt" --rights "owned or authorized" --name "client-or-project-name" --max-height 360 --max-filesize 75M
```

## 4. Run And Verify

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --dry-run
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --yes
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 verify "batches\...\manifest.json"
```

Reruns are expected to be idempotent. Completed video IDs are stored in `archive.txt`; rerunning the same manifest should skip completed IDs instead of duplicating files.

## 5. Stop Conditions

Stop and review when any of these occur:

- source-side throttle, captcha, login challenge, block, or HTTP 429
- `verify` fails
- production doctor fails
- Mullvad recovery fails
- media probe fails
- rights basis is unclear

Do not rotate relays to continue through source-side blocks. Relay/location controls are manual operator controls for connectivity posture, not a bypass mechanism.

## 6. Safe VPN Test

Use only the guarded command:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad disconnect-test --emergency-unlock
```

It verifies fail-closed Lockdown behavior and reconnects before returning. Raw `mullvad disconnect` refuses by default when Lockdown is on.
