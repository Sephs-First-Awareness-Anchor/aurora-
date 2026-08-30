"""Regression + integration tests for EvolutionaryChamber.tick() finally
getting a live driveshaft in _run_live_response_turn -- the same
"dormant computation" defect already fixed for IVMLattice.tick() in
#210/#211, applied to genealogy fossilization/link-promotion.

chamber.tick() spends a real energy budget and can permanently disable
itself (self._alive=False) on a Non-Comp breach, so unlike the lattice
fix this needed real gating, not just a bare call. Two governor signals
are combined:
  - RuntimeConstraintGovernor.evaluate_task("evo_tick", ...) for resource
    admissibility (memory/load/disk pressure).
  - RuntimeConstraintGovernor.recommended_sleep(...) as the MINIMUM
    interval between live-path ticks -- discovered empirically (not
    assumed) that evaluate_task's own "maintenance multiplier" makes an
    established routine CHEAPER to keep running, never harder, so it does
    NOT provide temporal pacing on its own. recommended_sleep() is the
    same N/T-budget-derived value (15/20/30s) that already paces
    aurora_daemon.py's own outer loop -- reused here rather than
    inventing a new interval.
"""
from __future__ import annotations

import inspect
import os
import shutil
import sys
import tempfile
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_runtime_constraint_governor import RuntimeConstraintGovernor


# ---------------------------------------------------------------------------
# Governor semantics, verified directly (not assumed) -- these lock in the
# corrected understanding that shaped the gating design.
# ---------------------------------------------------------------------------

def _fresh_governor():
    scratch = tempfile.mkdtemp(prefix="aurora_governor_semantics_")
    return RuntimeConstraintGovernor(scratch)


def test_evaluate_task_does_not_by_itself_block_immediate_repeats():
    """evaluate_task("evo_tick", ...) is a resource-admissibility check, not
    a cadence gate: its "maintenance multiplier" makes an established
    routine CHEAPER to keep running (lower floor), never harder. A second
    call immediately after note_task_run() must NOT be blocked by
    evaluate_task alone under healthy resource conditions -- this is why
    the live call site also needs recommended_sleep()-based interval
    gating, verified separately below."""
    gov = _fresh_governor()
    systems = {}
    d1 = gov.evaluate_task("evo_tick", systems, heat="medium", quiet=False, state_write_lock=False)
    assert d1.get("allowed") is True
    gov.note_task_run("evo_tick")
    d2 = gov.evaluate_task("evo_tick", systems, heat="medium", quiet=False, state_write_lock=False)
    assert d2.get("allowed") is True
    assert d2.get("floor", 1.0) <= d1.get("floor", 0.0), (
        "the maintenance multiplier should make the floor easier, not harder, "
        "for a recently-run task"
    )


def test_recommended_sleep_matches_daemon_cadence_default():
    """15.0s is the healthy-conditions default -- the same value
    aurora_daemon.py's own outer loop uses (its comment: '15s loop
    iterations'). Locks in the number the live-path interval gate relies on."""
    gov = _fresh_governor()
    assert gov.recommended_sleep({}, heat="medium") == 15.0


# ---------------------------------------------------------------------------
# Source-order check (mirrors tests/test_rw6c_track1_wiring.py's and
# tests/test_ivm_lattice_live_driveshaft.py's methodology): confirm the new
# call site exists, in the Subsurface-safe zone, after on_surface_ready.
# ---------------------------------------------------------------------------

def test_live_response_turn_calls_chamber_tick_after_surface_ready():
    import aurora

    source = inspect.getsource(aurora._run_live_response_turn)
    surface_ready_idx = source.index("on_surface_ready(resp_A)")
    chamber_tick_idx = source.index("_chamber_live.tick()")
    evaluate_task_idx = source.index('evaluate_task(\n                    "evo_tick"')
    recommended_sleep_idx = source.index("recommended_sleep(systems")

    assert chamber_tick_idx > surface_ready_idx, (
        "chamber.tick() must run after on_surface_ready(resp_A), not before -- "
        "it must never be able to delay or alter the delivered response"
    )
    assert recommended_sleep_idx < chamber_tick_idx, (
        "the interval gate must be checked before ticking, not after"
    )
    assert evaluate_task_idx < chamber_tick_idx, (
        "the resource-admissibility gate must be checked before ticking"
    )


# ---------------------------------------------------------------------------
# Real-boot integration: proves both gates AND the wiring work end-to-end.
# ---------------------------------------------------------------------------

def test_real_turns_advance_chamber_tick_once_then_hold_within_interval():
    scratch = tempfile.mkdtemp(prefix="aurora_chamber_driveshaft_")
    try:
        shutil.copytree(
            os.path.join(REPO_ROOT, "aurora_state"),
            os.path.join(scratch, "aurora_state"),
        )
        import aurora as A

        systems = A.boot_aurora(state_dir=os.path.join(scratch, "aurora_state"), verbose=False)
        systems["_session_turn_buffer"] = []

        chamber = systems.get("chamber")
        assert chamber is not None, "boot_aurora() did not register systems['chamber']"
        ticks_before = chamber.tick_count

        result1 = A.process_external_user_turn(
            systems, "Hi Aurora, how are you doing today?",
            source_label="chamber_driveshaft_test_1",
        )
        assert result1.get("resp_B") is not None

        ticks_after_first = chamber.tick_count
        assert ticks_after_first > ticks_before, (
            "EvolutionaryChamber.tick() did not run during a real live turn under "
            "healthy resource conditions -- the driveshaft is disconnected again"
        )
        assert "_last_chamber_tick_time" in systems

        # Immediately-following second turn, well within the 15s minimum
        # interval -- the tick must be withheld, not fired again.
        result2 = A.process_external_user_turn(
            systems, "That's good to hear.",
            source_label="chamber_driveshaft_test_2",
        )
        assert result2.get("resp_B") is not None
        assert chamber.tick_count == ticks_after_first, (
            "chamber.tick() ran again inside the minimum interval -- the "
            "recommended_sleep()-based gate did not hold"
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
