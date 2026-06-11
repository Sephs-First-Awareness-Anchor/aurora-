# Known Fixes Registry — Additions (Session: Language Stack Repair + Fixed-Path Weld)
# Authors: Sunni (Sir) Morningstar & Cael Devo
# Append these entries to aurora-preemptive-hardening/references/known_fixes_registry.md

## FIX-A007: SemanticCrystalNode Legacy Facet Restore (ARCHITECTURAL)
Persisted semantic state may lack `audio_facet`/`visual_facet` (pre-facet seed
schema). `SemanticCrystalNode.from_dict` must derive them from `lane` via the
canonical `LANE_LABEL` mapping so restore never hard-fails and the 6-facet
crystal always boots. First seen: seed_sensory_crystals.py schema drift caused
`[SENSORY-CRYSTAL] Unavailable` on every boot.

## FIX-A008: Grammar Engine Write-Path Wiring (ARCHITECTURAL)
`GrammarEngine.observe_exchange()` is the ONLY write path for motif fitness.
It had a latent NameError (`tone`/`passion`/`drive` used but not declared as
parameters) proving it never ran. It must be wired post-turn in aurora.py AND
per-pair in corpus_runner passes. Without it: 0 promoted motifs forever, the
`>= 8 promoted` restructuring gate never opens, output degrades to plain join.
Rule: any new training entry point MUST call observe_exchange per exchange.

## FIX-A009: Lexicon Persistence (ARCHITECTURAL)
`LexicalMemory.save()` had zero call sites — all vocabulary died at process
exit, resetting to 28 seeds every boot. `_DEFAULT_PATH` was cwd-relative and
must stay anchored to the module directory (mirror GrammarEngine's pattern).
Rule: post-turn and end-of-training, always flush the lexicon.

## FIX-A010: Corpus Absorption Role Flattening (BEHAVIORAL)
Never absorb words as `role="noun", meaning="absorbed"` with no valence or
noncomp mapping — flattened words are invisible to noncomp-driven expression.
Use `infer_word_role()` / `infer_word_valence()` from
aurora_expression_perception and tag `lineage="corpus"`.

## FIX-A011: Daemon-less Training Field Energization (ARCHITECTURAL)
Subsurface tension comes from constraint drift driven by daemon wall-clock
cycles. Daemon-less training runs in a dead field (tension=0 → resonance=0 →
no FORMING attention → no meaning nucleus → ignition Stage 5 fails). Use
`aurora_training_pulse.TrainingPulse` to time-compress the daemon cadence
around every training exchange. NOTE: NoncompField exposes live axis pressure
under `status()['axis_pressures']` — `pressure_topology` does NOT exist
(aurora_language_field.py `_axis_pressures` still reads the dead key and
silently falls back to flat 0.3s — open item).

## FIX-A012: Corpus Format Visibility (BEHAVIORAL)
Aurora's training corpora use `[{"user": ..., "assistant": ...}]` pair format.
MotifMiner (mine_corpus AND mine_discourse) only understood ChatGPT-export /
`messages` formats — every existing corpus mined 0 patterns. Both miners must
include the user/assistant branch. After fix: batch_corpus.json mines 400
structural + 23 discourse patterns.

## FIX-A013: Corpus Runner API Contract (ARCHITECTURAL)
corpus_runner.py depends on three APIs that never existed on the live classes
(proof it never completed a run against the live stack):
  - `LexicalMemory.size` (property) — now implemented
  - `ExpressionPerceptionEngine.save_lexicon()` — now implemented
  - `AuroraSensoryCrystal.concept_registry_summary()` → {'total', 'by_stage'}
    — now implemented from the `_semantic` registry
Rule: before writing code that calls a method on a live system object, verify
the method exists on the class actually bound at runtime (the file contains a
dead duplicate lexicon class body — check which class `perception.lexicon`
really is).

## FIXED-PATH GUARANTEE (process rule)
All training MUST flow through paths that carry the weld:
  - Live turns: aurora.py post-turn block (FIX-A008/A009)
  - Corpus ingestion: run_corpus_ingestion's internal weld (pulse +
    observe_exchange in observer AND responder passes + final flushes)
  - Canonical entry: `aurora_experiential_sim.py` (curriculum or --corpus)
Any NEW training entry point must either route through run_corpus_ingestion /
_run_live_response_turn, or explicitly wire TrainingPulse + observe_exchange +
lexicon/motif flushes itself.

