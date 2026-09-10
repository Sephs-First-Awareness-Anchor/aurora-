# Aurora Phone Occurrence Causal Trace

**Date:** 2026-09-10  
**Authors:** Sunni (Sir) Morningstar & Ceph  
**Scope:** Current `main` at `976d145` plus the Presence-barrier correction on `ceph/phone-occurrence-presence-barrier`.

## Governing question

For one real Android user occurrence, which work is a true causal dependency, which work is an independent reaction to the same occurrence, and where is execution merely sequential because of implementation history?

The goal is not to add a global scheduler. The goal is to let independent reactions coexist and then reconcile at the narrowest correct causal barrier, while keeping the same semantics when only one worker/core is available.

## 1. Actual phone entry path

The live Android path is:

```text
Flutter HomeScreen
  -> AuroraBridge.sendMessage()
  -> MethodChannel org.aurora.app/bridge
  -> MainActivity.kt
  -> AuroraService.sendMessage()
  -> Chaquopy
  -> flutter_app/android/app/src/main/python/aurora_bridge.py::handle_message()
  -> aurora.process_external_user_turn()
  -> _run_live_response_turn()
  -> _run_reasoning_pipeline()
```

`handle_message()` intentionally serializes admission to the canonical user-turn mutation path with `_lock`. That lock is retained. Concurrent human turns would mutate shared conversational state without an occurrence-commit boundary and are not the parallelism target.

Build 774 already separates **response availability** from **deep-turn completion**: `process_external_user_turn(..., on_surface_ready=...)` can externalize `resp_A` as soon as it is decided while consequence/genealogy/memory work continues in the same admitted turn.

## 2. Turn identity and present-frame boundary

`process_external_user_turn()` owns the canonical `turn_id` on Android, adopts an existing one on daemon callers, and restores the prior value in `finally`.

At that boundary it also freezes `surface_sensory_snapshot.json` into `systems["_present_frame_snapshot"]`, making visual/audio state and the incoming language part of one present occurrence rather than sampling them at unrelated later times.

It then publishes `turn_open` into the live Subsurface Presence channel before substantive reasoning.

This is a correct occurrence boundary.

## 3. The reasoning chain is causal, not a parallelization target

The canonical reasoning pipeline performs:

```text
UP:
  Information (X)
  -> Belief (T)
  -> Purpose (N)
  -> Meaning (B)
  -> Understanding (A)

DOWN:
  Understanding (A)
  -> Meaning (B)
  -> Purpose (N)
  -> [interpreted-turn barrier]
  -> Belief (T)
  -> Information (X)
  -> expression/emission
```

Each stage intentionally inherits state deposited by the preceding stage. Running these five stages as sibling tasks would erase Aurora's designed constraint genealogy by pretending derived states were independent. They should remain ordered.

The parallelism opportunities are **around** this chain: co-equal inputs that can be captured from one occurrence snapshot, independent background organs, and post-decision consequences that can run without delaying Surface once their mutation boundaries are safe.

## 4. First confirmed broken synchronization joint

`_run_reasoning_pipeline()` already contains the right conceptual barrier calls:

```python
_ingest_live_subsurface_presence(
    systems, state, turn_id=_live_turn_id,
    phase="turn_open", wait_s=0.20,
)
...
_ingest_live_subsurface_presence(
    systems, state, turn_id=_turn_id_live,
    phase="interpreted", wait_s=0.25,
)
```

`_ingest_live_subsurface_presence()` only performs the bounded wait when the in-process runtime exposes `wait_for_turn_phase`:

```python
if runtime is not None and hasattr(runtime, "wait_for_turn_phase") and wait_s > 0:
    frame = runtime.wait_for_turn_phase(...)
```

But `SubsurfacePresenceRuntime` did not implement `wait_for_turn_phase` at all.

