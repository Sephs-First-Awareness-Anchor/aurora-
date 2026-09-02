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

  2. PRESSURE → SEDIMEMORY: The same PressureExperiences are also ingested
     as MemoryEvents so they reach the 25-cell NCStrainFilter and settle
     into the sediment column.  Before this bridge existed, PressureExperience
     records had exactly one outbound path (the DPS crystal hook below) and
     the ledger's own 500-entry JSONL ring buffer was therefore terminal:
     experience 501 silently destroyed experience 1 with nothing downstream
     holding it.  SediMemory is the durable strata; PressureExperienceLedger
     is a staging buffer in front of it.  The NCStrainFilter DIFFERENCE
     dimension already keys on novelty/deviation/surprise/error/anomaly/gap,
     so surprise-weighted retention is performed by the existing strainer --
     this module supplies the divergence measurement, it does not re-implement
     selection.

  3. DUAL STRATA FRAME → SEDIMEMORY: High-coherence conscious frames
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
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals

from typing import Any, Dict

# ── Tunable thresholds ──────────────────────────────────────────────────────

PRESSURE_CRYSTAL_MIN_WORTH  = 0.48   # experiences below this skip DPS
FRAME_SEDIMENT_THRESHOLD    = 0.70   # coherence gate for sedimemory

# Flood control ONLY -- not a selection rule.  Depth-of-deposit selection is
# NCStrainFilter's job (resonance threshold + DIFFERENCE-dimension lens).
# This gate exists so that a subsystem emitting hundreds of identical
# genealogy ticks per minute cannot bury the strata in confirmations of what
# Aurora already predicts.  A first-ever (anchor, action) pair scores 1.0 and
# always passes; a perfectly predicted repeat scores 0.0 and does not.
PRESSURE_SEDIMENT_MIN_DIVERGENCE = 0.15

# Canonical constraint axes, in the order fixed by the AXIS_NC_DIM mapping.
_PRESSURE_AXES = ("X", "T", "N", "B", "A")

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

    Role is derived from BOTH source and causal_action so each distinct
    action on the same concept creates a new facet rather than repeatedly
    strengthening the same one.  This is what makes concepts compound across
    subsystems — the same anchor touched for different reasons grows toward
    COMPOSITE rather than just accumulating usage on a single facet.
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

        source        = str(getattr(exp, "source",        "pressure") or "pressure")
        pursuing      = str(getattr(exp, "pursuing",      anchor)     or anchor)
        causal_action = str(getattr(exp, "causal_action", "")         or "")

        # Role = source:causal_action so distinct actions produce distinct facets
        # on the same crystal rather than collapsing to one.
        role = f"{source}:{causal_action[:30]}" if causal_action else source

        crystal = dps._get_or_create(anchor)
        crystal.add_facet(role=role, content=pursuing[:120], confidence=worth)
        crystal.use()
        crystal.evolve()
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_crystal_ingestion.py:96",
            exc=_aurora_boundary_exc,
            context={"function": "_crystallize_pressure_exp", "handler_line": 96, "source_file": "aurora_crystal_ingestion.py"},
        )
        pass


# ══════════════════════════════════════════════════════════════════════════════
# 1b. PRESSURE → SEDIMEMORY
# ══════════════════════════════════════════════════════════════════════════════

def _pressure_axis_for(anchor: str) -> str:
    """
    Read the constraint axis the anchor declares about itself.

    Two anchor formats reach the ledger and both are handled by their own
    canonical reader -- no heuristic classification happens here:

      1. Prose signature names from genealogy_signature_bridge, built by
         aurora_constraint_signature_resolver.nc_name(law, dim, target)
         -- "Existential_Operator_of_Agency".  These are decoded with that
         module's own parse_nc_name(), and the TARGET is the axis, because
         constraint_genealogy passes target=dom_axis at the call site.
         Scanning these for a bare axis letter does NOT work and silently
         mislabels every anchor whose target is not A.

      2. Colon-delimited keys written directly by constraint_genealogy --
         "B:INTERFACE_WEAKEN:T:ADVANCE_TICK", "REFAB:X:OPERATOR:A:...".
         The first token that is a canonical axis symbol is the axis this
         experience was recorded against.

    Anything else (dream_trainer passes a bare fail-dimension name) falls
    back to A: an unlabelled recorded experience is by construction an
    authored action.
    """
    text = str(anchor or "").strip()
    if not text:
        return "A"

    if "_of_" in text and ":" not in text:
        try:
            from aurora_constraint_signature_resolver import parse_nc_name
            _law, _dim, target = parse_nc_name(text)
            if str(target).upper() in _PRESSURE_AXES:
                return str(target).upper()
        except Exception:
            # Not a well-formed signature name; fall through to token scan.
            pass

    for token in text.split(":"):
        tok = token.strip().upper()
        if tok in _PRESSURE_AXES:
            return tok
    return "A"