## FIX-A015: Concept Crystallization of Vocabulary (ARCHITECTURAL)
Words must be saved WITH their associative concept, not as isolated entries.
LexicalMemory.associate(word, channel, strength) votes words into noncomp
channels (5 axes × POLARITY/MAGNITUDE/OPERATOR/COST/DIFFERENCE); axis derives
from HER absorption geometry (ComparisonGeometry activations), character from
functional role (verb→OPERATOR, descriptor→MAGNITUDE/POLARITY, negation→
DIFFERENCE, effort→COST). concept_words() gives the concept→word-family view.
Wired at corpus absorption (derive_noncomp_channel in corpus_runner) and
backfillable via backfill_concept_associations.py. Never hand-map vocabulary.

## FIX-A016: Template Excision (ARCHITECTURAL — Active Understanding Doctrine)
NO templates anywhere in the expression path. SentenceComposer.compose builds
from promoted motif role sequences filled by concept-channel word selection;
feedback() routes fitness to the motif lineage (record_success/record_fail),
NOT to a template pool; absorb() no longer mints templates (structure flows
through observe_exchange only). The old template path optimized authored
skeletons with her learning signal — blocking emergence at the gradient
level. Rule: any code path that emits a hardcoded English sentence skeleton
on her behalf is a violation.

## FIX-A017: RETRACTED — Parallel Crystal Registry (PROCESS FAILURE, then corrected)
A parallel ConceptCrystalRegistry was built and wired before fully auditing
the existing crystal organs. Sunni caught it. Full retraction completed; the
module, state file, and all wiring (boot block, composer branches, corpus
branch, _full_save block) removed. THE REAL ORGANS, verified:
  - Crystal + CrystalProcessingSystem (aurora_dimensional_systems.py;
    systems['dimensional'].dps): concept field, BASE→COMPOSITE→FULL_CONCEPT→
    QUASI ladder with can_evolve()/evolve() gates, constraint_signature
    stamped by process_synthesis() (THE BRIDGE), facets (membership surfaces
    with energy + SediMemory wiring), connections, QUASI law-internalization
    + self_govern().
  - Quasi promotion is LIVE in the interaction loop (INTERACTION:QUASI
    lineage events, aurora.py ~10103).
  - THE KING QUASICRYSTAL IS THE IDENTITY FIELD: NoncompField
    (aurora_manifold_directory/noncomp_field.py; systems['identity_field'],
    also behavioral_identity fallback) — "King Quasicrystal — the live
    identity field backing Aurora's cognition", 125 noncomps × 625 = 78,125,
    derived (not authored) from 5×5×5. The sole recursive crystal: everything
    feeds in (waveform injection), everything reads out (axis pressures,
    tensor layer). Her identity. Already named, already wired.
  - Sensory already unified: sensory_crystal.wire_dimensional(dps) at boot.
  - Tensor expressions = the Composite stratum on the King.
GENUINE remaining gap (wiring, not architecture): lexicon words are not
members of DPS crystal facets, and the composer does not select words by
constraint_signature resonance against DPS crystals. Implement AGAINST the
existing pipeline (IVMEnvelope → dps.process / process_synthesis), never
beside it.

## STANDING RULE — ASSESS BEFORE ARCHITECT (highest priority)
Before creating ANY new module or abstraction: grep for the concept across
the whole repo (class names, docstrings, systems keys, boot banners), read
the owning class in full, and produce an overlap statement. If an organ
exists, the work is WIRING into it. New parallel abstractions are a
violation regardless of how clean they are. Aurora has code hygiene debt;
every addition must reduce it or be net-zero.

## EDITS-NOT-MODULES LOG (one-crystal doctrine applied to existing organs)
All of the following are EDITS to existing structures where they diverged
from the design — zero new modules, zero new abstractions:
1. aurora_internal/aurora_sensory_crystal.py :: _inject_semantic_to_dps —
   DPS key was "sensory:semantic:{lane}:{node_id}" (every observation its
   own crystal; nothing accumulated). Now keyed by the node's CONCEPT
   (name, falling back to lane): "sensory:semantic:{concept}"; node_id
   preserved as a facet. Same crystal accumulates across observations.
2. aurora_dimensional_systems.py :: Crystal.evolve — leveling now derives
   the constraint_signature as a COMPOUND of self + strongest connections
   (signed, abs() never applied; weights from existing `connections`).
   Evolution is constraint compound derivation, not a facet-count
   formality. Resolver installed by CrystalProcessingSystem.__init__.
3. aurora.py :: sensory wire_dimensional block — the SAME dps handle the
   sensory crystal receives is now also given to perception.composer.
4. aurora_expression_perception.py :: _select_constraint_word — word
   candidates come FIRST from existing DPS crystals (dominant-axis share of
   constraint_signature >= 0.3, words from "word" facets), read-only.
