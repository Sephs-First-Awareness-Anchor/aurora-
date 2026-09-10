"""King Quasicrystal authority canaries for live possibility actualization."""
from __future__ import annotations

from types import SimpleNamespace

import aurora_internal.aurora_live_possibility_frontier as frontier


class _IdentityField:
    def __init__(self, current, reference, dimensions=None):
        self.current = dict(current)
        self.reference = dict(reference)
        self.dimensions = dict(dimensions or {})
        self.status_calls = 0
        self.mutations = 0

    def status(self):
        self.status_calls += 1
        return {
            "axis_pressures": dict(self.current),
            "reference_axis_pressures": dict(self.reference),
            "dimension_pressures": dict(self.dimensions),
        }

    # These methods exist only to prove arbitration never mutates the field.
    def ingest(self, *args, **kwargs):
        self.mutations += 1
        raise AssertionError("possibility arbitration must not mutate the King")

    def reset(self, *args, **kwargs):
        self.mutations += 1
        raise AssertionError("possibility arbitration must not reset the King")


class _Thought:
    def __init__(self, axes):
        self.axis_fingerprint = list(axes)


def _candidate(cid, axes, perspective=()):
    return frontier.PossibilityContinuation(
        candidate_id=cid,
        source="test",
        predictive_frame={
            "pressure_perspective": list(perspective),
            "dominant_axis_hint": axes[0] if axes else "",
        },
        pressure_perspective=tuple(perspective),
        thought_state=_Thought(axes),
        braid_slice=None,
    )


def test_king_snapshot_uses_native_current_vs_reference_topology_read_only():
    field = _IdentityField(
        current={"X": 0.10, "T": 0.16, "N": 0.12, "B": 0.22, "A": 0.70},
        reference={axis: 0.10 for axis in frontier._AXES},
        dimensions={"OPERATOR": 0.21, "DIFFERENCE": 0.08},
    )

    snapshot = frontier._king_identity_snapshot({"identity_field": field})

    assert snapshot["available"] is True
    assert snapshot["axis_elevation"]["A"] == 0.60
    assert snapshot["axis_elevation"]["B"] == 0.12
    assert snapshot["axis_elevation"]["X"] == 0.0
    assert field.status_calls == 1
    assert field.mutations == 0


def test_king_identity_topology_resolves_otherwise_equivalent_survivors():
    field = _IdentityField(
        current={"X": 0.10, "T": 0.10, "N": 0.10, "B": 0.18, "A": 0.80},
        reference={axis: 0.10 for axis in frontier._AXES},
    )
    snapshot = frontier._king_identity_snapshot({"identity_field": field})
    agency_path = _candidate("agency_path", ("A",), ("A",))
    boundary_path = _candidate("boundary_path", ("B",), ("B",))

    selected, evidence = frontier._king_identity_arbitrate(
        [boundary_path, agency_path], snapshot
    )

    assert selected is agency_path
    assert evidence["authority_used"] is True
    assert evidence["authority"] == "king_quasicrystal_identity_field"
    assert evidence["identity_discrimination"] is True
    assert agency_path.evidence["king_identity_fit"] > boundary_path.evidence["king_identity_fit"]


def test_king_at_native_reference_does_not_manufacture_a_preference():
    reference = {axis: 0.10 for axis in frontier._AXES}
    field = _IdentityField(current=reference, reference=reference)
    snapshot = frontier._king_identity_snapshot({"identity_field": field})
    left = _candidate("left", ("A",), ("A",))
    right = _candidate("right", ("B",), ("B",))

    selected, evidence = frontier._king_identity_arbitrate([left, right], snapshot)

    assert snapshot["available"] is False
    assert selected is None
    assert evidence["authority_used"] is False
    assert evidence["reason"] == "identity_at_reference"
    assert "king_identity_fit" not in left.evidence
    assert "king_identity_fit" not in right.evidence


def test_king_equivalence_remains_neutral_and_order_independent():
    field = _IdentityField(
        current={"X": 0.10, "T": 0.10, "N": 0.10, "B": 0.50, "A": 0.50},
        reference={axis: 0.10 for axis in frontier._AXES},
    )
    snapshot = frontier._king_identity_snapshot({"identity_field": field})
    left = _candidate("left", ("A", "B"), ("A", "B"))
    right = _candidate("right", ("B", "A"), ("B", "A"))

    selected, evidence = frontier._king_identity_arbitrate([left, right], snapshot)
    assert selected is None
    assert evidence["authority_used"] is True
    assert evidence["identity_discrimination"] is False
    assert evidence["reason"] == "identity_topology_equivalent"

    first = frontier._neutral_equivalence_choice([left, right], "same turn", 42)
    second = frontier._neutral_equivalence_choice([right, left], "same turn", 42)
    assert first.candidate_id == second.candidate_id
