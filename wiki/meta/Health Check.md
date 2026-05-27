---
type: meta
status: active
created: 2026-05-27
updated: 2026-05-27
tags: [health, meta]
---

# Health Check

Run:

```powershell
powershell -ExecutionPolicy Bypass -File tools/vault-health-check.ps1
```

Expected initial result:

- Required vault files present.
- No dead wikilinks.
- Git initialized.

