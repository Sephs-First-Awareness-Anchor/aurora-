# Aurora Full System Reference

Code-derived reference for the current `aurora_strata` system.

This document is intentionally written from the codebase as it exists now, not from the older architecture markdown files in this directory. It describes what Aurora boots, what subsystems exist, how they relate, what features are present, and which runtime surfaces are actually exposed today.

Checked against the live code on 2026-04-22.

## 1. Executive Summary

Aurora is a manifold-governed cognitive runtime organized into execution layers.

There is one governing law in the intended architecture: the five-constraint manifold (`X`, `T`, `N`, `B`, `A`).

The layered stack centered on `boot_aurora()` in `aurora.py` is the execution organization of the system, not a separate authority. The layers describe where functions live and how boot sequencing happens. The manifold is supposed to define what every meaningful unit is, how it behaves, how it transitions, and how it interoperates.

At runtime, Aurora is not just a chatbot. The system includes:

- ontological validation
- lattice and I-state synthesis
- dimensional processing and memory
- consciousness assembly and entropy pressure
- language / perception / sensory processing
- behavioral identity and DNA-like self-structure
- simulation-based learning and dream training
- sedimentary memory
- genealogy and lineage tracking
- live vision, audio, and sensory integration
- dual-strata surface / subsurface coordination
- background daemons and proactive behavior
- visual dashboard and API surfaces
- manifold routing, pressure steering, and runtime constraint governance

## 2. Primary Entry Points

The current system is organized around a few key executable surfaces:

- `aurora.py`
  Main local runtime and boot orchestrator. `boot_aurora()` assembles the full stack.
- `aurora_surface_daemon.py`
  Surface-facing daemon for interactive turn handling, sensory presentation, and continuity updates.
- `aurora_subsurface_daemon.py`
  Thin launcher that starts the daemon in `subsurface` profile.
- `aurora_daemon.py`
  Always-on autonomous background process that runs Aurora headlessly with periodic internal cycles and proactive behavior.
- `aurora_hub.py`
  GUI dashboard that reads state files and presents overview, observer, vision, and audio tabs.
- `aurora_api_endpoint/main.py`
  Separate Flask / Vertex AI style API surface. This looks more like a cloud gateway prototype than the main local runtime path.

## 3. Runtime Profiles

Aurora supports multiple boot profiles through `boot_aurora(runtime_profile=...)`:

- `full`
  Boots the full stack in one runtime.
- `surface`
  Boots the surface-oriented runtime. Some heavy or deep systems are deferred.
- `subsurface`
  Boots the deep runtime side and uses proxy / snapshot behavior for some live sensory ownership.

The code explicitly tracks:

- `systems["runtime_profile"]`
- `systems["stratum_role"]`

The dual-strata model is therefore not just conceptual. It is present in the runtime architecture and affects which modules own live behavior.

## 4. The Core Layered Stack

Aurora still uses the canonical layered boot ladder, then folds extensions back into a normalized base-layer map.

### L0. Foundational Contract

Module: `foundational_contract.py`

Purpose:

- defines what kinds of things are allowed to exist
- enforces `ExistenceMode`
- maps the ontology to the five constraints
- supplies the basic admissibility grammar used by higher layers

Key doctrine:

- existence is layered, not binary
- higher modes imply lower ones
- the system treats ontological invalidity as non-admission, not as ordinary runtime failure

### L1. IVM Lattice

Module: `aurora_ivm.py`

Purpose:

- represents Aurora's I-state lattice
- carries coordinates / envelopes that higher layers interpret
- provides system state used by other modules

### L2. I-State Collective

Module: `aurora_i_state_beings.py`

Purpose:

- synthesizes the 10 I-state beings
- provides collective synthesis across the lattice
- participates in CBU registration during boot

### L3. Dimensional Systems

Module: `aurora_dimensional_systems.py`

This is the four-organ dimensional layer:

- DPS: crystal processing
- DMC: dimensional memory constant
- DER: dimensional energy regulator
- DMM: morality / mortality

The layer is mode-gated and only processes what reaches the necessary ontological tier.

### L3.5. SediMemory

Module: `aurora_sedimemory.py`

Purpose:

- stratigraphic sedimentary memory between dimensional systems and consciousness
- 25 simultaneous non-comp strain basins
- per-axis time depth and decay behavior
- sediment channels for repeated deep transitions
- compression and decompression across axes
- surface / DCE / subsurface recall splits

