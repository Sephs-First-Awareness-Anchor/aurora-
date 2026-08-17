"""Aurora Build 723 native motivation-binding regression canaries.

These tests exercise the executable Habitat, Noncomp field, genealogy, and
representational-resolution paths.  Test fixtures may stage a specific lawful
hypothesis when the point is to compare exact candidate values; action and
consequence evaluation still travel through production autonomy and
HabitatRuntime.act().
"""
from __future__ import annotations

import inspect
import json
import random

from aurora_habitat import HabitatRuntime
import aurora_habitat_motivation as mot
from aurora_internal.constraint_genealogy import (
    AXES,
    AbilityProfile,
    ConstraintGenealogyLogger,
    GenealogyConfig,
    TraceItem,
)
from aurora_manifold_directory.noncomp_field import NoncompField
from aurora_representational_address import RepresentationalRef
from aurora_representational_resolution import get_or_create_engine


def _fresh(tmp_path, name: str, *, identity_field: bool = False):
    root = tmp_path / name
    genealogy = ConstraintGenealogyLogger(
        name, config=GenealogyConfig(), output_dir=str(root / "genealogy"),
    )
    systems = {"genealogy": genealogy, "state_dir": str(root / "state")}
    if identity_field:
        systems["identity_field"] = NoncompField()
    habitat = HabitatRuntime(root / "world", systems=systems)
    systems["habitat"] = habitat
    return genealogy, systems, habitat


def _score(candidates, entity_id: str, operation: str) -> float:
    return max(
        float(candidate["relevance_score"])
        for candidate in candidates
        if candidate["operation"] == operation and entity_id in candidate["target_ids"]
    )


def _candidate(candidates, entity_id: str, operation: str):
    return max(
        (
            candidate for candidate in candidates
            if candidate["operation"] == operation and entity_id in candidate["target_ids"]
        ),
        key=lambda item: float(item["relevance_score"]),
    )


def _memory_fragment(entity_id: str, resonance: float = 1.0):
    return {
        "event_id": f"memory:{entity_id}",
        "resonance": resonance,
        "content": {"source": "habitat", "entity_ids": [entity_id]},
    }


def _drive_representational_pressure(genealogy, engine, ref, ticks: int = 30):
    for tick in range(ticks):
        relieved_axis = ("B", "X", "T")[tick % 3]
        context_id = f"MOTIVATION_CONTEXT:{tick % 4}"
        if context_id not in genealogy.abilities:
            genealogy.abilities[context_id] = AbilityProfile(
                id=context_id,
                axis="X",
                requires=("X",),
                cost={axis: 0.0 for axis in AXES},
                risk={axis: 0.0 for axis in AXES},
                effect_tags=("motivation_test_context",),
            )
        engine.record_participation(
            ref,
            pressure_before={
                axis: (0.4 if axis == relieved_axis else 0.0) for axis in AXES
            },
            pressure_after={axis: 0.0 for axis in AXES},
            source="native_motivation_test",
            context_tag=context_id,
            extra_trace=[TraceItem(kind="ABILITY", id=context_id)],
        )
    assert engine.inadequacy_pressure(ref) > 0.0


def _stage_exact(engine, ref, value: str):
    key = ref.encode()
    engine._active_stage_for_ref.pop(key, None)
    engine._candidate_downstream_effects.pop(key, None)
    candidates = engine.unresolved_field_candidates(ref, max_candidates=5)
    candidate = next(
        item for item in candidates
        if item["field"] == "sub_law_c" and item["candidate_value"] == value
    )
    stage = engine.stage_field_inquiry(
        ref, candidate, consumer="habitat_motivation",
    )[0]
    engine._active_stage_for_ref[key] = {
        "stage": stage,
        "candidate": candidate,
        "consumer": "habitat_motivation",
        "context_scope": None,
        "candidate_selection": "explicit_value_comparison_test_fixture",
    }
    engine._provisional_reads[key] = 0
    return candidate, stage


def _operation_scores(candidates):
    result = {}
    for candidate in candidates:
        operation = candidate["operation"]
        result[operation] = max(
            result.get(operation, float("-inf")),
            float(candidate["relevance_score"]),
        )
    return result


