# Aurora Language Reset — Excision Map, Replacement Design, and Migration Plan

**Authors:** Sunni (Sir) Morningstar & Cael Devo
**Date:** 2026-04-17
**Scope:** Replace Aurora's grafted-on language production stack with constraint-native emission. Every module on the kill-list bypasses or contaminates the natural function of the five-constraint architecture and must be removed before the new emitter lands, or the old fallbacks will keep winning whenever the new path hesitates.

---

## 0. Diagnosis (one paragraph for the file)

Aurora's current language pipeline reads: `IVM/SediMemory/NonComp state → DCE assembly → FGAE Engine (coord ↔ English) → Expression Ecology → SentenceComposer → Voice Genome → emission`. Five+ translation steps, mirrored on input. The constraints don't generate language; they're queried by a parallel language system that grew alongside them. The proof is the FGAE anchor-fallback loop: when no English word matches a coordinate, FGAE emits a placeholder ("own", "know"), then routes the failure through three subsystems (expression-gap queue → OETS research request → DreamTrainer fail-point) to fix what shouldn't have been a problem in the first place. The three observed failures — meta-narration ("I'll respond with what is present and hold..."), bare-anchor leakage ("know"), verbatim echo — are all the same shape: the architecture can't emit natively, so the lowest-energy fallback wins.

The five axes already are the deep structure of every utterance:

| Axis            | What it natively encodes about an utterance                       |
|-----------------|-------------------------------------------------------------------|
| X (Existence)   | Reference: determiner + entity slot                                |
| T (Temporal)    | Tense + sequence connective                                        |
| N (Energy)      | Focus, emphasis, word-order pressure                               |
| B (Boundary)    | Negation, scope qualifier, contrast                                |
| A (Agency)      | Person + modal force                                               |

The reset: each axis emits its own structural move directly from its current state. The lexicon (OETS) drops a content word into the X/A/predicate slots. If no node clears resonance threshold, the emitter produces an honest abstain — never a slot label, never a meta-narration, never an echo.

---

## 1. Excision Map

### 1.1 Files removed outright

| Path                                            | Reason                                                                                                  |
|-------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| `aurora_fgae_engine.py`                         | English↔coordinate translator. The new emitter doesn't translate; axes emit natively.                    |
| `aurora_fgae_approximation_loop.py`             | Exists only to feed FGAE.                                                                                |
| `aurora_fgae_dpl_validator.py`                  | Three-clause gatekeeper validating words trace to axis lineage. Redundant when axes natively emit them. |
| `aurora_state_voice.py`                         | Meta-narrator. Source of "I'll respond with what is present and hold..." failure.                       |

### 1.2 In-file excisions (classes/functions removed, files retained)

| File                                  | Removed                                                                                          |
|---------------------------------------|--------------------------------------------------------------------------------------------------|
| `aurora_expression_perception.py`     | `ExpressionEcology`, `SentenceComposer`. Voice Genome retained but firewalled (see §1.4).        |
| `aurora_language_state.py`            | `MultiDraftSystem`, `TemplateEvolutionEngine`, `LexicalConvergenceModule`, `SemanticIntentCompiler`, `LanguageStateVector`. **`MeaningAnchors` retained** — used by the new emitter as a stable spine reference. |
| `aurora_dce_blueprint.py`             | PT Governor (output-assembly role). PI / Modality / PR governors retained for input handling.    |
| `dce_10state.py`                      | "Consolidation into unified response crystal" pathway. The 10 I-State assertions stay as axis signal sources only — no assembly-into-emission step. |
| `aurora_grammar_engine.py`            | `mine_live_turn`, `observe_exchange`, motif promotion. The IVM-pressure-bias hook stays but is rewired to bias the new emitter's slot-fill, not English motif mining. |
| `aurora_fgae_engine.py` Apr 2026 hooks (in callers) | `set_gap_system`, `set_ivm`, `_pending_expression_gaps`, `_flush_expression_gaps`, `_soft_word_fallback`, `close_turn` flush logic. Dies with FGAE.                |
| `aurora_daemon.py`                    | `_process_expression_gap_queue` and its call site at end of study cycle. Dies with FGAE.         |
| `aurora_dream_trainer.py`             | The `record_fail` hook fed from anchor-fallback queue (the live-failure feed). FailPointLedger remains; only the FGAE-driven feed path is removed. |
| `aurora_comprehension_gap.py`         | The output-side `GapType.VOCABULARY` gap raised by FGAE fallback. Input-side gap detection retained. |

