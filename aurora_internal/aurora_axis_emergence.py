"""
aurora_axis_emergence.py
─────────────────────────────────────────────────────────────────────────────
Compound axis emergence from pressure co-occurrence patterns.

The 5-axis, 625-slot ceiling is broken by allowing new NC channels to emerge
when two axes are consistently co-occurring above a stability threshold.
When X and N are both high in 70%+ of occupied slots, a compound channel
NC:XN>XN is born. That channel pairs with existing channels to create new
virtual slots — which appear as "empty" to the evolver's slot_pressure bonus,
giving it new gradient to evolve toward.

Sources of co-occurrence evidence (used in order of availability):
  1. surface_pressure_log.jsonl  — real runtime axis snapshots
  2. evo_625_pressure_map.json   — axis_pressure per occupied slot

The process compounds: compound axes can themselves form compound axes when
their virtual slots are occupied and their co-occurrence stabilizes. There
is no architectural ceiling — the space expands as long as Aurora produces
novel behavior.

Compound axis naming:
  A pair ("N","B") → compound letter "NB" (sorted, joined)
  NC channel: NC:NB>NB
  Virtual slots: NC:NB>NB×NC:NB>NB, NC:NB>NB×NC:X>X, NC:X>X×NC:NB>NB, ...

Storage: aurora_state/compound_axes.json
  {
    "NB": {
      "axes": ["N", "B"],
      "co_occurrence": 0.74,
      "sample_count": 312,
      "channel": "NC:NB>NB",
      "emerged_at": 1234567890.0,
      "generation": 1,
      "virtual_slots": ["NC:NB>NB×NC:NB>NB", "NC:NB>NB×NC:X>X", ...]
    },
    ...
  }

Usage:
  detector = AxisEmergenceDetector(repo_root)
  result = detector.scan_and_register()
  # result: {"new_compounds": ["NB", "AT"], "total": 3, "virtual_slots_added": 18}
─────────────────────────────────────────────────────────────────────────────
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import json
import math
import os
import time
from itertools import combinations
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

_AXES = ("X", "T", "N", "B", "A")
_ALL_BASE_CHANNELS = tuple(f"NC:{s}>{d}" for s in _AXES for d in _AXES)

_STATE_DIR_REL       = "aurora_state"
_PRESSURE_MAP_REL    = "aurora_state/evo_625_pressure_map.json"
_PRESSURE_LOG_REL    = "aurora_state/surface_pressure_log.jsonl"
_COMPOUND_AXES_REL   = "aurora_state/compound_axes.json"

# A pair must exceed this co-occurrence fraction to form a compound axis
EMERGENCE_THRESHOLD  = 0.65
# Minimum number of observations before we trust a co-occurrence score
MIN_SAMPLE_COUNT     = 30
# Maximum compound axes to register (prevents explosion on first run with noisy data)
MAX_COMPOUNDS        = 20
# Compound axes can themselves compound (generation limit)
MAX_GENERATION       = 3


class AxisEmergenceDetector:
    """
    Detects stable axis co-occurrence patterns and registers compound channels.

    The compound channels become virtual empty pressure slots. The evolver's
    slot_pressure bonus rewards operations that project into those channels,
    organically driving evolution toward the new compound space.
    """

    def __init__(self, repo_root: str):
        self.repo_root = os.path.abspath(repo_root)

    # ── public ────────────────────────────────────────────────────────────────

    def scan_and_register(self) -> Dict[str, Any]:
        """
        Full pipeline: collect evidence → compute co-occurrence → register
        new compound axes → write compound_axes.json.

        Safe to call repeatedly — already-stable compounds are not re-registered.
        Returns a summary dict.
        """
        existing = self._load_compounds()
        existing_keys = set(existing.keys())

        # collect axis pressure observations
        observations = self._collect_observations()
        if not observations:
            return {
                "new_compounds": [],
                "total": len(existing),
                "virtual_slots": self._count_virtual_slots(existing),
                "observations": 0,
            }

        # compute pairwise co-occurrence for base axes
        pairs = self._compute_cooccurrence(observations, _AXES)

        # compute co-occurrence for existing compound axes with base axes
        compound_axes_list = list(existing.keys())
        if compound_axes_list:
            compound_obs = self._compound_observations(observations, existing)
            mixed_pairs  = self._compute_cooccurrence(compound_obs, tuple(compound_axes_list + list(_AXES)))
            pairs.update(mixed_pairs)

        # register new compounds
        new_compounds: List[str] = []
        for (a1, a2), score in sorted(pairs.items(), key=lambda x: -x[1]):
            if len(existing) + len(new_compounds) >= MAX_COMPOUNDS:
                break
            compound_key = "".join(sorted([a1, a2]))
            if compound_key in existing_keys:
                continue
            if score < EMERGENCE_THRESHOLD:
                continue
            count = pairs.get((a1, a2, "_count"), MIN_SAMPLE_COUNT)  # type: ignore[call-overload]
            if isinstance(count, (int, float)) and count < MIN_SAMPLE_COUNT:
                continue

            gen1 = existing.get(a1, {}).get("generation", 0) if a1 not in _AXES else 0
            gen2 = existing.get(a2, {}).get("generation", 0) if a2 not in _AXES else 0
            generation = max(gen1, gen2) + 1
            if generation > MAX_GENERATION:
                continue

            channel = f"NC:{compound_key}>{compound_key}"
            virtual_slots = self._virtual_slots_for(compound_key)
            existing[compound_key] = {
                "axes":          sorted([a1, a2]),
                "co_occurrence": round(float(score), 6),
                "sample_count":  int(len(observations)),
                "channel":       channel,
                "emerged_at":    float(time.time()),
                "generation":    int(generation),
                "virtual_slots": virtual_slots,
            }
            existing_keys.add(compound_key)
            new_compounds.append(compound_key)

        if new_compounds or not os.path.exists(self._path(_COMPOUND_AXES_REL)):
            self._save_compounds(existing)

        return {
            "new_compounds":   new_compounds,
            "total":           len(existing),
            "virtual_slots":   self._count_virtual_slots(existing),
            "observations":    len(observations),
            "pairs_evaluated": len(pairs),
        }

    def load_empty_virtual_channels(self) -> FrozenSet[str]:
        """
        Return the set of NC channels that appear in unoccupied virtual slots.
        Used by the evolver's _empty_slot_channels() to extend the slot space.
        """
        compounds = self._load_compounds()
        if not compounds:
            return frozenset()

        # which compound slots are already filled (have a surface that targets them)?
        # We treat all virtual slots as empty until a surface specifically targets them
        # (the evolver will populate them over time)
        channels: Set[str] = set()
        for comp_data in compounds.values():
            ch = str(comp_data.get("channel", ""))
            if ch:
                channels.add(ch)
            for slot in comp_data.get("virtual_slots", []):
                try:
                    row_ch, col_ch = str(slot).split("×")
                    channels.add(row_ch)
                    channels.add(col_ch)
                except ValueError:
                    pass
        return frozenset(channels)

    def status(self) -> Dict[str, Any]:
        """Return current compound axis registry status."""
        compounds = self._load_compounds()
        obs = self._collect_observations()
        return {
            "compounds":      len(compounds),
            "virtual_slots":  self._count_virtual_slots(compounds),
            "observations":   len(obs),
            "compound_list":  [
                {
                    "key":          k,
                    "axes":         v["axes"],
                    "co_occurrence": v["co_occurrence"],
                    "generation":   v["generation"],
                    "virtual_slots": len(v.get("virtual_slots", [])),
                }
                for k, v in sorted(compounds.items(), key=lambda x: -x[1]["co_occurrence"])
            ],
        }

    # ── observation collection ────────────────────────────────────────────────

    def _collect_observations(self) -> List[Dict[str, float]]:
        """
        Collect axis pressure snapshots from all available sources.
        Returns list of dicts like {"X": 0.6, "T": 0.1, "N": 0.2, "B": 0.05, "A": 0.05}
        """
        obs: List[Dict[str, float]] = []

        # Source 1: surface_pressure_log.jsonl  (runtime snapshots — most reliable)
        log_path = self._path(_PRESSURE_LOG_REL)
        if os.path.exists(log_path):
            try:
                with open(log_path, encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            snap = entry.get("axis_pressure") or entry.get("intent_pressure")
                            if isinstance(snap, dict):
                                row = {ax: float(snap.get(ax, 0.0) or 0.0) for ax in _AXES}
                                obs.append(row)
                        except Exception:
                            pass
            except Exception:
                pass

        # Source 2: evo_625_pressure_map.json  (slot axis_pressure profiles)
        map_path = self._path(_PRESSURE_MAP_REL)
        if os.path.exists(map_path) and len(obs) < MIN_SAMPLE_COUNT:
            try:
                with open(map_path, encoding="utf-8") as fh:
                    pmap = json.load(fh)
                for slot_data in (pmap.get("slots") or {}).values():
                    profile = slot_data.get("profile") if isinstance(slot_data, dict) else slot_data
                    if not isinstance(profile, dict):
                        continue
                    if not profile.get("is_occupied"):
                        continue
                    ap = profile.get("axis_pressure")
                    if isinstance(ap, dict):
                        row = {ax: float(ap.get(ax, 0.0) or 0.0) for ax in _AXES}
                        obs.append(row)
            except Exception:
                pass

        return obs

    # ── co-occurrence computation ─────────────────────────────────────────────

    def _compute_cooccurrence(
        self,
        observations: List[Dict[str, float]],
        axis_keys: Tuple[str, ...],
    ) -> Dict[Tuple[str, str], float]:
        """
        For each pair of axis keys, compute the fraction of observations where
        both axes are simultaneously above their individual medians.

        Returns dict: {(a1, a2): co_occurrence_score}
        """
        if not observations:
            return {}

        n = len(observations)
        # compute per-axis medians
        medians: Dict[str, float] = {}
        for ax in axis_keys:
            vals = sorted(float(obs.get(ax, 0.0) or 0.0) for obs in observations)
            mid = n // 2
            medians[ax] = vals[mid] if vals else 0.0

        result: Dict[Tuple[str, str], float] = {}
        for a1, a2 in combinations(axis_keys, 2):
            m1 = medians.get(a1, 0.0)
            m2 = medians.get(a2, 0.0)
            # count observations where both exceed their median
            both_high = sum(
                1 for obs in observations
                if float(obs.get(a1, 0.0) or 0.0) > m1
                and float(obs.get(a2, 0.0) or 0.0) > m2
            )
            score = round(both_high / max(1, n), 6)
            result[(a1, a2)] = score

        return result

    def _compound_observations(
        self,
        observations: List[Dict[str, float]],
        existing: Dict[str, Any],
    ) -> List[Dict[str, float]]:
        """
        Augment observations with compound axis values (geometric mean of component axes).
        Used to detect higher-order co-occurrences between compounds and base axes.
        """
        augmented = []
        for obs in observations:
            row = dict(obs)
            for comp_key, comp_data in existing.items():
                axes = comp_data.get("axes", [])
                if len(axes) >= 2:
                    vals = [float(obs.get(ax, 0.0) or 0.0) for ax in axes if ax in obs]
                    if vals:
                        row[comp_key] = round(math.prod(v for v in vals) ** (1.0 / len(vals)), 6)
            augmented.append(row)
        return augmented

    # ── virtual slot computation ──────────────────────────────────────────────

    def _virtual_slots_for(self, compound_key: str) -> List[str]:
        """
        Generate virtual NC channel slot pairs for a compound axis.
        Includes: compound×compound, compound×each_base, each_base×compound
        """
        ch = f"NC:{compound_key}>{compound_key}"
        slots = [f"{ch}×{ch}"]
        for base in _AXES:
            base_ch = f"NC:{base}>{base}"
            slots.append(f"{ch}×{base_ch}")
            slots.append(f"{base_ch}×{ch}")
        return slots

    def _count_virtual_slots(self, compounds: Dict[str, Any]) -> int:
        return sum(len(v.get("virtual_slots", [])) for v in compounds.values())

    # ── persistence ───────────────────────────────────────────────────────────

    def _load_compounds(self) -> Dict[str, Any]:
        path = self._path(_COMPOUND_AXES_REL)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_compounds(self, data: Dict[str, Any]) -> None:
        path = self._path(_COMPOUND_AXES_REL)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, sort_keys=True, ensure_ascii=True)
        except Exception:
            pass

    def _path(self, rel: str) -> str:
        return os.path.join(self.repo_root, rel)


# ── module-level convenience ──────────────────────────────────────────────────

def empty_virtual_channels(repo_root: str) -> FrozenSet[str]:
    """
    Return frozenset of NC channels in unoccupied compound virtual slots.
    Drop-in addition to CodeAutoEvolver._empty_slot_channels().
    """
    try:
        return AxisEmergenceDetector(repo_root).load_empty_virtual_channels()
    except Exception:
        return frozenset()


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
    detector = AxisEmergenceDetector(root)
    result = detector.scan_and_register()
    print(json.dumps(result, indent=2))
    print()
    st = detector.status()
    if st["compound_list"]:
        print("Compound axes registered:")
        for c in st["compound_list"]:
            print(f"  {c['key']:6s}  co_occ={c['co_occurrence']:.3f}  "
                  f"gen={c['generation']}  virtual_slots={c['virtual_slots']}")
    else:
        print("No compound axes yet (need more observations).")
