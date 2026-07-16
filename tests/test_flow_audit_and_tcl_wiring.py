# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression coverage for aurora_flow_audit.py's shared detection machinery
(FIX-A010) and a structural check that the Toroidal Circulation Layer is
wired into the live turn path -- not just that the module exists, but
that something constructs it, seeds it from the real lived record on
first touch, and never surfaces raw mechanism (only the compressed
ToroidalSignature).

N5 item 2 (R1 Campaign Closure dead-systems docket, 2026-07-16) found
that test_aurora_py_wires_toroidal_layer_into_cers_snapshot_pass below
had gone stale: it asserted the PRE-MTSL-Phase-3 wiring pattern (TCL
constructed/observed directly inline in aurora.py's CERS shadow pass).
That pattern was deliberately superseded on 2026-07-13 by FIX-A011
(single-observer law) -- TopologicalSemanticCoordinator now owns the
TCL instance exclusively (constructs/seeds it in its own __init__,
ticks it inside observe_turn(), called exactly once per turn from
aurora_consciousness_engine.py's _attach_dual_strata_snapshot) so two
independent call sites can never double-tick the same shared crest
registry. aurora.py's CERS shadow pass was correctly changed to READ
the coordinator's cached toroidal_signature, never to re-observe. The
capability was never dead; the test was checking for code that had
moved, not code that had disappeared. Rewritten below to assert the
current (correct) wiring instead of the superseded one.
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


def test_topological_coordinator_owns_toroidal_layer_construction_and_seeding():
    """The coordinator, not aurora.py, is the single owner of the TCL
    instance -- construction, first-touch seeding from the real surface
    log, and per-turn observe/save all live inside
    topological_semantic_coordinator.py (FIX-A011)."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    coord_path = os.path.join(
        root, "aurora_internal", "dual_strata", "topological_semantic_coordinator.py"
    )
    with open(coord_path, "r", encoding="utf-8") as f:
        source = f.read()

    assert "from aurora_toroidal_circulation import ToroidalCirculationLayer" in source
    assert "self._tcl = _TCL(state_dir=self._state_dir)" in source
    assert "self._tcl.seed_from_surface_log()" in source
    assert "self._tcl.observe(intensity)" in source
    assert "self._tcl.save()" in source
    assert "self._tcl.current_signature().to_dict()" in source


def test_aurora_py_reads_toroidal_signature_from_coordinator_not_layer_directly():
    """Structural check: aurora.py's CERS shadow pass must READ the
    coordinator's cached, compressed signature (read-only, must never
    affect the authoritative runtime dict on failure) and must never
    construct, import, or observe a ToroidalCirculationLayer itself --
    that would reintroduce the double-tick bug FIX-A011 eliminated.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "aurora.py"), "r", encoding="utf-8") as f:
        source = f.read()

    assert "ToroidalCirculationLayer" not in source
    assert '_mtsl_coordinator.latest_snapshot.toroidal_signature' in source
    assert 'systems["_toroidal_signature"] = dict(_mtsl_coordinator.latest_snapshot.toroidal_signature or {})' in source

    # The read must sit inside the same try/except as the CERS shadow
    # pass -- confirms it stays read-only/advisory, never authoritative.
    anchor = source.index('_mtsl_coordinator.latest_snapshot.toroidal_signature')
    head = source[max(0, anchor - 3000):anchor]
    assert "try:" in head
    tail = source[anchor:anchor + 500]
    assert "except Exception:\n        pass" in tail


def test_consciousness_engine_is_the_single_observer_of_the_coordinator():
    """FIX-A011's single-observer law: exactly one call site (aurora_
    consciousness_engine.py's _attach_dual_strata_snapshot) may call
    observe_turn() on the shared coordinator; aurora.py's own dual-strata
    refresh path must only ever read latest_snapshot."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "aurora_consciousness_engine.py"), "r", encoding="utf-8") as f:
        ace_source = f.read()
    assert "_mtsl_coordinator.observe_turn(" in ace_source or ".observe_turn(" in ace_source

    with open(os.path.join(root, "aurora.py"), "r", encoding="utf-8") as f:
        aurora_source = f.read()
    assert "_mtsl_coordinator.observe_turn(" not in aurora_source
