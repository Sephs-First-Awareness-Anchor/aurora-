"""
aurora_manifold_directory.noncomp_field
========================================
Runtime NoncompField — the King Quasicrystal (125 noncomps × 625 slots).

Backed by the JSON files in aurora_manifold_directory/.  Maintains a live
pressure state per axis and per noncomp position.  This is what the
consciousness engine gates (emotion / reasoning / thought / reflection /
understanding) read to decide whether constraint physics have produced
enough pressure to allow an emergent function to fire.

Interface expected by aurora.py and aurora_consciousness_engine.py:
  get_field()                                    → NoncompField singleton
  field.ingest_sensory_event(modality, **kw)     → update axis pressure
  field.ingest_external_input(axes_dict, **kw)   → update axis pressure
  field.axis_pressure(axis_int)                  → float
  field.all_profiles()                           → Iterable[NoncompProfile]
  field.diagonal_profiles()                      → Iterable[NoncompProfile]
  field.status()                                 → dict
  field.reset_pressure_topology(understanding)   → None (pressure decay)
"""
from __future__ import annotations

import json
import os
import math
import threading
from dataclasses import dataclass, field as dc_field
from typing import Dict, Iterator, List, Optional

# ── Axis / dimension mappings ────────────────────────────────────────────────
_AXIS_STR_TO_INT: Dict[str, int] = {"X": 0, "T": 1, "N": 2, "B": 3, "A": 4}
_AXIS_INT_TO_STR: Dict[int, str] = {v: k for k, v in _AXIS_STR_TO_INT.items()}
_DIM_STR_TO_INT:  Dict[str, int] = {
    "OPERATOR": 0, "POLARITY": 1, "MAGNITUDE": 2, "COST": 3, "DIFFERENCE": 4,
}

# Sensory modality → weighted axis contributions (must sum to 1.0)
_MODALITY_AXES: Dict[str, Dict[str, float]] = {
    "visual":         {"X": 0.45, "B": 0.30, "N": 0.10, "T": 0.10, "A": 0.05},
    "auditory":       {"T": 0.40, "B": 0.35, "X": 0.10, "N": 0.10, "A": 0.05},
    "language":       {"B": 0.35, "A": 0.25, "T": 0.20, "N": 0.12, "X": 0.08},
    "internal":       {"N": 0.45, "A": 0.30, "T": 0.15, "B": 0.05, "X": 0.05},
    "spatial":        {"X": 0.50, "B": 0.25, "T": 0.10, "N": 0.10, "A": 0.05},
    # Physical body state — battery depletion and device power.
    # N-axis dominant: low energy = high cost signal. X-axis secondary:
    # power level directly affects presence strength.
    "body_power":     {"N": 0.55, "X": 0.25, "T": 0.12, "B": 0.05, "A": 0.03},
    # Screen as self-surface — own interface is presence (X) and agency (A).
    "screen":         {"X": 0.48, "A": 0.25, "T": 0.15, "B": 0.08, "N": 0.04},
    # Screen visual properties (brightness, motion, density) — like visual.
    "screen_visual":  {"X": 0.45, "B": 0.30, "N": 0.10, "T": 0.10, "A": 0.05},
    # Screen information content from other apps — like language (boundary/meaning).
    "screen_info":    {"B": 0.35, "A": 0.25, "T": 0.20, "N": 0.12, "X": 0.08},
    # Proprioceptive body sense — motion, acceleration, physical continuity.
    "proprioceptive": {"T": 0.38, "X": 0.28, "N": 0.18, "A": 0.12, "B": 0.04},
    "default":        {"X": 0.20, "T": 0.20, "N": 0.20, "B": 0.20, "A": 0.20},
}

_DATA_DIR = os.path.dirname(os.path.abspath(__file__))
_INDEX_PATH = os.path.join(_DATA_DIR, "_index.json")

_SINGLETON: Optional["NoncompField"] = None
_SINGLETON_LOCK = threading.Lock()


@dataclass
class _ProfileKey:
    nc_law_c: int  # row axis int (0–4)
    nc_dim:   int  # dimension int (0–4)
    nc_target: int  # column axis int (0–4)
    nc_name:  str  = ""
    diagonal: bool = False


