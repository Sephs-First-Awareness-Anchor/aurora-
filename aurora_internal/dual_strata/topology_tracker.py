"""
aurora_internal/dual_strata/topology_tracker.py
==================================================
TopologyTracker — MTSL Phase 1 (2026-07-13), shadow-only topology
observation. Not wired into aurora.py yet (Phase 3's job, when the
coordinator replaces the direct ToroidalCirculationLayer.observe() call
with coordinator ownership of it).

Generalizes ToroidalCirculationLayer's flow machinery
(_antisymmetric / _cycles) into three corrections + one generalization:

1. Balanced flow attribution. The existing TCL.observe() attributes a
   losing axis's ENTIRE loss as flux, proportional to gainers' share of
   total gains -- correct only when losses and gains balance exactly.
   When they don't (a real external pressure injection or drain), TCL
   over-attributes: it invents a donor axis for pressure that was
   actually created, or a receiving axis for pressure that actually
   dissipated. This tracker computes creation/dissipation as the
   unattributable net (matching TopologyFrame.creation_residual /
   dissipation_residual) and only ever attributes transfer_mass =
   min(total losses, total gains) as flux, scaled so a loser/gainer pair
   never carries more mass than the smaller of the two totals allows:
       flux[(loser, gainer)] += loss * gain / max(total_losses, total_gains)
   Summed across all pairs this attributes exactly transfer_mass, never
   more -- verified algebraically for both the net-creation and
   net-dissipation cases (see test_topology_tracker.py).

2. Cycle decomposition without double-counting. TCL's _cycles() lists
   every simple cycle found by DFS -- heavily overlapping when the same
   edges participate in several loops, so summing their strengths
   double-counts shared mass. This tracker instead greedily PEELS: find
   the single strongest cycle (by bottleneck edge, ties broken by
   canonical rotation order), subtract its bottleneck from every edge on
   it, accumulate that bottleneck as cyclic mass, and repeat until no
   cycle clears the noise floor. What's left decomposes into gradient
   flow (direct source-to-sink edges) plus an unattributed residual.

3. Multi-scale windows. Three independently-decaying flux accumulators
   (micro/meso/developmental) sharing the same physics, each producing
   its own TopologySignature. ToroidalCirculationLayer remains the live,
   already-wired developmental-scale engine as-is; this tracker is a
   parallel, not-yet-wired implementation for Phase 1.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from __future__ import annotations

import json
import math
import os
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from aurora_internal.dual_strata.topology_frame import AXES, TopologyFrame

_AXIS_ORDER = {a: i for i, a in enumerate(AXES)}

STATE_FILENAME = "topology_tracker_state.json"
SCHEMA_VERSION = 1

# First-pass calibration (to be tuned from lived history, same posture as
# the directive's own "to be calibrated" note on match thresholds):
# min_observations is the low end of each named range from the directive
# (micro 3-8, meso 20-50, developmental 100-500); half_life_obs is
# roughly that range's center, so accumulated flux decays on a timescale
# matched to the window's intended granularity.
WINDOW_CONFIG: Dict[str, Dict[str, int]] = {
    "micro":         {"min_observations": 3,   "half_life_obs": 5},
    "meso":          {"min_observations": 20,  "half_life_obs": 35},
    "developmental": {"min_observations": 100, "half_life_obs": 300},
}
WINDOW_SCALES: Tuple[str, ...] = tuple(WINDOW_CONFIG.keys())

CYCLE_EPS_FRACTION = 0.004   # loop edge floor, as fraction of accumulated traffic (matches TCL)
MAX_CYCLE_LEN = 5            # up to the full X...A loop
TOP_LOOPS = 5                # loops retained as human-readable descriptors


def _canon(path: Sequence[str]) -> Tuple[str, ...]:
    """Rotation-invariant canonical form of a directed loop."""
    p = tuple(path)
    if not p:
        return p
    k = p.index(min(p))
    return p[k:] + p[:k]


# ── Signature (TS -- observed organization over a window) ─────────────────────

@dataclass(frozen=True)
class TopologySignature:
    """
    Observed organization over one window scale: edges, loops, sources,
    sinks, residuals, persistence. Distinct from (and a superset of the
    concerns of) the existing ToroidalSignature -- see the directive's
    vocabulary table: "signature" unqualified is banned in new code.
    """
    schema_version: int
    window_scale: str
    regime: str                                    # "quiescent" | "gradient" | "circulating" | "mixed"
    loops: Tuple[Tuple[Tuple[str, ...], float], ...]  # peeled loops: (axis-path, bottleneck mass)
    cyclic_mass: float
    gradient_mass: float
    residual_mass: float
    circulation_fraction: float                     # cyclic / (cyclic + gradient + residual)
    sources: Tuple[str, ...]
    sinks: Tuple[str, ...]
    persistence: int                                # consecutive observations with the same dominant loop
    observations: int
    updated_at: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "window_scale": self.window_scale,
            "regime": self.regime,
            "loops": [{"path": list(p), "strength": round(s, 4)} for p, s in self.loops],
            "cyclic_mass": round(self.cyclic_mass, 4),
            "gradient_mass": round(self.gradient_mass, 4),
            "residual_mass": round(self.residual_mass, 4),
            "circulation_fraction": round(self.circulation_fraction, 4),
            "sources": list(self.sources),
            "sinks": list(self.sinks),
            "persistence": int(self.persistence),
            "observations": int(self.observations),
            "updated_at": self.updated_at,
        }


# ── Fingerprint (spec §8) ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class TopologyFingerprint:
    """
    Deterministic, versioned, quantized identity for a TopologySignature
    -- used for indexing (semantic_variant_registry matching, Phase 2),
    never for exact-value comparisons. ivm_phase is excluded by
    construction: this class only ever reads from a TopologySignature,
    which never carries ivm_phase (P3 -- IVM geometry is representation,
    never evidence that circulation occurred).
    """
    schema_version: int
    axes_key: str
    loops_key: str
    bands_key: str
    fingerprint_id: str

    @classmethod
    def from_signature(cls, sig: TopologySignature, *, bands: int = 5) -> "TopologyFingerprint":
        axes_in_loops = sorted({a for path, _ in sig.loops for a in path})
        axes_key = "".join(axes_in_loops) or "-"

        loop_parts = []
        for path, strength in sig.loops[:TOP_LOOPS]:
            band = _quantize(strength, bands=bands, lo=0.0, hi=max(strength, 1e-9))
            loop_parts.append("".join(path) + str(band))
        loops_key = "+".join(loop_parts) or "-"

        band_cf = _quantize(sig.circulation_fraction, bands=bands, lo=0.0, hi=1.0)
        bands_key = f"cf{band_cf}"

        fingerprint_id = f"TS:{axes_key}:{loops_key}:{bands_key}:v{sig.schema_version}"
        return cls(
            schema_version=sig.schema_version,
            axes_key=axes_key,
            loops_key=loops_key,
            bands_key=bands_key,
            fingerprint_id=fingerprint_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "axes_key": self.axes_key,
            "loops_key": self.loops_key,
            "bands_key": self.bands_key,
            "fingerprint_id": self.fingerprint_id,
        }


def _quantize(value: float, *, bands: int, lo: float, hi: float) -> int:
    """Bucket a float into one of `bands` bands over [lo, hi]. Quantizing
    (rather than hashing the raw float) is what makes the fingerprint
    stable under small noise -- two nearby values land in the same band."""
    span = max(1e-9, hi - lo)
    frac = max(0.0, min(1.0, (value - lo) / span))
    band = int(frac * bands)
    return min(bands - 1, band)


# ── One window's flow physics ──────────────────────────────────────────────────

class _FlowWindow:
    """One scale's decaying flux accumulator + balanced attribution +
    greedy-peel cycle decomposition. Shared by all three WINDOW_SCALES."""

    def __init__(self, scale: str) -> None:
        cfg = WINDOW_CONFIG[scale]
        self.scale = scale
        self._min_observations = int(cfg["min_observations"])
        self._decay_per_obs = math.exp(-math.log(2.0) / max(1, int(cfg["half_life_obs"])))
        self._flux: Dict[Tuple[str, str], float] = {}
        self._observations = 0
        self._last_dominant_loop: Optional[Tuple[str, ...]] = None
        self._persistence = 0

    def to_state(self) -> Dict[str, Any]:
        return {
            "observations": self._observations,
            "flux": {f"{u}>{v}": round(f, 6) for (u, v), f in self._flux.items() if f > 1e-6},
            "last_dominant_loop": list(self._last_dominant_loop) if self._last_dominant_loop else None,
            "persistence": self._persistence,
        }

    @classmethod
    def from_state(cls, scale: str, state: Dict[str, Any]) -> "_FlowWindow":
        w = cls(scale)
        w._observations = int(state.get("observations", 0) or 0)
        for k, v in dict(state.get("flux", {}) or {}).items():
            u, _, v2 = str(k).partition(">")
            if u in AXES and v2 in AXES:
                w._flux[(u, v2)] = float(v)
        ldl = state.get("last_dominant_loop")
        w._last_dominant_loop = tuple(ldl) if ldl else None
        w._persistence = int(state.get("persistence", 0) or 0)
        return w

    def observe(self, delta_vector: Dict[str, float]) -> None:
        self._observations += 1
        for k in list(self._flux):
            self._flux[k] *= self._decay_per_obs

        losers = [(a, -delta_vector.get(a, 0.0)) for a in AXES if delta_vector.get(a, 0.0) < 0]
        gainers = [(a, delta_vector.get(a, 0.0)) for a in AXES if delta_vector.get(a, 0.0) > 0]
        total_losses = sum(x for _, x in losers)
        total_gains = sum(x for _, x in gainers)
        if not losers or not gainers:
            return
        denom = max(total_losses, total_gains)
        if denom <= 1e-12:
            return
        for lu, lv in losers:
            for gu, gv in gainers:
                self._flux[(lu, gu)] = self._flux.get((lu, gu), 0.0) + (lv * gv) / denom

    def _antisymmetric(self) -> Dict[Tuple[str, str], float]:
        return {(u, v): self._flux.get((u, v), 0.0) - self._flux.get((v, u), 0.0)
                for u in AXES for v in AXES}

    def _strongest_cycle(
        self, A: Dict[Tuple[str, str], float], eps: float,
    ) -> Optional[Tuple[Tuple[str, ...], float]]:
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
        if not found:
            return None
        deduped = [c for c in found if c[0][0] == min(c[0])]
        if not deduped:
            return None
        deduped.sort(key=lambda c: (-c[1], _canon(c[0])))
        return deduped[0]

    def _peel_cycles(
        self, A: Dict[Tuple[str, str], float], eps: float,
    ) -> Tuple[List[Tuple[Tuple[str, ...], float]], float, Dict[Tuple[str, str], float]]:
        """Deterministic greedy peeling: repeatedly remove the single
        strongest cycle's bottleneck mass from every edge on it, so
        shared edges are never double-counted across multiple loops."""
        remainder = dict(A)
        peeled: List[Tuple[Tuple[str, ...], float]] = []
        cyclic_mass = 0.0
        while len(peeled) < TOP_LOOPS:
            cyc = self._strongest_cycle(remainder, eps)
            if cyc is None:
                break
            path, bottleneck = cyc
            if bottleneck <= eps:
                break
            for i in range(len(path)):
                u, v = path[i], path[(i + 1) % len(path)]
                remainder[(u, v)] = remainder.get((u, v), 0.0) - bottleneck
            peeled.append((path, bottleneck))
            cyclic_mass += bottleneck
        return peeled, cyclic_mass, remainder

    def signature(self) -> TopologySignature:
        traffic = sum(v for v in self._flux.values())
        A = self._antisymmetric()
        obs = self._observations

        if obs < self._min_observations or traffic <= 1e-9:
            return TopologySignature(
                schema_version=SCHEMA_VERSION, window_scale=self.scale, regime="quiescent",
                loops=(), cyclic_mass=0.0, gradient_mass=0.0, residual_mass=0.0,
                circulation_fraction=0.0, sources=(), sinks=(), persistence=0,
                observations=obs, updated_at=time.time(),
            )

        eps = max(1e-6, CYCLE_EPS_FRACTION * traffic)
        peeled, cyclic_mass, remainder = self._peel_cycles(A, eps)

        sources = tuple(u for u in AXES
                        if all(remainder.get((u, v), 0.0) >= -eps for v in AXES if v != u)
                        and any(remainder.get((u, v), 0.0) > eps for v in AXES))
        sinks = tuple(u for u in AXES
                     if all(remainder.get((u, v), 0.0) <= eps for v in AXES if v != u)
                     and any(remainder.get((u, v), 0.0) < -eps for v in AXES))

        remainder_net = sum(f for (u, v), f in remainder.items()
                            if f > eps and _AXIS_ORDER[u] < _AXIS_ORDER[v])
        gradient_mass = sum(remainder.get((u, v), 0.0) for u in sources for v in sinks
                            if remainder.get((u, v), 0.0) > eps)
        residual_mass = max(0.0, remainder_net - gradient_mass)

        denom = cyclic_mass + gradient_mass + residual_mass
        circ_frac = (cyclic_mass / denom) if denom > 1e-9 else 0.0

        dominant = peeled[0][0] if peeled else None
        dominant_canon = _canon(dominant) if dominant else None
        prior_canon = _canon(self._last_dominant_loop) if self._last_dominant_loop else None
        if dominant_canon is not None and dominant_canon == prior_canon:
            self._persistence += 1
        elif dominant_canon is not None:
            self._persistence = 1
        else:
            self._persistence = 0
        self._last_dominant_loop = dominant

        if not peeled:
            regime = "gradient"
        elif circ_frac >= 0.25:
            regime = "circulating"
        else:
            regime = "mixed"

        return TopologySignature(
            schema_version=SCHEMA_VERSION, window_scale=self.scale, regime=regime,
            loops=tuple(peeled), cyclic_mass=cyclic_mass, gradient_mass=gradient_mass,
            residual_mass=residual_mass, circulation_fraction=circ_frac,
            sources=sources, sinks=sinks, persistence=self._persistence,
            observations=obs, updated_at=time.time(),
        )


# ── The tracker ──────────────────────────────────────────────────────────────

class TopologyTracker:
    """
    Idempotent multi-scale observer. observe(frame) is a no-op if
    frame.turn_id was already the last-observed turn_id (prevents the
    dual-runtime-path double-tick FIX-A011 warns about, once a
    coordinator routes both paths through one tracker in Phase 3).
    """

    def __init__(self, state_dir: Optional[str] = None) -> None:
        self._state_dir = str(state_dir) if state_dir else None
        self._path = os.path.join(self._state_dir, STATE_FILENAME) if self._state_dir else None
        self._lock = threading.Lock()
        self._windows: Dict[str, _FlowWindow] = {scale: _FlowWindow(scale) for scale in WINDOW_SCALES}
        self.last_observed_turn_id: Optional[str] = None
        self._dirty = False
        if self._path:
            self._load()

    # ── persistence ──

    def _load(self) -> None:
        try:
            if not os.path.exists(self._path):
                return
            with open(self._path, encoding="utf-8") as fh:
                raw = json.load(fh)
            if not isinstance(raw, dict):
                return
            self.last_observed_turn_id = raw.get("last_observed_turn_id")
            windows = raw.get("windows", {}) or {}
            for scale in WINDOW_SCALES:
                if scale in windows:
                    self._windows[scale] = _FlowWindow.from_state(scale, windows[scale])
        except Exception:
            pass

    def save(self) -> bool:
        if not self._path:
            return False
        with self._lock:
            if not self._dirty:
                return False
            try:
                os.makedirs(self._state_dir, exist_ok=True)
                payload = {
                    "schema_version": SCHEMA_VERSION,
                    "last_observed_turn_id": self.last_observed_turn_id,
                    "windows": {scale: w.to_state() for scale, w in self._windows.items()},
                    "saved_at": time.time(),
                }
                tmp = self._path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, indent=1)
                os.replace(tmp, self._path)
                self._dirty = False
                return True
            except Exception:
                return False

    # ── observation ──

    def observe(self, frame: TopologyFrame) -> bool:
        """Returns True if this frame was newly observed, False if it was
        a duplicate turn_id (idempotency -- FIX-A011)."""
        with self._lock:
            if frame.turn_id and frame.turn_id == self.last_observed_turn_id:
                return False
            for window in self._windows.values():
                window.observe(frame.delta_vector)
            self.last_observed_turn_id = frame.turn_id
            self._dirty = True
        return True

    def signatures(self) -> Dict[str, TopologySignature]:
        return {scale: window.signature() for scale, window in self._windows.items()}

    def signature(self, scale: str) -> TopologySignature:
        return self._windows[scale].signature()

    def fingerprints(self) -> Dict[str, TopologyFingerprint]:
        return {scale: TopologyFingerprint.from_signature(sig)
                for scale, sig in self.signatures().items()}

    # ── replay ──

    @classmethod
    def from_frames(cls, frames: Sequence[TopologyFrame], state_dir: Optional[str] = None) -> "TopologyTracker":
        tracker = cls(state_dir=None)  # replay builds in memory; caller saves if desired
        for frame in sorted(frames, key=lambda f: f.timestamp):
            tracker.observe(frame)
        if state_dir:
            tracker._state_dir = str(state_dir)
            tracker._path = os.path.join(tracker._state_dir, STATE_FILENAME)
        return tracker
