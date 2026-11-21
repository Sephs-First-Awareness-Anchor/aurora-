# Dream entanglement: evidence and participation audit (2026-11-16)

Historical audit from November 16, 2026. The findings below describe the pre-fix implementation. Current `main` retains regression coverage in `tests/test_dream_entanglement_evidence_boundary.py`.


Parent: #257. Scope: **existing** `aurora_quantum_dream_substrate.py`; no parallel association store, no new promotion system.

## Verified source-level path
`QuantumDreamSubstrate.run_dream_cycle` invokes `CrystalEntanglementRegistry.auto_entangle_from_genealogy` followed by `propagate` before temporal feedback, fusion, dimensional collapse, dream encounter, and the MTSL perturbation probe.

`auto_entangle_from_genealogy` reads up to 20 `genealogy.recent_promotions` entries, infers parents by splitting the concept name on its final underscore (otherwise first five characters), then creates candidate sibling pairs with `random.uniform(0.55,0.85)` strength. This is a **name heuristic**, not demonstrated genealogy ancestry or a measured association.

`propagate` uses random gating and random delta, then invokes `genealogy.tick_crystal_promotion` on **both** paired concepts with `source='entangle:...'`. Thus speculative pairing can alter promotion state without new witnessed evidence. The method documentation describes propagating *actual* recent weight deltas, but the implementation does not read an observed delta.

The existing `_run_mtsl_perturbation_probe` is different: its source-tagged dream evidence is explicitly lower-authority and cannot alone promote a semantic variant. Preserve this existing discipline.

## Participation classification
- **Participatory within dream cycles:** discovery and propagation are invoked unconditionally by `run_dream_cycle`, but mutation requires available genealogy and candidate pairs.
- **Conditionally dormant:** if no recent promotions or no sibling candidates, no pairs; if no `tick_crystal_promotion`, no propagation.
- **Representational reposition candidate:** speculative entanglement is useful as an *activation/attention hypothesis*, not as earned maturity or empirical evidence.
- **Not yet proven:** whether the dream cycle is scheduled and reached in a specific deployment, and whether promotion calls have further internal evidence gates. Inspect callers and genealogy implementation before declaring an end-to-end defect.

## Repair requirements (do not implement blindly)
1. Trace scheduler → dream cycle → registry → genealogy mutation and record exact pressure/timing gates and source-qualified downstream consumers.
2. Use existing canonical genealogy parent identifiers, if present. Do not infer lineage from shared string prefixes or invent another ancestry index.
3. Preserve legitimate associative propagation as transient activation through an **existing** pressure/salience interface, if verified. Do not turn dream-only hypotheses into durable experiential evidence or promotion.
4. If genealogy already rejects unearned `entangle:` sources, prove it with tests before changing this module.
5. Reconcile candidate relationships with canonical crystal IDs, aliases, and source/occasion provenance.
6. Keep `_run_mtsl_perturbation_probe`, dream encounter, and other cycle stages intact; do not suppress dream processing globally.

## Tests required before merge
- Two names with matching prefix but unrelated ancestry do not earn a relationship.
- Genuine siblings with shared canonical parent may form an *exploratory* association without promotion.
- A dream-only cycle with no new lived evidence leaves earned maturity unchanged.
- Previously earned relations and recorded experience remain intact across save/restore.
- Deterministic replay of the same event set does not accumulate duplicate promotion or evidence.
- Multi-pressure and inactive-gate cases distinguish dormancy from broken wiring.
- Run baseline and candidate traces side-by-side; assert no loss of dream encounter, MTSL, or other cycle outputs.

## Status
Source-level audit only. No runtime code changed; no test execution claimed. This file is a migration guardrail for a separate focused repair PR.
