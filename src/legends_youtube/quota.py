"""Deterministic YouTube Data API v3 quota calculator and multi-day batch wave planner."""
from __future__ import annotations

import math
from typing import Any

DEFAULT_DAILY_POOL_UNITS = 10_000
GRANULAR_SEARCH_DAILY_CAP = 100
GRANULAR_UPLOAD_DAILY_CAP = 100
RECOMMENDED_SAFETY_RESERVE_UNITS = 500

ENDPOINT_COSTS: dict[str, int] = {
    "channels.list": 1,
    "playlistItems.list": 1,
    "videos.list": 1,
    "playlists.list": 1,
    "commentThreads.list": 1,
    "comments.list": 1,
    "captions.list": 1,
    "search.list": 1,
    "videos.update": 50,
    "thumbnails.set": 50,
    "playlists.insert": 50,
    "playlists.update": 50,
    "playlistItems.insert": 50,
    "playlistItems.delete": 50,
    "videos.delete": 50,
    "videos.rate": 50,
    "videos.insert": 100,
    "videos.insert_legacy": 1600,
    "captions.insert": 400,
    "captions.update": 450,
    "captions.delete": 50,
}


def inventory_quota_cost(video_count: int) -> dict[str, Any]:
    """Calculate the exact quota cost to inventory N channel videos via uploads playlist vs search.list."""
    count = max(0, int(video_count))
    pages = math.ceil(count / 50) if count > 0 else 0
    playlist_route_units = 1 + (pages * 1) + (pages * 1)  # channels.list(1) + playlistItems.list(pages) + videos.list(pages)
    search_calls = pages
    return {
        "video_count": count,
        "pages_of_50": pages,
        "uploads_playlist_route": {
            "channels_list_calls": 1,
            "playlist_items_list_calls": pages,
            "videos_list_calls": pages,
            "total_units": playlist_route_units,
        },
        "naive_search_route": {
            "search_list_calls": search_calls,
            "granular_search_cap_per_day": GRANULAR_SEARCH_DAILY_CAP,
            "legacy_100_unit_equivalent": search_calls * 100 + pages,
            "exceeds_daily_search_cap": search_calls > GRANULAR_SEARCH_DAILY_CAP,
        },
    }


def _max_meta_batch_for_budget(budget: int, per_item_cost: int, include_preflight: bool) -> int:
    if budget <= 0 or per_item_cost <= 0:
        return 0
    candidate = budget // per_item_cost
    while candidate > 0:
        preflight = math.ceil(candidate / 50) if include_preflight else 0
        if preflight + candidate * per_item_cost <= budget:
            return candidate
        candidate -= 1
    return 0


