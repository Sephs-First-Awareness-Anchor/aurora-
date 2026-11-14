# Aurora — Information Circulation and Consequence Map

**Authors:** Sunni (Sir) Morningstar & Cael Devo  
**Generated:** 2026-11-13 at commit `54e4f4f` by `scripts/map_turn_information_flow.py`

This document is produced by watching her run. Nothing in it is anyone's reading of how she is supposed to work. Regenerate it after any change; a fix is placed on this map before it is written.

## How to read it

- A **signal** is one named entry in the turn's pipeline state — the shared record every stage of a live turn writes to and reads from.
- **Stage order** is the order functions first wrote during real turns.
- **Never read** means: written during a live turn, and no code anywhere reads that name outside the function that wrote it. Information that circulates nowhere.
- **Awaited, never written** means: read during a live turn, and never written in any of them. A consumer waiting on a producer.
- Decisions (`FIX-A…`) are the registry entries cited inside that stage's code.

**Limits.** Reader lists come from matching the signal's name in source, so a common name (`confidence`) lists readers of unrelated dictionaries; a *never read* verdict has no such weakness. Only the pipeline state is watched live; fields on the turn-understanding object and each organ's private state are not on this map. Four turns were run; a path no turn took is not shown.

## The turns that were run

| Said | Reply | Source | Gate outcome |
|---|---|---|---|
| Hey Aurora, how are you today? | — | silence | silence · blocked: scripted_source:constraint_abstain · articulation: no_stance · confluence: nothing_contributed |
| I spent the morning fixing the fence behind the house. | — | silence | silence · blocked: scripted_source:constraint_seek · articulation: echo · confluence: nothing_contributed |
| What do you remember about what I was working on? | no memories on this yet. | generative | own_voice |
| Do you like music? | I understand music. I did music. I am music. I want music. | composer_unified | own_voice |

## Totals

- Signals written during live turns: **162**, by **23** stages
- Never read outside their writer: **51** — of these, **39** have a name that appears nowhere else in the source (no reader can exist), and **12** are named elsewhere without being read there (each needs a look)
- Awaited but never written: **17**
- `systems["_…"]` bus keys in source: **314** — written and never read: **96**; read and never written by assignment: **38**

## 1. Signals written and never read

### 1a. No reader can exist: the name appears only where it is written

| Signal | Written by |
|---|---|
| `subsurface_effects` | aurora._extract_pipeline_signals |
| `subsurface_intuition` | aurora._extract_pipeline_signals |
| `present_frame` | aurora._extract_pipeline_signals |
| `interaction_secondary_strategy` | aurora._apply_interaction_quasi_route, aurora._run_reasoning_pipeline |
| `interaction_failure_indicators` | aurora._apply_interaction_quasi_route |
| `interaction_expected_effects` | aurora._apply_interaction_quasi_route |
| `subsurface_conscious_frame` | aurora._run_reasoning_pipeline |
| `subsurface_conscious_crest` | aurora._run_reasoning_pipeline |
| `live_sensory_vitals` | aurora._run_reasoning_pipeline |
| `perspective_birth` | aurora._chain_up1_information |
| `conversation_memory_summary` | aurora._chain_up2_belief |
| `memory_locations` | aurora._chain_up2_belief |
| `braid_axis_blend` | aurora._chain_up3_purpose |
| `axis_intensity` | aurora._chain_up3_purpose, aurora._build_comprehension_response |
| `noncomp_anchor` | aurora._apply_noncomp_input_guidance |
| `perception_result` | aurora._run_reasoning_pipeline |
| `active_ability_effects_raw` | aurora._run_reasoning_pipeline |
| `active_ability_effect_translation` | aurora._run_reasoning_pipeline |
| `active_ability_effect_passive` | aurora._run_reasoning_pipeline |
| `active_ability_effect_unhandled` | aurora._run_reasoning_pipeline |
| `noncomp_input_behavior_actuation` | aurora._apply_noncomp_behavior_actuation |
| `conscious_frame_crest` | aurora._run_reasoning_pipeline |
| `pre_generation_subsurface_state` | aurora._run_reasoning_pipeline |
| `structured_perceptual_context` | aurora._chain_down5_understanding |
| `representational_existence` | aurora._chain_down5_understanding |
| `constraint_relation_alignment` | aurora._chain_down5_understanding |
| `poedex_learning_reason` | aurora._stage_poedex_learning_request |
| `poedex_representation_reason` | aurora._stage_poedex_representation_request |
| `pressure_tuner_kind` | aurora._run_reasoning_pipeline |
| `dual_strata_runtime` | aurora._run_reasoning_pipeline |
| `noncomp_should_seek_remedy` | aurora._apply_noncomp_input_guidance |
| `noncomp_remedy` | aurora._apply_noncomp_input_guidance |
| `subsurface_dominant_axis_hint` | aurora._run_reasoning_pipeline |
| `subsurface_readiness_bias` | aurora._run_reasoning_pipeline |
| `subsurface_intuition_signals` | aurora._run_reasoning_pipeline |
| `subsurface_active_effects` | aurora._run_reasoning_pipeline |
| `rubric_weak_dims` | aurora._run_live_response_turn |
| `rubric_strong_dims` | aurora._run_live_response_turn |
| `rubric_quality_alert` | aurora._run_live_response_turn |

### 1b. Named elsewhere, but not read there

| Signal | Written by |
|---|---|
| `presence` | aurora._extract_pipeline_signals |
| `dmm_alignment` | aurora._extract_pipeline_signals |
| `kill_reason` | aurora._extract_pipeline_signals, aurora._run_reasoning_pipeline |
| `interaction_wake_tiers` | aurora._apply_interaction_quasi_route, aurora._run_reasoning_pipeline |
| `interaction_search_policy` | aurora._apply_interaction_quasi_route, aurora._run_reasoning_pipeline |
| `constraint_genealogy_trace` | aurora._chain_up3_purpose |
| `axis_polarity` | aurora._chain_up3_purpose, aurora._build_comprehension_response |
| `polarity_gradient` | aurora._chain_up3_purpose |
| `learned_hints` | aurora._chain_down5_understanding |
| `other_model` | aurora._run_reasoning_pipeline |
| `subsurface_surface_guidance` | aurora._run_reasoning_pipeline |
| `grammar_discourse_hint` | aurora._chain_down5_understanding |

## 2. Signals awaited and never written

| Signal | Read by | Reads | Assigned anywhere in aurora.py |
|---|---|---|---|
| `reflective_readdressing` | aurora._run_reasoning_pipeline, aurora._chain_up3_purpose, aurora._chain_down4_meaning | 12 | yes |
| `gap_question` | aurora._chain_down5_understanding, aurora._build_comprehension_response | 8 | yes |
| `poedex_learning_result` | aurora._build_established_strata_evidence, aurora._stage_poedex_learning_request | 7 | yes |
| `poedex_representation_result` | aurora._build_established_strata_evidence, aurora._stage_poedex_representation_request | 6 | yes |
| `poedex_prefetch_result` | aurora._build_established_strata_evidence, aurora._stage_noncomp_prefetch | 5 | yes |
| `correction_absorbed` | aurora._chain_up3_purpose | 4 | yes |
| `remembered_path` | aurora._run_reasoning_pipeline | 4 | yes |
| `input_is_negated` | aurora._chain_down5_understanding | 4 | yes |
| `sensory_scene_desc` | aurora._chain_down5_understanding | 4 | yes |
| `intent_override` | aurora._build_comprehension_response | 4 | yes |
| `conscious_frame_reactive` | aurora._build_comprehension_response | 4 | **no** |
| `correction_acknowledgment` | aurora._build_comprehension_response | 4 | yes |
| `conditional_concept_notes` | aurora._chain_down4_meaning | 4 | yes |
| `oets_gap` | aurora._build_established_strata_evidence | 4 | **no** |
| `poedex_lookup_concept` | aurora._build_established_strata_evidence | 4 | yes |
| `poedex_lookup_result` | aurora._build_established_strata_evidence | 4 | yes |
| `response_confidence_cap` | aurora._chain_down5_understanding | 1 | yes |

