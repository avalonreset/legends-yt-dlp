---
type: research
status: summarized
created: 2026-05-27
updated: 2026-05-27
source_url: "https://mullvad.net/en/help/how-use-mullvad-cli"
tags: [research, mullvad, cli, windows]
---

# Mullvad CLI Notes 2026-05-27

Source: [[Mullvad CLI Guide]]

## Findings

- Mullvad documents an official CLI for desktop platforms including Windows.
- The guide covers status, connect, disconnect, relay update, relay location, and other operational commands.
- Mullvad documents kill-switch behavior and Lockdown mode, including `mullvad lockdown-mode set on`.
- The guide includes connection-check examples.

## Project Implications

- The MVP can start with subprocess calls to the official CLI.
- `slayer doctor` should verify the CLI path, status command, version if available, and Lockdown mode.
- Live target-machine testing is required because exact CLI output and localization can affect parsers.
