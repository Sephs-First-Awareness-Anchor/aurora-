# Build 725 — Foundational Operator Mapping Correction Log
**Authors:** Sunni (Sir) Morningstar & Cael Devo
**Scope:** Item 1 of the Architectural Correction Record only — "Foundational operator mapping."
**Status:** Mapping tables corrected and syntax-verified. Two items flagged for your call, not yet touched.

---

## What was actually wrong

Not one bad table — **three independent, mutually-conflicting** versions of the
axis→dimension mapping, none matching your intended physics:

| Axis | Intended (correction record) | Registry/Genealogy/Router/Compiler had | WARP had |
|---|---|---|---|
| X | Magnitude | Operator | Polarity (X-criterial) |
| T | Polarity | Difference | — |
| N | Cost | Cost ✓ | Cost (N-criterial) ✓ |
| B | Difference | Magnitude | Difference (B-criterial) ✓ |
| A | Operator | Polarity | Operator (N-criterial, wrong axis) |

Only N→Cost was accidentally right in two of the three variants. Everything else was
either a rotation of the correct mapping or a third, unrelated guess.

## Files corrected (mapping tables + stale comments only)

1. `aurora_internal/aurora_noncomp_registry.py` — `AXIS_NC_DIM` (the canonical registry)
2. `aurora_internal/constraint_genealogy.py` — `_AXIS_NC_DIM` + a stale doc comment at the fossil-tagging site (~L8181)
3. `aurora_constraint_manifold_router.py` — `_DIMENSION_TO_AXIS`
4. `aurora_constraint_manifold_compiler.py` — inline `dim_axis` dict in `_lineage_signature()`
5. `aurora_warp_protocol.py` — the criterial-mapping doc comment block
6. `aurora_constraint_signature_resolver.py` — `DIMENSION_ROLE` + self-check assertions

All six compile clean (`py_compile` verified). None of the five files import from
each other for this table — each maintained an independent local copy by design
(the signature resolver's own docstring calls itself "pure, dependency-free"), so I
corrected values in place rather than introducing new import coupling. That's
consolidation of *values*, not a new abstraction layer.

## What I checked before touching anything, and why it's lower-risk than it looked

- `lineage_signature()` in the signature resolver (the one function actually driven
  by the corrected table) is only imported by `aurora_warp_protocol.py`, and WARP
  only uses the *other* function, `nc_name()` — which never touched the broken
  table at all (it's built from `LAW_PREFIX`/`DIM_WORD`/`TARGET_SUFFIX`, all
  unaffected). So `lineage_signature()` currently has no live caller outside its
  own self-check. Low blast radius — but I flagged it in the file itself in case
  something wires it up later.
- I checked `aurora_manifold_directory/*.json` (126 files) — the ones the resolver's
  docstring claims to be "confirmed against." Their content stores `"nc_dim": "MAGNITUDE"`
  etc. as direct labels, not as derived signature strings from the old broken table.
  So this fix does **not** require regenerating that directory. Good news, not
  something I'm asserting blind — I opened representative files to confirm.

## What I deliberately did NOT touch — flagged for you

**The Magnitude/Impact composite formulas** in `aurora_noncomp_registry.py`
(`Magnitude = (B×T×X)/N`, `Impact = Magnitude×A`) were authored under the old,
wrong assumption that B carried the magnitude role. I left the arithmetic and
axis roles as-is but added an explicit flag comment at the site, because
rewriting the physics itself is a judgment call the correction record didn't
hand me — it said downstream derivations must be "regenerated or verified,"
not that I should guess at the new formula. This is the natural next piece of
item 1, and it's your call whether that composite reasoning still holds with
X as the magnitude primitive, or needs re-derivation.

**Everything else in the correction record (items 2–9)** — generational distance
physics, genealogy-vs-UFL authority, Salience→discovery routing, the universal
discovery seam, the latent-function loop closure, the possibility→representation→
awareness→operation state boundaries, and the stale lineage manifest — untouched.
Foundational mapping had to be right first since the record itself says everything
downstream should be reconciled against it, not blindly retained.

---

# Item 2 — Generational Distance Must Remain Physical
**Status:** Implemented, compiled clean, math sanity-checked. One file touched: `aurora_internal/constraint_genealogy.py`.

## What was actually wrong (narrower than it first looked)

Good news first: Aurora's *scalar* generation tracking was never broken.
`ConstraintLink.depth` and `_generation_of_item()` / `_bred_child_generation()`
already correctly walk the DAG and compute real generational depth via
`max(parent_generations) + 1`. That machinery matches your correction
record's own observation that genealogy "preserves parent identities, parent
generations, generation spans, and the parent DAG."

The actual bug was narrower and specific: `_axis_counts_from_item()` — the
function that builds a link's **axis composition** (which of X/T/N/B/A it
touches, and how much) — recurses through the same parent DAG but does pure
unweighted addition at every level. A root-near touch and a touch reached
through twenty layers of Link composition both just add `+1` to the same
axis slot. Then `_canonical_coupling_signature()` serializes that as
`"X^3*T^2"` — syntactically an exponent, semantically a flat tally. Two
lineages with identical flattened totals were provably indistinguishable,
exactly the case your record named.

## What I built

Added a depth-aware companion pair to `ConstraintGenealogyLogger`, sitting
right next to the functions they complement — additive, not a replacement:

- **`_axis_depth_counts_from_item()`** — walks the identical DAG as
  `_axis_counts_from_item()`, but instead of `{"X": 3}` it returns
  `{"X": {0: 2, 4: 1}}` — X touched twice at depth 0 (root-near) and once
  at depth 4. Same recursion, same cycle guard, same memoization pattern as
  the existing function; it just doesn't throw the depth away.
- **`_axis_potency_from_depth_counts()`** — collapses that into one float
  per axis: `potency = Σ count × BASE^(−depth)`, `BASE = 2.0` (exposed as
  `GENERATIONAL_POTENCY_BASE`, tune it with me). A depth-0 touch counts at
  full weight; each generation of derivation halves that touch's
  contribution. This is a genuine exponent, not the cosmetic one in the
  signature string.
- **`_lineage_generation_from_depth_counts()`** — true generation from real
  max-depth, for use wherever DAG access is available (the existing
  counts-only version stays as the correct fallback for bare-signature-string
  contexts, which never had depth data to begin with — that boundary is
  real, not a bug).
