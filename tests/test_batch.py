import unittest
from pathlib import Path

from slayer_cli.batch import read_url_file, validate_url, write_ytdlp_config


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
            self.assertNotIn("\\", text)

    def test_read_url_file_ignores_comments_and_blanks(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "urls.txt"
            path.write_text("\n# comment\nhttps://example.com/a\n\nhttps://example.com/b\n", encoding="utf-8")
            self.assertEqual(read_url_file(path), ["https://example.com/a", "https://example.com/b"])
