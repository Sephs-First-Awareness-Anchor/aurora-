"""
aurora_warp_protocol.py
========================
Universal structural adaptation mechanism for Aurora's cognitive stack.

DOCTRINE:
    Every system level in Aurora holds a set of components, each oriented
    toward a region of the full coverage space. The coverage space is 15D:

        10D I-STATE SPACE
        ─────────────────
        X: I_IS  (existence present)   / I_ISNT   (existence denied — pressure)
        T: I_CAN (continuity possible) / I_CANNOT  (continuity blocked — pressure)
        N: I_DO  (energy expressed)    / I_DONOT   (energy withheld — pressure)
        B: I_SAW (boundary found)      / I_SOUGHT  (boundary unfound — pressure)
        A: I_DID (agency enacted)      / I_DIDNT   (agency failed — pressure)

        Coverage in I-state space is measured by cosine similarity. A stream
        covering I_CAN does NOT cover I_CANNOT. Negative I-states are active
        orthogonal forces — pressure — not the absence of the positive.

        5D RECURSION SPACE
        ──────────────────
        REC_SURFACE   — existence/reflex layer (IVM SURFACE=0, fastest-changing)
        REC_SHALLOW   — temporal/fast layer    (IVM SHALLOW=1)
        REC_MODERATE  — energy/crossover layer (IVM MODERATE=2)
        REC_DEEP      — boundary/alignment     (IVM DEEP=3)
        REC_CORE      — agency/identity        (IVM CORE=4, most stable)

        The recursion dimension captures HOW DEEP in the processing stack a
        phenomenon lives. A surface-level reflex and a core-identity anchor can
        share identical I-state profiles but reside at opposite recursion depths.
        They are different phenomena. Only the 15D representation tells them apart.

    The system's question: "Can I find a phenomenon that cannot be represented
    through any combination of constraint magnitude, polarity, recursion, phase,
    or stream orientation?" — the 15D space operationalises this.

    When incoming data carries a profile that no existing component resonates
    with, WARP derives a new component from what already exists — not from
    nothing, but from the closest known configurations, combined in a proportion
    that wasn't needed until now. The genealogy (ConstraintLink fossil record)
    is queried first: if proven prior structures cover the gap, they bias the
    derivation toward known-effective territory rather than fresh synthesis.

    The possibility of a 6th constraint (an 11th/12th I-state pair) exists
    but requires sustained anomaly evidence before any structural action.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import hashlib
import math
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import aurora_manifold_lookup
from aurora_constraint_signature_resolver import nc_name as _resolve_nc_name

# ─── I-State Space ────────────────────────────────────────────────────────────

# The 10 I-state beings — the actual operational units of the coverage space.
# Positive I-states = affirmative constraint expression.
# Negative I-states = constraint pressure (denial, blockage, withdrawal).
_ALL_ISTATES: Tuple[str, ...] = (
    "I_IS",    "I_ISNT",
    "I_CAN",   "I_CANNOT",
    "I_DO",    "I_DONOT",
    "I_SAW",   "I_SOUGHT",
    "I_DID",   "I_DIDNT",
)

# Which axis each I-state belongs to
_ISTATE_TO_AXIS: Dict[str, str] = {
    "I_IS":    "X", "I_ISNT":   "X",
    "I_CAN":   "T", "I_CANNOT": "T",
    "I_DO":    "N", "I_DONOT":  "N",
    "I_SAW":   "B", "I_SOUGHT": "B",
    "I_DID":   "A", "I_DIDNT":  "A",
}

# +1 = positive I-state, -1 = negative I-state (pressure)
_ISTATE_POLARITY: Dict[str, int] = {
    "I_IS":    +1, "I_ISNT":   -1,
    "I_CAN":   +1, "I_CANNOT": -1,
    "I_DO":    +1, "I_DONOT":  -1,
    "I_SAW":   +1, "I_SOUGHT": -1,
    "I_DID":   +1, "I_DIDNT":  -1,
}

# Human-readable names for gap naming and synthesis
_ISTATE_NAMES: Dict[str, str] = {
    "I_IS":    "existence",
    "I_ISNT":  "absence",
    "I_CAN":   "continuity",
    "I_CANNOT":"blockage",
    "I_DO":    "energy",
    "I_DONOT": "withdrawal",
    "I_SAW":   "boundary",
    "I_SOUGHT":"seeking",
    "I_DID":   "agency",
    "I_DIDNT": "failure",
}

# Backward-compatible 5-axis tuple (used internally for some conversions)
_ALL_AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")

# ─── Recursion Depth Dimensions ───────────────────────────────────────────────

# The 5 recursion depth dimensions — orthogonal to I-state polarity.
# Maps directly to IVM RecursionLevel enum (SURFACE=0 through CORE=4).
# A component's recursion profile describes HOW DEEP in the processing stack
# it operates. Same I-states at different depths = different phenomena.
_RECURSION_DIMS: Tuple[str, ...] = (
    "REC_SURFACE",   # SURFACE=0 — existence/reflex layer, fastest to change
    "REC_SHALLOW",   # SHALLOW=1 — temporal/fast layer
    "REC_MODERATE",  # MODERATE=2 — energy/crossover layer
    "REC_DEEP",      # DEEP=3 — boundary/alignment layer, slow to shift
    "REC_CORE",      # CORE=4 — agency/identity layer, the ship's heading
)

# Full 15D coverage space: 10 I-states + 5 recursion depths
# Aurora's question: "Can I find a phenomenon that cannot be represented
# through any combination of constraint magnitude, polarity, recursion,
# phase, or stream orientation?" — this is the space that operationalises it.
_ALL_DIMS: Tuple[str, ...] = _ALL_ISTATES + _RECURSION_DIMS


def axes_to_istates(
    axis_weights: Dict[str, float],
    ivm_polarity: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    Convert 5D axis weights + IVM polarity to 10D I-state vector.

    axis_weights: {X, T, N, B, A} magnitudes [0, 1]
    ivm_polarity: {X, T, N, B, A} signed polarity [-1, +1] from IVM lattice
                  global polarity (cos(phase)). If None, assumes neutral (0.0).

    For each axis:
        positive_weight = magnitude × (1 + polarity) / 2
        negative_weight = magnitude × (1 - polarity) / 2

    When polarity is 0 (neutral), positive and negative share the magnitude
    equally. When polarity is +1 (fully positive), all weight goes to the
    positive I-state. When polarity is -1 (fully negative/pressure), all
    weight goes to the negative I-state.
    """
    pol = ivm_polarity or {}
    _pairs = [
        ("I_IS",  "I_ISNT",   "X"),
        ("I_CAN", "I_CANNOT", "T"),
        ("I_DO",  "I_DONOT",  "N"),
        ("I_SAW", "I_SOUGHT", "B"),
        ("I_DID", "I_DIDNT",  "A"),
    ]
    result: Dict[str, float] = {}
    for pos, neg, ax in _pairs:
        magnitude = float(axis_weights.get(ax, 0.5))
        polarity  = float(pol.get(ax, 0.0))          # [-1, +1]
        pos_w = magnitude * (1.0 + polarity) / 2.0
        neg_w = magnitude * (1.0 - polarity) / 2.0
        result[pos] = round(min(1.0, max(0.0, pos_w)), 3)
        result[neg] = round(min(1.0, max(0.0, neg_w)), 3)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# REPRESENTATIONAL DISCOVERY (EDIT — the paradigm layer)