## 3. Stage order — the path a live turn takes

| # | Stage | Signals it writes | Decisions cited there |
|---|---|---|---|
| 1 | aurora._extract_pipeline_signals | `coherence`, `stagnation`, `novelty`, `thermal_load`, `spike_detected`, `presence`, `dmm_alignment`, `dmm_vitality` … +26 |  |
| 2 | aurora._apply_interaction_quasi_route | `interaction_quasi`, `interaction_archetype`, `interaction_primary_strategy`, `interaction_secondary_strategy`, `interaction_confidence`, `interaction_quasi_ready`, `interaction_route_reason`, `interaction_wake_tiers` … +3 |  |
| 3 | aurora._run_reasoning_pipeline | `coherence`, `stagnation`, `novelty`, `dominant_axis`, `paradoxes`, `thought_killed`, `kill_reason`, `assembly_quality` … +41 |  |
| 4 | aurora._chain_up1_information | `paradoxes`, `parsed`, `relational_form`, `perspective_birth`, `axis_tensions`, `collective_dominant_axis`, `collective_resonance`, `reality_warp` … +4 |  |
| 5 | aurora._inject_surface_recent_context | `recent_context_mode`, `recent_context`, `recent_context_turns` |  |
| 6 | aurora._chain_up2_belief | `relational_form`, `working_memory_snapshot`, `conversation_memory_summary`, `memory_locations`, `surface_conversation_frame` |  |
| 7 | aurora._chain_up3_purpose | `dominant_axis`, `braid_axis_blend`, `constraint_semantic_state`, `constraint_genealogy_trace`, `response_obligation`, `axis_activation`, `axis_depth`, `axis_intensity` … +18 |  |
| 8 | aurora._apply_noncomp_input_guidance | `noncomp_input`, `noncomp_anchor`, `noncomp_should_seek_remedy`, `noncomp_remedy`, `concept_gap`, `noncomp_gap_anchor` |  |
| 9 | aurora._apply_noncomp_behavior_actuation | `noncomp_input`, `active_ability_effects`, `ability_runtime_flags`, `noncomp_input_behavior_actuation` |  |
| 10 | aurora._chain_down5_understanding | `constraint_semantic_state`, `learned_hints`, `understanding_stage`, `dominant_meaning_form`, `goal_stack`, `salient_concepts`, `semantic_pressure`, `belief_tension` … +11 |  |
| 11 | aurora._build_comprehension_response | `dominant_axis`, `axis_activation`, `axis_depth`, `axis_intensity`, `axis_polarity`, `field_balance`, `referent_map`, `referent_confidence` … +9 |  |
| 12 | aurora._emit_interpreted_turn_packet | `response_fit_pressure`, `interpretation_adequate`, `interpreted_meaning` |  |
| 13 | aurora._structure_current_turn_scout_evidence | `subsurface_response_evidence`, `external_grounding_evidence` |  |
| 14 | aurora._stage_poedex_learning_request | `poedex_learning_concept`, `poedex_learning_request`, `poedex_learning_reason`, `poedex_learning_status` |  |
| 15 | aurora._stage_poedex_representation_request | `poedex_representation_concept`, `poedex_representation_request`, `poedex_representation_reason`, `poedex_representation_status` |  |
| 16 | aurora._learning_worker | `poedex_learning_status` |  |
| 17 | aurora._representation_worker | `poedex_representation_status` |  |
| 18 | aurora._chain_down1_information | `question_alignment` |  |
| 19 | aurora._finalize_articulation | `articulation_arbitration` |  |
| 20 | aurora._apply_pipeline_modulation | `_problem_solving_drive` |  |
| 21 | aurora._run_live_response_turn | `rubric_weak_dims`, `rubric_strong_dims`, `rubric_quality_alert` | FIX-A119 |
| 22 | aurora._stage_noncomp_prefetch | `poedex_prefetch_concept`, `poedex_prefetch_status` |  |
| 23 | aurora._prefetch_worker | `poedex_prefetch_status` |  |

## 4. Every signal: who writes it, who reads it

