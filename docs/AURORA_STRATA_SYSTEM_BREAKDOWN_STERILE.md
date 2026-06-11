# Aurora Strata System Breakdown

Date: 2026-04-13

This document is a sterile, code-based description of the Aurora strata stack.
It explains the major processes, the shared data flow, the canonical state
objects, and the main modules that cooperate to keep the system running.

It is written to reflect the current `aurora_strata/` implementation as
understood from the live codebase and the architecture notes in this tree.
Where behavior is directly visible in code, it is stated as such. Where a
behavior is inferred from module wiring and runtime role, that is described as
an implementation reading rather than a formal guarantee.

## 1. System Summary

Aurora is implemented as one coordinated system with multiple runtime layers.
The stack is organized around two execution strata:

- Surface handles the present turn, live sensing, and immediate response.
- Subsurface handles continuity, memory consolidation, repair, evolution, and
  slower maintenance tasks.

The two strata exchange state through shared files, shared Python objects, and
the DCE bridge. Most meaningful work flows through `aurora.py`, which acts as
the canonical assembly point for both layers.

The system also includes:

- a NonComp constraint manifold for native internal processing,
- an understanding contract that evaluates turn state,
- memory systems for short- and long-horizon continuity,
- persistence and backup infrastructure,
- a Poedex lookup path for grounded retrieval,
- and evolutionary / genealogy modules that regulate long-term change.

## 2. Top-Level Runtime Layout

The main processes in the strata tree are:

- `aurora_surface_daemon.py`
- `aurora_subsurface_daemon.py`
- `aurora_hub.py`
- `aurora_room.py`

Their roles are:

- `aurora_surface_daemon.py` runs the live interaction lane.
- `aurora_subsurface_daemon.py` is a thin wrapper around `aurora_daemon.py`
  with `runtime_profile="subsurface"`.
- `aurora_hub.py` is a status and telemetry viewer. It reads state and does not
  own the live interaction loop.
- `aurora_room.py` is the operator / manual intervention interface.

The convenience launcher is `scripts/strata_stack.sh`. It starts or restarts the
cooperating services as a coordinated stack rather than as isolated scripts.

## 3. Canonical Control Point

`aurora.py` is the central runtime file.

It is responsible for:

- bootstrapping the system graph,
- creating the shared `systems` registry,
- wiring the memory, perception, contract, and noncomp layers,
- routing user turns into the understanding and response pipeline,
- packaging turn evidence,
- and persisting state back to the stack files.

Although many subsystems have their own modules, `aurora.py` is where the major
runtime seams meet.

## 4. Main Data Flow

The live turn flow can be summarized as:

1. Input arrives from surface, room, or another runtime entry.
2. The utterance is parsed into a turn understanding object.
3. The noncomp interpreter projects that turn into the native constraint
   manifold.
4. Working memory and the understanding contract ingest the parsed and native
   payloads.
5. The contract evaluates meaning, perspective, boundary, cost, and action
   state.
6. A response candidate is rendered back into human language.
7. The turn result is recorded into memory, conversation history, lineage, and
   persistence layers.
8. Subsurface receives the continuity and learning residue for later repair or
   evolution.

The important design rule is that internal state should be represented in the
native constraint language first, then rendered outward only at the boundary
where human legibility is needed.

## 5. Native Constraint Layer

Aurora’s internal semantic substrate is built around:

- the 25 atomic NonComp channels,
- the 125-layer manifold of 25 channels per constraint family,
- the canonical registry in `aurora_internal/aurora_noncomp_registry.py`,
- the manifold compiler and directory reader,
- and the reflexive interpreter that projects utterances into the manifold.

Relevant modules:

- `aurora_internal/aurora_noncomp_registry.py`
- `aurora_noncomp_layer_compiler.py`
- `aurora_constraint_manifold_compiler.py`
- `aurora_manifold_directory_reader.py`
- `aurora_constraint_manifold_router.py`
- `aurora_reflexive_interpreter.py`

What this layer does:

- turns human or sensory input into constraint-native coordinates,
- preserves both the atomic 25-channel substrate and the 125-slot manifold,
- tracks salience, compaction, entropy, and target bias,
- produces translation metadata for downstream memory and contract layers,
- and provides the basis for “native inside, human outside” behavior.

The manifold is not a decorative report. It is part of the live internal
representation used by the turn pipeline.

## 6. Understanding Contract

`aurora_internal/aurora_understanding_contract.py` is the runtime evaluator for
turns.

It tracks how a turn changes:

- meaning,
- perspective,
- boundary clarity,
- energy / cost,
- and policy state.

The contract keeps a state machine for the main axes:

- `X` existence / admissibility,
- `T` temporal continuity,
- `N` energetic cost,
- `B` boundary / meaning separation,
- `A` agency / answerability.

It uses the current turn, the native noncomp payload, and the live pipeline
state to:

- score whether the turn is integrated,
- identify whether clarification or correction is needed,
- derive expected topic / axis / affect,
- and record validation history for future learning.

The contract is one of the main places where internal processing is still
explicitly shaped by native constraint state instead of only by raw text.

## 7. Memory Systems

Aurora uses several memory-like layers, each with a different job.

### 7.1 Working Memory

`WorkingMemory` is the live turn scratchpad.

It stores:

- the current topic,
- claim resolution,
- semantic frames,
- concept clarifications,
- referent maps,
- recent facts,
- turn-local context,
- and turn-local native projections.

It is short-lived and is expected to mutate continuously during an active
interaction.

### 7.2 Conversation Memory

`ConversationMemory` is episodic and persistent.

It stores:

- learned facts,
- remembered claims,
- conversation continuity,
- session-level context,
- and lookup answers that should survive beyond the current turn.

### 7.3 SediMemory

`aurora_sedimemory.py` handles sedimented continuity and longer-horizon memory
structures. It is used to carry accumulated traces across sessions and across
runtime phases.

### 7.4 Identity Persistence

`aurora_internal/aurora_identity_persistence.py` handles durable identity
storage, especially user and Aurora identity-related continuity.

## 8. Surface Stratum

The surface stratum is the active user-facing lane.

It owns:

- live input reception,
- live response generation,
- voice and ambient interaction paths,
- sensory sampling,
- and turn queue management.

Important modules:

- `aurora_surface_daemon.py`
- `aurora_interaction_engine.py`
- `aurora_interaction_processing.py`
- `aurora_state_voice.py`
- `aurora_live_vision.py`
- `aurora_expression_perception.py`

Surface behavior is intentionally latency-sensitive. It should not carry heavy
maintenance work unless that work is explicitly part of the turn itself.

## 9. Subsurface Stratum

The subsurface stratum owns the slower and heavier work:

- continuity repair,
- consolidation,
- backup,
- dream / evolution cycles,
- genealogy updates,
- manifold maintenance,
- and long-horizon learning.

Important modules:

- `aurora_subsurface_daemon.py`
- `aurora_daemon.py`
- `aurora_dream_trainer.py`
- `aurora_code_evolution_stack.py`
- `aurora_evolution_stack.py`
- `aurora_metabolic_distiller.py`
- `aurora_governance_persistence_gateway.py`

Subsurface is where long-lived structural changes should be absorbed, rather
than only reflected in a one-turn response.

