# Legends YT-DLP Slayer

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Windows first](https://img.shields.io/badge/Windows-first-0078D4.svg)
![yt-dlp](https://img.shields.io/badge/powered%20by-yt--dlp-lightgrey.svg)
![Mullvad guarded](https://img.shields.io/badge/Mullvad-guarded-orange.svg)

Windows-first control plane for lawful, resumable video archiving with `yt-dlp` and a Mullvad VPN preflight gate.

Legends YT-DLP Slayer exists because raw `yt-dlp` is powerful but easy to operate carelessly at scale. The project wraps the official `yt-dlp` binary with explicit batch plans, rights-basis checks, local state, conservative defaults, and a fail-closed Mullvad gate so downloads do not start unless the machine is in the expected VPN posture.

## What It Does

- Detects the official Mullvad CLI installed with the Windows app.
- Stores the Mullvad account number locally in an ignored `.env` file.
- Downloads the official Windows `yt-dlp.exe` release from `yt-dlp/yt-dlp`.
- Verifies the downloaded binary against upstream `SHA2-256SUMS`.
- Detects `ffmpeg`.
- Detects a JavaScript runtime for modern YouTube extraction.
- Creates rights-aware batch manifests.
- Inventories channel and playlist URLs into a reviewable item ledger before downloads.
- Copies optional rights evidence files into the batch folder.
- Provides a one-command production setup path for Mullvad safety posture.
- Supports custom operator-provided smoke URLs for install validation.
- Supports bounded smoke jobs with max downloads, height, and filesize limits.
- Generates stable anonymous-mode `yt-dlp` config files with download archives and conservative retry/sleep settings.
- Blocks real runs until production preflight passes.
- Requires an explicit `--yes` flag for real downloads.
- Verifies completed batches with archive, report, info JSON, media count, and ffprobe checks.
- Runs the ready-made CrispASR Parakeet backend against verified local media.
- Imports timestamped word ledgers for verified local media.
- Searches exact words and phrases across local transcripts.
- Generates reviewable FFmpeg clip plans and optional montages.
- Builds Obsidian-compatible transcript vault pages.

## Why It Exists

Large archive jobs fail in predictable ways: accidental non-VPN traffic, duplicate downloads, broken resumes, messy output paths, unclear rights, and no evidence trail. This project turns those weak points into boring preflight checks and repeatable operator commands.

The goal is not to evade platform controls. The goal is to make legitimate archival work safer, slower, resumable, and auditable.

## Current Status

Early private alpha.

Working now:

- `doctor`
- `setup production`
- Mullvad status/login/connect/lockdown wrappers
- Mullvad inspect and settings wrappers
- Mullvad safe recovery for tunnel/network failures
- guarded Mullvad disconnect testing that reconnects before returning
- production posture checks for Mullvad Lockdown, split tunneling, LAN sharing, and auto-connect
- anonymous yt-dlp auth/cookie policy checks
- JavaScript runtime detection/configuration for YouTube extraction
- bounded batch limits for smoke tests and controlled archive jobs
- official `yt-dlp.exe` install and version check
- custom smoke-pack planning
- batch `plan`
- channel/playlist `inventory`
- multi-URL and URL-file batch planning
- batch `catalog`
- item `ledger`
- batch `preflight`
- guarded `run`
- batch `verify`
- post-capture `intelligence` workspace, CrispASR/Parakeet transcription, word import, search, clip planning, rendering, and vault export
- Codex skill suite under `skills/legends-yt-dlp-slayer`

Still needs before a release tag:

- review the generated alpha zip and decide whether to publish a first release tag

## Quick Start

From the project root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 onboard
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 setup production
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 yt-dlp version
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad status --verbose
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad inspect
```

After the Mullvad account is active:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad login
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad lockdown on
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad connect
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad recover
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad disconnect-test --emergency-unlock
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor --require-connected
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor --production
```

Validate the install with a small authorized smoke URL:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 smoke plan --url "https://www.youtube.com/watch?v=..." --name "first-smoke"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --dry-run
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --yes
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 verify "batches\...\manifest.json"
```

Create a batch:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan "https://www.youtube.com/@CHANNEL" --rights "owned or authorized" --name "channel-name"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan --from-file ".\urls.txt" --rights "owned or authorized" --name "catalog-name"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan --from-file ".\urls.txt" --rights "owned or authorized" --rights-file ".\rights-evidence.md" --name "catalog-name"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan --from-file ".\urls.txt" --rights "owned or authorized" --name "catalog-name" --folder-policy batch
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 catalog
```

Folder policy controls output layout. `auto` puts direct multi-link plans into one named batch folder and keeps inventoried channel/playlist work grouped by uploader. Use `--folder-policy batch` for mixed one-off links, `--folder-policy by-uploader` for channel/archive work, and `--folder-policy flat` only when the selected output folder already represents the job.

For channel or playlist work, inventory first:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 inventory "https://www.youtube.com/@CHANNEL" --rights "owned or authorized" --rights-file ".\rights-evidence.md" --name "channel-name"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 ledger "batches\...\manifest.json"
```

Inventory creates the batch manifest, `urls.txt`, `yt-dlp.conf`, and `items.jsonl` without downloading media. Review the ledger with the user before a real run.

Preflight and run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --dry-run
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --yes
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 verify "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 ledger "batches\...\manifest.json" --refresh
```

Analyze verified local media after download when the user asks for transcripts, search, clips, a transcript vault, or when the job clearly calls for post-capture analysis. Plain archive/download jobs do not need transcription by default:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence init "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence doctor "batches\...\manifest.json" --require-gpu
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence transcribe "batches\...\manifest.json" --media ".\video.mp4" --video-id "VIDEO_ID" --model auto
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence transcribe "batches\...\manifest.json" --all --model auto --gpu-backend cuda --require-gpu
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence ingest-words "batches\...\manifest.json" --input ".\examples\intelligence-words.jsonl" --video-id "VIDEO_ID"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence search "batches\...\manifest.json" "agentic workflow"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence clips plan "batches\...\manifest.json" --query "agentic workflow"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence vault build "batches\...\manifest.json"
```

`intelligence doctor --require-gpu` is the truth gate for GPU-backed Parakeet. CPU-only CrispASR still runs locally without Codex or Claude token spend, but the project does not label that install GPU-ready unless CrispASR diagnostics report a compiled GPU backend.

Treat `slayer intelligence` as an optional post-capture layer. The normal archive contract ends after run, verify, and ledger review unless the user requested analysis or the operator has a clear reason to propose it.

## Safety Boundary

Allowed:

- archiving videos you own
- archiving videos you have permission to download
- archiving public-domain or appropriately licensed content
- using Mullvad as a privacy and leak-prevention layer
- stopping on throttling, captcha, login, or block signals

Not allowed:

- bypassing DRM, paywalls, captchas, login challenges, account controls, or access controls
- rotating VPN relays to continue through throttles, captchas, login prompts, account controls, or platform blocks
- automating downloads without a documented rights basis
- hiding abusive or copyright-infringing use

See [docs/SAFETY.md](docs/SAFETY.md).

## Architecture

```text
Operator command
  -> CLI control plane
  -> Policy checks
  -> Mullvad guard
  -> yt-dlp runner
  -> Batch state and reports
```

The project uses `yt-dlp` as an external child-process dependency rather than reimplementing download logic.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Documentation

- [CLI Commands](docs/CLI.md)
- [First-Run Walkthrough](docs/WALKTHROUGH.md)
- [Standard Operating Procedure](docs/SOP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Post-Capture Intelligence](docs/INTELLIGENCE.md)
- [Safety and Use Policy](docs/SAFETY.md)
- [Legal and Attribution Notes](docs/LEGAL.md)
- [Alpha Packaging](docs/PACKAGING.md)
- [Changelog](CHANGELOG.md)
- [Codex Skill Suite](skills/legends-yt-dlp-slayer/SKILL.md)

## Local Secrets

`.env` is ignored by git. Use `.env.example` for the expected shape.

Never commit Mullvad account numbers, cookies, account tokens, or batch outputs.

Production batches are anonymous by default: no browser cookies, no cookie files, no username/password auth, no `.netrc`, and no inherited user-level `yt-dlp` config.

## Packaging

Build a local alpha zip:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\package-alpha.ps1 -Version "0.1.0-alpha"
```

The package excludes `.env`, `.local`, `batches`, `reports`, downloads, caches, cookies, secrets, and git metadata.

## License

Legends YT-DLP Slayer is released under the [MIT License](LICENSE).

Important distribution note: the project does not commit or package the `yt-dlp.exe` binary. It downloads the official upstream executable locally and verifies its checksum. See [NOTICE](NOTICE) and [docs/LEGAL.md](docs/LEGAL.md).
