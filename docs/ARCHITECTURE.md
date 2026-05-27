# Architecture

Legends YT-DLP Slayer is a wrapper and operator control plane. It does not reimplement video extraction.

## Components

```text
CLI Control Plane
  - parses commands
  - prints pass/fail checks
  - refuses unsafe real runs

Policy Checks
  - require source URL
  - require rights basis
  - reject unsafe run states

Mullvad Guard
  - locates the official Mullvad CLI
  - checks status
  - supports login/connect/lockdown wrappers
  - blocks preflight when disconnected

yt-dlp Manager
  - downloads official Windows yt-dlp.exe
  - verifies SHA256 against upstream checksum files
  - reports version

Batch Orchestrator
  - writes manifest.json
  - writes urls.txt
  - writes yt-dlp.conf
  - uses download archive files for resumability

Codex Skill Suite
  - guides Codex through setup, planning, preflight, dry-run, and guarded real runs
  - keeps safety/error policy in context
  - routes to detailed references only when needed
```

## Current Implementation

The CLI is a Python package under `src/slayer_cli`.

The PowerShell launcher sets `PYTHONPATH=src` and runs:

```powershell
python -m slayer_cli
```

This keeps early development lightweight. Packaging can come later after the command surface stabilizes.

## Dependency Strategy

Use the official standalone `yt-dlp.exe` as a managed child-process dependency for Windows. This keeps the app independent from the user's Python environment and matches upstream's recommended Windows binary path.

Use the official Mullvad CLI installed by the Windows app. Do not reverse engineer the GUI.

## State Strategy

MVP state is file-based:

- ignored `batches/` folders for manifests and runtime files
- ignored `.local/` for managed local binaries
- ignored `.env` for the Mullvad account number

SQLite can come later if multi-batch dashboards or richer query support justify it.

## Skill Packaging

The Codex-first package lives under `skills/legends-yt-dlp-slayer/`.

The skill does not replace the CLI. It tells Codex how to operate the CLI safely, when to load reference material, and when to stop instead of continuing.
