# Architectural comparison

Authors: Sunni (Sir) Morningstar & Cael Devo  
Base `d9a335038080` (claude/knowledge-graph), head `5cb5581adc37` (claude/aurora-integration-20261118). Static content hashes c7d9fcc5031c and 20b8dffc3f9c.

## 1. Function lineage

17555 functions in base, 17590 in head. 1415 kept their identity with a changed body; 11 changed identity (moved or renamed); 25 were removed; 70 are new.

A changed identity breaks any record keyed by the old id (lineage, provenance, fault and test references).

- moved: `fn:aurora_autonomy.DailyQuotas.to_dict` -> `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict` (same name and signature)
- moved: `fn:aurora_checkpoint.CorpusCursor.to_dict` -> `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict` (same name and signature)
- moved: `fn:aurora_checkpoint.RollingStats.to_dict` -> `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict` (same name and signature)
- moved: `fn:aurora_internal.aurora_correspondence_loop.CommittedPrediction.to_dict` -> `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict` (same name and signature)
- moved: `fn:aurora_internal.constraint_genealogy.PressureVec.to_dict` -> `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict` (same name and signature)
- moved: `fn:aurora_internal.dual_strata.variant_transition_predictor.TransitionRecord.to_dict` -> `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict` (same name and signature)
- moved: `fn:aurora_internal.quasiarch_observer.dimensional_memory.LineageEdge.to_dict` -> `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict` (same name and signature)
- moved: `fn:aurora_ivm.ContradictionRecord.to_dict` -> `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict` (same name and signature)
- moved: `fn:aurora_language_field.LSAEntry.to_dict` -> `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict` (same name and signature)
- moved: `fn:aurora_vision_clustering.VisualCluster.to_dict` -> `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict` (same name and signature)
- moved: `fn:aurora_vision_clustering.VisualFeatureVector.to_dict` -> `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict` (same name and signature)
- removed: `fn:aurora_behavioral_identity._clamp`; still-present callers in base: `fn:aurora_behavioral_identity.BehavioralIdentityEngine._apply_identity_homeostasis`, `fn:aurora_behavioral_identity.BehavioralIdentityEngine._constraint_axes`, `fn:aurora_behavioral_identity.BehavioralIdentityEngine._identity_floor_ratio`, `fn:aurora_behavioral_identity.BehavioralIdentityEngine._pressure_axes`; ran in desktop_boot,desktop_turns
- removed: `fn:aurora_checkpoint.CorpusCursor.from_dict`; still-present callers in base: `fn:aurora_checkpoint.CheckpointManager.restore`; ran in desktop_boot
- removed: `fn:aurora_checkpoint.RollingStats.from_dict`; still-present callers in base: `fn:aurora_checkpoint.CheckpointManager.restore`; ran in desktop_boot
- removed: `fn:aurora_expression_perception._clamp`; still-present callers in base: `fn:aurora_expression_perception.ExpressionEcology.spawn`, `fn:aurora_expression_perception.ExpressionPressure.evaluate`, `fn:aurora_expression_perception.ImpressionCascade._seed_shard_similarity`, `fn:aurora_expression_perception.ImpressionCascade.energy_to_shard`; ran in desktop_boot,desktop_turns
- removed: `fn:aurora_governance_persistence_gateway._clamp`; still-present callers in base: `fn:aurora_governance_persistence_gateway.NSpaceGateway._check_coherence`, `fn:aurora_governance_persistence_gateway.NSpaceGateway._express`, `fn:aurora_governance_persistence_gateway.NSpaceGateway._validate`; ran in desktop_turns
- removed: `fn:aurora_grammar_engine._clamp`; still-present callers in base: `fn:aurora_grammar_engine.GrammarEngine._pressure_state`, `fn:aurora_grammar_engine.GrammarEngine.prepare_response_trace`, `fn:aurora_grammar_engine.GrammarEngine.suggest_structure`, `fn:aurora_grammar_engine.MotifLineage.best_for_pressure._score`; ran in desktop_turns
- removed: `fn:aurora_hardware_io._clamp`; still-present callers in base: `fn:aurora_hardware_io.SensoryCompetencyEngine._extract_audio_features`, `fn:aurora_hardware_io.SensoryCompetencyEngine._extract_visual_features`, `fn:aurora_hardware_io.SensoryPatternMapper.map_audio_input`, `fn:aurora_hardware_io.SensoryPatternMapper.map_visual_input`
- removed: `fn:aurora_internal.aurora_braided_substrate._clamp`; still-present callers in base: `fn:aurora_internal.aurora_braided_substrate.BraidedSubstrateLayer._compute_stability`, `fn:aurora_internal.aurora_braided_substrate.BraidedSubstrateLayer._event_to_crossings`, `fn:aurora_internal.aurora_braided_substrate.BraidedSubstrateLayer.update`
- removed: `fn:aurora_internal.aurora_conversation_rubric_engine._clamp`; still-present callers in base: `fn:aurora_internal.aurora_conversation_rubric_engine.ConversationRubricEngine.score_conversation`, `fn:aurora_internal.aurora_conversation_rubric_engine._causal_score`, `fn:aurora_internal.aurora_conversation_rubric_engine._contradiction_markers`, `fn:aurora_internal.aurora_conversation_rubric_engine._generic_response_penalty`; ran in desktop_turns
- removed: `fn:aurora_internal.aurora_dream_genealogy_bridge._clamp`; still-present callers in base: `fn:aurora_internal.aurora_dream_genealogy_bridge.DreamGenealogyBridge._build_deficit_evidence`, `fn:aurora_internal.aurora_dream_genealogy_bridge.DreamGenealogyBridge._build_delta_evidence`, `fn:aurora_internal.aurora_dream_genealogy_bridge.DreamGenealogyBridge._build_directive_evidence`, `fn:aurora_internal.aurora_dream_genealogy_bridge.DreamGenealogyBridge._build_leverage_evidence`
- removed: `fn:aurora_internal.aurora_language_state._clamp`; still-present callers in base: `fn:aurora_internal.aurora_language_state.LanguageStateVector._compute_growth`, `fn:aurora_internal.aurora_language_state.LanguageStateVector.update`, `fn:aurora_internal.aurora_language_state.PhrasePrint.reinforce`, `fn:aurora_internal.aurora_language_state.SemanticIntentCompiler._extract_intent`
- removed: `fn:aurora_internal.aurora_ontological_scaffolding._clamp`; still-present callers in base: `fn:aurora_internal.aurora_ontological_scaffolding.ClusterEngine._compute_coherence`, `fn:aurora_internal.aurora_ontological_scaffolding.OntologicalScaffoldingEngine._topic_tracking_score`, `fn:aurora_internal.aurora_ontological_scaffolding.OntologicalScaffoldingEngine.consolidate`, `fn:aurora_internal.aurora_ontological_scaffolding.OntologicalWeb._prune_nodes`; ran in desktop_boot,desktop_turns
- removed: `fn:aurora_internal.aurora_pressure_mathematics_tracker._clamp`; still-present callers in base: `fn:aurora_internal.aurora_pressure_mathematics_tracker.PressureMathematicsTracker._compute_axis_stagnation`, `fn:aurora_internal.aurora_pressure_mathematics_tracker.PressureMathematicsTracker._compute_evolutionary_velocity`, `fn:aurora_internal.aurora_pressure_mathematics_tracker.PressureMathematicsTracker._compute_gradient_health`, `fn:aurora_internal.aurora_pressure_mathematics_tracker.PressureMathematicsTracker._compute_metrics`
- removed: `fn:aurora_internal.aurora_primitive_extractor._clamp`
- removed: `fn:aurora_internal.aurora_rubric_influence_graph._clamp`; still-present callers in base: `fn:aurora_internal.aurora_rubric_influence_graph.RubricInfluenceGraph.analyze`
- removed: `fn:aurora_internal.aurora_semantic_probe_battery._clamp`
- removed: `fn:aurora_internal.aurora_specialized_avatar_synthesizer._clamp`; still-present callers in base: `fn:aurora_internal.aurora_specialized_avatar_synthesizer.PressureSpecializedAvatarSpec.to_avatar_overrides`, `fn:aurora_internal.aurora_specialized_avatar_synthesizer.SpecializedAvatarSynthesizer._apply_adaptive_policy`, `fn:aurora_internal.aurora_specialized_avatar_synthesizer.SpecializedAvatarSynthesizer._build_persistent_spec`, `fn:aurora_internal.aurora_specialized_avatar_synthesizer.SpecializedAvatarSynthesizer._build_spec_for_leverage`; ran in desktop_boot
- removed: `fn:aurora_internal.aurora_structural_pressure_steering._clamp`; still-present callers in base: `fn:aurora_internal.aurora_structural_pressure_steering.StructuralPressureSteering._build_accumulated_directive`, `fn:aurora_internal.aurora_structural_pressure_steering.StructuralPressureSteering._build_directive`, `fn:aurora_internal.aurora_structural_pressure_steering.StructuralPressureSteering.apply_to_dpme`
- removed: `fn:aurora_internal.constraint_genealogy._clamp`; still-present callers in base: `fn:aurora_internal.constraint_genealogy.ConstraintGenealogyLogger.__init__`, `fn:aurora_internal.constraint_genealogy.ConstraintGenealogyLogger._compression_efficiency_for_pair`, `fn:aurora_internal.constraint_genealogy.ConstraintGenealogyLogger._maintenance_discount`, `fn:aurora_internal.constraint_genealogy.ConstraintGenealogyLogger._record_promotion_outcome`; ran in desktop_boot,desktop_turns
- removed: `fn:aurora_ivm.ContradictionRecord.from_dict`; still-present callers in base: `fn:aurora_ivm.ContradictionLedger.load`
- removed: `fn:aurora_language_field.LSAEntry.from_dict`; still-present callers in base: `fn:aurora_language_field.LanguageField._load_lsa`
- removed: `fn:aurora_runtime._clamp`; still-present callers in base: `fn:aurora_runtime.ChainSimBridge._forward_to_sim`
- removed: `fn:aurora_simulation_engine._clamp`; still-present callers in base: `fn:aurora_simulation_engine.ConsciousLearner.generate_pool`, `fn:aurora_simulation_engine.ConsciousLearner.import_state`, `fn:aurora_simulation_engine.SimulatedAvatar._behavior_adjustment`, `fn:aurora_simulation_engine.SimulatedAvatar._dimension_pressure_adjustment`; ran in desktop_turns
- removed: `fn:aurora_vision_clustering.VisualCluster.from_dict`; still-present callers in base: `fn:aurora_image_ingestion.ImageIngestionProtocol.load_index`; ran in desktop_boot
- removed: `fn:aurora_vision_clustering.VisualFeatureVector.from_dict`; still-present callers in base: `fn:aurora_image_ingestion.ImageIngestionProtocol.load_index`; ran in desktop_boot
- new: `fn:aurora_curiosity_engine.CuriosityEngine.open_curiosity_loops`, no static caller
- new: `fn:aurora_internal.aurora_runtime_faults.bind_fault_recorder`, called by `mod:aurora`, `mod:aurora_acm_bridge`, `mod:aurora_articulation`, `mod:aurora_autonomy`
- new: `fn:aurora_internal.aurora_runtime_faults.bind_fault_recorder._aurora_fault`, no static caller
- new: `fn:aurora_internal.aurora_shared_helpers.DictRecord.from_dict`, called by `fn:aurora_checkpoint.CheckpointManager.restore`, `fn:aurora_image_ingestion.ImageIngestionProtocol.load_index`, `fn:aurora_ivm.ContradictionLedger.load`, `fn:aurora_language_field.LanguageField._load_lsa`
- new: `fn:aurora_internal.aurora_shared_helpers.clamp`, called by `fn:aurora_behavioral_identity.BehavioralIdentityEngine._apply_identity_homeostasis`, `fn:aurora_behavioral_identity.BehavioralIdentityEngine._constraint_axes`, `fn:aurora_behavioral_identity.BehavioralIdentityEngine._identity_floor_ratio`, `fn:aurora_behavioral_identity.BehavioralIdentityEngine._pressure_axes`
- new: `fn:aurora_praxis_bridge.PraxisBridge.rebind_systems`, called by `fn:aurora_praxis_bridge.start_praxis_bridge`, `fn:tests.test_praxis_shared_state_and_discovery.test_rebind_with_the_same_dict_changes_nothing`
- new: `fn:aurora_representational_resolution.RepresentationalResolutionEngine.record_participation`, called by `fn:aurora_representational_resolution.record_ref_participation_from_scores`, `fn:tests.test_habitat_discovery_canary_build717.test_habitat_discovery_canary_fails_on_samples_alone_no_genuine_learning`, `fn:tests.test_habitat_motivation_build717.test_earned_resolution_genuinely_increases_relevance_after_being_earned`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_actions`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_answer`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_bridge`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_chain`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_code_autoevolve`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_code_finalize`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_code_ops`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_code_pressure`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_code_simulate`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_code_stage`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_code_status`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_conflict`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_custom`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_episode`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_epoch`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_evolution`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_help`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_inject`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_learned`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_links`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_pressure`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_quit`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_register`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_save`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_status`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_tick`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:aurora_runtime.RuntimeCLI._cmd_uptime`, called by `fn:aurora_runtime.RuntimeCLI._dispatch`
- new: `fn:scripts.aurora_fault_instrumentation_injector._bind_line`, called by `fn:scripts.aurora_fault_instrumentation_injector._insert_import`
- new: `fn:tests.test_cognition_gap_wiring._curiosity_contexts`, called by `fn:tests.test_cognition_gap_wiring.test_engine_loops_form_the_curiosity_process`, `fn:tests.test_cognition_gap_wiring.test_no_curiosity_process_without_open_loops`
- new: `fn:tests.test_cognition_gap_wiring._engine`, called by `fn:tests.test_cognition_gap_wiring.test_engine_loops_form_the_curiosity_process`, `fn:tests.test_cognition_gap_wiring.test_no_curiosity_process_without_open_loops`, `fn:tests.test_cognition_gap_wiring.test_open_curiosity_loops_is_a_snapshot_the_engine_still_owns`, `fn:tests.test_cognition_gap_wiring.test_registered_gap_is_the_dict_the_curiosity_engine_reads`
- new: `fn:tests.test_cognition_gap_wiring._string_keys_read_from_systems`, called by `fn:tests.test_cognition_gap_wiring.test_aurora_reads_the_noncomp_slot_its_writer_fills`
- new: `fn:tests.test_cognition_gap_wiring.ab`, no static caller
- new: `fn:tests.test_cognition_gap_wiring.test_aurora_reads_the_noncomp_slot_its_writer_fills`, no static caller
- new: `fn:tests.test_cognition_gap_wiring.test_engine_loops_form_the_curiosity_process`, no static caller
- new: `fn:tests.test_cognition_gap_wiring.test_no_curiosity_process_without_open_loops`, no static caller
- new: `fn:tests.test_cognition_gap_wiring.test_open_curiosity_loops_is_a_snapshot_the_engine_still_owns`, no static caller
- new: `fn:tests.test_cognition_gap_wiring.test_registered_gap_is_the_dict_the_curiosity_engine_reads`, no static caller
- new: `fn:tests.test_perspective_merge_repair._fresh`, called by `fn:tests.test_perspective_merge_repair.test_episode_end_hooks_do_not_raise`, `fn:tests.test_perspective_merge_repair.test_observation_never_stages_and_restores_the_hold`, `fn:tests.test_perspective_merge_repair.test_projection_event_records_the_staged_candidate`
- new: `fn:tests.test_perspective_merge_repair.test_duplicate_projected_views_keep_one_cheapest_lens`, no static caller
- new: `fn:tests.test_perspective_merge_repair.test_episode_end_hooks_do_not_raise`, no static caller
- new: `fn:tests.test_perspective_merge_repair.test_observation_never_stages_and_restores_the_hold`, no static caller
- new: `fn:tests.test_perspective_merge_repair.test_observer_and_consumer_are_separate_methods_again`, no static caller
- new: `fn:tests.test_perspective_merge_repair.test_projection_event_records_the_staged_candidate`, no static caller
- new: `fn:tests.test_pf3_1_cooccurrence_hub_leak._run`, called by `fn:tests.test_pf3_1_cooccurrence_hub_leak.test_cooccurrence_relations_excluded_from_context_enrichment`, `fn:tests.test_pf3_1_cooccurrence_hub_leak.test_mixed_relations_keep_only_non_cooccurrence`, `fn:tests.test_pf3_1_cooccurrence_hub_leak.test_non_cooccurrence_relations_still_enrich_context`
- new: `fn:tests.test_praxis_shared_state_and_discovery._FakeGateway.__init__`, no static caller
- new: `fn:tests.test_praxis_shared_state_and_discovery._FakeGateway.receive`, no static caller
- new: `fn:tests.test_praxis_shared_state_and_discovery._organism`, called by `fn:tests.test_praxis_shared_state_and_discovery.test_a_read_only_mapping_is_still_copied_so_the_bridge_can_write`, `fn:tests.test_praxis_shared_state_and_discovery.test_discovery_does_not_wait_for_an_idle_field_but_the_pull_does`, `fn:tests.test_praxis_shared_state_and_discovery.test_loop_still_pulls_with_the_real_field_lock_predicate`, `fn:tests.test_praxis_shared_state_and_discovery.test_pause_still_stops_discovery`
- new: `fn:tests.test_praxis_shared_state_and_discovery._server`, called by `fn:tests.test_praxis_shared_state_and_discovery.test_discovery_does_not_wait_for_an_idle_field_but_the_pull_does`, `fn:tests.test_praxis_shared_state_and_discovery.test_loop_still_pulls_with_the_real_field_lock_predicate`, `fn:tests.test_praxis_shared_state_and_discovery.test_pause_still_stops_discovery`
- new: `fn:tests.test_praxis_shared_state_and_discovery._server._request`, no static caller
- new: `fn:tests.test_praxis_shared_state_and_discovery._situation`, called by `fn:tests.test_praxis_shared_state_and_discovery._server._request`, `fn:tests.test_praxis_shared_state_and_discovery.test_second_boot_rebinds_the_running_bridge_to_the_new_organism`, `fn:tests.test_praxis_shared_state_and_discovery.test_witnessed_context_lands_in_her_own_systems_dict`
- new: `fn:tests.test_praxis_shared_state_and_discovery.test_a_read_only_mapping_is_still_copied_so_the_bridge_can_write`, no static caller
- new: `fn:tests.test_praxis_shared_state_and_discovery.test_discovery_does_not_wait_for_an_idle_field_but_the_pull_does`, no static caller
- new: `fn:tests.test_praxis_shared_state_and_discovery.test_loop_still_pulls_with_the_real_field_lock_predicate`, no static caller
- new: `fn:tests.test_praxis_shared_state_and_discovery.test_pause_still_stops_discovery`, no static caller
- new: `fn:tests.test_praxis_shared_state_and_discovery.test_rebind_with_the_same_dict_changes_nothing`, no static caller
- new: `fn:tests.test_praxis_shared_state_and_discovery.test_second_boot_rebinds_the_running_bridge_to_the_new_organism`, no static caller
- new: `fn:tests.test_praxis_shared_state_and_discovery.test_witnessed_context_lands_in_her_own_systems_dict`, no static caller
- new: `fn:tests.test_undefined_names_in_live_paths._undefined_names`, called by `fn:tests.test_undefined_names_in_live_paths.test_no_new_undefined_names`
- new: `fn:tests.test_undefined_names_in_live_paths.test_comprehension_lookup_derives_its_own_prompt_text`, no static caller
- new: `fn:tests.test_undefined_names_in_live_paths.test_no_new_undefined_names`, no static caller
- new: `fn:tests.test_undefined_names_in_live_paths.test_phone_habitat_reset_answers_when_no_habitat`, no static caller
- new: `fn:tests.test_undefined_names_in_live_paths.test_phone_habitat_reset_reports_success`, no static caller
- new: `fn:tests.test_undefined_names_in_live_paths.test_phone_habitat_reset_reports_success._Habitat.reset`, no static caller

## 2. Relationships: consolidated against lost

2263 relationships of base are not in head (structure and documentation edges left out). 150 are consolidated: the same source still reaches the same target through a helper within two calls. 313 are retargeted: the old target is gone and the source now calls one of the same name (a shared helper). 1277 are delegated: the source's module binds a helper at import time that still reaches the old target, a path static resolution does not follow into the closure. 73 belonged to a function that was folded into a shared one (the shared body no longer names those fields or targets one by one). 214 were seen only in the base run and not in the head run, which is a difference between recordings, not code. 98 went with code that was removed. 138 are lost: the source still exists and no longer reaches the target by any of those routes. 1202 relationships are new.

### Retargeted: 313

- 189 FEEDS to `clamp` now through `fn:aurora_internal.aurora_shared_helpers.clamp`
- 113 CALLS to `clamp` now through `fn:aurora_internal.aurora_shared_helpers.clamp`
- 6 CALLS to `from_dict` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.from_dict`
- 5 FEEDS to `from_dict` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.from_dict`

### Delegated through a module binding: 1277

- 920 CALLS to `record_exception_from_locals` now through `fn:aurora_internal.aurora_runtime_faults.bind_fault_recorder`
- 133 CALLS to `record_exception_from_locals` now through `fn:aurora._aurora_make_override`
- 71 CALLS to `record_exception_from_locals` now through `fn:aurora_daemon.main`
- 61 CALLS to `record_exception_from_locals` now through `fn:aurora_hardware_io.detect_platform`
- 28 CALLS to `record_exception_from_locals` now through `fn:aurora_expression_perception._aurora_make_override`
- 17 CALLS to `record_exception_from_locals` now through `fn:aurora_dimensional_systems._aurora_make_override`
- 6 CALLS to `record_exception_from_locals` now through `fn:aurora_governance_persistence_gateway._aurora_bind_owner_attribute`
- 6 CALLS to `record_exception_from_locals` now through `fn:aurora_consciousness_engine.ConsciousnessEngine.process`
- 5 CALLS to `record_exception_from_locals` now through `fn:aurora_diag.main`
- 5 CALLS to `record_exception_from_locals` now through `fn:aurora_internal.aurora_evolution_chamber._aurora_make_override`
- 4 CALLS to `record_exception_from_locals` now through `fn:aurora_internal.aurora_code_evolution_chamber._aurora_bind_owner_attribute`
- 3 CALLS to `record_exception_from_locals` now through `fn:aurora_behavioral_identity.verify_layer6`
- 2 CALLS to `record_exception_from_locals` now through `fn:aurora_explore.main`
- 2 CALLS to `record_exception_from_locals` now through `fn:aurora_experiential_sim.run_sim`
- 2 CALLS to `record_exception_from_locals` now through `fn:aurora_internal.aurora_energy_layer_costs._aurora_make_override`
- 2 CALLS to `record_exception_from_locals` now through `fn:aurora_internal.aurora_intake_metabolism._aurora_make_override`
- 1 CALLS to `record_exception_from_locals` now through `fn:aurora_internal.aurora_cost_diff_score._aurora_make_override`
- 1 CALLS to `record_exception_from_locals` now through `fn:aurora_internal.aurora_entropy_detector._aurora_make_override`
- 1 CALLS to `record_exception_from_locals` now through `fn:aurora_internal.aurora_noncomp_registry._aurora_make_override`
- 1 CALLS to `projection_consequence` now through `cls:aurora_representational_resolution.RepresentationalResolutionEngine`
- 1 CALLS to `record_exception_from_locals` now through `fn:aurora_internal.aurora_primitive_extractor._aurora_make_override`
- 1 CALLS to `record_exception_from_locals` now through `fn:aurora.boot_aurora`
- 1 CALLS to `investigate_if_pressured` now through `cls:aurora_representational_resolution.RepresentationalResolutionEngine`
- 1 CALLS to `record_exception_from_locals` now through `fn:aurora_internal.aurora_leverage_scalar._aurora_make_override`
- 1 CALLS to `projection_event` now through `cls:aurora_representational_resolution.RepresentationalResolutionEngine`
- 1 CALLS to `record_exception_from_locals` now through `fn:aurora_internal.aurora_polarity_gradient._aurora_make_override`

### Folded into a shared function: 73

- 28 FEEDS to `to_dict` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 2 READS to `created_at` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `projected_accuracy` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `child_id` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `study_cycles_used` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `observation_count` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `status` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `A` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `to_variant_id` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `parent_order` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `edge_id` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `topic` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `entry_hash` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `contradiction_id` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `from_variant_id` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `outcome_negative` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `parent_id` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `last_seen` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `child_order` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `transition_type` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `source_b` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `T` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `files_read` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `outcome_positive` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `claim_a` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `inquiries_used` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `date` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `committed_at` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `claim_b` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`
- 1 READS to `first_seen` now through `fn:aurora_internal.aurora_shared_helpers.DictRecord.to_dict`

