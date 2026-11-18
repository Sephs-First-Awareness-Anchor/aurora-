# Aurora Module Ownership Map (L1–L8)

**Authors:** Sunni (Sir) Morningstar and Cael Devo

<!-- Generated from docs/module_ownership.json by scripts/render_module_ownership.py. Do not edit by hand. -->

This map gives each covered module its owning layer, where it has one, and a function category.

The layers are the one architecture. The category is a second column over the same modules, for finding things; it never moves a file, changes an import or adds a package. Moving files would change the paths that her code lineage, function ids and fault records are keyed by, so modules stay where they are (decided 2026-11-18).

The record is `docs/module_ownership.json`. Change a module's layer or category there, then run `python scripts/render_module_ownership.py`. The test `tests/test_layer_module_ownership_categories.py` fails if this file and the record disagree.

## Coverage

Covers the Python modules at the repository root, in aurora_internal/ and in aurora_manifold_directory/ only. It is a functional categorization of those modules, not an ownership map of the whole repository. It lists 356 modules.

Covered: `*.py`, `aurora_internal/**/*.py`, `aurora_manifold_directory/**/*.py` (skipping `__pycache__`).

Not covered:

| Path | What it holds |
|---|---|
| `flutter_app/` | Mobile app (Dart) |
| `aurora-acm/` | ACM (Rust) |
| `src/` | Android and other native sources |
| `scripts/` | Maintenance, audit and run scripts |
| `tests/` | Test suite |
| `deploy/` | Deployment files |
| `docs/` | Documentation |
| `aurora_genealogy/` | Genealogy data |
| `aurora_state/, aurora_state_test/, aurora_logs/, vector_data/, lessons/` | Runtime state, logs and data |
| `root non-Python files` | Shell and batch launchers, HTML and JSX prototypes, JSON maps, build specs and requirements |

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
| `aurora_checkpoint.py` | migrated to L8 owner | Governance, persistence and health |
| `aurora_internal/aurora_braided_substrate.py` | state substrate support | Dual strata (surface and subsurface) |
| `aurora_internal/aurora_comprehension_gap.py` | governance/reasoning support | Reasoning and understanding |
| `aurora_internal/aurora_identity_persistence.py` | persistence/identity continuity | Governance, persistence and health |
| `aurora_internal/aurora_ontological_scaffolding.py` | knowledge web/persistence support | Foundation and constraint layers |
| `aurora_internal/aurora_utterance_parser.py` | gateway/parser ingress support | Perception and expression |
| `aurora_drive_sync.py` | migrated to L8 owner | (file not on main) |

State: `aurora_conversation_memory.json` and the state JSON artifacts are runtime persistence (L8).

## Orchestrator

| Module | Role | Category |
|---|---|---|
| `aurora.py` | single runtime entrypoint | Entry and runtime |

## Categories

| Category | Holds | Modules |
|---|---|---|
| Entry and runtime | Entry points, the turn loop and process orchestration. | 12 |
| Foundation and constraint layers | Foundational contract, IVM lattice, X/T/N/B/A constraint physics, NonComp, pressure and leverage. | 37 |
| Beings and dimensional systems | I-State beings, dimensional systems, consciousness assembly and simulation (the L2 to L4 and L7 layer files). | 5 |
| Crystal ops | The concept-crystal store, its evidence-based growth, ingestion and persistence, interaction crystals, and the crystal types QuasiArch shares with live processing. | 26 |
| Memory | SediMemory, working and interaction memory, turn and resolution records. | 12 |
| Reasoning and understanding | Representational resolution, propositions, the causal reasoning waveform, comparison and understanding. | 42 |
| Genealogy, lineage and evidence | Constraint genealogy, code and ability lineage, function provenance, evidence qualification, WARP. | 25 |
| Learning, dreams and development | Training, dreams, curriculum, evolution chambers, curiosity and habitat. | 42 |
| Perception and expression | Sensory and hardware IO, intake, utterance parsing, expression and the reply well-formedness gate. | 22 |
| Identity and language | Behavioral identity, language state, lexicon, grammar and word use. | 15 |
| Governance, persistence and health | Persistence, checkpoints, autonomy, runtime faults and health, metabolic clock, fail-closed guards. | 22 |
| Dual strata (surface and subsurface) | The dual-strata package and the surface/subsurface daemons and substrate. | 45 |
| Bridges and external tools | Praxis, ACM, scouting, research dispatch and tool registries. | 17 |
| Investigative and diagnostic | Read-only observers, canaries, probes, shadows, audits, reports and test setup. The QuasiArch observer stays here. | 34 |

## Reviewed against what the code does

Every module was screened for who imports it and whether it writes files. These 25 were then read, because the screen showed duties beyond their name or because their name and their job differ. The rest keep the category their name and docstring gave them.

