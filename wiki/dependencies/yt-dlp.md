---
type: dependency
status: planned
created: 2026-05-27
updated: 2026-05-27
source_url: "https://github.com/yt-dlp/yt-dlp"
tags: [dependency, yt-dlp]
---

# yt-dlp

yt-dlp is the downloader engine. The Slayer app should call it as a child process and manage configuration, state, policy, and reporting around it.

## Required Capabilities

- URL and batch input.
- Download archive files.
- Output templates.
- Sleep and retry controls.
- Metadata/thumbnail/subtitle options, behind explicit profiles.

## Linked Notes

- [[yt-dlp Operational Notes 2026-05-27]]
- [[YT DLP Runner]]

## Implementation Risks

- Extractor behavior changes frequently.
- YouTube-specific failures may require updates to yt-dlp itself.
- Error output classification should be tested against fixtures, not guessed from one run.