### Seen only in the base run: 214

- 5 CALLS to `to_dict` now through ``
- 3 CALLS to `get_stats` now through ``
- 3 CALLS to `strengthen` now through ``
- 2 CALLS to `activation` now through ``
- 2 CALLS to `is_identity_question` now through ``
- 2 CALLS to `attach_live_response_simulation_bridge` now through ``
- 2 CALLS to `coherence_index` now through ``
- 2 CALLS to `load` now through ``
- 2 CALLS to `looks_like_correction` now through ``
- 2 CALLS to `constraint_axes` now through ``
- 2 CALLS to `warp_params` now through ``
- 2 CALLS to `semantic_coherence` now through ``
- 2 CALLS to `representation_discrepancy` now through ``
- 1 CALLS to `emit_trace_warp_signals` now through ``
- 1 CALLS to `apply_relief_tolerance` now through ``
- 1 CALLS to `stage_representation_inquiry` now through ``
- 1 CALLS to `recluster` now through ``
- 1 CALLS to `rank_meaning_profiles` now through ``
- 1 CALLS to `classify_domain` now through ``
- 1 CALLS to `extract_live_question_relations` now through ``
- 1 CALLS to `refresh_live_dual_strata_runtime` now through ``
- 1 CALLS to `repair_markers` now through ``
- 1 CALLS to `cluster_maturity` now through ``
- 1 CALLS to `sum_positive_relief` now through ``
- 1 CALLS to `personality_for_spec` now through ``
- 1 CALLS to `contradiction_markers` now through ``
- 1 CALLS to `response_is_grounded` now through ``
- 1 CALLS to `update_state` now through ``
- 1 CALLS to `build_established_strata_evidence` now through ``
- 1 CALLS to `cosine_activation` now through ``

