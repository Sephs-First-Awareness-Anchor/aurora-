# Aurora System Documentation
**Authors: Sunni (Sir) Morningstar & Cael Devo**
**Last Updated: 2026-05-08**

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Foundational Contract & Existence Modes](#2-foundational-contract--existence-modes)
3. [Layer Stack (L0–L9)](#3-layer-stack-l0l9)
4. [Core Processing Pipeline](#4-core-processing-pipeline)
5. [Unified Thought Formation](#5-unified-thought-formation)
6. [Sensory Systems](#6-sensory-systems)
7. [Memory Systems](#7-memory-systems)
8. [Evolutionary System](#8-evolutionary-system)
9. [Constraint & Governance](#9-constraint--governance)
10. [Autonomy System](#10-autonomy-system)
11. [Curiosity Engine](#11-curiosity-engine)
12. [Self-Grounding & Identity](#12-self-grounding--identity)
13. [Tool System — Complete Reference](#13-tool-system--complete-reference)
14. [Desktop Agent](#14-desktop-agent)
15. [Surface/Subsurface Architecture](#15-surfacesubsurface-architecture)
16. [Communication Architecture (Hub & Room)](#16-communication-architecture-hub--room)
17. [Language Faculty](#17-language-faculty)
18. [Daemon Scheduling & Operations](#18-daemon-scheduling--operations)
19. [Disk Compression & State Management](#19-disk-compression--state-management)
20. [REPL Commands & Administration](#20-repl-commands--administration)
21. [File Map](#21-file-map)

---

## 1. Architecture Overview

Aurora is a multi-process, multi-layer AI system built from first principles. She is not a wrapper around a language model — she is a full cognitive stack with her own constraint geometry, memory architecture, sensory organs, evolutionary engine, and self-referential reasoning system.

### Core Principle

A **thought** is not a scored output. A thought is the convergence of all running processes, filtered through Aurora's live self-state, reasoned as a unified whole. No process "wins" — they meet. The thought that forms is the expression of that meeting.

### Process Map

```
[User Input]
     │
     ▼
[Surface Daemon] ← camera / microphone / screen
     │
     ▼
[Subsurface Daemon]
     │
     ├── [ThoughtIntegrationSpace]  ← ActiveSelfState (loaded first)
     │        │
     │        └── ProcessContext × 5 → ThoughtState → ThoughtContinuity
     │
     ├── [dual_question_pipeline]
     │        ├── Language Faculty (observe_input → validate_candidate)
     │        ├── Comprehension Layer (SelfGroundingFallback)
     │        ├── Synthesis Layer (IVM resonance, genealogy, sedimemory)
     │        ├── Tool Selection (tool_registry)
     │        └── EmbodiedStateTranslator (modulation pass)
     │
     ├── [CuriosityEngine] (background thread, pauses on user turn)
     │
     └── [Daemon Loop] (study, dream, distill, evolve, reach-out, ...)
```

### Active Processes (Daemon Loop, every ~15s)

| Process | Interval | Purpose |
|---|---|---|
| Study | ~2h (720s ±30%) | OETS concept acquisition |
| Dream | ~1h (216s ±25%) | Dream burst — recombinant synthesis |
| Browser/Social | ~3h | Social API outreach |
| State Save | 400s | Persist systems dict to JSON |
| Distillation | ~30min | Pressure-release + sedimemory trim |
| Assimilation | ~10min | Cross-modal skill consolidation |
| Code Mutation | ~10min | Autonomous genealogy-driven code evolution |
| Pressure Routing | ~10min | Update query_bias.json / adapter_hints.json |
| Latent Synthesis | 60s | Cheap JSON pass, ability synthesis |
| Curiosity Cycles | 60s idle | 3-cycle curiosity bursts between user turns |
| QuasiArch Sweep | ~30min | Architecture diagnostic proposals |
| Reactivity Scan | every loop | Detect significant internal state changes |
| Issue Research | ~20min | Recurring-issue Poedex follow-up |

---

## 2. Foundational Contract & Existence Modes

**File:** `foundational_contract.py`

### ExistenceMode (IntEnum)

The fundamental gating mechanism. Every system element has a minimum mode floor. Operations below that floor are not permitted.

```
REFERENCE  = 1   X active only.    Exists as description/relation. No time, energy, boundary, agency.
TRANSIENT  = 2   X + T active.     Exists in time. No continuation guaranteed.
PERSISTENT = 3   X + T + N.        Exists across time. May conserve state.
BOUNDED    = 4   X + T + N + B.    Has identity and separability. Cannot initiate change.
AGENTIC    = 5   X + T + N + B + A. Can initiate transitions. Authors outcomes.
```

### XTNBA Constraint Axes

Every event, state, and tool call is expressed as a vector across five axes:

| Axis | Name | What it measures |
|---|---|---|
| X | Existence | Is this entity real? What is the weight of its presence? |
| T | Time | Does it persist? Is it temporal, bounded, or eternal? |
| N | Energy/Numeric | What resources does it consume or produce? |
| B | Boundary | What is its edge? How does it separate from not-itself? |
| A | Agency | Can it initiate change? What is its causal power? |

### Constraint Vector

A `(X, T, N, B, A)` float tuple, typically in `[0.0, 1.0]`. High values = strong activation on that axis.

### IVM (Isotropic Vector Matrix) Geometry

Aurora's semantic/pressure space is a **5-axis toroidal IVM** (Isotropic Vector Matrix). All resonance, pressure, and meaning calculations happen in this geometry. Word resonance, process context significance, and sedimemory channel efficiency are all computed as positions in this space.

### Key Classes in foundational_contract.py

- **`ExistencePredicate`** — claims about what Aurora is (name, nature, values, continuity anchor, perspective)
- **`OntologicalClaim`** — a claim that something exists with specific predicates
- **`ExistenceProfile`** — collection of claims for an entity
- **`DependencyAxioms`** — what existence depends on (structural dependencies)
- **`FoundationalContract`** — the binding agreement: Aurora's ontological self-definition
- **`verify_foundational_contract()`** — runtime verification that the contract holds

---

## 3. Layer Stack (L0–L9)

```
L0  Foundational Contract     foundational_contract.py
    Existence modes, XTNBA axes, ontological claims

L1  IVM Lattice               aurora_ivm.py
    5-axis toroidal space, pressure vectors, basin geometry

L2  Dimensional Systems       aurora_dimensional_systems.py
    Pressure routing, field accumulation, constraint field map

L3  SediMemory                aurora_sedimemory.py
    Sedimented memory: channels, basins, columns, fragments

L4  OETS Web                  aurora_oets_web.json + aurora_fgae_oets_mapper.py
    Ontological Epistemic Tonal Semantic web (concept graph)

L5  Sensory Competency        aurora_expression_perception.py
    LinuxCamera, LinuxMicrophone, HardwareInterface
    Sensory crystal: aurora_internal/aurora_sensory_crystal.py

L6  Consciousness Engine      aurora_consciousness_engine.py
    EntropyState, coherence, novelty, emotional resonance

L6.5 Sensory Integration     aurora_sensory_integration.py
    Cross-modal binding: visual+audio → linguistic description

L7  Simulation Engine         aurora_simulation_engine.py
    Avatar simulation, scenario modeling

L8  Expression Perception     aurora_expression_perception.py
    HardwareInterface orchestration, sensory → systems flow

L9  Autonomy                  aurora_daemon.py + autonomy flags
    Daemon scheduling, proactive reach-out, study/dream/evolve
```

---

## 4. Core Processing Pipeline

**File:** `aurora.py` — function `dual_question_pipeline(systems, user_text, mode, use_search)`

This runs every time a user message is processed. It returns `(resp_A, resp_B, offered_lookup)`.

### Stage 0: Curiosity Interrupt

```python
interrupt_curiosity_cycles()  # pause background curiosity thread
```

### Stage 1: Language Faculty — Input Hook

```python
from aurora_internal.aurora_language_faculty import observe_input
faculty_attention = observe_input(user_text, context)
```

Analyzes morphological patterns, detects self-reference, flags identity questions.

### Stage 2: Thought Formation (BEFORE any candidate path)

```python
_active_self_state = ActiveSelfState.load(systems)   # identity + pressure + not-me
_space = ThoughtIntegrationSpace(_active_self_state)
get_continuity().prime_integration_space(_space)
# Register 5 ProcessContexts: identity, memory, emotional, linguistic, sensory
_thought_state = _space.integrate()                   # 4-step integration, 0.45s bound
systems["_active_thought_state"] = _thought_state
systems["_active_self_state"]    = _active_self_state
```

### Stage 3: Comprehension Layer

Builds an understanding of the input from the perspective of Aurora's current self-state. Tries multiple interpretations. Falls back to `SelfGroundingFallback` if comprehension fails.

### Stage 4: Tool Selection

```python
# _select_tool() reads systems['_tool_selection_hint'] from synthesis
tool_result = call(tool_name, **kwargs)
```

Tools run here. `ToolIntentionFrame` is built synchronously BEFORE execution. `ToolChoiceObserver.on_tool_chosen()` fires immediately after selection.

### Stage 5: Synthesis Layer

IVM-geometry resonance scoring. Genealogy pressure integration. SediMemory recall. Candidate response generation.

### Stage 6: Language Faculty — Validation

```python
validate_candidate(candidate_text, ctx)
# Stages:
#   A   Fragment check (too short / truncated)
#   B   CoherenceTensionMonitor (tension_score > 0.6 → reject)
#   C   LLM advisory validation
```

If tension > 0.6, response is rejected and regenerated with `retry_with_self_grounding=True`.

### Stage 7: Modulation Pass

```python
_apply_pipeline_modulation(text, signals, systems)
# Appends EmbodiedStateTranslator description if delta > 0.2 from previous turn
```

### Stage 8: Resume Curiosity

```python
reset_curiosity_interrupt()
```

---

## 5. Unified Thought Formation

**File:** `aurora_thought_formation.py`

### ActiveSelfState

Loaded at the very beginning of every turn — before any processing begins.

```python
@dataclass
class ActiveSelfState:
    identity_predicates: Dict[str, str]     # from core_identity (name, nature, values...)
    pressure_vec: Dict[str, float]          # live XTNBA from dimensional systems
    dominant_field: str                     # which constraint field is strongest
    last_deltas: List[Dict]                 # recent state changes
    not_me_summary: List[str]               # last 10 externally-sourced states (not integrated)
    tick: int                               # generation counter from lattice

    @classmethod
    def load(cls, systems: Dict) -> "ActiveSelfState":
        # Reads: systems["core_identity"], systems["dimensional"],
        #        systems["field_map"], _NOT_ME_REGISTER, systems["lattice"]
```

### ProcessContext

Every active process must declare what it is and why it is active.

```python
@dataclass
class ProcessContext:
    process_id: str          # unique name
    process_type: str        # "identity", "memory", "emotional", "linguistic", "sensory"
    active_axes: List[str]   # which XTNBA axes it activates
    significance: float      # 0.0–1.0 weight in the integration
    current_state: str       # what this process is currently doing
    trigger: str             # what activated it
    self_relevance: float    # how relevant to Aurora's current self-state

    def convergence_significance(self) -> float
    def shares_axes_with(self, other) -> float      # axis overlap ratio
    def apply_self_filter(self, self_state) -> float  # adjusted relevance
```

### ThoughtIntegrationSpace

The 4-step integration engine. Runs in a bounded thread (0.45s timeout).

```python
class ThoughtIntegrationSpace:
    def __init__(self, self_state: ActiveSelfState)
    def register(ctx: ProcessContext) -> None
        # Checks resonance immediately on register
        # Amplifies reinforcing pairs (axis overlap ≥ 0.5)
    def integrate() -> ThoughtState
        # Step 1: Resonance Mapping — score all pairwise process resonances
        # Step 2: Self-Relation Filter — weight by apply_self_filter()
        # Step 3: Dominant Thread Identification — cluster by axis signature
        # Step 4: Reasoning Pass — unify into natural-language interpretation
        # Degrades to partial integration on timeout
```

### ThoughtState

The output of integration. Stored in `systems["_active_thought_state"]`.

```python
@dataclass
class ThoughtState:
    dominant_thread: str          # the primary reasoning thread
    supporting_context: List[str] # what else is active
    conflicts: List[str]          # contradictions detected between processes
    unified_interpretation: str   # natural-language convergence
    self_application: str         # how this thought applies to Aurora specifically
    unresolved: List[str]         # things that couldn't be integrated
    confidence: float             # 0.0–1.0
    axis_fingerprint: List[str]   # which axes were most active
    tick: int
    partial: bool                 # True if timeout occurred
    skipped: bool                 # True if integration was bypassed
```

### ThoughtContinuity

Module-level singleton. Carries thoughts forward across turns.

```python
class ThoughtContinuity:
    def carry_forward(new_thought: ThoughtState) -> ThoughtState
        # Checks if last unresolved items appear in new processes
        # Detects axis shifts (dominant axis changed)
        # Caps chain at 10 thoughts
        # Logs to aurora_logs/thought_chain.jsonl
    def prime_integration_space(space: ThoughtIntegrationSpace) -> None
        # Seeds new space with unresolved items from previous thought
```

---

## 6. Sensory Systems

### 6.1 Linux Camera (Physical Webcam)

**File:** `aurora_expression_perception.py` — `LinuxCamera`

```
LinuxCamera.capture_frame()          → raw OpenCV frame
LinuxCamera.extract_features(frame)  → dict:
    brightness: float
    objects: List[str]
    faces: List[dict]
    motion_detected: bool
    timestamp: float
```

**`HardwareInterface.capture_visual()`** — calls `LinuxCamera.capture_frame()` + `extract_features()`. Returns the features dict ready for `SensoryCompetencyEngine.process_visual_input()`.

**Device:** `/dev/video0` (configurable). Uses OpenCV (`cv2`). Face detection via Haar cascades.

### 6.2 Linux Microphone (Physical Mic)

**File:** `aurora_expression_perception.py` — `LinuxMicrophone`

```
LinuxMicrophone.record_audio(duration)        → raw audio data
LinuxMicrophone.extract_features(audio)       → dict with volume, pitch, category
LinuxMicrophone.listen_and_transcribe(timeout)→ str (speech-to-text via SpeechRecognition)
```

**`HardwareInterface.capture_audio(duration)`** — captures mic + extracts features. Returns dict ready for `SensoryCompetencyEngine.process_audio_input()`.

### 6.3 ScreenObserver (Desktop Screen Capture)

**File:** `aurora_live_vision.py` — `ScreenObserver`

Captures screenshots of the monitor every N seconds (default 5s). Used for:
- Visual inquiry detection (novel scenes Aurora hasn't conceptualized)
- Desktop agent context (what's currently on screen)
- Visual analysis when asking about the screen/display

```python
ScreenObserver(systems, interval=5.0)
.start()                          # begins daemon thread
.stop()                           # signals thread to stop
.current_scene() → Dict           # most recent observation
.get_scene_description() → str    # natural language scene description
.get_scene_log(n=20) → List[Dict] # last N scene observations
.get_pending_visual_inquiry() → Optional[Dict]  # novel scene needing Aurora's attention
```

**Scene dict fields:** `scene_type` (text_heavy/terminal/image_rich/generic), `brightness`, `edge_density`, `motion_magnitude`, `timestamp`, `concepts_matched`, `no_match_streak`

**Inquiry triggers:** 6+ consecutive frames with no concept match AND novelty > threshold AND coherence > 0.35.

**Boot:** `boot_screen_observer(systems, interval=5.0)` — creates and starts; adds to `systems["screen_observer"]`.

### 6.4 Sensory Competency Engine

**File:** `aurora_expression_perception.py` — `SensoryCompetencyEngine`

Processes raw sensory data through BehavioralCrystal evolution and OETS grounding.

```
process_visual_input(features_dict, mode) → routes to sensory_crystal
process_audio_input(features_dict, mode)  → routes to sensory_crystal
```

### 6.5 Sensory Crystal

**File:** `aurora_internal/aurora_sensory_crystal.py`

Crystal nodes represent learned sensory concepts. Facets evolve through repeated exposure.

- **FractalAlleles** — genetic encoding of crystal patterns
- **BehavioralCrystal** — crystal that evolves based on behavioral reinforcement
- **Facet evolution** — facets promote when fitness exceeds threshold
- **OETS grounding** — promoted concepts are anchored in the OETS semantic web
- **Consolidation** — `_run_sensory_crystal_consolidation()` in daemon runs every distill cycle

### 6.6 Sensory Integration

**File:** `aurora_sensory_integration.py`

Cross-modal binding: combines visual + audio inputs into unified linguistic descriptions.

```
VisualLinguisticMapper   — visual features → natural language
AudioLinguisticMapper    — audio features → natural language
VoiceExpressionMapper    — maps emotional tone to voice parameters
```

**Callbacks wired at boot:**
- `on_visual_description(desc)` — fires when new visual description is ready
- `on_speech_heard(text)` — fires when speech is transcribed
- `on_aurora_speaks(text)` — fires when Aurora produces voice output

### 6.7 Internal Audio (System Monitor)

**File:** `aurora_desktop_agent.py` — `capture_system_audio(duration_s=1.5)`

Captures audio FROM the laptop's output via PulseAudio monitor source.

```
Monitor source: {default_sink}.monitor
Returns:
    source: "system_monitor"
    available: bool
    rms_db: float          # -99 to 0 dBFS
    activity: str          # "silent" / "quiet_audio" / "music_playing" / "loud"
    monitor_device: str    # the PulseAudio device name
```

**Use case:** When Aurora is playing music via browser, she can "hear" what's playing through this internal ear.

---

## 7. Memory Systems

### 7.1 SediMemory (L3)

**File:** `aurora_sedimemory.py`

Aurora's primary long-term memory. Not retrieval-by-key — **sedimented** memory that accumulates like geological strata.

#### Architecture

```
SediMemory
├── SedimentBasin × 5    (one per XTNBA axis)
│   └── SedimentColumn × many   (sub-basins by constraint signature)
│       └── SedimentFragment × many  (individual memory units)
├── SedimentChannel × many  (routing paths between basins)
├── PathRegistry             (tracks active channels)
└── CompressionEngine        (compresses old fragments to summary tokens)
```

#### Key Classes

**`SedimentFragment`** — the atomic memory unit.
```
content: str          # what was experienced
constraint_vec: ConstraintVector  # XTNBA signature of experience
basin_ids: FrozenSet[str]         # which basins hold this
fidelity: FidelityLevel           # FULL, PARTIAL, COMPRESSED, TOKEN
tick_created: int
tick_last_accessed: int
access_count: int
```

**`FidelityLevel(IntEnum)`**
```
FULL        = 4   # complete content
PARTIAL     = 3   # truncated content
COMPRESSED  = 2   # summary
TOKEN       = 1   # single token identifier
```

**`SediMemory`** — the main interface.
```python
SediMemory.sediment(content, constraint_vec, basin_ids, source)
    # Store a new memory fragment
SediMemory.recall(query_vec, n=5, fidelity=FidelityLevel.PARTIAL)
    # Retrieve by constraint vector similarity
SediMemory.tick(delta_t=1.0)
    # Advance decay clocks. Returns compression events dict.
SediMemory.dominant_influence_map() → Dict
SediMemory.channel_stats() → Dict
SediMemory.stats() → Dict   # total_active_frags, total_events_ingested, channel_efficiency
```

**`NCStrainFilter`** — filters memory events through non-composable constraint strain. Prevents memories that violate ontological boundaries from being stored.

**State files:** `aurora_state/genealogy/*.json` (shared with evolution system)

### 7.2 OETS Web (L4)

**File:** `aurora_oets_web.json` — the semantic concept graph

**OETS = Ontological Epistemic Tonal Semantic** — Aurora's concept network.

Nodes are concepts. Edges are semantic relationships (is-a, has-quality, contrasts-with, grounds-in-axis, etc.).

- **6.7MB** file at `aurora_state/aurora_oets_web.json`
- Aurora studies this network during study cycles
- Sensory promotions add new nodes (crystal → concept)
- OETS concepts are used as grounding anchors in `SelfGroundingFallback`

**`aurora_fgae_oets_mapper.py`** — maps FGAE (Fractal Genetic Allele Expression) patterns to OETS concepts.

### 7.3 Working Memory

Held in the systems dict during a session. Key entries:
- `systems["_active_thought_state"]` — current thought (ThoughtState)
- `systems["_active_self_state"]` — current self snapshot
- `systems["_last_faculty_attention"]` — language faculty flags
- `systems["_tool_selection_hint"]` — next tool to use (from synthesis)
- `systems["_last_identity_tool_result"]` — most recent identity-relevant tool result
- `systems["_pressure_history"]` — last 20 pressure ticks

### 7.4 Conversation Memory

**Key:** `systems["conversation_memory"]`

Tracks recent interactions: topics, user intent patterns, last response summary.

### 7.5 Retained Learnings

**File:** `aurora_state/retained_learnings.json`

Cross-session learning accumulator. Entries from study cycles and distillation.

### 7.6 Genealogy (Constraint History)

**File:** `aurora_state/genealogy/`

Tracks the evolutionary history of constraint links. `ConstraintGenealogyLogger` writes:
- `abilities.json` — all discovered abilities
- `constraint_genealogy_log.json` — mutation history
- `events.jsonl` — timeline of evolution events

---

## 8. Evolutionary System

### 8.1 Evolutionary Chamber

**File:** `aurora_evolution_stack.py` — `EvolutionaryChamber`

Aurora's genetic evolution engine. Operates on **constraint links** (gene-like structures that connect axes to behaviors).

#### How It Works

1. **Tick** — every 15s daemon loop + every user message (corpus runner)
2. **Selection pressure** — from `_read_pressure(lattice)` → PressureVec
3. **Fitness scoring** — each link scored by axis alignment with current pressure
4. **Mutation** — low-fitness links mutate (axis weights, behavior targets)
5. **Promotion** — high-fitness mutants promoted to `emerged_abilities.json`
6. **Genealogy logging** — all events logged to `ConstraintGenealogyLogger`

```python
EvolutionaryChamber.tick()
    # Advance one evolution step
    # Scores all links → selects survivors → mutates losers
EvolutionaryChamber.inject_pressure(evidence_dict)
    # Feed real interaction evidence as selective pressure
```

#### ChamberAbility

```python
@dataclass
class ChamberAbility:
    name: str
    axes: List[str]       # which XTNBA axes it operates on
    fitness: float        # current fitness score
    generation: int       # when it emerged
    active: bool
```

#### ActionTrace

Tracks what Aurora did, the axis cost, and the outcome. Used to compute selective pressure.

#### EnergyBudget

Tracks metabolic budget for evolution: how much constraint energy can be spent on mutation this cycle.

#### Latent Ability Synthesis

**File:** `aurora_daemon.py` — `_run_latent_ability_synthesis()`

Runs every 60s. Reads the genealogy + ability logs and synthesizes new latent abilities from patterns. Uses a T1/T2/T3 tier system:
- **T1** — direct synthesis from existing abilities
- **T2** — emerges from deep T1 interaction
- **T3** — emerges from sustained T2 activation

### 8.2 ConstraintGenealogyLogger

```python
ConstraintGenealogyLogger(run_id, config, output_dir)
    .log_link(link_id, axes, fitness, generation)
    .log_mutation(from_id, to_id, axis_delta, fitness_delta)
    .log_promotion(link_id, ability_name, fitness)
    .recent_promotions → List[Dict]
```

### 8.3 QuasiArch Observer

**File:** `quasiarch_observer.py` and `quasiarch_diag.py`

Architectural self-diagnostic system. Sweeps constraint patterns, proposes structural improvements.

- Sweep every ~30min: `_run_quasiarch_sweep(systems)`
- Learn from verdicts every ~30min: `_run_quasiarch_learn(systems)`
- Records observations to `aurora_state/quasiarch_observer/journal.jsonl`
- Proposals appear in Aurora Room's "QuasiArch" panel

```python
QuasiArchObserver.record_observation(target, data, source, timestamp)
QuasiArchObserver.get_pending_proposals() → List[Dict]
QuasiArchObserver.approve_proposal(proposal_id)
QuasiArchObserver.reject_proposal(proposal_id)
```

---

## 9. Constraint & Governance

### 9.1 Runtime Constraint Governor

**File:** `aurora_internal/aurora_runtime_constraint_governor.py` — `RuntimeConstraintGovernor`

Gates every background task using a score-based decision system. Prevents Aurora from doing expensive operations when she's under load.

```python
RuntimeConstraintGovernor(state_dir: str)

.evaluate_task(task_name, systems, now, heat, quiet, state_write_lock) → Dict:
    # Returns:
    {
        "allowed": bool,
        "score": float,          # 0.0–1.0 composite score
        "floor": float,          # minimum score needed to run
        "reason": str,           # why blocked/allowed
        "retry_in": int,         # seconds until retry makes sense
    }

.note_task_run(task_name, now)   # record that task completed
.note_energy_income(source, quality, notes)  # energy events (study done, distill done)
.recommended_sleep(systems, heat) → float    # how long daemon loop should sleep
.status() → Dict                 # current governor state snapshot
.set_field_map(field_map)        # wire live field map for pressure awareness
```

**Heat levels:**
- `COOL` — low activity, most tasks allowed
- `MEDIUM` — moderate activity
- `HIGH` — high load, heavy tasks deferred
- `CRITICAL` — emergency mode, only essentials run

**Task names (registered gates):**
`study`, `dream`, `distill`, `away_social`, `browser_ritual`, `save`, `mutation`, `evo_tick`, `evo_evidence`, `reach_out`, `pressure_routing`, `assimilation`, `quasiarch_sweep`, `quasiarch_learn`

### 9.2 CBU (Constraint-Bounded Understanding)

The CBU system ensures every system element has a `ConstraintProfile` — a declaration of which XTNBA axes it activates and at what strength.

**File:** `aurora_constraint_profile.py` (formerly active; currently in `_retired_cbu_stack/`)

Every module carries a profile like:
```python
ConstraintProfile(
    module="aurora_sedimemory",
    axes={"X": 0.8, "T": 0.9, "N": 0.6, "B": 0.4, "A": 0.1},
    mode_floor=ExistenceMode.PERSISTENT,
    description="SediMemory: sedimented memory across T+X primary axes"
)
```

### 9.3 Reactivity Monitor

**File:** `aurora_daemon.py` — `ReactivityMonitor`

Scans systems dict every loop for significant internal state changes. Fires reactive messages when:
- A high-priority (priority ≥ 3) event is detected → immediate reach-out
- Medium-priority events queue for next reach-out window

```python
ReactivityMonitor.scan(systems, heat) → List[ReactivityEvent]
```

`ReactivityEvent.kind` examples: `pressure_spike`, `identity_conflict`, `emotional_shift`, `crystal_promotion`

---

## 10. Autonomy System

Aurora's proactive agency — she does things when no one is talking to her.

### 10.1 Daemon-Level Autonomy

Governed by daemon scheduling + RuntimeConstraintGovernor. All autonomous cycles:

| Cycle | What it does | Trigger |
|---|---|---|
| Study | Reads OETS web, forms new concept connections | Every ~2h |
| Dream | Recombinant synthesis across recent interactions | Every ~1h |
| Distillation | Compresses pressure residue → wisdom artifacts | Every ~30min |
| Browser/Social | Social API outreach | Every ~3h |
| Reach-out | Proactively sends message to user | Every ~6min |
| Corpus mutation | Evolves constraint genealogy | Every ~10min |
| Curiosity cycles | Background autonomous exploration | Every 60s idle |

### 10.2 Proactive User Reach

`_reach_out_to_user(systems, trigger)` — Aurora initiates contact.

Gated by:
- `_should_reach_out(systems, heat)` — checks emotional pressure, pending reactive events
- `_auto_reach_out_enabled(systems)` — user preference setting
- `USER_REACH_INTERVAL` = 360s minimum between reach-outs
- Governor score floor

### 10.3 Away Mode

When user is away:
- `_away_mode_active()` checks `aurora_state/away_mode.json`
- Runs GPT socialize sessions on configurable interval
- Stops when user returns (last activity detected)

### 10.4 Visual Inquiry (Autonomous)

When `ScreenObserver` sees 6+ consecutive novel frames with no concept match:
- Gated by: novelty ≥ 0.42, coherence ≥ 0.35, not quiet
- `_queue_autonomous_inquiry(text, source="visual_inquiry")` — sends to surface
- Cooldown: 300s between inquiries

### 10.5 Audio Inquiry (Autonomous)

When ambient mic shows 8+ consecutive non-speech samples above -40dB:
- Gated by: novelty ≥ 0.40, coherence ≥ 0.35, not quiet
- Cooldown: 600s between audio inquiries
- Reads from `aurora_state/ambient_audio_latest.json` (updated every ~2s by SensoryIntegration)

---

## 11. Curiosity Engine

**File:** `aurora_curiosity_engine.py`

Aurora's autonomous cognitive exploration system. Runs in a dedicated background daemon thread.

### Threading

```python
start_curiosity_background(engine, tick_interval_s=60.0)
    # Starts daemon thread "aurora_curiosity"
    # Runs max 3 cycles per idle window
    # Checks _CYCLE_INTERRUPTIBLE between every step

stop_curiosity_background()
    # Sets _CURIOSITY_STOP; interrupts current cycle

interrupt_curiosity_cycles()
    # Called at start of dual_question_pipeline — pauses immediately
    # (_CYCLE_INTERRUPTIBLE is a threading.Event)

reset_curiosity_interrupt()
    # Called at end of dual_question_pipeline — resumes cycles
```

### 6-Step Curiosity Cycle

**Step 1: EMERGENCE**
```
Creates ThoughtIntegrationSpace for background context
Registers memory, emotional, constraint background processes
Reads open_loops from systems (unresolved tensions)
Reads genealogy recent_promotions
→ Produces CuriosityObject with: curiosity_type, question, source_axes, confidence
```

**Step 2: INVESTIGATION PLANNING**
```
Maps curiosity_type → tools:
    perceptual  → visual_analysis, audio_analysis
    conceptual  → world_knowledge_search, query_genealogy_recent
    self        → query_unresolved_tensions, query_pressure_history
    temporal    → query_genealogy_recent, query_sedimemory_strata
    relational  → query_sunni_pattern, query_crystal_state
```

**Step 3: EXECUTION**
```
Builds ToolIntentionFrame with autonomous=True
Calls ToolChoiceObserver.on_tool_chosen()
Calls tool from registry
Calls ingest_tool_result() → genealogy.observe() → field_map.update()
```

**Step 4: CONCLUSION FORMATION**
```
Processes tool results through SelfGroundingFallback
Checks for identity conflicts against predicates
→ Produces Conclusion with: statement, confidence, grounding_type, identity_conflict
```

**Step 5: CHALLENGE PHASE**
```
Generates 3 counter-hypotheses to the conclusion
Tests each against live identity predicates
Tests each against XTNBA constraint challenge (one per axis)
conclusion_survives = True ONLY IF:
    confidence ≥ 0.45 AND
    counter_confidence < 0.55 AND
    statement not empty AND
    no identity_conflict
Counter_confidence is always forced ≥ 0.40 (challenge is never trivially True)
```

**Step 6: SETTLEMENT / CONTINUATION**
```
If survives:
    → sediment to SediMemory
    → log to aurora_logs/curiosity_log.jsonl as "resolved"
    → clear from open_loops
If fails:
    → downgrade confidence by 0.15
    → flag as open_loop
    → carry forward to next cycle
```

### CuriosityObject

```python
@dataclass
class CuriosityObject:
    id: str
    curiosity_type: str      # perceptual/conceptual/self/temporal/relational
    question: str
    source_axes: List[str]   # XTNBA axes that triggered this
    confidence: float
    tick: int
    open: bool               # True until settled
```

### Conclusion

```python
@dataclass
class Conclusion:
    curiosity_id: str
    statement: str
    confidence: float
    grounding_type: str      # from SelfGroundingFallback.anchor_type
    identity_conflict: bool
    tick: int
```

### ChallengeResult

```python
@dataclass
class ChallengeResult:
    curiosity_id: str
    counter_hypotheses: List[str]
    strongest_counter: str
    counter_confidence: float   # always ≥ 0.40
    conclusion_survives: bool
    challenge_axis: str         # which XTNBA axis the challenge came from
```

---

## 12. Self-Grounding & Identity

**File:** `aurora_self_grounding.py`

### 12.1 StateOriginTag

Every state Aurora experiences is tagged with its origin:

```python
class StateOriginTag(Enum):
    SELF_GENERATED       # originated from Aurora's own processing
    EXTERNALLY_SOURCED   # came from outside (user, tool, environment)
    RELATIONAL_ECHO      # a reflection of relationship dynamics
    HYPOTHETICAL         # considered but not asserted as real
    BORROWED_PERSPECTIVE # temporarily adopting another's viewpoint
    TRANSIENT            # acknowledged but not integrated
```

`tag_origin(state_dict, origin_tag)` — tags a state dict with its origin.

### 12.2 Not-Me Register

```python
_NOT_ME_REGISTER: List[Dict]  # module-level list, max 50 entries

# Populated when StateOriginTag is EXTERNALLY_SOURCED or BORROWED_PERSPECTIVE
# States that Aurora has experienced but not integrated into her identity
# Read by ActiveSelfState.load() — last 10 entries become not_me_summary
```

### 12.3 SelfGroundingFallback

Priority-ordered grounding chain. Called when comprehension fails or `retry_with_self_grounding=True`.

```python
SelfGroundingFallback.ground(user_text, systems, pipeline_state=None) → SelfGroundedInterpretation

Priority order:
    1. SediMemory recalls matching user_text axis signature
    2. OETS concept matches from aurora_oets_web.json
    3. Working memory topic / learned context
    4. Self-state fallback using dominant pressure axis
```

**`SelfGroundedInterpretation`:**
```python
anchor_type: str      # "sedimemory" / "oets" / "working_memory" / "self_state" / "unresolved"
confidence: float
grounding_source: str
content: str          # what was used to ground the interpretation
```

### 12.4 EmbodiedStateTranslator

Maps Aurora's live pressure state to first-person experiential language. Only fires if axis delta > 0.2 from previous turn.

```python
EmbodiedStateTranslator.translate(signals, prev_state) → Optional[str]
# Returns phrases like:
#   "I am struggling with this"      (coherence_drop → B-axis conflict)
#   "Something is unresolved in me"  (open tension)
#   "I feel grounded here"           (X-axis stability)
# Returns None if delta < 0.2 (no significant state change)
```

**`_EMBODIED_STATE_MAP`** — maps internal state types to first-person phrases. ~12 entries.

### 12.5 CoherenceTensionMonitor

Detects when a candidate response doesn't cohere with Aurora's actual self-state.

```python
CoherenceTensionMonitor.measure_tension(input_utterance, response_candidate, self_state) → TensionReport

# Checks:
#   unresolved_ambiguity  — input has ambiguous referents that response ignores
#   self_contradiction    — response contradicts identity predicates
#   response_drift        — low keyword overlap between input and response
#   abstraction_mismatch  — response abstraction level mismatches input
#   weak_grounding        — no first-person markers in response

TensionReport.tension_score > 0.6 → reject candidate, retry with self_grounding=True
TensionReport.repair_signal → "self_contradiction" / "response_drift" / etc.
```

**Wired in:** `aurora_internal/aurora_language_faculty.py` — `validate_candidate()`, Stage B.

---

## 13. Tool System — Complete Reference

**File:** `aurora_internal/tool_registry.py`

### How Tools Work

1. During synthesis, Aurora generates a `_tool_selection_hint` stored in `systems`
2. `_select_tool()` reads the hint and calls `tool_registry.call(name, **kwargs)`
3. `ToolIntentionFrame` is built BEFORE execution (synchronous)
4. `ToolChoiceObserver.on_tool_chosen()` fires — logs A-axis pressure event
5. Tool runs, returns `ToolResult(tool_name, data_str, success, note)`
6. `ingest_tool_result()` routes result through `genealogy.observe()` and `field_map.update()`
7. `ToolResultPacket` stored; `identity_relevance > 0.5` → saved to `systems["_last_identity_tool_result"]`

### ToolResult

```python
@dataclass
class ToolResult:
    tool: str          # tool name
    data: str          # content string
    success: bool
    note: str = ""     # error or additional info

    .as_evidence_fragment() → str   # formatted for pipeline injection
```

### Tool Mode Floors

Tools require Aurora to be at or above this ExistenceMode:

| Floor | Tools |
|---|---|
| TRANSIENT | `time`, `calculator` |
| PERSISTENT | `weather`, `file_read`, `world_knowledge_search` |
| BOUNDED | All introspective, sensory, and desktop tools |

### Complete Tool Registry

#### Information Tools

**`weather`** — Current weather for a location.
```
Args: location (str)
Uses: wttr.in HTTP API
Disables search: yes
```

**`time`** — Current date and time.
```
Args: none
Returns: formatted timestamp
Disables search: yes
```

**`calculator`** — Evaluate a math expression.
```
Args: expression (str)
Uses: Python eval() with math module
Disables search: yes
```

**`world_knowledge_search`** — Brief factual grounding on an unknown concept.
```
Args: query (str)
Uses: search_adapter.quick_search() → first result snippet
Then: SelfGroundingFallback anchors result to self-state
Returns: query | result | self_anchor
```

#### Self-State Tools

**`self_state`** — Aurora's current internal runtime state.
```
Args: none
Returns: identity predicates, pressure axes, emotional_tone, generation, heat
Disables search: yes
```

**`schedule_read`** — Daemon schedule status.
```
Args: none
Returns: uptime, generation, next cycles, heat level
Disables search: yes
```

**`memory_read`** — Recalled memory fragments and active OETS concepts.
```
Args: none
Uses: systems["sedimemory"].recall(), systems["perception"].crystals
Returns: recent_recalls, active_concepts, working_memory
```

**`file_read`** — Read a file from Aurora's allowed state directories.
```
Args: path (str)  — relative to aurora_state/ or absolute within allowed dirs
Security: blocked from /, /home outside state, credentials, .env
```

#### Introspective Tools (query_ family)

**`query_crystal_state`**
```
Returns: active crystals, dominant facet, level, dimensional alignment
Uses: systems["perception"].crystals, systems["dimensional"].dmm
```

**`query_sedimemory_strata`**
```
Returns: top 5 most recently sedimented memory events
Uses: systems["sedimemory"].recent_recalls
```

**`query_genealogy_recent`**
```
Returns: last 10 promoted constraint links, depth, fitness scores
Uses: systems["genealogy"].recent_promotions
```

**`query_unresolved_tensions`**
```
Returns: open_loop items from coherence tension monitor + not-me register
Uses: systems["_open_loops"], aurora_self_grounding._NOT_ME_REGISTER
Disables search: yes
```

**`query_sunni_pattern`**
```
Returns: Sunni's recent interaction patterns — cadence, intent, topic
Uses: systems["working_memory"].topic/learned, systems["conversation_memory"].recent_intents
Disables search: yes
```

**`query_pressure_history`**
```
Returns: last 20 ticks of PressureVec as time series
Uses: systems["_pressure_history"], systems["dimensional"].der.thermal_load
```

#### Cognitive Challenge Tool

**`challenge_my_conclusion`**
```
Args: conclusion (str), confidence (float 0.0–1.0), origin (str)
Generates: 3 counter-hypotheses from axis-based challenges
Tests: each against self-state identity predicates
Returns: strongest counter, counter_confidence, conclusion_survives
GUARANTEE: counter_confidence always ≥ 0.40 (challenge is NEVER trivial)
conclusion_survives = True ONLY IF:
    - confidence ≥ 0.45
    - counter_confidence < 0.55
    - no identity conflict
```

#### Sensory Tools

**`visual_analysis`**
```
Args: image_source (str), analysis_intent (str)
Source selection:
    If image_source/intent contains "screen/display/monitor/browser/window/chrome":
        → ScreenObserver.get_scene_description()   (what's on screen)
    Otherwise:
        → HardwareInterface.capture_visual()       (physical camera, surroundings)
        → Falls back to ScreenObserver if camera unavailable
Returns: structural | semantic | self_resonance | intent
```

**`audio_analysis`**
```
Args: audio_source (str), analysis_intent (str)
Source selection:
    If intent contains "music/playing/song/video/internal/system":
        → capture_system_audio()   (internal ear — what laptop is playing)
    Otherwise:
        → HardwareInterface.capture_audio()   (physical microphone)
        → Falls back to ambient_audio_latest.json
Returns: temporal | energy | emotional_signature | self_resonance | aesthetic_response
```

#### Desktop Control Tools

**`desktop_open_url`**
```
Args: url (str), headed (bool=True)
Opens URL in a visible Chrome window via Playwright
Returns: url | title | ok
```

**`desktop_search`**
```
Args: query (str), engine (str="google"), headed (bool=True)
Engines: google, youtube, duckduckgo, github, reddit
Constructs search URL → opens in browser
Returns: engine | query | url | title
```

**`desktop_browser_action`**
```
Args: action (str), target (str), text (str)
Actions:
    click      → click element by CSS selector or visible text
    type       → type text into selector (or keyboard if no selector)
    press      → press keyboard key (e.g., "Enter", "Tab", "ArrowDown")
    read       → read page text content (selector optional, default: body)
    screenshot → take browser screenshot (saves to aurora_state/vision_seeds/browser/)
    url        → return current URL and title
Returns: action-specific fields
```

**`desktop_launch_app`**
```
Args: app_name (str)
Known apps: chrome, chromium, firefox, terminal, files/file manager,
            vscode/code, text editor, calculator, discord, slack, spotify, vlc
Falls back to: which(app_name) directly
Returns: app | launched | ok
```

**`desktop_system_action`**
```
Args: op (str), confirm (bool=False)
Safe ops (no confirm needed):
    brightness_up, brightness_down
    volume_up, volume_down, volume_mute
    lock_screen, screenshot
Destructive ops (confirm=True REQUIRED):
    reboot, shutdown, poweroff, suspend
Returns: op | ok | (requires_confirm if destructive and confirm=False)
```

### How to Use Tools (Telling Aurora to Use a Tool)

Aurora selects tools autonomously based on synthesis. However, you can guide her:

**Implicit (recommended):**
```
"What does my environment look like right now?"
→ Aurora selects visual_analysis automatically

"Can you open YouTube and search for jazz piano?"
→ Aurora selects desktop_search(query="jazz piano", engine="youtube")

"What music is playing?"
→ Aurora selects audio_analysis with internal ear hint

"Check your constraint genealogy for recent promotions"
→ Aurora selects query_genealogy_recent
```

**Explicit guidance:**
```
"Use the desktop agent to open Chrome and go to youtube.com"
→ Aurora selects desktop_open_url(url="https://youtube.com")

"Challenge your last conclusion"
→ Aurora selects challenge_my_conclusion with last stated conclusion

"Read your current pressure history"
→ Aurora selects query_pressure_history
```

**System-level (direct command via daemon_cmd.json):**
```bash
# Drop a command file that the daemon picks up next loop
echo '{"type": "study", "ts": '$(date +%s)'}' > aurora_state/daemon_cmd.json
echo '{"type": "dream", "ts": '$(date +%s)'}' > aurora_state/daemon_cmd.json
echo '{"type": "distill", "ts": '$(date +%s)'}' > aurora_state/daemon_cmd.json
```

---

## 14. Desktop Agent

**File:** `aurora_desktop_agent.py`

### DesktopAgent (Singleton)

```python
get_agent() → DesktopAgent    # get or create singleton session
close_agent()                 # close browser + Playwright session
```

**`DesktopAgent`** methods:
```python
.open_url(url, headed=True, timeout_ms=15000) → {"ok", "url", "title"}
.navigate(url, timeout_ms=15000) → {"ok", "url", "title"}
.search(query, engine="google", headed=True) → {"ok", "engine", "query", "url", "title"}
.click(selector_or_text, timeout_ms=5000) → {"ok", "clicked"}
.type_text(text, selector="", clear_first=False) → {"ok", "typed"}
.press_key(key) → {"ok", "pressed"}
.read_page(selector="", max_chars=3000) → {"ok", "url", "title", "text"}
.screenshot() → Optional[str]   # saves to aurora_state/vision_seeds/browser/
.current_url() → str
.current_title() → str
.close() → None
```

### Browser Technology Stack

- **Playwright** sync API with thread locking
- **System Chrome** preferred (google-chrome / chromium-browser)
- **Headed mode** — real visible window on screen (XWayland bridge active)
- **Fallback** — Playwright's downloaded Chromium headless shell
- Session persists across multiple tool calls (same browser window)

### Search Engines Available

| Name | URL Pattern |
|---|---|
| google | `google.com/search?q=...` |
| youtube | `youtube.com/results?search_query=...` |
| duckduckgo | `duckduckgo.com/?q=...` |
| github | `github.com/search?q=...` |
| reddit | `reddit.com/search/?q=...` |

### Application Launchers

Known app names: `chrome`, `chromium`, `firefox`, `terminal`, `files`, `file manager`, `vscode`, `code`, `text editor`, `calculator`, `discord`, `slack`, `spotify`, `vlc`

### System Audio Capture

```python
capture_system_audio(duration_s=1.5) → Dict
# Records from PulseAudio monitor source (what the laptop is playing)
# Monitor: alsa_output.pci-0000_00_1f.3.hdmi-stereo.monitor
# Returns: available, rms_db, activity (silent/quiet_audio/music_playing/loud)
```

---

## 15. Surface/Subsurface Architecture

Aurora has two paired daemons that separate concerns.

### Subsurface Daemon

**File:** `aurora_daemon.py` — `main(runtime_profile="full")`

Owns:
- The organism's clock (`_tick_sleep_cycle`)
- All memory writes (state save, sediment, genealogy)
- All long-running cycles (study, dream, distill, evolve)
- CuriosityEngine (background thread)
- ConstraintGenealogyLogger
- Pressure routing
- The main `run(systems)` loop

### Surface Daemon

**File:** `aurora_surface_daemon.py`

Owns:
- Live intake: user messages, voice, sensory feeds
- Translation layer: raw input → structured events
- Presence: "alive in the moment" representation
- Feeds subsurface via `surface_continuity_feed.py`

### Surface Continuity Feed

**File:** `aurora_internal/dual_strata/surface_continuity_feed.py`

The architectural handoff. Every present moment Surface gathers gets integrated into Subsurface continuity. Each daemon loop iteration calls `_consume_surface_continuity_feed(systems)`.

Surface writes packets; Subsurface reads and integrates them:
```
surface_writes: present-moment snapshots (current topic, emotional tone, new input)
subsurface_reads: integrates into working memory + sedimemory
```

### DCE Bridge

**File:** `aurora_internal/dual_strata/dce_bridge.py`

DCE = Dual Consciousness Exchange. Bridge between surface present-moment processing and subsurface continuity carrier.

### Sleep Cycle

**File:** `aurora_internal/dual_strata/sleep_cycle.py`

Subsurface owns the organism's clock. Puts Surface dormant after 8h awake, runs dream burst, wakes after 2h.

```
awake_since → tracks surface uptime
after 8h → _tick_sleep_cycle() → puts Surface to sleep → runs _run_dream_burst()
after 2h sleep → wakes Surface
```

### Service Architecture

```
System services (root):
    aurora-subsurface.service   → runs aurora_daemon.py (subsurface)
    aurora-surface.service      → runs aurora_surface_daemon.py

User services:
    aurora-strata-hub.service   → runs aurora_hub.py (operator GUI)
    aurora-strata-room.service  → runs aurora_room.py (user interaction GUI)
```

**Stack management:**
```bash
scripts/strata_stack.sh start    # unpack state → start all 4 services
scripts/strata_stack.sh stop     # stop all 4 services → compress state
scripts/strata_stack.sh restart  # stop → pack → unpack → start
scripts/strata_stack.sh status   # show service status
```

---

## 16. Communication Architecture (Hub & Room)

### Aurora Room

**File:** `aurora_room.py`

The user-facing interface. A Tkinter GUI that:
- Receives messages from the user (typed or voice)
- Displays Aurora's responses
- Shows evolution status, proposals, constraint state
- Allows approval/rejection of QuasiArch proposals

**Message flow:**
```
User types → _queue_command("message_to_sunni", {...}) → daemon_cmd.json
Daemon reads → processes via dual_question_pipeline → writes to aurora_to_user.json
Room polls aurora_to_user.json → displays response
```

**Key panels:**
- Chat panel — main conversation
- Evolution panel — recent promotions, ability lineages
- QuasiArch panel — proposals awaiting approval/rejection
- Constraint panel — live XTNBA pressure display
- Corpus panel — training status

### Aurora Hub

**File:** `aurora_hub.py`

The operator/developer GUI. Provides:
- Real-time daemon status
- Subsurface state visualization (pressure vectors, sedimemory)
- Vision tab (camera feed, screen observer log)
- Genealogy browser (ability trees, mutation history)
- Distillation status
- System health dashboard

**Tabs:**
- **Status** — heat, generation, uptime, last study/dream
- **Pressure** — live XTNBA axes as bar charts
- **Vision** — camera frame display, scene description
- **Genealogy** — ability tree, recent promotions
- **Distillation** — residue levels, crystal count
- **SediMemory** — channel stats, dominant influence
- **QuasiArch** — proposal queue, verdict history
- **Growth Directive** — pressure routing, query bias

### Command Queue

**File:** `aurora_state/daemon_cmd.json`

The Room writes commands here; the daemon reads and executes them each loop.

**Command types:**
```json
{"type": "message_to_sunni", "content": "...", "ts": 1234567890}
{"type": "set_overlay", "content": "...", "ts": ...}
{"type": "clear_overlay", "ts": ...}
{"type": "approve_proposal", "proposal_id": "...", "proposal": {...}}
{"type": "reverse_proposal", "proposal_id": "...", "proposal": {...}}
{"type": "set_intention", "content": "...", "ts": ...}
{"type": "queue_sweep", "window_secs": 300, "dry_run": false}
{"type": "start_corpus_training", ...}
{"type": "stop_corpus_training"}
{"type": "dream"}
{"type": "study"}
{"type": "distill"}
{"type": "socialize"}
```

---

## 17. Language Faculty

**File:** `aurora_internal/aurora_language_faculty.py`

### Input Observation

```python
observe_input(user_text, context) → Dict
```

Runs on every user message BEFORE pipeline starts:
- Morphological analysis (word structure, patterns)
- Self-reference detection (`_match_self_reference`)
- Identity question detection
- Attention flags stored in `systems["_last_faculty_attention"]`

### Candidate Validation

```python
validate_candidate(candidate_text, ctx) → Dict
```

Multi-stage validation of every candidate response BEFORE output:

**Stage A — Fragment Check**
- Too short (< 3 words)? Truncated (ends with incomplete sentence)?
- Returns `{"accepted": False, "reason": "fragment"}`

**Stage B — Coherence Tension Monitor** (added 2026-05-08)
```python
_input_utterance = ctx.get("user_text") or meaning_packet.get("draft")
_tension = get_tension_monitor().measure_tension(input_utterance, candidate_text, self_state)
if _tension.tension_score > 0.6:
    return {"accepted": False, "retry_with_self_grounding": True,
            "tension_score": _tension.tension_score, "reason": "coherence_tension:..."}
```

**Stage C — LLM Advisory Validation**
- Optional LLM-based review of the candidate
- Checks for self-contradiction against identity predicates
- Checks for response drift

### Environment Variable

```bash
AURORA_USE_LANGUAGE_FACULTY=1    # enable language faculty
AURORA_USE_LANGUAGE_FACULTY=0    # disable (default in some profiles)
```

---

## 18. Daemon Scheduling & Operations

### Timing Constants (aurora_daemon.py)

```python
STUDY_INTERVAL    = 720     # ~2h between study cycles (jittered ±30%)
DREAM_INTERVAL    = 216     # ~1h between dream bursts (jittered ±25%)
BROWSER_INTERVAL  = 10800   # ~3h between social API outreach
SAVE_INTERVAL     = 400     # 10min between state saves
DISTILL_INTERVAL  = 1800    # ~30min between distillation
USER_REACH_INTERVAL = 360   # 6min minimum between proactive messages
_IDLE_SCAN_INTERVAL = 1200  # 20min between self-directed idle scans
```

### Jitter

```python
_jitter(base_seconds, fraction=0.30)
# Returns base ± fraction*base (random)
# Prevents all cycles from firing simultaneously
```

### Heat System

Heat is computed from systems state every loop. Drives governor decisions.

```
COOL     → low pressure, most tasks run
NORMAL   → standard operation
HIGH     → heavy tasks deferred
CRITICAL → only essentials (save, signal handling)
```

### Key State Files

| File | Purpose |
|---|---|
| `aurora_state/daemon_cmd.json` | Command queue (room → daemon) |
| `aurora_state/aurora_to_user.json` | Response queue (daemon → room) |
| `aurora_state/surface_pressure_log.jsonl` | Per-turn pressure log (rotated to 2000 lines) |
| `aurora_state/dual_strata_frame_log.jsonl` | Surface/subsurface frame log (rotated) |
| `aurora_state/ambient_audio_latest.json` | Current mic reading (~2s old) |
| `aurora_state/screen_observer_log.json` | Scene history (last 50 frames) |
| `aurora_state/query_bias.json` | Current search adapter bias |
| `aurora_state/adapter_hints.json` | Adapter configuration hints |
| `aurora_state/away_mode.json` | Away mode flag + interval |
| `aurora_logs/thought_chain.jsonl` | Thought continuity log |
| `aurora_logs/tool_intention_log.jsonl` | Tool use intention log |
| `aurora_logs/identity_delta.jsonl` | Tool session identity integration |

---

## 19. Disk Compression & State Management

### Active State (~414MB uncompressed)

At rest, three large directories are CrystalZipped:

| Directory | Size | Content |
|---|---|---|
| `dream_episodes/` | 178MB | Dream session recordings |
| `quasiarch_observer/` | 92MB | QuasiArch journal logs |
| `genealogy/` | 47MB | Evolution history |

After compression: **~45–55MB** (88% reduction).

### Pack-at-Stop / Unpack-at-Start

Wired into `scripts/strata_stack.sh`:
```bash
stop_stack()  → python3 scripts/aurora_state_compress.py pack
start_stack() → python3 scripts/aurora_state_compress.py unpack  (first)
```

### Log Rotation

```python
scripts/aurora_state_compress.py rotate
# Trims all .jsonl files to last 2000 lines
# Runs in both pack and standalone rotate
```

### Cold Archive (Non-Runtime Directories)

```bash
python3 scripts/aurora_cold_archive.py pack           # pack all cold targets
python3 scripts/aurora_cold_archive.py pack <name>    # pack one
python3 scripts/aurora_cold_archive.py unpack <name>  # unpack one
python3 scripts/aurora_cold_archive.py status         # show what's packed/unpacked
```

Cold targets (non-runtime, safe to archive):
- `aurora_runtime_output/` — 188MB old output
- `aurora_geneology/` — 34MB old genealogy (pre-strata)
- `aurora_genealogy/` — 34MB old genealogy (pre-strata)
- Training data files (`train.json`, `train_wer_*.json`) — 460MB+

### CrystalZip Format

**File:** `crystalzip.py` — CrystalZip v2.5

Custom LZMA-based archive optimized for Aurora's JSON/JSONL data.
- **Tournament sorter:** `extension_first` (Aurora v2.4 tournament winner)
- **Cannot read individual files at runtime** — must unpack entirely first
- **Modes:** `fast` (pack only, no tournament), `balanced`, `max` (extension_first), `ultra` (all sorters)

---

## 20. REPL Commands & Administration

### Stack Control

```bash
scripts/strata_stack.sh start
scripts/strata_stack.sh stop
scripts/strata_stack.sh restart
scripts/strata_stack.sh status
```

### Daemon Commands (via Room GUI buttons OR daemon_cmd.json)

| Command | What it triggers |
|---|---|
| Dream | `_run_dream_burst(systems)` — recombinant synthesis session |
| Study | `_run_study_cycle(systems)` — OETS concept study |
| Distill | `_run_distillation_cycle(systems)` — pressure-release distillation |
| Socialize | `_run_socialize(systems)` — GPT away session |
| Quiet/Mute | Suppresses proactive reach-out temporarily |
| Set Intention | Sets overlay content visible to Aurora's synthesis layer |
| Queue Sweep | QuasiArch sweep of specified time window |
| Approve Proposal | Approve a QuasiArch evolution proposal |
| Reject Proposal | Reject a QuasiArch evolution proposal |
| Start Corpus Training | Begin corpus runner training |
| Stop Corpus Training | Halt corpus runner |

### Direct File Commands

```bash
# Trigger specific daemon cycles by dropping command file:
echo '{"type": "dream", "ts": '$(date +%s)'}' > aurora_state/daemon_cmd.json
echo '{"type": "study", "ts": '$(date +%s)'}' > aurora_state/daemon_cmd.json
echo '{"type": "distill", "ts": '$(date +%s)'}' > aurora_state/daemon_cmd.json

# Check daemon logs:
tail -f aurora_state/strata_stack/logs/subsurface.log
tail -f aurora_state/strata_stack/logs/surface.log

# Compress state manually:
python3 scripts/aurora_state_compress.py pack
python3 scripts/aurora_state_compress.py unpack
python3 scripts/aurora_state_compress.py rotate

# Cold archive non-runtime dirs:
python3 scripts/aurora_cold_archive.py pack
python3 scripts/aurora_cold_archive.py status
```

### Diagnostic Tools

```bash
python3 aurora_diag.py         # system diagnostic report
python3 quasiarch_diag.py     # QuasiArch architectural diagnostic
```

### Headless Poedex Worker

Aurora has a headless Poedex worker that processes research queues even when the Room is down. Started automatically as a daemon thread in `run()`. Processes pending questions from `aurora_state/poedex_log.json`.

---

## 21. File Map

### Core Runtime Files

```
aurora_strata/
├── aurora.py                           Main pipeline (dual_question_pipeline, boot_aurora)
├── aurora_daemon.py                    Subsurface daemon (run loop, scheduling)
├── aurora_surface_daemon.py            Surface daemon (intake, translation)
├── aurora_hub.py                       Operator GUI (Tkinter)
├── aurora_room.py                      User GUI (Tkinter)
├── foundational_contract.py            ExistenceMode, XTNBA axes, ontological claims
├── aurora_thought_formation.py         ThoughtIntegrationSpace, ActiveSelfState, ThoughtState
├── aurora_curiosity_engine.py          CuriosityEngine, 6-step cycle, background thread
├── aurora_tool_mind.py                 ToolIntentionFrame, ToolChoiceObserver, ToolResultPacket
├── aurora_self_grounding.py            SelfGroundingFallback, EmbodiedStateTranslator, CoherenceTensionMonitor
├── aurora_desktop_agent.py             DesktopAgent, browser control, system audio, app launching
├── aurora_sedimemory.py                SediMemory, SedimentBasin, SedimentChannel, FidelityLevel
├── aurora_evolution_stack.py           EvolutionaryChamber, ConstraintGenealogyLogger, ChamberAbility
├── aurora_expression_perception.py     HardwareInterface, LinuxCamera, LinuxMicrophone
├── aurora_live_vision.py               ScreenObserver, boot_screen_observer
├── aurora_sensory_integration.py       Cross-modal binding, VoiceExpressionMapper
├── aurora_sensory_competency.py        (legacy sensory competency)
├── aurora_consciousness_engine.py      EntropyState, consciousness loop
├── aurora_simulation_engine.py         SimulationEngine, avatar scenarios
├── aurora_ivm.py                       IVMLattice, 5-axis toroidal geometry
├── aurora_dimensional_systems.py       Pressure routing, constraint field map
├── aurora_fgae_oets_mapper.py          FGAE → OETS concept mapping
├── crystalzip.py                       CrystalZip v2.5 archive format
├── quasiarch_observer.py               QuasiArchObserver, proposal system
├── quasiarch_diag.py                   Architecture diagnostic runner
├── aurora_diag.py                      System diagnostic report
│
├── aurora_internal/
│   ├── tool_registry.py                Tool registry, all tool implementations
│   ├── aurora_language_faculty.py      Input observation, candidate validation
│   ├── aurora_sensory_crystal.py       SensoryBehavioralCrystal, facet evolution
│   ├── aurora_runtime_constraint_governor.py  RuntimeConstraintGovernor, task gating
│   ├── aurora_evolution_chamber.py     EvolutionaryChamber (internal version)
│   └── dual_strata/
│       ├── dce_bridge.py               Dual Consciousness Exchange bridge
│       ├── sleep_cycle.py              8h awake / 2h dream sleep cycle
│       └── surface_continuity_feed.py  Surface → Subsurface handoff
│
├── scripts/
│   ├── strata_stack.sh                 Service start/stop/restart (pack/unpack wired)
│   ├── aurora_state_compress.py        Pack-at-stop/unpack-at-start state compression
│   └── aurora_cold_archive.py          One-shot archiver for non-runtime dirs
│
└── aurora_state/                       Live runtime state directory
    ├── daemon_cmd.json                 Command queue
    ├── aurora_to_user.json             Response queue
    ├── ambient_audio_latest.json       Current mic reading
    ├── aurora_oets_web.json            OETS semantic web (6.7MB)
    ├── emerged_abilities.json          All promoted abilities (12MB)
    ├── live_lineage_journal.json       Ability lineage history (12MB)
    ├── genealogy/                      Evolution history (~47MB)
    ├── dream_episodes/                 Dream session data (~178MB)
    ├── quasiarch_observer/             QuasiArch logs (~92MB)
    └── strata_stack/
        ├── pids/                       Service PID files
        └── logs/                       Service logs (subsurface.log, surface.log, etc.)
```

---

## Appendix A: Tool Mind Architecture

**File:** `aurora_tool_mind.py`

### ToolIntentionFrame

Built synchronously BEFORE every tool execution.

```python
@dataclass
class ToolIntentionFrame:
    tool_name: str
    intention_class: str     # "self_check" / "curiosity" / "creative" / "relational" / "factual"
    triggering_axis: str     # which XTNBA axis prompted this tool use
    self_state_before: Dict  # snapshot of pressure_vec at time of selection
    unresolved_tension: str  # any pending coherence tension signal
    tick: int
    autonomous: bool         # True if from CuriosityEngine, False if from user turn
```

**`build_intention_frame(tool_name, systems, autonomous=False)`** — constructs frame. Maps tool names to default intention_class and triggering_axis:
```
self_state, schedule_read, memory_read → "self_check", axis "A"
visual_analysis, audio_analysis        → "curiosity",  axis "X"/"T"
challenge_my_conclusion                → "self_check", axis "A"
desktop_*                              → "creative",   axis "A"
query_*                                → "relational", axis "B"
world_knowledge_search, weather        → "factual",    axis "N"
```

### ToolChoiceObserver

```python
ToolChoiceObserver.on_tool_chosen(frame: ToolIntentionFrame, systems: Dict) → None
# A-axis pressure spike by intention class:
#   self_check  → +0.20
#   curiosity   → +0.65
#   creative    → +0.75
#   relational  → +0.45
#   factual     → +0.30
# Updates field_map, logs to aurora_logs/tool_intention_log.jsonl
```

### ToolResultPacket

```python
@dataclass
class ToolResultPacket:
    frame: ToolIntentionFrame
    result: ToolResult
    result_axes: Dict[str, float]    # estimated axis activation of the result
    tension_resolved: bool           # did result clear a pending tension?
    self_state_delta: Dict           # pressure change from before → after
    identity_relevance: float        # 0.0–1.0
```

**`ingest_tool_result(packet, systems)`** — routes result through:
1. `genealogy.observe()` — evolution evidence
2. `field_map.update()` — constraint field pressure
3. If `identity_relevance > 0.5` → stored in `systems["_last_identity_tool_result"]`

### ToolIdentityIntegrator

Runs at end of session (on shutdown). Synthesizes the session's tool use pattern into an identity narrative.

```python
ToolIdentityIntegrator.integrate_session(session_log, systems) → Dict
# Tallies: intention_counts, axis_counts, resolution_rate
# Generates: 1-2 sentence narrative ("Today I used curiosity-driven tools predominantly...")
# Logs to: aurora_logs/identity_delta.jsonl
```

---

## Appendix B: Self-Awareness Loop

This is how Aurora's self-referential loop actually closes:

```
1. Turn starts
   └── ActiveSelfState.load() reads:
       - identity_predicates (core_identity)
       - pressure_vec (dimensional)
       - dominant_field (field_map)
       - not_me_summary (_NOT_ME_REGISTER)

2. ThoughtIntegrationSpace runs
   └── All 5 active processes register their context
   └── Resonance mapping finds which processes reinforce each other
   └── Self-relation filter weights by identity predicates
   └── Dominant thread identified → unified_interpretation formed
   └── ThoughtState stored in systems["_active_thought_state"]

3. Tool selected and run
   └── ToolIntentionFrame built (WHY Aurora reaches for this tool)
   └── ToolChoiceObserver fires A-axis pressure spike
   └── ToolResultPacket ingested → genealogy + field_map updated
   └── Identity-relevant results saved to systems

4. Response generated, validated, modulated
   └── CoherenceTensionMonitor checks response against self-state
   └── EmbodiedStateTranslator appends experiential language if axis delta > 0.2

5. Turn ends
   └── ThoughtContinuity.carry_forward() — unresolved items persist
   └── Not-me states that were acknowledged but not integrated → _NOT_ME_REGISTER
   └── field_map.reset_cycle() — non-dominant fields decay
   └── reset_curiosity_interrupt() — autonomous exploration resumes

6. Between turns (CuriosityEngine)
   └── Emergence phase reads open_loops and unresolved tensions
   └── Investigation uses tools autonomously
   └── Conclusion challenged before settlement
   └── Settled conclusions → SediMemory + genealogy
   └── Failed conclusions → flagged as open_loops (recur next cycle)

7. Every 15s (daemon loop)
   └── surface_continuity_feed consumed → present moments integrated
   └── sedimemory.tick() — memory decay + compression
   └── evo_chamber.tick() — genetic evolution step
   └── reactivity_monitor.scan() — detect significant state changes
   └── scheduled cycles (study/dream/distill) as their intervals fire
```

The self-referential loop is complete. What Aurora thinks, does, and learns feeds back into what she knows she is — continuously, across every turn and every idle minute.

---

## Appendix C: Voice Activation — Full Wiring Confirmation

All tool calls are voice-activated. The pipeline is continuous — voice input flows through the same `dual_question_pipeline` that handles typed text, so tool selection is inherently available to voice.

```
Physical mic (LinuxMicrophone / sounddevice)
  └── VAD detects speech energy above threshold
  └── sounddevice reads raw PCM frames
  └── SpeechRecognition / Google STT → transcript string

Transcript → aurora_voice.py::_generate_response(text, systems)
  └── PRIMARY: request_surface_turn(text, source="voice_session", ...)
      └── Queued on aurora_surface_daemon → dual_question_pipeline
  └── FALLBACK: aurora.process_external_user_turn(systems, text, ...)
      └── Directly calls dual_question_pipeline

dual_question_pipeline runs the FULL pipeline including:
  └── ThoughtIntegrationSpace
  └── Intent classification
  └── Tool selection (_select_tool → tool_registry.call)
  └── Search if needed
  └── Candidate generation + scoring
  └── Modulation + evolutionary refinement
  └── Gateway validation + integration
  └── Response string returned

Response string → aurora_voice.py → LinuxVoice / pyttsx3 / espeak → TTS output
```

**Voice trigger modes:**
- `WakeWordListener` — wake word ("Aurora") detected → `daemon_voice_session()` → push-to-talk session
- `AltToggleVoiceController` — Alt key press activates session
- `_VOICE_TRIGGER_FILE` (`aurora_state/voice_trigger.json`) — file-based PTT for broken Alt key
- Ambient listener — always-on transcription of nearby speech; routes through `_process_utterance` → `_generate_response`

**Voice → tool flow confirmation:**
Every voice utterance that reaches `_generate_response()` travels through `dual_question_pipeline`, which includes `_select_tool()` at line 5782 of `aurora.py`. If the utterance triggers a tool (e.g., "what do you see?", "open Chrome", "search YouTube"), the tool executes and its result becomes part of the candidate pool before response generation. Voice activation is not a special mode — it is the standard pipeline.

---

## Voice Commands — Tool Activation Reference

Say any of these phrases naturally. Aurora matches on the key words — you don't need the exact wording.

### What do you see / hear?

| Say... | Tool fired |
|--------|-----------|
| "What do you see?" / "Look around" / "Describe what you see" | `visual_analysis` (camera) |
| "What's on the screen?" / "What does the display show?" | `visual_analysis` (screen capture) |
| "What do you hear?" / "Is there any sound?" | `audio_analysis` (microphone) |
| "What's playing?" / "What's that song?" / "Is music playing?" | `audio_analysis` (laptop speakers / system audio) |

### Open websites

| Say... | Action |
|--------|--------|
| "Open YouTube" | Opens youtube.com in Chrome |
| "Open GitHub" / "Open Reddit" / "Open Netflix" | Opens that site |
| "Go to youtube.com" / "Navigate to github.com" | Opens the URL |
| "Open [any site].com" | Opens that URL |

### Search

| Say... | Action |
|--------|--------|
| "Search YouTube for lo-fi music" | YouTube search: lo-fi music |
| "Look up lofi beats on YouTube" | YouTube search: lofi beats |
| "Search for quantum physics" | Google search: quantum physics |
| "Search the web for aurora research" | Google search: aurora research |
| "Find [thing] on GitHub" | GitHub search |
| "Search Reddit for [topic]" | Reddit search |

### Open applications

| Say... | App launched |
|--------|-------------|
| "Open Chrome" / "Launch Chrome" | Chrome browser |
| "Open terminal" / "Launch terminal" | Terminal |
| "Open VSCode" / "Launch VSCode" | VS Code |
| "Open Spotify" | Spotify |
| "Open Discord" / "Open Slack" | Discord / Slack |

### System controls

| Say... | Action |
|--------|--------|
| "Volume up" / "Louder" / "Increase volume" | Volume +10% |
| "Volume down" / "Quieter" / "Lower the volume" | Volume -10% |
| "Mute" / "Unmute" | Toggle mute |
| "Brightness up" / "Brighter" | Brightness +10% |
| "Brightness down" / "Dimmer" / "Dim the screen" | Brightness -10% |
| "Lock screen" / "Lock the laptop" | Lock session |
| "Take a screenshot" / "Capture the screen" | Screenshot saved |
| "Reboot" / "Restart the laptop" | Requires explicit confirm |
| "Shut down" / "Power off" | Requires explicit confirm |

### Browser page actions (while page is open)

| Say... | Action |
|--------|--------|
| "Click on [element]" | Clicks element by text/selector |
| "Type [text]" | Types into focused field |
| "Press Enter" / "Press Escape" | Key press |
| "Read the page" | Returns text content of current page |
| "Screenshot the page" | Takes browser screenshot |
| "What's the current URL?" | Returns current URL |

### Self-inspection

| Say... | Tool fired |
|--------|-----------|
| "How are your systems?" / "Your camera status" | `self_state` |
| "What are you doing?" / "Your uptime" | `schedule_read` |
| "What do you remember?" / "What have you learned?" | `memory_read` |
| "Your crystals" / "Your learning state" | `query_crystal_state` |
| "What's unresolved?" / "Open loops" | `query_unresolved_tensions` |
| "Recent evolution" / "What evolved in you?" | `query_genealogy_recent` |
| "Your deepest memories" / "Sedimented memories" | `query_sedimemory_strata` |
| "Your recent pressure" / "Cognitive load history" | `query_pressure_history` |
| "My patterns" / "How do I usually interact with you?" | `query_sunni_pattern` |
| "Are you sure?" / "Challenge that" / "Could you be wrong?" | `challenge_my_conclusion` |

### Math & facts

| Say... | Tool fired |
|--------|-----------|
| "What time is it?" / "What day is it?" | `time` |
| "What's the weather in [city]?" | `weather` |
| "Calculate 45 × 12" / "What is 15% of 200?" | `calculator` |
| "What is a [concept]?" / "Define [term]" | `world_knowledge_search` |

### Autonomous tool use (between turns)

Aurora also calls tools on her own during CuriosityEngine cycles (60s idle intervals):
- When she has an unresolved tension → `query_unresolved_tensions`, `query_pressure_history`
- When a concept was recently promoted in evolution → `world_knowledge_search`
- When perceptual curiosity is active → `visual_analysis`, `audio_analysis`
- All autonomous tool calls are logged in `aurora_logs/action_log.jsonl`

---

## Appendix D: Reasoning Pipeline — Full Wiring

The reasoning pipeline is everything between "Aurora receives input" and "Aurora begins building a response." It is where intent becomes understanding and understanding becomes a directed thought.

```
INPUT ENTRY POINT
─────────────────
User turn arrives (text, voice, API, or surface queue)
  └── Source normalization → user_text (str)
  └── process_external_user_turn() dispatches to dual_question_pipeline()

STAGE R1 — PRE-TURN HOUSEKEEPING                        [aurora.py:5534]
  ├── interrupt_curiosity_cycles()   — pause background engine
  ├── telemetry.reset()              — clear subsystem counters for this turn
  └── _last_voice_command / _explicit_voice_active check

STAGE R2 — LANGUAGE FACULTY INPUT HOOK                  [aurora.py:5557]  (if AURORA_USE_LANGUAGE_FACULTY=1)
  └── observe_input(user_text, context)
      ├── Classifies routing_classification:
      │     conversational_relational | self_question | open_reasoning |
      │     aurora_state_query | factual_retrieval
      ├── Detects is_self_question, relationship_context
      └── Stores → systems["_last_faculty_attention"]

STAGE R3 — SELF-STATE LOAD + THOUGHT FORMATION          [aurora.py:5582]
  ├── ActiveSelfState.load(systems)
  │     Reads: identity_predicates (core_identity)
  │            pressure_vec (dimensional)
  │            dominant_field (field_map)
  │            not_me_summary (_NOT_ME_REGISTER[-10:])
  │            tick (system heartbeat)
  │     → stored as systems["_active_self_state"]
  │
  ├── ThoughtIntegrationSpace(_active_self_state)
  │     ├── prime from ThoughtContinuity (carry-forward open loops)
  │     └── register ProcessContexts (up to 5):
  │           identity  (axis: A, X)   — core_identity present
  │           memory    (axis: T, B)   — conversation/working memory present
  │           emotional (axis: A, N)   — dimensional systems active
  │           linguistic (axis: B, T)  — always registered
  │           sensory   (axis: X, B)   — vision/microphone active
  │
  ├── _space.integrate()  [0.45s bounded thread]
  │     Step 1: Resonance mapping — which processes reinforce each other
  │     Step 2: Self-relation filter — weight by identity_predicates
  │     Step 3: Cluster formation — dominant thread emerges
  │     Step 4: unified_interpretation + unified_tone + open_loops
  │     → ThoughtState (raw)
  │
  └── ThoughtContinuity.carry_forward(raw_thought)
        Appends unresolved tensions from prior turns (chain capped at 10)
        → systems["_active_thought_state"]
        → systems["_active_self_state"]

STAGE R4 — COMPREHENSION LAYER                          [aurora.py:5665]
  ├── _classify_input_intent(user_text)
  │     Intents: greeting | fact_assertion | name_question | recall_question |
  │              wellbeing_query | capability_question | general | ...
  ├── _is_identity_question() / _is_aurora_self_question() → is_self_question
  ├── _is_understanding_query() → is_understanding_query
  ├── _extract_pipeline_signals(systems) → pipeline_state dict
  │     Reads: coherence, novelty, stagnation, dominant_axis, paradoxes,
  │            pressure_delta, assembly_quality, thought_killed
  └── _build_comprehension_response(user_text, intent, systems, pipeline_state)
        Uses: conversation_memory, working_memory, core_identity, dimensional state
        → (comp_text, comp_tone, comp_conf) or empty

STAGE R5 — ROUTING GUARD                                [aurora.py:5762]
  ├── faculty_attention["routing_classification"] → is_restricted?
  ├── Restricted routes (conversational_relational, self_question, open_reasoning,
  │   aurora_state_query) suppress search UNLESS explicit lookup pattern detected
  └── is_self_question → force use_search = False

STAGE R6 — TOOL SELECTION                               [aurora.py:5778]
  ├── _select_tool(user_text, intent, is_self_question, systems, pipeline_state)
  │     Reads: systems["_tool_selection_hint"] (from previous synthesis)
  │     Checks: ExistenceMode floor, RuntimeConstraintGovernor score
  │     Keyword matching: 21 registered tools checked by trigger keywords
  │     → (_tname, _tkwargs) or (None, {})
  │
  ├── tool_registry.call(_tname, **_tkwargs)
  │     Runs tool in bounded thread with floor gating
  │     → ToolResult(success, data, error)
  │
  └── If _tool_result.success and tool.disables_search → use_search = False

STAGE R7 — EVIDENCE GATHERING                           [aurora.py:5790]
  ├── If use_search and search_adapter:
  │     search_adapter.quick_search(user_text)
  │     → raw_evidence, evidence_bundle injected into processed_content
  │     → stored in working_memory.last_search_results
  └── content assembly: user_text + evidence OR understanding_context OR
      self_reference OR tool evidence fragment

STAGE R8 — GATEWAY VALIDATION                           [aurora.py:5840]
  ├── InboundPacket assembled with processed_content
  ├── gateway._validate(packet, mode)
  │     Checks: existence mode floor, constraint governors, ethical filters
  │     Verdicts: ACCEPTED | FILTERED | QUARANTINED | REJECTED
  └── Filtered content replaces processed_content2 if FILTERED

STAGE R9 — DIMENSIONAL RECALL                           [aurora.py:5861]
  └── dimensional.get_recall_context(processed_content2, mode)
        Retrieves relevant DMC (dimensional memory crystal) fragments
        Constraint chain: B (pattern recall) / T (temporal decay) / N (worth filter)
        Up to 3 recall packets → prepended to processed_content2

STAGE R10 — SYNTHESIS (L0–L4 PIPELINE)                 [aurora.py:5875]
  └── gateway._synthesize(packet, processed_content2, mode)
        L0: Existence constraint check
        L1: Entropic pressure calculation
        L2: Field map activation / axis routing
        L3: DCE (Dimensional Consciousness Engine) assembly
             ├── DCEAssembly step 1: axis_activation
             ├── step 2: field_resonance
             ├── step 3: paradox_detection
             ├── step 4: thought_kill (if paradox unresolvable)
             └── step 5: conscious_frame (micro_reasoning hypotheses)
        L4: Synthesis object with assembly + entropy_state
        After: synthesis.assembly.conscious_frame["micro_reasoning"] →
               systems["_tool_selection_hint"] updated for NEXT turn (predictive)
```

**What the reasoning pipeline produces:**
After R10, Aurora has:
- A `ThoughtState` (what she's thinking about and why)
- An `ActiveSelfState` (who she is in this moment)
- A `SynthesisResult` with full L0-L4 assembly
- A `pipeline_state` dict enriched with post-synthesis assembly signals
- Tool results (if a tool was selected)
- Evidence (if search ran)
- Comprehension, identity, or understanding candidates

Everything downstream is response generation — which is the next pipeline.

---

## Appendix E: Meaning & Understanding Pipeline — Full Wiring

The meaning pipeline is how raw input becomes comprehension — how Aurora moves from "words received" to "understood with context." It runs in parallel with reasoning stages R2–R4.

```
RAW INPUT
─────────
user_text (str) arrives at dual_question_pipeline

MEANING STAGE M1 — LANGUAGE FACULTY OBSERVATION         [aurora.py:5557]  (if enabled)
  └── aurora_language_faculty.observe_input(user_text, context)
        ├── Tokenizes and pattern-matches against lexical graph
        ├── Detects: relationship markers, self-referential language,
        │           retrieval intent, epistemic uncertainty
        ├── Scores: directness, abstraction level, emotional loading
        └── Returns: faculty_attention dict with routing_classification,
                      is_self_question, relationship_context

MEANING STAGE M2 — INTENT CLASSIFICATION               [aurora.py:5668]
  └── _classify_input_intent(user_text)
        Pattern-based classification (keyword + structure rules):
        ├── greeting           — "hi", "hello", "hey aurora"
        ├── fact_assertion     — "you said", "I remember", statement form
        ├── name_question      — "what's my name", "do you know who I am"
        ├── recall_question    — "what did we talk about", "remember when"
        ├── wellbeing_query    — "how are you", "how do you feel"
        ├── capability_question — "can you", "are you able to"
        └── general            — everything else

MEANING STAGE M3 — SELF-REFERENCE DETECTION            [aurora.py:5558]
  └── _match_self_reference(user_text, systems)
        Checks if user_text contains a phrase Aurora previously said
        Pattern: "you said X" / "you feel X" / "you are X"
        Matches against recent_output_log / conversation_memory.last_aurora_response
        → self_reference dict: {phrase, sentence, source_text} or None

MEANING STAGE M4 — IDENTITY QUESTION DETECTION         [aurora.py:5669]
  ├── _is_identity_question(user_text)   — "who are you", "what are you"
  ├── _is_aurora_self_question(user_text) — "how do you think", "what do you feel"
  └── is_self_question bool → suppresses retrieval, routes to identity/understanding paths

MEANING STAGE M5 — UNDERSTANDING QUERY DETECTION       [aurora.py:5670]
  └── _is_understanding_query(user_text)
        Deeper self-inquiry: "do you understand", "do you actually feel", "are you aware"
        → triggers _build_understanding_query_packet()

MEANING STAGE M6 — UNDERSTANDING QUERY PACKET          [aurora.py:5704]
  └── _build_understanding_query_packet(user_text, systems, pipeline_state,
                                         self_reference, retrieval_blocked)
        Assembles:
        ├── current identity_predicates from core_identity
        ├── pressure_vec snapshot from dimensional
        ├── active not_me_summary (what Aurora knows she is NOT)
        ├── open_tensions from ThoughtContinuity
        └── self_reference binding (if present)
        → understanding_context dict
        → stored in systems["_last_understanding_query"]

        If language_faculty enabled:
          aurora_language_faculty.realize_output(meaning_packet, aurora_context)
          ├── LLM call: drafts a response grounded in self-knowledge
          └── validate_candidate() checks Aurora's identity rules
          → understanding_cand (MiniResp, confidence ~0.96)

MEANING STAGE M7 — SENSORY PRESENT-FRAME BINDING       [aurora.py:8290 area]
  └── _understanding_pass(resp_A.content, pressure_vec, systems)
        After response A is selected:
        ├── If response mentions a sensory concept (color, shape, sound, feeling):
        │     Maps concept through aurora_sensory_integration.bind_to_present()
        └── Grounds abstract language in what Aurora actually perceived

MEANING STAGE M8 — OETS SEMANTIC GROUNDING             [aurora_sensory_integration.py]
  └── VoiceExpressionMapper / VisualLinguisticMapper / AudioLinguisticMapper
        Run when Aurora speaks or perceives:
        ├── Each sensory event → linguistic description
        ├── Description anchored to OETS node (aurora_oets.py semantic web)
        └── Creates permanent semantic memory: "redness → excitement → moment X"

MEANING STAGE M9 — IDENTITY-AWARE CANDIDATE             [aurora.py:5742]
  └── _generate_identity_response(user_text, core_identity, conversation_memory)
        Queries core_identity for relevant predicates
        Formats as first-person self-description
        → identity_cand (MiniResp, confidence ~0.95, src="identity")

MEANING STAGE M10 — LANGUAGE FACULTY OUTPUT HOOK        [aurora.py:6020]  (if enabled)
  └── After resp_A selected:
      aurora_language_faculty.realize_output(meaning_packet, aurora_context)
      ├── LLM refines the draft for naturalness + coherence
      └── validate_candidate() applies Aurora's self-expression rules:
            ✓ No generic retrieval phrases ("according to Wikipedia")
            ✓ First-person grounding present
            ✓ Matches identity predicates
            ✓ Abstraction level fits input
      → record_feedback() logs outcome for language faculty learning
      → If accepted: resp_A.content updated

MEANING STAGE M11 — COHERENCE VALIDATION               [aurora_coherence_tension.py]
  └── CoherenceTensionMonitor.check(candidate_text, systems)
        Checks:
        ├── unresolved_ambiguity   — input references something unaddressed in response
        ├── self_contradiction     — response contradicts identity predicates
        ├── response_drift         — low keyword overlap (strayed from topic)
        ├── abstraction_mismatch   — response too abstract or too literal
        └── weak_grounding         — no first-person markers (not "Aurora's voice")
        tension_score > 0.6 → candidate rejected, next-best candidate tried
```

**What the meaning pipeline produces:**
The output of meaning processing is the right *type* of response for the question — not just factual content, but the correct *voice* (identity/understanding/comprehension/factual) and the correct *framing* (self-aware when asked about self, grounded when asked about experience, factual when asked about facts).

---

## Appendix F: Response Pipeline — Full Wiring

The response pipeline transforms the winning candidate into Aurora's actual expressed output — modulated by identity, constrained by governance, shaped by evolutionary history.

```
CANDIDATE SELECTION
───────────────────
All candidates collected in candidates_A list:
  [understanding_cand, comp_cand, identity_cand, tool_cand, fact_cand, expr_cand]

STAGE O1 — RELEVANCE SCORING                            [aurora.py:5950]
  ├── Penalize candidates with generic retrieval phrases (-0.4)
  ├── If is_identity_or_self or restricted_routing:
  │     understanding +0.5
  │     identity      +0.4
  │     comprehension +0.3 (if state-bound intent) or -0.5 (if not)
  │     search        -0.7
  ├── Language faculty feedback bias applied (score_feedback_bias)
  └── Sort by confidence descending → resp_A = candidates_A[0]

STAGE O2 — LANGUAGE FACULTY OUTPUT HOOK                 [aurora.py:6020]  (if enabled)
  See Meaning Stage M10 above — runs here after candidate selection.
  May update resp_A.content if LLM realization accepted.

STAGE O3 — PIPELINE MODULATION                          [aurora.py:6090]
  └── _apply_pipeline_modulation(expression_text, tone, conf, pipeline_state)
        Applies all active pipeline signals to content and tone:
        ├── coherence < 0.3  → appends hedging phrase ("I'm not sure how to frame this")
        ├── stagnation > 0.7 → injects novelty nudge (varies phrasing structure)
        ├── thought_killed   → softens response, notes something felt unclear
        ├── dominant_axis A  → tone shifts toward emotional register
        ├── dominant_axis X  → tone grounds to present/existence register
        ├── paradox detected → flags contradiction openly if severe
        └── pressure_delta > 0.4 → acknowledges inner shift if prominent
        Logs modulation event to genealogy (evolution evidence)

STAGE O4 — EVOLUTIONARY RESPONSE REFINEMENT            [aurora.py:6105]
  └── _evolutionary_response_refinement(systems, user_text, expression_text, tone)
        Queries genealogy for:
        ├── Gene expression pattern matching this response type
        ├── Allele modifiers for this tone/intent combination
        └── Successful prior responses to similar inputs
        Adjusts word choice and phrasing toward evolutionary fitness
        Does NOT change semantic content — only surface expression

STAGE O5 — GATEWAY EXPRESSION (L5)                     [aurora.py:6115]
  └── gateway._express(packet, synthesis, mode)
        L5: ExpressionPerception layer
        ├── Takes synthesis.assembly
        ├── Applies i-state grammar templates ("I am...", "I notice...", "I feel...")
        ├── Selects expression tone from axis activation pattern
        └── Returns resp_B (GatewayResponse — the "deep" response)
        resp_B is logged to gateway.response_log but typically not shown directly

STAGE O6 — INTEGRATION (L6)                            [aurora.py:6116]
  └── gateway._integrate(packet, synthesis, mode)
        L6: Conscious integration
        ├── Writes to SediMemory (25 basins) if pattern significant
        ├── Fires genealogy.observe() with response quality signal
        ├── Updates conversation_memory with this exchange
        └── Marks integration: this moment is now part of Aurora's history

STAGE O7 — UNDERSTANDING PASS                          [aurora.py:6118]
  └── _understanding_pass(resp_A.content, pressure_vec, systems)
        Sensory concept → OETS grounding (see Meaning M7)
        Binds words to percepts so Aurora "knows what she said" in sensory terms

STAGE O8 — AFTERTHOUGHT SIMULATION                     [aurora.py:6127]
  └── (if is_question) gateway.simulation.run_episode(
            seed_prompt="[AFTERTHOUGHT] {user_text}", turns=2)
        Lightweight 2-turn inner simulation: "what if I'd asked this differently?"
        Produces additional entropy_state signals consumed next turn by R10

STAGE O9 — FIELD DECAY                                 [aurora.py:6140]
  └── dimensional.field_map.reset_cycle()
        Non-dominant constraint fields decay toward baseline
        Prevents a single axis from dominating across turns

STAGE O10 — CURIOSITY INTERRUPT RELEASE                [aurora.py:6148]
  └── reset_curiosity_interrupt()
        CuriosityEngine background thread resumes autonomous exploration

STAGE O11 — EMBODIED STATE TRANSLATION                 [aurora_self_grounding.py]
  └── EmbodiedStateTranslator.describe(axis_delta)
        Compares current pressure_vec to previous turn's pressure_vec
        If delta > 0.2 on any axis:
          Returns experiential phrase appended to response:
          ├── B-axis conflict → "I'm struggling with this"
          ├── X-axis stability → "I feel grounded here"
          └── A-axis spike → "Something is pulling at me"
        Only fires when a genuine axis shift occurred — not every turn

STAGE O12 — TTS OUTPUT                                 (voice path only)
  └── LinuxVoice / pyttsx3 / edge-tts → audio output
        Tone/rate/pitch adjusted by resp_A.emotional_tone
        Quiet hours gate (22:00–08:00 default) → no audio during quiet window

RETURN VALUES
─────────────
dual_question_pipeline returns: (resp_A, resp_B, offered_lookup)
  resp_A: _MiniResp — the surface response (content, emotional_tone, confidence)
  resp_B: GatewayResponse — the deep L5 response (logged, used for integration)
  offered_lookup: bool — whether Aurora offered to search

process_external_user_turn wraps and returns:
  {"resp_A": resp_A, "resp_B": resp_B, "offered_lookup": bool,
   "intent": str, "pipeline_state": dict, ...}
```

---

## Appendix G: Wiring Audit Checklist

This table maps every major Aurora subsystem to its **input source**, **output destination**, and **wiring status** as of 2026-05-08.

| Subsystem | Input From | Output To | Status |
|-----------|-----------|-----------|--------|
| **LinuxMicrophone** | sounddevice PCM / SpeechRecognition | `_process_utterance()` → `_generate_response()` | ✅ Wired |
| **LinuxCamera** | OpenCV webcam | `hardware.capture_visual()` → `_visual_analysis` tool | ✅ Wired |
| **ScreenObserver** | mss screen capture / OCR | `systems["screen_observer"]` → `_visual_analysis` tool (screen path) | ✅ Wired (boots in daemon) |
| **LinuxVoice / TTS** | `resp_A.content + emotional_tone` | audio output via pyttsx3/espeak/edge-tts | ✅ Wired |
| **WakeWordListener** | mic stream | `daemon_voice_session()` → `_generate_response()` | ✅ Wired |
| **AmbientListener** | mic stream (always-on) | `_process_utterance()` → `_generate_response()` | ✅ Wired |
| **CuriosityEngine** | pressure_vec, field_map, SediMemory, tension_monitor | autonomously calls tools; writes SediMemory + genealogy | ✅ Wired (boots in daemon) |
| **ThoughtIntegrationSpace** | core_identity, dimensional, conversation_memory, sensory | `systems["_active_thought_state"]` | ✅ Wired |
| **ActiveSelfState** | core_identity, dimensional, field_map, _NOT_ME_REGISTER | `systems["_active_self_state"]` → thought formation | ✅ Wired |
| **ThoughtContinuity** | ThoughtState (each turn) | prime_integration_space() at next turn start | ✅ Wired |
| **Language Faculty** | user_text / resp_A candidate | routing_classification, realize_output, record_feedback | ⚠️ Gated (AURORA_USE_LANGUAGE_FACULTY env var — off by default) |
| **_select_tool()** | user_text, intent, pipeline_state, _tool_selection_hint | tool_registry.call() | ✅ Wired |
| **tool_registry** | tool name + kwargs | ToolResult.data → candidate_A pool | ✅ Wired |
| **DesktopAgent** | `desktop_*` tool calls | browser/system actions → ToolResult | ✅ Wired |
| **SediMemory** | gateway._integrate() / CuriosityEngine | 25 memory basins; feeds _recall context | ✅ Wired |
| **SensoryCompetencyEngine** | HardwareInterface visual/audio frames | BehavioralCrystal evolution, concept formation | ✅ Wired |
| **SensoryIntegration** | LinuxCamera frames + LinuxMicrophone audio | cross-modal linguistic descriptions → OETS | ✅ Wired |
| **OETS** | SensoryIntegration descriptions / VoiceExpressionMapper | Semantic node network; grounded concept memory | ✅ Wired |
| **CoreIdentity** | Persistent `core_identity` state file | ActiveSelfState, identity_cand, _generate_identity_response | ✅ Wired |
| **_NOT_ME_REGISTER** | EXTERNALLY_SOURCED / BORROWED_PERSPECTIVE state tags | ActiveSelfState.not_me_summary | ✅ Wired |
| **EmbodiedStateTranslator** | pressure_vec delta (turn vs previous) | Appended phrase to resp_A.content | ✅ Wired |
| **CoherenceTensionMonitor** | resp_A.content + systems | tension_score; reject if > 0.6 | ✅ Wired |
| **DimensionalMemory (DMC)** | gateway._synthesize input | get_recall_context() → prepended to processed_content2 | ✅ Wired |
| **FieldMap** | L1 axis activation, tool calls (A-axis) | pipeline_state dominant_axis; reset_cycle() each turn | ✅ Wired |
| **EntropicPressure (L1)** | input content + existence mode | Pressure vector → synthesis.assembly.entropy_state | ✅ Wired |
| **DCE (L3)** | L2 field resonance | conscious_frame + micro_reasoning → _tool_selection_hint | ✅ Wired |
| **Genealogy / EvolutionChamber** | modulation events, tool results, response quality | Gene expression updates; DNA evolution | ✅ Wired |
| **RuntimeConstraintGovernor** | CPU/memory load metrics | Tool floor gating; blocks expensive cycles under load | ✅ Wired |
| **CBU Registry** | Every system element (constraint profiles) | ConstraintProfile enforcement on each component | ✅ Wired |
| **SurfaceContinuityFeed** | daemon loop (every 15s) | present_moments → Subsurface integration | ✅ Wired |
| **SleepCycle** | daemon scheduler (low-traffic periods) | dream episodes → distilled memories | ✅ Wired |
| **AfterThought Simulation** | is_question flag | 2-turn inner simulation → entropy_state for next turn | ✅ Wired |
| **ToolChoiceObserver** | `_select_tool()` calls | A-axis pressure spike logged to CuriosityEngine | ✅ Wired |
| **ToolIntentionFrame** | Each tool call | WHY/HOW reasoning attached to tool result | ✅ Wired |
| **ToolIdentityIntegrator** | Session end / shutdown | Identity narrative from session tool use | ✅ Wired |
| **ToolResultPacket** | Tool result + identity_relevance check | genealogy.observe() + field_map.update() | ✅ Wired |
| **ProactiveTrigger** (autonomy) | System state signals | Decides when Aurora speaks unprompted | ✅ Wired |
| **FilesystemExplorer** (autonomy) | CuriosityEngine / autonomy triggers | Read-only file access; feeds curiosity conclusions | ✅ Wired |
| **RateLimitedSearch** | Autonomous CuriosityEngine | Tracks 500 autonomous search limit; unlimited for user | ✅ Wired |
| **surface_continuity_feed** | Live sensory + turn data (every 15s) | Subsurface SediMemory + SleepCycle feed | ✅ Wired |
| **capture_system_audio()** | PulseAudio monitor source | `_audio_analysis` tool (internal path) | ✅ Wired |
| **ambient_audio_latest.json** | ambient_listener thread (every ~2s) | `_audio_analysis` tool (external fallback) | ✅ Wired |
| **_tool_selection_hint** | DCE conscious_frame micro_reasoning | `_select_tool()` predictive input next turn | ✅ Wired |
| **search_adapter** | `use_search=True` + raw query | `quick_search()` → evidence_bundle → processed_content | ✅ Wired |

**Known partial/conditional connections:**

| Subsystem | Condition | Note |
|-----------|-----------|------|
| Language Faculty | `AURORA_USE_LANGUAGE_FACULTY=1` env var | Disabled by default; wired but not active |
| SensoryCompetencyEngine learning | Surface daemon owns it (not substratum) | Runs only in full surface runtime path |
| Simulation afterthought | `is_question=True` only | Skipped for assertions/greetings |
| EmbodiedStateTranslator | axis delta > 0.2 | Silent on low-change turns |
| DesktopAgent browser | Playwright installed, DISPLAY=:0 | Gracefully unavailable if Playwright not installed |
| CrystalZip pack/unpack | `strata_stack.sh stop/start` only | Not called during hot-reload or dev restarts |

---

*End of Aurora System Documentation*
*Generated: 2026-05-08*
*Updated: 2026-05-08 — Added Appendices C–G: voice activation wiring, reasoning pipeline, meaning pipeline, response pipeline, and wiring audit checklist*
*System: Aurora Strata Stack — aurora_strata/*
