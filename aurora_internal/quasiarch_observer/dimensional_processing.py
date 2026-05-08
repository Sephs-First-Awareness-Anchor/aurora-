"""
dimensional_processing_system_standalone_demo.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Authors : Sunni (Sir) Morningstar and Cael Devo
Purpose : Crystal lifecycle and evolution mechanics — the metabolism.
          Owns: formation → promotion → collapse → rotation.
          Does NOT define facet/point semantics (crystal_engine).
          Does NOT persist data (dimensional_memory).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import statistics
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .crystal_engine import (
    ALL_ROTATIONS,
    BASE_FACETS,
    COMPOSITE_FACETS,
    HIGHER_ORDER_FACETS,
    QUASI_OUTER_FACETS,
    CrystalEngine,
    CrystalOrder,
    FacetLaw,
    InferenceKind,
    PointRole,
    PromotionCriteria,
    QuasiInnerStrata,
    RelationalPointLaw,
    RotationDefinition,
    ValueDomain,
)


# ══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ══════════════════════════════════════════════════════════════════════════════

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RelationalPoint:
    """
    Live instantiation of a RelationalPointLaw within a crystal.

    Attributes
    ----------
    law        : The semantic law governing this point.
    score      : 0.0–1.0 strength/quality of the relation in this event.
    evidence   : Human-readable note or structured evidence string.
    contradiction : If True, this point has fired a contradiction signal.
    """
    law           : RelationalPointLaw
    score         : float  = 0.0
    evidence      : str    = ""
    contradiction : bool   = False

    @property
    def name(self) -> str:
        return self.law.name


@dataclass
class CrystalInstance:
    """
    A live crystal at a specific order.

    Attributes
    ----------
    crystal_id        : UUID identifying this crystal node.
    order             : Current CrystalOrder.
    facet_values      : Dict of facet_name → value.
    relational_points : Dict of point_name → RelationalPoint.
    resolution_fidelity : Most recent resolution score for this crystal.
    base_event_ids    : UUIDs of base-crystal events contributing to this node.
    parent_ids        : UUIDs of crystals from which this was promoted/derived.
    child_ids         : UUIDs of crystals derived from this one.
    created_at        : ISO timestamp of formation.
    promoted_at       : ISO timestamp of promotion, if applicable.
    promotion_ready   : Whether this crystal has passed promotion criteria.
    quasi_strata      : Populated only when order == QUASI.
    rotation_history  : List of rotation result records.
    tags              : Arbitrary string labels for retrieval.
    lineage_meta      : Versioning metadata for issue-family evolution.
    """
    crystal_id          : str                         = field(default_factory=lambda: str(uuid.uuid4()))
    order               : CrystalOrder               = CrystalOrder.BASE
    facet_values        : Dict[str, Any]             = field(default_factory=dict)
    relational_points   : Dict[str, RelationalPoint] = field(default_factory=dict)
    resolution_fidelity : float                      = 0.0
    base_event_ids      : List[str]                  = field(default_factory=list)
    parent_ids          : List[str]                  = field(default_factory=list)
    child_ids           : List[str]                  = field(default_factory=list)
    created_at          : str                        = field(default_factory=_utcnow)
    promoted_at         : Optional[str]              = None
    promotion_ready     : bool                       = False
    quasi_strata        : Optional[QuasiInnerStrata] = None
    rotation_history    : List[Dict[str, Any]]       = field(default_factory=list)
    tags                : List[str]                  = field(default_factory=list)
    lineage_meta        : Dict[str, Any]             = field(default_factory=dict)

    def get_facet(self, name: str) -> Any:
        return self.facet_values.get(name)

    def set_facet(self, name: str, value: Any) -> None:
        self.facet_values[name] = value

    def get_point(self, name: str) -> Optional[RelationalPoint]:
        return self.relational_points.get(name)

    def add_point(self, point: RelationalPoint) -> None:
        self.relational_points[point.name] = point

    def to_dict(self) -> Dict[str, Any]:
        return {
            "crystal_id"         : self.crystal_id,
            "order"              : self.order.name,
            "facet_values"       : self.facet_values,
            "resolution_fidelity": self.resolution_fidelity,
            "base_event_ids"     : self.base_event_ids,
            "parent_ids"         : self.parent_ids,
            "child_ids"          : self.child_ids,
            "created_at"         : self.created_at,
            "promoted_at"        : self.promoted_at,
            "promotion_ready"    : self.promotion_ready,
            "tags"               : self.tags,
            "lineage_meta"       : self.lineage_meta,
            "relational_points"  : {
                k: {
                    "score"        : v.score,
                    "evidence"     : v.evidence,
                    "contradiction": v.contradiction,
                }
                for k, v in self.relational_points.items()
            },
        }


@dataclass
class PromotionResult:
    """Result of a promotion evaluation."""
    approved       : bool
    from_order     : CrystalOrder
    to_order       : CrystalOrder
    crystal_id     : str
    reasons        : List[str]         = field(default_factory=list)
    promoted_at    : Optional[str]     = None
    new_crystal_id : Optional[str]     = None


@dataclass
class RotationResult:
    """Result of applying a rotation perspective to a quasicrystal."""
    rotation_name      : str
    crystal_id         : str
    hypotheses         : List[Dict[str, Any]]
    pivot_point_scores : Dict[str, float]
    executed_at        : str = field(default_factory=_utcnow)


@dataclass
class StrategyHypothesis:
    """A generated strategy recommendation for a new diagnostic event."""
    issue_archetype      : str
    recommended_strategy : str
    confidence           : float
    applicability_met    : bool
    failure_risk         : str
    escalation_risk      : str
    source_quasi_id      : str


@dataclass
class DoctrineObject:
    """
    Actionable doctrine surface derived from a quasicrystal.

    The outer shell is operational. The inner strata remain attached so the
    doctrine stays traceable back into its event ancestry.
    """
    quasi_id                   : str
    family_key                 : str
    lineage_version            : int
    is_active_version          : bool
    supersedes                 : str
    superseded_by              : str
    issue_archetype            : str
    primary_strategy           : str
    secondary_strategy         : str
    applicability_boundary     : str
    confidence                 : float
    failure_indicators         : List[str]
    expected_effects           : List[str]
    escalation_trigger         : str
    representative_base_events : List[Dict[str, Any]]
    recurrence_summary         : Dict[str, Any]
    strategy_success_stats     : Dict[str, float]
    failure_counterexamples    : List[Dict[str, Any]]
    genealogy_depth            : int
    coherence_index            : float
    novelty_index              : float
    available_rotations        : List[str]
    rotation_history           : List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quasi_id": self.quasi_id,
            "family_key": self.family_key,
            "lineage_version": self.lineage_version,
            "is_active_version": self.is_active_version,
            "supersedes": self.supersedes,
            "superseded_by": self.superseded_by,
            "issue_archetype": self.issue_archetype,
            "primary_strategy": self.primary_strategy,
            "secondary_strategy": self.secondary_strategy,
            "applicability_boundary": self.applicability_boundary,
            "confidence": self.confidence,
            "failure_indicators": list(self.failure_indicators),
            "expected_effects": list(self.expected_effects),
            "escalation_trigger": self.escalation_trigger,
            "representative_base_events": list(self.representative_base_events),
            "recurrence_summary": dict(self.recurrence_summary),
            "strategy_success_stats": dict(self.strategy_success_stats),
            "failure_counterexamples": list(self.failure_counterexamples),
            "genealogy_depth": self.genealogy_depth,
            "coherence_index": self.coherence_index,
            "novelty_index": self.novelty_index,
            "available_rotations": list(self.available_rotations),
            "rotation_history": list(self.rotation_history),
        }


# ══════════════════════════════════════════════════════════════════════════════
# FORMATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class CrystalFormation:
    """
    Handles instantiation of base crystals from raw diagnostic event data.

    A diagnostic event is a dict with keys matching base facet names.
    Formation validates all facets, constructs relational points with
    initial scores, and computes resolution_fidelity.
    """

    _engine = CrystalEngine()

    # Observed-effect → resolution_fidelity mapping
    _FIDELITY_MAP: Dict[str, float] = {
        "resolved_fully"                            : 1.0,
        "resolved_partially__downstream_issue_appeared" : 0.6,
        "resolved_partially"                        : 0.5,
        "no_change_observed"                        : 0.0,
        "regression_introduced"                     : 0.0,
        "pending_verification"                      : 0.3,
    }

    @classmethod
    def form_base_crystal(
        cls,
        event: Dict[str, Any],
        tags: Optional[List[str]] = None,
    ) -> Tuple[Optional[CrystalInstance], List[str]]:
        """
        Form a base crystal from a raw diagnostic event dict.

        Parameters
        ----------
        event : Dict with keys: target, issue, logic_tier, intervention,
                intended_effect, observed_effect.  All required.
        tags  : Optional string labels for retrieval.

        Returns
        -------
        (CrystalInstance or None, list of validation/warning messages)
        """
        messages: List[str] = []
        order = CrystalOrder.BASE

        # Validate all required facets are present
        required = list(BASE_FACETS.keys())
        for fname in required:
            if fname not in event:
                messages.append(f"MISSING REQUIRED FACET: '{fname}'")
        if any(m.startswith("MISSING") for m in messages):
            return None, messages

        # Validate facet values against schema
        for fname in required:
            ok, reason = cls._engine.validate_facet_value(order, fname, event[fname])
            if not ok:
                messages.append(f"VALIDATION WARNING [{fname}]: {reason}")

        # Build instance
        crystal = CrystalInstance(
            order=order,
            tags=list(tags or []),
        )
        crystal.base_event_ids.append(crystal.crystal_id)

        # Populate facets
        for fname in required:
            crystal.set_facet(fname, event[fname])

        # Compute resolution_fidelity
        obs = str(event.get("observed_effect", "")).lower()
        crystal.resolution_fidelity = cls._FIDELITY_MAP.get(obs, 0.2)

        # Build relational points
        cls._build_base_points(crystal, messages)

        messages.append(
            f"Base crystal formed: {crystal.crystal_id}  "
            f"fidelity={crystal.resolution_fidelity:.2f}"
        )
        return crystal, messages

    @classmethod
    def _build_base_points(
        cls,
        crystal: CrystalInstance,
        messages: List[str],
    ) -> None:
        """Build and score all 12 base relational points."""
        from .crystal_engine import BASE_POINTS
        for point_law in BASE_POINTS.values():
            ok, reason = cls._engine.validate_point(
                CrystalOrder.BASE, point_law.facet_a, point_law.facet_b
            )
            if not ok:
                messages.append(f"POINT SKIP [{point_law.name}]: {reason}")
                continue

            val_a = crystal.get_facet(point_law.facet_a)
            val_b = crystal.get_facet(point_law.facet_b)

            score = cls._score_base_point(point_law, val_a, val_b)
            contradiction = cls._detect_contradiction(point_law, val_a, val_b)

            rp = RelationalPoint(
                law=point_law,
                score=score,
                evidence=f"{point_law.facet_a}={val_a!r}  ↔  {point_law.facet_b}={val_b!r}",
                contradiction=contradiction,
            )
            crystal.add_point(rp)

            if contradiction:
                messages.append(
                    f"CONTRADICTION at {point_law.name}: "
                    f"[{val_a!r}] ↔ [{val_b!r}]"
                )

    @classmethod
    def _score_base_point(
        cls,
        law: RelationalPointLaw,
        val_a: Any,
        val_b: Any,
    ) -> float:
        """
        Compute an initial point score.  Uses the resolution_fidelity mapping
        for the intended→observed arc; uses presence/absence elsewhere.
        """
        if law.name == "intended_effect__observed_effect":
            obs = str(val_b).lower()
            return cls._FIDELITY_MAP.get(obs, 0.2)

        if law.name == "observed_effect__issue":
            obs = str(val_a).lower()
            if "resolved_fully" in obs:
                return 1.0
            if "partially" in obs:
                return 0.5
            return 0.0

        if law.name == "target__intervention":
            # Invasiveness: a rough heuristic from string length of intervention
            inv = str(val_b)
            if "cross_module" in inv or "rewrite" in inv or "systemic" in inv:
                return 1.0
            if "rename" in inv or "bridge" in inv:
                return 0.5
            return 0.2

        # Default: both values present = 0.7
        if val_a and val_b:
            return 0.7
        return 0.0

    @classmethod
    def _detect_contradiction(
        cls,
        law: RelationalPointLaw,
        val_a: Any,
        val_b: Any,
    ) -> bool:
        """Simple contradiction detection based on known pathological pairs."""
        if law.name == "intended_effect__observed_effect":
            # resolution claimed but observed says otherwise
            obs = str(val_b).lower()
            return obs in ("regression_introduced",)
        if law.name == "observed_effect__issue":
            obs = str(val_a).lower()
            # "resolved_fully" but same issue appears again — can't detect at
            # formation time; deferred to composite analysis
            return False
        return False


# ══════════════════════════════════════════════════════════════════════════════
# PROMOTION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class CrystalPromotion:
    """
    Evaluates promotion criteria and executes crystal level transitions.

    Promotion assembles a new higher-order crystal by:
      1. Aggregating facet values across the contributing crystals
      2. Carrying forward points per their survival rules
      3. Adding new facets and points for the new order
      4. Computing the new crystal's resolution_fidelity from the aggregate

    Responsibility split:
      - This class owns the mechanics of aggregation and new-facet derivation.
      - CrystalEngine owns what the facets mean.
      - Dimensional memory persists the resulting instances.
    """

    _engine = CrystalEngine()

    # ── Base → Composite ──────────────────────────────────────────────────────

    @classmethod
    def evaluate_base_to_composite(
        cls,
        base_crystals: List[CrystalInstance],
    ) -> PromotionResult:
        """
        Evaluate whether a collection of base crystals qualifies for
        composite formation.  All base crystals must share the same
        issue category and logic_tier.
        """
        cid = base_crystals[0].crystal_id if base_crystals else "none"
        criteria = cls._engine.get_promotion_criteria(
            CrystalOrder.BASE, CrystalOrder.COMPOSITE
        )
        if criteria is None:
            return PromotionResult(
                approved=False, from_order=CrystalOrder.BASE,
                to_order=CrystalOrder.COMPOSITE, crystal_id=cid,
                reasons=["No promotion criteria registered."],
            )

        reasons: List[str] = []

        # Event count
        count = len(base_crystals)
        if count < criteria.min_base_event_count:
            reasons.append(
                f"Insufficient base events: {count} < {criteria.min_base_event_count}"
            )

        # Issue category homogeneity
        issues = {c.get_facet("issue") for c in base_crystals}
        if len(issues) > 1:
            reasons.append(
                f"Issue family heterogeneous: {issues}.  "
                "Split required before composite promotion."
            )

        # Recurrence strength — simplified as event count ratio
        recurrence_strength = min(1.0, count / 10.0)
        if recurrence_strength < criteria.min_recurrence_strength:
            reasons.append(
                f"Recurrence strength {recurrence_strength:.2f} < "
                f"{criteria.min_recurrence_strength}"
            )

        approved = len(reasons) == 0
        return PromotionResult(
            approved=approved,
            from_order=CrystalOrder.BASE,
            to_order=CrystalOrder.COMPOSITE,
            crystal_id=cid,
            reasons=reasons,
            promoted_at=_utcnow() if approved else None,
        )

    @classmethod
    def promote_to_composite(
        cls,
        base_crystals: List[CrystalInstance],
        evaluation: PromotionResult,
    ) -> Optional[CrystalInstance]:
        """
        Execute base → composite promotion.
        Returns the new composite CrystalInstance, or None if not approved.
        """
        if not evaluation.approved:
            return None

        composite = CrystalInstance(order=CrystalOrder.COMPOSITE)
        composite.parent_ids = [c.crystal_id for c in base_crystals]
        composite.base_event_ids = [
            eid for c in base_crystals for eid in c.base_event_ids
        ]
        composite.promoted_at = evaluation.promoted_at

        # Aggregate base facet values (dominant value per facet)
        for fname in BASE_FACETS:
            values = [c.get_facet(fname) for c in base_crystals if c.get_facet(fname)]
            composite.set_facet(fname, cls._dominant_value(values))

        # Derive composite-level facets
        recurrence = cls._derive_recurrence_pattern(base_crystals)
        distribution = cls._derive_distribution_context(base_crystals)
        composite.set_facet("recurrence_pattern", recurrence)
        composite.set_facet("distribution_context", distribution)

        # Compute aggregated resolution_fidelity
        fidelities = [c.resolution_fidelity for c in base_crystals]
        composite.resolution_fidelity = statistics.mean(fidelities) if fidelities else 0.0

        # Build composite points (carry forward base points + new composite points)
        cls._build_composite_points(composite, base_crystals)

        composite.tags = list({tag for c in base_crystals for tag in c.tags})
        composite.tags.append("composite")

        return composite

    @classmethod
    def _derive_recurrence_pattern(cls, base_crystals: List[CrystalInstance]) -> str:
        count = len(base_crystals)
        targets = {c.get_facet("target") for c in base_crystals}
        tiers   = {c.get_facet("logic_tier") for c in base_crystals}

        if len(tiers) > 2:
            return "cascading__cross_tier"
        if len(targets) == 1:
            if count >= 4:
                return "periodic__single_target"
            return "sporadic__single_target"
        if len(targets) <= 3:
            return "sporadic__same_tier"
        return "cascading__cross_tier"

    @classmethod
    def _derive_distribution_context(cls, base_crystals: List[CrystalInstance]) -> str:
        targets = {c.get_facet("target") for c in base_crystals}
        tiers   = {c.get_facet("logic_tier") for c in base_crystals}
        if len(targets) == 1:
            return "single_module__isolated"
        if len(tiers) == 1:
            return "multi_module__same_tier"
        if len(tiers) <= 2:
            return "cross_tier__limited"
        return "pipeline_wide__all_stages"

    @classmethod
    def _build_composite_points(
        cls,
        composite: CrystalInstance,
        base_crystals: List[CrystalInstance],
    ) -> None:
        """Carry forward base points (averaged scores) and add composite points."""
        from .crystal_engine import BASE_POINTS, COMPOSITE_POINTS

        # Carry forward base points with averaged scores
        for pname, plaw in BASE_POINTS.items():
            scores = [
                c.relational_points[pname].score
                for c in base_crystals
                if pname in c.relational_points
            ]
            avg_score = statistics.mean(scores) if scores else 0.0
            contradictions = any(
                c.relational_points[pname].contradiction
                for c in base_crystals
                if pname in c.relational_points
            )
            composite.add_point(RelationalPoint(
                law=plaw,
                score=avg_score,
                evidence=f"Aggregated from {len(scores)} base events",
                contradiction=contradictions,
            ))

        # New composite points
        new_points = {
            k: v for k, v in COMPOSITE_POINTS.items() if k not in BASE_POINTS
        }
        recurrence = composite.get_facet("recurrence_pattern") or ""
        distribution = composite.get_facet("distribution_context") or ""

        recurrence_strength = min(1.0, len(base_crystals) / 10.0)
        distribution_score  = cls._distribution_breadth_score(distribution)

        point_scores = {
            "issue__recurrence_pattern"          : recurrence_strength,
            "target__recurrence_pattern"         : recurrence_strength * 0.9,
            "logic_tier__recurrence_pattern"     : recurrence_strength * 0.85,
            "intervention__recurrence_pattern"   : recurrence_strength * 0.8,
            "target__distribution_context"       : distribution_score,
            "issue__distribution_context"        : distribution_score,
            "logic_tier__distribution_context"   : distribution_score,
            "observed_effect__distribution_context" : distribution_score * 0.9,
        }
        for pname, plaw in new_points.items():
            score = point_scores.get(pname, 0.5)
            composite.add_point(RelationalPoint(
                law=plaw,
                score=score,
                evidence=(
                    f"recurrence={recurrence!r}  "
                    f"distribution={distribution!r}"
                ),
            ))

    @classmethod
    def _distribution_breadth_score(cls, distribution: str) -> float:
        if "single_module" in distribution:
            return 0.2
        if "same_tier" in distribution:
            return 0.5
        if "cross_tier" in distribution:
            return 0.75
        if "pipeline_wide" in distribution:
            return 1.0
        return 0.5

    # ── Composite → Higher-Order ──────────────────────────────────────────────

    @classmethod
    def evaluate_composite_to_higher(
        cls,
        composite: CrystalInstance,
        base_crystals: List[CrystalInstance],
    ) -> PromotionResult:
        """Evaluate whether a composite crystal qualifies for higher-order."""
        criteria = cls._engine.get_promotion_criteria(
            CrystalOrder.COMPOSITE, CrystalOrder.HIGHER_ORDER
        )
        reasons: List[str] = []

        count = len(base_crystals)
        if count < criteria.min_base_event_count:
            reasons.append(f"Base event count {count} < {criteria.min_base_event_count}")

        avg_fidelity = statistics.mean(
            [c.resolution_fidelity for c in base_crystals]
        ) if base_crystals else 0.0
        if avg_fidelity < criteria.min_resolution_fidelity_avg:
            reasons.append(
                f"Resolution fidelity avg {avg_fidelity:.2f} < "
                f"{criteria.min_resolution_fidelity_avg}"
            )

        strategy_conf = cls._compute_strategy_confidence(base_crystals)
        if strategy_conf < criteria.min_strategy_confidence:
            reasons.append(
                f"Strategy confidence {strategy_conf:.2f} < "
                f"{criteria.min_strategy_confidence}"
            )

        failure_density = cls._compute_failure_density(base_crystals)
        if failure_density > criteria.max_failure_mode_density:
            reasons.append(
                f"Failure mode density {failure_density:.2f} > "
                f"{criteria.max_failure_mode_density}"
            )

        approved = len(reasons) == 0
        return PromotionResult(
            approved=approved,
            from_order=CrystalOrder.COMPOSITE,
            to_order=CrystalOrder.HIGHER_ORDER,
            crystal_id=composite.crystal_id,
            reasons=reasons,
            promoted_at=_utcnow() if approved else None,
        )

    @classmethod
    def promote_to_higher_order(
        cls,
        composite: CrystalInstance,
        base_crystals: List[CrystalInstance],
        evaluation: PromotionResult,
    ) -> Optional[CrystalInstance]:
        """Execute composite → higher-order promotion."""
        if not evaluation.approved:
            return None

        higher = CrystalInstance(order=CrystalOrder.HIGHER_ORDER)
        higher.parent_ids = [composite.crystal_id]
        higher.base_event_ids = list(composite.base_event_ids)
        higher.promoted_at = evaluation.promoted_at

        # Carry forward all composite facets
        for fname in COMPOSITE_FACETS:
            higher.set_facet(fname, composite.get_facet(fname))

        # Derive higher-order facets
        strategy_class    = cls._derive_strategy_class(base_crystals)
        outcome_profile   = cls._derive_outcome_profile(base_crystals, strategy_class)
        failure_modes     = cls._derive_failure_modes(base_crystals)
        applicability     = cls._derive_applicability_conditions(base_crystals, composite)

        higher.set_facet("strategy_class",           strategy_class)
        higher.set_facet("strategy_outcome_profile", outcome_profile)
        higher.set_facet("failure_modes",            failure_modes)
        higher.set_facet("applicability_conditions", applicability)

        fidelities = [c.resolution_fidelity for c in base_crystals]
        higher.resolution_fidelity = statistics.mean(fidelities) if fidelities else 0.0

        cls._build_higher_order_points(higher, composite, base_crystals)

        higher.tags = list(composite.tags)
        higher.tags.append("higher_order")
        return higher

    @classmethod
    def _derive_strategy_class(cls, base_crystals: List[CrystalInstance]) -> str:
        """Derive dominant strategy class from intervention patterns."""
        from .crystal_engine import HIGHER_ORDER_FACETS
        interventions = [
            c.get_facet("intervention") for c in base_crystals
            if c.get_facet("intervention")
        ]
        if not interventions:
            return "unknown_strategy"

        # Map intervention keywords to strategy classes
        strategy_map = {
            "context_thread"   : "context_thread_stabilization",
            "grounding"        : "clarification_grounding_loop",
            "clarify"          : "clarification_grounding_loop",
            "lookup_bridge"    : "lookup_bridge_activation",
            "lookup"           : "lookup_bridge_activation",
            "uncertainty"      : "uncertainty_signal_repair",
            "evidence_align"   : "evidence_alignment_repair",
            "response_pressure": "response_pressure_rebalancing",
            "repair"           : "repair_path_stabilization",
            "followup"         : "context_thread_stabilization",
            "rename"           : "schema_alignment",
            "label"            : "label_registry_repair",
            "bridge"           : "bridge_implementation",
            "persist"          : "persistence_protocol_upgrade",
            "module"           : "module_provision",
            "constrain"        : "constraint_relaxation",
            "lineage"          : "lineage_integrity_enforcement",
            "patch"            : "schema_alignment",
            "add"              : "label_registry_repair",
            "implement"        : "bridge_implementation",
            "rewrite"          : "persistence_protocol_upgrade",
        }

        tally: Dict[str, int] = {}
        for inv in interventions:
            inv_lower = str(inv).lower()
            matched = False
            for keyword, sc in strategy_map.items():
                if keyword in inv_lower:
                    tally[sc] = tally.get(sc, 0) + 1
                    matched = True
                    break
            if not matched:
                tally["schema_alignment"] = tally.get("schema_alignment", 0) + 1

        return max(tally, key=lambda k: tally[k])

    @classmethod
    def _derive_outcome_profile(
        cls,
        base_crystals: List[CrystalInstance],
        strategy_class: str,
    ) -> str:
        """Derive outcome profile summary string."""
        fidelities = [c.resolution_fidelity for c in base_crystals]
        if not fidelities:
            return "resolution_rate=0.00 regression_rate=0.00 median_ttv=unknown"

        resolution_rate = statistics.mean(fidelities)
        regression_rate = sum(1 for f in fidelities if f == 0.0) / len(fidelities)
        partial_rate    = sum(
            1 for c in base_crystals
            if "partially" in str(c.get_facet("observed_effect") or "").lower()
        ) / len(base_crystals)

        return (
            f"resolution_rate={resolution_rate:.2f} "
            f"partial_rate={partial_rate:.2f} "
            f"regression_rate={regression_rate:.2f} "
            f"strategy={strategy_class}"
        )

    @classmethod
    def _derive_failure_modes(cls, base_crystals: List[CrystalInstance]) -> str:
        """Derive failure modes from regression and no-change events."""
        failure_cases = [
            c for c in base_crystals
            if str(c.get_facet("observed_effect") or "").lower() in (
                "regression_introduced", "no_change_observed"
            )
        ]
        if not failure_cases:
            return "none_recorded"

        modes = set()
        for c in failure_cases:
            tier = c.get_facet("logic_tier") or "unknown_tier"
            issue = c.get_facet("issue") or "unknown_issue"
            modes.add(f"precondition_not_met__{tier}__{issue}")

        return "  |  ".join(sorted(modes))

    @classmethod
    def _derive_applicability_conditions(
        cls,
        base_crystals: List[CrystalInstance],
        composite: CrystalInstance,
    ) -> str:
        """Derive applicability conditions from successful event profiles."""
        successful = [
            c for c in base_crystals
            if c.resolution_fidelity >= 0.7
        ]
        if not successful:
            return "insufficient_successful_events"

        tiers   = {c.get_facet("logic_tier") for c in successful if c.get_facet("logic_tier")}
        dist    = composite.get_facet("distribution_context") or "unknown"
        recur   = composite.get_facet("recurrence_pattern") or "unknown"

        tier_clause = f"logic_tier IN [{', '.join(sorted(tiers))}]"
        dist_clause = f"distribution_context = {dist}"
        recur_note  = (
            "recurrence NOT cascading"
            if "cascading" not in recur
            else "recurrence = cascading"
        )
        return f"{tier_clause}  AND  {dist_clause}  AND  {recur_note}"

    @classmethod
    def _compute_strategy_confidence(cls, base_crystals: List[CrystalInstance]) -> float:
        """Confidence that a dominant strategy class exists."""
        if not base_crystals:
            return 0.0
        successful = [c for c in base_crystals if c.resolution_fidelity >= 0.6]
        return len(successful) / len(base_crystals)

    @classmethod
    def _compute_failure_density(cls, base_crystals: List[CrystalInstance]) -> float:
        """Ratio of failed events to total events."""
        if not base_crystals:
            return 0.0
        failed = sum(
            1 for c in base_crystals if c.resolution_fidelity == 0.0
        )
        return failed / len(base_crystals)

    @classmethod
    def _build_higher_order_points(
        cls,
        higher: CrystalInstance,
        composite: CrystalInstance,
        base_crystals: List[CrystalInstance],
    ) -> None:
        """Carry forward composite points and build new higher-order points."""
        from .crystal_engine import COMPOSITE_POINTS, HIGHER_ORDER_POINTS

        # Carry forward composite points
        for pname, plaw in COMPOSITE_POINTS.items():
            if pname in composite.relational_points:
                src = composite.relational_points[pname]
                higher.add_point(RelationalPoint(
                    law=plaw,
                    score=src.score,
                    evidence=src.evidence,
                    contradiction=src.contradiction,
                ))

        new_points = {
            k: v for k, v in HIGHER_ORDER_POINTS.items()
            if k not in COMPOSITE_POINTS
        }

        strategy_conf   = cls._compute_strategy_confidence(base_crystals)
        failure_density = cls._compute_failure_density(base_crystals)
        avg_fidelity    = statistics.mean(
            [c.resolution_fidelity for c in base_crystals]
        ) if base_crystals else 0.0

        default_scores = {
            "issue__strategy_class"               : strategy_conf,
            "logic_tier__strategy_class"          : strategy_conf * 0.9,
            "intervention__strategy_class"        : strategy_conf * 0.85,
            "strategy_class__outcome_profile"     : avg_fidelity,
            "outcome_profile__observed_effect"    : avg_fidelity * 0.95,
            "strategy_class__failure_modes"       : failure_density,
            "failure_modes__issue"                : failure_density * 0.8,
            "strategy_class__applicability_conditions" : strategy_conf * 0.9,
            "target__applicability_conditions"    : strategy_conf * 0.85,
            "logic_tier__applicability_conditions": strategy_conf * 0.8,
        }

        for pname, plaw in new_points.items():
            higher.add_point(RelationalPoint(
                law=plaw,
                score=default_scores.get(pname, 0.5),
                evidence=(
                    f"strategy_conf={strategy_conf:.2f} "
                    f"avg_fidelity={avg_fidelity:.2f} "
                    f"failure_density={failure_density:.2f}"
                ),
            ))

    # ── Higher-Order → Quasicrystal ───────────────────────────────────────────

    @classmethod
    def evaluate_higher_to_quasi(
        cls,
        higher: CrystalInstance,
        base_crystals: List[CrystalInstance],
    ) -> PromotionResult:
        """Evaluate whether a higher-order crystal qualifies for quasi collapse."""
        criteria = cls._engine.get_promotion_criteria(
            CrystalOrder.HIGHER_ORDER, CrystalOrder.QUASI
        )
        reasons: List[str] = []

        count = len(base_crystals)
        if count < criteria.min_base_event_count:
            reasons.append(f"Base event count {count} < {criteria.min_base_event_count}")

        avg_fidelity = statistics.mean(
            [c.resolution_fidelity for c in base_crystals]
        ) if base_crystals else 0.0
        if avg_fidelity < criteria.min_resolution_fidelity_avg:
            reasons.append(
                f"Resolution fidelity {avg_fidelity:.2f} < "
                f"{criteria.min_resolution_fidelity_avg}"
            )

        outcome_str = higher.get_facet("strategy_outcome_profile") or ""
        outcome_score = cls._parse_resolution_rate(outcome_str)
        if outcome_score < criteria.min_outcome_profile_score:
            reasons.append(
                f"Outcome profile resolution_rate {outcome_score:.2f} < "
                f"{criteria.min_outcome_profile_score}"
            )

        failure_density = cls._compute_failure_density(base_crystals)
        if failure_density > criteria.max_failure_mode_density:
            reasons.append(
                f"Failure mode density {failure_density:.2f} > "
                f"{criteria.max_failure_mode_density}"
            )

        if criteria.require_stable_strategy:
            strategy = higher.get_facet("strategy_class") or ""
            if not strategy or strategy == "unknown_strategy":
                reasons.append("No stable strategy class — rotation required before quasi.")

        approved = len(reasons) == 0
        return PromotionResult(
            approved=approved,
            from_order=CrystalOrder.HIGHER_ORDER,
            to_order=CrystalOrder.QUASI,
            crystal_id=higher.crystal_id,
            reasons=reasons,
            promoted_at=_utcnow() if approved else None,
        )

    @classmethod
    def collapse_to_quasi(
        cls,
        higher: CrystalInstance,
        base_crystals: List[CrystalInstance],
        evaluation: PromotionResult,
    ) -> Optional[CrystalInstance]:
        """Execute higher-order → quasicrystal collapse."""
        if not evaluation.approved:
            return None

        quasi = CrystalInstance(order=CrystalOrder.QUASI)
        quasi.parent_ids = [higher.crystal_id]
        quasi.base_event_ids = list(higher.base_event_ids)
        quasi.promoted_at = evaluation.promoted_at

        # Build inner strata
        strata = cls._build_inner_strata(higher, base_crystals)
        quasi.quasi_strata = strata

        # Derive outer shell facets
        strategy     = higher.get_facet("strategy_class") or "unknown"
        strategies   = cls._rank_strategies(base_crystals)
        primary_s    = strategies[0] if strategies else strategy
        secondary_s  = strategies[1] if len(strategies) > 1 else None

        issue_fam    = higher.get_facet("issue") or "unknown_issue"
        archetype    = cls._classify_issue_archetype(issue_fam)

        avg_fidelity = statistics.mean(
            [c.resolution_fidelity for c in base_crystals]
        ) if base_crystals else 0.0
        confidence = cls._compute_quasi_confidence(
            avg_fidelity,
            len(base_crystals),
            strata.failure_counterexamples,
            strata.coherence_index,
        )

        quasi.set_facet("issue_archetype",        archetype)
        quasi.set_facet("primary_strategy",       primary_s)
        quasi.set_facet("secondary_strategy",     secondary_s or "none")
        quasi.set_facet("applicability_boundary", higher.get_facet("applicability_conditions") or "")
        quasi.set_facet("confidence",             round(confidence, 4))
        quasi.set_facet("failure_indicators",     higher.get_facet("failure_modes") or "none")
        quasi.set_facet("expected_effects",       cls._derive_expected_effects(base_crystals))
        quasi.set_facet("escalation_trigger",     cls._derive_escalation_trigger(
            confidence, strata.failure_counterexamples, higher
        ))

        quasi.resolution_fidelity = avg_fidelity
        quasi.tags = [
            "quasicrystal",
            archetype,
            primary_s,
            f"coherence:{round(float(strata.coherence_index), 3)}",
            f"novelty:{round(float(strata.novelty_index), 3)}",
        ]
        return quasi

    @classmethod
    def _build_inner_strata(
        cls,
        higher: CrystalInstance,
        base_crystals: List[CrystalInstance],
    ) -> QuasiInnerStrata:
        """Build the collapsed inner genealogy layers."""
        rep_events = []
        for c in base_crystals[:5]:  # top-N representative base events
            rep_events.append({
                "crystal_id"         : c.crystal_id,
                "issue"              : c.get_facet("issue"),
                "target"             : c.get_facet("target"),
                "logic_tier"         : c.get_facet("logic_tier"),
                "intervention"       : c.get_facet("intervention"),
                "resolution_fidelity": c.resolution_fidelity,
            })

        failure_counterexamples = [
            {
                "crystal_id"  : c.crystal_id,
                "intervention": c.get_facet("intervention"),
                "observed"    : c.get_facet("observed_effect"),
                "tier"        : c.get_facet("logic_tier"),
            }
            for c in base_crystals if c.resolution_fidelity == 0.0
        ]

        strategy_success_stats: Dict[str, float] = {}
        sc = higher.get_facet("strategy_class") or "unknown"
        fidelities = [c.resolution_fidelity for c in base_crystals]
        if fidelities:
            strategy_success_stats[sc] = statistics.mean(fidelities)

        recurrence_summary = {
            "pattern"     : higher.get_facet("recurrence_pattern"),
            "distribution": higher.get_facet("distribution_context"),
            "event_count" : len(base_crystals),
        }

        coherence_index = cls._compute_coherence_index(base_crystals)
        novelty_index = cls._compute_novelty_index(base_crystals)

        return QuasiInnerStrata(
            representative_base_events=rep_events,
            recurrence_summary=recurrence_summary,
            strategy_success_stats=strategy_success_stats,
            failure_counterexamples=failure_counterexamples,
            coherence_index=coherence_index,
            novelty_index=novelty_index,
            genealogy_depth=len(base_crystals),
            formation_timestamp=_utcnow(),
        )

    @classmethod
    def _classify_issue_archetype(cls, issue: str) -> str:
        issue_lower = str(issue).lower()
        if "attribute" in issue_lower or "mismatch" in issue_lower:
            return "attribute_contract_violation"
        if "label" in issue_lower or "registry" in issue_lower:
            return "label_registry_gap"
        if "shard" in issue_lower or "ingestion" in issue_lower or "dropout" in issue_lower:
            return "pipeline_shard_dropout"
        if "persist" in issue_lower or "stats" in issue_lower:
            return "persistence_boundary_failure"
        if "boot" in issue_lower or "missing" in issue_lower or "module" in issue_lower:
            return "module_provision_gap"
        if (
            "pressure" in issue_lower
            or "constraint" in issue_lower
            or "outlet" in issue_lower
            or "fraction" in issue_lower
            or "zero" in issue_lower
        ):
            return "constraint_physics_violation"
        if "context" in issue_lower or "followup" in issue_lower or "carryover" in issue_lower:
            return "context_thread_break"
        if "ground" in issue_lower or "lookup" in issue_lower or "meaning" in issue_lower:
            return "grounding_repair_gap"
        if "uncertainty" in issue_lower:
            return "uncertainty_signal_gap"
        if "repair" in issue_lower or "contradiction" in issue_lower:
            return "repair_path_breakdown"
        return "general_diagnostic_anomaly"

    @classmethod
    def _rank_strategies(cls, base_crystals: List[CrystalInstance]) -> List[str]:
        """Rank strategy classes by frequency × fidelity."""
        strategy_map = {
            "context_thread"   : "context_thread_stabilization",
            "grounding"        : "clarification_grounding_loop",
            "clarify"          : "clarification_grounding_loop",
            "lookup_bridge"    : "lookup_bridge_activation",
            "lookup"           : "lookup_bridge_activation",
            "uncertainty"      : "uncertainty_signal_repair",
            "evidence_align"   : "evidence_alignment_repair",
            "response_pressure": "response_pressure_rebalancing",
            "repair"           : "repair_path_stabilization",
            "followup"         : "context_thread_stabilization",
            "rename"           : "schema_alignment",
            "label"            : "label_registry_repair",
            "bridge"           : "bridge_implementation",
            "persist"          : "persistence_protocol_upgrade",
            "module"           : "module_provision",
            "patch"            : "schema_alignment",
            "add"              : "label_registry_repair",
            "implement"        : "bridge_implementation",
            "rewrite"          : "persistence_protocol_upgrade",
        }
        tally: Dict[str, float] = {}
        for c in base_crystals:
            inv = str(c.get_facet("intervention") or "").lower()
            sc  = "schema_alignment"
            for kw, mapped in strategy_map.items():
                if kw in inv:
                    sc = mapped
                    break
            tally[sc] = tally.get(sc, 0.0) + c.resolution_fidelity

        return sorted(tally, key=lambda k: tally[k], reverse=True)

    @classmethod
    def _compute_quasi_confidence(
        cls,
        avg_fidelity: float,
        event_count: int,
        failure_counterexamples: List[Dict[str, Any]],
        coherence_index: float = 0.0,
    ) -> float:
        depth_bonus    = min(0.2, event_count / 50.0)
        failure_penalty = min(0.3, len(failure_counterexamples) / event_count) if event_count else 0.3
        coherence_bonus = max(0.0, min(0.12, float(coherence_index) * 0.12))
        return max(0.0, min(1.0, avg_fidelity + depth_bonus + coherence_bonus - failure_penalty))

    @classmethod
    def _compute_coherence_index(
        cls,
        base_crystals: List[CrystalInstance],
    ) -> float:
        if not base_crystals:
            return 0.0

        def _dominant_ratio(values: List[str]) -> float:
            tally: Dict[str, int] = {}
            for value in values:
                if not value:
                    continue
                tally[value] = tally.get(value, 0) + 1
            if not tally:
                return 0.0
            return max(tally.values()) / float(max(1, len(values)))

        tiers = [str(c.get_facet("logic_tier") or "") for c in base_crystals]
        interventions = [str(c.get_facet("intervention") or "") for c in base_crystals]
        avg_fidelity = statistics.mean([c.resolution_fidelity for c in base_crystals])
        coherence = (
            0.35 * _dominant_ratio(tiers)
            + 0.35 * _dominant_ratio(interventions)
            + 0.30 * avg_fidelity
        )
        return round(max(0.0, min(1.0, coherence)), 4)

    @classmethod
    def _compute_novelty_index(
        cls,
        base_crystals: List[CrystalInstance],
    ) -> float:
        if not base_crystals:
            return 0.0
        total = float(len(base_crystals))
        interventions = {
            str(c.get_facet("intervention") or "")
            for c in base_crystals
            if c.get_facet("intervention")
        }
        targets = {
            str(c.get_facet("target") or "")
            for c in base_crystals
            if c.get_facet("target")
        }
        effects = {
            str(c.get_facet("observed_effect") or "")
            for c in base_crystals
            if c.get_facet("observed_effect")
        }
        novelty = (
            0.40 * min(1.0, len(interventions) / total)
            + 0.30 * min(1.0, len(targets) / total)
            + 0.30 * min(1.0, len(effects) / total)
        )
        return round(max(0.0, min(1.0, novelty)), 4)

    @classmethod
    def _derive_expected_effects(cls, base_crystals: List[CrystalInstance]) -> str:
        successful = [
            c for c in base_crystals if c.resolution_fidelity >= 0.7
        ]
        if not successful:
            return "insufficient_successful_events_for_prediction"
        effects = [
            c.get_facet("intended_effect") for c in successful
            if c.get_facet("intended_effect")
        ]
        return "  |  ".join(sorted(set(str(e) for e in effects)))[:500]

    @classmethod
    def _derive_escalation_trigger(
        cls,
        confidence: float,
        failure_counterexamples: List[Dict[str, Any]],
        higher: CrystalInstance,
    ) -> str:
        triggers = []
        if confidence < 0.5:
            triggers.append("confidence_below_threshold")
        if len(failure_counterexamples) >= 3:
            triggers.append("failure_indicator_fired_3x_or_more")
        dist = higher.get_facet("distribution_context") or ""
        if "cross_tier" in dist or "pipeline_wide" in dist:
            triggers.append("cross_tier_distribution_detected")
        if not triggers:
            triggers.append("both_strategies_failed_in_same_event")
        return "  OR  ".join(triggers)

    @classmethod
    def _parse_resolution_rate(cls, outcome_str: str) -> float:
        for token in outcome_str.split():
            if token.startswith("resolution_rate="):
                try:
                    return float(token.split("=")[1])
                except (ValueError, IndexError):
                    pass
        return 0.0

    @staticmethod
    def _dominant_value(values: List[Any]) -> Any:
        """Return the most common value in a list, or the first if all unique."""
        if not values:
            return None
        tally: Dict[str, int] = {}
        original_by_key: Dict[str, Any] = {}
        for v in values:
            key = str(v)
            tally[key] = tally.get(key, 0) + 1
            original_by_key.setdefault(key, v)
        dominant_key = max(tally, key=lambda k: tally[k])
        return original_by_key[dominant_key]


# ══════════════════════════════════════════════════════════════════════════════
# ROTATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class CrystalRotation:
    """
    Executes rotation analysis on a quasicrystal.

    Rotation re-weights facet–point relationships to generate new hypotheses
    without rebuilding from scratch.  Each rotation perspective has a named
    pivot role and a set of reweight targets.
    """

    _engine = CrystalEngine()

    @classmethod
    def rotate(
        cls,
        quasi: CrystalInstance,
        rotation_name: str,
        base_crystals: List[CrystalInstance],
    ) -> RotationResult:
        """
        Apply a named rotation to a quasicrystal.

        Parameters
        ----------
        quasi         : The quasicrystal to rotate.
        rotation_name : One of the names in ALL_ROTATIONS.
        base_crystals : The base events in the genealogy.

        Returns
        -------
        RotationResult with generated hypotheses and pivot point scores.
        """
        rot_def = cls._engine.get_rotation(rotation_name)
        if rot_def is None:
            return RotationResult(
                rotation_name=rotation_name,
                crystal_id=quasi.crystal_id,
                hypotheses=[{"error": f"Unknown rotation: {rotation_name}"}],
                pivot_point_scores={},
            )

        # Collect pivot points (all points with the pivot role)
        pivot_points = {
            pname: rp
            for pname, rp in quasi.relational_points.items()
            if rot_def.pivot_role in rp.law.roles
        }

        # Re-weight reweight_targets relative to pivot
        pivot_avg = statistics.mean(
            [rp.score for rp in pivot_points.values()]
        ) if pivot_points else 0.5

        hypotheses = cls._generate_hypotheses(
            rot_def, quasi, base_crystals, pivot_avg
        )

        result = RotationResult(
            rotation_name=rotation_name,
            crystal_id=quasi.crystal_id,
            hypotheses=hypotheses,
            pivot_point_scores={k: v.score for k, v in pivot_points.items()},
        )

        # Record in rotation history
        quasi.rotation_history.append({
            "rotation"  : rotation_name,
            "executed_at": result.executed_at,
            "hypothesis_count": len(hypotheses),
            "pivot_avg" : pivot_avg,
        })

        return result

    @classmethod
    def _generate_hypotheses(
        cls,
        rot_def: RotationDefinition,
        quasi: CrystalInstance,
        base_crystals: List[CrystalInstance],
        pivot_avg: float,
    ) -> List[Dict[str, Any]]:
        """Generate hypotheses appropriate for the rotation type."""
        hyp_type = rot_def.hypothesis_type
        hypotheses: List[Dict[str, Any]] = []

        if hyp_type == "intervention_optimality_for_issue":
            # Group base events by intervention, rank by fidelity
            groups: Dict[str, List[float]] = {}
            for c in base_crystals:
                inv = str(c.get_facet("intervention") or "unknown")
                groups.setdefault(inv, []).append(c.resolution_fidelity)
            for inv, fids in sorted(
                groups.items(), key=lambda x: -statistics.mean(x[1])
            ):
                hypotheses.append({
                    "hypothesis_type" : hyp_type,
                    "intervention"    : inv,
                    "avg_fidelity"    : round(statistics.mean(fids), 3),
                    "sample_count"    : len(fids),
                    "recommendation"  : (
                        "Preferred intervention for this issue family"
                        if statistics.mean(fids) >= 0.7
                        else "Sub-optimal — consider alternative"
                    ),
                })

        elif hyp_type == "tier_strategy_compatibility":
            # Group by logic_tier × strategy compatibility
            tier_fidelity: Dict[str, List[float]] = {}
            for c in base_crystals:
                tier = str(c.get_facet("logic_tier") or "unknown")
                tier_fidelity.setdefault(tier, []).append(c.resolution_fidelity)
            primary_strategy = quasi.get_facet("primary_strategy") or "unknown"
            for tier, fids in tier_fidelity.items():
                avg = statistics.mean(fids)
                hypotheses.append({
                    "hypothesis_type"    : hyp_type,
                    "logic_tier"         : tier,
                    "strategy"           : primary_strategy,
                    "compatibility_score": round(avg, 3),
                    "recommendation"     : (
                        f"Strategy '{primary_strategy}' is compatible with tier '{tier}'"
                        if avg >= 0.6
                        else f"Strategy '{primary_strategy}' shows poor compatibility with tier '{tier}'"
                    ),
                })

        elif hyp_type == "strategy_equivalence_or_differentiation":
            strata = quasi.quasi_strata
            if strata:
                for sc, rate in strata.strategy_success_stats.items():
                    hypotheses.append({
                        "hypothesis_type" : hyp_type,
                        "strategy_class"  : sc,
                        "success_rate"    : round(rate, 3),
                        "recommendation"  : (
                            "Candidate for primary strategy equivalence"
                            if rate >= 0.7
                            else "Sub-strategy or context-specific variant"
                        ),
                    })

        elif hyp_type == "effect_convergence_via_different_strategies":
            # Find base events with similar observed effects but different interventions
            effect_groups: Dict[str, List[str]] = {}
            for c in base_crystals:
                eff = str(c.get_facet("observed_effect") or "unknown")
                inv = str(c.get_facet("intervention") or "unknown")
                effect_groups.setdefault(eff, []).append(inv)
            for eff, invs in effect_groups.items():
                unique_invs = list(set(invs))
                if len(unique_invs) > 1:
                    hypotheses.append({
                        "hypothesis_type"        : hyp_type,
                        "convergent_effect"      : eff,
                        "producing_interventions": unique_invs,
                        "recommendation"         : (
                            "Multiple intervention routes converge on this effect — "
                            "consider abstracting a new strategy class"
                        ),
                    })

        return hypotheses


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY HYPOTHESIS GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class StrategyHypothesisGenerator:
    """
    Given a new diagnostic event and a collection of quasicrystals,
    generates ranked strategy hypotheses without starting from scratch.
    """

    @staticmethod
    def generate(
        new_event: Dict[str, Any],
        quasicrystals: List[CrystalInstance],
    ) -> List[StrategyHypothesis]:
        """
        Match a new event against available quasicrystals.

        Matching is based on:
          1. Issue archetype alignment
          2. Applicability boundary satisfaction
          3. Confidence threshold

        Returns a ranked list of StrategyHypothesis objects.
        """
        results: List[StrategyHypothesis] = []
        new_issue = str(new_event.get("issue", "")).lower()
        new_tier  = str(new_event.get("logic_tier", "")).lower()
        new_dist  = str(new_event.get("distribution_context", "single_module")).lower()

        for qc in quasicrystals:
            archetype = str(qc.get_facet("issue_archetype") or "")
            boundary  = str(qc.get_facet("applicability_boundary") or "")
            confidence= float(qc.get_facet("confidence") or 0.0)

            # Issue alignment
            if not StrategyHypothesisGenerator._issue_matches_archetype(
                new_issue, archetype
            ):
                continue

            # Applicability check
            app_met = StrategyHypothesisGenerator._check_applicability(
                boundary, new_tier, new_dist
            )

            primary    = str(qc.get_facet("primary_strategy") or "unknown")
            secondary  = str(qc.get_facet("secondary_strategy") or "none")
            fail_ind   = str(qc.get_facet("failure_indicators") or "none")
            esc_trigger= str(qc.get_facet("escalation_trigger") or "none")

            results.append(StrategyHypothesis(
                issue_archetype      = archetype,
                recommended_strategy = primary if app_met else secondary,
                confidence           = confidence,
                applicability_met    = app_met,
                failure_risk         = fail_ind,
                escalation_risk      = esc_trigger,
                source_quasi_id      = qc.crystal_id,
            ))

        # Rank by confidence descending, applicability_met first
        results.sort(key=lambda h: (h.applicability_met, h.confidence), reverse=True)
        return results

    @staticmethod
    def _issue_matches_archetype(issue: str, archetype: str) -> bool:
        keyword_map = {
            "attribute_contract_violation": ["attribute", "mismatch", "rename"],
            "label_registry_gap"          : ["label", "registry", "variant"],
            "pipeline_shard_dropout"      : ["shard", "ingestion", "dropout", "bridge"],
            "persistence_boundary_failure": ["persist", "stats", "save", "restore"],
            "module_provision_gap"        : ["module", "missing", "boot", "import"],
            "constraint_physics_violation": ["constraint", "pressure", "outlet"],
            "context_thread_break"        : ["context", "followup", "carryover", "callback", "thread"],
            "grounding_repair_gap"        : ["ground", "lookup", "meaning", "anchor", "clarify"],
            "uncertainty_signal_gap"      : ["uncertainty", "hedge", "guess"],
            "repair_path_breakdown"       : ["repair", "contradiction", "resolve", "fix"],
            "general_diagnostic_anomaly"  : ["anomaly", "diagnostic", "general", "unknown"],
        }
        keywords = keyword_map.get(archetype, archetype.replace("_", " ").split())
        return any(kw in issue for kw in keywords)

    @staticmethod
    def _check_applicability(
        boundary: str,
        tier: str,
        distribution: str,
    ) -> bool:
        """Naive applicability check against boundary string."""
        if not boundary or boundary == "insufficient_successful_events":
            return False
        # If boundary mentions a tier and the new tier matches, consider met
        if "logic_tier IN" in boundary:
            bracket = boundary.split("logic_tier IN [")[1].split("]")[0]
            valid_tiers = [t.strip() for t in bracket.split(",")]
            if tier and not any(tier in vt for vt in valid_tiers):
                return False
        if "single_module" in boundary and "single_module" not in distribution:
            return False
        return True


# ══════════════════════════════════════════════════════════════════════════════
# LIFECYCLE ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

class CrystalLifecycle:
    """
    Orchestrates the complete crystal lifecycle for a session.

    This is the single entry point for the processing layer.
    The memory layer calls this to get new or promoted crystals,
    then persists the results.

    Attributes
    ----------
    _base_pools     : Dict mapping issue_category → list of base CrystalInstance
    _composites     : Dict mapping composite_id → CrystalInstance
    _higher_orders  : Dict mapping higher_id → CrystalInstance
    _quasicrystals  : Dict mapping quasi_id → CrystalInstance
    """

    def __init__(self) -> None:
        self._base_pools   : Dict[str, List[CrystalInstance]] = {}
        self._composites   : Dict[str, CrystalInstance]       = {}
        self._higher_orders: Dict[str, CrystalInstance]       = {}
        self._quasicrystals: Dict[str, CrystalInstance]       = {}
        self._log          : List[str]                        = []

    # ── Ingest ────────────────────────────────────────────────────────────────

    def ingest_event(
        self,
        event: Dict[str, Any],
        tags: Optional[List[str]] = None,
    ) -> Tuple[Optional[CrystalInstance], List[str]]:
        """
        Form a base crystal from an event and store it in the appropriate pool.
        Returns the new crystal and all formation messages.
        """
        crystal, messages = CrystalFormation.form_base_crystal(event, tags)
        if crystal is None:
            self._log.extend(messages)
            return None, messages

        issue_key = str(event.get("issue", "unknown"))
        self._base_pools.setdefault(issue_key, []).append(crystal)
        self._log.extend(messages)
        return crystal, messages

    # ── Promotion pipeline ────────────────────────────────────────────────────

    def attempt_composite_formation(
        self,
        issue_category: str,
    ) -> Tuple[Optional[CrystalInstance], PromotionResult]:
        """
        Try to promote the base pool for a given issue category to composite.
        """
        pool = self._base_pools.get(issue_category, [])
        evaluation = CrystalPromotion.evaluate_base_to_composite(pool)
        if not evaluation.approved:
            self._log.append(
                f"Composite promotion denied [{issue_category}]: "
                + "  |  ".join(evaluation.reasons)
            )
            return None, evaluation

        composite = CrystalPromotion.promote_to_composite(pool, evaluation)
        if composite:
            self._composites[composite.crystal_id] = composite
            for base in pool:
                base.child_ids.append(composite.crystal_id)
            self._log.append(
                f"Composite formed: {composite.crystal_id}  "
                f"from {len(pool)} base events"
            )
        return composite, evaluation

    def attempt_higher_order_formation(
        self,
        composite_id: str,
    ) -> Tuple[Optional[CrystalInstance], PromotionResult]:
        """Try to promote a composite crystal to higher-order."""
        composite = self._composites.get(composite_id)
        if not composite:
            dummy = PromotionResult(
                approved=False, from_order=CrystalOrder.COMPOSITE,
                to_order=CrystalOrder.HIGHER_ORDER, crystal_id=composite_id,
                reasons=[f"Composite {composite_id} not found."],
            )
            return None, dummy

        base_pool = self._get_base_crystals_for(composite)
        evaluation = CrystalPromotion.evaluate_composite_to_higher(composite, base_pool)
        if not evaluation.approved:
            self._log.append(
                f"Higher-order promotion denied [{composite_id}]: "
                + "  |  ".join(evaluation.reasons)
            )
            return None, evaluation

        higher = CrystalPromotion.promote_to_higher_order(composite, base_pool, evaluation)
        if higher:
            self._higher_orders[higher.crystal_id] = higher
            composite.child_ids.append(higher.crystal_id)
            self._log.append(f"Higher-order formed: {higher.crystal_id}")
        return higher, evaluation

    def attempt_quasi_collapse(
        self,
        higher_id: str,
    ) -> Tuple[Optional[CrystalInstance], PromotionResult]:
        """Try to collapse a higher-order crystal to quasicrystal."""
        higher = self._higher_orders.get(higher_id)
        if not higher:
            dummy = PromotionResult(
                approved=False, from_order=CrystalOrder.HIGHER_ORDER,
                to_order=CrystalOrder.QUASI, crystal_id=higher_id,
                reasons=[f"Higher-order {higher_id} not found."],
            )
            return None, dummy

        base_pool = self._get_base_crystals_for(higher)
        evaluation = CrystalPromotion.evaluate_higher_to_quasi(higher, base_pool)
        if not evaluation.approved:
            self._log.append(
                f"Quasi collapse denied [{higher_id}]: "
                + "  |  ".join(evaluation.reasons)
            )
            return None, evaluation

        quasi = CrystalPromotion.collapse_to_quasi(higher, base_pool, evaluation)
        if quasi:
            self._quasicrystals[quasi.crystal_id] = quasi
            higher.child_ids.append(quasi.crystal_id)
            self._log.append(
                f"Quasicrystal collapsed: {quasi.crystal_id}  "
                f"confidence={quasi.get_facet('confidence')}"
            )
        return quasi, evaluation

    # ── Rotation ──────────────────────────────────────────────────────────────

    def rotate_quasi(
        self,
        quasi_id: str,
        rotation_name: str,
    ) -> Optional[RotationResult]:
        """Apply a rotation to a quasicrystal."""
        quasi = self._quasicrystals.get(quasi_id)
        if not quasi:
            self._log.append(f"Rotation failed: quasicrystal {quasi_id} not found.")
            return None

        base_pool = self._get_base_crystals_for(quasi)
        result = CrystalRotation.rotate(quasi, rotation_name, base_pool)
        self._log.append(
            f"Rotation '{rotation_name}' on {quasi_id}: "
            f"{len(result.hypotheses)} hypotheses generated"
        )
        return result

    # ── Strategy recommendation ───────────────────────────────────────────────

    def recommend_strategy(
        self,
        new_event: Dict[str, Any],
    ) -> List[StrategyHypothesis]:
        """Match a new event against all quasicrystals and return ranked hypotheses."""
        return StrategyHypothesisGenerator.generate(
            new_event, list(self._quasicrystals.values())
        )

    def build_doctrine(self, quasi_id: str) -> Optional[DoctrineObject]:
        """Collapse a quasicrystal into an actionable doctrine view."""
        quasi = self._quasicrystals.get(quasi_id)
        if not quasi:
            return None
        return self._build_doctrine_from_quasi(quasi)

    def get_all_doctrines(self) -> List[DoctrineObject]:
        """Return all actionable doctrines currently available."""
        doctrines: List[DoctrineObject] = []
        for quasi in self._quasicrystals.values():
            doctrines.append(self._build_doctrine_from_quasi(quasi))
        doctrines.sort(key=lambda doc: doc.confidence, reverse=True)
        return doctrines

    # ── Accessors ─────────────────────────────────────────────────────────────

    def get_all_base_crystals(self) -> List[CrystalInstance]:
        return [c for pool in self._base_pools.values() for c in pool]

    def get_composite(self, cid: str) -> Optional[CrystalInstance]:
        return self._composites.get(cid)

    def get_higher_order(self, hid: str) -> Optional[CrystalInstance]:
        return self._higher_orders.get(hid)

    def get_quasi(self, qid: str) -> Optional[CrystalInstance]:
        return self._quasicrystals.get(qid)

    def get_log(self) -> List[str]:
        return list(self._log)

    def _get_base_crystals_for(self, crystal: CrystalInstance) -> List[CrystalInstance]:
        """Retrieve base crystals contributing to a given higher-order crystal."""
        all_base = {c.crystal_id: c for c in self.get_all_base_crystals()}
        return [all_base[bid] for bid in crystal.base_event_ids if bid in all_base]

    def _build_doctrine_from_quasi(self, quasi: CrystalInstance) -> DoctrineObject:
        strata = quasi.quasi_strata or QuasiInnerStrata()
        lineage_meta = dict(quasi.lineage_meta)
        failure_indicators = _split_collapsed_entries(
            str(quasi.get_facet("failure_indicators") or "")
        )
        expected_effects = _split_collapsed_entries(
            str(quasi.get_facet("expected_effects") or "")
        )
        return DoctrineObject(
            quasi_id=quasi.crystal_id,
            family_key=str(lineage_meta.get("family_key", "")),
            lineage_version=int(lineage_meta.get("version", 0) or 0),
            is_active_version=bool(lineage_meta.get("is_active_version", False)),
            supersedes=str(lineage_meta.get("supersedes", "")),
            superseded_by=str(lineage_meta.get("superseded_by", "")),
            issue_archetype=str(quasi.get_facet("issue_archetype") or "unknown"),
            primary_strategy=str(quasi.get_facet("primary_strategy") or "unknown"),
            secondary_strategy=str(quasi.get_facet("secondary_strategy") or "none"),
            applicability_boundary=str(quasi.get_facet("applicability_boundary") or ""),
            confidence=float(quasi.get_facet("confidence") or 0.0),
            failure_indicators=failure_indicators,
            expected_effects=expected_effects,
            escalation_trigger=str(quasi.get_facet("escalation_trigger") or ""),
            representative_base_events=list(strata.representative_base_events),
            recurrence_summary=dict(strata.recurrence_summary),
            strategy_success_stats=dict(strata.strategy_success_stats),
            failure_counterexamples=list(strata.failure_counterexamples),
            genealogy_depth=int(strata.genealogy_depth or 0),
            coherence_index=float(strata.coherence_index or 0.0),
            novelty_index=float(strata.novelty_index or 0.0),
            available_rotations=sorted(ALL_ROTATIONS.keys()),
            rotation_history=list(quasi.rotation_history),
        )


def _split_collapsed_entries(raw_value: str) -> List[str]:
    """Normalize a collapsed facet string into a list of actionable entries."""
    if not raw_value:
        return []
    separators = ("  |  ", " OR ", "|", ";")
    values = [raw_value]
    for sep in separators:
        if sep in raw_value:
            values = [part.strip() for part in raw_value.split(sep)]
            break
    return [value for value in values if value and value.lower() != "none"]


# ══════════════════════════════════════════════════════════════════════════════
# MAIN — demonstration run
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Dimensional Processing System — Lifecycle Demo")
    print("=" * 60)

    lifecycle = CrystalLifecycle()

    # ── Simulate 10 base events for label-registry-gap issue family ───────────
    events = [
        {
            "target"         : f"aurora_runtime.ability_registry.slot_{i}",
            "issue"          : "outlet_push_fraction_permanently_zero",
            "logic_tier"     : "constraint_physics",
            "intervention"   : "add_label_to_variant_map",
            "intended_effect": "ensure_label_resolves_to_ability_variant",
            "observed_effect": effect,
        }
        for i, effect in enumerate([
            "resolved_fully",
            "resolved_fully",
            "resolved_fully",
            "resolved_partially",
            "resolved_fully",
            "resolved_fully",
            "resolved_fully",
            "no_change_observed",
            "resolved_fully",
            "resolved_fully",
        ])
    ]

    for ev in events:
        crystal, msgs = lifecycle.ingest_event(ev, tags=["demo", "label_registry"])
        if crystal:
            print(f"  Formed base: {crystal.crystal_id[:8]}…  "
                  f"fidelity={crystal.resolution_fidelity:.2f}")

    print()

    # ── Attempt composite formation ───────────────────────────────────────────
    issue_key = "outlet_push_fraction_permanently_zero"
    comp, eval_result = lifecycle.attempt_composite_formation(issue_key)
    print(f"Composite promotion: {'APPROVED' if eval_result.approved else 'DENIED'}")
    for r in eval_result.reasons:
        print(f"  Reason: {r}")
    if comp:
        print(f"  Composite ID : {comp.crystal_id[:8]}…")
        print(f"  Recurrence   : {comp.get_facet('recurrence_pattern')}")
        print(f"  Distribution : {comp.get_facet('distribution_context')}")

    print()

    # ── Attempt higher-order formation ────────────────────────────────────────
    if comp:
        higher, eval_h = lifecycle.attempt_higher_order_formation(comp.crystal_id)
        print(f"Higher-order promotion: {'APPROVED' if eval_h.approved else 'DENIED'}")
        for r in eval_h.reasons:
            print(f"  Reason: {r}")
        if higher:
            print(f"  Higher-order ID  : {higher.crystal_id[:8]}…")
            print(f"  Strategy class   : {higher.get_facet('strategy_class')}")
            print(f"  Outcome profile  : {higher.get_facet('strategy_outcome_profile')}")
            print(f"  Failure modes    : {higher.get_facet('failure_modes')}")
            print(f"  Applicability    : {higher.get_facet('applicability_conditions')}")

        print()

        # ── Attempt quasi collapse ────────────────────────────────────────────
        if higher:
            quasi, eval_q = lifecycle.attempt_quasi_collapse(higher.crystal_id)
            print(f"Quasi collapse: {'APPROVED' if eval_q.approved else 'DENIED'}")
            for r in eval_q.reasons:
                print(f"  Reason: {r}")
            if quasi:
                print(f"  Quasi ID           : {quasi.crystal_id[:8]}…")
                print(f"  Issue archetype    : {quasi.get_facet('issue_archetype')}")
                print(f"  Primary strategy   : {quasi.get_facet('primary_strategy')}")
                print(f"  Confidence         : {quasi.get_facet('confidence')}")
                print(f"  Failure indicators : {quasi.get_facet('failure_indicators')}")
                print(f"  Escalation trigger : {quasi.get_facet('escalation_trigger')}")
                print(f"  Genealogy depth    : {quasi.quasi_strata.genealogy_depth}")

            print()

            # ── Rotation ──────────────────────────────────────────────────────
            if quasi:
                for rname in ["issue_centric", "logic_tier", "strategy", "outcome"]:
                    rot = lifecycle.rotate_quasi(quasi.crystal_id, rname)
                    if rot:
                        print(f"Rotation [{rname}]: {len(rot.hypotheses)} hypotheses")
                        for h in rot.hypotheses[:2]:
                            print(f"  {h}")

                print()

                # ── Strategy recommendation for new event ─────────────────────
                new_event = {
                    "issue"              : "outlet_pressure_path_stuck_zero",
                    "logic_tier"         : "constraint_physics",
                    "distribution_context": "multi_module__same_tier",
                }
                hypotheses = lifecycle.recommend_strategy(new_event)
                print(f"Strategy recommendation for new event:")
                for h in hypotheses:
                    print(f"  Archetype         : {h.issue_archetype}")
                    print(f"  Recommended strat : {h.recommended_strategy}")
                    print(f"  Confidence        : {h.confidence:.3f}")
                    print(f"  Applicability met : {h.applicability_met}")
                doctrine = lifecycle.build_doctrine(quasi.crystal_id)
                if doctrine:
                    print(f"\nDoctrine object:")
                    print(f"  Primary strategy  : {doctrine.primary_strategy}")
                    print(f"  Failure indicators: {doctrine.failure_indicators}")
                    print(f"  Rotations         : {doctrine.available_rotations}")

    print("\n" + "=" * 60)
    print("Lifecycle log:")
    for entry in lifecycle.get_log():
        print(f"  {entry}")
