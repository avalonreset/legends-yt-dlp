import tempfile
import unittest
import shutil
from pathlib import Path

from legends_ytdlp.smoke import SMOKE_VIDEOS, create_custom_smoke_batch, smoke_urls


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

    def test_custom_smoke_batch_accepts_operator_urls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "downloads"

            paths = None
            try:
                paths = create_custom_smoke_batch(
                    urls=["https://www.youtube.com/watch?v=example"],
                    name="custom-smoke-test",
                    output_dir=str(output),
                    max_height=1080,
                )

                self.assertTrue(paths.manifest.exists())
                self.assertEqual(paths.urls.read_text(encoding="utf-8").strip(), "https://www.youtube.com/watch?v=example")
                self.assertIn("Operator-provided smoke-test URL", paths.manifest.read_text(encoding="utf-8"))
            finally:
                if paths:
                    shutil.rmtree(paths.root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
