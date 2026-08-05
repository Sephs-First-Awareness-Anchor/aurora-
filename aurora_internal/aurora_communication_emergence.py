"""
aurora_communication_emergence.py
==================================

Constraint-native cultivation of communication faculties.

This module does not install finished language functions and does not classify
utterances into a prefabricated communication ontology.  It observes where a
constraint-derived proposition fails to remain coherent through a live turn,
represents that deficiency as pressure in X/T/N/B/A, and lets Aurora's existing
WARP and genealogy machinery derive, trial, promote, or dissolve a new
combinatory operation.

The developmental law is:

    unresolved relational configuration
        -> root-constraint pressure profile
        -> persistent WARP gap
        -> trial composition of existing root-derived operations
        -> varied live use
        -> receiver-validated meaning preservation
        -> genealogical promotion or dissolution

Every candidate operation remains traceable to the five roots.  No keyword,
surface phrase, or human-language intent label is allowed to become the source
of the ability.

Authors: Sunni (Sir) Morningstar and Ceph
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

from aurora_persistence_utils import atomic_write_json
from aurora_warp_protocol import (
    CoverageGap,
    WarpCapable,
    WarpComponent,
    WarpDemand,
    WarpPathway,
    WarpTrigger,
)
from aurora_internal.aurora_constraint_semantic_continuity import (
    AXES,
    DERIVED_OPERATIONS,
    bind_referential_continuity,
    derive_constraint_semantic_state,
    relation_alignment,
)
from aurora_internal.aurora_meaning_evolution import canonical_signature

_NEGATIVE_ISTATE = {
    "X": "I_ISNT",
    "T": "I_CANNOT",
    "N": "I_DONOT",
    "B": "I_SOUGHT",
    "A": "I_DIDNT",
}
_POSITIVE_ISTATE = {
    "X": "I_IS",
    "T": "I_CAN",
    "N": "I_DO",
    "B": "I_SAW",
    "A": "I_DID",
}
_RECURSION_DIMS = ("REC_SURFACE", "REC_SHALLOW", "REC_MODERATE", "REC_DEEP", "REC_CORE")

# Promotion still goes through WarpCapable's own ten-tick / EMA gate.  These
# additional minima prevent a candidate from earning a high score by repeating
# one wording or by succeeding only before receiver validation arrives.
_MIN_VALIDATED_TRIALS = 4
_MIN_DISTINCT_SURFACES = 3
_MIN_POSITIVE_RECEIVER_OUTCOMES = 2
_MAX_OBSERVATIONS = 800
_MAX_FAMILIES = 240
_MAX_PENDING = 300
_PENDING_TTL_SECONDS = 24 * 60 * 60


@dataclass
class CommunicationGapObservation:
    observation_id: str
    response_id: str
    proposition_id: str
    timestamp: float
    raw_text_hash: str
    structural_family: str
    relational_shape: Dict[str, Any]
    root_pressure: Dict[str, float]
    warp_profile: Dict[str, float]
    deficits: List[str]
    relation_alignment: Dict[str, Any]
    response_source: str
    response_text: str
    response_confidence: float
    trial_component_id: str = ""
    receiver_outcome: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EmergentCommunicationOperation:
    operation_id: str
    component_id: str
    structural_family: str
    applicability_family: str
    root_constraints: List[str]
    canonical_signature: str
    primitive_sequence: List[str]
    parent_ids: List[str]
    invariants: List[Dict[str, Any]]
    axis_gain: Dict[str, float]
    status: str = "trial"
    created_at: float = field(default_factory=time.time)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    genealogy_ability_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _clip01(value: Any, default: float = 0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except Exception:
        return default


def _stable_hash(payload: Any, length: int = 14) -> str:
    try:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    except Exception:
        raw = str(payload)
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:length]


def _normalise_axis_profile(profile: Mapping[str, Any]) -> Dict[str, float]:
    vals = {ax: max(0.0, float(dict(profile or {}).get(ax, 0.0) or 0.0)) for ax in AXES}
    total = sum(vals.values()) or 1.0
    return {ax: round(vals[ax] / total, 6) for ax in AXES}


def _surface_hash(raw_text: str) -> str:
    # Surface diversity is evidence against one-phrase overfitting.  It never
    # determines the operation itself.
    normalized = re.sub(r"\s+", " ", str(raw_text or "").strip().lower())
    return _stable_hash(normalized, 12)


def _profile_key(profile: Mapping[str, Any]) -> str:
    dims = list(_NEGATIVE_ISTATE.values()) + list(_POSITIVE_ISTATE.values()) + list(_RECURSION_DIMS)
    normalized = {dim: round(float(dict(profile or {}).get(dim, 0.0) or 0.0), 3) for dim in dims}
    return _stable_hash(normalized, 16)


def _applicability_shape(form: Mapping[str, Any]) -> Dict[str, Any]:
    rel = dict(form or {})
    return {
        "question": bool(rel.get("question")),
        "has_subject": bool(rel.get("subject")),
        "has_relation": bool(rel.get("relation")),
        "has_object": bool(rel.get("obj")),
        "has_complement": bool(rel.get("complement")),
        "unknown_role": str(rel.get("unknown_role", "") or ""),
        "has_owner": bool(rel.get("owner")),
        "has_alternatives": bool(rel.get("alternatives")),
        "negated": bool(rel.get("negated")),
        "unresolved_references": bool(rel.get("unresolved_references")),
    }


def _relational_shape(form: Mapping[str, Any], alignment: Mapping[str, Any]) -> Dict[str, Any]:
    rel = dict(form or {})
    align = dict(alignment or {})
    return {
        "question": bool(rel.get("question")),
        "has_subject": bool(rel.get("subject")),
        "has_relation": bool(rel.get("relation")),
        "has_object": bool(rel.get("obj")),
        "has_complement": bool(rel.get("complement")),
        "unknown_role": str(rel.get("unknown_role", "") or ""),
        "has_owner": bool(rel.get("owner")),
        "has_alternatives": bool(rel.get("alternatives")),
        "negated": bool(rel.get("negated")),
        "unresolved_references": bool(rel.get("unresolved_references")),
        "missing_slots": sorted(str(x) for x in list(align.get("missing_slots") or [])),
        "relation_present_in_response": bool(align.get("relation_present", False)),
        "unknown_resolved_in_response": bool(align.get("addresses_unknown", False)),
        "unknown_leaked": bool(align.get("leaked_unknown_token", False)),
    }


def _deficit_axes(
    semantic_state: Mapping[str, Any],
    alignment: Mapping[str, Any],
    response_text: str,
    response_source: str,
) -> Tuple[Dict[str, float], List[str]]:
    """Derive communication pressure directly from root obligations.

    The returned reasons describe failed root relations, not conventional NLP
    features.  They are kept for introspection and genealogy evidence.
    """
    state = dict(semantic_state or {})
    form = dict(state.get("relational_form") or {})
    obligation = dict(state.get("response_obligation") or {})
    align = dict(alignment or {})
    pressure = {ax: 0.0 for ax in AXES}
    deficits: List[str] = []

    if not form.get("subject") and not form.get("obj") and not form.get("complement"):
        pressure["X"] += 0.80
        pressure["B"] += 0.45
        deficits.append("X:B entity configuration not admitted")
    if not form.get("relation"):
        pressure["T"] += 0.45
        pressure["N"] += 0.65
        pressure["B"] += 0.65
        deficits.append("T:N:B directed relation not bound")
    if form.get("unresolved_references"):
        pressure["X"] += 0.45
        pressure["T"] += 0.90
        pressure["B"] += 0.80
        deficits.append("X:T:B referential identity did not persist")
    if not bool(align.get("relation_present", False)):
        pressure["T"] += 0.55
        pressure["N"] += 0.60
        pressure["B"] += 0.55
        deficits.append("T:N:B response lost the active relation")
    if not bool(align.get("addresses_unknown", False)):
        pressure["N"] += 0.70
        pressure["A"] += 0.85
        pressure["B"] += 0.35
        deficits.append("N:B:A response obligation remained unresolved")
    missing_slots = list(align.get("missing_slots") or [])
    if missing_slots:
        pressure["X"] += 0.50
        pressure["B"] += min(0.75, 0.25 + 0.15 * len(missing_slots))
        deficits.append("X:B proposition participants were not preserved")
    if bool(align.get("leaked_unknown_token", False)):
        pressure["B"] += 0.90
        pressure["A"] += 0.70
        deficits.append("B:A structural unknown became declarative content")

    low = str(response_text or "").strip().lower()
    source = str(response_source or "").strip().lower()
    no_authored_resolution = (
        not low
        or "don't have a clear sense" in low
        or "do not have a clear sense" in low
        or low.startswith("the recorded path began through")
        or low.startswith("active axes:")
        or "abstain" in source
    )
    if no_authored_resolution and form.get("question"):
        pressure["A"] += 0.75
        pressure["N"] += 0.45
        deficits.append("N:A no selected resolution crossed into expression")

    completeness = _clip01(state.get("completeness", 0.0))
    if completeness < 0.75:
        pressure["X"] += (0.75 - completeness) * 0.8
        pressure["B"] += (0.75 - completeness) * 0.8
        deficits.append("X:B proposition boundary remained incomplete")

    # If there is no demonstrated gap, preserve a zero vector.  A candidate is
    # never cultivated merely because a turn exists.
    if not deficits:
        return {ax: 0.0 for ax in AXES}, []
    return _normalise_axis_profile(pressure), list(dict.fromkeys(deficits))


def _warp_profile(root_pressure: Mapping[str, Any], structural_shape: Mapping[str, Any]) -> Dict[str, float]:
    """Lift a five-root deficiency into WARP's native 15D coverage space."""
    root = _normalise_axis_profile(root_pressure)
    profile: Dict[str, float] = {}
    for ax in AXES:
        magnitude = float(root.get(ax, 0.0) or 0.0)
        profile[_NEGATIVE_ISTATE[ax]] = round(magnitude, 6)
        # A small affirmative component preserves which existing law is being
        # pressured rather than treating pressure as a new primitive.
        profile[_POSITIVE_ISTATE[ax]] = round(magnitude * 0.18, 6)

    shape = dict(structural_shape or {})
    profile["REC_SURFACE"] = 0.35 if shape.get("unknown_leaked") else 0.10
    profile["REC_SHALLOW"] = 0.50 if shape.get("unresolved_references") else 0.20
    profile["REC_MODERATE"] = 0.55 if not shape.get("relation_present_in_response") else 0.20
    profile["REC_DEEP"] = 0.65 if shape.get("missing_slots") else 0.30
    profile["REC_CORE"] = 0.60 if not shape.get("unknown_resolved_in_response") else 0.20
    return profile


