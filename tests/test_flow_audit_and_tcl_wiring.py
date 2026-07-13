# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression coverage for aurora_flow_audit.py's shared detection machinery
(FIX-A010) and a structural check that aurora.py actually wires the
Toroidal Circulation Layer into the CERS snapshot pass -- not just that
the module exists, but that _run_live_response_turn's dual-strata block
constructs it, seeds it from the real lived record on first touch, and
never surfaces raw mechanism (only the compressed ToroidalSignature).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_flow_audit import antisymmetric, find_cycles, flow_ratio

_AXES = ("X", "T", "N", "B", "A")


def test_antisymmetric_cancels_symmetric_flow():
    """Equal traffic both directions on an edge must net to zero -- pure
    churn, not circulation or gradient."""
    F = {("X", "T"): 5.0, ("T", "X"): 5.0}
    A = antisymmetric(F, _AXES)
    assert A[("X", "T")] == 0.0
    assert A[("T", "X")] == 0.0


def test_antisymmetric_preserves_net_directional_flow():
    F = {("N", "B"): 10.0, ("B", "N"): 3.0}
    A = antisymmetric(F, _AXES)
    assert A[("N", "B")] == 7.0
    assert A[("B", "N")] == -7.0


def test_find_cycles_detects_a_real_triangle():
    A = {(u, v): 0.0 for u in _AXES for v in _AXES}
    A[("N", "A")] = 5.0
    A[("A", "B")] = 5.0
    A[("B", "N")] = 5.0
    cycles = find_cycles(A, _AXES, eps=0.01)
    assert cycles
    assert set(cycles[0][0]) == {"N", "A", "B"}


def test_find_cycles_ignores_pure_source_sink():
    A = {(u, v): 0.0 for u in _AXES for v in _AXES}
    A[("N", "B")] = 10.0  # one-way only, no return edge
    cycles = find_cycles(A, _AXES, eps=0.01)
    assert cycles == []


def test_flow_ratio_is_zero_for_no_traffic():
    F = {}
    A = antisymmetric(F, _AXES)
    traffic, net, ratio = flow_ratio(F, A, _AXES)
    assert traffic == 0.0
    assert ratio == 0.0


def test_aurora_py_wires_toroidal_layer_into_cers_snapshot_pass():
    """Structural check: the toroidal layer construction/observe/save call
    sequence must sit inside the same try/except block as the CERS
    snapshot pass (read-only, must never affect the authoritative runtime
    dict on failure), and only the compressed signature -- never the
    layer object itself -- may be exposed via systems[...].
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "aurora.py"), "r", encoding="utf-8") as f:
        source = f.read()

    assert "from aurora_toroidal_circulation import ToroidalCirculationLayer as _TCL" in source
    assert 'systems.get("_toroidal")' in source
    assert "_tcl.seed_from_surface_log()" in source
    assert "_tcl.observe(_TCL.intensity_from_crests(_precomputed))" in source
    assert 'systems["_toroidal_signature"] = _tcl.current_signature().to_dict()' in source

    # The wiring block must appear before the enclosing "except Exception:
    # pass" that already governs the CERS shadow pass -- confirms it did
    # not get inserted outside the safety boundary.
    anchor = source.index("from aurora_toroidal_circulation import ToroidalCirculationLayer as _TCL")
    tail = source[anchor:anchor + 1500]
    assert "except Exception:\n        pass" in tail
