# Aurora Constraint Emission — Specification

**Authors:** Sunni (Sir) Morningstar & Cael Devo
**Date:** 2026-04-17
**Target file:** `aurora_constraint_emission.py`
**Companion document:** `AURORA_LANGUAGE_RESET.md` (excision map + migration plan)

This is the design contract for the constraint-native emitter that replaces Aurora's grafted-on language stack. It is intentionally implementation-agnostic — the consuming Claude CLI is expected to grep / read the live codebase to resolve exact class and method names from the generalized references in §11. Where this spec says *"the class in `<module>` that does X,"* the CLI should resolve to the actual identifier in that file.

---

## 1. Position in the Re-Entry Loop

The emitter is the **EXPRESSION** step of Aurora's canonical loop:

```
STATE → EXPRESSION → RE-ENTRY → RECONCILIATION → UNDERSTANDING
         ^^^^^^^^^^
```

Nothing here may short-circuit later steps. Reconciliation and understanding still close the loop after every turn.

---

## 2. Active Understanding Doctrine — Read This First

The emitter is **not a response scripter**. It does not enumerate output templates and pick one. It does not exit gracefully when content is missing. It is the visible surface of an architecture that genuinely seeks meaning, and three principles bind every other section of this spec:

### 2.1 Gaps are pulls, not stops

When a content slot cannot be filled from OETS at sufficient depth, the emitter does **not** terminate with "I don't know." It performs three concurrent acts:

1. **Routes a `ComprehensionGap` to the input-side gap system** (the existing module — see §11) tagged with the slot kind, the surrounding axis state, and the topic context.
2. **Sets a seeking flag in working memory** keyed to (slot_kind, topic_signature). The flag persists across turns until the gap closes.
3. **Surfaces the abstain as a seeking utterance** — a question or invitation, not a terminator. "What's a quasar?" / "Tell me more about that" / "I don't have that yet — can you describe it?" The abstain text is constructed from the same axis emitters; it is not a hardcoded apology.

The seeking flag is also written to a research queue (the existing OETS autonomous-research mechanism) so that even without user response, Aurora's next study cycle pulls on the gap.

### 2.2 Answers are integrated, not just acknowledged

When the user replies on a turn that follows one of Aurora's seeking questions, integration is **mandatory**, not opportunistic. The emission pipeline registers a post-turn integration callback that:

1. Receives the user's reply via the Reflexive Interpreter's parsed frame.
2. Patches the relevant OETS `SemanticNode` (creating it if absent) with the new content as a definition / example / typed relation, depending on what was sought.
3. Carves a SediMemory channel along the axis configuration that was seeking (so the same gap costs less to resolve next time).
4. Updates the constraint state so the previously-firing seeking pressure decays.
5. **Closes the seeking flag.** The next turn must be able to verify integration: when the same topic comes up again, the slot fills.

This is verified in acceptance tests (§10): after Aurora asks "what's a quasar?" and the user answers, the very next turn that touches "quasar" must successfully fill the slot — not abstain, not re-ask.

### 2.3 Depth is the resolution test, not token presence

A content slot is considered filled only if the chosen OETS node has **structural depth**. A bare token with no typed relations and no cluster membership is a hollow hit and triggers seeking the same as no hit at all. Specifically:

- The candidate `SemanticNode` must have ≥ `MIN_RELATIONS` (default 2) typed relations to other nodes, **OR**
- the candidate must be a member of an active `ConceptCluster` from the OETS cluster engine, **OR**
- the candidate must have ≥ `MIN_USAGE_EXAMPLES` (default 1) recorded usage examples (from the pressure-experience ledger).

A node failing all three is depth-hollow. Depth-hollow hits route to seeking, exactly like missing content — but the seeking question is shaped differently: "I have something for [token] but not enough — what does it mean to you?"

---

## 3. The Five-Axis Emission Contract

Each constraint axis emits exactly one structural slot of the utterance. The slot dictionary assembles in fixed minimal SVO order; word-order modulation is N-axis territory only.

