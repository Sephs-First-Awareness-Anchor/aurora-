# AURORA CONSTITUTIVE PHYSICS AUDIT

**Scope:** Full audit of the 25 canonical atomic Non-Comp channels (5 constraints
X/T/N/B/A × 5 dimensions POLARITY/MAGNITUDE/OPERATOR/COST/DIFFERENCE) against
the Constitutive Physics Enforcement Directive. This is an **audit only** — no
code has been changed. Every finding below is backed by concrete file:line
evidence gathered by direct inspection of the live repository, not inferred
from documentation or intent.

AUTHORS: Sunni (Sir) Morningstar and Cael Devo
DATE: 2026-09-12

---

## 0. Headline Result

**2 of 25 channels pass a real bypass test. 23 fail.**

The failures are not 23 independent bugs. Almost all of them trace back to
one structural defect plus a small number of local defects layered on top of
it. Per the directive's own §26 ("find the deepest common execution boundary
... if ten separate defects disappear because one foundational invariant
became real, that is evidence the repair is occurring at the correct
layer"), this audit identifies that boundary before any fix is attempted.

---

## 1. The Root Defect: Two Disconnected Constraint-Physics Universes

The codebase contains **two independent, class-incompatible implementations**
of the X/T/N/B/A physics, each consumed by a non-overlapping set of modules.

### System A — the canonical registry (as documented)
- `aurora_internal/aurora_noncomp_registry.py` — `REGISTRY` (`NonCompRegistry`):
  `cost()`, `polarity()`, `operator()`, `difference()`, `compute_difference()`,
  `shift_cost()`.
- Depends on `aurora_internal/aurora_constraint_manifold_patched.py` for
  `Constraint` (IntEnum), `ConstraintVector`, `ManifoldViolation`.
- Live consumer: `aurora_internal/aurora_evolution_chamber.py`
  (`EvolutionaryChamber.tick()` — confirmed the real, ticking loop via
  `run_chain.py`), plus `aurora_leverage_scalar.py`, `aurora_energy_layer_costs.py`,
  `aurora_entropy_detector.py`, `aurora_cost_diff_score.py`,
  `aurora_difference_buffer.py`, `aurora_dna_strand_schema.py`,
  `aurora_worth_evaluator.py`, `aurora_variant_promotion.py`,
  `aurora_solidification.py`, `aurora_intake_metabolism.py`,
  `aurora_closure_basis.py`, `aurora_sedimemory.py`,
  `aurora_reflexive_interpreter.py`, `aurora_noncomp_layer_compiler.py`,
  `aurora_ontological_scaffolding.py`, `aurora_metabolic_distiller.py`,
  `aurora_runtime.py`, and `aurora.py` (via a deferred/local import only).

### System B — a second, independently authored engine
- `aurora_constraint_engine.py` (2,280 lines, repo root) independently
  **redefines its own** `ConstraintVector`, `ManifoldViolation`,
  `NonCompDimension` (a plain string-valued `enum.Enum` — a different class
  from the registry's `IntEnum`), `EnergyLaw`, `MagnitudeImpact`,
  `PrimitiveOperator`, `RuntimeGovernor`, `ConstraintEngine`, `EngineRuntime`.
- Live consumer set: `aurora_interaction_engine.py`,
  `aurora_interaction_processing.py`, `aurora_hardware_io.py`,
  `aurora_expression_perception.py`, `aurora_dream_trainer.py`,
  `aurora_live_vision.py`, `aurora_response_teacher.py`,
  `aurora_image_ingestion.py`, `aurora_internal/aurora_runtime_constraint_governor.py`,
  `aurora_internal/aurora_conversation_episode_compiler.py`,
  `tensor_occupancy_hook.py`, `aurora_constraint_manifold_compiler.py`,
  `aurora_constraint_manifold.py` (a different, unpatched file from
  `aurora_internal/aurora_constraint_manifold_patched.py`), and
  `foundational_contract.py` (deferred import).

**These two `ManifoldViolation` classes are not the same class.** Code that
catches one will not catch the other. **These two `NonCompDimension` enums
are not the same enum.** A value from one is not equal to, nor
interchangeable with, a value from the other.

Because System B owns every consumer that touches perception, interaction,
hardware I/O, and expression — i.e. exactly the transitions the directive's
§3 lists first ("external observation received," "expression emitted,"
"environmental action performed") — the entire external-facing half of
Aurora's runtime is physically governed by a copy of the physics that the
canonical registry, its own tests, and its own verification function
(`verify_noncomp_registry()`) know nothing about.

### It gets worse: System B's own consumers frequently don't call System B either

For several of System B's named consumers (`aurora_interaction_engine.py`,
`aurora_hardware_io.py`), grep confirms **zero call sites** for
`RuntimeGovernor(`, `ConstraintEngine(`, or `.govern()`. These files import
only inert dataclasses (`ConstraintVector`, `GovernorWeights`,
`ExistenceMode`) and never invoke the engine that is supposed to gate
anything. So for large parts of the live surface, the correct description
isn't "the wrong physics runs" — it's "no physics runs; only its data types
are borrowed for shape."