Therefore Android's supposed phase barrier was not a slow barrier. It was structurally absent. Surface published the event, skipped the wait because `hasattr(...)` was false, and immediately read the presence-frame file. The independent Presence thread normally discovers new events on its 150ms poll. Which side won that race determined whether current-turn Subsurface state was visible to Surface at the intended point.

That is exactly the class of defect the causal-generation directive is meant to expose: behavior dependent on physical execution order rather than causal relation.

## 5. Correction in this branch

`SubsurfacePresenceRuntime` now provides the missing `wait_for_turn_phase()` contract.

The correction adds:

- `_wake_event`: an in-process fast wake signal for the already-independent Presence thread.
- `_phase_condition` + `_tick_generation`: a non-polling wait/notification barrier.
- phase proof for the two live waits Aurora actually uses:
  - `turn_open` requires same `turn_id` + `turn_open_at`.
  - `interpreted` requires same `turn_id` + `interpreted_at`.
- `_run()` notification after each completed integration tick.
- `stop()` waking the new sleep primitive so shutdown remains prompt.

Surface **never calls `tick()`**. `wait_for_turn_phase()` wakes the daemon and waits. The Presence runtime remains a separate execution lane.

The existing 150ms periodic poll remains intact as the idle/cross-process/backstop mechanism. This means the semantic architecture does not fork between Android and desktop: Android gets the in-process fast path, while file-backed process separation still works.

## 6. Regression tests added

`tests/test_presence_runtime_occurrence_barrier.py` verifies:

1. A runtime deliberately configured with a 5-second poll still integrates `turn_open` inside a 750ms bounded wait, proving wake-driven execution rather than lucky polling.
2. `interpreted_turn` reaches the same-turn interpreted barrier.
3. Presence `tick()` runs only on the independent runtime thread, never the Surface caller thread.
4. A nonexistent turn times out rather than fabricating a frame.
5. Stop interrupts the long backstop sleep.

## 7. Next occurrence-wavefront work

The trace shows two separate categories for the next pass.

### 7.1 Same-occurrence co-equal inputs

The Information/X stage currently performs several operations in one sequential body: parsing, I-State admission, SediMemory recall, waveform pre-injection, and sensory-context injection. These must be classified individually before parallel execution. Some are pure reads from the frozen occurrence, while others mutate shared fields and must remain commits. The correct shape is:

```text
frozen occurrence snapshot
  -> independent read/transform branches
  -> deterministic X-stage reconciliation
  -> existing T/N/B/A causal chain
```

No branch may read another sibling's partial commit.

### 7.2 Fresh Phase-0 duplicate-target audit

PR #224 correctly deferred crystal/facet relational-link computation until the full batch lands. However, `CrystalProcessingSystem.process_concepts()` still mutates the same `Crystal` during Pass 1 for each signal, including `usage_count`, facet strengthening/evolution, and the running `constraint_signature` update:

```python
prev = crystal.constraint_signature.get(axis, w)
crystal.constraint_signature[axis] = round(prev * 0.8 + w * 0.2, 4)
```

If two sibling signals in one occurrence can target the same concept/crystal with different axis weights, that recurrence is itself order-sensitive even though link reconciliation is deferred. This must be tested with duplicate-target permutations before any Pass-1 parallelization is attempted. If duplicate targets are impossible by upstream contract, that invariant should be asserted; if they are possible, same-target contributions need an occurrence-level fold before one crystal commit.

## 8. Architectural direction

Aurora already has multiple execution lanes: Android Surface, Presence/Scout workers, ThoughtBraid/background cognition, autonomy/sensory threads, the General Execution Foundry, and ACM constrained multiprocessing. The missing concept is not "more threads." It is a shared causal rule:

> **Independent reactions may execute whenever capacity permits, but no reaction may observe a sibling's partial commit from the same occurrence. Reconciliation happens at the earliest barrier where their joint relation becomes causally meaningful.**

On a constrained phone, the same structure may use one worker or a few threads. Under ACM hardware it may use broader organ-level execution. The causal graph stays the same; only available execution capacity changes.
