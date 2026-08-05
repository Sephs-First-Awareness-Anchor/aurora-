from __future__ import annotations

from aurora_internal.aurora_general_execution_foundry import (
    AuroraGeneralExecutionFoundry,
    CapabilityDenied,
    CapabilitySpec,
    ExecutionLimits,
    GeneralProgramExecutor,
    execute_python_sandbox,
    validate_python_source,
)


class _Genealogy:
    def __init__(self):
        self.records = []

    def register_emergent_general_execution(self, payload):
        self.records.append(dict(payload))
        return {"registered": True, "ability_id": "A:GEN_EXEC_TEST"}


def _add_holdouts(foundry, task_id, pairs):
    for input_value, output_value in pairs:
        foundry.observe_example(task_id, input_value, output_value, validation=True, source="holdout")


def test_loop_is_synthesized_and_transpiled_to_new_python():
    genealogy = _Genealogy()
    foundry = AuroraGeneralExecutionFoundry(persist=False, genealogy=genealogy)
    foundry.attach_systems({"genealogy": genealogy})
    for input_value, output_value in [([1, 2, 3], 6), ([4, 5], 9), ([10, -2, 1], 9)]:
        foundry.observe_example("sum_loop", input_value, output_value)
    status = foundry.task_status("sum_loop")
    assert status["candidate"]["kind"] == "loop"
    assert "for index, item in enumerate" in status["candidate"]["source_python"]
    assert foundry.execute("sum_loop", [7, 8, 9])["output"] == 24
    sandboxed = execute_python_sandbox(status["candidate"]["source_python"], [7, 8, 9])
    assert sandboxed["executed"] is True
    assert sandboxed["output"] == 24

    _add_holdouts(foundry, "sum_loop", [([i, i + 1, i + 2], 3 * i + 3) for i in range(10, 20)])
    promoted = foundry.task_status("sum_loop")
    assert promoted["status"] == "promoted"
    assert promoted["candidate"]["genealogy_ability_id"] == "A:GEN_EXEC_TEST"
    assert genealogy.records[-1]["program_kind"] == "loop"


def test_recursive_factorial_is_synthesized_and_bounded():
    foundry = AuroraGeneralExecutionFoundry(persist=False)
    for input_value, output_value in [(1, 1), (2, 2), (3, 6), (4, 24)]:
        foundry.observe_example("factorial", input_value, output_value)
    status = foundry.task_status("factorial")
    assert status["candidate"]["kind"] == "recursive"
    assert "factorial((n - 1))" in status["candidate"]["source_python"]
    assert foundry.execute("factorial", 6)["output"] == 720
    limited = foundry.execute("factorial", 20, limits=ExecutionLimits(recursion_depth=4))
    assert limited["executed"] is False
    assert limited["reason"] == "ExecutionBudgetExceeded"


def test_semantically_unbounded_loop_is_stopped_by_fuel():
    program = {
        "op": "BLOCK",
        "body": [
            {"op": "SET", "name": "x", "value": {"op": "CONST", "value": 0}},
            {
                "op": "WHILE",
                "condition": {"op": "CONST", "value": True},
                "body": {
                    "op": "SET",
                    "name": "x",
                    "value": {"op": "ADD", "left": {"op": "VAR", "name": "x"}, "right": {"op": "CONST", "value": 1}},
                },
            },
        ],
    }
    executor = GeneralProgramExecutor(task_id="runaway", state={}, limits=ExecutionLimits(fuel=50, wall_seconds=1.0))
    try:
        executor.execute(program, None)
    except Exception as exc:
        assert type(exc).__name__ == "ExecutionBudgetExceeded"
    else:
        raise AssertionError("runaway loop escaped the execution budget")


def test_long_lived_state_machine_persists_across_restart(tmp_path):
    foundry = AuroraGeneralExecutionFoundry(state_dir=str(tmp_path), persist=True)
    foundry.observe_transition("door", "closed", "open", "open", initial_state="closed")
    foundry.observe_transition("door", "open", "close", "closed")
    foundry.observe_transition("door", "open", "lock", "locked")
    first = foundry.step_machine("door", "front", "open")
    assert first["state"] == "open"

    restored = AuroraGeneralExecutionFoundry(state_dir=str(tmp_path), persist=True)
    second = restored.step_machine("door", "front", "lock")
    assert second["previous_state"] == "open"
    assert second["state"] == "locked"
    assert restored.machine_status("door")["instances"] == 1


def test_tool_plan_is_learned_but_requires_capability_grant():
    foundry = AuroraGeneralExecutionFoundry(persist=False)
    foundry.register_capability(
        CapabilitySpec("lookup", description="safe deterministic lookup", input_keys=("key",)),
        lambda arguments: {"alpha": 1, "beta": 2, "gamma": 3}.get(arguments["key"], -1),
    )
    demonstrations = [
        ({"name": "alpha"}, [{"tool": "lookup", "arguments": {"key": "alpha"}}]),
        ({"name": "beta"}, [{"tool": "lookup", "arguments": {"key": "beta"}}]),
        ({"name": "gamma"}, [{"tool": "lookup", "arguments": {"key": "gamma"}}]),
    ]
    for input_value, steps in demonstrations:
        foundry.observe_tool_demonstration("lookup_plan", input_value, steps)
    denied = foundry.execute_tool_plan("lookup_plan", {"name": "beta"})
    assert denied["executed"] is False
    assert denied["reason"] == "CapabilityDenied"

    foundry.grant_capability("lookup_plan", "lookup")
    allowed = foundry.execute_tool_plan("lookup_plan", {"name": "beta"})
    assert allowed["executed"] is True
    assert allowed["output"] == 2