### A duplicated unverified formula

`aurora_internal/aurora_noncomp_registry.py` (lines 154–197) carries an
explicit, pre-existing flag: the shipped `Magnitude = (B×T×X)/N` formula was
authored under a mapping later corrected (Build 725: X→MAGNITUDE, not
B→MAGNITUDE) and is marked "unverified... do not blindly retain." This
audit found that `aurora_constraint_engine.py`'s `MagnitudeImpact.magnitude()`
(line ~143) **independently hardcodes the exact same formula**. Correcting
the registry's copy — the fix implied by the directive's §5.2 — would not
touch System B's copy at all.

---

## 2. Per-Channel Audit

Format per the directive's §22. **Result** reflects whether an applicable
realized transition can be shown, with concrete evidence, to bypass the
channel's physics — not whether the channel is defined, tested, or
documented.

### X — Existence

| Dim | Physical invariant | Canonical implementation(s) | Applicable transition | Enforcement boundary | Known bypass | Root cause | Result |
|---|---|---|---|---|---|---|---|
| POLARITY | is/isn't; phase_neutral=π/2, flip_threshold=0.35 | Registry: `POLARITY_PARAMS[X]` (`aurora_noncomp_registry.py:437`); Engine: `IStatePredicate.I_IS/I_ISNT` (`aurora_constraint_engine.py:277`) | Any is/isn't assertion on a new occurrence | Only if an `OntologicalClaim`/`IStatePredicate` is actually constructed | Real ingestion paths (`aurora_image_ingestion.py:422-428`, `aurora_live_vision.py:571-629`) never construct one | No physics object created on admission at all | **FAIL** |
| MAGNITUDE | X is the magnitude primitive (corrected mapping) | Registry field-magnitude logic; Engine `ConstraintVector.magnitude()` — duplicate of the flagged unverified formula | Any magnitude computation | Only runs if a vector exists | `constraint_profile()` in ingestion modules builds a vector **post-hoc from counters**, not from an admissibility computation (`aurora_image_ingestion.py:354`) | Duplicate formula (System B) + never invoked pre-admission | **FAIL** |
| OPERATOR | "If X≤0 the manifold collapses" | `OPERATOR_PARAMS[X]` (`aurora_noncomp_registry.py:505`); mechanically enforced via `ConstraintVector.__init__` guards in **both** systems (`aurora_constraint_manifold_patched.py:113`, `aurora_constraint_engine.py:49`) | Every representation event | Only fires if a `ConstraintVector` is constructed | Ingestion never constructs one for the admitted item | Gate is correct but structurally unreachable | **FAIL** (unreachable, not incorrect) |
| COST | Cheapest layer: baseline=1.0, coeff=1.0 | `LAYER_COST[X]` (`aurora_noncomp_registry.py:239`) — System B has no equivalent | Any X-shift | `REGISTRY.shift_cost()`, System A only | Perception pipeline runs entirely on System B, which has no X-cost concept | Parallel-universe: feature exists only in the system perception never imports | **FAIL** |
| DIFFERENCE | unsigned, prior_self, 1-tick window | `DIFFERENCE_PARAMS[X]` (`:340`) — registry only | Tick-over-tick drift | `REGISTRY.compute_difference()` | No System B consumer calls it; System B has no X-Difference concept | Same as COST | **FAIL** |

### T — Time

