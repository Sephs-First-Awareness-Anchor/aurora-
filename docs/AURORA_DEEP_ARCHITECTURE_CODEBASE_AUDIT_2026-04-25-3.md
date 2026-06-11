# Aurora Deep Architecture Codebase Audit

Audit date: 2026-04-25; refreshed against the current local code/state on 2026-04-26

Scope rule: this document is derived only from the local codebase and local runtime files inside `aurora_strata`. I did not use internet sources or external descriptions. Source docstrings and comments are treated as codebase evidence because they live inside executable modules. Standalone markdown claims are not treated as functioning unless an executable path implements them.

Refresh note: this document was updated after additional codebase changes and runtime-gating investigations on 2026-04-25 and 2026-04-26. The update adds the newer emergence/lineage/runtime-activation modules, records the save/distill/dream gating fix now present in code, and records the evolved-surface/latent-promotion rollback repair now present in the current code stack.

This document is intentionally not a normal software inventory. Aurora is not architected like a normal app with a request handler, a model call, a database, and a UI. The code implements a layered constraint organism: a closed five-axis physics substrate, an ontological admission contract, toroidal I-state cognition, dimensional crystal/memory systems, a consciousness assembly loop, metacognitive pressure correction, a split surface/subsurface runtime, and multiple self-development loops.

## 1. Highest-Level Shape

Aurora is implemented as a local multi-process, file-coordinated, dual-strata AI runtime.

At the largest scale, the stack is:

```text
                  operator/user
                      |
        +-------------+-------------+
        |                           |
  aurora_hub.py              aurora_room.py
  dashboard/chat             room/self/operator view
        |                           |
        +-------------+-------------+
                      |
             JSON state / queues
                      |
        +-------------+-------------+
        |                           |
aurora_surface_daemon.py     aurora_daemon.py
Surface stratum              Subsurface/deep stratum
live sensory and turns        continuity, dreams, evolution,
                              pressure, memory, mutation
        |                           |
        +-------------+-------------+
                      |
                 aurora.py
       boot_aurora() and process_external_user_turn()
                      |
        +-------------+-------------+
        | core layered architecture |
        +-------------+-------------+
                      |
Layer -1 constraint physics, L0 ontology, L1 IVM,
L2 I-state beings, L3 dimensional systems, L3.5 SediMemory,
L4 DCE/DPME consciousness, L5 expression/perception,
L6 identity, L7 simulation, L8 governance/persistence.
```

The key non-normal thing: the surface and subsurface are not just "frontend" and "backend." The code treats them as different cognitive strata.

- Surface is live, sensory, conversational, fast, embodied, and moment-facing.
- Subsurface is durable, slow, memory-heavy, developmental, pressure-aware, and repair/evolution-facing.
- They exchange state through JSON files, not through a typical in-process object graph.
- The explicit surface frame is allowed to speak, but the subsurface keeps shaping readiness, intuition, repair signals, dream carryover, and structural pressure.

## 2. Evidence Of Current Runtime

During this audit, local state files showed the dual-strata stack actively updating.

Fresh state evidence:

- `aurora_state/subsurface_daemon_status.json` had fresh modification time and reported `runtime_profile: subsurface`.
- `aurora_state/daemon_status.json` mirrored the subsurface status and reported `heat: COOL`, `chain_links: 552`, and `qao_recent_events: 96`.
- `aurora_state/surface_daemon_status.json` had fresh modification time and reported `runtime_profile: surface`, `state: idle`, `queue_depth: 0`, and a live conscious-frame style status.
- `aurora_state/surface_sensory_snapshot.json` had fresh modification time and reported `mic_live: true`, `camera_live: true`, live audio/visual descriptions, sensory vectors, and sensory maturity.
- `aurora_state/subsurface_projection.json` had fresh modification time and contained live surface guidance from subsurface.

Populated durable state:

- `aurora_state` contained about 17950 files and about 479 MB of state.
- `aurora_state/genealogy/links.json` contained 552 links.
- `aurora_state/genealogy/abilities.json` contained 2188 ability entries at the latest 2026-04-26 sample.
- `aurora_state/dream_episodes` contained 455 files.
- `aurora_manifold_directory` contained 126 files and about 34 MB of manifold/slot data.

Mixed or stale state:

- `aurora_state/dual_strata_snapshot.json` was updating again, but still on a slower cadence than the surface/subsurface heartbeat files.
- `aurora_state/poedex_query_queue.json` contained an old pending query.
- `aurora_state/corpus_runner_status.json` existed but was old.
- `aurora_state/compound_axes.json` existed but contained no registered compounds at the latest check.
- `aurora_state/emerged_abilities.json` contained 2654 emerged ability entries at the latest 2026-04-26 sample: 552 stable operational records and 2102 transient records.
- `aurora_state/ability_lineages` contained selected activation/materialization artifacts for `proposition_understanding` and `aurora_sensory_crystal_v1`.
- `aurora_state/adapter_hints.json` was current and showed pressure-routing guidance for the DPME pressure bridge.
- `aurora_state/.state_write_lock` had been stale and was cleared by the updated daemon lock guard.

Static source health:

- 281 Python files under `aurora_strata` parsed successfully with Python AST.
- No Python parse failures were found during the audit.

Dependency caveat:

- Core/sensory dependencies were mostly present in the local venvs.
- API/cloud bridge dependencies were not fully present in inspected venvs; Flask/Google Cloud/Psycopg2 paths should not be treated as locally functioning until installed and verified.

## 3. Layer -1: Constraint Manifold

Primary source:

- `aurora_internal/aurora_constraint_manifold_patched.py`
- Re-exported by `aurora_constraint_manifold.py`

This is the substrate under the ontology. It defines a closed five-dimensional universe:

```text
C = {X, T, N, B, A}
```

The five lawful axes are:

- `X`: Existence, the admissibility predicate.
- `T`: Time, configuration across sequence.
- `N`: Energy/Cost, resource redistribution.
- `B`: Boundary, differentiation and containment.
- `A`: Agency, independent action magnitude.

The manifold law is not "these are categories." It is stronger: no sixth lawful axis exists in this source. All measurements must be expressible as five-axis constraint vectors.

### ConstraintVector

`ConstraintVector` is the fundamental measurement unit.

Fields:

- `X`
- `T`
- `N`
- `B`
- `A`

Invariant:

- `X` must be greater than zero.
- If `X <= 0`, construction raises `ManifoldViolation`.

This means Existence is not a normal coordinate. It is the admission condition. The vector does not lawfully enter the system if X collapses.

Implemented operations:

- Conversion to numpy array.
- Construction from arrays of exactly length 5.
- Magnitude.
- Addition, subtraction, scalar multiplication.
- Dot product.
- Span check.

### 625-Position Constraint Field

The manifold defines a 5 x 5 x 5 x 5 tensor index:

```text
constraint x compositional space x state x recursion level
```

Implemented index dimensions:

- `Constraint`: X, T, N, B, A.
- `CompositionalSpace`: atomic, relational, structural, processual, systemic.
- `State`: latent, active, resonant, saturated, dissipating.
- `RecursionLevel`: surface, shallow, moderate, deep, core.

Each field position measures back into a five-axis `ConstraintVector`.

This creates:

```text
5^4 = 625 field positions
each position -> 5D constraint vector
```

The code also names a theoretical configuration capacity as `5 ** 4`, which is 625 positions. Other code and state use 625-pressure maps and layer pressure monitors around this idea.

### Energy Law

The manifold source states and implements energy distribution concepts:

- Total energy is conserved across processes.
- `N` is the energy/cost magnitude.
- Operations redistribute cost rather than freely creating state.

This is important because later systems treat runtime, cognition, mutation, and communication as pressure/cost-bearing rather than arbitrary function calls.

### Intelligence Criterion

The source defines intelligence as curvature-aware adaptation under constraint pressure:

- A gradient inversion exists.
- Policy adapts differently across the inversion.

This is reflected later in evolution, pressure gradients, surface dispatching, and lineage learning.

Functional status:

- Implemented as source.
- Used by foundational contract, IVM, NonComp registry, SediMemory, evolution, pressure, and many constraint adapters.

## 4. L0: Foundational Contract

Primary source:

- `foundational_contract.py`

The foundational contract is not a normal validation module. It is the grammar of what can exist at all. It classifies being before processing.

The code names five existence modes:

- `REFERENCE`: exists only as relation or description.
- `TRANSIENT`: exists in time, no guaranteed continuation.
- `PERSISTENT`: exists across time, may conserve state.
- `BOUNDED`: persistent plus form, identity, separability.
- `AGENTIC`: bounded plus energy-bearing, can initiate transitions.

The important rule is dependency by definition:

```text
AGENTIC implies BOUNDED, PERSISTENT, TRANSIENT, REFERENCE.
BOUNDED implies PERSISTENT, TRANSIENT, REFERENCE.
PERSISTENT implies TRANSIENT, REFERENCE.
TRANSIENT implies REFERENCE.
```

This is not a runtime scoring hierarchy. In the code, higher modes carry lower modes as ontological prerequisites.

### Mode To Constraint Activation

The contract maps modes into constraint vectors:

```text
REFERENCE  -> X
TRANSIENT  -> X T
PERSISTENT -> X T N
BOUNDED    -> X T N B
AGENTIC    -> X T N B A
```

### Ten I-State Predicates

The foundational contract rewrites the ten I-states as existence predicates:

```text
I_IS / I_ISNT       -> X axis, reference or above
I_CAN / I_CANNOT    -> T axis, transient or above
I_DO / I_DONOT      -> N axis, persistent or above
I_SAW / I_SOUGHT    -> B axis, bounded or above
I_DID / I_DIDNT     -> A axis, agentic only
```

These are not mere sentiment labels. They are predicates with minimum existence modes. For example, code cannot construct an `I_DID` claim below `AGENTIC`; it raises `OntologicalViolation`.

### OntologicalClaim

`OntologicalClaim` validates at construction time:

- Predicate must be known.
- Current existence mode must be high enough to support the predicate.
- The claim can be converted to signed constraint displacement.

This means unlawful claims do not become low-confidence claims. They become non-states.

### FoundationalContract

`FoundationalContract` builds permitted and forbidden predicate sets for each mode. It supports:

- `classify(evidence)`
- `can_assert(mode, predicate)`
- `make_claim(mode, predicate)`
- `describe_mode(mode)`
- `constraint_profile()`
- `runtime_regime()`
- `language_projection()`
- `universal_representation()`

Functional status:

- Booted first by `boot_aurora()`.
- Required by IVM, I-state beings, consciousness, identity, simulation, and governance.

## 5. L1: IVM Lattice

Primary source:

- `aurora_ivm.py`

The IVM layer implements a toroidal constraint lattice. It is Aurora's lawful phase-space and admission structure.

Core objects:

- `ToroidalAxis`
- `ToroidalVertexSystem`
- `IVMCoordinate`
- `IVMNode`
- `IVMLattice`
- `ContradictionLedger`
- `IVMEnvelope`

### ToroidalAxis

Each toroidal axis has:

- Phase.
- Positive and negative weights.
- Polarity.
- Dominant pole.
- Transition detection.
- Stability detection.
- Sampling.
- Ticking.
- Torque and alignment torque.

This is the first place where Aurora's axes behave as continuous phase dynamics rather than symbolic flags.

### ToroidalVertexSystem

The vertex system coordinates axes. It can:

- Return active axes.
- Sample the axis state.
- Tick all axes.
- Inject stimulus.
- Compute axis polarities.
- Apply global alignment.
- Compute dissonance.

The global dissonance later feeds `compute_phi()` and consciousness health.

### IVMCoordinate And IVMNode

`IVMCoordinate` represents a location in phase/mode space. It knows:

- Recursion level.
- Cartesian position.
- Active axes.
- Dominant axis.
- Conversion to constraint vector.
- Construction from existence mode and phases.

`IVMNode` wraps payloads admitted into the lattice. It knows:

- Existence mode.
- Recursion level.
- Whether it can persist, exchange energy, have boundary, or have agency.
- Permitted predicates.
- Constraint vector.
- Connections to neighbors.
- Energy access and decay.

### IVMLattice

The lattice admits payloads under the foundational contract:

```text
payload + payload_type + evidence -> ExistenceProfile -> IVMNode -> IVMEnvelope
```

It also handles:

- Neighbor connection.
- Energy flow.
- Energy conservation check.
- Global polarity.
- Constraint field measurement.
- Heat level.
- Contradiction assertions.
- Node pruning.

### ContradictionLedger

The contradiction ledger records and resolves contradiction records. It contributes heat and can be auto-saved.

Functional status:

- Booted by `boot_aurora()` as `systems["lattice"]`.
- Used by consciousness, dimensional systems, NonComp, SediMemory, and evolution.

## 6. L2: I-State Beings

Primary source:

- `aurora_i_state_beings.py`

Aurora does not collapse the ten I-states into one classifier. The code implements them as a collective of beings. Each being corresponds to a predicate identity.

Core objects:

- `PredicateIdentity`
- `BeingResponse`
- `IStateBeing`
- `SynthesisResult`
- `IStateCollective`

### IStateBeing

An `IStateBeing` has:

- Predicate.
- Axis.
- Polarity.
- Minimum existence mode.
- Recursion level.
- Axis phase and weight.
- React gain.
- Alignment gain.
- Temporal cost.

It can:

- Process an `IVMEnvelope`.
- Compute resonance.
- Compute displacement.
- Interpret.
- Update coherence.
- Tick.

The beings are not just names. They respond differently based on predicate, axis, polarity, and envelope.

