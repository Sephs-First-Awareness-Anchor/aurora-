#!/usr/bin/env python3
"""
AURORA REFLEXIVE INTERPRETER  v2
==================================
Module: aurora_reflexive_interpreter.py
Layer: Constraint Ontology — Expression Re-Entry and Understanding

Authors: Sunni (Sir) Morningstar and Cael Devo
Created: April 2026  |  Refined: April 2026

WHAT CHANGED FROM v1
---------------------
Two issues fixed using Aurora's own codestack:

1. SEMANTIC MATCHING  (was: keyword bags → now: UtteranceParser)
   aurora_utterance_parser.py replaces the keyword scorer entirely.
   UtteranceFrame → constraint:
       EXPERIENTIAL  → B  (boundary / meaning / self-other)
       CLARIFYING    → A  (agency / correction / understanding)
       CHALLENGING   → A  (authorship under pressure)
       HYPOTHETICAL  → T  (temporal / belief / transition)
       CALLBACK      → T  (prior-self temporal reference)
       CONTRASTIVE   → B  (distinction / differentiation)
       SPECULATING   → X  (admissibility / uncertainty)
       ACKNOWLEDGING → X  (accepting something as real)
       EXPLORATORY   → A  (seeking understanding)
       ASSERTING     → X  (information / admissibility claim)
   Stance → dimension:
       challenging/clarifying/accepting → OPERATOR
       tentative/speculative            → POLARITY
       contrastive/curious              → DIFFERENCE
       emphatic/subjective              → MAGNITUDE

2. RECONCILIATION  (was: hand-tuned thresholds → now: Worth formula)
   From aurora_worth_evaluator.py: W(x) = 1/(1 + Σᵢ wᵢ·|Δforced|)
   WorthTrajectory (RISING/STABLE/FALLING/OSCILLATING) drives understanding state.
   polarity_coherent = surface frame aligned with core intent = reflexive closure.

3. LIVE COST MODULATION  (new)
   CostDiffScore amplifier available when DifferenceSnapshot present.
"""

from __future__ import annotations

import json
import math
import re
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Deque, Dict, List, Optional, Tuple

# ── Aurora codestack ─────────────────────────────────────────────────────────
try:
    from aurora_internal.aurora_utterance_parser import UtteranceParser
    _PARSER_AVAILABLE = True
except ImportError:
    _PARSER_AVAILABLE = False

try:
    from aurora_manifold_directory_reader import ManifoldDirectory, NoncompManifold, SlotView
    _DIRECTORY_AVAILABLE = True
except ImportError:
    _DIRECTORY_AVAILABLE = False

try:
    from aurora_constraint_manifold_router import (
        ManifoldRouter, RouteIndex, RouteSignal, RouteResult,
        SlotCoord, BandPosition, build_route_index,
    )
    _ROUTER_AVAILABLE = True
except ImportError:
    _ROUTER_AVAILABLE = False
    class BandPosition:
        INSIDE = "inside"; LOW = "low"; HIGH = "high"

try:
    from aurora_internal.aurora_noncomp_registry import NonCompDimension
    _NONCOMP_DIMENSIONS = tuple(dim.name for dim in NonCompDimension)
except Exception:
    _NONCOMP_DIMENSIONS = ("POLARITY", "MAGNITUDE", "OPERATOR", "COST", "DIFFERENCE")

try:
    from aurora_noncomp_layer_compiler import NonCompLayerCompiler
    _NONCOMP_LAYER_COMPILER = NonCompLayerCompiler()
    _NONCOMP_LAYER_AVAILABLE = True
except Exception:
    _NONCOMP_LAYER_COMPILER = None
    _NONCOMP_LAYER_AVAILABLE = False

try:
    from aurora_understanding_sediment import (
        UnderstandingSedimentOverlay, PersistentWorthLedger,
        recall_confidence_boost, slot_key as _sediment_slot_key,
    )
    _SEDIMENT_AVAILABLE = True
except ImportError:
    _SEDIMENT_AVAILABLE = False

SHIFT_COST: Dict[str, float] = {"X":1.0,"T":4.0,"N":10.0,"B":40.0,"A":150.0}
AXES = ("X","T","N","B","A")
DIM_NAMES = ("POLARITY","MAGNITUDE","OPERATOR","COST","DIFFERENCE")
UNDERSTANDING_THRESHOLD = 0.55
DENSE_THRESHOLD  = 0.70
SPARSE_THRESHOLD = 0.35

# ── Frame / stance → constraint / dimension ───────────────────────────────────
FRAME_TO_CONSTRAINT: Dict[str, str] = {
    "experiential":  "B", "clarifying":    "A", "challenging":   "A",
    "hypothetical":  "T", "callback":      "T", "contrastive":   "B",
    "speculating":   "X", "acknowledging": "X", "exploratory":   "A",
    "asserting":     "X", "unknown":       "N",
}
STANCE_TO_DIMENSION: Dict[str, str] = {
    "challenging": "OPERATOR", "clarifying":  "OPERATOR", "accepting":   "OPERATOR",
    "curious":     "DIFFERENCE","tentative":  "POLARITY",  "speculative": "POLARITY",
    "contrastive": "DIFFERENCE","emphatic":   "MAGNITUDE", "subjective":  "MAGNITUDE",
    "neutral":     "OPERATOR",
}
ROLE_TO_DIMENSION: Dict[str, str] = {
    "uncertainty": "POLARITY", "certainty":    "POLARITY", "emphasis":      "MAGNITUDE",
    "contrast":    "DIFFERENCE","callback":    "OPERATOR", "hypothesis":    "POLARITY",
    "experience":  "OPERATOR", "clarification":"OPERATOR",
}
HIGH_CONF_FRAMES = {"experiential","clarifying","challenging","hypothetical","callback","contrastive"}
MID_CONF_FRAMES  = {"speculating","acknowledging","asserting"}

