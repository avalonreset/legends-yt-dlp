from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .batch import (
    BatchPaths,
    classify_success,
    create_batch_from_urls,
    diagnostic_output,
    js_runtime_args,
    validate_url,
)
from .ledger import item_from_inventory_entry
from .process import CommandResult, run_command
from .tools import find_ytdlp


@dataclass(frozen=True)
class InventoryResult:
    source_url: str
    entries: list[dict]
    warnings: tuple[str, ...]


def run_ytdlp_inventory(source_url: str, *, max_items: int | None = None) -> CommandResult:
    if max_items is not None and max_items <= 0:
        raise ValueError("--max-items must be greater than 0")
    tool = find_ytdlp()
    if not tool.path:
        return CommandResult(("yt-dlp",), 127, "", "yt-dlp not found")
    args: list[str | Path] = [
        tool.path,
        "--ignore-config",
        "--no-cookies",
        "--no-cookies-from-browser",
        *js_runtime_args(),
        "--flat-playlist",
        "--dump-single-json",
    ]
    if max_items:
        args.extend(["--playlist-end", str(max_items)])
    args.append(source_url)
    return run_command(args, timeout=30 * 60)


def parse_inventory_json(source_url: str, stdout: str, stderr: str = "") -> InventoryResult:
    data = json.loads(stdout)
    raw_entries = data.get("entries")
    if isinstance(raw_entries, list):
        entries = [entry for entry in raw_entries if isinstance(entry, dict)]
    else:
        entries = [data]
    warnings = tuple(line for line in stderr.splitlines() if line.lower().startswith("warning:"))
    return InventoryResult(source_url=source_url, entries=entries, warnings=warnings)


def filter_entries(entries: list[dict], *, live_statuses: set[str] | None = None) -> list[dict]:
    if not live_statuses:
        return entries
    return [entry for entry in entries if str(entry.get("live_status") or "").lower() in live_statuses]


def inventory_items(result: InventoryResult, *, live_statuses: set[str] | None = None) -> list[dict]:
    entries = filter_entries(result.entries, live_statuses=live_statuses)
    return [
        item_from_inventory_entry(entry, source_url=result.source_url, position=index + 1)
        for index, entry in enumerate(entries)
    ]


def create_batch_from_inventory(
    *,
    source_url: str,
    rights_basis: str | None = None,
    name: str | None = None,
    output_dir: str | None = None,
    max_height: int | None = None,
    max_downloads: int | None = None,
    max_filesize: str | None = None,
    max_items: int | None = None,
    live_statuses: set[str] | None = None,
    rights_file: str | None = None,
    folder_policy: str = "auto",
    with_vpn: bool = False,
) -> tuple[BatchPaths, InventoryResult]:
    if not validate_url(source_url):
        raise ValueError(f"Invalid URL: {source_url}")
    result = run_ytdlp_inventory(source_url, max_items=max_items)
    if result.returncode != 0:
        output = diagnostic_output(result) or result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(output or "yt-dlp inventory failed")
    category = classify_success(result)
    if category == "source-warning":
        output = diagnostic_output(result)
        raise RuntimeError(
            "Source-side warning detected during inventory; pausing without creating a batch.\n"
            + (output or "Review the source manually before continuing.")
        )
    inventory = parse_inventory_json(source_url, result.stdout, result.stderr)
    items = inventory_items(inventory, live_statuses=live_statuses)
    urls = [str(item.get("url", "")) for item in items if item.get("url")]
    if not urls:
        raise ValueError("Inventory produced no downloadable URLs after filters")
    paths = create_batch_from_urls(
        urls=urls,
        rights_basis=rights_basis,
        name=name,
        output_dir=output_dir,
        max_height=max_height,
        max_downloads=max_downloads,
        max_filesize=max_filesize,
        items=items,
        rights_file=rights_file,
        folder_policy=folder_policy,
        with_vpn=with_vpn,
    )
    return paths, inventory
