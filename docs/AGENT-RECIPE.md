# Agent Recipe: `legends-youtube` (Unified Studio API + `legends-yt-dlp` Media Engine)

Use this recipe when the user asks to inspect or manage a YouTube channel, audit video metadata or description links, plan YouTube Data API v3 quota usage, analyze YouTube Studio or Analytics API v2 CTR/retention metrics, score video ideas before recording, validate video chapters or Studio quizzes, check custom thumbnails, upload a private draft, probe or archive videos/channels via `yt-dlp`, verify media streams with `ffprobe`, transcribe local media into GPU word ledgers, cut FFmpeg clips, or attach the YouTube knowledge pack to a `legends-empire` vault.

## 1. Readiness, Credential Check & Resource Paths (`doctor`, `auth-status`, `knowledge-pack`, `paths`, `resources`)

Always start with read-only readiness across both surfaces:

```bash
legends-youtube doctor --json
legends-youtube auth-status --json
legends-youtube knowledge-pack --json
legends-youtube paths --json
legends-youtube resources --json
legends-yt-dlp doctor --offline
```

When the user requests a live YouTube Data API v3 channel check, pass `--live` (and `--expected-channel-id UC...` when targeting a specific owned channel):

```bash
legends-youtube doctor --live --expected-channel-id UC_x5XG1OV2P6uZZ5FSM9Ttw --json
```

## 2. Quota Cost Calculation Before Any API Batch (`quota-plan`)

Before executing channel-wide inventory or write batches, calculate exact unit usage against the 10,000-unit daily pool and 2026-06-01 granular caps (`100` `search.list`/day, `100` `videos.insert`/day):

```bash
legends-youtube quota-plan --inventory-videos 100 --metadata-updates 50 --json
```

## 3. Low-Quota Channel Inventory, Video Inspection & Zero-Quota Radar (`channel-inventory`, `video-inspect`, `public-readback`, `channel-outliers`)

Always inventory a channel via its `relatedPlaylists.uploads` playlist (`2` units per 50 videos), never via `search.list`:

```bash
legends-youtube channel-inventory --mine --output channel-inventory.json
legends-youtube video-inspect --video-ids dQw4w9WgXcQ,VidLong0001 --json

# Zero-quota, zero-credential public video verification and RSS outlier radar
legends-youtube public-readback --video-id dQw4w9WgXcQ --json
legends-youtube channel-outliers --channel-id UC_x5XG1OV2P6uZZ5FSM9Ttw --threshold 2.0 --json
```

## 4. Pre-Recording Idea Radar, Transcript Packaging & Retention X-Ray (`score-idea`, `transcript-package`, `retention-xray`)

```bash
# Score a video candidate before recording (Perfect Video Score + Goldilocks timing + 9-point fit filter)
legends-youtube score-idea --title "I Built an Agentic System to Score YouTube Ideas" --days-since-catalyst 14 --fit-checks 8 --json

# Compile a transcript (.json/.srt/.vtt/.txt) into validated chapters, Shorts gem-cuts, and a Release Workbench
legends-youtube transcript-package --transcript transcript.json --title "My Video Title" --json

# Correlate a retention curve (elapsedVideoTimeRatio) with exact spoken sentences in the transcript
legends-youtube retention-xray --transcript transcript.json --retention-file retention.json --json
```

## 5. Preview-First `yt-dlp` Media Probing, Anonymous Capture & GPU Word-Ledger Clips (`legends-yt-dlp` / `legends-youtube yt-dlp`)

You can invoke the media capture and clip engine directly via `legends-yt-dlp` (or `legends-ytdlp`) or via subcommand forwarding on `legends-youtube` (`legends-youtube yt-dlp <args>`, `legends-youtube archive <args>`, `legends-youtube pull <args>`, `legends-youtube transcribe <args>`, `legends-youtube clips <args>`):

```bash
# 1. Probe a channel or playlist into a reviewable items.jsonl ledger without downloading media
legends-yt-dlp inventory "https://www.youtube.com/@CHANNEL" --name "channel-review" --max-items 25
legends-yt-dlp ledger "batches/<batch-id>/manifest.json"

# 2. Plan a bounded batch from direct URLs or a URL file
legends-yt-dlp plan --from-file "./examples/urls.txt" --name "reference-clips" --folder-policy batch

# 3. Run SHA-256 config preflight, dry-run simulation, approved capture (--yes), and ffprobe stream verification
legends-yt-dlp preflight "batches/<batch-id>/manifest.json"
legends-yt-dlp run "batches/<batch-id>/manifest.json" --dry-run
legends-yt-dlp run "batches/<batch-id>/manifest.json" --yes
legends-yt-dlp verify "batches/<batch-id>/manifest.json"
legends-yt-dlp ledger "batches/<batch-id>/manifest.json" --refresh

# 4. Optional post-capture GPU word ledgers, phrase search, FFmpeg clip plans, and Obsidian vault export
legends-yt-dlp intelligence init "batches/<batch-id>/manifest.json"
legends-yt-dlp intelligence transcribe "batches/<batch-id>/manifest.json" --all --model auto
legends-yt-dlp intelligence search "batches/<batch-id>/manifest.json" "agentic workflow"
legends-yt-dlp intelligence clips plan "batches/<batch-id>/manifest.json" --query "agentic workflow"
legends-yt-dlp intelligence clips render "batches/<batch-id>/intelligence/clips/<slug>/clip-plan.json" --yes
legends-yt-dlp intelligence vault build "batches/<batch-id>/manifest.json"
```

