# Aurora Ownership Map

**Authors:** Sunni (Sir) Morningstar and Cael Devo

<!-- Generated from docs/module_ownership.json by scripts/render_module_ownership.py. Do not edit by hand. -->

This map places every source file in the repository on one ladder, the way her crystals are built. The layers (L0 to L8) stay the one architecture of desktop Aurora; the ladder is a view over the files for finding things, and it never moves a file, changes an import or adds a package. Moving files would change the paths that her code lineage, function ids and fault records are keyed by, so files stay where they are (decided 2026-11-18).

| Order | Holds |
|---|---|
| King quasi | The repository. |
| Quasi | A domain: desktop Aurora, the phone app, the ACM, and the repository's CI. |
| Higher order | A subsystem inside a domain. Desktop's are the function categories. |
| Composite | Files that import evidence joins inside one subsystem. |
| Base | One source file. |

The record is `docs/module_ownership.json`. Change a domain, subsystem, layer or duty there, then run `python scripts/render_module_ownership.py --update-derived` and `python scripts/render_module_ownership.py`. Composites and the files each test exercises are derived from the source, never typed in. The test `tests/test_layer_module_ownership_categories.py` fails if this file, the record and the source disagree.

## Coverage

Covers every source file in the repository: desktop Aurora's Python (runtime, scripts and tests), the phone app's Dart, Kotlin, Java and Python, the ACM's Rust and Python, launchers, service units, prototypes and CI workflows. Data, state, documentation and build configuration are not source and are listed below. It lists 985 files.

Covered: files ending in `.py`, `.dart`, `.rs`, `.kt`, `.java`, `.sh`, `.bat`, `.ps1`, `.jsx`, `.html`, `.service`, and files under `.github/workflows/`, skipping folders named `.git`, `__pycache__`, `node_modules`, `build`, `.dart_tool`, `target`, `aurora_state`, `aurora_state_test`, `aurora_logs`, `vector_data`, `lessons`, `aurora_genealogy`.

Not covered:

| Path | What it holds |
|---|---|
| `aurora_state/, aurora_state_test/, aurora_logs/, vector_data/, lessons/, aurora_genealogy/` | Runtime state, logs, lessons and genealogy data |
| `docs/ and root .md files` | Documentation, install notes and build reports |
| `root .json and .jsonl files` | Maps, audits, manifests and run history |
| `Cargo.toml, pubspec.yaml, Gradle files, buildozer.spec, requirements and pytest.ini` | Build and dependency configuration |
| `flutter_app/android/ resources and manifests` | Android resources and XML configuration |

## King quasi: The Aurora repository

| Quasi (domain) | Holds | Subsystems | Composites | Files |
|---|---|---|---|---|
| Desktop Aurora | Her Python runtime and everything that runs, tests or maintains it on a computer. | 16 | 43 | 927 |
| Phone app | The Flutter app with its Android services and on-device Python. | 5 | 4 | 22 |
| ACM | The Rust kernel, its runner and the native Python ACM runtime. | 8 | 3 | 30 |
| Repository and CI | Workflows that build, test and run the other domains. | 1 | 0 | 6 |

## Quasi: Desktop Aurora

| Higher order (subsystem) | Holds | Composites | Files in composites | Base files |
|---|---|---|---|---|
| Entry and runtime | Entry points, the turn loop, process orchestration, launchers and service units. | 1 | 7 | 21 |
| Foundation and constraint layers | Foundational contract, IVM lattice, X/T/N/B/A constraint physics, NonComp, pressure and leverage. | 4 | 21 | 16 |
| Beings and dimensional systems | I-State beings, dimensional systems, consciousness assembly and simulation (the L2 to L4 and L7 layer files). | 1 | 4 | 1 |
| Crystal ops | The concept-crystal store, its evidence-based growth, ingestion and persistence, interaction crystals, and the crystal types QuasiArch shares with live processing. | 4 | 24 | 2 |
| Memory | SediMemory, working and interaction memory, turn and resolution records. | 1 | 2 | 10 |
| Reasoning and understanding | Representational resolution, propositions, the causal reasoning waveform, comparison and understanding. | 5 | 21 | 21 |
| Genealogy, lineage and evidence | Constraint genealogy, code and ability lineage, function provenance, evidence qualification, WARP. | 3 | 16 | 9 |
| Learning, dreams and development | Training, dreams, curriculum, evolution chambers, curiosity and habitat. | 6 | 21 | 21 |
| Perception and expression | Sensory and hardware IO, intake, utterance parsing, expression and the reply well-formedness gate. | 1 | 9 | 14 |
| Identity and language | Behavioral identity, language state, lexicon, grammar and word use. | 3 | 7 | 8 |
| Governance, persistence and health | Persistence, checkpoints, autonomy, runtime faults and health, metabolic clock, fail-closed guards. | 2 | 21 | 2 |
| Dual strata (surface and subsurface) | The dual-strata package and the surface/subsurface daemons and substrate. | 2 | 39 | 7 |
| Bridges and external tools | Praxis, ACM, scouting, research dispatch and tool registries. | 3 | 9 | 8 |
| Investigative and diagnostic | Observers, canaries, probes, shadows, audits, reports and test setup. Some observers run live and write their own records, as the QuasiArch observer and the learning probe do; the QuasiArch observer stays here. | 5 | 12 | 23 |
| Tests | The pytest suite. Each test lists the files it exercises. | 2 | 4 | 461 |
| Scripts, tooling and prototypes | Maintenance, audit, migration and analysis scripts, and the HTML and JSX prototypes. | 0 | 0 | 86 |

## Quasi: Phone app

| Higher order (subsystem) | Holds | Composites | Files in composites | Base files |
|---|---|---|---|---|
| App shell and screens | The Flutter entry point, home and hub screens, overlay entry and the orb widget. | 1 | 4 | 1 |
| Habitat | The habitat model, renderer, gesture layer and bridge, and the habitat screens. | 1 | 6 | 0 |
| Dart bridges | Dart bridges to her Python stack and to Praxis. | 0 | 0 | 2 |
| On-device Python | Python that Chaquopy runs on the phone: the entry bridge, the cv2 shim and the historical experience environment. | 1 | 2 | 1 |
| Android services | Kotlin and Java Android components: the main activity, Aurora and overlay services, screen observer and boot receiver. | 1 | 5 | 1 |

## Quasi: ACM

| Higher order (subsystem) | Holds | Composites | Files in composites | Base files |
|---|---|---|---|---|
| ACM core | Axes, crystal, drift and sedi modules of the kernel. | 0 | 0 | 5 |
| Constraint physics machine | CPM organs and scheduler. | 0 | 0 | 3 |
| X-Aurora ISA, VM and JIT | The instruction set, virtual machine and JIT. | 1 | 4 | 0 |
| Expression | Face, colour and renderer. | 1 | 4 | 0 |
| Hardware drivers | IDT, PIC, PIT, ports, PS/2 and UART. | 1 | 7 | 0 |
| Bridge protocol | The kernel side of the bridge to her Python stack. | 0 | 0 | 2 |
| Boot and runner | The kernel entry point, the host runner and the boot script. | 0 | 0 | 4 |
| Native Python runtime | The Python-native ACM runtime. | 0 | 0 | 1 |

## Quasi: Repository and CI

| Higher order (subsystem) | Holds | Composites | Files in composites | Base files |
|---|---|---|---|---|
| CI workflows | GitHub Actions workflows for runs, clones, experiments, the APK and Python CI. | 0 | 0 | 6 |

## Desktop layers (L0 to L8)

### L0 (Foundational contract)

| Module | Role | Subsystem |
|---|---|---|
| `foundational_contract.py` | layer file | Foundation and constraint layers |

### L1 (IVM / geometry substrate)

| Module | Role | Subsystem |
|---|---|---|
| `aurora_ivm.py` | layer file | Foundation and constraint layers |

### L2 (I-State synthesis)

| Module | Role | Subsystem |
|---|---|---|
| `aurora_i_state_beings.py` | layer file | Beings and dimensional systems |

### L3 (Dimensional transforms)

| Module | Role | Subsystem |
|---|---|---|
| `aurora_dimensional_systems.py` | layer file | Beings and dimensional systems |

### L4 (Consciousness assembly)

| Module | Role | Subsystem |
|---|---|---|
| `aurora_consciousness_engine.py` | layer file | Beings and dimensional systems |

### L5 (Perception/IO surface)

| Module | Role | Subsystem |
|---|---|---|
| `aurora_expression_perception.py` | layer file | Perception and expression |
| `aurora_sensory_competency.py` | migrated to L5 owner | (file not on main) |
| `aurora_hardware_interface.py` | migrated to L5 owner | (file not on main) |
| `aurora_sensory_integration.py` | migrated to L5 owner | (file not on main) |
| `aurora_vision_bootstrap.py` | migrated to L5 owner | (file not on main) |

### L6 (Behavioral identity)

| Module | Role | Subsystem |
|---|---|---|
| `aurora_behavioral_identity.py` | layer file | Identity and language |
| `aurora_internal/aurora_language_state.py` | identity-expression adaptation support | Identity and language |

### L7 (Simulation)

| Module | Role | Subsystem |
|---|---|---|
| `aurora_simulation_engine.py` | layer file | Beings and dimensional systems |

### L8 (Governance / persistence / gateway)

| Module | Role | Subsystem |
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

### Orchestrator

| Module | Role | Subsystem |
|---|---|---|
| `aurora.py` | single runtime entrypoint | Entry and runtime |

## Reviewed against what the code does

Every Python module in desktop Aurora's runtime was screened for who imports it and whether it writes files. These 29 files were then read, because the screen showed duties beyond their name or because their name and their job differ.

