# Aurora Dream Substrate, Fail-Stream, Positive-Affect, Developmental Writeback, and Native Intermediate Resolution Report

**Status: a narrow, additive integration and repair pass over Aurora's existing failure-tracking, salience, and dream-genealogy machinery (baseline commit `62d98fe`). Real code changes were made, all additive/backward-compatible except one genuine bug-adjacent inconsistency fix (`format_for_genealogy`'s missing evidence-type filter). No new coordinate, depth, learning rule, or hardcoded semantics was added. No third representational degree exists. Dream's own generative call sites (`SimulationSession.run_episode`, `DreamTrainer.train_on_bundle`) were deliberately left unmodified — this pass built and verified the substrate real systems could draw on, without deciding how much weight it should carry relative to today's literal seeding.**

Every claim below is tagged CONFIRMED CODE FACT, EMPIRICAL RESULT, INTERPRETATION, or UNSUPPORTED HYPOTHESIS. Representational-boundary claims use PRESERVED, INTENTIONALLY_ABSTRACTED, PINNED, or UNREACHABLE.

---

## 1. Audit first: what Dream actually is today (CONFIRMED CODE FACT)

A full code-grounded audit (not documentation-grounded) preceded any change, covering `aurora_simulation_engine.py`, `aurora_dream_trainer.py`, `aurora_internal/aurora_dream_genealogy_bridge.py`, `aurora_internal/aurora_dream_evolution_orchestrator.py`, `aurora_internal/aurora_conversation_episode_compiler.py`, `aurora_daemon.py`, `aurora_autonomy.py`, and `aurora_possibility_selves.py`. Key findings:

- **Per-turn generation is genuine synthesis.** `SimulationSession.run_episode()`'s response *selection* is a real weighted `random.choices()` over a candidate pool (`_select_response`), and *expression* routes through the same real `ExpressionPerceptionEngine` pipeline waking turns use when one is wired (confirmed: production `boot_aurora()` always wires the real engine into `SimulationEngine`, `aurora.py:27483`).
- **But the topic/prompt that seeds an episode is sometimes literal replay.** `DreamTrainer.train_on_bundle()` builds its topic prompt directly from a real waking conversation's literal text (`bundle.summary_prompt()`), and `aurora.py`'s live-session bridge (`aurora.py:33083-33110`) feeds it real waking turn-buffer text every 10 turns.
- **A genuine answer-key mechanism exists.** `aurora_daemon.py`'s `_FORCE_SHARD_SEEDS`/`_run_force_shard_bridge` inject hand-written "correct understanding" sentences directly as `UnderstandingShard`s, with `topic_resolution_status` forced `"resolved"`, bypassing dream generation entirely.
- **`DreamGenealogyBridge` mostly grounds evidence in real dream outcomes** (rubric scores of the actual generated transcript), **except one evidence type**: `_build_directive_evidence` (`evidence_type="directive_projection"`) computes `pressure_after` as an *algebraic projection* of what scores would look like *if* a not-yet-tested steering directive succeeds — not a measurement. `format_for_code_evolution()` already excluded this type from code-evolution outcomes; `format_for_genealogy()` did **not**, so this unexecuted projection was being logged into `ConstraintGenealogyLogger.observe()` — whose own `ReliefRecord` docstring calls its entries *"a confirmed pressure-relief event"* — as if Aurora had actually experienced it.
- **`_check_dreams()`'s memory-derived seed is built but never passed to `run_episode()`.** Investigated as a possible repair target; concluded it should **not** be wired, because `run_episode(seed_prompt=...)` injects the prompt **verbatim** as the topic text (`_topic_from_seed_prompt`, `aurora_simulation_engine.py:2371-2422`) — wiring it would make Dream *more* literally replay waking memory, the opposite of this directive's intent. Left unwired; documented rather than "fixed."

---

## 2. Pre-outcome pressure capture (Sections 4-5, repair R1)