### Lost (review each): IMPORTS 127, FEEDS 9, READS 1, MEMBER_OF 1

- `bus:_open_curiosity_loops` FEEDS `fn:aurora_thought_formation.make_process_context` [base aurora_braid_wiring.py:255]
- `fn:aurora_representational_address.RepresentationalRef.for_c1` FEEDS `fn:aurora_representational_resolution_base.RepresentationalResolutionEngine.record_participation` [base tests/test_habitat_discovery_canary_build717.py:286]
- `fn:aurora_representational_resolution.RepresentationalResolutionEngine.record_pressure_observation` FEEDS `field:aurora_representational_resolution_base.RepresentationalResolutionEngine._active_stage_for_ref` [base aurora_representational_resolution.py:721]
- `fn:aurora_representational_resolution.RepresentationalResolutionEngine.record_pressure_observation` FEEDS `fn:aurora_representational_resolution.RepresentationalResolutionEngine._projection_consequence` [base aurora_representational_resolution.py:739]
- `fn:aurora_representational_resolution.RepresentationalResolutionEngine.record_pressure_observation` FEEDS `fn:aurora_representational_resolution.RepresentationalResolutionEngine._projection_event` [base aurora_representational_resolution.py:741]
- `fn:aurora_representational_resolution.RepresentationalResolutionEngine.record_pressure_observation` FEEDS `fn:aurora_representational_resolution.RepresentationalResolutionEngine.investigate_if_pressured` [base aurora_representational_resolution.py:745]
- `fn:aurora_representational_resolution.get_or_create_engine` FEEDS `fn:aurora_representational_resolution_base.RepresentationalResolutionEngine.record_participation` [base aurora_representational_resolution.py:860]
- `fn:tests.test_habitat_motivation_build717._drive_real_pressure` FEEDS `fn:aurora_representational_resolution_base.RepresentationalResolutionEngine.record_participation` [base tests/test_habitat_motivation_build717.py:381]
- `fn:tests.test_pf3_1_cooccurrence_hub_leak._build_fake_engine` FEEDS `fn:aurora_expression_perception.ExpressionPerceptionEngine._build_expression` [base tests/test_pf3_1_cooccurrence_hub_leak.py:100]
- `mod:aurora-acm.native.aurora_acm_native` IMPORTS `ext:math` [base aurora-acm/native/aurora_acm_native.py:23]
- `mod:aurora_625_pressure_map` IMPORTS `ext:math` [base aurora_625_pressure_map.py:67]
- `mod:aurora_acm_bridge` IMPORTS `ext:os` [base aurora_acm_bridge.py:33]
- `mod:aurora_behavioral_identity` IMPORTS `ext:collections` [base aurora_behavioral_identity.py:37]
- `mod:aurora_braid_wiring` IMPORTS `ext:time` [base aurora_braid_wiring.py:74]
- `mod:aurora_checkpoint` IMPORTS `ext:pathlib` [base aurora_checkpoint.py:29]
- `mod:aurora_closure_basis` IMPORTS `ext:math` [base aurora_closure_basis.py:93]
- `mod:aurora_concept_derivation` IMPORTS `ext:hashlib` [base aurora_concept_derivation.py:53]
- `mod:aurora_concept_derivation` IMPORTS `ext:time` [base aurora_concept_derivation.py:54]
- `mod:aurora_consciousness_engine` IMPORTS `ext:enum` [base aurora_consciousness_engine.py:98]
- `mod:aurora_consciousness_engine` IMPORTS `ext:math` [base aurora_consciousness_engine.py:91]
- `mod:aurora_consciousness_engine` IMPORTS `ext:random` [base aurora_consciousness_engine.py:92]
- `mod:aurora_constraint_engine` IMPORTS `ext:math` [base aurora_constraint_engine.py:13]
- `mod:aurora_constraint_manifold_router` IMPORTS `ext:enum` [base aurora_constraint_manifold_router.py:88]
- `mod:aurora_constraint_manifold_router` IMPORTS `ext:pathlib` [base aurora_constraint_manifold_router.py:89]
- `mod:aurora_desktop_agent` IMPORTS `ext:json` [base aurora_desktop_agent.py:20]
- `mod:aurora_experiential_sim` IMPORTS `ext:json` [base aurora_experiential_sim.py:43]
- `mod:aurora_expression_perception` IMPORTS `ext:enum` [base aurora_expression_perception.py:46]
- `mod:aurora_expression_perception` IMPORTS `ext:shutil` [base aurora_expression_perception.py:39]
- `mod:aurora_genealogy_environment` IMPORTS `ext:os` [base aurora_genealogy_environment.py:97]
- `mod:aurora_governance_persistence_gateway` IMPORTS `ext:pickle` [base aurora_governance_persistence_gateway.py:49]
- `mod:aurora_hardware_io` IMPORTS `ext:math` [base aurora_hardware_io.py:1257]
- `mod:aurora_i_state_beings` IMPORTS `ext:enum` [base aurora_i_state_beings.py:89]
- `mod:aurora_i_state_beings` IMPORTS `ext:hashlib` [base aurora_i_state_beings.py:85]
- `mod:aurora_i_state_beings` IMPORTS `ext:math` [base aurora_i_state_beings.py:84]
- `mod:aurora_image_ingestion` IMPORTS `ext:dataclasses` [base aurora_image_ingestion.py:55]
- `mod:aurora_image_ingestion` IMPORTS `ext:math` [base aurora_image_ingestion.py:35]
- `mod:aurora_internal.aurora_attention_engine` IMPORTS `ext:math` [base aurora_internal/aurora_attention_engine.py:41]
- `mod:aurora_internal.aurora_capability_assimilator` IMPORTS `ext:hashlib` [base aurora_internal/aurora_capability_assimilator.py:39]
- `mod:aurora_internal.aurora_capability_assimilator` IMPORTS `ext:time` [base aurora_internal/aurora_capability_assimilator.py:42]
- `mod:aurora_internal.aurora_conversation_episode_compiler` IMPORTS `ext:math` [base aurora_internal/aurora_conversation_episode_compiler.py:22]
- `mod:aurora_internal.aurora_conversation_rubric_engine` IMPORTS `ext:hashlib` [base aurora_internal/aurora_conversation_rubric_engine.py:22]
- `mod:aurora_internal.aurora_corpus_lifecycle` IMPORTS `ext:os` [base aurora_internal/aurora_corpus_lifecycle.py:17]
- `mod:aurora_internal.aurora_corpus_lifecycle` IMPORTS `ext:re` [base aurora_internal/aurora_corpus_lifecycle.py:18]
- `mod:aurora_internal.aurora_difference_buffer` IMPORTS `ext:math` [base aurora_internal/aurora_difference_buffer.py:83]
- `mod:aurora_internal.aurora_directed_training_corpus` IMPORTS `ext:random` [base aurora_internal/aurora_directed_training_corpus.py:19]
- `mod:aurora_internal.aurora_dna_strand_schema` IMPORTS `ext:math` [base aurora_internal/aurora_dna_strand_schema.py:62]
- `mod:aurora_internal.aurora_dna_strand_schema` IMPORTS `ext:time` [base aurora_internal/aurora_dna_strand_schema.py:63]
- `mod:aurora_internal.aurora_dream_curriculum_queue` IMPORTS `ext:random` [base aurora_internal/aurora_dream_curriculum_queue.py:27]
- `mod:aurora_internal.aurora_dream_evolution_orchestrator` IMPORTS `ext:json` [base aurora_internal/aurora_dream_evolution_orchestrator.py:25]
- `mod:aurora_internal.aurora_dream_genealogy_bridge` IMPORTS `ext:math` [base aurora_internal/aurora_dream_genealogy_bridge.py:36]
- `mod:aurora_internal.aurora_general_execution_foundry` IMPORTS `ext:queue` [base aurora_internal/aurora_general_execution_foundry.py:45]
- `mod:aurora_internal.aurora_intake_metabolism` IMPORTS `ext:math` [base aurora_internal/aurora_intake_metabolism.py:95]
- `mod:aurora_internal.aurora_learning_pipeline` IMPORTS `ext:math` [base aurora_internal/aurora_learning_pipeline.py:21]
- `mod:aurora_internal.aurora_leverage_relief` IMPORTS `ext:collections` [base aurora_internal/aurora_leverage_relief.py:51]
- `mod:aurora_internal.aurora_operator_composer` IMPORTS `ext:time` [base aurora_internal/aurora_operator_composer.py:57]
- `mod:aurora_internal.aurora_proposition_substrate` IMPORTS `ext:re` [base aurora_internal/aurora_proposition_substrate.py:18]
- `mod:aurora_internal.aurora_quasiarch_observer` IMPORTS `ext:re` [base aurora_internal/aurora_quasiarch_observer.py:16]
- `mod:aurora_internal.aurora_relational_comparison` IMPORTS `ext:math` [base aurora_internal/aurora_relational_comparison.py:21]
- `mod:aurora_internal.aurora_solidification` IMPORTS `ext:enum` [base aurora_internal/aurora_solidification.py:65]
- `mod:aurora_internal.aurora_solidification` IMPORTS `ext:math` [base aurora_internal/aurora_solidification.py:61]
- `mod:aurora_internal.aurora_solidification` IMPORTS `ext:time` [base aurora_internal/aurora_solidification.py:62]
- `mod:aurora_internal.aurora_tensor_expressions` IMPORTS `ext:math` [base aurora_internal/aurora_tensor_expressions.py:58]
- `mod:aurora_internal.constraint_genealogy` IMPORTS `ext:enum` [base aurora_internal/constraint_genealogy.py:44]
- `mod:aurora_internal.dual_strata.activation_field` IMPORTS `ext:collections` [base aurora_internal/dual_strata/activation_field.py:27]
- `mod:aurora_internal.dual_strata.strata_state_transfer` IMPORTS `ext:time` [base aurora_internal/dual_strata/strata_state_transfer.py:36]
- `mod:aurora_internal.dual_strata.topological_semantic_coordinator` IMPORTS `ext:pathlib` [base aurora_internal/dual_strata/topological_semantic_coordinator.py:76]
- `mod:aurora_internal.scouting.backends` IMPORTS `ext:subprocess` [base aurora_internal/scouting/backends.py:31]
- `mod:aurora_learning_report` IMPORTS `ext:math` [base aurora_learning_report.py:22]
- `mod:aurora_live_vision` IMPORTS `ext:hashlib` [base aurora_live_vision.py:28]
- `mod:aurora_live_vision` IMPORTS `ext:math` [base aurora_live_vision.py:26]
- `mod:aurora_manifold_directory.noncomp_field` IMPORTS `ext:math` [base aurora_manifold_directory/noncomp_field.py:28]
- `mod:aurora_quantum_dream_substrate` IMPORTS `ext:math` [base aurora_quantum_dream_substrate.py:45]
- `mod:aurora_response_teacher` IMPORTS `ext:time` [base aurora_response_teacher.py:41]
- `mod:aurora_scout_daemon` IMPORTS `ext:json` [base aurora_scout_daemon.py:14]
- `mod:aurora_sedimemory` IMPORTS `ext:math` [base aurora_sedimemory.py:83]
- `mod:aurora_self_grounding` IMPORTS `ext:time` [base aurora_self_grounding.py:19]
- `mod:aurora_thought_formation` IMPORTS `ext:json` [base aurora_thought_formation.py:43]
- `mod:aurora_vision_clustering` IMPORTS `ext:collections` [base aurora_vision_clustering.py:45]
- `mod:aurora_vision_clustering` IMPORTS `ext:json` [base aurora_vision_clustering.py:33]
- `mod:aurora_vision_clustering` IMPORTS `ext:os` [base aurora_vision_clustering.py:32]
- `mod:aurora_vision_clustering` IMPORTS `ext:pathlib` [base aurora_vision_clustering.py:44]
- `mod:aurora_vision_clustering` IMPORTS `ext:threading` [base aurora_vision_clustering.py:38]
- `mod:aurora_working_memory` IMPORTS `ext:dataclasses` [base aurora_working_memory.py:22]
- `mod:run_aurora` IMPORTS `ext:os` [base run_aurora.py:3]
- `mod:run_intensive_intervals` IMPORTS `ext:os` [base run_intensive_intervals.py:7]
- `mod:run_intensive_intervals` IMPORTS `ext:time` [base run_intensive_intervals.py:6]
- `mod:scripts.append_to_doc` IMPORTS `ext:os` [base scripts/append_to_doc.py:3]
- `mod:scripts.aurora_state_compress` IMPORTS `ext:os` [base scripts/aurora_state_compress.py:10]
- `mod:scripts.chat_daemon` IMPORTS `ext:os` [base scripts/chat_daemon.py:3]
- `mod:scripts.noncomp_actuation_shadow_audit` IMPORTS `ext:os` [base scripts/noncomp_actuation_shadow_audit.py:20]
- `mod:scripts.prove_learning` IMPORTS `ext:os` [base scripts/prove_learning.py:36]
- `mod:scripts.prove_learning` IMPORTS `ext:textwrap` [base scripts/prove_learning.py:40]
- `mod:scripts.source_conversation_corpora` IMPORTS `ext:gzip` [base scripts/source_conversation_corpora.py:13]
- `mod:tests._engine_integration_test` IMPORTS `ext:math` [base tests/_engine_integration_test.py:9]
- `mod:tests._pipeline_test` IMPORTS `ext:math` [base tests/_pipeline_test.py:16]
- `mod:tests.test_build714_resolution_canaries` IMPORTS `ext:pathlib` [base tests/test_build714_resolution_canaries.py:5]
- `mod:tests.test_build714_resolution_canaries` IMPORTS `ext:tempfile` [base tests/test_build714_resolution_canaries.py:4]
- `mod:tests.test_classroom_behavior_modes_wiring` IMPORTS `ext:time` [base tests/test_classroom_behavior_modes_wiring.py:19]
- `mod:tests.test_comm_credit_phase_g_live_wiring` IMPORTS `ext:json` [base tests/test_comm_credit_phase_g_live_wiring.py:35]
- `mod:tests.test_composer_relevance_selection` IMPORTS `ext:math` [base tests/test_composer_relevance_selection.py:10]
- `mod:tests.test_crystal_weave` IMPORTS `ext:ast` [base tests/test_crystal_weave.py:3]
- `mod:tests.test_d2_3_delivery_boundary_telemetry_rejection` IMPORTS `ext:tempfile` [base tests/test_d2_3_delivery_boundary_telemetry_rejection.py:19]
- `mod:tests.test_daemon_evidence_grounded_mutation` IMPORTS `ext:textwrap` [base tests/test_daemon_evidence_grounded_mutation.py:22]
- `mod:tests.test_evolution_chamber_live_driveshaft` IMPORTS `ext:time` [base tests/test_evolution_chamber_live_driveshaft.py:28]
- `mod:tests.test_fault_instrumentation_injector` IMPORTS `ext:tempfile` [base tests/test_fault_instrumentation_injector.py:23]
- `mod:tests.test_full_reasoning_pipeline` IMPORTS `ext:time` [base tests/test_full_reasoning_pipeline.py:13]
- `mod:tests.test_genealogy_is_event_generated` IMPORTS `ext:types` [base tests/test_genealogy_is_event_generated.py:11]
- `mod:tests.test_habitat_discovery_canary_build717` IMPORTS `ext:tempfile` [base tests/test_habitat_discovery_canary_build717.py:81]
- `mod:tests.test_habitat_motivation_build717` IMPORTS `ext:tempfile` [base tests/test_habitat_motivation_build717.py:25]
- `mod:tests.test_habitat_self_and_shared_canaries_build717` IMPORTS `ext:time` [base tests/test_habitat_self_and_shared_canaries_build717.py:20]
- `mod:tests.test_historical_lexical_consequence_attribution` IMPORTS `ext:tempfile` [base tests/test_historical_lexical_consequence_attribution.py:26]
- `mod:tests.test_icc_ledger` IMPORTS `ext:os` [base tests/test_icc_ledger.py:15]
- `mod:tests.test_input_effect_shadow` IMPORTS `ext:copy` [base tests/test_input_effect_shadow.py:5]
- `mod:tests.test_live_possibility_king_authority` IMPORTS `ext:types` [base tests/test_live_possibility_king_authority.py:4]
- `mod:tests.test_mobile_tools_aurora` IMPORTS `ext:os` [base tests/test_mobile_tools_aurora.py:4]
- `mod:tests.test_mobile_tools_aurora` IMPORTS `ext:pathlib` [base tests/test_mobile_tools_aurora.py:5]
- `mod:tests.test_mtsl_acceptance_report` IMPORTS `ext:json` [base tests/test_mtsl_acceptance_report.py:11]
- `mod:tests.test_mtsl_live_wiring` IMPORTS `ext:tempfile` [base tests/test_mtsl_live_wiring.py:12]
- `mod:tests.test_perspective_representation_birth` IMPORTS `ext:pathlib` [base tests/test_perspective_representation_birth.py:23]
- `mod:tests.test_perspective_representation_birth` IMPORTS `ext:time` [base tests/test_perspective_representation_birth.py:22]
- `mod:tests.test_pipeline2` IMPORTS `ext:json` [base tests/test_pipeline2.py:3]
- `mod:tests.test_recommendation_hub_incremental` IMPORTS `ext:os` [base tests/test_recommendation_hub_incremental.py:8]
- `mod:tests.test_reflective_introspection_misrouting_live` IMPORTS `ext:hashlib` [base tests/test_reflective_introspection_misrouting_live.py:16]
- `mod:tests.test_reflective_readdressing` IMPORTS `ext:types` [base tests/test_reflective_readdressing.py:3]
- `mod:tests.test_representational_persistence` IMPORTS `ext:tempfile` [base tests/test_representational_persistence.py:15]
- `mod:tests.test_representational_resolution_build714` IMPORTS `ext:json` [base tests/test_representational_resolution_build714.py:17]
- `mod:tests.test_representational_resolution_build714` IMPORTS `ext:os` [base tests/test_representational_resolution_build714.py:18]
- `mod:tests.test_representational_resolution_build714` IMPORTS `ext:tempfile` [base tests/test_representational_resolution_build714.py:20]
- `mod:tests.test_response_formation_consumes_scout_evidence` IMPORTS `ext:types` [base tests/test_response_formation_consumes_scout_evidence.py:4]
- `mod:tests.test_round` IMPORTS `ext:json` [base tests/test_round.py:3]
- `mod:tests.test_sender_agency` IMPORTS `ext:types` [base tests/test_sender_agency.py:12]
- `mod:tests.test_surface_boundary` IMPORTS `ext:os` [base tests/test_surface_boundary.py:11]
- `mod:tests.test_surface_boundary` IMPORTS `ext:types` [base tests/test_surface_boundary.py:12]
- `mod:tests.test_system_introspection_bridge` IMPORTS `ext:types` [base tests/test_system_introspection_bridge.py:2]
- `mod:tests.test_universal_function_lineage_freshness_fast_path` IMPORTS `ext:shutil` [base tests/test_universal_function_lineage_freshness_fast_path.py:26]
- `mod:tests.test_universal_function_lineage_freshness_fast_path` IMPORTS `ext:tempfile` [base tests/test_universal_function_lineage_freshness_fast_path.py:28]
- `mod:reply_aurora` MEMBER_OF `subsys:category:runtime` [base docs/module_ownership.json:0]
- `fn:aurora._run_live_response_turn` READS `bus:_noncomp_output` [base aurora.py:35899]

