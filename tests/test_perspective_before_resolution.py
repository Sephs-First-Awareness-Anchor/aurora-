"""Regression coverage for perspective projection before Build 714 refinement."""
from types import SimpleNamespace

import aurora_representational_resolution as rr
from aurora_representational_address import RepresentationalRef
from aurora_internal.dual_strata.predictive_stager import PRESSURE_PERSPECTIVES


def _coarse():
    return RepresentationalRef.for_c1("X", "MAGNITUDE", "A")


def _source():
    return RepresentationalRef.for_c2(
        "X", "MAGNITUDE", "A", "T", "POLARITY", "B", "DIFFERENCE",
    )


def _bare_engine():
    engine = rr.RepresentationalResolutionEngine.__new__(rr.RepresentationalResolutionEngine)
    engine.genealogy = SimpleNamespace(abilities={}, tick_count=0)
    engine.root = None
    engine._genealogy_records = {}
    engine._active_resolutions = {}
    engine._resolution_events = []
    engine._cost_ledger = {}
    engine._active_stage_for_ref = {}
    engine._provisional_reads = {}
    engine._candidate_downstream_effects = {}
    engine._candidate_attempt_counts = {}
    engine._in_complete_field_inquiry = False
    engine._projection_state()
    return engine


def test_native_dimension_ownership_is_projection_geometry():
    expected = {
        "MAGNITUDE": "X", "POLARITY": "T", "COST": "N",
        "DIFFERENCE": "B", "OPERATOR": "A",
    }
    for dimension, axis in expected.items():
        assert rr.perspective_owner_axis(dimension) == axis
    for axis in ("X", "T", "N", "B", "A"):
        assert rr.perspective_owner_axis(axis) == axis


def test_projection_reuses_predictive_stagers_exact_31_lenses():
    assert rr._canonical_perspectives() == tuple(tuple(p) for p in PRESSURE_PERSPECTIVES)
    assert len(rr._canonical_perspectives()) == 31


def test_one_lens_reveals_multiple_latent_fields_without_refining_base():
    base, source = _coarse(), _source()
    projections = rr.build_perspective_projections(
        base, [("REFAB:source", source, {"structural": True})], max_projections=20,
    )
    t_view = next(p for p in projections if p["pressure_perspective"] == ["T"])
    projected = RepresentationalRef.decode(t_view["projected_ref"])
    assert t_view["exposed_fields"] == {"sub_law_c": "T", "sub_law_d": "POLARITY"}
    assert projected.sub_law_c == "T" and projected.sub_law_d == "POLARITY"
    assert base.sub_law_c is None and base.sub_law_d is None


def test_projection_stage_precedes_field_inquiry_when_real_mirror_exists():
    engine, base, source = _bare_engine(), _coarse(), _source()
    structural = {
        "field": "sub_law_c", "candidate_value": "T", "source": "collision:c1",
        "counterpart_ability_id": "REAL:source", "evidence": {"collision": True},
        "origin": "collision",
    }
    engine.inadequacy_pressure = lambda ref: 0.7
    engine.unresolved_field_candidates = lambda ref: [structural]
    engine._ref_from_ability_id = lambda aid: source if aid == "REAL:source" else None
    engine.stage_field_inquiry = lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("field inquiry must not run before perspective projection"))
    staged = engine.investigate_if_pressured(base, consumer="test")
    assert staged["mode"] == "perspective_projection"
    assert staged["stage"] is None
    assert engine.current_resolution(base).encode() == base.encode()


def test_domain_hypothesis_is_never_a_projection_mirror():
    engine, base = _bare_engine(), _coarse()
    domain = {
        "field": "sub_law_c", "candidate_value": "T",
        "source": "domain_hypothesis:sub_law_c=T",
        "counterpart_ability_id": "REFHYP:test", "evidence": {"origin": "lawful_domain"},
        "origin": "domain_hypothesis",
    }
    engine.inadequacy_pressure = lambda ref: 0.7
    engine.unresolved_field_candidates = lambda ref: [domain]
    engine.stage_field_inquiry = lambda ref, candidate, consumer: [{"stage_id": None}]
    staged = engine.investigate_if_pressured(base, consumer="test")
    assert staged["mode"] == "field_inquiry"
    assert staged["candidate"]["origin"] == "domain_hypothesis"