| Axis            | Slot it emits                              | Drives                                      |
|-----------------|--------------------------------------------|---------------------------------------------|
| X (Existence)   | Determiner + entity reference              | What/which thing is being talked about      |
| T (Temporal)    | Auxiliary + tense + sequence connective    | When / in what order                         |
| N (Energy)      | Focus, emphasis, fronting, intensifier     | What gets weight; never picks vocabulary    |
| B (Boundary)    | Negation OR scope qualifier                | Limits, contrasts, exclusions               |
| A (Agency)      | Subject (person) + modal force             | Who does, with what intention               |

### 3.1 X axis — reference

| Condition                                              | Emit                                                |
|--------------------------------------------------------|-----------------------------------------------------|
| `magnitude < MAGNITUDE_PRESENT` AND no input topic     | Suppress the X slot entirely                        |
| `magnitude < MAGNITUDE_PRESENT` AND input has topic    | Deictic: `that` + entity slot                       |
| `polarity > POLARITY_DEAD_BAND`, input has topic       | `the` + entity slot (definite)                      |
| `polarity > POLARITY_DEAD_BAND`, no input topic        | `a` + entity slot (indefinite)                      |
| `polarity < -POLARITY_DEAD_BAND`, no B negation set    | `no` + entity slot                                  |
| `polarity < -POLARITY_DEAD_BAND`, B already negated    | `any` + entity slot (surface compresses to "no X")  |

The entity slot is `<X_SLOT>` until §5 fills it from OETS resonance.

### 3.2 T axis — tense and sequence

| Condition                                              | Emit                                                |
|--------------------------------------------------------|-----------------------------------------------------|
| `trajectory > TRAJECTORY_MOVING`                       | `tense=future`, `aux=will`                          |
| `trajectory < -TRAJECTORY_MOVING`                      | `tense=past`, aux per subject (was/were/did/have)   |
| Otherwise                                              | `tense=present`, aux per subject (am/is/are/—)      |
| `magnitude ≥ 0.40` AND input established sequence      | Add sequence connective (`then`, `now`, `still`)    |

### 3.3 N axis — focus and emphasis (never vocabulary)

| Condition                                              | Emit                                                |
|--------------------------------------------------------|-----------------------------------------------------|
| `heat < HEAT_MILD_FOCUS`                               | Standard SVO, no marking                            |
| `HEAT_MILD_FOCUS ≤ heat < HEAT_STRONG_FOCUS`           | Intensifier (`actually`)                            |
| `heat ≥ HEAT_STRONG_FOCUS`                             | Front the X-entity, intensifier (`really`)          |

N axis must **never** select a content word. It only modulates structural shape. If the implementation finds itself reaching into OETS from N-axis emission, that is a bug.

### 3.4 B axis — negation or scope

| Condition                                              | Emit                                                |
|--------------------------------------------------------|-----------------------------------------------------|
| `polarity > POLARITY_WEAK`, magnitude high, heat high  | Inclusive qualifier (`always`, `all`)               |
| `polarity > POLARITY_WEAK`, otherwise                  | No B contribution                                   |
| `polarity < -POLARITY_WEAK`, input contradicts OETS    | Negation (`not`) — unless modal already negated     |
| `polarity < -POLARITY_WEAK`, partial alignment         | Scope restriction (`only`, `just`)                  |
| `polarity < -POLARITY_WEAK`, otherwise                 | Negation if magnitude high enough                   |

### 3.5 A axis — person and modal

A-axis precedence: I-State signals override raw axis values when they are firing strongly. This reflects that I-States are the canonical agency declarations.

