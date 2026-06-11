# Aurora Strata Domain Map

This file maps the `aurora_strata` branch into the seven domains you asked for.

Source anchors:
- [DUAL_STRATA_ARCHITECTURE.md](./DUAL_STRATA_ARCHITECTURE.md)
- [OBLIGATION_LAW.md](./OBLIGATION_LAW.md)
- [NONCOMP_SEMANTIC_INVENTORY.md](./NONCOMP_SEMANTIC_INVENTORY.md)
- [aurora_internal/aurora_noncomp_registry.py](./aurora_internal/aurora_noncomp_registry.py)

## 1. Genetic & Lineage Systems

Owns:
- Constraint genealogy
- Closure basis and slot derivation
- Ability/link grading
- Manual code lineage assimilation
- Live lineage journal

Key modules:
- `aurora_internal/constraint_genealogy.py`
- `aurora_closure_basis.py`
- `constraint_genealogy_closure_wiring.py`
- `aurora_internal/lineage_canonical.py`
- `aurora_internal/aurora_noncomp_registry.py`
- `aurora_evolution_stack.py`
- `aurora_internal/aurora_manual_code_lineage.py`
- `aurora_internal/aurora_live_lineage_journal.py`

Reads:
- Registry physics
- Constraint signatures
- Ability profiles
- Lineage states
- Code-change descriptors

Writes:
- Genealogy state
- Lineage manifests
- Manual lineage state
- Live emergence journal

Clause tags:
- `subsurface`
- `evolution and repair routing`
- `DCE pressure selection`

## 2. Environmental Filter & Viability

Owns:
- Pressure banding
- Viable-band calibration
- Threshold nudging
- Pressure routing
- Pressure classification
- Cost accounting
- Runtime gating

Key modules:
- `aurora_625_pressure_map.py`
- `aurora_internal/aurora_leverage_scalar.py`
- `aurora_pressure_ontology.py`
- `aurora_internal/aurora_pressure_classifier.py`
- `aurora_internal/aurora_pressure_router.py`
- `aurora_internal/aurora_pressure_adapter.py`
- `aurora_internal/aurora_pressure_ledger.py`
- `aurora_internal/aurora_runtime_constraint_governor.py`
- `aurora_internal/aurora_response_pressure_tuner.py`

Reads:
- Non-Comp registry
- Runtime pressure observations
- IVM and constraint state
- Fail-ledger signals

Writes:
- Pressure maps
- Route summaries
- Governor state
- Pressure-ledger history

Clause tags:
- `subsurface` pressure reservoir
- `DCE pressure gate`
- `surface` receives only selected obligations

## 3. Conscious Perception & Expression

Owns:
- Conscious frame
- DCE bridge
- Meaning and accuracy tracking
- Surface expression
- Mouth-catching-up-to-mind evolution

Key modules:
- `aurora_consciousness_engine.py`
- `aurora_expression_perception.py`
- `aurora_internal/aurora_understanding_contract.py`
- `aurora_internal/aurora_language_state.py`
- `aurora_state_voice.py`
- `aurora_internal/aurora_surface_dispatcher.py`
- `aurora_reflexive_interpreter.py`
- `aurora_grammar_engine.py`

Reads:
- Working memory
- Sensory context
- OETS
- Pressure snapshots
- Language maturity signals

Writes:
- Conscious-frame state
- Understanding-contract JSON
- Language-state JSON
- Expression drafts
- Natural-language state reports

Clause tags:
- `DCE bridge`
- `surface`
- `sensory split`

## 4. Experiential Depth & Memory

Owns:
- Relational identity
- Conversation memory
- OETS persistence
- Sedimented long-horizon memory
- Meaning continuity

Key modules:
- `aurora_internal/aurora_identity_persistence.py`
- `aurora_interaction_memory.py`
- `aurora_sedimemory.py`
- `aurora_internal/aurora_meaning_evolution.py`
- `aurora_internal/aurora_ontological_scaffolding.py`
- `aurora_support_stack.py`

Reads:
- Conversation history
- OETS web state
- Interaction crystals
- Sensory and meaning traces
- Current turn context

Writes:
- Identity JSON
- Conversation-memory stores
- Sediment archives
- Backup snapshots

Clause tags:
- `memory and continuity split`
- `subsurface`
- `sensory split`

## 5. Evolutionary Systems

Owns:
- Fail-point training
- Lesson planning
- Code mutation
- Manual-code assimilation
- Lineage journaling
- Distillation of temporal residue

Key modules:
- `aurora_dream_trainer.py`
- `aurora_code_evolution_stack.py`
- `aurora_internal/aurora_code_mutation_operators.py`
- `aurora_internal/aurora_manual_code_lineage.py`
- `aurora_internal/aurora_live_lineage_journal.py`
- `aurora_metabolic_distiller.py`
- `run_gauntlet.py`
- `corpus_runner.py`
- `force_evolve.py`

Reads:
- Fail-ledger data
- Corpus sessions
- Mutation candidates
- Code state
- Training outcomes

Writes:
- `fail_points.json`
- Retained learnings
- Distillation archives
- Lineage journal events
- Mutation traces

Clause tags:
- `subsurface`
- `evolution and repair routing`
- `DCE pressure selection`

## 6. Adaptive Systems

Owns:
- Output pipelines
- Articulation
- Behavior selection
- Interaction crystal promotion and collapse
- Surface-facing response shaping

Key modules:
- `aurora_interaction_engine.py`
- `aurora_interaction_processing.py`
- `aurora_internal/aurora_surface_dispatcher.py`
- `aurora_internal/aurora_response_pressure_tuner.py`
- `aurora_reflexive_interpreter.py`
- `aurora_grammar_engine.py`
- `aurora_state_voice.py`
- `aurora_telemetry.py`
- `aurora_room.py`
- `aurora_surface_daemon.py`

Reads:
- Turn telemetry
- Interaction memory
- Pressure signals
- Language state
- User utterances

Writes:
- Response drafts
- Interaction nodes
- Telemetry
- Dispatch state
- Surface voice output

Clause tags:
- `surface processing law`
- `DCE bridge`
- `room split`

## 7. Learning Pipeline - Active Acquisition

Owns:
- Study cycles
- Socializing
- Exploration
- Browser outreach
- Live vision intake
- Self-play
- Intentional probing
- Consolidation

Key modules:
- `aurora_gpt_learning_session.py`
- `corpus_runner.py`
- `aurora_explore.py`
- `aurora_browser_agent.py`
- `aurora_live_vision.py`
- `aurora_daemon.py`
- `run_gpt_session.py`
- `seed_sensory_crystals.py`
- `aurora_subsurface_daemon.py`

Reads:
- Pressure ontology
- Fail ledgers
- OETS
- Runtime state
- Sensory snapshots
- Journals
- Browser outcomes

Writes:
- Exploration logs
- Session transcripts
- Journal updates
- Sensory crystals
- Consolidated learnings

Clause tags:
- `room split`
- `memory and continuity`
- `evolution/repair routing`
- `DCE bridge`

## Notes

- `aurora_strata` is the experimental dual-strata branch.
- `aurora.py`, `aurora_consciousness_engine.py`, `aurora_dimensional_systems.py`, `aurora_expression_perception.py`, `aurora_internal/aurora_identity_persistence.py`, and `aurora_internal/aurora_understanding_contract.py` are the main anchors.
- `aurora_strata` was treated as excluded from the offload audit, as requested.