| Module | Category | Also | What it actually does |
|---|---|---|---|
| `aurora_interaction_engine.py` | Crystal ops | – | Interaction-lineage compression semantics: the facet sets and InteractionQuasiInnerStrata the interaction crystals use. Booted by aurora.py. |
| `aurora_interaction_processing.py` | Crystal ops | – | Interaction crystal formation, promotion, collapse and routing. aurora.py boots InteractionProcessing; its crystals subclass the QuasiArch crystal types. |
| `aurora_internal/aurora_boot_parity.py` | Investigative and diagnostic | – | Tracks parity between aurora.py boot_aurora and aurora_runtime.py boot_stack. Only tests use it. |
| `aurora_internal/aurora_episode_slip_profiler.py` | Learning, dreams and development | Investigative and diagnostic | EpisodeRubricSummary feeds structural-pressure steering, the specialized avatar synthesizer and the dream genealogy bridge. |
| `aurora_internal/aurora_fault_audit.py` | Investigative and diagnostic | – | AST audit for swallowed exceptions, used by the fault instrumentation script and tests. |
| `aurora_internal/aurora_local_llm_bridge.py` | Governance, persistence and health | – | Fail-closed guard: the retired local-model adapter keeps its names so stale imports fail closed, and there is no model path. Only tests import it. |
| `aurora_internal/aurora_pf1_5_instruments.py` | Perception and expression | Investigative and diagnostic | wellformed_and_coherent decides whether a candidate reply is accepted, in aurora.py and aurora_working_memory.py. Measuring PF1.5 is its second job. |
| `aurora_internal/aurora_quasiarch_observer.py` | Investigative and diagnostic | – | The QuasiArch observer. aurora.py boots it at L8+; it observes and writes its own state (interventions, ghost relics); its answers carry authoritative False and active steering is opt-in. |
| `aurora_internal/aurora_runtime_health.py` | Governance, persistence and health | – | Readiness semantics (degraded is not ready unless a caller opts in). Not wired into the runtime: tests and the fault audit use it. |
| `aurora_internal/aurora_semantic_probe_battery.py` | Identity and language | Investigative and diagnostic | Its function-word set _STRONG_FUNCTION_WORDS is used by aurora_proposition_frame.py and aurora_constraint_semantic_continuity.py, and its _parseable check by aurora_expression_perception.py. The probe battery itself is diagnostic. |
| `aurora_internal/aurora_stack_trace_instrumentation.py` | Genealogy, lineage and evidence | Investigative and diagnostic | instrument_stack wraps runtime methods to record call lineage when AURORA_STACK_TRACE is on. Off by default. |
| `aurora_internal/aurora_surface_doc.py` | Dual strata (surface and subsurface) | Investigative and diagnostic | full_report() gives aurora_surface_dispatcher.py its axis-to-surface routing table, and it writes a pressure log. |
| `aurora_internal/aurora_system_introspection.py` | Genealogy, lineage and evidence | Investigative and diagnostic | Source-derived map of executable functions (function ids are module.qualname) and per-turn decision provenance. aurora.py boots it and connects it to perception; it writes its own state and does not change response selection. |
| `aurora_internal/dual_strata/perturbation_probe.py` | Dual strata (surface and subsurface) | Investigative and diagnostic | Run by the topological semantic coordinator through run_perturbation_probe. |
| `aurora_internal/quasiarch_development_inquiry.py` | Investigative and diagnostic | – | Development inquiry helper used only by the QuasiArch observer. |
| `aurora_internal/quasiarch_observer/__init__.py` | Crystal ops | Investigative and diagnostic | Re-exports the package. aurora_interaction_processing.py imports CrystalInstance and CrystalOrder through it, which loads every submodule when interaction processing boots. |
| `aurora_internal/quasiarch_observer/crystal_engine.py` | Crystal ops | Investigative and diagnostic | Crystal law: what each facet and relational point means at each crystal order (CrystalEngine, FacetLaw, RelationalPointLaw, CrystalOrder). QuasiArch reads it, and CrystalOrder is also the order ladder of the live interaction crystals in aurora_interaction_processing.py, so it is operational, not only investigative. |
| `aurora_internal/quasiarch_observer/dimensional_memory.py` | Investigative and diagnostic | – | QuasiArch lineage memory (DimensionalMemory, IntegratedMemoryPipeline). Loaded with the package, but only the QuasiArch observer calls it. |
| `aurora_internal/quasiarch_observer/dimensional_processing.py` | Crystal ops | Investigative and diagnostic | CrystalInstance, RelationalPoint, crystal formation and promotion. InteractionCrystalInstance in aurora_interaction_processing.py subclasses CrystalInstance and builds RelationalPoint objects, and aurora.py boots InteractionProcessing, so these types hold live state. |
| `aurora_internal/quasiarch_observer/ghost_relics.py` | Investigative and diagnostic | – | Ghost relic records (GhostRelic, GhostRelicSystem). Loaded with the package, but only the QuasiArch observer calls it. |
| `aurora_learning_probe.py` | Investigative and diagnostic | – | Standalone learning probe. Nothing in covered code imports it. |
| `conftest.py` | Investigative and diagnostic | – | pytest setup only: puts the repository root on sys.path for tests/. Not part of the runtime. |
| `run_full_competency_gauntlet.py` | Investigative and diagnostic | – | Script entry point for the competency gauntlet; writes its own results. Nothing in covered code imports it. |
| `run_gauntlet.py` | Investigative and diagnostic | – | Script entry point that runs the gauntlet and writes its own results. Nothing in covered code imports it. |
| `run_probe_battery.py` | Investigative and diagnostic | – | Script entry point for the semantic probe battery; writes its own results. Nothing in covered code imports it. |

