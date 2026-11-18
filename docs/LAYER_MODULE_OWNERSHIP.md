# Aurora Module Ownership Map (L1–L8)

**Authors:** Sunni (Sir) Morningstar and Cael Devo

This map enumerates non-layer modules and their owning layer classification, and gives every module a function category.

The layers are the one architecture. The category is a second column over the same modules, for finding things; it never moves a file, changes an import or adds a package. Moving files would change the paths that her code lineage, function ids and fault records are keyed by, so modules stay where they are (decided 2026-11-18).

Categories were first assigned from each module's name and docstring and are open to correction: change a row here and the test `tests/test_layer_module_ownership_categories.py` keeps the map whole.

## L1 (IVM / geometry substrate)

| Module | Role | Category |
|---|---|---|
| `aurora_ivm.py` | layer file | Foundation and constraint layers |

## L2 (I-State synthesis)

| Module | Role | Category |
|---|---|---|
| `aurora_i_state_beings.py` | layer file | Beings and dimensional systems |

## L3 (Dimensional transforms)

| Module | Role | Category |
|---|---|---|
| `aurora_dimensional_systems.py` | layer file | Beings and dimensional systems |

## L4 (Consciousness assembly)

| Module | Role | Category |
|---|---|---|
| `aurora_consciousness_engine.py` | layer file | Beings and dimensional systems |

## L5 (Perception/IO surface)

| Module | Role | Category |
|---|---|---|
| `aurora_expression_perception.py` | layer file | Perception and expression |
| `aurora_sensory_competency.py` | migrated to L5 owner | (file not on main) |
| `aurora_hardware_interface.py` | migrated to L5 owner | (file not on main) |
| `aurora_sensory_integration.py` | migrated to L5 owner | (file not on main) |
| `aurora_vision_bootstrap.py` | migrated to L5 owner | (file not on main) |

## L6 (Behavioral identity)

| Module | Role | Category |
|---|---|---|
| `aurora_behavioral_identity.py` | layer file | Identity and language |
| `aurora_internal/aurora_language_state.py` | identity-expression adaptation support | Identity and language |

## L7 (Simulation)

| Module | Role | Category |
|---|---|---|
| `aurora_simulation_engine.py` | layer file | Beings and dimensional systems |

## L8 (Governance / persistence / gateway)

| Module | Role | Category |
|---|---|---|
| `aurora_governance_persistence_gateway.py` | layer file | Governance, persistence and health |
| `aurora_autonomy.py` | migrated to L8 owner | Governance, persistence and health |
| `aurora_drive_sync.py` | migrated to L8 owner | (file not on main) |
| `aurora_checkpoint.py` | migrated to L8 owner | Governance, persistence and health |
| `aurora_internal/aurora_identity_persistence.py` | persistence/identity continuity | Governance, persistence and health |
| `aurora_internal/aurora_utterance_parser.py` | gateway/parser ingress support | Perception and expression |
| `aurora_internal/aurora_ontological_scaffolding.py` | knowledge web/persistence support | Foundation and constraint layers |
| `aurora_internal/aurora_comprehension_gap.py` | governance/reasoning support | Reasoning and understanding |
| `aurora_internal/aurora_braided_substrate.py` | state substrate support | Dual strata (surface and subsurface) |

## Orchestrator

| Module | Role | Category |
|---|---|---|
| `aurora.py` | single runtime entrypoint | Entry and runtime |

State: `aurora_conversation_memory.json` and the state JSON artifacts are runtime persistence (L8).

## Categories

