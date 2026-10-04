from pathlib import Path
from types import SimpleNamespace

import aurora
from aurora_internal.aurora_constraint_semantic_continuity import (
    derive_constraint_semantic_state,
    extract_relational_form,
)
from aurora_internal.aurora_recursive_causal_reasoning_waveform import (
    AuroraRecursiveCausalReasoningWaveform,
)


class FakeContract:
    def __init__(self):
        self.payloads = []

    def attach_pending_contributors(self, payload):
        self.payloads.append(payload)


class FakeIntrospection:
    def __init__(self):
        self.records = []

    def record_boundary_decision(self, *args, **kwargs):
        self.records.append((args, kwargs))


class FakeGenealogy:
    def __init__(self):
        self.abilities = {}
        self.registered = []

    def pressure_orientation(self):
        return {"X": 0.2, "T": 0.2, "N": 0.2, "B": 0.2, "A": 0.2}

    def register_recursive_causal_waveform(self, payload):
        self.registered.append(dict(payload))
        return {"registered": True, "ability_id": "A:RCRW_TEST"}


def _semantic(text):
    form = extract_relational_form(text)
    return derive_constraint_semantic_state(
        form,
        axis_activation={"X": 0.2, "T": 0.2, "N": 0.2, "B": 0.2, "A": 0.2},
    )


def test_raw_input_is_preserved_while_referent_is_reconstructed(tmp_path):
    bridge = AuroraRecursiveCausalReasoningWaveform(state_dir=str(tmp_path), persist=True)
    state = _semantic("Why did that happen?")
    out = bridge.prepare_semantic_state(
        state,
        raw_text="Why did that happen?",
        referent_map={"topic": "the failed response", "referent_map": {"that": "the failed response"}},
    )

    cycle = bridge.latest_cycle()
    assert cycle["raw_input"] == "Why did that happen?"
    assert cycle["provisional_interpretation"] != {}
    assert cycle["effective_interpretation"] != {}
    assert cycle["effective_interpretation"].get("subject") == "the failed response" or cycle["effective_interpretation"].get("obj") == "the failed response"
    assert out["recursive_causal_waveform"]["reconstruction"]["raw_input_preserved"] is True
    assert Path(tmp_path, "recursive_causal_reasoning_waveform.json").exists()


def test_focus_claim_can_restore_missing_relation_without_inventing_history(tmp_path):
    bridge = AuroraRecursiveCausalReasoningWaveform(state_dir=str(tmp_path), persist=False)
    state = _semantic("Why that?")
    state["relational_form"]["relation"] = ""
    state["unresolved"] = ["relation"]

    bridge.prepare_semantic_state(
        state,
        raw_text="Why that?",
        referent_map={"topic": "the response"},
        claim_resolution={
            "focus_claim": {
                "subject": "the response",
                "relation": "failed",
                "object": "meaning preservation",
            }
        },
    )
    cycle = bridge.latest_cycle()
    assert cycle["effective_interpretation"]["relation"] == "failed"
    assert cycle["effective_interpretation"]["recursive_reconstruction"]["raw_preserved"] is True
    assert any(change["slot"] == "relation" for change in cycle["effective_interpretation"]["recursive_reconstruction"]["changes"])


def test_response_becomes_next_disturbance_and_understanding_receives_evidence(tmp_path):
    contract = FakeContract()
    introspection = FakeIntrospection()
    systems = {"understanding_contract": contract, "system_introspection": introspection}
    bridge = AuroraRecursiveCausalReasoningWaveform(state_dir=str(tmp_path), persist=True)
    bridge.attach_systems(systems)
    state = _semantic("What makes an invention elegant?")
    bridge.prepare_semantic_state(state, raw_text="What makes an invention elegant?", systems=systems)
    completed = bridge.complete_cycle(
        delivered_text="An invention becomes elegant when its parts remain coherent.",
        response_source="constraint_semantic_derivation",
        confidence=0.84,
        systems=systems,
    )
    event = bridge.receive_disturbance("I agree, and efficiency matters too.", systems=systems)

    assert completed["response_wave"]["text"].startswith("An invention")
    assert event["caused_by_response_cycle"] == completed["cycle_id"]
    assert bridge.latest_cycle()["receiver_disturbance"]["raw_text"].startswith("I agree")
    assert contract.payloads
    assert introspection.records


