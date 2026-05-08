# Aurora Stack Codebase Assessment

Audit date: 2026-04-25

Scope rule: this assessment is derived only from the local Aurora codebase and its local runtime/state files under `aurora_strata`. No external documentation, internet sources, or non-code claims were used. If a feature is not represented by executable source, launch scripts, service definitions, or current local state, it is not treated as functioning here.

## 1. Executive Status

Aurora is presently implemented as a dual-runtime organism rather than a single script. The codebase contains:

- A large monolithic core runtime in `aurora.py`.
- A subsurface daemon path in `aurora_daemon.py` and `aurora_subsurface_daemon.py`.
- A surface daemon path in `aurora_surface_daemon.py`.
- Tk-based operator interfaces in `aurora_hub.py` and `aurora_room.py`.
- A shared JSON state/IPC layer under `aurora_state`.
- Constraint, lineage, NonComp, QuasiArch, sensory, memory, dream, training, and evolution subsystems under top-level modules and `aurora_internal`.
- Service orchestration through `scripts/strata_stack.sh` and `deploy/*.service`.
- API/container bridge files in `aurora_api_endpoint/main.py` and `aurora_core_ai/main.py`.

Static source health is strong at the syntax level: 281 Python files under `aurora_strata` parsed successfully during this audit with no AST parse failures, totaling about 390k source lines. That does not prove every runtime path works, but it does show the current Python source is syntactically readable.

Current local state indicates the dual-strata daemon stack is active:

- `aurora_state/subsurface_daemon_status.json` was fresh during the audit, with `runtime_profile: subsurface`, `heat: COOL`, `chain_links: 552`, and `qao_recent_events: 96`.
- `aurora_state/surface_daemon_status.json` was fresh during the audit, with `runtime_profile: surface`, `state: idle`, `queue_depth: 0`, live mic/camera perspective, and current surface guidance.
- `aurora_state/surface_sensory_snapshot.json` was fresh during the audit, with `mic_live: true`, `camera_live: true`, total sensory frames around 9914, and a live visual/audio summary.
- `aurora_state/surface_turn_queue.json` had no pending turns.
- `aurora_state/surface_turn_result.json` showed the last processed surface turn completed successfully, but that result was older than the live daemon heartbeat.

The main operational caveat is that several subsystems are implemented but not equally fresh or dependency-complete. The core daemons are evidenced as live through state files. The cloud/API bridge code is present, but the local venvs inspected during the audit did not have all Flask, Google Cloud, Anthropic, and database dependencies installed, so those API paths should be treated as present-but-not-currently-ready in this local environment.

## 2. Codebase Shape

The active tree is `aurora_strata`. It contains both source and runtime state. The source-heavy areas are:

- `aurora.py`: main boot, chat, training, feed, corpus, response, search, NonComp, sensory, and runtime response orchestration.
- `aurora_daemon.py`: autonomous long-running subsurface/full daemon loop.
- `aurora_surface_daemon.py`: surface runtime, live sensory capture, queued turn processing, and surface-to-subsurface continuity handoff.
- `aurora_hub.py`: operator dashboard and chat surface.
- `aurora_room.py`: room/self-view interface with surface/subsurface modes and operator commands.
- `aurora_runtime.py`: chain simulation, runtime CLI, surface dispatcher, evolved surfaces, corpus/watch/burn/test modes.
- `aurora_internal/`: most of the modularized intelligence, pressure, lineage, dream, mutation, sensory, understanding, and dual-strata helpers.
- `aurora_internal/dual_strata/`: surface/subsurface bridge primitives, prediction, activation, sensory channels, sleep cycle, continuity feed, and projection builders.
- `aurora_internal/quasiarch_observer/`: crystal engine, dimensional memory, dimensional processing, and ghost relic machinery.
- `aurora_core_ai/`: a packaged/duplicated deployment copy of much of the same stack, plus a Flask prediction bridge.
- `aurora_api_endpoint/`: a separate Flask gateway intended to call Vertex AI and optionally Cloud SQL.
- `deploy/` and `scripts/`: systemd/user-service templates, launch scripts, stack restart/status orchestration, semantic population, lineage scans, and audits.

