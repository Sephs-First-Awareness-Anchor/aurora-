"""Regression tests for a real, always-active production bug found while
investigating cross-test pollution flagged in #214's PR body: importing
aurora_internal.aurora_evolution_chamber (which every real boot does,
since EvolutionaryChamber is core) unconditionally monkeypatches
ConstraintGenealogyLogger.observe at the class level
(aurora_evolution_chamber.py:3877-3880, top-level module code). The
installed wrapper (make_override()'s _override() closure, and
apply_result_rewrite()'s generic/specialized branches --
aurora_internal/aurora_evolution_hook.py) could not distinguish "the
original legitimately returned None" from "no usable original was
available," so it silently replaced observe()'s own documented,
correct None return (its own contract: no consequence to attribute when
nothing measurably happened) with a large "evolved_surface_method_renamed"
reflection dict.

Confirmed actively consequential, not just theoretically wrong:
EvolutionaryChamber.tick() does `if result is not None:
self.total_relief_events += 1` right after calling the (corrupted)
observe() -- so total_relief_events was incrementing on every tick, not
just genuine relief events, on every real boot (desktop and, since #214,
Android) since this override was installed.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_evolution_hook import make_override


# ---------------------------------------------------------------------------
# Isolated unit tests against make_override() directly -- no real class,
# no import side effects, exercises the exact logic that was fixed.
# ---------------------------------------------------------------------------

def _engine_unavailable():
    return None


def test_override_preserves_legitimate_none_from_real_callable():
    """The original ran and genuinely returned None -- must stay None,
    not get replaced by the reflection stub."""
    originals = {'X.y': lambda: None}
    evolved_last = {}
    override_fn = make_override({}, originals, evolved_last, _engine_unavailable,
                                 'some_module', {}, 'export_y', 'X.y')
    assert override_fn() is None


def test_override_still_degrades_gracefully_when_target_genuinely_missing():
    """The case this fallback exists to serve: no original registered at
    all (a genuinely renamed/dropped method) -- must still return the
    reflection stub, proving the fix narrows the bug without disabling
    graceful degradation."""
    originals = {}  # no entry for this target_key at all
    evolved_last = {}
    override_fn = make_override({}, originals, evolved_last, _engine_unavailable,
                                 'some_module', {}, 'export_missing', 'SomeClass.missing_method')
    result = override_fn()
    assert result.get('reason') == 'evolved_surface_engine_unavailable'


def test_override_preserves_legitimate_none_with_a_result_producing_engine():
    """Same as the first test, but with a live (non-None) evolved-surfaces
    engine present, exercising the reflection-building + apply_result_rewrite
    path fully rather than short-circuiting on 'engine unavailable'."""
    class _FakeEngine:
        pass

    def _live_engine():
        return _FakeEngine()

    def _export_y(payload=None, **kwargs):
        return {'available': True, 'reason': 'ok', 'op_id': 'X.y', 'kind': 'reflection'}

    originals = {'X.y': lambda: None}
    evolved_last = {}
    globals_dict = {'export_y': _export_y}
    override_fn = make_override(globals_dict, originals, evolved_last, _live_engine,
                                 'some_module', {}, 'export_y', 'X.y')
    assert override_fn() is None


# ---------------------------------------------------------------------------
# Real reproduction of the exact bug found, now locked in as a regression.
# ---------------------------------------------------------------------------

def test_constraint_genealogy_observe_returns_none_after_evolution_chamber_import():
    import aurora_internal.aurora_evolution_chamber  # noqa: F401  (triggers the module-level override)
    from aurora_internal.constraint_genealogy import (
        ConstraintGenealogyLogger, PressureVec, TraceItem, GenealogyConfig,
    )

    scratch = tempfile.mkdtemp(prefix="aurora_evo_hook_none_")
    try:
        genealogy = ConstraintGenealogyLogger(run_id="t", config=GenealogyConfig(), output_dir=scratch)
        zero = PressureVec(X=0.0, T=0.0, N=0.0, B=0.0, A=0.0)
        result = genealogy.observe(
            pressure_before=zero,
            trace=[TraceItem(kind="ABILITY", id="X:A")],
            pressure_after=zero,
        )
        assert result is None, (
            f"observe() should return None for a non-relief tick, got: {result!r}"
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# ---------------------------------------------------------------------------
# Real-boot integration: the concrete, demonstrated-wrong behavior this fix
# corrects -- total_relief_events must not inflate on every tick.
# ---------------------------------------------------------------------------

def test_total_relief_events_does_not_inflate_on_every_tick():
    scratch = tempfile.mkdtemp(prefix="aurora_relief_count_")
    try:
        shutil.copytree(
            os.path.join(REPO_ROOT, "aurora_state"),
            os.path.join(scratch, "aurora_state"),
        )
        import aurora as A

        systems = A.boot_aurora(state_dir=os.path.join(scratch, "aurora_state"), verbose=False)
        systems["_session_turn_buffer"] = []

        chamber = systems.get("chamber")
        assert chamber is not None
        events_before = chamber.total_relief_events

        # Two turns so self._prev_pressure is not None on the second call to
        # tick() -- the exact condition that triggers genealogy.observe().
        A.process_external_user_turn(
            systems, "Hi Aurora, how are you doing today?",
            source_label="relief_count_test_1",
        )
        A.process_external_user_turn(
            systems, "That's good to hear.",
            source_label="relief_count_test_2",
        )

        events_after = chamber.total_relief_events
        ticks_run = chamber.total_ticks if hasattr(chamber, "total_ticks") else chamber.tick_count
        # Before the fix, every tick after the first incremented
        # total_relief_events unconditionally (the corrupted observe()
        # always returned non-None). After the fix, relief events should
        # only be counted on genuine relief -- almost certainly not on
        # every single one of the ticks this real (ordinary, low-pressure)
        # exchange produced.
        assert events_after - events_before < chamber.tick_count, (
            f"total_relief_events grew by {events_after - events_before} across "
            f"{chamber.tick_count} ticks -- looks like every tick is still being "
            f"counted as a relief event"
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
