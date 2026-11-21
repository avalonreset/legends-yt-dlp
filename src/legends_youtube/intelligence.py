"""Offensive YouTube intelligence: transcript-to-chapter/Shorts extractor, outlier scout, and retention-to-transcript X-ray."""
from __future__ import annotations

import datetime as dt
import math
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .api import (
    YouTubeError,
    build_safe_opener,
    safe_read_json_file,
    safe_read_text_file,
    scrub_secrets,
    validate_channel_id,
    validate_video_id,
)
from .inventory import SHORTS_MAX_SECONDS, public_video_readback
from .studio_lint import lint_chapters, transform_legends_lowercase_title

MAX_FEED_BYTES = 2 * 1024 * 1024
_XML_DTD_RE = re.compile(rb"<!\s*(?:DOCTYPE|ENTITY)\b", re.IGNORECASE)

SRT_TIME_RE = re.compile(
    r"(?:(?P<sh>\d{1,2}):)?(?P<sm>\d{2}):(?P<ss>\d{2})[,.](?P<sms>\d{1,3})\s*-->\s*"
    r"(?:(?P<eh>\d{1,2}):)?(?P<em>\d{2}):(?P<es>\d{2})[,.](?P<ems>\d{1,3})"
)
TXT_BRACKET_RE = re.compile(
    r"^\s*\[\s*(?P<start>\d+(?:\.\d+)?)\s*-\s*(?P<end>\d+(?:\.\d+)?)\s*\]\s*(?P<text>.+?)\s*$"
)
STOPWORDS = frozenset(
    {
        "the", "and", "that", "this", "with", "from", "your", "have", "what", "when", "where",
        "which", "there", "their", "about", "would", "could", "should", "because", "really",
        "actually", "basically", "literally", "going", "want", "wanted", "talk", "moment",
        "little", "thing", "things", "people", "right", "know", "like", "just", "kind", "very",
        "some", "into", "them", "they", "were", "been", "being", "than", "then", "also", "only",
        "over", "more", "most", "other", "such", "even", "much", "many", "well", "back", "down",
        "make", "made", "does", "didn", "don", "isn", "aren", "wasn", "weren", "won", "can",
        "will", "let", "lets", "here", "look", "looking", "think", "thought", "something",
    }
)
TRANSITION_CUES = (
    "first",
    "second",
    "third",
    "next",
    "finally",
    "now let",
    "let's talk",
    "so how",
    "how to",
    "the problem",
    "the secret",
    "the reason",
    "why ",
    "what happens",
    "if you had to",
    "i would love to",
    "for example",
    "on the other hand",
    "the bottom line",
)
HOOK_CLAIM_CUES = (
    "the secret",
    "nobody",
    "stop ",
    "never ",
    "if you had to",
    "here is why",
    "the truth",
    "most people",
    "forget about",
    "boil it all down",
    "instantly know",
    "fresh eyes",
    "single image",
    "the biggest mistake",
    "actually works",
)
FILLER_WORDS_RE = re.compile(r"\b(um|uh|erm|like,\s+you\s+know|you\s+know\s+what\s+i\s+mean)\b", re.IGNORECASE)


def format_mmss(seconds: float) -> str:
    """Format seconds as MM:SS or HH:MM:SS for YouTube chapters."""
    total = max(0, int(math.floor(seconds)))
    hh = total // 3600
    mm = (total % 3600) // 60
    ss = total % 60
    if hh > 0:
        return f"{hh:02d}:{mm:02d}:{ss:02d}"
    return f"{mm:02d}:{ss:02d}"


def _hms_to_seconds(h: str | None, m: str, s: str, ms: str) -> float:
    ms_norm = int(ms.ljust(3, "0")[:3])
    return int(h or 0) * 3600 + int(m) * 60 + int(s) + (ms_norm / 1000.0)


def _finite_float(val: Any, label: str = "value", *, default: float = 0.0) -> float:
    if val is None or val == "":
        return float(default)
    if isinstance(val, bool):
        raise YouTubeError(f"Invalid finite number for {label}: {val!r}")
    try:
        f = float(val)
    except (TypeError, ValueError):
        raise YouTubeError(f"Invalid finite number for {label}: {val!r}") from None
    if not math.isfinite(f):
        raise YouTubeError(f"Non-finite number (NaN/Infinity) is not allowed for {label}: {val!r}")
    return f


