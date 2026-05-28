from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse


LEDGER_SCHEMA_VERSION = 1
MEDIA_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def youtube_id_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.endswith("youtu.be"):
        candidate = parsed.path.strip("/").split("/", 1)[0]
        return candidate or None
    if "youtube.com" in host:
        value = parse_qs(parsed.query).get("v", [None])[0]
        return value or None
    return None


def canonical_url_for_entry(entry: dict) -> str:
    webpage_url = entry.get("webpage_url") or entry.get("url")
    if isinstance(webpage_url, str) and webpage_url.startswith(("http://", "https://")):
        return webpage_url
    video_id = entry.get("id")
    if isinstance(video_id, str) and video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return str(webpage_url or "")


def planned_item(url: str, *, position: int, source_url: str | None = None, metadata: dict | None = None) -> dict:
    metadata = metadata or {}
    video_id = metadata.get("id") or youtube_id_from_url(url)
    created = now_iso()
    return {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "position": position,
        "status": metadata.get("status", "planned"),
        "url": url,
        "source_url": source_url or url,
        "id": video_id,
        "title": metadata.get("title"),
        "uploader": metadata.get("uploader") or metadata.get("channel"),
        "duration_seconds": metadata.get("duration"),
        "upload_date": metadata.get("upload_date"),
        "live_status": metadata.get("live_status"),
        "attempts": int(metadata.get("attempts", 0) or 0),
        "warnings": list(metadata.get("warnings", [])),
        "output_path": metadata.get("output_path"),
        "info_json_path": metadata.get("info_json_path"),
        "bytes": metadata.get("bytes"),
        "created": metadata.get("created", created),
        "updated": metadata.get("updated", created),
    }


def planned_items_from_urls(urls: list[str]) -> list[dict]:
    return [planned_item(url, position=index + 1) for index, url in enumerate(urls)]


def item_from_inventory_entry(entry: dict, *, source_url: str, position: int) -> dict:
    url = canonical_url_for_entry(entry)
    return planned_item(
        url,
        position=position,
        source_url=source_url,
        metadata={
            "id": entry.get("id"),
            "title": entry.get("title"),
            "uploader": entry.get("uploader") or entry.get("channel"),
            "duration": entry.get("duration"),
            "upload_date": entry.get("upload_date"),
            "live_status": entry.get("live_status"),
            "status": "inventoried",
        },
    )


def write_item_ledger(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in items)
    path.write_text(text, encoding="utf-8")


def load_item_ledger(path: Path) -> list[dict]:
    if not path.exists():
        return []
    items: list[dict] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line:
            items.append(json.loads(line))
    return items


def archive_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    ids: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        parts = raw_line.strip().split()
        if len(parts) >= 2:
            ids.add(parts[-1])
    return ids


def find_media_for_info(info_json: Path) -> Path | None:
    base = info_json.name.removesuffix(".info.json")
    for candidate in info_json.parent.iterdir():
        candidate_base = candidate.name.removesuffix(candidate.suffix)
        if candidate.is_file() and candidate.suffix.lower() in MEDIA_EXTENSIONS and candidate_base == base:
            return candidate
    return None


def info_items(output: Path) -> list[dict]:
    if not output.exists():
        return []
    items: list[dict] = []
    for path in sorted(output.rglob("*.info.json")):
        try:
            metadata = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        media = find_media_for_info(path)
        item = {
            "id": metadata.get("id"),
            "title": metadata.get("title"),
            "url": metadata.get("webpage_url") or metadata.get("original_url"),
            "uploader": metadata.get("uploader") or metadata.get("channel"),
            "duration_seconds": metadata.get("duration"),
            "upload_date": metadata.get("upload_date"),
            "live_status": metadata.get("live_status"),
            "info_json_path": str(path),
            "output_path": str(media) if media else None,
            "bytes": media.stat().st_size if media else None,
        }
        items.append(item)
    return items


def merge_download_artifacts(items: list[dict], *, archive: Path, output: Path) -> list[dict]:
    merged = [dict(item) for item in items]
    index_by_id = {item.get("id"): index for index, item in enumerate(merged) if item.get("id")}
    index_by_url = {item.get("url"): index for index, item in enumerate(merged) if item.get("url")}
    archived = archive_ids(archive)
    updated_at = now_iso()

    for artifact in info_items(output):
        item_id = artifact.get("id")
        item_url = artifact.get("url")
        index = index_by_id.get(item_id) if item_id else None
        if index is None and item_url:
            index = index_by_url.get(item_url)
        if index is None:
            index = len(merged)
            merged.append(planned_item(str(item_url or ""), position=index + 1, metadata={"id": item_id}))
        item = merged[index]
        for key, value in artifact.items():
            if value is not None:
                item[key] = value
        item["status"] = "downloaded" if artifact.get("output_path") else "metadata_only"
        item["updated"] = updated_at
        if item_id:
            index_by_id[item_id] = index

    for item in merged:
        item_id = item.get("id") or youtube_id_from_url(str(item.get("url", "")))
        if item_id and not item.get("id"):
            item["id"] = item_id
        if item_id in archived and item.get("status") not in {"downloaded", "metadata_only"}:
            item["status"] = "archived"
            item["updated"] = updated_at
    return merged


def summarize_ledger(items: list[dict]) -> dict:
    counts = Counter(str(item.get("status", "unknown")) for item in items)
    return {
        "items": len(items),
        "statuses": dict(sorted(counts.items())),
        "downloaded": counts.get("downloaded", 0),
        "archived": counts.get("archived", 0),
        "warnings": sum(len(item.get("warnings", [])) for item in items),
        "bytes": sum(int(item.get("bytes") or 0) for item in items),
    }


def refresh_item_ledger(manifest: dict) -> dict:
    ledger_value = manifest.get("paths", {}).get("item_ledger")
    if not ledger_value:
        return {"items": 0, "statuses": {}}
    ledger_path = Path(ledger_value)
    output = Path(manifest["paths"]["output"])
    archive = Path(manifest["paths"]["download_archive"])
    items = load_item_ledger(ledger_path)
    if not items:
        urls = list(manifest.get("source_urls", []))
        items = planned_items_from_urls(urls)
    merged = merge_download_artifacts(items, archive=archive, output=output)
    write_item_ledger(ledger_path, merged)
    return summarize_ledger(merged)