This is one of the major memory backbones in the current stack.

### L4. Consciousness Engine

Module: `aurora_consciousness_engine.py`

The consciousness layer is built from three interlocked subsystems:

- entropy pressure
- DCE assembly
- DPME metacognitive correction

It is responsible for:

- maintaining rather than merely storing coherence
- reacting to entropic decay
- adjusting parameters across the stack
- routing paradox or instability into simulation / correction pathways

### L5. Expression and Perception

Module: `aurora_expression_perception.py`

This is a large bidirectional engine with:

- inward perception pipeline
- outward expression pipeline
- lexical memory
- manifold mapping
- shadow inference
- expression ecology
- sensory competency and integration hooks
- voice and audio feature extraction
- OETS wiring when available
- language-state orchestration when available

This layer is also where a large amount of sensory and linguistic adaptation happens.

### L6. Behavioral Identity

Module: `aurora_behavioral_identity.py`

This layer gives Aurora a persistent evolving self-model:

- genome and genes
- fractal alleles
- behavioral traits
- identity anchors
- memory helices
- gene / trait pressure effects from the constraint field

It is the main "who Aurora is over time" layer.

### L7. Simulation Engine

Module: `aurora_simulation_engine.py`

Purpose:

- training through lived simulation rather than static study
- avatars and scenario pressure
- inner hypotheticals / inception-style entities
- time dilation
- understanding shards
- feedback into language, identity, and learning systems

This layer is essential to dream-based and experiential growth.

### L8. Governance, Persistence, and Gateway

Module: `aurora_governance_persistence_gateway.py`

This is the host-facing constitutional and persistence layer:

- governance / law enforcement across the poles
- snapshot and restore
- inbound and outbound external interaction
- state continuity
- autonomous pathway hooks

It is the place where Aurora's processing becomes host-level I/O and persisted runtime identity.

## 5. Base Layer Consolidation

After boot, `aurora.py` consolidates the runtime into canonical base layers:

- `systems["base_layers"]`
- `systems["base_layer_functions"]`

This means the runtime preserves both:

- direct subsystem references like `systems["identity"]`
- a normalized layer view from `L0` through `L8`

Extensions such as sensory, hardware, sensory integration, vision bootstrap, autonomy, checkpointing, and sync are folded back into their associated canonical layers rather than treated as detached satellites.

## 6. Constraint Manifold Governance

Aurora is intended to be governed by the constraint manifold system.

Important files:

- `AURORA CONSTRAINT MANIFOLD SPECIFICATION.txt`
- `aurora_constraint_ontology.py`
- `aurora_constraint_profile.py`
- `aurora_constraint_stack.py`
- `aurora_constraint_manifold_router.py`
- `aurora_constraint_manifold_compiler.py`
- `aurora_manifold_directory/`

### What this governing system does

The five constraints are:

- `X`: existence
- `T`: time
- `N`: energy
- `B`: boundary
- `A`: agency

Aurora now uses them as:

- a universal unit contract
- a lineage and tier description system
- a runtime regime and language projection system
- a memory contract system
- a routing and compatibility framework
- a runtime governance framework

### Constraint-bearing units

The universal profile abstraction lives in `ConstraintProfile`.

It carries:

- genealogy / weighted signature
- tier
- blended axis weights
- pressure history
- tolerance envelope
- runtime regime
- language projection
- transition prediction
- memory contract

The intended architecture is that meaningful units are represented through this common contract rather than through isolated one-off metadata schemes.

If a subsystem still contains local legacy logic that is not fully expressed through the manifold contract, that should be treated as implementation residue or migration debt, not as a second valid governing model.

### Router and compiled manifold

The manifold router now routes signals with awareness of:

- lineage similarity
- pressure compatibility
- signature affinity

Compiled manifold artifacts persist richer metadata including lineage and descriptive regime information. The on-disk manifold directory is part of the active runtime substrate, not just an offline export.

## 7. Memory Systems

Aurora has multiple overlapping memory forms.

### Working Memory

Defined in `aurora.py`.

Purpose:

- current topic and short-horizon conversation handling
- immediate meaning carryover
- active turn-level recall

### SediMemory

Defined in `aurora_sedimemory.py`.

