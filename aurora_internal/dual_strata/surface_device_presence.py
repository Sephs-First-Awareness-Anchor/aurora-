"""Subsurface's authority over the one Surface and its traveling state.

One instance is owned by the hub process. A Surface endpoint acknowledges
its own state and the operator chooses a transfer target. The transport
must authenticate device identities before invoking these methods.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import threading
import time
from typing import Callable
import uuid

from aurora_persistence_utils import atomic_write_json


class SurfacePresenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class SurfaceCheckpoint:
    revision: int
    data: bytes
    digest: str


@dataclass(frozen=True)
class SurfaceLease:
    surface_id: str
    device_id: str
    epoch: int
    state: str
    valid_for_s: float
    checkpoint_revision: int


@dataclass(frozen=True)
class _Presence:
    surface_id: str
    devices: dict[str, str]
    epoch: int = 0
    active: str | None = None
    requested: str | None = None
    checkpoint: SurfaceCheckpoint | None = None
    recovery_required: bool = False


class SurfaceDevicePresence:
    def __init__(self, path: Path, *, lease_s: float = 15.0, online_s: float = 30.0,
                 clock: Callable[[], float] = time.monotonic) -> None:
        if not 0 < lease_s <= online_s:
            raise ValueError("expected a positive lease no longer than the online window")
        self._path = Path(path)
        self._clock = clock
        self._lease_s = lease_s
        self._online_s = online_s
        self._lock = threading.Lock()
        self._last_seen: dict[str, float] = {}
        self._in_flight: str | None = None
        self._expires = 0.0
        try:
            saved = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            saved = {}
        checkpoint = None
        if saved.get("checkpoint") is not None:
            stored = saved["checkpoint"]
            data = base64.b64decode(stored["data"], validate=True)
            digest = hashlib.sha256(data).hexdigest()
            if digest != stored["digest"]:
                raise SurfacePresenceError("the saved Surface checkpoint is damaged")
            checkpoint = SurfaceCheckpoint(int(stored["revision"]), data, digest)
        self._record = _Presence(
            surface_id=saved.get("surface_id") or uuid.uuid4().hex,
            devices=dict(saved.get("devices", {})),
            epoch=int(saved.get("epoch", 0)),
            requested=saved.get("requested_device"),
            checkpoint=checkpoint,
            recovery_required=bool(saved.get("recovery_required") or saved.get("active_device")),
        )
        # Keep the previous active marker on disk until its full lease lifetime
        # passes. A second hub restart must also respect that quarantine.
        old_lease_s = float(saved.get("lease_s", lease_s))
        self._recover_until = self._clock() + old_lease_s if saved.get("active_device") else 0.0

    @property
    def _revision(self) -> int:
        checkpoint = self._record.checkpoint
        return checkpoint.revision if checkpoint else 0

    def _save(self, **changes) -> None:
        record = replace(self._record, **changes)
        checkpoint = record.checkpoint
        saved = atomic_write_json(self._path, {
            "surface_id": record.surface_id,
            "devices": record.devices,
            "epoch": record.epoch,
            "active_device": record.active,
            "requested_device": record.requested,
            "recovery_required": record.recovery_required,
            "lease_s": self._lease_s,
            "checkpoint": {
                "revision": checkpoint.revision,
                "digest": checkpoint.digest,
                "data": base64.b64encode(checkpoint.data).decode("ascii"),
            } if checkpoint else None,
        })
        if not saved:
            raise OSError("could not commit the Surface checkpoint and lease")
        self._record = record

    def _require_device(self, device_id: str) -> None:
        if device_id not in self._record.devices:
            raise SurfacePresenceError("Surface device is unregistered")

    def _require_recovery_window_end(self, now: float) -> None:
        if now < self._recover_until:
            raise SurfacePresenceError("the hub is waiting for the previous lease to expire")

    def _online(self, device_id: str, now: float) -> bool:
        last_seen = self._last_seen.get(device_id)
        return last_seen is not None and now - last_seen < self._online_s

    def register(self, device_id: str, label: str) -> None:
        device_id, label = device_id.strip(), label.strip()
        if not device_id or not label:
            raise ValueError("a registered device needs an ID and a label")
        with self._lock:
            existing = self._record.devices.get(device_id)
            if existing is not None:
                if existing != label:
                    raise SurfacePresenceError("the device ID is already registered")
                return
            self._require_recovery_window_end(self._clock())
            self._save(devices={**self._record.devices, device_id: label})

    def _activate(self, device_id: str, now: float) -> None:
        self._save(active=device_id, requested=None, epoch=self._record.epoch + 1)
        self._expires = now + self._lease_s

    def _advance(self, now: float) -> None:
        if self._record.active is not None and now >= self._expires:
            self._save(active=None, epoch=self._record.epoch + 1, recovery_required=True)
            self._in_flight = None
        # Only the very first Surface may start without a checkpoint.
        target = self._record.requested
        if (self._record.active is None and self._record.checkpoint is None
                and not self._record.recovery_required and target is not None
                and self._online(target, now)):
            self._activate(target, now)

    def heartbeat(self, device_id: str) -> SurfaceLease:
        with self._lock:
            self._require_device(device_id)
            now = self._clock()
            self._last_seen[device_id] = now
            self._advance(now)
            record = self._record
            state, valid_for = "asleep", 0.0
            if record.active == device_id:
                draining = record.requested is not None
                if not draining or self._in_flight is not None:
                    self._expires = now + self._lease_s
                state, valid_for = ("draining" if draining else "awake"), self._expires - now
            elif (record.active is None and not record.recovery_required
                  and record.requested == device_id):
                state = "restoring"
            return SurfaceLease(record.surface_id, device_id, record.epoch, state, valid_for, self._revision)

    def status(self) -> dict:
        with self._lock:
            now = self._clock()
            self._advance(now)
            record = self._record
            return {
                "surface_id": record.surface_id,
                "epoch": record.epoch,
                "active_device": record.active,
                "requested_device": record.requested,
                "in_flight_turn": self._in_flight,
                "recovering": now < self._recover_until,
                "recovery_required": record.recovery_required,
                "checkpoint_revision": self._revision,
                "devices": {
                    device_id: {"label": label, "online": self._online(device_id, now)}
                    for device_id, label in record.devices.items()
                },
            }

    def request_transfer(self, target: str, *, expected_epoch: int) -> None:
        with self._lock:
            self._require_device(target)
            now = self._clock()
            self._advance(now)
            self._require_recovery_window_end(now)
            record = self._record
            if expected_epoch != record.epoch:
                raise SurfacePresenceError("Surface presence changed before transfer")
            if not self._online(target, now):
                raise SurfacePresenceError("the requested Surface is offline")
            if record.requested is not None and record.requested != target:
                raise SurfacePresenceError("another transfer is already pending")
            if record.active == target or record.requested == target:
                return
            self._save(requested=target)
            self._advance(now)

    def _require_lease(self, device_id: str, epoch: int, now: float) -> None:
        self._advance(now)
        if self._record.active != device_id or self._record.epoch != epoch:
            raise SurfacePresenceError("the Surface lease is stale or belongs to another device")

    def _require_awake(self, device_id: str, epoch: int) -> None:
        self._require_lease(device_id, epoch, self._clock())
        if self._record.requested is not None:
            raise SurfacePresenceError("Surface is preparing to sleep")

    def require_awake(self, device_id: str, epoch: int) -> None:
        with self._lock:
            self._require_awake(device_id, epoch)

    def begin_turn(self, device_id: str, epoch: int, turn_id: str) -> None:
        if not turn_id:
            raise ValueError("a Surface turn needs an ID")
        with self._lock:
            self._require_awake(device_id, epoch)
            if self._record.checkpoint is None:
                raise SurfacePresenceError("save the initial Surface checkpoint before admitting turns")
            if self._in_flight is not None:
                raise SurfacePresenceError("another Surface turn is in flight")
            self._in_flight = turn_id

    def finish_turn(self, device_id: str, epoch: int, turn_id: str) -> None:
        with self._lock:
            now = self._clock()
            self._require_lease(device_id, epoch, now)
            if self._in_flight is None or self._in_flight != turn_id:
                raise SurfacePresenceError("this turn is not in flight")
            self._in_flight = None
            if self._record.requested is not None:
                self._expires = now + self._lease_s

    def _next_checkpoint(self, data: bytes, expected_revision: int) -> SurfaceCheckpoint:
        if not isinstance(data, bytes) or not data:
            raise ValueError("Surface state must be serialized as nonempty bytes")
        if expected_revision != self._revision:
            raise SurfacePresenceError("the Surface checkpoint revision changed")
        return SurfaceCheckpoint(self._revision + 1, data, hashlib.sha256(data).hexdigest())

    def save_checkpoint(self, device_id: str, epoch: int, data: bytes, *,
                        expected_revision: int) -> SurfaceCheckpoint:
        with self._lock:
            self._require_awake(device_id, epoch)
            if self._in_flight is not None:
                raise SurfacePresenceError("checkpoint at a completed turn boundary")
            checkpoint = self._next_checkpoint(data, expected_revision)
            self._save(checkpoint=checkpoint)
            return checkpoint

    def acknowledge_sleep(self, device_id: str, epoch: int, data: bytes, *,
                          expected_revision: int) -> None:
        with self._lock:
            self._require_lease(device_id, epoch, self._clock())
            if self._record.requested is None or self._in_flight is not None:
                raise SurfacePresenceError("Surface has no handoff ready to acknowledge")
            checkpoint = self._next_checkpoint(data, expected_revision)
            # Freeze state and retire the old writer in the same disk commit.
            self._save(active=None, checkpoint=checkpoint, epoch=self._record.epoch + 1)
            self._expires = 0.0

    def _restore_for(self, device_id: str, epoch: int, now: float) -> SurfaceCheckpoint:
        record = self._record
        if (record.active is not None or record.requested != device_id or record.epoch != epoch
                or record.recovery_required or record.checkpoint is None or not self._online(device_id, now)):
            raise SurfacePresenceError("this Surface has no checkpoint ready to restore")
        return record.checkpoint

    def restore_checkpoint(self, device_id: str, epoch: int) -> SurfaceCheckpoint:
        with self._lock:
            return self._restore_for(device_id, epoch, self._clock())

    def acknowledge_restore(self, device_id: str, epoch: int, revision: int, digest: str) -> None:
        with self._lock:
            now = self._clock()
            checkpoint = self._restore_for(device_id, epoch, now)
            if revision != checkpoint.revision or digest != checkpoint.digest:
                raise SurfacePresenceError("the Surface did not restore the current checkpoint")
            self._activate(device_id, now)

    def recover_checkpoint(self, *, expected_epoch: int, revision: int) -> None:
        """Operator authorizes resuming from the last committed state after an interruption."""
        with self._lock:
            now = self._clock()
            self._advance(now)
            self._require_recovery_window_end(now)
            record = self._record
            if (not record.recovery_required or record.epoch != expected_epoch or record.requested is None
                    or record.checkpoint is None or record.checkpoint.revision != revision):
                raise SurfacePresenceError("no matching committed Surface checkpoint is ready for recovery")
            self._save(recovery_required=False)
