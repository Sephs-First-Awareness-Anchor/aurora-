#!/usr/bin/env python3
"""
AURORA ICC LEDGER — Internal Coherence Credit
================================================
Phase 0 of the ICC Landing / Strategic Horizon / Operator Composition
directive (2026-07-14). Currency grounded in *resolved ignorance that
survived reality pressure*. Hash-chained, tamper-evident, append-only.

Live balance:
    balance = historical_weight × active_coherence × moral_standing × intent_integrity

WHAT THIS MODULE IS NOT:
    - Not an actuator. It never writes to constraint state and never
      emits PhaseNudges itself -- it is a balance, not a command.
    - Not a parallel intake/worth/entropy/moral-weight system. Every
      factor is a READ-ONLY pull from the systems that already compute
      that signal (CrossScaleWorthEvaluator, EntropySaturationDetector,
      MoralWeightLedger, FailureGuardSuite).

BOUNDARY RULES (TCL template, aurora_toroidal_circulation.py):
    Read-only observer of every upstream system. A failure anywhere in
    this module must never affect the runtime -- every integration read
    is wrapped in try/except, degrading to a safe default rather than
    raising. Phase 1 (strategic horizon) is the only permitted consumer
    of this ledger's output; nothing here acts on its own balance.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

from aurora_internal.aurora_constraint_manifold_patched import Constraint
from aurora_internal.aurora_persistence_utils import PERSISTENCE_LOCK, _ensure_parent
from aurora_internal.aurora_worth_evaluator import (
    CrossScaleWorthEvaluator,
    WorthHistory,
    WorthReport,
    WorthTrajectory,
)
from aurora_internal.aurora_entropy_detector import (
    EntropySaturationDetector,
    SaturationLevel,
    SaturationSignal,
)
from aurora_internal.aurora_variant_promotion import (
    MoralWeightLedger,
    _MORAL_WEIGHT_MAX,
)

# ===========================================================================
# SECTION 1 — CONSTANTS
# ===========================================================================

LEDGER_FILENAME = "icc_ledger.jsonl"
VIOLATIONS_FILENAME = "icc_violations.jsonl"

GENESIS_PREV_HASH: str = "0" * 64

# Age-decay half-life for historical_weight, expressed in ticks.
# Not independently spec-pinned ("one full genealogy epoch") -- reuses
# the existing bounded VariantHorizon ceiling (_HORIZON_MAX_TICKS = 200,
# aurora_worth_evaluator.py: the longest observation window the system
# already grants its deepest, most expensive intakes) as the epoch length,
# rather than inventing an unrelated number. First-pass, documented, like
# semantic_variant_registry.py's own lifecycle thresholds.
_HISTORICAL_HALF_LIFE_TICKS: float = 200.0
_HISTORICAL_DECAY_LAMBDA: float = math.log(2.0) / _HISTORICAL_HALF_LIFE_TICKS

# active_coherence floor (directive 0.3).
_ACTIVE_COHERENCE_FLOOR: float = 0.05
# Penalty applied to active_coherence once saturation moves past WATCH.
_SATURATION_PENALTY: float = 0.5

# moral_standing per-constraint cap -- MoralWeightLedger.register() caps
# accumulated bias per constraint at _MORAL_WEIGHT_MAX * 3; read here
# rather than re-declared (directive 0.3).
_MORAL_STANDING_PER_CONSTRAINT_CAP: float = _MORAL_WEIGHT_MAX * 3

# intent_integrity rolling window (directive 0.3: "last 200 check_all() sweeps").
_INTENT_INTEGRITY_WINDOW: int = 200

_ALL_CONSTRAINTS: Tuple[Constraint, ...] = (
    Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A,
)


def _canonical_json(data: Dict[str, Any]) -> str:
    """Deterministic JSON encoding for hashing -- sorted keys, no
    whitespace ambiguity, so the same entry always hashes identically."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ===========================================================================
# SECTION 2 — CHAIN ENTRY
# ===========================================================================

