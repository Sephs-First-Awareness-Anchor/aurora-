# Turn routing: the phrase lists, and her own read

**Authors:** Sunni (Sir) Morningstar and Cael Devo
**Date:** 2026-11-21

## What changed

A live turn now forms her own NonComp read of the message once, at the top of
`_run_live_response_turn` (`aurora_turn_read.form_turn_read`). That read is the
interpreter's `interpret()` of the message (frame, constraint, dimension, the
25-channel projection and its dominant target) together with the parser's
relational form (who does what to whom, what is open, whether it is asked or
directed). The input guidance later in the turn reuses that interpretation
instead of interpreting the same message a second time.

Five routing questions are now answered by that read. The phrase lists that
used to answer them still run on every call, in shadow, and both verdicts are
recorded in `turn_read_shadow.jsonl` in her state directory (a journal, so a
surface-only device keeps its own record and no developmental store forks).

| Routing question | Function (unchanged name, callers untouched) | Phrase list kept in shadow | Her read answers from |
|---|---|---|---|
| Is it asked of her? | `_looks_like_question` (16 callers) | `_lexical_looks_like_question`: 29 prefixes | relational form `question` / `directive`, utterance type; a modal question ("can you explain gravity?") is a request |
| Is it about her? | `_is_aurora_self_question` (8 callers) | `_lexical_is_aurora_self_question`: 112 markers, including bare "sunni", "cael", "aurora" | she is a participant of the asked relation (subject, object, owner resolve to the second person or her own name), or a participant she holds in her core identity is named, or the speaker asks her to recall; never when the open slot is an embedded outside question |
| Is it her inner state? | `_looks_like_inner_state_query` (2 callers) | `_lexical_looks_like_inner_state_query`: 41 markers | she is the experiencer (subject) of the asked relation |
| Her perspective, or look it up? | `_should_prefer_live_perspective` (8 callers) | `_lexical_should_prefer_live_perspective`: 16 opinion phrases plus the two lists above | about her or her inner state, unless it is recall or her read places it on a clarification of meaning |
| Is it recall? | `_classify_input_intent`, recall step (4 callers) | 21 recall triggers | her read's temporal-recall override, a callback, or a question whose source is the speaker ("what did I tell you", "what is my name") |

`aurora_turn_read.ROUTE_BY_TURN_READ = False` gives the lists back the
decision (a baseline) and keeps recording the comparison.

Text she has not read this turn (an earlier message, a prompt, a draft) still
falls back to the list, and is counted as `no_read`.

## Every phrase list on the turn path

`scripts/map_phrase_routes.py` (AST walk of `aurora.py`) found 51 top-level functions
holding 8 or more phrase literals; 44 are reachable from
`_run_live_response_turn` by name. They fall into four kinds.

### Routers: English phrases choose the turn's path

Now answered by her read (above): `_looks_like_question`,
`_is_aurora_self_question`, `_looks_like_inner_state_query`,
`_should_prefer_live_perspective`, `_classify_input_intent` (recall step).

Still lexical, the next ones to bring onto her read:

| Function | Phrases | What it routes |
|---|---|---|
| `_surface_recent_context_horizon` | 35 | how much of the conversation is pulled in (readdress, callback, recall triggers) |
| `_resolve_lookup_request` | 37 | whether the message is an explicit "look it up" |
| `_resolve_hypothesis_offer` | 28 | whether a reply accepts or declines her last offer |
| `_derive_noncomp_behavior_actuation` | 23 | recall/continuity flags inside the NonComp actuation itself |
| `_definition_lookup_target` | 22 | whether, and what, to define |
| `_grounding_gap_strategy` | 20 | where to look first for missing grounding |
| `_is_identity_question`, `_generate_identity_response` | 20, 15 | identity questions (mostly behind `_is_aurora_self_question` now) |
| `_is_understanding_challenge` | 10 | "do you actually understand" challenges |
| `_should_use_search_for_question` | 8 | whether to search |
| `_is_explicit_meaning_or_continuity_request` | working-memory markers | meaning/continuity guard inside the perspective decision (still runs in the shadow list) |
| `_apply_noncomp_input_guidance` | 6 inline | `definition_like` forces a lookup remedy |
| `_run_live_response_turn` | 31 | present-frame fusion gate (`_AURORA_VISUAL_CUES`, `_USER_DEICTIC`) |
| `_answer_live_sensory_question` | 23 | sensory questions |

### Inside her read itself

Her NonComp read is not yet free of lists, and this matters for the next step:

- `aurora_reflexive_interpreter._semantic_override` uses `_RECALL_PATTERNS`,
  `_CLARIFICATION_PATTERNS`, `_MEANING_PATTERNS`, `_FACTUAL_LOOKUP_PATTERNS`,
  and the parser's `query_type`, and it decides the read's constraint and
  dimension when it fires. Measured on a clean interpreter: "How are you
  feeling?", "Do you like music?", "Can you explain gravity?" and "What did I
  just tell you?" all land on the same `X:OPERATOR` with override
  `existential_lookup`. The channels alone cannot yet tell her wellbeing from
  a lookup, so this change routes from the relational form (who the relation
  is about) and uses the channel read for recall and clarification.
- `_project_noncomp_state` adds small literal bumps ("what does", "remember",
  "cost") to the channel weights.
- The UtteranceParser's pragmatic signals are phrase-bound; they are the
  substrate her read is built on.

Bringing `_semantic_override` into the channels (so that the 25-channel
projection itself separates "about her" from "about the world") is the step
that would let the routing read come from the channels rather than the
relational form.

### Reply builders (not routing)

`_build_comprehension_response` (235), `_build_grounded_fallback_response`
(173), `_render_runtime_intent` (24), `_generate_from_manifold` (40),
`_constraint_emission_is_substantive` (11): vocabulary used to compose or
filter a reply, not to choose a path.

### Grammar, stop words and internal labels (not routing)

`_extract_factual_answer`, `_semantic_basis_tokens`, `_extract_user_name`,
`_normalize_surface_anchor_label`, `_sediment_validated_fact`,
`_response_is_grounded`, `_input_references_anchor`,
`_lookup_local_grounded_definition`, `_apply_pipeline_modulation`,
`_evolutionary_response_refinement`, `_extract_pipeline_signals`,
`_chain_down5_understanding`, `_chain_down1_information`,
`_finalize_articulation`, `_ensure_pipeline_abilities`,
`_derive_problem_solving_drive`, `_repair_discourse_coherence`,
`_run_reasoning_pipeline`, `_classify_validated_communication`,
`_should_try_ability_guided_recall`, `_answer_from_sedimemory_context`,
`_apply_noncomp_output_guidance`.

Elsewhere: `aurora_internal/aurora_understanding_contract.py` keeps its own
`_looks_like_question` method; it is not on this switch.

## Retiring a list

A list can retire when its shadow column shows, over real conversation, that
every disagreement is one where her read was right. The journal keeps one
line per turn with both verdicts per routing question; `shadow_report()`
gives the running totals and the latest disagreements.
