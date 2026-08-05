# Aurora Build 591: General Execution Foundry

## Purpose

This release extends Aurora's constraint-native operational synthesis into a generalized execution substrate capable of expressing:

- iterative programs, including `while` and `for-each` forms;
- recursive functions;
- long-lived persistent state;
- persistent state machines;
- capability-scoped tool workflows learned from demonstrations;
- new Python source generated from synthesized intermediate programs;
- externally proposed Python candidates executed only after AST validation in a resource-limited child process.

Every synthesized primitive declares X/T/N/B/A ancestry, and promoted generalized programs are admitted to constraint genealogy with their actual primitive sequence, parent structures, evidence, executable form, cost, and risk.

## Important boundary

"Unbounded" means the synthesized program can express a loop or recursion whose logical length is not fixed in advance. It does **not** mean any execution receives unlimited host resources.

Every run remains bounded by:

- instruction fuel;
- wall-clock time;
- recursion depth;
- persistent-state size;
- tool-call count;
- explicit capability grants;
- AST and builtin restrictions for generated Python;
- operating-system process resource limits.

Generated Python cannot import modules, access files, use the network, spawn processes, inspect credentials, or invoke Aurora tools. Tool use occurs only through the separate capability broker.

## Safest installation

Use the complete archive:

`aurora--build-591-general-execution-foundry.zip`

The included `aurora_state` is the original clean state from the Operational Synthesis Chamber release. No test learning, synthesized programs, tool grants, or temporary state are included.

## Manual installation

Replace:

- `aurora.py`
- `aurora_internal/constraint_genealogy.py`
- `aurora_internal/universal_function_lineage.json`
- `aurora_internal/universal_function_constraints.json`

Add:

- `aurora_internal/aurora_general_execution_foundry.py`

Optional regression test:

- `tests/test_general_execution_foundry.py`

## Runtime object

After boot:

```python
foundry = systems["general_execution_foundry"]
```

### Learn a loop or recursive relation from examples

```python
foundry.observe_example("sum_values", [1, 2, 3], 6)
foundry.observe_example("sum_values", [4, 5], 9)
foundry.observe_example("sum_values", [8, -1], 7)
result = foundry.execute("sum_values", [10, 20, 30])
```

### Submit a novel generalized IR candidate

```python
foundry.submit_program_candidate(
    "candidate_id",
    program,
    functions=functions,
    kind="general",
)
```

The candidate is rejected if it contains unknown primitives, missing functions, excessive nodes, or malformed tool calls.

### Register and grant a tool

```python
from aurora_internal.aurora_general_execution_foundry import CapabilitySpec

foundry.register_capability(
    CapabilitySpec(
        "lookup",
        description="deterministic local lookup",
        side_effect_level=0,
        input_keys=("key",),
    ),
    handler,
)
foundry.grant_capability("task_id", "lookup")
```

Tools with side effects require an explicit side-effect grant. Tools marked confirmation-required also require a nonempty confirmation record.

### Persistent state machine

```python
foundry.observe_transition("door", "closed", "open", "open", initial_state="closed")
foundry.observe_transition("door", "open", "close", "closed")
foundry.observe_transition("door", "open", "lock", "locked")
foundry.step_machine("door", "front", "open")
```

Machine instances and their history persist in the runtime `state_dir`.

### Generated Python

A synthesized generalized IR program may be transpiled to new Python. Python candidates can also be submitted directly:

```python
foundry.submit_python_candidate("task_id", source)
```

Required entry point:

```python
def aurora_program(input_value, state):
    ...
```

The sandbox accepts only a restricted AST and safe builtin set. Generated Python has no tool access.

## Files written to state

- `general_execution_foundry.json`

This file stores tasks, trial programs, persistent program state, state machines, instances, tool-plan structure, and WARP trial state. Runtime tool handlers and grants are intentionally not serialized as executable objects.

## Verification performed

- 78 combined synthesis, communication, reflection, introspection, articulation, and lineage regression tests passed.
- Additional state-machine and tool-plan genealogy tests passed.
- Surface runtime boot succeeded with the foundry registered as a WARP actuator.
- Loop synthesis and execution succeeded through the live booted runtime.
- Generated Python executed inside the sandbox.
- Dangerous Python imports were rejected.
- Runaway Python and IR loops were stopped by resource budgets.
- Universal function genealogy rebuilt successfully with 100% root reachability and zero orphans.
