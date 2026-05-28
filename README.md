# Legends YT-DLP Slayer

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
- Provides a one-command production setup path for Mullvad safety posture.
- Provides a curated NASA Goddard smoke pack for install validation.
- Supports bounded smoke jobs with max downloads, height, and filesize limits.
- Generates stable anonymous-mode `yt-dlp` config files with download archives and conservative retry/sleep settings.
- Blocks real runs until production preflight passes.
- Requires an explicit `--yes` flag for real downloads.
- Verifies completed batches with archive, report, info JSON, media count, and ffprobe checks.

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
- curated 5-video smoke-pack planning
- batch `plan`
- multi-URL and URL-file batch planning
- batch `catalog`
- batch `preflight`
- guarded `run`
- batch `verify`
- Codex skill suite under `skills/legends-yt-dlp-slayer`

Still needs before a release tag:

- alpha packaging/release notes

## Quick Start

From the project root:

```powershell
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

Validate the install with the curated smoke pack:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 smoke plan --count 5
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --dry-run
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --yes
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 verify "batches\...\manifest.json"
```

Create a batch:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan "https://www.youtube.com/@CHANNEL" --rights "owned or authorized" --name "channel-name"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan --from-file ".\urls.txt" --rights "owned or authorized" --name "catalog-name"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 catalog
```

Preflight and run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --dry-run
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --yes
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 verify "batches\...\manifest.json"
```

## Safety Boundary

Allowed:

- archiving videos you own
- archiving videos you have permission to download
- archiving public-domain or appropriately licensed content
- using Mullvad as a privacy and leak-prevention layer
- stopping on throttling, captcha, login, or block signals

Not allowed:

- bypassing DRM, paywalls, captchas, login challenges, or access controls
- rotating VPN relays to continue through platform blocks
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
- [Standard Operating Procedure](docs/SOP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Safety and Use Policy](docs/SAFETY.md)
- [Changelog](CHANGELOG.md)
- [Codex Skill Suite](skills/legends-yt-dlp-slayer/SKILL.md)

## Local Secrets

`.env` is ignored by git. Use `.env.example` for the expected shape.

Never commit Mullvad account numbers, cookies, account tokens, or batch outputs.

Production batches are anonymous by default: no browser cookies, no cookie files, no username/password auth, no `.netrc`, and no inherited user-level `yt-dlp` config.

## License

License is not finalized. This repository is private while the product and distribution model are being worked out.

Important distribution note: the project does not commit the `yt-dlp.exe` binary. If a future release bundles upstream binaries, review upstream licensing and notices before distribution.
