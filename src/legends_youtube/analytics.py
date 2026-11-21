"""YouTube Analytics API v2 parser, pre-recording Perfect Video Score radar, and channel packaging diagnostics."""
from __future__ import annotations

import math
from typing import Any

# Primary Google/YouTube Help constants:
# - Impressions CTR half-channel reference band: 2% to 10% (support.google.com/youtube/answer/7628154)
# - Average percentage viewed target: 50% (support.google.com/youtube/answer/12942217)
# - Mid-roll ad eligibility minimum runtime: 480 seconds / 8 minutes (support.google.com/youtube/answer/6175006)
CTR_FLOOR = 0.02
CTR_CEILING = 0.10
RETENTION_TARGET_APV = 0.50
MIDROLL_MIN_SECONDS = 480

REQUIRED_EXPORT_KEYS = ("video_id", "title", "length_seconds", "impressions", "views")


def _coerce_float(record: dict[str, Any], key: str, idx: int, *, default: float = 0.0, allow_negative: bool = False) -> float:
    raw = record.get(key, default)
    if raw is None:
        return float(default)
    if isinstance(raw, bool):
        raise ValueError(f"Record #{idx + 1} field {key!r} must be numeric, not bool")
    try:
        val = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"Record #{idx + 1} field {key!r} is not a valid number: {raw!r}") from None
    if not math.isfinite(val):
        raise ValueError(f"Record #{idx + 1} field {key!r} must be finite, got {raw!r}")
    if val < 0 and not allow_negative:
        raise ValueError(f"Record #{idx + 1} field {key!r} cannot be negative ({val})")
    return val


