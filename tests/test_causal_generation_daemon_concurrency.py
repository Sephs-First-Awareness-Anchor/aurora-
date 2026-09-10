# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA DIRECTIVE -- Causal-Generation Correction, Phase 4 regression suite.

Unlike Phases 0-2 (order-dependence within a single-threaded batch loop),
this file's defect shape is REAL concurrency: aurora_acm_bridge.py's
tick-triggered threads and aurora_daemon.py's own run() loop both reach
_run_dream_burst() and _run_code_mutation_cycle() on independent
schedules, in the same process, against fixed shared file paths -- with no
in-memory state shared between them (each boots its own `systems` dict via
its own boot_aurora() call), so the only real hazard is the file I/O
itself. Confirmed live during this fix's development: the pre-fix
unlocked read-modify-write pattern lost 2 of 3 concurrent updates in a
real multi-threaded reproduction (see this file's own test below and the
commit history on this branch for the exact numbers).

These tests use REAL threading.Thread, not just shuffled call order --
the hazard here only manifests under actual concurrent execution.
"""
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora_daemon as D  # noqa: E402
from aurora_persistence_utils import PERSISTENCE_LOCK, atomic_write_json  # noqa: E402


# ============================================================================
# _run_dream_burst(): PERSISTENCE_LOCK around the projection read-modify-write
# ============================================================================

def test_dream_burst_projection_writes_are_mutually_exclusive():
    """Calls the REAL _run_dream_burst() concurrently (empty systems dict --
    confirmed live to fail gracefully past the missing subsystems and still
    reach the projection-write section every time) and spies on
    atomic_write_json to record each call's [start, end) interval. If the
    fix's lock is doing its job, no two intervals can overlap -- proving
    true mutual exclusion at the exact critical section that used to race,
    not just "the test happened to pass this time"."""
    tmpdir = tempfile.mkdtemp()
    original_path = D._SUBSURFACE_PROJECTION
    D._SUBSURFACE_PROJECTION = Path(tmpdir) / "subsurface_projection.json"

    intervals = []
    real_atomic_write = D.atomic_write_json

    def spy_atomic_write(path, data, **kwargs):
        start = time.time()
        time.sleep(0.1)  # widen the critical section so a race WOULD show
        result = real_atomic_write(path, data, **kwargs)
        intervals.append((start, time.time()))
        return result

    D.atomic_write_json = spy_atomic_write
    try:
        threads = [threading.Thread(target=D._run_dream_burst, args=({},))
                   for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        D.atomic_write_json = real_atomic_write
        D._SUBSURFACE_PROJECTION = original_path

    assert len(intervals) == 3, "all three concurrent calls must reach the write"
    intervals.sort()
    overlapping = any(
        intervals[i][1] > intervals[i + 1][0] for i in range(len(intervals) - 1)
    )
    assert not overlapping, (
        "concurrent dream-burst projection writes overlapped -- "
        "PERSISTENCE_LOCK is not providing mutual exclusion"
    )


def test_persistence_lock_pattern_prevents_lost_updates_under_real_race():
    """Standalone reproduction of the exact pattern _run_dream_burst() now
    uses (read under PERSISTENCE_LOCK -> modify -> atomic_write_json,
    still under the same lock) versus the pre-fix pattern (same shape, no
    lock) -- both run with 3 real concurrent threads against the same
    file. Confirmed live during development: the unlocked version lost 2
    of 3 updates (only the last writer's key survived); the locked version
    keeps all 3."""
    def race(tmp_path: Path, use_lock: bool, n: int):
        def worker(i):
            ctx = PERSISTENCE_LOCK if use_lock else _NullContext()
            with ctx:
                data = {}
                if tmp_path.exists():
                    data = json.loads(tmp_path.read_text())
                time.sleep(0.05)
                data[f"thread_{i}"] = True
                if use_lock:
                    atomic_write_json(tmp_path, data)
                else:
                    tmp = str(tmp_path) + f".tmp{i}"
                    with open(tmp, "w") as f:
                        json.dump(data, f)
                    os.replace(tmp, str(tmp_path))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return json.loads(tmp_path.read_text()) if tmp_path.exists() else {}

    tmpdir = tempfile.mkdtemp()

    unlocked_result = race(Path(tmpdir) / "unlocked.json", use_lock=False, n=3)
    locked_result = race(Path(tmpdir) / "locked.json", use_lock=True, n=3)

    assert len(unlocked_result) < 3, (
        "expected the unlocked pattern to lose at least one concurrent "
        f"update (classic lost-update race); got {unlocked_result}"
    )
    assert all(f"thread_{i}" in locked_result for i in range(3)), (
        f"locked pattern must preserve every concurrent update; got {locked_result}"
    )


class _NullContext:
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


# ============================================================================
# _run_code_mutation_cycle(): dedicated non-blocking lock, skip not block
# ============================================================================

def test_code_mutation_cycle_skips_concurrent_second_trigger():
    """Two real threads both call the public _run_code_mutation_cycle()
    (the wrapper, exactly as both aurora_daemon.py's own run() loop and
    aurora_acm_bridge.py's tick-triggered thread do) with
    _run_code_mutation_cycle_impl monkeypatched to a slow stand-in.
    Confirms only ONE impl invocation happens -- the second trigger must
    be skipped, not queued behind the first (queuing would make an
    unrelated daemon loop iteration block for however long a real
    mutation cycle takes, which can include a multi-minute
    function_lineage.rebuild() -- see this fix's own comments)."""
    real_impl = D._run_code_mutation_cycle_impl
    calls = []
    first_running = threading.Event()

    def slow_impl(systems):
        first_running.set()
        time.sleep(0.3)
        calls.append("ran")

    D._run_code_mutation_cycle_impl = slow_impl
    try:
        t1 = threading.Thread(target=D._run_code_mutation_cycle, args=({},))
        t1.start()
        assert first_running.wait(timeout=2), "first call never started"
        # second trigger arrives while the first is still "running"
        D._run_code_mutation_cycle({})
        t1.join()
    finally:
        D._run_code_mutation_cycle_impl = real_impl

    assert len(calls) == 1, (
        f"expected exactly one impl invocation (second must skip, not "
        f"queue), got {len(calls)}"
    )


def test_code_mutation_cycle_second_trigger_does_not_block():
    """The skipped trigger must return promptly, not wait for the first
    to finish -- this is what makes it safe for a daemon loop iteration
    to call this without stalling on an unrelated in-flight cycle."""
    real_impl = D._run_code_mutation_cycle_impl
    first_running = threading.Event()

    def slow_impl(systems):
        first_running.set()
        time.sleep(1.0)

    D._run_code_mutation_cycle_impl = slow_impl
    try:
        t1 = threading.Thread(target=D._run_code_mutation_cycle, args=({},))
        t1.start()
        assert first_running.wait(timeout=2), "first call never started"

        started = time.time()
        D._run_code_mutation_cycle({})  # should skip immediately
        elapsed = time.time() - started

        t1.join()
    finally:
        D._run_code_mutation_cycle_impl = real_impl

    assert elapsed < 0.5, (
        f"second trigger took {elapsed:.2f}s -- it blocked instead of skipping"
    )


def test_code_mutation_cycle_runs_normally_when_not_contended():
    """Sanity check: with no concurrent call in flight, the wrapper must
    still actually invoke the real implementation exactly once -- the
    lock must gate concurrency, not functionality."""
    real_impl = D._run_code_mutation_cycle_impl
    calls = []
    D._run_code_mutation_cycle_impl = lambda systems: calls.append(systems)
    try:
        marker = {"probe": True}
        D._run_code_mutation_cycle(marker)
    finally:
        D._run_code_mutation_cycle_impl = real_impl

    assert calls == [{"probe": True}]