def load_transcript_segments(path: str | Path) -> dict[str, Any]:
    """Load timestamped transcript segments from JSON (.json), SubRip (.srt), WebVTT (.vtt), or bracketed (.txt)."""
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".json":
        _, data, _ = safe_read_json_file(p, max_bytes=15 * 1024 * 1024, label="transcript JSON")
        raw_segs = data.get("segments") if isinstance(data, dict) else data
        if not isinstance(raw_segs, list):
            raise YouTubeError("Transcript JSON must contain a 'segments' list or be a list of segment objects.")
        segments: list[dict[str, Any]] = []
        for idx, item in enumerate(raw_segs):
            if not isinstance(item, dict):
                continue
            start = _finite_float(item.get("start"), f"segment[{idx}].start", default=0.0)
            end = _finite_float(item.get("end"), f"segment[{idx}].end", default=start)
            text = str(item.get("text") or "").strip()
            if text:
                segments.append({"index": idx, "start": round(start, 2), "end": round(end, 2), "text": text})
        default_dur = segments[-1]["end"] if segments else 0.0
        duration = (
            _finite_float(data.get("duration"), "duration", default=default_dur)
            if isinstance(data, dict)
            else default_dur
        )
        return {"format": "json", "duration_seconds": round(duration, 2), "segments": segments}

    _, raw_text = safe_read_text_file(p, max_bytes=15 * 1024 * 1024, label="transcript file")
    lines = raw_text.splitlines()

    # Check if bracketed [  0.00 -   6.32] format
    bracket_segs: list[dict[str, Any]] = []
    for line in lines:
        m = TXT_BRACKET_RE.match(line)
        if m:
            start = _finite_float(m.group("start"), "start")
            end = _finite_float(m.group("end"), "end")
            txt = m.group("text").strip()
            if txt:
                bracket_segs.append({"index": len(bracket_segs), "start": round(start, 2), "end": round(end, 2), "text": txt})
    if bracket_segs:
        return {
            "format": "bracketed_txt",
            "duration_seconds": round(bracket_segs[-1]["end"], 2),
            "segments": bracket_segs,
        }

    # Parse SRT / VTT blocks
    srt_segs: list[dict[str, Any]] = []
    cur_start: float | None = None
    cur_end: float | None = None
    cur_lines: list[str] = []
    in_skip_block = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if cur_start is not None and cur_lines:
                joined = " ".join(cur_lines).strip()
                if joined:
                    srt_segs.append(
                        {"index": len(srt_segs), "start": round(cur_start, 2), "end": round(cur_end or cur_start, 2), "text": joined}
                    )
            cur_start = None
            cur_end = None
            cur_lines = []
            in_skip_block = False
            continue
        if in_skip_block:
            continue
        if cur_start is None and stripped.startswith(("NOTE", "STYLE", "REGION")):
            in_skip_block = True
            continue
        m = SRT_TIME_RE.search(stripped)
        if m:
            if cur_start is not None and cur_lines:
                joined = " ".join(cur_lines).strip()
                if joined:
                    srt_segs.append(
                        {"index": len(srt_segs), "start": round(cur_start, 2), "end": round(cur_end or cur_start, 2), "text": joined}
                    )
            cur_start = _hms_to_seconds(m.group("sh"), m.group("sm"), m.group("ss"), m.group("sms"))
            cur_end = _hms_to_seconds(m.group("eh"), m.group("em"), m.group("es"), m.group("ems"))
            cur_lines = []
        elif cur_start is not None and not stripped.isdigit() and not stripped.startswith(("WEBVTT", "Kind:", "Language:")):
            clean_tag = re.sub(r"<[^>]+>", "", stripped).strip()
            if clean_tag:
                cur_lines.append(clean_tag)
    if cur_start is not None and cur_lines:
        joined = " ".join(cur_lines).strip()
        if joined:
            srt_segs.append(
                {"index": len(srt_segs), "start": round(cur_start, 2), "end": round(cur_end or cur_start, 2), "text": joined}
            )
    if not srt_segs:
        raise YouTubeError(f"Could not parse timestamped segments from {p.name}.")
    return {
        "format": "srt_vtt",
        "duration_seconds": round(srt_segs[-1]["end"], 2),
        "segments": srt_segs,
    }


TOPIC_EXTRACTOR_RES = (
    re.compile(r"\b(?:talk(?:\s+for\s+a\s+moment)?\s+about|talking\s+about|deep\s+dive\s+on)\s+([A-Za-z0-9\s'-]{8,55})", re.IGNORECASE),
    re.compile(r"\b(how\s+to\s+[A-Za-z0-9\s'-]{8,50})", re.IGNORECASE),
    re.compile(r"\b(?:the\s+(?:first|second|third|next)\s+one\s+is)\s+([A-Za-z0-9\s'-]{5,45})", re.IGNORECASE),
    re.compile(r"\b(what\s+(?:is\s+)?currently\s+working[A-Za-z0-9\s'-]{0,35})", re.IGNORECASE),
)
LEADING_FILLER_RE = re.compile(
    r"^(?:and\s+yeah|yeah|right|okay|well|so|and\s+so|but|first\s+of\s+all|you\s+know|i\s+mean|"
    r"i\s+wanted\s+to\s+talk(?:\s+for\s+a\s+moment)?\s+about|let's\s+talk\s+about|it's\s+like)[,\s]+",
    re.IGNORECASE,
)
TRAILING_WEAK_WORDS = frozenset(
    {
        "and", "but", "or", "so", "because", "which", "that", "who", "when", "where", "while",
        "if", "than", "with", "from", "into", "about", "for", "to", "of", "in", "on", "at",
        "by", "as", "is", "are", "was", "were", "be", "been", "it's", "its", "his", "her",
        "their", "our", "your", "my", "this", "these", "those", "too", "very", "really", "not",
    }
)