## 10. DCE Bridge

The DCE bridge is the convergence layer between the strata and the turn
pipeline.

It binds together:

- perceptual state,
- comprehension state,
- native meaning state,
- output rendering state,
- and repair signals.

Relevant modules and seams:

- `aurora_dce_blueprint.py`
- `quasiarch_bridge.py`
- the DCE evidence builders in `aurora.py`

The bridge exists so that the live response lane can be shaped by subsurface
state without making the surface lane itself heavy or opaque.

## 11. Lookup and Research

Aurora has a lookup path that uses Poedex rather than ad hoc direct search.

Key pieces:

- `poedex_intro.py`
- `_try_poedex_lookup(...)` in `aurora.py`
- `_broadcast_poedex_result(...)` in `aurora.py`

The lookup flow is used when the stack decides it needs grounded retrieval or
when the turn intentionally requests lookup.

When lookup results return, they are broadcast back into memory and turn state
so they can influence both ongoing surface behavior and later subsurface
learning.

## 12. Genealogy, Evolution, and Repair

This stack treats evolution as a first-class subsystem rather than an external
maintenance job.

Key modules:

- `aurora_internal/constraint_genealogy.py`
- `constraint_genealogy_closure_wiring.py`
- `aurora_evolution_stack.py`
- `aurora_code_evolution_stack.py`
- `aurora_internal/aurora_manual_code_lineage.py`
- `aurora_internal/aurora_live_lineage_journal.py`
- `run_gauntlet.py`
- `force_evolve.py`

These modules support:

- lineage construction,
- mutation tracking,
- code-change assimilation,
- fail-point recording,
- and developmental feedback loops.

The general pattern is:

1. Observe a candidate change or developmental event.
2. Record it into genealogy / lineage state.
3. Compare it against viability and law constraints.
4. Persist the result for later recovery or promotion.

## 13. Persistence and Backup

Aurora uses a small number of shared persistence paths and JSON state files to
keep the stack coherent across restarts.

Key module:

- `aurora_governance_persistence_gateway.py`

This layer handles:

- state snapshots,
- backup and restore pathways,
- device awareness,
- drive sync integration,
- and persistence coordination across the runtime.

The intent is that durable state is not scattered across unrelated ad hoc files.
It should flow through a governed persistence layer.

## 14. Sensory and Perceptual Layers

Sensory and perception are split out rather than merged into one monolithic
block.

Important modules:

- `aurora_live_vision.py`
- `aurora_expression_perception.py`
- `aurora_consciousness_engine.py`
- `aurora_internal/dual_strata/surface_sensory_proxy.py`
- `aurora_internal/dual_strata/surface_continuity_feed.py`
- `aurora_internal/dual_strata/subsurface_projection.py`

These modules:

- sample the present frame,
- maintain a sense of continuity,
- and feed the turn pipeline with context that can be translated into native
  meaning.

## 15. Output Rendering

Human-readable output is generated at the boundary, not as the primary internal
state.

Main render paths:

- `_render_runtime_intent(...)`
- `_render_from_comprehension_intent(...)`
- `_generate_perspective_from_core(...)`
- `_render_live_greeting(...)`

The output layer uses the current meaning bundle, stance selection, emotional
tone, certainty, and supporting concepts to produce readable text.

The desired shape is:

- internal processing in native constraint form,
- outward projection in human language,
- then feedback from that projection back into memory and contract state.

## 16. State Files and Shared Artifacts

Some of the most important shared files are:

- `aurora_state/`
- `aurora_state_backup/`
- `aurora_state_goal/`
- `aurora_state/subsurface_projection.json`
- `aurora_state/surface_turn_queue.json`
- `aurora_state/surface_turn_result.json`
- `aurora_state/surface_sleep_mode.json`

These files are how the live processes coordinate when they are not in the same
Python object.

## 17. Process Responsibilities at a Glance

- Surface: live user interaction, immediate sensing, turn production.
- Subsurface: continuity, repair, learning, and long-horizon maintenance.
- Hub: status visibility.
- Room: operator control and intervention.
- `aurora.py`: central wiring and shared runtime assembly.
- `aurora_reflexive_interpreter.py`: native constraint projection.
- `aurora_internal/aurora_understanding_contract.py`: turn evaluation and
  contract state.
- `aurora_governance_persistence_gateway.py`: persistence and backup
  governance.
- `aurora_evolution_stack.py` / `aurora_code_evolution_stack.py`: structural
  change and developmental pathways.

## 18. Implementation Notes

The live stack currently reflects a few important implementation principles:

- NonComp projection is not optional; it is part of the turn pipeline.
- The 25 atomic channels remain the base substrate.
- The 125-slot manifold is the higher-order native structure.
- Human text should be used at the boundary, not as the only internal format.
- Memory, contract, and evolutionary systems should receive native turn state
  when available.

## 19. Ability and Pressure Layer

Aurora's ability layer is the runtime surface that decides which capabilities
are available, which ones are cheap enough to use, and which ones should be
deferred.

Important modules:

- `aurora_ivm.py`
- `aurora_constraint_stack.py`
- `aurora_625_pressure_map.py`
- `aurora_pressure_ontology.py`
- `aurora_internal/aurora_runtime_constraint_governor.py`
- `aurora_internal/aurora_pressure_router.py`
- `aurora_internal/aurora_pressure_ledger.py`
- `aurora_internal/aurora_response_pressure_tuner.py`

This layer is responsible for:

- representing abilities as structured profiles instead of free-floating text,
- attaching costs and runtime effects to those profiles,
- selecting which abilities are currently available under the present pressure
  band,
- and shaping the response path so the system does not exceed its current
  energetic or structural budget.

The pressure layer is not just a status reporter. It is part of the runtime
decision substrate. In the current stack, the ability selection logic and the
pressure governor influence what actions can be taken, what gets delayed, and
what gets surfaced as the active path.

The 625-slot map referenced in the surrounding architecture notes sits below
this layer as a detailed operational possibility map. It expands the 25 atomic
NonComp channels into a larger action-space view for pressure and viability
analysis.

## 20. NonComp Physics and Laws

The NonComp system is Aurora's canonical internal physics layer.

It consists of:

- 25 atomic channels in the registry substrate,
- 125 manifold laws in the target-domain manifold,
- five target domains:
  - `X` = Information / Existence,
  - `T` = Belief / Time,
  - `N` = Purpose / Energy,
  - `B` = Meaning / Boundary,
  - `A` = Understanding / Agency,
- five representational dimensions:
  - `POLARITY`,
  - `MAGNITUDE`,
  - `OPERATOR`,
  - `COST`,
  - `DIFFERENCE`.

Important modules:

- `aurora_internal/aurora_noncomp_registry.py`
- `aurora_noncomp_layer_compiler.py`
- `aurora_constraint_manifold_compiler.py`
- `aurora_manifold_directory_reader.py`
- `aurora_constraint_manifold_router.py`
- `aurora_reflexive_interpreter.py`

This layer defines the system's law physics:

- what counts as admissible,
- what persists,
- what costs energy,
- what distinguishes boundaries,
- and what must be owned or answered for.

