# Aurora Live-Turn Baseline and Findings — 2026-11-11

**Authors:** Sunni (Sir) Morningstar & Cael Devo
**Directive:** Unified Cognitive Architecture, Parts II, V, VI, XIII, XV (§43).
**Method:** `scripts/measure_turn_baseline.py` boots Aurora against a copy of the
repository's `aurora_state` and runs six fixed live turns through
`process_external_user_turn` with the arguments her phone uses. Everything
below was measured on those runs, on a 2-core development machine (not the
phone), from the repository's state (not the phone's lived state).

## 1. Every live turn on `main` was crashing (fixed — FIX-A119)

Commit `5aaa303` (merged in #238, 2026-11-09) built the per-turn parse cache on
`_turn_ledger.computations` sixty lines **above** the line that creates
`_turn_ledger`. `_run_live_response_turn` raised `UnboundLocalError` on its
first statement, for every turn. No test in CI runs a real turn, so it merged.

Fixed by resetting the ledger first, as `reset_turn_ledger`'s own docstring
requires. `tests/test_live_turn_smoke.py` now boots her and runs real turns in
PR CI, with a static guard for this ordering.

## 2. The last response stage raised NameError (fixed — FIX-A120)

`_build_grounded_fallback_response` read `state.pipeline_state`, but `state` is
not one of its parameters. Its lookup branches raised `NameError`, swallowed by
the boundary handler in `_chain_down2_belief`. It now receives the turn's
pipeline state as an argument. This removes the fault; it does **not** by
itself make her speak (see §4).

## 3. Baseline (after FIX-A119; before it, no turn completed)

| Measure | Value |
|---|---|
| Boot | 14–22 s |
| Peak memory | ~650–690 MB |
| Six turns, unprofiled | 9.2–9.8 s total; first turn 2.7–3.0 s, later turns 0.6–2.1 s |
| Function calls per warm turn (profiled) | ~9 million |
| Shared compute graph per turn | 1 computation, 2 hits |

Run-to-run, her replies to identical input differ (4 of 6 matched between two
runs with a fixed hash seed). A before/after comparison therefore cannot use
"same reply" as proof of no behavioural change; equivalence has to be shown at
the level of the function being changed.

## 4. Where a warm turn's time goes (five warm turns, profiled, 17.3 s)

| Share | What | Evidence |
|---|---|---|
| ~18% | `ConstraintGenealogy.observe` — 17 calls per turn | 85 calls, 3.05 s; `_representation_index` rebuilt 62 times (1.62 s, 836k sort-key calls) |
| ~15% | Grammar `observe_exchange` — 8–9 calls per turn, each logging relief to genealogy | 43 calls, 2.62 s; 2.16 s of it in `_log_relief_to_genealogy` |
| ~14% | Whole-file JSON rewrites | 86 dumps, 2.37 s, 4.65M encoder calls; `aurora_expression_perception.py:626 save` alone 1.23 s for 5 calls; grammar `_save` 1.09 s |
| ~7% | Lexical grounding gap submissions | 158 `observe_lexical_context`, 140 `_submit_gap`, 1.26 s |
| one-time | Genealogy relevance index cold build | ~5 s, first turn after boot only (13.7k abilities); already incremental afterwards |

## 5. Tried and reverted: sharing every parse through the turn graph

The same user text is parsed 10–13 times per turn by readers that each build
their own `UtteranceParser` (14–17 parses for 2–3 distinct texts). Routing all
of them through the existing `TurnComputeGraph` cut parser runs from 77 to 20
over five turns and produced identical parses — and **no measurable time
change** (20.11 s → 20.09 s profiled; within noise unprofiled), because the
expensive part of a parse is already memoised below it. Per the directive
(complexity must show benefit), the change was **not kept**. The redundancy is
real; it is not where the time is.

## 6. Learning-integrity finding (not yet changed — needs a decision)

`ExpressionComposer.absorb` forwards heard text to
`GrammarEngine.observe_exchange("", text, success=True)`. Observed on real turns:

- **Heard and unspoken text is credited as her successful production.** With
  `success=True`, `observe_exchange` calls `_log_relief_to_genealogy`, whose
  own docstring says it logs relief "when a grammatically clear sentence is
  produced" (A = expression completed, agency exercised), and it credits
  `_last_motif_id` — the last motif **she** applied. So each of the following
  rewards her most recent expressive motif as if she had just spoken well:
  the user's sentence (2–3 times per turn, two of them identical calls),
  recalled memories, and her own internal candidates that were never said
  (`"I am meaning."`, `"You do consciousness."`) on turns that ended in silence.
- **One recalled sentence counts as several new contexts.** Recall re-absorbs
  the stored sentence once per recall keyword, with the marker inside the text
  (`"[recalled:fixing] I spent the morning…"`, `"[recalled:house] …"`). The
  context hash is taken from that text, so each keyword is a distinct context.
  Context diversity is the motif promotion gate (≥ 3 contexts).

This is the directive's §26 and §23 exactly: consequences reinforcing
representations that did not contribute, and counts growing without
understanding. It is also the second-largest cost in §4.

**Proposed repair (mechanism only, nothing scripted):** heard text still feeds
the motif lineage as exposure, but (a) production relief is logged only for
sentences she actually emitted, (b) a recalled sentence is absorbed with its
marker stripped, so it shares the context it was first heard in, and (c) one
sentence is absorbed once per turn.

## 7. Other verified faults, not yet fixed

- `aurora_consciousness_engine.py` (reality-warp routing) calls
  `SimulationSession.run_epoch(topic=..., focus=...)`; `run_epoch` accepts
  neither argument. `TypeError`, swallowed, 1–2 times per turn: severe
  paradoxes never reach the simulation engine. Not "fixed" by simply dropping
  the arguments — that would run a full 8×5-episode epoch inside a live turn.
- **Direct greetings end in silence** (`src=silence`) on the repository state:
  "Hey Aurora, how are you today?" produced no reply in every run. Candidates
  are formed internally (`"I don't have a clear sense of that."`,
  `"What do you mean by 'spent'?"`) and do not reach expression. Her own
  communication-emergence record names the deficits ("no selected resolution
  crossed into expression", "response obligation remained unresolved"). Where
  the candidates are dropped has not been traced yet.

## 7a. Silence trace (2026-11-12)

Silence is her voice gate working as designed (`aurora_voice_gate.py`,
2026-11-07): scripted candidates are blocked, and she speaks only when her own
composition, the confluence, or pressure articulation produces something.
`systems["_last_voice_gate"]` records why each turn ended as it did. On eight
live turns the blocked candidates were all scripted sources
(`constraint_abstain`, `constraint_seek`, `constraint_semantic_derivation`) or
a leaked internal label (`"pressure:turn_chain."`), and the confluence
reported `nothing_contributed` on every turn it ran.

Tracing why nothing contributed led to the earliest stage of all:
`extract_relational_form`. It bound a noun as the relation in 9 of 11 plain
sentences ("The posts were rotten" -> relation "posts"; "My name is Sunni." ->
subject "My", relation "name"). The confluence builds her stance from that
relation and requires it to be a verb, so a misbound sentence can contribute
no stance.

**A repair was written and withdrawn (FIX-A122).** It corrected the binding by
adding positional English rules to the scaffold. On 5,000 sentences from her
corpus it rebound 264 and lost none. It was withdrawn because it was authored
grammar placed in her by hand: such knowledge may exist in her only in the way
it would if she had generated it herself (Sunni, 2026-11-12).

**What remains true and unaddressed:**
- the misbinding itself;
- a suffix guess outranks her own promoted relation roles, which are consulted
  only when no guess exists anywhere in the clause;
- on the repository state she has promoted zero relation words, so the route
  by which she would earn this herself is not yet producing anything;
- "How are you?" binds the copula "are", which gives the confluence no
  content verb. Her confluence deliberately has no "I am <feeling>" frame
  (FIX-A114: affect sets tone, it is not a clause), so that is not the repair.

## 7b. Learning-integrity repair (FIX-A123, approved 2026-11-12)

Implemented as proposed in §6, with one difference stated plainly: recalled
fragments are no longer absorbed as heard language at all (rather than
absorbed with the marker stripped). They only ever reached absorption because
the recall-enriched copy of the turn's input was ingested a second time; that
copy now still feeds perception and expression context but is not heard twice.

Measured on the same two traced turns: exchange observations per turn went
from 8 and 6 to 4 and 1, and none of them logs production relief. Credit for
her speech now comes only from `record_motif_outcome()`, i.e. from what the
receiver actually did next.

**Latency:** no measurable change on this machine (six turns unprofiled:
9.2–9.8 s before, 10.6–10.9 s after, on a host whose boot time alone varied
between 14 s and 31 s across runs). The one-time genealogy index build moved
from the first turn to the second, because the observation that used to
trigger it early no longer exists.

**Still open:** her unspoken articulation drafts ("You are meaning.", "You did
consciousness.") are still absorbed as heard language, three per turn. They no
longer earn relief, but she is still learning sentence structure from her own
unsaid candidates.

## 8. Status

| Item | Status |
|---|---|
| FIX-A119 turn-ledger ordering crash | Implemented and verified (live turns run; smoke test in CI) |
| FIX-A120 fallback `NameError` | Implemented and verified (fault no longer recorded) |
| `scripts/measure_turn_baseline.py` | Implemented; used for every number above |
| Parse sharing | Tried, measured, reverted |
| §6 learning-integrity repair (FIX-A123) | Implemented and verified by unit tests and live trace; no latency gain demonstrated |
| §4 genealogy index / persistence costs | Measured only |
| FIX-A122 relation-slot repair | **Withdrawn** — scripted grammar; the misbinding finding stands (§7a) |
| Silence trace | Done (§7a); the pathways it points at are not yet traced on a whole-system map |
| Reality-warp routing fault | Not fixed |
| Pre-existing failing test `test_interaction_event_action_handoff.py::...relationless_external_payloads` | Fails on `main` before these changes; untouched |
| Python CI workflow | **Disabled manually since 2026-07-28** — no Python test has run on any PR since; the new smoke test only runs if it is re-enabled |

---

## Addendum 2026-11-13 — what the measurements justified (Task: measured optimization)

Authors: Sunni (Sir) Morningstar & Cael Devo

Per-turn profiles (cProfile, one profile per turn, six fixed turns on the
boot copy of state) show the time is **not** steady redundant work. It is
mostly first-touch cost and her own articulation:

| Turn | Dominant cost (profiled) | Kind |
|---|---|---|
| 1 | genealogy `representation_gap_candidates` 1.9 s | first build of the representation index |
| 2 | genealogy `flush_write_batch` 2.2 s | one 20 MB abilities rewrite (0.89 s unprofiled) |
| 3 | voice gate `articulate_from_pressure` 3.0 s | her articulation |
| 5 | evolution chamber `observe_external_evidence` → genealogy `observe` 1.2 s | chamber tick |

Checked and **found not to be redundant**:

- `representation_is_eligible` (712 entries in the organ map) costs ~0.00 s in total; the call count is not the cost.
- The abilities file was written **once** in six turns (turn 2), not every turn; whole-file rewrites are already gated by the turn-persistence batch.
- The representation index already rebuilds incrementally (Repairs K, L, M).

Found and fixed (behaviour-preserving, equivalence pinned by tests):

| Change | Evidence |
|---|---|
| effect-tag metadata filter uses tuple `startswith` | 11.3 M generator steps, 3.5 s cum (profiled) |
| `_last_tag_value` scans in place in C | 260 k calls; ~7–9× on a hit in a long tag list, not slower on a miss |
| lexicon save uses `dumps` (C encoder) not `dump` to file | 30 ms → 4 ms on the real 940 KB lexicon, byte-identical |

Result: profiled calls 72.1 M → 54.3 M (−25 %); unprofiled wall for six turns
8.59 s → 8.46 s, i.e. within run-to-run noise. The call-count drop is real; the
wall-clock effect is small because the profiler inflates Python-level loops.

Not changed, and why: the 20 MB abilities write (0.9 s once per dirty batch)
uses `indent=2`, which forces the Python encoder; compacting it would change an
on-disk format for under a second, so it stays until a measurement on the
phone says otherwise. The 3 s voice-gate articulation on turn 3 is her
generation path, not storage or bookkeeping; it needs its own trace.

Replies on the six-turn script differ run to run on unchanged code, so reply
identity was not used as a pass condition; 260 genealogy/representation tests
and 6 + 3 new tests were.
