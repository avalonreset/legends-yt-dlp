# CLI Commands

Use the PowerShell launcher from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 <command>
```

## Doctor

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor --require-connected
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor --production
```

Checks Mullvad, `yt-dlp`, `ffmpeg`, local account configuration, and connected state.

`doctor --production` additionally requires Mullvad Lockdown on, split tunneling off, LAN sharing blocked, and auto-connect on.

## Mullvad

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad status --verbose
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad login
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad lockdown on
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad connect
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad recover
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad inspect
```

`mullvad login` reads `MULLVAD_ACCOUNT_NUMBER` from `.env` and redacts it in output.

The CLI exposes first-class wrappers for the useful Mullvad command surface:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad account get
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad account devices
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad version
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad auto-connect get
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad auto-connect set on
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad lan get
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad lan set block
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad relay get
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad relay update
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad relay location us
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad dns get
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad dns default --block-ads --block-trackers --block-malware
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad tunnel get
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad tunnel quantum-resistant on
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad tunnel ipv6 off
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad split-tunnel get
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad split-tunnel set off
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad anti-censorship get
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad api-access get
```

Raw passthrough remains available for installed Mullvad CLI features that do not yet have a named wrapper:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad raw --timeout 120 relay list
```

## yt-dlp

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 yt-dlp install
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 yt-dlp version
```

The install command downloads the official Windows standalone executable and verifies it against upstream checksums.

## Batch Planning

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan "https://www.youtube.com/@CHANNEL" --rights "owned or authorized" --name "channel-name"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan "https://example.com/a" "https://example.com/b" --rights "owned or authorized" --name "multi-url"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan --from-file ".\urls.txt" --rights "owned or authorized" --name "url-file"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 catalog
```

The plan command creates:

- `manifest.json`
- `urls.txt`
- `yt-dlp.conf`
- download archive path
- output and temp folders

Generated batch folders are ignored by git.

## Preflight

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "batches\...\manifest.json"
```

Default preflight requires production posture and anonymous `yt-dlp` auth policy: Mullvad connected, Lockdown on, split tunneling off, LAN sharing blocked, auto-connect on, no browser cookies, no cookie files, no account auth, and ignored user-level `yt-dlp` config.

For local harness testing only:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "batches\...\manifest.json" --no-require-connected
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "batches\...\manifest.json" --no-production
```

## Run

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --dry-run
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --yes
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --yes --vpn-recovery-attempts 3
```

Real downloads require passing production preflight and an explicit `--yes`. The runner refuses real downloads with `--no-production` or `--no-require-connected`.

`run` defaults to safe VPN recovery for Mullvad/tunnel/network failures. Use `--no-recover-vpn` for diagnostics.

Do not use relay/location commands as an automatic response to source-side throttling or block signals.