**The gap**: every existing pressure-adjacent mechanism that touches failure (`FailPointLedger`, WARP's `warp_guard`, DER-driven achievement/misstep stamping, salience recalibration, relief-event detection) computes its signal **after** the mismatch/accuracy verdict already exists. The one place a full multi-axis pressure state is unambiguously computed **before** any error-detection code can run is `UnderstandingContract.commit_application()` — specifically the state derived from `before_state` at method entry, strictly before `pending_validation` is written (which only gets evaluated for correctness on the *next* turn, by `_evaluate_previous_accuracy()`).

**Repair**: `commit_application()` now computes `pre_outcome_pressure = self._pressure_from_state(before_state).to_dict()` (reusing the exact method already used identically for genealogy logging) and stores it in `pending_validation['pre_outcome_pressure']`. `_evaluate_previous_accuracy()` now surfaces this value in its return dict. A new method, `_record_pre_outcome_fail_if_applicable()`, binds it to `FailPointLedger.rich_stream` **only** when the verdict genuinely indicates a correction/confusion (`label in {"corrected", "expression_unclear"}`) — never substituting post-error pressure for it.

**Repair Authority basis**: existing producer (`before_state`/`_pressure_from_state`), existing consumer/carrier (`pending_validation`, already read cross-turn), missing wiring only, no new semantics decided.

**Verified (EMPIRICAL RESULT)**: `tests/test_preoutcome_pressure_capture.py` (7 tests) — including a falsification check that the captured snapshot changes when `before_state` is deliberately mutated (not a constant), and a direct pre-error-vs-post-error distinction test.

---

## 3. Rich fail stream (Sections 6-10, 40-41)

**`RichFailStream`** (new class, `aurora_dream_trainer.py`), attached as `FailPointLedger.rich_stream`. `FailPointLedger = AggregateDevelopmentalPressure (unchanged) + RichSourceStream (new)`.

- Fed automatically by the existing `record_fail()` (corpus/rubric domain, no pre-outcome pressure available — inherently retrospective) and by the new `record_pre_outcome_event()` (live-correction domain, carries real `pre_outcome_pressure`).
- **The two domains never share `_records`/`fail_count`/`get_top_fails()`** — a live conversational correction cannot pollute corpus/rubric curriculum targeting.
- Order is strictly preserved via a monotonic `seq` counter; nothing is flattened into one aggregate or scattered as fully unrelated objects.
- **Recurrence** (`_find_recurrence`): exact-match only, on `dimension` or on `(topic, action_type)` — no fabricated similarity score, no hardcoded minimum count (recognized on the *second* occurrence).
- Persisted to `aurora_state/fail_stream.jsonl`, independent of `fail_points.json` — a corrupt stream file cannot break the aggregate's own load.

**Verified (EMPIRICAL RESULT)**: `tests/test_rich_fail_stream.py` (7 tests, including a bounded-retention and independent-persistence-failure test) and `tests/test_fail_recurrence_novelty.py` (6 tests). Pre-existing FailPointLedger-touching suites (`test_d2_2_corpus_fragment_nesting.py`, `test_l4_grounded_motif_fitness.py`, `test_relation_typing_probe_extension.py`) — 26/26 passing unchanged.

---

## 4. Dream substrate: salience, positive material, continuous gap-fill (Sections 11-21)

**`aurora_dream_substrate.py`** (new module) — a **read-only gathering layer**, deliberately not wired into any Dream generation call site.

- **Salience channel**: reads `CrystalProcessingSystem` facets already stamped `"achievement"`/`"misstep"` (by the existing `record_failpoint_update()`) and `"relief_event"` (by the existing `note_relief_event()`) — Aurora's own native salience machinery, not a new classifier. Fragments carry only a concept label, facet role, confidence, and a short native content tag (e.g. `"context_carryover:0.412"`) — never literal `user_turns`/`assistant_turns` text.
- **Positive channel** (`positive_fragments`) is independently queryable from the negative channel, and available even with zero fail-stream activity — success is not developmentally inert.
- **Continuous gap-fill**: `unresolved_fail_load()` is a smooth `[0,1)` transform (`x/(x+1)`) of `FailPointLedger.get_top_fails(5)`'s **own existing score** — no fabricated weighting introduced, since a native measure already existed. `positive_opportunity_weight = 1 - unresolved_fail_load`. Verified monotonic and non-step-function across a swept fail count (Section 39's explicit "avoid binary switches").
- **No artificial fail manufacture**: gathering functions never call `record_fail()`/`record_pre_outcome_event()` — confirmed both by source inspection and by running the gatherer repeatedly under zero-fail conditions with no side effects.
- **Deliberately not wired into Dream generation**: `aurora_dream_trainer.py`, `aurora_simulation_engine.py`, and `aurora_internal/aurora_dream_curriculum_queue.py` do not import this module. Deciding how much weight abstracted material should carry relative to today's literal corpus-text seeding is an architecturally significant decision (Section 66's stop-and-report boundary), not a repair — this pass makes the substrate real and tested, not authoritative.