def test_side_effect_tool_requires_explicit_grant_and_confirmation():
    foundry = AuroraGeneralExecutionFoundry(persist=False)
    foundry.register_capability(
        CapabilitySpec("write_like", side_effect_level=2, confirmation_required=True, input_keys=("value",)),
        lambda arguments: arguments["value"],
    )
    try:
        foundry.grant_capability("task", "write_like")
    except CapabilityDenied as exc:
        assert "side_effect_grant_required" in str(exc)
    else:
        raise AssertionError("side-effect capability was granted without authorization")
    foundry.grant_capability("task", "write_like", allow_side_effects=True, confirmation="approved")


def test_python_candidate_is_ast_sandboxed_and_dangerous_source_rejected():
    safe = """
def helper(n):
    if n <= 1:
        return 1
    return n * helper(n - 1)

def aurora_program(input_value, state):
    return helper(input_value)
"""
    assert validate_python_source(safe)["valid"] is True
    result = execute_python_sandbox(safe, 5, limits=ExecutionLimits(fuel=10000, wall_seconds=2.0))
    assert result["executed"] is True
    assert result["output"] == 120

    dangerous = """
import os
def aurora_program(input_value, state):
    return os.listdir('/')
"""
    validation = validate_python_source(dangerous)
    assert validation["valid"] is False
    assert validation["reason"] == "forbidden_ast_node"


def test_python_runaway_is_terminated():
    runaway = """
def aurora_program(input_value, state):
    while True:
        input_value = input_value + 1
"""
    result = execute_python_sandbox(runaway, 0, limits=ExecutionLimits(fuel=100, wall_seconds=0.25))
    assert result["executed"] is False
    assert result["reason"] in {"ExecutionBudgetExceeded", "sandbox_timeout"}


def test_state_machine_and_tool_plan_register_genealogy_after_validation(tmp_path):
    genealogy = _Genealogy()
    foundry = AuroraGeneralExecutionFoundry(state_dir=str(tmp_path), persist=True, genealogy=genealogy)
    foundry.attach_systems({"genealogy": genealogy})

    foundry.observe_transition("traffic", "red", "timer", "green", initial_state="red")
    foundry.observe_transition("traffic", "green", "timer", "yellow")
    foundry.observe_transition("traffic", "yellow", "timer", "red")
    for _ in range(4):
        current = foundry.machine_instances.get("traffic:main", {}).get("state", "red")
        foundry.step_machine("traffic", "main", "timer")
    machine = foundry.machine_status("traffic")
    assert machine["status"] == "promoted"
    assert machine["genealogy_ability_id"] == "A:GEN_EXEC_TEST"

    foundry.register_capability(
        CapabilitySpec("echo", input_keys=("value",)),
        lambda arguments: arguments["value"],
    )
    for value in ("a", "b", "c"):
        foundry.observe_tool_demonstration(
            "echo_plan",
            {"message": value},
            [{"tool": "echo", "arguments": {"value": value}}],
        )
    foundry.grant_capability("echo_plan", "echo")
    for value in ("d", "e", "f", "g"):
        foundry.observe_tool_demonstration(
            "echo_plan",
            {"message": value},
            [{"tool": "echo", "arguments": {"value": value}}],
            expected_output=value,
            validation=True,
        )
    plan = foundry.tool_plan_status("echo_plan")
    assert plan["status"] == "promoted"
    assert plan["genealogy_ability_id"] == "A:GEN_EXEC_TEST"
    assert {record["program_kind"] for record in genealogy.records} >= {"state_machine", "tool_plan"}


def test_direct_novel_ir_candidate_can_combine_state_loop_and_capability():
    foundry = AuroraGeneralExecutionFoundry(persist=False)
    foundry.register_capability(
        CapabilitySpec("double", input_keys=("value",)),
        lambda arguments: arguments["value"] * 2,
    )
    foundry.grant_capability("stateful_tool", "double")
    program = {
        "op": "BLOCK",
        "body": [
            {"op": "SET", "name": "acc", "value": {"op": "STATE_GET", "key": {"op": "CONST", "value": "acc"}, "default": {"op": "CONST", "value": 0}}},
            {"op": "FOR_EACH", "item": "item", "iterable": {"op": "INPUT"}, "body": {
                "op": "SET", "name": "acc", "value": {"op": "ADD", "left": {"op": "VAR", "name": "acc"}, "right": {
                    "op": "TOOL", "name": "double", "arguments": {"op": "MAP", "fields": {"value": {"op": "VAR", "name": "item"}}}
                }}
            }},
            {"op": "STATE_SET", "key": {"op": "CONST", "value": "acc"}, "value": {"op": "VAR", "name": "acc"}},
            {"op": "RETURN", "value": {"op": "VAR", "name": "acc"}},
        ],
    }
    accepted = foundry.submit_program_candidate("stateful_tool", program, kind="stateful_tool_program")
    assert accepted["accepted"] is True
    assert accepted["python_generated"] is False
    first = foundry.execute("stateful_tool", [1, 2])
    second = foundry.execute("stateful_tool", [3])
    assert first["output"] == 6
    assert second["output"] == 12
    roots = foundry.trace_to_roots("stateful_tool")
    assert set(roots["root_constraints"]) == {"X", "T", "N", "B", "A"}
