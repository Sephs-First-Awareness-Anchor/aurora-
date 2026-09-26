"""Canaries for progressive perspective widening and live branch consumption."""
from types import SimpleNamespace

import aurora_representational_resolution as rr
from aurora_representational_address import RepresentationalRef
from aurora_internal import aurora_live_possibility_frontier as frontier


def _bare_engine():
    genealogy = SimpleNamespace(
        abilities={},
        tick_count=0,
        representation_collision_candidates=lambda trace: [],
        representation_gap_candidates=lambda trace: [],
    )
    engine = rr.RepresentationalResolutionEngine.__new__(rr.RepresentationalResolutionEngine)
    engine.genealogy = genealogy
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


def _collision_entries(source_ids):
    return [
        {
            "counterpart_representation_id": sid,
            "collision_id": f"collision::{sid}",
            "evidence": {"collision": True},
            "pressure": 0.7,
        }
        for sid in source_ids
    ]


def _wire_structural_mirrors(engine, base, sources):
    engine.genealogy.abilities[engine.ability_id_for_ref(base)] = object()
    engine.genealogy.representation_collision_candidates = (
        lambda trace: _collision_entries(sources.keys())
    )
    engine.genealogy.representation_gap_candidates = lambda trace: []
    engine._ref_from_ability_id = lambda aid: sources.get(aid)


def test_complete_projection_frontier_survives_old_five_item_budget():
    engine = _bare_engine()
    base = _coarse()
    sources = _sources()
    _wire_structural_mirrors(engine, base, sources)
    engine.inadequacy_pressure = lambda ref: 0.8

    structural = engine._structural_projection_candidates(base, charge_cost=False)
    all_views = engine._projection_frontier(base, structural)
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


def test_hypothetical_peek_has_zero_resolution_or_search_cost_side_effects():
    engine = _bare_engine()
    base = _coarse()
    sources = _sources()
    _wire_structural_mirrors(engine, base, sources)
    engine.inadequacy_pressure = lambda ref: 0.7

    before = {
        "active": dict(engine._active_stage_for_ref),
        "reads": dict(engine._provisional_reads),
        "effects": dict(engine._candidate_downstream_effects),
        "attempts": dict(engine._projection_attempt_counts),
        "events": list(engine._projection_events),
        "cost": dict(engine._cost_ledger),
        "abilities": dict(engine.genealogy.abilities),
    }
    view = engine.peek_projection(base, consumer="hypothetical")
    after = {
        "active": dict(engine._active_stage_for_ref),
        "reads": dict(engine._provisional_reads),
        "effects": dict(engine._candidate_downstream_effects),
        "attempts": dict(engine._projection_attempt_counts),
        "events": list(engine._projection_events),
        "cost": dict(engine._cost_ledger),
        "abilities": dict(engine.genealogy.abilities),
    }
    assert view and view["observed"] is False
    assert before == after


def test_hypothetical_peek_never_bootstraps_domain_hypotheses():
    engine = _bare_engine()
    base = _coarse()
    engine.genealogy.abilities[engine.ability_id_for_ref(base)] = object()
    engine.inadequacy_pressure = lambda ref: 0.7
    before_abilities = dict(engine.genealogy.abilities)
    before_cost = dict(engine._cost_ledger)

    assert engine.peek_projection(base, consumer="hypothetical") is None
    assert engine.genealogy.abilities == before_abilities
    assert engine._cost_ledger == before_cost


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


def test_live_candidate_selects_one_projection_for_unambiguous_causal_credit(monkeypatch):
    ref_x = RepresentationalRef.for_c1("X", "MAGNITUDE", "A").encode()
    ref_t = RepresentationalRef.for_c1("T", "POLARITY", "A").encode()

    def fake_peek(_systems, encoded, **kwargs):
        axis = "T" if encoded == ref_t else "X"
        return {
            "base_ref": encoded,
            "current_ref": encoded,
            "projected_ref": encoded + f"::{axis}",
            "projection_id": f"projection_{axis}",
            "pressure_perspective": [axis],
            "exposed_fields": {"sub_law_c": axis},
            "observed": False,
        }

    monkeypatch.setattr(rr, "peek_projection_for_ref", fake_peek)
    predictive_frame = {
        "pressure_perspective": ["T"],
        "left": {"representational_ref": ref_x},
        "right": {"representational_ref": ref_t},
    }
    contexts, views = frontier._projection_contexts_for_candidate(
        {},
        SimpleNamespace(memory_signal=None, sensory_signal=None),
        predictive_frame,
        [],
        "candidate",
        12,
    )

    assert len(contexts) == 1
    assert len(views) == 1
    assert views[0]["projection_id"] == "projection_T"
    assert views[0]["candidate_axis_overlap"] == 1.0


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
