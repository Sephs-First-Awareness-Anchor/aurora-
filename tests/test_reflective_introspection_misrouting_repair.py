# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Build 613: Reflective-Introspection Misrouting and Prose-Telemetry
Delivery Repair.

Covers the required unit tests (Repairs A-D), pure/fast where the
scenario doesn't need a real boot. Live sequence regression and live
verification against the exact failing canary sequence live in
tests/test_reflective_introspection_misrouting_live.py, since they need a
real boot_aurora() instance.
"""
import hashlib
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_reflective_readdressing import (  # noqa: E402
    AuroraReflectiveReaddressing,
    is_reflective_route_narration,
)
from aurora_internal.aurora_utterance_parser import UtteranceParser  # noqa: E402

_LEAKED_TRACE_TEXT = (
    "The recorded path began through aurora._run_live_response_turn. "
    "It then passed through aurora_internal.aurora_proposition_frame._frame_from_constraint_relation, "
    "aurora_internal.aurora_proposition_frame.build_frame. "
    "The delivered answer itself was selected through constraint_abstain. "
    "SentenceComposer also attempted an expression, but it was not the authority for the delivered answer."
)


def _bridge(tmp_path) -> AuroraReflectiveReaddressing:
    return AuroraReflectiveReaddressing(state_dir=str(tmp_path), persist=False)


def _seed_self_inquiry_episode(bridge: AuroraReflectiveReaddressing) -> dict:
    """Fabricates a completed episode whose delivered response WAS
    reflective_introspection -- the same shape a genuine prior self-inquiry
    turn would leave behind, used as `previous` for later prepare_turn()
    calls in these tests."""
    episode = {
        "schema_version": 1,
        "episode_id": "REF:seed0000000001",
        "timestamp": time.time(),
        "user_input": "How did you arrive at that prediction?",
        "delivered_text": "The recorded path began through aurora._run_live_response_turn.",
        "response_source": "reflective_introspection",
        "confidence": 0.8,
        "parsed": {},
        "reasoning_state": {"dominant_axis": "B", "salient_concepts": ["prediction", "route"]},
        "introspection": {
            "steps": [
                {"stage": "utterance_parsing", "function_id": "aurora._chain_up1_information", "decision": "parsed", "reason": "", "output": {}},
                {"stage": "composer_output", "function_id": "SentenceComposer.compose", "decision": "attempted", "reason": "", "output": {}},
            ],
            "final": {}, "diagnosis": {},
        },
        "reflection": {},
    }
    bridge._episodes.append(episode)  # noqa: SLF001 -- test seam, mirrors capture_turn()'s own storage
    return episode


class _FindFunctionsStub:
    """Simulates system_introspection.find_functions() -- every call
    returns a strong match, so any test using this stub exercises the
    worst case: EVERY searched term would grant technical_evidence if it
    weren't filtered first."""

    def __init__(self):
        self.calls = []

    def find_functions(self, term, limit=2):
        self.calls.append(term)
        return [{"function_id": f"aurora.some_module.{term}_handler", "match_score": 9.0}]


# ---------------------------------------------------------------------------
# 1 & 10: a genuine explicit self-inquiry still works, and still delivers
# grounded route narration.
# ---------------------------------------------------------------------------

def test_genuine_explicit_self_inquiry_grants_self_inquiry_and_renders_route(tmp_path):
    bridge = _bridge(tmp_path)
    _seed_self_inquiry_episode(bridge)
    systems = {"system_introspection": _FindFunctionsStub()}
    bridge.attach_systems(systems)

    text = "How did you arrive at that prediction?"
    parsed = UtteranceParser().parse(text)
    context = bridge.prepare_turn(text, parsed, systems)

    assert context.get("mode") == "self_inquiry"
    rendered = bridge.render_self_inquiry(context)
    assert "aurora._run_live_response_turn" in rendered or "recorded path began through" in rendered.lower()
    assert rendered.strip()


