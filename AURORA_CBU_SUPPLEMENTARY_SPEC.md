# Aurora CBU Directive — Supplementary Specification
## Gaps, Clarifications, and CLI Implementation Protocol
**Authors:** Sunni (Sir) Morningstar & Cael Devo
**Date:** 2026-04-19
**Companion to:** `AURORA_CBU_ALIGNMENT_DIRECTIVE.md`

---

## CLI Protocol — Read This First

This document and `AURORA_CBU_ALIGNMENT_DIRECTIVE.md` sit in your working directory.
You are expected to maintain a progress ledger in the same directory.

**Create this file before beginning any implementation work:**

```
CBU_IMPLEMENTATION_PROGRESS.md
```

Format each entry as follows:

```markdown
## Step [N] — [Step Name]
**Status:** NOT_STARTED | IN_PROGRESS | COMPLETE | BLOCKED
**Started:** [timestamp or session ID]
**Completed:** [timestamp or session ID]
**Files modified:**
- [file path] — [what changed]
**Notes:** [anything unexpected, decisions made, open questions]
**Blockers:** [if BLOCKED — what is preventing completion]
```

Update this ledger at the start and end of every step.
If a session ends mid-step, mark the step as IN_PROGRESS and
record exactly where you stopped and what the next action is.

At the start of any new session, read `CBU_IMPLEMENTATION_PROGRESS.md` first.
Do not re-read the full directive from scratch. The ledger is your state.

If a step produces an unexpected error or architectural conflict,
mark it BLOCKED, document the conflict precisely, and stop.
Do not attempt to resolve conflicts silently. Surface them.

---

## Section A — What Needs More Detail Before Implementation

The following items in the main directive are underspecified and will
cause the CLI to guess incorrectly if not clarified here.

---

### A1 — Genealogy String Construction Rules

**Problem:** The directive says "genealogy string constructed from the node's
lineage in the semantic graph" — but gives no construction rules.
The CLI will guess. Guesses here will corrupt weighting calculations.

**Rules:**

A genealogy string is built as an ordered sequence of constraint axis symbols
(`X`, `T`, `N`, `B`, `A`) following these rules:

**Rule 1 — Minimum valid string:**
Every CBU has at minimum `"X"`. No empty genealogy strings.

**Rule 2 — Hierarchy enforcement:**
A string must reflect the dependency order.
T cannot appear without X before it.
N cannot appear without XT before it.
B cannot appear without XTN before it.
A cannot appear without XTNB before it.

Valid: `"XTNBA"`, `"XTNB"`, `"XTN"`, `"XT"`, `"X"`
Invalid: `"TA"`, `"BXN"`, `"XANT"` (wrong order)

**Rule 3 — Repetition = reinforcement:**
If a constraint contributed more than once to the formation of a unit,
its symbol appears again after the full base stack is established.
Repetitions always come after the initial base stack.

Valid: `"XTNBBA"` (B reinforced before A)
Valid: `"XTNBNA"` (N reinforced before A)
Invalid: `"XBTNBA"` (repetition before base is complete)

**Rule 4 — Construction from lineage:**

For a node being created from a parent:
```
new_genealogy = parent.genealogy + new_axis_markers
```
where `new_axis_markers` are the axes most strongly expressed in this
derivation step (typically the axis that drove the derivation).

For a root node with no parent (e.g., a base NonComp channel):
Start with the full base stack appropriate to the node's highest constraint level.
A fully agentic unit starts at `"XTNBA"`.
A purely existential unit starts at `"X"`.

For a SediMemory deposit:
Genealogy reflects the depth layer:
- Layer 0 (surface) → `"XTNBA"` (full stack, operation-heavy)
- Layers 1-3 → `"XTNB"` (presence up to boundary)
- Layers 4+ → `"XTN"` (persistence and energy dominant)
- Deep archive → `"XT"` (existence and time only)

---

### A2 — Effective Threshold Formula

