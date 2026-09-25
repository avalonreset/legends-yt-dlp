# Post-Capture Intelligence

`legends-yt-dlp intelligence` is the post-download analysis layer for lawful local media that already exists in a Legends YT-DLP batch.

The module does not download media, operate Mullvad, call `yt-dlp`, rotate relays, or continue through source-side blocks. It works against local batch artifacts after the archive workflow has been verified.

It is not part of every download by default. Use it when the user asks for transcripts, exact search, clip extraction, a transcript vault, or another analysis workflow. If the user only asks to archive or download media, the normal stopping point is `run`, `verify`, and ledger review.

## Product Shape

The durable contract is a timestamped word ledger. ASR engines such as CrispASR + Parakeet, NVIDIA NeMo + Parakeet, or future backends should produce the same shape:

```json
{"word":"Agentic","start":312.42,"end":312.79,"confidence":0.92,"speaker":null}
```

Legends YT-DLP normalizes that input into:

```json
{
  "schema_version": 1,
  "item_id": "abc123",
  "video_id": "abc123",
  "source_url": "https://www.youtube.com/watch?v=abc123",
  "media_path": "E:\\path\\to\\video.mp4",
  "word_index": 184,
  "word": "Agentic",
  "normalized": "agentic",
  "start": 312.42,
  "end": 312.79,
  "confidence": 0.92,
  "speaker": null,
  "timing_source": "crispasr-word",
  "engine": "crispasr/parakeet-tdt-0.6b-v3"
}
```

Exact search operates on contiguous `normalized` tokens. `agentic` matches `Agentic`, but `agent` does not match `agentic`.

## Commands

Initialize the intelligence workspace for a batch:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence init "batches\...\manifest.json"
```

Check local state:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence doctor "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence doctor "batches\...\manifest.json" --require-gpu
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence status "batches\...\manifest.json"
```

`doctor --require-gpu` is the truth gate for long local ASR jobs. It fails unless the discovered CrispASR binary reports a compiled GPU backend such as CUDA, Vulkan, or Metal. A CPU-only CrispASR build is still local and token-free, but it should not be described as GPU-ready.

Contradictory transcription flags are rejected before work starts. Do not combine `--require-gpu` with `--no-gpu` or `--gpu-backend cpu`.

Import timestamped words from JSONL or JSON:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence ingest-words "batches\...\manifest.json" --input ".\words.jsonl" --video-id "abc123" --engine "nvidia/parakeet-tdt-0.6b-v2"
```

Run the ready-made CrispASR Parakeet backend on local media:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence transcribe "batches\...\manifest.json" --media ".\video.mp4" --video-id "abc123" --model auto
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence transcribe "batches\...\manifest.json" --all --model auto --limit 5
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence transcribe "batches\...\manifest.json" --all --model auto --gpu-backend cuda --require-gpu
```

Import existing CrispASR `-ojf` JSON:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence import-crispasr "batches\...\manifest.json" --input ".\transcript.json" --video-id "abc123" --media-path ".\video.mp4"
```

Prepare a NVIDIA NeMo Forced Aligner manifest from an existing word ledger:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence align nfa "batches\...\manifest.json" --media ".\video.mp4" --video-id "abc123" --prepare-only
```

Run NFA through an external NeMo environment and import the resulting word CTM:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence align nfa "batches\...\manifest.json" --media ".\video.mp4" --video-id "abc123" --python "C:\path\to\nemo-env\python.exe" --nemo-dir "C:\path\to\NeMo"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence align nfa "batches\...\manifest.json" --import-ctm ".\output\ctm\words\abc123.ctm" --video-id "abc123"
```

Search exact words or phrases:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence search "batches\...\manifest.json" "agentic"
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence search "batches\...\manifest.json" "agentic workflow" --json
```

Create a reviewable FFmpeg clip plan:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence clips plan "batches\...\manifest.json" --query "agentic" --pad-before 0.5 --pad-after 0.75
```

Render a reviewed plan:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence clips render "batches\...\intelligence\clips\agentic\clip-plan.json" --yes
```

