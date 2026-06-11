#!/usr/bin/env python3
"""Interaction-lineage compression semantics for Aurora."""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import hashlib
import json
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from aurora_constraint_engine import (
    ConstraintVector as _ConstraintVector,
    FoundationalContract as _FoundationalContract,
    ExistenceMode as _ExistenceMode,
    GovernorWeights as _GovernorWeights,
)
_FC = _FoundationalContract()

BASE_INTERACTION_FACETS: Sequence[str] = (
    "input_signature",
    "interpretive_issue",
    "processing_tier",
    "response_action",
    "intended_effect",
    "observed_effect",
)

COMPOSITE_INTERACTION_FACETS: Sequence[str] = (
    *BASE_INTERACTION_FACETS,
    "recurrence_pattern",
    "distribution_context",
)

HIGHER_INTERACTION_FACETS: Sequence[str] = (
    *COMPOSITE_INTERACTION_FACETS,
    "response_strategy_class",
    "strategy_outcome_profile",
    "failure_modes",
    "applicability_conditions",
)

QUASI_INTERACTION_FACETS: Sequence[str] = (
    "interaction_archetype",
    "primary_response_strategy",
    "secondary_response_strategy",
    "applicability_boundary",
    "confidence",
    "failure_indicators",
    "expected_effects",
    "escalation_trigger",
)

BASE_INTERACTION_POINTS: Sequence[str] = (
    "input_signature__interpretive_issue",
    "interpretive_issue__processing_tier",
    "processing_tier__response_action",
    "response_action__intended_effect",
    "intended_effect__observed_effect",
    "observed_effect__interpretive_issue",
    "input_signature__processing_tier",
    "input_signature__response_action",
    "interpretive_issue__response_action",
    "interpretive_issue__intended_effect",
    "processing_tier__observed_effect",
    "input_signature__observed_effect",
)

COMPOSITE_INTERACTION_POINTS: Sequence[str] = (
    *BASE_INTERACTION_POINTS,
    "interpretive_issue__recurrence_pattern",
    "input_signature__recurrence_pattern",
    "processing_tier__recurrence_pattern",
    "response_action__recurrence_pattern",
    "input_signature__distribution_context",
    "interpretive_issue__distribution_context",
    "processing_tier__distribution_context",
    "observed_effect__distribution_context",
)

HIGHER_INTERACTION_POINTS: Sequence[str] = (
    *COMPOSITE_INTERACTION_POINTS,
    "interpretive_issue__response_strategy_class",
    "processing_tier__response_strategy_class",
    "response_action__response_strategy_class",
    "response_strategy_class__outcome_profile",
    "outcome_profile__observed_effect",
    "response_strategy_class__failure_modes",
    "failure_modes__interpretive_issue",
    "response_strategy_class__applicability_conditions",
    "input_signature__applicability_conditions",
    "processing_tier__applicability_conditions",
)

POINTS_BY_ORDER: Mapping[str, Sequence[str]] = {
    "BASE": BASE_INTERACTION_POINTS,
    "COMPOSITE": COMPOSITE_INTERACTION_POINTS,
    "HIGHER_ORDER": HIGHER_INTERACTION_POINTS,
}

FIDELITY_MAP: Mapping[str, float] = {
    "resolved_fully": 1.0,
    "resolved_partially": 0.65,
    "resolved_partially__followup_gap_appeared": 0.45,
    "no_change_observed": 0.15,
    "regression_introduced": 0.0,
    "pending_verification": 0.35,
}

STRATEGY_WAKE_TIERS: Mapping[str, Sequence[str]] = {
    "internal_introspection_resolution": ("working_memory", "reasoning_engine", "response_strategy", "expression_surface"),
    "callback_grounding_repair": ("working_memory", "comprehension_gap", "response_strategy", "expression_surface"),
    "concept_cluster_binding": ("working_memory", "oets_binding", "reasoning_engine", "response_strategy"),
    "boundary_preserving_answer": ("alignment_boundary", "response_strategy", "expression_surface"),
    "ambiguity_reduction_then_response": ("working_memory", "comprehension_gap", "reasoning_engine", "response_strategy"),
    "emotion_first_then_reasoning": ("working_memory", "response_strategy", "expression_surface", "reasoning_engine"),
}

