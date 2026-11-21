"""Loopback hub and independent owner console. No network handler runs cognition."""
from __future__ import annotations

import hmac
import json
import os
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .common import read_json


def owner_token(state_dir):
    path = Path(state_dir) / "desktop_owner_token.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return path.read_text(encoding="utf-8").strip()
    token = secrets.token_urlsafe(32)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(token)
    return token


def make_server(runtime, *, port=8790, token=None):
    token = token or owner_token(runtime.state_dir)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, status, value, ctype="application/json; charset=utf-8"):
            body = value.encode() if isinstance(value, str) else json.dumps(value, default=str).encode()
            self.send_response(status)
            for key, val in {"Content-Type": ctype, "Content-Length": str(len(body)), "Cache-Control": "no-store",
                             "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
                             "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; object-src 'none'; frame-ancestors 'none'"}.items():
                self.send_header(key, val)
            self.end_headers()
            self.wfile.write(body)

        def authorized(self):
            expected_host = f"127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") not in {expected_host, f"localhost:{self.server.server_port}"}:
                self.send(403, {"error": "host"})
                return False
            origin = self.headers.get("Origin")
            if origin and origin not in {"http://" + expected_host, f"http://localhost:{self.server.server_port}"}:
                self.send(403, {"error": "origin"})
                return False
            got = self.headers.get("Authorization", "").removeprefix("Bearer ")
            if not hmac.compare_digest(got, token):
                self.send(401, {"error": "owner_authentication_required"})
                return False
            return True

        def do_GET(self):
            parsed = urlsplit(self.path)
            path, q = parsed.path, parse_qs(parsed.query)
            if path in {"/", "/owner", "/diagnostics"}:
                from .page import PAGE
                self.send(200, PAGE, "text/html; charset=utf-8")
                return
            if not self.authorized():
                return
            try:
                if path == "/api/status":
                    return self.send(200, runtime.status())
                if path.startswith("/api/jobs/"):
                    job = runtime.job(path.rsplit("/", 1)[1])
                    return self.send(200 if job else 404, job or {"error": "unknown_job"})
                if path == "/api/blueprints":
                    return self.send(200, runtime.blueprints.view(query=q.get("q", [""])[0]))
                if path == "/api/demonstrations":
                    return self.send(200, runtime.demonstrations.view())
                if path == "/api/diagnostics":
                    from aurora_internal.hub_panels import strata_panel, pass_panel
                    return self.send(200, {"runtime": runtime.status(), "strata": strata_panel(str(runtime.state_dir)),
                                           "crystal_pass": pass_panel(str(runtime.state_dir)),
                                           "last_diagnosis": read_json(runtime.state_dir / "last_system_diagnosis.json")})
                if path.startswith("/api/concepts"):
                    from aurora_internal.crystal_web import ConceptWeb
                    web = ConceptWeb.from_file(str(runtime.state_dir / "dps_crystals.json"))
                    query = q.get("q", [""])[0]
                    return self.send(200, web.neighborhood(query) if query else web.overview())
                self.send(404, {"error": "not_found"})
            except Exception as exc:
                self.send(400, {"error": str(exc)[:500]})

        def do_POST(self):
            if not self.authorized():
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 256_000:
                    return self.send(413, {"error": "body_size"})
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError("object required")
                path = urlsplit(self.path).path
                if path == "/api/chat":
                    text = str(data.get("text") or "").strip()
                    if not text or len(text) > 16000:
                        raise ValueError("1-16000 characters required")
                    return self.send(202, runtime.submit("turn", {"text": text}, job_id=data.get("request_id")))
                if path == "/api/owner":
                    action = data.get("action")
                    if action == "stop":
                        runtime._stop.set()
                        return self.send(200, {"ok": True, "status": "stopping", "active_job": runtime.active_job})
                    if action in {"pause", "resume"}:
                        runtime.background = action == "resume"
                        return self.send(200, {"ok": True, "background_enabled": runtime.background})
                    if action == "console":
                        # Explicit owner command; independent of the cognitive
                        # queue so a broken boot cannot take away recovery.
                        from aurora_desktop_agent import shell_command
                        cmd = str(data.get("command") or "")
                        if not cmd or len(cmd) > 8000:
                            raise ValueError("command required")
                        return self.send(200, shell_command(cmd, cwd=str(runtime.state_dir)))
                    allowed = {"operation", "compose", "demo_begin", "demo_finish", "demo_verify", "refresh", "sensor_control",
                               "clone_absorb", "save", "handoff_prepare", "handoff_claim", "handoff_cancel", "move_surface"}
                    if action not in allowed:
                        raise ValueError("unknown owner action")
                    return self.send(202, runtime.submit(action, data.get("payload", {}), owner=True,
                                                        job_id=data.get("request_id")))
                self.send(404, {"error": "not_found"})
            except (ValueError, KeyError, TypeError) as exc:
                self.send(400, {"error": str(exc)[:500]})
            except RuntimeError as exc:
                self.send(503, {"error": str(exc)[:500]})
        do_PUT = do_DELETE = do_PATCH = lambda self: self.send(405, {"error": "method_not_allowed"})
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server
