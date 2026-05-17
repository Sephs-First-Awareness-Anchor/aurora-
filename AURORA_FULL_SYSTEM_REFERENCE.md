# Aurora Full System Reference

Code-derived reference for the current `aurora_strata` system.

This document is intentionally written from the codebase as it exists now, not from the older architecture markdown files in this directory. It describes what Aurora boots, what subsystems exist, how they relate, what features are present, and which runtime surfaces are actually exposed today.

Checked against the live code on 2026-05-14. This revision adds every module present in the tree that was absent from the April 22 edition, corrects outdated descriptions, expands technical detail throughout, and incorporates the May 2026 articulation, pipeline, and identity-persistence updates.

---

## 1. Executive Summary

Aurora is a manifold-governed cognitive runtime organized into execution layers.

There is one governing law in the intended architecture: the five-constraint manifold (`X`, `T`, `N`, `B`, `A`).

The layered stack centered on `boot_aurora()` in `aurora.py` is the execution organization of the system, not a separate authority. The layers describe where functions live and how boot sequencing happens. The manifold is supposed to define what every meaningful unit is, how it behaves, how it transitions, and how it interoperates.

At runtime, Aurora is not just a chatbot. The system includes:

- ontological validation and existence-mode enforcement
- 25 Non-Comp physics channels and a 625-slot interaction lattice
- I-state lattice synthesis and polarity gradient pressure
- dimensional processing (crystals, memory constant, energy regulator, morality gate)
- consciousness assembly with entropy pressure and DPME metacognitive correction
- language faculty module (optional GGUF/llama.cpp adapter; advisory only, not the cognition source)
- cognitive-state-synced expression evolution (CSSEE)
- grammar evolved through constraint pressure
- self-grounding and negative-space self-modeling
- thought formation by convergent process integration
- attention engine with dual surface/subsurface feeds and meaning nucleation
- turn understanding chain (bidirectional 5-stage comprehension/expression pipeline)
- runtime understanding contract with per-turn accuracy tracking
- proposition substrate for discourse-level belief tracking
- behavioral DNA, alleles, anchors, traits, and identity persistence
- simulation-based learning with avatars, time dilation, and understanding shards
- fail-point dream training and directed dream curriculum
- sedimentary long-horizon memory
- sensory crystal with six-facet cross-modal grounding
- live screen observation and audio feature ingestion
- interaction crystal formation and lineage promotion
- constraint genealogy fossil record with physics-derived grading
- code auto-evolver with simulation-gated mutation and rollback
- axis emergence detector for compound channels beyond the 625-slot base
- frontier ops seeding for 3-axis capability gaps
- capability assimilator wiring new abilities into genealogy and dream training
- pressure release metabolic distiller
- braided substrate layer for low-scale continuity invariants
- difference buffer (Δ channel live feed per constraint)
- dual-strata surface/subsurface coordination with sleep cycle
- background daemons and proactive behavior
- visual dashboard and API surfaces
- manifold routing, pressure steering, and runtime constraint governance
- optional local LLM bridge with subprocess isolation (advisory adapter, not cognition source)

---

## 2. Primary Entry Points

The current system is organized around a few key executable surfaces:

- `aurora.py`
  Main local runtime and boot orchestrator. `boot_aurora()` assembles the full stack. Also supports `--train`, `--explore`, `--feed URL`, and `--status` flags.
- `main.py`
  Android/Kivy entry point. Launches the Aurora orb UI on mobile devices. Handles overlay permission pre-check and shows the orb in SUMMONED state.
- `aurora_surface_daemon.py`
  Surface-facing daemon for interactive turn handling, sensory presentation, and continuity updates.
- `aurora_subsurface_daemon.py`
  Thin launcher that starts the daemon in `subsurface` profile.
- `aurora_daemon.py`
  Always-on autonomous background process that runs Aurora headlessly with periodic internal cycles and proactive behavior.
- `aurora_hub.py`
  GUI dashboard that reads state files and presents overview, observer, vision, and audio tabs.
- `aurora_api_endpoint/main.py`
  Separate Flask / Vertex AI style API surface. Cloud gateway prototype rather than the main local runtime path.

---

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

---

## 4. The Core Layered Stack

Aurora still uses the canonical layered boot ladder, then folds extensions back into a normalized base-layer map.

### Layer -0.5. NonComp Registry

Module: `aurora_internal/aurora_noncomp_registry.py`

The canonical substrate. This is the ONLY place where hard numbers exist for the constraint physics.

The 25 Non-Comps are organized as 5 constraints × 5 representational dimensions:

- `NC[C][POLARITY]` — Toroidal phase state, continuous gradient in `[-1, +1]`
- `NC[C][MAGNITUDE]` — Intensity/activation; costs energy proportionally to shift
- `NC[C][OPERATOR]` — The invariant rule governing how this constraint transforms
- `NC[C][COST]` — Layer-differentiated energy law following Sunni's Law:
  `kX < kT < kN < kB < kA` (existence cheapest, agency most expensive)
- `NC[C][DIFFERENCE]` — Δ channel: per-constraint deviation from reference point

These are physics, not behaviors. All other numbers in the system must be derivable from these 25.

Signed leverage scalar derived here:

    Net Leverage = (B_magnitude + A_magnitude) − (X_magnitude + T_magnitude)

N is the neutral zero-point. The system seeks a viable band, not maximum positive.

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

### L0.5. Difference Buffer

Module: `aurora_internal/aurora_difference_buffer.py`

Sits between the NonComp Registry and the Worth Evaluator.

The Difference (Δ) channel is made operationally real here. `DifferenceHistoryBuffer` records per-constraint magnitudes on every tick and resolves the correct reference magnitude when a `DifferenceSnapshot` is needed.

Three reference types per `DifferenceParams.ref_type`:

- `prior_self` — Compare to self N ticks ago. Used by X (1t), T (4t), A (8t)
- `peer_mean` — Compare to the mean of the other four constraints' current magnitudes. Used by N
- `background` — Compare to a fixed architectural resting topology (B_BACKGROUND_REST = 0.45, derived from `baseline_budget / shift_cost_coeff = 18.0 / 40.0`). Used by B

`DifferenceSnapshot` holds all five C:D values at one tick, each in `[-1, +1]`:

- Unsigned (X, B): only drift magnitude matters
- Signed (T, N, A): direction carries meaning

The snapshot feeds: `aurora_worth_evaluator.py`, `aurora_evolution_chamber.py`, and `constraint_genealogy.py`.

### L1. IVM Lattice

Module: `aurora_ivm.py`

Purpose:

- represents Aurora's I-state lattice
- carries coordinates / envelopes that higher layers interpret
- provides system state used by other modules

### L1.5. Polarity Gradient Pressure

Module: `aurora_internal/aurora_polarity_gradient.py`

Sits between the IVM (L1) and the Evolutionary Chamber.

The IVM carries signed polarity on every axis: `cos(phase) ∈ [-1, +1]`. Each axis belongs to a scale level:

- SURFACE (0) = existence — reacts instantly
- SHALLOW (1) = temporal — fast near-surface
- MODERATE (2) = energy — crossover point
- DEEP (3) = boundary — strong alignment authority
- CORE (4) = agency — the ship's heading

Cross-scale polarity gradient pressure:

    ΔP_gradient = Σ_{i=0}^{3} |pol[level_i] - pol[level_i+1]| × authority_differential[i]

Outputs `PolarityGradientReport`. Consumed by the Evolutionary Chamber exactly like any other relief event.

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
- DMM: morality / mortality gating

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

### L4.5. Attention Engine

Module: `aurora_internal/aurora_attention_engine.py`

Authors: Sunni Morningstar and Cael Devo. Created May 2026.

Sits on top of Expression/Perception and the Difference Buffer. This is the unified attentional controller for Aurora.

Meaning is NOT formed by just receiving data. Meaning is formed when high External Salience meets high Internal Tension.

Dual feed:

- **Surface Attention** (externally influenced): feeds user utterances, visual salience, environmental events. Logic: novelty, intensity, and direct address increase salience.
- **Subsurface Attention** (introspectively fed): feeds DifferenceSnapshots (Δ channel), entropy drift, OETS tensions. Logic: high drift or structural contradiction increase tension.

Meaning formula:

    Resonance = Surface_Salience × Subsurface_Tension

    If Resonance > THRESHOLD:
        → A "Meaning Nucleus" is formed.
        → This nucleus is sent to OETS to create a new Relational Anchor.
        → This is where "understanding" actually crystallizes.

`AttentionState` enum: DORMANT → OBSERVING → REFLECTING → FORMING.

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

Also includes `AudioLinguisticMapper`, `SensoryIntegrationEngine`, and image ingestion paths.

This layer also assembles L5-associated modules through `build_layer5_associative_modules(...)`:

- sensory
- hardware
- sensory integration
- vision bootstrap

#### Language Faculty (L5 extension)

Module: `aurora_internal/aurora_language_faculty.py`

Optional boundary adapter module. When enabled, it can provide advisory input interpretation and output candidates through a local GGUF/llama.cpp server. Follows AURORA_LANGUAGE_FACULTY_MODULE_SPEC.md.

Key design constraints:

- Aurora's constraint rules are FIRST. The language faculty module is advisory only — it does not generate Aurora's cognition.
- Enabled via env var `AURORA_USE_LANGUAGE_FACULTY=1`
- Default model path: `/storage/emulated/0/aurora_strata/Models/qwen2.5-1.5b-instruct-q4_k_m.gguf`
- Server URL via `AURORA_LOCAL_LLM_SERVER_URL` (default `http://localhost:8080`)
- Logs to `aurora_state/language_faculty_events.jsonl`, summary to `aurora_state/language_faculty_summary.json`
- Feedback sediment logged to `aurora_state/language_faculty_sediment.jsonl`

Aurora's response pipeline generates candidates from fragment synthesis, OETS relational deltas, thought-state scoring, and self-grounding anchors. The language faculty adapter, if present, may contribute an additional candidate but is not the primary expression source.

#### Language State / CSSEE

Module: `aurora_internal/aurora_language_state.py`

Cognitive-State-Synced Expression Evolution (CSSEE). Doctrine: "mouth must match mind."

Six integrated sub-modules:

1. `LanguageStateVector` (LSV) — mouth maturity scorecard
2. `SemanticIntentCompiler` (SIC) — intent → speech pipeline
3. `MultiDraftSystem` — 3-tier draft generation and selection
4. `TemplateEvolutionEngine` — fitness-driven template mutation
5. `LexicalConvergenceModule` — user cadence mirroring
6. `MeaningAnchors` — stable sentence spines