| Category | Holds | Modules |
|---|---|---|
| Entry and runtime | Entry points, the turn loop and process orchestration. | 15 |
| Foundation and constraint layers | Foundational contract, IVM lattice, X/T/N/B/A constraint physics, NonComp, pressure and leverage. | 37 |
| Beings and dimensional systems | I-State beings, dimensional systems, consciousness assembly and simulation (the L2 to L4 and L7 layer files). | 5 |
| Crystal ops | The concept-crystal store, its evidence-based growth, ingestion and persistence. | 21 |
| Memory | SediMemory, working and interaction memory, turn and resolution records. | 12 |
| Reasoning and understanding | Representational resolution, propositions, the causal reasoning waveform, comparison and understanding. | 42 |
| Genealogy, lineage and evidence | Constraint genealogy, code and ability lineage, evidence qualification, WARP. | 23 |
| Learning, dreams and development | Training, dreams, curriculum, evolution chambers, curiosity and habitat. | 41 |
| Perception and expression | Sensory and hardware IO, intake, utterance parsing and expression. | 21 |
| Identity and language | Behavioral identity, language state, lexicon, grammar and word use. | 14 |
| Governance, persistence and health | Persistence, checkpoints, autonomy, runtime faults and health, metabolic clock. | 23 |
| Dual strata (surface and subsurface) | The dual-strata package and the surface/subsurface daemons and substrate. | 43 |
| Bridges and external tools | Praxis, ACM, local LLM, scouting, research dispatch and tool registries. | 18 |
| Investigative and diagnostic | Read-only observers, canaries, probes, shadows, audits and reports. QuasiArch stays here. | 41 |

## Every module by category

Covers every `.py` file at the repository root, in `aurora_internal/` (with its subpackages) and in `aurora_manifold_directory/`. Tests and scripts are not listed. Layer is given where the sections above name one.

### Entry and runtime

| Module | Layer |
|---|---|
| `aurora.py` | Orchestrator |
| `aurora_daemon.py` |  |
| `aurora_hub.py` |  |
| `aurora_interaction_engine.py` |  |
| `aurora_interaction_processing.py` |  |
| `aurora_internal/__init__.py` |  |
| `aurora_internal/aurora_turn_chain.py` |  |
| `aurora_internal/aurora_turn_compute_graph.py` |  |
| `aurora_runtime.py` |  |
| `conftest.py` |  |
| `corpus_runner.py` |  |
| `reply_aurora.py` |  |
| `run_aurora.py` |  |
| `run_chain.py` |  |
| `run_corpus.py` |  |

### Foundation and constraint layers

| Module | Layer |
|---|---|
| `aurora_625_pressure_map.py` |  |
| `aurora_computational_model.py` |  |
| `aurora_constraint_emission.py` |  |
| `aurora_constraint_engine.py` |  |
| `aurora_constraint_field_map.py` |  |
| `aurora_constraint_head.py` |  |
| `aurora_constraint_manifold.py` |  |
| `aurora_constraint_manifold_compiler.py` |  |
| `aurora_constraint_manifold_router.py` |  |
| `aurora_constraint_ontology.py` |  |
| `aurora_constraint_signature_resolver.py` |  |
| `aurora_constraint_stack.py` |  |
| `aurora_constraint_unit_adapter.py` |  |
| `aurora_internal/aurora_axis_emergence.py` |  |
| `aurora_internal/aurora_boundary_envelope.py` |  |
| `aurora_internal/aurora_constraint_manifold_patched.py` |  |
| `aurora_internal/aurora_dpme_pressure_bridge.py` |  |
| `aurora_internal/aurora_leverage_scalar.py` |  |
| `aurora_internal/aurora_noncomp_registry.py` |  |
| `aurora_internal/aurora_ontological_scaffolding.py` | L8 |
| `aurora_internal/aurora_polarity_gradient.py` |  |
| `aurora_internal/aurora_pressure_adapter.py` |  |
| `aurora_internal/aurora_pressure_classifier.py` |  |
| `aurora_internal/aurora_pressure_ledger.py` |  |
| `aurora_internal/aurora_pressure_mathematics_tracker.py` |  |
| `aurora_internal/aurora_pressure_router.py` |  |
| `aurora_internal/aurora_structural_pressure_steering.py` |  |
| `aurora_internal/aurora_tensor_expressions.py` |  |
| `aurora_ivm.py` | L1 |
| `aurora_manifold_directory/__init__.py` |  |
| `aurora_manifold_directory/noncomp_field.py` |  |
| `aurora_manifold_directory_reader.py` |  |
| `aurora_manifold_lookup.py` |  |
| `aurora_noncomp_layer_compiler.py` |  |
| `aurora_noncomp_manifold_compiler.py` |  |
| `aurora_pressure_ontology.py` |  |
| `foundational_contract.py` |  |

