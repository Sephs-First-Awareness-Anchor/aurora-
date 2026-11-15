# Evidence qualification for the environmental genealogy (FIX-A144 revised, FIX-A145)

**Authors:** Sunni (Sir) Morningstar & Cael Devo
**Date:** 2026-11-14
**Directive:** Developmental Evidence, Simulated Experience, and Consequence-Grounded Promotion (Stages A and B done; C–F open, see §8)
**Stack:** #251 (FIX-A143) ← #253 (this); #252 merges cleanly with this stack and the combined state passes 127 tests (§7).

> Experience precedes dreaming. Dreaming may transform experience. Consequences determine development. Genealogy preserves the lineage.

## 1. One event, seven questions (`aurora_internal/evidence_qualification.py`)

Kept apart, never collapsed into one label:

| Question | Field | Values |
|---|---|---|
| Where did it originate / what happened? | `occurrence` | heard, read, perceived, acted, tested, derived, imagined, simulated, dreamed, recalled |
| How is its content supported? | `basis` | observed, told, corrected, supposed, inferred, unknown |
| What did it develop from? | `ancestry`, `ancestry_status` | event ids; traced / partial / unattributed |
| What world does it apply to? | `context` | world: external, internal, simulated, dreamed, imagined; plus a domain |
| Which mechanisms contributed? | `consequence.attribution`, `attribution_complete` | event ids; incomplete is the default |
| What actually changed? | `consequence` | target + change |
| Where has it demonstrated effect? | computed by `demonstration()` | never asserted |

The existing mechanisms are preserved: event identity (hash of content; replay is one event; fields at their defaults are
not hashed, so events written before the new fields keep their ids), deterministic merge, replay idempotence,
contradiction preservation (a correction settles the verdict, what it settled stays visible), conflict detection.

## 2. Rules the tests hold

* An imagined, simulated or dreamed occurrence **cannot** carry told/observed/corrected content, and cannot claim the
  external world. A dream is a real dream; it is not evidence the dreamed event occurred. A simulation is real
  computation; it does not certify external effectiveness.
* Hearing is an occurrence; what was said is testimony (`told`), supposition or correction by its content. A user_input
  stream is **not** "observed fact".
* A recollection never adds evidence (the original carried it). A recalled dream does not confirm its contents.
* inferred and unknown never count; an inference must name its premises and cannot raise their confidence.
* `carried` (legacy) evidence keeps the standing it had and is labelled unattributed; genuine evidence later clarifies it.
  Nothing she developed is disabled by migration.
