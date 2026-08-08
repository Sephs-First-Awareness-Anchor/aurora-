# Genealogy-Native Representational Environment — Implementation Report

**Status:** Phase 1 (observational derivation + shadow comparison)
implemented, then **Phase 1.1 (edge-fidelity repair)** on top of it after a
targeted re-review surfaced two real bugs in the Phase 1 derivation (§8),
then **Phase 2 (promotion-time dimension-participation observer)** — a
retrospective, purely-observational measurement of whether Aurora's live
formation dynamics actually engage NonComp dimensions the current genealogy
atoms cannot preserve (§10) — then **Phase 3A (native DIFFERENCE
preservation shadow)** — a parallel `PairStats` companion, replayed against
real events, asking whether the dropped DIFFERENCE signal would actually
matter if kept (§11; verdict: partially confirmed, decisive experiment
blocked by a newly-found architectural gap, not by a negative result) —
then **Phase 3A.1 (co-occurrence observatory)** — this time instrumenting
the real, live `observe()` call path itself (still no behavioral wiring),
to distinguish "DIFFERENCE genuinely isn't computed near pair-forming
calls" from "it's computed elsewhere but unreachable" from "it exists but
is stale" (§12; result: live execution confirms Phase 3A's zero-cooccurrence
finding by two independent methods, and narrows the diagnosis for the one
real caller directly examined) — then **Phase 3A.2 (producer observatory)**
— instrumenting the PRODUCER boundary this time
(`DifferenceHistoryBuffer.record()`/`.snapshot()`, class-level, still no
behavioral wiring), to ask whether the processes that experience DIFFERENCE
and the processes that form genealogical relationships ever share a causal
moment at all (§13; result: four real producer call sites and four real
consumer call sites found across the codebase, hand-verified by reading —
none of the eight connects to any other; leans toward genuine architectural
separation between developmental regimes rather than fossil compression,
though not yet fully closed). All six phases are purely observational: none
of them alter promotion behavior, WARP's coverage authority, the pressure
map, or the meaning/understanding registry. Live representational exposure,
the WARP coverage-authority change, pressure-map expansion, and the
meaning/understanding rewrite are intentionally **not** started — the
directive that scoped this work requires shadow validation before any of
those, and this report's job is to state honestly whether that validation
supports moving on, not to assume it does.

**Files added:** `aurora_genealogy_environment.py`,
`aurora_genealogy_environment_shadow.py`,
`tests/test_genealogy_environment_dag_preservation.py` (Phase 1/1.1);
`aurora_genealogy_promotion_dimension_observer.py`,
`aurora_genealogy_promotion_dimension_shadow.py`,
`tests/test_genealogy_promotion_dimension_observer.py` (Phase 2);
`aurora_genealogy_difference_shadow.py`,
`aurora_genealogy_difference_shadow_report.py`,
`tests/test_genealogy_difference_shadow.py` (Phase 3A);
`aurora_genealogy_cooccurrence_observatory.py`,
`aurora_genealogy_cooccurrence_observatory_report.py`,
`tests/test_genealogy_cooccurrence_observatory.py` (Phase 3A.1);
`aurora_genealogy_difference_producer_observatory.py`,
`aurora_genealogy_difference_producer_observatory_report.py`,
`tests/test_genealogy_difference_producer_observatory.py` (Phase 3A.2).
Nothing existing was modified in any phase — Phase 3A.1 and 3A.2's sidecars
wrap real bound/class methods at runtime rather than editing
`constraint_genealogy.py` or `aurora_internal/aurora_difference_buffer.py`.

**Phase 1.1 field renames** (Phase 1 → Phase 1.1, on `EnvironmentSignature`;
nothing outside this module's own test file imports it, so this was a
free rename, not a breaking change): `lineage` → `closure_projection`
(documented as a slot-deduplicated projection, not a faithful replay —
see §8.3); `signature_hash` → `provenance_hash` (unchanged meaning); new
`structural_hash` and `edge_provenance` fields added.

Every claim below is either (a) marked CONFIRMED, meaning it was verified by
reading or executing the actual code in this repository, or (b)
INTERPRETATION, meaning it is my reading of what a confirmed fact implies.
Where a claim in the original directive turned out to not match the code, I
say so rather than silently correcting it.

---

## 1. What was verified before anything was written

### 1.1 `ConstraintLink` and the current lineage-grading reduction (CONFIRMED)

`ConstraintLink` (`aurora_internal/constraint_genealogy.py:1181-1229`) stores
only **direct parents** (`parents: List[str]`) and a single `depth: int` — no
ancestor list, no DAG object. Full ancestry only exists implicitly, via
`self.links[parent_id]` lookups the caller has to walk itself.

Two different walkers already exist over that structure, and they disagree
sharply on how much they preserve:

- **`_axis_counts_from_item()`** (`constraint_genealogy.py:2642-2696`), used by
  `_lineage_grade_for_pair()` → `_merged_axis_counts_for_pair()`
  (`:5943-5952`), does recurse the full DAG, but only to accumulate a merged
  `{X,T,N,B,A: count}` dict. Branch structure, order, and per-ancestor
  identity are discarded; a shared ancestor reached via two parent paths is
  **double-counted** rather than deduplicated. `_lineage_grade_payload()`
  (`:747-815`) then reduces that further to one dominant axis, one secondary
  axis, and one generation int, and synthesizes a 2-atom `root_slot` string
  (`aurora_closure_basis.py:764-777`) before calling `derive_lineage()`. This
  is the flattening the directive suspected, confirmed by reading, not
  inferred from behavior.
- **`walk_link_sequence()`** (`constraint_genealogy.py:6249-6305`) is a
  *second*, independent walker over the exact same `.parents` DAG. It is
  identity-deduplicated (a `visited` set, no double counting), preserves full
  traversal order (oldest ancestor first), and returns one entry **per link**
  — `{link_id, i_state, recursion_level, axis, mean_relief, depth}` — with
  nothing merged away. It is fully order- and structure-preserving. It is
  currently consumed by exactly one thing: `aurora_computational_model.py`,
  which replays it as an executable "program tape." **It was never wired into
  lineage grading, `derive_lineage()`, or anything in `aurora_closure_basis.py`
  before this change.**

This is the concrete "missing causal loop" the directive predicted: the
full-fidelity walk already existed in the codebase, just disconnected from
the physics that needed it. `aurora_genealogy_environment.py` closes that gap
by calling `walk_link_sequence()` directly and feeding its output into
`derive_lineage()` via a full-length chained `root_slot`, instead of
reimplementing DAG traversal.

### 1.2 `derive_lineage()` already supports unlimited-length chains (CONFIRMED)

`_resolve_slots_from_root_slot()` (`aurora_closure_basis.py:743-763`) splits a
`root_slot` string on `×`/`x` with **no atom-count limit** — it was already
written to accept an arbitrary-length chain of genealogy atoms. The current
caller (`_lineage_grade_payload`) simply never gives it more than 2. No new
parser or physics table was needed; only a different (longer, ordered) input.

### 1.3 The closure basis's own dimension-channel physics (CONFIRMED — this
matters for §3)

`_build_noncomp_channels()` (`aurora_closure_basis.py:371-395`) builds all 25
`NonCompChannel`s from 5 constraint-level registry lookups
(`REGISTRY.cost(c)`, `.polarity(c)`, `.operator(c)`, `.difference(c)`), each
computed **once per constraint** and then reused, unchanged, across that
constraint's 5 dimension-labelled channels. Concretely: `NC:X:POLARITY`,
`NC:X:MAGNITUDE`, `NC:X:OPERATOR`, `NC:X:COST`, and `NC:X:DIFFERENCE` all
carry the **identical** `shift_cost_coeff`, `baseline_budget`,
`base_flip_threshold`, `inertia`, `i_state_pos/neg`, `diff_ref_type`, and
`diff_signed` values. Nothing at the channel level distinguishes what
"MAGNITUDE" vs. "COST" vs. "DIFFERENCE" physically *means* for a given
constraint — the five dimension names are structural roles a channel can
occupy in an `InteractionSlot` cross-product, not five independently-defined
physical quantities.

`genealogy_atom_to_channel_pair()` (`:419-439`) enforces "Sunni's Cost Law":
every one of the 25 genealogy atoms (`NC:C1>C2`) resolves to
`NC:C1:OPERATOR × NC:C2:COST` — always. This is checked by
`verify_closure_basis()` at import (`:1321-1329`).

**Consequence, discovered while building the derivation, not assumed going
in:** any environment signature derived purely from genealogy-atom
transitions is *structurally* confined to the OPERATOR/COST corner of the
5-dimension space. This is reported in full in §3.

### 1.4 WARP, crest profiles, axis emergence, pressure map (CONFIRMED)

- `_CORE_CREST_PROFILES` (`aurora_internal/dual_strata/subsystem_waveforms.py:305-370`)
  are 8 hand-authored 15D vectors (10 I-state keys + 5 recursion-depth keys).
  `CrestRegistry.check_coverage()` compares an incoming profile against these
  plus any WARP-promoted crests via cosine similarity.
- `WarpGenerator`/`AxisCoverageChecker`/`CoverageGap`/`WarpComponent`
  (`aurora_warp_protocol.py`) run coverage checks by cosine similarity in that
  same 15D space; trial components are scored over `TRIAL_TICKS=10` ticks and
  promoted only at `trial_score_ema >= PROMOTION_SCORE=0.60`
  (`:262,265,1039-1085`). Nothing in this project's new code calls
  `WarpGenerator.generate()`, `_record_anomaly()`, `check_and_extend()`, or
  `evaluate_warp_trials()` — verified by a source-scan test
  (`TestWarpUntouched::test_module_never_imports_warp_authority_surfaces`).
- `AxisEmergenceDetector` (`aurora_internal/aurora_axis_emergence.py`) builds
  compound axes and virtual slots that feed
  `CodeAutoEvolver._empty_slot_channels()` (`aurora_code_autoevolver.py:369,1053,1071-1080`).
  Grepping `aurora_625_pressure_map.py` for any reference to it returns zero
  matches — it does **not** feed `Aurora625PressureMap` today, confirming the
  directive's suspicion.
- `Aurora625PressureMap` (`aurora_625_pressure_map.py:78-315`) is a
  statically-enumerated, fixed 625-slot structure (`assert len(ALL_SLOTS) ==
  625`, line 87) with no growth mechanism in the file. **Not touched or
  expanded by this work**, per the directive's explicit instruction to
  determine what pressure needs to carry before growing anything.

### 1.5 Meaning and understanding (CONFIRMED)

`MEANING_PROFILES` (`aurora_internal/aurora_meaning_evolution.py:153-316`,
21 fixed entries) and `DEVELOPMENTAL_CHAIN` (`:409-516`, 8 fixed stages) are
never mutated at runtime. `rank_meaning_profiles()` (`:343-382`) only filters
and scores the existing 21-entry dict; it cannot construct a new signature.
`RuntimeUnderstandingContract._apply_genealogy_relief_boost()`
(`aurora_internal/aurora_understanding_contract.py:777-860`) uses genealogy
only to nudge existing axis-activation scores by at most 0.06 before
re-running the same fixed-set ranking — new entries are never appended
outside the pre-authored 21. **This confirms the directive's suspicion
exactly**: genealogy currently boosts pre-fixed meaning forms; it does not
generate them. No change was made here — per the directive, this requires the
representational-environment work to be validated first (§4), and a proper
meaning-genealogy shadow comparison is real, separate follow-on work (§6),
not something to rush into the same pass as the primary objective.

