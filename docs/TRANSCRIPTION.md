# Transcription Routes

Legends YT-DLP captures media. Transcription is a separate concern with its own
routing. This module never bundles an ASR runtime, PyTorch, NeMo, or model
weights. Pick the route that fits the job:

## Route 1: In-module post-capture (this repo)

`intelligence transcribe` runs an operator-installed CrispASR executable against
media this module already verified. CrispASR is Parakeet-capable and stays
external: point the module at the binary with `CRISPASR_CLI` or drop it in
`.local/bin`. The module owns word ledgers, exact search, clip plans, and the
transcript vault. See [CRISPASR.md](CRISPASR.md) and
[INTELLIGENCE.md](INTELLIGENCE.md).

Use this when the media came from a Legends YT-DLP batch and the goal is
search, clips, or cited transcript pages.

## Route 2: Continuous and ambient audio (another module)

Background recording, voice sketchpads, recorder ingest, dedup archiving, and
vault distillation belong to `legends-ambient-intelligence`. If the audio did
not come from a capture batch, or the job is ongoing capture rather than a
bounded pull, hand off there instead of stretching this module.

## Route 3: Live typing (another module)

Real-time dictation at the keyboard belongs to `hyperyap`. Never route live
typing through capture batches.

## Precision re-timing (external, optional)

`intelligence align nfa` refines word timings with the NVIDIA NeMo Forced
Aligner for delicate clip boundaries. NeMo, PyTorch, and weights live in an
operator-managed environment; this module only writes the manifest and imports
the CTM output back into the word ledger, with a pre-import backup.

## Policy

No route in this repo downloads models silently, calls paid endpoints, or
requires a GPU. `intelligence doctor --require-gpu` is the truth gate before
claiming GPU-backed Parakeet.
