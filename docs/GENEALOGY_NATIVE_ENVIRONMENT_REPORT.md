# Genealogy-Native Representational Environment — Implementation Report

**Status:** Phase 1 (observational derivation + shadow comparison) implemented.
Phases 2–4 (live representational exposure, WARP coverage-authority change,
pressure-map expansion, meaning/understanding rewrite) intentionally **not**
started — the directive that scoped this work requires shadow validation
before any of those, and this report's job is to state honestly whether that
validation supports moving on, not to assume it does.

**Files added:** `aurora_genealogy_environment.py`,
`aurora_genealogy_environment_shadow.py`,
`tests/test_genealogy_environment_dag_preservation.py`. Nothing existing was
modified.

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
  - builds `dimension_distribution` by resolving every **consecutive
    transition** in the ordered sequence to a real genealogy atom
    (`NC:{a}>{b}`), looking up its actual `InteractionSlot` via
    `genealogy_atom_to_channel_pair()`/`slot_for_pair()`, and weighting by
    that slot's own `depth_score` — an existing field, not an invented
    constant;
  - chains **every** touched atom (not just 2) into one `root_slot` string
    and calls the existing `derive_lineage()` with it, producing a real
    `ConstraintLineage` (leverage_grade, formation_cost, viable_band_alignment,
    energetic_footprint, ontological_status) from the *full* preserved
    ancestry instead of the 2-atom synthetic one;
  - records `active_slots` and `provenance` in traversal order (this is what
    makes the signature order-sensitive), and a `signature_hash` over them.
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

### 2.3 Tests (`tests/test_genealogy_environment_dag_preservation.py`, 8 tests)

| Test | What it proves |
|---|---|
| `test_merged_axis_counts_treats_both_chains_as_identical` | Executes the **existing** `_axis_counts_from_item()` on two structurally different 3-link DAGs with the same per-axis histogram and shows it returns identical counts — reproducing the information loss this directive targeted, on real `ConstraintLink` objects. |
| `test_full_dag_derivation_distinguishes_the_same_pair` | Same two DAGs, run through `derive_environment_signature()`: identical `axis_distribution`, but different `chained_root_slot`, `active_slots`, and `signature_hash`. |
| `test_same_genealogy_under_different_labels_produces_identical_signature` | Identical DAG structure, entirely different link ids/"names": every structural field of the signature matches. The derivation never reads a name. |
| `test_different_genealogies_same_totals_can_differ` | Two 2-axis-histogram-equal DAGs differing only in recursion depth diverge in `recursion_distribution` and `signature_hash`. |
| `test_compare_against_core_crests_runs_and_stays_bounded` | Shadow comparison returns exactly the 8 authored keys, all cosine-bounded, and leaves `_CORE_CREST_PROFILES` byte-identical before/after. |
| `test_empty_genealogy_projects_to_empty_profile` | An unresolvable link id degrades to an explicit `insufficient_genealogy` flag rather than a fabricated signature. |
| `test_module_never_imports_warp_authority_surfaces` | Source-scans the new module for any reference to WARP's promotion/anomaly/generation entry points. None exist. |
| `test_derivation_and_comparison_are_pure` | Running derivation + shadow comparison creates zero new files under the real `aurora_state/` directory. |

All 8 pass.

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

## 5. Regression suite

Full existing test suite run: `python3 -m pytest tests/` (184 test files).
See the commit for the exact pass/fail/skip counts from this run — reported
literally as pytest printed them, no filtering. Zero existing test files were
modified; the two new files added are purely additive.

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

## 7. Remaining architectural gaps (confirmed, not interpretation)

1. `ConstraintLink` cannot express which of a constraint's 5 dimension-roles
   an operation engaged (§3) — this is the most consequential open gap for
   the "derived environmental signature" goal specifically.
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
