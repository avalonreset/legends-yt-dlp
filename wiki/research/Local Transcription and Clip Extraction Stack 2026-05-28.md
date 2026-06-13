---
type: research
status: developing
created: 2026-05-28
updated: 2026-06-12
tags: [research, transcription, asr, forced-alignment, diarization, clips, ffmpeg, product]
---

# Local Transcription and Clip Extraction Stack 2026-05-28

## Scope

This research track covers a lawful post-download video intelligence module for Legends YT-DLP Slayer. It does not change the download safety boundary: Mullvad is for privacy and leak prevention, not bypassing source-side throttling, captchas, login challenges, account controls, or blocks.

The target workflow is:

1. User lawfully archives videos.
2. Slayer extracts local audio.
3. A local ASR engine produces transcript text plus word-level timestamps.
4. Slayer builds a normalized word ledger and optional speaker map.
5. User searches exact words or phrases across many videos.
6. Slayer converts search hits into padded clip spans and FFmpeg montage plans.
7. Slayer can build an Obsidian-compatible wiki from transcript, source metadata, and clip references.

## Executive Recommendation

Build this as a separate "post-capture intelligence" module instead of mixing it into the download runner.

Recommended stack:

1. **Default ready-made ASR:** CrispASR with Parakeet TDT 0.6B v3 GGUF. It is a local C++ CLI, supports Parakeet, full JSON with word/token detail, VAD, Windows build scripts, and avoids a Python/PyTorch dependency chain in Slayer.
2. **Upstream/reference ASR:** NVIDIA NeMo + Parakeet, starting with `nvidia/parakeet-tdt-0.6b-v2` for English and `nvidia/parakeet-tdt-0.6b-v3` when multilingual support matters. NeMo documents direct char, word, and segment timestamp output for Parakeet models, and Parakeet v2/v3 model cards explicitly advertise word-level timestamps and commercial/non-commercial use under CC BY 4.0.
3. **Precision alignment pass:** NVIDIA NeMo Forced Aligner for CTM/ASS word alignment when a CTC or hybrid CTC model is acceptable. NFA emits token, word, and segment CTM files, handles long files subject to hardware, and can align against ASR-generated text. It cannot use pure transducer models, so this is a second-stage refinement path, not a drop-in Parakeet TDT replacement.
4. **Diarization:** pyannote.audio community pipeline as optional speaker labeling. Treat it as speaker segments, not word timing. Reconcile speaker labels onto the word ledger by interval overlap.
5. **Fallback all-in-one:** WhisperX for users who want one mature package with Whisper/faster-whisper ASR, wav2vec2 alignment, VAD, and pyannote diarization. It is not the first choice because the product direction prefers Parakeet, but it is the strongest fallback ecosystem.
6. **Clip assembly:** FFmpeg for deterministic extraction and montage. Store clip spans first, then render with either a re-encoded concat filter path for frame-accurate output or a stream-copy concat demuxer path only when sources/codecs are compatible.

## Ranked Tool Assessment

### 1. CrispASR + Parakeet TDT v3 GGUF

**Role:** Default ready-made local ASR CLI for Slayer intelligence.

**Why it fits:** CrispASR is a C++ speech engine with a Parakeet backend, JSON/SRT/VTT/CSV/LRC outputs, full JSON word/token arrays, VAD, auto-download support, and Windows build scripts. The companion Parakeet v3 GGUF conversion provides quantized model files for this runtime and documents built-in TDT timestamps.

**License/commercial:** CrispASR is MIT. The Parakeet GGUF files inherit CC BY 4.0 model terms from NVIDIA Parakeet, so Slayer should not bundle them and should preserve attribution guidance.

**Windows/local practicality:** Better first product path than NeMo because operators can run a local CLI instead of managing a CUDA/PyTorch/NeMo environment. Slayer should discover `CRISPASR_CLI`, `.local/bin/crispasr.exe`, or `crispasr` on `PATH`.

**Integration notes:**

- Extract audio to mono 16 kHz WAV with FFmpeg.
- Run `crispasr --backend parakeet -m auto -f audio.wav -ojf -of transcript`.
- Import CrispASR JSON into Slayer's normalized word ledger.
- Keep raw engine JSON under `intelligence/transcripts/`.

