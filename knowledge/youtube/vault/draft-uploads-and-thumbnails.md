# SHA-256 Frozen Private-Draft Uploads and Thumbnail Guards

`legends-youtube` enforces a two-step **Freeze -> Upload Private Draft** workflow so an agent can never accidentally publish an unreviewed video or upload mismatched assets.

## 1. Thumbnail Validation (`thumbnail-check`)

Before calling `thumbnails.set` (`50` quota units) or freezing a draft package, `legends-youtube thumbnail-check` inspects the image header using pure Python stdlib:

- Verifies valid PNG (`\x89PNG\r\n\x1a\n` + `IHDR`) or JPEG (`\xff\xd8` + `SOF`) structure.
- Enforces YouTube Data API v3's hard **2 MB (`2,097,152` bytes)** custom thumbnail ceiling.
- Checks resolution (`>= 1280x720` recommended) and aspect ratio (`16:9` widescreen or `1:1` square house card).

```bash
legends-youtube thumbnail-check --image thumbnail.png --json
```

## 2. Freezing a Release Package (`draft-freeze`)

`draft-freeze` validates all four local release files (`--video`, `--title-file`, `--description-file`, `--thumbnail`), locks their SHA-256 checksums and byte sizes, and writes a frozen plan with `privacyStatus: "private"`:

```bash
legends-youtube draft-freeze \
  --video master-4k60.mp4 \
  --title-file title.txt \
  --description-file description.txt \
  --thumbnail thumbnail.png \
  --channel-id UC_x5XG1OV2P6uZZ5FSM9Ttw \
  --output frozen-draft.json
```

## 3. Uploading the Private Draft (`draft-upload`)

- Running `draft-upload --plan frozen-draft.json` without `--apply` re-verifies all four SHA-256 file hashes offline and prints the exact `videos.insert` request body.
- Running with `--apply` requires `--confirm-phrase "UPLOAD_PRIVATE_DRAFT <channel_id>"`, verifies via `channels.list(mine=true)` that the OAuth token belongs to the exact target `channelId`, and streams the video in 8 MB resumable chunks (`POST https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status`) strictly as `privacyStatus="private"`.