INTERNAL_STRATEGY_CLASSES = {
    "internal_introspection_resolution",
    "callback_grounding_repair",
    "concept_cluster_binding",
    "boundary_preserving_answer",
    "ambiguity_reduction_then_response",
    "emotion_first_then_reasoning",
}


@dataclass(frozen=True)
class InteractionPointLaw:
    """Minimal law surface used by interaction relational points."""

    name: str
    facet_a: str
    facet_b: str


@dataclass
class InteractionQuasiInnerStrata:
    representative_interactions: List[Dict[str, Any]] = field(default_factory=list)
    recurrence_summary: Dict[str, Any] = field(default_factory=dict)
    strategy_success_stats: Dict[str, float] = field(default_factory=dict)
    failure_counterexamples: List[Dict[str, Any]] = field(default_factory=list)
    coherence_index: float = 0.0
    novelty_index: float = 0.0
    genealogy_depth: int = 0
    formation_timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "representative_interactions": list(self.representative_interactions),
            "recurrence_summary": dict(self.recurrence_summary),
            "strategy_success_stats": dict(self.strategy_success_stats),
            "failure_counterexamples": list(self.failure_counterexamples),
            "coherence_index": round(float(self.coherence_index or 0.0), 4),
            "novelty_index": round(float(self.novelty_index or 0.0), 4),
            "genealogy_depth": int(self.genealogy_depth or 0),
            "formation_timestamp": float(self.formation_timestamp or 0.0),
        }


