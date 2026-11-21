#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_perspective_merge_repair.py -- the perspective engine as both of its
branches built it, after the Sep 26 merge (40587f4) mixed them.

That merge of ceph/progressive-perspective-consumption with main kept one
branch's method headers and the other's bodies.  On main it left:

- _projection_event formatting a `c` that no longer existed, so every staged,
  adequate or failed projection raised NameError;
- _projection_frontiers cleared at the end of every field inquiry but never
  created, so complete_field_inquiry raised AttributeError;
- record_pressure_observation with record_participation's body (NameError on
  candidate_evaluation) and no record_participation override, so a real
  consumer's evaluation never judged the projection it used;
- provisional_resolution without the demand edge its docstring describes;
- build_perspective_projections without either branch's duplicate-view rule.

Each piece is restored as its own branch wrote it.  Sir then chose the two
progressive pieces that change when she inquires (Nov 18): scores without a
candidate evaluation go to record_pressure_observation, so raw Habitat
pressure no longer stages an inquiry and her own provisional read does; and
the frontier is cached, one structural scan per inadequacy episode.

With no real mirror, the lawful-domain bootstrap keeps Build 714's per-pass
bound.  Offered at full capacity, it lets a finer field (sub_law_d) be staged
before the field it refines, where the provisional view changes nothing
downstream, so the inquiry is never evaluated and never released.
"""
from __future__ import annotations

import inspect

import aurora_representational_resolution as rr
from aurora_internal.constraint_genealogy import (
    AXES, ConstraintGenealogyLogger, GenealogyConfig, TraceItem)
from aurora_representational_address import RepresentationalRef
from aurora_representational_resolution import RepresentationalResolutionEngine


def _fresh(tmp_path, name="merge_repair"):
    genealogy = ConstraintGenealogyLogger(
        name, config=GenealogyConfig(), output_dir=str(tmp_path / name / "g"))
    return genealogy, RepresentationalResolutionEngine(
        genealogy, state_dir=str(tmp_path / name / "s"))


def test_observer_and_consumer_are_separate_methods_again():
    cls = RepresentationalResolutionEngine
    assert "record_participation" in cls.__dict__
    assert "record_pressure_observation" in cls.__dict__
    obs = inspect.signature(cls.record_pressure_observation).parameters
    assert "candidate_evaluation" not in obs
    assert inspect.signature(cls.record_participation).parameters[
        "candidate_evaluation"].default is None


def test_projection_event_records_the_staged_candidate(tmp_path):
    _g, engine = _fresh(tmp_path)
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    pending = {"candidate": {"projection_id": "rproj_x", "projected_ref": "P",
                             "pressure_perspective": ["N"], "source_ref": "S"}}
    engine._projection_event(ref, pending, "staged")
    event = engine.recent_projection_events(1)[-1]
    assert event["projection_id"] == "rproj_x"
    assert event["pressure_perspective"] == ["N"]
    assert event["outcome"] == "staged"


def test_episode_end_hooks_do_not_raise(tmp_path):
    _g, engine = _fresh(tmp_path)
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    engine._clear_frontier_if_pressure_resolved(ref)
    assert engine._projection_frontiers == {}


def test_observation_never_stages_and_restores_the_hold(tmp_path):
    genealogy, engine = _fresh(tmp_path)
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    sibling = RepresentationalRef.for_m21("T", "MAGNITUDE", "B",
                                          col_law_c="N", col_law_d="COST")
    engine.ensure_registered(sibling)
    for ax in ["B", "N", "X"] * 5:
        engine.record_pressure_observation(
            ref, pressure_before={a: (0.3 if a == ax else 0.0) for a in AXES},
            pressure_after={a: 0.0 for a in AXES}, source="observer_test")
    assert engine._active_stage_for_ref == {}
    assert engine._projection_resolution_hold is False


def test_duplicate_projected_views_keep_one_cheapest_lens():
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    src = RepresentationalRef.for_m21("T", "MAGNITUDE", "B",
                                      col_law_c="N", col_law_d="COST")
    views = rr.build_perspective_projections(
        ref, [("a", src, {}), ("b", src, {"structural_pressure": 0.9})],
        max_projections=None)
    keys = [v["projection_view_key"] for v in views]
    assert len(keys) == len(set(keys))
    assert views == sorted(views, key=rr._projection_priority)


def test_no_mirror_bootstrap_walks_one_field_at_a_time(tmp_path):
    _g, engine = _fresh(tmp_path)
    ref = RepresentationalRef.for_c1("N", "OPERATOR", "A")
    assert engine._native_structural_finders_available()
    frontier = {"projections": [], "structural_candidates": [], "refresh_used": False}
    candidates = engine._field_candidates_after_frontier(ref, frontier)
    assert candidates
    assert len(candidates) <= rr.MAX_CANDIDATE_FIELDS_PER_PASS
    assert {c["field"] for c in candidates} == {ref.unresolved_fields()[0]}
    assert all(c["origin"] == "domain_hypothesis" for c in candidates)


def test_observation_leaves_a_consumers_pending_projection_and_reads(tmp_path):
    _g, engine = _fresh(tmp_path)
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    pending = {"mode": "perspective_projection", "stage": None,
               "candidate": {"projection_id": "rproj_y", "projected_ref": ref.encode()},
               "consumer": "habitat_motivation", "context_scope": None}
    engine._active_stage_for_ref[ref.encode()] = pending
    engine._provisional_reads[ref.encode()] = 3
    engine.record_pressure_observation(
        ref, pressure_before={a: 1.0 for a in AXES},
        pressure_after={a: 0.5 for a in AXES}, source="test")
    assert engine._active_stage_for_ref[ref.encode()] is pending
    assert engine._provisional_reads[ref.encode()] == 3


def test_score_bridge_routes_observation_and_consumption_apart(tmp_path, monkeypatch):
    calls = []

    class _Engine:
        def record_pressure_observation(self, *a, **k):
            calls.append("observation")

        def record_participation(self, *a, **k):
            calls.append("participation")

    monkeypatch.setattr(rr, "get_or_create_engine", lambda systems: _Engine())
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B").encode()
    rr.record_ref_participation_from_scores({"x": 1}, ref, {"s": 0.4}, source="habitat")
    rr.record_ref_participation_from_scores(
        {"x": 1}, ref, {"s": 0.4}, source="habitat",
        candidate_evaluation={"baseline_error": 0.5, "candidate_conditioned_error": 0.1})
    assert calls == ["observation", "participation"]