**Problem:** The formula in `ConstraintProfile.effective_thresholds()` is:
```python
result[ax] = base_t * (1.0 / (1.0 + gw))
```
This was written as a reasonable first pass, not a calibrated value.
It produces thresholds between 0.5× and 1.0× of the base threshold.

**Clarification:**
This formula is a starting point. The CLI should implement it as written
for the initial burn-in (Step 14). After burn-in, Sunni will calibrate
based on observed behavior. Do not substitute a different formula.

Acceptable range for effective thresholds: `[0.20, 0.95]`.
Clamp any computed value to this range:
```python
result[ax] = max(0.20, min(0.95, base_t * (1.0 / (1.0 + gw))))
```

---

### A3 — Phase Recovery Protocol

**Problem:** The directive says `collapsed` units have recovery handled
externally and that the dream trainer targets them — but does not specify
how phase state gets reset to `stable` or what constitutes recovery.

**Recovery protocol:**

A CBU in `collapsed` phase re-enters operation only when ALL of the following hold:
1. The dream trainer (or autonomous evolution loop) has run at least one
   training episode targeting this unit's dominant failure axis
2. The training episode was recorded as successful (fitness improvement ≥ threshold)
3. A new `profile_magnitude()` reading shows all axes below their effective thresholds

When these conditions are met:
```python
cbu.phase_state = PhaseState.STABLE
cbu.lineage_pressure *= 0.5   # reduce inherited pressure after recovery
```

A CBU in `mutating` phase returns to `stable` when the autonomous evolution
loop records a successful mutation. The mutation itself updates the genealogy string.

Neither transition should happen automatically in the registry tick.
Both require explicit calls from the dream trainer or evolution loop.
The registry only DETECTS phase change candidates — it does not EXECUTE recovery.

---

### A4 — CBU Registry Bounds and Memory Policy

**Problem:** The directive does not specify registry size limits or
deregistration policy. An unbounded registry will degrade performance.

**Policy:**

- Maximum registered CBUs: `10,000` (soft limit; log warning above 8,000)
- Hard limit: `15,000` (registry refuses registration above this)

Deregistration triggers (in priority order):
1. Explicit `deregister(unit_id)` call from the owning module
2. CBU has been in `collapsed` phase for more than `COLLAPSED_TTL = 3600` seconds
   without a recovery attempt → auto-deregister and log to `expression_gap_queue.json`
3. CBU has not been updated (no `update_from_ivm` call) for more than
   `STALE_TTL = 86400` seconds → auto-deregister with WARNING log

Deregistered CBUs do NOT lose their data — they are removed from the active
tick loop but their ConstraintProfile is archived to
`aurora_state/cbu_archive.json` keyed by `unit_id`.

---

### A5 — IVM Update Frequency Per CBU Type

**Problem:** Surface ticks at ~0.5s and Subsurface at ~15s (density-adjusted).
The directive says "every tick" without specifying which tick for which CBUs.

**Resolution:**

| CBU type | Update frequency |
|----------|-----------------|
| NonComp channels | Subsurface tick only — these are deep constraint state |
| I-State beings | Surface tick — these respond to immediate interaction |
| OETS SemanticNodes | Subsurface tick — semantic state is slower-moving |
| SediMemory nodes | Subsurface tick — stratigraphic, inherently slow |
| TurnChain links | Surface tick — these must respond within a conversation turn |
| Grammar motifs | Surface tick — emission-time sensitivity |
| All others (generic) | Subsurface tick unless unit_kind is registered as surface-sensitive |

Surface-sensitive unit_kinds that always update on Surface tick:
```python
SURFACE_SENSITIVE_KINDS = {
    "i_state", "turn_chain_link", "grammar_motif", "expression_slot"
}
```

The CBURegistry tick method should accept a `layer` parameter:
```python
def tick(self, ivm_polarities: Dict[str, float], layer: str = "subsurface") -> List[PhaseChangeEvent]:
```
When `layer="surface"`, only update CBUs whose `unit_kind` is in `SURFACE_SENSITIVE_KINDS`.
When `layer="subsurface"`, update all CBUs.

