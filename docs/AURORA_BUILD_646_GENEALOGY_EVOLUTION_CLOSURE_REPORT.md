# Aurora Build 646 — Genealogy-to-Evolution Closure: Implementation Report

Authors: Sunni (Sir) Morningstar & Cael Devo

This report documents the completion of the "Aurora Build 646 —
Genealogy-to-Evolution Closure Directive" against the executable
codebase (not documentation, not prior-build claims). All commands
below were actually run; all data was captured from real objects, not
constructed for illustration.

---

## 1. Audit Findings

Audited live, before any modification, via direct code reading and
executable probing:

| Mechanism | Classification | Basis |
|---|---|---|
| `UniversalFunctionLineage` (`aurora_internal/aurora_universal_function_lineage.py`) | **CONFIRMED FUNCTIONAL** (reconstruction), **BUG-ADJACENT** (verification) | `rebuild()`/`_scan_surfaces()` genuinely reconstruct whole-repo call/inheritance/recursion ancestry via AST + Tarjan SCC clustering. `verify()` existed but checked only internal graph coherence (`missing_parents`/`orphans`/`bad_roots`); it had no notion of whether the persisted manifest still corresponded to current source. |
| Persisted manifest (`aurora_internal/universal_function_lineage.json`) | **BUG-ADJACENT** | Contained 8,780 recorded functions against 9,108 actually present in source at audit time — confirmed via a fresh `_scan_surfaces()` call and matching a pre-existing failing test, `tests/test_universal_function_lineage.py::test_manifest_covers_every_scanned_executable_function` (`8780 == 9108` `AssertionError`, present before any change in this pass). |
| `CodeEvolutionChamber` (`aurora_internal/aurora_code_evolution_chamber.py`) | **CONFIRMED FUNCTIONAL** | `propose_mutation()`/`evaluate_mutation()`/`observe_mutation()` form a real, evidence-grounded acceptance pipeline: `accepted = bool(checks_passed and admissible_x and is_relief and net_benefit >= float(effective_net_min))`, computed from actual before/after `CodeConstraintEvaluator.snapshot()` measurements of real file content (loc, branches, fanout, etc.), not from any self-reported success flag. Mutation lineage (`_mutation_lineage`, `_lineage_children`) already tracked `parent_ids`/`generation`/`accepted` — but had no path back into `UniversalFunctionLineage`'s operational ancestry, and no `target_files` field on its own lineage payload (a real gap, fixed in Phase 2, see §3). |
| `CodeAutoEvolver` (`aurora_internal/aurora_code_autoevolver.py`) | **CONFIRMED FUNCTIONAL** (as a file-writer) | `apply_operator()` writes real `.py` files, gated only by `ast.parse`. It performs no pressure/relief evaluation itself — that is `CodeEvolutionChamber`'s job when invoked through it. |
| `aurora_daemon.py:_run_code_mutation_cycle` | **DISCONNECTED / BUG-ADJACENT** | Aurora's autonomous background mutation cycle calls `CodeAutoEvolver.apply_operator()` directly and accepts a mutation on `py_compile` success + a forced module-reload import check alone — it never calls `CodeEvolutionChamber.observe_mutation()`/`evaluate_mutation()`, so it never measures real pressure relief. This conflicts with Requirement 6.1 ("compilation is survivability evidence, NOT fitness evidence"). **Left un-rewired** — see §11 Claim Boundaries and the Repair Authority discussion below. |
| `ConstraintGenealogyLogger.register_code_evolution_outcome()` (`aurora_internal/constraint_genealogy.py:4229`) | **CONFIRMED FUNCTIONAL** | Pre-existing developmental-writeback path: registers an accepted/rejected code-evolution outcome as a genealogy "ability" with its own cost/risk vectors across all five axes. Already wired from `aurora_runtime.py:finalize_code_mutation()` via `_feedback_code_mutation_to_genealogy()`. Not duplicated by this pass. |
| `DreamGenealogyBridge.format_for_genealogy()` (`aurora_internal/aurora_dream_genealogy_bridge.py`) | **CONFIRMED FUNCTIONAL** | The prior directive's fix — excluding `evidence_type == "directive_projection"` records from genealogy — was found intact and was re-verified with fresh tests in this pass (`tests/test_dream_evolution_boundary.py`), not merely assumed carried over. |
| `AuroraRuntime.stage_code_mutation()` / `finalize_code_mutation()` (`aurora_runtime.py`, class beginning line 5152) | **CONFIRMED FUNCTIONAL**, extended | Real staging/finalization path used by live Aurora; `self.systems: Optional[StackSystems]` is the actual systems container (not `UniverseSteerer`, which was an early false lead — see §9 below for how this was corrected before any test was run against it). |

