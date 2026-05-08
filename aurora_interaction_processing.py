#!/usr/bin/env python3
"""Interaction crystal formation, promotion, collapse, and routing."""
from __future__ import annotations

import re
import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from aurora_constraint_engine import (
    ConstraintVector as _ConstraintVector,
    FoundationalContract as _FoundationalContract,
    ExistenceMode as _ExistenceMode,
    GovernorWeights as _GovernorWeights,
)
_FC = _FoundationalContract()
from quasiarch_observer import CrystalInstance, CrystalOrder
try:
    from dimensional_processing_system_standalone_demo import RelationalPoint
except ImportError:
    from aurora_internal.quasiarch_observer.dimensional_processing import RelationalPoint

from aurora_interaction_engine import (
    BASE_INTERACTION_FACETS,
    COMPOSITE_INTERACTION_FACETS,
    HIGHER_INTERACTION_FACETS,
    InteractionEngine,
    InteractionQuasiInnerStrata,
)
from aurora_interaction_memory import InteractionMemory


@dataclass
class InteractionCrystalInstance(CrystalInstance):
    execution_surface: Dict[str, Any] = field(default_factory=dict)
    interaction_family: str = ""


@dataclass
class InteractionFormation:
    crystal: Optional[InteractionCrystalInstance]
    messages: List[str] = field(default_factory=list)


@dataclass
class InteractionPromotion:
    approved: bool
    from_order: str
    to_order: str
    crystal_id: str
    reasons: List[str] = field(default_factory=list)
    promoted_at: float = 0.0


@dataclass
class InteractionCollapse:
    approved: bool
    crystal_id: str
    reasons: List[str] = field(default_factory=list)
    collapsed_at: float = 0.0


class InteractionGhostRelicSystem:
    """Lightweight relic bias surface for recently collapsed interaction quasis."""

    def __init__(self) -> None:
        self._relics: Dict[str, Dict[str, Any]] = {}

    def remember(self, quasi: InteractionCrystalInstance) -> None:
        archetype = str(quasi.get_facet("interaction_archetype") or "general_response_archetype")
        self._relics[archetype] = {
            "quasi_id": quasi.crystal_id,
            "primary_response_strategy": quasi.get_facet("primary_response_strategy"),
            "secondary_response_strategy": quasi.get_facet("secondary_response_strategy"),
            "confidence": quasi.get_facet("confidence"),
            "stored_at": time.time(),
        }

    def apply(self, intake_signature: Mapping[str, Any]) -> Dict[str, Any]:
        issue = str(intake_signature.get("interpretive_issue") or "")
        if "referent" in issue:
            archetype = "callback_grounding_archetype"
        elif "self" in issue:
            archetype = "self_introspection_archetype"
        elif "concept" in issue:
            archetype = "concept_binding_archetype"
        elif "emotion" in issue:
            archetype = "emotion_attunement_archetype"
        else:
            archetype = "general_response_archetype"
        relic = dict(self._relics.get(archetype) or {})
        if relic:
            relic["relic_match"] = archetype
        return relic


