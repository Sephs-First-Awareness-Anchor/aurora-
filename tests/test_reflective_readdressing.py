from __future__ import annotations

from types import SimpleNamespace

import pytest

from aurora_internal.aurora_reflective_readdressing import AuroraReflectiveReaddressing
from aurora_internal.aurora_turn_chain import TurnUnderstandingState
from aurora_internal.aurora_utterance_parser import UtteranceParser


class _SourceMap:
    def find_functions(self, query, limit=2):
        if str(query).lower() in {
            "system", "subsystem", "response", "reasoning", "processing", "pathway"
        }:
            return [{
                "function_id": "aurora.demo_path",
                "qualname": "demo_path",
                "file": "aurora.py",
                "line": 42,
                "match_score": 6.0,
            }]
        return []


class _Contract:
    def __init__(self):
        self.contributors = []

    def attach_pending_contributors(self, value):
        self.contributors.append(value)


class _Observer:
    def __init__(self):
        self.observations = []

    def record_observation(self, **kwargs):
        self.observations.append(kwargs)


def _systems():
    return {
        "system_introspection": _SourceMap(),
        "understanding_contract": _Contract(),
        "quasiarch_observer": _Observer(),
        "_last_pipeline_state": {
            "dominant_axis": "B",
            "axis_activation": {"X": 0.10, "T": 0.15, "N": 0.15, "B": 0.40, "A": 0.20},
            "salient_concepts": ["creator", "identity"],
            "goal_stack": ["preserve creator relationship"],
            "meaning_focus": "creator identity",
        },
        "_last_system_introspection_episode": {
            "episode_id": "INT:test",
            "steps": [{"function_id": "aurora.demo_path", "decision": "selected"}],
        },
        "_last_system_diagnosis": {
            "problem_type": "composer_semantic_rejection",
            "confidence": 0.91,
            "summary": "The composer lost the creator relationship.",
            "likely_boundary": {
                "function_id": "aurora_expression_perception.SentenceComposer.compose",
                "file": "aurora_expression_perception.py",
                "line": 100,
                "reason": "the composer candidate dropped named entities",
            },
        },
    }


def _bridge(tmp_path):
    systems = _systems()
    bridge = AuroraReflectiveReaddressing(state_dir=str(tmp_path), persist=False)
    bridge.attach_systems(systems)
    systems["reflective_readdressing"] = bridge
    bridge.capture_turn(
        user_input="Who made you?",
        delivered_text="My creator is Sunni (Sir) Morningstar.",
        response_source="relational_role",
        confidence=0.82,
        systems=systems,
    )
    return bridge, systems


def test_self_inquiry_resolves_from_normal_semantic_parse(tmp_path):
    bridge, systems = _bridge(tmp_path)
    parsed = UtteranceParser().parse("Which subsystem shaped the answer you just gave?")
    context = bridge.prepare_turn(
        "Which subsystem shaped the answer you just gave?", parsed, systems
    )
    assert context["mode"] == "self_inquiry"
    assert context["target_episode_id"] == "INT:test"
    assert context["source_anatomy_score"] > 0.0


def test_contextual_why_can_reach_previous_episode_without_command_phrase(tmp_path):
    bridge, systems = _bridge(tmp_path)
    text = "Why did that happen?"
    context = bridge.prepare_turn(text, UtteranceParser().parse(text), systems)
    assert context["mode"] == "self_inquiry"


def test_ordinary_opinion_question_is_not_misrouted_to_system_introspection(tmp_path):
    bridge, systems = _bridge(tmp_path)
    text = "What do you think about music?"
    assert bridge.prepare_turn(text, UtteranceParser().parse(text), systems) == {}


def test_clarification_reopens_relevant_reasoning_state(tmp_path):
    bridge, systems = _bridge(tmp_path)
    # Replace the previous episode with an interpretation episode relevant to
    # the incoming clarification.
    systems["_last_pipeline_state"]["salient_concepts"] = ["anger", "frustration", "relationship"]
    bridge.capture_turn(
        user_input="Are you interpreting me as angry with you?",
        delivered_text="I think you are angry with me.",
        response_source="reasoning",
        confidence=0.61,
        systems=systems,
    )
    text = "No, the frustration was with the result, not with you."
    context = bridge.prepare_turn(text, UtteranceParser().parse(text), systems)
    assert context["mode"] == "readdress"
    assert "Prior matter:" in context["recontextualized_text"]
    assert "New evidence or perspective:" in context["recontextualized_text"]


def test_perspective_instruction_reopens_same_problem(tmp_path):
    bridge, systems = _bridge(tmp_path)
    systems["_last_pipeline_state"]["salient_concepts"] = ["boundary", "problem", "agency"]
    bridge.capture_turn(
        user_input="How should we solve this boundary problem?",
        delivered_text="Use agency first.",
        response_source="reasoning",
        confidence=0.65,
        systems=systems,
    )
    text = "Consider it from the boundary side instead."
    context = bridge.prepare_turn(text, UtteranceParser().parse(text), systems)
    assert context["mode"] == "perspective_shift"


def test_self_inquiry_rendering_is_grounded_in_recorded_evidence(tmp_path):
    bridge, systems = _bridge(tmp_path)
    text = "What part of your system led you to that response?"
    context = bridge.prepare_turn(text, UtteranceParser().parse(text), systems)
    rendered = bridge.render_self_inquiry(context)
    assert "relational_role" in rendered
    assert "SentenceComposer.compose" in rendered
    assert "aurora_expression_perception.py:100" in rendered


