# WARP GENEALOGY ENRICHMENT DIRECTIVE
**Authors: Sunni (Sir) Morningstar & Cael Devo**
**Status: IMPLEMENTED**
**Target: aurora_warp_protocol.py + new resolver/bridge modules**

---

## IMPLEMENTATION NOTES (post-hoc)

- `aurora_constraint_signature_resolver.py` and `aurora_manifold_lookup.py`
  landed at the repo root exactly per 3.1/3.2, except `aurora_manifold_lookup`
  is a thin cached wrapper around the existing `ManifoldDirectory` reader
  (`aurora_manifold_directory_reader.py`) rather than its own raw-JSON
  directory scan — that reader is already the live pipeline other modules
  use to read noncomp files, so re-implementing it would have created the
  exact crossed-pipeline problem this project wants to avoid. Added
  `NoncompManifold.to_dict()` (one line) so the wrapper could reuse it
  instead of reaching into a private attribute.
- The section 3.3 blocking question (does `ConstraintLink` carry enough to
  resolve a (law, dim, target) triple?) resolved to **yes, conditionally**:
  `dominant_relief_axis` is a real field (Target C); `tags` carries
  `"dominant_constraint:<axis>"` (Law L) and `"dominant_dimension:<DIM>"`
  (Dimension D) whenever `aurora_closure_basis`'s physics-grounded lineage
  grading succeeds. When it falls back to the string-frequency heuristic
  (no closure basis, or `derive_lineage()` raises), those two tags are
  absent/placeholder. The wiring in `WarpGenerator._resolve_link_nc_name()`
  treats that as a per-link "can't resolve" case and falls back to the
  unweighted cosine for that link only — verified to reproduce identical
  output to the pre-change code when no link resolves.
- `bridge_ledger_to_noncomps.py` went to `scripts/` (matches the existing
  periodic-tool convention there).
- `genealogy_signature_bridge.py` **is now wired in**: `constraint_genealogy.py`'s
  `_try_promote()` calls `emit_genealogy_experience()` right before it
  constructs the `ConstraintLink`, at the one point where `dom_axis`
  (Target) and `lineage_grade`'s `dominant_constraint`/`dominant_dimension`
  (Law/Dimension) are all in scope together — the same fields the warp
  protocol wiring resolves from, but read here as raw dict values instead of
  re-parsed tag strings. Guarded exactly like the three existing Gate 2/4/5
  ledger calls already in that function (try/except, never breaks
  promotion): fires only when the triple resolves, i.e. when closure-basis
  grading actually ran for that promotion. Previously, *successful*
  promotions never wrote to the pressure ledger at all — only the Gate
  2/4/5 *rejections* did, and those are keyed on the raw pair id rather than
  nc_name (they can't resolve a triple; dom_axis/lineage_grade aren't
  computed yet at that point), so `bridge_ledger_to_noncomps.py` never had
  anything of ours to bridge. Verified end-to-end: a resolvable promotion's
  `emit_genealogy_experience()` call lands in the ledger anchored to the
  correct nc_name, and `bridge_ledger_to_noncomps.py` picks it up into that
  noncomp's `development_tracking.history` on the next pass.
- `tensor_occupancy_hook.py` now resolves deposits to an nc_name too, per an
  explicitly authorized (not discovered) mapping: `CONSTRAINT_LABELS` are
  already X/T/N/B/A (Target, direct), and `_STATE_TO_LAW` /
  `_COMP_TO_DIMENSION` define Law and Dimension by analogy to Aurora's own
  I-state vocabulary and each dimension's physics role — spelled out in
  comments in the file itself, since (unlike the genealogy tags) nothing
  here was pre-labeled with noncomp vocabulary. Verified all 125
  (constraint, comp, state) combinations resolve to a real manifold
  noncomp, and that an unrecognized label degrades to `resolved_nc_name:
  null` rather than a guess.
