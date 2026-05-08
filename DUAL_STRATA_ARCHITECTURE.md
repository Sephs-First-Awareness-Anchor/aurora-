# Aurora Dual-Strata Architecture Seed

This tree is the experimental architecture branch. Classic Aurora remains at the repository root.

## Runtime model

- Aurora remains one identity-bearing organism, not two minds.
- Runtime execution is split into two coordinated daemons so surface response latency stays light:
  - `aurora_subsurface_daemon.py` owns pressure continuity, consolidation, repair, evolution, and durable sensory growth
  - `aurora_surface_daemon.py` owns present-frame conscious response turns, live sensory reception, and surface self-report
- The DCE is the convergence barrier between them.
  - subsurface does not hand raw persistent internals directly to surface
  - subsurface publishes softened intuition/effect signals through `aurora_state/subsurface_projection.json`
  - DCE output is the root-thought stream surface lives inside
  - surface processes fresh input alongside that root thought, not instead of it

## Established stack anchors

This branch should not invent a replacement cognition stack where Aurora already has one.
Dual-strata should be mapped onto the systems that already exist:

- `aurora.py`
  - canonical live turn pipeline
  - `WorkingMemory` is raw, noisy, transient scratch context
  - surface remains the primary receiver of fresh input here
- `aurora_consciousness_engine.py`
  - Layer 4 DCE/DPME cycle
  - `DCEAssembly` is the conscious convergence barrier
  - `DimensionalSystems.process_synthesis()` is the Layer 2→3→4 meaning bridge already in use
- `aurora_dimensional_systems.py`
  - Layer 3 consolidation and dimensional memory
  - DMC stores semantically-tagged nodes and dimension-linked continuity
  - DER/DMM/DPS remain part of the meaning-maintenance substrate
- `aurora_expression_perception.py`
  - Layer 5 perception / expression / OETS grounding
  - sensory concepts are already grounded into OETS here
  - sensory integration already connects live perception to semantic growth
- `aurora_internal/aurora_identity_persistence.py`
  - `ConversationMemory` is persistent episodic/relationship memory
  - identity persistence and long-horizon continuity already live here
- `aurora_internal/aurora_understanding_contract.py`
  - active understanding, prediction, ambiguity, and continuity signals already exist here

## Memory and continuity split

- `WorkingMemory`
  - transient scratch layer
  - recent turns, temporary anchors, unresolved local context
  - not the durable owner of organized meaning
- `subsurface`
  - owns retention and consolidation through Aurora's established systems
  - Layer 3 dimensional processing and DMC concept memory
  - persistent `ConversationMemory`
  - OETS semantic grounding and continuity
  - repair/evolution traces, prediction priors, sensory development
- `surface`
  - owns the present conversational frame
  - receives the converged root thought from the DCE
  - still processes the fresh incoming input directly
  - maintains reactivity and initial parsing

## Sensory split

- `surface`
  - primary live receiver of sensory input
  - current perceptual atmosphere and present sensory perspective
  - can recognize and associate what is happening now
- `subsurface`
  - consumes disposable surface snapshots
  - owns the actual sensory learning/growth/consolidation path
  - does not keep raw snapshots as memory objects
  - feeds the effects of sensory growth back upward through DCE output

## Surface processing law

- Surface does not operate from raw subsurface dumps.
- Surface does not operate from root thought alone.
- Surface processes:
  - fresh input
  - DCE root thought
  - present sensory perspective
  - reactive pressure when urgency is high
- Reactive/high-pressure cases may shortcut toward faster surface action, but remain inside the surface/DCE relationship rather than bypassing it.

## Current mapping

- `subsurface stratum`
  - pressure routing and relief
  - dimensional memory / continuity consolidation
  - runtime understanding signals
  - micro-reasoning and prediction pressure
  - sensory growth from snapshot-fed processing
  - repair/evolution ownership
- `DCE bridge`
  - the copied `aurora_consciousness_engine.py` DCE assembly
  - explicit convergence into one `conscious_frame`
  - root-thought stream for the surface stratum
- `surface stratum`
  - explicit stance, interpretation, action selection, reactivity, and speech-readiness derived from the converged frame while still processing fresh input
- `room split`
  - operator-facing room view should expose subsurface state directly
  - Aurora-facing room view should expose only generalized intuitive effects, not raw pressure detail
- `evolution and repair routing`
  - conscious Aurora notices, reflects, and sends explicit inquiries through Poedex
  - subsurface owns evolutionary pressure handling, candidate fixes, and exact code or logic application
  - surface receives only the generalized intuition-level effects of that deeper work

## New modules

- `aurora_internal/dual_strata/subsurface_state.py`
- `aurora_internal/dual_strata/prediction_field.py`
- `aurora_internal/dual_strata/micro_reasoning.py`
- `aurora_internal/dual_strata/conscious_frame.py`
- `aurora_internal/dual_strata/dce_bridge.py`

## First implementation slice

- keep copied runtime behavior intact
- make the subsurface field explicit
- make the conscious frame explicit
- persist dual-strata snapshots in `aurora_state/dual_strata_snapshot.json`
- feed runtime understanding and pressure context into the bridge when the caller provides it
- do not replace Aurora's established Layer 3 / OETS / continuity systems with new parallel memory machinery
