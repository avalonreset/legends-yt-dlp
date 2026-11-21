"""Validators for YouTube description chapters, Studio video quizzes (ytve-posts-modal), and channel-wide description links."""
from __future__ import annotations

import http.client
import re
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .api import (
    build_safe_opener,
    resolve_public_https_ips,
    scrub_secrets,
    validate_public_https_host,
    validate_video_id,
)
from .inventory import extract_chapter_lines, extract_urls

MIN_CHAPTER_COUNT = 3
MIN_CHAPTER_DURATION_SECONDS = 10

MAX_QUIZZES_PER_VIDEO = 10
QUIZ_OPTION_MAX_CHARS = 80
QUIZ_OPTION_TARGET_MIN_CHARS = 60
QUIZ_OPTION_TARGET_MAX_CHARS = 75
QUIZ_OPTION_MAX_SPREAD_CHARS = 15
QUIZ_EXPLANATION_MAX_CHARS = 500
QUIZ_TIMESTAMP_RE = re.compile(r"^(?P<mm>\d{2}):(?P<ss>[0-5]\d):(?P<ff>[0-5]\d)$")


def lint_chapters(description: str, *, video_duration_seconds: int | None = None) -> dict[str, Any]:
    """Validate YouTube description chapter timestamps against YouTube's official chapter parser rules."""
    chapters = extract_chapter_lines(description)
    errors: list[str] = []
    warnings: list[str] = []

    if not chapters:
        return {
            "valid": False,
            "chapter_count": 0,
            "chapters": [],
            "errors": ["No timestamped chapter lines found in description."],
            "warnings": [],
        }

    if len(chapters) < MIN_CHAPTER_COUNT:
        errors.append(
            f"YouTube requires at least {MIN_CHAPTER_COUNT} chapters to activate video chapters (found {len(chapters)})."
        )

    if chapters[0]["seconds"] != 0:
        errors.append(
            f"First chapter must start at 00:00 (0 seconds), but starts at {chapters[0]['timestamp']} ({chapters[0]['seconds']}s)."
        )

    enriched: list[dict[str, Any]] = []
    for idx, chap in enumerate(chapters):
        sec = chap["seconds"]
        title = chap["title"]
        next_sec = chapters[idx + 1]["seconds"] if idx + 1 < len(chapters) else video_duration_seconds
        span: int | None = None
        if idx > 0:
            prev_sec = chapters[idx - 1]["seconds"]
            if sec <= prev_sec:
                errors.append(
                    f"Chapter #{idx + 1} ({chap['timestamp']} {title!r}) is not strictly ascending after {chapters[idx - 1]['timestamp']}."
                )
        if next_sec is not None:
            span = next_sec - sec
            if span < MIN_CHAPTER_DURATION_SECONDS:
                errors.append(
                    f"Chapter #{idx + 1} ({chap['timestamp']} {title!r}) is only {span}s long; YouTube requires >= {MIN_CHAPTER_DURATION_SECONDS}s per chapter."
                )
        if len(title) < 3:
            warnings.append(f"Chapter #{idx + 1} ({chap['timestamp']}) has a very short title ({title!r}).")
        if len(title) > 60:
            warnings.append(f"Chapter #{idx + 1} ({chap['timestamp']}) exceeds 60 characters ({len(title)} chars) and may truncate on mobile.")

        enriched.append(
            {
                "index": idx + 1,
                "timestamp": chap["timestamp"],
                "seconds": sec,
                "duration_seconds": span,
                "title": title,
            }
        )

    return {
        "valid": len(errors) == 0,
        "chapter_count": len(enriched),
        "video_duration_seconds": video_duration_seconds,
        "chapters": enriched,
        "errors": errors,
        "warnings": warnings,
    }


