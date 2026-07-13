# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression coverage for aurora_toroidal_circulation.py (FIX-A010,
2026-07-12): circulation detection over Aurora's TEMPORAL constraint
record, never over the compiled static grids.

Independently re-run aurora_flow_audit.py against the real repo data
before applying anything (per this session's standing practice for
external deliveries): confirmed 0/125 compiled manifolds show 3-cycle
circulation (the bedrock is a potential field), while the real
surface_pressure_log.jsonl (1005 timestamp-ordered events) shows 7 closed
circulation loops, dominant vortex strength 8.15 -- matching the
delivery's claims exactly. That empirical split is the entire reason this
layer feeds only on per-tick CERS sub-crest intensities and never on
static grids.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_toroidal_circulation import (
    AXES,
    ToroidalCirculationLayer,
    ToroidalSignature,
)


def test_quiescent_before_enough_observations(tmp_path):
    tcl = ToroidalCirculationLayer(state_dir=str(tmp_path))
    tcl.observe({"N": 0.5, "A": 0.1, "B": 0.0, "X": 0.0, "T": 0.0})
    sig = tcl.current_signature()
    assert sig.regime == "quiescent"
    assert sig.loops == []


def test_pure_gradient_flow_produces_no_loops(tmp_path):
    """A monotone one-way drain N -> B (source/sink only, no return path)
    must never register as circulation -- this is exactly what
    aurora_flow_audit.py found for the compiled bedrock and the genealogy
    fossil record."""
    tcl = ToroidalCirculationLayer(state_dir=str(tmp_path))
    for i in range(20):
        n_level = max(0.0, 1.0 - i * 0.05)
        b_level = min(1.0, i * 0.05)
        tcl.observe({"N": n_level, "B": b_level, "X": 0.0, "T": 0.0, "A": 0.0})
    sig = tcl.current_signature()
    assert sig.loops == []
    assert sig.regime in ("gradient", "quiescent")


def test_real_closed_loop_is_detected(tmp_path):
    """A genuine round-trip N -> A -> B -> N cycle, repeated, must surface
    as a real detected loop -- the positive control for the whole
    detector."""
    tcl = ToroidalCirculationLayer(state_dir=str(tmp_path))
    # Cycle intensity through N -> A -> B -> N repeatedly.
    pattern = [
        {"N": 1.0, "A": 0.0, "B": 0.0, "X": 0.0, "T": 0.0},
        {"N": 0.0, "A": 1.0, "B": 0.0, "X": 0.0, "T": 0.0},
        {"N": 0.0, "A": 0.0, "B": 1.0, "X": 0.0, "T": 0.0},
    ]
    for _ in range(12):
        for state in pattern:
            tcl.observe(state)
    sig = tcl.current_signature()
    assert sig.regime in ("circulating", "mixed")
    assert sig.loops, "a genuine repeating N->A->B->N cycle must be detected"
    loop_axes = set(sig.loops[0][0])
    assert loop_axes == {"N", "A", "B"}


def test_seed_from_surface_log_against_real_repo_data():
    """The exact real-world bootstrap path: seeding from the committed
    aurora_state/surface_pressure_log.jsonl must produce a genuinely
    circulating signature, matching aurora_flow_audit.py's TEST 3 verdict
    (independently reproduced against this repo before this test was
    written)."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tcl = ToroidalCirculationLayer(state_dir=td)
        n = tcl.seed_from_surface_log(
            path=os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "aurora_state", "surface_pressure_log.jsonl",
            )
        )
        assert n > 0, "the real surface_pressure_log.jsonl must exist and be ingestible"
        sig = tcl.current_signature()
        assert sig.regime == "circulating"
        assert sig.loops


def test_flux_decays_with_half_life(tmp_path):
    tcl = ToroidalCirculationLayer(state_dir=str(tmp_path))
    pattern = [
        {"N": 1.0, "A": 0.0, "B": 0.0, "X": 0.0, "T": 0.0},
        {"N": 0.0, "A": 1.0, "B": 0.0, "X": 0.0, "T": 0.0},
        {"N": 0.0, "A": 0.0, "B": 1.0, "X": 0.0, "T": 0.0},
    ]
    for _ in range(12):
        for state in pattern:
            tcl.observe(state)
    before = sum(tcl._flux.values())

    # Simulate the decay clock advancing without any further real flux.
    for _ in range(500):
        tcl.observe({"N": 0.0, "A": 0.0, "B": 0.0, "X": 0.0, "T": 0.0})
    after = sum(tcl._flux.values())

    assert after < before * 0.6, "accumulated flux must meaningfully decay over its half-life"


def test_persistence_round_trip_preserves_signature(tmp_path):
    tcl = ToroidalCirculationLayer(state_dir=str(tmp_path))
    pattern = [
        {"N": 1.0, "A": 0.0, "B": 0.0, "X": 0.0, "T": 0.0},
        {"N": 0.0, "A": 1.0, "B": 0.0, "X": 0.0, "T": 0.0},
        {"N": 0.0, "A": 0.0, "B": 1.0, "X": 0.0, "T": 0.0},
    ]
    for _ in range(10):
        for state in pattern:
            tcl.observe(state)
    tcl.save()
    sig1 = tcl.current_signature()

    reloaded = ToroidalCirculationLayer(state_dir=str(tmp_path))
    sig2 = reloaded.current_signature()

    assert sig1.similarity(sig2) == 1.0


def test_intensity_from_crests_handles_objects_and_dicts():
    class _FakeCrest:
        def __init__(self, axis, intensity):
            self.axis = axis
            self.intensity = intensity

    crests = [_FakeCrest("N", 0.6), {"axis": "A", "intensity": 0.3}, _FakeCrest("X", -0.1)]
    out = ToroidalCirculationLayer.intensity_from_crests(crests)
    assert out["N"] == 0.6
    assert out["A"] == 0.3
    assert out["X"] == 0.0  # negative intensities clamp to zero, never subtract


def test_similarity_is_low_between_vortex_and_gradient_signatures():
    vortex = ToroidalSignature(
        "circulating", [(("N", "A", "B"), 5.0)], 0.5, 0.4, 0.1, [], [], 500,
    )
    gradient = ToroidalSignature("gradient", [], 0.09, 0.0, -0.2, ["N"], ["B"], 100)
    assert vortex.similarity(gradient) < 0.5


def test_signature_never_generates_states_only_observes():
    """Boundary rule: attach_to_record must only ever add the signature
    key, never mutate anything else in the passed-in record."""
    tcl = ToroidalCirculationLayer(state_dir="/tmp/nonexistent_should_still_not_raise")
    record = {"existing_key": "untouched", "other": 42}
    result = tcl.attach_to_record(dict(record))
    assert result["existing_key"] == "untouched"
    assert result["other"] == 42
    assert "toroidal_signature" in result