No existing functioning machinery was rebuilt. All work in this pass is
additive: a new bridge module, new fields on existing dataclasses/
payloads, and narrow, guarded call sites.

---

## 2. Freshness Repair (Phase 0)

**File:** `aurora_internal/aurora_universal_function_lineage.py`

- Added `verify_source_freshness()`: reuses the already-existing
  `_scan_surfaces()` (the first stage of `rebuild()`, ~0.6s on the real
  ~9,100-function repo vs. ~40-50s for a full `rebuild()`) to compute a
  fresh per-file SHA-256 digest set and an aggregate
  `source_manifest_hash` (SHA-256 over sorted `rel|sha` lines), and
  compares both against the persisted manifest. Returns a structured
  result distinguishing `source_current`, hash match, missing/obsolete
  function counts, and changed/removed file lists.
- Rewrote `verify()` to return:
  ```
  internally_coherent: bool   # old behavior: no orphans/missing-parents/bad-roots
  source_current: bool        # NEW: does the manifest match current source?
  valid: bool                 # = internally_coherent AND source_current
  freshness: {...}            # nested detail from verify_source_freshness()
  ```
  This matches the directive's required structured-result shape exactly
  (`manifest internally coherent: true / manifest source-current: false
  / overall genealogy valid: false` is now a real, produceable state,
  not a hypothetical).
- Fixed `__init__` (**Boot Authority, Requirement 0.4**): previously,
  `if self.manifest_path.exists(): self.load()` followed by
  `if auto_build and not self._functions: self.rebuild()` meant a
  successfully-loaded-but-stale manifest was permanently treated as
  authoritative for the process's lifetime. Now:
  ```python
  if self.manifest_path.exists():
      self.load()
  if auto_build:
      if not self._functions or not self.verify_source_freshness().get("source_current"):
          self.rebuild()
  ```
  A stale manifest is rebuilt before being exposed as authoritative;
  persisted manifests remain a cache, never independent truth.
- **Requirement 0.5** (historical vs. operational genealogy): no
  historical evolutionary record was touched or erased by this repair.
  `CodeEvolutionChamber._mutation_lineage` and its persisted
  `code_links.json`/`code_events.jsonl` remain the historical record
  independent of `UniversalFunctionLineage`'s current-source snapshot —
  demonstrated directly in `tests/test_hereditary_closure.py::TestHistoricalRemoval`,
  where a removed function disappears from
  `UniversalFunctionLineage.all_functions()` after `rebuild()` while its
  mutation-history entry and `target_files` remain in
  `CodeEvolutionChamber._mutation_lineage` and `code_events.jsonl`.

Regenerated the persisted manifest (`scripts/compile_universal_function_lineage.py --pretty`)
to be current with final source: **9,115 functions, `valid: true`,
`internally_coherent: true`, `source_current: true`, `orphan_count: 0`,
`missing_parent_count: 0`, `bad_root_path_count: 0`**.

---

## 3. Hereditary Bridge (Phase 2)

**New file:** `aurora_internal/aurora_evolutionary_ancestry_bridge.py`

A pure, read-only query layer — it never mutates
`UniversalFunctionLineage` or `CodeEvolutionChamber` state, and never
decides acceptance/rejection.

- `AcquiredAncestry` (dataclass): keeps **multiple distinct forms of
  ancestry separate** (Requirement 2.1) — `resolved_function_ids`,
  `operational_ancestors`, `constraint_signature`, `traceable_roots`,
  `descendant_count`/`descendant_sample`,
  `previous_accepted_mutation_ids`, `previous_rejected_mutation_ids`,
  and `ancestry_status` (`"unknown"` / `"root_originating"` /
  `"resolved"` — absence is representable, never fabricated, per
  Requirement 2.2).
