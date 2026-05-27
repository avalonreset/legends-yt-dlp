# Safety and Error Policy

## Purpose

The skill helps Codex operate a powerful downloader safely. It must not convert privacy tooling into evasion tooling.

## Required Gates

Before any real run:

- `doctor --require-connected` passes.
- Batch has a rights basis.
- Batch preflight passes.
- User explicitly approves a real run.

## Stop Conditions

Pause and report if any of these appear:

- missing rights basis
- Mullvad disconnected or ambiguous
- captcha or bot challenge
- sign-in challenge
- explicit platform block
- repeated rate-limit signal
- DRM, paywall, private access, or access-control signal
- copyright ambiguity

## Retry Policy

Allowed automatic recovery:

- reconnect Mullvad after tunnel or daemon failure
- rerun preflight after reconnect
- rely on yt-dlp retries for transient item/network failures
- resume using `archive.txt`

Not allowed:

- rotating relays/IPs to bypass throttling or blocks
- automating captchas or login challenges
- using proxy/geo/impersonation options to evade platform controls
- running without a rights basis

## User Language

If the user asks for bypass behavior, be direct:

"I can build reconnect and resume logic for tunnel failures, but I cannot automate VPN IP rotation to bypass source-side throttling or blocks. The safe behavior is to pause and report that condition."

