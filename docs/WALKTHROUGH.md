# First-Run Walkthrough

This walkthrough takes a Windows operator from a fresh checkout to a verified first batch. It is designed for Codex-assisted operation, but the commands also work directly in PowerShell.

## 1. Start With Onboarding

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 onboard
```

`onboard` inspects the local machine and prints:

- dependency readiness
- missing setup steps
- the next safe commands
- the user interview checklist
- the normal first batch flow

For automation or CI-style checks:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 onboard --json
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 onboard --strict
```

## 2. Install External Tools

Let Legends YT-DLP install the official upstream `yt-dlp.exe` locally:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 yt-dlp install
```

The installer downloads `yt-dlp.exe` from the official upstream GitHub release and verifies it against upstream `SHA2-256SUMS`.
For an existing checkout, use `yt-dlp update` to refresh the managed local binary. Doctor and preflight fail managed builds older than 90 days so stale extractors are fixed before a real batch.

## 3. Configure The Local Account File (VPN Runs Only)

Skip this section unless you want VPN-guarded runs. Create `.env` from
`.env.example`:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set:

```text
MULLVAD_ACCOUNT_NUMBER=<your account number>
```

Never commit `.env`.

## 4. Set VPN Posture (Optional)

Mullvad is optional. Skip this section for everyday pulls. For guarded runs,
install Mullvad VPN for Windows (`https://mullvad.net/en/download/vpn/windows`),
set `MULLVAD_ACCOUNT_NUMBER` in `.env`, then:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad login
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 setup production
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 doctor --production
```

VPN posture requires Mullvad connected, Lockdown on, split tunneling off, LAN sharing blocked, and auto-connect on. Anonymous `yt-dlp` (no browser cookies or account auth) applies to every run regardless. Pass `--with-vpn` to `plan`, `preflight`, and `run` to require this posture.

## 5. Validate With A Smoke Run

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 smoke plan --url "<authorized-video-url>" --name first-smoke
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 preflight "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 run "batches\...\manifest.json" --dry-run
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 run "batches\...\manifest.json" --yes
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 verify "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 ledger "batches\...\manifest.json" --refresh
```

Use the manifest path printed by `smoke plan`.

Use a short source the operator has permission to download. The count-based built-in smoke fixtures remain for compatibility, but new manual validation should use `--url`.

## 6. Interview The User Before A Real Batch

Ask:

1. What exact channel, playlist, or video URLs should be archived?
2. Remind the operator to use material only when they have rights, permission, fair use, or another lawful basis.
3. Do you want to attach an optional rights note or evidence file with `--rights`/`--rights-file`?
4. Should this start bounded with `--max-items`, `--max-height`, `--max-filesize`, or `--max-downloads`?
5. Where should outputs go, if not the batch downloads folder?
6. Should output use one batch folder, uploader folders, or a flat folder?
7. Do you want inventory-only review before any media download?

Use [examples/batch-intake.md](../examples/batch-intake.md) and [examples/rights-evidence-template.md](../examples/rights-evidence-template.md) when optional rights context is useful. Copy the rights template to a local evidence file and fill it in before attaching it:

```powershell
Copy-Item .\examples\rights-evidence-template.md .\rights-evidence.md
```

## 7. Inventory Before Downloading

For a channel or playlist:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 inventory "<channel-or-playlist-url>" --rights-file ".\rights-evidence.md" --name "<batch-name>" --max-items 25 --max-height 360 --max-filesize 75M
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 ledger "batches\...\manifest.json"
```

For a hand-curated URL file:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 plan --from-file ".\examples\urls.txt" --rights "optional permission/license/fair-use note" --rights-file ".\rights-evidence.md" --name "<batch-name>" --max-height 360 --max-filesize 75M --folder-policy batch
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 ledger "batches\...\manifest.json"
```

Review `items.jsonl` with the user before any real run.

## 8. Run The Batch

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 preflight "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 run "batches\...\manifest.json" --dry-run
```

Only after the user approves:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 run "batches\...\manifest.json" --yes
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 verify "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 ledger "batches\...\manifest.json" --refresh
```

For a plain archive/download request, stop there. Move into `legends-yt-dlp intelligence` only when the user asked for transcripts, exact search, clips, a transcript vault, or the job clearly needs analysis.

## Stop Conditions

Stop and report when the source presents throttles, captchas, login challenges, account controls, HTTP 429 blocks, DRM, paywalls, or access-control signals.

Do not rotate relays or accounts to continue through source-side controls.