def _pressure_divergence(exp: Any) -> Dict[str, Any]:
    """
    How far this experience's outcome sits from what her own prior record
    predicted for the same (anchor, causal_action) pair.

    Measured against the ledger buffer EXCLUDING this experience -- the
    crystal hook fires after PressureExperienceLedger.record() has already
    appended, so the current record must be filtered out or every experience
    would partly predict itself.

    Returns {divergence, prior_resolution_rate, prior_sample_count}.
    A pair never seen before scores 1.0: a first encounter carries maximum
    information about a region of her map she has no history in.
    """
    result = {"divergence": 1.0, "prior_resolution_rate": 0.0, "prior_sample_count": 0}
    try:
        from aurora_internal.aurora_pressure_ledger import PressureExperienceLedger
        ledger = PressureExperienceLedger.get()

        anchor = str(getattr(exp, "anchor", "") or "")
        action = str(getattr(exp, "causal_action", "") or "")
        this_id = str(getattr(exp, "experience_id", "") or "")

        prior = [
            e for e in ledger._buffer
            if e.anchor == anchor
            and e.causal_action == action
            and e.experience_id != this_id
        ]
        if not prior:
            return result

        resolved_n = sum(1 for e in prior if e.outcome.get("resolved", False))
        prior_rate = resolved_n / len(prior)
        observed   = 1.0 if dict(getattr(exp, "outcome", {}) or {}).get("resolved", False) else 0.0

        result["divergence"] = round(abs(observed - prior_rate), 4)
        result["prior_resolution_rate"] = round(prior_rate, 4)
        result["prior_sample_count"] = len(prior)
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_crystal_ingestion.py:_pressure_divergence",
            exc=_aurora_boundary_exc,
            context={"function": "_pressure_divergence", "source_file": "aurora_crystal_ingestion.py"},
        )
    return result


def _sediment_pressure_exp(exp: Any, sedimemory: Any) -> None:
    """
    Ingest one PressureExperience into SediMemory as a MemoryEvent.

    Content keys are named so the existing NCStrainFilter lenses find them
    without any change to the strainer:
        cost / tension          → COST cell,       N constraint
        surprise / deviation    → DIFFERENCE cell
        polarity / outcome      → POLARITY cell
        action / operation      → OPERATOR cell,   A constraint
        confidence              → MAGNITUDE cell
        timestamp               → T constraint

    The ConstraintVector is built from _AXIS_CV exactly as maybe_sediment_frame
    already does -- no new vector physics is introduced by this bridge.
    """
    if sedimemory is None or exp is None:
        return
    try:
        anchor = str(getattr(exp, "anchor", "") or "").strip()
        if not anchor:
            return

        from aurora_internal.aurora_constraint_manifold_patched import ConstraintVector
        from foundational_contract import ExistenceMode

        consequence = dict(getattr(exp, "consequence", {}) or {})
        outcome     = dict(getattr(exp, "outcome",     {}) or {})
        resolved    = bool(outcome.get("resolved", False))
        tension     = float(consequence.get(
            "tension",
            consequence.get("belief_tension",
            consequence.get("cost_signal", 0.0))
        ) or 0.0)

        div = _pressure_divergence(exp)
        if div["divergence"] < PRESSURE_SEDIMENT_MIN_DIVERGENCE:
            return

        axis   = _pressure_axis_for(anchor)
        cv     = ConstraintVector(**_AXIS_CV.get(axis, _AXIS_CV["A"]))
        source = str(getattr(exp, "source", "pressure") or "pressure")

        content = {
            "source":        f"pressure:{source}",
            "anchor":        anchor,
            "meaning":       str(getattr(exp, "meaning", "") or "")[:160],
            "intent":        str(getattr(exp, "pursuing", "") or "")[:160],
            "action":        str(getattr(exp, "causal_action", "") or "")[:160],
            "outcome":       "resolved" if resolved else "diverted",
            "polarity":      1.0 if resolved else -1.0,
            "cost":          round(tension, 4),
            "confidence":    round(1.0 - min(1.0, max(0.0, tension)), 4),
            "surprise":      div["divergence"],
            "deviation":     div["divergence"],
            "dominant_axis": axis,
            "timestamp":     float(getattr(exp, "timestamp", 0.0) or 0.0),
            # Provenance -- lets a reactivated fragment point back at the
            # exact ledger record without a parallel pressure memory store.
            "experience_id":         str(getattr(exp, "experience_id", "") or ""),
            "prior_resolution_rate": div["prior_resolution_rate"],
            "prior_sample_count":    div["prior_sample_count"],
        }
        if div["prior_sample_count"] == 0:
            # First encounter with this (anchor, action): a genuine gap in her
            # record, surfaced under the DIFFERENCE lens's own key.
            content["gap"] = True

        sedimemory.ingest_event(
            content=content,
            constraint_vector=cv,
            source=f"pressure:{source}",
            existence_mode=ExistenceMode.AGENTIC,
        )
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_crystal_ingestion.py:_sediment_pressure_exp",
            exc=_aurora_boundary_exc,
            context={"function": "_sediment_pressure_exp", "source_file": "aurora_crystal_ingestion.py"},
        )
        pass


