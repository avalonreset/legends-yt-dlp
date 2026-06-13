---
type: runbook
status: active
created: 2026-06-12
updated: 2026-06-12
tags: [runbook, intelligence, nemo, forced-alignment, clips]
---

# NeMo Forced Aligner Refinement

Use this runbook when a clip boundary is delicate and word starts/ends need a stricter pass than the default ASR timestamps.

## Position in the Stack

NVIDIA NeMo Forced Aligner is an optional refinement layer for `slayer intelligence`. It does not download media and it does not replace CrispASR/Parakeet as the preferred ready-made transcription path. Slayer keeps NeMo, PyTorch, CUDA, and model weights outside the core package.

The durable contract remains the normalized word ledger:

- input: existing `intelligence/words/<video_id>.words.jsonl`
- NFA prep: `intelligence/alignments/nfa/<video_id>/<video_id>.manifest.jsonl`
- NFA output: `intelligence/alignments/nfa/<video_id>/output/ctm/words/*.ctm`
- refined output: the same `intelligence/words/<video_id>.words.jsonl`
- backup: `intelligence/words/<video_id>.words.pre-nfa.jsonl`

## Commands

Prepare an NFA manifest from the existing word ledger:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence align nfa "batches\...\manifest.json" --media ".\video.mp4" --video-id "VIDEO_ID" --prepare-only
```

Run NFA through an operator-managed NeMo checkout:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence align nfa "batches\...\manifest.json" --media ".\video.mp4" --video-id "VIDEO_ID" --python "C:\path\to\nemo-env\python.exe" --nemo-dir "C:\path\to\NeMo"
```

Import a CTM produced outside Slayer:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence align nfa "batches\...\manifest.json" --import-ctm ".\output\ctm\words\VIDEO_ID.ctm" --video-id "VIDEO_ID"
```

After import, rerun the normal search and clip workflow. Search and clip planning automatically use the refined ledger:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence search "batches\...\manifest.json" "crazy insane"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence clips plan "batches\...\manifest.json" --query "crazy insane"
powershell -ExecutionPolicy Bypass -File scripts\slayer.ps1 intelligence clips render "batches\...\intelligence\clips\crazy-insane\clip-plan.json" --yes
```

## Guardrails

- Use a CTC or hybrid CTC/Transducer model in CTC mode. NFA does not support pure Transducer models.
- Start with `--prepare-only` when validating a new machine or environment.
- Keep `--transcribe-device cuda` and `--viterbi-device cuda` only when the NeMo environment really has CUDA available. Use `cpu` explicitly for CPU runs.
- The CTM import is strict: the NFA word count and normalized word order must match the current ledger before timings are replaced.
- If import fails with a word mismatch, do not force it. Review the transcript text, regenerate the reference, or align a smaller region.

## Source

- [NVIDIA NeMo Forced Aligner docs](https://docs.nvidia.com/nemo-framework/user-guide/latest/nemotoolkit/tools/nemo_forced_aligner.html)
