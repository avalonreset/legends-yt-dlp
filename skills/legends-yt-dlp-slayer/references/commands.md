# Slayer CLI Command Reference

Run all commands from the project root.

## Doctor

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor --require-connected
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 doctor --production
```

Use `doctor --production` before real work. It requires connected Mullvad, Lockdown on, split tunneling off, LAN sharing blocked, and auto-connect on.

## Mullvad

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad inspect
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad status --verbose
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad login
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad lockdown on
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad connect
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad reconnect
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad recover
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad disconnect
```

Useful settings:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad auto-connect set on
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad lan set block
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad split-tunnel set off
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad tunnel quantum-resistant on
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad tunnel ipv6 off
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad relay get
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad dns get
```

Manual relay selection is available:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 mullvad relay location us
```

Do not use relay selection as an automatic response to source-side blocks.

## yt-dlp

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 yt-dlp install
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 yt-dlp version
```

## Catalog and Batches

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 catalog
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan "<URL>" --rights "<basis>" --name "<name>"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan "<URL1>" "<URL2>" --rights "<basis>" --name "<name>"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 plan --from-file "<urls.txt>" --rights "<basis>" --name "<name>"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 preflight "<manifest.json>"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "<manifest.json>" --dry-run
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "<manifest.json>" --yes
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 run "<manifest.json>" --yes --vpn-recovery-attempts 3
```

`run` defaults to safe VPN recovery. It can reconnect Mullvad and retry after transient tunnel/network failures. It must not continue through source-side block signals.
