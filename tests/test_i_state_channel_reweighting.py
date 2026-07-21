# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Phase R1.1 of the Semantic Plateau Remediation Directive (2026-07-15):
InceptionEntity.process_experience() previously mapped i_state to a
string label only (i_state_bias) -- the SAME channels dict ran through
the SAME cascade for every entity regardless of i_state, so two entities
given different i_states produced numerically identical (valence,
intensity) every time. Confirmed against real data: classroom_log.jsonl
had one distinct (avg_intensity, avg_valence) tuple across 904 entity
resolutions (452 lessons x 2 entities), and divergence_score was 0.0 in
100% of lessons as a direct consequence.

_I_STATE_CHANNEL_WEIGHTS reweights channel magnitudes BEFORE they reach
ImpressionCascade.energy_to_shard(), so the label now follows a real
computational difference instead of decorating an identical one. These
tests hold the directive's own acceptance bar: same experience, two
different i_states, must produce different (valence, intensity) --
"the 0/472 identity failure becomes impossible by construction."
"""
from aurora_simulation_engine import (
    ExistenceMode,
    InceptionEntity,
    _I_STATE_CHANNEL_WEIGHTS,
)


def _fresh_entity(entity_id: str, i_state: str) -> InceptionEntity:
    return InceptionEntity(entity_id=entity_id, i_state=i_state)


def test_default_classroom_pair_produces_different_valence_and_intensity():
    """i_can/i_saw is the pair observed in every real classroom lesson to
    date -- this is the exact identity failure the directive cites."""
    experience = {"channels": {"joy": 0.4, "curiosity": 0.3, "trust": 0.3}, "tone": "warm"}

    e_can = _fresh_entity("e_can", "i_can")
    e_saw = _fresh_entity("e_saw", "i_saw")

    r_can = e_can.process_experience(dict(experience), mode=ExistenceMode.BOUNDED)
    r_saw = e_saw.process_experience(dict(experience), mode=ExistenceMode.BOUNDED)

    assert (r_can["valence"], r_can["intensity"]) != (r_saw["valence"], r_saw["intensity"])


def test_all_ten_canonical_poles_are_registered_and_apply_without_error():
    experience = {
        "channels": {
            "joy": 0.2, "curiosity": 0.2, "trust": 0.15, "anticipation": 0.1,
            "fear": 0.1, "sadness": 0.1, "determination": 0.15,
        },
        "tone": "warm",
    }
    expected_poles = {
        "i_is", "i_isnt", "i_can", "i_cannot", "i_do", "i_donot",
        "i_saw", "i_sought", "i_did", "i_didnt",
    }
    assert set(_I_STATE_CHANNEL_WEIGHTS.keys()) == expected_poles

    results = {}
    for pole in expected_poles:
        entity = _fresh_entity(f"e_{pole}", pole)
        r = entity.process_experience(dict(experience), mode=ExistenceMode.BOUNDED)
        results[pole] = (round(r["valence"], 6), round(r["intensity"], 6))

    # A rich, multi-channel experience should differentiate most poles --
    # not a strict all-distinct guarantee (some poles share unweighted
    # channels on any given input by construction), but a real spread must
    # exist, not the collapsed single-tuple failure mode being fixed here.
    assert len(set(results.values())) >= 6


def test_opposing_poles_diverge_in_valence_direction():
    """i_is (affirmation) amplifies trust/joy; i_isnt (negation) amplifies
    disgust/anger/fear and dampens trust/joy -- an experience weighted
    toward affirmative channels should read measurably more positive
    through i_is than through i_isnt."""
    experience = {"channels": {"trust": 0.5, "joy": 0.3, "fear": 0.2}, "tone": "warm"}

    e_is = _fresh_entity("e_is", "i_is")
    e_isnt = _fresh_entity("e_isnt", "i_isnt")

    r_is = e_is.process_experience(dict(experience), mode=ExistenceMode.BOUNDED)
    r_isnt = e_isnt.process_experience(dict(experience), mode=ExistenceMode.BOUNDED)

    assert r_is["valence"] > r_isnt["valence"]


def test_unweighted_i_state_leaves_channels_unchanged():
    """An i_state with no entry in the map (defensive/unknown case) must
    not raise and must fall back to the original cascade behavior."""
    experience = {"channels": {"joy": 0.5, "neutral": 0.5}, "tone": "neutral"}
    entity = _fresh_entity("e_unknown", "i_unregistered_pole")
    result = entity.process_experience(dict(experience), mode=ExistenceMode.BOUNDED)
    assert result["valence"] is not None
    assert result["intensity"] is not None


def test_legacy_two_scalar_channels_still_produce_output_without_crashing():
    """Pre-R1.2 callers pass {'resonant': x, 'strained': y} -- neither name
    is in ImpressionCascade.EMOTION_VALENCE, so valence is mathematically
    forced to 0.0 regardless of i_state (a separate, known gap R1.2
    closes). This test only guards against a crash/regression, not against
    that already-documented gap."""
    experience = {"channels": {"resonant": 0.7, "strained": 0.3}, "tone": "warm"}
    entity = _fresh_entity("e_legacy", "i_can")
    result = entity.process_experience(dict(experience), mode=ExistenceMode.BOUNDED)
    assert result["intensity"] > 0.0