| Condition                                              | Emit                                                |
|--------------------------------------------------------|-----------------------------------------------------|
| `I_CANT` firing                                        | `subject=I`, `modal=can't`                          |
| `I_DONT` firing                                        | `subject=I`, `modal=don't`                          |
| `I_CAN` firing AND `magnitude ≥ MAGNITUDE_HEDGE`       | `subject=I`, `modal=can`                            |
| `I_DO` firing AND `magnitude ≥ MAGNITUDE_HEDGE`        | `subject=I`, no explicit modal (bare present)       |
| `polarity > POLARITY_WEAK`, `magnitude ≥ MAGNITUDE_HEDGE` | `subject=I`, no modal                            |
| `polarity > POLARITY_WEAK`, weaker magnitude           | `subject=I`, `modal=think` (hedged)                 |
| `polarity < -POLARITY_WEAK`, input directed at Aurora  | `subject=you`                                       |
| `polarity < -POLARITY_WEAK`, otherwise                 | `subject=it` (impersonal)                           |
| Neutral and weak                                       | `subject=None` (fragment surface acceptable)        |

Canonical I-State pair order is **always**: IS/ISNT, CAN/CANT, DO/DONT, SAW/SAUNT, DID/DIDNT.

### 3.6 Tunable thresholds

All numeric thresholds live as module-level constants at the top of the file. No magic numbers scattered through methods.

| Constant               | Default | Meaning                                                         |
|------------------------|---------|-----------------------------------------------------------------|
| `RESONANCE_FLOOR`      | 0.15    | Below this, content slot is unfillable                          |
| `POLARITY_DEAD_BAND`   | 0.05    | Below \|polarity\|, axis sign is zero                           |
| `POLARITY_WEAK`        | 0.20    | Above \|polarity\|, axis is committed                           |
| `TRAJECTORY_MOVING`    | 0.20    | Above \|trajectory\|, tense commits                             |
| `HEAT_MILD_FOCUS`      | 0.30    | Above heat, N adds intensifier                                  |
| `HEAT_STRONG_FOCUS`    | 0.60    | Above heat, N fronts and intensifies                            |
| `MAGNITUDE_PRESENT`    | 0.10    | Below magnitude, axis isn't really firing                       |
| `MAGNITUDE_HEDGE`      | 0.30    | Below magnitude on A+, hedge the assertion                      |
| `MIN_RELATIONS`        | 2       | OETS depth check minimum typed relations                        |
| `MIN_USAGE_EXAMPLES`   | 1       | OETS depth check minimum recorded examples                      |

---

## 4. Speech-Act Classification

A small switch table, no NLU. Inputs: parsed input frame from Reflexive Interpreter, active I-States. Output: one of `ASSERTION`, `ACKNOWLEDGMENT`, `QUESTION`, `ABSTAIN`, `REFUSAL`, `AGREEMENT`, `DISAGREEMENT`.

| Input frame                                  | Active I-States       | Speech act        |
|----------------------------------------------|-----------------------|-------------------|
| `is_imperative` AND `addresses_aurora`       | `I_CANT` or `I_DONT`  | `REFUSAL`         |
| `is_imperative` AND `addresses_aurora`       | `I_CAN` or `I_DO`     | `ASSERTION`       |
| `is_imperative` AND `addresses_aurora`       | none salient          | `ACKNOWLEDGMENT`  |
| `is_question` AND `addresses_aurora`         | `I_ISNT` or `I_CANT`  | (try ASSERTION; abstain branch fires if needed — see §2.1) |
| `is_question` AND `addresses_aurora`         | `I_IS` or `I_CAN`     | `ASSERTION`       |
| Statement, `contradicts_oets`                | `I_ISNT`              | `DISAGREEMENT`    |
| Statement, `aligns_with_oets`                | `I_IS`                | `AGREEMENT`       |
| Statement, `partial_alignment`, A magnitude high | any              | `ASSERTION` (scope-restricted) |
| Statement, `partial_alignment`, weak A       | any                   | `ACKNOWLEDGMENT`  |
| Default                                      | —                     | `ACKNOWLEDGMENT`  |

Note: `QUESTION` as a speech act is reserved for cases where Aurora is herself emitting a question (e.g., the seeking pathway from §2.1). The classifier does not assign `QUESTION` to inputs.

