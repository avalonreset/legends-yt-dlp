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
legends-yt-dlp mullvad inspect
legends-yt-dlp mullvad recover
legends-yt-dlp mullvad disconnect-test --emergency-unlock
legends-yt-dlp mullvad account get
legends-yt-dlp mullvad account devices
legends-yt-dlp mullvad version
legends-yt-dlp mullvad auto-connect get
legends-yt-dlp mullvad auto-connect set on
legends-yt-dlp mullvad lan get
legends-yt-dlp mullvad lan set block
legends-yt-dlp mullvad relay get
legends-yt-dlp mullvad relay update
legends-yt-dlp mullvad relay location us
legends-yt-dlp mullvad dns get
legends-yt-dlp mullvad dns default
legends-yt-dlp mullvad tunnel get
legends-yt-dlp mullvad tunnel quantum-resistant on
legends-yt-dlp mullvad tunnel ipv6 off
legends-yt-dlp mullvad split-tunnel get
legends-yt-dlp mullvad split-tunnel set off
legends-yt-dlp mullvad anti-censorship get
legends-yt-dlp mullvad api-access get
```

## Raw Passthrough

Raw passthrough exists for any installed Mullvad CLI command not yet wrapped:

```powershell
legends-yt-dlp mullvad raw --timeout 120 relay list
```

The wrapper redacts the Mullvad account number in command output.

## Disconnect Safety

Raw disconnect can strand the operator when Lockdown is on. The wrapped `mullvad disconnect` command refuses in that state unless `--force` is explicit.

Use this for controlled fail-closed testing:

```powershell
legends-yt-dlp mullvad disconnect-test --emergency-unlock
```

The guarded test sets a US relay constraint by default, enables Lockdown, verifies the blocked disconnected state, and reconnects before returning. `--emergency-unlock` disables Lockdown only if recovery fails, restoring operator connectivity at the cost of native-IP exposure.

## Boundary

Relay/location controls are manual operator controls. They must not be automated as a response to YouTube throttling, captchas, account controls, or block signals.
