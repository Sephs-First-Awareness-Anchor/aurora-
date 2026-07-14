"""
tests/test_cers_topology_context.py
======================================
MTSL Phase 4 (2026-07-13): cers_converge()'s optional TopologyContext --
byte-identical behavior when absent, bounded raise-only semantic
salience/hesitation when present, and the manual authority-stage gate.
"""
from aurora_internal.dual_strata.crest import Crest
from aurora_internal.dual_strata.cers_regulator import (
    cers_converge,
    PotentialTracker,
    TopologyContext,
    MAX_SEMANTIC_SALIENCE_RAISE,
    MTSL_AUTHORITY_STAGE,
)

_CONFLICT_CRESTS = (
    Crest(label="comfort", intensity=0.6, axis="B"),
    Crest(label="urgency", intensity=0.55, axis="N"),
    Crest(label="steady", intensity=0.2, axis="X"),
)
_QUIET_CRESTS = (Crest(label="steady", intensity=0.4, axis="X"),)


def _ctx(**overrides):
    base = dict(
        schema_version=1, turn_id="t1", manifold_slot_id="MANIFOLD:X:NC[T:OPERATOR]xNC[N:OPERATOR]",
        variant_confidence=0.5, variant_status="provisional", variant_created=False,
        semantic_ambiguity=False, circulation_fraction=0.5, regime="circulating",
    )
    base.update(overrides)
    return TopologyContext(**base)


# ---- absent context: byte-identical guarantee ----

def test_default_authority_stage_is_1_record_only():
    assert MTSL_AUTHORITY_STAGE == 1


def test_absent_context_new_fields_stay_at_inert_defaults():
    tracker = PotentialTracker()
    _crest, verdict = cers_converge(_CONFLICT_CRESTS, tracker)
    assert verdict.semantic_salience == 0.0
    assert verdict.semantic_hesitation is False
    assert verdict.semantic_salience_proposed == 0.0
    assert verdict.semantic_hesitation_proposed is False
    assert verdict.semantic_mode is None
    assert verdict.response_bias == 0.0
    assert verdict.variant_confidence == 0.0


def test_absent_context_preexisting_fields_unaffected_across_all_three_branches():
    # conflict branch, geometry-deviation branch, and clean-agreement branch --
    # topology_context=None must never perturb any of them.
    cases = [
        (_CONFLICT_CRESTS, {}),
        (_QUIET_CRESTS, {"geometry_coord_id": "MANIFOLD:X:NC[T:OPERATOR]xNC[N:OPERATOR]",
                          "geometry_distortion_normalized": 0.9, "geometry_is_new": False}),
        (_QUIET_CRESTS, {}),
    ]
    for sub_crests, kwargs in cases:
        tracker_a = PotentialTracker()
        tracker_b = PotentialTracker()
        crest_a, verdict_a = cers_converge(sub_crests, tracker_a, **kwargs)
        crest_b, verdict_b = cers_converge(sub_crests, tracker_b, topology_context=None, **kwargs)
        assert crest_a.label == crest_b.label
        assert crest_a.intensity == crest_b.intensity
        assert crest_a.axis == crest_b.axis
        assert verdict_a.permitted == verdict_b.permitted
        assert verdict_a.legacy_label == verdict_b.legacy_label
        assert verdict_a.cers_label == verdict_b.cers_label
        assert verdict_a.agrees_with_legacy == verdict_b.agrees_with_legacy
        assert [c.to_dict() for c in verdict_a.conflicts] == [c.to_dict() for c in verdict_b.conflicts]


# ---- authority staging (manual, evidence-gated) ----

def test_stage1_computes_proposed_but_never_applies():
    tracker = PotentialTracker()
    ctx = _ctx(semantic_ambiguity=True, variant_created=True)
    _crest, verdict = cers_converge(_QUIET_CRESTS, tracker, topology_context=ctx, authority_stage=1)
    assert verdict.semantic_salience == 0.0
    assert verdict.semantic_hesitation is False
    assert verdict.semantic_salience_proposed > 0.0
    assert verdict.semantic_hesitation_proposed is True


def test_stage2_applies_the_proposed_values():
    tracker = PotentialTracker()
    ctx = _ctx(semantic_ambiguity=True, variant_created=True)
    _crest, verdict = cers_converge(_QUIET_CRESTS, tracker, topology_context=ctx, authority_stage=2)
    assert verdict.semantic_salience == verdict.semantic_salience_proposed
    assert verdict.semantic_hesitation == verdict.semantic_hesitation_proposed


# ---- bounded, raise-only semantic salience ----

def test_salience_raise_never_exceeds_configured_bound():
    tracker = PotentialTracker()
    ctx = _ctx(semantic_ambiguity=True, variant_created=True)  # both boosts stack
    _crest, verdict = cers_converge(_QUIET_CRESTS, tracker, topology_context=ctx, authority_stage=2)
    assert verdict.semantic_salience_proposed <= MAX_SEMANTIC_SALIENCE_RAISE
    assert verdict.semantic_salience_proposed >= 0.0


def test_salience_zero_when_context_carries_no_boost_signal():
    tracker = PotentialTracker()
    ctx = _ctx(semantic_ambiguity=False, variant_created=False)
    _crest, verdict = cers_converge(_QUIET_CRESTS, tracker, topology_context=ctx, authority_stage=2)
    assert verdict.semantic_salience == 0.0
    assert verdict.semantic_salience_proposed == 0.0


