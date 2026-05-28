---
name: legends-yt-dlp-slayer
description: Use when the user wants Codex to operate Legends YT-DLP Slayer: lawful yt-dlp batch archiving, Mullvad VPN preflight/control, large download catalogs, dry-runs, resumable queue execution, or troubleshooting the Slayer/Printing Press CLI.
---

# Legends YT-DLP Slayer

Operate the local Slayer CLI as the deterministic runtime. The skill is the operator brain; the CLI is the control plane.

## Start Here

1. Confirm the working directory is the project root containing `scripts/slayer.ps1`.
2. Read `wiki/hot.md` if it exists.
3. Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor --require-connected
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor --production
```

If the command fails, fix setup before planning or running downloads.

## Safety Boundary

Allowed: lawful archiving with a documented rights basis, Mullvad privacy checks, conservative pacing, resumable batches, and operator-reviewed retries.

Disallowed: bypassing DRM, paywalls, login challenges, captchas, access controls, account controls, throttling, bans, or IP blocks. Do not automatically rotate Mullvad relays/IPs to keep downloading through source-side blocks.

Production mode is mandatory for real downloads. It requires Mullvad connected, a JavaScript runtime for YouTube extraction, Lockdown mode on, split tunneling off, LAN sharing blocked, auto-connect on, and anonymous `yt-dlp` operation with no browser cookies, cookie files, username/password auth, `.netrc`, or inherited user config.

If the user asks for automatic IP switching on download errors, implement only this safe policy:

- tunnel/VPN/network failure: reconnect Mullvad, rerun preflight, retry within limits.
- item-level transient failure: retry using yt-dlp retry settings.
- source-side throttle, captcha, login challenge, explicit block, or repeated rate limit: pause the batch and report. Do not switch relays to continue.

For the detailed policy, read `references/safety-and-errors.md`.

## Core Workflows

### Setup / Inspect

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 setup production
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad inspect
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 yt-dlp version
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 catalog
```

Read `references/commands.md` for the full command surface.

For VPN fail-closed testing, use only the guarded command:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad disconnect-test --emergency-unlock
```

Do not use raw `disconnect` during operator work unless the user explicitly accepts the risk. The guarded test constrains to a US relay by default, checks Lockdown behavior, and reconnects before returning.

### Productized Archive SOP

Use this sequence for real channel, playlist, or larger URL-set work:

1. Consult the user for scope, authorized source URLs, rights basis, rights evidence file, output location, and limits.
2. Inventory channel or playlist URLs before downloading.
3. Create or review the item ledger.
4. Run production preflight.
5. Dry-run.
6. Ask for explicit approval before a real run.
7. Run with `--yes`.
8. Verify artifacts.
9. Refresh and review the item ledger.
10. Stop on source-side throttles, captchas, login challenges, account controls, or blocks.

The safety boundary is firm: do not use relay rotation, account switching, login automation, captcha solving, or other continuation tactics to push through source controls.

### Plan A Batch

For one or more explicit URLs:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan "<URL>" --rights "<owned or authorized reason>" --name "<batch-name>"
```

For many URLs, create a text file with one URL per line and run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan --from-file "<urls.txt>" --rights "<owned or authorized reason>" --name "<batch-name>"
```

Attach rights evidence when available:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan --from-file "<urls.txt>" --rights "<owned or authorized reason>" --rights-file "<rights-evidence.md>" --name "<batch-name>"
```

### Inventory A Channel Or Playlist

For channel or playlist work, inventory first:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 inventory "<channel-or-playlist-url>" --rights "<owned or authorized reason>" --rights-file "<rights-evidence.md>" --name "<batch-name>"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 ledger "<manifest.json>"
```

Inventory creates `items.jsonl` for operator review without downloading media. Use `--max-items`, `--max-height`, `--max-downloads`, or `--max-filesize` when the user wants a bounded first pass.

For smoke tests or bounded jobs, add limits:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan "<URL>" --rights "<owned or authorized reason>" --name "<batch-name>" --max-downloads 1 --max-height 360 --max-filesize 50M
```

Read `references/batch-catalog.md` before planning large archives.

### Validate The Install

Use the curated five-video smoke pack before treating an install as ready:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 smoke plan --count 5
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "<manifest.json>"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "<manifest.json>" --dry-run
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "<manifest.json>" --yes
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 verify "<manifest.json>"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 ledger "<manifest.json>" --refresh
```

### Preflight / Dry Run / Real Run

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "<manifest.json>"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "<manifest.json>" --dry-run
```

Only after the user explicitly approves a real download:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "<manifest.json>" --yes
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 verify "<manifest.json>"
```

`run` defaults to safe VPN recovery. It may reconnect Mullvad and retry for tunnel/network failures. Use `--no-recover-vpn` only for diagnostics.

Dry-runs suppress raw yt-dlp JSON by default. Use `--show-output` only when debugging.

## Concurrency Policy

Default to one active YouTube batch at a time. Do not parallelize YouTube downloads by default. Large archives should be systematic through cataloging, download archives, resume support, and pacing, not aggressive concurrency.

If the user asks about parallelism, read `references/batch-catalog.md`.

## Reporting Back

Report:

- what command was run
- whether Mullvad was connected
- batch manifest path
- URL count
- rights evidence path, if attached
- item ledger path and status summary
- whether it was dry-run or real
- stop condition, if any
- verify result, if a real run occurred
- next safe action