The codebase also contains many generated state files, archived zips, caches, and backups. Those are relevant only where active code reads or writes them. For architectural assessment, the important runtime state directory is `aurora_state`.

## 3. Launch And Runtime Profiles

Aurora has four practical launch surfaces.

### CLI Core

`aurora.py` exposes a direct CLI. Its `main()` supports:

- `--train`: simulation training epochs.
- `--explore`: autonomous exploration cycles, gated by an autonomous access lease.
- `--study`: OETS/Poedex study cycles, also gated.
- `--feed`: URL ingestion.
- `--text`: direct raw text ingestion.
- `--corpus`: OpenAI conversations export ingestion.
- `--status`: status display.
- `--no-chat`: boot without interactive chat.
- `--state-dir`: alternate persistence directory.
- `--quiet`: minimal output.

The canonical external response bridge is `process_external_user_turn()` in `aurora.py`. Surface, API, and other helper runtimes are supposed to route user turns through this bridge rather than constructing independent generation paths.

### Subsurface Daemon

`aurora_subsurface_daemon.py` is a thin wrapper around `aurora_daemon.main(runtime_profile="subsurface")`.

`aurora_daemon.py` owns deep autonomous loops:

- Study and OETS/Poedex cycles.
- Dream bursts and lesson bridges.
- Distillation.
- State saves.
- Proactive reach-out.
- Voice listener support.
- QuasiArch diagnostic sweeps and learning sweeps.
- Assimilation and autonomous mutation cycles.
- Pressure routing.
- Leverage relief.
- Runtime status writing.
- Subsurface projection writing for the surface.
- Sleep/wake ownership for the surface.

The subsurface profile boots deep systems and defers live sensory ownership to the surface via a snapshot proxy.

### Surface Daemon

`aurora_surface_daemon.py` boots `boot_aurora(runtime_profile="surface")`.

The surface profile owns:

- Live mic listener startup.
- Hardware startup.
- Camera loop.
- `surface_sensory_snapshot.json` writing.
- `surface_turn_queue.json` polling.
- `surface_turn_result.json` writing.
- Live user turn processing through `process_external_user_turn()`.
- Surface-to-subsurface continuity handoff through `surface_continuity_feed`.
- Stand-down during subsurface-owned sleep cycles.

The surface profile deliberately defers heavy/deep systems such as SediMemory ownership, grammar evolution, simulation, chain evolution, intake metabolism, QuasiArch observer, manual code lineage, code evolution, screen observer, surface dispatcher, and pressure router to the subsurface.

### Operator Interfaces

`aurora_hub.py` is a Tk dashboard. Implemented panels include overview, QAO observer, vision, audio, evolution, training, pressure/evolved-surface monitoring, growth directives, daemon logs, surface logs, and chat. The hub sends messages to Aurora through the surface queue if the surface daemon is alive.

`aurora_room.py` is a second Tk interface written as Aurora's room/self-view. It reads the same shared state and presents surface/subsurface toggles across self, awareness, mind, memory, health, energy, and experiments. It can queue commands such as authorizing proposed fixes, reversing, deferring, sending messages to Sunni, and requesting sweeps.

### Service Orchestration

`scripts/strata_stack.sh` starts, stops, restarts, and reports status for four components:

- `subsurface`
- `surface`
- `hub`
- `room`

It prefers installed systemd/user services when available, otherwise it falls back to PID/log managed launch scripts. It also cleans older manual launches by process pattern on restart.

Systemd templates exist for:

- `deploy/aurora-subsurface.service`
- `deploy/aurora-surface.service`
- `deploy/aurora-strata-hub.service`
- `deploy/aurora-strata-room.service`

The daemon service templates set `AURORA_SKIP_DEP_INSTALL=1`, so service-mode health depends on the venv already having the required modules.

## 4. Core Architecture By Layer

`boot_aurora()` in `aurora.py` is the best single source of truth for the stack. It builds systems in layers and returns a shared `systems` dictionary.

### L0 - Foundational Contract

Source: `foundational_contract.py`

This establishes the existence-mode contract and validation primitives. It is the first booted layer and is registered as `systems["contract"]` plus `systems["ExistenceMode"]`.