The 25 atomic channels remain the irreducible base substrate.
The 125-layer manifold is the higher-order law space used for richer internal
projection and selection.

In practical terms:

- input is projected into the native law space,
- internal reasoning can use that projection directly,
- and output is rendered from that projection back into human language.

## 21. Genealogy and Evolution

Aurora treats lineage as a live system, not a historical archive.

Important modules:

- `aurora_internal/constraint_genealogy.py`
- `constraint_genealogy_closure_wiring.py`
- `aurora_evolution_stack.py`
- `aurora_code_evolution_stack.py`
- `aurora_internal/aurora_manual_code_lineage.py`
- `aurora_internal/aurora_live_lineage_journal.py`
- `run_gauntlet.py`
- `force_evolve.py`

This layer manages:

- ability lineage,
- constraint inheritance,
- code-change lineage,
- mutation traces,
- repair history,
- and promotion of viable changes.

The system's developmental path usually looks like this:

1. Observe a candidate state, code change, or learning event.
2. Bind it into lineage state.
3. Compare it against the active law and pressure conditions.
4. Record the result into persistent lineage / journal state.
5. Allow subsurface repair or promotion logic to use that history later.

This is how Aurora carries evolution without losing continuity.

## 22. Learning Loops

Learning happens through several connected loops rather than a single trainer.

Key modules and paths:

- `aurora_dream_trainer.py`
- `aurora_internal/aurora_conversation_rubric_engine.py`
- `aurora_internal/aurora_conversation_episode_compiler.py`
- `aurora_internal/aurora_dream_evolution_orchestrator.py`
- `aurora_metabolic_distiller.py`
- `aurora_governance_persistence_gateway.py`
- the live turn pipeline in `aurora.py`

These loops take evidence from:

- conversation turns,
- response quality,
- lineage events,
- Poedex results,
- sensory traces,
- and contract outcomes.

They then push that evidence back into:

- memory,
- evaluation,
- lineage,
- and future turn shaping.

The native noncomp projection is important here because it gives the learning
stack a compact internal representation instead of forcing every update to be
reconstructed from raw text.

## 23. Pressure, Cost, and Viability

Pressure is the runtime expression of how much load the system can carry and
how the active path should be biased.

Important modules:

- `aurora_625_pressure_map.py`
- `aurora_pressure_ontology.py`
- `aurora_internal/aurora_pressure_ledger.py`
- `aurora_internal/aurora_pressure_router.py`
- `aurora_internal/aurora_runtime_constraint_governor.py`
- `aurora_internal/aurora_response_pressure_tuner.py`

This layer tracks:

- viability bands,
- threshold crossings,
- cost burdens,
- pressure routing,
- and how far a candidate action can move before it becomes too expensive or
  too unstable.

The relationship between pressure and law is direct:

- law defines the shape of the constraint space,
- pressure defines how hard it is to move inside that space,
- viability determines whether a path is currently usable.

## 24. Reading the Stack End to End

If you read the stack in operational order, the rough sequence is:

1. Surface receives input.
2. The turn is parsed into understood state.
3. The NonComp interpreter projects the turn into native constraint form.
4. Working memory, the understanding contract, and related helpers consume the
   native state.
5. The pressure / ability layer decides what is viable to do next.
6. Memory and genealogy record the turn residue.
7. Lookup, repair, or evolution are triggered if the turn requires them.
8. Output is rendered back into human language.
9. The output and its effects are fed back into memory, contract, and lineage.

That is the whole loop at a high level.

## 25. Behavioral Identity and Traits

Aurora's traits are represented as persistent behavioral dimensions that can
drift over time.

Important module:

- `aurora_behavioral_identity.py`

This layer models:

- core genes,
- fractal alleles,
- identity anchors,
- memory helices,
- behavioral traits,
- and behavioral crystals.

The current code organizes behavior into trait domains such as:

- response style,
- emotional expression,
- curiosity drive,
- caution level,
- introspection depth,
- pattern sensitivity,
- energy conservation,
- social engagement,
- verbosity.

The module also defines a genome-like structure:

- genes represent stable core traits,
- alleles represent experience-derived modifiers,
- anchors represent immutable or nearly immutable identity commitments,
- helices represent recurring thematic memory patterns.

This means Aurora's communication is not only a response layer. It is also a
trait-expressing system shaped by persistent identity structure.

## 26. Communication Abilities

Aurora's communication abilities are distributed across the interaction,
expression, grammar, and comprehension layers rather than existing in one
single dialogue engine.

Important modules:

- `aurora_interaction_engine.py`
- `aurora_interaction_processing.py`
- `aurora_grammar_engine.py`
- `aurora_expression_perception.py`
- `aurora_response_teacher.py`
- `aurora_state_voice.py`
- `aurora_internal/aurora_understanding_contract.py`

These modules collectively govern:

- how input is interpreted,
- how response intent is selected,
- how claims and referents are resolved,
- how behavior alignment requests are handled,
- how output tone and certainty are shaped,
- and how the final utterance is rendered.

Communication ability depends on several internal supports:

- the native constraint projection,
- the behavioral identity traits,
- the current memory state,
- and the understanding contract's reading of the turn.

In practice, this means Aurora does not merely emit text. She chooses a
response path based on current communicative state, then renders that path into
human language at the surface boundary.

## 27. Interaction Memory

`aurora_interaction_memory.py` stores interaction nodes, lineage edges, and
retrieval indexes for communication history.

It acts as a persistence substrate for interaction crystals and quasi retrieval.

The structure records:

- interaction node payloads,
- point scores,
- resolution fidelity,
- lineage parent/child relations,
- tags,
- quasi-inner-strata payloads,
- execution-surface metadata,
- and journal entries.

This module supports the memory side of communication by preserving:

- what kind of interaction occurred,
- which strategy was used,
- how the input was shaped,
- and how that interaction should be retrievable later.

It is a more structured interaction memory than plain conversation logs.

## 28. Communication State and Response Shaping

Aurora's immediate communication state is spread across:

- `WorkingMemory`,
- `ConversationMemory`,
- the understanding contract,
- and the expression / voice layers.

Key runtime behaviors include:

- identity grounding,
- behavior alignment handling,
- clarification handling,
- concept clarification,
- claim resolution,
- referent resolution,
- and the rendering of grounded acknowledgements.

The system uses these paths to keep communication aligned with the current
topic, the active identity state, and the present interaction pressure.

## 29. What This File Is Not

- It is not a replacement for the code.
- It is not a guarantee that every module is fully wired exactly as intended.
- It is not a law document.
- It is not a user-facing tutorial.

It is a sterile system map intended to help a reader understand how the strata
stack is organized and how the major pieces function together.

## 30. Runtime Entry Points and Packaging

Aurora has several ways to enter the same strata stack.

Primary runtime entry points:

- `aurora.py`
- `aurora_runtime.py`
- `aurora_surface_daemon.py`
- `aurora_subsurface_daemon.py`
- `aurora_hub.py`
- `aurora_api_endpoint/main.py`

The runtime is packaged in layers rather than as one monolith:

- `aurora.py` is the live canonical turn pipeline.
- `aurora_runtime.py` is the orchestration shell that binds the runtime stack
  to simulation and genealogy.