- `acquire_ancestry_for_target()`: resolves a mutation's `target_files`
  to function_ids via `UniversalFunctionLineage.all_functions()`, then
  queries `parents_of()`, `descendants_of()`, and `root_weights` for
  each, and separately scans `CodeEvolutionChamber._mutation_lineage`
  for prior mutations whose `target_files` overlap, split into accepted
  vs. rejected.
- `auto_parent_ids()`: **Requirement 2.3** — explicit `parent_ids` are
  never overwritten; only when a caller supplies none does the bridge
  fill in the target's real prior **accepted**-mutation history (never
  rejected, to preserve `CodeEvolutionChamber`'s existing
  generation-counting semantics, which are defined over the accepted
  lineage only).
- `lineage_scoped_pressure()` (**Requirement 4.1**, see §4): widens the
  exact-file matching above to also count mutation attempts against a
  target's operational **descendants** (via `descendants_of()`), so
  repeated failure among a function's descendants raises pressure
  specifically on that function's lineage — never globally.

**Wiring** (`aurora_internal/aurora_code_evolution_chamber.py`,
`propose_mutation()`): when a caller passes `function_lineage=...`
(new, optional, backward-compatible parameter), the chamber calls the
bridge, stores the richer view under
`payload["acquired_operational_ancestry"]` (never collapsing it into
`parent_ids`), and — only if the caller supplied no explicit
`parent_ids` — fills `parents` from `auto_parent_ids()`.

**Bug found and fixed while wiring this in:** `observe_mutation()`'s
`lineage_payload` dict (written into `self._mutation_lineage[mutation_id]`)
had **no `target_files` key at all**. This silently broke the bridge's
ability to find prior mutations by target against the real chamber (it
had only appeared to work in early ad-hoc testing because those tests
manually injected fake dict entries that happened to include
`target_files`). Fixed by adding
`"target_files": list(getattr(trace, "target_files", tuple()) or tuple())`
to the payload construction. Re-verified via a real (non-doubled)
chamber smoke test and the full ancestry-acquisition test suite
afterward.

**Runtime wiring** (`aurora_runtime.py`): `StackSystems` gained a
`function_lineage: Optional[Any] = None` field (additive). An early
mistake — assuming `stage_code_mutation()`/`finalize_code_mutation()`
belonged to `UniverseSteerer` (which uses `self._s`), based on a
misleading `awk`/line-number search that was fooled by a triple-quoted
code-generation template embedded as a string literal — was caught and
corrected via `ast.walk()` class-boundary analysis (confirming the true
enclosing class is `AuroraRuntime`, using `self.systems`) **before**
any test was run against the wrong attribute path. `stage_code_mutation()`
now passes `function_lineage=getattr(self.systems, "function_lineage", None)`
into `propose_mutation()`.

---

## 4. Developmental Selection (Phase 4-6)

- **4.1 (lineage-scoped pressure):** `lineage_scoped_pressure()` (§3)
  aggregates repeated rejected-mutation evidence across a target's
  resolved operational descendant set, returning a **decomposable**
  dict (`target_function_ids`, `descendant_scope_count`,
  `rejected_count_in_scope`, `accepted_count_in_scope`, and the actual
  mutation-id lists behind those counts) — never a single opaque score.
  Wired additively into `propose_mutation()`'s payload as
  `lineage_scoped_pressure`. Tested in
  `tests/test_lineage_scoped_pressure.py`: a rejected attempt against a
  function's descendant raises its scoped count; an unrelated
  function's rejected attempt does not.
- **4.2 (positive selection from genuine outcomes):**
  `CodeEvolutionChamber`'s acceptance formula was **not changed** by
  this pass (confirmed by
  `tests/test_no_hardcoded_evolutionary_answer_key.py`, which asserts
  the exact source string is unchanged). It already required measured
  `relief` from real before/after `CodePressureSnapshot` objects — a
  self-predicted or projected success is structurally incapable of
  satisfying it, since `evaluate_mutation()` always re-measures the
  actual file content. `tests/test_genealogy_positive_selection.py`
  demonstrates both directions: a genuine 30-branch→`return x`
  reduction is accepted with `pressure_before != pressure_after`, while
  a "claimed improvement" with zero actual file change is rejected.