| File | Subsystem | Also | What it actually does |
|---|---|---|---|
| `aurora_interaction_engine.py` | Crystal ops | – | Interaction-lineage compression semantics: the facet sets and InteractionQuasiInnerStrata the interaction crystals use. Booted by aurora.py. |
| `aurora_interaction_processing.py` | Crystal ops | – | Interaction crystal formation, promotion, collapse and routing. aurora.py boots InteractionProcessing; its crystals subclass the QuasiArch crystal types. |
| `aurora_internal/aurora_boot_parity.py` | Investigative and diagnostic | – | Tracks parity between aurora.py boot_aurora and aurora_runtime.py boot_stack. Only tests use it. |
| `aurora_internal/aurora_episode_slip_profiler.py` | Learning, dreams and development | Investigative and diagnostic | EpisodeRubricSummary feeds structural-pressure steering, the specialized avatar synthesizer and the dream genealogy bridge. |
| `aurora_internal/aurora_fault_audit.py` | Investigative and diagnostic | – | AST audit for swallowed exceptions, used by the fault instrumentation script and tests. |
| `aurora_internal/aurora_local_llm_bridge.py` | Governance, persistence and health | – | Fail-closed guard: the retired local-model adapter keeps its names so stale imports fail closed, and there is no model path. Only tests import it. |
| `aurora_internal/aurora_pf1_5_instruments.py` | Perception and expression | Investigative and diagnostic | wellformed_and_coherent decides whether a candidate reply is accepted, in aurora.py and aurora_working_memory.py. Measuring PF1.5 is its second job. |
| `aurora_internal/aurora_quasiarch_observer.py` | Investigative and diagnostic | Entry and runtime | The QuasiArch observer, a live organ: aurora.py boots it at L8+, it runs during boot and every turn, and it writes its own state under aurora_state/quasiarch_observer (runtime_state.json, which aurora_hub.py and aurora_diag.py read; interventions; ghost relics). Its query answers carry authoritative False. In gated mode only (AURORA_QUASIARCH_MODE=gated; advisory is the default), advise_training_plan() writes qao_mutation_signal.json once doctrine confidence passes the gate, and the daemon's _select_discovery_driven_operator reads it, marks it consumed and may take its operator hint as the next code mutation. So it is an input to the daemon as well as an observer. |
| `aurora_internal/aurora_runtime_health.py` | Governance, persistence and health | – | Readiness semantics (degraded is not ready unless a caller opts in). Not wired into the runtime: tests and the fault audit use it. |
| `aurora_internal/aurora_semantic_probe_battery.py` | Identity and language | Investigative and diagnostic | Its function-word set _STRONG_FUNCTION_WORDS is used by aurora_proposition_frame.py and aurora_constraint_semantic_continuity.py, and its _parseable check by aurora_expression_perception.py. The probe battery itself is diagnostic. |
| `aurora_internal/aurora_stack_trace_instrumentation.py` | Genealogy, lineage and evidence | Investigative and diagnostic | instrument_stack wraps runtime methods to record call lineage when AURORA_STACK_TRACE is on. Off by default. |
| `aurora_internal/aurora_surface_doc.py` | Dual strata (surface and subsurface) | Investigative and diagnostic | full_report() gives aurora_surface_dispatcher.py its axis-to-surface routing table, and it writes a pressure log. |
| `aurora_internal/aurora_system_introspection.py` | Genealogy, lineage and evidence | Investigative and diagnostic | Source-derived map of executable functions (function ids are module.qualname) and per-turn decision provenance. aurora.py boots it and connects it to perception; it writes its own state and does not change response selection. |
| `aurora_internal/dual_strata/perturbation_probe.py` | Dual strata (surface and subsurface) | Investigative and diagnostic | Run by the topological semantic coordinator through run_perturbation_probe. |
| `aurora_internal/quasiarch_development_inquiry.py` | Investigative and diagnostic | – | Development inquiry helper for the QuasiArch observer. It runs wherever the observer runs, which includes the phone app's runtime. |
| `aurora_internal/quasiarch_observer/__init__.py` | Crystal ops | Investigative and diagnostic | Re-exports the package. aurora_interaction_processing.py imports CrystalInstance and CrystalOrder through it, which loads every submodule when interaction processing boots. |
| `aurora_internal/quasiarch_observer/crystal_engine.py` | Crystal ops | Investigative and diagnostic | Crystal law: what each facet and relational point means at each crystal order (CrystalEngine, FacetLaw, RelationalPointLaw, CrystalOrder). QuasiArch reads it, and CrystalOrder is also the order ladder of the live interaction crystals in aurora_interaction_processing.py, so it is operational, not only investigative. |
| `aurora_internal/quasiarch_observer/dimensional_memory.py` | Investigative and diagnostic | – | QuasiArch lineage memory (DimensionalMemory, IntegratedMemoryPipeline). Only the QuasiArch observer calls it, and it runs during boot and turns because the observer does. |
| `aurora_internal/quasiarch_observer/dimensional_processing.py` | Crystal ops | Investigative and diagnostic | CrystalInstance, RelationalPoint, crystal formation and promotion. InteractionCrystalInstance in aurora_interaction_processing.py subclasses CrystalInstance and builds RelationalPoint objects, and aurora.py boots InteractionProcessing, so these types hold live state. |
| `aurora_internal/quasiarch_observer/ghost_relics.py` | Investigative and diagnostic | – | Ghost relic records (GhostRelic, GhostRelicSystem). Only the QuasiArch observer calls it; it runs at boot when the observer starts. |
| `aurora_learning_probe.py` | Investigative and diagnostic | Learning, dreams and development | LearningProbe, a live organ on the phone: the phone app's aurora_bridge.py starts it as systems['learning_probe'] and it appends to aurora_state/learning_probe.jsonl. Nothing on desktop imports it. |
| `conftest.py` | Investigative and diagnostic | – | pytest setup only: puts the repository root on sys.path for tests/. Not part of the runtime. |
| `flutter_app/android/app/src/main/python/aurora_bridge.py` | On-device Python | – | Chaquopy entry point that AuroraService.kt calls. It boots the root aurora.py stack and exposes text in and text out, so audio stays on the Kotlin and Flutter side. |
| `flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py` | On-device Python | – | Rehearsal environment that scores her rehearsed reply against what was really said next. aurora.py's change lineage names it as a target file, and tests import it by module name, so desktop depends on it too. |
| `flutter_app/android/app/src/main/python/cv2.py` | On-device Python | – | Android stand-in for opencv: numpy and Pillow versions of the cv2 calls her stack uses, with camera frames fed in from the Kotlin CameraX bridge. |
| `reply_aurora.py` | Scripts, tooling and prototypes | Reasoning and understanding | Command-line script Sir runs by hand from a terminal: it appends his reply to aurora_state/correspondence/from_sunni.jsonl using the correspondence loop's own helpers, and aurora_internal/aurora_correspondence_loop.py reads that file the next time the loop runs. No entry point, boot path or production importer reaches it, so it is tooling, not runtime; nothing imports it, and the loop and its test only name it in their docstrings. |
| `run_full_competency_gauntlet.py` | Investigative and diagnostic | – | Script entry point for the competency gauntlet. It writes aurora_state/last_full_competency_gauntlet.json. Nothing in covered code imports it. |
| `run_gauntlet.py` | Investigative and diagnostic | – | Script entry point that starts the daemon and runs the gauntlet. It opens aurora_state/daemon.log and hands it to the daemon process as stdout and stderr, as aurora_hub.py and the other launchers do, so the log's lines are the daemon's own output; aurora_metabolic_distiller.py reads and trims that log as one of its residue sources. It also writes its own results under aurora_state. Nothing in covered code imports it. |
| `run_probe_battery.py` | Investigative and diagnostic | – | Script entry point for the semantic probe battery. It boots against a scratch copy of aurora_state and writes results to aurora_state/probe_battery/results/. Nothing in covered code imports it. |

## Composites

A composite is a connected group of two or more files in one subsystem, joined by import edges that stay inside that subsystem. Edges come from Python imports (desktop by dotted path from the repo root, other domains by module name in their own folder), Dart imports, Rust mod declarations and crate, super and self paths, and Kotlin or Java class names used in the same folder. Shell, batch, PowerShell, HTML, JSX, systemd and workflow files have no import edges here, so they stay base files. A composite is named after its subsystem and numbered by size; its hub is the member with the most links inside it. A candidate the knowledge graph marks import_only is not promoted; it is listed under composite_candidates and its files stay base files.

Support is the knowledge graph's verdict: `supported` and `partly_supported` mean calls, data flow, spawns or shared state join the files as well as imports; `unchecked` means the graph has not seen this group yet.

| Composite | Subsystem | Hub | Files | Support |
|---|---|---|---|---|
| `runtime.1` | Entry and runtime | `aurora.py` | 7 | partly_supported |
| `foundation.1` | Foundation and constraint layers | `aurora_internal/aurora_noncomp_registry.py` | 15 | partly_supported |
| `foundation.2` | Foundation and constraint layers | `aurora_computational_model.py` | 2 | supported |
| `foundation.3` | Foundation and constraint layers | `aurora_internal/aurora_pressure_classifier.py` | 2 | supported |
| `foundation.4` | Foundation and constraint layers | `aurora_manifold_directory_reader.py` | 2 | supported |
| `dimensional.1` | Beings and dimensional systems | `aurora_consciousness_engine.py` | 4 | partly_supported |
| `crystal.1` | Crystal ops | `aurora_internal/crystal_runtime.py` | 14 | supported |
| `crystal.2` | Crystal ops | `aurora_interaction_processing.py` | 5 | partly_supported |
| `crystal.3` | Crystal ops | `aurora_internal/aurora_lexical_crystals.py` | 3 | supported |
| `crystal.4` | Crystal ops | `aurora_crystal_state_bridge.py` | 2 | supported |
| `memory.1` | Memory | `aurora_interaction_memory.py` | 2 | supported |
| `reasoning.1` | Reasoning and understanding | `aurora_representational_address.py` | 8 | supported |
| `reasoning.2` | Reasoning and understanding | `aurora_internal/aurora_constraint_semantic_continuity.py` | 5 | partly_supported |
| `reasoning.3` | Reasoning and understanding | `aurora_internal/aurora_strategic_horizon.py` | 4 | supported |
| `reasoning.4` | Reasoning and understanding | `aurora_internal/aurora_confluence.py` | 2 | supported |
| `reasoning.5` | Reasoning and understanding | `aurora_internal/aurora_contradiction_perception.py` | 2 | supported |
| `genealogy.1` | Genealogy, lineage and evidence | `aurora_internal/constraint_genealogy.py` | 12 | supported |
| `genealogy.2` | Genealogy, lineage and evidence | `aurora_genealogy_promotion_dimension_observer.py` | 2 | supported |
| `genealogy.3` | Genealogy, lineage and evidence | `aurora_internal/aurora_attribution_trace.py` | 2 | supported |
| `learning.1` | Learning, dreams and development | `aurora_internal/aurora_evolution_chamber.py` | 5 | partly_supported |
| `learning.2` | Learning, dreams and development | `aurora_dream_trainer.py` | 4 | supported |
| `learning.3` | Learning, dreams and development | `aurora_internal/aurora_dream_evolution_orchestrator.py` | 4 | supported |
| `learning.4` | Learning, dreams and development | `aurora_training_pulse.py` | 3 | supported |
| `learning.5` | Learning, dreams and development | `aurora_internal/aurora_capability_binding.py` | 3 | supported |
| `learning.6` | Learning, dreams and development | `aurora_possibility_selves.py` | 2 | supported |
| `perception.1` | Perception and expression | `aurora_expression_perception.py` | 9 | partly_supported |
| `language.1` | Identity and language | `aurora_internal/aurora_conversation_rubric_engine.py` | 3 | partly_supported |
| `language.2` | Identity and language | `aurora_grammar_engine.py` | 2 | supported |
| `language.3` | Identity and language | `aurora_internal/aurora_communication_emergence.py` | 2 | supported |
| `governance.1` | Governance, persistence and health | `aurora_internal/aurora_runtime_faults.py` | 19 | partly_supported |
| `governance.2` | Governance, persistence and health | `aurora_internal/aurora_metabolic_steps.py` | 2 | supported |
| `strata.1` | Dual strata (surface and subsurface) | `aurora_internal/dual_strata/__init__.py` | 37 | partly_supported |
| `strata.2` | Dual strata (surface and subsurface) | `aurora_internal/aurora_surface_dispatcher.py` | 2 | supported |
| `bridges.1` | Bridges and external tools | `aurora_internal/scouting/contracts.py` | 4 | supported |
| `bridges.2` | Bridges and external tools | `aurora_praxis_messenger.py` | 3 | supported |
| `bridges.3` | Bridges and external tools | `aurora_desktop_agent.py` | 2 | supported |
| `investigative.1` | Investigative and diagnostic | `aurora_genealogy_cooccurrence_observatory.py` | 4 | supported |
| `investigative.2` | Investigative and diagnostic | `aurora_causal_vs_representational_probe.py` | 2 | supported |
| `investigative.3` | Investigative and diagnostic | `aurora_genealogy_difference_shadow.py` | 2 | supported |
| `investigative.4` | Investigative and diagnostic | `aurora_internal/aurora_quasiarch_observer.py` | 2 | supported |
| `investigative.5` | Investigative and diagnostic | `aurora_internal/quasiarch_observer/dimensional_memory.py` | 2 | supported |
| `tests.1` | Tests | `tests/test_communication_bar.py` | 2 | supported |
| `tests.2` | Tests | `tests/test_confluence.py` | 2 | supported |
| `phone_ui.1` | App shell and screens | `flutter_app/lib/main.dart` | 4 | partly_supported |
| `phone_habitat.1` | Habitat | `flutter_app/lib/habitat/habitat_gesture_layer.dart` | 6 | partly_supported |
| `phone_python.1` | On-device Python | `flutter_app/android/app/src/main/python/aurora_bridge.py` | 2 | supported |
| `phone_android.1` | Android services | `flutter_app/android/app/src/main/kotlin/org/aurora/app/AuroraService.kt` | 5 | supported |
| `acm_xaurora.1` | X-Aurora ISA, VM and JIT | `aurora-acm/kernel/src/xaurora/isa.rs` | 4 | partly_supported |
| `acm_expression.1` | Expression | `aurora-acm/kernel/src/expression/mod.rs` | 4 | partly_supported |
| `acm_hw.1` | Hardware drivers | `aurora-acm/kernel/src/hw/mod.rs` | 7 | partly_supported |

### Not promoted: imports only

Imports join these files, but the knowledge graph found no call, flow, spawn or shared state between them, so they stay base files.

| Candidate | Subsystem | Files |
|---|---|---|
| `tests.3` | Tests | `tests/test_generation_collapse_regression.py`, `tests/test_pf1_5_instruments.py` |
| `acm_core.1` | ACM core | `aurora-acm/kernel/src/acm/axes.rs`, `aurora-acm/kernel/src/acm/crystal.rs`, `aurora-acm/kernel/src/acm/drift.rs`, `aurora-acm/kernel/src/acm/mod.rs`, `aurora-acm/kernel/src/acm/sedi.rs` |
| `acm_cpm.1` | Constraint physics machine | `aurora-acm/kernel/src/cpm/mod.rs`, `aurora-acm/kernel/src/cpm/organ.rs`, `aurora-acm/kernel/src/cpm/scheduler.rs` |
| `acm_bridge.1` | Bridge protocol | `aurora-acm/kernel/src/bridge/mod.rs`, `aurora-acm/kernel/src/bridge/protocol.rs` |

## Cross-domain links (candidates, not promoted)

What the knowledge graph found when it checked this record. A composite the graph marks import_only (no call, flow, spawn or shared state joins its files) is not promoted: it stays a candidate and its files stay base files. Cross-domain links are evidence-backed candidates for higher-order links; none is promoted without Sir's word. Knowledge graph, PR #263 at commit 099d43f: knowledge_graph/coverage/composites.json and claims.json.

