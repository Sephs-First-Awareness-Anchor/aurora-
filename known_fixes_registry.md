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

<!-- FIX-A002 (Anomaly Ledger Consumer, PART A of the directive) to be appended
     when that part is implemented. -->
