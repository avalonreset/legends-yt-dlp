---
type: runbook
status: active
created: 2026-05-27
updated: 2026-05-27
tags: [runbook, cli, operator]
---

# CLI Operator Commands

Use the PowerShell launcher from the project root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor
```

## Tooling

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 yt-dlp install
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 yt-dlp version
```

## Mullvad

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad status --verbose
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad login
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad lockdown on
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad connect
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad inspect
```

The `login` command reads `MULLVAD_ACCOUNT_NUMBER` from `.env` and redacts it in output.

First-class Mullvad wrappers now cover account/device reads, version, auto-connect, LAN sharing, relay constraints and updates, DNS defaults/custom servers, tunnel options, split tunneling, anti-censorship mode, and API access inspection. `mullvad raw` remains available for installed CLI features not yet wrapped.

## Batch Planning

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan "https://www.youtube.com/@CHANNEL" --rights "owned or authorized" --name "channel-name"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "batches\...\manifest.json"
```

## Running

Real downloads require passing preflight and an explicit `--yes` flag:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --dry-run
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --yes
```

Until Mullvad is connected, default preflight exits nonzero and the runner does not start.
