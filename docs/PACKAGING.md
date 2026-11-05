# Alpha Packaging

Use the packaging script from the repository root:

```bash
python scripts/check_release.py
```

The script writes:

- `dist/legends-yt-dlp-0.1.2.zip`
- `dist/legends-yt-dlp-0.1.2.zip.sha256`

The package includes tracked source, docs, scripts, tests, the router skill file, and legal/community files. It excludes ignored local runtime state:

- `.env` and `.env.*`
- `.local/`
- `batches/`
- `reports/`
- `downloads/`
- `cache/`
- `secrets/`
- `cookies/`
- `.git/`

After unpacking, the first command for a user should be:

```powershell
legends-yt-dlp onboard
```

## Release Checklist

Before attaching the zip to a release:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
python -m compileall -q src tests
python scripts/check_release.py
git diff --check
$accountEnv = 'MULLVAD_ACCOUNT_NUMBER'
$secretPattern = "$accountEnv=.*[0-9]|[0-9]{16}"
rg -n $secretPattern --glob '!*.pyc' --glob '!.git/**' --glob '!.env' --glob '!.local/**' --glob '!batches/**' --glob '!reports/**'
```

Then inspect the package:

```powershell
tar -tf dist\legends-yt-dlp-0.1.2.zip
Get-Content dist\legends-yt-dlp-0.1.2.zip.sha256
```

Do not publish a package that contains account numbers, cookies, downloaded media, local `yt-dlp.exe` binaries, batch outputs, client rights evidence, or untracked local experiment files.
