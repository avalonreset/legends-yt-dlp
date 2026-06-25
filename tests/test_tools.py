import unittest
from datetime import date
from pathlib import Path

from slayer_cli.tools import expected_sha256_from_sums, parse_ytdlp_release_date, ytdlp_age_days, ytdlp_stale_detail


class ToolTests(unittest.TestCase):
    def test_expected_sha256_from_sums(self) -> None:
        text = "abc123  yt-dlp.exe\nfff999  other\n"
        self.assertEqual(expected_sha256_from_sums(text, "yt-dlp.exe"), "abc123")

    def test_parse_ytdlp_release_date(self) -> None:
        self.assertEqual(parse_ytdlp_release_date("2026.06.09"), date(2026, 6, 9))
        self.assertEqual(parse_ytdlp_release_date("stable@2026.06.09"), date(2026, 6, 9))
        self.assertIsNone(parse_ytdlp_release_date("nightly"))

    def test_ytdlp_age_days(self) -> None:
        self.assertEqual(ytdlp_age_days("2026.06.09", today=date(2026, 6, 24)), 15)

    def test_ytdlp_stale_detail_after_90_days(self) -> None:
        detail = ytdlp_stale_detail(Path("yt-dlp.exe"), "2026.03.17", today=date(2026, 6, 24))
        self.assertIsNotNone(detail)
        self.assertIn("99 days old", detail or "")
        self.assertIn("yt-dlp update", detail or "")

    def test_ytdlp_stale_detail_allows_current_build(self) -> None:
        detail = ytdlp_stale_detail(Path("yt-dlp.exe"), "2026.06.09", today=date(2026, 6, 24))
        self.assertIsNone(detail)