def lint_studio_quizzes(
    quizzes_data: dict[str, Any] | list[dict[str, Any]],
    *,
    video_duration_seconds: int | None = None,
) -> dict[str, Any]:
    """Validate and compile YouTube Studio Video Quizzes (`ytve-posts-modal`) against hard platform limits."""
    if isinstance(quizzes_data, dict):
        raw_list = quizzes_data.get("quizzes") if "quizzes" in quizzes_data and quizzes_data.get("quizzes") is not None else []
        if not isinstance(raw_list, list):
            raise ValueError("Quizzes 'quizzes' field must be a JSON list.")
        if video_duration_seconds is None and quizzes_data.get("video_duration_seconds") is not None:
            raw_dur = quizzes_data["video_duration_seconds"]
            if isinstance(raw_dur, bool) or not isinstance(raw_dur, (int, float)):
                raise ValueError("Quizzes 'video_duration_seconds' must be an integer.")
            video_duration_seconds = int(raw_dur)
    elif isinstance(quizzes_data, list):
        raw_list = quizzes_data
    else:
        raise ValueError("Quizzes payload must be a JSON object with 'quizzes' or a JSON list.")

    errors: list[str] = []
    warnings: list[str] = []

    if not raw_list:
        errors.append("Quizzes list is empty.")
    if len(raw_list) > MAX_QUIZZES_PER_VIDEO:
        errors.append(
            f"Quiz count ({len(raw_list)}) exceeds YouTube Studio maximumPostsCount limit of {MAX_QUIZZES_PER_VIDEO}."
        )

    compiled: list[dict[str, Any]] = []
    seen_timestamps: set[str] = set()

    for idx, item in enumerate(raw_list):
        label = f"Quiz #{idx + 1}"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object.")
            continue
        question = str(item.get("question") or "").strip()
        timestamp = str(item.get("timestamp") or "").strip()
        explanation = str(item.get("explanation") or "").strip()
        options_raw = item.get("options") or []
        correct_index = item.get("correct_index")

        if not question:
            errors.append(f"{label}: question stem is empty.")
        elif "\n" in question or "\r" in question:
            errors.append(f"{label}: question stem contains a newline (isNewLineForbidden=true in Studio).")
        elif not (85 <= len(question) <= 130):
            warnings.append(
                f"{label}: question stem is {len(question)} chars (recommended framing band is 85..130 chars so options stay concise)."
            )

        ts_match = QUIZ_TIMESTAMP_RE.fullmatch(timestamp)
        ts_seconds = 0
        if not ts_match:
            errors.append(
                f"{label}: timestamp {timestamp!r} must use 8-character MM:SS:FF format (e.g. '05:25:00')."
            )
        else:
            mm = int(ts_match.group("mm"))
            ss = int(ts_match.group("ss"))
            ts_seconds = mm * 60 + ss
            if timestamp == "00:00:00":
                warnings.append(
                    f"{label}: timestamp is 00:00:00; Studio creates new quizzes at 00:00:00 before re-sorting, so prefer non-zero timestamps."
                )
            if timestamp in seen_timestamps:
                errors.append(f"{label}: duplicate quiz timestamp {timestamp}.")
            seen_timestamps.add(timestamp)
            if video_duration_seconds is not None and ts_seconds >= video_duration_seconds:
                errors.append(
                    f"{label}: timestamp {timestamp} ({ts_seconds}s) is at or beyond video duration ({video_duration_seconds}s)."
                )

        if len(explanation) > QUIZ_EXPLANATION_MAX_CHARS:
            errors.append(
                f"{label}: explanation is {len(explanation)} chars, exceeding QUIZ_EXPLANATION_TEXT_TOO_LONG ({QUIZ_EXPLANATION_MAX_CHARS} max)."
            )

        if not isinstance(options_raw, list) or not (2 <= len(options_raw) <= 4):
            errors.append(f"{label}: must supply 2 to 4 answer options (found {len(options_raw) if isinstance(options_raw, list) else 0}).")
            continue

        option_texts: list[str] = []
        resolved_correct_indices: list[int] = []
        for opt_i, opt in enumerate(options_raw):
            if isinstance(opt, dict):
                opt_text = str(opt.get("text") or "").strip()
                if opt.get("is_correct") is True:
                    resolved_correct_indices.append(opt_i)
            else:
                opt_text = str(opt or "").strip()
            option_texts.append(opt_text)

        if (
            isinstance(correct_index, int)
            and not isinstance(correct_index, bool)
            and 0 <= correct_index < len(option_texts)
        ):
            if correct_index not in resolved_correct_indices:
                resolved_correct_indices.append(correct_index)

        if len(resolved_correct_indices) != 1:
            errors.append(
                f"{label}: must specify exactly 1 correct option via 'correct_index' (0..{len(option_texts) - 1}) or 'is_correct: true'."
            )
        correct_idx = resolved_correct_indices[0] if len(resolved_correct_indices) == 1 else 0

        lengths = [len(t) for t in option_texts]
        for opt_i, text in enumerate(option_texts):
            opt_letter = chr(ord("A") + opt_i)
            if not text:
                errors.append(f"{label} Option {opt_letter}: text is empty.")
            if "\n" in text or "\r" in text:
                errors.append(f"{label} Option {opt_letter}: contains newline (isNewLineForbidden=true).")
            if len(text) > QUIZ_OPTION_MAX_CHARS:
                errors.append(
                    f"{label} Option {opt_letter}: length {len(text)} exceeds QUIZ_OPTION_TEXT_TOO_LONG ({QUIZ_OPTION_MAX_CHARS} max)."
                )
            elif not (QUIZ_OPTION_TARGET_MIN_CHARS <= len(text) <= QUIZ_OPTION_TARGET_MAX_CHARS):
                warnings.append(
                    f"{label} Option {opt_letter}: length is {len(text)} chars (target sweet spot is {QUIZ_OPTION_TARGET_MIN_CHARS}..{QUIZ_OPTION_TARGET_MAX_CHARS} chars)."
                )

        if lengths:
            spread = max(lengths) - min(lengths)
            if spread > QUIZ_OPTION_MAX_SPREAD_CHARS:
                warnings.append(
                    f"{label}: option length spread is {spread} chars (min {min(lengths)}, max {max(lengths)}); keep options within ~1..{QUIZ_OPTION_MAX_SPREAD_CHARS} chars so decoys match the correct answer."
                )
            correct_len = lengths[correct_idx]
            decoy_lengths = [l for i, l in enumerate(lengths) if i != correct_idx]
            if decoy_lengths and correct_len > max(decoy_lengths) + 8:
                warnings.append(
                    f"{label}: correct option ({correct_len} chars) is conspicuously longer than the longest decoy ({max(decoy_lengths)} chars)."
                )

        compiled.append(
            {
                "quiz_number": idx + 1,
                "timestamp": timestamp,
                "timestamp_seconds": ts_seconds,
                "question": question,
                "question_length": len(question),
                "correct_index": correct_idx,
                "options": [
                    {
                        "label": chr(ord("A") + i),
                        "text": t,
                        "length": len(t),
                        "is_correct": i == correct_idx,
                    }
                    for i, t in enumerate(option_texts)
                ],
                "explanation": explanation,
                "explanation_length": len(explanation),
                "studio_execution_steps": [
                    "1. Click '+ Add quiz' (row spawns at 00:00:00).",
                    f"2. Fill question stem ({len(question)} chars) while row is still at 00:00:00.",
                    f"3. Ensure {len(option_texts)} option rows exist, fill options A..{chr(ord('A') + len(option_texts) - 1)}, and mark Option {chr(ord('A') + correct_idx)} correct.",
                    "4. Fill explanation field if non-empty.",
                    f"5. Set timestamp '{timestamp}' LAST so chronological row re-sorting never interrupts field entry.",
                ],
            }
        )

    return {
        "valid": len(errors) == 0,
        "quiz_count": len(compiled),
        "max_quizzes_allowed": MAX_QUIZZES_PER_VIDEO,
        "errors": errors,
        "warnings": warnings,
        "quizzes": compiled,
    }