* `violations(before, after)` names dropped events, rewritten events, laundered basis (a dream returning as an
  observation) and **conflicting duplicate ids** (Codex P2 on #253: the earlier version let the last duplicate win).
* `grounding()` follows ancestry/premises to lived roots and reports dangling and ungrounded ancestry. It invents
  nothing: a dream element with no supported ancestry is reported as ungrounded, not given a history.
* `demonstration()` counts **distinct consequences**, so a replay, or a re-run reproducing the same result, adds no
  independent evidence; a different attribution or change is new evidence. External support needs a lived, observed
  test or action in the external world. A failed external test is kept and revises applicability
  (`external_contradicted` / `external_mixed`) without erasing the simulation's history.
  (Bug found by its own test: testimony and a test of the same consequence shared a signature; the occurrence kind is now part of it.)

## 3. Stage B: provenance at the source (FIX-A145)

* The store defaulted a missing basis to `told`. Now `unknown`, kept on the predicate (basis count, history), never
  counted, never strengthening a relation, marking a source, changing a word's role or placing a concept, and never
  voiced as a statement (asked directly, she says she does not know).
* Every production caller states its basis; an AST test fails if one relies on a default again. Harvested text and the
  identity record say `told` **by decision**.
* Standing that predates provenance is untouched and reported as unattributed.
* 23 test fixtures that teach by testimony now say `basis="told"`.

## 3b. How finely a memory is held: the live view (Sir, 2026-11-14)

A memory that mattered should be held more finely than one that did not. The rule, in `evidence_qualification.py`:

* **The log is the authority and is never shrunk.** Active cognition holds a *view* derived from it (`live_view`).
* **Fineness follows impact, read from the events, never from a flag or from emphasis** (saying something emphatically is
  testimony about importance, not evidence). Held in full: events carrying a **consequence**, **corrections**, the losing
  side of a **contradiction**, events **overruled** by a correction, events relied on as **ancestry / premise / attribution**
  by another event, and the **first**, **latest** and **latest counted** event. Ordinary repeats become counts; the `budget`
  most recent ordinary events stay in full.
* **Importance shows up late**, so the view is rebuilt from the log: a compacted memory that is later cited as ancestry
  regains its detail. (Detail already thrown away could not be regained, which is why the log is never shrunk.)
* **Shrinking is lossless for the evidence.** `view_qualification` reads only the view and equals the whole log's
  qualification on 120 random logs x 4 budgets; `view_problems` catches an invented, altered, relabelled, miscounted or
  dropped entry; building a view leaves the log untouched and `violations()` empty.
* **Named limitation:** the propositional store trims its history by position (first + latest 7), not impact, so a
  correction in the middle of a long history is evicted from `history` (its effect survives in `settled`). A test records
  this; adopting impact-aware trimming in the store is a separate change, not made here.
* **Not available as a signal:** "how often a memory changed her answers" has no producer yet; `consequence` is the only
  impact evidence the model has. The identity record would be held finer as per-statement events (who, when, corrected or not,
  what it changed), not by a firmer basis label.

## 3c. The shape of an impact, in the pressure system's own terms (Sir, 2026-11-14)

How finely a memory is held should follow the **shape** of what it did, and that shape already has a native form: the
5-axis pressure vector (X/T/N/B/A, higher = worse) and the relief between before and after (`PressureVec.relief_from`,
`ReliefRecord`). So:

* A consequence carries `pressure_before`, `pressure_after` and `relief` (= before − after, positive means pressure dropped)
  per axis, translated from a `ReliefRecord` by `consequence_from_relief` (nothing re-derived; a relief that contradicts
  before/after is refused). Tests cross-check the arithmetic against the real `PressureVec`/`ReliefRecord`.
* **Unknown shape is not zero.** A consequence with no measured shape is kept in full; a measured all-zero shape is ordinary.
* **Harm matters as much as relief:** pressure that rose (negative relief) is a measured change and is kept.
* **No arbitrary threshold.** "Impactful" is any measured change (the directive: a measurable change is a genuine event).
  Redundancy is judged by form, not size: events repeating a shape already held (same target, same sign pattern over
  X/T/N/B/A) are compacted into per-axis sums; the **first** and the **strongest** of each form stay in full.
* **Compaction loses detail, never shape:** the roll-up carries per-axis relief sums, and `view_shape` equals the whole
  log's shape (80 random logs x 3 budgets).
* **Replay noise cannot inflate an effect:** a consequence's identity is what changed, not the measured quantity, and
  relief is rounded (float noise does not make a replay a new event). `demonstration` reports `effect` (mean relief over
  *independent* consequences; the first occurrence stands for a signature), `samples` and `distinct_contexts`, the same
  quantities genealogy keeps in `AbilityProfile.consequence_profile`. It does not report a confidence: that needs a
  rule for what volume and recurrence justify, which is not established here.
* **Not yet connected:** nothing produces these consequences in the live path. The natural producer is
  `ConstraintGenealogyLogger._attribute_consequence`, which already attributes measured relief per ability; wiring it is
  Stage D/E work and has not been done or measured.

## 3d. Impact is tied to the received or environmental input (Sir, 2026-11-14)

Sir's correction: her lower subsystems (emotion, development) are all measured through pressure, so an event's impact
should be tied directly to the input she received, not asserted. The contract now does this without adding a second
language.

* **What came in.** An event may carry `input_pressure`: the per-axis load (0..1 on X, T, N, B, A) that
  `aurora_input_pressure.content_axis_loads` measured for that input. It is carried, never recomputed. `None` from the
  intake (no word loaded any axis) means *unknown*, and the field is omitted; `{}` means measured and loaded nothing.
  Non-finite, negative or off-axis values raise. It joins the event id only when set, so existing ids do not move.
  `input_shape_of(event)` gives dominant axis, profile string and peak.
* **What it did.** A consequence names the subsystem that measured it (`measured_by`, e.g. `emotion`, `development`) and
  the input it answers (`attribution`). `effects_of(log, input_id)` groups the independent measured consequences per
  subsystem (relief per axis, pattern, samples). The same relief measured by two subsystems is two effects; a re-run of
  one effect is one; a `recalled` occurrence is not an effect (nothing was measured).
* **Fineness follows effect.** `impact` gains an `effect` reason: an input is held finely when something measured a
  non-nil effect, or when an effect exists but its shape is unknown. An input whose every recorded effect was measured
  nil does not earn a place on that ground. Being relied on as ancestry stays its own, separate reason.
* **Compaction keeps what came in.** The rollup sums input pressure per axis for what it compacted, and
  `view_input_shape(view) == log_input_shape(log)`; `view_problems` catches a view that lost any of it.
* **Pressure never changes evidence status.** 40 randomised logs: qualification is identical with and without
  `input_pressure`. A dream that imposes pressure is still a dream and counts as nothing said.

Tests: `tests/test_evidence_input_impact.py` (115, using the real `content_axis_loads` with a stub lexicon); seven mutants caught
(effect tiering both ways, `measured_by` in the signature, rollup input sums, attribution check, replay/recall guard, input validation).

**Measured on the live path (`scripts/measure_input_impact.py`, 8 scripted turns), reported with its limits:**

* The intake produced axis loads for 7 of 8 turns; "Hello Aurora." loaded nothing (unknown, not zero).
* Emotion (DER) moved on every turn, but only `fear` moved appreciably (0.48, 0.30, 0.19 on turns 2-4, which carried
  B/X load); later turns, including the one with the highest-valence content ("terrible ... scared"), moved only `calm` by about 0.03.
  So the correlation between input load and emotion movement is **not clean on 8 turns**; I do not claim one.
* Genealogy relief summed per turn (`observe` pressure/relief) mixes every source in the turn (4 to 17 `observe` calls per
  turn). `observe` notes carry **no turn or input identity**, so relief cannot be attributed to the input that caused it.
  That is the missing link: until the turn/input id is threaded through, `effects_of` has nothing live to read.
* Consistent with the earlier finding: 233 of 233 live trace items have an empty EnvironmentVector.

**Not done:** no live producer. The proposed next step is a read-only shadow producer through
`_attribute_consequence`, after turn/input identity is added to the observe note (both are Stage D, separate commits).

## 3e. Told versus overheard (Sir, 2026-11-14)

Rule from Sir: *told* means addressed or directly involved; *overheard* is information gathered through curiosity and is
never held as truth unless it is confirmed through the told route.

* New occurrence `overheard` (a real, lived event: it happened to her) whose only allowed basis is `unknown`. It never
  counts: any amount of it leaves `n == 0` and the verdict `unsaid`; an overheard denial does not deny and an overheard
  correction does not correct. `qualification` reports `overheard_only` (a lead, never a fact) and `overheard_confirmed`
  (a lead that someone later told her, as an ordinary told event, optionally citing the overheard event in its ancestry).
* `occurrence_of_address(address, stream_type, internal_origin)`: `direct` is `heard` (testimony); `mention` and `ambient`
  are `overheard`. Only speech is re-read by address; read, perceived, simulated and dreamed origins keep their own
  occurrence. A missing or unrecognised address changes nothing (not guessed).
* Decision for Sir: I put `mention` (speech about her that she is not part of) with `overheard`. If you count being
  talked about as "directly involved", it is a one-word change in `OVERHEARD_ADDRESSES`.
* Live finding: the daemon's ambient listener already classifies speech (`_classify_ambient`: direct / mention / ambient) but
  passes it to working memory as `"[ambient:<class>] text"`. Measured: that tagging currently keeps ambient and mention speech out of
  `stated_facts` (the same sentence untagged is learned). That is a protection by tag, not by rule, so
  `tests/test_evidence_overheard.py` pins it. The address is **not yet** passed to the evidence layer; nothing in the daemon was changed.

Tests: `tests/test_evidence_overheard.py` (67); seven mutants caught.

## 3f. Measured relief can now be traced to its input (Sir, 2026-11-14)

The missing link found in 3d: genealogy `observe` notes carried no turn or input identity. Now:

* `aurora_internal/aurora_input_identity.py` holds the identity of the input being processed in a ContextVar. The identity
  is an evidence-contract event (subject `input|<turn_id>|-`; occurrence from the address, so `direct` is `heard`, and
  `mention`/`ambient` would be `overheard`; `input_pressure` as the intake measured it, unknown when it loaded nothing).
* `ConstraintGenealogyLogger._observe_impl` merges **only the input's id** (`{"input_event": id}`) into the notes with
  `setdefault` (a caller that named its own keeps it). What the input was (how it was addressed, the pressure it imposed,
  its turn) is kept **once per input** in `_input_events` (bounded at 256) and written once per input into
  `events_recent.json` under `"inputs"`, limited to inputs the persisted records still refer to. Nothing is repeated on
  each observation. **Identity only: no measurement, gate or decision reads it.**
  Verified: relief, dominant axis, before/after pressure and cost are identical with and without an input set.
* `aurora._process_external_user_turn_impl` begins the identity just before the turn's `try` and resets it in the `finally`.
* A thread started by the turn does not inherit the ContextVar, so a background observation carries no identity: unattributed,
  never guessed.
* `consequence_from_relief` takes `measured_by`; a real `ReliefRecord` now goes end to end: observe -> note -> consequence ->
  `effects_of(log, input_event)` (tested).

**Measured live** (`scripts/measure_input_attribution.py`, 8 scripted turns): 74 of 74 `observe` calls named their input,
8 distinct turn ids, 0 background-thread calls in that run. A longer run may show background observations; they would
appear as unnamed, which is the honest answer.

**Cost:** one short id per relief record (about 20 bytes) plus one small entry per input. (First version repeated the
input's pressure, occurrence and turn on every observation; Sir's correction, "she shouldn't be repeating information", removed that.)

**Not done:** only the direct-turn path names an input. The ambient listener does not call `observe`, so overheard speech has
no genealogy observations to name (not measured beyond that). No producer yet builds consequences from these records
in the live path; that is the next, separate step (read-only shadow through `_attribute_consequence`).

Tests: `tests/test_input_identity.py` (12, including a source guard that the reset is a call inside a `finally`); six
mutants caught (one survived until the guard was tightened). 225 genealogy and live-turn tests pass.

## 3g. Architecture, not awareness (Sir, 2026-11-14)

"The effects of that information should be the thing she experiences; the architecture of it isn't reliant on her knowing
it for it to be how things work." So the evidence contract, provenance, ancestry, the live view and the input identity are
**substrate**. What she experiences is what the information *does*: the pressure it imposes and what her emotion and
development subsystems measure. Nothing in her cognition or speech may read or speak the machinery.

Held by `tests/test_evidence_substrate_boundary.py` (3 tests, 3 mutants caught):

* Only the turn entry (`begin_input`/`end_input`) and genealogy's `observe` (`note_for_observe`/`summary_for_registry`) import it, and only for identity.
* The substrate imports nothing of her cognition or speech (standard library and itself only).
* Nothing outside genealogy and the substrate reads `input_event` / `_input_events` off an observation.

Live check (`scripts/measure_input_attribution.py`, 8 turns): none of the turn results contained `input_event`,
`overheard`, `evidence_qualification`, `input_pressure` or any observed input id. (The word "provenance" appears in every
result, but from her existing `relation_provenance` keys, not from this work.)

What does change her experience is an *effect*, not a disclosure: FIX-A145 means an unattributed claim is not voiced as
known ("I do not know if Mara likes tea"); that is the consequence of not having been told, not a statement about provenance.

## 3h. Read-only shadow: what each input did to each representation (Sir, 2026-11-14)

* `ConstraintGenealogyLogger._shadow_input_effect` is called from inside `_attribute_consequence`'s own `_apply`, so it
  records exactly the representations the real attribution credits (a promoted link for a covered pair, individual
  abilities otherwise; never ids the real one skips or zero-weight ticks), and nothing else. One aggregate per
  (input, representation) in memory (bounded at 4096): ticks measured, relief summed over them, and how many were
  active together. An attribution that names no input is counted (`_input_effects_unattributed`), never guessed.
  **Nothing reads it for any decision, gate, threshold or promotion**; a failure in it never affects the observation.
* `evidence_qualification.consequences_from_input_effects` turns the rows into contract consequences (one per input and
  representation; the tick count is not the independent-consequence count; a representation measured alone is a
  complete attribution, one measured with others is not). Genealogy itself does not import the contract (substrate boundary).
* **First version was wrong and the live comparison caught it:** it counted every trace id and saw 8 samples where the
  real attribution added 5 (a covered pair goes to its link; unknown ids and zero-weight ticks are skipped). Moved into `_apply`.
* **Live, 8 turns:** shadow samples equal the real `consequence_profile` samples added, turn for turn
  (0, 14, 11, 6, 14, 18, 10, 21), 0 unattributed.
* **What it shows about impact, with its limits:** relief is now attributable to the input that caused it. The relation
  between an input's own load and the relief attributed to it is **not clear on these 8 turns** ("What is a noun?",
  X load 1.0, shows X relief 0.002 and T relief 8.3). Rows are per (input, representation) and share the same tick relief
  across crowded items, so they are not additive across rows and not comparable across inputs of different trace size. A fair comparison needs
  per-credited-item normalisation and more turns; I do not claim a correlation.