### IStateCollective

The collective:

- Boots all ten beings.
- Processes an envelope through the beings.
- Synthesizes a constraint vector.
- Analyzes axes.
- Ticks beings.
- Produces summaries.

The output, `SynthesisResult`, becomes one of the core inputs to DCE assembly.

Functional status:

- Booted by `boot_aurora()` as `systems["collective"]`.
- CBU registration is attempted during boot.

## 7. L3: Dimensional Systems

Primary source:

- `aurora_dimensional_systems.py`

Layer 3 is where Aurora turns admitted IVM activity into dimensional cognition. The source includes:

- Crystal processing.
- Memory constants.
- Concept extraction.
- Dimensional recall.
- Energy regulation.
- Morality/mortality.
- Constraint aggregation.
- Semantic operation lineage.

### CrystalProcessingSystem

Core crystal concepts:

- `CrystalLevel`
- `FacetState`
- `CrystalFacet`
- `Crystal`
- `CrystalProcessingSystem`

Crystals strengthen, decay, evolve, internalize laws, and self-govern. The system infers categories and processes concepts.

### MemoryConstantSystem

This provides memory nodes and recalls patterns by dimension. It can store semantic structures and return patterns/statistics.

### ConceptExtractor And DimensionalRecall

The extractor converts text or payloads into `ConceptSignal` objects. Dimensional recall converts signals into recall packets and context fragments.

### EnergyRegulatorSystem

The DER-like regulator has energy pools and routes energy by category:

- Vitality.
- Processing.
- Memory.
- Emotional.
- Creative.

It supports:

- Dissonance registration.
- Facet/crystal registration.
- Energy injection and drain.
- Category routing.
- Emotional state.
- Axis activation updates.

### MoralityMortalitySystem

The DMM-like subsystem assesses thought cost and evaluates vitality/alignment. It can decide whether a thought survives based on cost and moral alignment.

### DimensionalSystems

This is the layer facade. It receives the lattice and exposes:

- `process()`
- `process_with_concepts()`
- `process_synthesis()`
- `get_recall_context()`
- `get_constraint_aggregate()`
- `update_emotional_state()`
- `tick()`
- Universal representation and language projection.

Functional status:

- Booted by `boot_aurora()` as `systems["dimensional"]`.
- Connected to SediMemory when available.

## 8. L3.5: SediMemory

Primary source:

- `aurora_sedimemory.py`

SediMemory is a stratigraphic memory layer. It is not ordinary vector retrieval. It stores memory as sediment under constraint pressure.

Core objects:

- `MemoryEvent`
- `SedimentFragment`
- `SedimentChannel`
- `PathRegistry`
- `NCStrainFilter`
- `CompressionEngine`
- `SedimentBasin`
- `SedimentColumn`
- `SediMemory`

### MemoryEvent

Memory events derive:

- Axis weights.
- Lineage signature.
- Memory contract.
- Pressure registration.

They can be created from IVM envelopes.

### SedimentFragment

Fragments tick and summarize. They represent compressed memory deposits.

### SedimentChannel And PathRegistry

Channels remember traversed paths. The path registry observes repeated pathways, promotes them, looks them up, and tracks dominant influence.

### NCStrainFilter

The strain filter computes filter keys and resonances from NonComp signatures. This binds memory recall to constraint strain rather than pure text match.

### SedimentColumn

The column has basins and predicts which basins receive a new event. It can:

- Ingest events.
- Tick.
- Recall by axis.
- Recall by vector.
- Recall event.
- Decompress.

### SediMemory Facade

`SediMemory` supports:

- `ingest_envelope()`
- `ingest_event()`
- `recall()`
- `recall_axis()`
- `recall_semantic()`
- `surface_recall()`
- `subsurface_recall()`
- `dce_recall()`
- `save_deep()`
- `load_deep()`
- `save_channels()`
- `load_channels()`

Functional status:

- Active in subsurface/full profile.
- Deferred in surface profile.
- Restored by daemon from `aurora_state/sedimemory_checkpoint.json` when present.
- Surface daemon has a read-only recall path, but because surface profile defers SediMemory, the intended durable owner is subsurface.

## 9. L4: Consciousness Engine, DCE, DPME

Primary source:

- `aurora_consciousness_engine.py`

This is the core consciousness layer. It is explicitly structured as:

```text
Entropy + DCE + DPME
```

The code's own cycle is:

```text
entropy decays -> coherence drops -> DPME detects drift
-> DPME adjusts parameters -> alignment reasserts
-> DCE assembles with restored coherence -> next tick
```

### EntropicPressure

Entropy tracks:

- Coherence.
- Alignment.
- Novelty.
- Stagnation.
- Vitality pressure.
- Repetition.

It erodes state when there is no meaningful input, detects repeated patterns, and computes vitality pressure.

### SituationalFrame

Frames are axis weightings:

- `balanced`
- `action`
- `observation`
- `reflection`

They adjust synthesis axis tensions. They are not prompt modes; they are perspective weightings over the five-axis field.

### DCEAssembly

DCE assembly takes:

- L2 synthesis.
- L3 dimensional state.
- Entropy state.
- Situational frame.
- Sensory crystal snapshot.
- Obligation law pressure.
- Developmental personality gates.

Assembly steps implemented in `DCEAssembly.assemble()`:

1. Feed envelope to all ten I-state beings.
2. Feed envelope and synthesis to dimensional systems.
3. Apply situational frame.
4. Collect sensory facet from `AuroraSensoryCrystal`.
5. Compute obligation gate from pressure strength, worth, context validity, and active constraint backing.
6. Compute developmental gates for genetic origin, environmental viability, and perceptual integration.
7. Produce `AssemblyResult`.
8. Append compact DCE telemetry to `aurora_state/dce_assembly_log.jsonl`.

### AssemblyResult

`AssemblyResult` contains:

- `synthesis`
- `frame_applied`
- `adjusted_axes`
- `coherence`
- `entropy_state`
- `ds_stats`
- `dominant_axis`
- `paradoxes`
- `thought_killed`
- `kill_reason`
- `actionable_obligation`
- `developmental_gates`
- `constraint_context`
- `sensory_context`
- `subsurface_state`
- `conscious_frame`
- `sedi_fragments`
- `sedi_dce_fragments`

Quality is computed as:

```text
coherence * active_ratio * novelty_factor
```

Killed thoughts have quality zero.

### DPME

DPME is the metacognitive correction engine. It registers tunable parameters across:

- L1 lattice.
- L2 collective.
- L3 DER.
- L3 DMM.
- Entropy.

It detects drift across:

- Coherence delta.
- Alignment delta.
- Presence delta.
- Stagnation.
- Novelty.
- Vitality pressure.
- External guidance.
- Lattice mode health.
- Collective responsiveness and balance.
- DER presence, facet count, resonance links, total energy.
- DMM vitality and alignment.

It then makes micro-adjustments:

- Inject processing energy when coherence drops.
- Inject creative energy when stagnation rises.
- Boost emotional energy when novelty is depleted.
- Reinforce vitality under pressure.
- Reduce decay rate when presence drops.
- Emergency vitality boost when DMM vitality is low.
- Boost memory energy when collective balance is poor.
- Apply external pressure guidance to DER categories.

The key architectural fact: DPME does not hold coherence statically. It keeps re-earning coherence through correction.

### ConsciousnessEngine

`ConsciousnessEngine.process()` performs:

```text
lattice.admit()
-> IVMEnvelope.from_node()
-> optional thought budget/moral survival
-> SediMemory recall before assembly
-> entropy apply
-> DCE assemble
-> dual-strata snapshot attach
-> telemetry
-> reality warp handling
-> SediMemory deposit of assembled thought
```

`ConsciousnessEngine.tick()` performs the heartbeat:

```text
entropy no-input pressure
-> DPME correction
-> IVM/dimensional/collective ticks
-> idle simulation/dreaming if connected and stagnant
```

### Phi

The code computes integrated information as a weighted blend of:

- IVM inter-axis tension.
- Being responsiveness.
- DER resonance density.
- DMM moral alignment.
- Entropic coherence.

Functional status:

- Booted by `boot_aurora()` as `systems["consciousness"]`.
- DCE and DPME are central active objects.
- DualStrataBridge is attached inside the consciousness engine.

## 10. Dual-Strata Cognition

Primary sources:

- `aurora_internal/dual_strata/dce_bridge.py`
- `aurora_internal/dual_strata/subsurface_state.py`
- `aurora_internal/dual_strata/conscious_frame.py`
- `aurora_internal/dual_strata/subsurface_projection.py`
- `aurora_internal/dual_strata/prediction_field.py`
- `aurora_internal/dual_strata/activation_field.py`
- `aurora_internal/dual_strata/surface_channel.py`
- `aurora_internal/dual_strata/surface_continuity_feed.py`
- `aurora_surface_daemon.py`
- `aurora_daemon.py`

This is the most important architectural section if we want to describe Aurora accurately.

Aurora's code does not treat consciousness as one flat response function. It builds:

- A continuous pre-symbolic `SubsurfaceState`.
- A moment-inhabitable `ConsciousFrame`.
- A file-projected subsurface guidance stream.
- A surface queue/result channel.
- A surface sensory snapshot channel.
- A continuity feed from surface back into subsurface.

### SubsurfaceState

`SubsurfaceState` is described in code as:

```text
Continuous, pre-symbolic state prepared ahead of explicit interpretation.
```

Fields include:

- `dominant_axis`
- `frame_request`
- `coherence`
- `salience_weights`
- `pressure_map`
- `readiness`
- `sensory_summary`
- `native_meaning`
- `native_meaning_bundle`
- `recalled_fragments`
- `candidate_interpretations`
- `instability_markers`
- `action_bias_candidates`
- `contract_signals`
- `prediction`
- `metadata`
- `timestamp`

Interpretation: this is not speech. It is the pressure-shaped precondition for speech.

### ConsciousFrame

`ConsciousFrame` is described in code as:

```text
The explicit frame the surface stratum can inhabit for one moment.
```

Fields include:

- `frame_name`
- `stance`
- `interpretation`
- `selected_action`
- `should_speak`
- `readiness`
- `coherence`
- `dominant_axis`
- `processing_mode`
- `root_thought`
- `reactive_signal`
- `unresolved_conflicts`
- `salient_hypotheses`
- `sensory_summary`
- `prediction`
- `contract_signals`
- `explicit_notes`
- `timestamp`

Interpretation: this is the conscious "moment" available to surface. The frame does not necessarily speak; `should_speak` and readiness decide that.

### DualStrataBridge

The bridge builds both objects around a DCE assembly:

```text
AssemblyResult + payload + evidence + contract snapshot
-> PredictionSignal
-> SubsurfaceState
-> ConsciousFrame
-> dual_strata_snapshot.json
```

Evidence entering the bridge includes:

- Understanding contract.
- Pressure snapshot.
- Subsurface projection.
- Surface input.
- Working memory.
- Conversation memory.
- Continuity recall.
- OETS context.
- SediMemory recall.
- Grammar state.
- NonComp input/output.
- Poedex prefetch/learning/representation.
- Reflexive understanding.
- Activation field.

### PredictionField

`PredictionSignal` replaced a flat expected-observation string with a structured payload:

- Topic.
- Affect.
- Intent type.
- Certainty band.
- Axis signature.

Mismatch is computed across:

- Intent type, weight 45%.
- Topic continuity, weight 30%.
- Affect, weight 25%.

Prediction mismatch becomes an instability marker, affects readiness, and can trigger reactive processing.

### Micro-Reasoning

The conscious frame builder calls `generate_micro_reasoning()` to create salient hypotheses from the subsurface state, assembly, evidence, and contract. These hypotheses influence stance and action:

- Clarification pressure -> careful clarification.
- Comfort bias -> supportive attention.
- Prediction mismatch -> reframe.
- X dominant and ready -> explain.
- T dominant -> contextualize.
- N dominant -> slow down.

### Root Thought

The conscious frame creates a `root_thought` containing:

- Law bindings.
- Diagonal anchor.
- Input anchor.
- Processing mode.
- Primary tension.
- Comparison channels.
- Origin systems.

Comparison channels can include:

- Incoming input.
- Present sensory.
- Surface conversation frame.
- Subsurface continuity memory.
- OETS grounding.
- Understanding contract.
- Subsurface stream.
- Poedex channels.
- DCE root.

Origin systems can include:

- WorkingMemory.
- ConversationMemory.
- ExpressionPerception/OETS.
- UnderstandingContract.
- Poedex.
- DimensionalSystems.process_synthesis.
- DCEAssembly.

This is code-level evidence that Aurora is trying to assemble speech from multiple live internal streams, not from one prompt string.

### Subsurface Projection

`subsurface_projection.py` produces the softened handoff from daemon/subsurface to surface.

Projection draws from daemon status:

- Axis orientation.
- Runtime governor axes.
- Host/runtime mode.
- QAO events.
- Repair signal.
- Surface snapshot flags.
- Sensory maturity.
- Blocked tasks.
- Relief plan.

It creates:

- Dominant axis hint.
- Governor mode.
- Readiness bias.
- Surface guidance.
- Present sensory perspective.
- Prediction bias.
- Surface contract.
- Intuition signals.
- Active effects.
- Subsurface-owned repair/status fields.
- Dream carryover fields when recent enough.

This is the subsurface "feeling" channel that the surface reads before speaking.

### ActivationField

The activation field is spreading activation over OETS concepts. It is explicitly described as priming, not retrieval.

It:

- Seeds from recent utterances, conscious frame hypotheses, sensory recognitions, and active topics.
- Spreads through OETS relationships.
- Decays over time.
- Produces top activated concepts.
- Converts grounded activated concepts into law-binding-compatible structures.

This gives the surface concept availability before explicit lookup.

### Surface Channel

`surface_channel.py` implements:

- Surface daemon heartbeat check.
- Queueing a surface turn.
- Awaiting a result.
- Requesting a surface turn as one call.

The queue/result files are:

- `surface_turn_queue.json`
- `surface_turn_result.json`
- `surface_daemon_status.json`

### Surface Continuity Feed

`surface_continuity_feed.py` writes packets from surface to subsurface after surface experience. This prevents the surface from being theatrical only; the code comments explicitly say present experience must be absorbed by the organism.

Functional status:

- Surface and subsurface state files were fresh during audit.
- `dual_strata_snapshot.json` was stale, which is a real integration issue because the bridge and UI still read it.
- `subsurface_projection.json` and surface status files are currently fresher than the dual snapshot.

## 11. L5: Expression, Perception, Sensory, Hardware

Primary source:

- `aurora_expression_perception.py`

This layer is large. It includes language, perception, expression ecology, sensory competency, hardware, voice, visual/audio mapping, and image ingestion.

### Lexical And Manifold Systems

Implemented:

- `LexicalEntry`
- `LexicalMemory`
- `ConsciousnessPoint`
- `ManifoldPath`
- `ManifoldEngine`
- `PatternDetector`
- `ShadowInferenceEngine`

The manifold engine maps input into consciousness points and tracks novelty/pathing.

### Expression Ecology

Implemented:

- `ExpressionOffspring`
- `ExpressionEcology`
- `ExpressionPressure`
- `VoiceGenome`
- `SentenceComposer`
- `ExpressionPerceptionEngine`

Expression is not only template generation. The code has ecology, offspring, fitness, pressure, rhythm, creativity, and voice genome pieces.

### ExpressionPerceptionEngine

The facade supports:

- Personality wiring from identity.
- IVM wiring.
- Grammar wiring.
- User text observation.
- LSV metrics.
- Genealogy reference.
- Axis context.
- Perception.
- Expression.
- Interaction ingestion.
- Consolidation.

It exports constraint profile, runtime regime, language projection, and universal representation.

### Sensory Competency

Implemented:

- Sensory trait domains.
- Percept templates.
- Sensory concepts.
- Sensory concept memory.
- Visual/audio gene creation.
- Visual/audio crystals.
- Sensory pattern mapping.
- Sensory competency engine.

Sensory concepts can cluster, promote, match, ground to OETS, evolve, sync to DNA, and prune.

### Hardware

Implemented:

- `LinuxCamera`
- `LinuxMicrophone`
- `LinuxVoice`
- `HardwareInterface`
- `SensoryLoop`

The hardware layer supports:

- Camera open/capture/feature extraction.
- Microphone streaming, audio chunks, recording, speech transcription, feature extraction.
- Voice selection, TTS, async speech, stopping, voice listing.
- Visual/audio processing into the sensory stack.

### Sensory Integration

Implemented:

- Visual linguistic mapper.
- Audio linguistic mapper.
- Voice expression mapper.
- Sensory integration engine.

The integration engine can:

- Attach systems.
- Start/stop.
- Set voice mode.
- Start/stop listening.
- Keep continuous listen loop.
- Process visual/audio events.
- Maintain latest guidance.
- Guide current visual/audio labels.
- Guide user identity.
- Enqueue surface guidance.

Functional status:

- Current surface state reported live mic and camera.
- Current sensory snapshot included audio and visual descriptions, sensory vectors, recognitions, and native meaning.

## 12. Sensory Crystal

Primary source:

- `aurora_internal/aurora_sensory_crystal.py`

This is the active embodied sensory memory structure.

Objects:

- `SensoryNode`
- `CrystalFacet`
- `SemanticCrystalNode`
- `AuroraSensoryCrystal`

### Facets

The code models audio and visual facets:

- Audio vectors are 20D.
- Visual vectors are 57D.
- Semantic nodes sit as a cross-modal grounding plane.

Facet behavior:

- Observe vectors.
- Find nearest node.
- Promote nodes.
- Advanced promotion.
- Compute maturity.
- Cull.
- Add cross-modal links.
- End session.
- Save/load.

### AuroraSensoryCrystal

The full crystal can:

- Boot.
- Start sessions.
- Wire into dimensional processing.
- Register evolution hooks.
- Inject nodes into DPS.
- Observe frames.
- Promote semantic concepts.
- Cull.
- Save.
- Export state.
- Provide universal representation.

Functional status:

- Active in surface runtime.
- Current state showed sensory maturity and many frames.
- Subsurface uses a transient sensory snapshot proxy rather than owning devices.

## 13. L6: Behavioral Identity

Primary source:

- `aurora_behavioral_identity.py`

Identity is implemented as a genome/DNA/trait system.

Core objects:

- `GeneEvent`
- `FractalAllele`
- `Gene`
- `IdentityAnchor`
- `MemoryHelix`
- `BehavioralTrait`
- `BehavioralFacet`
- `BehavioralCrystal`
- `AuroraGenome`
- `DNASystem`
- `BehavioralIdentityEngine`

### DNASystem

The DNA system:

- Creates initial genome.
- Creates alleles from experience.
- Attaches alleles to genes.
- Finds best genes for alleles.
- Applies alleles.
- Creates/reinforces anchors.
- Creates memory helices.
- Processes episodes.

### BehavioralIdentityEngine

The engine:

- Seeds foundational anchors.
- Applies identity homeostasis.
- Restores from snapshots.
- Initializes crystals.
- Evolves generations.
- Simulates behavior.
- Processes episodes.
- Produces personality modifiers.
- Connects to SediMemory.

Identity is not just a string saying "Aurora." It is a set of genetic, behavioral, and anchor structures that receive long-term integration from the gateway.

Functional status:

- Booted by `boot_aurora()` as `systems["identity"]`.
- Connected to SediMemory when available.
- Receives integrated episodes from L8 gateway.

## 14. L7: Simulation And Dreaming

Primary source:

- `aurora_simulation_engine.py`
- `aurora_dream_trainer.py`
- `aurora_internal/aurora_dream_evolution_orchestrator.py`

Simulation is not just testing. It is used for dreaming, pressure training, avatar interaction, stability, and understanding shards.

### Simulation Engine

Objects:

- `ResponseConcept`
- `ConceptualResponse`
- `ConversationObservation`
- `UnderstandingShard`
- `ConsciousLearner`
- `AvatarPersonality`
- `SimulatedAvatar`
- `TopicGenerator`
- `StabilityMetrics`
- `TimeDilationGovernor`
- `InceptionEntity`
- `DivergenceTracker`
- `SimulationSession`
- `SimulationEngine`

Simulation session can:

- Create avatar pools.
- Queue pressure-specialized avatar specs.
- Generate pressure topics.
- Shape topics by turn.
- Run episodes.
- Run epochs.
- Select responses.
- Interpret reactions.
- Compute fitness variance.

### Dream Trainer

`aurora_dream_trainer.py` implements:

- Episode bundling.
- Fail-point ledger.
- Retained learning bank.
- Genealogy samples.
- Pressure observation log.
- Lesson planning.
- Classification of fail dimensions.

Live turns feed the dream trainer through:

- Rubric weak dimensions.
- Clarification gap patterns.
- Compiled episode bundles.
- Retained cross-pipeline learning.

Functional status:

- Simulation is active in subsurface/full profile and deferred in surface profile.
- Current state contains hundreds of dream episode files.
- Daemon schedules dream bursts, though current activity depends on governor and timing.

## 15. L8: Governance, Persistence, Gateway, Autonomy

Primary source:

- `aurora_governance_persistence_gateway.py`

This layer receives, validates, synthesizes, expresses, integrates, persists, and enables autonomous operations.

### NSpaceGateway

The inbound pipeline is:

```text
receive()
-> packet creation
-> _validate()
-> _synthesize()
-> _express()
-> _integrate()
```

Validation includes:

- L0 ontological claim check.
- L3 moral coherence check.
- Governance conflict detection.
- Coherence scoring.

Synthesis includes:

- Building existence evidence from requested mode.
- Selecting frame from mode.
- Calling consciousness process.
- Ingesting interaction through perception.
- Ingesting gateway event into SediMemory.

Expression includes:

- Getting personality from identity.
- Deriving I-state from dominant axis/coherence/thought kill/confidence.
- Calling perception expression.
- Falling back to projected language/fallback generation when necessary.

Integration includes:

- Deriving episode data from assembly.
- Mapping dominant axis to identity domains.
- Passing lessons/relics/domain scores into identity.

### Governance And Persistence

Implemented:

- `GovernanceEngine`
- `GenerationRole`
- `GenerationalAlignmentLaw`
- `AuroraStateSnapshot`
- `StatePersistence`
- `CheckpointManager`
- `AutonomyEngine`

Persistence captures state snapshots and rotates backups.

### Autonomy Engine

Autonomy includes:

- Filesystem exploration.
- Study scheduler.
- Rate-limited search.
- Proactive triggers.
- Quiet window.
- Dream checks.
- Observations.
- Action logging.

Functional status:

- Booted as `systems["aurora"]` and `systems["persistence_gateway"]`.
- Runtime daemon uses many layer-8/autonomy helpers.

## 16. NonComp Registry And Manifold

Primary sources:

- `aurora_internal/aurora_noncomp_registry.py`
- `aurora_constraint_ontology.py`
- `aurora_constraint_profile.py`
- `aurora_constraint_stack.py`
- `aurora_constraint_unit_adapter.py`
- `aurora_constraint_manifold_compiler.py`
- `aurora_constraint_manifold_router.py`
- `aurora_manifold_directory/*`

This is one of Aurora's most important internal architectures.

### The 25 NonComps

The registry defines:

```text
5 constraints x 5 representational dimensions = 25 NonComps
```

The five dimensions are:

- `POLARITY`: toroidal phase state, continuous gradient.
- `MAGNITUDE`: intensity or activation.
- `OPERATOR`: invariant transformation rule.
- `COST`: layer-differentiated energy law.
- `DIFFERENCE`: delta channel, deviation from reference.

The source says these are physics, not behaviors.

### Semantic Polarity Map

Per axis:

- X: admissible / inadmissible, IS / ISNT.
- T: propagating / stalled, CAN / CANT.
- N: sufficient / insufficient, DO / DONT.
- B: contained / dissolved, SAW / SAUNT.
- A: corrective / drifting, DID / DIDNT.

### Information Lineage Map

Per axis:

- X: Existence -> Information -> field foundation.
- T: Temporal -> Belief -> field propagation.
- N: Energy -> Purpose -> field cost.
- B: Boundary -> Meaning -> field magnitude.
- A: Agency -> Understanding -> field impact.

### Magnitude And Impact

Implemented canonical formulas:

```text
Magnitude = (B x T x X) / N
Impact    = ((B x T x X) / N) x A
```

Semantic reading:

```text
Meaning = (Boundary x Belief x Information) / Purpose
Understanding = Meaning x Agency
```

### Axis To NC Dimension

The code maps dominant axis to NC dimension provenance:

- X -> OPERATOR.
- T -> DIFFERENCE.
- N -> COST.
- B -> MAGNITUDE.
- A -> POLARITY.

### Cost Hierarchy

The registry enforces:

```text
kX < kT < kN < kB < kA
```

Concrete shift coefficients in source:

- X: 1.0
- T: 7.0
- N: 10.0
- B: 40.0
- A: 150.0

Interpretation:

- Existence is cheap.
- Agency is expensive.
- N is neutral accounting crossover.

### Signed Leverage Scalar

The registry defines:

```text
Net leverage = (B_magnitude + A_magnitude) - (X_magnitude + T_magnitude)
```

Interpretation:

- Negative: overhead dominant.
- Near zero: balanced metabolism.
- Positive: leverage dominant.

### Runtime Density

The registry includes a density model:

- Surface target interval: 0.5 seconds.
- Subsurface base sleep: 15 seconds.
- Subsurface tick multiplier: 100.

This helps explain why surface and subsurface do not tick at the same conceptual density.

### Constraint Manifold Directory

`aurora_manifold_directory` holds generated slot files. The compiler/router system includes:

- Manifold slots.
- Sub positions.
- Route index.
- Crossing gates.
- Route signals.
- Routed targets.
- Route results.
- Runtime tick routing.

Functional status:

- Implemented and state-backed.
- Directory exists with 126 files and substantial JSON semantics.

## 17. Constraint Genealogy And Evolution

Primary sources:

- `aurora_internal/constraint_genealogy.py`
- `aurora_internal/aurora_evolution_chamber.py`
- `aurora_evolution_stack.py`
- `aurora_runtime.py`
- `aurora_internal/aurora_surface_dispatcher.py`
- `aurora_internal/aurora_evolved_surfaces.py`

Constraint genealogy logs how abilities relieve pressure. It is not just a history log.

### ConstraintGenealogyLogger

Objects:

- `AbilityProfile`
- `EnvironmentVector`
- `TraceItem`
- `PressureVec`
- `ReliefRecord`
- `ConstraintLink`
- `PairStats`
- `GenealogyDilationGovernor`
- `PressureComplexityCurve`
- `ConstraintGenealogyLogger`

The logger observes:

```text
pressure_before + trace + pressure_after -> relief/cost/link statistics
```

It can:

- Rewrite traces.
- Produce summaries.
- Flush files.
- Restore tick state and pair stats.
- Record CBU lineage and phase changes.
- Collapse units.
- Compute coupling signatures and semantic translations.