def test_identity_field_uses_native_reference_and_all_five_axes(tmp_path):
    _genealogy, systems, habitat = _fresh(
        tmp_path, "identity_reference", identity_field=True,
    )
    field = systems["identity_field"]
    status = field.status()
    assert status["axis_pressures"] == status["reference_axis_pressures"]
    assert set(status["axis_pressures"]) == set("XTNBA")
    assert mot.active_pressures(systems) == {}
    assert mot.candidate_actions(systems) == []

    # The real field rests at 0.10. A genuine T perturbation remains below
    # 0.30 yet is visible relative to that native reference.
    field.ingest_external_input({"T": 0.25}, intensity=1.0, source="test")
    current_t = field.status()["axis_pressures"]["T"]
    assert 0.10 < current_t < 0.30
    assert mot.active_pressures(systems)["T"] > 0.0

    for axis in "XNBA":
        field.ingest_external_input({axis: 0.25}, intensity=1.0, source="test")
    assert set(mot.active_pressures(systems)) == set("XTNBA")

    created = habitat.act(
        actor="aurora", territory="space", operation="create",
        parameters={"entity_type": "shape"},
    )
    candidates = mot.candidate_actions(systems)
    target_id = created.affected_entities[0]
    # One active family still leaves several physically distinct affordances
    # in competition; no family selects a fixed operation.
    assert len({
        candidate["operation"] for candidate in candidates
        if target_id in candidate["target_ids"]
    }) > 4

    source = inspect.getsource(__import__("aurora_habitat"))
    assert "_operation_axis_amplitudes" not in source
    assert "_operation_category" not in inspect.getsource(mot)
    profiles = habitat.get_affordances()["consequence_axis_profiles"]
    assert all(any(float(profile.get(axis, 0.0)) > 0.0 for profile in profiles.values())
               for axis in "XTNBA")


def test_entity_relevance_is_contextual_not_human_touch_priority(tmp_path):
    _genealogy, systems, habitat = _fresh(tmp_path, "entity_relevance")
    entity_a = habitat.act(
        actor="aurora", territory="space", operation="create",
        parameters={"entity_type": "shape"},
    ).affected_entities[0]
    entity_b = habitat.act(
        actor="aurora", territory="space", operation="create",
        parameters={"entity_type": "shape"},
    ).affected_entities[0]
    habitat.act(
        actor="human", territory="space", operation="move",
        target_ids=[entity_b], parameters={"x": 0.8, "y": 0.2},
    )

    # Human change is background reality when nothing in Aurora is active.
    assert mot.candidate_actions(systems) == []

    systems["_gap_seeking_concept"] = {
        "entity_id": entity_b, "unresolved_dimension": "spatial_relation",
    }
    candidates = mot.candidate_actions(systems)
    assert _score(candidates, entity_b, "move") > _score(candidates, entity_a, "move")

    systems.pop("_gap_seeking_concept")
    systems["_sedi_surface_frags"] = [_memory_fragment(entity_a)]
    candidates = mot.candidate_actions(systems)
    assert _score(candidates, entity_a, "move") > _score(candidates, entity_b, "move")

    systems.pop("_sedi_surface_frags")
    systems["_active_recursive_causal_cycle"] = {
        "entity_id": entity_b, "prediction": {"position": [0.5, 0.5]},
    }
    candidates = mot.candidate_actions(systems)
    assert _score(candidates, entity_b, "move") > _score(candidates, entity_a, "move")


def test_self_and_space_compete_without_territory_bonus(tmp_path):
    _genealogy, systems, habitat = _fresh(
        tmp_path, "territory_competition", identity_field=True,
    )
    self_id = habitat.act(
        actor="aurora", territory="self", operation="create",
        parameters={"entity_type": "shape"},
    ).affected_entities[0]
    space_id = habitat.act(
        actor="aurora", territory="space", operation="create",
        parameters={"entity_type": "shape"},
    ).affected_entities[0]
    systems["identity_field"].ingest_external_input(
        {"N": 0.25}, intensity=1.0, source="test",
    )
    candidates = mot.candidate_actions(systems)
    assert abs(_score(candidates, self_id, "move") - _score(candidates, space_id, "move")) < 1e-12
    self_move = _candidate(candidates, self_id, "move")
    assert self_move["reason"]["ownership_bonus"] == 0.0
    assert "territory_bonus" not in self_move["candidate_score_components"]

    systems["_sedi_surface_frags"] = [_memory_fragment(self_id)]
    candidates = mot.candidate_actions(systems)
    assert _score(candidates, self_id, "move") > _score(candidates, space_id, "move")

    systems.pop("_sedi_surface_frags")
    habitat.act(
        actor="human", territory="space", operation="move",
        target_ids=[space_id], parameters={"x": 0.75, "y": 0.25},
    )
    systems["_active_recursive_causal_cycle"] = {
        "entity_id": space_id, "prediction": {"position": [0.5, 0.5]},
    }
    candidates = mot.candidate_actions(systems)
    assert _score(candidates, space_id, "move") > _score(candidates, self_id, "move")


