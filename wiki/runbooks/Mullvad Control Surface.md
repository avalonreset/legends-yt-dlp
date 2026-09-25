---
type: runbook
status: active
created: 2026-05-27
updated: 2026-05-28
tags: [runbook, mullvad, vpn]
---

# Mullvad Control Surface

The installed Mullvad Windows app exposes `mullvad-cli 2026.2` at:

```text
C:\Program Files\Mullvad VPN\resources\mullvad.exe
```

## Current Proven State

- Account is logged in and active through 2026-06-27.
- VPN is connected.
- Lockdown mode is on.
- Auto-connect is on.
- Local network sharing is blocked.
- Split tunneling is off.
- Quantum-resistant tunnel mode is on.
- IPv6 is off.
- Mullvad API access is direct.
- Current relay constraint is country `us`.

## Wrapped Commands

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad inspect
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad recover
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad disconnect-test --emergency-unlock
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
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad dns default
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad tunnel get
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad tunnel quantum-resistant on
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad tunnel ipv6 off
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad split-tunnel get
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad split-tunnel set off
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad anti-censorship get
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad api-access get
```

## Raw Passthrough

Raw passthrough exists for any installed Mullvad CLI command not yet wrapped:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad raw --timeout 120 relay list
```

The wrapper redacts the Mullvad account number in command output.

## Disconnect Safety

Raw disconnect can strand the operator when Lockdown is on. The wrapped `mullvad disconnect` command refuses in that state unless `--force` is explicit.

Use this for controlled fail-closed testing:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 mullvad disconnect-test --emergency-unlock
```

The guarded test sets a US relay constraint by default, enables Lockdown, verifies the blocked disconnected state, and reconnects before returning. `--emergency-unlock` disables Lockdown only if recovery fails, restoring operator connectivity at the cost of native-IP exposure.

## Boundary

Relay/location controls are manual operator controls. They must not be automated as a response to YouTube throttling, captchas, account controls, or block signals.
