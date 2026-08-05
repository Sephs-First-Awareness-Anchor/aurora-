from __future__ import annotations

from aurora_internal.aurora_operational_synthesis import (
    AXES,
    AuroraOperationalSynthesisChamber,
    execute_program,
)


class _Genealogy:
    def __init__(self):
        self.registered = []

    def register_emergent_operational_synthesis(self, payload):
        self.registered.append(dict(payload))
        return {"registered": True, "ability_id": "A:OP_SYNTH_TEST"}


def _advance_with_holdouts(chamber, task_id, holdouts):
    for input_value, output_value in holdouts:
        chamber.observe_example(
            task_id,
            input_value,
            output_value,
            validation=True,
            source="unseen_holdout",
        )


def test_veyra_operation_is_synthesized_and_generalizes():
    genealogy = _Genealogy()
    chamber = AuroraOperationalSynthesisChamber(persist=False, genealogy=genealogy)
    chamber.attach_systems({"genealogy": genealogy})

    training = [
        (["a", "b", "c"], ["b", "c", "a", "c"]),
        (["d", "e", "f"], ["e", "f", "d", "f"]),
        (["g", "h", "i"], ["h", "i", "g", "i"]),
    ]
    for input_value, output_value in training:
        chamber.observe_example("veyra", input_value, output_value, need_description="unknown symbolic transform")

    result = chamber.execute("veyra", ["j", "k", "l"])
    assert result["executed"] is True
    assert result["output"] == ["k", "l", "j", "l"]

    holdouts = [
        ([f"u{i}", f"v{i}", f"w{i}"], [f"v{i}", f"w{i}", f"u{i}", f"w{i}"])
        for i in range(10)
    ]
    _advance_with_holdouts(chamber, "veyra", holdouts)

    status = chamber.task_status("veyra")
    assert status["status"] == "promoted"
    assert status["candidate"]["status"] == "promoted"
    assert status["candidate"]["genealogy_ability_id"] == "A:OP_SYNTH_TEST"
    assert set(status["candidate"]["root_constraints"]) == {"X", "T", "B", "A"}
    assert genealogy.registered
    assert genealogy.registered[-1]["primitive_sequence"] == [
        "SEQUENCE", "SELECT", "SELECT", "SELECT", "SELECT"
    ]


def test_numeric_relation_can_be_composed_from_same_root_substrate():
    chamber = AuroraOperationalSynthesisChamber(persist=False)
    for input_value, output_value in [([2, 3], 5), ([4, 5], 9), ([7, 1], 8)]:
        chamber.observe_example("sum_pair", input_value, output_value)
    result = chamber.execute("sum_pair", [10, 11])
    assert result["executed"] is True
    assert result["output"] == 21
    description = chamber.task_status("sum_pair")["description"]
    assert description.startswith("add(")


def test_mapping_reconstruction_is_not_tied_to_a_domain_label():
    chamber = AuroraOperationalSynthesisChamber(persist=False)
    examples = [
        ({"left": "a", "right": "b"}, {"first": "b", "second": "a"}),
        ({"left": "c", "right": "d"}, {"first": "d", "second": "c"}),
        ({"left": "e", "right": "f"}, {"first": "f", "second": "e"}),
    ]
    for input_value, output_value in examples:
        chamber.observe_example("unnamed_relation", input_value, output_value)
    result = chamber.execute("unnamed_relation", {"left": "g", "right": "h"})
    assert result["output"] == {"first": "h", "second": "g"}


def test_repeated_identical_example_cannot_create_an_ability():
    chamber = AuroraOperationalSynthesisChamber(persist=False)
    for _ in range(8):
        chamber.observe_example("rote", ["a", "b"], ["b", "a"])
    status = chamber.task_status("rote")
    assert status["candidate"] is None
    assert status["distinct_training_inputs"] == 1


def test_contradictory_examples_block_synthesis():
    chamber = AuroraOperationalSynthesisChamber(persist=False)
    chamber.observe_example("conflict", [1, 2], [2, 1])
    chamber.observe_example("conflict", [3, 4], [4, 3])
    chamber.observe_example("conflict", [1, 2], [1, 2])
    chamber.observe_example("conflict", [5, 6], [6, 5])
    status = chamber.task_status("conflict")
    assert status["conflicts"] >= 1
    assert status["candidate"] is None


def test_executor_rejects_unknown_or_unbounded_operations():
    try:
        execute_program({"op": "PYTHON", "args": []}, [1, 2, 3])
    except ValueError as exc:
        assert "unknown_synthesis_primitive" in str(exc)
    else:
        raise AssertionError("unknown operation was executed")

    deeply_nested = {"op": "CONST", "value": 1}
    for _ in range(300):
        deeply_nested = {"op": "ABS", "args": [deeply_nested]}
    try:
        execute_program(deeply_nested, 0, budget=32)
    except RuntimeError as exc:
        assert "operation_budget_exceeded" in str(exc)
    else:
        raise AssertionError("execution budget was not enforced")


def test_trial_state_persists_across_restart(tmp_path):
    chamber = AuroraOperationalSynthesisChamber(state_dir=str(tmp_path), persist=True)
    for input_value, output_value in [
        (["a", "b", "c"], ["b", "c", "a", "c"]),
        (["d", "e", "f"], ["e", "f", "d", "f"]),
        (["g", "h", "i"], ["h", "i", "g", "i"]),
    ]:
        chamber.observe_example("persisted", input_value, output_value)
    before = chamber.task_status("persisted")
    assert before["candidate"] is not None
    assert before["warp_component_id"]

    restored = AuroraOperationalSynthesisChamber(state_dir=str(tmp_path), persist=True)
    after = restored.task_status("persisted")
    assert after["candidate"]["program_id"] == before["candidate"]["program_id"]
    assert after["warp_component_id"] == before["warp_component_id"]
    assert restored.warp_status()["trials"] == 1


def test_promoted_program_registers_when_genealogy_attaches_later():
    chamber = AuroraOperationalSynthesisChamber(persist=False)
    for input_value, output_value in [
        (["a", "b", "c"], ["b", "c", "a", "c"]),
        (["d", "e", "f"], ["e", "f", "d", "f"]),
        (["g", "h", "i"], ["h", "i", "g", "i"]),
    ]:
        chamber.observe_example("late_genealogy", input_value, output_value)
    for i in range(10):
        chamber.observe_example(
            "late_genealogy",
            [f"a{i}", f"b{i}", f"c{i}"],
            [f"b{i}", f"c{i}", f"a{i}", f"c{i}"],
            validation=True,
        )
    assert chamber.task_status("late_genealogy")["candidate"]["genealogy_ability_id"] == ""

    genealogy = _Genealogy()
    chamber.attach_systems({"genealogy": genealogy})
    status = chamber.task_status("late_genealogy")
    assert status["candidate"]["genealogy_ability_id"] == "A:OP_SYNTH_TEST"
    assert genealogy.registered


def test_domain_neutral_experience_intake_exposes_no_domain_gate():
    chamber = AuroraOperationalSynthesisChamber(persist=False)
    payloads = [
        {"input": ["a", "b"], "output": ["b", "a"], "domain": "music"},
        {"input": ["c", "d"], "output": ["d", "c"], "domain": "memory"},
        {"input": ["e", "f"], "output": ["f", "e"], "domain": "planning"},
    ]
    for index, payload in enumerate(payloads):
        payload.update({"task_id": "cross_domain_swap", "source": f"organ:{index}"})
        result = chamber.observe_experience(payload)
        assert result["accepted"] is True
    assert chamber.execute("cross_domain_swap", ["g", "h"])["output"] == ["h", "g"]