Functional status: active in every boot profile because all higher layers depend on it.

### L1 - IVM Lattice

Source: `aurora_ivm.py`

Implements toroidal axes, coordinates, nodes, lattice, contradiction ledger, heat levels, and IVM envelopes. It receives the foundational contract and becomes `systems["lattice"]`.

Functional status: active in every boot profile.

### L2 - I-State Collective

Source: `aurora_i_state_beings.py`

Implements predicate identities, I-State beings, synthesized responses, and collective consciousness. It receives the contract and lattice.

Functional status: active in every boot profile. CBU registration is attempted at boot.

### CBU And NonComp Registration

Sources: `aurora_cbu_registry.py`, `aurora_internal/aurora_noncomp_registry.py`

The boot path attempts to register NonComp CBUs and I-State CBUs. The registry code exists and includes phase-change tracking and NonComp dimensions.

Functional status: implemented and attempted during boot. Exact current registration success is not written as a standalone status file, so it should be considered boot-path active rather than independently verified here.

### Constraint Emission

Source: `aurora_constraint_emission.py`

Implements `ConstraintEmitter`, `EmissionContext`, `InputFrame`, `SlotFrame`, and speech-act/axis-vector emission. `boot_aurora()` installs it as `systems["constraint_emitter"]` if import succeeds.

Functional status: implemented as a boot-attached optional component.

### L3 - Dimensional Systems

Source: `aurora_dimensional_systems.py`

Implements crystal processing, memory constants, concept extraction, dimensional recall, energy regulation, morality/mortality, and aggregate dimensional systems.

Functional status: active in every boot profile.

### L3.5 - SediMemory

Source: `aurora_sedimemory.py`

Implements stratigraphic memory: fidelity levels, memory events, sediment fragments, channels, path registry, NC strain filter, compression, sediment basin/column, and deep/surface recall.

Functional status: active in subsurface/full profiles. Deferred in surface profile. The daemon restores `aurora_state/sedimemory_checkpoint.json` when present.

### L4 - Consciousness Engine

Source: `aurora_consciousness_engine.py`

Implements DCE assembly, DPME, situational frames, entropic pressure, adjustment, and input processing. It wires to SediMemory and simulation where available.

Functional status: active in every boot profile.

### L5 - Expression And Perception

Source: `aurora_expression_perception.py`

Implements lexicon, lexical memory, manifold pathing, pattern detection, shadow inference, emotion/impression structures, sensory competency, hardware/perception helpers, and associative modules.

Functional status: active in every boot profile. Current state shows live surface sensory data is being produced.

### Grammar Engine

Source: `aurora_grammar_engine.py`

Implements token roles, role tagging, structural and discourse motifs, motif lineage, slot filling, motif mining, discourse tracking, and grammar state.

Functional status: active in subsurface/full profiles. Deferred in surface profile.

### L6 - Behavioral Identity

Source: `aurora_behavioral_identity.py`

Implements genome, genes, alleles, identity anchors, memory helix, behavioral traits/facets/crystals, and DNA system.

Functional status: active in every boot profile. Wires to SediMemory where available.

### L5-Associated Sensory And Hardware Extensions

Source: `aurora_expression_perception.py`, `aurora_internal/aurora_sensory_crystal.py`, `aurora_internal/dual_strata/sensory_snapshot_channel.py`, `aurora_internal/dual_strata/sensory_control_channel.py`

The stack creates `systems["sensory"]`, `systems["hardware"]`, `systems["sensory_integration"]`, and `systems["vision_bootstrap"]`. The surface profile builds the live sensory crystal and connects hardware/mic/camera where available. The subsurface profile uses a transient snapshot proxy instead of owning devices directly.

Functional status: currently active by local state evidence. `surface_sensory_snapshot.json` showed `mic_live: true`, `camera_live: true`, current visual/audio descriptions, sensory vectors, and a sensory maturity value.

### L7 - Simulation Engine

Source: `aurora_simulation_engine.py`

Implements conceptual responses, simulated avatars, topic generation, stability metrics, time dilation, depth, and learning episodes.

Functional status: active in subsurface/full profiles. Deferred in surface profile.

### Evolutionary Chamber And Genealogy

