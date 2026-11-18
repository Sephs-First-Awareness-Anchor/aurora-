#!/usr/bin/env python3
"""
strata_link.py -- the carrier between a Surface device and the Subsurface
device (FIX-A118).

Aurora's two strata already speak through channel files in ONE aurora_state
directory (surface_continuity_feed.json, subsurface_projection.json,
predictive_frame_queue.json, ...).  That contract is unchanged.  This module
only moves the contents of those same channels between TWO state directories
on two machines, and adds what plain files cannot give across a network:

  * a durable outbox on each side      -- nothing is lost while disconnected
  * sequence numbers + acknowledgments -- nothing is applied twice
  * a session epoch and one owner      -- only one active Surface at a time
  * signed requests and responses      -- a shared secret, no open door

It contains no cognition.  It never interprets a payload: every channel is
read and written through the module that already owns that channel's format.

DIRECTION OF CALLS
  The Surface always calls the Subsurface (a phone can reach a laptop through
  a private tunnel; the reverse is rarely true).  One request carries the
  Surface's pending uplink and its ack of the downlink; the response carries
  the Subsurface's ack and its pending downlink.

CHANNELS
  up    continuity        surface_continuity_feed  (event; every lived turn)
  up    sensory_snapshot  surface_sensory_snapshot (state; latest wins)
  down  projection        subsurface_projection    (state; latest wins)
  down  predictive_frame  PredictiveStager queue   (event)
  down  sensory_guidance  surface_sensory_guidance_queue (event)
  on request: whole-state seed / handoff (strata_state_transfer.py)
  Turn events and the presence frame stay on the Surface device on purpose:
  that loop is latency-critical and the Surface already runs it locally.

THE DOWNLINK IS OFF UNTIL ENABLED
  A projection is only meaningful when it comes from a Subsurface that has
  lived the same history as the Surface it colours.  Until the Subsurface
  device has been seeded with the Surface device's state, the downlink would
  carry a different history's intuition.  It stays off unless the file
  <state_dir>/strata_link/downlink_enabled exists on the Subsurface device.

OWNERSHIP
  The Subsurface holds the only ownership record.  The first Surface to sync
  becomes owner; another device becomes owner only by an explicit claim,
  which raises the epoch.  A Surface that is not the owner is told "standby":
  nothing it sends is applied or acknowledged, so its outbox simply waits.
  Moving the role WITH the state is the handoff in strata_state_transfer.py
  (FIX-A125): the active Surface checkpoints its state on the Subsurface
  device, and only a device presenting that checkpoint's token may claim.

FENCING AND LIVED MOMENTS (surface restructure, 2026-11-18)
  * The leaving device freezes on disk BEFORE it commits a checkpoint, and
    home refuses a handoff commit from a source that has not frozen.  A lost
    reply leaves the source frozen until home confirms there is no checkpoint
    (or the source cancels), so a failed move never revives two surfaces.
  * The client keeps its role, epoch and readiness on disk, so a device that
    was the holder when it lost the link stays present away from home, and a
    device that never was cannot start living on its own.
  * Every lived moment is numbered (device, epoch, seq) by stamp_lived_moment.
    A device that has since been superseded still delivers what it lived in
    its own epochs (up to where its freeze sealed them); home integrates it
    once, however late it comes.  Anything else waits on that device, kept.
  * The outbox never evicts a lived turn.  Under storage pressure new turns
    are kept in a compact form; if even that cannot be written the condition
    is raised and the turn stays in the continuity feed.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import shutil
import threading
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

LINK_VERSION = 1
DEFAULT_PORT = 8791
LINK_DIRNAME = "strata_link"
SYNC_PATH = "/strata/v1/sync"
HEALTH_PATH = "/strata/v1/health"

MAX_BODY_BYTES = 4 * 1024 * 1024
MAX_BATCH = 32
MAX_OUTBOX_RECORDS = 5000      # soft budget: past it, new events are kept compact
OUTBOX_MAX_BYTES = 32 * 1024 * 1024   # soft size budget for the outbox file
LOW_FREE_BYTES = 64 * 1024 * 1024     # device free space below which turns go compact
# Sensory detail a compact lived turn leaves out; identity, text and state stay.
COMPACT_DROPS = ("visual_description", "audio_description", "recent_speech")
MAX_CLOCK_SKEW_S = 300.0

_PROJECTION_FILENAME = "subsurface_projection.json"
HANDOFF_TTL_S = 3600.0          # a checkpoint waits this long for its claimant
MAX_SENSORY_SNAPSHOT_BYTES = 1_500_000


def publish_raw_input(state_dir, text):
    """Disposable pre-processing feed; it is never a completed lived event."""
    if not str(text).strip():
        return
    packet = {"input_id": uuid.uuid4().hex, "text": str(text)[:16000], "at": time.time(),
              "expires_at": time.time() + 30, "basis": "unprocessed_input"}
    _atomic_write_json(link_dir(state_dir) / "raw_input.json", packet)
    if _CLIENT is not None and _CLIENT.state_dir.resolve() == Path(state_dir).resolve():
        _CLIENT.outbox.append("raw_input", "state", packet)


def require_surface_admission(systems):
    """Fence actual conscious turns, not just their outbound transport."""
    source = str(systems.get("_turn_source_label") or "")
    root = Path(str(systems.get("state_dir") or "aurora_state"))
    if (link_dir(root) / "surface_frozen").exists():
        raise RuntimeError("surface_frozen_for_handoff")
    server = systems.get("_strata_link_server")
    sid = systems.get("_desktop_surface_id")
    if server is not None and sid and not server.surface_ready(sid):
        raise RuntimeError("surface_standby")
    client = systems.get("strata_link")
    if client is not None and (client.role != "active" or not client.surface_ready):
        raise RuntimeError("surface_standby_or_not_restored")


# ---------------------------------------------------------------------------
# Small file helpers
# ---------------------------------------------------------------------------

def link_dir(state_dir: Any) -> Path:
    root = Path(str(state_dir)) / LINK_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _atomic_write_json(path: Path, payload: Any) -> None:
    from aurora_persistence_utils import atomic_write_json
    if not atomic_write_json(path, payload, default=str):
        raise OSError(f"could not persist {path.name}")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip() if path.exists() else ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Signing
# ---------------------------------------------------------------------------

def sign(secret: str, timestamp: str, body: bytes) -> str:
    return hmac.new(str(secret).encode("utf-8"),
                    str(timestamp).encode("utf-8") + b"." + body,
                    hashlib.sha256).hexdigest()


def verify(secret: str, timestamp: str, body: bytes, signature: str,
           *, now: Optional[float] = None) -> bool:
    if not secret or not timestamp or not signature:
        return False
    try:
        skew = abs((time.time() if now is None else now) - float(timestamp))
    except Exception:
        return False
    if skew > MAX_CLOCK_SKEW_S:
        return False
    return hmac.compare_digest(sign(secret, timestamp, body), str(signature))


# ---------------------------------------------------------------------------
# Durable outbox
# ---------------------------------------------------------------------------

class DurableOutbox:
    """Records waiting to cross the link, kept on disk until acknowledged.

    kind "event": every record is kept, in order, until acknowledged.  A lived
                  event is never evicted, however long the link is down.
    kind "state": only the newest record of a channel is kept (latest wins),
                  so an unchanged or superseded state is never sent twice.
    The outbox has a soft budget (record count, file size, and the device's
    free space).  Past it, new events are stored compact (COMPACT_DROPS left
    out) and counted; a write that still fails raises OSError to the caller,
    which keeps the event where it already was.  overflow_dropped is kept for
    older readers and stays 0: nothing is dropped any more.
    """

    def __init__(self, path: Path, *, max_records: int = MAX_OUTBOX_RECORDS,
                 max_bytes: int = OUTBOX_MAX_BYTES, low_free_bytes: int = LOW_FREE_BYTES,
                 free_space: Optional[Callable[[Path], int]] = None) -> None:
        self.path = Path(path)
        self.max_records = int(max_records)
        self.max_bytes = int(max_bytes)
        self.low_free_bytes = int(low_free_bytes)
        self._free_space = free_space or _free_bytes
        self._lock = threading.RLock()
        self.last_write_error = ""

    def _load(self) -> Dict[str, Any]:
        data = _read_json(self.path, {})
        if not isinstance(data, dict):
            data = {}
        records = [r for r in (data.get("records") or []) if isinstance(r, dict)]
        highest = max([int(r.get("seq", 0) or 0) for r in records] or [0])
        return {
            "next_seq": max(int(data.get("next_seq", 1) or 1), highest + 1),
            "overflow_dropped": int(data.get("overflow_dropped", 0) or 0),
            "compacted": int(data.get("compacted", 0) or 0),
            "seen": [str(s) for s in (data.get("seen") or [])][-400:],
            "records": records,
        }

    def pressed(self, data: Optional[Dict[str, Any]] = None) -> bool:
        """True when the outbox is past its budget or the device is short of space."""
        data = data if data is not None else self._load()
        if len(data["records"]) >= self.max_records:
            return True
        try:
            if self.path.exists() and self.path.stat().st_size >= self.max_bytes:
                return True
        except OSError:
            pass
        try:
            return int(self._free_space(self.path.parent)) < self.low_free_bytes
        except Exception:
            return False

    def append(self, channel: str, kind: str, payload: Any, *, dedupe_id: str = "") -> int:
        """Returns the record's seq, or 0 when dedupe_id was already queued.
        Raises OSError when the record cannot be written at all."""
        with self._lock:
            data = self._load()
            if dedupe_id:
                if dedupe_id in data["seen"]:
                    return 0
            if kind == "state":
                data["records"] = [r for r in data["records"] if r.get("channel") != channel]
            compact = False
            if kind == "event" and isinstance(payload, dict) and self.pressed(data):
                payload = {k: v for k, v in payload.items() if k not in COMPACT_DROPS}
                payload["compact"] = True
                compact = True
            seq = data["next_seq"]
            data["next_seq"] = seq + 1
            data["records"].append({"seq": seq, "channel": str(channel), "kind": str(kind),
                                    "at": time.time(), "payload": payload})
            if dedupe_id:
                data["seen"] = (data["seen"] + [dedupe_id])[-400:]
            if compact:
                data["compacted"] += 1
            try:
                _atomic_write_json(self.path, data)
            except OSError as exc:
                self.last_write_error = f"{type(exc).__name__}: {exc}"[:200]
                raise
            self.last_write_error = ""
            return seq

    def pending(self, limit: int = MAX_BATCH) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._load()["records"][:max(1, int(limit))])

    def ack(self, seq: int) -> int:
        """Drop every record with seq <= the acknowledged seq."""
        with self._lock:
            data = self._load()
            before = len(data["records"])
            data["records"] = [r for r in data["records"] if int(r.get("seq", 0) or 0) > int(seq or 0)]
            dropped = before - len(data["records"])
            if dropped:
                _atomic_write_json(self.path, data)
            return dropped

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            data = self._load()
            out: Dict[str, Any] = {"pending": len(data["records"]),
                                   "next_seq": data["next_seq"],
                                   "overflow_dropped": data["overflow_dropped"]}
            pressed = self.pressed(data)
            if data["compacted"]:
                out["compacted"] = data["compacted"]
            if pressed or self.last_write_error:
                out["condition"] = "storage_exhausted" if self.last_write_error else "storage_low"
            if self.last_write_error:
                out["last_write_error"] = self.last_write_error
            return out


def _free_bytes(path: Path) -> int:
    probe = Path(path)
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return int(shutil.disk_usage(str(probe)).free)


# ---------------------------------------------------------------------------
# Lived-moment numbering (device, epoch, seq)
# ---------------------------------------------------------------------------

_STAMP_LOCK = threading.RLock()


def current_epoch(state_dir: Any, surface_id: str = "") -> int:
    """The epoch this device last confirmed as holder.  A paired device reads
    its own client state; the Subsurface device's own surface reads the
    server record when it is the owner."""
    root = link_dir(state_dir)
    client = _read_json(root / "client_state.json", {})
    if isinstance(client, dict) and client.get("epoch") is not None:
        return int(client.get("epoch") or 0)
    server = _read_json(root / "server_state.json", {})
    if isinstance(server, dict) and (not surface_id or server.get("owner") == surface_id):
        return int(server.get("epoch", 0) or 0)
    return 0


def lived_high_water(state_dir: Any) -> int:
    """The last lived seq this device numbered in its current epoch."""
    with _STAMP_LOCK:
        surface_id = surface_identity(state_dir)
        numbering = _read_json(link_dir(state_dir) / "lived_numbering.json", {})
        if not isinstance(numbering, dict) or numbering.get("surface_id") != surface_id \
                or int(numbering.get("epoch", -1)) != current_epoch(state_dir, surface_id):
            return 0
        return int(numbering.get("seq", 0) or 0)


def stamp_lived_moment(state_dir: Any) -> Dict[str, Any]:
    """Number one lived moment on this device: {surface_id, epoch, seq}.

    The sequence restarts at 1 in each epoch, and is persisted before it is
    returned, so a number is never reused after a crash."""
    with _STAMP_LOCK:
        root = link_dir(state_dir)
        surface_id = surface_identity(state_dir)
        epoch = current_epoch(state_dir, surface_id)
        path = root / "lived_numbering.json"
        numbering = _read_json(path, {})
        if not isinstance(numbering, dict) or numbering.get("surface_id") != surface_id \
                or int(numbering.get("epoch", -1)) != epoch:
            numbering = {"surface_id": surface_id, "epoch": epoch, "seq": 0}
        numbering["seq"] = int(numbering.get("seq", 0) or 0) + 1
        _atomic_write_json(path, numbering)
        return {"surface_id": surface_id, "epoch": epoch, "seq": numbering["seq"]}


# ---------------------------------------------------------------------------
# Channel adapters -- each goes through the module that owns the format
# ---------------------------------------------------------------------------

def collect_surface_uplink(state_dir: Any, outbox: DurableOutbox) -> int:
    """Surface side: move lived continuity packets into the durable outbox.

    Copy first, consume second: a crash between the two repeats a packet
    (de-duplicated by packet_id) instead of losing it.
    """
    from aurora_internal.dual_strata.surface_continuity_feed import (
        peek_continuity_packets, read_and_clear_continuity_packets)
    packets = peek_continuity_packets(state_dir)
    queued = 0
    for packet in packets:
        packet_id = str(packet.get("packet_id") or "")
        if not packet_id:
            continue
        clean = {k: v for k, v in packet.items() if k not in ("consumed", "consumed_at")}
        try:
            if outbox.append("continuity", "event", clean, dedupe_id=packet_id):
                queued += 1
        except OSError:
            # The outbox could not take it: the packets stay unconsumed in the
            # feed, where they already are, and the condition shows in stats.
            return queued
    if packets:
        read_and_clear_continuity_packets(state_dir)
    queued += _collect_sensory_snapshot(state_dir, outbox)
    return queued


def _collect_sensory_snapshot(state_dir: Any, outbox: DurableOutbox) -> int:
    """Surface side: the live sensory snapshot goes up when its content
    changed (latest wins -- a stale frame is never worth sending twice).  It
    is read and re-written through sensory_snapshot_channel's own path, so the
    Subsurface reads it exactly as it would on one device."""
    try:
        from aurora_internal.dual_strata.sensory_snapshot_channel import snapshot_path
        path = snapshot_path(state_dir)
        if not path.exists():
            return 0
        raw = path.read_bytes()
        if not raw or len(raw) > MAX_SENSORY_SNAPSHOT_BYTES:
            return 0
        memo_path = link_dir(state_dir) / "uplink_memo.json"
        memo = _read_json(memo_path, {})
        memo = memo if isinstance(memo, dict) else {}
        digest = hashlib.sha256(raw).hexdigest()
        if digest == memo.get("sensory_sha"):
            return 0
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            return 0
        outbox.append("sensory_snapshot", "state", payload)
        memo["sensory_sha"] = digest
        _atomic_write_json(memo_path, memo)
        return 1
    except Exception:
        return 0


def apply_uplink_record(state_dir: Any, record: Mapping[str, Any], *, late: bool = False) -> str:
    """Subsurface side.  Returns "applied", "duplicate" or "unknown_channel".
    ``late`` marks a continuity packet delivered by a device that has since
    been superseded; it is integrated like any other, tagged as late."""
    channel = str(record.get("channel") or "")
    if channel == "raw_input" and isinstance(record.get("payload"), dict):
        payload = record["payload"]
        if float(payload.get("expires_at", 0)) >= time.time():
            _atomic_write_json(link_dir(state_dir) / "raw_input.json", payload)
        return "applied"
    if channel == "continuity":
        from aurora_internal.dual_strata.surface_continuity_feed import deposit_continuity_packet
        return "applied" if deposit_continuity_packet(state_dir, dict(record.get("payload") or {}),
                                                      late=late) else "duplicate"
    if channel == "sensory_snapshot" and isinstance(record.get("payload"), dict):
        from aurora_internal.dual_strata.sensory_snapshot_channel import snapshot_path
        path = snapshot_path(state_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(path, record["payload"])
        return "applied"
    return "unknown_channel"


def collect_subsurface_downlink(state_dir: Any, outbox: DurableOutbox, memo: Dict[str, Any]) -> int:
    """Subsurface side: stage what the active Surface is likely to need.

    The projection is sent only when its content changed.  Predictive frames
    are popped from the same queue a local Surface would pop them from.
    """
    queued = 0
    projection_path = Path(str(state_dir)) / _PROJECTION_FILENAME
    try:
        if projection_path.exists():
            raw = projection_path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            if digest != memo.get("projection_sha"):
                payload = json.loads(raw.decode("utf-8"))
                if isinstance(payload, dict):
                    outbox.append("projection", "state", payload)
                    memo["projection_sha"] = digest
                    queued += 1
    except Exception:
        pass
    try:
        from aurora_internal.dual_strata.sensory_snapshot_channel import read_surface_guidance_queue
        sent = [str(x) for x in (memo.get("guidance_sent") or [])]
        for event in read_surface_guidance_queue(state_dir):
            event_id = str((event or {}).get("event_id") or "")
            if event_id and event_id not in sent:
                outbox.append("sensory_guidance", "event", dict(event))
                sent.append(event_id)
                queued += 1
        memo["guidance_sent"] = sent[-200:]
    except Exception:
        pass
    try:
        from aurora_internal.dual_strata.predictive_stager import PredictiveStager
        queued += PredictiveStager.relay_to(outbox, state_dir)
    except Exception:
        pass
    return queued


def apply_downlink_record(state_dir: Any, record: Mapping[str, Any]) -> str:
    """Surface side.  Returns "applied" or "unknown_channel"."""
    channel = str(record.get("channel") or "")
    payload = record.get("payload")
    if channel == "projection" and isinstance(payload, dict):
        root = Path(str(state_dir))
        root.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(root / _PROJECTION_FILENAME, payload)
        return "applied"
    if channel == "predictive_frame" and isinstance(payload, dict):
        from aurora_internal.dual_strata.predictive_stager import PredictiveStager
        PredictiveStager.push_staged_frame(payload, state_dir=state_dir)
        return "applied"
    if channel == "sensory_guidance" and isinstance(payload, dict):
        from aurora_internal.dual_strata.sensory_snapshot_channel import (
            append_surface_guidance, read_surface_guidance_queue)
        event_id = str(payload.get("event_id") or "")
        if event_id and any(str(e.get("event_id") or "") == event_id
                            for e in read_surface_guidance_queue(state_dir)):
            return "applied"  # already queued here; a resend changes nothing
        append_surface_guidance(state_dir, payload)
        return "applied"
    return "unknown_channel"


# ---------------------------------------------------------------------------
# Subsurface side: the server
# ---------------------------------------------------------------------------

def ensure_secret(state_dir: Any) -> str:
    path = link_dir(state_dir) / "secret.txt"
    secret = _read_text(path)
    if not secret:
        secret = secrets.token_urlsafe(32)
        path.write_text(secret, encoding="utf-8")
    return secret


def pairing_line(state_dir: Any, host: str, port: int = DEFAULT_PORT) -> str:
    """The one line a Surface device needs: http://host:port#secret"""
    return f"http://{host}:{int(port)}#{ensure_secret(state_dir)}"


