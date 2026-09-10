"""Regression coverage for progressive perspective widening and observer/consumer separation."""
from pathlib import Path
from types import SimpleNamespace

import aurora_representational_resolution as rr
from aurora_representational_address import RepresentationalRef


def _coarse():
    return RepresentationalRef.for_c1("X", "MAGNITUDE", "A")


def _source_one():
    return RepresentationalRef.for_c2(
        "X", "MAGNITUDE", "A", "T", "POLARITY", "B", "DIFFERENCE",
    )


def _source_two():
    return RepresentationalRef.for_c2(
        "X", "MAGNITUDE", "A", "N", "COST", "A", "OPERATOR",
    )


def _bare_engine():
    engine = rr.RepresentationalResolutionEngine.__new__(
        rr.RepresentationalResolutionEngine
    )
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


def _structural_sources():
    return [
        ("REAL:one", _source_one(), {"structural_pressure": 0.4}),
        ("REAL:two", _source_two(), {"structural_pressure": 0.9}),
    ]


def test_progressive_frontier_is_not_epistemically_truncated_at_five():
    engine = _bare_engine()
    base = _coarse()
    projections = rr.build_perspective_projections(
        base, _structural_sources(), max_projections=None,
    )
    assert len(projections) > rr.MAX_CANDIDATE_FIELDS_PER_PASS

    engine.inadequacy_pressure = lambda _ref: 0.7
    engine._projection_sources_for_ref = lambda _ref: _structural_sources()
    for projection in projections[: rr.MAX_CANDIDATE_FIELDS_PER_PASS]:
        engine._projection_attempt_counts[projection["projection_id"]] = 1

    engine.stage_field_inquiry = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("field inquiry must not start while a lawful projection remains")
    )
    staged = engine.investigate_if_pressured(base, consumer="test")

    assert staged["mode"] == "perspective_projection"
    assert staged["candidate"]["projection_id"] == projections[
        rr.MAX_CANDIDATE_FIELDS_PER_PASS
    ]["projection_id"]
    assert staged["available_projection_count"] == len(projections)


def test_field_inquiry_requires_explicit_projection_frontier_exhaustion():
    engine = _bare_engine()
    base = _coarse()
    projections = rr.build_perspective_projections(
        base, _structural_sources(), max_projections=None,
    )
    engine.inadequacy_pressure = lambda _ref: 0.7
    engine._projection_sources_for_ref = lambda _ref: _structural_sources()
    for projection in projections:
        engine._projection_attempt_counts[projection["projection_id"]] = 1

    seen_capacity = []
    fallback = {
        "field": "sub_law_c",
        "candidate_value": "T",
        "origin": "domain_hypothesis",
        "source": "test",
        "counterpart_ability_id": "REFHYP:test",
    }

    def candidates(_ref, *, max_candidates):
        seen_capacity.append(max_candidates)
        return [fallback]

    engine.unresolved_field_candidates = candidates
    engine.stage_field_inquiry = lambda *args, **kwargs: [{"stage_id": "s"}]

    staged = engine.investigate_if_pressured(base, consumer="test")
    assert staged["mode"] == "field_inquiry"
    assert seen_capacity == [rr._complete_candidate_capacity(base)]
    event = engine.recent_projection_events()[-1]
    assert event["outcome"] == "frontier_exhausted"
    assert event["evaluation"]["projection_count"] == len(projections)
    assert event["evaluation"]["attempted_count"] == len(projections)


def test_structural_search_is_amortized_across_failed_lenses():
    engine = _bare_engine()
    base = _coarse()
    projections = rr.build_perspective_projections(
        base, _structural_sources(), max_projections=None,
    )
    assert len(projections) > 1
    engine.inadequacy_pressure = lambda _ref: 0.7

    scans = []
    def sources(_ref):
        scans.append("scan")
        return _structural_sources()
    engine._projection_sources_for_ref = sources

    fallback = {
        "field": "sub_law_c",
        "candidate_value": "T",
        "origin": "domain_hypothesis",
        "source": "test",
        "counterpart_ability_id": "REFHYP:test",
    }
    engine.unresolved_field_candidates = lambda _ref, **_kwargs: [fallback]
    engine.stage_field_inquiry = lambda *args, **kwargs: [{"stage_id": "s"}]

    # Consume the cached frontier without allowing each failed lens to rescan.
    for expected in projections:
        staged = engine.investigate_if_pressured(base, consumer="test")
        assert staged["mode"] == "perspective_projection"
        assert staged["candidate"]["projection_view_key"] == expected["projection_view_key"]
        view_key = staged["candidate"]["projection_view_key"]
        engine._projection_attempt_counts[view_key] = 1
        engine._active_stage_for_ref.pop(base.encode(), None)

    # Exhaustion permits one refresh and then the field inquiry.
    staged = engine.investigate_if_pressured(base, consumer="test")
    assert staged["mode"] == "field_inquiry"
    assert scans == ["scan", "scan"]


def test_duplicate_projected_view_keeps_cheapest_strongest_structural_provenance():
    base = _coarse()
    same_view_weak = _source_one()
    same_view_strong = _source_one()
    projections = rr.build_perspective_projections(
        base,
        [
            ("weak", same_view_weak, {"structural_pressure": 0.1}),
            ("strong", same_view_strong, {"structural_pressure": 0.9}),
        ],
        max_projections=None,
    )
    t_view = next(
        item for item in projections
        if item["pressure_perspective"] == ["T"]
    )
    assert t_view["counterpart_ability_id"] == "strong"
    assert t_view["evidence"]["structural_pressure"] == 0.9