| Signal | Writers | Read live by | Read in source by (count) |
|---|---|---|---|
| `coherence` | aurora._extract_pipeline_signals, aurora._run_reasoning_pipeline | aurora._run_reasoning_pipeline, aurora._apply_pipeline_modulation, aurora._derive_problem_solving_drive | 39 |
| `stagnation` | aurora._extract_pipeline_signals, aurora._run_reasoning_pipeline | aurora._run_reasoning_pipeline, aurora._apply_pipeline_modulation, aurora._derive_problem_solving_drive | 12 |
| `novelty` | aurora._extract_pipeline_signals, aurora._run_reasoning_pipeline | aurora._run_reasoning_pipeline | 13 |
| `thermal_load` | aurora._extract_pipeline_signals | aurora._apply_pipeline_modulation, aurora._derive_problem_solving_drive | 8 |
| `spike_detected` | aurora._extract_pipeline_signals | aurora._apply_pipeline_modulation, aurora._derive_problem_solving_drive | 2 |
| `presence` | aurora._extract_pipeline_signals | — | 0 |
| `dmm_alignment` | aurora._extract_pipeline_signals | — | 0 |
| `dmm_vitality` | aurora._extract_pipeline_signals | — | 3 |
| `dominant_axis` | aurora._extract_pipeline_signals, aurora._chain_up3_purpose | aurora._apply_pipeline_modulation | 57 |
| `paradoxes` | aurora._extract_pipeline_signals, aurora._chain_up1_information | aurora._apply_pipeline_modulation | 3 |
| `thought_killed` | aurora._extract_pipeline_signals, aurora._run_reasoning_pipeline | aurora._apply_pipeline_modulation | 2 |
| `kill_reason` | aurora._extract_pipeline_signals, aurora._run_reasoning_pipeline | — | 0 |
| `assembly_quality` | aurora._extract_pipeline_signals, aurora._run_reasoning_pipeline | aurora._apply_pipeline_modulation | 1 |
| `comprehension_rendered` | aurora._extract_pipeline_signals | aurora._apply_pipeline_modulation | 1 |
| `primary_emotion` | aurora._extract_pipeline_signals | aurora._apply_interaction_quasi_route | 6 |
| `intensity` | aurora._extract_pipeline_signals | aurora._apply_interaction_quasi_route | 25 |
| `drive` | aurora._extract_pipeline_signals | aurora._apply_interaction_quasi_route | 8 |
| `passion` | aurora._extract_pipeline_signals | aurora._apply_interaction_quasi_route | 12 |
| `meaning_label` | aurora._extract_pipeline_signals | — | 5 |
| `meaning_signature` | aurora._extract_pipeline_signals | — | 4 |
| `meaning_summary` | aurora._extract_pipeline_signals | — | 2 |
| `meaning_focus` | aurora._extract_pipeline_signals | — | 4 |
| `meaning_semantic_pressure` | aurora._extract_pipeline_signals | — | 1 |
| `meaning_axes` | aurora._extract_pipeline_signals | — | 4 |
| `subsurface_effects` | aurora._extract_pipeline_signals | — | 0 |
| `subsurface_intuition` | aurora._extract_pipeline_signals | — | 0 |
| `present_frame` | aurora._extract_pipeline_signals | — | 0 |
| `interaction_quasi` | aurora._apply_interaction_quasi_route, aurora._run_reasoning_pipeline | aurora._chain_down5_understanding | 2 |
| `interaction_archetype` | aurora._apply_interaction_quasi_route, aurora._run_reasoning_pipeline | — | 13 |
| `interaction_primary_strategy` | aurora._apply_interaction_quasi_route, aurora._run_reasoning_pipeline | — | 1 |
| `interaction_secondary_strategy` | aurora._apply_interaction_quasi_route, aurora._run_reasoning_pipeline | — | 0 |
| `interaction_confidence` | aurora._apply_interaction_quasi_route, aurora._run_reasoning_pipeline | — | 3 |
| `interaction_quasi_ready` | aurora._apply_interaction_quasi_route, aurora._run_reasoning_pipeline | — | 2 |
| `interaction_route_reason` | aurora._apply_interaction_quasi_route, aurora._run_reasoning_pipeline | — | 1 |
| `interaction_wake_tiers` | aurora._apply_interaction_quasi_route, aurora._run_reasoning_pipeline | — | 0 |
| `interaction_failure_indicators` | aurora._apply_interaction_quasi_route | — | 0 |
| `interaction_expected_effects` | aurora._apply_interaction_quasi_route | — | 0 |
| `interaction_search_policy` | aurora._apply_interaction_quasi_route, aurora._run_reasoning_pipeline | — | 0 |
| `utterance_meta` | aurora._run_reasoning_pipeline | — | 2 |
| `input_stance` | aurora._run_reasoning_pipeline | aurora_reasoning_paths.utterance_shape, aurora._chain_down5_understanding | 3 |
| `pragmatic_signals` | aurora._run_reasoning_pipeline | — | 9 |
| `subsurface_conscious_frame` | aurora._run_reasoning_pipeline | — | 0 |
| `subsurface_conscious_crest` | aurora._run_reasoning_pipeline | — | 0 |
| `live_sensory_vitals` | aurora._run_reasoning_pipeline | — | 0 |
| `parsed` | aurora._chain_up1_information | — | 3 |
| `relational_form` | aurora._chain_up1_information, aurora._chain_up2_belief | aurora_reasoning_paths.utterance_shape | 26 |
| `perspective_birth` | aurora._chain_up1_information | — | 0 |
| `axis_tensions` | aurora._chain_up1_information | aurora._run_reasoning_pipeline | 3 |
| `collective_dominant_axis` | aurora._chain_up1_information | — | 1 |
| `collective_resonance` | aurora._chain_up1_information | aurora._chain_up3_purpose | 1 |
| `reality_warp` | aurora._chain_up1_information | — | 1 |
| `warp_severity` | aurora._chain_up1_information | — | 2 |
| `collective_axis_net` | aurora._chain_up1_information | aurora._chain_up3_purpose | 1 |
| `sedi_recalled` | aurora._chain_up1_information | aurora._chain_down2_belief | 1 |
| `sensory_crystal` | aurora._chain_up1_information | aurora._derive_emotional_layers, aurora._chain_down5_understanding | 46 |
| `recent_context_mode` | aurora._inject_surface_recent_context | aurora._chain_up2_belief | 2 |
| `recent_context` | aurora._inject_surface_recent_context | aurora._chain_up2_belief, aurora._chain_down5_understanding | 3 |
| `recent_context_turns` | aurora._inject_surface_recent_context | aurora._chain_up2_belief, aurora._build_established_strata_evidence | 2 |
| `working_memory_snapshot` | aurora._chain_up2_belief | — | 1 |
| `conversation_memory_summary` | aurora._chain_up2_belief | — | 0 |
| `memory_locations` | aurora._chain_up2_belief | — | 0 |
| `surface_conversation_frame` | aurora._chain_up2_belief | — | 2 |
| `braid_axis_blend` | aurora._chain_up3_purpose | — | 0 |
| `constraint_semantic_state` | aurora._chain_up3_purpose, aurora._chain_down5_understanding | — | 4 |
| `constraint_genealogy_trace` | aurora._chain_up3_purpose | — | 0 |
| `response_obligation` | aurora._chain_up3_purpose | — | 11 |
| `axis_activation` | aurora._chain_up3_purpose, aurora._build_comprehension_response | — | 17 |
| `axis_depth` | aurora._chain_up3_purpose, aurora._build_comprehension_response | — | 2 |
| `axis_intensity` | aurora._chain_up3_purpose, aurora._build_comprehension_response | — | 0 |
| `axis_polarity` | aurora._chain_up3_purpose, aurora._build_comprehension_response | — | 0 |
| `field_balance` | aurora._chain_up3_purpose, aurora._build_comprehension_response | — | 2 |
| `referent_map` | aurora._chain_up3_purpose, aurora._build_comprehension_response | — | 6 |
| `referent_confidence` | aurora._chain_up3_purpose, aurora._build_comprehension_response | — | 1 |
| `resolved_referent_topic` | aurora._chain_up3_purpose, aurora._build_comprehension_response | — | 4 |
| `claim_confidence` | aurora._chain_up3_purpose, aurora._build_comprehension_response | — | 1 |
| `resolved_claim` | aurora._chain_up3_purpose, aurora._build_comprehension_response | — | 1 |
| `dominant_emotion` | aurora._chain_up3_purpose, aurora._build_comprehension_response | — | 13 |
| `emotional_coherence` | aurora._chain_up3_purpose, aurora._build_comprehension_response | aurora._apply_pipeline_modulation | 1 |
| `emotional_energy` | aurora._chain_up3_purpose, aurora._build_comprehension_response | — | 2 |
| `surface_reactive_emotion` | aurora._chain_up3_purpose, aurora._extract_pipeline_signals | aurora._apply_pipeline_modulation | 7 |
| `surface_reactive_bias` | aurora._chain_up3_purpose, aurora._extract_pipeline_signals | — | 2 |
| `surface_reactive_intensity` | aurora._chain_up3_purpose, aurora._extract_pipeline_signals | aurora._apply_pipeline_modulation | 1 |
| `deep_emotional_state` | aurora._chain_up3_purpose, aurora._extract_pipeline_signals | — | 3 |
| `deep_dominant_emotion` | aurora._chain_up3_purpose, aurora._extract_pipeline_signals | — | 3 |
| `deep_passion_state` | aurora._chain_up3_purpose, aurora._extract_pipeline_signals | — | 1 |
| `emotion_bridge` | aurora._chain_up3_purpose, aurora._extract_pipeline_signals | — | 3 |
| `polarity_gradient` | aurora._chain_up3_purpose | — | 0 |
| `noncomp_input` | aurora._apply_noncomp_input_guidance, aurora._apply_noncomp_behavior_actuation | — | 6 |
| `noncomp_anchor` | aurora._apply_noncomp_input_guidance | — | 0 |
| `perception_result` | aurora._run_reasoning_pipeline | — | 0 |
| `active_abilities` | aurora._run_reasoning_pipeline | aurora._run_reasoning_pipeline | 2 |
| `active_ability_effects_raw` | aurora._run_reasoning_pipeline | — | 0 |
| `active_ability_effects` | aurora._run_reasoning_pipeline, aurora._apply_noncomp_behavior_actuation | aurora._apply_noncomp_behavior_actuation, aurora._chain_down4_meaning, aurora._build_comprehension_response | 3 |
| `active_ability_effect_translation` | aurora._run_reasoning_pipeline | — | 0 |
| `active_ability_effect_passive` | aurora._run_reasoning_pipeline | — | 0 |
| `active_ability_effect_unhandled` | aurora._run_reasoning_pipeline | — | 0 |
| `ability_runtime_flags` | aurora._run_reasoning_pipeline, aurora._apply_noncomp_behavior_actuation | aurora._apply_noncomp_behavior_actuation, aurora._build_comprehension_response | 3 |
| `noncomp_input_behavior_actuation` | aurora._apply_noncomp_behavior_actuation | — | 0 |
| `pressure_before` | aurora._run_reasoning_pipeline | — | 11 |
| `pre_generation_conscious_frame` | aurora._run_reasoning_pipeline | aurora._chain_down5_understanding | 2 |
| `conscious_frame_mode` | aurora._run_reasoning_pipeline | aurora._build_comprehension_response | 2 |
| `conscious_frame_crest` | aurora._run_reasoning_pipeline | — | 0 |
| `pre_generation_subsurface_state` | aurora._run_reasoning_pipeline | — | 0 |
| `learned_hints` | aurora._chain_down5_understanding | — | 0 |
| `understanding_stage` | aurora._chain_down5_understanding | — | 1 |
| `dominant_meaning_form` | aurora._chain_down5_understanding | — | 7 |
| `goal_stack` | aurora._chain_down5_understanding | — | 2 |
| `salient_concepts` | aurora._chain_down5_understanding | — | 8 |
| `semantic_pressure` | aurora._chain_down5_understanding | — | 6 |
| `belief_tension` | aurora._chain_down5_understanding | — | 4 |
| `understanding_accuracy` | aurora._chain_down5_understanding | aurora._chain_down5_understanding | 4 |
| `understanding_fit_reason` | aurora._chain_down5_understanding | — | 1 |
| `understanding_accuracy_label` | aurora._chain_down5_understanding | — | 1 |
| `meaning_delta` | aurora._chain_down5_understanding | — | 5 |
| `user_stance` | aurora._chain_down5_understanding | — | 2 |
| `structured_perceptual_context` | aurora._chain_down5_understanding | — | 0 |
| `selected_conscious_action` | aurora._chain_down5_understanding | — | 1 |
| `representational_existence` | aurora._chain_down5_understanding | — | 0 |
| `constraint_grounded_candidate` | aurora._chain_down5_understanding | aurora._finalize_articulation | 1 |
| `native_meaning` | aurora._build_comprehension_response | — | 8 |
| `native_meaning_bundle` | aurora._build_comprehension_response | — | 6 |
| `sensory_native_meaning` | aurora._build_comprehension_response | — | 1 |
| `constraint_relation_alignment` | aurora._chain_down5_understanding | — | 0 |
| `response_fit_pressure` | aurora._emit_interpreted_turn_packet | aurora._ingest_current_turn_scout_evidence | 3 |
| `interpretation_adequate` | aurora._emit_interpreted_turn_packet | — | 1 |
| `interpreted_meaning` | aurora._emit_interpreted_turn_packet | — | 2 |
| `subsurface_response_evidence` | aurora._structure_current_turn_scout_evidence | aurora._derive_response_fit_observation_profile | 4 |
| `external_grounding_evidence` | aurora._structure_current_turn_scout_evidence | aurora._install_provisional_scout_grounding, aurora._reconsider_interpretation_from_scout_grounding | 3 |
| `poedex_learning_concept` | aurora._stage_poedex_learning_request | aurora._build_established_strata_evidence, aurora._stage_poedex_learning_request | 3 |
| `poedex_learning_request` | aurora._stage_poedex_learning_request | — | 1 |
| `poedex_learning_reason` | aurora._stage_poedex_learning_request | — | 0 |
| `poedex_learning_status` | aurora._stage_poedex_learning_request, aurora._learning_worker | aurora._stage_poedex_learning_request | 3 |
| `poedex_representation_concept` | aurora._stage_poedex_representation_request | aurora._build_established_strata_evidence | 3 |
| `poedex_representation_request` | aurora._stage_poedex_representation_request | — | 1 |
| `poedex_representation_reason` | aurora._stage_poedex_representation_request | — | 0 |
| `poedex_representation_status` | aurora._stage_poedex_representation_request, aurora._representation_worker | — | 3 |
| `question_alignment` | aurora._chain_down1_information | — | 1 |
| `pressure_tuner_kind` | aurora._run_reasoning_pipeline | — | 0 |
| `dual_strata_runtime` | aurora._run_reasoning_pipeline | — | 0 |
| `articulation_arbitration` | aurora._finalize_articulation | — | 2 |
| `other_model` | aurora._run_reasoning_pipeline | — | 0 |
| `observation_text` | aurora._run_reasoning_pipeline | — | 1 |
| `noncomp_should_seek_remedy` | aurora._apply_noncomp_input_guidance | — | 0 |
| `noncomp_remedy` | aurora._apply_noncomp_input_guidance | — | 0 |
| `concept_gap` | aurora._apply_noncomp_input_guidance | aurora._build_established_strata_evidence | 2 |
| `noncomp_gap_anchor` | aurora._apply_noncomp_input_guidance | — | 1 |
| `subsurface_dominant_axis_hint` | aurora._run_reasoning_pipeline | — | 0 |
| `subsurface_readiness_bias` | aurora._run_reasoning_pipeline | — | 0 |
| `subsurface_intuition_signals` | aurora._run_reasoning_pipeline | — | 0 |
| `subsurface_active_effects` | aurora._run_reasoning_pipeline | — | 0 |
| `subsurface_surface_guidance` | aurora._run_reasoning_pipeline | — | 0 |
| `subsurface_repair_phase` | aurora._run_reasoning_pipeline | — | 2 |
| `grammar_discourse_hint` | aurora._chain_down5_understanding | — | 0 |
| `_problem_solving_drive` | aurora._apply_pipeline_modulation | aurora._problem_drive_runtime_event | 1 |
| `grammar_motif_id` | aurora._run_reasoning_pipeline | — | 2 |
| `grammar_role_sequence` | aurora._run_reasoning_pipeline | — | 2 |
| `grammar_constraint_fit` | aurora._run_reasoning_pipeline | — | 2 |
| `rubric_weak_dims` | aurora._run_live_response_turn | — | 0 |
| `rubric_strong_dims` | aurora._run_live_response_turn | — | 0 |
| `rubric_quality_alert` | aurora._run_live_response_turn | — | 0 |
| `poedex_prefetch_concept` | aurora._stage_noncomp_prefetch | aurora._build_established_strata_evidence | 3 |
| `poedex_prefetch_status` | aurora._stage_noncomp_prefetch, aurora._prefetch_worker | — | 3 |