### Beings and dimensional systems

| Module | Layer |
|---|---|
| `aurora_consciousness_engine.py` | L4 |
| `aurora_dimensional_systems.py` | L3 |
| `aurora_i_state_beings.py` | L2 |
| `aurora_istate_operations.py` |  |
| `aurora_simulation_engine.py` | L7 |

### Crystal ops

| Module | Layer |
|---|---|
| `aurora_core_concept_crystallization.py` |  |
| `aurora_crystal_ingestion.py` |  |
| `aurora_crystal_state_bridge.py` |  |
| `aurora_internal/aurora_lexical_crystals.py` |  |
| `aurora_internal/aurora_representation_crystals.py` |  |
| `aurora_internal/aurora_sensory_crystal.py` |  |
| `aurora_internal/crystal_associations.py` |  |
| `aurora_internal/crystal_convergence.py` |  |
| `aurora_internal/crystal_facets.py` |  |
| `aurora_internal/crystal_grammar.py` |  |
| `aurora_internal/crystal_interior.py` |  |
| `aurora_internal/crystal_lexicon.py` |  |
| `aurora_internal/crystal_maturity.py` |  |
| `aurora_internal/crystal_promotion.py` |  |
| `aurora_internal/crystal_runtime.py` |  |
| `aurora_internal/crystal_sensory.py` |  |
| `aurora_internal/crystal_store.py` |  |
| `aurora_internal/crystal_substitutability.py` |  |
| `aurora_internal/crystal_weave.py` |  |
| `concept_crystal.py` |  |
| `crystalzip.py` |  |

### Memory

| Module | Layer |
|---|---|
| `aurora_developmental_log.py` |  |
| `aurora_interaction_memory.py` |  |
| `aurora_internal/aurora_conversation_episode_compiler.py` |  |
| `aurora_internal/aurora_difference_buffer.py` |  |
| `aurora_internal/aurora_resolution_ledger.py` |  |
| `aurora_internal/aurora_solidification.py` |  |
| `aurora_internal/aurora_turn_persistence.py` |  |
| `aurora_sedimemory.py` |  |
| `aurora_turn_ledger.py` |  |
| `aurora_understanding_sediment.py` |  |
| `aurora_working_memory.py` |  |
| `geological_baseline.py` |  |

### Reasoning and understanding