def normalize_records(videos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize Studio export or Analytics API video rows with derived CTR, APV, RPM, and mid-roll eligibility."""
    if not isinstance(videos, list):
        raise ValueError("Videos payload must be a JSON list.")
    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(videos):
        if not isinstance(item, dict):
            raise ValueError(f"Record #{idx + 1} must be a JSON object")
        for req_key in REQUIRED_EXPORT_KEYS:
            if req_key not in item:
                raise ValueError(f"Record #{idx + 1} missing required field: {req_key}")

        duration_sec = _coerce_float(item, "length_seconds", idx)
        views = _coerce_float(item, "views", idx)
        impressions = _coerce_float(item, "impressions", idx)
        avd_sec = _coerce_float(item, "average_view_duration_seconds", idx)
        revenue_usd = _coerce_float(item, "estimated_revenue_usd", idx)
        derived_ctr = (views / impressions) if impressions > 0 else 0.0
        ctr = _coerce_float(item, "impressions_ctr", idx, default=derived_ctr)
        if 1.0 < ctr <= 100.0:
            ctr = ctr / 100.0
        apv = (avd_sec / duration_sec) if duration_sec > 0 else 0.0
        rpm = (revenue_usd / views * 1000.0) if views > 0 else 0.0
        watch_hours = _coerce_float(item, "watch_time_hours", idx, default=(avd_sec * views) / 3600.0)
        subs_gained = round(_coerce_float(item, "subscribers_gained", idx, allow_negative=True))
        fmt_raw = str(item.get("format", "long")).strip().lower()
        fmt = "short" if fmt_raw == "short" else "long"

        normalized.append(
            {
                "video_id": str(item["video_id"]),
                "title": str(item["title"]),
                "published": str(item.get("published", "")),
                "format": fmt,
                "length_seconds": round(duration_sec, 2),
                "impressions": round(impressions, 2),
                "impressions_ctr": round(ctr, 4),
                "views": round(views, 2),
                "average_view_duration_seconds": round(avd_sec, 2),
                "average_percentage_viewed": round(apv, 4),
                "watch_time_hours": round(watch_hours, 2),
                "subscribers_gained": subs_gained,
                "estimated_revenue_usd": round(revenue_usd, 2),
                "rpm_usd": round(rpm, 2),
                "midroll_eligible": bool(fmt == "long" and duration_sec >= MIDROLL_MIN_SECONDS),
            }
        )
    normalized.sort(key=lambda r: r["video_id"])
    return normalized


def channel_health(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute weighted channel performance metrics and diagnostic flags."""
    if not records:
        return {
            "video_count": 0,
            "total_views": 0.0,
            "total_watch_hours": 0.0,
            "total_subscribers_gained": 0,
            "total_estimated_revenue_usd": 0.0,
            "avg_impressions_ctr": 0.0,
            "avg_percentage_viewed": 0.0,
            "blended_rpm_usd": 0.0,
            "subs_per_1k_views": 0.0,
            "flags": ["no videos in export"],
        }

    total_views = sum(r["views"] for r in records)
    total_impressions = sum(r["impressions"] for r in records)
    total_watch_hours = round(sum(r["watch_time_hours"] for r in records), 2)
    total_subs = sum(r["subscribers_gained"] for r in records)
    total_revenue = round(sum(r["estimated_revenue_usd"] for r in records), 2)

    weighted_ctr = (
        round(sum(r["impressions_ctr"] * r["impressions"] for r in records) / total_impressions, 4)
        if total_impressions > 0
        else 0.0
    )
    weighted_apv = (
        round(sum(r["average_percentage_viewed"] * r["views"] for r in records) / total_views, 4)
        if total_views > 0
        else 0.0
    )
    blended_rpm = round((total_revenue / total_views * 1000.0) if total_views > 0 else 0.0, 2)
    subs_per_1k = round((total_subs / total_views * 1000.0) if total_views > 0 else 0.0, 2)

    flags: list[str] = []
    if weighted_ctr < CTR_FLOOR:
        flags.append("Weighted CTR is below the 2% reference floor (YouTube Help 7628154); audit titles and thumbnails.")
    if weighted_apv < RETENTION_TARGET_APV:
        flags.append("Weighted average percentage viewed is below 50% (YouTube Help 12942217); tighten 30-second hook and pacing.")
    under_midroll = [r for r in records if r["format"] == "long" and not r["midroll_eligible"]]
    if under_midroll:
        flags.append(
            f"{len(under_midroll)} long-form video(s) are under 8 minutes (480s) and ineligible for mid-roll ads (YouTube Help 6175006)."
        )

    return {
        "video_count": len(records),
        "total_views": round(total_views, 2),
        "total_watch_hours": total_watch_hours,
        "total_subscribers_gained": total_subs,
        "total_estimated_revenue_usd": total_revenue,
        "avg_impressions_ctr": weighted_ctr,
        "avg_percentage_viewed": weighted_apv,
        "blended_rpm_usd": blended_rpm,
        "subs_per_1k_views": subs_per_1k,
        "flags": flags,
    }


def packaging_audit(records: list[dict[str, Any]], min_impressions: float = 1000.0) -> dict[str, Any]:
    """Identify high-impression long-form videos with below-median CTR for title/thumbnail Test & Compare runs."""
    if isinstance(min_impressions, bool) or not math.isfinite(float(min_impressions)):
        raise ValueError("min_impressions must be a finite number.")
    eligible = [r for r in records if r["format"] == "long" and r["impressions"] >= min_impressions]
    if not eligible:
        return {"candidate_count": 0, "median_ctr": 0.0, "decision_rule": "watch_time_share", "candidates": []}

    sorted_ctrs = sorted(r["impressions_ctr"] for r in eligible)
    mid = len(sorted_ctrs) // 2
    median_ctr = sorted_ctrs[mid] if len(sorted_ctrs) % 2 == 1 else round((sorted_ctrs[mid - 1] + sorted_ctrs[mid]) / 2.0, 4)

    candidates = [
        {
            "video_id": r["video_id"],
            "title": r["title"],
            "impressions": r["impressions"],
            "impressions_ctr": r["impressions_ctr"],
            "gap_to_median": round(median_ctr - r["impressions_ctr"], 4),
            "estimated_missed_views_at_median": round(r["impressions"] * max(0.0, median_ctr - r["impressions_ctr"])),
            "average_percentage_viewed": r["average_percentage_viewed"],
        }
        for r in eligible
        if r["impressions_ctr"] < median_ctr
    ]
    candidates.sort(key=lambda c: (-c["impressions"], c["video_id"]))
    return {
        "candidate_count": len(candidates),
        "median_ctr": round(median_ctr, 4),
        "decision_rule": "watch_time_share (YouTube Help 13861714)",
        "candidates": candidates,
    }


def parse_analytics_api_response(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert a YouTube Analytics API v2 columnHeaders + rows response into structured dicts."""
    headers_raw = report.get("columnHeaders") or []
    col_names = [str(h.get("name") or f"col_{i}") for i, h in enumerate(headers_raw) if isinstance(h, dict)]
    rows_raw = report.get("rows") or []
    out: list[dict[str, Any]] = []
    for row in rows_raw:
        if isinstance(row, list):
            item = {col_names[i]: row[i] for i in range(min(len(col_names), len(row)))}
            out.append(item)
    return out


def render_scorecard_markdown(records: list[dict[str, Any]], *, channel_name: str = "Channel") -> str:
    """Render a Markdown channel-health scorecard and packaging A/B test queue."""
    health = channel_health(records)
    packaging = packaging_audit(records)
    lines = [
        f"# Channel Health Scorecard: {channel_name}",
        "",
        "## Headline Metrics",
        "",
        f"- Videos analyzed: {health['video_count']}",
        f"- Total views: {health['total_views']}",
        f"- Total watch time (hours): {health['total_watch_hours']}",
        f"- Subscribers gained: {health['total_subscribers_gained']} ({health['subs_per_1k_views']} per 1,000 views)",
        f"- Estimated revenue (USD): {health['total_estimated_revenue_usd']}",
        f"- Weighted impressions CTR: {round(health['avg_impressions_ctr'] * 100, 2)}%",
        f"- Weighted average percentage viewed: {round(health['avg_percentage_viewed'] * 100, 2)}%",
        f"- Blended RPM (USD): {health['blended_rpm_usd']}",
        "",
        "## Diagnostic Flags",
        "",
    ]
    if health["flags"]:
        for flag in health["flags"]:
            lines.append(f"- {flag}")
    else:
        lines.append("- None. All headline metrics sit within healthy reference bands.")

    lines.extend(
        [
            "",
            "## Packaging A/B Test Queue",
            "",
            f"Long-form median CTR: {round(packaging['median_ctr'] * 100, 2)}%. Evaluate variants by watch-time share.",
            "",
        ]
    )
    if packaging["candidates"]:
        for c in packaging["candidates"]:
            lines.append(
                f"- `{c['video_id']}` {c['title']}: {round(c['impressions_ctr'] * 100, 2)}% CTR on {int(c['impressions'])} impressions "
                f"({round(c['gap_to_median'] * 100, 2)} pts below median; ~{c['estimated_missed_views_at_median']} missed clicks)"
            )
    else:
        lines.append("- No long-form videos below median CTR with >= 1,000 impressions.")
    return "\n".join(lines) + "\n"


def score_video_idea(
    *,
    title: str,
    days_since_catalyst: int = 14,
    trend_timing: float = 7.0,
    search_surface: float = 7.0,
    audience_pain: float = 8.0,
    channel_dna_fit: float = 8.0,
    proof_advantage: float = 8.0,
    packaging_strength: float = 8.0,
    production_drag: float = 3.0,
    platform_risk: float = 1.0,
    hype_saturation: float = 3.0,
    fit_checks_passed: int = 7,
) -> dict[str, Any]:
    """Compute the Perfect Video Score, Goldilocks Timing window, and 9-Point Fit Filter verdict before recording."""
    for factor_name, factor_val in (
        ("trend_timing", trend_timing),
        ("search_surface", search_surface),
        ("audience_pain", audience_pain),
        ("channel_dna_fit", channel_dna_fit),
        ("proof_advantage", proof_advantage),
        ("packaging_strength", packaging_strength),
        ("production_drag", production_drag),
        ("platform_risk", platform_risk),
        ("hype_saturation", hype_saturation),
    ):
        if isinstance(factor_val, bool) or not math.isfinite(float(factor_val)):
            raise ValueError(f"Score factor {factor_name!r} must be a finite number.")
    numerator_factors = {
        "trend_timing": max(1.0, min(10.0, float(trend_timing))),
        "search_surface": max(1.0, min(10.0, float(search_surface))),
        "audience_pain": max(1.0, min(10.0, float(audience_pain))),
        "channel_dna_fit": max(1.0, min(10.0, float(channel_dna_fit))),
        "proof_advantage": max(1.0, min(10.0, float(proof_advantage))),
        "packaging_strength": max(1.0, min(10.0, float(packaging_strength))),
    }
    drag_factors = {
        "production_drag": max(1.0, min(10.0, float(production_drag))),
        "platform_risk": max(1.0, min(10.0, float(platform_risk))),
        "hype_saturation": max(1.0, min(10.0, float(hype_saturation))),
    }

    # Normalize each numerator factor to a 0.1..1.0 multiplier and scale to 0..100
    product_norm = 1.0
    for val in numerator_factors.values():
        product_norm *= val / 10.0
    drag_sum = sum(drag_factors.values())  # 3.0 .. 30.0
    raw_score = (product_norm * 1000.0) / drag_sum
    score_100 = round(min(100.0, raw_score), 2)

    if days_since_catalyst <= 3:
        timing_stage = "too_early_day_0_3"
        timing_note = "Day 0-3: Watchlist unless you have an immediate working demo today."
    elif days_since_catalyst <= 30:
        timing_stage = "goldilocks_prime_day_4_30"
        timing_note = "Day 4-30 (Goldilocks Prime): Fresh catalyst + public evidence + weak practical coverage. Produce now."
    elif days_since_catalyst <= 180:
        timing_stage = "workflow_evergreen_day_31_180"
        timing_note = "Day 31-180 (Workflow Evergreen): Strong for practical workflow videos where creator coverage is still weak."
    else:
        timing_stage = "mature_180_plus"
        timing_note = "180+ Days: Only produce if you have a major new update, contrarian proof, or a superior system."

    fit_passed = max(0, min(9, int(fit_checks_passed)))
    fit_ok = fit_passed >= 5
    greenlight = fit_ok and score_100 >= 15.0 and timing_stage in ("goldilocks_prime_day_4_30", "workflow_evergreen_day_31_180")

    return {
        "title": title,
        "perfect_video_score": score_100,
        "greenlight": greenlight,
        "timing": {
            "days_since_catalyst": days_since_catalyst,
            "stage": timing_stage,
            "recommendation": timing_note,
        },
        "fit_filter": {
            "passed_count": fit_passed,
            "required_minimum": 5,
            "total_questions": 9,
            "passes_filter": fit_ok,
        },
        "numerator_factors": numerator_factors,
        "drag_factors": drag_factors,
    }
