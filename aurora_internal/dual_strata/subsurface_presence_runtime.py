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

Occurrence-barrier correction (2026-09-10): aurora.py already calls
runtime.wait_for_turn_phase(turn_id, phase, timeout=...) after publishing
turn_open/interpreted_turn, but this runtime previously exposed no such
method. The hasattr() guard therefore always failed and Surface immediately
fell through to a file read, racing this thread's 150ms poll. The runtime
now exposes the missing barrier. Waiting Surface nudges this independent
thread awake and blocks only until the requested phase is integrated (or
its existing bounded timeout expires). The periodic poll remains the
cross-process/backstop path; no cognitive work is moved onto Surface.
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
    read_presence_frame,
    write_heartbeat,
)

# Spec section 4 responsiveness targets are <250ms; polling well under
# that (not AT it) leaves headroom for the actual integration work each
# tick does. The poll is now a backstop: in-process Surface waits wake the
# runtime immediately through _wake_event.
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
        self._wake_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.last_tick_at: float = 0.0
        self.last_tick_error: str = ""
        self.tick_count: int = 0

        # One condition protects only the tick-generation signal. It never
        # protects cognitive state or the presence files themselves. A waiter
        # observes a generation, wakes this thread, and sleeps until a later
        # integration cycle completes, avoiding active polling on Surface.
        self._phase_condition = threading.Condition()
        self._tick_generation: int = 0

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
        self._wake_event.clear()
        self._thread = threading.Thread(
            target=self._run, name="subsurface-presence-runtime", daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop_event.set()
        # _run now sleeps on _wake_event rather than _stop_event so a stop
        # must wake it explicitly; otherwise a custom long poll interval
        # could make stop() wait unnecessarily.
        self._wake_event.set()
        with self._phase_condition:
            self._phase_condition.notify_all()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        self._thread = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @staticmethod
    def _frame_has_phase(frame: Any, turn_id: str, phase: str) -> bool:
        """Return whether one persisted PresenceFrame proves phase landed.

        turn_open/interpreted are the two bounded waits used by aurora.py.
        Unknown/future phase names conservatively require only a same-turn
        frame rather than inventing a new semantic completion criterion.
        """
        if not isinstance(frame, dict):
            return False
        if str(frame.get("turn_id", "") or "") != str(turn_id or ""):
            return False
        phase_key = str(phase or "").strip().lower()
        if phase_key == "turn_open":
            return bool(frame.get("turn_open_at"))
        if phase_key == "interpreted":
            return bool(frame.get("interpreted_at"))
        return True

    def wait_for_turn_phase(
        self,
        turn_id: str,
        phase: str,
        *,
        timeout: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        """Wake Subsurface and wait for this turn's requested phase.

        This is the missing synchronization joint aurora.py already probes
        for with hasattr(). The caller never performs tick() itself: Surface
        only sets _wake_event, while this runtime's independent daemon thread
        does the actual integration. The wait is condition-based and bounded
        by the caller's existing timeout. If the runtime is not running, the
        newest matching file-backed frame is returned if already available;
        otherwise None lets aurora.py keep its existing fallback behavior.
        """
        wanted_turn = str(turn_id or "")
        if not wanted_turn:
            return None
        budget = max(0.0, float(timeout or 0.0))
        deadline = time.monotonic() + budget

        while True:
            # Hold the condition while checking the file and capturing the
            # generation number. _run increments that generation under the
            # same condition after each tick, preventing a lost notification
            # between "not ready" and the wait below.
            with self._phase_condition:
                try:
                    frame = read_presence_frame(self.state_dir)
                except Exception as _aurora_boundary_exc:
                    _aurora_record_exception_from_locals(
                        locals(), module=__name__,
                        operation="exception_handler:aurora_internal/dual_strata/subsurface_presence_runtime.py:wait_for_turn_phase:read",
                        exc=_aurora_boundary_exc,
                        context={"function": "SubsurfacePresenceRuntime.wait_for_turn_phase", "source_file": "aurora_internal/dual_strata/subsurface_presence_runtime.py"},
                    )
                    frame = None
                if self._frame_has_phase(frame, wanted_turn, phase):
                    return dict(frame)

                remaining = deadline - time.monotonic()
                if remaining <= 0.0 or not self.is_running() or self._stop_event.is_set():
                    return None

                observed_generation = self._tick_generation
                # The event is the in-process fast path. It wakes the daemon
                # from its normal 150ms backstop sleep without doing any of
                # that daemon's work on this Surface thread.
                self._wake_event.set()
                self._phase_condition.wait_for(
                    lambda: self._tick_generation != observed_generation or self._stop_event.is_set(),
                    timeout=remaining,
                )

            if self._stop_event.is_set():
                return None

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
            with self._phase_condition:
                self._tick_generation += 1
                self._phase_condition.notify_all()
            if self._stop_event.is_set():
                break
            # Periodic polling remains the cross-process and idle backstop;
            # wait_for_turn_phase() can interrupt this sleep immediately.
            self._wake_event.wait(self.poll_interval_s)
            self._wake_event.clear()

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