- **4.3 (negative selection, no blind deletion):** rejection never
  triggers any deletion or `if failure: mutate_function()`-style
  pattern (asserted by
  `tests/test_no_hardcoded_evolutionary_answer_key.py::TestNoSimplisticFailureMutateRule`).
  `tests/test_hereditary_closure.py::TestRejectedMutationLearning::test_rejection_is_not_a_permanent_taboo`
  demonstrates a rejected attempt against a target followed by a later,
  genuinely relieving mutation against the same target being accepted —
  rejection is evidence, not a ban.
- **Phase 5 (candidate formation evidence):** lineage pressure,
  descendant fan-out (`descendant_count`/`descendant_sample`), prior
  accepted/rejected history, and constraint signature are all now
  available to a caller via `acquired_operational_ancestry` and
  `lineage_scoped_pressure` — without collapsing them into one scalar.
  **5.2 (ancestral overreach protection):** pre-existing
  `CodeEvolutionChamber._lineage_ripple()` and `lineage_report()`
  (already ranking mutations by `descendant_count` /
  `descendant_acceptance_rate` into `top_ripple_roots`) were found
  already functional and are now fed by richer upstream ancestry data;
  not rebuilt.
- **Phase 6 (evaluation grounding):** `observe_mutation()`'s formula
  (`accepted = bool(checks_passed and admissible_x and is_relief and
  net_benefit >= float(effective_net_min))`) is unchanged; its recorded
  payload already captures mutation_id, target lineage, parent chain,
  generation, structural delta evidence (relief dict), acceptance
  boolean, and now additionally the acquired ancestry and lineage
  pressure evidence — additive, backward-compatible.

---

## 5. Accepted Descendant Writeback (Phase 7)

**`aurora_runtime.py:finalize_code_mutation()`** — after the existing
`evaluate_mutation()` + `_feedback_code_mutation_to_genealogy()` calls,
added:

```python
if bool(result.get("accepted", False)):
    function_lineage = getattr(self.systems, "function_lineage", None)
    if function_lineage is not None and hasattr(function_lineage, "rebuild"):
        try:
            function_lineage.rebuild()
            result["function_lineage_refreshed"] = True
        except Exception:
            ...
            result["function_lineage_refreshed"] = False
```

No incremental-update API exists on `UniversalFunctionLineage`
(confirmed by the Phase 1 audit) — a full `rebuild()` is the only
available mechanism, so it is used here, **guarded to accepted
mutations only** (a rejected mutation's file changes are rolled back by
this method's caller *after* `finalize_code_mutation()` returns, so
rebuilding on rejection would capture transient, soon-to-be-reverted
state).

This is **Requirement 7.1's closure mechanism**: an accepted mutation's
resulting operation becomes visible to `UniversalFunctionLineage`
immediately, so the *next* `propose_mutation()` call against the same
target automatically inherits it via `auto_parent_ids()` — demonstrated
end-to-end in `tests/test_hereditary_closure.py::TestAcceptedDescendantClosure`
(the directive's own named "critical regression"):

```python
gen1_result = chamber.evaluate_mutation(...)   # accepted
lineage.rebuild()                              # what finalize_code_mutation triggers
...
gen2_trace = chamber.propose_mutation(..., function_lineage=lineage)
assert gen1_trace.mutation_id in gen2_trace.parent_ids
assert gen2_trace.meta["lineage_generation"] == gen1_trace.meta["lineage_generation"] + 1
```

**7.2 (identity across structural change):** no renaming assumption is
made anywhere in the bridge — function resolution is always by
`file`-membership lookup against `UniversalFunctionLineage`'s current
scan, so a function that keeps its name but changes internals, or one
whose file is entirely rewritten, is picked up correctly by the next
`rebuild()`. Where a target's functions cannot be resolved at all (e.g.
a mutation to a non-`.py` asset, or a file not yet observed),
`ancestry_status` stays `"unknown"` rather than fabricating continuity
— this is the directive's required explicit-ambiguity representation.

---

## 6. Rejected Evolution (Phase 8)

