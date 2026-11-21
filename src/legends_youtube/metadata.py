"""Lossless partial-update engine for YouTube video metadata with ETag concurrency, preflight merge, and readback verification."""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from typing import Any

from .api import YouTubeClient, YouTubeError, validate_channel_id, validate_video_id

PLAN_TOP_LEVEL_FIELDS = {"schemaVersion", "allowedVideoIds", "updates", "notes", "channelId"}
UPDATE_CONTROL_FIELDS = {"videoId", "expectedCurrent"}
WRITABLE_FIELDS = {"title", "description"}
PRESERVED_SNIPPET_FIELDS = (
    "title",
    "description",
    "tags",
    "categoryId",
    "defaultLanguage",
    "defaultAudioLanguage",
)
STANDALONE_I_RE = re.compile(r"\bi\b")
SACRED_GOD_RE = re.compile(r"\bgod(?P<possessive>'s|\u2019s)?\b", re.IGNORECASE)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_plan_sha256(plan_data: dict[str, Any]) -> str:
    """Compute a deterministic SHA-256 hash over a normalized update plan."""
    canonical = json.dumps(plan_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def legends_lowercase_title(title: str) -> str:
    """Lowercase a complete video title while preserving standalone 'I' and standalone 'God' / 'God's'."""
    lowered = (title or "").lower()
    with_i = STANDALONE_I_RE.sub("I", lowered)

    def _restore(match: re.Match[str]) -> str:
        poss = match.group("possessive") or ""
        return f"God{poss}"

    return SACRED_GOD_RE.sub(_restore, with_i)


def validate_metadata_plan(data: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a declarative YouTube metadata update plan."""
    if not isinstance(data, dict):
        raise YouTubeError("Metadata plan must be a JSON object.")
    unknown_top = set(data.keys()) - PLAN_TOP_LEVEL_FIELDS
    if unknown_top:
        raise YouTubeError(f"Forbidden top-level plan field(s): {', '.join(sorted(unknown_top))}")
    if data.get("schemaVersion", 1) != 1:
        raise YouTubeError("schemaVersion must equal 1.")

    allowlist_raw = data.get("allowedVideoIds")
    if not isinstance(allowlist_raw, list) or not allowlist_raw:
        raise YouTubeError("allowedVideoIds must be a non-empty list of 11-character video IDs.")
    allowlist = [validate_video_id(str(v), field_name="allowedVideoIds[]") for v in allowlist_raw]
    if len(set(allowlist)) != len(allowlist):
        raise YouTubeError("allowedVideoIds must not contain duplicate video IDs.")

    updates_raw = data.get("updates")
    if not isinstance(updates_raw, list) or not updates_raw:
        raise YouTubeError("updates must be a non-empty list.")

    normalized_updates: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    allowed_entry_fields = UPDATE_CONTROL_FIELDS | WRITABLE_FIELDS

    for index, entry in enumerate(updates_raw):
        label = f"updates[{index}]"
        if not isinstance(entry, dict):
            raise YouTubeError(f"{label} must be a JSON object.")
        unknown_entry = set(entry.keys()) - allowed_entry_fields
        if unknown_entry:
            raise YouTubeError(
                f"{label} contains forbidden field(s): {', '.join(sorted(unknown_entry))}; "
                "only title and description are writable in this lane."
            )
        vid = validate_video_id(str(entry.get("videoId") or ""), field_name=f"{label}.videoId")
        if vid not in allowlist:
            raise YouTubeError(f"{label}.videoId {vid!r} is not in allowedVideoIds.")
        if vid in seen_ids:
            raise YouTubeError(f"Duplicate update entry for videoId {vid!r}.")
        seen_ids.add(vid)

        changes = {k: entry[k] for k in WRITABLE_FIELDS if k in entry}
        if not changes:
            raise YouTubeError(f"{label} must specify at least one of 'title' or 'description'.")
        for field_name, val in changes.items():
            if not isinstance(val, str):
                raise YouTubeError(f"{label}.{field_name} must be a string.")
        if "title" in changes:
            if not changes["title"].strip() or not (1 <= len(changes["title"]) <= 100):
                raise YouTubeError(f"{label}.title must be 1..100 non-whitespace characters (got {len(changes['title'])}).")
            if "<" in changes["title"] or ">" in changes["title"]:
                raise YouTubeError(f"{label}.title must not contain '<' or '>' angle brackets (rejected by YouTube Data API v3).")
        if "description" in changes:
            if len(changes["description"]) > 5000:
                raise YouTubeError(f"{label}.description must be <= 5000 characters (got {len(changes['description'])}).")
            if "<" in changes["description"] or ">" in changes["description"]:
                raise YouTubeError(
                    f"{label}.description must not contain '<' or '>' angle brackets (rejected by YouTube Data API v3)."
                )

        expected = entry.get("expectedCurrent") or {}
        if not isinstance(expected, dict):
            raise YouTubeError(f"{label}.expectedCurrent must be an object.")
        unknown_expected = set(expected.keys()) - WRITABLE_FIELDS
        if unknown_expected:
            raise YouTubeError(
                f"{label}.expectedCurrent contains forbidden field(s): {', '.join(sorted(unknown_expected))}."
            )
        for k, v in expected.items():
            if not isinstance(v, str):
                raise YouTubeError(f"{label}.expectedCurrent.{k} must be a string.")

        normalized_entry: dict[str, Any] = {
            "videoId": vid,
            "expectedCurrent": dict(expected),
        }
        normalized_entry.update(changes)
        normalized_updates.append(normalized_entry)

    out: dict[str, Any] = {
        "schemaVersion": 1,
        "allowedVideoIds": allowlist,
        "updates": normalized_updates,
    }
    if data.get("channelId"):
        out["channelId"] = validate_channel_id(str(data["channelId"]), field_name="channelId")
    if data.get("notes"):
        out["notes"] = str(data["notes"])
    return out


def build_merged_snippet(current_snippet: dict[str, Any], changes: dict[str, str]) -> dict[str, Any]:
    """Merge requested title/description changes onto the full existing snippet so YouTube never deletes omitted fields."""
    merged: dict[str, Any] = {}
    for key in PRESERVED_SNIPPET_FIELDS:
        if key in current_snippet and current_snippet[key] is not None:
            merged[key] = current_snippet[key]
    for key, val in changes.items():
        if key in WRITABLE_FIELDS:
            merged[key] = val
    if not merged.get("title"):
        raise YouTubeError("Merged snippet is missing required 'title'.")
    if not merged.get("categoryId"):
        raise YouTubeError("Live video snippet is missing required 'categoryId'; refusing partial update.")
    return merged


def preview_metadata_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Validate a plan offline and return its canonical SHA-256 lock and update summary."""
    normalized = validate_metadata_plan(plan)
    plan_hash = canonical_plan_sha256(normalized)
    items: list[dict[str, Any]] = []
    for entry in normalized["updates"]:
        fields_changed = [f for f in ("title", "description") if f in entry]
        items.append(
            {
                "video_id": entry["videoId"],
                "fields_to_update": fields_changed,
                "has_expected_current_guard": bool(entry.get("expectedCurrent")),
                "new_title": entry.get("title"),
                "new_description_length": len(entry["description"]) if "description" in entry else None,
            }
        )
    update_count = len(normalized["updates"])
    return {
        "mode": "dry_run_preview",
        "plan_sha256": plan_hash,
        "allowed_video_count": len(normalized["allowedVideoIds"]),
        "update_count": update_count,
        "estimated_quota_units": math.ceil(update_count / 50) + update_count * 51,
        "updates": items,
        "normalized_plan": normalized,
    }


def execute_metadata_plan(
    client: YouTubeClient,
    plan: dict[str, Any],
    *,
    expected_plan_sha256: str,
    confirm: bool = False,
) -> dict[str, Any]:
    """Execute a validated metadata update plan with preflight ETag capture, drift rejection, and readback verification."""
    normalized = validate_metadata_plan(plan)
    actual_sha = canonical_plan_sha256(normalized)
    clean_expected = (expected_plan_sha256 or "").strip().lower()
    if clean_expected and actual_sha.lower() != clean_expected:
        raise YouTubeError(
            f"Plan SHA-256 mismatch: expected {expected_plan_sha256}, calculated {actual_sha}. Refusing execution."
        )
    if not confirm:
        return preview_metadata_plan(normalized)
    if not clean_expected:
        raise YouTubeError("Refusing live metadata execution without expected_plan_sha256 lock.")

    target_ids = [u["videoId"] for u in normalized["updates"]]
    preflight_items = client.list_videos_by_ids(target_ids, part="id,snippet,status")
    preflight_map = {str(item.get("id")): item for item in preflight_items if isinstance(item, dict)}

    missing = [vid for vid in target_ids if vid not in preflight_map]
    if missing:
        raise YouTubeError(f"Preflight failed: video ID(s) not found on YouTube: {', '.join(missing)}")

    before_snapshot: dict[str, Any] = {}
    prepared_mutations: list[dict[str, Any]] = []
    locked_channel_id = normalized.get("channelId")

    for entry in normalized["updates"]:
        vid = entry["videoId"]
        live_item = preflight_map[vid]
        etag = str(live_item.get("etag") or "").strip()
        if not etag:
            raise YouTubeError(f"Preflight failed: missing ETag on video {vid}.")
        live_snippet = live_item.get("snippet") if isinstance(live_item.get("snippet"), dict) else {}
        live_status = live_item.get("status") if isinstance(live_item.get("status"), dict) else {}

        if locked_channel_id:
            actual_channel_id = str(live_snippet.get("channelId") or "")
            if actual_channel_id != locked_channel_id:
                raise YouTubeError(
                    f"Preflight channelId mismatch on {vid}: plan locked to {locked_channel_id!r}, live video belongs to {actual_channel_id!r}. Aborting before first write."
                )

        expected_current = entry.get("expectedCurrent") or {}
        for field_name, exp_val in expected_current.items():
            live_val = str(live_snippet.get(field_name) or "")
            if live_val.replace("\r\n", "\n") != exp_val.replace("\r\n", "\n"):
                raise YouTubeError(
                    f"Preflight drift detected on {vid}.{field_name}: expected {exp_val!r}, live value is {live_val!r}. Aborting before first write."
                )

        changes = {k: entry[k] for k in ("title", "description") if k in entry}
        merged_snippet = build_merged_snippet(live_snippet, changes)
        before_snapshot[vid] = {
            "etag": etag,
            "snippet": {k: live_snippet.get(k) for k in PRESERVED_SNIPPET_FIELDS},
            "privacyStatus": live_status.get("privacyStatus"),
        }
        prepared_mutations.append(
            {
                "videoId": vid,
                "etag": etag,
                "changes": changes,
                "mergedSnippet": merged_snippet,
            }
        )

    results: list[dict[str, Any]] = []
    mutations_applied = 0

    for item in prepared_mutations:
        vid = item["videoId"]
        updated_resource = client.update_video_snippet(
            video_id=vid,
            snippet=item["mergedSnippet"],
            etag=item["etag"],
        )
        mutations_applied += 1
        readback_list = client.list_videos_by_ids([vid], part="id,snippet,status")
        readback_item = readback_list[0] if readback_list else updated_resource
        rb_snippet = readback_item.get("snippet") if isinstance(readback_item.get("snippet"), dict) else {}
        rb_status = readback_item.get("status") if isinstance(readback_item.get("status"), dict) else {}

        # Verify updated fields match and untouched preserved fields did not drift
        for k, expected_val in item["mergedSnippet"].items():
            actual_val = rb_snippet.get(k)
            if k == "tags":
                if list(actual_val or []) != list(expected_val or []):
                    raise YouTubeError(
                        f"Post-write readback verification failed on {vid}.tags: expected {expected_val!r}, got {actual_val!r}."
                    )
            elif isinstance(expected_val, str) and isinstance(actual_val, str):
                if actual_val.replace("\r\n", "\n") != expected_val.replace("\r\n", "\n"):
                    raise YouTubeError(
                        f"Post-write readback verification failed on {vid}.{k}: expected {expected_val!r}, got {actual_val!r}."
                    )
            elif actual_val != expected_val:
                raise YouTubeError(
                    f"Post-write readback verification failed on {vid}.{k}: expected {expected_val!r}, got {actual_val!r}."
                )
        before_priv = before_snapshot[vid]["privacyStatus"]
        after_priv = rb_status.get("privacyStatus")
        if before_priv and after_priv and before_priv != after_priv:
            raise YouTubeError(
                f"Forbidden privacyStatus drift on {vid}: was {before_priv!r}, read back {after_priv!r}."
            )

        results.append(
            {
                "video_id": vid,
                "status": "verified",
                "before_etag": item["etag"],
                "after_etag": readback_item.get("etag"),
                "updated_fields": sorted(item["changes"].keys()),
                "privacy_preserved": after_priv == before_priv,
            }
        )

    return {
        "mode": "confirmed_execution",
        "executed_at": utc_now(),
        "plan_sha256": actual_sha,
        "youtube_mutations": mutations_applied,
        "forbidden_surface_mutations": 0,
        "before_snapshot": before_snapshot,
        "results": results,
    }


def generate_link_migration_plan(
    videos: list[dict[str, Any]],
    *,
    find_url: str = "",
    replace_url: str = "",
    set_exact_description: str | None = None,
    include_formats: tuple[str, ...] = ("long",),
    exclude_video_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Generate a hash-locked metadata update plan to migrate links or standardize descriptions across a channel."""
    if set_exact_description is None and not (find_url and replace_url):
        raise YouTubeError("Specify either set_exact_description or both find_url and replace_url.")
    excluded = set(exclude_video_ids or [])
    updates: list[dict[str, Any]] = []
    allowed: list[str] = []

    for rec in videos:
        vid = str(rec.get("video_id") or "")
        fmt = str(rec.get("format") or "long")
        if not vid or vid in excluded or fmt not in include_formats:
            continue
        current_desc = str(rec.get("description") or "")
        if set_exact_description is not None:
            new_desc = set_exact_description
        elif find_url and replace_url:
            if find_url not in current_desc:
                continue
            new_desc = current_desc.replace(find_url, replace_url)
        else:
            continue

        if new_desc == current_desc:
            continue

        allowed.append(vid)
        updates.append(
            {
                "videoId": vid,
                "expectedCurrent": {"description": current_desc},
                "description": new_desc,
            }
        )

    if not updates:
        return {
            "matched_count": 0,
            "plan": None,
            "plan_sha256": None,
        }

    plan = validate_metadata_plan(
        {
            "schemaVersion": 1,
            "allowedVideoIds": allowed,
            "updates": updates,
            "notes": f"Generated link/description migration plan for {len(updates)} video(s).",
        }
    )
    return {
        "matched_count": len(updates),
        "plan_sha256": canonical_plan_sha256(plan),
        "plan": plan,
    }
