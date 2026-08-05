from pathlib import Path
from types import SimpleNamespace

from aurora_expression_perception import LexicalMemory, SentenceComposer, VoiceGenome
from aurora_internal.aurora_proposition_frame import PropositionFrame
from aurora_internal.aurora_system_introspection import AuroraSystemIntrospection


REPO_ROOT = Path(__file__).resolve().parents[1]


def _bridge(tmp_path, *, persist=False):
    return AuroraSystemIntrospection(
        repo_root=str(REPO_ROOT),
        state_dir=str(tmp_path),
        persist=persist,
        build_index=True,
    )


def _composer(tmp_path, bridge):
    lexicon = LexicalMemory(state_dir=str(tmp_path))
    composer = SentenceComposer(lexicon, VoiceGenome(), state_dir=str(tmp_path))
    composer.set_system_introspection(bridge)
    return composer


def test_source_map_locates_real_slot_binder(tmp_path):
    bridge = _bridge(tmp_path)
    match = bridge.describe_function(
        "aurora_expression_perception.SentenceComposer._bind_slot_from_frame"
    )
    assert match["file"] == "aurora_expression_perception.py"
    assert match["line"] > 0
    assert "role" in match["signature"]


def test_bare_interrogative_rejection_is_introspectable(tmp_path):
    bridge = _bridge(tmp_path)
    bridge.begin_episode("Who made you?", turn_tick=1, session_id="test")
    composer = _composer(tmp_path, bridge)
    frame = PropositionFrame(
        subject="you", relation="make", obj="who", source="claim"
    )

    result = composer._bind_slot_from_frame("object", frame, ["agent"], ["I"])

    assert result is None
    episode = bridge.latest_episode()
    step = episode["steps"][-1]
    assert step["function_id"].endswith("_bind_slot_from_frame")
    assert step["decision"] == "rejected"
    assert step["inputs"]["frame_object"] == "who"
    assert step["derived"]["bare_interrogative"] is True
    assert step["derived"]["inferred_role"] != "noun"


def test_simulated_bad_binding_localizes_exact_function(tmp_path):
    bridge = _bridge(tmp_path)
    episode_id = bridge.begin_episode("Who made you?", turn_tick=1, session_id="test")
    bridge.record_boundary_decision(
        function_id=(
            "aurora_expression_perception.SentenceComposer."
            "_bind_slot_from_frame"
        ),
        stage="composer_slot_binding",
        inputs={"slot": "object", "frame_object": "who", "token": "who"},
        derived={"inferred_role": "noun", "bare_interrogative": False},
        decision="accepted",
        output="who",
        reason="unknown-word noun default accepted the frame object",
        confidence=0.95,
        tags=["composer", "slot_binding", "object", "visible_language"],
        anomaly="structural_interrogative_accepted_as_content",
    )
    diagnosis = bridge.finish_episode(
        delivered_text="I made who.",
        response_source="composer_unified",
        confidence=0.9,
        observed_problem={
            "type": "malformed_delivered_response",
            "description": "bare interrogative spoken as an object",
        },
    )

    assert diagnosis["episode_id"] == episode_id
    assert diagnosis["likely_boundary"]["function_id"].endswith(
        "SentenceComposer._bind_slot_from_frame"
    )
    assert diagnosis["confidence"] >= 0.8
    assert diagnosis["likely_boundary"]["file"] == "aurora_expression_perception.py"
    assert bridge.trace_value("who", episode_id=episode_id)


def test_valid_object_binding_remains_accepted(tmp_path):
    bridge = _bridge(tmp_path)
    bridge.begin_episode("What did you build?", turn_tick=2, session_id="test")
    composer = _composer(tmp_path, bridge)
    frame = PropositionFrame(
        subject="Aurora", relation="build", obj="system", source="claim"
    )

    result = composer._bind_slot_from_frame("object", frame, ["agent"], ["I"])

    assert result == "system"
    step = bridge.latest_episode()["steps"][-1]
    assert step["decision"] == "accepted"
    assert step["derived"]["inferred_role"] == "noun"
    assert not step["anomaly"]


def test_finish_episode_publishes_to_existing_systems(tmp_path):
    bridge = _bridge(tmp_path, persist=True)
    observer_events = []

    class Observer:
        def record_observation(self, target, data, source="OBSERVER", timestamp=None):
            observer_events.append((target, data, source))

    contributors = []

    class Contract:
        def attach_pending_contributors(self, payload):
            contributors.append(payload)
            return True

        def snapshot(self):
            return {}

    systems = {
        "state_dir": str(tmp_path),
        "quasiarch_observer": Observer(),
        "understanding_contract": Contract(),
        "_last_articulation_arbitration": {
            "rejection_reasons": ["composer_fails_wellformedness"]
        },
    }
    bridge.attach_systems(systems)
    bridge.begin_episode("test", turn_tick=1, session_id="test")
    bridge.record_boundary_decision(
        function_id="aurora._finalize_articulation",
        stage="response_arbitration",
        inputs={},
        derived={"rejection_reasons": ["composer_fails_wellformedness"]},
        decision="selected",
        output={"source": "grounded_chain"},
        anomaly="composer_candidate_rejected",
        tags=["articulation", "arbitration"],
    )
    diagnosis = bridge.finish_episode(
        delivered_text="My creator is Sunni Morningstar.",
        response_source="relational_role",
        confidence=0.8,
        systems=systems,
    )

    assert systems["_last_system_diagnosis"] == diagnosis
    assert contributors and "system_introspection" in contributors[-1]
    assert observer_events and observer_events[-1][2] == "SYSTEM_INTROSPECTION"
    assert (tmp_path / "last_system_diagnosis.json").exists()


def test_uninstrumented_problem_uses_source_map_as_explicit_hypothesis(tmp_path):
    bridge = _bridge(tmp_path)
    bridge.begin_episode("diagnose object slot binding", turn_tick=3, session_id="test")
    diagnosis = bridge.finish_episode(
        delivered_text="",
        response_source="diagnostic_probe",
        confidence=0.0,
        observed_problem={
            "type": "object_slot_binding_problem",
            "description": "inspect bind slot from frame object inference",
        },
    )

    target = diagnosis["likely_boundary"]
    assert target
    assert target["step_id"] == "source_map_hypothesis"
    assert target["confidence"] <= 0.48
    assert "no observed decision boundary" in target["reason"]


def test_runtime_fault_uses_source_derived_function_location(tmp_path):
    import time

    bridge = _bridge(tmp_path)
    systems = {
        "_last_runtime_fault": {
            "timestamp": time.time() + 0.01,
            "message": "synthetic fault",
            "exception_type": "RuntimeError",
            "context": {
                "module": "aurora",
                "function": "_finalize_articulation",
                "source_file": "aurora.py",
                "handler_line": 1,
            },
        }
    }
    bridge.attach_systems(systems)
    bridge.begin_episode("fault probe", turn_tick=4, session_id="test")
    diagnosis = bridge.finish_episode(
        delivered_text="fallback",
        response_source="grounded_chain",
        confidence=0.5,
        systems=systems,
    )

    target = diagnosis["likely_boundary"]
    assert target["function_id"] == "aurora._finalize_articulation"
    assert target["line"] > 1
    assert target["derived"]["source_line_verified_from_ast"] is True
    assert target["inputs"]["reported_handler_line"] == 1
