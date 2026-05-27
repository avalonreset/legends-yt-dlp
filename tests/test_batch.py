import unittest
from pathlib import Path

from slayer_cli.batch import validate_url, write_ytdlp_config


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

