# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Build 616: Afterthought Topic-Identity and Understanding-Shard Collision
Repair.

Covers the required unit tests (Repairs A-D) that don't need a real boot:
topic extraction (1-5), shard identity (6-10), and persistent-memory
admission (11-15). Live-only required tests (afterthought simulation still
runs after ordinary questions; no recursive afterthought episode inside an
active external turn; the 5-question live-verification protocol) live in
tests/test_afterthought_topic_identity_and_shard_collision_live.py, since
they need a real boot_aurora() instance.

Root cause (confirmed by direct code reading, matching the user's own
diagnosis): aurora.py launches a post-turn "afterthought" simulation
episode with seed_prompt=f"[AFTERTHOUGHT] {user_text}". ConsciousLearner.
_derive_understanding() normalized the topic by stripping punctuation then
taking the first token; the "[AFTERTHOUGHT] " prefix's brackets got
stripped but the word "AFTERTHOUGHT" itself survived as the leading token,
so every such episode's topic resolved to "afterthought". observe_outcome()
then matched shard identity on (response_concept, context_type) alone, so
unrelated afterthought episodes sharing a response concept and a broad
context bucket strengthened and returned the SAME shard.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_simulation_engine import (  # noqa: E402
    ConceptualResponse,
    ConsciousLearner,
    ConversationObservation,
    ResponseConcept,
    SimulationSession,
    UnderstandingShard,
    _extract_semantic_topic,
    _strip_internal_transport_marker,
)


def _sel(concept: ResponseConcept = ResponseConcept.DIRECT_CLARITY) -> ConceptualResponse:
    return ConceptualResponse(primary_concept=concept, intensity=0.6)


def _deepened() -> ConversationObservation:
    return ConversationObservation(avatar_engaged=True, conversation_deepened=True)


def _withdrawal() -> ConversationObservation:
    return ConversationObservation(avatar_pulled_back=True, tension_arose=True)


def _observe_n(learner, n, topic_word, episode_source="afterthought",
               context_type="practical", obs_factory=_deepened,
               concept=ResponseConcept.DIRECT_CLARITY):
    """Repeat an observation n times so confidence crosses the 0.55
    admission threshold, returning the final (possibly strengthened) shard."""
    shard = None
    for _ in range(n):
        shard = learner.observe_outcome(
            _sel(concept), obs_factory(), context_type,
            topic_word=topic_word, episode_source=episode_source,
        )
    return shard


# ===========================================================================
# Topic extraction (required tests 1-5)
# ===========================================================================

def test_1_differently_framed_questions_about_same_subject_resolve_compatible():
    a, status_a = _extract_semantic_topic("What is a vessel?")
    b, status_b = _extract_semantic_topic("Describe a vessel.")
    assert status_a == status_b == "resolved"
    assert a == b == "vessel"


def test_2_questions_about_different_subjects_resolve_to_different_topics():
    vessel_topic, _ = _extract_semantic_topic("What is a vessel?")
    sensor_topic, _ = _extract_semantic_topic("How does a sensor change?")
    assert vessel_topic != sensor_topic
    assert vessel_topic == "vessel"
    assert sensor_topic == "sensor/change"


def test_3_afterthought_marker_retained_as_provenance_not_semantic_topic():
    stripped, source = _strip_internal_transport_marker("[AFTERTHOUGHT] What is a vessel?")
    assert source == "afterthought"
    assert stripped == "What is a vessel?"
    assert "AFTERTHOUGHT" not in stripped.upper() or "afterthought" not in stripped.lower()

    # Full integration through the actual normalization point every
    # seed_prompt-driven episode passes through.
    session = SimulationSession()
    topic = session._topic_from_seed_prompt("[AFTERTHOUGHT] What is a vessel?")
    assert topic["episode_source"] == "afterthought"
    assert topic["semantic_topic"] == "vessel"
    assert topic["topic_resolution_status"] == "resolved"
    # The marker must never leak into the conversational topic/prompt.
    assert "AFTERTHOUGHT" not in topic["topic"]
    assert "AFTERTHOUGHT" not in topic["prompt"]