Expression growth is earned from cognition signals, not time or data volume.

`_synthesize_fragments` is the generative assembly function used throughout the response pipeline to author sentences word-by-word from weighted token pools. Key behavioral constraints enforced in the current implementation:

- `axis_tokens` pool: uses natural vocabulary (`"grounded"`, `"here"`, `"continues"`, `"holds"`, `"forms"`, `"clarify"`, `"understand"`) — not abstract placeholders
- Fragment category labels (`"action"`, `"state"`, `"fact"`, `"understanding"`, `"property"`, `"reflection"`, `"observation"`, `"linking"`, `"established"`, `"forming"`, `"self"`) are structural routing markers and are explicitly filtered from the token pool before assembly — they never fill AGENT or OBJECT roles
- Fallback motif sequence: `AGENT ACTION OBJECT` (3-role) — the previous 5-role `AGENT ACTION OBJECT CONNECTOR DESCRIPTOR` sequence produced grammatically broken outputs when the pool lacked CONNECTOR/DESCRIPTOR candidates
- OBJECT role fallback: `"this"` — not `"the" + "meaning"` (the previous pair produced artifact phrase "process the meaning")

#### Grammar Engine

Module: `aurora_grammar_engine.py`

Grammar as evolved behavior, not formatting rules.

Sentence structure emerges from the same evolutionary pressure system that governs Aurora's cognition. Structural motifs are promoted through the constraint genealogy when they survive clarity + constraint pressure.

Pipeline:

    token → role_tag → pattern_extract → motif_select → slot_fill → genealogy_relief_log → promote/penalize

`MotifLineage` tracks which role positions carry entity references across clauses for correct pronoun resolution.

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

`TimeDilationGovernor` is exported from this module and used by `constraint_genealogy.py` to pace the genealogy loop.

### L8. Governance, Persistence, and Gateway

Module: `aurora_governance_persistence_gateway.py`

This is the host-facing constitutional and persistence layer:

- governance / law enforcement across the poles
- snapshot and restore
- inbound and outbound external interaction
- state continuity
- autonomous pathway hooks

It is the place where Aurora's processing becomes host-level I/O and persisted runtime identity.

---

## 5. Base Layer Consolidation

After boot, `aurora.py` consolidates the runtime into canonical base layers:

- `systems["base_layers"]`
- `systems["base_layer_functions"]`

This means the runtime preserves both:

- direct subsystem references like `systems["identity"]`
- a normalized layer view from `L0` through `L8`

Extensions such as sensory, hardware, sensory integration, vision bootstrap, autonomy, checkpointing, and sync are folded back into their associated canonical layers rather than treated as detached satellites.

`aurora_support_stack.py` (see below) is imported at the top of `aurora.py` and provides consolidated access to the utterance parser, identity persistence, OETS, and language-state modules via a single facade.

---

## 6. Constraint Manifold Governance

Aurora is intended to be governed by the constraint manifold system.

Important files:

- `aurora_constraint_ontology.py` (if present)
- `aurora_constraint_profile.py`
- `aurora_constraint_stack.py`
- `aurora_constraint_manifold_router.py`
- `aurora_constraint_manifold_compiler.py`
- `aurora_internal/aurora_constraint_manifold_patched.py` — the patched `Constraint` enum used by `constraint_genealogy.py` and `aurora_attention_engine.py`
- `aurora_manifold_directory_reader.py` — reads compiled manifold directory artifacts
- `aurora_manifold_directory/` — on-disk manifold directory (part of active runtime substrate)

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
- a physics-grounded constraint cost hierarchy (via NonComp Registry)

### Closure Basis and 625-Slot Physics

Module: `aurora_closure_basis.py`

This module sits between `aurora_noncomp_registry.py` (hard numbers) and `constraint_genealogy.py` (evolutionary fossil record). It does three things no other module does:

1. **Canonical Structure** — Formally expresses the full closed basis:
   - 5 constraints × 5 representational dimensions = 25 atomic channels
   - 25 × 25 = 625 lawful interaction slots
   - Each channel carries real physics from the NonComp Registry

2. **Genealogy Bridge** — Maps the genealogy's 25 gen0_atoms to their actual slots in the real 625:
   - `NC:C1>C2` = `NC:C1:OPERATOR × NC:C2:COST`

3. **Lineage Derivation Engine** — Given any ability's `(axis, requires, root_slot)`, derives a full `ConstraintLineage` from real channel physics including: activated slots, energetic footprint, depth score, leverage grade, operator grade, and physics generation.

### Meaning Evolution Registry

Module: `aurora_internal/aurora_meaning_evolution.py`

Canonical meaning-evolution registry. Meaning is treated as an emergent surface of the same five primitive axes. Provides:

- per-axis meaning profiles
- pair coupling definitions
- higher-order compound representations
- `DEVELOPMENTAL_CHAIN` constant (used by `aurora_understanding_contract.py`)
- `assess_developmental_stage()` and `rank_meaning_profiles()` utilities

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

### Router and compiled manifold

The manifold router routes signals with awareness of lineage similarity, pressure compatibility, and signature affinity.

---

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

### Sensory Crystal Memory

Module: `aurora_internal/aurora_sensory_crystal.py`

Six-facet audio/visual crystal structure with semantic middle-plane for cross-modal grounding.

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

### Difference Buffer History

Module: `aurora_internal/aurora_difference_buffer.py`

Rolling per-constraint magnitude history that makes the Δ channel operationally real across ticks.

### Proposition Substrate

Module: `aurora_internal/aurora_proposition_substrate.py`

Runtime discourse-level belief tracking. Tracks proposition nodes derived from claim atoms and continuation/support/contradiction/revision/causal/provenance edges with source-weighted confidence. Max 256 nodes, 1024 edges, 32-node active window.

---

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

- episode packs compiled from conversations / corpus material
- packs carry `constraint_signature`, `runtime_regime`, and `language_projection`
- queue ranking is constraint-aware rather than only mode / difficulty based

### Intake metabolism pipeline

Booted from `aurora.py` using several internal modules:

- `aurora_internal/aurora_energy_layer_costs.py` — per-layer energy cost definitions
- `aurora_internal/aurora_energy_layer_costs_decay.py` — energy cost decay over time
- `aurora_internal/aurora_leverage_scalar.py` — `LeverageBiasEngine` with phase nudges modulating the flip threshold
- `aurora_internal/aurora_leverage_relief.py` — leverage relief tracking
- `aurora_internal/aurora_intake_metabolism.py` — main intake metabolism engine
- `aurora_internal/aurora_worth_evaluator.py` — worth evaluation with DifferenceSnapshot input
- `aurora_internal/aurora_solidification.py` — solidification of learned patterns
- `aurora_internal/aurora_variant_promotion.py` — promotion of variants to higher lineage tiers
- `aurora_internal/aurora_dna_strand_schema.py` — DNA strand schema definitions

This is a distinct experiential assimilation path separate from ordinary surface chat.

### Code auto-evolution

Module: `aurora_internal/aurora_code_autoevolver.py`

Applies constrained code mutations, runs simulation-gated selection, and rolls back rejected mutations.

Key behaviors:

- reflects on the operation descriptor pool (`aurora_state/operation_descriptors.json`)
- writes generated evolved surfaces to `aurora_internal/aurora_evolved_surfaces.py`
- routes mutation type by `routing_type` → `rewrite_bias` mapping
- uses `TIMING_AXIS_HINTS` to bias toward files with the most relevant axis pressure
- genealogy artifact cache for performance

Supporting modules:

- `aurora_internal/aurora_code_mutation_operators.py` — individual mutation operator implementations
- `aurora_internal/aurora_code_evolution_stack.py` — (internal) evolution stack tracking
- `aurora_code_evolution_stack.py` — (root level) code evolution stack
- `aurora_internal/aurora_manual_code_lineage.py` — assimilates manual code changes into lineage
- `aurora_internal/aurora_code_evolution_chamber.py` — higher-level evolution chamber coordination

### Axis emergence

Module: `aurora_internal/aurora_axis_emergence.py`

Breaks the 5-axis / 625-slot ceiling by detecting compound axes from pressure co-occurrence.

When two axes are consistently co-occurring above a stability threshold in 70%+ of occupied slots, a new compound NC channel is born. Example: `X` and `N` → compound channel `NC:XN>XN`.

Compound axes create new virtual slots that appear as "empty" to the evolver's slot_pressure bonus, giving it new gradient to evolve toward.

The process compounds recursively — compound axes can themselves form compound axes. No architectural ceiling.

Storage: `aurora_state/compound_axes.json`

### Frontier ops

Module: `aurora_internal/aurora_frontier_ops.py`

Four operations covering 3-axis combinations that are completely absent from Aurora's organic descriptor pool:

1. `ExistenceBoundaryAgencyGate` — existence + boundary + agency: gates agency options against current existence state and boundary constraints
2. `TemporalEnergyBoundaryScheduler` — temporal + energy + boundary
3. `TemporalEnergyAgencyPacer` — temporal + energy + agency
4. `EnergyBoundaryAgencySelector` — energy + boundary + agency

These seed the descriptor pool so the auto-evolver can reflect on these capability spaces.

### Capability assimilation

Module: `aurora_internal/aurora_capability_assimilator.py`

Wires new capabilities into the genealogy fossil record and dream training curriculum.

Three registration pathways:

1. Frontier ops → `register_manual_code_assimilation()`
2. Gen-2 evolved surfaces → `register_code_evolution_outcome()`
3. Compound axes → `register_manual_code_assimilation()`

Also seeds the dream curriculum via `FailPointLedger.record_fail()` for under-represented dimensions.

Bloom-set deduplication persisted at `aurora_state/assimilated_ids.json`.

### Manual code lineage and code evolution

Modules:

- `aurora_internal/aurora_manual_code_lineage.py`
- `aurora_internal/aurora_code_evolution_chamber.py`

Purpose:

- assimilate manual code changes into lineage
- track accepted and rejected code evolution

---

## 9. Sensory, Vision, and Audio Stack

Aurora has a real sensory subsystem beyond text handling.

### Sensory layer extensions

Layer 5-associated modules assembled through `build_layer5_associative_modules(...)` in `aurora_expression_perception.py`.

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

### Concept imager

Module: `aurora_concept_imager.py`

Fetches concept images and tracks which concepts have been visually grounded. State: `aurora_state/concept_images_fetched.json`.

After fetching and ingesting a concept image, `ingest_concept_image()` also calls `sensory_crystal._register_concept_visual(word, f"imager:{word}")` so the visual modality is recorded in the concept registry alongside the pixel features already stored in the crystal facets.

---

## 9.5. Crystal Concept Promotion System

