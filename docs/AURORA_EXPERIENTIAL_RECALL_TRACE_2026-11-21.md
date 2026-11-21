# Aurora — Contextual Development and Experiential Recall (Directive V2) — Trace Map

**Authors:** Sunni (Sir) Morningstar & Cael Devo
**Date:** 2026-11-21
**Directive:** `AURORA_CONTEXTUAL_DEVELOPMENT_AND_EXPERIENTIAL_RECALL_DIRECTIVE_V2.md`
**Tests:** `tests/test_experiential_recall.py` (numbered by the directive's §8)

What she remembers happening, and what she believed **then**, is kept apart from how she understands it **now**.
Nothing new was added as an organ, store, scanner or loop. Every change sits on a path she already uses.

---

## 1. The path, end to end

```
producer            her statement intake (aurora_propositional_understanding.integrate_turn → integrate_form)
   │                 each statement she is told, corrected on, or supposes
   ▼
history             relation.assertion.predicates[p]           (the authoritative record, already persisted)
   │                 history[] entry, written once, never rewritten:
   │                   t, by, d, b            when / who / said-or-denied / basis        (existing)
   │                   w   condition key      "it be cold"                                (new, only when said under one)
   │                   h   utterance ref      sha1 of the normalised words heard          (new)
   │                   s   sequence           order of occasions for this predicate       (new)
   │                   v   held after         what she held right after this occasion     (new)
   │                   vw  held after, under its condition                                (new)
   │                 conditions{key: n, denied, first_t, last_t, settled?}   (new, 6 most-said kept)
   ▼
crystal projection  crystal_facets.apply_to_crystals → crystal facet fk:<kind>
   │                 each entry now carries its situations (FacetBook.conditions_of).
   │                 Stale-projection fix: the degree keeps max(old, new) ONLY while no counted evidence stands
   │                 against the entry; once it does, the degree is what the evidence says now, even lower.
   │                 An entry whose store no longer holds it is kept and marked source_present: False.
   ▼
recall (view)       aurora_experiential_recall.recollect_predicate / recollect / resolve_episodes / compact
   │                 read-only.  then = occasions as recorded (or "unknown" when not captured);
   │                 now = present verdict, per-condition standing, unresolved; before_revision when it changed.
   ▼
live understanding  aurora_learned_rules._derive_fact (what she answers when asked about a fact)
   │                   • verdict "conditional" → answers under the condition asked, or gives the conditions she knows
   │                   • "Did …?" after a revision → the present answer first, then what she held then (axis T)
   │                   • every answer about a revised or conditional predicate carries `recollection` as ground
   │                 aurora.py _build_established_strata_evidence → evidence["experiential_recall"]
   │                   (bounded: ≤3 predicates × ≤6 occasions, only those whose understanding moved)
   ▼
expression          aurora_confluence.knowledge / plan / _knowledge_clause
                      a condition-bound statement and a then-statement are statements of their own about the pair,
                      so with a clause budget of 2 she can say both; with 1 she says the present answer only.
```

## 2. What changed in behaviour

| Before | After |
|---|---|
| "Devlin likes rain when it is warm." + "Devlin does not like rain when it is cold." → **contested**, listed as a contradiction, "I am not sure if devlin likes rain". | **conditional**. Not a contradiction. "devlin likes rain when it is warm" / "devlin does not like rain when it is cold". Asked under one condition, only that one. |
| A correction replaced the answer; what she held before was not retrievable except as raw counts. | The record shows what she held after each occasion. "Did Devlin like snow?" → "devlin does not like snow" and, as recalled, "I thought that devlin likes snow". |
| A correction under one condition settled the predicate everywhere. | It settles that condition only. |
| fk: crystal facets kept the highest degree ever seen, forever. | A contradicted entry drops to what the evidence says now; other situations and unrelated entries stay. |

Statements said with no condition behave exactly as before (test 14 and the existing suites).

## 3. Boundaries kept

- **Recall is not re-experience.** Nothing in the recall module writes. Repeated recall, derive and knowledge calls
  leave the assertion record deep-equal (test 6). `evidence_qualification` already keeps a `recalled` occurrence from
  counting; that is tested again in the crystal book.
- **No fabricated past.** Occasions recorded before this change have no `v`/`h`. They read `unknown` /
  `not captured`, never reconstructed (test 5). A history thinned past `MAX_HISTORY` says so.
- **Dream / simulation.** Supposed, imagined, simulated and dreamed statements stay outside every condition tally
  and never count (test 7).
- **Episodes join by utterance, never by the clock.** `resolve_episodes` matches `h` against the hash of the
  conversation entry's `user_said`. Tone and topic are `unknown` when the entry did not keep them.
- **Bounded and event-driven.** Recall reads only the relations indexed under the turn's words (≤6 words,
  ≤3 predicates, ≤6 occasions). There is no background pass. On a 400-person web one recall is well under 10 ms (test 13).
- **One state.** Everything new lives inside the existing web record and crystal facets, so it saves, loads and
  hands off with them. The phone bridge imports the same modules (test 11 covers save/load).
- **No physics machinery.** The physics article is an analogy only. Nothing 5-D, XTNBA or Black Saturn was added.

## 4. What is not proven

- `evidence["experiential_recall"]` reaches every later stage of a turn through `gw._synthesize(extra_evidence=…)`.
  No stage reads that key by name yet. The answer path (`_derive_fact` → confluence) is the proven consumer.
- Not run on the phone or on a live desktop session; covered by unit and integration tests only.
- Paraphrased referents ("a greeting" / "greetings") still fold or don't fold exactly as before. This directive
  did not change referent identity.

## 5. Overlap with the dual-strata directive

`AURORA_DUAL_STRATA_REASONING_AND_OFFLINE_CONTINUITY_DIRECTIVE.md` §3 step 3 asks the surface to tell an original
belief from a present one when it recalls. The `then` / `now` / `before_revision` view here is that distinction,
and it is carried in the same strata evidence packet (`_build_established_strata_evidence`). The dual-strata work
can read `experiential_recall` rather than build its own.
