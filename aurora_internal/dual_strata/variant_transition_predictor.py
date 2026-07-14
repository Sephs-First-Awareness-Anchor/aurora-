# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_internal/dual_strata/variant_transition_predictor.py
===============================================================
VariantTransitionPredictor — MTSL Phase 7 (2026-07-13), spec section 8.
"predictor learns variant-transition chains (SV-a -> SV-b -> outcome)."

No prior code in the repo learns this kind of chain (confirmed by
research before writing this file: PredictionPayload/PredictionSignal
in prediction_field.py are single-step only; PredictiveStager queues
staged frames, it doesn't learn transitions) -- this is new territory,
built fresh rather than bent into an existing module's shape.

Learns simple transition statistics: given the previously observed
semantic variant and the current one, accumulate outcome evidence for
that (from, to) pair. predict_next() ranks the variants historically
seen to follow the current one, weighted by how often and how well
that transition has gone. NO AUTHORITY: purely descriptive/predictive
plumbing, same posture as every other Phase 2-7 module this session
built -- nothing here decides anything or gets called from a live
per-turn path yet (that live wiring -- observe() fed from the
coordinator's semantic_variant_id each turn, record_turn_outcome()
threading positive/negative back in -- is deferred, same posture as
this session's other Phase 4-6 deferrals).
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = 1
STATE_FILENAME = "variant_transition_chains.json"

DEFAULT_PREDICTION_LIMIT = 5


@dataclass
class TransitionRecord:
    from_variant_id: str
    to_variant_id: str
    observation_count: int = 0
    outcome_positive: int = 0
    outcome_negative: int = 0
    first_seen: float = 0.0
    last_seen: float = 0.0

    @property
    def outcome_support(self) -> float:
        total = self.outcome_positive + self.outcome_negative
        if total <= 0:
            return 0.5  # neutral prior, no evidence yet -- matches the
        return round(self.outcome_positive / total, 4)  # convention used throughout MTSL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_variant_id": self.from_variant_id,
            "to_variant_id": self.to_variant_id,
            "observation_count": self.observation_count,
            "outcome_positive": self.outcome_positive,
            "outcome_negative": self.outcome_negative,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TransitionRecord":
        return cls(
            from_variant_id=str(d.get("from_variant_id", "") or ""),
            to_variant_id=str(d.get("to_variant_id", "") or ""),
            observation_count=int(d.get("observation_count", 0) or 0),
            outcome_positive=int(d.get("outcome_positive", 0) or 0),
            outcome_negative=int(d.get("outcome_negative", 0) or 0),
            first_seen=float(d.get("first_seen", 0.0) or 0.0),
            last_seen=float(d.get("last_seen", 0.0) or 0.0),
        )


@dataclass(frozen=True)
class TransitionPrediction:
    to_variant_id: str
    probability: float        # this transition's observation share among all transitions FROM current
    outcome_support: float
    observation_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "to_variant_id": self.to_variant_id,
            "probability": self.probability,
            "outcome_support": self.outcome_support,
            "observation_count": self.observation_count,
        }


class VariantTransitionPredictor:
    """Call observe(variant_id, positive=...) once per turn with the
    coordinator's current semantic_variant_id (or None when nothing
    matched). Tracks only the last-seen variant internally -- no other
    memory -- to form (from, to) transition pairs automatically."""

    def __init__(self, state_dir: Optional[str] = None) -> None:
        self._state_dir = str(state_dir) if state_dir else None
        self._path = os.path.join(self._state_dir, STATE_FILENAME) if self._state_dir else None
        self._transitions: Dict[Tuple[str, str], TransitionRecord] = {}
        self.last_variant_id: Optional[str] = None
        self._dirty = False
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
            self.last_variant_id = raw.get("last_variant_id")
            for entry in raw.get("transitions", []) or []:
                rec = TransitionRecord.from_dict(entry)
                if rec.from_variant_id and rec.to_variant_id:
                    self._transitions[(rec.from_variant_id, rec.to_variant_id)] = rec
        except Exception:
            pass

    def save(self) -> bool:
        if not self._path:
            return False
        if not self._dirty:
            return False
        try:
            os.makedirs(self._state_dir, exist_ok=True)
            payload = {
                "schema_version": SCHEMA_VERSION,
                "last_variant_id": self.last_variant_id,
                "transitions": [rec.to_dict() for rec in self._transitions.values()],
                "saved_at": time.time(),
            }
            tmp = self._path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=1, sort_keys=True)
            os.replace(tmp, self._path)
            self._dirty = False
            return True
        except Exception:
            return False

    def observe(self, variant_id: Optional[str], *, positive: Optional[bool] = None) -> Optional[TransitionRecord]:
        """Record a transition FROM the previously observed variant TO
        this one. Returns None (records nothing) when there's no prior
        variant to transition from, or when this turn's variant is
        None -- there's nothing real to transition into. The internal
        last_variant_id cursor still advances either way, so a None
        turn correctly breaks the chain rather than falsely linking
        across it."""
        prev = self.last_variant_id
        self.last_variant_id = variant_id
        if not prev or not variant_id:
            return None
        key = (prev, variant_id)
        now = time.time()
        rec = self._transitions.get(key)
        if rec is None:
            rec = TransitionRecord(from_variant_id=prev, to_variant_id=variant_id, first_seen=now)
            self._transitions[key] = rec
        rec.observation_count += 1
        rec.last_seen = now
        if positive is True:
            rec.outcome_positive += 1
        elif positive is False:
            rec.outcome_negative += 1
        self._dirty = True
        return rec

    def predict_next(self, current_variant_id: str, *, limit: int = DEFAULT_PREDICTION_LIMIT) -> List[TransitionPrediction]:
        """Rank the variants historically observed to follow
        current_variant_id, by observation share (probability) with
        outcome_support as a tiebreaker. Empty list -- never fabricated
        -- when nothing has ever transitioned from this variant."""
        candidates = [rec for (f, _t), rec in self._transitions.items() if f == current_variant_id]
        if not candidates:
            return []
        total = sum(rec.observation_count for rec in candidates)
        if total <= 0:
            return []
        predictions = [
            TransitionPrediction(
                to_variant_id=rec.to_variant_id,
                probability=round(rec.observation_count / total, 4),
                outcome_support=rec.outcome_support,
                observation_count=rec.observation_count,
            )
            for rec in candidates
        ]
        predictions.sort(key=lambda p: (-p.probability, -p.outcome_support))
        return predictions[: max(1, int(limit or 1))]

    def transition_count(self) -> int:
        return len(self._transitions)

    def get_transition(self, from_variant_id: str, to_variant_id: str) -> Optional[TransitionRecord]:
        return self._transitions.get((from_variant_id, to_variant_id))
