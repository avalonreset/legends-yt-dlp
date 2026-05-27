---
type: raw-brief
status: captured
created: 2026-05-27
updated: 2026-05-27
tags: [idea, raw-brief]
---

# User Brief - Legends YT-DLP Slayer

The project idea is a Windows-first app or skill suite that coordinates yt-dlp downloads with Mullvad VPN state. The user wants a tool that can archive large YouTube channels without exposing the operator's regular IP address, while making the workflow systematic enough for community use.

## Captured Product Intent

- Make yt-dlp easier and safer for repeated archival jobs.
- Require Mullvad VPN connectivity before downloads run.
- Provide a CLI-style control plane for Windows.
- Track jobs so large channel archives can resume and finish cleanly.
- Package the result for the Legends / Skool community.

## Safety Reframe

The implementation vault keeps the useful parts of the idea: VPN privacy, fail-closed networking, job state, resumability, and operator ergonomics. It rejects the unsafe part: rotating VPN endpoints to bypass YouTube throttling, account controls, or source blocks.