| Dim | Physical invariant | Canonical implementation(s) | Applicable transition | Enforcement boundary | Known bypass | Root cause | Result |
|---|---|---|---|---|---|---|---|
| POLARITY | can/can't, flip_threshold=0.42 | `PolarityParams` (`aurora_noncomp_registry.py:444`) | I-state assertions | Registry consumers only | System B's separate `NonCompDimension`/engine never references it | Parallel-universe | **FAIL** |
| MAGNITUDE | T is the propagation-multiplier term | `MAGNITUDE_NUMERATOR_AXES` (`:173`) | Magnitude computation | Registry consumers only | Same disconnection; `surface_profile` boot path leaves `chamber`/`genealogy` as `None` (`aurora.py:29537`), so no chamber exists to compute it | Parallel-universe + a surface-mode skip | **FAIL** |
| OPERATOR | "every sequence-step advances... nothing can un-tick" | `OperatorParams` (`:515`); enforced via `check_T` (`aurora_evolution_chamber.py:441`) | Every tick | Only when `chamber.tick()` runs | `aurora.py:34461-34469` contains an explicit comment admitting `chamber.tick()` was **never called in the live runtime** until a recent patch; it is now gated behind a 15-30s cadence (`aurora_runtime_constraint_governor.py:209`), unrelated to real conversational turns | Historically dead call site, now throttled rather than transition-driven | **FAIL** |
| COST | coeff=7.0, leverage_sign=-1 | `LAYER_COST[T]` (`:246`) | T-shift | Registry only | System B has no cost accounting on this table at all | Parallel-universe | **FAIL** |
| DIFFERENCE | signed, prior_self, 4-tick window (momentum) | `DifferenceParams` (`:354`) | Tick-over-tick momentum | Needs real `tick_count` history | `tick_state.json` is written on every flush (`constraint_genealogy.py:2967`) but its sole reader, `restore_tick_state()` (`:2985`), **has zero callers anywhere in the repo** — `tick_count` silently resets to 0 on every live restart while entities are still treated as continuous | Write-without-read persistence bug | **FAIL** — a genuine local defect, independent of the parallel-universe issue |

Also found: **at least three independent tick counters** that can drift
apart — `EvolutionaryChamber.tick_count`, `ConstraintGenealogyLogger.tick_count`
(a separate counter `aurora.py` reads directly, `aurora.py:18149`), and
per-instance `ToroidalVertexSystem` phase clocks (~10 independently
instantiated lattices across `aurora.py`, `aurora_consciousness_engine.py`,
`run_aurora.py`, `aurora_behavioral_identity.py`, `aurora_i_state_beings.py`).

### N — Energy

| Dim | Physical invariant | Canonical implementation(s) | Applicable transition | Enforcement boundary | Known bypass | Root cause | Result |
|---|---|---|---|---|---|---|---|
| POLARITY | do/don't, flip_threshold=0.50 | `PolarityParams` (`:451`) — single source | Phase→I-state mapping | Registry accessor only | None found | — | **PASS** |
| MAGNITUDE | N is the cost-normalization denominator | Engine `MagnitudeImpact.magnitude()` (`:143`) vs. registry leverage math (`leverage_sign=0`, `:258`) — two disconnected definitions | Any magnitude shift | System A: `LayerEnergyAccountant.apply_shift()` can reject; System B: nothing | `EvolutionaryChamber.tick()` never imports `LayerEnergyAccountant` at all — an explicit comment (`aurora_evolution_chamber.py:1321-1324`) says magnitudes are approximated from IVM pressure "without a full LayerEnergyAccountant" | The real enforcement class exists but the live loop deliberately bypasses it | **FAIL** |
| OPERATOR | "total system energy... neither created nor destroyed within a closed tick" — the *only* conserved channel | `is_conserved=True` (`:536`) vs. Engine `EnergyLaw` (`:109-133`) | Every redistribution | Nothing wired: `EnergyLaw.conserved()` has **zero callers in the repo** | `EnergyLaw.redistribute()` (`:128-131`) adds the *full* delta to all axes **before** flooring N at 0, so when `gain > vec.N` the deficit is silently discarded rather than clawed back — energy is created from nothing. Traced concretely: `vec=(X=1,T=0.1,N=0.05,B=0.1,A=0.1)` + `delta=(T=+0.3,B=+0.2)` → total energy rises from 1.35 to 1.8. `redistribute()` itself has exactly one caller in the entire repo: its own self-test | Subtract-after-add ordering bug + a conservation check that is dead code | **FAIL** |
| COST | coeff=10.0, baseline=6.0 | `shift_cost()`/`baseline_tick_cost()` (`:667,677`), enforced by `LayerEnergyAccountant.apply_shift()` (`aurora_energy_layer_costs.py:426`, real reject path) | Per-tick maintenance tax | Real reject logic exists but only in satellite modules (`aurora_variant_promotion.py:73`, `aurora_solidification.py:71`, `aurora_leverage_scalar.py:117`, etc.), each with its **own independently-seeded** accountant, not a persistent budget shared with the live chamber | `EvolutionaryChamber.tick()` never instantiates `LayerEnergyAccountant` | Enforcement class and live tick loop are architecturally separate code paths | **FAIL** |
| DIFFERENCE | signed, peer_mean, 4-tick window | `DifferenceParams` (`:369`) — sole implementation | Tick-to-tick relative spend | Registry-only, feeds difference buffer | None found | — | **PASS** |

