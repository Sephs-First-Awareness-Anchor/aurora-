# Aurora Build 648 — Evolutionary Infrastructure Closure and Developmental Reachability: Implementation Report

Authors: Sunni (Sir) Morningstar & Cael Devo

This report documents the "Aurora Build 648 Evolutionary Infrastructure
Closure and Developmental Reachability Directive." Its purpose was not
to finish Aurora's development or to install a dimensional-pressure
architecture, but to repair confirmed infrastructure gaps that
prevented Aurora's existing genealogy, pressure evidence, and
evolutionary machinery from forming a trustworthy developmental
experiment. Every claim below distinguishes what was directly read
from source, what a real test run demonstrated, and what remains an
open architectural question.

---

## 1. Confirmed Repairs

### Phase 0 — Runtime Genealogy Connection

**Two defects, both directly blocking, both fixed:**

1. `boot_stack()` (`aurora_runtime.py`) never constructed a
   `UniversalFunctionLineage` or set `systems.function_lineage` at all.
   `AuroraRuntime.stage_code_mutation()`'s existing
   `getattr(self.systems, "function_lineage", None)` read always saw
   `None` in production under this boot path. Fixed by adding a
   `UniversalFunctionLineage` construction step to `boot_stack()`,
   reusing the exact same construction `aurora.py`'s separate
   `boot_aurora()` path already uses (`repo_root=_HERE, auto_build=True,
   include_lambdas=True, persist=True`) — no second genealogy
   implementation was created. `auto_build=True` preserves the Build
   646 source-freshness repair: a stale persisted manifest is rebuilt
   before being exposed as authoritative.

2. **A second, more severe defect found while verifying Phase 0's own
   premise before touching it**, per the directive's own instruction to
   verify each confirmed fact at its call site: `CodeEvolutionChamber`
   at module scope in `aurora_runtime.py` was imported from a module
   name — `aurora_code_evolution_stack` — that **does not exist
   anywhere in this repository**. `_soft()` silently returned `{}`, so
   `CodeEvolutionChamber` (and `CodeMutationTrace`,
   `CodePressureSnapshot`, etc.) all resolved to `None` at import time.
   Confirmed directly: a real `AuroraRuntime().boot()` produced
   `runtime.code_chamber is None` even though `self._code_enabled` was
   `True` — the guard `if self._code_enabled and CodeEvolutionChamber is
   not None:` was always `False`. **The entire runtime code-mutation
   transaction path (`stage_code_mutation()`/`finalize_code_mutation()`)
   was unreachable in production**, regardless of the function_lineage
   gap above. `CodeAutoEvolver`'s correctly-pathed sibling import
   (`aurora_internal.aurora_code_autoevolver`) made clear this was a
   simple wrong-module-name bug, not an intentional soft-dependency —
   fixed by pointing the import at the real module,
   `aurora_internal.aurora_code_evolution_chamber`.

Confirmed via a real boot after both fixes:
`runtime.systems.function_lineage` is a live object,
`runtime.systems.function_lineage.verify()["source_current"] is True`,
and `runtime.code_chamber is not None`.

### Phase 1 — One Authoritative Autonomous Evolution Transaction

Confirmed: `aurora_daemon.py::_run_code_mutation_cycle()` called
`CodeAutoEvolver.apply_operator()` directly and retained a mutation
after compile + import-reload + QAO surface-integrity checks alone,
never calling `CodeEvolutionChamber.evaluate_mutation()` — compilation
and import success were being treated as fitness evidence.

Repaired by inserting the real, unduplicated
`CodeEvolutionChamber.propose_mutation()` /
`evaluate_mutation()` transaction after all three viability gates pass
and before the mutation is treated as final:
- A non-mutating plan (`CodeAutoEvolver.plan_operator()`, new — see
  Phase 4) is taken before `apply_operator()` runs, so the before-
  snapshot covers the operator's real anticipated scope.
- On rejection (measured relief insufficient): the mutation is rolled
  back via the existing `backups` mechanism — the daemon no longer
  silently keeps a compiled-but-unfit change.
