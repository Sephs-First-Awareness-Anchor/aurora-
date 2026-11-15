# Crystal architecture over the unmerged work (integration branch)

**Authors:** Sunni (Sir) Morningstar & Cael Devo
**Date:** 2026-11-15
**Branch:** `ceph/crystal-integration-20261115` = the #251/#252/#253 stack (evidence qualification, input identity, genealogy redistribution, FIX-A142/A143) + the crystal build (P1 associations, P2 convergence, P3 maturity, facet placement) + `crystal_weave`. Nothing merged to main. Nothing wired into the running system; every writer is dry-run by default.

## What now works together

* `crystal_weave.place_event` takes an evidence-contract event and places it as an occasion on a facet entry: counts only if `evidence_qualification.counts` says so (a recollection, dreamed, imagined, simulated, overheard, supposed, inferred or unknown occasion is kept and earns nothing; a negated one is evidence against); occurrence, context, ancestry and consequence travel with it.
* `genealogy_associations` turns the genealogy's pair ledger and promoted links into typed associations by recurrence (each exposure worth 0.1, n exposures 1-(0.9)^n), and carries the qualification by kind of occurrence when a link has one (lived counted; hypothetical and overheard kept, uncounted; externally demonstrated inputs are inside lived, not extra).
* `weave(state_dir)` runs every adapter (OETS nodes and relations, assertions, genealogy, waveform cycle) and returns a facet book, an association store and a summary. `consequence` measures what the links change.
* `scripts/measure_crystal_weave.py --state-dir <dir>` prints all of it. Reads only.

## Measured on the repository snapshot (not live state)

| Measure | Value |
|---|---|
| Concepts woven (OETS + genealogy) | 1,369; 565 have a crystal, 804 do not |
| Associations held | 15,926 records: recurrence 11,197, heuristic 6,450 (OETS and genealogy), looked_up 1,411, unattributed 228, unknown 59, seeded 20 |
| Crystals that would gain any link | 382 of 5,977 (6.4%); 4,171 links |
| Reach of `sunni` | 9 crystals in one step, 190 in two (3.2% of all crystals) |
| Wholes formed by `is_a` from counted evidence | 0 (its 54 edges come from axis_embodiment, foundational, seeded, definition_analysis and `conversation`, none counted) |
| Genealogy ids that have a crystal | 0 of 404 (by design: they reach crystals through the concepts of the inputs that exercised them) |
| Links with an evidence qualification | 0 of 356 (all predate FIX-A144 recording) |

## What this says about "the links would be consequential"

* The mechanism is in place: weaving does place everything in its facet once with its occasions, and the links do form a web. On today's snapshot the web is thin because most of what she holds has no earned evidence behind it, not because the architecture cannot hold it.
* The category skeleton (`is_a`) is entirely uncounted. Until her categories rest on occurrence, no whole forms by convergence. Her `conversation`-sourced `is_a` edges (10) have a source the evidence table does not map; they stay unknown rather than being read as told.
* Operations are not a separate kind of crystal (Sir, 2026-11-15): they are part of her lived history and live in the same crystals as the concepts she was dealing with when she exercised them. `place_exercise` places an operation entry in each of those concepts' crystals, one occasion per distinct input. What the genealogy's own ids (`NC:...`, `X:ADMIT`, `L:...`) need is the route from a credited input to the concepts of that turn; the pair ledger keeps the input ids, the conversation records keep the turn, and joining them is the next step. Until then the genealogy associations stay among representations, with no crystal to receive them.
* Usage examples and valence carry no recorded occurrence, so they stay uncounted; the input-identity work records it from now on.

## Conversations and development (Sir, 2026-11-15)

* `place_conversation` reads the conversation memory (200 records in the snapshot) and places each as one `episode_ref` at every known concept either side mentioned, weighted by the record's own importance: 3,346 placements reaching 297 concepts. With conversation-sourced `is_a` edges now counted, 7 small wholes form (one member each), where none did.
* `place_development` attaches a representation to the crystals of the concepts it developed among, with where and when (tick, input time, depth), the operation it is (lineage, signature), what it was made from (its parents are its ancestry) and the associated information present then. `concepts_of_inputs` joins a ledger row's inputs to the concepts of their turns by the turn id, and leaves out any turn it cannot match rather than guess from the clock. The conversation memory records carry no turn id today, so the live join needs one (a recorded `turn_id` on each conversation entry); that is a change to the running writer and is not made here.
* The waveform cycle in the uploaded state came from a `turn_open` with source `aurora_sensory_pulse` and no input, not from a conversation.

