from __future__ import annotations

from pathlib import Path

from aurora_internal.aurora_communication_emergence import AuroraCommunicationEmergence
from aurora_internal.aurora_constraint_semantic_continuity import (
    derive_constraint_grounded_candidate,
    derive_constraint_semantic_state,
    extract_relational_form,
)
from aurora_warp_protocol import WarpField


def _axes():
    return {"X": 0.2, "T": 0.2, "N": 0.2, "B": 0.2, "A": 0.2}


def _state(text: str):
    return derive_constraint_semantic_state(
        extract_relational_form(text),
        axis_activation=_axes(),
    )


def _field(tmp_path: Path, genealogy=None):
    field = AuroraCommunicationEmergence(
        state_dir=str(tmp_path),
        persist=False,
        genealogy=genealogy,
    )
    warp = WarpField()
    warp.register_warp_capable("communication_emergence", field)
    field.attach_systems({"warp_field": warp, "genealogy": genealogy})
    return field


def _seed_causal_trial(field: AuroraCommunicationEmergence):
    prompts = [
        "What makes an invention elegant?",
        "What makes a tool elegant?",
        "What makes a solution elegant?",
    ]
    for idx, text in enumerate(prompts):
        field.observe_turn(
            semantic_state=_state(text),
            raw_text=text,
            response_text="I don't have a clear sense of that.",
            response_source="constraint_abstain",
            response_confidence=0.4,
            response_id=f"fail:{idx}",
        )


def test_persistent_constraint_gap_derives_trial_operation(tmp_path):
    field = _field(tmp_path)
    _seed_causal_trial(field)

    operations = field.active_operations()
    assert len(operations) == 1
    operation = operations[0]
    assert operation["status"] == "trial"
    assert operation["canonical_signature"] == "X^1*N^1*B^1*A^1"
    assert operation["primitive_sequence"][-1] == "proposition_understanding"
    assert set(operation["root_constraints"]) == {"X", "N", "B", "A"}
    assert operation["parent_ids"]


def test_trial_generalizes_by_relational_shape_not_exact_wording(tmp_path):
    field = _field(tmp_path)
    _seed_causal_trial(field)

    new_text = "What makes a bridge elegant?"
    prepared = field.prepare_semantic_state(
        _state(new_text),
        raw_text=new_text,
        axis_activation=_axes(),
    )
    operation = prepared.get("emergent_operation")
    assert operation
    assert operation["status"] == "trial"
    assert prepared["relational_form"]["obj"] == "bridge"
    assert prepared["relational_form"]["complement"] == "elegant"
    assert "bridge" in prepared["response_obligation"]["must_preserve"]
    assert "what" in prepared["response_obligation"]["must_not_replace_with"]


def test_coherent_turn_does_not_confess_a_missing_function(tmp_path):
    field = _field(tmp_path)
    text = "What makes an invention elegant?"
    semantic = _state(text)
    candidate = derive_constraint_grounded_candidate(semantic)
    result = field.observe_turn(
        semantic_state=semantic,
        raw_text=text,
        response_text=candidate["text"],
        response_source=candidate["source"],
        response_confidence=candidate["confidence"],
        response_id="coherent:1",
    )
    assert result["deficits"] == []
    assert field.status()["trial_operations"] == 0


class _GenealogyProbe:
    def __init__(self):
        self.payloads = []

    def register_emergent_communication_operation(self, payload):
        self.payloads.append(dict(payload))
        return {"registered": True, "ability_id": "A:COMM_TEST"}


def test_varied_receiver_validated_trials_promote_into_genealogy(tmp_path):
    genealogy = _GenealogyProbe()
    field = _field(tmp_path, genealogy=genealogy)
    _seed_causal_trial(field)

    prompts = [
        "What makes a bridge elegant?",
        "What makes a machine elegant?",
        "What makes a plan elegant?",
        "What makes a structure elegant?",
        "What makes a method elegant?",
    ]
    promoted = []
    for idx in range(10):
        text = prompts[idx % len(prompts)]
        prepared = field.prepare_semantic_state(
            _state(text), raw_text=text, axis_activation=_axes()
        )
        candidate = derive_constraint_grounded_candidate(prepared)
        response_id = f"success:{idx}"
        turn = field.observe_turn(
            semantic_state=prepared,
            raw_text=text,
            response_text=candidate["text"],
            response_source=candidate["source"],
            response_confidence=candidate["confidence"],
            response_id=response_id,
        )
        assert turn["trial_component_id"]
        outcome = field.record_receiver_outcome(
            response_id,
            {
                "outcome_kind": "positive",
                "score": 0.95,
                "observed_effect": "resolved_fully",
            },
        )
        promoted.extend(outcome["promoted"])

    assert promoted
    assert field.status()["promoted_operations"] == 1
    assert genealogy.payloads
    payload = genealogy.payloads[0]
    assert payload["canonical_signature"] == "X^1*N^1*B^1*A^1"
    assert payload["evidence_count"] == 10
    assert payload["distinct_surfaces"] >= 3
    assert field.active_operations()[0]["genealogy_ability_id"] == "A:COMM_TEST"


def test_single_surface_repetition_cannot_earn_promotion_score(tmp_path):
    field = _field(tmp_path)
    _seed_causal_trial(field)
    component_id = field.active_operations()[0]["component_id"]
    operation = field._operations[component_id]
    operation.evidence = [
        {
            "surface_hash": "same",
            "validated": True,
            "outcome_kind": "positive",
            "receiver_score": 1.0,
            "relation_alignment": 1.0,
        }
        for _ in range(12)
    ]
    component = field._warp_trials[component_id]
    assert field._score_trial(component) < 0.60


def test_coherent_non_trial_turn_does_not_wait_for_receiver_validation(tmp_path):
    field = _field(tmp_path)
    text = "What makes an invention elegant?"
    semantic = _state(text)
    candidate = derive_constraint_grounded_candidate(semantic)
    field.observe_turn(
        semantic_state=semantic,
        raw_text=text,
        response_text=candidate["text"],
        response_source=candidate["source"],
        response_confidence=candidate["confidence"],
        response_id="coherent:no-pending",
    )
    assert field.status()["pending_receiver_validation"] == 0
