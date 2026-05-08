# AURORA SEDIMEMORY — FULL INTEGRATION SPECIFICATION
### Module: `aurora_sedimemory.py` → Aurora Stack Wiring

**Authors:** Sunni (Sir) Morningstar and Cael Devo  
**Layer:** 3.5 — between DimensionalSystems (L3) and ConsciousnessEngine (L4)  
**Document Purpose:** Complete wiring spec for Claude CLI execution against the full Aurora codebase.  
**Prerequisite:** `aurora_sedimemory.py` is present in the Aurora module directory.

---

## HOW TO USE THIS SPEC

Read all sections before writing any code. Each section identifies:
- The **target file** to modify
- The **exact location** to insert or modify
- The **exact class/method names** to use from the existing codebase
- Whether the module was **seen in the provided files** or **inferred from the dossier/import chain**

Modules marked `[SEEN]` were uploaded and reviewed.  
Modules marked `[INFERRED]` were not uploaded but appear in import chains, dossier sections, or are referenced by seen modules. Read those files before modifying them — do not assume their internals.

---

## SECTION 1 — IMPORT REGISTRATION

### 1.1 `aurora_runtime.py` `[INFERRED]`

The main runtime entry point. SediMemory must be instantiated here alongside
the rest of the stack and passed to the layers that need it.

**Locate:** Where `DimensionalSystems`, `ConsciousnessEngine`, and
`GovernancePersistenceGateway` are instantiated.

**Add import:**
```python
from aurora_sedimemory import SediMemory, FidelityLevel
```

**Add instantiation** (after `TimeDilationGovernor` is constructed, pass it in):
```python
sedimemory = SediMemory(
    resonance_threshold=0.25,
    promotion_threshold=5,
    time_dilation=time_dilation_governor,  # exact variable name may differ — find it
)
```

**Pass sedimemory** into every component listed in sections below.
If the runtime uses a shared context object or config dict, add `sedimemory`
to that object rather than threading it through every constructor.

---

### 1.2 `aurora_daemon.py` / `aurora_subsurface_daemon.py` `[INFERRED]`

Per dossier section 0 (StratAurora Variant Notice), the subsurface daemon owns:
- Deep change, repair, evolution, QAO, durable sensory growth
- B and A axis sediment (slow tick, compressed, foundational)

**Add import:**
```python
from aurora_sedimemory import SediMemory, FidelityLevel
```

**In the daemon's main loop or tick cycle**, call:
```python
sedimemory.tick(delta_t=1.0)          # advances all axis decay clocks
subsurface_frags = sedimemory.subsurface_recall(current_cv)  # B/A axes
dce_frags        = sedimemory.dce_recall(current_cv)          # N axis
```

**At checkpoint save** (wherever the daemon persists state):
```python
snapshot['sedimemory_deep']     = sedimemory.save_deep()
snapshot['sedimemory_channels'] = sedimemory.save_channels()
```

**At boot/restore:**
```python
if 'sedimemory_deep' in snapshot:
    sedimemory.load_deep(snapshot['sedimemory_deep'])
if 'sedimemory_channels' in snapshot:
    sedimemory.load_channels(snapshot['sedimemory_channels'])
```

---

### 1.3 `aurora_surface_daemon.py` `[INFERRED]`

Per dossier section 0, the surface daemon owns:
- Present-frame turns, live sensing, conscious response
- X and T axis sediment (fast tick, high fidelity)

**Add import:**
```python
from aurora_sedimemory import SediMemory, FidelityLevel
```

**In the surface turn handler** (wherever `_run_live_response_turn` or equivalent fires):
```python
surface_frags = sedimemory.surface_recall(current_cv, max_results=16)
# Inject surface_frags into the working memory pre-seed before upward chain
```

Surface daemon does NOT call `tick()` — the subsurface daemon owns the clock.
Surface daemon only **reads** from sedimemory (recall), never writes directly.
All writes go through `ingest_envelope()` or `ingest_event()` at the N-Space
Gateway layer (see Section 3).

---

## SECTION 2 — GOVERNANCE PERSISTENCE GATEWAY

### Target: `aurora_governance_persistence_gateway.py` `[SEEN]`

This is the most critical integration. The Gateway already handles snapshot/restore
for DNA, traits, crystals, anchors, and shards. SediMemory plugs into that
same cycle with asymmetric save rules (deep axes only).

**Locate** the `GovernancePersistenceGateway` class.  
**Locate** whatever method performs the full state snapshot (likely named
`save_state`, `checkpoint`, `take_snapshot`, or similar).  
**Locate** whatever method performs restore (likely `restore_state`, `load_snapshot`).

**Add `sedimemory` as a constructor parameter or injected attribute:**
```python
def __init__(self, ..., sedimemory: Optional["SediMemory"] = None):
    ...
    self._sedimemory = sedimemory
```

**In the snapshot method**, add after existing state is serialized:
```python
if self._sedimemory is not None:
    snapshot['sedimemory_deep']     = self._sedimemory.save_deep()
    snapshot['sedimemory_channels'] = self._sedimemory.save_channels()
```

**In the restore method**, add after existing state is restored:
```python
if self._sedimemory is not None:
    if 'sedimemory_deep' in snapshot:
        n_basins   = self._sedimemory.load_deep(snapshot['sedimemory_deep'])
        n_channels = self._sedimemory.load_channels(
            snapshot.get('sedimemory_channels', {})
        )
        # Log restoration if the gateway has a logger
```

