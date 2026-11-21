# Lossless Metadata Partial Updates and ETag Concurrency

Updating video titles or descriptions via `PUT https://www.googleapis.com/youtube/v3/videos?part=snippet` is the highest-risk routine operation in the YouTube Data API v3.

## The `videos.update` Partial-Update Trap

Per Google's official `videos.update` documentation:
1. `snippet.title` and `snippet.categoryId` are mandatory whenever `part=snippet` is updated.
2. Any mutable property inside `snippet` (`description`, `tags`, `defaultLanguage`, `defaultAudioLanguage`) that is omitted from the request body is **deleted** by YouTube.
3. Sending `part=snippet,status` when only changing a title or description risks mutating `privacyStatus`, `publishAt`, or `selfDeclaredMadeForKids`.

## The 6-Layer `legends-youtube` Safety Contract

`legends-youtube metadata-plan` and `legends-youtube metadata-apply` enforce six deterministic safeguards:

1. **Allowlist & Schema Lock:** Every target `videoId` must appear in `allowedVideoIds`. Only `title` (`1..100` chars) and `description` (`<= 5,000` chars) are accepted in `updates[]`. Unknown fields fail validation immediately.
2. **SHA-256 Plan Hash (`--expected-plan-sha256`):** `metadata-plan` computes a canonical SHA-256 digest over the normalized plan. `metadata-apply` refuses execution if the plan file was modified after review.
3. **Preflight ETag & Drift Check:** Before the first write, `metadata-apply` fetches all target videos via `videos.list(part="id,snippet,status")`. If any video's live `title` or `description` differs from `expectedCurrent`, the entire batch aborts before any mutation occurs.
4. **Lossless Snippet Field Merge:** For each video, `build_merged_snippet()` copies `title`, `description`, `tags`, `categoryId`, `defaultLanguage`, and `defaultAudioLanguage` from the live preflight resource, overlaying only the explicitly planned `title` and/or `description` change.
5. **Optimistic Concurrency (`If-Match`):** Every `PUT /youtube/v3/videos?part=snippet` request carries `If-Match: <preflight_etag>` so concurrent edits in YouTube Studio cannot be silently overwritten.
6. **Immediate Readback Verification:** After each write, the video is read back via `videos.list` to verify that every preserved and updated field matches expectations and `privacyStatus` did not change.

## Declarative Plan Format

```json
{
  "schemaVersion": 1,
  "allowedVideoIds": ["dQw4w9WgXcQ"],
  "updates": [
    {
      "videoId": "dQw4w9WgXcQ",
      "expectedCurrent": {
        "title": "Old Video Title"
      },
      "title": "New Video Title"
    }
  ]
}
```
