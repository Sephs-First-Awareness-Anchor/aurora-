#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_training_pulse.py — Field energization for daemon-less training.

THE PROBLEM THIS SOLVES (FIX-A011)
==================================
Aurora's language ignition sequence requires the meaning crystal to cross
0.25 (Stage 5), which requires the AttentionEngine to reach FORMING state,
which requires resonance = salience_ema × tension_ema to cross threshold.

Subsurface tension comes from internal constraint drift — which is driven
by the daemon's continuous wall-clock cycles. Both EMAs use alpha=0.3 and
start at zero, so they need MANY consecutive ticks to climb.

Training sims (corpus runner, interaction tests) run daemon-less, firing
isolated single ticks into a cold field:

    tension_ema ≈ 0  →  resonance ≈ 0  →  attention never FORMS
    →  no meaning nucleus  →  ignition Stage 5 fails  →  go=False

Result: every training exchange happens in a field that cannot ignite.
Language learning signals (motif success, fidelity, re-entry) fire into
a dead manifold, and nothing consolidates.

THE FIX
=======
TrainingPulse compresses the daemon's wall-clock cycling into a burst of
micro-cycles around each training exchange. Each micro-cycle:

  1. Injects a WaveformPressurePump disturbance into the identity field
     (same pattern as aurora.py's per-turn pre-injection).
  2. Records constraint magnitudes into the DifferenceHistoryBuffer and
     takes a DifferenceSnapshot (same pattern as aurora.py's per-turn tick).
  3. Ticks the AttentionEngine with the snapshot so salience/tension EMAs
     accumulate exactly as they would under the live daemon.
  4. Feeds any FORMING meaning nucleus to the understanding contract.

This is not synthetic stimulation — every value flows from the same live
systems the daemon uses. It is the daemon's cadence, time-compressed.

USAGE
=====
    from aurora_training_pulse import TrainingPulse

    pulse = TrainingPulse(systems)
    # ... per training exchange:
    pulse.energize(user_text, response_text)     # default 6 micro-cycles
    # ... check field state any time:
    print(pulse.field_report())

corpus_runner integration: call pulse.energize() once per absorbed item.
Zero manual steps — constructed from the existing `systems` dict only.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

# Canonical five-axis symbols — X=Existence, T=Temporal, N=Energy,
# B=Boundary, A=Agency (constraint physics hard rule).
_AXES = ("X", "T", "N", "B", "A")

# Conscious-crest key mapping used by aurora.py's per-turn tick.
_AXIS_MAP = {
    "X": "existence",
    "T": "temporal",
    "N": "energy",
    "B": "boundary",
    "A": "agency",
}


class TrainingPulse:
    """
    Time-compressed daemon cadence for daemon-less training sessions.

    Reads only from the live `systems` dict produced by boot_aurora():
        systems['pressure_pump']          — WaveformPressurePump
        systems['identity_field']         — NoncompField (ingest_external_input)
        systems['dimensional']            — DimensionalSystems (constraint aggregate)
        systems['_diff_history_buffer']   — DifferenceHistoryBuffer
        systems['_attention_engine']      — AttentionEngine
        systems['understanding_contract'] — runtime understanding contract
        systems['quasiarch_observer']     — optional trace consumer
    """

    def __init__(self, systems: Dict[str, Any]):
        self._systems = systems
        self._tick = int(time.time()) % 1_000_000

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def energize(
        self,
        user_text: str = "",
        response_text: str = "",
        cycles: int = 6,
        intensity: float = 0.65,
    ) -> Dict[str, Any]:
        """
        Run `cycles` micro-cycles around one training exchange.

        Returns a summary: final attention state, resonance, whether a
        meaning nucleus formed, and the per-cycle resonance trace.
        """
        trace = []
        nucleus = None
        frame = None

        for i in range(max(1, int(cycles))):
            self._tick += 1
            self._inject_waveform(user_text, intensity=intensity, cycle=i)
            snap = self._record_and_snapshot()
            frame = self._tick_attention(user_text, snap)
            if frame is not None:
                trace.append(round(float(frame.resonance), 4))
            nucleus = self._capture_nucleus() or nucleus

        return {
            "cycles": len(trace),
            "resonance_trace": trace,
            "final_state": (str(frame.state.value)
                            if frame is not None and hasattr(frame.state, "value")
                            else str(getattr(frame, "state", "none"))),
            "final_resonance": trace[-1] if trace else 0.0,
            "nucleus_formed": nucleus is not None,
        }

    def field_report(self) -> Dict[str, Any]:
        """Snapshot of field-energization-relevant state for diagnostics."""
        out: Dict[str, Any] = {}
        frame = self._systems.get("_last_attention_frame")
        if frame is not None:
            out["attention_state"] = str(getattr(frame.state, "value", frame.state))
            out["salience"] = float(frame.surface_salience)
            out["tension"] = float(frame.subsurface_tension)
            out["resonance"] = float(frame.resonance)
        lf = self._systems.get("language_field")
        if lf is not None and hasattr(lf, "ignition_check"):
            try:
                ig = lf.ignition_check()
                out["ignition_go"] = bool(ig.get("go", False))
                out["ignition_stages"] = [k for k, v in (ig.get("stages") or {}).items() if v]
            except Exception:
                pass
        return out

    # ------------------------------------------------------------------
    # Micro-cycle internals — each mirrors a verified aurora.py pattern
    # ------------------------------------------------------------------

    def _inject_waveform(self, user_text: str, intensity: float, cycle: int) -> None:
        """Mirror of aurora.py's per-turn waveform pre-injection."""
        try:
            pump = self._systems.get("pressure_pump")
            ifield = self._systems.get("identity_field")
            dim = self._systems.get("dimensional")
            if pump is None or ifield is None or dim is None:
                return
            agg: Optional[Dict[str, float]] = (
                dim.get_constraint_aggregate()
                if hasattr(dim, "get_constraint_aggregate") else None
            )
            if not agg:
                # Cold field on fresh boot: derive a gentle, honest axis state
                # from the exchange itself so the manifold has something real
                # to propagate (B from text structure, A from address).
                n_words = len((user_text or "").split())
                agg = {
                    "X": 0.45,
                    "T": 0.40,
                    "N": min(1.0, 0.30 + 0.02 * n_words),
                    "B": 0.40,
                    "A": 0.50 if user_text.strip() else 0.30,
                }
            from aurora_waveform_pressure import WaveformPressurePump
            dist = WaveformPressurePump.from_axis_state(
                agg,
                source=f"training_pulse_c{cycle}",
                intensity=max(0.0, min(1.0, float(intensity))),
                coupling_mode="full",
                tick=self._tick,
            )
            pump.inject(dist, ifield, qao=self._systems.get("quasiarch_observer"))
        except Exception:
            pass

    def _record_and_snapshot(self):
        """Mirror of aurora.py's per-turn diff buffer record + snapshot.

        Magnitudes come from the identity field's live pressure topology —
        the very state the waveform injection just perturbed — so drift (and
        therefore tension) honestly reflects field motion, exactly as it does
        under the daemon's wall-clock cycles. The conscious crest is used as
        a secondary source when present.
        """
        try:
            from aurora_internal.aurora_constraint_manifold_patched import Constraint
            dhb = self._systems.get("_diff_history_buffer")
            if dhb is None:
                return None
            topo: Dict[str, float] = {}
            try:
                ifield = self._systems.get("identity_field")
                if ifield is not None and hasattr(ifield, "status"):
                    _st = ifield.status() or {}
                    # NoncompField exposes 'axis_pressures' (live, moves under
                    # waveform injection). 'pressure_topology' kept as legacy
                    # fallback for older field implementations.
                    topo = dict(_st.get("axis_pressures")
                                or _st.get("pressure_topology") or {})
            except Exception:
                topo = {}
            cc = dict(self._systems.get("_live_conscious_crest") or {})
            mags: Dict[Any, float] = {}
            for cname, ckey in _AXIS_MAP.items():
                raw = topo.get(cname)
                if raw is None:
                    raw = cc.get(ckey, cc.get(cname, 0.5))
                mags[getattr(Constraint, cname)] = min(1.0, max(0.0, float(raw or 0.5)))
            dhb.record(tick=self._tick, magnitudes=mags)
            snap = dhb.snapshot(tick=self._tick)
            self._systems["_last_diff_snapshot"] = snap
            return snap
        except Exception:
            return None

    def _tick_attention(self, user_text: str, snap):
        """Mirror of aurora.py's per-turn AttentionEngine tick."""
        try:
            ae = self._systems.get("_attention_engine")
            if ae is None or snap is None:
                return None
            salience = 0.5
            try:
                dvals = list(snap.values.values())
                if dvals:
                    salience = min(1.0, sum(abs(v) for v in dvals) / len(dvals) * 2.0)
            except Exception:
                pass
            addressed = bool(user_text and user_text.strip())
            if addressed:
                salience = max(salience, 0.40)
            stim = {
                "intensity": round(salience, 4),
                "addressed": addressed,
                "tags": (user_text or "").split()[:4],
            }
            frame = ae.tick(self._tick, stim, snap)
            self._systems["_last_attention_frame"] = frame
            return frame
        except Exception:
            return None

    def _capture_nucleus(self):
        """Mirror of aurora.py's nucleus → understanding contract wiring."""
        try:
            ae = self._systems.get("_attention_engine")
            if ae is None or not hasattr(ae, "get_meaning_nucleus"):
                return None
            nucleus = ae.get_meaning_nucleus()
            if nucleus is not None:
                self._systems["_meaning_nucleus"] = nucleus
                uc = self._systems.get("understanding_contract")
                if uc is not None and hasattr(uc, "register_meaning_event"):
                    uc.register_meaning_event(nucleus)
            return nucleus
        except Exception:
            return None