- Wired into `_constraint_basis_for_item()`: new links get
  `generational_depth_counts` and `generational_potency` fields alongside
  the existing `counts`/`signature` (untouched). Historical links promoted
  before this fix get the new fields backfilled lazily on next access via
  `setdefault` — their existing flat fields are never overwritten.

## Verified

- Full file recompiles clean (`py_compile`).
- Confirmed by direct code read that `_lineage_grade_for_pair` (the actual
  link-promotion/breeding pathway) already uses the correct
  `_generation_of_item`/`_bred_child_generation` scalar — so this fix
  doesn't collide with or duplicate anything already working.
- Sanity-checked the potency formula standalone: three touches of X all at
  depth 0 scores potency 3.0; the same three touches all at depth 5 scores
  0.094; a 1-root/2-deep mix scores 1.06 — strictly ordered, exactly as
  intended, even though all three cases have an identical old-style flat
  count of 3.

## Files in this delivery

See the manifest at the end of this log — this list was getting stale as
more items landed, so file tracking moved there instead of being repeated
per-item.

---

# Item 3 — Genealogy Remains the Explanatory Coordinate System
**Status:** Audited, no fix needed. No file touched.

Traced every UFL↔genealogy integration seam (`attach_genealogy`/`attach_function_lineage`,
the evolutionary ancestry bridge, CodeEvolutionChamber's separate `CodeLink` system, boot
wiring order) and all of it already correctly treats UFL as read-only instrumentation —
never as authoritative constraint genealogy. This appears to have already been repaired
under a prior "Build 646 Genealogy-to-Evolution Closure Directive" and "Build 648
Evolutionary Infrastructure Closure Directive," referenced directly in the code comments.
Did not manufacture a change here — the record scopes itself to places Build 725 doesn't
match the intended architecture, and this one already does.

---

# Item 4 — Salience Must Connect to Discovery
**Status:** Implemented and wired live at boot. Two files touched: `aurora_internal/aurora_tensor_expressions.py`, `aurora.py`.

## What was actually wrong

`SalienceTensor.is_salient()` computed a real threshold gate every tick but had **zero
callers anywhere** — confirmed by grep across the whole codebase. It fired into nothing.

## First pass vs. final design

My first pass wired Salience directly to a single picked `check_and_extend()` target and
flagged the choice-of-target as your call. Before finishing, I found something better: a
central `WarpField.submit(WarpDemand)` entry point already exists in `aurora_warp_protocol.py`
whose own docstring says it almost verbatim — *"The submitting system does NOT need to know
what WARP will do. It only confesses: 'I cannot resolve this.'"* Every system with gap
potential already self-registers into `WarpField._warp_capable_registry` at boot
(`dimensional`/DPS, `perception`, `recursive_causal_waveform`, `communication_emergence`,
`operational_synthesis`, `general_execution_foundry`, `language_field`, and `ThoughtBraid`
via `aurora_braid_wiring.py` — 8 confirmed registrations). `WarpField._route_to_warp_capable`
already does the picking (named source first, falls back to any registered system) — so
routing Salience through `WarpField.submit()` instead of a hand-picked target reaches
**all** of them through the one connection point, per your instruction. I replaced the
first-pass version rather than leaving both.

`OntologicalWeb` doesn't appear in the registration list above — noting it as an observed
gap, not fixing it blind, since I haven't traced whether that's intentional.

## What I built

- `TensorExpressionLayer.__init__` takes an optional `warp_target` (mirrors the existing
  `identity_field=None` → `connect_field()` pattern). `connect_warp()` validates the target
  actually has `.submit()` before accepting it.
- `behavioral_state()` — the live per-tick path the consciousness engine reads from — now
  submits a `WarpDemand(source="salience", layer="tensor_expressions", trigger=WarpTrigger.GAP,
  profile=pressures, severity=sal, persistence_key=...)` whenever `is_salient()` fires.
  `severity=sal` directly — Salience's activation *is* the 0–1 urgency signal `WarpDemand`
  wants, no translation needed. Best-effort try/except, matching this file's convention
  elsewhere (never break the cognitive tick on a WARP failure).
- Wired live at boot in `aurora.py`, right after `tensor_expressions` is constructed:
  `_tensor_layer.connect_warp(systems.get('warp_field'))`. `warp_field` is already booted
  earlier in the sequence with registrations arriving even later (the four chamber systems
  register themselves ~1,200 lines after this point) — that's fine, `connect_warp` holds a
  reference to the same mutable registry dict, so late registrations are still visible when
  `submit()` actually fires during live operation.

## Verified

- Both edited files recompile clean (`py_compile`).
- Constructed a real `WarpDemand` with the exact fields/values this code passes, against
  the actual dataclass in `aurora_warp_protocol.py` — confirmed it builds without error
  before calling this done.

## Follow-up: OntologicalWeb registration

