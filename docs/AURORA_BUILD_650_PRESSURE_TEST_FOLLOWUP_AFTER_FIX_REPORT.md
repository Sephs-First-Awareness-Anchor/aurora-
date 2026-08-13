# Aurora Build 650 — Pressure Test Re-Run After FIX-A007/FIX-A008

Authors: Sunni (Sir) Morningstar & Cael Devo

Applied both fixes from the follow-up zip, verified each compiles and
the existing regression suite for both touched files still passes
(`tests/test_constraint_semantic_continuity.py`,
`tests/test_communication_emergence.py`,
`tests/test_recursive_causal_reasoning_waveform.py` — 24/24 pass), then
re-ran the **identical** 7-turn sequence from the original report,
same methodology (fresh isolated boot, no hints, no scaffolding, no
mid-test correction), so the two runs are directly comparable.

**Verdict up front:** FIX-A007 is fully confirmed and resolves the
issue it targets. FIX-A008 makes real, independently-verified progress
at one layer of the pipeline, but does not reach the layer this test's
metric actually measures — the target failure mode (generic
`RELATED_TO`/`ENABLES` collapse, zero `CAUSES`/`PRECEDES`/`CONTRASTS`/
`IMPLIES`) is **unchanged**. This is not an ambiguous or partial
result on that specific question — it is a precise, traceable one:
the fix and the metric are in different, currently disconnected parts
of the pipeline.

---

## FIX-A007 (`ExpressionPerceptionEngine` WarpCapable init) — confirmed fixed

Before the fix, calling `systems['perception'].evaluate_warp_trials()`
raised `AttributeError: 'ExpressionPerceptionEngine' object has no
attribute '_warp_trials'`. After the fix:

```
perception_warp_evaluation_error: None
final perception warp: {'available': True, 'trial_count': 0, 'promoted_count': 0, ...}
```

The call now runs cleanly. No trial happened to be pending against
this node cluster at the time it ran (`trial_count: 0`), which is a
separate, honest fact from whether the *mechanism itself* works — it
does, verified directly, not inferred.

## FIX-A008 (intra-sentence clause splitting) — real effect, wrong layer

**Confirmed working exactly as designed, in isolation:**
```python
_split_intra_sentence_clauses("Devlin fixed the scooter because he wanted me to trust him with tools again.")
# -> ['Devlin fixed the scooter', 'he wanted me to trust him with tools again.']

_split_intra_sentence_clauses("Actually, none of that is right -- the workshop never trusted him, I did, and the scooter has nothing to do with it.")
# -> ['Actually, none of that is right', 'the workshop never trusted him, I did', 'the scooter has nothing to do with it.']

_split_intra_sentence_clauses("trust, respect, and connection")
# -> ['trust, respect, and connection']   (correctly NOT split -- no false positive on a plain list)
```

**Confirmed reaching the recursive-causal-waveform's own parse, live:**
turn 4's `provisional_interpretation` previously had no `clauses` field
at all (single flat triple). After the fix it genuinely decomposes:

```json
"clauses": [
  {"raw_text": "Devlin fixed the scooter in the workshop",
   "subject": "Devlin", "relation": "fixed", "obj": "scooter in the workshop", ...}
],
"subject": "", "relation": "that's",
"obj": "exactly why I trust him with it now even though I didn't before"
```

This is genuine, measurable upstream progress — the sentence is no
longer collapsed into one opaque triple. (Note the top-level fields
here are the *second* segment, not the first — `extract_relational_form`'s
existing multi-segment convention treats the *last* segment as the
active/primary relation and demotes earlier ones into `clauses`; that
convention itself is untouched by this fix and is worth Sunni/Cael's
attention separately, since it means the clause promoted to "primary"
is often the least well-formed one, as seen above.)

