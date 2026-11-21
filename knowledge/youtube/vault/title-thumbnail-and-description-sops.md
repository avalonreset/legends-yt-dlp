# Title, Thumbnail, and Description Packaging SOP

Operational rules for packaging long-form YouTube videos and Shorts so titles, thumbnails, and descriptions work together without redundancy or metadata drift.

---

## 1. Final-Cut Verification Rule

* **Treat the newest final render as authoritative:** Never reuse chapter timestamps, claims, or metadata from an earlier rough cut without verifying against the final video file and transcript.
* **Separate core promise from incidental mentions:** If a clip briefly mentions a secondary tool or model that is not the video's main thesis, keep it in the links or chapters rather than diluting the title.

---

## 2. Title Engineering Rules

1. **Lead with human, high-intent phrasing:** Combine the specific project/model/system name with the broader measurable category in a single clear promise.
   * *Example:* `Stable Audio 3 Is the Local AI Music Generator I Wanted`
2. **Never overclaim:** Do not call a benchmark or showcase a "step-by-step tutorial" unless the video actually teaches the installation and workflow end to end.
3. **Optional House Lowercase Law (`house-style-lint`):**
   * For channels or Shorts series that enforce lowercase aesthetic discipline: lowercase the entire title except standalone first-person pronoun `I` and standalone sacred name `God` (`God's`), with zero hashtags in the title.

---

## 3. Thumbnail Engineering Rules

1. **2 to 5 Words Maximum:** Thumbnail copy should be `2` to `5` high-contrast words.
2. **Complementary Split (Never Repeat the Title):**
   * Let the **Title** carry the exact model/category SEO phrase.
   * Let the **Thumbnail** sell the emotional reason to click or the curiosity/proof gap (e.g., Title: `I Built a System to Find My Next YouTube Video` -> Thumbnail: `STOP GUESSING`).
3. **Mobile Legibility First:** Avoid tiny UI chrome unless cropped and magnified so it reads clearly on a mobile feed.
4. **Hard Technical Pre-Flight (`thumbnail-check`):**
   * Format: PNG or JPEG (`16:9`, ideally `1280x720` or `1920x1080`).
   * File size: Strictly `<= 2,097,152` bytes (`2 MB`) for `thumbnails.set` API acceptance.

---

## 4. Description Engineering Rules

1. **The First 2 Lines (Above the Fold):**
   * Line 1: Say clearly what the video is.
   * Line 2: Say why the viewer should care right now.
   * Never waste the first 150 characters on social links, sponsor boilerplate, or hashtags.
2. **Body & Links:**
   * Follow with official project/documentation links and the standard community/CTA block.
3. **Chapters (`chapters-lint`):**
   * First chapter must start at `00:00`.
   * At least `3` chapters in strictly ascending order.
   * Every chapter interval must be `>= 10` seconds.
