#!/usr/bin/env python3
"""
aurora_reasoning_paths.py -- remembered reasoning paths that PARTICIPATE.

Sunni, 2026-11-08: "Why can't the paths participate in reasoning rather than
skip?"  They do here.  Nothing in this module skips a stage, chooses a reply,
or stores a word of speech.

WHAT A PATH IS
  The pressure she was under (axis activation + the shape of what was said)
  and where each of her stages LANDED the last time that pressure was met and
  she was understood: meaning label and signature, dominant axis, conscious
  action, response operation, deep emotion, reactive bias, the abilities that
  were live, the salient concepts.  Structure only.

HOW IT PARTICIPATES
  When her pressure resonates with a path (same utterance shape, axis
  activation cosine >= RESONANCE_FLOOR), the path is OFFERED for this turn:
    * as `remembered_path` in her established strata evidence, beside memory,
      continuity and grounding -- every later stage sees it;
    * as a lean on ability selection: abilities the path used gain up to
      MAX_ABILITY_LEAN of active weight, scaled by the path's EARNED weight
      and the resonance.  A lean among near-equals -- it cannot outvote what
      her current state supports.
  Every stage still reasons in full.

AGREEMENT AND DIVERGENCE
  After the turn her live landings are compared with the offered path, field
  by field.  Agreement and divergence are both recorded (the Hub shows them).

CARVING AND WEARING (receiver verdicts decide; nothing else does)
  understood + agreed      -> the path deepens (weight up), centroid follows
  understood + diverged    -> her NEW landings carve (or deepen) their own
                              path; the old one loses a little pull -- this
                              is the reconsideration
  misunderstood + agreed   -> the path wears down (it led her wrong)
  misunderstood + diverged -> the old path regains a little pull
  understood, nothing offered -> a faint new path is carved
  Paths below DISSOLVE_WEIGHT dissolve.  New paths start at CARVE_WEIGHT:
  faint, so their pull is earned.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import hashlib
import json
import math
import os
import threading
import time
from typing import Any, Dict, List, Mapping, Optional, Tuple

PATHS_VERSION = "aurora_reasoning_paths_v1"
AXES = ("X", "T", "N", "B", "A")

RESONANCE_FLOOR = 0.92
OFFER_MIN_WEIGHT = 0.10
CARVE_WEIGHT = 0.12
DEEPEN_RATE = 0.20          # weight += rate * (1 - weight)
WEAR_FACTOR = 0.60          # misunderstood while following it
RECONSIDER_FACTOR = 0.85    # understood while diverging from it
REGAIN = 0.05               # misunderstood while diverging from it
# Below the offer floor a path can never be offered again, so it could never
# be confirmed or worn either -- it dissolves there instead of lingering.
DISSOLVE_WEIGHT = 0.10
AGREE_THRESHOLD = 0.60
MAX_ABILITY_LEAN = 0.12
MAX_PATHS = 400
MAX_PENDING = 64
CENTROID_KEEP = 0.8

LANDING_FIELDS = ("meaning_label", "meaning_signature", "dominant_axis", "action",
                  "operation", "emotion", "bias")
# What defines a path: how she understood it, what she chose to do, and the
# response it called for.  A difference in any of these is a divergence
# whatever else matches.  Quieter landings count for less.
CORE_FIELDS = ("meaning_label", "action", "operation")
FIELD_WEIGHT = {"meaning_label": 2.0, "action": 2.0, "operation": 2.0,
                "meaning_signature": 1.0, "dominant_axis": 1.0, "abilities": 1.0,
                "emotion": 0.5, "bias": 0.5}


def _f(value: Any) -> float:
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0


def _unit(vec: Mapping[str, Any]) -> Dict[str, float]:
    raw = {ax: max(0.0, _f(vec.get(ax))) for ax in AXES}
    norm = math.sqrt(sum(v * v for v in raw.values()))
    return {ax: (v / norm if norm > 0 else 0.0) for ax, v in raw.items()}


def _cosine(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    return sum(_f(a.get(ax)) * _f(b.get(ax)) for ax in AXES)


def utterance_shape(pipeline_state: Mapping[str, Any]) -> str:
    """The structural shape of what was said -- no words."""
    form = dict(pipeline_state.get("relational_form") or {})
    raw = str(form.get("raw_text") or "")
    return "|".join((
        str(form.get("unknown_role") or "none"),
        "q" if raw.rstrip().endswith("?") else "s",
        "rel" if str(form.get("relation") or "").strip() else "norel",
        "obj" if str(form.get("obj") or "").strip() else "noobj",
        str(pipeline_state.get("input_stance") or pipeline_state.get("user_stance") or ""),
    ))


def signature(pipeline_state: Mapping[str, Any], axis_activation: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    return {"shape": utterance_shape(pipeline_state),
            "axes": _unit(axis_activation if axis_activation is not None
                          else pipeline_state.get("axis_activation") or {})}


def landings(pipeline_state: Mapping[str, Any], ability_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Where her stages landed this turn -- structure, never speech."""
    obligation = dict(pipeline_state.get("response_obligation") or {})
    return {
        "meaning_label": str(pipeline_state.get("meaning_label") or ""),
        "meaning_signature": str(pipeline_state.get("meaning_signature") or ""),
        "dominant_axis": str(pipeline_state.get("dominant_axis") or ""),
        "action": str(pipeline_state.get("selected_conscious_action") or ""),
        "operation": str(obligation.get("operation") or ""),
        "emotion": str(pipeline_state.get("deep_dominant_emotion") or ""),
        "bias": str(pipeline_state.get("surface_reactive_bias") or ""),
        "abilities": [str(a) for a in list(ability_ids or pipeline_state.get("active_abilities") or [])][:5],
        "concepts": [str(c) for c in list(pipeline_state.get("salient_concepts") or [])][:4],
    }