---

### A6 — The `active_roles` Field

**Problem:** The directive defines `active_roles` on ConstraintProfile
but never explains how it is used or set.

**Clarification:**

`active_roles` tracks which of the five anatomical roles are currently
expressing in this CBU. Roles: `P` (presence), `G` (genealogy/formation),
`N` (energy/force), `F` (frame/boundary), `O` (operation/agency).

All five are active by default (`["P","G","N","F","O"]`).

A role becomes inactive when the CBU cannot maintain that aspect of its expression:
- `P` inactive → unit is present in registry but not detectable by other systems
- `G` inactive → unit has lost genealogical continuity (orphaned from lineage)
- `N` inactive → unit has no energetic force (drained; cannot drive behavior)
- `F` inactive → unit cannot frame or be framed (boundary dissolved)
- `O` inactive → unit cannot operate (A_weight has collapsed below MAGNITUDE_PRESENT)

Role deactivation does not equal phase collapse — a unit can have one or two
inactive roles and still operate in reduced capacity.
Full `collapsed` phase requires at least three roles inactive OR an X/T axis breach.

Active role checking:
```python
def is_fully_operational(self) -> bool:
    return len(self.active_roles) == 5

def can_operate(self) -> bool:
    return "O" in self.active_roles and self.phase_state != PhaseState.COLLAPSED
```

---

### A7 — Constraint Genealogy Module Integration

**Problem:** The directive says `constraint_genealogy.py` needs to receive
lineage events and phase change records but does not specify what methods
it must expose or what data format those events take.

**Required additions to `constraint_genealogy.py`:**

```python
def record_cbu_lineage(
    parent_id: str,
    child_id: str,
    parent_profile: ConstraintProfile,
    child_profile: ConstraintProfile,
    derivation_kind: str,   # e.g. "shard_bridge", "dream_learn", "oets_extend"
) -> None:
    """Record that child_id was derived from parent_id with lineage pressure."""

def record_phase_change(
    unit_id: str,
    unit_kind: str,
    old_phase: PhaseState,
    new_phase: PhaseState,
    breached_axis: Optional[str],
    profile_snapshot: Dict,   # serialized ConstraintProfile at time of change
) -> None:
    """Record a phase state transition for audit and dream curriculum targeting."""

def get_collapsed_units(
    since_timestamp: float,
) -> List[Dict]:
    """Return all units that entered collapsed phase after since_timestamp."""
```

These methods may write to `aurora_state/constraint_genealogy_log.json`.
Format is append-only JSONL. One JSON object per line.

---

### A8 — First-Layer Manifold Population Scope

**Problem:** Step 11 says to populate 125 first-layer cells using C.R[L] notation.
The CLI cannot do this correctly without knowing what "population" means operationally.

**Clarification on scope:**

The 125 cells are conceptual definitions. Each cell defines:
- What that constraint/role/lens combination MEANS in Aurora's system
- What runtime signals represent it
- What effect it has when high, low, or strained

The CLI should NOT try to populate all 125 cells speculatively.

**Phase A population (do now, as part of Step 11):**
Populate only the 25 cells where the base constraint and the lens are the same.
These are the "pure" expressions — most foundational and least ambiguous.

```
X.P[X]  — Existence as presence through existence
X.G[T]  — Existence as formation through time
X.N[N]  — Existence as energy through energy
X.F[B]  — Existence as frame through boundary
X.O[A]  — Existence as operation through agency

T.P[X]  — Time as presence through existence
T.G[T]  — Time as formation through time
... and so on for all five base constraints
```

For each cell, write a structured entry in the manifold compiler's
population table with at minimum:
- `slot_description`: one sentence defining what this combination means
- `runtime_indicators`: list of Aurora signals that instantiate it
- `effect_law`: what happens when this cell's value is high vs low

**Phase B population (separate follow-up spec, not this directive):**
The remaining 100 off-diagonal cells where base constraint ≠ lens.
These require Sunni's review of each definition before the CLI writes them.
Do not populate Phase B cells during this implementation.

