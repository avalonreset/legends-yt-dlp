"""SHA-256 frozen private-draft upload manifest, pure-stdlib PNG/JPEG thumbnail inspection, and resumable upload guard."""
from __future__ import annotations

import hashlib
import http.client
import json
import re
import struct
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .api import (
    YouTubeClient,
    YouTubeError,
    _reject_symlink_chain,
    build_safe_opener,
    safe_read_text_file,
    scrub_secrets,
    validate_channel_id,
)

MAX_THUMBNAIL_BYTES = 2 * 1024 * 1024  # 2 MB YouTube Data API thumbnails.set limit
MAX_VIDEO_BYTES = 256 * 1024 * 1024 * 1024  # 256 GB YouTube upload limit
DEFAULT_CHUNK_BYTES = 8 * 1024 * 1024


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a regular file after rejecting symlinks."""
    _reject_symlink_chain(path)
    resolved = path.resolve()
    if not resolved.is_file() or resolved.is_symlink():
        raise YouTubeError(f"Refusing to hash missing or symlinked file: {path}")
    digest = hashlib.sha256()
    with resolved.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    idx = 2
    n = len(data)
    sof_markers = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while idx + 4 < n:
        if data[idx] != 0xFF:
            idx += 1
            continue
        while idx < n and data[idx] == 0xFF:
            idx += 1
        if idx >= n:
            break
        marker = data[idx]
        idx += 1
        if marker in (0xD8, 0xD9) or (0xD0 <= marker <= 0xD7):
            continue
        if idx + 2 > n:
            break
        seg_len = struct.unpack(">H", data[idx : idx + 2])[0]
        if seg_len < 2 or idx + seg_len > n:
            break
        if marker in sof_markers and idx + 7 <= n:
            height, width = struct.unpack(">HH", data[idx + 3 : idx + 7])
            return width, height
        idx += seg_len
    return None


def inspect_thumbnail(path: str | Path) -> dict[str, Any]:
    """Validate a YouTube thumbnail file (PNG or JPEG, <= 2 MB, dimensions and aspect ratio) using pure stdlib."""
    raw_path = Path(path).expanduser()
    _reject_symlink_chain(raw_path)
    resolved = raw_path.resolve()
    if not resolved.is_file() or resolved.is_symlink():
        raise YouTubeError(f"Thumbnail file does not exist or is a symlink: {resolved}")
    size = resolved.stat().st_size
    if size <= 0:
        raise YouTubeError(f"Thumbnail file is empty: {resolved}")
    if size > MAX_THUMBNAIL_BYTES:
        raise YouTubeError(
            f"Thumbnail exceeds YouTube Data API 2 MB (2,097,152 bytes) limit: {size} bytes ({resolved.name})"
        )

    header = resolved.read_bytes()
    fmt: str | None = None
    width = 0
    height = 0

    if len(header) >= 24 and header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR":
        fmt = "PNG"
        width, height = struct.unpack(">II", header[16:24])
    elif header[:2] == b"\xff\xd8":
        dims = _parse_jpeg_dimensions(header)
        if dims:
            fmt = "JPEG"
            width, height = dims

    if not fmt or width <= 0 or height <= 0:
        raise YouTubeError(f"Thumbnail must be a valid PNG or JPEG image: {resolved.name}")

    ratio = round(width / height, 4)
    is_16_9 = abs(ratio - (16.0 / 9.0)) <= 0.02
    is_square = width == height
    warnings: list[str] = []
    if width < 1280 or height < 720:
        warnings.append(f"Resolution {width}x{height} is below YouTube's recommended 1280x720 minimum.")
    if not (is_16_9 or is_square):
        warnings.append(f"Aspect ratio {width}x{height} ({ratio}) is neither 16:9 widescreen nor 1:1 square.")

    return {
        "valid": True,
        "path": str(resolved),
        "format": fmt,
        "width": width,
        "height": height,
        "aspect_ratio": ratio,
        "is_16_9": is_16_9,
        "bytes": size,
        "max_bytes": MAX_THUMBNAIL_BYTES,
        "sha256": hashlib.sha256(header).hexdigest(),
        "warnings": warnings,
    }


_VIDEO_MIME_MAP = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
}
_RANGE_HEADER_RE = re.compile(r"bytes=0-(\d+)", re.IGNORECASE)


def _video_mime_type(path: Path) -> str:
    return _VIDEO_MIME_MAP.get(path.suffix.lower(), "application/octet-stream")


def _canonical_draft_plan_sha256(plan_core: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(plan_core, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def confirmation_phrase(channel_id: str) -> str:
    return f"UPLOAD_PRIVATE_DRAFT {channel_id}"


def freeze_draft_plan(
    *,
    video_path: str | Path,
    title_path: str | Path,
    description_path: str | Path,
    thumbnail_path: str | Path,
    channel_id: str,
    playlist_title: str = "",
    category_id: str = "27",
    language: str = "en",
    notify_subscribers: bool = False,
) -> dict[str, Any]:
    """Create a SHA-256 hash-locked private-draft upload plan after verifying all 4 local assets."""
    clean_channel_id = validate_channel_id(channel_id)
    vid_raw = Path(video_path).expanduser()
    _reject_symlink_chain(vid_raw)
    vid_resolved = vid_raw.resolve()
    if not vid_resolved.is_file() or vid_resolved.is_symlink():
        raise YouTubeError(f"Video file not found or is a symlink: {vid_resolved}")
    vid_bytes = vid_resolved.stat().st_size
    if vid_bytes <= 0:
        raise YouTubeError(f"Video file is empty: {vid_resolved}")
    if vid_bytes > MAX_VIDEO_BYTES:
        raise YouTubeError(f"Video file exceeds YouTube 256 GB limit: {vid_bytes} bytes")

    title_resolved, title_raw = safe_read_text_file(title_path, label="title file")
    desc_resolved, desc_raw = safe_read_text_file(description_path, label="description file")
    title = title_raw.rstrip("\r\n")
    description = desc_raw.rstrip("\r\n")

    if not title.strip() or not (1 <= len(title) <= 100):
        raise YouTubeError(f"Title must be 1..100 non-whitespace characters (got {len(title)}).")
    if "<" in title or ">" in title:
        raise YouTubeError("Title must not contain '<' or '>' angle brackets (rejected by YouTube Data API v3).")
    if len(description) > 5000:
        raise YouTubeError(f"Description must be <= 5000 characters (got {len(description)}).")
    if "<" in description or ">" in description:
        raise YouTubeError("Description must not contain '<' or '>' angle brackets (rejected by YouTube Data API v3).")

    thumb_info = inspect_thumbnail(thumbnail_path)

    paths = {
        "video": str(vid_resolved),
        "title": str(title_resolved),
        "description": str(desc_resolved),
        "thumbnail": thumb_info["path"],
    }
    sha256_map = {
        "video": sha256_file(vid_resolved),
        "title": sha256_file(title_resolved),
        "description": sha256_file(desc_resolved),
        "thumbnail": thumb_info["sha256"],
    }
    bytes_map = {
        "video": vid_bytes,
        "title": title_resolved.stat().st_size,
        "description": desc_resolved.stat().st_size,
        "thumbnail": thumb_info["bytes"],
    }

    plan_core = {
        "schemaVersion": 1,
        "channelId": clean_channel_id,
        "playlistTitle": playlist_title.strip(),
        "title": title,
        "description": description,
        "categoryId": str(category_id),
        "language": str(language),
        "privacyStatus": "private",
        "notifySubscribers": bool(notify_subscribers),
        "selfDeclaredMadeForKids": False,
        "containsSyntheticMedia": False,
        "paths": paths,
        "bytes": bytes_map,
        "sha256": sha256_map,
        "thumbnail": {
            "format": thumb_info["format"],
            "width": thumb_info["width"],
            "height": thumb_info["height"],
        },
    }
    plan_hash = _canonical_draft_plan_sha256(plan_core)
    return {
        "frozen_at": utc_now(),
        "plan_sha256": plan_hash,
        "required_confirmation": confirmation_phrase(clean_channel_id),
        "plan": plan_core,
    }


def verify_frozen_draft_plan(frozen_envelope: dict[str, Any]) -> dict[str, Any]:
    """Re-verify that all 4 local files and the canonical plan_sha256 in a frozen draft plan are untampered."""
    if not isinstance(frozen_envelope, dict):
        raise YouTubeError("Invalid frozen draft plan structure.")
    has_envelope = "plan" in frozen_envelope or "plan_sha256" in frozen_envelope
    plan = frozen_envelope.get("plan") if "plan" in frozen_envelope else frozen_envelope
    if not isinstance(plan, dict):
        raise YouTubeError("Invalid frozen draft plan structure.")
    if has_envelope:
        expected_plan_sha = str(frozen_envelope.get("plan_sha256") or "").strip().lower()
        actual_plan_sha = _canonical_draft_plan_sha256(plan).lower()
        if not expected_plan_sha or actual_plan_sha != expected_plan_sha:
            raise YouTubeError(
                f"Frozen draft plan_sha256 mismatch or tamper detected: expected {expected_plan_sha!r}, calculated {actual_plan_sha!r}."
            )
    if plan.get("privacyStatus") != "private":
        raise YouTubeError("Draft uploader strictly enforces privacyStatus='private'.")
    validate_channel_id(str(plan.get("channelId") or ""))
    paths = plan.get("paths")
    expected_hashes = plan.get("sha256")
    if not isinstance(paths, dict) or not isinstance(expected_hashes, dict):
        raise YouTubeError("Frozen draft plan 'paths' and 'sha256' must be JSON objects.")
    for key in ("video", "title", "description", "thumbnail"):
        raw_p = str(paths.get(key) or "").strip()
        if not raw_p:
            raise YouTubeError(f"Missing path for {key} in frozen draft plan.")
        p = Path(raw_p)
        actual = sha256_file(p)
        expected = str(expected_hashes.get(key) or "").lower()
        if not expected or actual.lower() != expected:
            raise YouTubeError(f"Asset drift detected on {key} ({p.name}): expected {expected}, got {actual}.")

    _, disk_title_raw = safe_read_text_file(paths["title"], label="title file")
    _, disk_desc_raw = safe_read_text_file(paths["description"], label="description file")
    disk_title = disk_title_raw.rstrip("\r\n")
    disk_desc = disk_desc_raw.rstrip("\r\n")
    if str(plan.get("title") or "") != disk_title:
        raise YouTubeError("Frozen draft plan title does not match verified title file on disk.")
    if str(plan.get("description") or "") != disk_desc:
        raise YouTubeError("Frozen draft plan description does not match verified description file on disk.")
    if not disk_title.strip() or not (1 <= len(disk_title) <= 100) or "<" in disk_title or ">" in disk_title:
        raise YouTubeError("Frozen draft title violates YouTube length or angle-bracket constraints.")
    if len(disk_desc) > 5000 or "<" in disk_desc or ">" in disk_desc:
        raise YouTubeError("Frozen draft description violates YouTube length or angle-bracket constraints.")
    return plan


def build_resumable_insert_body(plan: dict[str, Any]) -> dict[str, Any]:
    """Construct the YouTube Data API v3 videos.insert JSON body for a private draft."""
    if plan.get("privacyStatus") != "private":
        raise YouTubeError("Refusing to build upload body with non-private privacyStatus.")
    return {
        "snippet": {
            "title": plan["title"],
            "description": plan["description"],
            "categoryId": str(plan.get("categoryId") or "27"),
            "defaultLanguage": str(plan.get("language") or "en"),
        },
        "status": {
            "privacyStatus": "private",
            "license": "youtube",
            "embeddable": True,
            "publicStatsViewable": True,
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": False,
        },
    }


def execute_private_draft_upload(
    client: YouTubeClient,
    frozen_envelope: dict[str, Any],
    *,
    confirm_phrase: str = "",
    apply: bool = False,
) -> dict[str, Any]:
    """Verify frozen asset hashes and execute a private-draft resumable upload when apply=True and confirm_phrase matches."""
    plan = verify_frozen_draft_plan(frozen_envelope)
    channel_id = validate_channel_id(str(plan.get("channelId") or ""))
    expected_phrase = confirmation_phrase(channel_id)

    if not apply:
        return {
            "mode": "dry_run_verified",
            "channel_id": channel_id,
            "privacy_status": "private",
            "assets_verified": True,
            "required_confirmation": expected_phrase,
            "insert_body": build_resumable_insert_body(plan),
        }

    if confirm_phrase.strip() != expected_phrase:
        raise YouTubeError(f"Confirmation phrase mismatch: expected {expected_phrase!r}.")

    # Verify authenticated OAuth channel matches target channel_id before uploading a single byte
    live_channel = client.get_channel(mine=True)
    live_channel_id = str(live_channel.get("id") or "")
    if live_channel_id != channel_id:
        raise YouTubeError(
            f"Authenticated channel ({live_channel_id}) does not match frozen plan channelId ({channel_id}). Refusing upload."
        )

    token = client.ensure_access_token()
    video_path = Path(plan["paths"]["video"]).resolve()
    video_size = video_path.stat().st_size
    video_mime = _video_mime_type(video_path)
    body_bytes = json.dumps(build_resumable_insert_body(plan)).encode("utf-8")

    init_url = (
        f"{client.upload_base_url}/videos?uploadType=resumable&part=snippet,status"
        f"&notifySubscribers={'true' if plan.get('notifySubscribers', False) else 'false'}"
    )
    client._validate_api_url(init_url)
    init_req = urllib.request.Request(
        init_url,
        data=body_bytes,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
            "X-Upload-Content-Length": str(video_size),
            "X-Upload-Content-Type": video_mime,
        },
    )
    opener = getattr(client, "_opener", None) or build_safe_opener()
    try:
        with opener.open(init_req, timeout=client.timeout) as resp:
            session_uri = resp.headers.get("Location") or ""
    except urllib.error.HTTPError as exc:
        err_body = ""
        try:
            err_body = exc.read(65536).decode("utf-8", errors="replace")
        except Exception:
            pass
        raise YouTubeError(
            f"Resumable upload initiation failed ({exc.code}): {scrub_secrets(err_body or str(exc))}",
            status=exc.code,
        ) from None
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
        raise YouTubeError(f"Resumable upload initiation network error: {scrub_secrets(str(exc))}") from None

    if not session_uri:
        raise YouTubeError("YouTube resumable upload initiation did not return a Location header.")
    client._validate_api_url(session_uri)

    uploaded_resource: dict[str, Any] = {}
    with video_path.open("rb") as fh:
        offset = 0
        while offset < video_size:
            fh.seek(offset)
            chunk = fh.read(DEFAULT_CHUNK_BYTES)
            if not chunk:
                break
            end_byte = offset + len(chunk) - 1
            chunk_req = urllib.request.Request(
                session_uri,
                data=chunk,
                method="PUT",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {offset}-{end_byte}/{video_size}",
                    "Content-Type": video_mime,
                },
            )
            try:
                with opener.open(chunk_req, timeout=max(60.0, client.timeout)) as chunk_resp:
                    raw = chunk_resp.read(1024 * 1024 + 1)
                    if len(raw) > 1024 * 1024:
                        raise YouTubeError("Resumable upload response exceeded 1 MiB safety cap.")
                    if raw:
                        try:
                            uploaded_resource = json.loads(raw.decode("utf-8"))
                        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                            raise YouTubeError(f"Invalid JSON in resumable upload response: {scrub_secrets(str(exc))}") from None
            except urllib.error.HTTPError as exc:
                if exc.code == 308:
                    range_hdr = (exc.headers.get("Range") or exc.headers.get("range") or "") if exc.headers else ""
                    m = _RANGE_HEADER_RE.search(range_hdr)
                    if m:
                        next_offset = int(m.group(1)) + 1
                        if next_offset <= offset:
                            raise YouTubeError(
                                f"Resumable upload made no forward progress at byte {offset} (Range: {range_hdr!r})."
                            ) from None
                        offset = next_offset
                    else:
                        offset = end_byte + 1
                    continue
                err_body = ""
                try:
                    err_body = exc.read(65536).decode("utf-8", errors="replace")
                except Exception:
                    pass
                raise YouTubeError(
                    f"Resumable chunk upload failed at byte {offset} ({exc.code}): {scrub_secrets(err_body or str(exc))}",
                    status=exc.code,
                ) from None
            except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
                raise YouTubeError(f"Resumable chunk upload network error at byte {offset}: {scrub_secrets(str(exc))}") from None
            offset = end_byte + 1

    video_id = str(uploaded_resource.get("id") or "").strip()
    if not video_id:
        raise YouTubeError("Resumable upload completed without returning a YouTube video ID.")
    return {
        "mode": "uploaded_private_draft",
        "uploaded_at": utc_now(),
        "channel_id": channel_id,
        "video_id": video_id,
        "privacy_status": (uploaded_resource.get("status") or {}).get("privacyStatus", "private"),
    }
