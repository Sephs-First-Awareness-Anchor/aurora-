# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
CERS Regulator — Conscious Experiential Regulation System, governing logic layer.

This module holds ONLY the novel ERS mechanics that do not exist in the legacy
dual_strata pipeline:

    1. Conflict-of-correctness detection — where legacy `converge_crests()`
       (dce_bridge.py) always blends two competing crest clusters into a
       mixed label, `cers_converge()` first checks whether the two dominant
       clusters are structurally opposed at real severity. If so, it refuses
       to blend and surfaces an explicit `unresolved_conflict` crest instead,
       forcing resolution at a higher layer rather than smoothing it over.

    2. Unused-potential tracking — a rolling per-channel intensity history
       across the eight fixed waveform positions (see subsystem_waveforms.py
       CHANNEL order), flagging any channel that has gone chronically dormant.

    3. Equivalence bookkeeping — CERSVerdict carries the data a higher layer
       (or Aurora's own self-observation) needs to eventually recognize when
       the CERS-native convergence and the legacy convergence agree, without
       CERS ever overriding or removing the legacy path.

This module does not build overlays, prediction signals, or emit subsystem
crests — those stages are unchanged and are reused directly from dce_bridge.py
and subsystem_waveforms.py by cers_bridge.py. CERS only governs the single
convergence step where sub_crests become one subsurface_crest.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple

from .crest import Crest
from .subsurface_state import clip01
from .dce_bridge import _CONVERGENCE_GROUPS, converge_crests

# ---------------------------------------------------------------------------
# Fixed channel order — matches emit_subsystem_crests() core tuple exactly
# (subsystem_waveforms.py, `core_crests = (...)`). Warp-derived crests beyond
# this fixed length are tracked separately, keyed by label.
# ---------------------------------------------------------------------------
CORE_CHANNEL_NAMES: Tuple[str, ...] = (
    "sensory", "memory", "emotional", "prediction",
    "symbolic", "continuity", "constraint", "pressure",
)

# ---------------------------------------------------------------------------
# Opposed-cluster pairs: clusters that cannot both be the dominant read of the
# same moment without one subordinating the other. Distinct from legacy's
# _mixed_labels blend pairs in dce_bridge.py, which represent legitimate
# co-occurring blends (e.g. comfort+caution -> warmth). These pairs represent
# genuine structural incompatibility, not a blendable middle ground.
# ---------------------------------------------------------------------------
_OPPOSED_CLUSTER_PAIRS: Dict[frozenset, str] = {
    frozenset({"constraint", "alignment"}): "capacity_vs_resonance",
    frozenset({"continuity", "novelty"}): "thread_vs_novelty",
    frozenset({"comfort", "urgency"}): "safety_vs_alarm",
    frozenset({"steady", "reframe"}): "stability_vs_reframe",
}

CONFLICT_SEVERITY_THRESHOLD = 0.32
DORMANCY_THRESHOLD = 0.35
DORMANCY_TICKS = 8
POTENTIAL_WINDOW = 20


@dataclass(frozen=True)
class CrestConflict:
    """A detected structural incompatibility between two active crest clusters."""

    conflict_id: str
    cluster_a: str
    cluster_b: str
    intensity_a: float
    intensity_b: float
    severity: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "cluster_a": self.cluster_a,
            "cluster_b": self.cluster_b,
            "intensity_a": round(self.intensity_a, 4),
            "intensity_b": round(self.intensity_b, 4),
            "severity": round(self.severity, 4),
        }