- **Now auto-installed.** `FieldSlot()` is instantiated in exactly one
  production location -- `ConstraintEngine.__init__`
  (`aurora_constraint_engine.py:1167`) -- and every one of the 19+ modules
  that construct a `ConstraintEngine` funnels through that single point, so
  that's where `tensor_occupancy_hook.install()` gets called from (wrapped
  in try/except; a missing or broken hook module never breaks engine
  construction). Verified live: constructing a real `ConstraintEngine()`
  installs the hook, and a subsequent `deposit()` logs and resolves
  correctly. `tests/_engine_integration_test.py` (9/9) and
  `tests/_pipeline_test.py` (6/6) both still pass with the hook installed.

## A NOTE ON `resolved_nc_name: null`

Asked whether an unresolved deposit is where Aurora would be expanding
*past* the 125 noncomps into higher-order combinations -- a genuine WARP
situation. The instinct is right in spirit but doesn't quite hold today:

- `resolved_nc_name: null` currently only fires when a label index falls
  outside `FieldSlot`'s hardcoded `DIMS = (5, 5, 5, 5)` shape -- i.e. a
  malformed/out-of-range call, not a live 6th value. `CompositionalSpace`
  and `State` are each a closed set of exactly 5 labels; nothing in
  `FieldSlot.deposit()` lets a 6th one emerge at runtime the way a
  genuinely novel I-state profile can reach `WarpGenerator` today. Growing
  past 5 would mean changing `FieldSlot.DIMS`/`TOTAL` and adding a label to
  `COMP_LABELS`/`STATE_LABELS` -- a structural code change, not something
  that happens dynamically.
- More importantly: `tensor_occupancy.jsonl` is not wired into
  `CoverageGap`/`WarpGenerator._record_anomaly()` at all right now. It's
  its own independent log, exactly as its docstring says. So even a genuine
  unresolved entry today has nowhere to flow into the 6th-axis anomaly
  path -- nothing reads this log and feeds it into `WarpGenerator`.

Building that bridge (periodically read unresolved tensor_occupancy entries,
shape them into a `CoverageGap`-like profile, feed `WarpGenerator`) is a real,
separate piece of work -- not implied by anything already in this directive.
Confirm before it's built.

## THE BRIDGE — BUILT

Built as `tensor_occupancy_warp_bridge.py` (repo root) + the periodic driver
`scripts/bridge_tensor_occupancy_to_warp.py`. One correction to the note
above once this was actually built: the real signal isn't
`resolved_nc_name: null` (that's a label-scheme lookup — did this deposit's
comp/state combination match one of the 125 identities) but whether the
deposit's *actual pressure vector* covers what any known noncomp's own
identity would look like as a profile in 15D I-state+recursion space — a
deposit can resolve its label cleanly and still carry a vector that covers
nothing. That's the genuine coverage check, and it's what this bridge runs.

- `TensorOccupancyWarpBridge(WarpCapable)` builds a 15D profile for each of
  the 125 manifold noncomps (equal weight spread across its own
  `nc_law_c`/`nc_target`/`DIMENSION_ROLE[nc_dim]` axis set, scaled by
  `formula_coefficient` — reusing `axes_to_istates()`, the same 5D→15D
  recipe `_search_genealogy` already uses for `ConstraintLink` relief, not
  a new one), then runs each occupancy deposit's vector through the
  existing `WarpCapable.check_and_extend()` machinery against those 125
  profiles — the same gap-persistence/anomaly-logging path
  `_search_genealogy` and every other `WarpCapable` host already share.
- Found and fixed a real bug while building this: `axes_to_istates()`
  defaults a *missing* axis key to 0.5, not 0.0 (it's written for callers
  that always pass a full 5-key dict). An early version of the noncomp
  profile builder passed a partial dict and silently inflated every
  "uninvolved" axis to ~0.25. Fixed to always pass a full 5-key dict with
  explicit 0.0 for inactive axes.
