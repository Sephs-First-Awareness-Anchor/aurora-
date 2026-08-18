#!/usr/bin/env python3
"""
Aurora Build 723 -- native motivation binding for the App Habitat.

The Habitat remains a neutral physical substrate. This module performs five
inspectable stages:

  A. collect Aurora's already-live unresolved internal state;
  B. bind it to persisted facts about particular Habitat entities;
  C. compare it with the physical consequence dimensions of legal affordances;
  D. instantiate complete actions and source every parameter;
  E. submit complete instances to neutral agency arbitration.

No territory, actor, constraint family, or provisional-field count receives a
fixed preference. A staged representational candidate can affect a score only
through its exact value, and can receive later credit only if that difference
changed downstream cognition and the resulting consequence discriminated it.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")
DIMENSIONS: Tuple[str, ...] = ("POLARITY", "MAGNITUDE", "OPERATOR", "COST", "DIFFERENCE")
MIN_RELEVANCE_TO_ENGAGE = 0.20
IDENTITY_FIELD_DEVIATION_WEIGHT = 1.0
REPRESENTATIONAL_INQUIRY_STRENGTH = 0.28
SCORE_EPSILON = 1e-9

_RECOLOR_PALETTE: Tuple[str, ...] = (
    "red", "blue", "green", "yellow", "purple", "orange", "teal", "gray",
)
_CREATABLE_ENTITY_TYPES: Tuple[str, ...] = (
    "shape", "mark_path",
)

# Native NonComp dimensions compared with physical consequence dimensions.
# The table describes structural compatibility, not developmental meaning and
# never names an operation.
_CONSEQUENCE_DIMENSION_FEATURES: Dict[str, Dict[str, float]] = {
    "existence":            {"OPERATOR": 0.55, "DIFFERENCE": 0.70},
    "persistence":          {"COST": 0.35, "DIFFERENCE": 0.45},
    "spatial_relation":     {"POLARITY": 0.55, "MAGNITUDE": 0.75, "OPERATOR": 0.35, "DIFFERENCE": 0.85},
    "extent_magnitude":     {"MAGNITUDE": 1.00, "OPERATOR": 0.35, "DIFFERENCE": 0.65},
    "orientation":          {"POLARITY": 1.00, "MAGNITUDE": 0.45, "DIFFERENCE": 0.65},
    "appearance":           {"POLARITY": 0.35, "MAGNITUDE": 0.35, "DIFFERENCE": 0.85},
    "relational_structure": {"OPERATOR": 0.75, "DIFFERENCE": 0.90},
    "containment":          {"OPERATOR": 0.65, "DIFFERENCE": 0.75},
    "ownership":            {"POLARITY": 0.45, "OPERATOR": 0.65, "DIFFERENCE": 0.55},
    "territory_boundary":   {"POLARITY": 0.55, "OPERATOR": 0.65, "DIFFERENCE": 0.75},
    "permission_boundary":  {"POLARITY": 0.65, "OPERATOR": 0.65, "DIFFERENCE": 0.75},
}


@dataclass
class HabitatEngagementRecord:
    timestamp: float
    active_pressures: Dict[str, float]
    active_inquiries: List[str]
    environmental_affordances_considered: int
    candidate_actions: List[Dict[str, Any]]
    selected_action: Optional[Dict[str, Any]]
    selection_evidence: Dict[str, Any]
    competing_candidates: List[Dict[str, Any]]
    internal_sources: Dict[str, Any]
    pre_state: Optional[Dict[str, Any]] = None
    post_state: Optional[Dict[str, Any]] = None
    consequence: Optional[Dict[str, Any]] = None
    pressure_change: Optional[Dict[str, float]] = None
    engaged: bool = False
    useful_distinction: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "active_pressures": self.active_pressures,
            "active_inquiries": self.active_inquiries,
            "environmental_affordances_considered": self.environmental_affordances_considered,
            "candidate_actions": self.candidate_actions,
            "selected_action": self.selected_action,
            "selection_evidence": self.selection_evidence,
            "competing_candidates": self.competing_candidates,
            "internal_sources": self.internal_sources,
            "pre_state": self.pre_state,
            "post_state": self.post_state,
            "consequence": self.consequence,
            "pressure_change": self.pressure_change,
            "engaged": self.engaged,
            "useful_distinction": self.useful_distinction,
        }


def _clip01(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except Exception:
        return 0.0


def _cosine(left: Dict[str, float], right: Dict[str, float], keys: Iterable[str]) -> float:
    key_list = list(keys)
    dot = sum(float(left.get(k, 0.0)) * float(right.get(k, 0.0)) for k in key_list)
    lnorm = math.sqrt(sum(float(left.get(k, 0.0)) ** 2 for k in key_list))
    rnorm = math.sqrt(sum(float(right.get(k, 0.0)) ** 2 for k in key_list))
    if lnorm <= 1e-12 or rnorm <= 1e-12:
        return 0.0
    return _clip01(dot / (lnorm * rnorm))


def _stable_blob(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "to_dict"):
        try:
            return _json_safe(value.to_dict())
        except Exception:
            pass
    content = getattr(value, "content", None)
    if content is not None:
        return {"type": type(value).__name__, "content": _json_safe(content)}
    return {"type": type(value).__name__, "identity": str(value)}


def _candidate_identity(candidate: Dict[str, Any]) -> str:
    payload = {
        "operation": candidate.get("operation"),
        "territory": candidate.get("territory"),
        "target_ids": sorted(str(v) for v in (candidate.get("target_ids") or [])),
        "parameters": candidate.get("parameters") or {},
    }
    return "hcand_" + hashlib.sha256(_stable_blob(payload).encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Stage A -- internal motivational state
# ---------------------------------------------------------------------------

def _identity_field_status(systems: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    identity_field = (systems or {}).get("identity_field")
    if identity_field is None or not hasattr(identity_field, "status"):
        return {}
    try:
        status = identity_field.status() or {}
    except Exception:
        return {}
    return status if isinstance(status, dict) else {}


def _identity_field_reference(
    systems: Optional[Dict[str, Any]], status: Dict[str, Any],
) -> Dict[str, float]:
    identity_field = (systems or {}).get("identity_field")
    reference: Dict[str, Any] = {}
    if identity_field is not None and hasattr(identity_field, "reference_axis_pressures"):
        try:
            reference = identity_field.reference_axis_pressures() or {}
        except Exception:
            reference = {}
    if not reference:
        reference = status.get("reference_axis_pressures") or {}
    if not reference and systems is not None:
        # Neutral local fallback for older field implementations: the first
        # observed stable state becomes the reference, so the first read cannot
        # manufacture motive. Later perturbations are measured against it.
        key = "_habitat_identity_reference_state"
        reference = dict(systems.get(key) or {})
        if not reference:
            current = status.get("axis_pressures") or {}
            reference = {axis: float(current[axis]) for axis in AXES if axis in current}
            systems[key] = dict(reference)
    return {axis: float(reference[axis]) for axis in AXES if axis in reference}


def _identity_field_axis_elevation(systems: Optional[Dict[str, Any]]) -> Dict[str, float]:
    status = _identity_field_status(systems)
    current = status.get("axis_pressures") or {}
    reference = _identity_field_reference(systems, status)
    elevation: Dict[str, float] = {}
    for axis in AXES:
        if axis not in current or axis not in reference:
            continue
        deviation = float(current[axis]) - float(reference[axis])
        if deviation > 0.0:
            elevation[axis] = deviation * IDENTITY_FIELD_DEVIATION_WEIGHT
    return elevation


def _representational_inadequacy(systems: Optional[Dict[str, Any]]) -> Dict[str, float]:
    from aurora_representational_address import RepresentationalRef
    from aurora_representational_resolution import get_or_create_engine

    engine = get_or_create_engine(systems)
    if engine is None:
        return {}
    out: Dict[str, float] = {}
    for axis in AXES:
        ref = RepresentationalRef.for_c1(axis, "OPERATOR", "A")
        ability_id = engine.ability_id_for_ref(ref)
        if ability_id not in getattr(engine.genealogy, "abilities", {}):
            continue
        pressure = float(engine.inadequacy_pressure(ref))
        if pressure > 0.0:
            out[axis] = pressure
    return out


def active_inquiries(systems: Optional[Dict[str, Any]]) -> List[str]:
    from aurora_representational_address import RepresentationalRef
    from aurora_representational_resolution import get_or_create_engine

    engine = get_or_create_engine(systems)
    if engine is None:
        return []
    active: List[str] = []
    for axis in AXES:
        ref = RepresentationalRef.for_c1(axis, "OPERATOR", "A")
        if ref.encode() in getattr(engine, "_active_stage_for_ref", {}):
            active.append(axis)
    return active


def active_pressures(systems: Optional[Dict[str, Any]]) -> Dict[str, float]:
    inadequacy = _representational_inadequacy(systems)
    field_deviation = _identity_field_axis_elevation(systems)
    inquiries = set(active_inquiries(systems))
    pressures: Dict[str, float] = {}
    for axis in AXES:
        value = inadequacy.get(axis, 0.0) + field_deviation.get(axis, 0.0)
        if axis in inquiries:
            value += REPRESENTATIONAL_INQUIRY_STRENGTH
        if value > 0.0:
            pressures[axis] = value
    return pressures


def _snapshot_to_dict(snapshot: Any) -> Dict[str, Any]:
    if snapshot is None:
        return {}
    if hasattr(snapshot, "to_dict"):
        try:
            value = snapshot.to_dict()
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}
    return dict(snapshot) if isinstance(snapshot, dict) else {}


def _native_dimension_state(systems: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    status = _identity_field_status(systems)
    raw = dict(status.get("dimension_pressures") or {})
    identity_field = (systems or {}).get("identity_field")
    if not raw and identity_field is not None and hasattr(identity_field, "dimension_pressures"):
        try:
            raw = dict(identity_field.dimension_pressures() or {})
        except Exception:
            raw = {}

    result: Dict[str, Dict[str, Any]] = {
        dimension: {
            "strength": _clip01(float(raw.get(dimension, 0.0)) * 8.0),
            "sources": ["identity_field_profiles"] if float(raw.get(dimension, 0.0) or 0.0) > 0.0 else [],
        }
        for dimension in DIMENSIONS
    }

    difference_snapshot = _snapshot_to_dict((systems or {}).get("_last_diff_snapshot"))
    values = difference_snapshot.get("values") or {}
    numeric_values: List[float] = []
    for value in values.values() if isinstance(values, dict) else []:
        try:
            numeric_values.append(float(value))
        except Exception:
            continue
    if numeric_values:
        strength = _clip01(max(abs(value) for value in numeric_values))
        result["DIFFERENCE"]["strength"] = max(result["DIFFERENCE"]["strength"], strength)
        result["DIFFERENCE"]["sources"].append("difference_snapshot")
        signed = sum(numeric_values) / len(numeric_values)
        result["POLARITY"]["signed_value"] = max(-1.0, min(1.0, signed))
        result["POLARITY"]["strength"] = max(result["POLARITY"]["strength"], _clip01(abs(signed)))
        result["POLARITY"]["sources"].append("difference_snapshot")
    return result


def _ref_axis_profile(ref: Any) -> Dict[str, float]:
    profile = {axis: 0.0 for axis in AXES}
    for field_name in ("nc_law_c", "nc_target", "sub_law_c", "col_law_c"):
        value = getattr(ref, field_name, None)
        if value in profile:
            profile[value] += 1.0
    return profile


def _ref_dimension_profile(ref: Any) -> Dict[str, float]:
    profile = {dimension: 0.0 for dimension in DIMENSIONS}
    for field_name in ("nc_dim", "sub_law_d", "col_law_d"):
        value = getattr(ref, field_name, None)
        if value in profile:
            profile[value] += 1.0
    return profile


def resolved_context_for_axis(systems: Optional[Dict[str, Any]], axis: str) -> Dict[str, Any]:
    from aurora_representational_address import RepresentationalRef
    from aurora_representational_resolution import get_or_create_engine

    engine = get_or_create_engine(systems)
    empty = {
        "resolved_fields": (),
        "earned_fields": (),
        "provisional_fields": (),
        "level": "UNKNOWN",
        "representation_without_candidate": None,
        "representation_with_candidate": None,
        "provisional_candidate": None,
    }
    if engine is None:
        return empty
    ref = RepresentationalRef.for_c1(axis, "OPERATOR", "A")
    refined = engine.current_resolution(ref)
    base_resolved = set(ref.resolved_fields())
    earned = tuple(field for field in refined.resolved_fields() if field not in base_resolved)
    provisional = engine.provisional_resolution(ref)
    provisional_fields = tuple(
        field for field in provisional.resolved_fields()
        if field not in base_resolved and field not in earned
    )
    pending = dict(getattr(engine, "_active_stage_for_ref", {}).get(ref.encode()) or {})
    candidate = dict(pending.get("candidate") or {})
    provisional_candidate = None
    if candidate:
        provisional_candidate = {
            "field": str(candidate.get("field") or ""),
            "value": candidate.get("candidate_value"),
            "source": candidate.get("source"),
            "origin": candidate.get("origin"),
            "ref_encoded": ref.encode(),
        }
    return {
        "resolved_fields": refined.resolved_fields(),
        "earned_fields": earned,
        "provisional_fields": provisional_fields,
        "level": refined.level(),
        "representation_without_candidate": refined.encode(),
        "representation_with_candidate": provisional.encode(),
        "provisional_candidate": provisional_candidate,
        "_without_ref": refined,
        "_with_ref": provisional,
    }


def collect_internal_motivational_state(systems: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    inadequacy = _representational_inadequacy(systems)
    field_deviations = _identity_field_axis_elevation(systems)
    inquiries = active_inquiries(systems)
    axis_strength = active_pressures(systems)
    resolution_context = {
        axis: resolved_context_for_axis(systems, axis)
        for axis in AXES
        if axis in axis_strength or axis in inquiries
    }
    generic_inquiry_sources: List[Dict[str, Any]] = []
    for key in (
        "_gap_seeking_concept",
        "_active_reflective_readdressing",
    ):
        value = (systems or {}).get(key)
        if value:
            generic_inquiry_sources.append({"source": key, "value": value})
    causal_thread_sources: List[Dict[str, Any]] = []
    prediction_discrepancy_sources: List[Dict[str, Any]] = []
    for key in (
        "_active_recursive_causal_cycle",
        "_last_recursive_causal_cycle",
        "_incoming_recursive_causal_disturbance",
    ):
        value = (systems or {}).get(key)
        if not value:
            continue
        record = {"source": key, "value": value}
        causal_thread_sources.append(record)
        if _contains_identity(value, "prediction"):
            prediction_discrepancy_sources.append(record)
    self_directed = bool((systems or {}).get("_active_reflective_readdressing"))
    return {
        "axis_strength": axis_strength,
        "representational_inadequacy": inadequacy,
        "field_deviations": field_deviations,
        "representational_inquiries": inquiries,
        "generic_inquiry_sources": generic_inquiry_sources,
        "causal_thread_sources": causal_thread_sources,
        "prediction_discrepancy_sources": prediction_discrepancy_sources,
        "native_dimensions": _native_dimension_state(systems),
        "resolution_context": resolution_context,
        "self_directed_structure": self_directed,
        "reactivated_memory_count": len(list((systems or {}).get("_sedi_surface_frags") or [])),
    }


def _has_internal_source(internal: Dict[str, Any]) -> bool:
    if internal.get("axis_strength"):
        return True
    if internal.get("generic_inquiry_sources"):
        return True
    if internal.get("causal_thread_sources") or internal.get("prediction_discrepancy_sources"):
        return True
    if int(internal.get("reactivated_memory_count", 0) or 0) > 0:
        return True
    return any(
        float(value.get("strength", 0.0)) > 0.0
        for value in (internal.get("native_dimensions") or {}).values()
    )


# ---------------------------------------------------------------------------
# Stage B -- entity-specific environmental relevance
# ---------------------------------------------------------------------------

def _contains_identity(value: Any, entity_id: str) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value == entity_id or entity_id in value
    if isinstance(value, dict):
        return any(_contains_identity(k, entity_id) or _contains_identity(v, entity_id)
                   for k, v in value.items())
    if isinstance(value, (list, tuple, set)):
        return any(_contains_identity(item, entity_id) for item in value)
    content = getattr(value, "content", None)
    return _contains_identity(content, entity_id) if content is not None else False


def _event_entity_snapshot(event: Dict[str, Any], key: str, entity_id: str) -> Dict[str, Any]:
    raw = event.get(key) or {}
    if not isinstance(raw, dict):
        return {}
    if raw.get("id") == entity_id:
        return dict(raw)
    nested = raw.get(entity_id)
    return dict(nested) if isinstance(nested, dict) else {}


def _state_difference_dimensions(previous: Dict[str, Any], current: Dict[str, Any]) -> List[str]:
    dimensions: List[str] = []
    if not previous:
        return dimensions
    if previous.get("deleted") != current.get("deleted"):
        dimensions.extend(("existence", "persistence"))
    if previous.get("position") != current.get("position"):
        dimensions.append("spatial_relation")
    if previous.get("dimensions") != current.get("dimensions"):
        dimensions.append("extent_magnitude")
    if previous.get("orientation") != current.get("orientation"):
        dimensions.append("orientation")
    if previous.get("visual_properties") != current.get("visual_properties"):
        dimensions.append("appearance")
    if previous.get("links") != current.get("links"):
        dimensions.append("relational_structure")
    if previous.get("group_membership") != current.get("group_membership"):
        dimensions.append("containment")
    if previous.get("owner") != current.get("owner"):
        dimensions.append("ownership")
    if previous.get("territory") != current.get("territory"):
        dimensions.append("territory_boundary")
    if previous.get("interaction_permissions") != current.get("interaction_permissions"):
        dimensions.append("permission_boundary")
    return sorted(set(dimensions))


def _reactivated_memory_links(systems: Optional[Dict[str, Any]], entity_id: str) -> List[Dict[str, Any]]:
    links: List[Dict[str, Any]] = []
    for fragment in list((systems or {}).get("_sedi_surface_frags") or []):
        content = getattr(fragment, "content", None)
        if content is None and isinstance(fragment, dict):
            content = fragment.get("content", fragment)
        if not _contains_identity(content, entity_id):
            continue
        links.append({
            "event_id": getattr(fragment, "event_id", None)
                        or (fragment.get("event_id") if isinstance(fragment, dict) else None),
            "resonance": float(getattr(fragment, "resonance", 0.0)
                               or (fragment.get("resonance", 0.0) if isinstance(fragment, dict) else 0.0)),
        })
    return links


def _entity_evidence(
    systems: Optional[Dict[str, Any]],
    habitat: Any,
    entity: Dict[str, Any],
    internal: Dict[str, Any],
) -> Dict[str, Any]:
    entity_id = str(entity.get("id") or "")
    history = list(habitat.get_history(entity_id=entity_id, limit=100) or [])
    last_event = history[-1] if history else {}
    aurora_events = [event for event in history if event.get("actor") == "aurora"]
    human_events = [event for event in history if event.get("actor") == "human"]
    last_aurora = aurora_events[-1] if aurora_events else {}
    last_aurora_state = _event_entity_snapshot(last_aurora, "post_state", entity_id)
    differences = _state_difference_dimensions(last_aurora_state, entity)

    inquiry_links = [
        source.get("source")
        for source in (internal.get("generic_inquiry_sources") or [])
        if _contains_identity(source.get("value"), entity_id)
    ]
    memory_links = _reactivated_memory_links(systems, entity_id)

    active_cycle = (systems or {}).get("_active_recursive_causal_cycle")
    last_cycle = (systems or {}).get("_last_recursive_causal_cycle")
    causal_runtime_links = [
        name for name, value in (
            ("active_recursive_causal_cycle", active_cycle),
            ("last_recursive_causal_cycle", last_cycle),
        ) if _contains_identity(value, entity_id)
    ]
    prediction_sources = [
        name for name, value in (
            ("active_recursive_causal_cycle", active_cycle),
            ("last_recursive_causal_cycle", last_cycle),
            ("incoming_recursive_causal_disturbance", (systems or {}).get("_incoming_recursive_causal_disturbance")),
        ) if _contains_identity(value, entity_id)
        and _contains_identity(value, "prediction")
    ]

    open_shared_thread = False
    if last_event and last_event.get("actor") == "human":
        later_aurora = [
            event for event in history
            if event.get("actor") == "aurora"
            and float(event.get("timestamp", 0.0)) > float(last_event.get("timestamp", 0.0))
        ]
        open_shared_thread = bool(last_event.get("causal_parent")) and not later_aurora

    lineage = list(habitat.get_lineage(entity_id) or [])
    actors = sorted({str(event.get("actor")) for event in history if event.get("actor")})
    unobserved_change = bool(
        last_event.get("actor") == "human"
        and last_aurora_state
        and differences
    )
    return {
        "entity_id": entity_id,
        "territory": entity.get("territory"),
        "ownership": entity.get("owner"),
        "creator": entity.get("creator"),
        "prior_actors": actors,
        "last_change": {
            "actor": last_event.get("actor"),
            "operation": last_event.get("event_type"),
            "timestamp": last_event.get("timestamp"),
            "state_changed": last_event.get("state_changed"),
        } if last_event else {},
        "last_aurora_action": {
            "operation": last_aurora.get("event_type"),
            "timestamp": last_aurora.get("timestamp"),
        } if last_aurora else {},
        "last_human_action": {
            "operation": human_events[-1].get("event_type"),
            "timestamp": human_events[-1].get("timestamp"),
        } if human_events else {},
        "state_differences": differences,
        "last_aurora_state": last_aurora_state,
        "unobserved_change": unobserved_change,
        "active_inquiry_links": inquiry_links,
        "reactivated_memory_links": memory_links,
        "causal_runtime_links": causal_runtime_links,
        "prediction_discrepancy_links": prediction_sources,
        "unresolved_lineage": open_shared_thread,
        "creation_lineage": lineage[-20:],
        "interaction_recency": entity.get("modified_at"),
        "recurrence": int(entity.get("interaction_count", 0) or 0),
        "active_links": list(entity.get("links") or []),
        "group_membership": entity.get("group_membership"),
        "shared_participation": len(actors) > 1,
    }


def _entity_relevance(
    evidence: Dict[str, Any],
    internal: Dict[str, Any],
) -> Tuple[float, Dict[str, float]]:
    components: Dict[str, float] = {}
    inquiry_count = len(evidence.get("active_inquiry_links") or [])
    memory_links = list(evidence.get("reactivated_memory_links") or [])
    causal_count = len(evidence.get("causal_runtime_links") or [])
    prediction_count = len(evidence.get("prediction_discrepancy_links") or [])
    axis_strength = internal.get("axis_strength") or {}
    continuity_strength = _clip01(float(axis_strength.get("T", 0.0)))
    agency_strength = _clip01(float(axis_strength.get("A", 0.0)))
    has_prior_aurora_relation = bool(
        evidence.get("creator") == "aurora"
        or evidence.get("last_aurora_action")
        or memory_links
    )
    lineage_intersects_active_state = bool(
        evidence.get("unresolved_lineage")
        and has_prior_aurora_relation
        and (continuity_strength > 0.0 or agency_strength > 0.0)
    )
    if inquiry_count:
        components["active_inquiry_binding"] = min(0.45, 0.30 + 0.05 * inquiry_count)
    if memory_links:
        resonance = max(float(link.get("resonance", 0.0) or 0.0) for link in memory_links)
        components["reactivated_memory_binding"] = 0.22 + 0.18 * _clip01(resonance)
    if causal_count or lineage_intersects_active_state:
        components["causal_thread_binding"] = min(0.42, 0.27 + 0.05 * causal_count)
    if prediction_count:
        components["prediction_discrepancy_binding"] = min(0.40, 0.28 + 0.04 * prediction_count)

    dimension_state = internal.get("native_dimensions") or {}
    difference_strength = float((dimension_state.get("DIFFERENCE") or {}).get("strength", 0.0))
    if evidence.get("state_differences") and difference_strength > 0.0:
        components["active_difference_intersection"] = 0.22 * difference_strength

    if has_prior_aurora_relation and continuity_strength > 0.0:
        components["continuity_of_prior_action"] = 0.12 * continuity_strength
    if has_prior_aurora_relation and agency_strength > 0.0:
        components["agency_authorship_intersection"] = 0.10 * agency_strength
    if evidence.get("shared_participation") and (
        inquiry_count or causal_count or prediction_count or lineage_intersects_active_state
    ):
        components["shared_causal_structure"] = 0.12
    return sum(components.values()), components


# ---------------------------------------------------------------------------
# Stage C -- consequence-specific affordance relevance
# ---------------------------------------------------------------------------

def _dimension_affinity(
    native_dimensions: Dict[str, Dict[str, Any]],
    consequence_dimensions: Sequence[str],
) -> float:
    active = {
        dimension: float((native_dimensions.get(dimension) or {}).get("strength", 0.0))
        for dimension in DIMENSIONS
    }
    physical = {dimension: 0.0 for dimension in DIMENSIONS}
    for consequence_dimension in consequence_dimensions:
        for dimension, weight in _CONSEQUENCE_DIMENSION_FEATURES.get(consequence_dimension, {}).items():
            physical[dimension] += float(weight)
    return _cosine(active, physical, DIMENSIONS)


def _representation_affinity(ref: Any, axis_profile: Dict[str, float],
                             consequence_dimensions: Sequence[str]) -> float:
    axis_affinity = _cosine(_ref_axis_profile(ref), axis_profile, AXES)
    physical_dimensions = {dimension: 0.0 for dimension in DIMENSIONS}
    for consequence_dimension in consequence_dimensions:
        for dimension, weight in _CONSEQUENCE_DIMENSION_FEATURES.get(consequence_dimension, {}).items():
            physical_dimensions[dimension] += float(weight)
    dimension_affinity = _cosine(_ref_dimension_profile(ref), physical_dimensions, DIMENSIONS)
    return (axis_affinity * 0.72) + (dimension_affinity * 0.28)


def _history_yield_factor(
    habitat: Any,
    operation: str,
    territory: str,
    target_ids: Sequence[str],
) -> Tuple[float, Dict[str, Any]]:
    try:
        history = habitat.get_motivation_history(limit=100)
    except Exception:
        history = []
    target_key = sorted(str(value) for value in target_ids)
    equivalent = [
        event for event in history
        if event.get("selected_operation") == operation
        and event.get("selected_territory") == territory
        and sorted(str(value) for value in (event.get("selected_target_ids") or [])) == target_key
    ]
    ineffective_since_useful = 0
    for event in reversed(equivalent):
        if event.get("useful_distinction") is True:
            break
        if event.get("useful_distinction") is False:
            ineffective_since_useful += 1
    factor = 1.0 / (1.0 + ineffective_since_useful)
    return factor, {
        "equivalent_consequences_observed": len(equivalent),
        "ineffective_since_last_useful_distinction": ineffective_since_useful,
        "factor": factor,
    }


def _score_affordance(
    internal: Dict[str, Any],
    entity_evidence: Dict[str, Any],
    consequence_dimensions: Sequence[str],
    axis_profile: Dict[str, float],
    entity_score: float,
    entity_components: Dict[str, float],
    yield_factor: float,
) -> Tuple[float, float, Dict[str, float], List[Dict[str, Any]]]:
    axis_strength = internal.get("axis_strength") or {}
    total_strength = sum(float(value) for value in axis_strength.values())
    axis_affinity = _cosine(axis_strength, axis_profile, AXES)
    axis_component = min(0.60, total_strength) * (0.30 + 0.70 * axis_affinity)
    native_dimension_affinity = _dimension_affinity(
        internal.get("native_dimensions") or {}, consequence_dimensions,
    )
    native_dimension_strength = max(
        [float(value.get("strength", 0.0))
         for value in (internal.get("native_dimensions") or {}).values()] or [0.0]
    )
    dimension_component = 0.28 * native_dimension_affinity * native_dimension_strength

    state_differences = set(entity_evidence.get("state_differences") or [])
    overlap = state_differences & set(consequence_dimensions)
    bound_entity = bool(
        entity_evidence.get("active_inquiry_links")
        or entity_evidence.get("reactivated_memory_links")
        or entity_evidence.get("causal_runtime_links")
        or entity_evidence.get("prediction_discrepancy_links")
        or entity_components.get("causal_thread_binding")
    )
    discrepancy_component = 0.0
    if overlap and bound_entity:
        discrepancy_component = 0.38 * (len(overlap) / max(1, len(state_differences)))

    base_score = (
        axis_component
        + dimension_component
        + entity_score
        + discrepancy_component
    ) * yield_factor
    score = base_score
    provisional_effects: List[Dict[str, Any]] = []
    for axis, context in (internal.get("resolution_context") or {}).items():
        candidate = context.get("provisional_candidate")
        without_ref = context.get("_without_ref")
        with_ref = context.get("_with_ref")
        if not candidate or without_ref is None or with_ref is None:
            continue
        source_strength = float(axis_strength.get(axis, 0.0))
        without_affinity = _representation_affinity(
            without_ref, axis_profile, consequence_dimensions,
        )
        with_affinity = _representation_affinity(
            with_ref, axis_profile, consequence_dimensions,
        )
        delta = (with_affinity - without_affinity) * source_strength * 0.38
        score += delta
        provisional_effects.append({
            "ref_encoded": candidate.get("ref_encoded"),
            "field": candidate.get("field"),
            "value": candidate.get("value"),
            "representation_without_candidate": context.get("representation_without_candidate"),
            "representation_with_candidate": context.get("representation_with_candidate"),
            "affinity_without_candidate": without_affinity,
            "affinity_with_candidate": with_affinity,
            "score_delta": delta,
        })

    components = {
        "axis_consequence_intersection": axis_component,
        "native_dimension_intersection": dimension_component,
        "entity_relevance": entity_score,
        "entity_state_difference_intersection": discrepancy_component,
        "consequence_yield_factor": yield_factor,
        **{f"entity:{name}": value for name, value in entity_components.items()},
    }
    return score, base_score, components, provisional_effects


# ---------------------------------------------------------------------------
# Stage D -- fully instantiated actions and parameter provenance
# ---------------------------------------------------------------------------

def _exploratory_source(source: str = "bounded_stochastic_exploration") -> Dict[str, Any]:
    return {"mode": "exploratory", "source_evidence": [source], "confidence": 0.0}


def _constrained_source(sources: Sequence[str], confidence: float) -> Dict[str, Any]:
    return {
        "mode": "structurally_constrained",
        "source_evidence": list(sources),
        "confidence": _clip01(confidence),
    }


def _prior_value(entity_evidence: Dict[str, Any], key: str, nested_key: Optional[str] = None) -> Any:
    previous = entity_evidence.get("last_aurora_state") or {}
    value = previous.get(key)
    if nested_key is not None:
        return value.get(nested_key) if isinstance(value, dict) else None
    return value


def _operation_instances(
    operation: str,
    entity: Dict[str, Any],
    all_entities: List[Dict[str, Any]],
    internal: Dict[str, Any],
    evidence: Dict[str, Any],
) -> List[Tuple[Dict[str, Any], List[str], Dict[str, Any]]]:
    entity_id = str(entity.get("id") or "")
    native_dimensions = internal.get("native_dimensions") or {}
    magnitude = float((native_dimensions.get("MAGNITUDE") or {}).get("strength", 0.0))
    polarity_record = native_dimensions.get("POLARITY") or {}
    polarity_available = (
        "signed_value" in polarity_record
        and float(polarity_record.get("strength", 0.0) or 0.0) > 0.0
    )
    polarity = float(polarity_record.get("signed_value", 0.0) or 0.0)
    differences = set(evidence.get("state_differences") or [])
    bound = bool(
        evidence.get("active_inquiry_links")
        or evidence.get("reactivated_memory_links")
        or evidence.get("causal_runtime_links")
        or evidence.get("prediction_discrepancy_links")
        or evidence.get("unresolved_lineage")
    )

    if operation == "move":
        prior = _prior_value(evidence, "position")
        if bound and "spatial_relation" in differences and isinstance(prior, list) and len(prior) >= 2:
            return [(
                {"x": _clip01(prior[0]), "y": _clip01(prior[1])}, [],
                {
                    "x": _constrained_source(["entity_state_difference", "last_aurora_state"], 0.85),
                    "y": _constrained_source(["entity_state_difference", "last_aurora_state"], 0.85),
                },
            )]
        if magnitude > 0.0:
            current = list(entity.get("position") or [0.5, 0.5])
            step = 0.04 + (0.36 * magnitude)
            direction = (1.0 if polarity >= 0.0 else -1.0) if polarity_available else random.choice((-1.0, 1.0))
            sources = ["native_MAGNITUDE"] + (["native_POLARITY"] if polarity_available else [])
            source = _constrained_source(sources, magnitude)
            if not polarity_available:
                source["unconstrained_components"] = ["direction:bounded_stochastic_exploration"]
            return [(
                {
                    "x": _clip01(float(current[0]) + direction * step),
                    "y": _clip01(float(current[1]) - direction * step),
                },
                [],
                {"x": source, "y": source},
            )]
        return [(
            {"x": round(random.uniform(0.0, 1.0), 4),
             "y": round(random.uniform(0.0, 1.0), 4)},
            [],
            {"x": _exploratory_source(), "y": _exploratory_source()},
        )]

    if operation == "resize":
        prior = _prior_value(evidence, "dimensions")
        if bound and "extent_magnitude" in differences and isinstance(prior, list) and len(prior) >= 2:
            return [(
                {"width": _clip01(prior[0]), "height": _clip01(prior[1])}, [],
                {
                    "width": _constrained_source(["entity_state_difference", "last_aurora_state"], 0.85),
                    "height": _constrained_source(["entity_state_difference", "last_aurora_state"], 0.85),
                },
            )]
        if magnitude > 0.0:
            value = round(0.05 + 0.90 * magnitude, 4)
            source = _constrained_source(["native_MAGNITUDE"], magnitude)
            return [({"width": value, "height": value}, [], {"width": source, "height": source})]
        return [(
            {"width": round(random.uniform(0.05, 1.0), 4),
             "height": round(random.uniform(0.05, 1.0), 4)},
            [],
            {"width": _exploratory_source(), "height": _exploratory_source()},
        )]

    if operation == "rotate":
        prior = _prior_value(evidence, "orientation")
        if bound and "orientation" in differences and prior is not None:
            return [(
                {"degrees": float(prior) % 360.0}, [],
                {"degrees": _constrained_source(["entity_state_difference", "last_aurora_state"], 0.85)},
            )]
        if magnitude > 0.0 or polarity_available:
            degrees = (360.0 * magnitude) * (1.0 if polarity >= 0.0 else -1.0)
            sources = (["native_MAGNITUDE"] if magnitude > 0.0 else []) \
                + (["native_POLARITY"] if polarity_available else [])
            source = _constrained_source(sources, max(magnitude, abs(polarity)))
            if not polarity_available:
                degrees *= random.choice((-1.0, 1.0))
                source["unconstrained_components"] = ["direction:bounded_stochastic_exploration"]
            return [(
                {"degrees": round(degrees % 360.0, 2)}, [],
                {"degrees": source},
            )]
        return [(
            {"degrees": round(random.uniform(0.0, 360.0), 2)}, [],
            {"degrees": _exploratory_source()},
        )]

    if operation == "recolor":
        prior_color = _prior_value(evidence, "visual_properties", "color")
        if bound and "appearance" in differences and prior_color is not None:
            return [(
                {"color": prior_color}, [],
                {"color": _constrained_source(["entity_state_difference", "last_aurora_state"], 0.85)},
            )]
        current = (entity.get("visual_properties") or {}).get("color")
        choices = [value for value in _RECOLOR_PALETTE if value != current] or list(_RECOLOR_PALETTE)
        return [(
            {"color": random.choice(choices)}, [],
            {"color": _exploratory_source()},
        )]

    if operation in ("connect", "disconnect", "group"):
        territory = entity.get("territory")
        links = set(entity.get("links") or [])
        instances = []
        for other in all_entities:
            other_id = str(other.get("id") or "")
            if not other_id or other_id == entity_id or other.get("deleted"):
                continue
            if other.get("territory") != territory:
                continue
            if not (other.get("interaction_permissions") or {}).get("modifiable_by_aurora", False):
                continue
            linked = other_id in links
            if operation == "connect" and linked:
                continue
            if operation == "disconnect" and not linked:
                continue
            if operation == "group" and entity.get("group_membership") == other.get("group_membership") \
                    and entity.get("group_membership") is not None:
                continue
            instances.append(({}, [other_id], {}))
        return instances

    if operation == "transfer":
        instances = []
        for owner in ("aurora", "human", "shared"):
            for territory in ("space", "self"):
                if owner == entity.get("owner") and territory == entity.get("territory"):
                    continue
                params = {"owner": owner, "territory": territory}
                sources = {
                    "owner": _exploratory_source("enumerated_legal_alternative"),
                    "territory": _exploratory_source("enumerated_legal_alternative"),
                }
                instances.append((params, [], sources))
        return instances

    if operation in ("grant_permission", "revoke_permission"):
        desired = operation == "grant_permission"
        instances = []
        for permission, current in (entity.get("interaction_permissions") or {}).items():
            if bool(current) == desired:
                continue
            instances.append((
                {"permission": permission}, [],
                {"permission": _exploratory_source("enumerated_legal_alternative")},
            ))
        return instances

    if operation == "restore" and not entity.get("deleted"):
        return []
    if operation != "restore" and entity.get("deleted"):
        return []
    return [({}, [], {})]


def _creation_instance(
    territory: str,
    internal: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    native_dimensions = internal.get("native_dimensions") or {}
    magnitude = float((native_dimensions.get("MAGNITUDE") or {}).get("strength", 0.0))
    polarity_record = native_dimensions.get("POLARITY") or {}
    polarity_strength = float(polarity_record.get("strength", 0.0))
    polarity_available = "signed_value" in polarity_record and polarity_strength > 0.0
    polarity = float(polarity_record.get("signed_value", 0.0) or 0.0)
    entity_type = random.choice(_CREATABLE_ENTITY_TYPES)
    parameters: Dict[str, Any] = {
        "entity_type": entity_type,
        "position": [round(random.uniform(0.0, 1.0), 4), round(random.uniform(0.0, 1.0), 4)],
        "visual_properties": {"color": random.choice(_RECOLOR_PALETTE)},
    }
    if entity_type == "mark_path":
        # Geometry is a complete physical affordance, not invented semantic
        # content. Text remains unavailable until Aurora has actual text to externalize.
        parameters["content"] = {
            "points": [[round(random.uniform(0.1, 0.4), 4), round(random.uniform(0.1, 0.9), 4)],
                       [round(random.uniform(0.6, 0.9), 4), round(random.uniform(0.1, 0.9), 4)]]
        }
    sources: Dict[str, Any] = {
        "entity_type": _exploratory_source(),
        "position": _exploratory_source(),
        "visual_properties.color": _exploratory_source(),
    }
    if entity_type == "mark_path":
        sources["content.points"] = _exploratory_source("bounded_geometric_instantiation")
    if magnitude > 0.0:
        size = round(0.05 + 0.45 * magnitude, 4)
        parameters["dimensions"] = [size, size]
        sources["dimensions"] = _constrained_source(["native_MAGNITUDE"], magnitude)
    else:
        parameters["dimensions"] = [
            round(random.uniform(0.05, 0.30), 4),
            round(random.uniform(0.05, 0.30), 4),
        ]
        sources["dimensions"] = _exploratory_source()
    if polarity_available:
        parameters["orientation"] = round((180.0 * (1.0 + polarity)) % 360.0, 2)
        sources["orientation"] = _constrained_source(["native_POLARITY"], polarity_strength)
    else:
        parameters["orientation"] = round(random.uniform(0.0, 360.0), 2)
        sources["orientation"] = _exploratory_source()
    return parameters, sources


def _real_operations_for_entity(
    habitat: Any, territory: Optional[str], entity: Dict[str, Any],
) -> List[str]:
    try:
        operations = list((habitat.get_affordances() or {}).get("operations") or [])
    except Exception:
        return []
    entity_type = entity.get("entity_type")
    deleted = bool(entity.get("deleted"))
    result: List[str] = []
    for operation in operations:
        if operation == "create":
            continue
        if deleted and operation != "restore":
            continue
        if not deleted and operation == "restore":
            continue
        if operation in ("resize", "rotate", "recolor") and entity_type == "group":
            continue
        if operation == "ungroup" and entity_type != "group":
            continue
        if operation == "group" and entity_type == "group":
            continue
        result.append(operation)
    return result


def _operation_available_to_aurora(operation: str, entity: Dict[str, Any]) -> bool:
    """Mirror Habitat's structural permission distinctions per operation."""
    permissions = entity.get("interaction_permissions") or {}
    if operation == "transfer":
        return bool(permissions.get("transferable", True))
    if operation in ("grant_permission", "revoke_permission"):
        return entity.get("owner") in ("aurora", "shared")
    return bool(permissions.get("modifiable_by_aurora", False))


