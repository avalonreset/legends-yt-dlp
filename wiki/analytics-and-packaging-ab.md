# Analytics API v2, Channel Health, and Packaging A/B Tests

`legends-youtube` combines live queries to the **YouTube Analytics API v2** (`GET https://youtubeanalytics.googleapis.com/v2/reports`) and offline YouTube Studio exports with sourced benchmarks from Google for Developers and YouTube Help.

## Sourced Reference Benchmarks

Every diagnostic flag in `legends-youtube analytics-audit` and `legends-youtube packaging-audit` traces to a dated primary source:

| Metric | Sourced Threshold | Official Citation | Diagnostic Action |
| :--- | :--- | :--- | :--- |
| **Impressions CTR** | `2.0%` to `10.0%` (half of all channels) | YouTube Help `7628154` | Flag channel or long-form videos below `2.0%` CTR for title/thumbnail redesign |
| **Average Percentage Viewed (APV)** | `>= 50.0%` target (`50%+` past 0:30 intro) | YouTube Help `12942217` / `12340300` | Flag below-50% APV videos for first-30-second hook and pacing review |
| **Mid-Roll Ad Eligibility** | `>= 8:00` (`480 seconds`) | YouTube Help `6175006` | Flag long-form uploads under 480 seconds that forfeit mid-roll ad inventory |
| **Test & Compare A/B Winner** | **Watch-time share** (not raw CTR) | YouTube Help `13861714` | Rank long-form videos with `>= 1,000` impressions below median CTR for Studio A/B testing |

## Running an Offline or Live Scorecard

```bash
# Offline YouTube Studio export audit + Markdown scorecard
legends-youtube analytics-audit --export studio-export.json --channel-name "Example Channel" --markdown --output scorecard.json

# Focused Title/Thumbnail A/B candidate ranking
legends-youtube packaging-audit --export studio-export.json --min-impressions 1000 --json

# Live YouTube Analytics API v2 report (requires yt-analytics.readonly OAuth scope)
legends-youtube analytics-audit --live --start-date 2026-01-01 --end-date 2026-11-09 --json
```

## Packaging-First Workflow

1. **Title + Thumbnail as One Unit:** Viewers process the thumbnail and title together in under one second. Never repeat the exact same phrase in both; use the thumbnail to establish visual tension or stakes and the title to supply the concrete mechanism or curiosity gap.
2. **Prioritize High-Impression Below-Median Videos:** Changing packaging on a video with 50,000 impressions and a 2.8% CTR (when channel median is 5.2%) yields immediate click volume without filming a new video.
3. **Evaluate by Watch-Time Share:** High-CTR clickbait that collapses retention in the first 30 seconds stalls recommendation distribution. Always let watch-time share decide Test & Compare experiments.