- On acceptance: `function_lineage.rebuild()` is called, mirroring
  `AuroraRuntime.finalize_code_mutation()`'s existing Build 646
  Requirement 7.1 behavior, so the daemon's own accepted mutations
  become real operational genealogy immediately.
- The chamber is cached on `systems["code_chamber"]`, constructed
  against the same `repo_root`/default `output_dir` convention
  `AuroraRuntime`'s own chamber uses, so both share one persisted
  `code_links.json`/`code_events.jsonl` history rather than diverging.

The daemon's acceptance formula was not duplicated — it calls the same
`CodeEvolutionChamber` method every other caller in this codebase now
uses.

### Phase 2 — Restore Hereditary Mutation State Across Restart

Confirmed by direct executable probing (matching the directive's own
described consequence exactly): a fresh `CodeEvolutionChamber`
constructed against an output directory containing a real, persisted,
accepted generation-one mutation started with `_mutation_lineage = {}`
and `_lineage_children` empty — a generation-two proposal against the
same target with no explicit parent IDs saw no accepted ancestor at
all, even though `flush_files()` had genuinely persisted it.

Repaired by adding `_restore_persisted_state()`, called at the end of
`CodeEvolutionChamber.__init__()`: reads `code_links.json` (if present)
and repopulates `_mutation_lineage`, `_lineage_children`, `links`,
`_pair_counts`/`_pair_stats`, `_operator_gradients`, and the scalar
counters (`tick_count`, `accepted_count`, `rejected_count`,
`links_promoted`) from exactly what was persisted. Malformed JSON
aborts the restore cleanly (`restore_report["loaded"] = False`,
`_mutation_lineage` stays empty rather than guessing); a malformed
*individual* record inside an otherwise-valid file is skipped and
counted, not fabricated or allowed to abort the whole restore — the
directive's "represent the ambiguity, preserve what can be recovered"
requirement, applied literally. No ancestry is reconstructed by
inference — only what was actually written is loaded, and restoration
never itself grants or revokes accepted/rejected status: that remains
exactly what `observe_mutation()` recorded at persistence time.

### Phase 3 — Operation-Level Evolutionary Addressing

Confirmed: `CodeMutationTrace` identified scope only through
`target_files`; `functions_in_files()` + `acquire_ancestry_for_target()`
always expanded a target file into *every* function
`UniversalFunctionLineage` found there, then averaged their
`root_weights` into one `constraint_signature` — coarse when a file
holds many independently meaningful operations.

Repaired additively:
- `AcquiredAncestry` gained an explicit `ancestry_scope` field
  (`"exact"` | `"file_level_fallback"`) — never silently implied.
- `acquire_ancestry_for_target()` gained an optional
  `exact_function_ids` parameter: real `UniversalFunctionLineage`
  function IDs a caller already knows are affected. When supplied and
  resolvable, ancestry (operational ancestors, constraint signature,
  descendants, traceable roots) is computed over exactly those
  functions, never the whole file. An unresolvable ID is dropped, not
  fabricated into ancestry. No function-name matching or
  operation-descriptor-to-function-id mapping is performed anywhere —
  no operational-homology formula was invented.
- `CodeEvolutionChamber.propose_mutation()` gained matching
  `exact_function_ids` and `requested_operation_ids` parameters.
  `requested_operation_ids` records opaque operation-descriptor
  `op_id`/`op_chain` strings (from `aurora_state/operation_descriptors.json`)
  purely as attached evidence — this module never maps them onto
  function IDs.
- Every proposal's payload now records `requested_target_files`,
  `requested_operation_ids`, `exact_function_ids`, and
  `mutation_scope_kind` (`"exact"` | `"exact_unresolved"` |
  `"file_level_fallback"`) regardless of whether `function_lineage` was
  even supplied — file-level scope remains a fully-supported, always-
  explicit fallback, never removed.

### Phase 4 — Mutation Planning and Actual Fitness Scope