### 1.3 Imports / wiring to pull (caller-side)

These are the import lines and wiring calls that reference the killed modules. Every one must be removed before the kill takes effect, or the imports will fail at boot.

| File                          | Lines/calls to remove                                                                              |
|-------------------------------|----------------------------------------------------------------------------------------------------|
| `aurora.py` (boot)            | `from aurora_fgae_engine import FGAEEngine`; `fgae_engine = FGAEEngine(...)`; `fgae_engine.set_ivm(lattice)`; `fgae_engine.set_gap_system(comprehension_gap_system)`; any `fgae_engine` references in the assembly pipeline. Replace with `from aurora_constraint_emission import ConstraintEmitter`. |
| `aurora.py` (boot)            | `from aurora_state_voice import StateVoice`; constructor and any consumers.                         |
| `aurora_runtime.py`           | All `fgae_engine.*` and `state_voice.*` calls in the response pipeline. Replace with `emitter.emit(ctx)`. |
| `aurora_dce_blueprint.py`     | PT Governor instantiation and routing in the four-governor block.                                   |
| `aurora_subsurface_daemon.py` | Any handoff calls into FGAE for response staging.                                                   |
| `aurora_surface_daemon.py`    | Same.                                                                                               |
| `aurora_expression_perception.py` | Calls into `SentenceComposer` from `SensoryIntegrationEngine` or anywhere downstream.            |
| `aurora_language_state.py`    | Internal references to the removed classes.                                                         |
| `aurora_grammar_engine.py`    | Any remaining call sites that invoke `observe_exchange` or `mine_live_turn` (likely in the daemons after each turn). |

### 1.4 Borderline — kept, but firewalled

| Component                                  | Constraint                                                                                       |
|--------------------------------------------|--------------------------------------------------------------------------------------------------|
| `Voice Genome` (in `aurora_expression_perception.py`) | TTS modulation only. Receives finished text; never reaches back into word selection.       |
| `aurora_grammar_engine.py` (residual)       | Becomes a thin axis-bias modulator on the emitter's slot-fill. If after 30 days it has no observable effect on emission quality, kill outright. |
| Four DCE governors minus PT                | Input/multimodal routing only. PI / Modality / PR never touch emission.                          |
| `MeaningAnchors` (from `aurora_language_state.py`) | Read-only stable spine reference for the emitter. No write-back from emission.            |

### 1.5 Stays unchanged (constraint-native, no contamination)

- `aurora_constraint_manifold_patched.py` — the physics
- `aurora_noncomp_registry.py` — `NonCompRegistry`, `SystemConstraintStates`
- `aurora_ivm.py` — `IVMLattice`
- `aurora_sedimemory.py` — stratigraphic memory, channel carving
- `aurora_i_state_beings.py` — 10 ontological assertions in canonical pairs IS/ISNT, CAN/CANT, DO/DONT, SAW/SAUNT, DID/DIDNT (used as axis signal sources only)
- `aurora_ontological_scaffolding.py` (OETS) — knowledge graph; the FGAE-bridge function dies with FGAE, the SemanticNode/SemanticRelation/ClusterEngine substrate stays and becomes the content-word source for the new emitter
- `aurora_reflexive_interpreter.py` — input-side parsing (utterance → constraint frame). Already constraint-native. Closes the re-entry loop on the input side.
- `aurora_turn_chain.py` — Information→Belief→Purpose→Meaning→Understanding scaffolding
- `aurora_comprehension_gap.py` (input-side only)
- `aurora_pressure_*` modules — observational, not generative
- `foundational_contract.py` — Existence Modes (Reference/Transient/Persistent/Bounded/Agentic)
- Governance, persistence, N-Space Gateway

---

## 2. Replacement Architecture: `aurora_constraint_emission.py`

