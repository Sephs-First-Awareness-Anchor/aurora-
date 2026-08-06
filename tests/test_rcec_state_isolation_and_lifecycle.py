# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Build 608: RCEC Closed-Loop Activation and Admissibility Repair -- D.
Repair shadow isolation and runtime lifecycle.

Covers: default-state file hashes/mtimes remain unchanged across a full
boot + live simulated turn + shutdown (D1/D2); shutdown_aurora() actually
stops the background daemon threads a boot starts (D3); a small repeated-
boot battery with shutdown between each call does not accumulate threads
across iterations (D4 -- the "stalled after 22 of 25 cases" symptom was
traced to unstopped ConnectivityMonitor/ThoughtBraid/CheckpointAutoSave
threads piling up across a battery with no shutdown in between).
"""
import hashlib
import os
import random
import shutil
import sys
import tempfile
import threading
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora as A  # noqa: E402 -- imported once, before any measured window below
from aurora_internal.aurora_cognitive_experience_chamber import (  # noqa: E402
    WorldGenerator,
    HiddenRuleEngine,
    ObservationBoundary,
    EpisodeTrace,
    build_episode_runtime_context,
    run_episode_step,
)

LIVE_STATE_DIR = os.path.join(REPO_ROOT, "aurora_state")


def _snapshot(state_dir: str) -> dict:
    out = {}
    for root, _dirs, files in os.walk(state_dir):
        for fn in files:
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, state_dir)
            try:
                with open(path, "rb") as handle:
                    digest = hashlib.sha256(handle.read()).hexdigest()
                out[rel] = (os.path.getmtime(path), digest)
            except OSError:
                continue
    return out


def _run_one_boot_and_turn(shadow_state_dir: str) -> None:
    systems = A.boot_aurora(state_dir=shadow_state_dir, runtime_profile="surface", verbose=False)
    try:
        world = WorldGenerator().build_world(
            seed=random.randint(1, 10_000), num_entities=3,
            entity_types=("vessel", "conduit"), connect_chain=False,
        )
        engine = HiddenRuleEngine.generate(world, rng=random.Random(1), family="direct_trigger")
        boundary = ObservationBoundary()
        trace = EpisodeTrace(episode_id="lifecycle_check", world_seed=1, rule_family=engine._rule.family, agent_id="agent_a")
        ctx = build_episode_runtime_context(systems)
        run_episode_step(trace, systems, ctx, world, engine, boundary, "agent_a")
    finally:
        A.shutdown_aurora(systems)


# ---------------------------------------------------------------------------
# D1/D2: real aurora_state/ file hashes and mtimes are unchanged by a full
# boot + live simulated turn + shutdown against an isolated shadow copy.
# ---------------------------------------------------------------------------

def test_default_state_files_unchanged_by_boot_and_live_turn():
    before = _snapshot(LIVE_STATE_DIR)

    tmp = tempfile.mkdtemp()
    try:
        shadow_state_dir = os.path.join(tmp, "aurora_state")
        shutil.copytree(LIVE_STATE_DIR, shadow_state_dir)
        _run_one_boot_and_turn(shadow_state_dir)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    time.sleep(0.5)  # let any in-flight blocking probe (up to 3s worst case) return
    after = _snapshot(LIVE_STATE_DIR)

    changed = {k for k in before if before.get(k) != after.get(k)}
    added = set(after) - set(before)
    assert not changed, f"real aurora_state/ files modified: {changed}"
    assert not added, f"real aurora_state/ files created: {added}"


# ---------------------------------------------------------------------------
# D3: shutdown_aurora() actually stops the threads a boot starts.
# ---------------------------------------------------------------------------

def test_shutdown_aurora_stops_spawned_threads():
    tmp = tempfile.mkdtemp()
    try:
        shadow_state_dir = os.path.join(tmp, "aurora_state")
        shutil.copytree(LIVE_STATE_DIR, shadow_state_dir)

        before_threads = {t.name for t in threading.enumerate()}
        systems = A.boot_aurora(state_dir=shadow_state_dir, runtime_profile="surface", verbose=False)
        after_boot_threads = {t.name for t in threading.enumerate()}
        spawned = after_boot_threads - before_threads
        assert spawned, "expected boot_aurora() to start at least one background thread in this environment"

        A.shutdown_aurora(systems)
        time.sleep(4.0)  # the connectivity monitor's in-flight probe can block up to 3s
        after_shutdown_threads = {t.name for t in threading.enumerate()}
        still_alive = spawned & after_shutdown_threads
        # CheckpointAutoSave now waits on a threading.Event (Build 608
        # D3/D4 fix to aurora_checkpoint.py) rather than a plain
        # time.sleep(300) -- stop_auto_save() wakes it immediately instead
        # of leaving it asleep for up to 5 minutes. All three threads a
        # boot starts must have actually exited by now.
        assert not still_alive, f"threads still alive after shutdown: {still_alive}"

        checkpoint = systems.get("checkpoint")
        if checkpoint is not None:
            assert getattr(checkpoint, "_running", None) is False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_shutdown_aurora_is_idempotent_and_safe_on_unbooted_systems():
    A.shutdown_aurora({})  # never booted
    A.shutdown_aurora({"not": "a real systems dict from boot_aurora"})
    # No exception is the assertion.


# ---------------------------------------------------------------------------
# D4: a repeated-boot battery with shutdown() between each call does not
# accumulate threads across iterations -- the root cause traced for the
# "stalled after 22 of 25 cases" symptom (unstopped ConnectivityMonitor/
# ThoughtBraid/CheckpointAutoSave threads piling up with no shutdown
# in between). A smaller N here (not the full 25) keeps this test's own
# runtime reasonable while still proving the accumulation pattern is gone;
# a full 25-iteration battery was run manually for this directive's live
# verification (see the commit message / directive summary).
# ---------------------------------------------------------------------------

def test_repeated_boot_with_shutdown_does_not_accumulate_threads():
    """A SINGLE baseline captured once before the whole battery, checked
    after every iteration -- a per-iteration baseline (re-measured fresh
    each time) would silently absorb real accumulation into an
    ever-rising "baseline" instead of catching it, which is exactly the
    mistake an earlier version of this test made."""
    baseline_thread_count = threading.active_count()
    thread_counts = []
    for iteration in range(8):
        tmp = tempfile.mkdtemp()
        try:
            shadow_state_dir = os.path.join(tmp, "aurora_state")
            shutil.copytree(LIVE_STATE_DIR, shadow_state_dir)
            _run_one_boot_and_turn(shadow_state_dir)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        time.sleep(0.3)
        thread_counts.append(threading.active_count())

    slack = [count - baseline_thread_count for count in thread_counts]
    # A trend growing with iteration index is the actual accumulation
    # signature (matches the traced "stalled after 22 of 25 cases" cause);
    # a small constant slack across all iterations is fine.
    assert max(slack) <= 2, f"thread count did not return near baseline: slack per iteration = {slack}"
    assert slack[-1] <= slack[0] + 1, f"slack is trending upward across the battery: {slack}"