## 7. Her organs on live turns

An organ is an object held in `systems`. Counts are calls that cross INTO the organ from outside it, summed over the 4 turns. "Changed" lists the organ's own attributes whose size or value differed after a turn (a shallow comparison: a change deep inside a nested structure of unchanged size is not seen).

- Organs held in `systems`: **89**
- Entered during the live turns: **56**
- Never entered: **33**
- Entered, with no visible change to their own state: **9**

### 7a. Organs that took part

| Organ (class) | Entries | Entered through | Called by | Calls into | What it changed |
|---|---|---|---|---|---|
| `accountant` (LayerEnergyAccountant) | 1158 | pool ×512, withdraw ×484, slot ×120, magnitudes ×18 | chamber ×976, aurora._capture_pressure_snapshot ×80, metabolizer ×37, worth_eval ×30 | — | _tick, _pool, _history, _aurora_evolved_reflections, _aurora_generic_evolution_state, _replenishment_log |
| `genealogy` (ConstraintGenealogyLogger) | 862 | representation_is_eligible ×712, axis_relief_state ×52, pressure_orientation ×48, _outlet_fraction ×25 | working_memory ×714, grammar_engine ×63, aurora.project ×24, understanding_contract ×18 | function_lineage ×4 | tick_count, skipped_no_relief, _activity_log, _last_abilities_snapshot, _event_log, relief_event_count |
| `working_memory` (WorkingMemory) | 239 | _normalize_mention ×53, resolve_referents ×18, _is_explicit_meaning_or_continuity_request ×14, resolve_concept_meaning ×12 | aurora._normalize_surface_anchor_label ×49, aurora._build_comprehension_response ×41, aurora._run_live_response_turn ×37, understanding_contract ×24 | genealogy ×714, conversation_memory ×4, sedimemory ×3, perception ×2 | turn_count, recent_user_utterances, semantic_anchor_pool, semantic_frames, active_contexts, stated_facts |
| `identity_field` (NoncompField) | 178 | axis_pressure ×80, ingest_external_input ×32, ingest_sensory_event ×20, ingest_internal_signal ×16 | tensor_expressions ×60, consciousness ×24, aurora._extract_pipeline_signals ×20, pressure_pump ×20 | — | _internal_signals |
| `system_introspection` (AuroraSystemIntrospection) | 114 | record_boundary_decision ×95, find_functions ×11, begin_episode ×4, finish_episode ×4 | perception ×55, aurora._run_reasoning_pipeline ×16, reflective_readdressing ×11, aurora._process_external_user_turn_impl ×8 | function_lineage ×29, understanding_contract ×8, manual_code_lineage ×4, quasiarch_observer ×4 | _systems, _episodes, _episode_order, _find_cache, _match_feature_cache |
| `sedimemory` (SediMemory) | 80 | recall_semantic ×28, ingest_event ×28, recall ×8, dce_recall ×8 | consciousness ×24, aurora._run_reasoning_pipeline ×12, lexical_grounding ×9, aurora._build_established_strata_evidence ×8 | — | _event_log |
| `perception` (ExpressionPerceptionEngine) | 73 | set_axis_context ×16, ingest_interaction ×15, express ×10, set_personality ×8 | aurora._run_reasoning_pipeline ×33, aurora._build_communication_contributors ×16, aurora._chain_up3_purpose ×8, aurora._build_comprehension_response ×8 | system_introspection ×55, grammar_engine ×20 | total_perceptions, total_expressions, _dominant_axis, _dominant_emotion, _axis_activation, _aurora_evolved_reflections |
| `lattice` (IVMLattice) | 67 | heat_status ×17, get_global_heat ×16, admit ×12, get_global_polarity ×12 | aurora._capture_pressure_snapshot ×16, collective ×12, consciousness ×8, chamber ×6 | — | nodes, _spatial, _constitutive_mobility, _initial_total_energy, total_created, total_ticks |
| `warp_field` (WarpField) | 66 | submit ×66 | lexical_grounding ×39, tensor_expressions ×12, aurora._run_live_response_turn ×6, communication_emergence ×4 | language_field ×41, dream_trainer ×5, communication_emergence ×4, sedimemory ×3 | _demands, _decisions, _demand_count, _pathway_counts, _anomaly_ledger |
| `lexical_grounding` (AuroraLexicalGrounding) | 59 | observe_lexical_context ×45, drain_turn_consumption_trace ×8, has_promoted_relation_role ×5, flush_write_batch ×1 | recursive_causal_waveform ×23, aurora._run_observation_pipeline ×22, aurora._build_communication_contributors ×8, aurora.<lambda> ×5 | warp_field ×39, sedimemory ×9 | systems, _candidates, _pending_context, _tick, _warp_trials, _wb_pending |
| `language_field` (LanguageField) | 54 | check_and_extend ×41, build_pragmatic_vector ×4, ignition_check ×4, extract_proto_language ×4 | warp_field ×41, aurora._build_comprehension_response ×8, aurora._run_live_response_turn ×5 | tensor_expressions ×8 | _tensor_confirmed |
| `dimensional` (DimensionalSystems) | 44 | process_synthesis ×12, update_emotional_state ×12, get_stats ×8, _current_pressure_vec ×4 | consciousness ×16, aurora._run_reasoning_pipeline ×8, aurora._run_live_response_turn ×4, aurora._chain_up1_information ×4 | — | _last_signals |
| `understanding_contract` (RuntimeUnderstandingContract) | 41 | snapshot ×12, attach_pending_contributors ×12, ingest_observation ×7, commit_application ×4 | aurora._run_live_response_turn ×19, system_introspection ×8, aurora._run_reasoning_pipeline ×4, aurora._process_external_user_turn_impl ×4 | working_memory ×24, genealogy ×18, sedimemory ×4 | _wb_pending, state, _wb_depth |
| `function_lineage` (UniversalFunctionLineage) | 33 | lineage_for ×25, status ×8 | system_introspection ×29, genealogy ×4 | — | _systems |
| `grammar_engine` (GrammarEngine) | 29 | observe_exchange ×20, suggest_discourse ×8, prepare_response_trace ×1 | perception ×20, aurora._chain_down5_understanding ×4, aurora._build_established_strata_evidence ×4, aurora._run_reasoning_pipeline ×1 | genealogy ×63 | _last_motif_id |
| `field_balancer` (ConstraintFieldBalancer) | 28 | rebalanced_activation ×12, update ×8, status ×8 | aurora._chain_up3_purpose ×12, aurora._build_comprehension_response ×12, aurora._run_observation_pipeline ×4 | genealogy ×8 | _exchange_count |
| `conversation_memory` (ConversationMemory) | 27 | memory_sweep_summary ×8, recall_about ×7, open_evolutionary_trace ×4, record_exchange ×4 | aurora._run_live_response_turn ×12, aurora._build_established_strata_evidence ×10, working_memory ×4, aurora._build_comprehension_response ×1 | — | entries, evolutionary_trace_log, mutation_ledger, topics_discussed |
| `identity` (BehavioralIdentityEngine) | 24 | get_personality ×12, process_episode ×8, process_from_assembly ×4 | aurora._run_reasoning_pipeline ×24 | — | generation, _last_constraint_axis |
| `sensory_crystal` (AuroraSensoryCrystal) | 21 | get_state ×21 | consciousness ×8, aurora._run_live_response_turn ×4, aurora._chain_up1_information ×4, aurora._chain_up3_purpose ×4 | — | **nothing visible** |
| `quasiarch_observer` (AuroraQuasiArchObserver) | 18 | record_pressure_disturbance ×10, record_observation ×4, reason_about_event ×3, record_intervention_event ×1 | pressure_pump ×10, system_introspection ×4, aurora._emit_honest_abstain_and_seek ×2, aurora._flush_quasiarch_runtime_events ×2 | genealogy ×1 | issue_counts, issue_consultation_debt |
| `tensor_expressions` (TensorExpressionLayer) | 16 | behavioral_state ×16 | language_field ×8, consciousness ×8 | identity_field ×60, warp_field ×12 | _cache_ts, _update_count, _cached_state |
| `noncomp_manifold_directory` (ManifoldDirectory) | 16 | open ×8, entries_for_axis ×4, get_index_entry ×4 | noncomp_reflexive_interpreter ×16 | — | **nothing visible** |
| `communication_emergence` (AuroraCommunicationEmergence) | 13 | prepare_semantic_state ×4, observe_turn ×4, check_and_extend ×4, flush_write_batch ×1 | aurora._chain_up3_purpose ×4, aurora._process_external_user_turn_impl ×4, warp_field ×4, aurora.process_external_user_turn ×1 | genealogy ×4, warp_field ×4 | systems, _pending, _tick, _families, _wb_pending, _wb_depth |
| `perspective` (PrimitivePerspectiveEngine) | 12 | form ×12 | collective ×12 | — | formed |
| `collective` (IStateCollective) | 12 | process ×12 | consciousness ×8, aurora._chain_up1_information ×4 | lattice ×12, perspective ×12 | synthesis_count, history |
| `constraint_reasoner` (ConstraintReasoner) | 12 | reason ×4, to_process_context ×4, integrate ×4 | aurora._run_live_response_turn ×12 | warp_field ×3 | **nothing visible** |
| `bias_engine` (LeverageBiasEngine) | 12 | band_position ×8, compute_nudges ×4 | aurora._advance_intake_pipeline ×4, metabolizer ×4, aurora._sync_noncomp_runtime_band ×4 | accountant ×4 | _window |
| `interaction_processing` (InteractionProcessing) | 12 | route_interaction ×4, observe_interaction ×4, get_status ×4 | aurora._observe_interaction_runtime_turn ×8, aurora._apply_interaction_quasi_route ×4 | — | _bases |
| `recursive_causal_waveform` (AuroraRecursiveCausalReasoningWaveform) | 12 | receive_disturbance ×4, prepare_semantic_state ×4, complete_cycle ×4 | aurora._process_external_user_turn_impl ×8, aurora._chain_up3_purpose ×4 | lexical_grounding ×23, genealogy ×9, system_introspection ×4, understanding_contract ×4, sedimemory ×1 | systems, _cycles, _pending_response_cycle_id, _active_cycle, _gap_counter, _warp_trials |
| `pressure_pump` (WaveformPressurePump) | 10 | inject ×10 | aurora._run_live_response_turn ×6, aurora._chain_up1_information ×4 | identity_field ×20, quasiarch_observer ×10 | _trace_buffer |
| `solidification` (SolidificationPipeline) | 9 | observe_recurrence ×5, drain_solidified ×4 | aurora._advance_intake_pipeline ×9 | — | **nothing visible** |
| `relational_comparison` (RelationalComparisonEngine) | 9 | ground_to_self ×4, select_best_comparison_target ×3, compare ×2 | aurora._compute_peer_relation ×5, aurora._compute_self_relation ×4 | — | _history |
| `dream_trainer` (DreamTrainer) | 9 | flush_lessons_to_simulation ×5, get_response_hints ×4 | warp_field ×5, aurora._chain_up5_understanding ×4 | — | _systems, _flush_call_count |
| `reasoning_paths` (ReasoningPaths) | 9 | begin_turn ×4, end_turn ×4, flush_write_batch ×1 | aurora._run_reasoning_pipeline ×4, aurora._process_external_user_turn_impl ×4, aurora.process_external_user_turn ×1 | — | pending, _wb_pending, _wb_depth |
| `reflective_readdressing` (AuroraReflectiveReaddressing) | 8 | prepare_turn ×4, capture_turn ×4 | aurora._process_external_user_turn_impl ×8 | system_introspection ×11 | _systems, _episodes, _last_decision_trace |
| `consciousness` (ConsciousnessEngine) | 8 | process ×8 | aurora._run_reasoning_pipeline ×8 | sedimemory ×24, identity_field ×24, dimensional ×16, lattice ×8, tensor_expressions ×8 | _pending_warps, _mtsl_turn_counter |
| `metabolizer` (IntakeMetabolizer) | 8 | receive ×4, advance ×4 | aurora._advance_intake_pipeline ×8 | accountant ×37, bias_engine ×4 | _live, _total_received, _promotion_queue, _total_promoted |
| `noncomp_manifold_router` (ManifoldRouter) | 8 | update_band ×4, route_signal ×4 | aurora._sync_noncomp_runtime_band ×4, noncomp_reflexive_interpreter ×4 | — | **nothing visible** |
| `noncomp_reflexive_interpreter` (ReflexiveInterpreter) | 8 | update_band ×4, interpret ×4 | aurora._sync_noncomp_runtime_band ×4, aurora._apply_noncomp_input_guidance ×4 | noncomp_manifold_directory ×16, noncomp_manifold_router ×4 | _history, _worth_histories |
| `_attention_engine` (AttentionEngine) | 8 | tick ×4, get_meaning_nucleus ×4 | aurora._run_live_response_turn ×8 | — | history, _salience_ema, _tension_ema |
| `_diff_history_buffer` (DifferenceHistoryBuffer) | 8 | record ×4, snapshot ×4 | aurora._run_live_response_turn ×8 | — | _history |
| `metabolic_clock` (MetabolicClock) | 8 | turn ×8 | aurora.process_external_user_turn ×8 | — | _systems, _span_turns, _span_slots |
| `chamber` (EvolutionaryChamber) | 7 | status ×4, tick ×2, observe_external_evidence ×1 | _surface_dispatcher ×4, aurora._run_live_response_turn ×3 | accountant ×976, genealogy ×8, lattice ×6 | tick_count, _prev_boundary_polarity, _aurora_evolved_reflections, _aurora_generic_evolution_state |
| `_thought_braid` (ThoughtBraid) | 6 | tap ×4, feed_expression_back ×2 | aurora._run_live_response_turn ×6 | — | _braid_tick, _memory_stream, _sensory_stream, _predictive_stream, _emotion_stream, _last_expression_feedback |
| `constraint_emitter` (ConstraintEmitter) | 5 | check_and_run_integration ×2, _emit_abstain ×2, _seek_gap ×1 | aurora._emit_honest_abstain_and_seek ×5 | — | **nothing visible** |
| `simulation` (SimulationEngine) | 5 | run_epoch ×5 | consciousness ×5 | — | _systems, total_episodes |
| `worth_eval` (CrossScaleWorthEvaluator) | 5 | evaluate ×5 | aurora._advance_intake_pipeline ×5 | accountant ×30 | _histories, _promoted_this_session |
| `lineage_emergence_journal` (LiveLineageJournal) | 5 | observe_systems ×4, flush_write_batch ×1 | aurora._observe_live_lineage_emergence ×4, aurora.process_external_user_turn ×1 | — | seen_abilities, _wb_pending, _storage_mtime_ns, _wb_depth |
| `unformed_patterns` (UnformedPatterns) | 5 | observe_turn ×4, flush_write_batch ×1 | aurora._process_external_user_turn_impl ×4, aurora.process_external_user_turn ×1 | — | pending, patterns, _wb_pending, last_residue, _wb_depth |
| `comprehension_gap_system` (ComprehensionGapSystem) | 4 | process ×4 | aurora.dual_question_pipeline ×4 | — | _turn_count |
| `entropy_detector` (EntropySaturationDetector) | 4 | measure ×4 | aurora._advance_intake_pipeline ×4 | accountant ×12 | _entropy_window, _prev_entropy |
| `manual_code_lineage` (ManualCodeLineageAssimilator) | 4 | status ×4 | system_introspection ×4 | — | **nothing visible** |
| `screen_observer` (ScreenObserver) | 4 | current_scene ×4 | aurora._chain_up1_information ×4 | — | _systems, _capture_fail_streak, last_claims, _capture_disabled |
| `_surface_dispatcher` (SurfaceDispatcher) | 4 | tick ×4 | aurora._run_reasoning_pipeline ×4 | chamber ×4 | _tick_count |
| `core_identity` (CoreRelationalIdentity) | 1 | get_entity ×1 | aurora._build_grounded_fallback_response ×1 | — | **nothing visible** |
| `evolved_surfaces` (AuroraEvolvedSurfaceEngine) | 1 | __getattr__ ×1 | aurora.process_external_user_turn ×1 | — | **nothing visible** |

