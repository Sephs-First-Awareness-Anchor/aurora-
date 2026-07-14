# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
CERS Deprecation Ledger — the auto subsystem-deprecation test.

This is the mechanism the ERS conceptual spec describes in Section 8: running
CERSBridge and the legacy DualStrataBridge in parallel and letting sustained
agreement between them be the evidence that decides whether the legacy path
gets merged, deprecated, or kept as-is. Nothing here deletes or disables
anything automatically — this produces a recommendation, never an action.

Per direct instruction: dormancy is not treated as a permanent block. A
channel that PotentialTracker flags dormant gets an ACTIVE trial opened
against it (cers_potential_trial.py — correlation-tested the same way the
existing WARP CrestRegistry trials new crests). Only channels with a trial
still UNRESOLVED right now block a merge/deprecate recommendation. Once a
trial resolves — either CONFIRMED INERT (genuinely no latent value, stop
blocking) or CONFIRMED BENEFIT (real cross-pipeline correlation found and
attributed) — it stops blocking either way. A confirmed benefit is not
grounds to deprecate that signal; it's evidence to route it, which is a
separate decision this ledger only surfaces, never makes.
"""
from __future__ import annotations

import json
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

MIN_FRAMES_FOR_RECOMMENDATION = 150
AGREEMENT_THRESHOLD_FOR_MERGE = 0.92
MAX_CONFLICT_RATE_FOR_MERGE = 0.02
LEDGER_WINDOW = 500

DEPRECATION_LEDGER_FILENAME = "cers_deprecation_ledger.json"
# Persisted window is a fixed multiple of the recommendation threshold, not
# the full in-memory LEDGER_WINDOW -- enough margin past
# MIN_FRAMES_FOR_RECOMMENDATION to survive restarts without ballooning the
# state file with history evaluate() will never look at.
PERSISTED_WINDOW_CAP = MIN_FRAMES_FOR_RECOMMENDATION * 2


@dataclass
class DeprecationRecommendation:
    """A read, never an action. Something else decides whether to act on it."""

    status: str  # "insufficient_data" | "hold_potential_pending" | "recommend_hold" | "recommend_merge"
    frames_evaluated: int
    agreement_rate: Optional[float]
    conflict_rate: Optional[float]
    blocking_potential: List[str] = field(default_factory=list)
    confirmed_potential_benefits: Dict[str, str] = field(default_factory=dict)
    confirmed_inert_potential: List[str] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "frames_evaluated": self.frames_evaluated,
            "agreement_rate": self.agreement_rate,
            "conflict_rate": self.conflict_rate,
            "blocking_potential": list(self.blocking_potential),
            "confirmed_potential_benefits": dict(self.confirmed_potential_benefits),
            "confirmed_inert_potential": list(self.confirmed_inert_potential),
            "rationale": self.rationale,
        }


class SubsystemDeprecationLedger:
    """Accumulates per-tick equivalence records (as produced by
    CERSBridge.persist()) and evaluates whether sustained evidence supports
    recommending that the legacy subsurface path be merged with or
    deprecated in favor of the CERS-governed path — gated by whether any
    channel currently has an UNRESOLVED potential trial open against it."""

    def __init__(self, window: int = LEDGER_WINDOW, state_dir: Optional[str] = None) -> None:
        self._window = window
        self._entries: Deque[Dict[str, Any]] = deque(maxlen=window)
        self._latest_actively_trialing: List[str] = []
        self._latest_confirmed_benefits: Dict[str, str] = {}
        self._latest_confirmed_inert: List[str] = []
        # Persistence (MTSL Phase 0, P0.2): without this the 150-frame
        # threshold is unreachable across restarting autonomous runs -- the
        # ledger reset to empty on every process boot, so evaluate() never
        # got past "insufficient_data" in practice.
        self._state_dir = str(state_dir) if state_dir else None
        self._path = (
            os.path.join(self._state_dir, DEPRECATION_LEDGER_FILENAME)
            if self._state_dir else None
        )
        if self._path:
            self._load()

    def _load(self) -> None:
        try:
            if not os.path.exists(self._path):
                return
            with open(self._path, encoding="utf-8") as fh:
                raw = json.load(fh)
            if not isinstance(raw, dict):
                return
            for e in list(raw.get("entries", []) or [])[-self._window:]:
                if isinstance(e, dict):
                    self._entries.append({
                        "agrees_with_legacy": bool(e.get("agrees_with_legacy", False)),
                        "conflicts": list(e.get("conflicts", []) or []),
                    })
            self._latest_actively_trialing = list(raw.get("latest_actively_trialing", []) or [])
            self._latest_confirmed_benefits = dict(raw.get("latest_confirmed_benefits", {}) or {})
            self._latest_confirmed_inert = list(raw.get("latest_confirmed_inert", []) or [])
        except Exception:
            # Corrupt ledger never blocks evaluation -- start clean.
            pass

    def _save(self) -> None:
        if not self._path:
            return
        try:
            os.makedirs(self._state_dir, exist_ok=True)
            # Compact: only the two fields evaluate() reads from historical
            # frames (agrees_with_legacy, conflicts) -- not the full
            # equivalence_entry shape, which carries per-tick detail
            # evaluate() never looks at for anything but the latest entry.
            persisted_entries = [
                {
                    "agrees_with_legacy": bool(e.get("agrees_with_legacy", False)),
                    "conflicts": list(e.get("conflicts", []) or []),
                }
                for e in list(self._entries)[-PERSISTED_WINDOW_CAP:]
            ]
            payload = {
                "schema_version": 1,
                "entries": persisted_entries,
                "latest_actively_trialing": list(self._latest_actively_trialing),
                "latest_confirmed_benefits": dict(self._latest_confirmed_benefits),
                "latest_confirmed_inert": list(self._latest_confirmed_inert),
                "saved_at": time.time(),
            }
            tmp = self._path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=1)
            os.replace(tmp, self._path)
        except Exception:
            pass

    def record(self, equivalence_entry: Dict[str, Any]) -> None:
        """equivalence_entry matches the shape CERSBridge.persist() builds,
        including actively_trialing_potential / confirmed_potential_benefits
        / confirmed_inert_potential from the PotentialTrialBoard."""
        self._entries.append(dict(equivalence_entry))
        # The trial board is monotonic and authoritative — a resolved trial
        # never reopens — so the LATEST tick's lists are the current truth,
        # not something to accumulate "ever seen" across the whole window.
        self._latest_actively_trialing = list(equivalence_entry.get("actively_trialing_potential", []) or [])
        self._latest_confirmed_benefits = dict(equivalence_entry.get("confirmed_potential_benefits", {}) or {})
        self._latest_confirmed_inert = list(equivalence_entry.get("confirmed_inert_potential", []) or [])
        self._save()

    def evaluate(self) -> DeprecationRecommendation:
        frames = list(self._entries)
        blocking = list(self._latest_actively_trialing)

        if len(frames) < MIN_FRAMES_FOR_RECOMMENDATION:
            return DeprecationRecommendation(
                status="insufficient_data",
                frames_evaluated=len(frames),
                agreement_rate=None,
                conflict_rate=None,
                blocking_potential=blocking,
                confirmed_potential_benefits=dict(self._latest_confirmed_benefits),
                confirmed_inert_potential=list(self._latest_confirmed_inert),
                rationale=(
                    f"Only {len(frames)} frames observed; need at least "
                    f"{MIN_FRAMES_FOR_RECOMMENDATION} before any recommendation is meaningful."
                ),
            )

        agree_count = sum(1 for f in frames if f.get("agrees_with_legacy"))
        agreement_rate = round(agree_count / len(frames), 4)
        conflict_count = sum(len(f.get("conflicts", []) or []) for f in frames)
        conflict_rate = round(conflict_count / len(frames), 4)

        if blocking:
            return DeprecationRecommendation(
                status="hold_potential_pending",
                frames_evaluated=len(frames),
                agreement_rate=agreement_rate,
                conflict_rate=conflict_rate,
                blocking_potential=blocking,
                confirmed_potential_benefits=dict(self._latest_confirmed_benefits),
                confirmed_inert_potential=list(self._latest_confirmed_inert),
                rationale=(
                    "Agreement rate would otherwise support a recommendation, but "
                    f"{len(blocking)} channel(s) — {', '.join(blocking)} — still have an "
                    "unresolved potential trial open. Not a permanent hold: each is being "
                    "actively correlation-tested against every other cluster and will resolve "
                    "to either confirmed-inert or confirmed-benefit. Holding until resolution."
                ),
            )

        benefit_note = ""
        if self._latest_confirmed_benefits:
            pairs = ", ".join(f"{ch}->{cl}" for ch, cl in self._latest_confirmed_benefits.items())
            benefit_note = f" Note: {pairs} resolved as confirmed cross-pipeline benefit — worth wiring, not discarding."

        if agreement_rate >= AGREEMENT_THRESHOLD_FOR_MERGE and conflict_rate <= MAX_CONFLICT_RATE_FOR_MERGE:
            return DeprecationRecommendation(
                status="recommend_merge",
                frames_evaluated=len(frames),
                agreement_rate=agreement_rate,
                conflict_rate=conflict_rate,
                blocking_potential=[],
                confirmed_potential_benefits=dict(self._latest_confirmed_benefits),
                confirmed_inert_potential=list(self._latest_confirmed_inert),
                rationale=(
                    f"{agreement_rate*100:.1f}% agreement across {len(frames)} frames with "
                    f"{conflict_rate*100:.2f}% conflict rate. All potential trials in this "
                    "window resolved — none still open — so CERS-governed convergence is "
                    "producing equivalent or better results without losing anything the "
                    f"legacy path was doing.{benefit_note}"
                ),
            )

        return DeprecationRecommendation(
            status="recommend_hold",
            frames_evaluated=len(frames),
            agreement_rate=agreement_rate,
            conflict_rate=conflict_rate,
            blocking_potential=[],
            confirmed_potential_benefits=dict(self._latest_confirmed_benefits),
            confirmed_inert_potential=list(self._latest_confirmed_inert),
            rationale=(
                f"{agreement_rate*100:.1f}% agreement / {conflict_rate*100:.2f}% conflict rate "
                f"does not yet clear the bar for a merge recommendation.{benefit_note} Keep both paths running."
            ),
        )