class InteractionProcessing:
    """Implements the interaction-lineage promotion ladder and routing surface."""

    def __init__(
        self,
        engine: Optional[InteractionEngine] = None,
        memory: Optional[InteractionMemory] = None,
        ghost_system: Optional[InteractionGhostRelicSystem] = None,
    ) -> None:
        self.engine = engine or InteractionEngine()
        self.memory = memory or InteractionMemory(engine=self.engine)
        self.ghost_system = ghost_system or InteractionGhostRelicSystem()
        self._bases: Dict[str, InteractionCrystalInstance] = {}
        self._composites: Dict[str, InteractionCrystalInstance] = {}
        self._higher_orders: Dict[str, InteractionCrystalInstance] = {}
        self._quasicrystals: Dict[str, InteractionCrystalInstance] = {}

    def form_base_interaction(
        self,
        turn_event: Mapping[str, Any],
        tags: Optional[List[str]] = None,
    ) -> InteractionFormation:
        normalized = self.engine.normalize_turn_event(turn_event)
        messages = self.engine.validate_base_event(normalized)
        crystal = InteractionCrystalInstance(order=CrystalOrder.BASE, tags=list(tags or []))
        crystal.base_event_ids.append(crystal.crystal_id)
        for field_name in BASE_INTERACTION_FACETS:
            crystal.set_facet(field_name, normalized[field_name])
        crystal.resolution_fidelity = self.engine.resolution_fidelity(normalized["observed_effect"])
        crystal.interaction_family = self._family_key(normalized["interpretive_issue"])
        crystal.lineage_meta = {
            "family_key": crystal.interaction_family,
            "issue_category": normalized["interpretive_issue"],
            "stage": crystal.order.name,
            "interaction_context": normalized,
        }
        crystal.tags = self._unique(
            list(crystal.tags)
            + [
                "interaction_base",
                normalized["input_signature"],
                normalized["interpretive_issue"],
                normalized["processing_tier"],
            ]
        )
        for law in self.engine.point_laws_for_order("BASE"):
            score = self.engine.score_base_point(law.name, normalized)
            contradiction = score < 0.4 and law.name in {
                "intended_effect__observed_effect",
                "input_signature__processing_tier",
                "interpretive_issue__response_action",
            }
            crystal.add_point(RelationalPoint(
                law=law,
                score=score,
                evidence=f"{law.facet_a}={normalized.get(law.facet_a)!r} <-> {law.facet_b}={normalized.get(law.facet_b)!r}",
                contradiction=contradiction,
            ))
        messages.append(f"base_interaction:{crystal.crystal_id}")
        return InteractionFormation(crystal=crystal, messages=messages)

    def observe_interaction(
        self,
        turn_event: Mapping[str, Any],
        tags: Optional[List[str]] = None,
        auto_promote: bool = False,
    ) -> Dict[str, Any]:
        formation = self.form_base_interaction(turn_event, tags=tags)
        if formation.crystal is None:
            return {"base": None, "messages": formation.messages, "advance": None}
        base = formation.crystal
        self._bases[base.crystal_id] = base
        self.memory.persist(base)
        summary: Dict[str, Any] = {
            "base": base,
            "messages": formation.messages,
            "advance": None,
        }
        if auto_promote:
            summary["advance"] = self.advance_interaction_family(base.get_facet("interpretive_issue"))
        return summary

    def promote_to_composite(self, issue_family: str) -> Tuple[Optional[InteractionCrystalInstance], InteractionPromotion]:
        base_crystals = self._base_family(issue_family)
        evaluation = self._evaluate_base_to_composite(base_crystals, issue_family)
        if not evaluation.approved:
            return None, evaluation
        composite = InteractionCrystalInstance(order=CrystalOrder.COMPOSITE)
        composite.parent_ids = [crystal.crystal_id for crystal in base_crystals]
        composite.base_event_ids = [event_id for crystal in base_crystals for event_id in crystal.base_event_ids]
        composite.promoted_at = self._iso_now()
        composite.interaction_family = self._family_key(issue_family)
        for field_name in BASE_INTERACTION_FACETS:
            composite.set_facet(field_name, self._dominant_value([crystal.get_facet(field_name) for crystal in base_crystals]))
        composite.set_facet("recurrence_pattern", self.engine.derive_recurrence_pattern(base_crystals))
        composite.set_facet("distribution_context", self.engine.derive_distribution_context(base_crystals))
        composite.resolution_fidelity = statistics.mean([crystal.resolution_fidelity for crystal in base_crystals])
        composite.lineage_meta = {
            "family_key": composite.interaction_family,
            "issue_category": issue_family,
            "stage": composite.order.name,
            "event_count": len(base_crystals),
        }
        self._build_aggregate_points(composite, base_crystals, order_name="COMPOSITE")
        composite.tags = self._unique([tag for crystal in base_crystals for tag in crystal.tags] + ["interaction_composite"])
        self._composites[composite.crystal_id] = composite
        self.memory.persist(composite)
        for base in base_crystals:
            if composite.crystal_id not in base.child_ids:
                base.child_ids.append(composite.crystal_id)
            self.memory.register_lineage_edge(base, composite, "promotion")
        return composite, evaluation

    def promote_to_higher_order(self, composite: Any) -> Tuple[Optional[InteractionCrystalInstance], InteractionPromotion]:
        composite_obj = self._resolve_composite(composite)
        if composite_obj is None:
            return None, InteractionPromotion(False, "COMPOSITE", "HIGHER_ORDER", str(composite), ["composite_missing"], 0.0)
        base_crystals = self._crystals_from_base_ids(composite_obj.base_event_ids)
        evaluation = self._evaluate_composite_to_higher(composite_obj, base_crystals)
        if not evaluation.approved:
            return None, evaluation
        higher = InteractionCrystalInstance(order=CrystalOrder.HIGHER_ORDER)
        higher.parent_ids = [composite_obj.crystal_id]
        higher.base_event_ids = list(composite_obj.base_event_ids)
        higher.promoted_at = self._iso_now()
        higher.interaction_family = composite_obj.interaction_family
        for field_name in COMPOSITE_INTERACTION_FACETS:
            higher.set_facet(field_name, composite_obj.get_facet(field_name))
        strategy_class = self.engine.derive_response_strategy_class(base_crystals, composite_obj)
        higher.set_facet("response_strategy_class", strategy_class)
        higher.set_facet("strategy_outcome_profile", self.engine.derive_outcome_profile(base_crystals, strategy_class))
        higher.set_facet("failure_modes", self.engine.derive_failure_modes(base_crystals))
        higher.set_facet("applicability_conditions", self.engine.derive_applicability_conditions(base_crystals, composite_obj))
        higher.resolution_fidelity = statistics.mean([crystal.resolution_fidelity for crystal in base_crystals]) if base_crystals else 0.0
        higher.lineage_meta = {
            "family_key": higher.interaction_family,
            "issue_category": composite_obj.get_facet("interpretive_issue"),
            "stage": higher.order.name,
            "event_count": len(base_crystals),
        }
        self._build_aggregate_points(higher, base_crystals, order_name="HIGHER_ORDER")
        higher.tags = self._unique(list(composite_obj.tags) + ["interaction_higher_order", strategy_class])
        self._higher_orders[higher.crystal_id] = higher
        self.memory.persist(higher)
        if higher.crystal_id not in composite_obj.child_ids:
            composite_obj.child_ids.append(higher.crystal_id)
        self.memory.register_lineage_edge(composite_obj, higher, "promotion")
        return higher, evaluation

    def collapse_to_interaction_quasi(self, higher: Any) -> Tuple[Optional[InteractionCrystalInstance], InteractionCollapse]:
        higher_obj = self._resolve_higher(higher)
        if higher_obj is None:
            return None, InteractionCollapse(False, str(higher), ["higher_missing"], 0.0)
        base_crystals = self._crystals_from_base_ids(higher_obj.base_event_ids)
        evaluation = self._evaluate_higher_to_quasi(higher_obj, base_crystals)
        if not evaluation.approved:
            return None, evaluation
        quasi = InteractionCrystalInstance(order=CrystalOrder.QUASI)
        quasi.parent_ids = [higher_obj.crystal_id]
        quasi.base_event_ids = list(higher_obj.base_event_ids)
        quasi.promoted_at = self._iso_now()
        quasi.interaction_family = higher_obj.interaction_family
        ranked_strategies = self.engine.rank_response_strategies(base_crystals, higher_obj)
        primary = ranked_strategies[0] if ranked_strategies else str(higher_obj.get_facet("response_strategy_class") or "ambiguity_reduction_then_response")
        secondary = ranked_strategies[1] if len(ranked_strategies) > 1 else "request_missing_context"
        confidence = self._compute_quasi_confidence(base_crystals, higher_obj)
        failure_counterexamples = self._failure_counterexamples(base_crystals)
        strata = InteractionQuasiInnerStrata(
            representative_interactions=self._representative_interactions(base_crystals),
            recurrence_summary={
                "pattern": higher_obj.get_facet("recurrence_pattern"),
                "distribution": higher_obj.get_facet("distribution_context"),
                "event_count": len(base_crystals),
            },
            strategy_success_stats={primary: round(confidence, 4)},
            failure_counterexamples=failure_counterexamples,
            coherence_index=self.engine.compute_coherence_index(base_crystals),
            novelty_index=self.engine.compute_novelty_index(base_crystals),
            genealogy_depth=len(base_crystals),
        )
        quasi.quasi_strata = strata
        quasi.set_facet("interaction_archetype", self.engine.classify_interaction_archetype(higher_obj))
        quasi.set_facet("primary_response_strategy", primary)
        quasi.set_facet("secondary_response_strategy", secondary)
        quasi.set_facet("applicability_boundary", str(higher_obj.get_facet("applicability_conditions") or ""))
        quasi.set_facet("confidence", round(confidence, 4))
        quasi.set_facet("failure_indicators", str(higher_obj.get_facet("failure_modes") or "none_recorded"))
        quasi.set_facet("expected_effects", self.engine.derive_expected_effects(base_crystals))
        quasi.set_facet("escalation_trigger", self.engine.derive_escalation_trigger(confidence, failure_counterexamples, higher_obj))
        quasi.resolution_fidelity = confidence
        quasi.execution_surface = self.engine.build_execution_surface(quasi.facet_values)
        quasi.lineage_meta = {
            "family_key": quasi.interaction_family,
            "issue_category": higher_obj.get_facet("interpretive_issue"),
            "stage": quasi.order.name,
            "event_count": len(base_crystals),
        }
        quasi.tags = self._unique(list(higher_obj.tags) + ["interaction_quasi", str(quasi.get_facet("interaction_archetype")), primary])
        self._quasicrystals[quasi.crystal_id] = quasi
        self.memory.persist(quasi)
        if quasi.crystal_id not in higher_obj.child_ids:
            higher_obj.child_ids.append(quasi.crystal_id)
        self.memory.register_lineage_edge(higher_obj, quasi, "collapse")
        self.memory.relic(higher_obj)
        self.ghost_system.remember(quasi)
        return quasi, evaluation

    def advance_interaction_family(self, issue_family: str) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "issue_family": issue_family,
            "composite": None,
            "composite_eval": None,
            "higher": None,
            "higher_eval": None,
            "quasi": None,
            "quasi_eval": None,
        }
        composite, composite_eval = self.promote_to_composite(issue_family)
        summary["composite"] = composite
        summary["composite_eval"] = composite_eval
        if composite is None:
            return summary
        higher, higher_eval = self.promote_to_higher_order(composite)
        summary["higher"] = higher
        summary["higher_eval"] = higher_eval
        if higher is None:
            return summary
        quasi, quasi_eval = self.collapse_to_interaction_quasi(higher)
        summary["quasi"] = quasi
        summary["quasi_eval"] = quasi_eval
        return summary

    def retrieve_best_interaction_quasi(self, intake_signature: Mapping[str, Any], min_confidence: float = 0.55, top_k: int = 3) -> List[Dict[str, Any]]:
        signature = self.engine.build_intake_signature(intake_signature)
        return self.memory.retrieve_best_interaction_quasi(signature, min_confidence=min_confidence, top_k=top_k)

    def apply_interaction_relic(self, current_interaction: Mapping[str, Any]) -> Dict[str, Any]:
        signature = self.engine.build_intake_signature(current_interaction)
        relic_bias = self.ghost_system.apply(signature)
        candidates = self.memory.retrieve_best_interaction_quasi(signature, min_confidence=0.45, top_k=1)
        return {
            "intake_signature": signature,
            "relic_bias": relic_bias,
            "quasi_candidate": candidates[0] if candidates else None,
        }

    def route_interaction(self, turn_event: Mapping[str, Any], min_confidence: float = 0.55) -> Dict[str, Any]:
        intake_signature = self.engine.build_intake_signature(turn_event)
        matches = self.memory.retrieve_best_interaction_quasi(intake_signature, min_confidence=min_confidence, top_k=3)
        relic_bias = self.ghost_system.apply(intake_signature)
        if not matches:
            return {
                "intake_signature": intake_signature,
                "selected_quasi": None,
                "execution_surface": None,
                "relic_bias": relic_bias,
                "escalate": True,
                "reason": "novel_interaction_outside_indexed_archetypes",
            }
        selected = matches[0]
        competing = len(matches) > 1 and abs(matches[0]["match_score"] - matches[1]["match_score"]) <= 0.05
        execution_surface = dict(selected["execution_surface"])
        escalate = bool(competing or selected["match_score"] < 0.45)
        reason = "multiple_competing_quasis" if competing else execution_surface.get("escalation_trigger")
        return {
            "intake_signature": intake_signature,
            "selected_quasi": selected,
            "execution_surface": execution_surface,
            "relic_bias": relic_bias,
            "escalate": escalate,
            "reason": reason if escalate else "quasi_ready",
        }

    def _status_snapshot(self) -> Dict[str, Any]:
        nodes = list(getattr(self.memory, "_nodes", {}).values())
        active = [node for node in nodes if not getattr(node, "is_relic", False)]
        quasis = [node for node in active if str(getattr(node, "order", "")) == "QUASI"]
        latest = quasis[-1] if quasis else None
        return {
            "base_count": len([node for node in active if str(getattr(node, "order", "")) == "BASE"]),
            "composite_count": len([node for node in active if str(getattr(node, "order", "")) == "COMPOSITE"]),
            "higher_count": len([node for node in active if str(getattr(node, "order", "")) == "HIGHER_ORDER"]),
            "quasi_count": len(quasis),
            "relic_count": len([node for node in nodes if getattr(node, "is_relic", False)]),
            "ghost_relics": len(getattr(self.ghost_system, "_relics", {}) or {}),
            "latest_archetype": str((latest.payload.get("interaction_archetype") if latest else "") or ""),
            "latest_strategy": str((latest.payload.get("primary_response_strategy") if latest else "") or ""),
            "latest_confidence": float((latest.payload.get("confidence") if latest else 0.0) or 0.0),
        }

    def get_status(self) -> Dict[str, Any]:
        status = self._status_snapshot()
        cp = self.constraint_profile()
        status["lineage_signature"] = cp.weighted_signature() if hasattr(cp, "weighted_signature") else "XTNBA"
        status["runtime_regime"] = self.runtime_regime()
        status["language_projection"] = self.language_projection()
        return status

    def _constraint_axes(self) -> Dict[str, float]:
        status = self._status_snapshot()
        active_total = float(status["base_count"] + status["composite_count"] + status["higher_count"] + status["quasi_count"])
        return {
            "X": min(1.0, 0.20 + active_total / 120.0),
            "T": min(1.0, 0.18 + status["composite_count"] / 40.0 + status["higher_count"] / 40.0),
            "N": min(1.0, 0.18 + status["base_count"] / 80.0),
            "B": min(1.0, 0.22 + status["relic_count"] / 80.0 + status["ghost_relics"] / 40.0),
            "A": min(1.0, 0.22 + status["quasi_count"] / 40.0),
        }

    def constraint_profile(self) -> _ConstraintVector:
        ax = self._constraint_axes()
        return _ConstraintVector(
            X=max(1e-9, float(ax.get("X", 0.2))),
            T=float(ax.get("T", 0.18)),
            N=float(ax.get("N", 0.18)),
            B=float(ax.get("B", 0.22)),
            A=float(ax.get("A", 0.22)),
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
            "unit_state": self._status_snapshot(),
        }

    def _evaluate_base_to_composite(self, base_crystals: Sequence[InteractionCrystalInstance], issue_family: str) -> InteractionPromotion:
        reasons: List[str] = []
        if len(base_crystals) < 3:
            reasons.append("recurring_interaction_family_missing")
        avg_fidelity = statistics.mean([crystal.resolution_fidelity for crystal in base_crystals]) if base_crystals else 0.0
        if avg_fidelity < 0.45:
            reasons.append("stable_intended_to_observed_relation_missing")
        consistency = self._point_consistency(base_crystals, "intended_effect__observed_effect")
        if consistency < 0.5:
            reasons.append("nontrivial_point_consistency_missing")
        return InteractionPromotion(
            approved=not reasons,
            from_order="BASE",
            to_order="COMPOSITE",
            crystal_id=issue_family,
            reasons=reasons,
            promoted_at=time.time() if not reasons else 0.0,
        )

    def _evaluate_composite_to_higher(self, composite: InteractionCrystalInstance, base_crystals: Sequence[InteractionCrystalInstance]) -> InteractionPromotion:
        reasons: List[str] = []
        if len(base_crystals) < 3:
            reasons.append("repeatable_strategy_shape_missing")
        avg_fidelity = statistics.mean([crystal.resolution_fidelity for crystal in base_crystals]) if base_crystals else 0.0
        if avg_fidelity < 0.55:
            reasons.append("outcome_profile_too_weak")
        failure_density = self._failure_density(base_crystals)
        if failure_density > 0.4:
            reasons.append("contradiction_profile_unbounded")
        return InteractionPromotion(
            approved=not reasons,
            from_order="COMPOSITE",
            to_order="HIGHER_ORDER",
            crystal_id=composite.crystal_id,
            reasons=reasons,
            promoted_at=time.time() if not reasons else 0.0,
        )

    def _evaluate_higher_to_quasi(self, higher: InteractionCrystalInstance, base_crystals: Sequence[InteractionCrystalInstance]) -> InteractionCollapse:
        reasons: List[str] = []
        if len(base_crystals) < 3:
            reasons.append("stable_primary_strategy_missing")
        avg_fidelity = statistics.mean([crystal.resolution_fidelity for crystal in base_crystals]) if base_crystals else 0.0
        if avg_fidelity < 0.6:
            reasons.append("confidence_below_threshold")
        failure_density = self._failure_density(base_crystals)
        if failure_density > 0.35:
            reasons.append("failure_modes_unbounded")
        applicability = str(higher.get_facet("applicability_conditions") or "")
        if not applicability:
            reasons.append("applicability_conditions_missing")
        return InteractionCollapse(
            approved=not reasons,
            crystal_id=higher.crystal_id,
            reasons=reasons,
            collapsed_at=time.time() if not reasons else 0.0,
        )

    def _build_aggregate_points(self, target: InteractionCrystalInstance, base_crystals: Sequence[InteractionCrystalInstance], order_name: str) -> None:
        for law in self.engine.point_laws_for_order(order_name):
            if law.name in {point.name for point in target.relational_points.values()}:
                continue
            if law.name in {point.name for point in base_crystals[0].relational_points.values()} if base_crystals else False:
                scores = [
                    crystal.relational_points[law.name].score
                    for crystal in base_crystals
                    if law.name in crystal.relational_points
                ]
                contradiction = any(
                    crystal.relational_points[law.name].contradiction
                    for crystal in base_crystals
                    if law.name in crystal.relational_points
                )
                score = statistics.mean(scores) if scores else 0.0
            else:
                score = self._derived_point_score(law.name, target, base_crystals)
                contradiction = score < 0.35
            target.add_point(RelationalPoint(
                law=law,
                score=round(score, 4),
                evidence=f"aggregated:{order_name.lower()}",
                contradiction=contradiction,
            ))

    def _derived_point_score(self, point_name: str, target: InteractionCrystalInstance, base_crystals: Sequence[InteractionCrystalInstance]) -> float:
        avg_fidelity = statistics.mean([crystal.resolution_fidelity for crystal in base_crystals]) if base_crystals else 0.0
        recurrence = str(target.get_facet("recurrence_pattern") or "")
        distribution = str(target.get_facet("distribution_context") or "")
        if point_name.endswith("__recurrence_pattern"):
            if recurrence.startswith("periodic"):
                return 0.9
            if recurrence.startswith("cascading"):
                return 0.75
            return 0.55
        if point_name.endswith("__distribution_context"):
            if distribution.startswith("cross_stage"):
                return 0.85
            if distribution.startswith("multi_stage"):
                return 0.7
            return 0.55
        if point_name.endswith("__response_strategy_class"):
            return min(1.0, avg_fidelity + 0.15)
        if point_name.endswith("__outcome_profile") or point_name == "outcome_profile__observed_effect":
            return avg_fidelity
        if point_name.endswith("__failure_modes") or point_name == "failure_modes__interpretive_issue":
            return max(0.0, 1.0 - self._failure_density(base_crystals))
        if point_name.endswith("__applicability_conditions"):
            return min(1.0, avg_fidelity + 0.1)
        return avg_fidelity or 0.5

    def _base_family(self, issue_family: str) -> List[InteractionCrystalInstance]:
        return [
            crystal for crystal in self._bases.values()
            if str(crystal.get_facet("interpretive_issue") or "") == str(issue_family)
        ]

    def _crystals_from_base_ids(self, base_ids: Sequence[str]) -> List[InteractionCrystalInstance]:
        result: List[InteractionCrystalInstance] = []
        for base_id in base_ids:
            crystal = self._bases.get(str(base_id))
            if crystal is not None:
                result.append(crystal)
        return result

    def _resolve_composite(self, composite: Any) -> Optional[InteractionCrystalInstance]:
        if isinstance(composite, InteractionCrystalInstance):
            return composite
        return self._composites.get(str(composite))

    def _resolve_higher(self, higher: Any) -> Optional[InteractionCrystalInstance]:
        if isinstance(higher, InteractionCrystalInstance):
            return higher
        return self._higher_orders.get(str(higher))

    def _compute_quasi_confidence(self, base_crystals: Sequence[InteractionCrystalInstance], higher: InteractionCrystalInstance) -> float:
        if not base_crystals:
            return 0.0
        avg_fidelity = statistics.mean([crystal.resolution_fidelity for crystal in base_crystals])
        coherence = self.engine.compute_coherence_index(base_crystals)
        failure_penalty = self._failure_density(base_crystals) * 0.35
        confidence = (avg_fidelity * 0.6) + (coherence * 0.4) - failure_penalty
        return round(max(0.0, min(1.0, confidence)), 4)

    def _failure_density(self, base_crystals: Sequence[InteractionCrystalInstance]) -> float:
        if not base_crystals:
            return 0.0
        failures = sum(1 for crystal in base_crystals if crystal.get_facet("observed_effect") in {"regression_introduced", "no_change_observed"})
        return failures / len(base_crystals)

    def _point_consistency(self, base_crystals: Sequence[InteractionCrystalInstance], point_name: str) -> float:
        scores = [
            crystal.relational_points[point_name].score
            for crystal in base_crystals
            if point_name in crystal.relational_points
        ]
        return statistics.mean(scores) if scores else 0.0

    def _representative_interactions(self, base_crystals: Sequence[InteractionCrystalInstance]) -> List[Dict[str, Any]]:
        ranked = sorted(base_crystals, key=lambda crystal: crystal.resolution_fidelity, reverse=True)
        return [
            {
                "crystal_id": crystal.crystal_id,
                "input_signature": crystal.get_facet("input_signature"),
                "interpretive_issue": crystal.get_facet("interpretive_issue"),
                "processing_tier": crystal.get_facet("processing_tier"),
                "response_action": crystal.get_facet("response_action"),
                "observed_effect": crystal.get_facet("observed_effect"),
                "resolution_fidelity": crystal.resolution_fidelity,
            }
            for crystal in ranked[:5]
        ]

    def _failure_counterexamples(self, base_crystals: Sequence[InteractionCrystalInstance]) -> List[Dict[str, Any]]:
        return [
            {
                "crystal_id": crystal.crystal_id,
                "input_signature": crystal.get_facet("input_signature"),
                "interpretive_issue": crystal.get_facet("interpretive_issue"),
                "observed_effect": crystal.get_facet("observed_effect"),
            }
            for crystal in base_crystals
            if crystal.get_facet("observed_effect") in {"regression_introduced", "no_change_observed", "resolved_partially__followup_gap_appeared"}
        ]

    def _family_key(self, issue_family: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", str(issue_family or "unknown").lower()).strip("_")
        return f"interaction_family::{slug or 'unknown'}"

    def _dominant_value(self, values: Sequence[Any]) -> Any:
        tally: Dict[str, int] = {}
        lookup: Dict[str, Any] = {}
        for value in values:
            key = str(value or "").strip()
            if not key:
                continue
            lookup[key] = value
            tally[key] = tally.get(key, 0) + 1
        if not tally:
            return ""
        return lookup[max(tally, key=lambda item: tally[item])]

    def _unique(self, values: Sequence[str]) -> List[str]:
        seen = set()
        result: List[str] = []
        for value in values:
            text = str(value or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result

    def _iso_now(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
