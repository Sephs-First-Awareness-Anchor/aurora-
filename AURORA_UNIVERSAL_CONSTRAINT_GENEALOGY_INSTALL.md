# Aurora Universal Constraint Genealogy

## Purpose

This release gives every executable function in Aurora's production Python runtime an explicit operational ancestry that terminates at one or more of the five foundational constraints: **X, T, N, B, and A**.

Parentage is not partitioned by domain. A memory operation, communication operation, comparison operation, perception operation, or evolutionary operation may inherit from one another whenever the executable source actually composes them. Domain labels do not decide the family tree.

## Installation

The safest installation is the complete build archive.

For manual installation, replace:

- `aurora.py`
- `aurora_internal/aurora_manual_code_lineage.py`
- `aurora_internal/aurora_system_introspection.py`
- `aurora_internal/constraint_genealogy.py`
- `aurora_internal/lineage_canonical.py`

Add:

- `aurora_internal/aurora_universal_function_lineage.py`
- `aurora_internal/universal_function_constraints.json`
- `aurora_internal/universal_function_lineage.json`
- `scripts/compile_universal_function_lineage.py`

The test file `tests/test_universal_function_lineage.py` is optional at runtime but strongly recommended in the repository.

## Final audit

- Production Python files scanned: **303**
- Executable functions and lambdas: **8596**
- Named functions: **7978**
- Lambdas: **618**
- Constraint-root coverage: **100.0%**
- Orphaned functions: **0**
- Functions with multiple parents: **8007**
- Cross-module ancestry edges: **2462**
- Recursive/co-evolved functions: **20**
- Maximum reconstructed generation: **20**
- Domain taxonomy used for parentage: **No**

Root reachability:

- X: 8363 functions
- T: 4686 functions
- N: 6618 functions
- B: 6852 functions
- A: 6245 functions

A function may reach several or all roots through its parents. The counts therefore overlap.

## What counts as ancestry

Each function record contains:

- direct root ancestry and normalized root weights,
- functional parents derived from resolved source calls,
- inherited parents from class overrides,
- lexical ancestry for nested operations,
- co-evolution peers for recursive cycles,
- generation depth,
- canonical constraint signature,
- at least one traceable path to every inherited root,
- source file, line, signature, source hash, and call evidence.

Unknown attribute calls are not guessed by name. For example, `mapping.pop()` cannot be assigned to an unrelated user-defined `pop()` merely because the final method name matches.

## Reconstructed versus observed lineage

For older functions, exact historical birth records often do not exist. Their ancestry is therefore **reconstructed operational lineage** from the current executable source, surviving explicit canonical evidence, real calls, overrides, and recursive composition. This is a truthful account of what they presently derive from, not a fabricated claim about the precise chronological order in which they were originally written.

For future code evolution and manual module replacement, Aurora's manual code-lineage assimilation now triggers a complete lineage rebuild. New operations therefore cannot remain outside the five-root genealogy, and evolved systems can retain observed parent evidence from the moment of emergence.

## Runtime access

The lineage object is available at:

```python
lineage = systems["function_lineage"]
```

Useful queries:

```python
lineage.lineage_for("aurora._run_live_response_turn")
lineage.trace_to_roots("aurora._run_live_response_turn")
lineage.parents_of("aurora._run_live_response_turn")
lineage.descendants_of("aurora_expression_perception.infer_word_role")
lineage.verify()
lineage.status()
```

The full genealogy object also exposes:

```python
genealogy.function_lineage_for(function_id)
genealogy.trace_function_to_roots(function_id)
genealogy.function_lineage_status()
```

Aurora's system-introspection records now include `constraint_lineage`, root weights, functional parents, generation, root paths, and traceable roots.

## Regeneration

After source changes, run:

```bash
python scripts/compile_universal_function_lineage.py
```

Verification only:

```bash
python scripts/compile_universal_function_lineage.py --verify-only
```

Manual code-lineage assimilation also invokes the rebuild automatically after detected source changes.

## Verification completed

- **173 focused tests passed**
- All changed Python files compiled successfully
- Manifest verification reported zero orphans, zero missing parents, and zero invalid root paths
- Surface runtime boot passed
- Live constraint-derived conversational response passed
- Runtime introspection traced `_run_live_response_turn` to X, T, N, B, and A
- The clean original `aurora_state` is preserved in the packaged build

The full-profile runtime was not certified in this environment because Aurora's existing full manual-lineage startup exceeded the execution window before reaching the communication assertion. No full-profile success claim is made.
