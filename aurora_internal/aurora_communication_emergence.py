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
    derive_constraint_grounded_candidate,
    derive_constraint_semantic_state,
    extract_relational_form,
    relation_alignment,
    relational_axis_vector,
)
from aurora_internal.aurora_meaning_evolution import canonical_signature
from aurora_internal.aurora_turn_persistence import batch_defer

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
_MAX_SEEN_POSSIBILITIES = 60000


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
    observation_context: str = "live"
    receiver_validation_eligible: bool = True
    possibility_evidence: Dict[str, Any] = field(default_factory=dict)

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
    applicability_shape: Dict[str, Any] = field(default_factory=dict)
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


def _applicability_similarity(
    current: Mapping[str, Any], candidate: Mapping[str, Any]
) -> float:
    """Compare two lexical-free proposition configurations.

    Exact family identity remains preferred.  This bounded similarity exists
    for configurations that differ in one still-unlearned slot (for example a
    causal unknown instead of an object unknown) while requiring the same
    root operations.  It never compares words or imports response content.
    """
    left = dict(current or {})
    right = dict(candidate or {})
    if not left or not right:
        return 0.0
    # Questions and assertions impose different agency obligations; never
    # borrow an operation across that boundary merely because their nouns fit.
    if bool(left.get("question")) != bool(right.get("question")):
        return 0.0

    weights = {
        "question": 0.22,
        "has_subject": 0.12,
        "has_relation": 0.14,
        "has_object": 0.12,
        "has_complement": 0.10,
        "has_owner": 0.06,
        "has_alternatives": 0.06,
        "negated": 0.04,
        "unresolved_references": 0.04,
    }
    score = sum(
        weight
        for key, weight in weights.items()
        if bool(left.get(key)) == bool(right.get(key))
    )
    left_unknown = str(left.get("unknown_role", "") or "")
    right_unknown = str(right.get("unknown_role", "") or "")
    if left_unknown == right_unknown:
        score += 0.10
    elif left_unknown and right_unknown:
        # Both configurations localize a missing slot even when its precise
        # role differs.  Unknown localization is the shared operation; the
        # current proposition retains the actual role.
        score += 0.06
    return round(max(0.0, min(1.0, score)), 6)


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
        self._seen_possibilities: Dict[str, float] = {}
        self._tick: int = 0
        # Historical/counterfactual observations are checkpointed by their
        # owning environment.  Suspending eager writes while one is admitted
        # keeps the communication ledger and the historical cursor on the same
        # durable boundary after an interrupted Android process.
        self._persistence_suspended: int = 0
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
        genealogy_parent_ids = [
            str(item or "")
            for item in list(family_rec.get("genealogy_supporting_ability_ids") or [])
            if str(item or "")
        ]
        lineage_parents = list(dict.fromkeys(list(parent_ids or []) + genealogy_parent_ids))[:18]
        return {
            "structural_family": family,
            "applicability_family": str(family_rec.get("applicability_family", "") or ""),
            "root_constraints": roots,
            "canonical_signature": canonical_signature(roots or AXES),
            "primitive_sequence": sequence,
            "parent_ids": lineage_parents,
            "genealogy_supporting_ability_ids": genealogy_parent_ids[:16],
            "genealogy_orientation": dict(family_rec.get("genealogy_orientation") or {}),
            "invariants": self._derive_invariants(family_rec),
            "axis_gain": {ax: round(float(root_pressure.get(ax, 0.0) or 0.0) * 0.22, 6) for ax in AXES},
            "surface_diversity_at_birth": int(len(set(family_rec.get("surface_hashes") or []))),
            "observation_count_at_birth": int(family_rec.get("count", 0) or 0),
            "origin": "persistent_constraint_communication_gap",
        }

    def _integrate_warp(self, component: WarpComponent) -> None:
        params = dict(component.parameters or {})
        family = str(params.get("structural_family", "") or "")
        family_rec = dict(self._families.get(family, {}) or {})
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
            # Warp's geometric parents and genealogy's proven operational
            # parents are both legitimate ancestry.  Preserve the cross-domain
            # lineage rather than discarding the genealogy support after it
            # influenced profile synthesis.
            parent_ids=list(dict.fromkeys(
                list(component.parent_ids or []) + list(params.get("parent_ids") or [])
            )),
            invariants=list(params.get("invariants") or []),
            axis_gain={ax: float(dict(params.get("axis_gain") or {}).get(ax, 0.0) or 0.0) for ax in AXES},
            applicability_shape=dict(family_rec.get("applicability_shape") or {}),
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

    def _possibility_activation(self, form: Mapping[str, Any]) -> Dict[str, float]:
        """Blend the present relation with proven genealogical orientation.

        The utterance configuration remains dominant.  Genealogy supplies a
        bounded orientation from previously relieved X/T/N/B/A pressure; it
        never supplies lexical content or an answer.
        """
        relation_profile = relational_axis_vector(form)
        genealogy = self.systems.get("genealogy") or getattr(self, "_warp_genealogy", None)
        orientation: Dict[str, float] = {}
        if genealogy is not None and hasattr(genealogy, "pressure_orientation"):
            try:
                orientation = {
                    ax: max(0.0, float(value or 0.0))
                    for ax, value in dict(genealogy.pressure_orientation() or {}).items()
                    if ax in AXES
                }
            except Exception:
                orientation = {}
        if not any(orientation.values()):
            return dict(relation_profile)
        genealogy_profile = _normalise_axis_profile(orientation)
        return _normalise_axis_profile({
            ax: 0.76 * float(relation_profile.get(ax, 0.0) or 0.0)
                + 0.24 * float(genealogy_profile.get(ax, 0.0) or 0.0)
            for ax in AXES
        })

    def observe_structural_possibility(
        self,
        *,
        raw_text: str,
        observed_response_text: str,
        possibility_id: str = "",
        observed_source: str = "environmental_other",
        epistemic_status: str = "observation_not_truth",
        causal_status: str = "sequence_observed_causality_not_asserted",
        defer_persistence: bool = False,
    ) -> Dict[str, Any]:
        """Let an observed exchange expose a representable communication gap.

        The observed response is held only as a *possibility*: Aurora compares
        its relational alignment with the response she can currently derive.
        It is never treated as a correct answer, copied into a candidate, or
        accepted as receiver validation.  A sufficiently clearer structural
        possibility can prove that a gap is representable and route Aurora's
        own counterfactual failure through WARP.  Only later live use and real
        receiver consequence can promote the resulting trial into genealogy.
        """
        raw = str(raw_text or "").strip()
        observed = str(observed_response_text or "").strip()
        if not raw or not observed:
            return {
                "admitted": False,
                "reason": "exchange_requires_two_nonempty_surfaces",
                "representable_gap": False,
            }

        resolved_possibility_id = str(possibility_id or "POSS:" + _stable_hash({
            "u": _surface_hash(raw),
            "o": _surface_hash(observed),
        }, 16))
        if resolved_possibility_id in self._seen_possibilities:
            return {
                "admitted": False,
                "duplicate": True,
                "reason": "possibility_already_observed",
                "possibility_id": resolved_possibility_id,
                "representable_gap": False,
            }
        self._seen_possibilities[resolved_possibility_id] = time.time()
        if len(self._seen_possibilities) > _MAX_SEEN_POSSIBILITIES:
            oldest = sorted(self._seen_possibilities, key=self._seen_possibilities.get)
            for key in oldest[: len(self._seen_possibilities) - _MAX_SEEN_POSSIBILITIES]:
                self._seen_possibilities.pop(key, None)

        if defer_persistence:
            self._persistence_suspended += 1
        try:
            form = extract_relational_form(raw)
            if not form:
                return {
                    "admitted": False,
                    "reason": "no_relational_configuration",
                    "representable_gap": False,
                }
            activation = self._possibility_activation(form)
            semantic = derive_constraint_semantic_state(
                form,
                axis_activation=activation,
                genealogy=self.systems.get("genealogy") or getattr(self, "_warp_genealogy", None),
            )
            prepared = self.prepare_semantic_state(
                semantic,
                raw_text=raw,
                axis_activation=activation,
            )
            candidate = dict(derive_constraint_grounded_candidate(prepared) or {})
            candidate_text = str(candidate.get("text", "") or "")
            candidate_alignment = relation_alignment(form, candidate_text)
            observed_alignment = relation_alignment(form, observed)
            candidate_score = _clip01(candidate_alignment.get("score", 0.0))
            observed_score = _clip01(observed_alignment.get("score", 0.0))

            # A surface is only useful as possibility evidence when it holds a
            # meaningful part of the active relation.  Its truth, helpfulness,
            # and causal role remain explicitly undecided.
            structural_support = bool(
                observed_score >= 0.55
                and not bool(observed_alignment.get("leaked_unknown_token", False))
            )
            representable_gap = bool(
                structural_support
                and (
                    not candidate_text
                    or candidate_score < 0.55
                    or observed_score - candidate_score >= 0.12
                )
            )
            active_trial = str(
                dict(prepared.get("emergent_operation") or {}).get("component_id", "") or ""
            )
            possibility = {
                "possibility_id": resolved_possibility_id,
                "observed_source": str(observed_source or "environmental_other"),
                "epistemic_status": str(epistemic_status or "observation_not_truth"),
                "causal_status": str(causal_status or "sequence_observed_causality_not_asserted"),
                "observed_surface_hash": _surface_hash(observed),
                "observed_alignment": dict(observed_alignment),
                "candidate_alignment": dict(candidate_alignment),
                "alignment_delta": round(observed_score - candidate_score, 4),
                "structural_support": structural_support,
                "representable_gap": representable_gap,
                "truth_assumed": False,
                "receiver_validation_assumed": False,
            }

            # Once a matching trial exists, each further possibility supplies
            # counterfactual performance evidence even if the trial has closed
            # the original gap.  It remains deliberately unvalidated.
            if not representable_gap and not (active_trial and structural_support):
                return {
                    "admitted": False,
                    "reason": "no_representable_constraint_gap",
                    "representable_gap": False,
                    "structural_support": structural_support,
                    "candidate_alignment": candidate_alignment,
                    "observed_alignment": observed_alignment,
                    "trial_component_id": active_trial,
                }

            rid = "COMM-POSS:" + _stable_hash({
                "id": possibility["possibility_id"],
                "proposition": prepared.get("proposition_id", ""),
            }, 18)
            result = self.observe_turn(
                semantic_state=prepared,
                raw_text=raw,
                response_text=candidate_text,
                response_source=str(candidate.get("source") or "constraint_possibility_counterfactual"),
                response_confidence=float(candidate.get("confidence", 0.0) or 0.0),
                response_id=rid,
                receiver_validation_eligible=False,
                observation_context="environmental_counterfactual",
                possibility_evidence=possibility,
                persist_response_text=False,
            )
            result.update({
                "admitted": True,
                "representable_gap": representable_gap,
                "structural_support": structural_support,
                "candidate_available": bool(candidate_text),
                "candidate_alignment": candidate_alignment,
                "observed_alignment": observed_alignment,
                "possibility_id": possibility["possibility_id"],
            })
            return result
        finally:
            if defer_persistence:
                self._persistence_suspended = max(0, self._persistence_suspended - 1)

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
        operation, operation_match = self._select_operation(form)
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
            "applicability_shape": dict(operation.applicability_shape or {}),
            "match_kind": str(operation_match.get("kind", "") or ""),
            "match_score": float(operation_match.get("score", 0.0) or 0.0),
            "current_applicability_family": applicability_family,
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
        receiver_validation_eligible: bool = True,
        observation_context: str = "live",
        possibility_evidence: Optional[Mapping[str, Any]] = None,
        persist_response_text: bool = True,
    ) -> Dict[str, Any]:
        if not str(raw_text or "").strip():
            # Boot emissions and other unaddressed articulation are not
            # communication trials.  Without a receiver proposition there is
            # no relational configuration to preserve or validate.
            return {}
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
            response_text=str(response_text or "")[:500] if persist_response_text else "",
            response_confidence=_clip01(response_confidence),
            trial_component_id=str(dict(state.get("emergent_operation") or {}).get("component_id", "") or ""),
            observation_context=str(observation_context or "live"),
            receiver_validation_eligible=bool(receiver_validation_eligible),
            possibility_evidence=dict(possibility_evidence or {}),
        )
        record = observation.to_dict()
        self._observations.append(record)
        self._observations = self._observations[-_MAX_OBSERVATIONS:]
        # Receiver validation is developmentally relevant only when a turn
        # exposed a communication gap or exercised an active trial operation.
        # Ordinary coherent turns remain in the observation history but do not
        # accumulate indefinitely in the pending validation ledger.
        if observation.receiver_validation_eligible and (deficits or observation.trial_component_id):
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
            genealogy_trace = dict(state.get("genealogy_trace") or {})
            genealogy_ids = list(family_rec.get("genealogy_supporting_ability_ids") or [])
            genealogy_ids.extend(
                str(item.get("id", "") or "")
                for item in list(genealogy_trace.get("supporting_abilities") or [])
                if isinstance(item, Mapping) and str(item.get("id", "") or "")
            )
            family_rec["genealogy_supporting_ability_ids"] = list(
                dict.fromkeys(genealogy_ids)
            )[-24:]
            family_rec["genealogy_orientation"] = dict(
                genealogy_trace.get("orientation") or {}
            )
            family_rec["genealogy_signature"] = str(
                genealogy_trace.get("canonical_signature", "") or canonical_signature(AXES)
            )
            if observation.possibility_evidence:
                family_rec["possibility_support_count"] = int(
                    family_rec.get("possibility_support_count", 0) or 0
                ) + 1
                possibility_hashes = list(family_rec.get("possibility_surface_hashes") or [])
                possibility_hash = str(
                    observation.possibility_evidence.get("observed_surface_hash", "") or ""
                )
                if possibility_hash:
                    possibility_hashes.append(possibility_hash)
                family_rec["possibility_surface_hashes"] = list(
                    dict.fromkeys(possibility_hashes)
                )[-80:]
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
                    "outcome_kind": (
                        "pending" if observation.receiver_validation_eligible
                        else "unvalidated_possibility"
                    ),
                    "receiver_score": 0.0,
                    "observation_context": observation.observation_context,
                    "possibility_evidence": dict(observation.possibility_evidence or {}),
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
            "observation_context": observation.observation_context,
            "receiver_validation_eligible": observation.receiver_validation_eligible,
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
            if str(rec.get("raw_text_hash", "") or "") == _surface_hash(""):
                continue
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
            "environmental_possibility_observations": sum(
                1 for item in self._observations
                if str(dict(item or {}).get("observation_context", "") or "")
                    == "environmental_counterfactual"
            ),
            "environmental_possibilities_seen": len(self._seen_possibilities),
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

    def _select_operation(
        self, form: Mapping[str, Any]
    ) -> Tuple[Optional[EmergentCommunicationOperation], Dict[str, Any]]:
        applicability_family = self._applicability_family(form)
        candidates = [
            op for op in self._operations.values()
            if op.applicability_family == applicability_family and op.status in {"trial", "promoted"}
        ]
        if candidates:
            candidates.sort(
                key=lambda op: (
                    op.status == "promoted",
                    len(op.evidence),
                    op.created_at,
                ),
                reverse=True,
            )
            return candidates[0], {"kind": "exact", "score": 1.0}

        current_shape = _applicability_shape(form)
        ranked: List[Tuple[float, EmergentCommunicationOperation]] = []
        for operation in self._operations.values():
            if operation.status not in {"trial", "promoted"}:
                continue
            operation_shape = dict(operation.applicability_shape or {})
            if not operation_shape:
                operation_shape = dict(
                    dict(self._families.get(operation.structural_family) or {}).get(
                        "applicability_shape"
                    )
                    or {}
                )
            score = _applicability_similarity(current_shape, operation_shape)
            if score > 0.0:
                ranked.append((score, operation))
        if not ranked:
            return None, {"kind": "none", "score": 0.0}
        ranked.sort(
            key=lambda item: (
                item[0],
                item[1].status == "promoted",
                len(item[1].evidence),
                item[1].created_at,
            ),
            reverse=True,
        )
        score, operation = ranked[0]
        if score < 0.72:
            return None, {"kind": "below_threshold", "score": score}
        return operation, {"kind": "structural_nearest", "score": score}

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
            self._profile_family = dict(raw.get("profile_family") or {})
            self._seen_possibilities = {
                str(key): float(value or 0.0)
                for key, value in dict(raw.get("seen_possibilities") or {}).items()
            }
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
                    applicability_shape=dict(
                        rec.get("applicability_shape")
                        or dict(self._families.get(str(rec.get("structural_family", "") or "")) or {}).get(
                            "applicability_shape"
                        )
                        or {}
                    ),
                    status=str(rec.get("status", "trial") or "trial"),
                    created_at=float(rec.get("created_at", time.time()) or time.time()),
                    evidence=list(rec.get("evidence") or []),
                    genealogy_ability_id=str(rec.get("genealogy_ability_id", "") or ""),
                )
                self._operations[op.component_id] = op
            self._warp_trials = {
                str(component_id): self._restore_warp_component(item)
                for component_id, item in dict(raw.get("warp_trials") or {}).items()
            }
            self._warp_promoted = {
                str(component_id): self._restore_warp_component(item)
                for component_id, item in dict(raw.get("warp_promoted") or {}).items()
            }
            self._gap_counter = {
                str(key): int(value or 0)
                for key, value in dict(raw.get("warp_gap_counter") or {}).items()
            }
            self._warp_dissolved_count = int(raw.get("warp_dissolved_count", 0) or 0)
        except Exception:
            self._operations = {}
            self._observations = []
            self._pending = {}
            self._families = {}

    @staticmethod
    def _restore_warp_component(item: Mapping[str, Any]) -> WarpComponent:
        rec = dict(item or {})
        return WarpComponent(
            component_id=str(rec.get("component_id", "") or ""),
            level=str(rec.get("level", "communication_emergence") or "communication_emergence"),
            axis_profile={str(k): float(v or 0.0) for k, v in dict(rec.get("axis_profile") or {}).items()},
            parent_ids=list(rec.get("parent_ids") or []),
            name=str(rec.get("name", "") or "") or None,
            parameters=dict(rec.get("parameters") or {}),
            trial_tick=int(rec.get("trial_tick", 0) or 0),
            trial_score_ema=float(rec.get("trial_score_ema", 0.0) or 0.0),
            promoted=bool(rec.get("promoted", False)),
            dissolved=bool(rec.get("dissolved", False)),
            created_at=float(rec.get("created_at", time.time()) or time.time()),
            sixth_axis_signal=float(rec.get("sixth_axis_signal", 0.0) or 0.0),
            topology_gap_ref=rec.get("topology_gap_ref"),
        )

    def save(self) -> bool:
        """Persist the complete communication/WARP lifecycle at a checkpoint."""
        return self._persist(force=True)

    def flush_write_batch(self) -> bool:
        """Real write for aurora_turn_persistence's end-of-turn flush."""
        return self._persist(force=True)

    def _persist(self, *, force: bool = False) -> bool:
        if not self.persist or (self._persistence_suspended > 0 and not force):
            return False
        # Turn-scoped batching (see aurora_turn_persistence).
        if not force and batch_defer(self):
            return True
        payload = {
            "schema_version": 3,
            "tick": self._tick,
            "observations": self._observations[-_MAX_OBSERVATIONS:],
            "pending": self._pending,
            "families": self._families,
            "profile_family": self._profile_family,
            "seen_possibilities": dict(self._seen_possibilities),
            "operations": {cid: op.to_dict() for cid, op in self._operations.items()},
            "warp_trials": {cid: asdict(comp) for cid, comp in self._warp_trials.items()},
            "warp_promoted": {cid: asdict(comp) for cid, comp in self._warp_promoted.items()},
            "warp_gap_counter": dict(self._gap_counter),
            "warp_dissolved_count": int(getattr(self, "_warp_dissolved_count", 0) or 0),
            "warp_status": self.warp_status(),
            "saved_at": time.time(),
        }
        try:
            Path(self.state_dir).mkdir(parents=True, exist_ok=True)
            return bool(atomic_write_json(Path(self.storage_path), payload, indent=2, default=str))
        except Exception:
            return False