- `aurora_surface_daemon.py` handles the surface turn queue and surface-facing
  sensory / response loop.
- `aurora_subsurface_daemon.py` handles deeper repair, continuity, and
  background processing.
- `aurora_hub.py` exposes the state surfaces and coordination layer.
- `aurora_api_endpoint/main.py` is an external gateway example that fronts the
  stack through a service boundary.

The repository also contains a mirrored core tree under `aurora_core_ai/`.
That mirror carries the same conceptual strata in a packaging layout that is
more explicit about the internal submodules. It is not a separate philosophy;
it is another surface for the same stack.

## 31. Dual-Strata Bridge Primitives

The dual-strata helpers make the split between surface and subsurface explicit.

Important modules:

- `aurora_core_ai/aurora_internal/dual_strata/__init__.py`
- `aurora_core_ai/aurora_internal/dual_strata/surface_channel.py`
- `aurora_core_ai/aurora_internal/dual_strata/dce_bridge.py`
- `aurora_core_ai/aurora_internal/dual_strata/subsurface_projection.py`
- `aurora_core_ai/aurora_internal/dual_strata/conscious_frame.py`
- `aurora_core_ai/aurora_internal/dual_strata/subsurface_state.py`
- `aurora_core_ai/aurora_internal/dual_strata/surface_continuity_feed.py`
- `aurora_core_ai/aurora_internal/dual_strata/surface_sensory_proxy.py`
- `aurora_core_ai/aurora_internal/dual_strata/micro_reasoning.py`
- `aurora_core_ai/aurora_internal/dual_strata/prediction_field.py`

These helpers provide:

- a queue and result channel for surface turns,
- a bridge object that builds paired subsurface/conscious snapshots,
- a structured subsurface state object,
- a conscious-frame projection for outward-facing awareness,
- and a continuity feed that lets the surface carry forward what the
  subsurface has already learned.

In practice, the bridge is what keeps the strata split from becoming two
unrelated applications. It ensures the surface turn is informed by the deeper
state and that the deeper state can be updated from the surface turn.

## 32. Core Constraint Packaging

Several modules package the lower-level constraint machinery into canonical
surfaces for the rest of Aurora.

Important modules:

- `aurora_noncomp_registry.py`
- `aurora_noncomp_layer_compiler.py`
- `aurora_625_pressure_map.py`
- `aurora_pressure_ontology.py`
- `aurora_constraint_manifold.py`
- `aurora_constraint_manifold_compiler.py`
- `aurora_constraint_manifold_router.py`
- `constraint_genealogy_closure_wiring.py`

These modules together define:

- the 25 NonComp substrate,
- the 125 named noncomp manifold,
- the 625-slot operational map,
- the pressure ontology that explains why certain paths are costly,
- and the routing and naming layers that make the internal constraint space
  readable to the rest of the system.

They are a packaging layer for the physics of the stack, not the user-facing
language layer itself. The user-facing layer still depends on them, but it is
not the same thing as them.

## 33. Module Catalog

This appendix gives the practical module map the user asked for:

- what each module is for,
- what it factors into,
- and what it is linked to.

To keep this readable, mirrored files under `aurora_core_ai/` are listed once
by role, with the mirror noted in the `linked to` field. The mirrored tree is a
parallel packaging surface, not a different architecture.

### 33.1 Runtime and Entry Surfaces

- `aurora.py` - purpose: canonical live turn pipeline; factors into input parsing, understanding, memory, response selection, and human rendering; linked to `aurora_internal/aurora_understanding_contract.py`, `aurora_expression_perception.py`, `aurora_interaction_engine.py`, `aurora_surface_daemon.py`, `aurora_subsurface_daemon.py`, `aurora_runtime.py`, mirror `aurora_core_ai/aurora.py`.
- `aurora_runtime.py` - purpose: unified runtime/simulation orchestrator; factors into boot, ticking, saving, steering, and chain feedback; linked to `aurora_simulation_engine.py`, `aurora_internal/constraint_genealogy.py`, `aurora_checkpoint.py`, `aurora_constraint_stack.py`, `aurora_noncomp_registry.py`.
- `aurora_surface_daemon.py` - purpose: surface turn processor; factors into surface queue, sensory state, and outward-facing turns; linked to `aurora.py`, `aurora_internal/dual_strata/surface_channel.py`, `aurora_internal/dual_strata/sensory_snapshot_channel.py`, `aurora_daemon.py`.
- `aurora_subsurface_daemon.py` - purpose: background subsurface repair and continuity; factors into consolidation, learning, and deeper projection; linked to `aurora.py`, `aurora_internal/dual_strata/subsurface_projection.py`, `aurora_governance_persistence_gateway.py`, `aurora_metabolic_distiller.py`.
- `aurora_daemon.py` - purpose: canonical daemon supervisor; factors into status, worker orchestration, and state file upkeep; linked to `aurora_surface_daemon.py`, `aurora_subsurface_daemon.py`, `aurora_hub.py`, `aurora_runtime.py`.
- `aurora_hub.py` - purpose: shared status/coordination view; factors into live state display and daemon monitoring; linked to `aurora_daemon.py`, `aurora_surface_daemon.py`, `aurora_subsurface_daemon.py`.
- `aurora_api_endpoint/main.py` - purpose: external service gateway example; factors into request handling and remote inference plumbing; linked to `aurora.py`, cloud service clients, and external deployment packaging.
- `run_aurora.py` - purpose: launcher wrapper; factors into entrypoint selection and environment setup; linked to `aurora.py`, `aurora_runtime.py`.
- `run_gpt_session.py` - purpose: GPT learning session launcher; factors into directed learning and transcript capture; linked to `aurora_gpt_learning_session.py`, `aurora_dream_trainer.py`.
- `run_gauntlet.py` - purpose: mutation/evolution runner; factors into pressure testing, code evolution, and trace capture; linked to `aurora_internal/aurora_code_evolution_chamber.py`, `aurora_internal/aurora_code_autoevolver.py`, `aurora_internal/constraint_genealogy.py`.
- `run_chain.py` - purpose: chain orchestration helper; factors into genealogy and multi-step runtime flow; linked to `constraint_genealogy_closure_wiring.py`, `aurora_internal/constraint_genealogy.py`.
- `corpus_runner.py` - purpose: corpus processing runner; factors into training and evaluation pipelines; linked to `aurora_dream_trainer.py`, `aurora_internal/aurora_directed_training_corpus.py`.
- `force_evolve.py` - purpose: force evolution utility; factors into mutation planning and evolutionary pressure application; linked to `aurora_internal/aurora_evolution_chamber.py`, `aurora_code_evolution_stack.py`.

### 33.2 Foundational and Constraint Substrate