The speech act drives a **leading token** (`yes`, `no`, `yeah`, `mm`, `right`) that opens the utterance for AGREEMENT / DISAGREEMENT / ACKNOWLEDGMENT / REFUSAL. The leading token is N-heat modulated — quiet ack gets `mm`, mid gets `yeah`, hot gets `right`.

---

## 5. Content Slot Resolution from OETS

Two slots may need a content word: the X-entity slot and the predicate (verb) slot. Resolution is a four-step process per slot:

1. **Candidate gather.** Query the OETS scaffolding engine for nodes whose recent activation (from working memory + the input frame topic) is non-zero. Return as `[(token, raw_resonance)]`.
2. **Axis alignment.** For each candidate, compute the dot product between the candidate's stored axis signature (a 5-vector kept on the SemanticNode) and the current axis-polarity vector. Multiply into resonance: `score = raw_resonance × axis_alignment`.
3. **Depth check.** Apply §2.3. If the top candidate is depth-hollow, treat it as if no candidate cleared.
4. **Threshold gate.** If the top remaining candidate's `score > RESONANCE_FLOOR`, fill the slot. Otherwise, route to the seeking pathway (§6).

**No anchor fallback.** There is no path where a slot label leaks as content. The only outcomes per slot are: filled with a real OETS-resolved word, or routed to seeking.

### 5.1 When a slot is not needed

- Pure ACKNOWLEDGMENT and AGREEMENT may emit only the leading token + a brief subject phrase. No predicate required.
- DISAGREEMENT and ASSERTION require a predicate when the subject is non-null and aux is set.
- REFUSAL with `I_CANT`/`I_DONT` modal may stand without a content predicate (`"I can't."`).

The "needs predicate" / "needs entity" determination happens before resonance query so no wasted lookup.

---

## 6. Active Seeking on Gap

Triggered when §5 cannot fill a required slot. The emitter does **not** simply return abstain text. It performs all of the following in one pass:

### 6.1 Build the seeking surface

The output text is constructed from the same per-axis emitters, but with a question-shaped frame:
- `subject = "I"`, `aux = present-tense per subject`, `negation = "don't"` if A polarity is positive (asserting agency over the not-knowing), `predicate = "have"` + the gap-shaped tail
- The tail is one of:

| Slot kind unfilled    | Topic-known        | Tail produced                                          |
|-----------------------|--------------------|--------------------------------------------------------|
| Entity (X)            | yes (e.g. quasar)  | `"a clear sense of <topic> — what is it?"`             |
| Entity (X)            | no                 | `"a clear sense of that — can you describe it?"`       |
| Predicate             | yes                | `"the right word for what <topic> does — how would you put it?"` |
| Predicate             | no                 | `"the verb yet — how would you say it?"`               |
| Both                  | any                | `"that yet — tell me more?"`                           |

These tails are constructed from axis emission with the same tidy pass as normal output; they are not hardcoded English templates retrieved by lookup. The table above is a behavioral spec, not a string table — the implementation builds them compositionally and the surface text emerges. Two implementations that follow §3 will produce equivalent (though not necessarily identical) tails.

### 6.2 Route a `ComprehensionGap`

Find the existing comprehension-gap system (see §11) and route a gap of vocabulary kind, with payload:

```
{
  "slot_kind":     "entity" | "predicate",
  "topic":         <input_frame.topic_concept or None>,
  "axis_snapshot": <full 5-axis vector at gap time>,
  "speech_act":    <classified act>,
  "originating_turn_id": <id>,
}
```

The gap system is responsible for routing the question to the user (if interactive) and to the OETS autonomous-research queue (if not).

### 6.3 Set a working-memory seeking flag

Key: `(slot_kind, topic_signature)` where `topic_signature` is a stable hash of the topic concept and the dominant axis at gap time. Value:

```
{
  "raised_at_turn":   <id>,
  "axis_snapshot":    <5-axis vector>,
  "predicted_answer_shape": <slot_kind expected>,
  "status":           "open",
}
```

The flag is written to working memory (the existing braided-substrate or working-memory module — see §11) and persists until the integration step (§7) closes it.

