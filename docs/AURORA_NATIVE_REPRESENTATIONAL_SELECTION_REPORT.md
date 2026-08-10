# Aurora Native Representational Selection and Causal-to-Representational Transition Falsification Report

**Status: observational and falsification-oriented only. No code repair was made in this pass — no confirmed loss defect meeting Repair Authority's bar (an already-existing intended contract broken, with the richer value already present on both sides) was found. No new coordinate, depth, cognitive operation, or wiring was added.**

Every claim below is tagged:
- **CONFIRMED CODE FACT** — verified by reading the actual source.
- **EMPIRICAL RESULT** — verified by executing real code, this session, against real data.
- **INTERPRETATION** — a reading of confirmed facts that could be argued differently.
- **UNSUPPORTED HYPOTHESIS** — flagged explicitly so it isn't quietly assumed.

Supporting code (all new, all read-only/ephemeral-state, none touching production files):
- `aurora_same_input_history_canary.py` / covered by `tests/test_native_representational_selection.py`
- `aurora_causal_vs_representational_probe.py` / same test file
- `aurora_selection_feedback_map.json` — the required machine-readable feedback map

---

## Baseline re-verification (CONFIRMED CODE FACT)

All nine baseline items were independently re-checked against current source, not assumed from the prior report:

1. `sub_law_c`: still 5/5 distinct numeric manifold states (re-run via `aurora_rank6_shadow_analysis`, unchanged).
2. `sub_law_d`: still capped at ≤2 numeric states (re-run, unchanged).
3. `ReflexiveInterpreter.interpret()` still builds `SlotCoord(match.constraint, match.constraint, match.dimension, match.constraint, match.dimension)` (`aurora_reflexive_interpreter.py:1004-1011`, unchanged).
4. `SemanticMatcher.match()` still defaults `dim="OPERATOR"` before role-checking and falls back to `STANCE_TO_DIMENSION.get(stance,"OPERATOR")`; `FRAME_TO_CONSTRAINT["asserting"]="X"` unchanged.
5. `UnderstandingSedimentOverlay` still preserves `(constraint, dimension)` verbatim across a fresh interpreter instance (re-run empirically this session, see the same-input-history canary below).
6. The coordinate distinction still measurably affects `worth_score` (re-confirmed).
7. The coordinate still influences live behavior actuation (`_NONCOMP_CONSTRAINT_RUNTIME_EFFECTS` differs by constraint, re-confirmed).
8. WARP, Genealogy/Evolution/RCEC, old SediMemory write direction, and Dream episodic schemas remain unreachable for this representation (re-confirmed; no code changed there since the prior pass).
9. `SemanticMatcher.match(self, expression: str) -> MatchResult` — re-confirmed by direct signature inspection this session — takes no history/worth/sediment argument, and its source contains zero references to `worth`, `sediment`, `ledger`, `history`, `recall`, or `overlay`.

**No drift found. Proceeding was authorized.**

---

## Part I — The causal/representational distinction used in this audit

Defined once, applied consistently, never assumed satisfied by a label:

- **Independent causal degree**: controlled variation of a coordinate produces a unique, measurable change in existing behavior/physics not reducible to already-controlled degrees. `sub_law_c` already qualifies (rank-6 audit).
- **Candidate representational degree** requires, additionally, evidence for:
  - **R1 Differentiation** — values remain distinguishable.
  - **R2 Independent consequence** — differences have unique downstream effect.
  - **R3 Invariant relation** — an *Aurora-code-supported* invariant exists under which the differentiated states are states/presentations of the same thing. Must be discovered, not supplied.
  - **R4 Persistence** — the candidate-distinction-to-invariant relation holds across more than one context/episode/retrieval.
  - **R5 Functional use** — some downstream process actually *uses* the differentiated candidate while the invariant stays fixed.
  - **R6 Decoupling/mismatch capability** — a native way to detect "internal state says A, underlying condition says B," *if one exists*. Absence is reported as `NOT DEMONSTRATED`, not as a defect.

---

## Part II — Full native selection-feedback audit (EMPIRICAL RESULT + CONFIRMED CODE FACT)

Traced actual data flow (never inferred from co-import or shared terminology) across every area the directive named, using both direct inspection and an independent background research pass:

| Area | Result |
|---|---|
| `UtteranceParser` adaptive state | **No path.** No `__init__` at all — zero instance state. All lookup sets are class-level literals, never reassigned, monkeypatched, or subclassed anywhere in the repo. |
| `BehavioralIdentityEngine` | **No path.** Zero references to any of the 6 selector-input identifiers anywhere in the file. |
| `ConsciousnessEngine` | **No path.** Same zero-match result. |
| `DimensionalSystems` | **No path.** Same zero-match result. |
| RCEC (`aurora_cognitive_experience_chamber.py`) | **No path.** Its `ActionInterface.interpret_expression` is a locally-defined, separate interpreter for simulated-world action selection — not `SemanticMatcher`, writes to none of the same stores. |
| Afterthought / reflective inspection / correction / backprojection | **No path.** `aurora_reflective_readdressing.py`'s own docstring: *"No permanent belief, rule, or code change is made here."* Reads `UtteranceParser` only as a consumer. |
| Adaptive manifold rewriting | **Dead write path found.** `scripts/bridge_ledger_to_noncomps.py` genuinely writes real consequence data (from the live `PressureExperienceLedger`) into each noncomp file's `development_tracking.history` — but it is a manually-invoked, `__main__`-gated offline script with **zero runtime consumers** of that field anywhere in the codebase (`_find_nc`, `ManifoldFieldMap`, `stream_slots`, `entries_for_axis` — none read it). A real write into a field nothing reads. |
| `UnderstandingSedimentOverlay` / `PersistentWorthLedger` / `recall_confidence_boost` | **Downstream only, re-confirmed.** All three run *after* `match()` has already fixed the coordinate (`aurora_reflexive_interpreter.py:911` runs before lines 930-970); none is ever consulted by `UtteranceParser.parse()` or `_find_nc()` for a *future* call. |

**Central Part II finding: across every traced area, no live/automatic path exists by which Aurora's past experience alters the inputs to a later coordinate selection.** The one place consequence data touches the manifold directory at all is a dead write with no reader.

---

## Part III — Same-input, different-history canary

`aurora_same_input_history_canary.py`. Two real experiential histories, built using only `ReflexiveInterpreter.interpret()` (the live call path — nothing written directly to the overlay/ledger):

- **History P**: 5 repeated real interpretations of the test input itself (real consequence: worth history rises, sediment deposits accumulate for *this exact* key).
- **History Q**: 5 repeated real interpretations of a different sentence landing on a different `nc_name` (real consequence for a *different* key).

Then, **the identical test input** (`"I need to protect my boundaries here"`) was presented to a fresh `ReflexiveInterpreter` instance under each history (simulating a new session inheriting only persisted state):

```
selection_inputs_identical:    True   (frame, stance, pragmatic_signal_roles, topic_words, query_type, semantic_override — all bit-identical)
selected_coordinate_identical: True   (constraint=X, dimension=OPERATOR, nc_name=Existential_Operator_of_Existence — identical)
downstream worth_score:        0.963 under both histories — identical
downstream field_region:       "dense" under History P, "mid" under History Q — DIFFERENT
```

**Outcome A**, per the directive's own taxonomy: *same coordinate, identical selection inputs.* No history-derived value reached coordinate selection through any path this canary exercised.

**A precise, honest, additional finding, kept separate from the selection question per the directive's instruction not to conflate them**: `field_region` legitimately *did* differ between histories, purely because History P's own repeated exposure built real sediment-overlay density for the test input's own slot, while History Q's exposure (a different slot) contributed nothing to it. This demonstrates that experiential modulation is real and reaches downstream understanding state (consistent with the prior conservation report) — while confirming, empirically and not just structurally, that it never reaches coordinate *selection* itself.

---

## Part IV/V — Causal-vs-representational probe and invariant discovery

`aurora_causal_vs_representational_probe.py`, applied to `sub_law_c`:

| Criterion | Result | Evidence |
|---|---|---|
| R1 Differentiation | **MET** | 5/5 distinct numeric manifold states (rank-6 audit, reused). |
| R2 Independent consequence | **MET** | `_NONCOMP_CONSTRAINT_RUNTIME_EFFECTS['X']=()` vs `['B']=('speaker_grounding','referent_recenter')` — live-wired to response composition. |
| R3 Invariant relation | **Partial** | `topic_words` — computed by the *same* `parse()` call that produces frame/stance, and independently read by `_find_nc()`'s own scoring (`+0.5` per overlapping word, `aurora_reflexive_interpreter.py:714-719`) — is a real, code-discovered candidate. Empirically confirmed: the topic stem `"boundar"` appeared in topic_words for 4/4 hand-varied paraphrases of a boundary-themed idea while `constraint` varied across `{B, T, X}`. |
| R4 Persistence | **NOT MET** | `UnderstandingSedimentOverlay`/`PersistentWorthLedger` key exclusively by `(constraint, dimension)`/`nc_name` — `topic_words` is recomputed fresh from raw text every call and is never itself stored, keyed, or retrieved anywhere in the codebase. Two utterances sharing a topic but landing on different constraints leave no cross-referencing trace that a later retrieval could recover. |
| R5 Functional use | **MET, narrowly** | `_find_nc`'s topic-overlap term is real and always active — but it disambiguates *within a single call*, not across episodes (the stronger sense R4's failure rules out). |
| R6 Decoupling/mismatch | **NOT DEMONSTRATED** | See below. |

