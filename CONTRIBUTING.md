# Contributing

Thanks for helping improve Legends YT-DLP Slayer.

## Development Setup

```powershell
git clone https://github.com/avalonreset-pro/legends-yt-dlp-slayer.git
cd legends-yt-dlp-slayer
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor
```

For production-path testing, install the Mullvad app, fund/login to a Mullvad
account, create an ignored `.env` from `.env.example`, then run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 setup production
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor --production
```

## Test Gate

Run the deterministic gate before opening a pull request:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
python -m compileall -q src tests
powershell -ExecutionPolicy Bypass -File tools\vault-health-check.ps1
git diff --check
```

## Safety Rules

Contributions must preserve these rules:

- no browser cookies or account auth in production batches
- no relay rotation to continue through throttles, captchas, login challenges,
  account controls, or source blocks
- no DRM, paywall, captcha, or access-control bypass features
- no committed secrets, downloaded media, cookies, or batch outputs

When source-side controls say stop, the tool stops and reports.

## Pull Request Checklist

- Tests pass.
- Docs and wiki are updated for user-visible behavior.
- Secret scan is clean.
- New commands have a safe default and a documented failure mode.
- Generated packages exclude `.env`, `.local`, `batches`, `reports`, and media.