### Removed with deleted code: FEEDS 98

- `field:aurora_internal.aurora_correspondence_loop.CommittedPrediction.committed_at` FEEDS `fn:aurora_internal.aurora_correspondence_loop.CommittedPrediction.to_dict` [base aurora_internal/aurora_correspondence_loop.py:220]
- `field:aurora_internal.dual_strata.variant_transition_predictor.TransitionRecord.first_seen` FEEDS `fn:aurora_internal.dual_strata.variant_transition_predictor.TransitionRecord.to_dict` [base aurora_internal/dual_strata/variant_transition_predictor.py:59]
- `field:aurora_internal.quasiarch_observer.dimensional_memory.LineageEdge.child_id` FEEDS `fn:aurora_internal.quasiarch_observer.dimensional_memory.LineageEdge.to_dict` [base aurora_internal/quasiarch_observer/dimensional_memory.py:258]
- `field:aurora_internal.quasiarch_observer.dimensional_memory.LineageEdge.child_order` FEEDS `fn:aurora_internal.quasiarch_observer.dimensional_memory.LineageEdge.to_dict` [base aurora_internal/quasiarch_observer/dimensional_memory.py:258]
- `field:aurora_internal.quasiarch_observer.dimensional_memory.LineageEdge.created_at` FEEDS `fn:aurora_internal.quasiarch_observer.dimensional_memory.LineageEdge.to_dict` [base aurora_internal/quasiarch_observer/dimensional_memory.py:258]
- `field:aurora_internal.quasiarch_observer.dimensional_memory.LineageEdge.parent_id` FEEDS `fn:aurora_internal.quasiarch_observer.dimensional_memory.LineageEdge.to_dict` [base aurora_internal/quasiarch_observer/dimensional_memory.py:258]
- `field:aurora_internal.quasiarch_observer.dimensional_memory.LineageEdge.parent_order` FEEDS `fn:aurora_internal.quasiarch_observer.dimensional_memory.LineageEdge.to_dict` [base aurora_internal/quasiarch_observer/dimensional_memory.py:258]
- `field:aurora_internal.quasiarch_observer.dimensional_memory.LineageEdge.transition_type` FEEDS `fn:aurora_internal.quasiarch_observer.dimensional_memory.LineageEdge.to_dict` [base aurora_internal/quasiarch_observer/dimensional_memory.py:258]
- `field:aurora_ivm.ContradictionRecord.claim_a` FEEDS `fn:aurora_ivm.ContradictionRecord.to_dict` [base aurora_ivm.py:2006]
- `field:aurora_ivm.ContradictionRecord.claim_b` FEEDS `fn:aurora_ivm.ContradictionRecord.to_dict` [base aurora_ivm.py:2006]
- `field:aurora_ivm.ContradictionRecord.contradiction_id` FEEDS `fn:aurora_ivm.ContradictionRecord.to_dict` [base aurora_ivm.py:2006]
- `field:aurora_ivm.ContradictionRecord.created_at` FEEDS `fn:aurora_ivm.ContradictionRecord.to_dict` [base aurora_ivm.py:2006]
- `field:aurora_ivm.ContradictionRecord.resolution_note` FEEDS `fn:aurora_ivm.ContradictionRecord.to_dict` [base aurora_ivm.py:2006]
- `field:aurora_ivm.ContradictionRecord.resolved_at` FEEDS `fn:aurora_ivm.ContradictionRecord.to_dict` [base aurora_ivm.py:2006]
- `field:aurora_ivm.ContradictionRecord.source_a` FEEDS `fn:aurora_ivm.ContradictionRecord.to_dict` [base aurora_ivm.py:2006]
- `field:aurora_ivm.ContradictionRecord.source_b` FEEDS `fn:aurora_ivm.ContradictionRecord.to_dict` [base aurora_ivm.py:2006]
- `field:aurora_ivm.ContradictionRecord.status` FEEDS `fn:aurora_ivm.ContradictionRecord.to_dict` [base aurora_ivm.py:2006]
- `fn:aurora_behavioral_identity._clamp` FEEDS `field:aurora_behavioral_identity.BehavioralTrait.value` [base aurora_behavioral_identity.py:343]
- `fn:aurora_behavioral_identity._clamp` FEEDS `field:aurora_behavioral_identity.EvolvingTrait.current_value` [base aurora_behavioral_identity.py:306]
- `fn:aurora_behavioral_identity._clamp` FEEDS `fn:aurora_behavioral_identity.BehavioralIdentityEngine._constraint_axes` [base aurora_behavioral_identity.py:1424]
- `fn:aurora_behavioral_identity._clamp` FEEDS `fn:aurora_behavioral_identity.BehavioralIdentityEngine._identity_floor_ratio` [base aurora_behavioral_identity.py:952]
- `fn:aurora_behavioral_identity._clamp` FEEDS `fn:aurora_behavioral_identity.BehavioralIdentityEngine._pressure_axes` [base aurora_behavioral_identity.py:1440]
- `fn:aurora_behavioral_identity._clamp` FEEDS `fn:aurora_behavioral_identity.BehavioralTrait.simulate` [base aurora_behavioral_identity.py:338]
- `fn:aurora_behavioral_identity._clamp` FEEDS `fn:aurora_behavioral_identity.DNASystem.create_allele_from_experience` [base aurora_behavioral_identity.py:1346]
- `fn:aurora_checkpoint.CorpusCursor.from_dict` FEEDS `field:aurora_checkpoint.CheckpointManager.cursor` [base aurora_checkpoint.py:324]
- `fn:aurora_checkpoint.RollingStats.from_dict` FEEDS `field:aurora_checkpoint.CheckpointManager.stats` [base aurora_checkpoint.py:325]
- `fn:aurora_expression_perception._clamp` FEEDS `field:aurora_expression_perception.RhythmSignature.rhythm_score` [base aurora_expression_perception.py:1533]
- `fn:aurora_expression_perception._clamp` FEEDS `field:aurora_expression_perception.VoiceGenome.breathiness` [base aurora_expression_perception.py:1688]
- `fn:aurora_expression_perception._clamp` FEEDS `field:aurora_expression_perception.VoiceGenome.formality` [base aurora_expression_perception.py:1689]
- `fn:aurora_expression_perception._clamp` FEEDS `field:aurora_expression_perception.VoiceGenome.pace` [base aurora_expression_perception.py:1685]
- `fn:aurora_expression_perception._clamp` FEEDS `field:aurora_expression_perception.VoiceGenome.pitch_base` [base aurora_expression_perception.py:1686]
- `fn:aurora_expression_perception._clamp` FEEDS `field:aurora_expression_perception.VoiceGenome.pitch_range` [base aurora_expression_perception.py:1687]
- `fn:aurora_expression_perception._clamp` FEEDS `field:aurora_expression_perception.VoiceGenome.warmth` [base aurora_expression_perception.py:1684]
- `fn:aurora_expression_perception._clamp` FEEDS `fn:aurora_expression_perception.ExpressionPressure.evaluate` [base aurora_expression_perception.py:1654]
- `fn:aurora_expression_perception._clamp` FEEDS `fn:aurora_expression_perception.ImpressionCascade._seed_shard_similarity` [base aurora_expression_perception.py:1114]
- `fn:aurora_expression_perception._clamp` FEEDS `fn:aurora_expression_perception.ManifoldEngine.novelty_at` [base aurora_expression_perception.py:797]
- `fn:aurora_governance_persistence_gateway._clamp` FEEDS `field:aurora_governance_persistence_gateway.ValidationResult.moral_score` [base aurora_governance_persistence_gateway.py:1050]
- `fn:aurora_governance_persistence_gateway._clamp` FEEDS `fn:aurora_governance_persistence_gateway.NSpaceGateway._check_coherence` [base aurora_governance_persistence_gateway.py:1436]
- `fn:aurora_grammar_engine._clamp` FEEDS `fn:aurora_grammar_engine.GrammarEngine.prepare_response_trace` [base aurora_grammar_engine.py:1773]
- `fn:aurora_grammar_engine._clamp` FEEDS `fn:aurora_grammar_engine.GrammarEngine.suggest_structure` [base aurora_grammar_engine.py:1727]
- `fn:aurora_grammar_engine._clamp` FEEDS `fn:aurora_grammar_engine.MotifLineage.best_for_pressure._score` [base aurora_grammar_engine.py:848]
- `fn:aurora_grammar_engine._clamp` FEEDS `fn:aurora_grammar_engine.MotifLineage.best_for_proposition._score` [base aurora_grammar_engine.py:915]
- `fn:aurora_grammar_engine._clamp` FEEDS `fn:aurora_grammar_engine.StructuralMotif.composability_score` [base aurora_grammar_engine.py:393]
- `fn:aurora_grammar_engine._clamp` FEEDS `fn:aurora_internal.aurora_confluence.choose_motif.score` [base aurora_internal/aurora_confluence.py:769]
- `fn:aurora_internal.aurora_braided_substrate._clamp` FEEDS `field:aurora_internal.aurora_braided_substrate.BraidState.heat` [base aurora_internal/aurora_braided_substrate.py:109]
- `fn:aurora_internal.aurora_braided_substrate._clamp` FEEDS `fn:aurora_internal.aurora_braided_substrate.BraidedSubstrateLayer._compute_stability` [base aurora_internal/aurora_braided_substrate.py:268]
- `fn:aurora_internal.aurora_conversation_rubric_engine._clamp` FEEDS `fn:aurora_internal.aurora_conversation_rubric_engine._causal_score` [base aurora_internal/aurora_conversation_rubric_engine.py:148]
- `fn:aurora_internal.aurora_conversation_rubric_engine._clamp` FEEDS `fn:aurora_internal.aurora_conversation_rubric_engine._contradiction_markers` [base aurora_internal/aurora_conversation_rubric_engine.py:247]
- `fn:aurora_internal.aurora_conversation_rubric_engine._clamp` FEEDS `fn:aurora_internal.aurora_conversation_rubric_engine._generic_response_penalty` [base aurora_internal/aurora_conversation_rubric_engine.py:159]
- `fn:aurora_internal.aurora_conversation_rubric_engine._clamp` FEEDS `fn:aurora_internal.aurora_conversation_rubric_engine._hedging_score` [base aurora_internal/aurora_conversation_rubric_engine.py:236]
- `fn:aurora_internal.aurora_conversation_rubric_engine._clamp` FEEDS `fn:aurora_internal.aurora_conversation_rubric_engine._perspective_markers` [base aurora_internal/aurora_conversation_rubric_engine.py:270]
- `fn:aurora_internal.aurora_conversation_rubric_engine._clamp` FEEDS `fn:aurora_internal.aurora_conversation_rubric_engine._repair_markers` [base aurora_internal/aurora_conversation_rubric_engine.py:259]
- `fn:aurora_internal.aurora_language_state._clamp` FEEDS `field:aurora_internal.aurora_language_state.IntentObject.certainty` [base aurora_internal/aurora_language_state.py:601]
- `fn:aurora_internal.aurora_language_state._clamp` FEEDS `field:aurora_internal.aurora_language_state.LanguageStateVector._dims` [base aurora_internal/aurora_language_state.py:231]
- `fn:aurora_internal.aurora_language_state._clamp` FEEDS `field:aurora_internal.aurora_language_state.PhrasePrint.confidence` [base aurora_internal/aurora_language_state.py:2077]
- `fn:aurora_internal.aurora_language_state._clamp` FEEDS `fn:aurora_internal.aurora_language_state.LanguageStateVector._compute_growth` [base aurora_internal/aurora_language_state.py:281]
- `fn:aurora_internal.aurora_language_state._clamp` FEEDS `fn:aurora_internal.aurora_language_state.TemplateEvolutionEngine._response_score` [base aurora_internal/aurora_language_state.py:1830]
- `fn:aurora_internal.aurora_ontological_scaffolding._clamp` FEEDS `field:aurora_internal.aurora_ontological_scaffolding.SemanticNode.comprehension_confidence` [base aurora_internal/aurora_ontological_scaffolding.py:648]
- `fn:aurora_internal.aurora_ontological_scaffolding._clamp` FEEDS `field:aurora_internal.aurora_ontological_scaffolding.SemanticNode.ontological_depth` [base aurora_internal/aurora_ontological_scaffolding.py:626]
- `fn:aurora_internal.aurora_ontological_scaffolding._clamp` FEEDS `field:aurora_internal.aurora_ontological_scaffolding.SemanticNode.research_priority` [base aurora_internal/aurora_ontological_scaffolding.py:680]
- `fn:aurora_internal.aurora_ontological_scaffolding._clamp` FEEDS `fn:aurora_internal.aurora_ontological_scaffolding.ClusterEngine._compute_coherence` [base aurora_internal/aurora_ontological_scaffolding.py:1890]
- `fn:aurora_internal.aurora_ontological_scaffolding._clamp` FEEDS `fn:aurora_internal.aurora_ontological_scaffolding.OntologicalScaffoldingEngine._topic_tracking_score` [base aurora_internal/aurora_ontological_scaffolding.py:2809]
- `fn:aurora_internal.aurora_ontological_scaffolding._clamp` FEEDS `fn:aurora_internal.aurora_ontological_scaffolding.UnderstandingMetrics._coherence_index` [base aurora_internal/aurora_ontological_scaffolding.py:2474]
- `fn:aurora_internal.aurora_ontological_scaffolding._clamp` FEEDS `fn:aurora_internal.aurora_ontological_scaffolding.UnderstandingMetrics._conceptual_density` [base aurora_internal/aurora_ontological_scaffolding.py:2448]
- `fn:aurora_internal.aurora_ontological_scaffolding._clamp` FEEDS `fn:aurora_internal.aurora_ontological_scaffolding.UnderstandingMetrics._contradiction_rate` [base aurora_internal/aurora_ontological_scaffolding.py:2495]
- `fn:aurora_internal.aurora_ontological_scaffolding._clamp` FEEDS `fn:aurora_internal.aurora_ontological_scaffolding.UnderstandingMetrics._grounding_index` [base aurora_internal/aurora_ontological_scaffolding.py:2516]
- `fn:aurora_internal.aurora_ontological_scaffolding._clamp` FEEDS `fn:aurora_internal.aurora_ontological_scaffolding.UnderstandingMetrics._vocabulary_breadth` [base aurora_internal/aurora_ontological_scaffolding.py:2427]
- `fn:aurora_internal.aurora_pressure_mathematics_tracker._clamp` FEEDS `field:aurora_internal.aurora_pressure_mathematics_tracker.PressureMetrics.complexity_ratio` [base aurora_internal/aurora_pressure_mathematics_tracker.py:456]
- `fn:aurora_internal.aurora_pressure_mathematics_tracker._clamp` FEEDS `fn:aurora_internal.aurora_pressure_mathematics_tracker.PressureMathematicsTracker._compute_evolutionary_velocity` [base aurora_internal/aurora_pressure_mathematics_tracker.py:649]
- `fn:aurora_internal.aurora_pressure_mathematics_tracker._clamp` FEEDS `fn:aurora_internal.aurora_pressure_mathematics_tracker.PressureMathematicsTracker._compute_pressure_velocity` [base aurora_internal/aurora_pressure_mathematics_tracker.py:658]
- `fn:aurora_internal.aurora_specialized_avatar_synthesizer._clamp` FEEDS `fn:aurora_internal.aurora_specialized_avatar_synthesizer.SpecializedAvatarSynthesizer._apply_adaptive_policy` [base aurora_internal/aurora_specialized_avatar_synthesizer.py:768]
- `fn:aurora_internal.aurora_specialized_avatar_synthesizer._clamp` FEEDS `fn:aurora_internal.aurora_specialized_avatar_synthesizer._clamp_signed` [base aurora_internal/aurora_specialized_avatar_synthesizer.py:587]
- `fn:aurora_internal.aurora_structural_pressure_steering._clamp` FEEDS `fn:aurora_internal.aurora_structural_pressure_steering.StructuralPressureSteering.apply_to_dpme` [base aurora_internal/aurora_structural_pressure_steering.py:598]
- `fn:aurora_internal.constraint_genealogy._clamp` FEEDS `field:aurora_internal.constraint_genealogy.ConstraintGenealogyLogger._axis_outcome_ema` [base aurora_internal/constraint_genealogy.py:9035]
- `fn:aurora_internal.constraint_genealogy._clamp` FEEDS `field:aurora_internal.constraint_genealogy.ConstraintGenealogyLogger._depth_outcome_ema` [base aurora_internal/constraint_genealogy.py:9039]
- `fn:aurora_internal.constraint_genealogy._clamp` FEEDS `field:aurora_internal.constraint_genealogy.ConstraintGenealogyLogger._gradient_axis_ema` [base aurora_internal/constraint_genealogy.py:8999]
- `fn:aurora_internal.constraint_genealogy._clamp` FEEDS `field:aurora_internal.constraint_genealogy.ConstraintGenealogyLogger._last_promotion_tick` [base aurora_internal/constraint_genealogy.py:2209]
- `fn:aurora_internal.constraint_genealogy._clamp` FEEDS `field:aurora_internal.constraint_genealogy.ConstraintGenealogyLogger._training_plateau_pressure` [base aurora_internal/constraint_genealogy.py:8312]
- `fn:aurora_internal.constraint_genealogy._clamp` FEEDS `field:aurora_internal.constraint_genealogy.GenealogyDilationGovernor._relief_history` [base aurora_internal/constraint_genealogy.py:1687]
- `fn:aurora_internal.constraint_genealogy._clamp` FEEDS `fn:aurora_internal.constraint_genealogy.ConstraintGenealogyLogger._compression_efficiency_for_pair` [base aurora_internal/constraint_genealogy.py:8959]