def _instance_would_change_entity(
    operation: str, entity: Dict[str, Any], parameters: Dict[str, Any], extra_targets: Sequence[str],
) -> bool:
    """Reject fully instantiated simple no-ops before agency arbitration."""
    if operation == "move":
        current = list(entity.get("position") or [0.5, 0.5])
        proposed = [_clip01(parameters.get("x", current[0])), _clip01(parameters.get("y", current[1]))]
        return proposed != current
    if operation == "resize":
        current = list(entity.get("dimensions") or [0.1, 0.1])
        proposed = [
            _clip01(parameters.get("width", current[0])),
            _clip01(parameters.get("height", current[1])),
        ]
        return proposed != current
    if operation == "rotate":
        current = float(entity.get("orientation", 0.0) or 0.0) % 360.0
        return (float(parameters.get("degrees", current)) % 360.0) != current
    if operation == "recolor":
        visual = entity.get("visual_properties") or {}
        return any(visual.get(key) != value for key, value in parameters.items())
    if operation == "transfer":
        return (
            parameters.get("owner", entity.get("owner")) != entity.get("owner")
            or parameters.get("territory", entity.get("territory")) != entity.get("territory")
        )
    if operation in ("connect", "disconnect", "group"):
        return bool(extra_targets)
    return True


def _dominant_axis(internal: Dict[str, Any]) -> Optional[str]:
    strengths = internal.get("axis_strength") or {}
    if not strengths:
        return None
    return max(sorted(strengths), key=lambda axis: float(strengths.get(axis, 0.0)))


