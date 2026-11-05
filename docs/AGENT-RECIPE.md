# Legends YT-DLP Agent Recipe

Deterministic operator procedure for `legends-yt-dlp` (`v0.1.4`). Loaded by `cto-legends handoff legends-yt-dlp`. Do not register a separate per-module skill.

## 1. Readiness & Diagnostics

Always verify package readiness before planning or running a batch:

```bash
legends-yt-dlp doctor --offline
```

- `legends-yt-dlp doctor` (and `legends-yt-dlp doctor --offline`) emits JSON diagnostics and exits `0` when the Python control plane is healthy, reporting external `yt-dlp` and `ffmpeg` binaries as optional runtime tools until a live batch requires them.
- Pass `--require-tools` to require `yt-dlp` and `ffmpeg` to be installed and fresh (`<= 90` days for managed `yt-dlp.exe`).
- Pass `--production` (or `--require-connected`) only when the operator requests VPN-guarded execution (`--with-vpn`).

## 2. Complete CLI Command Surface

| Command | Purpose | Mutates Local State / Network |
| --- | --- | --- |
| `legends-yt-dlp doctor [--offline] [--require-tools] [--require-connected] [--production] [--json] [--text]` | Inspect package health, optional `yt-dlp`/`ffmpeg` binaries, and opt-in Mullvad posture | Read-only |
| `legends-yt-dlp onboard [--basic] [--with-vpn] [--strict] [--json]` | Print non-mutating first-run readiness, interview checklist, and next commands | Read-only |
| `legends-yt-dlp yt-dlp install` | Download official Windows `yt-dlp.exe` and verify against upstream `SHA2-256SUMS` | Writes `.local/bin/yt-dlp.exe` |
| `legends-yt-dlp yt-dlp update` | Refresh managed `yt-dlp.exe` and verify SHA-256 checksum | Writes `.local/bin/yt-dlp.exe` |
| `legends-yt-dlp yt-dlp version` | Print discovered `yt-dlp` version and binary path | Read-only |
| `legends-yt-dlp yt-dlp check` | Compare managed `yt-dlp` version against upstream stable release | Network read-only |
| `legends-yt-dlp plan [urls...] [--from-file <file>] [--name <name>] [--output <dir>] [--folder-policy auto\|batch\|by-uploader\|flat] [--rights <note>] [--rights-file <path>] [--max-height <px>] [--max-downloads <n>] [--max-filesize <size>] [--with-vpn]` | Create a batch manifest, `urls.txt`, `items.jsonl`, and anonymous `yt-dlp.conf` | Writes `batches/<id>/` |
| `legends-yt-dlp inventory <source_url> [--name <name>] [--output <dir>] [--max-items <n>] [--live-status <state>] [--folder-policy auto\|batch\|by-uploader\|flat] [--rights <note>] [--rights-file <path>] [--with-vpn]` | Expand a channel or playlist into a reviewable `items.jsonl` ledger without downloading media | Writes `batches/<id>/` |
| `legends-yt-dlp smoke plan [--url <url>] [--count <n>] [--name <name>] [--output <dir>] [--max-height 360] [--max-filesize 75M]` | Create a bounded smoke-validation batch | Writes `batches/<id>/` |
| `legends-yt-dlp catalog` | List local batch manifests under `batches/` | Read-only |
| `legends-yt-dlp ledger <manifest.json> [--refresh] [--status <status>] [--limit <n>] [--json]` | Summarize, filter, or refresh per-item ledger state from archives and media files | Read-only (`--refresh` updates `items.jsonl`) |
| `legends-yt-dlp preflight <manifest.json> [--with-vpn]` | Validate manifest, anonymous cookie/auth policy, output paths, and tool readiness | Read-only |
| `legends-yt-dlp run <manifest.json> --dry-run [--show-output]` | Simulate `yt-dlp` execution without downloading media | Writes run report |
| `legends-yt-dlp run <manifest.json> --yes [--with-vpn] [--bulk] [--keep-vpn] [--no-recover-vpn]` | Execute approved batch download after passing preflight | Downloads media + writes report |
| `legends-yt-dlp verify <manifest.json> [--allow-empty] [--no-probe]` | Verify archive entries, info JSON sidecars, ledger media files, and `ffprobe` streams | Updates ledger + verifies media |
| `legends-yt-dlp setup production [--relay-location <loc...>] [--no-connect]` | Configure opt-in Mullvad production posture (Lockdown, auto-connect, LAN block, split-tunnel off) | Mutates Mullvad settings |
| `legends-yt-dlp mullvad status\|login\|connect\|disconnect\|shutdown\|disconnect-test\|recover\|lockdown\|inspect\|account\|version\|auto-connect\|lan\|relay\|dns\|tunnel\|split-tunnel\|anti-censorship\|api-access\|raw` | Operate the official Mullvad CLI when VPN-guarded mode is requested | Mutates Mullvad state |
| `legends-yt-dlp intelligence init <manifest.json>` | Initialize `intelligence/` workspace under a batch | Writes `intelligence/manifest.json` |
| `legends-yt-dlp intelligence doctor <manifest.json> [--require-crispasr] [--require-gpu]` | Check local `ffmpeg` and CrispASR backend readiness (including compiled GPU backends) | Read-only |
| `legends-yt-dlp intelligence status <manifest.json> [--json]` | Summarize transcripts, word ledgers, searches, and clip plans for a batch | Read-only |
| `legends-yt-dlp intelligence transcribe <manifest.json> (--media <file> \| --all) [--model auto] [--gpu-backend <backend>] [--require-gpu] [--no-gpu]` | Transcribe local verified media via external CrispASR Parakeet CLI into word ledgers | Writes `intelligence/words/*.words.jsonl` |
| `legends-yt-dlp intelligence import-crispasr <manifest.json> --input <json> [--video-id <id>] [--media-path <path>]` | Import CrispASR `-ojf` JSON into normalized word ledgers | Writes `intelligence/words/*.words.jsonl` |
| `legends-yt-dlp intelligence ingest-words <manifest.json> --input <jsonl_or_json> [--video-id <id>]` | Import timestamped word JSONL/JSON into normalized word ledgers | Writes `intelligence/words/*.words.jsonl` |
| `legends-yt-dlp intelligence align nfa <manifest.json> [--media <file>] [--prepare-only] [--import-ctm <ctm>]` | Prepare NVIDIA NeMo Forced Aligner manifests or import refined word CTM timings | Writes `intelligence/alignments/nfa/` |
| `legends-yt-dlp intelligence search <manifest.json> "<query>" [--pad-before 0.5] [--pad-after 0.75] [--json]` | Exact contiguous token search across batch word ledgers | Writes `intelligence/searches/*.matches.jsonl` |
| `legends-yt-dlp intelligence clips plan <manifest.json> --query "<query>" [--json]` | Generate reviewable FFmpeg clip plan JSON from word-ledger matches | Writes `intelligence/clips/*/clip-plan.json` |
| `legends-yt-dlp intelligence clips render <clip-plan.json> --yes` | Render individual clips and montage via local `ffmpeg` | Writes clip MP4s |
| `legends-yt-dlp intelligence vault build <manifest.json>` | Export Obsidian-compatible Markdown transcript pages | Writes `intelligence/vault/*.md` |

