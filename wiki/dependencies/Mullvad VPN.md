---
type: dependency
status: planned
created: 2026-05-27
updated: 2026-05-27
source_url: "https://mullvad.net/en"
tags: [dependency, mullvad, vpn]
---

# Mullvad VPN

Mullvad is the required VPN layer for the Windows MVP.

## Required Capabilities

- CLI available on Windows.
- Connect and status commands.
- Lockdown mode or equivalent fail-closed setting.
- Relay list update.
- Connection verification endpoint.

## Current Source Notes

- [[Mullvad Pricing Snapshot 2026-05-27]]
- [[Mullvad CLI Notes 2026-05-27]]

## Implementation Risks

- CLI output may change between versions.
- Status output may be localized.
- Lockdown mode verification needs exact command validation on the target machine.

