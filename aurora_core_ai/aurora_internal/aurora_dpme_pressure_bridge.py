"""
aurora_dpme_pressure_bridge.py
─────────────────────────────────────────────────────────────────────────────
Connects the evolutionary pressure system to the DPME (Dimensional Parameter
Metacognition Engine) so that axis imbalances detected by PressureParameterAdapter
directly influence DER facet energy corrections.

How it works:
  PressureParameterAdapter writes adapter_hints.json with evolver_bias_hints:
      {"energy": +0.1, "boundary": -0.05, "agency": +0.08, ...}
  Positive hint = axis is over-pressured and not relieving well → that
  capability domain needs more internal energy support.

  This bridge reads those hints, maps constraint axes to DER channels
  (vitality/processing/memory/emotional/creative), and calls
  set_external_pressure_guidance() so DPME.auto_correct() injects energy
  to the right category on its next heartbeat.

Axis → DER channel mapping (rationale):
  existence (X) → vitality    (core identity = system aliveness)
  temporal  (T) → processing  (temporal coherence = active computation)
  energy    (N) → processing  (resource management = processing throughput)
  boundary  (B) → memory      (boundary tracking = what to hold / not hold)
  agency    (A) → creative    (agency expression = generative choice-making)

Secondary channel: the second-highest-pressure axis also gets a boost at
half strength — matching DPME's existing secondary channel behavior.
─────────────────────────────────────────────────────────────────────────────
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Tuple

_ADAPTER_HINTS_REL = "aurora_state/adapter_hints.json"

# Axis constraint name → DER channel name
_AXIS_TO_DER: Dict[str, str] = {
    "x":          "vitality",
    "existence":  "vitality",
    "t":          "processing",
    "temporal":   "processing",
    "n":          "processing",
    "energy":     "processing",
    "b":          "memory",
    "boundary":   "memory",
    "a":          "creative",
    "agency":     "creative",
}

# DER channels the DPME recognises (from aurora_consciousness_engine._DER_CHANNELS)
_VALID_DER_CHANNELS = {"vitality", "processing", "memory", "emotional", "creative"}


class DPMEPressureBridge:
    """
    Reads adapter_hints.json and translates axis pressure imbalances into
    DER channel guidance for the DPME.

    Usage (in runtime tick):
        bridge = DPMEPressureBridge(repo_root)
        bridge.apply()   # calls set_external_pressure_guidance internally
    """

    def __init__(self, repo_root: str):
        self.repo_root = os.path.abspath(repo_root)

    # ── public ────────────────────────────────────────────────────────────────

    def apply(self) -> Dict[str, Any]:
        """
        Read adapter hints, compute the highest-pressure axis, and push
        guidance to the DPME via set_external_pressure_guidance().

        Returns a summary dict with what was pushed (or why it was skipped).
        """
        try:
            from aurora_consciousness_engine import set_external_pressure_guidance  # type: ignore
        except ImportError as exc:
            return {"applied": False, "reason": f"import_error: {exc}"}

        hints = self._load_hints()
        bias: Dict[str, float] = hints.get("evolver_bias_hints", {})
        if not bias:
            # No pressure data yet — clear any stale guidance
            set_external_pressure_guidance(None)
            return {"applied": False, "reason": "no_bias_hints"}

        # Map each axis hint to a DER channel; sum positive-pressure signals
        channel_pressure: Dict[str, float] = {}
        for axis_key, weight in bias.items():
            der_ch = _AXIS_TO_DER.get(str(axis_key).lower())
            if der_ch and der_ch in _VALID_DER_CHANNELS:
                # positive weight = axis overloaded → needs energy support
                channel_pressure[der_ch] = channel_pressure.get(der_ch, 0.0) + float(weight)

        if not channel_pressure:
            set_external_pressure_guidance(None)
            return {"applied": False, "reason": "no_mappable_axes"}

        # Pick primary (highest) and secondary (second-highest) positive signals
        ranked = sorted(channel_pressure.items(), key=lambda kv: -kv[1])
        primary_ch, primary_score = ranked[0]
        secondary_ch = ranked[1][0] if len(ranked) > 1 else None

        # Normalise score to 0–1 range (bias hints are typically ±0.2)
        norm_score = min(1.0, max(0.0, primary_score / 0.4))

        if norm_score < 0.05:
            # Pressure is minimal — no push needed
            set_external_pressure_guidance(None)
            return {"applied": False, "reason": "pressure_too_low", "score": norm_score}

        axis_stats = hints.get("axis_stats", {})
        # compare_value: mean pre-pressure for the dominant axis (gives DPME context)
        compare_value = float(
            axis_stats.get(
                self._der_to_axis_letter(primary_ch), {}
            ).get("mean_pressure_pre", norm_score) or norm_score
        )

        set_external_pressure_guidance({
            "score":             norm_score,
            "compare_value":     compare_value,
            "primary_channel":   primary_ch,
            "secondary_channel": secondary_ch,
        })

        return {
            "applied":           True,
            "primary_channel":   primary_ch,
            "secondary_channel": secondary_ch,
            "score":             round(norm_score, 4),
            "compare_value":     round(compare_value, 4),
            "channel_pressure":  {k: round(v, 4) for k, v in channel_pressure.items()},
        }

    def status(self) -> Dict[str, Any]:
        hints = self._load_hints()
        bias  = hints.get("evolver_bias_hints", {})
        return {
            "adapter_hints_present": bool(hints),
            "bias_hint_count":       len(bias),
            "bias_hints":            bias,
            "last_updated":          hints.get("last_updated", 0.0),
        }

    # ── helpers ───────────────────────────────────────────────────────────────

    def _load_hints(self) -> Dict[str, Any]:
        path = os.path.join(self.repo_root, _ADAPTER_HINTS_REL)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _der_to_axis_letter(der_channel: str) -> str:
        """Reverse-map DER channel → primary axis letter for axis_stats lookup."""
        return {
            "vitality":   "X",
            "processing": "N",   # N is the highest-frequency energy pressure axis
            "memory":     "B",
            "creative":   "A",
            "emotional":  "T",
        }.get(der_channel, "X")


def apply_pressure_to_dpme(repo_root: str) -> Dict[str, Any]:
    """
    Module-level convenience. Call from aurora_runtime.py tick loop.
    """
    try:
        return DPMEPressureBridge(repo_root).apply()
    except Exception as exc:
        return {"applied": False, "reason": str(exc)}