def test_same_projected_representation_keeps_only_cheapest_lens():
    base = _coarse()
    source = RepresentationalRef.for_c2(
        "X", "MAGNITUDE", "A", "T", "POLARITY", None, None,
    )
    projections = rr.build_perspective_projections(
        base, [("source", source, {"structural_pressure": 0.5})],
        max_projections=None,
    )
    encoded = RepresentationalRef.for_c2(
        "X", "MAGNITUDE", "A", "T", "POLARITY", None, None,
    ).encode()
    matches = [item for item in projections if item["projected_ref"] == encoded]
    assert len(matches) == 1
    assert matches[0]["pressure_perspective"] == ["T"]


def test_pressure_observer_cannot_stage_or_complete_resolution(monkeypatch):
    engine = _bare_engine()
    base = _coarse()
    calls = []

    def base_record(self, ref, **kwargs):
        calls.append({
            "hold": self._projection_resolution_hold,
            "candidate_evaluation": kwargs.get("candidate_evaluation"),
        })
        self.investigate_if_pressured(ref, consumer="observer")
        return "observed"

    monkeypatch.setattr(rr._BaseEngine, "record_participation", base_record)
    engine.inadequacy_pressure = lambda _ref: 0.8
    engine._projection_sources_for_ref = lambda _ref: _structural_sources()

    result = engine.record_pressure_observation(
        base,
        pressure_before={axis: 1.0 for axis in "XTNBA"},
        pressure_after={axis: 0.5 for axis in "XTNBA"},
        source="rcec",
    )

    assert result == "observed"
    assert calls == [{"hold": True, "candidate_evaluation": None}]
    assert engine._active_stage_for_ref == {}


def test_provisional_reader_is_the_demand_edge_after_pressure_exists():
    engine = _bare_engine()
    base = _coarse()
    engine.inadequacy_pressure = lambda _ref: 0.8
    engine._projection_sources_for_ref = lambda _ref: _structural_sources()

    assert engine._active_stage_for_ref == {}
    view = engine.provisional_resolution(base, consumer="habitat_motivation")
    pending = engine._active_stage_for_ref[base.encode()]

    assert pending["mode"] == "perspective_projection"
    assert pending["consumer"] == "habitat_motivation"
    assert view.encode() == pending["candidate"]["projected_ref"]
    assert view.encode() != base.encode()
    assert engine._provisional_reads[base.encode()] == 1


def test_pressure_observer_cannot_steal_real_consumers_pending_projection(monkeypatch):
    engine = _bare_engine()
    base = _coarse()
    projection = rr.build_perspective_projections(
        base, _structural_sources(), max_projections=None,
    )[0]
    pending = {
        "mode": "perspective_projection",
        "stage": None,
        "candidate": projection,
        "consumer": "habitat_motivation",
        "context_scope": None,
    }
    engine._active_stage_for_ref[base.encode()] = pending

    def base_record(self, ref, **kwargs):
        assert self._active_stage_for_ref[ref.encode()] is pending
        assert self._projection_resolution_hold is True
        return "observed"

    monkeypatch.setattr(rr._BaseEngine, "record_participation", base_record)
    engine.record_pressure_observation(
        base,
        pressure_before={axis: 1.0 for axis in "XTNBA"},
        pressure_after={axis: 0.5 for axis in "XTNBA"},
        source="rcec",
    )
    assert engine._active_stage_for_ref[base.encode()] is pending
    assert engine._provisional_reads[base.encode()] == 0


def test_score_bridge_requires_candidate_evaluation_for_consumption(monkeypatch):
    base = _coarse()
    calls = {"observer": 0, "consumer": 0}

    class FakeEngine:
        def record_pressure_observation(self, *args, **kwargs):
            calls["observer"] += 1

        def record_participation(self, *args, **kwargs):
            calls["consumer"] += 1

    monkeypatch.setattr(rr, "get_or_create_engine", lambda systems: FakeEngine())

    rr.record_ref_participation_from_scores(
        {"genealogy": object()},
        base.encode(),
        {"causal_accuracy": 0.5},
        source="rcec_causal_evaluation",
    )
    assert calls == {"observer": 1, "consumer": 0}

    rr.record_ref_participation_from_scores(
        {"genealogy": object()},
        base.encode(),
        {"conditioned_consequence_match": 0.9},
        source="habitat",
        candidate_evaluation={
            "actual_consequence": {"state_changed": True},
            "baseline_error": 0.5,
            "candidate_conditioned_error": 0.1,
        },
    )
    assert calls == {"observer": 1, "consumer": 1}


def test_live_possibility_frontier_does_not_fabricate_representational_refs():
    """The live frontier precedes per-turn ref discovery; preserve that boundary."""
    path = Path(__file__).parents[1] / "aurora_internal" / "aurora_live_possibility_frontier.py"
    source = path.read_text(encoding="utf-8")
    assert "RepresentationalRef(" not in source
    assert "for_c1(" not in source
    assert "for_c2(" not in source