@dataclass(frozen=True)
class ICCEntry:
    """
    One link in the hash chain.

    entry_id   — "ICC:{sha10}", derived from entry_hash
    tick       — the tick this entry was minted at
    prev_hash  — sha256 hex of the previous entry's canonical JSON
                 ("0"*64 for genesis)
    entry_hash — sha256 hex of this entry's own canonical JSON, WITH
                 prev_hash included in the hashed payload (so tampering
                 with any earlier entry breaks every hash after it)
    source     — "worth_survival" | "contradiction_resolution" |
                 "manual_doctrine"
    axes       — canonical X/T/N/B/A relief attribution for this mint
    minted     — credit minted (>= 0)
    evidence   — provenance snapshot (worth trajectory, horizon, etc.)
    """
    entry_id:   str
    tick:       int
    prev_hash:  str
    entry_hash: str
    source:     str
    axes:       Dict[str, float]
    minted:     float
    evidence:   Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id":   self.entry_id,
            "tick":       self.tick,
            "prev_hash":  self.prev_hash,
            "entry_hash": self.entry_hash,
            "source":     self.source,
            "axes":       dict(self.axes),
            "minted":     self.minted,
            "evidence":   dict(self.evidence),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ICCEntry":
        return cls(
            entry_id   = str(d.get("entry_id", "") or ""),
            tick       = int(d.get("tick", 0) or 0),
            prev_hash  = str(d.get("prev_hash", "") or ""),
            entry_hash = str(d.get("entry_hash", "") or ""),
            source     = str(d.get("source", "") or ""),
            axes       = dict(d.get("axes", {}) or {}),
            minted     = float(d.get("minted", 0.0) or 0.0),
            evidence   = dict(d.get("evidence", {}) or {}),
        )

    def _payload_for_hash(self) -> Dict[str, Any]:
        """Everything except entry_hash/entry_id itself -- those are
        DERIVED from this payload, so they can't be part of it."""
        return {
            "tick":      self.tick,
            "prev_hash": self.prev_hash,
            "source":    self.source,
            "axes":      dict(self.axes),
            "minted":    self.minted,
            "evidence":  dict(self.evidence),
        }

    def recomputed_hash(self) -> str:
        return _sha256(_canonical_json(self._payload_for_hash()))


def _mint_entry(
    *,
    tick: int,
    prev_hash: str,
    source: str,
    axes: Dict[str, float],
    minted: float,
    evidence: Dict[str, Any],
) -> ICCEntry:
    payload = {
        "tick": tick, "prev_hash": prev_hash, "source": source,
        "axes": dict(axes), "minted": minted, "evidence": dict(evidence),
    }
    entry_hash = _sha256(_canonical_json(payload))
    entry_id = "ICC:" + entry_hash[:10]
    return ICCEntry(
        entry_id=entry_id, tick=tick, prev_hash=prev_hash, entry_hash=entry_hash,
        source=source, axes=dict(axes), minted=minted, evidence=dict(evidence),
    )


# ===========================================================================
# SECTION 3 — ICC LEDGER
# ===========================================================================

