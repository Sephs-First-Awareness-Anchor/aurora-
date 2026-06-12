#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_crystal_ingestion.py — Live crystallization loops.

All crystal types (concept, sensory, behavioral, pressure) now use the SAME
DPS Crystal type and the SAME CrystalProcessingSystem registry.  This module
wires the two remaining cross-system data flows that still need a bridge:

  1. PRESSURE → DPS: PressureExperiences feed their anchor concept into the
     DPS crystal as facets, so recurring behavioral patterns crystallize
     rather than only accumulating in the JSONL log.

  2. DUAL STRATA FRAME → SEDIMEMORY: High-coherence conscious frames
     (coherence >= FRAME_SEDIMENT_THRESHOLD) are ingested into SediMemory
     as self-observation events so coherent states accumulate geologically.

WHAT IS NO LONGER NEEDED HERE
==============================
  - Sensory → DPS sync: AuroraSensoryCrystal.observe_frame() now routes
    ALL observations through _dps_route_observation() directly.
  - Genome → AGB wisdom sync: Behavioral facet values reach DPS as facets
    on "behavioral:{domain}:{facet}" crystals (see BehavioralCrystal
    integration in wire_crystallization_loops).

WIRING
======
Call wire_crystallization_loops(systems) once after boot_aurora().
"""
from __future__ import annotations

from typing import Any, Dict

# ── Tunable thresholds ──────────────────────────────────────────────────────

PRESSURE_CRYSTAL_MIN_WORTH  = 0.48   # experiences below this skip DPS
FRAME_SEDIMENT_THRESHOLD    = 0.70   # coherence gate for sedimemory

# ── Axis/I-state map for ConstraintVector construction ─────────────────────

_AXIS_CV: Dict[str, Dict[str, float]] = {
    "X": {"X": 1.0, "T": 0.3, "N": 0.4, "B": 0.5, "A": 0.3},
    "T": {"X": 0.3, "T": 1.0, "N": 0.4, "B": 0.4, "A": 0.3},
    "N": {"X": 0.3, "T": 0.4, "N": 1.0, "B": 0.4, "A": 0.5},
    "B": {"X": 0.4, "T": 0.4, "N": 0.4, "B": 1.0, "A": 0.3},
    "A": {"X": 0.3, "T": 0.3, "N": 0.5, "B": 0.4, "A": 1.0},
}


# ══════════════════════════════════════════════════════════════════════════════
# 1. PRESSURE → DPS CRYSTAL
# ══════════════════════════════════════════════════════════════════════════════

def _crystallize_pressure_exp(exp: Any, dps: Any) -> None:
    """
    Feed one PressureExperience into the matching DPS crystal as a facet.

    The experience's `anchor` maps to a DPS concept.  The `source` becomes the
    facet role so different subsystems (turn_chain, genealogy, dream_trainer…)
    compound as distinct facets under the same crystal rather than colliding.
    """
    try:
        anchor = str(getattr(exp, "anchor", "") or "").strip()
        if not anchor:
            return

        consequence = dict(getattr(exp, "consequence", {}) or {})
        outcome     = dict(getattr(exp, "outcome",     {}) or {})
        resolved    = bool(outcome.get("resolved", False))
        tension     = float(consequence.get(
            "tension",
            consequence.get("belief_tension",
            consequence.get("cost_signal", 0.0))
        ) or 0.0)
        worth = 0.55 if resolved else 0.35
        worth += min(0.30, tension * 0.30)
        worth = min(1.0, worth)

        if worth < PRESSURE_CRYSTAL_MIN_WORTH:
            return

        source   = str(getattr(exp, "source",   "pressure") or "pressure")
        pursuing = str(getattr(exp, "pursuing", anchor)     or anchor)

        crystal = dps._get_or_create(anchor)
        crystal.add_facet(role=source, content=pursuing[:120], confidence=worth)
        crystal.use()
    except Exception:
        pass


def _install_pressure_dps_hook(dps: Any) -> None:
    """Inject a crystal hook into PressureExperienceLedger."""
    try:
        from aurora_internal.aurora_pressure_ledger import PressureExperienceLedger
        ledger = PressureExperienceLedger.get()
        ledger._crystal_hook = lambda exp: _crystallize_pressure_exp(exp, dps)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# 2. BEHAVIORAL GENOME → DPS CRYSTAL
# ══════════════════════════════════════════════════════════════════════════════

def _route_behavioral_to_dps(sensory_engine: Any, dps: Any) -> None:
    """
    Write behavioral genome facet values as DPS crystal facets so the
    behavioral state lives in the same crystal registry as everything else.

    Keying convention: "behavioral:{domain}:{facet_name}"
    """
    try:
        for crystal_attr, domain_name in (
            ("audio_crystal",  "audio"),
            ("visual_crystal", "visual"),
        ):
            bc = getattr(sensory_engine, crystal_attr, None)
            if bc is None:
                continue
            facets = getattr(bc, "facets", {}) or {}
            for facet_name, bf in facets.items():
                value = float(getattr(bf, "value", 0.5))
                concept = f"behavioral:{domain_name}:{facet_name}"
                crystal = dps._get_or_create(concept)
                crystal.add_facet(
                    role=f"genome_{facet_name}",
                    content=round(value, 4),
                    confidence=value,
                )
                crystal.use()
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# 3. DUAL STRATA FRAME → SEDIMEMORY
# ══════════════════════════════════════════════════════════════════════════════

def maybe_sediment_frame(frame_dict: Dict[str, Any], sedimemory: Any) -> None:
    """
    Ingest a high-coherence ConsciousFrame dict into SediMemory.

    Only frames with coherence >= FRAME_SEDIMENT_THRESHOLD are sedimented.
    """
    if sedimemory is None or not isinstance(frame_dict, dict):
        return
    coherence = float(frame_dict.get("coherence", 0.0))
    if coherence < FRAME_SEDIMENT_THRESHOLD:
        return
    try:
        from aurora_internal.aurora_constraint_manifold_patched import ConstraintVector
        from foundational_contract import ExistenceMode

        dominant_axis = str(frame_dict.get("dominant_axis", "A") or "A")
        cv_vals = _AXIS_CV.get(dominant_axis, _AXIS_CV["A"])
        cv = ConstraintVector(**cv_vals)

        content = {
            "source":          "dual_strata_frame",
            "crest":           frame_dict.get("conscious_crest", ""),
            "stance":          frame_dict.get("stance", ""),
            "selected_action": frame_dict.get("selected_action", ""),
            "processing_mode": frame_dict.get("processing_mode", ""),
            "dominant_axis":   dominant_axis,
            "readiness":       round(float(frame_dict.get("readiness", 0.0)), 4),
            "coherence":       round(coherence, 4),
        }
        sedimemory.ingest_event(
            content=content,
            constraint_vector=cv,
            source="dual_strata_frame",
            existence_mode=ExistenceMode.AGENTIC,
        )
    except Exception:
        pass


def _install_dce_sediment_hook(dce_bridge: Any, sedimemory: Any) -> None:
    """Inject sedimemory reference into DCEBridge."""
    try:
        if dce_bridge is not None and sedimemory is not None:
            dce_bridge._sedimemory_ref = sedimemory
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# MAIN WIRING ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def wire_crystallization_loops(systems: Dict[str, Any]) -> None:
    """
    Wire all crystallization loops. Call once after boot_aurora().

    Degrades gracefully when any target system is absent.
    """
    dps = getattr(systems.get("dimensional"), "dps", None)
    if dps is None:
        dps = systems.get("dps")

    # ── 1. Pressure → DPS ────────────────────────────────────────────────────
    if dps is not None:
        _install_pressure_dps_hook(dps)

    # ── 2. Sensory observations → DPS (via AuroraSensoryCrystal._dps_ref) ───
    # Ensure the sensory crystal has the DPS reference so _dps_route_observation
    # fires on every observe_frame() call.
    sensory_crystal = systems.get("sensory_crystal")
    if sensory_crystal is not None and dps is not None:
        sensory_crystal._dps_ref = dps   # may already be set by wire_dimensional

    # ── 3. Behavioral genome → DPS ───────────────────────────────────────────
    hw = systems.get("hardware")
    sensory_engine = getattr(hw, "sensory_engine", None)
    if sensory_engine is None:
        sensory_engine = systems.get("sensory_integration")
    if sensory_engine is not None and dps is not None:
        _route_behavioral_to_dps(sensory_engine, dps)

    # ── 4. Dual strata frame → sedimemory ────────────────────────────────────
    sedimemory  = systems.get("sedimemory")
    consciousness = systems.get("consciousness")
    dce_bridge = (
        getattr(consciousness, "dce", None)
        or systems.get("dce_bridge")
        or getattr(systems.get("dce"), "bridge", None)
    )
    if dce_bridge is not None and sedimemory is not None:
        _install_dce_sediment_hook(dce_bridge, sedimemory)
