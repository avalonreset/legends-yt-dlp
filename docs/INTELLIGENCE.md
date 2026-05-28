# Post-Capture Intelligence

`slayer intelligence` is the post-download analysis layer for lawful local media that already exists in a Slayer batch.

The module does not download media, operate Mullvad, call `yt-dlp`, rotate relays, or continue through source-side blocks. It works against local batch artifacts after the archive workflow has been verified.

## Product Shape

The durable contract is a timestamped word ledger. ASR engines such as NVIDIA NeMo + Parakeet, WhisperX, or future backends should produce the same shape:

```json
{"word":"Agentic","start":312.42,"end":312.79,"confidence":0.92,"speaker":null}
```

Slayer normalizes that input into:

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
  "engine": "nvidia/parakeet-tdt-0.6b-v2"
}
```

Exact search operates on contiguous `normalized` tokens. `agentic` matches `Agentic`, but `agent` does not match `agentic`.

## Commands

Initialize the intelligence workspace for a batch:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence init "batches\...\manifest.json"
```

Check local state:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence doctor "batches\...\manifest.json"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence status "batches\...\manifest.json"
```

Import timestamped words from JSONL or JSON:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence ingest-words "batches\...\manifest.json" --input ".\words.jsonl" --video-id "abc123" --engine "nvidia/parakeet-tdt-0.6b-v2"
```

Search exact words or phrases:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence search "batches\...\manifest.json" "agentic"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence search "batches\...\manifest.json" "agentic workflow" --json
```

Create a reviewable FFmpeg clip plan:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence clips plan "batches\...\manifest.json" --query "agentic" --pad-before 0.5 --pad-after 0.75
```

Render a reviewed plan:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence clips render "batches\...\intelligence\clips\agentic\clip-plan.json" --yes
```

Build Obsidian-compatible transcript pages:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence vault build "batches\...\manifest.json"
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
    clips/<query>/clip-plan.json
    clips/<query>/concat.txt
    clips/<query>/<query>-montage.mp4
    vault/index.md
    vault/<video_id>.md
```

## ASR Backend Strategy

The MVP accepts imported word ledgers so the search and clip system can be verified without a heavy GPU dependency.

The recommended production ASR path is still NVIDIA NeMo + Parakeet:

- English default: `nvidia/parakeet-tdt-0.6b-v2`
- Multilingual option: `nvidia/parakeet-tdt-0.6b-v3`
- Runtime isolation: WSL2 Ubuntu with NVIDIA CUDA, Docker Desktop with WSL2 GPU backend, or a separate managed Python environment

Do not add PyTorch, NeMo, or model weights to the core CLI package. They are optional external runtime dependencies.

Primary references:

- NVIDIA NeMo ASR timestamps: https://docs.nvidia.com/nemo/speech/nightly/asr/intro.html
- Parakeet v2 model card: https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2
- Parakeet v3 model card: https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3
- NeMo install docs: https://docs.nvidia.com/nemo/speech/nightly/starthere/install.html
- Docker Desktop GPU support: https://docs.docker.com/desktop/features/gpu/

## Operating SOP

1. Run the normal Slayer archive workflow: inventory, ledger review, preflight, dry-run, approved real run, verify, ledger refresh.
2. Import or generate a word ledger for verified local media.
3. Search exact words or phrases.
4. Review matches and clip spans.
5. Generate a clip plan.
6. Render only after reviewing the plan and passing `--yes`.
7. Build the transcript vault for Codex/Claude/Gemini-assisted analysis.

No ASR system can find a word it failed to transcribe. For critical searches, compare two engines or add a future forced-alignment review pass.