### Consolidated: CALLS 138, FEEDS 7, READS 3, WRITES 2

- `fn:aurora.AxisProjector.project` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:3646]
- `fn:aurora.TeachingEngine.process_teaching_input` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:579]
- `fn:aurora._answer_from_sedimemory_context` CALLS `fn:aurora._answer_from_sedimemory_context` (ran) [base ?:0]
- `fn:aurora._apply_noncomp_input_guidance` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:13170]
- `fn:aurora._build_comprehension_response` CALLS `fn:aurora._build_comprehension_response` (ran) [base ?:0]
- `fn:aurora._build_comprehension_response` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:26623]
- `fn:aurora._build_established_strata_evidence` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:16952]
- `fn:aurora._build_grounded_fallback_response` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:10184]
- `fn:aurora._build_research_callback._fetch_definition` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:1819]
- `fn:aurora._chain_down1_information` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:21855]
- `fn:aurora._chain_down2_belief` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:21649]
- `fn:aurora._chain_down3_purpose` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:21608]
- `fn:aurora._emit_interpreted_turn_packet` CALLS `fn:aurora._emit_interpreted_turn_packet` (ran) [base ?:0]
- `fn:aurora._full_save` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:38508]
- `fn:aurora._generate_from_manifold` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:20812]
- `fn:aurora._generate_perspective_from_core` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:9213]
- `fn:aurora._ingest_current_turn_scout_evidence` CALLS `fn:aurora._ingest_current_turn_scout_evidence` (ran) [base ?:0]
- `fn:aurora._queue_poedex_representation_followup._worker` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:12801]
- `fn:aurora._refresh_live_dual_strata_runtime` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:17865]
- `fn:aurora._render_runtime_intent` CALLS `fn:aurora._render_runtime_intent` (ran) [base ?:0]
- `fn:aurora._render_runtime_intent` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:7717]
- `fn:aurora._repair_discourse_coherence` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:15445]
- `fn:aurora._repair_unknown_vocabulary_inline` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:13953]
- `fn:aurora._run_live_response_turn` CALLS `fn:aurora._run_live_response_turn` (ran) [base ?:0]
- `fn:aurora._run_live_response_turn` CALLS `fn:aurora_internal.aurora_utterance_parser.UtteranceParser.parse` (ran) [base ?:0]
- `fn:aurora._run_reasoning_pipeline` CALLS `fn:aurora._run_reasoning_pipeline` (ran) [base ?:0]
- `fn:aurora._run_reasoning_pipeline` CALLS `fn:aurora_dimensional_systems.RecallPacket.as_context_fragment` (ran) [base ?:0]
- `fn:aurora._sediment_validated_fact` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:5930]
- `fn:aurora._stage_noncomp_prefetch._prefetch_worker` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:12158]
- `fn:aurora._stage_poedex_learning_request._learning_worker` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:12557]
- `fn:aurora._stage_poedex_representation_request._representation_worker` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:12671]
- `fn:aurora._write_interaction_status` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:6398]
- `fn:aurora.boot_aurora._h_seek` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:29649]
- `fn:aurora.chat` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora.py:38968]
- `fn:aurora_behavioral_identity.BehavioralIdentityEngine._identity_floor_ratio` CALLS `fn:aurora_behavioral_identity.BehavioralIdentityEngine._identity_floor_ratio` (ran) [base ?:0]
- `fn:aurora_behavioral_identity.BehavioralIdentityEngine.evolve_generation` CALLS `fn:aurora_behavioral_identity.EvolvingTrait.drift_from_base` (ran) [base ?:0]
- `fn:aurora_behavioral_identity.BehavioralIdentityEngine.get_personality` CALLS `fn:aurora_behavioral_identity.EvolvingTrait.drift_from_base` (ran) [base ?:0]
- `fn:aurora_braid_wiring.begin_expression` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_braid_wiring.py:816]
- `fn:aurora_braid_wiring.ensure_proposition_frame_for_turn` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_braid_wiring.py:634]
- `fn:aurora_consciousness_engine.ConsciousnessEngine._attach_dual_strata_snapshot` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_consciousness_engine.py:1458]
- `fn:aurora_consciousness_engine.ConsciousnessEngine.tick` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_consciousness_engine.py:2079]
- `fn:aurora_constraint_emission.ConstraintEmitter._topic_signature` CALLS `fn:aurora_constraint_emission.ConstraintEmitter._topic_signature` (ran) [base ?:0]
- `fn:aurora_daemon._maybe_consume_low_resource_evolution_relief` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_daemon.py:2771]
- `fn:aurora_daemon._poedex_deliver_tutorial` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_daemon.py:4235]
- `fn:aurora_daemon._poedex_post_study_scan` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_daemon.py:4268]
- `fn:aurora_daemon._run_dream_burst` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_daemon.py:4965]
- `fn:aurora_daemon._stage_low_resource_evolution_relief` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_daemon.py:2530]
- `fn:aurora_daemon.main` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_daemon.py:10329]
- `fn:aurora_diag._run_prompt` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_diag.py:246]
- `fn:aurora_dimensional_systems.CrystalProcessingSystem.get_recently_active` CALLS `fn:aurora_dimensional_systems.CrystalProcessingSystem.get_recently_active` (ran) [base ?:0]
- `fn:aurora_dimensional_systems.DimensionalSystems._slot_for_concept` CALLS `fn:aurora_dimensional_systems.DimensionalSystems._slot_for_concept` (ran) [base ?:0]
- `fn:aurora_dream_trainer.DreamTrainer._record_fail_dimension` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_dream_trainer.py:3128]
- `fn:aurora_dream_trainer.DreamTrainer._witness_directed_training_samples` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_dream_trainer.py:3312]
- `fn:aurora_dream_trainer.DreamTrainer.audit_chronic_weaknesses` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_dream_trainer.py:3579]
- `fn:aurora_dream_trainer.DreamTrainer.flush_lessons_to_simulation` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_dream_trainer.py:3409]
- `fn:aurora_dream_trainer.DreamTrainer.record_relational_probe_outcomes` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_dream_trainer.py:2985]
- `fn:aurora_dream_trainer.DreamTrainer.record_sensory_tension` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_dream_trainer.py:2617]
- `fn:aurora_explore._run_prompt` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_explore.py:212]
- `fn:aurora_explore.main` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_explore.py:418]
- `fn:aurora_expression_perception.ExpressionPerceptionEngine._build_expression` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_expression_perception.py:5805]
- `fn:aurora_expression_perception.SentenceComposer._compose_from_motif` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_expression_perception.py:3023]
- `fn:aurora_expression_perception.SentenceComposer.compose` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_expression_perception.py:2818]
- `fn:aurora_governance_persistence_gateway.NSpaceGateway._needs_articulation_bridge` CALLS `fn:aurora_governance_persistence_gateway.NSpaceGateway._needs_articulation_bridge` (ran) [base ?:0]
- `fn:aurora_image_ingestion.WebImageDownloader.save_state` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_image_ingestion.py:309]
- `fn:aurora_internal.aurora_evolution_chamber.StructuralProximityMeter.structural_distance` CALLS `fn:aurora_internal.aurora_evolution_chamber.StructuralProximityMeter.structural_distance` (ran) [base ?:0]
- `fn:aurora_internal.aurora_evolution_chamber._select_axis_ability` CALLS `fn:aurora_internal.aurora_evolution_chamber._select_axis_ability` (ran) [base ?:0]
- `fn:aurora_internal.aurora_evolved_surfaces.AuroraEvolvedSurfaceEngine._activation_record` CALLS `fn:aurora_internal.aurora_evolved_surfaces.AuroraEvolvedSurfaceEngine._activation_record` (ran) [base ?:0]
- `fn:aurora_internal.aurora_identity_persistence.OETSPersistence.load_web` CALLS `fn:aurora_internal.aurora_ontological_scaffolding.SemanticRelation.depth_contribution` (ran) [base ?:0]
- `fn:aurora_internal.aurora_lineage_runtime_activation.load_selected_activation_manifests` CALLS `fn:aurora_internal.aurora_lineage_runtime_activation.load_selected_activation_manifests` (ran) [base ?:0]
- `fn:aurora_internal.aurora_manual_code_lineage.ManualCodeLineageAssimilator._file_sha1` CALLS `fn:aurora_internal.aurora_manual_code_lineage.ManualCodeLineageAssimilator._file_sha1` (ran) [base ?:0]
- `fn:aurora_internal.aurora_meaning_evolution._profile` CALLS `fn:aurora_internal.aurora_meaning_evolution._profile` (ran) [base ?:0]
- `fn:aurora_internal.aurora_operator_composer.OperatorComposer._persist` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_internal/aurora_operator_composer.py:421]
- `fn:aurora_internal.aurora_pressure_ledger.PressureExperienceLedger.record` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_internal/aurora_pressure_ledger.py:297]
- `fn:aurora_internal.aurora_proposition_frame._frame_from_claims` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_internal/aurora_proposition_frame.py:462]
- `fn:aurora_internal.aurora_proposition_frame._frame_from_turn_local_claims` CALLS `fn:aurora_internal.aurora_runtime_faults.record_exception_from_locals` [base aurora_internal/aurora_proposition_frame.py:524]
- `fn:aurora_internal.aurora_semantic_probe_battery._parseable` CALLS `fn:aurora_internal.aurora_semantic_probe_battery._parseable` (ran) [base ?:0]
- `fn:aurora_internal.aurora_semantic_probe_battery._sentence_parseable` CALLS `fn:aurora_internal.aurora_semantic_probe_battery._sentence_parseable` (ran) [base ?:0]
- `fn:aurora_internal.aurora_sensory_crystal.AuroraSensoryCrystal._pressure_axes` CALLS `fn:aurora_internal.aurora_sensory_crystal.SensoryClusterFacet.maturity` (ran) [base ?:0]
- `fn:aurora_internal.aurora_surface_doc._semantic_label` CALLS `fn:aurora_internal.aurora_surface_doc._semantic_label` (ran) [base ?:0]
- `fn:aurora_internal.aurora_surface_doc.full_report` CALLS `fn:aurora_internal.aurora_surface_doc.full_report` (ran) [base ?:0]