Confirmed: `code_autoevolve_once()` snapshotted "before" over only the
caller-supplied `target_files`, then `evaluate_mutation()`'s "after"
snapshot also used the ORIGINAL `target_files` (via `trace.target_files`)
— even though `apply_operator()`'s real `changed_files` (particularly
for `native_surface_projection`, whose real update set is derived from
operation descriptors) can diverge from what was originally requested.
A mutation could receive fitness credit for changing files that were
never measured.

Repaired:
- `CodeAutoEvolver.plan_operator()` (new): a pure, non-mutating preview
  of the files `apply_operator()` would write, reusing the SAME
  `_build_update_plan()` `apply_operator()` itself already calls first
  — not a second planning implementation.
- `code_autoevolve_once()` now calls `plan_operator()` before staging,
  stages against `plan_scope = requested_targets ∪ planned_files`, and
  after `apply_operator()` runs, checks `changed_files` against
  `plan_scope`:
  - If every changed file was inside the plan: `finalize_code_mutation()`
    is called with a new `actual_target_files` parameter, which
    reconciles `trace.target_files` (via `dataclasses.replace()`, since
    `CodeMutationTrace` is frozen) to the real changed set before
    `evaluate_mutation()` runs — fitness now measures what actually
    changed, not merely what was requested.
  - If any changed file escaped the plan: the mutation is rolled back
    immediately and `finalize_code_mutation()` is called with
    `checks_passed=False` (through the same evidence-grounded path,
    not a second formula) — rejected because valid before/after
    evidence was never available for the escaped file, exactly per the
    directive's stated fallback. No pre-change snapshot is ever
    fabricated after the fact.
- `finalize_code_mutation()`'s existing `auto_ok` compile-check now also
  benefits: it runs over the reconciled (real) target set.

### Phase 5 — Contextual Relatives Are Evidence, Not Automatic Propagation

Confirmed by direct regression: `UniversalFunctionLineage` already keys
functions by module-qualified identity, never bare name — this phase
added no new machinery, only regression protection that an accepted
mutation to one same-named function never touches another, and that a
REAL existing call relationship between two functions (one calling the
other) remains visible as evidence without ever causing the caller's
mutation to write to the callee's file.

### Phase 6 — Pressure Experience Continuity

Confirmed: `PressureExperienceLedger._LOG_PATH` was a hardcoded class
attribute (`"aurora_state/pressure_experiences.jsonl"`, always
CWD-relative, never state-dir-aware), and `__init__` always started
`_buffer = []` with no rehydration — a fresh construction lost all
prior causal history, including exactly the same-action/different-
outcome conditionality `outcome_variance()`'s own docstring names as
the signal this ledger exists to preserve.

Repaired: `__init__` now accepts an optional `state_dir`, falling back
to `aurora_internal.aurora_state_context.get_active_state_dir()` when
none is supplied, and only then to the literal `"aurora_state"` — the
exact default every existing `PressureExperienceLedger.get()` call site
already relies on, preserved. A new `_rehydrate_from_persisted_log()`
restores a bounded (last `_MAX_ENTRIES=500`, matching the existing
trim threshold) history from the persisted JSONL on construction, with
per-line malformed-entry tolerance (skip and continue, never abort).
No pressure semantics were changed — `outcome_variance()`/
`conditioning_signal()`'s logic is untouched; only the buffer's
starting contents changed.

---

## 2. Tests Demonstrating Each Repair

28 new tests across 8 files, all passing:

| File | Tests | Phase |
|---|---|---|
| `test_runtime_lineage_connection.py` | 1 (real boot) | 0 |
| `test_daemon_evidence_grounded_mutation.py` | 2 | 1 |
| `test_code_evolution_restart_heredity.py` | 4 | 2 |
| `test_operation_level_mutation_identity.py` | 6 | 3 |
| `test_native_surface_projection_scope_reconciliation.py` | 2 (real boot ×2) | 4 |
| `test_same_name_cross_module_independence.py` | 3 | 5 |
| `test_pressure_ledger_restart_continuity.py` | 5 | 6 |
| `test_developmental_reachability_canaries.py` | 5 | 8 |