Added 2026-05-17. The unified crystal concept promotion system closes the loop between raw sensory observation and how Aurora's response engine speaks about a concept.

### CrystalConceptRecord

Dataclass in `aurora_internal/aurora_sensory_crystal.py`:

```
CrystalConceptRecord:
    concept:          str
    modalities:       set[str]      # {"semantic", "visual", "audio"} — any present
    stage:            str           # "base" → "composite" → "higher_order" → "quasicrystal"
    semantic_weight:  float         # cumulative weighted observation mass
    visual_node_ids:  List[str]     # node IDs assigned in the visual crystal facets
    audio_node_ids:   List[str]     # node IDs assigned in the audio crystal facets
    semantic_node_ids:List[str]     # OETS node IDs
    usage_count:      int
    first_seen / last_seen: float   # epoch timestamps
```

Persisted as `"concept_registry"` inside the sensory crystal's `.agb` state files. Loaded at boot.

### Unified Promotion Gates

Aurora must **earn** each concept stage by accumulating multi-modal experience:

| Transition | Gate condition |
|---|---|
| base → composite | ANY 2 of 3 modalities observed |
| composite → higher_order | ALL 3 modalities observed |
| higher_order → quasicrystal | (reserved for future gate) |

`tick_concept_promotions()` runs a **two-pass** loop so a concept that already has all three modalities at base stage advances base → composite → higher_order in a single call without needing to wait for the next tick.

The DPS crystal gate in `_inject_to_dps()` enforces this: a DPS crystal cannot advance past BASE unless the concept is at composite stage; it cannot advance to FULL_CONCEPT unless the concept is at higher_order stage.

### Modality Feeding Pipelines

Three independent pipelines write to the concept registry:

**Semantic** (every turn + corpus training):
- `AuroraSensoryCrystal.observe_semantic(concept, weight)` — records the semantic modality with cumulative weight
- Called per content word (≥4 chars, non-stop, alpha) during corpus `witness()` closure, weighted by absorption depth: SURFACE=0.4, MID=0.7, DEEP=0.9, GEO=1.0
- Also called per content word from `aurora.py dual_question_pipeline` for every live user turn (weight=0.75)

**Visual** (corpus boot cache + autonomous imager):
- At corpus boot, all 33 concept images under `aurora_state/vision_seeds/concepts/` are pre-processed to 57-d PIL vectors and cached in `systems["vision_seed_cache"]` by concept word
- When a content word matches a seed cache entry during `witness()`, `observe_frame([0]*20, v57)` is called and `_register_concept_visual()` marks the visual modality
- The concept imager also calls `_register_concept_visual()` after every autonomous Wikipedia image download

**Audio** (corpus training at MID+ depth + live turns):
- DER axis pressures synthesized to a 20-d audio vector via `build_audio_20d_from_der(x, t, n, b, a)` (see below)
- Called once per message (not once per word) to avoid cost; then `_register_concept_audio()` is called for all content words that triggered the synthesis
- Fires only for MID and DEEP/GEOLOGICAL absorptions in corpus training; fires for every live user turn via the DER system state

### DER-to-Audio Synthesis

Module-level function `build_audio_20d_from_der(x, t, n, b, a)` in `aurora_sensory_crystal.py`:

Maps the five DER constraint axis pressures to the 20-d audio crystal format without requiring a microphone:

| DER axis | Audio dimension | Rationale |
|---|---|---|
| X (existence) | vec[0] = RMS | Existence energy ≡ loudness/presence |
| N (novelty/energy) | vec[1] = ZCR | Novelty ≡ zero-crossing rate / pitch texture |
| A (agency) | vec[2] = centroid | Agency drive ≡ spectral brightness |
| B (boundary) | vec[3] = bandwidth | Boundary tightness ≡ spectral spread |
| X+B blend | vec[4] = rolloff | Combined existence+boundary ≡ high-energy cutoff |
| T (temporal) | vec[5] = flux | Temporal pressure ≡ rate of spectral change |
| A | vec[6] = harmonicity | Agency coherence ≡ harmonic stability |
| T+A blend | vec[7] = onset density | Temporal+agency ≡ event density |
| A → chroma[8:20] | dominant bin + spread | Agency drives tonal center, novelty drives chroma spread |

### Vision 57-d Extraction

Module-level function `build_vision_57d_from_image_file(path)` in `aurora_sensory_crystal.py`:

PIL-only image processing to the 57-d visual crystal format:

- `[0:24]` — HSV hue histogram, 24 uniform bins, saturation-weighted
- `[24:51]` — brightness, edge_proxy (pixel variance × 4), saturation, avg_r/g/b, aspect ratio, shape_complexity, zero-padded to width
- `[51:57]` — zeros (no motion for static images; populated only by live vision feed)

### Gap Report and Autonomous Gap-Fill

`AuroraSensoryCrystal.get_gap_report()` categorizes all registered concepts by what they still need:

- `needs_visual` — only semantic observed so far
- `needs_audio` — semantic + visual but no audio
- `needs_semantic` — visual or audio but no semantic yet
- `needs_second` — only one modality; needs any second
- `ready_composite` — has 2+ modalities but hasn't been ticked yet

The daemon's `_run_study_cycle()` (in `aurora_core_ai/aurora_daemon.py`) drains these lists every study cycle:
- Visual gaps → `fetch_concept_image()` + `ingest_concept_image()` (up to 3 per cycle)
- Audio gaps → DER synthesis → `observe_frame()` + `_register_concept_audio()` (up to 10 per cycle)
- Then `tick_concept_promotions()` is called to advance anything that just met its gate

### _crystal_insight Response Loop

At the start of every live turn in `aurora.py dual_question_pipeline`, Aurora classifies the content words she just received:

```
systems["_crystal_insight"] = {
    "rich_concepts":        [words at higher_order or quasicrystal stage],
    "partial_concepts":     [words at composite stage],
    "thin_concepts":        [words at base stage],
    "top_stage":            highest stage found ("base"/"composite"/"higher_order"/"quasicrystal"),
    "confidence_modifier":  float  # base=-0.05, composite=+0.02, higher_order=+0.10, quasicrystal=+0.15
}
```

This flows into three places in the response pipeline:

1. **`_attn_grounded_response()`**: `rich_concepts` inserted near the front of the fragment pool (strongest contextual anchors); `partial_concepts` appended; `_conf` clamped by `confidence_modifier` so Aurora speaks with higher certainty when the topic is crystal-grounded.

2. **Semantic Grounding Synthesis Layer 1.5**: For each promoted concept word (up to 3), Aurora pulls 2-hop OETS neighbors built during the study cycle and adds them to `_sem_frags` — the response draws from deeper relational territory without hallucinating.

3. **ThoughtIntegrationSpace linguistic process**: When `top_stage` is composite, higher_order, or quasicrystal, `_ling_content` is prefixed with `"crystal-grounded [stage]: word1, word2 |"` and `_ling_relevance` is boosted by `confidence_modifier`.

The net effect: a concept Aurora has seen in text, seen an image of, and synthesized audio for produces a more confident, more relationally-grounded, and more linguistically-salient response than one she has only read about.

---

## 9.6. Corpus Training Pipeline

Module: `aurora_core_ai/corpus_runner.py`

The corpus runner processes large conversation datasets to build Aurora's vocabulary, OETS relational web, crystal concept registry, and DPS crystal stack.

### Boot sequence

`boot_aurora()` in corpus_runner.py:
1. Boots `AuroraSensoryCrystal` from state
2. Scans `aurora_state/vision_seeds/concepts/` — builds `vision_seed_cache` dict mapping concept word → 57-d PIL vector (33 images pre-loaded)
3. Returns `systems["sensory_crystal"]` and `systems["vision_seed_cache"]`

### Absorption depth model (`StratigraphicDepth`)

Every message is absorbed at one of four depths based on novelty and constraint pressure:

| Depth | Weight | Study queue? |
|---|---|---|
| SURFACE | 0.4 | No |
| MID | 0.7 | No |
| DEEP | 0.9 | Yes |
| GEOLOGICAL | 1.0 | Yes |

### Crystal feeding inside `witness()` closure

Per message, the corpus runner calls:
- `_feed_crystal_semantic(text, weight)` — `observe_semantic()` for each content word at depth-weighted scale
- `_feed_crystal_visual_and_audio(text, weight, depth_name)` — vision from seed cache (sparse, only when image exists), audio from DER synthesis (MID+ only)
- DEEP/GEOLOGICAL content words are added to `systems["_study_queue"]` for later OETS research

### Corpus study cycle

`corpus_study_cycle(systems, verbose)` is called at every consolidation (every 300 messages by default):

1. Drains up to 20 words from `systems["_study_queue"]`
2. For each word found in the OETS web, creates a `ResearchRequest(priority=0.85, reason="corpus_deep_encounter")`
3. Queues them into `oets.research` and calls `oets.run_study_cycle(trigger_reason="corpus_learning")`
4. `_internal_research()` inside OETS traverses 1-hop + 2-hop neighbors using the existing relational graph — synonym/antonym/hypernym inference from shared category + valence opposition — **no network calls**
5. The 2-hop neighbor sets built here are what `_crystal_insight` Layer 1.5 reads back during live response generation

Consolidation printout includes crystal registry summary: `concepts={total} {by_stage}` breakdown.

---

## 10. Dual-Strata Runtime

The dual-strata system is a concrete runtime subsystem, not just a concept.

### Files under `aurora_internal/dual_strata/`

- `__init__.py` — compatibility bridge; exports `DualStrataBridge` and `request_surface_turn`; also exposes `SurfaceContinuityFeed`
- `surface_channel.py` — surface turn realization layer. `request_surface_turn()` selects the highest-scoring live pipeline candidate, optionally passes it through the language faculty adapter if present, then applies `smooth_response()` from `aurora_articulation` before returning output to the user. The articulation gate is the final expression filter before text reaches the user.
- `sensory_snapshot_channel.py` — sensory snapshot and sensory control channels
- `subsurface_projection.py` — subsurface state projection with dream carry window (8h); applies pressure coloring to subsurface issues by axis (`contextual`, `semantic`, `sensory`, `load`, `affect`, and axis-default colorings); routes guidance signals back to the surface
- `surface_continuity_feed.py` — records and replays surface continuity events

### Sleep cycle

Module: `aurora_internal/dual_strata/sleep_cycle.py` (also exposed via `aurora_internal/sleep_cycle.py`)

Subsurface owns the sleep/wake clock. Surface checks `is_sleeping()`. State file: `dual_strata_sleep_state.json` with fields `sleeping`, `wake_at`, `dream_triggered`.