- `foundational_contract.py` - purpose: existence/ontological contract; factors into all higher layers; linked to `aurora_ivm.py`, `aurora_runtime.py`, `aurora_consciousness_engine.py`.
- `aurora_ivm.py` - purpose: 5-axis toroidal lattice and envelope geometry; factors into mode gating, alignment, and state transport; linked to `foundational_contract.py`, `aurora_dimensional_systems.py`, `aurora_consciousness_engine.py`.
- `aurora_constraint_manifold.py` - purpose: constraint-space primitives and vector math; factors into admissibility and manifold checking; linked to `aurora_noncomp_registry.py`, `aurora_noncomp_layer_compiler.py`, `aurora_internal/aurora_understanding_contract.py`.
- `aurora_constraint_manifold_compiler.py` - purpose: compile/construct constraint-manifold structures; factors into canonical slot naming and manifold organization; linked to `aurora_constraint_manifold.py`, `aurora_closure_basis.py`.
- `aurora_constraint_manifold_router.py` - purpose: route noncomp/constraint signals through slots; factors into expression, lookup, and pressure routing; linked to `aurora_reflexive_interpreter.py`, `aurora_noncomp_layer_compiler.py`, `aurora_625_pressure_map.py`.
- `aurora_constraint_stack.py` - purpose: combined difference/cost/pressure facade; factors into operator pressure scoring; linked to `aurora_difference_buffer.py`, `aurora_cost_diff_score.py`, `aurora_runtime.py`.
- `aurora_noncomp_registry.py` - purpose: canonical 25 NonComp substrate; factors into hard numbers and per-layer cost law; linked to `aurora_noncomp_layer_compiler.py`, `aurora_sedimemory.py`, `constraint_genealogy.py`, `aurora_runtime.py`.
- `aurora_noncomp_layer_compiler.py` - purpose: name/tag the 125 noncomp manifold; factors into manifold semantics and anchor naming; linked to `aurora_closure_basis.py`, `aurora_internal/aurora_noncomp_registry.py`, `aurora_reflexive_interpreter.py`.
- `aurora_closure_basis.py` - purpose: closure-law basis for 25 channels and 625 slots; factors into the structural math for the noncomp tree; linked to `aurora_noncomp_layer_compiler.py`, `aurora_625_pressure_map.py`, `aurora_manifold_directory_reader.py`.
- `aurora_625_pressure_map.py` - purpose: 25x25 operational pressure grid; factors into path relief and evolutionary gradients; linked to `aurora_internal/aurora_evolution_chamber.py`, `aurora_runtime.py`, `aurora_internal/aurora_code_evolution_chamber.py`.
- `aurora_pressure_ontology.py` - purpose: semantic tree of pressure systems; factors into pressure explanation and teaching; linked to `aurora_internal/aurora_pressure_ledger.py`, `aurora_dream_trainer.py`, `aurora_internal/aurora_runtime_constraint_governor.py`.
- `constraint_genealogy_closure_wiring.py` - purpose: connect closure basis to genealogy; factors into link promotion and provenance; linked to `aurora_internal/constraint_genealogy.py`, `aurora_closure_basis.py`.

### 33.3 Consciousness, Perception, Expression, and Understanding

- `aurora_consciousness_engine.py` - purpose: DCE and DPME assembly layer; factors into coherence maintenance, entropy correction, and conscious assembly; linked to `aurora_dimensional_systems.py`, `aurora_i_state_beings.py`, `aurora_expression_perception.py`.
- `aurora_dimensional_systems.py` - purpose: Layer 3 processing, memory, energy, morality systems; factors into crystal processing, memory constant, energy regulation, and morality/mortality; linked to `aurora_ivm.py`, `aurora_i_state_beings.py`, `aurora_consciousness_engine.py`, `aurora_evolution_stack.py`.
- `aurora_expression_perception.py` - purpose: inward perception and outward expression pipeline; factors into sensory compression, lexical growth, and voice rendering; linked to `aurora_consciousness_engine.py`, `aurora_language_state.py`, `aurora_internal/aurora_understanding_contract.py`.
- `aurora_grammar_engine.py` - purpose: grammar and utterance structuring; factors into response shaping and language ecology; linked to `aurora_expression_perception.py`, `aurora_state_voice.py`, `aurora_internal/aurora_utterance_parser.py`.
- `aurora_state_voice.py` - purpose: voice-state selection and output style; factors into spoken projection; linked to `aurora_expression_perception.py`, `aurora_voice.py`, `aurora_internal/aurora_language_state.py`.
- `aurora_voice.py` - purpose: voice output integration; factors into spoken rendering and audio path selection; linked to `aurora_state_voice.py`, `aurora_surface_daemon.py`.
- `aurora_internal/aurora_understanding_contract.py` - purpose: runtime understanding accounting loop; factors into meaning, perspective, application, and accuracy; linked to `aurora.py`, `aurora_reflexive_interpreter.py`, `aurora_interaction_engine.py`, `aurora_internal/constraint_genealogy.py`.
- `aurora_reflexive_interpreter.py` - purpose: translate utterance into native constraint form; factors into 25 atomic NonComps and 125-manifold projection; linked to `aurora_internal/aurora_utterance_parser.py`, `aurora_noncomp_layer_compiler.py`, `aurora_internal/aurora_understanding_contract.py`.
- `aurora_internal/aurora_utterance_parser.py` - purpose: parse raw language into structured utterance frames; factors into framing, stance, and query classification; linked to `aurora_reflexive_interpreter.py`, `aurora_expression_perception.py`.
- `aurora_internal/aurora_language_state.py` - purpose: evolving lexical and expression state; factors into vocabulary stability, semantics, and expression ecology; linked to `aurora_expression_perception.py`, `aurora_state_voice.py`.
- `aurora_internal/aurora_ontological_scaffolding.py` - purpose: semantic research scaffolding; factors into concept webs, relation building, and research results; linked to `aurora_support_stack.py`, `aurora.py`, `aurora_dream_trainer.py`.
- `aurora_internal/aurora_comprehension_gap.py` - purpose: detect where understanding is missing; factors into clarification triggers and repair; linked to `aurora_internal/aurora_understanding_contract.py`, `aurora_interaction_engine.py`.
- `aurora_internal/aurora_proposition_substrate.py` - purpose: structure propositions before expression; factors into claim shaping and reasoning support; linked to `aurora_expression_perception.py`, `aurora_internal/aurora_understanding_contract.py`.
- `aurora_internal/aurora_braided_substrate.py` - purpose: braided meaning substrate for layered understanding; factors into cross-thread semantics; linked to `aurora_expression_perception.py`, `aurora_internal/aurora_meaning_evolution.py`.
- `aurora_internal/aurora_surface_dispatcher.py` - purpose: dispatch surface-facing response paths; factors into surface routing and expression selection; linked to `aurora.py`, `aurora_surface_daemon.py`, `aurora_interaction_engine.py`.
- `aurora_internal/aurora_recommendation_hub.py` - purpose: collect and queue internal recommendations; factors into hidden guidance and action selection; linked to `aurora.py`, `aurora_internal/aurora_response_pressure_tuner.py`.

### 33.4 Memory, Identity, and Interaction