def probe_public_https_url(url: str, *, timeout: float = 10.0) -> dict[str, Any]:
    """Probe a single public HTTPS URL with pinned-IP SSRF protection and redirects disabled."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        return {"url": url, "ok": False, "status": None, "note": f"Non-HTTPS scheme ({parsed.scheme})"}
    if parsed.username or parsed.password:
        return {"url": url, "ok": False, "status": None, "note": "URLs with embedded credentials are refused"}
    try:
        port = parsed.port
    except ValueError:
        return {"url": url, "ok": False, "status": None, "note": "Invalid URL port"}
    if port not in (None, 443):
        return {"url": url, "ok": False, "status": None, "note": f"Non-443 HTTPS port ({port}) is refused"}

    host = parsed.hostname or ""
    try:
        norm_host, resolved_ips = resolve_public_https_ips(host, port=443)
    except Exception as exc:
        return {"url": url, "ok": False, "status": None, "note": scrub_secrets(str(exc))}

    req_path = parsed.path or "/"
    if parsed.query:
        req_path = f"{req_path}?{parsed.query}"
    host_header = f"[{norm_host}]" if ":" in norm_host else norm_host
    ctx = ssl.create_default_context()
    conn: http.client.HTTPConnection | None = None
    raw_sock: socket.socket | None = None
    tls_sock: ssl.SSLSocket | None = None
    try:
        raw_sock = socket.create_connection((resolved_ips[0], 443), timeout=timeout)
        tls_sock = ctx.wrap_socket(raw_sock, server_hostname=norm_host)
        conn = http.client.HTTPConnection(norm_host, 443, timeout=timeout)
        conn.sock = tls_sock
        conn.request(
            "HEAD",
            req_path,
            headers={
                "Host": host_header,
                "User-Agent": "legends-youtube-link-auditor/0.1.1",
                "Connection": "close",
            },
        )
        resp = conn.getresponse()
        code = int(resp.status)
        if 300 <= code < 400:
            return {"url": url, "ok": False, "status": code, "note": "Redirect"}
        return {
            "url": url,
            "ok": 200 <= code < 300,
            "status": code,
            "note": "OK" if 200 <= code < 300 else f"HTTP {code}",
        }
    except urllib.error.HTTPError as exc:
        note = "Redirect" if 300 <= exc.code < 400 else f"HTTP {exc.code}"
        return {"url": url, "ok": False, "status": exc.code, "note": note}
    except Exception as exc:
        return {"url": url, "ok": False, "status": None, "note": scrub_secrets(str(exc))}
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        elif tls_sock is not None:
            try:
                tls_sock.close()
            except Exception:
                pass
        elif raw_sock is not None:
            try:
                raw_sock.close()
            except Exception:
                pass


def audit_description_links(
    videos: list[dict[str, Any]],
    *,
    canonical_cta: str = "",
    legacy_domains: list[str] | None = None,
    probe_https: bool = False,
) -> dict[str, Any]:
    """Audit description links across a list of normalized video records."""
    if not isinstance(videos, list):
        raise ValueError("Videos payload must be a JSON list.")
    legacy_set = {d.strip().lower() for d in (legacy_domains or []) if d.strip()}
    url_to_videos: dict[str, list[str]] = {}
    domain_counts: dict[str, int] = {}
    insecure_http_videos: list[dict[str, str]] = []
    legacy_domain_hits: list[dict[str, str]] = []
    missing_cta_regular_videos: list[dict[str, str]] = []

    for rec in videos:
        if not isinstance(rec, dict):
            raise ValueError("Each video entry must be a JSON object.")
        vid = str(rec.get("video_id") or "")
        title = str(rec.get("title") or "")
        fmt = str(rec.get("format") or "long")
        desc = str(rec.get("description") or "")
        urls = [u.strip() for u in rec["urls"] if isinstance(u, str) and u.strip()] if isinstance(rec.get("urls"), list) else extract_urls(desc)

        if canonical_cta and fmt == "long" and canonical_cta not in desc:
            missing_cta_regular_videos.append({"video_id": vid, "title": title})

        for u in urls:
            url_to_videos.setdefault(u, []).append(vid)
            parsed = urllib.parse.urlparse(u)
            host = (parsed.hostname or "").lower()
            if host:
                domain_counts[host] = domain_counts.get(host, 0) + 1
            if parsed.scheme == "http":
                insecure_http_videos.append({"video_id": vid, "url": u})
            if host and any(host == leg or host.endswith(f".{leg}") for leg in legacy_set):
                legacy_domain_hits.append({"video_id": vid, "url": u, "domain": host})

    probes: list[dict[str, Any]] = []
    if probe_https:
        for unique_url in sorted(url_to_videos.keys())[:50]:
            res = probe_public_https_url(unique_url)
            res["video_count"] = len(url_to_videos[unique_url])
            probes.append(res)

    return {
        "videos_scanned": len(videos),
        "unique_url_count": len(url_to_videos),
        "domain_counts": dict(sorted(domain_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        "canonical_cta": canonical_cta or None,
        "missing_cta_regular_count": len(missing_cta_regular_videos),
        "missing_cta_regular_videos": missing_cta_regular_videos,
        "insecure_http_count": len(insecure_http_videos),
        "insecure_http_hits": insecure_http_videos,
        "legacy_domain_hit_count": len(legacy_domain_hits),
        "legacy_domain_hits": legacy_domain_hits,
        "probes": probes,
    }


HASHTAG_RE = re.compile(r"(?<!\w)#\w+")
STANDALONE_I_RE = re.compile(r"\bi\b")
SACRED_GOD_RE = re.compile(r"\bgod(?P<suffix>'s|’s)?\b", re.IGNORECASE)

FORBIDDEN_RELATED_OPS = frozenset(
    {
        "update_snippet",
        "update_status",
        "videos.update",
        "videos.insert",
        "set_privacy",
        "set_visibility",
        "publish",
        "unpublish",
        "schedule",
        "set_publish_at",
        "set_title",
        "set_description",
        "set_tags",
        "set_thumbnail",
        "delete",
    }
)


def transform_legends_lowercase_title(title: str) -> str:
    """Apply Legends lowercase title law: all lowercase except standalone pronoun `I` and standalone `God` (`God's`)."""
    lowered = (title or "").lower()
    with_i = STANDALONE_I_RE.sub("I", lowered)
    return SACRED_GOD_RE.sub(lambda m: "God" + (m.group("suffix") or ""), with_i)


def lint_house_style(title: str, description: str = "", *, cta_block: str = "") -> dict[str, Any]:
    """Check title and description against house lowercase, hashtag-free, and CTA block rules."""
    expected_title = transform_legends_lowercase_title(title)
    title_is_compliant = bool(title) and (title == expected_title)
    title_has_hashtags = bool(HASHTAG_RE.search(title or ""))
    desc_has_hashtags = bool(HASHTAG_RE.search(description or ""))
    norm_desc = (description or "").replace("\r\n", "\n").replace("\r", "\n")
    norm_cta = (cta_block or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    has_cta = bool(norm_cta and norm_cta in norm_desc) if norm_cta else True
    return {
        "valid": title_is_compliant and (not title_has_hashtags) and (not desc_has_hashtags) and has_cta,
        "title": title,
        "expected_lowercase_title": expected_title,
        "title_matches_lowercase_law": title_is_compliant,
        "title_has_hashtags": title_has_hashtags,
        "description_has_hashtags": desc_has_hashtags,
        "description_has_expected_cta": has_cta,
    }


def validate_related_video_guard(
    video_ids: list[str],
    target_video_id: str,
    *,
    confirm: bool = False,
    phrase: str | None = None,
    max_batch: int = 20,
) -> dict[str, Any]:
    """Validate a Shorts-to-Longform Related Video operation against fail-closed isolation guards."""
    target = validate_video_id(target_video_id)
    deduped: list[str] = []
    seen: set[str] = set()
    errors: list[str] = []

    for raw in video_ids:
        vid = validate_video_id(raw)
        if vid == target:
            errors.append(f"Self-link forbidden: Short {vid} cannot link to itself ({target}) as Related video.")
        if vid not in seen:
            seen.add(vid)
            deduped.append(vid)

    if not deduped:
        errors.append("Allowlist is empty; provide at least one 11-character Short videoId.")
    if len(deduped) > max_batch:
        errors.append(f"Allowlist size ({len(deduped)}) exceeds hard batch cap of {max_batch}.")

    if len(deduped) == 1:
        expected_phrase = f"SET_RELATED {deduped[0]} -> {target}"
    else:
        expected_phrase = f"LINK_RELATED_BATCH {len(deduped)} -> {target}"

    phrase_matched = False
    if confirm:
        got = (phrase or "").strip()
        if got != expected_phrase:
            errors.append(
                f"Confirmation phrase mismatch: expected {expected_phrase!r}, got {got!r}."
            )
        else:
            phrase_matched = True

    return {
        "valid": len(errors) == 0,
        "mode": "live_confirmed" if (confirm and phrase_matched and not errors) else "dry_run_preview",
        "target_video_id": target,
        "short_video_ids": deduped,
        "short_count": len(deduped),
        "max_batch_cap": max_batch,
        "expected_confirmation_phrase": expected_phrase,
        "confirmation_verified": phrase_matched,
        "forbidden_mutations_blocked": sorted(FORBIDDEN_RELATED_OPS),
        "errors": errors,
    }