### 7b. Organs never entered during a live turn

| Organ | Class | Module |
|---|---|---|
| `contradiction_ledger` | ContradictionLedger | aurora_ivm |
| `sensory` | SensoryCompetencyEngine | aurora_hardware_io |
| `hardware` | HardwareInterface | aurora_hardware_io |
| `sensory_integration` | SensoryIntegrationEngine | aurora_hardware_io |
| `vision_bootstrap` | ImageIngestionProtocol | aurora_image_ingestion |
| `_simulation_governor` | TimeDilationGovernor | aurora_simulation_engine |
| `_chain_bridge` | ChainSimBridge | aurora_runtime |
| `primitive_extractor` | PrimitiveExtractor | aurora_internal.aurora_primitive_extractor |
| `variant_promoter` | VariantPromoter | aurora_internal.aurora_variant_promotion |
| `strand_lib` | StrandLibrary | aurora_internal.aurora_dna_strand_schema |
| `_strand_builder` | StrandBuilder | aurora_internal.aurora_dna_strand_schema |
| `aurora` | GovernancePersistenceGateway | aurora_governance_persistence_gateway |
| `state_persistence` | StatePersistence | aurora_governance_persistence_gateway |
| `search_adapter` | SearchAdapter | aurora |
| `dream_orchestrator` | DreamEvolutionOrchestrator | aurora_internal.aurora_dream_evolution_orchestrator |
| `autonomy` | AutonomyEngine | aurora_autonomy |
| `drive_sync` | DriveSync | aurora_persistence_utils |
| `git_sync` | GitStateSync | aurora_persistence_utils |
| `checkpoint` | CheckpointManager | aurora_checkpoint |
| `enhanced_persist` | EnhancedStatePersistence | aurora_internal.aurora_identity_persistence |
| `icc_ledger` | ICCLedger | aurora_internal.aurora_icc_ledger |
| `strategic_horizon` | StrategicHorizonLayer | aurora_internal.aurora_strategic_horizon |
| `operator_composer` | OperatorComposer | aurora_internal.aurora_operator_composer |
| `code_evolution_chamber` | CodeEvolutionChamber | aurora_internal.aurora_code_evolution_chamber |
| `operational_synthesis` | AuroraOperationalSynthesisChamber | aurora_internal.aurora_operational_synthesis |
| `general_execution_foundry` | AuroraGeneralExecutionFoundry | aurora_internal.aurora_general_execution_foundry |
| `noncomp_layer_compiler` | NonCompLayerCompiler | aurora_noncomp_layer_compiler |
| `_pressure_router` | PressureRouter | aurora_internal.aurora_pressure_router |
| `_dpme_bridge` | DPMEPressureBridge | aurora_internal.aurora_dpme_pressure_bridge |
| `_braided_substrate` | BraidedSubstrateLayer | aurora_internal.aurora_braided_substrate |
| `_connectivity_monitor` | ConnectivityMonitor | aurora_offline_resilience |
| `_thought_braid_thread` | StreamingThoughtThread | aurora_thought_formation |
| `time_dilation_governor` | TimeDilationGovernor | aurora_simulation_engine |

