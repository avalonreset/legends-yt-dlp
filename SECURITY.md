# Security Policy

## Supported Versions

Legends YT-DLP Slayer is currently a private alpha. Security fixes target the
`main` branch until tagged releases begin.

## Reporting A Vulnerability

Open a private GitHub security advisory when available, or report the issue to
the repository maintainers through the Avalon Reset Pro GitHub organization.

Do not open a public issue for:

- leaked secrets
- account numbers, tokens, cookies, or credential material
- bypass techniques for platform access controls
- vulnerabilities that expose a user's native IP address during a guarded run

## Sensitive Data

Never include these in bug reports, screenshots, logs, or pull requests:

- Mullvad account numbers
- cookies or browser profile paths
- `.env` contents
- downloaded private media
- client permission documents

## Security Boundary

This project is a safety-oriented control plane. Reports that request or
implement bypasses for DRM, paywalls, captchas, login challenges, account
controls, throttling, or platform blocks will be closed.