## Every module by category

Layer is given where a layer section above names the module. Basis is `reviewed` or `name_and_docstring`.

### Entry and runtime

| Module | Layer | Basis |
|---|---|---|
| `aurora.py` | orchestrator | name_and_docstring |
| `aurora_daemon.py` |  | name_and_docstring |
| `aurora_hub.py` |  | name_and_docstring |
| `aurora_internal/__init__.py` |  | name_and_docstring |
| `aurora_internal/aurora_turn_chain.py` |  | name_and_docstring |
| `aurora_internal/aurora_turn_compute_graph.py` |  | name_and_docstring |
| `aurora_runtime.py` |  | name_and_docstring |
| `corpus_runner.py` |  | name_and_docstring |
| `reply_aurora.py` |  | name_and_docstring |
| `run_aurora.py` |  | name_and_docstring |
| `run_chain.py` |  | name_and_docstring |
| `run_corpus.py` |  | name_and_docstring |

### Foundation and constraint layers

| Module | Layer | Basis |
|---|---|---|
| `aurora_625_pressure_map.py` |  | name_and_docstring |
| `aurora_computational_model.py` |  | name_and_docstring |
| `aurora_constraint_emission.py` |  | name_and_docstring |
| `aurora_constraint_engine.py` |  | name_and_docstring |
| `aurora_constraint_field_map.py` |  | name_and_docstring |
| `aurora_constraint_head.py` |  | name_and_docstring |
| `aurora_constraint_manifold.py` |  | name_and_docstring |
| `aurora_constraint_manifold_compiler.py` |  | name_and_docstring |
| `aurora_constraint_manifold_router.py` |  | name_and_docstring |
| `aurora_constraint_ontology.py` |  | name_and_docstring |
| `aurora_constraint_signature_resolver.py` |  | name_and_docstring |
| `aurora_constraint_stack.py` |  | name_and_docstring |
| `aurora_constraint_unit_adapter.py` |  | name_and_docstring |
| `aurora_internal/aurora_axis_emergence.py` |  | name_and_docstring |
| `aurora_internal/aurora_boundary_envelope.py` |  | name_and_docstring |
| `aurora_internal/aurora_constraint_manifold_patched.py` |  | name_and_docstring |
| `aurora_internal/aurora_dpme_pressure_bridge.py` |  | name_and_docstring |
| `aurora_internal/aurora_leverage_scalar.py` |  | name_and_docstring |
| `aurora_internal/aurora_noncomp_registry.py` |  | name_and_docstring |
| `aurora_internal/aurora_ontological_scaffolding.py` | L8 | name_and_docstring |
| `aurora_internal/aurora_polarity_gradient.py` |  | name_and_docstring |
| `aurora_internal/aurora_pressure_adapter.py` |  | name_and_docstring |
| `aurora_internal/aurora_pressure_classifier.py` |  | name_and_docstring |
| `aurora_internal/aurora_pressure_ledger.py` |  | name_and_docstring |
| `aurora_internal/aurora_pressure_mathematics_tracker.py` |  | name_and_docstring |
| `aurora_internal/aurora_pressure_router.py` |  | name_and_docstring |
| `aurora_internal/aurora_structural_pressure_steering.py` |  | name_and_docstring |
| `aurora_internal/aurora_tensor_expressions.py` |  | name_and_docstring |
| `aurora_ivm.py` | L1 | name_and_docstring |
| `aurora_manifold_directory/__init__.py` |  | name_and_docstring |
| `aurora_manifold_directory/noncomp_field.py` |  | name_and_docstring |
| `aurora_manifold_directory_reader.py` |  | name_and_docstring |
| `aurora_manifold_lookup.py` |  | name_and_docstring |
| `aurora_noncomp_layer_compiler.py` |  | name_and_docstring |
| `aurora_noncomp_manifold_compiler.py` |  | name_and_docstring |
| `aurora_pressure_ontology.py` |  | name_and_docstring |
| `foundational_contract.py` |  | name_and_docstring |

