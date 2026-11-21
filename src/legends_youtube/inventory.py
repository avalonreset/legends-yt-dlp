"""Low-quota channel inventory, ISO-8601 duration parsing, and video forensics."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .api import (
    MAX_RESPONSE_BYTES,
    YouTubeClient,
    YouTubeError,
    build_safe_opener,
    scrub_secrets,
    validate_channel_id,
    validate_video_id,
)

ISO_DURATION_RE = re.compile(
    r"^P(?:(?P<weeks>\d+)W)?(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)
URL_EXTRACT_RE = re.compile(r"https?://[^\s<>\"'\]]+")
CHAPTER_LINE_RE = re.compile(r"^\s*(?P<ts>(?:\d{1,2}:)?\d{1,2}:\d{2})\s+(?P<label>\S.*)$")
MIDROLL_MIN_SECONDS = 8 * 60
SHORTS_MAX_SECONDS = 60
MAX_OEMBED_BYTES = 256 * 1024


def parse_iso8601_duration(duration_str: str) -> int:
    """Convert an ISO-8601 YouTube duration (e.g. 'PT12M34S', 'PT1H5M', 'PT45S', 'P1W') into total seconds."""
    cleaned = (duration_str or "").strip().upper()
    if not cleaned:
        return 0
    match = ISO_DURATION_RE.fullmatch(cleaned)
    if not match:
        return 0
    weeks = int(match.group("weeks") or 0)
    days = int(match.group("days") or 0)
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    return weeks * 604800 + days * 86400 + hours * 3600 + minutes * 60 + seconds


def extract_urls(text: str) -> list[str]:
    """Extract all HTTP(S) URLs from a video description, stripping trailing punctuation while preserving balanced parentheses."""
    urls: list[str] = []
    for raw in URL_EXTRACT_RE.findall(text or ""):
        cleaned = raw
        while cleaned:
            if cleaned[-1] in ".,;:!?'\"":
                cleaned = cleaned[:-1]
            elif cleaned.endswith(")") and cleaned.count(")") > cleaned.count("("):
                cleaned = cleaned[:-1]
            else:
                break
        if cleaned:
            urls.append(cleaned)
    return urls


def extract_chapter_lines(description: str) -> list[dict[str, Any]]:
    """Extract timestamped chapter lines from a video description."""
    chapters: list[dict[str, Any]] = []
    for line in (description or "").splitlines():
        match = CHAPTER_LINE_RE.match(line)
        if not match:
            continue
        ts_raw = match.group("ts")
        label = match.group("label").strip()
        parts = [int(p) for p in ts_raw.split(":")]
        if len(parts) == 2:
            seconds = parts[0] * 60 + parts[1]
        else:
            seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
        chapters.append({"timestamp": ts_raw, "seconds": seconds, "title": label})
    return chapters


def normalize_api_video_item(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize a YouTube Data API v3 `videos.list` resource into a deterministic inventory record."""
    vid = str(item.get("id") or "").strip()
    etag = str(item.get("etag") or "").strip()
    snippet = item.get("snippet") if isinstance(item.get("snippet"), dict) else {}
    status = item.get("status") if isinstance(item.get("status"), dict) else {}
    content = item.get("contentDetails") if isinstance(item.get("contentDetails"), dict) else {}
    stats = item.get("statistics") if isinstance(item.get("statistics"), dict) else {}

    title = str(snippet.get("title") or "")
    description = str(snippet.get("description") or "")
    tags = [str(t) for t in (snippet.get("tags") or []) if isinstance(t, str)]
    category_id = str(snippet.get("categoryId") or "27")
    default_lang = str(snippet.get("defaultLanguage") or "")
    default_audio_lang = str(snippet.get("defaultAudioLanguage") or "")
    published_at = str(snippet.get("publishedAt") or "")
    channel_id = str(snippet.get("channelId") or "")
    channel_title = str(snippet.get("channelTitle") or "")

    duration_iso = str(content.get("duration") or "")
    length_seconds = parse_iso8601_duration(duration_iso)
    has_custom_caption = str(content.get("caption") or "").lower() == "true"
    definition = str(content.get("definition") or "hd")

    privacy_status = str(status.get("privacyStatus") or "private")
    made_for_kids = bool(status.get("selfDeclaredMadeForKids") or status.get("madeForKids"))
    embeddable = bool(status.get("embeddable", True))
    publish_at = str(status.get("publishAt") or "")

    lower_combined = f"{title} {description}".lower()
    is_short = (0 < length_seconds <= SHORTS_MAX_SECONDS) or ("#shorts" in lower_combined) or ("#short" in lower_combined)
    fmt = "short" if is_short else "long"
    midroll_eligible = (not is_short) and (length_seconds >= MIDROLL_MIN_SECONDS)

    urls = extract_urls(description)
    chapters = extract_chapter_lines(description)

    views = int(stats.get("viewCount") or 0)
    likes = int(stats.get("likeCount") or 0)
    comments = int(stats.get("commentCount") or 0)

    return {
        "video_id": vid,
        "etag": etag,
        "channel_id": channel_id,
        "channel_title": channel_title,
        "title": title,
        "description": description,
        "published_at": published_at,
        "publish_at": publish_at or None,
        "privacy_status": privacy_status,
        "format": fmt,
        "duration_iso": duration_iso,
        "length_seconds": length_seconds,
        "midroll_eligible": midroll_eligible,
        "definition": definition,
        "has_captions": has_custom_caption,
        "made_for_kids": made_for_kids,
        "embeddable": embeddable,
        "category_id": category_id,
        "default_language": default_lang or None,
        "default_audio_language": default_audio_lang or None,
        "tags": tags,
        "tag_count": len(tags),
        "description_length": len(description),
        "urls": urls,
        "url_count": len(urls),
        "chapters": chapters,
        "chapter_count": len(chapters),
        "views": views,
        "likes": likes,
        "comments": comments,
    }


