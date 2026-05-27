# Safety and Use Policy

This project is for lawful, rights-aware archiving only.

## Allowed Use

- Downloading your own videos.
- Downloading videos where the creator or rights holder gave permission.
- Downloading public-domain content.
- Downloading content under a license that permits local archival use.
- Creating a local preservation copy when you have a documented lawful basis.
- Using Mullvad VPN as a privacy and leak-prevention layer.

## Disallowed Use

- Downloading copyrighted videos without permission or lawful basis.
- Bypassing DRM, paywalls, private access controls, captchas, or login challenges.
- Rotating VPN endpoints to continue through throttling, bans, account controls, or IP blocks.
- Misrepresenting the project as a way to avoid platform consequences.
- Hiding abusive scraping, spam, or copyright infringement.

## Stop Conditions

The runner should pause or refuse to continue when it sees:

- missing rights basis
- Mullvad disconnected or ambiguous
- captcha or bot challenge
- sign-in challenge
- explicit platform block
- repeated rate-limit signal
- DRM, paywall, or access-control signal

## Automatic Recovery

The app may automatically reconnect Mullvad and retry for tunnel, daemon, DNS, or transient network failures. It may resume the batch because `yt-dlp` download archives skip completed items.

The app must not rotate relays or IPs to keep downloading through source-side throttling, login challenges, captchas, account controls, or explicit blocks.

## Operator Rule

When the source says stop, the tool stops. Human review comes before any resume.
