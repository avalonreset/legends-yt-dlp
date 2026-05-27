# Mullvad Controls

The skill operates Mullvad through the official Windows CLI, usually found at:

```text
C:\Program Files\Mullvad VPN\resources\mullvad.exe
```

Use the project launcher instead of calling the binary directly:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad inspect
```

## Proven Good Posture

- connected
- lockdown mode on
- auto-connect on
- LAN sharing blocked
- split tunneling off
- quantum-resistant tunnel on
- IPv6 off
- direct API access

## First-Class Controls

- `mullvad account get`
- `mullvad account devices`
- `mullvad status --verbose`
- `mullvad inspect`
- `mullvad connect`
- `mullvad reconnect`
- `mullvad recover`
- `mullvad disconnect`
- `mullvad lockdown get|on|off`
- `mullvad auto-connect get|set on|off`
- `mullvad lan get|set allow|block`
- `mullvad relay get|list|update|location|provider|ownership|multihop`
- `mullvad dns get|default|custom`
- `mullvad tunnel get|quantum-resistant|ipv6|rotate-key`
- `mullvad split-tunnel get|set|app`
- `mullvad anti-censorship get|mode`
- `mullvad api-access get|list`
- `mullvad raw`

## Relay Boundary

Relay commands are for manual operator selection and connection hygiene. They are not a block-bypass loop.
