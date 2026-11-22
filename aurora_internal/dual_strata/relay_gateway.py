"""Small, stateless-content Aurora relay gateway (deploy on a public HTTPS host).

Only opaque AES-GCM packets pass through. The gateway never receives Strata
secrets, plaintext, owner-console access, or Aurora state. Rooms and pending
requests are in RAM; reconnect after a restart re-registers the same room.

Public HTTPS terminates at a trusted reverse proxy. This backend MUST bind to
127.0.0.1 and MUST NOT be exposed directly on the public internet.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_BODY = 9 * 1024 * 1024
MAX_ROOMS = 256
MAX_QUEUE = 32
ROOM_TTL_S = 3600
POLL_S = 23
EXCHANGE_S = 30
ROOM_ID = re.compile(r"^[A-Za-z0-9_-]{24,72}$")
PACKET = re.compile(r"^[A-Za-z0-9_\-=]{40,}$")


class Pending:
    def __init__(self, packet):
        self.id = secrets.token_urlsafe(20)
        self.packet = packet
        self.answer = None


class Room:
    def __init__(self, token):
        self.token_digest = hashlib.sha256(token.encode()).digest()
        self.last_seen = time.monotonic()
        self.cv = threading.Condition()
        self.queue = collections.deque()
        self.pending = {}

    def authorized(self, token):
        return bool(token) and hmac.compare_digest(
            self.token_digest, hashlib.sha256(token.encode()).digest())


class RelayRegistry:
    """Bounded in-memory mailbox of encrypted messages, never histories."""
    def __init__(self, registration_key):
        if len(registration_key) < 24:
            raise ValueError("Set AURORA_RELAY_REGISTRATION_KEY to a random 24+ character secret.")
        self.key = registration_key
        self.lock = threading.Lock()
        self.rooms = {}

    def register(self, room_id, token, provisioning):
        if not ROOM_ID.fullmatch(room_id) or len(token) < 32:
            return 400, {"error": "invalid_room"}
        with self.lock:
            now = time.monotonic()
            if room_id not in self.rooms:
                # First registration is authorized by the gateway owner.
                if not hmac.compare_digest(provisioning, self.key):
                    return 403, {"error": "provisioning_required"}
                if len(self.rooms) >= MAX_ROOMS:
                    for key, room in list(self.rooms.items()):
                        if now - room.last_seen > ROOM_TTL_S and not room.pending:
                            self.rooms.pop(key, None)
                    if len(self.rooms) >= MAX_ROOMS:
                        return 503, {"error": "room_capacity"}
                self.rooms[room_id] = Room(token)
            room = self.rooms[room_id]
            if not room.authorized(token):
                return 403, {"error": "room_unauthorized"}
            room.last_seen = now
        return 200, {"ok": True}

    def locate(self, room_id, token):
        if not ROOM_ID.fullmatch(room_id):
            return None
        with self.lock:
            room = self.rooms.get(room_id)
            if not room or not room.authorized(token):
                return None
            room.last_seen = time.monotonic()
            return room

    @staticmethod
    def valid_packet(packet):
        return isinstance(packet, str) and len(packet) <= MAX_BODY and bool(PACKET.fullmatch(packet))

    def exchange(self, room, packet):
        if not self.valid_packet(packet):
            return 400, {"error": "invalid_packet"}
        item = Pending(packet)
        with room.cv:
            if len(room.pending) >= MAX_QUEUE:
                return 429, {"error": "room_busy"}
            room.pending[item.id] = item
            room.queue.append(item)
            room.cv.notify_all()
            deadline = time.monotonic() + EXCHANGE_S
            try:
                while item.answer is None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return 504, {"error": "home_not_reachable"}
                    room.cv.wait(timeout=remaining)
                return 200, {"packet": item.answer}
            finally:
                room.pending.pop(item.id, None)
                # Remove stale unclaimed requests; the home may already hold it.
                try:
                    room.queue.remove(item)
                except ValueError:
                    pass

    def poll(self, room):
        deadline = time.monotonic() + POLL_S
        with room.cv:
            while not room.queue:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return 200, {"request_id": None}
                room.cv.wait(timeout=remaining)
            request = room.queue.popleft()
            return 200, {"request_id": request.id, "packet": request.packet}

    def reply(self, room, request_id, packet):
        if not self.valid_packet(packet):
            return 400, {"error": "invalid_packet"}
        with room.cv:
            request = room.pending.get(request_id)
            if not request or request.answer is not None:
                return 409, {"error": "request_expired"}
            request.answer = packet
            room.cv.notify_all()
        return 200, {"ok": True}


def create_server(registration_key, host="127.0.0.1", port=8795):
    registry = RelayRegistry(registration_key)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            # Never log bearer credentials or opaque message contents.
            return

        def do_GET(self):
            if self.path == "/v1/health":
                self.reply(200, {"ok": True, "service": "aurora-opaque-relay"})
            else:
                self.reply(404, {"error": "not_found"})

        def reply(self, status, result):
            data = json.dumps(result, separators=(",", ":")).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if self.path not in ("/v1/register", "/v1/exchange", "/v1/poll", "/v1/reply"):
                self.reply(404, {"error": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > MAX_BODY:
                    self.reply(413, {"error": "body_size"})
                    return
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError()
            except (ValueError, UnicodeDecodeError):
                self.reply(400, {"error": "invalid_json"})
                return
            auth = self.headers.get("Authorization", "")
            token = auth[7:] if auth.startswith("Bearer ") else ""
            room_id = str(payload.get("room", ""))
            if self.path == "/v1/register":
                status, result = registry.register(room_id, token,
                    self.headers.get("X-Aurora-Relay-Registration", ""))
            else:
                room = registry.locate(room_id, token)
                if room is None:
                    status, result = 403, {"error": "room_unauthorized"}
                elif self.path == "/v1/exchange":
                    status, result = registry.exchange(room, payload.get("packet"))
                elif self.path == "/v1/poll":
                    status, result = registry.poll(room)
                else:
                    status, result = registry.reply(
                        room, str(payload.get("request_id", "")), payload.get("packet"))
            self.reply(status, result)

    class Server(ThreadingHTTPServer):
        daemon_threads = True
        allow_reuse_address = True

    server = Server((host, port), Handler)
    server.registry = registry
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description="Aurora opaque HTTPS relay backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8795)
    args = parser.parse_args(argv)
    if args.host not in ("127.0.0.1", "::1", "localhost"):
        raise SystemExit("Bind to loopback only and publish via an HTTPS reverse proxy.")
    server = create_server(os.environ.get("AURORA_RELAY_REGISTRATION_KEY", ""), args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
