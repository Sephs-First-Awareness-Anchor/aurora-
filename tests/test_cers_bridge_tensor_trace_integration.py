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
