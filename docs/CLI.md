# CLI Commands

Use the PowerShell launcher from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 <command>
```

## Doctor

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor --require-connected
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor --production
```

Checks Mullvad, `yt-dlp`, `ffmpeg`, local account configuration, and connected state.

`doctor --production` additionally requires a JavaScript runtime for YouTube extraction, Mullvad Lockdown on, split tunneling off, LAN sharing blocked, and auto-connect on.

## Onboarding

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 onboard
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 onboard --json
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 onboard --strict
```

`onboard` prints first-run readiness, missing setup steps, the operator interview checklist, and the next safe workflow. It does not mutate local state or start downloads.

Use `--strict` when an automation should fail until production readiness passes. Use `--basic` to skip production posture checks and inspect only basic dependencies.

## Setup

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 setup production
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 setup production --relay-location us
```

`setup production` applies the expected Mullvad posture, connects or recovers the VPN, and runs production doctor.

## Mullvad

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad status --verbose
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad login
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad lockdown on
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad connect
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad recover
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad disconnect-test --emergency-unlock
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad inspect
```

`mullvad login` reads `MULLVAD_ACCOUNT_NUMBER` from `.env` and redacts it in output.

`mullvad disconnect` refuses by default when Lockdown is on, because that can strand the operator without internet access. Use `mullvad disconnect-test` for fail-closed testing; it constrains the relay to `us` by default, disconnects, verifies Lockdown behavior, and reconnects before returning. `--emergency-unlock` disables Lockdown only if recovery fails.

The CLI exposes first-class wrappers for the useful Mullvad command surface:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad account get
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad account devices
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad version
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad auto-connect get
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad auto-connect set on
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad lan get
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad lan set block
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad relay get
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad relay update
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad relay location us
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad dns get
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad dns default --block-ads --block-trackers --block-malware
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad tunnel get
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad tunnel quantum-resistant on
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad tunnel ipv6 off
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad split-tunnel get
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad split-tunnel set off
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad anti-censorship get
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad api-access get
```

Raw passthrough remains available for installed Mullvad CLI features that do not yet have a named wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad raw --timeout 120 relay list
```

## yt-dlp

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 yt-dlp install
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 yt-dlp version
```

The install command downloads the official Windows standalone executable and verifies it against upstream checksums.

## Packaging

```powershell
powershell -ExecutionPolicy Bypass -File scripts\package-alpha.ps1 -Version "0.1.0-alpha"
```

Creates a local alpha zip and `.sha256` file under `dist/`. The package contains source, docs, scripts, tests, skill files, and legal/community files. It excludes local secrets, managed binaries, batches, reports, downloads, cookies, caches, and git metadata.

## Batch Planning

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan "https://www.youtube.com/@CHANNEL" --rights "owned or authorized" --name "channel-name"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan "https://example.com/a" "https://example.com/b" --rights "owned or authorized" --name "multi-url"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan --from-file ".\urls.txt" --rights "owned or authorized" --name "url-file"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan --from-file ".\urls.txt" --rights "owned or authorized" --rights-file ".\rights-evidence.md" --name "url-file"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan --from-file ".\urls.txt" --rights "owned or authorized" --name "url-file" --folder-policy batch
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan "https://www.youtube.com/watch?v=..." --rights "owned or authorized" --name "smoke" --max-downloads 1 --max-height 360 --max-filesize 50M
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 catalog
```

The plan command creates:

- `manifest.json`
- `urls.txt`
- `yt-dlp.conf`
- download archive path
- output and temp folders
- optional limits for smoke jobs and bounded runs
- optional copied rights evidence under the batch `rights` folder

Generated batch folders are ignored by git.

Folder policy controls the human-facing output layout:

- `auto`: direct multi-link plans use one named batch folder; inventoried channel/playlist work uses uploader folders.
- `batch`: put all media for the batch into one named folder under `--output`.
- `by-uploader`: group media under uploader/channel folders.
- `flat`: put files directly in the selected output folder.

Use `batch` for mixed ad hoc links when the user wants one working folder. Use `by-uploader` when the source scope naturally splits by channel, creator, or project.

## Inventory

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 inventory "https://www.youtube.com/@CHANNEL" --rights "owned or authorized" --rights-file ".\rights-evidence.md" --name "channel-name"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 inventory "https://www.youtube.com/playlist?list=..." --rights "owned or authorized" --name "playlist-name" --max-items 50
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 inventory "https://www.youtube.com/@CHANNEL" --rights "owned or authorized" --name "channel-name" --folder-policy by-uploader
```

`inventory` expands a channel, playlist, or source URL into a batch without downloading media. It runs production doctor first unless `--no-production` is used for diagnostics. It creates `manifest.json`, `urls.txt`, `yt-dlp.conf`, and `items.jsonl`.