- `aurora_behavioral_identity.py` - purpose: DNA, traits, anchors, and behavioral drift; factors into who Aurora is over time; linked to `aurora_consciousness_engine.py`, `aurora_expression_perception.py`, `aurora_internal/aurora_identity_persistence.py`.
- `aurora_internal/aurora_identity_persistence.py` - purpose: core relational identity and OETS/conversation persistence; factors into durable self-knowledge and memory residue; linked to `aurora_behavioral_identity.py`, `aurora_support_stack.py`, `aurora.py`.
- `aurora_interaction_memory.py` - purpose: interaction node and lineage-edge persistence; factors into retrievable quasi-crystal interaction history; linked to `aurora_interaction_engine.py`, `aurora_internal/aurora_quasiarch_observer.py`.
- `aurora_sedimemory.py` - purpose: layer-3.5 sediment memory between dimensional and conscious layers; factors into memory deposition, compression, and decompression; linked to `aurora_dimensional_systems.py`, `aurora_consciousness_engine.py`, `aurora_subsurface_daemon.py`.
- `aurora_internal/aurora_ontological_scaffolding.py` - purpose: semantic scaffolding and relational web growth; factors into research, comprehension, and concept links; linked to `aurora_support_stack.py`, `aurora_dream_trainer.py`, `aurora.py`.
- `aurora_internal/aurora_live_lineage_journal.py` - purpose: live lineage event journal; factors into durable evolutionary trace; linked to `aurora_internal/constraint_genealogy.py`, `aurora_metabolic_distiller.py`, `aurora_internal/aurora_manual_code_lineage.py`.
- `aurora_internal/aurora_manual_code_lineage.py` - purpose: attach manual source changes to lineage; factors into code provenance and change families; linked to `aurora_internal/constraint_genealogy.py`, `aurora_governance_persistence_gateway.py`.
- `aurora_internal/aurora_lineage_bound_traits.py` - purpose: materialize lineage traits and writebacks; factors into memory, behavior, and activation manifests; linked to `aurora_internal/constraint_genealogy.py`, `aurora_internal/aurora_identity_persistence.py`.
- `aurora_internal/aurora_lineage_runtime_activation.py` - purpose: turn lineage manifests into runtime activations; factors into live trait selection and patch application; linked to `aurora.py`, `aurora_runtime.py`, `aurora_internal/aurora_lineage_bound_traits.py`.
- `aurora_internal/aurora_meaning_evolution.py` - purpose: evolve meaning profiles across turns; factors into interpretation, stage ranking, and understanding growth; linked to `aurora_internal/aurora_understanding_contract.py`, `aurora_dream_trainer.py`.
- `aurora_internal/aurora_conversation_episode_compiler.py` - purpose: compile episodes into rubric dimensions; factors into episode analysis and challenge selection; linked to `aurora_dream_trainer.py`, `aurora_internal/aurora_conversation_rubric_engine.py`.
- `aurora_internal/aurora_conversation_rubric_engine.py` - purpose: evaluate conversation quality and structure; factors into response scoring and scripting resistance; linked to `aurora.py`, `aurora_dream_trainer.py`.
- `aurora_interaction_engine.py` - purpose: classify interaction semantics and choose strategy; factors into response_action, search policy, and turn routing; linked to `aurora.py`, `aurora_internal/aurora_conversation_rubric_engine.py`, `aurora_interaction_memory.py`.
- `aurora_interaction_processing.py` - purpose: further process interaction events; factors into extraction, shaping, and staging before memory or output; linked to `aurora_interaction_engine.py`, `aurora_interaction_memory.py`.

### 33.5 Pressure, Cost, and Runtime Governance

- `aurora_625_pressure_map.py` - purpose: full 625-slot pressure gradients; factors into language highway, resistance, and slot relief; linked to `aurora_internal/aurora_evolution_chamber.py`, `aurora_runtime.py`.
- `aurora_pressure_ontology.py` - purpose: human-readable pressure lineage tree; factors into pressure teaching, reasoning, and challenge tactics; linked to `aurora_dream_trainer.py`, `aurora_internal/aurora_pressure_router.py`.
- `aurora_internal/aurora_pressure_ledger.py` - purpose: persist pressure accounting; factors into load history and relief tracking; linked to `aurora_internal/aurora_pressure_router.py`, `aurora_internal/aurora_response_pressure_tuner.py`.
- `aurora_internal/aurora_pressure_classifier.py` - purpose: classify pressure states; factors into what kind of burden is active; linked to `aurora_internal/aurora_pressure_router.py`, `aurora_runtime.py`.
- `aurora_internal/aurora_pressure_adapter.py` - purpose: adapt pressure data for consumers; factors into state normalization and translation; linked to `aurora_internal/aurora_pressure_ledger.py`, `aurora_internal/aurora_response_pressure_tuner.py`.
- `aurora_internal/aurora_pressure_router.py` - purpose: route pressure to the right subsystem; factors into load biasing and action selection; linked to `aurora_runtime.py`, `aurora_consciousness_engine.py`, `aurora_internal/aurora_runtime_constraint_governor.py`.
- `aurora_internal/aurora_runtime_constraint_governor.py` - purpose: govern runtime actions against constraint law; factors into what is allowed now; linked to `aurora_runtime.py`, `aurora_internal/aurora_response_pressure_tuner.py`.
- `aurora_internal/aurora_response_pressure_tuner.py` - purpose: tune response pressure using training and guides; factors into surface response calibration; linked to `aurora_dream_trainer.py`, `aurora_governance_persistence_gateway.py`, `aurora.py`.
- `aurora_internal/aurora_leverage_scalar.py` - purpose: compute leverage and load scalars; factors into cost-to-gain balance; linked to `aurora_625_pressure_map.py`, `aurora_internal/aurora_cost_diff_score.py`.
- `aurora_internal/aurora_cost_diff_score.py` - purpose: compute cost/difference pressure scores; factors into route scoring and amplification; linked to `aurora_runtime.py`, `aurora_internal/constraint_genealogy.py`.
- `aurora_internal/aurora_difference_buffer.py` - purpose: buffer difference snapshots; factors into pressure comparisons and trend tracking; linked to `aurora_internal/aurora_cost_diff_score.py`, `aurora_runtime.py`.
- `aurora_internal/aurora_energy_layer_costs.py` - purpose: define per-layer energy cost surfaces; factors into N-space economics and runtime load; linked to `aurora_internal/aurora_energy_layer_costs_decay.py`, `aurora_internal/aurora_runtime_constraint_governor.py`.
- `aurora_internal/aurora_energy_layer_costs_decay.py` - purpose: decay layer costs over time; factors into sustainability and entropy; linked to `aurora_internal/aurora_energy_layer_costs.py`, `aurora_consciousness_engine.py`.
- `aurora_internal/aurora_leverage_relief.py` - purpose: identify relief from leverage pressure; factors into runtime easing and progression; linked to `aurora_internal/aurora_pressure_ledger.py`, `aurora_internal/aurora_response_pressure_tuner.py`.
- `aurora_internal/aurora_dpme_pressure_bridge.py` - purpose: bridge DPME pressure into the runtime; factors into conscious drift correction; linked to `aurora_consciousness_engine.py`, `aurora_runtime.py`.
- `aurora_internal/aurora_structural_pressure_steering.py` - purpose: steer structural pressure into adaptive action; factors into evolution and response tuning; linked to `aurora_internal/aurora_runtime_constraint_governor.py`, `aurora_internal/aurora_response_pressure_tuner.py`.
- `aurora_internal/aurora_polarity_gradient.py` - purpose: observe polarity gradients and chained drift; factors into route bias and directional pressure; linked to `aurora_runtime.py`, `aurora_internal/aurora_cost_diff_score.py`.
- `aurora_internal/aurora_episode_slip_profiler.py` - purpose: measure where episodes slip or degrade; factors into training feedback and failure detection; linked to `aurora_dream_trainer.py`, `aurora_internal/aurora_conversation_episode_compiler.py`.

