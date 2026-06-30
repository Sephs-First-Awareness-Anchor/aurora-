# Aurora Known Fixes Registry
# Authors: Sunni (Sir) Morningstar & Cael Devo

A running record of verified bug/architecture fixes, so the same issue is not
re-diagnosed from scratch. Each entry: id, class, what was wrong, the fix, and
how it was verified.

---

## FIX-A001 (RUNTIME BUG) — EEPR shard-ingestion bridge never transferred a shard

**File:** `aurora_runtime.py`, `ChainSimBridge._forward_to_sim()`

**What was wrong (two stacked bugs on the same path):**

1. Line ~1489 read `ecology = getattr(getattr(perception, "ecology", None), None, None)`.
   The inner `getattr` returns the ecology object; the **outer** call then passes
   `None` as the attribute name. `getattr(obj, None, default)` raises
   `TypeError` (not `AttributeError`), so the 3-arg default does not catch it.
   The `TypeError` propagated to the method's outer `except Exception: pass` and
   was silently swallowed — the method returned before transferring any shard,
   every call. The "fallback" on the next lines was dead code (unreachable).

2. Once (1) is fixed and the method reaches its transfer loop, it calls
   `_clamp(...)` at lines ~1529/1559/1560/1561 — but `_clamp` was **never
   defined or imported** in `aurora_runtime.py`. It raised `NameError`, again
   swallowed by the same `except Exception: pass`. Bug (1) had always killed the
   method before this line, so the missing helper was never observed. Fixing (1)
   surfaced it.

Net effect: zero `WisdomShard`s ever transferred from the simulation learner to
`ExpressionEcology.WisdomStore` since the method was written.

**The fix:**
- `ecology = getattr(perception, "ecology", None)` (single, correct getattr;
  removed the dead fallback).
- Added the canonical module-level helper
  `def _clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))`
  (identical to the one defined in 9 other modules; the method already assumed
  it existed).

**Verified:** driving `_forward_to_sim` with a confident mock shard now calls
`wisdom_store.add(...)` exactly once (`ws_<id>`), advances
`learner.total_observations`, and is idempotent across calls (dedup via
`_transferred_shard_ids`). Previously: 0 transfers.

**Also (improvement-on-top):** `corpus_runner.py` plateau detector
(`CURRICULUM_STALL`) now confesses the stall to WarpField via
`warp_guard(TENSION, persistence_key="curriculum_stall")` instead of only
logging + resetting — a corpus novelty plateau is a genuine unresolved tension.

---

## FIX-A002 (ARCHITECTURAL) — WarpField anomaly ledger had no consumer

**Files:** `aurora_warp_protocol.py`, `aurora_curiosity_engine.py`

**What was wrong:** `WarpField._anomaly_ledger` accumulates every demand
classified as `WarpPathway.ANOMALY` (severity >= 0.90 with a persistence_key —
a high-severity *recurring* unresolved state). It was written and surfaced only
as a count in `status()`; nothing read or drained it. Demands routed to ANOMALY
were therefore permanently silenced after classification — recognized, then
forgotten. (Distinct from `WarpGenerator._anomaly_log`, the coverage-gap signal,
which the curiosity engine already consumes.)

**The fix:**
- `WarpField.anomaly_ledger_summary()` — non-destructive read, collapses entries
  by persistence_key (count + max severity), ranked by (count, severity).
- `WarpField.drain_anomaly_ledger(keep_recent=50)` — destructive epoch-level
  compaction.
- `CuriosityEngine._step1_emergence` now consumes the ledger as a third
  WARP-aware emergence source (between the WarpGenerator structural-gap
  candidates and the crystal gap report): a demand that recurred >= 2 times
  becomes a `CuriosityObject` ("recurring unresolved demand: …") so Aurora
  investigates whether it reflects a genuine missing primitive or a handler
  registration gap.

**Verified:** `anomaly_ledger_summary()` returns `[]` when empty; two ANOMALY
demands sharing a persistence_key collapse to one entry with `count == 2`;
`drain` removes correctly; the consumer builds a CuriosityObject whose subject
begins with "recurring unresolved demand:". This pairs with the warp-confession
wiring — the ledger now accumulates real demands to consume.

---

## FIX-A003 (RUNTIME BUG, class-wide) — undefined names in swallowed code paths

A pyflakes F821 sweep surfaced the same class of bug as FIX-A001's `_clamp`:
a name used in a code path that never raised because something upstream failed
first (or the path is rarely hit), with the `NameError` absorbed by a
surrounding `except Exception`. Triaged to names never bound anywhere in their
file. Fixed the safe, verifiable ones:

- `aurora_runtime.py`: `Set` missing from the typing import (used in
  `_forward_to_sim` annotations).
- `aurora_daemon.py`: `_log_error(...)` called 3× but never defined → switched
  to the module's existing `_log(...)`.
- `aurora_working_memory.py`: `SimpleNamespace` (killed the `perception.express`
  branch of `_render_from_comprehension_intent`), `_merge_native_meaning_bundle`,
  `ConversationMemory` — added imports (no circular import; turn battery
  unchanged).
