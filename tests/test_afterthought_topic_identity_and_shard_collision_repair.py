"""Build 725 replacement for the superseded Build 616 lexical-topic tests.

Build 616 correctly prevented the literal transport marker AFTERTHOUGHT from
becoming the subject, but did so by installing a regex/stopword topic parser.
Build 725 removes that semantic authority entirely. These tests preserve the
valid transport-provenance contract while asserting the new invariant: raw
wording cannot manufacture semantic identity or generated outcome prose.
"""
from aurora_simulation_engine import (
    _strip_internal_transport_marker,
    ConsciousLearner,
    ConversationObservation,
    ConceptualResponse,
    ResponseConcept,
    SimulationSession,
)


def test_internal_transport_marker_is_still_provenance_not_content():
    prompt, source = _strip_internal_transport_marker("[AFTERTHOUGHT] How are you?")
    assert prompt == "How are you?"
    assert source == "afterthought"


def test_raw_prompt_normalization_does_not_assign_semantic_topic():
    session = SimulationSession.__new__(SimulationSession)
    topic = session._topic_from_seed_prompt("[AFTERTHOUGHT] How are you?", {})
    assert topic["prompt"] == "How are you?"
    assert topic["episode_source"] == "afterthought"
    assert topic["semantic_topic"] == ""
    assert topic["topic_resolution_status"] == "unresolved"


def test_native_semantic_identity_can_be_carried_when_already_resolved():
    session = SimulationSession.__new__(SimulationSession)
    topic = session._topic_from_seed_prompt(
        "[AFTERTHOUGHT] arbitrary surface wording",
        {"semantic_topic": "native:representation-42", "topic_resolution_status": "resolved"},
    )
    assert topic["semantic_topic"] == "native:representation-42"
    assert topic["topic_resolution_status"] == "resolved"


def test_afterthought_response_outcome_never_becomes_semantic_claim():
    learner = ConsciousLearner()
    shard = learner.observe_outcome(
        ConceptualResponse(primary_concept=ResponseConcept.DIRECT_CLARITY),
        ConversationObservation(connection_felt_stronger=True),
        "practical",
        topic_word="How are you?",
        episode_source="afterthought",
    )
    assert shard is not None
    assert shard.evidence_kind == "response_outcome"
    assert shard.understanding == ""
    assert learner.check_admission(shard) == (False, "nonsemantic_outcome_evidence")


def test_literal_user_word_afterthought_is_not_stripped_when_not_transport_marker():
    prompt, source = _strip_internal_transport_marker("What is an afterthought?")
    assert prompt == "What is an afterthought?"
    assert source == ""