def test_provisional_projection_is_view_not_current_resolution():
    engine, base, source = _bare_engine(), _coarse(), _source()
    projection = rr.build_perspective_projections(base, [("REAL:source", source, {})], max_projections=20)[0]
    engine._active_stage_for_ref[base.encode()] = {
        "mode": "perspective_projection", "stage": None, "candidate": projection,
        "consumer": "test", "context_scope": None,
    }
    view = engine.provisional_resolution(base)
    assert view.encode() == projection["projected_ref"] != base.encode()
    assert engine.current_resolution(base).encode() == base.encode()
    assert engine._active_resolutions == {} and engine._genealogy_records == {}


def test_projection_effect_records_full_view_not_one_field():
    engine, base, source = _bare_engine(), _coarse(), _source()
    projection = next(p for p in rr.build_perspective_projections(
        base, [("REAL:source", source, {})], max_projections=20,
    ) if p["pressure_perspective"] == ["T"])
    engine._active_stage_for_ref[base.encode()] = {
        "mode": "perspective_projection", "stage": None, "candidate": projection,
        "consumer": "test", "context_scope": None,
    }
    record = engine.record_candidate_downstream_effect(
        base, consumer="test", downstream_difference={"ranking_changed": True},
        action_or_prediction_affected="candidate_relevance",
    )
    projected = RepresentationalRef.decode(record["representation_with_candidate"])
    assert record["mode"] == "perspective_projection"
    assert projected.sub_law_c == "T" and projected.sub_law_d == "POLARITY"
    assert engine.current_resolution(base).encode() == base.encode()


def test_successful_projection_satisfies_distinction_without_resolution(monkeypatch):
    engine, base, source = _bare_engine(), _coarse(), _source()
    projection = rr.build_perspective_projections(base, [("REAL:source", source, {})], max_projections=1)[0]
    pending = {"mode": "perspective_projection", "stage": None, "candidate": projection,
               "consumer": "test", "context_scope": None}
    engine._active_stage_for_ref[base.encode()] = pending
    engine._provisional_reads[base.encode()] = 1
    engine._candidate_downstream_effects[base.encode()] = {
        "mode": "perspective_projection", "downstream_difference_produced": {"prediction_changed": True}}
    engine.inadequacy_pressure = lambda ref: 0.6
    engine.resolve_field = lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("projection adequacy must never resolve a field"))
    monkeypatch.setattr(rr._BaseEngine, "record_participation", lambda self, ref, **kwargs: "observed")
    result = engine.record_participation(
        base, pressure_before={a: 1.0 for a in "XTNBA"},
        pressure_after={a: 0.5 for a in "XTNBA"}, source="test",
        candidate_evaluation={"actual_consequence": {"observed": True},
                              "baseline_error": 0.8, "candidate_conditioned_error": 0.2},
    )
    assert result == "observed"
    assert engine._active_stage_for_ref[base.encode()]["mode"] == "perspective_projection"
    assert engine._active_resolutions == {} and engine._genealogy_records == {}
    assert engine.recent_projection_events()[-1]["outcome"] == "adequate"


def test_failed_projection_releases_optic_and_allows_resolution_path(monkeypatch):
    engine, base, source = _bare_engine(), _coarse(), _source()
    projection = rr.build_perspective_projections(base, [("REAL:source", source, {})], max_projections=1)[0]
    pending = {"mode": "perspective_projection", "stage": None, "candidate": projection,
               "consumer": "test", "context_scope": None}
    engine._active_stage_for_ref[base.encode()] = pending
    engine._provisional_reads[base.encode()] = 1
    engine._candidate_downstream_effects[base.encode()] = {
        "mode": "perspective_projection", "downstream_difference_produced": {"prediction_changed": True}}
    monkeypatch.setattr(rr._BaseEngine, "record_participation", lambda self, ref, **kwargs: "observed")
    escalations = []
    engine.investigate_if_pressured = lambda ref, **kwargs: escalations.append(ref.encode())
    engine.record_participation(
        base, pressure_before={a: 1.0 for a in "XTNBA"},
        pressure_after={a: 0.5 for a in "XTNBA"}, source="test",
        candidate_evaluation={"actual_consequence": {"observed": True},
                              "baseline_error": 0.3, "candidate_conditioned_error": 0.4},
    )
    assert base.encode() not in engine._active_stage_for_ref
    assert engine._projection_attempt_counts[projection["projection_id"]] == 1
    assert escalations == [base.encode()]
    assert engine.recent_projection_events()[-1]["outcome"] == "failed"


def test_public_projection_layer_has_no_direct_promotion_authority():
    source = open(rr.__file__, encoding="utf-8").read()
    assert ".resolve_field(" not in source
    assert "_in_complete_field_inquiry = True" not in source
