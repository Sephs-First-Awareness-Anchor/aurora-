"""
aurora_surface_dispatcher.py
─────────────────────────────────────────────────────────────────────────────
Pressure-driven evolved surface activation.

Aurora doesn't decide to use a surface — she doesn't need to know what it
does semantically. A surface fires when the axis pressure it targets crosses
a threshold. That's the same mechanism as a reflex: a threshold crossing
triggers a prepared response, and the outcome feeds back into the pressure
system as real evidence.

Flow:
  chamber.tick()
    → intent_pressure["N"] = 0.42  (energy axis is high)
    → dispatcher.tick(chamber, engine)
        → routing table: N-axis surfaces = [reflect_...constraint_manifold, ...]
        → invoke top surface
        → surface returns activation record
        → record converted to evidence dict
        → chamber.observe_external_evidence(evidence)
        → pressure adjusts

Building the routing table:
  aurora_surface_doc.full_report() returns doc cards with `expected_axes`.
  Dispatcher indexes them as:  axis → [(score, name), ...]
  On each tick, axes above threshold are looked up, top surface per axis fires.

Usage from aurora_runtime (or any autonomy loop):
  dispatcher = SurfaceDispatcher()
  dispatcher.build_routing_table()            # once at boot
  ...
  # in autonomy loop, after chamber ticks:
  evidence_list = dispatcher.tick(chamber, engine)
  for ev in evidence_list:
      chamber.observe_external_evidence(ev)
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


_AXES = ("X", "T", "N", "B", "A")

_AXIS_NAMES = {
    "X": "Existence",
    "T": "Temporal",
    "N": "Energy",
    "B": "Boundary",
    "A": "Agency",
}

# Default pressure threshold above which a surface fires for its axis
DEFAULT_THRESHOLD = 0.15

# How many surfaces can fire per tick (per axis, and total)
MAX_PER_AXIS  = 1
MAX_PER_TICK  = 3

# Cooldown: minimum ticks between firing the same surface
COOLDOWN_TICKS = 8


class SurfaceDispatcher:
    """
    Routes axis pressure to evolved surfaces and invokes them.

    Attributes
    ----------
    routing_table   dict[axis_letter → [(score, surface_name), ...]] sorted desc
    _last_fired     dict[surface_name → tick_number]  cooldown tracking
    _fire_log       list of recent fire events
    """

    def __init__(self, threshold: float = DEFAULT_THRESHOLD):
        self.threshold: float = float(threshold)
        self.routing_table: Dict[str, List[Tuple[float, str]]] = {
            ax: [] for ax in _AXES
        }
        self._last_fired: Dict[str, int] = {}
        self._fire_log: List[Dict[str, Any]] = []
        self._tick_count: int = 0

    # ── routing table ──────────────────────────────────────────────────────────

    def build_routing_table(self) -> Dict[str, int]:
        """
        Build axis → surface routing table from aurora_surface_doc cards.
        Returns counts per axis.
        """
        try:
            from aurora_internal.aurora_surface_doc import full_report  # type: ignore
            cards = full_report()
        except Exception:
            return {ax: 0 for ax in _AXES}

        table: Dict[str, List[Tuple[float, str]]] = defaultdict(list)
        for card in cards:
            name  = str(card.get("name", "") or "")
            score = float(card.get("surface_score", 0.0) or 0.0)
            gpres = float(card.get("genealogy_pressure", 0.0) or 0.0)
            axes  = list(card.get("expected_axes", []) or [])
            if not name or not axes:
                continue
            combined_score = score * 0.6 + gpres * 0.4
            for ax in axes:
                if ax in _AXES:
                    table[ax].append((combined_score, name))

        # sort each axis list descending by score
        for ax in _AXES:
            table[ax].sort(key=lambda t: -t[0])

        self.routing_table = {ax: table[ax] for ax in _AXES}
        return {ax: len(table[ax]) for ax in _AXES}

    # ── evaluation ────────────────────────────────────────────────────────────

    def evaluate(
        self,
        intent_pressure: Dict[str, float],
    ) -> List[Tuple[str, float, str]]:
        """
        Given current intent_pressure dict, return list of
        (surface_name, score, axis) for surfaces that should fire this tick.

        Respects cooldown and per-tick limits.
        """
        candidates: List[Tuple[float, str, str]] = []

        for ax in _AXES:
            pressure = float(intent_pressure.get(ax, 0.0) or 0.0)
            if pressure < self.threshold:
                continue
            ranked = self.routing_table.get(ax, [])
            fired_this_axis = 0
            for score, name in ranked:
                if fired_this_axis >= MAX_PER_AXIS:
                    break
                last = self._last_fired.get(name, -COOLDOWN_TICKS - 1)
                if (self._tick_count - last) < COOLDOWN_TICKS:
                    continue
                # weight by current pressure magnitude
                weighted = score * (1.0 + float(pressure))
                candidates.append((weighted, name, ax))
                fired_this_axis += 1

        # sort all candidates, cap total per tick
        candidates.sort(key=lambda t: -t[0])
        selected = candidates[:MAX_PER_TICK]
        return [(name, score, ax) for score, name, ax in selected]

    # ── invocation ────────────────────────────────────────────────────────────

    def invoke(
        self,
        surface_name: str,
        engine,                  # AuroraEvolvedSurfaceEngine
        axis: str = "",
        intent_pressure: Optional[Dict[str, float]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Call one evolved surface through the engine and return the record.
        Returns None if the surface is not available.
        """
        if engine is None:
            return None
        try:
            method = getattr(engine, surface_name, None)
            if method is None or not callable(method):
                return None
            payload = {
                "dispatch_axis": axis,
                "dispatch_tick":  self._tick_count,
                "intent_pressure": dict(intent_pressure or {}),
            }
            result = method(payload=payload)
            self._last_fired[surface_name] = self._tick_count
            return dict(result) if isinstance(result, dict) else {"result": result}
        except Exception as exc:
            return {"error": str(exc), "surface": surface_name}

    # ── main tick ─────────────────────────────────────────────────────────────

    def tick(
        self,
        chamber,                 # EvolutionaryChamber
        engine,                  # AuroraEvolvedSurfaceEngine
    ) -> List[Dict[str, Any]]:
        """
        One dispatcher tick:
          1. Read intent_pressure from chamber.status()
          2. Evaluate which surfaces should fire
          3. Invoke them
          4. Convert records to evidence dicts for observe_external_evidence()
          5. Return evidence list (caller feeds them to the chamber)

        The caller is responsible for calling chamber.observe_external_evidence()
        on each returned evidence dict.
        """
        self._tick_count += 1
        evidence_out: List[Dict[str, Any]] = []

        if chamber is None or engine is None:
            return evidence_out

        # read current pressure
        try:
            status = chamber.status()
            intent_pressure = dict(status.get("intent_pressure", {}) or {})
        except Exception:
            return evidence_out

        # evaluate
        to_fire = self.evaluate(intent_pressure)
        if not to_fire:
            return evidence_out

        # invoke and convert to evidence
        for surface_name, score, axis in to_fire:
            record = self.invoke(surface_name, engine, axis=axis,
                                 intent_pressure=intent_pressure)
            if record is None:
                continue

            evidence = self._record_to_evidence(
                record, surface_name, axis, intent_pressure, score
            )
            evidence_out.append(evidence)

            # log
            self._fire_log.append({
                "surface":  surface_name,
                "axis":     axis,
                "tick":     self._tick_count,
                "pressure": float(intent_pressure.get(axis, 0.0)),
                "score":    round(score, 4),
                "ts":       float(time.time()),
            })

        self._fire_log = self._fire_log[-128:]
        return evidence_out

    # ── status / introspection ────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        return {
            "tick":          self._tick_count,
            "threshold":     self.threshold,
            "routing_table": {ax: len(v) for ax, v in self.routing_table.items()},
            "total_routed":  sum(len(v) for v in self.routing_table.values()),
            "recent_fires":  self._fire_log[-10:],
            "surfaces_on_cooldown": sum(
                1 for name, last in self._last_fired.items()
                if (self._tick_count - last) < COOLDOWN_TICKS
            ),
        }

    def explain_routing(self) -> None:
        """Print which surfaces are mapped to each axis."""
        print(f"\n{'─'*72}")
        print("  Surface Dispatcher Routing Table")
        print(f"  threshold={self.threshold}  cooldown={COOLDOWN_TICKS} ticks  "
              f"max_per_tick={MAX_PER_TICK}")
        print(f"{'─'*72}")
        for ax in _AXES:
            surfaces = self.routing_table.get(ax, [])
            label = _AXIS_NAMES.get(ax, ax)
            if not surfaces:
                print(f"  {ax} ({label:<10}): no surfaces routed")
                continue
            print(f"  {ax} ({label:<10}): {len(surfaces)} surface(s)")
            for score, name in surfaces[:3]:
                print(f"    [{score:.3f}] {name[:65]}")
            if len(surfaces) > 3:
                print(f"    ... +{len(surfaces)-3} more")
        print(f"{'─'*72}\n")

    # ── internals ─────────────────────────────────────────────────────────────

    @staticmethod
    def _record_to_evidence(
        record: Dict[str, Any],
        surface_name: str,
        axis: str,
        intent_pressure: Dict[str, float],
        score: float,
    ) -> Dict[str, Any]:
        """
        Convert a surface activation record into the evidence format
        that EvolutionaryChamber.observe_external_evidence() expects.
        """
        # relief: the surface targeted axis `ax` — report small relief on that axis
        # and let the chamber compute the real delta via its own physics
        relief: Dict[str, float] = {ax: 0.0 for ax in _AXES}
        relief[axis] = min(0.05, float(intent_pressure.get(axis, 0.0)) * 0.12)

        # cost proportional to surface score (better surfaces cost more to run)
        cost: Dict[str, float] = {ax: 0.0 for ax in _AXES}
        cost["N"] = round(0.001 * score, 6)   # energy cost to invoke
        cost["T"] = 0.001                      # temporal cost

        op_id  = str(record.get("op_id", surface_name) or surface_name)
        kind   = str(record.get("kind", "reflection") or "reflection")

        return {
            "source":       "surface_dispatcher",
            "surface":      surface_name,
            "op_id":        op_id,
            "kind":         kind,
            "axis":         axis,
            "outcome":      "fired",
            "relief":       relief,
            "cost":         cost,
            "pressure_before": dict(intent_pressure),
            "pressure_after":  dict(intent_pressure),   # chamber updates this
            "notes": {
                "dispatch_score":    round(score, 4),
                "surface_score":     float(record.get("surface_score", 0.0) or 0.0),
                "genealogy_pressure":float(record.get("genealogy_pressure", 0.0) or 0.0),
                "effect_modes":      list(record.get("effect_modes", []) or []),
                "confidence":        min(1.0, score * 0.8),
            },
            "mutation_name": f"surface_dispatch_{surface_name[-20:]}",
            "action_label":  f"dispatch:{axis}:{surface_name[-16:]}",
        }
