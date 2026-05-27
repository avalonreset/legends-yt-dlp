---
type: question
status: answered
created: 2026-05-27
updated: 2026-05-27
tags: [question, mvp]
---

# What are we building first?

Build the Windows CLI control plane and the preflight system first.

## Answer

The first useful milestone is a `doctor` command that proves the machine can safely run a batch:

- Mullvad installed and connected.
- Lockdown mode verified or clearly reported as missing.
- yt-dlp installed.
- ffmpeg installed.
- Output folder writable.
- Config directory writable.

Only after that should the project implement `plan`, `preflight`, and `run`.

