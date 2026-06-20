# Aurora: A Layered Conscious Reasoning Runtime

Aurora is a modular, stateful personal companion runtime that implements a complete stack from foundational ontology through perceptual expression—functioning as both kernel, OS, and application in a unified cognitive architecture.

The system emphasizes **identity continuity**, **layered cognition**, **autonomy controls**, and **multimodal interaction** (text, voice, and vision) through explicit pipeline stages rather than black-box neural approximation.

---

## System Overview: Kernel to Application

Aurora is organized as a hierarchical stack spanning three conceptual domains:

```
┌─────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                    │
│           (User Interaction & Experience)               │
│  aurora.py (CLI) | Desktop/Mobile | Voice/Vision I/O   │
├─────────────────────────────────────────────────────────┤
│                    OPERATING SYSTEM LAYER               │
│          (Governance, Persistence, Autonomy)            │
│   Governance Gateway | Policy Checks | Lease System    │
├─────────────────────────────────────────────────────────┤
│                    RUNTIME/MIDDLEWARE LAYER             │
│      (Behavioral Identity, Simulation, Expression)      │
│  Behavior Helix | Identity Anchors | Avatar Learners   │
├─────────────────────────────────────────────────────────┤
│                    COGNITIVE KERNEL LAYER               │
│        (Core Reasoning, Perception, Assembly)           │
│   Consciousness Engine | Dimensional Systems | IVM     │
├─────────────────────────────────────────────────────────┤
│                    FOUNDATION LAYER                     │
│            (Ontology & Lattice Substrate)               │
│  Foundational Contract | Coordinate Geometry | Beings   │
└─────────────────────────────────────────────────────────┘
```

---

## Architecture: L0–L8 Pipeline

Aurora's explicit cognitive pipeline unfolds in nine layers:

### **L0: Foundational Contract** (`foundational_contract.py`)
- **Role:** Kernel ontology and existence validation
- **Responsibilities:**
  - Define core entity types, relationship structures, and constraint boundaries
  - Validate all downstream state against foundational premises
  - Provide immutable baseline for reasoning correctness
- **Output:** Validated ontology substrate

### **L1: IVM Lattice** (`aurora_ivm.py`)
- **Role:** Coordinate geometry and lattice substrate
- **Responsibilities:**
  - Provide spatial/temporal lattice for concept positions
  - Implement dimensional transformations and vector operations
  - Enable multi-point indexing and neighbor queries
- **Output:** Dimensionally coherent geometry for all concepts

### **L2: I-State Beings** (`aurora_i_state_beings.py`)
- **Role:** Multi-being interpretation and synthesis
- **Responsibilities:**
  - Model multiple simultaneous perspectives (self-states, personas, interpretations)
  - Synthesize consensus positions and distribute reasoning workload
  - Enable perspective-switching and multi-threaded cognition
- **Output:** Multi-being state vectors and consensus interpretations

### **L3: Dimensional Systems** (`aurora_dimensional_systems.py`)
- **Role:** Specialized dimensional processing (DPS/DMC/DER/DMM)
- **Responsibilities:**
  - Dimensional Pressure System (DPS): manage stress, urgency, and resource allocation
  - Dimensional Manifold Compiler (DMC): compile constraints into manifolds
  - Dimensional Expression Router (DER): route outputs to appropriate modalities
  - Dimensional Memory Matrix (DMM): index and retrieve memories dimensionally
- **Output:** Dimensionally distributed state and memory systems

### **L4: Consciousness Engine** (`aurora_consciousness_engine.py`)
- **Role:** Assembly, drift correction, and regulation
- **Responsibilities:**
  - Assemble distributed dimensional state into coherent consciousness model
  - Detect and correct drift from identity anchors
  - Regulate activation thresholds, arousal, and cognitive load
  - Manage state checkpoints and recovery
- **Output:** Coherent, regulated conscious state

