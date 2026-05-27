---
type: readme
status: active
created: 2026-05-27
updated: 2026-05-27
tags: [readme, project]
---

# Legends YT-DLP Slayer

Development vault for a Windows-first, rights-aware video archive orchestrator built around yt-dlp and Mullvad VPN.

The vault is the operating surface for the project. Start with:

- [[Project Overview]]
- [[Hot Cache]]
- [[Roadmap]]
- [[Use Policy]]
- [[Windows Operator Setup]]
- [[Preflight Checklist]]

## Operating Boundary

This project is for lawful archiving of videos the operator owns, has permission to download, or can otherwise legally preserve. Mullvad is treated as a privacy and leak-prevention layer, not as an evasion layer. The system should fail closed when VPN state is unsafe, back off when platforms throttle, and stop when a source blocks or challenges access.

## Vault Layout

- `.raw/` stores immutable source notes, briefings, and evidence.
- `wiki/` stores synthesized project knowledge.
- `_templates/` stores reusable note templates.
- `tools/` stores vault maintenance helpers.
- `CODEX.md` defines the vault rules for Codex sessions.

