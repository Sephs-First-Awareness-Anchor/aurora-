#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_crystal_ingestion.py — Live crystallization loops.

Connects three data flows that were previously siloed into flat logs:

  1. PRESSURE → DPS: PressureExperiences with high worth feed their anchor
     concept into the DPS crystal as facets, so recurring behavioral patterns
     solidify into crystals rather than accumulating only in the JSONL log.
     Multiple experiences for the same anchor compound under the same DPS
     crystal — this IS the concept crystallization the architecture always
     intended.

  2. SENSORY GENOME → AGB WISDOM: BehavioralCrystal facet values (focus,
     motion_sensitivity, sensitivity, etc.) from SensoryCompetencyEngine are
     propagated to the corresponding AGB SensoryNode wisdom fields
     (wisdom_tone_bias, wisdom_structure_bias) so the sensory genome's
     developmental state informs the crystal's own distillation logic.

  3. DUAL STRATA FRAME → SEDIMEMORY: High-coherence conscious frames
     (coherence >= FRAME_SEDIMENT_THRESHOLD) are ingested into SediMemory
     as self-observation events so coherent states accumulate in the
     geological memory rather than only being logged to JSONL.

WIRING
======
Call wire_crystallization_loops(systems) once after boot_aurora() completes.
All three loops are installed with zero overhead when the target system is
absent — every path degrades gracefully.

IMPORT SAFETY
=============
aurora_pressure_ledger and aurora_internal.dual_strata.dce_bridge both exist
deep in the dependency tree.  We touch them only through attribute injection
(no import-time coupling).  SensoryCompetencyEngine is read-only here.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

# ── Tunable thresholds ──────────────────────────────────────────────────────

