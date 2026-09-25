# CLI Commands

Use the PowerShell launcher from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 <command>
```

## Doctor

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 doctor
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 doctor --require-connected
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 doctor --production
```

Checks Mullvad, `yt-dlp`, `ffmpeg`, local account configuration, and connected state.

`doctor --production` additionally requires a JavaScript runtime for YouTube extraction, Mullvad Lockdown on, split tunneling off, LAN sharing blocked, and auto-connect on.

## Onboarding

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 onboard
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 onboard --json
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 onboard --strict
```

`onboard` prints first-run readiness, missing setup steps, the operator interview checklist, and the next safe workflow. It does not mutate local state or start downloads.

Use `--strict` when an automation should fail until readiness passes. `onboard` inspects basic dependencies by default; add `--with-vpn` to include Mullvad production posture checks.

## Setup

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 setup production
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 setup production --relay-location us
```

`setup production` applies the expected Mullvad posture, connects or recovers the VPN, and runs VPN production doctor. Only needed for `--with-vpn` runs.

## Mullvad

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad status --verbose
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad login
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad lockdown on
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad connect
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad recover
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad shutdown
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad disconnect-test --emergency-unlock
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad inspect
```

`mullvad login` reads `MULLVAD_ACCOUNT_NUMBER` from `.env` and redacts it in output.

`mullvad shutdown` is the normal end-of-work command. It turns Lockdown mode off, disconnects Mullvad with `--wait`, and verifies that Mullvad is no longer connected.

`mullvad disconnect` refuses by default when Lockdown is on, because that can strand the operator without internet access. Use `mullvad disconnect-test` for fail-closed testing; it constrains the relay to `us` by default, disconnects, verifies Lockdown behavior, and reconnects before returning. `--emergency-unlock` disables Lockdown only if recovery fails.

The CLI exposes first-class wrappers for the useful Mullvad command surface:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad account get
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad account devices
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad version
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad auto-connect get
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad auto-connect set on
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad lan get
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad lan set block
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad relay get
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad relay update
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad relay location us
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad dns get
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad dns default --block-ads --block-trackers --block-malware
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad tunnel get
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad tunnel quantum-resistant on
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad tunnel ipv6 off
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad split-tunnel get
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad split-tunnel set off
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad anti-censorship get
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad api-access get
```

Raw passthrough remains available for installed Mullvad CLI features that do not yet have a named wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad raw --timeout 120 relay list
```

## yt-dlp

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 yt-dlp install
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 yt-dlp update
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 yt-dlp version
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 yt-dlp check
```

The install and update commands download the official Windows standalone executable and verify it against upstream checksums. `check` compares the managed binary against upstream stable without downloading anything: exit 0 when current, exit 1 when an update is available. Readiness checks fail managed `yt-dlp` builds older than 90 days so extractor breakage is caught before a real batch.

## Packaging

```powershell
powershell -ExecutionPolicy Bypass -File scripts\package-alpha.ps1 -Version "0.1.0"
```

Creates a local alpha zip and `.sha256` file under `dist/`. The package contains source, docs, scripts, tests, the router skill file, and legal/community files. It excludes local secrets, managed binaries, batches, reports, downloads, cookies, caches, and git metadata.

