---
type: dependency
status: planned
created: 2026-05-27
updated: 2026-05-27
tags: [dependency, ffmpeg]
---

# ffmpeg

ffmpeg is required for merging separate video/audio streams and for optional media post-processing.

## MVP Role

- Verify ffmpeg is installed and visible to yt-dlp.
- Report missing ffmpeg as a setup issue.
- Avoid custom transcoding in the first MVP unless a profile explicitly asks for it.

## Open Question

Should the installer bundle ffmpeg or ask users to install it separately?