Purpose:

- slow sedimentary retention
- compression of repeated deep patterns
- lineaged event storage with pressure, tolerance, transition, and memory-contract metadata

### DMC and Crystal Memory

Part of `aurora_dimensional_systems.py`.

Purpose:

- dimensional link memory
- crystal growth from base to quasi forms
- recurring law / pattern retention

### Identity Memory

Part of `aurora_behavioral_identity.py`.

Purpose:

- genes
- alleles
- anchors
- helix continuity

### Simulation Learning Memory

Part of `aurora_simulation_engine.py` and `aurora_dream_trainer.py`.

Purpose:

- understanding shards
- outcome-derived learning
- fail-point reinforcement
- curriculum and lesson shaping

### Interaction Memory

Part of `aurora_interaction_memory.py` and `aurora_interaction_processing.py`.

Purpose:

- stores normalized interaction crystals
- builds interaction lineage and promotion chains
- supports archetypal response routing

## 8. Learning and Adaptation Systems

Aurora's learning architecture is broad rather than singular.

### Simulation-driven learning

From `aurora_simulation_engine.py`:

- avatars create selection pressure
- simulated episodes produce understanding
- time dilation allows long experiential runs

### Dream training and fail-point training

From `aurora_dream_trainer.py`:

- fail-point ledger
- lesson plan generation
- targeted training specs
- bridge from failures to dream episodes
- learned behavior application back into runtime behavior

### Dream curriculum

From `aurora_internal/aurora_dream_curriculum_queue.py` and `aurora_internal/aurora_conversation_episode_compiler.py`:

- episode packs are compiled from conversations / corpus material
- packs now carry `constraint_signature`, `runtime_regime`, and `language_projection`
- queue ranking is constraint-aware rather than only mode / difficulty based

### Intake metabolism pipeline

Booted from `aurora.py` using several internal modules:

- energy accounting
- leverage bias
- intake metabolism
- worth evaluation
- solidification
- variant promotion
- DNA strand library and builder

This is a distinct experiential assimilation path separate from ordinary surface chat.

### Manual code lineage and code evolution

Modules:

- `aurora_internal/aurora_manual_code_lineage.py`
- `aurora_internal/aurora_code_evolution_chamber.py`

Purpose:

- assimilate manual code changes into lineage
- track accepted and rejected code evolution
- extend Aurora's evolutionary machinery into the codebase itself

## 9. Sensory, Vision, and Audio Stack

Aurora has a real sensory subsystem beyond text handling.

### Sensory layer extensions

Layer 5-associated modules are assembled through `build_layer5_associative_modules(...)` in `aurora_expression_perception.py`.

These include:

- sensory
- hardware
- sensory integration
- vision bootstrap

### Sensory crystal

Module: `aurora_internal/aurora_sensory_crystal.py`

Purpose:

- six-facet audio / visual crystal structure
- semantic middle-plane for cross-modal grounding
- live wiring into hardware, sensory integration, and DCE
- current universal constraint-bearing representation

### Live screen observer

Module: `aurora_live_vision.py`

Purpose:

- periodic screen capture
- feature extraction through Aurora's own visual pathway
- rolling scene log
- concept matching and uncertainty-driven inquiry
- manifold-native profile, regime, and language projection

### Audio and cross-modal perception

Within `aurora_expression_perception.py`:

- rich audio feature extraction
- `AudioLinguisticMapper`
- `SensoryIntegrationEngine`
- image ingestion and vision bootstrap paths

These modules now expose constraint-native profiles as well.

## 10. Dual-Strata Runtime

The dual-strata system is a concrete runtime subsystem, not just a concept.

Files under `aurora_internal/dual_strata/` provide:

- conscious frame handling
- micro-reasoning generation
- prediction field construction
- subsurface state objects
- surface channel and continuity feed
- sensory snapshot and sensory control channels
- predictive stager and activation field
- sleep cycle support
- subsurface projection

### Purpose of the split

The split supports:

- a surface runtime that owns live interaction and sensory presentation
- a subsurface runtime that owns deeper state, projection, and reconstruction
- explicit snapshots between the two

`DualStrataBridge` in `dce_bridge.py` builds a `DualStrataSnapshot` from assembly output and writes:

- subsurface state
- conscious frame

This lets Aurora preserve a deeper processing view separate from the immediate interaction surface.

