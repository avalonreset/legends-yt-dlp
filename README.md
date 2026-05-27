# Legends YT-DLP Slayer

Windows-first control plane for lawful, resumable video archiving with `yt-dlp` and a Mullvad VPN preflight gate.

Legends YT-DLP Slayer exists because raw `yt-dlp` is powerful but easy to operate carelessly at scale. The project wraps the official `yt-dlp` binary with explicit batch plans, rights-basis checks, local state, conservative defaults, and a fail-closed Mullvad gate so downloads do not start unless the machine is in the expected VPN posture.

## What It Does

- Detects the official Mullvad CLI installed with the Windows app.
- Stores the Mullvad account number locally in an ignored `.env` file.
- Downloads the official Windows `yt-dlp.exe` release from `yt-dlp/yt-dlp`.
- Verifies the downloaded binary against upstream `SHA2-256SUMS`.
- Detects `ffmpeg`.
- Creates rights-aware batch manifests.
- Generates stable `yt-dlp` config files with download archives and conservative retry/sleep settings.
- Blocks real runs until preflight passes.
- Requires an explicit `--yes` flag for real downloads.

## Why It Exists

Large archive jobs fail in predictable ways: accidental non-VPN traffic, duplicate downloads, broken resumes, messy output paths, unclear rights, and no evidence trail. This project turns those weak points into boring preflight checks and repeatable operator commands.

The goal is not to evade platform controls. The goal is to make legitimate archival work safer, slower, resumable, and auditable.

## Current Status

Early private alpha.

Working now:

- `doctor`
- Mullvad status/login/connect/lockdown wrappers
- Mullvad inspect and settings wrappers
- official `yt-dlp.exe` install and version check
- batch `plan`
- multi-URL and URL-file batch planning
- batch `catalog`
- batch `preflight`
- guarded `run`
- Codex skill suite under `skills/legends-yt-dlp-slayer`

Blocked until the local Mullvad account is funded and connected:

- passing default batch preflight
- real download smoke tests

## Quick Start

From the project root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 yt-dlp version
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad status --verbose
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad inspect
```

After the Mullvad account is active:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad login
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad lockdown on
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad connect
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor --require-connected
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
- [Architecture](docs/ARCHITECTURE.md)
- [Safety and Use Policy](docs/SAFETY.md)
- [Changelog](CHANGELOG.md)
- [Codex Skill Suite](skills/legends-yt-dlp-slayer/SKILL.md)

## Local Secrets

`.env` is ignored by git. Use `.env.example` for the expected shape.

Never commit Mullvad account numbers, cookies, account tokens, or batch outputs.

## License

License is not finalized. This repository is private while the product and distribution model are being worked out.

Important distribution note: the project does not commit the `yt-dlp.exe` binary. If a future release bundles upstream binaries, review upstream licensing and notices before distribution.
