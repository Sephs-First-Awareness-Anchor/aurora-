from pathlib import Path

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