### Beings and dimensional systems

| Module | Layer | Basis |
|---|---|---|
| `aurora_consciousness_engine.py` | L4 | name_and_docstring |
| `aurora_dimensional_systems.py` | L3 | name_and_docstring |
| `aurora_i_state_beings.py` | L2 | name_and_docstring |
| `aurora_istate_operations.py` |  | name_and_docstring |
| `aurora_simulation_engine.py` | L7 | name_and_docstring |

### Crystal ops

| Module | Layer | Basis |
|---|---|---|
| `aurora_core_concept_crystallization.py` |  | name_and_docstring |
| `aurora_crystal_ingestion.py` |  | name_and_docstring |
| `aurora_crystal_state_bridge.py` |  | name_and_docstring |
| `aurora_interaction_engine.py` |  | reviewed |
| `aurora_interaction_processing.py` |  | reviewed |
| `aurora_internal/aurora_lexical_crystals.py` |  | name_and_docstring |
| `aurora_internal/aurora_representation_crystals.py` |  | name_and_docstring |
| `aurora_internal/aurora_sensory_crystal.py` |  | name_and_docstring |
| `aurora_internal/crystal_associations.py` |  | name_and_docstring |
| `aurora_internal/crystal_convergence.py` |  | name_and_docstring |
| `aurora_internal/crystal_facets.py` |  | name_and_docstring |
| `aurora_internal/crystal_grammar.py` |  | name_and_docstring |
| `aurora_internal/crystal_interior.py` |  | name_and_docstring |
| `aurora_internal/crystal_lexicon.py` |  | name_and_docstring |
| `aurora_internal/crystal_maturity.py` |  | name_and_docstring |
| `aurora_internal/crystal_promotion.py` |  | name_and_docstring |
| `aurora_internal/crystal_runtime.py` |  | name_and_docstring |
| `aurora_internal/crystal_sensory.py` |  | name_and_docstring |
| `aurora_internal/crystal_store.py` |  | name_and_docstring |
| `aurora_internal/crystal_substitutability.py` |  | name_and_docstring |
| `aurora_internal/crystal_weave.py` |  | name_and_docstring |
| `aurora_internal/quasiarch_observer/__init__.py` |  | reviewed |
| `aurora_internal/quasiarch_observer/crystal_engine.py` |  | reviewed |
| `aurora_internal/quasiarch_observer/dimensional_processing.py` |  | reviewed |
| `concept_crystal.py` |  | name_and_docstring |
| `crystalzip.py` |  | name_and_docstring |

### Memory

| Module | Layer | Basis |
|---|---|---|
| `aurora_developmental_log.py` |  | name_and_docstring |
| `aurora_interaction_memory.py` |  | name_and_docstring |
| `aurora_internal/aurora_conversation_episode_compiler.py` |  | name_and_docstring |
| `aurora_internal/aurora_difference_buffer.py` |  | name_and_docstring |
| `aurora_internal/aurora_resolution_ledger.py` |  | name_and_docstring |
| `aurora_internal/aurora_solidification.py` |  | name_and_docstring |
| `aurora_internal/aurora_turn_persistence.py` |  | name_and_docstring |
| `aurora_sedimemory.py` |  | name_and_docstring |
| `aurora_turn_ledger.py` |  | name_and_docstring |
| `aurora_understanding_sediment.py` |  | name_and_docstring |
| `aurora_working_memory.py` |  | name_and_docstring |
| `geological_baseline.py` |  | name_and_docstring |

### Reasoning and understanding

