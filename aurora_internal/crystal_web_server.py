# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Serve the subsurface hub (read-only): the concept web and the ledger, strata link and pass panels from the desktop subsurface: `python -m aurora_internal.crystal_web_server --state-dir aurora_state`.

Standard library only; GET only; reads `dps_crystals.json` and reloads it when the file changes.  It binds to the loopback address unless told otherwise.  To reach it from
the phone over the private tunnel, give `--host <tunnel address>` and a `--token`: every request must then carry `t=<token>` (the page passes its own through).
Nothing here imports Aurora's stack, and nothing writes.
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import aurora_internal.hub_panels as _P
from aurora_internal.crystal_web import ConceptWeb

FILE = "dps_crystals.json"


class WebSource:
    """The current `ConceptWeb`, reloaded when the store's file changes (checked on every request, not on a timer)."""

    def __init__(self, state_dir: str) -> None:
        self.state_dir = str(state_dir)
        self.path = os.path.join(self.state_dir, FILE)
        self._lock = threading.Lock()
        self._stamp: Optional[Tuple[float, int]] = None
        self._web = ConceptWeb({})

    def get(self) -> ConceptWeb:
        try:
            st = os.stat(self.path)
            stamp = (st.st_mtime, st.st_size)
        except OSError:
            return self._web
        with self._lock:
            if stamp != self._stamp:
                try:
                    self._web = ConceptWeb.from_file(self.path)
                    self._stamp = stamp
                except Exception:
                    pass                                         # a file caught mid-write: keep the last good view
            return self._web


def _int(q, key, default, lo, hi):
    try:
        return max(lo, min(hi, int(q.get(key, [default])[0])))
    except (TypeError, ValueError):
        return default


def make_handler(source: WebSource, token: str = ""):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AuroraConceptWeb"

        def log_message(self, *a):                               # quiet
            pass

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj: Any) -> None:
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self) -> None:                                # noqa: N802
            u = urlparse(self.path)
            q = parse_qs(u.query)
            if token and not hmac.compare_digest(str((q.get("t") or [""])[0]), token):
                return self._json(403, {"error": "forbidden"})
            web = source.get()
            if u.path in ("/", "/index.html"):
                from aurora_internal.crystal_web_page import PAGE
                return self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            if u.path == "/api/overview":
                return self._json(200, web.overview(_int(q, "top", 40, 1, 200)))
            if u.path == "/api/search":
                return self._json(200, {"results": web.search((q.get("q") or [""])[0], _int(q, "limit", 20, 1, 100))})
            if u.path == "/api/ledger":
                return self._json(200, _P.ledger_panel(web.crystals(), _int(q, "top", 40, 1, 200)))
            if u.path == "/api/strata":
                return self._json(200, _P.strata_panel(source.state_dir))
            if u.path == "/api/pass":
                return self._json(200, _P.pass_panel(source.state_dir))
            name = (q.get("name") or [""])[0]
            if u.path == "/api/concept":
                card = web.lookup(name, _int(q, "ties", 40, 1, 200))
                return self._json(200 if card else 404, card or {"error": "unknown concept"})
            if u.path == "/api/web":
                g = web.neighborhood(name, _int(q, "depth", 1, 1, 3), _int(q, "max", 60, 2, 300), _int(q, "fan", 12, 1, 40))
                return self._json(200 if g else 404, g or {"error": "unknown concept"})
            return self._json(404, {"error": "not found"})

        def do_POST(self) -> None:                               # noqa: N802
            self._json(405, {"error": "read-only"})

        do_PUT = do_DELETE = do_PATCH = do_POST

    return Handler


def serve(state_dir: str, host: str = "127.0.0.1", port: int = 8792, token: str = "") -> ThreadingHTTPServer:
    if host not in ("127.0.0.1", "localhost", "::1") and not token:
        raise SystemExit("refusing to bind beyond loopback without --token")
    return ThreadingHTTPServer((host, port), make_handler(WebSource(state_dir), token))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Aurora concept web (read-only)")
    ap.add_argument("--state-dir", default="aurora_state")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8792)
    ap.add_argument("--token", default=os.environ.get("AURORA_CONCEPT_WEB_TOKEN", ""))
    a = ap.parse_args(argv)
    srv = serve(a.state_dir, a.host, a.port, a.token)
    print(f"concept web on http://{a.host}:{srv.server_address[1]}/" + (f"?t={a.token}" if a.token else ""))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
