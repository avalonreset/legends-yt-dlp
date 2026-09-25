# Safety and Error Policy

## Purpose

The skill helps Codex operate a powerful downloader safely. It must not convert privacy tooling into evasion tooling.

## Required Gates

Before any real run:

- `doctor --production` passes.
- Batch preflight passes.
- A JavaScript runtime is available for YouTube extraction.
- Generated `yt-dlp` config uses anonymous mode: `--ignore-config`, `--no-cookies`, and `--no-cookies-from-browser`.
- No browser cookies, cookie files, username/password auth, `.netrc`, or account credentials are used for any batch.
- The CLI prints a legal-use notice reminding operators to download only when they have rights, permission, a license, fair use, or another lawful basis.
- User explicitly approves a real run.

## Stop Conditions

Pause and report if any of these appear:

- Mullvad disconnected or ambiguous
- captcha or bot challenge
- sign-in challenge
- explicit platform block
- repeated rate-limit signal
- DRM, paywall, private access, or access-control signal

## Retry Policy

Allowed automatic recovery:

- reconnect Mullvad after tunnel or daemon failure
- rerun preflight after reconnect
- rely on yt-dlp retries for transient item/network failures
- resume using `archive.txt`
- retry the batch after transient network failure because yt-dlp's download archive skips completed items

Not allowed:

- rotating relays/IPs to bypass throttling or blocks
- automating captchas or login challenges
- using proxy/geo/impersonation options to evade platform controls

## User Language

If the user asks for bypass behavior, be direct:

"I can build reconnect and resume logic for tunnel failures, but I cannot automate VPN IP rotation to bypass source-side throttling or blocks. The safe behavior is to pause and report that condition."

## Implemented Classifier

Treat these as stop/source-block signals:

- captcha
- sign in or login challenge
- HTTP 429 or too many requests
- rate limit
- temporarily blocked
- forbidden or access denied
- private video
- DRM

Treat these as recoverable network signals:

- network unreachable
- no route to host
- connection reset/aborted/refused
- timeout
- DNS or temporary name-resolution failure
- TLS/SSL transport failure
- remote end closed connection
