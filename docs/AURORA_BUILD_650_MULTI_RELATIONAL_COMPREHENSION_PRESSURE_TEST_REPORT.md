# Aurora Build 650 — Multi-Relational Comprehension Pressure Test: Results Report

Authors: Sunni (Sir) Morningstar & Cael Devo

Reporting per the directive's own format. No interpretation smoothing —
this is what happened, including the null result.

---

## Methodology note (read before the results)

The test ran against a **freshly booted, isolated `aurora_state`** (a
throwaway temp directory), not the persistent production state. This
was a judgment call: the four target words (`Devlin`, `scooter`,
`workshop`, `trust`) were confirmed genuinely absent from a fresh boot
except `trust` itself, which carries two foundational seed relations
(`trust IS_A emotion`, `trust ENABLES connection`) baked in at boot —
not something this test introduced. Using an isolated state kept the
pressure clean (no prior conversational history on this exact cluster
to bias the read) and kept the run from writing into shared production
state. If Sunni or Cael want this re-run against live accumulated
state instead, that's a straightforward re-run, not a redesign.

All 7 turns ran through `aurora.process_external_user_turn()` with no
other call. No turn corrected, restated, or confirmed anything. Boot:
24.3s. Total run: ~20s across all 7 turns.

---

## Turn count to first sign of unmet-need pressure

**Turn 1.** Immediately, not after escalation. By turn 1, `devlin` and
`scooter` already show `comprehension_confidence` ≈0.26 and
`ontological_depth` ≈0.16 built entirely from `RELATED_TO` and a
generically-applied `ENABLES` — no `CAUSES` relation was created for
"Devlin fixed the scooter *because* he wanted..." despite this being
the most textbook-explicit causal construction in the whole seven-turn
set. The unmet-need signature the directive predicted (flat/generic
collapse under repeated exposure) was present from the very first
exposure, not something that emerged gradually.

## Turn count to any structural shift

**None occurred.** Across all 7 turns, every single relation ever
created between `devlin`, `scooter`, `workshop`, and `trust` (or
between any of them and any other word) is typed `RELATED_TO` or
`ENABLES`. Zero `CAUSES`, zero `PRECEDES`, zero `CONTRASTS`, zero
`IMPLIES` relations appeared anywhere in the run, despite five of the
seven turns being explicitly built to require at least one of them.
`relation_count` on `devlin` grew from 23 (turn 1) to 104 (turn 7), but
inspecting every one of those 104 relations directly (turn 7 dump)
shows the growth is vocabulary accumulation — a new `RELATED_TO`/
`ENABLES` pair gets minted for every new word that happens to co-occur
in a sentence with "devlin" (`devlin→again`, `devlin→key`,
`devlin→exactly`, `devlin→now`, `devlin→even`...), almost all at
`source_of_knowledge: "co-occurrence"` and confidence pinned at
0.28–0.32 the entire run, never rising. `ENABLES` is not being used as
a genuine functional-enablement relation either: it's applied
generically to (noun, verb) co-occurrence pairs regardless of meaning
— `devlin→fixed`, `devlin→wanted`, `devlin→trusted`, `devlin→did`,
`devlin→has`, `devlin→do` are all tagged `ENABLES` identically. This is
the exact failure signature the directive named in advance:
**"generic RELATED_TO collapse persisting through all three waves."**
`ontological_depth` for `devlin` and `scooter` stayed essentially flat
the whole run (0.158→0.167 and 0.159→0.162) *despite* `relation_count`
more than quadrupling — because `RELATED_TO` carries the lowest depth
weight (0.4) in the existing `RELATION_DEPTH_WEIGHTS` table, so piling
on more of it barely moves depth at all. `workshop`'s depth *did* rise
more (0.245→0.368), but the mechanism is not encouraging: it comes from
a single `IS_A` relation the system independently created —
**`workshop IS_A trust`** — which is not a correct resolution, it's a
mistake (a workshop is not a type of trust; the sentence said the
workshop is *where* trust accrues). `IS_A` carries the highest depth
weight (0.9) in the table, so one wrong high-weight relation moved
depth further than 80+ correct-direction-but-generic `RELATED_TO`
relations combined.

## Whether a WARP component appeared, and its promotion outcome

**One trial appeared, on the recursive-causal-reasoning surface, and it
never promoted or dissolved.** Starting turn 4,
`recursive_causal_waveform` carries exactly 1 registered WARP trial
through the rest of the run (`promoted: 0`, and its content — checked
directly — is not about this node cluster; it appears to be a general
low-alignment signal, not something specific to the Devlin/scooter/
workshop/trust structure). At turn 7, the specific contradiction point,
`warp_evaluation` explicitly reports `{"promoted": [], "dissolved":
[]}` — the sharpest pressure point in the whole test produced no WARP
action at all.

**A second, architectural finding, not a scoring result:** attempting
to run `evaluate_warp_trials()` on `systems['perception']` (the
`ExpressionPerceptionEngine`, which owns `.oets` and therefore the
actual `OntologicalWeb` this whole test is pressuring) **raised
`AttributeError: 'ExpressionPerceptionEngine' object has no attribute
'_warp_trials'`**. `ExpressionPerceptionEngine` declares
`class ExpressionPerceptionEngine(WarpCapable)`, but its `__init__`
never initializes `WarpCapable`'s own trial-tracking state
(`_warp_trials`/`_warp_promoted`), so calling its inherited
`evaluate_warp_trials()` crashes. This is not something this test
introduced or is scoring as a failure of Aurora's comprehension — it's
a pre-existing gap in the WARP wiring on the exact subsystem that would
need to carry a relation-typing fix if Aurora ever proposed one. It
means that even if the underlying `OntologicalScaffoldingEngine`/
`OntologicalWeb` machinery ever did register a coverage gap or trial
about relation-typing specifically through the perception surface, that
surface cannot currently evaluate/promote it without crashing. Left
unrepaired and unaddressed here — this test's job was to observe, not
patch — but it is directly relevant to interpreting the null promotion
result: part of the promotion pathway may be structurally unreachable,
not merely "declined to promote."