### Purpose of the split

The split supports:

- a surface runtime that owns live interaction and sensory presentation
- a subsurface runtime that owns deeper state, projection, and reconstruction
- explicit snapshots between the two

`DualStrataBridge` in `dce_bridge.py` builds a `DualStrataSnapshot` from assembly output and writes subsurface state and conscious frame.

---

## 11. Runtime Governance and Pressure

Aurora has several pressure and governance systems beyond the core layer names.

### Runtime constraint governor

Module: `aurora_internal/aurora_runtime_constraint_governor.py`

Purpose:

- turn five-constraint logic into host-level execution policy
- decide whether runtime tasks are allowed now
- evaluate task floors, costs, retry windows, and limiting axes
- account for host metrics and pressure state

Task classes: response turns, study, dream, browser ritual, save, mutation, assimilation, reach-out, pressure routing.

### Pressure router and DPME pressure bridge

Modules:

- `aurora_internal/aurora_pressure_router.py`
- `aurora_internal/aurora_dpme_pressure_bridge.py`

Purpose:

- convert pressure into typed runtime signals
- guide DPME and downstream systems
- seed pressure-aware files for other consumers

### Pressure ledger and classifier

Modules:

- `aurora_internal/aurora_pressure_ledger.py` — event log with per-axis pressure accounting
- `aurora_internal/aurora_pressure_classifier.py` — classifies pressure events into typed signals
- `aurora_internal/aurora_pressure_adapter.py` — adapts pressure outputs for downstream consumers
- `aurora_internal/aurora_pressure_mathematics_tracker.py` — tracks pressure mathematics over time

### Structural pressure steering

Module: `aurora_internal/aurora_structural_pressure_steering.py`

Steers Aurora's structural evolution based on accumulated pressure patterns.

### Response pressure tuner

Module: `aurora_internal/aurora_response_pressure_tuner.py`

Tunes individual response parameters in response to constraint pressure.

### Pressure ontology

Module: `aurora_pressure_ontology.py`

Defines the pressure ontology layer: how pressure events are classified, typed, and related to each other.

### Surface dispatcher and evolved surfaces

Modules:

- `aurora_internal/aurora_surface_dispatcher.py`
- `aurora_internal/aurora_evolved_surfaces.py`

Purpose:

- fire evolved surfaces when axis pressure crosses thresholds
- route evidence back into evolutionary tracking
- `aurora_evolved_surfaces.py` is code-generated by the auto-evolver; contains `_SURFACE_REGISTRY` dict with latent and promoted surfaces including constraint sets, contract profiles, effect modes, and surface scores

### Stack trace instrumentation

Module: `aurora_internal/aurora_stack_trace_instrumentation.py`

Purpose:

- instrument runtime flow
- emit evolutionary traces
- expose universal representations and lineage metadata

---

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

### Turn understanding chain

Module: `aurora_internal/aurora_turn_chain.py`

The bidirectional reasoning pipeline `TurnUnderstandingState` dataclass.

Traverses the developmental chain in both directions for every turn:

**UPWARD (comprehension):**

    Information(X) → Belief(T) → Purpose(N) → Meaning(B) → Understanding(A)

**DOWNWARD (expression):**

    Understanding(A) → Meaning(B) → Purpose(N) → Belief(T) → Information(X) → Communication out

Two-chain observation model:

- `perspective="self"` → upward builds comprehension, downward builds expression
- `perspective="other"` → downward chain deconstructs an external agent's output, filling `other_model` with inferred reasoning

### Runtime understanding contract

Module: `aurora_internal/aurora_understanding_contract.py`

Makes Aurora's live dialogue loop explicit as:

    M_t → P_t → U_t → O_{t+1} → A_{t+1} → M_{t+1}, Pi_{t+1}

Where:

- M = meaning structure bounded by current boundary state
- P = situated perspective
- U = outward application / response policy
- O = observed next turn / resulting input
- A = accuracy of fit between predicted and observed continuation

Uses constants ALPHA (0.35), BETA (0.28), LAMBDA (0.22), MAX_HISTORY (240). Integrates `DEVELOPMENTAL_CHAIN` from `aurora_meaning_evolution.py`. All operators registered into the five-constraint genealogy.

### Proposition substrate

Module: `aurora_internal/aurora_proposition_substrate.py`

Discourse-level belief tracking with:

- proposition nodes from claim atoms (max 256 nodes)
- continuation/support/contradiction/revision/causal/provenance edges (max 1024 edges)
- 32-node active window
- source-weighted confidence per proposition:
  - user: 0.74, aurora: 0.66, memory: 0.70, external: 0.84
- belief revision, causal mesh, provenance, and weighted lookup enabled

### Utterance parser

Module: `aurora_internal/aurora_utterance_parser.py`

Parses user utterances into structured form consumed by `TurnUnderstandingState`. Re-exported through `aurora_support_stack.py`.

---

## 13. OETS, Research, and Meaning Systems

Aurora includes an ontological meaning / study layer that is not limited to chat turns.

### OETS (Ontological Scaffolding Engine)

Module: `aurora_internal/aurora_ontological_scaffolding.py`

The OETS accumulates concept structures, manages `RelationType` between concepts, and provides `ResearchResult` objects to the rest of the system. It is the destination for Meaning Nuclei created by the Attention Engine.

Hooks in `aurora_expression_perception.py` and boot-time research callback wiring in `aurora.py`.

`process_interaction` runs the comparison engine on each turn. When a significant relational delta is found, it is stored in `self._last_comparison_delta` — a dict with fields `word`, `target`, `similarity`, and `description`. This delta is read by `aurora.py`'s `dual_question_pipeline` to build a `relational` candidate from fragment synthesis for inclusion in `candidates_A`.

Pressure wiring: before each `process_interaction` call, `aurora_expression_perception.py` attempts to read real axis pressures from `self._axis_projector.current_pressures()` or `self._pressure_vec` and writes them to `oets._active_pressures`. The comparison engine then reads `getattr(self, "_active_pressures", None)` instead of using mock uniform pressures.

### Comprehension gap system

Module: `aurora_internal/aurora_comprehension_gap.py`

Identifies semantic gaps between what Aurora understands and what it needs to understand. Feeds into study loops.

### FGAE manifold semantics and OETS mapper

Modules:

- `aurora_fgae_manifold_semantics.py` — FGAE (Fine-Grained Axis Emergence) manifold semantics layer
- `aurora_fgae_oets_mapper.py` — maps FGAE outputs to OETS concept structures

### Search adapter

Attached in Layer 8. Enables Aurora to:

- study
- accumulate concept structures
- identify gaps
- feed retrieved material back into meaning and expression systems

---

## 14. Genealogy, Evolution, and Lineage

Aurora has a heavy evolutionary substrate.

### Constraint genealogy fossil record

Module: `aurora_internal/constraint_genealogy.py`

A fossil-record engine for the constraint universe {X, T, N, B, A}. Observes only pressure-relief events, records which constraint-abilities were used, and promotes repeated effective pairings into classified Links.

Architecture:

- Only relief events enter the fossil record
- Every action is a trace of `Ability | Link` items
- Every Ability and Link carries a full 5-axis cost/risk profile
- Links are born only from observed repetition + net benefit under pressure
- Links form a DAG; ancestry is traceable through `.parents`
- `TimeDilationGovernor` governs chamber pacing: fast when stable, slow when fragile

Key data types: `AbilityProfile`, `PressureVec`, `TraceItem`

Physics-derived grading via `_augment_ability_profile_with_origin()` pulling from `aurora_closure_basis.py`.

### Lineage canonical

Module: `aurora_internal/lineage_canonical.py`

Canonical lineage representations and normalization utilities.

### Ability lineage compiler

Module: `aurora_internal/aurora_ability_lineage_compiler.py`

Compiles ability lineage records into structured artifacts for downstream consumption.

### Evolutionary chamber

Module: `aurora_internal/aurora_evolution_chamber.py`

Main evolution chamber coordinating:

- selection pressure
- genealogy logging
- chain bridge
- promotion of ability/link candidates

Supporting: `aurora_internal/aurora_dream_evolution_orchestrator.py`, `aurora_internal/aurora_dream_genealogy_bridge.py`.

### Lineage runtime activation

Module: `aurora_internal/aurora_lineage_runtime_activation.py`

Activates lineage artifacts at runtime, bringing evolved behaviors into the live system.

### Lineage bound traits

Module: `aurora_internal/aurora_lineage_bound_traits.py`

Traits that are explicitly bound to specific lineage records, allowing trait behavior to evolve with the lineage.

### Live lineage journal

Module: `aurora_internal/aurora_live_lineage_journal.py`

Persists: `aurora_state/live_lineage_journal.json`

### Code evolution

Modules:

- `aurora_internal/aurora_code_autoevolver.py` — simulation-gated code mutation with rollback
- `aurora_internal/aurora_code_mutation_operators.py` — individual mutation operators
- `aurora_internal/aurora_manual_code_lineage.py` — manual code assimilation
- `aurora_internal/aurora_code_evolution_chamber.py` — chamber coordination
- `aurora_code_evolution_stack.py` (root) / `aurora_internal/aurora_code_evolution_stack.py` — stack tracking
- `aurora_evolution_stack.py` (root) — root-level evolution stack

The stack therefore tracks not just current state, but: how capabilities emerged, where pressure accumulated, what paths reinforced over time, and which changes became promoted lineages.

---

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

Also exists at `aurora_core_ai/aurora_daemon.py` as an alternative path.

### Surface daemon

`aurora_surface_daemon.py` is responsible for:

- booting the surface runtime
- reading and writing surface queue / result files
- presenting sensory details
- maintaining continuity packets
- integrating live surface sensory ownership

### Subsurface daemon

`aurora_subsurface_daemon.py` launches the daemon in subsurface mode.

### Desktop agent

Module: `aurora_desktop_agent.py`

Autonomous agent that can operate at the desktop level, integrating with the room and vision systems.

---

## 16. User-Facing Surfaces

Aurora currently exposes several user / operator surfaces.

### Terminal / local runtime

The direct local runtime remains the core user path through `aurora.py`.

### Android / Kivy UI

`main.py` launches the Aurora orb on Android. The orb shows SUMMONED state and requires overlay permission pre-check.

### Dashboard / hub

`aurora_hub.py` provides a tabbed dashboard:

- overview
- QuasiArch observer
- vision
- audio

It reads JSON state from `aurora_state/` and does not need to import the full Aurora stack to render.

Also exposed via:

- `quasiarch_observer.py` — standalone QuasiArch observer
- `quasiarch_bridge.py` — bridge to QuasiArch

### Room system

