# Aurora's crystal ladder: declared responsibility against implemented and observed behaviour

Authors: Sunni (Sir) Morningstar & Cael Devo  
Source commit `311eb097b936`.  Ownership mapping: `docs/module_ownership.json` (schema `aurora.module_ownership/2`).

The repository is the king quasi. Each domain is a quasi, each declared subsystem a higher-order unit, and every file a base unit. Domains and subsystems are claims from the ownership mapping. A composite is promoted only when the graph shows its files bound by calls, instantiation, inheritance, spawns, callbacks, value flow or shared state; the mapping's own composites (built from imports) are listed beside them with how much of that binding their links carry. A conflict means the evidence points beyond the declared subsystem; it is a question to review, not a correction.

## Aurora repository (king quasi)

### Quasi: ACM (`subsys:quasi:acm`), 30 base file(s)

Declared: The Rust kernel, its runner and the native Python ACM runtime.

#### Higher order: Boot and runner (`subsys:category:acm_boot`), 4 member(s)

Declared: The kernel entry point, the host runner and the boot script.

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora-acm/kernel/src/main.rs` | location | - | - | - | 0 | - |
| `aurora-acm/run.sh` | location | - | - | - | 0 | - |
| `aurora-acm/runner/build.rs` | location | - | - | - | 0 | - |
| `aurora-acm/runner/src/main.rs` | location | - | - | - | 0 | - |

#### Higher order: Bridge protocol (`subsys:category:acm_bridge`), 2 member(s)

Declared: The kernel side of the bridge to her Python stack.

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora-acm/kernel/src/bridge/mod.rs` | location | - | - | - | 0 | - |
| `aurora-acm/kernel/src/bridge/protocol.rs` | location | - | - | - | 0 | - |

#### Higher order: ACM core (`subsys:category:acm_core`), 5 member(s)

Declared: Axes, crystal, drift and sedi modules of the kernel.

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora-acm/kernel/src/acm/axes.rs` | location | - | - | - | 0 | - |
| `aurora-acm/kernel/src/acm/crystal.rs` | location | - | - | - | 0 | - |
| `aurora-acm/kernel/src/acm/drift.rs` | location | - | - | - | 0 | - |
| `aurora-acm/kernel/src/acm/mod.rs` | location | - | - | - | 0 | - |
| `aurora-acm/kernel/src/acm/sedi.rs` | location | - | - | - | 0 | - |

#### Higher order: Constraint physics machine (`subsys:category:acm_cpm`), 3 member(s)

Declared: CPM organs and scheduler.

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora-acm/kernel/src/cpm/mod.rs` | location | - | - | - | 0 | - |
| `aurora-acm/kernel/src/cpm/organ.rs` | location | - | - | - | 0 | - |
| `aurora-acm/kernel/src/cpm/scheduler.rs` | location | - | - | - | 0 | - |

#### Higher order: Expression (`subsys:category:acm_expression`), 4 member(s)

Declared: Face, colour and renderer.

- Evidence composite `subsys:composite:acm_expression:3f00d90e`: 2 files, cohesion 0.75, binding {'CALLS': 3}. Files: `aurora-acm/kernel/src/expression/color.rs`, `aurora-acm/kernel/src/expression/renderer.rs`
- Declared composite `acm_expression.1` (hub `aurora-acm/kernel/src/expression/mod.rs`): 4 files, 1 of 5 import links carry binding, status partly_supported, closest evidence composite `subsys:composite:acm_expression:3f00d90e` (overlap 0.5).

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora-acm/kernel/src/expression/color.rs` | location | - | - | - | 0 | - |
| `aurora-acm/kernel/src/expression/face.rs` | location | - | - | - | 0 | - |
| `aurora-acm/kernel/src/expression/mod.rs` | location | - | - | - | 0 | - |
| `aurora-acm/kernel/src/expression/renderer.rs` | location | - | - | - | 0 | - |

#### Higher order: Hardware drivers (`subsys:category:acm_hw`), 7 member(s)

Declared: IDT, PIC, PIT, ports, PS/2 and UART.

- Evidence composite `subsys:composite:acm_hw:58b75e45`: 3 files, cohesion 0.6, binding {'CALLS': 9}. Files: `aurora-acm/kernel/src/hw/pic.rs`, `aurora-acm/kernel/src/hw/port.rs`, `aurora-acm/kernel/src/hw/uart.rs`
- Declared composite `acm_hw.1` (hub `aurora-acm/kernel/src/hw/mod.rs`): 7 files, 4 of 11 import links carry binding, status partly_supported, closest evidence composite `subsys:composite:acm_hw:58b75e45` (overlap 0.429).

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora-acm/kernel/src/hw/idt.rs` | location | - | - | - | 0 | - |
| `aurora-acm/kernel/src/hw/mod.rs` | location | - | - | - | 0 | - |
| `aurora-acm/kernel/src/hw/pic.rs` | location | - | - | - | 0 | - |
| `aurora-acm/kernel/src/hw/pit.rs` | location | - | - | - | 0 | - |
| `aurora-acm/kernel/src/hw/port.rs` | location | - | - | - | 0 | - |
| `aurora-acm/kernel/src/hw/ps2.rs` | location | - | - | - | 0 | - |
| `aurora-acm/kernel/src/hw/uart.rs` | location | - | - | - | 0 | - |

#### Higher order: Native Python runtime (`subsys:category:acm_native`), 1 member(s)

Declared: The Python-native ACM runtime.

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora-acm/native/aurora_acm_native.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |

#### Higher order: X-Aurora ISA, VM and JIT (`subsys:category:acm_xaurora`), 4 member(s)

Declared: The instruction set, virtual machine and JIT.

- Evidence composite `subsys:composite:acm_xaurora:3ed31dfd`: 2 files, cohesion 0.375, binding {'CALLS': 3}. Files: `aurora-acm/kernel/src/xaurora/isa.rs`, `aurora-acm/kernel/src/xaurora/jit.rs`
- Declared composite `acm_xaurora.1` (hub `aurora-acm/kernel/src/xaurora/isa.rs`): 4 files, 3 of 6 import links carry binding, status partly_supported, closest evidence composite `subsys:composite:acm_xaurora:3ed31dfd` (overlap 0.5).

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora-acm/kernel/src/xaurora/isa.rs` | location | - | - | - | 0 | - |
| `aurora-acm/kernel/src/xaurora/jit.rs` | location | - | - | - | 0 | - |
| `aurora-acm/kernel/src/xaurora/mod.rs` | location | - | - | - | 0 | - |
| `aurora-acm/kernel/src/xaurora/vm.rs` | location | - | - | - | 0 | - |

### Quasi: Desktop Aurora (`subsys:quasi:desktop`), 934 base file(s)

Declared: Her Python runtime and everything that runs, tests or maintains it on a computer.

#### Higher order: Bridges and external tools (`subsys:category:bridges`), 17 member(s)

Declared: Praxis, ACM, scouting, research dispatch and tool registries.

- Evidence composite `subsys:composite:bridges:32b189f0`: 3 files, cohesion 0.128, binding {'CALLS': 6, 'INSTANTIATES': 2, 'FEEDS': 18, 'SHARED_STATE': 1}. Files: `aurora_praxis_initiative.py`, `aurora_praxis_messenger.py`, `aurora_social_corroboration.py`
- Evidence composite `subsys:composite:bridges:9c439ea7`: 3 files, cohesion 0.104, binding {'CALLS': 19, 'FEEDS': 15, 'SHARED_STATE': 1}. Files: `aurora_desktop_agent.py`, `aurora_internal/tool_registry.py`, `aurora_tool_mind.py`
- Evidence composite `subsys:composite:bridges:d8368445`: 2 files, cohesion 0.029, binding {'CALLS': 4, 'FEEDS': 6}. Files: `aurora_internal/scouting/broker.py`, `aurora_internal/scouting/contracts.py`
- Declared composite `bridges.1` (hub `aurora_internal/scouting/contracts.py`): 4 files, 4 of 4 import links carry binding, status supported, closest evidence composite `subsys:composite:bridges:d8368445` (overlap 0.5).
- Declared composite `bridges.2` (hub `aurora_praxis_messenger.py`): 3 files, 2 of 2 import links carry binding, status supported, closest evidence composite `subsys:composite:bridges:32b189f0` (overlap 1.0).
- Declared composite `bridges.3` (hub `aurora_desktop_agent.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite `subsys:composite:bridges:9c439ea7` (overlap 0.667).

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora_acm_bridge.py` | name_and_docstring | - | - | - | 0 | consistent |
| `aurora_desktop_agent.py` | name_and_docstring | - | - | - | 0 | consistent |
| `aurora_internal/aurora_clone_harvest.py` | name_and_docstring | phone | - | - | 0 | consistent |
| `aurora_internal/aurora_recommendation_hub.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 5 | consistent |
| `aurora_internal/scouting/__init__.py` | name_and_docstring | - | desktop_turns | - | 0 | consistent |
| `aurora_internal/scouting/backends.py` | name_and_docstring | phone | - | - | 0 | consistent |
| `aurora_internal/scouting/broker.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/scouting/contracts.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/scouting/subsurface_scout_bridge.py` | name_and_docstring | desktop, phone | desktop_turns | - | 1 | consistent |
| `aurora_internal/tool_registry.py` | name_and_docstring | desktop, phone | desktop_turns | - | 2 | consistent |
| `aurora_praxis_bridge.py` | name_and_docstring | phone | - | praxis_bridge | 0 | consistent |
| `aurora_praxis_initiative.py` | name_and_docstring | phone | - | - | 1 | consistent |
| `aurora_praxis_messenger.py` | name_and_docstring | desktop, phone | - | conversation_memory, praxis_messenger | 2 | consistent |
| `aurora_recommendation_hub.py` | name_and_docstring | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `aurora_research_dispatch.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_social_corroboration.py` | name_and_docstring | phone | - | - | 2 | consistent |
| `aurora_tool_mind.py` | name_and_docstring | desktop, phone | - | - | 2 | consistent |

#### Higher order: Crystal ops (`subsys:category:crystal`), 26 member(s)

Declared: The concept-crystal store, its evidence-based growth, ingestion and persistence, interaction crystals, and the crystal types QuasiArch shares with live processing.