## P0 answered: the waveform state Sir uploaded (2026-11-15)

`recursive_causal_reasoning_waveform.json` and `_history.jsonl` hold exactly one cycle (`RCRW:c984155b81ae1ff0`, created 2026-08-22 08:47 UTC), identical to the file in the repository snapshot. Its raw input is empty, its effective relation has no subject, relation or object, completeness 0.25, response "I am tones"; promoted, trial and dissolved wavelets are all 0, and its representation experiment was not admitted as evidence (`inconclusive_causal_measurement`). So there is no recorded waveform history to climb from yet: either the waveform has run once (a probe) on this state, or live turns are not being recorded to it. Nothing placed from it, correctly. When a cycle does develop a relation, `place_cycle` places the relation at both concepts, an episode reference and what she said with its alignment, and `place_cycle_operations` places the operations that parented it in the same crystals, counted only if the cycle's own experiment was admitted.

## Decisions for Sir

1. (Answered: operations live in the same crystals as the concepts they were exercised on.)
2. (Answered by Sir, 2026-11-15: conversations are her lived experiential history; she witnesses them or is told, from either conversational position, including when rehearsing. Said TO her is told; what she herself said she witnessed; both count. A relation learned in conversation is told. Built: `place_conversation`.)
3. Wiring: this branch changes nothing live. Which writer, if any, runs first on a copy of state?

## Promotion by group classification

Added `crystal_promotion.py` (12 tests, 10 mutants killed, `scripts/measure_crystal_promotion.py`). Not wired into the running system. It reads the same `AssociationStore` as the other crystal modules and its level is the generalization's, while P3 stays the crystal's own standing. See plan doc, P3b.

Authors: Sunni (Sir) Morningstar and Cael Devo.

## Evidence-based growth, turn id, function words

Added: `turn_id` on conversation memory entries (joined by id, never the clock), `Crystal.maturity` and the evidence-based `can_evolve`, `crystal_weave.apply_maturity`, `crystal_grammar`, `scripts/trial_crystal_writers.py`, `scripts/measure_crystal_grammar.py`. These are on `ceph/crystal-integration-20261115`, not main. See plan doc P3c and P6.

Authors: Sunni (Sir) Morningstar and Cael Devo.

Also added: `crystal_substitutability` (+ `scripts/measure_crystal_substitutability.py`), the `substitutes_for` link type, and per-member degrees in `crystal_grammar.place_classes`. See plan doc, P6 follow-up.

## The whole pass is live (merged to main)

Authors: Sunni (Sir) Morningstar and Cael Devo.

`crystal_runtime.run_pass(dps, state_dir, force, clock, min_interval)` runs every writer in order: associations and facets (`crystal_weave`), grammar classes and substitutability (`crystal_grammar`, `crystal_substitutability`), promotion by group classification (`crystal_promotion`), then evidence-based maturity (`apply_maturity`). It is called once from `aurora.py::_full_save`, before `dimensional.save_state`.

* Additive and fail-safe: an exception is caught and logged, never raised into the save. Rate-limited to once per 600 s (`MIN_INTERVAL`). Kill switch: `AURORA_CRYSTAL_WEAVE=0`.
* Generalization crystals are created at level 1 and only raised by degree (`min(3, round(level_under))`), never lowered, never QUASI.
* `LexicalStructure.contexts` is a bounded `ContextProfiles` (1500 words, 24 contexts) fed from her own turns; dictionary-sourced text stays out (it goes through her understanding development).
* Speed: promotion caches profiles (`FAN = 40`) and `AssociationStore` has a per-concept index (identical results to a full scan; tie-breaks by name). Whole pass on real state: 31.6 s to about 3.3 s.
* Trial on a copy of real state: 5,988 crystals given maturity, 176 ready to grow under evidence (0 under the old count rule), about 5,180 links over 437 crystals, 885 facets over 537 crystals, 11 new generalization crystals, `sunni` facets 4 to 6 and links 0 to 16. Known and benign: the link count varies by about 10 across hash seeds (zero-strength links), and maturity differs by about 1e-9.
* Open: `and`, `or`, `a`, `that` have no crystals in this state yet; her own word classes are not found by `LexicalStructure` (diffuse words excluded by design); emotional maturity point not wired.
* Pre-existing failures on main, unrelated: `test_build725_native_semantic_externalization` (collection error), `test_build694...canonical_turn_id`, `test_communication_integrity_repair...identity_seed`, `test_native_intermediate_resolution_audit...byte_identical`.
