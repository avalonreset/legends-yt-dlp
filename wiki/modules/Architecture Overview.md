---
type: module
status: draft
created: 2026-05-27
updated: 2026-05-27
tags: [architecture, module]
---

# Architecture Overview

The first implementation should be a Windows CLI app that coordinates existing tools and maintains state. Avoid GUI work until the core orchestration is proven.

```mermaid
flowchart TD
  A["Operator Command"] --> B["CLI Control Plane"]
  B --> C["Policy Engine"]
  C --> D["Mullvad Guard Module"]
  D --> E["YT DLP Runner"]
  E --> F["Job Queue and State Store"]
  E --> G["Downloads Folder"]
  F --> H["Telemetry and Reports"]
  D --> H
  C --> H
```

## Components

- [[CLI Control Plane]] receives commands and renders operator output.
- [[Policy Engine]] checks rights basis, target allowlists, and stop conditions.
- [[Mullvad Guard Module]] verifies VPN and leak-prevention state before network work.
- [[YT DLP Runner]] owns process execution and yt-dlp config generation.
- [[Job Queue and State Store]] records batch state.
- [[Telemetry and Reports]] writes evidence and summaries.

## First Stack Guess

Use Python or Node for the first CLI. Python has strong process control and packaging options; Node has friendlier TUI/CLI libraries. Defer the decision until the repository scaffold starts and local runtime preferences are checked.

## Core Rule

The runner may start a download only after both [[Policy Engine]] and [[Mullvad Guard Module]] return a passing preflight.