Sources:

- [CrispASR GitHub](https://github.com/CrispStrobe/CrispASR)
- [CrispASR CLI docs](https://raw.githubusercontent.com/CrispStrobe/CrispASR/main/docs/cli.md)
- [Parakeet v3 GGUF for CrispASR](https://huggingface.co/cstr/parakeet-tdt-0.6b-v3-GGUF)

### 2. NVIDIA NeMo + Parakeet

**Role:** Upstream/reference ASR engine and advanced fallback.

**Why it fits:** NeMo's ASR docs show loading Parakeet with `ASRModel.from_pretrained`, enabling `timestamps=True`, and reading `timestamp['word']`, `timestamp['segment']`, and `timestamp['char']`. Parakeet v2 is English-focused and explicitly lists accurate word-level timestamps. Parakeet v3 extends support to 25 European languages and lists accurate word-level and segment-level timestamps.

**License/commercial:** NeMo code is Apache 2.0. Parakeet v2 and v3 are CC BY 4.0 and the v2/v3 model cards say the models are ready for commercial and non-commercial use. Attribution should be included in our dependency notice if we guide users to install the models.

**Windows/local GPU practicality:** NeMo is Python/PyTorch/CUDA-oriented. It should be treated as a serious GPU dependency, not a tiny CLI dependency. The newer `parakeet-unified-en-0.6b` is promising for unified offline/streaming inference, but its model card lists Linux as preferred/supported OS and uses the NVIDIA Open Model License. For this Windows-first product, start with the better-documented Parakeet timestamp path and keep unified as a tracked experiment.

**Timestamp granularity:** Word, segment, and char/token timestamps are available through NeMo timestamp APIs for Parakeet models. NeMo examples convert FastConformer offsets with an 80 ms stride, so the product should treat boundaries as excellent for search and clip selection but still pad clip edges.

**Integration notes:**

- Extract audio to mono 16 kHz WAV with FFmpeg.
- Run Parakeet ASR in a separate dependency environment, not the core downloader venv.
- Save raw NeMo hypothesis JSON and normalized Slayer word ledger.
- Use a default pad of 0.35 to 0.75 seconds around word/phrase hits.
- Add a "critical keyword audit" mode that can reprocess the local region around a hit with a second model or aligner when precision matters.

Sources:

- [NeMo ASR timestamp docs](https://docs.nvidia.com/nemo/speech/nightly/asr/intro.html)
- [NeMo Speech quickstart with word timestamps](https://docs.nvidia.com/nemo/speech/nightly/starthere/ten_minutes.html)
- [NeMo GitHub license and install notes](https://github.com/NVIDIA-NeMo/NeMo)
- [Parakeet TDT 0.6B v2 model card](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2)
- [Parakeet TDT 0.6B v3 model card](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)
- [Parakeet unified EN 0.6B model card](https://huggingface.co/nvidia/parakeet-unified-en-0.6b)

### 3. NVIDIA NeMo Forced Aligner

**Role:** Precision alignment and subtitle/CTM generator.

**Why it fits:** NFA is built to generate token, word, and segment timestamps from audio using NeMo CTC-based ASR models. It accepts a manifest with audio paths and optional text, can use ASR-predicted text with `align_using_pred_text=true`, and writes CTM and ASS outputs. CTM is exactly the kind of format we need for a word-span ledger.

**License/commercial:** Part of NeMo's Apache 2.0 codebase. Model licenses depend on the chosen checkpoint.

**Windows/local GPU practicality:** Better as an advanced dependency than first-run default. It relies on the NeMo stack, CTC or hybrid CTC models, and CUDA/PyTorch for practical throughput. It can use CPU but should not be presented as lightweight.

**Timestamp granularity:** Token, word, and segment CTM. NFA docs state CTM lines include utterance id, channel id, start time in seconds, duration in seconds, and text.

**Tradeoff:** NFA currently supports CTC or hybrid CTC/Transducer in CTC mode, not pure Transducer models. That means Parakeet TDT direct timestamps remain the default, while NFA is the alignment refinery when we select a compatible CTC model.

**Implementation update 2026-06-12:** Slayer now has the refinement bridge in code. `slayer intelligence align nfa` prepares absolute-path NFA manifests under `intelligence/alignments/nfa/<video_id>/`, can launch an external NeMo `tools/nemo_forced_aligner/align.py`, and imports `ctm/words/*.ctm` back into `intelligence/words/<video_id>.words.jsonl`. Import is strict: the CTM word count and normalized word order must match the existing ledger before timings are replaced. Successful imports create a `*.words.pre-nfa.jsonl` backup.

Current command shape:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence align nfa "batches\...\manifest.json" --media ".\video.mp4" --video-id "abc123" --prepare-only
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence align nfa "batches\...\manifest.json" --media ".\video.mp4" --video-id "abc123" --python "C:\path\to\nemo-env\python.exe" --nemo-dir "C:\path\to\NeMo"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence align nfa "batches\...\manifest.json" --import-ctm ".\output\ctm\words\abc123.ctm" --video-id "abc123"
```

Sources:

- [NeMo Forced Aligner docs](https://docs.nvidia.com/nemo-framework/user-guide/latest/nemotoolkit/tools/nemo_forced_aligner.html)
- [NeMo Forced Aligner nightly docs](https://docs.nvidia.com/nemo/speech/nightly/tools/nemo_forced_aligner.html)
- [NVIDIA forced alignment explainer](https://research.nvidia.com/labs/conv-ai/blogs/2023/2023-08-forced-alignment/)

### 4. WhisperX

**Role:** Best mature fallback when a user accepts Whisper.

**Why it fits:** WhisperX combines faster-whisper, VAD, wav2vec2 alignment, word-level timestamps, and pyannote diarization. The repository is mature, highly starred, and focused on long-form transcription with word-level timings and diarization.

**License/commercial:** BSD-2-Clause repository license. Downstream model licenses still matter: Whisper is MIT, alignment models vary, and pyannote models may require Hugging Face gate acceptance.

**Windows/local GPU practicality:** Practical, but dependency-heavy. It supports CPU via `--device cpu --compute_type int8`, but GPU is the expected path for large jobs.

**Timestamp granularity:** Word-level timestamps via wav2vec2 forced phoneme alignment. The WhisperX paper specifically frames the problem as Whisper lacking word-level timestamps out of the box and solving it with VAD plus forced alignment.

**Tradeoff:** It violates the product preference to avoid Whisper as the primary engine. Keep it as a fallback and comparison baseline.

Sources:

- [WhisperX GitHub](https://github.com/m-bain/whisperX)
- [WhisperX paper](https://arxiv.org/abs/2303.00747)
- [OpenAI Whisper GitHub](https://github.com/openai/whisper)
- [faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper)

### 5. pyannote.audio

**Role:** Optional speaker diarization.

**Why it fits:** pyannote.audio is a mature PyTorch speaker diarization toolkit with a current `community-1` pipeline. The model card includes local execution, GPU transfer, offline cloning, speaker-count hints, and an exclusive diarization output intended to simplify reconciliation with transcription timestamps.

**License/commercial:** pyannote.audio code is MIT. The `speaker-diarization-community-1` model is CC BY 4.0 but gated on Hugging Face user-condition acceptance and contact-info sharing. Do not bundle the model. Guide users through their own token and acceptance step.

**Windows/local GPU practicality:** Python/PyTorch/FFmpeg stack. Runs on CPU by default and can move to CUDA. Should be optional because it introduces Hugging Face account/token setup.

**Timestamp granularity:** Speaker turn segments, not word timings. Use it to assign speakers to ASR word spans by overlap.

Sources:

- [pyannote.audio GitHub](https://github.com/pyannote/pyannote-audio)
- [pyannote speaker-diarization-community-1 model card](https://huggingface.co/pyannote/speaker-diarization-community-1)

### 6. stable-ts

**Role:** Whisper-based subtitle/timestamp refinement fallback.

**Why it fits:** stable-ts focuses on stabilized timestamps, forced alignment, audio indexing, SRT/VTT/ASS output, and timestamp refinement on top of Whisper/faster-whisper/Hugging Face/MLX backends. It has useful APIs for padding word timestamps and refining existing results.

**License/commercial:** MIT.

**Windows/local GPU practicality:** Works on Windows with FFmpeg and PyTorch, but still belongs in the optional Whisper fallback path.

**Timestamp granularity:** Segment and word-level timestamps, plus refinement functions that narrow word starts and ends.

**Tradeoff:** Less complete than WhisperX for diarization and less aligned with the Parakeet-first product direction.

Source:

- [stable-ts GitHub](https://github.com/jianfch/stable-ts)

### 7. Montreal Forced Aligner

**Role:** Advanced known-transcript aligner, not default archive transcription.

**Why it fits:** MFA is a mature command-line forced aligner using Kaldi, conda-distributed dependencies, pretrained acoustic models, pronunciation dictionaries, and TextGrid output. It is excellent when you already have a clean transcript and language resources.

**License/commercial:** MIT.

**Windows/local GPU practicality:** Conda installs Kaldi/MFA dependencies, including Windows paths. It is less GPU-focused than NeMo/WhisperX and heavier operationally because of dictionaries/acoustic models.

**Timestamp granularity:** Word and phone intervals via TextGrid-style forced alignment.

**Tradeoff:** Not a good first default for arbitrary YouTube video archives because transcripts are not guaranteed clean and language/dictionary setup adds user friction.

Sources:

- [Montreal Forced Aligner GitHub](https://github.com/MontrealCorpusTools/Montreal-Forced-Aligner)
- [MFA installation docs](https://montreal-forced-aligner.readthedocs.io/en/latest/installation.html)
- [MFA TextGrid utilities](https://montreal-forced-aligner.readthedocs.io/en/stable/reference/helper/textgrid.html)

### 8. ctc-segmentation and torchaudio forced alignment

**Role:** Low-level building blocks for a custom aligner later.

**Why they fit:** ctc-segmentation can find utterance alignments from CTC emissions and includes examples for word timestamps. Torchaudio exposes a CTC forced-alignment API with CPU and CUDA implementations and a higher-level bundle API.

**License/commercial:** ctc-segmentation is Apache 2.0. Torchaudio follows the PyTorch ecosystem licensing.

**Windows/local GPU practicality:** Useful for engineers, not end users. These require model emissions, tokenization, and alignment code. They are not one-command product features.

**Timestamp granularity:** Word spans are possible, but quality depends heavily on the CTC model, tokenizer, frame stride, and transcript accuracy.

Sources:

- [ctc-segmentation GitHub](https://github.com/lumaku/ctc-segmentation)
- [torchaudio CTC forced alignment tutorial](https://docs.pytorch.org/audio/2.3.0/tutorials/ctc_forced_alignment_api_tutorial.html)

### 9. FFmpeg

**Role:** Audio extraction, clip rendering, and montage assembly.

**Why it fits:** FFmpeg is already a Slayer dependency. The formats docs define the concat demuxer, and the ffmpeg docs cover seeking. Use FFmpeg only after the transcript module has produced normalized clip spans.

**Integration recommendation:**

- Extract audio: `ffmpeg -i input.mp4 -vn -ac 1 -ar 16000 audio.wav`
- For accurate individual clips, prefer re-encode extraction around the padded span.
- For montage, create normalized intermediate clips first, then concat. This avoids codec/timebase surprises from trying to stream-copy arbitrary source segments.
- Keep an EDL/JSON clip-plan before rendering so the user can review every match.

Sources:

- [FFmpeg command docs](https://www.ffmpeg.org/ffmpeg.html)
- [FFmpeg concat demuxer docs](https://ffmpeg.org/ffmpeg-formats.html#concat)

## Product Artifact Design

The module should not treat transcript text as the source of truth. The source of truth should be a structured word ledger.

Suggested files per batch:

- `intelligence/audio/<video_id>.wav`
- `intelligence/transcripts/<video_id>.json`
- `intelligence/words/<video_id>.jsonl`
- `intelligence/alignments/nfa/<video_id>/<video_id>.manifest.jsonl`
- `intelligence/alignments/nfa/<video_id>/output/ctm/words/*.ctm`
- `intelligence/speakers/<video_id>.rttm` or `.json`
- `intelligence/index/slayer-intelligence.sqlite`
- `intelligence/clips/<query_slug>/clip-plan.json`
- `intelligence/clips/<query_slug>/concat.txt`
- `intelligence/vault/<video_id>.md`

Suggested word ledger fields:

```json
{
  "batch_id": "batch-20260528",
  "video_id": "abc123",
  "source_url": "https://example.invalid/video",
  "media_path": "archive/abc123.mp4",
  "word_index": 42,
  "word": "agentic",
  "normalized": "agentic",
  "start": 123.44,
  "end": 123.81,
  "confidence": 0.92,
  "speaker": "SPEAKER_00",
  "engine": "nemo-parakeet-tdt-0.6b-v2",
  "alignment_engine": null
}
```

Exact word and phrase search should be token-sequence search over `normalized`, not plain-text substring search. This makes `"agentic"` retrieval deterministic once ASR has recognized the word. It also supports phrase windows such as `"AI agentic workflow"` by matching consecutive normalized tokens and returning the first word start and last word end.

Critical limitation: no ASR engine can find a word it failed to transcribe. For high-stakes query terms, add optional cross-check modes:

- second ASR engine comparison;
- local audio-window re-run around near-hits;
- forced alignment against a user-supplied target phrase/transcript;
- manual review queue for low-confidence matches.

## Proposed Commands

Implemented command surface:

```powershell
slayer intelligence init ".\runs\batch-20260528\manifest.json"
slayer intelligence transcribe ".\runs\batch-20260528\manifest.json" --media ".\video.mp4" --video-id "abc123" --model auto
slayer intelligence search ".\runs\batch-20260528\manifest.json" "agentic"
slayer intelligence clips plan ".\runs\batch-20260528\manifest.json" --query "agentic" --pad-before 0.50 --pad-after 0.75
slayer intelligence clips render ".\runs\batch-20260528\intelligence\clips\agentic\clip-plan.json" --yes
slayer intelligence vault build ".\runs\batch-20260528\manifest.json"
```

Advanced options:

```powershell
slayer intelligence transcribe ".\runs\batch-20260528\manifest.json" --all --model auto --gpu-backend cuda --require-gpu
slayer intelligence align nfa ".\runs\batch-20260528\manifest.json" --media ".\video.mp4" --video-id "abc123" --pretrained-name stt_en_fastconformer_hybrid_large_pc
slayer intelligence diarize --engine pyannote-community --hf-token-env HF_TOKEN
```

## Implementation Plan

Phase 1 should be a small local proof:

1. Add `intelligence` module skeleton behind optional extras.
2. Add FFmpeg audio extraction.
3. Add Parakeet/NeMo adapter that writes raw JSON plus `words.jsonl`.
4. Add deterministic exact word/phrase search over JSONL.
5. Add clip-plan generation only, no rendering.
6. Add FFmpeg rendering for a reviewed clip plan.
7. Add Obsidian transcript page generation.

Phase 2:

1. Add SQLite FTS5 plus exact token table.
2. Add pyannote speaker labeling as optional.
3. Validate the implemented NeMo Forced Aligner bridge against a real NeMo/CUDA environment.
4. Add search hit QA: confidence thresholds, padding previews, and low-confidence review.
5. Add a small lawful sample-media test fixture so CI can validate parsing/search/clip-plan logic without relying on live YouTube.

Phase 3:

1. Add UI-grade review reports.
2. Add montage templates.
3. Add per-channel transcript wiki.
4. Add model install wizard and environment doctor.

## Decision

This belongs in Slayer, but as a companion module: **Post-Capture Intelligence**.

The product should remain conservative:

- Download runner: safe, rights-aware archiving.
- Intelligence module: local transcription, search, clip planning, wiki generation.
- Clip renderer: local FFmpeg operations against already-downloaded media.

The strongest first build is Parakeet-first, word-ledger-first, FFmpeg-plan-first. Diarization and forced alignment should be optional precision layers, not required for the first usable experience.