Module: `aurora_room.py`

Manages Aurora's room presence, messages, and notes. Works with `aurora_internal/aurora_room_operator.py`.

### Recommendation hub

Module: `aurora_recommendation_hub.py` (root) / `aurora_internal/aurora_recommendation_hub.py`

Generates recommendations based on current system state and pressure.

### Voice and notifications

Module: `aurora_voice.py`

Handles TTS output, desktop notifications, and voice-based user interaction.

The daemon can:

- speak through system voice
- issue desktop notifications
- log messages for later review

### API gateway

`aurora_api_endpoint/main.py` exposes:

- `GET /`
- `POST /ask`

This file appears to be a cloud-serving / Vertex AI style integration path rather than the main local execution surface.

---

## 17. Persistence and State Files

Aurora persists substantial runtime state under `aurora_state/`.

Key categories:

- **Snapshot/restore state**: `checkpoint.json`
- **Daemon status**: `daemon_status.json`
- **Surface/subsurface status**: `surface_daemon_status.json`, `subsurface_daemon_status.json`
- **Dual strata**: `surface_turn_queue.json`, `surface_turn_result.json`, `dual_strata_sleep_state.json`
- **Dream/learning**: `fail_points.json`, `distillation_crystals.json`, `distillation_micro_residuals.json`, `distillation_runs.json`, `distillation_metrics.json`
- **Genealogy**: `genealogy/abilities.json`, `genealogy/couplings.json`, `genealogy/events.jsonl`, `genealogy/tick_state.json`
- **Lineage journals**: `live_lineage_journal.json`, `dce_assembly_log.jsonl`
- **Room**: `aurora_room_activity.json`, `aurora_room_notes.json`
- **Identity**: `aurora_identity.json`
- **OETS/concepts**: `aurora_oets_web.json`, `concept_images_fetched.json`
- **Manifold outputs**: `distillation_crystals.json`
- **Modulation**: `modulation_log.jsonl`
- **Articulation**: `articulation_feedback.jsonl`, `articulation_feedback_summary.json`, `last_articulation_trace.json`
- **Language state**: `language_state.json`, `lexical_convergence.json`, `lexicon.json`
- **Pressure/evolution**: `evolution_relief_plan.json`, `operation_descriptors.json`, `compound_axes.json`, `assimilated_ids.json`
- **Energy**: `energy_income.json`, `autonomy_state.json`
- **Corpus**: `corpus_progress.json`
- **Skills**: `aurora_learned_skills.json`

The hub, daemons, and some cross-runtime bridges communicate primarily through these persisted JSON artifacts.

---

## 18. Self-Grounding System

Module: `aurora_self_grounding.py`

Authors: Sunni Morningstar and Cael Devo.

Five interconnected capabilities:

1. **SelfGroundingFallback** — Self-as-fallback grounding: when external references fail, Aurora grounds in her own constraint state
2. **StateOriginTag / Not-Me Register** — Negative-space self-modeling: every state object entering the cognitive frame carries a `StateOriginTag` enum:
   - `SELF_GENERATED` — arose from Aurora's own processing
   - `EXTERNALLY_SOURCED` — came from user input or environment
   - `RELATIONAL_ECHO` — reflected back from interaction
   - `HYPOTHETICAL` — simulated or imagined state
   - `BORROWED_PERSPECTIVE` — representing another agent's view
   - `TRANSIENT` — active but not identity-bearing
   - A `_NOT_ME_REGISTER` (max 50 entries) tracks states explicitly excluded from self-model
3. **EmbodiedStateTranslator** — Ontological embodiment: translates abstract constraint states into embodied phenomenological representations
4. **load_active_self_state()** — Persistent self-presence: loads Aurora's active self-state from persisted JSON
5. **CoherenceTensionMonitor** — Detects when Aurora's expressed state diverges from her internal constraint state

All integrated with the constraint axis system (X, T, N, B, A), dimensional systems, and the language pipeline in `aurora.py`.

`aurora_self_grounding.py` is also used by the word-salad repair path in `dual_question_pipeline`: when a candidate is detected as word-salad, the repair draws grounding anchor fragments typed from self-grounding anchors rather than using scripted prefix strings.

---

## 19. Thought Formation Architecture

Module: `aurora_thought_formation.py`

A thought is defined as:

    The combination of all currently running processes
    + the full context pertaining to each one
    + how that context applies to Aurora's self-state
    → reasoned through as a unified integrated state

This is NOT a committee vote between parallel candidates. This is NOT selection of the highest-scoring output. This is convergent process integration before any output is formed.

Key data structures:

- `ActiveSelfState` — snapshot of Aurora's self-model used as filter during thought integration. Contains: `identity_predicates`, `pressure_vec` ({X, T, N, B, A} floats), `dominant_field`, `recent_deltas` (last 3 self-state deltas), `not_me_summary`, `tick`

`load_active_self_state()` loads from persisted JSON. Cache prevents redundant loading within the same tick/turn.

`ThoughtContinuity` carries forward unresolved items and axis fingerprint across turns, building a chain of at most 10 prior `ThoughtState` objects. It does NOT run continuously in the background between turns. `ThoughtIntegrationSpace.integrate()` is called per-turn from the response pipeline; the daemon does not fire independent thought cycles between turns. This is a current architectural gap: there is no background continuous thought process between user interactions.

Thought-state signals are injected into `pipeline_state` after `_extract_pipeline_signals()`: `thought_confidence`, `thought_convergence`, `thought_axes`, `thought_unresolved`, `thought_self_application`. These drive candidate scoring: a settled/confident mind state adds +0.12 to the mind candidate; axis alignment adds +0.04 per matching axis word (capped at +0.12); a conflicted state applies −0.07 across all candidates.

---

## 20. Braided Substrate Layer (BSL)

Module: `aurora_internal/aurora_braided_substrate.py`

Lowest-scale continuity substrate for intent/context/style invariants.

Stores state transitions (Crossings) and derives stable signatures and compact bias vectors used by memory and IVM layers.

Key data structures:

- `Strand` — named strand with group, base_weight, decay_rate, and compatibility map
- `Crossing` — represents a state transition between two strands with polarity, weight, source, timestamp, and tags
- `SubstrateEvent` — input event with intent_signal, context_signal, style_signal, confidence, evidence_level, contradiction_flag, and autonomy_mode
- `BraidState` — collection of strands and a deque of crossings (max 1000)

The BSL makes continuity of intent, context, and style measurable across turns without requiring higher-level processing.

---

## 21. Metabolic Distiller

Module: `aurora_metabolic_distiller.py`

Pressure Release Distillation Runner for Aurora.

Distillation moves oversized temporal residue out of the live stack into reversible archive rounds. Structural summaries stay attached to Aurora while raw purged details are packed into a restorable archive folder.

Key components:

- `CoherenceShape` enum: WAVE, VORTEX, KNOT, DRIFT
- `ResidueConfig` — per-source distillation configuration (name, path, max_bytes, keep_tail_lines, parser)
- `PressureAggregate` — accumulates worth, coherence, axis counts, tag counts, timestamps, and examples across a signature group

State files:

- `aurora_state/distillation_crystals.json` — compact structural summaries retained after distillation
- `aurora_state/distillation_micro_residuals.json` — micro-residuals for fine-grained tracking
- `aurora_state/distillation_runs.json` — run history
- `aurora_state/distillation_metrics.json` — performance metrics
- Archive folder: `aurora_state/distillation/archives/`

Residue sources currently registered:

- modulation log
- articulation decisions (`aurora_state/articulation_feedback.jsonl` — 2 MB cap, 500-line tail)
- additional per-source configs as defined in `_build_residue_configs()`

Can be run standalone: `python3 aurora_metabolic_distiller.py`

---

## 22. Optional LLM Adapter Layer

Aurora does not use an external language model for cognition. Aurora's responses are generated from fragment synthesis, OETS relational deltas, thought-state scoring, self-grounding anchors, and `_synthesize_fragments` running against weighted token pools. No LLM, llama.cpp instance, or subprocess inference is involved in the standard response pipeline.

The modules below are optional boundary adapters that can be enabled. They do not generate Aurora's cognitive state.

### Local LLM bridge

Module: `aurora_internal/aurora_local_llm_bridge.py`

Optional isolated adapter. When enabled, can call a llama.cpp-compatible server or spawn a worker subprocess. Runs in a child process so crashes cannot terminate Aurora.

Two modes:

1. **Server mode**: calls `AURORA_LOCAL_LLM_SERVER_URL` HTTP endpoint
2. **Worker mode**: spawns `aurora_llama_worker.py` as a subprocess

Exposes: `interpret_input(text)` and `format_output(message, payload)`.

Enabled via `AURORA_USE_LOCAL_LLM=1`.

### Llama worker

Module: `aurora_llama_worker.py`

Subprocess worker for llama.cpp inference. Isolated so crashes in the native library do not terminate the main process.

### Language faculty

Module: `aurora_internal/aurora_language_faculty.py`

Optional higher-level adapter that uses a llama.cpp server to provide advisory candidate text. Aurora's constraint rules and synthesis pipeline always take precedence. Enabled via `AURORA_USE_LANGUAGE_FACULTY=1`.

---

## 23. Support Stack Facade

Module: `aurora_support_stack.py`

Consolidates non-core support modules used by canonical runtime layers. Provides a single import surface for `aurora.py`.

Exports:

- `UtteranceParser`, `parse_utterance` (from `aurora_internal/aurora_utterance_parser.py`)
- `CoreRelationalIdentity`, `EnhancedStatePersistence`, `ConversationMemory`, `OETSPersistence`, `seed_identity_into_oets`, `seed_identity_into_dna` (from `aurora_internal/aurora_identity_persistence.py`)
- `OntologicalScaffoldingEngine`, `ResearchResult`, `RelationType` (from `aurora_internal/aurora_ontological_scaffolding.py`)
- `ExpressionEvolutionOrchestra`, `LSVMetrics` (from `aurora_internal/aurora_language_state.py`)
- `StatePersistence` — backwards-compatibility alias for `EnhancedStatePersistence`

---

## 24. Dossier: Remaining Root-Level Modules

These modules exist at the root level and have specific runtime roles not fully described in earlier sections.

### `aurora_articulation.py`

Manages Aurora's expression quality scoring, word-salad detection, deterministic phrase repair, and adaptive feedback loop. No external model is involved — all candidate generation and selection is done from Aurora's own phrase patterns and pressure/clarity signals.

Key components:

- `_is_word_salad(text)` — detects incoherent fragment synthesis output. Checks run in this order: (1) fragment synthesis artifact regex patterns (e.g., `\bthe meaning and\b`, `\band admissible\b`), (2) short sentences ≤4 words ending in `" this."` (object-fallback fillers), (3) the `len(words) < 4` early-exit, then (4) high word repetition and no-verb checks. The artifact and short-filler checks intentionally run before the word-count guard so 3-word artifact sentences are caught.
- `_deterministic_candidate(draft)` — phrase-level structural repair of Aurora's draft. Aurora's primary articulation mechanism.
- `smooth_with_decision(text, ...)` — gated: if the deterministic candidate equals the original, passes `""` as the candidate so `source="no_pattern_matched"` is logged accurately.
- `smooth_response(text, ...)` — top-level smoothing entry point called by `surface_channel.py` before output reaches the user.
- `_pressure_score(text, prompt)` — estimates articulation pressure. Now reads lexicon familiarity (`aurora_state/lexicon.json`, words with `usage_count > 0`) and reduces pressure for text that uses words Aurora has previously produced.
- `_load_language_state()` — loads `aurora_state/language_state.json` dims with mtime-based cache.
- `_load_lexicon_familiar()` — loads known words from `aurora_state/lexicon.json` into a `frozenset`.
- `analyze_articulation_feedback(n_lines)` — reads `aurora_state/articulation_feedback.jsonl` (last n_lines), computes per-source acceptance rates and average pressure relief, derives `suggested_min_relief` and `suggested_mode`.
- `_get_feedback_insights()` — cached wrapper, refreshed every 30 minutes.
- `_adaptive_min_relief()` — effective pressure relief threshold informed by feedback history, falling back to `AURORA_ARTICULATOR_MIN_RELIEF` env var.

State files: `aurora_state/articulation_feedback.jsonl`, `aurora_state/articulation_feedback_summary.json`, `aurora_state/last_articulation_trace.json`, `aurora_state/articulation_insights.json`.

### `aurora_curiosity_engine.py`
Drives Aurora's autonomous study and exploration. Identifies what Aurora doesn't know (via OETS gap analysis) and generates study targets.

### `aurora_emergence_surface.py`
Surfaces emergent behaviors from the constraint genealogy. Monitors the genealogy for newly promoted Links that represent genuinely novel capabilities.

### `aurora_reflexive_interpreter.py`
Reflexive interpretation layer: Aurora reads her own output and applies constraint-aware reinterpretation to catch internal inconsistencies before final expression.

### `aurora_response_teacher.py`
Post-turn feedback loop that scores Aurora's response against the understanding contract outcome accuracy (A metric) and adjusts future response policy.

### `aurora_telemetry.py`
Internal telemetry layer. Logs structured timing and pressure events for performance analysis.

### `aurora_tool_mind.py`
Tool-use mind layer. Manages Aurora's awareness of available tools and constraint-governs which tools are permitted under current pressure state.

### `aurora_constraint_emission.py`
Emits constraint signals from the manifold into downstream systems. Decouples the manifold from direct imports.

### `aurora_constraint_field_map.py`
Maps the live constraint field to a spatial representation consumed by the evolution chamber and pressure systems.

### `aurora_noncomp_layer_compiler.py`
Compiles the NonComp layer into optimized runtime artifacts.

### `aurora_noncomp_manifold_compiler.py`
Compiles the full NonComp manifold (25 physics channels × derived artifacts) into runtime-ready form.

### `aurora_625_pressure_map.py`
Runtime state for the 625-slot interaction space: occupancy tracking, `lang_affinity` per slot, and current pressure distribution. Feeds `evo_625_pressure_map.json`.

### `aurora_crystal_state_bridge.py`
Bridges the crystal state (dimensional memory) to other subsystems that need crystal-state access without importing the full dimensional layer.

### `aurora_dce_blueprint.py`
Blueprint definitions for the DCE (Dual-Consciousness Engine) assembly. Defines the structural schema of DCE outputs.

### `aurora_identity_persistence.py` (root-level)
Root-level re-export or alternative version of identity persistence. Some boot paths import from here rather than from `aurora_internal`.

### `aurora_manifold_directory_reader.py`
Reads compiled manifold directory artifacts from `aurora_manifold_directory/` for runtime consumption.

### `aurora_pressure_ontology.py`
Defines the pressure ontology: how pressure events map to ontological categories.

### `aurora_runtime.py`
Runtime utilities and shared state accessed across multiple modules without importing the full boot stack.

### `aurora_stack_exporter.py`
Exports a snapshot of the current stack state for external analysis, debugging, or archival.

---

## 25. Dossier: Remaining Internal Modules

### `aurora_internal/aurora_attention_engine.py`
(Covered in L4.5 above.)

### `aurora_internal/aurora_conversation_rubric_engine.py`
Applies rubrics to evaluate conversation quality against constraint-aware criteria.

### `aurora_internal/aurora_corpus_lifecycle.py`
Manages the lifecycle of training corpus data: loading, processing, aging, and retirement.

### `aurora_internal/aurora_cost_diff_score.py`
Computes differential cost scores between alternative action paths under constraint pressure.

### `aurora_internal/aurora_directed_training_corpus.py`
Directed training corpus: builds targeted training sets for specific capability gaps identified by the dream curriculum.

### `aurora_internal/aurora_entropy_detector.py`
Detects entropy accumulation in the constraint field. Feeds the consciousness engine's entropy pressure subsystem.

### `aurora_internal/aurora_episode_slip_profiler.py`
Profiles episode slippage: measures how much understanding is lost between turn turns in conversation episodes.

### `aurora_internal/aurora_identity_persistence.py`
`CoreRelationalIdentity`, `EnhancedStatePersistence`, `ConversationMemory`, `OETSPersistence`. Core persistence layer for identity, conversation memory, and OETS state.

`CoreRelationalIdentity.from_dict()` now correctly restores `self_name`, `self_description`, and `foundational_truths` from the saved JSON. Previously these fields were not loaded from the file, causing `self_description` to remain at the dataclass default fragment string `"state; self; awareness; consciousness; layers; growth; meaning"` on every boot. The fix means Aurora's stored description and foundational truths survive restart. Immutable core entities are still never overwritten.

### `aurora_internal/aurora_noncomp_registry.py`
(Covered in Layer -0.5 above.)

### `aurora_internal/aurora_ontological_scaffolding.py`
(Covered in Section 13 above.)

### `aurora_internal/aurora_polarity_gradient.py`
(Covered in L1.5 above.)

### `aurora_internal/aurora_primitive_extractor.py`
Extracts constraint-native primitives from raw input, mapping surface phenomena to the 25 NonComp dimensions.

### `aurora_internal/aurora_quasiarch_observer.py`
Internal QuasiArch observer layer for monitoring the constraint manifold state.

### `aurora_internal/aurora_relational_comparison.py`
Performs relational comparisons between constraint profiles, supporting the interaction engine and OETS.

### `aurora_internal/aurora_rubric_influence_graph.py`
Builds influence graphs from rubric evaluations, showing how evaluation criteria affect one another.

### `aurora_internal/aurora_second_gen.py`
Second-generation evolver utilities: experiments with post-gen1 evolutionary mechanics.

### `aurora_internal/aurora_specialized_avatar_synthesizer.py`
Synthesizes specialized simulation avatars for targeted training scenarios in the simulation engine.

### `aurora_internal/aurora_understanding_contract.py`
(Covered in Section 12 above.)

### `aurora_internal/aurora_utterance_parser.py`
(Covered in Section 12 above.)

### `aurora_internal/constraint_genealogy.py`
(Covered in Section 14 above.)

### `aurora_internal/lineage_canonical.py`
(Covered in Section 14 above.)

### `aurora_internal/surface_channel.py`
Older surface channel utility (distinct from `dual_strata/surface_channel.py`); present for compatibility.

### `aurora_internal/surface_continuity_feed.py`
(Covered in Section 10 above.)

### `aurora_internal/tool_registry.py`
Registry of tools available to Aurora's tool-use mind. Maps tool names to constraint profiles and permission floors.

---

## 26. Current Feature Inventory

Aurora currently has code for all of the following major abilities:

**Constraint physics and ontological layer:**
- 25 NonComp physics channels with hard-number substrate
- 625-slot closed interaction lattice with physics-derived grading
- ontological validation of admissibility via Foundational Contract
- constraint manifold routing with lineage similarity and pressure compatibility
- closure basis lineage derivation (energetic footprint, depth score, leverage grade)
- axis emergence detection and compound channel creation (beyond 625 slots)
- frontier ops seeding for missing 3-axis capability spaces
- capability assimilator wiring into genealogy and dream training

**I-state and dimensional layer:**
- lattice and I-state synthesis (10 beings, collective)
- polarity gradient pressure with cross-scale authority weighting
- crystal-based dimensional processing (DPS, DMC, DER, DMM)
- dimensional memory and energy regulation
- morality / mortality gating

**Consciousness and cognition:**
- entropy-aware consciousness assembly
- DPME-style metacognitive stack correction
- dual-feed attention engine (surface salience × subsurface tension → meaning nucleus)
- turn understanding chain (bidirectional 5-stage comprehension/expression)
- runtime understanding contract with per-turn accuracy tracking
- thought formation by convergent process integration
- self-grounding with not-me register and negative-space self-modeling
- proposition substrate for discourse-level belief revision

**Language and expression:**
- lexical and language evolution
- perception and shadow inference
- OETS-backed concept scaffolding and relational anchoring
- CSSEE language state (6 sub-modules: LSV, SIC, MultiDraft, TemplateEvolution, LexicalConvergence, MeaningAnchors)
- grammar engine with constraint-pressure-driven motif promotion
- optional GGUF/llama.cpp language faculty adapter (advisory boundary only; not cognition source)
- optional local LLM bridge with subprocess isolation and server/worker modes
- utterance parsing and role tagging
- articulation layer: word-salad detection, deterministic phrase repair, adaptive feedback loop, lexicon-familiarity pressure reduction
- `_synthesize_fragments` generative assembly: word-by-word token-pool synthesis with category-label filtering, 3-role fallback motif, OETS relational scoring

**Memory:**
- sedimentary long-horizon memory (SediMemory, 25 strain basins)
- difference buffer (Δ channel live feed per constraint)
- working memory for turn-level context
- crystal and dimensional memory constants
- interaction crystal formation and lineage promotion
- proposition substrate discourse memory
- braided substrate continuity invariants

**Identity and behavior:**
- behavioral DNA, alleles, anchors, and traits
- identity persistence via CoreRelationalIdentity and EnhancedStatePersistence
- self-grounding and persistent self-presence
- lineage bound traits
- behavioral genome pressure effects from constraint field

