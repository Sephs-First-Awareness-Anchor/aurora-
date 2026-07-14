"""
tests/test_perturbation_probe.py
===================================
MTSL Phase 6 (2026-07-13): PerturbationProbe -- occlusion/clamp/delay
experiments on copied shadow state, live-reference guard, and correct
previous_vector chaining (regression test for a real bug caught during
development: perturbing a frame's constraint_vector while leaving its
previous_vector stale manufactured a fake delta on completely
unrelated axes).
"""
import pytest

from aurora_dimensional_systems import CrystalProcessingSystem, EvolutionTracker
from aurora_internal.dual_strata.semantic_variant_registry import SemanticVariantRegistry
from aurora_internal.dual_strata.topology_frame import AXES, TopologyFrame
from aurora_internal.dual_strata.topology_tracker import TopologyTracker
from aurora_internal.dual_strata.perturbation_probe import (
    LiveReferenceError,
    PerturbationProbe,
    PerturbationResult,
    record_probe_evidence,
)


def _cyclic_frames(reps: int = 20):
    prev = {a: 0.5 for a in AXES}
    turn = 0
    steps = [("N", "A"), ("A", "B"), ("B", "N")]
    frames = []
    for _rep in range(reps):
        for (loser, gainer) in steps:
            turn += 1
            cur = dict(prev)
            cur[loser] -= 0.2
            cur[gainer] += 0.2
            frames.append(TopologyFrame.from_vectors(
                turn_id=f"t{turn}", timestamp=float(turn),
                constraint_vector=cur, previous_vector=prev,
            ))
            prev = cur
    return frames


# ---- constructor guard: plain frames only ----

def test_rejects_non_topology_frame_objects():
    with pytest.raises(LiveReferenceError):
        PerturbationProbe([{"not": "a frame"}])


def test_rejects_mixed_valid_and_invalid_frames():
    frames = _cyclic_frames(2)
    with pytest.raises(LiveReferenceError):
        PerturbationProbe(list(frames) + ["not a frame"])


def test_accepts_real_topology_frames():
    probe = PerturbationProbe(_cyclic_frames(5))
    assert probe.frame_count == 15


def test_never_mutates_input_frames():
    frames = _cyclic_frames(10)
    original_first_cv = dict(frames[0].constraint_vector)
    probe = PerturbationProbe(frames)
    probe.occlude("N")
    probe.clamp("A", 0.9)
    probe.delay("B", 3)
    assert frames[0].constraint_vector == original_first_cv


# ---- input validation ----

def test_occlude_rejects_unknown_axis():
    probe = PerturbationProbe(_cyclic_frames(5))
    with pytest.raises(ValueError):
        probe.occlude("Q")


def test_clamp_rejects_unknown_axis():
    probe = PerturbationProbe(_cyclic_frames(5))
    with pytest.raises(ValueError):
        probe.clamp("Q", 0.5)


def test_delay_rejects_unknown_axis():
    probe = PerturbationProbe(_cyclic_frames(5))
    with pytest.raises(ValueError):
        probe.delay("Q", 1)


def test_delay_rejects_negative_lag():
    probe = PerturbationProbe(_cyclic_frames(5))
    with pytest.raises(ValueError):
        probe.delay("N", -1)


# ---- chaining correctness (regression: no fake deltas on untouched axes) ----

def test_occluding_an_untouched_axis_has_no_effect():
    # X and T are never modified across the cyclic sequence (always 0.5
    # relative to their own previous frame) -- occluding X must not
    # manufacture a spurious delta once previous_vector is correctly
    # chained through the perturbed sequence.
    probe = PerturbationProbe(_cyclic_frames(20))
    result = probe.occlude("X")
    for scale, delta in result.circulation_fraction_delta.items():
        assert abs(delta) < 1e-6, f"occluding an untouched axis disrupted {scale}: {delta}"
    assert all(not changed for changed in result.regime_changed.values())


def test_clamping_an_axis_to_its_own_constant_value_has_no_effect():
    probe = PerturbationProbe(_cyclic_frames(20))
    result = probe.clamp("T", 0.5)  # T is already constant at 0.5 throughout
    for scale, delta in result.circulation_fraction_delta.items():
        assert abs(delta) < 1e-6


def test_occluding_a_cycle_member_axis_meaningfully_disrupts_circulation():
    probe = PerturbationProbe(_cyclic_frames(20))
    result = probe.occlude("N")  # N is one of the three axes driving the N->A->B->N cycle
    assert abs(result.circulation_fraction_delta["micro"]) > 0.3
    assert result.regime_changed["micro"] is True


def test_delay_zero_lag_is_effectively_a_no_op():
    probe = PerturbationProbe(_cyclic_frames(20))
    result = probe.delay("N", 0)
    for scale, delta in result.circulation_fraction_delta.items():
        assert abs(delta) < 1e-6