# ---- raise-only hesitation: can only turn True, never suppress an existing True ----

def test_hesitation_can_be_raised_from_a_permitted_baseline():
    tracker = PotentialTracker()
    baseline_crest, baseline_verdict = cers_converge(_QUIET_CRESTS, PotentialTracker())
    assert baseline_verdict.permitted is True  # quiet crests, no conflict, no geometry deviation
    ctx = _ctx(semantic_ambiguity=True)
    _crest, verdict = cers_converge(_QUIET_CRESTS, tracker, topology_context=ctx, authority_stage=2)
    assert verdict.permitted is True  # topology_context never touches `permitted` itself
    assert verdict.semantic_hesitation is True  # but semantic_hesitation was raised


def test_hesitation_stays_true_when_base_verdict_already_denied_even_without_ambiguity():
    tracker = PotentialTracker()
    ctx = _ctx(semantic_ambiguity=False)  # no ambiguity boost at all
    _crest, verdict = cers_converge(_CONFLICT_CRESTS, tracker, topology_context=ctx, authority_stage=2)
    assert verdict.permitted is False  # this crest set is a real structural conflict
    assert verdict.semantic_hesitation is True  # OR'd with the base verdict's own denial


# ---- semantic_mode labels (informational, never stage-gated) ----

def test_semantic_mode_ambiguous():
    tracker = PotentialTracker()
    ctx = _ctx(semantic_ambiguity=True)
    _crest, verdict = cers_converge(_QUIET_CRESTS, tracker, topology_context=ctx, authority_stage=1)
    assert verdict.semantic_mode == "ambiguous"


def test_semantic_mode_undetermined_when_no_variant():
    tracker = PotentialTracker()
    ctx = _ctx(semantic_ambiguity=False, variant_status=None)
    _crest, verdict = cers_converge(_QUIET_CRESTS, tracker, topology_context=ctx, authority_stage=1)
    assert verdict.semantic_mode == "undetermined"


def test_semantic_mode_organized_when_circulating():
    tracker = PotentialTracker()
    ctx = _ctx(semantic_ambiguity=False, variant_status="reinforced", regime="circulating")
    _crest, verdict = cers_converge(_QUIET_CRESTS, tracker, topology_context=ctx, authority_stage=1)
    assert verdict.semantic_mode == "organized"


def test_semantic_mode_directional_when_gradient_or_mixed():
    tracker = PotentialTracker()
    for regime in ("gradient", "mixed"):
        ctx = _ctx(semantic_ambiguity=False, variant_status="reinforced", regime=regime)
        _crest, verdict = cers_converge(_QUIET_CRESTS, tracker, topology_context=ctx, authority_stage=1)
        assert verdict.semantic_mode == "directional"


def test_semantic_mode_not_gated_by_authority_stage():
    # semantic_mode is informational only -- it doesn't raise anything CERS
    # decides, so it should be identical at stage 1 and stage 2.
    ctx = _ctx(semantic_ambiguity=True)
    _c1, v1 = cers_converge(_QUIET_CRESTS, PotentialTracker(), topology_context=ctx, authority_stage=1)
    _c2, v2 = cers_converge(_QUIET_CRESTS, PotentialTracker(), topology_context=ctx, authority_stage=2)
    assert v1.semantic_mode == v2.semantic_mode == "ambiguous"


# ---- response_bias ----

def test_response_bias_high_when_ambiguous():
    tracker = PotentialTracker()
    ctx = _ctx(semantic_ambiguity=True)
    _crest, verdict = cers_converge(_QUIET_CRESTS, tracker, topology_context=ctx, authority_stage=1)
    assert verdict.response_bias == 0.7


def test_response_bias_scales_inversely_with_confidence_when_not_ambiguous():
    tracker = PotentialTracker()
    ctx_low_conf = _ctx(semantic_ambiguity=False, variant_confidence=0.1)
    ctx_high_conf = _ctx(semantic_ambiguity=False, variant_confidence=0.9)
    _c1, v_low = cers_converge(_QUIET_CRESTS, tracker, topology_context=ctx_low_conf, authority_stage=1)
    _c2, v_high = cers_converge(_QUIET_CRESTS, tracker, topology_context=ctx_high_conf, authority_stage=1)
    assert v_low.response_bias > v_high.response_bias
    assert 0.0 <= v_low.response_bias <= 1.0
    assert 0.0 <= v_high.response_bias <= 1.0


# ---- variant_confidence passthrough ----

def test_variant_confidence_carried_through_verbatim():
    tracker = PotentialTracker()
    ctx = _ctx(variant_confidence=0.73)
    _crest, verdict = cers_converge(_QUIET_CRESTS, tracker, topology_context=ctx, authority_stage=1)
    assert verdict.variant_confidence == 0.73


# ---- surface_compressed_dict: exactly the directive's five keys ----

def test_surface_compressed_dict_has_exactly_five_keys():
    tracker = PotentialTracker()
    ctx = _ctx(semantic_ambiguity=True)
    _crest, verdict = cers_converge(_QUIET_CRESTS, tracker, topology_context=ctx, authority_stage=2)
    compressed = verdict.surface_compressed_dict()
    assert set(compressed.keys()) == {
        "semantic_salience", "semantic_hesitation", "variant_confidence",
        "semantic_mode", "response_bias",
    }
    assert "semantic_salience_proposed" not in compressed
    assert "semantic_hesitation_proposed" not in compressed
    assert "conflicts" not in compressed
