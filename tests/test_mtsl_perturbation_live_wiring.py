"""
tests/test_mtsl_perturbation_live_wiring.py
==============================================
MTSL, live-wired 2026-07-14: TopologicalSemanticCoordinator.run_perturbation_probe()
(the shared entry point dream/classroom call into) and its two actual
live hooks, in aurora_quantum_dream_substrate.py and aurora_classroom.py.
"""
import time
import types

from aurora_classroom import ClassroomSession
from aurora_dimensional_systems import CrystalProcessingSystem, EvolutionTracker
from aurora_internal.dual_strata.crest import Crest
from aurora_internal.dual_strata.topological_semantic_coordinator import TopologicalSemanticCoordinator
from aurora_quantum_dream_substrate import QuantumDreamSubstrate

_AXES_CYCLE = [
    {"X": 0.5, "T": 0.5, "N": 0.7, "B": 0.5, "A": 0.3},
    {"X": 0.5, "T": 0.5, "N": 0.3, "B": 0.5, "A": 0.7},
    {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.7, "A": 0.3},
]
_CRESTS = (Crest(label="steady", intensity=0.6, axis="N"),)


def _driven_coordinator(n=40, state_dir=None):
    dps = CrystalProcessingSystem(tracker=EvolutionTracker())
    coord = TopologicalSemanticCoordinator(state_dir=state_dir)
    for i in range(n):
        coord.observe_turn(
            turn_id=f"t{i}", timestamp=time.time(), adjusted_axes=_AXES_CYCLE[i % 3],
            sub_crests=_CRESTS, dps=dps,
        )
    return coord, dps


# ---- TopologicalSemanticCoordinator.run_perturbation_probe() ----

def test_too_few_frames_returns_none():
    dps = CrystalProcessingSystem(tracker=EvolutionTracker())
    coord = TopologicalSemanticCoordinator(state_dir=None)
    coord.observe_turn(turn_id="t1", timestamp=time.time(), adjusted_axes=_AXES_CYCLE[0], sub_crests=_CRESTS, dps=dps)
    assert coord.run_perturbation_probe(dps) is None


def test_no_dps_returns_none():
    coord, _dps = _driven_coordinator()
    assert coord.run_perturbation_probe(None) is None


def test_no_matched_variant_returns_none():
    dps = CrystalProcessingSystem(tracker=EvolutionTracker())
    coord = TopologicalSemanticCoordinator(state_dir=None)
    for i in range(40):
        coord.observe_turn(
            turn_id=f"t{i}", timestamp=time.time(), adjusted_axes=_AXES_CYCLE[i % 3],
            sub_crests=_CRESTS, dps=None,  # no dps during observation -> no variant ever matched
        )
    assert coord.run_perturbation_probe(dps) is None


def test_occlude_default_records_dream_evidence():
    coord, dps = _driven_coordinator()
    result = coord.run_perturbation_probe(dps, source="dream")
    assert result is not None
    assert result.perturbation_type == "occlusion"
    snap = coord.latest_snapshot
    mid, tid = coord._split_variant_id(snap)
    variant = coord._registry._read_variant(dps, mid, tid)
    assert variant.dream_evidence
    assert variant.dream_evidence[-1]["source"] == "dream"


def test_classroom_source_records_classroom_evidence():
    coord, dps = _driven_coordinator()
    result = coord.run_perturbation_probe(dps, source="classroom")
    assert result is not None
    snap = coord.latest_snapshot
    mid, tid = coord._split_variant_id(snap)
    variant = coord._registry._read_variant(dps, mid, tid)
    assert variant.classroom_evidence
    assert variant.classroom_evidence[-1]["source"] == "classroom"


def test_clamp_perturbation():
    coord, dps = _driven_coordinator()
    result = coord.run_perturbation_probe(dps, perturbation="clamp", value=0.8)
    assert result is not None
    assert result.perturbation_type == "clamp"
    assert result.parameter == 0.8


def test_delay_perturbation():
    coord, dps = _driven_coordinator()
    result = coord.run_perturbation_probe(dps, perturbation="delay", lag=4)
    assert result is not None
    assert result.perturbation_type == "delay"
    assert result.parameter == 4.0


