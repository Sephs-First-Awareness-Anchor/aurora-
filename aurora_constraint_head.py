"""
ConstraintHead — the computational address register of Aurora's Constraint Physics Machine.

The head maps the IVM's current global polarity state to a crystal-registry address.
As IVM toroidal dynamics evolve, the head moves through crystal space automatically —
no explicit head movement is needed. Computation IS physics.

IVM axis names → crystal axis keys:
    'existence' → 'X'
    'temporal'  → 'T'
    'energy'    → 'N'
    'boundary'  → 'B'
    'agency'    → 'A'

IVM global_polarity is signed [-1.0, +1.0] (cosine of toroidal phase).
Crystal bucket addressing uses [0.0, 1.0]. Mapping: (polarity + 1.0) / 2.0
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple
from collections import deque

_IVM_TO_AXIS: Dict[str, str] = {
    'existence': 'X',
    'temporal':  'T',
    'energy':    'N',
    'boundary':  'B',
    'agency':    'A',
}

_HISTORY_DEPTH = 64


@dataclass
class HeadPosition:
    """A single snapshot of the head's location in crystal space."""
    bucket:     Tuple[float, ...]       # 5-tuple (X,T,N,B,A) quantised to 0.10
    axis_state: Dict[str, float]        # raw [0,1] values before quantisation
    crystal:    Optional[Any]           # ConceptCrystalNode at this address, or None
    tick:       int                     # CPM tick counter when this was recorded


class ConstraintHead:
    """
    Tracks the current computational address in crystal space by reading the
    IVM global polarity each advance() call.

    Requires:
        ivm              — IVMLattice instance (exposes get_global_polarity())
        crystal_registry — ConceptCrystalRegistry instance (exposes query() and _to_bucket())
    """

    def __init__(self, ivm: Any, crystal_registry: Any) -> None:
        self._ivm      = ivm
        self._registry = crystal_registry
        self._history: Deque[HeadPosition] = deque(maxlen=_HISTORY_DEPTH)
        self._current: Optional[HeadPosition] = None
        self._tick: int = 0

    # ------------------------------------------------------------------
    # Core

    def advance(self) -> HeadPosition:
        """
        Read IVM global polarity → translate to 5D axis state → map to
        nearest crystal → return HeadPosition.

        Does NOT create crystals. The head is a read-only cursor over the
        existing crystal landscape; new crystal formation is a side-effect
        of normal synthesis, not of address lookup.
        """
        polarity: Dict[str, float] = self._ivm.get_global_polarity()

        # Translate IVM long-axis names and map from [-1,1] → [0,1]
        axes: Dict[str, float] = {}
        for ivm_key, axis_key in _IVM_TO_AXIS.items():
            raw = polarity.get(ivm_key, 0.0)
            axes[axis_key] = (raw + 1.0) / 2.0

        # Bucket key via the registry's own static method
        try:
            from concept_crystal import ConceptCrystalRegistry
            bucket = ConceptCrystalRegistry._to_bucket(axes)
        except Exception:
            bucket = tuple(round(axes.get(k, 0.5) / 0.10) * 0.10 for k in ("X", "T", "N", "B", "A"))

        crystal = self._registry.query(axes)

        self._tick += 1
        pos = HeadPosition(bucket=bucket, axis_state=axes, crystal=crystal, tick=self._tick)

        if self._current is not None:
            self._history.append(self._current)
        self._current = pos
        return pos

    # ------------------------------------------------------------------
    # Properties

    @property
    def current(self) -> Optional[HeadPosition]:
        return self._current

    @property
    def has_moved(self) -> bool:
        """True if the bucket address changed on the last advance()."""
        if not self._history or self._current is None:
            return False
        return self._history[-1].bucket != self._current.bucket

    @property
    def trace(self) -> List[HeadPosition]:
        """Ordered sequence of visited positions, oldest first, including current."""
        result = list(self._history)
        if self._current is not None:
            result.append(self._current)
        return result

    @property
    def tick(self) -> int:
        return self._tick

    # ------------------------------------------------------------------
    # Address helpers

    def address(self) -> Optional[Tuple[float, ...]]:
        """Current crystal address as a 5-tuple bucket key, or None before first advance()."""
        return self._current.bucket if self._current else None

    def crystal_stage(self) -> Optional[str]:
        """Stage of the crystal at the current address ('base'/'composite'/etc.), or None."""
        if self._current and self._current.crystal:
            return getattr(self._current.crystal, 'stage', None)
        return None

    def at_known_crystal(self) -> bool:
        """True if the current address has an existing crystal."""
        return self._current is not None and self._current.crystal is not None

    def dominant_axis(self) -> Optional[str]:
        """Which of the 5 axes has the highest value at the current address."""
        if not self._current:
            return None
        axes = self._current.axis_state
        return max(axes, key=lambda k: axes[k]) if axes else None

    def recursion_depth(self) -> int:
        """
        Infer recursion depth (0–4) from current axis state.
        High A (agency) + B (boundary) → deeper deliberate processing.
        Low A + B → surface reactive.
        Matches IVM sea-anemone model: SURFACE tips react; CORE steers.
        """
        if not self._current:
            return 0
        axes = self._current.axis_state
        depth_signal = (axes.get('A', 0.5) + axes.get('B', 0.5)) / 2.0
        if depth_signal > 0.85:
            return 4   # CORE
        elif depth_signal > 0.70:
            return 3   # DEEP
        elif depth_signal > 0.55:
            return 2   # MODERATE
        elif depth_signal > 0.35:
            return 1   # SHALLOW
        return 0       # SURFACE

    # ------------------------------------------------------------------
    # Diagnostics

    def status(self) -> Dict[str, Any]:
        pos = self._current
        return {
            'tick':           self._tick,
            'address':        pos.bucket if pos else None,
            'crystal_stage':  self.crystal_stage(),
            'axis_state':     pos.axis_state if pos else None,
            'dominant_axis':  self.dominant_axis(),
            'recursion_depth': self.recursion_depth(),
            'has_moved':      self.has_moved,
            'at_known_crystal': self.at_known_crystal(),
            'history_len':    len(self._history),
        }
