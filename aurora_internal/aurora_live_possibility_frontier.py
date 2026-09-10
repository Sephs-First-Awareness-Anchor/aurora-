# Authors: Sunni (Sir) Morningstar & Ceph
"""Live possibility-continuation arbitration for Aurora.

Aurora's possibility architecture already exposes more than one prospective
continuation through the Subsurface predictive stager. This module does not
invent a second reasoning system. It connects those existing projections to
ThoughtBraid, ActiveSelfState, ThoughtIntegrationSpace, representational
perspective, and Layer-7 inception simulation so one live occurrence may
support several *uncommitted* thoughts before Agency actualizes exactly one.

Semantic contract
-----------------

    one braid/self snapshot
        -> relevant predictive continuations
        -> independent ThoughtIntegrationSpace resolutions
        -> lawful perspective view when a real RepresentationalRef is present
        -> Pareto elimination by self + situation + coherence + continuity
        -> inception self-projection only while competition remains
        -> King identity-topology arbitration while competition remains
        -> Agency actualizes one non-dominated continuation

No continuation in this module is lived state. The caller owns the actuality
boundary by applying ThoughtContinuity.carry_forward() only to the selected
ThoughtState. Rejected continuations are reduced to diagnostic summaries and
never enter SediMemory or continuity.

A representational projection is likewise not lived knowledge. Candidate
branches may look through an already-staged Build 714 perspective only when a
real encoded RepresentationalRef is already carried by their braid/predictive
evidence. The branch never fabricates a ref and never promotes a field. If the
projected view changes downstream thought, that causal difference is reported
to the existing resolution engine and awaits real consequence evidence.

The King Quasicrystal is not treated as a second scoring intelligence. Its
existing live identity field is snapshotted once per occurrence and receives
final authority only after situational evidence and deeper self-projection have
failed to distinguish the remaining continuations. The comparison uses the
field's own current-vs-reference pressure topology, matching the native identity
semantics already used by Habitat motivation. If the King itself cannot
distinguish the survivors, the final choice is explicitly neutral and is not
recorded as an identity preference.

The module is scheduler-neutral. Branches execute serially on today's Python
phone runtime; because they share frozen inputs and do not commit live state,
the same branch set can later be widened by an ACM executor without changing
which information each branch was allowed to observe.
"""
from __future__ import annotations

import copy
import hashlib
import json
import random
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


_AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")
_BASE_METRICS: Tuple[str, ...] = (
    "self_fit",
    "situational_fit",
    "coherence",
    "closure",
    "continuity",
    "predictive_support",
)
_SIM_METRICS: Tuple[str, ...] = _BASE_METRICS + ("simulation_coherence",)
_EPS = 1e-9

_AXIS_NAMES = {
    "X": ("X", "existence"),
    "T": ("T", "temporal", "time"),
    "N": ("N", "energy", "change"),
    "B": ("B", "boundary", "containment"),
    "A": ("A", "agency"),
}
_I_STATE_BY_AXIS = {
    "X": ("i_is", "i_isnt"),
    "T": ("i_can", "i_cannot"),
    "N": ("i_do", "i_donot"),
    "B": ("i_saw", "i_sought"),
    "A": ("i_did", "i_didnt"),
}


@dataclass
class PossibilityContinuation:
    candidate_id: str
    source: str
    predictive_frame: Dict[str, Any]
    pressure_perspective: Tuple[str, ...]
    thought_state: Any
    braid_slice: Any
    evidence: Dict[str, float] = field(default_factory=dict)
    simulation: Dict[str, Any] = field(default_factory=dict)
    projection_views: List[Dict[str, Any]] = field(default_factory=list)
    selected: bool = False

    def summary(self) -> Dict[str, Any]:
        thought = self.thought_state
        return {
            "candidate_id": self.candidate_id,
            "source": self.source,
            "pressure_perspective": list(self.pressure_perspective),
            "predictive_frame": _public_frame(self.predictive_frame),
            "thought": thought.to_dict() if hasattr(thought, "to_dict") else {},
            "evidence": {k: round(float(v), 4) for k, v in self.evidence.items()},
            "simulation": dict(self.simulation),
            "projection_views": [dict(view) for view in self.projection_views],
            "selected": bool(self.selected),
        }


@dataclass
class PossibilityResolution:
    selected: PossibilityContinuation
    candidates: List[PossibilityContinuation]
    arbitration: Dict[str, Any]

    @property
    def thought_state(self) -> Any:
        return self.selected.thought_state

    @property
    def braid_slice(self) -> Any:
        return self.selected.braid_slice


def _clip01(value: Any, default: float = 0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except Exception:
        return max(0.0, min(1.0, float(default)))


def _tokens(value: Any) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9']+", str(value or "").lower())
        if len(token) > 2
    }