def _install_pressure_hooks(dps: Any, sedimemory: Any = None) -> None:
    """
    Inject the single PressureExperienceLedger hook.

    PressureExperienceLedger supports exactly one `_crystal_hook`, so both
    downstream consumers are composed into it here rather than each module
    installing its own -- two competing installers would silently overwrite
    each other, and the loser would be whichever wired last.

    Either target may be absent; the hook degrades to whatever is present.
    """
    try:
        from aurora_internal.aurora_pressure_ledger import PressureExperienceLedger
        ledger = PressureExperienceLedger.get()

        def _pressure_fanout(exp: Any) -> None:
            # Failures are isolated per consumer: a DPS error must not cost
            # Aurora the sediment deposit, and vice versa.
            if dps is not None:
                try:
                    _crystallize_pressure_exp(exp, dps)
                except Exception as _aurora_boundary_exc:
                    _aurora_record_exception_from_locals(
                        locals(),
                        module=__name__,
                        operation="exception_handler:aurora_crystal_ingestion.py:_pressure_fanout_dps",
                        exc=_aurora_boundary_exc,
                        context={"function": "_pressure_fanout", "source_file": "aurora_crystal_ingestion.py"},
                    )
            if sedimemory is not None:
                try:
                    _sediment_pressure_exp(exp, sedimemory)
                except Exception as _aurora_boundary_exc:
                    _aurora_record_exception_from_locals(
                        locals(),
                        module=__name__,
                        operation="exception_handler:aurora_crystal_ingestion.py:_pressure_fanout_sedi",
                        exc=_aurora_boundary_exc,
                        context={"function": "_pressure_fanout", "source_file": "aurora_crystal_ingestion.py"},
                    )

        ledger._crystal_hook = _pressure_fanout
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_crystal_ingestion.py:_install_pressure_hooks",
            exc=_aurora_boundary_exc,
            context={"function": "_install_pressure_hooks", "source_file": "aurora_crystal_ingestion.py"},
        )
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
                crystal.evolve()
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_crystal_ingestion.py:141",
            exc=_aurora_boundary_exc,
            context={"function": "_route_behavioral_to_dps", "handler_line": 141, "source_file": "aurora_crystal_ingestion.py"},
        )
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
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_crystal_ingestion.py:184",
            exc=_aurora_boundary_exc,
            context={"function": "maybe_sediment_frame", "handler_line": 184, "source_file": "aurora_crystal_ingestion.py"},
        )
        pass