| Module | Layer |
|---|---|
| `aurora_boundary_hypothesis.py` |  |
| `aurora_concept_derivation.py` |  |
| `aurora_constraint_reasoner.py` |  |
| `aurora_internal/aurora_attention_engine.py` |  |
| `aurora_internal/aurora_causal_generation.py` |  |
| `aurora_internal/aurora_comprehension_gap.py` | L8 |
| `aurora_internal/aurora_confluence.py` |  |
| `aurora_internal/aurora_constraint_semantic_continuity.py` |  |
| `aurora_internal/aurora_contradiction_perception.py` |  |
| `aurora_internal/aurora_correspondence_loop.py` |  |
| `aurora_internal/aurora_cost_diff_score.py` |  |
| `aurora_internal/aurora_entropy_detector.py` |  |
| `aurora_internal/aurora_frontier_ops.py` |  |
| `aurora_internal/aurora_live_possibility_frontier.py` |  |
| `aurora_internal/aurora_operational_synthesis.py` |  |
| `aurora_internal/aurora_operator_composer.py` |  |
| `aurora_internal/aurora_primitive_extractor.py` |  |
| `aurora_internal/aurora_primitive_perspective.py` |  |
| `aurora_internal/aurora_proposition_frame.py` |  |
| `aurora_internal/aurora_proposition_substrate.py` |  |
| `aurora_internal/aurora_propositional_understanding.py` |  |
| `aurora_internal/aurora_reasoning_paths.py` |  |
| `aurora_internal/aurora_recursive_causal_reasoning_waveform.py` |  |
| `aurora_internal/aurora_reflective_readdressing.py` |  |
| `aurora_internal/aurora_relation_pairs.py` |  |
| `aurora_internal/aurora_relational_comparison.py` |  |
| `aurora_internal/aurora_representation_exchange.py` |  |
| `aurora_internal/aurora_rubric_influence_graph.py` |  |
| `aurora_internal/aurora_shadow_state.py` |  |
| `aurora_internal/aurora_strategic_horizon.py` |  |
| `aurora_internal/aurora_understanding_contract.py` |  |
| `aurora_internal/aurora_unformed_patterns.py` |  |
| `aurora_internal/aurora_worth_evaluator.py` |  |
| `aurora_referent_hypothesis.py` |  |
| `aurora_reflexive_interpreter.py` |  |
| `aurora_representational_address.py` |  |
| `aurora_representational_resolution.py` |  |
| `aurora_representational_resolution_base.py` |  |
| `aurora_semantic_intention_bridge.py` |  |
| `aurora_thought_formation.py` |  |
| `aurora_toroidal_circulation.py` |  |
| `aurora_waveform_pressure.py` |  |

### Genealogy, lineage and evidence

| Module | Layer |
|---|---|
| `aurora_closure_basis.py` |  |
| `aurora_genealogy_environment.py` |  |
| `aurora_genealogy_promotion_dimension_observer.py` |  |
| `aurora_genealogy_representation_resolver.py` |  |
| `aurora_genealogy_same_event_correlation.py` |  |
| `aurora_internal/aurora_ability_lineage_compiler.py` |  |
| `aurora_internal/aurora_attribution_trace.py` |  |
| `aurora_internal/aurora_dna_strand_schema.py` |  |
| `aurora_internal/aurora_evolutionary_ancestry_bridge.py` |  |
| `aurora_internal/aurora_icc_ledger.py` |  |
| `aurora_internal/aurora_lineage_bound_traits.py` |  |
| `aurora_internal/aurora_lineage_runtime_activation.py` |  |
| `aurora_internal/aurora_live_lineage_journal.py` |  |
| `aurora_internal/aurora_manual_code_lineage.py` |  |
| `aurora_internal/aurora_universal_function_lineage.py` |  |
| `aurora_internal/constraint_genealogy.py` |  |
| `aurora_internal/evidence_qualification.py` |  |
| `aurora_internal/genealogy_evidence_journal.py` |  |
| `aurora_internal/lineage_canonical.py` |  |
| `aurora_warp_protocol.py` |  |
| `genealogy_signature_bridge.py` |  |
| `tensor_occupancy_hook.py` |  |
| `tensor_occupancy_warp_bridge.py` |  |

### Learning, dreams and development