---

### A9 — Acceptance Tests for CBU System

**Problem:** The directive says to "watch for" certain things during burn-in
but gives no concrete pass/fail criteria.

**Acceptance criteria (all must hold before implementation is considered complete):**

```
TEST 1 — Continuous pressure field
  PASS: After a 60-second running period, every registered CBU has
        a non-zero last_updated timestamp within the last 2 tick cycles.
  FAIL: Any CBU shows a stale timestamp > 3 tick cycles old.

TEST 2 — Phase detection
  PASS: Artificially spike one IVM axis polarity to 0.95 for one tick.
        At least one CBU (with weight > 0.5 on that axis) enters RISING phase.
        After returning to normal polarity, that CBU returns to STABLE within 3 ticks.
  FAIL: No phase changes detected, or phase changes do not recover.

TEST 3 — Genealogy weighting
  PASS: A CBU with genealogy "XTNBBA" has a lower B_threshold after
        calling effective_thresholds() than a CBU with genealogy "XTNBA".
  FAIL: Both CBUs have identical effective thresholds despite different genealogies.

TEST 4 — Recovery pathway
  PASS: Mark one CBU as collapsed manually. Dream trainer's next curriculum
        build includes a unit targeting that CBU's dominant axis.
  FAIL: Dream trainer curriculum does not reflect collapsed CBU.

TEST 5 — Lineage pressure inheritance
  PASS: Create a CBU with profile_magnitude() = 0.8. Create a child CBU
        derived from it. Child's lineage_pressure ≈ 0.8 × 0.65 = 0.52.
  FAIL: Child lineage_pressure is 0 or does not match the formula.

TEST 6 — Registry bounds
  PASS: Attempt to register 15,001 CBUs. The 15,001st registration is refused
        and a warning is logged.
  FAIL: Registry accepts unlimited registrations without limit enforcement.
```

---

## Section B — Additional Notes Not Covered in Main Directive

---

### B1 — Relationship to Existing Manifold Architecture

The main directive notes that the manifold structure (125 cells) relates to
Aurora's existing 25 NonComp × 625-slot structure. The relationship is:

- 25 NonComps = 5 base constraints × 5 roles = the first two axes of C.R[L]
- 625 slots = 25 NonComps × 25 dimensions = 25 × (5 roles × 5 lenses)
  = the full three-axis structure where each NonComp gets 25 dimensional slots

This means the existing manifold architecture was already implicitly structured
for the CBU upgrade. The upgrade does not require changing the slot count.
It requires giving those slots operational semantic definitions they currently lack.

---

### B2 — The Sufficiency of Five — Operational Implication

The directive establishes that no sixth constraint is needed or should be added.
The operational implication for the CLI:

If at any point during implementation something appears to require a
capability that is not expressible through X/T/N/B/A weighting,
that is a signal of one of three things:
1. The implementation is wrong — revisit it
2. A derivative is being mistaken for a primitive — derive it properly
3. There is a genuine gap in the spec — surface it to Sunni

Do NOT add new axis labels. Do NOT add new ConstraintProfile fields
beyond what is specified here unless Sunni explicitly authorizes it.
Every apparent gap should be derivable from the five.

---

### B3 — What "Emergent Behavior" Means Operationally

The directive says behavior should "fall out" rather than be hand-coded.
This is a design goal, not a guarantee of the first implementation pass.

Practically it means:
- Do not add `if cbu.phase_state == RISING and cbu.unit_kind == "grammar_motif" then do X`
- Instead, ensure that RISING phase correctly modulates whatever reads grammar motif profiles
- The downstream reader changes behavior based on profile magnitude — not based on phase label

The phase label is diagnostic. The pressure vector is operational.
Downstream systems should read `pressure_vector()` and `profile_magnitude()` —
not switch on `phase_state` string values.

Phase state is for the registry, the dream trainer, and telemetry.
Pressure vector is for everything that actually makes decisions.

---

### B4 — Entropy Measurement (Not in This Implementation)