## 5. The `systems` bus: written and never read

| Key | Written by |
|---|---|
| `_active_introspection_episode` | aurora_system_introspection.begin_episode |
| `_active_recursive_causal_cycle` | aurora_recursive_causal_reasoning_waveform._publish_active_cycle |
| `_active_thought_state` | aurora_daemon._record_task_run |
| `_ambient_listener_state` | aurora_daemon._set_listener_state |
| `_ambient_suppress_until` | aurora_voice._start_recording, aurora_voice.daemon_voice_session |
| `_cached_device_state` | aurora_bridge._run_burst |
| `_clone_harvest_absorb` | aurora_bridge.initialize |
| `_core_dilation` | aurora_metabolic_steps.step_governor |
| `_core_understanding_last` | aurora_metabolic_steps.step_core_understanding |
| `_dev_events_logged` | aurora_developmental_log.record_developmental_event |
| `_explicit_voice_active` | aurora_voice._finish_recording, aurora_voice._process_recording, aurora_voice._start_recording |
| `_fgae_language_projection` | aurora._generate_from_manifold |
| `_fgae_selected_entries` | aurora._generate_from_manifold |
| `_gap_seeking_concept_type` | aurora_bridge._as_int, aurora_bridge._run_burst, aurora_curiosity_engine._step6_settlement |
| `_generative_only_responses` | aurora._generative_only_responses_enabled |
| `_geological_summary` | aurora._discuss_cb |
| `_historical_communication_apprenticeship` | aurora_historical_experience_environment._observe_communication_possibility |
| `_historical_experience_complete` | aurora_historical_experience_environment._run |
| `_incoming_recursive_causal_disturbance` | aurora._process_external_user_turn_impl |
| `_interaction_search_viability` | aurora.__init__ |
| `_language_ignition` | aurora._build_comprehension_response |
| `_last_application_understanding_profile` | aurora_understanding_contract.commit_application |
| `_last_articulation_arbitration` | aurora._finalize_articulation |
| `_last_articulation_seed` | aurora_voice_gate.apply_voice_gate, aurora_voice_gate.articulate_from_pressure |
| `_last_communication_emergence` | aurora._process_external_user_turn_impl |
| `_last_confluence` | aurora_voice_gate.apply_voice_gate |
| `_last_corpus_quality` | aurora.witness |
| `_last_crest_blended_sources` | aurora._compress_at_crest |
| `_last_crest_output` | aurora._enforce_emission_discipline |
| `_last_dream_communication_evidence` | aurora._finalize_validated_communication |
| `_last_episode_pack` | aurora._discuss_cb |
| `_last_explicit_voice_time` | aurora_voice._process_recording, aurora_voice.daemon_voice_session, aurora_voice.resume |
| `_last_field_resonance` | aurora._run_live_response_turn |
| `_last_fitness_result` | aurora.__init__ |
| `_last_fused_output` | aurora._enforce_emission_discipline |
| `_last_gap_research` | aurora.__init__ |
| `_last_identity_tool_result` | aurora_tool_mind.ingest_tool_result |
| `_last_learning_delta` | aurora._record_learning_delta |
| `_last_live_turn_profile` | aurora._commit_early_response |
| `_last_lww_output` | aurora._enforce_emission_discipline |
| `_last_other_model` | aurora._run_afterthought_episode_bg |
| `_last_pipeline_learning_resolution` | aurora_dream_trainer.resolve_pipeline_learning |
| `_last_propositions` | aurora_propositional_understanding.integrate_turn |
| `_last_ps_report` | aurora._declarative_segments |
| `_last_quasiarch_runtime_records` | aurora._flush_quasiarch_runtime_events |
| `_last_reasoning_path` | aurora._process_external_user_turn_impl |
| `_last_recommendation_notes` | aurora._discuss_cb |
| `_last_recursive_causal_cycle` | aurora._process_external_user_turn_impl, aurora_recursive_causal_reasoning_waveform._publish_completion |
| `_last_recursive_causal_semantics` | aurora_recursive_causal_reasoning_waveform._publish_active_cycle |
| `_last_reentry_text_len` | aurora_braid_wiring.complete_expression |
| `_last_reentry_tick` | aurora_braid_wiring.complete_expression |
| `_last_reflection_result` | aurora._discuss_cb |
| `_last_reflective_authority_rejection` | aurora._apply_reflective_readdressing_to_state, aurora._commit_early_response |
| `_last_reflective_reapplication` | aurora._merge |
| `_last_research_observation` | aurora._broadcast_poedex_result |
| `_last_research_reapplication` | aurora._merge_labels |
| `_last_response_pressure_training_plan` | aurora._apply_response_pressure_training_plan |
| `_last_response_runtime_contract` | aurora._process_external_user_turn_impl |
| `_last_rest` | aurora_metabolic_steps.step_rest_close |
| `_last_rubric_mean` | aurora._discuss_cb |
| `_last_saturation_signal` | aurora._pol |
| `_last_semantic_pressure` | aurora._run_afterthought_episode_bg |
| `_last_staged_pipeline_candidate_count` | aurora._retain_cross_pipeline_learning |
| `_last_surface_packet` | aurora_daemon._consume_surface_continuity_feed |
| `_last_tone_prosody` | aurora.__init__ |
| `_last_understanding_profile` | aurora_understanding_contract.ingest_observation |
| `_last_warp_result` | aurora.__init__ |
| `_last_waveform` | aurora._enforce_emission_discipline |
| `_lattice_passes_last` | aurora_metabolic_steps.step_lattice |
| `_low_resource_evolution_relief` | aurora_daemon._persist, aurora_daemon._stage_low_resource_evolution_relief |
| `_maintenance_viability` | aurora._process_external_user_turn_impl |
| `_meaning_nucleus` | aurora._run_live_response_turn, aurora_training_pulse._capture_nucleus |
| `_native_reflection` | aurora_working_memory._render_from_comprehension_intent |
| `_native_reflection_history` | aurora_working_memory._render_from_comprehension_intent |
| `_poedex_learning` | aurora._learning_worker |
| `_pragmatic_vector` | aurora._run_live_response_turn |
| `_praxis_context` | aurora_praxis_bridge._witness |
| `_present_frame_active` | aurora._declarative_segments |
| `_prev_dominant_axis` | aurora._build_comprehension_response |
| `_render_record` | aurora_working_memory._render_from_comprehension_intent |
| `_reported_missing_organs` | aurora._report_missing_required_organ |
| `_runtime_health` | aurora_runtime_health.publish_runtime_health |
| `_runtime_health_write_error` | aurora_runtime_health.publish_runtime_health |
| `_runtime_ready` | aurora_runtime_health.publish_runtime_health |
| `_runtime_status` | aurora_runtime_health.publish_runtime_health |
| `_runtime_unready` | aurora_runtime_health.mark_runtime_unready, aurora_runtime_health.publish_runtime_health |
| `_runtime_unready_reason` | aurora_runtime_health.mark_runtime_unready, aurora_runtime_health.publish_runtime_health |
| `_screen_observation` | aurora_bridge.provide_screen_observation |
| `_screen_visual_data` | aurora_bridge.provide_screen_observation |
| `_search_viability` | aurora._process_external_user_turn_impl |
| `_simulation_bridge_active` | aurora._run_simulation_live_response_bridge |
| `_simulation_governor` | aurora._h_seek |
| `_sleep_dream_context` | aurora_daemon._build_sleep_dream_context |
| `_strata_link_server` | aurora_daemon.run |
| `_toroidal_signature` | aurora._refresh_live_dual_strata_runtime |
| `_warp_research_target` | aurora._queue_warp_poedex_study_target |