| Module | Layer |
|---|---|
| `aurora_classroom.py` |  |
| `aurora_curiosity_engine.py` |  |
| `aurora_dream_substrate.py` |  |
| `aurora_dream_trainer.py` |  |
| `aurora_evolution_stack.py` |  |
| `aurora_experiential_sim.py` |  |
| `aurora_explore.py` |  |
| `aurora_habitat.py` |  |
| `aurora_habitat_motivation.py` |  |
| `aurora_internal/aurora_capability_assimilator.py` |  |
| `aurora_internal/aurora_capability_binding.py` |  |
| `aurora_internal/aurora_code_autoevolver.py` |  |
| `aurora_internal/aurora_code_evolution_chamber.py` |  |
| `aurora_internal/aurora_cognitive_experience_chamber.py` |  |
| `aurora_internal/aurora_corpus_lifecycle.py` |  |
| `aurora_internal/aurora_development_experiment.py` |  |
| `aurora_internal/aurora_developmental_ecology.py` |  |
| `aurora_internal/aurora_directed_training_corpus.py` |  |
| `aurora_internal/aurora_dream_curriculum_queue.py` |  |
| `aurora_internal/aurora_dream_evolution_orchestrator.py` |  |
| `aurora_internal/aurora_dream_genealogy_bridge.py` |  |
| `aurora_internal/aurora_evolution_chamber.py` |  |
| `aurora_internal/aurora_evolution_hook.py` |  |
| `aurora_internal/aurora_evolved_surfaces.py` |  |
| `aurora_internal/aurora_general_execution_foundry.py` |  |
| `aurora_internal/aurora_learned_index.py` |  |
| `aurora_internal/aurora_learned_rules.py` |  |
| `aurora_internal/aurora_learning_pipeline.py` |  |
| `aurora_internal/aurora_second_gen.py` |  |
| `aurora_internal/aurora_variant_promotion.py` |  |
| `aurora_internal/lesson_replay.py` |  |
| `aurora_possibility_selves.py` |  |
| `aurora_quantum_dream_substrate.py` |  |
| `aurora_reasoning_games.py` |  |
| `aurora_response_teacher.py` |  |
| `aurora_training_pulse.py` |  |
| `aurora_training_run.py` |  |
| `aurora_vocabulary_seed_apply.py` |  |
| `backfill_concept_associations.py` |  |
| `constraint_evolutionary_sim.py` |  |
| `run_intensive_intervals.py` |  |

### Perception and expression

| Module | Layer |
|---|---|
| `aurora_articulation.py` |  |
| `aurora_concept_imager.py` |  |
| `aurora_emergence_surface.py` |  |
| `aurora_expression_perception.py` | L5 |
| `aurora_hardware_io.py` |  |
| `aurora_image_ingestion.py` |  |
| `aurora_internal/aurora_input_identity.py` |  |
| `aurora_internal/aurora_input_pressure.py` |  |
| `aurora_internal/aurora_intake_metabolism.py` |  |
| `aurora_internal/aurora_live_experience.py` |  |
| `aurora_internal/aurora_response_pressure_tuner.py` |  |
| `aurora_internal/aurora_sender_state.py` |  |
| `aurora_internal/aurora_turn_parse_cache.py` |  |
| `aurora_internal/aurora_utterance_parser.py` | L8 |
| `aurora_live_vision.py` |  |
| `aurora_perception_primitives.py` |  |
| `aurora_sensory_fallback.py` |  |
| `aurora_streaming_expression.py` |  |
| `aurora_vision_clustering.py` |  |
| `aurora_voice.py` |  |
| `aurora_voice_gate.py` |  |

### Identity and language

| Module | Layer |
|---|---|
| `aurora_behavioral_identity.py` | L6 |
| `aurora_grammar_engine.py` |  |
| `aurora_internal/aurora_communication_emergence.py` |  |
| `aurora_internal/aurora_conversation_rubric_engine.py` |  |
| `aurora_internal/aurora_language_state.py` | L6 |
| `aurora_internal/aurora_lexical_grounding.py` |  |
| `aurora_internal/aurora_lexical_structure.py` |  |
| `aurora_internal/aurora_meaning_evolution.py` |  |
| `aurora_internal/aurora_specialized_avatar_synthesizer.py` |  |
| `aurora_internal/aurora_stance_lexicon.py` |  |
| `aurora_internal/aurora_word_use.py` |  |
| `aurora_language_field.py` |  |
| `aurora_language_structure_fitness.py` |  |
| `aurora_self_grounding.py` |  |

### Governance, persistence and health