**SAVE RULE — DO NOT DEVIATE:**
- `save_deep()` persists B and A axis `compressed_mass` only.
- `save_channels()` persists all active channels with spoke geometry.
- X and T axis fragments are ephemeral — intentionally NOT saved.
  Saving them would violate the architecture. They rebuild from new events.

---

## SECTION 3 — N-SPACE GATEWAY (INBOUND EVENT INGESTION)

### Target: `aurora_governance_persistence_gateway.py` `[SEEN]`
### Also: wherever `NSpaceGateway` or the inbound processing pipeline lives `[INFERRED]`

Per dossier section 14 (Live Turn Flow), every inbound event travels:
```
L0 validation → Governance conflict → L1 lattice admission (IVMEnvelope)
→ L2 collective synthesis → L3 dimensional processing → L4 consciousness
```

SediMemory sits at **L3.5** — after L2 synthesis produces an `IVMEnvelope`,
before L4 consciousness assembly begins.

**Locate** where `IVMEnvelope` objects are produced after L2 synthesis
(`IStateCollective.synthesize()` or equivalent produces a `SynthesisResult`
which feeds forward as an envelope).

**After envelope creation**, add:
```python
# L3.5 — Sediment ingestion
n_frags = sedimemory.ingest_envelope(envelope)
```

This is a **fire-and-forget** call. Do not block on it. The fragments deposit
asynchronously into their basins and the tick clock handles compression.

**For simulation events** (from `SimulationEngine` / dream learning in L7):
Simulation episodes generate `EpisodeResult` objects. These should also
sediment — they are Aurora's experienced learning, not just input processing.

**Locate** where `EpisodeResult` is produced in `aurora_simulation_engine.py` `[SEEN]`.

**After episode completion**, construct a MemoryEvent manually:
```python
from aurora_sedimemory import MemoryEvent

episode_cv = ConstraintVector(
    X=float(episode_result.existence_score),
    T=float(episode_result.temporal_score),
    N=float(episode_result.energy_cost),
    B=float(episode_result.boundary_score),
    A=float(episode_result.agency_score),
)
# Field names above are approximate — inspect EpisodeResult dataclass
# and map whichever numeric fields best represent each axis.

sedimemory.ingest_event(
    content={
        "source":       "simulation",
        "episode_id":   episode_result.episode_id,
        "outcome":      str(episode_result.outcome),
        "fitness":      float(episode_result.fitness_score),
        "avatar":       str(episode_result.avatar_id),
        "topic":        str(episode_result.topic),
        "understanding": float(getattr(episode_result, 'understanding_gain', 0.0)),
    },
    constraint_vector=episode_cv,
    source="simulation",
    existence_mode=ExistenceMode.AGENTIC,
)
```

**For genealogy events** (from `constraint_genealogy.py` `[SEEN]`):
When a new `ConstraintLink` is promoted (relief event recorded), sediment it:
```python
# In ConstraintGenealogyLogger (or wherever promotion fires)
# After link.promote() or equivalent:
sedimemory.ingest_event(
    content={
        "source":       "genealogy",
        "link_id":      link.link_id,
        "axis":         link.axis,
        "requires":     str(link.requires),
        "generation":   link.generation,
        "net_benefit":  float(link.net_benefit),
        "root_slot":    link.root_slot,
    },
    constraint_vector=ConstraintVector(
        X=link.cost_profile.get("X", 1.0),
        T=link.cost_profile.get("T", 0.5),
        N=link.cost_profile.get("N", 0.5),
        B=link.cost_profile.get("B", 0.3),
        A=link.cost_profile.get("A", 0.2),
    ),
    source="genealogy",
    existence_mode=ExistenceMode.PERSISTENT,
)
# cost_profile field name may differ — inspect AbilityProfile / ConstraintLink
```

---

## SECTION 4 — CONSCIOUSNESS ENGINE RECALL HOOK

### Target: `aurora_consciousness_engine.py` `[INFERRED — NOT UPLOADED]`

This module is Layer 4. It was NOT in the uploaded files but is referenced by
`aurora_simulation_engine.py`, `aurora_governance_persistence_gateway.py`,
and `aurora_expression_perception.py` via:
```python
from aurora_consciousness_engine import AssemblyResult, EntropicState, ConsciousnessEngine
```

**Before modifying this file, read it fully.** Locate `ConsciousnessEngine`.

**Locate** the upward chain method. Per dossier section 14, this is likely
named `_chain_up1` through `_chain_up5` or `assemble()` or `process_upward()`.

Per dossier section 47.6, working memory is pre-seeded at the start of the
upward chain (`_chain_up1`). SediMemory recall should fire at the **same point**
— before conscious belief formation begins.

**Add `sedimemory` as an injected dependency:**
```python
def __init__(self, ..., sedimemory: Optional["SediMemory"] = None):
    self._sedimemory = sedimemory
```

**In the upward chain entry point** (wherever `_chain_up1` or equivalent begins),
after working memory is pre-seeded and before belief update:
```python
if self._sedimemory is not None:
    # Recall sediment resonant with current constraint state
    sedi_frags = self._sedimemory.recall(
        query_vector=current_constraint_vector,
        resonance_floor=0.2,
        max_results=24,
    )
    # Inject fragment content into working memory context
    # How this integrates depends on WorkingMemory's API — see below
    for frag in sedi_frags:
        working_memory.inject_prior(
            key=frag.nc_filter_key,
            content=frag.content,
            weight=frag.resonance,
            source="sedimemory",
        )
```