class StrataLinkServer:
    """Runs inside the Subsurface process (aurora_daemon), so it shares the
    continuity feed's in-process lock with the Subsurface loop that reads it."""

    def __init__(self, state_dir: Any, *, host: str = "0.0.0.0", port: int = DEFAULT_PORT,
                 state_install_allowed: bool = True) -> None:
        self.state_dir = Path(str(state_dir))
        self.host = str(host)
        self.port = int(port)
        self.state_install_allowed = state_install_allowed
        self.secret = ensure_secret(self.state_dir)
        self._state_path = link_dir(self.state_dir) / "server_state.json"
        self.outbox = DurableOutbox(link_dir(self.state_dir) / "down_outbox.json")
        self._lock = threading.RLock()
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self.counters: Dict[str, int] = {"syncs": 0, "applied": 0, "duplicates": 0,
                                         "unknown_channel": 0, "apply_errors": 0,
                                         "rejected_signature": 0, "standby_syncs": 0,
                                         "late_applied": 0}
        self.last_error = ""

    # -- state --------------------------------------------------------------

    def _load_state(self) -> Dict[str, Any]:
        data = _read_json(self._state_path, {})
        if not isinstance(data, dict):
            data = {}
        return {"instance": str(data.get("instance") or uuid.uuid4().hex[:12]),
                "epoch": int(data.get("epoch", 0) or 0),
                "owner": str(data.get("owner") or ""),
                "claimed_at": float(data.get("claimed_at", 0.0) or 0.0),
                "applied": {str(k): int(v or 0) for k, v in dict(data.get("applied") or {}).items()},
                "last_seen": {str(k): float(v or 0.0) for k, v in dict(data.get("last_seen") or {}).items()},
                "memo": dict(data.get("memo") or {}),
                "handoff": dict(data["handoff"]) if isinstance(data.get("handoff"), dict) else None,
                "migrations": [m for m in (data.get("migrations") or []) if isinstance(m, dict)][-20:],
                "owner_epochs": self._owner_epochs(data),
                # epoch -> the last lived seq its holder had when it froze
                "sealed": {str(k): int(v or 0) for k, v in dict(data.get("sealed") or {}).items()},
                # surface_id -> its first-pairing migration (strata_migration)
                "first_pairing": {str(k): dict(v) for k, v in dict(data.get("first_pairing") or {}).items()
                                  if isinstance(v, dict)}}

    @staticmethod
    def _owner_epochs(data: Mapping[str, Any]) -> Dict[str, str]:
        """Which device held each epoch, so what a superseded device lived in
        its own epochs can still be told apart from anything else."""
        record = {str(k): str(v) for k, v in dict(data.get("owner_epochs") or {}).items() if v}
        owner, epoch = str(data.get("owner") or ""), int(data.get("epoch", 0) or 0)
        if owner and epoch and str(epoch) not in record:
            record[str(epoch)] = owner
        if len(record) > 500:
            record = dict(sorted(record.items(), key=lambda kv: int(kv[0]))[-500:])
        return record

    def _take_ownership(self, state: Dict[str, Any], surface_id: str, now: float) -> None:
        state["epoch"] += 1
        state["owner"] = surface_id
        state["claimed_at"] = now
        state["owner_epochs"][str(state["epoch"])] = surface_id
        if (state["first_pairing"].get(surface_id) or {}).get("tail_open"):
            # From here its records are the holder's and are applied directly.
            state["first_pairing"][surface_id]["tail_open"] = False
        # Staged downlink was prepared for the previous owner's numbering; the
        # new owner starts its own.
        self.outbox.ack(10 ** 18)
        state["memo"] = {}

    def _accept_from_superseded(self, state: Dict[str, Any], surface_id: str,
                                records: List[Dict[str, Any]], up_ack: int) -> int:
        """A device that is not the holder may still be carrying what it lived
        while it was.  Continuity it lived in an epoch it held, up to where
        that epoch was sealed by its freeze, is integrated (once, tagged
        late).  Anything else waits on the device, unacknowledged, exactly as
        a standby device's records always have: kept, never dropped."""
        owned = {int(e) for e, sid in state["owner_epochs"].items() if sid == surface_id}
        tail = state["first_pairing"].get(surface_id) or {}
        tail_from = int(tail.get("lived_seq", 0) or 0) if tail.get("tail_open") else None
        if not owned and tail_from is None:
            return up_ack
        for record in sorted(records, key=lambda r: int(r.get("seq", 0) or 0)):
            seq = int(record.get("seq", 0) or 0)
            if seq <= up_ack:
                self.counters["duplicates"] += 1
                continue
            payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
            if record.get("channel") != "continuity" or record.get("kind") != "event":
                break
            if str(payload.get("surface_id") or surface_id) != surface_id:
                break
            lived_seq = int(payload.get("seq", 0) or 0)
            if tail_from is not None and lived_seq and lived_seq <= tail_from:
                # Lived before its first-pairing snapshot: already home in the
                # migrated stores.
                self.counters["duplicates"] += 1
                up_ack = seq
                state["applied"][surface_id] = seq
                _atomic_write_json(self._state_path, state)
                continue
            if tail_from is not None and lived_seq > tail_from:
                pass  # lived as a whole mind while its migration waited: integrate once
            elif payload.get("epoch") is not None:
                lived_epoch = int(payload.get("epoch") or 0)
                sealed = state["sealed"].get(str(lived_epoch))
                if lived_epoch not in owned or (sealed is not None and lived_seq > int(sealed)):
                    break
            elif not owned:
                break
            try:
                outcome = apply_uplink_record(self.state_dir, record, late=True)
            except Exception as exc:
                self.counters["apply_errors"] += 1
                self.last_error = f"{type(exc).__name__}: {exc}"[:200]
                break
            self.counters["late_applied" if outcome == "applied" else "duplicates"] += 1
            up_ack = seq
            state["applied"][surface_id] = seq
            _atomic_write_json(self._state_path, state)
        return up_ack

    def downlink_enabled(self) -> bool:
        return (link_dir(self.state_dir) / "downlink_enabled").exists()

    # -- the exchange (transport-free, so it is testable directly) -----------

    def handle_sync(self, request: Mapping[str, Any]) -> Dict[str, Any]:
        surface_id = str(request.get("surface_id") or "")[:64]
        if not surface_id:
            return {"v": LINK_VERSION, "error": "surface_id required"}
        with self._lock:
            state = self._load_state()
            now = time.time()
            self.counters["syncs"] += 1
            state["last_seen"][surface_id] = now
            handoff = state.get("handoff")
            expired = bool(handoff and now - float(handoff.get("at", 0.0) or 0.0) > HANDOFF_TTL_S)
            wants_claim = bool(request.get("claim")) and state["owner"] != surface_id
            refused = ""
            if wants_claim and state["owner"] and not handoff:
                wants_claim, refused = False, "checkpoint_handoff_required"
            if wants_claim and handoff and state["owner"]:
                if expired:
                    wants_claim, refused = False, "handoff_expired; cancel from the source and prepare again"
                elif handoff.get("claimed_by") not in (None, surface_id):
                    wants_claim, refused = False, "handoff_already_claimed"
                elif not hmac.compare_digest(str(request.get("handoff_token") or ""),
                                           str(handoff.get("token") or "")):
                    # A checkpoint is waiting for its claimant: a stateless
                    # claim must not take the Surface role out from under it.
                    wants_claim, refused = False, "handoff_pending"
                else:
                    handoff["claimed_by"] = surface_id
            if not state["owner"] or wants_claim:
                self._take_ownership(state, surface_id, now)
            active = state["owner"] == surface_id
            # Downlink numbering belongs to one (server instance, epoch).  A
            # Surface still holding an older key must not acknowledge by it.
            link_key = f"{state['instance']}:{state['epoch']}"
            up_ack = state["applied"].get(surface_id, 0)
            down: List[Dict[str, Any]] = []
            state_result: Optional[Dict[str, Any]] = None
            if isinstance(request.get("state_op"), dict):
                state_result = self._state_op(state, surface_id, active, dict(request["state_op"]), now)
                active = state["owner"] == surface_id
                link_key = f"{state['instance']}:{state['epoch']}"
            if active:
                records = [r for r in (request.get("up") or []) if isinstance(r, dict)]
                for record in sorted(records, key=lambda r: int(r.get("seq", 0) or 0)):
                    seq = int(record.get("seq", 0) or 0)
                    if seq <= up_ack:
                        self.counters["duplicates"] += 1
                        continue
                    try:
                        outcome = apply_uplink_record(self.state_dir, record)
                    except Exception as exc:
                        # Never acknowledge past a record that failed to apply.
                        self.counters["apply_errors"] += 1
                        self.last_error = f"{type(exc).__name__}: {exc}"[:200]
                        break
                    key = {"applied": "applied", "duplicate": "duplicates"}.get(outcome, "unknown_channel")
                    self.counters[key] += 1
                    up_ack = seq
                    state["applied"][surface_id] = seq
                    _atomic_write_json(self._state_path, state)
                if str(request.get("link_key") or "") == link_key:
                    self.outbox.ack(int(request.get("down_ack", 0) or 0))
                if self.downlink_enabled() and not state.get("handoff"):
                    collect_subsurface_downlink(self.state_dir, self.outbox, state["memo"])
                    down = self.outbox.pending(MAX_BATCH)
            else:
                self.counters["standby_syncs"] += 1
                up_ack = self._accept_from_superseded(
                    state, surface_id, [r for r in (request.get("up") or []) if isinstance(r, dict)], up_ack)
            _atomic_write_json(self._state_path, state)
            response = {"v": LINK_VERSION, "epoch": state["epoch"], "owner": state["owner"],
                        "role": "active" if active else "standby", "link_key": link_key,
                        "up_ack": up_ack, "down": down,
                        "downlink_enabled": self.downlink_enabled()}
            response["surface_ready"] = active and not bool(state.get("handoff"))
            # Lets a source whose commit reply was lost learn whether the
            # checkpoint landed (it stays frozen) or not (it may thaw).
            response["handoff_from"] = str((state.get("handoff") or {}).get("from") or "")
            if refused:
                response["error"] = refused
            if state_result is not None:
                response["state_result"] = state_result
            return response

    # -- state transfer (seed and handoff) ----------------------------------------

    def _staging_root(self) -> Path:
        return link_dir(self.state_dir) / "staging"

    def _handoff_root(self) -> Path:
        return link_dir(self.state_dir) / "handoff"

    def _drop_handoff(self) -> None:
        shutil.rmtree(self._handoff_root(), ignore_errors=True)

    def _state_op(self, state: Dict[str, Any], surface_id: str, active: bool,
                  op: Dict[str, Any], now: float) -> Dict[str, Any]:
        """One step of a seed or handoff.  Only the active Surface may seed or
        checkpoint; only the device that claimed with the checkpoint's token
        may pull it.  Every failure is reported, none is swallowed."""
        from aurora_internal.dual_strata import strata_state_transfer as st
        name = str(op.get("op") or "")
        try:
            if name == "handoff_cancel":
                pending = state.get("handoff")
                if not pending or pending.get("from") != surface_id or not hmac.compare_digest(
                        str(op.get("token") or ""), str(pending.get("token") or "")):
                    return {"ok": False, "error": "source_and_checkpoint_token_required"}
                state["handoff"] = None
                self._take_ownership(state, surface_id, now)
                self._drop_handoff()
                return {"ok": True, "cancelled": True}
            if name == "migration_status":
                from aurora_internal.dual_strata import strata_migration as sm
                status = sm.status_for(self.state_dir, surface_id)
                record = state["first_pairing"].get(surface_id)
                if status.get("status") == "applied" and record and record.get("status") != "applied":
                    record.update(status="applied", tail_open=True,
                                  lived_seq=int((status.get("receipt") or {}).get("lived_seq", 0) or 0))
                return {"ok": True, **status}
            tid_hint = str(op.get("transfer_id") or "")
            migrating = (name == "offer" and str(op.get("purpose") or "") == "migrate") or \
                (name in ("chunk", "commit") and tid_hint.startswith("migrate-"))
            if not active and not migrating:
                return {"ok": False, "error": "not_active_surface"}
            if name in ("offer", "chunk", "commit"):
                tid = "".join(c for c in str(op.get("transfer_id") or "") if c.isalnum() or c in "-_")[:80]
                if not tid:
                    return {"ok": False, "error": "transfer_id required"}
                transfer = st.IncomingTransfer(self._staging_root(), tid)
                if name == "offer":
                    purpose = str(op.get("purpose") or "")
                    if purpose not in ("seed", "handoff", "migrate"):
                        return {"ok": False, "error": "purpose must be seed, handoff or migrate"}
                    if purpose == "migrate" and not tid.startswith("migrate-"):
                        return {"ok": False, "error": "a migration's transfer id starts with migrate-"}
                    manifest = st.validate_manifest(op.get("manifest"))
                    digest = st.manifest_digest(manifest)
                    if transfer.exists() and st.manifest_digest(transfer.raw_manifest()) != digest:
                        transfer.discard()
                    if not transfer.exists():
                        transfer.begin(manifest, meta={"purpose": purpose, "from": surface_id,
                                                       "epoch": state["epoch"], "at": now,
                                                       "digest": digest,
                                                       "lived_seq": int(op.get("lived_seq", 0) or 0)})
                    complete = set(transfer.complete_paths())
                    if purpose == "seed":
                        for row in manifest:
                            if row["path"] in complete:
                                continue
                            target = st.safe_join(self.state_dir, row["path"])
                            if target.is_file() and target.stat().st_size == row["size"] \
                                    and st.file_sha256(target) == row["sha256"]:
                                transfer.accept_existing(row["path"], target)
                                complete.add(row["path"])
                    return {"ok": True, "have": sorted(complete), "digest": digest}
                if not transfer.exists():
                    return {"ok": False, "error": "unknown_transfer"}
                if migrating and (transfer.meta().get("purpose") != "migrate"
                                  or transfer.meta().get("from") != surface_id):
                    return {"ok": False, "error": "not_this_devices_migration"}
                if name == "chunk":
                    return transfer.put_chunk(str(op.get("path") or ""), int(op.get("offset", 0) or 0),
                                              str(op.get("data") or ""))
                bad = transfer.verify_all()
                if bad:
                    return {"ok": False, "error": "incomplete", "bad": bad[:20], "bad_count": len(bad)}
                meta, manifest = transfer.meta(), transfer.raw_manifest()
                if meta.get("purpose") == "migrate":
                    # Staged only: home's live state is untouched until Sir's
                    # choices are made and it is applied cold.
                    from aurora_internal.dual_strata import strata_migration as sm
                    staged = sm.stage_received(self.state_dir, transfer.root, tid, meta=meta, manifest=manifest)
                    state["first_pairing"][surface_id] = {"migration_id": tid, "status": "staged", "at": now,
                                                          "lived_seq": int(meta.get("lived_seq", 0) or 0),
                                                          "tail_open": False}
                    return {"ok": True, "purpose": "migrate", **staged}
                if meta.get("purpose") == "handoff" and not op.get("source_frozen"):
                    # One holder at a time: the source must already be fenced
                    # on its own disk before home holds its checkpoint.
                    return {"ok": False, "error": "source_not_frozen"}
                if meta.get("purpose") == "handoff":
                    # Seal the epoch: what the source lived up to its freeze
                    # is hers wherever it arrives; nothing after it is.
                    state["sealed"][str(state["epoch"])] = int(op.get("lived_seq", 0) or 0)
                if meta.get("purpose") == "seed":
                    if not self.state_install_allowed:
                        return {"ok": False, "error": "cold_seed_required; stop the resident before installing state"}
                    report = st.install_verified(transfer.files, manifest, self.state_dir,
                                                 link_dir(self.state_dir) / "backup" / tid)
                    seeded = {"at": now, "from": surface_id, "epoch": state["epoch"],
                              "transfer_id": tid, "digest": meta.get("digest"),
                              "files": len(manifest), "restart_required": True, **report}
                    _atomic_write_json(link_dir(self.state_dir) / "seeded.json", seeded)
                    # The stated condition for turning the downlink on (module
                    # docstring) is exactly this: the Subsurface has been
                    # seeded, and every file was verified against its hash.
                    (link_dir(self.state_dir) / "downlink_enabled").write_text(
                        f"seeded {tid} at {now}", encoding="utf-8")
                    transfer.discard()
                    return {"ok": True, "purpose": "seed", "restart_required": True, **report}
                self._drop_handoff()
                self._handoff_root().mkdir(parents=True, exist_ok=True)
                os.replace(str(transfer.root), str(self._handoff_root() / "current"))
                token = secrets.token_urlsafe(18)
                state["handoff"] = {"token": token, "from": surface_id, "epoch": state["epoch"],
                                    "at": now, "digest": meta.get("digest"), "tid": tid,
                                    "files": len(manifest)}
                return {"ok": True, "purpose": "handoff", "token": token,
                        "digest": meta.get("digest"), "files": len(manifest),
                        "expires_in_s": HANDOFF_TTL_S}
            if name == "verify":
                manifest = st.validate_manifest(op.get("manifest"))
                return {"ok": True, **st.compare_to_manifest(self.state_dir, manifest)}
            handoff = state.get("handoff")
            if name in ("pull_offer", "pull_chunk", "handoff_complete"):
                if not handoff or handoff.get("claimed_by") != surface_id:
                    return {"ok": False, "error": "no_handoff_for_this_surface"}
                current = st.IncomingTransfer(self._handoff_root(), "current")
                if name == "pull_offer":
                    return {"ok": True, "manifest": current.raw_manifest(),
                            "digest": handoff.get("digest"), "epoch": state["epoch"]}
                if name == "pull_chunk":
                    return {"ok": True, **st.read_chunk(current.files, str(op.get("path") or ""),
                                                         int(op.get("offset", 0) or 0),
                                                         int(op.get("length", st.CHUNK_BYTES) or st.CHUNK_BYTES))}
                if str(op.get("digest") or "") != str(handoff.get("digest") or ""):
                    return {"ok": False, "error": "digest_mismatch"}
                state["migrations"] = (state.get("migrations") or []) + [{
                    "from": handoff.get("from"), "to": surface_id, "epoch": state["epoch"],
                    "at": now, "digest": handoff.get("digest"), "files": handoff.get("files")}]
                state["handoff"] = None
                self._drop_handoff()
                return {"ok": True, "completed": True}
            return {"ok": False, "error": f"unknown_state_op: {name}"}
        except st.TransferError as exc:
            self.last_error = f"state_op {name}: {exc}"[:200]
            return {"ok": False, "error": str(exc)[:300]}
        except Exception as exc:
            self.last_error = f"state_op {name}: {type(exc).__name__}: {exc}"[:200]
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:300]}

    # -- HTTP ----------------------------------------------------------------

    def handle_http(self, body: bytes, headers: Mapping[str, str]) -> Tuple[int, bytes, Dict[str, str]]:
        timestamp = str(headers.get("X-Aurora-Ts") or "")
        if not verify(self.secret, timestamp, body, str(headers.get("X-Aurora-Sig") or "")):
            self.counters["rejected_signature"] += 1
            return 401, b'{"error":"signature"}', {}
        try:
            request = json.loads(body.decode("utf-8"))
            if not isinstance(request, dict):
                raise ValueError("request must be an object")
        except Exception:
            return 400, b'{"error":"body"}', {}
        out = json.dumps(self.handle_sync(request), default=str).encode("utf-8")
        ts = repr(time.time())
        return 200, out, {"X-Aurora-Ts": ts, "X-Aurora-Sig": sign(self.secret, ts, out)}

    def start(self) -> bool:
        if self._thread is not None and self._thread.is_alive():
            return False
        server = self

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:  # quiet
                return

            def do_GET(self) -> None:
                if self.path != HEALTH_PATH:
                    self.send_error(404)
                    return
                body = json.dumps({"ok": True, "v": LINK_VERSION}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self) -> None:
                if self.path != SYNC_PATH:
                    self.send_error(404)
                    return
                try:
                    length = int(self.headers.get("Content-Length") or 0)
                except Exception:
                    length = 0
                if length <= 0 or length > MAX_BODY_BYTES:
                    self.send_error(413)
                    return
                status, body, extra = server.handle_http(self.rfile.read(length), self.headers)
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                for key, value in extra.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(body)

        self._httpd = ThreadingHTTPServer((self.host, self.port), _Handler)
        self._httpd.daemon_threads = True
        self.port = int(self._httpd.server_address[1])
        self._thread = threading.Thread(target=self._httpd.serve_forever,
                                        name="aurora-strata-link-server", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        self._thread = None

    def status(self) -> Dict[str, Any]:
        state = self._load_state()
        return {"version": LINK_VERSION, "port": self.port,
                "thread_alive": bool(self._thread and self._thread.is_alive()),
                "epoch": state["epoch"], "owner": state["owner"],
                "last_seen": state["last_seen"], "applied": state["applied"],
                "downlink_enabled": self.downlink_enabled(),
                "seeded": _read_json(link_dir(self.state_dir) / "seeded.json", None),
                "handoff_pending": bool(state.get("handoff")),
                "migrations": state.get("migrations") or [],
                "down_outbox": self.outbox.stats(),
                "last_error": self.last_error, **self.counters}

    def surface_ready(self, surface_id):
        with self._lock:
            state = self._load_state()
            return state["owner"] == surface_id and not bool(state.get("handoff"))


_SERVER: Optional[StrataLinkServer] = None


def start_strata_link_server_if_configured(state_dir: Any, *, host: str = "0.0.0.0",
                                           port: Optional[int] = None) -> Optional[StrataLinkServer]:
    """Start the server only when this device was set up as a Subsurface host
    (a secret exists because `pair` was run).  Otherwise do nothing at all."""
    global _SERVER
    if _SERVER is not None:
        return _SERVER
    if not _read_text(link_dir(state_dir) / "secret.txt"):
        return None
    chosen = int(port or os.environ.get("AURORA_STRATA_LINK_PORT") or DEFAULT_PORT)
    server = StrataLinkServer(state_dir, host=host, port=chosen, state_install_allowed=False)
    server.start()
    _SERVER = server
    return server


def get_server() -> Optional[StrataLinkServer]:
    return _SERVER


# ---------------------------------------------------------------------------
# Surface side: the client
# ---------------------------------------------------------------------------

Transport = Callable[[bytes, Dict[str, str]], Tuple[bytes, Mapping[str, str]]]


def configure_surface(state_dir: Any, pairing: str) -> Dict[str, Any]:
    """Store the pairing line (http://host:port#secret) on a Surface device."""
    text = str(pairing or "").strip()
    endpoint, _, secret = text.partition("#")
    endpoint = endpoint.strip().rstrip("/")
    secret = secret.strip()
    if not endpoint.startswith(("http://", "https://")) or not secret:
        return {"ok": False, "error": "expected http://host:port#secret"}
    root = link_dir(state_dir)
    (root / "endpoint.txt").write_text(endpoint, encoding="utf-8")
    (root / "secret.txt").write_text(secret, encoding="utf-8")
    # Pairing is the operator's explicit act, so it carries the claim: this
    # device asks to become the active Surface until the Subsurface agrees.
    (root / "claim_pending").write_text(str(time.time()), encoding="utf-8")
    return {"ok": True, "endpoint": endpoint}


def load_surface_config(state_dir: Any) -> Optional[Tuple[str, str]]:
    root = link_dir(state_dir)
    endpoint, secret = _read_text(root / "endpoint.txt"), _read_text(root / "secret.txt")
    return (endpoint, secret) if endpoint and secret else None


def surface_identity(state_dir: Any) -> str:
    path = link_dir(state_dir) / "surface_id.txt"
    surface_id = _read_text(path)
    if not surface_id:
        surface_id = "surface-" + uuid.uuid4().hex[:16]
        path.write_text(surface_id, encoding="utf-8")
    return surface_id


class StrataLinkClient:
    """Runs on the Surface device.  File work only: it never touches Aurora's
    cognitive lock, so it cannot delay a live turn."""

    FAST_INTERVAL_S = 2.0
    IDLE_INTERVAL_S = 20.0
    MAX_BACKOFF_S = 60.0

    def __init__(self, state_dir: Any, *, endpoint: str, secret: str,
                 transport: Optional[Transport] = None, timeout_s: float = 8.0) -> None:
        self.state_dir = Path(str(state_dir))
        self.endpoint = str(endpoint).rstrip("/")
        self.secret = str(secret)
        self.timeout_s = float(timeout_s)
        self.surface_id = surface_identity(self.state_dir)
        self.outbox = DurableOutbox(link_dir(self.state_dir) / "up_outbox.json")
        self._state_path = link_dir(self.state_dir) / "client_state.json"
        self._transport: Transport = transport or self._http_transport
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        # One exchange or transfer at a time per client: the background loop
        # and a user-started seed/handoff share the outbox and the numbering.
        self._sync_lock = threading.RLock()
        self._claim_path = link_dir(self.state_dir) / "claim_pending"
        self.online = False
        # Role, readiness and epoch survive a restart: the device that held
        # her when the link dropped stays present away from home; a device
        # that never held her cannot start living on its own.
        saved = self._load_client_state()
        self.role = str(saved.get("role") or "unknown")
        self.surface_ready = bool(saved.get("surface_ready", False))
        self.epoch = int(saved.get("epoch", 0) or 0)
        self.last_confirmed_at = float(saved.get("confirmed_at", 0.0) or 0.0)
        self.rtt_ms = 0.0
        self.last_sync_at = 0.0
        self.last_error = ""
        self.counters: Dict[str, int] = {"syncs": 0, "sent": 0, "received": 0,
                                         "failures": 0, "bad_signature": 0}

    def _load_client_state(self) -> Dict[str, Any]:
        data = _read_json(self._state_path, {})
        return data if isinstance(data, dict) else {}

    def _save_client_state(self, **updates: Any) -> Dict[str, Any]:
        data = self._load_client_state()
        data.update(updates)
        _atomic_write_json(self._state_path, data)
        return data

    def _confirm(self, response: Mapping[str, Any]) -> None:
        """Take the holder's view from a verified response and keep it on disk."""
        self.role = str(response.get("role") or self.role or "unknown")
        self.surface_ready = bool(response.get("surface_ready", self.role == "active"))
        self.epoch = int(response.get("epoch", self.epoch) or 0)
        self.last_confirmed_at = time.time()
        self._save_client_state(role=self.role, surface_ready=self.surface_ready, epoch=self.epoch,
                                owner=str(response.get("owner") or ""), confirmed_at=self.last_confirmed_at)
        self._resolve_inflight_handoff(str(response.get("handoff_from") or ""))

    def _frozen_path(self) -> Path:
        return link_dir(self.state_dir) / "surface_frozen"

    def _resolve_inflight_handoff(self, handoff_from: str) -> None:
        """A checkpoint commit whose reply never came: home now says whether
        it landed.  Landed (or the role moved on) keeps the freeze; no
        checkpoint while this device still holds her lifts it."""
        saved = self._load_client_state()
        if not saved.get("handoff_in_flight"):
            return
        if handoff_from == self.surface_id or self.role != "active":
            self._save_client_state(handoff_in_flight=None)
            return
        if not handoff_from:
            self._frozen_path().unlink(missing_ok=True)
            self._save_client_state(handoff_in_flight=None)
            self.surface_ready = self.role == "active"

    def away(self) -> bool:
        """Holding her, with home out of reach: she stays present here."""
        return (not self.online) and self.role == "active" and self.surface_ready

    def _http_transport(self, body: bytes, headers: Dict[str, str]) -> Tuple[bytes, Mapping[str, str]]:
        request = urllib.request.Request(self.endpoint + SYNC_PATH, data=body, method="POST",
                                         headers={"Content-Type": "application/json", **headers})
        with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
            return response.read(), dict(response.headers.items())

    def request_claim(self) -> None:
        """Ask to become the active Surface on the next sync (explicit only)."""
        self._claim_path.write_text(str(time.time()), encoding="utf-8")

    def sync_once(self) -> bool:
        with self._sync_lock:
            return self._sync_once_locked()

    def _sync_once_locked(self) -> bool:
        """One exchange.  Returns True when anything moved in either direction.
        Uplink is collected into the durable outbox BEFORE the network is
        touched, so being offline never loses a lived turn."""
        try:
            collect_surface_uplink(self.state_dir, self.outbox)
        except Exception as exc:
            self.last_error = f"collect: {type(exc).__name__}: {exc}"[:200]
        client_state = _read_json(self._state_path, {})
        if not isinstance(client_state, dict):
            client_state = {}
        link_key = str(client_state.get("link_key") or "")
        down_applied = int(client_state.get("down_applied", 0) or 0)
        batch = self.outbox.pending(MAX_BATCH)
        body = json.dumps({"v": LINK_VERSION, "surface_id": self.surface_id,
                           "claim": self._claim_path.exists(), "up": batch,
                           "link_key": link_key, "down_ack": down_applied},
                          default=str).encode("utf-8")
        ts = repr(time.time())
        started = time.time()
        try:
            raw, headers = self._transport(body, {"X-Aurora-Ts": ts,
                                                  "X-Aurora-Sig": sign(self.secret, ts, body)})
        except Exception as exc:
            self.online = False
            self.counters["failures"] += 1
            self.last_error = f"{type(exc).__name__}: {exc}"[:200]
            return False
        lowered = {str(k).lower(): str(v) for k, v in dict(headers).items()}
        if not verify(self.secret, lowered.get("x-aurora-ts", ""), raw, lowered.get("x-aurora-sig", "")):
            self.online = False
            self.counters["bad_signature"] += 1
            self.last_error = "response signature rejected"
            return False
        try:
            response = json.loads(raw.decode("utf-8"))
        except Exception:
            self.online = False
            self.counters["failures"] += 1
            self.last_error = "response not JSON"
            return False
        sample = (time.time() - started) * 1000.0
        self.rtt_ms = sample if not self.rtt_ms else 0.8 * self.rtt_ms + 0.2 * sample
        self.online = True
        self.last_sync_at = time.time()
        self.last_error = str(response.get("error") or "")
        self.counters["syncs"] += 1
        self._confirm(response)
        if self.role == "active" and self._claim_path.exists():
            try:
                self._claim_path.unlink()
            except Exception:
                pass
        new_key = str(response.get("link_key") or "")
        if new_key != link_key:
            # A new epoch or a rebuilt Subsurface numbers its downlink afresh.
            link_key, down_applied = new_key, 0
            self._save_client_state(link_key=link_key, down_applied=0)
        sent = self.outbox.ack(int(response.get("up_ack", 0) or 0))
        self.counters["sent"] += sent
        received = 0
        for record in sorted([r for r in (response.get("down") or []) if isinstance(r, dict)],
                             key=lambda r: int(r.get("seq", 0) or 0)):
            seq = int(record.get("seq", 0) or 0)
            if seq <= down_applied:
                continue
            try:
                apply_downlink_record(self.state_dir, record)
            except Exception as exc:
                self.last_error = f"apply: {type(exc).__name__}: {exc}"[:200]
                break
            down_applied = seq
            received += 1
            self._save_client_state(link_key=link_key, down_applied=down_applied)
        self.counters["received"] += received
        return bool(sent or received)

    # -- state transfer (seed and handoff) ----------------------------------------

    def _call(self, extra: Dict[str, Any]) -> Dict[str, Any]:
        """One signed exchange carrying a state operation.  Raises
        TransferError with the reason; never returns a half-trusted answer."""
        from aurora_internal.dual_strata.strata_state_transfer import TransferError
        client_state = _read_json(self._state_path, {})
        client_state = client_state if isinstance(client_state, dict) else {}
        payload = {"v": LINK_VERSION, "surface_id": self.surface_id, "claim": False, "up": [],
                   "link_key": str(client_state.get("link_key") or ""),
                   "down_ack": int(client_state.get("down_applied", 0) or 0)}
        payload.update(extra)
        body = json.dumps(payload, default=str).encode("utf-8")
        ts = repr(time.time())
        try:
            raw, headers = self._transport(body, {"X-Aurora-Ts": ts,
                                                  "X-Aurora-Sig": sign(self.secret, ts, body)})
        except Exception as exc:
            self.online = False
            raise TransferError(f"link down: {type(exc).__name__}: {exc}")
        lowered = {str(k).lower(): str(v) for k, v in dict(headers).items()}
        if not verify(self.secret, lowered.get("x-aurora-ts", ""), raw, lowered.get("x-aurora-sig", "")):
            raise TransferError("response signature rejected")
        try:
            response = json.loads(raw.decode("utf-8"))
        except Exception:
            raise TransferError("response not JSON")
        self.online = True
        self._confirm(response)
        return response

    def _state_call(self, op: Dict[str, Any], **extra: Any) -> Dict[str, Any]:
        from aurora_internal.dual_strata.strata_state_transfer import TransferError
        response = self._call({"state_op": op, **extra})
        result = response.get("state_result")
        # A first-pairing migration is staged from a standby device.
        standby_ok = op.get("op") == "migration_status" or str(op.get("transfer_id") or "").startswith("migrate-")
        if response.get("role") != "active" and not standby_ok:
            raise TransferError(f"this device is not the active Surface ({response.get('error') or 'standby'})")
        if isinstance(result, dict) and "expected_offset" in result:
            return result  # a resumable disagreement about where a file stands, not a failure
        if not isinstance(result, dict) or not result.get("ok"):
            raise TransferError(str((result or {}).get("error") or "state operation failed"))
        return result

    def flush_outbox(self, rounds: int = 20) -> bool:
        """Sync until everything lived so far has been acknowledged."""
        for _ in range(max(1, int(rounds))):
            self.sync_once()
            if not self.outbox.stats()["pending"] and self.online:
                return True
        return not self.outbox.stats()["pending"]

    def push_state(self, purpose: str = "seed", *, chunk_bytes: Optional[int] = None,
                   progress: Optional[Callable[[str, int, int], None]] = None) -> Dict[str, Any]:
        with self._sync_lock:
            return self._push_state_locked(purpose, chunk_bytes=chunk_bytes, progress=progress)

    def _push_state_locked(self, purpose: str, *, chunk_bytes: Optional[int],
                           progress: Optional[Callable[[str, int, int], None]]) -> Dict[str, Any]:
        """Give the Subsurface device this device's continuity.

        purpose "seed"     the Subsurface installs it (backing up what it
                           replaces), then the downlink may carry projections.
        purpose "handoff"  the Subsurface holds it as a checkpoint for the next
                           Surface device, and returns the token that device
                           must present.
        purpose "migrate"  first pairing of a phone that lived as a whole mind
                           (strata_migration): home stages it and reports how
                           the two copies differ.  Allowed from a standby
                           device; nothing at home changes until applied.

        Everything lived so far is flushed first, the files are snapshotted so
        the hashes describe the bytes sent, and the transfer resumes after an
        interruption (the transfer id is derived from the content)."""
        from aurora_internal.dual_strata import strata_state_transfer as st
        chunk = int(chunk_bytes or st.CHUNK_BYTES)
        try:
            lived_at_snapshot = 0
            if purpose == "migrate":
                # What it lived after this point stays in its outbox and is
                # integrated at home after the receipt (the first-pairing tail).
                self._call({})
                lived_at_snapshot = lived_high_water(self.state_dir)
            else:
                if not self.flush_outbox():
                    return {"ok": False, "error": "unacknowledged_continuity; state transfer must wait"}
                probe = self._call({})
                if probe.get("role") != "active":
                    return {"ok": False, "error": f"not the active Surface ({probe.get('error') or 'standby'})"}
            snap = link_dir(self.state_dir) / "snapshots" / "current"
            if purpose == "handoff":
                # Her present goes with her: the working frame and her habitat
                # (aurora_store_ownership.MOVES_WITH_HER).  Deep stores are
                # home's and never ride a handoff.
                from aurora_internal.dual_strata.surface_working_state import FILENAME
                from aurora_internal.aurora_store_ownership import moves_with_her
                rel_paths = sorted({FILENAME, *moves_with_her(self.state_dir)})
                manifest = st.snapshot_state(self.state_dir, snap, rel_paths=rel_paths)
            else:
                manifest = st.snapshot_state(self.state_dir, snap)
            if not manifest:
                return {"ok": False, "error": "nothing to transfer"}
            digest = st.manifest_digest(manifest)
            tid = f"{purpose}-{digest[:16]}"
            offered = self._state_call({"op": "offer", "transfer_id": tid, "purpose": purpose,
                                        "manifest": manifest, "lived_seq": lived_at_snapshot})
            have = set(offered.get("have") or [])
            sent = 0
            total = sum(int(m["size"]) for m in manifest if m["path"] not in have)
            for row in manifest:
                if row["path"] in have:
                    continue
                offset = 0
                with open(snap / row["path"], "rb") as handle:
                    while True:
                        handle.seek(offset)
                        data = handle.read(chunk)
                        reply = self._state_call({"op": "chunk", "transfer_id": tid, "path": row["path"],
                                                  "offset": offset,
                                                  "data": base64.b64encode(data).decode("ascii")})
                        if "expected_offset" in reply:
                            offset = int(reply["expected_offset"])
                            continue
                        offset += len(data)
                        sent += len(data)
                        if progress:
                            progress(row["path"], sent, total)
                        if reply.get("complete") or not data:
                            break
            if purpose == "handoff":
                # Freeze before release: fenced on this disk first, then the
                # checkpoint is committed.  If the reply is lost the freeze
                # stays until home says no checkpoint landed.
                self._frozen_path().write_text(str(time.time()), encoding="utf-8")
                self.surface_ready = False
                self._save_client_state(surface_ready=False, handoff_in_flight=tid)
                try:
                    done = self._state_call({"op": "commit", "transfer_id": tid, "source_frozen": True,
                                             "lived_seq": lived_high_water(self.state_dir)})
                except st.TransferError as exc:
                    if not str(exc).startswith(("link down", "response")):
                        # Home answered and refused: no checkpoint exists.
                        self._frozen_path().unlink(missing_ok=True)
                        self._save_client_state(handoff_in_flight=None)
                        self.surface_ready = self.role == "active"
                    raise
                self._save_client_state(handoff_in_flight=None, surface_ready=False)
                self.surface_ready = False
            else:
                done = self._state_call({"op": "commit", "transfer_id": tid})
                if purpose == "migrate":
                    self._save_client_state(migration={"id": tid, "digest": digest,
                                                       "lived_seq": lived_at_snapshot, "at": time.time()})
            shutil.rmtree(snap, ignore_errors=True)
            return {"ok": True, "purpose": purpose, "transfer_id": tid, "digest": digest,
                    "files": len(manifest), "skipped_already_there": len(have),
                    "bytes_sent": sent, **{k: v for k, v in done.items() if k != "ok"}}
        except st.TransferError as exc:
            self.last_error = f"push_state: {exc}"[:200]
            return {"ok": False, "error": str(exc)}

    def migrate(self, *, progress: Optional[Callable[[str, int, int], None]] = None) -> Dict[str, Any]:
        """First pairing: send this whole mind home to be staged and compared.
        This device keeps running as it is until the receipt is accepted."""
        return self.push_state("migrate", progress=progress)

    def check_migration(self) -> Dict[str, Any]:
        """Ask home how the first pairing stands.  When home has applied it,
        check the receipt against the snapshot this device sent; only a
        matching receipt is kept, and it takes effect at the next start."""
        from aurora_internal.dual_strata import strata_migration as sm
        from aurora_internal.dual_strata import strata_state_transfer as st
        mine = dict(self._load_client_state().get("migration") or {})
        if not mine.get("id"):
            return {"ok": False, "status": "not_started"}
        with self._sync_lock:
            try:
                status = self._state_call({"op": "migration_status"})
            except st.TransferError as exc:
                return {"ok": False, "status": "unreachable", "error": str(exc)}
        if status.get("migration_id") != mine["id"]:
            return {"ok": False, "status": "unknown_at_home"}
        if status.get("status") != "applied":
            return {"ok": True, **{k: v for k, v in status.items() if k != "ok"}}
        accepted = sm.accept_receipt(self.state_dir, status.get("receipt") or {},
                                     migration_id=mine["id"], source_digest=str(mine.get("digest") or ""))
        if not accepted.get("ok"):
            return {"ok": False, "status": "receipt_refused", "error": accepted.get("error")}
        self._drop_migrated_from_outbox(int(mine.get("lived_seq", 0) or 0))
        return {"ok": True, "status": "applied", "surface_only_at_next_start": True,
                "restart_required": True}

    def _drop_migrated_from_outbox(self, lived_seq: int) -> None:
        """Continuity lived up to the snapshot is already home in the migrated
        stores; it must not be lived a second time there."""
        last = 0
        for record in self.outbox.pending(10 ** 6):
            payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
            if record.get("channel") == "continuity" and int(payload.get("seq", 0) or 0) > lived_seq:
                break
            last = int(record.get("seq", 0) or 0)
        if last:
            self.outbox.ack(last)

    def cancel_handoff(self, token: str) -> Dict[str, Any]:
        with self._sync_lock:
            try:
                result = self._state_call({"op": "handoff_cancel", "token": str(token)})
                self._frozen_path().unlink(missing_ok=True)
                self._save_client_state(handoff_in_flight=None)
                self.sync_once()
                return result
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

    def pull_handoff(self, token: str, *, chunk_bytes: Optional[int] = None,
                     restore_callback=None) -> Dict[str, Any]:
        with self._sync_lock:
            return self._pull_handoff_locked(token, chunk_bytes=chunk_bytes, restore_callback=restore_callback)

    def _pull_handoff_locked(self, token: str, *, chunk_bytes: Optional[int], restore_callback=None) -> Dict[str, Any]:
        """Become the active Surface with the previous Surface's state.

        Claims the role with the checkpoint token, pulls every file, verifies
        each against its hash, installs with a backup, and only then tells the
        Subsurface the migration is complete.  Files this device already holds
        byte-for-byte are not pulled again."""
        from aurora_internal.dual_strata import strata_state_transfer as st
        chunk = int(chunk_bytes or st.CHUNK_BYTES)
        try:
            claimed = self._call({"claim": True, "handoff_token": str(token or "")})
            if claimed.get("role") != "active":
                return {"ok": False, "error": str(claimed.get("error") or "claim refused")}
            try:
                self._claim_path.unlink()
            except OSError:
                pass
            offer = self._state_call({"op": "pull_offer"})
            manifest = st.validate_manifest(offer.get("manifest"))
            digest = st.manifest_digest(manifest)
            if digest != str(offer.get("digest") or ""):
                return {"ok": False, "error": "manifest digest does not match the checkpoint"}
            staging = st.IncomingTransfer(link_dir(self.state_dir) / "staging", f"pull-{digest[:16]}")
            if not staging.exists():
                staging.begin(manifest, meta={"purpose": "pull", "digest": digest})
            done = set(staging.complete_paths())
            reused = pulled = 0
            for row in manifest:
                if row["path"] in done:
                    continue
                local = st.safe_join(self.state_dir, row["path"])
                if local.is_file() and local.stat().st_size == row["size"] \
                        and st.file_sha256(local) == row["sha256"]:
                    staging.accept_existing(row["path"], local)
                    reused += 1
                    continue
                offset = 0
                while True:
                    got = self._state_call({"op": "pull_chunk", "path": row["path"],
                                            "offset": offset, "length": chunk})
                    reply = staging.put_chunk(row["path"], offset, str(got.get("data") or ""))
                    if "expected_offset" in reply:
                        offset = int(reply["expected_offset"])
                        continue
                    n = int(got.get("n", 0) or 0)
                    offset += n
                    pulled += n
                    if reply.get("complete") or not n:
                        break
            bad = staging.verify_all()
            if bad:
                return {"ok": False, "error": "verification failed", "bad": bad[:20]}
            report = st.install_verified(staging.files, manifest, self.state_dir,
                                         link_dir(self.state_dir) / "backup" / f"pull-{digest[:16]}")
            if restore_callback is not None:
                # The role remains fenced until the living destination has
                # restored its present-frame state, not merely received bytes.
                restore_callback()
            self._state_call({"op": "handoff_complete", "digest": digest})
            # This device is now the one holder; a freeze left from an earlier
            # time it was the source no longer applies.
            self._frozen_path().unlink(missing_ok=True)
            self._save_client_state(handoff_in_flight=None)
            self.sync_once()
            staging.discard()
            return {"ok": True, "digest": digest, "files": len(manifest),
                    "reused_local": reused, "bytes_pulled": pulled, "epoch": self.epoch,
                    "restart_required": restore_callback is None, **report}
        except st.TransferError as exc:
            self.last_error = f"pull_handoff: {exc}"[:200]
            return {"ok": False, "error": str(exc)}
        except Exception as exc:
            self.last_error = f"restore_handoff: {type(exc).__name__}: {exc}"[:200]
            return {"ok": False, "error": self.last_error}

    def verify_sync(self) -> Dict[str, Any]:
        """How this device's state stands against the Subsurface device's,
        file by file, plus what is still waiting on the link."""
        from aurora_internal.dual_strata import strata_state_transfer as st
        try:
            self.sync_once()
            manifest = st.build_manifest(self.state_dir)
            report = self._state_call({"op": "verify", "manifest": manifest})
            return {"ok": True, "role": self.role, "epoch": self.epoch,
                    "up_pending": self.outbox.stats()["pending"],
                    **{k: v for k, v in report.items() if k != "ok"}}
        except st.TransferError as exc:
            return {"ok": False, "error": str(exc)}

    def _run(self) -> None:
        interval = self.FAST_INTERVAL_S
        while not self._stop.is_set():
            moved = self.sync_once()
            if not self.online:
                interval = min(max(interval, self.FAST_INTERVAL_S) * 2.0, self.MAX_BACKOFF_S)
            elif moved or self.outbox.stats()["pending"]:
                interval = self.FAST_INTERVAL_S
            else:
                interval = min(interval * 1.5, self.IDLE_INTERVAL_S)
            self._stop.wait(interval)

    def start(self) -> bool:
        if self._thread is not None and self._thread.is_alive():
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="aurora-strata-link", daemon=True)
        self._thread.start()
        return True

    def stop(self, timeout: float = 3.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        self._thread = None

    def status(self) -> Dict[str, Any]:
        if not self.online:
            label = "away" if self.away() else "offline"
        elif self.role == "standby":
            label = "standby"
        else:
            label = "online"
        return {"status": label, "version": LINK_VERSION, "endpoint": self.endpoint,
                "surface_id": self.surface_id, "role": self.role, "epoch": self.epoch,
                "thread_alive": bool(self._thread and self._thread.is_alive()),
                "rtt_ms": round(self.rtt_ms, 1), "last_sync_at": self.last_sync_at,
                "surface_ready": self.surface_ready, "away": self.away(),
                "frozen": self._frozen_path().exists(),
                "home_last_confirmed_at": self.last_confirmed_at,
                "up_outbox": self.outbox.stats(), "last_error": self.last_error,
                **self.counters}


_CLIENT: Optional[StrataLinkClient] = None


def start_strata_link_client_if_configured(state_dir: Any) -> Optional[StrataLinkClient]:
    """Start the client only when this Surface device has been paired."""
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    config = load_surface_config(state_dir)
    if config is None:
        return None
    client = StrataLinkClient(state_dir, endpoint=config[0], secret=config[1])
    client.start()
    _CLIENT = client
    return client


def stop_strata_link_client() -> None:
    global _CLIENT
    if _CLIENT is not None:
        _CLIENT.stop()
        _CLIENT = None


def strata_link_client_status() -> Dict[str, Any]:
    if _CLIENT is None:
        return {"status": "not_configured", "thread_alive": False}
    return _CLIENT.status()


# ---------------------------------------------------------------------------
# Command line (Subsurface device)
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Aurora strata link (Subsurface device)")
    parser.add_argument("command", choices=("pair", "status", "serve", "seed", "handoff-checkpoint",
                                            "handoff-claim", "verify"))
    parser.add_argument("--token", default="", help="handoff-claim: the token handoff-checkpoint printed")
    parser.add_argument("--state-dir", default="aurora_state")
    parser.add_argument("--host", default="", help="name or address the Surface device will dial")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    if args.command == "pair":
        if not args.host:
            parser.error("pair needs --host (the name or address the phone will dial)")
        print(pairing_line(args.state_dir, args.host, args.port))
        return 0
    if args.command == "status":
        print(json.dumps({"server_state": _read_json(link_dir(args.state_dir) / "server_state.json", {}),
                          "down_outbox": DurableOutbox(link_dir(args.state_dir) / "down_outbox.json").stats(),
                          "paired": bool(_read_text(link_dir(args.state_dir) / "secret.txt"))}, indent=2))
        return 0
    if args.command in ("seed", "handoff-checkpoint", "handoff-claim", "verify"):
        # Surface device: needs the pairing (`configure_surface`) already done.
        config = load_surface_config(args.state_dir)
        if config is None:
            parser.error("this device is not paired; pair it first")
        client = StrataLinkClient(args.state_dir, endpoint=config[0], secret=config[1])
        if args.command == "seed":
            result = client.push_state("seed")
        elif args.command == "handoff-checkpoint":
            result = client.push_state("handoff")
        elif args.command == "handoff-claim":
            if not args.token:
                parser.error("handoff-claim needs --token")
            result = client.pull_handoff(args.token)
        else:
            result = client.verify_sync()
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("ok") else 1
    # serve: standalone, for testing the connection.  In normal operation the
    # server runs inside aurora_daemon so it shares the continuity feed lock
    # with the Subsurface loop; standalone has no such lock across processes.
    server = StrataLinkServer(args.state_dir, port=args.port)
    server.start()
    print(f"strata link listening on port {server.port}")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
