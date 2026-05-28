import json
import tempfile
import unittest
from pathlib import Path

from slayer_cli.ledger import (
    load_item_ledger,
    merge_download_artifacts,
    planned_items_from_urls,
    summarize_ledger,
    write_item_ledger,
)


class LedgerTests(unittest.TestCase):
    def test_planned_items_extract_youtube_ids_and_preserve_order(self) -> None:
        urls = [
            "https://www.youtube.com/watch?v=alpha123&list=playlist",
            "https://youtu.be/bravo456?si=share",
            "https://example.com/not-youtube",
        ]

        items = planned_items_from_urls(urls)

        self.assertEqual([item["position"] for item in items], [1, 2, 3])
        self.assertEqual([item["url"] for item in items], urls)
        self.assertEqual([item["id"] for item in items], ["alpha123", "bravo456", None])
        self.assertTrue(all(item["status"] == "planned" for item in items))

    def test_jsonl_roundtrip(self) -> None:
        items = [
            {
                "schema_version": 1,
                "position": 1,
                "status": "planned",
                "url": "https://www.youtube.com/watch?v=alpha123",
                "id": "alpha123",
                "warnings": [],
            },
            {
                "schema_version": 1,
                "position": 2,
                "status": "archived",
                "url": "https://www.youtube.com/watch?v=bravo456",
                "id": "bravo456",
                "warnings": ["already archived"],
            },
        ]

        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = Path(tmp) / "nested" / "items.jsonl"
            write_item_ledger(ledger_path, items)

            self.assertEqual(load_item_ledger(ledger_path), items)
            self.assertEqual(len(ledger_path.read_text(encoding="utf-8").splitlines()), 2)

    def test_merge_download_artifacts_updates_media_and_archive_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "downloads"
            output.mkdir()
            archive = root / "archive.txt"
            archive.write_text("youtube bravo456\n", encoding="utf-8")

            info = output / "Episode One [alpha123].info.json"
            media = output / "Episode One [alpha123].mp4"
            info.write_text(
                json.dumps(
                    {
                        "id": "alpha123",
                        "title": "Episode One",
                        "webpage_url": "https://www.youtube.com/watch?v=alpha123",
                        "uploader": "Legends",
                        "duration": 123,
                        "upload_date": "20260528",
                        "live_status": "not_live",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            media.write_bytes(b"fake media")

            items = planned_items_from_urls(
                [
                    "https://www.youtube.com/watch?v=alpha123",
                    "https://www.youtube.com/watch?v=bravo456",
                ]
            )

            merged = merge_download_artifacts(items, archive=archive, output=output)

            by_id = {item["id"]: item for item in merged}
            self.assertEqual(by_id["alpha123"]["status"], "downloaded")
            self.assertEqual(by_id["alpha123"]["title"], "Episode One")
            self.assertEqual(by_id["alpha123"]["output_path"], str(media))
            self.assertEqual(by_id["alpha123"]["info_json_path"], str(info))
            self.assertEqual(by_id["alpha123"]["bytes"], len(b"fake media"))
            self.assertEqual(by_id["bravo456"]["status"], "archived")

            summary = summarize_ledger(merged)
            self.assertEqual(summary["items"], 2)
            self.assertEqual(summary["downloaded"], 1)
            self.assertEqual(summary["archived"], 1)
            self.assertEqual(summary["bytes"], len(b"fake media"))


if __name__ == "__main__":
    unittest.main()