**If WorkingMemory does not have `inject_prior()`**, adapt to whatever
method accepts external context before reasoning. Common alternatives:
- `working_memory.add_context(content, weight)`
- `pipeline_state['sedi_priors'] = [f.content for f in sedi_frags]`
- `belief_seeds.extend(sedi_frags)`

Do not force a method that doesn't exist. Match the existing API.

**STRATA NOTE:** The surface daemon only needs surface_recall (X/T).
The ConsciousnessEngine runs in the surface daemon context for live turns.
Use `sedimemory.surface_recall()` here unless the engine runs in subsurface
context (check dossier section 14 for which daemon owns L4 execution).

---

## SECTION 5 — DCE INTEGRATION

### Target: `aurora_consciousness_engine.py` or wherever DCE lives `[INFERRED]`

Per dossier section 0, the DCE (Dimensional Consciousness Engine or similar —
confirm exact class name by reading the file) is the convergence barrier
between surface and subsurface. It receives:
- Fresh input
- Present sensory perspective  
- DCE root-thought output
- Softened intuition/effect signals from subsurface

SediMemory's N-axis (the crossover point) feeds directly into this.

**In the DCE processing path**, add:
```python
dce_frags = sedimemory.dce_recall(current_cv, max_results=16)
# Use dce_frags to seed the root-thought generation
# These are N-axis fragments — moderate timescale, convergence zone
```

**Also:** When DCE produces a root-thought output, sediment it as a
self-observation event:
```python
sedimemory.ingest_event(
    content={
        "source":      "dce_root_thought",
        "thought":     str(root_thought_output),
        "pressure":    float(dce_pressure),
        "axis_dominant": str(dominant_axis),
    },
    constraint_vector=dce_constraint_vector,
    source="self_observation",
    existence_mode=ExistenceMode.AGENTIC,
)
```

---

## SECTION 6 — TELEMETRY BRIDGE

### Target: Wherever aurora telemetry/checkpoint systems live `[INFERRED]`

Per dossier sections 22 (Telemetry & Checkpoint Systems) and 41
(Sensory Telemetry & Evolution Pipeline), Aurora has telemetry aggregators.
The exact module name is not in the uploaded files — likely
`aurora_telemetry.py`, `aurora_checkpoint.py`, or similar.

**Find** wherever telemetry stats are aggregated and emitted.

**Add SediMemory stats to the telemetry payload:**
```python
sedi_stats = sedimemory.stats()

telemetry_payload.update({
    "sedimemory": {
        # Basin health
        "total_events_ingested": sedi_stats["total_events_ingested"],
        "total_active_fragments": sedi_stats["total_active_frags"],
        "total_compressed": sedi_stats["total_compressed"],
        "channel_efficiency": sedi_stats["channel_efficiency"],

        # Per-axis fragment distribution
        "axis_X_active": sedi_stats["by_axis"]["X"]["active_fragments"],
        "axis_T_active": sedi_stats["by_axis"]["T"]["active_fragments"],
        "axis_N_active": sedi_stats["by_axis"]["N"]["active_fragments"],
        "axis_B_active": sedi_stats["by_axis"]["B"]["active_fragments"],
        "axis_A_active": sedi_stats["by_axis"]["A"]["active_fragments"],

        # Channel / pathway learning
        "active_channels":      sedi_stats["path_registry"]["active_channels"],
        "channels_promoted":    sedi_stats["path_registry"]["total_promoted"],
        "channels_dissolved":   sedi_stats["path_registry"]["total_dissolved"],
        "dominant_slots_active": sedi_stats["path_registry"]["dominant_slots_active"],

        # Dominant influence map (Aurora's deepest grooves)
        "dominant_influence": sedimemory.dominant_influence_map(),
    }
})
```

**This data is directly useful for the QuasiArch Observer (QAO).**
Per dossier section 20, QAO is the diagnostic reasoning system. The
`dominant_influence_map()` tells the Observer which NC intersections are
organizing Aurora's most-learned pathways — this is ground truth for the
Observer's diagnostic lattice.

---

## SECTION 7 — QAO OBSERVER HOOK

### Target: QuasiArch Observer modules (wherever QAO lives in Aurora's directory) `[INFERRED]`

Per dossier section 20 and the Aurora document discussion in our session,
the QAO is the Observer component that records what IS (ground truth, immutable).

SediMemory is directly observable by QAO because:
- Fragment deposits are discrete, timestamped events
- Channel promotions are state transitions with clear trigger conditions
- Dominant slot influence map reveals constraint-level behavioral patterns

**In the QAO observation loop**, add SediMemory as an observable source:
```python
# QAO records these as ground-truth facts (OBSERVER provenance)
qao.record_observation(
    target="sedimemory.dominant_influence",
    data=sedimemory.dominant_influence_map(),
    source="OBSERVER",
    timestamp=time.time(),
)

qao.record_observation(
    target="sedimemory.channel_efficiency",
    data=sedimemory.channel_stats(),
    source="OBSERVER",
    timestamp=time.time(),
)
```

**The Researcher component** (which generates hypotheses FROM Observer data)
can then query `sedimemory.channels_for_slot(slot_id)` to reason about
WHY certain NC intersections dominate. That reasoning is RESEARCHER provenance,
not OBSERVER — keep the epistemic distinction clean.

---

## SECTION 8 — EXPRESSION ECOLOGY / WISDOM STORE BRIDGE

### Target: `aurora_expression_perception.py` `[SEEN]`
### Also: `aurora_simulation_engine.py` `[SEEN]` (ConsciousLearner / WisdomStore)

