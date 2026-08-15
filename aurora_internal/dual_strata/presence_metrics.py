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
from collections import Counter, deque
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

        # Build 694 step 17 (spec section 30) additions -- everything the
        # prior build's baseline instrumentation (above) didn't already
        # cover, needed to empirically answer "did Subsurface become more
        # present?" and "did generic admissibility decrease because
        # unresolved pressure is now acted upon?"
        self._turn_open_latency_ms: deque = deque(maxlen=_MAX_SAMPLES)
        self._interpreted_turn_latency_ms: deque = deque(maxlen=_MAX_SAMPLES)
        self._presence_processing_latency_ms: deque = deque(maxlen=_MAX_SAMPLES)
        self._presence_event_queue_depth = 0
        self._response_fit_pressure: deque = deque(maxlen=_MAX_SAMPLES)
        self._knowledge_gap_pressure: deque = deque(maxlen=_MAX_SAMPLES)
        self._scout_dispatch_reason: Counter = Counter()
        self._scout_request_kind: Counter = Counter()
        self._scout_backend: Counter = Counter()
        self._same_turn_wait_ms: deque = deque(maxlen=_MAX_SAMPLES)
        self._same_turn_binding_used_count = 0
        self._same_turn_binding_unused_count = 0
        self._abstain_before_scout_count = 0
        self._abstain_after_scout_count = 0
        self._abstain_rescue_attempted_count = 0
        self._abstain_rescue_succeeded_count = 0

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

    # ── Build 694 step 17 recorders ─────────────────────────────────────

    def record_turn_open_latency_ms(self, ms: float) -> None:
        """Time between Surface writing a turn_open event (event's own
        created_at) and Subsurface integrating it -- the direct measure
        of "does Subsurface know a live turn is happening promptly," spec
        section 30's first empirical question."""
        with self._lock:
            self._turn_open_latency_ms.append(float(ms))

    def record_interpreted_turn_latency_ms(self, ms: float) -> None:
        with self._lock:
            self._interpreted_turn_latency_ms.append(float(ms))

    def record_presence_processing_latency_ms(self, ms: float) -> None:
        """One SubsurfacePresenceRuntime.tick() cycle's own wall-clock
        cost -- distinct from subsurface_main_loop_block_ms (the SLOW
        daemon-loop backstop's per-iteration cost, prior build)."""
        with self._lock:
            self._presence_processing_latency_ms.append(float(ms))

    def set_presence_event_queue_depth(self, n: int) -> None:
        with self._lock:
            self._presence_event_queue_depth = max(0, int(n))

    def record_response_fit_pressure(self, value: float) -> None:
        with self._lock:
            self._response_fit_pressure.append(max(0.0, min(1.0, float(value))))

    def record_knowledge_gap_pressure(self, value: float) -> None:
        with self._lock:
            self._knowledge_gap_pressure.append(max(0.0, min(1.0, float(value))))

    def record_scout_dispatch_reason(self, reason: str) -> None:
        """spec section 30's scout_dispatch_reason -- e.g.
        "trigger_a_pressure", "trigger_b_abstention_rescue",
        "evidence_need_knowledge_gap", "self_diagnostic"."""
        with self._lock:
            self._scout_dispatch_reason[str(reason or "unspecified")] += 1

    def record_scout_request_kind(self, request_kind: str) -> None:
        with self._lock:
            self._scout_request_kind[str(request_kind or "unspecified")] += 1

    def record_scout_backend(self, backend_name: str) -> None:
        with self._lock:
            self._scout_backend[str(backend_name or "none")] += 1

    def record_same_turn_wait_ms(self, ms: float) -> None:
        with self._lock:
            self._same_turn_wait_ms.append(float(ms))

    def record_same_turn_binding_used(self, used: bool) -> None:
        """spec section 30's same_turn_binding_used -- whether a bounded
        same-turn wait (Build 694 step 14/15) actually produced evidence
        response formation used, not merely whether a wait happened."""
        with self._lock:
            if used:
                self._same_turn_binding_used_count += 1
            else:
                self._same_turn_binding_unused_count += 1

    def record_abstain_before_scout(self) -> None:
        """The emission chokepoint reached constraint_abstain BEFORE any
        rescue was attempted -- the raw count spec section 30 asks for to
        answer "did generic admissibility decrease" against, over time."""
        with self._lock:
            self._abstain_before_scout_count += 1

    def record_abstain_after_scout(self) -> None:
        """The turn's FINAL outcome was still an abstention, after
        whatever rescue attempt (if any) ran."""
        with self._lock:
            self._abstain_after_scout_count += 1

    def record_abstain_rescue_attempted(self) -> None:
        with self._lock:
            self._abstain_rescue_attempted_count += 1

    def record_abstain_rescue_succeeded(self) -> None:
        with self._lock:
            self._abstain_rescue_succeeded_count += 1

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
            turn_open_latency = list(self._turn_open_latency_ms)
            interpreted_turn_latency = list(self._interpreted_turn_latency_ms)
            presence_processing_latency = list(self._presence_processing_latency_ms)
            presence_event_queue_depth = self._presence_event_queue_depth
            response_fit_pressure = list(self._response_fit_pressure)
            knowledge_gap_pressure = list(self._knowledge_gap_pressure)
            scout_dispatch_reason = dict(self._scout_dispatch_reason)
            scout_request_kind = dict(self._scout_request_kind)
            scout_backend = dict(self._scout_backend)
            same_turn_wait = list(self._same_turn_wait_ms)
            same_turn_binding_used = self._same_turn_binding_used_count
            same_turn_binding_unused = self._same_turn_binding_unused_count
            abstain_before_scout = self._abstain_before_scout_count
            abstain_after_scout = self._abstain_after_scout_count
            abstain_rescue_attempted = self._abstain_rescue_attempted_count
            abstain_rescue_succeeded = self._abstain_rescue_succeeded_count

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

            # Build 694 step 17 (spec section 30) additions.
            "turn_open_latency_ms": {
                "count": len(turn_open_latency),
                "p50": round(_percentile(turn_open_latency, 50), 2),
                "p95": round(_percentile(turn_open_latency, 95), 2),
            },
            "interpreted_turn_latency_ms": {
                "count": len(interpreted_turn_latency),
                "p50": round(_percentile(interpreted_turn_latency, 50), 2),
                "p95": round(_percentile(interpreted_turn_latency, 95), 2),
            },
            "presence_processing_latency_ms": {
                "count": len(presence_processing_latency),
                "p50": round(_percentile(presence_processing_latency, 50), 2),
                "p95": round(_percentile(presence_processing_latency, 95), 2),
            },
            "presence_event_queue_depth": presence_event_queue_depth,
            "response_fit_pressure": {
                "count": len(response_fit_pressure),
                "p50": round(_percentile(response_fit_pressure, 50), 4),
                "max": round(max(response_fit_pressure), 4) if response_fit_pressure else 0.0,
            },
            "knowledge_gap_pressure": {
                "count": len(knowledge_gap_pressure),
                "p50": round(_percentile(knowledge_gap_pressure, 50), 4),
                "max": round(max(knowledge_gap_pressure), 4) if knowledge_gap_pressure else 0.0,
            },
            "scout_dispatch_reason": scout_dispatch_reason,
            "scout_request_kind": scout_request_kind,
            "scout_backend": scout_backend,
            # binding_integration_ms is the spec's own literal field name
            # for exactly what scout_integration_ms (above, prior build)
            # already measures -- exposed under both keys rather than
            # tracked twice, so a consumer reading either name sees the
            # same underlying counter.
            "binding_integration_ms": {
                "count": len(scout_integration),
                "p50": round(_percentile(scout_integration, 50), 2),
            },
            "same_turn_wait_ms": {
                "count": len(same_turn_wait),
                "p50": round(_percentile(same_turn_wait, 50), 2),
                "p95": round(_percentile(same_turn_wait, 95), 2),
            },
            "same_turn_binding_used_count": same_turn_binding_used,
            "same_turn_binding_unused_count": same_turn_binding_unused,
            "abstain_before_scout_count": abstain_before_scout,
            "abstain_after_scout_count": abstain_after_scout,
            "abstain_rescue_attempted_count": abstain_rescue_attempted,
            "abstain_rescue_succeeded_count": abstain_rescue_succeeded,
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
