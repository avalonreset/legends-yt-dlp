# CrispASR Parakeet Backend

CrispASR is the preferred ready-made ASR backend for Slayer intelligence.

It gives Slayer a local Parakeet transcription runner without making the core CLI depend on PyTorch, NeMo, or model weights. Slayer treats CrispASR as an external executable: CrispASR handles audio-to-transcript, and Slayer handles normalized word ledgers, exact search, clip plans, montage rendering, and transcript vaults.

## Why This Backend

The current recommendation is:

1. **Primary:** CrispASR with `--backend parakeet` and Parakeet TDT 0.6B v3 GGUF.
2. **Advanced fallback:** official NVIDIA NeMo + Parakeet when the operator specifically wants the upstream Python/CUDA stack.
3. **Not primary:** Whisper/WhisperX. Keep them as comparison or fallback tools only.

CrispASR fits this project because it is a C++ CLI, supports Parakeet v3, writes JSON/SRT/VTT/CSV/LRC outputs, supports full JSON with word/token arrays, supports VAD, has Windows build scripts, and can auto-download registered models with `-m auto`.

Sources:

- https://github.com/CrispStrobe/CrispASR
- https://raw.githubusercontent.com/CrispStrobe/CrispASR/main/docs/cli.md
- https://huggingface.co/cstr/parakeet-tdt-0.6b-v3-GGUF
- https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3

## Install

Slayer does not bundle CrispASR or Parakeet models. Operators install them locally and point Slayer at the executable.

Expected executable discovery order:

1. `CRISPASR_CLI`
2. `.local\bin\crispasr.exe`
3. `.local\crispasr\build*\bin\crispasr.exe`
4. `crispasr` on `PATH`

Typical Windows source build:

```powershell
git clone https://github.com/CrispStrobe/CrispASR .local\crispasr
cd .local\crispasr
.\build-windows.bat
$env:CRISPASR_CLI = "$PWD\build\bin\crispasr.exe"
```

If the Windows build creates the binary somewhere else, set `CRISPASR_CLI` to that exact path.

On machines without Visual Studio Build Tools, a MinGW/Ninja build can work:

```powershell
cd .local\crispasr
cmake -S . -B build-mingw-lowwin -G Ninja -DCMAKE_BUILD_TYPE=Release -DGGML_CCACHE=OFF -DGGML_OPENMP=OFF -DCRISPASR_BUILD_TESTS=OFF -DCMAKE_C_FLAGS="-D_WIN32_WINNT=0x0601" -DCMAKE_CXX_FLAGS="-D_WIN32_WINNT=0x0601"
cmake --build build-mingw-lowwin --target crispasr-cli
```

The `_WIN32_WINNT=0x0601` flag avoids older MinGW headers failing on the newer `THREAD_POWER_THROTTLING_STATE` API used by ggml.

## One-File Transcription

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence transcribe "batches\...\manifest.json" --media "batches\...\downloads\video.mp4" --video-id "abc123" --model auto
```

This command:

1. extracts mono 16 kHz WAV into `intelligence\audio\`;
2. runs CrispASR with `--backend parakeet -ojf`;
3. saves raw CrispASR JSON into `intelligence\transcripts\`;
4. imports timestamped words into `intelligence\words\<video>.words.jsonl`.

## Batch Transcription

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence transcribe "batches\...\manifest.json" --all --model auto --limit 5
```

By default, `--all` processes ledger items with `downloaded`, `archived`, or `verified` status and an existing local `output_path`.

## Import Existing CrispASR JSON

If you run CrispASR yourself:

```powershell
crispasr --backend parakeet -m auto -f ".\audio.wav" -ojf -of ".\transcript"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence import-crispasr "batches\...\manifest.json" --input ".\transcript.json" --video-id "abc123" --media-path ".\video.mp4"
```

## Output Contract

The adapter expects CrispASR full JSON output from `-ojf`. It reads top-level or segment-level `words[]` when present. If Parakeet emits token timings instead, Slayer combines adjacent subword tokens into word rows. It accepts segment fallback rows with timestamps only when a backend output lacks explicit word or token timing.

For exact clip retrieval, explicit word rows are preferred.

Rows derived from explicit CrispASR words are marked `timing_source: crispasr-word`. Rows combined from token timings are marked `timing_source: crispasr-token`. Rows split from segment timing are marked with `*-split-approximate` so review tools can treat them as lower precision.