# ═══════════════════════════════════════════════════════════════════════════
# Representation = FUNCTION, not form. Something represents a constraint if
# it carries that constraint's information through one of the five character
# lenses — which the architecture already defines:
#
#   POLARITY    → presence/absence, being vs non-being        (X-criterial)
#   MAGNITUDE   → degree, intensity, how-much                  (all axes)
#   OPERATOR    → transformation, action capacity              (N-criterial)
#   COST        → effort, expenditure, work                    (N/T-criterial)
#   DIFFERENCE  → distinguishability, inside/outside, deviation (B-criterial)
#
# So the root-level criteria are not a new definition set — they are the
# 25-channel basis read functionally. A candidate representation of axis C
# is any encoding whose output carries C-channel information; its DEGREE is
# set by the pressure system (potency), per the doctrine: pressure
# determines the level of constraint potency in any combination.

REPRESENTATION_CRITERIA: Dict[str, str] = {
    "X": "establishes presence, persistence, or distinguishability from non-being",
    "T": "encodes change, sequence, duration, or continuity across states",
    "N": "reflects capacity for action, transformation, or state change",
    "B": "distinguishes inside from outside; defines separation or contact",
    "A": "encodes directed selection, ownership, or attribution of action",
}


def representation_degree(
    channel_weights: Dict[str, float],
    axis_pressures: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    To what DEGREE does an encoded pattern represent each constraint?

    Degree per axis = that axis's share of channel information, weighted by
    live pressure potency (axis_pressures in [0,1], e.g. from the identity
    field). High pressure on an axis amplifies how strongly patterns
    carrying that axis's channels count as representing it — the pressure
    system is the arbiter of constraint potency.
    """
    pressures = axis_pressures or {}
    raw: Dict[str, float] = {}
    total = 0.0
    for ch, w in (channel_weights or {}).items():
        ax = str(ch).split(":")[0]
        if ax in ("X", "T", "N", "B", "A"):
            v = abs(float(w or 0.0))
            raw[ax] = raw.get(ax, 0.0) + v
            total += v
    if total <= 0:
        return {ax: 0.0 for ax in ("X", "T", "N", "B", "A")}
    out: Dict[str, float] = {}
    for ax in ("X", "T", "N", "B", "A"):
        share = raw.get(ax, 0.0) / total
        potency = 0.5 + float(pressures.get(ax, 0.5) or 0.5)   # [0.5, 1.5]
        out[ax] = round(min(1.0, share * potency), 4)
    return out


def istates_to_axes(istate_weights: Dict[str, float]) -> Dict[str, float]:
    """
    Collapse 10D I-state vector back to 5D axis magnitudes.
    magnitude[ax] = max(positive_istate, negative_istate) for that axis.
    Used when a legacy 5D interface is needed.
    """
    result: Dict[str, float] = {}
    for pos, neg, ax in [
        ("I_IS", "I_ISNT", "X"),
        ("I_CAN", "I_CANNOT", "T"),
        ("I_DO", "I_DONOT", "N"),
        ("I_SAW", "I_SOUGHT", "B"),
        ("I_DID", "I_DIDNT", "A"),
    ]:
        result[ax] = round(max(
            istate_weights.get(pos, 0.0),
            istate_weights.get(neg, 0.0),
        ), 3)
    return result

# Cosine similarity threshold — below this means no component covers the data
COVERAGE_THRESHOLD: float = 0.82

# Below this, even the best single component is very far away — potential 6th axis
ANOMALY_THRESHOLD: float = 0.35

# A trial component must reach this EMA score to earn permanent status
PROMOTION_SCORE: float = 0.60

# How many advance ticks before a trial component is evaluated for promotion
TRIAL_TICKS: int = 10

# How many consecutive coverage gaps must persist before WARP fires
GAP_PERSISTENCE_REQUIRED: int = 3

# Gap-weighting vs parent-blending in profile derivation
_GAP_WEIGHT: float = 0.65
_PARENT_WEIGHT: float = 0.35

# Minimum axis weight to be considered "dominant" in name synthesis
_DOMINANCE_FLOOR: float = 0.40

# Minimum anomaly occurrences before it becomes a formal candidate
ANOMALY_CANDIDATE_THRESHOLD: int = 12


# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class CoverageGap:
    """
    A detected gap in a system level's coverage of an incoming axis profile.

    best_coverage is the cosine similarity of the closest existing component.
    closest_ids are the top-3 existing components ranked by proximity.
    is_sixth_axis_candidate is True when even the best coverage is below
    ANOMALY_THRESHOLD — the data may not decompose into existing 5 axes.
    """
    axis_profile:           Dict[str, float]
    best_coverage:          float
    closest_ids:            List[str]
    closest_profiles:       List[Dict[str, float]]
    is_sixth_axis_candidate: bool = False
    source:                 str = ""
    gap_tick:               int = 0


@dataclass
class WarpComponent:
    """
    A newly derived structural component born from a coverage gap.

    axis_profile is the 5D constraint coordinate this component covers.
    parent_ids are the existing components it was derived from.
    parameters holds level-specific data (e.g. stream update function,
    crest compression target, channel basin targets).
    trial_score_ema tracks its contribution quality during trial.
    """
    component_id:    str
    level:           str                    # e.g. "braid_stream", "crest", "lsa_path"
    axis_profile:    Dict[str, float]
    parent_ids:      List[str]
    name:            Optional[str]
    parameters:      Dict[str, Any]         = field(default_factory=dict)
    trial_tick:      int                    = 0
    trial_score_ema: float                  = 0.0
    promoted:        bool                   = False
    dissolved:       bool                   = False
    created_at:      float                  = field(default_factory=time.time)
    sixth_axis_signal: float                = 0.0  # residual after best 5D projection
    # MTSL Phase 7 (2026-07-13): when a coverage gap was surfaced from an
    # MTSL topology observation (a real, persistent organization pattern
    # existing components don't cover), the resulting trial component's
    # provenance is tagged here -- WarpComponent.promoted still only ever
    # flips via evaluate_warp_trials()'s own TRIAL_TICKS/PROMOTION_SCORE
    # gate below, exactly as for every other component. This field never
    # grants any component a shortcut past that gate; it's provenance, not
    # authority ("never promote by decree" per the directive). Optional,
    # default None -- nothing currently calls generate() with one (see
    # WarpGenerator.generate()'s own docstring for the deferred live-
    # wiring note).
    topology_gap_ref: Optional[str]         = None


@dataclass
class ConstraintAnomalyRecord:
    """
    A logged signal that may indicate a dimension beyond the 5 known constraints.

    The system does not act on this immediately. It accumulates evidence.
    When occurrence_count crosses ANOMALY_CANDIDATE_THRESHOLD, the record
    is promoted to candidate status and surfaced for deeper analysis.
    """
    anomaly_id:          str
    axis_residual:       float              # 1.0 - best_coverage at detection
    triggering_profile:  Dict[str, float]
    occurrence_count:    int                = 1
    first_seen:          float              = field(default_factory=time.time)
    last_seen:           float              = field(default_factory=time.time)
    promoted_to_candidate: bool            = False


# ─── Coverage Checker ─────────────────────────────────────────────────────────

class AxisCoverageChecker:
    """
    Checks whether a set of profiled components covers an incoming profile.

    Coverage is cosine similarity in 15D space (10 I-states + 5 recursion depths).
    If the best cosine across all components is below COVERAGE_THRESHOLD, a
    CoverageGap is returned.

    Profiles should be dicts keyed by I-state strings (I_IS, I_ISNT, etc.) plus
    optional recursion depth strings (REC_SURFACE, REC_CORE, etc.).
    Legacy 5D axis profiles are accepted and auto-expanded assuming neutral polarity.
    Missing dimensions default to 0.0 in cosine computation.
    """

    def __init__(self, components: Dict[str, Dict[str, float]]) -> None:
        # {component_id: profile}  — normalised to full dims on entry
        self._components: Dict[str, Dict[str, float]] = {
            cid: self._ensure_full_dims(profile)
            for cid, profile in components.items()
        }

    def update(self, component_id: str, profile: Dict[str, float]) -> None:
        self._components[component_id] = self._ensure_full_dims(profile)

    def remove(self, component_id: str) -> None:
        self._components.pop(component_id, None)

    @staticmethod
    def _ensure_full_dims(profile: Dict[str, float]) -> Dict[str, float]:
        """
        Normalise to 15D: 10 I-states + 5 recursion dims.
        - If profile has I-state keys → keep them, zero-pad missing dims.
        - If profile has only 5-axis keys → expand to 10D I-states (neutral
          polarity) then zero-pad recursion dims.
        Missing dims default to 0.0 — they do not participate in cosine.
        """
        if any(k in _ALL_ISTATES for k in profile):
            result = dict(profile)
            for dim in _ALL_DIMS:
                if dim not in result:
                    result[dim] = 0.0
            return result
        # Legacy 5D axis dict — expand with neutral polarity, no recursion
        base = axes_to_istates(profile, ivm_polarity=None)
        for r in _RECURSION_DIMS:
            base[r] = 0.0
        return base

    @staticmethod
    def _ensure_10d(profile: Dict[str, float]) -> Dict[str, float]:
        """Backward-compatible shim — expands to 10D I-state only (no recursion)."""
        if any(k in _ALL_ISTATES for k in profile):
            return dict(profile)
        return axes_to_istates(profile, ivm_polarity=None)

    @staticmethod
    def cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
        """
        Cosine similarity in 15D space (10 I-states + 5 recursion levels).
        Missing dimensions default to 0.0, so profiles that don't specify
        recursion dims are still comparable to those that do.
        """
        dims = _ALL_DIMS
        dot   = sum(a.get(d, 0.0) * b.get(d, 0.0) for d in dims)
        mag_a = math.sqrt(sum(a.get(d, 0.0) ** 2 for d in dims))
        mag_b = math.sqrt(sum(b.get(d, 0.0) ** 2 for d in dims))
        if mag_a < 1e-9 or mag_b < 1e-9:
            return 0.0
        return dot / (mag_a * mag_b)

    def check(
        self,
        data_profile: Dict[str, float],
        source: str = "",
        tick: int = 0,
    ) -> Optional[CoverageGap]:
        """
        Returns CoverageGap if no existing component resonates with data_profile.
        Returns None if coverage is sufficient (best cosine >= COVERAGE_THRESHOLD).

        data_profile can be 10D (I-state keys), 15D (I-state + recursion), or
        legacy 5D axis keys. All are normalised to 15D before comparison.
        """
        if not self._components or not data_profile:
            return None

        data_15d = self._ensure_full_dims(data_profile)

        scores: Dict[str, float] = {
            cid: self.cosine(profile, data_15d)
            for cid, profile in self._components.items()
        }

        ranked = sorted(scores, key=lambda k: scores[k], reverse=True)
        best_id = ranked[0]
        best_score = scores[best_id]

        if best_score >= COVERAGE_THRESHOLD:
            return None

        closest_ids = ranked[:3]
        closest_profiles = [self._components[cid] for cid in closest_ids]

        return CoverageGap(
            axis_profile=data_15d,          # stored as full 15D
            best_coverage=round(best_score, 4),
            closest_ids=closest_ids,
            closest_profiles=closest_profiles,
            is_sixth_axis_candidate=(best_score < ANOMALY_THRESHOLD),
            source=source,
            gap_tick=tick,
        )


# ─── Warp Generator ───────────────────────────────────────────────────────────

class WarpGenerator:
    """
    Derives new structural components from coverage gaps.

    Generation follows the genealogy doctrine: every new component is a
    derivative of what already exists. Before fresh derivation, the genealogy
    (ConstraintLink fossil record) is queried — proven prior structures bias the
    new component toward known-effective territory.

    The gap's 15D axis profile (10D I-state + 5D recursion) is the attractor.
    Closest parents and any genealogy matches contribute their profiles as context.

    6th-axis anomalies are logged and accumulated but never hastily acted on.
    """

    def __init__(self) -> None:
        self._anomaly_log: Dict[str, ConstraintAnomalyRecord] = {}

    def generate(
        self,
        gap: CoverageGap,
        level: str,
        level_params_fn: Optional[Callable[[CoverageGap, List[str]], Dict[str, Any]]] = None,
        genealogy: Any = None,
        topology_gap_ref: Optional[str] = None,
    ) -> Optional[WarpComponent]:
        """
        Generate a new component from the coverage gap.

        genealogy: optional ConstraintGenealogyLogger — if provided, its link
        fossil record is searched first to bias the derived profile toward
        proven constraint pairings before purely fresh synthesis.

        topology_gap_ref (MTSL Phase 7): optional provenance tag when this
        gap was surfaced from an MTSL topology observation rather than
        this level's own axis-coverage check. Purely a label on the
        resulting WarpComponent (see its field comment) -- does not
        change generation, trial scoring, or promotion in any way. Not
        called with one anywhere yet: wiring a live caller that surfaces
        topology gaps FROM the coordinator's snapshot into check_and_extend()
        is deferred, same posture as this session's other Phase 4-6
        live-wiring deferrals.

        Returns None if the gap is a 6th-axis anomaly — it is logged but
        no structural piece is created until sufficient evidence accumulates.
        """
        if gap.is_sixth_axis_candidate:
            self._record_anomaly(gap)
            return None

        genealogy_profiles = self._search_genealogy(gap, genealogy)
        new_profile = self._derive_profile(gap, extra_profiles=genealogy_profiles)
        name = self._synthesize_name(new_profile)
        comp_id = self._make_id(level, new_profile)
        params = level_params_fn(gap, gap.closest_ids) if level_params_fn else {}

        return WarpComponent(
            component_id=comp_id,
            level=level,
            axis_profile=new_profile,
            parent_ids=list(gap.closest_ids[:2]),
            name=name,
            parameters=params,
            sixth_axis_signal=round(1.0 - gap.best_coverage, 4),
            topology_gap_ref=topology_gap_ref,
        )

    # ── private ──────────────────────────────────────────────────────────────

    # Tunable: how much a manifold-sourced formula_coefficient can move a raw
    # cosine similarity. 0.7 floor keeps the genealogy match itself dominant;
    # 0.3 span lets a noncomp's own accountability weight nudge it +/-30%.
    _MANIFOLD_COEFFICIENT_WEIGHT = 0.3
    _MANIFOLD_COEFFICIENT_FLOOR = 1.0 - _MANIFOLD_COEFFICIENT_WEIGHT

    _DOMINANT_CONSTRAINT_TAG_PREFIX = "dominant_constraint:"
    _DOMINANT_DIMENSION_TAG_PREFIX = "dominant_dimension:"

    def _resolve_link_nc_name(self, link: Any) -> Optional[str]:
        """
        Best-effort resolve this ConstraintLink to a manifold nc_name.

        ConstraintLink itself has no dedicated (law, dim, target) field —
        the closest it comes is: `dominant_relief_axis` (a real dataclass
        field — the axis that received the most relief, i.e. the Target C)
        plus two free-form strings inside `tags` — "dominant_constraint:<axis>"
        (the Law L) and "dominant_dimension:<DIM>" (the Dimension D) —
        emitted by constraint_genealogy.py's promotion path when
        aurora_closure_basis's physics-grounded lineage grading succeeds.

        Those tags are informal and conditional: when closure-basis grading
        falls back to its string-frequency heuristic (no aurora_closure_basis,
        or derive_lineage() raised), the payload never sets those keys, so
        the tag ends up empty/placeholder. Rather than guess in that case,
        return None per-link so the caller falls back to the unweighted
        similarity exactly as before — never assume a triple is resolvable
        just because a tag string happens to be present.
        """
        tags = getattr(link, "tags", None) or []
        law: Optional[str] = None
        dim: Optional[str] = None
        for tag in tags:
            if law is None and tag.startswith(self._DOMINANT_CONSTRAINT_TAG_PREFIX):
                law = tag[len(self._DOMINANT_CONSTRAINT_TAG_PREFIX):].strip().upper()
            elif dim is None and tag.startswith(self._DOMINANT_DIMENSION_TAG_PREFIX):
                dim = tag[len(self._DOMINANT_DIMENSION_TAG_PREFIX):].strip().upper()

        target = getattr(link, "dominant_relief_axis", None)
        if not law or not dim or not target or law not in _ALL_AXES or target not in _ALL_AXES:
            return None
        try:
            return _resolve_nc_name(law, dim, target)
        except KeyError:
            return None

    def _search_genealogy(
        self,
        gap: CoverageGap,
        genealogy: Any,
    ) -> List[Dict[str, float]]:
        """
        Query ConstraintGenealogyLogger.links for I-state profiles that
        resonate with the gap. Each ConstraintLink has mean_relief (5D axis)
        and depth (DAG depth) — converted to 15D for cosine comparison.

        When a link resolves to a known manifold noncomp (see
        _resolve_link_nc_name), its formula_coefficient secondarily weights
        the match — proven links whose own noncomp carries a heavier
        accountability weight bias the derivation a little more strongly.
        Unresolved links (the common case when manifold data or the
        closure-basis tags aren't available) use the raw cosine unchanged.

        Returns up to 3 I-state profiles from top-matching links (min 0.35
        adjusted-similarity) to bias the derived component toward proven
        territory.
        """
        if genealogy is None or not hasattr(genealogy, "links"):
            return []
        links = genealogy.links
        if not links:
            return []

        results: List[Tuple[float, Dict[str, float]]] = []
        for link in links.values():
            relief = getattr(link, "mean_relief", None)
            if not relief or not isinstance(relief, dict):
                continue
            # mean_relief is 5D axis — convert to I-state space.
            # Relief = successful resolution → lean positive (high pos_w)
            # We pass neutral polarity; axes_to_istates() splits equally,
            # which is correct because we don't know the polarity of the relief.
            link_istate = axes_to_istates(
                {ax: float(relief.get(ax, 0.0)) for ax in _ALL_AXES},
                ivm_polarity=None,
            )
            # Map link depth to recursion dim
            depth = int(getattr(link, "depth", 1))
            rec: Dict[str, float] = {r: 0.0 for r in _RECURSION_DIMS}
            if depth <= 1:
                rec["REC_SHALLOW"] = 0.55
                rec["REC_SURFACE"] = 0.25
            elif depth == 2:
                rec["REC_MODERATE"] = 0.60
                rec["REC_SHALLOW"] = 0.25
            else:
                rec["REC_DEEP"] = 0.60
                rec["REC_MODERATE"] = 0.25
                if depth >= 4:
                    rec["REC_CORE"] = 0.40
            link_istate.update(rec)

            sim = AxisCoverageChecker.cosine(link_istate, gap.axis_profile)

            adjusted_sim = sim
            resolved_name = self._resolve_link_nc_name(link)
            if resolved_name is not None:
                noncomp = aurora_manifold_lookup.load_noncomp(resolved_name)
                if noncomp is not None:
                    coeff = float(noncomp.get("formula_coefficient", 0.0) or 0.0)
                    adjusted_sim = sim * (self._MANIFOLD_COEFFICIENT_FLOOR
                                           + self._MANIFOLD_COEFFICIENT_WEIGHT * coeff)

            results.append((adjusted_sim, link_istate))

        results.sort(key=lambda x: x[0], reverse=True)
        return [prof for sim, prof in results[:3] if sim > 0.35]

    def _derive_profile(
        self,
        gap: CoverageGap,
        extra_profiles: Optional[List[Dict[str, float]]] = None,
    ) -> Dict[str, float]:
        """
        Blend gap profile with closest parent profiles in 15D space.
        Gap contributes _GAP_WEIGHT; parents share _PARENT_WEIGHT weighted
        by their cosine proximity to the gap.

        extra_profiles (from genealogy search) are weighted alongside structural
        parents — genealogy knowledge enriches the derived profile without
        overriding the gap's pull.
        """
        result = {dim: 0.0 for dim in _ALL_DIMS}

        # Gap contribution — already 15D from AxisCoverageChecker.check()
        for dim in _ALL_DIMS:
            result[dim] += gap.axis_profile.get(dim, 0.0) * _GAP_WEIGHT

        # Parent contribution: structural closest + genealogy matches
        all_parents = list(gap.closest_profiles)
        if extra_profiles:
            all_parents = all_parents + extra_profiles

        if all_parents:
            weights = [
                max(1e-6, AxisCoverageChecker.cosine(p, gap.axis_profile))
                for p in all_parents
            ]
            total_w = sum(weights)
            for profile, w in zip(all_parents, weights):
                norm_w = (w / total_w) * _PARENT_WEIGHT
                for dim in _ALL_DIMS:
                    result[dim] += profile.get(dim, 0.0) * norm_w

        return {dim: round(min(1.0, max(0.0, v)), 3) for dim, v in result.items()}

    def _synthesize_name(self, profile: Dict[str, float]) -> str:
        """
        Name the component from its dominant I-states and recursion depth.
        Negative I-states get equal naming rights — a component oriented toward
        I_CANNOT pressure is named accordingly, not hidden.
        Recursion depth enriches the name when a single depth strongly dominates.
        """
        dominant_istates = sorted(
            [(ist, profile[ist]) for ist in _ALL_ISTATES
             if profile.get(ist, 0.0) >= _DOMINANCE_FLOOR],
            key=lambda t: t[1],
            reverse=True,
        )
        parts = [_ISTATE_NAMES[ist] for ist, _ in dominant_istates[:2]]

        # Append recursion depth suffix if a single depth strongly dominates
        rec_vals = [(r, profile.get(r, 0.0)) for r in _RECURSION_DIMS]
        rec_vals.sort(key=lambda x: x[1], reverse=True)
        if rec_vals[0][1] >= 0.55:
            depth_suffix = rec_vals[0][0].lower().replace("rec_", "")
            parts.append(depth_suffix)

        return "_".join(parts) if parts else "derived"

    def _make_id(self, level: str, profile: Dict[str, float]) -> str:
        sig = ":".join(f"{dim}{profile.get(dim, 0.0):.2f}" for dim in _ALL_DIMS)
        return f"warp_{level}_{hashlib.md5(sig.encode()).hexdigest()[:8]}"

    def _record_anomaly(self, gap: CoverageGap) -> None:
        """Log a potential beyond-5-constraint signal without acting on it."""
        sig = ":".join(
            f"{ist}{gap.axis_profile.get(ist, 0.0):.1f}"
            for ist in _ALL_ISTATES
            if gap.axis_profile.get(ist, 0.0) > 0.3
        )
        key = hashlib.md5(sig.encode()).hexdigest()[:10]
        if key in self._anomaly_log:
            rec = self._anomaly_log[key]
            rec.occurrence_count += 1
            rec.last_seen = time.time()
            if (
                not rec.promoted_to_candidate
                and rec.occurrence_count >= ANOMALY_CANDIDATE_THRESHOLD
            ):
                rec.promoted_to_candidate = True
        else:
            self._anomaly_log[key] = ConstraintAnomalyRecord(
                anomaly_id=key,
                axis_residual=round(1.0 - gap.best_coverage, 4),
                triggering_profile=dict(gap.axis_profile),
            )

    def anomaly_summary(self) -> List[Dict[str, Any]]:
        """Surface logged 6th-constraint anomalies, ranked by recurrence."""
        return [
            {
                "id":           r.anomaly_id,
                "occurrences":  r.occurrence_count,
                "residual":     r.axis_residual,
                "profile":      r.triggering_profile,
                "candidate":    r.promoted_to_candidate,
                "first_seen":   r.first_seen,
                "last_seen":    r.last_seen,
            }
            for r in sorted(
                self._anomaly_log.values(),
                key=lambda r: r.occurrence_count,
                reverse=True,
            )
        ]

    def has_candidates(self) -> bool:
        """True if any anomaly has crossed the candidate threshold."""
        return any(r.promoted_to_candidate for r in self._anomaly_log.values())


# ─── WarpCapable Mixin ────────────────────────────────────────────────────────

class WarpCapable:
    """
    Mixin that makes any Aurora system level structurally extensible via WARP.

    Concrete levels override the five abstract methods below. The mixin handles
    gap detection, gap persistence tracking, component lifecycle (trial →
    promote / dissolve), and status reporting.

    Usage
    -----
    class MySystem(WarpCapable):
        def __init__(self):
            self._init_warp()
            ...

        # required overrides:
        def _get_axis_profiles(self) -> Dict[str, Dict[str, float]]: ...
        def _warp_level_name(self) -> str: ...
        def _integrate_warp(self, component: WarpComponent) -> None: ...
        def _score_trial(self, component: WarpComponent) -> float: ...
        def _dissolve_warp(self, component_id: str) -> None: ...

        # optional override:
        def _warp_params(self, gap, parent_ids) -> Dict[str, Any]: return {}
    """

    def _init_warp(self, genealogy: Any = None) -> None:
        self._warp_trials:    Dict[str, WarpComponent] = {}
        self._warp_promoted:  Dict[str, WarpComponent] = {}
        self._warp_generator: WarpGenerator = WarpGenerator()
        self._warp_genealogy: Any = genealogy  # ConstraintGenealogyLogger or None
        self._contradiction_ledger: Any = None  # ContradictionLedger or None — injected via connect_contradiction_ledger
        self._sedimemory: Any = None  # L3.5 SediMemory or None — injected via connect_sedimemory
        self._gap_counter:    Dict[str, int] = {}   # gap_sig → consecutive count
        self._last_gap:       Optional[CoverageGap] = None
        # MTSL, live-wired 2026-07-14: a failed trial is pruned from
        # _warp_trials by evaluate_warp_trials() itself (WarpCapable
        # discipline -- dissolved components aren't archived), so this
        # running counter is the only "it happened" record left for the
        # alive/dead catalog (lifecycle_catalog.py) to read. Purely
        # additive bookkeeping -- changes no lifecycle decision.
        self._warp_dissolved_count: int = 0

    def connect_sedimemory(self, sedimemory: Any) -> None:
        """
        Late-bind a SediMemory instance so Warp's discovery/synthesis output
        deposits into the channel-carving erosion substrate (PathRegistry /
        SedimentChannel) instead of staying local to this host system.
        Mirrors the existing connect_sedimemory() convention used by
        ConsciousnessEngine, DimensionalSystems, and BehavioralIdentityEngine.
        Safe to skip — Warp functions identically without it.
        """
        self._sedimemory = sedimemory

    def connect_contradiction_ledger(self, ledger: Any) -> None:
        """
        Late-bind a ContradictionLedger so trial scoring (evaluate_warp_trials)
        can dampen promotion under elevated unresolved-contradiction heat.
        This is a GLOBAL throttle, not per-path attribution — see the
        signal-through directive, Section 2, for why that's the honest
        scope of this signal as currently wired. Safe to skip — Warp trial
        scoring functions identically (pure _score_trial output) without it.
        """
        self._contradiction_ledger = ledger


    def set_warp_genealogy(self, genealogy: Any) -> None:
        """
        Late-bind a ConstraintGenealogyLogger so future WARP derivations
        search the fossil record before fresh synthesis. Call this once the
        genealogy is available in systems (it won't be at construction time).
        """
        if hasattr(self, "_warp_genealogy"):
            self._warp_genealogy = genealogy

    # ── abstract interface (override in concrete level) ───────────────────────

    def _get_axis_profiles(self) -> Dict[str, Dict[str, float]]:
        """Return {component_id: axis_profile} for ALL current components."""
        raise NotImplementedError

    def _warp_level_name(self) -> str:
        raise NotImplementedError

    def _integrate_warp(self, component: WarpComponent) -> None:
        """Add the new component to the running system."""
        raise NotImplementedError

    def _score_trial(self, component: WarpComponent) -> float:
        """
        Return a quality score [0.0, 1.0] for the trial component.
        Called once per tick/advance cycle.
        """
        raise NotImplementedError

    def _dissolve_warp(self, component_id: str) -> None:
        """Remove a failed trial component from the running system."""
        raise NotImplementedError

    def _warp_params(
        self,
        gap: CoverageGap,
        parent_ids: List[str],
    ) -> Dict[str, Any]:
        return {}

    def _sediment_warp_traversal(
        self,
        component: "WarpComponent",
        event: str,
    ) -> None:
        """
        Deposit a Warp lifecycle event into SediMemory, if the host has
        connected one via connect_sedimemory(). This is the "signal travels
        through the field and carves a path" mechanism — Warp's own
        discovery/synthesis output now participates in the same
        channel-carving erosion (PathRegistry/SedimentChannel) that governs
        the rest of Aurora's memory substrate, instead of staying siloed
        inside the host system that spawned it.

        event: "warp_gap_closed" (component just integrated, first traversal)
               or "warp_trial_promoted" (component proved itself over
               TRIAL_TICKS — a stronger, independently-weighted traversal)

        Silent no-op if the host never called connect_sedimemory() — Warp
        must function identically with or without SediMemory present.
        """
        sedi = getattr(self, "_sedimemory", None)
        if sedi is None:
            return
        try:
            from aurora_internal.aurora_constraint_manifold_patched import ConstraintVector
        except ImportError:
            from aurora_constraint_manifold_patched import ConstraintVector  # type: ignore
        from foundational_contract import ExistenceMode

        axes_5d = istates_to_axes(component.axis_profile)
        try:
            cv = ConstraintVector(
                X=axes_5d.get("X", 0.5),
                T=axes_5d.get("T", 0.5),
                N=axes_5d.get("N", 0.5),
                B=axes_5d.get("B", 0.5),
                A=axes_5d.get("A", 0.5),
            )
        except Exception:
            return  # manifold rejected an out-of-band profile — don't force it

        try:
            sedi.ingest_event(
                content={
                    "source":        "warp_traversal",
                    "event":         event,
                    "level":         component.level,
                    "component_id":  component.component_id,
                    "name":          component.name,
                    "parent_ids":    list(component.parent_ids or []),
                    "trial_score":   round(float(component.trial_score_ema), 4),
                },
                constraint_vector=cv,
                source=self._warp_level_name() if hasattr(self, "_warp_level_name") else "warp",
                existence_mode=ExistenceMode.AGENTIC,
            )
        except Exception:
            pass  # SediMemory ingestion is best-effort; never break Warp lifecycle on it

    # ── public interface ──────────────────────────────────────────────────────

    def check_and_extend(
        self,
        data_axes: Dict[str, float],
        source: str = "",
        tick: int = 0,
        topology_gap_ref: Optional[str] = None,
    ) -> Optional[WarpComponent]:
        """
        Check coverage of data_axes. If a persistent gap exists, generate
        and integrate a new component. Returns the new component or None.

        The gap must persist for GAP_PERSISTENCE_REQUIRED consecutive checks
        before WARP fires — single-tick anomalies are not acted on.

        topology_gap_ref (MTSL, live-wired 2026-07-14): optional
        provenance tag threaded straight through to WarpGenerator.generate()
        -- see that method's own docstring. Purely a label on whatever
        component this call spawns; changes nothing about detection,
        trial scoring, or promotion.
        """
        profiles = self._get_axis_profiles()
        # Include already-promoted warp components in coverage
        for comp in self._warp_promoted.values():
            profiles[comp.component_id] = comp.axis_profile

        checker = AxisCoverageChecker(profiles)
        gap = checker.check(data_axes, source=source, tick=tick)

        if gap is None:
            self._gap_counter.clear()
            return None

        self._last_gap = gap
        gap_sig = self._gap_signature(gap)
        self._gap_counter[gap_sig] = self._gap_counter.get(gap_sig, 0) + 1

        if self._gap_counter[gap_sig] < GAP_PERSISTENCE_REQUIRED:
            return None  # not yet persistent enough

        # Reset counter so the same gap doesn't keep spawning components
        self._gap_counter[gap_sig] = 0

        new_comp = self._warp_generator.generate(
            gap=gap,
            level=self._warp_level_name(),
            level_params_fn=lambda g, pids: self._warp_params(g, pids),
            genealogy=getattr(self, "_warp_genealogy", None),
            topology_gap_ref=topology_gap_ref,
        )

        if new_comp is None:
            return None  # 6th-axis anomaly logged, not instantiated

        # Avoid duplicate warps at the same coordinate
        if (
            new_comp.component_id in self._warp_trials
            or new_comp.component_id in self._warp_promoted
        ):
            return None

        self._integrate_warp(new_comp)
        self._sediment_warp_traversal(new_comp, "warp_gap_closed")
        self._warp_trials[new_comp.component_id] = new_comp
        return new_comp

    def evaluate_warp_trials(self) -> Tuple[List[str], List[str]]:
        """
        Score all trial components. Promote or dissolve based on EMA score.
        Returns (promoted_ids, dissolved_ids). Call once per tick/advance cycle.
        """
        promoted: List[str] = []
        dissolved: List[str] = []

        for comp_id in list(self._warp_trials):
            comp = self._warp_trials[comp_id]
            score = self._score_trial(comp)

            ledger = getattr(self, "_contradiction_ledger", None)
            if ledger is not None:
                try:
                    heat = float(ledger.heat_contribution())
                    score = score * max(0.0, 1.0 - heat)
                except Exception:
                    pass

            comp.trial_score_ema = 0.7 * comp.trial_score_ema + 0.3 * score
            comp.trial_tick += 1

            if comp.trial_tick < TRIAL_TICKS:
                continue

            if comp.trial_score_ema >= PROMOTION_SCORE:
                comp.promoted = True
                self._warp_promoted[comp_id] = comp
                del self._warp_trials[comp_id]
                self._sediment_warp_traversal(comp, "warp_trial_promoted")
                promoted.append(comp_id)
            else:
                comp.dissolved = True
                self._dissolve_warp(comp_id)
                del self._warp_trials[comp_id]
                dissolved.append(comp_id)
                self._warp_dissolved_count = getattr(self, "_warp_dissolved_count", 0) + 1

        return promoted, dissolved

    def warp_status(self) -> Dict[str, Any]:
        """Return current WARP state summary for diagnostics and observation string."""
        return {
            "level":    self._warp_level_name() if hasattr(self, "_warp_generator") else "?",
            "trials":   len(getattr(self, "_warp_trials", {})),
            "promoted": len(getattr(self, "_warp_promoted", {})),
            "dissolved": getattr(self, "_warp_dissolved_count", 0),
            "anomalies": (
                len(self._warp_generator._anomaly_log)
                if hasattr(self, "_warp_generator") else 0
            ),
            "has_sixth_axis_candidates": (
                self._warp_generator.has_candidates()
                if hasattr(self, "_warp_generator") else False
            ),
            "trial_components": [
                {
                    "id":      c.component_id,
                    "name":    c.name,
                    "profile": c.axis_profile,
                    "score":   round(c.trial_score_ema, 3),
                    "tick":    c.trial_tick,
                }
                for c in getattr(self, "_warp_trials", {}).values()
            ],
            "promoted_components": [
                {
                    "id":      c.component_id,
                    "name":    c.name,
                    "profile": c.axis_profile,
                }
                for c in getattr(self, "_warp_promoted", {}).values()
            ],
        }

    # ── private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _gap_signature(gap: CoverageGap) -> str:
        """
        Stable string key for comparing gaps across ticks. Operates in 15D space.
        Includes dominant I-states AND dominant recursion depth — two gaps at the
        same I-state coordinate but different recursion depths are different gaps.
        """
        dominant_istates = tuple(
            ist for ist in _ALL_ISTATES if gap.axis_profile.get(ist, 0.0) > _DOMINANCE_FLOOR
        )
        dominant_rec = tuple(
            r for r in _RECURSION_DIMS if gap.axis_profile.get(r, 0.0) > _DOMINANCE_FLOOR
        )
        return ":".join(dominant_istates + dominant_rec)


# ══════════════════════════════════════════════════════════════════════════════
# WARP AS UNIVERSAL ACCOMMODATION PRIMITIVE
# ══════════════════════════════════════════════════════════════════════════════
#
# DOCTRINE:
#   WARP is Aurora's universal accommodation function: whenever the existing
#   architecture cannot resolve tension, gap, ambiguity, contradiction, or
#   prediction failure, WARP receives the unresolved relation and attempts to
#   generate a viable new relation.
#
#   Every unresolved state must either resolve locally, route to WARP, or be
#   consciously deferred.  Nothing silently disappears.
#
#   WarpCapable is ONE ACTUATOR within this system (the structural-gap /
#   derive-component pathway).  It is not the root primitive.
#   The root primitive is: unresolved → WarpField.
#
# AUTHORS: Sunni (Sir) Morningstar & Cael Devo
# ══════════════════════════════════════════════════════════════════════════════


class WarpTrigger:
    """Standard trigger-type constants. Any string is valid; these are canonical."""
    GAP                     = "gap"
    AMBIGUITY               = "ambiguity"
    CONTRADICTION           = "contradiction"
    TENSION                 = "tension"
    FAILED_PREDICTION       = "failed_prediction"
    MISSING_REPRESENTATION  = "missing_representation"
    FAILED_COMPREHENSION    = "failed_comprehension"
    CONFLICTING_OUTPUTS     = "conflicting_outputs"
    NO_ACTION               = "no_action"
    NO_MEMORY               = "no_memory"
    NO_LANGUAGE_FORM        = "no_language_form"
    NO_STABLE_PATH          = "no_stable_path"
    NO_ORGAN_ALIGNMENT      = "no_organ_alignment"


class WarpPathway:
    """Resolution pathways. WarpField selects one per demand."""
    IGNORE              = "ignore"           # noise — below severity floor
    DEFER               = "defer"            # low-severity, may self-resolve
    SEEK                = "seek"             # answerable — ask or retrieve info
    DERIVE_LOCAL        = "derive_local"     # structural gap in one system
    DERIVE_MEDIATOR     = "derive_mediator"  # cross-system tension / contradiction
    REVISE_MODEL        = "revise_model"     # prediction or expectation failed
    GENERATE_FORM       = "generate_form"    # no language / representation exists
    SURFACE_EMERGENCE   = "surface_emergence"  # architecture-level failure
    ANOMALY             = "anomaly"          # possible new primitive — accumulate


@dataclass
class WarpDemand:
    """
    The universal primitive: an unresolved state emitted by any layer.

    Any process in Aurora that cannot resolve what is happening through its
    existing architecture constructs a WarpDemand and submits it to WarpField.
    The submitting system does NOT need to know what WARP will do.
    It only confesses: "I cannot resolve this."

    Fields
    ------
    source          system/module name emitting the demand
    layer           architectural layer (e.g. "perception", "memory", "expression")
    trigger         WarpTrigger constant or custom string describing the failure kind
    unresolved_text the raw text / content that could not be accommodated
    expected        what the system predicted or required
    actual          what actually arrived or was found
    participants    other subsystem names involved in a cross-system conflict
    profile         axis / I-state profile of the unresolved content (5D or 10D dict)
    local_attempts  list of resolution strategies already tried and failed
    severity        0.0–1.0; governs pathway selection and escalation
    persistence_key stable key to track a recurring unresolved state across ticks
    """
    source:           str
    layer:            str
    trigger:          str
    unresolved_text:  str             = ""
    expected:         Dict[str, Any]  = field(default_factory=dict)
    actual:           Dict[str, Any]  = field(default_factory=dict)
    participants:     List[str]       = field(default_factory=list)
    profile:          Dict[str, float]= field(default_factory=dict)
    local_attempts:   List[str]       = field(default_factory=list)
    severity:         float           = 0.0
    persistence_key:  str             = ""
    timestamp:        float           = field(default_factory=time.time)
    demand_id:        str             = field(
        default_factory=lambda: uuid.uuid4().hex[:12]
    )


@dataclass
class WarpDecision:
    """
    What WarpField decided to do with a WarpDemand.

    The caller receives this immediately from warp_guard() / WarpField.submit().
    action_taken=True means a handler ran; resolved=True means the handler
    reported a successful resolution.  Most pathways will have action_taken=False
    on first pass — the decision records the intent, handlers fill in the result.
    """
    demand:       WarpDemand
    pathway:      str
    action_taken: bool       = False
    resolved:     bool       = False
    result:       Any        = None
    notes:        str        = ""
    decided_at:   float      = field(default_factory=time.time)


class WarpField:
    """
    The universal accommodation field.

    Every unresolved state in Aurora routes here.  WarpField classifies the
    demand by trigger type and severity, selects a resolution pathway, and
    dispatches to the appropriate actuator — which may be a WarpCapable
    structural-gap resolver, a registered pathway handler, or the deferral /
    anomaly ledger.

    WarpCapable is ONE ACTUATOR (derive_local / derive_mediator).
    The field is the root primitive.

    Lifecycle
    ---------
    1. Any subsystem calls warp_guard() or WarpField.submit(WarpDemand).
    2. _classify() maps trigger + severity → WarpPathway.
    3. _route() dispatches to registered handler or WarpCapable registry.
    4. WarpDecision is returned immediately; long-running work is async.

    Registration
    ------------
    register_warp_capable(name, system)    — for derive_local / derive_mediator
    register_pathway_handler(pathway, fn)  — for seek / revise_model / generate_form
                                             / surface_emergence handlers
    """

    # Maps canonical trigger → default pathway (severity may override)
    _TRIGGER_PATHWAY: Dict[str, str] = {
        WarpTrigger.GAP:                    WarpPathway.DERIVE_LOCAL,
        WarpTrigger.AMBIGUITY:              WarpPathway.SEEK,
        WarpTrigger.CONTRADICTION:          WarpPathway.DERIVE_MEDIATOR,
        WarpTrigger.TENSION:                WarpPathway.DERIVE_MEDIATOR,
        WarpTrigger.FAILED_PREDICTION:      WarpPathway.REVISE_MODEL,
        WarpTrigger.MISSING_REPRESENTATION: WarpPathway.GENERATE_FORM,
        WarpTrigger.FAILED_COMPREHENSION:   WarpPathway.SEEK,
        WarpTrigger.CONFLICTING_OUTPUTS:    WarpPathway.DERIVE_MEDIATOR,
        WarpTrigger.NO_ACTION:              WarpPathway.SURFACE_EMERGENCE,
        WarpTrigger.NO_MEMORY:              WarpPathway.SEEK,
        WarpTrigger.NO_LANGUAGE_FORM:       WarpPathway.GENERATE_FORM,
        WarpTrigger.NO_STABLE_PATH:         WarpPathway.DEFER,
        WarpTrigger.NO_ORGAN_ALIGNMENT:     WarpPathway.SURFACE_EMERGENCE,
    }

    # Severity below this → IGNORE
    _NOISE_FLOOR: float = 0.08
    # Severity below this → downgrade to DEFER (unless already IGNORE/ANOMALY)
    _DEFER_CEILING: float = 0.25
    # Severity above this with a persistence_key → escalate to ANOMALY
    _ANOMALY_FLOOR: float = 0.90

    def __init__(self) -> None:
        self._demands:   deque = deque(maxlen=2000)
        self._decisions: deque = deque(maxlen=2000)
        self._deferred:  List[WarpDecision] = []
        self._anomaly_ledger: List[WarpDecision] = []
        self._warp_capable_registry: Dict[str, Any] = {}
        self._pathway_handlers: Dict[str, Callable] = {}
        self._demand_count:    int = 0
        self._pathway_counts:  Dict[str, int] = {}

    def register_warp_capable(self, name: str, system: Any) -> None:
        """Register a WarpCapable system for derive_local / derive_mediator routing."""
        self._warp_capable_registry[name] = system

    def register_pathway_handler(
        self, pathway: str, handler: Callable[["WarpDecision"], Any]
    ) -> None:
        """
        Register a handler for a resolution pathway.
        Handler receives WarpDecision, sets decision.result / decision.resolved,
        returns any result object or None.
        """
        self._pathway_handlers[pathway] = handler

    def submit(self, demand: WarpDemand) -> WarpDecision:
        """
        The law: every unresolved state enters here.
        Returns a WarpDecision synchronously.
        """
        self._demands.append(demand)
        self._demand_count += 1

        pathway = self._classify(demand)
        decision = WarpDecision(demand=demand, pathway=pathway)
        self._pathway_counts[pathway] = self._pathway_counts.get(pathway, 0) + 1

        self._route(decision)
        self._decisions.append(decision)
        return decision

    def _classify(self, demand: WarpDemand) -> str:
        sev = float(demand.severity)

        if sev < self._NOISE_FLOOR:
            return WarpPathway.IGNORE

        # High-severity + recurring = possible new primitive
        if sev >= self._ANOMALY_FLOOR and demand.persistence_key:
            return WarpPathway.ANOMALY

        # Canonical trigger lookup
        trigger = demand.trigger.lower()
        for key, pathway in self._TRIGGER_PATHWAY.items():
            if trigger == key or trigger.startswith(key):
                # Low severity downgrades non-terminal pathways to defer
                if sev < self._DEFER_CEILING and pathway not in (
                    WarpPathway.IGNORE, WarpPathway.ANOMALY, WarpPathway.DEFER
                ):
                    return WarpPathway.DEFER
                return pathway

        # Unknown trigger — severity-based fallback
        if sev < self._DEFER_CEILING:
            return WarpPathway.DEFER
        if sev >= 0.70:
            return WarpPathway.SURFACE_EMERGENCE
        return WarpPathway.SEEK

    def _route(self, decision: WarpDecision) -> None:
        pathway = decision.pathway

        if pathway == WarpPathway.IGNORE:
            return

        if pathway == WarpPathway.DEFER:
            self._deferred.append(decision)
            decision.notes = "deferred — severity below action threshold"
            return

        if pathway == WarpPathway.ANOMALY:
            self._anomaly_ledger.append(decision)
            decision.notes = "logged to anomaly ledger — possible new primitive"
            return

        # Registered pathway handler takes precedence
        handler = self._pathway_handlers.get(pathway)
        if handler:
            try:
                result = handler(decision)
                if result is not None:
                    decision.result = result
                decision.action_taken = True
                decision.resolved = True
            except Exception:
                decision.notes = f"handler for '{pathway}' raised exception"
            return

        # derive_local / derive_mediator → WarpCapable structural actuator
        if pathway in (WarpPathway.DERIVE_LOCAL, WarpPathway.DERIVE_MEDIATOR):
            self._route_to_warp_capable(decision)
            return

        # All other pathways without a registered handler: record intent
        decision.notes = f"pathway '{pathway}' awaiting handler registration"

    def _route_to_warp_capable(self, decision: WarpDecision) -> None:
        """Route derive_local / derive_mediator to the best WarpCapable system."""
        demand = decision.demand
        profile = demand.profile

        # Prefer the named source system; fall back to any registered system
        system = self._warp_capable_registry.get(demand.source)
        if system is None and self._warp_capable_registry:
            system = next(iter(self._warp_capable_registry.values()))

        if system is None or not profile:
            decision.notes = "no warp_capable system or profile for derive pathway"
            return

        try:
            comp = system.check_and_extend(
                profile, source=demand.source, tick=0
            )
            if comp is not None:
                decision.result = comp
                decision.action_taken = True
                decision.resolved = True
                decision.notes = f"derived component: {comp.component_id}"
            else:
                decision.notes = "gap below persistence threshold — monitoring"
        except Exception as exc:
            decision.notes = f"warp_capable error: {exc}"

    def flush_deferred(self) -> List[WarpDecision]:
        """
        Re-submit deferred demands with decayed severity.
        Call periodically (e.g. once per epoch or on idle tick).
        Demands that decay below noise floor are silently dropped.
        """
        pending = list(self._deferred)
        self._deferred.clear()
        results: List[WarpDecision] = []
        for dec in pending:
            dec.demand.severity *= 0.80
            if dec.demand.severity >= self._NOISE_FLOOR:
                results.append(self.submit(dec.demand))
        return results

    def anomaly_ledger_summary(self) -> List[Dict[str, Any]]:
        """
        Return a summary of WarpDecision anomaly entries, ranked by severity.
        Non-destructive — the ledger is not cleared.
        Consumers (e.g. CuriosityEngine) use this to surface recurring
        high-severity unresolved demands as curiosity targets.
        """
        seen: Dict[str, Dict[str, Any]] = {}
        for dec in self._anomaly_ledger:
            key = dec.demand.persistence_key or dec.demand.demand_id
            if key in seen:
                seen[key]["count"] += 1
                seen[key]["last_severity"] = max(
                    seen[key]["last_severity"], float(dec.demand.severity)
                )
            else:
                seen[key] = {
                    "persistence_key": key,
                    "source":          dec.demand.source,
                    "layer":           dec.demand.layer,
                    "trigger":         dec.demand.trigger,
                    "unresolved_text": dec.demand.unresolved_text[:120],
                    "last_severity":   float(dec.demand.severity),
                    "count":           1,
                    "first_seen":      dec.demand.timestamp,
                }
        return sorted(
            seen.values(),
            key=lambda r: (r["count"], r["last_severity"]),
            reverse=True,
        )

    def drain_anomaly_ledger(self, keep_recent: int = 50) -> int:
        """
        Compact the anomaly ledger, keeping only the most recent `keep_recent`
        entries. Returns the number of entries removed.
        Call at most once per epoch — not per tick.
        """
        removed = max(0, len(self._anomaly_ledger) - keep_recent)
        if removed > 0:
            self._anomaly_ledger = self._anomaly_ledger[-keep_recent:]
        return removed

    def status(self) -> Dict[str, Any]:
        return {
            "total_demands":      self._demand_count,
            "pending_deferred":   len(self._deferred),
            "anomaly_ledger":     len(self._anomaly_ledger),
            "pathway_counts":     dict(self._pathway_counts),
            "registered_systems": list(self._warp_capable_registry.keys()),
            "registered_handlers": list(self._pathway_handlers.keys()),
        }


# ── Module-level field singleton + helpers ────────────────────────────────────

_global_warp_field: Optional[WarpField] = None


def get_warp_field() -> WarpField:
    """Return the global WarpField, creating it lazily if not yet installed."""
    global _global_warp_field
    if _global_warp_field is None:
        _global_warp_field = WarpField()
    return _global_warp_field


def install_warp_field(field: WarpField) -> None:
    """
    Install the system's WarpField as the global singleton.
    Call once at boot after creating WarpField with registered systems.
    """
    global _global_warp_field
    _global_warp_field = field


def warp_guard(
    source: str,
    layer: str,
    trigger: str,
    *,
    unresolved_text: str = "",
    expected: Optional[Dict] = None,
    actual: Optional[Dict] = None,
    participants: Optional[List[str]] = None,
    profile: Optional[Dict] = None,
    local_attempts: Optional[List[str]] = None,
    severity: float = 0.5,
    persistence_key: str = "",
) -> WarpDecision:
    """
    The universal confession: "I cannot resolve this."

    Every subsystem that hits an unresolved state calls this.
    Returns the WarpDecision so the caller can inspect what WARP chose.

    Example
    -------
    if not response_found:
        warp_guard(
            source="memory",
            layer="comprehension",
            trigger=WarpTrigger.NO_MEMORY,
            unresolved_text=query,
            severity=0.6,
        )
    """
    demand = WarpDemand(
        source=source,
        layer=layer,
        trigger=trigger,
        unresolved_text=unresolved_text,
        expected=expected or {},
        actual=actual or {},
        participants=participants or [],
        profile=profile or {},
        local_attempts=local_attempts or [],
        severity=severity,
        persistence_key=persistence_key,
    )
    return get_warp_field().submit(demand)


# ── Exception-hook sealing ─────────────────────────────────────────────────────
# After seal_warp() is called it is structurally impossible for an unhandled
# Python exception to exit the Aurora process without WARP seeing it.

def _warp_excepthook(
    exc_type: type,
    exc_value: BaseException,
    exc_tb: Any,
    *,
    original_hook: Optional[Callable] = None,
) -> None:
    """Route unhandled exceptions to WarpField, then fall through to default."""
    try:
        source_module = "unknown"
        if exc_tb is not None:
            frame = exc_tb
            while frame.tb_next is not None:
                frame = frame.tb_next
            source_module = frame.tb_frame.f_globals.get("__name__", "unknown")
        get_warp_field().submit(WarpDemand(
            source=source_module,
            layer="exception",
            trigger=WarpTrigger.NO_STABLE_PATH,
            unresolved_text=f"{exc_type.__name__}: {exc_value}",
            severity=0.75,
            persistence_key=exc_type.__name__,
        ))
    except Exception:
        pass
    if original_hook is not None:
        original_hook(exc_type, exc_value, exc_tb)
    else:
        import sys as _sys
        _sys.__excepthook__(exc_type, exc_value, exc_tb)


def seal_warp(warp_field: Optional[WarpField] = None) -> None:
    """
    Seal WARP as a primitive.

    Installs sys.excepthook and threading.excepthook so unhandled Python
    exceptions auto-route to WarpField before the process sees them.
    After this call, no unresolved state in the Aurora process can exit
    without WARP receiving it.

    Call once at boot after install_warp_field().
    """
    import sys as _sys
    import threading as _threading

    if warp_field is not None:
        install_warp_field(warp_field)

    _prev_hook = getattr(_sys, "excepthook", None)
    _sys.excepthook = lambda et, ev, tb: _warp_excepthook(
        et, ev, tb,
        original_hook=_prev_hook if (
            _prev_hook is not None and _prev_hook is not _sys.__excepthook__
        ) else None,
    )

    _prev_thread_hook = getattr(_threading, "excepthook", None)

    def _thread_warp_hook(args: Any) -> None:
        try:
            get_warp_field().submit(WarpDemand(
                source=(
                    getattr(args.thread, "name", "thread")
                    if getattr(args, "thread", None) is not None else "thread"
                ),
                layer="exception",
                trigger=WarpTrigger.NO_STABLE_PATH,
                unresolved_text=(
                    f"{args.exc_type.__name__}: {args.exc_value}"
                    if getattr(args, "exc_type", None) is not None
                    else "thread_exception"
                ),
                severity=0.75,
                persistence_key=getattr(
                    getattr(args, "exc_type", None), "__name__", "thread_error"
                ),
            ))
        except Exception:
            pass
        if _prev_thread_hook is not None:
            try:
                _prev_thread_hook(args)
            except Exception:
                pass

    _threading.excepthook = _thread_warp_hook