def _minimal_primitive_cover(axes: Iterable[str]) -> List[str]:
    remaining = set(str(ax).upper() for ax in axes if str(ax).upper() in AXES)
    if not remaining:
        return ["proposition_understanding"]
    selected: List[str] = []
    candidates = []
    for name, spec in DERIVED_OPERATIONS.items():
        roots = set(str(ax).upper() for ax in list(spec.get("axes") or []))
        if name == "proposition_understanding":
            continue
        candidates.append((name, roots))
    while remaining:
        ranked = sorted(
            candidates,
            key=lambda item: (
                len(item[1] & remaining),
                -len(item[1] - remaining),
                -len(item[1]),
            ),
            reverse=True,
        )
        name, roots = ranked[0]
        if not (roots & remaining):
            break
        selected.append(name)
        remaining -= roots
        candidates = [item for item in candidates if item[0] != name]
        if not candidates:
            break
    selected.append("proposition_understanding")
    return list(dict.fromkeys(selected))


class AuroraCommunicationEmergence(WarpCapable):
    """Cultivates missing communication operations through Aurora's roots."""

    def __init__(
        self,
        *,
        state_dir: str = "aurora_state",
        persist: bool = True,
        genealogy: Any = None,
    ) -> None:
        self.state_dir = str(state_dir or "aurora_state")
        self.persist = bool(persist)
        self.storage_path = os.path.join(self.state_dir, "communication_emergence_state.json")
        self.systems: Dict[str, Any] = {}
        self._operations: Dict[str, EmergentCommunicationOperation] = {}
        self._observations: List[Dict[str, Any]] = []
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._families: Dict[str, Dict[str, Any]] = {}
        self._profile_family: Dict[str, str] = {}
        self._tick: int = 0
        self._init_warp(genealogy=genealogy)
        self._load()

    def attach_systems(self, systems: Mapping[str, Any]) -> None:
        self.systems = dict(systems or {}) if not isinstance(systems, dict) else systems
        genealogy = self.systems.get("genealogy")
        if genealogy is not None:
            self.set_warp_genealogy(genealogy)
        sedi = self.systems.get("sedimemory")
        if sedi is not None:
            try:
                self.connect_sedimemory(sedi)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # WarpCapable implementation
    # ------------------------------------------------------------------

    def _warp_level_name(self) -> str:
        return "communication_emergence"

    def _get_axis_profiles(self) -> Dict[str, Dict[str, float]]:
        # Root-pressure primitives are negative I-state forms of the same five
        # laws.  Pair/compound gaps are therefore derivable rather than treated
        # as evidence of a sixth primitive.
        profiles: Dict[str, Dict[str, float]] = {}
        for ax in AXES:
            for depth in ("REC_SHALLOW", "REC_MODERATE", "REC_DEEP", "REC_CORE"):
                profiles[f"root_pressure:{ax}:{depth}"] = {
                    _NEGATIVE_ISTATE[ax]: 1.0,
                    _POSITIVE_ISTATE[ax]: 0.15,
                    depth: 0.70,
                }
        for op in self._operations.values():
            if op.status == "promoted":
                comp = self._warp_promoted.get(op.component_id)
                if comp is not None:
                    profiles[op.component_id] = dict(comp.axis_profile)
        return profiles

    def _warp_params(self, gap: CoverageGap, parent_ids: List[str]) -> Dict[str, Any]:
        profile_key = _profile_key(gap.axis_profile)
        family = self._profile_family.get(profile_key, "")
        family_rec = dict(self._families.get(family, {}) or {})
        root_pressure = dict(family_rec.get("root_pressure") or {})
        roots = [ax for ax in AXES if float(root_pressure.get(ax, 0.0) or 0.0) >= 0.12]
        if not roots:
            # Recover ancestry from negative I-state coordinates if the runtime
            # was restored without the ephemeral profile index.
            roots = [ax for ax in AXES if float(gap.axis_profile.get(_NEGATIVE_ISTATE[ax], 0.0) or 0.0) > 0.10]
        sequence = _minimal_primitive_cover(roots)
        return {
            "structural_family": family,
            "applicability_family": str(family_rec.get("applicability_family", "") or ""),
            "root_constraints": roots,
            "canonical_signature": canonical_signature(roots or AXES),
            "primitive_sequence": sequence,
            "parent_ids": list(parent_ids or []),
            "invariants": self._derive_invariants(family_rec),
            "axis_gain": {ax: round(float(root_pressure.get(ax, 0.0) or 0.0) * 0.22, 6) for ax in AXES},
            "surface_diversity_at_birth": int(len(set(family_rec.get("surface_hashes") or []))),
            "observation_count_at_birth": int(family_rec.get("count", 0) or 0),
            "origin": "persistent_constraint_communication_gap",
        }

    def _integrate_warp(self, component: WarpComponent) -> None:
        params = dict(component.parameters or {})
        family = str(params.get("structural_family", "") or "")
        op_id = "COMM:" + _stable_hash(
            {
                "component": component.component_id,
                "family": family,
                "sequence": params.get("primitive_sequence", []),
            },
            14,
        )
        operation = EmergentCommunicationOperation(
            operation_id=op_id,
            component_id=component.component_id,
            structural_family=family,
            applicability_family=str(params.get("applicability_family", "") or ""),
            root_constraints=list(params.get("root_constraints") or []),
            canonical_signature=str(params.get("canonical_signature", "") or canonical_signature(AXES)),
            primitive_sequence=list(params.get("primitive_sequence") or []),
            parent_ids=list(component.parent_ids or []),
            invariants=list(params.get("invariants") or []),
            axis_gain={ax: float(dict(params.get("axis_gain") or {}).get(ax, 0.0) or 0.0) for ax in AXES},
        )
        self._operations[component.component_id] = operation
        self._persist()

    def _score_trial(self, component: WarpComponent) -> float:
        operation = self._operations.get(component.component_id)
        if operation is None:
            return 0.0
        evidence = [dict(e or {}) for e in operation.evidence]
        validated = [e for e in evidence if e.get("validated")]
        surfaces = {str(e.get("surface_hash", "") or "") for e in validated if e.get("surface_hash")}
        positive = [e for e in validated if str(e.get("outcome_kind", "") or "") == "positive"]
        negative = [e for e in validated if str(e.get("outcome_kind", "") or "") == "negative"]
        if (
            len(validated) < _MIN_VALIDATED_TRIALS
            or len(surfaces) < _MIN_DISTINCT_SURFACES
            or len(positive) < _MIN_POSITIVE_RECEIVER_OUTCOMES
        ):
            return 0.34
        alignment = sum(_clip01(e.get("relation_alignment", 0.0)) for e in validated) / max(1, len(validated))
        receiver = sum(_clip01(e.get("receiver_score", 0.0)) for e in validated) / max(1, len(validated))
        regression_penalty = min(0.55, 0.18 * len(negative))
        overfit_penalty = 0.0 if len(surfaces) >= max(3, len(validated) // 2) else 0.10
        score = 0.52 * alignment + 0.48 * receiver - regression_penalty - overfit_penalty
        return _clip01(score)

    def _dissolve_warp(self, component_id: str) -> None:
        operation = self._operations.get(component_id)
        if operation is not None:
            operation.status = "dissolved"
        self._persist()

    # ------------------------------------------------------------------
    # Structural observation and trial influence
    # ------------------------------------------------------------------

    def prepare_semantic_state(
        self,
        semantic_state: Mapping[str, Any],
        *,
        raw_text: str = "",
        referent_map: Optional[Mapping[str, Any]] = None,
        claim_resolution: Optional[Mapping[str, Any]] = None,
        meaning_forms: Optional[Sequence[Mapping[str, Any]]] = None,
        axis_activation: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Apply a matching trial as a temporary constraint-derived bias.

        The trial may preserve or rebind structural information, change root
        emphasis, and strengthen invariants.  It may not install an answer or
        branch on a surface phrase.
        """
        state = copy.deepcopy(dict(semantic_state or {}))
        form = dict(state.get("relational_form") or {})
        if not form:
            return state
        provisional_alignment = {
            "missing_slots": [],
            "relation_present": bool(form.get("relation")),
            "addresses_unknown": not bool(form.get("question")),
            "leaked_unknown_token": False,
        }
        shape = _relational_shape(form, provisional_alignment)
        applicability_family = self._applicability_family(form)
        operation = self._select_operation(applicability_family)
        if operation is None:
            return state

        relation = dict(form)
        if "reference_continuity" in operation.primitive_sequence:
            relation = bind_referential_continuity(relation, referent_map=referent_map)

        activation = {
            ax: max(0.0, float(dict(axis_activation or state.get("axis_activation") or {}).get(ax, 0.0) or 0.0))
            for ax in AXES
        }
        for ax, gain in operation.axis_gain.items():
            activation[ax] = activation.get(ax, 0.0) + max(0.0, float(gain or 0.0))
        activation = _normalise_axis_profile(activation)

        rebuilt = derive_constraint_semantic_state(
            relation,
            axis_activation=activation,
            genealogy=self.systems.get("genealogy"),
            referent_map=referent_map,
            claim_resolution=claim_resolution,
            meaning_forms=meaning_forms,
        )
        obligation = dict(rebuilt.get("response_obligation") or {})
        preserve = list(obligation.get("must_preserve") or [])
        for invariant in operation.invariants:
            inv = dict(invariant or {})
            slot = str(inv.get("slot", "") or "").strip()
            value = str(relation.get(slot, "") or "").strip() if slot else ""
            if value and value not in preserve:
                preserve.append(value)
        obligation["must_preserve"] = preserve
        obligation["emergent_operation_id"] = operation.operation_id
        obligation["emergent_operation_signature"] = operation.canonical_signature
        rebuilt["response_obligation"] = obligation
        rebuilt["emergent_operation"] = {
            "operation_id": operation.operation_id,
            "component_id": operation.component_id,
            "status": operation.status,
            "primitive_sequence": list(operation.primitive_sequence),
            "root_constraints": list(operation.root_constraints),
            "canonical_signature": operation.canonical_signature,
            "structural_family": operation.structural_family,
            "applicability_family": operation.applicability_family,
        }
        return rebuilt

    def observe_turn(
        self,
        *,
        semantic_state: Mapping[str, Any],
        raw_text: str,
        response_text: str,
        response_source: str,
        response_confidence: float,
        response_id: str = "",
    ) -> Dict[str, Any]:
        state = dict(semantic_state or {})
        form = dict(state.get("relational_form") or {})
        if not form:
            return {}
        alignment = relation_alignment(form, response_text)
        root_pressure, deficits = _deficit_axes(state, alignment, response_text, response_source)
        shape = _relational_shape(form, alignment)
        applicability_family = self._applicability_family(form)
        family = self._structural_family({
            "applicability_family": applicability_family,
            "root_deficits": [ax for ax in AXES if float(root_pressure.get(ax, 0.0) or 0.0) >= 0.12],
            "missing_slots": list(shape.get("missing_slots") or []),
            "relation_present_in_response": bool(shape.get("relation_present_in_response")),
            "unknown_resolved_in_response": bool(shape.get("unknown_resolved_in_response")),
            "unknown_leaked": bool(shape.get("unknown_leaked")),
        })
        rid = str(response_id or "COMM-R:" + _stable_hash({"t": time.time(), "text": response_text}, 16))
        observation = CommunicationGapObservation(
            observation_id="CGO:" + _stable_hash({"r": rid, "p": state.get("proposition_id"), "t": time.time()}, 14),
            response_id=rid,
            proposition_id=str(state.get("proposition_id", "") or ""),
            timestamp=time.time(),
            raw_text_hash=_surface_hash(raw_text),
            structural_family=family,
            relational_shape=shape,
            root_pressure=root_pressure,
            warp_profile=_warp_profile(root_pressure, shape) if deficits else {},
            deficits=deficits,
            relation_alignment=alignment,
            response_source=str(response_source or ""),
            response_text=str(response_text or "")[:500],
            response_confidence=_clip01(response_confidence),
            trial_component_id=str(dict(state.get("emergent_operation") or {}).get("component_id", "") or ""),
        )
        record = observation.to_dict()
        self._observations.append(record)
        self._observations = self._observations[-_MAX_OBSERVATIONS:]
        # Receiver validation is developmentally relevant only when a turn
        # exposed a communication gap or exercised an active trial operation.
        # Ordinary coherent turns remain in the observation history but do not
        # accumulate indefinitely in the pending validation ledger.
        if deficits or observation.trial_component_id:
            self._pending[rid] = record
            self._prune_pending()

        if deficits:
            family_rec = dict(self._families.get(family, {}) or {})
            family_rec["count"] = int(family_rec.get("count", 0) or 0) + 1
            family_rec["root_pressure"] = dict(root_pressure)
            family_rec["relational_shape"] = dict(shape)
            family_rec["applicability_family"] = applicability_family
            family_rec["applicability_shape"] = _applicability_shape(form)
            hashes = list(family_rec.get("surface_hashes") or [])
            hashes.append(observation.raw_text_hash)
            family_rec["surface_hashes"] = list(dict.fromkeys(hashes))[-80:]
            family_rec["last_seen"] = time.time()
            family_rec["last_deficits"] = list(deficits)
            self._families[family] = family_rec
            if len(self._families) > _MAX_FAMILIES:
                oldest = sorted(self._families, key=lambda key: float(self._families[key].get("last_seen", 0.0) or 0.0))
                for key in oldest[: len(self._families) - _MAX_FAMILIES]:
                    self._families.pop(key, None)

            profile_key = _profile_key(observation.warp_profile)
            self._profile_family[profile_key] = family
            self._submit_gap(observation)

        if observation.trial_component_id:
            operation = self._operations.get(observation.trial_component_id)
            if operation is not None:
                operation.evidence.append({
                    "observation_id": observation.observation_id,
                    "response_id": rid,
                    "surface_hash": observation.raw_text_hash,
                    "relation_alignment": float(alignment.get("score", 0.0) or 0.0),
                    "validated": False,
                    "outcome_kind": "pending",
                    "receiver_score": 0.0,
                })
                operation.evidence = operation.evidence[-160:]

        self._tick += 1
        self._persist()
        return {
            "response_id": rid,
            "observation_id": observation.observation_id,
            "structural_family": family,
            "applicability_family": applicability_family,
            "root_pressure": root_pressure,
            "deficits": deficits,
            "relation_alignment": alignment,
            "trial_component_id": observation.trial_component_id,
            "warp_status": self.warp_status(),
        }

    def _prune_pending(self) -> None:
        """Bound receiver-validation state without discarding live trials.

        Pending entries are ephemeral bridges between one Aurora response and
        the receiver's next turn.  They are not long-term memory.  Expired
        entries and the oldest overflow are removed so an unattended dialogue
        cannot turn the developmental ledger into an ever-growing transcript.
        """
        now = time.time()
        live: Dict[str, Dict[str, Any]] = {}
        for response_id, item in dict(self._pending or {}).items():
            rec = dict(item or {})
            timestamp = float(rec.get("timestamp", 0.0) or 0.0)
            if timestamp > 0.0 and now - timestamp > _PENDING_TTL_SECONDS:
                continue
            live[str(response_id)] = rec
        if len(live) > _MAX_PENDING:
            ordered = sorted(
                live.items(),
                key=lambda pair: float(dict(pair[1] or {}).get("timestamp", 0.0) or 0.0),
            )
            live = dict(ordered[-_MAX_PENDING:])
        self._pending = live

    def record_receiver_outcome(self, response_id: str, outcome: Mapping[str, Any]) -> Dict[str, Any]:
        rid = str(response_id or "")
        observation = self._pending.pop(rid, None)
        if observation is None:
            return {"matched": False, "response_id": rid}
        receiver = dict(outcome or {})
        observation["receiver_outcome"] = {
            "outcome_kind": str(receiver.get("outcome_kind", "") or "indeterminate"),
            "score": _clip01(receiver.get("score", 0.0)),
            "observed_effect": str(receiver.get("observed_effect", "") or ""),
            "label": str(receiver.get("label", "") or ""),
            "meaning_issue": bool(receiver.get("meaning_issue", False)),
            "expression_issue": bool(receiver.get("expression_issue", False)),
        }
        for idx in range(len(self._observations) - 1, -1, -1):
            if str(self._observations[idx].get("response_id", "") or "") == rid:
                self._observations[idx] = dict(observation)
                break

        component_id = str(observation.get("trial_component_id", "") or "")
        operation = self._operations.get(component_id)
        if operation is not None:
            for evidence in reversed(operation.evidence):
                if str(evidence.get("response_id", "") or "") == rid:
                    evidence["validated"] = True
                    evidence["outcome_kind"] = str(receiver.get("outcome_kind", "") or "indeterminate")
                    evidence["receiver_score"] = _clip01(receiver.get("score", 0.0))
                    evidence["observed_effect"] = str(receiver.get("observed_effect", "") or "")
                    break

        promoted, dissolved = self.evaluate_development()
        self._persist()
        return {
            "matched": True,
            "response_id": rid,
            "trial_component_id": component_id,
            "promoted": promoted,
            "dissolved": dissolved,
        }

    def evaluate_development(self) -> Tuple[List[str], List[str]]:
        promoted, dissolved = self.evaluate_warp_trials()
        for component_id in promoted:
            operation = self._operations.get(component_id)
            if operation is None:
                continue
            operation.status = "promoted"
            operation.genealogy_ability_id = self._register_genealogy(operation, self._warp_promoted.get(component_id))
        for component_id in dissolved:
            operation = self._operations.get(component_id)
            if operation is not None:
                operation.status = "dissolved"
        return promoted, dissolved

    # ------------------------------------------------------------------
    # Queries / introspection
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        return {
            "observations": len(self._observations),
            "pending_receiver_validation": len(self._pending),
            "gap_families": len(self._families),
            "trial_operations": sum(1 for op in self._operations.values() if op.status == "trial"),
            "promoted_operations": sum(1 for op in self._operations.values() if op.status == "promoted"),
            "dissolved_operations": sum(1 for op in self._operations.values() if op.status == "dissolved"),
            "warp": self.warp_status(),
            "storage_path": self.storage_path,
        }

    def latest_gap(self) -> Dict[str, Any]:
        return copy.deepcopy(self._observations[-1]) if self._observations else {}

    def active_operations(self) -> List[Dict[str, Any]]:
        return [op.to_dict() for op in self._operations.values() if op.status in {"trial", "promoted"}]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _structural_family(self, shape: Mapping[str, Any]) -> str:
        # The family contains no lexical content.  Two different sentences that
        # produce the same relational deficiency exert pressure on the same
        # developmental region.
        return "CFAM:" + _stable_hash(dict(shape or {}), 14)

    def _derive_invariants(self, family_rec: Mapping[str, Any]) -> List[Dict[str, Any]]:
        shape = dict(dict(family_rec or {}).get("relational_shape") or {})
        invariants: List[Dict[str, Any]] = []
        if shape.get("has_subject"):
            invariants.append({"root": "X:B", "kind": "preserve_subject_identity", "slot": "subject"})
        if shape.get("has_relation"):
            invariants.append({"root": "T:N:B", "kind": "preserve_directed_relation", "slot": "relation"})
        if shape.get("has_object"):
            invariants.append({"root": "X:B", "kind": "preserve_object_identity", "slot": "obj"})
        if shape.get("has_complement"):
            invariants.append({"root": "X:N:B", "kind": "preserve_resulting_quality", "slot": "complement"})
        if shape.get("unknown_role"):
            invariants.append({"root": "X:B:A", "kind": "resolve_unknown_without_speaking_marker", "unknown_role": shape["unknown_role"]})
        if shape.get("unresolved_references"):
            invariants.append({"root": "X:T:B", "kind": "maintain_referential_continuity", "slot": "referent"})
        return invariants

    def _applicability_family(self, form: Mapping[str, Any]) -> str:
        return "CAFAM:" + _stable_hash(_applicability_shape(form), 14)

    def _select_operation(self, applicability_family: str) -> Optional[EmergentCommunicationOperation]:
        candidates = [
            op for op in self._operations.values()
            if op.applicability_family == applicability_family and op.status in {"trial", "promoted"}
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda op: (op.status == "promoted", len(op.evidence), op.created_at), reverse=True)
        return candidates[0]

    def _submit_gap(self, observation: CommunicationGapObservation) -> None:
        if not observation.warp_profile:
            return
        warp_field = self.systems.get("warp_field")
        demand = WarpDemand(
            source="communication_emergence",
            layer="constraint_semantic_continuity",
            trigger=WarpTrigger.GAP,
            unresolved_text="; ".join(observation.deficits)[:600],
            expected={
                "proposition_id": observation.proposition_id,
                "relation_alignment": 1.0,
                "root_signature": canonical_signature(AXES),
            },
            actual={
                "relation_alignment": observation.relation_alignment,
                "relational_shape": observation.relational_shape,
            },
            participants=["constraint_semantics", "genealogy", "expression", "receiver_validation"],
            profile=dict(observation.warp_profile),
            local_attempts=["constraint_semantic_derivation", "relation_alignment_audit"],
            # This is a known five-root deficiency, not a sixth-axis claim.
            severity=min(0.88, _clip01(1.0 - float(observation.relation_alignment.get("score", 0.0) or 0.0) + 0.18)),
            persistence_key=observation.structural_family,
        )
        if warp_field is not None and hasattr(warp_field, "submit"):
            try:
                warp_field.submit(demand)
                return
            except Exception:
                pass
        # Isolated tests and degraded boots can still use the same WarpCapable
        # lifecycle without the universal router.
        self.check_and_extend(
            observation.warp_profile,
            source="communication_emergence",
            tick=self._tick,
        )

    def _register_genealogy(
        self,
        operation: EmergentCommunicationOperation,
        component: Optional[WarpComponent],
    ) -> str:
        genealogy = self.systems.get("genealogy") or getattr(self, "_warp_genealogy", None)
        if genealogy is None:
            return ""
        payload = {
            "operation_id": operation.operation_id,
            "component_id": operation.component_id,
            "constraints": list(operation.root_constraints),
            "canonical_signature": operation.canonical_signature,
            "primitive_sequence": list(operation.primitive_sequence),
            "parent_ids": list(operation.parent_ids),
            "invariants": list(operation.invariants),
            "trial_score": float(getattr(component, "trial_score_ema", 0.0) or 0.0),
            "evidence_count": len(operation.evidence),
            "distinct_surfaces": len({str(e.get("surface_hash", "") or "") for e in operation.evidence if e.get("surface_hash")}),
            "structural_family": operation.structural_family,
        }
        if hasattr(genealogy, "register_emergent_communication_operation"):
            try:
                result = dict(genealogy.register_emergent_communication_operation(payload) or {})
                return str(result.get("ability_id", "") or "")
            except Exception:
                return ""
        return ""

    def _load(self) -> None:
        if not self.persist or not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as handle:
                raw = dict(json.load(handle) or {})
            self._observations = list(raw.get("observations") or [])[-_MAX_OBSERVATIONS:]
            self._pending = dict(raw.get("pending") or {})
            self._prune_pending()
            self._families = dict(raw.get("families") or {})
            self._tick = int(raw.get("tick", 0) or 0)
            for component_id, item in dict(raw.get("operations") or {}).items():
                rec = dict(item or {})
                op = EmergentCommunicationOperation(
                    operation_id=str(rec.get("operation_id", "") or ""),
                    component_id=str(rec.get("component_id", component_id) or component_id),
                    structural_family=str(rec.get("structural_family", "") or ""),
                    applicability_family=str(rec.get("applicability_family", "") or ""),
                    root_constraints=list(rec.get("root_constraints") or []),
                    canonical_signature=str(rec.get("canonical_signature", "") or canonical_signature(AXES)),
                    primitive_sequence=list(rec.get("primitive_sequence") or []),
                    parent_ids=list(rec.get("parent_ids") or []),
                    invariants=list(rec.get("invariants") or []),
                    axis_gain={ax: float(dict(rec.get("axis_gain") or {}).get(ax, 0.0) or 0.0) for ax in AXES},
                    status=str(rec.get("status", "trial") or "trial"),
                    created_at=float(rec.get("created_at", time.time()) or time.time()),
                    evidence=list(rec.get("evidence") or []),
                    genealogy_ability_id=str(rec.get("genealogy_ability_id", "") or ""),
                )
                self._operations[op.component_id] = op
        except Exception:
            self._operations = {}
            self._observations = []
            self._pending = {}
            self._families = {}

    def _persist(self) -> None:
        if not self.persist:
            return
        payload = {
            "schema_version": 1,
            "tick": self._tick,
            "observations": self._observations[-_MAX_OBSERVATIONS:],
            "pending": self._pending,
            "families": self._families,
            "operations": {cid: op.to_dict() for cid, op in self._operations.items()},
            "warp_status": self.warp_status(),
            "saved_at": time.time(),
        }
        try:
            Path(self.state_dir).mkdir(parents=True, exist_ok=True)
            atomic_write_json(Path(self.storage_path), payload, indent=2, default=str)
        except Exception:
            pass
