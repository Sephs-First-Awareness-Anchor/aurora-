# Authors: Sunni (Sir) Morningstar & Ceph
"""Regression tests for the live phone occurrence Presence barrier.

Aurora's canonical turn pipeline already calls
SubsurfacePresenceRuntime.wait_for_turn_phase() after publishing turn_open
and interpreted_turn. Before the 2026-09-10 correction the runtime did not
implement that method, so aurora.py's hasattr() guard always skipped the
bounded wait and Surface raced the runtime's 150ms file poll.

These tests deliberately give the runtime a very long poll interval. A
successful bounded wait therefore proves the caller woke the independent
runtime thread instead of merely getting lucky on the periodic poll.
"""
from __future__ import annotations

import threading
import time

from aurora_internal.dual_strata.subsurface_presence import (
    write_interpreted_turn,
    write_turn_open,
)
from aurora_internal.dual_strata.subsurface_presence_runtime import (
    SubsurfacePresenceRuntime,
)


def _wait_for_initial_tick(runtime: SubsurfacePresenceRuntime, timeout: float = 1.0) -> None:
    deadline = time.monotonic() + timeout
    while runtime.tick_count < 1 and time.monotonic() < deadline:
        time.sleep(0.005)
    assert runtime.tick_count >= 1


def test_turn_open_wait_wakes_runtime_instead_of_waiting_for_poll(tmp_path):
    runtime = SubsurfacePresenceRuntime(
        tmp_path,
        poll_interval_s=5.0,
        metrics_write_interval_s=60.0,
    )
    runtime.start()
    try:
        _wait_for_initial_tick(runtime)
        before_ticks = runtime.tick_count
        write_turn_open(tmp_path, turn_id="turn-open-fast", raw_input="hello")

        started = time.monotonic()
        frame = runtime.wait_for_turn_phase("turn-open-fast", "turn_open", timeout=0.75)
        elapsed = time.monotonic() - started

        assert frame is not None
        assert frame["turn_id"] == "turn-open-fast"
        assert frame.get("turn_open_at")
        assert runtime.tick_count > before_ticks
        # The backstop poll is 5 seconds. Returning inside this bounded
        # window demonstrates the wake path, not periodic polling.
        assert elapsed < 0.75
    finally:
        runtime.stop()


def test_interpreted_wait_reaches_the_same_turn_barrier(tmp_path):
    runtime = SubsurfacePresenceRuntime(
        tmp_path,
        poll_interval_s=5.0,
        metrics_write_interval_s=60.0,
    )
    runtime.start()
    try:
        _wait_for_initial_tick(runtime)
        write_turn_open(tmp_path, turn_id="turn-interpreted", raw_input="what is happening")
        open_frame = runtime.wait_for_turn_phase("turn-interpreted", "turn_open", timeout=0.75)
        assert open_frame is not None

        write_interpreted_turn(
            tmp_path,
            turn_id="turn-interpreted",
            interpreted_meaning="the user is asking about the current event",
            inferred_purpose="understand",
            interpretation_confidence=0.82,
        )
        frame = runtime.wait_for_turn_phase("turn-interpreted", "interpreted", timeout=0.75)

        assert frame is not None
        assert frame["turn_id"] == "turn-interpreted"
        assert frame.get("turn_open_at")
        assert frame.get("interpreted_at")
        assert frame.get("interpreted_meaning") == "the user is asking about the current event"
    finally:
        runtime.stop()


def test_wait_never_runs_presence_tick_on_surface_thread(tmp_path):
    runtime = SubsurfacePresenceRuntime(
        tmp_path,
        poll_interval_s=5.0,
        metrics_write_interval_s=60.0,
    )
    caller_thread = threading.get_ident()
    tick_threads = []
    real_tick = runtime.tick

    def observed_tick():
        tick_threads.append(threading.get_ident())
        return real_tick()

    runtime.tick = observed_tick  # type: ignore[method-assign]
    runtime.start()
    try:
        _wait_for_initial_tick(runtime)
        write_turn_open(tmp_path, turn_id="turn-thread-separation", raw_input="hi")
        frame = runtime.wait_for_turn_phase("turn-thread-separation", "turn_open", timeout=0.75)

        assert frame is not None
        assert tick_threads
        assert all(thread_id != caller_thread for thread_id in tick_threads)
    finally:
        runtime.stop()


def test_missing_turn_times_out_without_fabricating_presence(tmp_path):
    runtime = SubsurfacePresenceRuntime(
        tmp_path,
        poll_interval_s=5.0,
        metrics_write_interval_s=60.0,
    )
    runtime.start()
    try:
        _wait_for_initial_tick(runtime)
        frame = runtime.wait_for_turn_phase("turn-that-does-not-exist", "turn_open", timeout=0.05)
        assert frame is None
    finally:
        runtime.stop()


def test_stop_interrupts_long_backstop_sleep(tmp_path):
    runtime = SubsurfacePresenceRuntime(
        tmp_path,
        poll_interval_s=5.0,
        metrics_write_interval_s=60.0,
    )
    runtime.start()
    _wait_for_initial_tick(runtime)

    started = time.monotonic()
    runtime.stop(timeout=0.75)
    elapsed = time.monotonic() - started

    assert not runtime.is_running()
    assert elapsed < 0.75