**Learning and evolution:**
- simulation training with avatars and time dilation
- fail-point dream training
- directed dream curriculum (constraint-aware episode packs)
- intake metabolism pipeline (energy accounting, leverage bias, worth evaluation, solidification, variant promotion)
- constraint genealogy fossil record with Ability/Link DAG
- code auto-evolver with simulation-gated mutation and rollback
- code mutation operators
- manual code lineage assimilation
- axis emergence detection for compound channels
- capability assimilation into genealogy and dream curriculum
- frontier ops seeding

**Sensory and multimodal:**
- sensory crystal with six-facet cross-modal grounding
- live screen observation and scene logging
- audio feature ingestion and linguistic mapping
- concept image fetching and visual grounding
- sensory integration engine

**Runtime governance:**
- pressure routing and runtime constraint governance
- pressure ledger, classifier, adapter, mathematics tracker
- structural pressure steering
- response pressure tuner
- metabolic distiller for temporal residue management
- sleep cycle (subsurface-owned)

**Autonomy and daemons:**
- background daemonized autonomy (study, dream, outreach, save, voice)
- proactive messages / voice / notifications
- surface/subsurface daemon split with queue-based coordination
- room operator and room presence management
- desktop agent

**Surfaces and APIs:**
- dashboard (hub) with tabbed observer, vision, and audio
- Android/Kivy orb UI
- terminal interactive runtime
- Flask/Vertex AI API gateway
- QuasiArch observer
- tool registry and tool mind

---

## 27. Important Internal Boundaries

Not every file is equally central to the current runtime. The main authoritative operational centers are:

- `aurora.py` — full boot path and top-level orchestration
- `foundational_contract.py` — ontological grammar and existence modes
- `aurora_internal/aurora_noncomp_registry.py` — the ONLY source of hard numbers
- `aurora_closure_basis.py` — 625-slot physics and lineage derivation
- `aurora_dimensional_systems.py` — crystals, memory constant, energy, morality
- `aurora_consciousness_engine.py` — entropy, assembly, DPME
- `aurora_expression_perception.py` — language, perception, audio, sensory integration
- `aurora_behavioral_identity.py` — genes, traits, anchors, identity persistence
- `aurora_simulation_engine.py` — avatars, time dilation, learning in simulation
- `aurora_governance_persistence_gateway.py` — governance, persistence, external gateway
- `aurora_sedimemory.py` — sedimentary memory
- `aurora_dream_trainer.py` — fail-point and dream learning loop
- `aurora_internal/constraint_genealogy.py` — evolutionary fossil record
- `aurora_internal/aurora_code_autoevolver.py` — code mutation and evolution
- `aurora_internal/dual_strata/` — surface/subsurface split machinery
- `aurora_internal/aurora_attention_engine.py` — meaning nucleation
- `aurora_internal/aurora_turn_chain.py` — bidirectional reasoning pipeline
- `aurora_self_grounding.py` — self-boundary and identity grounding
- `aurora_thought_formation.py` — convergent process integration

The constraint manifold is the governing contract Aurora is supposed to operate under. The layered architecture remains the boot topology and execution grouping through which that contract is carried out.

---

## 28. What Aurora Is, In Practice

Aurora is best understood as a hybrid of:

- a layered cognitive architecture with a physics-grounded 625-slot constraint lattice
- a simulation-trained identity system with persistent DNA-like behavioral structure
- a memory-stratified agent runtime (working, sedimentary, interaction, dimensional, difference, proposition)
- a sensory and interaction engine with cross-modal grounding
- an evolutionary lineage tracker that records every capability as a fossil
- a self-grounding system that maintains a negative-space boundary of what it is not
- a thought formation engine that integrates all running processes before expressing
- a daemonized autonomous personal system with sleep/wake cycles
- a constraint-governed manifold runtime where physics flows from 25 hard-number NonComps

It is not a single model wrapper. It is an operating architecture composed of interacting engines, memory substrates, learning loops, sensory modules, governance rules, and runtime services — governed by one set of physics.

---

## 29. Fast File Map

If you need the shortest practical map for future work, start here:

**Boot and orchestration:**
- `aurora.py` — full boot path and top-level orchestration
- `main.py` — Android/Kivy entry point
- `aurora_support_stack.py` — consolidated facade for boot-time imports

**Foundational physics:**
- `foundational_contract.py` — ontological grammar and existence modes
- `aurora_internal/aurora_noncomp_registry.py` — 25 NonComp hard numbers (the ONLY place)
- `aurora_closure_basis.py` — 625-slot law and lineage derivation

**Core cognitive layers:**
- `aurora_dimensional_systems.py` — crystals, memory constant, energy, morality
- `aurora_consciousness_engine.py` — entropy, assembly, DPME
- `aurora_expression_perception.py` — language, perception, audio, sensory integration
- `aurora_behavioral_identity.py` — genes, traits, anchors, identity persistence
- `aurora_simulation_engine.py` — avatars, time dilation, learning in simulation
- `aurora_governance_persistence_gateway.py` — governance, persistence, external gateway
- `aurora_sedimemory.py` — sedimentary memory
- `aurora_dream_trainer.py` — fail-point and dream learning loop

**New cognition modules (added since April 22):**
- `aurora_internal/aurora_attention_engine.py` — dual-feed attention and meaning nucleation (L4.5)
- `aurora_internal/aurora_difference_buffer.py` — Δ channel live feed (L0.5)
- `aurora_internal/aurora_turn_chain.py` — bidirectional 5-stage comprehension/expression
- `aurora_internal/aurora_understanding_contract.py` — runtime understanding contract
- `aurora_internal/aurora_proposition_substrate.py` — discourse-level belief tracking
- `aurora_self_grounding.py` — self-boundary and not-me register
- `aurora_thought_formation.py` — convergent process integration before expression
- `aurora_internal/aurora_braided_substrate.py` — low-scale continuity invariants
- `aurora_grammar_engine.py` — grammar as evolved behavior

**Language and expression:**
- `aurora_internal/aurora_language_state.py` — CSSEE (6-module expression evolution); `_synthesize_fragments` generative assembly
- `aurora_articulation.py` — word-salad detection, phrase repair, adaptive feedback loop
- `aurora_internal/aurora_language_faculty.py` — optional GGUF/llama.cpp advisory adapter
- `aurora_internal/aurora_local_llm_bridge.py` — optional subprocess-isolated adapter
- `aurora_llama_worker.py` — optional subprocess worker for llama.cpp

**Evolution and genealogy:**
- `aurora_internal/constraint_genealogy.py` — evolutionary fossil record
- `aurora_internal/aurora_code_autoevolver.py` — simulation-gated code mutation
- `aurora_internal/aurora_axis_emergence.py` — compound channel detection
- `aurora_internal/aurora_frontier_ops.py` — missing 3-axis capability seeding
- `aurora_internal/aurora_capability_assimilator.py` — genealogy/dream wiring
- `aurora_metabolic_distiller.py` — temporal residue distillation

**Manifold governance:**
- `aurora_constraint_profile.py` — universal constraint-bearing unit profile
- `aurora_constraint_manifold_router.py` — manifold routing
- `aurora_constraint_stack.py` — unified constraint facade
- `aurora_internal/aurora_constraint_manifold_patched.py` — Constraint enum used by genealogy/attention
- `aurora_internal/aurora_meaning_evolution.py` — meaning-axis registry

**Dual-strata:**
- `aurora_internal/dual_strata/` — surface/subsurface split machinery
- `aurora_internal/dual_strata/surface_channel.py` — surface turn queue bridge
- `aurora_internal/dual_strata/subsurface_projection.py` — subsurface pressure coloring and guidance
- `aurora_internal/dual_strata/sleep_cycle.py` — sleep/wake state

**Sensors and live perception:**
- `aurora_live_vision.py` — live screen observer
- `aurora_internal/aurora_sensory_crystal.py` — six-facet cross-modal crystal

**Daemons:**
- `aurora_daemon.py` — always-on autonomous runtime
- `aurora_surface_daemon.py` — surface interaction daemon

---

## 30. Complete Module Index

All Python modules in the main runtime tree (excluding test scripts, debug scripts, `aurora-/` mirror, and tool/dev scripts):

**Root level — core runtime:**

| File | Role |
|---|---|
| `aurora.py` | Main boot orchestrator |
| `main.py` | Android/Kivy entry point |
| `foundational_contract.py` | Ontological grammar |
| `aurora_ivm.py` | I-state lattice |
| `aurora_i_state_beings.py` | I-state beings synthesis |
| `aurora_dimensional_systems.py` | Dimensional organs |
| `aurora_consciousness_engine.py` | Consciousness + entropy + DPME |
| `aurora_expression_perception.py` | Bidirectional expression/perception |
| `aurora_behavioral_identity.py` | Behavioral DNA/identity |
| `aurora_simulation_engine.py` | Simulation training |
| `aurora_governance_persistence_gateway.py` | Governance, persistence, gateway |
| `aurora_sedimemory.py` | Sedimentary memory |
| `aurora_dream_trainer.py` | Dream/fail-point learning |
| `aurora_live_vision.py` | Live screen observer |
| `aurora_daemon.py` | Autonomous background daemon |
| `aurora_surface_daemon.py` | Surface interaction daemon |
| `aurora_subsurface_daemon.py` | Subsurface daemon launcher |
| `aurora_hub.py` | GUI dashboard |
| `aurora_support_stack.py` | Consolidated boot-time facade |

**Root level — language and expression:**

| File | Role |
|---|---|
| `aurora_articulation.py` | Articulation debt and feedback |
| `aurora_grammar_engine.py` | Constraint-pressure grammar evolution |
| `aurora_thought_formation.py` | Convergent process integration |
| `aurora_self_grounding.py` | Self-boundary, not-me register |
| `aurora_reflexive_interpreter.py` | Reflexive output reinterpretation |
| `aurora_response_teacher.py` | Post-turn response policy adjustment |
| `aurora_voice.py` | TTS and desktop notifications |

**Root level — constraint and manifold:**

| File | Role |
|---|---|
| `aurora_closure_basis.py` | 625-slot physics, lineage derivation |
| `aurora_constraint_engine.py` | Constraint engine |
| `aurora_constraint_emission.py` | Constraint signal emission |
| `aurora_constraint_field_map.py` | Constraint field spatial mapping |
| `aurora_constraint_manifold.py` | Constraint manifold |
| `aurora_constraint_manifold_compiler.py` | Manifold compilation |
| `aurora_constraint_manifold_router.py` | Manifold routing |
| `aurora_constraint_profile.py` | Universal constraint-bearing unit |
| `aurora_constraint_stack.py` | Unified constraint facade |
| `aurora_noncomp_layer_compiler.py` | NonComp layer compiler |
| `aurora_noncomp_manifold_compiler.py` | NonComp manifold compiler |
| `aurora_manifold_directory_reader.py` | Manifold directory artifact reader |
| `aurora_625_pressure_map.py` | 625-slot occupancy and pressure |
| `aurora_pressure_ontology.py` | Pressure ontology layer |