| Files | Domains | Edges the graph found |
|---|---|---|
| `aurora_internal/aurora_runtime_faults.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 77, IMPORTS 1 |
| `concept_crystal.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 22, IMPORTS 1, INSTANTIATES 1 |
| `aurora_habitat.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 12, IMPORTS 1, INSTANTIATES 1 |
| `aurora_internal/aurora_constraint_manifold_patched.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | INSTANTIATES 12 |
| `aurora_internal/dual_strata/strata_link.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 11, IMPORTS 1 |
| `aurora_waveform_pressure.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 8, IMPORTS 1 |
| `aurora_praxis_bridge.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 7, IMPORTS 1 |
| `aurora_internal/aurora_lexical_grounding.py` and `flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py` | desktop and phone | CALLS 6, IMPORTS 1 |
| `aurora_praxis_messenger.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 6, IMPORTS 1 |
| `aurora_dream_trainer.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 4, IMPORTS 1, INSTANTIATES 1 |
| `aurora_reasoning_games.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 4, IMPORTS 1, INSTANTIATES 1 |
| `flutter_app/android/app/src/main/python/aurora_bridge.py` and `geological_baseline.py` | phone and desktop | CALLS 4, IMPORTS 1, INSTANTIATES 1 |
| `aurora.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 4, IMPORTS 1 |
| `aurora_internal/dual_strata/sensory_snapshot_channel.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 4, IMPORTS 1 |
| `constraint_evolutionary_sim.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 3, IMPORTS 1, INSTANTIATES 1 |
| `aurora_internal/aurora_communication_emergence.py` and `flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py` | desktop and phone | CALLS 4 |
| `aurora_internal/aurora_live_experience.py` and `flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py` | desktop and phone | CALLS 3, IMPORTS 1 |
| `aurora_language_field.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 2, IMPORTS 1, INSTANTIATES 1 |
| `aurora_curiosity_engine.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 1, IMPORTS 1, INSTANTIATES 1 |
| `aurora_habitat_motivation.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 2, IMPORTS 1 |
| `aurora_internal/aurora_clone_harvest.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 2, IMPORTS 1 |
| `aurora_internal/aurora_reasoning_paths.py` and `flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py` | desktop and phone | CALLS 2, IMPORTS 1 |
| `aurora_internal/aurora_resolution_ledger.py` and `flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py` | desktop and phone | CALLS 2, IMPORTS 1 |
| `aurora_internal/aurora_runtime_faults.py` and `flutter_app/android/app/src/main/python/cv2.py` | desktop and phone | CALLS 2, IMPORTS 1 |
| `aurora_internal/aurora_sensory_crystal.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 2, IMPORTS 1 |
| `aurora_internal/aurora_turn_persistence.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 2, IMPORTS 1 |
| `aurora_internal/lesson_replay.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 2, IMPORTS 1 |
| `aurora_learning_probe.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 1, IMPORTS 1, INSTANTIATES 1 |
| `aurora_self_grounding.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 1, IMPORTS 1, INSTANTIATES 1 |
| `aurora-acm/native/aurora_acm_native.py` and `aurora_i_state_beings.py` | acm and desktop | IMPORTS 1, INSTANTIATES 1 |
| `aurora-acm/native/aurora_acm_native.py` and `aurora_ivm.py` | acm and desktop | IMPORTS 1, INSTANTIATES 1 |
| `aurora-acm/native/aurora_acm_native.py` and `foundational_contract.py` | acm and desktop | IMPORTS 1, INSTANTIATES 1 |
| `aurora_computational_model.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | IMPORTS 1, INSTANTIATES 1 |
| `aurora_internal/aurora_clone_harvest.py` and `flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py` | desktop and phone | CALLS 1, IMPORTS 1 |
| `aurora_internal/aurora_confluence.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 1, IMPORTS 1 |
| `aurora_internal/aurora_constraint_semantic_continuity.py` and `flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py` | desktop and phone | CALLS 1, IMPORTS 1 |
| `aurora_internal/aurora_representation_exchange.py` and `flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py` | desktop and phone | CALLS 2 |
| `aurora_internal/dual_strata/subsurface_presence_runtime.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 1, IMPORTS 1 |
| `aurora_internal/tool_registry.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 1, IMPORTS 1 |
| `aurora_persistence_utils.py` and `flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py` | desktop and phone | CALLS 1, IMPORTS 1 |
| `aurora_quantum_dream_substrate.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 1, IMPORTS 1 |
| `aurora_scout_daemon.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 1, IMPORTS 1 |
| `aurora_sensory_fallback.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 1, IMPORTS 1 |
| `aurora_tool_mind.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | IMPORTS 1, INSTANTIATES 1 |
| `aurora_vocabulary_seed_apply.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | CALLS 1, IMPORTS 1 |
| `aurora-acm/kernel/src/bridge/mod.rs` and `aurora_acm_bridge.py` | acm and desktop | endpoint:SUBSCRIBES/EMITS 1 |
| `aurora-acm/kernel/src/bridge/protocol.rs` and `aurora_acm_bridge.py` | acm and desktop | endpoint:EMITS/SUBSCRIBES 1 |
| `aurora_internal/dual_strata/__init__.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | IMPORTS 1 |
| `aurora_sedimemory.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | IMPORTS 1 |
| `aurora_simulation_engine.py` and `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop and phone | IMPORTS 1 |
| `flutter_app/android/app/src/main/python/aurora_bridge.py` and `foundational_contract.py` | phone and desktop | IMPORTS 1 |
| `flutter_app/android/app/src/main/python/aurora_bridge.py` and `tests/test_capability_binding.py` | phone and desktop | CALLS 1 |

## Every file by domain and subsystem

Composite is blank for a base file that no import joins to another file in its subsystem. Layer is given for desktop modules a layer section names.

### Desktop Aurora / Entry and runtime

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora.py` | runtime.1 | orchestrator | name_and_docstring |
| `aurora_daemon.py` | runtime.1 |  | name_and_docstring |
| `aurora_hub.py` |  |  | name_and_docstring |
| `aurora_internal/__init__.py` | runtime.1 |  | name_and_docstring |
| `aurora_internal/aurora_turn_chain.py` | runtime.1 |  | name_and_docstring |
| `aurora_internal/aurora_turn_compute_graph.py` |  |  | name_and_docstring |
| `aurora_runtime.py` | runtime.1 |  | name_and_docstring |
| `corpus_runner.py` | runtime.1 |  | name_and_docstring |
| `deploy/aurora-strata-hub.service` |  |  | location |
| `deploy/aurora-strata-room.service` |  |  | location |
| `deploy/aurora-subsurface.service` |  |  | location |
| `deploy/aurora-surface.service` |  |  | location |
| `run_aurora.py` |  |  | name_and_docstring |
| `run_chain.py` |  |  | name_and_docstring |
| `run_corpus.py` | runtime.1 |  | name_and_docstring |
| `run_gui_linux_mac.sh` |  |  | location |
| `run_gui_windows.bat` |  |  | location |
| `scripts/install_systemd_service.sh` |  |  | location |
| `scripts/run_aurora.sh` |  |  | location |
| `scripts/run_daemon.sh` |  |  | location |
| `scripts/run_hub.sh` |  |  | location |
| `scripts/run_room.sh` |  |  | location |
| `scripts/run_scout_worker.sh` |  |  | location |
| `scripts/run_subsurface_daemon.sh` |  |  | location |
| `scripts/run_surface_daemon.sh` |  |  | location |
| `scripts/windows/install_subsurface_task.ps1` |  |  | location |
| `scripts/windows/run_subsurface.bat` |  |  | location |
| `start_vector.sh` |  |  | location |

### Desktop Aurora / Foundation and constraint layers

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora_625_pressure_map.py` |  |  | name_and_docstring |
| `aurora_computational_model.py` | foundation.2 |  | name_and_docstring |
| `aurora_constraint_emission.py` | foundation.1 |  | name_and_docstring |
| `aurora_constraint_engine.py` | foundation.1 |  | name_and_docstring |
| `aurora_constraint_field_map.py` |  |  | name_and_docstring |
| `aurora_constraint_head.py` | foundation.2 |  | name_and_docstring |
| `aurora_constraint_manifold.py` | foundation.1 |  | name_and_docstring |
| `aurora_constraint_manifold_compiler.py` | foundation.1 |  | name_and_docstring |
| `aurora_constraint_manifold_router.py` |  |  | name_and_docstring |
| `aurora_constraint_ontology.py` |  |  | name_and_docstring |
| `aurora_constraint_signature_resolver.py` |  |  | name_and_docstring |
| `aurora_constraint_stack.py` |  |  | name_and_docstring |
| `aurora_constraint_unit_adapter.py` | foundation.1 |  | name_and_docstring |
| `aurora_internal/aurora_axis_emergence.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_boundary_envelope.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_constraint_manifold_patched.py` | foundation.1 |  | name_and_docstring |
| `aurora_internal/aurora_dpme_pressure_bridge.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_leverage_scalar.py` | foundation.1 |  | name_and_docstring |
| `aurora_internal/aurora_noncomp_registry.py` | foundation.1 |  | name_and_docstring |
| `aurora_internal/aurora_ontological_scaffolding.py` | foundation.1 | L8 | name_and_docstring |
| `aurora_internal/aurora_polarity_gradient.py` | foundation.1 |  | name_and_docstring |
| `aurora_internal/aurora_pressure_adapter.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_pressure_classifier.py` | foundation.3 |  | name_and_docstring |
| `aurora_internal/aurora_pressure_ledger.py` | foundation.1 |  | name_and_docstring |
| `aurora_internal/aurora_pressure_mathematics_tracker.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_pressure_router.py` | foundation.3 |  | name_and_docstring |
| `aurora_internal/aurora_structural_pressure_steering.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_tensor_expressions.py` |  |  | name_and_docstring |
| `aurora_ivm.py` | foundation.1 | L1 | name_and_docstring |
| `aurora_manifold_directory/__init__.py` |  |  | name_and_docstring |
| `aurora_manifold_directory/noncomp_field.py` |  |  | name_and_docstring |
| `aurora_manifold_directory_reader.py` | foundation.4 |  | name_and_docstring |
| `aurora_manifold_lookup.py` | foundation.4 |  | name_and_docstring |
| `aurora_noncomp_layer_compiler.py` | foundation.1 |  | name_and_docstring |
| `aurora_noncomp_manifold_compiler.py` | foundation.1 |  | name_and_docstring |
| `aurora_pressure_ontology.py` |  |  | name_and_docstring |
| `foundational_contract.py` | foundation.1 | L0 | name_and_docstring |

### Desktop Aurora / Beings and dimensional systems

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora_consciousness_engine.py` | dimensional.1 | L4 | name_and_docstring |
| `aurora_dimensional_systems.py` | dimensional.1 | L3 | name_and_docstring |
| `aurora_i_state_beings.py` | dimensional.1 | L2 | name_and_docstring |
| `aurora_istate_operations.py` |  |  | name_and_docstring |
| `aurora_simulation_engine.py` | dimensional.1 | L7 | name_and_docstring |

### Desktop Aurora / Crystal ops

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora_core_concept_crystallization.py` |  |  | name_and_docstring |
| `aurora_crystal_ingestion.py` | crystal.1 |  | name_and_docstring |
| `aurora_crystal_state_bridge.py` | crystal.4 |  | name_and_docstring |
| `aurora_interaction_engine.py` | crystal.2 |  | reviewed |
| `aurora_interaction_processing.py` | crystal.2 |  | reviewed |
| `aurora_internal/aurora_lexical_crystals.py` | crystal.3 |  | name_and_docstring |
| `aurora_internal/aurora_representation_crystals.py` | crystal.3 |  | name_and_docstring |
| `aurora_internal/aurora_sensory_crystal.py` |  |  | name_and_docstring |
| `aurora_internal/crystal_associations.py` | crystal.1 |  | name_and_docstring |
| `aurora_internal/crystal_convergence.py` | crystal.1 |  | name_and_docstring |
| `aurora_internal/crystal_facets.py` | crystal.1 |  | name_and_docstring |
| `aurora_internal/crystal_grammar.py` | crystal.1 |  | name_and_docstring |
| `aurora_internal/crystal_interior.py` | crystal.1 |  | name_and_docstring |
| `aurora_internal/crystal_lexicon.py` | crystal.1 |  | name_and_docstring |
| `aurora_internal/crystal_maturity.py` | crystal.1 |  | name_and_docstring |
| `aurora_internal/crystal_promotion.py` | crystal.1 |  | name_and_docstring |
| `aurora_internal/crystal_runtime.py` | crystal.1 |  | name_and_docstring |
| `aurora_internal/crystal_sensory.py` | crystal.1 |  | name_and_docstring |
| `aurora_internal/crystal_store.py` | crystal.1 |  | name_and_docstring |
| `aurora_internal/crystal_substitutability.py` | crystal.1 |  | name_and_docstring |
| `aurora_internal/crystal_weave.py` | crystal.1 |  | name_and_docstring |
| `aurora_internal/quasiarch_observer/__init__.py` | crystal.2 |  | reviewed |
| `aurora_internal/quasiarch_observer/crystal_engine.py` | crystal.2 |  | reviewed |
| `aurora_internal/quasiarch_observer/dimensional_processing.py` | crystal.2 |  | reviewed |
| `concept_crystal.py` | crystal.3 |  | name_and_docstring |
| `crystalzip.py` | crystal.4 |  | name_and_docstring |