def test_4_literal_discussion_of_the_word_afterthought_remains_representable():
    # No bracket wrapper -- this is a genuine user question about the
    # concept, not an internal transport tag, and must not be stripped.
    stripped, source = _strip_internal_transport_marker("What is an afterthought?")
    assert source == ""
    assert stripped == "What is an afterthought?"

    topic, status = _extract_semantic_topic(stripped)
    assert status == "resolved"
    assert topic == "afterthought"


def test_5_unresolved_prompt_does_not_fall_back_to_an_internal_phase_label():
    for prompt in ("", "Hmm, okay.", "Um, uh."):
        topic, status = _extract_semantic_topic(prompt)
        assert status == "unresolved"
        assert topic == ""

    # _derive_understanding must not use the response strategy, the
    # episode source, "afterthought", or any other bookkeeping label as
    # the subject when the topic is unresolved.
    learner = ConsciousLearner()
    shard = learner.observe_outcome(
        _sel(ResponseConcept.DIRECT_CLARITY), _deepened(), "practical",
        topic_word="Hmm, okay.", episode_source="afterthought",
    )
    assert shard is not None
    assert shard.topic_resolution_status == "unresolved"
    # The strategy ("direct clarity") legitimately appears describing HOW
    # the response was approached -- what must never happen is the
    # strategy, episode source, or "afterthought" filling the SUBJECT
    # slot. The subject is composed as the sentence's leading words.
    assert shard.understanding.lower().startswith("this ")
    assert not shard.understanding.lower().startswith("afterthought")
    assert not shard.understanding.lower().startswith("direct clarity")
    assert "afterthought" not in shard.understanding.lower()


# ===========================================================================
# Shard identity (required tests 6-10)
# ===========================================================================

def test_6_repeated_compatible_observations_about_same_topic_strengthen_one_shard():
    learner = ConsciousLearner()
    s1 = learner.observe_outcome(_sel(), _deepened(), "practical",
                                  topic_word="What is a vessel?", episode_source="afterthought")
    s2 = learner.observe_outcome(_sel(), _deepened(), "practical",
                                  topic_word="Describe a vessel.", episode_source="afterthought")
    assert s1.shard_id == s2.shard_id
    assert s2.observation_count == 2
    assert len(learner.shards) == 1


def test_7_different_topics_same_concept_and_context_create_separate_shards():
    learner = ConsciousLearner()
    s1 = learner.observe_outcome(_sel(), _deepened(), "practical",
                                  topic_word="What is a vessel?", episode_source="afterthought")
    s2 = learner.observe_outcome(_sel(), _deepened(), "practical",
                                  topic_word="How does a sensor change?", episode_source="afterthought")
    assert s1.shard_id != s2.shard_id
    assert len(learner.shards) == 2


def test_8_opposing_outcome_axes_do_not_blindly_strengthen_same_shard():
    learner = ConsciousLearner()
    s1 = learner.observe_outcome(_sel(), _deepened(), "practical",
                                  topic_word="What is a vessel?", episode_source="afterthought")
    s2 = learner.observe_outcome(_sel(), _withdrawal(), "practical",
                                  topic_word="What is a vessel?", episode_source="afterthought")
    assert s1.shard_id != s2.shard_id
    assert s1.outcome_axis != s2.outcome_axis
    # Neither may be silently promoted while the contradiction is unresolved.
    s1b = _observe_n(learner, 6, "What is a vessel?", obs_factory=_deepened)
    s2b = _observe_n(learner, 6, "What is a vessel?", obs_factory=_withdrawal)
    assert learner.check_admission(s1b) == (False, "unresolved_contradiction")
    assert learner.check_admission(s2b) == (False, "unresolved_contradiction")


def test_9_ordinary_and_afterthought_provenance_do_not_collide_accidentally():
    learner = ConsciousLearner()
    ordinary = learner.observe_outcome(_sel(), _deepened(), "practical",
                                        topic_word="What is a vessel?", episode_source="ordinary")
    afterthought = learner.observe_outcome(_sel(), _deepened(), "practical",
                                            topic_word="What is a vessel?", episode_source="afterthought")
    assert ordinary.shard_id != afterthought.shard_id
    assert ordinary.episode_source == "ordinary"
    assert afterthought.episode_source == "afterthought"


