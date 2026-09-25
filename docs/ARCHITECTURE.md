# Architecture

Legends YT-DLP is a wrapper and operator control plane. It does not reimplement video extraction.

## Components

```text
CLI Control Plane
  - parses commands
  - prints pass/fail checks
  - guides first-run onboarding
  - refuses unsafe real runs

Policy Checks
  - require source URL
  - print legal-use notice before real downloads
  - reject unsafe run states

Mullvad Guard
  - locates the official Mullvad CLI
  - checks status
  - supports login/connect/lockdown wrappers
  - blocks preflight when disconnected
  - can apply the full production posture with setup production
  - shuts down Lockdown and disconnects Mullvad after terminal real runs by default

yt-dlp Manager
  - downloads official Windows yt-dlp.exe
  - verifies SHA256 against upstream checksum files
  - reports version

Batch Orchestrator
  - writes manifest.json
  - writes urls.txt
  - writes items.jsonl
  - writes yt-dlp.conf
  - copies optional rights evidence
  - uses download archive files for resumability

Smoke Pack
  - creates bounded validation batches from operator-provided smoke URLs
  - gives operators a safe install test before real work

Verifier
  - checks archive entries, reports, media files, and info JSON sidecars
  - validates media files through ffprobe when available

Post-Capture Intelligence
  - analyzes already-downloaded verified local media
  - runs external CrispASR/Parakeet transcription when installed
  - imports timestamped ASR word ledgers
  - exact-searches normalized word tokens
  - writes FFmpeg clip plans and optional rendered montages
  - exports Obsidian-compatible transcript pages

Codex Skill Suite
  - guides Codex through setup, planning, preflight, dry-run, and guarded real runs
  - keeps safety/error policy in context
  - routes to detailed references only when needed
```

## Current Implementation

The CLI is a Python package under `src/legends_ytdlp`.

The PowerShell launcher sets `PYTHONPATH=src` and runs:

```powershell
python -m legends_ytdlp
```

This keeps early development lightweight. Packaging can come later after the command surface stabilizes.

`legends-yt-dlp onboard` is the non-mutating first-run guide. It runs readiness checks,
prints missing setup actions, surfaces the user interview checklist, and points
operators to the normal inventory/ledger/preflight/run/verify workflow.

## Dependency Strategy

Use the official standalone `yt-dlp.exe` as a managed child-process dependency for Windows. This keeps the app independent from the user's Python environment and matches upstream's recommended Windows binary path.

Use the official Mullvad CLI installed by the Windows app. Do not reverse engineer the GUI.

Production capture starts by enabling a fail-closed Mullvad posture and connecting the VPN. Terminal real runs end by disabling Lockdown first, then disconnecting Mullvad with `--wait`, so the operator is not left in Mullvad Lockdown after the batch stops.

## State Strategy

MVP state is file-based:

- ignored `batches/` folders for manifests and runtime files
- ignored `.local/` for managed local binaries
- ignored `.env` for the Mullvad account number
- ignored `reports/` folders for run reports

Each new batch gets a JSON manifest and JSONL item ledger. The ledger starts as
planned or inventoried items, then `run` and `verify` refresh it from the
download archive, info JSON sidecars, and media files.

SQLite can come later if multi-batch dashboards or richer query support justify it.

Post-capture intelligence state is also file-based under each batch:

- `intelligence/manifest.json`
- `intelligence/words/*.words.jsonl`
- `intelligence/searches/*.matches.jsonl`
- `intelligence/alignments/nfa/*/*.manifest.jsonl`
- `intelligence/alignments/nfa/*/output/ctm/words/*.ctm`
- `intelligence/clips/*/clip-plan.json`
- `intelligence/vault/*.md`

The core intelligence contract is the word ledger, not plain transcript text. External ASR backends such as CrispASR + Parakeet or NVIDIA NeMo + Parakeet can produce that ledger without becoming core package dependencies.
The default ready-made producer is CrispASR with the Parakeet backend, discovered via `CRISPASR_CLI`, `.local/bin`, or `PATH`.
NVIDIA NeMo Forced Aligner is an optional refinement path: Legends YT-DLP prepares manifests and imports word CTM output into the same ledger, but the NeMo/PyTorch runtime stays external.

## Skill Packaging

The Codex-first package lives under `skills/legends-yt-dlp/`.

The skill does not replace the CLI. It tells Codex how to operate the CLI safely, when to load reference material, and when to stop instead of continuing.

## Packaging Strategy

Alpha packages are generated from source files with `scripts/package-alpha.ps1`.
Packages intentionally exclude `.env`, `.local`, `batches`, `reports`, media,
cookies, caches, secrets, and git metadata. Operators install `yt-dlp.exe`
locally with `legends-yt-dlp yt-dlp install` after unpacking.

Heavy ASR runtimes and model weights such as CrispASR, Parakeet GGUF files, PyTorch, NeMo, WhisperX, or pyannote are not bundled in the alpha package. They should be installed by the operator as external tools. The normal path is CrispASR as a local CLI; NeMo/WhisperX remain advanced fallback environments.
