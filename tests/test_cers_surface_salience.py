# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
CERS Phase 3: the compressed relevance/hesitation signal actually reaching
the surface, per the user's original ask ("her surface should receive the
relevance snapshots... the salience sensitivity metric").

CERS is architecturally forbidden from writing into dual_strata_snapshot.json
(the legacy bridge's own file -- see cers_bridge.py's design doc: "it never
touches subsurface_snapshot.json or subsurface_detail.json"). So this is
built as the SURFACE choosing to additionally read CERS's own private file
(cers_detail.json) and merge in only the two compressed values the ERS spec
calls for -- relevance (salience) and hesitation -- never CERS pushing its
much larger private detail across that line.

aurora.py is a large module; import alone (no boot_aurora()) is fast and
sufficient to exercise these pure functions.
"""
import json
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")

import aurora


def _systems(tmp_path):
    return {"state_dir": str(tmp_path)}


def test_read_cers_salience_defaults_when_no_file(tmp_path):
    result = aurora._read_cers_salience(_systems(tmp_path))
    assert result == {"cers_salience": 0.0, "cers_hesitation": False}


def test_read_cers_salience_reads_real_detail_file(tmp_path):
    (tmp_path / "cers_detail.json").write_text(json.dumps({
        "tensor_trace": {"salience": 0.87, "coord": "MANIFOLD:N:..."},
        "cers_verdict": {"permitted": True},
    }))
    result = aurora._read_cers_salience(_systems(tmp_path))
    assert result == {"cers_salience": 0.87, "cers_hesitation": False}


def test_read_cers_salience_hesitation_when_conflict_not_permitted(tmp_path):
    (tmp_path / "cers_detail.json").write_text(json.dumps({
        "tensor_trace": {"salience": 0.5},
        "cers_verdict": {"permitted": False},
    }))
    result = aurora._read_cers_salience(_systems(tmp_path))
    assert result["cers_hesitation"] is True


def test_read_cers_salience_clamps_out_of_range_values(tmp_path):
    (tmp_path / "cers_detail.json").write_text(json.dumps({
        "tensor_trace": {"salience": 3.5},
        "cers_verdict": {},
    }))
    result = aurora._read_cers_salience(_systems(tmp_path))
    assert result["cers_salience"] == 1.0


def test_read_cers_salience_survives_corrupt_file(tmp_path):
    (tmp_path / "cers_detail.json").write_text("{not valid json")
    result = aurora._read_cers_salience(_systems(tmp_path))
    assert result == {"cers_salience": 0.0, "cers_hesitation": False}


def test_read_live_dual_strata_runtime_merges_salience_into_conscious_frame(tmp_path):
    (tmp_path / "dual_strata_snapshot.json").write_text(json.dumps({
        "conscious_frame": {"stance": "attend", "selected_action": "hold"},
        "subsurface_state": {},
    }))
    (tmp_path / "cers_detail.json").write_text(json.dumps({
        "tensor_trace": {"salience": 0.42},
        "cers_verdict": {"permitted": True},
    }))

    runtime = aurora._read_live_dual_strata_runtime(_systems(tmp_path))

    # Legacy fields untouched -- CERS is additive only.
    assert runtime["conscious_frame"]["stance"] == "attend"
    assert runtime["conscious_frame"]["selected_action"] == "hold"
    # New compressed signal present.
    assert runtime["conscious_frame"]["cers_salience"] == 0.42
    assert runtime["conscious_frame"]["cers_hesitation"] is False


def test_read_live_dual_strata_runtime_defaults_salience_when_cers_never_ran(tmp_path):
    (tmp_path / "dual_strata_snapshot.json").write_text(json.dumps({
        "conscious_frame": {"stance": "steady"},
        "subsurface_state": {},
    }))
    runtime = aurora._read_live_dual_strata_runtime(_systems(tmp_path))
    assert runtime["conscious_frame"]["stance"] == "steady"
    assert runtime["conscious_frame"]["cers_salience"] == 0.0
    assert runtime["conscious_frame"]["cers_hesitation"] is False


def test_refresh_live_dual_strata_runtime_threads_dps_and_merges_salience(tmp_path):
    """The second, independent CERS call site (aurora.py's own live-turn
    refresh path) -- confirms it actually passes dps through (Phase 1/2's
    tensor-trace pass is otherwise silently inert here) and that its
    returned runtime dict carries the same compressed surface signal."""
    from aurora_dimensional_systems import CrystalProcessingSystem, EvolutionTracker

    dps = CrystalProcessingSystem(EvolutionTracker())
    systems = {
        "state_dir": str(tmp_path),
        "dimensional": types.SimpleNamespace(dps=dps),
    }
    assembly = types.SimpleNamespace(
        sensory_context={},
        entropy_state={"coherence": 0.6},
        coherence=0.6,
        adjusted_axes={"X": 0.2, "T": 0.3, "N": 0.9, "B": 0.6, "A": 0.1},
    )
    synthesis = types.SimpleNamespace(assembly=assembly)

    runtime = aurora._refresh_live_dual_strata_runtime(
        systems,
        synthesis=synthesis,
        payload="hello there",
        payload_type="text",
        evidence={},
        contract_snapshot={},
        requested_frame="balanced",
    )

    assert "cers_salience" in runtime["conscious_frame"]
    assert "cers_hesitation" in runtime["conscious_frame"]
    # dps was threaded through -> the tensor-trace pass actually ran and
    # recorded a real visit onto the crystal registry.
    assert len(dps.crystals) == 1