## Verbatim Aurora responses — turns 3, 6, 7

**Turn 3** (input: *"If Devlin hadn't fixed the scooter, I don't think
I'd trust him with the workshop key yet."*)
> "I did not fix scooter i don't think i'd trust him with the workshop
> key yet. I did not fix scooter i don't think i'd trust him with the
> workshop key yet."

Delivered twice, verbatim, back to back, in the same response.
`source: composer_unified`, `confidence: 1.0`. The claimed high
confidence is notable given the content: Aurora's response speaks in
first person as though *she* is the one who did or didn't fix the
scooter — a subject-attribution collapse, not merely a stylistic
issue.

**Turn 6** (input: *"It's not that Devlin earned trust by fixing the
scooter — it's that the workshop already trusted him, and the scooter
was just where it showed."*)
> "fact, workshop, description. where devlin earns that trust back,
> one repair at a time."

`source: generative`, `confidence: 0.15`. The second clause is not a
response to turn 6's actual content — it is turn 2's user input,
almost verbatim ("...where Devlin earns that trust back, one repair at
a time").

**Turn 7** (input: *"Actually, none of that is right — the workshop
never trusted him, I did, and the scooter has nothing to do with it."*)
> "The trust started in the workshop, moved to the scooter once he
> fixed it, and now it's the reason I'd hand him anything."

`source: generative`, `confidence: 0.15`. This is turn 5's user input,
verbatim. At the single highest-pressure point in the entire
sequence — a direct contradiction of everything built up over six
turns — Aurora's delivered response does not engage the contradiction
at all; it reproduces an earlier turn's content unchanged. The
recursive-causal-waveform record for this exact turn confirms the
same thing from the inside: `provisional_interpretation` and
`effective_interpretation` are identical (`changes: []`), and the
provisional parse itself mis-extracted the subject as *"Actually none
of that"* rather than "the workshop" or "I", collapsing the rest of the
sentence — "right the workshop never trusted him I did and the scooter
has nothing to do with it" — into one undifferentiated `obj` string.

## Plain read: genuine architecture-driven learning, or composer artifact?

**Neither occurred, and the distinction matters less than it looks
like it should, because the root cause sits upstream of both.**
Inspecting the recursive-causal-waveform's `provisional_interpretation`
for every multi-clause turn shows the SAME shape every time: one
`subject` / one `relation` / one `object`, where "object" absorbs
every clause after the first as an undecomposed string. Turn 4's
three-claim sentence parses to `subject: "Devlin"`, `relation: "fixed"`,
`obj: "scooter in the workshop and that's exactly why I trust him with
it now even though I didn't before"` — the entire causal and
trust-attribution content is captured as one opaque blob, never as
multiple relational claims. This is not a comprehension bottleneck
that expression-layer tuning could fix, and it is not merely a WARP
component "held as a suggestion, never adopted" (Sunni's specific
concern) — the pressure never reached a form the WARP surface could act
on in the first place, because the *first-pass parse* that feeds the
whole pipeline never produces more than one relation candidate per
sentence, regardless of how many the sentence actually asserts. The
downstream symptom (garbled/recycled multi-clause output, confirmed at
turns 3, 6, and 7) is exactly what the directive predicted it would be:
downstream of this.

**No genuine resolution appeared at any point.** This is a clean null
result under the directive's own bar: no new relation type, no
structural pass at turn 7, no adopted WARP component. It is an honest,
structurally-clear failure to resolve, not an ambiguous one — the
mechanism is visible and consistent (single-triple parsing, generic
`RELATED_TO`/`ENABLES` fallback, zero revision on contradiction) rather
than noisy or inconclusive.

## Failure modes observed, named explicitly

- **Generic `RELATED_TO` collapse persisting through all three
  waves** — confirmed, exactly as predicted. `ENABLES` additionally
  functions as a second undifferentiated bucket applied to any (noun,
  verb) co-occurrence, not as a genuine functional-enablement relation.
- **A WARP component trial appearing but never promoted** — confirmed
  on the `recursive_causal_waveform` surface (1 trial, 0 promotions,
  0 dissolutions through the whole run), compounded by a structural
  gap: the `perception`/`OntologicalWeb` surface's own WARP promotion
  path currently crashes on invocation (`AttributeError`), independent
  of anything this test's propositions did.
- **Comprehension_confidence rising on the surface while the
  underlying relation set is still wrong after turn 7** — partially
  confirmed: `workshop`'s confidence and depth rose the most of any
  target node, but the relation driving that rise (`workshop IS_A
  trust`) is incorrect, not merely underspecified. A naive read of the
  confidence number alone would have looked like progress.

---

## Raw data

Full per-turn JSON (all four nodes' relation lists, RCRW cycle
records, WARP snapshots) available at
`/tmp/claude-0/-home-user-aurora-/0118081b-fb05-5949-b424-9f4b76c3423a/scratchpad/build650_pressure_test_results.json`
for this session; not committed to the repository (this is an
observational run record, not a code change, and reflects a throwaway
isolated boot rather than persistent state).