### Desktop Aurora / Memory

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora_developmental_log.py` |  |  | name_and_docstring |
| `aurora_interaction_memory.py` | memory.1 |  | name_and_docstring |
| `aurora_internal/aurora_conversation_episode_compiler.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_difference_buffer.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_resolution_ledger.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_solidification.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_turn_persistence.py` | memory.1 |  | name_and_docstring |
| `aurora_sedimemory.py` |  |  | name_and_docstring |
| `aurora_turn_ledger.py` |  |  | name_and_docstring |
| `aurora_understanding_sediment.py` |  |  | name_and_docstring |
| `aurora_working_memory.py` |  |  | name_and_docstring |
| `geological_baseline.py` |  |  | name_and_docstring |

### Desktop Aurora / Reasoning and understanding

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora_boundary_hypothesis.py` | reasoning.2 |  | name_and_docstring |
| `aurora_concept_derivation.py` |  |  | name_and_docstring |
| `aurora_constraint_reasoner.py` | reasoning.1 |  | name_and_docstring |
| `aurora_internal/aurora_attention_engine.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_causal_generation.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_comprehension_gap.py` | reasoning.2 | L8 | name_and_docstring |
| `aurora_internal/aurora_confluence.py` | reasoning.4 |  | name_and_docstring |
| `aurora_internal/aurora_constraint_semantic_continuity.py` | reasoning.2 |  | name_and_docstring |
| `aurora_internal/aurora_contradiction_perception.py` | reasoning.5 |  | name_and_docstring |
| `aurora_internal/aurora_correspondence_loop.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_cost_diff_score.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_entropy_detector.py` | reasoning.3 |  | name_and_docstring |
| `aurora_internal/aurora_frontier_ops.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_live_possibility_frontier.py` | reasoning.1 |  | name_and_docstring |
| `aurora_internal/aurora_operational_synthesis.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_operator_composer.py` | reasoning.3 |  | name_and_docstring |
| `aurora_internal/aurora_primitive_extractor.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_primitive_perspective.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_proposition_frame.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_proposition_substrate.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_propositional_understanding.py` | reasoning.4 |  | name_and_docstring |
| `aurora_internal/aurora_reasoning_paths.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_recursive_causal_reasoning_waveform.py` | reasoning.2 |  | name_and_docstring |
| `aurora_internal/aurora_reflective_readdressing.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_relation_pairs.py` | reasoning.5 |  | name_and_docstring |
| `aurora_internal/aurora_relational_comparison.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_representation_exchange.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_rubric_influence_graph.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_shadow_state.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_strategic_horizon.py` | reasoning.3 |  | name_and_docstring |
| `aurora_internal/aurora_understanding_contract.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_unformed_patterns.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_worth_evaluator.py` | reasoning.3 |  | name_and_docstring |
| `aurora_referent_hypothesis.py` | reasoning.2 |  | name_and_docstring |
| `aurora_reflexive_interpreter.py` | reasoning.1 |  | name_and_docstring |
| `aurora_representational_address.py` | reasoning.1 |  | name_and_docstring |
| `aurora_representational_resolution.py` | reasoning.1 |  | name_and_docstring |
| `aurora_representational_resolution_base.py` | reasoning.1 |  | name_and_docstring |
| `aurora_semantic_intention_bridge.py` |  |  | name_and_docstring |
| `aurora_thought_formation.py` | reasoning.1 |  | name_and_docstring |
| `aurora_toroidal_circulation.py` |  |  | name_and_docstring |
| `aurora_waveform_pressure.py` | reasoning.1 |  | name_and_docstring |

### Desktop Aurora / Genealogy, lineage and evidence

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora_closure_basis.py` | genealogy.1 |  | name_and_docstring |
| `aurora_genealogy_environment.py` | genealogy.1 |  | name_and_docstring |
| `aurora_genealogy_promotion_dimension_observer.py` | genealogy.2 |  | name_and_docstring |
| `aurora_genealogy_representation_resolver.py` | genealogy.1 |  | name_and_docstring |
| `aurora_genealogy_same_event_correlation.py` | genealogy.2 |  | name_and_docstring |
| `aurora_internal/aurora_ability_lineage_compiler.py` | genealogy.1 |  | name_and_docstring |
| `aurora_internal/aurora_attribution_trace.py` | genealogy.3 |  | name_and_docstring |
| `aurora_internal/aurora_dna_strand_schema.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_evolutionary_ancestry_bridge.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_icc_ledger.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_lineage_bound_traits.py` | genealogy.1 |  | name_and_docstring |
| `aurora_internal/aurora_lineage_runtime_activation.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_live_lineage_journal.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_manual_code_lineage.py` | genealogy.1 |  | name_and_docstring |
| `aurora_internal/aurora_stack_trace_instrumentation.py` |  |  | reviewed |
| `aurora_internal/aurora_system_introspection.py` | genealogy.3 |  | reviewed |
| `aurora_internal/aurora_universal_function_lineage.py` |  |  | name_and_docstring |
| `aurora_internal/constraint_genealogy.py` | genealogy.1 |  | name_and_docstring |
| `aurora_internal/evidence_qualification.py` |  |  | name_and_docstring |
| `aurora_internal/genealogy_evidence_journal.py` | genealogy.1 |  | name_and_docstring |
| `aurora_internal/lineage_canonical.py` | genealogy.1 |  | name_and_docstring |
| `aurora_warp_protocol.py` | genealogy.1 |  | name_and_docstring |
| `genealogy_signature_bridge.py` | genealogy.1 |  | name_and_docstring |
| `tensor_occupancy_hook.py` |  |  | name_and_docstring |
| `tensor_occupancy_warp_bridge.py` | genealogy.1 |  | name_and_docstring |

### Desktop Aurora / Learning, dreams and development

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora_classroom.py` | learning.2 |  | name_and_docstring |
| `aurora_curiosity_engine.py` |  |  | name_and_docstring |
| `aurora_dream_substrate.py` |  |  | name_and_docstring |
| `aurora_dream_trainer.py` | learning.2 |  | name_and_docstring |
| `aurora_evolution_stack.py` | learning.1 |  | name_and_docstring |
| `aurora_experiential_sim.py` | learning.4 |  | name_and_docstring |
| `aurora_explore.py` | learning.4 |  | name_and_docstring |
| `aurora_habitat.py` |  |  | name_and_docstring |
| `aurora_habitat_motivation.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_capability_assimilator.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_capability_binding.py` | learning.5 |  | name_and_docstring |
| `aurora_internal/aurora_code_autoevolver.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_code_evolution_chamber.py` | learning.1 |  | name_and_docstring |
| `aurora_internal/aurora_cognitive_experience_chamber.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_corpus_lifecycle.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_development_experiment.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_developmental_ecology.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_directed_training_corpus.py` | learning.2 |  | name_and_docstring |
| `aurora_internal/aurora_dream_curriculum_queue.py` | learning.3 |  | name_and_docstring |
| `aurora_internal/aurora_dream_evolution_orchestrator.py` | learning.3 |  | name_and_docstring |
| `aurora_internal/aurora_dream_genealogy_bridge.py` | learning.3 |  | name_and_docstring |
| `aurora_internal/aurora_episode_slip_profiler.py` | learning.3 |  | reviewed |
| `aurora_internal/aurora_evolution_chamber.py` | learning.1 |  | name_and_docstring |
| `aurora_internal/aurora_evolution_hook.py` | learning.1 |  | name_and_docstring |
| `aurora_internal/aurora_evolved_surfaces.py` | learning.1 |  | name_and_docstring |
| `aurora_internal/aurora_general_execution_foundry.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_learned_index.py` | learning.5 |  | name_and_docstring |
| `aurora_internal/aurora_learned_rules.py` | learning.5 |  | name_and_docstring |
| `aurora_internal/aurora_learning_pipeline.py` | learning.2 |  | name_and_docstring |
| `aurora_internal/aurora_second_gen.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_variant_promotion.py` |  |  | name_and_docstring |
| `aurora_internal/lesson_replay.py` |  |  | name_and_docstring |
| `aurora_possibility_selves.py` | learning.6 |  | name_and_docstring |
| `aurora_quantum_dream_substrate.py` | learning.6 |  | name_and_docstring |
| `aurora_reasoning_games.py` |  |  | name_and_docstring |
| `aurora_response_teacher.py` |  |  | name_and_docstring |
| `aurora_training_pulse.py` | learning.4 |  | name_and_docstring |
| `aurora_training_run.py` |  |  | name_and_docstring |
| `aurora_vocabulary_seed_apply.py` |  |  | name_and_docstring |
| `backfill_concept_associations.py` |  |  | name_and_docstring |
| `constraint_evolutionary_sim.py` |  |  | name_and_docstring |
| `run_intensive_intervals.py` |  |  | name_and_docstring |

### Desktop Aurora / Perception and expression

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora_articulation.py` |  |  | name_and_docstring |
| `aurora_concept_imager.py` | perception.1 |  | name_and_docstring |
| `aurora_emergence_surface.py` |  |  | name_and_docstring |
| `aurora_expression_perception.py` | perception.1 | L5 | name_and_docstring |
| `aurora_hardware_io.py` | perception.1 |  | name_and_docstring |
| `aurora_image_ingestion.py` | perception.1 |  | name_and_docstring |
| `aurora_internal/aurora_input_identity.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_input_pressure.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_intake_metabolism.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_live_experience.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_pf1_5_instruments.py` | perception.1 |  | reviewed |
| `aurora_internal/aurora_response_pressure_tuner.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_sender_state.py` | perception.1 |  | name_and_docstring |
| `aurora_internal/aurora_turn_parse_cache.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_utterance_parser.py` |  | L8 | name_and_docstring |
| `aurora_live_vision.py` | perception.1 |  | name_and_docstring |
| `aurora_perception_primitives.py` | perception.1 |  | name_and_docstring |
| `aurora_sensory_fallback.py` |  |  | name_and_docstring |
| `aurora_streaming_expression.py` |  |  | name_and_docstring |
| `aurora_vision_clustering.py` | perception.1 |  | name_and_docstring |
| `aurora_voice.py` |  |  | name_and_docstring |
| `aurora_voice_gate.py` |  |  | name_and_docstring |
| `termux_voice_bridge.sh` |  |  | location |

### Desktop Aurora / Identity and language

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora_behavioral_identity.py` |  | L6 | name_and_docstring |
| `aurora_grammar_engine.py` | language.2 |  | name_and_docstring |
| `aurora_internal/aurora_communication_emergence.py` | language.3 |  | name_and_docstring |
| `aurora_internal/aurora_conversation_rubric_engine.py` | language.1 |  | name_and_docstring |
| `aurora_internal/aurora_language_state.py` | language.2 | L6 | name_and_docstring |
| `aurora_internal/aurora_lexical_grounding.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_lexical_structure.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_meaning_evolution.py` | language.3 |  | name_and_docstring |
| `aurora_internal/aurora_semantic_probe_battery.py` | language.1 |  | reviewed |
| `aurora_internal/aurora_specialized_avatar_synthesizer.py` | language.1 |  | name_and_docstring |
| `aurora_internal/aurora_stance_lexicon.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_word_use.py` |  |  | name_and_docstring |
| `aurora_language_field.py` |  |  | name_and_docstring |
| `aurora_language_structure_fitness.py` |  |  | name_and_docstring |
| `aurora_self_grounding.py` |  |  | name_and_docstring |