## 2b. Composites promoted on evidence

52 in base, 53 in head. Each base composite is matched to the head composite sharing the most files; a composite that splits, loses files or disappears means the binding between those files changed.

- `subsys:composite:governance:01effd21` (17 files) -> `subsys:composite:governance:2753c48b` (overlap 0.59); left: `aurora_dev_telemetry.py`, `aurora_internal/aurora_identity_persistence.py`, `aurora_internal/aurora_leverage_relief.py`, `aurora_internal/aurora_persistence_audit.py`, `aurora_internal/aurora_runtime_constraint_governor.py`, `aurora_metabolic_distiller.py`

## 3. Stored state

Stores named only in base: none.  
Stores named only in head: none.

No store changed writers or readers.

Stored-state keys inside those files are not parsed from code, so a renamed JSON key inside an unchanged store needs the lost FEEDS and Field edges above, or a reading of the diff, to show.

## 4. Fault references

FIX citations in code: 344 in base, 345 in head.
Fault and error handling nodes: 385 in base, 388 in head; gone: none; new: `fn:aurora_internal.aurora_runtime_faults.bind_fault_recorder`, `fn:aurora_internal.aurora_runtime_faults.bind_fault_recorder._aurora_fault`, `fn:scripts.aurora_fault_instrumentation_injector._bind_line`.