@dataclass
class CERSVerdict:
    """What CERS decided about this frame's convergence, and why."""

    permitted: bool
    conflicts: List[CrestConflict] = field(default_factory=list)
    unused_potential: List[str] = field(default_factory=list)
    actively_trialing_potential: List[str] = field(default_factory=list)
    confirmed_potential_benefits: Dict[str, str] = field(default_factory=dict)
    confirmed_inert_potential: List[str] = field(default_factory=list)
    intervention_label: Optional[str] = None
    legacy_label: Optional[str] = None
    cers_label: Optional[str] = None
    agrees_with_legacy: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "permitted": bool(self.permitted),
            "conflicts": [c.to_dict() for c in self.conflicts],
            "unused_potential": list(self.unused_potential),
            "actively_trialing_potential": list(self.actively_trialing_potential),
            "confirmed_potential_benefits": dict(self.confirmed_potential_benefits),
            "confirmed_inert_potential": list(self.confirmed_inert_potential),
            "intervention_label": self.intervention_label,
            "legacy_label": self.legacy_label,
            "cers_label": self.cers_label,
            "agrees_with_legacy": self.agrees_with_legacy,
        }


class PotentialTracker:
    """Rolling per-channel intensity history. Flags channels that could be
    producing meaningful change but have gone chronically dormant instead."""

    def __init__(self, window: int = POTENTIAL_WINDOW) -> None:
        self._window = window
        self._histories: Dict[str, Deque[float]] = {
            name: deque(maxlen=window) for name in CORE_CHANNEL_NAMES
        }
        self._warp_histories: Dict[str, Deque[float]] = {}

    def observe(self, sub_crests: Tuple[Crest, ...]) -> None:
        for idx, crest in enumerate(sub_crests):
            if idx < len(CORE_CHANNEL_NAMES):
                self._histories[CORE_CHANNEL_NAMES[idx]].append(clip01(crest.intensity))
            else:
                key = crest.label
                self._warp_histories.setdefault(key, deque(maxlen=self._window)).append(
                    clip01(crest.intensity)
                )

    def unused_potential(self) -> List[str]:
        dormant: List[str] = []
        for name, history in self._histories.items():
            if len(history) < DORMANCY_TICKS:
                continue
            recent = list(history)[-DORMANCY_TICKS:]
            if all(v < DORMANCY_THRESHOLD for v in recent):
                dormant.append(name)
        for name, history in self._warp_histories.items():
            if len(history) < DORMANCY_TICKS:
                continue
            recent = list(history)[-DORMANCY_TICKS:]
            if all(v < DORMANCY_THRESHOLD for v in recent):
                dormant.append(name)
        return dormant


def _cluster_intensity_map(sub_crests: Tuple[Crest, ...]) -> Dict[str, float]:
    """Sum crest intensity per convergence cluster, mirroring the grouping
    logic in dce_bridge.converge_crests() but exposed for conflict checks."""
    scores: Dict[str, float] = {}
    for crest in sub_crests:
        cluster = _CONVERGENCE_GROUPS.get(crest.label, "steady")
        scores[cluster] = scores.get(cluster, 0.0) + crest.intensity
    return scores


def channel_intensity_map(sub_crests: Tuple[Crest, ...]) -> Dict[str, float]:
    """Per-channel intensity this tick, keyed the same way PotentialTracker
    keys its histories — fixed core channel name by position, warp crest by
    label beyond that. Feeds PotentialTrialBoard's correlation tests."""
    result: Dict[str, float] = {}
    for idx, crest in enumerate(sub_crests):
        if idx < len(CORE_CHANNEL_NAMES):
            result[CORE_CHANNEL_NAMES[idx]] = clip01(crest.intensity)
        else:
            result[crest.label] = clip01(crest.intensity)
    return result