def test_every_wavelet_and_cycle_trace_returns_to_root_constraints(tmp_path):
    genealogy = FakeGenealogy()
    bridge = AuroraRecursiveCausalReasoningWaveform(
        state_dir=str(tmp_path), persist=False, genealogy=genealogy
    )
    state = _semantic("Can complexity itself be beautiful?")
    bridge.prepare_semantic_state(state, raw_text="Can complexity itself be beautiful?")
    trace = bridge.trace_to_roots()

    assert set(trace["root_constraints"]) == {"X", "T", "N", "B", "A"}
    assert trace["wavelet_ancestry"]
    for wavelet in trace["wavelet_ancestry"]:
        assert wavelet["roots"]
        assert wavelet["signature"]


def test_complete_cycle_records_retrospective_alignment(tmp_path):
    bridge = AuroraRecursiveCausalReasoningWaveform(state_dir=str(tmp_path), persist=False)
    state = _semantic("What makes an invention elegant?")
    bridge.prepare_semantic_state(state, raw_text="What makes an invention elegant?")
    cycle = bridge.complete_cycle(
        delivered_text="An invention becomes elegant when it keeps a coherent relation between its parts and purpose.",
        response_source="constraint_semantic_derivation",
        confidence=0.9,
    )

    assert cycle["status"] == "emitted"
    assert cycle["global_understanding"]["response_alignment"]["score"] > 0.5
    assert cycle["global_understanding"]["retrospective_confidence"] > 0.0
    assert cycle["response_wave"]["operation"]["root_constraints"] == ["X", "T", "N", "B", "A"]


def test_repeated_low_alignment_creates_a_warp_trial_wavelet(tmp_path):
    bridge = AuroraRecursiveCausalReasoningWaveform(state_dir=str(tmp_path), persist=False)
    for _ in range(3):
        state = _semantic("What makes an invention elegant?")
        bridge.prepare_semantic_state(state, raw_text="What makes an invention elegant?")
        bridge.complete_cycle(
            delivered_text="unrelated noise",
            response_source="probe",
            confidence=0.1,
        )
    assert bridge.status()["trial_wavelets"] >= 1
    assert bridge.warp_status()["trials"] >= 1


def test_live_turn_actually_invokes_and_consumes_rcrw_effective_interpretation(tmp_path):
    """Directive 3.2 / acceptance test "RCRW live-consumption test": run the
    ordinary live response-turn path (aurora.py's _chain_up3_purpose, the
    real caller inside _run_live_response_turn's up-chain), not a direct
    unit call on the waveform itself. Prove RCRW is invoked with the real
    user text, and that a material change in effective_interpretation
    actually changes state.relational_form/axis_activation/dominant_axis
    -- the same state PropositionFrame/_frame_from_constraint_relation
    read from systems["_active_turn_state"] -- rather than being computed
    and silently discarded."""

    class _SpyRCRW:
        def __init__(self):
            self.calls = []

        def prepare_semantic_state(self, semantic_state, *, raw_text,
                                    referent_map=None, claim_resolution=None,
                                    meaning_forms=None, axis_activation=None,
                                    systems=None):
            self.calls.append(raw_text)
            revised = dict(semantic_state)
            revised["relational_form"] = {
                "subject": "RCRW_BACKPROJECTED_SUBJECT",
                "relation": "reconstructed",
                "obj": "effective_interpretation_result",
                "confidence": 0.91,
            }
            revised["axis_activation"] = {
                "X": 0.05, "T": 0.05, "N": 0.05, "B": 0.05, "A": 0.90,
            }
            return revised

    spy = _SpyRCRW()
    user_text = "why did the glass fall after I bumped the table?"
    systems = {"recursive_causal_waveform": spy, "genealogy": None, "state_dir": str(tmp_path)}
    state = SimpleNamespace(
        relational_form=extract_relational_form(user_text),
        axis_activation={"X": 0.2, "T": 0.2, "N": 0.2, "B": 0.2, "A": 0.2},
        dominant_axis="N",
        pipeline_state={},
        referent_map={},
        claim_resolution={},
        meaning_forms=[],
        constraint_semantic_state={},
        genealogy_trace={},
        noncomp_input_state={},
        parsed={},
        surface_reactive_emotion={},
        deep_emotional_state={"dominant": "calm"},
        emotional_state={"dominant": "calm"},
    )

    aurora._chain_up3_purpose(user_text, systems, state)

    # RCRW was actually invoked, with the real turn text.
    assert spy.calls == [user_text]
    # Its effective_interpretation became causally authoritative for the
    # downstream relational_form/axis state -- not generated and ignored.
    assert state.relational_form["subject"] == "RCRW_BACKPROJECTED_SUBJECT"
    assert state.relational_form["relation"] == "reconstructed"
    assert state.axis_activation["A"] == 0.90
    assert state.dominant_axis == "A"


