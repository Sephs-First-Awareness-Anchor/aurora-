# Aurora Build 650 — Pressure Test Re-Run After FIX-A009/A010/A011/A012/A013

Authors: Sunni (Sir) Morningstar & Cael Devo

Applied all five fixes from the second follow-up zip (`aurorabuild650fixedv5.zip`),
verified each compiles, ran the existing regression suite covering both
touched files (11 test files, 122 tests total — see "Regression" below),
then re-ran the **identical** 7-turn sequence from the original report and
round-1 follow-up, same methodology (fresh isolated boot, no hints, no
scaffolding, no mid-test correction), so all three runs are directly
comparable.

**Verdict up front:** two of the five fixes are genuinely, verifiably
working and represent real forward progress — FIX-A009 (echo-confidence
cap) and FIX-A012 (contradiction reconciliation) both fire correctly on
live turns in this exact test, which they did not before. FIX-A010/A011
(WarpCapable-ified relation-type selection) also works exactly as coded,
but its effect on this test's actual target metric is a **lateral move,
not a fix**: the generic-collapse failure mode the original directive
named is still fully present — it has changed shape (from a
`RELATED_TO`-flavored collapse to an `INSTANCE_OF`-flavored one) rather
than resolved. Zero `CAUSES`/`PRECEDES`/`CONTRASTS`/`IMPLIES` relations
appeared anywhere across all three rounds, despite the sequence being
built explicitly to require them. One caused regression test failure and
one newly-observed run-to-run non-determinism are reported below without
smoothing.

---

## FIX-A009 (echo-confidence cap) — confirmed working, real improvement

Round 1's follow-up flagged an honest concern: turn 7's delivered
confidence rose from 0.15 to 0.65 while its delivered content stayed
byte-identical to turn 5's raw user input — the system got *more*
confident in the same wrong, recycled answer. FIX-A009 targets exactly
this. In this round's run:

```
TURN 7 | src=generative | confidence=0.2
delivered_text: "The trust started in the workshop, moved to the scooter
once he fixed it, and now it's the reason I'd hand him anything."
result["echoed_prior_input"] = {
  "echoed": true,
  "matched_raw_text": "The trust started in the workshop, moved to the
    scooter once he fixed it, and now it's the reason I'd hand him
    anything.",
  "ratio": 1.0
}
```

The delivered text is still turn 5's raw input verbatim (ratio 1.0 —
the echo detector isn't being generous here, it's an exact match) —
**the underlying recycling bug is unchanged** — but the confidence is
now correctly suppressed to 0.2 instead of climbing to 0.65. This is a
real, verified, working calibration fix: Aurora no longer reports high
confidence in an answer that is provably a copy of an earlier turn's
input. It does not touch why the recycling happens in the first place.

## FIX-A012 (`_reconcile_disturbed_cycle`) — confirmed firing, narrower effect than it looks

This is the most consequential result of this round. Round 1's report
found the reconciliation flag went up on contradiction but nothing ever
read it (`warp_evaluation: {"promoted": [], "dissolved": []}`,
`changes: []`, always). This round, checking the **full cycle history**
(`rcrw._cycles`, not just each turn's own newly-created cycle record —
important distinction below) shows the mechanism genuinely runs:

```
cycle for turn 2 ("workshop is where Devlin earns...")
  disturbed by turn 3 -> status: reconciled (1 reconciliation logged)
cycle for turn 3 ("If Devlin hadn't fixed the scooter...")
  disturbed by turn 4 -> status: reconciled (1 reconciliation logged)
cycle for turn 6 ("It's not that Devlin earned trust...")
  disturbed by turn 7 -> status: reconciled (1 reconciliation logged)
cycle for turn 1 -> disturbed by turn 2 -> status: reentered, NOT reconciled
cycle for turn 4 -> disturbed by turn 5 -> status: reentered, NOT reconciled
cycle for turn 5 -> disturbed by turn 6 -> status: reentered, NOT reconciled
```