def _candidate_record(
    *,
    operation: str,
    territory: str,
    target_ids: List[str],
    entity_type: Optional[str],
    parameters: Dict[str, Any],
    parameter_sources: Dict[str, Any],
    consequence_dimensions: List[str],
    consequence_axis_profile: Dict[str, float],
    entity_evidence: Dict[str, Any],
    score: float,
    baseline_score: float,
    score_components: Dict[str, float],
    provisional_effects: List[Dict[str, Any]],
    internal: Dict[str, Any],
    yield_evidence: Dict[str, Any],
) -> Dict[str, Any]:
    dominant_axis = _dominant_axis(internal)
    context = (internal.get("resolution_context") or {}).get(dominant_axis, {})
    public_entity_evidence = {
        key: value for key, value in entity_evidence.items()
        if key not in {"last_aurora_state", "creation_lineage"}
    }
    public_entity_evidence["creation_lineage"] = [
        {
            "event": event.get("event"),
            "action_id": event.get("action_id"),
            "parent_ids": list(event.get("parent_ids") or []),
        }
        for event in list(entity_evidence.get("creation_lineage") or [])[-5:]
    ]
    candidate = {
        "operation": operation,
        "territory": territory,
        "target_ids": list(target_ids),
        "entity_type": entity_type,
        "parameters": dict(parameters),
        "relevance_score": float(score),
        "baseline_relevance_score": float(baseline_score),
        "internal_sources": {
            "active_field_deviations": internal.get("field_deviations") or {},
            "representational_inadequacy": internal.get("representational_inadequacy") or {},
            "inquiries": internal.get("representational_inquiries") or [],
            "generic_inquiries": _json_safe(internal.get("generic_inquiry_sources") or []),
            "native_dimensions": internal.get("native_dimensions") or {},
            "causal_threads": {
                "active_sources": [
                    source.get("source") for source in (internal.get("causal_thread_sources") or [])
                ],
                "entity_bindings": list(public_entity_evidence.get("causal_runtime_links") or []),
            },
            "reactivated_memories": list(public_entity_evidence.get("reactivated_memory_links") or []),
            "prediction_discrepancies": {
                "active_sources": [
                    source.get("source")
                    for source in (internal.get("prediction_discrepancy_sources") or [])
                ],
                "entity_bindings": list(public_entity_evidence.get("prediction_discrepancy_links") or []),
            },
        },
        "entity_evidence": public_entity_evidence,
        "affordance": {
            "operation": operation,
            "consequence_dimensions_affected": consequence_dimensions,
            "consequence_axis_profile": consequence_axis_profile,
        },
        "parameter_sources": parameter_sources,
        "provisional_resolution": provisional_effects,
        "candidate_score_components": score_components,
        "consequence_yield_evidence": yield_evidence,
        "tie_status": "not_arbitrated",
        "selected": False,
        "rejected": False,
        # Compatibility surface for earlier observability consumers.
        "reason": {
            "axis": dominant_axis,
            "inadequacy_pressure": (internal.get("representational_inadequacy") or {}).get(dominant_axis, 0.0),
            "active_inquiry_pending": dominant_axis in set(internal.get("representational_inquiries") or []),
            "earned_resolution": {
                "resolved_fields": context.get("resolved_fields", ()),
                "earned_fields": context.get("earned_fields", ()),
                "provisional_fields": context.get("provisional_fields", ()),
                "level": context.get("level", "UNKNOWN"),
            },
            "ownership_bonus": 0.0,
        },
    }
    candidate["candidate_id"] = _candidate_identity(candidate)
    return candidate