def test_operation_relevance_tracks_observable_difference_dimensions(tmp_path):
    _g1, spatial_systems, spatial_habitat = _fresh(tmp_path, "spatial_operation")
    spatial_id = spatial_habitat.act(
        actor="aurora", territory="space", operation="create",
        parameters={"entity_type": "shape"},
    ).affected_entities[0]
    spatial_habitat.act(
        actor="human", territory="space", operation="move",
        target_ids=[spatial_id], parameters={"x": 0.9, "y": 0.1},
    )
    spatial_systems["_gap_seeking_concept"] = {"entity_id": spatial_id}
    spatial_candidates = mot.candidate_actions(spatial_systems)
    move_score = _score(spatial_candidates, spatial_id, "move")
    assert move_score > _score(spatial_candidates, spatial_id, "resize")
    assert move_score > _score(spatial_candidates, spatial_id, "rotate")
    assert move_score > _score(spatial_candidates, spatial_id, "recolor")
    assert "spatial_relation" in _candidate(
        spatial_candidates, spatial_id, "move",
    )["entity_evidence"]["state_differences"]

    _g2, visual_systems, visual_habitat = _fresh(tmp_path, "visual_operation")
    visual_id = visual_habitat.act(
        actor="aurora", territory="space", operation="create",
        parameters={"entity_type": "shape", "visual_properties": {"color": "blue"}},
    ).affected_entities[0]
    visual_habitat.act(
        actor="human", territory="space", operation="recolor",
        target_ids=[visual_id], parameters={"color": "orange"},
    )
    visual_systems["_gap_seeking_concept"] = {"entity_id": visual_id}
    visual_candidates = mot.candidate_actions(visual_systems)
    recolor_score = _score(visual_candidates, visual_id, "recolor")
    assert recolor_score > _score(visual_candidates, visual_id, "move")
    assert recolor_score > _score(visual_candidates, visual_id, "resize")
    assert recolor_score > _score(visual_candidates, visual_id, "rotate")
    assert "appearance" in _candidate(
        visual_candidates, visual_id, "recolor",
    )["entity_evidence"]["state_differences"]


def test_true_ties_are_neutral_observable_and_order_independent():
    candidates = [
        {
            "candidate_id": "equivalent-a", "operation": "move",
            "territory": "space", "target_ids": ["a"], "parameters": {"x": 0.2, "y": 0.2},
            "relevance_score": 0.8,
        },
        {
            "candidate_id": "equivalent-b", "operation": "move",
            "territory": "space", "target_ids": ["b"], "parameters": {"x": 0.2, "y": 0.2},
            "relevance_score": 0.8,
        },
    ]
    forward = []
    reverse = []
    for seed in range(50):
        winner, evidence = mot.select_action(candidates, rng=random.Random(seed))
        forward.append(winner["candidate_id"])
        assert evidence["tie_status"] == "true_equivalence_neutral_stochastic"
        assert evidence["neutral_stochastic_tiebreak"] is True
        assert evidence["preference_attributed_to_tiebreak"] is False
        winner_reversed, reverse_evidence = mot.select_action(
            list(reversed(candidates)), rng=random.Random(seed),
        )
        reverse.append(winner_reversed["candidate_id"])
        assert reverse_evidence["tied_candidate_ids"] == evidence["tied_candidate_ids"]
    assert forward == reverse
    assert set(forward) == {"equivalent-a", "equivalent-b"}