* Not persisted (in memory only), not wired to emotion (DER) yet, not read by anything.

Tests: `tests/test_input_effect_shadow.py` (13, including a naturally promoted link and a skipped representation);
six mutants caught. 787 tests pass across the evidence, identity, genealogy and live-turn suites.

## 3i. Stage C: dream ancestry (directive VIII, tests 1, 2, 3, 6)

* **Dream and simulation observations name themselves.** `identity_from_notes` builds an input identity from an observation's own
  notes when it carries `source: dream_episode` (or `simulation`) and an episode id (`seed_lineage_id`/`episode_id`): occurrence
  `dreamed` (or `simulated`), identity deterministic from the episode and never from the clock, so one episode is one
  occurrence and replaying it is the same input. Notes that name no episode get no identity (nothing is guessed).
* **A per-representation ledger** (`_rep_ledger`, persisted as `rep_ledger.json`, bounded) records, for each representation
  genealogy credited, ticks / distinct inputs / relief **by kind of occurrence** (lived, hypothetical, overheard) and the
  lived inputs that credited it (its experiential ancestry, most recent 8). It is written from the same place the real
  attribution credits (`_apply`), so it is the same single developmental history, not a second system.
* **`ancestry_of(rep_ids)`** answers "which lived inputs supplied this dream's material": `traced` / `partial` /
  `unattributed`, listing the unattributed ones. A representation the ledger never saw credited (legacy, never credited) is
  `unattributed`; nothing is reconstructed, and a dream never adds to a representation's lived history.