```
python3 -m pytest tests/test_runtime_lineage_connection.py \
  tests/test_daemon_evidence_grounded_mutation.py tests/test_code_evolution_restart_heredity.py \
  tests/test_operation_level_mutation_identity.py tests/test_native_surface_projection_scope_reconciliation.py \
  tests/test_same_name_cross_module_independence.py tests/test_pressure_ledger_restart_continuity.py \
  tests/test_developmental_reachability_canaries.py -q
```
Result: **28 passed** (three of these involve a real `AuroraRuntime.boot()`,
costing 2-5 minutes each; the rest run in under two seconds combined).

Combined with the 47 pre-existing genealogy-to-evolution regressions
(unmodified, still passing):
```
python3 -m pytest tests/test_hereditary_closure.py tests/test_evolutionary_ancestry_acquisition.py \
  tests/test_genealogy_source_freshness.py tests/test_dream_evolution_boundary.py \
  tests/test_no_hardcoded_evolutionary_answer_key.py tests/test_genealogy_operational_integrity.py \
  tests/test_genealogy_positive_selection.py tests/test_lineage_scoped_pressure.py \
  tests/test_constraint_continuity_across_mutation.py [+ the 8 files above, minus boot tests] -q
```
Result: **72 passed** in ~1.1s (fast subset; boot-based tests verified
separately above).

---

## 3. Pre-Existing Machinery Preserved

- `CodeEvolutionChamber.observe_mutation()`'s acceptance formula
  (`accepted = bool(checks_passed and admissible_x and is_relief and
  net_benefit >= float(effective_net_min))`) — byte-identical, not
  duplicated anywhere.
- `UniversalFunctionLineage`'s reconstruction (`_scan_surfaces()`/
  `rebuild()`), source-freshness verification (`verify()`,
  `verify_source_freshness()`), and query surface (`trace_to_roots()`,
  `parents_of()`, `descendants_of()`) — all from Build 646, untouched.
- `ConstraintGenealogyLogger.register_code_evolution_outcome()` and its
  wiring from `finalize_code_mutation()` via
  `_feedback_code_mutation_to_genealogy()`.
- `aurora_genealogy_environment.py`'s `derive_environment_signature()`/
  `EnvironmentSignature`/`logger_from_links()` — used read-only by
  Canaries A-C, never modified.
- `PressureExperienceLedger.outcome_variance()`/`conditioning_signal()`'s
  logic — untouched; only continuity of their input buffer changed.

---

## 4. Developmental Reachability Observations (Phase 8 Canaries)

All five canaries are observational: none installs the developer-
proposed dimensional-pressure solution, and Canary E verifies none of
Canaries A-D names it as an expected outcome.

- **Canary A (Distinct Representation Preservation):** two genealogies
  with an identical aggregate axis histogram (X, T, N each appearing
  once) but opposite recursive order produce identical
  `axis_distribution` but different `structural_hash` and `provenance`
  — Aurora's existing genealogy already distinguishes structurally
  distinct histories that look identical in aggregate.
- **Canary B (Representation-Specific Consequence History):** using
  the two REAL `structural_hash` values from Canary A as
  `PressureExperienceLedger` anchors, one accumulates a genuinely
  conditional (same-action, split-outcome) history and the other a
  consistent one, independently — Aurora already has a substrate
  capable of preserving "these superficially similar things behaved
  differently," without this test prescribing what that should mean.