def candidate_actions(systems: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    habitat = (systems or {}).get("habitat")
    if habitat is None:
        return []
    internal = collect_internal_motivational_state(systems)
    if not _has_internal_source(internal):
        return []
    try:
        state = habitat.get_state(actor="aurora", include_deleted=True)
        affordances = habitat.get_affordances()
    except Exception:
        return []
    all_entities = list((state or {}).get("entities") or [])
    consequence_map = dict((affordances or {}).get("consequence_dimensions") or {})
    axis_profile_map = dict((affordances or {}).get("consequence_axis_profiles") or {})
    candidates: List[Dict[str, Any]] = []

    for entity in all_entities:
        entity_id = str(entity.get("id") or "")
        if not entity_id:
            continue
        evidence = _entity_evidence(systems, habitat, entity, internal)
        entity_score, entity_components = _entity_relevance(evidence, internal)
        for operation in _real_operations_for_entity(habitat, entity.get("territory"), entity):
            if not _operation_available_to_aurora(operation, entity):
                continue
            consequence_dimensions = list(consequence_map.get(operation) or [])
            axis_profile = dict(axis_profile_map.get(operation) or {})
            for parameters, extra_targets, parameter_sources in _operation_instances(
                operation, entity, all_entities, internal, evidence,
            ):
                if not _instance_would_change_entity(
                    operation, entity, parameters, extra_targets,
                ):
                    continue
                target_ids = [entity_id] + list(extra_targets)
                yield_factor, yield_evidence = _history_yield_factor(
                    habitat, operation, str(entity.get("territory")), target_ids,
                )
                score, baseline_score, components, provisional_effects = _score_affordance(
                    internal, evidence, consequence_dimensions, axis_profile,
                    entity_score, entity_components, yield_factor,
                )
                candidates.append(_candidate_record(
                    operation=operation,
                    territory=str(entity.get("territory")),
                    target_ids=target_ids,
                    entity_type=entity.get("entity_type"),
                    parameters=parameters,
                    parameter_sources=parameter_sources,
                    consequence_dimensions=consequence_dimensions,
                    consequence_axis_profile=axis_profile,
                    entity_evidence=evidence,
                    score=score,
                    baseline_score=baseline_score,
                    score_components=components,
                    provisional_effects=provisional_effects,
                    internal=internal,
                    yield_evidence=yield_evidence,
                ))

    # Creation is a physical affordance of absence, not an X-to-create rule.
    # It competes whenever active structure exists. Its absence component is
    # strongest when no live entity currently offers any consequence surface.
    live_entities = [entity for entity in all_entities if not entity.get("deleted")]
    internal_strength = min(0.60, sum((internal.get("axis_strength") or {}).values()))
    if internal_strength <= 0.0:
        internal_strength = 0.25 if _has_internal_source(internal) else 0.0
    for territory in ("self", "space"):
        operation = "create"
        consequence_dimensions = list(consequence_map.get(operation) or [])
        axis_profile = dict(axis_profile_map.get(operation) or {})
        parameters, parameter_sources = _creation_instance(territory, internal)
        territory_component = 0.0
        if territory == "self" and internal.get("self_directed_structure"):
            territory_component = 0.18
        if territory == "space":
            open_shared = False
            for entity in all_entities:
                shared_evidence = _entity_evidence(systems, habitat, entity, internal)
                _shared_score, shared_components = _entity_relevance(
                    shared_evidence, internal,
                )
                if shared_components.get("shared_causal_structure", 0.0) > 0.0:
                    open_shared = True
                    break
            if open_shared:
                territory_component = 0.18
        absence_component = internal_strength * (0.55 if not live_entities else 0.10)
        empty_evidence = {
            "territory": territory,
            "environmental_absence": not live_entities,
            "self_directed_structure": bool(internal.get("self_directed_structure")),
            "shared_causal_structure_available": territory_component > 0.0 and territory == "space",
        }
        yield_factor, yield_evidence = _history_yield_factor(habitat, operation, territory, [])
        score, baseline_score, components, provisional_effects = _score_affordance(
            internal, empty_evidence, consequence_dimensions, axis_profile,
            0.0, {}, yield_factor,
        )
        score += absence_component + territory_component
        baseline_score += absence_component + territory_component
        components["persistent_absence_intersection"] = absence_component
        components["territory_specific_active_structure"] = territory_component
        candidates.append(_candidate_record(
            operation=operation,
            territory=territory,
            target_ids=[],
            entity_type=None,
            parameters=parameters,
            parameter_sources=parameter_sources,
            consequence_dimensions=consequence_dimensions,
            consequence_axis_profile=axis_profile,
            entity_evidence=empty_evidence,
            score=score,
            baseline_score=baseline_score,
            score_components=components,
            provisional_effects=provisional_effects,
            internal=internal,
            yield_evidence=yield_evidence,
        ))

    # Relational actions are encountered once from each endpoint.  Their
    # canonical action identity collapses those duplicates before arbitration.
    unique: Dict[str, Dict[str, Any]] = {}
    for candidate in candidates:
        current = unique.get(candidate["candidate_id"])
        if current is None or float(candidate["relevance_score"]) > float(current["relevance_score"]):
            unique[candidate["candidate_id"]] = candidate
    result = list(unique.values())
    result.sort(key=lambda item: (-float(item["relevance_score"]), item["candidate_id"]))
    return result


# ---------------------------------------------------------------------------
# Stage E -- agency arbitration and causal closure
# ---------------------------------------------------------------------------

def select_action(
    candidates: List[Dict[str, Any]],
    *,
    min_relevance: float = MIN_RELEVANCE_TO_ENGAGE,
    rng: Optional[Any] = None,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    if not candidates:
        return None, {"reason": "no_candidates", "tie_status": "none"}
    candidate_id = lambda item: item.get("candidate_id") or _candidate_identity(item)
    top_score = max(float(candidate.get("relevance_score", 0.0)) for candidate in candidates)
    tied = [
        candidate for candidate in candidates
        if abs(float(candidate.get("relevance_score", 0.0)) - top_score) <= SCORE_EPSILON
    ]
    if top_score < min_relevance:
        top = sorted(tied, key=candidate_id)[0]
        return None, {
            "reason": "below_relevance_threshold",
            "top_candidate": top,
            "threshold": min_relevance,
            "tie_status": "equivalent_below_threshold" if len(tied) > 1 else "unique_below_threshold",
            "tied_candidate_ids": [candidate_id(candidate) for candidate in sorted(tied, key=candidate_id)],
            "neutral_stochastic_tiebreak": False,
            "preference_attributed_to_tiebreak": False,
        }

    tied = sorted(tied, key=candidate_id)
    if len(tied) == 1:
        winner = tied[0]
        tie_evidence = {
            "tie_status": "unique",
            "tied_candidate_ids": [candidate_id(winner)],
            "neutral_stochastic_tiebreak": False,
            "preference_attributed_to_tiebreak": False,
        }
    else:
        chooser = rng if rng is not None else random
        winner = chooser.choice(tied)
        tie_evidence = {
            "tie_status": "true_equivalence_neutral_stochastic",
            "tied_candidate_ids": [candidate_id(candidate) for candidate in tied],
            "neutral_stochastic_tiebreak": True,
            "preference_attributed_to_tiebreak": False,
            "neutral_winner_id": candidate_id(winner),
        }
    return winner, {
        "reason": "cleared_relevance_threshold",
        "threshold": min_relevance,
        "margin": top_score - min_relevance,
        **tie_evidence,
    }


def _top_by_score(candidates: List[Dict[str, Any]], score_key: str) -> Tuple[List[Dict[str, Any]], float]:
    if not candidates:
        return [], 0.0
    top_score = max(float(candidate.get(score_key, 0.0)) for candidate in candidates)
    tied = [
        candidate for candidate in candidates
        if abs(float(candidate.get(score_key, 0.0)) - top_score) <= SCORE_EPSILON
    ]
    tied.sort(key=lambda item: item.get("candidate_id") or _candidate_identity(item))
    return tied, top_score


def _candidate_conditioned_evaluations(
    systems: Optional[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    winner: Dict[str, Any],
) -> List[Dict[str, Any]]:
    from aurora_representational_address import RepresentationalRef
    from aurora_representational_resolution import get_or_create_engine

    engine = get_or_create_engine(systems)
    if engine is None:
        return []
    refs = sorted({
        str(effect.get("ref_encoded") or "")
        for candidate in candidates
        for effect in (candidate.get("provisional_resolution") or [])
        if effect.get("ref_encoded")
    })
    evaluations: List[Dict[str, Any]] = []
    for ref_encoded in refs:
        per_candidate_delta: Dict[str, float] = {}
        prototype: Optional[Dict[str, Any]] = None
        for candidate in candidates:
            delta = 0.0
            for effect in candidate.get("provisional_resolution") or []:
                if effect.get("ref_encoded") != ref_encoded:
                    continue
                delta += float(effect.get("score_delta", 0.0))
                prototype = prototype or effect
            per_candidate_delta[str(candidate.get("candidate_id"))] = delta
            candidate["_counterfactual_score_without_current_candidate"] = (
                float(candidate.get("relevance_score", 0.0)) - delta
            )
        if prototype is None or not any(abs(value) > SCORE_EPSILON for value in per_candidate_delta.values()):
            continue
        baseline_tied, _ = _top_by_score(candidates, "_counterfactual_score_without_current_candidate")
        conditioned_tied, _ = _top_by_score(candidates, "relevance_score")
        if winner.get("candidate_id") not in {
            candidate.get("candidate_id") for candidate in conditioned_tied
        }:
            continue
        baseline_unique = baseline_tied[0] if len(baseline_tied) == 1 else None
        conditioned_unique = conditioned_tied[0] if len(conditioned_tied) == 1 else None
        without_dimensions = sorted({
            dimension
            for candidate in baseline_tied
            for dimension in (
                candidate.get("affordance", {}).get("consequence_dimensions_affected") or []
            )
        })
        with_dimensions = sorted({
            dimension
            for candidate in conditioned_tied
            for dimension in (
                candidate.get("affordance", {}).get("consequence_dimensions_affected") or []
            )
        })
        without_parameters = dict(baseline_unique.get("parameters") or {}) if baseline_unique else {}
        with_parameters = dict(conditioned_unique.get("parameters") or {}) if conditioned_unique else {}
        affected = {
            "relevance_score_changes": {
                candidate_id: round(delta, 8)
                for candidate_id, delta in per_candidate_delta.items()
                if abs(delta) > SCORE_EPSILON
            },
            "selected_action_without_candidate": baseline_unique.get("candidate_id") if baseline_unique else None,
            "selected_action_with_candidate": conditioned_unique.get("candidate_id") if conditioned_unique else None,
            "eligible_actions_without_candidate": [item.get("candidate_id") for item in baseline_tied],
            "eligible_actions_with_candidate": [item.get("candidate_id") for item in conditioned_tied],
            "baseline_counterfactual_was_tied": len(baseline_tied) > 1,
            "conditioned_counterfactual_was_tied": len(conditioned_tied) > 1,
        }
        try:
            ref = RepresentationalRef.decode(ref_encoded)
        except Exception:
            continue
        effect_record = engine.record_candidate_downstream_effect(
            ref,
            consumer="habitat_motivation",
            downstream_difference=affected,
            action_or_prediction_affected=(
                "action_ranking" if [item.get("candidate_id") for item in baseline_tied]
                != [item.get("candidate_id") for item in conditioned_tied]
                else "candidate_relevance"
            ),
            baseline_expectation={
                "candidate_id": baseline_unique.get("candidate_id") if baseline_unique else None,
                "consequence_dimensions": without_dimensions,
                "parameters": without_parameters,
            },
            conditioned_expectation={
                "candidate_id": conditioned_unique.get("candidate_id") if conditioned_unique else None,
                "consequence_dimensions": with_dimensions,
                "parameters": with_parameters,
            },
            metadata={"all_counterfactual_candidate_ids": [item.get("candidate_id") for item in baseline_tied]},
        )
        if effect_record is None:
            continue
        effect_record.update({
            "ref_encoded": ref_encoded,
            "expected_dimensions_without_candidate": without_dimensions,
            "expected_dimensions_with_candidate": with_dimensions,
            "parameters_without_candidate": without_parameters,
            "parameters_with_candidate": with_parameters,
        })
        evaluations.append(effect_record)
    return evaluations


def _useful_distinction(
    habitat: Any,
    winner: Dict[str, Any],
    engaged: bool,
    pressure_change: Optional[Dict[str, float]],
) -> bool:
    if not engaged:
        return False
    if any(float(value) < -1e-6 for value in (pressure_change or {}).values()):
        return True
    try:
        history = habitat.get_motivation_history(limit=100)
    except Exception:
        history = []
    target_key = sorted(str(value) for value in (winner.get("target_ids") or []))
    prior_equivalent = any(
        event.get("selected_operation") == winner.get("operation")
        and event.get("selected_territory") == winner.get("territory")
        and sorted(str(value) for value in (event.get("selected_target_ids") or [])) == target_key
        for event in history
    )
    return not prior_equivalent


def _public_internal_sources(internal: Dict[str, Any]) -> Dict[str, Any]:
    public = {key: value for key, value in internal.items() if key != "resolution_context"}
    public["resolution_context"] = {
        axis: {key: value for key, value in context.items() if not key.startswith("_")}
        for axis, context in (internal.get("resolution_context") or {}).items()
    }
    return _json_safe(public)


def maybe_engage_habitat(systems: Optional[Dict[str, Any]]) -> HabitatEngagementRecord:
    habitat = (systems or {}).get("habitat")
    internal = collect_internal_motivational_state(systems)
    pressures = dict(internal.get("axis_strength") or {})
    inquiries = list(internal.get("representational_inquiries") or [])
    try:
        candidates = candidate_actions(systems)
    except Exception:
        candidates = []

    record = HabitatEngagementRecord(
        timestamp=time.time(),
        active_pressures=pressures,
        active_inquiries=inquiries,
        environmental_affordances_considered=len(candidates),
        candidate_actions=candidates,
        selected_action=None,
        selection_evidence={},
        competing_candidates=[],
        internal_sources=_public_internal_sources(internal),
    )
    if habitat is None:
        record.selection_evidence = {"reason": "no_habitat", "tie_status": "none"}
        return record

    try:
        winner, evidence = select_action(candidates)
    except Exception:
        winner, evidence = None, {"reason": "selection_error", "tie_status": "unknown"}
    record.selection_evidence = evidence
    tied_ids = set(evidence.get("tied_candidate_ids") or [])
    for candidate in candidates:
        if candidate.get("candidate_id") in tied_ids:
            candidate["tie_status"] = evidence.get("tie_status")
        candidate["selected"] = winner is candidate
        candidate["rejected"] = winner is not candidate
    record.competing_candidates = [
        {
            "candidate_id": candidate.get("candidate_id"),
            "operation": candidate.get("operation"),
            "territory": candidate.get("territory"),
            "target_ids": list(candidate.get("target_ids") or []),
            "relevance_score": candidate.get("relevance_score"),
            "tie_status": candidate.get("tie_status"),
            "selected": candidate.get("selected"),
            "rejected": candidate.get("rejected"),
        }
        for candidate in candidates
    ]
    if winner is None:
        return record

    candidate_evaluations = _candidate_conditioned_evaluations(systems, candidates, winner)
    for candidate in candidates:
        candidate["provisional_resolution"] = [
            {
                **effect,
                "actual_downstream_effect": next(
                    (
                        evaluation.get("downstream_difference_produced")
                        for evaluation in candidate_evaluations
                        if evaluation.get("ref_encoded") == effect.get("ref_encoded")
                    ),
                    None,
                ),
            }
            for effect in (candidate.get("provisional_resolution") or [])
        ]

    try:
        record.pre_state = habitat.get_state()
    except Exception:
        record.pre_state = None
    record.selected_action = winner
    causal_context = {
        "candidate_id": winner.get("candidate_id"),
        "candidate_evaluations": candidate_evaluations,
        "tie_status": evidence.get("tie_status"),
        "neutral_tiebreak": bool(evidence.get("neutral_stochastic_tiebreak")),
        "internal_pressure_before": pressures,
    }
    intention = "autonomous_engagement"
    if evidence.get("neutral_stochastic_tiebreak"):
        intention += ":neutral_equivalence_tiebreak"

    try:
        consequence = habitat.act(
            actor="aurora",
            territory=winner["territory"],
            operation=winner["operation"],
            target_ids=winner["target_ids"],
            parameters=dict(winner.get("parameters") or {}),
            intention_context=intention,
            causal_context=causal_context,
        )
        record.consequence = (
            consequence.to_dict() if hasattr(consequence, "to_dict")
            else dict(consequence or {})
        )
        record.engaged = bool(getattr(consequence, "success", False)) and bool(
            getattr(consequence, "state_changed", True)
        )
    except Exception as exc:
        record.consequence = {"error": str(exc)}
        record.engaged = False

    try:
        record.post_state = habitat.get_state()
    except Exception:
        record.post_state = None
    try:
        after_pressures = active_pressures(systems)
        record.pressure_change = {
            axis: round(after_pressures.get(axis, 0.0) - pressures.get(axis, 0.0), 6)
            for axis in set(pressures) | set(after_pressures)
        }
    except Exception:
        record.pressure_change = None
    record.useful_distinction = _useful_distinction(
        habitat, winner, record.engaged, record.pressure_change,
    )

    try:
        habitat.record_motivation_event({
            "timestamp": record.timestamp,
            "candidate_records": candidates,
            "selected_candidate_id": winner.get("candidate_id"),
            "selected_operation": winner.get("operation"),
            "selected_territory": winner.get("territory"),
            "selected_target_ids": list(winner.get("target_ids") or []),
            "selection_evidence": evidence,
            "candidate_evaluations": candidate_evaluations,
            "consequence": record.consequence,
            "pressure_change": record.pressure_change,
            "useful_distinction": record.useful_distinction,
        })
    except Exception:
        pass
    return record