**R6 in detail**: `recall_confidence_boost()` (the one SediMemory-read path live-wired to `ReflexiveInterpreter`) calls `recall_semantic(..., axis_filter=(constraint,), ...)` — **pre-filtered to the current turn's own constraint**, so a same-topic memory resonant on a *different* constraint is excluded from the search itself, and the function reads only `r["score"]`, discarding SediMemory's own `"axis"` field on every result. A structurally similar but broader query exists elsewhere: `aurora.py`'s `_build_established_strata_evidence` calls `recall_semantic(..., axis_filter=['X','T','N','B','A'], ...)` and **does** preserve each result's `"axis"` alongside its score into `evidence['sedimemory_recall']`. But no consumer of that evidence dict was found comparing those recalled axes against the current turn's own `match.constraint` — confirmed by grepping every reference to `'sedimemory_recall'` in `aurora.py`. **The raw material for a mismatch signal exists in one place in the data; the comparison that would turn it into a detected mismatch does not exist anywhere in the traced code.**

**Classification: `CAUSAL_ONLY`.** Independent causation (R1/R2) is fully confirmed. A real, non-invented invariant candidate exists and is functionally used within a call (R3/R5), but fails persistence (R4) — nothing in this codebase maintains topic identity as a retrievable object across episodes for different constraint-classified utterances about it. R6 is not demonstrated. This is exactly the directive's **Outcome D**.

---

## Part VI — Relation-to-object promotion search

Searched broadly (not limited to `sub_law_c`) for any existing case where a conditional relation later becomes an independently measurable, reusable object. **One genuine, pre-existing example was found**, entirely outside the manifold/`sub_law_c` space:

`aurora_internal/constraint_genealogy.py:1182-1206`, `ConstraintLink` — its own docstring: *"A promoted pair (or pair-of-pairs) that has proven reliably effective. Once promoted, it becomes a re-usable trace element."* `parents: List[str]` can hold ability ids **or link ids**, and `depth: int` is `>1` exactly when a parent is itself a `Link` — genealogy already has a real, non-hypothetical mechanism where a promoted relation becomes an object that can itself be an endpoint of a later, higher-order relation.

**Caveat, stated per doctrine**: this pattern lives entirely in genealogy's atom-pair space, which the prior system-wide conservation report confirmed has **zero data flow** with `ReflexiveInterpreter`/the manifold coordinate under investigation here. It is reported as an existing precedent for the general pattern, not as evidence for the manifold's proposed depth-three space, and no depth number is assigned to it.

---

## Part VII — Persistence / mismatch probe

Covered by R6 above (persistence of a coordinate-derived state after its immediate cause is removed, and native mismatch detection). Summary: `UnderstandingSedimentOverlay`'s deposits genuinely **do** outlive the immediate turn that caused them (confirmed across sessions, Part III/rank-6 audit) — so a coordinate-derived *state* (not the coordinate-selection *decision* itself) can and does persist past its originating input. Native mismatch detection between an internal differentiated state and the condition it's purported to represent was searched for specifically and **not found reachable** from `ReflexiveInterpreter`'s own live path, though the raw material exists one hop away (per R6).

---

## Part VIII — Emergence observatory: not extended, and why

`aurora_representational_emergence_observatory.py` was **not modified** in this pass (confirmed: `git status` shows it untouched). Its five criteria (independent variation, measurable effect, recurrence, transfer, persistence) answer *"is this coordinate independently real,"* which is a different question from R1-R6's *"does Aurora use it as a representation of something, not merely as a causal knob."* This investigation did not surface a substrate-independent observable that could be added to the existing five without either (a) duplicating what R1-R6 already does in a separate, purpose-built module, or (b) blurring the observatory's existing, tested boundary. The two modules are kept separate by design; `aurora_causal_vs_representational_probe.py` is the correct home for this pass's new evidence, not a retrofit of the observatory.

---

## Part IX — Architectural absence report

**The missing transition, stated precisely**: *A producer exists (`PressureExperienceLedger`, real consequence data, already written live) whose data is genuinely written into the manifold directory's per-noncomp `development_tracking.history` field by an existing offline script — but no consumer exists (`_find_nc`, `ManifoldFieldMap`, `entries_for_axis`) that reads that field back into a live classification decision.*

