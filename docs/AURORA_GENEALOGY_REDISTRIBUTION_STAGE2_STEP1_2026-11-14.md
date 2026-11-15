# Genealogy redistribution — Stage 2, step 1: corrected instruments and the change-aware index

**Authors:** Sunni (Sir) Morningstar & Cael Devo
**Date:** 2026-11-14 · **Branch:** `ceph/genealogy-redistribution-stage1-20261114` (PR #252)
**Status:** measured. Nothing is deferred or relocated. No efficiency claim beyond the numbers below.

The Stage 1 report (`AURORA_GENEALOGY_REDISTRIBUTION_STAGE1_2026-11-14.md`) is kept exactly as it was, as the
history of what was measured and believed at that point. This document corrects it where the corrected
instruments disagree, says which Stage 1 statements stand, and records the first change.

## 1. What was wrong with the Stage 1 instruments

| Defect | Found by | Effect | Fixed |
|---|---|---|---|
| A read made *before* an observe in the same turn was counted as made *after* it (the turn's final call count was compared, not the revision at the read) | PR #252 review | the ordering evidence used to judge "safe to defer" was unreliable | `reads_after_same_turn_observe` compares the revision at the read with the revision at the turn's start |
| A collision-record-only change was counted as a change to abilities or links | PR #252 review | "what live code reads changed" was overstated | collisions are reported apart from abilities / links / promoted links |
| **State change was measured by size** (`len`) | re-audit | **an in-place change to a record was invisible** | diff mode compares each record's content and names the fields that changed |
| Timing and state-diffing shared a run, and method timers were always on | re-audit | wrapper overhead inflated the timings | three modes: `timing` (observe wrapped only), `diff`, `methods`; cost is quoted from `timing` only |
| Readers of genealogy state were found with `grep '\.attr'` | re-audit | same-named attributes of other classes matched; `getattr(x, "attr")` and reads through the logger's public methods were missed; `aurora_runtime.py` was not named | `scripts/audit_genealogy.py` walks every module's syntax tree and reports file:line with the receiver, classed *named* (the receiver says genealogy) or *unconfirmed* (same name, receiver unclear) |

Pinned by `tests/test_baseline_genealogy.py` (12 tests, including both review cases).

## 2. Stage 1 statements: what stands, what is withdrawn

| Stage 1 statement | Now |
|---|---|
| "`observe` is 22–28% of an 8-turn script" | **Stands.** Corrected instrument, three runs: 21.8%, 22.8%, 27.2% of total turn time. Wrapper overhead did not explain it. |
| "0 ms lock wait; all 78 calls on the turn thread" | **Stands.** Lock wait 0.0–0.1 ms; every call on the turn thread. |
| "0 of 78 observe calls changed the number of abilities or links, which supports deferral" | **Withdrawn. This was a measurement artifact.** Counted by content, **45–47 of 81 calls change what live code reads.** The only field that changes is `consequence_profile`: 6 record-changes on abilities and 83–85 on links (the pair-and-consequence stage; ~6 ms of the call). Collision records are added separately (42 in the window). The live ability pool is therefore *not* untouched by `observe`; that part must stay immediate or be replaced by a provisional value plus a deferred consolidation (directive §IV). |
| "95% of the collision search is the index being rebuilt on 46 of 47 calls" | **Corrected.** About 550–650 ms of the ~1,300 ms is **one** cold full build (first observe in a process, 13,775 ids); the other 46 calls cost ~17 ms each in-turn (9 ms in isolation: 64% sorting every bucket, 18% recomputing activity, 11% building the id set). |
| "96.1% of the live pool and 38 of 40 selections are code-lineage" | **Stands** (re-measured: 12,885 of 13,405; 38 of 40). Not changed here. |

## 3. The change

`ConstraintGenealogyLogger._representation_index` re-sorted every bucket (13,734 key evaluations over 129 buckets
per call on the full profile) whenever its stamp moved, which is nearly every observe. A bucket's order is a pure
function of its members' `(last tick, count)` and their ids, so a bucket needs sorting only if a member was added
or a member's activity changed. The index now remembers the activity and bucket of every id from the last build,
finds the ids whose activity moved, and re-sorts only their buckets. A bucket it must change is copied first, so a
failure mid-build cannot leave the cached index half-edited. The full-rebuild triggers are unchanged (identity
change, a count that went down, no cache).

`_representation_observed_and_activity()` is the old inline scan, extracted so the index and the test oracle share
it. `_representation_index_profile` records `{mode, scanned, buckets, resorted}` for the last build.

### Proof that nothing else changed

* **Oracle:** the index built from nothing for the state as it stands. `tests/test_representation_index_change_aware.py`
  keeps the previous implementation verbatim as the comparison baseline and, after every step of a mixed sequence
  (growth, activity moved for already-indexed ids, new ids, a link count moved, an identity change), checks that the
  new index, the previous index and the oracle agree (10 tests).
* **The tests can fail:** two mutants of the change detector (never re-sort a changed bucket; re-sort only one)
  fail 5 of the 10 tests each. An earlier draft of the tests did *not* detect the first mutant (its states had no
  bucket with two active members, so no order could move); it was rewritten to use the genealogy's own seed
  abilities and to assert that the sequence actually moved an order.
* **Live state:** diff mode compares the live index with a from-scratch rebuild after every observe call on the real
  13,406-ability profile: **81 checked, 0 differ.** The collision records added (42) and the fields changed
  (`consequence_profile` only) are the same as before the change.
* Existing genealogy and representation tests: 536 pass; the 15 that fail also fail on the unmodified genealogy
  (the 4 `afterthought_topic_identity` tests and 11 in `test_representational_resolution_build714`,
  `test_no_representational_selection_learning` and `test_cross_generational_representational_recombination`).

## 4. Re-measurement (same state, 8 turns, three runs each, nothing else running)

| | before | after |
|---|---|---|
| observe on the turn thread, whole window (ms) | 2845 · 2239 · 2134 | 1930 · 2143 · 1973 |
| observe, steady-state turns 3–8 (ms) | 1296 · 1171 · 1158 | 931 · 1040 · 952 |
| observe as a share of steady-state turn time | 23.0% · 20.5% · 21.6% | 15.6% · 16.2% · 18.2% |
| observe on the cold turn 2 (ms) | 1548 · 1067 · 976 | 999 · 1103 · 1020 |
| collision search stage (ms) | 1875 · 1423 · 1344 | 1051 · 1152 · 1067 |
| gap search stage (ms) | 818 · 680 · 658 | 739 · 819 · 745 |
| **total turn time, 8 turns (ms)** | **10445 · 10277 · 9346** | **10863 · 10999 · 10158** |

What this says, and does not say:

* The change removed roughly 20% of steady-state observe time (~35 ms per turn, ~3 ms per call).
* **Total turn time did not improve measurably.** It is within run-to-run noise (±8%) and in this sample moved the
  wrong way. The saving is real but small next to the other ~80% of a turn, and I make no responsiveness claim.
* The cold full build (~600 ms once per process) is untouched.
* Of what remains in `observe`, collision search (~54%, including the cold build) and gap search (~38%) are ~92%;
  coupling, gradient, pair accumulation, consequence attribution and the curve together are ~40 ms.

## 5. Which operations may be deferred — evidence so far, no decision

| Operation | Share of observe | What it writes | Read by live code? |
|---|---|---|---|
| Consequence attribution / pair accumulation | <1% (6 ms) | `consequence_profile` on abilities and links, `_pair_stats`, `_links_by_parents`, promotion | **Yes** — changes live-read records in 56–58% of calls (45–47 of 81). Keep immediate (or provisional + deferred consolidation). |
| Collision search + record | ~54% | `_representation_collisions` | Not by `_select_active_abilities`. Read by reporting (`chain_report`, `summary`), analysis scripts, and `stage_representation_inquiry` (resolution layer). **Open:** whether staging runs inside a live turn. |
| Gap search + record | ~38% | inquiry records | Same consumers as above. |

The two searches are the candidates. Two things must be established before moving them, and are the next work:
(a) trace whether the resolution layer reads their records during a live turn (the audit finds the consumers by name
but cannot say when they run), and (b) check that the resolution layer, which also calls
`representation_collision_candidates` / `representation_gap_candidates` itself
(`aurora_representational_resolution(_base).py`), would see the same candidates from an environment-computed result.

`aurora_runtime.py` (named in Stage 1 as untraced): its reads are in the console and simulation harness
(`status`, `chain_burst`, `sim_speed_run`, `mode_*`, `_on_epoch`), `inject_promoted_links`, `tick`,
`stance_snapshot`, `emergent_trait_cards` and `_dispatch`. `aurora.py` imports only `_restore_genealogy_state` and
`ChainSimBridge` from it, at boot; the phone bridge does not import it. I found no call from the live-turn path to
those readers. That is a finding from the syntax tree, not proof: it cannot see a reader reached through a variable
assigned from genealogy and passed through several calls.

## 6. Limitations

* One state, one 8-turn script, three runs per condition; a cold turn is part of every window. The machine's
  run-to-run spread (±8% of turn time) is larger than the effect on total turn time.
* Diff mode fingerprints 13k records per call (about 80 s per run); its timings are not costs.
* Audit matches by attribute and method *name*: `close`, `summary`, `observe` collide with other classes' methods.
  Only *named* receivers are counted as consumers above; *unconfirmed* ones need a hand read.
* Nothing was run on the phone or across devices; there is no end-to-end developmental sequence, no QuasiArch work,
  no comparative developmental testing. Nothing here is marked complete beyond what section 3 proves.

## 7. Rollback

Revert the change to `_representation_index` (the previous body is preserved verbatim in
`tests/test_representation_index_change_aware.py::_legacy_index`); the new state fields are additive and ignored by
the old code. The instruments are scripts and tests only.

## 8. Reproduce

```
python3 scripts/baseline_genealogy.py --mode timing      # cost (run alone, three times)
python3 scripts/baseline_genealogy.py --mode diff        # what observe changes, by content; index vs full rebuild
python3 scripts/baseline_genealogy.py --mode methods     # where the time goes (timers add overhead)
python3 scripts/audit_genealogy.py [--json]              # readers by syntax tree
python3 -m pytest tests/test_baseline_genealogy.py tests/test_representation_index_change_aware.py
```