def test_axis_readdressing_preserves_continuity_without_freezing_original(tmp_path):
    bridge, systems = _bridge(tmp_path)
    text = "No, reconsider the boundary rather than only agency."
    context = bridge.prepare_turn(text, UtteranceParser().parse(text), systems)
    if not context:
        # Build a direct internal request for this unit test. The public path is
        # separately covered above.
        bridge.request_readdress(reason="boundary challenge", mode="readdress")
        context = bridge.prepare_turn(text, UtteranceParser().parse(text), systems)
    current = {"X": 0.10, "T": 0.10, "N": 0.10, "B": 0.20, "A": 0.50}
    merged = bridge.axis_readdress_vector(current, context)
    assert pytest.approx(sum(merged.values()), abs=0.001) == 1.0
    assert merged != current
    assert merged["B"] > 0.20


def test_apply_readdressing_enriches_normal_turn_state(tmp_path):
    import aurora

    bridge, systems = _bridge(tmp_path)
    text = "Which subsystem shaped the answer you just gave?"
    context = bridge.prepare_turn(text, UtteranceParser().parse(text), systems)
    state = TurnUnderstandingState(raw_text=text)
    state.pipeline_state = {}
    state.parsed = UtteranceParser().parse(text)
    aurora._apply_reflective_readdressing_to_state(text, systems, state, context)
    assert state.parsed["reflective_reapplied"] is True
    assert state.pipeline_state["reflective_readdressing"]["mode"] == "self_inquiry"
    assert "creator" in state.parsed["topic_words"]


def test_finished_trial_is_published_to_existing_development_systems(tmp_path):
    bridge, systems = _bridge(tmp_path)
    text = "Which subsystem shaped the answer you just gave?"
    bridge.prepare_turn(text, UtteranceParser().parse(text), systems)
    systems["_last_pipeline_state"] = {
        "dominant_axis": "A",
        "axis_activation": {"X": 0.10, "T": 0.10, "N": 0.15, "B": 0.25, "A": 0.40},
    }
    result = bridge.finish_turn(
        delivered_text="The strongest boundary was SentenceComposer.compose.",
        response_source="reflective_introspection",
        confidence=0.90,
        systems=systems,
    )
    assert result["status"] == "trial_complete"
    assert result["changed"] is True
    assert systems["understanding_contract"].contributors
    assert systems["quasiarch_observer"].observations


def test_internal_systems_can_request_readdressing(tmp_path):
    bridge, systems = _bridge(tmp_path)
    bridge.request_readdress(
        reason="unresolved contradiction between remembered and present evidence",
        mode="readdress",
        focus="memory retrieval",
        evidence={"contradiction": True},
    )
    text = "Continue examining the same issue."
    context = bridge.prepare_turn(text, UtteranceParser().parse(text), systems)
    assert context["requested"]["focus"] == "memory retrieval"
    assert context["mode"] == "readdress"


def test_reflective_lineage_returns_to_original_matter_after_self_explanation(tmp_path):
    bridge, systems = _bridge(tmp_path)
    question = "What part of your system led you to that response?"
    bridge.prepare_turn(question, UtteranceParser().parse(question), systems)
    bridge.finish_turn(
        delivered_text="The answer came from the relational role path.",
        response_source="reflective_introspection",
        confidence=0.88,
        systems=systems,
    )
    bridge.capture_turn(
        user_input=question,
        delivered_text="The answer came from the relational role path.",
        response_source="reflective_introspection",
        confidence=0.88,
        systems=systems,
    )

    followup = "Consider the same question again from the relationship boundary."
    context = bridge.prepare_turn(followup, UtteranceParser().parse(followup), systems)
    assert context["mode"] == "perspective_shift"
    assert context["original_input"] == "Who made you?"
    assert context["target_episode_id"] == "INT:test"


def test_success_path_does_not_mistake_unrelated_runtime_fault_for_response_source(tmp_path):
    bridge, systems = _bridge(tmp_path)
    # An unrelated fault can coexist with a correct lineage-backed answer.
    systems["_last_system_diagnosis"] = {
        "problem_type": "runtime_fault",
        "confidence": 0.96,
        "likely_boundary": {
            "function_id": "aurora.AxisProjector.project",
            "file": "aurora.py",
            "line": 3599,
            "reason": "unrelated projection fault",
        },
    }
    bridge.capture_turn(
        user_input="Who made you?",
        delivered_text="My creator is Sunni (Sir) Morningstar.",
        response_source="relational_role",
        confidence=0.82,
        systems=systems,
    )
    text = "What part of your system led you to that response?"
    context = bridge.prepare_turn(text, UtteranceParser().parse(text), systems)
    rendered = bridge.render_self_inquiry(context)
    assert "relational_role" in rendered
    assert "AxisProjector.project" not in rendered


def test_ordinary_vague_example_question_does_not_become_technical_self_inquiry(tmp_path):
    bridge, systems = _bridge(tmp_path)
    text = "A crystal is complex, but its governing relationships can be compact. Is that a useful example?"
    context = bridge.prepare_turn(text, UtteranceParser().parse(text), systems)
    assert not context or context.get("mode") != "self_inquiry"


def test_positive_callback_confirmation_does_not_reopen_reasoning_episode(tmp_path):
    bridge, systems = _bridge(tmp_path)
    text = "Yes, that is what I meant."
    assert bridge.prepare_turn(text, UtteranceParser().parse(text), systems) == {}