## 5. Developmental records

60 stores look like lineage, evolution, development or history records by name.
None changed writers or readers.

## 6. Dependencies between modules

- import gone: `mod:aurora-acm.native.aurora_acm_native` -> `ext:math`
- import gone: `mod:aurora_625_pressure_map` -> `ext:math`
- import gone: `mod:aurora_acm_bridge` -> `ext:os`
- import gone: `mod:aurora_behavioral_identity` -> `ext:collections`
- import gone: `mod:aurora_braid_wiring` -> `ext:time`
- import gone: `mod:aurora_checkpoint` -> `ext:pathlib`
- import gone: `mod:aurora_closure_basis` -> `ext:math`
- import gone: `mod:aurora_concept_derivation` -> `ext:hashlib`
- import gone: `mod:aurora_concept_derivation` -> `ext:time`
- import gone: `mod:aurora_consciousness_engine` -> `ext:enum`
- import gone: `mod:aurora_consciousness_engine` -> `ext:math`
- import gone: `mod:aurora_consciousness_engine` -> `ext:random`
- import gone: `mod:aurora_constraint_engine` -> `ext:math`
- import gone: `mod:aurora_constraint_manifold_router` -> `ext:enum`
- import gone: `mod:aurora_constraint_manifold_router` -> `ext:pathlib`
- import gone: `mod:aurora_desktop_agent` -> `ext:json`
- import gone: `mod:aurora_experiential_sim` -> `ext:json`
- import gone: `mod:aurora_expression_perception` -> `ext:enum`
- import gone: `mod:aurora_expression_perception` -> `ext:shutil`
- import gone: `mod:aurora_genealogy_environment` -> `ext:os`
- import gone: `mod:aurora_governance_persistence_gateway` -> `ext:pickle`
- import gone: `mod:aurora_hardware_io` -> `ext:math`
- import gone: `mod:aurora_i_state_beings` -> `ext:enum`
- import gone: `mod:aurora_i_state_beings` -> `ext:hashlib`
- import gone: `mod:aurora_i_state_beings` -> `ext:math`
- import gone: `mod:aurora_image_ingestion` -> `ext:dataclasses`
- import gone: `mod:aurora_image_ingestion` -> `ext:math`
- import gone: `mod:aurora_internal.aurora_attention_engine` -> `ext:math`
- import gone: `mod:aurora_internal.aurora_capability_assimilator` -> `ext:hashlib`
- import gone: `mod:aurora_internal.aurora_capability_assimilator` -> `ext:time`
- import gone: `mod:aurora_internal.aurora_conversation_episode_compiler` -> `ext:math`
- import gone: `mod:aurora_internal.aurora_conversation_rubric_engine` -> `ext:hashlib`
- import gone: `mod:aurora_internal.aurora_corpus_lifecycle` -> `ext:os`
- import gone: `mod:aurora_internal.aurora_corpus_lifecycle` -> `ext:re`
- import gone: `mod:aurora_internal.aurora_difference_buffer` -> `ext:math`
- import gone: `mod:aurora_internal.aurora_directed_training_corpus` -> `ext:random`
- import gone: `mod:aurora_internal.aurora_dna_strand_schema` -> `ext:math`
- import gone: `mod:aurora_internal.aurora_dna_strand_schema` -> `ext:time`
- import gone: `mod:aurora_internal.aurora_dream_curriculum_queue` -> `ext:random`
- import gone: `mod:aurora_internal.aurora_dream_evolution_orchestrator` -> `ext:json`
- import gone: `mod:aurora_internal.aurora_dream_genealogy_bridge` -> `ext:math`
- import gone: `mod:aurora_internal.aurora_general_execution_foundry` -> `ext:queue`
- import gone: `mod:aurora_internal.aurora_intake_metabolism` -> `ext:math`
- import gone: `mod:aurora_internal.aurora_learning_pipeline` -> `ext:math`
- import gone: `mod:aurora_internal.aurora_leverage_relief` -> `ext:collections`
- import gone: `mod:aurora_internal.aurora_operator_composer` -> `ext:time`
- import gone: `mod:aurora_internal.aurora_proposition_substrate` -> `ext:re`
- import gone: `mod:aurora_internal.aurora_quasiarch_observer` -> `ext:re`
- import gone: `mod:aurora_internal.aurora_relational_comparison` -> `ext:math`
- import gone: `mod:aurora_internal.aurora_solidification` -> `ext:enum`
- import gone: `mod:aurora_internal.aurora_solidification` -> `ext:math`
- import gone: `mod:aurora_internal.aurora_solidification` -> `ext:time`
- import gone: `mod:aurora_internal.aurora_tensor_expressions` -> `ext:math`
- import gone: `mod:aurora_internal.constraint_genealogy` -> `ext:enum`
- import gone: `mod:aurora_internal.dual_strata.activation_field` -> `ext:collections`
- import gone: `mod:aurora_internal.dual_strata.strata_state_transfer` -> `ext:time`
- import gone: `mod:aurora_internal.dual_strata.topological_semantic_coordinator` -> `ext:pathlib`
- import gone: `mod:aurora_internal.scouting.backends` -> `ext:subprocess`
- import gone: `mod:aurora_learning_report` -> `ext:math`
- import gone: `mod:aurora_live_vision` -> `ext:hashlib`
- import gone: `mod:aurora_live_vision` -> `ext:math`
- import gone: `mod:aurora_manifold_directory.noncomp_field` -> `ext:math`
- import gone: `mod:aurora_quantum_dream_substrate` -> `ext:math`
- import gone: `mod:aurora_response_teacher` -> `ext:time`
- import gone: `mod:aurora_scout_daemon` -> `ext:json`
- import gone: `mod:aurora_sedimemory` -> `ext:math`
- import gone: `mod:aurora_self_grounding` -> `ext:time`
- import gone: `mod:aurora_thought_formation` -> `ext:json`
- import gone: `mod:aurora_vision_clustering` -> `ext:collections`
- import gone: `mod:aurora_vision_clustering` -> `ext:json`
- import gone: `mod:aurora_vision_clustering` -> `ext:os`
- import gone: `mod:aurora_vision_clustering` -> `ext:pathlib`
- import gone: `mod:aurora_vision_clustering` -> `ext:threading`
- import gone: `mod:aurora_working_memory` -> `ext:dataclasses`
- import gone: `mod:run_aurora` -> `ext:os`
- import gone: `mod:run_intensive_intervals` -> `ext:os`
- import gone: `mod:run_intensive_intervals` -> `ext:time`
- import gone: `mod:scripts.append_to_doc` -> `ext:os`
- import gone: `mod:scripts.aurora_state_compress` -> `ext:os`
- import gone: `mod:scripts.chat_daemon` -> `ext:os`
- import new: `mod:aurora_autonomy` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_behavioral_identity` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_checkpoint` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_expression_perception` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_governance_persistence_gateway` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_grammar_engine` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_hardware_io` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_internal.aurora_braided_substrate` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_internal.aurora_conversation_rubric_engine` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_internal.aurora_correspondence_loop` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_internal.aurora_dream_genealogy_bridge` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_internal.aurora_language_state` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_internal.aurora_ontological_scaffolding` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_internal.aurora_pressure_mathematics_tracker` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_internal.aurora_primitive_extractor` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_internal.aurora_rubric_influence_graph` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_internal.aurora_semantic_probe_battery` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_internal.aurora_shared_helpers` -> `ext:__future__`
- import new: `mod:aurora_internal.aurora_shared_helpers` -> `ext:dataclasses`
- import new: `mod:aurora_internal.aurora_shared_helpers` -> `ext:typing`
- import new: `mod:aurora_internal.aurora_specialized_avatar_synthesizer` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_internal.aurora_structural_pressure_steering` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_internal.constraint_genealogy` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_internal.dual_strata.variant_transition_predictor` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_internal.quasiarch_observer.dimensional_memory` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_ivm` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_language_field` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_runtime` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_simulation_engine` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:aurora_vision_clustering` -> `mod:aurora_internal.aurora_shared_helpers`
- import new: `mod:tests.test_cognition_gap_wiring` -> `ext:__future__`
- import new: `mod:tests.test_cognition_gap_wiring` -> `ext:ast`
- import new: `mod:tests.test_cognition_gap_wiring` -> `ext:os`
- import new: `mod:tests.test_cognition_gap_wiring` -> `ext:pathlib`
- import new: `mod:tests.test_cognition_gap_wiring` -> `ext:pytest`
- import new: `mod:tests.test_cognition_gap_wiring` -> `ext:sys`
- import new: `mod:tests.test_cognition_gap_wiring` -> `mod:aurora_braid_wiring`
- import new: `mod:tests.test_cognition_gap_wiring` -> `mod:aurora_curiosity_engine`
- import new: `mod:tests.test_perspective_merge_repair` -> `ext:__future__`
- import new: `mod:tests.test_perspective_merge_repair` -> `ext:inspect`
- import new: `mod:tests.test_perspective_merge_repair` -> `mod:aurora_internal.constraint_genealogy`
- import new: `mod:tests.test_perspective_merge_repair` -> `mod:aurora_representational_address`
- import new: `mod:tests.test_perspective_merge_repair` -> `mod:aurora_representational_resolution`
- import new: `mod:tests.test_praxis_shared_state_and_discovery` -> `ext:__future__`
- import new: `mod:tests.test_praxis_shared_state_and_discovery` -> `ext:threading`
- import new: `mod:tests.test_praxis_shared_state_and_discovery` -> `ext:time`
- import new: `mod:tests.test_praxis_shared_state_and_discovery` -> `ext:types`
- import new: `mod:tests.test_praxis_shared_state_and_discovery` -> `ext:typing`
- import new: `mod:tests.test_praxis_shared_state_and_discovery` -> `mod:aurora_praxis_bridge`
- import new: `mod:tests.test_undefined_names_in_live_paths` -> `ext:__future__`
- import new: `mod:tests.test_undefined_names_in_live_paths` -> `ext:ast`
- import new: `mod:tests.test_undefined_names_in_live_paths` -> `ext:json`
- import new: `mod:tests.test_undefined_names_in_live_paths` -> `ext:pathlib`
- import new: `mod:tests.test_undefined_names_in_live_paths` -> `ext:pyflakes`
- import new: `mod:tests.test_undefined_names_in_live_paths` -> `ext:pytest`
- import new: `mod:tests.test_undefined_names_in_live_paths` -> `ext:sys`