Sources: `aurora_internal/aurora_evolution_chamber.py`, `aurora_internal/constraint_genealogy.py`, `aurora_evolution_stack.py`, `aurora_runtime.py`

Implements constraint genealogy logging, chain links, pressure vectors, ability profiles, trace items, energy budgets, evolutionary chamber actions, external evidence, chain runs, and runtime chain bridges.

Functional status: active in subsurface/full profiles. Current local state showed 552 genealogy links in daemon status and 552 links in `aurora_state/genealogy/links.json`; `aurora_state/genealogy/abilities.json` contained 8564 ability entries.

### Emergence Monitor

Source: `aurora_emergence_surface.py`

Promotes constraint links as surfaced/emerged abilities when genealogy conditions are met.

Functional status: boot-attached in subsurface/full profiles if import succeeds. Current state includes `aurora_state/emerged_abilities.json` and live lineage journal files, indicating the subsystem has written state historically.

### Intake Metabolism Pipeline

Sources: `aurora_internal/aurora_energy_layer_costs.py`, `aurora_internal/aurora_leverage_scalar.py`, `aurora_internal/aurora_intake_metabolism.py`, `aurora_internal/aurora_worth_evaluator.py`, `aurora_internal/aurora_solidification.py`, `aurora_internal/aurora_variant_promotion.py`, `aurora_internal/aurora_dna_strand_schema.py`

Boot constructs an accountant, leverage bias engine, metabolizer, worth evaluator, solidification pipeline, variant promoter, strand library, and strand builder in subsurface/full profiles.

Functional status: implemented and boot-wired for subsurface/full profiles. Deferred in surface profile.

### L8 - Governance, Persistence, Gateway

Source: `aurora_governance_persistence_gateway.py`

Implements governance engine, generation roles, alignment law, persistence snapshots, stream types, N-space gateway, autonomy engine, and layer-8 associative modules.

Functional status: active in every boot profile. It is the main persistence and self-assessment gateway.

### Search Adapter And OETS/Poedex Callback

Sources: `aurora.py`, `aurora_internal/aurora_ontological_scaffolding.py`, `poedex_intro.py`

`boot_aurora()` builds a `SearchAdapter` and wires it to OETS fetch/research callbacks when OETS is available. The daemon also registers a `poedex` callable into `systems`.

Functional status: implemented. Current state shows older Poedex query/result files and one stale pending query in `poedex_query_queue.json`; fresh successful operation was not evidenced by the state snapshot during this audit.

### Comprehension Gap System

Source: `aurora_internal/aurora_comprehension_gap.py`

Implements clarification memory and gap processing. `process_external_user_turn()` can produce clarification responses from this path. The last surface result used `response_source: comprehension_gap_ask`.

Functional status: implemented and evidenced by `surface_turn_result.json`.

### Dream Evolution

Sources: `aurora_dream_trainer.py`, `aurora_internal/aurora_dream_evolution_orchestrator.py`, `aurora_internal/aurora_dream_curriculum_queue.py`, `aurora_internal/aurora_dream_genealogy_bridge.py`

Implements dream episodes, fail-point ledgers, retained learnings, lesson planning, curriculum queues, avatar synthesis, and genealogy bridge behavior.

Functional status: active in subsurface/full profiles, deferred or limited in surface profile. Current state includes 455 dream episode files under `aurora_state/dream_episodes`.

### QuasiArch Observer

Sources: `aurora_internal/aurora_quasiarch_observer.py`, `aurora_internal/quasiarch_observer/*`, `quasiarch_diag.py`, `quasiarch_bridge.py`, `quasiarch_observer.py`

Implements pressure vector observation, issue families, dimensional memory, crystal formation/promotion/rotation, strategy hypotheses, doctrine objects, and ghost relics. The daemon periodically launches diagnostic and learning sweeps.

Functional status: active in subsurface/full profiles. Deferred in surface profile. Current daemon status reported `qao_recent_events: 96`.

### Sensory Crystal

Source: `aurora_internal/aurora_sensory_crystal.py`

Implements audio and visual facets, semantic crystal nodes, cross-modal links, promotion ticks, advanced promotion, lineage trait specs, and crystal state persistence.