- **Producer that already exists**: `PressureExperienceLedger.record()` (`aurora_internal/aurora_pressure_ledger.py:108`) → `aurora_state/pressure_experiences.jsonl` → `scripts/bridge_ledger_to_noncomps.py` → `development_tracking.history` on disk.
- **Consumer that would need the information**: `SemanticMatcher._find_nc()`'s scoring, or `UtteranceParser.parse()`'s frame/stance defaults — neither currently reads `development_tracking` at all.
- **Exact representation available at the producer**: consequence/outcome records tied to a specific noncomp.
- **Exact schema expected by the consumer**: `_find_nc()` reads only `e.nc_dim`, `e.nc_name`, `e.nc_law_c` off static `IndexEntry` objects — no field for a consequence-weighted score exists in that schema at all.
- **Nature of the gap**: **schema absence plus missing cognitive operation**, not a wiring bug or type mismatch. `IndexEntry` would need a new field, and something would need to decide *how* accumulated consequence should bias scoring — that is designing a new cognitive operation, explicitly out of Repair Authority.
- **Native intermediary**: none found — no existing bridge already computes "consequence-weighted classification bias" from `development_tracking.history` in a form ready to consume.
- **Repair vs. invention**: closing this gap would invent new cognition, not restore an existing one. **Not repaired. Reported.**

---

## Required output artifacts

1. `docs/AURORA_NATIVE_REPRESENTATIONAL_SELECTION_REPORT.md` — this report.
2. `aurora_selection_feedback_map.json` — every discovered path (found / no-path / dead-write / downstream-only), the canary result, the probe result, and the relation-promotion finding.
3. `aurora_same_input_history_canary.py` — Part III, read-only/ephemeral-state.
4. `aurora_causal_vs_representational_probe.py` — Parts IV-VII, R1-R6, never labels a depth.
5. `tests/test_native_representational_selection.py` — 11 tests, including all six required negative controls (simple causal effect alone insufficient; multiple values alone insufficient; persistence alone insufficient — verified via the real overlay key schema; experimenter-invented invariant rejected unless code-grounded — verified by inspecting `_find_nc`'s actual source; `sub_law_d` not falsely promoted; observatory/probe/canary proven not to mutate production state; no test assumes its result before running real code).

---

## Central questions, answered plainly

**Can Aurora's past experience alter which representational frame she selects for the same later input?** No — confirmed both structurally (the selector's signature and source contain no history-derived input) and empirically (the same-input-history canary, Outcome A).

**If no, exactly where is the feedback path absent?** At `SemanticMatcher.match()` itself, and at every one of the six additional subsystems traced in Part II. The one place consequence data reaches the manifold directory at all (`development_tracking.history`) has no reader.

**Is `sub_law_c` merely independently causal, or does Aurora use it relative to a persistent native invariant?** Causal only (`CAUSAL_ONLY`, Outcome D). A real, code-discovered invariant candidate (`topic_words`) exists and is functionally used within a single call, but fails persistence across episodes.

**What invariant, if any, is demonstrated by Aurora rather than supplied by the experimenter?** `topic_words`, as read by `_find_nc()`'s own scoring — genuinely code-grounded, not invented — but only within a single interpretation call, never as a persisted cross-episode identity.

**Can the candidate representation persist or operate after its immediate causal source is absent?** The *understanding state* it produces (sediment deposits, worth history) does persist across sessions (confirmed). The *coordinate itself* is recomputed fresh from text every time — there is no persisted "this is still about the same thing" object independent of re-parsing the text.

**Can Aurora natively detect a mismatch between an internal differentiated state and the thing/state it is purported to represent?** Not demonstrated, for `sub_law_c`. The raw material (axis-tagged recall results) exists in one code path (`_build_established_strata_evidence`); no comparison logic consuming it was found.

**Is there any existing example where a dependent relation becomes an independently reusable object of representation?** Yes — `ConstraintLink` in genealogy's own atom-pair space — but disconnected from `sub_law_c`/the manifold coordinate, and not evidence for depth-three there.

**Does any finding justify changing the current Invariant Differentiation Principle, or does it merely constrain its measurement?** Merely constrains its measurement. Nothing found here contradicts the prior conservation report; it sharpens the boundary between "conserved/consequential" (which `sub_law_c` demonstrably is) and "representational" (which it is not yet shown to be).

**What, precisely, remains unproven?** Whether `topic_words` (or any other code-grounded invariant not yet tried) could satisfy R4 if some future, narrowly-scoped repair gave it a persistent identity — this pass found no such persistence mechanism *already existing*, so building one is out of scope here, not ruled out in principle. Whether the dead `development_tracking.history` write path was ever intended to be read by something that was since removed or never finished — this pass found no evidence either way and does not speculate.