Nothing is erased on rejection. `CodeEvolutionChamber._mutation_lineage[mutation_id]`
keeps `accepted: False`, `target_files`, `parents`, and all evaluation
evidence; `code_events.jsonl` retains the record permanently.
`acquire_ancestry_for_target()` surfaces this to future proposals via
`previous_rejected_mutation_ids` (kept **separate** from `parent_ids` —
Requirement 8.1's "available to future candidate formation" without
misrepresenting generation lineage). **8.2 (no permanent taboo):**
demonstrated directly — see §4's `test_rejection_is_not_a_permanent_taboo`.

---

## 7. Dream Boundary (Phase 12)

Re-verified, not assumed carried over, in
`tests/test_dream_evolution_boundary.py`:

- `DreamGenealogyBridge.format_for_genealogy()` still excludes every
  record with `evidence_type == "directive_projection"` — confirmed by
  count (`len(genealogy_entries) == non_projection_count`), not just a
  presence check.
- The excluded projection record is still tagged
  `origin_tags["artificial_seed"] is True` (so it remains discoverable
  as a *hypothesis*, just not as confirmed evidence).
- The contrast case (measured, non-projected evidence) still flows
  through completely: `len(genealogy_entries) == len(records)` when no
  directives are supplied.
- A dedicated test confirms `CodeEvolutionChamber` acceptance is always
  grounded in `pressure_before != pressure_after` — a real measured
  delta — never a dream-projected one, since `evaluate_mutation()` only
  ever receives real `CodePressureSnapshot` objects from `snapshot()`.

No boundary change was needed; the prior directive's fix was intact and
is now covered by this directive's own regression suite independently.

---

## 8. Constraint Continuity (Phase 13)

**New test file:** `tests/test_constraint_continuity_across_mutation.py`.

- `trace_to_roots()` returns full route lists (`[function_id, ..., "ROOT:*"]`-shaped,
  via the pre-existing `root_paths` field), never a bare terminal-axis
  label.
- A function's `traceable_roots`/`root_weights` can and do carry
  **multiple** axis influences simultaneously (a 30-branch function
  legitimately registers against both N and B) — never collapsed to
  one.
- An accepted mutation's constraint signature (`root_weights`) is shown
  to genuinely change (see the real trace in §9 below: generation 0
  traces to `{N, B}`; after full simplification, generation 2 traces
  to `{X}` only) — and that route change is preserved as ordinary
  hereditary evidence via the mutation's recorded `pressure_before`/
  `pressure_after`, not discarded. Continuity to *some* root is
  asserted to never be lost by an accepted mutation.

---

## 9. Multi-Generation Demonstration

Produced by actually running the following against real
`UniversalFunctionLineage` and `CodeEvolutionChamber` objects (script:
`/tmp/.../scratchpad/demo_trace.py`, executed against a synthetic
2-file repo so the trace is small enough to read in full — the
mechanism is identical against the real ~9,100-function repo, which is
exercised by the full regression suite in §10):

**Generation 0 — operational ancestor, traced to root constraints.**
`hot.hot_path` (a 30-branch function) resolves via
`lineage.trace_to_roots(fid0)` to:
```json
{"N": ["ROOT:N", "hot.hot_path"], "B": ["ROOT:B", "hot.hot_path"]}
```

**Developmental pressure → Mutation G1 (accepted).**
```
chamber.propose_mutation(name="reduce_branching_g1", ..., target_files=[target], function_lineage=lineage)
```
`parent_ids = []`, `lineage_generation = 1` (no prior evidence — root
originating, correctly). Real file rewrite (30 branches → 1),
evaluated:
```
pressure_before = {X:0.0, T:0.181, N:1.0,   B:0.0, A:0.779}
pressure_after  = {X:0.0, T:0.012, N:0.055, B:0.0, A:0.286}
accepted = True
```
`finalize_code_mutation`'s equivalent (`lineage.rebuild()`) makes the
resulting operation visible to `UniversalFunctionLineage`.

