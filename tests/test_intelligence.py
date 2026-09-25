import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from legends_ytdlp.process import CommandResult
from legends_ytdlp.intelligence import (
    build_vault,
    import_crispasr_json,
    import_words,
    init_intelligence,
    intelligence_paths,
    make_clip_plan,
    parse_nfa_words_ctm,
    prepare_nfa_manifest,
    parse_crispasr_diagnostics,
    read_jsonl,
    refine_words_with_nfa_ctm,
    run_nfa_alignment,
    search_words,
    transcribe_with_crispasr,
)
from legends_ytdlp.tools import ToolInfo


class IntelligenceTests(unittest.TestCase):
    def make_manifest(self, root: Path, *, with_media: bool = True) -> Path:
        output = root / "downloads"
        output.mkdir()
        media = output / "fixture.mp4"
        if with_media:
            media.write_bytes(b"fake media")
        ledger = root / "items.jsonl"
        ledger.write_text(
            json.dumps(
                {
                    "id": "vid123",
                    "position": 1,
                    "status": "downloaded",
                    "url": "https://www.youtube.com/watch?v=vid123",
                    "output_path": str(media) if with_media else None,
                    "warnings": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        manifest = root / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "name": "fixture-batch",
                    "source_urls": ["https://www.youtube.com/watch?v=vid123"],
                    "paths": {
                        "item_ledger": str(ledger),
                        "output": str(output),
                        "download_archive": str(root / "archive.txt"),
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return manifest

    def write_words(self, root: Path) -> Path:
        words = root / "words.jsonl"
        rows = [
            {"word": "This", "start": 0.10, "end": 0.22, "confidence": 0.9},
            {"word": "agentic", "start": 1.00, "end": 1.40, "confidence": 0.95},
            {"word": "workflow", "start": 1.42, "end": 1.90, "confidence": 0.91},
            {"word": "matters", "start": 2.20, "end": 2.60, "confidence": 0.87},
        ]
        words.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        return words

    def test_init_creates_workspace_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.make_manifest(root)

            target = init_intelligence(manifest)

            paths = intelligence_paths(root)
            self.assertEqual(target, paths.manifest)
            self.assertTrue(paths.words.is_dir())
            self.assertTrue(paths.clips.is_dir())
            self.assertIn("lawful_local_media_only", target.read_text(encoding="utf-8"))

    def test_import_words_normalizes_jsonl_and_exact_phrase_searches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.make_manifest(root)
            words = self.write_words(root)

            target, count = import_words(manifest, words, video_id="vid123", engine="fixture")
            matches = search_words(manifest, "agentic workflow", pad_start=0.5, pad_end=0.75)
            substring_matches = search_words(manifest, "agent")

            self.assertEqual(count, 4)
            imported = read_jsonl(target)
            self.assertEqual(imported[1]["normalized"], "agentic")
            self.assertEqual(imported[1]["media_path"], str(root / "downloads" / "fixture.mp4"))
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["start"], 1.0)
            self.assertEqual(matches[0]["end"], 1.9)
            self.assertEqual(matches[0]["clip_start"], 0.5)
            self.assertEqual(matches[0]["clip_end"], 2.65)
            self.assertEqual(substring_matches, [])

    def test_import_words_accepts_json_words_array_and_rejects_bad_timestamps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.make_manifest(root)
            payload = root / "words.json"
            payload.write_text(
                json.dumps({"words": [{"word": "bad", "start": 2.0, "end": 2.0}]}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "after start"):
                import_words(manifest, payload, video_id="vid123")

    def test_prepare_nfa_manifest_uses_existing_word_ledger_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.make_manifest(root)
            words = self.write_words(root)
            media = root / "downloads" / "fixture.mp4"
            import_words(manifest, words, video_id="vid123")

            def fake_extract(media_path: Path, audio_path: Path) -> CommandResult:
                audio_path.parent.mkdir(parents=True, exist_ok=True)
                audio_path.write_bytes(b"wav")
                return CommandResult(("ffmpeg",), 0, "", "")

            with patch("legends_ytdlp.intelligence.extract_audio", side_effect=fake_extract):
                prepared = prepare_nfa_manifest(manifest, media, video_id="vid123")

            nfa_manifest = Path(str(prepared["manifest_path"]))
            rows = read_jsonl(nfa_manifest)
            self.assertEqual(prepared["target_id"], "vid123")
            self.assertTrue(Path(str(prepared["audio_path"])).is_absolute())
            self.assertEqual(rows[0]["text"], "This agentic workflow matters")
            self.assertEqual(rows[0]["audio_filepath"], str(Path(str(prepared["audio_path"])).resolve()))

    def test_refine_words_with_nfa_ctm_updates_existing_ledger_and_backs_up(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.make_manifest(root)
            words = self.write_words(root)
            import_words(manifest, words, video_id="vid123")
            ctm = root / "vid123.ctm"
            ctm.write_text(
                "\n".join(
                    [
                        "vid123 1 0.050 0.210 This",
                        "vid123 1 0.940 0.500 agentic",
                        "vid123 1 1.470 0.390 workflow",
                        "vid123 1 2.140 0.320 matters",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            target, count, backup_path = refine_words_with_nfa_ctm(manifest, ctm, video_id="vid123")
            imported = read_jsonl(target)
            matches = search_words(manifest, "agentic workflow", pad_start=0.1, pad_end=0.2)

            self.assertEqual(count, 4)
            self.assertIsNotNone(backup_path)
            self.assertTrue(backup_path and backup_path.exists())
            self.assertEqual(imported[0]["start"], 0.05)
            self.assertEqual(imported[1]["end"], 1.44)
            self.assertEqual(imported[1]["timing_source"], "nfa-word-ctm")
            self.assertEqual(imported[1]["alignment_engine"], "nvidia/nemo-forced-aligner")
            self.assertEqual(matches[0]["start"], 0.94)
            self.assertEqual(matches[0]["end"], 1.86)

    def test_refine_words_with_nfa_ctm_rejects_word_sequence_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.make_manifest(root)
            words = self.write_words(root)
            import_words(manifest, words, video_id="vid123")
            ctm = root / "vid123.ctm"
            ctm.write_text(
                "\n".join(
                    [
                        "vid123 1 0.050 0.210 This",
                        "vid123 1 0.940 0.500 other",
                        "vid123 1 1.470 0.390 workflow",
                        "vid123 1 2.140 0.320 matters",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "word sequence mismatch"):
                refine_words_with_nfa_ctm(manifest, ctm, video_id="vid123")

    def test_parse_nfa_words_ctm_and_run_command_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctm = root / "words.ctm"
            ctm.write_text("utt 1 1.250 0.500 crazy\nutt 1 1.900 0.250 wild\n", encoding="utf-8")
            align_script = root / "align.py"
            align_script.write_text("# fake\n", encoding="utf-8")
            captured: list[tuple[str, ...]] = []

            def fake_run_command(args: object, **_: object) -> CommandResult:
                command = tuple(str(arg) for arg in args)  # type: ignore[union-attr]
                captured.append(command)
                return CommandResult(command, 0, "", "")

            rows = parse_nfa_words_ctm(ctm)
            with patch("legends_ytdlp.intelligence.run_command", side_effect=fake_run_command):
                result = run_nfa_alignment(
                    root / "manifest.jsonl",
                    root / "out",
                    python_executable="python-nemo",
                    align_script=align_script,
                    pretrained_name="stt_en_fastconformer_hybrid_large_pc",
                    transcribe_device="cpu",
                    viterbi_device="cpu",
                    extra_args=["minimum_timestamp_duration=0.02"],
                )

            self.assertEqual(rows[0]["word"], "crazy")
            self.assertEqual(rows[0]["end"], 1.75)
            self.assertTrue(result.ok)
            self.assertEqual(captured[0][0], "python-nemo")
            self.assertIn("pretrained_name=stt_en_fastconformer_hybrid_large_pc", captured[0])
            self.assertIn("save_output_file_formats=['ctm','ass']", captured[0])
            self.assertIn("minimum_timestamp_duration=0.02", captured[0])

    def test_import_crispasr_json_accepts_full_word_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.make_manifest(root)
            payload = root / "crispasr.json"
            payload.write_text(
                json.dumps(
                    {
                        "crispasr": {"backend": "parakeet", "model": "parakeet-tdt-0.6b-v3-q4_k.gguf"},
                        "transcription": [
                            {
                                "text": "Agentic workflow",
                                "offsets": {"from": 240, "to": 1880},
                                "words": [
                                    {"word": "Agentic", "offsets": {"from": 240, "to": 720}, "confidence": 0.96},
                                    {"word": "workflow", "timestamps": {"from": "00:00:00,760", "to": "00:00:01,880"}},
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            target, count = import_crispasr_json(manifest, payload, video_id="vid123")
            matches = search_words(manifest, "agentic workflow")

            imported = read_jsonl(target)
            self.assertEqual(count, 2)
            self.assertEqual(imported[0]["start"], 0.24)
            self.assertEqual(imported[1]["end"], 1.88)
            self.assertEqual(imported[0]["engine"], "crispasr/parakeet-tdt-0.6b-v3")
            self.assertEqual(imported[0]["timing_source"], "crispasr-word")
            self.assertEqual(imported[0]["asr_backend"], "parakeet")
            self.assertEqual(len(matches), 1)

    def test_import_crispasr_json_splits_single_timed_segment_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.make_manifest(root)
            payload = root / "crispasr.json"
            payload.write_text(
                json.dumps(
                    {
                        "transcription": [
                            {
                                "text": "perfect timestamps",
                                "timestamps": {"from": "00:00:10,000", "to": "00:00:12,000"},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            target, count = import_crispasr_json(manifest, payload, video_id="vid123")
            imported = read_jsonl(target)

            self.assertEqual(count, 2)
            self.assertEqual(imported[0]["word"], "perfect")
            self.assertEqual(imported[0]["start"], 10.0)
            self.assertEqual(imported[0]["timing_source"], "crispasr-segment-split-approximate")
            self.assertEqual(imported[1]["word"], "timestamps")
            self.assertEqual(imported[1]["end"], 12.0)

    def test_import_crispasr_json_combines_token_timings_into_words(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.make_manifest(root)
            payload = root / "crispasr.json"
            payload.write_text(
                json.dumps(
                    {
                        "crispasr": {"backend": "parakeet", "model": "parakeet-tdt-0.6b-v3-q4_k.gguf"},
                        "transcription": [
                            {
                                "text": "Agentic workflow.",
                                "timestamps": {"from": "00:00:00,000", "to": "00:00:02,400"},
                                "tokens": [
                                    {"text": " A", "p": 0.98, "t0": 0, "t1": 16},
                                    {"text": "gen", "p": 0.99, "t0": 16, "t1": 32},
                                    {"text": "tic", "p": 0.97, "t0": 32, "t1": 56},
                                    {"text": " work", "p": 0.96, "t0": 72, "t1": 96},
                                    {"text": "flow", "p": 0.95, "t0": 96, "t1": 136},
                                    {"text": ".", "p": 0.5, "t0": 136, "t1": 160},
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            target, count = import_crispasr_json(manifest, payload, video_id="vid123")
            imported = read_jsonl(target)

            self.assertEqual(count, 2)
            self.assertEqual(imported[0]["word"], "Agentic")
            self.assertEqual(imported[0]["start"], 0.0)
            self.assertEqual(imported[0]["end"], 0.56)
            self.assertEqual(imported[0]["timing_source"], "crispasr-token")
            self.assertEqual(imported[1]["word"], "workflow")
            self.assertEqual(imported[1]["start"], 0.72)
            self.assertEqual(imported[1]["end"], 1.36)

    def test_transcribe_with_crispasr_uses_crispasr_json_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.make_manifest(root)
            media = root / "downloads" / "fixture.mp4"
            captured: dict[str, Path] = {}
            commands: list[tuple[str, ...]] = []

            def fake_import(manifest_path: Path, json_path: Path, **_: object) -> tuple[Path, int]:
                captured["json_path"] = json_path
                return root / "intelligence" / "words" / "vid123.words.jsonl", 3

            def fake_run_command(args: object, **_: object) -> CommandResult:
                command = tuple(str(arg) for arg in args)  # type: ignore[union-attr]
                commands.append(command)
                return CommandResult(command, 0, "", "")

            with (
                patch(
                    "legends_ytdlp.intelligence.find_crispasr",
                    return_value=ToolInfo("crispasr", root / "crispasr.exe", "fake", True, "ok"),
                ),
                patch(
                    "legends_ytdlp.intelligence.extract_audio",
                    return_value=CommandResult(("ffmpeg",), 0, "", ""),
                ),
                patch("legends_ytdlp.intelligence.run_command", side_effect=fake_run_command),
                patch("legends_ytdlp.intelligence.import_crispasr_json", side_effect=fake_import),
            ):
                audio, transcript, words, count, results = transcribe_with_crispasr(
                    manifest,
                    media,
                    video_id="vid123",
                    item_id="vid123",
                    gpu_backend="cuda",
                )

            self.assertEqual(audio.name, "vid123.wav")
            self.assertEqual(transcript.name, "vid123.crispasr.json")
            self.assertEqual(captured["json_path"].name, "vid123.crispasr.json")
            self.assertEqual(words.name, "vid123.words.jsonl")
            self.assertEqual(count, 3)
            self.assertEqual(len(results), 2)
            self.assertIn("--gpu-backend", commands[0])
            self.assertIn("cuda", commands[0])

    def test_transcribe_rejects_conflicting_gpu_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.make_manifest(root)
            media = root / "clip.mp4"
            media.write_bytes(b"fake")

            with patch("legends_ytdlp.intelligence.find_crispasr") as find_crispasr:
                find_crispasr.return_value = ToolInfo(
                    "crispasr",
                    root / "crispasr.exe",
                    None,
                    True,
                    "CrispASR CLI found",
                )

                with self.assertRaisesRegex(ValueError, "--require-gpu cannot be combined with --no-gpu"):
                    transcribe_with_crispasr(
                        manifest,
                        media,
                        video_id="vid123",
                        no_gpu=True,
                        require_gpu=True,
                    )

                with self.assertRaisesRegex(ValueError, "--no-gpu cannot be combined"):
                    transcribe_with_crispasr(
                        manifest,
                        media,
                        video_id="vid123",
                        gpu_backend="cuda",
                        no_gpu=True,
                    )

                with self.assertRaisesRegex(ValueError, "--gpu-backend cpu"):
                    transcribe_with_crispasr(
                        manifest,
                        media,
                        video_id="vid123",
                        gpu_backend="cpu",
                        require_gpu=True,
                    )

    def test_parse_crispasr_diagnostics_reports_cpu_only(self) -> None:
        diagnostics = parse_crispasr_diagnostics(
            """
=== build info ===
  ggml backends : cpu

=== ggml backends + devices ===
  registered backends: 1
    [0] CPU (devices: 1)
  registered devices : 1
    [0] cpu    name=CPU desc=12th Gen Intel(R) Core(TM) i9-12900K mem=71672/130822 MiB id=?
"""
        )

        self.assertEqual(diagnostics.ggml_backends, ["cpu"])
        self.assertFalse(diagnostics.has_gpu_backend)
        self.assertIn("CPU-only", diagnostics.detail)

    def test_parse_crispasr_diagnostics_detects_gpu_backend(self) -> None:
        diagnostics = parse_crispasr_diagnostics(
            """
=== build info ===
  ggml backends : cpu cuda vulkan

=== ggml backends + devices ===
  registered backends: 3
    [0] CUDA (devices: 1)
    [1] Vulkan (devices: 1)
  registered devices : 2
    [0] cuda0  name=NVIDIA GeForce RTX 4090 desc=CUDA mem=20000/24564 MiB id=0
"""
        )

        self.assertTrue(diagnostics.has_gpu_backend)
        self.assertEqual(diagnostics.gpu_backends, ["cuda", "vulkan"])
        self.assertIn("GPU backend", diagnostics.detail)

    def test_clip_plan_clamps_padding_and_requires_media_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.make_manifest(root)
            words = self.write_words(root)
            import_words(manifest, words, video_id="vid123")

            plan_path, plan = make_clip_plan(manifest, "this", pad_start=1.0, pad_end=0.25)

            self.assertTrue(plan_path.exists())
            self.assertEqual(plan["clip_count"], 1)
            self.assertEqual(plan["clips"][0]["start"], 0.0)
            self.assertEqual(plan["clips"][0]["end"], 0.47)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.make_manifest(root, with_media=False)
            words = self.write_words(root)
            import_words(manifest, words, video_id="vid123")

            with self.assertRaisesRegex(ValueError, "media_path"):
                make_clip_plan(manifest, "agentic")

    def test_build_vault_writes_index_and_video_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.make_manifest(root)
            words = self.write_words(root)
            import_words(manifest, words, video_id="vid123")

            vault, pages = build_vault(manifest)

            self.assertEqual(pages, 1)
            self.assertTrue((vault / "index.md").exists())
            self.assertIn("[[vid123]]", (vault / "index.md").read_text(encoding="utf-8"))
            self.assertIn("agentic workflow", (vault / "vid123.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