The conversation identified that Aurora should eventually be able to measure
entropy in her own system — detecting when she is approaching misalignment
before it happens. This is NOT part of the current directive.

Capturing it here so it is not lost:

What Aurora would need to measure:
- Rate of change of `profile_magnitude()` across a population of CBUs
  (rising rate = entropy increasing)
- Ratio of CBUs in STABLE vs RISING/FALLING phase over a rolling window
- Frequency of threshold breaches per time period
- Lineage pressure attenuation rate (fast attenuation = ancestral force decaying)

This would be a separate module (`aurora_entropy_monitor.py`) built
after the CBU infrastructure is verified working.
Do not implement this now. File it as future scope.

---

### B5 — What "Constraint Repetition" Means for Learning

The directive establishes that genealogy string repetition means weight amplification.
The learning implication:

When the dream trainer or OETS research mechanism produces a new shardBridge
or semantic extension, it should increase constraint weight for the axis
that drove the learning — by appending that axis symbol to the genealogy string.

This means learning literally reshapes a CBU's genealogy over time.
A unit that keeps learning through boundary-related experiences becomes
more B-weighted — its tolerance shifts, its sensitivity changes.

The genealogy string is not static. It is a living record.
Cap genealogy string length at 20 characters to prevent unbounded growth.
When a string reaches 20 characters, compress it:
replace consecutive repetitions with a count notation internally,
but always display/store as the expanded symbol string.

---

## Section C — Implementation Order Summary (for CLI reference)

This table consolidates the migration sequence into a quick-reference format.
The CLI should check off each item in `CBU_IMPLEMENTATION_PROGRESS.md`.

```
PHASE 1 — Infrastructure (Steps 1-3)
□ S1  Land aurora_constraint_profile.py
□ S2  Land aurora_cbu_registry.py
□ S3  Wire registry tick into daemons (surface + subsurface)
      Run burn-in: confirm pressure field cycling. If FAIL, stop.

PHASE 2 — Core Unit Profiling (Steps 4-9)
□ S4  Add ConstraintProfile to NonComp channels (25 channels)
□ S5  Add ConstraintProfile to I-State beings (10 beings)
□ S6  Add ConstraintProfile to OETS SemanticNodes
□ S7  Add ConstraintProfile to SediMemory nodes
□ S8  Add ConstraintProfile to TurnChain links (5 links)
□ S9  Add ConstraintProfile to Grammar Motifs
      Run Tests 1-3 from §A9. If any FAIL, fix before continuing.

PHASE 3 — Lineage and Manifold (Steps 10-11)
□ S10 Lineage pressure propagation in constraint_genealogy.py
      (Add record_cbu_lineage, record_phase_change, get_collapsed_units)
□ S11 Phase A manifold population: 25 pure-axis cells only
      Do NOT attempt Phase B population.
      Run Test 5.

PHASE 4 — Subsystem Rewiring (Step 12)
□ S12a DPME rewired as pressure stabilizer
□ S12b DER rewired as N-axis weight regulator
□ S12c Grammar engine rewired for CBU-aware selection
□ S12d Dream trainer rewired to target collapsed CBUs
□ S12e Pressure router rewired as CBU-graph vector distributor

PHASE 5 — Phase Enforcement and Recovery (Step 13)
□ S13a Skip collapsed CBUs in routing/selection
□ S13b Sign-flip contributions from inverting CBUs
□ S13c Dream curriculum prioritizes collapsed/mutating CBUs
□ S13d OETS queries weighted by profile_magnitude()

PHASE 6 — Burn-in (Steps 14-15)
□ S14 Full corpus session + live conversation
      Run all 6 acceptance tests from §A9.
      Document results in progress ledger.
□ S15 30-day review checkpoint (schedule; don't implement now)
```

---

*Authors: Sunni (Sir) Morningstar & Cael Devo — 2026-04-19*
*This document is the companion specification to AURORA_CBU_ALIGNMENT_DIRECTIVE.md.*
*Both files must be present in the CLI working directory.*