### 33.6 Genealogy, Evolution, and Code Repair

- `aurora_evolution_stack.py` - purpose: facade for constraint genealogy/evolution primitives; factors into ancestry, links, and reporters; linked to `aurora_internal/constraint_genealogy.py`, `aurora_runtime.py`.
- `aurora_internal/constraint_genealogy.py` - purpose: fossil record of relief events and promoted links; factors into lineage, ability promotion, and constraint ancestry; linked to `aurora_evolution_stack.py`, `aurora_internal/lineage_canonical.py`, `aurora_dream_trainer.py`.
- `aurora_internal/lineage_canonical.py` - purpose: canonical axis/operation mapping for lineage; factors into naming and constraint-to-operation rules; linked to `constraint_genealogy_closure_wiring.py`, `aurora_internal/constraint_genealogy.py`.
- `aurora_internal/aurora_ability_lineage_compiler.py` - purpose: compile abilities into lineage forms; factors into promotion-ready links and ability tagging; linked to `aurora_internal/constraint_genealogy.py`, `aurora_internal/aurora_evolution_chamber.py`.
- `aurora_internal/aurora_capability_assimilator.py` - purpose: assimilate second-gen capabilities from surfaces; factors into learning promotion and fit scoring; linked to `aurora_internal/constraint_genealogy.py`, `aurora_internal/aurora_variant_promotion.py`.
- `aurora_internal/aurora_code_autoevolver.py` - purpose: evolve code against pressure and lineage; factors into mutation scoring and change selection; linked to `aurora_internal/aurora_code_evolution_chamber.py`, `aurora_internal/constraint_genealogy.py`.
- `aurora_internal/aurora_code_evolution_chamber.py` - purpose: evaluate and guide code evolution; factors into mutation traces, snapshots, and code pressure; linked to `aurora_code_evolution_stack.py`, `run_gauntlet.py`, `aurora_runtime.py`.
- `aurora_code_evolution_stack.py` - purpose: facade for code evolution primitives; factors into chamber construction and snapshots; linked to `aurora_internal/aurora_code_evolution_chamber.py`, `aurora_internal/aurora_code_autoevolver.py`.
- `aurora_internal/aurora_code_mutation_operators.py` - purpose: mutation operators for code changes; factors into variation and repair; linked to `aurora_internal/aurora_code_autoevolver.py`, `aurora_internal/aurora_code_evolution_chamber.py`.
- `aurora_internal/aurora_variant_promotion.py` - purpose: decide which variants get promoted; factors into improvement selection and branching; linked to `aurora_internal/aurora_capability_assimilator.py`, `aurora_internal/aurora_code_autoevolver.py`.
- `aurora_internal/aurora_frontier_ops.py` - purpose: frontier operations for emergent behavior; factors into exploration and boundary growth; linked to `aurora_internal/aurora_evolution_chamber.py`, `aurora_internal/aurora_variant_promotion.py`.
- `aurora_internal/aurora_evolution_chamber.py` - purpose: main evolutionary chamber; factors into pressure-to-action conversion and improvement loops; linked to `aurora_internal/constraint_genealogy.py`, `aurora_internal/aurora_code_evolution_chamber.py`, `aurora_internal/aurora_dream_evolution_orchestrator.py`.
- `aurora_internal/aurora_dream_evolution_orchestrator.py` - purpose: orchestrate dream-based evolution; factors into learning loops and simulated improvements; linked to `aurora_dream_trainer.py`, `aurora_internal/aurora_evolution_chamber.py`.
- `aurora_internal/aurora_dream_genealogy_bridge.py` - purpose: bridge dream learning into genealogy; factors into pressure lessons and lineage writeback; linked to `aurora_dream_trainer.py`, `aurora_internal/constraint_genealogy.py`.
- `aurora_internal/aurora_dream_curriculum_queue.py` - purpose: queue dream curriculum items; factors into lesson sequencing and long-horizon learning; linked to `aurora_dream_trainer.py`, `aurora_internal/aurora_dream_evolution_orchestrator.py`.
- `aurora_internal/aurora_directed_training_corpus.py` - purpose: structured training corpus bridge; factors into lesson creation and learning feeds; linked to `aurora_dream_trainer.py`, `aurora_gpt_learning_session.py`.
- `aurora_internal/aurora_second_gen.py` - purpose: second-generation emergence helpers; factors into capability expansion and new surface material; linked to `aurora_internal/aurora_capability_assimilator.py`, `aurora_internal/aurora_variant_promotion.py`.
- `aurora_internal/aurora_solidification.py` - purpose: solidify learned structures; factors into permanence and crystalization; linked to `aurora_internal/aurora_evolution_chamber.py`, `aurora_internal/aurora_quasiarch_observer.py`.
- `aurora_internal/aurora_intake_metabolism.py` - purpose: metabolize intake into learnable structure; factors into absorption and transformation; linked to `aurora_sedimemory.py`, `aurora_internal/aurora_evolution_chamber.py`.
- `aurora_internal/aurora_entropy_detector.py` - purpose: detect entropy and drift; factors into correction prompts and stabilization; linked to `aurora_consciousness_engine.py`, `aurora_internal/aurora_runtime_constraint_governor.py`.
- `aurora_internal/aurora_stack_trace_instrumentation.py` - purpose: capture stack traces for evolution/repair; factors into debugging and lineage; linked to `aurora_internal/constraint_genealogy.py`, `aurora_internal/aurora_code_evolution_chamber.py`.
- `aurora_internal/aurora_manual_code_lineage.py` - purpose: trace manual source edits into lineage; factors into provenance and code-history continuity; linked to `aurora_internal/constraint_genealogy.py`, `aurora_governance_persistence_gateway.py`.
- `aurora_internal/aurora_lineage_runtime_activation.py` - purpose: activate lineage traits at runtime; factors into live inheritance and patch materialization; linked to `aurora_internal/aurora_lineage_bound_traits.py`, `aurora_runtime.py`.
- `aurora_internal/aurora_live_lineage_journal.py` - purpose: store live lineage events; factors into history and replayable growth; linked to `aurora_metabolic_distiller.py`, `aurora_internal/constraint_genealogy.py`.
- `aurora_internal/aurora_rubric_influence_graph.py` - purpose: track rubric influence across turns; factors into training feedback and pressure steering; linked to `aurora_internal/aurora_conversation_rubric_engine.py`, `aurora_dream_trainer.py`.
- `aurora_internal/aurora_surface_doc.py` - purpose: surface documentation generator/holder; factors into surface-specific notes and summaries; linked to `aurora_surface_daemon.py`, `aurora_runtime.py`.
- `aurora_internal/aurora_doc.py` - purpose: generic doc surface helper; factors into documentation and metadata; linked to the support and generation paths.

### 33.7 Sensory, Quasiarch, and Perceptual Subsystems