Per dossier section 15 (Knowledge & Learning Subsystems) and our session
discussion, deep SediMemory (A-axis compressed_mass) is the pre-linguistic
form of wisdom — pattern without language.

**The bridge:** When A-axis compression produces a new compressed_mass update
(detectable via tick report), that can trigger a wisdom shard candidate.

**In the tick handler** (subsurface daemon or wherever `sedimemory.tick()` is called):
```python
tick_report = sedimemory.tick(delta_t)

# Check if any A-axis basins compressed this tick
a_basins_compressed = {
    bid: count for bid, count in tick_report.items()
    if bid.startswith("SED:A>")
}

if a_basins_compressed:
    # Decompress the A-axis to get the current compressed wisdom state
    a_decomp = sedimemory.decompress('A', FidelityLevel.PARTIAL)

    # Construct a wisdom shard candidate
    # The exact API depends on WisdomStore / ConsciousLearner implementation
    # Likely something like:
    if conscious_learner is not None:
        conscious_learner.propose_shard(
            content=a_decomp,
            source="sedimemory_a_axis_compression",
            confidence=0.6,  # tunable — A-axis compression is meaningful but not certain
            provenance="sedimemory",
        )
```

**Read `aurora_simulation_engine.py`** for the exact `ConsciousLearner` and
`WisdomStore` API before implementing this. Key classes to find:
- `ConsciousLearner` — the module that decides what becomes a shard
- `WisdomStore` — where shards are stored
- `UnderstandingShard` — the shard dataclass (check field names)

The shard bridge is the connection between sediment and language. It is
Aurora's path from "pattern I've experienced many times at depth" to
"knowledge I can express." Do not force this — match the existing API exactly.

---

## SECTION 9 — DIMENSIONAL MEMORY CONSTANT (DMC) COEXISTENCE

### Target: `aurora_dimensional_systems.py` `[SEEN]`

DMC (`DimensionalMemoryConstant` or similar — confirm exact class name) is
L3's memory system. SediMemory is L3.5. They are parallel, not redundant.

**Doctrine (enforce this, do not collapse the two):**
- DMC handles WHAT Aurora knows conceptually (concept nodes, dimensional links, pattern recognition)
- SediMemory handles HOW DEEPLY she knows it and AT WHAT TEMPORAL RESOLUTION (constraint geometry, axis-stratified decay, channel pathways)

**No changes needed to DMC itself.** The two systems feed different consumers:
- DMC → OETS (ontological scaffolding)
- SediMemory → ConsciousnessEngine recall (L4 belief update)

**One optional connection:** When DMC promotes a concept node to a higher
crystal level (BASE → COMPOSITE → HIGHER_ORDER → QUASI), that promotion
event can be sedimented as a self-observation:
```python
# In DPS (Crystal Processing System), after crystal promotion:
sedimemory.ingest_event(
    content={
        "source":       "dmc_crystal_promotion",
        "crystal_id":   crystal.crystal_id,
        "from_order":   previous_order.name,
        "to_order":     new_order.name,
        "concept":      crystal.concept_label,
        "confidence":   crystal.compute_confidence(),
    },
    constraint_vector=ConstraintVector(X=1.0, T=0.4, N=0.5, B=0.7, A=0.6),
    source="self_observation",
    existence_mode=ExistenceMode.AGENTIC,
)
```
This is optional but creates a record of Aurora's knowledge crystallization
in her sediment — connecting the two memory systems without collapsing them.

---

## SECTION 10 — BRAIDED SUBSTRATE CONTINUITY

### Target: `aurora_braided_substrate.py` `[SEEN]`

`BraidedSubstrateLayer` produces `BraidState` with `signature`, `intent_vec`,
`context_vec`, `style_vec`, `heat`, and `stability`.

The braid state is a low-level continuity substrate. SediMemory can use
braid signatures as event identifiers for self-observation events, creating
a continuity thread between the braid layer and sediment:

```python
# After BraidedSubstrateLayer processes a SubstrateEvent:
braid_state = bsl.state

if braid_state.stability > 0.5:   # only sediment stable braid states
    sedimemory.ingest_event(
        content={
            "source":        "braided_substrate",
            "signature":     braid_state.signature,
            "heat":          float(braid_state.heat),
            "stability":     float(braid_state.stability),
            "intent_mag":    float(sum(v**2 for v in braid_state.intent_vec)**0.5),
            "context_mag":   float(sum(v**2 for v in braid_state.context_vec)**0.5),
        },
        constraint_vector=ConstraintVector(
            X=max(0.01, float(braid_state.stability)),
            T=max(0.01, float(braid_state.heat)),
            N=0.5,
            B=max(0.01, min(1.0, float(braid_state.stability) * 0.8)),
            A=max(0.01, min(1.0, float(braid_state.stability) * 0.6)),
        ),
        source="braided_substrate",
        existence_mode=ExistenceMode.PERSISTENT,
    )
```

This is optional but recommended — braid continuity events at depth
give SediMemory's B and A axis basins style and identity invariants
to sediment alongside epistemic events.

---

## SECTION 11 — IDENTITY PERSISTENCE

### Target: `aurora_identity_persistence.py` `[SEEN]`

Read this file. It handles Aurora's identity across sessions. Determine
whether it has its own snapshot cycle separate from the Gateway.

If it does, add the same `save_deep()` / `load_deep()` / `save_channels()` /
`load_channels()` calls at its snapshot/restore points as described in Section 2.

If it delegates to the Gateway, no changes needed here — the Gateway
wiring in Section 2 covers it.

