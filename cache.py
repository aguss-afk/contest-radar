"""Tiny JSON cache helpers with atomic writes and failed-source fallback."""

from __future__ import annotations

import json
import os
from pathlib import Path


def load_json(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temporary, path)


def merge(new: dict, old: dict | None) -> dict:
    """Keep previous contests and health for sources that failed this round."""
    old = old or {}
    generated_at = int(new.get("generated_at") or 0)
    failed = {
        source.get("id")
        for source in new.get("sources", [])
        if not source.get("ok")
    }

    previous = [
        contest
        for contest in old.get("contests", [])
        if contest.get("site") in failed
        and int(contest.get("end") or 0) > generated_at
    ]

    seen: set[str] = set()
    contests = []
    for contest in list(new.get("contests", [])) + previous:
        key = contest.get("key")
        if not key or key in seen:
            continue
        seen.add(key)
        contests.append(contest)
    contests.sort(key=lambda item: (int(item.get("start") or 0), str(item.get("title", "")).lower()))

    old_sources = {source.get("id"): source for source in old.get("sources", [])}
    sources = []
    for source in new.get("sources", []):
        if not source.get("ok"):
            previous_source = old_sources.get(source.get("id"), {})
            source = {
                **source,
                "last_success": previous_source.get("last_success"),
                "count": previous_source.get("count", 0),
            }
        sources.append(source)

    return {
        "schema": 1,
        "generated_at": generated_at,
        "contests": contests,
        "sources": sources,
    }