**Important correction to how this has to be read.** Each turn's own
per-turn record (what `process_external_user_turn()` returns for *that*
turn) is a brand-new cycle — it is never the one that gets marked
"reconciled." Reconciliation happens to the *previous* turn's cycle,
the moment the *next* turn's text disturbs it. So looking only at "turn
7's own cycle" (as both prior reports did, because that's what the
driver script surfaced per-turn) makes it look like nothing happened at
the contradiction point — turn 7's own `provisional_interpretation` /
`effective_interpretation` are identical, `changes: []`, same as
before. But turn **6's** cycle — the belief turn 7 is actually
contradicting — genuinely transitions to `reconciled`, with a real
`reconciliation_log` entry: entity overlap (`scooter`, `workshop`) plus
a negation/correction signal (`"actually... none of that is right"`)
correctly detected as a mechanical conflict, `derive_constraint_semantic_state`
genuinely re-run with both claims as clauses, and — independently
verified in the live `OntologicalWeb` — the `scooter`↔`workshop`
relation strength measurably decayed as a direct result:

```
turn 6 (before disturbance): scooter -> workshop  strength=0.614  confidence=0.32
turn 7 (after reconciliation): scooter -> workshop strength=0.224  confidence=0.30
```

That is a real causal chain from "Aurora received a contradiction" to
"a specific stored belief about specific entities weakened," which did
not exist in either prior round. **The limits of it, reported plainly:**
(1) the *top-level* `effective_interpretation` (`subject: "scooter",
relation: "was", obj: "just where it showed"`) is completely unchanged
by the reconciliation — the disturbing turn's content gets appended to
a `clauses` list, not merged into or replacing the primary claim, so
Aurora's stated belief itself isn't corrected, only a secondary
structure gains an entry. (2) The mechanical gate (entity-overlap AND a
negation/correction-word match) is conservative: 3 of the 6 possible
disturbances in this sequence didn't clear it and stayed un-reconciled,
including turn 4→5, arguably one of the more information-bearing turns
in the sequence (a full causal-chain restatement with no explicit
"no/actually/wrong" marker to trigger the gate). (3) The decay only
touched one direction of the `scooter`/`workshop` relation pair
(`scooter→workshop`); the reverse-direction relation (`workshop→scooter`)
was untouched, still `strength=1.0` after the same turn.

## FIX-A010/A011 (`_select_relation_type` nearest-fit selector) — works as coded, target metric unchanged

**Confirmed diversified nominally:** the relation-type vocabulary
actually created between `devlin`/`scooter`/`workshop`/`trust` grew
from the prior rounds' `{related_to, enables, is_a}` to
`{related_to, enables, is_a, instance_of, context_of}` — two new types
now appear, where none did before.