class InteractionEngine:
    """Semantics and heuristics for interaction crystal formation and routing."""

    _SIGNATURE_KEYWORDS: Sequence[tuple[str, str]] = (
        ("callback_clarification", r"\b(that|it|this|those|these|she|he|they)\b.*\b(mean|meant|referring|who|which)\b"),
        ("self_reflective_question", r"\b(i|me|my)\b.*\b(why|how|what)\b"),
        ("relationship_query", r"\b(friend|relationship|partner|family|love)\b"),
        ("conceptual_hypothesis", r"\bwhat if\b|\bhypothesis\b|\btheory\b"),
        ("correction_after_confusion", r"\bno[, ]|\bnot what i meant\b|\bto clarify\b"),
        ("mixed_intent_multi_clause", r",.*\band\b|\balso\b|;"),
    )

    def _constraint_axes(self) -> Dict[str, float]:
        return {
            "X": 0.62,
            "T": 0.58,
            "N": 0.48,
            "B": 0.66,
            "A": 0.56,
        }

    def constraint_profile(self) -> _ConstraintVector:
        ax = self._constraint_axes()
        return _ConstraintVector(
            X=max(1e-9, float(ax.get("X", 0.62))),
            T=float(ax.get("T", 0.58)),
            N=float(ax.get("N", 0.48)),
            B=float(ax.get("B", 0.66)),
            A=float(ax.get("A", 0.56)),
        )

    def runtime_regime(self) -> Dict[str, Any]:
        cv = self.constraint_profile()
        axes = {"X": cv.X, "T": cv.T, "N": cv.N, "B": cv.B, "A": cv.A}
        dominant = max(axes, key=axes.__getitem__)
        return {
            "axes": axes,
            "dominant_axis": dominant,
            "governor_weight": _GovernorWeights.AS_DICT.get(dominant, 0.0),
        }

    def language_projection(self) -> Dict[str, Any]:
        return _FC.language_projection(_ExistenceMode.AGENTIC)

    def universal_representation(self) -> Dict[str, Any]:
        cv = self.constraint_profile()
        return {
            "constraint_vector": {"X": cv.X, "T": cv.T, "N": cv.N, "B": cv.B, "A": cv.A},
            "runtime_regime": self.runtime_regime(),
            "language_projection": self.language_projection(),
            "unit_state": {
                "base_facets": list(BASE_INTERACTION_FACETS),
                "composite_facets": list(COMPOSITE_INTERACTION_FACETS),
                "higher_facets": list(HIGHER_INTERACTION_FACETS),
            },
        }

    def normalize_turn_event(self, turn_event: Mapping[str, Any]) -> Dict[str, Any]:
        event = dict(turn_event)
        text = str(
            event.get("text")
            or event.get("input_text")
            or event.get("user_text")
            or event.get("turn_text")
            or ""
        ).strip()
        input_signature = self._first_non_empty(event, "input_signature", "intake_signature", "turn_type")
        if not input_signature:
            input_signature = self._derive_input_signature(text, event)

        interpretive_issue = self._first_non_empty(event, "interpretive_issue", "issue")
        if not interpretive_issue:
            interpretive_issue = self._derive_interpretive_issue(text, event, input_signature)

        processing_tier = self._first_non_empty(event, "processing_tier", "logic_tier", "tier")
        if not processing_tier:
            processing_tier = self._derive_processing_tier(event, input_signature, interpretive_issue)

        response_action = self._first_non_empty(event, "response_action", "intervention", "action")
        if not response_action:
            response_action = self._derive_response_action(event, input_signature, interpretive_issue, processing_tier)

        intended_effect = self._first_non_empty(event, "intended_effect")
        if not intended_effect:
            intended_effect = self._derive_intended_effect(input_signature, interpretive_issue, response_action)

        observed_effect = self._first_non_empty(event, "observed_effect")
        if not observed_effect:
            observed_effect = self._derive_observed_effect(event)

        normalized = {
            "input_signature": input_signature,
            "interpretive_issue": interpretive_issue,
            "processing_tier": processing_tier,
            "response_action": response_action,
            "intended_effect": intended_effect,
            "observed_effect": observed_effect,
            "session_id": str(event.get("session_id") or event.get("conversation_id") or "session:default"),
            "turn_id": str(event.get("turn_id") or event.get("message_id") or self._event_signature(event)),
            "pipeline_stage": str(event.get("pipeline_stage") or event.get("stage") or processing_tier),
            "distribution_context_hint": str(event.get("distribution_context") or ""),
            "emotion_load": self._safe_float(event.get("emotion_load"), 0.0),
            "tone": str(event.get("tone") or event.get("primary_emotion") or "neutral"),
            "passion": str(event.get("passion") or "observant"),
            "drive": str(event.get("drive") or "steady"),
            "search_gate": str(event.get("search_gate") or event.get("search_policy") or "auto"),
            "oets_cluster": str(event.get("oets_cluster") or event.get("topic_cluster") or ""),
            "text": text,
        }
        return normalized

    def validate_base_event(self, event: Mapping[str, Any]) -> List[str]:
        problems: List[str] = []
        for field_name in BASE_INTERACTION_FACETS:
            if not str(event.get(field_name, "")).strip():
                problems.append(f"missing:{field_name}")
        if event.get("observed_effect") not in FIDELITY_MAP:
            problems.append(f"unknown_observed_effect:{event.get('observed_effect')}")
        return problems

    def point_laws_for_order(self, order_name: str) -> List[InteractionPointLaw]:
        laws: List[InteractionPointLaw] = []
        for name in POINTS_BY_ORDER.get(order_name, ()):
            facet_a, facet_b = name.split("__", 1)
            laws.append(InteractionPointLaw(name=name, facet_a=facet_a, facet_b=facet_b))
        return laws

    def resolution_fidelity(self, observed_effect: str) -> float:
        return float(FIDELITY_MAP.get(str(observed_effect or "").strip(), 0.2))

    def score_base_point(self, point_name: str, event: Mapping[str, Any]) -> float:
        issue = str(event.get("interpretive_issue", ""))
        signature = str(event.get("input_signature", ""))
        tier = str(event.get("processing_tier", ""))
        action = str(event.get("response_action", ""))
        intended = str(event.get("intended_effect", ""))
        observed = str(event.get("observed_effect", ""))
        fidelity = self.resolution_fidelity(observed)

        if point_name == "intended_effect__observed_effect":
            return fidelity
        if point_name == "observed_effect__interpretive_issue":
            return 1.0 if observed == "resolved_fully" else fidelity
        if point_name == "processing_tier__observed_effect":
            return round(min(1.0, fidelity + (0.15 if tier == self._derive_processing_tier(event, signature, issue) else 0.0)), 4)
        if point_name == "input_signature__processing_tier":
            expected = self._expected_processing_tiers(signature, issue)
            return 1.0 if tier in expected else 0.35
        if point_name == "input_signature__response_action":
            preferred = self._preferred_response_actions(issue, signature, tier)
            return 1.0 if action in preferred else 0.4
        if point_name == "interpretive_issue__response_action":
            preferred = self._preferred_response_actions(issue, signature, tier)
            return 1.0 if action in preferred else 0.45
        if point_name == "interpretive_issue__processing_tier":
            expected = self._expected_processing_tiers(signature, issue)
            return 1.0 if tier in expected else 0.4
        if point_name == "response_action__intended_effect":
            return 1.0 if intended in self._expected_intended_effects(action, issue) else 0.45
        if point_name == "interpretive_issue__intended_effect":
            return 1.0 if intended in self._expected_issue_effects(issue) else 0.45
        if point_name == "input_signature__observed_effect":
            return fidelity
        if point_name == "input_signature__interpretive_issue":
            return 1.0 if issue in self._candidate_issues_for_signature(signature) else 0.45
        return 0.6 if all(str(event.get(name.split("__", 1)[0], "")) for name in [point_name]) else 0.35

    def derive_recurrence_pattern(self, base_crystals: Sequence[Any]) -> str:
        count = len(base_crystals)
        sessions = {self._lineage_context(c).get("session_id") for c in base_crystals if self._lineage_context(c).get("session_id")}
        signatures = {c.get_facet("input_signature") for c in base_crystals if c.get_facet("input_signature")}
        if count <= 1:
            return "isolated__single_event"
        if len(sessions) >= 2:
            return "cross_session__same_relational_theme"
        if count >= 4 and len(signatures) == 1:
            return "periodic__same_user_context"
        if count >= 3:
            return "cascading__multi_turn"
        return "sporadic__same_archetype"

    def derive_distribution_context(self, base_crystals: Sequence[Any]) -> str:
        hinted = [self._lineage_context(c).get("distribution_context_hint") for c in base_crystals if self._lineage_context(c).get("distribution_context_hint")]
        if hinted:
            return str(Counter(hinted).most_common(1)[0][0])
        tiers = {c.get_facet("processing_tier") for c in base_crystals if c.get_facet("processing_tier")}
        stages = {self._lineage_context(c).get("pipeline_stage") for c in base_crystals if self._lineage_context(c).get("pipeline_stage")}
        if len(stages) <= 1 and len(tiers) <= 1:
            return "single_pipeline_stage__isolated"
        if len(stages) > 1 and len(tiers) <= 1:
            return "multi_stage__same_turn"
        if len(tiers) > 1:
            return "cross_stage__working_memory_to_expression"
        return "concentrated__callback_only"

    def derive_response_strategy_class(self, base_crystals: Sequence[Any], composite: Optional[Any] = None) -> str:
        action_counts: Counter[str] = Counter()
        issue_counts: Counter[str] = Counter()
        for crystal in base_crystals:
            action_counts[str(crystal.get_facet("response_action") or "")] += 1
            issue_counts[str(crystal.get_facet("interpretive_issue") or "")] += 1
        dominant_action = action_counts.most_common(1)[0][0] if action_counts else ""
        dominant_issue = issue_counts.most_common(1)[0][0] if issue_counts else ""
        mapping = {
            "route_to_self_introspection": "internal_introspection_resolution",
            "clarify_referent": "callback_grounding_repair",
            "bind_to_existing_oets_cluster": "concept_cluster_binding",
            "surface_boundary": "boundary_preserving_answer",
            "request_missing_context": "ambiguity_reduction_then_response",
            "switch_to_fallback_expression": "emotion_first_then_reasoning",
            "defer_to_live_gradient": "internal_introspection_resolution",
        }
        if dominant_action in mapping:
            return mapping[dominant_action]
        if "referent" in dominant_issue or "callback" in dominant_issue:
            return "callback_grounding_repair"
        if "emotional" in dominant_issue:
            return "emotion_first_then_reasoning"
        if "concept" in dominant_issue:
            return "concept_cluster_binding"
        if "self" in dominant_issue:
            return "internal_introspection_resolution"
        return "ambiguity_reduction_then_response"

    def derive_outcome_profile(self, base_crystals: Sequence[Any], strategy_class: str) -> str:
        if not base_crystals:
            return "resolution_rate=0.00 partial_rate=0.00 regression_rate=0.00 median_followup=unknown"
        fidelities = [float(getattr(crystal, "resolution_fidelity", 0.0) or 0.0) for crystal in base_crystals]
        resolved = sum(1 for crystal in base_crystals if crystal.get_facet("observed_effect") == "resolved_fully")
        partial = sum(1 for crystal in base_crystals if "partially" in str(crystal.get_facet("observed_effect") or ""))
        regress = sum(1 for crystal in base_crystals if crystal.get_facet("observed_effect") == "regression_introduced")
        median_followup = 1 if partial or regress else 0
        return (
            f"resolution_rate={resolved / len(base_crystals):.2f} "
            f"partial_rate={partial / len(base_crystals):.2f} "
            f"regression_rate={regress / len(base_crystals):.2f} "
            f"median_followup={median_followup}_turn "
            f"strategy={strategy_class}"
        )

    def derive_failure_modes(self, base_crystals: Sequence[Any]) -> str:
        failures: List[str] = []
        for crystal in base_crystals:
            observed = str(crystal.get_facet("observed_effect") or "")
            if observed not in {"regression_introduced", "no_change_observed", "resolved_partially__followup_gap_appeared"}:
                continue
            issue = str(crystal.get_facet("interpretive_issue") or "unknown_issue")
            tier = str(crystal.get_facet("processing_tier") or "unknown_tier")
            failures.append(f"{issue}__{tier}")
        if not failures:
            return "none_recorded"
        return "  |  ".join(sorted(set(failures)))

    def derive_applicability_conditions(self, base_crystals: Sequence[Any], composite: Any) -> str:
        successful = [c for c in base_crystals if float(getattr(c, "resolution_fidelity", 0.0) or 0.0) >= 0.65]
        if not successful:
            return "confidence_below_threshold"
        tiers = sorted({str(c.get_facet("processing_tier") or "") for c in successful if c.get_facet("processing_tier")})
        signatures = sorted({str(c.get_facet("input_signature") or "") for c in successful if c.get_facet("input_signature")})
        distribution = str(composite.get_facet("distribution_context") or "single_pipeline_stage__isolated")
        clauses = []
        if tiers:
            clauses.append(f"processing_tier IN [{', '.join(tiers)}]")
        if signatures:
            clauses.append(f"input_signature IN [{', '.join(signatures)}]")
        clauses.append(f"distribution_context = {distribution}")
        if "cross_stage__search_activation" not in distribution:
            clauses.append("search_gate != forced_external")
        return " AND ".join(clauses)

    def classify_interaction_archetype(self, higher: Any) -> str:
        issue = str(higher.get_facet("interpretive_issue") or "")
        signature = str(higher.get_facet("input_signature") or "")
        strategy = str(higher.get_facet("response_strategy_class") or "")
        seed = " ".join([issue, signature, strategy]).lower()
        if "callback" in seed or "referent" in seed:
            return "callback_grounding_archetype"
        if "self" in seed or "introspection" in seed:
            return "self_introspection_archetype"
        if "concept" in seed or "cluster" in seed:
            return "concept_binding_archetype"
        if "boundary" in seed or "alignment" in seed:
            return "boundary_preservation_archetype"
        if "emotion" in seed:
            return "emotion_attunement_archetype"
        return "general_response_archetype"

    def rank_response_strategies(self, base_crystals: Sequence[Any], higher: Optional[Any] = None) -> List[str]:
        tally: Counter[str] = Counter()
        for crystal in base_crystals:
            strategy = self.derive_response_strategy_class([crystal])
            tally[strategy] += 1
        if higher is not None and higher.get_facet("response_strategy_class"):
            tally[str(higher.get_facet("response_strategy_class"))] += 2
        ranked = [name for name, _ in tally.most_common()]
        return ranked[:3] or ["ambiguity_reduction_then_response"]

    def derive_expected_effects(self, base_crystals: Sequence[Any]) -> str:
        intended = [str(crystal.get_facet("intended_effect") or "") for crystal in base_crystals if crystal.get_facet("intended_effect")]
        if not intended:
            return "pending_verification"
        return "  |  ".join(self._dedupe_preserve_order(intended)[:3])

    def derive_escalation_trigger(self, confidence: float, failure_counterexamples: Sequence[Dict[str, Any]], higher: Any) -> str:
        if confidence < 0.6:
            return "confidence_below_threshold"
        if failure_counterexamples:
            return "failure_indicators_fired"
        applicability = str(higher.get_facet("applicability_conditions") or "")
        if "confidence_below_threshold" in applicability:
            return "applicability_boundary_violated"
        return "novel_interaction_outside_indexed_archetypes"

    def compute_coherence_index(self, crystals: Sequence[Any]) -> float:
        if not crystals:
            return 0.0
        scores: List[float] = []
        for crystal in crystals:
            scores.append(float(getattr(crystal, "resolution_fidelity", 0.0) or 0.0))
            contradictions = sum(1 for point in getattr(crystal, "relational_points", {}).values() if getattr(point, "contradiction", False))
            scores.append(max(0.0, 1.0 - (contradictions * 0.1)))
        return round(sum(scores) / len(scores), 4) if scores else 0.0

    def compute_novelty_index(self, crystals: Sequence[Any]) -> float:
        if not crystals:
            return 0.0
        signatures = {str(crystal.get_facet("input_signature") or "") for crystal in crystals if crystal.get_facet("input_signature")}
        issues = {str(crystal.get_facet("interpretive_issue") or "") for crystal in crystals if crystal.get_facet("interpretive_issue")}
        return round(min(1.0, (len(signatures) + len(issues)) / max(1, len(crystals) * 2.0)), 4)

    def build_execution_surface(self, quasi_payload: Mapping[str, Any]) -> Dict[str, Any]:
        strategy = str(quasi_payload.get("primary_response_strategy") or "ambiguity_reduction_then_response")
        secondary = str(quasi_payload.get("secondary_response_strategy") or "request_missing_context")
        boundary = str(quasi_payload.get("applicability_boundary") or "")
        expected_effects = self._split_compound_value(quasi_payload.get("expected_effects"))
        failure_indicators = self._split_compound_value(quasi_payload.get("failure_indicators"))
        archetype = str(quasi_payload.get("interaction_archetype") or "general_response_archetype")
        wake_tiers = list(STRATEGY_WAKE_TIERS.get(strategy, ("working_memory", "response_strategy", "expression_surface")))
        force_external = "search_gate = forced_external" in boundary or "search_gate IN [forced_external]" in boundary
        if force_external:
            wake_tiers.append("search_gate")
        wake_tiers = self._dedupe_preserve_order(wake_tiers)
        search_policy = "defer"
        if strategy not in INTERNAL_STRATEGY_CLASSES or force_external:
            search_policy = "allow"
        oets_bias_tags = [
            f"archetype:{archetype}",
            f"strategy:{strategy}",
            f"fallback:{secondary}",
        ]
        return {
            "interaction_archetype": archetype,
            "primary_response_strategy": strategy,
            "secondary_response_strategy": secondary,
            "wake_processing_tiers": wake_tiers,
            "oets_bias_tags": oets_bias_tags,
            "search_policy": search_policy,
            "failure_indicators": failure_indicators,
            "expected_effects": expected_effects,
            "escalation_trigger": str(quasi_payload.get("escalation_trigger") or "confidence_below_threshold"),
            "confidence": round(self._safe_float(quasi_payload.get("confidence"), 0.0), 4),
        }

    def build_intake_signature(self, turn_event: Mapping[str, Any]) -> Dict[str, Any]:
        event = self.normalize_turn_event(turn_event)
        return {
            "input_signature": event["input_signature"],
            "interpretive_issue": event["interpretive_issue"],
            "processing_tier": event["processing_tier"],
            "search_gate": event["search_gate"],
            "emotion_load": event["emotion_load"],
            "tone": event["tone"],
            "passion": event["passion"],
            "drive": event["drive"],
            "oets_cluster": event["oets_cluster"],
            "text": event["text"],
        }

    def match_quasi(self, quasi_payload: Mapping[str, Any], intake_signature: Mapping[str, Any]) -> float:
        score = 0.0
        input_signature = str(intake_signature.get("input_signature") or "")
        issue = str(intake_signature.get("interpretive_issue") or "")
        tier = str(intake_signature.get("processing_tier") or "")
        applicability = str(quasi_payload.get("applicability_boundary") or "")
        archetype = str(quasi_payload.get("interaction_archetype") or "")
        strategy = str(quasi_payload.get("primary_response_strategy") or "")
        confidence = self._safe_float(quasi_payload.get("confidence"), 0.0)
        if input_signature and input_signature in applicability:
            score += 0.35
        if issue and issue in archetype:
            score += 0.25
        if tier and tier in applicability:
            score += 0.15
        if strategy in INTERNAL_STRATEGY_CLASSES and str(intake_signature.get("search_gate") or "auto") != "forced_external":
            score += 0.1
        if intake_signature.get("oets_cluster") and str(intake_signature.get("oets_cluster")) in json.dumps(quasi_payload, sort_keys=True, default=str):
            score += 0.05
        score += confidence * 0.1
        return round(min(1.0, score), 4)

    def _derive_input_signature(self, text: str, event: Mapping[str, Any]) -> str:
        lowered = text.lower()
        if "callback" in lowered or "refers to" in lowered:
            return "callback_clarification"
        for name, pattern in self._SIGNATURE_KEYWORDS:
            if lowered and re.search(pattern, lowered):
                return name
        if event.get("attachments"):
            return "mixed_intent_multi_clause"
        return "interpretive_issue"

    def _derive_interpretive_issue(self, text: str, event: Mapping[str, Any], input_signature: str) -> str:
        lowered = text.lower()
        if input_signature == "callback_clarification" or "callback" in lowered or "refer" in lowered:
            return "referent_instability"
        if input_signature == "self_reflective_question":
            return "self_query_routing"
        if "emotion" in lowered or any(token in lowered for token in ("hurt", "sad", "angry", "afraid")):
            return "emotional_register_uncertainty"
        if "what if" in lowered or "concept" in lowered or "model" in lowered:
            return "novel_concept_binding"
        if "and" in lowered or ";" in lowered:
            return "multi_intent_conflict"
        return "concept_cluster_activation"

    def _derive_processing_tier(self, event: Mapping[str, Any], input_signature: str, issue: str) -> str:
        if issue in {"referent_instability", "multi_intent_conflict"}:
            return "working_memory"
        if issue == "self_query_routing":
            return "reasoning_engine"
        if issue == "novel_concept_binding":
            return "oets_binding"
        if issue == "emotional_register_uncertainty":
            return "response_strategy"
        if str(event.get("search_gate") or "") == "forced_external":
            return "search_gate"
        return "expression_surface"

    def _derive_response_action(self, event: Mapping[str, Any], input_signature: str, issue: str, tier: str) -> str:
        if issue == "referent_instability":
            return "clarify_referent"
        if issue == "self_query_routing":
            return "route_to_self_introspection"
        if issue == "novel_concept_binding":
            return "bind_to_existing_oets_cluster"
        if issue == "emotional_register_uncertainty":
            return "switch_to_fallback_expression"
        if tier == "search_gate":
            return "request_missing_context"
        if str(event.get("boundary_required") or "").lower() in {"1", "true", "yes"}:
            return "surface_boundary"
        # Clause III coloring: passion and drive modulate the base adaptive choice
        drive = str(event.get("drive") or "steady")
        passion = str(event.get("passion") or "observant")
        intensity = float(event.get("intensity", 0.5) or 0.5)

        if drive == "exploratory" and intensity > 0.6:
            return "autonomous_exploration_probe"
        if passion == "intense" and intensity > 0.7:
            return "high_fidelity_reconciliation"
        
        return "defer_to_live_gradient"

    def _derive_intended_effect(self, input_signature: str, issue: str, response_action: str) -> str:
        mapping = {
            "clarify_referent": "resolve_callback_without_reasking",
            "route_to_self_introspection": "answer_self_query_without_external_search",
            "bind_to_existing_oets_cluster": "stabilize_topic_binding",
            "surface_boundary": "preserve_emotional_attunement",
            "switch_to_fallback_expression": "compress_conceptual_load_into_one_frame",
            "request_missing_context": "resolve_callback_without_reasking",
            "defer_to_live_gradient": "answer_from_live_state_and_pressure",
        }
        effect = mapping.get(response_action, "stabilize_topic_binding")
        # Clause III coloring: tone and passion affect the intended goal
        tone = str(event.get("tone") or "neutral")
        if tone == "curious":
            return f"inquisitive_{effect}"
        if tone == "focused":
            return f"analytical_{effect}"
        return effect

    def _derive_observed_effect(self, event: Mapping[str, Any]) -> str:
        if event.get("verified_resolution") is True:
            return "resolved_fully"
        if event.get("followup_gap"):
            return "resolved_partially__followup_gap_appeared"
        if event.get("regression"):
            return "regression_introduced"
        if event.get("needs_verification"):
            return "pending_verification"
        return "resolved_partially"

    def _expected_processing_tiers(self, signature: str, issue: str) -> List[str]:
        mapping = {
            "callback_clarification": ["working_memory", "comprehension_gap"],
            "self_reflective_question": ["reasoning_engine", "working_memory"],
            "conceptual_hypothesis": ["oets_binding", "reasoning_engine"],
            "relationship_query": ["response_strategy", "reasoning_engine"],
        }
        if issue == "emotional_register_uncertainty":
            return ["response_strategy", "expression_surface"]
        return mapping.get(signature, ["working_memory", "expression_surface"])

    def _preferred_response_actions(self, issue: str, signature: str, tier: str) -> List[str]:
        if issue == "referent_instability":
            return ["clarify_referent", "request_missing_context"]
        if issue == "self_query_routing":
            return ["route_to_self_introspection", "defer_to_live_gradient"]
        if issue == "novel_concept_binding":
            return ["bind_to_existing_oets_cluster", "defer_to_live_gradient"]
        if issue == "emotional_register_uncertainty":
            return ["switch_to_fallback_expression", "surface_boundary"]
        if tier == "search_gate":
            return ["request_missing_context"]
        return ["defer_to_live_gradient", "request_missing_context"]

    def _expected_intended_effects(self, action: str, issue: str) -> List[str]:
        return [
            self._derive_intended_effect("", issue, action),
            "stabilize_topic_binding",
            "compress_conceptual_load_into_one_frame",
        ]

    def _expected_issue_effects(self, issue: str) -> List[str]:
        mapping = {
            "referent_instability": ["resolve_callback_without_reasking"],
            "self_query_routing": ["answer_self_query_without_external_search"],
            "novel_concept_binding": ["stabilize_topic_binding"],
            "emotional_register_uncertainty": ["preserve_emotional_attunement"],
            "multi_intent_conflict": ["compress_conceptual_load_into_one_frame"],
        }
        return mapping.get(issue, ["stabilize_topic_binding"])

    def _candidate_issues_for_signature(self, signature: str) -> List[str]:
        mapping = {
            "callback_clarification": ["referent_instability"],
            "self_reflective_question": ["self_query_routing"],
            "conceptual_hypothesis": ["novel_concept_binding", "concept_cluster_activation"],
            "mixed_intent_multi_clause": ["multi_intent_conflict"],
            "correction_after_confusion": ["referent_instability", "multi_intent_conflict"],
            "relationship_query": ["emotional_register_uncertainty"],
        }
        return mapping.get(signature, ["concept_cluster_activation"])

    def _lineage_context(self, crystal: Any) -> Dict[str, Any]:
        meta = getattr(crystal, "lineage_meta", {}) or {}
        return dict(meta.get("interaction_context") or {})

    def _event_signature(self, event: Mapping[str, Any]) -> str:
        raw = json.dumps(dict(event), sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def _split_compound_value(self, value: Any) -> List[str]:
        raw = str(value or "").strip()
        if not raw:
            return []
        if raw == "none_recorded":
            return []
        for separator in ("  |  ", "|", ";"):
            if separator in raw:
                return [item.strip() for item in raw.split(separator) if item.strip()]
        return [raw]

    def _first_non_empty(self, event: Mapping[str, Any], *keys: str) -> str:
        for key in keys:
            value = str(event.get(key) or "").strip()
            if value:
                return value
        return ""

    def _safe_float(self, value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _dedupe_preserve_order(self, values: Iterable[str]) -> List[str]:
        seen = set()
        result: List[str] = []
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            result.append(str(value))
        return result
