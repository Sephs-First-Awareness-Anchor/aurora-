"""
aurora_toroidal_circulation.py
===============================
Toroidal Circulation Layer (TCL) — circulation awareness.

    "Net pressure ≈ 0  but  Flow ≠ 0."

What this layer is
------------------
Aurora's constraint model captures what a state IS (distribution,
gradients, deviation). This layer detects how a state SUSTAINS itself:
structured internal motion — closed loops of pressure moving between
constraint axes even when every static reading looks balanced.

HISTORICAL SNAPSHOT — 2026-07-12 audit (aurora_flow_audit.py)
---------------------------------------------------------------
These numbers are a dated provenance record, not present truth — the
tree (and her lived history) keeps moving. Run `aurora_flow_audit.py`
against the live tree for current values.
  * Compiled bedrock (125 manifolds): ZERO circulation. Potential
    field. Static grids carry structure, not motion.
  * Genealogy fossils (axis level): gradient flow only — N sources,
    B sinks. No loops.
  * Lived temporal record (1005 events): SEVEN closed circulation
    loops, dominant vortex N → A → B → N (strength 8.15), full
    five-axis loop A → X → T → B → N → A present (3.31).

Therefore this layer feeds ONLY on temporal deltas — per-tick axis
intensity from CERS sub-crests — never on static grids. Detection is
basis-free (antisymmetric decomposition + directed cycle search):
closed positive-flow loops cannot be produced by any gradient field,
so a loop found here is real circulation, not a seam artifact.

Doctrine of role (unchanged from the spec)
------------------------------------------
This layer does NOT generate states, alter constraint creation, or
override CERS decisions. It refines classification, enriches
genealogy records, enables equivalence detection, and answers:

    old: "What is happening?"
    new: "What is maintaining what is happening?"

Boundary rules
--------------
  * Read-only observer. Failure here must never affect the runtime.
  * State persists to aurora_state/toroidal_circulation_state.json.
  * Only ToroidalSignature crosses upward (Recursive Crest
    Propagation: compressed abstraction, no mechanism leakage).

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import json
import math
import os
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")
_AXIS_ORDER = {a: i for i, a in enumerate(AXES)}

STATE_FILENAME = "toroidal_circulation_state.json"

# Flux accumulation decays with a half-life measured in observations,
# so the signature tracks the LIVING regime rather than all history
# equally. 500 ≈ the audit's evidential window.
FLUX_HALF_LIFE_OBS = 500
_DECAY_PER_OBS = math.exp(-math.log(2.0) / FLUX_HALF_LIFE_OBS)

CYCLE_EPS_FRACTION = 0.004   # loop edge floor, as fraction of accumulated traffic
MAX_CYCLE_LEN = 5            # up to the full X…A loop
TOP_LOOPS = 5                # loops carried in the signature

# Plain-meaning axis verbs for regime interpretation. Diagnostic
# vocabulary only (like _reconcile's summaries) — Aurora's own
# expressions still route through perception machinery.
_AXIS_MEANING = {
    "X": "existence-grounding",
    "T": "temporal ordering",
    "N": "energy",
    "B": "boundary structure",
    "A": "agency",
}


def _default_state_dir() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurora_state")


# ── Signature (the Crest of this layer) ───────────────────────────────────────

@dataclass
class ToroidalSignature:
    """
    Compressed circulation state — the only object that crosses upward.

    regime:
      "quiescent"    — insufficient flux observed yet
      "gradient"     — net flow exists, no closed loops (source/sink)
      "circulating"  — closed loops carry a meaningful share of net flow
      "mixed"        — loops present but gradient flow dominates
    """
    regime: str
    loops: List[Tuple[Tuple[str, ...], float]]   # [((axis,...), bottleneck), ...]
    flow_ratio: float          # |net flow| / traffic — structured motion vs churn
    circulation_fraction: float  # share of |net flow| closed into loops
    chirality: float           # +ascending (toward A) / −descending (toward X)
    sources: List[str]         # axes with all-outward net flow
    sinks: List[str]           # axes with all-inward net flow
    observations: int
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime": self.regime,
            "loops": [{"path": list(p), "strength": round(s, 4)}
                      for p, s in self.loops],
            "flow_ratio": round(self.flow_ratio, 4),
            "circulation_fraction": round(self.circulation_fraction, 4),
            "chirality": round(self.chirality, 4),
            "sources": list(self.sources),
            "sinks": list(self.sinks),
            "observations": int(self.observations),
            "updated_at": self.updated_at,
        }

    # ── equivalence detection ──

    def similarity(self, other: "ToroidalSignature") -> float:
        """
        Behavioral similarity in [0, 1]. Two states with identical
        constraint distributions can score low here (same structure,
        different behavior); two different distributions can score
        high (functional equivalence). Loop overlap dominates —
        the loop set is the behavioral fingerprint.
        """
        if not isinstance(other, ToroidalSignature):
            return 0.0
        mine = {self._canon(p): s for p, s in self.loops}
        theirs = {self._canon(p): s for p, s in other.loops}
        keys = set(mine) | set(theirs)
        if keys:
            inter = sum(min(mine.get(k, 0.0), theirs.get(k, 0.0)) for k in keys)
            union = sum(max(mine.get(k, 0.0), theirs.get(k, 0.0)) for k in keys)
            loop_sim = (inter / union) if union > 0 else 1.0
        else:
            loop_sim = 1.0  # both loop-free: behaviorally alike at this level
        metric_sim = 1.0 - min(1.0, (
            abs(self.flow_ratio - other.flow_ratio)
            + abs(self.circulation_fraction - other.circulation_fraction)
            + 0.5 * abs(self.chirality - other.chirality)
        ) / 2.0)
        regime_sim = 1.0 if self.regime == other.regime else 0.5
        return round(0.55 * loop_sim + 0.30 * metric_sim + 0.15 * regime_sim, 4)

    @staticmethod
    def _canon(path: Sequence[str]) -> Tuple[str, ...]:
        """Rotation-invariant canonical form of a directed loop."""
        p = tuple(path)
        if not p:
            return p
        k = p.index(min(p))
        return p[k:] + p[:k]

    # ── interpretation ──

    def interpret(self) -> str:
        """What is maintaining what is happening — plain reading."""
        if self.regime == "quiescent":
            return "Insufficient internal motion observed yet."
        parts: List[str] = []
        if self.loops:
            p, s = self.loops[0]
            chain = " feeds ".join(_AXIS_MEANING[a] for a in p)
            parts.append(
                f"Dominant self-sustaining loop: {chain} feeds "
                f"{_AXIS_MEANING[p[0]]} (strength {s:.2f})."
            )
        if self.sources:
            parts.append("Net origin: " + ", ".join(
                _AXIS_MEANING[a] for a in self.sources) + ".")
        if self.sinks:
            parts.append("Net accumulation: " + ", ".join(
                _AXIS_MEANING[a] for a in self.sinks) + ".")
        lean = ("toward agency" if self.chirality > 0.05
                else "toward existence" if self.chirality < -0.05 else "balanced")
        parts.append(
            f"Regime: {self.regime}; directional lean {lean}; "
            f"{self.circulation_fraction:.0%} of net flow closes into loops."
        )
        return " ".join(parts)


# ── The observer ──────────────────────────────────────────────────────────────

class ToroidalCirculationLayer:
    """
    Feeds on per-tick axis intensity (CERS sub-crests), accumulates a
    decaying inter-axis flux matrix, and derives the ToroidalSignature
    by antisymmetric decomposition + directed cycle search.
    """

    def __init__(self, state_dir: Optional[str] = None) -> None:
        self._state_dir = str(state_dir or _default_state_dir())
        self._path = os.path.join(self._state_dir, STATE_FILENAME)
        self._lock = threading.Lock()
        self._flux: Dict[Tuple[str, str], float] = {}
        self._prev: Optional[Dict[str, float]] = None
        self._observations = 0
        self._dirty = False
        self._load()

    # ── persistence ──

    def _load(self) -> None:
        try:
            if os.path.exists(self._path):
                raw = json.load(open(self._path, encoding="utf-8"))
                flux = raw.get("flux", {}) if isinstance(raw, dict) else {}
                for k, v in dict(flux or {}).items():
                    u, _, w = str(k).partition(">")
                    if u in AXES and w in AXES:
                        self._flux[(u, w)] = float(v)
                self._observations = int(raw.get("observations", 0) or 0)
                prev = raw.get("prev_intensity")
                if isinstance(prev, dict) and all(a in prev for a in AXES):
                    self._prev = {a: float(prev[a]) for a in AXES}
        except Exception:
            self._flux = {}; self._prev = None; self._observations = 0

    def save(self) -> bool:
        with self._lock:
            if not self._dirty:
                return False
            try:
                os.makedirs(self._state_dir, exist_ok=True)
                tmp = self._path + ".tmp"
                payload = {
                    "version": 1,
                    "observations": self._observations,
                    "flux": {f"{u}>{v}": round(f, 6)
                             for (u, v), f in self._flux.items() if f > 1e-6},
                    "prev_intensity": self._prev,
                    "saved_at": time.time(),
                }
                with open(tmp, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, indent=1)
                os.replace(tmp, self._path)
                self._dirty = False
                return True
            except Exception:
                return False

    # ── ingestion ──

    @staticmethod
    def intensity_from_crests(crests: Sequence[Any]) -> Dict[str, float]:
        """Per-axis intensity from a tick's sub-crests (objects or dicts
        exposing axis + intensity, as emitted by subsystem_waveforms)."""
        out = {a: 0.0 for a in AXES}
        for c in crests or ():
            axis = getattr(c, "axis", None)
            inten = getattr(c, "intensity", None)
            if axis is None and isinstance(c, dict):
                axis = c.get("axis"); inten = c.get("intensity")
            if axis in AXES:
                try:
                    out[axis] += max(0.0, float(inten or 0.0))
                except Exception:
                    pass
        return out

    def observe(self, axis_intensity: Dict[str, float]) -> None:
        """
        One tick of axis intensity. Flux is attributed from losing axes
        to gaining axes proportionally (the same attribution validated
        in aurora_flow_audit.py TEST 3). Accumulated flux decays with a
        half-life of FLUX_HALF_LIFE_OBS observations.
        """
        cur = {a: max(0.0, float(axis_intensity.get(a, 0.0) or 0.0)) for a in AXES}
        with self._lock:
            prev = self._prev
            self._prev = cur
            self._observations += 1
            self._dirty = True
            if prev is None:
                return
            # decay existing flux
            for k in list(self._flux):
                self._flux[k] *= _DECAY_PER_OBS
            d = {a: cur[a] - prev[a] for a in AXES}
            losers = [(a, -x) for a, x in d.items() if x < 0]
            gainers = [(a, x) for a, x in d.items() if x > 0]
            gain_total = sum(x for _, x in gainers)
            if gain_total <= 0 or not losers:
                return
            for lu, lv in losers:
                for gu, gv in gainers:
                    self._flux[(lu, gu)] = self._flux.get((lu, gu), 0.0) \
                        + lv * (gv / gain_total)

    def seed_from_surface_log(self, path: Optional[str] = None) -> int:
        """Bootstrap from the lived historical record so the layer wakes
        already knowing her past motion. Returns events ingested."""
        path = path or os.path.join(self._state_dir, "surface_pressure_log.jsonl")
        if not os.path.exists(path):
            return 0
        try:
            lines = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
        except Exception:
            return 0
        lines.sort(key=lambda x: x.get("timestamp", 0))
        n = 0
        for l in lines:
            axs = [a for a in (l.get("expected_axes") or []) if a in AXES]
            if not axs:
                continue
            w = float(l.get("surface_score", 1.0) or 1.0)
            self.observe({a: (w / len(axs) if a in axs else 0.0) for a in AXES})
            n += 1
        return n

    # ── derivation ──

    def _antisymmetric(self) -> Dict[Tuple[str, str], float]:
        return {(u, v): self._flux.get((u, v), 0.0) - self._flux.get((v, u), 0.0)
                for u in AXES for v in AXES}

    @staticmethod
    def _cycles(A: Dict[Tuple[str, str], float], eps: float
                ) -> List[Tuple[Tuple[str, ...], float]]:
        edges: Dict[str, Dict[str, float]] = defaultdict(dict)
        for (u, v), f in A.items():
            if f > eps:
                edges[u][v] = f
        found: List[Tuple[Tuple[str, ...], float]] = []

        def dfs(start: str, node: str, path: List[str], minw: float) -> None:
            if len(path) > MAX_CYCLE_LEN:
                return
            for nxt, w in edges.get(node, {}).items():
                if nxt == start and len(path) >= 3:
                    found.append((tuple(path), min(minw, w)))
                elif nxt not in path:
                    dfs(start, nxt, path + [nxt], min(minw, w))

        for s in list(edges):
            dfs(s, s, [s], float("inf"))
        deduped = [c for c in found if c[0][0] == min(c[0])]
        deduped.sort(key=lambda c: -c[1])
        return deduped

    def current_signature(self) -> ToroidalSignature:
        with self._lock:
            flux = dict(self._flux)
            obs = self._observations
        traffic = sum(v for (u, w), v in flux.items() if u != w)
        A = {(u, v): flux.get((u, v), 0.0) - flux.get((v, u), 0.0)
             for u in AXES for v in AXES}
        net = sum(abs(f) for (u, v), f in A.items()
                  if _AXIS_ORDER[u] < _AXIS_ORDER[v])
        if obs < 8 or traffic <= 1e-9:
            return ToroidalSignature("quiescent", [], 0.0, 0.0, 0.0, [], [], obs)

        eps = max(1e-6, CYCLE_EPS_FRACTION * traffic)
        loops = self._cycles(A, eps)[:TOP_LOOPS]
        loop_flow = sum(s for _, s in loops)
        circ_frac = min(1.0, loop_flow / net) if net > 1e-9 else 0.0

        asc = sum(f for (u, v), f in A.items()
                  if f > 0 and _AXIS_ORDER[v] > _AXIS_ORDER[u])
        desc = sum(f for (u, v), f in A.items()
                   if f > 0 and _AXIS_ORDER[v] < _AXIS_ORDER[u])
        chirality = ((asc - desc) / (asc + desc)) if (asc + desc) > 1e-9 else 0.0

        sources = [u for u in AXES
                   if all(A[(u, v)] >= -eps for v in AXES if v != u)
                   and any(A[(u, v)] > eps for v in AXES)]
        sinks = [u for u in AXES
                 if all(A[(u, v)] <= eps for v in AXES if v != u)
                 and any(A[(u, v)] < -eps for v in AXES)]

        if not loops:
            regime = "gradient"
        elif circ_frac >= 0.25:
            regime = "circulating"
        else:
            regime = "mixed"
        return ToroidalSignature(regime, loops, (net / traffic), circ_frac,
                                 chirality, sources, sinks, obs)

    # ── integration surface ──

    def attach_to_record(self, record: Dict[str, Any],
                         key: str = "toroidal_signature") -> Dict[str, Any]:
        """Attach the current signature to any record (ability, state,
        genealogy link) without mutating anything else. Returns the
        same dict for chaining."""
        try:
            record[key] = self.current_signature().to_dict()
        except Exception:
            pass
        return record

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "observations": self._observations,
                "flux_edges": sum(1 for v in self._flux.values() if v > 1e-6),
                "path": self._path,
            }


# ── Main (self-check against her real lived record) ──────────────────────────

if __name__ == "__main__":
    print("=" * 68)
    print("AURORA TOROIDAL CIRCULATION LAYER  v1")
    print("what is maintaining what is happening")
    print("Authors: Sunni (Sir) Morningstar & Cael Devo")
    print("=" * 68)

    import tempfile, shutil
    src = os.path.join(_default_state_dir(), "surface_pressure_log.jsonl")
    with tempfile.TemporaryDirectory() as td:
        if os.path.exists(src):
            shutil.copy(src, os.path.join(td, "surface_pressure_log.jsonl"))
        tcl = ToroidalCirculationLayer(state_dir=td)
        n = tcl.seed_from_surface_log()
        print(f"\nseeded from lived record: {n} events")
        sig = tcl.current_signature()
        print(f"\nSIGNATURE: regime={sig.regime}  flow_ratio={sig.flow_ratio:.3f}  "
              f"circulation={sig.circulation_fraction:.0%}  chirality={sig.chirality:+.3f}")
        for p, s in sig.loops:
            print(f"  loop: {' → '.join(p)} → {p[0]}   strength={s:.3f}")
        print(f"\nINTERPRETATION:\n  {sig.interpret()}")

        print("\n--- persistence round-trip ---")
        tcl.save()
        tcl2 = ToroidalCirculationLayer(state_dir=td)
        sig2 = tcl2.current_signature()
        print(f"  reloaded regime={sig2.regime}, loops={len(sig2.loops)}, "
              f"similarity to live={sig.similarity(sig2):.3f}")

        print("\n--- equivalence sanity ---")
        quiet = ToroidalSignature("gradient", [], 0.09, 0.0, -0.2, ["N"], ["B"], 100)
        print(f"  vortex vs gradient similarity: {sig.similarity(quiet):.3f} (should be low)")
    print("\nDone.")
