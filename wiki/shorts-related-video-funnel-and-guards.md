# Shorts Related-Video Funnel and Isolation Guards

On YouTube Shorts, ordinary URLs in video descriptions and comments are **not clickable** ([YouTube Help 13748639](https://support.google.com/youtube/answer/13748639)).

The **Related video** field displayed directly beneath the channel handle inside the Shorts player is the primary clickable in-player CTA that routes Shorts viewers into a flagship long-form video or conversion asset ([YouTube Help 14075157](https://support.google.com/youtube/answer/14075157)).

---

## 1. Architectural Boundary: Data API v3 vs. YouTube Studio

* **YouTube Data API v3 limitation:** As of 2026, the official `videos` resource (`snippet`, `status`, `contentDetails`) does **not** expose a writable `relatedVideo` field.
* **Consequence:** Reporting on `videos.list` must mark Related video status as `unknown_via_data_api` (`Studio-only`) unless verified by a dedicated Studio inspection receipt.
* **Isolation Contract:** Any automation or operator helper that touches the Studio Related-video field must run under a strict **fail-closed isolation guard** (`related-guard`) that forbids any other mutation (`title`, `description`, `privacyStatus`, `publishAt`, `tags`, `thumbnails`, `delete`).

---

## 2. Fail-Closed Safety Rules for Related-Video Linking

1. **Exact 11-Character Video ID Validation:** Both the source Short `videoId` and the target long-form `targetVideoId` must match `^[A-Za-z0-9_-]{11}$`.
2. **Self-Link Prevention:** `videoId` and `targetVideoId` must never be identical; a Short cannot related-link to itself.
3. **Allowlist-Only Batch Caps:** Never scrape-all or mutate an entire channel blindly. Every Short ID must be explicitly allowlisted (default batch cap `12`, hard cap `20`).
4. **Dual Confirmation Phrase:**
   * **Single Short:** Requires `--confirm` and exact phrase:
     `SET_RELATED <videoId> -> <targetVideoId>`
   * **Allowlisted Batch:** Requires `--confirm` and exact phrase matching the deduplicated count `N`:
     `LINK_RELATED_BATCH <N> -> <targetVideoId>`

---

## 3. Shorts Metadata & Release Workflow

1. **Upload as `private` first:** Stage the Short via `draft-upload` or your scheduler in `private` / `DRAFT` state while metadata is reviewed.
2. **Title Casing & Hygiene:**
   * Keep Shorts titles clean and readable (or follow house lowercase law: all lowercase except standalone pronoun `I` and sacred name `God` / `God's`, with zero hashtags in the title).
3. **Description Structure:**
   * Lead with a sharp quote/gem-cut from real speech.
   * Keep standard brand/community URLs in the description for copy reference, knowing the clickable bridge is the **Related video** link.
4. **Attach Related Video in Studio:** Link the Short to the designated flagship long-form `targetVideoId` before or immediately upon publishing.

---

## 4. CLI Usage

```bash
# Dry-run validation and confirmation-phrase generation for a batch of Shorts
legends-youtube related-guard \
  --video-ids VidShrt0001,VidShrt0002,VidShrt0003,VidShrt0004 \
  --target VidLong0001

# Verify an operator confirmation phrase before executing a Studio batch
legends-youtube related-guard \
  --video-ids VidShrt0001,VidShrt0002,VidShrt0003,VidShrt0004 \
  --target VidLong0001 \
  --confirm \
  --phrase "LINK_RELATED_BATCH 4 -> VidLong0001"
```
