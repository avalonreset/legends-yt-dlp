# Authentication, Scopes, and Quota Cost Engineering

Every request to the YouTube Data API v3 (`https://www.googleapis.com/youtube/v3`) and YouTube Analytics API v2 (`https://youtubeanalytics.googleapis.com/v2`) requires explicit Google Cloud credentials.

## Credential Modes and Least-Privilege Scopes

| Mode | Environment Variables | Permitted Operations |
| :--- | :--- | :--- |
| **Public Read-Only (`API Key`)** | `YOUTUBE_API_KEY` | `channel-inventory`, `video-inspect`, and `links-audit` on public channels/videos |
| **Account Read-Only (`OAuth 2.0`)** | `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` (or `YOUTUBE_ACCESS_TOKEN`) | Private/unlisted video inspection (`mine=true`) and `analytics-audit --live` |
| **Guarded Write (`OAuth 2.0`)** | Same OAuth vars with `youtube.force-ssl` or `youtube.upload` scope | `metadata-apply` and `draft-upload` (requires `--confirm` / `--confirm-phrase`) |

### Official OAuth Scopes

- `https://www.googleapis.com/auth/youtube.readonly`: Read-only access to the authenticated user's channel, playlists, and videos.
- `https://www.googleapis.com/auth/youtube.force-ssl`: Narrowest scope accepted by `videos.update` and `thumbnails.set`.
- `https://www.googleapis.com/auth/youtube.upload`: Scope for `videos.insert` resumable uploads.
- `https://www.googleapis.com/auth/yt-analytics.readonly`: Read-only access to non-monetary YouTube Analytics API v2 reports.
- `https://www.googleapis.com/auth/yt-analytics-monetary.readonly`: Read-only access to revenue and CPM metrics (`estimatedRevenue`, `cpm`).

Never read local browser profile folders, cookie stores, or system credential stores. Supply credentials strictly via environment variables, `--dotenv <path>`, or `--token-file <path>`.

## YouTube Data API v3 Quota Cost Schedule

Every Google Cloud project starts with **10,000 units per day** (resets at midnight Pacific time), plus the **2026-06-01 granular daily caps** of **100 `search.list` calls/day** and **100 `videos.insert` calls/day**.

| API Method | Quota Cost (Units) | Notes |
| :--- | :--- | :--- |
| `channels.list` | `1` | Used to resolve `relatedPlaylists.uploads` (`UU...`) |
| `playlistItems.list` | `1` | Fetches up to 50 uploaded video IDs per page |
| `videos.list` | `1` | Batch-fetches up to 50 video IDs per call (`id=v1,v2,...`) |
| `commentThreads.list` | `1` | Fetches up to 100 top-level comments per page |
| `search.list` | `1` (100/day cap) | Capped at 100 calls/day; never use for channel inventory |
| `videos.update` | `50` | Guarded metadata update (`51` units including post-write readback) |
| `thumbnails.set` | `50` | Custom PNG/JPEG thumbnail upload (`<= 2 MB`) |
| `videos.insert` | `100` (100/day cap) | Reduced from 1,600 units in 2025-12; capped at 100 uploads/day |
| `captions.insert` | `400` | New caption track upload |
| `captions.update` | `450` | Existing caption track update |

## Pre-Calculating Batch Waves

Before running a channel-wide metadata or thumbnail batch, run `quota-plan`:

```bash
legends-youtube quota-plan --inventory-videos 120 --metadata-updates 120 --json
```

With a 500-unit safety reserve (`9,500` usable units/day), `legends-youtube` caps guarded metadata updates at **186 videos per day** (`51` units/video) and automatically splits larger channels into multi-day waves.