## 11. Runtime Governance and Pressure

Aurora has several pressure and governance systems beyond the core layer names.

### Runtime constraint governor

Module: `aurora_internal/aurora_runtime_constraint_governor.py`

Purpose:

- turn five-constraint logic into host-level execution policy
- decide whether runtime tasks are allowed now
- evaluate task floors, costs, retry windows, and limiting axes
- account for host metrics and pressure state

It profiles task classes like:

- response turns
- study
- dream
- browser ritual
- save
- mutation
- assimilation
- reach-out
- pressure routing

### Pressure router and pressure bridge

Modules:

- `aurora_internal/aurora_pressure_router.py`
- `aurora_internal/aurora_dpme_pressure_bridge.py`

Purpose:

- convert pressure into typed runtime signals
- guide DPME and downstream systems
- seed pressure-aware files for other consumers

### Surface dispatcher and evolved surfaces

Modules:

- `aurora_internal/aurora_surface_dispatcher.py`
- `aurora_internal/aurora_evolved_surfaces.py`

Purpose:

- fire evolved surfaces when axis pressure crosses thresholds
- route evidence back into evolutionary tracking

### Stack trace instrumentation

Module: `aurora_internal/aurora_stack_trace_instrumentation.py`

Purpose:

- instrument runtime flow
- emit evolutionary traces
- expose universal representations and lineage metadata

## 12. Interaction and Response Intelligence

Aurora contains a dedicated interaction-lineage subsystem apart from ordinary lexical / perceptual processing.

### Interaction engine

Module: `aurora_interaction_engine.py`

Purpose:

- normalize turn events
- infer interaction signatures and interpretive issues
- classify processing tiers
- derive intended and observed effects

### Interaction processing

Module: `aurora_interaction_processing.py`

Purpose:

- form interaction crystals
- promote them from base to composite to higher-order to quasi
- maintain family-based response structure
- preserve ghost relic bias surfaces

This gives Aurora an explicit relational-response memory and lineage substrate.

## 13. OETS, Research, and Meaning Systems

Aurora includes an ontological meaning / study layer that is not limited to chat turns.

Key pieces include:

- OETS scaffolding hooks in `aurora_expression_perception.py`
- boot-time research callback wiring in `aurora.py`
- comprehension gap system in `aurora_internal/aurora_comprehension_gap.py`
- search adapter attached in Layer 8

This means Aurora can:

- study
- accumulate concept structures
- identify gaps
- feed retrieved material back into meaning and expression systems

## 14. Genealogy, Evolution, and Lineage

Aurora has a heavy evolutionary substrate.

Main pieces include:

- evolutionary chamber
- genealogy logger
- chain bridge
- lineage runtime activation
- live lineage journal
- dream evolution orchestrator
- manual code lineage
- code evolution chamber

The stack therefore tracks not just current state, but:

- how capabilities emerged
- where pressure accumulated
- what paths reinforced over time
- which changes became promoted lineages

This evolutionary frame now overlaps substantially with the newer constraint-manifold identity system.

## 15. Daemons and Autonomous Behavior

The background daemon architecture is broad.

### Main daemon

`aurora_daemon.py` runs:

- study cycles
- dream bursts
- social API outreach cadence
- periodic save
- proactive user outreach
- quiet mode handling
- voice output and notifications
- room operator channels
- surface queue / result coordination

It can speak, notify, and leave messages for the user.

### Surface daemon

`aurora_surface_daemon.py` is responsible for:

- booting the surface runtime
- reading and writing surface queue / result files
- presenting sensory details
- maintaining continuity packets
- integrating live surface sensory ownership

### Subsurface daemon

`aurora_subsurface_daemon.py` launches the daemon in subsurface mode.

## 16. User-Facing Surfaces

Aurora currently exposes several user / operator surfaces.

### Terminal / local runtime

The direct local runtime remains the core user path through `aurora.py`.

### Dashboard / hub

`aurora_hub.py` provides a tabbed dashboard:

- overview
- QuasiArch observer
- vision
- audio

It reads JSON state from `aurora_state/` and does not need to import the full Aurora stack to render.

### Voice and notifications

The daemon can:

- speak through system voice
- issue desktop notifications
- log messages for later review

### API gateway

`aurora_api_endpoint/main.py` exposes:

