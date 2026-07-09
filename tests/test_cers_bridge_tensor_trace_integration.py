# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
End-to-end integration coverage for the tensor-trace pass wired into
CERSBridge.build_snapshot() (Phase 1 of the tensor-recursion upgrade).

Exercises the exact call shape aurora_consciousness_engine.py's live shadow
pass actually uses -- precomputed_sub_crests (the real per-turn path; the
bare adjusted_axes-only path was never hit in production, which is also
what this test caught: adjusted_axes used to only be computed in the
precomputed_sub_crests is None branch, so the live path never had a
pressure vector to resolve a coordinate from at all).
"""
import json
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.dual_strata.cers_bridge import CERSBridge
from aurora_internal.dual_strata.crest import Crest
from aurora_dimensional_systems import CrystalProcessingSystem, EvolutionTracker


def _assembly_result(adjusted_axes):
    return types.SimpleNamespace(
        sensory_context={},
        entropy_state={"coherence": 0.6},
        coherence=0.6,
        adjusted_axes=adjusted_axes,
    )


def test_build_snapshot_with_precomputed_crests_still_resolves_tensor_trace(tmp_path):
    """This is the actual production call shape -- precomputed_sub_crests
    set, which used to skip adjusted_axes computation entirely."""
    dps = CrystalProcessingSystem(EvolutionTracker())
    bridge = CERSBridge(state_dir=str(tmp_path))
    sub_crests = (
        Crest(label="steady", intensity=0.9, axis="N"),
        Crest(label="warmth", intensity=0.4, axis="B"),
    )

    snapshot = bridge.build_snapshot(
        _assembly_result({"X": 0.2, "T": 0.3, "N": 0.9, "B": 0.6, "A": 0.1}),
        payload="hello there",
        payload_type="text",
        evidence={},
        contract_snapshot={},
        requested_frame="balanced",
        precomputed_sub_crests=sub_crests,
        dps=dps,
    )

    assert snapshot is not None
    detail_path = tmp_path / "cers_detail.json"
    assert detail_path.exists()
    detail = json.loads(detail_path.read_text())

    trace = detail["tensor_trace"]
    assert trace["coord"].startswith("MANIFOLD:N:")  # N was the dominant axis
    assert trace["is_new_coordinate"] is True
    assert trace["distortion"] == 0.0
    assert trace["salience"] == 1.0

    assert len(dps.crystals) == 1
    crystal = next(iter(dps.crystals.values()))
    assert crystal.concept == f"tensor:{trace['coord']}"


def test_revisiting_same_pressure_geometry_reuses_the_crystal(tmp_path):
    dps = CrystalProcessingSystem(EvolutionTracker())
    bridge = CERSBridge(state_dir=str(tmp_path))
    sub_crests = (Crest(label="steady", intensity=0.9, axis="N"),)
    axes = {"X": 0.2, "T": 0.3, "N": 0.9, "B": 0.6, "A": 0.1}

    for _ in range(3):
        bridge.build_snapshot(
            _assembly_result(axes),
            payload="hello there",
            payload_type="text",
            evidence={},
            contract_snapshot={},
            requested_frame="balanced",
            precomputed_sub_crests=sub_crests,
            dps=dps,
        )

    assert len(dps.crystals) == 1, "the same recurring pressure geometry must not spawn multiple crystals"


def test_established_coordinate_sharp_deviation_flags_geometry_deviation_end_to_end(tmp_path):
    """CERS Stage 3, full chain: a coordinate with real established
    precedent whose reading suddenly breaks sharply must be caught by
    CERS's OWN verdict (not just recorded afterward), even when nothing
    in sub_crests looks like a classic opposed-cluster conflict."""
    dps = CrystalProcessingSystem(EvolutionTracker())
    bridge = CERSBridge(state_dir=str(tmp_path))
    # Same crest reads throughout -> same resolved coordinate throughout
    # (crest axis reads win over raw adjusted_axes magnitude in
    # resolve_pressure_coordinate), isolating pure geometry deviation from
    # coordinate drift.
    sub_crests = (Crest(label="steady", intensity=0.9, axis="N"),)

    # Establish real precedent: several steady visits with a consistent
    # pressure profile. adjusted_axes gets normalized to sum to 1.0
    # (normalize_axis_map -- a constraint-budget distribution across the 5
    # axes, not 5 independently-bounded magnitudes), so these are chosen
    # pre-normalized. The 4 non-target axes are kept equal to each other in
    # both phases so resolve_pressure_coordinate's tie-breaking picks the
    # same nc_law_c/law_c both times -- isolating pure axis_mean distortion
    # at a genuinely fixed coordinate, not coordinate drift from a flipped
    # tie-break.
    steady_axes = {"X": 0.0, "T": 0.0, "N": 1.0, "B": 0.0, "A": 0.0}
    for _ in range(6):
        bridge.build_snapshot(
            _assembly_result(steady_axes),
            payload="hello there", payload_type="text",
            evidence={}, contract_snapshot={}, requested_frame="balanced",
            precomputed_sub_crests=sub_crests, dps=dps,
        )

    # Now a sharply different pressure reading at the SAME coordinate (N
    # still narrowly dominant so the coordinate itself doesn't drift).
    deviant_axes = {"X": 0.22, "T": 0.22, "N": 0.34, "B": 0.22, "A": 0.0}
    bridge.build_snapshot(
        _assembly_result(deviant_axes),
        payload="hello there", payload_type="text",
        evidence={}, contract_snapshot={}, requested_frame="balanced",
        precomputed_sub_crests=sub_crests, dps=dps,
    )

    detail = json.loads((tmp_path / "cers_detail.json").read_text())
    verdict = detail["cers_verdict"]
    assert verdict["geometry_deviation"] is not None
    assert verdict["permitted"] is False
    assert verdict["intervention_label"] == "pattern_deviation"
    assert len(dps.crystals) == 1, "still the same coordinate, not a new one"


def test_prediction_signal_is_fed_from_the_same_manifold_on_revisit(tmp_path):
    """CERS Phase 2: prediction, not just the tensor-trace pass itself,
    should draw on the same constraint manifold. First visit to a
    coordinate has zero precedent (familiarity 0.0); by the time this
    exact pressure geometry has been visited several times, prediction's
    confidence should reflect that real precedent."""
    dps = CrystalProcessingSystem(EvolutionTracker())
    bridge = CERSBridge(state_dir=str(tmp_path))
    sub_crests = (Crest(label="steady", intensity=0.9, axis="N"),)
    axes = {"X": 0.2, "T": 0.3, "N": 0.9, "B": 0.6, "A": 0.1}

    confidences = []
    for _ in range(6):
        bridge.build_snapshot(
            _assembly_result(axes),
            payload="hello there",
            payload_type="text",
            evidence={},
            contract_snapshot={},
            requested_frame="balanced",
            precomputed_sub_crests=sub_crests,
            dps=dps,
        )
        detail = json.loads((tmp_path / "cers_detail.json").read_text())
        assert detail["prediction_source"].endswith("+manifold")
        confidences.append(detail["prediction_confidence"])

    assert confidences[-1] > confidences[0], (
        "prediction confidence should rise as real precedent accumulates "
        "at this coordinate, not stay flat"
    )


def test_build_snapshot_without_dps_skips_tensor_trace_gracefully(tmp_path):
    bridge = CERSBridge(state_dir=str(tmp_path))
    sub_crests = (Crest(label="steady", intensity=0.9, axis="N"),)

    snapshot = bridge.build_snapshot(
        _assembly_result({"X": 0.2, "T": 0.3, "N": 0.9, "B": 0.6, "A": 0.1}),
        payload="hello there",
        payload_type="text",
        evidence={},
        contract_snapshot={},
        requested_frame="balanced",
        precomputed_sub_crests=sub_crests,
        dps=None,
    )

    assert snapshot is not None
    detail = json.loads((tmp_path / "cers_detail.json").read_text())
    assert detail["tensor_trace"] == {}
    assert not detail["prediction_source"].endswith("+manifold"), (
        "no dps means 'couldn't check', not 'checked, unfamiliar' -- "
        "prediction must not be touched at all, same as before this feature existed"
    )
