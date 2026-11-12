"""AtCoder's public upcoming-contests table.

AtCoder has no official JSON API, so this adapter reads the server-rendered
`#contest-table-upcoming` section. It is intentionally tolerant of markup
details, but AtCoder can still change the page structure.
"""

from __future__ import annotations

import re
import time
from datetime import datetime

from model import Contest

from .common import fetch, parse_hhmm, text_from_html

URL = "https://atcoder.jp/contests/"

_TABLE_START = 'id="contest-table-upcoming"'
_TABLE_END = 'id="contest-table-daily"'
_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_TIME_RE = re.compile(r"<time[^>]*>(.*?)</time>", re.S)
_LINK_RE = re.compile(r'<a\s+href=["\']/contests/([^"\']+)["\'][^>]*>(.*?)</a>', re.S)
_TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)


def _rated_note(raw: str) -> str:
    value = " ".join(raw.split())
    if not value or value == "-":
        return ""
    if value.startswith("- "):
        return f"Rated \u2264 {value[2:].strip()}"
    if value.endswith(" -"):
        return f"Rated \u2265 {value[:-2].strip()}"
    if "-" in value:
        return "Rated " + value.replace("-", "\u2013")
    return "Rated " + value


def fetch_contests() -> list[Contest]:
    page = fetch(URL, timeout=35).decode("utf-8", "replace")
    start_index = page.find(_TABLE_START)
    if start_index < 0:
        raise RuntimeError("AtCoder upcoming-contests table was not found")

    section = page[start_index:]
    end_index = section.find(_TABLE_END)
    if end_index >= 0:
        section = section[:end_index]

    now = int(time.time())
    contests: list[Contest] = []

    for row in _ROW_RE.findall(section):
        time_match = _TIME_RE.search(row)
        link_match = _LINK_RE.search(row)
        if not time_match or not link_match:
            continue

        try:
            start = int(
                datetime.strptime(
                    text_from_html(time_match.group(1)), "%Y-%m-%d %H:%M:%S%z"
                ).timestamp()
            )
        except ValueError:
            continue

        slug = link_match.group(1)
        title = text_from_html(link_match.group(2))
        cells = [_ for _ in _TD_RE.findall(row)]
        duration = parse_hhmm(text_from_html(cells[2])) if len(cells) > 2 else 0
        note = _rated_note(text_from_html(cells[3])) if len(cells) > 3 else ""
        end = start + duration
        if end <= now:
            continue

        contests.append(
            Contest(
                key=f"atcoder:{slug}",
                site="atcoder",
                title=title or "AtCoder contest",
                url=f"https://atcoder.jp/contests/{slug}",
                start=start,
                end=end,
                duration=duration,
                kind="contest",
                note=note,
            )
        )

    return contests