## Batch Planning

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 plan "https://www.youtube.com/@CHANNEL" --name "channel-name"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 plan "https://example.com/a" "https://example.com/b" --name "multi-url"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 plan --from-file ".\urls.txt" --name "url-file"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 plan --from-file ".\urls.txt" --rights "optional permission/license/fair-use note" --rights-file ".\rights-evidence.md" --name "url-file"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 plan --from-file ".\urls.txt" --name "url-file" --folder-policy batch
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 plan "https://www.youtube.com/watch?v=..." --name "smoke" --max-downloads 1 --max-height 360 --max-filesize 50M
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 catalog
```

The plan command creates:

- `manifest.json`
- `urls.txt`
- `yt-dlp.conf`
- download archive path
- output and temp folders
- optional limits for smoke jobs and bounded runs
- optional rights note and copied rights evidence under the batch `rights` folder

Generated batch folders are ignored by git.

Folder policy controls the human-facing output layout:

- `auto`: direct multi-link plans use one named batch folder; inventoried channel/playlist work uses uploader folders.
- `batch`: put all media for the batch into one named folder under `--output`.
- `by-uploader`: group media under uploader/channel folders.
- `flat`: put files directly in the selected output folder.

Use `batch` for mixed ad hoc links when the user wants one working folder. Use `by-uploader` when the source scope naturally splits by channel, creator, or project.

## Inventory

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 inventory "https://www.youtube.com/@CHANNEL" --rights-file ".\rights-evidence.md" --name "channel-name"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 inventory "https://www.youtube.com/playlist?list=..." --name "playlist-name" --max-items 50
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 inventory "https://www.youtube.com/@CHANNEL" --name "channel-name" --folder-policy by-uploader
```

`inventory` expands a channel, playlist, or source URL into a batch without downloading media. It runs VPN production doctor first only with `--with-vpn`. It creates `manifest.json`, `urls.txt`, `yt-dlp.conf`, and `items.jsonl`.

Use optional `--rights` and `--rights-file` values to keep permission notes, license evidence, client approval, fair-use notes, or other context with the batch when useful. These fields are metadata, not a pre-download gate.

Useful inventory limits:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 inventory "<channel-or-playlist>" --name "review" --max-items 25 --live-status not_live
```

Review `items.jsonl` before any real run. If inventory produces source-side throttling, captcha, login, account-control, or block signals, stop and report instead of changing relays to continue.

## Ledger

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 ledger "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 ledger "batches\...\manifest.json" --refresh
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 ledger "batches\...\manifest.json" --status downloaded --limit 50
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 ledger "batches\...\manifest.json" --json
```

`ledger` summarizes and samples the batch item ledger. `--refresh` reconciles ledger status from the download archive, info JSON sidecars, and media files. Use it after dry-runs, real runs, and verification so the operator can review planned, inventoried, archived, downloaded, metadata-only, warning, or blocked items.

## Intelligence

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence init "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence doctor "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence doctor "batches\...\manifest.json" --require-gpu
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence status "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence transcribe "batches\...\manifest.json" --media ".\video.mp4" --video-id "abc123" --model auto
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence transcribe "batches\...\manifest.json" --all --model auto --gpu-backend cuda --require-gpu
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence transcribe "batches\...\manifest.json" --all --model auto --limit 5
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence import-crispasr "batches\...\manifest.json" --input ".\transcript.json" --video-id "abc123" --media-path ".\video.mp4"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence ingest-words "batches\...\manifest.json" --input ".\words.jsonl" --video-id "abc123"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence align nfa "batches\...\manifest.json" --media ".\video.mp4" --video-id "abc123" --prepare-only
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence align nfa "batches\...\manifest.json" --media ".\video.mp4" --video-id "abc123" --python "C:\path\to\nemo-env\python.exe" --nemo-dir "C:\path\to\NeMo"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence align nfa "batches\...\manifest.json" --import-ctm ".\output\ctm\words\abc123.ctm" --video-id "abc123"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence search "batches\...\manifest.json" "agentic workflow"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence clips plan "batches\...\manifest.json" --query "agentic workflow"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence clips render "batches\...\intelligence\clips\agentic-workflow\clip-plan.json" --yes
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence vault build "batches\...\manifest.json"
```

`intelligence` analyzes already-downloaded, verified local media. It does not download media, call `yt-dlp`, operate Mullvad, rotate relays, or continue through source-side blocks.

Do not treat transcription as mandatory for every rip. Use `intelligence` when the user asks for transcripts, exact search, clip extraction, transcript vaults, or when the operator explicitly decides the batch needs post-capture analysis. Otherwise stop after run, verify, and ledger review.

The default ready-made ASR path is CrispASR with Parakeet TDT v3. The generic import path still accepts timestamped word ledgers from JSONL or JSON. Exact search operates over normalized contiguous word tokens, so `agentic` matches `Agentic`, but `agent` does not match `agentic`.

`intelligence doctor --require-gpu` is the release gate for GPU-backed Parakeet. CPU-only CrispASR still runs locally without Codex or Claude token spend, but the suite should not call it GPU-ready unless CrispASR diagnostics report a CUDA, Vulkan, Metal, or similar backend.

`intelligence transcribe` rejects contradictory GPU flags before work starts; `--require-gpu` cannot be combined with `--no-gpu` or `--gpu-backend cpu`.

`intelligence align nfa` is the optional NVIDIA NeMo Forced Aligner refinement path. It writes NFA manifests under `intelligence\alignments\nfa\`, expects an external NeMo/PyTorch environment, and imports NFA word CTM output back into the existing word ledger only when the CTM word sequence matches the current transcript.

Clip planning writes reviewable JSON before media rendering. Rendering requires an explicit `--yes` and local `ffmpeg`.

See [Post-Capture Intelligence](INTELLIGENCE.md) and [CrispASR Parakeet Backend](CRISPASR.md).

## Smoke Pack

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 smoke plan --url "https://www.youtube.com/watch?v=..." --name "first-smoke"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 smoke plan --count 1
```