### Desktop Aurora / Governance, persistence and health

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora_autonomy.py` | governance.1 | L8 | name_and_docstring |
| `aurora_checkpoint.py` | governance.1 | L8 | name_and_docstring |
| `aurora_dev_telemetry.py` | governance.1 |  | name_and_docstring |
| `aurora_governance_persistence_gateway.py` | governance.1 | L8 | name_and_docstring |
| `aurora_internal/aurora_energy_layer_costs.py` | governance.1 |  | name_and_docstring |
| `aurora_internal/aurora_identity_persistence.py` | governance.1 | L8 | name_and_docstring |
| `aurora_internal/aurora_leverage_relief.py` | governance.1 |  | name_and_docstring |
| `aurora_internal/aurora_local_llm_bridge.py` |  |  | reviewed |
| `aurora_internal/aurora_metabolic_clock.py` | governance.1 |  | name_and_docstring |
| `aurora_internal/aurora_metabolic_steps.py` | governance.2 |  | name_and_docstring |
| `aurora_internal/aurora_persistence_audit.py` | governance.1 |  | name_and_docstring |
| `aurora_internal/aurora_persistence_utils.py` | governance.1 |  | name_and_docstring |
| `aurora_internal/aurora_rest_ledger.py` | governance.2 |  | name_and_docstring |
| `aurora_internal/aurora_runtime_constraint_governor.py` | governance.1 |  | name_and_docstring |
| `aurora_internal/aurora_runtime_faults.py` | governance.1 |  | name_and_docstring |
| `aurora_internal/aurora_runtime_health.py` | governance.1 |  | reviewed |
| `aurora_internal/aurora_state_context.py` | governance.1 |  | name_and_docstring |
| `aurora_metabolic_distiller.py` | governance.1 |  | name_and_docstring |
| `aurora_offline_resilience.py` | governance.1 |  | name_and_docstring |
| `aurora_persistence_utils.py` | governance.1 |  | name_and_docstring |
| `aurora_support_stack.py` | governance.1 |  | name_and_docstring |
| `aurora_telemetry.py` | governance.1 |  | name_and_docstring |
| `scripts/autonomous_access.sh` |  |  | location |

### Desktop Aurora / Dual strata (surface and subsurface)

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora_braid_wiring.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_braided_substrate.py` |  | L8 | name_and_docstring |
| `aurora_internal/aurora_surface_dispatcher.py` | strata.2 |  | name_and_docstring |
| `aurora_internal/aurora_surface_doc.py` | strata.2 |  | reviewed |
| `aurora_internal/dual_strata/__init__.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/activation_field.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/cers_bridge.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/cers_deprecation.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/cers_potential_trial.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/cers_regulator.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/cers_tensor_locator.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/conscious_frame.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/contextual_overlay.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/crest.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/dce_bridge.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/downward_traversal.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/lifecycle_catalog.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/micro_reasoning.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/perturbation_probe.py` | strata.1 |  | reviewed |
| `aurora_internal/dual_strata/prediction_field.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/predictive_stager.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/presence_metrics.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/semantic_intention_bridge.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/semantic_variant_registry.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/sensory_control_channel.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/sensory_observation.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/sensory_snapshot_channel.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/sleep_cycle.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/strata_link.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/strata_state_transfer.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/subsurface_presence.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/subsurface_presence_runtime.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/subsurface_projection.py` |  |  | name_and_docstring |
| `aurora_internal/dual_strata/subsurface_state.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/subsystem_waveforms.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/surface_channel.py` |  |  | name_and_docstring |
| `aurora_internal/dual_strata/surface_continuity_feed.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/surface_sensory_proxy.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/topological_semantic_coordinator.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/topology_frame.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/topology_tracker.py` | strata.1 |  | name_and_docstring |
| `aurora_internal/dual_strata/variant_transition_predictor.py` |  |  | name_and_docstring |
| `aurora_scout_daemon.py` | strata.1 |  | name_and_docstring |
| `aurora_subsurface_daemon.py` |  |  | name_and_docstring |
| `aurora_surface_daemon.py` | strata.1 |  | name_and_docstring |
| `scripts/strata_stack.sh` |  |  | location |

### Desktop Aurora / Bridges and external tools

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora_acm_bridge.py` |  |  | name_and_docstring |
| `aurora_desktop_agent.py` | bridges.3 |  | name_and_docstring |
| `aurora_internal/aurora_clone_harvest.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_recommendation_hub.py` |  |  | name_and_docstring |
| `aurora_internal/scouting/__init__.py` |  |  | name_and_docstring |
| `aurora_internal/scouting/backends.py` | bridges.1 |  | name_and_docstring |
| `aurora_internal/scouting/broker.py` | bridges.1 |  | name_and_docstring |
| `aurora_internal/scouting/contracts.py` | bridges.1 |  | name_and_docstring |
| `aurora_internal/scouting/subsurface_scout_bridge.py` | bridges.1 |  | name_and_docstring |
| `aurora_internal/tool_registry.py` | bridges.3 |  | name_and_docstring |
| `aurora_praxis_bridge.py` |  |  | name_and_docstring |
| `aurora_praxis_initiative.py` | bridges.2 |  | name_and_docstring |
| `aurora_praxis_messenger.py` | bridges.2 |  | name_and_docstring |
| `aurora_recommendation_hub.py` |  |  | name_and_docstring |
| `aurora_research_dispatch.py` |  |  | name_and_docstring |
| `aurora_social_corroboration.py` | bridges.2 |  | name_and_docstring |
| `aurora_tool_mind.py` |  |  | name_and_docstring |

### Desktop Aurora / Investigative and diagnostic

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora_build714_resolution_canaries.py` |  |  | name_and_docstring |
| `aurora_causal_vs_representational_probe.py` | investigative.2 |  | name_and_docstring |
| `aurora_diag.py` |  |  | name_and_docstring |
| `aurora_dream_new_experience_canary.py` |  |  | name_and_docstring |
| `aurora_flow_audit.py` |  |  | name_and_docstring |
| `aurora_genealogy_cooccurrence_observatory.py` | investigative.1 |  | name_and_docstring |
| `aurora_genealogy_cooccurrence_observatory_report.py` | investigative.1 |  | name_and_docstring |
| `aurora_genealogy_difference_producer_observatory.py` | investigative.1 |  | name_and_docstring |
| `aurora_genealogy_difference_producer_observatory_report.py` | investigative.1 |  | name_and_docstring |
| `aurora_genealogy_difference_shadow.py` | investigative.3 |  | name_and_docstring |
| `aurora_genealogy_difference_shadow_report.py` | investigative.3 |  | name_and_docstring |
| `aurora_genealogy_environment_shadow.py` |  |  | name_and_docstring |
| `aurora_genealogy_promotion_dimension_shadow.py` |  |  | name_and_docstring |
| `aurora_internal/aurora_boot_parity.py` |  |  | reviewed |
| `aurora_internal/aurora_fault_audit.py` |  |  | reviewed |
| `aurora_internal/aurora_quasiarch_observer.py` | investigative.4 |  | reviewed |
| `aurora_internal/dual_strata/mtsl_acceptance_report.py` |  |  | name_and_docstring |
| `aurora_internal/quasiarch_development_inquiry.py` | investigative.4 |  | reviewed |
| `aurora_internal/quasiarch_observer/dimensional_memory.py` | investigative.5 |  | reviewed |
| `aurora_internal/quasiarch_observer/ghost_relics.py` | investigative.5 |  | reviewed |
| `aurora_learning_probe.py` |  |  | reviewed |
| `aurora_learning_report.py` |  |  | name_and_docstring |
| `aurora_rank6_shadow_analysis.py` | investigative.2 |  | name_and_docstring |
| `aurora_representational_canary.py` |  |  | name_and_docstring |
| `aurora_representational_closed_loop_canary.py` |  |  | name_and_docstring |
| `aurora_representational_cross_system_canary.py` |  |  | name_and_docstring |
| `aurora_representational_divergence_canaries.py` |  |  | name_and_docstring |
| `aurora_representational_emergence_observatory.py` |  |  | name_and_docstring |
| `aurora_same_input_history_canary.py` |  |  | name_and_docstring |
| `conftest.py` |  |  | reviewed |
| `run_full_competency_gauntlet.py` |  |  | reviewed |
| `run_gauntlet.py` |  |  | reviewed |
| `run_probe_battery.py` |  |  | reviewed |
| `scripts/reset_quasiarch_observer_state.sh` |  |  | location |
| `test_constraint_reasoner.py` |  |  | name_and_docstring |

### Desktop Aurora / Tests