**N is the one hard conservation law the entire architecture claims to
have, and it is not enforced anywhere in the live execution path.**

### B — Boundary

| Dim | Physical invariant | Canonical implementation(s) | Applicable transition | Enforcement boundary | Known bypass | Root cause | Result |
|---|---|---|---|---|---|---|---|
| POLARITY | saw/saunt, deep layer resists flip (0.65) | `PolarityParams` (`:458`) — System B has no B-polarity concept | Phase flip | None calls `.polarity(B)` to gate a flip | No flip-rejection call site found anywhere | Computed, never wired to a guard | **FAIL** |
| MAGNITUDE | boundary expands/contracts continuously | Registry cost/operator (`:260,538`); Engine `BoundaryCalibrationGuard` (`aurora_constraint_engine.py:1081`) | Continuous shift | Guard is computed but `ConstraintEngine.govern()` (`:1230`) **never consults `self._guards`** — documented as diagnostics-only (`:1239`) | Guard failures cannot reject a task | Guard wired to telemetry, not the permission path | **FAIL** |
| OPERATOR | "boundaries can expand or contract but not dissolve without cost" | Registry (`:538`) vs. Engine's thin scalar guard | Structural change | `feed_evidence()` (`:1200-1228`) updates the boundary guard **without ever passing `boundary_pressure`** — it silently defaults to 0.0 (`:1095`), so the dissolution check can never fire | Same inert-guard defect, compounded by an unpopulated input | **FAIL** |
| COST | expensive, coeff=40.0 | `shift_cost()` (`:677`); the one gate that could enforce it, `can_afford_shift()` (`aurora_energy_layer_costs.py:143`), **has zero callers anywhere in the codebase** | Any B magnitude delta | None — dead in both systems | Cost is computed only for retrospective genealogy/worth scoring (`aurora_dna_strand_schema.py:130-132`), never as a precondition | Enforcement primitive built, never wired | **FAIL** — merges/dissolves are effectively free |
| DIFFERENCE | unsigned, background reference | `DifferenceParams` (`:383`) — System A only | Drift from resting topology | Feeds `aurora_difference_buffer.py`/`aurora_cost_diff_score.py`, still not a hard gate | System B has no B-Difference concept at all | Parallel-universe (System B) + soft-only enforcement (System A) | **FAIL** |

Separately: the "representational conservation" machinery from the prior
Communication Architecture Repair Directive (`aurora_proposition_frame.py`,
`aurora_constraint_semantic_continuity.py`) is called from only **7 of
roughly 22+** representation-producing/transforming modules — all in System
A's language-generation path. It has **zero reach** into System B's
perception/interaction/expression pipeline. The one apparent bridge
(`aurora_expression_perception.py` holding a `self._proposition_frame`) uses
the frame only for word/motif selection in generated text, never for
boundary-cost accounting or entity-merge gating.

### A — Agency