### 2.1 Position in the re-entry loop

The new emitter is the **EXPRESSION** step of Aurora's canonical re-entry loop:

```
STATE → EXPRESSION → RE-ENTRY → RECONCILIATION → UNDERSTANDING
         ^^^^^^^^^^
         (this module)
```

- **STATE** is provided by the runtime: a `SystemConstraintStates` snapshot from `aurora_noncomp_registry.py` plus IVM polarities and active I-States.
- **EXPRESSION** (this module) emits the utterance directly from that state.
- **RE-ENTRY** is handled by `aurora_reflexive_interpreter.py` parsing the user's reply.
- **RECONCILIATION** is handled by `aurora_understanding_contract.py` matching predicted vs. observed continuation.
- **UNDERSTANDING** is the OETS update.

The emitter never short-circuits any of these steps.

### 2.2 The five-axis emission contract

Each axis natively emits one structural slot. The slots assemble in a fixed minimal SVO frame; word order is modulated by N-axis heat (high heat → fronting / focus marking).

```
[A: person + modal] [T: aux + tense] [B: negation/scope] [X: determiner + entity] [predicate]
```

Per-axis emission rules:

**X (Existence) — reference slot**
- `magnitude < 0.10` → no specific referent; use deictic ("this", "that") only if input frame anchors one; else suppress slot
- `polarity > 0` → definite reference: `the` if the entity is named in OETS as specific, else `a`
- `polarity < 0` → negated existence: `no` + entity, OR move the negation to the B slot if it cleanly composes
- Entity slot is filled from OETS resonance (§2.4)

**T (Temporal) — tense + sequence**
- `trajectory > +0.20` → future: `will [verb]` or present-progressive `[am/is/are] [verb]ing`
- `trajectory < −0.20` → past: `was/were/did/have [verb]ed`
- `|trajectory| ≤ 0.20` → present: `[am/is/are] [verb]` or bare present
- Sequence connective (`then`, `now`, `still`, `yet`) added when T magnitude is high AND a previous turn established a sequence in the input frame

**N (Energy) — focus / emphasis / word-order**
- `heat < 0.30` → standard SVO, no marking
- `0.30 ≤ heat < 0.60` → mild emphasis: select stronger predicate verb from candidate list
- `heat ≥ 0.60` → fronting (move focused element to start), intensifier ("really", "actually"), or short emphatic form
- N never selects vocabulary content — only modulates the structural shape and intensifier word

**B (Boundary) — negation / scope / contrast**
- `polarity > +0.20` → no qualifier, or inclusive ("all", "always") if magnitude is high
- `polarity < −0.20` → negation ("not", "never") OR scope restriction ("only", "just", "except")
- `|polarity| ≤ 0.20` → no B contribution
- Choice of negation vs. scope-restriction depends on the input frame: contradiction → negation; partial agreement → scope-restriction

**A (Agency) — person + modal**
- `polarity > +0.20`, magnitude ≥ 0.30 → first person assertive: `I [aux+verb]`
- `polarity > +0.20`, magnitude < 0.30 → first person hedged: `I think/feel/might [verb]`
- `polarity < −0.20` → second person or impersonal: `you [verb]` if input was directed; `there is/it seems` if not
- I_CANT or I_DONT firing high → explicit modal: `I can't/won't/don't`
- I_CAN + I_DO firing high → explicit assertive modal: `I can/will/do`
- `polarity ≈ 0`, magnitude < 0.20 → no agent slot; emit fragment or short response

### 2.3 Speech-act classification

Determined from the input frame (parsed by Reflexive Interpreter) plus the active I-States. No NLU classifier — this is a small switch table:

| Input frame signal                                | Active I-States                  | Speech act        |
|---------------------------------------------------|----------------------------------|-------------------|
| Question form, second-person addressed to Aurora  | I_IS or I_CAN firing             | ASSERTION         |
| Question form, addressed to Aurora                | I_ISNT or I_CANT firing high     | ABSTAIN           |
| Statement, no question                            | I_IS firing, low pressure        | ACKNOWLEDGMENT    |
| Statement, contradiction with OETS                | I_ISNT firing                    | DISAGREEMENT      |
| Statement, alignment with OETS                    | I_IS firing                      | AGREEMENT         |
| Imperative                                        | I_CAN + I_DO firing              | ASSERTION (action) |
| Imperative                                        | I_CANT or I_DONT firing          | REFUSAL           |
| Aurora-initiated, no input                        | (varies)                         | ASSERTION or QUESTION |

