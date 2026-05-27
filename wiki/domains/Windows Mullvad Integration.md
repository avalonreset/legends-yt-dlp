---
type: domain
status: active
created: 2026-05-27
updated: 2026-05-27
tags: [domain, mullvad, windows, vpn]
---

# Windows Mullvad Integration

This domain covers how the Windows MVP interacts with Mullvad VPN.

## MVP Assumption

The app should use the official Mullvad CLI where possible:

- `mullvad status`
- `mullvad status -v`
- `mullvad connect`
- `mullvad relay update`
- `mullvad relay set location`
- `mullvad lockdown-mode set on`, with live target-machine verification still required

## Product Boundary

Mullvad is used for privacy, leak prevention, and operator-controlled network posture. It is not used to evade platform throttling or source blocks.

## Open Engineering Questions

- What exact CLI output should the parser expect on current Windows installs?
- Does the target machine have Mullvad installed and on PATH?
- How should the app verify Lockdown mode without relying on brittle localized text?
- Should the app require Mullvad's connection-check endpoint before each batch?

## Linked Pages

- [[Mullvad Guard Module]]
- [[VPN Connection Verification Flow]]
- [[Mullvad CLI Notes 2026-05-27]]