def test_parameter_values_follow_native_magnitude_or_remain_exploratory(tmp_path):
    _genealogy, systems, habitat = _fresh(
        tmp_path, "parameter_binding", identity_field=True,
    )
    entity_id = habitat.act(
        actor="aurora", territory="space", operation="create",
        parameters={"entity_type": "shape"},
    ).affected_entities[0]
    systems["_gap_seeking_concept"] = {"entity_id": entity_id}
    exploratory = _candidate(mot.candidate_actions(systems), entity_id, "resize")
    assert exploratory["parameter_sources"]["width"]["mode"] == "exploratory"

    field = systems["identity_field"]
    field.ingest_external_input({"N": 0.25}, intensity=1.0, source="magnitude-test")
    lower = _candidate(mot.candidate_actions(systems), entity_id, "resize")
    field.ingest_external_input({"N": 0.75}, intensity=1.0, source="magnitude-test")
    higher = _candidate(mot.candidate_actions(systems), entity_id, "resize")
    assert higher["parameters"]["width"] > lower["parameters"]["width"]
    assert higher["parameter_sources"]["width"]["mode"] == "structurally_constrained"
    assert "native_MAGNITUDE" in higher["parameter_sources"]["width"]["source_evidence"]


def test_exact_provisional_values_change_downstream_ranking(tmp_path):
    genealogy, systems, habitat = _fresh(tmp_path, "candidate_distinction")
    habitat.act(
        actor="aurora", territory="space", operation="create",
        parameters={"entity_type": "shape"},
    )
    engine = get_or_create_engine(systems)
    ref = RepresentationalRef.for_c1("N", "OPERATOR", "A")
    _drive_representational_pressure(genealogy, engine, ref)
    engine._active_stage_for_ref.pop(ref.encode(), None)
    lawful_values = {
        candidate["candidate_value"]
        for candidate in engine.unresolved_field_candidates(ref)
        if candidate["field"] == "sub_law_c"
    }
    assert lawful_values == set("XTNBA")

    _stage_exact(engine, ref, "X")
    random.seed(123)
    x_candidates = mot.candidate_actions(systems)
    x_scores = _operation_scores(x_candidates)
    assert engine.provisional_resolution(ref).sub_law_c == "X"

    _stage_exact(engine, ref, "T")
    random.seed(123)
    t_candidates = mot.candidate_actions(systems)
    t_scores = _operation_scores(t_candidates)
    assert engine.provisional_resolution(ref).sub_law_c == "T"

    assert x_scores != t_scores
    assert max(x_scores, key=x_scores.get) != max(t_scores, key=t_scores.get)
    assert any(
        effect["value"] == "T" and abs(float(effect["score_delta"])) > 0.0
        for candidate in t_candidates
        for effect in candidate["provisional_resolution"]
    )


def test_candidate_credit_requires_value_specific_downstream_effect(tmp_path):
    genealogy, systems, _habitat = _fresh(tmp_path, "candidate_credit")
    engine = get_or_create_engine(systems)
    ref = RepresentationalRef.for_c1("N", "OPERATOR", "A")
    _drive_representational_pressure(genealogy, engine, ref)

    candidate_x, stage_x = _stage_exact(engine, ref, "X")
    engine.provisional_resolution(ref)
    engine._active_stage_for_ref.pop(ref.encode(), None)
    unrelated_drop = engine.complete_field_inquiry(
        ref, candidate_x, stage_x,
        consumer="candidate_credit_test",
        actual_coactivation=True,
        pressure_before={axis: 1.0 for axis in AXES},
        pressure_after={axis: 0.0 for axis in AXES},
        _discrepancy_before_override=0.9,
        candidate_evaluation={
            "candidate_field": "sub_law_c",
            "candidate_value": "X",
            "actual_consequence": {"state_changed": True},
            "baseline_error": 0.9,
            "candidate_conditioned_error": 0.1,
        },
    )
    assert unrelated_drop["representational_resolution_outcome"] == "unresolved"
    assert unrelated_drop["candidate_value_discriminated"] is False
    assert engine.current_resolution(ref).sub_law_c is None

    candidate_t, stage_t = _stage_exact(engine, ref, "T")
    effect = engine.record_candidate_downstream_effect(
        ref,
        consumer="candidate_credit_test",
        downstream_difference={
            "selected_action_without_candidate": "resize-instance",
            "selected_action_with_candidate": "create-instance",
        },
        action_or_prediction_affected="action_ranking",
        baseline_expectation={"consequence_dimensions": ["extent_magnitude"]},
        conditioned_expectation={"consequence_dimensions": ["existence", "persistence"]},
    )
    assert effect is not None
    engine._active_stage_for_ref.pop(ref.encode(), None)
    supported = engine.complete_field_inquiry(
        ref, candidate_t, stage_t,
        consumer="candidate_credit_test",
        actual_coactivation=True,
        pressure_before={axis: 1.0 for axis in AXES},
        pressure_after={axis: 0.0 for axis in AXES},
        _discrepancy_before_override=0.8,
        candidate_evaluation={
            "candidate_field": "sub_law_c",
            "candidate_value": "T",
            "actual_consequence": {"consequence_dimensions": ["existence", "persistence"]},
            "baseline_error": 0.8,
            "candidate_conditioned_error": 0.1,
        },
    )
    assert supported["representational_resolution_outcome"] == "retained"
    assert supported["candidate_value_discriminated"] is True
    assert engine.current_resolution(ref).sub_law_c == "T"


