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

import pytest

from aurora_classroom import (
    ClassroomHaltedError,
    ClassroomSession,
    _DEFAULT_CANDIDATE_DIMENSIONS,
    _DEFAULT_I_STATE_PAIR,
    _DIMENSION_I_STATE_PAIRS,
    _FLAT_DIVERGENCE_HALT_THRESHOLD,
    _consecutive_zero_divergence_tail,
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


def _write_zero_divergence_lessons(log_path, count):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        for i in range(count):
            f.write(json.dumps({"lesson_id": f"lesson_{i}", "divergence_score": 0.0}) + "\n")


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