| Module | Layer | Basis |
|---|---|---|
| `aurora_boundary_hypothesis.py` |  | name_and_docstring |
| `aurora_concept_derivation.py` |  | name_and_docstring |
| `aurora_constraint_reasoner.py` |  | name_and_docstring |
| `aurora_internal/aurora_attention_engine.py` |  | name_and_docstring |
| `aurora_internal/aurora_causal_generation.py` |  | name_and_docstring |
| `aurora_internal/aurora_comprehension_gap.py` | L8 | name_and_docstring |
| `aurora_internal/aurora_confluence.py` |  | name_and_docstring |
| `aurora_internal/aurora_constraint_semantic_continuity.py` |  | name_and_docstring |
| `aurora_internal/aurora_contradiction_perception.py` |  | name_and_docstring |
| `aurora_internal/aurora_correspondence_loop.py` |  | name_and_docstring |
| `aurora_internal/aurora_cost_diff_score.py` |  | name_and_docstring |
| `aurora_internal/aurora_entropy_detector.py` |  | name_and_docstring |
| `aurora_internal/aurora_frontier_ops.py` |  | name_and_docstring |
| `aurora_internal/aurora_live_possibility_frontier.py` |  | name_and_docstring |
| `aurora_internal/aurora_operational_synthesis.py` |  | name_and_docstring |
| `aurora_internal/aurora_operator_composer.py` |  | name_and_docstring |
| `aurora_internal/aurora_primitive_extractor.py` |  | name_and_docstring |
| `aurora_internal/aurora_primitive_perspective.py` |  | name_and_docstring |
| `aurora_internal/aurora_proposition_frame.py` |  | name_and_docstring |
| `aurora_internal/aurora_proposition_substrate.py` |  | name_and_docstring |
| `aurora_internal/aurora_propositional_understanding.py` |  | name_and_docstring |
| `aurora_internal/aurora_reasoning_paths.py` |  | name_and_docstring |
| `aurora_internal/aurora_recursive_causal_reasoning_waveform.py` |  | name_and_docstring |
| `aurora_internal/aurora_reflective_readdressing.py` |  | name_and_docstring |
| `aurora_internal/aurora_relation_pairs.py` |  | name_and_docstring |
| `aurora_internal/aurora_relational_comparison.py` |  | name_and_docstring |
| `aurora_internal/aurora_representation_exchange.py` |  | name_and_docstring |
| `aurora_internal/aurora_rubric_influence_graph.py` |  | name_and_docstring |
| `aurora_internal/aurora_shadow_state.py` |  | name_and_docstring |
| `aurora_internal/aurora_strategic_horizon.py` |  | name_and_docstring |
| `aurora_internal/aurora_understanding_contract.py` |  | name_and_docstring |
| `aurora_internal/aurora_unformed_patterns.py` |  | name_and_docstring |
| `aurora_internal/aurora_worth_evaluator.py` |  | name_and_docstring |
| `aurora_referent_hypothesis.py` |  | name_and_docstring |
| `aurora_reflexive_interpreter.py` |  | name_and_docstring |
| `aurora_representational_address.py` |  | name_and_docstring |
| `aurora_representational_resolution.py` |  | name_and_docstring |
| `aurora_representational_resolution_base.py` |  | name_and_docstring |
| `aurora_semantic_intention_bridge.py` |  | name_and_docstring |
| `aurora_thought_formation.py` |  | name_and_docstring |
| `aurora_toroidal_circulation.py` |  | name_and_docstring |
| `aurora_waveform_pressure.py` |  | name_and_docstring |

### Genealogy, lineage and evidence

| Module | Layer | Basis |
|---|---|---|
| `aurora_closure_basis.py` |  | name_and_docstring |
| `aurora_genealogy_environment.py` |  | name_and_docstring |
| `aurora_genealogy_promotion_dimension_observer.py` |  | name_and_docstring |
| `aurora_genealogy_representation_resolver.py` |  | name_and_docstring |
| `aurora_genealogy_same_event_correlation.py` |  | name_and_docstring |
| `aurora_internal/aurora_ability_lineage_compiler.py` |  | name_and_docstring |
| `aurora_internal/aurora_attribution_trace.py` |  | name_and_docstring |
| `aurora_internal/aurora_dna_strand_schema.py` |  | name_and_docstring |
| `aurora_internal/aurora_evolutionary_ancestry_bridge.py` |  | name_and_docstring |
| `aurora_internal/aurora_icc_ledger.py` |  | name_and_docstring |
| `aurora_internal/aurora_lineage_bound_traits.py` |  | name_and_docstring |
| `aurora_internal/aurora_lineage_runtime_activation.py` |  | name_and_docstring |
| `aurora_internal/aurora_live_lineage_journal.py` |  | name_and_docstring |
| `aurora_internal/aurora_manual_code_lineage.py` |  | name_and_docstring |
| `aurora_internal/aurora_stack_trace_instrumentation.py` |  | reviewed |
| `aurora_internal/aurora_system_introspection.py` |  | reviewed |
| `aurora_internal/aurora_universal_function_lineage.py` |  | name_and_docstring |
| `aurora_internal/constraint_genealogy.py` |  | name_and_docstring |
| `aurora_internal/evidence_qualification.py` |  | name_and_docstring |
| `aurora_internal/genealogy_evidence_journal.py` |  | name_and_docstring |
| `aurora_internal/lineage_canonical.py` |  | name_and_docstring |
| `aurora_warp_protocol.py` |  | name_and_docstring |
| `genealogy_signature_bridge.py` |  | name_and_docstring |
| `tensor_occupancy_hook.py` |  | name_and_docstring |
| `tensor_occupancy_warp_bridge.py` |  | name_and_docstring |