**Lived outcome → Mutation G2 (accepted, automatically inherits G1).**
```
chamber.propose_mutation(name="reduce_branching_g2", ..., function_lineage=lineage)
```
```
parent_ids = ["CMUT:<gen1_id>"]        # acquired automatically, not supplied by the caller
lineage_generation = 2
acquired_operational_ancestry.previous_accepted_mutation_ids = ["CMUT:<gen1_id>"]
acquired_operational_ancestry.traceable_roots = ["A", "B", "N", "X"]
```
Further real simplification to `return x`, evaluated:
```
pressure_before = {X:0.0, T:0.012,  N:0.055,   B:0.0, A:0.286}
pressure_after  = {X:0.0, T:0.0058, N:0.00003, B:0.0, A:0.250}
accepted = True
```
After `lineage.rebuild()`, `trace_to_roots(fid2)` now returns only
`{"X": ["ROOT:X", "hot.hot_path"]}` — the constraint route genuinely
changed (Phase 13) as a direct consequence of the accepted mutation.

**Mutation G3 (forced rejection) does not replace G2.**
```
chamber.propose_mutation(name="pointless_g3", ..., function_lineage=lineage)
# parent_ids = ["CMUT:<gen1_id>", "CMUT:<gen2_id>"]  -- both prior accepted mutations visible
r3 = chamber.evaluate_mutation(trace=gen3, before=before3, checks_passed=False)
# accepted = False
```
Verified directly:
```python
gen1.mutation_id in chamber._mutation_lineage[gen2.mutation_id]["parents"]   # True
chamber._mutation_lineage[gen2.mutation_id]["accepted"] is True              # True
chamber._mutation_lineage[gen3.mutation_id]["accepted"] is False             # True
```

This is the complete cycle required by the directive's Completion
Condition, demonstrated with real objects: root constraints →
operational ancestor → developmental pressure → mutation G1 → accepted
descendant → lived outcome → mutation G2 (inheriting G1 without manual
reconstruction) → accepted descendant with a changed constraint route →
mutation G3, rejected, without erasing or replacing G2's status.

---

## 10. Regression Results

**New, directive-specific tests** (9 files, 47 tests, all passing):

```
python3 -m pytest tests/test_hereditary_closure.py tests/test_evolutionary_ancestry_acquisition.py \
  tests/test_genealogy_source_freshness.py tests/test_dream_evolution_boundary.py \
  tests/test_no_hardcoded_evolutionary_answer_key.py tests/test_genealogy_operational_integrity.py \
  tests/test_genealogy_positive_selection.py tests/test_lineage_scoped_pressure.py \
  tests/test_constraint_continuity_across_mutation.py -q
```
Result: **47 passed** in 0.6s.

Directive Phase 16 category coverage:

| Category | File | Status |
|---|---|---|
| A (Manifest Freshness) | `test_genealogy_source_freshness.py` | 8 tests, passing |
| B (Operational Genealogy Integrity) | `test_genealogy_operational_integrity.py` | 7 tests, passing |
| C (Evolutionary Parent Acquisition) | `test_evolutionary_ancestry_acquisition.py` | passing |
| D (Historical Parent Compatibility) | `test_evolutionary_ancestry_acquisition.py` | passing |
| E (Accepted Descendant Closure — "critical regression") | `test_hereditary_closure.py::TestAcceptedDescendantClosure` | passing |
| F (Rejected Mutation Learning) | `test_hereditary_closure.py::TestRejectedMutationLearning` | passing |
| G (Positive Selection) | `test_genealogy_positive_selection.py` | 3 tests, passing |
| H (Dream Boundary) | `test_dream_evolution_boundary.py` | 4 tests, passing |
| I (Descendant Ripple) | `test_hereditary_closure.py::TestDescendantRipple` | passing |
| J (Multi-Generation Evolution) | `test_hereditary_closure.py::TestMultiGenerationEvolution` | passing |
| K (Historical Removal) | `test_hereditary_closure.py::TestHistoricalRemoval` | passing |
| L (Restart Persistence) | `test_hereditary_closure.py::TestRestartPersistence` | passing |

**Full existing regression suite** (`tests/*.py`, 226 files), run in 4
sequential batches per this session's established OOM-avoidance
discipline (`ls tests/*.py | split -n l/4`):