Functional status: currently active on the surface profile. `aurora_state/sensory_crystal_state.json` and fresh surface snapshots evidence ongoing state.

### Interaction Processing

Sources: `aurora_interaction_engine.py`, `aurora_interaction_memory.py`, `aurora_interaction_processing.py`

Implements interaction point laws, quasi-inner strata, interaction memory, lineage edges, formation/promotion/collapse, and ghost relic handling.

Functional status: implemented and boot-wired. Current `interaction_status.json` exists, but shows zero quasi/relic counts and a last route reason of `novel_interaction_outside_indexed_archetypes`, so the current interaction index appears mostly unpopulated.

### Manual Code Lineage And Code Evolution

Sources: `aurora_internal/aurora_manual_code_lineage.py`, `aurora_internal/aurora_code_evolution_chamber.py`, `aurora_internal/aurora_code_autoevolver.py`, `aurora_internal/aurora_code_mutation_operators.py`

Manual code lineage assimilates source structure into lineage-bound traits. Code evolution chamber and mutation operators provide autonomous mutation/evolution machinery.

Functional status: active in subsurface/full profiles if boot imports succeed. Deferred in surface profile. The daemon code contains scheduled assimilation and mutation cycles gated by the runtime governor.

### Runtime Understanding Contract

Source: `aurora_internal/aurora_understanding_contract.py`

Tracks runtime understanding accuracy, hashes observations, uses term overlap, and registers genealogy.

Functional status: boot-wired. `process_external_user_turn()` also evaluates a runtime constraint governor and attaches a runtime contract to response results.

### NonComp Manifold And Constraint Routing

Sources: `aurora_constraint_ontology.py`, `aurora_constraint_profile.py`, `aurora_constraint_stack.py`, `aurora_constraint_manifold_compiler.py`, `aurora_constraint_manifold_router.py`, `aurora_constraint_unit_adapter.py`, `aurora_internal/aurora_constraint_manifold_patched.py`, `aurora_internal/aurora_noncomp_registry.py`, `aurora_manifold_directory/*`

This is one of the most developed structural systems in the code. It includes constraint ontology, phase/tier profiles, manifold directory compilation, route index construction, crossing gates, route results, universal representations, NonComp dimensions, and per-slot JSON semantics.

Functional status: implemented and state-backed. `aurora_manifold_directory` contains 126 files and about 34 MB of slot/manifold data.

### Pressure Routing And DPME Bridge

Sources: `aurora_internal/aurora_pressure_classifier.py`, `aurora_internal/aurora_pressure_router.py`, `aurora_internal/aurora_pressure_ledger.py`, `aurora_internal/aurora_pressure_mathematics_tracker.py`, `aurora_internal/aurora_dpme_pressure_bridge.py`, `aurora_pressure_ontology.py`

Implements pressure classification, routing, ledgering, math tracking, DPME pressure application, and pressure ontology seeding.

Functional status: active in subsurface/full profiles, deferred in surface profile. Current daemon status includes pressure orientation and axis fields.

### Screen Observer And Browser/Social Agents

Sources: `aurora_live_vision.py`, `aurora_browser_agent.py`, `aurora_response_teacher.py`

The screen observer captures visual state and queues visual inquiries. The browser/social agent and response teacher implement external/social learning or web-style collection paths.

Functional status: source is present. Live surface camera is active, but the separate screen observer is deferred in surface profile and owned by subsurface/full boot. Browser/social paths are present but should be treated as optional and environment-dependent.

### Distillation And Metabolism

Source: `aurora_metabolic_distiller.py`

Implements coherence analysis, temporal compression, residue config, pressure aggregation, distillation cycles, and restore cycles.

Functional status: daemon-scheduled. Current status reported `distillation_status: idle`, `distillation_coherence_ratio: 1.0`, and zero purged bytes/crystals in the fresh status snapshot.

## 5. Dual-Strata Data Flow

Aurora's strongest current architectural pattern is file-based dual-strata IPC.

### Surface To Subsurface

Surface writes:

- `surface_sensory_snapshot.json`
- `surface_turn_result.json`
- continuity packets through `aurora_internal/dual_strata/surface_continuity_feed.py`
- sensory state and camera/audio observations