* **Replay vs new:** ticks are kept but `n_inputs` counts distinct inputs, so the same dream replayed five times is one
  independent occurrence (five ticks) and a different episode is a second.
* **Tests** (`tests/test_dream_ancestry.py`, 12; eight mutants caught, one survived until the clock test was tightened):
  test 1 (dream traces to the lived inputs; no lived history created), 2 (a relationship that first appears in a dream keeps
  each constituent's own provenance), 3 (an element with no ancestry stays unattributed and no history is made), 6 (replay is
  not new evidence; a new episode is), restart persistence, an unreadable ledger is unattributed (no crash), and the dream path
  changes no real consequence profile.
* **Live** (`scripts/measure_dream_ancestry.py`): after the 8 turns, 17 representations had lived ancestry; a dream episode
  over two of them plus one never credited was `partial` (2 traced, 1 unattributed), the unattributed one had no lived history, and
  lived totals were unchanged.
* **Not covered:** the dream trainer's gateway replay (`_witness_directed_training_samples`, `internal_origin: dream_replay`)
  produced **0** genealogy observations in the live measurement, so it credits nothing synchronously; whatever it does later is
  not measured here. Legacy representations (everything credited before this change) are `unattributed`; their history is not
  reconstructed. The ledger is capped (16 inputs per kind, 8 lived ancestors), so very long histories are marked `capped`.