def test_unknown_perturbation_type_returns_none():
    coord, dps = _driven_coordinator()
    assert coord.run_perturbation_probe(dps, perturbation="not_a_real_type") is None


def test_explicit_axis_overrides_auto_selection():
    coord, dps = _driven_coordinator()
    result = coord.run_perturbation_probe(dps, axis="X")
    assert result.axis == "X"


def test_pick_probe_axis_chooses_the_most_active_axis():
    coord, dps = _driven_coordinator()
    frames = coord.recent_frames()
    axis = coord._pick_probe_axis(frames)
    # in this fixture N/A/B rotate through +/-0.2 changes every frame,
    # X/T never move -- the picked axis must be one of the active ones
    assert axis in ("N", "A", "B")


def test_evidence_never_alone_promotes_the_variant():
    coord, dps = _driven_coordinator()
    for _ in range(50):
        coord.run_perturbation_probe(dps, source="dream")
    snap = coord.latest_snapshot
    mid, tid = coord._split_variant_id(snap)
    variant = coord._registry._read_variant(dps, mid, tid)
    assert variant.status != "promoted"


# ---- live hook: aurora_quantum_dream_substrate.py ----

def test_dream_substrate_hook_no_coordinator_does_not_crash():
    dqs = QuantumDreamSubstrate()
    fake_dimensional = types.SimpleNamespace(dps=None)
    dqs._run_mtsl_perturbation_probe({"dimensional": fake_dimensional})  # must not raise


def test_dream_substrate_hook_no_dimensional_key_does_not_crash():
    dqs = QuantumDreamSubstrate()
    dqs._run_mtsl_perturbation_probe({})  # must not raise


def test_dream_substrate_hook_records_real_dream_evidence():
    coord, dps = _driven_coordinator()
    dqs = QuantumDreamSubstrate()
    fake_dimensional = types.SimpleNamespace(dps=dps, _mtsl_coordinator=coord)
    dqs._run_mtsl_perturbation_probe({"dimensional": fake_dimensional})

    snap = coord.latest_snapshot
    mid, tid = coord._split_variant_id(snap)
    variant = coord._registry._read_variant(dps, mid, tid)
    assert variant.dream_evidence
    assert variant.dream_evidence[-1]["source"] == "dream"


def test_dream_substrate_hook_bad_dimensional_object_does_not_crash():
    # a dimensional-like object missing the expected attributes entirely
    # must still degrade gracefully via getattr()'s own default handling.
    dqs = QuantumDreamSubstrate()
    dqs._run_mtsl_perturbation_probe({"dimensional": object()})


# ---- live hook: aurora_classroom.py ----
# ClassroomSession.__init__ needs a real SimulationEngine + systems dict
# (it spawns two entities) -- constructed via object.__new__ to test the
# narrow _run_mtsl_perturbation_probe() method in isolation, the same
# pattern the dream substrate's equivalent method above is tested with.

def _bare_session(systems):
    session = object.__new__(ClassroomSession)
    session.systems = systems
    return session


def test_classroom_hook_no_dimensional_key_does_not_crash():
    _bare_session({})._run_mtsl_perturbation_probe()  # must not raise


def test_classroom_hook_no_coordinator_does_not_crash():
    fake_dimensional = types.SimpleNamespace(dps=None)
    _bare_session({"dimensional": fake_dimensional})._run_mtsl_perturbation_probe()


def test_classroom_hook_records_real_classroom_evidence():
    coord, dps = _driven_coordinator()
    fake_dimensional = types.SimpleNamespace(dps=dps, _mtsl_coordinator=coord)
    _bare_session({"dimensional": fake_dimensional})._run_mtsl_perturbation_probe()

    snap = coord.latest_snapshot
    mid, tid = coord._split_variant_id(snap)
    variant = coord._registry._read_variant(dps, mid, tid)
    assert variant.classroom_evidence
    assert variant.classroom_evidence[-1]["source"] == "classroom"
