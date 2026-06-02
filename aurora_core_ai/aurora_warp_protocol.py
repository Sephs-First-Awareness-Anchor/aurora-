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

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

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
    ) -> Optional[WarpComponent]:
        """
        Generate a new component from the coverage gap.

        genealogy: optional ConstraintGenealogyLogger — if provided, its link
        fossil record is searched first to bias the derived profile toward
        proven constraint pairings before purely fresh synthesis.

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
        )

    # ── private ──────────────────────────────────────────────────────────────

    def _search_genealogy(
        self,
        gap: CoverageGap,
        genealogy: Any,
    ) -> List[Dict[str, float]]:
        """
        Query ConstraintGenealogyLogger.links for I-state profiles that
        resonate with the gap. Each ConstraintLink has mean_relief (5D axis)
        and depth (DAG depth) — converted to 15D for cosine comparison.

        Returns up to 3 I-state profiles from top-matching links (min 0.35
        cosine) to bias the derived component toward proven territory.
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
            results.append((sim, link_istate))

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
        self._gap_counter:    Dict[str, int] = {}   # gap_sig → consecutive count
        self._last_gap:       Optional[CoverageGap] = None

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

    # ── public interface ──────────────────────────────────────────────────────

    def check_and_extend(
        self,
        data_axes: Dict[str, float],
        source: str = "",
        tick: int = 0,
    ) -> Optional[WarpComponent]:
        """
        Check coverage of data_axes. If a persistent gap exists, generate
        and integrate a new component. Returns the new component or None.

        The gap must persist for GAP_PERSISTENCE_REQUIRED consecutive checks
        before WARP fires — single-tick anomalies are not acted on.
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
            comp.trial_score_ema = 0.7 * comp.trial_score_ema + 0.3 * score
            comp.trial_tick += 1

            if comp.trial_tick < TRIAL_TICKS:
                continue

            if comp.trial_score_ema >= PROMOTION_SCORE:
                comp.promoted = True
                self._warp_promoted[comp_id] = comp
                del self._warp_trials[comp_id]
                promoted.append(comp_id)
            else:
                comp.dissolved = True
                self._dissolve_warp(comp_id)
                del self._warp_trials[comp_id]
                dissolved.append(comp_id)

        return promoted, dissolved

    def warp_status(self) -> Dict[str, Any]:
        """Return current WARP state summary for diagnostics and observation string."""
        return {
            "level":    self._warp_level_name() if hasattr(self, "_warp_generator") else "?",
            "trials":   len(getattr(self, "_warp_trials", {})),
            "promoted": len(getattr(self, "_warp_promoted", {})),
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