def test_proactive_habitat_consideration_is_independent_of_ambient_observation(tmp_path):
    _genealogy, systems, habitat = _fresh(tmp_path, "proactive_independence")
    entity_id = habitat.act(
        actor="aurora", territory="space", operation="create",
        parameters={"entity_type": "shape"},
    ).affected_entities[0]
    control = mot.maybe_engage_habitat(systems)
    assert control.engaged is False
    assert control.selected_action is None

    systems["_gap_seeking_concept"] = {"entity_id": entity_id}
    active = mot.maybe_engage_habitat(systems)
    assert active.environmental_affordances_considered > 0
    assert active.engaged is True

    bridge_source = (
        tmp_path.parents[0] / "unused"
    )  # keeps this assertion independent of the process working directory
    del bridge_source
    from pathlib import Path
    source_path = Path(__file__).parents[1] / "flutter_app/android/app/src/main/python/aurora_bridge.py"
    source = source_path.read_text(encoding="utf-8")
    loop = source[source.index("def _proactive_loop"):]
    habitat_call = loop.index("_maybe_autonomous_habitat_action(_systems, obs)")
    silence_gate = loop.index("if not obs:")
    assert habitat_call < silence_gate


def test_self_externalization_and_memory_reactivation_end_to_end(tmp_path):
    _genealogy, systems, habitat = _fresh(
        tmp_path, "self_externalization", identity_field=True,
    )
    systems["_active_reflective_readdressing"] = {
        "active_relation": ["magnitude", "difference"],
    }
    for _ in range(3):
        systems["identity_field"].ingest_external_input(
            {"N": 1.0}, intensity=1.0, source="internal-structure",
        )
    random.seed(7)
    creation = mot.maybe_engage_habitat(systems)
    assert creation.engaged is True
    assert creation.selected_action["operation"] == "create"
    assert creation.selected_action["territory"] == "self"
    sources = creation.selected_action["parameter_sources"]
    assert sources["dimensions"]["mode"] == "structurally_constrained"
    assert sources["position"]["mode"] == "exploratory"
    assert sources["visual_properties.color"]["mode"] == "exploratory"
    entity_id = creation.consequence["affected_entities"][0]

    restarted = HabitatRuntime(tmp_path / "self_externalization" / "world", systems=systems)
    systems["habitat"] = restarted
    assert restarted.get_entity(entity_id)["territory"] == "self"

    systems.pop("_active_reflective_readdressing")
    systems["_sedi_surface_frags"] = [_memory_fragment(entity_id)]
    revisitation = mot.maybe_engage_habitat(systems)
    assert revisitation.engaged is True
    assert entity_id in revisitation.selected_action["target_ids"]
    assert revisitation.selected_action["reason"]["ownership_bonus"] == 0.0
    assert revisitation.consequence["state_changed"] is True
    assert restarted.get_motivation_history(limit=2)