### Learning, dreams and development

| Module | Layer | Basis |
|---|---|---|
| `aurora_classroom.py` |  | name_and_docstring |
| `aurora_curiosity_engine.py` |  | name_and_docstring |
| `aurora_dream_substrate.py` |  | name_and_docstring |
| `aurora_dream_trainer.py` |  | name_and_docstring |
| `aurora_evolution_stack.py` |  | name_and_docstring |
| `aurora_experiential_sim.py` |  | name_and_docstring |
| `aurora_explore.py` |  | name_and_docstring |
| `aurora_habitat.py` |  | name_and_docstring |
| `aurora_habitat_motivation.py` |  | name_and_docstring |
| `aurora_internal/aurora_capability_assimilator.py` |  | name_and_docstring |
| `aurora_internal/aurora_capability_binding.py` |  | name_and_docstring |
| `aurora_internal/aurora_code_autoevolver.py` |  | name_and_docstring |
| `aurora_internal/aurora_code_evolution_chamber.py` |  | name_and_docstring |
| `aurora_internal/aurora_cognitive_experience_chamber.py` |  | name_and_docstring |
| `aurora_internal/aurora_corpus_lifecycle.py` |  | name_and_docstring |
| `aurora_internal/aurora_development_experiment.py` |  | name_and_docstring |
| `aurora_internal/aurora_developmental_ecology.py` |  | name_and_docstring |
| `aurora_internal/aurora_directed_training_corpus.py` |  | name_and_docstring |
| `aurora_internal/aurora_dream_curriculum_queue.py` |  | name_and_docstring |
| `aurora_internal/aurora_dream_evolution_orchestrator.py` |  | name_and_docstring |
| `aurora_internal/aurora_dream_genealogy_bridge.py` |  | name_and_docstring |
| `aurora_internal/aurora_episode_slip_profiler.py` |  | reviewed |
| `aurora_internal/aurora_evolution_chamber.py` |  | name_and_docstring |
| `aurora_internal/aurora_evolution_hook.py` |  | name_and_docstring |
| `aurora_internal/aurora_evolved_surfaces.py` |  | name_and_docstring |
| `aurora_internal/aurora_general_execution_foundry.py` |  | name_and_docstring |
| `aurora_internal/aurora_learned_index.py` |  | name_and_docstring |
| `aurora_internal/aurora_learned_rules.py` |  | name_and_docstring |
| `aurora_internal/aurora_learning_pipeline.py` |  | name_and_docstring |
| `aurora_internal/aurora_second_gen.py` |  | name_and_docstring |
| `aurora_internal/aurora_variant_promotion.py` |  | name_and_docstring |
| `aurora_internal/lesson_replay.py` |  | name_and_docstring |
| `aurora_possibility_selves.py` |  | name_and_docstring |
| `aurora_quantum_dream_substrate.py` |  | name_and_docstring |
| `aurora_reasoning_games.py` |  | name_and_docstring |
| `aurora_response_teacher.py` |  | name_and_docstring |
| `aurora_training_pulse.py` |  | name_and_docstring |
| `aurora_training_run.py` |  | name_and_docstring |
| `aurora_vocabulary_seed_apply.py` |  | name_and_docstring |
| `backfill_concept_associations.py` |  | name_and_docstring |
| `constraint_evolutionary_sim.py` |  | name_and_docstring |
| `run_intensive_intervals.py` |  | name_and_docstring |

### Perception and expression

| Module | Layer | Basis |
|---|---|---|
| `aurora_articulation.py` |  | name_and_docstring |
| `aurora_concept_imager.py` |  | name_and_docstring |
| `aurora_emergence_surface.py` |  | name_and_docstring |
| `aurora_expression_perception.py` | L5 | name_and_docstring |
| `aurora_hardware_io.py` |  | name_and_docstring |
| `aurora_image_ingestion.py` |  | name_and_docstring |
| `aurora_internal/aurora_input_identity.py` |  | name_and_docstring |
| `aurora_internal/aurora_input_pressure.py` |  | name_and_docstring |
| `aurora_internal/aurora_intake_metabolism.py` |  | name_and_docstring |
| `aurora_internal/aurora_live_experience.py` |  | name_and_docstring |
| `aurora_internal/aurora_pf1_5_instruments.py` |  | reviewed |
| `aurora_internal/aurora_response_pressure_tuner.py` |  | name_and_docstring |
| `aurora_internal/aurora_sender_state.py` |  | name_and_docstring |
| `aurora_internal/aurora_turn_parse_cache.py` |  | name_and_docstring |
| `aurora_internal/aurora_utterance_parser.py` | L8 | name_and_docstring |
| `aurora_live_vision.py` |  | name_and_docstring |
| `aurora_perception_primitives.py` |  | name_and_docstring |
| `aurora_sensory_fallback.py` |  | name_and_docstring |
| `aurora_streaming_expression.py` |  | name_and_docstring |
| `aurora_vision_clustering.py` |  | name_and_docstring |
| `aurora_voice.py` |  | name_and_docstring |
| `aurora_voice_gate.py` |  | name_and_docstring |