---

## 2. What was built

### 2.1 `aurora_genealogy_environment.py`

- `link_from_dict()` / `logger_from_links()`: deserializes real
  `ConstraintLink` fossils and constructs a throwaway
  `ConstraintGenealogyLogger` (temp directory, never touches real
  `aurora_state/`) purely so `walk_link_sequence()` — the existing walker —
  can be called unmodified.
- `derive_environment_signature(logger, link_id)`: calls
  `logger.walk_link_sequence(link_id)`, then:
  - builds `axis_distribution` from each node's real `mean_relief` magnitude
    (X/T/N/B/A, kept separate from dimension distribution per the directive);
  - builds `recursion_distribution` and `istate_distribution` by directly
    tallying `walk_link_sequence`'s own `recursion_level` (0–4,
    already-existing depth bucketing) and `i_state` (already-existing
    `AXIS_I_STATE`-derived per-node label) fields — no new mapping;
  - builds `dimension_distribution` by resolving every **real
    `ConstraintLink.parents` edge** among the walked nodes (`_derive_edges()`
    — as of Phase 1.1, §8; NOT adjacency in the walked list, which was the
    Phase 1 approach and is now known to fabricate sibling transitions) to a
    real genealogy atom (`NC:{a}>{b}`), looking up its actual
    `InteractionSlot` via `genealogy_atom_to_channel_pair()`/
    `slot_for_pair()`, and weighting by that slot's own `depth_score` — an
    existing field, not an invented constant;
  - chains **every** real edge atom (not just 2, and not fabricated ones)
    into one Unicode-`"×"`-joined `root_slot` string (as of Phase 1.1 — the
    Phase 1 ASCII join silently failed to resolve for 3+ atoms, §8.2) and
    calls the existing `derive_lineage()` with it, producing a real
    `ConstraintLineage` — renamed `closure_projection` as of Phase 1.1, §8.3
    (`leverage_grade`, `formation_cost`, `viable_band_alignment`,
    `energetic_footprint`, `ontological_status`) from the *full* preserved,
    edge-accurate ancestry instead of the 2-atom synthetic one;
  - records `edge_provenance` (every real edge, with multiplicity),
    `active_slots`, and `provenance` in traversal order, plus a label-blind
    `structural_hash` (topology only) and a `provenance_hash` (includes real
    link ids) — split into two hashes as of Phase 1.1, §8.3.
- `project_to_crest_profile()` / `compare_against_core_crests()`: re-keys
  `istate_distribution` + `recursion_distribution` (already in the same
  15-key vocabulary `_CORE_CREST_PROFILES` uses) and computes cosine
  similarity against all 8 authored profiles — read-only.

No branch anywhere in this file checks a substrate name, a domain label, or a
hand-picked "strictness"/"creativity"/threshold constant. The only free
parameter is `depth_score`-based weighting, and `depth_score` is an existing
`InteractionSlot` field, not something introduced here.

### 2.2 `aurora_genealogy_environment_shadow.py`

Standalone, read-only script. Loads all 356 real promoted links from
`aurora_state/genealogy/links.json`, derives a signature for each, and
reports the cross-tabulation against the 8 authored crest profiles. Not
imported by any live path — a diagnostic tool, run manually.

### 2.3 Tests (`tests/test_genealogy_environment_dag_preservation.py`, 13 tests)

| Test | What it proves |
|---|---|
| `test_merged_axis_counts_treats_both_chains_as_identical` | Executes the **existing** `_axis_counts_from_item()` on two structurally different 3-link DAGs with the same per-axis histogram and shows it returns identical counts — reproducing the information loss this directive targeted, on real `ConstraintLink` objects. |
| `test_full_dag_derivation_distinguishes_the_same_pair` | Same two DAGs, run through `derive_environment_signature()`: identical `axis_distribution`, but different `chained_root_slot`, `active_slots`, `structural_hash`, and `provenance_hash`. |
| `test_same_genealogy_under_different_labels_produces_identical_signature` | Identical DAG structure, entirely different link ids/"names": every structural field matches, including `structural_hash`; only `provenance_hash` (which intentionally includes real link ids) differs. The derivation never reads a name. |
| `test_different_genealogies_same_totals_can_differ` | Two 2-axis-histogram-equal DAGs differing only in recursion depth diverge in `recursion_distribution` and `structural_hash`. |
| `test_four_plus_atom_chain_resolves_through_unicode_separator` *(Phase 1.1)* | A genuine 5-node chain resolves through the Unicode `"×"` join into a non-empty, correctly-populated `closure_projection` — the case Phase 1's ASCII join silently failed on. |
| `test_ascii_join_of_the_same_chain_would_have_silently_failed` *(Phase 1.1)* | Regression guard: rejoining the same 5 atoms with ASCII `"x"` (reproducing Phase 1 exactly) is proven to resolve to `[]` via `_resolve_slots_from_root_slot()`. |
| `test_diamond_dag_produces_real_edges_not_flat_adjacency` *(Phase 1.1)* | A genuine diamond DAG produces exactly the 5 real edges (1 self + 4 parent_child) implied by its actual `.parents` structure, not by list adjacency. |
| `test_no_sibling_transition_is_fabricated_between_diamond_branches` *(Phase 1.1)* | Directly asserts no `edge_provenance` entry connects the diamond's two sibling branches, which the Phase 1 adjacency-based code would have fabricated. |
| `test_same_linear_walk_different_real_structure_diverges` *(Phase 1.1)* | Two DAGs with byte-identical `walk_link_sequence()` axis order but different real parent structure (plain chain vs. one node with two real parents) produce different edge counts and `structural_hash`es — the exact bug Phase 1 could not have caught. |
| `test_compare_against_core_crests_runs_and_stays_bounded` | Shadow comparison returns exactly the 8 authored keys, all cosine-bounded, and leaves `_CORE_CREST_PROFILES` byte-identical before/after. |
| `test_empty_genealogy_projects_to_empty_profile` | An unresolvable link id degrades to an explicit `insufficient_genealogy` flag rather than a fabricated signature. |
| `test_module_never_imports_warp_authority_surfaces` | Source-scans the new module for any reference to WARP's promotion/anomaly/generation entry points. None exist. |
| `test_derivation_and_comparison_are_pure` | Running derivation + shadow comparison creates zero new files under the real `aurora_state/` directory. |

All 13 pass. (8 from Phase 1, 5 added in Phase 1.1 — see §8.)

---

## 3. The primary finding: genealogy atoms cannot currently express 3 of the 5 dimensions

This is the report's central, code-verified result, and it is more
fundamental than the axis-count-reduction bug the directive started from.

Because every genealogy atom is hard-defined as `NC:C1:OPERATOR ×
NC:C2:COST` (§1.3), **`dimension_distribution` is mathematically constant —
always exactly 0.5 OPERATOR / 0.5 COST / 0 POLARITY / 0 MAGNITUDE / 0
DIFFERENCE — for any non-empty `ConstraintLink` genealogy whatsoever**,
regardless of how much DAG fidelity is preserved upstream. This was verified
by running the derivation against all 356 real fossil links: every single
one produces the identical 0.5/0.5 split.

This is not a defect in the traversal fix in §2.1 — the traversal now
faithfully preserves everything genealogy *can* express. The ceiling is
architectural: `ConstraintLink` records per-axis `mean_relief`/`mean_cost`
(which axis, how much, what sign), but never records *which of a
constraint's 5 dimension-channels* a given operation actually engaged.
Combined with the fact that all 5 dimension-channels of a constraint share
identical scalar physics (§1.3), there is no existing signal anywhere in
Aurora's genealogy fossils, and no existing per-dimension physics
differentiator in the registry, from which POLARITY, MAGNITUDE, or DIFFERENCE
dimension-participation could be honestly derived.

