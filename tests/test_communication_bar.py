# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Communication emergence: lower bar, evidence-paced clock, corrections undo promotion.

Sunni, 2026-11-07: "with the ability to be corrected or directed towards
proper understanding [her] bar [should be] more lax ... without the time drag".
"""
from __future__ import annotations

from aurora_internal.aurora_constraint_semantic_continuity import (
    derive_constraint_grounded_candidate,
)

from tests.test_communication_emergence import _axes, _field, _seed_causal_trial, _state

PROMPTS = [
    "What makes a bridge elegant?",
    "What makes a machine elegant?",
    "What makes a plan elegant?",
    "What makes a structure elegant?",
    "What makes a method elegant?",
]


def _use(field, idx, kind, score):
    text = PROMPTS[idx % len(PROMPTS)]
    prepared = field.prepare_semantic_state(_state(text), raw_text=text, axis_activation=_axes())
    candidate = derive_constraint_grounded_candidate(prepared)
    rid = f"use:{idx}"
    turn = field.observe_turn(
        semantic_state=prepared,
        raw_text=text,
        response_text=candidate["text"],
        response_source=candidate["source"],
        response_confidence=candidate["confidence"],
        response_id=rid,
    )
    outcome = field.record_receiver_outcome(
        rid, {"outcome_kind": kind, "score": score, "observed_effect": "test"}
    )
    return turn, outcome


def test_two_understood_uses_in_two_wordings_promote(tmp_path):
    field = _field(tmp_path)
    _seed_causal_trial(field)
    promoted = []
    for idx in range(2):
        _, outcome = _use(field, idx, "positive", 0.9)
        promoted.extend(outcome["promoted"])
    assert promoted, "two understood uses in two wordings should be enough now"
    assert field.status()["promoted_operations"] == 1


def test_one_use_is_still_not_enough(tmp_path):
    field = _field(tmp_path)
    _seed_causal_trial(field)
    _, outcome = _use(field, 0, "positive", 0.95)
    assert not outcome["promoted"]
    assert field.status()["trial_operations"] == 1


def test_waiting_for_evidence_does_not_kill_a_trial(tmp_path):
    field = _field(tmp_path)
    _seed_causal_trial(field)
    # The shared WARP clock dissolved trials at ten evaluations regardless
    # of whether any receiver had answered yet.
    for _ in range(40):
        field.evaluate_development()
    assert field.status()["trial_operations"] == 1
    assert field.status()["dissolved_operations"] == 0
    # ...and it can still earn its place once evidence arrives.
    promoted = []
    for idx in range(2):
        promoted.extend(_use(field, idx, "positive", 0.9)[1]["promoted"])
    assert promoted


def test_evidence_that_says_it_fails_still_dissolves(tmp_path):
    field = _field(tmp_path)
    _seed_causal_trial(field)
    dissolved = []
    for idx in range(6):
        dissolved.extend(_use(field, idx, "negative", 0.1)[1]["dissolved"])
        if dissolved:
            break
    assert dissolved
    assert field.status()["dissolved_operations"] == 1


def test_corrections_send_a_kept_operation_back_to_trial(tmp_path):
    field = _field(tmp_path)
    _seed_causal_trial(field)
    for idx in range(2):
        _use(field, idx, "positive", 0.9)
    assert field.status()["promoted_operations"] == 1

    _, first = _use(field, 2, "negative", 0.1)
    assert not first["demoted"], "one misunderstanding is not enough"
    _, second = _use(field, 3, "negative", 0.1)
    assert second["demoted"]
    status = field.status()
    assert status["promoted_operations"] == 0
    assert status["trial_operations"] == 1
    assert status["demoted_operations"] == 1
    component_id = field.active_operations()[0]["component_id"]
    assert component_id in field._warp_trials
    assert component_id not in field._warp_promoted


def test_understood_more_than_misunderstood_stays_kept(tmp_path):
    field = _field(tmp_path)
    _seed_causal_trial(field)
    for idx in range(2):
        _use(field, idx, "positive", 0.9)
    _use(field, 2, "positive", 0.9)
    _use(field, 3, "positive", 0.9)
    _use(field, 4, "negative", 0.1)
    _, outcome = _use(field, 5, "negative", 0.1)
    assert not outcome["demoted"]
    assert field.status()["promoted_operations"] == 1


def test_new_bookkeeping_survives_restart(tmp_path):
    from aurora_internal.aurora_communication_emergence import AuroraCommunicationEmergence
    from aurora_warp_protocol import WarpField

    field = AuroraCommunicationEmergence(state_dir=str(tmp_path), persist=True)
    warp = WarpField()
    warp.register_warp_capable("communication_emergence", field)
    field.attach_systems({"warp_field": warp})
    _seed_causal_trial(field)
    for idx in range(2):
        _use(field, idx, "positive", 0.9)
    for idx in range(2, 4):
        _use(field, idx, "negative", 0.1)
    field._persist()
    before = field.active_operations()[0]

    reloaded = AuroraCommunicationEmergence(state_dir=str(tmp_path), persist=True)
    after = reloaded.active_operations()[0]
    assert after["demotions"] == before["demotions"] == 1
    assert after["promoted_at"] == before["promoted_at"] > 0
    assert after["evidence_seen"] == before["evidence_seen"]
    assert reloaded.status()["demoted_operations"] == 1