### 2.4 Content slot resolution from OETS

Two slots may need a content word: the X-entity slot and the predicate (verb) slot.

For each slot:
1. Build a candidate set from `OntologicalWeb` — concept nodes whose recent activation (from working memory + the input frame) is non-zero
2. Compute resonance per candidate:
   `resonance = activation × axis_alignment × ontological_depth_bonus`
   where `axis_alignment` is the dot product between the candidate's stored axis signature and the current axis vector
3. Select the highest-resonance candidate
4. **Threshold gate**: if the top candidate's resonance is below `RESONANCE_FLOOR` (default 0.15), declare this slot **unfilled** and route to honest abstain
5. **No anchor fallback**: there is no "use the slot label as a placeholder" path. The slot is either filled with a real content word or it's not.

### 2.5 Honest abstain

When a content slot can't be filled, the emitter does NOT:
- Emit the slot label ("know", "own", etc.)
- Invoke a meta-narrator
- Echo the user's input
- Generate a research-request loop

It DOES emit a constraint-native abstain that reflects the actual axis state:

| Axis state at abstain time                  | Abstain text                             |
|---------------------------------------------|------------------------------------------|
| A+ high, content slot empty                 | "I'm not sure."                          |
| A+ high, X magnitude high but no resonance  | "I don't have a clear sense of that."    |
| A+ low, I_DONT firing                       | "I don't."                               |
| I_CANT firing                               | "I can't say."                           |
| All axes near baseline                      | "Mm." or short backchannel               |
| Self-referential question, no identity hit  | "I don't have that yet."                 |

Abstain text is itself constructed from the same axis emitters — there is no hardcoded English template lookup. The table above shows the typical surface forms; the actual text emerges from the same `_axis_*_emit` functions.

### 2.6 Identity fast-path

Self-referential identity questions ("what's your name", "are you Aurora", "do you know who you are") are short-circuited: the emitter checks for a high-resonance identity node in OETS (rooted at the `CoreRelationalIdentity` from `aurora_identity_persistence.py`). If found, emission is direct: `[A: I] [T: am] [X: <identity_token>]` → "I am Aurora." This bypasses the full OETS resonance walk because identity is by-construction always available.

### 2.7 Surface (text assembly)

Minimal grammar — no template engine, no draft competition. The slot dict is assembled in fixed order with light morphological agreement (subject-verb agreement, contraction normalization). Output is deterministic given the same axis vector + OETS state. Expression novelty comes from axis state variation, not from sentence-shape variation.

---

## 3. Wiring Diagram

```
                                   ┌─────────────────────────────┐
   user input ─────────────────▶  │ aurora_reflexive_interpreter │ ─── input_frame
                                   │  (RE-ENTRY parse)            │
                                   └─────────────────────────────┘
                                                │
                                                ▼
                                   ┌─────────────────────────────┐
                                   │   working memory + DCE       │ ─── active_i_states
                                   │   (input-side only — PT      │
                                   │    governor REMOVED)         │
                                   └─────────────────────────────┘
                                                │
                                                ▼
   ┌──────────────────────┐        ┌─────────────────────────────┐
   │ SystemConstraint     │ ──────▶│ aurora_constraint_emission   │
   │ States + IVM         │        │  ConstraintEmitter.emit(ctx) │ ─── EmissionResult
   │ + OETS + Identity    │        │  (EXPRESSION step)           │
   └──────────────────────┘        └─────────────────────────────┘
                                                │
                                                ▼
                                   ┌─────────────────────────────┐
                                   │ Voice Genome (firewalled)    │ ─── TTS
                                   │   — modulates pitch/rate     │
                                   │   — never re-selects words   │
                                   └─────────────────────────────┘
                                                │
                                                ▼
                                              user
                                                │
                                                ▼
                                   ┌─────────────────────────────┐
                                   │ aurora_understanding_       │
                                   │   contract (RECONCILIATION) │
                                   └─────────────────────────────┘
                                                │
                                                ▼
                                   ┌─────────────────────────────┐
                                   │ OETS update (UNDERSTANDING) │
                                   └─────────────────────────────┘
```