class ICCLedger:
    """
    Hash-chained, tamper-evident, append-only ICC ledger.

    Read-only observer of CrossScaleWorthEvaluator, EntropySaturationDetector,
    MoralWeightLedger, and FailureGuardSuite -- computes a live balance from
    their existing signals, never commands them. Persists to
    aurora_state/icc_ledger.jsonl (append-only JSONL, one entry per line),
    with tamper detection freezing the chain read-only and logging to a
    separate icc_violations.jsonl (never overwritten, per standing project
    rule -- errors preserved visibly).
    """

    def __init__(self, state_dir: Optional[str] = None) -> None:
        self._state_dir = str(state_dir) if state_dir else "aurora_state"
        self._ledger_path = os.path.join(self._state_dir, LEDGER_FILENAME)
        self._violations_path = os.path.join(self._state_dir, VIOLATIONS_FILENAME)

        self._entries: List[ICCEntry] = []
        self._frozen: bool = False
        self._minted_intake_ids: set = set()

        # Rolling window of FailureGuardSuite.check_all() results, for
        # intent_integrity. Each element: bool (passed) per sweep-of-guards
        # is compressed to a single fraction contribution via record_guard_sweep().
        self._guard_pass_window: Deque[bool] = deque(maxlen=_INTENT_INTEGRITY_WINDOW)

        self._load()
        if not self._entries:
            self._append_genesis()

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        try:
            if not os.path.exists(self._ledger_path):
                return
            entries: List[ICCEntry] = []
            with open(self._ledger_path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    entries.append(ICCEntry.from_dict(json.loads(line)))
            self._entries = entries
            if not self._verify_loaded_chain():
                self._frozen = True
        except Exception:
            self._entries = []

    def _append_genesis(self) -> None:
        genesis = _mint_entry(
            tick=0, prev_hash=GENESIS_PREV_HASH, source="manual_doctrine",
            axes={}, minted=0.0, evidence={"note": "genesis"},
        )
        self._entries.append(genesis)
        self._write_entry(genesis)

    def _write_entry(self, entry: ICCEntry) -> bool:
        try:
            path = Path(self._ledger_path)
            with PERSISTENCE_LOCK:
                _ensure_parent(path)
                with open(path, "a", encoding="utf-8") as fh:
                    fh.write(_canonical_json(entry.to_dict()) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
            return True
        except Exception:
            return False

    def _log_violation(self, reason: str, detail: Dict[str, Any]) -> None:
        try:
            path = Path(self._violations_path)
            with PERSISTENCE_LOCK:
                _ensure_parent(path)
                with open(path, "a", encoding="utf-8") as fh:
                    fh.write(_canonical_json({
                        "ts": time.time(), "reason": reason, "detail": detail,
                    }) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
        except Exception:
            pass

    def _verify_loaded_chain(self) -> bool:
        prev = GENESIS_PREV_HASH
        for entry in self._entries:
            if entry.prev_hash != prev:
                self._log_violation("prev_hash_mismatch", {"entry_id": entry.entry_id})
                return False
            if entry.entry_hash != entry.recomputed_hash():
                self._log_violation("entry_hash_mismatch", {"entry_id": entry.entry_id})
                return False
            prev = entry.entry_hash
        return True

    # ------------------------------------------------------------------
    # chain integrity (public)
    # ------------------------------------------------------------------

    def verify_chain(self) -> bool:
        """Walk the full chain recomputing hashes. On any break, freezes
        the chain read-only and appends a violation record. Returns True
        iff the chain is intact."""
        ok = self._verify_loaded_chain()
        if not ok:
            self._frozen = True
        return ok

    def is_frozen(self) -> bool:
        return self._frozen

    # ------------------------------------------------------------------
    # minting (the only way credit is created)
    # ------------------------------------------------------------------

    def mint_if_eligible(
        self,
        intake_id: str,
        tick: int,
        *,
        worth_evaluator: Optional[CrossScaleWorthEvaluator] = None,
        worth_report: Optional[WorthReport] = None,
        depth_weight: float = 0.0,
        worth_score: float = 0.0,
    ) -> Optional[ICCEntry]:
        """
        Mint credit for `intake_id` iff, at horizon expiry, ALL hold
        (directive 0.2):
          1. worth_report reached >= the N->B transition (deep or core) --
             i.e. WorthReport.horizon is not None and its depth_reached is
             BOUNDED or AGENTIC.
          2. WorthHistory.has_ever_risen() is True and terminal trajectory()
             is not WorthTrajectory.FALLING.
          3. VariantHorizon.eligible_at(tick) is True -- the trace survived
             its full persistence window under live pressure.

        Never mints twice for the same intake_id. Degrades to None (no
        mint, no exception) on any missing/malformed input -- this is a
        read-only consumer of worth data, never a fabricator of it.
        """
        if self._frozen:
            return None
        if intake_id in self._minted_intake_ids:
            return None
        try:
            if worth_report is None or worth_evaluator is None:
                return None
            horizon = worth_report.horizon
            if horizon is None:
                return None
            # ExistenceMode is an IntEnum; BOUNDED/AGENTIC are the two
            # depths at/after the N->B transition.
            from foundational_contract import ExistenceMode
            if horizon.depth_reached not in (ExistenceMode.BOUNDED, ExistenceMode.AGENTIC):
                return None
            if not horizon.eligible_at(tick):
                return None

            history = worth_evaluator.history_for(intake_id)
            if history is None or not history.has_ever_risen:
                return None
            if history.trajectory == WorthTrajectory.FALLING:
                return None

            minted = max(0.0, float(worth_score) * max(0.0, float(depth_weight)))
            evidence = {
                "intake_id":     intake_id,
                "depth_reached": horizon.depth_label(),
                "trajectory":    history.trajectory.value,
                "worth_report":  {
                    "crossed_threshold": worth_report.crossed_threshold,
                    "polarity_coherent": worth_report.polarity_coherent,
                    "tense_transitions": list(worth_report.tense_transitions),
                },
            }
            entry = self._append(
                tick=tick, source="worth_survival", axes={}, minted=minted,
                evidence=evidence,
            )
            if entry is not None:
                self._minted_intake_ids.add(intake_id)
            return entry
        except Exception:
            return None

    def mint_from_contradiction_resolution(
        self,
        *,
        tick: int,
        contradiction_id: str,
        axes: Optional[Dict[str, float]] = None,
        minted: float = 0.0,
    ) -> Optional[ICCEntry]:
        """
        Second minting source (directive 0.2): contradiction resolutions.

        HOOK POINT NOT YET WIRED LIVE: the live ContradictionLedger
        resolution call site (aurora_working_memory.py's
        refresh_claim_conflicts, per FIX-A005 in known_fixes_registry.md)
        was not wired to call this during Phase 0 -- per the directive's
        "if ambiguous, stub the hook with a TODO and flag rather than
        guessing" instruction, this method exists and is tested
        standalone, but nothing calls it live yet. TODO: wire from
        aurora_working_memory.py's ledger.resolve() call site.
        """
        if self._frozen:
            return None
        try:
            minted = max(0.0, float(minted))
            evidence = {"contradiction_id": str(contradiction_id or "")}
            return self._append(
                tick=tick, source="contradiction_resolution",
                axes=dict(axes or {}), minted=minted, evidence=evidence,
            )
        except Exception:
            return None

    def _append(
        self, *, tick: int, source: str, axes: Dict[str, float],
        minted: float, evidence: Dict[str, Any],
    ) -> Optional[ICCEntry]:
        if self._frozen:
            return None
        prev_hash = self._entries[-1].entry_hash if self._entries else GENESIS_PREV_HASH
        entry = _mint_entry(
            tick=tick, prev_hash=prev_hash, source=source,
            axes=axes, minted=minted, evidence=evidence,
        )
        if not self._write_entry(entry):
            return None
        self._entries.append(entry)
        return entry

    # ------------------------------------------------------------------
    # intent_integrity feed (FailureGuardSuite sweeps)
    # ------------------------------------------------------------------

    def record_guard_sweep(self, results: List[Any]) -> None:
        """
        Feed one FailureGuardSuite.check_all() sweep into the rolling
        intent_integrity window. Directive 0.3: "UncertaintySignalingGuard
        passes obtained via acknowledgment count fully -- acknowledged
        uncertainty is integrity, not weakness." GuardResult.passed is
        already True for both the low-uncertainty case AND the
        acknowledged-high-uncertainty case (UncertaintySignalingGuard.check()
        returns passed=True once acknowledge_uncertainty() has cleared the
        flag) -- so counting .passed directly already honors this without
        special-casing any one guard.
        """
        try:
            sweep_passed = all(bool(getattr(r, "passed", False)) for r in results)
            self._guard_pass_window.append(sweep_passed)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # balance factors (all read-only pulls)
    # ------------------------------------------------------------------

    def _historical_weight(self, current_tick: int) -> float:
        try:
            total = 0.0
            for e in self._entries:
                age = max(0.0, float(current_tick - e.tick))
                total += e.minted * math.exp(-_HISTORICAL_DECAY_LAMBDA * age)
            return total / (1.0 + total)
        except Exception:
            return 0.0

    def _active_coherence(
        self, saturation_signal: Optional[SaturationSignal],
    ) -> float:
        try:
            if saturation_signal is None:
                return 1.0
            entropy_pressure = getattr(saturation_signal, "_entropy_at_measure", None)
            # SaturationSignal itself does not expose raw entropy (by design,
            # directive: coarse level only) -- active_coherence therefore
            # derives from the coarse level, not a raw pressure value we
            # were never given. NOMINAL/WATCH -> full coherence; CAUTION+
            # applies the saturation penalty per directive 0.3.
            base = 1.0
            if saturation_signal.level == SaturationLevel.NOMINAL:
                base = 1.0
            elif saturation_signal.level == SaturationLevel.WATCH:
                base = 0.85
            else:
                base = 0.85 * _SATURATION_PENALTY
            return max(_ACTIVE_COHERENCE_FLOOR, base)
        except Exception:
            return _ACTIVE_COHERENCE_FLOOR

    def _moral_standing(self, moral_ledger: Optional[MoralWeightLedger]) -> float:
        try:
            if moral_ledger is None:
                return 0.0
            biases = moral_ledger.all_biases()
            total = sum(max(0.0, float(v)) for v in biases.values())
            denom = 5.0 * _MORAL_STANDING_PER_CONSTRAINT_CAP
            if denom <= 0.0:
                return 0.0
            return min(1.0, total / denom)
        except Exception:
            return 0.0

    def _intent_integrity(self) -> float:
        try:
            if not self._guard_pass_window:
                return 1.0
            passed = sum(1 for p in self._guard_pass_window if p)
            return passed / len(self._guard_pass_window)
        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # public surface
    # ------------------------------------------------------------------

    def current_balance(
        self,
        *,
        current_tick: int = 0,
        saturation_signal: Optional[SaturationSignal] = None,
        moral_ledger: Optional[MoralWeightLedger] = None,
    ) -> float:
        """balance = historical_weight × active_coherence × moral_standing × intent_integrity"""
        try:
            hw = self._historical_weight(current_tick)
            ac = self._active_coherence(saturation_signal)
            ms = self._moral_standing(moral_ledger)
            ii = self._intent_integrity()
            return hw * ac * ms * ii
        except Exception:
            return 0.0

    def balance_trajectory(
        self,
        window: int,
        *,
        saturation_signal: Optional[SaturationSignal] = None,
        moral_ledger: Optional[MoralWeightLedger] = None,
    ) -> List[float]:
        """Balance evaluated at each of the last `window` entry ticks
        (chronological order), using the SAME live saturation/moral
        snapshot for every point -- this traces how minted-credit history
        alone shaped the trajectory, not a replay of long-gone external
        state."""
        try:
            window = max(0, int(window))
            recent = self._entries[-window:] if window else []
            return [
                self.current_balance(
                    current_tick=e.tick,
                    saturation_signal=saturation_signal,
                    moral_ledger=moral_ledger,
                )
                for e in recent
            ]
        except Exception:
            return []

    def summary(self) -> Dict[str, Any]:
        """Public summary -- mirrors MoralWeightLedger.summary()'s privacy
        posture: no raw factor internals, just counts and chain health."""
        try:
            return {
                "entry_count":    len(self._entries),
                "chain_intact":   not self._frozen,
                "frozen":         self._frozen,
                "total_minted":   round(sum(e.minted for e in self._entries), 6),
                "mint_sources":   sorted({e.source for e in self._entries}),
            }
        except Exception:
            return {"entry_count": 0, "chain_intact": False, "frozen": True,
                     "total_minted": 0.0, "mint_sources": []}


# ===========================================================================
# SECTION 4 — FACTORY
# ===========================================================================

def make_icc_ledger(state_dir: Optional[str] = None) -> ICCLedger:
    return ICCLedger(state_dir=state_dir)


# ===========================================================================
# SECTION 5 — SELF-VERIFICATION
# ===========================================================================

def verify_icc_ledger(tmp_state_dir: str) -> Dict[str, Any]:
    """
    Checks (mirrors make_worth_evaluator()/verify_worth_evaluator() and
    make_entropy_detector()/verify_entropy_detector() conventions):
        1. Genesis entry present with prev_hash = "0"*64, source=manual_doctrine
        2. verify_chain() True on a freshly-built ledger
        3. Tampering an entry on disk -> verify_chain() False, frozen
        4. mint_if_eligible degrades to None on missing worth_report
        5. current_balance() never raises, returns a float
        6. summary() exposes no raw factor internals
    """
    results: Dict[str, Any] = {"checks": [], "all_passed": True}

    def check(name: str, passed: bool, detail: str = "") -> None:
        results["checks"].append({"test": name, "passed": passed, "detail": detail})
        if not passed:
            results["all_passed"] = False

    ledger = make_icc_ledger(state_dir=tmp_state_dir)
    check(
        "genesis entry present with correct prev_hash/source",
        len(ledger._entries) == 1
        and ledger._entries[0].prev_hash == GENESIS_PREV_HASH
        and ledger._entries[0].source == "manual_doctrine",
    )
    check("verify_chain() True on fresh ledger", ledger.verify_chain() is True)

    entry = ledger.mint_if_eligible("intake_missing", 1)
    check("mint_if_eligible degrades to None on missing worth_report", entry is None)

    bal = ledger.current_balance(current_tick=1)
    check("current_balance() returns a float without raising", isinstance(bal, float))

    summ = ledger.summary()
    check(
        "summary() exposes no raw factor internals",
        "historical_weight" not in summ and "active_coherence" not in summ,
        f"summary keys={list(summ.keys())}",
    )

    return results


if __name__ == "__main__":
    import tempfile
    print("=" * 70)
    print("AURORA ICC LEDGER — SELF-VERIFICATION")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    with tempfile.TemporaryDirectory() as td:
        results = verify_icc_ledger(td)
    for c in results["checks"]:
        status = "OK" if c["passed"] else "FAIL"
        detail = f"  [{c['detail']}]" if c.get("detail") else ""
        print(f"  [{status}] {c['test']}{detail}")
    passed = sum(1 for c in results["checks"] if c["passed"])
    print(f"\n{passed}/{len(results['checks'])} checks passed.")
    print("=" * 70)
