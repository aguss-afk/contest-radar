"""LeetCode's upcoming weekly and biweekly contests via public GraphQL."""

from __future__ import annotations

import json
import time

from model import Contest

from .common import fetch_json

URL = "https://leetcode.com/graphql/"
QUERY = "query { upcomingContests { title titleSlug startTime duration } }"


def fetch_contests() -> list[Contest]:
    payload = fetch_json(
        URL,
        data=json.dumps({"query": QUERY}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Referer": "https://leetcode.com/contest/",
            "Origin": "https://leetcode.com",
        },
        timeout=30,
    )
    if not isinstance(payload, dict):
        raise RuntimeError("LeetCode returned an unexpected response")
    if payload.get("errors"):
        raise RuntimeError(str(payload["errors"])[:300])

    now = int(time.time())
    contests: list[Contest] = []
    for item in (payload.get("data") or {}).get("upcomingContests") or []:
        start = item.get("startTime")
        duration = int(item.get("duration") or 0)
        slug = str(item.get("titleSlug") or "")
        if start is None or not slug:
            continue
        start = int(start)
        end = start + duration
        if end <= now:
            continue

        title = str(item.get("title") or "LeetCode contest")
        note = ""
        lower = title.lower()
        if "weekly" in lower:
            note = "Weekly"
        elif "biweekly" in lower:
            note = "Biweekly"

        contests.append(
            Contest(
                key=f"leetcode:{slug}",
                site="leetcode",
                title=title,
                url=f"https://leetcode.com/contest/{slug}/",
                start=start,
                end=end,
                duration=duration,
                kind="contest",
                note=note,
            )
        )
    return contests