I deliberately did not patch this by inventing a mapping (e.g., "relief sign
→ POLARITY weight," "relief magnitude → MAGNITUDE weight," "stdev_relief →
DIFFERENCE weight"). Each of those would *sound* plausible and would make the
derived signature more visually varied, but none of them is backed by
anything Aurora's own physics currently asserts — they would be exactly the
kind of new invented constant the directive says not to introduce, dressed up
as if it were "existing physics." The honest answer is: **this information is
genuinely absent from the current propagation path, not merely uncomputed.**
Whether it is worth capturing (e.g., tagging which registry accessor —
`.cost()`, `.polarity()`, `.operator()`, `.difference()` — a promotion event
actually went through, at the point `ConstraintLink` is constructed in
`_try_promote()`) is a real, separate, and much smaller piece of future work
than anything else in this directive; it is not something this derivation
pass can retroactively recover from fossils that never recorded it.

The genuinely varying, genealogy-derived signal — confirmed by the tests in
§2.3 — lives in `axis_distribution` (which constraint, how strongly, in which
sign/direction), `recursion_distribution` (how deep), `istate_distribution`
(the same information reframed as I-state polarity), and **which specific
channels occupy the OPERATOR/COST roles** (`active_slots`,
`chained_root_slot`, and the resulting `ConstraintLineage`'s `leverage_grade`
/ `formation_cost` / `viable_band_alignment`, which do differ per DAG because
different `(constraint_a, constraint_b)` pairs have different
`combined_shift_cost` and `leverage_net` even though their `dim_a`/`dim_b`
labels are always the same two dimensions).

---

## 4. Shadow comparison results (real data, `aurora_genealogy_environment_shadow.py`)

Run against all 356 promoted links in `aurora_state/genealogy/links.json`:

```
Total links in fossil record: 356
Insufficient/empty genealogies: 0
Derived signatures: 356
node_count: min=1 max=11 mean=3.96

Dominant axis_distribution axis across all derived signatures:
  T: 232   X: 82   A: 33   N: 5   B: 4

Best-matching authored crest profile (argmax cosine):
  memory: 302   continuity: 23   pressure: 16   sensory: 10   prediction: 5

Per-crest cosine similarity stats:
  constraint   mean=+0.2918  stdev=0.0671  min=+0.1550  max=+0.5668
  continuity   mean=+0.5033  stdev=0.1399  min=+0.1338  max=+0.7097
  emotional    mean=+0.1522  stdev=0.1024  min=+0.0639  max=+0.4901
  memory       mean=+0.6299  stdev=0.1363  min=+0.1955  max=+0.8689
  prediction   mean=+0.3762  stdev=0.0966  min=+0.1770  max=+0.5900
  pressure     mean=+0.5018  stdev=0.0579  min=+0.4094  max=+0.6422
  sensory      mean=+0.4569  stdev=0.0812  min=+0.3228  max=+0.7978
  symbolic     mean=+0.2807  stdev=0.0838  min=+0.1448  max=+0.6349
```

**Interpretation (clearly separated from the numbers above):**

- The fossil record is heavily T-axis-dominant (232/356 links), which is a
  property of *this specific corpus of promoted links*, not a property of
  the derivation. The "memory"/"continuity" crest profiles being the modal
  best match is thematically unsurprising given that: the T axis is the one
  `walk_link_sequence` maps toward `I_CAN`/`I_CANNOT`, and the authored
  "memory"/"continuity" profiles (`subsystem_waveforms.py:82-108,215+`) are
  themselves T-axis-weighted by construction. This is a real, mild,
  *directionally consistent* alignment between independently-authored and
  genealogy-derived structure — not proof of the hypothesis. WARP's own
  `COVERAGE_THRESHOLD` for "this counts as covered" is 0.82; the observed
  memory-profile mean (0.63) and max (0.87, only barely over) fall mostly
  **below** that bar. Under the current, unmodified WARP threshold, most of
  this corpus's real genealogies would still register as coverage gaps
  against the authored profiles, not confirmed matches.
- The weakest match category is "emotional" (mean 0.15) — expected, since
  nothing in a T/X/A-dominated cost-genealogy corpus should resemble the
  authored emotional-waveform profile, and nothing here forces it to.
- This is a single corpus (promoted links from whatever runs produced
  `aurora_state/genealogy/links.json`), not a controlled per-substrate
  experiment. A stronger version of this experiment would need genealogies
  that are independently known to have been produced *while* e.g. a memory
  operation vs. a sensory operation was live — no such tagging exists on
  `ConstraintLink` today (checked: `tags` carries provenance like
  `generation_role`, `purpose_lane`, `seed_lineage`, never a subsystem name).
  Building that correlation is future work, not something fabricable from
  today's fossils.

**Honest verdict on the "primary success criteria":** the derivation
preserves genealogy structure through real closure-basis physics without any
domain-specific scripting (confirmed, §2, §2.3), and produces a stable,
non-fabricated signature for 356/356 real genealogies (confirmed, §4). It
does **not** yet demonstrate strong, unambiguous convergence with the
authored native-waveform profiles — the observed alignment is real but
modest, well short of WARP's own coverage bar, and concentrated in exactly
the axis (T) this corpus happens to be dominated by. That is a partial,
honest result, not a confirmed "cognition-emergence" success, and it is
reported as such rather than rounded up.

---

## 5. Regression suite (CONFIRMED — actual run, not the directive's cited baseline)

Full suite: `python3 -m pytest tests/` (184 test files, 1856 collected items,
46m19s). The directive's cited "147 passing, zero failures" baseline could
not be located anywhere in this repository (no script or doc references that
number) and does not match the current suite size (1856 items across 184
files today), so it is not something this report can reconcile — the numbers
below are the real, current, literally-reported result instead:

```
14 failed, 1841 passed, 1 skipped, 1 warning in 2779.08s (0:46:19)
```

All 8 new tests in `tests/test_genealogy_environment_dag_preservation.py`
pass. **All 14 failures are pre-existing and unrelated to this work** —
confirmed by grep: none of the 6 failing test files reference
`aurora_genealogy_environment` in any way, and this change modified zero
existing files. The failures, for the record:

- `test_concept_image_ingestion_import.py` (1) — concept-image ingestion
  fixture path, unrelated to genealogy/closure-basis/WARP.
- `test_d1_device_path_attribution.py` (1) — device-path response
  unification.
- `test_general_execution_foundry.py` (3) — Python-candidate AST sandboxing
  and runaway-loop termination.
- `test_m1_2_provenance_hygiene.py` (1) — blind-origin tagging.
- `test_reflective_readdressing.py` (7) — self-inquiry/reflective-lineage
  turn handling; one thread also threw `FileNotFoundError: [Errno 2] No such
  file or directory` from `aurora_checkpoint.py`'s autosave loop mid-run
  (`sh: 0: getcwd() failed`), consistent with this remote sandbox's working
  directory churning during a 46-minute run rather than a code defect.
- `test_rw4_relation_to_self.py` (1) — self-relation population in live-turn
  NonComp input.

None of these touch `ConstraintLink`, `aurora_closure_basis`,
`aurora_warp_protocol`, `aurora_internal.dual_strata.subsystem_waveforms`, or
`aurora_internal.aurora_meaning_evolution` — the modules this work actually
reads. They are reported here rather than silently ignored, per the
directive's instruction to distinguish confirmed behavior from
interpretation, but investigating/fixing them is out of scope for this
directive and was not attempted.

Running the suite also writes to a number of live `aurora_state/*.json` /
`.jsonl` files as a side effect of booting real Aurora subsystems inside
individual tests (e.g. `aurora_state/genealogy/{abilities,couplings,
events_recent,tick_state}.json`, `aurora_state/concept_crystals.json.gz`,
`aurora_state/*_snapshot.json`). Those are runtime artifacts of *running the
suite in this sandbox*, not part of this change — they were reverted before
committing and are not included in this branch.

---

## 6. What was deliberately not done in this pass, and why

Per the directive's own phase ordering, each of these requires the prior step
to be validated first — and §4 shows validation is partial, not complete:

- **Representational Exposure** (letting live incoming pressure encounter a
  genealogy-derived environment and behave accordingly): not implemented.
  The shadow comparison in §4 does not show strong enough convergence to
  justify treating the derived signature as authoritative for anything live.
- **WARP coverage-authority change** (checking against derived environments
  instead of only the 8 authored profiles): not implemented, per the
  directive's explicit instruction not to do this until shadow comparison
  demonstrates stability. `AxisCoverageChecker`/`WarpGenerator` are
  byte-for-byte untouched (verified by test).
- **`Aurora625PressureMap` expansion**: not done. Confirmed (§1.4) it is a
  fixed 625-slot structure with no live connection to
  `AxisEmergenceDetector`'s compound axes; nothing in this pass changes that,
  and nothing in this pass found evidence that pressure's bottleneck is slot
  count rather than genealogical fidelity (the fidelity fix in §2 was the
  cheaper, more targeted change, exactly per the directive's instinct).
- **Meaning/Understanding reassessment**: not done beyond confirming (§1.5)
  that genealogy currently only nudges, never generates, meaning-form
  selection. A real genealogy-vs-`MEANING_PROFILES` shadow comparison
  (analogous to §4 but against the 21 meaning signatures instead of the 8
  crest profiles) is the natural next experiment and would reuse
  `axis_distribution` directly (meaning signatures are already keyed in
  `X^n*T^m...` axis-power notation) — but running it carefully, with its own
  honest interpretation section, is a separate piece of work from this one,
  not a few extra lines to bolt on at the end.

## 8. Phase 1.1 — edge-fidelity repair

A follow-up review of the Phase 1 code (not new directive scope, just closer
reading of what was actually shipped) surfaced two real bugs. Both are fixed
here; both stayed fully within the "observational, no invented constants"
constraint — no new domain branches or behavioral thresholds were added,
only a correction to which existing data feeds the existing physics.

### 8.1 Bug 1 (CONFIRMED): transitions were read from list adjacency, not real edges

Phase 1's `derive_environment_signature()` built `pairs` from **consecutive
entries in `walk_link_sequence()`'s flat output list**
(`zip(axis_sequence, axis_sequence[1:])`), not from `ConstraintLink.parents`.
`walk_link_sequence()` is a post-order DFS
(`constraint_genealogy.py:6276-6287`): for any node with 2+ parents, two
nodes adjacent in its output are frequently **siblings from independent
branches with no real edge between them**. Treating that adjacency as a
genealogical transition fabricated edges that never happened in the real
DAG.

Fixed by `_derive_edges()` (`aurora_genealogy_environment.py`), which reads
each walked node's actual `ConstraintLink.parents` and only ever pairs a
node with an ancestor that is really one of its parents. A node whose every
parent is a non-`Link` leaf (a bare ability id, or a root-level genealogy
atom like `"NC:N>N"` — both already invisible to `walk_link_sequence()`
itself, confirmed at `constraint_genealogy.py:6280-6282`) now contributes an
explicit `edge_type="self"` entry instead of being silently paired with an
unrelated neighbor or silently dropped.

**Test:** `test_diamond_dag_produces_real_edges_not_flat_adjacency` and
`test_no_sibling_transition_is_fabricated_between_diamond_branches` build a
genuine diamond (`L_A -> {L_B, L_C} -> L_D`), confirm the DFS really does
place `L_B`/`L_C` adjacently in the flat list (the exact condition that
fooled Phase 1), and assert no `edge_provenance` entry connects them.
`test_same_linear_walk_different_real_structure_diverges` goes further:
constructs two 3-node DAGs whose `walk_link_sequence()` axis order is
byte-identical (`[X, T, N]`) but whose real parent structure differs (a
plain chain vs. one node with two real parents) — Phase 1's logic would have
produced identical output for both; the repaired logic correctly produces 3
edges vs. 4 and different `structural_hash`es.

### 8.2 Bug 2 (CONFIRMED): the ASCII separator silently failed for 3+ atoms

`_resolve_slots_from_root_slot()` (`aurora_closure_basis.py:743-763`) only
takes the ASCII-`"x"`-split branch when `root_slot.count("x") == 1` — exactly
2 atoms. Phase 1 joined the full chain with ASCII `"x"`
(`"x".join(atoms_in_order)`). For any genealogy with 3+ transitions — the
common case, since the 356-link shadow corpus has mean `node_count=3.96` —
`root_slot.count("x")` was ≥2, landing in the `else` branch, which treats the
**entire joined string as one unparseable atom** and returns an **empty**
slot list. `derive_lineage()` then silently fell through to its
axis+`requires`-only fallback path (`aurora_closure_basis.py:966`), meaning
the Phase 1 report's claim that `derive_lineage()` received "the full
preserved chain" **did not actually hold for most of the real genealogies it
was run against** — spot-checked directly: the one example quoted in the
Phase 1 report (`L:be51b47ae4`, a 6-atom chain) had already silently hit this
failure path, though because every atom in that particular chain happened to
be `T>T`, the axis+requires fallback (`requires=("T",)`) coincidentally
produced the same single slot the intended chain would have, masking the bug
in that one spot-check.

Fixed by joining with the canonical Unicode `"×"`
`_resolve_slots_from_root_slot()` checks **first and unconditionally**, for
any chain length.

**Test:** `test_four_plus_atom_chain_resolves_through_unicode_separator`
builds a genuine 5-node linear chain (X→T→N→B→A, 5 distinct atoms) and
asserts `_resolve_slots_from_root_slot()` actually returns non-empty slots
and that all 5 expected slot ids reach `closure_projection.active_slots`.
`test_ascii_join_of_the_same_chain_would_have_silently_failed` is a direct
regression guard: it takes that same 5-atom chain, rejoins it with ASCII
`"x"` (reproducing exactly what Phase 1 did), and asserts
`_resolve_slots_from_root_slot()` returns `[]` for it — proving the bug was
real and that the Unicode join is load-bearing, not cosmetic.

### 8.3 Renamed `lineage` → `closure_projection`, documented honestly

`derive_lineage()`'s `_add()` helper (`aurora_closure_basis.py:959-962`)
deduplicates by `slot_id`. Even with both bugs fixed, its output can never
by itself certify branch multiplicity or topology — two real, distinct
edges that resolve to the same slot collapse to one entry. Worse (found
while re-verifying the fix, not anticipated going in):
`derive_lineage()` **also unconditionally unions in slots from its own
axis+`requires` resolution path** (`aurora_closure_basis.py:966`), regardless
of `root_slot` content — so `closure_projection.active_slots` can legally
contain *more* slots than `edge_provenance` describes. The 5-atom linear
chain in §8.2's test resolves to **8** deduplicated slots, not 5, because
`requires` covered all 5 axes and pulled in 3 additional `X>*` slots the
real edges never touched.

None of this makes `closure_projection` wrong — it is a real,
physics-grounded reading, exactly as before. But it can no longer be
described as "the chain, resolved." It is renamed and documented as a
**closure projection**: a lawful but lossy view, useful for the existing
closure-basis grades (`leverage_grade`, `formation_cost`,
`viable_band_alignment`, `energetic_footprint`, `ontological_status`), never
for multiplicity or topology claims. `edge_provenance` (full multiplicity,
every real edge) and `structural_hash` (topology fingerprint, label-blind)
are the fields that carry what `closure_projection` structurally cannot.

**Test:** `test_same_genealogy_under_different_labels_produces_identical_signature`
now asserts `structural_hash` matches across relabeled-but-isomorphic
genealogies while `provenance_hash` (which intentionally includes real link
ids) does not — confirming `structural_hash` is the label-independent
signal the directive's testing strategy asked for, distinct from and
narrower than the old single `signature_hash`.

### 8.4 Re-run of the 356-link shadow, before/after

```
Best-matching authored crest profile (argmax cosine):        [UNCHANGED]
  memory: 302   continuity: 23   pressure: 16   sensory: 10   prediction: 5

Per-crest cosine similarity means:                            [UNCHANGED]
  memory 0.6299   continuity 0.5033   pressure 0.5018   sensory 0.4569 ...

Edge-fidelity stats (new in Phase 1.1):
  edges per genealogy: min=1 max=16 mean=5.13
  self edges (leaf-rooted nodes): total=772  mean=2.17
  parent_child edges (real DAG edges): total=1054  mean=2.96
  chained_root_slot empty (unresolvable): 0 / 356

closure_projection stats (new in Phase 1.1 — not collected in the Phase 1
report, since Phase 1 never instrumented this and, per §8.2, was mostly
silently falling back to the axis+requires-only path for these genealogies
anyway, so there is no valid "before" number to diff against here):
  deduped active_slots per genealogy: min=1 max=7 mean=1.97
  leverage_grade: min=0.0769 max=1.0000 mean=0.1734 stdev=0.2194
  formation_cost: min=0.0067 max=1.0000 mean=0.1181 stdev=0.1989
```

Exactly as predicted going in: the crest-comparison numbers in §4 are
**byte-identical** before and after, because `istate_distribution` and
`recursion_distribution` are node-level (from `walk_link_sequence()`
directly) and untouched by the edge-fidelity repair. The **closure-basis**
statistics are where the ASCII-separator and false-edge bugs mattered, and
those are now populated from real data for the first time at corpus scale —
mean edges-per-genealogy (5.13) exceeds mean `node_count - 1` (2.96), which
is the direct, confirmed signature of real branching (diamond merges
contributing multiple parent edges) being captured instead of flattened
into a linear list.

### 8.5 Regression scope for Phase 1.1

`grep -rl "aurora_genealogy_environment" --include="*.py" .` returns only
this module's own test file — nothing else in the repository imports it.
The full 184-file / 46-minute suite from §5 was therefore not re-run for
this follow-up; the change is fully isolated by construction (renamed
dataclass fields with no external consumers, new fields, corrected internal
logic), and the 13 tests in
`tests/test_genealogy_environment_dag_preservation.py` (up from 8; 5 new,
covering exactly the scenarios in §8.1/§8.2/§8.3) all pass.

## 9. Remaining architectural gaps (confirmed, not interpretation)

1. `ConstraintLink` cannot express which of a constraint's 5 dimension-roles
   an operation engaged (§3) — this is the most consequential open gap for
   the "derived environmental signature" goal specifically. Unaffected by
   Phase 1.1: real edges still resolve to genealogy atoms, which are still
   hard-confined to OPERATOR×COST.
2. No `ConstraintLink` field ties a promoted link to a subsystem/substrate
   name — the shadow comparison in §4 is corpus-wide, not per-substrate,
   for exactly this reason.
3. `walk_link_sequence()`'s cycle guard is identity-based (a `visited` set
   across the whole walk) — a diamond DAG (two paths converging on a shared
   ancestor) will visit that ancestor once, not twice. This is more correct
   than `_axis_counts_from_item()`'s double-counting behavior, but it does
   mean "repeated constraint participation" in this derivation means
   "the same axis dominant at multiple *distinct* links," not "the same
   link visited multiple times" — worth being precise about if this
   distinction matters for later work.
4. `derive_lineage()`'s unconditional axis+`requires` slot union (§8.3) means
   `closure_projection` is not a pure function of `edge_provenance` — two
   genealogies with identical edges but different `axis_distribution`
   coverage (different `requires` tuples) can get different
   `closure_projection.active_slots` padding even when their real edges
   match. This is pre-existing `derive_lineage()` behavior this repair
   surfaced but did not change; worth flagging for anyone consuming
   `closure_projection` expecting it to depend only on `edge_provenance`.

---

## 10. Phase 2 — promotion-time dimension-participation observer

**Question asked:** does Aurora's live formation dynamics actually involve
NonComp dimensions that the current OPERATOR×COST genealogy atoms fail to
preserve? If yes, §3's "five-dimensional ceiling" is measured
representational loss. If no, it may be a faithful compression instead.

**Method:** purely observational, and more conservative than a live hook —
no code that could affect promotion was touched, modified, imported, or
executed. This phase is entirely (a) direct inspection of the real
promotion code path's actual signatures/call sites, and (b) a read-only
statistical pass over already-persisted, real `ReliefRecord` fossils from
past Aurora runs. No Aurora process was booted or run to produce this
section's numbers.

### 10.1 Structural finding (CONFIRMED): promotion's live input is axis-only, not dimension-typed

`PairStats.update()` — promotion's entire live input surface — verified via
`inspect.signature()`:

```
(self, relief: 'PressureVec', cost: 'Dict[str, float]', x_risk: 'float', tick: 'int')
```

Both `PressureVec` and `Dict[str, float]` are keyed by AXES (X/T/N/B/A).
There is no parameter shape here that could carry "which NonComp dimension"
information even if a caller wanted to supply it — this is not a missing
value, it is a missing *channel*. `_try_promote()`
(`aurora_internal/constraint_genealogy.py:5433-5433+`) reads only
axis-level aggregates of exactly this input
(`mean_relief/mean_pos_relief/pos_fraction/stdev_relief/mean_cost/
mean_x_risk_val`), and the `ConstraintLink` it constructs stores only
axis-level fields — consistent with, and now completing, Phase 1's
output-side finding (§3): the confinement is not introduced downstream by
the genealogy-atom vocabulary; the atoms are confined because their input
already was.

### 10.2 Structural finding (CONFIRMED): dimension-typed live data exists at the exact same tick, and is never forwarded

`ConstraintGenealogyLogger.observe()` (`:1869-2118`, read start to finish)
is the single call that produces BOTH promotion's input and a much richer
per-tick fossil record, in this order:

1. Computes `relief`/`cost_total` (axis-level) — line ~1897-1924.
2. Accepts an optional `difference_snapshot: Optional[DifferenceSnapshot]`
   parameter (line 1877) — a **real, live, per-axis DIFFERENCE-dimension**
   value, computed by the evolution chamber's `DifferenceHistoryBuffer` via
   `compute_difference()` against each constraint's own
   `DifferenceParams.ref_type` (`aurora_internal/aurora_difference_buffer.py:21,347-360`).
   That module's own docstring: *"This snapshot is the live output of the
   Difference channel — the fifth lens made operationally real"*
   (`aurora_difference_buffer.py:136-137`) — Aurora's own code describing
   exactly the dimension this investigation is asking about.
3. Merges it into `record.notes["difference_snapshot"]` (line 1976) for the
   fossil log.
4. Only THEN calls `self._accumulate_pairs(trace, relief, cost_total,
   x_risk_total)` (line 2074) — **no `difference_snapshot` argument.**
   Verified directly (not by inspection alone —
   `test_observe_never_forwards_difference_snapshot_to_pair_accumulation`
   parses every actual `_accumulate_pairs(` call site in `observe()`'s real
   source via `inspect.getsource()` and asserts none of them mention
   `difference_snapshot`).

This is the core Phase 2 finding: a genuinely dimension-typed live physics
quantity is computed, at the same tick, by the same function call that
produces promotion's inputs — and is structurally excluded from reaching
promotion by that function's own call signature, not merely discarded by a
later reduction step.

### 10.3 A second, weaker-graded live signal (CONFIRMED present, graded differently)

`record.active_concepts` (line 1983-1995, sourced from
`self._dps.get_recently_active(5)`) can contain strings like
`"tensor:MANIFOLD:X:NC[N:COST]xNC[T:DIFFERENCE]"` — produced by
`aurora_internal/dual_strata/cers_tensor_locator.py`'s
`record_tensor_trace()`, which writes concepts named `f"tensor:{coord.slot_id}"`
for a `SlotCoord` (`aurora_constraint_manifold_router.py`). This **does**
reference dimensions beyond OPERATOR/COST in real persisted data.

Graded weaker than §10.2 because, per `_resolve_slot_coord()`
(`cers_tensor_locator.py:119-138`): the coordinate's two axes
(`nc_law_c`/`law_c`, the 2nd/3rd-most-active axis that tick) ARE genuinely
live and vary tick to tick — but each axis's attached *dimension name*
(`nc_dim`/`law_d`) comes from `axis_to_dim.get(axis, "OPERATOR")`, a
**static per-axis lookup table** (`_DIMENSION_TO_AXIS`, inverted,
`aurora_constraint_manifold_router.py:231`), not a live per-event dimension
computation. So this signal proves a real, separate live subsystem (CERS)
treats dimension identity as a fixed badge per axis — a different design
choice than `aurora_closure_basis._build_noncomp_channels()`, which gives
every dimension-channel of a constraint identical physics (§1.3) — but it
is not itself proof of live per-dimension *physics*, only of live
per-dimension *labeling*. Both are reported; neither is overstated as the
other.

### 10.4 Empirical measurement, real data (`aurora_genealogy_promotion_dimension_shadow.py`)

Two corpora, reported and interpreted **separately**, not pooled:

```
=== PRIMARY: aurora_state/genealogy/events_recent.json (real run) ===
  record_count: 137
  difference_signal_present: 49 / 137  (35.8%)
  difference_values_nontrivial: 49 / 137  (35.8%)
  tensor_concept_reference_present: 137 / 137  (100.0%)
  non_operator_cost_tensor_reference: 137 / 137  (100.0%)
  any_non_operator_cost_signal: 137 / 137  (100.0%)
  non_operator_cost_dimension_counts: {'DIFFERENCE': 143}

=== SECONDARY (excluded from the live-dynamics conclusion): synthetic
    artificial_seed lineage events (aurora_state/ability_lineages/**) ===
  record_count: 414
  (every stat 0/414, 0.0% — no tensor concepts, no difference signal at all)
```

**Interpretation (separated from the numbers):**

- **35.8% of real relief events in this corpus carried a genuine, live,
  per-axis DIFFERENCE-dimension value** (§10.2's strong signal). It is
  never present-but-empty when present: `difference_signal_present_count ==
  difference_nontrivial_count` exactly (49 == 49, locked in as a regression
  by `test_difference_signal_when_present_is_always_nontrivial_in_this_corpus`).
  It is not present on every tick — `observe()`'s `difference_snapshot`
  parameter is optional, and cross-referencing individual records shows it
  co-occurs specifically with dream/evolution-chamber-originated ticks
  (`notes.seed_lineage_id == "dream_episode"` in the manually-inspected
  example quoted in §10.2's write-up), not plain interaction ticks. The
  honest claim is therefore: *when the evolution chamber is active, it
  computes real DIFFERENCE-dimension physics that promotion structurally
  cannot see* — not "35.8% of all Aurora activity, universally."
- **100% of real relief events referenced at least one non-OPERATOR/COST
  tensor dimension** (§10.3's weaker signal) — but only DIFFERENCE ever
  appears among the three (POLARITY, MAGNITUDE never occurred in this
  corpus's 143 references). Given §10.3's finding that the dimension label
  is a static per-axis badge, this means: in this particular corpus, the
  axis statically bound to DIFFERENCE was frequently the 2nd/3rd-most-active
  axis; the axes statically bound to POLARITY/MAGNITUDE never were. This is
  a property of this corpus's activity pattern, not a claim that
  POLARITY/MAGNITUDE participation is structurally impossible.
- The synthetic corpus's flat 0% across every stat is itself a useful
  negative control: it confirms the observer isn't spuriously finding
  signal everywhere, and correctly distinguishes organic live activity from
  deliberately-constructed seed records.

**Answer to the question this phase asked:** yes, measured, not assumed.
Real Aurora runtime already computes and records genuine dimension-typed
physics (DIFFERENCE, confirmed strongly) at ticks that feed promotion, and
that physics never reaches `PairStats`, `_try_promote()`, the resulting
`ConstraintLink`, or (per §3) any genealogy atom derived from it. The
OPERATOR×COST confinement found in Phase 1 is **not** a faithful
compression of what promotion's inputs ever carried — it is measured loss
of information Aurora's own runtime was already producing, at minimum for
the DIFFERENCE dimension. POLARITY and MAGNITUDE remain unconfirmed by this
corpus specifically (see §10.6) — the finding is proven for one of the
three missing dimensions, not automatically extended to all three.

### 10.5 What this phase deliberately did not do

Per its own framing ("observe... without changing promotion behavior"):
no live hook was wired into `observe()`/`_accumulate_pairs()`/`_try_promote()`
to carry this forward into future runs — `aurora_genealogy_promotion_dimension_observer.py`
is a standalone library, callable against a `ReliefRecord`'s already-built
`notes`/`active_concepts` (documented in its own docstring as "designed to
be called right after `record = ReliefRecord(...)` construction," were a
future pass to wire it in). This keeps Phase 2 at zero execution risk —
consistent with every prior phase's rule of new files only, no edits to
existing files — at the cost of only being able to measure what past runs
happened to already persist, not what's happening in any run now. Whether
to wire a real-time version of this observer into a live `observe()` call
is a decision for a future pass, not assumed here.

### 10.6 Remaining gaps this phase surfaces

1. Only one corpus (`events_recent.json`, 137 records from a single run)
   was available to measure against — a second, independent real run would
   strengthen or weaken §10.4's specific percentages without changing the
   structural finding in §10.1/§10.2, which holds regardless of any corpus
   (it's a property of the function signatures, not of the data).
2. POLARITY and MAGNITUDE never appeared in this corpus's tensor
   references, and neither has any confirmed live-physics analog to
   `DifferenceSnapshot` been located for them (this pass did not search
   exhaustively for one — `aurora_internal/aurora_polarity_gradient.py` is
   an unexamined candidate for POLARITY; no MAGNITUDE-specific module was
   identified at all). Whether genuine live MAGNITUDE-dimension physics
   exists anywhere in Aurora and is similarly excluded from promotion is an
   open question this phase did not resolve either way.
3. `events_recent.json` is a bounded ring buffer (`maxlen=10_000`,
   confirmed Phase 1 §1) reflecting only the most recent portion of one run.
   **Correction (found during Phase 3A, §11):** the claim originally here —
   that this ring buffer's tick space doesn't overlap with `links.json`'s —
   was wrong. Both files share `run_id "2026-07-29_050108"`; `links.json`'s
   356 links have `created_at_tick` up to 129144, and
   `events_recent.json`'s 137-record window starts at tick 132643 — the same
   continuous session, just after all 356 promotions had already happened.
   So this ring buffer genuinely is the tail of the exact session that
   produced every link in Phase 1/1.1's corpus; it just doesn't capture any
   of their original promotion moments (which are further back than the
   buffer's `maxlen=10_000` retains) — it only captures later *reuse* of
   already-promoted links. See §11 for what that reuse data does and
   doesn't support.

---

## 11. Phase 3A — Native DIFFERENCE Preservation Shadow

**Question asked:** if DIFFERENCE were preserved instead of dropped, would
it turn out to matter — does it differentiate genealogies the current
representation conflates, correlate with real outcomes, persist across
ancestry, and (critically) carry information beyond axis identity? The
directive framed a specific "killer experiment" as the bar for the case to
become extremely strong. This section reports exactly what was found,
including where the experiment as specified could not be run and why.

**Method:** no code that could affect promotion was touched. `PairStats` was
not modified. A parallel structure, `ShadowPairStats`
(`aurora_genealogy_difference_shadow.py`), mirrors real `PairStats`'s
axis-level accumulation field-for-field and rule-for-rule (verified by
`test_axis_accumulation_matches_real_pairstats_update` — constructs a real
`PairStats`, runs the same updates through both, asserts numeric parity),
plus a companion channel for DIFFERENCE participation with explicit
provenance (`difference_source`, per-tick `difference_values_by_tick`,
never collapsed into "axis"). `replay_events()` reconstructs pair keys from
real, already-persisted `ReliefRecord`s using the exact adjacent-pair rule
`_accumulate_pairs()` uses (`constraint_genealogy.py:5388-5391`) — this is a
replay over static JSON, not a live hook; nothing here imports
`ConstraintGenealogyLogger` (verified,
`test_module_never_imports_constraint_genealogy_promotion_surfaces`).

### 11.1 The corpus has a floor effect the analysis had to surface honestly

Before any of the six questions could be answered, replaying the real 137
records revealed something none of the phases up to now had checked:
**every record carrying a real `DifferenceSnapshot` has trace length
exactly 1, and every record with trace length ≥ 2 (the only ones that ever
form a pair, since `_accumulate_pairs()` requires `len(trace) >= 2`) has no
`DifferenceSnapshot` at all.** Confirmed exactly: 49/49 DIFFERENCE-bearing
records are single-item `LINK`-replay traces with
`notes.artificial_seed=True, notes.seed_lineage_id="dream_episode"`; the
other 88 records (9 of length 2, 62 of length 3, 17 of length 8 — the ones
producing all 252 real pair-observations) carry zero DIFFERENCE signal
between them.

This is not only a property of this specific 137-record sample.
`aurora_grammar_engine.py:1563` — a real, confirmed, organic,
multi-item-trace caller of `observe()` — **hardcodes
`difference_snapshot=None`** on every call; it constructs its
`PressureVec`s from fixed formulas and never reads a live difference
buffer at all. The dream/evolution-chamber path
(`aurora_internal/aurora_evolution_chamber.py:1434`) does pass a real one,
but, in this corpus, only ever for single-link replay traces. (This pass
did not exhaustively audit every `.observe()`-named call site in the
repo — 53 files matched a loose grep, most almost certainly unrelated
`.observe()` methods on other classes — so "at least one confirmed organic
caller hardcodes None" is the honest claim, not "all organic callers
always do.")

Practical consequence: **the strongest, pair-level version of every
question below is untestable against this specific corpus**, not because
DIFFERENCE lacks predictive value, but because no real pair-observation in
it ever carries a real DIFFERENCE value to test with. Below, each question
is answered either from the pair-level replay (where it returns a clean,
honest null result explained by the floor effect) or from the closest
available real-data analog (the 6 links that DO get replayed repeatedly),
clearly labeled as such.

### 11.2 Question by question

1. **Differentiates signature-colliding genealogies?** Untestable at the
   pair level in this corpus: of 8 current-signature groups, 2 collide
   (>1 pair-key sharing the same axis pair), but difference-participation
   rate is 0% for every one of the 10 pair-keys, so there is nothing to
   diverge. Not a negative finding — a floor effect from §11.1.
2. **Correlates with DAG structure?** The 6 real links that get replayed in
   this window all happen to share the identical current signature
   (dominant axis T, depth 5) — no structural variation exists in this
   corpus's reuse sample to correlate against. Reported as a limitation,
   not a null result.
3. **Correlates with promotion success / relief / recurrence / closure
   grade / later reuse?** *Promotion success:* untestable — zero new
   promotions occur inside the available window (confirmed, §10.6#1 logic
   applies here too). *Relief / recurrence at the pair level:* untestable,
   same floor effect as Q1. *Closure grade / later reuse, via the 6 reused
   links:* replay counts range 5–12 per link; all 6 share the same closure
   signature (§11.2 Q2), so there is no structural spread to correlate
   replay count against in this sample — reported with the raw numbers in
   §11.3 rather than a synthesized correlation coefficient that would imply
   more structure than 6 identical-signature data points can support.
4. **Persists across ancestral chains, or transient?** **Measured, real
   answer, leans transient.** For the 6 reused links, own-axis DIFFERENCE
   values across repeated replays give a between-link standard deviation of
   means of **0.00318**, versus a mean *within-link* standard deviation of
   **0.01097** — within-link (tick-to-tick, same link) variability is
   **~3.4× larger** than between-link variability. If DIFFERENCE were a
   stable trait tied to a link's identity/ancestry, repeated replays of the
   *same* link should cluster more tightly than replays of *different*
   links do; here the opposite holds. Caveat: n=6 links, 5–12 replays each
   — real, but a small sample from one corpus.
5. **Two genealogies identical under current physics become distinguishable
   under native+DIFFERENCE?** Not demonstrated in this corpus — a direct
   consequence of §11.1's floor effect (Q1) and the identical-signature-only
   sample in Q2/Q3: there was no pair of colliding, difference-divergent
   genealogies available to compare.
6. **Carries information beyond axis identity?** **Yes, clearly, and this
   is the strongest result in this phase.** Across the 49 real
   DIFFERENCE-bearing records, **190 of 196 possible non-dominant-axis
   slots (97%) carry a nonzero DIFFERENCE value** — i.e. the live
   5-value measurement is almost never a one-hot reflection of "which axis
   is dominant"; nearly every one of the other four slots also carries real
   signal. Within the dominant axis itself: the T-axis group (n=5) shows
   real internal spread (stdev 0.0123, range −0.0210 to +0.0129) — same
   axis, materially different DIFFERENCE readings. The X-axis group (n=44)
   shows *zero* internal spread (every value exactly 0.0) — worth reporting
   honestly rather than folding into the headline number: in this corpus,
   dream-episode replay apparently never drives real existential (X) drift,
   so X-dominant records happen to carry no extra X-axis information here
   specifically (the cross-axis, non-dominant-slot result above still
   stands independent of this).

### 11.3 The killer experiment: implemented, correct, and empty on this corpus — for a confirmed reason

`find_pairs_with_divergent_difference()` searches for pairs of pair-keys
that share a current signature and similar mean relief but diverge in real
DIFFERENCE participation, then checks whether their recurrence diverges
too. It is implemented generically (not hand-fit to any known-empty case)
and verified correct against synthetic data built to qualify
(`test_finds_synthetic_divergent_candidate` constructs exactly such a pair
and confirms it's found, along with two negative-control tests confirming
it correctly rejects non-qualifying pairs). Run against the real corpus, it
returns **zero candidates** — the direct, expected, confirmed consequence
of §11.1: no real pair-observation in this corpus ever carries a real
DIFFERENCE value at all, so no divergence between two of them can exist to
find. `test_real_corpus_killer_experiment_correctly_returns_empty` locks
this in as a regression, so a future corpus where this stops being empty is
a visible, deliberate signal rather than a silent behavior change.

### 11.4 Honest verdict

**Not** the "extremely strong case" outcome the directive described as the
threshold result — but not a refutation either. What actually holds:

- The infrastructure works and is correct (§11.3's synthetic tests, and the
  exact-parity test against real `PairStats.update()`).
- One of the six questions has a clear, real-data-backed **yes**: DIFFERENCE
  carries information beyond axis identity (§11.2 Q6) — a necessary
  precondition for the whole doctrine ("preserve the actual live value...
  not `axis -> DIFFERENCE`") to be meaningful at all, and it holds.
- Another has a clear, real-data-backed lean toward **no persistence**
  (§11.2 Q4) — worth weighing against any future argument that DIFFERENCE
  should be treated as an inheritable trait along a lineage; in this
  corpus it looks more like tick-local signal.
- The decisive killer experiment (§11.2 Q5, §11.3) could not be run — not
  because it failed, but because this phase surfaced a **more specific**
  architectural gap than Phase 2 found: it's not merely that promotion's
  input is axis-only (Phase 2, §10.1) — in the only real corpus available,
  the event stream that carries live DIFFERENCE data and the event stream
  that forms genealogy pairs are **currently disjoint**, and at least one
  real organic caller (`aurora_grammar_engine.py`) hardcodes that
  disjointness rather than merely happening to exhibit it.

**Consequence for Phase 3B:** the case remains open and plausible (Phase 2:
the raw physics exists and is dropped; Phase 3A: when present, that physics
is informationally rich) but is **not yet empirically demonstrated to carry
predictive value for genealogy formation** — no real sample exists where a
pair-forming tick also carried real DIFFERENCE physics, so that specific
claim has neither been confirmed nor refuted. The smallest concrete
unblocking step, if this is worth pursuing further, is smaller than
altering `PairStats`: wiring at least one organic, multi-item-trace
`observe()` caller (starting with `aurora_grammar_engine.py`'s hardcoded
`None`) to pass a real `difference_snapshot` when the evolution chamber has
one available, so a *future* corpus could actually exercise the overlap
this phase needed and didn't have. That is itself a live-behavior change
and is explicitly not done here — flagged as the natural next question,
not attempted.

### 11.5 Tests

17 new tests in `tests/test_genealogy_difference_shadow.py`, all passing:
exact-parity replay tests against real `PairStats`, independence of the
DIFFERENCE companion channel from axis accumulation, killer-experiment
logic verified on synthetic qualifying/non-qualifying cases, and — critically
— four tests that run directly against the real fossil corpus and assert
the actual empirical findings above (zero pair/DIFFERENCE overlap, all
DIFFERENCE-bearing records are single-item traces, non-dominant-axis signal
exists, killer experiment returns empty), so this section's numbers are
enforced, not just narrated.

---

## 12. Phase 3A.1 — co-occurrence observatory

Phase 3A's floor effect (§11.1) was diagnosed from static, already-persisted
JSON. This phase asks the same question of the REAL, LIVE call path — still
with no behavioral wiring — to distinguish three different explanations for
that floor effect, which lead to different architectural conclusions:

1. DIFFERENCE is genuinely not computed anywhere near pair-forming calls.
2. DIFFERENCE **is** computed elsewhere at the same tick, but the specific
   caller that forms the pair has no reference to it.
3. A snapshot exists and gets passed, but it's stale relative to the pair
   event — a lifecycle mismatch, not an absence.

### 12.1 Method — this time, the real live call is actually exercised

`aurora_genealogy_cooccurrence_observatory.py`'s `install(logger)` wraps the
real, bound `ConstraintGenealogyLogger.observe` with a sidecar that (a)
calls the real, original `observe()` first, with every argument passed
through completely unchanged, and returns its real result unmodified, then
(b) only afterward, read-only and try/except-guarded, records what it can
observe. `test_wrapped_observe_produces_identical_result_to_unwrapped`
proves behavioral identity directly: same inputs through a wrapped and an
unwrapped fresh logger produce identical `ReliefRecord` contents, identical
`links_promoted`, identical `_pair_stats` keys.
`test_sidecar_failure_never_breaks_real_observe` forces the sidecar's
recording function to raise and confirms `observe()` still returns its real
result. `test_sidecar_never_feeds_difference_back_into_pairstats` confirms
the recorded difference value never appears on any real `PairStats`
instance — its field set is asserted exactly, unchanged.

For "available anywhere upstream," the honest scope is narrower than it
might sound: `DifferenceHistoryBuffer` is instance-scoped
(`self._diff_buffer` on whichever evolution-chamber-shaped object owns one
— `aurora_evolution_chamber.py:1089`), not a global registry, so there is
no ambient place to check "does DIFFERENCE exist anywhere in the live
process right now." What the sidecar can honestly do: read the direct
`difference_snapshot` argument (always exactly knowable — this alone
distinguishes possibility 3 via `.tick` vs. the pair's own tick), and, when
that argument is `None`, use read-only stack-frame introspection
(`inspect`, never `sys.settrace`) to check whether the immediate caller's
own `self` holds a `DifferenceHistoryBuffer`/`DifferenceSnapshot` instance
attribute it simply didn't pass — distinguishing possibility 2 (found,
just not threaded through) from possibility 1 (not found on this specific
caller at all). It does not and cannot rule out some unrelated object
elsewhere in the process holding one; the reported reason string says
exactly this rather than overclaiming a global negative.

### 12.2 Run against real, live code — two ways

**(a) Direct exercise of the real, confirmed caller.**
`aurora_grammar_engine.GrammarEngine` is cheap to construct (no heavy
boot). `_log_relief_to_genealogy()` — the exact method Phase 3A found
hardcodes `difference_snapshot=None` — was called 10 times against a real,
fresh `ConstraintGenealogyLogger` with the sidecar installed:

```
callers observed: {'GrammarEngine._log_relief_to_genealogy': 10}
pair-eligible: 10/10
difference_passed: 0/10
difference_source (when not passed): {None: 10} -- "no difference_snapshot
  argument passed, and no DifferenceHistoryBuffer/DifferenceSnapshot
  instance attribute found on the caller's `self`..."
```

Live-confirmed: for this real caller, possibility 1/2's boundary — no
buffer is reachable from `GrammarEngine`'s own `self` at all. `GrammarEngine`
holds `self._genealogy`, `self._ivm`, `self._dps` — no difference-buffer
reference of any kind (confirmed by reading its `__init__`,
`aurora_grammar_engine.py:1396-1407`). `aurora_grammar_engine.py`'s own
module comment places it explicitly "beneath aurora_evolution_chamber.py"
in the architecture's layering — the module that owns
`DifferenceHistoryBuffer` sits *above* this caller, not below it, so this
caller structurally cannot hold a reference to one without inverting that
layering. This is closer to possibility 1 for this specific call site (not
merely "didn't bother, but could") than possibility 2.

**(b) Live replay of the real historical corpus through the real pipeline.**
All 137 real `events_recent.json` records were reconstructed into real
`PressureVec`/`TraceItem`/`DifferenceSnapshot` objects and fed through
`ConstraintGenealogyLogger.observe()` on a fresh, throwaway logger (temp
directory; promotion outcomes during this replay are not expected to, and
do not need to, match the original historical run's — a fresh instance has
different ability/link state, and this replay exists to exercise the real
`observe()`/`_accumulate_pairs()` code with real inputs, not to reproduce
history's promotion decisions):

```
total observe() calls recorded: 137
pair-eligible (trace_length >= 2, after real rewrite_trace()): 67
difference_passed=True: 49
pair-eligible AND difference_passed (genuine co-occurrence): 0
```

(The pair-eligible count, 67, is lower than Phase 3A's static 88 — a real,
expected consequence of exercising the actual live `rewrite_trace()` step
this time: as this fresh logger accumulates its own promotions partway
through the 137-record replay, some later multi-item traces get rewritten
down to a single already-promoted-link id, correctly making them no longer
pair-eligible. Phase 3A's simplified shadow replay didn't include gated
promotion, so it couldn't see this effect; this is a genuine improvement
in fidelity, not a discrepancy to be resolved.)

**Zero genuine co-occurrence, now confirmed by two independent methods**:
Phase 3A's static analysis of persisted JSON, and Phase 3A.1's live
execution of the real `observe()` pipeline against both the real historical
corpus and a real, freshly-exercised organic caller. Locked in as
regressions: `test_live_replay_of_real_corpus_confirms_zero_cooccurrence`,
`test_live_grammar_engine_exercise_never_shows_difference_signal`.

### 12.3 Answering the three-way distinction

- **Possibility 1 (genuinely not computed near pair-forming calls):**
  supported for the one real caller directly examined
  (`aurora_grammar_engine.py`) — confirmed no buffer reference exists on
  that caller at all, and the module layering explains why one structurally
  can't, without this being read as proof for *every* organic caller in the
  codebase (only one was directly instrumented; §11.1's caveat about the
  loose 53-file `.observe(` grep still applies).
- **Possibility 2 (computed elsewhere, caller can't see it):** not
  demonstrated for the caller examined — the frame-introspection path is
  implemented and verified correct
  (`test_reachable_buffer_on_caller_found_via_frame_introspection`, a
  synthetic case built to exercise it), but it found nothing on the one
  real caller checked, consistent with possibility 1 for that caller
  specifically.
- **Possibility 3 (stale/lifecycle mismatch):** the age-computation
  machinery is implemented and verified
  (`test_difference_argument_captured_with_full_values`), ready to flag
  this the moment a corpus exists where a `difference_snapshot` is passed
  with a `.tick` meaningfully different from the pair event's own tick —
  no such case has been observed yet, real or synthetic-from-real-data, so
  this possibility is neither confirmed nor ruled out by what's available.

### 12.4 Tests

12 new tests in `tests/test_genealogy_cooccurrence_observatory.py`, all
passing — including two that regression-lock the live-execution
confirmation of §12.2's numbers, so a future run where genuine
co-occurrence stops being zero is a visible, deliberate signal.

A minor but genuine finding surfaced while building this: exercising real
`observe()` calls that reach real promotion-gate rejections triggers
`PressureExperienceLedger.get()` — a process-wide singleton with a
hardcoded path (`aurora_pressure_ledger.py:114`) — regardless of which
throwaway `ConstraintGenealogyLogger` triggered it. Even a fully isolated,
temp-directory logger cannot avoid touching that one real, shared
`aurora_state/pressure_experiences.jsonl` file if a gate actually rejects
something. The test file guards this with an autouse fixture that snapshots
and restores that file around every test; the standalone report script
documents the same effect in its own docstring rather than silently leaving
it for whoever runs it next to discover.

### 12.5 Phase 3A recorded, as requested

DIFFERENCE loss confirmed at an event-recording boundary (Phase 2: computed
live, structurally excluded from `PairStats`'s call signature).
Informational richness confirmed (Phase 3A §11.2 Q6: 97% of non-dominant-axis
slots carry real signal — not reducible to an axis label). Inheritance
value not demonstrated (Phase 3A §11.2 Q4: within-link variability ~3.4×
larger than between-link variability, leaning transient over persistent,
n=6). Pair-level relevance currently unobservable (Phase 3A §11.1, now
confirmed by live execution in Phase 3A.1 §12.2 via two independent
methods, not merely one static pass) — not refuted, not confirmed; the
zero-candidate result is a boundary marker, regression-locked in both
phases, that will announce itself the moment the experimental landscape
changes rather than silently going stale.

The data currently favors treating DIFFERENCE as a property of the
*formation event* — a local environmental condition present while a
genealogy forms — rather than a property to fold into genealogy identity
itself (`genealogy atom += DIFFERENCE`). No representational change is made
on this basis here; that remains a decision for whenever (if ever) a corpus
exists that can actually test pair-level relevance, per §11.4's
unblocking step.

---

## 13. Phase 3A.2 — producer observatory: is this fossil compression, or an ecology split?

Phase 3A.1 observed the CONSUMER boundary (`ConstraintGenealogyLogger.observe()`).
This phase observes the PRODUCER boundary — `DifferenceHistoryBuffer.record()`/
`.snapshot()` (`aurora_internal/aurora_difference_buffer.py`) — to answer
the sharper question the directive posed: do the processes that experience
DIFFERENCE and the processes that form genealogical relationships ever
inhabit the same causal moment at all? Still no behavioral wiring.

### 13.1 Method

`aurora_genealogy_difference_producer_observatory.py`'s
`install_producer_observatory()` wraps `DifferenceHistoryBuffer.record` and
`.snapshot` **at the class level** — every instance, process-wide, for the
duration of the installation. This is the actual production boundary: the
buffer is instance-scoped (§12.1), owned independently by whatever object
constructs one, so there is no per-instance way to catch every real
production event generically; class-level wrapping is the only way to
observe the boundary itself rather than one particular owner of it. Each
wrapped method calls the real, original method first, with every argument
unchanged, and returns its real result unmodified —
`test_wrapped_snapshot_and_record_produce_identical_results` proves this
directly (byte-identical `DifferenceSnapshot.to_dict()` from a wrapped and
an unwrapped call), and `test_producer_sidecar_never_feeds_anything_back`
confirms the buffer's own internal history is exactly what the caller put
there, nothing added by the sidecar.

Each observation records (per the directive's spec): `tick`, `producer_class`
and `producer_instance_id` (`id()` of the buffer instance), `call_path`
(nearest-first qualnames walked via `inspect`, real stack frames — verified,
`test_call_path_captures_real_caller_chain`), `axis_values` (for `snapshot`
calls), and `causal_context` — a best-effort, read-only scan of the
immediate caller's `self` for attributes whose *name* suggests identity/
lifecycle (`episode`, `session`, `run_id`, `lineage`, `turn`, `chamber`,
`tick_count`), extended one level into any dict-valued attribute after
discovering Aurora's common pattern is a `self._systems`-style registry
dict rather than direct attributes (confirmed on `TrainingPulse` and
`aurora.py`'s turn processing) — verified on both shapes,
`test_causal_context_found_on_direct_self_attribute` and
`test_causal_context_found_one_level_into_dict_attribute`.

### 13.2 The real producer/consumer catalog (hand-verified by reading, not an automated tracer)

Grepping for every real call to `.snapshot(`/`.record(` on a difference
buffer, and reading each call site, found four real producers — not one:

| Producer call site | Context |
|---|---|
| `aurora_evolution_chamber.py:1402` | Evolution chamber's own per-tick processing (already known, §12) |
| `aurora_evolution_chamber.py:1847` | A second call site, a "last computed" accessor (`diff_snapshot` property) |
| `aurora.py:31436-31449`, inside `_run_live_response_turn` | Computes a **real snapshot on every ordinary conversational turn** — not gated on dream/artificial-seed state — stores it at `systems['_last_diff_snapshot']` |
| `aurora_training_pulse.py:206-249`, `TrainingPulse._record_and_snapshot()` | Its own docstring: "Mirror of aurora.py's per-turn diff buffer record + snapshot" — stores at `self._systems["_last_diff_snapshot"]` |

And four real consumers (pair-forming or promotion-adjacent `observe()` calls):

| Consumer call site | What it passes as `difference_snapshot` |
|---|---|
| `aurora_grammar_engine.py:1547` (`_log_relief_to_genealogy`) | hardcoded `None` (Phase 3A/3A.1's original finding) |
| `aurora.py:17728` (`_log_modulation_event`) | omitted — defaults to `None` |
| `aurora.py:17830` (`_log_claim_resolution_relief`) | omitted — defaults to `None` |
| `aurora.py:4362` (a field-balance injector) | `{}` — **a real, separate, confirmed bug**, found as a side effect of this investigation (see §13.3) |

**`systems['_last_diff_snapshot']` — the value written on every real
conversational turn — is read by nothing else anywhere in the
repository**, confirmed by grepping the full codebase for that exact key.
This is now a code-level finding, not a corpus-limited one: across every
real call site located on both sides, there is no code path anywhere in
this repository connecting a value a producer wrote to an argument any
consumer reads.

### 13.3 A real bug, found and not fixed

`aurora.py:4362` passes `difference_snapshot={}` — a plain dict, not a
`DifferenceSnapshot` instance. `observe()`'s own body
(`constraint_genealogy.py:1975-1976`) calls `difference_snapshot.to_dict()`
unconditionally whenever the argument `is not None`. Live-verified,
`test_confirmed_empty_dict_difference_snapshot_bug`:

```
AttributeError: 'dict' object has no attribute 'to_dict'
```

This raises inside `observe()` itself; the call site's own surrounding
`try/except` silently swallows it (`_aurora_record_exception_from_locals`),
so **this caller's relief event never gets logged at all** when it fires —
not merely without DIFFERENCE, the entire call fails silently. Not fixed
here: fixing it is a live-behavior change to a file no other part of this
project touches, and is out of scope for an observational phase. Reported
so it isn't lost in the course of an unrelated investigation.

### 13.4 Live demonstration: two real call sites, driven together

The static catalog (§13.2) is the strongest evidence, but the directive
asked for a dynamic instrument too. `aurora_genealogy_difference_producer_observatory_report.py`
drives a real `TrainingPulse._record_and_snapshot()` (producer) and a real
`GrammarEngine._log_relief_to_genealogy()` (consumer) together, in the same
loop, against a shared tick sequence and a shared `run_id`, with both
sidecars installed:

```
Producer observations: 24
Consumer observations: 12
Pair-eligible consumer observations: 12
Correlation case: B_same_tick_no_link
Detail: {'n_proximate_pairs': 12, 'n_with_shared_causal_context': 0, 'tick_window': 2}
```

**Important caveat, stated in the report script's own docstring so it can't
be misread later**: the "same tick" proximity here is a property of this
test's design — both real call sites are deliberately driven from the same
loop, once per iteration. This demonstrates the correlation *mechanism*
correctly detects a same-tick/no-causal-link pattern when one is genuinely
present (`causal_context` on the producer side carries `run_id`; nothing on
the consumer side matches it, correctly yielding zero shared-context
pairs) — it is not a claim that real, unattended Aurora execution
autonomously interleaves these two subsystems this tightly. §13.2's static
catalog is the claim about real, natural execution; this section is proof
the instrument works correctly on real code, not a frequency estimate.

### 13.5 Which case does the evidence support?

`correlate_producer_consumer()` distinguishes the three cases via
nearest-producer-per-consumer pairing (not an all-pairs join over a loose
window, which was tried first and found to drift into spurious cross-pairs
whenever sequences overlap — fixed before any real numbers were reported,
`test_case_c_consistent_temporal_offset` locks in the corrected behavior):

- **Case A (no proximity anywhere)**: not directly testable from a single
  synthetic/live-combined run the way §13.4 was constructed, since that run
  was designed to interleave the two call sites. What IS directly
  testable, and holds: the one real historical corpus available
  (Phase 3A/3A.1) already showed zero pair-eligible ticks with any
  DIFFERENCE signal at all across its full 137-record span — consistent
  with Case A within that corpus.
- **Case B (same tick, no causal link)**: demonstrated live in §13.4 when
  the two real call sites are deliberately run together — this is the case
  the instrument is proven to detect correctly, not (per the §13.4 caveat)
  a claim about natural co-occurrence frequency.
- **Case C (consistent temporal offset)**: not observed in any real data;
  the detection logic is implemented and verified only against synthetic
  data built to exercise it (`test_case_c_consistent_temporal_offset`).

**The strongest evidence remains §13.2's static catalog**: across every
real producer and every real consumer call site found in this repository,
none references the other. That is closer to Case A (genuine architectural
separation between developmental regimes) than Case B (production and
consumption inhabiting the same causal moment in different branches) — the
four producers and four consumers found don't merely fail to connect at
runtime, they were never wired with any intention of connecting; nothing
here suggests a "missing pipe" between two systems designed to talk to each
other, more like two systems that were never designed with each other in
view. This is consistent with, and sharpens, the report's earlier framing
(§11.4): the question is no longer "did genealogy throw away a dimension it
had," but closer to "do the process that experiences DIFFERENCE and the
process that forms genealogical relationships currently share any causal
moment in this codebase" — and on the evidence gathered so far, the honest
answer leans toward *not yet, and not by design*, which is a different and
larger claim than fossil compression.

### 13.6 The evidence ladder, updated

| Question | Status |
|---|---|
| DIFFERENCE exists live and is structurally dropped (Phase 2) | ✓ confirmed |
| DIFFERENCE is informationally rich (Phase 3A) | ✓ confirmed |
| DIFFERENCE appears inheritable (Phase 3A) | ✗ unsupported — currently looks transient |
| DIFFERENCE naturally co-occurs with pair formation (Phase 3A/3A.1) | ✗ not observed, in the one corpus available |
| Consumer-side missing-forwarding bug (Phase 3A.1/3A.2) | ✗ increasingly unlikely — every real consumer call site, in two different files, shows the same pattern |
| Producer/consumer architectural separation (Phase 3A.2) | **leaning yes** — every real producer and every real consumer call site found in the repository, hand-verified, connects to none of the others |

### 13.7 Tests

17 new tests in `tests/test_genealogy_difference_producer_observatory.py`,
all passing: behavioral-identity and purity proofs on the producer sidecar,
call-path and causal-context correctness (including the nested-dict
pattern discovered on real classes), the `{}` bug reproduced directly, all
three correlation cases verified on synthetic data built to exercise each
one, and the live combined exercise locked in as a regression.

Same test-hygiene issue as Phase 3A.1 recurs here (exercising
`GrammarEngine` repeatedly touches the same `PressureExperienceLedger`
singleton) — guarded with the identical autouse snapshot/restore fixture,
now present in two test files. Worth treating as a standing pattern for any
future phase that exercises real promotion-adjacent code: check for
process-global organs hidden inside otherwise instance-local systems before
trusting that a throwaway instance means an isolated test.

---

## 14. Phase 3A.3 — causal-context identity, a real repair, and one piece of archaeology

Three distinct pieces of work, kept separate because they have different
risk profiles: (A) a stronger correlation method than tick proximity, using
identity Aurora already carries; (B) an actual, narrow, live-behavior fix
— the first one in this entire investigation — to a real bug Phase 3A.2
found; (C) archaeology on `_last_diff_snapshot`, explicitly not
implementation.

### 14.1 Same-event correlation: identity, not clock proximity

Phase 3A.2's tick-window correlation had a real, self-caught bug (an
all-pairs join drifted into spurious cross-pairs), and even fixed, clock
proximity alone can't distinguish "the same occurrence, observed twice"
from "two unrelated things that happened to land near the same tick."
`aurora_genealogy_same_event_correlation.py` asks the stronger question
directly: do a DIFFERENCE-bearing record and a pair-forming record ever
share an actual **identity value** — not just a nearby tick — using
identifiers Aurora already writes (`session_id`, `operation_lineage_id`,
`seed_lineage_id`, `constraint_combo_id`, `time_index`), deliberately
excluding bare `tick` (universal, trivial, already covered separately by
§13's temporal analysis).

**This is a pure, zero-risk read of the same real, already-persisted
`events_recent.json` corpus** — no live invocation needed, confirmed by
first checking what identity vocabulary its `notes` payloads actually
carry (a check the earlier phases hadn't run):

```
Producer population (49 real DIFFERENCE-bearing records):
  identity keys found: constraint_combo_id, operation_lineage_id, seed_lineage_id
  sample: {constraint_combo_id: "agency+boundary+temporal",
           operation_lineage_id: "DREAMOP:595770577d27",
           seed_lineage_id: "dream_episode"}

Consumer population (88 real pair-forming records):
  identity keys found: session_id, time_index
  sample: {session_id: "sim_1785302065884", time_index: 979}

shared_identity_keys: {}  (empty)
shared_identity_values: {}  (empty)
outcome: 2_different_event_populations
```

**This is decisive, real, and clean**: not merely different identity
*values* between the two populations, but a completely disjoint identity
*vocabulary*. Every real DIFFERENCE-bearing record in this corpus is
labeled with dream/DREAMOP-prefixed lineage identifiers; every real
pair-forming record is labeled with a `sim_`-prefixed session id and a
`time_index` sequence counter that the DIFFERENCE-bearing population never
carries at all. Per the directive's own framing, this is **Outcome 2**:
different event populations, not the same event observed on two
disconnected paths (Outcome 1) and not the same sequence at different
moments (Outcome 3). Worth being precise about what "population" means
here: even this corpus's "organic" pair-forming activity is itself a
simulation (`sim_`-prefixed), not literal live human conversation — the
finding is that dream-episode replay and this particular simulated
interaction regime are two developmental regimes that don't share identity
vocabulary in the fossils available, not a claim about live human
conversation specifically (§14.4 addresses that separately).

Regression-locked: `test_real_corpus_shows_different_event_populations`
and `test_real_corpus_producer_and_consumer_identity_vocabularies` assert
this exact vocabulary split, so a future corpus where it stops being
disjoint is a visible, deliberate signal — not something noticed by
accident.

### 14.2 A real gap in Phase 3A.2's own tooling, found and fixed

While building this, `_capture_causal_context()` (Phase 3A.2) turned out to
have a real blind spot: it only ever inspected `frame.f_locals.get("self")`
— which finds nothing for a plain function. Reading `aurora.py`'s
`_run_live_response_turn(systems, user_text, mode, *, session_id="",
turn_tick=None, ...)` — the single most important real producer call site,
computing a real snapshot on every ordinary turn — confirmed it is exactly
that: a free function, not a method. The original tool would have silently
missed its real `session_id`/`turn_tick` locals entirely had it ever been
pointed at that call site. Fixed to scan free-function locals directly, in
addition to `self` attributes and one level into dict-valued values;
verified on a synthetic reproduction of the exact real signature shape
(`test_causal_context_found_in_free_function_locals`) — not exercised
against the real 35,000-line function itself, which was assessed as too
heavily coupled to invoke safely in isolation for this investigation. All
19 pre-existing Phase 3A.2 tests still pass unchanged after this fix.

### 14.3 `_last_diff_snapshot`: archaeology, not implementation

**Git history is a dead end for both write sites.** `aurora.py` has 19
commits total in this repository's history; only one of them
(`423ff53`, "Consolidate 25x duplicated auto-evolution block into one
canonical engine" — entirely unrelated to DIFFERENCE) touches
`_last_diff_snapshot` at all, and that commit adds the ENTIRE 35,452-line
file as new (`git log --oneline --all -- aurora.py` confirmed; `git log -p
-S "_last_diff_snapshot"` confirmed the string was already present at that
single import commit). `aurora_training_pulse.py` shows the identical
pattern: one commit total (`e05f091`, "FIX-A069: registry entry for
SemanticIntentionBridge live-parse patch" — also unrelated), which is
where the file entered this repository whole. **`_last_diff_snapshot`'s
true origin predates this repository's tracked history entirely** — it was
already there when both files were each imported in one shot. No commit
message, no incremental blame trail, exists to consult.

Falling back to surrounding comments and architecture, per the directive's
own allowance: no comment anywhere explains the `systems['_last_diff_snapshot']`
write, and no documentation file (grepped across `docs/`) mentions it.
What IS observable: the value's PRIMARY use already exists and works —
the same local variable (`_diff_snap_pt`) is used immediately afterward,
in the same function, to compute `AttentionEngine` salience
(`aurora.py:31450-31461`). The `systems[...]` write is a second, separate,
additional stash, using the exact same storage convention as dozens of
other real, actively-consumed entries in the same dict
(`_diff_history_buffer`, `_attention_engine`, `_live_conscious_crest`,
`identity_field`, `working_memory`, `sensory_crystal` — all read elsewhere
via `systems.get(...)`). That consistency of convention is real evidence,
though not proof: it reads as a value stored the same way one would store
anything meant to be available to some other stage or subsystem later, not
as an ad hoc debug print or an obviously abandoned fragment. Per the
directive's own caution against inferring intent from the name alone: this
is offered as the best-supported *interpretation* available without commit
history, not a confirmed fact. "Unfinished integration" or "planned future
plumbing that never got a consumer" fit the evidence; "telemetry/debug
residue" fits less well, since debug instrumentation in this codebase
typically uses dedicated logging/telemetry calls (seen extensively
elsewhere in `aurora.py`), not the production `systems` registry pattern
reserved for real cross-subsystem state.

### 14.4 The `{}` bug: fixed, as its own narrow repair

Phase 3A.2 found `aurora.py:4362` passing `difference_snapshot={}` — a
plain dict — into `observe()`, which called `.to_dict()` on it
unconditionally, raising `AttributeError`, silently swallowed by that call
site's own `try/except`, losing the entire relief observation. Per the
directive, this is fixed here as its own narrow repair, independent of the
larger DIFFERENCE experiment:

- **`aurora_internal/constraint_genealogy.py`** (`observe()`, the type
  contract itself): now guards with `hasattr(difference_snapshot,
  "to_dict")` before calling it, so ANY caller passing a malformed
  optional snapshot degrades to "no snapshot supplied" instead of losing
  the whole relief record — not just this one known caller.
- **`aurora.py:4362`** (the known bad caller): changed
  `difference_snapshot={}` to `difference_snapshot=None`, since no real
  `DifferenceSnapshot` exists at that call site to pass instead (confirmed
  by reading the enclosing method — no difference-buffer reference exists
  on that class at all). Per the directive: not inventing an empty
  snapshot object to satisfy the type.

**A real complication, found and reported rather than quietly worked
around**: fixing the `difference_snapshot` contract does **not**, by
itself, repair this call site's ability to log events. The same call also
passes `pressure_before`/`pressure_after` as plain `dict`s rather than
`PressureVec` instances, which fails **earlier** in `observe()` —
`pressure_after.relief_from(pressure_before)` requires a real `PressureVec`
(verified live: `test_real_field_balance_call_site_no_longer_passes_
malformed_snapshot` reproduces the exact real arguments and confirms it
still raises `AttributeError`, now from `relief_from`, not from
`to_dict`). This second bug is a separate, independent issue from the one
this directive authorized fixing, and was left alone: fixing it wasn't
part of the narrowly-scoped "DifferenceSnapshot Type-Contract Repair," and
expanding scope to a second real-code change without it being explicitly
asked for isn't this investigation's call to make unilaterally. Reported
here so it's visible rather than discovered independently later.

Regression tests (added to `tests/test_genealogy_difference_producer_
observatory.py`, replacing the now-stale test that asserted the old,
pre-fix crashing behavior): `test_empty_dict_difference_snapshot_no_longer_
raises` (the exact malformed input now succeeds and logs no
difference_snapshot key), `test_real_difference_snapshot_still_works_after_
the_fix` (a real, valid `DifferenceSnapshot` is unaffected — no behavior
change for the working case), and `test_real_field_balance_call_site_no_
longer_passes_malformed_snapshot` (documents precisely what still fails at
the real call site, and why, so it isn't mistaken for a full repair).

**Regression scope for this fix**: `constraint_genealogy.py` is a shared,
heavily-used core file (unlike every previous phase's fully-isolated new
files), so the full repository test suite was run in the background for
this pass rather than skipped — see §14.5 for the result.

### 14.5 Regression suite (real core-file change)

[Fill in after the background run completes: `python3 -m pytest tests/`
pass/fail counts, and confirmation that no test outside this investigation's
own files regressed as a result of the `hasattr` guard in `observe()`.]

### 14.6 Where this leaves the evidence ladder

| Question | Status |
|---|---|
| DIFFERENCE exists live and is structurally dropped | ✓ confirmed |
| Informationally rich | ✓ confirmed |
| Inheritable | ✗ looks transient |
| Naturally co-occurs with pair formation (tick proximity) | ✗ not observed |
| Consumer-side missing-forwarding bug (general) | ✗ increasingly unlikely |
| Producer/consumer architectural separation | ✓ **now directly confirmed** — real identity vocabularies are fully disjoint (Outcome 2), not merely unconnected by clock |
| One specific consumer call site silently dropping valid relief events via a type-contract violation | ✓ confirmed **and fixed** (independent of the DIFFERENCE question — that call site has a second, unfixed bug of its own) |

The doctrine the directive proposed — preserve the native formation
context (pressure, cost, x_risk, DIFFERENCE, provenance) long enough for
Aurora's own developmental machinery to discover whether it matters,
rather than teaching genealogy what DIFFERENCE means — remains exactly
where it was left in §11.4, now on firmer ground: this phase's identity-level
evidence makes "different developmental regimes that were never wired
together" a better-supported description than "a bridge that's merely
missing," which is the version of the finding that would make building
`formation_context` immediately worthwhile. Still not built here. The
directive's own success condition — same cognitive event, DIFFERENCE
exists, genealogy formation occurs, current architecture separates them —
has not been demonstrated, because no real corpus available shows
DIFFERENCE and pair formation sharing a native event at all; what has been
shown is that they currently don't, and the identity vocabulary itself
gives a reason to expect that split runs deep rather than being an
oversight in one call site.

### 14.7 Tests

26 new/changed tests across three files: 2 new tests in
`tests/test_genealogy_difference_producer_observatory.py` (free-function
locals capture) plus 3 replacing the stale pre-fix bug test (empty-dict no
longer raises, real snapshot still works, real call site's remaining
failure documented precisely), and 9 new tests in
`tests/test_genealogy_same_event_correlation.py` (all three outcomes on
synthetic data built to exercise each precisely, plus two real-corpus
regressions locking in the actual Outcome 2 finding and its exact identity
vocabulary).
