"""
tests/test_topology_frame.py
==============================
MTSL Phase 1 (2026-07-13): TopologyFrame plain-data layer.
"""
import math

from aurora_internal.dual_strata.topology_frame import AXES, TopologyFrame


def test_from_vectors_computes_delta_honestly():
    prev = {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5}
    cur = {"X": 0.6, "T": 0.4, "N": 0.5, "B": 0.5, "A": 0.5}
    frame = TopologyFrame.from_vectors(
        turn_id="t1", timestamp=1000.0,
        constraint_vector=cur, previous_vector=prev,
    )
    assert frame.delta_vector["X"] == 0.6 - 0.5
    assert frame.delta_vector["T"] == 0.4 - 0.5
    assert frame.delta_vector["N"] == 0.0
    assert frame.constraint_vector == cur
    assert frame.previous_vector == prev


def test_crest_and_trough_axes_partition_on_own_mean():
    cur = {"X": 0.9, "T": 0.1, "N": 0.5, "B": 0.5, "A": 0.5}
    frame = TopologyFrame.from_vectors(
        turn_id="t2", timestamp=1000.0, constraint_vector=cur,
    )
    mean = sum(cur.values()) / len(AXES)
    assert set(frame.crest_axes) == {a for a in AXES if cur[a] >= mean}
    assert set(frame.trough_axes) == {a for a in AXES if cur[a] < mean}
    # partition: every axis in exactly one of the two sets
    assert set(frame.crest_axes) | set(frame.trough_axes) == set(AXES)
    assert set(frame.crest_axes) & set(frame.trough_axes) == set()


def test_active_constraint_fields_respects_floor():
    prev = {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5}
    cur = {"X": 0.51, "T": 0.5, "N": 0.7, "B": 0.5, "A": 0.5}
    frame = TopologyFrame.from_vectors(
        turn_id="t3", timestamp=1000.0,
        constraint_vector=cur, previous_vector=prev,
        active_floor=0.05,
    )
    # X moved by 0.01 (below floor) -> not active; N moved by 0.2 -> active
    assert "X" not in frame.active_constraint_fields
    assert "N" in frame.active_constraint_fields


def test_creation_and_dissipation_residual_are_exclusive_and_correct():
    prev = {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5}
    # net creation: sum(delta) > 0
    cur_creation = {"X": 0.5, "T": 0.5, "N": 0.7, "B": 0.5, "A": 0.5}
    f_create = TopologyFrame.from_vectors(
        turn_id="t4a", timestamp=1000.0,
        constraint_vector=cur_creation, previous_vector=prev,
    )
    assert math.isclose(f_create.creation_residual, 0.2, abs_tol=1e-9)
    assert math.isclose(f_create.dissipation_residual, 0.0, abs_tol=1e-9)

    # net dissipation: sum(delta) < 0
    cur_dissipate = {"X": 0.5, "T": 0.5, "N": 0.3, "B": 0.5, "A": 0.5}
    f_dissipate = TopologyFrame.from_vectors(
        turn_id="t4b", timestamp=1000.0,
        constraint_vector=cur_dissipate, previous_vector=prev,
    )
    assert math.isclose(f_dissipate.dissipation_residual, 0.2, abs_tol=1e-9)
    assert math.isclose(f_dissipate.creation_residual, 0.0, abs_tol=1e-9)


def test_ivm_phase_is_context_only_and_not_derived():
    frame = TopologyFrame.from_vectors(
        turn_id="t5", timestamp=1000.0,
        constraint_vector={a: 0.5 for a in AXES},
        ivm_phase={"X": 0.9, "T": -0.4},
    )
    assert frame.ivm_phase == {"X": 0.9, "T": -0.4}


def test_to_dict_from_dict_round_trip():
    frame = TopologyFrame.from_vectors(
        turn_id="t6", timestamp=1234.5,
        constraint_vector={"X": 0.7, "T": 0.2, "N": 0.5, "B": 0.4, "A": 0.6},
        previous_vector={"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5},
        manifold_slot_id="slot-123",
        base_meaning_form="bmf-abc",
        ivm_phase={"X": 0.1},
        context_family="dream",
    )
    data = frame.to_dict()
    restored = TopologyFrame.from_dict(data)
    assert restored == frame


def test_default_missing_vectors_treated_as_zero():
    frame = TopologyFrame.from_vectors(
        turn_id="t7", timestamp=1000.0,
        constraint_vector={"X": 0.3},
    )
    for a in AXES:
        if a != "X":
            assert frame.constraint_vector[a] == 0.0
            assert frame.previous_vector[a] == 0.0