Use `--rights-file` to copy permission notes, license evidence, client approval, or other rights proof into the batch `rights` folder. Stop if the user cannot provide a clear rights basis or evidence when the job requires one.

Useful inventory limits:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 inventory "<channel-or-playlist>" --rights "owned or authorized" --name "review" --max-items 25 --live-status not_live
```

Review `items.jsonl` before any real run. If inventory produces source-side throttling, captcha, login, account-control, or block signals, stop and report instead of changing relays to continue.

## Ledger

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 ledger "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 ledger "batches\...\manifest.json" --refresh
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 ledger "batches\...\manifest.json" --status downloaded --limit 50
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 ledger "batches\...\manifest.json" --json
```

`ledger` summarizes and samples the batch item ledger. `--refresh` reconciles ledger status from the download archive, info JSON sidecars, and media files. Use it after dry-runs, real runs, and verification so the operator can review planned, inventoried, archived, downloaded, metadata-only, warning, or blocked items.

## Intelligence

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence init "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence doctor "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence doctor "batches\...\manifest.json" --require-gpu
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence status "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence transcribe "batches\...\manifest.json" --media ".\video.mp4" --video-id "abc123" --model auto
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence transcribe "batches\...\manifest.json" --all --model auto --gpu-backend cuda --require-gpu
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence transcribe "batches\...\manifest.json" --all --model auto --limit 5
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence import-crispasr "batches\...\manifest.json" --input ".\transcript.json" --video-id "abc123" --media-path ".\video.mp4"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence ingest-words "batches\...\manifest.json" --input ".\words.jsonl" --video-id "abc123"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence search "batches\...\manifest.json" "agentic workflow"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence clips plan "batches\...\manifest.json" --query "agentic workflow"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence clips render "batches\...\intelligence\clips\agentic-workflow\clip-plan.json" --yes
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence vault build "batches\...\manifest.json"
```

`intelligence` analyzes already-downloaded, verified local media. It does not download media, call `yt-dlp`, operate Mullvad, rotate relays, or continue through source-side blocks.

The default ready-made ASR path is CrispASR with Parakeet TDT v3. The generic import path still accepts timestamped word ledgers from JSONL or JSON. Exact search operates over normalized contiguous word tokens, so `agentic` matches `Agentic`, but `agent` does not match `agentic`.

`intelligence doctor --require-gpu` is the release gate for GPU-backed Parakeet. CPU-only CrispASR still runs locally without Codex or Claude token spend, but the suite should not call it GPU-ready unless CrispASR diagnostics report a CUDA, Vulkan, Metal, or similar backend.

`intelligence transcribe` rejects contradictory GPU flags before work starts; `--require-gpu` cannot be combined with `--no-gpu` or `--gpu-backend cpu`.

Clip planning writes reviewable JSON before media rendering. Rendering requires an explicit `--yes` and local `ffmpeg`.

See [Post-Capture Intelligence](INTELLIGENCE.md) and [CrispASR Parakeet Backend](CRISPASR.md).

## Smoke Pack

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 smoke plan --url "https://www.youtube.com/watch?v=..." --name "first-smoke"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 smoke plan --count 1
```

Creates a bounded validation batch with conservative defaults. Prefer `--url` with an operator-verified source for new manual validation. The count-based built-in smoke URLs remain only as legacy compatibility fixtures.

## Preflight

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "batches\...\manifest.json"
```

Default preflight requires production posture and anonymous `yt-dlp` auth policy: Mullvad connected, a JavaScript runtime available, Lockdown on, split tunneling off, LAN sharing blocked, auto-connect on, no browser cookies, no cookie files, no account auth, and ignored user-level `yt-dlp` config.

For local harness testing only:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "batches\...\manifest.json" --no-require-connected
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "batches\...\manifest.json" --no-production
```

## Run

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --dry-run
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --dry-run --show-output
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --yes
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --yes --vpn-recovery-attempts 3
```

Real downloads require passing production preflight and an explicit `--yes`. The runner refuses real downloads with `--no-production` or `--no-require-connected`.

Dry-runs suppress raw `yt-dlp` JSON by default and still write a compact run report. Use `--show-output` only when debugging extractor output.

`run` defaults to safe VPN recovery for Mullvad/tunnel/network failures. Use `--no-recover-vpn` for diagnostics.

Do not use relay/location commands as an automatic response to source-side throttling or block signals.

## Verify

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 verify "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 verify "batches\...\manifest.json" --no-probe
```

`verify` checks archive entries, run reports, ledger-scoped media files, ledger-scoped info JSON sidecars, total batch media bytes, and ffprobe media readability. When a batch writes into a broad folder such as `Downloads`, verifier counts come from the item ledger instead of unrelated media already in that folder.
