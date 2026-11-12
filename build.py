"""Build the static snapshot used by GitHub Pages (or any static host)."""

from __future__ import annotations

from pathlib import Path

import cache
import theme
from sources import fetch_all

ROOT = Path(__file__).resolve().parent
DOCS_DATA = ROOT / "docs" / "data" / "contests.json"
CACHE_PATH = ROOT / "data" / "cache.json"


def main() -> None:
    previous = cache.load_json(CACHE_PATH) or cache.load_json(DOCS_DATA)
    fresh = fetch_all()
    merged = cache.merge(fresh, previous)

    cache.write_json_atomic(DOCS_DATA, merged)
    cache.write_json_atomic(CACHE_PATH, merged)
    theme.write_theme_css()

    ok = sum(1 for source in merged.get("sources", []) if source.get("ok"))
    total = len(merged.get("sources", []))
    print(
        f"Wrote {DOCS_DATA} with {len(merged.get('contests', []))} contests "
        f"({ok}/{total} sources ok)"
    )


if __name__ == "__main__":
    main()
