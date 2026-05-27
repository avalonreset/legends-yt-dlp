---
type: raw-source
status: captured
created: 2026-05-27
updated: 2026-05-27
source_url: "https://mullvad.net/en/help/how-use-mullvad-cli"
accessed: 2026-05-27
tags: [mullvad, cli, windows, source]
---

# Mullvad CLI Guide Snapshot

Source: https://mullvad.net/en/help/how-use-mullvad-cli

Accessed on 2026-05-27.

## Captured Facts

- Mullvad documents a desktop CLI for Windows, Linux, and macOS.
- Common commands include `mullvad connect`, `mullvad disconnect`, `mullvad status`, `mullvad status -v`, `mullvad relay update`, and `mullvad relay set location`.
- Mullvad describes a kill switch that activates when connected and a Lockdown mode that blocks internet traffic until connected. The documented Lockdown command is `mullvad lockdown-mode set on`.
- The guide includes examples for checking connection state with Mullvad's connection-check endpoint.

## Project Implications

- The Windows MVP can shell out to the official `mullvad` CLI instead of reverse engineering the GUI.
- Lockdown mode is a core preflight requirement.
- Location selection may be useful for privacy, reliability, and operator preference, but this vault does not treat relay changes as a way to bypass source blocks.