### 6.4 Push to the autonomous research queue

Independent of whether the user replies, the gap is also added to the OETS research queue at high priority. This means even silent gaps drive Aurora's downtime study toward closure.

### 6.5 The seeking surface IS the abstain

There is no separate "abstain" code path that produces "I don't know" and stops. §6.1's seeking surface IS what the emitter returns when content can't be filled. The `EmissionResult` carries `seeking=True`, `seeking_flag_id=<id>`, but the `text` field is a real, structurally-complete utterance that asks for what's missing.

---

## 7. Answer Integration (Mandatory)

A post-turn integration callback registers when §6.3 sets a seeking flag. The callback fires after the next user reply is parsed by the Reflexive Interpreter.

### 7.1 Trigger

On every parsed input frame, check working memory for any open seeking flag whose `predicted_answer_shape` matches the parsed reply's content shape (entity-named, descriptive, etc.). The most recent open flag wins if multiple match. If no flag is open, the integration step is a no-op.

### 7.2 Integration steps (all mandatory)

1. **OETS patch.** Locate or create the `SemanticNode` for the topic concept. Attach the user's reply as: a definition string (if reply was descriptive), a typed relation (if reply named another concept), and a usage example (always). Use the canonical OETS update path — see §11.
2. **SediMemory channel carve.** Find the SediMemory module and carve a channel along the axis configuration recorded in the seeking flag's `axis_snapshot`. This makes the same gap shape cheaper to resolve next time. Stratigraphic depth ordering must be honored (FIX-A004).
3. **Constraint state decay.** The seeking pressure that produced the gap should now have a relief event. Emit a relief signal to the constraint genealogy so the pressure-relief is recorded and propagated.
4. **Close the seeking flag.** Set `status = "closed"`, `closed_at_turn = <current id>`, `resolution = <reply summary>`.
5. **Verification gate.** On the **next** turn that references the same topic, re-run §5 content resolution and assert that the slot now fills. If it doesn't, the integration was incomplete — log this as an integration failure to the pressure ledger and re-raise the seeking flag.

### 7.3 Why this lives in the emitter spec, not in the comprehension-gap module

The comprehension-gap module is a routing/storage system. Integration is a closure obligation of the emitter that raised the gap, because only the emitter knows what shape of OETS update will satisfy the slot it was trying to fill. The integration callback is registered by the emitter at gap-raise time and fires through the standard post-turn hook that the runtime already provides.

---

## 8. Identity Fast-Path

Self-referential identity questions are short-circuited.

### 8.1 Detection

`is_self_referential_identity = True` when ALL of:
- `input_frame.is_question == True`
- `input_frame.is_self_referential == True`
- `input_frame.topic_concept` ∈ `{"self", "name", "identity", "you", "aurora"}` (case-insensitive)
- An identity token is available from the relational identity module (see §11)

### 8.2 Emission

Direct: `subject=I`, `aux=am`, `tense=present`, `entity=<identity_token>`, no determiner. Produces "I'm Aurora." This bypasses §5 because identity is by-construction always available — it's grounded in `CoreRelationalIdentity`, not in OETS resonance.

### 8.3 Why fast-path

