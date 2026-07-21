# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Phase R1.3 of the Semantic Plateau Remediation Directive (2026-07-15):
aurora_classroom.py's perspective-pair rotation and flat-divergence
watchdog (FIX-A019).

Before this fix, ClassroomSession froze one i_state pair ("i_can",
"i_saw" by default) at construction and reused it for every lesson for
the entity's entire lifetime -- one of the compounding causes behind the
452/452 identity-failure signal documented in classroom_log.jsonl. These
tests hold: (1) the dimension -> pair map covers every default candidate
dimension and actually reaches all ten canonical i_state poles across the
curriculum, and (2) the watchdog halts the classroom once the persisted
log shows 20 consecutive zero-divergence lessons, derived from the log
file itself (not in-memory state) so it trips correctly across separate
scheduled runs too.
"""
import json
import time

import pytest

from aurora_classroom import (
    ClassroomHaltedError,
    ClassroomSession,
    _DEFAULT_CANDIDATE_DIMENSIONS,
    _DEFAULT_I_STATE_PAIR,
    _DIMENSION_I_STATE_PAIRS,
    _FLAT_DIVERGENCE_HALT_THRESHOLD,
    _consecutive_zero_divergence_tail,
    acknowledge_flat_divergence_watchdog,
)
from aurora_simulation_engine import SimulationEngine

_ALL_TEN_POLES = {
    "i_is", "i_isnt", "i_can", "i_cannot", "i_do", "i_donot",
    "i_saw", "i_sought", "i_did", "i_didnt",
}


def test_every_default_candidate_dimension_has_a_pair():
    for dim in _DEFAULT_CANDIDATE_DIMENSIONS:
        assert dim in _DIMENSION_I_STATE_PAIRS, dim
        pair = _DIMENSION_I_STATE_PAIRS[dim]
        assert len(pair) == 2
        assert pair[0] != pair[1]


def test_pairs_use_only_valid_canonical_i_states():
    for dim, pair in _DIMENSION_I_STATE_PAIRS.items():
        for i_state in pair:
            assert i_state in _ALL_TEN_POLES, (dim, i_state)


def test_all_ten_poles_see_use_across_the_curriculum():
    used = set()
    for pair in _DIMENSION_I_STATE_PAIRS.values():
        used.update(pair)
    assert used == _ALL_TEN_POLES


def test_default_pair_is_a_valid_fallback():
    assert _DEFAULT_I_STATE_PAIR[0] in _ALL_TEN_POLES
    assert _DEFAULT_I_STATE_PAIR[1] in _ALL_TEN_POLES


def test_run_lesson_mutates_entity_i_state_per_dimension(tmp_path):
    engine = SimulationEngine(state_dir=str(tmp_path))
    systems = {"state_dir": str(tmp_path)}
    session = ClassroomSession(engine, systems, state_dir=str(tmp_path))

    session.run_lesson("contradiction_handling", turns=2)
    pair_a = tuple(engine.entities[eid].i_state for eid in session.entity_ids)
    assert pair_a == _DIMENSION_I_STATE_PAIRS["contradiction_handling"]

    session.run_lesson("boundary_calibration", turns=2)
    pair_b = tuple(engine.entities[eid].i_state for eid in session.entity_ids)
    assert pair_b == _DIMENSION_I_STATE_PAIRS["boundary_calibration"]

    assert pair_a != pair_b


def test_run_lesson_falls_back_to_default_pair_for_unmapped_dimension(tmp_path):
    engine = SimulationEngine(state_dir=str(tmp_path))
    systems = {"state_dir": str(tmp_path)}
    session = ClassroomSession(engine, systems, state_dir=str(tmp_path))

    session.run_lesson("some_dimension_not_in_the_map", turns=2)
    pair = tuple(engine.entities[eid].i_state for eid in session.entity_ids)
    assert pair == _DEFAULT_I_STATE_PAIR


def _write_zero_divergence_lessons(log_path, count, start_ts=None):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    # Comfortably in the past by default, so ack calls (stamped with real
    # wall-clock time.time() at call time) always land after these unless
    # a test explicitly wants otherwise.
    base = start_ts if start_ts is not None else (time.time() - 100000.0)
    with open(log_path, "a", encoding="utf-8") as f:
        for i in range(count):
            f.write(json.dumps({
                "lesson_id": f"lesson_{i}", "divergence_score": 0.0, "timestamp": base + i,
            }) + "\n")
    return base + count - 1 if count else base


def test_consecutive_zero_divergence_tail_counts_correctly(tmp_path):
    log_path = tmp_path / "classroom_log.jsonl"
    _write_zero_divergence_lessons(log_path, 5)
    assert _consecutive_zero_divergence_tail(tmp_path) == 5


def test_consecutive_zero_divergence_tail_stops_at_nonzero_entry(tmp_path):
    log_path = tmp_path / "classroom_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"lesson_id": "old", "divergence_score": 0.4}) + "\n")
        for i in range(7):
            f.write(json.dumps({"lesson_id": f"lesson_{i}", "divergence_score": 0.0}) + "\n")
    assert _consecutive_zero_divergence_tail(tmp_path) == 7


def test_consecutive_zero_divergence_tail_degrades_gracefully_on_missing_file(tmp_path):
    assert _consecutive_zero_divergence_tail(tmp_path / "does_not_exist") == 0


def test_watchdog_halts_after_threshold_reached(tmp_path):
    log_path = tmp_path / "classroom_log.jsonl"
    _write_zero_divergence_lessons(log_path, _FLAT_DIVERGENCE_HALT_THRESHOLD)

    engine = SimulationEngine(state_dir=str(tmp_path))
    systems = {"state_dir": str(tmp_path)}
    session = ClassroomSession(engine, systems, state_dir=str(tmp_path))

    with pytest.raises(ClassroomHaltedError):
        session.run_lesson("context_carryover", turns=2)


def test_watchdog_does_not_halt_below_threshold(tmp_path):
    log_path = tmp_path / "classroom_log.jsonl"
    _write_zero_divergence_lessons(log_path, _FLAT_DIVERGENCE_HALT_THRESHOLD - 1)

    engine = SimulationEngine(state_dir=str(tmp_path))
    systems = {"state_dir": str(tmp_path)}
    session = ClassroomSession(engine, systems, state_dir=str(tmp_path))

    result = session.run_lesson("context_carryover", turns=2)
    assert result.lesson_id


def test_acknowledge_clears_a_tripped_watchdog(tmp_path):
    """The chicken-and-egg case this mechanism exists for: a real fix just
    landed, but the persisted log tail still shows the pre-fix dead
    streak. Without an explicit ack, the watchdog would permanently
    block every future lesson, including the ones needed to prove the
    fix works."""
    log_path = tmp_path / "classroom_log.jsonl"
    _write_zero_divergence_lessons(log_path, _FLAT_DIVERGENCE_HALT_THRESHOLD)
    assert _consecutive_zero_divergence_tail(tmp_path) == _FLAT_DIVERGENCE_HALT_THRESHOLD

    acknowledge_flat_divergence_watchdog(tmp_path, reason="fix verified, testing")
    assert _consecutive_zero_divergence_tail(tmp_path) == 0

    engine = SimulationEngine(state_dir=str(tmp_path))
    systems = {"state_dir": str(tmp_path)}
    session = ClassroomSession(engine, systems, state_dir=str(tmp_path))
    result = session.run_lesson("context_carryover", turns=2)
    assert result.lesson_id


def test_acknowledge_does_not_raise_the_bar_for_a_fresh_dead_streak(tmp_path):
    """Acknowledging resets where counting starts -- it must not permanently
    disable the watchdog. If the SAME dead-signal condition recurs for
    another full threshold's worth of lessons after the ack, it must trip
    again."""
    log_path = tmp_path / "classroom_log.jsonl"
    _write_zero_divergence_lessons(log_path, _FLAT_DIVERGENCE_HALT_THRESHOLD)

    acknowledge_flat_divergence_watchdog(tmp_path, reason="fix verified, testing")
    assert _consecutive_zero_divergence_tail(tmp_path) == 0

    # New lessons written strictly AFTER the ack's own wall-clock timestamp.
    _write_zero_divergence_lessons(log_path, _FLAT_DIVERGENCE_HALT_THRESHOLD, start_ts=time.time() + 10.0)
    assert _consecutive_zero_divergence_tail(tmp_path) == _FLAT_DIVERGENCE_HALT_THRESHOLD

    engine = SimulationEngine(state_dir=str(tmp_path))
    systems = {"state_dir": str(tmp_path)}
    session = ClassroomSession(engine, systems, state_dir=str(tmp_path))
    with pytest.raises(ClassroomHaltedError):
        session.run_lesson("context_carryover", turns=2)


def test_no_ack_file_behaves_identically_to_before_the_ack_feature(tmp_path):
    _write_zero_divergence_lessons(tmp_path / "classroom_log.jsonl", 5)
    assert _consecutive_zero_divergence_tail(tmp_path) == 5


def test_classroom_uses_a_dedicated_divergence_tracker_not_the_shared_engine_one(tmp_path):
    """Second bug found during R1.4 live verification, same day as R1.1-3:
    SimulationSession.run_episode() (called internally by every lesson)
    ALSO captures into engine.session.divergence, with completely different
    keys ({avg_fitness, engagement} vs this classroom's entity_N_valence/
    entity_N_intensity). DivergenceTracker.current_divergence only sums
    diffs for keys present in BOTH the first and last captured snapshot --
    sharing the tracker meant divergence_score was mathematically forced to
    0.0 on every lesson forever, regardless of how different the two
    entities' resolved state actually was. ClassroomSession must own its
    own tracker instance, untouched by run_episode()."""
    engine = SimulationEngine(state_dir=str(tmp_path))
    systems = {"state_dir": str(tmp_path)}
    session = ClassroomSession(engine, systems, state_dir=str(tmp_path))

    assert session._divergence_tracker is not engine.session.divergence

    session.run_lesson("contradiction_handling", turns=2)
    # engine.session.divergence picked up run_episode()'s own capture too --
    # this assertion is about ClassroomSession's OWN tracker being isolated,
    # not about the shared tracker being empty.
    assert len(session._divergence_tracker._snapshots) >= 1

    result = session.run_lesson("uncertainty_signaling", turns=2)
    # By the second lesson, the dedicated tracker has 2 same-shaped
    # (entity_N_valence/entity_N_intensity) snapshots to compare -- a real
    # nonzero divergence must be possible now (was mathematically forced to
    # 0.0 before this fix, on every single lesson).
    assert result.divergence_score >= 0.0
    assert len(session._divergence_tracker._snapshots) == 2
    first_keys = set(session._divergence_tracker._snapshots[0].keys())
    last_keys = set(session._divergence_tracker._snapshots[-1].keys())
    assert first_keys == last_keys
    assert first_keys == {"entity_0_valence", "entity_0_intensity", "entity_1_valence", "entity_1_intensity"}