def _frame_axis(frame: Dict[str, Any]) -> str:
    raw = str(frame.get("dominant_axis_hint") or frame.get("dominant_field") or "").upper()
    if raw in _AXES:
        return raw
    for axis, aliases in _AXIS_NAMES.items():
        if raw.lower() in {alias.lower() for alias in aliases}:
            return axis
    perspective = tuple(str(v).upper() for v in (frame.get("pressure_perspective") or ()))
    return next((axis for axis in perspective if axis in _AXES), "X")


def _frame_polarity(frame: Dict[str, Any], axis: str) -> Optional[float]:
    polarities = dict(frame.get("axis_polarities") or frame.get("original_axis_polarities") or {})
    for key in _AXIS_NAMES.get(axis, (axis,)):
        if key in polarities:
            try:
                return max(-1.0, min(1.0, float(polarities[key])))
            except Exception:
                return None
    for key, value in polarities.items():
        if str(key).upper() == axis:
            try:
                return max(-1.0, min(1.0, float(value)))
            except Exception:
                return None
    return None


def _frame_topic(frame: Dict[str, Any]) -> str:
    wm = dict(frame.get("working_memory") or {})
    conscious = dict(frame.get("conscious_frame") or {})
    for value in (
        frame.get("curiosity_lean"),
        wm.get("dominant_theme"),
        conscious.get("focus_domain"),
        frame.get("topic_concept"),
    ):
        if value:
            return str(value)[:120]
    for projection in frame.get("slot_projections") or ():
        if isinstance(projection, dict) and projection.get("token"):
            return str(projection["token"])[:120]
    return ""


def _predictive_support(frame: Dict[str, Any]) -> float:
    direct = frame.get("perspective_confidence", frame.get("confidence"))
    if direct is not None:
        return _clip01(direct, 0.5)
    slot_conf = [
        _clip01(item.get("confidence"), 0.0)
        for item in (frame.get("slot_projections") or ())
        if isinstance(item, dict)
    ]
    return max(slot_conf, default=0.5)


def _public_frame(frame: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": frame.get("source"),
        "pressure_perspective": list(frame.get("pressure_perspective") or ()),
        "dominant_axis_hint": _frame_axis(frame),
        "topic": _frame_topic(frame),
        "perspective_confidence": round(_predictive_support(frame), 4),
    }


