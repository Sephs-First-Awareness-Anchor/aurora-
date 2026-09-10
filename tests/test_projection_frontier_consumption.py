"""Canaries for progressive perspective widening and live branch consumption."""
from types import SimpleNamespace

import aurora_representational_resolution as rr
from aurora_representational_address import RepresentationalRef
from aurora_internal import aurora_live_possibility_frontier as frontier


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


def _coarse():
    return RepresentationalRef.for_c1("X", "MAGNITUDE", "A")


def _sources():
    return {
        "REAL:one": RepresentationalRef.for_c2(
            "X", "MAGNITUDE", "A", "T", "POLARITY", "B", "DIFFERENCE"
        ),
        "REAL:two": RepresentationalRef.for_c2(
            "X", "MAGNITUDE", "A", "N", "COST", "A", "OPERATOR"
        ),
        "REAL:three": RepresentationalRef.for_c2(
            "X", "MAGNITUDE", "A", "B", "DIFFERENCE", "T", "POLARITY"
        ),
    }


def _structural_candidates(source_ids):
    return [
        {
            "field": "sub_law_c",
            "candidate_value": "T",
            "source": f"collision:{sid}",
            "counterpart_ability_id": sid,
            "evidence": {"collision": True},
            "origin": "collision",
        }
        for sid in source_ids
    ]


def test_complete_projection_frontier_survives_old_five_item_budget():
    engine = _bare_engine()
    base = _coarse()
    sources = _sources()
    candidates = _structural_candidates(sources)
    engine.inadequacy_pressure = lambda ref: 0.8
    engine.unresolved_field_candidates = lambda ref: candidates
    engine._ref_from_ability_id = lambda aid: sources.get(aid)

    all_views = engine._projection_frontier(base, candidates)
    assert len(all_views) > rr.MAX_CANDIDATE_FIELDS_PER_PASS
    for view in all_views[: rr.MAX_CANDIDATE_FIELDS_PER_PASS]:
        engine._projection_attempt_counts[view["projection_id"]] = 1

    engine.stage_field_inquiry = lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("resolution must not begin while any lawful projection remains")
    )
    staged = engine.investigate_if_pressured(base, consumer="test")
    assert staged["mode"] == "perspective_projection"
    assert staged["candidate"]["projection_id"] not in {
        view["projection_id"] for view in all_views[: rr.MAX_CANDIDATE_FIELDS_PER_PASS]
    }


def test_hypothetical_peek_has_zero_resolution_side_effects():
    engine = _bare_engine()
    base = _coarse()
    sources = _sources()
    candidates = _structural_candidates(sources)
    engine.genealogy.abilities[engine.ability_id_for_ref(base)] = object()
    engine.inadequacy_pressure = lambda ref: 0.7
    engine.unresolved_field_candidates = lambda ref: candidates
    engine._ref_from_ability_id = lambda aid: sources.get(aid)

    before = {
        "active": dict(engine._active_stage_for_ref),
        "reads": dict(engine._provisional_reads),
        "effects": dict(engine._candidate_downstream_effects),
        "attempts": dict(engine._projection_attempt_counts),
        "events": list(engine._projection_events),
    }
    view = engine.peek_projection(base, consumer="hypothetical")
    after = {
        "active": dict(engine._active_stage_for_ref),
        "reads": dict(engine._provisional_reads),
        "effects": dict(engine._candidate_downstream_effects),
        "attempts": dict(engine._projection_attempt_counts),
        "events": list(engine._projection_events),
    }
    assert view and view["observed"] is False
    assert before == after


def test_projection_use_without_real_consequence_stays_pending_not_failed():
    engine = _bare_engine()
    base = _coarse()
    source = next(iter(_sources().values()))
    projection = rr.build_perspective_projections(
        base, [("REAL:one", source, {})], max_projections=None
    )[0]
    pending = {
        "mode": "perspective_projection",
        "stage": None,
        "candidate": projection,
        "consumer": "test",
        "context_scope": None,
    }
    key = base.encode()
    engine._active_stage_for_ref[key] = pending
    engine._provisional_reads[key] = 1
    engine._candidate_downstream_effects[key] = {
        "downstream_difference_produced": {"thought_changed": True}
    }

    outcome = engine._projection_consequence(base, pending, candidate_evaluation=None)
    assert outcome == "pending_evidence"
    assert projection["projection_id"] not in engine._projection_attempt_counts
    assert engine._provisional_reads[key] == 1
    assert engine._candidate_downstream_effects[key]


def test_live_frontier_extracts_only_explicit_real_ref_fields():
    ref = _coarse().encode()
    found = frontier._extract_representational_refs(
        {"nested": [{"representational_ref": ref}]},
        {"plain_text": ref},
        ["REF:not-an-explicit-ref-field"],
    )
    assert found == [ref]


def test_actuality_commit_uses_only_selected_projection_views(monkeypatch):
    selected_view = {
        "base_ref": _coarse().encode(),
        "projection_id": "winner_projection",
        "thought_difference": {"interpretation_changed": True},
    }
    rejected_view = {
        "base_ref": _coarse().encode(),
        "projection_id": "rejected_projection",
        "thought_difference": {"interpretation_changed": True},
    }
    systems = {
        "_selected_possibility": {"projection_views": [selected_view]},
        "_current_possibility_frontier": {
            "actualized": False,
            "candidates": [
                {"selected": True, "projection_views": [selected_view]},
                {"selected": False, "projection_views": [rejected_view]},
            ],
        },
    }
    calls = []

    def fake_actualize(_systems, view, **kwargs):
        calls.append((view["projection_id"], kwargs))
        return {"status": "awaiting_consequence", "projection_id": view["projection_id"]}

    monkeypatch.setattr(rr, "actualize_projection_for_ref", fake_actualize)
    frontier.mark_actualized(systems, SimpleNamespace(tick=91))

    assert [call[0] for call in calls] == ["winner_projection"]
    assert systems["_current_possibility_frontier"]["actualized"] is True
    assert systems["_current_possibility_frontier"]["actualized_thought_tick"] == 91
    assert systems["_current_possibility_frontier"]["actualized_projection_commits"][0]["projection_id"] == "winner_projection"
