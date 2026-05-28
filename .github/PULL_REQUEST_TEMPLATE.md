## Summary

- 

## Verification

- [ ] `$env:PYTHONPATH='src'; python -m unittest discover -s tests`
- [ ] `$env:PYTHONPATH='src'; python -m compileall -q src tests`
- [ ] `powershell -ExecutionPolicy Bypass -File tools\vault-health-check.ps1`
- [ ] `git diff --check`
- [ ] Secret scan checked for `.env`, account numbers, cookies, media, and batch outputs

## Safety

- [ ] Preserves anonymous production yt-dlp behavior
- [ ] Does not add relay/account rotation to continue through source-side controls
- [ ] Does not bypass DRM, paywalls, captchas, login challenges, account controls, throttling, or platform blocks
- [ ] Updates docs/wiki for user-visible behavior