Build Obsidian-compatible transcript pages:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\legends-yt-dlp.ps1 intelligence vault build "batches\...\manifest.json"
```

## Artifact Layout

```text
batches/<batch>/
  intelligence/
    manifest.json
    audio/
    transcripts/
    words/<video_id>.words.jsonl
    searches/<query>.matches.jsonl
    alignments/nfa/<video_id>/<video_id>.manifest.jsonl
    alignments/nfa/<video_id>/output/ctm/words/*.ctm
    clips/<query>/clip-plan.json
    clips/<query>/concat.txt
    clips/<query>/<query>-montage.mp4
    vault/index.md
    vault/<video_id>.md
```

## ASR Backend Strategy

The default ready-made ASR backend is now **CrispASR + Parakeet TDT 0.6B v3**.

CrispASR is a local C++ speech engine that can run Parakeet without adding PyTorch or NeMo to the core Legends YT-DLP package. Legends YT-DLP invokes it as an external tool, asks for full JSON output, and imports the resulting timestamped words into the same ledger/search/clip system.

Recommended command shape:

```powershell
crispasr --backend parakeet -m auto -f ".\audio.wav" -ojf -of ".\transcript"
```

Legends YT-DLP wraps that with `legends-yt-dlp intelligence transcribe`, which first extracts mono 16 kHz WAV with FFmpeg, then imports the CrispASR JSON.

Do not bundle CrispASR, Parakeet GGUF files, PyTorch, NeMo, or model weights in the core package. They are external runtime dependencies with their own licenses and install steps.

Primary references:

- CrispASR: https://github.com/CrispStrobe/CrispASR
- CrispASR CLI docs: https://raw.githubusercontent.com/CrispStrobe/CrispASR/main/docs/cli.md
- Parakeet v3 GGUF for CrispASR: https://huggingface.co/cstr/parakeet-tdt-0.6b-v3-GGUF
- NVIDIA NeMo ASR timestamps: https://docs.nvidia.com/nemo/speech/nightly/asr/intro.html
- Parakeet v2 model card: https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2
- Parakeet v3 model card: https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3

NeMo remains the upstream/reference route when an operator wants the official NVIDIA Python/CUDA stack. WhisperX remains a fallback only; it is not the product default.

## NeMo Forced Aligner Refinement

NVIDIA NeMo Forced Aligner is the precision re-timing layer for high-stakes clip boundaries. It does not replace the default CrispASR/Parakeet path. Legends YT-DLP prepares an NFA manifest from the existing word ledger, runs `tools/nemo_forced_aligner/align.py` when an external NeMo environment is available, and imports NFA `ctm/words/*.ctm` output back into the same `words/<video_id>.words.jsonl` ledger.

The CTM import is strict by design: the CTM word sequence must match the existing ledger word sequence before Legends YT-DLP replaces timings. If the word count or normalized word order differs, the import fails so an operator can review the transcript instead of silently shifting clip boundaries to the wrong words. Before replacement, Legends YT-DLP writes a `*.words.pre-nfa.jsonl` backup beside the current ledger.

Operational constraints:

- Keep NeMo, PyTorch, CUDA, and model weights outside the core package.
- Use `--prepare-only` first when setting up a new environment; it writes the absolute-audio-path manifest NFA expects.
- Use a CTC or hybrid CTC/Transducer model in CTC mode. Pure Transducer models are not supported by NFA.
- Default command options target `stt_en_fastconformer_hybrid_large_pc` with CUDA for both transcription and Viterbi alignment; override `--pretrained-name`, `--transcribe-device`, and `--viterbi-device` when needed.
- After NFA import, rerun normal `search`, `clips plan`, and `clips render`; those commands automatically use the refined word ledger.

## Operating SOP

1. Run the normal Legends YT-DLP archive workflow: inventory, ledger review, preflight, dry-run, approved real run, verify, ledger refresh.
2. Import or generate a word ledger for verified local media.
3. For delicate boundaries, run `intelligence align nfa ... --prepare-only`, run/import the NFA CTM, then confirm the word ledger is refined.
4. Search exact words or phrases.
5. Review matches and clip spans.
6. Generate a clip plan.
7. Render only after reviewing the plan and passing `--yes`.
8. Build the transcript vault for Codex/Claude/Gemini-assisted analysis.

No ASR system can find a word it failed to transcribe. For critical searches, compare two engines or run the NFA refinement pass before final clipping.