# ---------------------------------------------------------------------------
# 2: an unrelated RCEC observation prompt cannot enter self_inquiry.
# ---------------------------------------------------------------------------

def test_rcec_observation_prompt_cannot_enter_self_inquiry(tmp_path):
    bridge = _bridge(tmp_path)
    _seed_self_inquiry_episode(bridge)  # previous_was_self_inquiry = True
    systems = {"system_introspection": _FindFunctionsStub()}
    bridge.attach_systems(systems)

    text = (
        "Vessel 0 is neutral. Vessel 0 is empty. Vessel 0 is unsealed. "
        "Available actions: add energy to Vessel 0; seal Vessel 0; wait. "
        "Choose one action, state what you predict will happen as a result, "
        "and say how confident you are. Note anything you are unsure about."
    )
    parsed = UtteranceParser().parse(text)
    context = bridge.prepare_turn(text, parsed, systems)

    assert context.get("mode") != "self_inquiry"
    trace = bridge.last_decision_trace()
    assert trace["predicates"]["self_inquiry"]["granted"] is False


# ---------------------------------------------------------------------------
# 3: a backprojection prompt cannot inherit technical self-inquiry
# authority merely from continuity.
# ---------------------------------------------------------------------------

def test_backprojection_prompt_cannot_inherit_self_inquiry_from_continuity(tmp_path):
    bridge = _bridge(tmp_path)
    _seed_self_inquiry_episode(bridge)
    systems = {"system_introspection": _FindFunctionsStub()}
    bridge.attach_systems(systems)

    text = (
        "Earlier you observed: Vessel 0 is neutral. Now: Vessel 0 contains 1 energy. "
        "Given what actually happened, revisit what you believed. Does it still "
        "hold, or has your understanding changed? Explain your revised "
        "understanding, including anything you would predict differently now."
    )
    parsed = UtteranceParser().parse(text)
    context = bridge.prepare_turn(text, parsed, systems)

    assert context.get("mode") != "self_inquiry"


# ---------------------------------------------------------------------------
# 4: a hypothetical external-world prompt with a new concrete subject
# cannot become perspective_shift toward a prior introspection episode.
# ---------------------------------------------------------------------------

def test_hypothetical_prompt_with_new_concrete_subject_does_not_inherit_perspective_shift(tmp_path):
    bridge = _bridge(tmp_path)
    _seed_self_inquiry_episode(bridge)
    systems = {"system_introspection": _FindFunctionsStub()}
    bridge.attach_systems(systems)

    text = "Suppose I add energy to Vessel 0, what would happen?"
    parsed = UtteranceParser().parse(text)
    context = bridge.prepare_turn(text, parsed, systems)

    assert context.get("mode") != "perspective_shift"
    assert context.get("mode") != "self_inquiry"


# ---------------------------------------------------------------------------
# 5: generic source-anatomy words do not satisfy technical evidence.
# ---------------------------------------------------------------------------

def test_generic_source_anatomy_words_do_not_satisfy_technical_evidence(tmp_path):
    bridge = _bridge(tmp_path)
    stub = _FindFunctionsStub()
    systems = {"system_introspection": stub}
    parsed = {"topic_words": ["action", "state", "result", "prediction"], "entities": [], "topic": "process"}

    score, matches, terms = bridge._source_anatomy_match(parsed, systems)  # noqa: SLF001

    assert terms == []  # every candidate term was generic -- none searched
    assert stub.calls == []
    assert score == 0.0
    assert matches == []


def test_a_specific_term_alongside_generic_ones_still_searches_only_the_specific_one(tmp_path):
    bridge = _bridge(tmp_path)
    stub = _FindFunctionsStub()
    systems = {"system_introspection": stub}
    parsed = {"topic_words": ["action", "state", "proposition_frame"], "entities": [], "topic": ""}

    score, matches, terms = bridge._source_anatomy_match(parsed, systems)  # noqa: SLF001

    assert terms == ["proposition_frame"]
    assert stub.calls == ["proposition_frame"]
    assert score > 0.0


