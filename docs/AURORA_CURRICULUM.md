# Teaching her to understand: one substrate, not seven modules

Authors: Sunni (Sir) Morningstar & Cael Devo

Status: **design for Sir's review. Nothing here is built or taught yet** (the mechanisms marked GAP do not exist).

## Principle

A lesson never installs a competency. It adds *knowledge* to the one structure everything already reads
(her relations with their assertions, resolved once by `aurora_learned_index` and consumed by the gate, the
confluence, and the capability binding). If a domain below needs a new reader, the reader is written once and
every lesson in every domain can use it. The seven domains are seven *topics*, not seven systems.

## How a concept develops (the lesson shape)

Declarative statements alone give associations. Each concept moves through four phases, said to her the same way a
person would say them (through `handle_message`, never placed):

| Phase | What is said | What it tests that a statement cannot |
|---|---|---|
| Exposure | plain statements ("b comes after a") | that she holds it |
| Contrast | questions whose answers differ: "Does a come after b?", "Is d after a?", "What comes after z?" | direction, inference through a chain, *and not knowing* |
| Application | the concept used in a new situation ("If c comes after b, and b after a...") | that it changes what she concludes |
| Consequence | she acts or is told what followed ("You looked: there was nothing.") | that the outcome is recorded against what she expected |

Uncertainty stays explicit at every phase: each held statement already carries a count, denials, who said it, and
(FIX-A135) the basis `told`. Each domain adds the bases it needs (`observed`, `inferred`, `corrected`).
**Developmental history:** a bounded timeline per predicate (first heard, contrasted, applied, revised, with the
basis each time) next to the existing counts, so a revision appends instead of overwriting. GAP (small: extend
`_record_assertion`).

**Verification is by asking her**, with a probe file per lesson (`lessons/<name>.probes`: question, what must be
derivable, what must *not* be said). Probes are never said as lessons and are never scripts for her to match.

## The seven domains: what they teach, what already carries it, what is missing

| Domain | Reuses | GAP (new, general) |
|---|---|---|
| 1. Identity and perspective (I/you/we/he/she/they, speaker vs listener, mine vs yours) | `participants()`, perspective swap (A129), `who` on conditions (A135) | referents for he/she/they/we beyond the two present people; possessives resolved per speaker; the same sentence resolving differently per speaker is tested by contrast pairs |
| 2. Truth and uncertainty (knowing vs believing, observed vs told, possible vs confirmed, contradiction, revision) | `denied`/`n` counts, `modality`, `basis: told` | `basis` values (observed from her own senses, inferred, corrected); contradiction detection between held statements; revision that appends to history |
| 3. Quantity and comparison (one vs two, more/less/equal, add/subtract) | order edges, kinds | **quantities first**: counts grounded in what she senses (objects her camera reports) before any arithmetic; a quantity reader; digits are dropped by the tokenizer today |
| 4. Time and consequence (before/after/during, change, persistence, cause vs co-occurrence) | order predicates, `_capability_outcomes` | an event log of (what she did or was told, what followed) so cause vs co-occurrence is a contrast on *intervention*, not on words |
| 5. Language as structure (nouns, actions, properties, questions, negation, tense, conjunctions, referents) | `apply_kind`/roles, question shapes, negated predicates | teaching by **minimal pairs** ("I see" / "I do not see" / "Do I see?") so she learns what each form *changes*; tense is not read yet |
| 6. Emotional and social understanding (another's feelings, empathy, comfort, preferences, boundaries) | kinds, third-person statements | **guard:** concepts are taught as knowledge about people, in the third person; a rule never assigns Aurora a feeling or an obligation unless she was told it as a rule *and* its condition is confirmed; her own feelings still come only from her own state |
| 7. Exploration and testing (observe, explain, predict, check, revise) | capability binding, outcomes | a small prediction ledger: what she expected, what the sense returned, whether the expectation is kept; an explanation is a held statement with `basis: proposed` until checked |

## What I would build first (each is general, none is a domain)

1. **Honest not-knowing as a derived answer.** A question she can classify (order, kind, mark) but cannot answer
   today falls to the pressure seed ("after. comes."). It should be "I do not know" derived from the same resolution,
   so *what follows z?* has a different resolution than *does a follow b?* This is the clearest contrast probe.
2. **Basis and history on assertions** (domain 2's backbone; domains 3, 4, 7 reuse it).
3. **Contradiction between held statements** and revision that keeps the earlier statement in history.
4. **Probe runner** (`scripts/verify_lesson.py`): asks her the probe file through the same live path and reports what
   she derived, without ever feeding her the answers.
5. Then lessons, in the order 1, 2, 5, 3, 4, 7, 6, each written with exposure / contrast / application / consequence
   and reviewed by Sir before anything is taught.

## Already drafted (exposure only, in `lessons/`)

alphabet_order, kinds_letters_and_words, punctuation_marks, when_then_feelings, senses_and_capabilities, numbers,
basic_communication. They are the *exposure* phase; contrast, application and consequence lines come with the
mechanisms above. A question that contains a feeling word must not establish that anyone has it (FIX-A135 closed
that gap for rules; it is a contrast probe for domain 6).