## 4. Audit findings (read from the source; the live one measured)

1. **The genealogy's evidence-origin label is empty in practice.** `scripts/measure_stream_provenance.py`: in an
   8-turn live script, **233 of 233** trace items carried an empty `EnvironmentVector` (76 `observe` calls from the
   evolution chamber tick, the understanding contract, `_log_learning_relief`, `_log_modulation_event`,
   `_inject_to_genealogy`). The documented "dream"/"simulation" labels are never produced there. Qualification has to
   be created at the source; there is nothing to preserve yet.
2. **Four unrelated stream vocabularies exist:** the gateway's `StreamType` (user_input, knowledge_feed, sensor_data,
   system_event, exploration, self_reflection), the genealogy docstring's (adds simulation, corpus, dream), the lineage
   compiler's `"synthetic_lineage"`, and `notes["stream_type"]` in the dimensional path (read; nothing found writing it).
3. **Dream replay enters as `knowledge_feed`.** `aurora_dream_trainer._witness_directed_training_samples` sends replays
   through `gateway.receive(stream_type=KNOWLEDGE_FEED, metadata={"internal_origin": "dream_replay"})`. The origin is only
   in metadata, so a stream-based reading would call a replay read/testimony. `occurrence_of_stream(stream, internal_origin)`
   lets the origin outrank the stream. Those replayed samples are *directed-training lesson attempts*, i.e. replays of
   external lessons, not novel dream content; whether Aurora produces novel dream recombinations that reach memory is
   not established by this audit.