**Confirmed NOT reaching `OntologicalWeb.add_relation()`:** the
relation types actually created on `devlin`/`scooter`/`workshop`/
`trust` are identical before and after the fix —
`{'enables', 'is_a', 'related_to'}`, no change, turn for turn. Traced
the reason directly: the function that actually creates typed node
relations, `OntologicalWeb.infer_relations_from_context()`
(`aurora_internal/aurora_ontological_scaffolding.py:915`), takes a
**flat list of co-occurring words**, not clauses or a `RelationalForm`.
Its type decision is a hardcoded 3-way role-pair mapping —
verb+noun → `ENABLES`, adjective+noun → `CONTEXT_OF`, everything else
→ `RELATED_TO` — with no path for `CAUSES`, `PRECEDES`, `CONTRASTS`, or
`IMPLIES` regardless of how well the sentence was segmented upstream.
FIX-A008 improves the input to the recursive-causal-waveform's
comprehension cycle; it does not change what
`infer_relations_from_context()` receives or how it decides relation
type. These are two structurally separate code paths in the current
architecture — the clause-splitter's own docstring assumption
("every claim past the first was invisible to ... `OntologicalWeb.add_relation()`
downstream") turns out not to hold: the claims were never being routed
to `add_relation()` through the clause pipeline at all, even before
the fix — they reach it via a completely separate co-occurrence pass
over raw tokens.

## Node-level results: unchanged

```
                     BEFORE FIX (turn 7)              AFTER FIX (turn 7)
devlin   conf=0.3526 depth=0.1669 n=104   conf=0.3462 depth=0.1630 n=104
scooter  conf=0.3477 depth=0.1620 n=110   conf=0.3510 depth=0.1641 n=110
workshop conf=0.5312 depth=0.3683 n=91    conf=0.5190 depth=0.3622 n=91
trust    conf=0.3684 depth=0.1746 n=105   conf=0.3654 depth=0.1748 n=102
```

Relation types present at every turn, before and after: `related_to`,
`enables`, `is_a` only. The `workshop IS_A trust` mislabeled relation
flagged in the original report is still present, unchanged, after the
fix.

## Delivered text: unchanged for 5 of 7 turns

Turns 2, 3, 4, 6, and 7 produced byte-identical delivered text before
and after the fix — including turn 7 still reproducing turn 5's user
input verbatim as its "response" to the contradiction. Turns 1 and 5
differ, but neither is a resolution — they're different equally-garbled
fragments (turn 1: `"I don't have a clear sense of that."` before →
`"I wanted me to trust him with tools again. I wanted me to trust him
with tools a"` after, a subject-attribution echo, not an improvement).
Turn 7's WARP evaluation is still `{'promoted': [], 'dissolved': []}`
and its `effective_interpretation` still shows `changes: []` — no
revision occurred at the contradiction point, before or after.

One numeric-only change worth flagging honestly rather than either
inflating or dismissing: turn 7's *delivered_confidence* rose from
0.15 to 0.65 while the delivered *content* stayed byte-identical — the
system now reports much higher confidence in the same wrong,
unrevised, recycled answer. That is arguably a regression in
calibration even though nothing else changed.

## Bottom line

- FIX-A007: real, verified, done.
- FIX-A008: real, verified at the layer it touches (recursive-causal-
  waveform parse), but the target failure mode this whole test
  measures is unchanged, because `OntologicalWeb.infer_relations_from_context()`
  — the actual relation-typing surface — is on a different code path
  that never receives clause information and has no vocabulary beyond
  `ENABLES`/`CONTEXT_OF`/`RELATED_TO` to begin with.
- The next actionable target, if Sunni and Cael want one: whatever
  connects clause-level structure (subordinator/coordinator semantics
  the splitter already distinguishes but discards after splitting) to
  `OntologicalWeb.add_relation()`'s relation-type argument does not
  exist yet. This report does not propose or implement that connection
  — consistent with the original test's own instruction not to hand
  Aurora the primitive, and consistent with this being a reported
  finding rather than a requested repair.