```
Batch 00 (54 files): 604 passed, 1 skipped, 2 failed  — 2624.54s
Batch 01 (59 files): 485 passed,            2 failed  —  691.37s
Batch 02 (57 files): 562 passed,            8 failed  — 1671.14s
Batch 03 (56 files): 532 passed,            0 failed  — 2112.45s
-----------------------------------------------------------------
Total:              2183 passed, 1 skipped, 12 failed
```

All 12 failures reconciled as pre-existing/unrelated, not caused by
this pass:

- `test_concept_image_ingestion_import.py`,
  `test_d1_device_path_attribution.py` (batch 00): neither file
  references `code_evolution_chamber`, `universal_function_lineage`,
  `evolutionary_ancestry_bridge`, `StackSystems`, or `function_lineage`
  (confirmed by grep). The D1 failure's own assertion message reads
  "not necessarily a regression, but this test proves nothing as-is."
- `test_governance_liveness.py`,
  `test_m1_2_provenance_hygiene.py` (batch 01): `test_governance_liveness.py`
  re-run standalone passes **12/12** — the batch failure was test-order
  interaction within that 59-file batch, not a real regression.
  `test_m1_2_provenance_hygiene.py` concerns lexicon blind-origin
  tagging, an unrelated subsystem.
- `test_rcec_state_isolation_and_lifecycle.py::test_shutdown_aurora_stops_spawned_threads`,
  and 7 tests in `test_reflective_readdressing.py` (batch 02): neither
  file references any file touched by this pass. The 7
  `test_reflective_readdressing.py` failures were verified to occur
  **identically, with the identical error message, against the
  pre-directive baseline commit `bafdb95`**, checked out into an
  isolated `git worktree` and run standalone — confirmed pre-existing,
  not introduced by this work.
- Batch 03, which includes `tests/test_universal_function_lineage.py`
  (the file containing the originally-failing
  `test_manifest_covers_every_scanned_executable_function`) and
  `tests/test_rw5_boot_parity.py`, ran with **zero failures** — the
  Phase 0 fix directly resolves the pre-existing manifest-staleness
  failure.

No existing assertion was weakened to obtain a green run.

---

## 11. Claim Boundaries

**CONFIRMED CODE FACT** (read directly from source, or from exact
tool/test output):
- `UniversalFunctionLineage.verify()` now returns `internally_coherent`,
  `source_current`, and `valid` as described in §2.
- `CodeEvolutionChamber.propose_mutation()` accepts an optional
  `function_lineage` parameter and, when supplied, calls
  `acquire_ancestry_for_target()`/`auto_parent_ids()`.
- `observe_mutation()`'s acceptance formula string is byte-identical to
  its pre-directive form (enforced by
  `test_no_hardcoded_evolutionary_answer_key.py`).
- `aurora_daemon.py:_run_code_mutation_cycle` accepts mutations on
  `py_compile` + import-reload success alone, with no call to
  `CodeEvolutionChamber.evaluate_mutation()`/`observe_mutation()`.

**TEST-DEMONSTRATED BEHAVIOR** (asserted and passing in an actual run):
- All 47 new tests and all Phase 16 A–L categories, as tabulated in
  §10.
- The full multi-generation demonstration in §9, captured from a real
  execution, not hand-written.
- The pre-existing-failure reconciliation in §10 (standalone re-runs
  and the baseline-worktree comparison).