def _title_case_clean(phrase: str) -> str:
    small = {"a", "an", "the", "and", "but", "or", "for", "nor", "on", "at", "to", "from", "by", "of", "in", "with"}
    words = phrase.split()
    out: list[str] = []
    for i, w in enumerate(words):
        low = w.lower()
        if i > 0 and i < len(words) - 1 and low in small:
            out.append(low)
        else:
            out.append(w[:1].upper() + w[1:])
    return " ".join(out)


def _summarize_window_heading(text_window: str, *, is_intro: bool = False) -> str:
    """Extract a grammatical, human-readable 3-to-7 word chapter heading from a transcript window."""
    normalized = " ".join((text_window or "").split())
    for pat in TOPIC_EXTRACTOR_RES:
        m = pat.search(normalized)
        if m:
            candidate = m.group(1).strip(" ,.;:!?-")
            cand_words = candidate.split()[:7]
            while len(cand_words) > 3 and cand_words[-1].lower().strip(".,?!") in TRAILING_WEAK_WORDS:
                cand_words.pop()
            if len(cand_words) >= 3:
                return _title_case_clean(" ".join(cand_words))[:58]

    clauses = [c.strip() for c in re.split(r"[.?!;]+|\s+-\s+|,\s+(?:and|but|so|because|which|like)\s+", normalized) if c.strip()]
    for clause in clauses:
        cleaned = LEADING_FILLER_RE.sub("", clause).strip()
        cleaned = LEADING_FILLER_RE.sub("", cleaned).strip(" ,.:;-")
        words = cleaned.split()
        if len(words) < 3:
            continue
        sliced = words[:7]
        while len(sliced) > 3 and sliced[-1].lower().strip(".,?!") in TRAILING_WEAK_WORDS:
            sliced.pop()
        if len(sliced) >= 3:
            return _title_case_clean(" ".join(sliced))[:58]

    return "Intro and Overview" if is_intro else "Key Breakdown"