_RECALL_PATTERNS = (
    r"\bremember\b",
    r"\brecall\b",
    r"\bwhat(?:'s|\s+is|\s+was|\s+were)\s+my\b",
    r"\bwhat\s+did\s+i\s+(?:say|call|name|mean)\b",
    r"\bwhat\s+was\s+my\b",
    r"\bwhat\s+did\s+you\s+say\s+my\b",
)
_CLARIFICATION_PATTERNS = (
    r"\bclarify\b",
    r"\bwhat\s+do\s+you\s+mean\b",
    r"\bwhat\s+did\s+you\s+mean\b",
    r"\bwhat\s+you\s+meant\b",
    r"\bcan\s+you\s+clarify\b",
    r"\bhelp\s+me\s+understand\b",
    r"\bexplain\s+what\s+you\s+meant\b",
)
_MEANING_PATTERNS = (
    r"\bwhat\s+does\s+.+\s+mean\b",
    r"\bmeaning\s+of\b",
    r"\bdefinition\s+of\b",
    r"\bdefine\b",
)
_FACTUAL_LOOKUP_PATTERNS = (
    r"\bwhat\s+is\b",
    r"\bwho\s+is\b",
    r"\bwhere\s+is\b",
    r"\bwhen\s+is\b",
    r"\blook\s+up\b",
    r"\bsearch\s+for\b",
)
_BOUNDARY_MISMATCH_PATTERNS = (
    r"\bnot\s+what\s+i\s+meant\b",
    r"\bnot\s+what\s+i\s+said\b",
    r"\bthat's\s+not\b",
    r"\bthat\s+is\s+not\b",
    r"\bdoes(?:n't|\s+not)\s+fit\b",
    r"\bmisunderstood\b",
    r"\bmismatch\b",
)
_COST_WORDS = {
    "cost", "price", "effort", "energy", "resource", "resources", "overhead",
    "commit", "commitment", "sustain", "sustaining", "expense", "expensive",
    "burden",
}


