"""
aurora_waveform_pressure.py
============================
Waveform-mediated pressure propagation across the constraint manifold.

Every observation, internal state change, or cognitive event generates a
PressureDisturbance — a localized perturbation in constraint-axis space.
The WaveformPressurePump injects it into the NoncompField (the waveform
substrate) and propagates it through coupling physics.

Propagation follows:
  - Primary injection at source axis amplitudes
  - Coupling propagation: each primary axis drives coupled axes at reduced amplitude
  - Attenuation with each hop (coupling_decay per step)
  - No subsystem is directly targeted — structures self-select participation
    by reading their own pressure state from the manifold

The QuasiArchObserver traces every disturbance for debuggability.

Coupling physics (same as CPM axis coupling):
  X → {T: 0.30, B: 0.20}
  T → {X: 0.25, A: 0.20}
  N → {B: 0.35, T: 0.20, X: 0.15}
  B → {N: 0.30, A: 0.25}
  A → {T: 0.20, B: 0.25, N: 0.15}
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

# Coupling physics — each primary axis drives these coupled axes
_COUPLING: Dict[str, Dict[str, float]] = {
    "X": {"T": 0.30, "B": 0.20},
    "T": {"X": 0.25, "A": 0.20},
    "N": {"B": 0.35, "T": 0.20, "X": 0.15},
    "B": {"N": 0.30, "A": 0.25},
    "A": {"T": 0.20, "B": 0.25, "N": 0.15},
}

# Attenuation applied at each coupling hop
_COUPLING_DECAY = 0.50

_VALID_AXES = frozenset({"X", "T", "N", "B", "A"})


@dataclass
class PressureDisturbance:
    """
    A localized perturbation in the constraint manifold.

    axis_amplitudes: primary axis contributions {X,T,N,B,A} in [0,1]
    intensity: overall event intensity in [0,1]
    coupling_mode:
        "full"         — primary + one coupling hop
        "primary_only" — no coupling propagation
    source: human-readable event identifier for tracing
    genealogy_id: optional genealogy link (influences relevance weighting)
    tick: system tick when this disturbance was created
    """
    source: str
    axis_amplitudes: Dict[str, float]
    intensity: float = 1.0
    coupling_mode: str = "full"
    genealogy_id: str = ""
    tick: int = 0
    ts: float = field(default_factory=time.time)
    propagation_trace: List[Dict[str, Any]] = field(default_factory=list)

    def dominant_axis(self) -> str:
        if not self.axis_amplitudes:
            return "X"
        return max(self.axis_amplitudes, key=self.axis_amplitudes.get)

    def effective_amplitude(self, axis: str) -> float:
        return self.axis_amplitudes.get(axis, 0.0) * max(0.0, min(1.0, self.intensity))


class WaveformPressurePump:
    """
    Injects PressureDisturbances into the NoncompField (identity_field) and
    propagates them through coupling physics.

    Keeps a rolling trace buffer for the QuasiArchObserver.
    """

    def __init__(self, trace_maxlen: int = 64) -> None:
        self._trace_buffer: Deque[Dict[str, Any]] = deque(maxlen=trace_maxlen)

    def inject(
        self,
        disturbance: PressureDisturbance,
        ifield: Any,
        qao: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Apply a PressureDisturbance to ifield via the waveform substrate.

        Returns the full propagation trace for this disturbance.
        qao (AuroraQuasiArchObserver) receives the trace if provided.
        """
        trace: List[Dict[str, Any]] = []

        if ifield is None or not hasattr(ifield, "ingest_external_input"):
            return trace

        intensity = max(0.0, min(1.0, float(disturbance.intensity)))
        if intensity < 1e-6:
            return trace

        # ── 1. Primary injection ──────────────────────────────────────────────
        primary_axes: Dict[str, float] = {}
        for ax, amp in disturbance.axis_amplitudes.items():
            if ax not in _VALID_AXES:
                continue
            eff = float(amp) * intensity
            if eff < 1e-6:
                continue
            primary_axes[ax] = eff

        if primary_axes:
            try:
                ifield.ingest_external_input(
                    primary_axes,
                    intensity=1.0,
                    source=disturbance.source,
                )
            except Exception:
                pass
            for ax, eff in primary_axes.items():
                trace.append({
                    "step": "primary",
                    "axis": ax,
                    "amplitude": round(eff, 4),
                    "source": disturbance.source,
                })

        # ── 2. Coupling propagation ───────────────────────────────────────────
        if disturbance.coupling_mode != "primary_only" and primary_axes:
            coupled_axes: Dict[str, float] = {}
            for ax, eff in primary_axes.items():
                for coupled_ax, coupling_strength in _COUPLING.get(ax, {}).items():
                    coupled_amp = eff * coupling_strength * _COUPLING_DECAY
                    if coupled_amp < 1e-6:
                        continue
                    # Accumulate — multiple primary axes may couple to the same target
                    coupled_axes[coupled_ax] = coupled_axes.get(coupled_ax, 0.0) + coupled_amp
                    trace.append({
                        "step": "coupling",
                        "from": ax,
                        "to": coupled_ax,
                        "coupling_strength": coupling_strength,
                        "amplitude": round(coupled_amp, 4),
                        "source": f"{disturbance.source}→{ax}→{coupled_ax}",
                    })

            if coupled_axes:
                try:
                    ifield.ingest_external_input(
                        {ax: min(1.0, amp) for ax, amp in coupled_axes.items()},
                        intensity=1.0,
                        source=f"{disturbance.source}[coupled]",
                    )
                except Exception:
                    pass

        # ── 3. Record trace ───────────────────────────────────────────────────
        disturbance.propagation_trace = trace
        summary: Dict[str, Any] = {
            "ts": disturbance.ts,
            "source": disturbance.source,
            "dominant_axis": disturbance.dominant_axis(),
            "intensity": intensity,
            "coupling_mode": disturbance.coupling_mode,
            "genealogy_id": disturbance.genealogy_id,
            "tick": disturbance.tick,
            "trace": trace,
        }
        self._trace_buffer.append(summary)

        if qao is not None and hasattr(qao, "record_pressure_disturbance"):
            try:
                qao.record_pressure_disturbance(summary)
            except Exception:
                pass

        return trace

    def get_recent_traces(self, n: int = 10) -> List[Dict[str, Any]]:
        """Return the n most recent pressure traces."""
        traces = list(self._trace_buffer)
        return traces[-max(1, n):]

    def last_dominant_axis(self) -> Optional[str]:
        if not self._trace_buffer:
            return None
        return self._trace_buffer[-1].get("dominant_axis")

    @staticmethod
    def from_axis_state(
        axis_state: Dict[str, float],
        source: str,
        intensity: float = 0.70,
        coupling_mode: str = "full",
        tick: int = 0,
    ) -> "PressureDisturbance":
        """
        Build a PressureDisturbance from a raw {X,T,N,B,A} axis state dict.
        Values are passed through as-is (already in [0,1] range after IVM normalisation).
        """
        amps = {
            ax: float(max(0.0, min(1.0, axis_state.get(ax, 0.0))))
            for ax in _VALID_AXES
        }
        return PressureDisturbance(
            source=source,
            axis_amplitudes=amps,
            intensity=intensity,
            coupling_mode=coupling_mode,
            tick=tick,
        )

    @staticmethod
    def from_istate(
        istate_name: str,
        axis: str,
        amplitude: float,
        source: str,
        intensity: float = 0.60,
        tick: int = 0,
    ) -> "PressureDisturbance":
        """
        Build a PressureDisturbance from a single I-state event on one axis.
        The I-state name is stored in source for tracing.
        """
        amp = max(0.0, min(1.0, float(amplitude)))
        amps = {ax: 0.0 for ax in _VALID_AXES}
        if axis in _VALID_AXES:
            amps[axis] = amp
        return PressureDisturbance(
            source=f"{source}[{istate_name}]",
            axis_amplitudes=amps,
            intensity=intensity,
            coupling_mode="full",
            tick=tick,
        )


# Module-level singleton — shared across the system
_PUMP_SINGLETON: Optional[WaveformPressurePump] = None


def get_pump() -> WaveformPressurePump:
    global _PUMP_SINGLETON
    if _PUMP_SINGLETON is None:
        _PUMP_SINGLETON = WaveformPressurePump()
    return _PUMP_SINGLETON
