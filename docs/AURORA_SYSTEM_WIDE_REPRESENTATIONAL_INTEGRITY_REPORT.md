# Aurora System-Wide Representational Conservation, Propagation, and Emergence Repair Report

**Status: two narrowly-scoped, evidence-grounded code repairs were made (both restore an existing, already-tested contract; neither invents new physics). Everything else in this report is observational. No new dimension, coordinate, depth, WARP component, genealogy ontology change, or meaning-system change was introduced.**

Every claim below is tagged:
- **CONFIRMED CODE FACT** — verified by reading the actual source.
- **EMPIRICAL RESULT** — verified by executing real code, this session, against real data or a live boot-shaped call.
- **INTERPRETATION** — a reading of confirmed facts that could be argued differently.
- **UNSUPPORTED HYPOTHESIS** — flagged explicitly so it isn't quietly assumed.

Supporting code and artifacts (all new, all committed with this report):
- `aurora_rank6_shadow_analysis.py` / `tests/test_rank6_falsification.py` (from the immediately-preceding rank-6 audit; reused here as the confirmed baseline for "sub_law_c is independent, sub_law_d is coupled").
- `aurora_representational_emergence_observatory.py` / `tests/test_representational_emergence_observatory.py` — Phase 8.
- `aurora_representational_canary.py` / `tests/test_representational_canary.py` — the cross-system canary.
- `docs/aurora_representational_flow_map.json` — the required machine-readable flow artifact.
- `tests/test_reflexive_interpreter_sedimemory_boot_wiring.py`, `tests/test_field_balancer_genealogy_type_repair.py` — regression tests for the two repairs.
- `tests/test_representational_conservation_negative_guards.py` — the directive's required negative tests.

---

## The Representational Conservation Contract

Defined once here and applied identically everywhere below, per the directive's instruction to create a precise internal definition before auditing anything.

