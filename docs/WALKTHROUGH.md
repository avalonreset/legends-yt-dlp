# First-Run Walkthrough

This walkthrough takes a Windows operator from a fresh checkout to a verified first batch. It is designed for Codex-assisted operation, but the commands also work directly in PowerShell.

## 1. Start With Onboarding

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 onboard
```

`onboard` inspects the local machine and prints:

- dependency readiness
- missing setup steps
- the next safe commands
- the user interview checklist
- the normal first batch flow

For automation or CI-style checks:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 onboard --json
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 onboard --strict
```

## 2. Install External Tools

Install Mullvad VPN from Mullvad:

```text
https://mullvad.net/en/download/vpn/windows
```

Then let Slayer install the official upstream `yt-dlp.exe` locally:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 yt-dlp install
```

The installer downloads `yt-dlp.exe` from the official upstream GitHub release and verifies it against upstream `SHA2-256SUMS`.

## 3. Configure The Local Account File

Create `.env` from `.env.example`:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set:

```text
MULLVAD_ACCOUNT_NUMBER=<your account number>
```

Never commit `.env`.

## 4. Set Production Posture

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad login
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 setup production
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor --production
```

Production posture requires Mullvad connected, Lockdown on, split tunneling off, LAN sharing blocked, auto-connect on, anonymous `yt-dlp`, and no browser cookies or account auth.

## 5. Validate With A Smoke Run

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 smoke plan --count 1 --name first-smoke
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --dry-run
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --yes
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 verify "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 ledger "batches\...\manifest.json" --refresh
```

Use the manifest path printed by `smoke plan`.

## 6. Interview The User Before A Real Batch

Ask:

1. What exact channel, playlist, or video URLs should be archived?
2. Do you own the content, have permission, or have a license/public-domain basis?
3. Do you have a rights evidence file to attach with `--rights-file`?
4. Should this start bounded with `--max-items`, `--max-height`, `--max-filesize`, or `--max-downloads`?
5. Where should outputs go, if not the batch downloads folder?
6. Do you want inventory-only review before any media download?

Use [examples/batch-intake.md](../examples/batch-intake.md) and [examples/rights-evidence-template.md](../examples/rights-evidence-template.md) to keep this clean. Copy the rights template to a local evidence file and fill it in before attaching it:

```powershell
Copy-Item .\examples\rights-evidence-template.md .\rights-evidence.md
```

## 7. Inventory Before Downloading

For a channel or playlist:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 inventory "<channel-or-playlist-url>" --rights "<owned or authorized reason>" --rights-file ".\rights-evidence.md" --name "<batch-name>" --max-items 25 --max-height 360 --max-filesize 75M
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 ledger "batches\...\manifest.json"
```

For a hand-curated URL file:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan --from-file ".\examples\urls.txt" --rights "<owned or authorized reason>" --rights-file ".\rights-evidence.md" --name "<batch-name>" --max-height 360 --max-filesize 75M
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 ledger "batches\...\manifest.json"
```

Review `items.jsonl` with the user before any real run.

## 8. Run The Batch

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --dry-run
```

Only after the user approves:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --yes
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 verify "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 ledger "batches\...\manifest.json" --refresh
```

## Stop Conditions

Stop and report when the source presents throttles, captchas, login challenges, account controls, HTTP 429 blocks, DRM, paywalls, or access-control signals.

Do not rotate relays or accounts to continue through source-side controls.
