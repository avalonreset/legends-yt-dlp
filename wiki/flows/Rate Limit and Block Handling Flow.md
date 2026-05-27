---
type: flow
status: draft
created: 2026-05-27
updated: 2026-05-27
tags: [flow, rate-limit, safety]
---

# Rate Limit and Block Handling Flow

```mermaid
flowchart TD
  A["yt-dlp item run"] --> B{"Normal success?"}
  B -->|yes| C["Mark item done"]
  B -->|no| D{"Transient network error?"}
  D -->|yes| E["Retry within configured limit"]
  D -->|no| F{"Throttle, captcha, login, or block?"}
  F -->|yes| G["Pause batch and require operator review"]
  F -->|no| H["Mark item failed and continue if policy allows"]
```

## Policy

Relay changes are not an automatic recovery path for throttling, captchas, login prompts, or source-side blocks. The correct behavior is pause, report, and require operator review.

