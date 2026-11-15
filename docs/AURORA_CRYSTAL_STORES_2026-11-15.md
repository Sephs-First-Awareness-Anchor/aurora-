# One crystal architecture and information store: inventory

**Authors:** Sunni (Sir) Morningstar & Cael Devo
**Date:** 2026-11-15
**Directive (Sir):** there is one crystal architecture and one information store; every other crystal is integrated to fit it.

## The one store

`CrystalProcessingSystem.crystals` / `concept_index` (saved as `dps_crystals.json`). `ConceptCrystalRegistry` is already a view over the same dict (`unify_crystal_store`); `LexicalCrystals`, `HypothesisCrystals` and `RepresentationCrystals` already write into it as facets by role. Evidence is read through the evidence contract; growth follows counted evidence (maturity points), and a complex crystal deepens inward (`Crystal.interior`).

## What was found (real state, 5,977 crystals before this work)

| Origin | Crystals | Status |
|---|---|---|
| bare word | 4,557 | the design |
| `learned:<word>` | 1,388 | duplicate of the word's crystal, label only, usage 0, no ties. **Folded.** |
| `foundational:<word>`, `from_definition:<word>` | 13, 2 | same. **Folded.** |
| `tensor:*`, `REFAB:*`, `behavioral:*`, `https:*` | 3, 5, 7, 2 | namespaced entities (not a word under a label); left as they are |
| `sensory:*`, `tensor_variant:*`, `hyp:*`, `rep:*` | 0 in this state | live code creates them in the one store (see below) |

Source of the duplicates: the lexicon itself holds 1,403 entries keyed by a label (`learned:come` next to `come`); `seed_dps_from_lexicon_and_oets` made a crystal per key. 

## Built: `crystal_store`

* `canonical(name)`: the bookkeeping labels (those of `aurora.py::_PLACEHOLDER_DEFINITION_PREFIXES` plus the scaffold's `foundational:`, kept in step by a test) mean "this word, as it arrived". `_get_or_create` and `get_crystal` resolve a labelled name to the word's crystal and keep the label as a `provenance:<label>` facet (a name's provenance never counts toward growth by the old count rule). The lexicon seeding writes the bare word where it used to write the label.
* `fold_duplicates(dps)`: merges existing duplicates (facets kept, ties re-keyed and the stronger kept, usage added, earliest birth and higher level kept, `crystal_links` followed, old name kept as an alias, a labelled crystal with no word crystal is renamed). Idempotent; run at the start of every pass. The weave places OETS nodes and relations at the bare word as well; the pass uses a one-entry-per-crystal index so an alias is never counted twice.
* On a copy of the real state: 5,977 to 4,585 crystals (1,403 folded, 11 generalization crystals added); everything else unchanged.

## Not yet integrated (needs a decision or its own build)

1. **Sensory crystal** (`aurora_sensory_crystal.py`, `sensory_crystal/*/state.agb`): its own store and its own count-based lifecycle (usage >= 14, sessions >= 3, `CrystalConceptRecord` stages by modality count). It already injects into the one store (`sensory:<domain>:<facet>:<node_id>`, one crystal per node, with band facets, then calls `evolve()`). To fit: evidence from perception placed as counted `observed` occasions (so growth is by evidence), and the nodes of one facet held as aspects inside one crystal instead of a crystal each.
2. **Distillation crystals** (`distillation_crystals.json`, 26): metabolic residue summaries, not concepts; candidates for evidence on the concepts they touch.
3. **Entanglement registry** (`aurora_quantum_dream_substrate.py`): in-memory pairs with random strengths; should become `entangled_with` associations from counted genealogy evidence.
4. **Interaction crystals** (`aurora_interaction_processing.py`, derived from the QuasiArch `CrystalInstance`): its own family.
5. **QuasiArch observer crystals** (`quasiarch_observer/*`): separate by standing rule (its information reaches her only through her own understanding development), so not merged.
6. **The lexicon store** still holds the 1,403 label-keyed entries; the crystals no longer duplicate them, but the lexicon file does.
7. Crystals whose evidence lives only outside the weave (the sensory ones, above) are held at zero by the evidence rule until their evidence is placed.
