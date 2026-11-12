"""HackerRank upcoming contests via the site's public REST endpoint."""

from __future__ import annotations

import time

from model import Contest

from .common import fetch_json

URL = "https://www.hackerrank.com/rest/contests/upcoming?limit=50&offset=0"


def fetch_contests() -> list[Contest]:
    payload = fetch_json(URL, timeout=35)
    if not isinstance(payload, dict):
        raise RuntimeError("HackerRank returned an unexpected response")

    now = int(time.time())
    contests: list[Contest] = []
    for item in payload.get("models") or []:
        if item.get("ended"):
            continue
        start = item.get("epoch_starttime")
        end = item.get("epoch_endtime")
        slug = str(item.get("slug") or "")
        if start is None or end is None or not slug:
            continue
        start, end = int(start), int(end)
        if end <= now:
            continue

        rated = bool(item.get("rated"))
        contests.append(
            Contest(
                key=f"hackerrank:{item.get('id') or slug}",
                site="hackerrank",
                title=str(item.get("name") or "HackerRank contest"),
                url=f"https://www.hackerrank.com/contests/{slug}",
                start=start,
                end=end,
                duration=max(0, end - start),
                kind="contest",
                note="Rated" if rated else "",
                rated=rated,
            )
        )
    return contests
