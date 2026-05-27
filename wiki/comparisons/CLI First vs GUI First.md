---
type: comparison
status: draft
created: 2026-05-27
updated: 2026-05-27
tags: [comparison, cli, gui]
---

# CLI First vs GUI First

## CLI First

Pros:

- Fastest way to validate Mullvad and yt-dlp orchestration.
- Easier to test.
- Easier to package for power users.
- Can become the core behind a GUI later.

Cons:

- Less friendly for the broadest community audience.
- Requires careful help text and reports.

## GUI First

Pros:

- Friendlier first impression.
- Easier for non-technical operators.

Cons:

- Slower to build.
- Risks hiding the hard orchestration problems behind UI work.
- Harder to automate tests early.

## Current Recommendation

Follow [[ADR 002 - Windows First CLI Architecture]] and build CLI first.