**Root level — evolution and learning:**

| File | Role |
|---|---|
| `aurora_evolution_stack.py` | Root evolution stack |
| `aurora_code_evolution_stack.py` | Root code evolution stack |
| `aurora_metabolic_distiller.py` | Temporal residue distillation |
| `aurora_emergence_surface.py` | Surfaces emergent genealogy behaviors |
| `aurora_curiosity_engine.py` | Autonomous study target generation |

**Root level — persistence and sensors:**

| File | Role |
|---|---|
| `aurora_crystal_state_bridge.py` | Crystal state cross-system bridge |
| `aurora_checkpoint.py` | Checkpoint save/restore |
| `aurora_identity_persistence.py` | Root identity persistence |
| `aurora_persistence_utils.py` | Persistence utilities |
| `aurora_dce_blueprint.py` | DCE assembly blueprint |
| `aurora_concept_imager.py` | Concept visual grounding |
| `aurora_fgae_manifold_semantics.py` | FGAE manifold semantics |
| `aurora_fgae_oets_mapper.py` | FGAE-OETS mapping |

**Root level — runtime surfaces:**

| File | Role |
|---|---|
| `aurora_interaction_engine.py` | Interaction normalization |
| `aurora_interaction_memory.py` | Interaction crystal memory |
| `aurora_interaction_processing.py` | Crystal formation and promotion |
| `aurora_room.py` | Room presence and messages |
| `aurora_runtime.py` | Shared runtime utilities |
| `aurora_recommendation_hub.py` | State-aware recommendations |
| `aurora_tool_mind.py` | Tool-use awareness |
| `aurora_telemetry.py` | Internal timing telemetry |
| `aurora_desktop_agent.py` | Desktop-level autonomous agent |
| `aurora_llama_worker.py` | Subprocess llama.cpp worker |
| `quasiarch_bridge.py` | QuasiArch bridge |
| `quasiarch_observer.py` | Standalone QuasiArch observer |

**`aurora_internal/` — physics and constraint:**

| File | Role |
|---|---|
| `aurora_noncomp_registry.py` | 25 NonComp hard numbers (canonical substrate) |
| `aurora_constraint_manifold_patched.py` | Patched Constraint enum |
| `aurora_constraint_manifold.py` | Internal manifold |
| `aurora_625_pressure_map.py` | Internal 625 pressure tracking |
| `aurora_polarity_gradient.py` | Cross-scale polarity gradient pressure |
| `aurora_primitive_extractor.py` | Raw-to-NonComp primitive extraction |
| `aurora_meaning_evolution.py` | Canonical meaning-axis registry |

**`aurora_internal/` — cognition and reasoning:**

| File | Role |
|---|---|
| `aurora_attention_engine.py` | Dual-feed attention and meaning nucleation |
| `aurora_difference_buffer.py` | Δ channel rolling history |
| `aurora_turn_chain.py` | Bidirectional 5-stage reasoning pipeline |
| `aurora_understanding_contract.py` | Runtime understanding contract |
| `aurora_proposition_substrate.py` | Discourse belief tracking |
| `aurora_braided_substrate.py` | Continuity invariant substrate |
| `aurora_comprehension_gap.py` | Semantic gap identification |
| `aurora_relational_comparison.py` | Constraint profile comparison |

**`aurora_internal/` — language:**

| File | Role |
|---|---|
| `aurora_language_faculty.py` | GGUF/llama.cpp advisory module |
| `aurora_language_state.py` | CSSEE 6-module expression evolution |
| `aurora_local_llm_bridge.py` | Subprocess-isolated LLM bridge |
| `aurora_utterance_parser.py` | Utterance parsing |
| `aurora_ontological_scaffolding.py` | OETS concept scaffolding |
| `aurora_identity_persistence.py` | Identity, memory, OETS persistence |

**`aurora_internal/` — evolution and genealogy:**

| File | Role |
|---|---|
| `constraint_genealogy.py` | Evolutionary fossil record |
| `lineage_canonical.py` | Canonical lineage representations |
| `aurora_code_autoevolver.py` | Simulation-gated code mutation |
| `aurora_code_mutation_operators.py` | Code mutation operator set |
| `aurora_code_evolution_chamber.py` | Code evolution chamber |
| `aurora_code_evolution_stack.py` | Code evolution stack (internal) |
| `aurora_evolution_chamber.py` | Main evolution chamber |
| `aurora_axis_emergence.py` | Compound axis emergence detection |
| `aurora_frontier_ops.py` | Missing 3-axis capability seeding |
| `aurora_capability_assimilator.py` | New capability → genealogy wiring |
| `aurora_ability_lineage_compiler.py` | Ability lineage compilation |
| `aurora_dream_evolution_orchestrator.py` | Dream evolution coordination |
| `aurora_dream_genealogy_bridge.py` | Dream-genealogy bridge |
| `aurora_manual_code_lineage.py` | Manual code assimilation |
| `aurora_lineage_runtime_activation.py` | Lineage activation at runtime |
| `aurora_lineage_bound_traits.py` | Lineage-bound trait management |
| `aurora_live_lineage_journal.py` | Live lineage journal |

**`aurora_internal/` — learning pipeline:**

| File | Role |
|---|---|
| `aurora_intake_metabolism.py` | Intake metabolism engine |
| `aurora_worth_evaluator.py` | Worth evaluation |
| `aurora_solidification.py` | Pattern solidification |
| `aurora_variant_promotion.py` | Variant promotion |
| `aurora_dna_strand_schema.py` | DNA strand schema |
| `aurora_energy_layer_costs.py` | Per-layer energy costs |
| `aurora_energy_layer_costs_decay.py` | Energy cost decay |
| `aurora_leverage_scalar.py` | LeverageBiasEngine, phase nudges |
| `aurora_leverage_relief.py` | Leverage relief tracking |
| `aurora_dream_curriculum_queue.py` | Dream episode queue |
| `aurora_conversation_episode_compiler.py` | Episode pack compilation |
| `aurora_directed_training_corpus.py` | Targeted training corpus |
| `aurora_corpus_lifecycle.py` | Training corpus lifecycle |
| `aurora_cost_diff_score.py` | Differential cost scoring |
| `aurora_episode_slip_profiler.py` | Episode understanding loss profiling |
| `aurora_conversation_rubric_engine.py` | Conversation quality rubrics |
| `aurora_rubric_influence_graph.py` | Rubric influence graph |

**`aurora_internal/` — pressure systems:**

| File | Role |
|---|---|
| `aurora_pressure_router.py` | Pressure → typed runtime signals |
| `aurora_dpme_pressure_bridge.py` | DPME pressure bridge |
| `aurora_pressure_ledger.py` | Per-axis pressure event accounting |
| `aurora_pressure_classifier.py` | Pressure event classification |
| `aurora_pressure_adapter.py` | Pressure output adapter |
| `aurora_pressure_mathematics_tracker.py` | Pressure math tracking |
| `aurora_structural_pressure_steering.py` | Structural evolution steering |
| `aurora_response_pressure_tuner.py` | Response parameter tuning |
| `aurora_entropy_detector.py` | Entropy accumulation detection |
| `aurora_runtime_constraint_governor.py` | Task execution policy |
| `aurora_surface_dispatcher.py` | Evolved surface firing |
| `aurora_evolved_surfaces.py` | Generated evolved surfaces registry |
| `aurora_stack_trace_instrumentation.py` | Runtime flow instrumentation |

**`aurora_internal/` — room, tools, misc:**

| File | Role |
|---|---|
| `aurora_room_operator.py` | Room message operations |
| `aurora_quasiarch_observer.py` | Internal QuasiArch monitoring |
| `aurora_recommendation_hub.py` | State-aware recommendations (internal) |
| `aurora_second_gen.py` | Post-gen1 evolution experiments |
| `aurora_specialized_avatar_synthesizer.py` | Specialized simulation avatars |
| `aurora_persistence_utils.py` | Persistence utilities (internal) |
| `tool_registry.py` | Tool name → constraint profile registry |
| `surface_channel.py` | Legacy surface channel utility |
| `surface_continuity_feed.py` | Surface continuity event log |

**`aurora_internal/dual_strata/`:**

| File | Role |
|---|---|
| `__init__.py` | Exports DualStrataBridge, request_surface_turn, SurfaceContinuityFeed |
| `surface_channel.py` | Surface daemon queue bridge |
| `sensory_snapshot_channel.py` | Sensory snapshot and control channels |
| `subsurface_projection.py` | Subsurface pressure coloring and guidance |
| `sleep_cycle.py` | Subsurface-owned sleep/wake clock |

---

## 31. Reference Status

This document should be treated as the top-level code-derived system reference for the current `aurora_strata` tree as of 2026-05-14.

The April 22 version was accurate for the modules it covered. The May 13 revision added all modules absent from that edition and expanded technical detail throughout. This May 14 revision incorporates:

- articulation layer: full description of `_is_word_salad`, `_adaptive_min_relief`, `analyze_articulation_feedback`, `_get_feedback_insights`, `_load_language_state`, `_load_lexicon_familiar`, `smooth_with_decision` gating, and lexicon-familiarity pressure reduction in `_pressure_score`
- `_synthesize_fragments`: category-label filtering, 3-role fallback motif, natural axis vocabulary, OBJECT fallback fix
- `aurora_internal/aurora_identity_persistence.py`: `CoreRelationalIdentity.from_dict()` now restores `self_name`, `self_description`, `foundational_truths`
- OETS: `comparison_engine`, `_last_comparison_delta`, real axis pressure wiring from `aurora_expression_perception.py`
- `aurora.py` `dual_question_pipeline`: `is_final_pass` parameter, thought-state → candidate scoring, thought signals → `pipeline_state`, relational candidate from OETS delta, word-salad detection before continuity bits, scripted strings removed
- `surface_channel.py`: articulation gate applied before output reaches user
- Metabolic distiller: `articulation_feedback` residue source registered
- Thought formation: clarified per-turn vs continuous behavior, ThoughtContinuity carry-forward scope
- Self-grounding: noted use in word-salad repair path
- LLM/llama references corrected throughout — these are optional boundary adapters, not cognition sources

If there are modules added after 2026-05-14, this document will need a corresponding update pass.