def detect_conflicts(sub_crests: Tuple[Crest, ...]) -> List[CrestConflict]:
    """Check every known opposed-cluster pair against this frame's cluster
    scores. A conflict is real only when BOTH sides carry a meaningful SHARE
    of the total cluster mass (near an even split, not one side trivially
    dominating) AND both carry meaningful absolute weight. A single loud
    crest from one cluster and a quiet one from the other is not a genuine
    conflict — it's exactly the case legacy's dominance_ratio already
    resolves cleanly. CERS only needs to intervene where legacy's blend
    would otherwise paper over a real near-tie between opposed reads."""
    if not sub_crests:
        return []
    cluster_scores = _cluster_intensity_map(sub_crests)
    total = sum(cluster_scores.values())
    if total <= 1e-9:
        return []
    conflicts: List[CrestConflict] = []
    for pair, conflict_id in _OPPOSED_CLUSTER_PAIRS.items():
        cluster_a, cluster_b = tuple(pair)
        raw_a = cluster_scores.get(cluster_a, 0.0)
        raw_b = cluster_scores.get(cluster_b, 0.0)
        share_a = raw_a / total
        share_b = raw_b / total
        min_share = min(share_a, share_b)
        if min_share >= CONFLICT_SEVERITY_THRESHOLD and raw_a > 0.3 and raw_b > 0.3:
            conflicts.append(
                CrestConflict(
                    conflict_id=conflict_id,
                    cluster_a=cluster_a,
                    cluster_b=cluster_b,
                    intensity_a=clip01(raw_a),
                    intensity_b=clip01(raw_b),
                    severity=round(min_share, 4),
                )
            )
    return conflicts


def cers_converge(
    sub_crests: Tuple[Crest, ...],
    tracker: PotentialTracker,
    trial_board: Optional["PotentialTrialBoard"] = None,
) -> Tuple[Crest, CERSVerdict]:
    """ERS-native convergence. Runs the legacy convergence alongside for
    equivalence bookkeeping, but only defers to it when no structural
    conflict is present. Never mutates or calls into subsurface_state.py's
    private detail — this stays entirely at the crest layer.

    trial_board: when provided, every channel PotentialTracker flags as
    dormant this tick gets an active correlation trial opened against it
    (see cers_potential_trial.py) rather than being reported as a static
    fact. Resolved trials (promoted or dissolved) stop appearing in
    unused_potential/actively_trialing_potential going forward."""
    tracker.observe(sub_crests)
    unused = tracker.unused_potential()
    conflicts = detect_conflicts(sub_crests)

    actively_trialing: List[str] = []
    confirmed_benefits: Dict[str, str] = {}
    confirmed_inert: List[str] = []
    if trial_board is not None:
        cluster_scores = _cluster_intensity_map(sub_crests)
        channel_intensities = channel_intensity_map(sub_crests)
        trial_board.observe(unused, cluster_scores, channel_intensities)
        actively_trialing = trial_board.actively_trialing()
        confirmed_benefits = trial_board.confirmed_benefits()
        confirmed_inert = trial_board.confirmed_inert()

    legacy_crest = converge_crests(sub_crests, mode="subsurface")

    if conflicts:
        worst = max(conflicts, key=lambda c: c.severity)
        peak_axis = "X"
        peak_intensity = 0.0
        for crest in sub_crests:
            cluster = _CONVERGENCE_GROUPS.get(crest.label, "steady")
            if cluster in (worst.cluster_a, worst.cluster_b) and crest.intensity > peak_intensity:
                peak_intensity = crest.intensity
                peak_axis = crest.axis
        cers_crest = Crest(
            label="unresolved_conflict",
            intensity=round(worst.severity, 4),
            axis=peak_axis,
        )
        verdict = CERSVerdict(
            permitted=False,
            conflicts=conflicts,
            unused_potential=unused,
            actively_trialing_potential=actively_trialing,
            confirmed_potential_benefits=confirmed_benefits,
            confirmed_inert_potential=confirmed_inert,
            intervention_label=cers_crest.label,
            legacy_label=legacy_crest.label,
            cers_label=cers_crest.label,
            agrees_with_legacy=False,
        )
        return cers_crest, verdict

    verdict = CERSVerdict(
        permitted=True,
        conflicts=[],
        unused_potential=unused,
        actively_trialing_potential=actively_trialing,
        confirmed_potential_benefits=confirmed_benefits,
        confirmed_inert_potential=confirmed_inert,
        intervention_label=None,
        legacy_label=legacy_crest.label,
        cers_label=legacy_crest.label,
        agrees_with_legacy=True,
    )
    return legacy_crest, verdict