| File | Composite | Layer | Basis |
|---|---|---|---|
| `tests/_engine_integration_test.py` |  |  | location |
| `tests/_pipeline_test.py` |  |  | location |
| `tests/run_intelligence_test_surface.py` |  |  | location |
| `tests/run_interaction_test.py` |  |  | location |
| `tests/test_ability_ancestral_provenance.py` |  |  | location |
| `tests/test_ability_origin_commit_pull.py` |  |  | location |
| `tests/test_abstention_rescue_retry.py` |  |  | location |
| `tests/test_acquisition_observation_framing_and_synthesis_validity.py` |  |  | location |
| `tests/test_afterthought_topic_identity_and_shard_collision_live.py` |  |  | location |
| `tests/test_afterthought_topic_identity_and_shard_collision_repair.py` |  |  | location |
| `tests/test_alignment.py` |  |  | location |
| `tests/test_ambient_audio_feature_handoff.py` |  |  | location |
| `tests/test_ambient_audio_raw_pcm_features.py` |  |  | location |
| `tests/test_ambient_visual_richer_features.py` |  |  | location |
| `tests/test_android_surface_subsurface_reconnection.py` |  |  | location |
| `tests/test_app_bridge_praxis.py` |  |  | location |
| `tests/test_articulation_semantic_strategy.py` |  |  | location |
| `tests/test_asked_thing_and_manner.py` |  |  | location |
| `tests/test_aurora_evolution_hook_equivalence.py` |  |  | location |
| `tests/test_aurora_habitat.py` |  |  | location |
| `tests/test_autoevolver_syntax_gate.py` |  |  | location |
| `tests/test_b1_1_envelope_shadow.py` |  |  | location |
| `tests/test_baseline_communication_apprenticeship.py` |  |  | location |
| `tests/test_baseline_genealogy.py` |  |  | location |
| `tests/test_battery_relevance_metric.py` |  |  | location |
| `tests/test_boundary_hypothesis_and_vocative_stripping.py` |  |  | location |
| `tests/test_boundary_surface_and_study_trace_regressions.py` |  |  | location |
| `tests/test_bounded_same_turn_evidence_wait.py` |  |  | location |
| `tests/test_bracket_tokens_not_words.py` |  |  | location |
| `tests/test_build694_instrumentation.py` |  |  | location |
| `tests/test_build694_required_regression.py` |  |  | location |
| `tests/test_build711_no_external_models.py` |  |  | location |
| `tests/test_build714_resolution_canaries.py` |  |  | location |
| `tests/test_build725_native_semantic_externalization.py` |  |  | location |
| `tests/test_build922_permanent_recognition.py` |  |  | location |
| `tests/test_canonical_noncomp_dimension.py` |  |  | location |
| `tests/test_capability_binding.py` |  |  | location |
| `tests/test_categorical_condition_search_admissibility.py` |  |  | location |
| `tests/test_causal_generation_acceptance.py` |  |  | location |
| `tests/test_causal_generation_batch_order.py` |  |  | location |
| `tests/test_causal_generation_daemon_concurrency.py` |  |  | location |
| `tests/test_causal_generation_daemon_concurrency_part2.py` |  |  | location |
| `tests/test_causal_generation_duplicate_target_audit.py` |  |  | location |
| `tests/test_causal_generation_infrastructure.py` |  |  | location |
| `tests/test_cers_bridge_tensor_trace_integration.py` |  |  | location |
| `tests/test_cers_conflict_monitoring_veto.py` |  |  | location |
| `tests/test_cers_geometry_deviation.py` |  |  | location |
| `tests/test_cers_shadow_error_logging.py` |  |  | location |
| `tests/test_cers_surface_salience.py` |  |  | location |
| `tests/test_cers_tensor_locator.py` |  |  | location |
| `tests/test_cers_topology_context.py` |  |  | location |
| `tests/test_ci_segment_dev_index_rolling_cap.py` |  |  | location |
| `tests/test_cir_wh_object_slot_guard.py` |  |  | location |
| `tests/test_classroom_behavior_modes_wiring.py` |  |  | location |
| `tests/test_classroom_curriculum_seeding.py` |  |  | location |
| `tests/test_classroom_divergence_cold_start.py` |  |  | location |
| `tests/test_classroom_perspective_rotation_and_watchdog.py` |  |  | location |
| `tests/test_clock_restart_accounting.py` |  |  | location |
| `tests/test_clone_harvest.py` |  |  | location |
| `tests/test_code_evolution_restart_heredity.py` |  |  | location |
| `tests/test_cognitive_experience_causal_evaluator.py` |  |  | location |
| `tests/test_cognitive_experience_counterfactual_transfer.py` |  |  | location |
| `tests/test_cognitive_experience_episode_loop.py` |  |  | location |
| `tests/test_cognitive_experience_expression_fidelity.py` |  |  | location |
| `tests/test_cognitive_experience_promotion_bridge.py` |  |  | location |
| `tests/test_cognitive_experience_world_substrate.py` |  |  | location |
| `tests/test_cognitive_stats_telemetry_contract.py` |  |  | location |
| `tests/test_comm_credit_phase0_dead_wiring.py` |  |  | location |
| `tests/test_comm_credit_phase_e_foundations.py` |  |  | location |
| `tests/test_comm_credit_phase_f_core_functions.py` |  |  | location |
| `tests/test_comm_credit_phase_g_live_wiring.py` |  |  | location |
| `tests/test_comm_credit_phase_h_corpus_bridge.py` |  |  | location |
| `tests/test_communication_architecture_repair_directive.py` |  |  | location |
| `tests/test_communication_bar.py` | tests.1 |  | location |
| `tests/test_communication_credit_unification.py` |  |  | location |
| `tests/test_communication_emergence.py` | tests.1 |  | location |
| `tests/test_communication_integrity_repair.py` |  |  | location |
| `tests/test_composer_relevance_selection.py` |  |  | location |
| `tests/test_compressed_genealogy_state.py` |  |  | location |
| `tests/test_concept_image_ingestion_import.py` |  |  | location |
| `tests/test_concept_imager_cycle.py` |  |  | location |
| `tests/test_confluence.py` | tests.2 |  | location |
| `tests/test_consequence_profile_does_not_govern_perception.py` |  |  | location |
| `tests/test_constraint_continuity_across_mutation.py` |  |  | location |
| `tests/test_constraint_field_constitutive_behavior.py` |  |  | location |
| `tests/test_constraint_manifold_prerequisites.py` |  |  | location |
| `tests/test_constraint_semantic_continuity.py` |  |  | location |
| `tests/test_conversation_desktop.py` |  |  | location |
| `tests/test_core_understanding.py` |  |  | location |
| `tests/test_correspondence_loop.py` |  |  | location |
| `tests/test_cpm.py` |  |  | location |
| `tests/test_crest_compression_placeholder_guard.py` |  |  | location |
| `tests/test_cross_generational_representational_recombination.py` |  |  | location |
| `tests/test_crystal_associations.py` |  |  | location |
| `tests/test_crystal_convergence.py` |  |  | location |
| `tests/test_crystal_evidence_evolution.py` |  |  | location |
| `tests/test_crystal_facets.py` |  |  | location |
| `tests/test_crystal_grammar.py` |  |  | location |
| `tests/test_crystal_interior.py` |  |  | location |
| `tests/test_crystal_lexicon.py` |  |  | location |
| `tests/test_crystal_maturity.py` |  |  | location |
| `tests/test_crystal_promotion.py` |  |  | location |
| `tests/test_crystal_runtime.py` |  |  | location |
| `tests/test_crystal_sensory.py` |  |  | location |
| `tests/test_crystal_store.py` |  |  | location |
| `tests/test_crystal_substitutability.py` |  |  | location |
| `tests/test_crystal_unification.py` |  |  | location |
| `tests/test_crystal_waveform_match.py` |  |  | location |
| `tests/test_crystal_weave.py` |  |  | location |
| `tests/test_d1_device_path_attribution.py` |  |  | location |
| `tests/test_d2_2_corpus_fragment_nesting.py` |  |  | location |
| `tests/test_d2_2_live_turn_reentrancy_guard.py` |  |  | location |
| `tests/test_d2_3_delivery_boundary_telemetry_rejection.py` |  |  | location |
| `tests/test_d2_4_probe_battery_measures_resp_a.py` |  |  | location |
| `tests/test_d2_condition2_abstain_sanity.py` |  |  | location |
| `tests/test_daemon_classroom_cycle.py` |  |  | location |
| `tests/test_daemon_evidence_grounded_mutation.py` |  |  | location |
| `tests/test_daemon_subsurface_and_ambient.py` |  |  | location |
| `tests/test_der_geometric_time.py` |  |  | location |
| `tests/test_desktop_stack_includes_scout_worker.py` |  |  | location |
| `tests/test_development_experiment.py` |  |  | location |
| `tests/test_developmental_ecology_boundary.py` |  |  | location |
| `tests/test_developmental_integration_closure.py` |  |  | location |
| `tests/test_developmental_reachability_canaries.py` |  |  | location |
| `tests/test_direct_address_formulation.py` |  |  | location |
| `tests/test_directed_training_corpus_cache_trust.py` |  |  | location |
| `tests/test_dmm_thought_intent_derivation.py` |  |  | location |
| `tests/test_downward_cascade_memory.py` |  |  | location |
| `tests/test_dream_agency.py` |  |  | location |
| `tests/test_dream_ancestry.py` |  |  | location |
| `tests/test_dream_as_new_experience.py` |  |  | location |
| `tests/test_dream_developmental_writeback.py` |  |  | location |
| `tests/test_dream_evolution_boundary.py` |  |  | location |
| `tests/test_dream_salience_abstraction.py` |  |  | location |
| `tests/test_dream_source_abstraction.py` |  |  | location |
| `tests/test_dream_trainer_genealogy_wiring.py` |  |  | location |
| `tests/test_dual_clock_starvation_preemption.py` |  |  | location |
| `tests/test_emergence_pathway_repairs.py` |  |  | location |
| `tests/test_emitter_crash.py` |  |  | location |
| `tests/test_entropy_reads_the_stimulus.py` |  |  | location |
| `tests/test_episode_to_entity_experience.py` |  |  | location |
| `tests/test_evidence_axes.py` |  |  | location |
| `tests/test_evidence_binding_request_kind_aware.py` |  |  | location |
| `tests/test_evidence_input_impact.py` |  |  | location |
| `tests/test_evidence_journal.py` |  |  | location |
| `tests/test_evidence_overheard.py` |  |  | location |
| `tests/test_evidence_pressure_shape.py` |  |  | location |
| `tests/test_evidence_qualification.py` |  |  | location |
| `tests/test_evidence_substrate_boundary.py` |  |  | location |
| `tests/test_evidence_view.py` |  |  | location |
| `tests/test_evolution_chamber_live_driveshaft.py` |  |  | location |
| `tests/test_evolution_hook_override_none_handling.py` |  |  | location |
| `tests/test_evolutionary_ancestry_acquisition.py` |  |  | location |
| `tests/test_f5_register_exploration_plumbing.py` |  |  | location |
| `tests/test_fail_recurrence_novelty.py` |  |  | location |
| `tests/test_failure_shape_tracing.py` |  |  | location |
| `tests/test_fault_instrumentation_injector.py` |  |  | location |
| `tests/test_field_balancer_genealogy_type_repair.py` |  |  | location |
| `tests/test_flow_audit_and_tcl_wiring.py` |  |  | location |
| `tests/test_frame_negated_auxiliary.py` |  |  | location |
| `tests/test_full_reasoning_pipeline.py` |  |  | location |
| `tests/test_function_word_gate_golden.py` |  |  | location |
| `tests/test_genealogy_activity_registry.py` |  |  | location |
| `tests/test_genealogy_atomic_writes.py` |  |  | location |
| `tests/test_genealogy_consequence_profile.py` |  |  | location |
| `tests/test_genealogy_cooccurrence_observatory.py` |  |  | location |
| `tests/test_genealogy_curve_persistence.py` |  |  | location |
| `tests/test_genealogy_difference_producer_observatory.py` |  |  | location |
| `tests/test_genealogy_difference_shadow.py` |  |  | location |
| `tests/test_genealogy_environment_dag_preservation.py` |  |  | location |
| `tests/test_genealogy_is_event_generated.py` |  |  | location |
| `tests/test_genealogy_operational_integrity.py` |  |  | location |
| `tests/test_genealogy_positive_selection.py` |  |  | location |
| `tests/test_genealogy_processing_reuse.py` |  |  | location |
| `tests/test_genealogy_promotion_dimension_observer.py` |  |  | location |
| `tests/test_genealogy_same_event_correlation.py` |  |  | location |
| `tests/test_genealogy_scale_and_orientation.py` |  |  | location |
| `tests/test_genealogy_source_freshness.py` |  |  | location |
| `tests/test_genealogy_tag_scan_equivalence.py` |  |  | location |
| `tests/test_general_execution_foundry.py` |  |  | location |
| `tests/test_generation_collapse_regression.py` |  |  | location |
| `tests/test_geological_write.py` |  |  | location |
| `tests/test_golden_transcript_validation.py` |  |  | location |
| `tests/test_governance_liveness.py` |  |  | location |
| `tests/test_governor_and_allocation.py` |  |  | location |
| `tests/test_grammar_motif_depletion_check.py` |  |  | location |
| `tests/test_habitat_compressed_motivation_state.py` |  |  | location |
| `tests/test_habitat_discovery_canary_build717.py` |  |  | location |
| `tests/test_habitat_motivation_build717.py` |  |  | location |
| `tests/test_habitat_self_and_shared_canaries_build717.py` |  |  | location |
| `tests/test_heard_vs_produced_learning.py` |  |  | location |
| `tests/test_hereditary_closure.py` |  |  | location |
| `tests/test_historical_experience_compressed_state.py` |  |  | location |
| `tests/test_historical_experience_environment.py` |  |  | location |
| `tests/test_historical_lexical_consequence_attribution.py` |  |  | location |
| `tests/test_historical_rehearsal.py` |  |  | location |
| `tests/test_hypothesis_crystals.py` |  |  | location |
| `tests/test_i_state_channel_reweighting.py` |  |  | location |
| `tests/test_i_state_occurrence_wavefront.py` |  |  | location |
| `tests/test_icc_ledger.py` |  |  | location |
| `tests/test_identity_and_asked_predicate.py` |  |  | location |
| `tests/test_identity_field_internal_signals.py` |  |  | location |
| `tests/test_ifelse_synthesis_primitive.py` |  |  | location |
| `tests/test_input_as_pressure.py` |  |  | location |
| `tests/test_input_effect_shadow.py` |  |  | location |
| `tests/test_input_identity.py` |  |  | location |
| `tests/test_interaction_event_action_handoff.py` |  |  | location |
| `tests/test_internal_origin_exempt.py` |  |  | location |
| `tests/test_interpreted_turn_packet.py` |  |  | location |
| `tests/test_interpreted_turn_scout_boundary.py` |  |  | location |
| `tests/test_irreducibility.py` |  |  | location |
| `tests/test_ivm_lattice_live_driveshaft.py` |  |  | location |
| `tests/test_l1_skeleton_validity_gate.py` |  |  | location |
| `tests/test_l2_pos_gating.py` |  |  | location |
| `tests/test_l3_conjugation_wiring.py` |  |  | location |
| `tests/test_l3b_determiner_preposition_slots.py` |  |  | location |
| `tests/test_l4_grounded_motif_fitness.py` |  |  | location |
| `tests/test_layer_acyclicity.py` |  |  | location |
| `tests/test_layer_module_ownership_categories.py` |  |  | location |
| `tests/test_learned_order_rules.py` |  |  | location |
| `tests/test_learning_probe.py` |  |  | location |
| `tests/test_lesson_replay.py` |  |  | location |
| `tests/test_lexical_structure.py` |  |  | location |
| `tests/test_lexical_waveform_trials.py` |  |  | location |
| `tests/test_lifecycle_catalog.py` |  |  | location |
| `tests/test_lineage_runtime_activation.py` |  |  | location |
| `tests/test_lineage_scoped_pressure.py` |  |  | location |
| `tests/test_live_axis_magnitudes.py` |  |  | location |
| `tests/test_live_communicative_baseline.py` |  |  | location |
| `tests/test_live_possibility_frontier.py` |  |  | location |
| `tests/test_live_possibility_isolation.py` |  |  | location |
| `tests/test_live_possibility_king_authority.py` |  |  | location |
| `tests/test_live_turn_parse_cache.py` |  |  | location |
| `tests/test_live_turn_smoke.py` |  |  | location |
| `tests/test_low_fail_positive_gap_fill.py` |  |  | location |
| `tests/test_m1_1a_relation_pairs.py` |  |  | location |
| `tests/test_m1_2_provenance_hygiene.py` |  |  | location |
| `tests/test_manifold_depth_score_reuse.py` |  |  | location |
| `tests/test_metabolic_clock.py` |  |  | location |
| `tests/test_metabolic_steps.py` |  |  | location |
| `tests/test_mobile_developmental_health_surface.py` |  |  | location |
| `tests/test_mobile_presence_runtime_startup.py` |  |  | location |
| `tests/test_mobile_scout_worker_startup.py` |  |  | location |
| `tests/test_mobile_tools_aurora.py` |  |  | location |
| `tests/test_modulation_event_representational_ref.py` |  |  | location |
| `tests/test_mtsl_acceptance_report.py` |  |  | location |
| `tests/test_mtsl_live_wiring.py` |  |  | location |
| `tests/test_mtsl_perturbation_live_wiring.py` |  |  | location |
| `tests/test_mtsl_phase0_plumbing.py` |  |  | location |
| `tests/test_mtsl_phase7_extensions.py` |  |  | location |
| `tests/test_mtsl_warp_gap_proposal.py` |  |  | location |
| `tests/test_multi_sentence_claim_boundary_and_input_echo_live.py` |  |  | location |
| `tests/test_multi_sentence_claim_boundary_and_input_echo_repair.py` |  |  | location |
| `tests/test_n21_hardened_reacceptance.py` |  |  | location |
| `tests/test_n3_correspondence_daemon_wiring.py` |  |  | location |
| `tests/test_native_intermediate_resolution_audit.py` |  |  | location |
| `tests/test_native_motivation_binding_build723.py` |  |  | location |
| `tests/test_native_representational_inquiry_experimentation.py` |  |  | location |
| `tests/test_native_representational_selection.py` |  |  | location |
| `tests/test_native_surface_projection_scope_reconciliation.py` |  |  | location |
| `tests/test_nc1_noncomp_population.py` |  |  | location |
| `tests/test_nc2_strengthen_cascade.py` |  |  | location |
| `tests/test_no_artificial_fail_generation.py` |  |  | location |
| `tests/test_no_hardcoded_evolutionary_answer_key.py` |  |  | location |
| `tests/test_no_representational_selection_learning.py` |  |  | location |
| `tests/test_no_speculative_d3.py` |  |  | location |
| `tests/test_oets.py` |  |  | location |
| `tests/test_oets_comprehension_confidence_growth.py` |  |  | location |
| `tests/test_oets_conf.py` |  |  | location |
| `tests/test_one_reading_one_observation.py` |  |  | location |
| `tests/test_one_speech_path.py` |  |  | location |
| `tests/test_operation_level_mutation_identity.py` |  |  | location |
| `tests/test_operational_synthesis_chamber.py` |  |  | location |
| `tests/test_operator_composer.py` |  |  | location |
| `tests/test_orientation_reaches_selector.py` |  |  | location |
| `tests/test_p1_st2_stance_lexicon.py` |  |  | location |
| `tests/test_p1_track_cp_contradiction.py` |  |  | location |
| `tests/test_p2_1_density_confidence.py` |  |  | location |
| `tests/test_p2_2_density_stance_blend.py` |  |  | location |
| `tests/test_p2_3_stance_composer_wiring.py` |  |  | location |
| `tests/test_perception_evolution_boundary.py` |  |  | location |
| `tests/test_perspective_before_resolution.py` |  |  | location |
| `tests/test_perspective_live_birth.py` |  |  | location |
| `tests/test_perspective_representation_birth.py` |  |  | location |
| `tests/test_perturbation_probe.py` |  |  | location |
| `tests/test_pf1_1_proposition_frame.py` |  |  | location |
| `tests/test_pf1_2_transport.py` |  |  | location |
| `tests/test_pf1_3_motif_selection.py` |  |  | location |
| `tests/test_pf1_4_slot_binding.py` |  |  | location |
| `tests/test_pf1_5_instruments.py` |  |  | location |
| `tests/test_pf3_1_carryover_isolation.py` |  |  | location |
| `tests/test_pf3_1_cooccurrence_hub_leak.py` |  |  | location |
| `tests/test_pf3_1_frame_staleness.py` |  |  | location |
| `tests/test_pf3_2_pronoun_consumer_split.py` |  |  | location |
| `tests/test_pf3_3_descriptor_neighborhood.py` |  |  | location |
| `tests/test_pf3_3_frame_absence.py` |  |  | location |
| `tests/test_pf3_4a_motif_thinning_guard.py` |  |  | location |
| `tests/test_pf3_5_motif_watch_readout.py` |  |  | location |
| `tests/test_phone_load_pacing.py` |  |  | location |
| `tests/test_pipeline2.py` |  |  | location |
| `tests/test_positive_dream_material.py` |  |  | location |
| `tests/test_praxis_contract_fence.py` |  |  | location |
| `tests/test_praxis_initiative.py` |  |  | location |
| `tests/test_praxis_messenger.py` |  |  | location |
| `tests/test_praxis_physics_routing.py` |  |  | location |
| `tests/test_praxis_same_device_loop.py` |  |  | location |
| `tests/test_prediction_field_manifold.py` |  |  | location |
| `tests/test_preoutcome_pressure_capture.py` |  |  | location |
| `tests/test_presence_metrics.py` |  |  | location |
| `tests/test_presence_runtime_occurrence_barrier.py` |  |  | location |
| `tests/test_pressure_ledger_restart_continuity.py` |  |  | location |
| `tests/test_primitive_perspective.py` |  |  | location |
| `tests/test_produced_ingest_not_heard.py` |  |  | location |
| `tests/test_progressive_perspective_consumption.py` |  |  | location |
| `tests/test_projection_frontier_consumption.py` |  |  | location |
| `tests/test_promotion_lookup_scaling.py` |  |  | location |
| `tests/test_propositional_understanding.py` | tests.2 |  | location |
| `tests/test_provenance_integrity.py` |  |  | location |
| `tests/test_prune_recall_marker_nodes.py` |  |  | location |
| `tests/test_ps1_2_persistence_arbitration.py` |  |  | location |
| `tests/test_qualified_promotion.py` |  |  | location |
| `tests/test_quasiarch_development_inquiry.py` |  |  | location |
| `tests/test_rank6_falsification.py` |  |  | location |
| `tests/test_rcec_closed_loop_orchestrator.py` |  |  | location |
| `tests/test_rcec_mechanism_coherence_and_ingestion.py` |  |  | location |
| `tests/test_rcec_state_isolation_and_lifecycle.py` |  |  | location |
| `tests/test_reasoning_paths.py` |  |  | location |
| `tests/test_recall_markers_not_words.py` |  |  | location |
| `tests/test_recall_no_stored_utterance.py` |  |  | location |
| `tests/test_receiver_loop.py` |  |  | location |
| `tests/test_recommendation_hub_incremental.py` |  |  | location |
| `tests/test_recurring_issue_scout_dispatch.py` |  |  | location |
| `tests/test_recursive_causal_reasoning_waveform.py` |  |  | location |
| `tests/test_reflective_introspection_misrouting_live.py` |  |  | location |
| `tests/test_reflective_introspection_misrouting_repair.py` |  |  | location |
| `tests/test_reflective_readdressing.py` |  |  | location |
| `tests/test_reflexive_interpreter_deposition_integration.py` |  |  | location |
| `tests/test_reflexive_interpreter_sedimemory_boot_wiring.py` |  |  | location |
| `tests/test_reflexive_interpreter_slotcoord_derivation.py` |  |  | location |
| `tests/test_rehearsal_both_positions.py` |  |  | location |
| `tests/test_rehearsal_demonstration.py` |  |  | location |
| `tests/test_rehearsal_every_comparison_teaches.py` |  |  | location |
| `tests/test_relation_typing_probe_extension.py` |  |  | location |
| `tests/test_relational_promotion_jurisdiction_repair.py` |  |  | location |
| `tests/test_representation_adoption.py` |  |  | location |
| `tests/test_representation_crystals.py` |  |  | location |
| `tests/test_representation_exchange.py` |  |  | location |
| `tests/test_representation_index_change_aware.py` |  |  | location |
| `tests/test_representation_inquiry_causal_integrity.py` |  |  | location |
| `tests/test_representational_addressability.py` |  |  | location |
| `tests/test_representational_canary.py` |  |  | location |
| `tests/test_representational_consequence_binding.py` |  |  | location |
| `tests/test_representational_conservation_negative_guards.py` |  |  | location |
| `tests/test_representational_consumer_audit_build717.py` |  |  | location |
| `tests/test_representational_cross_system_integration.py` |  |  | location |
| `tests/test_representational_divergence_canaries.py` |  |  | location |
| `tests/test_representational_emergence_observatory.py` |  |  | location |
| `tests/test_representational_existence_gate.py` |  |  | location |
| `tests/test_representational_form_gating.py` |  |  | location |
| `tests/test_representational_inquiry_lifecycle_repairs.py` |  |  | location |
| `tests/test_representational_live_propagation.py` |  |  | location |
| `tests/test_representational_persistence.py` |  |  | location |
| `tests/test_representational_resolution_build714.py` |  |  | location |
| `tests/test_representational_restart_replay.py` |  |  | location |
| `tests/test_representational_unresolved_fields.py` |  |  | location |
| `tests/test_resolution_ledger.py` |  |  | location |
| `tests/test_response_articulation_authority.py` |  |  | location |
| `tests/test_response_fit_automatic_dispatch.py` |  |  | location |
| `tests/test_response_fit_graduation.py` |  |  | location |
| `tests/test_response_fit_scout_requires_interpretation.py` |  |  | location |
| `tests/test_response_formation_consumes_scout_evidence.py` |  |  | location |
| `tests/test_rest_accounting_properties.py` |  |  | location |
| `tests/test_rest_ledger.py` |  |  | location |
| `tests/test_retained_learning_bank_strategy_filter.py` |  |  | location |
| `tests/test_rich_fail_stream.py` |  |  | location |
| `tests/test_round.py` |  |  | location |
| `tests/test_runtime_fault_lived_consequence.py` |  |  | location |
| `tests/test_runtime_hardening.py` |  |  | location |
| `tests/test_runtime_lineage_connection.py` |  |  | location |
| `tests/test_rw3_quasiarch_consult_loop.py` |  |  | location |
| `tests/test_rw4_relation_to_self.py` |  |  | location |
| `tests/test_rw5_boot_parity.py` |  |  | location |
| `tests/test_rw6c_track1_wiring.py` |  |  | location |
| `tests/test_rw7_attribution_trace.py` |  |  | location |
| `tests/test_same_name_cross_module_independence.py` |  |  | location |
| `tests/test_scaffolding_not_heard.py` |  |  | location |
| `tests/test_scheduled_run_state_persistence.py` |  |  | location |
| `tests/test_scheduler_balance.py` |  |  | location |
| `tests/test_scout_backends.py` |  |  | location |
| `tests/test_scout_broker.py` |  |  | location |
| `tests/test_scout_contracts.py` |  |  | location |
| `tests/test_scout_evidence_early_ingestion.py` |  |  | location |
| `tests/test_scout_never_writes_cognitive_state.py` |  |  | location |
| `tests/test_scout_presence_load_comparison.py` |  |  | location |
| `tests/test_scout_report_routes_only_to_subsurface.py` |  |  | location |
| `tests/test_scout_resource_budget.py` |  |  | location |
| `tests/test_scout_worker.py` |  |  | location |
| `tests/test_sedimemory_d2_625.py` |  |  | location |
| `tests/test_sedimemory_representational_ref.py` |  |  | location |
| `tests/test_semantic_bridge_live_state.py` |  |  | location |
| `tests/test_semantic_intention_bridge.py` |  |  | location |
| `tests/test_semantic_probe_battery.py` |  |  | location |
| `tests/test_semantic_variant_registry.py` |  |  | location |
| `tests/test_sender_agency.py` |  |  | location |
| `tests/test_sensory_citizenship_followup.py` |  |  | location |
| `tests/test_sensory_consequence_circuit_repairs.py` |  |  | location |
| `tests/test_sensory_genealogy_and_evolution_wiring.py` |  |  | location |
| `tests/test_sensory_learned_axis_participation.py` |  |  | location |
| `tests/test_sensory_representational_citizenship.py` |  |  | location |
| `tests/test_shadow_state_utility.py` |  |  | location |
| `tests/test_social_corroboration.py` |  |  | location |
| `tests/test_stale_scout_report_cannot_hijack_new_turn.py` |  |  | location |
| `tests/test_stimulus_pressure_seams.py` |  |  | location |
| `tests/test_strata_link.py` |  |  | location |
| `tests/test_strata_state_transfer.py` |  |  | location |
| `tests/test_strategic_horizon.py` |  |  | location |
| `tests/test_stratified_wellformedness.py` |  |  | location |
| `tests/test_subsurface_live_presence.py` |  |  | location |
| `tests/test_subsurface_presence_during_scout_delay.py` |  |  | location |
| `tests/test_subsurface_presence_runtime.py` |  |  | location |
| `tests/test_subsurface_presence_wiring.py` |  |  | location |
| `tests/test_subsurface_scout_bridge.py` |  |  | location |
| `tests/test_supposed_stays_supposed.py` |  |  | location |
| `tests/test_surface_boundary.py` |  |  | location |
| `tests/test_surface_does_not_wait_for_scout.py` |  |  | location |
| `tests/test_surface_poedex_dispatch.py` |  |  | location |
| `tests/test_surface_scout_evidence_harvest.py` |  |  | location |
| `tests/test_system_introspection_bridge.py` |  |  | location |
| `tests/test_tensor_downward_modulation.py` |  |  | location |
| `tests/test_thought_downward.py` |  |  | location |
| `tests/test_topological_semantic_coordinator.py` |  |  | location |
| `tests/test_topology_cycle_decomposition.py` |  |  | location |
| `tests/test_topology_frame.py` |  |  | location |
| `tests/test_topology_tracker.py` |  |  | location |
| `tests/test_toroidal_circulation_layer.py` |  |  | location |
| `tests/test_turn_compute_graph.py` |  |  | location |
| `tests/test_turn_write_behind.py` |  |  | location |
| `tests/test_ui_observation_journal.py` |  |  | location |
| `tests/test_understanding_genealogy_preservation.py` |  |  | location |
| `tests/test_understanding_sediment_overlay.py` |  |  | location |
| `tests/test_unformed_patterns.py` |  |  | location |
| `tests/test_universal_function_lineage.py` |  |  | location |
| `tests/test_universal_function_lineage_freshness_fast_path.py` |  |  | location |
| `tests/test_unknown_provenance.py` |  |  | location |
| `tests/test_up.py` |  |  | location |
| `tests/test_variant_transition_predictor.py` |  |  | location |
| `tests/test_verify_lesson.py` |  |  | location |
| `tests/test_voice_gate.py` |  |  | location |
| `tests/test_w1_turn_content_context.py` |  |  | location |
| `tests/test_w2_claim_gate_widening.py` |  |  | location |
| `tests/test_warp_phase1_resonance_graph.py` |  |  | location |
| `tests/test_warp_phase2_confession_calls.py` |  |  | location |
| `tests/test_warp_phase3a_language_field_confession.py` |  |  | location |
| `tests/test_warp_phase3b_resonant_lookup_confession.py` |  |  | location |
| `tests/test_warp_phase3c_memory_recall_confession.py` |  |  | location |
| `tests/test_warp_phase3d_parse_confidence_confession.py` |  |  | location |
| `tests/test_warp_phase4_resonant_trial_lifecycle.py` |  |  | location |
| `tests/test_waveform_pressure.py` |  |  | location |
| `tests/test_word_use.py` |  |  | location |
| `tests/test_zip_active_turn_state_frame_source.py` |  |  | location |
| `tests/test_zip_directed_training_fitness_gate.py` |  |  | location |
| `tests/test_zip_gap_research_router.py` |  |  | location |
| `tests/test_zip_integration_b_standalone_fixes.py` |  |  | location |
| `tests/test_zip_pipeline_learning_oets_promotion.py` |  |  | location |
| `tests/test_zip_semantic_intention_reset.py` |  |  | location |

