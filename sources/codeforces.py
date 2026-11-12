"""Codeforces contests and gym contests via the official API."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

from model import Contest

from .common import fetch_json

API = "https://codeforces.com/api/contest.list?gym=false"
GYM_API = "https://codeforces.com/api/contest.list?gym=true"


def _fetch_one(gym: bool) -> list[Contest]:
    payload = fetch_json(GYM_API if gym else API, timeout=45)
    if not isinstance(payload, dict) or payload.get("status") != "OK":
        raise RuntimeError("Codeforces API returned a non-OK status")

    now = int(time.time())
    contests: list[Contest] = []
    for item in payload.get("result") or []:
        start = item.get("startTimeSeconds")
        duration = int(item.get("durationSeconds") or 0)
        if start is None or duration <= 0:
            continue
        start = int(start)
        end = start + duration
        # Skip finished contests, plus ancient gym placeholders with absurdly
        # long windows (some self-test gyms run for years).
        if end <= now or start < now - 86400:
            continue
        if gym and duration > 7 * 86400:
            continue

        contest_id = str(item.get("id"))
        site = "codeforces"
        kind = "gym" if gym else "contest"
        note = "Gym" if gym else str(item.get("type") or "")
        url = f"https://codeforces.com/{'gym' if gym else 'contest'}/{contest_id}"

        contests.append(
            Contest(
                key=f"{site}:{'gym-' if gym else ''}{contest_id}",
                site=site,
                title=str(item.get("name") or "Codeforces contest"),
                url=url,
                start=start,
                end=end,
                duration=duration,
                kind=kind,
                note=note,
            )
        )
    return contests


def fetch() -> list[Contest]:
    results: list[Contest] = []
    errors: list[Exception] = []

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(_fetch_one, False), pool.submit(_fetch_one, True)]
        for future in futures:
            try:
                results.extend(future.result())
            except Exception as exc:  # gym failures should not hide the main list
                errors.append(exc)

    if errors and not results:
        raise errors[0]
    return results
