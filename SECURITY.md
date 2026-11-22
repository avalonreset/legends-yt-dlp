# Security Policy

## Supported Versions

| Version | Supported |
| --- | --- |
| `0.2.x` (`>= 0.2.1`) | Yes |
| `< 0.2.1` | No |

## Credential, Capture, and Network Boundaries

1. `legends-youtube` reads Google/YouTube API credentials strictly from explicit environment variables (`YOUTUBE_API_KEY`, `YOUTUBE_ACCESS_TOKEN`, `YOUTUBE_REFRESH_TOKEN`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`), `--dotenv`, or `--token-file`. It never scans browser profiles, cookie databases, DPAPI stores, or system keyrings.
2. Outbound API traffic in `legends_youtube` is restricted to `https://www.googleapis.com`, `https://youtubeanalytics.googleapis.com`, `https://oauth2.googleapis.com`, and public YouTube watch/oEmbed/feed endpoints with automatic HTTP 3xx redirects disabled (`_NoRedirectHandler`).
3. Description link probing (`links-audit --probe-https`) rejects loopback, link-local, and RFC1918 private addresses (CWE-918 SSRF defense).
4. `legends-yt-dlp` (`legends_ytdlp`) enforces `--ignore-config`, `--no-cookies`, and `--no-cookies-from-browser` under a strict `yt-dlp.conf` option allowlist (blocking `--exec*`, `--alias`, `--plugin-dirs`, `--config-location*`, `--load-info-json`, `--print-to-file`, and `--proxy`), verifies `yt-dlp.conf` SHA-256 digests on both `preflight` and `run`, and verifies upstream `yt-dlp` binaries against `SHA2-256SUMS`.
5. File reads, media paths, and single-file `--output` writes reject symlinks (`CWE-59`) and require explicit `--overwrite` before replacing existing files.
6. Reports or requests that implement bypasses for DRM, paywalls, captchas, login challenges, account controls, or platform rate limits are out of scope and will be closed.

## Reporting Vulnerabilities

Report security issues via [GitHub Issues](https://github.com/avalonreset/legends-youtube/issues) or private GitHub security advisories without including live credentials, tokens, cookies, or Mullvad account numbers.