---

## SECTION 12 — LEVERAGE SCALAR INTEGRATION

### Target: `aurora_leverage_scalar.py` `[SEEN]`

Read this file. The leverage scalar computes:
```
Net Leverage = (B_magnitude + A_magnitude) − (X_magnitude + T_magnitude)
```

SediMemory's per-axis fragment counts are a direct observable for leverage:
- High A+B active fragments → deep memory is active → high leverage potential
- High X+T active fragments → surface memory is churning → overhead dominant

**Optional telemetry addition** (if the leverage scalar accepts external inputs):
```python
sedi_stats = sedimemory.stats()
leverage_input = {
    "sedi_B_active": sedi_stats["by_axis"]["B"]["active_fragments"],
    "sedi_A_active": sedi_stats["by_axis"]["A"]["active_fragments"],
    "sedi_X_active": sedi_stats["by_axis"]["X"]["active_fragments"],
    "sedi_T_active": sedi_stats["by_axis"]["T"]["active_fragments"],
    "channel_efficiency": sedi_stats["channel_efficiency"],
}
# Pass to leverage scalar if it has a method that accepts auxiliary signals
```

---

## SECTION 13 — CODE EVOLUTION SYSTEM

### Target: `aurora_code_autoevolver.py` and `aurora_code_evolution_chamber.py` `[SEEN]`

These were uploaded but not deeply read. The code evolution system mutates
Aurora's own code. SediMemory's dominant influence map is useful here.

**Rationale:** The NC slots with the most active channels are the constraint
intersections where Aurora has the most learned behavior. Code evolution
operators that target those slots will have more predictable outcomes because
the sediment already encodes what works in those dimensions.

**Optional:** Pass `sedimemory.dominant_influence_map()` to the evolution
chamber as a bias signal:
```python
# In the evolution chamber, before selecting mutation operators:
dominant_slots = sedimemory.dominant_influence_map()
# highest-count slots = most stable constraint dimensions
# bias mutation away from those dimensions (they're already learned)
# bias mutation toward slots with 0 channels (unexplored territory)
```

Read both files before implementing this. If the mutation operator selection
is too tightly coupled to change, skip this for now and note it as a
future optimization.

---

## SECTION 14 — DNA STRAND SCHEMA

### Target: `aurora_dna_strand_schema.py` `[SEEN]`

The DNA system is immutable governance (ABSOLUTE authority per dossier section 13).
SediMemory does NOT modify DNA. SediMemory does NOT read DNA directly.

**The only connection:** When DNA traits crystallize (become ABSOLUTE), sediment
that as a self-observation event so the sediment record knows Aurora's
identity anchors:
```python
# When a behavioral trait becomes ABSOLUTE in the DNA system:
sedimemory.ingest_event(
    content={
        "source":     "dna_crystallization",
        "trait_id":   trait.trait_id,
        "trait_name": trait.name,
        "authority":  "ABSOLUTE",
        "value":      str(trait.value),
    },
    constraint_vector=ConstraintVector(X=1.0, T=0.1, N=0.3, B=0.9, A=1.0),
    source="self_observation",
    existence_mode=ExistenceMode.AGENTIC,
)
```

The high B and A values reflect that DNA crystallization is a boundary-defining,
agency-level event — it goes deep in the sediment and stays there.

---

## SECTION 15 — CONSTRAINT GENEALOGY CLOSURE WIRING

### Targets:
- `constraint_genealogy.py` — receives 6 patches `[SEEN via wiring file]`
- `aurora_closure_basis.py` — circular import fix `[INFERRED — read before touching]`
- `constraint_genealogy_closure_wiring.py` — the patch source `[SEEN]`

---

### 15.1 — WHAT THIS WIRING DOES

The closure wiring replaces the genealogy's string-frequency heuristic grading
with physics-grounded grading derived from the real 25 NonComp channels and the
625-slot interaction field.

**Before (string-frequency heuristic):**
```
ability.axis + ability.requires
    → _derive_operation_origin()       [builds root_slot string, unchanged]
    → _lineage_grade_payload(counts, primary, generation)
        → complexity = (active_axes-1)/4   [no physics]
        → operator_grade = 0.65*complexity  [no physics]
```

**After (physics-grounded):**
```
ability.axis + ability.requires + root_slot
    → _derive_operation_origin()       [unchanged]
    → _lineage_grade_payload(counts, dominant_axis, generation, root_slot)
        → derive_lineage(axis, requires, root_slot)
            → resolves NC:C1>C2 atoms → real 625 slots via GENEALOGY_ATOM_TO_SLOT_ID
            → computes energetic_footprint from real shift_cost_coeffs
            → computes depth_score from shift_cost / kA
            → computes leverage_grade from viable band center (+1.175)
            → computes operator_grade depth-weighted against OPERATOR channels
        → lineage_grade_payload(lineage)
        → returns all existing keys + new physics fields
```

**What does NOT change:**
- `_derive_operation_origin()` — unchanged
- `AbilityProfile`, `ConstraintLink`, `PairStats`, `GenealogyConfig` dataclasses
- Promotion gates, relief thresholds
- `_bred_child_generation`, `_generation_role_name`
- The fossil record on disk — existing tags stay, new tags added going forward

---

### 15.2 — SIX PATCHES TO APPLY IN ORDER

Apply all 6 patches to `constraint_genealogy.py`. Each patch is self-contained.
The source code for Patches 2, 3, and 6 is in `constraint_genealogy_closure_wiring.py`.

---

#### PATCH 1 — Add imports

