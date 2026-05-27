---
type: module
status: planned
created: 2026-05-27
updated: 2026-05-27
tags: [module, policy, compliance]
---

# Policy Engine

## Purpose

Prevent the tool from running batches that do not have a documented lawful basis or that hit stop conditions.

## Required Inputs

- Target URL or batch file.
- Rights basis.
- Operator identity or profile.
- Output path.
- Source-specific notes.

## Stop Conditions

- No rights basis.
- Account login challenge.
- Captcha or bot challenge.
- Explicit platform block.
- Repeated rate-limit response.
- DRM, paywall, or access-control signal.
- VPN state unsafe or ambiguous.

## Output

Return a structured allow/block decision with reasons, not a boolean.