Creates a bounded validation batch with conservative defaults. Prefer `--url` with an operator-verified source for new manual validation. The count-based built-in smoke URLs remain only as legacy compatibility fixtures.

## Preflight

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 preflight "batches\...\manifest.json"
```

Default preflight checks the manifest, paths, anonymous `yt-dlp` auth policy (no browser cookies, no cookie files, no account auth, ignored user-level config), and tool readiness. With `--with-vpn` it additionally requires Mullvad connected, Lockdown on, split tunneling off, LAN sharing blocked, and auto-connect on.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 preflight "batches\...\manifest.json" --with-vpn
```

## Run

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 run "batches\...\manifest.json" --dry-run
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 run "batches\...\manifest.json" --dry-run --show-output
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 run "batches\...\manifest.json" --yes
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 run "batches\...\manifest.json" --yes --with-vpn
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 run "batches\...\manifest.json" --yes --bulk
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 run "batches\...\manifest.json" --yes --with-vpn --keep-vpn
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 run "batches\...\manifest.json" --yes --vpn-recovery-attempts 3
```

Real downloads require passing preflight and an explicit `--yes`. Before invoking `yt-dlp`, the runner prints a legal-use notice reminding operators to download only when they have rights, permission, a license, fair use, or another lawful basis. Batches over 50 URLs additionally require `--bulk`; batches of 11-50 print a pacing notice.

In `--with-vpn` mode, after a real run reaches a terminal state, `run` shuts Mullvad down: Lockdown mode off, VPN disconnected with `--wait`, and final state verified. Use `--keep-vpn` only when the operator intentionally wants Mullvad and Lockdown left running after the batch.

Dry-runs suppress raw `yt-dlp` JSON by default and still write a compact run report. Use `--show-output` only when debugging extractor output.

`run --with-vpn` defaults to safe VPN recovery for Mullvad/tunnel/network failures. Use `--no-recover-vpn` for diagnostics.

Do not use relay/location commands as an automatic response to source-side throttling or block signals.

## Verify

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 verify "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 verify "batches\...\manifest.json" --no-probe
```

`verify` checks archive entries, run reports, ledger-scoped media files, ledger-scoped info JSON sidecars, total batch media bytes, and ffprobe media readability. When a batch writes into a broad folder such as `Downloads`, verifier counts come from the item ledger instead of unrelated media already in that folder.