4. **Promotion gates are source-blind.** `_try_promote` judges `PairStats` (count, mean/positive relief, positive
   fraction, stdev, x-risk); `PairStats` and `ConstraintLink` have no evidence-origin field, and the gates do not read
   the representation relation. Whether dream or simulation traffic reaches `observe` was **not** measured (the dream
   trainer was not run); no direct genealogy `observe` call was found in the dream trainer or simulation engine by grep.
5. Promotion was not altered (directive: audit first). The existing numeric thresholds are unchanged and still
   unexplained as to what they measure; the directive asks that be established before any dream/simulation weighting
   is touched.

## 5. Decisions made by the directive, and what remains Sir's

Decided by the directive: a simulation is an actual process with hypothetical contents; dream/simulation
co-activation may contribute to promotion when it yields a demonstrated consequence (no fixed discount fractions);
missing basis stays unknown. Remaining for Sir:

* The identity record and harvested text are `told` by decision here. Is the identity record better qualified?
* Mappings added beyond the directive's table (`sensor_data → perceived`, `synthetic_lineage → derived`,
  `dream_replay → dreamed`); `system_event`, `exploration`, `self_reflection` are left unspecified rather than guessed.
* What `consequence.target` names for a promoted link (a link id, a capability id) when Stage D wires it.

## 6. Directive tests 1–7, at the contract level only

| # | Test | Where | Level |
|---|---|---|---|
| 1 | Experiential precedence | `test_experiential_precedence...`, `test_a_dream_does_not_create...` | isolated |
| 2 | Novel recombination | `test_novel_recombination...` | isolated |
| 3 | Dream without grounding | `test_without_supported_ancestry...` | isolated |
| 4 | Internal promotion ≠ external | `test_internal_promotion_evidence...` | isolated |
| 5 | Simulation disagreement | `test_a_simulation_predicting_success...` | isolated |
| 6 | Replay vs new consequence | `test_replaying_a_dream...`, `test_a_genuinely_new_interaction...` | isolated |
| 7 | Provenance integrity | `test_every_basis_survives...`, store tests in `test_unknown_provenance.py` | isolated + store |

Tests 8–10 (cross-device, comparative equivalence, performance) are **not done**.

## 7. Verification

* 455 contract tests (axes 42, base 40, live view 129, pressure shape 129, input impact 115) + 10 store tests; thirty-two contract mutants and four store mutants each caught (one more store mutant, the
  recorder's own default, survived until a direct test was added).
* 384 tests across every file touching the knowledge path pass; the single failure (`test_build694` turn-id source
  check) fails identically on clean `main`.
* Live: `alphabet_order` 5/5 held as evidence, READY; `identity_perspective` still takes its taught statements and keeps its 4 open gaps.
  `basic_communication` did not finish inside the time I gave it, so it is not claimed.
* Combined with #252 in a throwaway worktree: merges without conflict, 127 tests pass (#252's audit and index tests included).

## 8. Status against the deliverables

| # | Deliverable | Status |
|---|---|---|
| 1 | Revised FIX-A144 contract | **implemented, isolated tests** |
| 2 | Ancestry and context representation | **implemented in the contract, isolated tests**; not in any live record |
| 3 | Provenance assignment and legacy handling | **implemented in the propositional store, isolated + related-suite tests, two lessons live**; genealogy side not started (§4.1) |
| 4 | Dream ancestry preservation | contract only; the dream path was audited, not changed |
| 5 | Qualified dream/simulation promotion | **not started** (audit only) |
| 6 | Environmental genealogy processing | **not started** here (#252 holds the index work) |
| 7 | QuasiArch ancestry retrieval | **not started** (`grounding`/`demonstration` are the retrieval it would call) |
| 8 | Comparative developmental results | **not done** |
| 9 | Performance | #252's measurements stand; nothing new |
| 10 | Limitations / rollback | below |

No device validation of any kind. Nothing here is integrated into the genealogy or the dream path.

**Rollback:** FIX-A145 is isolated to `aurora_propositional_understanding.py` (default basis, `UNCOUNTED_BASES`, the unsaid guard)
and one explicit `basis="told"` in `aurora_clone_harvest.py`; reverting those restores the old default. The contract module
has no callers, so removing it changes nothing live. No stored state was rewritten.

**Limitations:** the contract is proven against the propositional store, not against genealogy records, which do not yet
carry the information (§4.1). `consequence.target` has no producer. Sensor uncertainty is not represented (no basis for a
number). Bounded predicate history (8) is still bounded in the store; the event log must not cap it.
