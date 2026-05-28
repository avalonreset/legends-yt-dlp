from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Iterable

from .doctor import Check
from .ledger import load_item_ledger
from .process import CommandResult, run_command
from .tools import find_ffmpeg


INTELLIGENCE_SCHEMA_VERSION = 1
WORD_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")


@dataclass(frozen=True)
class IntelligencePaths:
    root: Path
    audio: Path
    transcripts: Path
    words: Path
    searches: Path
    clips: Path
    vault: Path
    manifest: Path


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def intelligence_paths(batch_root: Path) -> IntelligencePaths:
    root = batch_root / "intelligence"
    return IntelligencePaths(
        root=root,
        audio=root / "audio",
        transcripts=root / "transcripts",
        words=root / "words",
        searches=root / "searches",
        clips=root / "clips",
        vault=root / "vault",
        manifest=root / "manifest.json",
    )


def ensure_intelligence_dirs(paths: IntelligencePaths) -> None:
    for path in [paths.root, paths.audio, paths.transcripts, paths.words, paths.searches, paths.clips, paths.vault]:
        path.mkdir(parents=True, exist_ok=True)


def tokenize_text(value: str) -> list[str]:
    return WORD_RE.findall(value.lower())


def normalize_word(value: object) -> str:
    tokens = tokenize_text(str(value or ""))
    return tokens[0] if tokens else ""


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or "query"


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def read_word_input(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [dict(row) for row in payload]
        if isinstance(payload, dict) and isinstance(payload.get("words"), list):
            return [dict(row) for row in payload["words"]]
        raise ValueError("JSON word input must be an array or an object with a words array")
    return read_jsonl(path)


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def manifest_batch_id(manifest_path: Path, manifest: dict) -> str:
    return str(manifest.get("name") or manifest_path.parent.name)


def item_index(manifest: dict) -> dict[str, dict]:
    ledger_path = manifest.get("paths", {}).get("item_ledger")
    if not ledger_path:
        return {}
    index: dict[str, dict] = {}
    for item in load_item_ledger(Path(ledger_path)):
        for key in [item.get("id"), item.get("url"), item.get("output_path")]:
            if key:
                index[str(key)] = item
    return index


def lookup_item(defaults: dict, items: dict[str, dict]) -> dict:
    for key in [defaults.get("item_id"), defaults.get("video_id"), defaults.get("source_url"), defaults.get("media_path")]:
        if key and str(key) in items:
            return items[str(key)]
    return {}


def normalize_word_rows(
    rows: Iterable[dict],
    *,
    manifest_path: Path,
    manifest: dict,
    video_id: str | None = None,
    item_id: str | None = None,
    media_path: str | None = None,
    engine: str = "imported",
) -> list[dict]:
    batch_id = manifest_batch_id(manifest_path, manifest)
    items = item_index(manifest)
    normalized_rows: list[dict] = []
    for source_index, row in enumerate(rows, start=1):
        raw_word = row.get("word", row.get("token", row.get("text", "")))
        normalized = str(row.get("normalized") or normalize_word(raw_word))
        if not normalized:
            continue
        start = float(row.get("start", row.get("start_seconds", 0)))
        end = float(row.get("end", row.get("end_seconds", row.get("stop", start))))
        if end <= start:
            raise ValueError(f"word end must be after start at source row {source_index}")
        defaults = {
            "item_id": item_id or row.get("item_id") or row.get("id") or video_id or row.get("video_id"),
            "video_id": video_id or row.get("video_id") or row.get("id") or item_id,
            "source_url": row.get("source_url") or row.get("url"),
            "media_path": media_path or row.get("media_path") or row.get("output_path"),
        }
        item = lookup_item(defaults, items)
        resolved_video_id = str(defaults["video_id"] or item.get("id") or "unknown")
        resolved_item_id = str(defaults["item_id"] or item.get("id") or resolved_video_id)
        resolved_media_path = str(defaults["media_path"] or item.get("output_path") or "")
        normalized_rows.append(
            {
                "schema_version": INTELLIGENCE_SCHEMA_VERSION,
                "batch_id": batch_id,
                "item_id": resolved_item_id,
                "video_id": resolved_video_id,
                "source_url": str(defaults["source_url"] or item.get("url") or ""),
                "media_path": resolved_media_path,
                "word_index": int(row.get("word_index", len(normalized_rows))),
                "word": str(raw_word),
                "normalized": normalized,
                "start": round(start, 3),
                "end": round(end, 3),
                "confidence": row.get("confidence"),
                "speaker": row.get("speaker"),
                "engine": str(row.get("engine") or engine),
                "imported_at": now_iso(),
            }
        )
    return normalized_rows


def write_intelligence_manifest(paths: IntelligencePaths, *, manifest_path: Path, manifest: dict) -> None:
    payload = {
        "schema_version": INTELLIGENCE_SCHEMA_VERSION,
        "batch_manifest": str(manifest_path),
        "batch_id": manifest_batch_id(manifest_path, manifest),
        "created_or_updated": now_iso(),
        "paths": {
            "audio": str(paths.audio),
            "transcripts": str(paths.transcripts),
            "words": str(paths.words),
            "searches": str(paths.searches),
            "clips": str(paths.clips),
            "vault": str(paths.vault),
        },
        "policy": {
            "lawful_local_media_only": True,
            "does_not_download_media": True,
            "does_not_bypass_source_controls": True,
        },
    }
    paths.manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def init_intelligence(manifest_path: Path) -> Path:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    paths = intelligence_paths(manifest_path.parent)
    ensure_intelligence_dirs(paths)
    write_intelligence_manifest(paths, manifest_path=manifest_path, manifest=manifest)
    return paths.manifest


def doctor_intelligence(manifest_path: Path) -> list[Check]:
    paths = intelligence_paths(manifest_path.parent)
    ffmpeg = find_ffmpeg()
    status = intelligence_status(manifest_path)
    return [
        Check("batch manifest", manifest_path.exists(), str(manifest_path)),
        Check("intelligence workspace", paths.root.exists(), str(paths.root) if paths.root.exists() else "not initialized"),
        Check("word ledger", True, f"{status['words']} word(s) in {status['word_files']} file(s)"),
        Check("ffmpeg", ffmpeg.ok, ffmpeg.detail if not ffmpeg.version else ffmpeg.version),
        Check("asr backend", True, "optional; MVP supports imported Parakeet/NeMo-compatible word ledgers"),
    ]


def import_words(
    manifest_path: Path,
    words_path: Path,
    *,
    video_id: str | None = None,
    item_id: str | None = None,
    media_path: str | None = None,
    engine: str = "imported",
) -> tuple[Path, int]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    paths = intelligence_paths(manifest_path.parent)
    ensure_intelligence_dirs(paths)
    rows = normalize_word_rows(
        read_word_input(words_path),
        manifest_path=manifest_path,
        manifest=manifest,
        video_id=video_id,
        item_id=item_id,
        media_path=media_path,
        engine=engine,
    )
    if not rows:
        raise ValueError("No valid word rows were found")
    target_id = slugify(video_id or item_id or rows[0]["video_id"])
    target = paths.words / f"{target_id}.words.jsonl"
    write_jsonl(target, rows)
    write_intelligence_manifest(paths, manifest_path=manifest_path, manifest=manifest)
    return target, len(rows)


def load_all_words(manifest_path: Path) -> list[dict]:
    paths = intelligence_paths(manifest_path.parent)
    rows: list[dict] = []
    for path in sorted(paths.words.glob("*.words.jsonl")):
        rows.extend(read_jsonl(path))
    return rows


def group_words(rows: Iterable[dict]) -> list[list[dict]]:
    groups: dict[tuple[str, str, str], list[dict]] = {}
    for row in rows:
        key = (str(row.get("video_id", "")), str(row.get("item_id", "")), str(row.get("media_path", "")))
        groups.setdefault(key, []).append(row)
    return [
        sorted(group, key=lambda row: (float(row.get("start", 0)), int(row.get("word_index", 0))))
        for group in groups.values()
    ]


def phrase_context(group: list[dict], start_index: int, end_index: int, *, window: int = 8) -> str:
    left = max(0, start_index - window)
    right = min(len(group), end_index + window + 1)
    return " ".join(str(row.get("word", "")) for row in group[left:right]).strip()


def confidence_summary(rows: list[dict]) -> dict[str, float | None]:
    values = [float(row["confidence"]) for row in rows if row.get("confidence") is not None]
    if not values:
        return {"min": None, "mean": None}
    return {"min": round(min(values), 4), "mean": round(mean(values), 4)}


def search_words(
    manifest_path: Path,
    query: str,
    *,
    pad_start: float = 0.5,
    pad_end: float = 0.75,
    context_window: int = 8,
) -> list[dict]:
    tokens = tokenize_text(query)
    if not tokens:
        raise ValueError("Search query must contain at least one word token")
    matches: list[dict] = []
    for group in group_words(load_all_words(manifest_path)):
        normalized = [str(row.get("normalized") or normalize_word(row.get("word"))) for row in group]
        for start_index in range(0, len(group) - len(tokens) + 1):
            if normalized[start_index : start_index + len(tokens)] != tokens:
                continue
            end_index = start_index + len(tokens) - 1
            hit_rows = group[start_index : end_index + 1]
            start = float(hit_rows[0]["start"])
            end = float(hit_rows[-1]["end"])
            confidence = confidence_summary(hit_rows)
            matches.append(
                {
                    "schema_version": INTELLIGENCE_SCHEMA_VERSION,
                    "query": query,
                    "query_tokens": tokens,
                    "video_id": str(hit_rows[0].get("video_id", "")),
                    "item_id": str(hit_rows[0].get("item_id", "")),
                    "source_url": str(hit_rows[0].get("source_url", "")),
                    "media_path": str(hit_rows[0].get("media_path", "")),
                    "word_start_index": int(hit_rows[0].get("word_index", start_index)),
                    "word_end_index": int(hit_rows[-1].get("word_index", end_index)),
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "clip_start": round(max(0.0, start - pad_start), 3),
                    "clip_end": round(max(end, end + pad_end), 3),
                    "confidence_min": confidence["min"],
                    "confidence_mean": confidence["mean"],
                    "speaker": hit_rows[0].get("speaker"),
                    "context": phrase_context(group, start_index, end_index, window=context_window),
                }
            )
    return matches


def write_search_results(manifest_path: Path, query: str, matches: list[dict]) -> Path:
    paths = intelligence_paths(manifest_path.parent)
    ensure_intelligence_dirs(paths)
    target = paths.searches / f"{slugify(query)}.matches.jsonl"
    write_jsonl(target, matches)
    return target


def make_clip_plan(
    manifest_path: Path,
    query: str,
    *,
    pad_start: float = 0.5,
    pad_end: float = 0.75,
) -> tuple[Path, dict]:
    matches = search_words(manifest_path, query, pad_start=pad_start, pad_end=pad_end)
    if any(not str(match.get("media_path", "")).strip() for match in matches):
        raise ValueError("Cannot create clip plan because one or more matches do not have a local media_path")
    paths = intelligence_paths(manifest_path.parent)
    plan_root = paths.clips / slugify(query)
    plan_root.mkdir(parents=True, exist_ok=True)
    clips: list[dict] = []
    for index, match in enumerate(matches, start=1):
        clip_output = plan_root / f"{index:04d}-{slugify(match.get('video_id') or 'clip')}.mp4"
        clips.append(
            {
                "index": index,
                "source": match["media_path"],
                "start": match["clip_start"],
                "end": match["clip_end"],
                "duration": round(float(match["clip_end"]) - float(match["clip_start"]), 3),
                "output": str(clip_output),
                "match": match,
            }
        )
    plan = {
        "schema_version": INTELLIGENCE_SCHEMA_VERSION,
        "created": now_iso(),
        "batch_manifest": str(manifest_path),
        "query": query,
        "pad_start": pad_start,
        "pad_end": pad_end,
        "clip_count": len(clips),
        "clips": clips,
        "concat_list": str(plan_root / "concat.txt"),
        "montage_output": str(plan_root / f"{slugify(query)}-montage.mp4"),
        "rendering": {
            "requires_ffmpeg": True,
            "mode": "reencode-clips-then-concat",
        },
    }
    target = plan_root / "clip-plan.json"
    target.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_search_results(manifest_path, query, matches)
    return target, plan


def ffconcat_line(path: Path) -> str:
    value = path.resolve().as_posix().replace("'", "'\\''")
    return f"file '{value}'"


def render_clip_plan(plan_path: Path) -> tuple[list[CommandResult], Path | None]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    ffmpeg = find_ffmpeg()
    if not ffmpeg.path:
        raise RuntimeError("ffmpeg not found")
    results: list[CommandResult] = []
    rendered: list[Path] = []
    for clip in plan.get("clips", []):
        source = Path(str(clip.get("source", "")))
        if not source.exists():
            raise FileNotFoundError(f"clip source not found: {source}")
        output = Path(str(clip["output"]))
        output.parent.mkdir(parents=True, exist_ok=True)
        duration = max(0.01, float(clip["duration"]))
        args = [
            ffmpeg.path,
            "-y",
            "-i",
            source,
            "-ss",
            f"{float(clip['start']):.3f}",
            "-t",
            f"{duration:.3f}",
            "-map",
            "0:v:0?",
            "-map",
            "0:a:0?",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            output,
        ]
        result = run_command(args, timeout=60 * 60)
        results.append(result)
        if not result.ok:
            return results, None
        rendered.append(output)
    if not rendered:
        return results, None
    concat = Path(str(plan["concat_list"]))
    concat.write_text("\n".join(ffconcat_line(path) for path in rendered) + "\n", encoding="utf-8")
    montage = Path(str(plan["montage_output"]))
    montage_result = run_command([ffmpeg.path, "-y", "-f", "concat", "-safe", "0", "-i", concat, "-c", "copy", montage], timeout=60 * 60)
    results.append(montage_result)
    return results, montage if montage_result.ok else None


def build_vault(manifest_path: Path) -> tuple[Path, int]:
    paths = intelligence_paths(manifest_path.parent)
    ensure_intelligence_dirs(paths)
    groups = group_words(load_all_words(manifest_path))
    pages = 0
    index_lines = [
        "---",
        "type: transcript-vault-index",
        f"created: {now_iso()}",
        "---",
        "",
        "# Transcript Vault",
        "",
    ]
    for group in groups:
        if not group:
            continue
        first = group[0]
        video_id = str(first.get("video_id") or first.get("item_id") or "unknown")
        title = video_id
        page = paths.vault / f"{slugify(video_id)}.md"
        text = " ".join(str(row.get("word", "")) for row in group).strip()
        page.write_text(
            "\n".join(
                [
                    "---",
                    "type: transcript",
                    f"video_id: {json.dumps(video_id)}",
                    f"source_url: {json.dumps(first.get('source_url') or '')}",
                    f"media_path: {json.dumps(first.get('media_path') or '')}",
                    f"word_count: {len(group)}",
                    "---",
                    "",
                    f"# {title}",
                    "",
                    "## Source",
                    "",
                    f"- Video ID: `{video_id}`",
                    f"- Media: `{first.get('media_path') or ''}`",
                    f"- Source: {first.get('source_url') or ''}",
                    "",
                    "## Transcript",
                    "",
                    text,
                    "",
                ]
            ),
            encoding="utf-8",
        )
        index_lines.append(f"- [[{page.stem}]] - {len(group)} words")
        pages += 1
    (paths.vault / "index.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    return paths.vault, pages


def intelligence_status(manifest_path: Path) -> dict:
    paths = intelligence_paths(manifest_path.parent)
    word_files = sorted(paths.words.glob("*.words.jsonl")) if paths.words.exists() else []
    search_files = sorted(paths.searches.glob("*.matches.jsonl")) if paths.searches.exists() else []
    clip_plans = sorted(paths.clips.glob("*/clip-plan.json")) if paths.clips.exists() else []
    return {
        "root": str(paths.root),
        "word_files": len(word_files),
        "words": sum(len(read_jsonl(path)) for path in word_files),
        "search_files": len(search_files),
        "clip_plans": len(clip_plans),
        "vault_exists": (paths.vault / "index.md").exists(),
    }