## 3. Standard Operating Procedure

1. **Readiness check**: Run `legends-yt-dlp doctor --offline` (and `legends-yt-dlp doctor --require-tools` before live downloads).
2. **Inventory or plan**:
   - For single or curated URLs: `legends-yt-dlp plan <urls...> --name <slug> --folder-policy batch`.
   - For channels or playlists: `legends-yt-dlp inventory <url> --name <slug>` and review `legends-yt-dlp ledger <manifest.json>`.
3. **Preflight and dry-run**:
   - Run `legends-yt-dlp preflight <manifest.json>`.
   - Run `legends-yt-dlp run <manifest.json> --dry-run`.
4. **Approved execution and verification**:
   - Run `legends-yt-dlp run <manifest.json> --yes` (add `--bulk` if `> 50` URLs, `--with-vpn` only if requested).
   - Run `legends-yt-dlp verify <manifest.json>` and `legends-yt-dlp ledger <manifest.json> --refresh`.
5. **Optional post-capture intelligence**:
   - Only run `legends-yt-dlp intelligence ...` when the user asks for transcripts, exact phrase search, clip plans, or vault pages.

## 4. EDR and Security Guardrails

- **No hidden consoles or shell wrappers**: Never invoke PowerShell, `cmd.exe`, or background child processes with hidden-window flags or execution-policy bypass switches. Invoke `legends-yt-dlp` or `python -m legends_ytdlp` directly with argument arrays (`shell=False`).
- **Anonymous extraction only**: Never read browser cookie stores, local browser profile databases, DPAPI secrets, or `.netrc` files. Every generated `yt-dlp.conf` enforces `--ignore-config`, `--no-cookies`, and `--no-cookies-from-browser`.
- **Fail-closed source respect**: Never rotate VPN relays, switch accounts, or automate challenge solvers to continue through HTTP 429 throttles, captchas, login walls, or platform blocks. Pause the batch and report the stop condition.
- **Data boundary**: Never commit `.env` (such as `MULLVAD_ACCOUNT_NUMBER`), `.local/`, `batches/`, `reports/`, or downloaded media to version control.
