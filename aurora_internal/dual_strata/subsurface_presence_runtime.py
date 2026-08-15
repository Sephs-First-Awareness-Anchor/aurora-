"""
SubsurfacePresenceRuntime (Aurora Build 694, step 4).

Presence processing must not run on the 15-30s autonomous daemon
sleep -- confirmed directly against source: aurora_daemon.py's main
loop calls RuntimeConstraintGovernor.recommended_sleep() (15.0/20.0/
30.0 depending on host pressure) once at the very bottom of its while
loop, and every turn-event/Scout-evidence consumption call in that loop
only runs once per that same slow iteration. A heartbeat thread proves
the PROCESS is alive through that; it does not prove Subsurface is
cognitively participating in the CURRENT turn.

This is a dedicated, lightweight, independently-scheduled runtime --
its own thread, its own short poll interval, no relationship to the
governor's sleep recommendation at all. Its only responsibilities:

    receive live turn events        (subsurface_turn_events.json)
    maintain current PresenceFrame  (subsurface_presence_frame.json)
    consume Scout reports and integrate EvidenceBindings
    (evaluate Scout dispatch pressure / signal Surface -- extension
     points other Build 694 steps fill in: step 10 wires dispatch
     pressure evaluation; step 14 wires the Surface-facing signal)

It must NEVER perform Dream, genealogy evolution, corpus training,
autonomous research, memory consolidation, or a full cognitive boot --
structurally true here because this module only ever imports
subsurface_presence.py's file-based primitives and
subsurface_scout_bridge.consume_scout_reports() (itself already state_
dir-parameterized and boot-free), nothing from aurora.py or
aurora_daemon.py.

Two hosts start this runtime, both against an ALREADY-booted Aurora --
neither starts a second one:
    - aurora_bridge.initialize() (Android, step 5) -- the ONLY presence
      processing on that path, since Android never runs aurora_daemon.py
      at all.
    - aurora_daemon.run() (desktop) -- an ADDITIONAL fast path alongside
      the existing slow main-loop consumption, which stays in place
      unchanged as a redundant backstop rather than being torn out;
      double-processing the same turn_events batch is harmless (re-
      integrating the same interpreted_turn event just rewrites the
      presence frame with the same values) and safer than risking a
      regression in already-proven main-loop behavior.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals

import threading
import time
from typing import Any, Callable, Dict, List, Optional

from aurora_internal.dual_strata.subsurface_presence import (
    read_and_clear_turn_events,
    integrate_turn_event,
    write_heartbeat,
)

# Spec section 4 responsiveness targets are <250ms; polling well under
# that (not AT it) leaves headroom for the actual integration work each
# tick does.
DEFAULT_POLL_INTERVAL_S = 0.15


class SubsurfacePresenceRuntime:
    """One dedicated thread. start()/stop() are idempotent and safe to
    call from any thread; the runtime never touches cognitive state,
    only the file-based presence/Scout primitives, so nothing here needs
    Android's aurora_bridge._lock (see step 25)."""

    def __init__(
        self,
        state_dir: Any,
        *,
        poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
        on_binding_change: Optional[Callable[[List[Any]], None]] = None,
        metrics_write_interval_s: float = 2.0,
    ):
        self.state_dir = state_dir
        self.poll_interval_s = max(0.02, float(poll_interval_s or DEFAULT_POLL_INTERVAL_S))
        # Step 14 extension point: called with the list of EvidenceBindings
        # accepted this tick, so a Surface-side waiter can be signaled the
        # instant current-turn evidence changes rather than polling.
        self.on_binding_change = on_binding_change
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.last_tick_at: float = 0.0
        self.last_tick_error: str = ""
        self.tick_count: int = 0

        # Build 694 step 17: this runtime holds its own long-lived
        # PresenceMetrics instance (role="presence_runtime") -- ticking
        # every ~150ms makes per-tick disk writes wasteful, so
        # write_snapshot() is throttled to metrics_write_interval_s
        # rather than called every tick.
        from aurora_internal.dual_strata.presence_metrics import PresenceMetrics
        self.metrics = PresenceMetrics(state_dir, role="presence_runtime")
        self.metrics_write_interval_s = max(0.5, float(metrics_write_interval_s or 2.0))
        self._last_metrics_write_at: float = 0.0

    def start(self) -> None:
        if self.is_running():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, name="subsurface-presence-runtime", daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        self._thread = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.tick()
                self.last_tick_error = ""
            except Exception as _aurora_boundary_exc:
                self.last_tick_error = str(_aurora_boundary_exc)
                _aurora_record_exception_from_locals(
                    locals(), module=__name__,
                    operation="exception_handler:aurora_internal/dual_strata/subsurface_presence_runtime.py:_run",
                    exc=_aurora_boundary_exc,
                    context={"function": "SubsurfacePresenceRuntime._run", "source_file": "aurora_internal/dual_strata/subsurface_presence_runtime.py"},
                )
            self.last_tick_at = time.time()
            self.tick_count += 1
            self._stop_event.wait(self.poll_interval_s)

    def tick(self) -> Dict[str, Any]:
        """One integration cycle -- also callable directly (tests,
        synchronous callers) without starting the background thread."""
        _tick_started_at = time.time()
        integrated_kinds: List[str] = []
        try:
            events = read_and_clear_turn_events(self.state_dir)
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(), module=__name__,
                operation="exception_handler:aurora_internal/dual_strata/subsurface_presence_runtime.py:tick:events",
                exc=_aurora_boundary_exc,
                context={"function": "SubsurfacePresenceRuntime.tick", "source_file": "aurora_internal/dual_strata/subsurface_presence_runtime.py"},
            )
            events = []
        # Build 694 step 17: presence_event_queue_depth -- how many turn
        # events were waiting to be integrated at the START of this tick
        # (before this tick drains them), the direct measure of whether
        # events are piling up faster than they're being consumed.
        self.metrics.set_presence_event_queue_depth(len(events))
        for event in events:
            kind = integrate_turn_event(self.state_dir, event, metrics=self.metrics)
            if kind:
                integrated_kinds.append(kind)

        accepted_bindings: List[Any] = []
        try:
            from aurora_internal.scouting.subsurface_scout_bridge import consume_scout_reports
            bindings = consume_scout_reports(self.state_dir)
            accepted_bindings = [b for b in bindings if getattr(b, "status", "") == "accepted"]
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(), module=__name__,
                operation="exception_handler:aurora_internal/dual_strata/subsurface_presence_runtime.py:tick:scout",
                exc=_aurora_boundary_exc,
                context={"function": "SubsurfacePresenceRuntime.tick", "source_file": "aurora_internal/dual_strata/subsurface_presence_runtime.py"},
            )

        if accepted_bindings and self.on_binding_change is not None:
            try:
                self.on_binding_change(accepted_bindings)
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(), module=__name__,
                    operation="exception_handler:aurora_internal/dual_strata/subsurface_presence_runtime.py:tick:notify",
                    exc=_aurora_boundary_exc,
                    context={"function": "SubsurfacePresenceRuntime.tick", "source_file": "aurora_internal/dual_strata/subsurface_presence_runtime.py"},
                )

        try:
            write_heartbeat(self.state_dir)
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(), module=__name__,
                operation="exception_handler:aurora_internal/dual_strata/subsurface_presence_runtime.py:tick:heartbeat",
                exc=_aurora_boundary_exc,
                context={"function": "SubsurfacePresenceRuntime.tick", "source_file": "aurora_internal/dual_strata/subsurface_presence_runtime.py"},
            )

        try:
            self.metrics.record_presence_processing_latency_ms((time.time() - _tick_started_at) * 1000.0)
            now = time.time()
            if now - self._last_metrics_write_at >= self.metrics_write_interval_s:
                self.metrics.write_snapshot()
                self._last_metrics_write_at = now
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(), module=__name__,
                operation="exception_handler:aurora_internal/dual_strata/subsurface_presence_runtime.py:tick:metrics",
                exc=_aurora_boundary_exc,
                context={"function": "SubsurfacePresenceRuntime.tick", "source_file": "aurora_internal/dual_strata/subsurface_presence_runtime.py"},
            )

        return {"integrated_kinds": integrated_kinds, "accepted_bindings": accepted_bindings}


def start_subsurface_presence_runtime(
    systems: Optional[Dict[str, Any]] = None,
    *,
    state_dir: Any,
    poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
    on_binding_change: Optional[Callable[[List[Any]], None]] = None,
) -> SubsurfacePresenceRuntime:
    """Module-level convenience matching the spec's own pseudocode
    naming. Operates against an ALREADY-booted Aurora -- `systems`, if
    given, is stashed on the returned runtime purely for callers that
    want to look it up later (e.g. `systems["_presence_runtime"]`); it
    is never used to construct a second Aurora instance, and the
    runtime itself never touches it."""
    runtime = SubsurfacePresenceRuntime(
        state_dir, poll_interval_s=poll_interval_s, on_binding_change=on_binding_change,
    )
    runtime.start()
    if isinstance(systems, dict):
        systems["_presence_runtime"] = runtime
    return runtime
