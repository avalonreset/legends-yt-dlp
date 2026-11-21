"""CLI entry point for legends-youtube."""
from __future__ import annotations

import argparse
import datetime
import json
import math
import platform
import re
import sys
from typing import Any

from . import __version__
from .analytics import (
    channel_health,
    normalize_records,
    packaging_audit,
    parse_analytics_api_response,
    render_scorecard_markdown,
    score_video_idea,
)
from .api import (
    YouTubeClient,
    YouTubeError,
    redact_credential_summary,
    resolve_credentials,
    safe_read_json_file,
    safe_read_text_file,
    safe_write_text_file,
    scrub_secrets,
    validate_channel_id,
)
from .engagement import (
    audit_playlists,
    audit_shorts_funnel,
    fetch_and_triage_comments,
    triage_comments,
)
from .intelligence import (
    compile_transcript_package,
    correlate_retention_with_transcript,
    fetch_public_channel_feed,
    scout_channel_outliers,
)
from .inventory import (
    fetch_channel_inventory,
    inspect_videos,
    normalize_api_video_item,
    public_video_readback,
)
from .metadata import (
    execute_metadata_plan,
    generate_link_migration_plan,
    legends_lowercase_title,
    preview_metadata_plan,
    validate_metadata_plan,
)
from .quota import plan_quota_budget
from .resources import resolve as resolve_resources, status as resources_status
from .studio_lint import (
    audit_description_links,
    lint_chapters,
    lint_house_style,
    lint_studio_quizzes,
    validate_related_video_guard,
)
from .upload import (
    execute_private_draft_upload,
    freeze_draft_plan,
    inspect_thumbnail,
)


_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_iso_date(raw: str, label: str) -> str:
    cleaned = (raw or "").strip()
    if not _ISO_DATE_RE.fullmatch(cleaned):
        raise YouTubeError(f"Invalid {label} {raw!r}: expected YYYY-MM-DD.")
    try:
        datetime.date.fromisoformat(cleaned)
    except ValueError as exc:
        raise YouTubeError(f"Invalid {label} {raw!r}: {exc}") from None
    return cleaned


def _finite_float_arg(raw: str) -> float:
    try:
        val = float(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid float value: {raw!r}") from None
    if not math.isfinite(val):
        raise argparse.ArgumentTypeError(f"non-finite float value is not allowed: {raw!r}")
    return val


def _emit(
    payload: dict[str, Any],
    *,
    as_json: bool = True,
    output_path: str = "",
    overwrite: bool = False,
    exit_code: int = 0,
) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    text = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False)
    if output_path:
        written = safe_write_text_file(output_path, text + "\n", overwrite=overwrite)
        payload = dict(payload)
        payload["written_to"] = written
        text = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False)
    if as_json:
        print(text)
    else:
        for k, v in payload.items():
            print(f"{k}: {v}")
    return exit_code