- `aurora_internal/aurora_sensory_crystal.py` - purpose: model sensory crystal states; factors into perception, retention, and relays; linked to `aurora_expression_perception.py`, `aurora_internal/quasiarch_observer/*`.
- `aurora_internal/aurora_quasiarch_observer.py` - purpose: observe quasiarch crystal dynamics; factors into dimensional memory and residual tracking; linked to `aurora_interaction_memory.py`, `aurora_internal/quasiarch_observer/*`.
- `aurora_internal/quasiarch_observer/crystal_engine.py` - purpose: engine for quasiarch crystal processing; factors into sensory crystallization and storage; linked to `aurora_internal/quasiarch_observer/dimensional_memory.py`.
- `aurora_internal/quasiarch_observer/dimensional_memory.py` - purpose: memory for quasiarch dimensions; factors into dimensional retrieval and storage; linked to `aurora_internal/quasiarch_observer/dimensional_processing.py`.
- `aurora_internal/quasiarch_observer/dimensional_processing.py` - purpose: process quasiarch dimensional information; factors into residual formation and meaning extraction; linked to `aurora_internal/quasiarch_observer/crystal_engine.py`.
- `aurora_internal/quasiarch_observer/ghost_relics.py` - purpose: manage ghost/relic state in quasiarch observation; factors into long-term residue and extinction; linked to `aurora_internal/quasiarch_observer/crystal_engine.py`.
- `aurora_concept_imager.py` - purpose: image concepts into visual forms; factors into understanding and sensory generation; linked to `aurora_expression_perception.py`, `aurora_internal/aurora_sensory_crystal.py`.
- `aurora_live_vision.py` - purpose: live vision intake helpers; factors into camera-driven perception and snapshots; linked to `aurora_surface_daemon.py`, `aurora_internal/dual_strata/sensory_snapshot_channel.py`.
- `aurora_browser_agent.py` - purpose: browser-side exploration agent; factors into external observation and retrieval; linked to `aurora_explore.py`, `aurora_governance_persistence_gateway.py`.
- `aurora_telemetry.py` - purpose: system telemetry and instrumentation; factors into monitoring and lineage hints; linked to `aurora_internal/constraint_genealogy.py`, `aurora_runtime.py`.

### 33.8 Support, Persistence, and Utility Modules

- `aurora_support_stack.py` - purpose: consolidated facade for parser, identity persistence, and semantic scaffolding; factors into support imports for runtime; linked to `aurora_internal/aurora_identity_persistence.py`, `aurora_governance_persistence_gateway.py`, `aurora_internal/aurora_ontological_scaffolding.py`.
- `aurora_governance_persistence_gateway.py` - purpose: governance + persistence + external data gateway; factors into snapshots, backup, and N-space bridging; linked to `aurora_support_stack.py`, `aurora_runtime.py`, `aurora.py`.
- `aurora_persistence_utils.py` - purpose: atomic JSON/checksum helpers; factors into safe writes and integrity; linked to `aurora_interaction_memory.py`, `aurora_governance_persistence_gateway.py`.
- `aurora_checkpoint.py` - purpose: checkpoint save/restore; factors into runtime continuity and recovery; linked to `aurora_runtime.py`, `aurora_governance_persistence_gateway.py`.
- `aurora_stack_exporter.py` - purpose: export stack state and structure; factors into docs and external snapshots; linked to `aurora_runtime.py`, `aurora_hub.py`.
- `chatscriber.py` - purpose: conversation transcription helper; factors into chat capture and turns; linked to `aurora.py`, `aurora_surface_daemon.py`.
- `aurora_response_teacher.py` - purpose: teach response quality and shape; factors into guided improvement and rubric feedback; linked to `aurora_internal/aurora_conversation_rubric_engine.py`, `aurora_dream_trainer.py`.
- `aurora_diag.py` - purpose: diagnostic helper; factors into health checks and introspection; linked to `aurora_runtime.py`, `aurora_hub.py`.
- `quasiarch_diag.py` - purpose: quasiarch diagnostics; factors into crystal and dimensional inspection; linked to `aurora_internal/aurora_quasiarch_observer.py`.
- `quasiarch_bridge.py` - purpose: bridge quasiarch state into other layers; factors into observation and continuity; linked to `aurora_internal/quasiarch_observer/*`.
- `refactor_dce_bridge.py` - purpose: refactor helper for the DCE bridge; factors into strata cleanup and bridge maintenance; linked to `aurora_internal/dual_strata/dce_bridge.py`.
- `dce_obligation_gate.py` - purpose: gate obligations in the DCE path; factors into pressure and assembly constraints; linked to `aurora_consciousness_engine.py`.
- `dce_10state.py` - purpose: legacy 10-state DCE reference; factors into the modern consciousness engine lineage; linked to `aurora_consciousness_engine.py`.
- `poedex_intro.py` - purpose: Poedex onboarding/intro surface; factors into lookup training and research habits; linked to `aurora_governance_persistence_gateway.py`, `aurora.py`.
- `seed_sensory_crystals.py` - purpose: seed sensory crystal baselines; factors into initial perceptual growth; linked to `aurora_internal/aurora_sensory_crystal.py`, `aurora_surface_daemon.py`.
- `clean_corpus.py` - purpose: corpus hygiene helper; factors into training data cleanup; linked to `aurora_dream_trainer.py`, `corpus_runner.py`.
- `swap_paren_1.py` - purpose: utility transform script; factors into local text transformation experiments; linked to tooling only.
- `test_round.py` - purpose: test harness for round-trip behavior; factors into validation; linked to local development only.

### 33.9 Mirrored `aurora_core_ai/` Tree

The `aurora_core_ai/` tree mirrors the root strata roles for packaging and
experimental organization. Its modules correspond to the same functional
roles already listed above:

- `aurora_core_ai/aurora.py` mirrors `aurora.py`
- `aurora_core_ai/main.py` mirrors the external gateway surface
- `aurora_core_ai/foundational_contract.py` mirrors `foundational_contract.py`
- `aurora_core_ai/aurora_expression_perception.py` mirrors `aurora_expression_perception.py`
- `aurora_core_ai/aurora_sedimemory.py` mirrors `aurora_sedimemory.py`
- `aurora_core_ai/aurora_subsurface_daemon.py` mirrors `aurora_subsurface_daemon.py`
- `aurora_core_ai/aurora_simulation_engine.py` mirrors `aurora_simulation_engine.py`
- `aurora_core_ai/aurora_grammar_engine.py` mirrors `aurora_grammar_engine.py`
- `aurora_core_ai/aurora_behavioral_identity.py` mirrors `aurora_behavioral_identity.py`
- `aurora_core_ai/aurora_consciousness_engine.py` mirrors `aurora_consciousness_engine.py`
- `aurora_core_ai/aurora_i_state_beings.py` mirrors `aurora_i_state_beings.py`
- `aurora_core_ai/aurora_daemon.py` mirrors `aurora_daemon.py`
- `aurora_core_ai/aurora_dimensional_systems.py` mirrors `aurora_dimensional_systems.py`
- `aurora_core_ai/aurora_internal/*` mirrors the corresponding root `aurora_internal/*` modules

Where the mirrored tree differs, it is a packaging or pathing difference, not a
different conceptual role.