- **Canary C (Flattening Boundary):** traced a real function's exact
  identity (`UniversalFunctionLineage.lineage_for(fid)["root_weights"]`,
  addressed by its own `function_id`) through this directive's own
  Phase 3 ancestry bridge. The **last point** exact identity remains
  available is `acquire_ancestry_for_target(..., exact_function_ids=[fid])`'s
  `constraint_signature` (identical to the function's own weights). The
  **first point** it is reduced to an aggregate is the file-level
  fallback path (`acquire_ancestry_for_target()` with no
  `exact_function_ids`), which averages every function sharing a file
  together — the boundary this pass's own Phase 3 work makes possible
  to bypass, when a caller has the exact ID.
- **Canary D (Evolutionary Reachability):** two identically-shaped
  functions in one file, one with real, repeated rejected-mutation
  history (a genuine no-op rejection, not fabricated). Findings, using
  the directive's own outcome classes:
  - **Class 3 reached** for ancestry: `exact_function_ids` lets
    existing machinery address the specific function's operational
    ancestry precisely, using only already-available lineage data.
  - **Class 2 finding, reported not silently repaired**: the
    prior-mutation-history match (`previous_rejected_mutation_ids`) is
    keyed by `target_files` overlap only, *never* by
    `exact_function_ids` — even when the live query is exact-scoped,
    and even though the original rejection was itself only ever
    file-level-scoped (it never claimed to concern one function
    specifically). A query about either twin function currently
    inherits the other's unrelated historical rejection. This is a
    genuine current limitation of mutation-history granularity, not a
    detection or selection failure — repairing it would require
    deciding what "this historical record concerned exactly function
    X" should mean for every mutation ever recorded at file-level
    scope, which is a new provenance-inference policy, not a
    mechanical fix, and is therefore left unresolved per the
    directive's own Repair Authority boundary.
- **Canary E (No Answer-Key Leakage):** verified by direct source scan
  that Canaries A-D never name "representation-addressed pressure",
  "EnvironmentSignature pressure binding", "hierarchical pressure", or
  "dimensional pressure topology" as an expected test outcome.

---

## 5. Remaining Architecture Boundaries

- **Phase 7 confirmed, unchanged:** `derive_environment_signature()`
  has exactly one consumer in this repository —
  `aurora_genealogy_environment_shadow.py`, a manual, read-only
  diagnostic script that its own docstring states "is not imported by
  any live Aurora path." No repair was made or needed; this fact was
  re-verified directly (`grep` for every call site), not assumed.
- **`aurora_code_mutation_operators.py`/`get_operator`/
  `list_operator_specs`** referenced by `aurora_runtime.py` also resolve
  to `None` (the module does not exist anywhere in this repo). Unlike
  the `CodeEvolutionChamber` import, every consumer of these names
  already tolerates `None` gracefully (`op = get_operator(...) if
  get_operator is not None else None`), so this is a soft, gracefully-
  degraded feature gap, not a blocking defect matching this directive's
  named confirmed facts — left unrepaired, noted here for visibility.
- **`CodeAutoEvolver._apply_telemetry_probe`/`_apply_agency_surface`**
  both hardcode their target filename check to
  `"aurora_code_evolution_stack.py"` — a file that does not exist
  anywhere in this repo. Through `aurora_daemon.py`'s fixed
  `aurora_evolved_surfaces.py` target, these two operators can never
  actually produce a change. Adjacent to, but not itself, this
  directive's named confirmed facts (`architectural_reflection` and
  `native_surface_projection`, the operators actually exercised by
  `_run_code_mutation_cycle()`, are unaffected) — left unrepaired,
  noted here for visibility.
- **Canary D's mutation-history granularity gap** (§4) is the most
  actionable open boundary this pass surfaced: exact-function-scoped
  ancestry now coexists with only file-scoped mutation history.
  Closing it is a genuine, well-scoped next repair, but deciding how a
  historical file-level record should attribute to one of several
  functions it might concern is a provenance-inference policy
  decision, not a mechanical one, and was deliberately left for
  explicit resolution.

---

## 6. Deliberately Not Implemented

- No predetermined dimensional-pressure architecture was installed.
  `EnvironmentSignature` was never wired as a pressure key; no pressure
  field was indexed by genealogy; `PressureExperienceLedger` does not
  automatically drive code mutation; no Dream or conversational failure
  was mapped onto a source function.
- No automatic cross-file or cross-function mutation propagation was
  implemented (Phase 5) — same-named functions in different modules,
  or functions with real call relationships, each retain independent
  consequence-grounded selection.
- No definition of "operational homology" was invented anywhere —
  `exact_function_ids` is only ever supplied by a caller who already
  has it; this module never infers one function's identity from
  another's name or shape.