## 6. The `systems` bus: read, never written by assignment

These may be set by `setdefault`/`update` or by another process; each needs a look, none is proven dead.

| Key | Read by |
|---|---|
| `_abstained_gaps` | aurora._seed_abstained_gap, aurora_curiosity_engine._step1_emergence |
| `_allow_degraded` | aurora_runtime_health.publish_runtime_health |
| `_articulation_assist_state` | aurora._articulation_reuse_guidance, aurora_understanding_contract._derive_cost_state |
| `_auto_message_to_sunni_enabled` | aurora._run_afterthought_episode_bg, aurora_daemon._daemon_send_aurora_message |
| `_autonomy` | aurora_pressure_mathematics_tracker._take_snapshot |
| `_axis_state` | aurora_thought_formation._read_axes, aurora_thought_formation._read_istates |
| `_chat_response_pressure_tuner` | aurora._collect_response_pressure_guides |
| `_comprehension_gap` | aurora._discuss_cb |
| `_cpm_session` | aurora._sensory_promotion_hook |
| `_current_turn_knowledge_gaps` | aurora._ingest_current_turn_scout_evidence |
| `_deferred_surface_dispatcher_evidence` | aurora._commit_early_response |
| `_distillation_crystals` | aurora_daemon._record_task_run |
| `_gauntlet_events` | aurora_bridge.get_gauntlet_status |
| `_last_reflective_reasoning_episode` | aurora_reflective_readdressing.latest_episode |
| `_last_rubric_evidence` | aurora._build_communication_contributors, aurora._run_live_response_turn |
| `_live_session_id` | aurora_live_experience._observe |
| `_log_fn` | aurora_hardware_io.__init__ |
| `_manifold_directory` | aurora._represent_gap |
| `_manifold_router` | aurora._represent_gap |
| `_noncomp_output` | aurora._discuss_cb |
| `_open_curiosity_loops` | aurora_braid_wiring._build_turn_process_contexts, aurora_thought_formation._update_predictive |
| `_open_loops` | aurora._seed_abstained_gap, aurora_braid_wiring._build_turn_process_contexts, aurora_curiosity_engine._register_background_processes |
| `_pending_capability_gap` | aurora_curiosity_engine._not_stop |
| `_pending_proactive_thoughts` | aurora_bridge.get_pending_report |
| `_pending_reactive_events` | aurora_daemon._record_task_run |
| `_pipeline_state` | aurora._build_comprehension_response, aurora_braid_wiring.begin_expression, aurora_braid_wiring.checkpoint_expression |
| `_pre_turn_known_anchors` | aurora._turn_has_no_known_anchor |
| `_pressure_history` | tool_registry._query_pressure_history |
| `_relational_claim_log` | aurora_bridge._prime_waveform_composite |
| `_runtime_systems` | aurora_dream_evolution_orchestrator._apply_code_evolution, aurora_dream_evolution_orchestrator._apply_genealogy, aurora_dream_evolution_orchestrator._record_ref |
| `_scout_retry_done` | aurora._attempt_abstention_rescue |
| `_session_id` | aurora.explore |
| `_state_dir` | activation_field.extract_seeds_from_systems, aurora._commit_early_response, aurora._full_save |
| `_tension_bus` | aurora_understanding_contract._flag_tension |
| `_turn_participants` | aurora_propositional_understanding.participants |
| `_turn_tick` | aurora._run_afterthought_episode_bg |
| `_variant_transition_predictor` | aurora._finalize_validated_communication |
| `_warp_candidate` | aurora_bridge._check_internal_health, aurora_curiosity_engine._not_stop |
