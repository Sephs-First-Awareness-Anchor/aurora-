# Aurora

Aurora is a modular, stateful personal companion runtime focused on identity continuity, layered cognition, autonomy controls, and multimodal interaction (text, voice, and vision).

At the center of the repo is `aurora.py`, which boots Aurora’s layered cognitive stack and provides an interactive CLI session for conversation, training, exploration, research, memory recall, and sensory operations.

## Operator doctrine (required)

All CLI operators and contributors should read these first:

- `AURORA_OPERATOR_DOCTRINE.md`
- `AURORA_CONSTRAINT_SHADOW_STACK.md`

These define the emergence-first policy, parameter-only steering policy, and concise shadow control overlay for the L0-L8 stack.

## Aurora architecture (layered model)

Aurora is organized as an explicit pipeline:

1. **Foundational Contract** (`foundational_contract.py`) – ontology and existence validation.
2. **IVM Lattice** (`aurora_ivm.py`) – coordinate geometry and lattice substrate.
3. **I-State Beings** (`aurora_i_state_beings.py`) – multi-being interpretation/synthesis.
4. **Dimensional Systems** (`aurora_dimensional_systems.py`) – DPS/DMC/DER/DMM processing.
5. **Consciousness Engine** (`aurora_consciousness_engine.py`) – assembly, drift correction, regulation.
6. **Expression & Perception** (`aurora_expression_perception.py`) – inward perception/outward expression pipeline.
7. **Behavioral Identity** (`aurora_behavioral_identity.py`) – trait, memory helix, and identity anchors.
8. **Simulation Engine** (`aurora_simulation_engine.py`) – learner/avatars and response simulation.
9. **Governance & Persistence Gateway** (`aurora_governance_persistence_gateway.py`) – policy checks and persistence routing.

Supporting systems include:

- Identity and memory persistence (`aurora_identity_persistence.py`)
- Autonomy controls and quotas (owned by Layer 8: `aurora_governance_persistence_gateway.py`)
- Hardware interface, cross-modal sensory integration, and vision bootstrap (owned by Layer 5: `aurora_expression_perception.py`)
- Drive sync + checkpoint integration (migrated under Layer 8 in `aurora_governance_persistence_gateway.py`)
- Corpus ingestion pipeline (`corpus_runner.py`)

## Consolidation (Phase 1)

Active consolidated non-core facades:

- `aurora_constraint_stack.py`
- `aurora_evolution_stack.py`
- `aurora_support_stack.py`
- `aurora_constraint_manifold.py` (compatibility shim)

Full mapping:

- `AURORA_CONSOLIDATION_MAP.md`

## Repository layout

- `aurora.py` – primary runtime entrypoint.
- `aurora_*.py` – subsystem modules.
- `foundational_contract.py` – foundational ontology constraints.
- `scripts/run_aurora.sh` – startup wrapper (venv/deps/env flags).
- `scripts/autonomous_access.sh` – time-scoped autonomous access lease control.
- `deploy/aurora.service` – systemd user service unit.
- `*.json` – persisted runtime state, memory, criteria, and checkpoints.
- `ALWAYS_ON.md` – always-on operation runbook.

## Quick start

### 1) Run with helper script (recommended)

```bash
./scripts/run_aurora.sh
```

This script:

- creates `.venv` if needed,
- upgrades `pip`,
- checks autonomous access lease status,
- installs missing core runtime dependencies,
- starts `python aurora.py`.

### 2) Run directly

```bash
python3 aurora.py
```

Common startup flags:

```bash
python3 aurora.py --train 50
python3 aurora.py --explore
python3 aurora.py --feed "https://example.com"
python3 aurora.py --status
```

## Autonomous access controls

Aurora separates conversational behavior from autonomous system-action behavior with a lease mechanism.

- Grant lease (default 30 min):

```bash
./scripts/autonomous_access.sh grant 30
```

- Check status:

```bash
./scripts/autonomous_access.sh status
```

- Revoke immediately:

```bash
./scripts/autonomous_access.sh revoke
```

Lease metadata is stored at:

```text
~/.config/aurora/autonomous_access_lease
```

## Always-on mode (systemd user service)

Use `deploy/aurora.service` with the runbook in `ALWAYS_ON.md` to keep Aurora running continuously.

High-level flow:

1. Copy service to `~/.config/systemd/user/aurora.service`.
2. Reload user daemon.
3. Enable and start service.
4. Monitor logs with `journalctl --user -u aurora -f`.

## Development checks

Run the same smoke checks as CI:

```bash
python -m py_compile aurora.py aurora_*.py foundational_contract.py chatscriber.py corpus_runner.py
bash -n scripts/run_aurora.sh scripts/autonomous_access.sh
AURORA_SKIP_DEP_INSTALL=1 python - <<'PY'
import aurora
import aurora_consciousness_engine
import aurora_simulation_engine
import aurora_governance_persistence_gateway
print('Aurora imports OK')
PY
```

## Aurora review (current repo snapshot)

This section captures a practical engineering review of the current repository state.

### Strengths

- **Clear modular decomposition:** major cognitive concerns are separated into dedicated modules with descriptive interfaces.
- **Layered architecture is explicit:** boot sequence and conceptual layers are documented in code and consistent across module names.
- **Operational runbook exists:** `ALWAYS_ON.md` plus service and script wiring provide deployability for private always-on use.
- **Autonomy gating exists:** lease-based controls are a solid baseline for explicit operator intent boundaries.
- **CI smoke checks present:** syntax and import checks reduce breakage risk for core module wiring.

### Risks / technical debt

- **Single-file runtime concentration:** `aurora.py` is large and contains bootstrap, orchestration, command handling, and behavior logic in one place.
- **Dependency installation at runtime:** startup may install packages dynamically, which can create nondeterministic boot behavior.
- **State files in root:** many mutable JSON artifacts live alongside source code, increasing accidental commit/config drift risk.

### Recommended next steps

1. Split `aurora.py` into `cli`, `bootstrap`, `orchestration`, and `handlers` packages.
2. Pin dependencies in a lockfile (`requirements.txt` or `pyproject.toml`) and move installs to setup/docs.
3. Separate runtime state into a dedicated data directory and add stronger `.gitignore` policies.
4. Add unit tests around parser, memory, autonomy boundary checks, and persistence flows.
5. Keep a single supported runtime entrypoint (`aurora.py`) and retire variants.

## Notes

This project appears designed as a personal/private runtime rather than a published package. The current scripts and service files match that operational intent.
