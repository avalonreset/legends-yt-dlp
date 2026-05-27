---
type: evidence
status: captured
created: 2026-05-27
updated: 2026-05-27
tags: [evidence, mullvad, cli]
---

# Mullvad Control Surface - 2026-05-27

## Login and Connection

- Login through the local `.env` account succeeded.
- Lockdown mode was enabled through the CLI.
- VPN connection succeeded.
- `doctor --require-connected` passed.

## Installed CLI Surface

`mullvad-cli 2026.2` exposes these top-level commands:

- `account`
- `auto-connect`
- `beta-program`
- `lockdown-mode`
- `dns`
- `lan`
- `connect`
- `disconnect`
- `reconnect`
- `relay`
- `api-access`
- `anti-censorship`
- `split-tunnel`
- `status`
- `tunnel`
- `version`
- `factory-reset`
- `reset-settings`
- `custom-list`
- `import-settings`
- `export-settings`
- `log`

## Wrapped in Slayer CLI

- status and inspect
- account get and device listing
- login, connect, disconnect, reconnect
- lockdown get/set
- version
- auto-connect get/set
- LAN get/set
- relay get/list/update/location/provider/ownership/multihop
- DNS get/default/custom
- tunnel get/quantum-resistant/ipv6/rotate-key
- split tunnel get/set/app add/remove/clear
- anti-censorship get/mode
- API access get/list
- raw passthrough with account-number redaction

## Current Posture

- Connected state: connected.
- Lockdown mode: on.
- Auto-connect: on.
- LAN sharing: block.
- Split tunneling: off.
- Quantum resistance: on.
- IPv6: off.
- API access: direct.