class NoncompProfile:
    """
    Live pressure tracker for one of the 125 noncomp positions.
    Data from the corresponding JSON file is loaded lazily.
    """
    __slots__ = ("key", "_loaded", "_pressure", "_tension", "_slots", "_file")

    def __init__(self, key: _ProfileKey, file_rel: str) -> None:
        self.key       = key
        self._loaded   = False
        self._pressure = 0.0  # current constraint pressure
        self._tension  = 0.5  # distance from equilibrium (0=at rest, 1=max)
        self._slots: List[dict] = []
        self._file = os.path.join(_DATA_DIR, file_rel)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        try:
            with open(self._file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self._slots = data.get("slots", [])
            self._loaded = True
        except Exception:
            self._loaded = False

    def mean_pressure(self) -> float:
        return self._pressure

    def surface_expression(self) -> dict:
        return {"tension": self._tension, "pressure": self._pressure}

    def apply_pressure(self, delta: float) -> None:
        self._pressure = max(0.0, min(1.0, self._pressure + delta))
        # Tension is how far from equilibrium — increases with pressure
        self._tension = abs(self._pressure - 0.1)

    def decay(self, rate: float = 0.15) -> None:
        self._pressure = max(0.0, self._pressure * (1.0 - rate))
        self._tension  = abs(self._pressure - 0.1)


class NoncompField:
    """
    King Quasicrystal — the live identity field backing Aurora's cognition.

    125 NoncompProfile objects indexed by (nc_law_c, nc_dim, nc_target).
    Axis pressure is the aggregate constraint activity across the field.
    """

    def __init__(self) -> None:
        self._lock     = threading.Lock()
        self._profiles: List[NoncompProfile] = []
        self._by_axis: Dict[int, List[NoncompProfile]] = {i: [] for i in range(5)}
        self._axis_p:  Dict[int, float] = {i: 0.10 for i in range(5)}  # resting
        self._loaded_count = 0
        self._boot_done    = False
        self._load_index()

    def _load_index(self) -> None:
        try:
            with open(_INDEX_PATH, "r", encoding="utf-8") as fh:
                idx = json.load(fh)
            for entry in idx.get("entries", []):
                law_c  = _AXIS_STR_TO_INT.get(entry.get("nc_law_c", "X"), 0)
                dim    = _DIM_STR_TO_INT.get(entry.get("nc_dim", "OPERATOR"), 0)
                target = _AXIS_STR_TO_INT.get(entry.get("nc_target", "X"), 0)
                name   = entry.get("nc_name", "")
                diag   = entry.get("nc_is_diagonal", False)
                fpath  = entry.get("file", "")
                key    = _ProfileKey(nc_law_c=law_c, nc_dim=dim, nc_target=target,
                                     nc_name=name, diagonal=diag)
                prof   = NoncompProfile(key, fpath)
                self._profiles.append(prof)
                for ax_int in (law_c, target):
                    self._by_axis[ax_int].append(prof)
            self._loaded_count = len(self._profiles)
        except Exception as exc:
            # Index unreadable — field is available but empty
            pass

    # ── Public interface ─────────────────────────────────────────────────────

    def ingest_sensory_event(
        self,
        modality: str,
        intensity: float = 0.0,
        novelty:   float = 0.0,
        spatial:   float = 0.0,
        valence:   float = 0.0,
    ) -> None:
        weights = _MODALITY_AXES.get(modality, _MODALITY_AXES["default"])
        effective = max(0.0, min(1.0, intensity))
        with self._lock:
            for ax_str, w in weights.items():
                ax_int = _AXIS_STR_TO_INT[ax_str]
                delta  = w * effective * (1.0 + 0.3 * novelty)
                self._axis_p[ax_int] = min(1.0, self._axis_p[ax_int] + delta * 0.25)
                for prof in self._by_axis[ax_int]:
                    prof.apply_pressure(delta * 0.04)

    def ingest_external_input(
        self,
        axes_dict: Dict[str, float],
        intensity: float = 0.0,
        source:    str   = "",
    ) -> None:
        if not axes_dict:
            return
        effective = max(0.0, min(1.0, intensity))
        with self._lock:
            for ax_str, w in axes_dict.items():
                ax_int = _AXIS_STR_TO_INT.get(str(ax_str))
                if ax_int is None:
                    continue
                delta = float(w or 0.0) * effective
                self._axis_p[ax_int] = min(1.0, self._axis_p[ax_int] + delta * 0.20)
                for prof in self._by_axis[ax_int]:
                    prof.apply_pressure(delta * 0.03)

    def axis_pressure(self, axis: int) -> float:
        return self._axis_p.get(axis, 0.0)

    def all_profiles(self) -> List[NoncompProfile]:
        return self._profiles

    def diagonal_profiles(self) -> List[NoncompProfile]:
        # "Diagonal" = same-axis noncomps (nc_law_c == nc_target across all 5 dims)
        # = 5 axes × 5 dimensions = 25 positions — matches consciousness engine gate.
        return [p for p in self._profiles if p.key.nc_law_c == p.key.nc_target]

    def reset_pressure_topology(self, understanding: dict) -> None:
        resolved = float((understanding or {}).get("resolved_accuracy", 0.5) or 0.5)
        decay_rate = 0.10 + 0.20 * resolved  # resolved understanding → stronger decay
        with self._lock:
            for prof in self._profiles:
                prof.decay(decay_rate)
            for ax_int in self._axis_p:
                self._axis_p[ax_int] = max(0.05, self._axis_p[ax_int] * (1.0 - decay_rate))

    def status(self) -> dict:
        diag_live = sum(1 for p in self.diagonal_profiles() if p._pressure > 0.05)
        return {
            "loaded_count": self._loaded_count,
            "diagonal_live": diag_live,
            "axis_pressures": {
                _AXIS_INT_TO_STR[i]: round(v, 4)
                for i, v in self._axis_p.items()
            },
        }


def get_field() -> NoncompField:
    """Return the module-level NoncompField singleton."""
    global _SINGLETON
    if _SINGLETON is not None:
        return _SINGLETON
    with _SINGLETON_LOCK:
        if _SINGLETON is None:
            _SINGLETON = NoncompField()
    return _SINGLETON