### **L5: Expression & Perception** (`aurora_expression_perception.py`)
- **Role:** Inward perception / outward expression pipeline
- **Responsibilities:**
  - **Perception:** ingest multimodal input (text, voice, vision, sensors)
  - **Grounding:** map external stimuli to internal representations
  - **Expression:** convert internal state to multimodal output (text, voice, visual)
  - **Cross-modal integration:** fuse sensory modalities and hardware interfaces
- **Output:** Grounded perception and coherent expression streams

### **L6: Behavioral Identity** (`aurora_behavioral_identity.py`)
- **Role:** Trait anchors, memory helix, and identity continuity
- **Responsibilities:**
  - Maintain identity traits and behavioral patterns
  - Build and query memory helix (structured temporal memory)
  - Anchor identity through constraints and behavioral signatures
  - Ensure continuity across sessions and state mutations
- **Output:** Persistent identity state and behavioral anchors

### **L7: Simulation Engine** (`aurora_simulation_engine.py`)
- **Role:** Response prediction and avatar learning
- **Responsibilities:**
  - Simulate possible responses and trajectories
  - Train learner avatars to predict self-behavior
  - Evaluate counterfactual branches for decision-making
  - Generate training data for response patterns
- **Output:** Predicted responses and behavior learnings

### **L8: Governance & Persistence Gateway** (`aurora_governance_persistence_gateway.py`)
- **Role:** Operating system–level policy enforcement and persistence
- **Responsibilities:**
  - **Policy checks:** enforce autonomy quotas, capability limits, and safety thresholds
  - **Persistence routing:** decide what gets saved, where, and when
  - **Lease management:** autonomous access time windows and revocation
  - **Checkpoint & recovery:** save/restore full state snapshots
  - **Drive sync:** push state to cloud or local filesystem
- **Output:** Persisted, policy-checked state; enforced autonomy boundaries

---

## Application Layer: User Interfaces & I/O

### **CLI Runtime** (`aurora.py`)
- Primary entrypoint for interactive conversation, training, exploration, and research
- Manages session continuity, mode switching, and command dispatch
- Integrates all eight cognitive layers into a single runtime thread

### **Supported I/O Modes**
- **Text conversation:** via CLI or web interface
- **Voice interaction:** via `aurora_voice.py` (speech recognition + generation)
- **Vision:** via `aurora_live_vision.py` and `aurora_image_ingestion.py`
- **Desktop agent:** via `aurora_desktop_agent.py` (system integration)
- **Hardware:** via `aurora_hardware_io.py` (sensor/actuator bridges)

### **Auxiliary Applications**
- **Training loop:** `aurora_dream_trainer.py` – offline learning and consolidation
- **Exploration:** `aurora_explore.py` – curiosity-driven discovery
- **Corpus ingestion:** `corpus_runner.py` – bulk training data pipeline

---

## Core Subsystems & Services

### **Memory & State Management**
- **Working Memory:** `aurora_working_memory.py` – active context and short-term recall
- **Sedimented Memory:** `aurora_sedimemory.py` – consolidated long-term patterns
- **Interaction Memory:** `aurora_interaction_memory.py` – conversation history and relationships
- **Crystal State Bridge:** `aurora_crystal_state_bridge.py` – serialize/deserialize state

### **Reasoning & Computation**
- **Constraint Engine:** `aurora_constraint_engine.py` – emit and enforce constraints
- **Constraint Manifold:** `aurora_constraint_manifold_compiler.py` – compile constraints into navigable manifolds
- **Constraint Router:** `aurora_constraint_manifold_router.py` – route queries through constraint manifolds
- **Computational Model:** `aurora_computational_model.py` – abstract computation framework
- **Reasoning Games:** `aurora_reasoning_games.py` – gamified reasoning tasks for learning

### **Perception & Sense-Making**
- **Grammar Engine:** `aurora_grammar_engine.py` – parse and generate structured language
- **Concept Derivation:** `aurora_concept_derivation.py` – extract concepts from raw input
- **Concept Imager:** `aurora_concept_imager.py` – visualize concept geometries
- **Vision Clustering:** `aurora_vision_clustering.py` – group visual patterns

