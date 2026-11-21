# Zero-Quota Anonymous Public Video Readback

When operating at scale or when Google Cloud OAuth tokens are unavailable or expired (for example, the 7-day refresh-token expiry on Google Cloud OAuth apps in `Testing` status), you can still verify whether any YouTube video is publicly live, playable, and serving expected metadata for **0 API quota units and 0 credentials**.

---

## 1. How `public-readback` Works

Instead of spending `videos.list` quota or requiring an OAuth token, `legends-youtube public-readback` performs a two-part anonymous read-only probe over HTTPS:

1. **Anonymous Watch Page Probe (`https://www.youtube.com/watch?v=<id>&hl=en`):**
   * Extracts the embedded `ytInitialPlayerResponse` JSON object using balanced brace parsing.
   * Reads `playabilityStatus.status` (must be `"OK"` for public playback), `videoDetails` (`videoId`, `title`, `shortDescription`, `channelId`, `author`, `lengthSeconds`, `isLiveContent`), and `microformat.playerMicroformatRenderer` (`publishDate`, `embed.iframeUrl`).
2. **Public oEmbed Probe (`https://www.youtube.com/oembed?url=...&format=json`):**
   * Confirms `HTTP 200` on YouTube's public oEmbed endpoint and cross-checks `title` and `author_name`.

---

## 2. When to Use `public-readback` vs. `videos.list`

| Scenario | Recommended Tool | Quota Cost | Auth Required |
|---|---|---|---|
| Verify a newly published video is publicly playable & embeddable | `public-readback` | **0 units** | None |
| Verify public title, description, duration, and channel owner | `public-readback` | **0 units** | None |
| Inspect private/unlisted drafts, ETag, `categoryId`, or `tags` | `channel-inventory` / `metadata-plan` | **1 unit** | OAuth / API Key |
| Pre-flight before `videos.update` | `metadata-plan` | **1 unit** | OAuth (`youtube.force-ssl`) |

---

## 3. CLI Usage

```bash
legends-youtube public-readback --video-id dQw4w9WgXcQ
```
