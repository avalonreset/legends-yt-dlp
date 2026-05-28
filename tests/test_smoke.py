import unittest

from slayer_cli.smoke import SMOKE_VIDEOS, smoke_urls


class SmokeTests(unittest.TestCase):
    def test_smoke_urls_are_bounded(self) -> None:
        urls = smoke_urls(2)
        self.assertEqual(len(urls), 2)
        self.assertEqual(urls[0], SMOKE_VIDEOS[0].url)

    def test_smoke_urls_reject_invalid_count(self) -> None:
        with self.assertRaisesRegex(ValueError, "--count"):
            smoke_urls(0)
        with self.assertRaisesRegex(ValueError, "cannot exceed"):
            smoke_urls(len(SMOKE_VIDEOS) + 1)


if __name__ == "__main__":
    unittest.main()
