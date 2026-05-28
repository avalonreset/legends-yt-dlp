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

Inventory uses the same boundary. If channel or playlist inventory returns source-side warning signals, the tool should pause before creating a batch.

## Planning Evidence

Large jobs should start with a documented rights basis, optional copied rights evidence, and a reviewable item ledger. The ledger is an audit aid, not permission by itself: operators must still verify that each planned or inventoried item fits the stated rights basis before a real run.

## Production VPN Posture

Production runs require Mullvad to be connected with Lockdown mode enabled. Lockdown is mandatory because a reconnect, manual disconnect, daemon issue, or tunnel failure must not fall back to the native network path.

Production checks also require split tunneling off, LAN sharing blocked, and auto-connect on. These settings do not guarantee anonymity or immunity from platform controls; they reduce accidental leak and misconfiguration risk.

## Account And Cookie Policy

Production batches must use anonymous `yt-dlp` operation by default:

- no browser cookies
- no cookie files
- no `--cookies-from-browser`
- no username/password login
- no `.netrc` auth
- no inherited user-level `yt-dlp` config

`yt-dlp` does not need the user to be logged into YouTube for public videos, and this project should not attach a normal YouTube account to large archive runs. If a video truly requires account access, treat it as a separate high-risk authorization workflow and prefer official export or creator-owned download paths.

## Automatic Recovery

The app may automatically reconnect Mullvad and retry for tunnel, daemon, DNS, or transient network failures. It may resume the batch because `yt-dlp` download archives skip completed items.

The app must not rotate relays or IPs to keep downloading through source-side throttling, login challenges, captchas, account controls, or explicit blocks.

## Operator Rule

When the source says stop, the tool stops. Human review comes before any resume.