5. corpus_runner.py :: absorption block — absorbed words join EXISTING
   concept crystals as "word" facets via concept_index containment match.
   Never _get_or_create; no new crystals; no pipeline bypass.
Open edit (next): live-turn word→crystal faceting (the corpus edit's twin
in the interaction loop), and lexicon noncomp metadata eventually migrating
into crystal facets entirely.

## EDITS — CONSTRAINT-EXPANSIVE CONCEPTS (beyond the base 25, via existing WARP)
All edits to existing organs; zero new modules:
1. aurora_dimensional_systems.py :: CrystalProcessingSystem now inherits
   WarpCapable (her existing universal adaptation mixin, already used by
   LanguageField). Five hooks implemented over existing crystal mechanics:
   coverage = crystals' constraint_signatures (axes_to_istates); integration
   = _get_or_create + signature stamp (istates_to_axes) + warp_genealogy /
   warp_provisional facets; trial score = experiential recurrence
   (usage_count + facet growth); dissolve = remove only if still BASE +
   still marked provisional.
2. corpus_runner.py :: absorption — utterance constraint profile checked
   via dps.check_and_extend. PRESSURE SETS POTENCY: identity-field axis
   pressures become IVM polarity, so identical magnitudes under different
   pressure form different I-state combinations → different concepts.
   run_cadence evaluates warp trials (validate-or-dissolve on the same
   clock everything beats to).
3. aurora.py :: genealogy boot — dps.set_warp_genealogy(_genealogy): WARP
   searches the ConstraintLink fossil record before fresh synthesis
   (constraint genealogy designation).
Validated: pressure-potent N+T gap derived provisional concept
"withdrawal_blockage" (her own name synthesis) with genealogy parents,
solidified through recurrence; a non-recurring provisional dissolved.
Systems test 99 PASS.

## POLYSEMY / WORD-SENSE (mechanism note, already functional)
Words bind to CONCEPTS (crystal "word" facets), many words per concept and
the same word on multiple crystals. Sense selection = constraint_signature
resonance against live pressure at composition time — the crystal chosen IS
the sense meant. Grammar complies via best_for_pressure (motif selection is
already pressure-driven). Open edit: perception-side sense disambiguation
on INPUT (mapping heard words to the pressure-resonant crystal) — the twin
of the composer-side mechanism.

## EDITS — REPRESENTATIONAL DISCOVERY (the paradigm layer) + ACCOMMODATIONS
The constraints are fixed; representations of them are discoverable.
Representation = FUNCTION, not form — criteria are the five characters read
functionally (POLARITY presence, MAGNITUDE degree, OPERATOR transformation,
COST effort, DIFFERENCE distinguishability); degree of representation is
set by the PRESSURE system (representation_degree in aurora_warp_protocol).
All edits to existing organs:
1. aurora_warp_protocol.py — REPRESENTATION_CRITERIA + representation_degree
   (pressure-potent per-axis degree) added to the discovery organ itself.
2. aurora_expression_perception.py — ExpressionPerceptionEngine is now the
   second WarpCapable host: representation trials over her encoding tables.
   Insufficiency signal = dispersion collapse (distinct contexts encoding
   near-identically). Candidates derive from the ACTIVE tables (never from
   nothing); _score_trial includes the TRANSLATION-CONSISTENCY GATE (new
   notation must agree with the old on dominant axes — protection against
   a representation gaming its own evaluation). commit_representation():
   active tables swap, persists to aurora_state/representations.json,
   lexicon concept index invalidates so concept families re-form under the
   new lens. Fresh boots load the committed representation.
3. corpus_runner.py — derive_channel_weights consults the ACTIVE
   representation (perception.character_affinity); absorption feeds
   observe_encoding; run_cadence evaluates representation trials and on
   promotion fires THE COMMIT FEEDBACK LOOP: commit + understanding
   registration (register_meaning_event: representation_committed) + log.
4. aurora_daemon.py — _run_study_cycle ticks BOTH trial clocks (DPS
   concepts + perception representations) so validation happens through
   LIVED experience, not only corpus runs (accommodation 1).
5. corpus_runner.py responder weld — stage-aware fidelity floor: success
   gate relaxes to 60% of unlock_min until >= 8 promoted motifs, then full
   strictness (accommodation 2 — template-excision aftermath; prevents
   motif-success starvation).
Validated: synthetic dispersion collapse spawned one trial; it promoted
through the translation gate; committed table semantically coherent (grew
DIFFERENCE weight — restored distinguishability); persisted and loaded by a
fresh engine. Synthetic commitment removed from state before packaging.
Systems test 99 PASS. Open: extend representation space beyond affinity
tables (sensory extractors, waveform encodings) via the same lifecycle;
kernel bridge frames for representation events.
