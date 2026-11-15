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