def _matches_any_pattern(text: str, patterns: Tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _semantic_override(
    expression: str,
    parsed: Dict[str, object],
) -> Tuple[Optional[str], Optional[str], Optional[str], float]:
    lower_text = str(expression or "").strip().lower()
    topic_words = {str(word or "").strip().lower() for word in list(parsed.get("topic_words", []) or []) if str(word or "").strip()}
    query_type = str(parsed.get("query_type", "") or "").strip().lower()
    is_callback = bool(parsed.get("is_callback"))
    is_clarification = bool(parsed.get("is_clarification"))
    negated = bool(parsed.get("negated"))

    second_person_clarification = (
        _matches_any_pattern(lower_text, _CLARIFICATION_PATTERNS) or
        (is_clarification and bool(re.search(r"\b(?:you|your)\b", lower_text)))
    )
    self_recall = (
        _matches_any_pattern(lower_text, _RECALL_PATTERNS) or
        (query_type == "definition" and bool(re.search(r"\bmy\b", lower_text)))
    )
    energetic_cost = bool(topic_words & _COST_WORDS) or _matches_any_pattern(lower_text, (r"\bwhat\s+would\s+it\s+cost\b",))
    boundary_mismatch = (
        (
            "boundary" in topic_words or
            "boundary" in lower_text or
            "meaning" in lower_text or
            "meant" in lower_text
        ) and
        (negated or is_callback or _matches_any_pattern(lower_text, _BOUNDARY_MISMATCH_PATTERNS))
    )
    meaning_definition = (
        (
            query_type == "definition" or
            _matches_any_pattern(lower_text, _MEANING_PATTERNS)
        ) and
        not self_recall and
        not second_person_clarification and
        not bool(re.search(r"\b(?:this|that)\s+mean\b", lower_text))
    )
    factual_lookup = (
        not self_recall and
        not second_person_clarification and
        not meaning_definition and
        (
            query_type in {"factual_entity", "factual_general", "weather_location"} or
            _matches_any_pattern(lower_text, _FACTUAL_LOOKUP_PATTERNS)
        )
    )

    if energetic_cost:
        return "N", "COST", "energetic_cost", 0.92
    if self_recall:
        return "T", "OPERATOR", "temporal_recall", 0.94
    if boundary_mismatch:
        dim = "DIFFERENCE" if negated or _matches_any_pattern(lower_text, _BOUNDARY_MISMATCH_PATTERNS) else "OPERATOR"
        return "B", dim, "boundary_mismatch", 0.91
    if second_person_clarification:
        return "A", "OPERATOR", "agency_clarification", 0.90
    if meaning_definition:
        return "B", "OPERATOR", "boundary_meaning", 0.90
    if factual_lookup:
        return "X", "OPERATOR", "existential_lookup", 0.86
    return None, None, None, 0.0


def _normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(max(0.0, float(value or 0.0)) for value in weights.values()) or 1.0
    return {key: max(0.0, float(value or 0.0)) / total for key, value in weights.items()}


def _project_noncomp_state(
    match: MatchResult,
    *,
    worth_score: float,
    depth_score: float,
    origin_weight: float,
    origin_region: str,
    route: Optional["RouteResult"],
    expression: str,
) -> Dict[str, object]:
    """
    Compact a parsed utterance into the 25 atomic NonComp channels.

    The 25-channel matrix stays visible as internal substrate, while the
    dominant channel and compaction metrics give downstream systems a
    faster surface handle on what the utterance is doing.
    """
    expr_low = str(expression or "").lower()

    constraint_weights: Dict[str, float] = {ax: 0.04 for ax in AXES}
    constraint_weights[match.constraint] += 0.42
    if match.frame in HIGH_CONF_FRAMES:
        constraint_weights[match.constraint] += 0.05
    elif match.frame in MID_CONF_FRAMES:
        constraint_weights[match.constraint] += 0.03
    if route is not None and getattr(route, "admitted", False):
        constraint_weights[match.constraint] += 0.05
    if origin_region == "dense":
        constraint_weights[match.constraint] += 0.03
    elif origin_region == "sparse":
        constraint_weights[match.constraint] += 0.01
    if match.semantic_override == "temporal_recall":
        constraint_weights["T"] += 0.15
    elif match.semantic_override == "energetic_cost":
        constraint_weights["N"] += 0.15
    elif match.semantic_override == "boundary_mismatch":
        constraint_weights["B"] += 0.15
    elif match.semantic_override == "agency_clarification":
        constraint_weights["A"] += 0.15
    elif match.semantic_override == "boundary_meaning":
        constraint_weights["B"] += 0.12
    elif match.semantic_override == "existential_lookup":
        constraint_weights["X"] += 0.12
    if "what does" in expr_low or "define" in expr_low or "definition" in expr_low:
        constraint_weights["B"] += 0.04
    if "remember" in expr_low or "recall" in expr_low:
        constraint_weights["T"] += 0.04
    if "cost" in expr_low or "energy" in expr_low or "effort" in expr_low:
        constraint_weights["N"] += 0.04
    constraint_weights = _normalize_weights(constraint_weights)

    dimension_weights: Dict[str, float] = {dim: 0.04 for dim in _NONCOMP_DIMENSIONS}
    dimension_weights[match.dimension] += 0.42
    stance_bias = {
        "challenging": "OPERATOR",
        "clarifying": "OPERATOR",
        "accepting": "OPERATOR",
        "curious": "DIFFERENCE",
        "tentative": "POLARITY",
        "speculative": "POLARITY",
        "contrastive": "DIFFERENCE",
        "emphatic": "MAGNITUDE",
        "subjective": "MAGNITUDE",
    }.get(str(match.stance or "").strip().lower())
    if stance_bias:
        dimension_weights[stance_bias] += 0.10
    role_bias = {
        "uncertainty": "POLARITY",
        "certainty": "POLARITY",
        "emphasis": "MAGNITUDE",
        "contrast": "DIFFERENCE",
        "callback": "OPERATOR",
        "hypothesis": "POLARITY",
        "experience": "OPERATOR",
        "clarification": "OPERATOR",
    }.get(str(match.dominant_role or "").strip().lower())
    if role_bias:
        dimension_weights[role_bias] += 0.08
    if match.semantic_override == "energetic_cost":
        dimension_weights["COST"] += 0.18
    elif match.semantic_override == "temporal_recall":
        dimension_weights["OPERATOR"] += 0.10
    elif match.semantic_override == "boundary_mismatch":
        dimension_weights["DIFFERENCE"] += 0.16
    elif match.semantic_override == "agency_clarification":
        dimension_weights["OPERATOR"] += 0.12
    elif match.semantic_override == "existential_lookup":
        dimension_weights["OPERATOR"] += 0.12
    if "not what i meant" in expr_low or "that's not what i meant" in expr_low:
        dimension_weights["DIFFERENCE"] += 0.06
    if "what" in expr_low and "mean" in expr_low:
        dimension_weights["OPERATOR"] += 0.04
    dimension_weights = _normalize_weights(dimension_weights)

    channels: Dict[str, Dict[str, float]] = {}
    flat_channels: List[Dict[str, object]] = []
    channel_vector: List[float] = []
    for ax in AXES:
        row: Dict[str, float] = {}
        for dim in _NONCOMP_DIMENSIONS:
            score = round(constraint_weights.get(ax, 0.0) * dimension_weights.get(dim, 0.0), 6)
            row[dim] = score
            channel_vector.append(score)
            flat_channels.append({
                "channel": f"{ax}:{dim}",
                "constraint": ax,
                "dimension": dim,
                "score": score,
            })
        channels[ax] = row

    total = sum(channel_vector) or 1.0
    if abs(total - 1.0) > 1e-9:
        for ax in AXES:
            for dim in _NONCOMP_DIMENSIONS:
                channels[ax][dim] = round(channels[ax][dim] / total, 6)
        flat_channels = [
            {
                "channel": item["channel"],
                "constraint": item["constraint"],
                "dimension": item["dimension"],
                "score": round(float(item["score"]) / total, 6),
            }
            for item in flat_channels
        ]
        channel_vector = [round(score / total, 6) for score in channel_vector]

    flat_channels.sort(key=lambda item: float(item["score"]), reverse=True)
    top_channels = flat_channels[:5]
    salience = float(top_channels[0]["score"]) if top_channels else 0.0
    compaction = float(sum(float(item["score"]) for item in top_channels)) if top_channels else 0.0
    entropy = 0.0
    for score in channel_vector:
        if score <= 0.0:
            continue
        entropy -= score * math.log(score, 25)

    focus_channel = f"{match.constraint}:{match.dimension}"
    target_weights = _normalize_weights(dict(constraint_weights))
    manifold_layers: Dict[str, Dict[str, object]] = {}
    manifold_slots: List[Dict[str, object]] = []
    manifold_vector: List[float] = []
    for target in AXES:
        target_weight = float(target_weights.get(target, 0.0) or 0.0)
        compiled_layer = None
        if _NONCOMP_LAYER_AVAILABLE and _NONCOMP_LAYER_COMPILER is not None:
            try:
                compiled_layer = _NONCOMP_LAYER_COMPILER.compile_layer(target)
            except Exception:
                compiled_layer = None

        layer_slots: List[Dict[str, object]] = []
        for c_law in AXES:
            for dim in _NONCOMP_DIMENSIONS:
                base_score = float(channels.get(c_law, {}).get(dim, 0.0) or 0.0)
                score = round(target_weight * base_score, 6)
                slot: Dict[str, object] = {
                    "slot_id": f"NC_LAYER:{target}:{c_law}:{dim}",
                    "target_constraint": target,
                    "law_constraint": c_law,
                    "law_dimension": dim,
                    "law_channel": f"NC:{c_law}:{dim}",
                    "score": score,
                }
                if compiled_layer is not None:
                    try:
                        compiled_slot = compiled_layer.slot_by_law(c_law, dim)
                    except Exception:
                        compiled_slot = None
                    if compiled_slot is not None:
                        slot.update(
                            {
                                "slot_name": str(getattr(compiled_slot, "name", "") or ""),
                                "description": str(getattr(compiled_slot, "description", "") or ""),
                                "cluster": str(getattr(getattr(compiled_slot, "cluster", None), "value", "") or ""),
                                "position": int(getattr(compiled_slot, "position", 0) or 0),
                                "is_diagonal": bool(getattr(compiled_slot, "is_diagonal", False)),
                                "is_self_family": bool(getattr(getattr(compiled_slot, "tags", None), "is_self_family", False)),
                            }
                        )
                layer_slots.append(slot)
                manifold_slots.append(slot)
                manifold_vector.append(score)

        layer_slots.sort(key=lambda item: float(item.get("score", 0.0) or 0.0), reverse=True)
        layer_top = layer_slots[:5]
        layer_entropy = 0.0
        layer_total = sum(float(item.get("score", 0.0) or 0.0) for item in layer_slots) or 1.0
        for item in layer_slots:
            score = float(item.get("score", 0.0) or 0.0)
            if score <= 0.0:
                continue
            p = score / layer_total
            layer_entropy -= p * math.log(p, 25)

        manifold_layers[target] = {
            "target_constraint": target,
            "target_weight": round(target_weight, 6),
            "representational_name": (
                str(getattr(compiled_layer, "representational_name", "") or "")
                if compiled_layer is not None else ""
            ),
            "slot_count": len(layer_slots),
            "top_slots": layer_top,
            "slots": layer_slots,
            "entropy": round(layer_entropy, 6),
            "dominant_slot": layer_slots[0] if layer_slots else {},
        }

    manifold_total = sum(manifold_vector) or 1.0
    manifold_vector = [round(score / manifold_total, 6) for score in manifold_vector]
    manifold_slots.sort(key=lambda item: float(item.get("score", 0.0) or 0.0), reverse=True)
    manifold_top = manifold_slots[:12]
    manifold_entropy = 0.0
    for score in manifold_vector:
        if score <= 0.0:
            continue
        manifold_entropy -= score * math.log(score, 125)
    dominant_target = max(target_weights.items(), key=lambda kv: kv[1])[0] if target_weights else match.constraint
    top_slot_labels = []
    for item in manifold_top[:5]:
        slot_name = str(item.get("slot_name", "") or item.get("law_channel", "") or item.get("slot_id", "") or "")
        top_slot_labels.append(
            f"{item.get('target_constraint', '')}:{slot_name}@{float(item.get('score', 0.0) or 0.0):.3f}"
        )
    manifold_translation = (
        f"125-layer manifold: target={dominant_target}, "
        f"basis={focus_channel}, top={' | '.join(top_slot_labels)}"
        if top_slot_labels else f"125-layer manifold: target={dominant_target}, basis={focus_channel}"
    )
    return {
        "focus": {
            "constraint": match.constraint,
            "dimension": match.dimension,
            "channel": focus_channel,
            "nc_name": match.nc_name or "",
            "frame": match.frame,
            "stance": match.stance,
        },
        "constraint_weights": {ax: round(val, 6) for ax, val in constraint_weights.items()},
        "dimension_weights": {dim: round(val, 6) for dim, val in dimension_weights.items()},
        "channels": channels,
        "channel_vector": channel_vector,
        "top_channels": top_channels,
        "salience": round(salience, 6),
        "compaction": round(compaction, 6),
        "entropy": round(entropy, 6),
        "basis": {
            "constraint": match.constraint,
            "dimension": match.dimension,
            "worth_score": round(float(worth_score), 6),
            "depth_score": round(float(depth_score), 6),
            "origin_weight": round(float(origin_weight), 6),
            "origin_region": str(origin_region or ""),
        },
        "basis_channel": focus_channel,
        "channel_count": 25,
        "manifold_slot_count": 125,
        "layer_count": 5,
        "target_weights": {ax: round(val, 6) for ax, val in target_weights.items()},
        "dominant_target": dominant_target,
        "manifold_entropy": round(manifold_entropy, 6),
        "manifold_translation": manifold_translation,
        "semantic_translation": manifold_translation,
        "manifold": {
            "slot_count": 125,
            "layer_count": 5,
            "dominant_target": dominant_target,
            "dominant_target_weight": round(float(target_weights.get(dominant_target, 0.0) or 0.0), 6),
            "entropy": round(manifold_entropy, 6),
            "layers": manifold_layers,
            "top_slots": manifold_top,
            "vector": manifold_vector,
            "basis_channel": focus_channel,
            "translation": manifold_translation,
        },
    }

# ── Worth formula (aurora_worth_evaluator physics, no full stack) ─────────────
_TRANSITIONS = (("X","T"),("T","N"),("N","B"),("B","A"))
_MAX_K = 150.0
_TRANS_AUTH = {(u,l): (SHIFT_COST[l]-SHIFT_COST[u])/_MAX_K for u,l in _TRANSITIONS}
_MAX_FSD    = sum(_TRANS_AUTH[(u,l)]*(SHIFT_COST[l]/_MAX_K) for u,l in _TRANSITIONS)
_AXIS_DEPTH = {ax: i/4.0 for i,ax in enumerate(AXES)}


class WorthTrajectory(Enum):
    RISING="rising"; FALLING="falling"; OSCILLATING="oscillating"
    STABLE="stable"; UNKNOWN="unknown"


class WorthHistory:
    def __init__(self, window: int = 8) -> None:
        self._scores: Deque[float] = deque(maxlen=window)

    def record(self, score: float) -> None:
        self._scores.append(score)

    @property
    def trajectory(self) -> WorthTrajectory:
        if len(self._scores) < 2:
            return WorthTrajectory.UNKNOWN
        s = list(self._scores)
        d = [s[i]-s[i-1] for i in range(1,len(s))]
        if all(x>0 for x in d): return WorthTrajectory.RISING
        if all(x<0 for x in d): return WorthTrajectory.FALLING
        sc = sum(1 for i in range(1,len(d)) if (d[i]>0)!=(d[i-1]>0))
        if sc >= max(1,len(d)//2): return WorthTrajectory.OSCILLATING
        return WorthTrajectory.STABLE

    @property
    def latest(self) -> float:
        return list(self._scores)[-1] if self._scores else 0.0


def _worth_score(
    expr_c: str, nc_target: str, nc_dim: str,
    depth_sc: float, conf: float,
) -> float:
    """W(x) = 1/(1 + Σᵢ wᵢ·|Δforced|), depth-weighted, confidence-modulated."""
    ed = _AXIS_DEPTH.get(expr_c, 0.5)
    nd = _AXIS_DEPTH.get(nc_target, 0.5)
    fsd = 0.0
    for (u,l) in _TRANSITIONS:
        auth = _TRANS_AUTH[(u,l)]
        ld   = _AXIS_DEPTH.get(l, 0.5)
        dist = abs(ed - ld)
        prox = max(0.0, 1.0 - abs(nd - ld))
        fsd += auth * dist * prox
    raw   = 1.0 / (1.0 + fsd / max(_MAX_FSD, 1e-9))
    score = raw * (0.7 + 0.3 * conf)
    score += 0.10 * depth_sc
    if expr_c == nc_target:
        score += 0.15   # polarity coherent bonus
    return min(1.0, score)


# ── Semantic matcher ──────────────────────────────────────────────────────────

@dataclass
class MatchResult:
    constraint:str; dimension:str; frame:str; stance:str
    dominant_role:Optional[str]; topic_words:List[str]
    nc_name:Optional[str]; confidence:float
    is_ambiguous:bool; is_experiential:bool
    is_clarification:bool; is_hypothetical:bool; negated:bool
    query_type:Optional[str]=None; semantic_override:Optional[str]=None

    @property
    def is_reliable(self) -> bool: return self.confidence >= 0.30


class SemanticMatcher:
    def __init__(self, directory=None) -> None:
        self._directory = directory
        self._parser = UtteranceParser() if _PARSER_AVAILABLE else None

    def match(self, expression: str) -> MatchResult:
        if not self._parser:
            return MatchResult("B","OPERATOR","unknown","neutral",None,[],
                               None,0.25,True,False,False,False,False,None,None)
        p = self._parser.parse(expression)
        frame   = p.get("frame","unknown")
        stance  = p.get("stance","neutral")
        signals = [s[0] for s in p.get("pragmatic_signals",[])]
        topics  = p.get("topic_words",[])
        query_type = str(p.get("query_type", "") or "").strip().lower() or None

        constraint = FRAME_TO_CONSTRAINT.get(frame,"N")

        dim = "OPERATOR"
        dominant_role = signals[0] if signals else None
        for role in signals:
            if role in ROLE_TO_DIMENSION:
                dim = ROLE_TO_DIMENSION[role]
                dominant_role = role
                break
        if dim == "OPERATOR":
            dim = STANCE_TO_DIMENSION.get(stance,"OPERATOR")

        if frame in HIGH_CONF_FRAMES:   conf = 0.80
        elif frame in MID_CONF_FRAMES:  conf = 0.55
        else:                           conf = 0.35

        semantic_override = None
        override_constraint, override_dim, semantic_override, override_conf = _semantic_override(expression, p)
        if override_constraint and override_dim:
            constraint = override_constraint
            dim = override_dim
            conf = max(conf, override_conf)

        nc_name = self._find_nc(constraint, dim, topics) if self._directory else None

        return MatchResult(
            constraint=constraint, dimension=dim, frame=frame, stance=stance,
            dominant_role=dominant_role, topic_words=topics, nc_name=nc_name,
            confidence=conf, is_ambiguous=(p.get("is_hypothetical",False) and
                                           p.get("is_clarification",False)),
            is_experiential=p.get("is_experiential",False),
            is_clarification=p.get("is_clarification",False),
            is_hypothetical=p.get("is_hypothetical",False),
            negated=p.get("negated",False),
            query_type=query_type,
            semantic_override=semantic_override,
        )

    def _find_nc(self, constraint:str, dim:str, topics:List[str]) -> Optional[str]:
        candidates = self._directory.entries_for_axis(constraint)
        if not candidates: return None
        def score(e) -> float:
            s = 3.0 if e.nc_dim == dim else 0.0
            nc_words = set(e.nc_name.lower().replace("_"," ").split())
            s += len(nc_words & {t.lower() for t in topics}) * 0.5
            s += 1.5 if str(getattr(e, "nc_law_c", "") or "").strip() == constraint else 0.0
            return s
        return max(candidates, key=score).nc_name


# ── ManifoldFieldMap ──────────────────────────────────────────────────────────

def region_type(w: float) -> str:
    return "dense" if w>=DENSE_THRESHOLD else "sparse" if w<=SPARSE_THRESHOLD else "mid"

class ManifoldFieldMap:
    AXES=("X","T","N","B","A"); DIM_NAMES=("POLARITY","MAGNITUDE","OPERATOR","COST","DIFFERENCE")
    def __init__(self, m: "NoncompManifold") -> None:
        self._nc_name=m.nc_name; self._nc_domain=m.nc_domain
        self._nc_law_c=m.nc_law_c; self._nc_dim=m.nc_dim; self._nc_target=m.nc_target
        self._idx:Dict[Tuple[str,str],int] = {
            (ax,dm): i*5+j for i,ax in enumerate(self.AXES) for j,dm in enumerate(self.DIM_NAMES)
        }
        self._grid:List[List[float]] = [[0.0]*25 for _ in range(25)]
        for slot in m.stream_slots():
            r=self._idx.get((slot.sub_law_c,slot.sub_law_d)); c=self._idx.get((slot.col_law_c,slot.col_law_d))
            if r is not None and c is not None: self._grid[r][c]=slot.accountability_weight
        all_v=[v for row in self._grid for v in row]
        self._mean=sum(all_v)/len(all_v); self._dense=sum(1 for v in all_v if v>=DENSE_THRESHOLD)

    def weight(self,slc:str,sld:str,clc:str,cld:str)->float:
        r=self._idx.get((slc,sld),-1); c=self._idx.get((clc,cld),-1)
        return self._grid[r][c] if r>=0 and c>=0 else 0.0

    def accountability_at(self,slc,sld,clc,cld): w=self.weight(slc,sld,clc,cld); return w,region_type(w)

    @property
    def nc_name(self)->str: return self._nc_name
    @property
    def nc_domain(self)->str: return self._nc_domain
    @property
    def dense_count(self)->int: return self._dense
    @property
    def mean_weight(self)->float: return self._mean
    def __repr__(self)->str: return f"ManifoldFieldMap({self._nc_name!r}, dense={self._dense}, mean={self._mean:.3f})"


# ── Understanding state ───────────────────────────────────────────────────────

@dataclass
class UnderstandingState:
    expression:str; constraint:str; dimension:str; frame:str
    nc_name:Optional[str]; nc_domain:Optional[str]
    worth_score:float; worth_trajectory:str; field_region:str
    is_understood:bool; polarity_coherent:bool
    match_confidence:float; band_pos:str; summary:str
    query_type:Optional[str]=None; semantic_override:Optional[str]=None
    noncomp_state:Dict[str, object]=field(default_factory=dict)

    def to_dict(self)->Dict:
        return {k:v for k,v in {
            "expression":self.expression[:200],"constraint":self.constraint,
            "dimension":self.dimension,"frame":self.frame,"nc_name":self.nc_name,
            "nc_domain":self.nc_domain,"worth_score":round(self.worth_score,4),
            "worth_trajectory":self.worth_trajectory,"field_region":self.field_region,
            "is_understood":self.is_understood,"polarity_coherent":self.polarity_coherent,
            "match_confidence":self.match_confidence,"band_pos":self.band_pos,
            "summary":self.summary,"query_type":self.query_type,
            "semantic_override":self.semantic_override,
            "noncomp_state": dict(self.noncomp_state or {}),
        }.items()}

    def __repr__(self)->str:
        flag="✓ UNDERSTOOD" if self.is_understood else "○ integrating"
        return (f"UnderstandingState({flag}, frame={self.frame}, "
                f"worth={self.worth_score:.3f}, traj={self.worth_trajectory})")


# ── Reconciliation v2 ─────────────────────────────────────────────────────────

def _polarity_coherent(match:MatchResult, route:Optional["RouteResult"]) -> bool:
    if match.negated or match.is_ambiguous: return False
    if match.constraint in ("B","A"):
        if route and route.admitted:
            return any(t.coord.target in ("B","A") for t in route.targets)
        return True
    return match.confidence >= 0.60

def _reconcile(
    w:float, traj:WorthTrajectory, region:str,
    coherent:bool, conf:float, route:Optional["RouteResult"],
) -> Tuple[bool, str]:
    traj_w = {
        WorthTrajectory.RISING:1.0, WorthTrajectory.STABLE:0.9,
        WorthTrajectory.UNKNOWN:0.7, WorthTrajectory.OSCILLATING:0.4,
        WorthTrajectory.FALLING:0.2,
    }.get(traj, 0.5)
    coh_mult = 1.15 if coherent else 0.85
    orig_b   = {"dense":0.20,"mid":0.05,"sparse":0.0}.get(region,0.0)
    score    = min(1.0, w*traj_w*coh_mult + orig_b)
    und      = score >= UNDERSTANDING_THRESHOLD

    if und:
        if traj==WorthTrajectory.RISING:
            s = (f"Expression integrating cleanly. Worth rising (score={w:.2f}), "
                 f"meaning finding its accountability cluster.")
        else:
            s = (f"Expression recognized. Worth={w:.2f} in {region} territory, "
                 f"trajectory={traj.value}. Aurora recognizes what she said.")
    elif traj==WorthTrajectory.FALLING:
        s = (f"Expression losing integration. Worth falling (score={w:.2f}). "
             f"Meaning drifting from accountability anchor.")
    elif traj==WorthTrajectory.OSCILLATING:
        s = (f"Expression in churn (worth≈{w:.2f}). Cannot stabilize — "
             f"constraint pressure inconsistent.")
    elif region=="sparse":
        s = (f"Sparse field territory (worth={w:.2f}). Not yet bound to "
             f"accountability structure. Said but not yet owned.")
    else:
        s = (f"Partially integrated (worth={w:.2f}, traj={traj.value}). "
             f"In {region} territory. More constraint passes needed.")

    return und, s


# ── Reflexive Interpreter ─────────────────────────────────────────────────────

class ReflexiveInterpreter:
    """
    Closes the loop: STATE → EXPRESSION → RE-ENTRY → RECONCILIATION → UNDERSTANDING
    v2: UtteranceParser-backed matching + Worth-formula reconciliation.
    """
    def __init__(self, directory=None, router=None,
                 band_pos:str=BandPosition.INSIDE,
                 sedimemory=None, state_dir:Optional[str]=None) -> None:
        self._directory = directory; self._router = router
        self._matcher   = SemanticMatcher(directory)
        self._band_pos  = band_pos
        self._history:  List[UnderstandingState] = []
        self._worth_histories: Dict[str, WorthHistory] = {}
        self._sedimemory = sedimemory

        # ── Deposition stratum (aurora_understanding_sediment) ──
        # Overlay: runtime accountability-weight deltas layered over the
        # read-only compiled manifold. Ledger: worth windows persisted so
        # trajectory survives sessions instead of resetting to UNKNOWN.
        self._overlay: Optional["UnderstandingSedimentOverlay"] = None
        self._worth_ledger: Optional["PersistentWorthLedger"] = None
        if _SEDIMENT_AVAILABLE:
            try:
                self._overlay = UnderstandingSedimentOverlay(state_dir=state_dir)
                self._worth_ledger = PersistentWorthLedger(state_dir=state_dir)
            except Exception:
                self._overlay = None; self._worth_ledger = None

    def _worth_history_for(self, key:str) -> WorthHistory:
        """WorthHistory for a key, rehydrated from the persisted ledger
        on first touch so trajectory carries across sessions."""
        hist = self._worth_histories.get(key)
        if hist is None:
            hist = WorthHistory()
            if self._worth_ledger is not None:
                try:
                    for s in self._worth_ledger.scores_for(key):
                        hist.record(s)
                except Exception: pass
            self._worth_histories[key] = hist
        return hist

    def update_band(self, band_pos:str) -> None:
        self._band_pos = band_pos

    def interpret(self, expression:str, min_evo:float=0.40, max_t:int=8) -> UnderstandingState:
        match  = self._matcher.match(expression)

        # Field map
        origin_weight=0.0; origin_region="sparse"; depth_sc=0.50
        if self._directory and match.nc_name:
            try:
                with self._directory.open(match.nc_name) as m:
                    fmap = ManifoldFieldMap(m)
                    origin_weight, origin_region = fmap.accountability_at(
                        match.constraint, match.dimension, match.constraint, "OPERATOR"
                    )
                    idx_e = self._directory.get_index_entry(match.nc_name)
                    if idx_e:
                        depth_sc = SHIFT_COST.get(idx_e.nc_law_c,1.0)/150.0
            except Exception: pass

        # ── Sediment overlay: bedrock + lived deposits ──
        # Prior understood expressions densified this neighborhood; the
        # adjusted weight can shift origin_region sparse → mid → dense,
        # which feeds _reconcile()'s origin bonus. This is the compounding
        # edge of the snowball.
        sediment_delta = 0.0
        _slot = None
        if self._overlay is not None:
            try:
                _slot = _sediment_slot_key(match.constraint, match.dimension)
                _fkey = match.nc_name or f"{match.constraint}:{match.dimension}"
                sediment_delta = self._overlay.delta(_fkey, _slot)
                if sediment_delta > 0.0:
                    origin_weight = self._overlay.adjusted_weight(
                        origin_weight, _fkey, _slot)
                    origin_region = region_type(origin_weight)
            except Exception:
                sediment_delta = 0.0

        # ── Recall coupling: memory lowers the energy cost of re-knowing ──
        # Resonant SediMemory fragments on the matched axis lift the
        # confidence term of the worth formula (0.7 + 0.3·conf). Polarity
        # coherence still judges the raw match.confidence — recall may
        # cheapen re-understanding, never counterfeit coherence.
        recall_boost = 0.0
        if _SEDIMENT_AVAILABLE and self._sedimemory is not None:
            try:
                recall_boost = recall_confidence_boost(
                    self._sedimemory, expression, match.constraint)
            except Exception:
                recall_boost = 0.0
        conf_effective = min(1.0, match.confidence + recall_boost)

        # NC target from nc_name (extract constraint from "..._of_Boundary")
        nc_target = match.constraint
        if match.nc_name:
            parts = match.nc_name.split("_of_")
            if len(parts) > 1:
                dom = parts[-1].lower()
                for ax,name in [("X","existence"),("T","temporal"),("N","energetic"),
                                 ("B","boundary"),("A","agency")]:
                    if name in dom: nc_target = ax; break

        # Worth score (confidence term carries the recall boost)
        ws = _worth_score(match.constraint, nc_target, match.dimension, depth_sc, conf_effective)

        # Worth history — rehydrated from the persisted ledger, so
        # trajectory survives sessions instead of restarting UNKNOWN.
        key = match.nc_name or f"{match.constraint}:{match.dimension}"
        hist = self._worth_history_for(key)
        hist.record(ws)
        if self._worth_ledger is not None:
            try: self._worth_ledger.record(key, ws)
            except Exception: pass
        traj = hist.trajectory

        # Route
        route_result = None
        if self._router and match.is_reliable:
            try:
                coord  = SlotCoord(match.constraint,match.constraint,match.dimension,
                                   match.constraint,match.dimension)
                signal = RouteSignal(source=coord,strength=ws,intent=expression[:80],
                                     band_pos=self._band_pos,min_evo_target=min_evo,max_targets=max_t)
                route_result = self._router.route_signal(signal)
            except Exception: pass

        coherent     = _polarity_coherent(match, route_result)
        is_und, summ = _reconcile(ws, traj, origin_region, coherent, match.confidence, route_result)

        # ── Deposition: understanding writes back into the field ──
        # Every understood expression lays sediment at the slot it landed
        # in (capped, decaying — see aurora_understanding_sediment).
        # The next nearby expression reads a denser field.
        if is_und and self._overlay is not None and _slot is not None:
            try:
                sediment_delta = self._overlay.deposit(
                    match.nc_name or f"{match.constraint}:{match.dimension}",
                    _slot, ws, threshold=UNDERSTANDING_THRESHOLD)
                self._overlay.save()
            except Exception: pass
        if self._worth_ledger is not None:
            try: self._worth_ledger.save()
            except Exception: pass

        noncomp_state = _project_noncomp_state(
            match,
            worth_score=ws,
            depth_score=depth_sc,
            origin_weight=origin_weight,
            origin_region=origin_region,
            route=route_result,
            expression=expression,
        )

        # ── FGAE Criterion 8 — Stamp FGAE input projection into noncomp_state ──
        # The FGAE engine runs process_input() upstream in _run_live_response_turn.
        # Here we pull that projection and attach its slot activations to
        # noncomp_state so the full constraint pattern is visible to downstream
        # processing (DCE, understanding contract, subsurface projection).
        # This completes the I-3 projection assembly step inside the interpreter.
        state = UnderstandingState(
            expression=expression, constraint=match.constraint, dimension=match.dimension,
            frame=match.frame, nc_name=match.nc_name, nc_domain=None,
            worth_score=round(ws,4), worth_trajectory=traj.value,
            field_region=origin_region, is_understood=is_und,
            polarity_coherent=coherent, match_confidence=match.confidence,
            band_pos=self._band_pos, summary=summ, query_type=match.query_type,
            semantic_override=match.semantic_override,
            noncomp_state=noncomp_state,
        )

        # Surface the deposition physics of this pass so DCE evidence and
        # the turn chain can see the snowball working.
        try:
            state.noncomp_state["sediment_delta"] = round(float(sediment_delta), 4)
            state.noncomp_state["recall_boost"]   = round(float(recall_boost), 4)
        except Exception: pass

        self._history.append(state)
        return state

    def interpret_batch(self, expressions:List[str]) -> List[UnderstandingState]:
        return [self.interpret(e) for e in expressions]

    @property
    def history(self) -> List[UnderstandingState]:
        return list(self._history)

    def understanding_rate(self) -> float:
        if not self._history: return 0.0
        return round(sum(1 for s in self._history if s.is_understood)/len(self._history), 4)

    def unintegrated(self) -> List[UnderstandingState]:
        return [s for s in self._history if not s.is_understood]

    def export_history(self, path:str) -> None:
        with open(path,"w",encoding="utf-8") as f:
            json.dump([s.to_dict() for s in self._history], f, indent=2)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    DIRECTORY_PATH = sys.argv[1] if len(sys.argv) > 1 else "aurora_manifold_directory"
    SEMANTICS_PATH = sys.argv[2] if len(sys.argv) > 2 else "aurora_full_noncomp_rich_semantics.json"

    print("="*68)
    print("AURORA REFLEXIVE INTERPRETER  v2")
    print("STATE → EXPRESSION → RE-ENTRY → RECONCILIATION → UNDERSTANDING")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("="*68)
    print(f"\nUtteranceParser: {_PARSER_AVAILABLE}")
    print(f"Directory:       {_DIRECTORY_AVAILABLE}")
    print(f"Router:          {_ROUTER_AVAILABLE}")

    print("\n--- Semantic Matcher (UtteranceParser-backed) ---")
    matcher = SemanticMatcher()
    for expr in [
        "something feels off at the boundary, I can't tell if it fits",
        "I'm not sure this holds as real — is it admissible?",
        "what does it cost me to commit to this?",
        "I understand what I just said — it belongs here",
        "the sequence doesn't continue the way I expected",
        "yeah but that's not what I meant at all",
        "like I said, the meaning has to hold together structurally",
    ]:
        m = matcher.match(expr)
        print(f"\n  '{expr[:56]}'")
        print(f"    [{m.constraint}:{m.dimension}]  frame={m.frame:14s}"
              f"  stance={m.stance:12s}  conf={m.confidence:.2f}"
              f"  {'[ambiguous]' if m.is_ambiguous else ''}"
              f"  {'[negated]' if m.negated else ''}")

    if _DIRECTORY_AVAILABLE:
        print("\n--- Full Re-Entry Loop  v2 ---")
        try:
            directory = ManifoldDirectory(DIRECTORY_PATH)
            router = None
            if _ROUTER_AVAILABLE:
                try:
                    idx    = build_route_index(SEMANTICS_PATH)
                    router = ManifoldRouter(idx, seed=42)
                except Exception: pass
            interp = ReflexiveInterpreter(directory=directory, router=router)

            for expr in [
                "I recognize what this means — it holds together as a distinct structure",
                "something feels off, I said something but I don't know if it fits",
                "I need to commit to what I just said and own it",
                "the boundary between self and other isn't clear here",
                "I understand — what I expressed is consistent with what I know",
                "yeah but that's not what I meant at all",
                "like I said, the meaning has to hold together structurally",
                "I'm not sure this holds as real yet",
            ]:
                s = interp.interpret(expr)
                flag = "✓ UNDERSTOOD" if s.is_understood else "○ integrating"
                print(f"\n  '{expr[:60]}'")
                print(f"    {flag}  [{s.constraint}:{s.dimension}]"
                      f"  frame={s.frame:14s}  worth={s.worth_score:.3f}"
                      f"  traj={s.worth_trajectory}  coherent={s.polarity_coherent}")
                print(f"    {s.summary[:112]}")

            rate = interp.understanding_rate()
            n    = len(interp.history)
            und  = sum(1 for s in interp.history if s.is_understood)
            print(f"\n  Understanding rate: {rate:.0%}  ({und}/{n})")
        except FileNotFoundError:
            print(f"  Directory not found: {DIRECTORY_PATH}")
    print("\nDone.")