def plan_quota_budget(
    *,
    inventory_videos: int = 0,
    metadata_updates: int = 0,
    thumbnail_sets: int = 0,
    caption_inserts: int = 0,
    caption_updates: int = 0,
    draft_uploads: int = 0,
    search_queries: int = 0,
    daily_limit: int = DEFAULT_DAILY_POOL_UNITS,
    safety_reserve: int = RECOMMENDED_SAFETY_RESERVE_UNITS,
    include_preflight_and_readback: bool = True,
) -> dict[str, Any]:
    """Calculate total YouTube Data API v3 quota usage and split large mutations into safe daily waves."""
    limit_int = int(daily_limit)
    reserve_int = int(safety_reserve)
    if limit_int <= 0:
        raise ValueError(f"daily_limit must be > 0, got {daily_limit}")
    if reserve_int < 0 or reserve_int >= limit_int:
        raise ValueError(
            f"safety_reserve ({safety_reserve}) must be >= 0 and strictly less than daily_limit ({daily_limit})"
        )
    usable_daily = limit_int - reserve_int
    inv = inventory_quota_cost(inventory_videos) if inventory_videos > 0 else None
    inventory_units = inv["uploads_playlist_route"]["total_units"] if inv else 0

    # Each guarded metadata update does: preflight chunked videos.list (1 per 50), videos.update (50), and readback videos.list (1)
    meta_count = max(0, int(metadata_updates))
    meta_preflight_units = math.ceil(meta_count / 50) if (meta_count > 0 and include_preflight_and_readback) else 0
    meta_write_units = meta_count * ENDPOINT_COSTS["videos.update"]
    meta_readback_units = meta_count * ENDPOINT_COSTS["videos.list"] if include_preflight_and_readback else 0
    meta_total_units = meta_preflight_units + meta_write_units + meta_readback_units

    thumb_count = max(0, int(thumbnail_sets))
    thumb_units = thumb_count * ENDPOINT_COSTS["thumbnails.set"]

    cap_ins_count = max(0, int(caption_inserts))
    cap_ins_units = cap_ins_count * ENDPOINT_COSTS["captions.insert"]

    cap_upd_count = max(0, int(caption_updates))
    cap_upd_units = cap_upd_count * ENDPOINT_COSTS["captions.update"]

    upload_count = max(0, int(draft_uploads))
    # Each draft upload typically verifies channel (1), inserts video (100), sets thumbnail (50), inserts playlistItem (50), reads back (1)
    per_upload_units = (
        ENDPOINT_COSTS["videos.insert"]
        + (ENDPOINT_COSTS["thumbnails.set"] + ENDPOINT_COSTS["playlistItems.insert"] + 2 if include_preflight_and_readback else 0)
    )
    upload_units = upload_count * per_upload_units

    search_count = max(0, int(search_queries))
    search_units = search_count * ENDPOINT_COSTS["search.list"]

    total_pool_units = (
        inventory_units
        + meta_total_units
        + thumb_units
        + cap_ins_units
        + cap_upd_units
        + upload_units
        + search_units
    )

    per_meta_item_cost = 51 if include_preflight_and_readback else 50
    day1_budget = max(0, usable_daily - inventory_units)
    full_day_meta_cap = max(
        1,
        _max_meta_batch_for_budget(usable_daily, per_meta_item_cost, include_preflight_and_readback),
    )
    day1_meta_cap = _max_meta_batch_for_budget(day1_budget, per_meta_item_cost, include_preflight_and_readback)
    max_meta_updates_per_day = day1_meta_cap if day1_meta_cap > 0 else full_day_meta_cap
    max_thumbnails_per_day = max(1, day1_budget // ENDPOINT_COSTS["thumbnails.set"])
    max_captions_per_day = max(1, day1_budget // ENDPOINT_COSTS["captions.insert"])

    waves: list[dict[str, Any]] = []
    if meta_count > 0:
        remaining = meta_count
        wave_idx = 1
        while remaining > 0:
            wave_cap = max_meta_updates_per_day if wave_idx == 1 else full_day_meta_cap
            batch = min(remaining, wave_cap)
            preflight_cost = math.ceil(batch / 50) if include_preflight_and_readback else 0
            waves.append(
                {
                    "wave": wave_idx,
                    "operation": "metadata_updates",
                    "items": batch,
                    "estimated_units": preflight_cost + batch * per_meta_item_cost,
                }
            )
            remaining -= batch
            wave_idx += 1

    days_needed = max(1, math.ceil(total_pool_units / usable_daily)) if total_pool_units > 0 else 1
    if waves:
        days_needed = max(days_needed, len(waves))
    if search_count > GRANULAR_SEARCH_DAILY_CAP:
        days_needed = max(days_needed, math.ceil(search_count / GRANULAR_SEARCH_DAILY_CAP))
    if upload_count > GRANULAR_UPLOAD_DAILY_CAP:
        days_needed = max(days_needed, math.ceil(upload_count / GRANULAR_UPLOAD_DAILY_CAP))

    warnings: list[str] = []
    if total_pool_units > usable_daily:
        warnings.append(
            f"Planned operations require {total_pool_units} units, exceeding usable single-day budget ({usable_daily} units after {reserve_int}-unit safety reserve). Split across {days_needed} daily waves."
        )
    if search_count > GRANULAR_SEARCH_DAILY_CAP:
        warnings.append(
            f"search_queries={search_count} exceeds the 2026-06-01 granular cap of {GRANULAR_SEARCH_DAILY_CAP} search.list calls/day."
        )
    if upload_count > GRANULAR_UPLOAD_DAILY_CAP:
        warnings.append(
            f"draft_uploads={upload_count} exceeds the 2026-06-01 granular cap of {GRANULAR_UPLOAD_DAILY_CAP} videos.insert calls/day."
        )

    return {
        "daily_limit_units": limit_int,
        "safety_reserve_units": reserve_int,
        "usable_daily_units": usable_daily,
        "total_estimated_units": total_pool_units,
        "fits_in_single_day": total_pool_units <= usable_daily
        and search_count <= GRANULAR_SEARCH_DAILY_CAP
        and upload_count <= GRANULAR_UPLOAD_DAILY_CAP,
        "estimated_days_required": days_needed,
        "breakdown": {
            "inventory_units": inventory_units,
            "metadata_update_units": meta_total_units,
            "thumbnail_set_units": thumb_units,
            "caption_insert_units": cap_ins_units,
            "caption_update_units": cap_upd_units,
            "draft_upload_units": upload_units,
            "search_units": search_units,
        },
        "safe_daily_capacities": {
            "max_guarded_metadata_updates_per_day": max_meta_updates_per_day,
            "max_thumbnail_sets_per_day": max_thumbnails_per_day,
            "max_caption_inserts_per_day": max_captions_per_day,
            "max_search_list_calls_per_day": GRANULAR_SEARCH_DAILY_CAP,
            "max_video_uploads_per_day": min(GRANULAR_UPLOAD_DAILY_CAP, usable_daily // max(1, per_upload_units)),
        },
        "inventory_comparison": inv,
        "recommended_waves": waves,
        "warnings": warnings,
    }