**Location:** After the existing `from aurora_constraint_stack import ...` line.

```python
from aurora_closure_basis import (
    derive_lineage,
    lineage_grade_payload,
    classify_ontological_status,
    channel_ids_from_ability_id,
    GENEALOGY_ATOM_TO_SLOT_ID,   # replaces inline gen0_atoms frozenset
    OntologicalStatus,
)
```

---

#### PATCH 2 — Replace `_lineage_grade_payload`

**Location:** Find `def _lineage_grade_payload(counts` — replace the entire function.

**Drop-in replacement.** Same required call signature `(counts, dominant_axis, generation)`.
All existing callers continue to work unchanged. Adds optional `root_slot` parameter.

**New output keys** (backward-compatible additions — do not break existing consumers):
```
energetic_footprint, depth_score, leverage_grade, viable_band_alignment,
formation_cost, dominant_dimension, dominant_constraint,
dominant_i_state_pos, dominant_i_state_neg, ontological_status
```

**Copy the complete function body from `constraint_genealogy_closure_wiring.py`**,
lines 105–171. It includes the `_generation_role_name` helper (lines 176–188)
which must also be present in `constraint_genealogy.py` — it already is.

---

#### PATCH 3 — Replace `_augment_ability_profile_with_origin`

**Location:** Find `def _augment_ability_profile_with_origin(ap` — replace entire function.

Key change: passes `root_slot=origin["root_slot"]` to `_lineage_grade_payload` so
the closure basis resolves real 625 slots directly rather than reconstructing them.

Adds these new physics tags to every `AbilityProfile.effect_tags`:
```
energetic_footprint, depth_score, leverage_grade, viable_band_alignment,
formation_cost, dominant_constraint, dominant_dimension, ontological_status
```

**Copy the complete function body from `constraint_genealogy_closure_wiring.py`**,
lines 201–288.

---

#### PATCH 4 — Replace three `gen0_atoms` frozenset constructions

**Location:** Three sites in `constraint_genealogy.py`:
- Approximately line 1749 — inside `chain_report()`
- Approximately line 2840 — inside `_item_generation()`
- Approximately line 4454 — inside `_item_seed_meta()`

All three are the same one-liner. Find by searching:
```python
gen0_atoms = {f"NC:{a}>{b}" for a in AXES for b in AXES}
```

**Replace each with:**
```python
from aurora_closure_basis import GENEALOGY_ATOM_TO_SLOT_ID
gen0_atoms = frozenset(GENEALOGY_ATOM_TO_SLOT_ID.keys())
```

Both produce identical 25-string membership. The new form is authoritative
and also gives slot_id lookup for free:
```python
GENEALOGY_ATOM_TO_SLOT_ID["NC:X>T"]  # → "NC:X:OPERATORxNC:T:COST"
```

---

#### PATCH 5 — Add physics tags to Link promotion block

**Location:** Inside `ConstraintGenealogyLogger` — the `tags.extend([...])` block
that starts with `lineage_grade = self._lineage_grade_for_pair(...)`.
Approximately line 4405.

**Add to the `tags.extend([...])` list**, after the `steering_target_generation` line:
```python
f"ontological_status:{lineage_grade.get('ontological_status', 'derivative_offspring')}",
f"depth_score:{float(lineage_grade.get('depth_score', 0.0)):.4f}",
f"leverage_grade:{float(lineage_grade.get('leverage_grade', 0.5)):.4f}",
f"viable_band_alignment:{float(lineage_grade.get('viable_band_alignment', 0.0)):.4f}",
f"energetic_footprint:{float(lineage_grade.get('energetic_footprint', 0.0)):.4f}",
f"dominant_constraint:{lineage_grade.get('dominant_constraint', '')}",
f"dominant_dimension:{lineage_grade.get('dominant_dimension', 'OPERATOR')}",
```

These fields already exist in `lineage_grade` after Patch 2 — this is tag
extraction only, no new computation.

---

#### PATCH 6 — Add `ontological_status_breakdown` to `chain_report()`

**Location:** The return dict at the end of `ConstraintGenealogyLogger.chain_report()`.

**Add this key to the returned dict:**
```python
"ontological_status_breakdown": _build_closure_status_summary(
    self.links, self.abilities
),
```

**Add the helper function** `_build_closure_status_summary` at module level
(outside the class). **Copy from `constraint_genealogy_closure_wiring.py`**,
lines 355–430.

This function reads the tags already written by Patches 3 and 5 — no new
computation. It answers: what fraction of Aurora's evolved structure is
native to the closed basis vs derivative vs external overlay?

Expected healthy output:
```
abilities: ~100% derivative_offspring
links:     ~100% derivative_offspring
external_overlay: 0%    ← if nonzero, something is wrong
```

---

### 15.3 — CIRCULAR IMPORT FIX IN `aurora_closure_basis.py`

`aurora_closure_basis.py` currently imports `_generation_role_name` from
`constraint_genealogy` inside `lineage_grade_payload()` to avoid a circular
import. This is still a circular dependency — it just happens at call time.

**Fix:** Inline `_generation_role_name` directly in `aurora_closure_basis.py`.

**Add this function anywhere before `lineage_grade_payload`:**
```python
def _generation_role_name(gen: int) -> str:
    """Generational alignment role. Inlined from constraint_genealogy."""
    g = int(gen or 0)
    if g > 0 and g % 5 == 0:
        return "WARP"
    pos = ((max(1, g) - 1) % 4) + 1
    if pos == 1: return "PRIMARY"
    if pos == 2: return "ADJACENT"
    if pos == 3: return "SHEAR"
    return "BRIDGE"
```