- No new trait ontology was created.
- Dream projections were not turned into confirmed evidence (unchanged
  from Build 646; not revisited since nothing in this pass touched that
  boundary).
- No capability-specific solution was coded to make Canary D's Class 2
  finding pass — it is reported as a genuine current limit, not
  patched around.

---

## 7. Regression Results

Full suite (234 files), run in the established sequential 4-batch
split to avoid OOM:

```
Batch 00 (56 files): 613 passed, 1 skipped, 2 failed  — 2784.12s
Batch 01 (61 files): 498 passed,            2 failed  —  749.40s
Batch 02 (58 files): 546 passed,            8 failed  — 1894.78s
Batch 03 (59 files): 554 passed,            0 failed  — 2293.69s
-----------------------------------------------------------------
Total:               2211 passed, 1 skipped, 12 failed
```

All 12 failures are the same failures, in the same files, identified
and individually reconciled as pre-existing/unrelated in the
immediately preceding Build 646 session (same repository state,
re-confirmed here rather than assumed):
- `test_concept_image_ingestion_import.py`,
  `test_d1_device_path_attribution.py` — no reference to any file this
  pass touched.
- `test_governance_liveness.py`,
  `test_m1_2_provenance_hygiene.py` — the former is known batch-order
  interaction (passes standalone); the latter concerns lexicon
  blind-origin tagging, an unrelated subsystem.
- `test_rcec_state_isolation_and_lifecycle.py::test_shutdown_aurora_stops_spawned_threads`
  and 7 tests in `test_reflective_readdressing.py` — verified against
  a pre-directive baseline commit via an isolated `git worktree` in the
  Build 646 session, identical failures, identical error messages,
  confirmed pre-existing.

No existing assertion was weakened. One genuine timeout-kill (SIGTERM
at a 280s command budget, mid-boot, triggering `aurora_checkpoint.py`'s
signal handler) during ad-hoc verification of Phase 4's test was
re-run with a longer budget and passed cleanly — not classified as a
product failure, per the directive's own instruction.

---

## Completion Condition Check

> A normal AuroraRuntime boot contains a real, source-current
> UniversalFunctionLineage — **yes**, demonstrated by real boot.
> Every autonomous production code-mutation path uses consequence-
> grounded fitness selection rather than compile/import success alone
> — **yes**, both `AuroraRuntime.finalize_code_mutation()` (Build 646)
> and `aurora_daemon.py::_run_code_mutation_cycle()` (this pass) now
> go through the same `CodeEvolutionChamber.evaluate_mutation()`.
> Accepted evolutionary ancestry survives process restart
> operationally — **yes**, demonstrated: a truly destroyed-and-rebuilt
> chamber auto-acquires a persisted accepted mutation as a real parent.
> Rejected evolutionary evidence survives restart without becoming
> parentage — **yes**, demonstrated separately.
> Mutation lineage can identify exact affected operations when that
> information exists — **yes**, `exact_function_ids` (Phase 3).
> File-level scope remains an explicit fallback rather than
> masquerading as exact operation ancestry — **yes**,
> `ancestry_scope`/`mutation_scope_kind` are always explicit.
> Fitness evaluation covers the actual mutation scope — **yes**, Phase
> 4's plan/reconcile/escape-reject cycle, demonstrated with a real
> escaped-file rejection and a real reconciled-scope acceptance.
> Same-named functions in different contexts remain independent unless
> real existing genealogy relates them — **yes**, demonstrated.
> PressureExperienceLedger's existing causal history survives restart
> and state-directory isolation — **yes**, demonstrated.
> No predetermined dimensional-pressure architecture has been installed
> — **confirmed**, see §6.
> The developmental canaries report how far Aurora's existing machinery
> can carry a representation-specific unresolved discrepancy — **yes**,
> §4, including one honestly-reported limiting boundary (Canary D).

This pass makes the developmental physics more intact than they were —
it does not claim Aurora has developed any new capability, and it does
not claim the dimensional-pressure question is answered. It reports,
concretely, exactly where her own existing machinery currently stops
carrying a discrepancy, so the next developmental experiment knows
precisely what it is testing against.
