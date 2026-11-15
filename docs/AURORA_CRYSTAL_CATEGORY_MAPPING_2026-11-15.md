# Mapping everything Aurora records, takes in, reasons and puts out onto crystal categories (P0)

**Authors:** Sunni (Sir) Morningstar & Cael Devo
**Date:** 2026-11-15
**Status:** read-only audit; nothing built. Companion to `AURORA_CRYSTAL_BUILD_PLAN_2026-11-14.md`. L4 is quasi (confirmed by Sir).

**Method and limits.** Inventory of the 201 entries in the repository's `aurora_state` snapshot (not live device state). The structure of about 60 stores was
read (keys, counts); the rest are classified by name only and marked so. Intake, reasoning and output channels come from the input-identity work
(speech, read, perceived, derived, dreamed, overheard) and the module names. Counts below were measured on the snapshot.

## 1. The categories before adjustment

* **Levels (spec):** L1 base, L2 composite, L3 full concept, L4 quasi (8 surface + 8 internal facets, 9th nexus, laws).
* **Facet kinds (spec, older design and live roles):** definition, example, relation, evidence, abstract, context, operation; cause, effect, condition,
  analogy, counterexample, generalization, particular, temporal, spatial, agent, patient; at L4 hypothesis, contradiction, abduction, plan, value,
  uncertainty, intent; live: `lexicon:*`, `oets:*`, `topic`, `entity`, `action`, `emotion`, `relief_event`, `misstep`, `genealogy:*`, `LAW_*`.
* **Points:** emotional, polarity, associative, abstract, temporal, cognitive, recursive.
* **Memory kinds** (`Core_Crystal_Systems.py`): experiential, conceptual, emotional, procedural, relational.

## 2. The mapping

| What she handles | Where recorded | Crystal home | Fits? |
|---|---|---|---|
| Words, forms, parts of speech | `lexicon.json` (5,610), `lexeme_bindings`, `lexical_*` | L1 base; `definition`, `lexicon:*` | yes |
| Recurring structure of language | `grammar_motifs.json` (10.5 MB) | L2 composite of base crystals | yes (function words missing, P6) |
| Concepts, definitions, examples, valence | `aurora_oets_web.json`: 944 nodes (931 with definitions, 850 with examples) | L1–L2 crystals; `definition`, `example`, `emotional` point | yes, already a parallel concept store (§3) |
| Associations between concepts | OETS: 17,284 typed relations; genealogy pair ledger; `relation_pair_log`; interaction edges | `connections` (empty today) and `relation` facet | **partly**: needs a type and provenance (A7) |
| Concept categories | OETS: 16 (pronoun, existence, value, verb, growth, action, temporality, emotion, noun, structure, adjective, cognition, inquiry, relation, perception, adverb) | the parents P2 convergence should form | yes |
| Things heard or said in turns | `topic` and `entity` facets (quoted turns), `aurora_conversation_memory`, `historical_experience` | `example`, historic recall | **partly**: copies text (A2) |
| People and entities | `entity` facets, identity entities, interaction nodes | L3 full concept; specific people or recursive concepts at L4 | yes |
| What she is and values | `aurora_identity` (name, description, entities, foundational truths), `autonomy_state`, `presence_metrics` | self crystal at L4 | yes |
| Effects and outcomes | `relief_event`, `emotion`, `energy_income` (59, with half-lives), `pressure_experiences` (source, anchor, consequence, outcome) | emotional and cognitive points; `effect` | yes |
| Cause and condition reasoning | `recursive_causal_reasoning_waveform` (cycles, promoted/trial/dissolved wavelets), `reasoning_paths`, `understanding_contract_state` | `cause`, `effect`, `condition` at L3 | yes (a lifecycle that already mirrors promotion) |
| Skills and abilities | `ability_lineages`, `aurora_learned_skills`, `operation_descriptors`, code lineage | `operation`; procedural kind | **partly** (A4) |
| What she says and how it lands | `last_voice_generation_trace`, `articulation_habits`, `register_log`, `communication_outcomes`, `aurora_to_user` | no spec facet | **no** (A3) |
| Open questions, contradictions, gaps | `contradiction_ledger`, `open_loop_ledger`, `clarification_memory`, `provisional_knowledge`, pending curiosity | spec has them only at L4 | **no** (A5) |
| Patterns not yet concepts | `unformed_patterns.json` | below L1 | **no** (A5) |
| Sensory signal | `vision_*`, `sensory_*`, ambient audio | features into sensory base crystals (six-facet structure); raw stays outside | yes |
| Dreams and simulations | `dream_selves` (Ember, Kindle, Riven, Sable), `dream_earned`, `dream_genealogy`, sleep context | the same crystals, flagged by occurrence class | yes via A6 |
| Sources and trust | `source_trust`, genealogy qualification, evidence logs | cross-cutting | **no** as a facet (A6) |
| Event streams | `classroom_log`, `exploration_log`, `study_log`, `dual_strata_frame_log`, timeline, `experience_ledger` | none; they are the raw record | **no** (A2) |
| Coordinate space | `evo_625_pressure_map`, `pressure_ontology`, X/T/N/B/A | the geometry crystals sit in | **no** (A8) |
| Training and measurement | corpora (`batch`, `fast`, `small`, `medium`, `mini`, `intensive`), `probe_battery`, `growth_test`, `threshold_test*`, `live_*_assessment*` | none | **no** (A9) |
| Operations | `daemon_status`, heartbeats, locks, checkpoints, backups, `runtime_faults`, `persistence_audit`, `system_introspection_*` (10 MB code index), diagnoses | none | **no** (A1) |
| Room and Poedex | `aurora_room_*`, `poedex_*` | definition and example facets, only via her understanding development | yes, under that rule |