### Desktop Aurora / Scripts, tooling and prototypes

| File | Composite | Layer | Basis |
|---|---|---|---|
| `constraint_prototype.html` |  |  | location |
| `constraint_prototype.jsx` |  |  | location |
| `reply_aurora.py` |  |  | reviewed |
| `scripts/analyze_cross_generational_representations.py` |  |  | location |
| `scripts/analyze_native_representation_inquiries.py` |  |  | location |
| `scripts/append_to_doc.py` |  |  | location |
| `scripts/apply_vocabulary_seed.py` |  |  | location |
| `scripts/audit_actual_runtime_turn.py` |  |  | location |
| `scripts/audit_genealogy.py` |  |  | location |
| `scripts/audit_unified_response_regression.py` |  |  | location |
| `scripts/aurora_ci_segment.py` |  |  | location |
| `scripts/aurora_cold_archive.py` |  |  | location |
| `scripts/aurora_fault_instrumentation_injector.py` |  |  | location |
| `scripts/aurora_stack_exporter.py` |  |  | location |
| `scripts/aurora_state_compress.py` |  |  | location |
| `scripts/backfill_noncomp_and_relations.py` |  |  | location |
| `scripts/baseline_genealogy.py` |  |  | location |
| `scripts/bridge_ledger_to_noncomps.py` |  |  | location |
| `scripts/bridge_tensor_occupancy_to_warp.py` |  |  | location |
| `scripts/chain_dossier_codec.py` |  |  | location |
| `scripts/characterize_pf16_residue.py` |  |  | location |
| `scripts/chat_daemon.py` |  |  | location |
| `scripts/chatscriber.py` |  |  | location |
| `scripts/clean_corpus.py` |  |  | location |
| `scripts/compare_architectures.py` |  |  | location |
| `scripts/compare_genealogy_equivalence.py` |  |  | location |
| `scripts/compile_universal_function_lineage.py` |  |  | location |
| `scripts/generate_nc_lineage_docs.py` |  |  | location |
| `scripts/greeting_exposure_experiment.py` |  |  | location |
| `scripts/inject_math_forms_v2.py` |  |  | location |
| `scripts/m1_1a_tier1_backfill.py` |  |  | location |
| `scripts/m1_2_provenance_hygiene.py` |  |  | location |
| `scripts/m1_3_v0_rerun.py` |  |  | location |
| `scripts/map_turn_information_flow.py` |  |  | location |
| `scripts/measure_crystal_associations.py` |  |  | location |
| `scripts/measure_crystal_convergence.py` |  |  | location |
| `scripts/measure_crystal_facets.py` |  |  | location |
| `scripts/measure_crystal_grammar.py` |  |  | location |
| `scripts/measure_crystal_maturity.py` |  |  | location |
| `scripts/measure_crystal_promotion.py` |  |  | location |
| `scripts/measure_crystal_substitutability.py` |  |  | location |
| `scripts/measure_crystal_weave.py` |  |  | location |
| `scripts/measure_dream_ancestry.py` |  |  | location |
| `scripts/measure_evidence_journal.py` |  |  | location |
| `scripts/measure_input_attribution.py` |  |  | location |
| `scripts/measure_input_impact.py` |  |  | location |
| `scripts/measure_quasiarch_inquiry.py` |  |  | location |
| `scripts/measure_stream_provenance.py` |  |  | location |
| `scripts/measure_turn_baseline.py` |  |  | location |
| `scripts/noncomp_actuation_shadow_audit.py` |  |  | location |
| `scripts/pf1_0_attribution_run.py` |  |  | location |
| `scripts/pf1_5_instrument_revalidation.py` |  |  | location |
| `scripts/pf1_6_acceptance.py` |  |  | location |
| `scripts/pf3_1_carryover_trace.py` |  |  | location |
| `scripts/pf3_1_context_keywords_trace.py` |  |  | location |
| `scripts/pf3_1_frame_staleness_trace.py` |  |  | location |
| `scripts/pf3_3_descriptor_trace.py` |  |  | location |
| `scripts/pf3_3_frame_absence_trace.py` |  |  | location |
| `scripts/pf3_5_motif_watch_readout.py` |  |  | location |
| `scripts/populate_fgae_semantics.py` |  |  | location |
| `scripts/process_docs.py` |  |  | location |
| `scripts/prove_learning.py` |  |  | location |
| `scripts/prune_recall_marker_nodes.py` |  |  | location |
| `scripts/rcec_canary_cohort.py` |  |  | location |
| `scripts/rcec_canary_cohort_610.py` |  |  | location |
| `scripts/rcec_canary_reduced_613.py` |  |  | location |
| `scripts/render_module_ownership.py` |  |  | location |
| `scripts/repair_stale_priority_depth.py` |  |  | location |
| `scripts/resolution_ledger_replay.py` |  |  | location |
| `scripts/run_growth_session.py` |  |  | location |
| `scripts/rw7_attribution_run.py` |  |  | location |
| `scripts/scan_lineage_25x25.py` |  |  | location |
| `scripts/scout_presence_load_comparison.py` |  |  | location |
| `scripts/seed_abstract_regions_s1.py` |  |  | location |
| `scripts/seed_oets_aurora_vocabulary.py` |  |  | location |
| `scripts/seed_sensory_crystals.py` |  |  | location |
| `scripts/source_conversation_corpora.py` |  |  | location |
| `scripts/stamp_authorship_headers.py` |  |  | location |
| `scripts/teach_lesson.py` |  |  | location |
| `scripts/termux_voice_bridge.py` |  |  | location |
| `scripts/trace_live_response_pipeline.py` |  |  | location |
| `scripts/trial_crystal_writers.py` |  |  | location |
| `scripts/verify_lesson.py` |  |  | location |
| `scripts/w1_reentrancy_trace.py` |  |  | location |
| `scripts/w1_thought_state_diagnostic.py` |  |  | location |
| `session_continuity_manager.html` |  |  | location |

