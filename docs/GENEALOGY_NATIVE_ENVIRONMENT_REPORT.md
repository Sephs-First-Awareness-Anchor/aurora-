# Genealogy-Native Representational Environment — Implementation Report

**Status:** Phase 1 (observational derivation + shadow comparison) implemented,
then **Phase 1.1 (edge-fidelity repair)** implemented on top of it after a
targeted re-review surfaced two real bugs in the Phase 1 derivation — see §8.
Both phases remain fully observational. Phases 2–4 (live representational
exposure, WARP coverage-authority change, pressure-map expansion,
meaning/understanding rewrite) intentionally **not** started — the directive
that scoped this work requires shadow validation before any of those, and
this report's job is to state honestly whether that validation supports
moving on, not to assume it does.

**Files added:** `aurora_genealogy_environment.py`,
`aurora_genealogy_environment_shadow.py`,
`tests/test_genealogy_environment_dag_preservation.py`. Nothing existing was
modified in either phase.

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