def compile_transcript_package(
    transcript_path: str | Path,
    *,
    video_title: str = "Untitled Video",
    target_chapters: int = 6,
    min_chapter_seconds: int = 45,
    silence_threshold_seconds: float = 1.25,
    canonical_cta: str = "",
) -> dict[str, Any]:
    """Generate validated YouTube chapters, Shorts gem-cut candidates, dead-air cut list, and a Release Workbench from a transcript."""
    silence_threshold_seconds = _finite_float(silence_threshold_seconds, "silence_threshold_seconds", default=1.25)
    loaded = load_transcript_segments(transcript_path)
    segments = loaded["segments"]
    duration = float(loaded["duration_seconds"])
    if not segments:
        raise YouTubeError("Transcript contains zero segments.")

    # 1. Pacing & Dead-Air Audit
    total_words = sum(len(s["text"].split()) for s in segments)
    wpm = round((total_words / duration) * 60.0, 1) if duration > 0 else 0.0
    first_30_words = sum(len(s["text"].split()) for s in segments if s["start"] < 30.0)
    hook_30_window = min(30.0, duration)
    hook_wpm = round((first_30_words / hook_30_window) * 60.0, 1) if hook_30_window > 0 else 0.0

    dead_air_gaps: list[dict[str, Any]] = []
    filler_hits = 0
    for i, seg in enumerate(segments):
        filler_hits += len(FILLER_WORDS_RE.findall(seg["text"]))
        if i > 0:
            prev_end = segments[i - 1]["end"]
            gap = round(seg["start"] - prev_end, 2)
            if gap >= silence_threshold_seconds:
                dead_air_gaps.append(
                    {
                        "start_seconds": prev_end,
                        "end_seconds": seg["start"],
                        "timestamp": format_mmss(prev_end),
                        "gap_seconds": gap,
                        "after_text": segments[i - 1]["text"][-60:],
                        "before_text": seg["text"][:60],
                    }
                )

    # 2. Topic-Shift Chapter Boundary Detection
    effective_min_sec = max(15, min(min_chapter_seconds, int(duration // max(3, target_chapters))))
    scored_candidates: list[tuple[float, int]] = []
    for idx in range(1, len(segments)):
        seg = segments[idx]
        sec = seg["start"]
        if sec < effective_min_sec or (duration - sec) < 15:
            continue
        prev_end = segments[idx - 1]["end"]
        pause = max(0.0, sec - prev_end)
        low_txt = seg["text"].lower()
        cue_bonus = 3.0 if any(cue in low_txt for cue in TRANSITION_CUES) else 0.0
        sentence_start_bonus = 1.5 if segments[idx - 1]["text"].rstrip().endswith((".", "?", "!")) else 0.0
        score = pause * 2.5 + cue_bonus + sentence_start_bonus
        scored_candidates.append((score, idx))

    scored_candidates.sort(key=lambda item: (-item[0], segments[item[1]]["start"]))
    chosen_indices: list[int] = [0]
    chosen_times: list[float] = [0.0]

    for _, cand_idx in scored_candidates:
        if len(chosen_indices) >= max(3, target_chapters):
            break
        cand_sec = segments[cand_idx]["start"]
        if all(abs(cand_sec - t) >= effective_min_sec for t in chosen_times):
            chosen_indices.append(cand_idx)
            chosen_times.append(cand_sec)

    # Fallback evenly spaced chapters if transcript had no strong pauses
    if len(chosen_indices) < 3 and duration >= 35:
        step = duration / 3.0
        for mult in (1, 2):
            target_t = step * mult
            closest_idx = min(range(len(segments)), key=lambda i: abs(segments[i]["start"] - target_t))
            t_val = segments[closest_idx]["start"]
            if all(abs(t_val - existing) >= 10.0 for existing in chosen_times):
                chosen_indices.append(closest_idx)
                chosen_times.append(t_val)

    chosen_indices = sorted(set(chosen_indices), key=lambda i: segments[i]["start"])
    chapters_out: list[dict[str, Any]] = []
    for pos, seg_idx in enumerate(chosen_indices):
        start_sec = 0 if pos == 0 else int(math.floor(segments[seg_idx]["start"]))
        window_text = " ".join(s["text"] for s in segments[seg_idx : min(len(segments), seg_idx + 5)])
        heading = _summarize_window_heading(window_text, is_intro=(pos == 0))
        chapters_out.append(
            {
                "timestamp": format_mmss(start_sec),
                "seconds": start_sec,
                "title": heading,
                "opening_quote": segments[seg_idx]["text"],
            }
        )

    chapter_block = "\n".join(f"{c['timestamp']} {c['title']}" for c in chapters_out)
    chapter_lint = lint_chapters(chapter_block, video_duration_seconds=int(duration) if duration > 0 else None)

    # 3. Shorts Clip & Gem-Cut Extractor (22s to 56s self-contained windows)
    shorts_candidates: list[dict[str, Any]] = []
    for i, start_seg in enumerate(segments):
        if start_seg["start"] > duration - 22:
            break
        # Prefer starting on a fresh sentence with substantive length (>= 6 words)
        if i > 0 and not segments[i - 1]["text"].rstrip().endswith((".", "?", "!")):
            continue
        first_seg_words = start_seg["text"].split()
        if len(first_seg_words) < 6 or start_seg["text"].lower().startswith(("yeah", "right", "you know, the", "and yeah")):
            continue
        window_segs: list[dict[str, Any]] = []
        for j in range(i, len(segments)):
            window_segs.append(segments[j])
            span = segments[j]["end"] - start_seg["start"]
            if 24.0 <= span <= 55.0 and segments[j]["text"].rstrip().endswith((".", "?", "!")):
                break
            if span > 56.0:
                break
        if not window_segs:
            continue
        clip_duration = round(window_segs[-1]["end"] - start_seg["start"], 2)
        if not (22.0 <= clip_duration <= 58.0):
            continue
        full_quote = " ".join(s["text"] for s in window_segs)
        low_quote = full_quote.lower()
        hook_hits = sum(1 for cue in HOOK_CLAIM_CUES if cue in low_quote)
        word_count = len(full_quote.split())
        clip_wpm = (word_count / clip_duration) * 60.0 if clip_duration > 0 else 0.0
        punch_score = round(hook_hits * 3.5 + min(3.0, clip_wpm / 60.0), 2)

        # Gem-cut first sentence in continuous lowercase per Design Bible §4c
        first_sentence = re.split(r"(?<=[.!?])\s+", full_quote)[0].strip()
        gem_cut = transform_legends_lowercase_title(first_sentence.rstrip("."))
        short_title = transform_legends_lowercase_title(_summarize_window_heading(full_quote))
        clean_cta = (canonical_cta or "").strip()
        shorts_candidates.append(
            {
                "start_timestamp": format_mmss(start_seg["start"]),
                "end_timestamp": format_mmss(window_segs[-1]["end"]),
                "start_seconds": start_seg["start"],
                "end_seconds": window_segs[-1]["end"],
                "duration_seconds": clip_duration,
                "score": punch_score,
                "suggested_short_title": short_title,
                "gem_cut_description_lead": gem_cut,
                "design_bible_4c_description": f"{gem_cut}\n.\n{clean_cta}" if clean_cta else gem_cut,
                "transcript_excerpt": full_quote[:260] + ("..." if len(full_quote) > 260 else ""),
            }
        )

    shorts_candidates.sort(key=lambda c: (-c["score"], c["start_seconds"]))
    deduped_shorts: list[dict[str, Any]] = []
    for cand in shorts_candidates:
        if all(abs(cand["start_seconds"] - existing["start_seconds"]) >= 30.0 for existing in deduped_shorts):
            deduped_shorts.append(cand)
        if len(deduped_shorts) >= 5:
            break

    workbench_lines = [
        f"# YouTube Release Workbench: {video_title}",
        "",
        f"- **Duration:** `{format_mmss(duration)}` (`{round(duration, 1)}s`)",
        f"- **Speaking Pace:** `{wpm} WPM` (First 30s Hook: `{hook_wpm} WPM`)",
        f"- **Chapters Generated:** `{len(chapters_out)}` (`chapters-lint` valid: `{chapter_lint['valid']}`)",
        f"- **Dead-Air Gaps (>= {silence_threshold_seconds}s):** `{len(dead_air_gaps)}`",
        "",
        "## Copy-Paste Description Chapters",
        "",
        "```text",
        chapter_block,
        "```",
        "",
        "## Top Shorts Clip Candidates & Design Bible 4c Gem-Cuts",
        "",
    ]
    for idx, sh in enumerate(deduped_shorts, 1):
        workbench_lines.extend(
            [
                f"### Short #{idx}: `{sh['start_timestamp']} - {sh['end_timestamp']}` ({sh['duration_seconds']}s · score {sh['score']})",
                f"- **Lowercase Title:** `{sh['suggested_short_title']}`",
                f"- **Gem-Cut Lead:** `{sh['gem_cut_description_lead']}`",
                f"- **Excerpt:** \"{sh['transcript_excerpt']}\"",
                "",
            ]
        )

    return {
        "video_title": video_title,
        "transcript_format": loaded["format"],
        "duration_seconds": duration,
        "duration_formatted": format_mmss(duration),
        "pacing_audit": {
            "total_words": total_words,
            "words_per_minute": wpm,
            "first_30s_wpm": hook_wpm,
            "filler_word_count": filler_hits,
            "dead_air_gap_count": len(dead_air_gaps),
            "dead_air_gaps": dead_air_gaps[:15],
        },
        "chapters": {
            "valid": chapter_lint["valid"],
            "chapter_count": len(chapters_out),
            "copy_paste_block": chapter_block,
            "items": chapters_out,
        },
        "shorts_candidates": deduped_shorts,
        "workbench_markdown": "\n".join(workbench_lines),
    }


def _safe_nonneg_int(value: Any) -> int:
    try:
        return max(0, int(str(value or "0").strip()))
    except (TypeError, ValueError):
        return 0


def _safe_parse_xml_bytes(xml_bytes: bytes) -> ET.Element:
    """Safely parse bounded XML bytes after rejecting DTD/ENTITY declarations and null/UTF-16 smuggling (CWE-611 / CWE-776)."""
    if not xml_bytes:
        raise YouTubeError("Empty XML response from YouTube feed.")
    if len(xml_bytes) > MAX_FEED_BYTES:
        raise YouTubeError(f"XML feed response exceeded {MAX_FEED_BYTES} bytes.")
    if xml_bytes.startswith((b"\xff\xfe", b"\xfe\xff")) or b"\x00" in xml_bytes:
        raise YouTubeError("Refusing UTF-16 or null-byte XML payload.")
    if _XML_DTD_RE.search(xml_bytes):
        raise YouTubeError("Refusing XML payload containing DOCTYPE or ENTITY declarations (CWE-611 / CWE-776).")
    try:
        return ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise YouTubeError(f"Malformed XML feed response: {exc}") from None


def fetch_public_channel_feed(channel_id: str, *, enrich_top_n: int = 5, timeout: float = 20.0) -> list[dict[str, Any]]:
    """Fetch the 15 most recent uploads from any public YouTube channel via its Atom/RSS feed for 0 API quota units."""
    cid = validate_channel_id(channel_id)
    opener = build_safe_opener()
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={urllib.parse.quote(cid)}"
    req = urllib.request.Request(
        feed_url,
        headers={"User-Agent": "legends-youtube-outlier-scout/0.1.1"},
    )
    try:
        with opener.open(req, timeout=timeout) as resp:
            xml_bytes = resp.read(MAX_FEED_BYTES + 1)
            if len(xml_bytes) > MAX_FEED_BYTES:
                raise YouTubeError(f"Public channel feed for {cid} exceeded {MAX_FEED_BYTES} bytes.")
    except YouTubeError:
        raise
    except Exception as exc:
        raise YouTubeError(f"Failed to fetch public channel feed for {cid}: {scrub_secrets(str(exc))}") from None

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "media": "http://search.yahoo.com/mrss/",
    }
    root = _safe_parse_xml_bytes(xml_bytes)
    channel_title_el = root.find("atom:title", ns)
    channel_title = channel_title_el.text if channel_title_el is not None and channel_title_el.text else cid

    videos: list[dict[str, Any]] = []
    for entry in root.findall("atom:entry", ns):
        vid_el = entry.find("yt:videoId", ns)
        title_el = entry.find("atom:title", ns)
        pub_el = entry.find("atom:published", ns)
        media_group = entry.find("media:group", ns)
        desc_el = media_group.find("media:description", ns) if media_group is not None else None
        comm_el = media_group.find("media:community", ns) if media_group is not None else None
        stats_el = comm_el.find("media:statistics", ns) if comm_el is not None else None
        rating_el = comm_el.find("media:starRating", ns) if comm_el is not None else None

        raw_vid = (vid_el.text or "").strip() if vid_el is not None else ""
        if not raw_vid:
            continue
        try:
            vid = validate_video_id(raw_vid)
        except YouTubeError:
            continue
        views = _safe_nonneg_int(stats_el.attrib.get("views", "0")) if stats_el is not None else 0
        likes = _safe_nonneg_int(rating_el.attrib.get("count", "0")) if rating_el is not None else 0
        videos.append(
            {
                "video_id": vid,
                "channel_id": cid,
                "channel_title": channel_title,
                "title": (title_el.text or "").strip() if title_el is not None else "",
                "description": (desc_el.text or "").strip() if desc_el is not None else "",
                "published_at": (pub_el.text or "").strip() if pub_el is not None else "",
                "views": views,
                "likes": likes,
                "comments": 0,
                "format": "long",
                "length_seconds": 0,
                "privacy_status": "public",
            }
        )

    # Sort by views descending and optionally enrich top N with 0-quota watch-page readback for exact duration
    by_views = sorted(videos, key=lambda v: -v["views"])
    for item in by_views[: max(0, min(15, enrich_top_n))]:
        try:
            rb = public_video_readback(item["video_id"], timeout=timeout)
            item["length_seconds"] = rb["length_seconds"]
            item["format"] = "short" if rb["is_short_duration"] else "long"
        except Exception:
            pass
    return videos


def _parse_iso_date_days_ago(iso_str: str, now_utc: dt.datetime | None = None) -> float:
    if not iso_str:
        return 30.0
    ref = now_utc or dt.datetime.now(dt.timezone.utc)
    try:
        cleaned = iso_str.replace("Z", "+00:00")
        parsed = dt.datetime.fromisoformat(cleaned)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        delta_days = (ref - parsed).total_seconds() / 86400.0
        return max(1.0, round(delta_days, 2))
    except Exception:
        return 30.0


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 == 1 else (s[mid - 1] + s[mid]) / 2.0


def _analyze_title_structure(title: str) -> list[str]:
    patterns: list[str] = []
    t = (title or "").strip()
    low = t.lower()
    if re.search(r"\bi\b", low) and any(v in low for v in ("i built", "i tested", "i made", "i tried", "my ")):
        patterns.append("first_person_proof")
    if "?" in t or low.startswith(("how ", "why ", "what ", "can ", "is ")):
        patterns.append("question_or_curiosity_gap")
    if re.search(r"\b\d+\b", t):
        patterns.append("numeric_specificity")
    if t == transform_legends_lowercase_title(t):
        patterns.append("lowercase_aesthetic")
    if any(w in low for w in ("vs", "versus", "alternative", "compared")):
        patterns.append("comparison_frame")
    if not patterns:
        patterns.append("direct_declarative_claim")
    return patterns


def scout_channel_outliers(
    videos: list[dict[str, Any]],
    *,
    outlier_threshold_multiplier: float = 2.0,
) -> dict[str, Any]:
    """Identify breakout outlier videos (by total views and views/day velocity) and extract winning packaging patterns."""
    if not isinstance(videos, list):
        raise YouTubeError("Videos payload must be a JSON list.")
    outlier_threshold_multiplier = _finite_float(
        outlier_threshold_multiplier, "outlier_threshold_multiplier", default=2.0
    )
    for v in videos:
        if not isinstance(v, dict):
            raise YouTubeError("Each video entry must be a JSON object.")
    public_vids = [v for v in videos if str(v.get("privacy_status", "public")) == "public"]
    if not public_vids:
        return {
            "videos_analyzed": 0,
            "median_views": 0.0,
            "median_views_per_day": 0.0,
            "outlier_count": 0,
            "outliers": [],
            "top_performing_videos": [],
        }

    now_utc = dt.datetime.now(dt.timezone.utc)
    enriched: list[dict[str, Any]] = []
    for v in public_vids:
        raw_vid = str(v.get("video_id") or "")
        vid = validate_video_id(raw_vid)
        title = str(v.get("title") or "")
        views = _finite_float(v.get("views"), "views", default=0.0)
        if views < 0:
            raise YouTubeError(f"Video views cannot be negative: {views}")
        likes = _safe_nonneg_int(v.get("likes"))
        pub = str(v.get("published_at") or v.get("published") or "")
        days_live = _parse_iso_date_days_ago(pub, now_utc)
        views_per_day = round(views / days_live, 2)
        like_rate = round((likes / views) * 100.0, 2) if views > 0 else 0.0
        enriched.append(
            {
                "video_id": vid,
                "title": title,
                "format": str(v.get("format") or "long"),
                "length_seconds": _safe_nonneg_int(v.get("length_seconds")),
                "published_at": pub,
                "days_live": days_live,
                "views": int(views),
                "views_per_day": views_per_day,
                "likes": likes,
                "like_rate_pct": like_rate,
                "title_char_length": len(title),
                "title_patterns": _analyze_title_structure(title),
                "thumbnail_maxres_url": f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg",
                "watch_url": f"https://www.youtube.com/watch?v={vid}",
            }
        )

    med_views = max(1.0, _median([ float(e["views"]) for e in enriched ]))
    med_vpd = max(0.1, _median([ float(e["views_per_day"]) for e in enriched ]))

    for e in enriched:
        e["views_multiplier_vs_median"] = round(e["views"] / med_views, 2)
        e["velocity_multiplier_vs_median"] = round(e["views_per_day"] / med_vpd, 2)
        e["is_outlier"] = (
            e["views_multiplier_vs_median"] >= outlier_threshold_multiplier
            or e["velocity_multiplier_vs_median"] >= outlier_threshold_multiplier
        )

    enriched.sort(key=lambda e: (-e["views_multiplier_vs_median"], -e["velocity_multiplier_vs_median"]))
    outliers = [e for e in enriched if e["is_outlier"]]

    pattern_counts: dict[str, int] = {}
    for o in (outliers or enriched[:5]):
        for pat in o["title_patterns"]:
            pattern_counts[pat] = pattern_counts.get(pat, 0) + 1

    return {
        "videos_analyzed": len(enriched),
        "channel_id": str(public_vids[0].get("channel_id") or ""),
        "channel_title": str(public_vids[0].get("channel_title") or ""),
        "median_views": round(med_views, 1),
        "median_views_per_day": round(med_vpd, 2),
        "outlier_threshold_multiplier": outlier_threshold_multiplier,
        "outlier_count": len(outliers),
        "winning_title_patterns": dict(sorted(pattern_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        "outliers": outliers[:15],
        "top_performing_videos": enriched[:10],
    }


def correlate_retention_with_transcript(
    transcript_path: str | Path,
    retention_data: dict[str, Any] | list[Any],
    *,
    cliff_drop_threshold: float = -0.025,
) -> dict[str, Any]:
    """Correlate a YouTube retention curve (elapsedVideoTimeRatio -> audienceWatchRatio) with exact spoken sentences."""
    cliff_drop_threshold = _finite_float(cliff_drop_threshold, "cliff_drop_threshold", default=-0.025)
    loaded = load_transcript_segments(transcript_path)
    segments = loaded["segments"]
    duration = float(loaded["duration_seconds"])
    if duration <= 0 or not segments:
        raise YouTubeError("Transcript must have positive duration and non-empty segments.")

    # Normalize retention curve points: accept Analytics API v2 {rows: [[ratio, watchRatio, relPerf?], ...]}
    # or list of {"elapsed_ratio": 0.05, "watch_ratio": 0.72} or {"second": 30, "retention_pct": 68.5}
    raw_points: list[Any] = []
    if isinstance(retention_data, dict):
        if isinstance(retention_data.get("rows"), list):
            raw_points = retention_data["rows"]
        elif isinstance(retention_data.get("points"), list):
            raw_points = retention_data["points"]
        elif isinstance(retention_data.get("retention"), list):
            raw_points = retention_data["retention"]
    elif isinstance(retention_data, list):
        raw_points = retention_data
    if not raw_points:
        raise YouTubeError("Retention data must contain 'rows', 'points', or a list of retention points.")

    points: list[dict[str, float]] = []
    for idx, item in enumerate(raw_points):
        if isinstance(item, list) and len(item) >= 2:
            ratio = _finite_float(item[0], f"rows[{idx}][0]")
            watch = _finite_float(item[1], f"rows[{idx}][1]")
            rel = _finite_float(item[2], f"rows[{idx}][2]", default=0.5) if len(item) >= 3 and item[2] is not None else 0.5
            sec = ratio * duration if ratio <= 1.0 else ratio
            norm_ratio = ratio if ratio <= 1.0 else (ratio / duration)
            norm_watch = watch / 100.0 if watch > 1.5 else watch
            points.append({"ratio": round(norm_ratio, 4), "second": round(sec, 2), "watch_ratio": round(norm_watch, 4), "relative": round(rel, 4)})
        elif isinstance(item, dict):
            if "elapsed_ratio" in item or "elapsedVideoTimeRatio" in item:
                raw_r = item.get("elapsed_ratio") if "elapsed_ratio" in item and item.get("elapsed_ratio") is not None else item.get("elapsedVideoTimeRatio")
                ratio = _finite_float(raw_r, f"points[{idx}].elapsed_ratio", default=0.0)
                sec = ratio * duration
            else:
                raw_s = item.get("second") if "second" in item and item.get("second") is not None else item.get("seconds")
                sec = _finite_float(raw_s, f"points[{idx}].second", default=0.0)
                ratio = sec / duration if duration > 0 else 0.0
            raw_w = item.get("watch_ratio")
            if raw_w is None:
                raw_w = item.get("audienceWatchRatio")
            if raw_w is None:
                raw_w = item.get("retention_pct")
            watch_raw = _finite_float(raw_w, f"points[{idx}].watch_ratio", default=0.0)
            watch = watch_raw / 100.0 if watch_raw > 1.5 else watch_raw
            raw_rel = item.get("relative") if "relative" in item and item.get("relative") is not None else item.get("relativeRetentionPerformance")
            rel = _finite_float(raw_rel, f"points[{idx}].relative", default=0.5)
            points.append({"ratio": round(ratio, 4), "second": round(sec, 2), "watch_ratio": round(watch, 4), "relative": round(rel, 4)})

    points.sort(key=lambda p: p["second"])
    if len(points) < 2:
        raise YouTubeError("Retention curve requires at least 2 points.")

    def _spoken_at(sec_start: float, sec_end: float) -> str:
        window_start = max(0.0, sec_start - 3.0)
        window_end = min(duration, sec_end + 3.0)
        matched = [
            s["text"]
            for s in segments
            if s["end"] >= window_start and s["start"] <= window_end
        ]
        return " ".join(matched).strip() or "(silence / transition)"

    # 30-second hook survival
    hook_point = min(points, key=lambda p: abs(p["second"] - min(30.0, duration)))
    hook_retention_pct = round(hook_point["watch_ratio"] * 100.0, 2)

    cliffs: list[dict[str, Any]] = []
    rewatch_spikes: list[dict[str, Any]] = []
    for idx in range(1, len(points)):
        prev_p = points[idx - 1]
        cur_p = points[idx]
        delta = round(cur_p["watch_ratio"] - prev_p["watch_ratio"], 4)
        quote = _spoken_at(prev_p["second"], cur_p["second"])
        entry = {
            "timestamp_range": f"{format_mmss(prev_p['second'])} - {format_mmss(cur_p['second'])}",
            "start_seconds": prev_p["second"],
            "end_seconds": cur_p["second"],
            "retention_before_pct": round(prev_p["watch_ratio"] * 100.0, 2),
            "retention_after_pct": round(cur_p["watch_ratio"] * 100.0, 2),
            "delta_pct_points": round(delta * 100.0, 2),
            "spoken_lines": quote,
        }
        if delta <= cliff_drop_threshold:
            cliffs.append(entry)
        elif delta >= 0.005:
            rewatch_spikes.append(entry)

    cliffs.sort(key=lambda c: c["delta_pct_points"])
    rewatch_spikes.sort(key=lambda s: -s["delta_pct_points"])

    avg_watch_ratio = sum(p["watch_ratio"] for p in points) / len(points)
    return {
        "duration_seconds": duration,
        "duration_formatted": format_mmss(duration),
        "points_analyzed": len(points),
        "hook_30s_retention_pct": hook_retention_pct,
        "hook_30s_healthy": hook_retention_pct >= 55.0,
        "hook_opening_lines": _spoken_at(0.0, min(30.0, duration)),
        "average_percentage_viewed_pct": round(avg_watch_ratio * 100.0, 2),
        "dropoff_cliff_count": len(cliffs),
        "steepest_dropoff_cliffs": cliffs[:8],
        "rewatch_spike_count": len(rewatch_spikes),
        "rewatch_spikes": rewatch_spikes[:5],
    }
