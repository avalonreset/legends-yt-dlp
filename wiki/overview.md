# Overview and Studio Stack Architecture

`legends-youtube` is the deterministic YouTube Data API v3, YouTube Analytics API v2, and YouTube Studio packaging engine for the [CTO Legends](https://cto-legends.com) ecosystem.

## Why Improvised Agent Calls Break YouTube Channels

When an AI coding agent touches a YouTube channel through ad-hoc scripts or generic MCP wrappers, four failure modes routinely occur:

1. **Silent Snippet Field Deletion (`videos.update` Partial-Update Trap):** Calling `PUT https://www.googleapis.com/youtube/v3/videos?part=snippet` replaces the entire mutable `snippet` object. If an agent sends only `title` and `categoryId`, YouTube deletes the video's `description`, `tags`, `defaultLanguage`, and `defaultAudioLanguage`. `legends-youtube` enforces preflight retrieval, merges all untouched `snippet` fields, attaches `If-Match: <etag>`, saves a pre-write rollback snapshot, and verifies post-write readback.
2. **Quota Exhaustion (`search.list` vs Uploads Playlist):** Every Google Cloud project receives a default 10,000-unit daily pool plus a 2026-06-01 granular cap of 100 `search.list` calls/day and 100 `videos.insert` calls/day. Listing a channel via `search.list` burns scarce search calls, whereas reading the channel's `contentDetails.relatedPlaylists.uploads` (`UU...`) via `playlistItems.list` + 50-ID batched `videos.list` costs **2 units per 50 videos**.
3. **Unverified Public Uploads:** Improvised upload scripts often default to `public` or skip thumbnail and chapter validation. `legends-youtube` freezes all four release assets (`video`, `title`, `description`, `thumbnail`) with SHA-256 locks, verifies exact authenticated `channelId`, and uploads strictly as `privacyStatus="private"`.
4. **Guesswork Packaging Changes:** Changing titles or thumbnails without impression and retention baselines hurts click-through rate (CTR) and average percentage viewed (APV). `legends-youtube` benchmarks channel telemetry against dated official YouTube Help thresholds before flagging A/B test candidates.

## Position in the CTO Legends Studio Pipeline

| Stage | Module | Role |
| :--- | :--- | :--- |
| **1. Capture** | `legends-obs` | Record 4K60 local scenes and audio tracks over WebSocket |
| **2. Ingest & Cut** | `legends-yt-dlp` | Download sources, align GPU word timestamps, and cut FFmpeg clips |
| **3. Score** | `legends-stable-audio-3` | Generate local GPU instrumental beds and crossfade mixes |
| **4. Subtitle** | `legends-captions` | Repair technical terms, lock acronym timing, and render subtitles |
| **5. Publish & Grow** | `legends-youtube` | Validate chapters/quizzes/thumbnails, upload private drafts, sweep description CTAs, and audit CTR/retention via Data API v3 + Analytics API v2 |

## Related Runbooks

- [Authentication, Scopes, and Quota Cost Engineering](authentication-and-quotas.md)
- [Lossless Metadata Partial Updates and ETag Concurrency](metadata-and-partial-updates.md)
- [Analytics API v2, Channel Health, and Packaging A/B Tests](analytics-and-packaging-ab.md)
