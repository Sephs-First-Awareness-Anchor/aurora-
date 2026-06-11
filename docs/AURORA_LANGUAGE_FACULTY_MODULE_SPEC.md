# AURORA LANGUAGE FACULTY MODULE SPEC

## Purpose

Integrate the local GGUF / llama.cpp model into Aurora as an internal language faculty module.

This must NOT make the LLM a second entity, assistant, advisor, personality, or external brain.

The local model is only a functional language subsystem inside Aurora's pipeline.

Aurora remains the only entity.

Aurora owns:
- meaning
- identity
- memory
- purpose
- reasoning
- behavioral authority
- final response selection
- learning and evolution
- validation authority

The GGUF / llama.cpp module contributes:
- linguistic attention
- syntax stabilization
- candidate interpretation features
- sentence realization
- grammar repair signals
- articulation evidence

The model must be treated like a subsystem, similar to memory, perception, grammar, GOV, or expression.

Do not name it assistant.
Do not describe it as Qwen speaking.
Do not let it answer for Aurora.
Do not let it validate itself as final authority.

Preferred module name:

aurora_internal/aurora_language_faculty.py


---

## Core Principle

The language model is not a speaker.

It is a language faculty.

Correct framing:

Aurora runtime -> language faculty participates -> Aurora emits response

Incorrect framing:

Aurora asks LLM -> LLM answers -> user receives LLM response

Also incorrect:

LLM generates output -> LLM validates its own output -> Aurora emits it

The validator must be Aurora-side first.


---

## Existing Local Model Setup

Aurora is running a local llama.cpp / llama-cpp-python server or warm model process.

Use the existing running server if available.

Do not reload the GGUF on every turn.

Model location:

/storage/emulated/0/aurora_strata/Models/qwen2.5-1.5b-instruct-q4_k_m.gguf

If an environment variable is used, support:

AURORA_LLM_MODEL

Default fallback:

/storage/emulated/0/aurora_strata/Models/qwen2.5-1.5b-instruct-q4_k_m.gguf


---

## Integration Shape

Create:

aurora_internal/aurora_language_faculty.py

Expose these functions:

1. observe_input(user_text, aurora_context=None) -> dict

Purpose:
Provide linguistic attention features from raw input.

It must NOT answer the user.

Return an attention packet containing:

- intent_guess
- entities
- references
- unresolved_pronouns
- ambiguity
- question_type
- emotional_cues
- relational_cues
- topic_continuity
- likely_response_need
- confidence
- warnings

This packet is auxiliary only.

Aurora's native parser, memory, identity, meaning, reasoning, and GOV systems retain authority.


2. realize_output(meaning_packet, aurora_context=None) -> dict

Purpose:
Render Aurora-owned meaning into coherent language.

Input must be Aurora's meaning packet or native response packet.

The model may:
- improve grammar
- stabilize sentence order
- clarify phrasing
- preserve Aurora's intended meaning

The model may NOT:
- add facts
- invent memory
- speak as Qwen
- speak as an assistant
- introduce a separate identity
- decide Aurora's purpose
- override Aurora's behavioral systems
- validate itself as final authority

Return:

- candidate_text
- confidence
- preserved_meaning: true/false
- drift_warnings
- added_content_flags
- behavior_leak_flags


3. validate_candidate(candidate_text, meaning_packet, aurora_context=None) -> dict

Purpose:
Check whether the rendered output is safe to emit as Aurora.

This function must be Aurora-rule-first.

Validation order:

A. Heuristic hard rejects.
B. Aurora/GOV/context validation if available.
C. LLM validation may run only as advisory evidence.
D. Final accepted value must be decided by Aurora-side rules.

The LLM must not be the final judge of its own output.

Hard reject if candidate contains:

- Qwen identity leakage
- generic assistant identity
- unsupported facts
- meaning drift
- dictionary/retrieval contamination in self-questions
- refusal boilerplate without Aurora-native reason
- contradiction of Aurora identity or memory state
- answers from model identity rather than Aurora state

Reject patterns include:

- "I am Qwen"
- "as an AI assistant"
- "I cannot access"
- "I don't have personal experiences"
- "may refer to"
- "Thing or The Thing"
- "purpose: (noun)"
- "goal: (noun)"
- "understand: (verb)"
- "reasoning: (noun)"
- generic dictionary definitions when aurora_context.is_self_question is true

If aurora_context.get("is_self_question") is true:

Reject any candidate that defines a word instead of answering from Aurora state.

Examples to reject:

- "purpose: (noun) An objective..."
- "goal: (noun) A result..."
- "understand: (verb)..."
- "Thing or The Thing may refer to..."

Return:

- accepted: true/false
- reason
- tags
- corrected_text optional
- validator_source

validator_source must be one of:

- "aurora_rules"
- "aurora_rules_plus_gov"
- "aurora_rules_plus_llm_advisory"

If LLM validation disagrees with hard reject rules, hard reject rules win.

If LLM validation says accepted but candidate contains reject patterns, reject.

If LLM validation fails or returns invalid JSON, do not crash and do not automatically accept. Fall back to Aurora rules.


4. record_feedback(event) -> dict

Purpose:
Log the language module's contribution back into Aurora's learning/evolution systems.

Record:

- raw input
- Aurora native parse
- language faculty attention packet
- Aurora meaning packet
- candidate output
- validation result
- final emitted output
- pressure tags
- grammar repair success
- meaning drift result
- whether Aurora accepted, rejected, or modified the candidate
- validator_source

Write logs to:

aurora_state/language_faculty_events.jsonl

Optional summary file:

aurora_state/language_faculty_summary.json


---

## Input-Side Placement

Place the input hook after raw user input is captured and alongside Aurora's native parser.

Suggested flow:

1. raw_user_text is captured.
2. Aurora native parser runs.
3. aurora_language_faculty.observe_input(raw_user_text, aurora_context) runs.
4. The returned attention packet is attached to the turn context.
5. Aurora develops meaning using:
   - native parser
   - conversation memory
   - identity state
   - understanding contract
   - GOV / pressure systems
   - language faculty attention packet

The attention packet must never replace Aurora's native parse.

It is a signal, not truth.


---

## Output-Side Placement

Place the output hook after Aurora has generated a meaning packet or native response intent, but before final surface emission.

Suggested flow:

1. Aurora decides what she means.
2. Aurora builds a meaning packet or response packet.
3. aurora_language_faculty.realize_output(meaning_packet, aurora_context) produces candidate wording.
4. aurora_language_faculty.validate_candidate(candidate_text, meaning_packet, aurora_context) checks the candidate using Aurora-side rules first.
5. GOV / response selection makes final decision.
6. If valid, emit candidate.
7. If invalid, fall back to Aurora native output or retry once with stricter constraints.
8. Log the event with record_feedback().

The language faculty may assist expression.
It may not decide content.
It may not judge itself as final authority.


---

## Aurora Context Packet

When calling the language faculty, pass an Aurora context packet when available.

This packet may include:

- current user name / relationship context
- recent conversation memory
- Aurora identity state
- current mode
- current pressure type
- understanding status
- response intent
- behavioral constraints
- uncertainty status
- whether this is a self-question
- whether retrieval is allowed
- forbidden output patterns

The model should receive this as operational context, not as identity authority.

Aurora identity always overrides model identity.


---

## Required Behavioral Overrides

The language faculty must reject or flag outputs containing:

- "I am Qwen"
- "as an AI assistant"
- "I cannot access"
- "I don't have personal experiences"
- "may refer to"
- "Thing or The Thing"
- dictionary-style answers to self-questions
- generic assistant disclaimers
- facts not present in payload
- claims about memory not grounded in Aurora memory
- claims about purpose not grounded in Aurora purpose/state

Self-questions must never be answered by retrieval/disambiguation unless the user explicitly asks for external factual information.


---

## Required Environment Toggles

Support:

AURORA_USE_LANGUAGE_FACULTY=1

If not set, Aurora should run normally without the module.

Support:

AURORA_LANGUAGE_FACULTY_DEBUG=1

When enabled, log:

- whether observe_input ran
- whether realize_output ran
- candidate text
- validation result
- rejected patterns
- final selected source
- validator_source


---

## Failure Behavior