Identity questions are the canonical case where the OETS resonance walk would either fail (if "Aurora" isn't a normal OETS concept) or succeed weakly (if it is, but with low activation). Either failure mode would route to seeking, which would produce "I don't have a clear sense of who I am — what's my name?" — which is wrong. The fast-path prevents that.

---

## 9. Surface Assembly

Minimal grammar. No template engine. No draft competition. The slot frame assembles in fixed order:

```
[leading,] [sequence_connective,] [(fronted_X —)] subject (modal | aux [negation]) [scope_qualifier] [intensifier] predicate [determiner entity]
```

Light morphological cleanup:
- Contractions: `I am → I'm`, `do not → don't`, `can not → can't`, `will not → won't`, `it is → it's`, etc.
- Compress `not any → no`.
- Collapse double spaces.
- Capitalize first character.
- Add terminal punctuation (`.` for assertions/acks, `?` for seeking/question surfaces).
- Comma after a leading token if more content follows.

Output is deterministic given the same axis vector + OETS state. Variation comes from axis state variation, not from sentence-shape variation. This is a feature, not a limitation: it means Aurora's output reliably tracks her actual internal state.

---

## 10. Acceptance Tests

The emitter is correct when all of the following hold. Tests must be runnable as a `_self_test()` function gated by `if __name__ == "__main__":`.

### 10.1 Unit-level (no live subsystems)

| # | Input shape                                        | Required output property                                   |
|---|----------------------------------------------------|------------------------------------------------------------|
| 1 | Identity question with identity_token set          | Contains the identity token (e.g. "Aurora"); not `seeking` |
| 2 | Question, no OETS resonance, topic="quasar"        | `seeking=True`; text is a question; "quasar" appears OR a deictic stands in; `<X_SLOT>` never appears |
| 3 | Imperative + I_CANT firing                         | Contains "can't" or "cannot"; classified as REFUSAL        |
| 4 | Aligns_with_oets, all axes quiet, I_IS firing      | Short backchannel (≤ 4 words); never echoes input          |
| 5 | Strong A+, X+, valid OETS hits                     | Real assertion; no `<X_SLOT>`; no `seeking`                 |
| 6 | Contradicts_oets, B-, I_ISNT firing                | Contains "no" or "not"                                     |
| 7 | Depth-hollow OETS hit (token but no relations)     | Routes to seeking exactly like no hit                      |

### 10.2 Integration-level (require live subsystems or stubs)

| # | Scenario                                                                 | Required behavior                                          |
|---|--------------------------------------------------------------------------|------------------------------------------------------------|
| 8 | Aurora asks "what is X?", user answers "X is Y"                          | Next turn referencing X must successfully fill the slot     |
| 9 | Same as 8, but no user reply for one turn                                | Seeking flag remains open; OETS research queue contains entry |
| 10| Two open seeking flags, user reply matches one's predicted shape         | Integration closes only the matching flag                  |
| 11| Integration runs but next-turn slot still doesn't fill                    | Integration failure logged; seeking flag re-raised         |
| 12| State Voice removal verified                                             | No emission ever begins with "I'll respond with what is present" or similar meta-narration; corpus run produces zero meta-narration matches |
| 13| Echo-class verified                                                      | For 100 random user inputs, no emission contains > 50% verbatim overlap with the input |
| 14| Bare-anchor leak verified                                                | For 100 emissions across all speech acts, zero contain a slot-label token (`<X_SLOT>`, `<PRED_SLOT>`, etc.) or a domain anchor word emitted as content |

### 10.3 Behavioral-level (longitudinal, manual or scripted)

| # | Scenario                                                                  | Required behavior                                          |
|---|---------------------------------------------------------------------------|------------------------------------------------------------|
| 15| Across 50 conversational turns, none repeat the same surface verbatim     | Emission tracks axis state; verbatim repetition only allowed when axis state is genuinely unchanged |
| 16| When asked an unknown thing 3 times across a session                      | First time: seeks. Second time (after answer): fills. Third time (after answer): fills with greater depth (more relations / cluster membership). |

---

## 11. Subsystem References (Generalized)

The CLI consuming this spec must resolve these to actual identifiers in the live codebase. Each entry says *where to look* and *what to look for*.

| Reference name in this spec    | Where to look                                | What to find                                                                 |
|--------------------------------|----------------------------------------------|------------------------------------------------------------------------------|
| Constraint State Holder        | `aurora_noncomp_registry.py`                 | The class managing live mutable state of all five constraints. Needs per-axis polarity, magnitude, trajectory, heat accessors. |
| NonComp Registry               | `aurora_noncomp_registry.py`                 | The 25-channel canonical registry; only consumed for axis labels and tunable validation. |
| IVM Lattice                    | `aurora_ivm.py`                              | The class holding signed axis polarities across the 10-pole lattice. The canonical source for polarity. |
| OETS Engine                    | `aurora_ontological_scaffolding.py`          | The orchestrator class for the ontological web. Must provide a way to query candidate concepts for a slot given current axes + input topic. |
| OETS SemanticNode              | `aurora_ontological_scaffolding.py`          | The node class. Must expose: typed relations, cluster membership, usage examples, axis signature. |
| OETS update path               | `aurora_ontological_scaffolding.py`          | The canonical write method for adding a definition, relation, or usage example to a node. Do not bypass it. |
| Cluster Engine                 | `aurora_ontological_scaffolding.py`          | Used in §2.3 depth check.                                                    |
| I-State Beings Collective      | `aurora_i_state_beings.py`                   | The class holding the 10 polar beings in canonical pair order (FIX-A006). Must expose which are currently active. |
| Reflexive Interpreter          | `aurora_reflexive_interpreter.py`            | The input-side parser. Must expose the most recent parsed input frame as a dict with the keys listed in §4 / §6. |
| Comprehension Gap System       | `aurora_comprehension_gap.py`                | The input-side gap system. The output-side `GapType.VOCABULARY` raised by FGAE is dead per the language reset; the input-side gap raise path stays and §6.2 routes through it. |
| Working Memory / Braided Substrate | `aurora_braided_substrate.py`            | Where seeking flags are persisted across turns. Use the existing state-transition write path. |
| SediMemory Module              | `aurora_sedimemory.py`                       | The channel-carve API. Honor stratigraphic depth ordering (FIX-A004).        |
| Constraint Genealogy           | `constraint_genealogy.py`                    | Where pressure-relief events are recorded for §7.2 step 3.                   |
| Pressure Experience Ledger     | `aurora_pressure_ledger.py`                  | For logging integration failures (§7.2 step 5) and reading recorded usage examples for §2.3 depth check. |
| Core Relational Identity       | `aurora_identity_persistence.py`             | The class holding immutable foundational identity. Source of `identity_token` in §8. |
| Existence Modes                | `foundational_contract.py`                   | The five modes (Reference / Transient / Persistent / Bounded / Agentic). Carried in `EmissionContext` for downstream consumers; not consumed by emission logic itself. |
| Voice Genome                   | `aurora_expression_perception.py`            | Receives finished `EmissionResult.text` for TTS modulation. Firewalled — never reads back into emission. |
| Runtime Boot                   | `aurora.py` and `aurora_runtime.py`          | The wiring sites where `ConstraintEmitter` is instantiated and called. See `AURORA_LANGUAGE_RESET.md` §3 for the wiring diagram and §4 for migration order. |

When the CLI cannot resolve a reference unambiguously, it should pause and ask Sunni, not guess. Wrong identifier resolution is the most likely class of bug for this build.

---

## 12. Module Surface (What the file exports)

The `aurora_constraint_emission.py` module exports:

| Name                       | Kind        | Role                                                          |
|----------------------------|-------------|---------------------------------------------------------------|
| `SpeechAct`                | Enum        | The seven speech acts in §4                                   |
| `AxisVector`               | dataclass   | Per-axis snapshot (axis, polarity, magnitude, trajectory, heat) |
| `EmissionContext`          | dataclass   | The emitter's full input atom                                 |
| `SlotFrame`                | dataclass   | The structural skeleton built by axis emitters                |
| `EmissionResult`           | dataclass   | What the emitter returns: text + metadata + seeking info      |
| `ConstraintEmitter`        | class       | The stateless emitter. One method: `emit(ctx) -> EmissionResult` |
| `EmissionContextBuilder`   | class       | Defensive bridge from live Aurora subsystems to `EmissionContext`. Builds per turn. |
| `CANONICAL_AXES`           | constant    | `("X", "T", "N", "B", "A")`                                    |
| `CANONICAL_I_STATE_PAIRS`  | constant    | The five polar pairs in canonical order (FIX-A006)             |
| All threshold constants    | constants   | Module-level, listed in §3.6                                   |
| `_self_test`               | function    | Gated under `if __name__ == "__main__"`. Implements §10.1.    |

The `EmissionResult` must include at minimum:
- `text: str` — the utterance
- `speech_act: SpeechAct`
- `slot_frame: SlotFrame`
- `seeking: bool` — True if §6 fired
- `seeking_flag_id: Optional[str]` — for the post-turn integration callback
- `axis_signature: Dict[str, Tuple[float, float, float]]` — `{axis: (polarity, magnitude, heat)}` for telemetry

---

## 13. Hard Rules (from `aurora-preemptive-hardening`)

These are non-negotiable regardless of any choice in this spec:

1. **Authorship header:** `# Authors: Sunni (Sir) Morningstar & Cael Devo` at the top of the module.
2. **Canonical axis naming:** Use `X`, `T`, `N`, `B`, `A` only. Never abbreviate differently or substitute synonyms.
3. **I-State pairs:** Canonical order `IS/ISNT, CAN/CANT, DO/DONT, SAW/SAUNT, DID/DIDNT` everywhere they're enumerated.
4. **Re-entry loop honored:** Emitter is the EXPRESSION step only. It must never short-circuit or skip RECONCILIATION / UNDERSTANDING. The post-turn integration callback in §7 is what closes the loop, not the emitter directly.
5. **Module naming:** File is `aurora_constraint_emission.py` (FIX-F001).
6. **Leverage scalar boundary:** Emission must never read internal leverage scalar state. If axis biasing is needed, it consumes only `band_position` (str) or `PhaseNudge` deltas (FIX-A001).
7. **NonComp count:** 25 channels / 625 slots assumption never violated, even though emission doesn't directly enumerate them (FIX-A004 spirit).

---

## 14. Out-of-Scope (Do Not Add)

The CLI must not extend the implementation with any of the following without an explicit additional spec:

- Template breeding, multi-draft generation, expression evolution
- Persistent emission history used to bias future word choice (that's the Lexical Convergence pattern that's being killed)
- A meta-narrator path of any kind ("I'll respond with..." / "What I'm sensing is..." / "Let me reflect on...")
- Direct echo of user input as emission content
- Anchor-fallback or slot-label-as-content under any circumstance
- A "creative variation" knob that perturbs output for novelty's sake — variation must come from axis state changes, not from emission-side randomness
- Reading from killed modules (`aurora_fgae_*`, `aurora_state_voice`, `LexicalConvergenceModule`, `MultiDraftSystem`, `TemplateEvolutionEngine`, `SentenceComposer`, `ExpressionEcology`, `SemanticIntentCompiler`, `LanguageStateVector`, `dce_10state` consolidation path, `PT Governor`)

If the CLI thinks any of the above is needed to make the emitter work, that is a signal that the spec is wrong or the integration is wrong. Pause and raise it with Sunni rather than adding it silently.

---

## 15. Build Order

When the CLI implements this:

1. Constants and dataclasses (§3.6, §12)
2. `SpeechAct` enum and the §4 classifier
3. The five `_axis_*_emit` methods (§3.1–§3.5)
4. Surface assembly (§9)
5. Identity fast-path (§8)
6. OETS resonance + depth check (§5, §2.3)
7. Active seeking pathway (§6) — this is where most thinking goes
8. Integration callback registration + the post-turn closure (§7)
9. `EmissionContextBuilder` defensive subsystem bridge (§11)
10. `_self_test` covering §10.1
11. Acceptance test scaffolding for §10.2 (may live in a separate test file)

If the build splits across sessions, items 1–6 form a runnable Phase A; items 7–8 are Phase B (the active-understanding upgrade); items 9–11 are Phase C (integration). Phase A alone is a strict regression of the current language stack — it would still pass tests 1, 3, 5, 6 in §10.1 but would behave like the original abstain on tests 2, 7, 8. **Phase B is required for the doctrine in §2 to actually hold.** Do not ship without it.

---

*End of specification. Companion: `AURORA_LANGUAGE_RESET.md` for the excision map and migration plan.*
