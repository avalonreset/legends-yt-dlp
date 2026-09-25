# Legends YT-DLP: LLM Wiki

Mode: Combined Mode B/C/E
Purpose: Build a Windows-first, rights-aware video archive orchestrator around yt-dlp, Mullvad VPN privacy controls, queue state, audit logs, and community release packaging.
Owner: Ryan / Legends operator
Created: 2026-05-27

## Structure

```text
vault/
├── .raw/
│   ├── idea/
│   ├── sources/
│   └── evidence/
├── wiki/
│   ├── index.md
│   ├── log.md
│   ├── hot.md
│   ├── overview.md
│   ├── domains/
│   ├── modules/
│   ├── decisions/
│   ├── dependencies/
│   ├── flows/
│   ├── runbooks/
│   ├── compliance/
│   ├── research/
│   ├── releases/
│   ├── sources/
│   ├── entities/
│   ├── concepts/
│   ├── comparisons/
│   ├── questions/
│   └── meta/
├── _templates/
├── skills/
├── tools/
└── CODEX.md
```

## Conventions

- All notes use YAML frontmatter with at least `type`, `status`, `created`, `updated`, and `tags`.
- Wikilinks use Obsidian double-bracket note links. Filenames should be unique across the vault.
- `.raw/` contains source documents and source summaries. Do not modify existing raw source files; add a new dated file when evidence changes.
- `wiki/index.md` is the master catalog. Update it whenever pages are added or renamed.
- `wiki/log.md` is append-only. New log entries go at the top.
- `wiki/hot.md` is the short context cache. Rewrite it after significant changes.
- Keep implementation notes separate from compliance boundaries. If a design would bypass platform restrictions or account/IP controls, file it as rejected in [[Key Decisions]] or a dedicated ADR.

## Product Safety Boundary

Allowed project scope:

- Download only videos the operator owns, has permission to download, or can lawfully preserve.
- Verify Mullvad VPN state before network work.
- Fail closed if VPN status, DNS/IP leak checks, or operator policy checks fail.
- Use yt-dlp's built-in archive, retry, sleep, and output controls for reliable, respectful batch operation.
- Stop and require operator review on throttling, captchas, sign-in challenges, copyright ambiguity, or explicit platform blocks.

Out of scope:

- Rotating VPN relays to bypass YouTube throttling, account controls, or IP blocks.
- Circumventing access controls, paywalls, DRM, geo restrictions, or authentication challenges.
- Automating downloads from accounts without clear rights, consent, or a documented lawful basis.
- Hiding abuse, spam, scraping, or copyright infringement.

## Operations

- Setup: read [[Hot Cache]], then [[Project Overview]], then [[Roadmap]].
- Architecture work: update [[Architecture Overview]], module pages, and ADRs.
- Runbook work: update [[Windows Operator Setup]], [[Preflight Checklist]], and [[Batch Archive SOP]].
- Source work: add immutable notes under `.raw/sources/`, then synthesize a page under `wiki/sources/` or `wiki/research/`.
- Health check: run `powershell -ExecutionPolicy Bypass -File tools/vault-health-check.ps1`.
- Skill suite: use `skills/legends-yt-dlp/SKILL.md` as the Codex operating procedure for archive batches.