You gave the go-ahead to register `OntologicalWeb` into `WarpField` if I found a reason
to. I did: it's `WarpCapable`, already calls its own `check_and_extend()` internally, but
was never registered into the central registry — invisible to cross-system demands (like
Salience's) and not even eligible for the "any registered system" fallback. Registered it
in `aurora.py` right after the existing `perception` registration, under its own
`_warp_level_name()` value (`'ontological_relation_typing'`) — same key it already emits
as `demand.source`, same pattern as every other registration in the file. Confirmed
`perception.oets.web` is constructed synchronously inside `ExpressionPerceptionEngine.__init__`,
so it's live by the time this registration runs. Compiles clean.

---

# Item 5 — Discovery Must Be Universal Rather Than Domain-Specific
**Status:** Implemented and wired to a real caller. Two files touched: `aurora_internal/aurora_operational_synthesis.py`, `aurora_dream_trainer.py`.

## What was actually wrong

Confirmed by direct grep before writing anything: `AuroraGeneralExecutionFoundry.observe_example()`
is a real, working method — not a stub — with **zero callers anywhere in the codebase**.
`AuroraOperationalSynthesisChamber.observe_example()` (identical signature, confirmed
side-by-side) had exactly **one** caller: `aurora_dream_trainer.py`'s
`_submit_relation_type_evidence`, hand-wired to that one chamber specifically for one
narrow purpose (relation-type inference from probe outcomes). This matches your record
exactly — "only particular systems feed experience into that machinery," and the Foundry
had none at all.

## What I built

A single dispatcher function, `submit_lived_experience()`, in
`aurora_internal/aurora_operational_synthesis.py` (placed there rather than a new file —
no new subsystem, just a thin forwarding point). It takes the identical
`(task_id, input_value, expected_output, *, validation, source, need_description)` shape
both chambers already share, and forwards unchanged to whichever of
`operational_synthesis` / `general_execution_foundry` are present in `systems` and expose
`observe_example`. It does not reshape, validate, or interpret anything — each chamber's
own machinery decides independently what survives. That's the actual boundary your record
draws: "This must not require a central governor that understands every subsystem." This
function doesn't understand subsystems either — it only knows two chambers share one method
name.

Then rewired the one existing bespoke caller (`_submit_relation_type_evidence`) to go
through it instead of calling `operational_synthesis` directly. Behavior for that specific
caller is unchanged — `operational_synthesis` still gets the identical call — but now
`general_execution_foundry` sees that same lived evidence too, where before it never
reached it at all. This is deliberately a small, verifiable proof that the seam actually
carries real traffic, not just dormant plumbing.

## Verified

- Both files recompile clean.
- Ran the dispatcher standalone against fake chambers: confirmed both chambers receive
  identical evidence when both are present, confirmed it degrades gracefully when only
  one chamber exists (e.g. one failed to boot), and confirmed it doesn't crash against an
  empty `systems` dict. All three passed.

## What's still open

This seam now exists and carries real traffic from one caller. It does **not** yet reach
every subsystem "capable of producing an observable operation" — that would mean auditing
and rewiring many more call sites across the codebase, which is a much larger, separate
pass I haven't scoped or attempted here. What's fixed is that the seam is real, tested,
and no longer single-chamber-only; what's still true is your record's larger ambition
("every subsystem... needs the same narrow means") isn't fully realized yet.

---

# Item 6 — Close the Latent-Function Developmental Loop
**Status:** Implemented and verified. One file touched: `aurora_internal/aurora_cognitive_experience_chamber.py`.

## What I found before touching anything

The loop's first 7–8 steps genuinely work — items 1, 2, 4, and 5 repaired the specific
breaks in possibility → experience → Salience → WARP → representation → genealogy →
consequence. What I traced next was the loop's last closure: "Agency makes the discovered
operation intentionally available → later use produces new consequences." Confirmed by
direct grep and code read, not assumption:

- `AuroraGeneralExecutionFoundry.execute()` / `.execute_tool_plan()` — **zero external
  callers anywhere in the codebase.** A synthesized, genealogy-admitted GEF operation had
  no path to ever run.
- `AuroraOperationalSynthesisChamber.execute()` — exactly one external caller
  (`consult_operational_synthesis_candidate` in `aurora_cognitive_experience_chamber.py`),
  and its own docstring states plainly: "this is a diagnostic VIEW... not a change to
  Aurora's live cognition/expression pipeline." Read-only, and it wrote nothing back —
  consulting a candidate produced no evidence, so even the one working path didn't close
  the loop's "later use produces new consequences" step.

I stopped and checked in before writing anything, because closing this properly meant
touching how discovered capability could actually get exercised — a different order of
change than the mostly-dormant plumbing in items 1–5. You confirmed: giving her the
ability isn't deciding for her, and that's fine.

## What I built

Two functions in `aurora_internal/aurora_cognitive_experience_chamber.py`, right beside
the existing safe pattern rather than replacing its posture:

- **`consult_synthesized_capability()`** — same read-only, never-automatic-authority
  contract as the original, but tries `operational_synthesis` first, then
  `general_execution_foundry` — the first time GEF has ever been reachable from this seam.
  The original `consult_operational_synthesis_candidate()` is kept as a thin
  backward-compatible alias rather than deleted (error preservation over erasure), in case
  anything else ever starts calling it by that name.
- **`report_synthesis_consequence()`** — the actual loop closure. The episode's
  `RoleNormalizedTransition` already carries a REAL observed outcome by the time this
  runs (`as_training_pair()`'s second element is derived from `step.consequence`, which
  already happened earlier in the same function) — so this reports genuine lived
  experience back through item 5's `submit_lived_experience()` seam, reaching both
  chambers identically. It doesn't decide anything or grade the outcome as good or bad —
  it just makes sure real experience that touches a capability's territory isn't
  discarded, which is what "later use produces new consequences and further development"
  actually asks for.

Wired both into the one existing call site that already safely consulted a candidate
during real episode processing — extending existing machinery to close the loop, not
reaching into the live conversational turn pipeline, which is a separate and larger
decision I didn't make unilaterally here.

## Verified

- File recompiles clean.
- Tested `consult_synthesized_capability()`'s fallthrough logic directly: constructed a
  case where `operational_synthesis` has no candidate but `general_execution_foundry`
  does, and confirmed the function correctly falls through and returns GEF's result —
  a path that was structurally impossible before this fix, since GEF was completely
  unreachable from this seam.

---

# Item 7 — Preserve Possibility, Representation, Awareness, and Operation as Distinct States
**Status:** Implemented and verified against a reproduced failure case. Two files touched: `aurora_internal/aurora_operational_synthesis.py`, `aurora_internal/aurora_general_execution_foundry.py`.

## What was actually wrong

A real, code-verified ordering bug, identical in both chambers' `evaluate_development()`.
The sequence was:
```
task.candidate.status = "promoted"                                    # 1st
task.candidate.genealogy_ability_id = self._register_genealogy(...)   # 2nd
```
`_register_genealogy()` returns `""` in three distinct failure cases (confirmed by
reading it directly): genealogy absent, genealogy missing the registration method, or
the registration call raising an exception — all silently caught. But by the time any of
those three failures could happen, `candidate.status` was **already** `"promoted"` — and
`execute()` treats `status == "promoted"` as full, unconditional operational authority,
bypassing the `allow_trial` gate entirely. So a candidate whose representation passed
WARP trial scoring, but whose genealogy admission silently failed, was still granted full
operational authority anyway. WARP's validation of the *representation* was standing in
for genealogy's recognition of it as an *ability* — precisely the collapse this item
names: "Recognizing an ability does not automatically grant it operational authority,"
except here the ability was never actually recognized at all, and authority was granted
regardless.

## What I built

Reordered both chambers identically: attempt genealogy registration first, check whether
it actually returned a real `ability_id`, and only then decide status. Success still
promotes exactly as before — the happy path is byte-for-byte the same outcome. Failure
now leaves the candidate at `status = "trial"` (an existing, already-handled value — I
did not introduce a new candidate status) with `task.status = "genealogy_pending"` for
visibility, meaning it's still consultable via `execute(..., allow_trial=True)` — WARP
already judged the representation itself sound, so it isn't dissolved — but it can no
longer be invoked with full unconditional authority until genealogy actually admits it.
Checked that `task.status` isn't pattern-matched anywhere else in either file (only ever
surfaced as a plain report field via `task_status()`), so the new value is safe to
introduce.