| Module | Layer |
|---|---|
| `aurora_autonomy.py` | L8 |
| `aurora_checkpoint.py` | L8 |
| `aurora_dev_telemetry.py` |  |
| `aurora_governance_persistence_gateway.py` | L8 |
| `aurora_internal/aurora_boot_parity.py` |  |
| `aurora_internal/aurora_energy_layer_costs.py` |  |
| `aurora_internal/aurora_fault_audit.py` |  |
| `aurora_internal/aurora_identity_persistence.py` | L8 |
| `aurora_internal/aurora_leverage_relief.py` |  |
| `aurora_internal/aurora_metabolic_clock.py` |  |
| `aurora_internal/aurora_metabolic_steps.py` |  |
| `aurora_internal/aurora_persistence_audit.py` |  |
| `aurora_internal/aurora_persistence_utils.py` |  |
| `aurora_internal/aurora_rest_ledger.py` |  |
| `aurora_internal/aurora_runtime_constraint_governor.py` |  |
| `aurora_internal/aurora_runtime_faults.py` |  |
| `aurora_internal/aurora_runtime_health.py` |  |
| `aurora_internal/aurora_state_context.py` |  |
| `aurora_metabolic_distiller.py` |  |
| `aurora_offline_resilience.py` |  |
| `aurora_persistence_utils.py` |  |
| `aurora_support_stack.py` |  |
| `aurora_telemetry.py` |  |

### Dual strata (surface and subsurface)

| Module | Layer |
|---|---|
| `aurora_braid_wiring.py` |  |
| `aurora_internal/aurora_braided_substrate.py` | L8 |
| `aurora_internal/aurora_surface_dispatcher.py` |  |
| `aurora_internal/dual_strata/__init__.py` |  |
| `aurora_internal/dual_strata/activation_field.py` |  |
| `aurora_internal/dual_strata/cers_bridge.py` |  |
| `aurora_internal/dual_strata/cers_deprecation.py` |  |
| `aurora_internal/dual_strata/cers_potential_trial.py` |  |
| `aurora_internal/dual_strata/cers_regulator.py` |  |
| `aurora_internal/dual_strata/cers_tensor_locator.py` |  |
| `aurora_internal/dual_strata/conscious_frame.py` |  |
| `aurora_internal/dual_strata/contextual_overlay.py` |  |
| `aurora_internal/dual_strata/crest.py` |  |
| `aurora_internal/dual_strata/dce_bridge.py` |  |
| `aurora_internal/dual_strata/downward_traversal.py` |  |
| `aurora_internal/dual_strata/lifecycle_catalog.py` |  |
| `aurora_internal/dual_strata/micro_reasoning.py` |  |
| `aurora_internal/dual_strata/prediction_field.py` |  |
| `aurora_internal/dual_strata/predictive_stager.py` |  |
| `aurora_internal/dual_strata/presence_metrics.py` |  |
| `aurora_internal/dual_strata/semantic_intention_bridge.py` |  |
| `aurora_internal/dual_strata/semantic_variant_registry.py` |  |
| `aurora_internal/dual_strata/sensory_control_channel.py` |  |
| `aurora_internal/dual_strata/sensory_observation.py` |  |
| `aurora_internal/dual_strata/sensory_snapshot_channel.py` |  |
| `aurora_internal/dual_strata/sleep_cycle.py` |  |
| `aurora_internal/dual_strata/strata_link.py` |  |
| `aurora_internal/dual_strata/strata_state_transfer.py` |  |
| `aurora_internal/dual_strata/subsurface_presence.py` |  |
| `aurora_internal/dual_strata/subsurface_presence_runtime.py` |  |
| `aurora_internal/dual_strata/subsurface_projection.py` |  |
| `aurora_internal/dual_strata/subsurface_state.py` |  |
| `aurora_internal/dual_strata/subsystem_waveforms.py` |  |
| `aurora_internal/dual_strata/surface_channel.py` |  |
| `aurora_internal/dual_strata/surface_continuity_feed.py` |  |
| `aurora_internal/dual_strata/surface_sensory_proxy.py` |  |
| `aurora_internal/dual_strata/topological_semantic_coordinator.py` |  |
| `aurora_internal/dual_strata/topology_frame.py` |  |
| `aurora_internal/dual_strata/topology_tracker.py` |  |
| `aurora_internal/dual_strata/variant_transition_predictor.py` |  |
| `aurora_scout_daemon.py` |  |
| `aurora_subsurface_daemon.py` |  |
| `aurora_surface_daemon.py` |  |