See [docs/OPERATOR-ROUTING.md](OPERATOR-ROUTING.md) and [docs/CLI.md](CLI.md) for the complete `legends-yt-dlp` flag matrix and opt-in `--with-vpn` Mullvad controls.

## 6. Lossless Metadata Partial Updates (`metadata-plan`, `metadata-apply`)

Never send raw `videos.update(part="snippet")` requests without merging existing `snippet` fields (`title`, `description`, `tags`, `categoryId`, `defaultLanguage`, `defaultAudioLanguage`), or YouTube will delete omitted fields.

1. Preview and lock the plan (`0` mutations):
   ```bash
   legends-youtube metadata-plan --plan update-plan.json --output preview.json
   ```
2. Apply only after explicit user confirmation with `--expected-plan-sha256` and `--confirm`:
   ```bash
   legends-youtube metadata-apply \
     --plan update-plan.json \
     --expected-plan-sha256 <sha256_from_preview> \
     --confirm \
     --output metadata-receipt.json
   ```

## 7. Description Link Audits, CTA Migrations, Playlists & Shorts Funnel (`links-audit`, `links-migrate`, `playlists-audit`, `funnel-audit`, `comments-triage`)

```bash
legends-youtube links-audit \
  --inventory channel-inventory.json \
  --canonical-cta "https://example.com" \
  --probe-https \
  --json

legends-youtube links-migrate \
  --inventory channel-inventory.json \
  --find-url "https://legacy-example.com" \
  --replace-url "https://example.com" \
  --output link-migration-plan.json

legends-youtube playlists-audit \
  --inventory channel-inventory.json \
  --playlists playlists.json \
  --json

legends-youtube funnel-audit \
  --inventory channel-inventory.json \
  --canonical-cta "https://example.com" \
  --json

legends-youtube comments-triage \
  --from-json comments.json \
  --json
```

## 8. Sourced Channel Health Scorecard & Packaging A/B Tests (`analytics-audit`, `packaging-audit`)

```bash
# Offline Studio export JSON
legends-youtube analytics-audit --export studio-export.json --channel-name "Channel" --markdown --json
legends-youtube packaging-audit --export studio-export.json --min-impressions 1000 --json

# Live YouTube Analytics API v2
legends-youtube analytics-audit --live --start-date 2026-01-01 --end-date 2026-03-31 --json
```

## 9. Chapters, Studio Video Quizzes, Shorts Related-Video Guards & Thumbnail Validation (`chapters-lint`, `quiz-lint`, `thumbnail-check`, `related-guard`, `house-style-lint`)

```bash
legends-youtube chapters-lint --description-file description.txt --duration-seconds 1800 --json
legends-youtube quiz-lint --quizzes-file quizzes.json --duration-seconds 1800 --json
legends-youtube thumbnail-check --image thumbnail.png --json
legends-youtube related-guard --video-ids VidShrt0001,VidShrt0002 --target VidLong0001 --json
legends-youtube house-style-lint --title "I made God's grace visible in ai" --json
```

## 10. SHA-256 Frozen Private-Draft Upload (`draft-freeze`, `draft-upload`)

Uploads are strictly locked to `privacyStatus="private"`:

```bash
legends-youtube draft-freeze \
  --video video.mp4 \
  --title-file title.txt \
  --description-file description.txt \
  --thumbnail thumbnail.png \
  --channel-id UC_x5XG1OV2P6uZZ5FSM9Ttw \
  --output frozen-draft.json

# Dry-run hash verification
legends-youtube draft-upload --plan frozen-draft.json --json

# Confirmed private-draft upload (requires explicit user approval)
legends-youtube draft-upload \
  --plan frozen-draft.json \
  --apply \
  --confirm-phrase "UPLOAD_PRIVATE_DRAFT UC_x5XG1OV2P6uZZ5FSM9Ttw" \
  --output upload-receipt.json
```

## 11. EDR and Security Guardrails (Mandatory)

1. Never spawn background shells, hidden console windows, or execution-policy bypass shell wrappers.
2. Never read local browser profile databases, DPAPI stores, cookie stores, or system credential stores outside explicit environment variables (`YOUTUBE_API_KEY`, `YOUTUBE_ACCESS_TOKEN`, `YOUTUBE_REFRESH_TOKEN`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`), `--dotenv`, or `--token-file`. Every `yt-dlp.conf` enforces `--ignore-config`, `--no-cookies`, and `--no-cookies-from-browser`.
3. Never rotate VPN relays, switch accounts, or automate challenge solvers to continue through HTTP 429 throttles, captchas, login walls, or platform blocks.
4. Never print raw OAuth tokens, client secrets, API keys, or Mullvad account numbers to stdout, logs, or Markdown receipts.
