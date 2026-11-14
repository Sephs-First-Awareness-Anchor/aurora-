# Authors: Sunni (Sir) Morningstar & Cael Devo

# Genealogy redistribution — Stage 1: dependency audit and baseline (2026-11-14)

Directive: *Environmental Genealogy, Deferred Developmental Attribution, and QuasiArch Diagnostic Access*
(§XII Stage 1, §XIV deliverables 1 and 2).

**Status: Stage 1 only.** Nothing in genealogy, the live turn, QuasiArch or the strata link has been changed.
Two measuring scripts were added (`scripts/audit_genealogy.py`, `scripts/baseline_genealogy.py`). Every number
below was produced by them on a scratch copy of the state; nothing is estimated.

## 1. How it was measured

- `scripts/audit_genealogy.py` parses `constraint_genealogy.py` and, for every method `_observe_impl` reaches, lists
  the `self.<attr>` it **writes** and which *other* modules mention that attribute (a grep, so it over-counts common
  names such as `abilities`, `links`, `cfg`; it never under-counts).
- `scripts/baseline_genealogy.py` boots Aurora on a copy of the state, says 8 fixed turns through
  `process_external_user_turn`, and wraps methods **in the harness process only** to count and time:
  every `observe` call (thread, call site, genealogy's own `lock_wait_ms`/`compute_ms`/stage times), whether a call
  changed `abilities`/`links`/collisions, every live `_select_active_abilities` read and what it returned.
  Run alone; wall-clock.
- Machine: the cloud workspace, no phone, no Windows laptop (see §7).

## 2. Baseline (8 turns, warm state: 13,404 abilities, 356 links)

| Run | Turn time | `observe` on the turn thread | Share | Notes |
|---|---|---|---|---|
| 1 | 9.78 s | 2.20 s | 22.5% | no method wrappers |
| 2 | 9.19 s | 2.04 s | 22.2% | no method wrappers |
| 3 | 9.91 s | 2.75 s | 27.7% | + method timing wrappers (overhead) |
| 4 | 10.68 s | 2.58 s | 24.2% | + method timing and selection capture |

Constant across runs: **78 `observe` calls in 8 turns (~10 per turn), all on the turn thread, lock wait 0.0 ms** —
the cost is computation, not contention. The 2026-11-11 baseline (`AURORA_LIVE_TURN_BASELINE_2026-11-11.md`)
measured 17 calls per turn and ~18%; this one measures fewer calls and a larger share, on a different 8-turn script.
The two are consistent in kind, not comparable in number.

## 3. Findings

**F1 — Almost all of `observe` is two searches.** Stage totals over the 78 calls (run 2): collision search
1,260 ms + gap search 654 ms = **1,914 ms of 2,034 ms (94%)**. Pair accumulation, consequence attribution, coupling
roots, gradient/causal feedback, complexity curve and the event write together cost under ~40 ms.

**F2 — The collision search is the index being rebuilt.** `_representation_index` is 1,779 of the 1,863 ms inside
`representation_collision_candidates` (95%); it took over 5 ms on **46 of 47 calls (~38 ms each)**. Cause, read
from the code: its cache stamp includes `len(self._pair_stats)`, which grows on nearly every event, so the
"incremental" path runs every call — and that path re-scans every pair to rebuild activity, copies the whole
cached index, and re-sorts **every** bucket (`constraint_genealogy.py` ~4466–4560). The per-item identity cache
below it is cheap (90k calls, 456 ms). This is the same cost the Nov 11 report saw (62 rebuilds, 836k sort-key calls).

**F3 — What the two searches produce is not experience.** `representation_collision_candidates` documents itself as
returning "bounded unresolved distinctions … for later lived/dream/counterfactual inquiry", never updating
`PairStats` or promoting. Its output goes to `_representation_collisions` / inquiry records. The audit finds readers
of those only in analysis scripts, `aurora_runtime.py` and `run_chain.py`; none in `aurora.py`'s turn code.
`aurora_runtime.py` has not yet been traced, so "no live reader" is still a Stage 2 item to confirm.

**F4 — In this sample, `observe` did not change the abilities or links the live turn reads.** Of 78 calls,
**0 changed the number of `abilities`, 0 changed the number of `links`**; 9 changed only the collision records
(net +42). The harness counted entries, not in-place edits to a profile's fields, so "no change" is established for
membership, not for every field. The live turn's `_select_active_abilities` read `abilities` 8 times, every one after
a same-turn `observe`. This is evidence for deferral being safe **for this sample only** (8 turns, no promotion
happened); Stage 3 must test it against a sequence that does promote, and compare field values, not counts.

**F5 — Where the calls come from (all on the turn thread):**

| Call site | Calls | Time |
|---|---|---|
| `aurora_evolution_chamber.py:1686 tick` | 56 (~7 per turn) | 0.96 s |
| `aurora_understanding_contract.py:2392 _record_genealogy_event` | 15 | 1.11 s |
| `aurora.py:18633 _log_learning_relief` | 5 | 0.10 s |
| `aurora.py:4334 _inject_to_genealogy` | 2 | 0.03 s |

(Grammar `observe_exchange → _log_relief_to_genealogy` was measured separately on Nov 11: 8–9 calls per turn,
2.16 s of 2.62 s — it reaches `observe` through the same path.) The afterthought thread is already off the turn
thread but was not exercised by this harness.

**F6 — Live ability selection is dominated by code-lineage records (directive §IX, confirmed).**
Of 13,404 candidates, **12,884 (96.1%) are code-lineage/evolution records** (ids `…:CODE_LINEAGE_…`,
`…:CODE_EVOLVED_…`); 520 are anything else. Across 8 selections, **38 of the 40 picks were code-lineage records**.
Selection scans all 13.4k per turn and keeps 5. A historical record with an XTNBA signature is being treated as a
live operation, exactly as the directive describes.

**F7 — The existing strata-link outbox cannot carry developmental evidence as it is** (`strata_link.DurableOutbox`):
- on overflow it drops the **oldest events** (counted in `overflow_dropped`, but dropped) — §V forbids silently
  discarding unique evidence;
- its de-duplication memory is the last **400** ids — §V requires duplicate delivery never to duplicate learning;
- every `append` rewrites the whole JSON file (up to 5,000 records) — fine for packets, too heavy per `observe`.
It does have what §V asks to reuse: durable sequence numbers, `ack`, "event" vs "state" kinds, and an authenticated
link. Developmental evidence needs a **local append-only evidence log** as the authority (never dropped), with the
outbox carrying batches/references, and a **persistent applied-id ledger** on the receiving side.

**Existing machinery to reuse** (not replace): `ConstraintGenealogyLogger._concurrency_lock` and its
`_last_observe_profile`; the non-blocking snapshot in `_select_active_abilities` (a stale perceptive frame, never a
stall); the afterthought daemon thread; the daemon's genealogy flush task (every ~5 min, `flush_files`);
`TurnComputeGraph` (per-turn only — must not own history); `persist_scope` (session vs canonical state); the
single-active-surface mechanism in the strata link.

## 4. Operations by purpose (deliverable 1)

Classes are the directive's §III list: 1 immediate experience · 2 activity/participation · 3 pressure/relief ·
4 representation-effect attribution · 5 ancestral relationships · 6 pair accumulation/promotion · 7 historical
reconstruction/explanation · 8 fitness/capability · 9 diagnostics · 10 persistence/sync.
"Evidence" says what the classification rests on; **"unverified"** means it follows the name/docstring and must be
traced in Stage 2 before anything moves (the directive forbids relocating on names).

| Operation (in `_observe_impl`) | Class | Writes read outside genealogy? | Needed by this turn? | Proposed owner | Evidence |
|---|---|---|---|---|---|
| `_apply_relief_tolerance` | 3 | no (private tolerance EMAs) | shapes the record's relief | stays with the event | AST; unverified effect on later events |
| `_record_activity` | 2 | no | no | evidence log → Subsurface | AST |
| `_is_relief_event` (noise filter) | 3 | n/a (pure) | yes (gates the rest) | stays | read |
| `_resolve_ability`, trace cost/risk accumulation | 4/8 | no | no | Subsurface | read; unverified |
| `_update_coupling_roots` | 5 | `_coupling_*`: `aurora_runtime.py`, `run_chain.py` only | no | Subsurface | AST + measured ~25 ms |
| `_update_gradient_memory(_from_relief)`, `_update_causal_feedback` | 3/4 | no | unverified | Subsurface after Stage 2 trace | AST, ~24 ms |
| `representation_collision_candidates` → `_record_representation_collisions` | 5/7 | `_representation_collisions`: analysis + runtime only | no (candidates for later inquiry) | Subsurface | AST + measured 1.26 s/8 turns |
| `representation_gap_candidates` → `_record_representation_inquiries` | 5/7 | same | no | Subsurface | AST + measured 0.65 s/8 turns |
| `_write_event` (JSONL), crystal back-stamp | 10 | – | no | persistence batching in Subsurface | read; measured ~0 ms |
| `_attribute_consequence` | 4 | writes `abilities`/`links` (**live selection reads these**) | unverified | **needs Stage 2 trace before any move** | AST; 0/78 calls changed them |
| `_accumulate_pairs` (+ promotion) | 6 | writes `links`, `abilities`, `links_promoted` | unverified | **needs Stage 2 trace** | AST; 0/78 calls promoted |
| `_check_pending_outcomes`, `_record_env_observation` | 3/9 | no | no | Subsurface | AST |
| complexity curve (`record_tick/outcome`) | 8 | unverified | unverified | Stage 2 trace | read |
| `flush_files` / persistence | 10 | – | no | Subsurface (already daemon-timed) | measured 466 ms inclusive, 27 calls |

## 5. Immediate versus deferred (deliverable 2) — proposed, not yet implemented

**Stays on the turn (immediate):** the relief calculation and noise filter (they decide whether the event is one);
whatever the live turn reads after the event — `abilities`/`links` and the profile fields selection uses — until a
projection serves those readers; an evidence record of the event (compact, append-only).

**Deferred to the Subsurface (candidates, in order of evidence):**
1. Collision and gap search (94% of `observe` cost; output is inquiry candidates; no live reader found).
2. Coupling roots, gradient/causal feedback, activity, env observation, pending-outcome checks (private or
   analysis-only writes; each must first show its result does not alter a later same-session decision).
3. Persistence batching (already largely on the daemon timer).

**Not to move on the strength of this stage:** pair accumulation/promotion and consequence attribution — they change
what live selection reads; they are cheap (~tens of ms), so there is little to gain and real risk.

**A first step that needs no relocation (preserves semantics exactly):** make `_representation_index` change-aware —
stamp on what actually changes the *index* (new/changed eligible ids, identity-dirty counter) instead of
`len(_pair_stats)`, maintain activity incrementally, and re-sort only touched buckets. "Compute once, distribute"
(§II.4). Its correctness is a one-line test: for the same state, the new index equals the old one. By F2 it removes
~95% of the collision search without moving anything out of the turn.

## 6. Decisions this evidence makes for Stage 2 (for Sir's confirmation before code)

1. Do the change-aware index first (pure optimisation, equivalence-tested), then re-measure — it may make deferral of
   the searches unnecessary for latency, though it will not make them *independent of turn timing*, which is the
   directive's goal.
2. Introduce a local append-only developmental evidence log (never drops, ordered, applied-id ledger) as the
   authority; reuse the strata outbox only as the transport. Do not reuse `DurableOutbox` unchanged (F7).
3. §IX: the selection pool must stop treating code-lineage records as operations, **without a hard-coded list**
   (§IX): the candidate criterion has to come from existing evidence (`ontological_status`, participation in
   `operation_lineage`, consequence profile). This is a separate change from the relocation and gets its own
   comparative test (§XII Stage 7) because it alters which abilities she can use.
4. QuasiArch access (Stage 5) comes after the record exists; it reads, never writes.

## 7. Limitations of this stage (not hidden)

- 8 turns, one script, in-process; `observe` call counts differ from Nov 11 because the script differs.
- The afterthought thread and the daemon flush task were not exercised; the "0 of 78 changed abilities" result is from
  a window with no promotion, so it supports — does not prove — that these writes are deferrable.
- Method-level timings wrap the functions (overhead; nested calls double-count). Runs 1–2 are unwrapped.
- The reader search is a grep: it can name a file that merely shares an attribute name.
- **Not done:** any cross-device (phone/laptop) test — §XII Stage 6 and deliverable 8 remain **incomplete**; no
  end-to-end developmental sequence (§XIII) exists yet; QuasiArch is untouched; no comparative developmental test.
- Not claimed: any efficiency improvement. This stage only measures.

## 8. Rollback

Nothing to roll back in behaviour: this branch adds two scripts and this document. Removing them restores the tree.
The scripts only read a *copy* of the state directory and delete their scratch copy when they end.

## 9. Reproduce

```
python3 scripts/audit_genealogy.py
python3 scripts/baseline_genealogy.py --state-dir <copy of aurora_state>
```