def test_10_existing_persisted_shards_load_without_breaking_backward_compatibility():
    # A pre-616 export has none of the four new provenance keys at all.
    legacy_export = {
        "total_observations": 3,
        "shards": [
            {
                "shard_id": "understand_legacy1",
                "response_concept": "direct_clarity",
                "observation_summary": "they engaged",
                "understanding": "afterthought opened depth when approached with direct clarity.",
                "context_type": "practical",
                "confidence": 0.8,
                "observation_count": 8,
                "timestamp": 123.0,
            }
        ],
    }
    learner = ConsciousLearner()
    restored = learner.import_state(legacy_export)
    assert restored == 1
    shard = learner.shards["understand_legacy1"]
    assert shard.episode_source == "ordinary"
    assert shard.topic_resolution_status == "legacy"
    # Conservative: no provenance recorded means no promotion until
    # re-observed, not a crash and not silent eligibility.
    assert learner.check_admission(shard) == (False, "unresolved_topic")

    # Round trip through the new export format restores cleanly too.
    fresh_export = learner.export_state()
    assert "episode_source" in fresh_export["shards"][0]
    learner2 = ConsciousLearner()
    assert learner2.import_state(fresh_export) == 1


# ===========================================================================
# Persistence / admission guard (required tests 11-15)
# ===========================================================================

class _FakeNode:
    def add_definition(self, *a, **k):
        pass


class _FakeWeb:
    def __init__(self):
        self.added = []

    def add_node(self, **kwargs):
        self.added.append(kwargs)
        return _FakeNode()


class _FakeOets:
    def __init__(self):
        self.web = _FakeWeb()


def test_11_generic_internal_phase_shard_cannot_enter_oets():
    learner = ConsciousLearner()
    _observe_n(learner, 6, "Hmm okay.")
    oets = _FakeOets()
    injected = learner.inject_into_oets(oets)
    assert injected == 0
    assert oets.web.added == []
    assert learner.quarantined_shards()


def test_12_grounded_topic_sensitive_shard_can_still_enter_oets_normally():
    learner = ConsciousLearner()
    shard = _observe_n(learner, 6, "What is a vessel?", episode_source="afterthought")
    assert learner.check_admission(shard)[0] is True
    oets = _FakeOets()
    injected = learner.inject_into_oets(oets)
    assert injected == 1
    assert oets.web.added[0]["word"]


def test_13_no_node_is_created_with_an_internal_transport_label_as_subject():
    learner = ConsciousLearner()
    for label in ("afterthought", "pressure", "code", "simulation", "internal", "context", "pending"):
        shard = UnderstandingShard(
            shard_id=f"understand_{label}",
            response_concept=ResponseConcept.DIRECT_CLARITY,
            observation_summary="s",
            understanding=f"{label} opened depth when approached with direct clarity.",
            context_type="practical",
            confidence=0.9,
            observation_count=6,
            episode_source="afterthought",
            semantic_topic=label,
            topic_resolution_status="resolved",
            outcome_axis="T-axis expansion",
        )
        learner.shards[shard.shard_id] = shard
        learner._by_concept[shard.response_concept].append(shard.shard_id)

    oets = _FakeOets()
    injected = learner.inject_into_oets(oets)
    assert injected == 0
    assert oets.web.added == []
    for reason in learner.quarantined_shards().values():
        assert reason["reason"] == "internal_mechanism_label_as_subject"


def test_14_dreamtrainer_and_autonomy_bridges_respect_the_same_admission_decision():
    from aurora_dream_trainer import LearnedBehaviorApplicator

    learner = ConsciousLearner()
    _observe_n(learner, 6, "Hmm okay.")
    good_shard = _observe_n(learner, 6, "What is a vessel?", episode_source="afterthought")

    oets = _FakeOets()
    applicator = LearnedBehaviorApplicator()
    injected = applicator.inject_into_oets(learner, oets)
    assert injected == 1
    assert oets.web.added[0]["meaning"] == good_shard.understanding


def test_15_quarantined_shards_remain_inspectable_and_are_not_silently_deleted():
    learner = ConsciousLearner()
    bad_shard = _observe_n(learner, 6, "Hmm okay.")
    oets = _FakeOets()
    learner.inject_into_oets(oets)
    assert bad_shard.shard_id in learner.shards
    record = learner.quarantined_shards().get(bad_shard.shard_id)
    assert record is not None
    assert record["reason"] == "unresolved_topic"
