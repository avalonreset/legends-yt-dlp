import unittest

from slayer_cli.tools import expected_sha256_from_sums


class ToolTests(unittest.TestCase):
    def test_expected_sha256_from_sums(self) -> None:
        text = "abc123  yt-dlp.exe\nfff999  other\n"
        self.assertEqual(expected_sha256_from_sums(text, "yt-dlp.exe"), "abc123")