PRESSURE_CRYSTAL_MIN_WORTH      = 0.48   # experiences below this skip DPS
FRAME_SEDIMENT_THRESHOLD        = 0.70   # coherence gate for sedimemory
GENOME_TONE_WEIGHT              = 0.20   # EMA alpha: sensory genome → AGB nodes

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
    Confidence is derived from whether the outcome resolved and how much
    tension was incurred — high tension + resolved = strong crystallization.
    """
    try:
        if dps is None or exp is None:
            return

        anchor = str(getattr(exp, "anchor", "") or "").strip()
        if not anchor:
            return

        # Derive worth from consequence + outcome
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

        source    = str(getattr(exp, "source",   "pressure") or "pressure")
        pursuing  = str(getattr(exp, "pursuing", anchor)     or anchor)

        crystal = dps._get_or_create(anchor)
        crystal.add_facet(role=source, content=pursuing[:120], confidence=worth)
        crystal.use()
    except Exception:
        pass


def _install_pressure_dps_hook(dps: Any) -> None:
    """
    Inject a crystal hook into PressureExperienceLedger so every new
    experience immediately feeds its anchor concept into DPS.
    """
    try:
        from aurora_internal.aurora_pressure_ledger import PressureExperienceLedger
        ledger = PressureExperienceLedger.get()
        ledger._crystal_hook = lambda exp: _crystallize_pressure_exp(exp, dps)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# 2. SENSORY GENOME → AGB WISDOM FIELDS
# ══════════════════════════════════════════════════════════════════════════════

def sync_sensory_genome_to_agb(
    sensory_engine: Any,
    sensory_crystal: Any,
) -> None:
    """
    Propagate BehavioralCrystal facet values from SensoryCompetencyEngine
    into the corresponding AGB SensoryNode wisdom fields.

    Mapping:
        audio  (sensitivity, voice_isolation, emotion_detection)
            → audio SensoryNode.wisdom_tone_bias
        visual (focus, detail_orientation, motion_sensitivity)
            → visual SensoryNode.wisdom_structure_bias

    Uses EMA (GENOME_TONE_WEIGHT alpha) so the genome influences gradually
    rather than overwriting — the nodes still earn their own maturity.
    """
    if sensory_engine is None or sensory_crystal is None:
        return
    try:
        # ── Compute genome values ─────────────────────────────────────────
        a_crystal = getattr(sensory_engine, "audio_crystal", None)
        v_crystal = getattr(sensory_engine, "visual_crystal", None)

        audio_tone = 0.5
        visual_struct = 0.5

        if a_crystal is not None:
            facets = getattr(a_crystal, "facets", {}) or {}
            vals = [
                float(getattr(f, "value", 0.5))
                for k, f in facets.items()
                if k in ("sensitivity", "voice_isolation", "emotion_detection")
            ]
            if vals:
                audio_tone = sum(vals) / len(vals)

        if v_crystal is not None:
            facets = getattr(v_crystal, "facets", {}) or {}
            vals = [
                float(getattr(f, "value", 0.5))
                for k, f in facets.items()
                if k in ("focus", "detail_orientation", "motion_sensitivity")
            ]
            if vals:
                visual_struct = sum(vals) / len(vals)

        α = GENOME_TONE_WEIGHT

        # ── Push into AGB audio facet nodes ──────────────────────────────
        sc_audio = getattr(sensory_crystal, "_audio", {}) or {}
        for facet_obj in sc_audio.values():
            nodes = getattr(facet_obj, "_nodes", {}) or {}
            for node in nodes.values():
                old = float(getattr(node, "wisdom_tone_bias", 0.0))
                node.wisdom_tone_bias = round((1.0 - α) * old + α * audio_tone, 4)

        # ── Push into AGB visual facet nodes ─────────────────────────────
        sc_visual = getattr(sensory_crystal, "_visual", {}) or {}
        for facet_obj in sc_visual.values():
            nodes = getattr(facet_obj, "_nodes", {}) or {}
            for node in nodes.values():
                old = float(getattr(node, "wisdom_structure_bias", 0.0))
                node.wisdom_structure_bias = round((1.0 - α) * old + α * visual_struct, 4)

    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# 3. DUAL STRATA FRAME → SEDIMEMORY
# ══════════════════════════════════════════════════════════════════════════════

def maybe_sediment_frame(frame_dict: Dict[str, Any], sedimemory: Any) -> None:
    """
    Ingest a high-coherence ConsciousFrame dict into SediMemory.

    Only frames with coherence >= FRAME_SEDIMENT_THRESHOLD are sedimented —
    low-coherence frames are too noisy to deserve geological permanence.
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
            "source":         "dual_strata_frame",
            "crest":          frame_dict.get("conscious_crest", ""),
            "stance":         frame_dict.get("stance", ""),
            "selected_action":frame_dict.get("selected_action", ""),
            "processing_mode":frame_dict.get("processing_mode", ""),
            "dominant_axis":  dominant_axis,
            "readiness":      round(float(frame_dict.get("readiness", 0.0)), 4),
            "coherence":      round(coherence, 4),
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
    """
    Inject sedimemory reference into DCEBridge so persist() can call
    maybe_sediment_frame on high-coherence frames.
    """
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
    Install all three crystallization loops. Call once after boot_aurora().

    Safe to call when individual systems are absent — every path degrades
    gracefully to a no-op.
    """
    # ── 1. Pressure → DPS ────────────────────────────────────────────────────
    dps = getattr(systems.get("dimensional"), "dps", None)
    if dps is None:
        dps = systems.get("dps")
    if dps is not None:
        _install_pressure_dps_hook(dps)

    # ── 2. Sensory genome → AGB wisdom (initial sync at boot + per-session) ─
    hw = systems.get("hardware")
    sensory_engine = getattr(hw, "sensory_engine", None)
    if sensory_engine is None:
        # Fallback: some integrations expose the engine directly
        sensory_engine = systems.get("sensory_integration")
    sensory_crystal = systems.get("sensory_crystal")
    if sensory_engine is not None and sensory_crystal is not None:
        sensory_crystal._sensory_engine_ref = sensory_engine
        sync_sensory_genome_to_agb(sensory_engine, sensory_crystal)

    # ── 3. Dual strata frame → sedimemory ────────────────────────────────────
    sedimemory = systems.get("sedimemory")
    consciousness = systems.get("consciousness")
    dce_bridge = (
        getattr(consciousness, "dce", None)         # primary: consciousness.dce
        or systems.get("dce_bridge")                # fallback: direct key
        or getattr(systems.get("dce"), "bridge", None)
    )
    if dce_bridge is not None and sedimemory is not None:
        _install_dce_sediment_hook(dce_bridge, sedimemory)