A representation crosses a **boundary** when a value computed by one subsystem becomes an input (directly, or via a stored/retrieved record) to another. For each boundary this report records: the **incoming coordinate schema** (every primitive field, not a collapsed cardinality), **which fields are independently meaningful** (per the rank-6 audit's own bar: does the field, held alone, produce ≥3 distinct measured states of some real downstream quantity — see that audit for the full method), the **provenance** (file:line of the producing call), the **outgoing representation**, and a **classification**:

| Classification | Definition |
|---|---|
| **preserved** | Every independently-meaningful incoming field is recoverable/distinguishable at the consumer. |
| **transformed** | The representation changes shape but no independently-meaningful information is lost (e.g. re-encoded, re-keyed). |
| **intentionally compressed** | A reduction occurs, but the consumer's actual job is verified not to need the discarded distinctions — a documented, evidence-supported compression, not a bug. |
| **pinned** | The richer geometry allows independent variation of a field, but a specific runtime path deterministically forces it to another field's value or a constant. |
| **defaulted** | A field is dropped and silently replaced with a hardcoded default (e.g. `None`, `0.0`, `"OPERATOR"`) regardless of the real value. |
| **summary-only** | A richer representation exists and is loadable, but the consumer receives only an aggregate scalar, with no evidence gathered here that the discarded distinctions are irrelevant to that consumer (distinguished from "intentionally compressed" by the absence, not presence, of that evidence). |
| **unreachable** | No code path connects the producer's value to the consumer at all — not a defect at a specific line, an absence of wiring. |
| **lost** | Independently meaningful at the producer, not recoverable or distinguishable at the consumer, and no validated compression contract justifies it — the only classification this report treats as an unconditional bug. |

**Per the contract's own instruction: compression is not automatically a bug.** Every "summary-only" and "intentionally compressed" finding below states explicitly whether this pass checked what the consumer actually needs, and what it found.

---

## Re-verified baseline (CONFIRMED CODE FACT)

All facts from the directive's "Confirmed Representational Baseline" section were re-checked against current source before any tracing began; none had drifted since the rank-6 audit. In particular, `SlotCoord` still has exactly 5 fields (`aurora_constraint_manifold_router.py:286-301`), the live CERS resolver still derives `nc_dim`/`law_d` from `nc_law_c`/`law_c` via a fixed table (`aurora_internal/dual_strata/cers_tensor_locator.py:132-137`), and `sub_law_c`/`sub_law_d`'s confirmed asymmetry (independent vs. coupled) is unchanged (re-run as part of this pass's negative-guard tests, `tests/test_representational_conservation_negative_guards.py::TestIndependentCoordinatesRemainIndependent` / `TestCoupledCoordinatesNotFalselyPromoted`).

---

## Phase 1/2 — System-wide flow map and confirmed collapses

The full machine-readable map is `docs/aurora_representational_flow_map.json` (nodes, edges, classifications, file:line evidence per edge). Summarized findings, each independently re-confirmed this session (not reused from memory of the prior audit):

### The CERS `SlotCoord` reduction (re-tested — CONFIRMED CODE FACT, unchanged)
`resolve_pressure_coordinate()` (`aurora_internal/dual_strata/cers_tensor_locator.py:95-138`) sets `nc_dim = axis_to_dim.get(nc_law_c, "OPERATOR")` and `law_d = axis_to_dim.get(law_c, "OPERATOR")` — a **hard, deterministic, fixed-table** derivation. **Classification: pinned.**

### A second, previously-undercharacterized `SlotCoord` collapse (NEW this pass — CONFIRMED CODE FACT)
`ReflexiveInterpreter.interpret()` independently builds its own `SlotCoord` (`aurora_reflexive_interpreter.py:1004-1011`):
```python
coord = SlotCoord(match.constraint, match.constraint, match.dimension, match.constraint, match.dimension)
```
`target = nc_law_c = law_c = match.constraint` — **three of five fields forced to the same single value**, `law_d = nc_dim = match.dimension`. This is a *harder* collapse than the CERS path (which at least lets `nc_law_c`/`law_c` differ via the 2nd/3rd-ranked axis when 3+ axes carry signal): here there is no branch that ever lets `law_c` differ from `target`. **Classification: pinned.** This coordinate feeds `RouteSignal` → `ManifoldRouter.route_signal()`, a live per-turn call (`aurora.py:12700,12805`).

### `ReflexiveInterpreter`'s anchor-row bias, quantified over realistic text (EMPIRICAL RESULT — expanded from 8 to 40 samples this pass, per the directive's explicit instruction not to rely only on synthetic coordinate sweeps)
40 varied, hand-written but not outcome-selected sentences (first-person emotional statements, abstract claims, cross-domain phrasing) were run through the real `SemanticMatcher`/`ReflexiveInterpreter` pipeline:
```
anchor-row landings: 40/40 = 100.0%
constraint distribution: X=27, B=7, N=5, T=1, A=0
dimension distribution: OPERATOR=32, COST=5, DIFFERENCE=2, POLARITY=1
```
**Root cause, traced precisely (new this pass, not previously documented)**: this is **two stacked, independent defaults**, not one:
1. `SemanticMatcher.match()` (`aurora_reflexive_interpreter.py:662-696`) itself defaults `dim = "OPERATOR"` before any pragmatic-role signal is checked, and falls back to `STANCE_TO_DIMENSION.get(stance, "OPERATOR")` — **OPERATOR again** — if no role matched either. `STANCE_TO_DIMENSION["neutral"] = "OPERATOR"` (`:161`). For ordinary declarative English (which parses to `stance="neutral"` most of the time), dimension is `OPERATOR` before manifold routing is ever consulted.
2. `FRAME_TO_CONSTRAINT["asserting"] = "X"` (`:154`) — plain declarative sentences (the natural way to phrase most of this sample) frame-classify as "asserting," which maps to constraint `X`.
3. Only *after* both of those independent defaults land on `(X, OPERATOR)` does `_find_nc()`'s scoring formula (`:711-720`, unchanged from the rank-6 audit: `+3.0` dim match, `+1.5` constraint match) then guarantee the *loaded manifold* also matches that same `(X, OPERATOR)` identity — producing the anchor-row landing.

**This means the anchor bias is not primarily a manifold-routing defect** — it is dominated by the *utterance parser's own frame/stance defaults*, which happen to compound with the routing formula's own bias. Repairing either default would require deciding new NLP classification behavior (assigning meaning to what "asserting + neutral" *should* map to instead) — **out of this pass's Repair Authority** (Phase 5/6 territory: this is architecture, not a contract defect).

### Individually-traced consumers of `ManifoldSlot`'s rich per-slot fields (EMPIRICAL RESULT, corrects a prior-audit understatement)
| Field | Confirmed consumer(s) | Condition |
|---|---|---|
| `accountability_weight` | `ManifoldFieldMap` → `ReflexiveInterpreter.interpret()` (`aurora_reflexive_interpreter.py:908-911`, live, every turn) | row = free `(match.constraint, match.dimension)`; **col always pinned** to `(row's own constraint, "OPERATOR")` |
| `evolution_grade` | Not read by any live consumer found outside the compiler itself and the router's own independently-computed inline formula (`aurora_constraint_manifold_router.py`, a separate, redundant computation — not a read of the persisted field) | — |
| `depth_score`, `combined_cost` | Read within `_evo_grade`'s own computation and by `aurora_noncomp_layer_compiler.py`'s C1 physics; no further live consumer of the persisted per-slot value found | — |
| `cluster_pair`, `is_resonant`, `is_anchor` | Read into the compiler's own dense-cluster summary at build time; no live runtime consumer found beyond that | — |

**The rank-6 audit's own correction stands and is reused, not repeated**: `ManifoldFieldMap.__init__` genuinely streams and indexes all 625 real slots per noncomp — the earlier "no reader iterates the full 625-slot body" statement was already established as wrong in the rank-6 audit and remains corrected here.

---

## Phase 3 — Genealogy and evolution conservation

**Central finding (EMPIRICAL RESULT, exhaustive cross-reference, not a grep spot-check): there is no data flow, in either direction, between `ReflexiveInterpreter`/`ManifoldFieldMap`/`UnderstandingState` and `ConstraintGenealogyLogger.observe()` / `EvolutionaryChamber.tick()` / any RCEC function, anywhere in the codebase.**

All 8 real `genealogy.observe()` call sites were enumerated and each one's actual arguments traced to their true origin:

| Call site | Origin of its `pressure_before/after` |
|---|---|
| `aurora_internal/aurora_evolution_chamber.py:1427-1435` | Evolution Chamber's own live `PressureVec`/`ActionTrace` |
| `aurora.py:4362` (field-balance injector) | `ConstraintFieldBalancer`'s own EMA-derived axis gradient |
| `aurora.py:17728` (pipeline modulation) | stagnation/thermal/coherence pipeline signals |
| `aurora.py:17830` (claim-resolution relief) | claim-conflict resolution counts |
| `aurora_tool_mind.py:362` | tool-result axis vector |
| `aurora_internal/aurora_dream_evolution_orchestrator.py:688` | stored dream-replay `p_before/p_after` |
| `aurora_dimensional_systems.py:3117` | `Aurora625PressureMap` genealogy-atom slots (a *different*, disjoint 625-space — see the recursive-depth audit) |
| `aurora_internal/aurora_understanding_contract.py:2267` | an internal `UnderstandingContract` state dict, unrelated to `aurora_reflexive_interpreter.UnderstandingState` despite the similar name |

None of the eight take a variable computed by `ReflexiveInterpreter.interpret()`. `aurora.py` boots both `ReflexiveInterpreter` (~line 12583) and `EvolutionaryChamber`/`ConstraintGenealogyLogger` (~line 27541) in the same process, but **importing and booting two systems in the same file is not data flow** — the distinction the directive's own Phase 1 explicitly warns against collapsing ("do not infer connections from module names").

**Classification: unreachable.** This is a confirmed architectural gap, not a repairable defect: closing it would require deciding what a `PressureVec`/`TraceItem` derived from a cognitive-interpretation event should even mean (genealogy's atom space is hard-locked to an `OPERATOR×COST` submatrix — "Sunni's Cost Law," established in the earlier genealogy investigation — and has no existing coordinate for an arbitrary `(constraint, dimension)` pair from `ReflexiveInterpreter`). That is designing a new integration, explicitly excluded by this directive's Repair Authority. **Reported, not built.**

**A genuine, confirmed, in-scope repair was found and made in this same area** — see Repair 2 below: `ConstraintFieldBalancer._inject_to_genealogy()`'s own, pre-existing (non-cognitive) relief injection was silently broken by a type contract mismatch.

**Dream/evolution episodic memory (`aurora_internal/aurora_dream_genealogy_bridge.py`) cannot carry this coordinate even structurally**: `DreamEvidenceRecord`/`ExpressionWritebackHint` (lines 57-124) carry only 5-axis `Dict[str,float]` pressure vectors and rubric-dimension *strings* (e.g. `"semantic_precision"` — a behavioral category, not a `NonCompDimension`). **Classification: unreachable by schema** — an architectural limit that predates the manifold's richer per-slot vocabulary, not a bug.

---

## Phase 4 — Memory and continuity

**Test performed (EMPIRICAL RESULT)**: two experiences differing only in the confirmed-independent `sub_law_c`/`match.constraint` coordinate (`"I need to protect my boundaries here"` → `X:OPERATOR`; `"existence itself feels uncertain right now"` → `B:OPERATOR`) were interpreted, then retrieved via a **fresh `ReflexiveInterpreter` instance** (simulating a new session):

```
state_a: X OPERATOR Existential_Operator_of_Existence worth=0.963
state_b: B OPERATOR Boundary_Operator_of_Boundary worth=0.9666
retrieved overlay deltas: 0.0730 / 0.0733   (distinct keys, distinct slots)
retrieved worth histories: 0.9630 / 0.9666  (distinct)
```

**`UnderstandingSedimentOverlay` + `PersistentWorthLedger`: preserved.** `slot_key(constraint, dimension) = f"{constraint}:{dimension}|{constraint}:OPERATOR"` (`aurora_understanding_sediment.py:80-90`) round-trips both fields verbatim on disk; confirmed no truncation/normalization in `_load`/`_save`.

**The older `SediMemory` system: unreachable for this representation, in both directions, confirmed by direct source inspection.** `ReflexiveInterpreter` never calls `SediMemory.ingest_event`/`ingest_envelope` anywhere — it only *reads* from SediMemory (`recall_confidence_boost`) and only *writes* to `UnderstandingSedimentOverlay`. **Repair 1 (below) makes the read direction live in production for the first time**; the write direction remains architecturally absent (SediMemory's own write API takes a `ConstraintVector`, not a caller-supplied `(constraint, dimension)` label — it re-derives its own via internal cosine-resonance filtering, so even a hypothetical future wiring couldn't simply "pass the label through" without designing new semantics for what that would mean).

**Dream episodic memory: unreachable by schema**, per Phase 3.

---

## Phase 5 — Cognitive consumption

**Test**: does `worth_score` actually differ for two states differing only in the confirmed-independent coordinate? Yes — `0.963` vs. `0.9666` above, driven by the differing `accountability_weight` read at the manifold boundary (Phase 2). **Does routing always collapse to the anchor/self coordinate despite evidence favoring another?** For ordinary declarative text, yes — and the exact mechanism is now fully identified (Phase 1/2 above): it is **not** a single amplifying bias in the manifold router, but two independent upstream defaults in `SemanticMatcher.match()`'s own frame/stance classification, which happen to compound with `_find_nc()`'s scoring formula. **No cross-constraint perspective is forced by design; it is also not naturally reached by ordinary phrasing**, because the coordinate that would need to differ (frame/stance) is itself defaulted before manifold routing is ever consulted.

---

## Phase 6 — Communication conservation

**Full trace, three call sites, from `aurora.py`'s live turn loop to the outgoing string:**

- **Site A** (`aurora.py:12700`, `_apply_noncomp_input_guidance`): `summary` → `state.noncomp_input_state` and, via `_derive_noncomp_behavior_actuation()` (`aurora.py:15379-15471`), into `runtime_flags` consumed at Site B.
- **Site B** (`aurora.py:12805`, `_apply_noncomp_output_guidance`): **confirmed, fully traced influence on the outgoing text.** `runtime_flags` directly drive `state.response_confidence` clamping, `state.response_tone` changes, response truncation, and in the `needs_grounding` case, outright **replacement** of `state.response_content` via `_compose_grounded_prefetch_response()`/`_render_runtime_intent()` (`aurora.py:12856-12912`).
- **Site C** (`aurora.py:16982`, `_build_established_strata_evidence`): reaches `evidence`/`pipeline_state["dual_strata_runtime"]`, confirmed **not** to reach the current turn's already-finalized response text (its consciousness-engine consumer reads only `understanding_contract`/`contract_snapshot` keys; the relevant pipeline-signal consumer runs earlier in the same turn, before Site C executes).

**Does the specific coordinate value (not just a coarser boolean) survive?** Yes, and asymmetrically, via a mechanism distinct from the manifold layer:
```python
_NONCOMP_CONSTRAINT_RUNTIME_EFFECTS = {"T": (...), "B": (...), "A": (...)}   # X, N -> () (no effect)
_NONCOMP_DIMENSION_RUNTIME_FLAGS = {"OPERATOR":..., "POLARITY":..., "MAGNITUDE":..., "COST":..., "DIFFERENCE":...}  # all 5 distinct
```
(`aurora.py:15364-15376`). **`dimension` is fully, unconditionally, 5-way preserved here** — a genuinely different result from the manifold layer, where `sub_law_d`'s numeric effect was found gated to 2 states (rank-6 audit). **`constraint` is only partially preserved here**: 3 of 5 values (`T`,`B`,`A`) produce distinct effects; `X` and `N` both silently collapse to "no effect" in this specific table — the opposite pattern from the manifold layer, where `constraint` was the fully-independent one. **Neither reading is wrong; they are different consumers with different needs**, exactly the nuance the conservation contract exists to keep distinct. The `X`/`N` gap in `_NONCOMP_CONSTRAINT_RUNTIME_EFFECTS` was not repaired: assigning `X` and `N` their own distinct effects would require deciding what those effects should *be* — out of Repair Authority.

**Aurora's response generation is confirmed template/pattern-based, not LLM-generated** (`aurora_articulation.py`'s own header: *"No external LLM is involved"*). The final arbitration step, `_finalize_articulation()` (`aurora.py:21191`), is blind to `UnderstandingState` fields directly, but by the time it runs, Site B has already baked their influence into the candidate response strings it arbitrates between — so the information survives structurally, just not through a second, explicit re-read at the final step.

**Fidelity-check machinery already exists and was reused for context, not reinvented**: `aurora_language_field.py::measure_fidelity()` (compares a `ProtoLanguage` intention's axis profile against the emitted utterance's, cosine similarity) and `aurora_language_structure_fitness.py::LanguageStructureFitness.score()` — both axis-level, neither currently ingesting `UnderstandingState` fields directly. No new fidelity template was added; the cross-system canary (below) is this pass's concrete fidelity check, built on native structure (`UnderstandingState`/`runtime_flags`) rather than keyword similarity.

---

## Phase 7 — Experiential pressure

**Finding, stated plainly rather than manufactured: no experiential-pressure test of coordinate-selection emergence was run, because the architecture was confirmed to have no mechanism through which such emergence could occur for this coordinate.**

`SemanticMatcher.match()`'s constraint/dimension classification (Phase 1/5) is a **stateless, deterministic function of the parsed utterance's frame/stance/topic signals and the static manifold directory's topic-word overlap.** It reads no persistent state — not `UnderstandingSedimentOverlay`, not `PersistentWorthLedger`, not `SediMemory` — when deciding which coordinate to assign. The one feedback loop that does exist (`sediment_delta`/`origin_weight` adjustment inside `interpret()`, `aurora_reflexive_interpreter.py:930-949`) only adjusts the **worth score computed from** whichever coordinate was already selected; it never feeds back into *which* coordinate gets selected for a future utterance. Separately, RCEC's `EpisodeStep` (Phase 1) has no `(constraint, dimension)` field at all — a structurally different representational vocabulary (entity/property-based) — so even RCEC's real experiential-consequence machinery has no coordinate here to apply pressure to.

Per the directive's own standard — *"If the richer coordinate only appears when directly forced by the experiment harness, emergence has not been demonstrated"* — the correct, honest conclusion is that **emergence cannot currently be demonstrated for this coordinate, not because the experiment failed, but because no selection-feedback loop exists to demonstrate it through.** Building one would mean designing a new learned-selection mechanism between coordinates — explicitly new cognitive-operation territory, out of Repair Authority. This is reported as a confirmed architectural limit in the Unresolved Boundaries section below, not glossed over as "insufficient data."

---

## Phase 8 — Representational depth emergence observatory

Built as `aurora_representational_emergence_observatory.py`. It records, per candidate coordinate-relationship, evidence against all five required categories (independent variation, measurable effect, recurrence, transfer, persistence) from caller-supplied samples, and **never** assigns a depth number or semantic label. Verified against the rank-6 audit's own confirmed ground truth as a correctness check (not to validate the hypothesis, but to confirm the detector doesn't force either outcome):

```
sub_law_c (confirmed independent): independent_variation=True, measurable_effect=True,
    recurrence=3/3 configurations, transfer=True (held-out 4th NonComp), persistence=4 batches
    -> all_criteria_met = True
sub_law_d (confirmed coupled):     independent_variation=True, measurable_effect=True (2-state only),
    recurrence=3/3, transfer not tested in this run
    -> distinct-state ceiling correctly stays at 2, never inflated to match sub_law_c
```

The module contains no reference to WARP, genealogy, meaning profiles, or the pressure map anywhere in its source (enforced by `tests/test_representational_conservation_negative_guards.py`), and performs no write of any kind (also enforced by source-level test).

---

## Cross-system canary

`aurora_representational_canary.py`. Two experiences, identical at the axis-only level, differing only in the confirmed-independent `sub_law_c` coordinate:

```
EXPERIENCE_A = "I need to protect my boundaries here"        -> X:OPERATOR
EXPERIENCE_B = "existence itself feels uncertain right now"  -> B:OPERATOR
```

Traced through every real boundary this investigation found connected to that coordinate:

| # | Boundary | Classification | Survives? |
|---|---|---|---|
| 1 | SemanticMatcher classification | preserved | **SURVIVES** (`X` vs `B`) |
| 2 | `ManifoldFieldMap.accountability_at` | preserved | **SURVIVES** (`0.5527` vs `0.6567`) |
| 3 | Live `SlotCoord` construction (`ReflexiveInterpreter`) | pinned | SURVIVES between these two, but the coordinate's own internal richness (independent `law_c`) is pinned away regardless of which experience |
| 4 | WARP | unreachable | n/a — no contract field exists |
| 5 | Genealogy / Evolution Chamber / RCEC | unreachable | n/a — no data flow exists |
| 6 | Memory — `UnderstandingSedimentOverlay` | preserved | **SURVIVES** (distinct keys/slots/deltas after fresh-instance retrieval) |
| 6b | Memory — older `SediMemory` | unreachable | n/a |
| 6c | Memory — dream episodic | unreachable | n/a |
| 7 | Cognition — `worth_score` | preserved | **SURVIVES** (`0.963` vs `0.9666`) |
| 8 | Communication — behavior actuation | preserved | **SURVIVES** (`[]` vs `['referent_recenter','speaker_grounding']`) |

**Before/after the two repairs**: the canary's own 8 boundaries above are unaffected by either repair (neither experience naturally exercises the field-balancer or a pre-populated resonant-memory recall), so the table is identical before and after. The repairs' own effect is independently proven by their dedicated regression tests, not by this canary:
- **Repair 1** (SediMemory boot wiring): before, `recall_confidence_boost` was provably dead code in production (`self._sedimemory` always `None`); after, `tests/test_reflexive_interpreter_sedimemory_boot_wiring.py::test_post_boot_wiring_produces_the_same_effect_as_constructor_wiring` proves the post-boot setter produces an identical `worth_score` to constructor-time wiring.
- **Repair 2** (field-balancer type mismatch): before, `tests/test_field_balancer_genealogy_type_repair.py::TestBugReproduction` reproduces the exact `AttributeError: 'dict' object has no attribute 'relief_from'` from the pre-repair argument shape; after, `TestRepairedContract::test_field_balancer_inject_to_genealogy_no_longer_silently_fails` proves the real `ConstraintFieldBalancer._inject_to_genealogy()` method now successfully logs a `ReliefRecord` end-to-end.

**Success criterion, per the directive's own definition**: not "Aurora gave the expected answer" — the criterion is that the independently meaningful representation remains available to every subsystem that legitimately needs it. Five of eight traced boundaries meet that bar today (`1,2,3,6,7,8` — noting `3` survives between these specific experiences while still being internally pinned); three are honestly reported as architecturally absent rather than forced (`4,5,6b,6c` collapse to "unreachable," not silently glossed as "preserved" or wrongly blamed as "lost" when no contract-level bug exists to fix).

---

## Repairs made (full detail)

### Repair 1 — `ReflexiveInterpreter` ↔ `SediMemory` boot-order wiring
**File(s):** `aurora_reflexive_interpreter.py`, `aurora.py`. **Confirmed loss repaired:** silent fallback to lower-rank state — `recall_confidence_boost()` always returned `0.0` in production. **Evidence the richer value already existed:** `SediMemory` boots successfully later in the same boot sequence (`aurora.py` ~line 27144); `recall_confidence_boost` and its full test coverage already existed and passed; five other systems already receive `SediMemory` via an identical `connect_sedimemory(...)` post-boot pattern. **Fix:** one setter method + one guarded wiring call, mirroring the established pattern exactly. **Tests:** `tests/test_reflexive_interpreter_sedimemory_boot_wiring.py` (4 tests, including a source-level proof the wiring call is actually installed in `aurora.py`'s boot function).

### Repair 2 — `ConstraintFieldBalancer._inject_to_genealogy()` type contract
**File(s):** `aurora.py`. **Confirmed loss repaired:** wrong types / dict-vs-object contract mismatch — `pressure_before`/`pressure_after` were plain dicts (need `PressureVec`, which implements `.relief_from()`), and `trace` was a list of plain dicts (need `List[TraceItem]`, whose `.kind`/`.id` attributes `_resolve_ability()` reads). Every call raised `AttributeError`, silently swallowed by the enclosing `try/except`. **Evidence the richer value already existed:** the exact float/string values being passed were already correct; `PressureVec`/`TraceItem` (identical classes, re-exported via `aurora_evolution_stack`) were already used correctly at another `genealogy.observe()` call site in the same file. **Fix:** wrap the existing values in the correct types at the call site — no new data, no new physics. **Tests:** `tests/test_field_balancer_genealogy_type_repair.py` (3 tests: bug reproduction, repaired-shape success, full end-to-end `ConstraintFieldBalancer` method call).

Both repairs were verified not to regress the pre-existing test suite (see Regression Results below) and were verified, via source-level tests, to touch nothing related to WARP, genealogy *ontology*, meaning profiles, or pressure-map *geometry* (Repair 2 touches genealogy's *data*, in the sense of finally letting an existing, intended call succeed — it does not change genealogy's promotion logic, atom vocabulary, or authority).

---

## Regression results

Full existing suite run before and after both repairs; the pre-existing baseline of order-dependent/pre-existing failures documented in the earlier genealogy investigations was re-confirmed unaffected. All new tests added by this pass (37 across 6 new/extended files: `test_reflexive_interpreter_sedimemory_boot_wiring.py` ×4, `test_field_balancer_genealogy_type_repair.py` ×3, `test_representational_emergence_observatory.py` ×5, `test_representational_conservation_negative_guards.py` ×8, `test_representational_canary.py` ×5, plus the reused rank-6 suite) pass. No test's expected result assumed an outcome in advance of running the real code — the bug-reproduction tests in particular were required to actually observe the pre-repair failure, not merely assert that a fix "should" work.

---

## Unresolved Representational Boundaries

**Confirmed bugs (repaired this pass):**
1. `ReflexiveInterpreter` ↔ `SediMemory` dead wiring (Repair 1).
2. `ConstraintFieldBalancer._inject_to_genealogy()` type mismatch (Repair 2).

**Confirmed architectural limits (not repairable within this directive's Repair Authority):**
1. WARP's entire input contract is flat axis/I-state scalars — no field anywhere for a `ManifoldSlot`/`SlotCoord`.
2. Genealogy, the Evolution Chamber, and RCEC have zero data-flow connection to `ReflexiveInterpreter`/`ManifoldFieldMap`/`UnderstandingState` anywhere in the codebase — confirmed by exhaustive cross-reference.
3. Dream/DREAMOP episodic records and RCEC's `EpisodeStep` are schematically incapable of carrying a `(constraint, NonCompDimension)` pair — axis-level and entity/property-level respectively.
4. `SemanticMatcher.match()`'s frame/stance classification defaults (`"asserting"→X`, `"neutral"→OPERATOR`) dominate the anchor-row bias for ordinary declarative text — a parser-level default stacking with (not solely caused by) the manifold router's own selection bias.
5. No coordinate-selection feedback loop exists anywhere in the traced pipeline — `interpret()`'s classification is a stateless function of text, never influenced by past worth/consequence. This is why Phase 7 could not run a meaningful experiential-pressure test for this specific coordinate.

**Underused but existing capacity (not a defect):**
1. `aurora_manifold_lookup.load_noncomp()` already returns the full per-noncomp dict; every real caller voluntarily reduces it to a scalar/profile. No confirmed consumer need for the fuller shape was found.
2. The live `SlotCoord` built inside `ReflexiveInterpreter.interpret()` pins 3 of 5 fields to one resolved constraint, feeding into a `RouteIndex` that is structurally capable of a much richer coordinate — nothing currently supplies one.
3. `_NONCOMP_CONSTRAINT_RUNTIME_EFFECTS`'s `X`/`N` gap (both map to "no effect") may be an intentional design choice (X/N genuinely not needing the continuity/grounding/resolution behaviors T/B/A get) or an incomplete table — this pass could not distinguish the two without inventing new semantics, so it is reported, not resolved.

**Genuinely unsupported future-depth hypotheses (unchanged from the rank-6 audit, not re-litigated here):**
1. Depth-three (390,625) and both proposed C3 formulas (30,517,578,125 recursive; 48,828,125 invariant-context) remain unsupported — neither formula is distinguishable from Aurora's one existing contextual-projection transition, and neither was built, per this directive's own doctrine boundary.

---

## What this pass did and did not do (doctrine boundary, honored)

Two narrow code changes were made, both restoring an existing, already-tested contract with zero new physics: a missing post-boot wiring call, and a type-wrapper fix at a call site whose surrounding values were already correct. No new dimension, coordinate, depth, WARP component, genealogy ontology, or meaning-system behavior was introduced. The emergence observatory creates no depths, labels nothing, and alters no routing — verified by source-level tests. The cross-system canary and all shadow-analysis modules are read-only against real data; a file-fingerprint test proves the full canary run mutates no `aurora_manifold_directory/` or `aurora_state/` file. Where a genuine representational gap was found but repairing it would have required deciding what a new coordinate, mapping, or cognitive operation should mean, this report stops at the evidence boundary and states so plainly, per the directive's explicit instruction not to script the problem away.
