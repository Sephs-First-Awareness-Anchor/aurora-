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
from dataclasses import dataclass, field, replace
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

# Deliberately the SAME bar as CONFLICT_SEVERITY_THRESHOLD -- one severity
# scale for "worth treating as a real event," whether the event is two
# clusters opposing each other or one established coordinate's own history
# breaking sharply. Not a coincidence; keep these equal.
GEOMETRY_DEVIATION_THRESHOLD = CONFLICT_SEVERITY_THRESHOLD

# ---------------------------------------------------------------------------
# MTSL Phase 4 (2026-07-13): TopologyContext + bounded, stage-gated salience/
# hesitation raise. Field/bound choices below are first-pass, documented
# decisions -- the external MTSL spec's section 12/22 register-rule detail
# wasn't available to this implementation, same posture as topology_frame.py's
# crest/trough axes. Authority staging (directive section 7): the proposed
# raise is always computed (for future evidence-based staging decisions) but
# only actually APPLIED to the surface-facing semantic_salience/
# semantic_hesitation fields at stage 2+; stage 1 is "record only."
#
# ADVANCED 2026-07-14: manual, evidence-cited decision (directive section 7's
# own bar for this) to move from stage 1 to stage 2, made explicitly by the
# user after reviewing this session's Phase 0-8 implementation and its
# acceptance-report evidence (mtsl_acceptance_report.py confirmed
# applied_strategy_shift_count stayed 0 through 30 real turns at stage 1,
# and that the summarizer WOULD have detected it if raised). This is the one
# line that turns MTSL from a pure observer into something that actually
# raises real hesitation/salience -- every live call site that reads it
# (cers_bridge.py, aurora_articulation.py) still only ever RAISES bounded
# signals, never lowers or overrides a base decision outright.
# ---------------------------------------------------------------------------
MTSL_AUTHORITY_STAGE = 2

SEMANTIC_SALIENCE_AMBIGUITY_BOOST = 0.25   # raise when two plausible organizations compete
SEMANTIC_SALIENCE_NOVELTY_BOOST = 0.15     # raise when this SV was freshly created this turn
MAX_SEMANTIC_SALIENCE_RAISE = 0.35         # hard bound: this mechanism may never contribute more


@dataclass(frozen=True)
class TopologyContext:
    """Compact, CERS-facing summary of a coordinator snapshot (spec 12).
    Plain primitive fields only -- this module never imports
    topological_semantic_coordinator.py (that would invert the natural
    producer/consumer direction and risk a cycle); callers build this from
    whatever CoordinatorSnapshot they have in hand."""

    schema_version: int
    turn_id: str
    manifold_slot_id: Optional[str]
    variant_confidence: float          # 0..1; 0.0 when no variant matched
    variant_status: Optional[str]      # provisional/reinforced/promoted/merged/retired/None
    variant_created: bool              # True if this turn's SV match created a brand-new variant
    semantic_ambiguity: bool           # understanding_classification == "ambiguous_organization"
    circulation_fraction: float        # dominant-scale TopologySignature's own field
    regime: str                        # dominant-scale TopologySignature's own field

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "turn_id": self.turn_id,
            "manifold_slot_id": self.manifold_slot_id,
            "variant_confidence": round(self.variant_confidence, 4),
            "variant_status": self.variant_status,
            "variant_created": self.variant_created,
            "semantic_ambiguity": self.semantic_ambiguity,
            "circulation_fraction": round(self.circulation_fraction, 4),
            "regime": self.regime,
        }


def _semantic_salience_raise(topology_context: TopologyContext) -> float:
    """Never negative, never exceeds MAX_SEMANTIC_SALIENCE_RAISE -- this
    mechanism can only ever ADD a bounded signal on top of whatever CERS's
    own geometry-based salience already is, never suppress it."""
    raise_amount = 0.0
    if topology_context.semantic_ambiguity:
        raise_amount += SEMANTIC_SALIENCE_AMBIGUITY_BOOST
    if topology_context.variant_created:
        raise_amount += SEMANTIC_SALIENCE_NOVELTY_BOOST
    return round(min(MAX_SEMANTIC_SALIENCE_RAISE, raise_amount), 4)


def _semantic_mode(topology_context: TopologyContext) -> str:
    """Descriptive label only -- carries no authority, not stage-gated.
    Doesn't decide anything; a future Phase 5 SemanticIntentionBridge is
    what would eventually consume this to select a response strategy."""
    if topology_context.semantic_ambiguity:
        return "ambiguous"
    if topology_context.variant_status is None:
        return "undetermined"
    if topology_context.regime == "circulating":
        return "organized"
    if topology_context.regime in ("gradient", "mixed"):
        return "directional"
    return "undetermined"


def _response_bias(topology_context: TopologyContext) -> float:
    """0..1 "clarification pressure" signal -- higher means a future
    consumer might lean toward checking/clarifying rather than asserting.
    Purely informational: does not affect permitted/conflicts/hesitation
    and is not stage-gated (it never raises anything CERS itself decides)."""
    if topology_context.semantic_ambiguity:
        return 0.7
    return round(clip01((1.0 - topology_context.variant_confidence) * 0.3), 4)


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