def _normalize_staged_frame(frame: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(dict(frame or {}))
    axis = _frame_axis(out)
    topic = _frame_topic(out)
    out.setdefault("dominant_axis_hint", axis)
    out.setdefault("dominant_field", axis)
    if topic:
        out.setdefault("curiosity_lean", topic)
    out.setdefault("confidence", _predictive_support(out))
    return out


def _frame_identity(source: str, frame: Dict[str, Any]) -> str:
    # Source is intentionally excluded. The same possibility arriving once via
    # the live braid and once via the file-backed Subsurface queue is one
    # continuation, not two votes for the same continuation.
    payload = {
        "perspective": list(frame.get("pressure_perspective") or ()),
        "axis": _frame_axis(frame),
        "topic": _frame_topic(frame),
        "slots": [
            (item.get("token"), tuple(item.get("roles") or ()), item.get("slot_kind"))
            for item in (frame.get("slot_projections") or ())
            if isinstance(item, dict)
        ],
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "pcand_" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _candidate_frames(
    systems: Dict[str, Any],
    self_state: Any,
    braid_slice: Any,
) -> List[Tuple[str, Dict[str, Any]]]:
    """Harvest and dedupe the possibility frontier already staged by Subsurface."""
    staged: List[Dict[str, Any]] = []
    try:
        from aurora_internal.dual_strata.predictive_stager import (
            PredictiveStager,
            n_passes_for_density,
        )

        # A new live occurrence must not inherit an earlier turn's systems-side
        # cache if the file-backed queue has no new frames.
        systems["_staged_subsurface_frames"] = []
        systems["_staged_subsurface_frame"] = None
        harvested = PredictiveStager.harvest_into_systems(systems, max_frames=8)
        if harvested:
            staged = [
                dict(frame) for frame in (systems.get("_staged_subsurface_frames") or ())
                if isinstance(frame, dict)
            ]

        hinted_axis = _frame_axis(staged[0]) if staged else ""
        if not hinted_axis:
            pressure = dict(getattr(self_state, "pressure_vec", {}) or {})
            hinted_axis = max(_AXES, key=lambda axis: float(pressure.get(axis, 0.0))) if pressure else "X"
        branch_limit = max(1, min(5, int(n_passes_for_density(hinted_axis))))
    except Exception:
        staged = []
        branch_limit = 1

    raw: List[Tuple[str, Dict[str, Any]]] = []
    # Keep the present braid frame byte-for-semantic-byte equivalent. In the
    # one-candidate case this branch must reproduce the historic integration
    # path, not gain a synthetic pressure label merely because the frontier is
    # installed.
    present = copy.deepcopy(
        dict(getattr(braid_slice, "predictive_frame", {}) or {})
        if braid_slice is not None else {}
    )
    raw.append(("braid_present", present))
    raw.extend(
        ("subsurface_pressure_perspective", _normalize_staged_frame(frame))
        for frame in staged
    )

    unique: Dict[str, Tuple[str, Dict[str, Any]]] = {}
    for source, frame in raw:
        cid = _frame_identity(source, frame)
        if cid not in unique:
            unique[cid] = (source, frame)
    return list(unique.values())[:branch_limit]


def _clone_slice(base_slice: Any, predictive_frame: Dict[str, Any]) -> Any:
    if base_slice is None:
        from aurora_thought_formation import ThoughtStreamSlice
        cloned = ThoughtStreamSlice()
    else:
        cloned = copy.deepcopy(base_slice)
    cloned.predictive_frame = copy.deepcopy(predictive_frame)
    return cloned


def _register_candidate_context(
    space: Any,
    frame: Dict[str, Any],
    candidate_id: str,
    tick: int,
    source: str,
) -> None:
    # The braid-present candidate is the exact pre-frontier path. Its existing
    # ThoughtStreamSlice predictive context is sufficient, and adding another
    # candidate context would bias ordinary one-path turns.
    if source == "braid_present":
        return

    from aurora_thought_formation import make_process_context

    perspective = [
        str(v).upper() for v in (frame.get("pressure_perspective") or ())
        if str(v).upper() in _AXES
    ]
    if not perspective:
        perspective = [_frame_axis(frame), "A"]
    topic = _frame_topic(frame) or f"{_frame_axis(frame)} continuation"
    confidence = _predictive_support(frame)
    ctx = make_process_context(
        process_id=f"possibility_{candidate_id}_{tick}",
        process_type="predictive",
        what_triggered_it="subsurface_possibility_frontier",
        what_it_is_operating_on=topic,
        self_relevance=0.35 + 0.30 * confidence,
        axis_signature=list(dict.fromkeys(perspective)),
        tick=tick,
        unresolved_tension_weight=1.0 - confidence,
    )
    space.register(ctx)


def _extract_representational_refs(*values: Any) -> List[str]:
    """Collect only explicitly-carried encoded refs; never infer or fabricate one."""
    found: List[str] = []
    seen: set[str] = set()
    stack: List[Any] = list(values)
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            for key, child in value.items():
                if str(key) == "representational_ref":
                    encoded = str(child or "")
                    if encoded.startswith("REF:") and encoded not in seen:
                        seen.add(encoded)
                        found.append(encoded)
                elif isinstance(child, (dict, list, tuple, set)):
                    stack.append(child)
        elif isinstance(value, (list, tuple, set)):
            stack.extend(value)
    return found


def _projection_contexts_for_candidate(
    systems: Dict[str, Any],
    branch_slice: Any,
    predictive_frame: Dict[str, Any],
    turn_contexts: Sequence[Any],
    candidate_id: str,
    turn_tick: int,
) -> Tuple[List[Any], List[Dict[str, Any]]]:
    """Expose active lawful projection views already supported by real refs."""
    try:
        from aurora_representational_resolution import consume_projection_for_ref
        from aurora_thought_formation import make_process_context
    except Exception:
        return [], []

    context_states = [
        getattr(ctx, "current_output_state", None)
        for ctx in (turn_contexts or ())
    ]
    refs = _extract_representational_refs(
        predictive_frame,
        getattr(branch_slice, "memory_signal", None),
        getattr(branch_slice, "sensory_signal", None),
        systems.get("_braid_sedi_recall"),
        context_states,
    )
    contexts: List[Any] = []
    views: List[Dict[str, Any]] = []
    for index, encoded in enumerate(refs):
        view = consume_projection_for_ref(
            systems,
            encoded,
            consumer="live_possibility_frontier",
            context_scope=f"turn:{int(turn_tick)}:candidate:{candidate_id}",
        )
        if not isinstance(view, dict) or not view.get("projected_ref"):
            continue
        axes = [
            str(axis).upper() for axis in (view.get("pressure_perspective") or ())
            if str(axis).upper() in _AXES
        ]
        exposed = dict(view.get("exposed_fields") or {})
        if not exposed:
            continue
        compact = ", ".join(f"{key}={value}" for key, value in sorted(exposed.items()))
        ctx = make_process_context(
            process_id=f"possibility_projection_{candidate_id}_{index}_{turn_tick}",
            process_type="predictive",
            what_triggered_it="perspective_before_resolution",
            what_it_is_operating_on=f"projected distinction: {compact}"[:200],
            current_output_state=dict(view),
            self_relevance=0.50,
            axis_signature=axes or [_frame_axis(predictive_frame)],
            tick=turn_tick,
            unresolved_tension_weight=0.20,
        )
        contexts.append(ctx)
        views.append(dict(view))
    return contexts, views


def _prepare_integration_space(
    self_state: Any,
    branch_slice: Any,
    continuity: Any,
    turn_contexts: Sequence[Any],
    constraint_context: Any,
    predictive_frame: Dict[str, Any],
    candidate_id: str,
    turn_tick: int,
    source: str,
    extra_contexts: Sequence[Any] = (),
) -> Any:
    from aurora_thought_formation import ThoughtIntegrationSpace

    space = ThoughtIntegrationSpace(self_state, braid_slice=branch_slice)
    if continuity is not None and hasattr(continuity, "prime_integration_space"):
        continuity.prime_integration_space(space)
    for ctx in copy.deepcopy(list(turn_contexts or ())):
        space.register(ctx)
    if constraint_context is not None:
        space.register(copy.deepcopy(constraint_context))
    _register_candidate_context(
        space, predictive_frame, candidate_id, turn_tick, source,
    )
    for ctx in copy.deepcopy(list(extra_contexts or ())):
        space.register(ctx)
    return space


def _thought_difference(before: Any, after: Any) -> Dict[str, Any]:
    """Describe only material internal change caused by a projected view."""
    difference: Dict[str, Any] = {}
    before_interp = str(getattr(before, "unified_interpretation", "") or "")
    after_interp = str(getattr(after, "unified_interpretation", "") or "")
    if before_interp != after_interp:
        difference["interpretation_changed"] = True
    before_self = str(getattr(before, "self_application", "") or "")
    after_self = str(getattr(after, "self_application", "") or "")
    if before_self != after_self:
        difference["self_application_changed"] = True
    before_axes = tuple(getattr(before, "axis_fingerprint", []) or [])
    after_axes = tuple(getattr(after, "axis_fingerprint", []) or [])
    if before_axes != after_axes:
        difference["axis_fingerprint_changed"] = {"before": list(before_axes), "after": list(after_axes)}
    before_conflicts = len(getattr(before, "conflicts", []) or [])
    after_conflicts = len(getattr(after, "conflicts", []) or [])
    if before_conflicts != after_conflicts:
        difference["conflict_count_changed"] = {"before": before_conflicts, "after": after_conflicts}
    before_unresolved = len(getattr(before, "unresolved", []) or [])
    after_unresolved = len(getattr(after, "unresolved", []) or [])
    if before_unresolved != after_unresolved:
        difference["unresolved_count_changed"] = {"before": before_unresolved, "after": after_unresolved}
    try:
        before_conf = float(getattr(before, "confidence", 0.0) or 0.0)
        after_conf = float(getattr(after, "confidence", 0.0) or 0.0)
        if abs(before_conf - after_conf) > _EPS:
            difference["confidence_changed"] = {"before": before_conf, "after": after_conf}
    except Exception:
        pass
    return difference


def _record_projection_thought_difference(
    systems: Dict[str, Any],
    views: Sequence[Dict[str, Any]],
    difference: Dict[str, Any],
    candidate_id: str,
) -> None:
    if not difference:
        return
    try:
        from aurora_representational_address import RepresentationalRef
        from aurora_representational_resolution import get_or_create_engine
        engine = get_or_create_engine(systems)
    except Exception:
        return
    if engine is None:
        return
    for view in views:
        try:
            ref = RepresentationalRef.decode(str(view.get("base_ref") or ""))
            engine.record_candidate_downstream_effect(
                ref,
                consumer="live_possibility_frontier",
                downstream_difference=dict(difference),
                action_or_prediction_affected="candidate_thought_integration",
                baseline_expectation={"candidate_id": candidate_id, "projection": False},
                conditioned_expectation={"candidate_id": candidate_id, "projection": True},
                metadata={"projection_id": view.get("projection_id")},
            )
        except Exception:
            continue


def _axis_overlap(left: Iterable[str], right: Iterable[str]) -> float:
    a, b = set(left or ()), set(right or ())
    if not a or not b:
        return 0.5
    return len(a & b) / max(1, len(a | b))


def _evidence_for(
    thought: Any,
    frame: Dict[str, Any],
    self_state: Any,
    user_text: str,
    prior_thought: Any,
) -> Dict[str, float]:
    dominant = list(getattr(thought, "dominant_thread", []) or [])
    self_fit = (
        sum(_clip01(getattr(ctx, "self_relevance", 0.0)) for ctx in dominant) / len(dominant)
        if dominant else 0.5
    )
    topic_tokens = _tokens(_frame_topic(frame))
    user_tokens = _tokens(user_text)
    situational_fit = (
        len(topic_tokens & user_tokens) / max(1, len(topic_tokens | user_tokens))
        if topic_tokens and user_tokens else 0.5
    )
    conflicts = len(getattr(thought, "conflicts", []) or [])
    unresolved = len(getattr(thought, "unresolved", []) or [])
    closure = 1.0 / (1.0 + conflicts + unresolved)
    prior_axes = (
        getattr(prior_thought, "axis_fingerprint", []) or []
        if prior_thought is not None else []
    )
    continuity = _axis_overlap(
        getattr(thought, "axis_fingerprint", []) or [],
        prior_axes,
    )
    return {
        "self_fit": _clip01(self_fit, 0.5),
        "situational_fit": _clip01(situational_fit, 0.5),
        "coherence": _clip01(getattr(thought, "confidence", 0.0), 0.0),
        "closure": _clip01(closure, 0.5),
        "continuity": _clip01(continuity, 0.5),
        "predictive_support": _predictive_support(frame),
    }


def _dominates(
    left: PossibilityContinuation,
    right: PossibilityContinuation,
    metrics: Sequence[str],
) -> bool:
    lvals = [float(left.evidence.get(metric, 0.5)) for metric in metrics]
    rvals = [float(right.evidence.get(metric, 0.5)) for metric in metrics]
    return (
        all(l + _EPS >= r for l, r in zip(lvals, rvals))
        and any(l > r + _EPS for l, r in zip(lvals, rvals))
    )


def _pareto_frontier(
    candidates: Sequence[PossibilityContinuation],
    metrics: Sequence[str],
) -> List[PossibilityContinuation]:
    return [
        candidate for candidate in candidates
        if not any(
            other is not candidate and _dominates(other, candidate, metrics)
            for other in candidates
        )
    ]


def _simulate_candidate(candidate: PossibilityContinuation, self_state: Any) -> Dict[str, Any]:
    """Run an ephemeral Layer-7 inception self-projection with no live registration."""
    # ImpressionCascade's ID helper consumes Python's module-global RNG. A
    # rejected hypothetical must not advance the stochastic stream later lived
    # execution will see, so the entire projection happens inside an RNG
    # snapshot/restore boundary.
    rng_state = random.getstate()
    try:
        from aurora_simulation_engine import InceptionEntity
        from foundational_contract import ExistenceMode

        axis = _frame_axis(candidate.predictive_frame)
        polarity = _frame_polarity(candidate.predictive_frame, axis)
        if polarity is None:
            polarity = 0.0
        positive, negative = _I_STATE_BY_AXIS.get(axis, _I_STATE_BY_AXIS["X"])
        i_state = positive if polarity >= 0.0 else negative

        entity = InceptionEntity(
            entity_id=f"live_possibility::{candidate.candidate_id}",
            i_state=i_state,
        )
        closure = candidate.evidence.get("closure", 0.5)
        self_fit = candidate.evidence.get("self_fit", 0.5)
        predictive = candidate.evidence.get("predictive_support", 0.5)
        channels = {
            "anticipation": _clip01(predictive),
            "determination": _clip01(self_fit),
            "curiosity": _clip01(1.0 - predictive),
            "confusion": _clip01(1.0 - closure),
            "neutral": 0.2,
        }
        projected = entity.process_experience(
            {"channels": channels, "tone": "neutral"},
            mode=ExistenceMode.BOUNDED,
        )
        collapsed = entity.collapse_to_parent()
        valence = max(
            -1.0,
            min(1.0, float(projected.get("valence", 0.0) or 0.0)),
        )
        # Simulation contributes as internal consistency, never as a
        # happiness/reward objective. A branch whose simulated inner response
        # contradicts its own predicted polarity is less self-coherent.
        simulation_coherence = 1.0 - min(1.0, abs(valence - polarity) / 2.0)
        return {
            "mode": "ephemeral_inception",
            "i_state": i_state,
            "axis": axis,
            "expected_polarity": round(polarity, 4),
            "valence": round(valence, 4),
            "intensity": round(float(projected.get("intensity", 0.0) or 0.0), 4),
            "simulation_coherence": round(_clip01(simulation_coherence, 0.5), 4),
            "experience_count": int(collapsed.get("experience_count", 1) or 1),
        }
    except Exception as exc:
        return {
            "mode": "unavailable",
            "reason": type(exc).__name__,
            "simulation_coherence": 0.5,
        }
    finally:
        random.setstate(rng_state)


def _king_identity_snapshot(systems: Dict[str, Any]) -> Dict[str, Any]:
    """Freeze the King Quasicrystal's live identity topology for this occurrence.

    NoncompField already exposes current axis pressure and its own neutral
    reference. Mirroring Habitat motivation, only positive displacement above
    that native reference counts as active identity pressure. This function is
    read-only: it never ingests, decays, resets, or otherwise changes the King.
    """
    identity_field = systems.get("identity_field")
    if identity_field is None or not hasattr(identity_field, "status"):
        return {"available": False, "reason": "identity_field_unavailable"}
    try:
        status = identity_field.status() or {}
    except Exception as exc:
        return {
            "available": False,
            "reason": f"identity_field_status_{type(exc).__name__}",
        }
    if not isinstance(status, dict):
        return {"available": False, "reason": "identity_field_status_invalid"}

    raw_current = dict(status.get("axis_pressures") or {})
    raw_reference = dict(status.get("reference_axis_pressures") or {})
    if not raw_reference and hasattr(identity_field, "reference_axis_pressures"):
        try:
            raw_reference = dict(identity_field.reference_axis_pressures() or {})
        except Exception:
            raw_reference = {}

    current = {
        axis: float(raw_current[axis])
        for axis in _AXES
        if axis in raw_current
    }
    reference = {
        axis: float(raw_reference[axis])
        for axis in _AXES
        if axis in raw_reference
    }
    elevation = {
        axis: max(0.0, current.get(axis, 0.0) - reference.get(axis, current.get(axis, 0.0)))
        for axis in _AXES
        if axis in current and axis in reference
    }
    magnitude = sum(value * value for value in elevation.values()) ** 0.5
    topology = {
        axis: (value / magnitude if magnitude > _EPS else 0.0)
        for axis, value in elevation.items()
    }
    dimensions = {
        str(key): float(value)
        for key, value in dict(status.get("dimension_pressures") or {}).items()
        if isinstance(value, (int, float))
    }
    return {
        "available": bool(magnitude > _EPS),
        "reason": "active_identity_topology" if magnitude > _EPS else "identity_at_reference",
        "axis_pressures": current,
        "reference_axis_pressures": reference,
        "axis_elevation": elevation,
        "normalized_topology": topology,
        "dimension_pressures": dimensions,
    }


def _public_king_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Compact observability record for the frozen King state."""
    return {
        "available": bool(snapshot.get("available")),
        "reason": snapshot.get("reason"),
        "axis_elevation": {
            axis: round(float(value), 6)
            for axis, value in dict(snapshot.get("axis_elevation") or {}).items()
        },
        "normalized_topology": {
            axis: round(float(value), 6)
            for axis, value in dict(snapshot.get("normalized_topology") or {}).items()
        },
        "dimension_pressures": {
            str(key): round(float(value), 6)
            for key, value in dict(snapshot.get("dimension_pressures") or {}).items()
        },
    }


def _candidate_axis_profile(candidate: PossibilityContinuation) -> Dict[str, float]:
    """Represent which native axes a surviving continuation actually occupies."""
    axes = {
        str(axis).upper()
        for axis in (getattr(candidate.thought_state, "axis_fingerprint", []) or [])
        if str(axis).upper() in _AXES
    }
    axes.update(
        str(axis).upper()
        for axis in (candidate.pressure_perspective or ())
        if str(axis).upper() in _AXES
    )
    raw_axis = str(
        candidate.predictive_frame.get("dominant_axis_hint")
        or candidate.predictive_frame.get("dominant_field")
        or ""
    )
    if raw_axis:
        axis = _frame_axis(candidate.predictive_frame)
        if axis in _AXES:
            axes.add(axis)
    if not axes:
        return {}
    return {axis: (1.0 if axis in axes else 0.0) for axis in _AXES}


def _king_identity_fit(
    candidate: PossibilityContinuation,
    king_snapshot: Dict[str, Any],
) -> Optional[float]:
    """Cosine congruence between a continuation and the frozen King topology.

    Candidate axes are a set, not a weighted personality vector. This avoids
    inventing arbitrary preferences: the only magnitudes come from the King's
    own live field. A candidate simply intersects more or less with what the
    identity field is presently carrying.
    """
    if not king_snapshot.get("available"):
        return None
    topology = dict(king_snapshot.get("normalized_topology") or {})
    profile = _candidate_axis_profile(candidate)
    if not topology or not profile:
        return None
    p_norm = sum(float(value) ** 2 for value in profile.values()) ** 0.5
    k_norm = sum(float(topology.get(axis, 0.0)) ** 2 for axis in _AXES) ** 0.5
    if p_norm <= _EPS or k_norm <= _EPS:
        return None
    dot = sum(float(profile.get(axis, 0.0)) * float(topology.get(axis, 0.0)) for axis in _AXES)
    return _clip01(dot / (p_norm * k_norm), 0.0)


def _king_identity_arbitrate(
    candidates: Sequence[PossibilityContinuation],
    king_snapshot: Dict[str, Any],
) -> Tuple[Optional[PossibilityContinuation], Dict[str, Any]]:
    """Let the King distinguish only futures other evidence could not separate."""
    if not candidates:
        return None, {"authority_used": False, "reason": "no_candidates"}
    if not king_snapshot.get("available"):
        return None, {
            "authority_used": False,
            "reason": str(king_snapshot.get("reason") or "identity_field_unavailable"),
        }

    scored: List[Tuple[PossibilityContinuation, float]] = []
    for candidate in candidates:
        fit = _king_identity_fit(candidate, king_snapshot)
        if fit is None:
            continue
        candidate.evidence["king_identity_fit"] = fit
        scored.append((candidate, fit))
    if not scored:
        return None, {
            "authority_used": False,
            "reason": "no_candidate_identity_surface",
        }

    top_fit = max(fit for _candidate, fit in scored)
    if top_fit <= _EPS:
        return None, {
            "authority_used": True,
            "reason": "no_candidate_identity_intersection",
            "candidate_fits": {
                candidate.candidate_id: round(fit, 6)
                for candidate, fit in scored
            },
        }
    tied = [
        candidate for candidate, fit in scored
        if abs(fit - top_fit) <= _EPS
    ]
    evidence = {
        "authority_used": True,
        "authority": "king_quasicrystal_identity_field",
        "candidate_fits": {
            candidate.candidate_id: round(fit, 6)
            for candidate, fit in scored
        },
        "top_fit": round(top_fit, 6),
        "top_candidate_ids": sorted(candidate.candidate_id for candidate in tied),
    }
    if len(tied) == 1:
        evidence.update({
            "reason": "identity_topology_discriminated",
            "identity_discrimination": True,
        })
        return tied[0], evidence
    evidence.update({
        "reason": "identity_topology_equivalent",
        "identity_discrimination": False,
    })
    return None, evidence


def _neutral_equivalence_choice(
    candidates: Sequence[PossibilityContinuation],
    user_text: str,
    turn_tick: int,
) -> PossibilityContinuation:
    """Resolve true equivalence without manufacturing evidence of preference."""
    ordered = sorted(candidates, key=lambda candidate: candidate.candidate_id)
    payload = {
        "turn": int(turn_tick),
        "text": str(user_text or ""),
        "candidate_ids": [candidate.candidate_id for candidate in ordered],
    }
    digest = hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")
    ).hexdigest()
    return random.Random(int(digest[:16], 16)).choice(ordered)


def _stable_agency_choice(
    candidates: Sequence[PossibilityContinuation],
    self_state: Any,
    user_text: str,
    turn_tick: int,
) -> PossibilityContinuation:
    """Compatibility alias for pre-King tests; this is neutral, not preference."""
    return _neutral_equivalence_choice(candidates, user_text, turn_tick)


def resolve_live_possibilities(
    systems: Dict[str, Any],
    *,
    self_state: Any,
    braid_slice: Any,
    user_text: str,
    turn_tick: int,
    turn_contexts: Sequence[Any],
    continuity: Any,
    constraint_context: Any = None,
) -> Optional[PossibilityResolution]:
    """Resolve several possible thoughts without committing any of them.

    The caller must apply continuity to ``resolution.thought_state`` only after
    this function returns. That call is the actualization boundary.
    """
    prior_thought = systems.get("_current_thought_state")
    # Freeze the King once, before any sibling continuation is evaluated. Every
    # candidate therefore encounters the same identity state regardless of
    # execution order or future ACM parallelization.
    king_snapshot = _king_identity_snapshot(systems)
    frame_specs = _candidate_frames(systems, self_state, braid_slice)
    if not frame_specs:
        return None

    candidates: List[PossibilityContinuation] = []
    for source, predictive_frame in frame_specs:
        candidate_id = _frame_identity(source, predictive_frame)
        branch_slice = _clone_slice(braid_slice, predictive_frame)

        # Coarse baseline first. Perspective is conditional extra work, never a
        # mandatory second integration on every branch.
        baseline_space = _prepare_integration_space(
            self_state,
            branch_slice,
            continuity,
            turn_contexts,
            constraint_context,
            predictive_frame,
            candidate_id,
            turn_tick,
            source,
        )
        baseline_thought = baseline_space.integrate()

        projection_contexts, projection_views = _projection_contexts_for_candidate(
            systems,
            branch_slice,
            predictive_frame,
            turn_contexts,
            candidate_id,
            turn_tick,
        )
        if projection_contexts:
            projected_space = _prepare_integration_space(
                self_state,
                branch_slice,
                continuity,
                turn_contexts,
                constraint_context,
                predictive_frame,
                candidate_id,
                turn_tick,
                source,
                extra_contexts=projection_contexts,
            )
            thought = projected_space.integrate()
            difference = _thought_difference(baseline_thought, thought)
            _record_projection_thought_difference(
                systems, projection_views, difference, candidate_id,
            )
        else:
            thought = baseline_thought

        candidate = PossibilityContinuation(
            candidate_id=candidate_id,
            source=source,
            predictive_frame=predictive_frame,
            pressure_perspective=tuple(
                str(axis).upper()
                for axis in (predictive_frame.get("pressure_perspective") or ())
                if str(axis).upper() in _AXES
            ),
            thought_state=thought,
            braid_slice=branch_slice,
            projection_views=projection_views,
        )
        candidate.evidence.update(
            _evidence_for(
                thought,
                predictive_frame,
                self_state,
                user_text,
                prior_thought,
            )
        )
        candidates.append(candidate)

    survivors = _pareto_frontier(candidates, _BASE_METRICS)
    arbitration: Dict[str, Any] = {
        "candidate_count": len(candidates),
        "initial_non_dominated": [
            candidate.candidate_id for candidate in survivors
        ],
        "deep_simulation_used": False,
        "perspective_projection_used": any(candidate.projection_views for candidate in candidates),
        "projection_view_count": sum(len(candidate.projection_views) for candidate in candidates),
        "king_identity_snapshot": _public_king_snapshot(king_snapshot),
        "king_identity_arbitration": {"authority_used": False, "reason": "not_needed"},
        "rule": "coarse_then_perspective_then_pareto_then_simulation_then_king_identity",
    }

    if len(survivors) == 1:
        selected = survivors[0]
        arbitration["reason"] = "single_non_dominated_continuation"
        arbitration["actualization_authority"] = "existing_evidence"
    else:
        arbitration["deep_simulation_used"] = True
        for candidate in survivors:
            candidate.simulation = _simulate_candidate(candidate, self_state)
            candidate.evidence["simulation_coherence"] = _clip01(
                candidate.simulation.get("simulation_coherence"), 0.5
            )
        simulated_survivors = _pareto_frontier(survivors, _SIM_METRICS)
        arbitration["post_simulation_non_dominated"] = [
            candidate.candidate_id for candidate in simulated_survivors
        ]
        if len(simulated_survivors) == 1:
            selected = simulated_survivors[0]
            arbitration["reason"] = "simulation_disambiguated_continuation"
            arbitration["actualization_authority"] = "self_projection_evidence"
        else:
            king_selected, king_evidence = _king_identity_arbitrate(
                simulated_survivors,
                king_snapshot,
            )
            arbitration["king_identity_arbitration"] = king_evidence
            if king_selected is not None:
                selected = king_selected
                arbitration.update({
                    "reason": "king_identity_actualized_continuation",
                    "actualization_authority": "king_quasicrystal_identity_field",
                    "tie_status": "identity_discriminated_non_dominated",
                    "preference_attributed_to_tiebreak": False,
                })
            else:
                selected = _neutral_equivalence_choice(
                    simulated_survivors,
                    user_text,
                    turn_tick,
                )
                arbitration.update({
                    "reason": "true_equivalence_neutral_actualization",
                    "actualization_authority": "neutral_equivalence",
                    "tie_status": "genuinely_non_dominated_after_identity",
                    "preference_attributed_to_tiebreak": False,
                    "eligible_candidate_ids": [
                        candidate.candidate_id
                        for candidate in sorted(
                            simulated_survivors,
                            key=lambda item: item.candidate_id,
                        )
                    ],
                })

    selected.selected = True
    arbitration["selected_candidate_id"] = selected.candidate_id

    # Observability only. Store summaries, never rejected ThoughtState objects.
    systems["_current_possibility_frontier"] = {
        "turn_tick": int(turn_tick),
        "actualized": False,
        "arbitration": dict(arbitration),
        "candidates": [candidate.summary() for candidate in candidates],
    }
    systems["_selected_possibility"] = selected.summary()

    return PossibilityResolution(
        selected=selected,
        candidates=candidates,
        arbitration=arbitration,
    )


def mark_actualized(systems: Dict[str, Any], selected_thought: Any) -> None:
    """Mark the caller-owned actuality boundary after continuity commits winner."""
    frontier = systems.get("_current_possibility_frontier")
    if isinstance(frontier, dict):
        frontier["actualized"] = True
        frontier["actualized_thought_tick"] = int(
            getattr(selected_thought, "tick", 0) or 0
        )
