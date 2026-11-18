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

Each piece is restored as its own branch wrote it.  Two progressive-branch
pieces are left for Sir because they change when she inquires: routing scores
without a candidate evaluation to record_pressure_observation (so raw Habitat
pressure stops staging inquiry), and the cached frontier (one structural scan
per inadequacy episode).  Tests that need them still fail.
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
