# Third-Party Notices

`legends-youtube` is released under the MIT License ([LICENSE](LICENSE)).

## Runtime Dependencies

- `legends_youtube` (YouTube Data API v3, Analytics API v2, Studio validators, 0-quota public radar, and knowledge pack resolver) uses the Python 3.11+ standard library (`urllib.request`, `json`, `hashlib`, `argparse`, `struct`) with zero third-party runtime imports.
- `legends_ytdlp` (bundled `legends-yt-dlp` media archiving and word-ledger control plane) declares `yt-dlp>=2026.10.01` (`Unlicense`) in `pyproject.toml` and uses the Python standard library for its control plane.

## External Tools and References (Not Bundled)

`legends-youtube` and `legends-yt-dlp` orchestrate optional external command-line tools installed separately by the operator. No third-party binaries or model weights are bundled in this source repository or release archive:

| Tool / Model | Upstream Project | License | Role |
| --- | --- | --- | --- |
| `yt-dlp` | [github.com/yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp) | Unlicense | External media extractor downloaded on demand via `legends-yt-dlp yt-dlp install` and verified against `SHA2-256SUMS` |
| `FFmpeg` / `ffprobe` | [ffmpeg.org](https://ffmpeg.org) | LGPL-2.1+ / GPL-2.0+ (build-dependent) | External media stream verification, audio demuxing, and clip rendering |
| `Mullvad VPN CLI` | [github.com/mullvad/mullvadvpn-app](https://github.com/mullvad/mullvadvpn-app) | GPL-3.0 | Optional external VPN CLI for `--with-vpn` guarded capture runs |
| `CrispASR` | [github.com/CrispStrobe/CrispASR](https://github.com/CrispStrobe/CrispASR) | MIT | Optional external local ASR CLI for GPU word ledgers |
| `NVIDIA Parakeet TDT v2/v3` | [huggingface.co/nvidia/parakeet-tdt-0.6b-v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3) | CC-BY-4.0 | Optional external ASR model weights used with CrispASR or NeMo |
| `NVIDIA NeMo` | [github.com/NVIDIA/NeMo](https://github.com/NVIDIA/NeMo) | Apache-2.0 | Optional external forced-aligner runtime (`intelligence align nfa`) |

Official YouTube Data API v3, YouTube Analytics API v2, and YouTube Help documentation references cited in [references/sources.md](references/sources.md) and `knowledge/youtube/vault/` remain the property of Google LLC and their respective authors. See [NOTICE](NOTICE), [NOTICE.md](NOTICE.md), and [docs/LEGAL.md](docs/LEGAL.md) for additional attribution details.