### Phone app / App shell and screens

| File | Composite | Layer | Basis |
|---|---|---|---|
| `flutter_app/lib/main.dart` | phone_ui.1 |  | location |
| `flutter_app/lib/overlay_entry.dart` |  |  | location |
| `flutter_app/lib/screens/home_screen.dart` | phone_ui.1 |  | location |
| `flutter_app/lib/screens/hub_screen.dart` | phone_ui.1 |  | location |
| `flutter_app/lib/widgets/aurora_orb.dart` | phone_ui.1 |  | location |

### Phone app / Habitat

| File | Composite | Layer | Basis |
|---|---|---|---|
| `flutter_app/lib/habitat/habitat_bridge.dart` | phone_habitat.1 |  | location |
| `flutter_app/lib/habitat/habitat_gesture_layer.dart` | phone_habitat.1 |  | location |
| `flutter_app/lib/habitat/habitat_model.dart` | phone_habitat.1 |  | location |
| `flutter_app/lib/habitat/habitat_renderer.dart` | phone_habitat.1 |  | location |
| `flutter_app/lib/screens/habitat_self_screen.dart` | phone_habitat.1 |  | location |
| `flutter_app/lib/screens/habitat_space_screen.dart` | phone_habitat.1 |  | location |

### Phone app / Dart bridges

| File | Composite | Layer | Basis |
|---|---|---|---|
| `flutter_app/lib/aurora_bridge.dart` |  |  | location |
| `flutter_app/lib/praxis/praxis_bridge.dart` |  |  | location |

### Phone app / On-device Python

| File | Composite | Layer | Basis |
|---|---|---|---|
| `flutter_app/android/app/src/main/python/aurora_bridge.py` | phone_python.1 |  | reviewed |
| `flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py` | phone_python.1 |  | reviewed |
| `flutter_app/android/app/src/main/python/cv2.py` |  |  | reviewed |

### Phone app / Android services

| File | Composite | Layer | Basis |
|---|---|---|---|
| `flutter_app/android/app/src/main/kotlin/org/aurora/app/AuroraService.kt` | phone_android.1 |  | location |
| `flutter_app/android/app/src/main/kotlin/org/aurora/app/BootCompletedReceiver.kt` | phone_android.1 |  | location |
| `flutter_app/android/app/src/main/kotlin/org/aurora/app/MainActivity.kt` | phone_android.1 |  | location |
| `flutter_app/android/app/src/main/kotlin/org/aurora/app/OverlayService.kt` | phone_android.1 |  | location |
| `flutter_app/android/app/src/main/kotlin/org/aurora/app/ScreenObserverService.kt` | phone_android.1 |  | location |
| `src/android/java/org/aurora/OverlayService.java` |  |  | location |

### ACM / ACM core

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora-acm/kernel/src/acm/axes.rs` |  |  | location |
| `aurora-acm/kernel/src/acm/crystal.rs` |  |  | location |
| `aurora-acm/kernel/src/acm/drift.rs` |  |  | location |
| `aurora-acm/kernel/src/acm/mod.rs` |  |  | location |
| `aurora-acm/kernel/src/acm/sedi.rs` |  |  | location |

### ACM / Constraint physics machine

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora-acm/kernel/src/cpm/mod.rs` |  |  | location |
| `aurora-acm/kernel/src/cpm/organ.rs` |  |  | location |
| `aurora-acm/kernel/src/cpm/scheduler.rs` |  |  | location |

### ACM / X-Aurora ISA, VM and JIT

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora-acm/kernel/src/xaurora/isa.rs` | acm_xaurora.1 |  | location |
| `aurora-acm/kernel/src/xaurora/jit.rs` | acm_xaurora.1 |  | location |
| `aurora-acm/kernel/src/xaurora/mod.rs` | acm_xaurora.1 |  | location |
| `aurora-acm/kernel/src/xaurora/vm.rs` | acm_xaurora.1 |  | location |

### ACM / Expression

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora-acm/kernel/src/expression/color.rs` | acm_expression.1 |  | location |
| `aurora-acm/kernel/src/expression/face.rs` | acm_expression.1 |  | location |
| `aurora-acm/kernel/src/expression/mod.rs` | acm_expression.1 |  | location |
| `aurora-acm/kernel/src/expression/renderer.rs` | acm_expression.1 |  | location |

### ACM / Hardware drivers

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora-acm/kernel/src/hw/idt.rs` | acm_hw.1 |  | location |
| `aurora-acm/kernel/src/hw/mod.rs` | acm_hw.1 |  | location |
| `aurora-acm/kernel/src/hw/pic.rs` | acm_hw.1 |  | location |
| `aurora-acm/kernel/src/hw/pit.rs` | acm_hw.1 |  | location |
| `aurora-acm/kernel/src/hw/port.rs` | acm_hw.1 |  | location |
| `aurora-acm/kernel/src/hw/ps2.rs` | acm_hw.1 |  | location |
| `aurora-acm/kernel/src/hw/uart.rs` | acm_hw.1 |  | location |

### ACM / Bridge protocol

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora-acm/kernel/src/bridge/mod.rs` |  |  | location |
| `aurora-acm/kernel/src/bridge/protocol.rs` |  |  | location |

### ACM / Boot and runner

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora-acm/kernel/src/main.rs` |  |  | location |
| `aurora-acm/run.sh` |  |  | location |
| `aurora-acm/runner/build.rs` |  |  | location |
| `aurora-acm/runner/src/main.rs` |  |  | location |

### ACM / Native Python runtime

| File | Composite | Layer | Basis |
|---|---|---|---|
| `aurora-acm/native/aurora_acm_native.py` |  |  | location |

### Repository and CI / CI workflows

| File | Composite | Layer | Basis |
|---|---|---|---|
| `.github/workflows/aurora-autonomous-run.yml` |  |  | location |
| `.github/workflows/aurora-clones.yml` |  |  | location |
| `.github/workflows/aurora-development-experiment.yml` |  |  | location |
| `.github/workflows/build-apk.yml` |  |  | location |
| `.github/workflows/flutter-android.yml` |  |  | location |
| `.github/workflows/python-ci.yml` |  |  | location |