- `aurora_manifold_directory_reader.py`: `Any` missing from typing.
- `aurora_hub.py`: `_DAEMON_STATUS` constant missing for a status panel.
- `aurora_autonomy.py`: `subprocess` / `sys` never imported, so
  `run_training_tool` silently failed on every call — Aurora could never launch
  her own whitelisted training tools. Added the imports and updated the
  (outdated) doctrine text to reflect that she may launch the whitelisted
  TRAINING_TOOLS as subprocesses.
- `aurora_hardware_io.py`: `_extract_rich_audio_features` (defined in
  aurora_expression_perception) was never imported, so the audio feature
  extraction in the hardware paths silently failed. Added the import (verified
  no circular import).

**Still open (need a decision, not a blind patch):**
- `aurora_working_memory.py:3222` — `state` referenced in the grammar-suggestion
  block but not in scope (guarded; just skips grammar). Needs intended source.
- `aurora_working_memory.py` — `_classify_input_intent`, `_is_understanding_challenge`,
  `_meaning_profile_for_value`, `_log_claim_resolution_relief` are defined in
  `aurora.py`, which imports working_memory → importing back is circular. Needs
  the helpers moved to a shared module.
- `aurora_daemon.py:195` — `_surface_channel_recently_active` is defined nowhere;
  needs implementing or the call removed.
- `aurora_hardware_io.py` — the `_ConstraintVector`/`_GovernorWeights`/`_FC`/
  `_ExistenceMode` cluster (in the dormant `constraint_profile` / governor /
  `language_projection` hardware methods). `_ConstraintVector` and
  `_GovernorWeights` map cleanly to `aurora_constraint_engine`, but `_FC` /
  `_ExistenceMode` are ambiguous: `_FC.language_projection(_ExistenceMode.AGENTIC)`
  implies `_FC` is an *instance* (the method is `language_projection(self, mode)`),
  and `AGENTIC` lives on `foundational_contract.ExistenceMode` while
  `language_projection` lives on `aurora_constraint_engine.FoundationalContract`
  — i.e. two different ExistenceMode enums. Needs the author's confirmation of
  the original import intent; not safe to reconstruct blind.


---

## FIX-A005 (ARCHITECTURAL) — Signal-Through Field Wiring (Warp ↔ SediMemory ↔ ContradictionLedger)

Implemented the Signal-Through Field Propagation directive (2026-06-30): Warp's
discovery/synthesis output now carves paths in the SediMemory erosion substrate,
and real per-turn contradiction detection now reaches ContradictionLedger whose
heat dampens Warp trial promotion (with resolution wired so heat can fall again).

- aurora_warp_protocol.py (WarpCapable mixin): `_sediment_warp_traversal()` (deposits
  warp_gap_closed / warp_trial_promoted into SediMemory via ingest_event), called
  from check_and_extend and the evaluate_warp_trials promotion branch;
  `connect_sedimemory` / `connect_contradiction_ledger` on the mixin;
  `_init_warp` now seeds `_sedimemory` / `_contradiction_ledger`; heat dampening
  (`score *= max(0, 1 - heat)`) in evaluate_warp_trials.
- `_sedimemory = None` added to ThoughtBraid / ExpressionPerceptionEngine /
  LanguageField __init__.
- aurora.py: ContradictionLedger instantiated; perception / language_field /
  dimensional / working_memory wired at boot.
- aurora_braid_wiring.py: thought braid wired.
- aurora_working_memory.py: `connect_contradiction_ledger`, ledger.record() in
  `_register_claim_conflict` (captures contradiction_id), ledger.resolve() in
  refresh_claim_conflicts on removed pairs.

Deviation from the literal directive (made to fulfil its intent): a SECOND
WorkingMemory() construction (aurora.py ~20422) replaced the wired instance, so
the live WM was unwired. Added a re-assert of connect_contradiction_ledger on the
FINAL working_memory instance. Verified WM-to-ledger now binds.

FLAGGED, not improvised (per the directive's standing rule): the `dimensional`
aggregate is NOT itself WarpCapable — `CrystalProcessingSystem` (`dimensional.dps`)
is. `DimensionalSystems.connect_sedimemory` forwards to `self.dps._sedimemory`
(so warp traversal deposits work for dps), but there is no parallel
`connect_contradiction_ledger` forwarder, so `hasattr(dimensional,
'connect_contradiction_ledger')` is False and dps's warp trials are NOT
heat-dampened. The other three hosts (perception, language_field, braid) are wired
directly and are dampened. Mirroring the connect_sedimemory forwarder onto
DimensionalSystems would close it, but that wasn't in the directive — flagging
rather than adding.

Verified: all boot wiring lines print; contradiction record increments
unresolved_count and captures contradiction_id; warp traversal increments
total_events_ingested and registers a PathRegistry observation; heat dampening
drops trial EMA 0.30->0.06; resolution decrements unresolved_count. No turn-battery
regression.
