"""Encrypted, outbound-only internet carriage for Aurora's existing Strata Link.

The relay never runs Aurora, owns her stores, learns her credentials, or sees
plaintext: AES-GCM protects the *entire signed Strata request/response* with
a key known only to the paired Surface and Subsurface. HTTPS separately
protects traffic to the relay. The direct LAN route remains preferred.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

PAIR_SCHEME = "aurora-relay"
ROOM_PATTERN = re.compile(r"^[A-Za-z0-9_-]{24,72}$")
HOME_FILE = "relay_home.json"
SURFACE_FILE = "relay_surface.json"
REQUEST_LIMIT = 9 * 1024 * 1024


def _directory(state_dir: Any) -> Path:
    from aurora_internal.dual_strata.strata_link import link_dir
    return link_dir(state_dir)


def _read(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(path: Path, value: dict) -> None:
    from aurora_internal.dual_strata.strata_link import _atomic_write_json
    _atomic_write_json(path, value)
    if os.name != "nt":
        os.chmod(path, 0o600)


def validate_origin(origin: str) -> str:
    """No credentials, query, fragment, plaintext, or user-controlled paths."""
    u = urllib.parse.urlsplit(str(origin).strip())
    if (u.scheme != "https" or not u.hostname or u.username is not None
            or u.password is not None or u.path not in ("", "/")
            or u.query or u.fragment):
        raise ValueError("Use a relay HTTPS origin, for example https://relay.example.org")
    try:
        port = u.port
    except ValueError as exc:
        raise ValueError("Invalid relay HTTPS port") from exc
    if port is not None and not (1 <= port <= 65535):
        raise ValueError("Invalid relay port")
    return f"https://{u.netloc.lower()}"


def _seal(secret: str, room: str, direction: str, payload: dict) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    key = hashlib.sha256(b"aurora-strata-relay-aes-gcm-v1\x00" + secret.encode()).digest()
    nonce = secrets.token_bytes(12)
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    ciphertext = AESGCM(key).encrypt(nonce, body, f"{room}:{direction}:v1".encode())
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def _unseal(secret: str, room: str, direction: str, encoded: str) -> dict:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    wire = base64.urlsafe_b64decode(encoded.encode("ascii"))
    if len(wire) < 29 or len(wire) > REQUEST_LIMIT:
        raise ValueError("Invalid encrypted relay packet length")
    key = hashlib.sha256(b"aurora-strata-relay-aes-gcm-v1\x00" + secret.encode()).digest()
    plain = AESGCM(key).decrypt(wire[:12], wire[12:], f"{room}:{direction}:v1".encode())
    obj = json.loads(plain.decode("utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("Invalid encrypted relay packet")
    return obj


def relay_pairing_line(state_dir: Any, origin: str, local_url: str = "") -> str:
    """Establish one relay identity, preserving it across restarts/repairs."""
    from aurora_internal.dual_strata.strata_link import ensure_secret
    origin = validate_origin(origin)
    path = _directory(state_dir) / HOME_FILE
    current = _read(path)
    if current.get("origin") != origin or not ROOM_PATTERN.fullmatch(str(current.get("room") or "")):
        current = {"origin": origin, "room": secrets.token_urlsafe(27),
                   "token": secrets.token_urlsafe(32)}
    current["local"] = local_url if local_url.startswith("http://") else ""
    _write(path, current)
    u = urllib.parse.urlsplit(origin)
    query = urllib.parse.urlencode({"local": current["local"]}) if current["local"] else ""
    return urllib.parse.urlunsplit((PAIR_SCHEME, u.netloc,
        "/" + current["room"], query,
        ensure_secret(state_dir) + ":" + current["token"]))


def parse_relay_pairing(text: str) -> tuple[str, str, dict]:
    u = urllib.parse.urlsplit(str(text).strip())
    if u.scheme != PAIR_SCHEME or not u.hostname or u.username or u.password:
        raise ValueError("Not an Aurora internet pairing link")
    room = u.path.lstrip("/")
    if not ROOM_PATTERN.fullmatch(room):
        raise ValueError("Invalid private relay room")
    try:
        secret, token = u.fragment.split(":", 1)
    except ValueError as exc:
        raise ValueError("Incomplete private pairing credentials") from exc
    if len(secret) < 32 or len(token) < 32 or not re.fullmatch(r"[A-Za-z0-9_-]+", token):
        raise ValueError("Invalid private pairing credentials")
    origin = validate_origin("https://" + u.netloc)
    params = urllib.parse.parse_qs(u.query)
    local = params.get("local", [""])[0]
    if local:
        local_parsed = urllib.parse.urlsplit(local)
        if (local_parsed.scheme != "http" or not local_parsed.hostname
                or local_parsed.username or local_parsed.password or local_parsed.path
                or local_parsed.query or local_parsed.fragment):
            raise ValueError("Invalid LAN fallback address")
    return origin, secret, {"origin": origin, "room": room, "token": token, "local": local}


def install_surface_relay(state_dir: Any, pairing: str) -> dict:
    from aurora_internal.dual_strata.strata_link import link_dir
    origin, secret, cfg = parse_relay_pairing(pairing)
    root = link_dir(state_dir)
    _write(root / SURFACE_FILE, cfg)
    (root / "endpoint.txt").write_text(origin, encoding="utf-8")
    (root / "secret.txt").write_text(secret, encoding="utf-8")
    (root / "claim_pending").write_text(str(time.time()), encoding="utf-8")
    return {"ok": True, "endpoint": origin, "route": "encrypted_relay_with_local_fallback"}


def _post(origin: str, path: str, body: dict, token: str, timeout: float,
          provisioning_key: str = "") -> dict:
    raw = json.dumps(body, separators=(",", ":")).encode()
    if len(raw) > REQUEST_LIMIT:
        raise ValueError("Relay request is too large")
    headers = {"Content-Type": "application/json",
               "Authorization": "Bearer " + token,
               "X-Aurora-Relay-Version": "1"}
    if provisioning_key:
        headers["X-Aurora-Relay-Registration"] = provisioning_key
    req = urllib.request.Request(origin + path, data=raw, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = response.read(REQUEST_LIMIT + 1)
        if len(data) > REQUEST_LIMIT:
            raise ValueError("Relay response is too large")
        result = json.loads(data.decode())
        if not isinstance(result, dict):
            raise ValueError("Invalid relay response")
        return result


class RelaySurfaceTransport:
    """Select trusted local transport first, then E2E-encrypted HTTPS relay."""
    def __init__(self, cfg: dict, secret: str, timeout_s: float = 8.0):
        self.cfg, self.secret, self.timeout_s = dict(cfg), secret, timeout_s
        self.last_route = "not_connected"
        self.local_retry_at = 0.0

    def __call__(self, body: bytes, headers: dict):
        local = str(self.cfg.get("local") or "")
        if local and time.monotonic() >= self.local_retry_at:
            from aurora_internal.dual_strata.strata_link import SYNC_PATH
            try:
                req = urllib.request.Request(local + SYNC_PATH, data=body,
                    headers={"Content-Type": "application/json", **headers}, method="POST")
                with urllib.request.urlopen(req, timeout=min(1.5, self.timeout_s)) as response:
                    self.last_route = "local"
                    return response.read(REQUEST_LIMIT), dict(response.headers.items())
            except (OSError, TimeoutError, ValueError):
                self.local_retry_at = time.monotonic() + 30.0
        packet = _seal(self.secret, self.cfg["room"], "request",
                       {"body": base64.b64encode(body).decode(), "headers": dict(headers)})
        result = _post(self.cfg["origin"], "/v1/exchange",
                       {"room": self.cfg["room"], "packet": packet},
                       self.cfg["token"], max(35, self.timeout_s))
        unpacked = _unseal(self.secret, self.cfg["room"], "response", result["packet"])
        self.last_route = "relay"
        if int(unpacked.get("status", 500)) != 200:
            raise ValueError(f"Home rejected signed exchange: {unpacked.get('status')}")
        return base64.b64decode(unpacked["body"]), unpacked["headers"]


class RelayHomePump:
    """One outbound worker on desktop. The relay sees ciphertext, not history."""
    def __init__(self, state_dir: Any, strata_server: Any):
        self.config = _read(_directory(state_dir) / HOME_FILE)
        self.secret = strata_server.secret
        self.server = strata_server
        self._stop = threading.Event()
        self._thread = None
        self.online = False
        self.last_error = ""
        self.last_connected_at = 0.0
        self.processed = 0

    def start(self):
        if not self.config.get("origin"):
            return False
        if self._thread and self._thread.is_alive():
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="aurora-encrypted-relay-home")
        self._thread.start()
        return True

    def _request(self, path: str, value: dict, timeout=35.0, provisioning=False):
        return _post(self.config["origin"], path, value, self.config["token"],
                     timeout, self.config.get("provisioning_key", "") if provisioning else "")

    def _run(self):
        room = self.config["room"]
        while not self._stop.is_set():
            try:
                self._request("/v1/register", {"room": room}, timeout=12, provisioning=True)
                while not self._stop.is_set():
                    reply = self._request("/v1/poll", {"room": room}, timeout=35)
                    self.online = True
                    self.last_connected_at = time.time()
                    if not reply.get("request_id"):
                        continue
                    request_id = str(reply["request_id"])
                    try:
                        decoded = _unseal(self.secret, room, "request", reply["packet"])
                        body = base64.b64decode(decoded["body"], validate=True)
                        headers = decoded["headers"]
                        status, response, extra = self.server.handle_http(body, headers)
                    except Exception:
                        # Invalid ciphertext must not invoke Aurora's cognitive
                        # mechanisms or reveal signatures to the relay.
                        status, response, extra = 400, b"{}", {}
                    answer = _seal(self.secret, room, "response",
                                  {"status": status, "body": base64.b64encode(response).decode(),
                                   "headers": extra})
                    self._request("/v1/reply", {"room": room, "request_id": request_id,
                                                "packet": answer}, timeout=12)
                    self.processed += 1
            except Exception as exc:
                self.online = False
                self.last_error = f"{type(exc).__name__}: {exc}"[:200]
                self._stop.wait(5)

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        self.online = False

    def status(self) -> dict:
        return {"configured": bool(self.config.get("origin")),
                "origin": self.config.get("origin", ""),
                "online": self.online, "last_connected_at": self.last_connected_at,
                "processed": self.processed, "error": self.last_error}