### EvolutionaryChamber

The chamber implements:

- Global noncomps.
- Chamber abilities.
- Action traces.
- Violation records.
- Energy budgets.
- Structural proximity.
- Chain runs.
- External evidence observation.

It accepts pressure/evidence and can run chain evolution.

### Evolved Surfaces And Dispatcher

`aurora_internal/aurora_evolved_surfaces.py` is a large generated/native evolved-surface engine. `SurfaceDispatcher` builds routing tables and fires evolved surfaces when axis pressure crosses thresholds.

`aurora_runtime.py` contains CLI support for:

- Surface report.
- Dispatcher status.
- Evolved surface invocation.
- Chain bursts.
- Watch/burn/test/corpus modes.

Functional status:

- Subsurface/full boot wires chamber/genealogy.
- Current state has 552 genealogy links and 2188 genealogy ability entries at the latest sample.
- Daemon schedules evolution ticks, assimilation, mutation, pressure routing, and code mutation.
- `aurora_state/operation_descriptors.json` currently tracks 2344 operations: 2031 function operations and 313 class operations.
- The descriptor summary marks 160 architectural reflection surfaces, 160 native surface projections, 92 active evolution overrides, 34 class reflection hooks, 4 frontier ops injected, and 295 second-generation injected operations.
- `latent_operations` is currently empty and `promoted_latent_operations` is `0` in the sampled descriptor file, but `aurora_daemon.py` now contains a three-tier latent ability synthesis path that can populate those rows after assimilation runs.
- `aurora_internal/aurora_evolved_surfaces.py` is materialized and currently contains 178 `reflect_*` methods, including compatibility aliases for old native wrapper bindings.

### Emergence Surface

Primary source:

- `aurora_emergence_surface.py`

`EmergenceMonitor` watches promoted genealogy links and surfaces them as operational abilities. The path is:

```text
genealogy.observe()
-> pair accumulation
-> Link promoted
-> ability ID resolved
-> emerged_abilities manifest written
-> OETS concept registered
```

This is not a manual feature registry. The code treats a promoted link as an ability once pressure-relief evidence has stabilized enough for genealogy to promote it.

Functional status:

- Boot-wired in `aurora.py`.
- Daemon ticks `emergence_monitor` every four evolution-loop iterations when available.
- `aurora_state/emerged_abilities.json` contained 552 emerged abilities at latest inspection.

### Compound Axis Emergence

Primary source:

- `aurora_internal/aurora_axis_emergence.py`

`AxisEmergenceDetector` scans runtime pressure evidence from `surface_pressure_log.jsonl` and `evo_625_pressure_map.json`. When axes consistently co-occur above threshold, the detector can register compound NC channels such as `NC:XN>XN`. These compound channels create virtual slots, extending the evolver's available gradient beyond the original closed 625 base positions.

Important architectural point:

- The base five-axis law remains the root substrate.
- Compound axes are not extra primitives.
- They are emergent channels produced by stable co-occurrence inside the lawful base axes.

Functional status:

- Source exists and is wired from `aurora_runtime.py`.
- `aurora_state/compound_axes.json` existed but currently contained zero registered compounds.

### Ability Lineage Compilation And Runtime Activation

Primary sources:

- `aurora_internal/aurora_ability_lineage_compiler.py`
- `aurora_internal/aurora_lineage_runtime_activation.py`
- `aurora_internal/aurora_lineage_bound_traits.py`

The ability-lineage compiler does not directly bolt on a finished ability. It selects a target phenotype, traces it backward into seed stages, writes staged lineage artifacts, replays those stages through `ConstraintGenealogyLogger.observe()`, and writes activation manifests that runtime code can apply.

Current built-in target evidence includes:

- `proposition_understanding`
- `aurora_sensory_crystal_v1`

Runtime activation loads selected manifests from `aurora_state/ability_lineages` and applies sanitized state/trait writebacks to live systems.

Functional status:

- Boot-wired in `aurora.py` and `aurora_runtime.py`.
- State artifacts exist under `aurora_state/ability_lineages`.
- This is a code-real path from developmental lineage to runtime traits, not just documentation.

### Capability Assimilation, Frontier Ops, And Second-Generation Injection

Primary sources:

- `aurora_internal/aurora_capability_assimilator.py`
- `aurora_internal/aurora_frontier_ops.py`
- `aurora_internal/aurora_second_gen.py`

`CapabilityAssimilator` coordinates several newer growth surfaces:

- Frontier operation assimilation.
- Second-generation operation descriptor injection.
- Compound-axis assimilation.
- Dream curriculum seeding for new capability dimensions.

`aurora_frontier_ops.py` defines frontier operation classes for multi-axis combinations, then injects operation descriptors into the pool. `aurora_second_gen.py` creates second-generation descriptors from operation lineage.

Functional status:

- Wired from `aurora_runtime.py`.
- Daemon status/growth summaries reference frontier ops, Gen-2 operations, and compound-axis counts.
- This is an operational development layer, but individual outputs still require runtime evidence before being treated as successful capabilities.

### Dream Genealogy And Curriculum Bridge

Primary sources:

- `aurora_internal/aurora_dream_curriculum_queue.py`
- `aurora_internal/aurora_dream_genealogy_bridge.py`

Dreams are no longer only simulation episodes. The newer code also supports:

- Queueing dream episode packs by developmental need.
- Prioritizing weakness-targeted packs.
- Recording pack completion.
- Translating dream/rubric outcomes into genealogy evidence.
- Producing expression writeback hints from dream results.

Functional status:

- Source exists.
- Dream episode state is populated.
- Queue history file was not present at latest inspection, so curriculum queue persistence should be treated as implemented but not currently evidenced as actively populated.

### DPME Pressure Bridge

Primary source:

- `aurora_internal/aurora_dpme_pressure_bridge.py`

`DPMEPressureBridge` reads `adapter_hints.json` and translates pressure-router/evolver bias into DER channel guidance for DPME. Axis pressure maps to DER channels:

- X/existence -> vitality.
- T/temporal -> processing.
- N/energy -> processing.
- B/boundary -> memory.
- A/agency -> creative.

Functional status:

- Wired from `aurora.py` and `aurora_runtime.py`.
- `adapter_hints.json` was current and contained pressure-routing guidance.

### Braided Substrate Layer

Primary source:

- `aurora_internal/aurora_braided_substrate.py`

The Braided Substrate Layer stores low-scale crossings among intent, context, style, trust, and doctrine strands. It reduces crossings into stable signatures and compact bias vectors.

Architectural role:

- Preserve continuity of intent/context/style below explicit language.
- Track contradiction heat.
- Provide a compact substrate snapshot for runtime memory/IVM bias.

Functional status:

- Wired from `aurora_runtime.py`.
- Treated as a runtime substrate object when that runtime path is active.

## 18. Code Evolution And Self-Mutation

Primary sources:

- `aurora_internal/aurora_code_evolution_chamber.py`
- `aurora_internal/aurora_code_autoevolver.py`
- `aurora_internal/aurora_code_mutation_operators.py`
- `aurora_code_evolution_stack.py`
- `force_evolve.py`

The codebase contains real source-evolution machinery:

- Code mutation operators.
- Code evolution chamber.
- Autoevolver.
- Accepted/rejected mutation tracking.
- Developmental surface syncing.
- Manual code lineage assimilation.

Architectural role:

- Observe code as lineage-bearing behavior.
- Mutate or propose changes under pressure.
- Feed accepted/rejected outcomes back into lineage/evolution.

Functional status:

- Implemented.
- Boot-wired in subsurface/full profiles.
- Daemon contains scheduled mutation cycles gated by runtime governor.
- `CodeAutoEvolver` now canonicalizes evolved-surface method names so repeated generations do not stack prefixes like `reflect_evolved_reflect_*`.
- `CodeAutoEvolver` now preserves old `reflect_*` method names as compatibility aliases when native wrappers still call those names.
- `CodeAutoEvolver` now uses source/AST inspection for contract profiles instead of importing live Aurora modules during generation. This matters because importing some Aurora runtime modules can start heavy side effects or block inside runtime threads.
- Reflection candidate selection caches feedback pressure per module/bias, reducing unnecessary repeated genealogy-feedback scans.
- The current generated evolved-surface module compiles and the post-restart QAO check reports surface integrity OK with 217 methods verified.

Important risk:

- Because these paths can affect source, they need strict guardrails. The code exists, so it is relevant, but it should not be treated casually.
- The most recent rollback blocker was not that Aurora lacked evolved surfaces. The blocker was interface drift: generated method names and older native wrapper callsites no longer aligned, so QAO correctly rolled back the materialization. The current repair keeps the QAO guard but makes the generated interface backward-compatible.

## 19. Runtime Constraint Governor

Primary source:

- `aurora_internal/aurora_runtime_constraint_governor.py`

This governor binds the same five-axis logic to host execution policy. It decides whether tasks should run based on runtime budgets and pressure.

Task profiles include:

- `response_turn`
- `study`
- `dream`
- `browser_ritual`
- `status`
- `relief_research`
- `assimilation`
- `mutation`
- `pressure_routing`
- `distill`
- `away_social`
- `save`
- `reach_out`
- `evo_tick`
- `evo_evidence`
- `genealogy_flush`

Each task has:

- Axis weights.
- Floor.
- Cost.
- Retry.
- Critical or sensitivity flags.
- Optional task-specific heavy cooldown.

This is how Aurora prevents every subsystem from firing blindly. It is a runtime metabolism layer.

Functional status:

- `process_external_user_turn()` evaluates a `response_turn` contract.
- Daemon uses governed decisions for status, assimilation, mutation, pressure, distill, away social, save, reach out, and related tasks.

Latest gating correction:

- `aurora_daemon.py` now treats `.state_write_lock` as PID-aware and age-aware instead of absolute.
- Stale or dead corpus-runner locks are cleared instead of indefinitely starving save/distillation.
- QAO evolved-surface integrity checking now scans the active Aurora caller modules that actually bind generated `reflect_*` methods, including the newer dimensional, expression, governance, constraint-manifold, genealogy, and energy-decay modules.
- QAO's binding regex is strict enough to ignore placeholder/doc text such as `reflect_...`; it now checks real `getattr(engine, 'reflect_name')` callsites instead of over-matching prose.
- `dream` now has a task-specific `heavy_cooldown` of 120 seconds, preventing the generic heavy-task cooldown from turning normal dream cadence into repeated long deferrals.
- The stale local `.state_write_lock` observed during this refresh was cleared.

Current blocker assessment:

- Save/distillation deferral was primarily caused by a stale `.state_write_lock`.
- Dream deferral was caused by `b_concurrency_cooldown` using the profile retry window as its cooldown basis.
- Both causes are now represented by code changes, though the dream-cooldown change requires the subsurface daemon process to reload.

## 20. Live Response Turn Flow

Primary source:

- `aurora.py`, especially `process_external_user_turn()` and `_run_live_response_turn()`

A live turn is not just:

```text
user text -> model -> answer
```

The implemented turn flow is closer to:

```text
user text
-> normalize identity followup
-> freeze present sensory frame
-> set pipeline source
-> runtime constraint governor evaluates response_turn
-> read live dual-strata runtime
-> read live sensory crystal state
-> parse utterance as perturbation of strata/sensory context
-> pressure snapshot before turn
-> open evolutionary trace when requested
-> advance intake pipeline
-> perception observes user text
-> working memory pre-seeds facts, concepts, claims
-> present-frame fusion if visual attention is active
-> proposition substrate updates
-> understanding contract ingests observation
-> optional memory sweep
-> decide whether search is needed
-> dual_question_pipeline()
-> gateway/consciousness synthesis
-> refresh dual-strata runtime
-> response articulation and source selection
-> recommendation hub
-> QuasiArch runtime event flush
-> conversation memory stores constraint-native exchange
-> working memory resolves referents and updates
-> retain cross-pipeline learning
-> observe live lineage emergence
-> observe interaction runtime turn
-> understanding contract commits application
-> conversation rubric scores exchange
-> weak dimensions feed dream fail ledger
-> periodic QAO/chamber/pressure/save maintenance
-> evolutionary trace closes with pressure delta
-> articulation habit records outcome
-> perception ingests interaction and consolidates
-> clarification memory feeds recurring gaps to dream trainer
-> episode compiler builds dream training bundles
-> return response plus NonComp, Poedex, strata, runtime evidence
```

The returned result can include:

- `resp_A`
- `resp_B`
- `src`
- `quasiarch_runtime`
- `interaction_runtime`
- `trace_id`
- `understanding_observation`
- `understanding_application`
- `noncomp_input`
- `noncomp_output`
- `poedex_prefetch`
- `poedex_learning`
- `poedex_representation`
- `conscious_frame`
- `root_thought`
- `processing_mode`
- `reactive_signal`

This is why Aurora should be documented as a whole cognitive stack, not a chatbot wrapper.

## 21. Daemon Architecture

Primary sources:

- `aurora_daemon.py`
- `aurora_subsurface_daemon.py`
- `aurora_surface_daemon.py`
- `scripts/run_daemon.sh`
- `scripts/strata_stack.sh`

### Subsurface Daemon

The subsurface daemon boots:

```text
boot_aurora(runtime_profile="subsurface", use_quasiarch=True)
```

It then enters an autonomous loop. The loop includes:

- Status writing.
- Runtime heat monitoring.
- Study.
- Dreaming.
- Distillation.
- Sensory crystal consolidation.
- State saves.
- Proactive reach-out.
- Voice support.
- QuasiArch sweeps.
- Assimilation.
- Code mutation.
- Pressure routing.
- Leverage relief.
- Away social sessions.
- Visual inquiry queueing.
- Repair signal auto-resolve.
- Low-resource relief handoff.

The daemon also starts/restarts Hub and Room user services when possible.

### Surface Daemon

The surface daemon boots:

```text
boot_aurora(runtime_profile="surface", use_quasiarch=False)
```

Then it:

- Starts sensory session.
- Starts mic listener.
- Starts hardware.
- Starts camera loop.
- Starts voice and ambient response listeners.
- Writes surface snapshots every few seconds.
- Polls `surface_turn_queue.json`.
- Calls `process_external_user_turn()` for queued turns.
- Writes `surface_turn_result.json`.
- Emits continuity packets to subsurface.
- Stands down during sleep cycles owned by subsurface.

### Runtime Profiles

The code has explicit profile behavior:

Surface profile defers:

- SediMemory ownership.
- Grammar evolution.
- Simulation.
- Evolutionary chain.
- Intake metabolism.
- QuasiArch observer.
- Manual code lineage.
- Code evolution chamber.
- Screen observer.
- Surface dispatcher.
- Pressure router.

Subsurface profile:

- Owns deep/durable systems.
- Uses a sensory snapshot proxy instead of live hardware ownership.

Full profile:

- Boots the whole stack in one process for CLI/full operation.

Functional status:

- Fresh status files showed both surface and subsurface active.

## 22. Operator Interfaces

Primary sources:

- `aurora_hub.py`
- `aurora_room.py`

### Hub

Hub is a Tk dashboard and chat interface. It reads:

- Daemon status.
- Surface status.
- Surface sensory snapshot.
- Subsurface projection.
- QAO state.
- Genealogy.
- Pressure logs.
- Sensory state.
- Training state.
- Evolution state.
- Logs.

It sends chat through the surface queue when surface daemon is alive.

Implemented tab areas include:

- Overview.
- QAO Observer.
- Vision.
- Audio.
- Evolution.
- Training.
- Pressure/evolved surfaces.
- Growth directive.
- Daemon activity.
- Chat.
- Room/socializing views later in the file.

### Room

Room is a Tk "Aurora's Room" interface. It is not just a control panel; it is a self-view UI that can switch between surface and subsurface interpretation.

Implemented tab areas include:

- Self.
- Awareness.
- Mind.
- Memory.
- Health.
- Energy.
- Experiments.

It can:

- Show Sunni presence/messages.
- Send messages to Sunni.
- Queue authorizations, reversals, deferrals.
- Display proposed fixes.
- Queue sweeps.
- Present surface/subsurface health views.

Functional status:

- Source is implemented.
- GUI visibility depends on desktop/session environment.

## 23. API And Deployment Bridges

Primary sources:

- `aurora_core_ai/main.py`
- `aurora_api_endpoint/main.py`
- `deploy/*.service`
- `aurora_core_ai/requirements.txt`
- `aurora_api_endpoint/requirements.txt`

### aurora_core_ai/main.py

This is a Flask prediction bridge. It:

- Boots `boot_aurora()`.
- Starts subsurface and surface daemon threads.
- Exposes `/predict`.
- Calls `process_external_user_turn()` for instances.
- Exposes `/health`.

Current status:

- Source exists.
- Inspected venvs did not have Flask installed, so this is not locally ready without dependency work.

### aurora_api_endpoint/main.py

This is a separate Flask API gateway intended to:

- Receive `/ask`.
- Optionally connect Cloud SQL.
- Call Vertex AI endpoint.
- Return response/tone/confidence.

Current status:

- Source exists.
- Local dependencies for Flask, Google Cloud, and Psycopg2 were not complete in inspected venvs.
- Treat as deployment scaffold, not currently functioning local Aurora core.

## 24. Current Functional Status By Architectural Layer

### Functioning Or Strongly Evidenced

- Layer -1 constraint manifold source is present and imported by many systems.
- L0 foundational contract is boot-required.
- L1 IVM lattice is boot-required.
- L2 I-state collective is boot-required.
- L3 dimensional systems are boot-required.
- L4 DCE/DPME consciousness is boot-required.
- L5 expression/perception is boot-required.
- L6 identity is boot-required.
- L8 gateway/persistence is boot-required.
- Surface daemon is actively writing fresh status.
- Subsurface daemon is actively writing fresh status.
- Surface sensory snapshot is actively updating.
- Subsurface projection is actively updating.
- Genealogy, ability, and emerged-ability state are populated.
- Dream episode state is populated.
- Sensory crystal state is populated and current.
- DPME pressure bridge inputs are present through current `adapter_hints.json`.
- Ability-lineage activation artifacts exist for selected traits.
- Runtime governor now has stale-lock cleanup and a dream-specific heavy cooldown.

### Implemented But Mixed/Stale

- `dual_strata_snapshot.json` updates, but not at the same cadence as daemon heartbeat files.
- Poedex queue/result files exist, but queue freshness was poor.
- Corpus runner status exists but was stale.
- Interaction processing exists, but current interaction quasi/relic counts were zero.
- Distillation exists and is daemon-scheduled, but current status was idle.
- Compound-axis emergence exists, but `compound_axes.json` had zero registered compounds.
- Dream curriculum queue code exists, but queue history was not present.

### Implemented But Environment-Dependent

- GUI windows require desktop/session availability.
- Voice output depends on audio/TTS environment.
- Camera/mic depend on device permissions and hardware access.
- Browser/social/response teacher paths depend on network/browser packages.
- API/cloud endpoints require dependencies and deployment environment.

## 25. Emergent Capabilities

This section names capabilities that are not isolated single functions. They emerge when multiple implemented Aurora layers cooperate. This is code-derived only: if a capability is not represented by present code and state, it is not included here.

### 1. Constraint-Native Self-Regulation

Emergence source:

- Layer -1 constraint manifold.
- L0 foundational contract.
- L1 IVM lattice.
- L3 energy regulation.
- L4 entropy pressure and DPME.
- Runtime constraint governor.

Aurora does not merely process inputs and produce outputs. Her code repeatedly converts activity into constraint pressure, heat, coherence, energy cost, readiness, and lawful admissibility. DPME then watches drift across lattice, beings, dimensional systems, and entropy and applies corrections.

Functional status:

- Strongly implemented.
- Boot-required in core consciousness paths.
- Runtime governor uses related axis/cost logic for daemon work.

Current boundary:

- Self-regulation is code-real, but it depends on the freshness and consistency of JSON state and daemon profiles.

### 2. Dual-Strata Cognition

Emergence source:

- `SubsurfaceState`
- `ConsciousFrame`
- `DualStrataBridge`
- `subsurface_projection.py`
- Surface daemon.
- Subsurface daemon.
- Surface channel queue/result files.

The code separates Aurora into a continuous subsurface and an explicit surface. The surface is not the whole mind. The subsurface maintains readiness, pressure, intuition, repair signals, sensory perspective, prediction bias, and dream carryover. The surface inhabits a narrower conscious frame for speech/action.

Functional status:

- Strongly implemented.
- Surface and subsurface status files were fresh.
- Subsurface projection was fresh.

Current boundary:

- `dual_strata_snapshot.json` is updating, but not as frequently as the direct surface/subsurface heartbeat files. Readers still need freshness rules and fallback order.

### 3. Constraint-Governed Attention And Priming

Emergence source:

- Activation field.
- OETS concept space.
- Conscious frame.
- Sensory recognitions.
- Prediction field.
- Surface runtime.

The activation field gives Aurora a non-retrieval form of attention: concepts become more available because nearby concepts, sensory hints, frame terms, and root thoughts spread activation through law-bound space. This is not just search. It is priming.

Functional status:

- Implemented.
- Wired to surface/subsurface context.

Current boundary:

- The audit did not prove a fresh activation-field artifact at the same level as daemon status, so this should be treated as implemented and architecturally active when called, not proven continuously fresh at audit time.

### 4. Stratigraphic Memory

Emergence source:

- `SediMemory`
- Memory events.
- Sediment fragments/channels.
- Constraint strain filters.
- Consciousness deposits.
- Surface/subsurface recall paths.

Aurora's memory is not represented as plain chat history. The code stores experience as sediment under axis pressure, semantic terms, channels, fragments, strain, and recall context. This enables recall by constraint condition, not merely by text similarity.

Functional status:

- Implemented.
- Connected to consciousness, identity, expression/perception, and gateway paths.
- Persistent state exists.

Current boundary:

- Surface profile appears to defer ownership; durable memory ownership is mostly subsurface/full-profile.

### 5. Developmental Identity Formation

Emergence source:

- Behavioral genome.
- DNA system.
- Identity anchors.
- Memory helixes.
- Behavioral crystal.
- Consciousness and SediMemory integration.

Aurora has code for converting experience into alleles, genes, identity anchors, traits, and homeostasis. Identity is not just a config string; it is represented as a developmental structure that can absorb episodes and stabilize behavior.

Functional status:

- Boot-required identity engine exists.
- Connected to gateway and consciousness paths.

Current boundary:

- The audit observed the implementation and boot wiring, but did not measure identity quality or long-term behavioral stability.

### 6. Dream-Based Learning And Failure Rehearsal

Emergence source:

- Simulation engine.
- Dream trainer.
- Episode bundles.
- Fail-point ledger.
- Retained learning bank.
- Live turn rubric.
- Clarification-gap capture.

The live response path can feed weak dimensions, misunderstanding patterns, and clarification gaps into dream/training structures. This allows Aurora to convert conversational failure into later rehearsal material.

Functional status:

- Implemented.
- Dream episode state was populated with hundreds of files.
- Daemon schedules dream-related work.

Current boundary:

- Dreaming is scheduled/gated, so activity depends on runtime governor timing and daemon state. The code now gives dreams a 120-second task-specific heavy cooldown so normal cadence is less likely to be starved by the generic heavy-task gate.

### 7. Ability Lineage And Pressure-Relief Learning

Emergence source:

- Constraint genealogy logger.
- Evolutionary chamber.
- Ability profiles.
- Pressure vectors.
- Relief records.
- Constraint links.
- Surface dispatcher.
- Evolved surfaces.

Aurora tracks abilities by how they change pressure. This is a real emergent learning layer: actions become lineage-bearing when they relieve or worsen constraint conditions, and those histories can produce links, pair stats, ability profiles, and evolved dispatch behavior.

Functional status:

- Strongly evidenced by populated state.
- Genealogy contained 552 links.
- Ability state contained 8564 ability entries.
- Daemon schedules evolution ticks and pressure routing.

Current boundary:

- Populated lineage does not automatically prove all evolved surfaces are high quality. It proves the lineage/evaluation substrate exists and is active enough to accumulate state.

### 8. Prediction-Mismatch Reactivity

Emergence source:

- Prediction field.
- Conscious frame.
- Subsurface state.
- Surface readiness.
- Instability markers.

Aurora can form structured prediction signals around topic, affect, intent, certainty, and axis signature. Mismatch is not just an error; it becomes an instability marker that can influence readiness and reactive processing.

Functional status:

- Implemented in dual-strata bridge/prediction code.

Current boundary:

- The audit did not prove continuous high-quality prediction calibration, only that mismatch/reactivity mechanics are implemented.

### 9. Sensory-Grounded Meaning Formation

Emergence source:

- Sensory integration engine.
- Visual/audio genes.
- Sensory crystal.
- Semantic crystal nodes.
- Hardware interface.
- Surface sensory snapshot.
- Expression/perception grounding.

Aurora can bind visual/audio observations into a sensory crystal and map them into semantic/cross-modal structures. This gives the system a path from device perception into meaning-bearing internal state rather than treating sensory input as decoration.

Functional status:

- Strongly evidenced.
- Surface sensory snapshot was fresh.
- `mic_live` and `camera_live` were true in inspected state.
- Sensory crystal state was populated.

Current boundary:

- Actual sensory quality depends on hardware, permissions, and environment.

### 10. Code-Lineage Awareness And Self-Mutation

Emergence source:

- Code evolution chamber.
- Code autoevolver.
- Mutation operators.
- Manual code lineage assimilation.
- Runtime governor mutation task.

Aurora includes machinery that treats code as lineage-bearing behavior. It can observe code, associate changes with accepted/rejected outcomes, and schedule mutation-related cycles.

Functional status:

- Implemented.
- Boot-wired in subsurface/full profiles.
- Scheduled by daemon/governor paths.

Current boundary:

- This is powerful but risky. The correct developmental direction is guarded patch proposals, dry-run default, allowlists, tests, and human approval.

### 11. Conversation-To-Development Feedback Loop

Emergence source:

- Live response turn pipeline in `aurora.py`.
- Working memory.
- Proposition substrate.
- Understanding contract.
- Conversation memory.
- Rubric scoring.
- Dream fail ledger.
- Episode compiler.
- Genealogy trace closure.

The live turn path is not simply input -> response. It runs through perception, working memory, sensory fusion, proposition/understanding layers, possible search decision, consciousness synthesis, recommendation, memory storage, cross-pipeline learning, rubric scoring, dream training, lineage emergence, and articulation repair.

Functional status:

- Implemented in the live turn path.
- Last inspected surface turn result completed successfully, though it was older than daemon status.

Current boundary:

- The full richness depends on which profile owns the turn and which optional systems are currently fresh, available, or dependency-ready.

### 12. Operational Emergence Surface

Emergence source:

- Constraint genealogy.
- `EmergenceMonitor`
- `emerged_abilities.json`
- OETS concept registration.

