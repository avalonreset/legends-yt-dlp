# Third-Party Notices

`legends-yt-dlp` is released under the MIT License (`LICENSE`).

## Runtime Dependencies

`legends-yt-dlp` declares `yt-dlp>=2026.10.01` (`Unlicense`) in `pyproject.toml` and uses the Python standard library for its control plane.

## External Tools (Not Bundled)

`legends-yt-dlp` orchestrates optional external command-line tools installed separately by the operator. No third-party binaries or model weights are bundled in this source repository or release archive:

| Tool / Model | Upstream Project | License | Role |
| --- | --- | --- | --- |
| `yt-dlp` | [github.com/yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp) | Unlicense | External media extractor downloaded on demand via `legends-yt-dlp yt-dlp install` and verified against `SHA2-256SUMS` |
| `FFmpeg` / `ffprobe` | [ffmpeg.org](https://ffmpeg.org) | LGPL-2.1+ / GPL-2.0+ (build-dependent) | External media probing, audio extraction, and clip rendering |
| `Mullvad VPN CLI` | [github.com/mullvad/mullvadvpn-app](https://github.com/mullvad/mullvadvpn-app) | GPL-3.0 | Optional external VPN CLI for `--with-vpn` guarded runs |
| `CrispASR` | [github.com/CrispStrobe/CrispASR](https://github.com/CrispStrobe/CrispASR) | MIT | Optional external local ASR CLI for post-capture word ledgers |
| `NVIDIA Parakeet TDT v2/v3` | [huggingface.co/nvidia/parakeet-tdt-0.6b-v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3) | CC-BY-4.0 | Optional external ASR model weights used with CrispASR or NeMo |
| `NVIDIA NeMo` | [github.com/NVIDIA/NeMo](https://github.com/NVIDIA/NeMo) | Apache-2.0 | Optional external forced-aligner runtime (`intelligence align nfa`) |

See [NOTICE](NOTICE) and [docs/LEGAL.md](docs/LEGAL.md) for additional attribution details.
