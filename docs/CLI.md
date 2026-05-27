# CLI Commands

Use the PowerShell launcher from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 <command>
```

## Doctor

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor --require-connected
```

Checks Mullvad, `yt-dlp`, `ffmpeg`, local account configuration, and connected state.

## Mullvad

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad status --verbose
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad login
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad lockdown on
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad connect
```

`mullvad login` reads `MULLVAD_ACCOUNT_NUMBER` from `.env` and redacts it in output.

## yt-dlp

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 yt-dlp install
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 yt-dlp version
```

The install command downloads the official Windows standalone executable and verifies it against upstream checksums.

## Batch Planning

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan "https://www.youtube.com/@CHANNEL" --rights "owned or authorized" --name "channel-name"
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

Default preflight requires Mullvad to be connected. For local harness testing only:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "batches\...\manifest.json" --no-require-connected
```

## Run

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --dry-run
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "batches\...\manifest.json" --yes
```

Real downloads require passing preflight and an explicit `--yes`.