- Evidence composite `subsys:composite:crystal:1a4df838`: 4 files, cohesion 0.33, binding {'INHERITS': 1, 'CALLS': 21, 'INSTANTIATES': 12, 'FEEDS': 44, 'SHARED_STATE': 11}. Files: `aurora_interaction_engine.py`, `aurora_interaction_processing.py`, `aurora_internal/quasiarch_observer/crystal_engine.py`, `aurora_internal/quasiarch_observer/dimensional_processing.py`
- Evidence composite `subsys:composite:crystal:1dc7e692`: 2 files, cohesion 0.667, binding {'CALLS': 1, 'INSTANTIATES': 2, 'FEEDS': 5}. Files: `aurora_crystal_state_bridge.py`, `crystalzip.py`
- Evidence composite `subsys:composite:crystal:2c7f2bbb`: 3 files, cohesion 0.046, binding {'CALLS': 7, 'FEEDS': 4}. Files: `aurora_internal/aurora_lexical_crystals.py`, `aurora_internal/aurora_representation_crystals.py`, `concept_crystal.py`
- Evidence composite `subsys:composite:crystal:cbfaf025`: 14 files, cohesion 0.232, binding {'CALLS': 80, 'FEEDS': 164, 'INSTANTIATES': 3}. Files: `aurora_crystal_ingestion.py`, `aurora_internal/crystal_associations.py`, `aurora_internal/crystal_convergence.py`, `aurora_internal/crystal_facets.py`, `aurora_internal/crystal_grammar.py`, `aurora_internal/crystal_interior.py`, `aurora_internal/crystal_lexicon.py`, `aurora_internal/crystal_maturity.py`, `aurora_internal/crystal_promotion.py`, `aurora_internal/crystal_runtime.py`, `aurora_internal/crystal_sensory.py`, `aurora_internal/crystal_store.py` ...
- Declared composite `crystal.1` (hub `aurora_internal/crystal_runtime.py`): 14 files, 30 of 30 import links carry binding, status supported, closest evidence composite `subsys:composite:crystal:cbfaf025` (overlap 1.0).
- Declared composite `crystal.2` (hub `aurora_interaction_processing.py`): 5 files, 3 of 6 import links carry binding, status partly_supported, closest evidence composite `subsys:composite:crystal:1a4df838` (overlap 0.8).
- Declared composite `crystal.3` (hub `aurora_internal/aurora_lexical_crystals.py`): 3 files, 3 of 3 import links carry binding, status supported, closest evidence composite `subsys:composite:crystal:2c7f2bbb` (overlap 1.0).
- Declared composite `crystal.4` (hub `aurora_crystal_state_bridge.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite `subsys:composite:crystal:1dc7e692` (overlap 1.0).

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora_core_concept_crystallization.py` | name_and_docstring | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_crystal_ingestion.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_crystal_state_bridge.py` | name_and_docstring | - | desktop_boot | - | 1 | consistent |
| `aurora_interaction_engine.py` | reviewed | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_interaction_processing.py` | reviewed | desktop, phone | desktop_boot, desktop_turns | interaction_processing | 0 | consistent |
| `aurora_internal/aurora_lexical_crystals.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_representation_crystals.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_sensory_crystal.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | sensory_crystal | 2 | consistent |
| `aurora_internal/crystal_associations.py` | name_and_docstring | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_internal/crystal_convergence.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_internal/crystal_facets.py` | name_and_docstring | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_internal/crystal_grammar.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_internal/crystal_interior.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_internal/crystal_lexicon.py` | name_and_docstring | desktop, phone | desktop_boot | - | 1 | consistent |
| `aurora_internal/crystal_maturity.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_internal/crystal_promotion.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_internal/crystal_runtime.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_internal/crystal_sensory.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_internal/crystal_store.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/crystal_substitutability.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/crystal_weave.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_internal/quasiarch_observer/__init__.py` | reviewed | - | desktop_boot | - | 0 | consistent |
| `aurora_internal/quasiarch_observer/crystal_engine.py` | reviewed | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_internal/quasiarch_observer/dimensional_processing.py` | reviewed | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `concept_crystal.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 1 | consistent |
| `crystalzip.py` | name_and_docstring | - | desktop_boot | - | 1 | consistent |

#### Higher order: Beings and dimensional systems (`subsys:category:dimensional`), 5 member(s)

Declared: I-State beings, dimensional systems, consciousness assembly and simulation (the L2 to L4 and L7 layer files).

- Evidence composite `subsys:composite:dimensional:78d8264b`: 4 files, cohesion 0.034, binding {'INSTANTIATES': 6, 'CALLS': 12, 'FEEDS': 21, 'SHARED_STATE': 3}. Files: `aurora_consciousness_engine.py`, `aurora_dimensional_systems.py`, `aurora_i_state_beings.py`, `aurora_simulation_engine.py`
- Declared composite `dimensional.1` (hub `aurora_consciousness_engine.py`): 4 files, 4 of 5 import links carry binding, status partly_supported, closest evidence composite `subsys:composite:dimensional:78d8264b` (overlap 1.0).

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora_consciousness_engine.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | consciousness | 1 | consistent |
| `aurora_dimensional_systems.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | dimensional | 0 | consistent |
| `aurora_i_state_beings.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | collective | 0 | consistent |
| `aurora_istate_operations.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_simulation_engine.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | simulation, time_dilation_governor | 0 | consistent |

#### Higher order: Foundation and constraint layers (`subsys:category:foundation`), 38 member(s)

Declared: Foundational contract, IVM lattice, X/T/N/B/A constraint physics, NonComp, pressure and leverage.

- Evidence composite `subsys:composite:foundation:5e482b6c`: 14 files, cohesion 0.122, binding {'INHERITS': 1, 'CALLS': 68, 'FEEDS': 158, 'INSTANTIATES': 29, 'SHARED_STATE': 3}. Files: `aurora_constraint_engine.py`, `aurora_constraint_manifold_compiler.py`, `aurora_constraint_unit_adapter.py`, `aurora_internal/aurora_constraint_manifold_patched.py`, `aurora_internal/aurora_leverage_scalar.py`, `aurora_internal/aurora_noncomp_registry.py`, `aurora_internal/aurora_ontological_scaffolding.py`, `aurora_internal/aurora_polarity_gradient.py`, `aurora_internal/aurora_pressure_ledger.py`, `aurora_internal/aurora_pressure_mathematics_tracker.py`, `aurora_internal/aurora_shared_helpers.py`, `aurora_internal/aurora_structural_pressure_steering.py` ...
- Evidence composite `subsys:composite:foundation:71e21bb1`: 2 files, cohesion 0.343, binding {'INSTANTIATES': 1, 'CALLS': 5, 'FEEDS': 13, 'SHARED_STATE': 4}. Files: `aurora_internal/aurora_pressure_classifier.py`, `aurora_internal/aurora_pressure_router.py`
- Evidence composite `subsys:composite:foundation:8bbcbdb6`: 2 files, cohesion 0.08, binding {'INSTANTIATES': 1, 'CALLS': 3, 'FEEDS': 3}. Files: `aurora_manifold_directory_reader.py`, `aurora_manifold_lookup.py`
- Evidence composite `subsys:composite:foundation:9389ce53`: 2 files, cohesion 0.195, binding {'INSTANTIATES': 1, 'CALLS': 5, 'FEEDS': 9}. Files: `aurora_computational_model.py`, `aurora_constraint_head.py`
- Declared composite `foundation.1` (hub `aurora_internal/aurora_noncomp_registry.py`): 18 files, 19 of 25 import links carry binding, status partly_supported, closest evidence composite `subsys:composite:foundation:5e482b6c` (overlap 0.778).
- Declared composite `foundation.2` (hub `aurora_computational_model.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite `subsys:composite:foundation:9389ce53` (overlap 1.0).
- Declared composite `foundation.3` (hub `aurora_internal/aurora_pressure_classifier.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite `subsys:composite:foundation:71e21bb1` (overlap 1.0).
- Declared composite `foundation.4` (hub `aurora_manifold_directory_reader.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite `subsys:composite:foundation:8bbcbdb6` (overlap 1.0).

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora_625_pressure_map.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 2 | consistent |
| `aurora_computational_model.py` | name_and_docstring | desktop, phone | - | cpm | 0 | consistent |
| `aurora_constraint_emission.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | constraint_emitter | 0 | consistent |
| `aurora_constraint_engine.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 2 | consistent |
| `aurora_constraint_field_map.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_constraint_head.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_constraint_manifold.py` | name_and_docstring | - | desktop_boot | - | 0 | consistent |
| `aurora_constraint_manifold_compiler.py` | name_and_docstring | desktop, phone | desktop_boot | - | 1 | consistent |
| `aurora_constraint_manifold_router.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | noncomp_manifold_router | 0 | consistent |
| `aurora_constraint_ontology.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_constraint_signature_resolver.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_constraint_stack.py` | name_and_docstring | - | desktop_boot | - | 0 | consistent |
| `aurora_constraint_unit_adapter.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_axis_emergence.py` | name_and_docstring | desktop | - | - | 1 | consistent |
| `aurora_internal/aurora_boundary_envelope.py` | name_and_docstring | desktop, phone | desktop_turns | - | 1 | consistent |
| `aurora_internal/aurora_constraint_manifold_patched.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_dpme_pressure_bridge.py` | name_and_docstring | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_internal/aurora_leverage_scalar.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | bias_engine | 0 | consistent |
| `aurora_internal/aurora_noncomp_registry.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_ontological_scaffolding.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 1 | consistent |
| `aurora_internal/aurora_polarity_gradient.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_pressure_adapter.py` | name_and_docstring | desktop | - | - | 1 | consistent |
| `aurora_internal/aurora_pressure_classifier.py` | name_and_docstring | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_internal/aurora_pressure_ledger.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 1 | consistent |
| `aurora_internal/aurora_pressure_mathematics_tracker.py` | name_and_docstring | desktop, phone | desktop_boot | - | 1 | consistent |
| `aurora_internal/aurora_pressure_router.py` | name_and_docstring | desktop, phone | desktop_boot | - | 2 | consistent |
| `aurora_internal/aurora_shared_helpers.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_internal/aurora_structural_pressure_steering.py` | name_and_docstring | desktop, phone | desktop_boot | - | 1 | consistent |
| `aurora_internal/aurora_tensor_expressions.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | tensor_expressions | 0 | consistent |
| `aurora_ivm.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | contradiction_ledger, lattice | 1 | consistent |
| `aurora_manifold_directory/__init__.py` | name_and_docstring | - | desktop_boot | - | 0 | consistent |
| `aurora_manifold_directory/noncomp_field.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | behavioral_identity, identity_field | 0 | consistent |
| `aurora_manifold_directory_reader.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | noncomp_manifold_directory | 0 | consistent |
| `aurora_manifold_lookup.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_noncomp_layer_compiler.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | noncomp_layer_compiler | 0 | consistent |
| `aurora_noncomp_manifold_compiler.py` | name_and_docstring | - | desktop_boot | - | 0 | consistent |
| `aurora_pressure_ontology.py` | name_and_docstring | desktop, phone | desktop_boot | - | 1 | consistent |
| `foundational_contract.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | contract | 0 | consistent |

#### Higher order: Genealogy, lineage and evidence (`subsys:category:genealogy`), 25 member(s)

Declared: Constraint genealogy, code and ability lineage, function provenance, evidence qualification, WARP.

- Evidence composite `subsys:composite:genealogy:10b01d71`: 7 files, cohesion 0.076, binding {'INHERITS': 1, 'CALLS': 23, 'INSTANTIATES': 5, 'FEEDS': 24, 'SHARED_STATE': 4}. Files: `aurora_genealogy_representation_resolver.py`, `aurora_internal/aurora_manual_code_lineage.py`, `aurora_internal/aurora_system_introspection.py`, `aurora_internal/aurora_universal_function_lineage.py`, `aurora_internal/lineage_canonical.py`, `aurora_warp_protocol.py`, `tensor_occupancy_warp_bridge.py`
- Evidence composite `subsys:composite:genealogy:c9b3e419`: 7 files, cohesion 0.088, binding {'CALLS': 27, 'INSTANTIATES': 10, 'FEEDS': 66, 'SHARED_STATE': 6}. Files: `aurora_closure_basis.py`, `aurora_genealogy_environment.py`, `aurora_internal/aurora_ability_lineage_compiler.py`, `aurora_internal/aurora_lineage_bound_traits.py`, `aurora_internal/constraint_genealogy.py`, `aurora_internal/genealogy_evidence_journal.py`, `genealogy_signature_bridge.py`
- Declared composite `genealogy.1` (hub `aurora_internal/constraint_genealogy.py`): 12 files, 13 of 13 import links carry binding, status supported, closest evidence composite `subsys:composite:genealogy:c9b3e419` (overlap 0.583).
- Declared composite `genealogy.2` (hub `aurora_genealogy_promotion_dimension_observer.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite none.
- Declared composite `genealogy.3` (hub `aurora_internal/aurora_attribution_trace.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite `subsys:composite:genealogy:10b01d71` (overlap 0.125).

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora_closure_basis.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_genealogy_environment.py` | name_and_docstring | - | - | - | 0 | consistent |
| `aurora_genealogy_promotion_dimension_observer.py` | name_and_docstring | - | - | - | 0 | consistent |
| `aurora_genealogy_representation_resolver.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_genealogy_same_event_correlation.py` | name_and_docstring | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `aurora_internal/aurora_ability_lineage_compiler.py` | name_and_docstring | desktop, phone | desktop_boot | - | 3 | consistent |
| `aurora_internal/aurora_attribution_trace.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_dna_strand_schema.py` | name_and_docstring | desktop, phone | desktop_boot | strand_lib | 0 | consistent |
| `aurora_internal/aurora_evolutionary_ancestry_bridge.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_internal/aurora_icc_ledger.py` | name_and_docstring | desktop, phone | desktop_boot | icc_ledger | 0 | consistent |
| `aurora_internal/aurora_lineage_bound_traits.py` | name_and_docstring | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_internal/aurora_lineage_runtime_activation.py` | name_and_docstring | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_internal/aurora_live_lineage_journal.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | lineage_emergence_journal | 1 | consistent |
| `aurora_internal/aurora_manual_code_lineage.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | manual_code_lineage | 1 | consistent |
| `aurora_internal/aurora_stack_trace_instrumentation.py` | reviewed | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_internal/aurora_system_introspection.py` | reviewed | desktop, phone | desktop_boot, desktop_turns | system_introspection | 4 | consistent |
| `aurora_internal/aurora_universal_function_lineage.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | function_lineage | 2 | consistent |
| `aurora_internal/constraint_genealogy.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | genealogy | 0 | consistent |
| `aurora_internal/evidence_qualification.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/genealogy_evidence_journal.py` | name_and_docstring | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_internal/lineage_canonical.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_warp_protocol.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | warp_field | 0 | consistent |
| `genealogy_signature_bridge.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `tensor_occupancy_hook.py` | name_and_docstring | - | desktop_boot | - | 1 | consistent |
| `tensor_occupancy_warp_bridge.py` | name_and_docstring | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |

#### Higher order: Governance, persistence and health (`subsys:category:governance`), 23 member(s)

Declared: Persistence, checkpoints, autonomy, runtime faults and health, metabolic clock, fail-closed guards.

- Evidence composite `subsys:composite:governance:16699d84`: 18 files, cohesion 0.047, binding {'CALLS': 134, 'INSTANTIATES': 4, 'FEEDS': 22, 'SHARED_STATE': 4}. Files: `aurora_autonomy.py`, `aurora_checkpoint.py`, `aurora_dev_telemetry.py`, `aurora_governance_persistence_gateway.py`, `aurora_internal/aurora_energy_layer_costs.py`, `aurora_internal/aurora_identity_persistence.py`, `aurora_internal/aurora_leverage_relief.py`, `aurora_internal/aurora_metabolic_clock.py`, `aurora_internal/aurora_metabolic_steps.py`, `aurora_internal/aurora_persistence_audit.py`, `aurora_internal/aurora_persistence_utils.py`, `aurora_internal/aurora_rest_ledger.py` ...
- Declared composite `governance.1` (hub `aurora_internal/aurora_runtime_faults.py`): 19 files, 22 of 25 import links carry binding, status partly_supported, closest evidence composite `subsys:composite:governance:16699d84` (overlap 0.762).
- Declared composite `governance.2` (hub `aurora_internal/aurora_metabolic_steps.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite `subsys:composite:governance:16699d84` (overlap 0.111).

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora_autonomy.py` | name_and_docstring | desktop, phone | desktop_boot | autonomy | 1 | consistent |
| `aurora_checkpoint.py` | name_and_docstring | desktop, phone | desktop_boot | checkpoint | 1 | consistent |
| `aurora_dev_telemetry.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_governance_persistence_gateway.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | aurora, persistence_gateway, state_persistence | 3 | consistent |
| `aurora_internal/aurora_energy_layer_costs.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | accountant | 0 | consistent |
| `aurora_internal/aurora_identity_persistence.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | conversation_memory, core_identity, enhanced_persist | 2 | consistent |
| `aurora_internal/aurora_leverage_relief.py` | name_and_docstring | desktop | - | - | 3 | consistent |
| `aurora_internal/aurora_local_llm_bridge.py` | reviewed | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `aurora_internal/aurora_metabolic_clock.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | metabolic_clock | 1 | consistent |
| `aurora_internal/aurora_metabolic_steps.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_persistence_audit.py` | name_and_docstring | desktop, phone | - | - | 1 | consistent |
| `aurora_internal/aurora_persistence_utils.py` | name_and_docstring | desktop, phone | desktop_boot | - | 1 | consistent |
| `aurora_internal/aurora_rest_ledger.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_internal/aurora_runtime_constraint_governor.py` | name_and_docstring | desktop, phone | desktop_turns | - | 1 | consistent |
| `aurora_internal/aurora_runtime_faults.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 2 | consistent |
| `aurora_internal/aurora_runtime_health.py` | reviewed | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `aurora_internal/aurora_state_context.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_metabolic_distiller.py` | name_and_docstring | desktop | - | - | 0 | consistent |
| `aurora_offline_resilience.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 3 | consistent |
| `aurora_persistence_utils.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | drive_sync, git_sync | 1 | consistent |
| `aurora_support_stack.py` | name_and_docstring | - | desktop_boot | - | 0 | consistent |
| `aurora_telemetry.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `scripts/autonomous_access.sh` | location | - | - | - | 0 | - |

#### Higher order: Investigative and diagnostic (`subsys:category:investigative`), 45 member(s)

Declared: Observers, canaries, probes, shadows, audits, reports and test setup. Some observers run live and write their own records, as the QuasiArch observer and the learning probe do; the QuasiArch observer stays here.

- Evidence composite `subsys:composite:investigative:4f4bb621`: 4 files, cohesion 0.152, binding {'INSTANTIATES': 2, 'CALLS': 14, 'FEEDS': 30, 'SHARED_STATE': 2}. Files: `aurora_internal/aurora_quasiarch_observer.py`, `aurora_internal/quasiarch_development_inquiry.py`, `aurora_internal/quasiarch_observer/dimensional_memory.py`, `aurora_internal/quasiarch_observer/ghost_relics.py`
- Evidence composite `subsys:composite:investigative:605f7d51`: 2 files, cohesion 0.104, binding {'CALLS': 5}. Files: `aurora_genealogy_difference_shadow.py`, `aurora_genealogy_difference_shadow_report.py`
- Evidence composite `subsys:composite:investigative:c6e8f22f`: 2 files, cohesion 0.103, binding {'CALLS': 2, 'FEEDS': 2}. Files: `aurora_genealogy_difference_producer_observatory.py`, `aurora_genealogy_difference_producer_observatory_report.py`
- Evidence composite `subsys:composite:investigative:d9f78b8b`: 2 files, cohesion 0.125, binding {'CALLS': 2, 'FEEDS': 2}. Files: `aurora_genealogy_cooccurrence_observatory.py`, `aurora_genealogy_cooccurrence_observatory_report.py`
- Evidence composite `subsys:composite:investigative:da615aa1`: 2 files, cohesion 0.047, binding {'CALLS': 3, 'PASSES_CALLBACK': 1}. Files: `aurora_causal_vs_representational_probe.py`, `aurora_rank6_shadow_analysis.py`
- Declared composite `investigative.1` (hub `aurora_genealogy_cooccurrence_observatory.py`): 4 files, 3 of 3 import links carry binding, status supported, closest evidence composite `subsys:composite:investigative:d9f78b8b` (overlap 0.5).
- Declared composite `investigative.2` (hub `aurora_causal_vs_representational_probe.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite `subsys:composite:investigative:da615aa1` (overlap 1.0).
- Declared composite `investigative.3` (hub `aurora_genealogy_difference_shadow.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite `subsys:composite:investigative:605f7d51` (overlap 1.0).
- Declared composite `investigative.4` (hub `aurora_internal/aurora_quasiarch_observer.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite `subsys:composite:investigative:4f4bb621` (overlap 0.5).
- Declared composite `investigative.5` (hub `aurora_internal/quasiarch_observer/dimensional_memory.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite `subsys:composite:investigative:4f4bb621` (overlap 0.5).

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora_build714_resolution_canaries.py` | name_and_docstring | - | - | - | 0 | unverified |
| `aurora_causal_vs_representational_probe.py` | name_and_docstring | - | - | - | 0 | unverified |
| `aurora_diag.py` | name_and_docstring | - | - | - | 0 | unverified |
| `aurora_dream_new_experience_canary.py` | name_and_docstring | - | - | - | 0 | unverified |
| `aurora_flow_audit.py` | name_and_docstring | - | - | - | 0 | unverified |
| `aurora_genealogy_cooccurrence_observatory.py` | name_and_docstring | - | - | - | 0 | consistent |
| `aurora_genealogy_cooccurrence_observatory_report.py` | name_and_docstring | - | - | - | 0 | unverified |
| `aurora_genealogy_difference_producer_observatory.py` | name_and_docstring | - | - | - | 0 | consistent |
| `aurora_genealogy_difference_producer_observatory_report.py` | name_and_docstring | - | - | - | 0 | unverified |
| `aurora_genealogy_difference_shadow.py` | name_and_docstring | - | - | - | 0 | consistent |
| `aurora_genealogy_difference_shadow_report.py` | name_and_docstring | - | - | - | 0 | unverified |
| `aurora_genealogy_environment_shadow.py` | name_and_docstring | - | - | - | 0 | unverified |
| `aurora_genealogy_promotion_dimension_shadow.py` | name_and_docstring | - | - | - | 0 | unverified |
| `aurora_internal/aurora_boot_parity.py` | reviewed | - | - | - | 0 | unverified |
| `aurora_internal/aurora_episode_slip_profiler.py` (also) | reviewed | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_internal/aurora_fault_audit.py` | reviewed | - | - | - | 0 | unverified |
| `aurora_internal/aurora_pf1_5_instruments.py` (also) | reviewed | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_quasiarch_observer.py` | reviewed | desktop, phone | desktop_boot, desktop_turns | quasiarch_observer | 2 | consistent |
| `aurora_internal/aurora_semantic_probe_battery.py` (also) | reviewed | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_stack_trace_instrumentation.py` (also) | reviewed | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_internal/aurora_surface_doc.py` (also) | reviewed | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_internal/aurora_system_introspection.py` (also) | reviewed | desktop, phone | desktop_boot, desktop_turns | system_introspection | 4 | consistent |
| `aurora_internal/dual_strata/mtsl_acceptance_report.py` | name_and_docstring | - | - | - | 0 | unverified |
| `aurora_internal/dual_strata/perturbation_probe.py` (also) | reviewed | desktop, phone | - | - | 0 | consistent |
| `aurora_internal/quasiarch_development_inquiry.py` | reviewed | desktop, phone | - | - | 0 | consistent |
| `aurora_internal/quasiarch_observer/__init__.py` (also) | reviewed | - | desktop_boot | - | 0 | consistent |
| `aurora_internal/quasiarch_observer/crystal_engine.py` (also) | reviewed | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_internal/quasiarch_observer/dimensional_memory.py` | reviewed | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/quasiarch_observer/dimensional_processing.py` (also) | reviewed | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/quasiarch_observer/ghost_relics.py` | reviewed | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_learning_probe.py` | reviewed | phone | - | learning_probe | 1 | consistent |
| `aurora_learning_report.py` | name_and_docstring | - | - | - | 0 | unverified |
| `aurora_rank6_shadow_analysis.py` | name_and_docstring | - | - | - | 0 | consistent |
| `aurora_representational_canary.py` | name_and_docstring | - | - | - | 0 | unverified |
| `aurora_representational_closed_loop_canary.py` | name_and_docstring | - | - | - | 0 | unverified |
| `aurora_representational_cross_system_canary.py` | name_and_docstring | - | - | - | 0 | unverified |
| `aurora_representational_divergence_canaries.py` | name_and_docstring | - | - | - | 0 | unverified |
| `aurora_representational_emergence_observatory.py` | name_and_docstring | - | - | - | 0 | unverified |
| `aurora_same_input_history_canary.py` | name_and_docstring | - | - | - | 0 | unverified |
| `conftest.py` | reviewed | - | - | - | 0 | unverified |
| `run_full_competency_gauntlet.py` | reviewed | - | - | - | 1 | unverified |
| `run_gauntlet.py` | reviewed | - | - | - | 2 | conflict: writes state that production code outside investigative work reads: store:daemon.log (read by aurora_hub) |
| `run_probe_battery.py` | reviewed | - | - | - | 3 | unverified |
| `scripts/reset_quasiarch_observer_state.sh` | location | - | - | - | 0 | - |
| `test_constraint_reasoner.py` | name_and_docstring | - | - | - | 0 | unverified |

#### Higher order: Identity and language (`subsys:category:language`), 15 member(s)

Declared: Behavioral identity, language state, lexicon, grammar and word use.

- Evidence composite `subsys:composite:language:ab4e00b7`: 2 files, cohesion 0.028, binding {'CALLS': 6, 'FEEDS': 1}. Files: `aurora_internal/aurora_communication_emergence.py`, `aurora_internal/aurora_meaning_evolution.py`
- Evidence composite `subsys:composite:language:f91cf40d`: 2 files, cohesion 0.077, binding {'CALLS': 4, 'INSTANTIATES': 2, 'FEEDS': 10}. Files: `aurora_internal/aurora_conversation_rubric_engine.py`, `aurora_internal/aurora_semantic_probe_battery.py`
- Declared composite `language.1` (hub `aurora_internal/aurora_conversation_rubric_engine.py`): 3 files, 1 of 2 import links carry binding, status partly_supported, closest evidence composite `subsys:composite:language:f91cf40d` (overlap 0.667).
- Declared composite `language.2` (hub `aurora_grammar_engine.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite none.
- Declared composite `language.3` (hub `aurora_internal/aurora_communication_emergence.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite `subsys:composite:language:ab4e00b7` (overlap 1.0).

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora_behavioral_identity.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | identity | 0 | consistent |
| `aurora_grammar_engine.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | grammar_engine | 3 | consistent |
| `aurora_internal/aurora_communication_emergence.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | communication_emergence | 0 | consistent |
| `aurora_internal/aurora_conversation_rubric_engine.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_language_state.py` | name_and_docstring | desktop, phone | desktop_boot | - | 3 | consistent |
| `aurora_internal/aurora_lexical_grounding.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | lexical_grounding | 0 | consistent |
| `aurora_internal/aurora_lexical_structure.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_internal/aurora_meaning_evolution.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_semantic_probe_battery.py` | reviewed | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_specialized_avatar_synthesizer.py` | name_and_docstring | desktop, phone | desktop_boot | - | 1 | consistent |
| `aurora_internal/aurora_stance_lexicon.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_internal/aurora_word_use.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_language_field.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | language_field | 0 | consistent |
| `aurora_language_structure_fitness.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_self_grounding.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |

#### Higher order: Learning, dreams and development (`subsys:category:learning`), 43 member(s)

Declared: Training, dreams, curriculum, evolution chambers, curiosity and habitat.

- Evidence composite `subsys:composite:learning:3874e50e`: 3 files, cohesion 0.162, binding {'CALLS': 12, 'FEEDS': 19}. Files: `aurora_internal/aurora_capability_binding.py`, `aurora_internal/aurora_learned_index.py`, `aurora_internal/aurora_learned_rules.py`
- Evidence composite `subsys:composite:learning:680a4391`: 3 files, cohesion 0.028, binding {'INSTANTIATES': 2, 'CALLS': 2, 'SHARED_STATE': 1, 'FEEDS': 1}. Files: `aurora_experiential_sim.py`, `aurora_explore.py`, `aurora_training_pulse.py`
- Evidence composite `subsys:composite:learning:6f24c869`: 4 files, cohesion 0.08, binding {'INSTANTIATES': 2, 'CALLS': 46, 'FEEDS': 32}. Files: `aurora_internal/aurora_code_evolution_chamber.py`, `aurora_internal/aurora_evolution_chamber.py`, `aurora_internal/aurora_evolution_hook.py`, `aurora_internal/aurora_evolved_surfaces.py`
- Evidence composite `subsys:composite:learning:80bafba2`: 4 files, cohesion 0.218, binding {'INSTANTIATES': 4, 'CALLS': 15, 'FEEDS': 48}. Files: `aurora_internal/aurora_dream_curriculum_queue.py`, `aurora_internal/aurora_dream_evolution_orchestrator.py`, `aurora_internal/aurora_dream_genealogy_bridge.py`, `aurora_internal/aurora_episode_slip_profiler.py`
- Evidence composite `subsys:composite:learning:b74d3707`: 2 files, cohesion 0.091, binding {'CALLS': 9, 'INSTANTIATES': 1, 'FEEDS': 12, 'SHARED_STATE': 1}. Files: `aurora_possibility_selves.py`, `aurora_quantum_dream_substrate.py`
- Evidence composite `subsys:composite:learning:f7283074`: 2 files, cohesion 0.014, binding {'CALLS': 2, 'FEEDS': 1}. Files: `aurora_classroom.py`, `aurora_internal/aurora_directed_training_corpus.py`
- Declared composite `learning.1` (hub `aurora_internal/aurora_evolution_chamber.py`): 5 files, 4 of 5 import links carry binding, status partly_supported, closest evidence composite `subsys:composite:learning:6f24c869` (overlap 0.8).
- Declared composite `learning.2` (hub `aurora_dream_trainer.py`): 4 files, 3 of 3 import links carry binding, status supported, closest evidence composite `subsys:composite:learning:f7283074` (overlap 0.5).
- Declared composite `learning.3` (hub `aurora_internal/aurora_dream_evolution_orchestrator.py`): 4 files, 4 of 4 import links carry binding, status supported, closest evidence composite `subsys:composite:learning:80bafba2` (overlap 1.0).
- Declared composite `learning.4` (hub `aurora_training_pulse.py`): 3 files, 2 of 2 import links carry binding, status supported, closest evidence composite `subsys:composite:learning:680a4391` (overlap 1.0).
- Declared composite `learning.5` (hub `aurora_internal/aurora_capability_binding.py`): 3 files, 3 of 3 import links carry binding, status supported, closest evidence composite `subsys:composite:learning:3874e50e` (overlap 1.0).
- Declared composite `learning.6` (hub `aurora_possibility_selves.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite `subsys:composite:learning:b74d3707` (overlap 1.0).

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora_classroom.py` | name_and_docstring | desktop | - | - | 3 | consistent |
| `aurora_curiosity_engine.py` | name_and_docstring | desktop, phone | desktop_turns | - | 1 | consistent |
| `aurora_dream_substrate.py` | name_and_docstring | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `aurora_dream_trainer.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | dream_trainer | 5 | consistent |
| `aurora_evolution_stack.py` | name_and_docstring | - | desktop_boot | - | 0 | consistent |
| `aurora_experiential_sim.py` | name_and_docstring | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `aurora_explore.py` | name_and_docstring | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `aurora_habitat.py` | name_and_docstring | phone | - | habitat | 1 | consistent |
| `aurora_habitat_motivation.py` | name_and_docstring | phone | - | - | 0 | consistent |
| `aurora_internal/aurora_capability_assimilator.py` | name_and_docstring | desktop | - | - | 1 | consistent |
| `aurora_internal/aurora_capability_binding.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_code_autoevolver.py` | name_and_docstring | desktop | desktop_boot | - | 0 | consistent |
| `aurora_internal/aurora_code_evolution_chamber.py` | name_and_docstring | desktop, phone | desktop_boot | code_chamber, code_evolution_chamber | 2 | consistent |
| `aurora_internal/aurora_cognitive_experience_chamber.py` | name_and_docstring | - | - | - | 0 | consistent |
| `aurora_internal/aurora_corpus_lifecycle.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_internal/aurora_development_experiment.py` | name_and_docstring | - | - | - | 2 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `aurora_internal/aurora_developmental_ecology.py` | name_and_docstring | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `aurora_internal/aurora_directed_training_corpus.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 1 | consistent |
| `aurora_internal/aurora_dream_curriculum_queue.py` | name_and_docstring | desktop, phone | desktop_boot | - | 1 | consistent |
| `aurora_internal/aurora_dream_evolution_orchestrator.py` | name_and_docstring | desktop, phone | desktop_boot | dream_orchestrator | 0 | consistent |
| `aurora_internal/aurora_dream_genealogy_bridge.py` | name_and_docstring | desktop, phone | desktop_boot | - | 1 | consistent |
| `aurora_internal/aurora_episode_slip_profiler.py` | reviewed | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_internal/aurora_evolution_chamber.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | chamber | 2 | consistent |
| `aurora_internal/aurora_evolution_hook.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_evolved_surfaces.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | evolved_surfaces | 1 | consistent |
| `aurora_internal/aurora_general_execution_foundry.py` | name_and_docstring | desktop, phone | desktop_boot | general_execution_foundry | 0 | consistent |
| `aurora_internal/aurora_learned_index.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_learned_rules.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_learning_pipeline.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_internal/aurora_second_gen.py` | name_and_docstring | desktop | - | - | 0 | consistent |
| `aurora_internal/aurora_variant_promotion.py` | name_and_docstring | desktop, phone | desktop_boot | variant_promoter | 0 | consistent |
| `aurora_internal/lesson_replay.py` | name_and_docstring | - | - | - | 0 | consistent |
| `aurora_learning_probe.py` (also) | reviewed | phone | - | learning_probe | 1 | consistent |
| `aurora_possibility_selves.py` | name_and_docstring | desktop, phone | - | - | 4 | consistent |
| `aurora_quantum_dream_substrate.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_reasoning_games.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_response_teacher.py` | name_and_docstring | desktop, phone | - | response_teacher | 1 | consistent |
| `aurora_training_pulse.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_training_run.py` | name_and_docstring | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `aurora_vocabulary_seed_apply.py` | name_and_docstring | phone | - | - | 0 | consistent |
| `backfill_concept_associations.py` | name_and_docstring | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `constraint_evolutionary_sim.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `run_intensive_intervals.py` | name_and_docstring | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |

#### Higher order: Memory (`subsys:category:memory`), 12 member(s)

Declared: SediMemory, working and interaction memory, turn and resolution records.

- Declared composite `memory.1` (hub `aurora_interaction_memory.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite none.

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora_developmental_log.py` | name_and_docstring | desktop, phone | desktop_turns | - | 1 | consistent |
| `aurora_interaction_memory.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 1 | consistent |
| `aurora_internal/aurora_conversation_episode_compiler.py` | name_and_docstring | desktop, phone | desktop_boot | - | 2 | consistent |
| `aurora_internal/aurora_difference_buffer.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_resolution_ledger.py` | name_and_docstring | desktop, phone | desktop_turns | resolution_ledger | 0 | consistent |
| `aurora_internal/aurora_solidification.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | solidification | 0 | consistent |
| `aurora_internal/aurora_turn_persistence.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_sedimemory.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | sedimemory | 0 | consistent |
| `aurora_turn_ledger.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_understanding_sediment.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 2 | consistent |
| `aurora_working_memory.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | working_memory | 0 | consistent |
| `geological_baseline.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |

#### Higher order: Perception and expression (`subsys:category:perception`), 23 member(s)

Declared: Sensory and hardware IO, intake, utterance parsing, expression and the reply well-formedness gate.

- Evidence composite `subsys:composite:perception:ab562dfd`: 7 files, cohesion 0.066, binding {'INSTANTIATES': 11, 'CALLS': 32, 'FEEDS': 31, 'SHARED_STATE': 4}. Files: `aurora_articulation.py`, `aurora_concept_imager.py`, `aurora_expression_perception.py`, `aurora_hardware_io.py`, `aurora_image_ingestion.py`, `aurora_internal/aurora_pf1_5_instruments.py`, `aurora_vision_clustering.py`
- Declared composite `perception.1` (hub `aurora_expression_perception.py`): 9 files, 8 of 10 import links carry binding, status partly_supported, closest evidence composite `subsys:composite:perception:ab562dfd` (overlap 0.6).

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora_articulation.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 1 | consistent |
| `aurora_concept_imager.py` | name_and_docstring | desktop | - | - | 1 | consistent |
| `aurora_emergence_surface.py` | name_and_docstring | desktop | desktop_boot | - | 3 | consistent |
| `aurora_expression_perception.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | perception | 10 | consistent |
| `aurora_hardware_io.py` | name_and_docstring | desktop, phone | desktop_boot | hardware, sensory, sensory_integration | 3 | consistent |
| `aurora_image_ingestion.py` | name_and_docstring | desktop, phone | desktop_boot | vision_bootstrap | 1 | consistent |
| `aurora_internal/aurora_input_identity.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_input_pressure.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_intake_metabolism.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | metabolizer | 0 | consistent |
| `aurora_internal/aurora_live_experience.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_pf1_5_instruments.py` | reviewed | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_response_pressure_tuner.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_sender_state.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_turn_parse_cache.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_utterance_parser.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_live_vision.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | screen_observer | 1 | consistent |
| `aurora_perception_primitives.py` | name_and_docstring | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_sensory_fallback.py` | name_and_docstring | - | - | - | 0 | consistent |
| `aurora_streaming_expression.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_vision_clustering.py` | name_and_docstring | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_voice.py` | name_and_docstring | desktop, phone | - | - | 5 | consistent |
| `aurora_voice_gate.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | addressed_pressure | 1 | consistent |
| `termux_voice_bridge.sh` | location | - | - | - | 0 | - |

#### Higher order: Reasoning and understanding (`subsys:category:reasoning`), 43 member(s)

Declared: Representational resolution, propositions, the causal reasoning waveform, comparison and understanding.

- Evidence composite `subsys:composite:reasoning:53271342`: 2 files, cohesion 0.061, binding {'CALLS': 10, 'FEEDS': 18}. Files: `aurora_internal/aurora_confluence.py`, `aurora_internal/aurora_propositional_understanding.py`
- Evidence composite `subsys:composite:reasoning:7255ef84`: 2 files, cohesion 0.05, binding {'CALLS': 2, 'FEEDS': 4}. Files: `aurora_internal/aurora_contradiction_perception.py`, `aurora_internal/aurora_relation_pairs.py`
- Evidence composite `subsys:composite:reasoning:7b47d38a`: 4 files, cohesion 0.051, binding {'CALLS': 3, 'FEEDS': 13, 'INSTANTIATES': 2}. Files: `aurora_internal/aurora_entropy_detector.py`, `aurora_internal/aurora_operator_composer.py`, `aurora_internal/aurora_strategic_horizon.py`, `aurora_internal/aurora_worth_evaluator.py`
- Evidence composite `subsys:composite:reasoning:929f8dd5`: 7 files, cohesion 0.205, binding {'INHERITS': 1, 'CALLS': 88, 'FEEDS': 194, 'SHARED_STATE': 12, 'INSTANTIATES': 3}. Files: `aurora_internal/aurora_live_possibility_frontier.py`, `aurora_reflexive_interpreter.py`, `aurora_representational_address.py`, `aurora_representational_resolution.py`, `aurora_representational_resolution_base.py`, `aurora_thought_formation.py`, `aurora_waveform_pressure.py`
- Evidence composite `subsys:composite:reasoning:b1415b0b`: 4 files, cohesion 0.075, binding {'CALLS': 13, 'FEEDS': 28}. Files: `aurora_boundary_hypothesis.py`, `aurora_internal/aurora_comprehension_gap.py`, `aurora_internal/aurora_constraint_semantic_continuity.py`, `aurora_internal/aurora_recursive_causal_reasoning_waveform.py`
- Declared composite `reasoning.1` (hub `aurora_representational_address.py`): 8 files, 8 of 8 import links carry binding, status supported, closest evidence composite `subsys:composite:reasoning:929f8dd5` (overlap 0.875).
- Declared composite `reasoning.2` (hub `aurora_internal/aurora_constraint_semantic_continuity.py`): 5 files, 3 of 4 import links carry binding, status partly_supported, closest evidence composite `subsys:composite:reasoning:b1415b0b` (overlap 0.8).
- Declared composite `reasoning.3` (hub `aurora_internal/aurora_strategic_horizon.py`): 4 files, 3 of 3 import links carry binding, status supported, closest evidence composite `subsys:composite:reasoning:7b47d38a` (overlap 1.0).
- Declared composite `reasoning.4` (hub `aurora_internal/aurora_confluence.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite `subsys:composite:reasoning:53271342` (overlap 1.0).
- Declared composite `reasoning.5` (hub `aurora_internal/aurora_contradiction_perception.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite `subsys:composite:reasoning:7255ef84` (overlap 1.0).

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora_boundary_hypothesis.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_concept_derivation.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_constraint_reasoner.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | constraint_reasoner | 0 | consistent |
| `aurora_internal/aurora_attention_engine.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_causal_generation.py` | name_and_docstring | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `aurora_internal/aurora_comprehension_gap.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | comprehension_gap_system | 1 | consistent |
| `aurora_internal/aurora_confluence.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_constraint_semantic_continuity.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_contradiction_perception.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_correspondence_loop.py` | name_and_docstring | desktop | - | - | 3 | consistent |
| `aurora_internal/aurora_cost_diff_score.py` | name_and_docstring | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_internal/aurora_entropy_detector.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | entropy_detector | 0 | consistent |
| `aurora_internal/aurora_frontier_ops.py` | name_and_docstring | - | - | - | 1 | consistent |
| `aurora_internal/aurora_live_possibility_frontier.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_operational_synthesis.py` | name_and_docstring | desktop, phone | desktop_boot | operational_synthesis | 0 | consistent |
| `aurora_internal/aurora_operator_composer.py` | name_and_docstring | desktop, phone | desktop_boot | operator_composer | 0 | consistent |
| `aurora_internal/aurora_primitive_extractor.py` | name_and_docstring | desktop, phone | desktop_boot | primitive_extractor | 0 | consistent |
| `aurora_internal/aurora_primitive_perspective.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | perspective | 1 | consistent |
| `aurora_internal/aurora_proposition_frame.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_proposition_substrate.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_propositional_understanding.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_reasoning_paths.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | reasoning_paths | 2 | consistent |
| `aurora_internal/aurora_recursive_causal_reasoning_waveform.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | recursive_causal_waveform | 1 | consistent |
| `aurora_internal/aurora_reflective_readdressing.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | reflective_readdressing | 0 | consistent |
| `aurora_internal/aurora_relation_pairs.py` | name_and_docstring | desktop, phone | desktop_turns | - | 1 | consistent |
| `aurora_internal/aurora_relational_comparison.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | relational_comparison | 0 | consistent |
| `aurora_internal/aurora_representation_exchange.py` | name_and_docstring | desktop, phone | desktop_turns | representation_exchange | 0 | consistent |
| `aurora_internal/aurora_rubric_influence_graph.py` | name_and_docstring | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_internal/aurora_shadow_state.py` | name_and_docstring | - | - | - | 0 | consistent |
| `aurora_internal/aurora_strategic_horizon.py` | name_and_docstring | desktop, phone | desktop_boot | strategic_horizon | 0 | consistent |
| `aurora_internal/aurora_understanding_contract.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | understanding_contract | 0 | consistent |
| `aurora_internal/aurora_unformed_patterns.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | unformed_patterns | 2 | consistent |
| `aurora_internal/aurora_worth_evaluator.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | worth_eval | 0 | consistent |
| `aurora_referent_hypothesis.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_reflexive_interpreter.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | noncomp_reflexive_interpreter | 0 | consistent |
| `aurora_representational_address.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_representational_resolution.py` | name_and_docstring | desktop, phone | desktop_turns | representational_resolution_engine | 0 | consistent |
| `aurora_representational_resolution_base.py` | name_and_docstring | desktop, phone | desktop_turns | representational_resolution_engine | 0 | consistent |
| `aurora_semantic_intention_bridge.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_thought_formation.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_toroidal_circulation.py` | name_and_docstring | desktop, phone | desktop_turns | - | 2 | consistent |
| `aurora_waveform_pressure.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | pressure_pump | 0 | consistent |
| `reply_aurora.py` (also) | reviewed | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |

#### Higher order: Entry and runtime (`subsys:category:runtime`), 29 member(s)

Declared: Entry points, the turn loop, process orchestration, launchers and service units.

- Evidence composite `subsys:composite:runtime:0414c162`: 5 files, cohesion 0.029, binding {'INSTANTIATES': 4, 'FEEDS': 53, 'CALLS': 9, 'SHARED_STATE': 60}. Files: `aurora.py`, `aurora_daemon.py`, `aurora_internal/aurora_turn_chain.py`, `aurora_runtime.py`, `corpus_runner.py`
- Declared composite `runtime.1` (hub `aurora.py`): 7 files, 6 of 7 import links carry binding, status partly_supported, closest evidence composite `subsys:composite:runtime:0414c162` (overlap 0.714).

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | field_balancer, search_adapter, teaching_engine | 6 | consistent |
| `aurora_daemon.py` | name_and_docstring | desktop | - | - | 48 | consistent |
| `aurora_hub.py` | name_and_docstring | - | - | - | 5 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `aurora_internal/__init__.py` | name_and_docstring | - | desktop_boot | - | 0 | consistent |
| `aurora_internal/aurora_quasiarch_observer.py` (also) | reviewed | desktop, phone | desktop_boot, desktop_turns | quasiarch_observer | 2 | consistent |
| `aurora_internal/aurora_turn_chain.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_turn_compute_graph.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_runtime.py` | name_and_docstring | desktop, phone | desktop_boot | - | 1 | consistent |
| `corpus_runner.py` | name_and_docstring | desktop, phone | desktop_turns | curriculum_tension | 0 | consistent |
| `deploy/aurora-strata-hub.service` | location | - | - | - | 0 | - |
| `deploy/aurora-strata-room.service` | location | - | - | - | 0 | - |
| `deploy/aurora-subsurface.service` | location | - | - | - | 0 | - |
| `deploy/aurora-surface.service` | location | - | - | - | 0 | - |
| `run_aurora.py` | name_and_docstring | desktop | - | - | 0 | consistent |
| `run_chain.py` | name_and_docstring | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `run_corpus.py` | name_and_docstring | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `run_gui_linux_mac.sh` | location | - | - | - | 0 | - |
| `run_gui_windows.bat` | location | - | - | - | 0 | - |
| `scripts/install_systemd_service.sh` | location | - | - | - | 0 | - |
| `scripts/run_aurora.sh` | location | - | - | - | 0 | - |
| `scripts/run_daemon.sh` | location | - | - | - | 0 | - |
| `scripts/run_hub.sh` | location | - | - | - | 0 | - |
| `scripts/run_room.sh` | location | - | - | - | 0 | - |
| `scripts/run_scout_worker.sh` | location | - | - | - | 0 | - |
| `scripts/run_subsurface_daemon.sh` | location | - | - | - | 0 | - |
| `scripts/run_surface_daemon.sh` | location | - | - | - | 0 | - |
| `scripts/windows/install_subsurface_task.ps1` | location | - | - | - | 0 | - |
| `scripts/windows/run_subsurface.bat` | location | - | - | - | 0 | - |
| `start_vector.sh` | location | - | - | - | 0 | - |

#### Higher order: Dual strata (surface and subsurface) (`subsys:category:strata`), 46 member(s)

Declared: The dual-strata package and the surface/subsurface daemons and substrate.

- Evidence composite `subsys:composite:strata:46b5e9ce`: 4 files, cohesion 0.049, binding {'CALLS': 12, 'FEEDS': 14, 'INSTANTIATES': 2}. Files: `aurora_internal/dual_strata/presence_metrics.py`, `aurora_internal/dual_strata/subsurface_presence.py`, `aurora_internal/dual_strata/subsurface_presence_runtime.py`, `aurora_scout_daemon.py`
- Evidence composite `subsys:composite:strata:a8913e4f`: 18 files, cohesion 0.335, binding {'INSTANTIATES': 25, 'CALLS': 106, 'FEEDS': 191}. Files: `aurora_internal/dual_strata/cers_bridge.py`, `aurora_internal/dual_strata/cers_deprecation.py`, `aurora_internal/dual_strata/cers_potential_trial.py`, `aurora_internal/dual_strata/cers_regulator.py`, `aurora_internal/dual_strata/cers_tensor_locator.py`, `aurora_internal/dual_strata/conscious_frame.py`, `aurora_internal/dual_strata/contextual_overlay.py`, `aurora_internal/dual_strata/crest.py`, `aurora_internal/dual_strata/dce_bridge.py`, `aurora_internal/dual_strata/micro_reasoning.py`, `aurora_internal/dual_strata/perturbation_probe.py`, `aurora_internal/dual_strata/prediction_field.py` ...
- Evidence composite `subsys:composite:strata:ef2079cf`: 9 files, cohesion 0.271, binding {'CALLS': 55, 'FEEDS': 75, 'INSTANTIATES': 4, 'SHARED_STATE': 2}. Files: `aurora_internal/dual_strata/predictive_stager.py`, `aurora_internal/dual_strata/sensory_control_channel.py`, `aurora_internal/dual_strata/sensory_observation.py`, `aurora_internal/dual_strata/sensory_snapshot_channel.py`, `aurora_internal/dual_strata/strata_link.py`, `aurora_internal/dual_strata/strata_state_transfer.py`, `aurora_internal/dual_strata/surface_continuity_feed.py`, `aurora_internal/dual_strata/surface_sensory_proxy.py`, `aurora_surface_daemon.py`
- Declared composite `strata.1` (hub `aurora_internal/dual_strata/__init__.py`): 37 files, 58 of 80 import links carry binding, status partly_supported, closest evidence composite `subsys:composite:strata:a8913e4f` (overlap 0.486).
- Declared composite `strata.2` (hub `aurora_internal/aurora_surface_dispatcher.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite none.

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `aurora_braid_wiring.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_braided_substrate.py` | name_and_docstring | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_internal/aurora_surface_dispatcher.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/aurora_surface_doc.py` | reviewed | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_internal/dual_strata/__init__.py` | name_and_docstring | - | desktop_boot | - | 0 | consistent |
| `aurora_internal/dual_strata/activation_field.py` | name_and_docstring | desktop, phone | desktop_boot | - | 1 | consistent |
| `aurora_internal/dual_strata/cers_bridge.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 2 | consistent |
| `aurora_internal/dual_strata/cers_deprecation.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 1 | consistent |
| `aurora_internal/dual_strata/cers_potential_trial.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/dual_strata/cers_regulator.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/dual_strata/cers_tensor_locator.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/dual_strata/conscious_frame.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/dual_strata/contextual_overlay.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/dual_strata/crest.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/dual_strata/dce_bridge.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 2 | consistent |
| `aurora_internal/dual_strata/downward_traversal.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/dual_strata/lifecycle_catalog.py` | name_and_docstring | - | desktop_boot | - | 0 | consistent |
| `aurora_internal/dual_strata/micro_reasoning.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/dual_strata/perturbation_probe.py` | reviewed | desktop, phone | - | - | 0 | consistent |
| `aurora_internal/dual_strata/prediction_field.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/dual_strata/predictive_stager.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 1 | consistent |
| `aurora_internal/dual_strata/presence_metrics.py` | name_and_docstring | desktop, phone | desktop_turns | - | 1 | consistent |
| `aurora_internal/dual_strata/semantic_intention_bridge.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/dual_strata/semantic_variant_registry.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/dual_strata/sensory_control_channel.py` | name_and_docstring | - | - | - | 0 | consistent |
| `aurora_internal/dual_strata/sensory_observation.py` | name_and_docstring | desktop | desktop_boot | - | 2 | consistent |
| `aurora_internal/dual_strata/sensory_snapshot_channel.py` | name_and_docstring | desktop, phone | desktop_turns | - | 0 | consistent |
| `aurora_internal/dual_strata/sleep_cycle.py` | name_and_docstring | desktop | - | - | 0 | consistent |
| `aurora_internal/dual_strata/strata_link.py` | name_and_docstring | desktop, phone | - | strata_link | 0 | consistent |
| `aurora_internal/dual_strata/strata_state_transfer.py` | name_and_docstring | desktop, phone | - | - | 1 | consistent |
| `aurora_internal/dual_strata/subsurface_presence.py` | name_and_docstring | desktop, phone | desktop_turns | - | 6 | consistent |
| `aurora_internal/dual_strata/subsurface_presence_runtime.py` | name_and_docstring | desktop, phone | - | - | 0 | consistent |
| `aurora_internal/dual_strata/subsurface_projection.py` | name_and_docstring | desktop | - | - | 0 | consistent |
| `aurora_internal/dual_strata/subsurface_state.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/dual_strata/subsystem_waveforms.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/dual_strata/surface_channel.py` | name_and_docstring | desktop, phone | desktop_boot | - | 0 | consistent |
| `aurora_internal/dual_strata/surface_continuity_feed.py` | name_and_docstring | desktop, phone | desktop_turns | - | 4 | consistent |
| `aurora_internal/dual_strata/surface_sensory_proxy.py` | name_and_docstring | desktop, phone | - | sensory_crystal | 0 | consistent |
| `aurora_internal/dual_strata/topological_semantic_coordinator.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 1 | consistent |
| `aurora_internal/dual_strata/topology_frame.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 0 | consistent |
| `aurora_internal/dual_strata/topology_tracker.py` | name_and_docstring | desktop, phone | desktop_boot, desktop_turns | - | 1 | consistent |
| `aurora_internal/dual_strata/variant_transition_predictor.py` | name_and_docstring | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `aurora_scout_daemon.py` | name_and_docstring | phone | - | - | 0 | consistent |
| `aurora_subsurface_daemon.py` | name_and_docstring | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `aurora_surface_daemon.py` | name_and_docstring | - | - | - | 4 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/strata_stack.sh` | location | - | - | - | 0 | - |

#### Higher order: Tests (`subsys:category:tests`), 469 member(s)

Declared: The pytest suite. Each test lists the files it exercises.

- Evidence composite `subsys:composite:tests:14c6dc66`: 2 files, cohesion 0.028, binding {'CALLS': 3, 'FEEDS': 1, 'SHARED_STATE': 1}. Files: `tests/test_confluence.py`, `tests/test_propositional_understanding.py`
- Evidence composite `subsys:composite:tests:3898fa35`: 2 files, cohesion 0.016, binding {'CALLS': 2, 'FEEDS': 1}. Files: `tests/test_core_understanding.py`, `tests/test_genealogy_is_event_generated.py`
- Evidence composite `subsys:composite:tests:40dfbc82`: 2 files, cohesion 0.446, binding {'CALLS': 15, 'FEEDS': 10}. Files: `tests/test_communication_bar.py`, `tests/test_communication_emergence.py`
- Evidence composite `subsys:composite:tests:b277a8d4`: 2 files, cohesion 0.095, binding {'CALLS': 2, 'FEEDS': 2}. Files: `tests/test_representation_exchange.py`, `tests/test_resolution_ledger.py`
- Declared composite `tests.1` (hub `tests/test_communication_bar.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite `subsys:composite:tests:40dfbc82` (overlap 1.0).
- Declared composite `tests.2` (hub `tests/test_confluence.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite `subsys:composite:tests:14c6dc66` (overlap 1.0).

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `tests/_engine_integration_test.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/_pipeline_test.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/run_intelligence_test_surface.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/run_interaction_test.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_ability_ancestral_provenance.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_ability_origin_commit_pull.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_abstention_rescue_retry.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_acquisition_observation_framing_and_synthesis_validity.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_afterthought_topic_identity_and_shard_collision_live.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_afterthought_topic_identity_and_shard_collision_repair.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_alignment.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_ambient_audio_feature_handoff.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_ambient_audio_raw_pcm_features.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_ambient_visual_richer_features.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_android_surface_subsurface_reconnection.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_app_bridge_praxis.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_articulation_semantic_strategy.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_asked_thing_and_manner.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_aurora_evolution_hook_equivalence.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_aurora_habitat.py` | location | desktop, phone | - | identity_field, pressure_pump, sedimemory | 0 | consistent |
| `tests/test_autoevolver_syntax_gate.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_b1_1_envelope_shadow.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_baseline_communication_apprenticeship.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_baseline_genealogy.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_battery_relevance_metric.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_boundary_hypothesis_and_vocative_stripping.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_boundary_surface_and_study_trace_regressions.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_bounded_same_turn_evidence_wait.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_bracket_tokens_not_words.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_build694_instrumentation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_build694_required_regression.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_build711_no_external_models.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_build714_resolution_canaries.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_build725_native_semantic_externalization.py` | location | desktop, phone | - | dimensional, perception | 0 | consistent |
| `tests/test_build922_permanent_recognition.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_canonical_noncomp_dimension.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_capability_binding.py` | location | desktop, phone | - | hardware | 0 | consistent |
| `tests/test_categorical_condition_search_admissibility.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_causal_generation_acceptance.py` | location | desktop, phone | - | dimensional, identity_field, perception | 0 | consistent |
| `tests/test_causal_generation_batch_order.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_causal_generation_daemon_concurrency.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_causal_generation_daemon_concurrency_part2.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_causal_generation_duplicate_target_audit.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_causal_generation_infrastructure.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_cers_bridge_tensor_trace_integration.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_cers_conflict_monitoring_veto.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_cers_geometry_deviation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_cers_shadow_error_logging.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_cers_surface_salience.py` | location | - | - | - | 7 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_cers_tensor_locator.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_cers_topology_context.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_ci_segment_dev_index_rolling_cap.py` | location | - | - | - | 2 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_cir_wh_object_slot_guard.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_classroom_behavior_modes_wiring.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_classroom_curriculum_seeding.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_classroom_divergence_cold_start.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_classroom_perspective_rotation_and_watchdog.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_clock_restart_accounting.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_clone_harvest.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_code_evolution_restart_heredity.py` | location | - | - | - | 2 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_cognition_gap_wiring.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_cognitive_experience_causal_evaluator.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_cognitive_experience_counterfactual_transfer.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_cognitive_experience_episode_loop.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_cognitive_experience_expression_fidelity.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_cognitive_experience_promotion_bridge.py` | location | - | - | submit_operational_experience | 0 | consistent |
| `tests/test_cognitive_experience_world_substrate.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_cognitive_stats_telemetry_contract.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_comm_credit_phase0_dead_wiring.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_comm_credit_phase_e_foundations.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_comm_credit_phase_f_core_functions.py` | location | desktop, phone | - | grammar_engine, language_field, perception | 0 | consistent |
| `tests/test_comm_credit_phase_g_live_wiring.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_comm_credit_phase_h_corpus_bridge.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_communication_architecture_repair_directive.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_communication_bar.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_communication_credit_unification.py` | location | desktop, phone | - | grammar_engine, language_field, perception | 0 | consistent |
| `tests/test_communication_emergence.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_communication_integrity_repair.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_composer_relevance_selection.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_compressed_genealogy_state.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_concept_image_ingestion_import.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_concept_imager_cycle.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_confluence.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_consequence_profile_does_not_govern_perception.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_constraint_continuity_across_mutation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_constraint_field_constitutive_behavior.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_constraint_manifold_prerequisites.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_constraint_semantic_continuity.py` | location | desktop, phone | - | system_introspection | 0 | consistent |
| `tests/test_conversation_desktop.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_core_understanding.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_correspondence_loop.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_cpm.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_crest_compression_placeholder_guard.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_cross_generational_representational_recombination.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_crystal_associations.py` | location | - | - | - | 3 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_crystal_convergence.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_crystal_evidence_evolution.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_crystal_facets.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_crystal_grammar.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_crystal_interior.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_crystal_lexicon.py` | location | - | - | - | 3 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_crystal_maturity.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_crystal_promotion.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_crystal_runtime.py` | location | - | - | - | 3 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_crystal_sensory.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_crystal_store.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_crystal_substitutability.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_crystal_unification.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_crystal_waveform_match.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_crystal_weave.py` | location | - | - | - | 4 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_d1_device_path_attribution.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_d2_2_corpus_fragment_nesting.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_d2_2_live_turn_reentrancy_guard.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_d2_3_delivery_boundary_telemetry_rejection.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_d2_4_probe_battery_measures_resp_a.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_d2_condition2_abstain_sanity.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_daemon_classroom_cycle.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_daemon_evidence_grounded_mutation.py` | location | desktop, phone | - | genealogy | 0 | consistent |
| `tests/test_daemon_subsurface_and_ambient.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_der_geometric_time.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_desktop_stack_includes_scout_worker.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_development_experiment.py` | location | - | - | - | 4 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_developmental_ecology_boundary.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_developmental_integration_closure.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_developmental_reachability_canaries.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_direct_address_formulation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_directed_training_corpus_cache_trust.py` | location | - | - | - | 2 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_dmm_thought_intent_derivation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_downward_cascade_memory.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_dream_agency.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_dream_ancestry.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_dream_as_new_experience.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_dream_developmental_writeback.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_dream_evolution_boundary.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_dream_salience_abstraction.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_dream_source_abstraction.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_dream_trainer_genealogy_wiring.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_dual_clock_starvation_preemption.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_emergence_pathway_repairs.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_emitter_crash.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_entropy_reads_the_stimulus.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_episode_to_entity_experience.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_evidence_axes.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_evidence_binding_request_kind_aware.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_evidence_input_impact.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_evidence_journal.py` | location | - | - | - | 8 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_evidence_overheard.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_evidence_pressure_shape.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_evidence_qualification.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_evidence_substrate_boundary.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_evidence_view.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_evolution_chamber_live_driveshaft.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_evolution_hook_override_none_handling.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_evolutionary_ancestry_acquisition.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_f5_register_exploration_plumbing.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_fail_recurrence_novelty.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_failure_shape_tracing.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_fault_instrumentation_injector.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_field_balancer_genealogy_type_repair.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_flow_audit_and_tcl_wiring.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_frame_negated_auxiliary.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_full_reasoning_pipeline.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_function_word_gate_golden.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_genealogy_activity_registry.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_genealogy_atomic_writes.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_genealogy_consequence_profile.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_genealogy_cooccurrence_observatory.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_genealogy_curve_persistence.py` | location | - | - | - | 2 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_genealogy_difference_producer_observatory.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_genealogy_difference_shadow.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_genealogy_environment_dag_preservation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_genealogy_is_event_generated.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_genealogy_operational_integrity.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_genealogy_positive_selection.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_genealogy_processing_reuse.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_genealogy_promotion_dimension_observer.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_genealogy_same_event_correlation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_genealogy_scale_and_orientation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_genealogy_source_freshness.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_genealogy_tag_scan_equivalence.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_general_execution_foundry.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_generation_collapse_regression.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_geological_write.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_golden_transcript_validation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_governance_liveness.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_governor_and_allocation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_grammar_motif_depletion_check.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_habitat_compressed_motivation_state.py` | location | - | - | - | 2 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_habitat_discovery_canary_build717.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_habitat_motivation_build717.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_habitat_self_and_shared_canaries_build717.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_heard_vs_produced_learning.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_hereditary_closure.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_historical_experience_compressed_state.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_historical_experience_environment.py` | location | desktop, phone | - | aurora, dimensional | 3 | consistent |
| `tests/test_historical_lexical_consequence_attribution.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_historical_rehearsal.py` | location | desktop, phone | - | aurora_module, understanding_contract | 0 | consistent |
| `tests/test_hypothesis_crystals.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_i_state_channel_reweighting.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_i_state_occurrence_wavefront.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_icc_ledger.py` | location | - | - | - | 4 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_identity_and_asked_predicate.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_identity_field_internal_signals.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_ifelse_synthesis_primitive.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_input_as_pressure.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_input_effect_shadow.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_input_identity.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_interaction_event_action_handoff.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_internal_origin_exempt.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_interpreted_turn_packet.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_interpreted_turn_scout_boundary.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_irreducibility.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_ivm_lattice_live_driveshaft.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_l1_skeleton_validity_gate.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_l2_pos_gating.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_l3_conjugation_wiring.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_l3b_determiner_preposition_slots.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_l4_grounded_motif_fitness.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_layer_acyclicity.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_layer_module_ownership_categories.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_learned_order_rules.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_learning_probe.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_lesson_replay.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_lexical_structure.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_lexical_waveform_trials.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_lifecycle_catalog.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_lineage_runtime_activation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_lineage_scoped_pressure.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_live_axis_magnitudes.py` | location | desktop, phone | - | identity_field | 0 | consistent |
| `tests/test_live_communicative_baseline.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_live_possibility_frontier.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_live_possibility_isolation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_live_possibility_king_authority.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_live_turn_parse_cache.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_live_turn_smoke.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_low_fail_positive_gap_fill.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_m1_1a_relation_pairs.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_m1_2_provenance_hygiene.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_manifold_depth_score_reuse.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_metabolic_clock.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_metabolic_steps.py` | location | desktop, phone | - | lattice, metabolic_clock | 0 | consistent |
| `tests/test_mobile_developmental_health_surface.py` | location | desktop, phone | - | lattice, recursive_causal_waveform, sensory_crystal | 0 | consistent |
| `tests/test_mobile_presence_runtime_startup.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_mobile_scout_worker_startup.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_mobile_tools_aurora.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_modulation_event_representational_ref.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_mtsl_acceptance_report.py` | location | - | - | - | 2 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_mtsl_live_wiring.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_mtsl_perturbation_live_wiring.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_mtsl_phase0_plumbing.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_mtsl_phase7_extensions.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_mtsl_warp_gap_proposal.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_multi_sentence_claim_boundary_and_input_echo_live.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_multi_sentence_claim_boundary_and_input_echo_repair.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_n21_hardened_reacceptance.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_n3_correspondence_daemon_wiring.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_native_intermediate_resolution_audit.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_native_motivation_binding_build723.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_native_representational_inquiry_experimentation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_native_representational_selection.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_native_surface_projection_scope_reconciliation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_nc1_noncomp_population.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_nc2_strengthen_cascade.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_no_artificial_fail_generation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_no_hardcoded_evolutionary_answer_key.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_no_representational_selection_learning.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_no_speculative_d3.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_oets.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_oets_comprehension_confidence_growth.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_oets_conf.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_one_reading_one_observation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_one_speech_path.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_operation_level_mutation_identity.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_operational_synthesis_chamber.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_operator_composer.py` | location | - | - | - | 8 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_orientation_reaches_selector.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_p1_st2_stance_lexicon.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_p1_track_cp_contradiction.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_p2_1_density_confidence.py` | location | desktop, phone | - | sedimemory | 0 | consistent |
| `tests/test_p2_2_density_stance_blend.py` | location | desktop, phone | - | sedimemory, working_memory | 0 | consistent |
| `tests/test_p2_3_stance_composer_wiring.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_perception_evolution_boundary.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_perspective_before_resolution.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_perspective_live_birth.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_perspective_merge_repair.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_perspective_representation_birth.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_perturbation_probe.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_pf1_1_proposition_frame.py` | location | desktop, phone | - | working_memory | 0 | consistent |
| `tests/test_pf1_2_transport.py` | location | desktop, phone | - | perception | 0 | consistent |
| `tests/test_pf1_3_motif_selection.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_pf1_4_slot_binding.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_pf1_5_instruments.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_pf3_1_carryover_isolation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_pf3_1_cooccurrence_hub_leak.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_pf3_1_frame_staleness.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_pf3_2_pronoun_consumer_split.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_pf3_3_descriptor_neighborhood.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_pf3_3_frame_absence.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_pf3_4a_motif_thinning_guard.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_pf3_5_motif_watch_readout.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_phone_load_pacing.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_pipeline2.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_positive_dream_material.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_praxis_contract_fence.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_praxis_initiative.py` | location | desktop, phone | - | understanding_contract | 0 | consistent |
| `tests/test_praxis_messenger.py` | location | desktop, phone | - | grammar_engine | 0 | consistent |
| `tests/test_praxis_physics_routing.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_praxis_same_device_loop.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_praxis_shared_state_and_discovery.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_prediction_field_manifold.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_preoutcome_pressure_capture.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_presence_metrics.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_presence_runtime_occurrence_barrier.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_pressure_ledger_restart_continuity.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_primitive_perspective.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_produced_ingest_not_heard.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_progressive_perspective_consumption.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_projection_frontier_consumption.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_promotion_lookup_scaling.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_propositional_understanding.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_provenance_integrity.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_prune_recall_marker_nodes.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_ps1_2_persistence_arbitration.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_qualified_promotion.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_quasiarch_development_inquiry.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_rank6_falsification.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_rcec_closed_loop_orchestrator.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_rcec_mechanism_coherence_and_ingestion.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_rcec_state_isolation_and_lifecycle.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_reasoning_paths.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_recall_markers_not_words.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_recall_no_stored_utterance.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_receiver_loop.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_recommendation_hub_incremental.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_recurring_issue_scout_dispatch.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_recursive_causal_reasoning_waveform.py` | location | desktop, phone | - | system_introspection, understanding_contract | 0 | consistent |
| `tests/test_reflective_introspection_misrouting_live.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_reflective_introspection_misrouting_repair.py` | location | desktop, phone | - | system_introspection | 0 | consistent |
| `tests/test_reflective_readdressing.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_reflexive_interpreter_deposition_integration.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_reflexive_interpreter_sedimemory_boot_wiring.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_reflexive_interpreter_slotcoord_derivation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_rehearsal_both_positions.py` | location | desktop, phone | - | understanding_contract | 0 | consistent |
| `tests/test_rehearsal_demonstration.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_rehearsal_every_comparison_teaches.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_relation_typing_probe_extension.py` | location | desktop, phone | - | operational_synthesis | 0 | consistent |
| `tests/test_relational_promotion_jurisdiction_repair.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_representation_adoption.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_representation_crystals.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_representation_exchange.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_representation_index_change_aware.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_representation_inquiry_causal_integrity.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_representational_addressability.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_representational_canary.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_representational_consequence_binding.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_representational_conservation_negative_guards.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_representational_consumer_audit_build717.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_representational_cross_system_integration.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_representational_divergence_canaries.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_representational_emergence_observatory.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_representational_existence_gate.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_representational_form_gating.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_representational_inquiry_lifecycle_repairs.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_representational_live_propagation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_representational_persistence.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_representational_resolution_build714.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_representational_restart_replay.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_representational_unresolved_fields.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_resolution_ledger.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_response_articulation_authority.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_response_fit_automatic_dispatch.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_response_fit_graduation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_response_fit_scout_requires_interpretation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_response_formation_consumes_scout_evidence.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_rest_accounting_properties.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_rest_ledger.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_retained_learning_bank_strategy_filter.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_rich_fail_stream.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_round.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_runtime_fault_lived_consequence.py` | location | desktop, phone | - | sedimemory | 0 | consistent |
| `tests/test_runtime_hardening.py` | location | - | - | - | 2 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_runtime_lineage_connection.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_rw3_quasiarch_consult_loop.py` | location | - | - | - | 2 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_rw4_relation_to_self.py` | location | desktop, phone | - | collective, identity_field | 0 | consistent |
| `tests/test_rw5_boot_parity.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_rw6c_track1_wiring.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_rw7_attribution_trace.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_same_name_cross_module_independence.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_scaffolding_not_heard.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_scheduled_run_state_persistence.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_scheduler_balance.py` | location | - | - | - | 2 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_scout_backends.py` | location | - | - | - | 2 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_scout_broker.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_scout_contracts.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_scout_evidence_early_ingestion.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_scout_never_writes_cognitive_state.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_scout_presence_load_comparison.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_scout_report_routes_only_to_subsurface.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_scout_resource_budget.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_scout_worker.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_sedimemory_d2_625.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_sedimemory_representational_ref.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_semantic_bridge_live_state.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_semantic_intention_bridge.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_semantic_probe_battery.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_semantic_variant_registry.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_sender_agency.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_sensory_citizenship_followup.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_sensory_consequence_circuit_repairs.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_sensory_genealogy_and_evolution_wiring.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_sensory_learned_axis_participation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_sensory_representational_citizenship.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_shadow_state_utility.py` | location | - | - | - | 10 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_social_corroboration.py` | location | desktop, phone | - | contradiction_ledger | 0 | consistent |
| `tests/test_stale_scout_report_cannot_hijack_new_turn.py` | location | - | - | - | 2 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_stimulus_pressure_seams.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_strata_link.py` | location | - | - | - | 4 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_strata_state_transfer.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_strategic_horizon.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_stratified_wellformedness.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_subsurface_live_presence.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_subsurface_presence_during_scout_delay.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_subsurface_presence_runtime.py` | location | - | - | - | 2 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_subsurface_presence_wiring.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_subsurface_scout_bridge.py` | location | - | - | - | 2 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_supposed_stays_supposed.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_surface_boundary.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_surface_does_not_wait_for_scout.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_surface_poedex_dispatch.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_surface_scout_evidence_harvest.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_system_introspection_bridge.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_tensor_downward_modulation.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_thought_downward.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_topological_semantic_coordinator.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_topology_cycle_decomposition.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_topology_frame.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_topology_tracker.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_toroidal_circulation_layer.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_turn_compute_graph.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_turn_write_behind.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_ui_observation_journal.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_undefined_names_in_live_paths.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_understanding_genealogy_preservation.py` | location | desktop, phone | - | genealogy | 0 | consistent |
| `tests/test_understanding_sediment_overlay.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_unformed_patterns.py` | location | - | - | covers, misses | 0 | consistent |
| `tests/test_universal_function_lineage.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_universal_function_lineage_freshness_fast_path.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_unknown_provenance.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_up.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_variant_transition_predictor.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_verify_lesson.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_voice_gate.py` | location | desktop, phone | - | pressure_pump | 1 | consistent |
| `tests/test_w1_turn_content_context.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_w2_claim_gate_widening.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_warp_phase1_resonance_graph.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_warp_phase2_confession_calls.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_warp_phase3a_language_field_confession.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_warp_phase3b_resonant_lookup_confession.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_warp_phase3c_memory_recall_confession.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_warp_phase3d_parse_confidence_confession.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_warp_phase4_resonant_trial_lifecycle.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_waveform_pressure.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_word_use.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_zip_active_turn_state_frame_source.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_zip_directed_training_fitness_gate.py` | location | desktop, phone | - | simulation | 0 | consistent |
| `tests/test_zip_gap_research_router.py` | location | desktop, phone | - | conversation_memory | 0 | consistent |
| `tests/test_zip_integration_b_standalone_fixes.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `tests/test_zip_pipeline_learning_oets_promotion.py` | location | desktop, phone | - | conversation_memory | 0 | consistent |
| `tests/test_zip_semantic_intention_reset.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |

#### Higher order: Scripts, tooling and prototypes (`subsys:category:tooling`), 88 member(s)

Declared: Maintenance, audit, migration and analysis scripts, and the HTML and JSX prototypes.

- Evidence composite `subsys:composite:tooling:1128286a`: 2 files, cohesion 0.098, binding {'CALLS': 3, 'FEEDS': 1, 'SHARED_STATE': 2}. Files: `scripts/seed_abstract_regions_s1.py`, `scripts/seed_oets_aurora_vocabulary.py`
- Evidence composite `subsys:composite:tooling:f81153a5`: 2 files, cohesion 0.081, binding {'CALLS': 2, 'FEEDS': 6, 'SHARED_STATE': 2}. Files: `scripts/analyze_cross_generational_representations.py`, `scripts/analyze_native_representation_inquiries.py`

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `constraint_prototype.html` | location | - | - | - | 0 | - |
| `constraint_prototype.jsx` | location | - | - | - | 0 | - |
| `reply_aurora.py` | reviewed | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/analyze_cross_generational_representations.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/analyze_native_representation_inquiries.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/append_to_doc.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/apply_vocabulary_seed.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/audit_actual_runtime_turn.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/audit_genealogy.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/audit_unified_response_regression.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/aurora_ci_segment.py` | location | - | - | - | 4 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/aurora_cold_archive.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/aurora_fault_instrumentation_injector.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/aurora_kg_observe.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/aurora_knowledge_graph.py` | location | - | - | - | 6 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/aurora_stack_exporter.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/aurora_state_compress.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/backfill_noncomp_and_relations.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/baseline_genealogy.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/bridge_ledger_to_noncomps.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/bridge_tensor_occupancy_to_warp.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/chain_dossier_codec.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/characterize_pf16_residue.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/chat_daemon.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/chatscriber.py` | location | - | - | - | 3 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/clean_corpus.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/compare_architectures.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/compare_genealogy_equivalence.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/compile_universal_function_lineage.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/generate_nc_lineage_docs.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/greeting_exposure_experiment.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/inject_math_forms_v2.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/m1_1a_tier1_backfill.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/m1_2_provenance_hygiene.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/m1_3_v0_rerun.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/map_turn_information_flow.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/measure_crystal_associations.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/measure_crystal_convergence.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/measure_crystal_facets.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/measure_crystal_grammar.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/measure_crystal_maturity.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/measure_crystal_promotion.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/measure_crystal_substitutability.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/measure_crystal_weave.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/measure_dream_ancestry.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/measure_evidence_journal.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/measure_input_attribution.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/measure_input_impact.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/measure_quasiarch_inquiry.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/measure_stream_provenance.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/measure_turn_baseline.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/noncomp_actuation_shadow_audit.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/pf1_0_attribution_run.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/pf1_5_instrument_revalidation.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/pf1_6_acceptance.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/pf3_1_carryover_trace.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/pf3_1_context_keywords_trace.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/pf3_1_frame_staleness_trace.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/pf3_3_descriptor_trace.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/pf3_3_frame_absence_trace.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/pf3_5_motif_watch_readout.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/populate_fgae_semantics.py` | location | - | - | - | 4 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/process_docs.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/prove_learning.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/prune_recall_marker_nodes.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/rcec_canary_cohort.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/rcec_canary_cohort_610.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/rcec_canary_reduced_613.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/render_module_ownership.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/repair_stale_priority_depth.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/resolution_ledger_replay.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/run_growth_session.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/rw7_attribution_run.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/scan_lineage_25x25.py` | location | - | - | - | 12 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/scout_presence_load_comparison.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/seed_abstract_regions_s1.py` | location | - | - | - | 2 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/seed_oets_aurora_vocabulary.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/seed_sensory_crystals.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/source_conversation_corpora.py` | location | - | - | - | 2 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/stamp_authorship_headers.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/teach_lesson.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/termux_voice_bridge.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/trace_live_response_pipeline.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/trial_crystal_writers.py` | location | - | - | - | 1 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/verify_lesson.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/w1_reentrancy_trace.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `scripts/w1_thought_state_diagnostic.py` | location | - | - | - | 0 | unverified: no static production importer, organ or recorded run reaches it (dynamic loading would not show) |
| `session_continuity_manager.html` | location | - | - | - | 0 | - |

### Quasi: Phone app (`subsys:quasi:phone`), 22 base file(s)

Declared: The Flutter app with its Android services and on-device Python.

#### Higher order: Android services (`subsys:category:phone_android`), 6 member(s)

Declared: Kotlin and Java Android components: the main activity, Aurora and overlay services, screen observer and boot receiver.

- Evidence composite `subsys:composite:phone_android:95732a08`: 2 files, cohesion 0.667, binding {'CALLS': 13, 'SPAWNS': 1}. Files: `flutter_app/android/app/src/main/kotlin/org/aurora/app/AuroraService.kt`, `flutter_app/android/app/src/main/kotlin/org/aurora/app/MainActivity.kt`
- Declared composite `phone_android.1` (hub `flutter_app/android/app/src/main/kotlin/org/aurora/app/AuroraService.kt`): 5 files, 5 of 5 import links carry binding, status supported, closest evidence composite `subsys:composite:phone_android:95732a08` (overlap 0.4).

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `flutter_app/android/app/src/main/kotlin/org/aurora/app/AuroraService.kt` | location | - | - | - | 0 | - |
| `flutter_app/android/app/src/main/kotlin/org/aurora/app/BootCompletedReceiver.kt` | location | - | - | - | 0 | - |
| `flutter_app/android/app/src/main/kotlin/org/aurora/app/MainActivity.kt` | location | - | - | - | 0 | - |
| `flutter_app/android/app/src/main/kotlin/org/aurora/app/OverlayService.kt` | location | - | - | - | 0 | - |
| `flutter_app/android/app/src/main/kotlin/org/aurora/app/ScreenObserverService.kt` | location | - | - | - | 0 | - |
| `src/android/java/org/aurora/OverlayService.java` | location | - | - | - | 0 | - |

#### Higher order: Dart bridges (`subsys:category:phone_bridges`), 2 member(s)

Declared: Dart bridges to her Python stack and to Praxis.

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `flutter_app/lib/aurora_bridge.dart` | location | - | - | - | 0 | - |
| `flutter_app/lib/praxis/praxis_bridge.dart` | location | - | - | - | 0 | - |

#### Higher order: Habitat (`subsys:category:phone_habitat`), 6 member(s)

Declared: The habitat model, renderer, gesture layer and bridge, and the habitat screens.

- Evidence composite `subsys:composite:phone_habitat:a1e0ab56`: 2 files, cohesion 0.316, binding {'CALLS': 6}. Files: `flutter_app/lib/habitat/habitat_bridge.dart`, `flutter_app/lib/habitat/habitat_model.dart`
- Declared composite `phone_habitat.1` (hub `flutter_app/lib/habitat/habitat_gesture_layer.dart`): 6 files, 6 of 7 import links carry binding, status partly_supported, closest evidence composite `subsys:composite:phone_habitat:a1e0ab56` (overlap 0.333).

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `flutter_app/lib/habitat/habitat_bridge.dart` | location | - | - | - | 0 | - |
| `flutter_app/lib/habitat/habitat_gesture_layer.dart` | location | - | - | - | 0 | - |
| `flutter_app/lib/habitat/habitat_model.dart` | location | - | - | - | 0 | - |
| `flutter_app/lib/habitat/habitat_renderer.dart` | location | - | - | - | 0 | - |
| `flutter_app/lib/screens/habitat_self_screen.dart` | location | - | - | - | 0 | - |
| `flutter_app/lib/screens/habitat_space_screen.dart` | location | - | - | - | 0 | - |

#### Higher order: On-device Python (`subsys:category:phone_python`), 3 member(s)

Declared: Python that Chaquopy runs on the phone: the entry bridge, the cv2 shim and the historical experience environment.

- Evidence composite `subsys:composite:phone_python:92d4d84c`: 2 files, cohesion 0.018, binding {'CALLS': 6, 'FEEDS': 7, 'SHARED_STATE': 1}. Files: `flutter_app/android/app/src/main/python/aurora_bridge.py`, `flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py`
- Declared composite `phone_python.1` (hub `flutter_app/android/app/src/main/python/aurora_bridge.py`): 2 files, 1 of 1 import links carry binding, status supported, closest evidence composite `subsys:composite:phone_python:92d4d84c` (overlap 1.0).

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `flutter_app/android/app/src/main/python/aurora_bridge.py` | reviewed | phone | - | device_embodiment | 11 | consistent |
| `flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py` | reviewed | phone | - | historical_experience | 1 | consistent |
| `flutter_app/android/app/src/main/python/cv2.py` | reviewed | - | - | - | 0 | consistent |

#### Higher order: App shell and screens (`subsys:category:phone_ui`), 5 member(s)

Declared: The Flutter entry point, home and hub screens, overlay entry and the orb widget.

- Evidence composite `subsys:composite:phone_ui:e24ca393`: 2 files, cohesion 0.45, binding {'CALLS': 45}. Files: `flutter_app/lib/screens/home_screen.dart`, `flutter_app/lib/screens/hub_screen.dart`
- Declared composite `phone_ui.1` (hub `flutter_app/lib/main.dart`): 4 files, 1 of 3 import links carry binding, status partly_supported, closest evidence composite `subsys:composite:phone_ui:e24ca393` (overlap 0.5).

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `flutter_app/lib/main.dart` | location | - | - | - | 0 | - |
| `flutter_app/lib/overlay_entry.dart` | location | - | - | - | 0 | - |
| `flutter_app/lib/screens/home_screen.dart` | location | - | - | - | 0 | - |
| `flutter_app/lib/screens/hub_screen.dart` | location | - | - | - | 0 | - |
| `flutter_app/lib/widgets/aurora_orb.dart` | location | - | - | - | 0 | - |

### Quasi: Repository and CI (`subsys:quasi:repo`), 6 base file(s)

Declared: Workflows that build, test and run the other domains.

#### Higher order: CI workflows (`subsys:category:ci`), 6 member(s)

Declared: GitHub Actions workflows for runs, clones, experiments, the APK and Python CI.

| base file | claim basis | reached from | ran in | organs | store writes | check |
|---|---|---|---|---|---:|---|
| `.github/workflows/aurora-autonomous-run.yml` | location | - | - | - | 0 | - |
| `.github/workflows/aurora-clones.yml` | location | - | - | - | 0 | - |
| `.github/workflows/aurora-development-experiment.yml` | location | - | - | - | 0 | - |
| `.github/workflows/build-apk.yml` | location | - | - | - | 0 | - |
| `.github/workflows/flutter-android.yml` | location | - | - | - | 0 | - |
| `.github/workflows/python-ci.yml` | location | - | - | - | 0 | - |

## Composite candidates the record holds back

The record lists these as candidates, not composites, and their files stay base files. Each is checked here like a declared composite, so a candidate whose links gain binding can be promoted.

- `acm_bridge.1` (acm, acm_bridge): 2 files, 0 of 1 import links carry binding, status import_only.
- `acm_core.1` (acm, acm_core): 5 files, 0 of 7 import links carry binding, status import_only.
- `acm_cpm.1` (acm, acm_cpm): 3 files, 0 of 3 import links carry binding, status import_only.
- `tests.3` (desktop, tests): 2 files, 0 of 1 import links carry binding, status import_only.

## Links across domains

52 file pairs in different domains are joined by implemented or observed edges, or meet at one endpoint (method channel, Chaquopy call, HTTP route, frame). The 40 strongest:

| file | file | domains | joined by |
|---|---|---|---|
| `aurora_internal/aurora_runtime_faults.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 77, IMPORTS 1 |
| `concept_crystal.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 22, IMPORTS 1, INSTANTIATES 1 |
| `aurora_habitat.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 12, IMPORTS 1, INSTANTIATES 1 |
| `aurora_internal/dual_strata/strata_link.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 11, IMPORTS 1 |
| `aurora_internal/aurora_constraint_manifold_patched.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | INSTANTIATES 12 |
| `aurora_waveform_pressure.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 8, IMPORTS 1 |
| `aurora_praxis_bridge.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 7, IMPORTS 1 |
| `aurora_praxis_messenger.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 6, IMPORTS 1 |
| `aurora_internal/aurora_lexical_grounding.py` | `flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py` | desktop / phone | CALLS 6, IMPORTS 1 |
| `flutter_app/android/app/src/main/python/aurora_bridge.py` | `geological_baseline.py` | phone / desktop | CALLS 4, IMPORTS 1, INSTANTIATES 1 |
| `aurora_dream_trainer.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 4, IMPORTS 1, INSTANTIATES 1 |
| `aurora_reasoning_games.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 4, IMPORTS 1, INSTANTIATES 1 |
| `constraint_evolutionary_sim.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 3, IMPORTS 1, INSTANTIATES 1 |
| `aurora.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 4, IMPORTS 1 |
| `aurora_internal/dual_strata/sensory_snapshot_channel.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 4, IMPORTS 1 |
| `aurora_language_field.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 2, IMPORTS 1, INSTANTIATES 1 |
| `aurora_internal/aurora_live_experience.py` | `flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py` | desktop / phone | CALLS 3, IMPORTS 1 |
| `aurora_internal/aurora_communication_emergence.py` | `flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py` | desktop / phone | CALLS 4 |
| `aurora_curiosity_engine.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 1, IMPORTS 1, INSTANTIATES 1 |
| `aurora_self_grounding.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 1, IMPORTS 1, INSTANTIATES 1 |
| `aurora_internal/aurora_clone_harvest.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 2, IMPORTS 1 |
| `aurora_learning_probe.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 1, IMPORTS 1, INSTANTIATES 1 |
| `aurora_internal/aurora_sensory_crystal.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 2, IMPORTS 1 |
| `aurora_internal/aurora_turn_persistence.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 2, IMPORTS 1 |
| `aurora_habitat_motivation.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 2, IMPORTS 1 |
| `aurora_internal/lesson_replay.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 2, IMPORTS 1 |
| `aurora_internal/aurora_resolution_ledger.py` | `flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py` | desktop / phone | CALLS 2, IMPORTS 1 |
| `aurora_internal/aurora_reasoning_paths.py` | `flutter_app/android/app/src/main/python/aurora_historical_experience_environment.py` | desktop / phone | CALLS 2, IMPORTS 1 |
| `aurora_internal/aurora_runtime_faults.py` | `flutter_app/android/app/src/main/python/cv2.py` | desktop / phone | CALLS 2, IMPORTS 1 |
| `aurora-acm/native/aurora_acm_native.py` | `foundational_contract.py` | acm / desktop | IMPORTS 1, INSTANTIATES 1 |
| `aurora-acm/native/aurora_acm_native.py` | `aurora_ivm.py` | acm / desktop | IMPORTS 1, INSTANTIATES 1 |
| `aurora-acm/native/aurora_acm_native.py` | `aurora_i_state_beings.py` | acm / desktop | IMPORTS 1, INSTANTIATES 1 |
| `aurora_vocabulary_seed_apply.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 1, IMPORTS 1 |
| `aurora_computational_model.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | IMPORTS 1, INSTANTIATES 1 |
| `aurora_tool_mind.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | IMPORTS 1, INSTANTIATES 1 |
| `aurora_quantum_dream_substrate.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 1, IMPORTS 1 |
| `aurora_scout_daemon.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 1, IMPORTS 1 |
| `aurora_internal/dual_strata/subsurface_presence_runtime.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 1, IMPORTS 1 |
| `aurora_internal/tool_registry.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 1, IMPORTS 1 |
| `aurora_sensory_fallback.py` | `flutter_app/android/app/src/main/python/aurora_bridge.py` | desktop / phone | CALLS 1, IMPORTS 1 |

## Layers and organs

Layers are declared in the ownership mapping; organ groupings come from the code's own implementation registry. Both are listed in `graph/nodes.jsonl` with their members in `graph/edges/MEMBER_OF.jsonl`.

