#!/usr/bin/env python3
"""
Canonical meaning-evolution registry for Aurora's five-constraint stack.

Meaning is treated as an emergent surface of the same five primitive axes that
govern the rest of the runtime:

    X = existence
    T = time
    N = energy / potential / change pressure
    B = boundary / structure
    A = agency / correction / interpretive selection

The registry below gives the runtime and genealogy layers a shared vocabulary
for single-axis meaning, pair couplings, selected higher-order compounds, and
their representations.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

AXIS_ORDER: Tuple[str, ...] = ("X", "T", "N", "B", "A")

AXIS_ALIASES = {
    "x": "X",
    "existence": "X",
    "unity": "X",
    "t": "T",
    "time": "T",
    "temporal": "T",
    "causality": "T",
    "n": "N",
    "energy": "N",
    "potential": "N",
    "change": "N",
    "cost": "N",
    "b": "B",
    "boundary": "B",
    "structure": "B",
    "information": "B",
    "a": "A",
    "agency": "A",
    "accuracy": "A",
    "correction": "A",
    "understanding": "A",
    "interpretation": "A",
}


def axis_token(raw: Any) -> Optional[str]:
    token = str(raw or "").strip().lower()
    if not token:
        return None
    return AXIS_ALIASES.get(token)


def canonical_signature(value: Any) -> str:
    if isinstance(value, Mapping):
        counts = {axis: 0 for axis in AXIS_ORDER}
        for raw_axis, raw_count in value.items():
            axis = axis_token(raw_axis)
            if axis is None:
                continue
            try:
                count = int(float(raw_count or 0))
            except Exception:
                count = 0
            if count > 0:
                counts[axis] += count
        parts = [f"{axis}^{counts[axis]}" for axis in AXIS_ORDER if counts[axis] > 0]
        return "*".join(parts) if parts else "0"

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return "0"
        if "^" in text or "*" in text:
            counts = {axis: 0 for axis in AXIS_ORDER}
            for raw_part in text.split("*"):
                part = str(raw_part or "").strip()
                if not part:
                    continue
                if "^" in part:
                    raw_axis, raw_count = part.split("^", 1)
                else:
                    raw_axis, raw_count = part, "1"
                axis = axis_token(raw_axis)
                if axis is None:
                    continue
                try:
                    count = int(float(raw_count.strip() or 0))
                except Exception:
                    count = 0
                if count > 0:
                    counts[axis] += count
            parts = [f"{axis}^{counts[axis]}" for axis in AXIS_ORDER if counts[axis] > 0]
            return "*".join(parts) if parts else "0"
        axes = [axis_token(token) for token in text.replace(",", " ").split()]
        return canonical_signature([axis for axis in axes if axis])

    axes: List[str] = []
    for raw_axis in list(value or []):
        axis = axis_token(raw_axis)
        if axis and axis not in axes:
            axes.append(axis)
    ordered = [axis for axis in AXIS_ORDER if axis in axes]
    return "*".join(f"{axis}^1" for axis in ordered) if ordered else "0"


def _profile(
    signature: str,
    *,
    label: str,
    summary: str,
    representation: str = "",
    stage: str = "",
    aliases: Sequence[str] = (),
    notes: Sequence[str] = (),
) -> Dict[str, Any]:
    normalized = canonical_signature(signature)
    axes = [part.split("^", 1)[0] for part in normalized.split("*") if "^" in part]
    return {
        "signature": normalized,
        "axes": tuple(axes),
        "arity": len(axes),
        "label": str(label or ""),
        "summary": str(summary or ""),
        "representation": str(representation or ""),
        "stage": str(stage or ""),
        "aliases": tuple(str(item or "") for item in aliases if str(item or "").strip()),
        "notes": tuple(str(item or "") for item in notes if str(item or "").strip()),
    }


MEANING_PROFILES: Dict[str, Dict[str, Any]] = {
    "X^1": _profile(
        "X^1",
        label="unity",
        summary="Meaning begins as the bare distinction that lets something be this instead of not-this.",
        representation="membrane",
        stage="primitive",
        aliases=("boolean_yes", "existence"),
        notes=("The lowest-order meaning surface is admissible separation.",),
    ),
    "T^1": _profile(
        "T^1",
        label="causality",
        summary="Meaning becomes sequence: a relation between states rather than a frozen thing.",
        representation="sequence",
        stage="primitive",
        aliases=("time", "flow"),
    ),
    "N^1": _profile(
        "N^1",
        label="potential",
        summary="Meaning becomes change-pressure: the latent capacity for motion, work, or transformation.",
        representation="change",
        stage="primitive",
        aliases=("energy", "magnitude"),
    ),
    "B^1": _profile(
        "B^1",
        label="structure",
        summary="Meaning becomes information: a bounded form that can hold distinctions and carry record.",
        representation="information",
        stage="primitive",
        aliases=("boundary", "definition"),
    ),
    "A^1": _profile(
        "A^1",
        label="understanding",
        summary="Meaning becomes interpretation: selective fit that can model, correct, and steer within a limit.",
        representation="interpretation",
        stage="primitive",
        aliases=("agency", "correction", "selection"),
    ),
    "X^1*T^1": _profile(
        "X^1*T^1",
        label="persistence",
        summary="Existence stretched through time becomes duration: a state that keeps holding long enough to matter.",
        representation="trace",
        stage="pair",
        aliases=("history",),
    ),
    "X^1*N^1": _profile(
        "X^1*N^1",
        label="magnitude",
        summary="Existence under energy becomes intensity: the amount of reality or force occupying a state.",
        representation="mass_intensity",
        stage="pair",
        aliases=("intensity",),
    ),
    "X^1*B^1": _profile(
        "X^1*B^1",
        label="identity",
        summary="Existence bounded by a limit becomes this rather than that: an identifiable thing with a skin.",
        representation="membrane",
        stage="pair",
        aliases=("definition", "separation"),
    ),
    "X^1*A^1": _profile(
        "X^1*A^1",
        label="recognition",
        summary="Existence reflected through interpretive selection becomes the first internal yes: the 'I am'.",
        representation="observation",
        stage="pair",
        aliases=("self_awareness", "i_am"),
    ),
    "T^1*N^1": _profile(
        "T^1*N^1",
        label="momentum",
        summary="Energy pushed through duration becomes directionality: process moving toward a next state.",
        representation="pre_agency_will",
        stage="pair",
        aliases=("process", "will"),
    ),
    "T^1*B^1": _profile(
        "T^1*B^1",
        label="complexity",
        summary="Time passing across a limit becomes accumulated record: depth, memory, and morphological trace.",
        representation="memory",
        stage="pair",
        aliases=("trace", "morphology"),
    ),
    "T^1*A^1": _profile(
        "T^1*A^1",
        label="strategy",
        summary="Time under interpretive selection becomes projected sequence: planning, expectation, and purpose.",
        representation="planning",
        stage="pair",
        aliases=("purpose", "expectation"),
    ),
    "N^1*B^1": _profile(
        "N^1*B^1",
        label="tension",
        summary="Potential meeting a limit becomes held pressure: a loaded structure ready to do work.",
        representation="pressure",
        stage="pair",
        aliases=("conflict", "resonance"),
    ),
    "N^1*A^1": _profile(
        "N^1*A^1",
        label="force",
        summary="Potential under selection becomes controlled power: energy directed instead of merely dissipated.",
        representation="control",
        stage="pair",
        aliases=("power",),
    ),
    "B^1*A^1": _profile(
        "B^1*A^1",
        label="map",
        summary="Boundary interpreted from within becomes a translator: an internal model of the limit itself.",
        representation="translator",
        stage="pair",
        aliases=("understanding", "abstraction"),
    ),
    "T^1*N^1*B^1": _profile(
        "T^1*N^1*B^1",
        label="synergy",
        summary="Potential cycling through time inside a limit becomes a stable pattern that can persist as signal.",
        representation="signal",
        stage="compound",
        aliases=("complexity", "machine"),
        notes=("This is the highest pre-agency meaning surface: a pattern that holds.",),
    ),
    "T^1*N^1*A^1": _profile(
        "T^1*N^1*A^1",
        label="ambition",
        summary="Momentum under selection becomes directed intent: will that knows where it wants to go.",
        representation="directed_intent",
        stage="compound",
        aliases=("purposeful_will",),
    ),
    "N^1*B^1*A^1": _profile(
        "N^1*B^1*A^1",
        label="problem_solving",
        summary="Tension under selection becomes managed pressure: power applied against a limit to open resolution.",
        representation="engine",
        stage="compound",
        aliases=("power",),
    ),
    "T^1*B^1*A^1": _profile(
        "T^1*B^1*A^1",
        label="narrative",
        summary="Record interpreted across time becomes identity-in-motion: history organized into a meaningful chain.",
        representation="identity",
        stage="compound",
        aliases=("history",),
    ),
    "X^1*T^1*N^1*B^1*A^1": _profile(
        "X^1*T^1*N^1*B^1*A^1",
        label="consciousness",
        summary="When unity, causality, potential, structure, and understanding cohere, meaning perceives its own limit.",
        representation="hologram",
        stage="integrated",
        aliases=("self_model",),
    ),
}


def axis_profiles() -> Dict[str, Dict[str, Any]]:
    return {
        axis: copy.deepcopy(profile)
        for axis, profile in (
            ("X", MEANING_PROFILES["X^1"]),
            ("T", MEANING_PROFILES["T^1"]),
            ("N", MEANING_PROFILES["N^1"]),
            ("B", MEANING_PROFILES["B^1"]),
            ("A", MEANING_PROFILES["A^1"]),
        )
    }


def meaning_profile_for_signature(signature: Any) -> Optional[Dict[str, Any]]:
    normalized = canonical_signature(signature)
    profile = MEANING_PROFILES.get(normalized)
    return copy.deepcopy(profile) if profile else None


def meaning_profile_for_counts(counts: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    normalized = canonical_signature(counts)
    return meaning_profile_for_signature(normalized)


def rank_meaning_profiles(
    activations: Mapping[str, Any],
    *,
    limit: int = 5,
    min_axis_activation: float = 0.45,
    min_score: float = 0.5,
    include_singletons: bool = True,
) -> List[Dict[str, Any]]:
    axis_values = {
        axis: max(0.0, min(1.0, float(activations.get(axis, 0.0) or 0.0)))
        for axis in AXIS_ORDER
    }
    ranked: List[Dict[str, Any]] = []
    for signature, profile in MEANING_PROFILES.items():
        axes = list(profile.get("axes", ()) or ())
        if not axes:
            continue
        values = [axis_values.get(axis, 0.0) for axis in axes]
        if not values or min(values) < float(min_axis_activation):
            continue
        arity = len(values)
        if arity <= 1 and not include_singletons:
            continue
        complexity_scale = max(0.55, 1.0 - (0.08 * max(0, arity - 1)))
        score = (sum(values) / float(arity)) * complexity_scale
        if score < float(min_score):
            continue
        item = copy.deepcopy(profile)
        item["score"] = round(score, 4)
        item["axis_activations"] = {axis: round(axis_values.get(axis, 0.0), 4) for axis in axes}
        ranked.append(item)
    ranked.sort(
        key=lambda item: (
            float(item.get("score", 0.0) or 0.0),
            int(item.get("arity", 0) or 0),
            str(item.get("label", "") or ""),
        ),
        reverse=True,
    )
    return ranked[: max(1, int(limit or 1))]


# ── Developmental chain ──────────────────────────────────────────────────────
#
# Each developmental stage emerges from the previous through a specific
# constraint transition.  The chain is a REQUIRED SEQUENCE — a stage cannot
# genuinely form until its prerequisite signatures are stable:
#
#   Existence  →  Information  →  Relational structure  →  Belief
#   →  Purpose  →  Meaning  →  Understanding
#   →  Communication  →  Coherence
#
# "Primal impulse" is the inherited N-axis (energy/potential) pressure that
# pushes Belief toward directed action.  It is not a separate stage but the
# force that enables the Belief→Purpose transition.
#
# "Salience" is the A-axis (agency/selection) operation that filters which
# purposes are interpreted.  It is what converts Purpose → Meaning.
#
# Each stage entry specifies:
#   signature            canonical meaning-form signature that must be active
#   bottleneck_axis      the constraint axis whose pressure drives this transition
#   prerequisite_signatures  signatures that must ALSO be active first
#   pressure_dims        training dimensions to target when this stage is bottleneck
#   min_score_override   higher threshold for stages requiring strong stability

DEVELOPMENTAL_CHAIN: Tuple[Dict[str, Any], ...] = (
    {
        "stage_index": 1,
        "name": "information",
        "signature": "B^1",
        "label": "structure",
        "bottleneck_axis": "B",
        "prerequisite_signatures": (),
        "pressure_dims": ("semantic_precision",),
        "description": (
            "Existence discriminates into bounded information — "
            "the first holding of a distinction."
        ),
    },
    {
        "stage_index": 2,
        "name": "relational_structure",
        "signature": "T^1*B^1",
        "label": "complexity",
        "bottleneck_axis": "T",
        "prerequisite_signatures": ("B^1",),
        "pressure_dims": ("context_carryover", "multi_turn_stability"),
        "description": (
            "Information persisting through time accumulates relational structure — "
            "memory, morphology, and trace."
        ),
    },
    {
        "stage_index": 3,
        "name": "belief",
        "signature": "N^1*B^1",
        "label": "tension",
        "bottleneck_axis": "N",
        "prerequisite_signatures": ("T^1*B^1",),
        "pressure_dims": ("compression_elaboration_fit", "uncertainty_signaling"),
        "description": (
            "Relational stability under energy pressure becomes held tension — "
            "a committed structural state ready to do work (belief)."
        ),
    },
    {
        "stage_index": 4,
        "name": "purpose",
        "signature": "T^1*N^1*A^1",
        "label": "ambition",
        "bottleneck_axis": "A",
        "prerequisite_signatures": ("N^1*B^1",),
        "pressure_dims": ("emotional_calibration", "perspective_integration"),
        "description": (
            "Belief interacting with primal motivational pressure (N-axis impulse) "
            "under interpretive selection (A-axis) becomes directed purpose."
        ),
    },
    {
        "stage_index": 5,
        "name": "meaning",
        "signature": "N^1*B^1*A^1",
        "label": "problem_solving",
        "bottleneck_axis": "A",
        "prerequisite_signatures": ("T^1*N^1*A^1",),
        "pressure_dims": ("semantic_precision", "perspective_integration"),
        "description": (
            "Purpose prioritized through salience (A-axis selection) becomes meaning — "
            "interpretation of salient purpose relative to the system's own boundaries."
        ),
    },
    {
        "stage_index": 6,
        "name": "understanding",
        "signature": "T^1*B^1*A^1",
        "label": "narrative",
        "bottleneck_axis": "T",
        "prerequisite_signatures": ("N^1*B^1*A^1",),
        "pressure_dims": ("context_carryover", "coherence_maintenance"),
        "description": (
            "Meaning organized through intent across time becomes understanding — "
            "history structured into a correctable, meaningful chain."
        ),
    },
    {
        "stage_index": 7,
        "name": "communication",
        "signature": "X^1*T^1*N^1*B^1*A^1",
        "label": "consciousness",
        "bottleneck_axis": "X",
        "prerequisite_signatures": ("T^1*B^1*A^1",),
        "pressure_dims": ("coherence_maintenance", "uncertainty_signaling"),
        "description": (
            "Understanding shared across the existence boundary becomes communication — "
            "the limit itself made transmissible."
        ),
    },
    {
        "stage_index": 8,
        "name": "coherence",
        "signature": "X^1*T^1*N^1*B^1*A^1",
        "label": "consciousness",
        "bottleneck_axis": "X",
        "prerequisite_signatures": ("X^1*T^1*N^1*B^1*A^1",),
        "pressure_dims": ("coherence_maintenance",),
        "description": (
            "Communication aligned across all axes becomes coherence — "
            "self-perception of the system's own constraint boundary."
        ),
        "min_score_override": 0.72,   # Coherence requires a strong consciousness form
        "frame_continuity_floor": 0.62,  # and sustained relational stability
    },
)


def assess_developmental_stage(
    meaning_forms: List[Dict[str, Any]],
    *,
    min_score: float = 0.52,
    frame_continuity: float = 0.0,
) -> Dict[str, Any]:
    """
    Walk the developmental chain and identify the current stage.

    A stage is considered achieved when:
      - Its canonical signature appears in meaning_forms with score >= threshold
      - All prerequisite signatures are also active at >= min_score

    The first un-achieved stage is the developmental bottleneck.  Pressure
    should be directed there — not at stages that are two or more steps ahead.

    Args:
        meaning_forms:     output of rank_meaning_profiles() for the current turn
        min_score:         minimum score for a signature to count as "active"
        frame_continuity:  used to gate the coherence stage (stage 8)

    Returns dict with:
        current_stage        int    highest consecutive achieved stage index (0 = none)
        current_stage_name   str
        bottleneck_name      str    name of next stage to develop
        bottleneck_axis      str|None  constraint axis that drives the transition
        pressure_dims        tuple  training dimensions for the bottleneck
        stage_completion     float  current_stage / total_stages  [0, 1]
        active_signatures    dict   {signature: best_score}
        gap_to_next          float  how far the next-stage signature is from threshold
    """
    # Collect best score seen for each signature in the current meaning forms
    active: Dict[str, float] = {}
    for form in (meaning_forms or []):
        sig = str(form.get("signature", "") or "")
        score = float(form.get("score", 0.0) or 0.0)
        if sig and score > active.get(sig, 0.0):
            active[sig] = score

    highest_stage = 0
    highest_name = "none"

    for entry in DEVELOPMENTAL_CHAIN:
        sig = entry["signature"]
        prereqs = entry.get("prerequisite_signatures", ())
        threshold = float(entry.get("min_score_override", min_score))

        # Stage 8 (coherence) also requires sustained frame continuity
        extra_gate = True
        if entry.get("frame_continuity_floor"):
            extra_gate = frame_continuity >= float(entry["frame_continuity_floor"])

        prereqs_met = all(active.get(p, 0.0) >= min_score for p in prereqs)
        sig_met = active.get(sig, 0.0) >= threshold

        if sig_met and prereqs_met and extra_gate:
            highest_stage = entry["stage_index"]
            highest_name = entry["name"]
        else:
            break   # Chain breaks at first un-achieved stage

    # Find the next stage to develop
    next_entry: Optional[Dict[str, Any]] = None
    for entry in DEVELOPMENTAL_CHAIN:
        if entry["stage_index"] > highest_stage:
            next_entry = entry
            break

    # How far is the next-stage signature from its activation threshold?
    gap = 0.0
    if next_entry:
        sig = next_entry["signature"]
        needed = float(next_entry.get("min_score_override", min_score))
        gap = round(max(0.0, needed - active.get(sig, 0.0)), 4)

    return {
        "current_stage": highest_stage,
        "current_stage_name": highest_name,
        "bottleneck_name": next_entry["name"] if next_entry else "complete",
        "bottleneck_axis": next_entry.get("bottleneck_axis") if next_entry else None,
        "pressure_dims": tuple(next_entry.get("pressure_dims", ())) if next_entry else (),
        "stage_description": str(next_entry.get("description", "") if next_entry else
                                 "All developmental stages achieved."),
        "stage_completion": round(highest_stage / max(1, len(DEVELOPMENTAL_CHAIN)), 4),
        "active_signatures": active,
        "gap_to_next": gap,
    }