## 3. Finding: the OETS web already holds what P1 and P2 are meant to build

OETS has 944 concept nodes and 17,284 typed relations with strength, confidence and a source. Relation types: related_to 10,659, enables 5,885,
context_of 671, is_a 54, opposite_of 4, causes 3, implies 3, contrasts 2. The sources are what matter:

* **co-occurrence 8,502** and **co-expression 614**: recurrence of real use. These can seed crystal links.
* **research 1,411**: arrived through lookup, so it follows the told route (understanding development).
* **backfill_role_heuristic 6,450**: assigned from part-of-speech labels, not from experience. These must not be treated as lived associations
  (the same objection as converting a label into experience). Carry them as `basis: unknown` and let recurrence earn them.
* axis_embodiment 68, definition_analysis 59, adjacency 101, seeded 20: small; each keeps its own source.

So P1 can project the recurrence-based OETS relations into `connections` instead of starting empty, with each link keeping its source as provenance.

## 4. What did not fit, and the adjustment

* **A1 Substrate.** Telemetry, locks, checkpoints, faults and the code index are not knowledge, and she does not experience the architecture, only its effects.
  Add a class **outside the crystal**: crystals carry effects (for example vitality from the metabolic clock), never the machinery.
* **A2 Episodes.** Event streams are raw time-ordered records. Add an **episode ledger** as the source layer and a facet kind `episode_ref`
  (id, time, short summary). Crystals then hold references, not quoted copies (today `topic` and `entity` facets carry the quoted turn).
* **A3 Expression.** The spec has no facet for what she puts out. Add a facet kind **`expression`**: what was said, in what context, with the outcome
  (consequence) attached. Memory kind: procedural.
* **A4 Procedure.** `operation` exists only from L2 in the schema; abilities exist from the start and carry lineage. Allow `operation` at L1, with the
  genealogy ancestry attached.
* **A5 Open items.** Uncertainty and contradiction are L4-only in the spec; she holds them from the beginning. Add an **`open`** facet kind at every
  level (status open/resolved, what would settle it), and a **seed** stage below L1 for patterns not yet concepts (`unformed_patterns`).
* **A6 Provenance.** Not a facet. Every facet carries the evidence contract (occurrence class, basis, ancestry, context, consequence). Dreams are an occurrence
  class on ordinary crystals, not a separate kind of crystal; dream-only evidence stays hypothetical until consequence is demonstrated outside it.
* **A7 Typed links.** A link is (type, strength, provenance), not a bare number. Types start from what OETS already distinguishes.
* **A8 Frame.** The coordinate system (axes, the 625 slots, the pressure ontology) is the space crystals live in, not a crystal. Class: **frame**.
* **A9 Instruments.** Corpora, probes and assessments are instruments and training input. When read they become experience (intake); their measurements are
  reported, not stored as knowledge. Class: **instrument**.

**Adjusted scheme:** levels L1–L4 with a seed stage below; the spec's facet kinds plus `expression`, `episode_ref`, `open`; typed, provenance-carrying links; memory kind
as a second dimension (from `MemoryType`); the evidence contract on every facet; and three classes that stay outside the crystal (substrate, frame, instrument).

## 5. Not covered

About 140 small or duplicate files were classified by name only. Live device state was not read. Whether each OETS relation's source label is accurate was not
checked beyond counting it. The mapping is a proposal for Sir to correct; nothing here changes how she develops.
