"""
aurora_warp_protocol.py
========================
Universal structural adaptation mechanism for Aurora's cognitive stack.

DOCTRINE:
    Every system level in Aurora holds a set of components, each oriented
    toward a region of 5D constraint space (X, T, N, B, A). When incoming
    data carries an axis profile that no existing component resonates with,
    that level has a coverage gap. WARP closes it by deriving a new component
    from the closest existing ones — not from nothing, but from what is already
    there, combined in a configuration that wasn't needed until now.

    Every new component is always a derivative combination of the 5 constraints.
    The possibility of a 6th constraint forming exists but requires sustained,
    high-confidence anomaly evidence before any structural action is taken.

    Coverage is measured as cosine similarity in 5D constraint space.
    A gap exists when best cosine < COVERAGE_THRESHOLD.
    A 6th-axis anomaly is flagged when best cosine < ANOMALY_THRESHOLD.

    New components run in trial alongside existing ones. If they score above
    PROMOTION_SCORE across TRIAL_TICKS evaluations, they are promoted.
    Otherwise they dissolve without trace.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

# ─── Constants ────────────────────────────────────────────────────────────────

_ALL_AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")

_AXIS_NAMES: Dict[str, str] = {
    "X": "existence",
    "T": "temporal",
    "N": "energy",
    "B": "boundary",
    "A": "agency",
}

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
    Checks whether a set of axis-profiled components covers an incoming profile.

    Coverage is cosine similarity in 5D constraint space. If the best cosine
    across all components is below COVERAGE_THRESHOLD, a CoverageGap is returned.
    """

    def __init__(self, components: Dict[str, Dict[str, float]]) -> None:
        # {component_id: {axis: weight}}
        self._components: Dict[str, Dict[str, float]] = dict(components)

    def update(self, component_id: str, axis_profile: Dict[str, float]) -> None:
        self._components[component_id] = dict(axis_profile)

    def remove(self, component_id: str) -> None:
        self._components.pop(component_id, None)

    @staticmethod
    def cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
        """Cosine similarity between two axis weight vectors."""
        axes = _ALL_AXES
        dot = sum(a.get(ax, 0.0) * b.get(ax, 0.0) for ax in axes)
        mag_a = math.sqrt(sum(a.get(ax, 0.0) ** 2 for ax in axes))
        mag_b = math.sqrt(sum(b.get(ax, 0.0) ** 2 for ax in axes))
        if mag_a < 1e-9 or mag_b < 1e-9:
            return 0.0
        return dot / (mag_a * mag_b)

    def check(
        self,
        data_axes: Dict[str, float],
        source: str = "",
        tick: int = 0,
    ) -> Optional[CoverageGap]:
        """
        Returns CoverageGap if no existing component resonates with data_axes.
        Returns None if coverage is sufficient (best cosine >= COVERAGE_THRESHOLD).
        """
        if not self._components or not data_axes:
            return None

        scores: Dict[str, float] = {
            cid: self.cosine(profile, data_axes)
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
            axis_profile=dict(data_axes),
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
    derivative of what already exists. The gap's axis profile is the
    attractor; the closest parents contribute their profiles as context.

    6th-axis anomalies are logged and accumulated but never hastily acted on.
    """

    def __init__(self) -> None:
        self._anomaly_log: Dict[str, ConstraintAnomalyRecord] = {}

    def generate(
        self,
        gap: CoverageGap,
        level: str,
        level_params_fn: Optional[Callable[[CoverageGap, List[str]], Dict[str, Any]]] = None,
    ) -> Optional[WarpComponent]:
        """
        Generate a new component from the coverage gap.

        Returns None if the gap is a 6th-axis anomaly — it is logged but
        no structural piece is created until sufficient evidence accumulates.
        """
        if gap.is_sixth_axis_candidate:
            self._record_anomaly(gap)
            return None

        new_profile = self._derive_profile(gap)
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

    def _derive_profile(self, gap: CoverageGap) -> Dict[str, float]:
        """
        Blend gap profile with closest parent profiles.
        Gap contributes _GAP_WEIGHT; parents share _PARENT_WEIGHT weighted
        by their cosine proximity to the gap.
        """
        result = {ax: 0.0 for ax in _ALL_AXES}

        # Gap contribution
        for ax in _ALL_AXES:
            result[ax] += gap.axis_profile.get(ax, 0.0) * _GAP_WEIGHT

        # Parent contribution
        if gap.closest_profiles:
            weights = [
                max(1e-6, AxisCoverageChecker.cosine(p, gap.axis_profile))
                for p in gap.closest_profiles
            ]
            total_w = sum(weights)
            for profile, w in zip(gap.closest_profiles, weights):
                norm_w = (w / total_w) * _PARENT_WEIGHT
                for ax in _ALL_AXES:
                    result[ax] += profile.get(ax, 0.0) * norm_w

        return {ax: round(min(1.0, max(0.0, v)), 3) for ax, v in result.items()}

    def _synthesize_name(self, profile: Dict[str, float]) -> str:
        """Name the component from its dominant axes."""
        dominant = sorted(
            [(ax, profile[ax]) for ax in _ALL_AXES if profile.get(ax, 0.0) >= _DOMINANCE_FLOOR],
            key=lambda t: t[1],
            reverse=True,
        )
        parts = [_AXIS_NAMES[ax] for ax, _ in dominant[:2]]
        return "_".join(parts) if parts else "derived"

    def _make_id(self, level: str, profile: Dict[str, float]) -> str:
        sig = ":".join(f"{ax}{profile.get(ax, 0.0):.2f}" for ax in _ALL_AXES)
        return f"warp_{level}_{hashlib.md5(sig.encode()).hexdigest()[:8]}"

    def _record_anomaly(self, gap: CoverageGap) -> None:
        """Log a potential 6th-constraint signal without acting on it."""
        sig = ":".join(
            f"{ax}{gap.axis_profile.get(ax, 0.0):.1f}"
            for ax in _ALL_AXES
            if gap.axis_profile.get(ax, 0.0) > 0.3
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

    def _init_warp(self) -> None:
        self._warp_trials:    Dict[str, WarpComponent] = {}
        self._warp_promoted:  Dict[str, WarpComponent] = {}
        self._warp_generator: WarpGenerator = WarpGenerator()
        self._gap_counter:    Dict[str, int] = {}   # gap_sig → consecutive count
        self._last_gap:       Optional[CoverageGap] = None

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
        """Stable string key for comparing gaps across ticks."""
        dominant = tuple(
            ax for ax in _ALL_AXES if gap.axis_profile.get(ax, 0.0) > _DOMINANCE_FLOOR
        )
        return ":".join(dominant)