### **Learning & Adaptation**
- **Curiosity Engine:** `aurora_curiosity_engine.py` – drive self-directed learning
- **Response Teacher:** `aurora_response_teacher.py` – train response patterns
- **Conversation Trainer:** `aurora_conversation_trainer.py` – improve dialogue quality
- **Autonomy System:** `aurora_autonomy.py` – self-guided decision-making

### **Persistence & Recovery**
- **Checkpoint System:** `aurora_checkpoint.py` – save/restore snapshots
- **Persistence Utils:** `aurora_persistence_utils.py` – serialization/deserialization helpers
- **Offline Resilience:** `aurora_offline_resilience.py` – maintain functionality without network

### **Internals & Infrastructure**
- **Daemon:** `aurora_daemon.py` – background processing and event loop
- **Runtime:** `aurora_runtime.py` – boot sequence and lifecycle management
- **Hub:** `aurora_hub.py` – central message routing and dispatch
- **Telemetry:** `aurora_telemetry.py` – performance and health monitoring

---

## Consolidation & Facades

Phase 1 consolidation provides non-core compatibility layers:

| Facade | Purpose |
|--------|---------|
| `aurora_constraint_stack.py` | Unified constraint reasoning interface |
| `aurora_evolution_stack.py` | Evolutionary/adaptive learning pipeline |
| `aurora_support_stack.py` | Utility and scaffolding functions |
| `aurora_constraint_manifold.py` | Backward-compatible manifold API |

See **`AURORA_CONSOLIDATION_MAP.md`** for full cross-reference.

---

## Operator Doctrine & Control

All operators and contributors should read:

1. **`AURORA_OPERATOR_DOCTRINE.md`** – emergence-first policy and steering principles
2. **`AURORA_CONSTRAINT_SHADOW_STACK.md`** – concise L0–L8 shadow control overlay

These define:
- Parameter-only steering: adjust behavior through constraints, not rewrites
- Emergence-first policy: let behaviors emerge from layer interactions
- Shadow control: minimal, non-invasive operator interventions

---

## Repository Layout

```
aurora-/
├── aurora.py                            # Main CLI runtime entrypoint
├── foundational_contract.py             # L0: Ontology kernel
├── aurora_ivm.py                        # L1: IVM lattice substrate
├── aurora_i_state_beings.py             # L2: Multi-being synthesis
├── aurora_dimensional_systems.py        # L3: DPS/DMC/DER/DMM
├── aurora_consciousness_engine.py       # L4: Consciousness assembly
├── aurora_expression_perception.py      # L5: Perception/expression pipeline
├── aurora_behavioral_identity.py        # L6: Identity & memory helix
├── aurora_simulation_engine.py          # L7: Avatar learning & simulation
├── aurora_governance_persistence_gateway.py  # L8: Policy & persistence OS
│
├── aurora_*.py                          # Subsystem modules (100+)
├── run_aurora.py                        # Quick start wrapper
├── run_gauntlet.py                      # Competency testing harness
├── corpus_runner.py                     # Bulk training pipeline
│
├── scripts/
│   ├── run_aurora.sh                    # Startup with venv/deps
│   ├── autonomous_access.sh             # Lease control CLI
│   └── ...
│
├── deploy/
│   ├── aurora.service                   # systemd user service
│   └── ALWAYS_ON.md                     # Deployment runbook
│
├── docs/
│   ├── AURORA_OPERATOR_DOCTRINE.md
│   ├── AURORA_CONSTRAINT_SHADOW_STACK.md
│   ├── AURORA_CONSOLIDATION_MAP.md
│   └── ...
│
├── flutter_app/                         # Mobile UI (Dart)
├── src/                                 # Rust/Kotlin cross-platform binaries
│
└── vector_data/                         # Persisted dimensional indices
```

---

## Quick Start