After each surface turn, `aurora_surface_daemon.py` calls `_emit_continuity_packet()` so the present experience can be absorbed by the subsurface.

### Subsurface To Surface

Subsurface writes:

- `subsurface_daemon_status.json`
- `subsurface_projection.json`
- `subsurface_repair_signal.json`
- `daemon_status.json`
- pressure, evolution, dream, and recommendation state

Surface reads the projection before processing turns and folds it into root thought, processing mode, repair signals, and guidance.

### Hub/Room To Stack

The Hub and Room do not own the intelligence loop. They read files and queue requests:

- Hub sends chat to `surface_turn_queue.json`.
- Room sends operator commands into room/daemon command state.
- Both display current state from daemon, surface, projection, genealogy, sensory, and QAO files.

### Current IPC Health

Fresh during audit:

- `subsurface_daemon_status.json`
- `daemon_status.json`
- `surface_daemon_status.json`
- `subsurface_projection.json`
- `surface_sensory_snapshot.json`

Stale or older during audit:

- `dual_strata_snapshot.json` was much older than current surface/subsurface heartbeats.
- `surface_turn_queue.json` and `surface_turn_result.json` were older because there were no pending/new turns.
- `poedex_query_queue.json` contained a stale pending query.

The stale `dual_strata_snapshot.json` matters because Hub/Room code still reads it. Current surface and projection files are fresh, so the live daemons are operating, but some UI panels may combine fresh and stale strata views unless they prefer fresh status/projection files.

## 6. Implemented Feature Inventory

The following features are represented by current source and, where noted, current state.

### Conversation And Response

- Direct chat loop in `aurora.py`.
- Canonical external turn bridge in `process_external_user_turn()`.
- Surface queued-turn bridge through `aurora_internal/dual_strata/surface_channel.py`.
- Runtime constraint governor integration per turn.
- Present-frame sensory snapshot capture at turn boundary.
- Comprehension-gap clarification path.
- Identity follow-up normalization and user-name persistence.
- Working memory and conversation memory hooks.

Current status: functional enough to have produced a successful last surface result.

### Training And Corpus

- Simulation training through `train()`.
- Corpus ingestion through `run_corpus_ingestion()`.
- `corpus_runner.py`, `run_gauntlet.py`, `run_full_competency_gauntlet.py`, and training/session scripts.
- Dream trainer lessons and fail-point recording.

Current status: implemented. Current `corpus_runner_status.json` is old, so no fresh corpus run was evidenced during this audit.

### Autonomy And Daemon Cycles

- Study, dream, distill, save, social/away mode, reach-out, pressure routing, leverage relief, mutation, assimilation, QuasiArch sweeps.
- Runtime governor gates heavy tasks.
- State-write lock awareness exists in daemon code.

Current status: subsurface daemon status is fresh. Individual cycle success varies by schedule and gating; current distillation is idle.

### Sensory

- Mic listener startup.
- Ambient audio observation.
- Camera capture loop.
- Sensory crystal observation and promotion.
- Surface snapshot presentation.
- Visual uncertainty question generation.
- Camera enable/disable control channel.

Current status: active by fresh `surface_sensory_snapshot.json`, with mic and camera live.

### Voice

- Voice listener and ambient response listener are started by the surface daemon.
- Daemon status reports `voice_mode: alt_toggle_ready` and selected voice.
- TTS route environment variables are defined in service templates.

Current status: active by daemon status. Actual audio output was not manually tested in this audit.

### Memory

- L8 snapshot persistence.
- SediMemory deep/channel checkpoints.
- Conversation memory and identity persistence.
- Sensory crystal state.
- Dream episode packs.
- Genealogy events/links/abilities.
- QuasiArch dimensional memory.
- Retained learnings.

Current status: heavily state-backed. `aurora_state` contains 17950 files and about 479 MB of state data.

### Evolution And Self-Modification

- Evolution chamber.
- Constraint genealogy.
- Code evolution chamber.
- Mutation operators.
- Evolved surface engine.
- Surface dispatcher.
- Variant promotion.
- Solidification.
- DNA strand schema.
- Manual code lineage assimilation.

