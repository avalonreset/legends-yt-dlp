# Troubleshooting and Error Recovery

## Common API and Validation Errors

### 1. `403 quotaExceeded`
- **Cause:** The Google Cloud project exhausted its 10,000-unit daily pool or hit the 100/day granular cap on `search.list` or `videos.insert`.
- **Resolution:** Stop retrying immediately (YouTube does not offer pay-as-you-go overage; quota resets at midnight Pacific time). Run `legends-youtube quota-plan` to split remaining updates into daily waves of `<= 186` guarded `videos.update` calls/day, and always use `channel-inventory` (`playlistItems.list`, 2 units per 50 videos) instead of `search.list`.

### 2. `412 Precondition Failed` or `Preflight drift detected`
- **Cause:** A video's live `title`, `description`, or `etag` changed in YouTube Studio after `metadata-plan` or `links-migrate` generated the plan.
- **Resolution:** Re-run `channel-inventory` or `video-inspect`, regenerate the plan so `expectedCurrent` reflects the latest state, review the diff, and apply with the new `plan_sha256`.

### 3. `403 insufficientPermissions` on `metadata-apply` or `analytics-audit --live`
- **Cause:** The OAuth token was authorized only with `youtube.readonly` and lacks `youtube.force-ssl` (for `videos.update`) or `yt-analytics.readonly` (for Analytics API v2).
- **Resolution:** Check granted scopes with `legends-youtube auth-status --json` and re-authorize the desktop OAuth token with the required scope.

### 4. Chapters Not Appearing on YouTube Scrub Bar
- **Cause:** First timestamp is not `00:00`, fewer than 3 chapters exist, or a chapter duration is under 10 seconds.
- **Resolution:** Run `legends-youtube chapters-lint --description-file description.txt --duration-seconds <sec>` and fix all reported errors.

### 5. YouTube Studio `Save` Button Disabled in Quizzes Modal
- **Cause:** An answer choice exceeds 80 characters (`QUIZ_OPTION_TEXT_TOO_LONG`), an explanation exceeds 500 characters (`QUIZ_EXPLANATION_TEXT_TOO_LONG`), or a timestamp is not in 8-character `MM:SS:FF` format.
- **Resolution:** Run `legends-youtube quiz-lint --quizzes-file quizzes.json` before entering quizzes in Studio.
