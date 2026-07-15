# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Phase R1.2 of the Semantic Plateau Remediation Directive (2026-07-15):
aurora_classroom.py::_episode_to_entity_experience(). The function used to
compress an entire episode into two scalars, {"resonant": x, "strained":
1-x} -- names that are not entries in ImpressionCascade.EMOTION_VALENCE
(aurora_expression_perception.py), so InceptionEntity.process_experience()'s
valence computation was mathematically forced to 0.0 every time, and since
strained == 1 - resonant, the channel magnitudes always summed to exactly
1.0, forcing intensity to a fixed 1/3. That is the literal arithmetic
behind the (0.3333, 0.0) constant tuple observed across all 904 real
entity resolutions in classroom_log.jsonl.

These tests hold the replacement adapter to: real EMOTION_VALENCE channel
names (so valence is no longer dead by construction), per-turn momentum,
grounded/understanding signal, target-dimension texture, and engagement
pull -- plus the unchanged dict contract downstream code depends on.
"""
from aurora_classroom import (
    _DIMENSION_CHANNEL_TEXTURE,
    _episode_to_entity_experience,
)
from aurora_expression_perception import ImpressionCascade
from aurora_simulation_engine import EpisodeResult, ExistenceMode, InceptionEntity


def _episode(**overrides) -> EpisodeResult:
    defaults = dict(
        episode_id="e1",
        avatar_personality="CURIOUS",
        topic_category="general",
        turns=4,
        avg_fitness=0.6,
        final_engagement=0.5,
        understanding_gained=[],
        relics_formed=0,
        conversation_trace=[],
    )
    defaults.update(overrides)
    return EpisodeResult(**defaults)


def test_dict_contract_unchanged():
    exp = _episode_to_entity_experience(_episode(), "context_carryover")
    assert set(exp.keys()) == {
        "channels", "tone", "target_dimension", "topic_category", "understanding_gained",
    }


def test_channels_use_real_emotion_valence_vocabulary():
    exp = _episode_to_entity_experience(_episode(), "contradiction_handling")
    for channel_name in exp["channels"]:
        assert channel_name in ImpressionCascade.EMOTION_VALENCE, channel_name


def test_no_more_resonant_strained_two_scalar_compression():
    exp = _episode_to_entity_experience(_episode(), "boundary_calibration")
    assert "resonant" not in exp["channels"]
    assert "strained" not in exp["channels"]


def test_valence_is_no_longer_forced_to_zero():
    """The literal bug: old channel names weren't in EMOTION_VALENCE, so
    valence was 0.0 by construction regardless of episode quality."""
    trace = [
        {"turn_index": i, "fitness": 0.3 + i * 0.15, "engagement": 0.2 + i * 0.15}
        for i in range(4)
    ]
    exp = _episode_to_entity_experience(
        _episode(avg_fitness=0.7, final_engagement=0.6, conversation_trace=trace,
                 understanding_gained=["learned something"]),
        "uncertainty_signaling",
    )
    entity = InceptionEntity(entity_id="e1", i_state="i_can")
    result = entity.process_experience(dict(exp), mode=ExistenceMode.BOUNDED)
    assert result["valence"] != 0.0


def test_rising_momentum_differs_from_falling_momentum():
    rising_trace = [{"turn_index": i, "fitness": f, "engagement": 0.4} for i, f in enumerate([0.2, 0.4, 0.6, 0.8])]
    falling_trace = [{"turn_index": i, "fitness": f, "engagement": 0.4} for i, f in enumerate([0.8, 0.6, 0.4, 0.2])]

    rising_exp = _episode_to_entity_experience(
        _episode(avg_fitness=0.5, conversation_trace=rising_trace), "semantic_precision",
    )
    falling_exp = _episode_to_entity_experience(
        _episode(avg_fitness=0.5, conversation_trace=falling_trace), "semantic_precision",
    )
    assert rising_exp["channels"] != falling_exp["channels"]
    assert rising_exp["channels"].get("determination", 0.0) > falling_exp["channels"].get("determination", 0.0)


def test_grounded_understanding_shifts_channels():
    grounded_exp = _episode_to_entity_experience(
        _episode(understanding_gained=["insight one", "insight two"]), "coherence_maintenance",
    )
    ungrounded_exp = _episode_to_entity_experience(
        _episode(understanding_gained=[]), "coherence_maintenance",
    )
    assert grounded_exp["channels"] != ungrounded_exp["channels"]
    assert grounded_exp["understanding_gained"] == ["insight one", "insight two"]
    assert ungrounded_exp["understanding_gained"] == []


def test_different_target_dimensions_produce_different_texture():
    exp_a = _episode_to_entity_experience(_episode(), "contradiction_handling")
    exp_b = _episode_to_entity_experience(_episode(), "boundary_calibration")
    assert exp_a["channels"] != exp_b["channels"]


def test_all_default_candidate_dimensions_have_texture_entries():
    from aurora_classroom import _DEFAULT_CANDIDATE_DIMENSIONS
    for dim in _DEFAULT_CANDIDATE_DIMENSIONS:
        assert dim in _DIMENSION_CHANNEL_TEXTURE, dim


def test_unknown_dimension_falls_back_gracefully():
    exp = _episode_to_entity_experience(_episode(), "some_future_dimension_not_yet_mapped")
    assert exp["channels"]  # never empty
    entity = InceptionEntity(entity_id="e1", i_state="i_is")
    result = entity.process_experience(dict(exp), mode=ExistenceMode.BOUNDED)
    assert result["intensity"] is not None


def test_engagement_pull_differs_between_rising_and_flat_engagement():
    flat_trace = [{"turn_index": i, "fitness": 0.5, "engagement": 0.5} for i in range(4)]
    rising_trace = [{"turn_index": i, "fitness": 0.5, "engagement": e} for i, e in enumerate([0.2, 0.3, 0.4, 0.9])]

    flat_exp = _episode_to_entity_experience(
        _episode(final_engagement=0.5, conversation_trace=flat_trace), "framing_selection",
    )
    rising_exp = _episode_to_entity_experience(
        _episode(final_engagement=0.9, conversation_trace=rising_trace), "framing_selection",
    )
    assert rising_exp["channels"].get("anticipation", 0.0) > flat_exp["channels"].get("anticipation", 0.0)