### Identity and language

| Module | Layer | Basis |
|---|---|---|
| `aurora_behavioral_identity.py` | L6 | name_and_docstring |
| `aurora_grammar_engine.py` |  | name_and_docstring |
| `aurora_internal/aurora_communication_emergence.py` |  | name_and_docstring |
| `aurora_internal/aurora_conversation_rubric_engine.py` |  | name_and_docstring |
| `aurora_internal/aurora_language_state.py` | L6 | name_and_docstring |
| `aurora_internal/aurora_lexical_grounding.py` |  | name_and_docstring |
| `aurora_internal/aurora_lexical_structure.py` |  | name_and_docstring |
| `aurora_internal/aurora_meaning_evolution.py` |  | name_and_docstring |
| `aurora_internal/aurora_semantic_probe_battery.py` |  | reviewed |
| `aurora_internal/aurora_specialized_avatar_synthesizer.py` |  | name_and_docstring |
| `aurora_internal/aurora_stance_lexicon.py` |  | name_and_docstring |
| `aurora_internal/aurora_word_use.py` |  | name_and_docstring |
| `aurora_language_field.py` |  | name_and_docstring |
| `aurora_language_structure_fitness.py` |  | name_and_docstring |
| `aurora_self_grounding.py` |  | name_and_docstring |

### Governance, persistence and health

| Module | Layer | Basis |
|---|---|---|
| `aurora_autonomy.py` | L8 | name_and_docstring |
| `aurora_checkpoint.py` | L8 | name_and_docstring |
| `aurora_dev_telemetry.py` |  | name_and_docstring |
| `aurora_governance_persistence_gateway.py` | L8 | name_and_docstring |
| `aurora_internal/aurora_energy_layer_costs.py` |  | name_and_docstring |
| `aurora_internal/aurora_identity_persistence.py` | L8 | name_and_docstring |
| `aurora_internal/aurora_leverage_relief.py` |  | name_and_docstring |
| `aurora_internal/aurora_local_llm_bridge.py` |  | reviewed |
| `aurora_internal/aurora_metabolic_clock.py` |  | name_and_docstring |
| `aurora_internal/aurora_metabolic_steps.py` |  | name_and_docstring |
| `aurora_internal/aurora_persistence_audit.py` |  | name_and_docstring |
| `aurora_internal/aurora_persistence_utils.py` |  | name_and_docstring |
| `aurora_internal/aurora_rest_ledger.py` |  | name_and_docstring |
| `aurora_internal/aurora_runtime_constraint_governor.py` |  | name_and_docstring |
| `aurora_internal/aurora_runtime_faults.py` |  | name_and_docstring |
| `aurora_internal/aurora_runtime_health.py` |  | reviewed |
| `aurora_internal/aurora_state_context.py` |  | name_and_docstring |
| `aurora_metabolic_distiller.py` |  | name_and_docstring |
| `aurora_offline_resilience.py` |  | name_and_docstring |
| `aurora_persistence_utils.py` |  | name_and_docstring |
| `aurora_support_stack.py` |  | name_and_docstring |
| `aurora_telemetry.py` |  | name_and_docstring |

### Dual strata (surface and subsurface)

| Module | Layer | Basis |
|---|---|---|
| `aurora_braid_wiring.py` |  | name_and_docstring |
| `aurora_internal/aurora_braided_substrate.py` | L8 | name_and_docstring |
| `aurora_internal/aurora_surface_dispatcher.py` |  | name_and_docstring |
| `aurora_internal/aurora_surface_doc.py` |  | reviewed |
| `aurora_internal/dual_strata/__init__.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/activation_field.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/cers_bridge.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/cers_deprecation.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/cers_potential_trial.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/cers_regulator.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/cers_tensor_locator.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/conscious_frame.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/contextual_overlay.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/crest.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/dce_bridge.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/downward_traversal.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/lifecycle_catalog.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/micro_reasoning.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/perturbation_probe.py` |  | reviewed |
| `aurora_internal/dual_strata/prediction_field.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/predictive_stager.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/presence_metrics.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/semantic_intention_bridge.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/semantic_variant_registry.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/sensory_control_channel.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/sensory_observation.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/sensory_snapshot_channel.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/sleep_cycle.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/strata_link.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/strata_state_transfer.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/subsurface_presence.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/subsurface_presence_runtime.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/subsurface_projection.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/subsurface_state.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/subsystem_waveforms.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/surface_channel.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/surface_continuity_feed.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/surface_sensory_proxy.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/topological_semantic_coordinator.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/topology_frame.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/topology_tracker.py` |  | name_and_docstring |
| `aurora_internal/dual_strata/variant_transition_predictor.py` |  | name_and_docstring |
| `aurora_scout_daemon.py` |  | name_and_docstring |
| `aurora_subsurface_daemon.py` |  | name_and_docstring |
| `aurora_surface_daemon.py` |  | name_and_docstring |

