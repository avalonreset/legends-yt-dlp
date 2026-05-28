import json
import tempfile
import unittest
from pathlib import Path

from slayer_cli.intelligence import (
    build_vault,
    import_crispasr_json,
    import_words,
    init_intelligence,
    intelligence_paths,
    make_clip_plan,
    read_jsonl,
    search_words,
)


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