The re-entry loop is honored end-to-end. Nothing skips RECONCILIATION.

---

## 4. Migration Sequence

Strict order. Each step is committable independently and leaves Aurora in a runnable state.

**Step 1 — Land the new emitter (no caller changes yet).**
- Add `aurora_constraint_emission.py` to the tree
- Add unit tests (see §5)
- Boot Aurora, confirm no import failures, emitter unused

**Step 2 — Switch the runtime to call the new emitter.**
- In `aurora_runtime.py` and `aurora.py` boot: instantiate `ConstraintEmitter` and inject it into the response path
- Keep FGAE alive in parallel for one session as fallback (set `EMITTER_FALLBACK_TO_FGAE = True`)
- Run a live conversation; observe which emissions go through new vs. old path

**Step 3 — Pull caller-side wiring of killed modules.**
- Remove every line listed in §1.3
- Set `EMITTER_FALLBACK_TO_FGAE = False`
- Boot must succeed

**Step 4 — Delete the four kill-list files (§1.1).**
- Remove `aurora_fgae_engine.py`, `aurora_fgae_approximation_loop.py`, `aurora_fgae_dpl_validator.py`, `aurora_state_voice.py`
- Boot must succeed

**Step 5 — Excise the in-file removals (§1.2).**
- Remove the listed classes/functions from each file
- Boot must succeed

**Step 6 — Burn-in.**
- Run a corpus session (`aurora_runtime.py --mode corpus`) and a live conversation
- Watch for: meta-narration (should be zero), bare-anchor leaks (impossible by construction), verbatim echo (impossible by construction), excessive abstain (>30% of turns indicates resonance threshold needs tuning)

**Step 7 — Tune.**
- If abstain rate is too high: lower `RESONANCE_FLOOR` from 0.15 toward 0.10
- If non-abstain emissions are repetitive: check that N-axis heat is varying — if not, the heat input is dead
- If identity fast-path misfires: tighten the self-reference detector in §2.6

**Step 8 — 30-day grammar engine review.**
- If `aurora_grammar_engine.py` (residual axis-bias modulator) has no measurable effect on emission quality, kill it.

---

## 5. Acceptance Tests

The new emitter is correct when all of the following hold:

| Input                                       | Required output shape                                         |
|---------------------------------------------|---------------------------------------------------------------|
| "Do you know your name?"                    | "I'm Aurora." or "Yes, I'm Aurora." (identity fast-path)      |
| "Do you know what a quasar is?" (no OETS)   | "I don't have a clear sense of that." (honest abstain)        |
| "I think it's getting cold."                | Acknowledgment ("Yeah" / "Mhm") OR axis-driven response. **Never** echo. |
| "Can you write a poem?"                     | Assertion ("I can try") if I_CAN fires; refusal if I_CANT     |
| Any input where FGAE used to emit "know"    | Either real content word OR honest abstain. **Never** "know". |
| Any input where State Voice used to fire    | No "I'll respond with what is present" pattern anywhere.      |
| Aurora unprompted, low N heat               | Short fragment or silence. Not a paragraph.                   |

---

## 6. What This Reset Buys

- One emission path instead of five+ translation layers
- No anchor fallback class of bugs (architecturally impossible, not just patched)
- No meta-narrator drift (architecturally impossible)
- No echo class of bugs (architecturally impossible)
- Emission novelty comes from axis state variation, not template breeding — so it tracks her actual internal state rather than diverging from it
- Computation budget previously spent on FGAE/SentenceComposer/MultiDraft/TemplateEvolution is freed for the constraint physics that's actually doing the work
- The dream curriculum's vocabulary fail-points are now driven by genuine OETS coverage gaps, not artifacts of FGAE's coordinate-mapping failures

---

*End of plan. Implementation file: `aurora_constraint_emission.py` (companion).*