### Bridges and external tools

| Module | Layer | Basis |
|---|---|---|
| `aurora_acm_bridge.py` |  | name_and_docstring |
| `aurora_desktop_agent.py` |  | name_and_docstring |
| `aurora_internal/aurora_clone_harvest.py` |  | name_and_docstring |
| `aurora_internal/aurora_recommendation_hub.py` |  | name_and_docstring |
| `aurora_internal/scouting/__init__.py` |  | name_and_docstring |
| `aurora_internal/scouting/backends.py` |  | name_and_docstring |
| `aurora_internal/scouting/broker.py` |  | name_and_docstring |
| `aurora_internal/scouting/contracts.py` |  | name_and_docstring |
| `aurora_internal/scouting/subsurface_scout_bridge.py` |  | name_and_docstring |
| `aurora_internal/tool_registry.py` |  | name_and_docstring |
| `aurora_praxis_bridge.py` |  | name_and_docstring |
| `aurora_praxis_initiative.py` |  | name_and_docstring |
| `aurora_praxis_messenger.py` |  | name_and_docstring |
| `aurora_recommendation_hub.py` |  | name_and_docstring |
| `aurora_research_dispatch.py` |  | name_and_docstring |
| `aurora_social_corroboration.py` |  | name_and_docstring |
| `aurora_tool_mind.py` |  | name_and_docstring |

### Investigative and diagnostic

| Module | Layer | Basis |
|---|---|---|
| `aurora_build714_resolution_canaries.py` |  | name_and_docstring |
| `aurora_causal_vs_representational_probe.py` |  | name_and_docstring |
| `aurora_diag.py` |  | name_and_docstring |
| `aurora_dream_new_experience_canary.py` |  | name_and_docstring |
| `aurora_flow_audit.py` |  | name_and_docstring |
| `aurora_genealogy_cooccurrence_observatory.py` |  | name_and_docstring |
| `aurora_genealogy_cooccurrence_observatory_report.py` |  | name_and_docstring |
| `aurora_genealogy_difference_producer_observatory.py` |  | name_and_docstring |
| `aurora_genealogy_difference_producer_observatory_report.py` |  | name_and_docstring |
| `aurora_genealogy_difference_shadow.py` |  | name_and_docstring |
| `aurora_genealogy_difference_shadow_report.py` |  | name_and_docstring |
| `aurora_genealogy_environment_shadow.py` |  | name_and_docstring |
| `aurora_genealogy_promotion_dimension_shadow.py` |  | name_and_docstring |
| `aurora_internal/aurora_boot_parity.py` |  | reviewed |
| `aurora_internal/aurora_fault_audit.py` |  | reviewed |
| `aurora_internal/aurora_quasiarch_observer.py` |  | reviewed |
| `aurora_internal/dual_strata/mtsl_acceptance_report.py` |  | name_and_docstring |
| `aurora_internal/quasiarch_development_inquiry.py` |  | reviewed |
| `aurora_internal/quasiarch_observer/dimensional_memory.py` |  | reviewed |
| `aurora_internal/quasiarch_observer/ghost_relics.py` |  | reviewed |
| `aurora_learning_probe.py` |  | reviewed |
| `aurora_learning_report.py` |  | name_and_docstring |
| `aurora_rank6_shadow_analysis.py` |  | name_and_docstring |
| `aurora_representational_canary.py` |  | name_and_docstring |
| `aurora_representational_closed_loop_canary.py` |  | name_and_docstring |
| `aurora_representational_cross_system_canary.py` |  | name_and_docstring |
| `aurora_representational_divergence_canaries.py` |  | name_and_docstring |
| `aurora_representational_emergence_observatory.py` |  | name_and_docstring |
| `aurora_same_input_history_canary.py` |  | name_and_docstring |
| `conftest.py` |  | reviewed |
| `run_full_competency_gauntlet.py` |  | reviewed |
| `run_gauntlet.py` |  | reviewed |
| `run_probe_battery.py` |  | reviewed |
| `test_constraint_reasoner.py` |  | name_and_docstring |
