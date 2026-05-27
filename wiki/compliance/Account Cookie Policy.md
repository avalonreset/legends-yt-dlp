---
type: compliance-note
status: active
created: 2026-05-27
updated: 2026-05-27
tags: [youtube, yt-dlp, cookies, account-safety]
---

# Account Cookie Policy

Production batches should not attach a normal YouTube account to large archive activity.

## Default Rule

- Do not use browser cookies.
- Do not use cookie files.
- Do not use `--cookies-from-browser`.
- Do not use username/password login.
- Do not use `.netrc` auth.
- Do not inherit user-level `yt-dlp` config.

## Reasoning

Public videos usually do not require a logged-in browser session. Adding cookies or account credentials creates an account-level association that the project cannot safely promise to manage.

If a target requires authenticated access, treat it as a separate high-risk authorization workflow. Prefer official export, creator-owned download paths, or a documented manual approval path over attaching a daily-use YouTube account to a bulk run.

## Implementation

Generated `yt-dlp` configs include `--ignore-config`, `--no-cookies`, and `--no-cookies-from-browser`. Production preflight rejects forbidden cookie and account-auth options before a run starts.