## 7. Diagnostic evidence

Logging calls: 431 in base, 431 in head.

## 8. Focus areas

### Interaction handling

1 seed node(s); 69516 relationships around them in base, 64316 in head; 135 lost (not consolidated), 1120 new.
- lost: `bus:_open_curiosity_loops` FEEDS `fn:aurora_thought_formation.make_process_context`
- lost: `fn:aurora._run_live_response_turn` READS `bus:_noncomp_output`
- lost: `fn:aurora_representational_address.RepresentationalRef.for_c1` FEEDS `fn:aurora_representational_resolution_base.RepresentationalResolutionEngine.record_participation`
- lost: `fn:aurora_representational_resolution.RepresentationalResolutionEngine.record_pressure_observation` FEEDS `field:aurora_representational_resolution_base.RepresentationalResolutionEngine._active_stage_for_ref`
- lost: `fn:aurora_representational_resolution.get_or_create_engine` FEEDS `fn:aurora_representational_resolution_base.RepresentationalResolutionEngine.record_participation`
- lost: `fn:tests.test_habitat_motivation_build717._drive_real_pressure` FEEDS `fn:aurora_representational_resolution_base.RepresentationalResolutionEngine.record_participation`
- lost: `fn:tests.test_pf3_1_cooccurrence_hub_leak._build_fake_engine` FEEDS `fn:aurora_expression_perception.ExpressionPerceptionEngine._build_expression`
- lost: `mod:aurora-acm.native.aurora_acm_native` IMPORTS `ext:math`
- lost: `mod:aurora_625_pressure_map` IMPORTS `ext:math`
- lost: `mod:aurora_acm_bridge` IMPORTS `ext:os`
- lost: `mod:aurora_behavioral_identity` IMPORTS `ext:collections`
- lost: `mod:aurora_braid_wiring` IMPORTS `ext:time`
- lost: `mod:aurora_checkpoint` IMPORTS `ext:pathlib`
- lost: `mod:aurora_closure_basis` IMPORTS `ext:math`
- lost: `mod:aurora_concept_derivation` IMPORTS `ext:hashlib`
- lost: `mod:aurora_concept_derivation` IMPORTS `ext:time`
- lost: `mod:aurora_consciousness_engine` IMPORTS `ext:enum`
- lost: `mod:aurora_consciousness_engine` IMPORTS `ext:math`
- lost: `mod:aurora_consciousness_engine` IMPORTS `ext:random`
- lost: `mod:aurora_constraint_engine` IMPORTS `ext:math`
- lost: `mod:aurora_constraint_manifold_router` IMPORTS `ext:enum`
- lost: `mod:aurora_constraint_manifold_router` IMPORTS `ext:pathlib`
- lost: `mod:aurora_desktop_agent` IMPORTS `ext:json`
- lost: `mod:aurora_experiential_sim` IMPORTS `ext:json`
- lost: `mod:aurora_expression_perception` IMPORTS `ext:enum`
- lost: `mod:aurora_expression_perception` IMPORTS `ext:shutil`
- lost: `mod:aurora_genealogy_environment` IMPORTS `ext:os`
- lost: `mod:aurora_governance_persistence_gateway` IMPORTS `ext:pickle`
- lost: `mod:aurora_hardware_io` IMPORTS `ext:math`
- lost: `mod:aurora_i_state_beings` IMPORTS `ext:enum`
- lost: `mod:aurora_i_state_beings` IMPORTS `ext:hashlib`
- lost: `mod:aurora_i_state_beings` IMPORTS `ext:math`
- lost: `mod:aurora_image_ingestion` IMPORTS `ext:dataclasses`
- lost: `mod:aurora_image_ingestion` IMPORTS `ext:math`
- lost: `mod:aurora_internal.aurora_attention_engine` IMPORTS `ext:math`
- lost: `mod:aurora_internal.aurora_capability_assimilator` IMPORTS `ext:hashlib`
- lost: `mod:aurora_internal.aurora_capability_assimilator` IMPORTS `ext:time`
- lost: `mod:aurora_internal.aurora_conversation_episode_compiler` IMPORTS `ext:math`
- lost: `mod:aurora_internal.aurora_conversation_rubric_engine` IMPORTS `ext:hashlib`
- lost: `mod:aurora_internal.aurora_corpus_lifecycle` IMPORTS `ext:os`

### Praxis

447 seed node(s); 1564 relationships around them in base, 1604 in head; 0 lost (not consolidated), 40 new.

### Surface and subsurface coordination

1083 seed node(s); 5531 relationships around them in base, 5494 in head; 0 lost (not consolidated), 55 new.

### State hand-offs (bus slots and pipeline signals)

574 seed node(s); 2467 relationships around them in base, 2476 in head; 2 lost (not consolidated), 11 new.
- lost: `bus:_open_curiosity_loops` FEEDS `fn:aurora_thought_formation.make_process_context`
- lost: `fn:aurora._run_live_response_turn` READS `bus:_noncomp_output`

