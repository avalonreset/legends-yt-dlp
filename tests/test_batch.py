import unittest
import json
from pathlib import Path

from slayer_cli.batch import (
    auth_policy_check,
    classify_run_failure,
    classify_success,
    create_batch_from_urls,
    preflight_batch,
    read_url_file,
    run_status,
    validate_url,
    write_run_report,
    write_ytdlp_config,
)
from slayer_cli.ledger import load_item_ledger
from slayer_cli.process import CommandResult


class BatchTests(unittest.TestCase):
    def test_validate_url(self) -> None:
        self.assertTrue(validate_url("https://www.youtube.com/@Example"))
        self.assertFalse(validate_url("file:///C:/secret.txt"))

    def test_batch_plan_rejects_invalid_limits(self) -> None:
        with self.assertRaisesRegex(ValueError, "--max-height"):
            create_batch_from_urls(
                urls=["https://www.youtube.com/watch?v=abc123"],
                rights_basis="fixture",
                max_height=0,
            )
        with self.assertRaisesRegex(ValueError, "--max-downloads"):
            create_batch_from_urls(
                urls=["https://www.youtube.com/watch?v=abc123"],
                rights_basis="fixture",
                max_downloads=0,
            )

    def test_batch_plan_writes_item_ledger_and_rights_evidence(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rights = root / "rights-note.md"
            rights.write_text("authorized fixture\n", encoding="utf-8")
            paths = create_batch_from_urls(
                urls=[
                    "https://www.youtube.com/watch?v=alpha123",
                    "https://youtu.be/bravo456",
                ],
                rights_basis="fixture",
                name="ledger-rights-fixture",
                output_dir=str(root / "out"),
                rights_file=str(rights),
            )
            try:
                manifest = paths.manifest.read_text(encoding="utf-8")
                self.assertTrue(paths.ledger.exists())
                self.assertIn('"item_ledger"', manifest)
                self.assertIn('"rights_evidence"', manifest)
                items = load_item_ledger(paths.ledger)
                self.assertEqual([item["id"] for item in items], ["alpha123", "bravo456"])
                self.assertTrue((paths.root / "rights" / rights.name).exists())
                self.assertTrue((root / "out").is_dir())
                self.assertTrue((root / "out" / "ledger-rights-fixture").is_dir())
            finally:
                import shutil

                shutil.rmtree(paths.root, ignore_errors=True)

    def test_batch_plan_allows_missing_rights_metadata(self) -> None:
        import tempfile
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_batch_from_urls(
                urls=["https://www.youtube.com/watch?v=alpha123"],
                name="no-rights-prompt-fixture",
                output_dir=str(root / "out"),
            )
            try:
                manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
                self.assertIsNone(manifest["rights_basis"])

                with patch("slayer_cli.batch.run_doctor", return_value=[]):
                    checks = preflight_batch(paths.manifest, require_connected=False, production=False)
                self.assertNotIn("rights basis", [check.name for check in checks])
            finally:
                import shutil

                shutil.rmtree(paths.root, ignore_errors=True)

    def test_multi_url_plan_auto_uses_single_batch_folder(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_batch_from_urls(
                urls=[
                    "https://x.com/i/status/111",
                    "https://x.com/i/status/222",
                ],
                rights_basis="fixture",
                name="mixed-links",
                output_dir=str(root / "downloads"),
            )
            try:
                manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
                config = paths.config.read_text(encoding="utf-8")

                self.assertEqual(manifest["folder_policy"]["effective"], "batch")
                self.assertEqual(Path(manifest["paths"]["output"]), root / "downloads" / "mixed-links")
                self.assertIn(
                    '"%(upload_date>%Y-%m-%d|NA)s - %(uploader|Unknown)s - %(title).180B [%(id)s].%(ext)s"',
                    config,
                )
                self.assertNotIn('"%(uploader|Unknown)s/%(upload_date>%Y-%m-%d|NA)s', config)
            finally:
                import shutil

                shutil.rmtree(paths.root, ignore_errors=True)

    def test_inventory_items_auto_keep_uploader_folders(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_batch_from_urls(
                urls=["https://www.youtube.com/watch?v=alpha123"],
                rights_basis="fixture",
                name="channel-fixture",
                output_dir=str(root / "downloads"),
                items=[{"id": "alpha123", "position": 1, "status": "inventoried", "url": "https://www.youtube.com/watch?v=alpha123"}],
            )
            try:
                manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
                config = paths.config.read_text(encoding="utf-8")

                self.assertEqual(manifest["folder_policy"]["effective"], "by-uploader")
                self.assertEqual(Path(manifest["paths"]["output"]), root / "downloads")
                self.assertIn('"%(uploader|Unknown)s/%(upload_date>%Y-%m-%d|NA)s', config)
            finally:
                import shutil

                shutil.rmtree(paths.root, ignore_errors=True)

    def test_ytdlp_config_uses_forward_slash_paths(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "yt-dlp.conf"
            write_ytdlp_config(
                config,
                root / "urls.txt",
                root / "archive.txt",
                root / "downloads",
                root / "tmp",
                max_height=360,
                max_downloads=1,
                max_filesize="50M",
            )
            text = config.read_text(encoding="utf-8")
            self.assertIn("--batch-file", text)
            self.assertIn("--ignore-config", text)
            self.assertIn("--no-cookies", text)
            self.assertIn("--no-cookies-from-browser", text)
            self.assertIn('"%(uploader|Unknown)s/%(upload_date>%Y-%m-%d|NA)s - %(title).180B [%(id)s].%(ext)s"', text)
            self.assertIn('"bestvideo[height<=360]+bestaudio/best[height<=360]/best"', text)
            self.assertIn("--max-downloads\n1", text)
            self.assertIn("--max-filesize\n\"50M\"", text)
            self.assertNotIn("\\", text)

    def test_auth_policy_rejects_browser_cookies(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "yt-dlp.conf"
            config.write_text("--ignore-config\n--no-cookies\n--cookies-from-browser\nchrome\n", encoding="utf-8")
            check = auth_policy_check(config)
            self.assertFalse(check.ok)
            self.assertIn("--cookies-from-browser", check.detail)

    def test_auth_policy_accepts_generated_anonymous_config(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "yt-dlp.conf"
            write_ytdlp_config(
                config,
                root / "urls.txt",
                root / "archive.txt",
                root / "downloads",
                root / "tmp",
            )
            self.assertTrue(auth_policy_check(config).ok)

    def test_read_url_file_ignores_comments_and_blanks(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "urls.txt"
            path.write_text("\n# comment\nhttps://example.com/a\n\nhttps://example.com/b\n", encoding="utf-8")
            self.assertEqual(read_url_file(path), ["https://example.com/a", "https://example.com/b"])

    def test_classify_source_block(self) -> None:
        result = CommandResult(("yt-dlp",), 1, "", "HTTP Error 429: Too Many Requests")
        self.assertEqual(classify_run_failure(result), "source-block")

    def test_classify_ignores_login_text_in_successful_metadata_stdout_when_stderr_has_real_error(self) -> None:
        result = CommandResult(("yt-dlp",), 1, '{"requires_login": false}', "ERROR: [generic] '-' is not a valid URL")
        self.assertEqual(classify_run_failure(result), "unknown")

    def test_classify_metadata_stdout_does_not_trigger_login_block(self) -> None:
        result = CommandResult(("yt-dlp",), 1, '{"requires_login": false}', "")
        self.assertEqual(classify_run_failure(result), "unknown")

    def test_classify_max_downloads_return_code_as_limit_reached(self) -> None:
        result = CommandResult(("yt-dlp",), 101, '{"requires_login": false}', "")
        self.assertEqual(classify_run_failure(result), "limit-reached")

    def test_classify_transient_network(self) -> None:
        result = CommandResult(("yt-dlp",), 1, "", "Connection reset by peer")
        self.assertEqual(classify_run_failure(result), "transient-network")

    def test_classify_success_with_source_warning(self) -> None:
        result = CommandResult(("yt-dlp",), 0, "WARNING: HTTP Error 429: Too Many Requests", "")
        self.assertEqual(classify_success(result), "source-warning")

    def test_run_status_maps_outcomes(self) -> None:
        self.assertEqual(run_status(dry_run=True, returncode=0, category="ok"), "dry_run_passed")
        self.assertEqual(run_status(dry_run=False, returncode=0, category="ok"), "completed")
        self.assertEqual(run_status(dry_run=False, returncode=0, category="source-warning"), "completed_with_source_warnings")
        self.assertEqual(run_status(dry_run=False, returncode=101, category="limit-reached"), "limit_reached")
        self.assertEqual(run_status(dry_run=False, returncode=1, category="source-block"), "paused_source_block")
        self.assertEqual(run_status(dry_run=False, returncode=1, category="transient-network"), "paused_network_failure")

    def test_write_run_report_updates_manifest_without_stdout_payload(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "manifest.json"
            output = root / "downloads"
            output.mkdir()
            archive = root / "archive.txt"
            ledger = root / "items.jsonl"
            ledger.write_text(
                '{"id":"alpha123","position":1,"status":"planned","url":"https://www.youtube.com/watch?v=alpha123","warnings":[]}\n',
                encoding="utf-8",
            )
            manifest.write_text(
                f'{{"name":"fixture","status":"planned","source_urls":["https://www.youtube.com/watch?v=alpha123"],"paths":{{"output":"{output.as_posix()}","download_archive":"{archive.as_posix()}","item_ledger":"{ledger.as_posix()}"}}}}\n',
                encoding="utf-8",
            )
            result = CommandResult(("yt-dlp",), 0, "large stdout", "")
            report = write_run_report(
                manifest,
                dry_run=True,
                result=result,
                category="ok",
                started="2026-05-27T00:00:00",
                ended="2026-05-27T00:00:01",
            )
            self.assertTrue(report.exists())
            self.assertIn('"status": "dry_run_passed"', manifest.read_text(encoding="utf-8"))
            self.assertNotIn("large stdout", report.read_text(encoding="utf-8"))
            self.assertIn('"ledger"', report.read_text(encoding="utf-8"))
            import shutil

            shutil.rmtree(report.parent)
