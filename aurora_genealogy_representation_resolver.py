"""
aurora_genealogy_representation_resolver.py
Sunni (Sir) Morningstar & Cael Devo

THE GAP THIS CLOSES
--------------------
aurora_working_memory.py's _render_from_comprehension_intent() was building a
fabricated `mock_assembly` (SimpleNamespace(active_count=10), a hardcoded
coherence clamp, generic current axis_activation) instead of grounding
expression in a real constraint-genealogy item for the specific comprehension
gap at hand. Neither aurora_working_memory.py nor aurora_expression_perception.py
ever referenced ConstraintGenealogyLogger at all -- the render path and the
genealogy engine were fully disconnected.

The genealogy engine itself (aurora_internal/constraint_genealogy.py) already
implements exactly the "one constraint signature, many representational
surfaces" design: _constraint_basis_for_item() returns real per-axis counts,
signature, generational_depth_counts/potency, and a persistent
semantic_origin_signature when present. But every genealogy read function
(_constraint_basis_for_item, representation_gap_candidates, etc.) requires an
item_id you already know. There was no function that took LIVE turn content
and resolved it FORWARD into an item_id in the first place.

This module is that resolver. It reuses the same per-link I-state/recursion
profile conversion WarpGenerator._search_genealogy() already performs (see
aurora_warp_protocol.py), but -- unlike that function, which discards the
link id and only returns blended profiles for synthesis biasing -- this
resolver keeps the id, so the render path can ask "which real item is this
turn standing on?" not just "what should a brand-new component look like?"

TIE-IN TO WARP DISCOVERY (per Sunni's direction)
--------------------------------------------------
When no existing genealogy item covers the live turn well enough
(best cosine < COVERAGE_THRESHOLD), this is a genuine coverage gap in the
exact sense AxisCoverageChecker/WarpGenerator already define. Rather than
fabricate anything, this resolver:
  1. Builds a real CoverageGap via AxisCoverageChecker (canonical, not
     hand-rolled).
  2. Calls WarpGenerator().generate(gap, ..., genealogy=genealogy) to
     synthesize a real WarpComponent, genealogy-biased exactly the way
     any other warp-derived structure is.
  3. Submits a WarpDemand to WarpField (when one is available) so the event
     is classified, routed, and tracked through the system's one real
     "I cannot resolve this" primitive -- not a side channel.

WHAT THIS DELIBERATELY DOES NOT DO
------------------------------------
It does NOT call genealogy.observe() to mint a fake permanent item_id for a
freshly-synthesized representation. observe() requires real PressureVec
before/after deltas -- fabricating those just to force an item_id into
existence would be the exact same anti-pattern as mock_assembly, one layer
down. A freshly-synthesized WarpComponent is returned honestly labeled as
`source="warp_synthesized"` with no item_id; it earns permanent standing in
genealogy the same way every other WarpComponent does -- through real trial
evidence (trial_score_ema / evaluate_warp_trials' promotion threshold) if the
render-path host is later registered as a WarpCapable actuator. Never script
what Aurora can develop herself.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aurora_internal.constraint_genealogy import AXES  # ("X","T","N","B","A")
from aurora_warp_protocol import (
    AxisCoverageChecker,
    axes_to_istates,
    istates_to_axes,
    CoverageGap,
    WarpGenerator,
    WarpDemand,
    WarpDecision,
    WarpField,
    WarpTrigger,
    COVERAGE_THRESHOLD,
)


@dataclass
class ResolvedRepresentation:
    """What the render path should ground expression in for this turn."""
    item_id: Optional[str]
    confidence: float
    constraint_basis: Dict[str, Any]
    source: str  # "genealogy_match" | "warp_synthesized" | "unresolved"
    warp_component_id: Optional[str] = None
    warp_decision: Optional[WarpDecision] = None
    notes: str = ""


def build_live_profile(
    perception: Any,
    recursion_hint: str = "shallow",
) -> Dict[str, float]:
    """
    Build a 15D (I-state + recursion) profile for the CURRENT turn from
    perception's own live axis activation -- the same attribute
    _render_from_comprehension_intent already reads for mock_assembly's
    adjusted_axes, so this introduces no new dependency, just a real
    destination for that data.

    recursion_hint defaults to "shallow": a live user turn is generation-0
    by definition, not yet part of any DAG depth -- this mirrors the
    depth<=1 bucket WarpGenerator._search_genealogy() already uses for
    shallow links, applied honestly (labeled as a default, not measured).
    """
    axis_activation = dict(getattr(perception, "_axis_activation", {}) or {})
    axis_weights = {ax: float(axis_activation.get(ax, 0.0) or 0.0) for ax in AXES}
    profile = axes_to_istates(axis_weights, ivm_polarity=None)
    if recursion_hint == "shallow":
        profile["REC_SHALLOW"] = 0.55
        profile["REC_SURFACE"] = 0.25
    elif recursion_hint == "moderate":
        profile["REC_MODERATE"] = 0.60
        profile["REC_SHALLOW"] = 0.25
    else:
        profile["REC_DEEP"] = 0.60
        profile["REC_MODERATE"] = 0.25
    return profile


def _link_istate_profile(link: Any) -> Dict[str, float]:
    """
    Convert one ConstraintLink to a 15D profile for cosine comparison.
    Mirrors WarpGenerator._search_genealogy()'s per-link conversion exactly
    (same mean_relief -> axes_to_istates step, same depth -> recursion
    bucket thresholds) so the two systems share representation math rather
    than drifting apart.
    """
    relief = getattr(link, "mean_relief", None)
    if not relief or not isinstance(relief, dict):
        return {}
    profile = axes_to_istates(
        {ax: float(relief.get(ax, 0.0) or 0.0) for ax in AXES},
        ivm_polarity=None,
    )
    depth = int(getattr(link, "depth", 1) or 1)
    if depth <= 1:
        profile["REC_SHALLOW"] = 0.55
        profile["REC_SURFACE"] = 0.25
    elif depth == 2:
        profile["REC_MODERATE"] = 0.60
        profile["REC_SHALLOW"] = 0.25
    else:
        profile["REC_DEEP"] = 0.60
        profile["REC_MODERATE"] = 0.25
        if depth >= 4:
            profile["REC_CORE"] = 0.40
    return profile


def constraint_basis_to_axis_weights(basis: Dict[str, Any]) -> Dict[str, float]:
    """
    Convert a resolved constraint_basis's raw per-axis counts into [0,1]
    relative weights suitable for AssemblyResult.adjusted_axes.

    genealogy_match counts are unbounded integer touch-tallies (from
    _constraint_basis_for_item) -- normalized here by the max count so the
    dominant axis reads 1.0 and others scale relative to it.
    warp_synthesized counts already arrive in [0,1] (from istates_to_axes),
    so normalizing by their own max is a no-op in shape, just re-scales the
    dominant axis to exactly 1.0 -- harmless either way.
    """
    counts = dict(basis.get("counts", {}) or {})
    values = [float(v or 0.0) for v in counts.values()]
    peak = max(values) if values else 0.0
    if peak <= 0.0:
        return {ax: 0.0 for ax in AXES}
    return {ax: round(float(counts.get(ax, 0.0) or 0.0) / peak, 4) for ax in AXES}


def dominant_axis_from_weights(weights: Dict[str, float]) -> str:
    if not weights:
        return ""
    return max(weights, key=lambda ax: weights.get(ax, 0.0))


def resolve_active_genealogy_item(
    genealogy: Any,
    live_profile: Dict[str, float],
    *,
    warp_field: Optional[WarpField] = None,
    source: str = "aurora_working_memory",
    layer: str = "expression",
    unresolved_text: str = "",
    persistence_key: str = "",
    warp_level: str = "expression_representation",
) -> ResolvedRepresentation:
    """
    THE resolver. Given the live turn's 15D profile, find which real
    genealogy item this turn is standing on -- or, if none covers it well
    enough, synthesize one honestly through WarpGenerator/WarpField.
    """
    if genealogy is None or not hasattr(genealogy, "links"):
        return ResolvedRepresentation(
            item_id=None, confidence=0.0, constraint_basis={},
            source="unresolved", notes="no genealogy instance available",
        )

    links = dict(getattr(genealogy, "links", {}) or {})
    candidates: Dict[str, Dict[str, float]] = {}
    for link_id, link in links.items():
        lid = str(link_id)
        if not genealogy.representation_is_eligible(lid):
            continue
        profile = _link_istate_profile(link)
        if profile:
            candidates[lid] = profile

    if candidates:
        best_id = max(
            candidates,
            key=lambda cid: AxisCoverageChecker.cosine(candidates[cid], live_profile),
        )
        best_score = AxisCoverageChecker.cosine(candidates[best_id], live_profile)
    else:
        best_id, best_score = None, 0.0

    if best_id is not None and best_score >= COVERAGE_THRESHOLD:
        basis = genealogy._constraint_basis_for_item(best_id)
        return ResolvedRepresentation(
            item_id=best_id,
            confidence=round(best_score, 4),
            constraint_basis=basis,
            source="genealogy_match",
            notes=f"matched existing genealogy item at cosine={best_score:.4f}",
        )

    # Genuine coverage gap -- build it canonically, don't hand-roll it.
    checker = AxisCoverageChecker(candidates)
    gap: Optional[CoverageGap] = checker.check(live_profile, source=source)
    if gap is None:
        # candidates was empty (cold genealogy) or check() itself found
        # sufficient coverage that our manual scan above disagreed with --
        # in either case, be honest that we have nothing real to ground on.
        return ResolvedRepresentation(
            item_id=best_id,
            confidence=round(best_score, 4),
            constraint_basis={},
            source="unresolved",
            notes="no coverage gap constructed and no eligible genealogy item met threshold",
        )

    generator = WarpGenerator()
    component = generator.generate(gap, level=warp_level, genealogy=genealogy)

    decision: Optional[WarpDecision] = None
    if warp_field is not None:
        trigger = WarpTrigger.NO_LANGUAGE_FORM if gap.is_sixth_axis_candidate else WarpTrigger.FAILED_COMPREHENSION
        demand = WarpDemand(
            source=source,
            layer=layer,
            trigger=trigger,
            unresolved_text=unresolved_text,
            profile=live_profile,
            severity=round(1.0 - gap.best_coverage, 4),
            persistence_key=persistence_key,
        )
        decision = warp_field.submit(demand)

    if component is None:
        # 6th-axis anomaly -- WarpGenerator.generate() already logged it.
        # Never force a representation into existence past that gate.
        return ResolvedRepresentation(
            item_id=None,
            confidence=round(gap.best_coverage, 4),
            constraint_basis={},
            source="unresolved",
            warp_decision=decision,
            notes="gap flagged as possible 6th-axis anomaly; accumulating evidence, not resolving yet",
        )

    axis_counts = istates_to_axes(component.axis_profile)
    synthesized_basis = {
        "counts": {ax: axis_counts.get(ax, 0.0) for ax in AXES},
        "signature": component.name or "derived",
        "generational_depth_counts": {ax: {} for ax in AXES},
        "generational_potency": {ax: 0.0 for ax in AXES},
    }
    return ResolvedRepresentation(
        item_id=None,
        confidence=round(gap.best_coverage, 4),
        constraint_basis=synthesized_basis,
        source="warp_synthesized",
        warp_component_id=component.component_id,
        warp_decision=decision,
        notes="freshly derived via WarpGenerator; not yet promoted into genealogy",
    )