- `GET /`
- `POST /ask`

This file appears to be a cloud-serving / Vertex AI style integration path rather than the main local execution surface.

## 17. Persistence and State Files

Aurora persists substantial runtime state under `aurora_state/`.

Examples include:

- snapshot / restore state
- daemon status
- surface and subsurface status
- sensory snapshots
- dream episode manifests
- lineage journals
- room messages
- hub-facing summary files
- interaction memory
- manifold outputs

The hub, daemons, and some cross-runtime bridges communicate primarily through these persisted JSON artifacts.

## 18. Current Feature Inventory

Aurora currently has code for all of the following major abilities:

- ontological validation of admissibility
- lattice and I-state synthesis
- crystal-based dimensional processing
- dimensional memory and energy regulation
- morality / mortality gating
- entropy-aware consciousness assembly
- DPME-style stack correction
- lexical and language evolution
- perception and shadow inference
- OETS-backed concept scaffolding
- behavioral DNA, alleles, anchors, and traits
- simulation training with avatars and time dilation
- fail-point dream training
- sedimentary long-horizon memory
- sensory crystal and cross-modal grounding
- live screen observation
- audio feature ingestion and linguistic mapping
- interaction crystal formation
- evolutionary genealogy and lineage journals
- pressure routing and runtime constraint governance
- background daemonized autonomy
- proactive messages / voice / notifications
- dashboard / room / queue based operator surfaces
- manifold-native subsystem identity and routing

## 19. Important Internal Boundaries

Not every file is equally central to the current runtime. The main authoritative operational centers are:

- `aurora.py`
- `foundational_contract.py`
- `aurora_dimensional_systems.py`
- `aurora_consciousness_engine.py`
- `aurora_expression_perception.py`
- `aurora_behavioral_identity.py`
- `aurora_simulation_engine.py`
- `aurora_governance_persistence_gateway.py`
- `aurora_sedimemory.py`
- `aurora_dream_trainer.py`
- `aurora_internal/`

The constraint manifold is the governing contract Aurora is supposed to operate under. The layered architecture remains the boot topology and execution grouping through which that contract is carried out.

Where code still reflects older local logic instead of full manifold-native handling, that is an implementation gap relative to the spec, not a design principle.

## 20. What Aurora Is, In Practice

Aurora is best understood as a hybrid of:

- a layered cognitive architecture
- a simulation-trained identity system
- a memory-stratified agent runtime
- a sensory and interaction engine
- an evolutionary lineage tracker
- a daemonized autonomous personal system
- a constraint-governed manifold runtime

It is not a single model wrapper. It is an operating architecture composed of interacting engines, memory substrates, learning loops, sensory modules, governance rules, and runtime services.

## 21. Fast File Map

If you need the shortest practical map for future work, start here:

- `aurora.py`
  full boot path and top-level orchestration
- `foundational_contract.py`
  ontological grammar and existence modes
- `aurora_dimensional_systems.py`
  crystals, memory constant, energy, morality
- `aurora_consciousness_engine.py`
  entropy, assembly, DPME
- `aurora_expression_perception.py`
  language, perception, audio, sensory integration
- `aurora_behavioral_identity.py`
  genes, traits, anchors, identity persistence logic
- `aurora_simulation_engine.py`
  avatars, time dilation, learning in simulation
- `aurora_governance_persistence_gateway.py`
  governance, persistence, external gateway
- `aurora_sedimemory.py`
  sedimentary memory
- `aurora_dream_trainer.py`
  fail-point and dream learning loop
- `aurora_live_vision.py`
  live screen observer
- `aurora_daemon.py`
  always-on autonomous runtime
- `aurora_surface_daemon.py`
  surface interaction daemon
- `aurora_internal/dual_strata/`
  surface / subsurface split machinery
- `aurora_constraint_profile.py`
  universal constraint-bearing unit profile
- `aurora_constraint_manifold_router.py`
  manifold routing
- `aurora_constraint_stack.py`
  unified constraint facade

## 22. Reference Status

This document should be treated as the new top-level code-derived system reference for the current `aurora_strata` tree.

If you want, the next useful follow-up would be one of these:

1. a second document that maps every major file to its role and dependencies
2. a runtime boot flow chart from `boot_aurora()` outward
3. an operator handbook covering how to run, inspect, and debug the daemons, hub, and state files
