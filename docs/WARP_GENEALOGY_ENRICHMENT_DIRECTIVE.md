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
- `tensor_occupancy_hook.py` stayed at repo root as a ready-to-install
  module, **not** auto-installed anywhere. Two reasons, not one: (1) unlike
  the genealogy case, resolving a deposit event to an nc_name has no
  existing field to hang off of — `FieldSlot.deposit()`'s
  (comp, state, recursion) indices don't correspond to a Dimension/Target
  anywhere in the codebase, so wiring that would mean inventing a mapping
  the hook's own docstring explicitly says not to force; (2) there's no
  single boot point to install it from even for the raw (non-resolved) log —
  `FieldSlot()` is instantiated independently in `ConstraintEngine.__init__`
  (`aurora_constraint_engine.py:1167`), which itself is constructed
  independently across 19+ call sites with no shared bootstrap. Left as the
  manual `import tensor_occupancy_hook; tensor_occupancy_hook.install(...)`
  its own docstring already describes.

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
