"""HackerEarth competitive challenges, excluding long-running hackathons."""

from __future__ import annotations

import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from model import Contest

from .common import fetch_json

URL = "https://www.hackerearth.com/chrome-extension/events/"
_STAMP_RE = re.compile(r"^(?P<stamp>.+?)\s*\((?P<zone>[^)]+)\)\s*$")


def _parse_stamp(value: object) -> int | None:
    if not value:
        return None
    match = _STAMP_RE.match(str(value).strip())
    if not match:
        return None
    try:
        local = datetime.strptime(match.group("stamp").strip(), "%b %d, %Y %I:%M %p")
        zone = ZoneInfo(match.group("zone").strip())
        return int(local.replace(tzinfo=zone).timestamp())
    except (ValueError, KeyError):
        return None


def fetch_contests() -> list[Contest]:
    payload = fetch_json(URL, timeout=35)
    if not isinstance(payload, dict):
        raise RuntimeError("HackerEarth returned an unexpected response")

    now = int(time.time())
    contests: list[Contest] = []
    for item in payload.get("response") or []:
        if item.get("status") not in {"UPCOMING", "ONGOING"}:
            continue

        url = str(item.get("url") or "")
        kind = str(item.get("challenge_type") or "Challenge")
        if "hackathon" in kind.lower() or "/hackathon/" in url:
            continue

        start = _parse_stamp(item.get("start_timestamp"))
        end = _parse_stamp(item.get("end_timestamp"))
        if start is None or end is None or end <= now:
            continue

        contests.append(
            Contest(
                key=f"hackerearth:{url or item.get('title')}",
                site="hackerearth",
                title=str(item.get("title") or "HackerEarth challenge"),
                url=url,
                start=start,
                end=end,
                duration=max(0, end - start),
                kind="challenge",
                note=kind,
            )
        )
    return contests