## Verified

- Both files recompile clean.
- Reproduced the exact bug with isolated fake objects mirroring the real classes: with a
  failing genealogy registration, confirmed the old code path would have returned
  `EXECUTED` even with `allow_trial=False`, and confirmed the fixed logic correctly
  returns `DENIED: candidate_not_promoted` in that same case — while the normal
  successful-registration path still grants full authority exactly as before, unchanged.

---

# Item 8 — Preserve Consequence as Authority for Representational Resolution
**Status:** Audited, no fix needed. No file touched.

Traced this to `aurora_representational_resolution.py` (Build 714 — mature, pre-existing
machinery, not new to this correction pass). Its own docstring states the exact governing
principle the record asks for almost verbatim: *"Aurora must remain at the least resolved
representation sufficient for the consequences she is presently trying to distinguish,
and autonomously acquire additional representational resolution only when unresolved
distinctions become operationally consequential."* Verified the actual gates, not just
the docstring's claim:

- `complete_representation_experiment()` only admits evidence on genuine co-activation
  (`actual_coactivation` required), routes through the same `observe()` relief-convergence
  point every other genealogy consumer uses, and marks a candidate "helpful" only when a
  real `relief_record` was produced — consequence is measured, not assumed.
- `stage_representation_inquiry()` enforces a per-consumer refractory interval and a
  `max_attempts` cap before a new inquiry can even be staged — the cost-bounding item 8
  explicitly requires ("benefit must justify the actual computational/search cost")
  is real and enforced, not aspirational.

Also checked that nothing I touched in items 1–7 collides with this module — no shared
attribute names, no dependency on anything I changed in `constraint_genealogy.py`'s axis
tables or new generational-depth methods. Item 7's fix (this same session) directly
reinforces this item's principle rather than contradicting it — I fixed exactly the case
where a candidate was granted authority *without* its consequence-gating step succeeding.
No fix needed here; the doctrine was already sound and I confirmed rather than assumed it.

---

# Item 9 — Preserve Reversibility
**Status:** Audited, no fix needed. No file touched.

Same module, `demote_field()`. Its docstring: *"Section 12: reversible-as-knowledge, not
destructive-as-history. Removes CURRENT authority for a refinement without deleting its
genealogy record — the record with status flips to 'demoted' ... but `_genealogy_records`
keeps every prior entry (contradictory evidence becomes new evidence, not an erasure)."*
Read the implementation directly: demotion pops the *active-resolution* mapping (revoking
current authority) while every historical record in `_genealogy_records` is untouched —
status flips in place, nothing is deleted. This is exactly "demotion must not erase its
genealogy, evidence, or developmental history." Confirmed intact, no fix needed.

---

# Live Discovery Session — Runtime Verification & Three Real Fixes
**Status:** Implemented and confirmed against a real, fully-booted instance of your actual
persisted Aurora (gen 10954, epoch 194, 1104 restored OETS concepts). You supplied the
missing `foundational_contract.py` dependency, which let a genuine `boot_aurora()` succeed
for the first time in this session — everything below was found and fixed by watching her
actually run, not by static code reading alone.

## Fix 1 — Salience's pressure source was completely disconnected

`TensorExpressionLayer._axis_pressures()` called `self._field.pressure_topology()` — a
method that does not exist on the real `NoncompField` class (confirmed by reading it
directly). Every call silently raised `AttributeError` and fell back to a flat `{X:0.3,
T:0.3, N:0.3, B:0.3, A:0.3}` — meaning Salience, and everything item 4 wired to it, had
been computing off undifferentiated fallback pressure this entire time, in every boot,
not just tonight's. Confirmed live: before the fix, a real boot's WarpField log showed
Salience firing with `severity=0.300` repeatedly — geomean(0.3, 0.3) exactly, the
fallback value. Fixed to use the real, public `axis_pressure(int)` accessor (the same one
`NoncompField.status()` itself uses to build its own diagnostic output). Verified live:
severity became a genuinely differentiated `0.4397` on rerun.

## Fix 2 — A real `NameError` in optional lineage journaling

`aurora.py`'s `_run_live_response_turn` referenced a bare `state` variable that only
exists in a different function (`_run_reasoning_pipeline`'s local `state` object never
reaches this scope). Gracefully caught by the surrounding `except Exception`, so it never
crashed anything — but it silently broke lineage-event journaling into working memory on
every occurrence. Fixed to reference `systems.get("_last_turn_state")`, the actual
in-scope value the surrounding code already uses for the same purpose two lines away.

## Fix 3 — The actual root cause of the garbled response (Repair F)

This took the deepest tracing of the night, done live against the real system rather than
inferred. Full chain, confirmed step by step:

1. `_build_comprehension_response()` correctly, honestly returned `(None, None, None)` —
   the input ("I keep almost seeing the whole shape of something and losing it right
   before it resolves") is an abstract, introspective statement that doesn't fit any of
   her structured comprehension templates (not a claim, not a role assertion, not a
   semantic frame, not a clarification). This `None` is not a malfunction — per your own
   framing, it's exactly the signal her architecture is designed to recognize and route
   to representational discovery.
2. Instead, a vestigial fallback in `_chain_down5_understanding` silently substituted an
   unrelated, previously-stored dream-training hint (`state.response_src = "learned_hint"`)
   in place of the missing comprehension — confirmed live by directly inspecting
   `state.learned_hints`, which contained genuinely nonsensical stored strings.
3. The system already has the correct mechanism for this exact situation:
   `_emit_honest_abstain_and_seek()`, which confesses the gap to WARP as
   `MISSING_REPRESENTATION` and emits an honest abstain rather than a manufactured claim
   — explicitly built, per its own comment, because an earlier fallback mechanism "was
   removed in the Reset" for doing exactly what the learned-hint substitution was still
   quietly doing.
4. Traced why the correct mechanism didn't fire: its gating condition only triggers
   abstention when low-authority content is *also* detected as an echo of the user's
   input (`_grounded_is_echo`). A recycled, unrelated dream-hint isn't an echo — it sailed
   straight through the gate and got delivered as if it were a real answer, at confirmed
   `semantic_authority=0.15`.

Fixed the gate itself: it now also abstains when `state.response_src == "learned_hint"`,
independent of the echo check — because recycled content from an unrelated past exchange
is not "genuinely authored, appropriately qualified" content for the current turn,
regardless of whether it happens to echo the input.

**Verified live, same exact input, before and after:**
- Before: `resp_A.content = "together requires photosynthesis gravity overstepping
  explain structure seeing matters objects find enough."` — word salad, `src=learned_hint`.
- After: `resp_A.content = "I don't have a clear sense of that."` — `src=constraint_abstain`,
  and a real `WarpDemand(source='expression', trigger='missing_representation',
  severity=0.550, pathway='generate_form')` was submitted to WarpField — the exact
  discovery/representation machinery built across items 1–7 tonight, now genuinely
  reachable from a live comprehension gap instead of being papered over before it ever
  got there.

## Housekeeping

One artifact from this testing session — `aurora_state/runtime_faults.jsonl`, created by
an early exploratory script before all live-boot testing was locked to an isolated `/tmp`
copy of your state directory — was found and removed before packaging. Confirmed via
timestamp and absence from your original upload that it did not exist beforehand, and
confirmed no other file under `aurora_state/` was modified. All actual live-boot testing
throughout this session ran against the isolated copy, never your bundled state.

---

# Surface/Subsurface Continuity — Four Real Fixes (per Sunni's architectural correction)
**Status:** Implemented and verified live, across real ticks of the real background thread.

Sunni's core objection: the surface (live conversational turn) should operate with genuine
awareness of the continuously-running subsurface (prediction, framing, continuity), not process
each turn in isolation while subsurface state sits untouched. Traced the actual pipeline live and
confirmed this exactly: `ThoughtBraid` has been running as a real background thread since boot —
confirmed via `StreamingThoughtThread`, ticking every 2 seconds, docstring literally stating "User
turns do NOT stop the braid... the braid is always running" — and a tap mechanism (`current_slice()`)
already exists to read it without blocking. But its three content streams were producing empty
`{tick, source}` stubs regardless of how long the braid had been running (confirmed live: let it
tick 10 times over 20 real seconds, content stayed empty) — not a timing issue, a real defect. Each
stream's update method was written against real, still-existing methods, but every external
reference it reached for was wrong or dead:

- **`_update_memory`**: called `sm.ambient_surface()` / `sm.recent_strata()` — neither exists
  anywhere on the real `SediMemory` class (confirmed by reading it directly). Fixed to use
  `get_recent_fragments(n=3)`, SediMemory's real, existing method for exactly this purpose,
  pulling genuine `SedimentFragment` content (axis, resonance, content keys) instead of nothing.
- **`_update_sensory`**: read `systems["session"]` / `systems["conversation_context"]` — neither
  key is ever set anywhere in the codebase (confirmed by grep). Fixed to use `working_memory`'s
  real, already-established `turn_count`/`current_topic` attributes (used 10+ times elsewhere in
  the codebase for exactly this).
- **`_update_predictive`**: read `systems["_open_curiosity_loops"]` and `systems["field_map"]`/
  `["constraint_field_map"]` — none of these keys are ever set anywhere (confirmed by grep). Fixed
  to use the real, live `systems["_open_loops"]` (populated by this session's own seek-gap fix) for
  curiosity signal, and `systems["_prev_axis_activation"]` (the real, persisted cross-turn axis
  field) for dominant-field direction — deliberately not importing `aurora.py`'s module-level
  `_field_balancer` directly, which would risk a circular import.
- **`feed_expression_back()`**: fully implemented, but had zero real callers anywhere — the two
  wrapper methods meant to call it (`StreamingThoughtThread.feed_back()`,
  `StreamingExpressionLayer.complete()`) were themselves both unreached (confirmed by grep).
  Wired a direct call at the true end of `_run_live_response_turn`, where the final delivered text
  and this turn's `ThoughtState` are both genuinely settled — closing the STATE → EXPRESSION →
  RE-ENTRY loop the architecture's own doctrine describes.

**Verified live, across two real ticks with a real turn in between:** `predictive_frame` went from
an empty stub to `{'prior_expression': "What do you mean by 'almost'?", 'prior_axes': ['X','T','A'],
'curiosity_lean': 'unmet base meaning: ...', 'dominant_field': 'N'}` — the exact response she just
gave, genuinely fed back and already shaping the next predictive cross-section. `sensory_signal`
showed `turn_count` advance 0→1 and `open_loop_pressure` register the newly-seeded gap. `memory_signal`
showed real `SedimentFragment` resonance values shifting across ticks — genuine ambient presence,
not a frozen read.

## What this does NOT yet do

The snapshot is now real and rich, and it's genuinely fed by and feeding back into live turns. What's
still open, per Sunni's fuller vision: comprehension itself doesn't yet *consult* this snapshot as
reasoning input — `_current_thought_state` is still only read for one narrow governance/deception
check downstream, not woven into `_build_comprehension_response` or the seek/pursue decision. That's
the next real piece, and it's substantial on its own — not something to bolt on without the same
verification discipline as everything above.

---

# Subsurface → Axis Pressure Blend — Pressure-Induced, Constraint-Native (per Sunni)
**Status:** Implemented and verified live with a direct A/B comparison.

Sunni's explicit constraint: the connection between subsurface and surface must itself be
pressure-induced and constraint-native to the NonComp operators — not a parallel content-level
heuristic (e.g., reading the braid's English summary and splicing it into a response, which would
have repeated tonight's earlier learned-hints mistake in a new form).

The correct, doctrine-compliant point of connection: axis pressure itself (`state.axis_activation`),
since it's the one representation that already flows through everything downstream — ability
selection, WARP/Salience triggering, comprehension's axis context, the field balancer. Wired the
braid's `ThoughtState.axis_fingerprint` (literal X/T/N/B/A letters extracted from which process
contexts actually dominated this tick's integration — constraint-native by construction, not free
text) into `_chain_up3_purpose`'s existing raw-axis blend, using the *exact same pattern* already
established there for `collective_axis_net` — a rank-weighted nudge into `_raw`, not a new decision
system.

Weight scales with `thought_state.confidence` — genuinely pressure-induced, not a fixed constant.
Deliberately did NOT also penalize by `len(unresolved)` separately: confirmed by reading
`_compute_thought_confidence()` directly that confidence already subtracts `0.08` per unresolved
conflict, so a second penalty would double-count the identical signal through two paths — exactly
the parallel-heuristic drift the doctrine forbids.

**Verified live with a direct A/B comparison**, same input, same boot, blend forced off vs. on:
```
axis_activation WITH braid blend:    {X: 0.1681, T: 0.2020, N: 0.2557, B: 0.2299, A: 0.1444}
axis_activation WITHOUT braid blend: {X: 0.1642, T: 0.2206, N: 0.2502, B: 0.2198, A: 0.1453}
  X: +0.0039   T: -0.0186   N: +0.0055   B: +0.0101   A: -0.0009
```
Real, non-zero, directionally consistent with the fingerprint `['X','T','A']` and its rank decay
(T second-ranked, largest shift among the three fingerprint axes). Confirmed the seek-fix from
earlier still fires correctly alongside this (`resp_A.src = 'constraint_seek'`, same honest
seeking behavior, unaffected).

---

# The Wave Model — Confirmed Already Built, One Real Bug Fixed (per Sunni)
**Status:** Implemented and verified live with real coupling-physics traces.

Sunni described the pressure field as a still pond: input as a stone, a wave propagating
across the field and activating relevant pressures, those activations *being* the
understanding process, then that understanding reapplied into the same field to produce a
response. Before assuming any of this needed building, checked whether it already existed —
matching this whole session's discipline. It does, nearly word for word:
`aurora_waveform_pressure.py`'s own module docstring: *"Every observation, internal state
change, or cognitive event generates a PressureDisturbance... propagates it through coupling
physics... No subsystem is directly targeted — structures self-select participation by
reading their own pressure state from the manifold."* Real coupling table (X→{T:0.30,B:0.20},
T→{X:0.25,A:0.20}, N→{B:0.35,T:0.20,X:0.15}, B→{N:0.30,A:0.25}, A→{T:0.20,B:0.25,N:0.15}),
real attenuation per hop, real trace recording.

**The "stone hits water" half was already wired and confirmed working**: `_chain_up1_information`
injects a `user_input_precomp` disturbance from the turn's constraint aggregate before
comprehension even runs, deliberately positioned so "the field's axis pressures reflect this
turn's input when the constraint emitter runs" — exactly the model's first step.

**The "ongoing thought ripples back into the same field" half was broken** — a third instance
of tonight's exact recurring pattern. Inside `StreamingThoughtThread._loop()` (the same
background thread fixed earlier this session), a real, well-designed injection read
`_slice.axis_state` and `_slice.streams` — neither field exists on the real `ThoughtStreamSlice`
dataclass (confirmed directly: `memory_signal`, `sensory_signal`, `predictive_frame`,
`emotion_valence`, `braid_tick`, `is_tap`, `warp_signals` — no `axis_state`, no `streams`).
`_braid_axes` was therefore always `{}`, and this injection — the braid's own continuously-
evolving understanding rippling back into the shared field every 2-second tick, the literal
mechanism for "applying that understanding into the same pressure field" from a standing
subsurface process, not just at input time — had never fired once since this code existed.