### Bridges and external tools

| Module | Layer |
|---|---|
| `aurora_acm_bridge.py` |  |
| `aurora_desktop_agent.py` |  |
| `aurora_internal/aurora_clone_harvest.py` |  |
| `aurora_internal/aurora_local_llm_bridge.py` |  |
| `aurora_internal/aurora_recommendation_hub.py` |  |
| `aurora_internal/scouting/__init__.py` |  |
| `aurora_internal/scouting/backends.py` |  |
| `aurora_internal/scouting/broker.py` |  |
| `aurora_internal/scouting/contracts.py` |  |
| `aurora_internal/scouting/subsurface_scout_bridge.py` |  |
| `aurora_internal/tool_registry.py` |  |
| `aurora_praxis_bridge.py` |  |
| `aurora_praxis_initiative.py` |  |
| `aurora_praxis_messenger.py` |  |
| `aurora_recommendation_hub.py` |  |
| `aurora_research_dispatch.py` |  |
| `aurora_social_corroboration.py` |  |
| `aurora_tool_mind.py` |  |

### Investigative and diagnostic

| Module | Layer |
|---|---|
| `aurora_build714_resolution_canaries.py` |  |
| `aurora_causal_vs_representational_probe.py` |  |
| `aurora_diag.py` |  |
| `aurora_dream_new_experience_canary.py` |  |
| `aurora_flow_audit.py` |  |
| `aurora_genealogy_cooccurrence_observatory.py` |  |
| `aurora_genealogy_cooccurrence_observatory_report.py` |  |
| `aurora_genealogy_difference_producer_observatory.py` |  |
| `aurora_genealogy_difference_producer_observatory_report.py` |  |
| `aurora_genealogy_difference_shadow.py` |  |
| `aurora_genealogy_difference_shadow_report.py` |  |
| `aurora_genealogy_environment_shadow.py` |  |
| `aurora_genealogy_promotion_dimension_shadow.py` |  |
| `aurora_internal/aurora_episode_slip_profiler.py` |  |
| `aurora_internal/aurora_pf1_5_instruments.py` |  |
| `aurora_internal/aurora_quasiarch_observer.py` |  |
| `aurora_internal/aurora_semantic_probe_battery.py` |  |
| `aurora_internal/aurora_stack_trace_instrumentation.py` |  |
| `aurora_internal/aurora_surface_doc.py` |  |
| `aurora_internal/aurora_system_introspection.py` |  |
| `aurora_internal/dual_strata/mtsl_acceptance_report.py` |  |
| `aurora_internal/dual_strata/perturbation_probe.py` |  |
| `aurora_internal/quasiarch_development_inquiry.py` |  |
| `aurora_internal/quasiarch_observer/__init__.py` |  |
| `aurora_internal/quasiarch_observer/crystal_engine.py` |  |
| `aurora_internal/quasiarch_observer/dimensional_memory.py` |  |
| `aurora_internal/quasiarch_observer/dimensional_processing.py` |  |
| `aurora_internal/quasiarch_observer/ghost_relics.py` |  |
| `aurora_learning_probe.py` |  |
| `aurora_learning_report.py` |  |
| `aurora_rank6_shadow_analysis.py` |  |
| `aurora_representational_canary.py` |  |
| `aurora_representational_closed_loop_canary.py` |  |
| `aurora_representational_cross_system_canary.py` |  |
| `aurora_representational_divergence_canaries.py` |  |
| `aurora_representational_emergence_observatory.py` |  |
| `aurora_same_input_history_canary.py` |  |
| `run_full_competency_gauntlet.py` |  |
| `run_gauntlet.py` |  |
| `run_probe_battery.py` |  |
| `test_constraint_reasoner.py` |  |
