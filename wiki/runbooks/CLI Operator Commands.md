---
type: runbook
status: active
created: 2026-05-27
updated: 2026-05-28
tags: [runbook, cli, operator]
---

# CLI Operator Commands

Use the PowerShell launcher from the project root:

```powershell
legends-yt-dlp doctor
```

## Tooling

```powershell
legends-yt-dlp yt-dlp install
legends-yt-dlp yt-dlp version
```

## Mullvad

```powershell
legends-yt-dlp mullvad status --verbose
legends-yt-dlp mullvad login
legends-yt-dlp mullvad lockdown on
legends-yt-dlp mullvad connect
legends-yt-dlp mullvad recover
legends-yt-dlp mullvad disconnect-test --emergency-unlock
legends-yt-dlp mullvad inspect
```

The `login` command reads `MULLVAD_ACCOUNT_NUMBER` from `.env` and redacts it in output.

First-class Mullvad wrappers now cover account/device reads, version, auto-connect, LAN sharing, relay constraints and updates, DNS defaults/custom servers, tunnel options, split tunneling, anti-censorship mode, and API access inspection. `mullvad raw` remains available for installed CLI features not yet wrapped.

`mullvad disconnect` refuses by default when Lockdown is on. Use `mullvad disconnect-test --emergency-unlock` for fail-closed testing; it constrains Mullvad to a US relay by default, verifies the blocked state, and reconnects before returning. The emergency unlock path disables Lockdown only if recovery fails, which is an operator-rescue fallback rather than production posture.

## Batch Planning

```powershell
legends-yt-dlp plan "https://www.youtube.com/@CHANNEL" --rights "owned or authorized" --name "channel-name"
legends-yt-dlp preflight "batches\...\manifest.json"
```

## Running

Real downloads require passing preflight and an explicit `--yes` flag:

```powershell
legends-yt-dlp run "batches\...\manifest.json" --dry-run
legends-yt-dlp run "batches\...\manifest.json" --yes
```

Until Mullvad is connected, default preflight exits nonzero and the runner does not start.
