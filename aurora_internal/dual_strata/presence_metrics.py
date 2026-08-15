"""
Instrumentation for the Subsurface Presence and Evidence Scout
architecture (spec section 19) -- recorded BEFORE any of the behavioral
changes (turn_open wiring, InterpretedTurnPacket, Scout dispatch) land,
so there is a real baseline to compare against once they do (spec
section 20, "Presence" acceptance criteria; step 12 of the implementation
order).

Deliberately a thin recorder, not a new metrics backend: process-level
host metrics (process_rss_mb, mem_available_mb, load_ratio) are read
from RuntimeConstraintGovernor.status()["host"] rather than
reimplemented -- that class already parses /proc/meminfo and
/proc/self/statm for exactly this purpose (see
aurora_runtime_constraint_governor.py's _host_metrics()). This module
adds only what didn't already exist: turn/scout timing counters and
presence-liveness ages, plus a single JSON snapshot file a baseline (or
post-change) capture can read.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals

import json
import time
from collections import deque
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

from aurora_internal.dual_strata import subsurface_presence as _presence

_METRICS_FILENAME = "presence_metrics.json"
_MAX_SAMPLES = 200


def _resolve(state_dir: Any) -> Path:
    if state_dir is not None:
        return Path(str(state_dir))
    return Path(__file__).resolve().parents[2] / "aurora_state"


def _percentile(samples: list, pct: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    idx = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return float(ordered[idx])


class PresenceMetrics:
    """One recorder per process (Surface daemon, Subsurface daemon, or
    Scout worker each hold their own). Thread-safe: aurora.py's existing
    Poedex staging threads (_stage_noncomp_prefetch et al.) show this
    process legitimately runs concurrent background work, so every
    counter update takes a lock."""

    def __init__(self, state_dir: Any = None, *, role: str = "unknown"):
        self.state_dir = state_dir
        self.role = str(role or "unknown")
        self._lock = Lock()
        self._surface_turn_latency_ms: deque = deque(maxlen=_MAX_SAMPLES)
        self._scout_dispatch_ms: deque = deque(maxlen=_MAX_SAMPLES)
        self._scout_roundtrip_ms: deque = deque(maxlen=_MAX_SAMPLES)
        self._scout_integration_ms: deque = deque(maxlen=_MAX_SAMPLES)
        self._subsurface_main_loop_block_ms: deque = deque(maxlen=_MAX_SAMPLES)
        self._scout_queue_depth = 0
        self._scout_active_count = 0
        self._surface_direct_retrieval_count = 0
        self._subsurface_direct_retrieval_count = 0

    # ── Recorders (each is a single, cheap, lock-protected append) ─────────

    def record_surface_turn_latency_ms(self, ms: float) -> None:
        with self._lock:
            self._surface_turn_latency_ms.append(float(ms))

    def record_scout_dispatch_ms(self, ms: float) -> None:
        with self._lock:
            self._scout_dispatch_ms.append(float(ms))

    def record_scout_roundtrip_ms(self, ms: float) -> None:
        with self._lock:
            self._scout_roundtrip_ms.append(float(ms))

    def record_scout_integration_ms(self, ms: float) -> None:
        with self._lock:
            self._scout_integration_ms.append(float(ms))

    def record_subsurface_main_loop_block_ms(self, ms: float) -> None:
        with self._lock:
            self._subsurface_main_loop_block_ms.append(float(ms))

    def set_scout_queue_depth(self, n: int) -> None:
        with self._lock:
            self._scout_queue_depth = max(0, int(n))

    def set_scout_active_count(self, n: int) -> None:
        with self._lock:
            self._scout_active_count = max(0, int(n))

    def record_surface_direct_retrieval(self) -> None:
        # Section 15's migration target: this counter should trend to
        # zero for AUTOMATIC gap retrieval as Steps 10-11 land. Explicit
        # user-requested search is not "automatic" and is out of scope
        # for that migration, so it still increments this counter --
        # the acceptance criterion is about the blocking retrieval path,
        # not this count reaching literal zero.
        with self._lock:
            self._surface_direct_retrieval_count += 1

    def record_subsurface_direct_retrieval(self) -> None:
        with self._lock:
            self._subsurface_direct_retrieval_count += 1

    # ── Snapshot ─────────────────────────────────────────────────────────

    def snapshot(self, systems: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Everything spec section 19 asks for, in one dict. Host metrics
        come from the live RuntimeConstraintGovernor when `systems`
        carries one (the normal in-process case); otherwise a fresh,
        standalone governor instance is used (safe -- status() falls
        back to a live _host_metrics() read when it has no decision
        history yet)."""
        host: Dict[str, Any] = {}
        governor_mode = "unknown"
        try:
            governor = None
            if isinstance(systems, dict):
                governor = systems.get("_runtime_constraint_governor")
            if governor is None:
                from aurora_internal.aurora_runtime_constraint_governor import RuntimeConstraintGovernor
                governor = RuntimeConstraintGovernor(str(self.state_dir or ""))
            status = governor.status()
            host = dict(status.get("host") or {})
            governor_mode = str(status.get("mode", "unknown") or "unknown")
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(), module=__name__,
                operation="exception_handler:aurora_internal/dual_strata/presence_metrics.py:snapshot:host",
                exc=_aurora_boundary_exc,
                context={"function": "PresenceMetrics.snapshot", "source_file": "aurora_internal/dual_strata/presence_metrics.py"},
            )
            host = {}

        with self._lock:
            surface_latency = list(self._surface_turn_latency_ms)
            scout_dispatch = list(self._scout_dispatch_ms)
            scout_roundtrip = list(self._scout_roundtrip_ms)
            scout_integration = list(self._scout_integration_ms)
            loop_block = list(self._subsurface_main_loop_block_ms)
            queue_depth = self._scout_queue_depth
            active_count = self._scout_active_count
            surface_retrieval = self._surface_direct_retrieval_count
            subsurface_retrieval = self._subsurface_direct_retrieval_count

        return {
            "captured_at": time.time(),
            "role": self.role,
            "governor_mode": governor_mode,
            "process_rss_mb": host.get("process_rss_mb", 0.0),
            "mem_available_mb": host.get("mem_available_mb", 0.0),
            "load_ratio": host.get("load_ratio", 0.0),
            "surface_turn_latency_ms": {
                "count": len(surface_latency),
                "p50": round(_percentile(surface_latency, 50), 2),
                "p95": round(_percentile(surface_latency, 95), 2),
                "max": round(max(surface_latency), 2) if surface_latency else 0.0,
            },
            "subsurface_presence_frame_age_ms": _presence.presence_frame_age_ms(self.state_dir),
            "subsurface_heartbeat_gap_ms": _presence.heartbeat_gap_ms(self.state_dir),
            "subsurface_main_loop_block_ms": {
                "count": len(loop_block),
                "p50": round(_percentile(loop_block, 50), 2),
                "p95": round(_percentile(loop_block, 95), 2),
                "max": round(max(loop_block), 2) if loop_block else 0.0,
            },
            "scout_dispatch_ms": {
                "count": len(scout_dispatch),
                "p50": round(_percentile(scout_dispatch, 50), 2),
            },
            "scout_roundtrip_ms": {
                "count": len(scout_roundtrip),
                "p50": round(_percentile(scout_roundtrip, 50), 2),
                "p95": round(_percentile(scout_roundtrip, 95), 2),
            },
            "scout_integration_ms": {
                "count": len(scout_integration),
                "p50": round(_percentile(scout_integration, 50), 2),
            },
            "scout_queue_depth": queue_depth,
            "scout_active_count": active_count,
            "surface_direct_retrieval_count": surface_retrieval,
            "subsurface_direct_retrieval_count": subsurface_retrieval,
        }

    def write_snapshot(self, systems: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Persist this recorder's snapshot to presence_metrics.json,
        keyed by role so Surface/Subsurface/Scout snapshots from
        separate processes don't clobber each other."""
        snap = self.snapshot(systems)
        root = _resolve(self.state_dir)
        path = root / _METRICS_FILENAME
        try:
            existing: Dict[str, Any] = {}
            if path.exists():
                try:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(raw, dict):
                        existing = raw
                except Exception as _aurora_boundary_exc:
                    _aurora_record_exception_from_locals(
                        locals(), module=__name__,
                        operation="exception_handler:aurora_internal/dual_strata/presence_metrics.py:write_snapshot:read",
                        exc=_aurora_boundary_exc,
                        context={"function": "PresenceMetrics.write_snapshot", "source_file": "aurora_internal/dual_strata/presence_metrics.py"},
                    )
                    existing = {}
            existing[self.role] = snap
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(existing, indent=2), encoding="utf-8")
            tmp.replace(path)
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(), module=__name__,
                operation="exception_handler:aurora_internal/dual_strata/presence_metrics.py:write_snapshot:write",
                exc=_aurora_boundary_exc,
                context={"function": "PresenceMetrics.write_snapshot", "source_file": "aurora_internal/dual_strata/presence_metrics.py"},
            )
        return snap


def read_all_snapshots(state_dir: Any) -> Dict[str, Any]:
    """Read every role's last-written snapshot -- what step 12's
    before/after comparison reads."""
    root = _resolve(state_dir)
    path = root / _METRICS_FILENAME
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(), module=__name__,
            operation="exception_handler:aurora_internal/dual_strata/presence_metrics.py:read_all_snapshots",
            exc=_aurora_boundary_exc,
            context={"function": "read_all_snapshots", "source_file": "aurora_internal/dual_strata/presence_metrics.py"},
        )
        return {}