def _load_videos_from_inventory_json(path: str) -> list[dict[str, Any]]:
    _, data, _ = safe_read_json_file(path, max_bytes=10 * 1024 * 1024, label="inventory JSON")
    if isinstance(data, dict):
        if "videos" in data and data.get("videos") is not None:
            raw_videos = data.get("videos")
        elif "items" in data and data.get("items") is not None:
            raw_videos = data.get("items")
        else:
            raw_videos = []
    elif isinstance(data, list):
        raw_videos = data
    else:
        raise YouTubeError("Inventory JSON must be an object with 'videos' or a JSON list.")
    if not isinstance(raw_videos, list):
        raise YouTubeError("'videos' field must be a list.")
    normalized: list[dict[str, Any]] = []
    for item in raw_videos:
        if not isinstance(item, dict):
            raise YouTubeError("Each inventory video item must be a JSON object.")
        if "snippet" in item and "id" in item:
            normalized.append(normalize_api_video_item(item))
        else:
            normalized.append(item)
    return normalized


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="legends-youtube",
        description="YouTube Data API v3 and Analytics API v2 CLI + attachable Empire knowledge pack.",
    )
    parser.add_argument("--version", action="version", version=f"legends-youtube {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # 1. doctor
    p_doc = sub.add_parser("doctor", help="Check offline readiness, knowledge pack integrity, and optional live auth.")
    p_doc.add_argument("--dotenv", default="", help="Optional .env file path.")
    p_doc.add_argument("--token-file", default="", help="Optional OAuth token JSON path.")
    p_doc.add_argument("--live", action="store_true", help="Verify live channel connectivity via YouTube Data API v3.")
    p_doc.add_argument("--expected-channel-id", default="", help="Require exact UC... channel ID on live check.")
    p_doc.add_argument("--json", action=argparse.BooleanOptionalAction, default=True, help="Emit JSON output.")
    p_doc.add_argument("--output", default="", help="Write single JSON report file.")
    p_doc.add_argument("--overwrite", action="store_true", help="Overwrite existing output file.")

    # 2. auth-status
    p_auth = sub.add_parser("auth-status", help="Inspect resolved OAuth/API-key state and optional live channel lock.")
    p_auth.add_argument("--dotenv", default="", help="Optional .env file path.")
    p_auth.add_argument("--token-file", default="", help="Optional OAuth token JSON path.")
    p_auth.add_argument("--live", action="store_true", help="Call channels.list to verify live identity.")
    p_auth.add_argument("--expected-channel-id", default="", help="Require exact UC... channel ID.")
    p_auth.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_auth.add_argument("--output", default="")
    p_auth.add_argument("--overwrite", action="store_true")

    # 3. quota-plan
    p_quota = sub.add_parser(
        "quota-plan",
        help="Calculate YouTube Data API v3 unit costs and split large batches into safe daily waves.",
    )
    p_quota.add_argument("--inventory-videos", type=int, default=0, help="Number of channel videos to inventory.")
    p_quota.add_argument("--metadata-updates", type=int, default=0, help="Number of guarded videos.update calls.")
    p_quota.add_argument("--thumbnail-sets", type=int, default=0, help="Number of thumbnails.set calls.")
    p_quota.add_argument("--caption-inserts", type=int, default=0, help="Number of captions.insert calls.")
    p_quota.add_argument("--caption-updates", type=int, default=0, help="Number of captions.update calls.")
    p_quota.add_argument("--draft-uploads", type=int, default=0, help="Number of videos.insert draft uploads.")
    p_quota.add_argument("--search-queries", type=int, default=0, help="Number of search.list calls.")
    p_quota.add_argument("--daily-limit", type=int, default=10000, help="Daily project quota pool (default 10000).")
    p_quota.add_argument("--safety-reserve", type=int, default=500, help="Units reserved as safety buffer (default 500).")
    p_quota.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_quota.add_argument("--output", default="")
    p_quota.add_argument("--overwrite", action="store_true")

    # 4. channel-inventory
    p_inv = sub.add_parser(
        "channel-inventory",
        help="Inventory a YouTube channel via its uploads playlist (2 quota units per 50 videos) or offline export.",
    )
    p_inv.add_argument("--channel-id", default="", help="Target UC... channel ID.")
    p_inv.add_argument("--mine", action="store_true", help="Inventory the authenticated owner's channel.")
    p_inv.add_argument("--max-videos", type=int, default=500, help="Max videos to fetch (default 500).")
    p_inv.add_argument("--from-json", default="", help="Load and normalize an offline inventory JSON file.")
    p_inv.add_argument("--dotenv", default="")
    p_inv.add_argument("--token-file", default="")
    p_inv.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_inv.add_argument("--output", default="")
    p_inv.add_argument("--overwrite", action="store_true")

    # 5. video-inspect
    p_vid = sub.add_parser("video-inspect", help="Inspect specific YouTube video IDs via videos.list.")
    p_vid.add_argument("--video-ids", required=True, help="Comma-separated 11-character YouTube video IDs.")
    p_vid.add_argument("--dotenv", default="")
    p_vid.add_argument("--token-file", default="")
    p_vid.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_vid.add_argument("--output", default="")
    p_vid.add_argument("--overwrite", action="store_true")

    # 6. metadata-plan
    p_mplan = sub.add_parser(
        "metadata-plan",
        help="Validate and preview a declarative metadata update plan or generate a Legends title/description plan.",
    )
    p_mplan.add_argument("--plan", default="", help="Path to an existing metadata plan JSON file to validate.")
    p_mplan.add_argument("--from-inventory", default="", help="Generate a plan from an inventory JSON file.")
    p_mplan.add_argument(
        "--lowercase-titles",
        action="store_true",
        help="Generate a plan that lowercases video titles while preserving standalone 'I' and 'God' / 'God's'.",
    )
    p_mplan.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_mplan.add_argument("--output", default="")
    p_mplan.add_argument("--overwrite", action="store_true")

    # 7. metadata-apply
    p_mapply = sub.add_parser(
        "metadata-apply",
        help="Execute a hash-locked metadata update plan with preflight ETag concurrency, snippet merge, and readback verification.",
    )
    p_mapply.add_argument("--plan", required=True, help="Path to the validated metadata plan JSON file.")
    p_mapply.add_argument("--expected-plan-sha256", required=True, help="Required SHA-256 lock from metadata-plan.")
    p_mapply.add_argument("--confirm", action="store_true", help="Authorize live YouTube Data API v3 mutations.")
    p_mapply.add_argument("--dotenv", default="")
    p_mapply.add_argument("--token-file", default="")
    p_mapply.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_mapply.add_argument("--output", default="")
    p_mapply.add_argument("--overwrite", action="store_true")

    # 8. links-audit
    p_laudit = sub.add_parser(
        "links-audit",
        help="Audit all URLs across a channel's video descriptions for missing CTAs, legacy domains, or HTTP links.",
    )
    p_laudit.add_argument("--inventory", required=True, help="Path to channel inventory JSON file.")
    p_laudit.add_argument("--canonical-cta", default="", help="Expected CTA URL on regular long-form videos.")
    p_laudit.add_argument("--legacy-domains", default="", help="Comma-separated legacy domains to flag.")
    p_laudit.add_argument("--probe-https", action="store_true", help="Probe unique public HTTPS URLs (no-redirect SSRF-safe).")
    p_laudit.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_laudit.add_argument("--output", default="")
    p_laudit.add_argument("--overwrite", action="store_true")

    # 9. links-migrate
    p_lmig = sub.add_parser(
        "links-migrate",
        help="Generate a hash-locked metadata plan to replace legacy URLs or set a canonical CTA across regular videos.",
    )
    p_lmig.add_argument("--inventory", required=True, help="Path to channel inventory JSON file.")
    p_lmig.add_argument("--find-url", default="", help="Exact legacy URL substring to replace.")
    p_lmig.add_argument("--replace-url", default="", help="Replacement URL.")
    p_lmig.add_argument("--set-exact-description", default=None, help="Set exact description on all included videos.")
    p_lmig.add_argument("--include-shorts", action="store_true", help="Include Shorts in addition to long-form videos.")
    p_lmig.add_argument("--exclude-video-ids", default="", help="Comma-separated video IDs to exclude.")
    p_lmig.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_lmig.add_argument("--output", default="")
    p_lmig.add_argument("--overwrite", action="store_true")

    # 10. analytics-audit
    today_utc = datetime.datetime.now(datetime.timezone.utc).date()
    default_start = (today_utc - datetime.timedelta(days=90)).isoformat()
    default_end = today_utc.isoformat()
    p_ana = sub.add_parser(
        "analytics-audit",
        help="Run a sourced Channel Health Scorecard and packaging audit from a Studio export JSON or live Analytics API v2.",
    )
    p_ana.add_argument("--export", default="", help="Path to a YouTube Studio video-level export JSON.")
    p_ana.add_argument("--live", action="store_true", help="Query live YouTube Analytics API v2 reports.")
    p_ana.add_argument("--start-date", default=default_start, help="Start date YYYY-MM-DD for live Analytics query.")
    p_ana.add_argument("--end-date", default=default_end, help="End date YYYY-MM-DD for live Analytics query.")
    p_ana.add_argument("--channel-name", default="Channel", help="Channel display name for scorecard.")
    p_ana.add_argument("--markdown", action="store_true", help="Include rendered Markdown scorecard.")
    p_ana.add_argument("--dotenv", default="")
    p_ana.add_argument("--token-file", default="")
    p_ana.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_ana.add_argument("--output", default="")
    p_ana.add_argument("--overwrite", action="store_true")

    # 11. packaging-audit
    p_pkg = sub.add_parser(
        "packaging-audit",
        help="Identify high-impression long-form videos below median CTR for Title/Thumbnail A/B testing.",
    )
    p_pkg.add_argument("--export", required=True, help="Path to a YouTube Studio video-level export JSON.")
    p_pkg.add_argument("--min-impressions", type=_finite_float_arg, default=1000.0, help="Minimum impressions threshold (default 1000).")
    p_pkg.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_pkg.add_argument("--output", default="")
    p_pkg.add_argument("--overwrite", action="store_true")

    # 12. chapters-lint
    p_chap = sub.add_parser(
        "chapters-lint",
        help="Validate video description chapters (00:00 start, >= 3 chapters, >= 10s step, ascending order).",
    )
    p_chap.add_argument("--description-file", required=True, help="Path to UTF-8 video description text file.")
    p_chap.add_argument("--duration-seconds", type=int, default=None, help="Total video duration in seconds.")
    p_chap.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_chap.add_argument("--output", default="")
    p_chap.add_argument("--overwrite", action="store_true")

    # 13. quiz-lint
    p_quiz = sub.add_parser(
        "quiz-lint",
        help="Validate and compile YouTube Studio Video Quizzes against hard platform limits (<=10 quizzes, <=80 char balanced options, MM:SS:FF).",
    )
    p_quiz.add_argument("--quizzes-file", required=True, help="Path to quizzes JSON file.")
    p_quiz.add_argument("--duration-seconds", type=int, default=None, help="Optional video duration in seconds.")
    p_quiz.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_quiz.add_argument("--output", default="")
    p_quiz.add_argument("--overwrite", action="store_true")

    # 14. thumbnail-check
    p_thumb = sub.add_parser(
        "thumbnail-check",
        help="Validate a PNG or JPEG thumbnail against YouTube's 2 MB limit, dimensions, and aspect ratio.",
    )
    p_thumb.add_argument("--image", required=True, help="Path to PNG or JPEG thumbnail file.")
    p_thumb.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_thumb.add_argument("--output", default="")
    p_thumb.add_argument("--overwrite", action="store_true")

    # 15. draft-freeze
    p_dfreeze = sub.add_parser(
        "draft-freeze",
        help="Freeze a video, title, description, and thumbnail with SHA-256 locks for private-draft upload.",
    )
    p_dfreeze.add_argument("--video", required=True, help="Path to video file (.mp4/.mov).")
    p_dfreeze.add_argument("--title-file", required=True, help="Path to UTF-8 title text file (1..100 chars).")
    p_dfreeze.add_argument("--description-file", required=True, help="Path to UTF-8 description text file (<=5000 chars).")
    p_dfreeze.add_argument("--thumbnail", required=True, help="Path to PNG/JPEG thumbnail (<=2 MB).")
    p_dfreeze.add_argument("--channel-id", required=True, help="Exact target UC... channel ID.")
    p_dfreeze.add_argument("--playlist-title", default="", help="Optional target playlist title.")
    p_dfreeze.add_argument("--category-id", default="27", help="YouTube category ID (default 27 Education).")
    p_dfreeze.add_argument("--language", default="en", help="Default language code (default en).")
    p_dfreeze.add_argument(
        "--notify-subscribers",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Whether YouTube should push upload notifications to subscribers (default False).",
    )
    p_dfreeze.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_dfreeze.add_argument("--output", default="")
    p_dfreeze.add_argument("--overwrite", action="store_true")

    # 16. draft-upload
    p_dupload = sub.add_parser(
        "draft-upload",
        help="Verify frozen SHA-256 asset hashes and upload a video strictly as a private YouTube draft.",
    )
    p_dupload.add_argument("--plan", required=True, help="Path to frozen draft plan JSON from draft-freeze.")
    p_dupload.add_argument("--apply", action="store_true", help="Execute live resumable upload as a private draft.")
    p_dupload.add_argument("--confirm-phrase", default="", help="Exact phrase: 'UPLOAD_PRIVATE_DRAFT <channel_id>'.")
    p_dupload.add_argument("--dotenv", default="")
    p_dupload.add_argument("--token-file", default="")
    p_dupload.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_dupload.add_argument("--output", default="")
    p_dupload.add_argument("--overwrite", action="store_true")

    # 17. comments-triage
    p_comm = sub.add_parser(
        "comments-triage",
        help="Triage viewer comments into questions/requests, timestamp citations, high-signal feedback, and spam.",
    )
    p_comm.add_argument("--from-json", default="", help="Path to offline comments JSON file.")
    p_comm.add_argument("--video-id", default="", help="Live YouTube video ID to fetch commentThreads from.")
    p_comm.add_argument("--channel-id", default="", help="Live YouTube channel ID to fetch commentThreads from.")
    p_comm.add_argument("--max-pages", type=int, default=3, help="Max 100-comment pages to fetch (1 quota unit/page).")
    p_comm.add_argument("--dotenv", default="")
    p_comm.add_argument("--token-file", default="")
    p_comm.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_comm.add_argument("--output", default="")
    p_comm.add_argument("--overwrite", action="store_true")

    # 18. playlists-audit
    p_pl = sub.add_parser(
        "playlists-audit",
        help="Audit channel playlists for orphaned long-form uploads, duplicate items, and private/deleted slots.",
    )
    p_pl.add_argument("--inventory", required=True, help="Path to channel inventory JSON file.")
    p_pl.add_argument("--playlists", required=True, help="Path to playlists JSON file.")
    p_pl.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_pl.add_argument("--output", default="")
    p_pl.add_argument("--overwrite", action="store_true")

    # 19. funnel-audit
    p_fun = sub.add_parser(
        "funnel-audit",
        help="Audit the Shorts-to-Long-Form funnel and recommend top long-form bridge targets.",
    )
    p_fun.add_argument("--inventory", required=True, help="Path to channel inventory JSON file.")
    p_fun.add_argument("--canonical-cta", default="", help="Optional CTA URL to check across Shorts.")
    p_fun.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_fun.add_argument("--output", default="")
    p_fun.add_argument("--overwrite", action="store_true")

    # 20. knowledge-pack
    p_kp = sub.add_parser("knowledge-pack", help="Inspect and verify the attachable Empire knowledge pack.")
    p_kp.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_kp.add_argument("--output", default="")
    p_kp.add_argument("--overwrite", action="store_true")

    # 21. paths / resources
    p_paths = sub.add_parser("paths", help="Resolve installed or checkout recipe and knowledge pack paths.")
    p_paths.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_paths.add_argument("--output", default="")
    p_paths.add_argument("--overwrite", action="store_true")

    p_res = sub.add_parser("resources", help="Resolve full resource manifest and verified knowledge pack files.")
    p_res.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_res.add_argument("--output", default="")
    p_res.add_argument("--overwrite", action="store_true")

    # 22. public-readback
    p_pub = sub.add_parser(
        "public-readback",
        help="Verify public playback, title, description, duration, and oEmbed status for 0 quota units and 0 credentials.",
    )
    p_pub.add_argument("--video-id", required=True, help="Exact 11-character YouTube video ID.")
    p_pub.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_pub.add_argument("--output", default="")
    p_pub.add_argument("--overwrite", action="store_true")

    # 23. related-guard
    p_rel = sub.add_parser(
        "related-guard",
        help="Validate a Shorts-to-Longform Related Video batch and verify the fail-closed confirmation phrase.",
    )
    p_rel.add_argument("--video-ids", required=True, help="Comma-separated allowlist of 11-char Short video IDs.")
    p_rel.add_argument("--target", required=True, help="Exact 11-char target long-form video ID.")
    p_rel.add_argument("--confirm", action="store_true", help="Verify confirmation phrase for live execution.")
    p_rel.add_argument("--phrase", default="", help="Exact phrase: 'SET_RELATED <id> -> <target>' or 'LINK_RELATED_BATCH <N> -> <target>'.")
    p_rel.add_argument("--max-batch", type=int, default=20, help="Hard batch cap (default 20).")
    p_rel.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_rel.add_argument("--output", default="")
    p_rel.add_argument("--overwrite", action="store_true")

    # 24. score-idea
    p_idea = sub.add_parser(
        "score-idea",
        help="Score a pre-recording video candidate using the Perfect Video Score formula, Goldilocks timing rule, and 9-point fit filter.",
    )
    p_idea.add_argument("--title", required=True, help="Candidate video title or thesis.")
    p_idea.add_argument("--days-since-catalyst", type=int, default=14, help="Days since tool/model release or catalyst.")
    p_idea.add_argument("--trend-timing", type=_finite_float_arg, default=7.0, help="1..10 score for rising trend momentum.")
    p_idea.add_argument("--search-surface", type=_finite_float_arg, default=7.0, help="1..10 score for searchable query demand.")
    p_idea.add_argument("--audience-pain", type=_finite_float_arg, default=8.0, help="1..10 score for concrete operator pain.")
    p_idea.add_argument("--channel-dna-fit", type=_finite_float_arg, default=8.0, help="1..10 score for channel DNA alignment.")
    p_idea.add_argument("--proof-advantage", type=_finite_float_arg, default=8.0, help="1..10 score for firsthand demo/system proof.")
    p_idea.add_argument("--packaging-strength", type=_finite_float_arg, default=8.0, help="1..10 score for title + 2-5 word thumbnail hook.")
    p_idea.add_argument("--production-drag", type=_finite_float_arg, default=3.0, help="1..10 score for production complexity/drag.")
    p_idea.add_argument("--platform-risk", type=_finite_float_arg, default=1.0, help="1..10 score for platform/ToS risk.")
    p_idea.add_argument("--hype-saturation", type=_finite_float_arg, default=3.0, help="1..10 score for existing competitor saturation.")
    p_idea.add_argument("--fit-checks", type=int, default=7, help="Number of 9-point Fit Filter questions answered YES (0..9).")
    p_idea.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_idea.add_argument("--output", default="")
    p_idea.add_argument("--overwrite", action="store_true")

    # 25. house-style-lint
    p_hstyle = sub.add_parser(
        "house-style-lint",
        help="Check title and description against Legends lowercase law (preserving standalone I and God), hashtag ban, and CTA block.",
    )
    p_hstyle.add_argument("--title", required=True, help="Video title to inspect.")
    p_hstyle.add_argument("--description", default="", help="Optional inline description text.")
    p_hstyle.add_argument("--description-file", default="", help="Optional path to description file.")
    p_hstyle.add_argument("--cta-block", default="", help="Optional required CTA substring.")
    p_hstyle.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_hstyle.add_argument("--output", default="")
    p_hstyle.add_argument("--overwrite", action="store_true")

    # 26. transcript-package
    p_tpkg = sub.add_parser(
        "transcript-package",
        help="Compile a transcript (.json/.srt/.vtt/.txt) into validated YouTube chapters, Shorts gem-cut candidates, dead-air cut list, and a Release Workbench.",
    )
    p_tpkg.add_argument("--transcript", required=True, help="Path to .json, .srt, .vtt, or bracketed .txt transcript file.")
    p_tpkg.add_argument("--title", default="Untitled Video", help="Video title for the Release Workbench.")
    p_tpkg.add_argument("--target-chapters", type=int, default=6, help="Target number of chapters to generate (default 6).")
    p_tpkg.add_argument("--min-chapter-seconds", type=int, default=45, help="Minimum spacing between chapters in seconds (default 45).")
    p_tpkg.add_argument("--silence-threshold", type=_finite_float_arg, default=1.25, help="Minimum pause gap in seconds to flag as dead air (default 1.25).")
    p_tpkg.add_argument("--canonical-cta", default="", help="Optional canonical CTA URL for Shorts descriptions.")
    p_tpkg.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_tpkg.add_argument("--output", default="")
    p_tpkg.add_argument("--overwrite", action="store_true")

    # 27. channel-outliers
    p_out = sub.add_parser(
        "channel-outliers",
        help="Scout breakout outlier videos (by views and views/day velocity) from an inventory JSON, live Data API v3, or 0-quota public RSS feed.",
    )
    p_out.add_argument("--inventory", default="", help="Optional path to channel inventory JSON.")
    p_out.add_argument("--channel-id", default="", help="Public UC... channel ID (uses 0-quota RSS feed unless --use-api is set).")
    p_out.add_argument("--use-api", action="store_true", help="Use YouTube Data API v3 uploads playlist instead of 0-quota RSS feed.")
    p_out.add_argument("--max-videos", type=int, default=100, help="Max videos when using --use-api (default 100).")
    p_out.add_argument("--threshold", type=_finite_float_arg, default=2.0, help="Outlier multiplier threshold vs channel median (default 2.0x).")
    p_out.add_argument("--dotenv", default="")
    p_out.add_argument("--token-file", default="")
    p_out.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_out.add_argument("--output", default="")
    p_out.add_argument("--overwrite", action="store_true")

    # 28. retention-xray
    p_rx = sub.add_parser(
        "retention-xray",
        help="Correlate a video's retention curve (elapsedVideoTimeRatio / audienceWatchRatio) with exact spoken lines in its transcript.",
    )
    p_rx.add_argument("--transcript", required=True, help="Path to .json, .srt, .vtt, or bracketed .txt transcript file.")
    p_rx.add_argument("--retention-file", required=True, help="Path to retention curve JSON file.")
    p_rx.add_argument("--cliff-threshold", type=_finite_float_arg, default=-0.025, help="Drop threshold per bucket to flag as a cliff (default -0.025 / -2.5 pts).")
    p_rx.add_argument("--json", action=argparse.BooleanOptionalAction, default=True)
    p_rx.add_argument("--output", default="")
    p_rx.add_argument("--overwrite", action="store_true")

    # 29-33. Delegated yt-dlp media archiving, probing, transcription, and clip commands
    sub.add_parser(
        "yt-dlp",
        help="Delegate to the bundled legends-yt-dlp media capture, verification, and word-ledger CLI.",
    )
    sub.add_parser(
        "archive",
        help="Delegate channel/playlist inventory or batch archiving commands to legends-yt-dlp.",
    )
    sub.add_parser(
        "pull",
        help="Delegate preview-first yt-dlp batch planning and capture to legends-yt-dlp.",
    )
    sub.add_parser(
        "transcribe",
        help="Delegate local GPU CrispASR Parakeet transcription to legends-yt-dlp intelligence transcribe.",
    )
    sub.add_parser(
        "clips",
        help="Delegate word-ledger FFmpeg clip planning and rendering to legends-yt-dlp intelligence clips.",
    )

    return parser


_YTDLP_TOP_COMMANDS = {
    "doctor",
    "onboard",
    "setup",
    "mullvad",
    "yt-dlp",
    "plan",
    "inventory",
    "smoke",
    "catalog",
    "ledger",
    "intelligence",
    "preflight",
    "verify",
    "run",
}
_YTDLP_BINARY_SUBCOMMANDS = {"install", "update", "version", "check"}
_DELEGATED_SUBCOMMANDS = {"yt-dlp", "ytdlp", "archive", "pull", "transcribe", "clips"}


def _delegate_to_ytdlp(subcmd: str, rest: list[str]) -> int:
    from legends_ytdlp.cli import main as ytdlp_main

    if subcmd in ("yt-dlp", "ytdlp"):
        if not rest:
            return ytdlp_main(["--help"])
        if rest[0] in _YTDLP_BINARY_SUBCOMMANDS:
            return ytdlp_main(["yt-dlp", *rest])
        return ytdlp_main(rest)

    if subcmd == "archive":
        if not rest:
            return ytdlp_main(["--help"])
        if rest[0] in _YTDLP_TOP_COMMANDS or rest[0] in ("-h", "--help", "--version"):
            return ytdlp_main(rest)
        return ytdlp_main(["inventory", *rest])

    if subcmd == "pull":
        if not rest:
            return ytdlp_main(["plan", "--help"])
        if rest[0] in _YTDLP_TOP_COMMANDS:
            return ytdlp_main(rest)
        return ytdlp_main(["plan", *rest])

    if subcmd == "transcribe":
        if not rest:
            return ytdlp_main(["intelligence", "transcribe", "--help"])
        if rest[0] == "intelligence":
            return ytdlp_main(rest)
        return ytdlp_main(["intelligence", "transcribe", *rest])

    if subcmd == "clips":
        if not rest:
            return ytdlp_main(["intelligence", "clips", "--help"])
        if rest[0] == "intelligence":
            return ytdlp_main(rest)
        if rest[0] in ("plan", "render", "-h", "--help"):
            return ytdlp_main(["intelligence", "clips", *rest])
        return ytdlp_main(["intelligence", "clips", "plan", *rest])

    return ytdlp_main(rest)


def main(argv: list[str] | None = None) -> int:
    eff_argv = list(sys.argv[1:] if argv is None else argv)
    if eff_argv and eff_argv[0] in _DELEGATED_SUBCOMMANDS:
        return _delegate_to_ytdlp(eff_argv[0], eff_argv[1:])
    parser = build_parser()
    args = parser.parse_args(argv)
    cmd = args.command

    try:
        if cmd == "doctor":
            res_info = resolve_resources()
            creds = resolve_credentials(dotenv_path=args.dotenv or None, token_file=args.token_file or None)
            live_channel = None
            if args.expected_channel_id:
                validate_channel_id(args.expected_channel_id)
            if args.live:
                client = YouTubeClient.from_credentials(creds)
                ch = client.get_channel(
                    channel_id=args.expected_channel_id or creds.get("channel_id") or None,
                    mine=bool(creds.get("has_oauth")),
                )
                actual_id = str(ch.get("id") or "")
                if args.expected_channel_id and actual_id != args.expected_channel_id:
                    raise YouTubeError(
                        f"Expected channel {args.expected_channel_id}, but authenticated channel is {actual_id}."
                    )
                live_channel = {
                    "channel_id": actual_id,
                    "title": (ch.get("snippet") or {}).get("title"),
                    "uploads_playlist": ((ch.get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads"),
                }
            ok = bool(res_info["complete"])
            payload = {
                "ok": ok,
                "module": "legends-youtube",
                "version": __version__,
                "python": platform.python_version(),
                "platform": platform.system(),
                "resources": resources_status(),
                "credentials": redact_credential_summary(creds),
                "live_channel": live_channel,
            }
            return _emit(
                payload,
                as_json=args.json,
                output_path=args.output,
                overwrite=args.overwrite,
                exit_code=0 if ok else 1,
            )

        if cmd == "auth-status":
            creds = resolve_credentials(dotenv_path=args.dotenv or None, token_file=args.token_file or None)
            if args.expected_channel_id:
                validate_channel_id(args.expected_channel_id)
            live_info = None
            if args.live:
                client = YouTubeClient.from_credentials(creds)
                ch = client.get_channel(
                    channel_id=args.expected_channel_id or creds.get("channel_id") or None,
                    mine=bool(creds.get("has_oauth")),
                )
                actual_id = str(ch.get("id") or "")
                if args.expected_channel_id and actual_id != args.expected_channel_id:
                    raise YouTubeError(
                        f"Channel lock mismatch: expected {args.expected_channel_id}, got {actual_id}."
                    )
                live_info = {
                    "channel_id": actual_id,
                    "title": (ch.get("snippet") or {}).get("title"),
                    "subscriber_count": int((ch.get("statistics") or {}).get("subscriberCount") or 0),
                    "video_count": int((ch.get("statistics") or {}).get("videoCount") or 0),
                }
            return _emit(
                {
                    "ok": True,
                    "credentials": redact_credential_summary(creds),
                    "live_channel": live_info,
                },
                as_json=args.json,
                output_path=args.output,
                overwrite=args.overwrite,
            )

        if cmd == "quota-plan":
            plan = plan_quota_budget(
                inventory_videos=args.inventory_videos,
                metadata_updates=args.metadata_updates,
                thumbnail_sets=args.thumbnail_sets,
                caption_inserts=args.caption_inserts,
                caption_updates=args.caption_updates,
                draft_uploads=args.draft_uploads,
                search_queries=args.search_queries,
                daily_limit=args.daily_limit,
                safety_reserve=args.safety_reserve,
            )
            return _emit(plan, as_json=args.json, output_path=args.output, overwrite=args.overwrite)

        if cmd == "channel-inventory":
            if args.from_json:
                videos = _load_videos_from_inventory_json(args.from_json)
                return _emit(
                    {
                        "source": "offline_json",
                        "summary": {
                            "inventoried_count": len(videos),
                            "long_count": sum(1 for v in videos if v.get("format") == "long"),
                            "short_count": sum(1 for v in videos if v.get("format") == "short"),
                        },
                        "videos": videos,
                    },
                    as_json=args.json,
                    output_path=args.output,
                    overwrite=args.overwrite,
                )
            creds = resolve_credentials(dotenv_path=args.dotenv or None, token_file=args.token_file or None)
            client = YouTubeClient.from_credentials(creds)
            inv = fetch_channel_inventory(
                client,
                channel_id=args.channel_id or creds.get("channel_id") or None,
                mine=args.mine or (not args.channel_id and bool(creds.get("has_oauth"))),
                max_videos=args.max_videos,
            )
            return _emit(inv, as_json=args.json, output_path=args.output, overwrite=args.overwrite)

        if cmd == "video-inspect":
            creds = resolve_credentials(dotenv_path=args.dotenv or None, token_file=args.token_file or None)
            client = YouTubeClient.from_credentials(creds)
            ids = [part.strip() for part in args.video_ids.split(",") if part.strip()]
            res = inspect_videos(client, ids)
            return _emit(res, as_json=args.json, output_path=args.output, overwrite=args.overwrite)

        if cmd == "metadata-plan":
            if args.from_inventory and args.lowercase_titles:
                videos = _load_videos_from_inventory_json(args.from_inventory)
                updates = []
                allowed = []
                for v in videos:
                    vid = str(v.get("video_id") or "")
                    cur_title = str(v.get("title") or "")
                    new_title = legends_lowercase_title(cur_title)
                    if vid and cur_title and new_title != cur_title:
                        allowed.append(vid)
                        updates.append(
                            {
                                "videoId": vid,
                                "expectedCurrent": {"title": cur_title},
                                "title": new_title,
                            }
                        )
                if not updates:
                    return _emit(
                        {"matched_count": 0, "note": "All video titles already comply with Legends lowercase rule."},
                        as_json=args.json,
                        output_path=args.output,
                        overwrite=args.overwrite,
                    )
                raw_plan = {
                    "schemaVersion": 1,
                    "allowedVideoIds": allowed,
                    "updates": updates,
                    "notes": "Legends lowercase title transformation plan (preserves standalone I and God/God's).",
                }
                preview = preview_metadata_plan(raw_plan)
                return _emit(preview, as_json=args.json, output_path=args.output, overwrite=args.overwrite)

            if not args.plan:
                raise YouTubeError("Pass --plan <path> or (--from-inventory <path> --lowercase-titles).")
            _, raw_plan, _ = safe_read_json_file(args.plan, label="metadata plan JSON")
            preview = preview_metadata_plan(raw_plan)
            return _emit(preview, as_json=args.json, output_path=args.output, overwrite=args.overwrite)

        if cmd == "metadata-apply":
            _, raw_plan, _ = safe_read_json_file(args.plan, label="metadata plan JSON")
            normalized = validate_metadata_plan(raw_plan)
            if not args.confirm:
                preview = execute_metadata_plan(
                    YouTubeClient(),
                    normalized,
                    expected_plan_sha256=args.expected_plan_sha256,
                    confirm=False,
                )
                return _emit(preview, as_json=args.json, output_path=args.output, overwrite=args.overwrite)
            creds = resolve_credentials(dotenv_path=args.dotenv or None, token_file=args.token_file or None)
            client = YouTubeClient.from_credentials(creds)
            result = execute_metadata_plan(
                client,
                normalized,
                expected_plan_sha256=args.expected_plan_sha256,
                confirm=True,
            )
            return _emit(result, as_json=args.json, output_path=args.output, overwrite=args.overwrite)

        if cmd == "links-audit":
            videos = _load_videos_from_inventory_json(args.inventory)
            legacy = [d.strip() for d in args.legacy_domains.split(",") if d.strip()] if args.legacy_domains else []
            report = audit_description_links(
                videos,
                canonical_cta=args.canonical_cta,
                legacy_domains=legacy,
                probe_https=args.probe_https,
            )
            return _emit(report, as_json=args.json, output_path=args.output, overwrite=args.overwrite)

        if cmd == "links-migrate":
            videos = _load_videos_from_inventory_json(args.inventory)
            excl = [v.strip() for v in args.exclude_video_ids.split(",") if v.strip()] if args.exclude_video_ids else []
            fmts = ("long", "short") if args.include_shorts else ("long",)
            mig = generate_link_migration_plan(
                videos,
                find_url=args.find_url,
                replace_url=args.replace_url,
                set_exact_description=args.set_exact_description,
                include_formats=fmts,
                exclude_video_ids=excl,
            )
            return _emit(mig, as_json=args.json, output_path=args.output, overwrite=args.overwrite)

        if cmd == "analytics-audit":
            if args.live:
                start_date = _validate_iso_date(args.start_date, "start-date")
                end_date = _validate_iso_date(args.end_date, "end-date")
                if start_date > end_date:
                    raise YouTubeError(f"Invalid date range: start-date ({start_date}) must not be after end-date ({end_date}).")
                creds = resolve_credentials(dotenv_path=args.dotenv or None, token_file=args.token_file or None)
                client = YouTubeClient.from_credentials(creds)
                raw_report = client.query_analytics_report(
                    start_date=start_date,
                    end_date=end_date,
                )
                parsed_rows = parse_analytics_api_response(raw_report)
                return _emit(
                    {
                        "source": "youtube_analytics_api_v2",
                        "start_date": start_date,
                        "end_date": end_date,
                        "row_count": len(parsed_rows),
                        "rows": parsed_rows,
                    },
                    as_json=args.json,
                    output_path=args.output,
                    overwrite=args.overwrite,
                )
            if not args.export:
                raise YouTubeError("Pass --export <path> for offline Studio analysis or --live for Analytics API v2.")
            _, raw_data, _ = safe_read_json_file(args.export, max_bytes=10 * 1024 * 1024, label="Studio export JSON")
            raw_list = raw_data.get("videos") if isinstance(raw_data, dict) else raw_data
            if not isinstance(raw_list, list):
                raise YouTubeError("Studio export JSON must contain a 'videos' list or be a JSON list.")
            records = normalize_records(raw_list)
            health = channel_health(records)
            pkg = packaging_audit(records)
            out_payload: dict[str, Any] = {
                "channel_name": args.channel_name,
                "channel_health": health,
                "packaging_audit": pkg,
            }
            if args.markdown:
                out_payload["scorecard_markdown"] = render_scorecard_markdown(records, channel_name=args.channel_name)
            return _emit(out_payload, as_json=args.json, output_path=args.output, overwrite=args.overwrite)

        if cmd == "packaging-audit":
            _, raw_data, _ = safe_read_json_file(args.export, max_bytes=10 * 1024 * 1024, label="Studio export JSON")
            raw_list = raw_data.get("videos") if isinstance(raw_data, dict) else raw_data
            if not isinstance(raw_list, list):
                raise YouTubeError("Studio export JSON must contain a 'videos' list or be a JSON list.")
            records = normalize_records(raw_list)
            pkg = packaging_audit(records, min_impressions=args.min_impressions)
            return _emit(pkg, as_json=args.json, output_path=args.output, overwrite=args.overwrite)

        if cmd == "chapters-lint":
            _, desc_text = safe_read_text_file(args.description_file, label="description file")
            res = lint_chapters(desc_text, video_duration_seconds=args.duration_seconds)
            return _emit(
                res,
                as_json=args.json,
                output_path=args.output,
                overwrite=args.overwrite,
                exit_code=0 if res.get("valid") else 1,
            )

        if cmd == "quiz-lint":
            _, quiz_data, _ = safe_read_json_file(args.quizzes_file, label="quizzes JSON file")
            res = lint_studio_quizzes(quiz_data, video_duration_seconds=args.duration_seconds)
            return _emit(
                res,
                as_json=args.json,
                output_path=args.output,
                overwrite=args.overwrite,
                exit_code=0 if res.get("valid") else 1,
            )

        if cmd == "thumbnail-check":
            res = inspect_thumbnail(args.image)
            return _emit(res, as_json=args.json, output_path=args.output, overwrite=args.overwrite)

        if cmd == "draft-freeze":
            frozen = freeze_draft_plan(
                video_path=args.video,
                title_path=args.title_file,
                description_path=args.description_file,
                thumbnail_path=args.thumbnail,
                channel_id=args.channel_id,
                playlist_title=args.playlist_title,
                category_id=args.category_id,
                language=args.language,
                notify_subscribers=args.notify_subscribers,
            )
            return _emit(frozen, as_json=args.json, output_path=args.output, overwrite=args.overwrite)

        if cmd == "draft-upload":
            _, frozen_data, _ = safe_read_json_file(args.plan, label="frozen draft plan JSON")
            if not args.apply:
                res = execute_private_draft_upload(YouTubeClient(), frozen_data, apply=False)
                return _emit(res, as_json=args.json, output_path=args.output, overwrite=args.overwrite)
            creds = resolve_credentials(dotenv_path=args.dotenv or None, token_file=args.token_file or None)
            client = YouTubeClient.from_credentials(creds)
            res = execute_private_draft_upload(
                client,
                frozen_data,
                confirm_phrase=args.confirm_phrase,
                apply=True,
            )
            return _emit(res, as_json=args.json, output_path=args.output, overwrite=args.overwrite)

        if cmd == "comments-triage":
            if args.from_json:
                _, raw_comments, _ = safe_read_json_file(args.from_json, max_bytes=10 * 1024 * 1024, label="comments JSON")
                if isinstance(raw_comments, dict):
                    if "items" in raw_comments and raw_comments.get("items") is not None:
                        items = raw_comments.get("items")
                    elif "comments" in raw_comments and raw_comments.get("comments") is not None:
                        items = raw_comments.get("comments")
                    else:
                        items = []
                else:
                    items = raw_comments
                if not isinstance(items, list):
                    raise YouTubeError("Comments JSON must contain an 'items'/'comments' list or be a JSON list.")
                res = triage_comments(items)
                return _emit(res, as_json=args.json, output_path=args.output, overwrite=args.overwrite)
            creds = resolve_credentials(dotenv_path=args.dotenv or None, token_file=args.token_file or None)
            client = YouTubeClient.from_credentials(creds)
            res = fetch_and_triage_comments(
                client,
                video_id=args.video_id,
                channel_id=args.channel_id or creds.get("channel_id") or "",
                max_pages=args.max_pages,
            )
            return _emit(res, as_json=args.json, output_path=args.output, overwrite=args.overwrite)

        if cmd == "playlists-audit":
            videos = _load_videos_from_inventory_json(args.inventory)
            _, pl_raw, _ = safe_read_json_file(args.playlists, max_bytes=10 * 1024 * 1024, label="playlists JSON")
            if isinstance(pl_raw, dict):
                if "playlists" in pl_raw and pl_raw.get("playlists") is not None:
                    pl_list = pl_raw.get("playlists")
                elif "items" in pl_raw and pl_raw.get("items") is not None:
                    pl_list = pl_raw.get("items")
                else:
                    pl_list = []
            else:
                pl_list = pl_raw
            if not isinstance(pl_list, list):
                raise YouTubeError("Playlists JSON must contain a 'playlists'/'items' list or be a JSON list.")
            res = audit_playlists(videos, pl_list)
            return _emit(res, as_json=args.json, output_path=args.output, overwrite=args.overwrite)

        if cmd == "funnel-audit":
            videos = _load_videos_from_inventory_json(args.inventory)
            res = audit_shorts_funnel(videos, canonical_cta=args.canonical_cta)
            return _emit(res, as_json=args.json, output_path=args.output, overwrite=args.overwrite)

        if cmd == "knowledge-pack":
            info = resolve_resources()
            ok = bool(info["complete"])
            return _emit(
                {
                    "ok": ok,
                    "source": info["source"],
                    "pack_manifest": info["pack_manifest"],
                    "verified_files": info["verified_files"],
                    "note": info["note"],
                    "ontology": (info["manifest"] or {}).get("ontology"),
                },
                as_json=args.json,
                output_path=args.output,
                overwrite=args.overwrite,
                exit_code=0 if ok else 1,
            )

        if cmd in ("paths", "resources"):
            info = resolve_resources()
            if cmd == "resources":
                return _emit(info, as_json=args.json, output_path=args.output, overwrite=args.overwrite)
            return _emit(
                {
                    "source": info["source"],
                    "root": info["root"],
                    "recipe": info["recipe"],
                    "pack_dir": info["pack_dir"],
                    "pack_manifest": info["pack_manifest"],
                    "verified_files": info["verified_files"],
                    "complete": info["complete"],
                },
                as_json=args.json,
                output_path=args.output,
                overwrite=args.overwrite,
            )

        if cmd == "public-readback":
            res = public_video_readback(args.video_id)
            return _emit(res, as_json=args.json, output_path=args.output, overwrite=args.overwrite)

        if cmd == "related-guard":
            vids = [v.strip() for v in args.video_ids.split(",") if v.strip()]
            res = validate_related_video_guard(
                vids,
                args.target,
                confirm=args.confirm,
                phrase=args.phrase,
                max_batch=args.max_batch,
            )
            return _emit(
                res,
                as_json=args.json,
                output_path=args.output,
                overwrite=args.overwrite,
                exit_code=0 if res.get("valid") else 1,
            )

        if cmd == "score-idea":
            res = score_video_idea(
                title=args.title,
                days_since_catalyst=args.days_since_catalyst,
                trend_timing=args.trend_timing,
                search_surface=args.search_surface,
                audience_pain=args.audience_pain,
                channel_dna_fit=args.channel_dna_fit,
                proof_advantage=args.proof_advantage,
                packaging_strength=args.packaging_strength,
                production_drag=args.production_drag,
                platform_risk=args.platform_risk,
                hype_saturation=args.hype_saturation,
                fit_checks_passed=args.fit_checks,
            )
            return _emit(res, as_json=args.json, output_path=args.output, overwrite=args.overwrite)

        if cmd == "house-style-lint":
            desc_text = args.description
            if args.description_file:
                _, desc_text = safe_read_text_file(
                    args.description_file, max_bytes=256 * 1024, label="description file"
                )
            res = lint_house_style(args.title, desc_text, cta_block=args.cta_block)
            return _emit(
                res,
                as_json=args.json,
                output_path=args.output,
                overwrite=args.overwrite,
                exit_code=0 if res.get("valid") else 1,
            )

        if cmd == "transcript-package":
            res = compile_transcript_package(
                args.transcript,
                video_title=args.title,
                target_chapters=args.target_chapters,
                min_chapter_seconds=args.min_chapter_seconds,
                silence_threshold_seconds=args.silence_threshold,
                canonical_cta=args.canonical_cta,
            )
            return _emit(res, as_json=args.json, output_path=args.output, overwrite=args.overwrite)

        if cmd == "channel-outliers":
            if args.inventory:
                videos = _load_videos_from_inventory_json(args.inventory)
            elif args.channel_id and args.use_api:
                creds = resolve_credentials(dotenv_path=args.dotenv or None, token_file=args.token_file or None)
                client = YouTubeClient.from_credentials(creds)
                inv = fetch_channel_inventory(client, channel_id=args.channel_id, max_videos=args.max_videos)
                videos = inv["videos"]
            elif args.channel_id:
                videos = fetch_public_channel_feed(args.channel_id)
            else:
                raise YouTubeError("Provide --inventory <file.json> or --channel-id <UC...>.")
            res = scout_channel_outliers(videos, outlier_threshold_multiplier=args.threshold)
            return _emit(res, as_json=args.json, output_path=args.output, overwrite=args.overwrite)

        if cmd == "retention-xray":
            _, ret_data, _ = safe_read_json_file(args.retention_file, max_bytes=10 * 1024 * 1024, label="retention JSON")
            res = correlate_retention_with_transcript(
                args.transcript,
                ret_data,
                cliff_drop_threshold=args.cliff_threshold,
            )
            return _emit(res, as_json=args.json, output_path=args.output, overwrite=args.overwrite)

    except (YouTubeError, ValueError, OSError) as exc:
        err_payload = {
            "ok": False,
            "error": scrub_secrets(str(exc)),
            "status": getattr(exc, "status", None),
            "reason": getattr(exc, "reason", None),
        }
        print(json.dumps(err_payload, indent=2), file=sys.stderr)
        return 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
