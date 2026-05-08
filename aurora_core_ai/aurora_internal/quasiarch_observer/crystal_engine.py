"""
crystal_engine_v3_cleaned.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Authors : Sunni (Sir) Morningstar and Cael Devo
Purpose : Semantic crystal law — the doctrine brain.
          Defines what every facet and relational point *means* at every
          crystal order.  Does NOT manage lifecycle or storage — those live in
          dimensional_processing and dimensional_memory respectively.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Crystal Order Ladder
  Level 1  →  Base Crystal         (6 facets,  12 relational points)
  Level 2  →  Composite Crystal    (8 facets,  20 relational points)
  Level 3  →  Higher-Order Crystal (12 facets, 30 relational points)
  Level 4  →  Quasicrystal         (8 outer operational facets + collapsed inner genealogy)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple


# ══════════════════════════════════════════════════════════════════════════════
# ENUMERATIONS
# ══════════════════════════════════════════════════════════════════════════════

class CrystalOrder(Enum):
    """Ordinal position in the evolution ladder."""
    BASE         = 1
    COMPOSITE    = 2
    HIGHER_ORDER = 3
    QUASI        = 4


class ValueDomain(Enum):
    """Allowed value types for a facet.  A facet may permit multiple domains."""
    IDENTIFIER     = auto()   # module path, file, class, function name
    CATEGORICAL    = auto()   # controlled vocabulary token
    NARRATIVE      = auto()   # free-text description
    BOOLEAN        = auto()   # binary flag
    NUMERIC        = auto()   # int or float measurement
    ENUM_REF       = auto()   # reference to a named enum value
    SCORE          = auto()   # 0.0–1.0 confidence / quality scalar
    TIMESTAMP      = auto()   # ISO-8601 datetime string
    CRYSTAL_REF    = auto()   # UUID pointer to another crystal node


class InferenceKind(Enum):
    """Kinds of inference a facet participates in."""
    CAUSAL_TRACE    = auto()   # can be chained into a cause–effect path
    PATTERN_CLUSTER = auto()   # can be used to form issue families
    STRATEGY_MATCH  = auto()   # can be matched against strategy templates
    CONTRADICTION   = auto()   # when two values conflict, triggers re-analysis
    ESCALATION      = auto()   # contributes to escalation-trigger scoring
    HYPOTHESIS      = auto()   # seeds new intervention hypotheses


class PointRole(Enum):
    """Structural role of a relational point inside a crystal."""
    CAUSAL_ANCHOR      = auto()   # marks a cause–effect boundary
    PATTERN_BRIDGE     = auto()   # joins two recurrence signals
    STRATEGY_LINKER    = auto()   # connects an intervention to a strategy class
    DIAGNOSTIC_EDGE    = auto()   # carries diagnostic evidence
    COLLAPSE_SEED      = auto()   # survives into quasicrystal inner strata
    ROTATION_PIVOT     = auto()   # acts as axis for crystal rotation analysis
    ESCALATION_MARKER  = auto()   # presence elevates escalation score


# ══════════════════════════════════════════════════════════════════════════════
# FACET LAW
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class FacetLaw:
    """
    Full semantic law for one facet.

    Parameters
    ----------
    name            : Canonical facet identifier used throughout the system.
    description     : What this facet represents in the diagnostic event model.
    value_domains   : The set of ValueDomain types a value for this facet may take.
    example_values  : Non-exhaustive examples showing the value space.
    promotion_role  : How this facet's content influences promotion decisions.
    allowed_partners: Facet names this facet is permitted to form a relational
                      point with.  (Enforced by the engine; not just advisory.)
    inference_kinds : Which inference operations this facet participates in.
    survival_rules  : What happens to this facet as the crystal ascends orders.
                      Key  = target CrystalOrder,
                      Value = "carry_forward" | "fold_inward" | "aggregate" |
                              "supersede" | "expand"
    """
    name            : str
    description     : str
    value_domains   : Tuple[ValueDomain, ...]
    example_values  : Tuple[str, ...]
    promotion_role  : str
    allowed_partners: Tuple[str, ...]
    inference_kinds : Tuple[InferenceKind, ...]
    survival_rules  : Dict[CrystalOrder, str]


# ── Base Crystal Facets (Level 1) ─────────────────────────────────────────────

FACET_TARGET = FacetLaw(
    name="target",
    description=(
        "The specific location in the system where the issue manifests. "
        "This is not a broad module — it is the precise addressable node: "
        "a function, class method, pipeline stage, or config key that was "
        "observed to misbehave.  It anchors every other facet to a real "
        "place in the codebase or architecture."
    ),
    value_domains=(ValueDomain.IDENTIFIER, ValueDomain.CATEGORICAL),
    example_values=(
        "aurora_runtime.corpus_runner",
        "ExpressionEcology.WisdomStore._ingest()",
        "ChainSimBridge._forward_to_sim()",
        "NC_manifold.slot[412]",
    ),
    promotion_role=(
        "Used to cluster events by architectural location at composite level. "
        "At higher-order, determines which strategy applicability conditions "
        "hold.  At quasicrystal, becomes part of the applicability boundary."
    ),
    allowed_partners=(
        "issue", "logic_tier", "intervention",
        "observed_effect", "recurrence_pattern",
        "distribution_context", "applicability_conditions",
    ),
    inference_kinds=(
        InferenceKind.CAUSAL_TRACE,
        InferenceKind.PATTERN_CLUSTER,
        InferenceKind.STRATEGY_MATCH,
    ),
    survival_rules={
        CrystalOrder.BASE         : "carry_forward",
        CrystalOrder.COMPOSITE    : "aggregate",      # grouped by location cluster
        CrystalOrder.HIGHER_ORDER : "carry_forward",
        CrystalOrder.QUASI        : "fold_inward",    # becomes inner strata target map
    },
)

FACET_ISSUE = FacetLaw(
    name="issue",
    description=(
        "The observed failure or diagnostic anomaly.  This is not a vague "
        "complaint — it is the classified symptom: what was wrong, stated in "
        "terms the system can act on.  Values are drawn from a controlled "
        "diagnostic vocabulary (type error, attribute not found, incorrect "
        "return value, silent data corruption, constraint violation, etc.) "
        "so that two events describing the same class of failure can be "
        "recognised as related without natural-language matching."
    ),
    value_domains=(ValueDomain.CATEGORICAL, ValueDomain.NARRATIVE),
    example_values=(
        "attribute_name_mismatch",
        "outlet_push_fraction_permanently_zero",
        "shard_not_reaching_ingestion",
        "pair_stats_not_persisting_across_runs",
        "missing_module_blocks_boot",
    ),
    promotion_role=(
        "Primary clustering key at composite level — events sharing an issue "
        "category form the core of an issue family.  At higher-order, issue "
        "maps to a strategy class.  At quasicrystal, becomes issue_archetype."
    ),
    allowed_partners=(
        "target", "logic_tier", "intervention",
        "intended_effect", "observed_effect",
        "recurrence_pattern", "distribution_context",
        "strategy_class", "failure_modes",
    ),
    inference_kinds=(
        InferenceKind.CAUSAL_TRACE,
        InferenceKind.PATTERN_CLUSTER,
        InferenceKind.STRATEGY_MATCH,
        InferenceKind.CONTRADICTION,
        InferenceKind.HYPOTHESIS,
    ),
    survival_rules={
        CrystalOrder.BASE         : "carry_forward",
        CrystalOrder.COMPOSITE    : "aggregate",
        CrystalOrder.HIGHER_ORDER : "supersede",      # collapsed into strategy_class input
        CrystalOrder.QUASI        : "fold_inward",
    },
)

FACET_LOGIC_TIER = FacetLaw(
    name="logic_tier",
    description=(
        "The architectural stratum that produced the issue.  The system is "
        "understood to have distinct semantic layers — data contract layer, "
        "constraint physics layer, evolutionary pipeline layer, persistence "
        "layer, runtime orchestration layer, etc. — and any given bug lives "
        "in exactly one tier even if its effects bleed across several. "
        "This facet names that home tier.  It controls which classes of fix "
        "are structurally applicable and which strategies are permitted."
    ),
    value_domains=(ValueDomain.CATEGORICAL, ValueDomain.ENUM_REF),
    example_values=(
        "data_contract",
        "constraint_physics",
        "evolutionary_pipeline",
        "persistence",
        "runtime_orchestration",
        "governance_gateway",
        "expression_ecology",
    ),
    promotion_role=(
        "At composite, reveals whether an issue family is tier-local or "
        "cross-tier.  At higher-order, gates strategy applicability. "
        "At quasicrystal, contributes to applicability_boundary."
    ),
    allowed_partners=(
        "target", "issue", "intervention",
        "observed_effect", "recurrence_pattern",
        "distribution_context", "strategy_class",
        "applicability_conditions",
    ),
    inference_kinds=(
        InferenceKind.CAUSAL_TRACE,
        InferenceKind.PATTERN_CLUSTER,
        InferenceKind.STRATEGY_MATCH,
    ),
    survival_rules={
        CrystalOrder.BASE         : "carry_forward",
        CrystalOrder.COMPOSITE    : "aggregate",
        CrystalOrder.HIGHER_ORDER : "carry_forward",
        CrystalOrder.QUASI        : "fold_inward",
    },
)

FACET_INTERVENTION = FacetLaw(
    name="intervention",
    description=(
        "The specific action taken to address the issue.  This is not the "
        "intention behind the action — it is the action itself: rename "
        "attribute, add missing import, patch method return type, rewrite "
        "label map, implement bridge method, etc.  The vocabulary is "
        "categorical so that the system can identify when two different "
        "events were addressed with structurally identical interventions."
    ),
    value_domains=(ValueDomain.CATEGORICAL, ValueDomain.NARRATIVE),
    example_values=(
        "rename_attribute",
        "add_label_to_variant_map",
        "implement_shard_bridge_method",
        "rewrite_pair_stats_persistence",
        "patch_genealogy_attribute_reference",
        "add_missing_module_file",
    ),
    promotion_role=(
        "At composite, measures whether one intervention class reliably "
        "resolves an issue family.  At higher-order, maps to strategy_class "
        "via intervention ↔ strategy_class point.  At quasicrystal, "
        "contributes to primary_strategy and secondary_strategy."
    ),
    allowed_partners=(
        "logic_tier", "target", "issue",
        "intended_effect", "recurrence_pattern",
        "strategy_class",
    ),
    inference_kinds=(
        InferenceKind.CAUSAL_TRACE,
        InferenceKind.STRATEGY_MATCH,
        InferenceKind.HYPOTHESIS,
    ),
    survival_rules={
        CrystalOrder.BASE         : "carry_forward",
        CrystalOrder.COMPOSITE    : "aggregate",
        CrystalOrder.HIGHER_ORDER : "supersede",
        CrystalOrder.QUASI        : "fold_inward",
    },
)

FACET_INTENDED_EFFECT = FacetLaw(
    name="intended_effect",
    description=(
        "The designer's stated goal for the intervention.  What was the "
        "change supposed to accomplish?  This is recorded before the outcome "
        "is known and serves as the reference signal against which "
        "observed_effect is measured.  It must be specific enough that "
        "the comparison is possible: not 'fix the bug' but 'ensure "
        "outlet_push_fraction increments when A:OUTLET_PUSH events fire'."
    ),
    value_domains=(ValueDomain.NARRATIVE, ValueDomain.CATEGORICAL),
    example_values=(
        "ensure_label_resolves_to_ability_variant",
        "propagate_shard_to_wisdom_store_ingestion",
        "persist_pair_stats_additively_across_runs",
        "unblock_boot_by_providing_missing_module",
    ),
    promotion_role=(
        "Compared against observed_effect to compute resolution_fidelity score "
        "used in promotion thresholds.  At higher-order, intended_effect "
        "contributes to strategy_outcome_profile."
    ),
    allowed_partners=(
        "intervention", "issue", "observed_effect",
    ),
    inference_kinds=(
        InferenceKind.CAUSAL_TRACE,
        InferenceKind.CONTRADICTION,
    ),
    survival_rules={
        CrystalOrder.BASE         : "carry_forward",
        CrystalOrder.COMPOSITE    : "aggregate",
        CrystalOrder.HIGHER_ORDER : "expand",         # becomes outcome_profile input
        CrystalOrder.QUASI        : "fold_inward",
    },
)

FACET_OBSERVED_EFFECT = FacetLaw(
    name="observed_effect",
    description=(
        "What actually happened after the intervention.  This is the empirical "
        "record: did the symptom resolve, partially resolve, shift, worsen, "
        "or produce a new downstream failure?  The value must be as specific "
        "as the intended_effect so that resolution_fidelity can be calculated. "
        "Unverified interventions carry observed_effect = 'pending'."
    ),
    value_domains=(ValueDomain.CATEGORICAL, ValueDomain.NARRATIVE),
    example_values=(
        "resolved_fully",
        "resolved_partially__downstream_issue_appeared",
        "no_change_observed",
        "regression_introduced",
        "pending_verification",
    ),
    promotion_role=(
        "Primary signal for resolution_fidelity scoring.  Events where "
        "observed_effect diverges from intended_effect are flagged for "
        "contradiction analysis.  At composite, determines issue-family "
        "resolution rate.  At higher-order, seeds strategy failure modes."
    ),
    allowed_partners=(
        "intended_effect", "issue", "logic_tier",
        "target", "distribution_context",
        "strategy_outcome_profile",
    ),
    inference_kinds=(
        InferenceKind.CAUSAL_TRACE,
        InferenceKind.CONTRADICTION,
        InferenceKind.ESCALATION,
        InferenceKind.PATTERN_CLUSTER,
    ),
    survival_rules={
        CrystalOrder.BASE         : "carry_forward",
        CrystalOrder.COMPOSITE    : "aggregate",
        CrystalOrder.HIGHER_ORDER : "expand",
        CrystalOrder.QUASI        : "fold_inward",
    },
)

# ── Composite Crystal Additional Facets (Level 2) ────────────────────────────

FACET_RECURRENCE_PATTERN = FacetLaw(
    name="recurrence_pattern",
    description=(
        "A named pattern describing how an issue repeats across events.  "
        "This facet does not exist in a single base event — it is computed "
        "at composite level by clustering base crystals that share issue "
        "and logic_tier values.  Values describe the temporal and structural "
        "shape of recurrence: sporadic, periodic, cascading, co-occurring. "
        "A recurrence_pattern is the composite crystal's core identity."
    ),
    value_domains=(ValueDomain.CATEGORICAL, ValueDomain.NUMERIC),
    example_values=(
        "sporadic__same_tier",
        "cascading__cross_tier",
        "periodic__every_N_evolution_cycles",
        "co_occurring__with_issue_class_X",
        "isolated__single_event",
    ),
    promotion_role=(
        "Determines whether a composite crystal qualifies for promotion to "
        "higher-order.  Persistent or cascading patterns have higher promotion "
        "weight than sporadic ones."
    ),
    allowed_partners=(
        "issue", "target", "logic_tier", "intervention",
    ),
    inference_kinds=(
        InferenceKind.PATTERN_CLUSTER,
        InferenceKind.STRATEGY_MATCH,
        InferenceKind.ESCALATION,
    ),
    survival_rules={
        CrystalOrder.COMPOSITE    : "carry_forward",
        CrystalOrder.HIGHER_ORDER : "aggregate",
        CrystalOrder.QUASI        : "fold_inward",
    },
)

FACET_DISTRIBUTION_CONTEXT = FacetLaw(
    name="distribution_context",
    description=(
        "A description of where in the system the issue family is distributed. "
        "Does it appear in one module only, across modules in one tier, or "
        "across tiers?  Does it occur in one evolutionary pipeline stage or "
        "many?  This is not a list of targets — it is a structural topology "
        "descriptor that informs whether a local or systemic intervention "
        "strategy is appropriate."
    ),
    value_domains=(ValueDomain.CATEGORICAL, ValueDomain.NARRATIVE),
    example_values=(
        "single_module__isolated",
        "multi_module__same_tier",
        "cross_tier__data_contract_to_persistence",
        "pipeline_wide__all_stages",
        "concentrated__evolution_boundary_only",
    ),
    promotion_role=(
        "A cross-tier distribution significantly raises the strategy complexity "
        "and boosts the push toward higher-order crystal formation."
    ),
    allowed_partners=(
        "target", "issue", "logic_tier", "observed_effect",
    ),
    inference_kinds=(
        InferenceKind.PATTERN_CLUSTER,
        InferenceKind.STRATEGY_MATCH,
        InferenceKind.ESCALATION,
    ),
    survival_rules={
        CrystalOrder.COMPOSITE    : "carry_forward",
        CrystalOrder.HIGHER_ORDER : "aggregate",
        CrystalOrder.QUASI        : "fold_inward",
    },
)

# ── Higher-Order Crystal Additional Facets (Level 3) ─────────────────────────

FACET_STRATEGY_CLASS = FacetLaw(
    name="strategy_class",
    description=(
        "The abstract class of intervention strategy that addresses this issue "
        "family.  This is not a specific fix action — it is the generalised "
        "approach: schema_alignment, label_registry_repair, bridge_implementation, "
        "persistence_protocol_upgrade, module_provision, etc.  Strategy classes "
        "are the vocabulary of reusable reasoning.  A strategy_class may map "
        "to many specific interventions."
    ),
    value_domains=(ValueDomain.CATEGORICAL, ValueDomain.ENUM_REF),
    example_values=(
        "schema_alignment",
        "label_registry_repair",
        "bridge_implementation",
        "persistence_protocol_upgrade",
        "module_provision",
        "constraint_relaxation",
        "lineage_integrity_enforcement",
    ),
    promotion_role=(
        "Primary identity field of a higher-order crystal.  A crystal with "
        "a stable, high-confidence strategy_class is a candidate for quasi "
        "collapse.  A crystal with conflicting strategy classes triggers "
        "rotation analysis before promotion."
    ),
    allowed_partners=(
        "issue", "logic_tier", "intervention",
        "strategy_outcome_profile", "failure_modes",
        "applicability_conditions",
    ),
    inference_kinds=(
        InferenceKind.STRATEGY_MATCH,
        InferenceKind.HYPOTHESIS,
        InferenceKind.CONTRADICTION,
    ),
    survival_rules={
        CrystalOrder.HIGHER_ORDER : "carry_forward",
        CrystalOrder.QUASI        : "supersede",   # becomes primary/secondary strategy
    },
)

FACET_STRATEGY_OUTCOME_PROFILE = FacetLaw(
    name="strategy_outcome_profile",
    description=(
        "The statistical and qualitative summary of how well this strategy "
        "class has performed.  Includes resolution rate, partial-resolution "
        "rate, regression rate, and the typical time-to-resolution.  This is "
        "computed from the aggregated observed_effect values of all base "
        "events whose interventions were classified under this strategy_class."
    ),
    value_domains=(ValueDomain.SCORE, ValueDomain.NARRATIVE),
    example_values=(
        "resolution_rate=0.91 regression_rate=0.04 median_ttv=1_cycle",
        "resolution_rate=0.60 partial_rate=0.30 regression_rate=0.10",
    ),
    promotion_role=(
        "High resolution_rate with low regression_rate is the primary "
        "quantitative gate for quasicrystal promotion."
    ),
    allowed_partners=(
        "strategy_class", "observed_effect",
    ),
    inference_kinds=(
        InferenceKind.STRATEGY_MATCH,
        InferenceKind.ESCALATION,
    ),
    survival_rules={
        CrystalOrder.HIGHER_ORDER : "carry_forward",
        CrystalOrder.QUASI        : "supersede",   # becomes expected_effects facet
    },
)

FACET_STRATEGY_FAILURE_MODES = FacetLaw(
    name="failure_modes",
    description=(
        "The known conditions under which this strategy class fails.  These "
        "are derived from base events where the intervention matched the "
        "strategy class but observed_effect showed no resolution or regression. "
        "Each failure mode is a named condition: precondition_not_met, "
        "cross_tier_dependency_unsatisfied, schema_version_mismatch, etc."
    ),
    value_domains=(ValueDomain.CATEGORICAL, ValueDomain.NARRATIVE),
    example_values=(
        "precondition_not_met__label_missing_upstream",
        "cross_tier_dependency_unsatisfied",
        "schema_version_mismatch_at_boundary",
        "incorrect_applicability_assumption",
    ),
    promotion_role=(
        "Failure modes feed directly into quasicrystal failure_indicators. "
        "A strategy with many failure modes and low outcome profile is not "
        "promoted — instead it is re-examined by rotation."
    ),
    allowed_partners=(
        "strategy_class", "issue",
    ),
    inference_kinds=(
        InferenceKind.CONTRADICTION,
        InferenceKind.ESCALATION,
        InferenceKind.HYPOTHESIS,
    ),
    survival_rules={
        CrystalOrder.HIGHER_ORDER : "carry_forward",
        CrystalOrder.QUASI        : "supersede",   # becomes failure_indicators
    },
)

FACET_APPLICABILITY_CONDITIONS = FacetLaw(
    name="applicability_conditions",
    description=(
        "The set of structural conditions that must be true for this strategy "
        "class to be applicable.  These are derived from the logic_tier and "
        "target distributions of successful base events.  A strategy that "
        "only worked in the persistence layer with single-module distribution "
        "carries those as applicability conditions — it must not be applied "
        "blindly to cross-tier patterns."
    ),
    value_domains=(ValueDomain.CATEGORICAL, ValueDomain.NARRATIVE),
    example_values=(
        "logic_tier IN [persistence, runtime_orchestration]",
        "distribution_context = single_module",
        "recurrence_pattern NOT cascading",
        "target_layer = data_contract",
    ),
    promotion_role=(
        "Prevents over-generalisation.  A strategy with overly broad "
        "applicability conditions that failed in multiple contexts is demoted "
        "or split into narrower strategies."
    ),
    allowed_partners=(
        "strategy_class", "target", "logic_tier",
    ),
    inference_kinds=(
        InferenceKind.STRATEGY_MATCH,
        InferenceKind.CONTRADICTION,
    ),
    survival_rules={
        CrystalOrder.HIGHER_ORDER : "carry_forward",
        CrystalOrder.QUASI        : "supersede",   # becomes applicability_boundary
    },
)

# ── Quasicrystal Outer Shell Facets (Level 4) ─────────────────────────────────

FACET_ISSUE_ARCHETYPE = FacetLaw(
    name="issue_archetype",
    description=(
        "The collapsed identity of the issue family that this quasicrystal "
        "represents.  Derived from the dominant issue category across all "
        "base events in the genealogy.  This is what the quasicrystal 'is' "
        "from the outside — the label that pattern-matching systems use to "
        "retrieve it."
    ),
    value_domains=(ValueDomain.CATEGORICAL,),
    example_values=(
        "attribute_contract_violation",
        "label_registry_gap",
        "pipeline_shard_dropout",
        "persistence_boundary_failure",
    ),
    promotion_role="Terminal outer identity facet.  Not promoted further.",
    allowed_partners=(),
    inference_kinds=(InferenceKind.PATTERN_CLUSTER, InferenceKind.STRATEGY_MATCH),
    survival_rules={CrystalOrder.QUASI: "carry_forward"},
)

FACET_PRIMARY_STRATEGY = FacetLaw(
    name="primary_strategy",
    description=(
        "The strategy_class with the highest outcome profile score from the "
        "higher-order genealogy.  This is the recommended first-choice "
        "intervention approach when a new event matching this quasicrystal's "
        "archetype is encountered."
    ),
    value_domains=(ValueDomain.CATEGORICAL, ValueDomain.ENUM_REF),
    example_values=("schema_alignment", "label_registry_repair"),
    promotion_role="Terminal outer strategy facet.",
    allowed_partners=(),
    inference_kinds=(InferenceKind.STRATEGY_MATCH, InferenceKind.HYPOTHESIS),
    survival_rules={CrystalOrder.QUASI: "carry_forward"},
)

FACET_SECONDARY_STRATEGY = FacetLaw(
    name="secondary_strategy",
    description=(
        "The fallback strategy class used when primary_strategy fails or when "
        "applicability conditions are not satisfied.  Derived from the second- "
        "highest outcome profile.  May be None if only one strategy class "
        "survived genealogy with adequate confidence."
    ),
    value_domains=(ValueDomain.CATEGORICAL, ValueDomain.ENUM_REF),
    example_values=("bridge_implementation", "module_provision"),
    promotion_role="Terminal outer fallback facet.",
    allowed_partners=(),
    inference_kinds=(InferenceKind.STRATEGY_MATCH, InferenceKind.HYPOTHESIS),
    survival_rules={CrystalOrder.QUASI: "carry_forward"},
)

FACET_APPLICABILITY_BOUNDARY = FacetLaw(
    name="applicability_boundary",
    description=(
        "The collapsed and refined applicability_conditions from the higher-order "
        "crystal, expressed as a set of hard boundary constraints.  If a new "
        "event does not satisfy these boundaries, this quasicrystal is not "
        "retrieved as a match — even if the issue_archetype aligns."
    ),
    value_domains=(ValueDomain.CATEGORICAL, ValueDomain.NARRATIVE),
    example_values=(
        "logic_tier IN [persistence]  AND  distribution = single_module",
        "recurrence NOT cascading",
    ),
    promotion_role="Terminal outer gating facet.",
    allowed_partners=(),
    inference_kinds=(InferenceKind.STRATEGY_MATCH,),
    survival_rules={CrystalOrder.QUASI: "carry_forward"},
)

FACET_CONFIDENCE = FacetLaw(
    name="confidence",
    description=(
        "A 0.0–1.0 scalar expressing the quasicrystal's overall reliability. "
        "Computed as a weighted combination of: outcome profile resolution_rate, "
        "genealogy depth (how many base events contributed), recurrence "
        "pattern stability, and failure_mode density.  A quasicrystal with "
        "confidence < 0.5 is marked provisional and is not used for automated "
        "strategy recommendation without human review."
    ),
    value_domains=(ValueDomain.SCORE,),
    example_values=("0.87", "0.62", "0.41"),
    promotion_role="Terminal outer quality scalar.",
    allowed_partners=(),
    inference_kinds=(InferenceKind.ESCALATION,),
    survival_rules={CrystalOrder.QUASI: "carry_forward"},
)

FACET_FAILURE_INDICATORS = FacetLaw(
    name="failure_indicators",
    description=(
        "The collapsed and deduplicated failure modes from the higher-order "
        "genealogy.  These are the observable signals that indicate the "
        "primary_strategy is about to fail or has already failed.  They allow "
        "the system to detect mid-intervention breakdown and switch to the "
        "secondary strategy or escalate."
    ),
    value_domains=(ValueDomain.CATEGORICAL, ValueDomain.NARRATIVE),
    example_values=(
        "label_still_absent_after_registry_repair",
        "observed_effect = no_change after N attempts",
    ),
    promotion_role="Terminal outer failure surface.",
    allowed_partners=(),
    inference_kinds=(InferenceKind.CONTRADICTION, InferenceKind.ESCALATION),
    survival_rules={CrystalOrder.QUASI: "carry_forward"},
)

FACET_EXPECTED_EFFECTS = FacetLaw(
    name="expected_effects",
    description=(
        "The canonical outcome profile translated into observable expected "
        "effects: what the system should see after primary_strategy is applied. "
        "Derived from the aggregated intended_effect and observed_effect "
        "record of all successful base events in the genealogy."
    ),
    value_domains=(ValueDomain.NARRATIVE, ValueDomain.CATEGORICAL),
    example_values=(
        "outlet_push_fraction increments within next evolution cycle",
        "shard reaches WisdomStore._ingest() without dropout",
    ),
    promotion_role="Terminal outer observable expectation.",
    allowed_partners=(),
    inference_kinds=(InferenceKind.CAUSAL_TRACE, InferenceKind.CONTRADICTION),
    survival_rules={CrystalOrder.QUASI: "carry_forward"},
)

FACET_ESCALATION_TRIGGER = FacetLaw(
    name="escalation_trigger",
    description=(
        "The conditions under which this quasicrystal's issue archetype must "
        "be escalated beyond automated strategy application — because the "
        "available strategies are insufficient, the failure_indicators have "
        "fired multiple times, or the applicability_boundary cannot be "
        "satisfied by any known strategy.  Escalation means: surface to "
        "human review or trigger architectural-level redesign flag."
    ),
    value_domains=(ValueDomain.CATEGORICAL, ValueDomain.NARRATIVE),
    example_values=(
        "both_strategies_failed_in_same_event",
        "failure_indicator_fired_3x_consecutive",
        "confidence_below_threshold_AND_cross_tier_distribution",
    ),
    promotion_role="Terminal outer escalation gate.",
    allowed_partners=(),
    inference_kinds=(InferenceKind.ESCALATION,),
    survival_rules={CrystalOrder.QUASI: "carry_forward"},
)


# ══════════════════════════════════════════════════════════════════════════════
# CANONICAL FACET REGISTRIES BY CRYSTAL ORDER
# ══════════════════════════════════════════════════════════════════════════════

BASE_FACETS: Dict[str, FacetLaw] = {
    f.name: f for f in [
        FACET_TARGET, FACET_ISSUE, FACET_LOGIC_TIER,
        FACET_INTERVENTION, FACET_INTENDED_EFFECT, FACET_OBSERVED_EFFECT,
    ]
}

COMPOSITE_FACETS: Dict[str, FacetLaw] = {
    **BASE_FACETS,
    **{f.name: f for f in [FACET_RECURRENCE_PATTERN, FACET_DISTRIBUTION_CONTEXT]},
}

HIGHER_ORDER_FACETS: Dict[str, FacetLaw] = {
    **COMPOSITE_FACETS,
    **{f.name: f for f in [
        FACET_STRATEGY_CLASS, FACET_STRATEGY_OUTCOME_PROFILE,
        FACET_STRATEGY_FAILURE_MODES, FACET_APPLICABILITY_CONDITIONS,
    ]},
}

QUASI_OUTER_FACETS: Dict[str, FacetLaw] = {
    f.name: f for f in [
        FACET_ISSUE_ARCHETYPE, FACET_PRIMARY_STRATEGY, FACET_SECONDARY_STRATEGY,
        FACET_APPLICABILITY_BOUNDARY, FACET_CONFIDENCE, FACET_FAILURE_INDICATORS,
        FACET_EXPECTED_EFFECTS, FACET_ESCALATION_TRIGGER,
    ]
}

FACETS_BY_ORDER: Dict[CrystalOrder, Dict[str, FacetLaw]] = {
    CrystalOrder.BASE         : BASE_FACETS,
    CrystalOrder.COMPOSITE    : COMPOSITE_FACETS,
    CrystalOrder.HIGHER_ORDER : HIGHER_ORDER_FACETS,
    CrystalOrder.QUASI        : QUASI_OUTER_FACETS,
}


# ══════════════════════════════════════════════════════════════════════════════
# RELATIONAL POINT LAW
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RelationalPointLaw:
    """
    Full semantic law for one relational point — the overlap between two facets.

    Parameters
    ----------
    name              : Canonical identifier, always in the form 'facetA__facetB'.
    facet_a           : First facet in the relation.
    facet_b           : Second facet in the relation.
    description       : What this relation represents; what question it answers.
    evidence_sources  : What kinds of data populate it (field values, logs, tests).
    scoring_method    : How the strength or quality of this relation is scored.
    contradiction_sig : What contradictory values at this point look like.
    cluster_role      : How this point contributes to issue-family clustering.
    strategy_contrib  : How this point contributes to strategy formation.
    collapse_fate     : What happens to this point during quasicrystal collapse.
                        "internalized" = survives as inner strata entry.
                        "discarded"    = not retained after collapse.
                        "promoted"     = becomes outer facet content.
    roles             : PointRole enum set.
    crystal_order     : Lowest CrystalOrder at which this point is valid.
    """
    name             : str
    facet_a          : str
    facet_b          : str
    description      : str
    evidence_sources : Tuple[str, ...]
    scoring_method   : str
    contradiction_sig: str
    cluster_role     : str
    strategy_contrib : str
    collapse_fate    : str
    roles            : Tuple[PointRole, ...]
    crystal_order    : CrystalOrder


# ── Base Crystal Points (Level 1) — 12 points ────────────────────────────────

POINT_TARGET__ISSUE = RelationalPointLaw(
    name="target__issue",
    facet_a="target",
    facet_b="issue",
    description=(
        "Where the problem manifests.  This point anchors the issue to a "
        "real structural location.  Without it, the issue is abstract; with "
        "it, the issue has a home address.  Repeated hits on the same "
        "target__issue pair signal a structurally vulnerable location."
    ),
    evidence_sources=(
        "error tracebacks", "test failure output", "runtime logs",
        "static analysis reports",
    ),
    scoring_method=(
        "Score = 1.0 for confirmed co-occurrence with traceback evidence; "
        "0.7 for inferred from test failure; 0.4 for manual report only."
    ),
    contradiction_sig=(
        "Same issue, different targets across consecutive events — suggests "
        "the issue has migrated or the target identification is imprecise."
    ),
    cluster_role=(
        "Primary axis for base-to-composite clustering.  Events sharing a "
        "target__issue pair are the seed of an issue family."
    ),
    strategy_contrib=(
        "Informs which structural locations are candidates for a given "
        "strategy class.  High-frequency target__issue pairs bias "
        "applicability_conditions toward that target."
    ),
    collapse_fate="internalized",
    roles=(PointRole.CAUSAL_ANCHOR, PointRole.COLLAPSE_SEED),
    crystal_order=CrystalOrder.BASE,
)

POINT_ISSUE__LOGIC_TIER = RelationalPointLaw(
    name="issue__logic_tier",
    facet_a="issue",
    facet_b="logic_tier",
    description=(
        "What layer of logic produced the issue.  This point determines "
        "whether the issue is a data-contract failure, a physics-layer "
        "inconsistency, a pipeline dropout, a persistence gap, or an "
        "orchestration error.  The tier shapes which intervention classes "
        "are even available."
    ),
    evidence_sources=(
        "module namespace of failing code", "layer diagram annotations",
        "architecture doc tier assignments",
    ),
    scoring_method=(
        "Score = 1.0 when traceback unambiguously identifies the tier's "
        "module; 0.6 when inferred from module namespace; 0.3 when assigned "
        "by developer judgment alone."
    ),
    contradiction_sig=(
        "Same issue assigned to different logic_tiers across events — "
        "suggests either a cross-tier leak or incorrect tier classification."
    ),
    cluster_role=(
        "Secondary clustering axis alongside target__issue.  Determines "
        "whether an issue family is tier-homogeneous or cross-tier."
    ),
    strategy_contrib=(
        "Tier assignment is the primary gate for strategy_class applicability "
        "at higher-order.  Mismatch between tier and strategy produces a "
        "contradiction at the issue__logic_tier point."
    ),
    collapse_fate="internalized",
    roles=(PointRole.CAUSAL_ANCHOR, PointRole.DIAGNOSTIC_EDGE, PointRole.COLLAPSE_SEED),
    crystal_order=CrystalOrder.BASE,
)

POINT_LOGIC_TIER__INTERVENTION = RelationalPointLaw(
    name="logic_tier__intervention",
    facet_a="logic_tier",
    facet_b="intervention",
    description=(
        "What class of fix applies to a given tier.  Not all interventions "
        "are valid at all tiers.  A persistence-layer issue cannot be fixed "
        "by renaming an attribute in the physics layer.  This point enforces "
        "structural appropriateness of the intervention."
    ),
    evidence_sources=(
        "intervention taxonomy table", "architecture fix-class matrix",
        "prior successful intervention records",
    ),
    scoring_method=(
        "Score = 1.0 for tier-matched intervention with historical success; "
        "0.5 for cross-tier intervention with partial precedent; "
        "0.0 for structurally invalid tier–intervention pairing."
    ),
    contradiction_sig=(
        "Intervention applied to a tier where it has no precedent and fails — "
        "invalidates the logic_tier__intervention pairing for future use."
    ),
    cluster_role=(
        "Used at composite level to detect whether one intervention class "
        "dominates a given tier's issue resolutions."
    ),
    strategy_contrib=(
        "Direct input to strategy_class derivation.  The dominant "
        "logic_tier__intervention pairing across a composite crystal "
        "names the strategy class."
    ),
    collapse_fate="promoted",
    roles=(PointRole.STRATEGY_LINKER, PointRole.ROTATION_PIVOT, PointRole.COLLAPSE_SEED),
    crystal_order=CrystalOrder.BASE,
)

POINT_INTERVENTION__INTENDED_EFFECT = RelationalPointLaw(
    name="intervention__intended_effect",
    facet_a="intervention",
    facet_b="intended_effect",
    description=(
        "What the change was meant to accomplish.  This point records the "
        "designer's causal hypothesis: if I do X, then Y should result.  "
        "It is the pre-outcome half of the causal arc; observed_effect "
        "completes the arc."
    ),
    evidence_sources=(
        "developer commit message", "task description", "PR summary",
        "debugging session notes",
    ),
    scoring_method=(
        "Score = 1.0 when intended_effect is specific and testable; "
        "0.5 when vague but directionally correct; "
        "0.1 when intended_effect is absent or tautological."
    ),
    contradiction_sig=(
        "Intended_effect describes resolution of a different issue than the "
        "one recorded — misaligned authorship of intention."
    ),
    cluster_role=(
        "Weak clustering signal alone.  Gains strength when combined with "
        "intervention__intended_effect → observed_effect arc."
    ),
    strategy_contrib=(
        "Feeds into strategy_outcome_profile as the reference signal against "
        "which outcomes are evaluated."
    ),
    collapse_fate="internalized",
    roles=(PointRole.CAUSAL_ANCHOR, PointRole.DIAGNOSTIC_EDGE),
    crystal_order=CrystalOrder.BASE,
)

POINT_INTENDED_EFFECT__OBSERVED_EFFECT = RelationalPointLaw(
    name="intended_effect__observed_effect",
    facet_a="intended_effect",
    facet_b="observed_effect",
    description=(
        "Did the change produce the expected result?  This is the core "
        "resolution signal.  High fidelity (observed matches intended) "
        "promotes the crystal upward.  Low fidelity triggers contradiction "
        "analysis and may seed failure_modes at higher-order."
    ),
    evidence_sources=(
        "test suite output", "runtime metric comparison",
        "manual verification log", "observed_effect field value",
    ),
    scoring_method=(
        "resolution_fidelity = 1.0 if observed_effect = resolved_fully; "
        "0.6 if partially resolved; 0.0 if no_change or regression. "
        "This score is the primary promotion signal."
    ),
    contradiction_sig=(
        "observed_effect = resolved_fully with a follow-on event reporting "
        "the same issue — indicates false resolution."
    ),
    cluster_role=(
        "High-fidelity events cluster together as 'successful resolutions' "
        "that validate the intervention class."
    ),
    strategy_contrib=(
        "resolution_fidelity is the dominant input to strategy_outcome_profile. "
        "Low-fidelity events define failure_modes."
    ),
    collapse_fate="promoted",
    roles=(
        PointRole.CAUSAL_ANCHOR, PointRole.ROTATION_PIVOT,
        PointRole.COLLAPSE_SEED, PointRole.ESCALATION_MARKER,
    ),
    crystal_order=CrystalOrder.BASE,
)

POINT_OBSERVED_EFFECT__ISSUE = RelationalPointLaw(
    name="observed_effect__issue",
    facet_a="observed_effect",
    facet_b="issue",
    description=(
        "Did the problem actually resolve?  This point closes the causal loop. "
        "When observed_effect = resolved_fully, the issue is retired in this "
        "event.  When observed_effect = no_change or regression, the issue "
        "remains open and the event feeds failure mode analysis."
    ),
    evidence_sources=(
        "follow-on test results", "subsequent event record",
        "issue tracker state", "runtime health metrics",
    ),
    scoring_method=(
        "Resolution confirmation score: 1.0 if issue does not reappear in "
        "N subsequent events; 0.5 if issue reappears after >3 events; "
        "0.0 if issue reappears immediately."
    ),
    contradiction_sig=(
        "Issue marked resolved but reappears within the same evolution cycle — "
        "triggers re-opening of the base crystal as unresolved."
    ),
    cluster_role=(
        "Determines whether a base crystal contributes to a 'resolved' or "
        "'unresolved' cluster within the issue family."
    ),
    strategy_contrib=(
        "Unresolved loops inflate failure_mode density and suppress confidence."
    ),
    collapse_fate="internalized",
    roles=(PointRole.CAUSAL_ANCHOR, PointRole.ESCALATION_MARKER),
    crystal_order=CrystalOrder.BASE,
)

POINT_TARGET__LOGIC_TIER = RelationalPointLaw(
    name="target__logic_tier",
    facet_a="target",
    facet_b="logic_tier",
    description=(
        "Which structural layer of the system this location belongs to.  "
        "This is an architectural truth claim: the target is a component of "
        "the logic_tier.  It validates that tier classification is consistent "
        "with the target's actual module position."
    ),
    evidence_sources=(
        "architecture doc tier-to-module mapping",
        "module directory structure", "import graph analysis",
    ),
    scoring_method=(
        "Score = 1.0 when target is formally assigned to this tier in the "
        "architecture doc; 0.5 when inferred from directory; "
        "0.2 when developer-asserted only."
    ),
    contradiction_sig=(
        "Target classified in two different tiers across two events — "
        "architecture mapping inconsistency."
    ),
    cluster_role=(
        "Used to validate tier assignments in composite clustering."
    ),
    strategy_contrib=(
        "Ensures strategy applicability conditions reference the correct tier."
    ),
    collapse_fate="internalized",
    roles=(PointRole.DIAGNOSTIC_EDGE, PointRole.COLLAPSE_SEED),
    crystal_order=CrystalOrder.BASE,
)

POINT_TARGET__INTERVENTION = RelationalPointLaw(
    name="target__intervention",
    facet_a="target",
    facet_b="intervention",
    description=(
        "How invasive the intervention was for that location.  Some targets "
        "are fragile — a rename propagates through many call sites.  Others "
        "are isolated — a single method patch has no downstream effect.  "
        "This point scores the intervention's structural impact on the target."
    ),
    evidence_sources=(
        "change scope analysis", "call-site count", "import dependency count",
        "test coverage of affected area",
    ),
    scoring_method=(
        "Invasiveness score: 0.0 = isolated patch; 0.5 = module-wide rename; "
        "1.0 = cross-module structural change.  "
        "High invasiveness increases escalation risk."
    ),
    contradiction_sig=(
        "Intervention marked low-invasiveness but produced cross-module "
        "observed effects — scope misclassification."
    ),
    cluster_role=(
        "High-invasiveness interventions on shared targets are flagged as "
        "systemic risks in composite analysis."
    ),
    strategy_contrib=(
        "Invasiveness feeds into strategy applicability conditions — "
        "high-invasiveness strategies carry restricted applicability."
    ),
    collapse_fate="internalized",
    roles=(PointRole.DIAGNOSTIC_EDGE, PointRole.ESCALATION_MARKER),
    crystal_order=CrystalOrder.BASE,
)

POINT_ISSUE__INTERVENTION = RelationalPointLaw(
    name="issue__intervention",
    facet_a="issue",
    facet_b="intervention",
    description=(
        "What fix class corresponds to that issue type.  This is the direct "
        "issue-to-fix mapping.  It is the most naive form of strategy — a "
        "lookup that says 'this category of problem is addressed by this "
        "category of action.'  Composite and higher-order crystals refine "
        "this into strategy_class with conditions."
    ),
    evidence_sources=(
        "intervention taxonomy table", "historical event records",
        "developer expertise notes",
    ),
    scoring_method=(
        "Mapping confidence = (successful events using this mapping) / "
        "(total events with this issue category).  "
        "Above 0.75 = strong mapping.  Below 0.4 = weak / contested."
    ),
    contradiction_sig=(
        "Same issue resolved by structurally incompatible interventions in "
        "different events — indicates the issue category is too broad."
    ),
    cluster_role=(
        "Core axis for issue family definition at composite level."
    ),
    strategy_contrib=(
        "Dominant issue__intervention pair becomes the seed of strategy_class."
    ),
    collapse_fate="promoted",
    roles=(PointRole.STRATEGY_LINKER, PointRole.ROTATION_PIVOT, PointRole.COLLAPSE_SEED),
    crystal_order=CrystalOrder.BASE,
)

POINT_ISSUE__INTENDED_EFFECT = RelationalPointLaw(
    name="issue__intended_effect",
    facet_a="issue",
    facet_b="intended_effect",
    description=(
        "What kind of resolution the issue demands.  Different issue categories "
        "have different resolution profiles.  An attribute mismatch demands "
        "alignment; a missing label demands registration; a pipeline dropout "
        "demands a bridge.  This point links the issue to its expected "
        "resolution shape."
    ),
    evidence_sources=(
        "issue taxonomy resolution rules", "historical resolution records",
    ),
    scoring_method=(
        "Fit score: 1.0 if intended_effect is the canonical resolution shape "
        "for this issue category; 0.5 if adjacent; 0.0 if mismatched."
    ),
    contradiction_sig=(
        "Intended_effect that addresses a symptom rather than the issue root — "
        "shallow fix flag."
    ),
    cluster_role=(
        "Used to distinguish 'proper' resolutions from symptomatic patches "
        "within an issue family."
    ),
    strategy_contrib=(
        "High-fit events define what a successful resolution looks like for "
        "a strategy class."
    ),
    collapse_fate="internalized",
    roles=(PointRole.DIAGNOSTIC_EDGE, PointRole.CAUSAL_ANCHOR),
    crystal_order=CrystalOrder.BASE,
)

POINT_LOGIC_TIER__OBSERVED_EFFECT = RelationalPointLaw(
    name="logic_tier__observed_effect",
    facet_a="logic_tier",
    facet_b="observed_effect",
    description=(
        "What system layer produced the measurable change.  The observed "
        "effect may appear in a different tier than the issue — this is how "
        "cross-tier cascade is detected.  A persistence-tier fix that produces "
        "an observable effect in the runtime-orchestration tier reveals a "
        "cross-layer dependency."
    ),
    evidence_sources=(
        "layer attribution of test failure output",
        "runtime metric tagged by module tier",
        "profiling data with tier annotation",
    ),
    scoring_method=(
        "Tier-match score: 1.0 if effect tier matches issue tier; "
        "0.5 if adjacent tier; 0.0 if remote tier — flags cross-tier cascade."
    ),
    contradiction_sig=(
        "Effect appears in a tier that has no logical path from the issue tier — "
        "suggests an undocumented dependency."
    ),
    cluster_role=(
        "Identifies cross-tier effect patterns at composite level."
    ),
    strategy_contrib=(
        "Cross-tier effects constrain strategy applicability and raise "
        "applicability_boundary thresholds."
    ),
    collapse_fate="internalized",
    roles=(PointRole.DIAGNOSTIC_EDGE, PointRole.ESCALATION_MARKER),
    crystal_order=CrystalOrder.BASE,
)

POINT_TARGET__OBSERVED_EFFECT = RelationalPointLaw(
    name="target__observed_effect",
    facet_a="target",
    facet_b="observed_effect",
    description=(
        "What part of the system experienced the outcome.  This closes the "
        "location loop: the issue was at the target, the intervention was "
        "applied to the target, and the observed effect is attributed back "
        "to the target.  When they all agree, the crystal is coherent.  "
        "When the effect appears elsewhere, a cascade is recorded."
    ),
    evidence_sources=(
        "post-intervention test output", "runtime health check attributed to target",
    ),
    scoring_method=(
        "Location coherence score: 1.0 if effect is observed at the target; "
        "0.5 if adjacent component; 0.0 if remote — cascade flag."
    ),
    contradiction_sig=(
        "Intervention at target A produces observed effect at target B with "
        "no documented link — undocumented coupling."
    ),
    cluster_role=(
        "Used to detect 'effect migration' patterns across issue families."
    ),
    strategy_contrib=(
        "Cascade events constrain strategy applicability to architecturally "
        "isolated targets."
    ),
    collapse_fate="internalized",
    roles=(PointRole.CAUSAL_ANCHOR, PointRole.COLLAPSE_SEED),
    crystal_order=CrystalOrder.BASE,
)


# ── Composite Crystal Additional Points (Level 2) — 8 new points ─────────────

POINT_ISSUE__RECURRENCE_PATTERN = RelationalPointLaw(
    name="issue__recurrence_pattern",
    facet_a="issue",
    facet_b="recurrence_pattern",
    description=(
        "Does this issue repeat across modules?  This point answers whether "
        "the issue category is a one-off anomaly or a structural recurring "
        "feature of the system.  The recurrence_pattern value is derived by "
        "analyzing all base crystals sharing this issue category."
    ),
    evidence_sources=(
        "base crystal cluster analysis", "event frequency count",
        "temporal distribution of events",
    ),
    scoring_method=(
        "Recurrence strength = (event count for issue category) weighted by "
        "temporal regularity.  Sporadic = low; periodic = medium; "
        "cascading = high."
    ),
    contradiction_sig=(
        "Issue classified as isolated but appears 4+ times across events — "
        "recurrence_pattern must be updated."
    ),
    cluster_role=(
        "Primary driver of composite crystal identity.  High recurrence "
        "strength is the first composite promotion criterion."
    ),
    strategy_contrib=(
        "High recurrence pushes toward persistent strategy class assignment."
    ),
    collapse_fate="internalized",
    roles=(PointRole.PATTERN_BRIDGE, PointRole.COLLAPSE_SEED),
    crystal_order=CrystalOrder.COMPOSITE,
)

POINT_TARGET__RECURRENCE_PATTERN = RelationalPointLaw(
    name="target__recurrence_pattern",
    facet_a="target",
    facet_b="recurrence_pattern",
    description=(
        "Does the issue cluster in one location?  This distinguishes a "
        "location-specific vulnerability (one target affected repeatedly) "
        "from a diffuse systemic pattern (many targets share the issue)."
    ),
    evidence_sources=("base crystal target frequency map", "location heat map"),
    scoring_method=(
        "Location concentration index: 1.0 = single target dominates; "
        "0.5 = distributed across 2-3 targets; 0.0 = diffuse across system."
    ),
    contradiction_sig=(
        "Pattern classified as concentrated but distributed across >5 targets."
    ),
    cluster_role="Distinguishes local from systemic issue families.",
    strategy_contrib=(
        "Concentrated patterns support targeted interventions; "
        "diffuse patterns require systemic strategies."
    ),
    collapse_fate="internalized",
    roles=(PointRole.PATTERN_BRIDGE,),
    crystal_order=CrystalOrder.COMPOSITE,
)

POINT_LOGIC_TIER__RECURRENCE_PATTERN = RelationalPointLaw(
    name="logic_tier__recurrence_pattern",
    facet_a="logic_tier",
    facet_b="recurrence_pattern",
    description=(
        "Does the issue cluster in one logic tier?  This identifies whether "
        "the recurrence is tier-local (a tier with structural debt) or "
        "cross-tier (a systemic architectural pattern)."
    ),
    evidence_sources=("base crystal tier frequency map",),
    scoring_method=(
        "Tier concentration index identical to target__recurrence_pattern."
    ),
    contradiction_sig="Pattern claims tier-local but appears across 3+ tiers.",
    cluster_role="Identifies structurally weak tiers.",
    strategy_contrib="Tier concentration informs strategy applicability tier gates.",
    collapse_fate="internalized",
    roles=(PointRole.PATTERN_BRIDGE,),
    crystal_order=CrystalOrder.COMPOSITE,
)

POINT_INTERVENTION__RECURRENCE_PATTERN = RelationalPointLaw(
    name="intervention__recurrence_pattern",
    facet_a="intervention",
    facet_b="recurrence_pattern",
    description=(
        "Does one intervention work consistently across targets?  This is "
        "the effectiveness stability signal.  If the same intervention class "
        "resolves a recurring issue across many targets, it is a strong "
        "strategy candidate.  If intervention effectiveness varies, the "
        "issue family may need to be split."
    ),
    evidence_sources=(
        "resolution_fidelity distribution across base crystals",
        "intervention frequency in successful events",
    ),
    scoring_method=(
        "Effectiveness stability = std deviation of resolution_fidelity "
        "across events using this intervention.  Low std = stable = good."
    ),
    contradiction_sig=(
        "Intervention resolves issue in some targets and causes regression "
        "in others — unstable, candidate for failure_mode entry."
    ),
    cluster_role="Validates or invalidates intervention class consistency.",
    strategy_contrib=(
        "High effectiveness stability promotes this intervention to primary "
        "strategy candidate."
    ),
    collapse_fate="promoted",
    roles=(PointRole.PATTERN_BRIDGE, PointRole.STRATEGY_LINKER, PointRole.ROTATION_PIVOT),
    crystal_order=CrystalOrder.COMPOSITE,
)

POINT_TARGET__DISTRIBUTION_CONTEXT = RelationalPointLaw(
    name="target__distribution_context",
    facet_a="target",
    facet_b="distribution_context",
    description=(
        "Where in the system is the issue family distributed?  This maps the "
        "affected target set to a structural topology descriptor."
    ),
    evidence_sources=("target list from base crystals", "architecture topology map"),
    scoring_method="Distribution breadth score based on distinct target count and tier span.",
    contradiction_sig="Distribution context says single_module but multiple modules are listed.",
    cluster_role="Topology classification for issue family.",
    strategy_contrib="Informs systemic vs local strategy selection.",
    collapse_fate="internalized",
    roles=(PointRole.PATTERN_BRIDGE, PointRole.DIAGNOSTIC_EDGE),
    crystal_order=CrystalOrder.COMPOSITE,
)

POINT_ISSUE__DISTRIBUTION_CONTEXT = RelationalPointLaw(
    name="issue__distribution_context",
    facet_a="issue",
    facet_b="distribution_context",
    description=(
        "Is this issue family geographically concentrated or system-wide?  "
        "Answers the question: if I fix it in one place, am I done?"
    ),
    evidence_sources=("issue category occurrence map",),
    scoring_method="Same topology breadth score as target__distribution_context.",
    contradiction_sig="Issue marked isolated but detected in 4+ separate modules.",
    cluster_role="Scope assignment for issue family.",
    strategy_contrib=(
        "Wide distribution demands pipeline-wide or architectural strategy; "
        "narrow demands local fix."
    ),
    collapse_fate="internalized",
    roles=(PointRole.PATTERN_BRIDGE, PointRole.ESCALATION_MARKER),
    crystal_order=CrystalOrder.COMPOSITE,
)

POINT_LOGIC_TIER__DISTRIBUTION_CONTEXT = RelationalPointLaw(
    name="logic_tier__distribution_context",
    facet_a="logic_tier",
    facet_b="distribution_context",
    description=(
        "Is the distribution of this issue family contained within one tier "
        "or does it span multiple tiers?  Cross-tier distribution changes the "
        "strategic options dramatically."
    ),
    evidence_sources=("tier distribution map from base crystal set",),
    scoring_method="Cross-tier breadth score: 1 tier = 0.0; 2 = 0.5; 3+ = 1.0.",
    contradiction_sig="Single-tier claim but events span multiple tier namespaces.",
    cluster_role="Tier topology for issue family.",
    strategy_contrib="Cross-tier distribution gates out single-tier strategy classes.",
    collapse_fate="internalized",
    roles=(PointRole.PATTERN_BRIDGE, PointRole.ESCALATION_MARKER),
    crystal_order=CrystalOrder.COMPOSITE,
)

POINT_OBSERVED_EFFECT__DISTRIBUTION_CONTEXT = RelationalPointLaw(
    name="observed_effect__distribution_context",
    facet_a="observed_effect",
    facet_b="distribution_context",
    description=(
        "Are the effects of interventions consistent across the distribution?  "
        "An issue family where the same intervention produces good effects in "
        "one cluster but poor effects in another may require context-specific "
        "strategies."
    ),
    evidence_sources=("observed_effect distribution by location cluster",),
    scoring_method=(
        "Effect consistency = std deviation of resolution_fidelity "
        "across distribution context segments."
    ),
    contradiction_sig="Effect polarity reverses across distribution segments.",
    cluster_role="Validates uniform treatability of issue family.",
    strategy_contrib=(
        "Low effect consistency forces strategy_class splitting into "
        "context-specific variants."
    ),
    collapse_fate="internalized",
    roles=(PointRole.PATTERN_BRIDGE, PointRole.ROTATION_PIVOT),
    crystal_order=CrystalOrder.COMPOSITE,
)


# ── Higher-Order Crystal Additional Points (Level 3) — 10 new points ─────────

POINT_ISSUE__STRATEGY_CLASS = RelationalPointLaw(
    name="issue__strategy_class",
    facet_a="issue",
    facet_b="strategy_class",
    description=(
        "What strategy usually fixes this problem?  This is the core strategic "
        "mapping.  Derived from the dominant issue__intervention pairs across "
        "the composite crystal's issue family, lifted to the abstract strategy "
        "level."
    ),
    evidence_sources=("composite crystal intervention frequency map",),
    scoring_method=(
        "Strategy assignment confidence = (base events resolved by strategy class) "
        "/ (total base events in issue family)."
    ),
    contradiction_sig=(
        "Multiple strategy classes with similar assignment confidence — "
        "issue family must be split before strategy assignment."
    ),
    cluster_role="Defines the issue-to-strategy mapping for this crystal.",
    strategy_contrib="This point IS the strategy assignment.",
    collapse_fate="promoted",
    roles=(PointRole.STRATEGY_LINKER, PointRole.ROTATION_PIVOT, PointRole.COLLAPSE_SEED),
    crystal_order=CrystalOrder.HIGHER_ORDER,
)

POINT_LOGIC_TIER__STRATEGY_CLASS = RelationalPointLaw(
    name="logic_tier__strategy_class",
    facet_a="logic_tier",
    facet_b="strategy_class",
    description=(
        "Which system layers accept that strategy?  Validates that the "
        "strategy class is structurally compatible with the tiers where "
        "the issue manifests."
    ),
    evidence_sources=("tier applicability matrix", "historical tier__intervention success"),
    scoring_method=(
        "Tier compatibility score = historical success rate of strategy "
        "class applied within this tier."
    ),
    contradiction_sig=(
        "Strategy class applied to an incompatible tier — "
        "produces automatic failure_mode entry."
    ),
    cluster_role="Tier-strategy compatibility validation.",
    strategy_contrib="Gates strategy class selection by tier.",
    collapse_fate="promoted",
    roles=(PointRole.STRATEGY_LINKER, PointRole.COLLAPSE_SEED),
    crystal_order=CrystalOrder.HIGHER_ORDER,
)

POINT_INTERVENTION__STRATEGY_CLASS = RelationalPointLaw(
    name="intervention__strategy_class",
    facet_a="intervention",
    facet_b="strategy_class",
    description=(
        "The mapping from specific intervention action to abstract strategy "
        "class.  Multiple interventions may map to the same strategy class.  "
        "This is the lifting step from concrete fix to reusable doctrine."
    ),
    evidence_sources=("intervention taxonomy", "strategy class definition table"),
    scoring_method=(
        "Mapping confidence = semantic fit of intervention within strategy "
        "class definition.  Manual assignment validated by historical success."
    ),
    contradiction_sig=(
        "Same intervention mapped to conflicting strategy classes in different "
        "events — taxonomy inconsistency."
    ),
    cluster_role="Validates that composite crystal's dominant intervention is strategy-class-coherent.",
    strategy_contrib="This is the grounding link between real actions and doctrine.",
    collapse_fate="promoted",
    roles=(PointRole.STRATEGY_LINKER, PointRole.COLLAPSE_SEED),
    crystal_order=CrystalOrder.HIGHER_ORDER,
)

POINT_STRATEGY_CLASS__OUTCOME_PROFILE = RelationalPointLaw(
    name="strategy_class__outcome_profile",
    facet_a="strategy_class",
    facet_b="strategy_outcome_profile",
    description=(
        "The statistical performance summary of the strategy class across all "
        "events in the genealogy.  This is the evidence that the strategy "
        "actually works — not just that it was applied."
    ),
    evidence_sources=("aggregated resolution_fidelity from base crystals",),
    scoring_method=(
        "resolution_rate, partial_rate, regression_rate, median_ttv — "
        "computed across all base events classified under this strategy."
    ),
    contradiction_sig=(
        "resolution_rate claimed high but base event resolution_fidelity "
        "scores contradict it — calculation error or stale profile."
    ),
    cluster_role="Validates strategy quality for promotion gating.",
    strategy_contrib="Primary quasicrystal promotion gate.",
    collapse_fate="promoted",
    roles=(PointRole.STRATEGY_LINKER, PointRole.COLLAPSE_SEED, PointRole.ROTATION_PIVOT),
    crystal_order=CrystalOrder.HIGHER_ORDER,
)

POINT_OUTCOME_PROFILE__OBSERVED_EFFECT = RelationalPointLaw(
    name="outcome_profile__observed_effect",
    facet_a="strategy_outcome_profile",
    facet_b="observed_effect",
    description=(
        "Grounds the outcome profile in actual base-crystal observed effects. "
        "This is the audit link that prevents the outcome profile from drifting "
        "from reality."
    ),
    evidence_sources=("observed_effect values across base crystal set",),
    scoring_method=(
        "Consistency score = correlation between outcome_profile resolution_rate "
        "and empirical observed_effect distribution."
    ),
    contradiction_sig="Outcome profile inconsistent with empirical observed_effect distribution.",
    cluster_role="Audit link for strategy quality.",
    strategy_contrib="Prevents strategy over-confidence.",
    collapse_fate="internalized",
    roles=(PointRole.DIAGNOSTIC_EDGE, PointRole.COLLAPSE_SEED),
    crystal_order=CrystalOrder.HIGHER_ORDER,
)

POINT_STRATEGY_CLASS__FAILURE_MODES = RelationalPointLaw(
    name="strategy_class__failure_modes",
    facet_a="strategy_class",
    facet_b="failure_modes",
    description=(
        "Under what conditions does this strategy fail?  This point collects "
        "all failure evidence from base events where the strategy was applied "
        "but did not produce resolution.  It is the anti-pattern library of "
        "the strategy."
    ),
    evidence_sources=("base events with observed_effect = no_change or regression",),
    scoring_method=(
        "Failure mode weight = frequency of this failure mode across base events "
        "using this strategy class."
    ),
    contradiction_sig=(
        "Failure mode listed but no base events support it — "
        "phantom entry must be removed."
    ),
    cluster_role="Identifies strategy failure contexts.",
    strategy_contrib="Directly feeds quasicrystal failure_indicators.",
    collapse_fate="promoted",
    roles=(PointRole.STRATEGY_LINKER, PointRole.ESCALATION_MARKER, PointRole.COLLAPSE_SEED),
    crystal_order=CrystalOrder.HIGHER_ORDER,
)

POINT_FAILURE_MODES__ISSUE = RelationalPointLaw(
    name="failure_modes__issue",
    facet_a="failure_modes",
    facet_b="issue",
    description=(
        "When this strategy fails, does it produce new issues?  This point "
        "records the downstream consequences of strategy failure — the "
        "regressions and cascades that result from applying the strategy "
        "outside its applicability conditions."
    ),
    evidence_sources=("regression events following failed strategy application",),
    scoring_method=(
        "Cascade severity = issue category of regression event weighted by "
        "observed_effect severity."
    ),
    contradiction_sig="Failure mode recorded with no downstream issue — incomplete failure record.",
    cluster_role="Maps strategy failure to new issue seeds.",
    strategy_contrib="Feeds escalation_trigger criteria.",
    collapse_fate="internalized",
    roles=(PointRole.ESCALATION_MARKER, PointRole.CAUSAL_ANCHOR),
    crystal_order=CrystalOrder.HIGHER_ORDER,
)

POINT_STRATEGY_CLASS__APPLICABILITY_CONDITIONS = RelationalPointLaw(
    name="strategy_class__applicability_conditions",
    facet_a="strategy_class",
    facet_b="applicability_conditions",
    description=(
        "The structural conditions under which this strategy is valid.  "
        "Derived from the target, logic_tier, and distribution_context values "
        "of successful base events classified under this strategy class."
    ),
    evidence_sources=("successful base event structural profiles",),
    scoring_method=(
        "Condition specificity score = how tightly the conditions bound the "
        "strategy application.  Over-broad = low; well-defined = high."
    ),
    contradiction_sig=(
        "Strategy applied outside conditions with success — conditions must "
        "be relaxed to capture new valid contexts."
    ),
    cluster_role="Defines where this strategy crystal is applicable.",
    strategy_contrib="Primary input to quasicrystal applicability_boundary.",
    collapse_fate="promoted",
    roles=(PointRole.STRATEGY_LINKER, PointRole.COLLAPSE_SEED),
    crystal_order=CrystalOrder.HIGHER_ORDER,
)

POINT_TARGET__APPLICABILITY_CONDITIONS = RelationalPointLaw(
    name="target__applicability_conditions",
    facet_a="target",
    facet_b="applicability_conditions",
    description=(
        "Target location compatibility with strategy applicability.  Validates "
        "that the targets seen in base events fall within the conditions' "
        "target constraints."
    ),
    evidence_sources=("target list from successful base events",),
    scoring_method=(
        "Target coverage score = fraction of strategy-successful events "
        "whose targets fall within applicability_conditions."
    ),
    contradiction_sig="Target in successful event but outside declared conditions — expand conditions.",
    cluster_role="Target validation for strategy scope.",
    strategy_contrib="Grounds applicability_conditions in real target data.",
    collapse_fate="internalized",
    roles=(PointRole.DIAGNOSTIC_EDGE,),
    crystal_order=CrystalOrder.HIGHER_ORDER,
)

POINT_LOGIC_TIER__APPLICABILITY_CONDITIONS = RelationalPointLaw(
    name="logic_tier__applicability_conditions",
    facet_a="logic_tier",
    facet_b="applicability_conditions",
    description=(
        "Logic tier compatibility with strategy applicability conditions.  "
        "Ensures the strategy is only recommended in tiers where it has "
        "demonstrated validity."
    ),
    evidence_sources=("tier distribution of successful base events",),
    scoring_method=(
        "Tier coverage score analogous to target coverage."
    ),
    contradiction_sig="Tier in successful event outside declared tier conditions — expand.",
    cluster_role="Tier validation for strategy scope.",
    strategy_contrib="Grounds applicability_conditions in real tier data.",
    collapse_fate="internalized",
    roles=(PointRole.DIAGNOSTIC_EDGE,),
    crystal_order=CrystalOrder.HIGHER_ORDER,
)


# ══════════════════════════════════════════════════════════════════════════════
# POINT REGISTRIES BY CRYSTAL ORDER
# ══════════════════════════════════════════════════════════════════════════════

BASE_POINTS: Dict[str, RelationalPointLaw] = {
    p.name: p for p in [
        POINT_TARGET__ISSUE,
        POINT_ISSUE__LOGIC_TIER,
        POINT_LOGIC_TIER__INTERVENTION,
        POINT_INTERVENTION__INTENDED_EFFECT,
        POINT_INTENDED_EFFECT__OBSERVED_EFFECT,
        POINT_OBSERVED_EFFECT__ISSUE,
        POINT_TARGET__LOGIC_TIER,
        POINT_TARGET__INTERVENTION,
        POINT_ISSUE__INTERVENTION,
        POINT_ISSUE__INTENDED_EFFECT,
        POINT_LOGIC_TIER__OBSERVED_EFFECT,
        POINT_TARGET__OBSERVED_EFFECT,
    ]
}

COMPOSITE_POINTS: Dict[str, RelationalPointLaw] = {
    **BASE_POINTS,
    **{p.name: p for p in [
        POINT_ISSUE__RECURRENCE_PATTERN,
        POINT_TARGET__RECURRENCE_PATTERN,
        POINT_LOGIC_TIER__RECURRENCE_PATTERN,
        POINT_INTERVENTION__RECURRENCE_PATTERN,
        POINT_TARGET__DISTRIBUTION_CONTEXT,
        POINT_ISSUE__DISTRIBUTION_CONTEXT,
        POINT_LOGIC_TIER__DISTRIBUTION_CONTEXT,
        POINT_OBSERVED_EFFECT__DISTRIBUTION_CONTEXT,
    ]},
}

HIGHER_ORDER_POINTS: Dict[str, RelationalPointLaw] = {
    **COMPOSITE_POINTS,
    **{p.name: p for p in [
        POINT_ISSUE__STRATEGY_CLASS,
        POINT_LOGIC_TIER__STRATEGY_CLASS,
        POINT_INTERVENTION__STRATEGY_CLASS,
        POINT_STRATEGY_CLASS__OUTCOME_PROFILE,
        POINT_OUTCOME_PROFILE__OBSERVED_EFFECT,
        POINT_STRATEGY_CLASS__FAILURE_MODES,
        POINT_FAILURE_MODES__ISSUE,
        POINT_STRATEGY_CLASS__APPLICABILITY_CONDITIONS,
        POINT_TARGET__APPLICABILITY_CONDITIONS,
        POINT_LOGIC_TIER__APPLICABILITY_CONDITIONS,
    ]},
}

POINTS_BY_ORDER: Dict[CrystalOrder, Dict[str, RelationalPointLaw]] = {
    CrystalOrder.BASE         : BASE_POINTS,
    CrystalOrder.COMPOSITE    : COMPOSITE_POINTS,
    CrystalOrder.HIGHER_ORDER : HIGHER_ORDER_POINTS,
    CrystalOrder.QUASI        : HIGHER_ORDER_POINTS,  # quasi inner strata uses full map
}


# ══════════════════════════════════════════════════════════════════════════════
# QUASICRYSTAL INNER STRATA DEFINITION
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class QuasiInnerStrata:
    """
    Represents the collapsed genealogy inside a quasicrystal.
    Not a live crystal — a compressed record of ancestry.

    Fields
    ------
    representative_base_events : List of (crystal_id, key_field_snapshot) for
                                 the most diagnostically significant base events.
    recurrence_summary         : Distilled recurrence_pattern and distribution
                                 context from the composite ancestry.
    strategy_success_stats     : Per-strategy-class outcome profile scores from
                                 higher-order ancestry.
    failure_counterexamples    : Base events where the strategy failed — kept as
                                 evidence for failure_indicators.
    coherence_index            : Structural consistency across the collapsed
                                 genealogy, inspired by L3 quasicrystal
                                 coherence scoring.
    novelty_index              : How structurally diverse the contributing
                                 genealogy is, used for hypothesis rotation.
    genealogy_depth            : Total count of base events that contributed.
    formation_timestamp        : When this quasicrystal was collapsed.
    """
    representative_base_events : List[Dict[str, Any]]  = field(default_factory=list)
    recurrence_summary         : Dict[str, Any]         = field(default_factory=dict)
    strategy_success_stats     : Dict[str, float]       = field(default_factory=dict)
    failure_counterexamples    : List[Dict[str, Any]]  = field(default_factory=list)
    coherence_index            : float                  = 0.0
    novelty_index              : float                  = 0.0
    genealogy_depth            : int                    = 0
    formation_timestamp        : str                    = ""


# ══════════════════════════════════════════════════════════════════════════════
# ROTATION DEFINITIONS
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RotationDefinition:
    """
    Defines a named rotation perspective for quasicrystal re-analysis.

    A rotation re-weights the facet–point relationship graph to surface
    new hypotheses.  The pivot is a PointRole that acts as the rotation axis.
    The reweight_targets are the facets whose relation scores are recalculated
    relative to the pivot.
    """
    name             : str
    description      : str
    pivot_role       : PointRole
    reweight_targets : Tuple[str, ...]   # facet names
    hypothesis_type  : str


ROTATION_ISSUE_CENTRIC = RotationDefinition(
    name="issue_centric",
    description=(
        "Re-weight all intervention outcome records relative to the issue "
        "family axis.  Surfaces: which interventions work best for this issue "
        "regardless of target or tier."
    ),
    pivot_role=PointRole.CAUSAL_ANCHOR,
    reweight_targets=("intervention", "observed_effect", "intended_effect"),
    hypothesis_type="intervention_optimality_for_issue",
)

ROTATION_LOGIC_TIER = RotationDefinition(
    name="logic_tier",
    description=(
        "Examine fix effectiveness across structural layers.  Surfaces: which "
        "tiers are most receptive to a given strategy class."
    ),
    pivot_role=PointRole.DIAGNOSTIC_EDGE,
    reweight_targets=("logic_tier", "strategy_class", "applicability_conditions"),
    hypothesis_type="tier_strategy_compatibility",
)

ROTATION_STRATEGY = RotationDefinition(
    name="strategy",
    description=(
        "Compare strategies that share intervention classes.  Surfaces: whether "
        "two ostensibly different strategies are actually equivalent under "
        "different conditions."
    ),
    pivot_role=PointRole.STRATEGY_LINKER,
    reweight_targets=("strategy_class", "intervention", "failure_modes"),
    hypothesis_type="strategy_equivalence_or_differentiation",
)

ROTATION_OUTCOME = RotationDefinition(
    name="outcome",
    description=(
        "Identify strategies that produce similar observed effects via "
        "different mechanisms.  Surfaces: alternative routes to the same "
        "resolution shape."
    ),
    pivot_role=PointRole.ROTATION_PIVOT,
    reweight_targets=("observed_effect", "intended_effect", "strategy_class"),
    hypothesis_type="effect_convergence_via_different_strategies",
)

ALL_ROTATIONS: Dict[str, RotationDefinition] = {
    r.name: r for r in [
        ROTATION_ISSUE_CENTRIC,
        ROTATION_LOGIC_TIER,
        ROTATION_STRATEGY,
        ROTATION_OUTCOME,
    ]
}


# ══════════════════════════════════════════════════════════════════════════════
# PROMOTION CRITERIA SCHEMA
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PromotionCriteria:
    """
    Defines the quantitative gates for promoting a crystal to the next order.

    All thresholds must be satisfied for promotion.  Any single violation
    blocks promotion and returns a reason string to the lifecycle engine.
    """
    from_order                  : CrystalOrder
    to_order                    : CrystalOrder
    min_base_event_count        : int     = 1
    min_resolution_fidelity_avg : float   = 0.6
    min_recurrence_strength     : float   = 0.0   # only applies from BASE→COMPOSITE
    min_strategy_confidence     : float   = 0.0   # only applies from COMPOSITE→HIGHER
    min_outcome_profile_score   : float   = 0.0   # only applies from HIGHER→QUASI
    max_failure_mode_density    : float   = 1.0   # ratio: failure modes per base event
    require_stable_strategy     : bool    = False  # True requires single dominant strategy


BASE_TO_COMPOSITE_CRITERIA = PromotionCriteria(
    from_order               = CrystalOrder.BASE,
    to_order                 = CrystalOrder.COMPOSITE,
    min_base_event_count     = 3,
    min_resolution_fidelity_avg = 0.0,   # any fidelity — recurrence is the gate
    min_recurrence_strength  = 0.3,
)

COMPOSITE_TO_HIGHER_CRITERIA = PromotionCriteria(
    from_order               = CrystalOrder.COMPOSITE,
    to_order                 = CrystalOrder.HIGHER_ORDER,
    min_base_event_count     = 5,
    min_resolution_fidelity_avg = 0.5,
    min_strategy_confidence  = 0.6,
    max_failure_mode_density = 0.5,
)

HIGHER_TO_QUASI_CRITERIA = PromotionCriteria(
    from_order               = CrystalOrder.HIGHER_ORDER,
    to_order                 = CrystalOrder.QUASI,
    min_base_event_count     = 8,
    min_resolution_fidelity_avg = 0.7,
    min_outcome_profile_score   = 0.65,
    max_failure_mode_density    = 0.3,
    require_stable_strategy     = True,
)

PROMOTION_CRITERIA: Dict[Tuple[CrystalOrder, CrystalOrder], PromotionCriteria] = {
    (CrystalOrder.BASE,         CrystalOrder.COMPOSITE    ) : BASE_TO_COMPOSITE_CRITERIA,
    (CrystalOrder.COMPOSITE,    CrystalOrder.HIGHER_ORDER  ) : COMPOSITE_TO_HIGHER_CRITERIA,
    (CrystalOrder.HIGHER_ORDER, CrystalOrder.QUASI         ) : HIGHER_TO_QUASI_CRITERIA,
}


# ══════════════════════════════════════════════════════════════════════════════
# ENGINE API
# ══════════════════════════════════════════════════════════════════════════════

class CrystalEngine:
    """
    Public interface to the semantic crystal law layer.

    This class does not instantiate or store crystals — that is the job of
    dimensional_processing (lifecycle) and dimensional_memory (persistence).
    It provides:
      - facet validation
      - point validity checking
      - promotion criteria lookup
      - rotation definition lookup
      - facet survival rule lookup
    """

    # ── Facet access ──────────────────────────────────────────────────────────

    @staticmethod
    def get_facet(order: CrystalOrder, facet_name: str) -> Optional[FacetLaw]:
        """Return the FacetLaw for a named facet at the given crystal order."""
        return FACETS_BY_ORDER.get(order, {}).get(facet_name)

    @staticmethod
    def get_all_facets(order: CrystalOrder) -> Dict[str, FacetLaw]:
        """Return all FacetLaw objects valid at the given crystal order."""
        return dict(FACETS_BY_ORDER.get(order, {}))

    @staticmethod
    def facets_added_at(order: CrystalOrder) -> Dict[str, FacetLaw]:
        """Return only the facets introduced at this specific crystal order."""
        if order == CrystalOrder.BASE:
            return dict(BASE_FACETS)
        prev_orders = [o for o in CrystalOrder if o.value < order.value]
        prev_facets: Set[str] = set()
        for po in prev_orders:
            prev_facets.update(FACETS_BY_ORDER.get(po, {}).keys())
        return {k: v for k, v in FACETS_BY_ORDER[order].items() if k not in prev_facets}

    # ── Point access ──────────────────────────────────────────────────────────

    @staticmethod
    def get_point(order: CrystalOrder, point_name: str) -> Optional[RelationalPointLaw]:
        """Return the RelationalPointLaw for a named point at the given order."""
        return POINTS_BY_ORDER.get(order, {}).get(point_name)

    @staticmethod
    def get_all_points(order: CrystalOrder) -> Dict[str, RelationalPointLaw]:
        """Return all RelationalPointLaw objects valid at the given order."""
        return dict(POINTS_BY_ORDER.get(order, {}))

    @staticmethod
    def points_added_at(order: CrystalOrder) -> Dict[str, RelationalPointLaw]:
        """Return only the points introduced at this specific crystal order."""
        if order == CrystalOrder.BASE:
            return dict(BASE_POINTS)
        prev_orders = [o for o in CrystalOrder if o.value < order.value]
        prev_points: Set[str] = set()
        for po in prev_orders:
            prev_points.update(POINTS_BY_ORDER.get(po, {}).keys())
        return {k: v for k, v in POINTS_BY_ORDER[order].items() if k not in prev_points}

    # ── Validation ────────────────────────────────────────────────────────────

    @staticmethod
    def validate_facet_value(
        order: CrystalOrder,
        facet_name: str,
        value: Any,
    ) -> Tuple[bool, str]:
        """
        Validate that a value is plausible for the given facet at the given order.
        Returns (is_valid, reason).  This is advisory — the engine does not
        enforce types rigidly but flags structural violations.
        """
        law = CrystalEngine.get_facet(order, facet_name)
        if law is None:
            return False, f"Facet '{facet_name}' is not valid at order {order.name}."
        if value is None or value == "":
            return False, f"Facet '{facet_name}' received empty value."
        if ValueDomain.SCORE in law.value_domains:
            try:
                s = float(value)
                if not (0.0 <= s <= 1.0):
                    return False, f"Score facet '{facet_name}' value {s} out of [0,1]."
            except (TypeError, ValueError):
                return False, f"Score facet '{facet_name}' received non-numeric value."
        return True, "ok"

    @staticmethod
    def validate_point(
        order: CrystalOrder,
        facet_a: str,
        facet_b: str,
    ) -> Tuple[bool, str]:
        """
        Verify that facet_a and facet_b are permitted to form a relational
        point at the given order, and that each facet lists the other as
        an allowed partner.
        """
        point_name = f"{facet_a}__{facet_b}"
        alt_name   = f"{facet_b}__{facet_a}"
        points     = POINTS_BY_ORDER.get(order, {})
        if point_name not in points and alt_name not in points:
            return False, (
                f"No relational point '{point_name}' or '{alt_name}' "
                f"defined at order {order.name}."
            )
        law_a = CrystalEngine.get_facet(order, facet_a)
        if law_a and facet_b not in law_a.allowed_partners:
            return False, (
                f"Facet '{facet_a}' does not list '{facet_b}' as an "
                f"allowed partner."
            )
        return True, "ok"

    # ── Survival ──────────────────────────────────────────────────────────────

    @staticmethod
    def survival_rule(facet_name: str, target_order: CrystalOrder) -> Optional[str]:
        """
        Return the survival rule for a facet at the target crystal order.
        Rules: "carry_forward" | "fold_inward" | "aggregate" | "supersede" | "expand"
        Returns None if the facet is not defined or has no rule for that order.
        """
        for facet_registry in FACETS_BY_ORDER.values():
            if facet_name in facet_registry:
                return facet_registry[facet_name].survival_rules.get(target_order)
        return None

    # ── Promotion criteria ────────────────────────────────────────────────────

    @staticmethod
    def get_promotion_criteria(
        from_order: CrystalOrder,
        to_order: CrystalOrder,
    ) -> Optional[PromotionCriteria]:
        """Return the PromotionCriteria for the given transition, or None."""
        return PROMOTION_CRITERIA.get((from_order, to_order))

    # ── Rotation ──────────────────────────────────────────────────────────────

    @staticmethod
    def get_rotation(name: str) -> Optional[RotationDefinition]:
        """Return a named RotationDefinition, or None."""
        return ALL_ROTATIONS.get(name)

    @staticmethod
    def all_rotations() -> Dict[str, RotationDefinition]:
        """Return all registered rotation definitions."""
        return dict(ALL_ROTATIONS)

    # ── Schema summary ────────────────────────────────────────────────────────

    @staticmethod
    def schema_summary() -> Dict[str, Any]:
        """Return a concise summary of the full crystal schema."""
        return {
            order.name: {
                "facet_count" : len(FACETS_BY_ORDER.get(order, {})),
                "point_count" : len(POINTS_BY_ORDER.get(order, {})),
                "facets"      : list(FACETS_BY_ORDER.get(order, {}).keys()),
                "points"      : list(POINTS_BY_ORDER.get(order, {}).keys()),
            }
            for order in CrystalOrder
        }


# ══════════════════════════════════════════════════════════════════════════════
# MAIN — schema integrity self-check
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json

    engine = CrystalEngine()
    summary = engine.schema_summary()

    print("Crystal Engine v3 — Schema Summary")
    print("=" * 60)
    for order_name, data in summary.items():
        print(f"\n  {order_name}")
        print(f"    Facets : {data['facet_count']}")
        print(f"    Points : {data['point_count']}")

    print("\n" + "=" * 60)
    print("Promotion Criteria")
    for (f, t), crit in PROMOTION_CRITERIA.items():
        print(f"\n  {f.name} → {t.name}")
        print(f"    min_base_events         : {crit.min_base_event_count}")
        print(f"    min_resolution_fidelity : {crit.min_resolution_fidelity_avg}")
        print(f"    min_strategy_confidence : {crit.min_strategy_confidence}")
        print(f"    min_outcome_profile     : {crit.min_outcome_profile_score}")
        print(f"    max_failure_mode_density: {crit.max_failure_mode_density}")

    print("\n" + "=" * 60)
    print("Rotation Perspectives")
    for name, rot in ALL_ROTATIONS.items():
        print(f"\n  {name}")
        print(f"    Pivot role       : {rot.pivot_role.name}")
        print(f"    Hypothesis type  : {rot.hypothesis_type}")
        print(f"    Reweight targets : {rot.reweight_targets}")

    print("\n" + "=" * 60)
    print("Facet Partner Validation — Base Crystal")
    for fname, flaw in BASE_FACETS.items():
        for partner in flaw.allowed_partners:
            ok, reason = engine.validate_point(CrystalOrder.BASE, fname, partner)
            status = "✓" if ok else f"✗ {reason}"
            print(f"  {fname} ↔ {partner} : {status}")

    print("\nEngine self-check complete.")
