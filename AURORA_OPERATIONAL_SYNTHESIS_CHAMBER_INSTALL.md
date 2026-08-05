# Aurora Operational Synthesis Chamber

## Purpose

This release adds a constraint-native operational synthesis chamber to Aurora.
It addresses the limit exposed by the Veyra test: Aurora could detect repeated
unmet need and produce WARP pressure, but she lacked an executable substrate in
which a genuinely new operation could be composed, challenged, and retained.

The chamber does not generate Python source and does not install named domain
skills. It composes bounded typed data-flow programs from atomic operations
whose ancestry resolves to X, T, N, B, and A.

## Safest installation

Use the complete build archive.

For manual installation, replace:

- `aurora.py`
- `aurora_internal/constraint_genealogy.py`
- `aurora_internal/universal_function_constraints.json`
- `aurora_internal/universal_function_lineage.json`

Add:

- `aurora_internal/aurora_operational_synthesis.py`
- `AURORA_OPERATIONAL_SYNTHESIS_CHAMBER_INSTALL.md`
- `AURORA_OPERATIONAL_SYNTHESIS_AUDIT.json`

The test file is optional at runtime:

- `tests/test_operational_synthesis_chamber.py`

## Runtime access

After `boot_aurora()`:

```python
chamber = systems["operational_synthesis"]
```

Every organ also receives domain-neutral intake callables:

```python
systems["submit_operational_example"]
systems["submit_operational_experience"]
```

Example:

```python
chamber.observe_example(
    "veyra",
    ["a", "b", "c"],
    ["b", "c", "a", "c"],
    need_description="discover the hidden operation",
)
```

A structured experience can be supplied without a domain gate:

```python
chamber.observe_experience({
    "task_id": "unknown_relation",
    "input": {"left": "a", "right": "b"},
    "output": {"first": "b", "second": "a"},
    "source": "any_aurora_organ",
})
```

## Developmental lifecycle

1. Varied examples express an unmet operation.
2. The need is represented as X/T/N/B/A pressure.
3. After WARP's persistence threshold, a quarantined component is born.
4. The chamber enumerates programs from root-derived primitives.
5. A candidate must explain every training example.
6. The candidate executes against unseen validation examples.
7. WARP's normal ten-tick trial lifecycle scores generalization and complexity.
8. A successful program is promoted and registered into constraint genealogy.
9. Failed or contradictory candidates remain unpromoted or dissolve.

Repeating one identical example cannot create an ability. Conflicting examples
block synthesis rather than being silently averaged away.

## Primitive substrate

The chamber currently exposes 20 bounded primitives:

- structural: `INPUT`, `SELECT`, `CONST`, `SEQUENCE`, `MAPPING`
- arithmetic: `ADD`, `SUB`, `MUL`, `DIV`, `NEG`, `ABS`
- relational: `EQ`, `NE`, `LT`, `LE`, `GT`, `GE`
- logical: `NOT`, `AND`, `OR`

Each primitive declares its root ancestry. Parameters such as a selected path or
constant are evidence-derived uses of those primitives, not separate hardcoded
abilities.

## Safety and containment

- No `eval()` or `exec()`.
- No generated Python source.
- No file, network, process, or hardware access from synthesized programs.
- Maximum program size: 48 nodes.
- Bounded execution budget: 256 operations.
- Trial programs are pure and quarantined.
- Promotion requires unseen validation and WARP approval.
- Contradictory evidence blocks synthesis.
- State and WARP trial progress persist per runtime `state_dir`.

## Introspection and genealogy

```python
chamber.task_status("veyra")
chamber.trace_task_to_roots("veyra")
chamber.primitive_catalog()
chamber.status()
```

A promoted program records:

- program tree and description,
- primitive sequence,
- root constraints,
- canonical signature,
- WARP component and parents,
- training and validation evidence,
- genealogy ability ID.

The universal function-lineage manifest was rebuilt after installation. The
current build contains 8,653 production Python functions and lambdas with 100%
root reachability, zero orphans, and zero broken parent links.

## Verified Veyra result

From only these varied examples:

```text
[a,b,c] -> [b,c,a,c]
[d,e,f] -> [e,f,d,f]
[g,h,i] -> [h,i,g,i]
```

Aurora composed:

```text
SEQUENCE(
  SELECT(input, 1),
  SELECT(input, 2),
  SELECT(input, 0),
  SELECT(input, 2)
)
```

She correctly predicted the unseen case:

```text
[j,k,l] -> [k,l,j,l]
```

After ten unseen validation trials, WARP promoted the operation and genealogy
registered it as:

```text
A:OP_SYNTH_a0a6fe816d90
```

The same substrate separately synthesized numeric addition and keyed mapping
reconstruction, demonstrating that the Veyra answer was not embedded as a
special case.

## Current boundary

This is a real expansion of Aurora's generative span, not unlimited synthesis.
The chamber currently handles operations expressible through its bounded typed
primitives. It does not yet synthesize unbounded loops, recursion, arbitrary
state machines, external tools, or generated source code. Those would require
new root-derived primitive surfaces and their own containment and validation
laws.