| Dim | Physical invariant | Canonical implementation(s) | Applicable transition | Enforcement boundary | Known bypass | Root cause | Result |
|---|---|---|---|---|---|---|---|
| POLARITY | did/didn't (authored vs. not) | Registry `leverage_sign=+1`; System B has no did/didn't semantics on `ConstraintVector.A` (a raw float) | Authored-change assertion | Registry consumers only | `aurora_interaction_engine.py`/`aurora_hardware_io.py` never reference the registry | Two unrelated A representations | **FAIL** |
| MAGNITUDE | bounded authored-change size | `check_A` ceiling (`aurora_evolution_chamber.py:460`, real ceiling=5.0) vs. Engine `MagnitudeImpact.magnitude()` | Any agency-magnitude change | Neither is wired into production | **`check_A(` has zero callers anywhere in the repo**, confirmed by grep — it is dead code despite being fully implemented with a real precondition | Gate defined, never called from the action path | **FAIL** |
| OPERATOR | "agency without energy allocation is incoherent" | System B: `RuntimeGovernor.govern()` (`:611-683`) | Action authorization | Governor exists but... | ...`RuntimeGovernor.govern()` is a **static-weight lookup** (`GovernorWeights.A=0.53` vs. a fixed `_DEFERRAL_THRESHOLD=0.60`) — no `magnitude`, `energy_available`, or per-call vector data ever enters the decision. And `aurora_interaction_engine.py`/`aurora_hardware_io.py` **never call `.govern()` at all** — zero grep matches | Governor built as a constant lookup table, then bypassed entirely by its named consumers | **FAIL** |
| COST | quadratic cost `k · magnitude²` charged before authorization | `check_A`'s cost formula (dead, see MAGNITUDE row) and Engine's `EnergyLaw`/`MagnitudeImpact` (`:1654-1662`, self-test only) | Every authored action | None — cost logic is authored in both systems, executed in neither | `GovernorResult` (PERMITTED/DEFERRED) never charges energy (`:669-683`) | Cost logic written, wiring never completed | **FAIL** |
| DIFFERENCE | signed, prior_self, 8-tick window — authored delta traceable through consequences | Registry `compute_difference()`; comm-only `aurora_attribution_trace.py` (`_ENABLED=False` by default, `:23`) | Any authored transition | Confined to generated-sentence composition when explicitly enabled (default off) | `aurora_hardware_io.py` has **zero** references to contributor/attribution/causal_generation — authorship is untracked for any non-communication agency (memory writes, hardware actions) | Attribution scoped to communication only, by design, never extended | **FAIL** |

**For constraint A, there is no live enforcement boundary anywhere in the
codebase.** The one real, correctly-implemented cost/ceiling gate
(`check_A`) is unreachable dead code; the live authorization path
(`RuntimeGovernor`) is a hardcoded constant table with no cost concept; and
its two named production consumers don't invoke even that.

---

## 3. Tally

| Constraint | PASS | FAIL |
|---|---|---|
| X | 0 | 5 |
| T | 0 | 5 |
| N | 2 | 3 |
| B | 0 | 5 |
| A | 0 | 5 |
| **Total** | **2 / 25** | **23 / 25** |

The two passes (N:POLARITY, N:DIFFERENCE) share a common shape: both are
pure registry accessors with no downstream enforcement consumer to bypass —
they pass because nothing yet depends on them being enforced, not because
enforcement was proven robust under load. That's a real pass by the
directive's §22 standard, but a narrow one.

---

## 4. Recommended Repair Order (proposal — not yet actioned)

Per the directive's §26, the evidence points to a small number of
high-leverage repairs rather than 23 independent patches:

1. **Collapse System B into System A.** Make `aurora_constraint_engine.py`
   import `ConstraintVector`, `ManifoldViolation`, and `NonCompDimension`
   from the canonical registry/manifold modules instead of redefining them.
   This alone would make every "parallel-universe" FAIL above at least
   structurally reachable from a single source of truth.
2. **Wire `ConstraintEngine.govern()` to its own guards** (`self._guards`)
   and to real per-call cost (`REGISTRY.shift_cost()`), replacing the
   static-weight lookup — closes most of B and A's OPERATOR/COST failures.
3. **Fix `EvolutionaryChamber.tick()` to use `LayerEnergyAccountant`**
   instead of the IVM-pressure proxy — closes N's OPERATOR/COST failures,
   the one channel the whole system calls a hard law.
4. **Wire `restore_tick_state()` into the real boot path** — closes T's
   restart-continuity defect.
5. **Give sensory ingestion a real admission gate** (construct and check a
   `ConstraintVector` before data enters `self._vectors`/`self._scene_log`)
   — closes X's "no physics touched at all" bypass class.
6. **Extend or replace the representational-conservation calls** so System
   B's producers are covered, not just System A's language path.
7. **Wire `check_A` into the actual action-selection call site.**

Items 1–3 are the ones most likely to collapse multiple FAILs at once, per
the directive's own completion criterion in §26 ("if ten separate defects
disappear because one foundational invariant became real, that is evidence
the repair is occurring at the correct layer").

This audit makes no code changes. Next step, per plan: work through the
5×5 grid in whatever order is chosen, verifying each fix against a real
bypass test before marking it closed.
