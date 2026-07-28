# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
FIX-A054 (2026-07-28): the classroom divergence cold-start bug.

R1.1/R1.2 (2026-07-15) fixed entity resolutions from a dead constant
(avg_valence=0.0, avg_intensity=0.3333...) to genuinely rich, varied
per-entity state. R1.4 (same day) fixed a second cause -- ClassroomSession
sharing SimulationSession's own DivergenceTracker, whose first-vs-last
snapshot comparison never had matching keys against episode-shaped
captures. Both fixes are real and verified working (this file's own
tests, plus a live full-boot run: see known_fixes_registry.md).

But a THIRD cause survived both fixes and kept divergence_score at 0.0
in production for months: DivergenceTracker.current_divergence requires
TWO captured snapshots before it computes anything
(_compute_divergence()'s own `len(self._snapshots) < 2` guard) -- with a
freshly-constructed tracker, lesson 1 of every session was therefore
STRUCTURALLY forced to 0.0, regardless of how different the two entities'
resolved perspectives actually were. Because the flat-divergence watchdog
(FIX-A019) reads the PERSISTED classroom_log.jsonl tail, and lesson 1's
forced zero got written to that log before lesson 2 of the same
run_targeted_curriculum() batch ever got a chance to execute, no session
has reached lesson 2 in the live scheduled pipeline since the watchdog
landed -- so R1.1/R1.2/R1.4's real fixes never got the chance to prove
themselves against real, persisted evidence.

Fix: ClassroomSession.__init__ seeds the dedicated tracker with ONE
baseline snapshot, built from the freshly-spawned entities' own real
pre-lesson state (zero compressed_experiences -> avg_valence/avg_intensity
default to 0.0 via collapse_to_parent()'s own "empty" contract, not an
injected constant). Lesson 1 then has a real baseline to diverge from
immediately.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_classroom import ClassroomSession  # noqa: E402
from aurora_simulation_engine import SimulationEngine, DivergenceTracker  # noqa: E402


_EXPECTED_KEYS = {"entity_0_valence", "entity_0_intensity", "entity_1_valence", "entity_1_intensity"}


def test_construction_seeds_exactly_one_baseline_snapshot(tmp_path):
    engine = SimulationEngine(state_dir=str(tmp_path))
    systems = {"state_dir": str(tmp_path)}
    session = ClassroomSession(engine, systems, state_dir=str(tmp_path))

    assert len(session._divergence_tracker._snapshots) == 1


def test_baseline_snapshot_matches_a_fresh_entitys_real_zero_experience_state(tmp_path):
    """Not an injected constant -- the freshly-spawned entities genuinely
    have zero compressed_experiences yet, so collapse_to_parent() returns
    {'empty': True} with no avg_valence/avg_intensity keys at all. The
    baseline must derive from that real contract via .get(..., 0.0), the
    same pattern run_lesson() itself uses for the real per-lesson capture."""
    engine = SimulationEngine(state_dir=str(tmp_path))
    systems = {"state_dir": str(tmp_path)}
    session = ClassroomSession(engine, systems, state_dir=str(tmp_path))

    entity_a, entity_b = (engine.entities[eid] for eid in session.entity_ids)
    assert entity_a.compressed_experiences == []
    assert entity_b.compressed_experiences == []
    fresh_collapse = entity_a.collapse_to_parent()
    assert fresh_collapse.get("empty") is True
    assert "avg_valence" not in fresh_collapse

    baseline = session._divergence_tracker._snapshots[0]
    assert baseline == {k: 0.0 for k in _EXPECTED_KEYS}


def test_baseline_snapshot_shape_matches_real_lesson_capture_shape(tmp_path):
    """The dedicated tracker's first-vs-last diff only sums keys present in
    BOTH snapshots (the exact mechanism R1.4 fixed for the episode-shaped
    sharing bug) -- if the baseline's keys didn't match a real lesson's
    keys, this fix would silently reintroduce that same class of bug."""
    engine = SimulationEngine(state_dir=str(tmp_path))
    systems = {"state_dir": str(tmp_path)}
    session = ClassroomSession(engine, systems, state_dir=str(tmp_path))

    baseline_keys = set(session._divergence_tracker._snapshots[0].keys())
    assert baseline_keys == _EXPECTED_KEYS


def test_lesson_one_is_no_longer_structurally_forced_to_zero(tmp_path):
    """The actual bug fix, verified deterministically: with a real second
    (non-baseline) snapshot captured, current_divergence computes a real
    first-vs-last diff instead of hitting the `len(snapshots) < 2` guard.
    Bypasses run_lesson()'s own randomness (episode content, entity
    resolution) by capturing a controlled, known-different snapshot
    directly -- the same divergence_stats shape run_lesson() builds."""
    engine = SimulationEngine(state_dir=str(tmp_path))
    systems = {"state_dir": str(tmp_path)}
    session = ClassroomSession(engine, systems, state_dir=str(tmp_path))

    # Before this fix: capturing ONE snapshot (lesson 1's real capture)
    # left len(_snapshots) == 1, and _compute_divergence() hard-guards
    # "< 2" to 0.0 -- structurally, regardless of the values below.
    session._divergence_tracker.capture({
        "entity_0_valence": 0.6, "entity_0_intensity": 0.8,
        "entity_1_valence": 0.1, "entity_1_intensity": 0.3,
    })

    assert len(session._divergence_tracker._snapshots) == 2
    # first-vs-last: baseline (all 0.0) vs this capture -- diff is exactly
    # the sum of the captured values themselves, divided by key count.
    expected = (0.6 + 0.8 + 0.1 + 0.3) / 4.0
    assert abs(session._divergence_tracker.current_divergence - expected) < 1e-9
    assert session._divergence_tracker.current_divergence > 0.0


def test_divergence_tracker_itself_still_needs_two_snapshots():
    """Regression guard on the general-purpose class this fix does NOT
    touch: DivergenceTracker itself is unchanged -- a tracker with zero or
    one capture still correctly reads 0.0. The fix is scoped entirely to
    ClassroomSession seeding its OWN dedicated instance at construction,
    not to DivergenceTracker's own semantics (which SimulationSession
    also relies on elsewhere)."""
    tracker = DivergenceTracker()
    assert tracker.current_divergence == 0.0

    tracker.capture({"a": 5.0})
    assert len(tracker._snapshots) == 1
    assert tracker.current_divergence == 0.0

    tracker.capture({"a": 8.0})
    assert len(tracker._snapshots) == 2
    assert tracker.current_divergence == 3.0