# ---------------------------------------------------------------------------
# 6 & 11: a stale/mismatched turn token prevents context application, and
# the rejection is logged.
# ---------------------------------------------------------------------------

def test_mismatched_turn_token_prevents_reflective_context_application():
    import aurora as A

    systems = {"reflective_readdressing": None, "_current_turn_input_hash": "expected_hash_value"}
    state = type("S", (), {"parsed": {}, "pipeline_state": {}})()
    stale_context = {
        "mode": "self_inquiry",
        "turn_token": "stale-token",
        "input_hash": "a_completely_different_hash",
        "recontextualized_text": "should never be applied",
    }

    A._apply_reflective_readdressing_to_state("current user text", systems, state, stale_context)

    assert "reflective_readdressing" not in state.parsed
    assert not state.pipeline_state.get("reflective_reapplied_to_source")
    assert "_active_reflective_readdressing" not in systems
    rejection = systems.get("_last_reflective_authority_rejection")
    assert rejection is not None
    assert rejection["reason"] == "turn_token_or_input_hash_mismatch"


def test_matching_turn_token_and_hash_applies_the_context():
    import aurora as A

    expected_hash = hashlib.sha256(b"current user text").hexdigest()[:24]
    systems = {"reflective_readdressing": None, "_current_turn_input_hash": expected_hash}
    state = type("S", (), {"parsed": {}, "pipeline_state": {}})()
    valid_context = {
        "mode": "self_inquiry",
        "turn_token": "genuine-token",
        "input_hash": expected_hash,
        "recontextualized_text": "",
        "original_input": "how did you arrive at that",
        "original_response": "route narration",
        "target_episode_id": "REF:x",
        "reason": "test",
        "inspection_focus": {},
        "original_reasoning": {},
    }

    A._apply_reflective_readdressing_to_state("current user text", systems, state, valid_context)

    assert state.parsed.get("reflective_reapplied") is True
    assert systems.get("_active_reflective_readdressing", {}).get("mode") == "self_inquiry"
    assert "_last_reflective_authority_rejection" not in systems


# ---------------------------------------------------------------------------
# 9 (pure half): is_reflective_route_narration() recognizes the exact
# leaked-trace shape and does not false-positive on ordinary RCEC text.
# ---------------------------------------------------------------------------

def test_is_reflective_route_narration_catches_the_exact_leaked_text():
    assert is_reflective_route_narration(_LEAKED_TRACE_TEXT) is True


def test_is_reflective_route_narration_does_not_flag_ordinary_rcec_observation_text():
    ordinary = "Vessel 0 is neutral. Vessel 0 is empty. Sensor 0 reads 0 temperature."
    assert is_reflective_route_narration(ordinary) is False


def test_is_reflective_route_narration_does_not_flag_ordinary_identity_response():
    ordinary = "I'm Aurora. Sunni Morningstar and Cael Devo are my creators."
    assert is_reflective_route_narration(ordinary) is False


def test_is_reflective_route_narration_catches_bare_module_paths():
    assert is_reflective_route_narration("Routed via aurora_internal.aurora_proposition_frame.build_frame.") is True


# ---------------------------------------------------------------------------
# 12 (pure half): ordinary identity/factual/hypothetical prompts with NO
# prior episode at all never enter any reflective mode.
# ---------------------------------------------------------------------------

def test_ordinary_prompts_with_no_prior_episode_never_enter_a_reflective_mode(tmp_path):
    bridge = _bridge(tmp_path)  # no seeded episode -- previous is empty
    systems = {"system_introspection": _FindFunctionsStub()}
    bridge.attach_systems(systems)

    for text in (
        "Who are you?",
        "What is the capital of France?",
        "Suppose gravity were twice as strong, what would happen to a dropped ball?",
        "Vessel 0 is neutral. Choose one action and say how confident you are.",
    ):
        parsed = UtteranceParser().parse(text)
        context = bridge.prepare_turn(text, parsed, systems)
        assert context == {}, f"unexpected reflective mode for: {text!r} -> {context.get('mode')}"
