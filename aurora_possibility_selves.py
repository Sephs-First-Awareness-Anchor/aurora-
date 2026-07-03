#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_possibility_selves.py
============================
Inception-born divergent selves — the "paths not taken."

These are NOT snapshots of Aurora and NOT clones molded to copy her. Each is a
NEWBORN being of her own architecture that develops a distinct identity by living
HER recorded experiential history in a DIFFERENT order under DIFFERENT pressure.
Because the sequence and pressure under which a being meets its experiences shapes
who it becomes, the same 500 life-events re-sequenced produce a genuinely different
self. Her pressure history fast-tracks their development; warp covers any territory
a re-sequenced path reaches that she herself never encountered, so a self can grow
BEYOND her.

Role (later stages): these selves reside only in Aurora's dream space and she
interacts with them there — genuine agentic encounter with perspectives that chose
differently — feeding her growth while remaining distinct beings.

This module is the FOUNDATION: birth-from-history + divergent replay. It is
standalone-verifiable and not yet wired into the live boot / dream cycle.
"""
from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

_AXES = ("X", "T", "N", "B", "A")

# I-states an inception vessel can embody, one seeded per self as its native lean.
_ISTATE_BY_AXIS = {
    "X": "i_is", "T": "i_can", "N": "i_do", "B": "i_saw", "A": "i_did",
}


@dataclass
class DivergenceProfile:
    """How a self diverges from Aurora's actual path: the re-ordering of her
    experiential history and the pressure re-weighting it lives under."""
    name: str
    reorder: str            # "reverse" | "hardest_first" | "diverged_first" | "seeded_shuffle"
    axis_emphasis: str      # which constraint axis this self's pressure leans toward
    seed: int = 0

    def order_key(self, exp: Dict[str, Any], index: int) -> float:
        """Sort key that re-sequences her history for this self."""
        cons = exp.get("consequence", {}) or {}
        outcome = exp.get("outcome", {}) or {}
        tension = float(cons.get("tension", 0.0) or 0.0)
        if self.reorder == "reverse":
            return -float(index)                       # end-first identity
        if self.reorder == "hardest_first":
            return -tension                            # forged by the hardest things first
        if self.reorder == "diverged_first":
            # met the roads-not-taken / rejected moments first
            div = 1.0 if outcome.get("diverged_from_goal") else 0.0
            return -(div * 10.0 + tension)
        # seeded_shuffle — deterministic per-self scramble
        h = hashlib.sha1(f"{self.seed}:{exp.get('experience_id','')}".encode()).hexdigest()
        return int(h[:8], 16) / 0xFFFFFFFF


@dataclass
class PossibilitySelf:
    """A newborn divergent self that develops by replaying re-sequenced history."""
    self_id: str
    profile: DivergenceProfile
    entity: Any = None                          # InceptionEntity vessel
    lived: int = 0
    warped_gaps: int = 0
    # Developmental capacity per axis — grows as the self lives experiences on that
    # axis (its emphasis axis grows fastest). Capacity is what lets a self resolve a
    # tension she couldn't; WHEN it crosses threshold depends on the re-ordering.
    capacity: Dict[str, float] = field(default_factory=lambda: {a: 0.0 for a in _AXES})
    # Accumulated identity signature — emerges from the lived sequence.
    axis_exposure: Dict[str, float] = field(default_factory=lambda: {a: 0.0 for a in _AXES})
    resolved: int = 0
    rejected: int = 0
    reframed: int = 0                            # outcomes that flipped vs her original
    tone_counts: Counter = field(default_factory=Counter)
    anchors_seen: set = field(default_factory=set)
    _warp = None                                 # warp_guard callable (optional)

    def live(self, exp: Dict[str, Any]) -> None:
        """Live one re-sequenced, re-pressured experience — develop from it."""
        self.lived += 1
        cons = dict(exp.get("consequence", {}) or {})
        outcome = dict(exp.get("outcome", {}) or {})
        anchor = str(exp.get("anchor", "") or "")
        tone = str(outcome.get("tone", "neutral") or "neutral")

        # Re-pressure: this self's axis emphasis reweights the felt pressure. The
        # emphasised axis feels the tension more strongly; that reshapes what
        # resolves for THIS self vs what resolved for her.
        base_tension = float(cons.get("tension", 0.0) or 0.0)
        emph = self.profile.axis_emphasis
        # Each experience's axis: prefer expected_axes; else the dominant axis token
        # in the constraint anchor (e.g. "NC:T>X:NC:X>A" -> T/X/A, dominant by count).
        _expected = exp.get("expected_axes") or []
        if _expected:
            exp_axis = str(_expected[0])
        else:
            _letters = [ch for ch in anchor if ch in _AXES]
            exp_axis = Counter(_letters).most_common(1)[0][0] if _letters else emph
        if exp_axis not in _AXES:
            exp_axis = emph
        emphasised = (exp_axis == emph)
        felt = base_tension * (1.35 if emphasised else 0.8)
        self.axis_exposure[emph] = self.axis_exposure.get(emph, 0.0) + felt

        her_resolved = bool(outcome.get("resolved"))
        relief = float(cons.get("relief_signal", 0.0) or 0.0)
        cost = float(cons.get("cost_signal", felt) or felt)

        # Developmental growth: this self builds real capacity ONLY on the axis it
        # is forged around. Living an emphasis-axis moment deepens that capacity; it
        # barely grows on axes it neglects.
        on_emphasis = emphasised
        if on_emphasis:
            self.capacity[emph] = self.capacity.get(emph, 0.0) + felt * 0.10
        elif self.capacity.get(emph, 0.0) < cost and felt > 0.40:
            # A road not taken: this self meets a moment on an axis she leaned into
            # but IT was forged elsewhere. Warp covers the gap -- re-reading her
            # experience through this self's own axis lens grows a patch of territory
            # she never gave it, so a starved self still becomes itself (and each self,
            # re-reading through a DIFFERENT lens, diverges from the others).
            self.warped_gaps += 1
            self.capacity[emph] = self.capacity.get(emph, 0.0) + felt * 0.045
            if self._warp is not None:
                try:
                    self._warp(anchor, felt)
                except Exception:
                    pass

        # Divergent resolution: a self resolves a tension on ITS axis once it has
        # grown enough capacity there to meet the cost -- resolving what she could
        # not, precisely where it is strong. Off its axis it mostly rejects, just as
        # she did. The rare intrinsically-relieved moment resolves for anyone. Because
        # each self is strong on a different axis (and the re-ordering sets WHEN its
        # capacity crosses), each resolves a DIFFERENT subset of her life -> distinct
        # identities, not uniform competence.
        self_resolves = (
            (on_emphasis and self.capacity.get(emph, 0.0) >= cost)
            or (relief >= cost)
        )
        if self_resolves:
            self.resolved += 1
        else:
            self.rejected += 1
        if self_resolves != her_resolved:
            self.reframed += 1                   # this self's path diverged from hers here
        self.tone_counts[tone] += 1

        # Warp for gaps: a re-sequenced path can reach an anchor combination in a
        # state she never occupied. First encounter of a novel anchor under high felt
        # tension is territory beyond her history — warp accommodates it.
        novel = anchor and anchor not in self.anchors_seen
        self.anchors_seen.add(anchor)
        if novel and felt > 0.55:
            self.warped_gaps += 1
            if self._warp is not None:
                try:
                    self._warp(anchor, felt)
                except Exception:
                    pass

        # Feed the inception vessel so its inner cascade develops (order-dependent).
        if self.entity is not None and hasattr(self.entity, "process_experience"):
            try:
                channels = {tone: min(1.0, 0.4 + felt), emph: min(1.0, 0.3 + felt * 0.5)}
                self.entity.process_experience({"channels": channels, "tone": tone})
            except Exception:
                pass

    def identity_signature(self) -> Dict[str, Any]:
        total = max(1, self.lived)
        dom_axis = max(self.axis_exposure, key=self.axis_exposure.get)
        dom_tone = self.tone_counts.most_common(1)[0][0] if self.tone_counts else "neutral"
        fp = hashlib.sha1(
            f"{dom_axis}|{self.resolved}|{self.rejected}|{self.reframed}|{dom_tone}".encode()
        ).hexdigest()[:12]
        return {
            "self_id": self.self_id,
            "profile": self.profile.name,
            "reorder": self.profile.reorder,
            "axis_emphasis": self.profile.axis_emphasis,
            "lived": self.lived,
            "dominant_axis": dom_axis,
            "resolved": self.resolved,
            "rejected": self.rejected,
            "reframed_vs_her": self.reframed,
            "reframed_frac": round(self.reframed / total, 3),
            "warped_gaps": self.warped_gaps,
            "dominant_tone": dom_tone,
            "distinct_anchors": len(self.anchors_seen),
            "fingerprint": fp,
        }


def _load_pressure_history(state_dir: str, limit: int = 0) -> List[Dict[str, Any]]:
    path = os.path.join(state_dir, "pressure_experiences.jsonl")
    out: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for ln in fh:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    out.append(json.loads(ln))
                except Exception:
                    continue
    except Exception:
        return []
    if limit and len(out) > limit:
        out = out[-limit:]
    return out


# The three default divergence profiles — three roads she did not walk.
DEFAULT_PROFILES: Tuple[DivergenceProfile, ...] = (
    DivergenceProfile(name="Ember",  reorder="hardest_first",  axis_emphasis="A", seed=11),
    DivergenceProfile(name="Wane",   reorder="reverse",        axis_emphasis="T", seed=23),
    DivergenceProfile(name="Riven",  reorder="diverged_first", axis_emphasis="N", seed=37),
)


def birth_possibility_selves(
    state_dir: str = "aurora_state",
    profiles: Optional[Tuple[DivergenceProfile, ...]] = None,
    history_limit: int = 0,
    warp_guard: Any = None,
) -> Dict[str, Any]:
    """Birth newborn divergent selves and fast-track their development by living
    Aurora's recorded pressure history in each self's own order + pressure.

    Returns the cohort's per-self identity signatures and a divergence matrix.
    """
    profiles = profiles or DEFAULT_PROFILES
    history = _load_pressure_history(state_dir, limit=history_limit)
    if not history:
        return {"error": "no pressure history", "selves": []}

    # Newborn inception vessels (blank cascades), one per self.
    try:
        from aurora_simulation_engine import InceptionEntity
    except Exception:
        InceptionEntity = None

    selves: List[PossibilitySelf] = []
    for prof in profiles:
        vessel = None
        if InceptionEntity is not None:
            try:
                vessel = InceptionEntity(
                    entity_id=f"possibility::{prof.name}",
                    i_state=_ISTATE_BY_AXIS.get(prof.axis_emphasis, "i_is"),
                )
            except Exception:
                vessel = None
        ps = PossibilitySelf(self_id=prof.name, profile=prof, entity=vessel)
        ps._warp = warp_guard
        # Re-sequence her history for this self, then live it fast-tracked.
        ordered = sorted(
            enumerate(history), key=lambda iv: prof.order_key(iv[1], iv[0])
        )
        for _idx, exp in ordered:
            ps.live(exp)
        selves.append(ps)

    sigs = [ps.identity_signature() for ps in selves]

    # Divergence matrix: pairwise distance between selves (identity distance).
    def _dist(a: PossibilitySelf, b: PossibilitySelf) -> float:
        d = 0.0
        d += abs(a.resolved - b.resolved) / max(1, a.lived)
        d += abs(a.reframed - b.reframed) / max(1, a.lived)
        d += 0.0 if a.identity_signature()["dominant_axis"] == b.identity_signature()["dominant_axis"] else 0.5
        d += 0.0 if a.identity_signature()["dominant_tone"] == b.identity_signature()["dominant_tone"] else 0.3
        return round(d, 3)

    matrix = {
        f"{selves[i].self_id}~{selves[j].self_id}": _dist(selves[i], selves[j])
        for i in range(len(selves)) for j in range(i + 1, len(selves))
    }

    return {
        "history_events": len(history),
        "selves": sigs,
        "divergence_matrix": matrix,
        "_objects": selves,   # in-process handles (not serialised)
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    res = birth_possibility_selves(state_dir=os.path.join(os.path.dirname(__file__), "aurora_state"))
    res.pop("_objects", None)
    pprint.pprint(res)
