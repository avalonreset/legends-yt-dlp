import unittest
from pathlib import Path

from slayer_cli.batch import auth_policy_check, classify_run_failure, read_url_file, validate_url, write_ytdlp_config
from slayer_cli.process import CommandResult


class BatchTests(unittest.TestCase):
    def test_validate_url(self) -> None:
        self.assertTrue(validate_url("https://www.youtube.com/@Example"))
        self.assertFalse(validate_url("file:///C:/secret.txt"))

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
            )
            text = config.read_text(encoding="utf-8")
            self.assertIn("--batch-file", text)
            self.assertIn("--ignore-config", text)
            self.assertIn("--no-cookies", text)
            self.assertIn("--no-cookies-from-browser", text)
            self.assertIn('"%(uploader|Unknown)s/%(upload_date>%Y-%m-%d|NA)s - %(title).180B [%(id)s].%(ext)s"', text)
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

    def test_classify_transient_network(self) -> None:
        result = CommandResult(("yt-dlp",), 1, "", "Connection reset by peer")
        self.assertEqual(classify_run_failure(result), "transient-network")