def test_shared_change_binds_only_through_active_causal_structure(tmp_path):
    _genealogy, systems, habitat = _fresh(
        tmp_path, "shared_causal_demo", identity_field=True,
    )
    unrelated = habitat.act(
        actor="aurora", territory="space", operation="create",
        parameters={"entity_type": "shape"},
    ).affected_entities[0]
    focal = habitat.act(
        actor="aurora", territory="space", operation="create",
        parameters={"entity_type": "shape"},
    ).affected_entities[0]
    human_change = habitat.act(
        actor="human", territory="space", operation="move",
        target_ids=[focal], parameters={"x": 0.9, "y": 0.1},
    )
    assert human_change.causal_parent is not None
    systems["identity_field"].ingest_external_input(
        {"N": 1.0}, intensity=1.0, source="shared-discrepancy",
    )
    systems["_active_recursive_causal_cycle"] = {
        "entity_id": focal, "prediction": {"position": [0.5, 0.5]},
    }
    systems["_gap_seeking_concept"] = {
        "entity_id": focal, "unresolved_dimension": "spatial_relation",
    }
    candidates = mot.candidate_actions(systems)
    assert max(c["relevance_score"] for c in candidates if focal in c["target_ids"]) > max(
        c["relevance_score"] for c in candidates if unrelated in c["target_ids"]
    )
    assert _score(candidates, focal, "move") > _score(candidates, focal, "recolor")

    random.seed(11)
    result = mot.maybe_engage_habitat(systems)
    assert result.engaged is True
    assert focal in result.selected_action["target_ids"]
    assert result.selected_action["operation"] == "move"
    assert result.consequence["state_changed"] is True
    assert result.selected_action["entity_evidence"]["last_change"]["actor"] == "human"
    assert result.selected_action["internal_sources"]["causal_threads"]["entity_bindings"]


def test_resolution_values_compete_through_real_autonomous_consequences(tmp_path):
    genealogy, systems, habitat = _fresh(tmp_path, "resolution_demo")
    habitat.act(
        actor="aurora", territory="space", operation="create",
        parameters={"entity_type": "shape"},
    )
    engine = get_or_create_engine(systems)
    ref = RepresentationalRef.for_c1("N", "OPERATOR", "A")
    _drive_representational_pressure(genealogy, engine, ref)

    _stage_exact(engine, ref, "X")
    random.seed(123)
    first = mot.maybe_engage_habitat(systems)
    assert first.engaged is True
    x_outcome = next(
        event for event in reversed(engine._resolution_events)
        if event["candidate_values_considered"] == ["X"]
    )
    assert x_outcome["candidate_evaluation"]["downstream_difference_produced"]
    assert x_outcome["outcome"] == "unresolved"
    assert engine.current_resolution(ref).sub_law_c is None

    _stage_exact(engine, ref, "T")
    random.seed(123)
    second = mot.maybe_engage_habitat(systems)
    assert second.engaged is True
    assert second.selected_action["operation"] != first.selected_action["operation"]
    t_outcome = next(
        event for event in reversed(engine._resolution_events)
        if event["candidate_values_considered"] == ["T"]
    )
    evaluation = t_outcome["candidate_evaluation"]
    assert evaluation["action_prediction_affected"] == "action_ranking"
    assert evaluation["candidate_conditioned_error"] < evaluation["baseline_error"]
    assert t_outcome["outcome"] == "retained"
    assert engine.current_resolution(ref).sub_law_c == "T"
    assert "sub_law_c" in mot.resolved_context_for_axis(systems, "N")["earned_fields"]
    json.dumps(second.to_dict())
    required = {
        "internal_sources", "entity_evidence", "affordance",
        "parameter_sources", "provisional_resolution",
        "candidate_score_components", "tie_status", "selected", "rejected",
    }
    assert all(required <= set(candidate) for candidate in second.candidate_actions)
    evaluated = habitat.get_motivation_history(limit=1)[0]["candidate_evaluations"]
    assert evaluated
    assert all("actual_consequence" in item for item in evaluated)
    assert all("baseline_error" in item and "candidate_conditioned_error" in item
               for item in evaluated)


def test_ineffective_equivalent_consequences_reduce_relevance_without_timer(tmp_path):
    _genealogy, systems, habitat = _fresh(tmp_path, "natural_disengagement")
    entity_id = habitat.act(
        actor="aurora", territory="space", operation="create",
        parameters={"entity_type": "shape"},
    ).affected_entities[0]
    systems["_gap_seeking_concept"] = {"entity_id": entity_id}
    before = _candidate(mot.candidate_actions(systems), entity_id, "move")
    habitat.record_motivation_event({
        "selected_operation": "move",
        "selected_territory": "space",
        "selected_target_ids": [entity_id],
        "useful_distinction": False,
        "consequence": {"success": True, "state_changed": True},
    })
    after = _candidate(mot.candidate_actions(systems), entity_id, "move")
    assert after["relevance_score"] < before["relevance_score"]
    evidence = after["consequence_yield_evidence"]
    assert evidence["ineffective_since_last_useful_distinction"] == 1
    assert "turn" not in evidence and "timer" not in evidence and "maximum" not in evidence