def _install_dce_sediment_hook(dce_bridge: Any, sedimemory: Any) -> None:
    """Inject sedimemory reference into DCEBridge."""
    try:
        if dce_bridge is not None and sedimemory is not None:
            dce_bridge._sedimemory_ref = sedimemory
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_crystal_ingestion.py:193",
            exc=_aurora_boundary_exc,
            context={"function": "_install_dce_sediment_hook", "handler_line": 193, "source_file": "aurora_crystal_ingestion.py"},
        )
        pass


# ══════════════════════════════════════════════════════════════════════════════
# MAIN WIRING ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def seed_dps_from_lexicon_and_oets(dps: Any, systems: Dict[str, Any]) -> int:
    """
    Seed DPS with facets from the lexicon and OETS for concepts that already
    have noncomp_id / semantic nodes but no DPS crystal yet.

    This gives concept crystals their second and third facets from independent
    sources (lexicon role + OETS semantic node) so they can reach COMPOSITE
    rather than being stuck at 1 facet from a single pressure source.
    """
    seeded = 0
    try:
        perception = systems.get("perception")
        oets       = systems.get("oets") or getattr(perception, "oets", None)
        lexicon    = getattr(perception, "lexicon", None)

        # ── Lexicon entries: one facet per word with its noncomp_id ──────────
        if lexicon is not None:
            entries = getattr(lexicon, "entries", {}) or {}
            for word, entry in entries.items():
                nid  = getattr(entry, "noncomp_id", None) or (
                    entry.get("noncomp_id") if isinstance(entry, dict) else None
                )
                role = getattr(entry, "role", None) or (
                    entry.get("role") if isinstance(entry, dict) else None
                ) or "word"
                valence = getattr(entry, "valence", 0.5) or (
                    entry.get("valence", 0.5) if isinstance(entry, dict) else 0.5
                )
                conf = min(1.0, 0.45 + abs(float(valence or 0.5)) * 0.2)
                # Add a "lexicon:{role}" facet to the word's concept crystal
                crystal = dps._get_or_create(str(word))
                crystal.add_facet(
                    role=f"lexicon:{role}",
                    content=nid or word,
                    confidence=conf,
                )
                crystal.evolve()
                seeded += 1

        # ── OETS semantic nodes: one facet per concept node ──────────────────
        if oets is not None:
            web   = getattr(oets, "web", oets)
            nodes = getattr(web, "nodes", {}) or {}
            for concept, node in nodes.items():
                lineage = str(getattr(node, "lineage", "") or "")
                meaning = str(getattr(node, "meaning", concept) or concept)
                conf    = float(getattr(node, "confidence", 0.5) or 0.5)
                crystal = dps._get_or_create(str(concept))
                crystal.add_facet(
                    role=f"oets:{lineage or 'semantic'}",
                    content=meaning[:80],
                    confidence=max(0.35, conf),
                )
                crystal.evolve()
                seeded += 1

    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_crystal_ingestion.py:257",
            exc=_aurora_boundary_exc,
            context={"function": "seed_dps_from_lexicon_and_oets", "handler_line": 257, "source_file": "aurora_crystal_ingestion.py"},
        )
        pass
    return seeded


def wire_crystallization_loops(systems: Dict[str, Any]) -> None:
    """
    Wire all crystallization loops. Call once after boot_aurora().

    Degrades gracefully when any target system is absent.
    """
    dps = getattr(systems.get("dimensional"), "dps", None)
    if dps is None:
        dps = systems.get("dps")

    # SediMemory is resolved up front because the pressure hook below needs it
    # at install time -- it is also used by the dual-strata wiring in step 4.
    sedimemory = systems.get("sedimemory")

    # ── 1. Pressure → DPS + SediMemory ───────────────────────────────────────
    # One ledger hook, two consumers.  Installed whenever EITHER target exists,
    # so a boot without DPS still lands pressure experiences in the strata.
    if dps is not None or sedimemory is not None:
        _install_pressure_hooks(dps, sedimemory)
    if dps is not None:
        seed_dps_from_lexicon_and_oets(dps, systems)

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
    # (sedimemory already resolved above for the pressure hook)
    consciousness = systems.get("consciousness")
    dce_bridge = (
        getattr(consciousness, "dce", None)
        or systems.get("dce_bridge")
        or getattr(systems.get("dce"), "bridge", None)
    )
    if dce_bridge is not None and sedimemory is not None:
        _install_dce_sediment_hook(dce_bridge, sedimemory)