def fetch_channel_inventory(
    client: YouTubeClient,
    *,
    channel_id: str | None = None,
    mine: bool = False,
    max_videos: int = 500,
) -> dict[str, Any]:
    """Fetch a low-quota channel inventory via the uploads playlist (2 quota units per 50 videos)."""
    if channel_id:
        validate_channel_id(channel_id)
    channel = client.get_channel(channel_id=channel_id, mine=mine)
    resolved_channel_id = str(channel.get("id") or "")
    if channel_id and resolved_channel_id != channel_id:
        raise YouTubeError(
            f"Channel ID mismatch: requested {channel_id}, API returned {resolved_channel_id}."
        )
    snippet = channel.get("snippet") or {}
    stats = channel.get("statistics") or {}
    content = channel.get("contentDetails") or {}
    related = content.get("relatedPlaylists") or {}
    uploads_playlist = str(related.get("uploads") or "")
    if not uploads_playlist:
        raise YouTubeError(f"Channel {resolved_channel_id} did not return a relatedPlaylists.uploads ID.")

    video_ids = client.list_playlist_video_ids(uploads_playlist, max_items=max_videos)
    raw_items = client.list_videos_by_ids(video_ids) if video_ids else []
    normalized = [normalize_api_video_item(item) for item in raw_items]

    by_privacy: dict[str, int] = {"public": 0, "unlisted": 0, "private": 0}
    by_format: dict[str, int] = {"long": 0, "short": 0}
    for rec in normalized:
        priv = rec["privacy_status"]
        by_privacy[priv] = by_privacy.get(priv, 0) + 1
        fmt = rec["format"]
        by_format[fmt] = by_format.get(fmt, 0) + 1

    return {
        "channel": {
            "channel_id": resolved_channel_id,
            "title": str(snippet.get("title") or ""),
            "custom_url": str(snippet.get("customUrl") or ""),
            "uploads_playlist_id": uploads_playlist,
            "subscriber_count": int(stats.get("subscriberCount") or 0),
            "view_count": int(stats.get("viewCount") or 0),
            "reported_video_count": int(stats.get("videoCount") or 0),
        },
        "summary": {
            "inventoried_count": len(normalized),
            "by_privacy": by_privacy,
            "by_format": by_format,
            "midroll_eligible_long_count": sum(1 for r in normalized if r["midroll_eligible"]),
            "missing_description_count": sum(1 for r in normalized if not r["description"].strip()),
        },
        "videos": normalized,
    }


def inspect_videos(client: YouTubeClient, video_ids: list[str]) -> dict[str, Any]:
    """Inspect a specific list of YouTube video IDs."""
    cleaned = [validate_video_id(v) for v in video_ids if v.strip()]
    if not cleaned:
        raise YouTubeError("Provide at least one valid 11-character YouTube video ID.")
    raw_items = client.list_videos_by_ids(cleaned)
    found_map = {str(item.get("id")): normalize_api_video_item(item) for item in raw_items}
    ordered = [found_map[vid] for vid in cleaned if vid in found_map]
    missing = [vid for vid in cleaned if vid not in found_map]
    return {
        "requested_count": len(cleaned),
        "found_count": len(ordered),
        "missing_video_ids": missing,
        "videos": ordered,
    }


