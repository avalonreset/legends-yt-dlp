# Batch Catalog Operating Model

Large archives should be organized as batches, not ad hoc commands.

## Batch Shape

Each batch folder contains:

- `manifest.json`: optional rights note, source URLs, status, paths, policy flags.
- `urls.txt`: one URL per line for yt-dlp.
- `yt-dlp.conf`: generated conservative downloader config.
- `archive.txt`: yt-dlp download archive for idempotent resumes.
- `downloads/`: output folder.
- `tmp/`: temporary files.

Generated batches live under ignored `batches/`.

## Planning Rules

- Keep rights notes/evidence optional; the real-run legal-use notice is the default legal reminder.
- Prefer one channel/playlist/source collection per batch.
- For very large jobs, split by source, date range, or logical collection.
- Keep YouTube execution sequential by default.
- Use `catalog` before creating new work so duplicate batches are visible.

## Parallelism

Default: one active YouTube batch at a time.

Parallelism can multiply source-side rate limits and failure modes. Do not parallelize YouTube downloads unless a future policy explicitly allows a bounded mode after testing.

Safe ways to scale first:

- use yt-dlp download archives
- resume incomplete batches
- split catalogs into named batches
- run conservative sleep/retry settings
- inspect reports before starting the next batch

## Error Handling

Classify errors before action:

- VPN disconnected, DNS failure, transient tunnel loss: reconnect Mullvad, rerun preflight, retry.
- Item unavailable or removed: mark failed/skipped, continue if policy allows.
- Captcha, login challenge, explicit block, repeated rate limit: pause and report.

Do not change relay/IP to keep going through source-side block signals.
