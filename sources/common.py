"""Small HTTP and parsing helpers. No third-party dependencies."""

from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36 ContestRadar/1.0"
)

_TAG_RE = re.compile(r"<[^>]+>")


def fetch(
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 35,
    retries: int = 2,
) -> bytes:
    """GET/POST a URL with a browser-ish user agent and a couple of retries."""
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/json,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "identity",
        "Cache-Control": "no-cache",
    }
    if headers:
        request_headers.update(headers)

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(url, data=data, headers=request_headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.8 + attempt * 0.9)

    if last_error is None:
        raise RuntimeError(f"request failed: {url}")
    raise last_error


def fetch_json(
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 35,
    retries: int = 2,
) -> dict | list:
    raw = fetch(url, data=data, headers=headers, timeout=timeout, retries=retries)
    return json.loads(raw.decode("utf-8", "replace"))


def parse_iso(value: object) -> int | None:
    if not value:
        return None
    try:
        return int(datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp())
    except (TypeError, ValueError):
        return None


def parse_hhmm(value: str) -> int:
    """Parse AtCoder's `01:40` duration format into seconds."""
    match = re.fullmatch(r"\s*(\d+):(\d{2})\s*", value or "")
    if not match:
        return 0
    return int(match.group(1)) * 3600 + int(match.group(2)) * 60


def text_from_html(value: str) -> str:
    return " ".join(html.unescape(_TAG_RE.sub(" ", value or "")).split())


def clamp_text(value: object, limit: int = 180) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]