**Confirmed NOT reaching the directive's actual target failure mode:**
zero `CAUSES`, `PRECEDES`, `CONTRASTS`, or `IMPLIES` relations exist
anywhere in the final graph, across all four target nodes, despite the
sequence containing an explicit causal clause ("...*because* he wanted
me to trust him..."), an explicit temporal-sequence claim ("...*started*
in the workshop, *moved to* the scooter... *now* it's the reason..."),
and two explicit contrastive corrections ("It's *not that* X, it's
*that* Y", "*Actually*, none of that is right"). This is the exact
metric the original directive was measuring, and it is unchanged from
turn 1 of round 1 through turn 7 of this round.

**A new, more concerning pattern, verified directly rather than
inferred:** `instance_of` is now the single largest relation-type
bucket on every one of the four target nodes — 59/109 (54%) of
`devlin`'s relations, 61/113 (54%) of `scooter`'s, 48/99 (48%) of
`workshop`'s, 59/103 (57%) of `trust`'s. Inspecting the actual pairs
typed `instance_of` on `devlin` shows the same undifferentiated
collapse the original report found for `related_to`, just relabeled:
`devlin instance_of scooter`, `devlin instance_of trust`, `devlin
instance_of tools`, `devlin instance_of him`, `devlin instance_of
again` — none of these are genuine instance/type relationships (a
person is not an instance of trust, of tools, or of the word "again"),
they are noun-adjacent co-occurrence pairs, exactly like the old
`related_to` catch-all was. Confirmed this isn't specific to this
sentence set — tested in isolation against five unrelated noun pairs
(`rain`/`cloud`, `table`/`chair`, `dog`/`cat`, `king`/`queen`,
`fire`/`smoke`): **all five resolve to `INSTANCE_OF` identically**,
because `_role_pair_axis_signal()` only reads part-of-speech role
(noun+noun), never the actual words, so any two co-occurring nouns
produce the same axis signal and the same nearest-fit type regardless
of what they mean. `RelationType.INSTANCE_OF` carries a much higher
depth weight than `RELATED_TO` in the existing `RELATION_DEPTH_WEIGHTS`
table, and it asserts a specific (usually false) taxonomic claim rather
than staying deliberately generic the way `RELATED_TO` was designed to.
**Net assessment:** this fix replaces one universal, honestly-weak
default (noun+noun → `RELATED_TO`) with a different universal default
that is no more differentiated but is now actively asserting something
false at a much higher confidence-in-structure weight. Whether that's
an acceptable tradeoff on the way to a better selector, or a regression
in what the graph claims to know, is a judgment call for Sunni and
Cael — reported here as a precise, reproduced fact, not smoothed in
either direction.

## Regression: one pre-existing test now fails, root cause fully traced

```
FAILED tests/test_nc1_noncomp_population.py::test_other_role_combination_stays_related_to
1 failed, 121 passed, 234 warnings in 416.41s
```

That test hard-codes the exact old behavior FIX-A011 exists to change:
it asserts a noun+noun pair (`"rain"`, `"cloud"`) must resolve to
`RelationType.RELATED_TO`. Verified directly: it now resolves to
`INSTANCE_OF` (`strength=0.2, confidence=0.3, selection_signature=
"noun+noun"`) — a predictable, mechanical consequence of the selector
change described above, not a bug in the sense of broken code. This
test's expectation is now stale relative to the intended behavior
change; it was not modified or silenced here, since deciding whether
`INSTANCE_OF` is the *right* replacement default (versus the fix
needing further tuning) is Sunni and Cael's call, not something to
paper over by rewriting the test's assertion.

## Newly observed: turn 3 is not deterministic across otherwise-identical runs

Not something either prior round reported, and not something this
round set out to find — it surfaced by re-running the identical script
four times (once per added data-capture field) against four fresh,
isolated boots with byte-identical input. Turns 1, 2, 4, 5, 6, 7 were
byte-identical, source-identical, and confidence-identical across all
four runs. **Turn 3 was not:** two runs produced
`"I don't have a clear sense of that."` (`constraint_abstain`,
confidence 0.4) and two runs produced a variant of
`"I did not fix scooter i don't think i'd trust him with the workshop
key yet."` (`composer_unified`, confidence 1.0 — matching the exact
garbled subject-attribution bug from the original report's turn 3).
Same code, same input sequence, same isolated fresh state each time —
the only thing that varied was wall-clock/process-level nondeterminism
(most likely hash-seed-driven iteration order somewhere upstream of
response composition, though the specific source was not tracked down
here since it's outside this round's scope). This matters for
interpreting *any* single-run before/after comparison in this whole
Build 650 exercise, including the prior two reports: a byte-identical
delivered-text comparison on turn 3 specifically should be read as one
sample from a distribution, not a fixed fact, until this is
investigated further.

## Node-level results

```
                     ROUND 2 (turn 7)                  ROUND 3 (turn 7, this run)
devlin   conf=0.3462 depth=0.1630 n=104     conf=0.3595 depth=0.1738 n=109
scooter  conf=0.3510 depth=0.1641 n=110     conf=0.3641 depth=0.1749 n=113
workshop conf=0.5190 depth=0.3622 n=91      conf=0.5342 depth=0.3713 n=99
trust    conf=0.3654 depth=0.1748 n=102     conf=0.3632 depth=0.1760 n=103
```

Depth rose slightly for all four nodes — consistent with `INSTANCE_OF`
now carrying more of the relation mass than `RELATED_TO` did, at a
higher depth weight, per the mechanism described above. This is not
evidence of better comprehension by itself; it is a direct numeric
consequence of the type-selection change.

## Delivered text: turns 1/2/4/6 unchanged failure modes; turn 7 content unchanged, confidence corrected

Turns 1, 2, 4, and 6 reproduce the exact same failure signatures as
both prior rounds (turn 1: first-person subject-attribution collapse;
turns 2/4/6: recycled turn-2 content, byte-identical). Turn 5 is stable
at `"I don't have a clear sense of that."` (`constraint_abstain`,
confidence 0.4) in this round — note this is the SAME text turn 3
alternates into on some runs (see non-determinism above), delivered
from two different sources/turns. **Turn 7 delivered content is still
turn 5's raw user input, verbatim** — the core "genuine resolution at
the contradiction point" bar from the original directive is still not
met. What changed, and it's real: the confidence attached to that
recycled content is now honestly low (0.2) instead of misleadingly
high (0.65), and — as detailed under FIX-A012 above — a real,
measurable belief-weakening did occur in the graph as a side effect of
the contradiction, even though it's not visible in the delivered text
and doesn't touch the top-level claim being contradicted.

## WARP

`OntologicalWeb`'s own new WarpCapable surface (added by FIX-A010)
shows zero trials across the whole run — meaning the below-threshold
fallback path (`_select_relation_type()` failing to clear 0.70 cosine
similarity against every existing type, and registering a coverage gap
via `check_and_extend()`) never triggered even once; every role-pair
signal in this sequence matched some existing type well enough to be
selected directly. `perception`'s WARP surface: still 0 trials, 0
promoted, no crash (FIX-A007 remains fixed). `recursive_causal_waveform`:
still exactly 1 trial, never promoted, unchanged from both prior
rounds.

## Bottom line

- FIX-A009: real, verified, working exactly as intended.
- FIX-A012: real, verified, working — but only for the specific prior
  cycle it reconciles, only through a conservative mechanical gate, and
  only as an appended clause rather than a revision to the top-level
  belief. A genuine step forward from "flag ignored" to "flag partially
  acted on," honestly short of "contradiction resolves the belief."
- FIX-A010/A011: works exactly as coded, but the directive's own named
  target metric — generic-collapse persisting through all three
  waves, zero causal/temporal/contrastive relation types — is
  **unchanged**. The collapse changed its label from `RELATED_TO` to
  `INSTANCE_OF`, which is arguably a step backward in correctness
  (asserting specific false claims at high depth-weight) even though
  it's nominally a wider vocabulary.
- One regression test (`test_other_role_combination_stays_related_to`)
  now fails for a fully-traced, non-mysterious reason: it encodes the
  exact old default this fix intentionally changes.
- One new finding outside anything either prior round looked for: turn
  3's delivered output is not deterministic across otherwise-identical
  fresh-boot runs of this exact sequence.
- No new relation type beyond the existing 12-type vocabulary appeared
  anywhere; no `CAUSES`/`PRECEDES`/`CONTRASTS`/`IMPLIES` relation was
  ever created in three full rounds of this test, across three
  different fix attempts.

---

## Raw data

Full per-turn JSON (all four nodes' relation lists, RCRW cycle records
including the full `_cycles` history with reconciliation logs, WARP
snapshots for `perception`/`recursive_causal_waveform`/`language_field`/
the `OntologicalWeb` itself) available at
`/tmp/claude-0/-home-user-aurora-/0118081b-fb05-5949-b424-9f4b76c3423a/scratchpad/build650_pressure_test_results_v5.json`
for this session; not committed to the repository (observational run
record against a throwaway isolated boot, not a code change).
