import json
import unittest
from unittest.mock import patch

from slayer_cli.inventory import create_batch_from_inventory, filter_entries, inventory_items, parse_inventory_json
from slayer_cli.process import CommandResult


class InventoryTests(unittest.TestCase):
    def test_parse_flat_playlist_json_keeps_entries_and_warnings(self) -> None:
        stdout = json.dumps(
            {
                "_type": "playlist",
                "entries": [
                    {"id": "alpha123", "title": "Alpha"},
                    "not an entry",
                    {"id": "bravo456", "title": "Bravo"},
                ],
            }
        )
        stderr = "WARNING: skipped unavailable video\nERROR: ignored here\nwarning: lower-case warning"

        result = parse_inventory_json("https://www.youtube.com/@legends/videos", stdout, stderr)

        self.assertEqual(result.source_url, "https://www.youtube.com/@legends/videos")
        self.assertEqual([entry["id"] for entry in result.entries], ["alpha123", "bravo456"])
        self.assertEqual(
            result.warnings,
            ("WARNING: skipped unavailable video", "warning: lower-case warning"),
        )

    def test_filter_entries_by_live_status(self) -> None:
        entries = [
            {"id": "alpha123", "live_status": "not_live"},
            {"id": "bravo456", "live_status": "is_live"},
            {"id": "charlie789", "live_status": "was_live"},
            {"id": "delta000"},
        ]

        filtered = filter_entries(entries, live_statuses={"not_live", "was_live"})

        self.assertEqual([entry["id"] for entry in filtered], ["alpha123", "charlie789"])

    def test_inventory_items_create_canonical_urls_after_filtering(self) -> None:
        result = parse_inventory_json(
            "https://www.youtube.com/@legends/videos",
            json.dumps(
                {
                    "entries": [
                        {
                            "id": "alpha123",
                            "title": "Alpha",
                            "uploader": "Legends",
                            "duration": 60,
                            "upload_date": "20260528",
                            "live_status": "not_live",
                        },
                        {
                            "id": "bravo456",
                            "title": "Bravo",
                            "webpage_url": "https://www.youtube.com/watch?v=bravo456&feature=share",
                            "live_status": "is_live",
                        },
                    ]
                }
            ),
        )

        items = inventory_items(result, live_statuses={"not_live"})

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["position"], 1)
        self.assertEqual(items[0]["status"], "inventoried")
        self.assertEqual(items[0]["source_url"], "https://www.youtube.com/@legends/videos")
        self.assertEqual(items[0]["url"], "https://www.youtube.com/watch?v=alpha123")
        self.assertEqual(items[0]["id"], "alpha123")
        self.assertEqual(items[0]["title"], "Alpha")
        self.assertEqual(items[0]["uploader"], "Legends")
        self.assertEqual(items[0]["duration_seconds"], 60)

    def test_create_batch_from_inventory_pauses_on_source_warning(self) -> None:
        result = CommandResult(("yt-dlp",), 0, "WARNING: HTTP Error 429: Too Many Requests", "")

        with patch("slayer_cli.inventory.run_ytdlp_inventory", return_value=result):
            with self.assertRaisesRegex(RuntimeError, "Source-side warning"):
                create_batch_from_inventory(
                    source_url="https://www.youtube.com/@legends/videos",
                    rights_basis="fixture",
                    name="should-not-create",
                    max_items=1,
                )


if __name__ == "__main__":
    unittest.main()
