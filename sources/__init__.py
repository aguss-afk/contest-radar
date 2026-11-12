"""Registry and parallel fetch entry point for all contest sources."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import atcoder, codechef, codeforces, hackerearth, hackerrank, leetcode

SOURCES = [
    ("codeforces", "Codeforces", codeforces.fetch),
    ("atcoder", "AtCoder", atcoder.fetch_contests),
    ("codechef", "CodeChef", codechef.fetch_contests),
    ("leetcode", "LeetCode", leetcode.fetch_contests),
    ("hackerrank", "HackerRank", hackerrank.fetch_contests),
    ("hackerearth", "HackerEarth", hackerearth.fetch_contests),
]

_ORDER = {source_id: index for index, (source_id, _, _) in enumerate(SOURCES)}


def fetch_all(now: int | None = None) -> dict:
    now = int(now if now is not None else time.time())
    contests = []
    sources = []
    seen: set[str] = set()

    with ThreadPoolExecutor(max_workers=len(SOURCES)) as pool:
        futures = {
            pool.submit(fetch): (source_id, name)
            for source_id, name, fetch in SOURCES
        }
        for future in as_completed(futures):
            source_id, name = futures[future]
            try:
                items = future.result()
                items = [item for item in items if item.end > now]
                for item in items:
                    if item.key in seen:
                        continue
                    seen.add(item.key)
                    contests.append(item)
                sources.append(
                    {
                        "id": source_id,
                        "name": name,
                        "ok": True,
                        "count": len(items),
                        "error": None,
                        "last_success": now,
                    }
                )
            except Exception as exc:
                sources.append(
                    {
                        "id": source_id,
                        "name": name,
                        "ok": False,
                        "count": 0,
                        "error": f"{type(exc).__name__}: {exc}"[:300],
                        "last_success": None,
                    }
                )

    sources.sort(key=lambda item: _ORDER.get(item["id"], 999))
    contests.sort(key=lambda item: (item.start, item.title.lower()))
    return {
        "schema": 1,
        "generated_at": now,
        "contests": [item.to_dict() for item in contests],
        "sources": sources,
    }
