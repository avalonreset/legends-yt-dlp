---
type: compliance-note
status: draft
created: 2026-05-27
updated: 2026-05-27
tags: [youtube, compliance]
---

# YouTube Boundary Notes

YouTube-specific automation needs a conservative boundary because account health, platform terms, copyright, and rate controls can all be implicated.

## Practical Boundary

- Prefer official export paths for content you own when they meet the need.
- Use yt-dlp only where you have a lawful basis.
- Do not automate around captchas, sign-in challenges, or source-side blocks.
- Treat repeated throttling as a signal to stop, not a reason to rotate relays.

## Product Implication

The app should make unsafe states visible and boring: clear block reason, stopped queue, next human action.