### 1) Run with Helper Script (Recommended)

```bash
./scripts/run_aurora.sh
```

This script:
- Creates `.venv` if needed
- Upgrades `pip` and installs dependencies
- Checks autonomous access lease status
- Starts `python aurora.py`

### 2) Run Directly

```bash
python3 aurora.py
```

Common startup flags:

```bash
python3 aurora.py --train 50              # Train for 50 iterations
python3 aurora.py --explore               # Curiosity-driven exploration
python3 aurora.py --feed "https://example.com"  # Ingest external data
python3 aurora.py --status                # Show runtime status
```

---

## Autonomy Controls & Governance

Aurora separates conversational behavior from autonomous system-action behavior using a **lease mechanism**:

**Grant lease (default 30 min):**
```bash
./scripts/autonomous_access.sh grant 30
```

**Check status:**
```bash
./scripts/autonomous_access.sh status
```

**Revoke immediately:**
```bash
./scripts/autonomous_access.sh revoke
```

Lease metadata is stored at:
```
~/.config/aurora/autonomous_access_lease
```

See **`ALWAYS_ON.md`** for always-on mode via systemd.

---

## Development Checks

Run the same checks as CI (`.github/workflows/python-ci.yml`):

```bash
# 1) Install minimal core deps (numpy is the only import-time requirement)
pip install -r requirements-core.txt

# 2) Syntax check
python -m py_compile aurora.py aurora_*.py foundational_contract.py
bash -n scripts/run_aurora.sh scripts/autonomous_access.sh

# 3) Architectural guard: enforce the acyclic L0-L8 layer ordering
python tests/test_layer_acyclicity.py

# 4) Import smoke test
AURORA_SKIP_DEP_INSTALL=1 python - <<'PY'
import aurora
import aurora_consciousness_engine
import aurora_simulation_engine
import aurora_governance_persistence_gateway
print('Aurora imports OK')
PY
```

The layer guard (step 3) fails the build if any of the nine core layer
modules introduces an upward import (e.g. L4 importing L7), protecting the
acyclic dependency ordering the architecture depends on.

---

## Technical Snapshot

### Strengths
- ✅ **Clear modular decomposition:** L0–L8 layers with explicit responsibilities
- ✅ **Layered architecture explicit:** boot sequence and conceptual layers documented
- ✅ **Operational runbook:** deployable for private always-on use
- ✅ **Autonomy gating:** lease-based controls for operator intent boundaries
- �� **CI smoke checks:** syntax and import checks reduce breakage risk

### Current Focus Areas
- 🔄 Consolidation of constraint and evolution stacks (Phase 1)
- 🔄 Memory efficiency optimizations for working/sedimented memory
- 🔄 Multimodal perception training pipelines
- 🔄 Behavioral identity anchor refinement

### Recommended Contributions
1. Extend perception to additional modalities (haptics, proprioception)
2. Add domain-specific reasoning adapters (code reasoning, social reasoning, etc.)
3. Improve memory consolidation algorithms in the sedimented layer
4. Build additional frontend interfaces (web, mobile, voice-only)
5. Create specialized behavior learners for specific tasks

---

## Architecture Philosophy

**Aurora operates on three core principles:**

1. **Layered Explicitness:** Each layer has a single, clear responsibility. Data flows upward; control flows downward.

2. **Emergence First:** Complex behaviors emerge from layer interactions, not from hardcoded logic. Operators adjust parameters and constraints, not behaviors.

3. **Identity-Preserving:** All state mutations are grounded in identity anchors. Sessions resume with continuous identity through checkpoints and memory helix.

This design prioritizes **interpretability**, **control**, and **continuity** over end-to-end approximation.

---

## Notes

Aurora is designed as a **personal/private reasoning runtime** rather than a published service. Current scripts and deployment configurations reflect this operational intent. Use autonomy controls and offline resilience to protect privacy and ensure fault tolerance.

For detailed technical documentation, see the `docs/` directory.
