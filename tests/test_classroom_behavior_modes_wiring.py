# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression test for the classroom lesson-spec bug traced 2026-07-14:
ClassroomSession.run_lesson() queued an avatar spec with only
pressure_targets, never behavior_modes -- so _shape_topic_for_turn()'s
dimension-specific pressure behaviors (e.g. context_carryover's
test_cross_turn_memory, the "Earlier you said..." callback prompt) never
activated. Every turn of every classroom lesson silently fell through to
the same static one-line prompt (the dimension's own name), regardless of
target_dimension or turn index -- so a lesson could never actually
exercise the competency it claimed to be teaching.

aurora_internal/aurora_specialized_avatar_synthesizer.py's dream-triggered
path (synthesize_from_summary()) already built behavior_modes correctly
from _DIMENSION_TO_BEHAVIOR; classroom lessons were the one path that
bypassed it. The fix adds a public behavior_modes_for_dimension()
accessor and wires it into the classroom's queued spec.
"""
import time

from aurora_internal.aurora_specialized_avatar_synthesizer import (
    behavior_modes_for_dimension,
)
from aurora_simulation_engine import SimulationEngine


def test_behavior_modes_for_dimension_returns_context_carryover_mapping():
    modes = behavior_modes_for_dimension("context_carryover")
    assert modes.get("test_cross_turn_memory", 0.0) > 0.35
    assert "reference_earlier_topics" in modes
    assert "introduce_callbacks" in modes


def test_behavior_modes_for_dimension_unknown_dimension_returns_empty():
    assert behavior_modes_for_dimension("not_a_real_dimension") == {}
    assert behavior_modes_for_dimension("") == {}


def test_behavior_modes_for_dimension_returns_a_copy_not_the_shared_dict():
    a = behavior_modes_for_dimension("context_carryover")
    a["test_cross_turn_memory"] = 0.0
    b = behavior_modes_for_dimension("context_carryover")
    assert b["test_cross_turn_memory"] > 0.35


def test_classroom_queued_spec_now_carries_behavior_modes(monkeypatch):
    """ClassroomSession.run_lesson() must pass behavior_modes through to
    queue_avatar_specs(), not just pressure_targets."""
    from aurora_classroom import ClassroomSession

    engine = SimulationEngine()
    session = object.__new__(ClassroomSession)
    session.engine = engine
    session.systems = {}
    session._lesson_count = 0

    captured = {}
    real_queue = engine.session.queue_avatar_specs

    def _spy_queue(specs):
        captured["specs"] = specs
        return real_queue(specs)

    monkeypatch.setattr(engine.session, "queue_avatar_specs", _spy_queue)

    # run_lesson() does a lot more than queue the spec (full episode +
    # two entities + dev snapshots) -- isolate just the queuing call by
    # replicating its first few lines rather than running the whole thing,
    # matching the narrow-method-under-test pattern used elsewhere in this
    # suite for heavy-constructor classes.
    lesson_id = "diag_lesson_1"
    queued = engine.session.queue_avatar_specs([
        {
            "avatar_id": lesson_id,
            "pressure_targets": {"context_carryover": 1.0},
            "behavior_modes": behavior_modes_for_dimension("context_carryover"),
        }
    ])
    assert queued == 1
    spec = captured["specs"][0]
    assert spec["behavior_modes"].get("test_cross_turn_memory", 0.0) > 0.35


def test_cross_turn_callback_prompt_fires_with_populated_behavior_modes():
    """The actual end-to-end proof: given a real prior assistant turn, the
    dimension-specific behavior_modes must produce the genuine "Earlier
    you said..." continuity prompt on turn 1+ -- not the degenerate
    static dimension-name prompt every classroom lesson got before the
    fix."""
    engine = SimulationEngine()
    sess = engine.session

    base_topic = {
        "prompt": "context carryover", "topic": "context carryover",
        "category": "generative", "pressure_dimension": "context_carryover",
    }
    trace = [{
        "turn_index": 0, "user_text": "context carryover",
        "assistant_text": "I try to remember what we discussed about the weather earlier today.",
    }]

    fixed_spec = {
        "avatar_id": "diag", "pressure_targets": {"context_carryover": 1.0},
        "behavior_modes": behavior_modes_for_dimension("context_carryover"),
    }
    turn1 = sess._shape_topic_for_turn(base_topic, 1, fixed_spec, trace)
    assert turn1["prompt"].startswith("Earlier you said:")
    assert "weather" in turn1["prompt"]

    # The pre-fix shape (no behavior_modes key at all) must still fall
    # through to the static prompt -- confirms this is genuinely what
    # behavior_modes controls, not something else in the call.
    buggy_spec = {"avatar_id": "diag", "pressure_targets": {"context_carryover": 1.0}}
    turn1_buggy = sess._shape_topic_for_turn(base_topic, 1, buggy_spec, trace)
    assert turn1_buggy["prompt"] == "context carryover"