def compare(path_landings: Mapping[str, Any], live: Mapping[str, Any]) -> Dict[str, Any]:
    agreed, diverged = [], []
    for name in LANDING_FIELDS:
        a, b = str(path_landings.get(name) or ""), str(live.get(name) or "")
        if not a and not b:
            continue
        (agreed if a == b else diverged).append(name)
    pa, la = set(path_landings.get("abilities") or []), set(live.get("abilities") or [])
    if pa or la:
        overlap = len(pa & la) / max(1, len(pa | la))
        (agreed if overlap >= 0.5 else diverged).append("abilities")
    total = sum(FIELD_WEIGHT.get(n, 1.0) for n in agreed + diverged)
    agreement = sum(FIELD_WEIGHT.get(n, 1.0) for n in agreed) / total if total else 0.0
    core_diverged = [n for n in diverged if n in CORE_FIELDS]
    return {"agreement": round(agreement, 4), "agrees": bool(total) and agreement >= AGREE_THRESHOLD and not core_diverged,
            "agreed": agreed, "diverged": diverged, "core_diverged": core_diverged,
            "differences": {n: {"path": path_landings.get(n), "live": live.get(n)}
                            for n in diverged if n != "abilities"}}


class ReasoningPaths:
    def __init__(self, *, state_dir: str = "aurora_state", persist: bool = True,
                 clock=time.time) -> None:
        self.path = os.path.join(state_dir, "reasoning_paths.json")
        self.persist = persist
        self.clock = clock
        self._lock = threading.RLock()
        self.paths: Dict[str, Dict[str, Any]] = {}
        self.pending: Dict[str, Dict[str, Any]] = {}
        self.offer: Optional[Dict[str, Any]] = None
        self.counters = {"offered": 0, "agreed": 0, "diverged": 0, "carved": 0,
                         "deepened": 0, "worn": 0, "reconsidered": 0, "dissolved": 0}
        self.last_divergence: Dict[str, Any] = {}
        self._load()

    # -- persistence --------------------------------------------------------------

    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw = json.load(fh) or {}
        except Exception:
            return
        self.paths = {str(k): dict(v) for k, v in dict(raw.get("paths") or {}).items()}
        self.counters.update({k: int(v) for k, v in dict(raw.get("counters") or {}).items()})
        self.last_divergence = dict(raw.get("last_divergence") or {})

    def _save(self) -> None:
        if not self.persist:
            return
        try:
            from aurora_internal.aurora_turn_persistence import batch_defer
            if batch_defer(self):
                return
        except Exception:
            pass
        self.flush_write_batch()

    def flush_write_batch(self) -> None:
        if not self.persist:
            return
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            tmp = self.path + ".tmp"
            with self._lock:
                payload = {"version": PATHS_VERSION, "paths": self.paths,
                           "counters": self.counters, "last_divergence": self.last_divergence}
                data = json.dumps(payload)
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(data)
            os.replace(tmp, self.path)
        except Exception:
            pass

    # -- offering -------------------------------------------------------------------

    def recall(self, sig: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
        """The best resonating path with earned weight, or None."""
        best, best_score = None, 0.0
        with self._lock:
            for pid, path in self.paths.items():
                if path.get("shape") != sig.get("shape"):
                    continue
                if _f(path.get("weight")) < OFFER_MIN_WEIGHT:
                    continue
                resonance = _cosine(path.get("centroid") or {}, sig.get("axes") or {})
                if resonance < RESONANCE_FLOOR:
                    continue
                score = resonance * _f(path.get("weight"))
                if score > best_score:
                    best, best_score = (pid, path, resonance), score
        if best is None:
            return None
        pid, path, resonance = best
        return {"path_id": pid, "weight": round(_f(path.get("weight")), 4),
                "resonance": round(resonance, 4), "landings": dict(path.get("landings") or {}),
                "confirmations": int(path.get("confirmations", 0) or 0)}

    def begin_turn(self, pipeline_state: Mapping[str, Any], axis_activation: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
        sig = signature(pipeline_state, axis_activation)
        offer = self.recall(sig)
        with self._lock:
            self.offer = {"signature": sig, "path": offer}
            if offer is not None:
                self.counters["offered"] += 1
        return offer

    def ability_lean(self, ability_id: str) -> float:
        """Extra active weight for an ability the offered path used."""
        offer = (self.offer or {}).get("path")
        if not offer or ability_id not in set(dict(offer.get("landings") or {}).get("abilities") or []):
            return 0.0
        return round(min(MAX_ABILITY_LEAN, MAX_ABILITY_LEAN * _f(offer.get("weight")) * _f(offer.get("resonance"))), 4)

    # -- after the turn ---------------------------------------------------------------

    def end_turn(self, pipeline_state: Mapping[str, Any], response_id: str,
                 ability_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        live = landings(pipeline_state, ability_ids)
        with self._lock:
            offer = dict(self.offer or {})
            self.offer = None
        sig = offer.get("signature") or signature(pipeline_state)
        offered = offer.get("path")
        record: Dict[str, Any] = {"signature": sig, "landings": live,
                                  "offered": offered, "comparison": None, "at": self.clock()}
        if offered:
            comparison = compare(offered.get("landings") or {}, live)
            record["comparison"] = comparison
            with self._lock:
                if comparison["agrees"]:
                    self.counters["agreed"] += 1
                else:
                    self.counters["diverged"] += 1
                    self.last_divergence = {"path_id": offered.get("path_id"),
                                            "differences": comparison["differences"],
                                            "agreement": comparison["agreement"], "at": self.clock()}
        if response_id:
            with self._lock:
                self.pending[str(response_id)] = record
                while len(self.pending) > MAX_PENDING:
                    self.pending.pop(next(iter(self.pending)))
        self._save()
        return record

    def _carve(self, sig: Mapping[str, Any], live: Mapping[str, Any]) -> str:
        """Deepen a path with these exact landings under this pressure, or carve one."""
        for pid, path in self.paths.items():
            if (path.get("shape") == sig.get("shape")
                    and _cosine(path.get("centroid") or {}, sig.get("axes") or {}) >= RESONANCE_FLOOR
                    and compare(path.get("landings") or {}, live)["agreement"] >= 0.999):
                self._deepen(path, sig)
                return pid
        pid = "RP:" + hashlib.sha1(json.dumps([sig, live], sort_keys=True).encode()).hexdigest()[:12]
        self.paths[pid] = {"shape": sig.get("shape"), "centroid": dict(sig.get("axes") or {}),
                           "landings": dict(live), "weight": CARVE_WEIGHT, "confirmations": 1,
                           "misled": 0, "created_at": self.clock(), "last_used": self.clock()}
        self.counters["carved"] += 1
        return pid

    def _deepen(self, path: Dict[str, Any], sig: Mapping[str, Any]) -> None:
        path["weight"] = round(_f(path.get("weight")) + DEEPEN_RATE * (1.0 - _f(path.get("weight"))), 4)
        path["confirmations"] = int(path.get("confirmations", 0) or 0) + 1
        old = dict(path.get("centroid") or {})
        new = dict(sig.get("axes") or {})
        path["centroid"] = _unit({ax: CENTROID_KEEP * _f(old.get(ax)) + (1 - CENTROID_KEEP) * _f(new.get(ax))
                                  for ax in AXES})
        path["last_used"] = self.clock()
        self.counters["deepened"] += 1

    def record_receiver_outcome(self, response_id: str, outcome_kind: str) -> Dict[str, Any]:
        kind = str(outcome_kind or "")
        with self._lock:
            record = self.pending.pop(str(response_id or ""), None)
            if record is None or kind not in ("positive", "negative"):
                return {"matched": record is not None, "effect": "none"}
            sig, live = record["signature"], record["landings"]
            offered, comparison = record.get("offered"), record.get("comparison") or {}
            agreed = bool(offered) and bool(comparison.get("agrees"))
            old = self.paths.get(str((offered or {}).get("path_id") or ""))
            effect = ""
            if kind == "positive":
                if agreed and old is not None:
                    self._deepen(old, sig)
                    effect = "deepened"
                else:
                    new_id = self._carve(sig, live)
                    effect = "carved:" + new_id
                    if old is not None:
                        old["weight"] = round(_f(old.get("weight")) * RECONSIDER_FACTOR, 4)
                        self.counters["reconsidered"] += 1
                        effect = "reconsidered:" + new_id
            else:
                if agreed and old is not None:
                    old["weight"] = round(_f(old.get("weight")) * WEAR_FACTOR, 4)
                    old["misled"] = int(old.get("misled", 0) or 0) + 1
                    self.counters["worn"] += 1
                    effect = "worn"
                elif old is not None:
                    old["weight"] = round(min(1.0, _f(old.get("weight")) + REGAIN), 4)
                    effect = "regained"
            for pid in [p for p, v in self.paths.items() if _f(v.get("weight")) < DISSOLVE_WEIGHT]:
                del self.paths[pid]
                self.counters["dissolved"] += 1
            if len(self.paths) > MAX_PATHS:
                ranked = sorted(self.paths.items(), key=lambda kv: (_f(kv[1].get("weight")), _f(kv[1].get("last_used"))))
                for pid, _ in ranked[: len(self.paths) - MAX_PATHS]:
                    del self.paths[pid]
                    self.counters["dissolved"] += 1
        self._save()
        return {"matched": True, "effect": effect}

    def status(self) -> Dict[str, Any]:
        with self._lock:
            weights = sorted((_f(p.get("weight")) for p in self.paths.values()), reverse=True)
            return {"version": PATHS_VERSION, "paths": len(self.paths),
                    "strong_paths": sum(1 for w in weights if w >= 0.5),
                    "top_weight": round(weights[0], 4) if weights else 0.0,
                    **self.counters, "pending": len(self.pending),
                    "last_divergence": dict(self.last_divergence)}
