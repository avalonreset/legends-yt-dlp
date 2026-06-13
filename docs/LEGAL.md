# Legal And Attribution Notes

> This analysis is automated compliance assistance, not legal advice.
> Always verify licensing decisions with your own due diligence.
> For complex or high-stakes situations, consult a qualified attorney.

## Project License

Legends YT-DLP Slayer is released under the MIT License. The code in this repository is an original wrapper/control plane and does not copy yt-dlp or Mullvad VPN source code.

## Third-Party Tools

### yt-dlp

The CLI downloads the official Windows `yt-dlp.exe` release from the upstream `yt-dlp/yt-dlp` project and verifies it against upstream checksum files. The upstream repository currently identifies its license as the Unlicense.

The repository and alpha package do not bundle `yt-dlp.exe`. If a future release bundles the executable, include upstream license text and current third-party notices in that release package.

### Mullvad VPN

The CLI controls the official Mullvad command-line interface installed by the user's local Mullvad VPN app. The Mullvad VPN app repository currently identifies its license as GPL-3.0. This repository and alpha package do not bundle Mullvad VPN, Mullvad CLI, Mullvad account access, or Mullvad assets.

Users install, fund, and operate Mullvad separately.

## Platform Boundary

This project is not affiliated with, sponsored by, or endorsed by YouTube, Google, yt-dlp, Mullvad VPN AB, or related rights holders.

The safety boundary is part of the product:

- no DRM, paywall, captcha, login, account-control, or access-control bypasses
- no relay or account rotation to continue through source-side throttles or blocks
- no production browser cookies or account auth
- a legal-use notice before real downloads
- optional rights notes and evidence files for batches

## Operator Responsibility

The item ledger and optional rights evidence folder are local context aids. They do not grant permission by themselves. Operators remain responsible for downloading and using material only when they have rights, permission, a license, fair use, or another lawful basis.