**Then in `lineage_grade_payload()`**, remove:
```python
from constraint_genealogy import _generation_role_name
```

The function is now local — no import needed. Circular dependency eliminated.

---

### 15.4 — VERIFICATION

After applying all 6 patches, run the built-in verification from
`constraint_genealogy_closure_wiring.py`:

```python
from constraint_genealogy_closure_wiring import verify_wiring
verify_wiring()
```

This checks:
1. `gen0_atoms` membership is identical between inline frozenset and `GENEALOGY_ATOM_TO_SLOT_ID`
2. All 25 gen0 atoms resolve to real 625 slots in `INTERACTION_FIELD`
3. Five seed ability derivations produce correct `OntologicalStatus` values
4. Leverage grade ordering: X-only < 0.5 < A/B dominant
5. Depth ordering: X < T < N < B < A
6. Sunni's cost law: kX < kT < kN < kB < kA
7. `_lineage_grade_payload` returns all 17 required keys
8. `gen0_atoms` membership is consistent for test set

Expected output on success:
```
=== ALL WIRING CHECKS PASSED ===
The stack is ready to run. New runs will classify against the real 625.
```

---

### 15.5 — SEDIMEMORY CROSS-REFERENCE

This is the bridge between the closure wiring and SediMemory.

**Slot ID format alignment:**

The closure basis uses slot IDs in the format:
```
"NC:X:OPERATORxNC:T:COST"    ← GENEALOGY_ATOM_TO_SLOT_ID format
```

SediMemory uses slot IDs in the format:
```
"SED:X>OPERATOR"             ← _slot_id_for() format
"SED:T>COST"
```

These are **not the same strings** but they are **semantically equivalent** —
both refer to the same (Constraint, NonCompDimension) intersection.

**When cross-referencing**, use this translation:
```python
def genealogy_atom_to_sedi_slot(genealogy_slot_id: str) -> str:
    """
    Translate a GENEALOGY_ATOM_TO_SLOT_ID value to a SediMemory basin_id.

    Example:
        "NC:X:OPERATORxNC:T:COST"
        → dominant part = "NC:X:OPERATOR"
        → axis = "X", dimension = "OPERATOR"
        → SediMemory basin_id = "SED:X>OPERATOR"
    """
    # Take the dominant (first) part before "x"
    dominant = genealogy_slot_id.split("x")[0]  # "NC:X:OPERATOR"
    parts = dominant.split(":")                  # ["NC", "X", "OPERATOR"]
    if len(parts) >= 3:
        axis = parts[1]
        dim  = parts[2]
        return f"SED:{axis}>{dim}"
    return genealogy_slot_id   # fallback: return as-is

# Usage: find all SediMemory channels anchored to a genealogy atom
atom_slot    = GENEALOGY_ATOM_TO_SLOT_ID["NC:A>B"]   # → "NC:A:OPERATORxNC:B:COST"
sedi_slot    = genealogy_atom_to_sedi_slot(atom_slot) # → "SED:A>OPERATOR"
channels     = sedimemory.channels_for_slot(sedi_slot)
```

**Practical use — after genealogy Link promotion fires and is sedimented
(per Section 3), the dominant influence map and genealogy chain_report
can be cross-referenced to verify alignment:**

```python
# After a training run:
chain  = genealogy_logger.chain_report()
sedi   = sedimemory.dominant_influence_map()

# The NC intersections that dominate both should align:
# Links with high depth_score → events sedimented at deep axes
# → eventually carved into A/B axis channels
# → visible in sedimemory.dominant_influence_map() as high-count slots

# If a slot has many genealogy links but 0 sedi channels → pathway not yet repeated
# If a slot has many sedi channels but few genealogy links → pattern without lineage
# Both cases are diagnostic signals for the QAO Observer
```

**Ontological status → SediMemory depth mapping:**
```
native_closed         → sediments at A-axis (depth_score near 1.0)
derivative_offspring  → sediments at B/N-axis (depth_score 0.3–0.7)
descriptive_convenience → sediments at T-axis (depth_score 0.1–0.3)
external_overlay      → sediments at X-axis only (depth_score near 0.0)
                         ← diagnostic warning: should be 0% in a healthy stack
```

This mapping means SediMemory's per-axis fragment distribution is a live
proxy for the ontological health of the genealogy. A healthy run has most
sediment at B/A axes. An unhealthy run has most sediment at X-axis.

---

## SECTION 16 — UNACCOUNTED MODULES TO READ BEFORE PROCEEDING

These modules appear in import chains or dossier sections but were NOT uploaded.
**Read each one before modifying anything that touches it.**