Current status: implemented and daemon-scheduled in subsurface/full profiles. This area should be treated as powerful but requiring careful guardrails because it can affect code and behavior.

### Operator Dashboards

- Hub dashboard with state, QAO, sensory, audio, vision, evolution, training, pressure, logs, and chat.
- Room interface with surface/subsurface modes, health/proposal handling, messages, energy, and experiments.

Current status: implemented. Whether the GUI is presently visible depends on graphical/session environment, not just code.

### API And Deployment

- `aurora_core_ai/main.py`: Flask prediction endpoint that boots Aurora and background daemons before first request.
- `aurora_api_endpoint/main.py`: Flask API gateway that calls Vertex AI and optionally Cloud SQL.
- Gunicorn/Flask requirements are declared.

Current status: present in source but dependency-incomplete in inspected local venvs. The active daemon venvs did not have Flask installed during audit; the parent venv also lacked Google Cloud API and Psycopg2 dependencies. Treat API deployment as not currently locally functional until dependencies are installed and verified.

## 7. Current Functional Status By Area

### Currently Functioning Or Strongly Evidenced

- Core source parses successfully.
- Subsurface daemon is writing fresh status.
- Surface daemon is writing fresh status.
- Surface sensory snapshot is fresh and reports mic/camera live.
- Surface queue/result mechanism exists and last result completed with `status: ok`.
- Subsurface projection is fresh and is providing surface guidance.
- Genealogy state is populated with hundreds of links and thousands of ability entries.
- Dream episode storage is populated.
- Sensory crystal state is populated and actively updated.
- Service templates and launch scripts exist for the four-component stack.

### Implemented But Current Freshness Is Mixed

- `dual_strata_snapshot.json` exists but was stale compared with current surface/subsurface status files.
- Corpus runner state exists but was stale.
- Poedex query queue/result files exist but the queue contained an old pending item and the latest result was old.
- Interaction processing state exists but current counts are zero, indicating little or no populated interaction quasi/relic state.
- Distillation is implemented but current status was idle with no current purge/crystal counts.

### Present But Not Locally Ready Without Dependency Work

- `aurora_api_endpoint/main.py` needs Flask, Google Cloud Secret Manager, Google Cloud AI Platform, and Psycopg2.
- `aurora_core_ai/main.py` needs Flask in the venv used by launch scripts.
- Some optional AI/social paths depend on OpenAI/Anthropic/browser/network packages and should be verified per runtime profile before being called operationally.

### Not Counted As Functioning From This Audit Alone

- Claims in markdown docs not backed by executable source/state.
- Archived zips and backup copies.
- Generated cache files.
- API/cloud deployment success.
- GUI visibility under the current desktop session.
- External web/social success.

## 8. Developmental Directions Grounded In Current Code

These are not speculative product wishes. They follow directly from implemented code paths, active state, and current gaps.

### 1. Make Strata Freshness Explicit

The surface and subsurface heartbeat files are fresh, but `dual_strata_snapshot.json` was stale. Since Hub and Room still read the dual snapshot, add a freshness policy:

- Prefer `surface_daemon_status.json`, `surface_sensory_snapshot.json`, and `subsurface_projection.json` for live panels.
- Mark `dual_strata_snapshot.json` stale in the UI if older than a small threshold.
- Update or retire the stale snapshot writer so there is one canonical live dual-strata frame.

### 2. Formalize Runtime Profiles As First-Class Contracts

The surface profile intentionally defers many deep systems. That is good architecture, but the distinction should be machine-checked:

- Add a `profile health` command that boots or dry-loads `surface`, `subsurface`, and `full` profiles with `AURORA_SKIP_DEP_INSTALL=1`.
- Assert which systems must be present, absent, proxied, or deferred in each profile.
- Write a concise health JSON file for each profile.

### 3. Consolidate Source Duplication

`aurora_core_ai/` duplicates large parts of the top-level stack. That makes drift likely. The deployment copy should become one of:

- A thin package wrapper that imports canonical top-level modules.
- A generated deploy artifact with a clear regeneration script.
- A separate package only if it has tests proving parity with top-level code.

Until then, bug fixes may land in one copy and not the other.