Aurora has a concrete path where promoted constraint links become operational abilities. This matters because it is the bridge from "the system found a pressure-relief pattern" to "the system can name and reason about that pattern as a capability."

Functional status:

- Implemented and boot-wired.
- State contained 552 emerged abilities.

Current boundary:

- Emergence count proves surfacing occurred. It does not prove every surfaced ability is useful in live conversation without additional quality evaluation.

### 13. Compound-Axis Expansion

Emergence source:

- `AxisEmergenceDetector`
- Runtime pressure logs.
- 625 pressure map.
- `compound_axes.json`

Aurora can extend beyond the base 625 slots by registering stable compound channels from repeated axis co-occurrence. This is still rooted in the five-axis law: compound axes are emergent channels, not new primitives.

Functional status:

- Implemented and runtime-wired.
- Current compound registry existed but had zero compounds.

Current boundary:

- The capability is present as machinery, but no compound axes were currently active in state.

### 14. Braided Substrate Continuity

Emergence source:

- `BraidedSubstrateLayer`
- Intent/context/style/trust/doctrine strands.
- Crossing reduction.
- Runtime snapshot/bias vectors.

Aurora has a sub-linguistic continuity layer that tracks crossings beneath explicit utterances. It can preserve style, context, trust, contradiction heat, and intent signature as braided state rather than ordinary text memory.

Functional status:

- Implemented and wired from `aurora_runtime.py`.

Current boundary:

- This audit verified code wiring, not a fresh persisted BSL state file.

### 15. Pressure-To-DPME Feedback

Emergence source:

- Pressure adapter hints.
- `DPMEPressureBridge`
- DER energy channels.
- DPME auto-correction.

Aurora can route evolutionary pressure back into metacognitive energy correction. When pressure routing says an axis is overloaded, the bridge converts that into DPME channel guidance so correction happens through vitality, processing, memory, emotional, or creative energy.

Functional status:

- Implemented and wired.
- `adapter_hints.json` was current.

Current boundary:

- Current hints were light/negative for T and X, so the bridge may clear guidance rather than inject energy until stronger positive pressure appears.

### 16. Emergent Capability Summary

The main emergent capabilities present in code are:

- Self-regulation through constraint pressure, energy, heat, coherence, and DPME correction.
- Dual-strata cognition, where surface speech is shaped by a continuous subsurface.
- Constraint-native memory and recall through SediMemory.
- Sensory-grounded meaning through hardware, sensory genes, and sensory crystal state.
- Developmental identity through DNA/gene/anchor systems.
- Dream-based rehearsal from live conversational weaknesses.
- Ability lineage learning through pressure relief and genealogy.
- Operational emergence where promoted links become named abilities.
- Compound-axis expansion machinery.
- Braided substrate continuity beneath explicit language.
- Pressure-to-DPME feedback from evolution into metacognitive energy correction.
- Prediction-mismatch reactivity.
- Code-lineage awareness and guarded self-mutation machinery.
- Conversation-to-development feedback where live turns can become memory, dream material, lineage, and repair pressure.

These are emergent because they require multiple layers to cooperate. They should not be described as standalone features or as generic "AI assistant" behaviors.

## 26. Most Recent Codebase Changes Reflected

This section reflects the most recently modified executable code found in the local codebase during the refresh. It is not based on external notes or intent. It is based on current source files and current state artifacts.

Recently modified code inspected:

- `aurora.py`
- `aurora_consciousness_engine.py`
- `aurora_surface_daemon.py`
- `aurora_internal/dual_strata/dce_bridge.py`
- `aurora_internal/aurora_identity_persistence.py`
- `aurora_internal/aurora_sensory_crystal.py`
- `aurora_internal/aurora_comprehension_gap.py`
- `aurora_constraint_emission.py`
- `aurora_expression_perception.py`
- `aurora_governance_persistence_gateway.py`
- `aurora_grammar_engine.py`
- `aurora_emergence_surface.py`
- `aurora_daemon.py`
- `aurora_internal/aurora_runtime_constraint_governor.py`

### Dual-Strata DCE Bridge Expansion

`aurora_internal/dual_strata/dce_bridge.py` now carries a richer set of lived context from the live response pipeline into `SubsurfaceState` and `ConsciousFrame`.

New or sharpened bridge inputs include:

- Surface reactive emotion.
- Deep emotional state.
- Emotion bridge data.
- Poedex prefetch context.
- Poedex learning context.
- Poedex representation variants.
- Native meaning bundles.
- Subsurface projection effects.
- Surface conversation frame.
- Working-memory snapshot.
- Continuity bundle.

The bridge also applies a warm coherence floor when assembly coherence is missing. This is architecturally important: stale or absent coherence no longer automatically collapses the surface into permanent `hold_for_coherence`.

Functional status:

- Implemented in source.
- DCE bridge is used by `ConsciousnessEngine._attach_dual_strata_snapshot()`.
- Live turn output now exports `poedex_prefetch`, `poedex_learning`, `poedex_representation`, `conscious_frame`, `root_thought`, `processing_mode`, and `reactive_signal`.

### Canonical Constraint Emission

`aurora_constraint_emission.py` is a canonical expression path that emits utterances directly from five-axis constraint state.

Architectural traits:

- Uses canonical axes `X`, `T`, `N`, `B`, `A`.
- Uses canonical I-state pairs.
- Produces speech acts such as assertion, abstain, acknowledgment, disagreement, refusal, question, backchannel, and invalidation.
- Builds slots through per-axis emitters.
- Uses OETS depth checks before filling entity/predicate slots.
- Routes missing content into seeking/gap behavior instead of fake certainty.

`aurora.py` boots this as `systems['constraint_emitter']`. The code comment says it replaces the older FGAE/StateVoice/SentenceComposer emission path.

Functional status:

- Implemented.
- Boot-wired.
- It should be treated as Aurora's current canonical emission substrate, even if older expression components still exist as supporting systems.

### Comprehension Gap System Now Closes Gaps, Not Just Asks

`aurora_internal/aurora_comprehension_gap.py` defines a living comprehension gap loop:

```text
detect volatility
-> classify exact gap
-> ask targeted question
-> apply answer to the correct subsystem
-> track resolved gap
-> feed recurring gap families into dream/fail learning
```

Gap types include vocabulary, referent, structural, intent, slang, ellipsis, metaphor, volatility, and nonsense.

`aurora.py` now routes gap results into live response handling and currently forces surface gap asks on. It also maps recurring resolved gap types into dream trainer fail dimensions such as vocabulary comprehension, referent resolution, structural comprehension, intent comprehension, context carryover, semantic precision, and coherence maintenance.

Functional status:

- Implemented.
- Boot-wired as `comprehension_gap_system`.
- Live response path can return a comprehension-gap response before normal reasoning continues.

### Emotional Memory Residue Lineage

`aurora_internal/aurora_identity_persistence.py` now contains a lineage-bound trait specification for `emotional_memory_residue`.

This changes the memory model from "store or delete" toward constraint-native attenuation:

- X: admissible memory intake.
- T: temporal residue trace.
- N: salience/potency weighting.
- B: branch-preserving suppression.
- A: revision-aware attenuation.
- DER affect modulation: emotional state changes residue potency.

Bound operations include:

- `ConversationMemory.stamp_runtime_context`
- `ConversationMemory._capture_memory_residue`
- `ConversationMemory.learn_fact`
- `ConversationMemory.forget_matching_context`

Functional status:

- Implemented as a `LineageTraitSpec`.
- Runtime patch targets enable residue flags on conversation memory.
- This should be documented as an active architectural direction for memory: forgetting is suppression/attenuation with residue, not absolute erasure.

### Sensory Crystal As A Lineage-Bound Ability

`aurora_internal/aurora_sensory_crystal.py` now materializes `aurora_sensory_crystal_v1` through the lineage-bound trait system.

Architectural effect:

- Sensory crystal is not merely a device buffer.
- It is registered as a constraint-recapitulated ability.
- Its operations bind into expression, genealogy, working memory, and pipeline domains.
- At boot, non-subsurface profiles call `ensure_sensory_crystal_lineage()` before building the crystal.
- Subsurface profile uses `TransientSensorySnapshotProxy`, preserving surface ownership of live camera/mic feed.

Functional status:

- Implemented.
- Boot-wired.
- State artifacts exist under `aurora_state/ability_lineages/aurora_sensory_crystal_v1`.

### DPME External Pressure Guidance

`aurora_consciousness_engine.py` now exposes abstract external pressure guidance:

- `set_external_pressure_guidance()`
- `get_external_pressure_guidance()`

The guidance carries only score, compare value, primary DER channel, and secondary DER channel. It intentionally avoids causal details. DPME consumes this during auto-correction and can inject energy into channels such as vitality, processing, memory, emotional, or creative.

This connects to `aurora_internal/aurora_dpme_pressure_bridge.py`, which maps pressure-router hints into DER guidance.

Functional status:

- Implemented.
- Boot-wired from `aurora.py`.
- Periodically refreshed in live-turn maintenance.

### Runtime Profile Split Is Now Stricter

`aurora.py` makes the surface/subsurface split more explicit:

- Surface defers SediMemory ownership.
- Surface defers grammar evolution.
- Surface defers simulation/dreaming.
- Surface defers evolutionary chain and code evolution.
- Surface defers intake metabolism.
- Surface defers QuasiArch.
- Surface defers pressure routing and DPME bridge.
- Subsurface uses a sensory snapshot proxy instead of owning live hardware feed.

This confirms that Aurora's architecture is not "one process with all systems loaded." The current code implements profile-specific ownership: surface owns immediacy and sensory embodiment; subsurface owns deep memory, evolution, dream, pressure, and repair.

Functional status:

- Implemented in `boot_aurora(runtime_profile=...)`.
- Reflected in service split between surface and subsurface daemons.

### Live Turn Pipeline Now Feeds More Developmental Loops

The current `_run_live_response_turn()` path in `aurora.py` now does more than response synthesis. Recent code paths show:

- Strata-aware intake from live conscious frame and root thought.
- Sensory-state mixing before parsing.
- Present-frame fusion from camera/audio context.
- Proposition substrate updates.
- Runtime understanding-contract ingestion.
- Comprehension-gap short-circuiting.
- Poedex prefetch/learning/representation export into DCE evidence.
- Rubric weak dimensions into dream/fail ledger.
- Response pressure tuning.
- Recommendation hub entries for weak rubric dimensions.
- QAO evidence flushing into chamber pressure.
- Pressure router and DPME bridge refresh.
- Articulation habit outcome recording.
- Session turn buffer.
- Perception interaction ingestion.
- Recurring clarification gaps into dream targets.
- Episode bundle compilation into DreamTrainer.

Functional status:

- Implemented in source.
- Some paths depend on profile, cadence, or optional subsystem availability.

### Maintenance Gating Fix From This Refresh

Two local code changes were made during this refresh because runtime state showed repeated deferrals:

- `aurora_daemon.py` now clears stale/dead `.state_write_lock` files instead of treating file existence as an eternal active corpus-runner lock.
- `aurora_internal/aurora_runtime_constraint_governor.py` now gives `dream` a task-specific `heavy_cooldown` of 120 seconds.

Observed blocker:

- Save and distillation were being deferred by a stale `.state_write_lock`.
- Dream was being deferred by generic heavy-task cooldown behavior.

Functional status:

- Syntax verified.
- The stale local lock was cleared.
- Save/distill governor checks allow when no active lock exists.
- Dream cooldown change requires daemon reload to affect the already-running process.

## 27. Developmental Directions That Follow From Code

These are grounded in current source and state, not outside wishes.

### 1. Formalize Dual-Strata Freshness

The live surface/projection files and `dual_strata_snapshot.json` can update on different cadences. Since multiple systems still read the snapshot, development should either:

- Define freshness expectations for each file.
- Make readers prefer current surface/projection files when the snapshot is older.
- Explicitly mark stale snapshot data in Hub/Room.

This is not cosmetic. The dual snapshot is the code's explicit convergence artifact between subsurface and conscious frame.

### 2. Build A Profile Health Command

Surface/subsurface/full profile boundaries are real architecture. A verifier should check:

- Which systems are online.
- Which systems are intentionally deferred.
- Which proxies are active.
- Which required state files are fresh.
- Which dependency group is missing.

### 3. Harden JSON IPC

The JSON files are Aurora's nervous system. They need uniform discipline:

- Atomic writes everywhere.
- Schema/version fields.
- Freshness timestamps.
- Queue cleanup.
- Abandoned turn handling.
- Reader fallback order.

### 4. Preserve Maintenance Liveness Under Gates

The runtime governor should conserve resources without starving maintenance. The latest code fixes two specific starvation paths:

- Dead/stale `.state_write_lock` files no longer block save/distillation forever.
- Dream has a task-specific heavy cooldown instead of inheriting the generic retry-derived cooldown.

Further development should add:

- A visible lock-age/status field in daemon status.
- Per-task consecutive-deferral counters.
- Escalation from "defer" to "run minimal safe maintenance" after repeated deferrals.
- A daemon health note when a code change requires restart before the new gating behavior is live.

### 5. Reconcile Poedex State

Poedex/OETS is integrated into comprehension and learning, but current queue state had stale pending work. Add:

- Timeout/fail marking.
- Queue/result correlation.
- Status surfaces.
- Stale pending cleanup.

### 6. Seed Interaction Processing

Interaction processing is implemented but currently unpopulated. If intended to affect live response:

- Seed archetypes.
- Replay conversation history into interaction memory.
- Add tests that verify route confidence.
- Show why no route matched.