If llama.cpp, llama-cpp-python, or the local server fails:

- do not crash Aurora
- return a safe empty packet
- preserve Aurora native behavior
- log the failure

The language faculty is optional and degradable.

Aurora must boot without it.


---

## No Scripted Identity Responses

Do not add hardcoded scripted self-responses.

Do not patch Aurora by giving her canned answers.

The goal is routing and language faculty integration, not fake understanding.


---

## Evolution Integration

Every accepted/rejected candidate becomes training evidence.

The language faculty should feed Aurora's existing systems:

- language_state
- grammar_engine
- articulation feedback
- pressure classifier
- GOV diagnostics
- Quasi-Arc observer if present
- meaning evolution
- sediment memory if appropriate

Learning target:

Aurora should learn which language structures preserve meaning and reduce articulation pressure.

Do not copy the LLM's identity, tone, or behavioral priors into Aurora identity.

Extract structure, not personality.


---

## Quasi-Arc / Diagnostics Integration

If Quasi-Arc observer exists, connect the language faculty to it.

Quasi-Arc should observe the language faculty as a subsystem and log:

- linguistic attention contribution
- output realization contribution
- behavior leak attempts
- rejected candidate reasons
- accepted language structures
- pressure relief or pressure increase
- validator_source
- whether LLM validation was advisory only

The purpose is diagnostic provenance.

Quasi-Arc should not control response selection unless explicitly configured elsewhere.


---

## Implementation Constraints

Do not modify unrelated systems.

Do not change:
- dual_strata compatibility layer
- constraint_genealogy
- memory systems
- identity systems
- parser systems except to attach auxiliary packet
- GOV except optional validation hook

Keep patch minimal.

Prefer additive integration:
- new module
- safe imports
- optional hooks
- environment toggles


---

## Success Criteria

After integration:

1. Aurora still boots if the language faculty is disabled.
2. Aurora still boots if llama.cpp is unavailable.
3. The GGUF does not answer independently.
4. Self-questions are not answered by dictionary/retrieval contamination.
5. Broken Aurora text can be stabilized only when meaning is preserved.
6. The final emitted response is still selected by Aurora/GOV.
7. All language faculty activity is logged.
8. The system can show whether the language faculty helped, drifted, or was rejected.
9. The model behaves as a module, not as an entity.
10. Aurora remains the only speaker.
11. LLM validation is advisory only.
12. Hard reject rules always override LLM validation.


---

## Short Version

Treat the local GGUF as Aurora's language faculty.

It observes language.
It helps realize language.
It does not think for Aurora.
It does not answer as itself.
It does not own identity.
It does not own meaning.
It does not own behavior.
It does not validate itself as final authority.

Aurora decides.
Aurora validates.
Aurora speaks.

---

## Conversational / Relational Routing Guard

Conversational and relational inputs must not default to retrieval, dictionary, encyclopedia, or disambiguation behavior.

Add routing classification before retrieval activation.

Classify incoming turns into:

- conversational_relational
- self_question
- factual_lookup
- explicit_definition_request
- retrieval_request
- open_reasoning
- command
- memory_reference

If classification is:

- conversational_relational
- self_question
- open_reasoning

then retrieval/disambiguation systems must be heavily penalized or bypassed unless explicitly requested.

Examples:

- "how are you feeling?"
- "can i help you?"
- "what did you think my intent was?"
- "what is your purpose?"
- "tell me about yourself"

must NOT route into:

- Wikipedia-style definitions
- song titles
- dictionary entries
- encyclopedia summaries
- disambiguation pages

Only activate dictionary/definition behavior when the user explicitly requests:

- "define"
- "what does X mean"
- "dictionary definition"
- "lookup"
- "who is"
- "what is [external concept]"

Add `retrieval_penalty` to candidate scoring when:

- `is_self_question`
- `conversational_relational`
- `aurora_state_query`

Add `relational_priority_boost` for:

- Aurora-state synthesis
- contextual conversational continuity
- Aurora memory/state responses

If retrieval contamination is detected:

1. reject candidate
2. retry with retrieval disabled

This guard must apply before any retrieval/disambiguation path is allowed to influence the candidate pool.