@dataclass(frozen=True)
class GeometryDeviation:
    """A tensor-trace-informed signal, distinct from CrestConflict: not two
    clusters fighting -- one specific pressure coordinate that has real,
    established precedent (a crystal already exists there) whose current
    reading diverges sharply from its own history. detect_conflicts() can
    never catch this on its own since it only compares live cluster shares
    against each other, with no memory of what's normal AT this exact
    location. coord_id is the manifold SlotCoord's slot_id, passed as a
    plain string so this module stays decoupled from
    aurora_constraint_manifold_router/cers_tensor_locator -- same pattern
    prediction_field.py already uses for manifold_axis/manifold_familiarity."""

    coord_id: str
    axis: str
    distortion: float
    severity: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coord_id": self.coord_id,
            "axis": self.axis,
            "distortion": round(self.distortion, 4),
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
    geometry_deviation: Optional[GeometryDeviation] = None
    intervention_label: Optional[str] = None
    legacy_label: Optional[str] = None
    cers_label: Optional[str] = None
    agrees_with_legacy: Optional[bool] = None

    # MTSL Phase 4: absent topology_context, ALL six of these stay at their
    # dataclass defaults below -- cers_converge()'s existing decision logic
    # (everything above this comment) never even looks at them, so passing
    # no context is byte-identical to pre-Phase-4 behavior on every other
    # field. semantic_salience/semantic_hesitation are the stage-gated,
    # APPLIED (raise-only) values the surface's compressed dict should read;
    # the _proposed variants are always computed (when context is given)
    # regardless of stage, for the evidence future stage-advancement
    # decisions get cited against -- they are never surface-facing.
    semantic_salience: float = 0.0
    semantic_hesitation: bool = False
    semantic_salience_proposed: float = 0.0
    semantic_hesitation_proposed: bool = False
    semantic_mode: Optional[str] = None
    response_bias: float = 0.0
    variant_confidence: float = 0.0    # carried through verbatim from TopologyContext, never raised/gated

    def to_dict(self) -> Dict[str, Any]:
        return {
            "permitted": bool(self.permitted),
            "conflicts": [c.to_dict() for c in self.conflicts],
            "unused_potential": list(self.unused_potential),
            "actively_trialing_potential": list(self.actively_trialing_potential),
            "confirmed_potential_benefits": dict(self.confirmed_potential_benefits),
            "confirmed_inert_potential": list(self.confirmed_inert_potential),
            "geometry_deviation": self.geometry_deviation.to_dict() if self.geometry_deviation else None,
            "intervention_label": self.intervention_label,
            "legacy_label": self.legacy_label,
            "cers_label": self.cers_label,
            "agrees_with_legacy": self.agrees_with_legacy,
            "semantic_salience": round(self.semantic_salience, 4),
            "semantic_hesitation": bool(self.semantic_hesitation),
            "semantic_salience_proposed": round(self.semantic_salience_proposed, 4),
            "semantic_hesitation_proposed": bool(self.semantic_hesitation_proposed),
            "semantic_mode": self.semantic_mode,
            "response_bias": round(self.response_bias, 4),
            "variant_confidence": round(self.variant_confidence, 4),
        }

    def surface_compressed_dict(self) -> Dict[str, Any]:
        """The ONLY MTSL-facing values the surface may read (directive
        section 7): semantic_salience, semantic_hesitation, variant_confidence,
        semantic_mode, response_bias. Deliberately excludes the _proposed
        audit fields and everything else this verdict carries -- same
        "compressed, not full explanation" discipline _read_cers_salience()
        already applies to cers_salience/cers_hesitation."""
        return {
            "semantic_salience": round(self.semantic_salience, 4),
            "semantic_hesitation": bool(self.semantic_hesitation),
            "variant_confidence": round(self.variant_confidence, 4),
            "semantic_mode": self.semantic_mode,
            "response_bias": round(self.response_bias, 4),
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


def _apply_topology_context(
    cers_crest: Crest,
    verdict: CERSVerdict,
    topology_context: Optional[TopologyContext],
    authority_stage: int,
) -> Tuple[Crest, CERSVerdict]:
    """The ONE place topology_context ever touches a verdict. Absent
    context, returns (cers_crest, verdict) completely unchanged -- the
    identity path that makes cers_converge()'s pre-Phase-4 behavior
    byte-identical when no context is supplied. The crest itself is never
    modified either way; only new CERSVerdict fields are populated."""
    if topology_context is None:
        return cers_crest, verdict
    proposed_salience = _semantic_salience_raise(topology_context)
    proposed_hesitation = (not verdict.permitted) or bool(topology_context.semantic_ambiguity)
    mode = _semantic_mode(topology_context)
    bias = _response_bias(topology_context)
    applied_salience = proposed_salience if authority_stage >= 2 else 0.0
    applied_hesitation = proposed_hesitation if authority_stage >= 2 else False
    augmented = replace(
        verdict,
        semantic_salience=applied_salience,
        semantic_hesitation=applied_hesitation,
        semantic_salience_proposed=proposed_salience,
        semantic_hesitation_proposed=proposed_hesitation,
        semantic_mode=mode,
        response_bias=bias,
        variant_confidence=topology_context.variant_confidence,
    )
    return cers_crest, augmented


def cers_converge(
    sub_crests: Tuple[Crest, ...],
    tracker: PotentialTracker,
    trial_board: Optional["PotentialTrialBoard"] = None,
    *,
    geometry_coord_id: Optional[str] = None,
    geometry_axis: str = "X",
    geometry_distortion_normalized: float = 0.0,
    geometry_is_new: bool = True,
    topology_context: Optional[TopologyContext] = None,
    authority_stage: int = MTSL_AUTHORITY_STAGE,
) -> Tuple[Crest, CERSVerdict]:
    """ERS-native convergence. Runs the legacy convergence alongside for
    equivalence bookkeeping, but only defers to it when no structural
    conflict is present. Never mutates or calls into subsurface_state.py's
    private detail — this stays entirely at the crest layer.

    topology_context (MTSL Phase 4): optional. Applied strictly as a
    post-hoc step AFTER cers_crest/verdict are otherwise fully decided by
    the exact same logic as before Phase 4 -- absent topology_context (the
    default), this function's behavior on every pre-Phase-4 field is
    byte-identical to before. When present, it may only RAISE
    semantic_salience/semantic_hesitation within configured bounds (see
    _semantic_salience_raise's MAX_SEMANTIC_SALIENCE_RAISE cap, and
    semantic_hesitation is combined with the already-decided `permitted`
    via boolean OR, which can only turn hesitation on, never off).
    authority_stage: directive section 7's manual staging gate (1..6,
    default 1 = "record only"). At stage 1 the proposed raise is always
    computed (verdict.semantic_salience_proposed/semantic_hesitation_proposed)
    for future evidence-based staging decisions, but NOT applied to the
    surface-facing semantic_salience/semantic_hesitation fields, which stay
    at their inert defaults. Applied only at stage 2+.

    trial_board: when provided, every channel PotentialTracker flags as
    dormant this tick gets an active correlation trial opened against it
    (see cers_potential_trial.py) rather than being reported as a static
    fact. Resolved trials (promoted or dissolved) stop appearing in
    unused_potential/actively_trialing_potential going forward.

    geometry_*: read-only tensor-trace context (cers_tensor_locator.py's
    measure_distortion, called BEFORE this tick's own visit is recorded --
    see cers_bridge.py). Plain values only (coord_id as a string, not a
    SlotCoord), same decoupling pattern prediction_field.py already uses.
    detect_conflicts() only ever compares live cluster shares against each
    other; it has no memory of what's normal at any specific pressure
    coordinate. This is what lets CERS's OWN verdict -- not just its
    downstream trace-recording -- catch "this exact geometry has real
    precedent and just broke sharply," even when nothing looks like a
    classic opposed-cluster conflict this tick."""
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

    geometry_deviation: Optional[GeometryDeviation] = None
    if (
        geometry_coord_id
        and not geometry_is_new
        and geometry_distortion_normalized >= GEOMETRY_DEVIATION_THRESHOLD
    ):
        geometry_deviation = GeometryDeviation(
            coord_id=geometry_coord_id,
            axis=geometry_axis,
            distortion=geometry_distortion_normalized,
            severity=round(geometry_distortion_normalized, 4),
        )

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
            geometry_deviation=geometry_deviation,
            intervention_label=cers_crest.label,
            legacy_label=legacy_crest.label,
            cers_label=cers_crest.label,
            agrees_with_legacy=False,
        )
        return _apply_topology_context(cers_crest, verdict, topology_context, authority_stage)

    if geometry_deviation is not None:
        # No classic cluster-vs-cluster conflict this tick, but a
        # coordinate with real precedent just diverged sharply from its
        # own history -- a genuine event detect_conflicts() structurally
        # cannot see, since it only ever compares clusters to each other.
        cers_crest = Crest(
            label="pattern_deviation",
            intensity=geometry_deviation.severity,
            axis=geometry_deviation.axis,
        )
        verdict = CERSVerdict(
            permitted=False,
            conflicts=[],
            unused_potential=unused,
            actively_trialing_potential=actively_trialing,
            confirmed_potential_benefits=confirmed_benefits,
            confirmed_inert_potential=confirmed_inert,
            geometry_deviation=geometry_deviation,
            intervention_label=cers_crest.label,
            legacy_label=legacy_crest.label,
            cers_label=cers_crest.label,
            agrees_with_legacy=False,
        )
        return _apply_topology_context(cers_crest, verdict, topology_context, authority_stage)

    verdict = CERSVerdict(
        permitted=True,
        conflicts=[],
        unused_potential=unused,
        actively_trialing_potential=actively_trialing,
        confirmed_potential_benefits=confirmed_benefits,
        confirmed_inert_potential=confirmed_inert,
        geometry_deviation=None,
        intervention_label=None,
        legacy_label=legacy_crest.label,
        cers_label=legacy_crest.label,
        agrees_with_legacy=True,
    )
    return _apply_topology_context(legacy_crest, verdict, topology_context, authority_stage)
