"""Contest Radar local server: live aggregation plus static file serving.

Run:
    python3 server.py --open

No third-party packages are required.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

import cache
import theme
from sources import fetch_all

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
CACHE_PATH = ROOT / "data" / "cache.json"


class ContestStore:
    def __init__(self, refresh_seconds: int = 600) -> None:
        self.refresh_seconds = max(60, refresh_seconds)
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.refreshing = False

        cached = cache.load_json(CACHE_PATH)
        if not cached.get("contests"):
            cached = cache.load_json(DOCS / "data" / "contests.json")
        self.data = cached if isinstance(cached, dict) else {}
        self.thread = threading.Thread(target=self._run, name="contest-refresh", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def snapshot(self) -> dict:
        with self.lock:
            data = dict(self.data)
            data["refreshing"] = self.refreshing
            data["ready"] = bool(data.get("sources"))
            return data

    def request_refresh(self) -> None:
        self.wake.set()

    def refresh(self) -> None:
        with self.lock:
            if self.refreshing:
                return
            self.refreshing = True
            previous = dict(self.data)

        try:
            fresh = fetch_all()
            merged = cache.merge(fresh, previous)
            with self.lock:
                self.data = merged
            cache.write_json_atomic(CACHE_PATH, merged)
            theme.write_theme_css()

            ok = sum(1 for source in merged.get("sources", []) if source.get("ok"))
            total = len(merged.get("sources", []))
            print(
                f"[contest-radar] refreshed {len(merged.get('contests', []))} contests "
                f"({ok}/{total} sources ok)",
                flush=True,
            )
        except Exception as exc:  # a background refresh must never kill the server
            print(f"[contest-radar] refresh failed: {exc}", flush=True)
        finally:
            with self.lock:
                self.refreshing = False

    def _run(self) -> None:
        while True:
            self.refresh()
            self.wake.wait(self.refresh_seconds)
            self.wake.clear()


class Handler(BaseHTTPRequestHandler):
    server_version = "ContestRadar/1.0"

    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: str, head_only: bool = False) -> None:
        relative = unquote(path).lstrip("/") or "index.html"
        target = (DOCS / relative).resolve()
        try:
            target.relative_to(DOCS.resolve())
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if target.suffix == ".js":
            content_type = "text/javascript; charset=utf-8"
        elif target.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif target.suffix == ".json":
            content_type = "application/json; charset=utf-8"
        elif target.suffix in {".html", ".htm"}:
            content_type = "text/html; charset=utf-8"
        elif target.suffix == ".ttf":
            content_type = "font/ttf"

        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if not head_only:
            self.wfile.write(data)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/contests":
            self._send_json(self.server.store.snapshot())  # type: ignore[attr-defined]
            return
        if path == "/api/health":
            self._send_json({"ok": True, "time": int(time.time())})
            return
        if path == "/api/refresh":
            self._send_json({"ok": False, "error": "use POST"}, HTTPStatus.METHOD_NOT_ALLOWED)
            return
        self._serve_file(path)

    def do_HEAD(self) -> None:
        self._serve_file(urlparse(self.path).path, head_only=True)

    def do_POST(self) -> None:
        if urlparse(self.path).path == "/api/refresh":
            store = self.server.store  # type: ignore[attr-defined]
            store.request_refresh()
            self._send_json({"ok": True, "refreshing": store.refreshing}, HTTPStatus.ACCEPTED)
            return
        self._send_json({"ok": False, "error": "not found"}, HTTPStatus.NOT_FOUND)

    def log_message(self, _format: str, *_args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Contest Radar local server")
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8787, help="port (default: 8787)")
    parser.add_argument("--refresh-seconds", type=int, default=600, help="background refresh interval")
    parser.add_argument("--open", action="store_true", help="open the page in a browser")
    args = parser.parse_args()

    theme.write_theme_css()

    store = ContestStore(args.refresh_seconds)
    store.start()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.daemon_threads = True
    server.store = store  # type: ignore[attr-defined]

    display_host = "127.0.0.1" if args.host in {"0.0.0.0", "::"} else args.host
    url = f"http://{display_host}:{server.server_address[1]}/"
    print(f"[contest-radar] listening on {url}", flush=True)
    if args.open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
