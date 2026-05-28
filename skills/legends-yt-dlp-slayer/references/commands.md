# Slayer CLI Command Reference

Run all commands from the project root.

## Doctor

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 onboard
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 onboard --json
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 onboard --strict
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor --require-connected
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor --production
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 setup production
```

Use `onboard` first in a fresh checkout. It prints readiness, missing setup steps, user interview prompts, and the next safe commands without mutating local state.

Use `doctor --production` before real work. It requires connected Mullvad, Lockdown on, split tunneling off, LAN sharing blocked, and auto-connect on.

## Mullvad

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad inspect
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad status --verbose
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad login
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad lockdown on
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad connect
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad reconnect
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad recover
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad disconnect-test --emergency-unlock
```

Useful settings:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad auto-connect set on
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad lan set block
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad split-tunnel set off
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad tunnel quantum-resistant on
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad tunnel ipv6 off
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad relay get
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad dns get
```

Manual relay selection is available:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad relay location us
```

Do not use relay selection as an automatic response to source-side blocks.

`mullvad disconnect` refuses by default when Lockdown is on. Use `disconnect-test` for controlled fail-closed testing because it reconnects before returning. Use `disconnect --force` only for explicit manual maintenance.

## yt-dlp

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 yt-dlp install
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 yt-dlp version
```

## Catalog and Batches

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 catalog
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan "<URL>" --rights "<basis>" --name "<name>"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan "<URL1>" "<URL2>" --rights "<basis>" --name "<name>"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan --from-file "<urls.txt>" --rights "<basis>" --name "<name>"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan --from-file "<urls.txt>" --rights "<basis>" --name "<name>" --folder-policy batch
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 inventory "<channel-or-playlist-url>" --rights "<basis>" --rights-file ".\rights-evidence.md" --name "<name>" --max-items 25
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 ledger "<manifest.json>"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 smoke plan --url "<authorized-video-url>" --name "first-smoke"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "<manifest.json>"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "<manifest.json>" --dry-run
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "<manifest.json>" --yes
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "<manifest.json>" --yes --vpn-recovery-attempts 3
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 verify "<manifest.json>"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 ledger "<manifest.json>" --refresh
```

`run` defaults to safe VPN recovery. It can reconnect Mullvad and retry after transient tunnel/network failures. It must not continue through source-side block signals.

Folder policy: `auto` puts direct multi-link plans into one named batch folder and keeps inventoried channel/playlist work grouped by uploader. Use `batch` for one folder per request, `by-uploader` for source/channel organization, and `flat` only when the selected output folder already represents the job.

## Intelligence

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence init "<manifest.json>"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence doctor "<manifest.json>"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence doctor "<manifest.json>" --require-gpu
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence transcribe "<manifest.json>" --all --model auto
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence transcribe "<manifest.json>" --all --model auto --gpu-backend cuda --require-gpu
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence search "<manifest.json>" "agentic workflow"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence clips plan "<manifest.json>" --query "agentic workflow"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence clips render "<clip-plan.json>" --yes
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence vault build "<manifest.json>"
```

`intelligence doctor --require-gpu` is the local ASR truth gate. CPU-only CrispASR remains local and token-free, but do not call a setup GPU-ready unless diagnostics report a GPU backend.
