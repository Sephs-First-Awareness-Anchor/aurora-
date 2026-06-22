#!/usr/bin/env python3
"""
Runtime understanding contract.

This module makes Aurora's live dialogue loop explicit in the form:

    M_t -> P_t -> U_t -> O_{t+1} -> A_{t+1} -> M_{t+1}, Pi_{t+1}

Where:
    M = meaning structure bounded by current boundary state
    P = situated perspective
    U = outward application / response policy
    O = observed next turn / resulting input
    A = accuracy of fit between predicted and observed continuation

The contract is not a separate cognition system. It is a runtime accounting
layer that derives its state from Aurora's actual working memory, emotional
signals, articulation debt, contradiction state, and current response policy.
Every operator it uses is registered into the five-constraint genealogy.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import time
from typing import Any, Dict, List, Optional

_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")

from aurora_internal.constraint_genealogy import (
    AbilityProfile,
    PressureVec,
    TraceItem,
    _augment_ability_profile_with_origin,
)
from aurora_internal.aurora_meaning_evolution import (
    DEVELOPMENTAL_CHAIN as _DEV_CHAIN,
    assess_developmental_stage as _assess_dev_stage,
    axis_profiles as _axis_meaning_profiles,
    rank_meaning_profiles as _rank_meaning_profiles,
)

AXES = ("X", "T", "N", "B", "A")
ALPHA = 0.35
BETA = 0.28
LAMBDA = 0.22
MAX_HISTORY = 240


def _clip01(value: Any, default: float = 0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value or 0.0)))
    except Exception:
        return max(0.0, min(1.0, float(default or 0.0)))


def _mean(values: List[float], default: float = 0.0) -> float:
    clean = [float(v) for v in values if isinstance(v, (int, float))]
    if not clean:
        return float(default or 0.0)
    return sum(clean) / float(len(clean))


def _terms(text: Any) -> List[str]:
    return re.findall(r"[a-z0-9]{3,}", str(text or "").lower())


def _term_overlap(left: List[str], right: List[str]) -> float:
    lset = set(left or [])
    rset = set(right or [])
    if not lset or not rset:
        return 0.0
    return len(lset & rset) / float(max(1, len(lset | rset)))


def _hash_payload(payload: Dict[str, Any]) -> str:
    try:
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    except Exception:
        blob = repr(payload)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:12]


class RuntimeUnderstandingContract:
    _ABILITY_SPECS = (
        AbilityProfile(
            id="X:MAINTAIN_UNDERSTANDING_EXISTENCE",
            axis="X",
            requires=("X", "T", "B"),
            cost={"X": 0.01, "T": 0.01, "N": 0.01, "B": 0.01, "A": 0.0},
            risk={"X": 0.01, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0},
            effect_tags=(
                "continuity_persistence",
                "runtime_state_maintenance",
                "meaning_survival",
            ),
            notes=(
                "Preserve a coherent runtime state across turns so meaning and "
                "policy survive long enough to be corrected rather than reset."
            ),
        ),
        AbilityProfile(
            id="T:SEQUENCE_UNDERSTANDING_TRANSITIONS",
            axis="T",
            requires=("X", "T", "B"),
            cost={"X": 0.0, "T": 0.02, "N": 0.01, "B": 0.01, "A": 0.01},
            risk={"X": 0.0, "T": 0.01, "N": 0.0, "B": 0.0, "A": 0.0},
            effect_tags=(
                "turn_sequencing",
                "observation_application_loop",
                "transition_stability",
            ),
            notes=(
                "Sequence observation, application, and correction as one "
                "continuous temporal loop instead of isolated turns."
            ),
        ),
        AbilityProfile(
            id="N:WEIGH_UNDERSTANDING_COST",
            axis="N",
            requires=("T", "N", "B", "A"),
            cost={"X": 0.0, "T": 0.01, "N": 0.03, "B": 0.01, "A": 0.01},
            risk={"X": 0.0, "T": 0.0, "N": 0.01, "B": 0.0, "A": 0.0},
            effect_tags=(
                "coherence_cost",
                "articulation_cost",
                "contradiction_cost",
                "policy_weighting",
            ),
            notes=(
                "Measure the runtime cost of speaking, clarifying, contradicting, "
                "or outsourcing articulation so policy can adapt under pressure."
            ),
        ),
        AbilityProfile(
            id="B:BOUND_MEANING_AND_PERSPECTIVE",
            axis="B",
            requires=("X", "B", "A"),
            cost={"X": 0.0, "T": 0.01, "N": 0.01, "B": 0.03, "A": 0.01},
            risk={"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.01, "A": 0.0},
            effect_tags=(
                "meaning_boundary",
                "speaker_ownership",
                "perspective_separation",
                "referent_bounding",
            ),
            notes=(
                "Bound meaning inside the correct speaker, referent, and "
                "self/world frame so Aurora does not flatten perspective."
            ),
        ),
        AbilityProfile(
            id="A:VALIDATE_UNDERSTANDING_ACCURACY",
            axis="A",
            requires=("T", "N", "B", "A"),
            cost={"X": 0.0, "T": 0.01, "N": 0.01, "B": 0.01, "A": 0.03},
            risk={"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.01},
            effect_tags=(
                "outcome_validation",
                "accuracy_correction",
                "policy_revision",
                "meaning_update",
            ),
            notes=(
                "Judge whether outward application fit the resulting turn and "
                "feed that accuracy back into meaning and policy."
            ),
        ),
        AbilityProfile(
            id="CONTRACT:COHERENCE_GUARD",
            axis="T",
            requires=("T", "X", "B"),
            cost={"X": 0.0, "T": 0.02, "N": 0.02, "B": 0.02, "A": 0.0},
            risk={"X": 0.0, "T": 0.01, "N": 0.0, "B": 0.01, "A": 0.0},
            effect_tags=(
                "referent_continuity",
                "conflict_stability",
                "topic_carryover",
                "causal_thread",
            ),
            notes=(
                "Promote identity and causal continuity across turns while "
                "penalizing fragmentation or drift in the thread."
            ),
        ),
        AbilityProfile(
            id="CONTRACT:COMMUNICATION_SEAM",
            axis="B",
            requires=("B", "N", "A"),
            cost={"X": 0.0, "T": 0.01, "N": 0.02, "B": 0.03, "A": 0.02},
            risk={"X": 0.0, "T": 0.0, "N": 0.01, "B": 0.01, "A": 0.01},
            effect_tags=(
                "articulation_fidelity",
                "signal_preservation",
                "expression_structure",
            ),
            notes=(
                "Ensure what is carried inside is rendered outward without losing "
                "structure, penalizing distortion that just sounds plausible."
            ),
        ),
        AbilityProfile(
            id="CONTRACT:INTELLIGENCE_EVOLUTION",
            axis="N",
            requires=("N", "T", "A"),
            cost={"X": 0.0, "T": 0.02, "N": 0.03, "B": 0.01, "A": 0.02},
            risk={"X": 0.0, "T": 0.01, "N": 0.01, "B": 0.0, "A": 0.01},
            effect_tags=(
                "adaptive_gain",
                "pressure_relief",
                "generalization",
                "manifold_navigation",
            ),
            notes=(
                "Reward structure-preserving adaptation under pressure and penalize "
                "shallow wins that don't deepen the organism."
            ),
        ),
    )

    def __init__(
        self,
        *,
        state_dir: str = _STATE_ROOT,
        storage_path: Optional[str] = None,
        persist: bool = True,
    ) -> None:
        self.state_dir = os.path.abspath(state_dir)
        self.storage_path = storage_path or os.path.join(
            self.state_dir, "understanding_contract_state.json"
        )
        self.persist = bool(persist)
        self._abilities_registered = False
        self.state: Dict[str, Any] = self._default_state()
        self._load()

    def _default_state(self) -> Dict[str, Any]:
        return {
            "time_index": 0,
            "X": {
                "continuity": 0.5,
                "memory_persistence": 0.5,
                "coherence_persistence": 0.5,
                "score": 0.5,
            },
            "T": {
                "turn_index": 0,
                "transition_stability": 0.5,
                "sequence_gap": 0.5,
                "last_phase": "",
            },
            "N": {
                "coherence_cost": 0.5,
                "contradiction_cost": 0.0,
                "articulation_cost": 0.0,
                "boundary_cost": 0.5,
                "external_dependency_cost": 0.0,
                "total": 0.25,
            },
            "B": {
                "ambiguity": 0.5,
                "referent_clarity": 0.5,
                "claim_clarity": 0.5,
                "ownership_clarity": 0.5,
                "self_world_separation": 0.5,
            },
            "A": {
                "score": 0.5,
                "label": "unvalidated",
                "delta": 0.0,
                "fit_reason": "",
                "projected_next": 0.5,
            },
            "M": {
                "active_meaning": {},
                "active_frame": {},
                "concepts": [],
                "focus_claim": {},
                "relation_weights": {},
                "semantic_frames": [],
                "active_topic": "",
                "meaning_delta": 0.0,
                "frame_continuity": 0.0,
                "semantic_pressure": 0.0,
                "utterance_continuity": 0.0,
                "constraint_meaning_axes": {},
                "meaning_forms": [],
                "dominant_meaning_form": {},
            },
            "P": {
                "dominant_axis": "X",
                "dominant_emotion": "calm",
                "surface_reactive_emotion": {},
                "deep_emotional_state": {},
                "deep_dominant_emotion": "calm",
                "deep_passion_state": "",
                "emotion_bridge": {},
                "speaker_owner": "user",
                "listener_owner": "aurora",
                "active_behavior_request": "",
                "user_name": "",
                "focus": "",
                "goal_stack": [],
                "perspective_signature": "",
            },
            "Pi": {
                "response_id": "",
                "response_source": "",
                "action_type": "",
                "confidence": 0.0,
                "expected_observation": "",
                "projected_accuracy": 0.5,
                "projected_cost": 0.25,
                "summary": "",
                "articulation_assisted": False,
            },
            "O": {
                "raw": "",
                "intent": "",
                "question": False,
                "callback": False,
                "clarification": False,
                "correction": False,
            },
            "pending_validation": {},
            "contract_domains": {},
            "history": [],
            "last_saved_at": 0.0,
        }

    def _load(self) -> None:
        if not self.persist or not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as handle:
                raw = dict(json.load(handle) or {})
        except Exception:
            return
        default = self._default_state()
        for key, value in raw.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                merged = dict(default[key])
                merged.update(value)
                default[key] = merged
            elif key == "history":
                default[key] = list(value or [])[-MAX_HISTORY:]
            else:
                default[key] = value
        self.state = default

    def save(self) -> bool:
        if not self.persist:
            return False
        try:
            os.makedirs(os.path.dirname(self.storage_path) or ".", exist_ok=True)
            self.state["last_saved_at"] = float(time.time())
            payload = copy.deepcopy(self.state)
            payload["history"] = list(payload.get("history", []) or [])[-MAX_HISTORY:]
            with open(self.storage_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=True, sort_keys=True)
            return True
        except Exception:
            return False

    def record_structural_gap(self, decision: Any) -> None:
        """
        Record an architecture-level structural gap surfaced by the warp field —
        a novelty (e.g. new code structure) that has no place in any existing
        organ. Logging it keeps runtime understanding honest about what the
        system does not yet represent, instead of silently ignoring it.
        """
        import time as _t
        demand = getattr(decision, "demand", None)
        gaps = list(self.state.get("structural_gaps", []) or [])
        gaps.append({
            "ts": float(_t.time()),
            "source": str(getattr(demand, "source", "") or ""),
            "layer": str(getattr(demand, "layer", "") or ""),
            "trigger": str(getattr(demand, "trigger", "") or ""),
            "unresolved": str(getattr(demand, "unresolved_text", "") or "")[:200],
            "severity": float(getattr(demand, "severity", 0.0) or 0.0),
            "pathway": str(getattr(decision, "pathway", "") or ""),
        })
        self.state["structural_gaps"] = gaps[-200:]
        try:
            self.save()
        except Exception:
            pass

    def clone_ephemeral(self, *, label: str = "simulation") -> "RuntimeUnderstandingContract":
        clone = RuntimeUnderstandingContract(
            state_dir=self.state_dir,
            storage_path=os.path.join(self.state_dir, f".understanding_contract_{label}.json"),
            persist=False,
        )
        clone.state = copy.deepcopy(self.state)
        clone.state["pending_validation"] = {}
        clone.state["Pi"] = dict(clone.state.get("Pi", {}) or {})
        clone.state["Pi"]["response_id"] = ""
        clone.state["Pi"]["expected_observation"] = ""
        clone.state["Pi"]["summary"] = ""
        return clone

    def snapshot(self) -> Dict[str, Any]:
        return copy.deepcopy(self.state)

    def status(self) -> Dict[str, Any]:
        return {
            "time_index": int(self.state.get("time_index", 0) or 0),
            "accuracy": float(self.state.get("A", {}).get("score", 0.0) or 0.0),
            "cost_total": float(self.state.get("N", {}).get("total", 0.0) or 0.0),
            "boundary_ambiguity": float(self.state.get("B", {}).get("ambiguity", 0.0) or 0.0),
            "active_topic": str(self.state.get("M", {}).get("active_topic", "") or ""),
            "active_frame": str(dict(self.state.get("M", {}).get("active_frame", {}) or {}).get("summary", "") or ""),
            "frame_continuity": float(self.state.get("M", {}).get("frame_continuity", 0.0) or 0.0),
            "dominant_meaning_form": str(
                dict(self.state.get("M", {}).get("dominant_meaning_form", {}) or {}).get("label", "") or ""
            ),
            "pending_action": str(self.state.get("Pi", {}).get("action_type", "") or ""),
            "persist": bool(self.persist),
            "storage_path": self.storage_path,
        }

    def training_guidance(self, systems: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        history = list(self.state.get("history", []) or [])[-24:]
        observation_entries = [dict(item) for item in history if str(item.get("phase", "") or "") == "observation"]
        application_entries = [dict(item) for item in history if str(item.get("phase", "") or "") == "application"]

        accuracy_values = [
            float(dict(item.get("accuracy", {}) or {}).get("score", 0.0) or 0.0)
            for item in observation_entries
        ]
        boundary_values = [
            float(dict(item.get("boundary", {}) or {}).get("ambiguity", 0.0) or 0.0)
            for item in application_entries
        ]
        cost_values = [
            float(dict(item.get("cost", {}) or {}).get("total", 0.0) or 0.0)
            for item in application_entries
        ]
        transition_values = [
            float(dict(item.get("meaning", {}) or {}).get("frame_continuity", 0.0) or 0.0)
            for item in observation_entries
        ]
        meaning_delta_values = [
            float(dict(item.get("meaning", {}) or {}).get("meaning_delta", 0.0) or 0.0)
            for item in observation_entries
        ]
        utterance_continuity_values = [
            float(dict(item.get("meaning", {}) or {}).get("utterance_continuity", 0.0) or 0.0)
            for item in observation_entries
        ]

        accuracy_avg = _mean(accuracy_values, float(self.state.get("A", {}).get("score", 0.5) or 0.5))
        boundary_avg = _mean(boundary_values, float(self.state.get("B", {}).get("ambiguity", 0.5) or 0.5))
        cost_avg = _mean(cost_values, float(self.state.get("N", {}).get("total", 0.25) or 0.25))
        frame_continuity_avg = _mean(
            transition_values,
            float(self.state.get("M", {}).get("frame_continuity", 0.5) or 0.5),
        )
        meaning_delta_avg = _mean(
            meaning_delta_values,
            float(self.state.get("M", {}).get("meaning_delta", 0.5) or 0.5),
        )
        utterance_continuity_avg = _mean(
            utterance_continuity_values,
            float(self.state.get("M", {}).get("utterance_continuity", 0.5) or 0.5),
        )
        articulation_cost = float(self.state.get("N", {}).get("articulation_cost", 0.0) or 0.0)
        dependency_cost = float(self.state.get("N", {}).get("external_dependency_cost", 0.0) or 0.0)

        pressure_targets: Dict[str, float] = {}
        rationale: List[str] = []
        axis_scores: Dict[str, float] = {}

        if accuracy_avg < 0.76 or cost_avg > 0.34:
            pressure_targets["coherence_maintenance"] = max(
                pressure_targets.get("coherence_maintenance", 0.0),
                round(max(0.78, 1.0 - accuracy_avg), 4),
            )
            pressure_targets["semantic_precision"] = max(
                pressure_targets.get("semantic_precision", 0.0),
                round(max(0.76, 0.45 + cost_avg), 4),
            )
            axis_scores["A"] = max(axis_scores.get("A", 0.0), round(1.0 - accuracy_avg, 4))
            axis_scores["N"] = max(axis_scores.get("N", 0.0), round(cost_avg, 4))
            rationale.append(
                f"contract_accuracy={accuracy_avg:.2f} cost_total={cost_avg:.2f}"
            )

        if frame_continuity_avg < 0.66 or meaning_delta_avg < 0.32:
            pressure_targets["context_carryover"] = max(
                pressure_targets.get("context_carryover", 0.0),
                round(max(0.8, 1.0 - frame_continuity_avg), 4),
            )
            pressure_targets["multi_turn_stability"] = max(
                pressure_targets.get("multi_turn_stability", 0.0),
                round(max(0.74, 1.0 - meaning_delta_avg), 4),
            )
            axis_scores["T"] = max(
                axis_scores.get("T", 0.0),
                round(max(1.0 - frame_continuity_avg, 1.0 - meaning_delta_avg), 4),
            )
            rationale.append(
                f"frame_continuity={frame_continuity_avg:.2f} meaning_delta={meaning_delta_avg:.2f}"
            )

        if utterance_continuity_avg < 0.62:
            pressure_targets["context_carryover"] = max(
                pressure_targets.get("context_carryover", 0.0),
                round(max(0.82, 1.0 - utterance_continuity_avg), 4),
            )
            pressure_targets["multi_turn_stability"] = max(
                pressure_targets.get("multi_turn_stability", 0.0),
                round(max(0.78, 1.0 - utterance_continuity_avg), 4),
            )
            axis_scores["T"] = max(
                axis_scores.get("T", 0.0),
                round(1.0 - utterance_continuity_avg, 4),
            )
            rationale.append(
                f"utterance_continuity={utterance_continuity_avg:.2f}"
            )

        if boundary_avg > 0.24:
            pressure_targets["perspective_integration"] = max(
                pressure_targets.get("perspective_integration", 0.0),
                round(max(0.74, boundary_avg + 0.34), 4),
            )
            pressure_targets["uncertainty_signaling"] = max(
                pressure_targets.get("uncertainty_signaling", 0.0),
                round(max(0.7, boundary_avg + 0.28), 4),
            )
            axis_scores["B"] = max(axis_scores.get("B", 0.0), round(boundary_avg, 4))
            rationale.append(f"boundary_ambiguity={boundary_avg:.2f}")

        if articulation_cost > 0.18 or dependency_cost > 0.16:
            pressure_targets["semantic_precision"] = max(
                pressure_targets.get("semantic_precision", 0.0),
                round(max(0.78, articulation_cost + dependency_cost + 0.38), 4),
            )
            axis_scores["N"] = max(
                axis_scores.get("N", 0.0),
                round(max(articulation_cost, dependency_cost), 4),
            )
            rationale.append(
                f"articulation_cost={articulation_cost:.2f} dependency_cost={dependency_cost:.2f}"
            )

        articulation_result = dict(dict(systems or {}).get("_last_articulation_result", {}) or {})
        pattern = dict(articulation_result.get("pattern_structure", {}) or {})
        failure_modes = set(str(mode).strip() for mode in list(pattern.get("failure_modes", []) or []))
        if "causal_link_missing" in failure_modes:
            pressure_targets["coherence_maintenance"] = max(
                pressure_targets.get("coherence_maintenance", 0.0),
                round(0.92, 4),
            )
            pressure_targets["context_carryover"] = max(
                pressure_targets.get("context_carryover", 0.0),
                round(0.86, 4),
            )
            axis_scores["T"] = max(
                axis_scores.get("T", 0.0),
                round(0.7, 4),
            )
            rationale.append("causal_link_missing")

        contract_state = dict(self.state.get("contract_domains", {}) or {})
        contract_pressure = dict(contract_state.get("pressure_targets", {}) or {})
        for key, value in contract_pressure.items():
            pressure_targets[key] = max(pressure_targets.get(key, 0.0), float(value or 0.0))
        rationale.extend(contract_state.get("rationale", []))

        # ── Developmental stage prioritization ───────────────────────────────
        # Use current meaning_forms (not history averages) for a fresh read of
        # where in the Existence→Coherence chain the system currently sits.
        # Boost pressure dims at the bottleneck; suppress dims for stages that
        # are more than two steps ahead (prerequisites not yet stable).
        _m_state = dict(self.state.get("M", {}) or {})
        _dev_forms = list(_m_state.get("meaning_forms", []) or [])
        _dev_fc = float(_m_state.get("frame_continuity", 0.0) or 0.0)
        dev = _assess_dev_stage(_dev_forms, frame_continuity=_dev_fc)
        dev_dims = dev.get("pressure_dims", ())
        dev_gap = dev["gap_to_next"]
        current_idx = int(dev.get("current_stage", 0))

        if dev_dims and dev_gap > 0.02:
            boost = round(min(0.22, dev_gap * 1.4), 4)
            for dim in dev_dims:
                pressure_targets[dim] = min(1.0, pressure_targets.get(dim, 0.0) + boost)
            if dev.get("bottleneck_axis"):
                axis_scores[dev["bottleneck_axis"]] = max(
                    axis_scores.get(dev["bottleneck_axis"], 0.0),
                    round(dev_gap, 4),
                )
            rationale.append(
                f"dev={dev['current_stage_name']}"
                f"|next={dev['bottleneck_name']}"
                f"|axis={dev.get('bottleneck_axis') or '?'}"
                f"|gap={dev_gap:.2f}"
            )

        # Suppress far-future pressures so effort stays on the actual bottleneck.
        for entry in _DEV_CHAIN:
            if entry["stage_index"] > current_idx + 2:
                for dim in entry.get("pressure_dims", ()):
                    if dim in pressure_targets and dim not in dev_dims:
                        pressure_targets[dim] = round(pressure_targets[dim] * 0.55, 4)

        return {
            "pressure_targets": {
                key: float(round(value, 4))
                for key, value in pressure_targets.items()
                if float(value or 0.0) > 0.0
            },
            "constraint_axes": {
                key: float(round(value, 4))
                for key, value in axis_scores.items()
                if float(value or 0.0) > 0.0
            },
            "rationale": rationale[:10],
            "metrics": {
                "accuracy_avg": round(accuracy_avg, 4),
                "boundary_avg": round(boundary_avg, 4),
                "cost_avg": round(cost_avg, 4),
                "frame_continuity_avg": round(frame_continuity_avg, 4),
                "meaning_delta_avg": round(meaning_delta_avg, 4),
                "utterance_continuity_avg": round(utterance_continuity_avg, 4),
                "articulation_cost": round(articulation_cost, 4),
                "dependency_cost": round(dependency_cost, 4),
                "dev_stage": int(current_idx),
                "dev_stage_name": str(dev.get("current_stage_name", "")),
                "dev_gap": round(dev_gap, 4),
            },
        }

    def register_genealogy(self, genealogy: Any) -> None:
        if self._abilities_registered or genealogy is None or not hasattr(genealogy, "abilities"):
            return
        try:
            for profile in self._ABILITY_SPECS:
                genealogy.abilities[profile.id] = _augment_ability_profile_with_origin(profile)
            self._abilities_registered = True
        except Exception:
            pass

    def _history_append(self, entry: Dict[str, Any]) -> None:
        history = list(self.state.get("history", []) or [])
        history.append(dict(entry or {}))
        self.state["history"] = history[-MAX_HISTORY:]

    def _pipeline_state(self, systems: Dict[str, Any]) -> Dict[str, Any]:
        return dict(systems.get("_last_pipeline_state", {}) or {})

    def _enrich_meaning_state(
        self,
        meaning_state: Dict[str, Any],
        *,
        existence_state: Dict[str, Any],
        transition_state: Dict[str, Any],
        cost_state: Dict[str, Any],
        boundary_state: Dict[str, Any],
        accuracy_score: float,
        projected_accuracy: Optional[float] = None,
    ) -> Dict[str, Any]:
        potential_activation = _clip01(
            0.55 * max(0.0, 1.0 - float(cost_state.get("total", 0.25) or 0.25)) +
            0.45 * float(meaning_state.get("semantic_pressure", 0.0) or 0.0),
            0.5,
        )
        boundary_activation = _clip01(
            _mean(
                [
                    float(boundary_state.get("referent_clarity", 0.5) or 0.5),
                    float(boundary_state.get("claim_clarity", 0.5) or 0.5),
                    float(boundary_state.get("ownership_clarity", 0.5) or 0.5),
                    float(boundary_state.get("self_world_separation", 0.5) or 0.5),
                    max(0.0, 1.0 - float(boundary_state.get("ambiguity", 0.5) or 0.5)),
                ],
                default=0.5,
            ),
            0.5,
        )
        accuracy_values = [float(accuracy_score or 0.0)]
        if projected_accuracy is not None:
            accuracy_values.append(float(projected_accuracy or 0.0))
        axis_activations = {
            "X": round(_clip01(existence_state.get("score", 0.5), 0.5), 4),
            "T": round(_clip01(transition_state.get("transition_stability", 0.5), 0.5), 4),
            "N": round(potential_activation, 4),
            "B": round(boundary_activation, 4),
            "A": round(_clip01(_mean(accuracy_values, default=0.5), 0.5), 4),
        }
        meaning_axes: Dict[str, Dict[str, Any]] = {}
        for axis, profile in _axis_meaning_profiles().items():
            meaning_axes[axis] = {
                "activation": float(axis_activations.get(axis, 0.0) or 0.0),
                "label": str(profile.get("label", "") or ""),
                "summary": str(profile.get("summary", "") or ""),
                "representation": str(profile.get("representation", "") or ""),
            }
        meaning_forms = _rank_meaning_profiles(
            axis_activations,
            limit=6,
            min_axis_activation=0.44,
            min_score=0.5,
            include_singletons=False,
        )
        if not meaning_forms:
            meaning_forms = _rank_meaning_profiles(
                axis_activations,
                limit=6,
                min_axis_activation=0.44,
                min_score=0.5,
                include_singletons=True,
            )
        meaning_state["constraint_meaning_axes"] = meaning_axes
        meaning_state["meaning_forms"] = meaning_forms
        meaning_state["dominant_meaning_form"] = dict(meaning_forms[0]) if meaning_forms else {}
        return meaning_state

    def _apply_genealogy_relief_boost(
        self,
        meaning_state: Dict[str, Any],
        systems: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Boost meaning_form scores when genealogy has active axis relief.

        The understanding contract derives axis_activations purely from
        contract-internal metrics (cost, accuracy, boundary clarity).  This
        means genealogy B-axis evolution never flows into B^1 form ranking —
        breaking the causal chain: genealogy evolution → developmental stage
        advancement.

        Fix: read axis_relief_state() from the genealogy logger, apply a small
        boost (≤ 0.06) to the axis_activations used for meaning-form ranking,
        re-run rank_meaning_profiles so forms whose prerequisite axes are
        actively evolving in genealogy get lifted into (or higher in) the ranked
        list.  Original forms that already passed the threshold are preserved;
        newly qualifying forms from the boosted pass are merged in.

        This creates the causal chain:
          genealogy B-axis link promotion → B-axis relief rises
          → B^1 form score rises → stage-1 (information) threshold reachable
          → B-axis sufficient → stage-2 (relational_structure) opens
          → etc. up the developmental chain.
        """
        try:
            genealogy = systems.get("genealogy")
            if not genealogy or not hasattr(genealogy, "axis_relief_state"):
                return meaning_state
            relief = genealogy.axis_relief_state()
            if not relief or max(relief.values()) < 0.05:
                return meaning_state  # no meaningful relief — skip

            # Build boosted axis_activations from contract's own per-axis scores
            original_axes = dict(meaning_state.get("constraint_meaning_axes", {}) or {})
            boosted_activations: Dict[str, float] = {}
            for axis in ("X", "T", "N", "B", "A"):
                base = float((original_axes.get(axis, {}) or {}).get("activation", 0.0))
                boost = round(min(0.06, relief.get(axis, 0.0) * 0.06), 4)
                boosted_activations[axis] = round(min(1.0, base + boost), 4)

            # Re-rank with boosted activations
            boosted_forms = _rank_meaning_profiles(
                boosted_activations,
                limit=6,
                min_axis_activation=0.44,
                min_score=0.5,
                include_singletons=False,
            )
            if not boosted_forms:
                boosted_forms = _rank_meaning_profiles(
                    boosted_activations,
                    limit=6,
                    min_axis_activation=0.44,
                    min_score=0.5,
                    include_singletons=True,
                )

            # Merge: original forms preserved in their original score order.
            # New forms from the boosted pass are appended at the end — they are
            # bonus additions that wouldn't have existed without genealogy relief,
            # so they don't displace or re-rank existing forms.
            original_forms = list(meaning_state.get("meaning_forms", []) or [])
            existing_sigs = {str(f.get("signature", "")) for f in original_forms}
            merged = list(original_forms)
            for f in boosted_forms:
                sig = str(f.get("signature", ""))
                if sig and sig not in existing_sigs:
                    merged.append(f)
            meaning_state["meaning_forms"] = merged
            if merged:
                meaning_state["dominant_meaning_form"] = dict(merged[0])
        except Exception:
            pass
        return meaning_state

    def _evaluate_contract_domains(
        self,
        *,
        phase: str,
        meaning_state: Dict[str, Any],
        boundary_state: Dict[str, Any],
        transition_state: Dict[str, Any],
        cost_state: Dict[str, Any],
        before_cost_total: float,
        policy_state: Optional[Dict[str, Any]] = None,
        policy_delta: float = 0.0,
        accuracy_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        referent_continuity = float(meaning_state.get("frame_continuity", 0.0) or 0.0)
        contradiction_stability = 1.0 - float(cost_state.get("contradiction_cost", 0.0) or 0.0)
        topic_carryover = float(transition_state.get("transition_stability", 0.0) or 0.0)
        causal_thread = float(meaning_state.get("semantic_pressure", 0.0) or 0.0)
        meaning_body = float(meaning_state.get("meaning_delta", 0.0) or 0.0)

        coherence_score = _mean(
            [
                referent_continuity,
                contradiction_stability,
                topic_carryover,
                causal_thread,
                meaning_body,
            ],
            default=referent_continuity,
        )
        coherence_failures: List[str] = []
        if referent_continuity < 0.58:
            coherence_failures.append("referent_continuity_drop")
        if contradiction_stability < 0.62:
            coherence_failures.append("contradiction_fragility")
        if topic_carryover < 0.55:
            coherence_failures.append("topic_carryover_loss")
        if causal_thread < 0.4:
            coherence_failures.append("causal_thread_gap")
        if meaning_body < 0.3:
            coherence_failures.append("meaning_body_fragment")

        articulation_alignment = 1.0 - float(cost_state.get("articulation_cost", 0.0) or 0.0)
        signal_preservation = max(
            0.0,
            min(
                1.0,
                float(policy_state.get("projected_accuracy", 0.5) or 0.5)
                if policy_state is not None
                else 0.5,
            ),
        )
        expression_structure = 1.0 - float(boundary_state.get("ambiguity", 0.5) or 0.5)
        communication_score = _mean(
            [articulation_alignment, signal_preservation, expression_structure],
            default=0.5,
        )
        communication_failures: List[str] = []
        if articulation_alignment < 0.6:
            communication_failures.append("articulation_fragment")
        if signal_preservation < 0.58:
            communication_failures.append("signal_loss")
        if expression_structure < 0.5:
            communication_failures.append("structure_blur")

        adaptive_gain = max(0.0, min(1.0, float(policy_delta or 0.0)))
        pressure_relief = max(0.0, before_cost_total - float(cost_state.get("total", 0.25) or 0.25))
        structure_growth = float(meaning_state.get("meaning_delta", 0.0) or 0.0)
        generalization = float(meaning_state.get("frame_continuity", 0.0) or 0.0)
        intelligence_score = _mean(
            [adaptive_gain, min(1.0, pressure_relief), structure_growth, generalization],
            default=min(1.0, adaptive_gain + pressure_relief),
        )
        intelligence_failures: List[str] = []
        if adaptive_gain < 0.08:
            intelligence_failures.append("adaptive_stagnation")
        if pressure_relief < 0.04:
            intelligence_failures.append("pressure_stuck")
        if structure_growth < 0.2:
            intelligence_failures.append("no_new_structure")
        if generalization < 0.35:
            intelligence_failures.append("manifold_narrow")

        domain_entries = {
            "coherence": {
                "score": round(_clip01(coherence_score, 1.0), 4),
                "success": coherence_score >= 0.62 and not coherence_failures,
                "failure_signatures": coherence_failures[:3],
                "genealogy_effect": {
                    "promote": "identity_across_time",
                    "penalize": "fragmentation",
                },
            },
            "communication": {
                "score": round(_clip01(communication_score, 1.0), 4),
                "success": communication_score >= 0.6 and not communication_failures,
                "failure_signatures": communication_failures[:3],
                "genealogy_effect": {
                    "promote": "precision_rendering",
                    "penalize": "distortion",
                },
            },
            "intelligence": {
                "score": round(_clip01(intelligence_score, 1.0), 4),
                "success": intelligence_score >= 0.5 and not intelligence_failures,
                "failure_signatures": intelligence_failures[:3],
                "genealogy_effect": {
                    "promote": "long_range_adaptation",
                    "penalize": "shallow_local_wins",
                },
            },
        }

        coherence_opposing = min(1.0, communication_score * 0.25 + intelligence_score * 0.15)
        communication_opposing = min(1.0, coherence_score * 0.25 + intelligence_score * 0.1)
        intelligence_opposing = min(1.0, max(coherence_score, communication_score) * 0.3)
        contract_pressures = {
            "coherence_contract": round(
                max(0.0, 1.0 - coherence_score) * (1.0 - coherence_opposing),
                4,
            ),
            "communication_contract": round(
                max(0.0, 1.0 - communication_score) * (1.0 - communication_opposing),
                4,
            ),
            "intelligence_contract": round(
                max(0.0, 1.0 - intelligence_score) * (1.0 - intelligence_opposing),
                4,
            ),
        }

        # ── Developmental stage domain ─────────────────────────────────────────
        # Identify which stage in the Existence→Coherence chain is the current
        # bottleneck and inject targeted pressure dims for that bottleneck.
        # Pressures for stages that are two or more steps AHEAD are suppressed
        # so training effort is never wasted on traits whose prerequisites haven't
        # stabilized yet.
        dev_meaning_forms = list(meaning_state.get("meaning_forms", []) or [])
        dev_frame_continuity = float(meaning_state.get("frame_continuity", 0.0) or 0.0)
        dev = _assess_dev_stage(dev_meaning_forms, frame_continuity=dev_frame_continuity)

        dev_score = dev["stage_completion"]
        dev_failures: List[str] = []
        if dev["gap_to_next"] > 0.15:
            dev_failures.append(f"stage_gap:{dev['bottleneck_name']}")
        if dev["current_stage"] == 0:
            dev_failures.append("no_stable_meaning_form")

        domain_entries["developmental"] = {
            "score": round(dev_score, 4),
            "success": dev_score >= 0.75 and not dev_failures,
            "failure_signatures": dev_failures[:3],
            "current_stage": dev["current_stage_name"],
            "bottleneck": dev["bottleneck_name"],
            "bottleneck_axis": dev.get("bottleneck_axis") or "",
            "genealogy_effect": {
                "promote": f"stage_transition:{dev['bottleneck_name']}",
                "penalize": "premature_stage_pressure",
            },
        }

        # Inject pressure for the current bottleneck dims — these flow into
        # training_guidance() via the contract_domains.pressure_targets merge.
        dev_dims = dev.get("pressure_dims", ())
        dev_gap = dev["gap_to_next"]
        if dev_dims and dev_gap > 0.02:
            bottleneck_boost = round(min(0.22, dev_gap * 1.4), 4)
            for dim in dev_dims:
                contract_pressures[dim] = round(
                    max(contract_pressures.get(dim, 0.0), bottleneck_boost), 4
                )

        # Scale down pressures for dims that belong to stages more than 2 ahead —
        # they are genuine goals but not the current bottleneck.
        current_idx = int(dev.get("current_stage", 0))
        for entry in _DEV_CHAIN:
            if entry["stage_index"] > current_idx + 2:
                for dim in entry.get("pressure_dims", ()):
                    if dim in contract_pressures and dim not in dev_dims:
                        contract_pressures[dim] = round(
                            contract_pressures[dim] * 0.55, 4
                        )

        rationale_list = [
            f"coherence={domain_entries['coherence']['score']}",
            f"communication={domain_entries['communication']['score']}",
            f"intelligence={domain_entries['intelligence']['score']}",
            f"dev_stage={dev['current_stage_name']}|next={dev['bottleneck_name']}"
            f"|axis={dev.get('bottleneck_axis') or '?'}|gap={dev_gap:.2f}",
        ]

        return {
            "phase": phase,
            "domains": domain_entries,
            "pressure_targets": contract_pressures,
            "rationale": rationale_list,
        }

    def _derive_meaning_state(
        self,
        systems: Dict[str, Any],
        user_text: str,
        understood: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        working_memory = systems.get("working_memory")
        active_meaning: Dict[str, Any] = {}
        active_frame: Dict[str, Any] = {}
        concepts: List[Dict[str, Any]] = []
        focus_claim: Dict[str, Any] = {}
        relation_weights: Dict[str, float] = {}
        semantic_frames: List[Dict[str, Any]] = []
        active_topic = ""
        utterance_continuity = 0.0

        if working_memory is not None:
            try:
                active_topic = str(getattr(working_memory, "current_topic", "") or "").strip()
            except Exception:
                active_topic = ""
            try:
                resolved = working_memory.resolve_concept_meaning(user_text, understood) or {}
            except Exception:
                resolved = {}
            if isinstance(resolved, dict):
                active_meaning = {
                    "term": str(resolved.get("term", "") or "").strip(),
                    "meaning": str(resolved.get("meaning", "") or "").strip(),
                    "contrast": str(resolved.get("contrast", "") or "").strip(),
                    "confidence": _clip01(resolved.get("confidence", 0.0)),
                    "verification_needed": bool(resolved.get("verification_needed", False)),
                }
            try:
                frame_resolution = working_memory.resolve_semantic_frame(user_text, understood) or {}
            except Exception:
                frame_resolution = {}
            if isinstance(frame_resolution, dict):
                active_frame = dict(frame_resolution.get("frame", {}) or {})
                if active_frame:
                    active_frame["resolution_confidence"] = _clip01(
                        frame_resolution.get("confidence", active_frame.get("confidence", 0.0))
                    )
            try:
                for item in list(getattr(working_memory, "concept_meanings", {}).values() or [])[-6:]:
                    if not isinstance(item, dict):
                        continue
                    term = str(item.get("term", "") or "").strip()
                    meaning = str(item.get("meaning", "") or "").strip()
                    if not term or not meaning:
                        continue
                    concepts.append(
                        {
                            "term": term,
                            "meaning": meaning,
                            "contrast": str(item.get("contrast", "") or "").strip(),
                            "turn": int(item.get("turn", 0) or 0),
                            "confidence": _clip01(item.get("confidence", 0.0), 0.65),
                        }
                    )
            except Exception:
                concepts = []
            try:
                claim_resolution = dict(getattr(working_memory, "last_claim_resolution", {}) or {})
                focus_claim = dict(claim_resolution.get("focus_claim", {}) or {})
            except Exception:
                focus_claim = {}
            try:
                recent_claims = list(getattr(working_memory, "recent_claims", []) or [])[-6:]
                for claim in recent_claims:
                    if not isinstance(claim, dict):
                        continue
                    relation = str(claim.get("relation", "") or "").strip() or "related_to"
                    relation_weights[relation] = round(
                        float(relation_weights.get(relation, 0.0) or 0.0) + 0.15,
                        4,
                    )
            except Exception:
                relation_weights = {}
            try:
                for frame in list(getattr(working_memory, "semantic_frames", []) or [])[-8:]:
                    if not isinstance(frame, dict):
                        continue
                    semantic_frames.append(
                        {
                            "frame_type": str(frame.get("frame_type", "") or frame.get("type", "") or "").strip(),
                            "focus": str(frame.get("focus", "") or "").strip(),
                            "source": str(frame.get("source", "") or "").strip(),
                            "turn": int(frame.get("turn", 0) or 0),
                        }
                    )
            except Exception:
                semantic_frames = []
            try:
                readdress_resolution = dict(
                    getattr(working_memory, "last_session_readdress_resolution", {}) or {}
                )
            except Exception:
                readdress_resolution = {}
            if readdress_resolution.get("matched"):
                matched_utterance = dict(readdress_resolution.get("matched_utterance", {}) or {})
                utterance_continuity = _term_overlap(
                    _terms(
                        " ".join(
                            filter(
                                None,
                                [
                                    str(matched_utterance.get("text", "") or ""),
                                    " ".join(list(matched_utterance.get("terms", []) or [])),
                                ],
                            )
                        )
                    ),
                    _terms(
                        " ".join(
                            filter(
                                None,
                                [
                                    active_topic,
                                    str(active_meaning.get("term", "") or ""),
                                    str(active_meaning.get("meaning", "") or ""),
                                    str(dict(active_frame or {}).get("summary", "") or ""),
                                    str(dict(focus_claim or {}).get("summary", "") or ""),
                                ],
                            )
                        )
                    ),
                )
            else:
                try:
                    recent_utterances = list(getattr(working_memory, "recent_user_utterances", []) or [])[:3]
                except Exception:
                    recent_utterances = []
                comparisons: List[float] = []
                for utterance in recent_utterances:
                    if not isinstance(utterance, dict):
                        continue
                    comparisons.append(
                        _term_overlap(
                            _terms(
                                " ".join(
                                    filter(
                                        None,
                                        [
                                            str(utterance.get("text", "") or ""),
                                            " ".join(list(utterance.get("terms", []) or [])),
                                        ],
                                    )
                                )
                            ),
                            _terms(
                                " ".join(
                                    filter(
                                        None,
                                        [
                                            active_topic,
                                            str(active_meaning.get("term", "") or ""),
                                            str(active_meaning.get("meaning", "") or ""),
                                            str(dict(active_frame or {}).get("summary", "") or ""),
                                            str(dict(focus_claim or {}).get("summary", "") or ""),
                                        ],
                                    )
                                )
                            ),
                        )
                    )
                utterance_continuity = _mean(comparisons, 0.0)

        prior_meaning = dict(self.state.get("M", {}) or {})
        previous_focus_terms = _terms(
            " ".join(
                filter(
                    None,
                    [
                        str(prior_meaning.get("active_topic", "") or ""),
                        str(dict(prior_meaning.get("active_meaning", {}) or {}).get("term", "") or ""),
                        str(dict(prior_meaning.get("focus_claim", {}) or {}).get("summary", "") or ""),
                    ],
                )
            )
        )
        previous_frame_terms = _terms(
            " ".join(
                filter(
                    None,
                    [
                        str(dict(prior_meaning.get("active_frame", {}) or {}).get("anchor", "") or ""),
                        str(dict(prior_meaning.get("active_frame", {}) or {}).get("summary", "") or ""),
                    ],
                )
            )
        )
        current_focus_terms = _terms(
            " ".join(
                filter(
                    None,
                    [
                        active_topic,
                        str(active_meaning.get("term", "") or ""),
                        str(active_meaning.get("meaning", "") or ""),
                        str(focus_claim.get("subject", "") or ""),
                        str(focus_claim.get("object", "") or ""),
                    ],
                )
            )
        )
        current_frame_terms = _terms(
            " ".join(
                filter(
                    None,
                    [
                        str(active_frame.get("anchor", "") or ""),
                        str(active_frame.get("summary", "") or ""),
                    ],
                )
            )
        )
        focus_overlap = _term_overlap(previous_focus_terms, current_focus_terms)
        frame_overlap = _term_overlap(previous_frame_terms, current_frame_terms)
        if not previous_frame_terms and current_frame_terms:
            frame_overlap = 0.72

        # Long-horizon anchor continuity: survive vocabulary pivots in abstract discourse.
        # If working_memory carries a semantic_anchor_pool (concept terms seen in prior
        # frames, persisting beyond the semantic_frames deque), check how many of those
        # anchors are still active in the current focus.  Use this as a floor for
        # frame_continuity so a topic renamed in abstract discussion does not drop to 0.
        anchor_continuity = 0.0
        if working_memory is not None:
            try:
                anchor_pool = dict(getattr(working_memory, "semantic_anchor_pool", {}) or {})
                current_turn = int(getattr(working_memory, "turn_count", 0) or 0)

                # Update pool: merge current active meaning + frame terms into pool
                for entry in [
                    {"term": str(active_meaning.get("term", "") or "").strip(),
                     "meaning": str(active_meaning.get("meaning", "") or "").strip()},
                    {"term": str(active_frame.get("anchor", "") or "").strip(),
                     "meaning": str(active_frame.get("summary", "") or "").strip()},
                ]:
                    t = entry["term"]
                    if len(t) >= 3:
                        key = t.lower()
                        existing = anchor_pool.get(key, {})
                        anchor_pool[key] = {
                            "term": t,
                            "meaning": entry["meaning"],
                            "turn": current_turn,
                            "weight": min(1.0, float(existing.get("weight", 0.5)) + 0.15),
                        }
                # Decay anchors older than 20 turns; evict those below floor weight
                evict = [
                    k for k, v in anchor_pool.items()
                    if current_turn - int(v.get("turn", current_turn)) > 20
                    and float(v.get("weight", 0.0)) < 0.2
                ]
                for k in evict:
                    anchor_pool.pop(k, None)
                working_memory.semantic_anchor_pool = anchor_pool

                # Score: how many pool anchors (seen ≥3 turns ago) overlap current focus
                current_all_terms = set(current_focus_terms + current_frame_terms)
                aged_anchors = {
                    k for k, v in anchor_pool.items()
                    if current_turn - int(v.get("turn", current_turn)) >= 3
                }
                if aged_anchors:
                    hits = sum(1 for k in aged_anchors if k in current_all_terms)
                    anchor_continuity = hits / float(len(aged_anchors))
            except Exception:
                anchor_continuity = 0.0

        # frame_continuity is the max of lexical overlap and anchor survival,
        # weighted so anchors contribute at most 70% to avoid over-crediting.
        frame_continuity = max(frame_overlap, anchor_continuity * 0.70)

        meaning_delta = round(_mean([focus_overlap, frame_continuity], default=focus_overlap), 4)
        semantic_pressure = round(
            _clip01(
                1.0 - _mean(
                    [
                        meaning_delta,
                        frame_continuity,
                        float(active_meaning.get("confidence", 0.0) or 0.0),
                        float(active_frame.get("resolution_confidence", active_frame.get("confidence", 0.0)) or 0.0),
                    ],
                    default=0.5,
                ),
                0.5,
            ),
            4,
        )

        return {
            "active_meaning": active_meaning,
            "active_frame": active_frame,
            "concepts": concepts[-6:],
            "focus_claim": focus_claim,
            "relation_weights": relation_weights,
            "semantic_frames": semantic_frames[-8:],
            "active_topic": active_topic,
            "meaning_delta": meaning_delta,
            "frame_continuity": round(frame_continuity, 4),
            "anchor_continuity": round(anchor_continuity, 4),
            "semantic_pressure": semantic_pressure,
            "utterance_continuity": round(_clip01(utterance_continuity, 0.0), 4),
        }

    def _derive_perspective_state(
        self,
        systems: Dict[str, Any],
        meaning_state: Dict[str, Any],
        *,
        source: str = "",
        response_source: str = "",
    ) -> Dict[str, Any]:
        working_memory = systems.get("working_memory")
        pipeline_state = self._pipeline_state(systems)
        user_bucket: Dict[str, Any] = {}
        behavior_request = ""

        if working_memory is not None:
            try:
                user_bucket = dict(getattr(working_memory, "stated_facts", {}).get("user", {}) or {})
            except Exception:
                user_bucket = {}
            try:
                behavior_request = str(
                    getattr(working_memory, "last_behavior_alignment_request", {}).get("requested_behavior", "") or ""
                ).strip()
            except Exception:
                behavior_request = ""

        goals: List[str] = []
        if getattr(working_memory, "pending_lookup_offer", None):
            goals.append("resolve_factual_gap")
        if getattr(working_memory, "pending_hypothesis_offer", None):
            goals.append("hold_possibility_space")
        if behavior_request:
            goals.append("behavior_alignment")
        active_meaning = dict(meaning_state.get("active_meaning", {}) or {})
        focus = (
            str(active_meaning.get("term", "") or "").strip()
            or str(dict(meaning_state.get("active_frame", {}) or {}).get("anchor", "") or "").strip()
            or str(meaning_state.get("active_topic", "") or "").strip()
        )
        dominant_axis = str(pipeline_state.get("dominant_axis", "") or "").strip().upper() or "X"
        if dominant_axis not in AXES:
            dominant_axis = "X"
        dominant_emotion = str(pipeline_state.get("dominant_emotion", "") or "").strip() or "calm"
        surface_reactive_emotion = dict(pipeline_state.get("surface_reactive_emotion", {}) or {})
        deep_emotional_state = dict(pipeline_state.get("deep_emotional_state", {}) or {})
        emotion_bridge = dict(pipeline_state.get("emotion_bridge", {}) or {})
        signature = "|".join(
            [
                dominant_axis,
                dominant_emotion,
                str(deep_emotional_state.get("passion", "") or "none"),
                focus or "none",
                f"behavior:{int(bool(behavior_request))}",
                str(response_source or source or "runtime"),
            ]
        )
        return {
            "dominant_axis": dominant_axis,
            "dominant_emotion": dominant_emotion,
            "surface_reactive_emotion": surface_reactive_emotion,
            "deep_emotional_state": deep_emotional_state,
            "deep_dominant_emotion": str(deep_emotional_state.get("dominant", "") or dominant_emotion),
            "deep_passion_state": str(deep_emotional_state.get("passion", "") or ""),
            "emotion_bridge": emotion_bridge,
            "speaker_owner": "user",
            "listener_owner": "aurora",
            "active_behavior_request": behavior_request,
            "user_name": str(user_bucket.get("name", "") or user_bucket.get("identity_label", "") or "").strip(),
            "focus": focus,
            "goal_stack": goals[:6],
            "perspective_signature": signature,
        }

    def _derive_boundary_state(
        self,
        systems: Dict[str, Any],
        meaning_state: Dict[str, Any],
        perspective_state: Dict[str, Any],
        *,
        response_text: str = "",
    ) -> Dict[str, Any]:
        pipeline_state = self._pipeline_state(systems)
        working_memory = systems.get("working_memory")
        referent_clarity = _clip01(pipeline_state.get("referent_confidence", 0.55), 0.55)
        claim_clarity = _clip01(pipeline_state.get("claim_confidence", 0.6), 0.6)
        ownership_clarity = 0.92
        self_world = 0.9

        response_low = str(response_text or "").lower()
        user_name = str(perspective_state.get("user_name", "") or "").strip().lower()
        if user_name and re.search(rf"\b(?:my name is|i am|i'm)\s+{re.escape(user_name)}\b", response_low):
            ownership_clarity = 0.12
            self_world = 0.18
        if perspective_state.get("active_behavior_request") and response_low:
            if perspective_state["active_behavior_request"].lower() in response_low and "you asked me" not in response_low:
                ownership_clarity = min(ownership_clarity, 0.4)
        if working_memory is not None:
            try:
                if getattr(working_memory, "claim_conflicts", None):
                    claim_clarity = max(0.0, claim_clarity - min(0.25, len(working_memory.claim_conflicts) * 0.06))
            except Exception:
                pass

        ambiguity = 1.0 - _mean(
            [referent_clarity, claim_clarity, ownership_clarity, self_world],
            default=0.5,
        )
        return {
            "ambiguity": round(_clip01(ambiguity, 0.5), 4),
            "referent_clarity": round(referent_clarity, 4),
            "claim_clarity": round(claim_clarity, 4),
            "ownership_clarity": round(_clip01(ownership_clarity, 0.5), 4),
            "self_world_separation": round(_clip01(self_world, 0.5), 4),
        }

    def _derive_cost_state(
        self,
        systems: Dict[str, Any],
        boundary_state: Dict[str, Any],
        *,
        accuracy_score: Optional[float] = None,
        response_text: str = "",
        response_source: str = "",
    ) -> Dict[str, Any]:
        pipeline_state = self._pipeline_state(systems)
        working_memory = systems.get("working_memory")
        articulation_state = dict(systems.get("_articulation_assist_state", {}) or {})
        contradiction_cost = 0.0
        if working_memory is not None:
            try:
                contradiction_cost = min(1.0, len(list(getattr(working_memory, "claim_conflicts", []) or [])) * 0.18)
                relief = dict(getattr(working_memory, "last_conflict_relief", {}) or {})
                if relief.get("resolved"):
                    contradiction_cost *= 0.35
            except Exception:
                contradiction_cost = 0.0

        coherence_cost = 1.0 - _clip01(pipeline_state.get("coherence", 0.62), 0.62)
        articulation_cost = min(1.0, float(articulation_state.get("assistance_debt", 0.0) or 0.0))
        external_dependency_cost = 0.0
        response_low = str(response_text or "").lower()
        if response_source == "search" or "look it up" in response_low:
            external_dependency_cost = 0.28
        if bool((systems.get("_last_articulation_result") or {}).get("used")):
            external_dependency_cost = max(external_dependency_cost, 0.22)

        repeated_claim_matches = re.findall(r"\bactive (?:claim|proposition)\b", response_low)
        active_claim_penalty = 0.0
        if repeated_claim_matches:
            active_claim_penalty = min(0.92, 0.22 + 0.14 * len(repeated_claim_matches))
            coherence_cost = max(coherence_cost, active_claim_penalty)

        boundary_cost = _clip01(boundary_state.get("ambiguity", 0.5), 0.5)
        total = _mean(
            [
                coherence_cost,
                contradiction_cost,
                articulation_cost,
                boundary_cost,
                external_dependency_cost,
                active_claim_penalty,
                max(0.0, 1.0 - _clip01(accuracy_score, 0.5)) if accuracy_score is not None else 0.0,
            ],
            default=0.25,
        )
        return {
            "coherence_cost": round(_clip01(coherence_cost, 0.5), 4),
            "active_claim_penalty": round(active_claim_penalty, 4),
            "contradiction_cost": round(_clip01(contradiction_cost, 0.0), 4),
            "articulation_cost": round(_clip01(articulation_cost, 0.0), 4),
            "boundary_cost": round(_clip01(boundary_cost, 0.5), 4),
            "external_dependency_cost": round(_clip01(external_dependency_cost, 0.0), 4),
            "total": round(_clip01(total, 0.25), 4),
        }

    def _derive_existence_state(
        self,
        systems: Dict[str, Any],
        meaning_state: Dict[str, Any],
        boundary_state: Dict[str, Any],
        cost_state: Dict[str, Any],
        *,
        accuracy_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        working_memory = systems.get("working_memory")
        turn_count = int(getattr(working_memory, "turn_count", 0) or 0) if working_memory is not None else 0
        memory_persistence = _clip01(min(1.0, turn_count / 12.0), 0.5)
        continuity_cost = (
            0.45 * float(boundary_state.get("ambiguity", 0.5) or 0.5) +
            0.35 * float(cost_state.get("contradiction_cost", 0.0) or 0.0)
        )
        if accuracy_score is not None:
            continuity_cost += 0.20 * max(0.0, 1.0 - _clip01(accuracy_score, 0.5))
        continuity = 1.0 - _clip01(continuity_cost, 0.5)
        coherence_persistence = 1.0 - _clip01(cost_state.get("coherence_cost", 0.5), 0.5)
        score = _mean(
            [continuity, memory_persistence, coherence_persistence, 1.0 - float(cost_state.get("total", 0.25) or 0.25)],
            default=0.5,
        )
        return {
            "continuity": round(_clip01(continuity, 0.5), 4),
            "memory_persistence": round(memory_persistence, 4),
            "coherence_persistence": round(_clip01(coherence_persistence, 0.5), 4),
            "score": round(_clip01(score, 0.5), 4),
        }

    def _transition_state(
        self,
        previous_meaning: Dict[str, Any],
        current_meaning: Dict[str, Any],
        *,
        turn_tick: int,
        phase: str,
    ) -> Dict[str, Any]:
        previous_focus = _terms(
            " ".join(
                filter(
                    None,
                    [
                        str(previous_meaning.get("active_topic", "") or ""),
                        str(dict(previous_meaning.get("active_meaning", {}) or {}).get("term", "") or ""),
                    ],
                )
            )
        )
        current_focus = _terms(
            " ".join(
                filter(
                    None,
                    [
                        str(current_meaning.get("active_topic", "") or ""),
                        str(dict(current_meaning.get("active_meaning", {}) or {}).get("term", "") or ""),
                        str(dict(current_meaning.get("active_meaning", {}) or {}).get("meaning", "") or ""),
                    ],
                )
            )
        )
        stability = _term_overlap(previous_focus, current_focus)
        if not previous_focus and current_focus:
            stability = 0.7
        return {
            "turn_index": int(turn_tick or 0),
            "transition_stability": round(_clip01(stability, 0.5), 4),
            "sequence_gap": round(1.0 - _clip01(stability, 0.5), 4),
            "last_phase": str(phase or ""),
        }

    def _looks_like_question(self, text: str) -> bool:
        low = str(text or "").strip().lower()
        return low.endswith("?") or low.startswith(
            (
                "what ",
                "why ",
                "how ",
                "where ",
                "when ",
                "who ",
                "which ",
                "can ",
                "could ",
                "would ",
                "will ",
                "do ",
                "does ",
                "did ",
                "is ",
                "are ",
            )
        )

    def _evaluate_previous_accuracy(
        self,
        systems: Dict[str, Any],
        user_text: str,
        understood: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        pending = dict(self.state.get("pending_validation", {}) or {})
        previous_score = _clip01(self.state.get("A", {}).get("score", 0.5), 0.5)
        if not pending:
            return {
                "used": False,
                "score": previous_score,
                "label": str(self.state.get("A", {}).get("label", "unvalidated") or "unvalidated"),
                "delta": 0.0,
                "fit_reason": "",
                "matched_expectation": False,
            }

        text_low = str(user_text or "").lower().strip()
        expected = str(pending.get("expected_observation", "") or "").strip()
        expected_topic = str(pending.get("expected_topic", "") or "").strip()
        expected_affect = str(pending.get("expected_affect", "") or "neutral").strip()
        expected_axis = str(pending.get("expected_axis", "") or "").strip().upper()
        observed_axis = str(self._pipeline_state(systems).get("dominant_axis", "") or "").strip().upper()
        if observed_axis not in AXES:
            observed_axis = ""
        matched_expectation = False
        label = "unresolved"
        score = previous_score

        correction_markers = (
            "that's not",
            "thats not",
            "wrong",
            "no,",
            "you misunderstood",
            "stop",
            "don't do that",
            "dont do that",
            "you're repeating",
            "you are repeating",
            "not from your perspective",
            "that's my",
            "thats my",
        )
        agreement_markers = (
            "exactly",
            "that's right",
            "thats right",
            "correct",
            "yes",
            "that works",
            "makes sense",
            "right.",
            "thank you",
            "thanks",
        )
        clarification_markers = (
            "i mean",
            "what i mean",
            "by that i mean",
            "in other words",
            "not ",
            "rather than",
        )

        is_question = self._looks_like_question(user_text)
        is_clarification = bool((understood or {}).get("is_clarification")) or any(
            marker in text_low for marker in clarification_markers
        )
        is_callback = bool((understood or {}).get("is_callback"))
        is_correction = any(marker in text_low for marker in correction_markers) or bool((understood or {}).get("is_contradiction"))

        if expected == "clarification" and is_clarification:
            score = 0.88
            label = "clarification_supplied"
            matched_expectation = True
        elif expected == "selection" and any(token in text_low for token in ("keep ", "drop ", "use ", "choose ")):
            score = 0.86
            label = "selection_supplied"
            matched_expectation = True
        elif expected == "confirmation" and any(marker in text_low for marker in agreement_markers):
            score = 0.92
            label = "confirmed"
            matched_expectation = True
        elif is_correction:
            score = 0.16
            label = "corrected"
        elif any(marker in text_low for marker in agreement_markers):
            score = 0.86
            label = "accepted"
        elif is_question and (is_callback or pending.get("action_type") in {"meaning_reasoning", "grounded_answer"}):
            score = 0.74
            label = "coherent_followup"
        elif is_question:
            score = 0.62
            label = "engaged_followup"
        else:
            score = 0.56
            label = "continued_without_validation"

        # Structured dimension adjustments (additive to intent-type score)
        # Topic continuity: if we predicted a topic and user is still on it, small boost;
        # if user diverged to a clearly different topic, small penalty.
        topic_note = ""
        if expected_topic and not is_correction:
            topic_words = set(_terms(expected_topic))
            obs_words = set(_terms(text_low))
            stop = {"the", "and", "for", "are", "was", "has", "but", "not",
                    "you", "that", "this", "with", "from", "they", "have"}
            topic_words -= stop
            if topic_words:
                if topic_words & obs_words:
                    score = _clip01(score + 0.04)
                    topic_note = f"topic_continues:{expected_topic[:30]}"
                else:
                    score = _clip01(score - 0.06)
                    topic_note = f"topic_diverged:{expected_topic[:30]}"

        # Affect continuity: heavy correction markers already handled above;
        # here check if the predicted affective register matches the user's tone
        affect_note = ""
        if expected_affect and expected_affect not in ("neutral", "") and not is_correction:
            understood_affect = str((understood or {}).get("tone", "") or "").lower()
            if understood_affect and expected_affect in understood_affect:
                score = _clip01(score + 0.03)
                affect_note = f"affect_consistent:{expected_affect}"

        axis_note = ""
        if expected_axis and observed_axis and not is_correction:
            if observed_axis == expected_axis:
                score = _clip01(score + 0.02)
                axis_note = f"axis_consistent:{expected_axis}"
            else:
                score = _clip01(score - 0.03)
                axis_note = f"axis_shifted:{expected_axis}->{observed_axis}"

        fit_parts = [f"intent={expected or 'none'}", f"matched={int(matched_expectation)}"]
        if topic_note:
            fit_parts.append(topic_note)
        if affect_note:
            fit_parts.append(affect_note)
        if axis_note:
            fit_parts.append(axis_note)

        delta = round(score - previous_score, 4)
        return {
            "used": True,
            "score": round(_clip01(score, previous_score), 4),
            "label": label,
            "delta": delta,
            "fit_reason": " ".join(fit_parts),
            "matched_expectation": matched_expectation,
        }

    def _derive_observation(self, user_text: str, understood: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        understood = dict(understood or {})
        return {
            "raw": str(user_text or "")[:600],
            "intent": str(understood.get("intent", "") or understood.get("query_type", "") or "").strip(),
            "question": bool(self._looks_like_question(user_text)),
            "callback": bool(understood.get("is_callback")),
            "clarification": bool(understood.get("is_clarification")),
            "correction": bool(
                understood.get("is_contradiction")
                or re.search(r"\b(?:wrong|not right|i mean|not what)\b", str(user_text or "").lower()) is not None
            ),
        }

    def _derive_policy_state(
        self,
        systems: Dict[str, Any],
        user_text: str,
        response_text: str,
        *,
        response_source: str,
        confidence: float,
        offered_lookup: bool,
    ) -> Dict[str, Any]:
        text_low = str(response_text or "").lower().strip()
        articulation_result = dict(systems.get("_last_articulation_result", {}) or {})
        active_meaning = dict(self.state.get("M", {}).get("active_meaning", {}) or {})
        user_terms = _terms(user_text)
        response_terms = _terms(response_text)
        meaning_terms = _terms(
            " ".join(
                filter(
                    None,
                    [
                        str(active_meaning.get("term", "") or ""),
                        str(active_meaning.get("meaning", "") or ""),
                        str(dict(self.state.get("M", {}).get("active_frame", {}) or {}).get("summary", "") or ""),
                        str(self.state.get("M", {}).get("active_topic", "") or ""),
                    ],
                )
            )
        )
        anchor_overlap = max(
            _term_overlap(user_terms, response_terms),
            _term_overlap(meaning_terms, response_terms),
        )
        causal_bonus = 0.12 if any(token in text_low for token in ("because", "therefore", "so ", "if ")) else 0.0
        clarification_bonus = 0.14 if text_low.endswith("?") else 0.0
        lookup_penalty = 0.14 if (offered_lookup or "look it up" in text_low) else 0.0
        articulation_penalty = 0.08 if bool(articulation_result.get("used")) else 0.0
        echo_penalty = 0.18 if _term_overlap(user_terms, response_terms) > 0.82 and len(set(response_terms) - set(user_terms)) < 2 else 0.0

        if text_low.endswith("?"):
            action_type = "clarification_request"
            expected = "clarification"
        elif "look it up" in text_low:
            action_type = "lookup_offer"
            expected = "confirmation"
        elif "contradict" in text_low or "conflict" in text_low:
            action_type = "contradiction_surfacing"
            expected = "selection"
        elif any(token in text_low for token in ("because", "therefore", "if ")):
            action_type = "meaning_reasoning"
            expected = "followup"
        elif response_source == "search":
            action_type = "grounded_answer"
            expected = "followup"
        else:
            action_type = "grounded_response"
            expected = "followup"

        # Structured prediction dimensions — pulled from live contract state
        expected_topic = str(self.state.get("M", {}).get("active_topic", "") or "").strip()
        expected_affect = str(self.state.get("P", {}).get("dominant_emotion", "") or "neutral").strip()
        expected_axis = str(self.state.get("P", {}).get("dominant_axis", "") or "").strip()

        projected_accuracy = _clip01(
            0.48 * _clip01(confidence, 0.5) +
            0.24 * anchor_overlap +
            0.14 * (1.0 - _clip01(self.state.get("N", {}).get("total", 0.25), 0.25)) +
            causal_bonus +
            clarification_bonus -
            lookup_penalty -
            articulation_penalty -
            echo_penalty,
            0.5,
        )
        projected_cost = _clip01(
            _clip01(self.state.get("N", {}).get("total", 0.25), 0.25) +
            lookup_penalty +
            articulation_penalty +
            echo_penalty -
            clarification_bonus * 0.4 -
            causal_bonus * 0.25,
            0.25,
        )
        response_id = f"U:{_hash_payload({'t': time.time(), 'src': response_source, 'text': response_text[:120]})}"
        return {
            "response_id": response_id,
            "response_source": str(response_source or ""),
            "action_type": action_type,
            "confidence": round(_clip01(confidence, 0.5), 4),
            "expected_observation": expected,
            "expected_topic": expected_topic,
            "expected_affect": expected_affect,
            "expected_axis": expected_axis,
            "projected_accuracy": round(projected_accuracy, 4),
            "projected_cost": round(projected_cost, 4),
            "summary": str(response_text or "")[:240],
            "articulation_assisted": bool(articulation_result.get("used")),
        }

    def audit_candidate_response(
        self,
        systems: Dict[str, Any],
        user_text: str,
        candidate_text: str,
        *,
        understood: Optional[Dict[str, Any]] = None,
        response_source: str = "",
        confidence: float = 0.0,
    ) -> Dict[str, Any]:
        clean = str(candidate_text or "").strip()
        if not clean:
            return {"should_revise": False, "issues": [], "reason": ""}

        meaning_state = self._derive_meaning_state(systems, user_text, understood)
        perspective_state = self._derive_perspective_state(
            systems,
            meaning_state,
            source="runtime_audit",
            response_source=response_source,
        )
        boundary_state = self._derive_boundary_state(
            systems,
            meaning_state,
            perspective_state,
            response_text=clean,
        )
        cost_state = self._derive_cost_state(
            systems,
            boundary_state,
            accuracy_score=float(self.state.get("A", {}).get("score", 0.5) or 0.5),
            response_text=clean,
            response_source=response_source,
        )
        response_terms = set(_terms(clean))
        text_low = str(user_text or "").lower()
        callback_like = bool(
            dict(understood or {}).get("is_callback")
            or dict(understood or {}).get("is_clarification")
            or any(token in text_low for token in ("that", "this", "when you said", "what you meant", "mean by that"))
        )
        reasoning_like = any(
            token in text_low
            for token in (
                "why", "how", "what breaks", "what would break", "what happens", "what should",
                "stay connected", "stay anchored", "preserve", "matter",
            )
        )

        active_meaning = dict(meaning_state.get("active_meaning", {}) or {})
        active_frame = dict(meaning_state.get("active_frame", {}) or {})
        meaning_terms = set(
            _terms(
                " ".join(
                    filter(
                        None,
                        [
                            str(active_meaning.get("term", "") or ""),
                            str(active_meaning.get("meaning", "") or ""),
                        ],
                    )
                )
            )
        )
        frame_terms = set(
            _terms(
                " ".join(
                    filter(
                        None,
                        [
                            str(active_frame.get("anchor", "") or ""),
                            str(active_frame.get("summary", "") or ""),
                        ],
                    )
                )
            )
        )

        issues: List[str] = []
        preferred_repair = ""
        if meaning_terms and (callback_like or reasoning_like):
            overlap = len(response_terms & meaning_terms) / float(max(1, len(meaning_terms)))
            if overlap < 0.18:
                issues.append("active_meaning_drift")
                preferred_repair = preferred_repair or "meaning"
        if frame_terms and (callback_like or reasoning_like):
            overlap = len(response_terms & frame_terms) / float(max(1, len(frame_terms)))
            if overlap < 0.16:
                issues.append("semantic_frame_dropout")
                preferred_repair = preferred_repair or "semantic_frame"
        if float(boundary_state.get("ownership_clarity", 1.0) or 1.0) < 0.46:
            issues.append("perspective_boundary_drift")
            preferred_repair = preferred_repair or "behavior_alignment"
        if float(cost_state.get("contradiction_cost", 0.0) or 0.0) > 0.34 and (
            "conflict" not in clean.lower() and "contradict" not in clean.lower()
        ):
            issues.append("unresolved_conflict_smoothing")
            preferred_repair = preferred_repair or "claim"

        # --- RICHER SELF-AUDIT CHECKS ---

        # 1. Axis balance: flag if any of the 5 constraint axes has collapsed near zero.
        #    A collapsed axis means that dimension of understanding has gone dark this turn.
        axis_floor = 0.12
        for axis_key, axis_label in (("X", "existence"), ("T", "temporal"),
                                      ("N", "energy"), ("B", "boundary"), ("A", "agency")):
            raw_axis = dict(self.state.get(axis_key, {}) or {})
            axis_score = _clip01(raw_axis.get("score", raw_axis.get("sequence_gap", 0.5)), 0.5)
            if axis_score < axis_floor:
                issues.append(f"axis_collapse_{axis_label}")
                preferred_repair = preferred_repair or "meaning"

        # 2. Proposition contradiction density: if the substrate has accumulated
        #    many contradiction edges in its active window, flag for repair.
        working_memory = systems.get("working_memory")
        if working_memory is not None:
            substrate = getattr(working_memory, "proposition_substrate", None)
            if substrate is not None:
                try:
                    edge_kinds = substrate.report().get("edge_kinds", {})
                    contradiction_count = int(edge_kinds.get("contradiction", 0))
                    active_count = max(1, int(substrate.report().get("active_count", 1)))
                    contradiction_density = contradiction_count / float(active_count)
                    if contradiction_density > 0.50:
                        issues.append("proposition_contradiction_density")
                        preferred_repair = preferred_repair or "claim"
                except Exception:
                    pass

            # 3. Long-horizon anchor survival: if anchor pool exists but no aged anchors
            #    survive into the current frame, long-horizon continuity has broken.
            try:
                anchor_pool = dict(getattr(working_memory, "semantic_anchor_pool", {}) or {})
                current_turn = int(getattr(working_memory, "turn_count", 0) or 0)
                aged = [
                    k for k, v in anchor_pool.items()
                    if current_turn - int(v.get("turn", current_turn)) >= 3
                ]
                if len(aged) >= 3:
                    anchor_continuity = float(meaning_state.get("anchor_continuity", 1.0) or 1.0)
                    if anchor_continuity < 0.15:
                        issues.append("long_horizon_anchor_dropout")
                        preferred_repair = preferred_repair or "semantic_frame"
            except Exception:
                pass

        verification_needed = bool(active_meaning.get("verification_needed")) and bool(issues)
        revision_pressure = _clip01(
            0.34 * float(cost_state.get("total", 0.25) or 0.25) +
            0.26 * float(boundary_state.get("ambiguity", 0.5) or 0.5) +
            0.22 * float(meaning_state.get("semantic_pressure", 0.0) or 0.0) +
            0.18 * max(0.0, 1.0 - _clip01(confidence, 0.5)),
            0.25,
        )
        should_revise = bool(issues) and (verification_needed or revision_pressure >= 0.28)

        verification_claim = ""
        if verification_needed:
            term = str(active_meaning.get("term", "") or active_frame.get("anchor", "") or "").strip()
            summary = (
                str(active_meaning.get("meaning", "") or "").strip() or
                str(active_frame.get("summary", "") or "").strip()
            )
            if term and summary:
                verification_claim = f"before I revise my own framing around {term}, I need to verify whether you mean {summary}"

        return {
            "should_revise": should_revise,
            "issues": issues,
            "reason": issues[0] if issues else "",
            "preferred_repair": preferred_repair or "meaning",
            "verification_needed": verification_needed,
            "verification_claim": verification_claim,
            "active_meaning": active_meaning,
            "active_frame": active_frame,
            "boundary": boundary_state,
            "cost": cost_state,
            "perspective": perspective_state,
            "revision_pressure": round(revision_pressure, 4),
        }

    def _pressure_from_state(self, state: Dict[str, Any]) -> PressureVec:
        return PressureVec(
            X=round(1.0 - _clip01(state.get("X", {}).get("score", 0.5), 0.5), 4),
            T=round(_clip01(state.get("T", {}).get("sequence_gap", 0.5), 0.5), 4),
            N=round(_clip01(state.get("N", {}).get("total", 0.25), 0.25), 4),
            B=round(_clip01(state.get("B", {}).get("ambiguity", 0.5), 0.5), 4),
            A=round(1.0 - _clip01(state.get("A", {}).get("score", 0.5), 0.5), 4),
        )

    def _record_genealogy_event(
        self,
        systems: Dict[str, Any],
        *,
        phase: str,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        notes: Dict[str, Any],
    ) -> None:
        genealogy = systems.get("genealogy")
        if genealogy is None or not hasattr(genealogy, "observe"):
            return
        self.register_genealogy(genealogy)
        trace = [TraceItem(kind="ABILITY", id=spec.id) for spec in self._ABILITY_SPECS]
        try:
            genealogy.observe(
                pressure_before=self._pressure_from_state(before_state),
                trace=trace,
                pressure_after=self._pressure_from_state(after_state),
                state_sig_before=_hash_payload(
                    {"phase": phase, "time_index": before_state.get("time_index", 0), "state": before_state}
                ),
                state_sig_after=_hash_payload(
                    {"phase": phase, "time_index": after_state.get("time_index", 0), "state": after_state}
                ),
                notes=dict(notes or {}),
            )
        except Exception:
            pass

    def ingest_observation(
        self,
        systems: Dict[str, Any],
        user_text: str,
        *,
        understood: Optional[Dict[str, Any]] = None,
        turn_tick: Optional[int] = None,
        source: str = "",
        session_id: str = "",
    ) -> Dict[str, Any]:
        before_state = copy.deepcopy(self.state)
        observation = self._derive_observation(user_text, understood)
        accuracy = self._evaluate_previous_accuracy(systems, user_text, understood)
        meaning_state = self._derive_meaning_state(systems, user_text, understood)
        perspective_state = self._derive_perspective_state(systems, meaning_state, source=source)
        boundary_state = self._derive_boundary_state(systems, meaning_state, perspective_state)
        cost_state = self._derive_cost_state(
            systems,
            boundary_state,
            accuracy_score=accuracy.get("score"),
            response_source=str(self.state.get("Pi", {}).get("response_source", "") or ""),
        )
        existence_state = self._derive_existence_state(
            systems,
            meaning_state,
            boundary_state,
            cost_state,
            accuracy_score=accuracy.get("score"),
        )
        transition_state = self._transition_state(
            dict(before_state.get("M", {}) or {}),
            meaning_state,
            turn_tick=int(turn_tick or before_state.get("time_index", 0) or 0),
            phase="observation",
        )

        current_time = max(int(self.state.get("time_index", 0) or 0) + 1, int(turn_tick or 0))
        self.state["time_index"] = int(current_time)
        self.state["X"] = existence_state
        self.state["T"] = transition_state
        self.state["N"] = cost_state
        self.state["B"] = boundary_state
        self.state["A"] = {
            "score": round(_clip01(accuracy.get("score", 0.5), 0.5), 4),
            "label": str(accuracy.get("label", "unvalidated") or "unvalidated"),
            "delta": round(float(accuracy.get("delta", 0.0) or 0.0), 4),
            "fit_reason": str(accuracy.get("fit_reason", "") or ""),
            "projected_next": round(_clip01(self.state.get("Pi", {}).get("projected_accuracy", 0.5), 0.5), 4),
        }
        meaning_delta = round(
            ALPHA * float(self.state["A"].get("score", 0.5) or 0.5) * float(meaning_state.get("meaning_delta", 0.0) or 0.0),
            4,
        )
        meaning_state["meaning_delta"] = meaning_delta
        meaning_state = self._enrich_meaning_state(
            meaning_state,
            existence_state=existence_state,
            transition_state=transition_state,
            cost_state=cost_state,
            boundary_state=boundary_state,
            accuracy_score=float(self.state["A"].get("score", 0.5) or 0.5),
        )
        meaning_state = self._apply_genealogy_relief_boost(meaning_state, systems)
        self.state["M"] = meaning_state
        self.state["P"] = perspective_state
        self.state["O"] = observation
        self.state["pending_validation"] = {}
        contract_domains = self._evaluate_contract_domains(
            phase="observation",
            meaning_state=meaning_state,
            boundary_state=boundary_state,
            transition_state=transition_state,
            cost_state=cost_state,
            before_cost_total=float(before_state.get("N", {}).get("total", 0.25) or 0.25),
            policy_state=None,
            policy_delta=0.0,
            accuracy_score=float(self.state["A"].get("score", 0.5) or 0.5),
        )
        self.state["contract_domains"] = contract_domains

        dominant_form = dict(meaning_state.get("dominant_meaning_form", {}) or {})
        notes = {
            "tag": "understanding_contract",
            "phase": "observation_validation",
            "axis_signature": "X^1*T^1*N^1*B^1*A^1",
            "purpose_lane": "meaning",
            "time_index": int(self.state.get("time_index", 0) or 0),
            "session_id": str(session_id or ""),
            "source": str(source or "runtime"),
            "observation_intent": str(observation.get("intent", "") or ""),
            "accuracy_score": float(self.state["A"].get("score", 0.0) or 0.0),
            "accuracy_label": str(self.state["A"].get("label", "") or ""),
            "cost_total": float(cost_state.get("total", 0.0) or 0.0),
            "boundary_ambiguity": float(boundary_state.get("ambiguity", 0.0) or 0.0),
            "meaning_delta": float(meaning_delta),
            "meaning_form": str(dominant_form.get("label", "") or ""),
            "meaning_signature": str(dominant_form.get("signature", "") or ""),
            "matched_expectation": bool(accuracy.get("matched_expectation")),
        }
        notes["contract_domains"] = contract_domains.get("domains", {})
        if accuracy.get("used"):
            self._record_genealogy_event(
                systems,
                phase="observation_validation",
                before_state=before_state,
                after_state=self.state,
                notes=notes,
            )

        self._history_append(
            {
                "time": round(time.time(), 3),
                "phase": "observation",
                "time_index": int(self.state.get("time_index", 0) or 0),
                "source": str(source or "runtime"),
                "user_text": str(user_text or "")[:260],
                "observation": observation,
                "accuracy": dict(self.state.get("A", {}) or {}),
                "meaning": {
                    "active_topic": str(meaning_state.get("active_topic", "") or ""),
                    "active_frame": str(dict(meaning_state.get("active_frame", {}) or {}).get("summary", "") or ""),
                    "meaning_delta": float(meaning_state.get("meaning_delta", 0.0) or 0.0),
                    "frame_continuity": float(meaning_state.get("frame_continuity", 0.0) or 0.0),
                    "semantic_pressure": float(meaning_state.get("semantic_pressure", 0.0) or 0.0),
                    "dominant_form": str(dominant_form.get("label", "") or ""),
                    "dominant_signature": str(dominant_form.get("signature", "") or ""),
                },
                "meaning_focus": str(meaning_state.get("active_topic", "") or ""),
                "pending_cleared": bool(accuracy.get("used")),
                "contracts": contract_domains.get("domains", {}),
            }
        )
        return {
            "time_index": int(self.state.get("time_index", 0) or 0),
            "observation": observation,
            "accuracy": dict(self.state.get("A", {}) or {}),
            "meaning": dict(self.state.get("M", {}) or {}),
            "perspective": dict(self.state.get("P", {}) or {}),
        }

    def commit_application(
        self,
        systems: Dict[str, Any],
        user_text: str,
        response_text: str,
        *,
        response_source: str = "",
        tone: str = "",
        confidence: float = 0.0,
        understood: Optional[Dict[str, Any]] = None,
        offered_lookup: bool = False,
        source: str = "",
        session_id: str = "",
    ) -> Dict[str, Any]:
        before_state = copy.deepcopy(self.state)
        meaning_state = self._derive_meaning_state(systems, user_text, understood)
        perspective_state = self._derive_perspective_state(
            systems,
            meaning_state,
            source=source,
            response_source=response_source,
        )
        boundary_state = self._derive_boundary_state(
            systems,
            meaning_state,
            perspective_state,
            response_text=response_text,
        )
        cost_state = self._derive_cost_state(
            systems,
            boundary_state,
            accuracy_score=float(before_state.get("A", {}).get("score", 0.5) or 0.5),
            response_text=response_text,
            response_source=response_source,
        )
        policy_state = self._derive_policy_state(
            systems,
            user_text,
            response_text,
            response_source=response_source,
            confidence=confidence,
            offered_lookup=offered_lookup,
        )
        transition_state = self._transition_state(
            dict(before_state.get("M", {}) or {}),
            meaning_state,
            turn_tick=int(self.state.get("time_index", 0) or 0),
            phase="application",
        )
        projected_accuracy = float(policy_state.get("projected_accuracy", 0.5) or 0.5)
        projected_state = copy.deepcopy(self.state)
        projected_state["X"] = self._derive_existence_state(
            systems,
            meaning_state,
            boundary_state,
            cost_state,
            accuracy_score=projected_accuracy,
        )
        projected_state["T"] = transition_state
        projected_state["N"] = cost_state
        projected_state["B"] = boundary_state
        projected_state["P"] = perspective_state
        projected_state["Pi"] = policy_state
        projected_state["A"] = {
            "score": round(float(before_state.get("A", {}).get("score", 0.5) or 0.5), 4),
            "label": str(before_state.get("A", {}).get("label", "") or ""),
            "delta": 0.0,
            "fit_reason": str(before_state.get("A", {}).get("fit_reason", "") or ""),
            "projected_next": round(_clip01(projected_accuracy, 0.5), 4),
        }
        meaning_state = self._enrich_meaning_state(
            meaning_state,
            existence_state=projected_state["X"],
            transition_state=transition_state,
            cost_state=cost_state,
            boundary_state=boundary_state,
            accuracy_score=float(projected_state["A"].get("score", 0.5) or 0.5),
            projected_accuracy=projected_accuracy,
        )
        meaning_state = self._apply_genealogy_relief_boost(meaning_state, systems)
        projected_state["M"] = meaning_state
        policy_delta = round(
            BETA * (projected_accuracy - LAMBDA * float(cost_state.get("total", 0.25) or 0.25)),
            4,
        )
        contract_domains = self._evaluate_contract_domains(
            phase="application",
            meaning_state=meaning_state,
            boundary_state=boundary_state,
            transition_state=transition_state,
            cost_state=cost_state,
            before_cost_total=float(before_state.get("N", {}).get("total", 0.25) or 0.25),
            policy_state=policy_state,
            policy_delta=policy_delta,
            accuracy_score=float(before_state.get("A", {}).get("score", 0.5) or 0.5),
        )
        self.state["contract_domains"] = contract_domains

        self.state["X"] = projected_state["X"]
        self.state["T"] = transition_state
        self.state["N"] = cost_state
        self.state["B"] = boundary_state
        self.state["M"] = meaning_state
        self.state["P"] = perspective_state
        self.state["Pi"] = policy_state
        self.state["A"]["projected_next"] = round(_clip01(projected_accuracy, 0.5), 4)
        self.state["pending_validation"] = {
            "response_id": str(policy_state.get("response_id", "") or ""),
            "action_type": str(policy_state.get("action_type", "") or ""),
            "expected_observation": str(policy_state.get("expected_observation", "") or ""),
            "expected_topic": str(policy_state.get("expected_topic", "") or ""),
            "expected_affect": str(policy_state.get("expected_affect", "") or "neutral"),
            "expected_axis": str(policy_state.get("expected_axis", "") or ""),
            "projected_accuracy": round(_clip01(projected_accuracy, 0.5), 4),
            "response_source": str(response_source or ""),
            "summary": str(response_text or "")[:240],
            "tone": str(tone or ""),
            "session_id": str(session_id or ""),
        }

        dominant_form = dict(meaning_state.get("dominant_meaning_form", {}) or {})
        notes = {
            "tag": "understanding_contract",
            "phase": "application_projection",
            "axis_signature": "X^1*T^1*N^1*B^1*A^1",
            "purpose_lane": "meaning",
            "time_index": int(self.state.get("time_index", 0) or 0),
            "session_id": str(session_id or ""),
            "source": str(source or "runtime"),
            "response_source": str(response_source or ""),
            "action_type": str(policy_state.get("action_type", "") or ""),
            "projected_accuracy": float(policy_state.get("projected_accuracy", 0.0) or 0.0),
            "projected_cost": float(policy_state.get("projected_cost", 0.0) or 0.0),
            "policy_delta": float(policy_delta),
            "boundary_ambiguity": float(boundary_state.get("ambiguity", 0.0) or 0.0),
            "meaning_focus": str(meaning_state.get("active_topic", "") or ""),
            "meaning_form": str(dominant_form.get("label", "") or ""),
            "meaning_signature": str(dominant_form.get("signature", "") or ""),
        }
        notes["contract_domains"] = contract_domains.get("domains", {})
        self._record_genealogy_event(
            systems,
            phase="application_projection",
            before_state=before_state,
            after_state=projected_state,
            notes=notes,
        )

        self._history_append(
            {
                "time": round(time.time(), 3),
                "phase": "application",
                "time_index": int(self.state.get("time_index", 0) or 0),
                "source": str(source or "runtime"),
                "response_source": str(response_source or ""),
                "response_text": str(response_text or "")[:260],
                "policy": policy_state,
                "meaning": {
                    "active_topic": str(meaning_state.get("active_topic", "") or ""),
                    "dominant_form": str(dominant_form.get("label", "") or ""),
                    "dominant_signature": str(dominant_form.get("signature", "") or ""),
                },
                "boundary": boundary_state,
                "cost": cost_state,
                "policy_delta": policy_delta,
                "contracts": contract_domains.get("domains", {}),
            }
        )
        return {
            "time_index": int(self.state.get("time_index", 0) or 0),
            "policy": dict(policy_state),
            "meaning": dict(meaning_state),
            "perspective": dict(perspective_state),
            "boundary": dict(boundary_state),
            "cost": dict(cost_state),
            "policy_delta": policy_delta,
        }

    # =========================================================================
    # REFLECTION RE-ENTRY SEQUENCE (AURORA_COGNITIVE_PHYSICS.md §6 & §7)
    #
    # Mandatory sequence: STATE → EXPRESSION → RE-ENTRY → RECONCILIATION → UNDERSTANDING
    #
    # Laws from the physics document:
    #   MAY NOT: Skip RECONCILIATION — STATE to UNDERSTANDING directly is invalid
    #   MAY NOT: Begin before Thought has reached full convergence
    #   MAY NOT: Run more than one unresolved RE-ENTRY cycle without flagging tension
    #   MAY NOT: Allow Emotion to author UNDERSTANDING
    #   MAY NOT: Silence unresolved tension — every contradiction must surface or be flagged
    #
    # After Understanding, the downward modulation cascade is mandatory:
    #   Identity → Memory (geological write) → Pressure topology reset →
    #   Prediction priors → Salience thresholds → Composite crystal weights
    # =========================================================================

    def run_reflection_cycle(
        self,
        systems: Dict[str, Any],
        user_text: str,
        candidate_response: str,
        *,
        constraint_state: Optional[Dict[str, Any]] = None,
        session_id: str = "",
    ) -> Dict[str, Any]:
        """
        Enforce the mandatory Reflection re-entry sequence before Understanding.

        Returns a dict with keys:
          reached_understanding (bool): True only if RECONCILIATION succeeded
          tension_flags (list): Non-empty if RECONCILIATION failed
          reflection_step (str): Last step completed
          understanding (dict): The resolved field state if reached; empty otherwise
        """
        result: Dict[str, Any] = {
            "reached_understanding": False,
            "tension_flags": [],
            "reflection_step": "STATE",
            "understanding": {},
        }

        # ── STEP 1: STATE ── capture the current full constraint state
        state_snapshot = self._capture_reflection_state(systems)
        result["reflection_step"] = "EXPRESSION"

        # ── STEP 2: EXPRESSION ── surface what the current state is generating
        expression = {
            "candidate": str(candidate_response or "")[:480],
            "meaning_topic": str(self.state.get("M", {}).get("active_topic", "") or ""),
            "boundary_ambiguity": float(self.state.get("B", {}).get("ambiguity", 0.0) or 0.0),
            "cost_total": float(self.state.get("N", {}).get("total", 0.0) or 0.0),
            "accuracy_score": float(self.state.get("A", {}).get("score", 0.5) or 0.5),
            "perspective_speaker": str(self.state.get("P", {}).get("primary_speaker", "") or ""),
        }
        result["reflection_step"] = "RE_ENTRY"

        # ── STEP 3: RE-ENTRY ── feed the expression back as new constraint input
        reentry = self._compute_reentry_delta(state_snapshot, expression, systems)
        result["reflection_step"] = "RECONCILIATION"

        # ── STEP 4: RECONCILIATION ── resolve tension between original state and re-entered output
        tension = self._compute_tension(state_snapshot, reentry)
        reconciled, flags = self._attempt_reconciliation(tension)

        if not reconciled:
            self._flag_tension(systems, flags, state_snapshot, session_id=session_id)
            result["tension_flags"] = flags
            result["reflection_step"] = "RECONCILIATION_FAILED"
            return result

        # ── STEP 5: UNDERSTANDING ── field at equilibrium; all noncomp manifolds coherent
        result["reflection_step"] = "UNDERSTANDING"
        understanding = self._emit_understanding(
            state_snapshot=state_snapshot,
            reentry=reentry,
            tension=tension,
            session_id=session_id,
        )
        result["reached_understanding"] = True
        result["understanding"] = understanding

        # Mandatory downward modulation cascade
        self._trigger_downward_cascade(systems, understanding)
        return result

    def _capture_reflection_state(self, systems: Dict[str, Any]) -> Dict[str, Any]:
        """STATE step: snapshot the full current constraint state."""
        return {
            "M": copy.deepcopy(self.state.get("M", {})),
            "P": copy.deepcopy(self.state.get("P", {})),
            "X": copy.deepcopy(self.state.get("X", {})),
            "T": copy.deepcopy(self.state.get("T", {})),
            "N": copy.deepcopy(self.state.get("N", {})),
            "B": copy.deepcopy(self.state.get("B", {})),
            "A": copy.deepcopy(self.state.get("A", {})),
            "Pi": copy.deepcopy(self.state.get("Pi", {})),
            "time_index": int(self.state.get("time_index", 0) or 0),
            "timestamp": round(time.time(), 4),
        }

    def _compute_reentry_delta(
        self,
        state_snapshot: Dict[str, Any],
        expression: Dict[str, Any],
        systems: Dict[str, Any],
    ) -> Dict[str, Any]:
        """RE-ENTRY step: compute constraint displacement from feeding expression back."""
        prior_accuracy = float(state_snapshot.get("A", {}).get("score", 0.5) or 0.5)
        prior_cost = float(state_snapshot.get("N", {}).get("total", 0.25) or 0.25)
        expressed_accuracy = float(expression.get("accuracy_score", 0.5) or 0.5)
        expressed_cost = float(expression.get("cost_total", 0.25) or 0.25)

        return {
            "accuracy_delta": round(expressed_accuracy - prior_accuracy, 4),
            "cost_delta": round(expressed_cost - prior_cost, 4),
            "boundary_ambiguity": float(expression.get("boundary_ambiguity", 0.0) or 0.0),
            "meaning_topic": str(expression.get("meaning_topic", "") or ""),
            "candidate_length": len(str(expression.get("candidate", "") or "")),
        }

    def _compute_tension(
        self,
        state_snapshot: Dict[str, Any],
        reentry: Dict[str, Any],
    ) -> Dict[str, float]:
        """Compute tension between the original state and the re-entered output."""
        accuracy_tension = abs(float(reentry.get("accuracy_delta", 0.0) or 0.0))
        cost_tension = max(0.0, float(reentry.get("cost_delta", 0.0) or 0.0))
        boundary_tension = float(reentry.get("boundary_ambiguity", 0.0) or 0.0)

        # Meaning continuity tension: if topic changed, tension rises
        prior_topic = str(state_snapshot.get("M", {}).get("active_topic", "") or "")
        reentry_topic = str(reentry.get("meaning_topic", "") or "")
        topic_tension = 0.0 if (not prior_topic or prior_topic == reentry_topic) else 0.4

        return {
            "accuracy": round(accuracy_tension, 4),
            "cost": round(cost_tension, 4),
            "boundary": round(boundary_tension, 4),
            "meaning": round(topic_tension, 4),
            "total": round((accuracy_tension + cost_tension + boundary_tension + topic_tension) / 4.0, 4),
        }

    def _attempt_reconciliation(
        self, tension: Dict[str, float]
    ) -> tuple:
        """
        RECONCILIATION step: attempt to resolve tension.

        Returns (reconciled: bool, flags: list).
        Reconciliation fails if total tension exceeds the resolution threshold.
        Flags enumerate the specific axes where tension is unresolved.
        """
        TENSION_THRESHOLD = 0.55
        flags: list = []

        if float(tension.get("accuracy", 0.0)) > 0.40:
            flags.append("accuracy_tension_unresolved")
        if float(tension.get("cost", 0.0)) > 0.35:
            flags.append("cost_tension_unresolved")
        if float(tension.get("boundary", 0.0)) > 0.45:
            flags.append("boundary_tension_unresolved")
        if float(tension.get("meaning", 0.0)) > 0.30:
            flags.append("meaning_continuity_break")

        reconciled = float(tension.get("total", 0.0)) <= TENSION_THRESHOLD and not flags
        return reconciled, flags

    def _flag_tension(
        self,
        systems: Dict[str, Any],
        flags: list,
        state_snapshot: Dict[str, Any],
        *,
        session_id: str = "",
    ) -> None:
        """
        Tension must never be silently suppressed.
        Record unresolved tension in history and notify any connected systems.
        """
        tension_record = {
            "time": round(time.time(), 3),
            "phase": "reflection_tension",
            "time_index": int(self.state.get("time_index", 0) or 0),
            "session_id": str(session_id or ""),
            "flags": list(flags),
            "state_snapshot_time_index": int(state_snapshot.get("time_index", 0) or 0),
            "law": "RECONCILIATION_REQUIRED — Understanding may not be emitted from unreconciled tension",
        }
        self._history_append(tension_record)

        # Surface tension into any connected tension bus (soft dispatch)
        tension_bus = systems.get("_tension_bus") or systems.get("tension_bus")
        if tension_bus and hasattr(tension_bus, "register_tension"):
            try:
                tension_bus.register_tension(flags, state_snapshot)
            except Exception:
                pass

    def _emit_understanding(
        self,
        *,
        state_snapshot: Dict[str, Any],
        reentry: Dict[str, Any],
        tension: Dict[str, float],
        session_id: str = "",
    ) -> Dict[str, Any]:
        """
        UNDERSTANDING step: emit the resolved field state.
        Only called after RECONCILIATION succeeds.
        """
        return {
            "time_index": int(self.state.get("time_index", 0) or 0),
            "session_id": str(session_id or ""),
            "timestamp": round(time.time(), 4),
            "resolved_accuracy": float(self.state.get("A", {}).get("score", 0.5) or 0.5),
            "resolved_cost": float(self.state.get("N", {}).get("total", 0.25) or 0.25),
            "resolved_meaning_topic": str(self.state.get("M", {}).get("active_topic", "") or ""),
            "resolved_boundary_ambiguity": float(self.state.get("B", {}).get("ambiguity", 0.0) or 0.0),
            "tension_at_resolution": dict(tension),
            "reentry_delta": dict(reentry),
            "prior_state_time_index": int(state_snapshot.get("time_index", 0) or 0),
            "crystal_level": "understanding",
            "law": "AURORA_COGNITIVE_PHYSICS §7 Understanding — field at equilibrium across all noncomp manifolds",
        }

    def _trigger_downward_cascade(
        self, systems: Dict[str, Any], understanding: Dict[str, Any]
    ) -> None:
        """
        DOWNWARD MODULATION CASCADE (AURORA_COGNITIVE_PHYSICS.md §8).

        After every Understanding, mandatory cascade reconfigures all lower crystal levels:
          1. Identity → King Quasicrystal reconfiguration
          2. Memory → geological stratum write
          3. Pressure topology → discharge and reset across all noncomp manifolds
          4. Prediction priors → reset from resolved ground truth
          5. Salience thresholds → recalibration for next turn
          6. Composite crystal weights → update
          7. Constraint Basis → recalibration for next turn

        All dispatches are soft: missing methods are skipped, never silently failed.
        """
        cascade_record = {
            "time": round(time.time(), 3),
            "phase": "downward_cascade",
            "time_index": int(understanding.get("time_index", 0) or 0),
            "understanding_summary": {
                "accuracy": understanding.get("resolved_accuracy"),
                "cost": understanding.get("resolved_cost"),
                "topic": understanding.get("resolved_meaning_topic"),
            },
            "dispatches": [],
        }

        def _soft(target_key: str, method: str, *args):
            obj = systems.get(target_key)
            if obj and hasattr(obj, method):
                try:
                    getattr(obj, method)(*args)
                    cascade_record["dispatches"].append(f"{target_key}.{method}:ok")
                except Exception as exc:
                    cascade_record["dispatches"].append(f"{target_key}.{method}:err:{exc}")
            else:
                cascade_record["dispatches"].append(f"{target_key}.{method}:not_found")

        # 1. Identity field: King Quasicrystal reconfiguration
        #    The NoncompField is the live 125-noncomp × 625-slot Identity field.
        _soft("identity_field", "accept_understanding_update", understanding)
        _soft("behavioral_identity", "accept_understanding_update", understanding)
        _soft("identity_persistence", "accept_understanding_update", understanding)

        # 2. Memory: geological stratum write (deepest — near-immutable)
        _soft("sedimemory", "geological_write", understanding)

        # 3. Pressure topology: discharge and reset
        _soft("consciousness", "reset_pressure_topology", understanding)
        _soft("consciousness_engine", "reset_pressure_topology", understanding)

        # 4. Prediction priors: reset from resolved ground truth
        _soft("prediction_field", "reset_from_understanding", understanding)

        # 5. Salience thresholds: recalibrate for next turn
        _soft("consciousness", "recalibrate_salience", understanding)
        _soft("consciousness_engine", "recalibrate_salience", understanding)
        # Tensor layer: SalienceCrystal threshold recalibrated from resolved state
        _soft("tensor_expressions", "recalibrate_salience", understanding)

        # 6. Composite crystal weights: update all five tensor expression crystals
        # This is the "composite crystal expression weights updated" in §8.
        # TensorExpressionLayer.receive_understanding() recalibrates all crystals.
        _soft("tensor_expressions", "receive_understanding", understanding)
        # Also dispatch to expression/perception layer (legacy)
        _soft("expression_perception", "update_crystal_weights", understanding)

        # 6b. Prediction priors: reset from resolved ground truth (tensor layer)
        # PredictionCrystal(T+N) holds temporal priors that must reset after Understanding.
        _soft("tensor_expressions", "reset_prediction_priors", understanding)

        # 7. Constraint Basis: recalibrate — next turn begins from here
        # Dispatches to dimensional (DER/DMM) and genealogy trackers.
        _soft("genealogy", "accept_understanding_update", understanding)
        _soft("constraint_genealogy", "accept_understanding_update", understanding)
        # Dimensional layer owns the live constraint basis
        _soft("dimensional", "recalibrate_from_understanding", understanding)

        self._history_append(cascade_record)
