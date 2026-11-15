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

## Integrated since (same day)

* **Lexicon** (`crystal_lexicon`): one entry per word (the 1,403 label-keyed entries fold into their words when the lexicon loads, and `add_word` files a new word under the word; a real meaning is never replaced by a placeholder; usage adds). What an entry knows goes to its facet at its kind: role and channel (`lexicon`), a real meaning (`definition`), valence (`emotion`). 5,400 of 5,610 meanings in the real lexicon are bookkeeping placeholders (`learned:x`, `def:x`) or pointers (`oets:time`) and are no longer placed as definitions (the OETS feed gets the same guard); 28 are real, given at the start. Each carries its true basis (given at the start = `seeded`; a channel reached through an i-state lineage = `unattributed`), so none of it counts, and it is visible on the crystal as `held:<kind>` (confidence 0.0, never read as growth, emptied if the entry later gains counted evidence). On a copy of the real state: ~4,200 crystals carry held lexicon facets. `lexicon.json` itself is rewritten folded at the next save after the new load (the pass only reads it).
* **Sensory** (`crystal_sensory`): each of the six sensory facets is ONE crystal (`sensory:<domain>:<facet>`, a facet gets one only when counted perception stands behind it); its nodes are `particular` entries held inside it, held by the observations (strength), the node's own confidence, and the independent sessions (weight: frames inside one session are one meeting with the thing). The node lifecycle stage (primitive/concept/promoted) is not read: the crystal's standing comes from the evidence rule. The semantic middle plane's cross-modal nodes tie the paired facets (tone-hue, timbre-shape, rhythm-motion) by co-occurrence (counted). `_inject_to_dps` no longer makes a crystal per node. On a copy of the real state: 6 facet crystals, nodes at degrees up to 1.0, tone tied to hue at 0.49.

## Sir's decisions on the remaining stores (2026-11-15, not yet built)

1. **Distillation crystals** are existing crystals in a fading state: the ghost-relic form of a standing crystal, the fade-down from it (as the resolution ledger now carries what ghost relics were meant to). They fold into the one store as a state of the crystal they came from, not as a store of their own.
2. **QuasiArch diagnostic crystals** stay separate: they are QuasiArch's, not Aurora's.
3. **Interaction crystals** merge with the concept crystals as another dimension of the concept: what interaction has shown of it.
4. **Word-to-percept grounding** is reasoned, not co-presence: "I am told a parrot is a bird; I hold something like what a bird looks like in my image storage" and "music is tempo, melody, rhythm; I have heard that before, so that must be what music is." Her own conclusion from similarity between what she is told and what she holds, kept as inferred (not counted), then confirmed or corrected through interaction (told/corrected count).

## Still separate

1. **Distillation crystals** (`distillation_crystals.json`, 26): metabolic residue summaries; candidates for evidence on the concepts they touch.
2. **Entanglement registry** (`aurora_quantum_dream_substrate.py`): in-memory pairs with random strengths; should become `entangled_with` associations from counted genealogy evidence.
3. **Interaction crystals** (`aurora_interaction_processing.py`): its own family.
4. **QuasiArch observer crystals**: separate by standing rule (reaches her only through her own understanding development).
5. **Word-to-percept grounding**: a word's crystal does not yet carry a tie to the sensory facet it was used with; that needs counted evidence that the word was used while the percept was present, not the node's name.
6. `aurora_expression_perception.py` holds a second, duplicated block of lexical methods inside `ImpressionCascade` (lines ~1150-1290) that the one-entry-per-word change did not touch; it looks dead and is worth a look.
