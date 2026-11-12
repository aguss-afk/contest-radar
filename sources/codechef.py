"""CodeChef live and future contests via the public site endpoint."""

from __future__ import annotations

import time

from model import Contest

from .common import fetch_json, parse_iso

URL = (
    "https://www.codechef.com/api/list/contests/all"
    "?sort_by=START&sorting_order=asc&offset=0&limit=100"
)


def fetch_contests() -> list[Contest]:
    payload = fetch_json(URL, timeout=35)
    if not isinstance(payload, dict) or payload.get("status") != "success":
        raise RuntimeError("CodeChef returned an unexpected response")

    now = int(time.time())
    contests: list[Contest] = []
    seen: set[str] = set()

    for item in (payload.get("present_contests") or []) + (payload.get("future_contests") or []):
        start = parse_iso(item.get("contest_start_date_iso"))
        end = parse_iso(item.get("contest_end_date_iso"))
        duration_minutes = int(item.get("contest_duration") or 0)
        duration = duration_minutes * 60
        if start is None:
            continue
        if end is None:
            end = start + duration
        if end <= now:
            continue

        contest_id = str(item.get("contest_id") or item.get("contest_code") or "")
        if not contest_id or contest_id in seen:
            continue
        seen.add(contest_id)

        code = str(item.get("contest_code") or contest_id)
        title = str(item.get("contest_name") or f"CodeChef {code}")
        contests.append(
            Contest(
                key=f"codechef:{contest_id}",
                site="codechef",
                title=title,
                url=f"https://www.codechef.com/{code}",
                start=start,
                end=end,
                duration=max(0, end - start if not duration else duration),
                kind="contest",
            )
        )

    return contests