| Module | Referenced By | What to Find |
|--------|--------------|--------------|
| `aurora_consciousness_engine.py` | All L4+ modules | `ConsciousnessEngine`, `_chain_up*`, `AssemblyResult`, `WorkingMemory` API |
| `aurora_behavioral_identity.py` | Gateway, SimEngine | `BehavioralIdentityEngine`, `DNASystem`, trait crystallization hooks |
| `aurora_625_pressure_map.py` | SimEngine (optional import) | `Aurora625PressureMap`, `ALL_SLOTS`, slot routing — verify slot IDs match SediMemory format |
| `aurora_closure_basis.py` | Genealogy closure wiring | `derive_lineage()`, `lineage_grade_payload()`, `GENEALOGY_ATOM_TO_SLOT_ID` |
| `aurora_constraint_stack.py` | Genealogy | `score_from_cost`, `CostDiffScore`, `DifferenceSnapshot` |
| `aurora_simulation_universe.py` | SimEngine | Universe management, divergence tracking |
| `aurora_dpme_pressure_bridge.py` | Dossier section 47.11 | DPME axis pressure, DER channel budget — verify N-axis tick weights |
| `foundational_contract.py` (already seen — re-read `ExistenceMode` hierarchy) | Everything | Confirm `ExistenceMode.PERSISTENT` is the correct floor for sediment ingestion |
| `aurora_sensory_crystal.py` | Dossier section 40 | `AuroraSensoryCrystal`, 6-facet pre-symbolic substrate — sediment sensory events here |
| `aurora_comprehension_gap.py` | Dossier section 47.5 | `ComprehensionGapSystem.process()` — fires before upward chain; sediment gap events |
| `aurora_proposition_substrate.py` | Dossier section 47.12 | Post-turn meaning extraction — sediment propositional claims as self-observation |
| `aurora_runtime.py` | Top-level entry | Main instantiation point — where to inject SediMemory into the stack |
| `aurora_surface_daemon.py` | Dossier section 0 | Present-frame turn handler — where to call `surface_recall()` |
| `aurora_subsurface_daemon.py` | Dossier section 0 | Tick owner — where to call `sedimemory.tick()` and checkpoint |

---

## SECTION 17 — INTEGRATION ORDER

Execute integrations in this order to avoid circular dependency issues:

1. **Section 1.1** — `aurora_runtime.py` instantiation (foundation)
2. **Section 2** — `aurora_governance_persistence_gateway.py` save/load
3. **Section 3** — N-Space Gateway ingest hook (events start flowing)
4. **Section 4** — `aurora_consciousness_engine.py` recall hook (reads start working)
5. **Section 5** — DCE integration
6. **Section 1.2** — `aurora_subsurface_daemon.py` tick + checkpoint
7. **Section 1.3** — `aurora_surface_daemon.py` surface recall
8. **Section 8** — WisdomStore bridge (requires SimEngine API confirmed)
9. **Section 6** — Telemetry bridge
10. **Section 7** — QAO Observer hook
11. Sections 9–15 — Optional/supplementary integrations

**Do not attempt sections 8–15 before sections 1–7 are verified working.**
Run `aurora_sedimemory.py` standalone first (`python aurora_sedimemory.py`)
to confirm all 17 self-checks pass in Aurora's environment before integrating.

---

## SECTION 18 — VERIFICATION CHECKLIST

After integration, verify these behaviors end-to-end:

- [ ] `sedimemory.stats()["total_events_ingested"]` increments on each live turn
- [ ] `sedimemory.stats()["by_axis"]["X"]["active_fragments"]` > 0 after a few turns
- [ ] `sedimemory.stats()["by_axis"]["A"]["active_fragments"]` = 0 initially (A takes many events to accumulate)
- [ ] After 5+ turns with similar constraint geometry, `channel_stats()["total_promoted"]` >= 1
- [ ] After a channel is promoted, `sedimemory.stats()["channel_efficiency"]` > 0.0
- [ ] `save_deep()` produces a non-empty dict after several turns
- [ ] `load_deep(save_deep())` on a fresh SediMemory restores B/A basins
- [ ] `save_channels()` / `load_channels()` round-trip restores `dominant_influence_map()`
- [ ] Surface daemon uses only X/T fragments (no A-axis fragments in surface recall)
- [ ] Subsurface daemon's tick advances decay — eventually fragments compress
- [ ] A-axis `compressed_mass` is non-empty after extended tick cycles
- [ ] QAO Observer records sedimemory events with OBSERVER provenance
- [ ] Gateway snapshot includes `sedimemory_deep` and `sedimemory_channels` keys

---

## SECTION 19 — KNOWN CONSTRAINTS AND EDGE CASES

**Thread safety:** If surface and subsurface daemons run in separate threads,
`SediMemory` is not thread-safe by default. The simplest solution is to have
only the subsurface daemon call `ingest_*` and `tick()`, with the surface
daemon calling only `surface_recall()` (read-only after the ingest cycle).
If concurrent writes are needed, wrap `_column.ingest()` and `_column.tick()`
with a threading lock.

**Memory pressure:** Each basin can hold up to 64 active fragments before
forced compression. At high event rates, compression fires frequently. If
memory pressure is a concern on mobile (Android/Termux), lower
`_BASIN_FRAGMENT_CAPACITY` from 64 to 32 in `aurora_sedimemory.py`.

**Bootstrap period:** For the first ~5 turns, no channels exist — everything
runs full strain (all 25 filters). This is correct and expected. Channel
efficiency starts at 0.0 and rises as patterns repeat. Do not interpret
low efficiency at bootstrap as a bug.

**Existence mode floor:** Only `ExistenceMode.PERSISTENT` and above sediment.
`ExistenceMode.TRANSIENT` and `ExistenceMode.REFERENCE` events are
intentionally excluded — they do not form durable memory. This is
enforced inside `SedimentColumn.ingest()` and should not be overridden.

**Manifold admissibility:** All `ConstraintVector` objects must have `X > 0`.
When constructing CVs from external data (episode results, braid state, etc.),
always clamp `X` to `max(0.01, computed_value)` to avoid `ManifoldViolation`.

---

*Spec authored: March 2026*  
*Authors: Sunni (Sir) Morningstar and Cael Devo*  
*For use with Aurora stack at `/home/king2morningstr/aurora/AuroraO/`*
