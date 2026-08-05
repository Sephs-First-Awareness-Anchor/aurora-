# Aurora Build 591: Recursive Causal Reasoning Waveform

## Purpose

This release adds **Recursive Causal Reasoning Waveform (RCRW)** to the General Execution Foundry build.

The initial external input is preserved as an immutable carrier disturbance, `W0`. Aurora then generates smaller, X/T/N/B/A-derived control wavelets that influence how the active proposition moves through her system. Their interference produces a system-level understanding, `H`. That understanding may project backward over the processing path and reconstruct the **effective interpretation** of `W0`, provided every revision is supported by referential, claim, or runtime evidence. Aurora's delivered response is emitted as `W1`, becoming causal input to the following interaction.

The release therefore keeps three separate records:

1. `raw_input`: the external event exactly as received.
2. `provisional_interpretation`: Aurora's first constraint-bearing reading.
3. `effective_interpretation`: the evidence-supported reading after recursive causal development.

The past is never rewritten. Later understanding may revise what Aurora believes the input was doing, while the original input remains preserved beside that reconstruction.

## Recommended installation

Use the complete archive. It includes the updated universal function-lineage manifests and retains the original clean `aurora_state` from the General Execution Foundry release.

## Manual installation

Replace:

- `aurora.py`
- `aurora_internal/constraint_genealogy.py`
- `aurora_internal/universal_function_lineage.json`
- `aurora_internal/universal_function_constraints.json`

Add:

- `aurora_internal/aurora_recursive_causal_reasoning_waveform.py`

Optional regression test:

- `tests/test_recursive_causal_reasoning_waveform.py`

## Runtime integration

At boot Aurora creates:

```python
systems["recursive_causal_waveform"]
```

The system is registered as a WARP-capable actuator.

During a turn:

```text
W0: raw input
  -> provisional relational form
  -> endogenous control wavelets
  -> X/T/N/B/A interference
  -> H: global understanding
  -> evidence-bounded backprojection
  -> effective relational form
  -> normal Aurora reasoning and articulation
  -> W1: delivered response
  -> next external disturbance
```

## Root-derived wavelet primitives

- `existence_admission`: X × B
- `continuity_phase_lock`: X × T × B
- `transformational_gradient`: T × N × A
- `boundary_separation`: X × N × B
- `agency_selection`: X × T × B × A
- `recursive_backprojection`: X × T × N × B × A
- `causal_emission`: X × T × N × B × A

These are not conversational intent handlers. They modulate entity admission, continuity, change pressure, boundary separation, authority, retrospective interpretation, and causal output across any domain.

## Adaptive development

If completed cycles repeatedly fail to preserve the active relation, RCRW produces a negative 15-dimensional WARP gap profile containing I-state and recursive-depth pressure. Persistent gaps create trial control wavelets. Trials are scored by actual use, response relation alignment, and improvement in global coherence. Successful wavelets may be promoted and registered in constraint genealogy through:

```python
genealogy.register_recursive_causal_waveform(...)
```

Promoted wavelets preserve:

- root constraints,
- canonical signature,
- parent operations,
- WARP component identity,
- use and success counts,
- relation-alignment gain,
- and the invariant that raw input history cannot be altered.

## Runtime queries

```python
rcrw = systems["recursive_causal_waveform"]

rcrw.status()
rcrw.latest_cycle()
rcrw.cycle(cycle_id)
rcrw.trace_to_roots(cycle_id)
```

Each cycle exposes:

- raw and provisional input,
- control wavelets,
- axis interference,
- global understanding,
- effective interpretation,
- response wave,
- receiver recurrence,
- WARP evaluation,
- and genealogy paths.

## Verification

Focused tests:

- 89 communication, reflection, introspection, synthesis, foundry, and RCRW tests passed.
- 7 universal function-lineage tests passed.
- Total: **96 focused tests passed**.

Universal function genealogy:

- 306 Python files
- 8,772 executable functions and lambdas
- 100% root reachability
- 0 orphans
- 0 missing parent links
- 0 invalid root paths

Live surface-runtime probe:

```text
Input:
What makes an invention elegant?

Aurora:
An invention becomes elegant when it retains a distinct identity,
keeps its parts and limits in a coherent relation, and continues
to hold as conditions change.
```

The live cycle produced five endogenous wavelets, a hurricane-condition score of approximately `0.9602`, relation alignment of `1.0`, preserved the raw input, and traced the cycle to all five roots.

## Honest boundary

RCRW is recursive causal reconstruction, not retrocausality. Aurora cannot change the input that occurred. She can develop a better, traceable account of what that input meant and let that understanding determine the response that becomes the next cause.