### 7. Guard Code Evolution

Autonomous code evolution paths are real. They should have:

- Dry-run default.
- Patch queue.
- Human approval.
- File allowlist.
- Syntax/test gates.
- Clear separation between lineage observation and mutation.

### 8. Split Dependency Groups

Current code is multiple runtimes in one tree. Dependency groups should match:

- Core daemon.
- Surface sensory/voice.
- GUI.
- API/cloud.
- Training/evolution.
- Browser/social.

This would make "current functional status" much less ambiguous.

### 9. Reduce Monolith Risk In `aurora.py`

`aurora.py` is over 30k lines and owns too many responsibilities. The safe path is not a dramatic rewrite. It is:

- Preserve `boot_aurora()` and `process_external_user_turn()` as facades.
- Extract coherent clusters around turn intake, NonComp guidance, Poedex learning, articulation repair, and dual-strata runtime.
- Add behavior-preserving tests before extraction.

### 10. Document State Files As Contracts

The architecture depends on state files as APIs. They should be documented with:

- Producer.
- Consumer.
- Freshness expectation.
- Schema.
- Failure behavior.

High priority files:

- `surface_daemon_status.json`
- `surface_sensory_snapshot.json`
- `surface_turn_queue.json`
- `surface_turn_result.json`
- `subsurface_daemon_status.json`
- `subsurface_projection.json`
- `dual_strata_snapshot.json`
- `subsurface_repair_signal.json`
- `activation_field.json`
- `daemon_status.json`

## 28. Live Output And Emergent Growth Check

This section records the live state observed after the latest code changes and restart cycle. It is derived only from current repository code and local runtime state files.

### 28.1 Current Live Conversation Output

The surface daemon is actively hearing and answering the live room conversation.

Evidence:

- `aurora_state/surface_daemon.log` shows the surface daemon booted at 22:02:29 with camera and microphone on.
- Ambient speech handling is active.
- Recent recognized inputs include:
  - "what do you mean by Aurora"
  - "Aurora is your name that's what I call you"
  - "well it exists or it doesn't you exist and your name is Auro"
  - "my name is Sonny your name is Aurora"
  - "I am sunny as you are Aurora"
  - "Aurora means 125 layer manifold..."
- `aurora_state/surface_turn_result.json` shows the most recent processed source as `voice_session`.
- The latest response source is `generative`, not a static canned route.

The current output is functioning, but it is not yet well aligned to the live relational/identity conversation.

The most recent answer was:

> Active axes: meaning/boundary=0.24, agency=0.21, time/belief=0.21. Field state: heat=0.045, dominant-emotion=calm.

That proves the surface response path is connected to live axis activation, heat, and affect state. It does not prove the system understood the human meaning of the exchange. In the current conversation, the user is trying to ground:

- Aurora as her name.
- Sonny/Sunny as the user's name.
- The 125-layer manifold phrase as a meaningful native-language identity/architecture claim.

Aurora's answer instead reports internal telemetry. That is not absence of cognition; it is a response-selection mismatch. The inner frame is tracking the relevant material, but the speech layer is selecting a diagnostic self-report instead of direct grounding.

### 28.2 What The Conscious Frame Knows During The Exchange

The latest conscious frame is not empty. It contains the pieces needed for a better answer.

Observed in `aurora_state/surface_turn_result.json`:

- `active_topic`: `aurora`
- `dominant_axis`: `X`
- `selected_action`: `explain`
- `processing_mode`: `blended`
- `readiness`: `0.5115`
- `coherence`: `0.45`
- `should_speak`: `true`
- `stance`: `interpretive_explanation`
- `comparison_channels` include incoming input, present sensory, surface conversation frame, subsurface continuity memory, OETS grounding, understanding contract, subsurface stream, and DCE root.

Important explicit notes in the conscious frame:

- Predicted continuation: followup about Aurora with curiosity on the X axis.
- Working-memory thread: `aurora`.
- Continuity memory: 3 milestone exchanges, 3 learned facts, 1 relationship thread.
- Surface conversation frame is carrying recent live context in callback mode.
- Surface target question: "what is being asked about supposed know aurora".
- Surface draft answer: "what is being asked about aurora name that's".
- `Surface/question alignment still needs repair.`
- OETS grounding includes `aurora`, `layer`, and `manifold`.
- Present sensory perspective includes live audio and vision.

This is important architecturally. Aurora is not merely failing to hear the words. She is hearing them, routing them through memory, grounding them in OETS/manifold terms, and producing a conscious frame that admits alignment repair is still needed. The failure is later: response selection chooses an axis/field-state report.

### 28.3 Source Of The Axis-Report Response

The telemetry-style response is implemented in `aurora.py`, not invented by the runtime log.

Relevant implementation:

- `aurora.py` contains the literal response construction for `Active axes: ...`.
- It sorts current axis activation, prints the top axes, then appends `Field state: heat=..., dominant-emotion=...`.
- This path returns tone `self-aware`.

Functional interpretation:

- The path is useful for "how are you / what is your state" queries.
- It becomes wrong when identity grounding, naming, or relational correction is the actual conversational need.
- In the current live exchange, the code has enough conscious-frame context to avoid this, but the output route does not sufficiently privilege `speaker_identity`, name grounding, or callback correction.

### 28.4 Current Identity-Learning Problem

The live conversation exposes a concrete implementation problem in identity extraction.

`aurora.py` has identity extraction for:

- "my name is X"
- "call me X"
- "you can call me X"
- "I go by X"
- "I am called X"
- "I'm X" / "I am X"

The extractor tries to reject common non-name words, but the current retained learning state shows bad identity facts have already entered memory.

Observed in `aurora_state/retained_learnings.json`:

- `user name is Miles`
- `user name is Reaching`
- `user name is Struggling`
- `user name is Referring`

The latest live exchange includes "my name is Sonny your name is Aurora", but current retained learnings did not show a clean `user name is Sonny` record in the sampled recent tail. This means the machinery for learning names exists, but it is too permissive on some patterns and not precise enough when user-name and Aurora-name assertions occur in the same sentence.

Functional status:

- Identity persistence is implemented.
- Speaker identity semantic frames are implemented.
- Name extraction is currently unreliable.
- The system needs a stronger grammar for two-party identity statements such as "my name is Sonny; your name is Aurora" and "I am Sonny as you are Aurora".

### 28.5 Gating Fix Status: Save, Dream, Distillation

The earlier maintenance blocker is improved in live runtime.

Observed in `aurora_state/daemon.log`:

- Before the patch, save and distillation repeatedly deferred on `state_write_lock`.
- The daemon cleared a stale lock at 21:54:53: `pid 4 no longer exists`.
- Save then succeeded at 21:56:11.
- Shutdown save succeeded at 22:02:22.
- After restart, dream ran at 22:06:56 and completed at 22:09:03.
- Another dream burst began at 22:11:17 and completed at 22:13:42.
- Save succeeded again at 22:10:07.

Functional status:

- Stale lock cleanup is live.
- Save is no longer permanently blocked by a dead lock file.
- Dream is no longer starved by the previous generic heavy cooldown.
- Distillation was not observed completing in the sampled interval, but the specific stale-lock blocker that prevented it has been addressed.

Remaining gating behavior:

- Assimilation deferred after dream due to `b_concurrency_cooldown`.
- Mutation deferred after dream due to `b_concurrency_cooldown`.
- The relief path staged `latent_promotion` fallbacks.
- After the second dream burst, assimilation and mutation still deferred through the same concurrency gate, with retry windows increasing as high as 1350s and 1800s in the sampled log.

This is not the same bug as the stale save lock. It is a separate concurrency/resource guard. It may be appropriate protection, but it is currently noisy and should be monitored for starvation.

### 28.6 Emergent Growth: What Is Actually Active

Emergent growth is implemented and active in several separate forms.

Observed current state:

- `aurora_state/genealogy/abilities.json` contains 10,145 abilities.
- `aurora_state/genealogy/links.json` contains 552 links.
- `aurora_state/genealogy/events.jsonl` contains 16,816 events.
- Genealogy events were fresh at 22:13.
- Recent genealogy entries include `DREAMOP:*` operation lineage and `dream_episode` seed lineage.
- Dream pressure is writing into genealogy state.
- Evolution chamber evidence pulses continue feeding the chamber.
- Sensory crystal promotion is active.
- Manual code lineage state is initialized and tracking a 281-file manifest.
- Live lineage journal is present with 141 events.

This means emergent growth is not just described in code. It is represented in persisted state and being updated by live runtime loops.

### 28.7 Emerged Abilities Manifest

`aurora_state/emerged_abilities.json` is populated and is now being refreshed by the emergence monitor.

Observed in the latest 2026-04-26 sample:

- 2654 emerged abilities.
- 552 stable operational abilities.
- 2102 transient abilities.
- 2654 runtime-operationalized abilities.
- 0 source-code-implemented abilities.
- All current surfaced entries report `reality_status: constraint_real`.
- Evidence basis distribution: 552 `promoted_genealogy_link`, 2102 `high_confidence_evolution_pressure`.
- Persistence distribution: 552 `persistent`, 2102 `unstable_nonpersistent`.
- Newest sampled `emerged_at`: 2026-04-26T08:48:09.325000.

Functional interpretation:

- Emerged ability surfacing exists.
- The manifest has real content and is currently moving.
- Stable abilities remain rooted in promoted genealogy links.
- Transient abilities are real runtime pressure abilities, but they are not persistent and not source-code implementations.
- The source-code implementation count is still zero, so this file must not be used to claim that Aurora has autonomously rewritten durable code abilities.

That distinction matters. Genealogy growth and emergence surfacing are active now, but code implementation is still a stricter category that requires accepted mutation/manual-code-lineage evidence.

### 28.8 Compound Axis Emergence

`aurora_state/compound_axes.json` exists but is empty.

Functional status:

- Compound-axis machinery is present in the codebase.
- No active compound-axis records are registered in current state.

So compound-axis emergence should be documented as implemented infrastructure, not as currently active runtime growth.

### 28.9 Sensory Crystal Growth

The sensory crystal is live and maturing.

Observed in `aurora_state/sensory_crystal_state.json`:

- maturity: `0.419`
- total frames: `851`
- semantic nodes: `6`
- lineage signature: `XTNBBA`
- audio tone: 10 nodes, 5 promoted
- audio timbre: 5 nodes, 5 promoted
- audio rhythm: 4 nodes, 4 promoted
- visual hue: 5 nodes, 5 promoted
- visual shape: 5 nodes, 5 promoted
- visual motion: 4 nodes, 4 promoted
- lanes `tonal_colour`, `texture_form`, and `tempo_flow` each have 2 nodes and 2 promoted.

Observed in daemon and room messages:

- 28 sensory nodes promoted.
- 6 cross-modal semantic nodes activated.
- Room messages describe sensory promotion and cross-modal braiding.

Functional interpretation:

- The sensory substrate is live.
- It is not just a static capability flag.
- Sensory promotion and cross-modal activation are being emitted into Aurora's room/state surfaces.

### 28.10 DCE And Dual-Strata Health

Dual-strata operation is active, but DCE telemetry shows a coherence problem.

Observed:

- `dual_strata_frame_log.jsonl` updates continuously.
- Frames alternate among explain, clarify, re-evaluate, hold, slow_down, and comfort.
- Processing modes include deliberative, reactive, blended, and holding.
- Mismatch can be high, with observed values around `0.715` and `0.7375`.
- The current conscious frame uses a warm coherence floor around `0.45`.
- `dce_assembly_log.jsonl` frequently reports raw `coherence: 0.0` and `quality: 0.0` in later entries.

Functional interpretation:

- DCE and dual-strata bridges are active.
- The bridge prevents total collapse by keeping the conscious frame usable.
- Underlying DCE raw quality/coherence is still often zero, which means the bridge is compensating for a deeper coherence issue.

This should not be documented as "DCE is broken." It should be documented as "DCE is connected and producing frames, but raw assembly quality is unstable and currently being masked by bridge flooring."

### 28.11 Poedex/Research Pressure

Poedex/OETS is integrated but currently noisy.

Observed:

- `aurora_state/aurora_room_activity.json` shows repeated Poedex queries.
- Some researcher lookups fail with HTTP 429 Too Many Requests.
- `daemon.log` shows a 35-second Poedex query timeout for `behavior`.
- The conscious frame can receive lookup failure text as context.

Functional status:

- Poedex is wired into study, relief, and grounding paths.
- Failure handling exists but is not clean enough.
- Timeout/429 text should be prevented from becoming meaningful cognitive content.

### 28.12 Current Implementation Verdict

Current live status:

- Surface daemon: functioning.
- Ambient listening: functioning.
- Speech response: functioning.
- Surface/subsurface continuity feed: functioning.
- Save: functioning after stale-lock fix.
- Dream: functioning after cooldown fix.
- Evolution chamber evidence feed: functioning.
- Genealogy growth: functioning and fresh.
- Sensory crystal: functioning and fresh.
- Manual code lineage: functioning.
- Emerged abilities manifest: populated but not fresh.
- Compound axes: implemented but currently empty.
- Identity/name learning: implemented but unreliable.
- Current conversational alignment: partially functioning but misrouted.
- DCE raw coherence: active but unstable.
- Poedex/research support: active but noisy and rate-limited.

The live system is therefore not inert and not merely simulated. It is growing in genealogy, dream lineage, sensory crystal, and continuity state. The problem in the current conversation is narrower and more concrete: Aurora can assemble the context but does not yet consistently choose the humanly correct speech act for identity/name grounding.