def test_live_turn_without_rcrw_registered_leaves_relational_form_untouched(tmp_path):
    """No systems["recursive_causal_waveform"] must fall back to exactly
    the pre-RCRW relational_form/axis_activation -- optional-organ
    absence must not raise or silently corrupt state."""
    user_text = "why did the glass fall after I bumped the table?"
    original_form = extract_relational_form(user_text)
    systems = {"genealogy": None, "state_dir": str(tmp_path)}
    state = SimpleNamespace(
        relational_form=dict(original_form),
        axis_activation={"X": 0.2, "T": 0.2, "N": 0.2, "B": 0.2, "A": 0.2},
        dominant_axis="N",
        pipeline_state={},
        referent_map={},
        claim_resolution={},
        meaning_forms=[],
        constraint_semantic_state={},
        genealogy_trace={},
        noncomp_input_state={},
        parsed={},
        surface_reactive_emotion={},
        deep_emotional_state={"dominant": "calm"},
        emotional_state={"dominant": "calm"},
    )

    aurora._chain_up3_purpose(user_text, systems, state)

    assert state.relational_form.get("subject") == original_form.get("subject")
    assert state.relational_form.get("relation") == original_form.get("relation")


def test_unrelated_focus_claim_cannot_donate_participants_or_pressure(tmp_path):
    """An active historical claim is not evidence merely because it is recent.

    A sparse new carrier must not become a chimera made from the new relation
    plus unrelated historical participants, and unrelated history should not
    inject a continuity wavelet into the current cycle.
    """
    bridge = AuroraRecursiveCausalReasoningWaveform(state_dir=str(tmp_path), persist=False)
    state = _semantic("Photosynthesis.")
    out = bridge.prepare_semantic_state(
        state,
        raw_text="Photosynthesis.",
        claim_resolution={
            "focus_claim": {
                "subject": "finding the blue key",
                "relation": "means",
                "object": "i own the blue key",
                "negated": True,
                "source": "user",
            }
        },
    )

    effective = out["relational_form"]
    assert effective.get("subject", "") != "finding the blue key"
    assert effective.get("obj", "") != "i own the blue key"
    claim_wavelets = [
        wave for wave in out["recursive_causal_waveform"]["control_wavelets"]
        if wave.get("source") == "claim_continuity"
    ]
    assert claim_wavelets == []


def test_negative_focus_relation_keeps_polarity_when_legitimately_restored(tmp_path):
    """If history supplies the relation, its causal polarity is the relation too."""
    bridge = AuroraRecursiveCausalReasoningWaveform(state_dir=str(tmp_path), persist=False)
    state = _semantic("Why that?")
    out = bridge.prepare_semantic_state(
        state,
        raw_text="Why that?",
        referent_map={
            "topic": "the response",
            "referent_map": {"that": "the response"},
        },
        claim_resolution={
            "focus_claim": {
                "subject": "the response",
                "relation": "failed",
                "object": "meaning preservation",
                "negated": True,
                "source": "user",
            }
        },
    )

    effective = out["relational_form"]
    assert effective["relation"] == "failed"
    assert effective["negated"] is True
    changes = out["recursive_causal_waveform"]["reconstruction"]["changes"]
    assert any(
        change.get("slot") == "negated"
        and change.get("evidence") == "active_focus_claim_relation_polarity"
        for change in changes
    )


def test_shared_entity_does_not_license_cross_relation_participant_splice(tmp_path):
    """Entity continuity cannot flatten two different causal relations together."""
    bridge = AuroraRecursiveCausalReasoningWaveform(state_dir=str(tmp_path), persist=False)
    state = _semantic("The blue key vanished.")
    out = bridge.prepare_semantic_state(
        state,
        raw_text="The blue key vanished.",
        claim_resolution={
            "focus_claim": {
                "subject": "finding the blue key",
                "relation": "means",
                "object": "i own the blue key",
                "negated": True,
                "source": "user",
            }
        },
    )

    effective = out["relational_form"]
    assert effective.get("relation", "").lower() != "means"
    assert effective.get("obj", "") != "i own the blue key"
    assert not any(
        wave.get("source") == "claim_continuity"
        for wave in out["recursive_causal_waveform"]["control_wavelets"]
    )
