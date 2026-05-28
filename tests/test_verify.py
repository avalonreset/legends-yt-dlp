import json
import shutil
import tempfile
import unittest
from pathlib import Path

from slayer_cli.batch import REPORTS_DIR
from slayer_cli.verify import summarize_batch, verify_batch


class VerifyTests(unittest.TestCase):
    def test_summarize_and_verify_batch_artifacts_without_probe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "fixture-batch"
            output = root / "downloads"
            output.mkdir(parents=True)
            (output / "one.mp4").write_bytes(b"fake")
            (output / "one.info.json").write_text(
                '{"id":"one","webpage_url":"https://www.youtube.com/watch?v=one","title":"One"}\n',
                encoding="utf-8",
            )
            (output / "two.webm").write_bytes(b"fake")
            (output / "two.info.json").write_text(
                '{"id":"two","webpage_url":"https://www.youtube.com/watch?v=two","title":"Two"}\n',
                encoding="utf-8",
            )
            archive = root / "archive.txt"
            archive.write_text("youtube one\nyoutube two\n", encoding="utf-8")
            ledger = root / "items.jsonl"
            ledger.write_text(
                "\n".join(
                    [
                        '{"id":"one","position":1,"status":"planned","url":"https://www.youtube.com/watch?v=one","warnings":[]}',
                        '{"id":"two","position":2,"status":"planned","url":"https://www.youtube.com/watch?v=two","warnings":[]}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "name": "fixture",
                        "status": "completed",
                        "url_count": 2,
                        "paths": {
                            "output": str(output),
                            "download_archive": str(archive),
                            "item_ledger": str(ledger),
                        },
                        "limits": {},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            report_dir = REPORTS_DIR / root.name
            report_dir.mkdir(parents=True, exist_ok=True)
            (report_dir / "report.json").write_text("{}\n", encoding="utf-8")
            try:
                summary = summarize_batch(manifest)
                self.assertEqual(summary.media_files, 2)
                self.assertEqual(summary.info_json_files, 2)
                self.assertEqual(summary.archive_entries, 2)
                self.assertEqual(summary.report_files, 1)
                self.assertEqual(summary.ledger_items, 2)
                _, checks = verify_batch(manifest, probe=False)
                self.assertTrue(all(check.ok for check in checks))
                refreshed = summarize_batch(manifest)
                self.assertEqual(refreshed.ledger_statuses, {"downloaded": 2})
            finally:
                shutil.rmtree(report_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