def test_delay_nonzero_lag_desynchronizes_a_cycle_member():
    probe = PerturbationProbe(_cyclic_frames(20))
    result = probe.delay("N", 5)
    assert any(abs(d) > 1e-6 for d in result.circulation_fraction_delta.values())


# ---- result shape / summary ----

def test_perturbation_result_fields_and_to_dict():
    probe = PerturbationProbe(_cyclic_frames(20))
    result = probe.occlude("N")
    assert isinstance(result, PerturbationResult)
    assert result.perturbation_type == "occlusion"
    assert result.axis == "N"
    assert result.parameter is None
    d = result.to_dict()
    assert set(d.keys()) == {
        "perturbation_type", "axis", "parameter",
        "baseline_signatures", "perturbed_signatures",
        "circulation_fraction_delta", "regime_changed",
    }
    assert set(d["baseline_signatures"].keys()) == {"micro", "meso", "developmental"}


def test_clamp_result_carries_the_clamped_value():
    probe = PerturbationProbe(_cyclic_frames(20))
    result = probe.clamp("A", 0.9)
    assert result.parameter == 0.9


def test_delay_result_carries_the_lag():
    probe = PerturbationProbe(_cyclic_frames(20))
    result = probe.delay("B", 5)
    assert result.parameter == 5.0


def test_summary_note_reports_regime_shift():
    probe = PerturbationProbe(_cyclic_frames(20))
    disruptive = probe.occlude("N")
    assert "shifted regime" in disruptive.summary_note()
    quiet = probe.occlude("X")
    assert "did not shift regime" in quiet.summary_note()


def test_clamp_value_is_bounded_0_to_1():
    probe = PerturbationProbe(_cyclic_frames(5))
    result = probe.clamp("A", 5.0)
    assert result.parameter == 1.0
    result2 = probe.clamp("A", -5.0)
    assert result2.parameter == 0.0


def test_baseline_is_cached_across_multiple_calls():
    probe = PerturbationProbe(_cyclic_frames(20))
    b1 = probe._baseline_signatures()
    b2 = probe._baseline_signatures()
    assert b1 is b2


# ---- record_probe_evidence: connector to SemanticVariantRegistry (FIX-A012) ----

def _driven_tracker_and_frames(reps: int = 20):
    frames = _cyclic_frames(reps)
    tracker = TopologyTracker(state_dir=None)
    for f in frames:
        tracker.observe(f)
    return tracker, frames


def test_record_probe_evidence_stores_source_tagged_note():
    tracker, frames = _driven_tracker_and_frames()
    dps = CrystalProcessingSystem(tracker=EvolutionTracker())
    registry = SemanticVariantRegistry(state_dir=None)
    ts = tracker.signature("meso")
    match = registry.match_or_create(
        manifold_slot_id="MANIFOLD:X:NC[T:OPERATOR]xNC[N:OPERATOR]",
        base_meaning_form="N^1*A^1*B^1", ts=ts, dps=dps,
    )
    assert match is not None

    probe = PerturbationProbe(frames)
    result = probe.occlude("N")
    recorded = record_probe_evidence(
        registry, dps, result,
        manifold_slot_id=match.variant.manifold_slot_id,
        topology_id=match.variant.topology_id,
        source="dream",
    )
    assert recorded is not None
    assert len(recorded.dream_evidence) == 1
    assert recorded.dream_evidence[0]["source"] == "dream"
    assert recorded.dream_evidence[0]["note"] == result.summary_note()


def test_record_probe_evidence_never_alone_promotes():
    tracker, frames = _driven_tracker_and_frames()
    dps = CrystalProcessingSystem(tracker=EvolutionTracker())
    registry = SemanticVariantRegistry(state_dir=None)
    ts = tracker.signature("meso")
    match = registry.match_or_create(
        manifold_slot_id="MANIFOLD:X:NC[T:OPERATOR]xNC[N:OPERATOR]",
        base_meaning_form="N^1*A^1*B^1", ts=ts, dps=dps,
    )
    probe = PerturbationProbe(frames)
    for _ in range(50):
        recorded = record_probe_evidence(
            registry, dps, probe.occlude("N"),
            manifold_slot_id=match.variant.manifold_slot_id,
            topology_id=match.variant.topology_id,
            source="classroom",
        )
    assert recorded.status != "promoted"


def test_record_probe_evidence_none_without_registry():
    _tracker, frames = _driven_tracker_and_frames(reps=2)
    probe = PerturbationProbe(frames)
    result = probe.occlude("N")
    assert record_probe_evidence(None, None, result, manifold_slot_id="x", topology_id="y", source="dream") is None
