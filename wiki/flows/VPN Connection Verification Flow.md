---
type: flow
status: draft
created: 2026-05-27
updated: 2026-05-27
tags: [flow, vpn, mullvad]
---

# VPN Connection Verification Flow

```mermaid
flowchart TD
  A["Start preflight"] --> B["Find mullvad CLI"]
  B --> C["Read mullvad status"]
  C --> D{"Connected?"}
  D -->|no| X["Fail closed"]
  D -->|yes| E["Read verbose status"]
  E --> F["Check required settings"]
  F --> G["Optional egress check"]
  G --> H{"All checks passed?"}
  H -->|no| X
  H -->|yes| I["Allow yt-dlp runner"]
```

## Verification Notes

- Exact commands must be verified on the target Windows machine.
- Do not parse localized text if a structured output mode exists.
- Ambiguous output is a failed preflight.