def _extract_balanced_json(text: str, marker: str) -> dict[str, Any] | None:
    """Extract a balanced JSON object following a JavaScript variable marker (e.g. ytInitialPlayerResponse)."""
    pos = text.find(marker)
    if pos < 0:
        return None
    brace_start = text.find("{", pos + len(marker))
    if brace_start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for idx in range(brace_start, len(text)):
        ch = text[idx]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    parsed = json.loads(text[brace_start : idx + 1])
                    return parsed if isinstance(parsed, dict) else None
                except json.JSONDecodeError:
                    return None
    return None


def public_video_readback(video_id: str, *, timeout: float = 20.0) -> dict[str, Any]:
    """Perform a 0-quota, 0-credential anonymous public readback via watch page ytInitialPlayerResponse + oEmbed."""
    vid = validate_video_id(video_id)
    opener = build_safe_opener()
    watch_url = f"https://www.youtube.com/watch?v={urllib.parse.quote(vid)}&hl=en"
    watch_req = urllib.request.Request(
        watch_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/136.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with opener.open(watch_req, timeout=timeout) as resp:
            watch_status = getattr(resp, "status", 200)
            raw_html = resp.read(MAX_RESPONSE_BYTES + 1)
            if len(raw_html) > MAX_RESPONSE_BYTES:
                raise YouTubeError(f"YouTube watch page response exceeded {MAX_RESPONSE_BYTES} bytes.")
            html = raw_html.decode("utf-8", errors="replace")
    except YouTubeError:
        raise
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        raise YouTubeError(f"Failed to fetch YouTube watch page for {vid}: {scrub_secrets(str(exc))}") from None

    player: dict[str, Any] | None = None
    for marker in ("var ytInitialPlayerResponse = ", '"ytInitialPlayerResponse":'):
        player = _extract_balanced_json(html, marker)
        if player:
            break
    if not player:
        raise YouTubeError(f"YouTube watch page for {vid} did not expose ytInitialPlayerResponse.")

    oembed_url = "https://www.youtube.com/oembed?" + urllib.parse.urlencode(
        {"url": f"https://www.youtube.com/watch?v={vid}", "format": "json"}
    )
    oembed_req = urllib.request.Request(
        oembed_url,
        headers={"User-Agent": "legends-youtube-public-readback/0.1.1"},
    )
    oembed_status = 0
    oembed_data: dict[str, Any] = {}
    try:
        with opener.open(oembed_req, timeout=timeout) as oresp:
            oembed_status = getattr(oresp, "status", 200)
            raw_oembed = oresp.read(MAX_OEMBED_BYTES + 1)
            if len(raw_oembed) <= MAX_OEMBED_BYTES:
                parsed_oembed = json.loads(raw_oembed.decode("utf-8", errors="replace"))
                if isinstance(parsed_oembed, dict):
                    oembed_data = parsed_oembed
    except Exception:
        oembed_status = 0

    playability = player.get("playabilityStatus") or {}
    details = player.get("videoDetails") or {}
    microformat = (player.get("microformat") or {}).get("playerMicroformatRenderer") or {}
    is_public = (
        watch_status == 200
        and oembed_status == 200
        and playability.get("status") == "OK"
        and details.get("videoId") == vid
    )
    length_sec = int(details.get("lengthSeconds") or 0)
    return {
        "video_id": vid,
        "quota_cost": 0,
        "anonymous_public": is_public,
        "watch_http_status": watch_status,
        "oembed_http_status": oembed_status,
        "playability_status": str(playability.get("status") or ""),
        "channel_id": str(details.get("channelId") or ""),
        "channel_title": str(details.get("author") or oembed_data.get("author_name") or ""),
        "title": str(details.get("title") or oembed_data.get("title") or ""),
        "description": str(details.get("shortDescription") or ""),
        "published_date": str(microformat.get("publishDate") or ""),
        "length_seconds": length_sec,
        "is_short_duration": 0 < length_sec <= SHORTS_MAX_SECONDS,
        "is_live_content": bool(details.get("isLiveContent")),
        "embeddable": bool((microformat.get("embed") or {}).get("iframeUrl")),
    }