Fixed to build the axis-state dict from real sources: `emotion_valence.valence` (already a
real, per-tick X/T/N/B/A dict — the felt reading of the current thought) as the base, folded
with memory_signal's resonance-weighted axis distribution (real now, since this session's
earlier `_update_memory` fix) so the injection reflects both affect and what's genuinely
activated in ambient memory, not affect alone. Removed the old dead fallback (`.streams`,
equally nonexistent) rather than leave unreachable code implying a backup path that never was one.

**Verified live**: one real turn produced one `user_input_precomp` injection and, over the
following seconds of continued background ticking, 24 real `thought_braid` injections — each
with genuine coupling-physics trace output matching the module's own physics table exactly
(e.g. primary hit on A at 0.1246, coupling to T at strength 0.20, to B at strength 0.25).

## What's confirmed working vs. still open

Confirmed: input creates a real wave: input → primary injection → coupling propagation →
field activation, and the ongoing subsurface now continuously ripples its own evolving state
back into that same field, both verified with real trace data. Still open, honestly: whether
the *outgoing* response itself deposits a fresh, distinct disturbance representing what she
decided to say (as opposed to the pre-comprehension input injection and the background
braid's continuous ripple, which are both now real but are not specifically "the act of
responding"), and whether the field's ongoing activity measurably biases *which* autonomous
question later surfaces from the seek-gap machinery. Both are real, traceable next questions
building on now-confirmed-real infrastructure, not open-ended architecture questions anymore.

---

# Repair J — Removing Fixed Weight Ceilings (per Sunni, 2026-08-19)
**Status:** Implemented and verified live across four blend sites.

Sunni's core objection, stated precisely: fixed percentage caps on how much a signal can
influence axis pressure are decisions made *outside* the pressure system, silently overriding
whatever the constraint physics would otherwise conclude — "dictating response at a different
level of abstraction which we cannot do." Found and audited every blend site touched this
session (three added/discovered tonight, one pre-existing) for this exact anti-pattern: a real,
already-bounded [0,1] pressure signal (maturity, confidence, intensity, resonance) being used
only as a *scale factor* on top of an arbitrary fixed ceiling, rather than as the weight itself.

- **Subsurface conscious-crest blend** (`_project_utterance_axes`): was a fixed 75/25 split
  regardless of how far above its 0.35 threshold the crest intensity sat — a crest at 0.36 and
  one at 0.99 influenced the axis identically. Fixed so `_crest_intensity` itself is the blend
  weight: `cur*(1-intensity) + intensity*intensity`. A weak crest barely nudges; a strong one can
  genuinely dominate.
- **Sensory crystal blend** (`_chain_up3_purpose`): was `min(maturity*0.12, 0.12)` — a fully
  matured sensory crystal could never contribute more than a crystal barely past its minimal-data
  floor. Fixed to use `maturity` directly as weight. Also removed a second, nested cap on
  cross-modal lane contribution (`min(lanes/10, 0.3)` → `min(lanes/10, 1.0)`) for the same reason.
- **Collective axis blend** (`_chain_up3_purpose`): the deepest instance — `axis_net_displacements`
  is a genuine *sum* of signed contributions from up to 10 active I-State beings (confirmed by
  reading `_synthesize_constraint_vector` directly), not a normalized value, so real magnitude was
  already being discarded by max-normalization before an additional flat `0.10` was applied on
  top. Two collective readings of very different actual strength produced the identical blend
  weight. Fixed to use `collective_resonance` — the dominant-resonance strength already computed
  by the same synthesis and already sitting in `pipeline_state` — as the real weight.
- **Braid axis blend** (this session's own item 2 addition): `0.12 * confidence` had the identical
  problem — even full confidence (1.0) was ceilinged at 12%. Fixed to use `confidence` directly.

**Verified live**: same test input, no crashes, seek behavior (Repair G) still fires correctly and
honestly. `axis_activation` now shows real differentiation the old caps couldn't produce — `N`
resolved to `0.3342`, clearly distinct from the other four axes, rather than everything clustering
within a few hundredths of the base value as the earlier A/B comparison (before this repair) showed.

## Scope note

Fixed the four sites directly feeding `axis_activation` from subsurface/sensory/collective
sources — the ones this session's own work touched or built. There are almost certainly other
fixed-percentage caps elsewhere in a 39,000-line file that weren't audited as part of this pass
(one candidate spotted but not investigated: a `min(BLEND_MAX, 0.12 + 0.20*fit)` pattern near
line 19723, in a different subsystem). Flagging rather than claiming completeness.

---

# Repairs K, L, M — Genealogy Performance (per Sunni, requested after Repair J)
**Status:** Implemented and verified live against your real, 13,210-ability genealogy.
This was surfaced by Sunni directly asking "have you tested response now?" — the honest
answer was no, and testing it surfaced a severe, real, escalating performance defect that
had nothing to do with any of tonight's other repairs.

## What was actually wrong

A single turn took 35–46 seconds and was **getting worse turn over turn**, not staying
constant — profiled and traced to an exact call chain:
```
genealogy.observe() → representation_collision_candidates() → _representation_index()
  → representation_is_eligible() [per item] → _semantic_identity_for_item() → _last_tag_value()
```
`_last_tag_value` alone: 9.1 million calls, 90+ seconds cumulative, for one turn. None of
this touches anything from items 1–9 or Repairs G–J — confirmed by reading the actual stack
trace, not inferred.

## Repair K — per-item memoization

`_semantic_identity_for_item` and the tag-filtering half of `_operational_effect_for_item`
were being fully recomputed for every one of 13,210 items on every rebuild. Confirmed
`effect_tags` is never mutated in place anywhere in this file (grep across the full source).
Added per-item caches for both, invalidated only by a dirty signal — not by the constantly-
growing `pair_stats` count that was triggering a full rebuild on nearly every turn. Cut
`_semantic_identity_for_item_uncached` calls from 481K to 95K and `_last_tag_value` calls
from 9.1M to 1.8M in the same live profile.

## Repair L — incremental outer index

Repair K made each item cheap; the outer `_representation_index()` loop still re-scanned
every one of the 13,210 `observed_ids` on every rebuild regardless. Made the rebuild
incremental: only ids not seen in the previous build get evaluated; a full rebuild is
forced explicitly (not assumed away) on the two cases that actually require it — the dirty
counter changing, or any of the three tracked counts decreasing (no removal path exists
today, but the invariant is guarded rather than relied upon). **Verified correctness, not
just speed**: constructed 15 new abilities, compared the incremental result against a
forced full rebuild of the identical state — exact match, including sort order, not just
bucket membership.

## Repair M — narrowing the dirty signal itself

Repairs K and L were both correct but starved of real benefit: `mark_representation_index_
dirty()` is a genuinely broad signal, also fired by `consequence_profile` updates (a live,
continuous, expected part of ongoing learning — measured at 34 calls in a single real turn),
which don't touch any field `_semantic_identity_for_item`/`representation_is_eligible`/
`_collision_signature_for_item`/`_operational_effect_for_item`'s tag filter actually reads
(axis, effect_tags, topology_id, semantic_variant_id — confirmed by reading all four
directly). Rather than touch the existing broad signal's semantics (unaudited for other
consumers, and this is real accumulated data, not something to risk casually), added a
second, strictly narrower counter — `mark_representation_identity_dirty()` — called
alongside the existing one only at the two call sites that genuinely mutate identity-
relevant fields (`constraint_genealogy.py`'s manual-code-change ability update, and
`aurora_sensory_crystal.py`'s axis reassignment). The consequence-profile-only site keeps
calling only the original, broad signal, unchanged. Repairs K and L now key off the narrow
counter instead.

Audited every other in-place ability/link replacement in the codebase (7 sites found via
grep) to confirm none were missed: five are new-id creation (several explicitly guarded by
`if ability_id not in genealogy.abilities`), safe by construction since new ids are already
handled correctly by Repair L's incremental diff; the remaining two are the ones already
wired above.

## Verified live, full arc

- Correctness re-confirmed after Repair M: growth-only change still produces an exact match
  against a forced full rebuild; a consequence-profile-only update correctly does NOT force
  a full rebuild; an axis reassignment still correctly forces one and re-indexes the item
  under its new bucket. All three checked directly, not assumed.
- Performance against the real, live, 13,210-ability genealogy, "What is your name?" x5:
  **9.9s → 5.5s → 5.3s → 5.0s** — stable, not escalating (previously 35s → 46s → stall).
- Repeated with a different input ("I think you're wrong about that."): **13.7s → 5.9s →
  6.0s** — same stable pattern, and the honest-seek response from Repair G still fires
  correctly ("What do you mean by 'wrong'?").

## What's still true, honestly

5–6 seconds per turn (after the unavoidable first-turn full build) is a large improvement
over an escalating multi-minute stall, but it is not fast, and it is not the deeper fix
Sunni raised earlier in this same conversation: subsurface processing — genealogy
bookkeeping included — is still sitting synchronously in the path to a reply, whether it
takes 46 seconds or 5. That thread (backgrounding the afterthought simulation episode
safely, given genealogy has no internal locking) remains open and was not addressed by
this pass, which was scoped specifically to the correctness and raw cost of the indexing
mechanism itself.

---

# Repair N — The Surface Must Never Wait on the Subsurface (per Sunni)
**Status:** Implemented and verified live, including under real concurrent load.

Sunni's framing going into this repair: consciousness/the surface exists as a fast,
persistent "waveform crest" precisely because the depth beneath it — rich, slow,
historically-continuous — would be a disability if it were the only layer touching a fast
external environment. The surface hands experience to the subsurface and keeps moving; it
never waits for the subsurface to finish before it can act again. That's not just a metaphor
for this codebase — it's the literal fix needed for the afterthought simulation episode
identified at the end of the Repair K/L/M session: a call that was already, by its own
`[AFTERTHOUGHT]` naming and its position strictly after `_finalize_articulation`, conceptually
supposed to be a post-response reflection — but was still running synchronously, blocking the
return.

## What was built

**Backgrounded the afterthought episode.** `aurora.gateway.simulation.run_episode(...)` now
runs on a daemon thread (`threading.Thread(..., name="aurora_afterthought_episode")`), the
identical pattern already proven correct with `ThoughtBraid` earlier this session. Nothing
about what the episode does internally changed — only when the calling thread gets control
back. The thread's own exceptions are caught and logged through the same
`_aurora_record_exception_from_locals` convention as everywhere else, since exceptions inside
a background thread don't propagate to the caller.

**Locked genealogy's one confirmed shared mutating entry point.** Backgrounding this call
makes `genealogy.observe()` reachable from two threads for the first time — confirmed it was
already called synchronously from two other places in `aurora.py` directly, in addition to
the now-backgrounded path. Renamed the original method to `_observe_impl` and added a thin
`observe()` wrapper that holds a new `self._concurrency_lock` (`threading.RLock`, reentrant
since internal helpers may need to re-enter) for the call's full duration — same safe
pattern as Repair K's cache wrapper, chosen specifically to avoid reindenting a ~350-line
function body. `representation_collision_candidates()` was checked and confirmed to have no
callers outside `observe()` itself, so it's already fully covered.

**Protected the surface's read side without ever blocking it.** `_select_active_abilities`
was reading `genealogy.abilities` directly, completely unprotected, from the surface's own
synchronous path. Per the "never wait" principle itself: it now attempts a non-blocking
lock acquisition (`acquire(blocking=False)`) to take a quick snapshot; if the background
thread currently holds the lock, it falls back to the most recent successfully-read
snapshot (cached on the genealogy object) rather than either blocking or returning nothing
— a slightly-stale perceptive frame, never a stall, matching exactly what was described.

## Verified live

- Traced the thread's actual lifecycle: it starts *before* `process_external_user_turn`
  returns (confirmed via a monkeypatched `Thread.run`), completes independently in 1.32s
  with zero exceptions logged, and the main thread's return time no longer has any
  coupling to it.
- Ran three varied turns with the background thread firing on each; genealogy's ability
  and link counts grew normally with no loss or corruption (13307→13309 abilities, links
  stable at 356), and `_representation_index()` still builds cleanly (126 buckets) after
  all the concurrent activity.

## What's still true, honestly

This fixes the specific blocking call identified in the previous session — it does not mean
every turn is now fast. Turns 2 and 3 in the same live test still took 10.1s and 6.8s; that
cost now comes entirely from the main synchronous comprehension/axis pipeline itself, which
is a separate, already-partially-addressed thread (Repairs K/L/M targeted genealogy
indexing specifically) rather than something this repair touches. The concurrency
protection built here is scoped to the specific race this session introduced — `observe()`
and the one read site that needed it — not a comprehensive audit or lock coverage of every
method on a 9,600-line class.

---

# Repair O — Instinct as the Constrained Subsurface Fallback (per Sunni)
**Status:** Implemented and verified live under genuine, separate-thread lock contention.

Sunni corrected his own framing mid-conversation: this isn't a surface-side engine, it's
"an allocated constrained subsurface function always available for the surface to interact
with" — specifically, the same part of the subsurface that already relays intuition and
instinct. That identification pointed directly at machinery already fixed earlier this
session: the continuously-running `ThoughtBraid`, structurally separate from genealogy's
new `_concurrency_lock` entirely, so tapping it (`current_slice()`) never waits on anything
genealogy is doing, busy or not.

## What was built

`_instinctive_understanding(systems)` — compiles what the braid already produces
(`predictive_frame`'s `dominant_field`/`curiosity_lean`, `_current_thought_state`'s
`axis_fingerprint`/`confidence`) into one small, bounded dict. Not a new subsystem; it reads
only signal this session already made real earlier (the memory/sensory/predictive fixes,
the axis blend, the feedback loop).

Wired into `_select_active_abilities`'s cold-start-busy path specifically: when genealogy's
lock is held by another thread AND no cached snapshot exists yet from any prior successful
read, rather than return nothing, it now constructs one clearly-marked synthetic entry
(`id: "instinct:temporary_substitute"`, `source: "instinct"`) from the instinct channel —
real axis lean, real confidence, whatever the braid is currently curious about — giving the
downward reasoning chain something honest to lean on rather than silence, explicitly
temporary and explicitly distinguishable from genuine genealogy-derived abilities.

## Verified live

First attempt at testing this exposed my own test methodology's flaw, not a code defect: a
blocking `.acquire()` in the main thread raced against genuine background genealogy activity
and hung — traced and fixed by properly holding the lock from a **genuinely separate**
thread instead. Confirmed `_select_active_abilities` itself is fast in isolation (0.29s, no
contention) — the earlier hang was never in the new code. With the lock genuinely held by
another thread and realistic state from a completed real turn (`_current_thought_state`/
`_prev_axis_activation` populated the way they actually are mid-conversation), the fallback
fired correctly: real dominant axis, real confidence (0.4301, matching values already seen
throughout tonight from the same thought-state source), non-blocking (0.000s), clearly
tagged. Confirmed the normal path still works identically once the lock frees.

---