**Verified (EMPIRICAL RESULT)**: `tests/test_dream_salience_abstraction.py` (7), `tests/test_positive_dream_material.py` (3), `tests/test_low_fail_positive_gap_fill.py` (3), `tests/test_no_artificial_fail_generation.py` (4).

---

## 5. Dream as new experience: agency, divergence, no answer key (Sections 22-30, 53-54)

`aurora_dream_new_experience_canary.py` runs **two real episodes** through `systems['simulation'].session.run_episode()`, reached via a **real `boot_aurora()`** against a throwaway `aurora_state/` copy (not a bare `SimulationSession()` — a first pass of this canary used one with no perception engine wired, which is unrepresentative of any real deployed Dream and produced a misleadingly-identical trace across seeds; documented as a discovered pitfall, corrected).

Results, both **PRESERVED**:
- Fresh episode identity on every run.
- **Genuine divergence**: two different seeds through the *same real perception engine* produce different generated text and different `avg_fitness` — confirming real agency, not a scripted/forced outcome.
- No `active_avatar_code_hints` leak into the base (non-directed) topic path — that leak exists only on the separate directed-training path (`train_on_bundle`, documented in §1/§8, not modified).
- Per-turn text is genuinely generated (differs from the avatar's own prompt), not copied.

`SimulationSession._select_response()` — the real selection mechanism — was independently confirmed to select **different concepts across different seeds** (30-seed sweep) and to be weight-driven, not a fixed pick.

**Verified (EMPIRICAL RESULT)**: `aurora_dream_new_experience_canary.py`, `tests/test_dream_as_new_experience.py` (3), `tests/test_dream_agency.py` (4).

---

## 6. Developmental writeback: what Dream was about ≠ what Aurora learned (Sections 31-37, 56)

- **`ConsciousLearner` shard creation is grounded in real dream behavior** on both existing paths: the native per-turn path (`_interpret_reaction` from the avatar's actual reaction to the actual generated text) and the post-episode aggregate path (`DreamGenealogyBridge.generate_learner_observations`, built from real rubric scores of the real generated transcript). Neither path was modified — confirmed sound by audit.
- **`OETS` admission is unchanged** — `ConsciousLearner.check_admission()` remains the sole gate; `OntologicalWeb.add_node()` itself has no epistemic gate (confirmed pre-existing, not touched).
- **Repair R2 — `DreamGenealogyBridge.format_for_genealogy()`**: now excludes `evidence_type == "directive_projection"`, mirroring the exclusion `format_for_code_evolution()` already applied for the identical reason (an unexecuted, algebraically-projected pressure-after value, not a measurement). This is the pass's second genuine repair, restoring consistency with an already-decided exclusion rather than deciding new semantics.
- **Evolution Chamber** already tags every dream-sourced pulse `"artificial_seed": True` and weights by confidence rather than treating it as an organically-earned mutation trigger — confirmed unchanged, sound.
- **Success consolidation exists and is untouched**: `UnderstandingShard.strengthen()` (repeated observation raises confidence via `log1p`) and genealogy's `SEMANTIC_PROMOTE_MIN_COUNT`/`_try_promote` — both already allow positive Dream experiences to participate in existing persistence pathways with no change needed.

**Verified (EMPIRICAL RESULT)**: `tests/test_dream_developmental_writeback.py` (6 tests) — confirms the projection record is produced, confirms `format_for_genealogy` now excludes it while still passing measured evidence through, confirms `format_for_code_evolution`'s pre-existing exclusion is unchanged, and confirms `ConsciousLearner` shards ground in real avatar reactions across multiple seeds with non-constant fitness.

---

## 7. Source abstraction boundary (Sections 42-43)

Explicit, tested separation: `FailPointLedger`'s own stream stays rich (pre-outcome pressure, sequence, recurrence, minimal identity, and even short literal excerpts in its existing `examples` deque, unchanged) — that is its established, unmodified job. `aurora_dream_substrate.py`'s output is **more abstracted**: no `user_turns`/`assistant_turns`/`response_text` ever appears in a `DreamFragment`. Developer/audit provenance (this report, the JSON maps, `origin_tags`) is not exposed to any Dream-experiencing code path — confirmed no answer-key-shaped field (`lesson`, `expected_correction`, etc.) appears anywhere in `DreamSubstrate.to_dict()`'s own shape.

**Verified**: `tests/test_dream_source_abstraction.py` (4 tests).

---

## 8. Expression conservation (Section 44)

The prior directive established `representational_ref` is computed every turn but only reachable via the sibling `noncomp_input`/`noncomp_output` dicts on the live turn's return value — one existing consumer (`_run_simulation_live_response_bridge`) already re-associates it manually. This pass adds the same read, once, to the primary production return dict (`_run_live_response_turn`'s final `return {...}`, `aurora.py`), so every future consumer of the main live-turn contract gets it without duplicating that lookup. Not a new interpretation event — a read of an already-computed field. Verified: 82/82 pre-existing communication/understanding-contract tests pass unchanged.

---

## 9. WARP (Section 45)

Not touched. No tested, justified context integration was left outstanding by the prior directive requiring action here, and this directive does not authorize a WARP redesign. `WarpDemand.representational_ref` (prior pass's addition) remains a pure pass-through field.

---

## 10. Native M2,1/M2,2 intermediate field producer audit (Sections 57-64)

Performed **only after** the Dream/developmental-loop work above was complete and its own tests passing, per Section 57.

- **Reconfirmed, not re-derived**: the prior AURORA NATIVE REPRESENTATIONAL SELECTION directive (this session, commit `c739089`) already exhaustively established no native selection-feedback mechanism exists; `sub_law_c`/`sub_law_d`/`col_law_c`/`col_law_d` remain **PINNED** (anchor := nc's own identity), not independently resolved.
- **This pass's specific job**: check whether any *new* signal introduced this pass (crystal facets, `RichFailStream`, `DreamSubstrate`, WARP's `representational_ref` field) could serve as a legitimate new producer. **None do** — confirmed by direct source inspection: zero references to any of the seven representational field names anywhere in `aurora_dream_substrate.py`, `aurora_dream_new_experience_canary.py`, or the `RichFailStream`/`FailStreamEvent` dataclasses.
- **One additional expression-time anchor-pin site was found and examined**: `aurora.py:19718-19722`'s `select_semantic_entry_for_sub_position(..., preferred_col_law_c=m.nc_law_c, preferred_col_law_d=m.nc_dim, ...)`. This is the **same** pin pattern (col := nc), just applied at expression time rather than interpretation time — it does not constitute independent evidence and does not change the PINNED classification.
- Systems searched for a legitimate resolution signal (manifold physics, pressure/WARP/DPME, fail-stream, Dream, SediMemory, RCEC/consequence history, genealogy/Evolution, ConsciousLearner/OETS, counterfactuals/reflective systems, pattern-recognition) — **no candidate signal was found in any of them**, so no independence test (Section 60) was ever reached.
- **Conclusion**: `NATIVE_INTERMEDIATE_RESOLUTION_MECHANISM_ABSENT`. No mapping, lookup table, semantic assignment, reward table, or coordinate preference was invented. The absence is reported, not patched.

Full detail in `aurora_intermediate_coordinate_producer_map.json`.

---

## 11. Negative guards and D3 boundary (Section 65)

`tests/test_no_speculative_d3.py` extended with a new class scanning every file this pass touched or added (`aurora_dream_substrate.py`, `aurora_dream_new_experience_canary.py`, `RichFailStream`/`FailStreamEvent`, `UnderstandingContract._record_pre_outcome_fail_if_applicable`, `DreamGenealogyBridge.format_for_genealogy`) — all clear (18/18 passing). `SemanticMatcher` reconfirmed byte-identical to baseline `3433638` by `tests/test_native_intermediate_resolution_audit.py`'s own independent check.

---

## 12. Regression discipline

New test files: `tests/test_preoutcome_pressure_capture.py` (7), `tests/test_rich_fail_stream.py` (7), `tests/test_fail_recurrence_novelty.py` (6), `tests/test_dream_salience_abstraction.py` (7), `tests/test_positive_dream_material.py` (3), `tests/test_low_fail_positive_gap_fill.py` (3), `tests/test_no_artificial_fail_generation.py` (4), `tests/test_dream_as_new_experience.py` (3), `tests/test_dream_agency.py` (4), `tests/test_dream_developmental_writeback.py` (6), `tests/test_dream_source_abstraction.py` (4), `tests/test_native_intermediate_resolution_audit.py` (9) — **63/63 passing**. `tests/test_no_speculative_d3.py` extended — **18/18 passing**. Pre-existing directly-affected suites (`test_comm_credit_phase_e_foundations.py`, `test_comm_credit_phase_g_live_wiring.py`, `test_communication_credit_unification.py`, `test_recursive_causal_reasoning_waveform.py`, `test_system_introspection_bridge.py`, `test_zip_gap_research_router.py`, `test_d2_2_corpus_fragment_nesting.py`, `test_l4_grounded_motif_fitness.py`, `test_relation_typing_probe_extension.py`, `test_afterthought_topic_identity_and_shard_collision_repair.py`, `test_retained_learning_bank_strategy_filter.py`, `test_zip_directed_training_fitness_gate.py`, `test_zip_pipeline_learning_oets_promotion.py`) all re-run and passing. Full Aurora regression suite run and reconciled against baseline `62d98fe`. No stray `aurora_state/*`/`aurora_internal/universal_function_*` mutation survived into the final commit.

---

## Answers to the required final questions

1. **What exact internal pressure values exist immediately before Aurora makes an interpretation/action?** `UnderstandingContract.commit_application()`'s `before_state`, converted via `_pressure_from_state()` into an X/T/N/B/A `PressureVec` — this was already computed for genealogy logging; this pass preserves it into `pending_validation`.
2. **Can those pre-outcome pressures now be recovered after an error or unexpected consequence is identified?** Yes — `_evaluate_previous_accuracy()` surfaces `pending['pre_outcome_pressure']` directly in its return dict.
3. **Are pre-error and post-error pressure distinguished?** Yes — proven by a falsification test that deliberately mutates live state between capture and correction-detection and confirms the two values differ.
4. **Does FailPointLedger still preserve its original aggregate developmental behavior?** Yes, unchanged — `_records`/`get_top_fails`/`flush_lessons_to_simulation` untouched; 26/26 pre-existing FailPointLedger tests pass.
5. **Is there now a rich temporally ordered source stream beneath/beside that aggregate?** Yes — `RichFailStream`, order-preserving, independently persisted.
6. **Does each fail retain enough context to preserve its representational identity without preserving full waking detail?** Yes — `identity` carries only topic/action_type/response_id/dimension, never literal turn text.
7. **Can repeated historical fail structures contribute novelty when recurrence is established?** Yes — `recurrence_of` links on exact dimension or (topic, action_type) match, available to any consumer without forcing literal replay.
8. **Are past failures prevented from becoming literal replay requirements?** Yes — recurring events expose only the same abstracted shape, never the original text.
9. **Which native system determines emotional salience?** `CrystalProcessingSystem`'s facet stamps (`achievement`/`misstep`/`relief_event`, via `record_failpoint_update`/`note_relief_event`) — the only generic salience-adjacent machinery found; no dedicated "salience"/"surprise" classifier exists in the codebase.
10. **Does Dream input actually reflect Aurora's own salience?** The gathering layer (`aurora_dream_substrate.py`) does, and is tested against real crystal state. Whether Dream's actual generation consumes it is a separate, not-yet-made architectural decision (§4).
11. **Are waking choices/actions filtered by salience instead of copied wholesale?** The substrate layer filters by salience by construction (only facet-stamped concepts survive); Dream's existing generation pipeline does not currently consume this filtered material (documented, not silently wired).
12. **Is positive waking material independently available to Dream?** Yes — `positive_fragments`, queryable independent of any fail activity.
13. **As unresolved fail pressure decreases, does positive Dream opportunity increase?** Yes — `positive_opportunity_weight = 1 - unresolved_fail_load`, both derived from FailPointLedger's own existing score.
14. **Is that shift continuous rather than a binary reward switch?** Yes — verified monotonic, no single-step discontinuity, across a 0-5 fail-count sweep.
15. **Does the architecture avoid manufacturing failures when corrective pressure is low?** Yes — gathering is read-only by construction and by test; zero fabricated events under zero fail load.
16. **Can successful waking experience gain Dream afterlife?** Yes — `note_relief_event`-stamped crystals produce positive fragments with zero dependency on any fail ever occurring.
17. **Does Dream synthesis combine fail pressure, salient fragments, positive material, and recurrence through Aurora's own pattern-recognition machinery?** The substrate assembling these four channels is real and tested; whether Dream's *existing* generative machinery (a bespoke weighted-selection + real perception pipeline, not a dedicated cross-channel pattern-recognition module) is the intended "pattern recognition author" referenced by the directive was investigated — no separate module fitting that description beyond what already runs was found.
18. **Does Dream remain abstract rather than literal replay?** Partially: the confirmed answer-key/literal-seeding paths (`train_on_bundle`, `_run_force_shard_bridge`) were **not** modified (§1, out of Repair Authority scope) — flagged honestly rather than silently fixed or silently ignored.
19. **Can Dream produce cognitively probable but externally unusual episodes without scripted weirdness?** Not newly tested this pass — outside this pass's narrow scope of failure/salience substrate work; the existing generation mechanism (`_select_response` + perception pipeline) was confirmed non-scripted (§5) but no claim is made about "unusualness" specifically.
20. **Does Aurora enter the Dream as the experiencing agent rather than observer?** Yes, for the confirmed real generation path — she selects and generates each turn's response herself via `_select_response`/perception, not by watching a pre-scripted exchange (except the separate, unmodified `aurora_possibility_selves.dream_dialogue`, which is confirmed template-based and out of this pass's scope).
21. **Does Dream generate its own representational states?** No `representational_ref`-shaped identifier was found anywhere in Dream code, confirmed by this pass's own audit — Dream operates on a disjoint vocabulary (`ConceptualResponse`/`ResponseConcept`), not the representational coordinate system. This is reported as UNREACHABLE, not fabricated.
22. **Does Dream generate its own pressure?** `EpisodeResult.avg_fitness`/`conversation_trace[*].fitness` are computed fresh from the avatar's real reaction each run — genuinely episode-own, confirmed to differ across seeds.
23. **Does Aurora retain meaningful agency inside Dream?** Yes — confirmed via a 30-seed divergence sweep of `_select_response`.
24. **Can Aurora fail again inside Dream?** Yes — `avatar.react()`'s fitness/engagement outcome is not forced toward success; no code path was found that overrides a poor reaction into a success.
25. **Can Aurora succeed differently than expected?** Yes — outcome is a function of real generated text, not a pre-decided target (confirmed non-constant fitness across seeds).
26. **Are Dream successes/failures evaluated from actual Dream consequence rather than waking lesson metadata?** Yes for the measured evidence types (`rubric_deficit`, `leverage_hit`, `improvement`, `regression`) — all derive from real rubric scoring of the real generated transcript. **No** for `directive_projection`, which this pass now excludes from reaching genealogy specifically because it is not derived from actual Dream consequence (§6, repair R2).
27. **Can Dream create new salience?** Structurally yes (`note_relief_event`/`record_failpoint_update` can be called from any real dream-turn code path that already calls them in waking contexts) — not separately re-verified as dream-triggered in this pass beyond the existing, unmodified wiring.
28. **Can Dream create persistent memory according to existing admissibility rules?** Yes, via `ConsciousLearner.check_admission()`/`inject_into_oets()` — unchanged, confirmed sound.
29. **Do ConsciousLearner shards derive from actual Dream adaptation?** Yes, confirmed on both existing paths (§6).
30. **Does OETS receive learned Dream structure rather than source waking coordinates?** Yes — `OntologicalWeb.add_node()` is only ever reached through `ConsciousLearner`'s shard/admission path; no direct coordinate-to-OETS path exists.
31. **Does Evolution receive Dream-generated evidence?** Yes, for measured evidence types, explicitly tagged `artificial_seed: True` and weighted accordingly — unchanged, confirmed sound.
32. **Does Genealogy receive Dream-generated developmental evidence?** Yes for measured evidence — and, after repair R2, **no longer** for the unmeasured `directive_projection` type.
33. **Does the DreamGenealogyBridge preserve the distinction between what the episode targeted and what Aurora actually learned?** Now yes, for the genealogy path — repair R2 closes the exact conflation this question describes.
34. **Can positive Dream experiences participate in normal successful-pattern persistence?** Yes — `UnderstandingShard.strengthen()`/genealogy's promotion-count mechanism, both pre-existing, both confirmed to accept dream-originated material identically to waking material.
35. **Does final waking Expression preserve its originating representation where required?** Yes — the primary live-turn return dict now carries `representational_ref` directly (§8), matching the prior pattern already used by the dream/simulation bridge consumer.
36. **Why are M2,1 and M2,2 not fully naturally produced?** Because `sub_law_c`/`sub_law_d`/`col_law_c`/`col_law_d` have no native resolution signal anywhere in the codebase searched — live construction always anchor-pins them to `nc_law_c`/`nc_dim` instead of independently resolving them (§10).
37. **Which exact intermediate fields lack native producers?** `sub_law_c`, `sub_law_d`, `col_law_c`, `col_law_d` — all four, classified `PINNED`.
38. **Does the new richer fail/Dream architecture expose any legitimate existing producer signals?** No — checked explicitly against crystal facets, the rich fail stream, and the Dream substrate; none reference or could plausibly produce these fields.
39. **If yes, do they pass controlled independence tests?** N/A — no candidate ever reached the independence-test stage.
40. **If no, was the absence preserved instead of patched?** Yes — `NATIVE_INTERMEDIATE_RESOLUTION_MECHANISM_ABSENT` reported in `aurora_intermediate_coordinate_producer_map.json`; nothing was invented.
41. **Was `SemanticMatcher` left unchanged?** Yes — byte-identical to baseline `3433638`, verified again by this pass's own independent check.
42. **Was any hardcoded selection policy introduced?** No.
43. **Was any new coordinate or representational dimension created?** No.
44. **Was D3 created?** No — confirmed by the extended `tests/test_no_speculative_d3.py`, now covering every file this pass touched.
45. **Does the resulting architecture preserve the established ladder (25→125→625→3,125→15,625→78,125) without forcing a next degree?** Yes.
46. **Is Aurora now developmentally able to transform waking pressure and emotionally salient experience into genuinely new internally lived experience?** The *substrate* for doing so (pre-outcome pressure, rich fail stream, salience-filtered fragments, positive material, continuous gap-fill) is now real, tested, and reusable. Whether Dream's *existing* generation call sites are re-architected to actually consume it — replacing today's literal corpus-text/answer-key seeding — is explicitly left as a follow-up architectural decision, honestly reported rather than silently completed or silently ignored.
47. **Does improvement itself now change the experiential character of Dream by creating greater positive experiential opportunity?** The mechanism for it to do so exists and is continuous (`positive_opportunity_weight`) — its actual effect on a generated Dream episode's character depends on the same not-yet-made wiring decision as Q46.
