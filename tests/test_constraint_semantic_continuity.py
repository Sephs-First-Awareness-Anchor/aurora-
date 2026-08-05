from __future__ import annotations

from types import SimpleNamespace

import pytest

import aurora
from aurora_internal.aurora_constraint_semantic_continuity import (
    AXES,
    bind_referential_continuity,
    derive_constraint_grounded_candidate,
    derive_constraint_semantic_state,
    extract_relational_form,
    relation_alignment,
)
from aurora_internal.aurora_proposition_frame import build_frame
from aurora_internal.aurora_reflective_readdressing import AuroraReflectiveReaddressing
from aurora_internal.aurora_utterance_parser import UtteranceParser


def _axes():
    return {"X": 0.20, "T": 0.15, "N": 0.20, "B": 0.25, "A": 0.20}


def test_open_quality_question_preserves_relation_and_unknown():
    form = extract_relational_form("What makes an invention elegant?")
    assert form["subject"] == ""
    assert form["relation"] == "makes"
    assert form["obj"] == "invention"
    assert form["complement"] == "elegant"
    assert form["unknown_role"] == "cause"


def test_compound_opinion_keeps_prior_claim_separate_from_active_question():
    form = extract_relational_form(
        "I think elegance is when one decision solves several problems at once. What do you think?"
    )
    assert form["subject"] == "you"
    assert form["relation"] == "think"
    assert form["unknown_role"] == "object"
    assert len(form["clauses"]) == 1
    assert "elegance" in form["clauses"][0]["obj"]


def test_alternative_clause_survives_boundary_derivation():
    form = extract_relational_form(
        "Can complexity itself be beautiful, or does beauty require simplicity?"
    )
    assert form["subject"] == "complexity itself"
    assert form["relation"] == "be"
    assert form["obj"] == "beautiful"
    assert form["unknown_role"] == "truth"
    assert form["alternatives"][0]["subject"] == "beauty"
    assert form["alternatives"][0]["relation"] == "require"


def test_constraint_state_declares_all_five_root_ancestries():
    form = extract_relational_form("What makes an invention elegant?")
    state = derive_constraint_semantic_state(form, axis_activation=_axes())
    assert state["genealogy_trace"]["root_constraints"] == list(AXES)
    assert state["genealogy_trace"]["canonical_signature"] == "X^1*T^1*N^1*B^1*A^1"
    assert state["response_obligation"]["derivation_signature"] == "X^1*T^1*N^1*B^1*A^1"
    assert set(state["axis_derivation"]) == {"X", "T", "N", "B", "A", "APEX"}
    assert state["axis_derivation"]["APEX"]["roots"] == list(AXES)


def test_referent_continuity_is_derived_without_inventing_missing_reference():
    form = extract_relational_form("Why did that happen?")
    bound = bind_referential_continuity(
        form,
        referent_map={"referent_map": {"that": "the rejected composer response"}},
    )
    assert bound["subject"] == "the rejected composer response"
    assert bound["continuity_bindings"][0]["derivation"]["roots"] == ["X", "T", "B"]


def test_constraint_candidate_is_bound_to_relation_not_only_topic():
    form = extract_relational_form("What makes an invention elegant?")
    state = derive_constraint_semantic_state(form, axis_activation=_axes())
    candidate = derive_constraint_grounded_candidate(state)
    assert "invention" in candidate["text"].lower()
    assert "elegant" in candidate["text"].lower()
    assert candidate["relation_alignment"]["score"] >= 0.9
    assert candidate["source"] == "constraint_semantic_derivation"


def test_constraint_candidate_can_evaluate_prior_asserted_relation():
    form = extract_relational_form(
        "I think elegance is when one decision solves several problems at once. What do you think?"
    )
    state = derive_constraint_semantic_state(form, axis_activation=_axes())
    candidate = derive_constraint_grounded_candidate(state)
    assert "one decision solves several problems" in candidate["text"].lower()
    assert candidate["relation_alignment"]["addresses_unknown"] is True


def test_relation_alignment_rejects_same_topic_wrong_relation():
    form = extract_relational_form("What has your attention at the moment?")
    wrong = relation_alignment(form, "I am still building my understanding of attention.")
    right = relation_alignment(form, "My attention is on the unresolved creator relationship.")
    # Both mention attention; only one actually supplies its current object.
    assert right["score"] > wrong["score"]


def test_axis_projector_accepts_dictionary_genealogy_orientation():
    parsed = UtteranceParser().parse("What makes an invention elegant?")
    systems = {
        "genealogy": {"pressure_orientation": {"X": 1.0, "T": 0.9, "N": 1.1, "B": 1.0, "A": 1.05}},
    }
    result = aurora.AxisProjector().project(parsed, systems)
    assert set(result) == set(AXES)
    assert pytest.approx(sum(result.values()), abs=0.001) == 1.0


def test_opinion_followup_is_not_reclassified_as_wellbeing():
    text = "I think elegance is when one decision solves several problems at once. What do you think?"
    parsed = UtteranceParser().parse(text)
    semantic = derive_constraint_semantic_state(parsed["relational_form"], axis_activation=_axes())
    intent = aurora._classify_input_intent(
        text,
        _axis_activation=_axes(),
        _parsed=parsed,
        _semantic_state=semantic,
    )
    assert intent != "wellbeing_query"


def test_proposition_frame_prefers_constraint_relation():
    parsed = UtteranceParser().parse("What makes an invention elegant?")
    semantic = derive_constraint_semantic_state(parsed["relational_form"], axis_activation=_axes())
    state = SimpleNamespace(
        pipeline_state={"constraint_semantic_state": semantic},
        parsed=parsed,
        raw_text="What makes an invention elegant?",
        salient_concepts=[],
    )
    systems = {"_active_turn_state": state}
    frame = build_frame(systems, state)
    assert frame is not None
    assert frame.source == "constraint_relation"
    assert frame.relation == "makes"
    assert frame.obj == "invention"
    assert frame.complement == "elegant"
    assert frame.derivation_signature == "X^1*T^1*N^1*B^1*A^1"


class _NoAnatomy:
    def find_functions(self, query, limit=2):
        return []


def test_ordinary_experience_question_does_not_activate_technical_reflection(tmp_path):
    systems = {
        "system_introspection": _NoAnatomy(),
        "_last_pipeline_state": {"salient_concepts": ["identity"]},
        "_last_system_introspection_episode": {
            "episode_id": "INT:prior",
            "steps": [{"function_id": "aurora.demo", "decision": "selected"}],
        },
    }
    bridge = AuroraReflectiveReaddressing(state_dir=str(tmp_path), persist=False)
    bridge.attach_systems(systems)
    systems["reflective_readdressing"] = bridge
    bridge.capture_turn(
        user_input="Who made you?",
        delivered_text="My creator is Sunni (Sir) Morningstar.",
        response_source="relational_role",
        confidence=0.8,
        systems=systems,
    )
    text = "What has your attention at the moment?"
    result = bridge.prepare_turn(text, UtteranceParser().parse(text), systems)
    assert result == {}
