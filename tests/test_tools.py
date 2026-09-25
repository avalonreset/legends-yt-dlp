import unittest
from datetime import date
from pathlib import Path

from legends_ytdlp.tools import compare_ytdlp_versions, expected_sha256_from_sums, fetch_upstream_ytdlp_version, parse_ytdlp_release_date, ytdlp_age_days, ytdlp_stale_detail


class ToolTests(unittest.TestCase):
    def test_expected_sha256_from_sums(self) -> None:
        text = "abc123  yt-dlp.exe\nfff999  other\n"
        self.assertEqual(expected_sha256_from_sums(text, "yt-dlp.exe"), "abc123")

    def test_parse_ytdlp_release_date(self) -> None:
        self.assertEqual(parse_ytdlp_release_date("2026.06.09"), date(2026, 6, 9))
        self.assertEqual(parse_ytdlp_release_date("stable@2026.06.09"), date(2026, 6, 9))
        self.assertIsNone(parse_ytdlp_release_date("nightly"))

    def test_parse_ytdlp_release_date_nightly_build(self) -> None:
        self.assertEqual(parse_ytdlp_release_date("2026.09.24.123456"), date(2026, 9, 24))

    def test_compare_ytdlp_versions(self) -> None:
        self.assertEqual(compare_ytdlp_versions("2026.08.19", "2026.08.19"), "current")
        self.assertEqual(compare_ytdlp_versions("2026.03.17", "2026.08.19"), "behind")
        self.assertEqual(compare_ytdlp_versions("2026.09.24.123456", "2026.08.19"), "ahead")
        self.assertEqual(compare_ytdlp_versions(None, "2026.08.19"), "unknown")
        self.assertEqual(compare_ytdlp_versions("nightly", "2026.08.19"), "unknown")

    def test_fetch_upstream_ytdlp_version(self) -> None:
        import io
        from unittest.mock import patch

        payload = io.BytesIO(b'{"tag_name": "2026.08.19"}')
        with patch("legends_ytdlp.tools.urllib.request.urlopen") as opened:
            opened.return_value.__enter__.return_value.read.return_value = payload.read()
            self.assertEqual(fetch_upstream_ytdlp_version(), "2026.08.19")

    def test_fetch_upstream_ytdlp_version_rejects_nonstable_tag(self) -> None:
        from unittest.mock import patch

        with patch("legends_ytdlp.tools.urllib.request.urlopen") as opened:
            opened.return_value.__enter__.return_value.read.return_value = b'{"tag_name": "latest"}'
            with self.assertRaises(RuntimeError):
                fetch_upstream_ytdlp_version()

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