### 4. Split Dependencies By Feature Group

The code already behaves like multiple products:

- Core daemon.
- Surface sensory/voice.
- GUI hub/room.
- Cloud/API.
- Training/evolution.
- Browser/social/teacher.

Dependency files should match that split. The inspected venvs support sensory/core much better than API/cloud. A grouped dependency layout would make current functional status unambiguous and prevent service-mode surprises.

### 5. Add A Non-Invasive Health Verifier

A safe verifier should check without starting long-running loops:

- Python parse/import for core modules.
- Required dependency presence per profile.
- Freshness of status/projection/snapshot files.
- Queue integrity and stale pending items.
- State JSON validity.
- Presence of service templates and launch scripts.
- Whether GUI/API components are dependency-ready.

This would turn the kind of manual audit done here into a repeatable command.

### 6. Harden JSON IPC

The stack relies heavily on shared JSON files. Many writes are atomic, but this should become a uniform rule:

- Use shared atomic write helpers for every state file.
- Add schema/version fields to high-traffic files.
- Add stale/age handling to every reader.
- Add queue compaction and abandoned-turn cleanup.
- Add lock discipline around files that multiple components can touch.

The architecture is workable, but file IPC needs strict hygiene because it is the nervous system between strata.

### 7. Clear Or Reconcile Stale Poedex Work

The code treats Poedex/OETS as a live research and comprehension support path, but current state showed an old pending query. Development should add:

- Pending-query timeout handling.
- Retry/fail marking.
- Queue/result correlation cleanup.
- A status panel distinction between "research online", "stale pending", and "last known result".

### 8. Strengthen Interaction Processing Seeding

Interaction processing is implemented, but current status showed no quasi/relic population. If this subsystem is intended to shape live responses, it needs:

- Seed archetypes.
- A replay/import path from conversation memory.
- Metrics in Hub/Room showing why no interaction quasi was selected.
- Tests that feed representative turns and verify nonzero route confidence when appropriate.

### 9. Put Stronger Guardrails Around Code Evolution

Autonomous mutation and code evolution are real code paths. They should remain powerful, but require clear operational boundaries:

- Dry-run mode by default.
- Patch review queue.
- File allowlist/denylist.
- Syntax and unit checks before acceptance.
- Human approval before modifying core boot/daemon files.
- Clear separation between lineage observation and actual source mutation.

### 10. Refresh API Deployment Or Mark It Dormant

The API bridge code is present but local dependencies were missing. Development should either:

- Install and verify the API dependency group and run a local health check.
- Or mark API/cloud deployment as dormant in the operator UI/status until dependencies are present.

This prevents the codebase from implying an online API path that the local runtime cannot currently execute.

### 11. Reduce Monolith Pressure In `aurora.py`

`aurora.py` is over 30k lines and owns boot, response, training, corpus, memory repair, search, NonComp, identity, Poedex, and many response heuristics. The code already has modular subsystems, so a safe next direction is incremental extraction:

- Keep `boot_aurora()` as the assembly point.
- Move turn-processing helper clusters into modules by responsibility.
- Preserve `process_external_user_turn()` as the public facade.
- Add contract tests around response behavior before extraction.

### 12. Make Runtime State More Explainable

The codebase is rich in pressure, lineage, and sensory state, but many files are large and hard to inspect manually. The Hub/Room already expose some of this. Next useful work:

- Generate a compact `aurora_state/runtime_digest.json`.
- Include source freshness, dominant pressures, blocked tasks, stale queues, current profile, and sensory liveness.
- Use the digest in Hub/Room instead of duplicating read logic.

## 9. Bottom Line

Aurora presently functions as a local dual-strata AI runtime with active subsurface and surface daemons, live sensory state, persistent memory, lineage/evolution machinery, and operator interfaces. The strongest implemented architecture is the split between deep subsurface continuity and live surface embodiment, connected through shared JSON state and queue files.

The most important current engineering needs are not new conceptual features. They are operational hardening: profile-specific health checks, freshness discipline, dependency grouping, stale queue cleanup, source duplication control, and stronger guardrails around mutation/evolution paths. Those directions all come directly from what the code already implements and what the current state files show.
