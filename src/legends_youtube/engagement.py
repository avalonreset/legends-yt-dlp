"""Comment triage, playlist orphan/duplicate auditing, and Shorts-to-Long-Form funnel diagnostics."""
from __future__ import annotations

import re
from typing import Any

from .api import YouTubeClient, validate_channel_id, validate_video_id

TIMESTAMP_REF_RE = re.compile(r"\b(?:\d{1,2}:)?\d{1,2}:\d{2}\b")
URL_SPAM_RE = re.compile(r"(?:https?://|whatsapp|telegram|t\.me/|crypto|usdt|forex)", re.IGNORECASE)
QUESTION_CUE_RE = re.compile(
    r"(?:\?|\b(?:how do|how can|can you|could you|what is|which one|would you|tutorial on|video on)\b)",
    re.IGNORECASE,
)


def _safe_int(val: Any, label: str = "integer") -> int:
    if val is None or val == "":
        return 0
    if isinstance(val, bool):
        raise ValueError(f"Invalid {label}: expected integer, got bool.")
    try:
        return int(val)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {label}: {val!r}") from None


def normalize_comment_thread_item(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize a YouTube Data API v3 commentThreads.list item or flat comment dict."""
    if not isinstance(item, dict):
        raise ValueError("Comment item must be a JSON object.")
    if "snippet" in item and isinstance(item["snippet"], dict):
        top_snippet = item["snippet"]
        top_lvl = top_snippet.get("topLevelComment")
        top_lvl_dict = top_lvl if isinstance(top_lvl, dict) else {}
        inner_snip = top_lvl_dict.get("snippet")
        top_comment = inner_snip if isinstance(inner_snip, dict) else top_snippet
        thread_id = str(item.get("id") or "")
        video_id = str(top_snippet.get("videoId") or top_comment.get("videoId") or "")
        reply_count = _safe_int(top_snippet.get("totalReplyCount"), "totalReplyCount")
        author = str(top_comment.get("authorDisplayName") or "")
        text = str(top_comment.get("textOriginal") or top_comment.get("textDisplay") or "")
        likes = _safe_int(top_comment.get("likeCount"), "likeCount")
        published_at = str(top_comment.get("publishedAt") or "")
    else:
        thread_id = str(item.get("comment_id") or item.get("id") or "")
        video_id = str(item.get("video_id") or "")
        reply_count = _safe_int(item.get("reply_count"), "reply_count")
        author = str(item.get("author") or "")
        text = str(item.get("text") or "")
        likes = _safe_int(item.get("like_count") if "like_count" in item else item.get("likes"), "like_count")
        published_at = str(item.get("published_at") or "")

    return {
        "comment_id": thread_id,
        "video_id": video_id,
        "author": author,
        "text": text.strip(),
        "like_count": likes,
        "reply_count": reply_count,
        "published_at": published_at,
    }


def triage_comments(raw_items: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify viewer comments into questions/video ideas, timestamp citations, high-signal praise, and spam candidates."""
    if not isinstance(raw_items, list):
        raise ValueError("Comments payload must be a JSON list.")
    for item in raw_items:
        if not isinstance(item, dict):
            raise ValueError("Each comment entry must be a JSON object.")
    questions: list[dict[str, Any]] = []
    timestamp_notes: list[dict[str, Any]] = []
    high_signal: list[dict[str, Any]] = []
    spam_candidates: list[dict[str, Any]] = []

    normalized = [normalize_comment_thread_item(i) for i in raw_items]
    for c in normalized:
        text = c["text"]
        if URL_SPAM_RE.search(text):
            spam_candidates.append(c)
            continue
        ts_matches = TIMESTAMP_REF_RE.findall(text)
        if ts_matches:
            entry = dict(c)
            entry["timestamps_referenced"] = ts_matches
            timestamp_notes.append(entry)
        if QUESTION_CUE_RE.search(text):
            questions.append(c)
        if c["like_count"] >= 5 or len(text) >= 120:
            high_signal.append(c)

    questions.sort(key=lambda x: (-x["like_count"], -x["reply_count"]))
    high_signal.sort(key=lambda x: (-x["like_count"], -len(x["text"])))

    return {
        "total_comments_analyzed": len(normalized),
        "question_count": len(questions),
        "timestamp_citation_count": len(timestamp_notes),
        "high_signal_count": len(high_signal),
        "spam_candidate_count": len(spam_candidates),
        "questions_and_requests": questions[:50],
        "timestamp_citations": timestamp_notes[:50],
        "high_signal_comments": high_signal[:50],
        "spam_candidates": spam_candidates[:50],
    }


def fetch_and_triage_comments(
    client: YouTubeClient,
    *,
    video_id: str = "",
    channel_id: str = "",
    max_pages: int = 3,
) -> dict[str, Any]:
    """Fetch top-level commentThreads from YouTube Data API v3 (1 unit/page) and run triage."""
    params: dict[str, Any] = {
        "part": "id,snippet",
        "maxResults": 100,
        "order": "relevance",
        "textFormat": "plainText",
    }
    if video_id:
        params["videoId"] = validate_video_id(video_id)
    elif channel_id:
        params["allThreadsRelatedToChannelId"] = validate_channel_id(channel_id)
    else:
        raise ValueError("Provide either video_id or channel_id for commentThreads.list.")

    items: list[dict[str, Any]] = []
    page_token: str | None = None
    for _ in range(max(1, max_pages)):
        if page_token:
            params["pageToken"] = page_token
        resp = client.request_json("GET", f"{client.data_base_url}/commentThreads", params=params)
        items.extend(resp.get("items") or [])
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    report = triage_comments(items)
    report["source"] = "youtube_data_api_v3"
    return report


def audit_playlists(
    videos: list[dict[str, Any]],
    playlists: list[dict[str, Any]],
) -> dict[str, Any]:
    """Audit channel playlists for orphaned long-form videos, duplicate entries, and non-public dead slots."""
    if not isinstance(videos, list):
        raise ValueError("Videos payload must be a JSON list.")
    if not isinstance(playlists, list):
        raise ValueError("Playlists payload must be a JSON list.")
    for v in videos:
        if not isinstance(v, dict):
            raise ValueError("Each video entry must be a JSON object.")
    video_by_id = {str(v.get("video_id") or ""): v for v in videos if v.get("video_id")}
    assigned_video_ids: set[str] = set()
    playlist_reports: list[dict[str, Any]] = []

    for pl in playlists:
        if not isinstance(pl, dict):
            raise ValueError("Each playlist entry must be a JSON object.")
        pl_id = str(pl.get("playlist_id") or pl.get("id") or "")
        pl_title = str(pl.get("title") or "")
        raw_vids = pl.get("video_ids") if "video_ids" in pl and pl.get("video_ids") is not None else []
        if not isinstance(raw_vids, list):
            raise ValueError("Playlist 'video_ids' must be a JSON list.")
        item_ids = [str(vid) for vid in raw_vids if str(vid)]
        seen: set[str] = set()
        duplicates: list[str] = []
        non_public_slots: list[str] = []

        for vid in item_ids:
            assigned_video_ids.add(vid)
            if vid in seen and vid not in duplicates:
                duplicates.append(vid)
            seen.add(vid)
            v_rec = video_by_id.get(vid)
            if v_rec is None or v_rec.get("privacy_status") != "public":
                non_public_slots.append(vid)

        playlist_reports.append(
            {
                "playlist_id": pl_id,
                "title": pl_title,
                "item_count": len(item_ids),
                "duplicate_video_ids": duplicates,
                "non_public_or_missing_video_ids": non_public_slots,
            }
        )

    orphaned_public_long = [
        {"video_id": v["video_id"], "title": v.get("title", ""), "views": v.get("views", 0)}
        for v in videos
        if v.get("format") == "long"
        and v.get("privacy_status") == "public"
        and v.get("video_id") not in assigned_video_ids
    ]

    return {
        "playlist_count": len(playlist_reports),
        "orphaned_public_long_count": len(orphaned_public_long),
        "orphaned_public_long_videos": orphaned_public_long,
        "playlists": playlist_reports,
    }


def audit_shorts_funnel(
    videos: list[dict[str, Any]],
    *,
    canonical_cta: str = "",
) -> dict[str, Any]:
    """Audit the Shorts-to-Long-Form funnel across a channel inventory."""
    if not isinstance(videos, list):
        raise ValueError("Videos payload must be a JSON list.")
    for v in videos:
        if not isinstance(v, dict):
            raise ValueError("Each video entry must be a JSON object.")
    shorts = [v for v in videos if v.get("format") == "short" and v.get("privacy_status") == "public"]
    long_videos = [v for v in videos if v.get("format") == "long" and v.get("privacy_status") == "public"]

    long_ids = {str(v.get("video_id") or "") for v in long_videos}
    shorts_missing_cta: list[dict[str, str]] = []
    shorts_referencing_long: list[dict[str, str]] = []

    for s in shorts:
        vid = str(s.get("video_id") or "")
        title = str(s.get("title") or "")
        desc = str(s.get("description") or "")
        if canonical_cta and canonical_cta not in desc:
            shorts_missing_cta.append({"video_id": vid, "title": title})
        for l_id in long_ids:
            if l_id and l_id in desc:
                shorts_referencing_long.append({"short_video_id": vid, "target_long_video_id": l_id})

    top_long_targets = sorted(long_videos, key=lambda x: _safe_int(x.get("views"), "views"), reverse=True)[:5]

    return {
        "public_shorts_count": len(shorts),
        "public_long_count": len(long_videos),
        "shorts_to_long_ratio": round(len(shorts) / len(long_videos), 2) if long_videos else None,
        "shorts_with_long_description_link_count": len(shorts_referencing_long),
        "shorts_missing_cta_count": len(shorts_missing_cta),
        "shorts_missing_cta": shorts_missing_cta,
        "recommended_long_form_bridge_targets": [
            {
                "video_id": v.get("video_id"),
                "title": v.get("title"),
                "views": v.get("views", 0),
            }
            for v in top_long_targets
        ],
    }