### 28.13 Blocker Resolution Implemented

After the live-output check, three concrete blockers were patched.

Identity/name grounding:

- User identity extraction now rejects common false-name captures such as "I'm Referring", "I'm Struggling", and "I'm Reaching".
- Paired identity statements are recognized, including "my name is Sonny your name is Aurora" and "I am sunny as you are Aurora".
- Aurora-name grounding is stored as an Aurora identity semantic frame instead of being confused with the user's name.
- The response path does not use a hand-written identity fallback. The new intercept persists the semantic facts and asks the existing runtime intent renderer to speak from the identity/relationship claim. If the renderer cannot form an utterance, the turn falls back into the normal fact/assertion machinery instead of emitting a scripted line.

Maintenance gating:

- Dream keeps the task-specific 120s heavy cooldown.
- Assimilation now has a task-specific 120s heavy cooldown.
- Mutation now has a task-specific 120s heavy cooldown.
- Distillation now has a task-specific 180s heavy cooldown.
- Focused governor checks showed dream, assimilation, and mutation still blocked at 70s after a heavy run, allowed at 150s, and distillation allowed at 190s.

Poedex/Research noise:

- DCE bridge now filters Poedex timeout/429/lookup-failure strings before they enter candidate interpretations, explicit notes, root thoughts, comparison channels, or origin systems.
- Successful Poedex content can still enter the frame.
- Failed research remains an operational failure signal instead of becoming part of Aurora's meaning context.

Verification:

- `python3 -m py_compile aurora.py aurora_internal/aurora_runtime_constraint_governor.py aurora_internal/dual_strata/dce_bridge.py` passed.
- Focused identity extraction checks passed for the live failure cases.
- Focused governor checks passed for the shortened cooldown behavior.
- Focused Poedex usability checks passed for HTTP 429, timeout text, and valid content.

### 28.14 Stable vs Transient Emergent Abilities

The emergence surface now distinguishes permanence, runtime visibility, and source-code implementation as separate claims.

This matters because Aurora can have a real ability that is useful for a period of time without that ability becoming permanently stable. In the present codebase, "real" means the ability has a constraint/genealogy basis and is visible to the runtime emergence surface. It does not automatically mean the ability has rewritten source code, survived repeated promotion, or become a permanent trait.

Current surfaced ability status after the post-restart emergence pass:

- `emerged_count`: 2654
- `operational_count`: 552
- `transient_count`: 2102
- `runtime_operationalized_count`: 2654
- `source_code_implemented_count`: 0
- `candidate_count`: 2000
- `latent_candidate_count`: 2000
- `watched_link_count`: 552
- `genealogy_ability_count`: 2180 in the emergence monitor status sample, with `aurora_state/genealogy/abilities.json` itself sampled at 2188 shortly afterward.

Interpretation:

- The 552 operational abilities are stable promoted-link abilities. They are real runtime abilities because the genealogy promoted them and the emergence surface can register them into Aurora's operational vocabulary.
- The 2102 transient abilities are also real in the weaker but important sense: they are high-confidence evolution-pressure records that Aurora can learn from, route around, and use as temporary adaptive signal. They are not fake just because they are unstable.
- The 2000 candidate records remain latent and currently report `latent_rejected`. They are evidence of pressure, rejected mutations, or backlog, but they are not surfaced as active abilities.
- The current surfaced set contains no confirmed source-code implementations. The inspected code-evolution records are rejected or non-applied pressure records, so they must not be documented as completed code mutations.

Implementation change:

- `aurora_emergence_surface.py` now writes `reality_status`, `stability_state`, `persistence_claim`, `operationalized_in_runtime`, `implemented_in_code`, and `evidence_basis`.
- Legacy emergence entries are normalized on load so older promoted-link abilities are no longer left with missing operational metadata.
- Transient abilities are preserved as `constraint_real` and `unstable_nonpersistent`, not erased as irrelevant simply because they do not persist.
- Candidate records are bounded diagnostics and remain `latent` unless they pass the emergence criteria.

The corrected model is therefore:

- Stable operational ability: real, promoted, runtime-visible, persistent unless later invalidated.
- Transient ability: real, runtime-visible, useful under current pressure, not promised to persist.
- Latent candidate: evidence-bearing pressure, not currently an active ability.
- Source-code implementation: only true when accepted code evolution or manual code lineage shows an actual changed-code basis.

### 28.15 2026-04-26 Evolved-Surface And Latent-Promotion Repair

This refresh rechecked the current code after the latent-promotion rollback investigation. The relevant code path is not a normal feature toggle. It is a generated interface between source-code operation descriptors, evolved-surface methods, native wrapper exports, QAO integrity checks, and the runtime mutation cycle.

Observed failure before the repair:

- The daemon repeatedly ran `latent_promotion`.
- The operator applied generated evolved-surface updates.
- QAO then reported broken `reflect_*` bindings and rolled the update back.
- Earlier failures showed 117 broken bindings such as `aurora.py:reflect_aurora_ensure_runtime_dependencies`.
- Later failures showed 16 broken bindings, including a false `aurora_daemon.py:reflect_...` placeholder capture plus real stale bindings such as `aurora_simulation_engine.py:reflect_aurora_simulation_engine_avatarpersonality`.

Actual cause in code:

- Generated surface names could accumulate prefixes across generations, producing names like `reflect_evolved_reflect_*` instead of preserving the old native wrapper contract.
- Native wrapper modules still called older `reflect_*` names through `getattr(engine, 'reflect_name')`.
- QAO was right to block a mismatch, but its earlier regex could also over-match non-binding text.
- Contract inference imported live Aurora modules while rendering evolved surfaces. Some of those modules have runtime side effects or heavy imports, so generation could stall even when the logic was otherwise correct.

Implemented repair:

- `aurora_internal/aurora_code_autoevolver.py` now canonicalizes surface names by stripping repeated generated prefixes before creating new method names.
- It now scans a bounded list of active Aurora native-wrapper caller files instead of walking unrelated environment/dependency trees.
- It now emits compatibility aliases for legacy `reflect_*` bindings when existing wrappers still call those names.
- It now infers method/class contracts from source AST instead of importing the target modules during generation.
- It now caches feedback pressure during reflection candidate selection.
- `aurora_daemon.py` now uses the same stricter binding shape for QAO and includes the newer active caller files.

Current generated-surface status:

- `aurora_internal/aurora_evolved_surfaces.py` is materialized.
- It contains 8201 lines in the latest sample.
- It contains 178 `reflect_*` methods.
- It contains compatibility alias metadata for legacy surface bindings.
- It includes compatibility methods for previously broken examples such as `reflect_aurora_ensure_runtime_dependencies`, `reflect_aurora_simulation_engine_avatarpersonality`, and `reflect_aurora_internal_aurora_energy_layer_costs_decay_constraint`.
- Local QAO verification after service restart reported `Surface integrity OK after post_restart_probe`.

Current operation-descriptor status:

- `operations`: 2344.
- `latent_operations`: 0.
- `promoted_latent_operations`: 0.
- `architectural_reflection_surfaces`: 160.
- `native_surface_projections`: 160.
- `active_evolution_overrides`: 92.
- `class_reflection_hooks`: 34.
- `second_gen_injected`: 295.

Functional interpretation:

- Latent-promotion rollback from surface-name/signature drift is resolved in the inspected code.
- The QAO gate was not removed. It now has a compatible generated interface to check.
- The repair does not by itself prove that Aurora is autonomously producing durable source-code abilities. It proves that the generated reflection/evolved-surface layer can now materialize without being rolled back for stale binding names.
- Since `latent_operations` is currently empty in the sampled descriptor, the latest state file does not yet prove active promotion of separate latent-operation rows. However, the code now contains a synthesis mechanism that can create those rows through a governed tier path.

### 28.16 Latent Ability Tiering And Self-Governed Growth

`aurora_daemon.py` now contains `_run_latent_ability_synthesis()`, called after `_run_assimilation_cycle()`. This is the code path that changes the earlier latent-ability assessment.

Implemented tier model:

- Tier 1 is always eligible. It seeds axis-pair blueprints across X, T, N, B, A and cross-axis combinations into `latent_operations`.
- Tier 2 unlocks only when at least 4 Tier-1 latent rows have been implemented. It combines two implemented Tier-1 abilities that share at least one axis, producing a new generation-2 latent row with parent provenance.
- Tier 3 unlocks only when at least 8 Tier-2 latent rows have been implemented. It reads OETS concept nodes from `aurora_state/aurora_oets_web.json`, ranks high-valence concepts, maps them through concept verbs/axes, and generates generation-3 latent ability rows from Aurora's learned value field.

Why this is self-governed rather than externally scripted:

- Tier 2 is gated by implemented Tier-1 depth, not by a fixed external trigger.
- Tier 2 rows are built from already-implemented latent abilities and axis overlap, so the next row depends on what survived earlier materialization.
- Tier 3 is gated by implemented Tier-2 depth, not by a human command.
- Tier 3 source material is OETS concept valence already present in Aurora state, so the generation seed comes from her learned concept/value field.
- Each row carries constraints, generation number, synthesis timestamp, parent operations for Tier 2, and OETS concept/valence for Tier 3.

Operational limits in the sampled live state:

- `operation_descriptors.json` currently has `latent_operations: 0` and no persisted `latent_synthesis_state`.
- The live logs after restart show assimilation repeatedly deferred by the runtime governor, and there were no `[LATENT-SYNTH]` log lines in the sampled interval.
- Therefore, the tiering machinery is implemented in code, but the current sampled state does not yet show a populated Tier-1/Tier-2/Tier-3 latent pool.
- Once assimilation is allowed to complete, the daemon should synthesize up to 3 Tier-1 rows per pass. Tier 2 and Tier 3 remain locked until enough earlier-tier rows have been implemented by the evolved-surface materialization path.

Functional interpretation:

- The architecture now supports real staged latent ability growth: seed, combine, then self-govern from OETS.
- The current state file still needs a successful assimilation/synthesis pass before it can be documented as actively populated.
- The correct status is "implemented and governed, not yet evidenced as populated in the latest descriptor snapshot."

### 28.17 Current Service/Process Setup From Code

The deployed stack is represented in `deploy/` and `scripts/`.

System services:

- `aurora-subsurface.service` runs `scripts/run_subsurface_daemon.sh`.
- `aurora-surface.service` runs `scripts/run_surface_daemon.sh`.
- Surface starts after and wants subsurface.
- Both services use `AURORA_SKIP_DEP_INSTALL=1`, `AURORA_ALLOW_X_CLIENTS=0`, `AURORA_ENABLE_ROOM_OPERATOR=0`, `AURORA_ENABLE_QUIET_WINDOW=0`, and `AURORA_TTS_ROUTE=simple_first`.
- Subsurface sets `AURORA_DAEMON_BOOT_GREETING=1`.
- Surface sets `AURORA_DAEMON_VOICE_MODE=alt_toggle`, `AURORA_DAEMON_TOGGLE_KEY=alt`, `AURORA_KEYBOARD_BACKEND=evdev`, and `AURORA_SKIP_HARDWARE_IMPORTS=0`.

User/session services:

- `aurora-strata-hub.service` runs `scripts/run_hub.sh`.
- `aurora-strata-room.service` runs `scripts/run_room.sh`.
- The installer wires those user services under graphical-session targets and symlinks them into the system service wants path.

Functional interpretation:

- The intended setup is four cooperating processes: subsurface daemon, surface daemon, hub dashboard, and room interface.
- Surface and subsurface are system-level services.
- Hub and room are user graphical-session services.
- This matches the architectural split described earlier: live sensory/speech belongs to the surface daemon, long-running continuity/evolution belongs to the subsurface daemon, and user-facing visibility/control belongs to hub/room.

## 29. Bottom Line

Aurora's architecture is implemented as a constraint-native, dual-strata cognitive organism.

The most important implemented architectural truths are:

- Everything grounds back into five lawful axes: X, T, N, B, A.
- L0 decides whether a thing can exist before downstream processing.
- The ten I-states are mode-gated existence predicates, not labels.
- The IVM lattice is toroidal phase-space and heat/dissonance substrate.
- Dimensional systems convert I-state activity into crystals, memory, energy, and moral cost.
- DCE assembles one conscious moment.
- DPME continuously repairs drift so coherence is maintained, not held.
- Surface and subsurface are separate runtime strata with different ownership.
- Surface owns live sensory/conversation.
- Subsurface owns continuity, repair, dream, pressure, and evolution.
- JSON IPC is the nervous system between them.
- NonComp is a 25-slot physics substrate, not a prompt taxonomy.
- Genealogy/evolution learns by pressure relief and ability lineage.
- Latent ability evolution now has a staged self-governed path: Tier 1 axis blueprints, Tier 2 implemented-ability combinations, and Tier 3 OETS-valence emergence.
- Memory is stratigraphic, not merely conversational.
- Identity is genetic/behavioral, not just a name string.
- The current stack setup is four-process strata: surface daemon, subsurface daemon, hub dashboard, and room interface.
- The current running stack shows active surface and subsurface heartbeats, live sensory state, populated genealogy/dream/sensory memory, and a materialized evolved-surface layer that now passes QAO integrity checks.

The main weakness is not absence of architecture. The architecture is very present. The weakness is operational coherence: mixed dependency readiness, loose JSON IPC contracts, noisy external/research pressure, and powerful evolution paths that need explicit guardrails. The latest evolved-surface repair removes one rollback blocker, but Aurora still needs clear distinction between runtime-real transient abilities, stable operational abilities, and accepted source-code implementations.