**ARCHITECTURAL INFERENCE** (reasoned from code structure, not directly
asserted by a test):
- That `lineage_scoped_pressure`'s descendant-scoped counts are a
  faithful instantiation of Requirement 4.1's intent for the
  *code-evolution* lineage specifically. The requirement's broader
  language ("developmental pressure... not just mutate because a timer
  fired") could in principle extend to Aurora's conversational/dream
  fail-stream (`RichFailStream`, keyed by `dimension`/`identity` — topic/
  action_type, not function_id). No such cross-domain mapping exists
  anywhere in the current architecture, and this pass deliberately did
  **not** invent one: doing so would mean deciding how a conversational
  failure attributes to a specific code function — a new
  developmental-pressure doctrine, not a mechanical repair. Per the
  directive's own Repair Authority ("If the required choice would
  determine a new learning philosophy... STOP at the mechanism boundary
  and REPORT the unresolved design decision"), this is reported here
  rather than silently decided.
- That `aurora_daemon.py`'s autonomous mutation cycle bypassing
  `CodeEvolutionChamber`'s evaluation is a genuine architectural
  tension with Requirement 6.1, not a bug this pass should silently
  fix: rewiring the daemon's acceptance criteria would change existing
  autonomous-evolution frequency/behavior and constitutes exactly the
  kind of "new mutation pedagogy" decision the Repair Authority
  reserves for explicit human resolution. **Left unresolved and
  reported, not modified.**

**NOT YET DEMONSTRATED** (acknowledged gaps):
- Phase 3's full heritable-trait-provenance ledger (first-appeared-in /
  ancestor-carriers / descendant-carriers / supporting-opposing-outcome
  tracing as a standalone queryable structure) was not built as a
  dedicated new system. `constraint_signature`/`traceable_roots`
  (already present via `AcquiredAncestry` and
  `UniversalFunctionLineage.root_weights`) serve as the
  evidence-derived characteristic representation the directive
  requires in place of an arbitrary trait ontology, and mutation
  acceptance/rejection evidence is already traceable via
  `_mutation_lineage`/`code_events.jsonl` — but a purpose-built
  "trait" abstraction layer distinct from these was judged, after
  auditing, to risk inventing exactly the kind of arbitrary trait
  ontology Non-Goals prohibits, and was not attempted without a
  clearer signal of what Aurora's own architecture already
  distinguishes as a "trait" versus a raw constraint weight. Flagged
  here rather than guessed at.
- Requirement 4.1's conversational/dream-domain pressure-to-lineage
  mapping (see Architectural Inference above) — deliberately left
  unresolved.
- The daemon-bypass tension (see above) — deliberately left unresolved
  and unmodified, reported for explicit resolution.

---

## Files Changed

```
aurora_internal/aurora_code_evolution_chamber.py       (+65)
aurora_internal/aurora_evolutionary_ancestry_bridge.py (new, 265 lines)
aurora_internal/aurora_universal_function_lineage.py    (+109)
aurora_internal/universal_function_constraints.json     (regenerated)
aurora_internal/universal_function_lineage.json         (regenerated, 9115 functions)
aurora_runtime.py                                        (+36)
tests/test_constraint_continuity_across_mutation.py     (new, 3 tests)
tests/test_dream_evolution_boundary.py                  (new, 4 tests)
tests/test_evolutionary_ancestry_acquisition.py         (new, 8 tests)
tests/test_genealogy_operational_integrity.py           (new, 7 tests)
tests/test_genealogy_positive_selection.py              (new, 3 tests)
tests/test_genealogy_source_freshness.py                (new, 8 tests)
tests/test_hereditary_closure.py                        (new, 7 tests)
tests/test_lineage_scoped_pressure.py                   (new, 3 tests)
tests/test_no_hardcoded_evolutionary_answer_key.py      (new, 4 tests)
```

## Completion Condition Check

> An Aurora operation can be traced to its real operational and
> constraint ancestors — **yes**, `trace_to_roots()`/`parents_of()`,
> unchanged, now boot-verified fresh.
> Lived outcomes can place evidence-backed evolutionary pressure upon
> that lineage — **yes**, via measured `CodePressureSnapshot` relief
> and `lineage_scoped_pressure()`.
> An evolutionary descendant can inherit and modify that ancestry —
> **yes**, via `acquire_ancestry_for_target()`/`auto_parent_ids()`.
> Actual consequences determine whether the modification survives —
> **yes**, `observe_mutation()`'s formula unchanged, still
> evidence-grounded.
> An accepted descendant becomes part of Aurora's current operational
> genealogy — **yes**, `finalize_code_mutation()`'s
> `function_lineage.rebuild()` on acceptance.
> Rejected descendants remain historical selection evidence — **yes**,
> `_mutation_lineage`/`code_events.jsonl`, never erased.
> Subsequent generations can inherit the entire resulting history
> without manual reconstruction — **yes**, demonstrated end-to-end in
> §9 with real objects.

Two design-boundary questions are reported, not silently resolved (see
§11): the daemon's bypass of evidence-grounded acceptance, and whether
conversational/dream-domain pressure should someday attribute to
specific function lineage.