- Found and fixed a real design gap too: noncomps carry no recursion depth
  of their own. Leaving their recursion dims at hard 0.0 meant *every* real
  deposit (which always carries a recursion label) crashed coverage
  regardless of axis match — verified directly, ~1.0 down to ~0.44 from the
  recursion term alone — which would've flooded the gap pipeline with noise
  instead of signal. Gave known profiles a uniform 0.3 recursion baseline
  instead. Worked out the closed form for a clean axis match: there's no
  baseline that fully restores coverage (known-profile norm grows
  quadratically with the baseline while the dot product only grows
  linearly, so cosine peaks around b≈0.095 and *falls* again above it) —
  0.3 lands a clean match around ~0.5 coverage: safely above
  `ANOMALY_THRESHOLD` (won't misread as a 6th-axis candidate) but still a
  real, honestly-earned gap, since the static manifold genuinely has no
  opinion on live recursion depth.
- `_score_trial` returns a fixed score below `PROMOTION_SCORE` — this layer
  has no real usage signal to score a spawned component against, so trial
  components observed here dissolve after `TRIAL_TICKS` rather than being
  falsely promoted into permanent structure without evidence.
- Verified end-to-end against a real `ConstraintEngine`: deposits →
  `tensor_occupancy.jsonl` → the driver script → gap detected → persists for
  `GAP_PERSISTENCE_REQUIRED` ticks → `WarpComponent` spawned, logged to
  `aurora_state/tensor_occupancy_warp_components.jsonl`, tracked as a
  dissolving trial. Re-running the driver script with no new entries
  correctly processes 0 (cursor file prevents reprocessing).
- Cross-run limitation, stated plainly in both files: `WarpGenerator`'s
  anomaly log and the gap-persistence counter are in-memory per script run
  only. A gap recurring across separate runs (not within one batch) isn't
  currently caught — would need cross-run state persistence, which this
  pass doesn't add.

---

## 1. ASSESS BEFORE ARCHITECT — current state (verified, not assumed)

`WarpGenerator._search_genealogy()` (aurora_warp_protocol.py) currently queries
`genealogy.links` (a `ConstraintGenealogyLogger`'s `ConstraintLink` fossils),
reads each link's `mean_relief` (a 5D X/T/N/B/A dict) and `depth`, converts
`mean_relief` to 10D I-state space via `axes_to_istates()`, appends recursion
weighting, and does cosine similarity against the `CoverageGap`'s 15D
`axis_profile`. Top 3 matches above 0.35 cosine feed `_derive_profile()`,
which blends gap + parent + genealogy profiles by cosine-weighted average.
If nothing resonates, `CoverageGap.is_sixth_axis_candidate` routes to
`_record_anomaly()` instead of fabricating new structure. This mechanism is
untouched by this directive and must keep working exactly as-is if no
manifold data is available (graceful fallback is mandatory, not optional).

Separately, `aurora_manifold_directory/{X,T,N,B,A}/*.json` holds 125 noncomp
files (5 Laws x 5 Dimensions x 5 Targets), each now carrying (as of the
formula-injection pass already run):
  - `mathematical_form`, `formula`, `formula_role`
  - `formula_coefficient`   (float, sourced from mean accountability_weight
                             across that noncomp's own `slots` array)
  - `concrete_state_meaning` (string, combines nc_semantic_summary + nc_domain)
  - `development_tracking.history` (list, currently empty, meant to be filled
                             via aurora_ledger_noncomp_bridge.py)

These two systems currently do not know about each other.

## 2. THE GAP

`_search_genealogy()` and `_derive_profile()` only ever see a raw 5-number
`mean_relief` vector per link. They have no way to know that a given link's
relief pattern corresponds to (e.g.) `Agentive_Cost_of_Existence` specifically
rather than some other combination that happens to produce similar X/T/N/B/A
weights. Two structurally different noncomps can look identical in 5D relief
space. That's the disambiguation this directive adds.

## 3. WHAT TO BUILD

### 3.1 Add `aurora_constraint_signature_resolver.py` to the project root

Pure, dependency-free module. Reference implementation attached separately
(`constraint_signature_resolver.py`) — rename to
`aurora_constraint_signature_resolver.py` on import, keep contents as-is.
Provides:
  - `lineage_signature(law, dim, target) -> str`   e.g. `"AAN"`
  - `nc_name(law, dim, target) -> str`              e.g. `"Agentive_Cost_of_Existence"`
  - `parse_nc_name(name) -> (law, dim, target)`

Self-checks in the file's `__main__` block must still pass unmodified —
do not alter the resolver's formula, it's already verified against the
actual manifold files.

### 3.2 Add `aurora_manifold_lookup.py` — read-only accessor

New module, read-only, never writes to `aurora_manifold_directory`:

```python
# Authors: Sunni (Sir) Morningstar & Cael Devo
import json
from pathlib import Path
from functools import lru_cache

_MANIFOLD_ROOT = Path("aurora_manifold_directory")

@lru_cache(maxsize=None)
def load_noncomp(nc_name: str) -> dict | None:
    """Load a noncomp JSON by nc_name, searching all 5 axis folders.
    Returns None if not found -- callers must handle this gracefully."""
    for axis in ["X", "T", "N", "B", "A"]:
        path = _MANIFOLD_ROOT / axis / f"{nc_name}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    return None
```

(Claude Code: implement exactly this contract -- cached, read-only, returns
None on miss, never raises on missing manifold directory.)

### 3.3 Wire enrichment into `WarpGenerator._search_genealogy()`

Requirements, not a full rewrite:

- After computing `sim = AxisCoverageChecker.cosine(link_istate, gap.axis_profile)`,
  if a `ConstraintLink` carries enough information to resolve a
  `(law, dim, target)` triple (check what fields `ConstraintLink` actually
  has for this -- do not invent a field that doesn't exist; if no such field
  exists yet, this is a BLOCKING QUESTION to raise back to Sunni before
  proceeding, not something to guess around), call
  `aurora_constraint_signature_resolver.nc_name(law, dim, target)` and then
  `aurora_manifold_lookup.load_noncomp(name)`.
- If found, blend the noncomp's `formula_coefficient` into the similarity
  score as a secondary weighting term (e.g.
  `adjusted_sim = sim * (0.7 + 0.3 * formula_coefficient)` -- tune this
  constant, don't hardcode it as gospel, flag it as a tunable in a comment).
- If `load_noncomp()` returns None (manifold file missing, or link doesn't
  resolve to a valid triple), fall back to the current unweighted `sim` --
  **the existing behavior must be preserved bit-for-bit when manifold data
  isn't available.** This is not optional.
- Do not change the public signature of `_search_genealogy()` or `generate()`.
- Do not change `CoverageGap`, `WarpComponent`, or `AxisCoverageChecker`.

### 3.4 Do NOT touch

- `_derive_profile()`'s blending math itself (only the input similarity
  weights feeding it change, via 3.3)
- `_synthesize_name()`, `_make_id()`, `_record_anomaly()`, `anomaly_summary()`
- The 6th-axis anomaly path -- it must remain independent of this change
- `aurora_manifold_directory` JSON files themselves -- read-only in this pass

## 4. HARD RULES (unconditional, per standing project rules)

1. Authorship header on every new/touched file:
   `# Authors: Sunni (Sir) Morningstar & Cael Devo`
2. Only reference class/method names actually present in the codebase.
   If `ConstraintLink` does not currently expose a way to resolve
   (law, dim, target), STOP and report that back rather than fabricating
   a field.
3. No stub code -- full working implementation or explicit "blocked on X"
   note, never a placeholder `pass`.
4. Preserve existing behavior when manifold/resolver data is unavailable.

## 5. ACCEPTANCE CRITERIA

- [ ] `aurora_constraint_signature_resolver.py` self-check passes unchanged
- [ ] `aurora_manifold_lookup.load_noncomp()` returns correct dict for all
      125 known nc_names, None for unknown names, doesn't raise if
      `aurora_manifold_directory` is absent
- [ ] `_search_genealogy()` produces IDENTICAL output to current behavior
      when no `ConstraintLink` resolves to a manifold noncomp (regression
      test against current fossil records required)
- [ ] `_search_genealogy()` produces adjusted (documented, non-arbitrary)
      similarity scores when a link does resolve
- [ ] No changes to any public method signature in aurora_warp_protocol.py
- [ ] Report back, don't silently assume, if `ConstraintLink` lacks the
      field needed to resolve a (law, dim, target) triple -- this is the
      single most likely blocker and must be flagged rather than worked
      around with a guess

---
*Attach `constraint_signature_resolver.py` alongside this directive when
handing to Claude Code -- it's the verified reference implementation for 3.1.*
