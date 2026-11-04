# Legends YT-DLP CLI Command Reference

Run all commands from the project root.

## Doctor

```powershell
legends-yt-dlp onboard
legends-yt-dlp onboard --json
legends-yt-dlp onboard --strict
legends-yt-dlp doctor
legends-yt-dlp doctor --require-connected
legends-yt-dlp doctor --production
legends-yt-dlp setup production
```

Use `onboard` first in a fresh checkout. It prints readiness, missing setup steps, user interview prompts, and the next safe commands without mutating local state.

Use `doctor` before real work. For VPN-guarded runs, use `doctor --production` (connected Mullvad, Lockdown on, split tunneling off, LAN sharing blocked, auto-connect on) and pass `--with-vpn` to `plan`, `preflight`, and `run`.

## Mullvad

```powershell
legends-yt-dlp mullvad inspect
legends-yt-dlp mullvad status --verbose
legends-yt-dlp mullvad login
legends-yt-dlp mullvad lockdown on
legends-yt-dlp mullvad connect
legends-yt-dlp mullvad reconnect
legends-yt-dlp mullvad recover
legends-yt-dlp mullvad disconnect-test --emergency-unlock
```

Useful settings:

```powershell
legends-yt-dlp mullvad auto-connect set on
legends-yt-dlp mullvad lan set block
legends-yt-dlp mullvad split-tunnel set off
legends-yt-dlp mullvad tunnel quantum-resistant on
legends-yt-dlp mullvad tunnel ipv6 off
legends-yt-dlp mullvad relay get
legends-yt-dlp mullvad dns get
```

Manual relay selection is available:

```powershell
legends-yt-dlp mullvad relay location us
```

Do not use relay selection as an automatic response to source-side blocks.

`mullvad disconnect` refuses by default when Lockdown is on. Use `disconnect-test` for controlled fail-closed testing because it reconnects before returning. Use `disconnect --force` only for explicit manual maintenance.

## yt-dlp

```powershell
legends-yt-dlp yt-dlp install
legends-yt-dlp yt-dlp update
legends-yt-dlp yt-dlp version
legends-yt-dlp yt-dlp check
```

`install` and `update` both fetch the current official upstream Windows executable and verify it against `SHA2-256SUMS`. `check` compares against upstream stable without downloading (exit 1 means update available). Doctor and preflight fail managed `yt-dlp` builds older than 90 days.

## Catalog and Batches

```powershell
legends-yt-dlp catalog
legends-yt-dlp plan "<URL>" --name "<name>"
legends-yt-dlp plan "<URL1>" "<URL2>" --name "<name>"
legends-yt-dlp plan --from-file "<urls.txt>" --name "<name>"
legends-yt-dlp plan --from-file "<urls.txt>" --name "<name>" --folder-policy batch
legends-yt-dlp inventory "<channel-or-playlist-url>" --rights-file ".\rights-evidence.md" --name "<name>" --max-items 25
legends-yt-dlp ledger "<manifest.json>"
legends-yt-dlp smoke plan --url "<authorized-video-url>" --name "first-smoke"
legends-yt-dlp preflight "<manifest.json>"
legends-yt-dlp run "<manifest.json>" --dry-run
legends-yt-dlp run "<manifest.json>" --yes
legends-yt-dlp run "<manifest.json>" --yes --vpn-recovery-attempts 3
legends-yt-dlp verify "<manifest.json>"
legends-yt-dlp ledger "<manifest.json>" --refresh
```

`run --yes` prints a legal-use notice before invoking `yt-dlp`. It defaults to safe VPN recovery and can reconnect Mullvad and retry after transient tunnel/network failures. It must not continue through source-side block signals.

Folder policy: `auto` puts direct multi-link plans into one named batch folder and keeps inventoried channel/playlist work grouped by uploader. Use `batch` for one folder per request, `by-uploader` for source/channel organization, and `flat` only when the selected output folder already represents the job.

## Intelligence

```powershell
legends-yt-dlp intelligence init "<manifest.json>"
legends-yt-dlp intelligence doctor "<manifest.json>"
legends-yt-dlp intelligence doctor "<manifest.json>" --require-gpu
legends-yt-dlp intelligence transcribe "<manifest.json>" --all --model auto
legends-yt-dlp intelligence transcribe "<manifest.json>" --all --model auto --gpu-backend cuda --require-gpu
legends-yt-dlp intelligence align nfa "<manifest.json>" --media "<video.mp4>" --video-id "<video-id>" --prepare-only
legends-yt-dlp intelligence search "<manifest.json>" "agentic workflow"
legends-yt-dlp intelligence clips plan "<manifest.json>" --query "agentic workflow"
legends-yt-dlp intelligence clips render "<clip-plan.json>" --yes
legends-yt-dlp intelligence vault build "<manifest.json>"
```

`intelligence doctor --require-gpu` is the local ASR truth gate. CPU-only CrispASR remains local and token-free, but do not call a setup GPU-ready unless diagnostics report a GPU backend.

`intelligence align nfa` is the optional NeMo Forced Aligner refinement path for delicate clip boundaries. It expects an external NeMo environment and imports word CTM output only when it matches the current word ledger sequence.

Transcription is optional. Do not run it for every download by default; run it when the user asks for transcripts, search, clips, vault output, or when the operator has a clear analysis reason.
