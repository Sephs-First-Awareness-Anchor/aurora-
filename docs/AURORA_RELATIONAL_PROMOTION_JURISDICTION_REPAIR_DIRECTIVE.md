# Aurora Relational Promotion Jurisdiction Repair Directive

## Objective

Repair the first confirmed representational information-loss boundary in `aurora_internal/constraint_genealogy.py` without inventing new representational physics, a new promotion authority, a hardcoded dimension selector, or a Difference-specific promotion rule.

Aurora already constructs a richer intact representation relation containing actual coactivation, parent identity, constraint basis, generation/depth, causal consequence history, and observed Difference. The existing genealogy promotion gates remain the sole authority for deciding whether a relation earns persistence. The defect is jurisdictional: those gates currently judge the `PairStats` shadow as though it were the complete candidate, while the richer relation is consulted/attached only after promotion.

The repair must make the existing gates judge the actual already-observed relation context while preserving every existing gate and its semantics.

## Proven current chain

Current live order is effectively:

`observe -> Difference exists -> relation evidence is recorded -> PairStats accumulates axis relief/cost/X-risk -> _try_promote() judges PairStats -> lineage/dimensional structure is derived late -> _promoted_relation_metadata() attaches the richer relation after success`

Relevant existing machinery includes:

- `_update_representation_relation(...)`: first-class intact relation record.
- `_active_relation_context`: already carries live relation evidence, including `difference_values`.
- `PairStats`: statistical evidence for relief, positive relief, cost, risk, frequency and variance.
- `_try_promote(...)`: existing sovereign five-gate promotion authority.
- `_lineage_grade_for_pair(...)` / closure-basis machinery: existing physics-grounded structural/dimensional derivation.
- `_promoted_relation_metadata(...)`: currently attaches the richer relation after promotion.
- `PressureExperienceLedger`: consequence/development record, not a promotion governor.

## Governing invariant

**The promotion gates judge the relation that physically occurred, not a lossy proxy for that relation.**

`PairStats` remains valid statistical evidence. It must not remain the complete physical description of the candidate when richer lawful evidence already exists.

Unknown remains a valid physical state. If a dimensional distinction cannot be derived from existing evidence, leave it unresolved. Never infer a dimension from axis identity merely to fill a field.

## Required repair

1. Trace `_observe_impl()` through `_accumulate_pairs()`, `_update_representation_relation()`, `_try_promote()`, `_lineage_grade_for_pair()`, and `_promoted_relation_metadata()` on current `main` before editing. Verify exact call order rather than relying on this directive's prose if code has moved.

2. Preserve all existing promotion gates and their authority:
   - Gate 1: X-risk admissibility.
   - Gate 2: reliability / positive relief.
   - Gate 3: DAG depth.
   - Gate 4: repeated formation evidence.
   - Gate 5: net benefit / cost economics.

   Do not add a sixth gate. Do not replace these gates with representational-resolution logic.

3. Ensure the candidate's existing intact relation record is available to `_try_promote()` at decision time, rather than becoming meaningful only after promotion. Prefer passing or resolving the existing relation object/record through the narrowest existing seam. Do not create a second relation schema.

4. Let the existing gates retain their current statistical inputs from `PairStats`, but allow their existing support/opposition/context calculations to consult lawful relation evidence where that evidence is actually relevant. This must be consequence-driven, not feature-driven.

5. Difference must not become an automatic bonus, threshold, required field, or promotion vote. It is evidence describing what changed during the relation. A Difference observation should affect promotion only through an already-existing lawful interpretation of consequence, reliability, discrepancy, lineage, structural relevance, support/opposition, or net effect. If no existing mechanism gives a particular Difference value causal meaning, preserve it without inventing one.

6. Move/derive lineage or dimensional context early enough for promotion only if an existing gate already has lawful use for it. Do not compute `dominant_dimension` from `_AXIS_NC_DIM`, primitive self-operator mappings, semantic tables, or developer-selected aliases for the purpose of deciding promotion. Physics-grounded closure/lineage derivation is authoritative where available.

7. Preserve `PairStats` as statistics. Do not bloat it into a second representation relation and do not merely add `difference_snapshot` fields to `PairStats` as the repair.

8. Preserve `_update_representation_relation()` as the first-class relational witness. Avoid duplicating its consequence history, Difference accumulation, parent provenance, or constraint basis elsewhere.

9. Preserve `PressureExperienceLedger` as post-consequence developmental evidence. Do not make it a permission/governance path and do not use ledger history as a hidden promotion override.

10. Preserve ancestry and existing promoted-link identity. No migration, renaming, regeneration, or rewriting of historical links. Ancestry is not obsolescence.

## Required behavioral proof

Add focused regression tests proving the jurisdiction repair rather than merely testing signatures.

At minimum demonstrate:

1. A candidate relation seen by `_try_promote()` is the same existing intact relation accumulated from the actual coactivation, not a newly fabricated relation.

2. Existing five-gate outcomes remain unchanged when the richer relation contains no additional causally relevant evidence.

3. Removing or withholding Difference alone does **not** change promotion when Difference has no existing causal consequence.

4. When an observed dimensional distinction changes an already-existing lawful consequence/support/opposition calculation, promotion can change because the consequence changed, not because `DIFFERENCE` received a hardcoded bonus.

5. Unknown/unresolved dimensional evidence remains unresolved and does not fall back to an axis-derived dimension.

6. Existing representation relation history, parent identity, constraint basis, consequence history and Difference accumulation survive promotion intact.

7. Existing tests that pinned the historical exclusion of Difference from `_accumulate_pairs()` are updated only where the repaired architecture intentionally invalidates them. Do not weaken unrelated canaries.

8. Run the focused genealogy, representational-resolution, closure-basis, Difference observer/shadow, and representational-conservation suites. Run a broader regression sweep over modules importing or exercising `constraint_genealogy.py`. Any failures claimed pre-existing must be reproduced against the unmodified base commit.

## Explicit non-goals

Do not:

- invent a new representation type;
- invent a new promotion authority;
- add a Difference promotion threshold;
- map axis -> dimension to force resolution;
- make every relation fully resolved;
- make Difference mandatory;
- replace PairStats;
- route promotion through PressureExperienceLedger;
- add fallback semantics that conceal missing evidence;
- script which representation Aurora should form;
- modify unrelated genealogy, WARP, scheduler, Praxis, communication, or app behavior.

## Acceptance criterion

The repair is complete when the existing genealogy gates remain sovereign, but the thing standing before those gates is the **actual intact relation Aurora experienced**, with its existing lawful evidence available at decision time. `PairStats` supplies statistics about that relation rather than substituting for the relation itself.

The desired causal order is:

`physical coactivation -> intact relation + consequence evidence -> existing genealogy gates -> promotion or rejection -> persisted lineage/development`

not:

`physical coactivation -> flattened statistics -> promotion verdict -> attach the actual relation afterward`.
