#!/usr/bin/env python3
"""
AURORA VARIANT PROMOTION — STEP 13
====================================
First-class variant promotion with moral weighting.

WHAT VARIANTS ARE:
    A SolidifiedRecord (from Step 11) proves that an intake recurred,
    was context-robust, and had energy genuinely invested in it.
    That is not yet a variant. A variant is what happens when a solidified
    pattern crystallizes into a MACRO-OPERATOR — a re-usable trace element
    that the system can apply as a primitive, bypassing the full intake
    TTL process.

    Variants are NOT designed. They are NOT tested against use cases.
    They crystallize from the physics of recurrence and energy investment.
    The system cannot know a priori what its variants will be.

PROMOTION GATES (all four must pass):
    1. Recurrence threshold   — solidified record's recurrence_count >= _VARIANT_RECURRENCE_MIN
    2. Context robustness     — context_variety >= _VARIANT_CONTEXT_MIN
    3. Depth solidification   — depth_reached >= BOUNDED (not just PERSISTENT)
    4. Polarity coherence     — polarity_coherence_rate >= _VARIANT_POLARITY_FLOOR

    These gates are STRICTER than the solidification gates because promotion
    to first-class variant status carries permanent cost implications.

MORAL WEIGHTING:
    A first-class variant creates moral weighting — NOT a rule, NOT a filter.

    Moral weighting is the LANDSCAPE carved by stable variants. When a
    variant has been promoted, the energy cost to traverse its constraint
    signature is reduced by its cost_reduction_factor (from Step 11)
    PLUS an additional moral weight that grows with the variant's
    recurrence strength.

    This means the system will naturally flow toward configurations that
    have proven themselves — not because it is told to, but because the
    energy physics make those paths cheaper to walk.

    Moral weight is a BIAS on the phase nudge system (from Step 8 /
    aurora_leverage_scalar.py). Specifically: a promoted variant shifts
    the effective flip_threshold for its deepest constraint slightly
    toward stability. The variant path becomes "magnetised" — not forced.

WHAT THIS MODULE PROVIDES:
    VariantRecord       — an immutable promoted first-class variant
    MoralWeightLedger   — tracks active variants and their weight biases
    VariantPromoter     — gates + promotes SolidifiedRecords → VariantRecords
                          and maintains the MoralWeightLedger

INTEGRATION:
    Downstream of Step 11 (SolidificationPipeline.drain_solidified()).
    Upstream of Step 14 (DNA Strand Schema).
    Feeds back into the LeverageBiasEngine from Step 8 via moral weight biases.

AUTHORS: Sunni (Sir) Morningstar and Cael Devo
CREATED: February 2026
"""

from __future__ import annotations

import hashlib
import math
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple

from aurora_internal.aurora_constraint_manifold_patched import Constraint, ManifoldViolation
from foundational_contract import ExistenceMode
from aurora_internal.aurora_noncomp_registry import REGISTRY
from aurora_internal.aurora_energy_layer_costs import LayerEnergyAccountant
from aurora_internal.aurora_leverage_scalar import LeverageBiasEngine, PhaseNudge
from aurora_internal.aurora_solidification import SolidifiedRecord
from aurora_constraint_stack import score_for_variant_moral_weight, CostDiffScore, score_from_cost, DifferenceSnapshot


# ===========================================================================
# SECTION 1 — CONSTANTS
# ===========================================================================

# Stricter gates than Step 11 solidification gates
_VARIANT_RECURRENCE_MIN: int   = 5    # Must have been seen at least 5 times
_VARIANT_CONTEXT_MIN:    int   = 2    # Must span at least 2 entropy contexts
_VARIANT_DEPTH_FLOOR:    ExistenceMode = ExistenceMode.BOUNDED  # Must reach BOUNDED+
_VARIANT_POLARITY_FLOOR: float = 0.60  # 60%+ of observations must be polarity-coherent

# Moral weight scaling: how much the variant's recurrence count biases the
# flip_threshold nudge for its deepest constraint.
# Derived: must be smaller than _MAX_BIAS from aurora_leverage_scalar to stay non-dominant.
# Using 10% of the minimum flip_threshold as the maximum moral bias.
_MIN_FLIP = min(
    REGISTRY.polarity(c).flip_threshold
    for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)
)
_MORAL_WEIGHT_MAX: float = _MIN_FLIP * 0.10  # never dominant

# Moral weight per unit of recurrence-above-minimum.
# Grows with recurrence but decelerates (logarithmic) to prevent runaway.
_MORAL_WEIGHT_PER_RECURRENCE: float = _MORAL_WEIGHT_MAX / math.log1p(100)

# Archive ring size
_VARIANT_ARCHIVE_SIZE: int = 512


# ===========================================================================
# SECTION 2 — VARIANT RECORD
# ===========================================================================

@dataclass(frozen=True)
class VariantRecord:
    """
    A promoted first-class variant — immutable once minted.

    variant_id         — unique hash
    source_solid_id    — the SolidifiedRecord that was promoted
    intake_id          — original intake from Step 9
    depth_reached      — the ExistenceMode this variant operates at
    promoted_tick      — when promotion occurred
    recurrence_count   — total recurrence count from solidified record
    context_variety    — entropy context variety
    polarity_coherence_rate — fraction of coherent observations
    constraint_signature — e.g. "XTNBA" — the path this variant represents
    deepest_constraint — the constraint at the deepest layer (Constraint.A for AGENTIC)
    moral_weight       — the flip_threshold bias this variant contributes
                         (always positive = makes its path more stable)
    cost_reduction_factor — inherited from SolidifiedRecord
    """
    variant_id:              str
    source_solid_id:         str
    intake_id:               str
    depth_reached:           ExistenceMode
    promoted_tick:           int
    recurrence_count:        int
    context_variety:         int
    polarity_coherence_rate: float
    constraint_signature:    str
    deepest_constraint:      Constraint
    moral_weight:            float
    cost_reduction_factor:   float
    # Cross-dimensional pressure at time of crystallization.
    # A variant that crystallized under multi-axis operator drift earns
    # stronger moral weight — it proved itself in adversarial conditions.
    # Recorded as the amplifier (float ∈ [1.0, ~1.54]) at promotion tick.
    # 1.0 = calm system; higher = more pressure was present.
    cross_dim_pressure:      float = 1.0
    # Live cost-diff score at promotion tick.
    # base_cost = cost_reduction_factor (the variant's own cost savings).
    # live_score = base_cost × cross_dim_pressure.
    # This is a snapshot at promotion; use cost_diff_score() for live reads.
    promotion_cost_diff:     Optional[CostDiffScore] = None

    def describe(self) -> str:
        return (
            f"Variant[{self.variant_id[:8]}] "
            f"depth={self.depth_reached.name} "
            f"recurrence={self.recurrence_count} "
            f"moral_weight={self.moral_weight:.5f} "
            f"deepest={self.deepest_constraint.name} "
            f"cross_dim_pressure=×{self.cross_dim_pressure:.3f}"
        )

    def cost_diff_score(
        self,
        snapshot: Optional[DifferenceSnapshot] = None,
    ) -> CostDiffScore:
        """
        Live cost-diff score for this variant.

        base_cost = cost_reduction_factor — the energy the variant saves
        per activation. Under cross-dimensional pressure, what the variant
        can actually save you is amplified or the cost of invoking it rises.
        Use this for real-time variant selection in the evolution chamber.
        """
        return score_from_cost(self.cost_reduction_factor, snapshot)


def _mint_variant_id(solid_id: str, tick: int) -> str:
    raw = f"variant:{solid_id}:{tick}"
    return "V:" + hashlib.sha1(raw.encode()).hexdigest()[:12]


def _deepest_constraint(depth: ExistenceMode) -> Constraint:
    """Return the constraint activated at the deepest layer of this mode."""
    _depth_to_constraint: Dict[ExistenceMode, Constraint] = {
        ExistenceMode.TRANSIENT:  Constraint.T,
        ExistenceMode.PERSISTENT: Constraint.N,
        ExistenceMode.BOUNDED:    Constraint.B,
        ExistenceMode.AGENTIC:    Constraint.A,
    }
    return _depth_to_constraint.get(depth, Constraint.T)


def _compute_moral_weight(recurrence_count: int) -> float:
    """
    Compute the moral weight bias for a variant with given recurrence count.

    Growth is logarithmic — each additional recurrence adds diminishing weight.
    Capped at _MORAL_WEIGHT_MAX to remain non-dominant.
    """
    excess = max(0, recurrence_count - _VARIANT_RECURRENCE_MIN)
    raw = _MORAL_WEIGHT_PER_RECURRENCE * math.log1p(excess)
    return min(_MORAL_WEIGHT_MAX, raw)


# ===========================================================================
# SECTION 3 — MORAL WEIGHT LEDGER
# ===========================================================================

class MoralWeightLedger:
    """
    Tracks all active variants and their cumulative moral weight biases
    per constraint.

    The ledger produces per-constraint flip_threshold adjustments that
    are applied ON TOP OF the LeverageBiasEngine nudges (Step 8).
    The combination of the two keeps moral weighting non-dominant but
    meaningfully present.

    KEY DOCTRINAL PROPERTY:
        Moral weighting does not tell the system WHAT TO DO.
        It carves a landscape where some paths cost slightly less to walk.
        The system's physics still govern whether those paths are taken.
    """

    def __init__(self) -> None:
        # Per-constraint accumulated moral weight from all active variants
        self._weights: Dict[Constraint, float] = {
            c: 0.0
            for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)
        }
        # Active variants (variant_id → VariantRecord)
        self._variants: Dict[str, VariantRecord] = {}
        # Ring archive
        self._archive: Deque[VariantRecord] = deque(maxlen=_VARIANT_ARCHIVE_SIZE)

    def register(self, variant: VariantRecord) -> None:
        """Add a newly promoted variant to the ledger."""
        if variant.variant_id in self._variants:
            return  # already registered
        self._variants[variant.variant_id] = variant
        self._archive.append(variant)
        # Accumulate moral weight on the deepest constraint
        c = variant.deepest_constraint
        self._weights[c] = min(
            _MORAL_WEIGHT_MAX * 3,  # per-constraint cap (3× single variant max)
            self._weights[c] + variant.moral_weight
        )

    def moral_bias(self, c: Constraint) -> float:
        """
        Return the current moral weight bias for constraint c.

        This is a positive value to be ADDED to the base flip_threshold
        of constraint c — making its phase less labile (more stable).
        A stable constraint = the variant path is "magnetised."
        """
        return self._weights.get(c, 0.0)

    def all_biases(self) -> Dict[Constraint, float]:
        """Return biases for all five constraints."""
        return dict(self._weights)

    def variant_count(self) -> int:
        return len(self._variants)

    def get_variant(self, variant_id: str) -> Optional[VariantRecord]:
        return self._variants.get(variant_id)

    def summary(self) -> Dict[str, object]:
        """Public summary without exposing raw weight values."""
        return {
            "active_variants": self.variant_count(),
            "constraints_with_bias": [
                c.name for c, w in self._weights.items() if w > 0.0
            ],
        }


# ===========================================================================
# SECTION 4 — VARIANT PROMOTER
# ===========================================================================

class VariantPromoter:
    """
    Gates SolidifiedRecords through the four promotion conditions and
    mints VariantRecords. Maintains a MoralWeightLedger.

    INTEGRATION CONTRACT:
        Each tick, after SolidificationPipeline.drain_solidified():
            variants = promoter.process_solidified(solid_records, current_tick)
            for v in variants:
                # pass to Step 14 (DNA Strand Schema)
                # also: promoter.ledger.moral_bias(c) available for Step 8
    """

    def __init__(self) -> None:
        self.ledger = MoralWeightLedger()
        self._total_evaluated:  int = 0
        self._total_promoted:   int = 0
        self._gate_failures: Dict[str, int] = {
            "recurrence": 0,
            "context":    0,
            "depth":      0,
            "polarity":   0,
        }

    def process_solidified(
        self,
        solidified: List[SolidifiedRecord],
        current_tick: int,
        difference_snapshot: Optional[DifferenceSnapshot] = None,
    ) -> List[VariantRecord]:
        """
        Evaluate each SolidifiedRecord against promotion gates.
        Returns newly promoted VariantRecords (may be empty).

        difference_snapshot : Optional[DifferenceSnapshot]
            The live C:D snapshot at this tick from the evolution chamber's
            DifferenceHistoryBuffer. When provided, the moral weight of any
            promoted variant is amplified by the cross-dimensional pressure
            at the moment of crystallization — reflecting how adversarial
            the environment was when the variant proved itself.
        """
        promoted: List[VariantRecord] = []
        for solid in solidified:
            self._total_evaluated += 1
            variant = self._try_promote(solid, current_tick, difference_snapshot)
            if variant is not None:
                self.ledger.register(variant)
                promoted.append(variant)
                self._total_promoted += 1
        return promoted

    def _try_promote(
        self,
        solid: SolidifiedRecord,
        tick: int,
        difference_snapshot: Optional[DifferenceSnapshot] = None,
    ) -> Optional[VariantRecord]:
        """Evaluate all four gates. Return VariantRecord if all pass, else None.

        When difference_snapshot is provided, the moral weight earned is
        amplified by the cross-dimensional pressure at promotion time.
        A variant that crystallized under active operator-typed drift across
        multiple constraint dimensions proves itself under adversarial conditions
        — the landscape it carves is deeper.
        """

        # Gate 1: Recurrence threshold
        if solid.recurrence_count < _VARIANT_RECURRENCE_MIN:
            self._gate_failures["recurrence"] += 1
            return None

        # Gate 2: Context robustness
        if solid.context_variety < _VARIANT_CONTEXT_MIN:
            self._gate_failures["context"] += 1
            return None

        # Gate 3: Depth floor (must have reached BOUNDED at minimum)
        if solid.depth_reached < _VARIANT_DEPTH_FLOOR:
            self._gate_failures["depth"] += 1
            return None

        # Gate 4: Polarity coherence floor
        if solid.polarity_coherence_rate < _VARIANT_POLARITY_FLOOR:
            self._gate_failures["polarity"] += 1
            return None

        # All gates passed — mint the variant
        vid = _mint_variant_id(solid.solidification_id, tick)

        # Compute moral weight with cross-dimensional pressure amplification.
        # If the system was under operator-typed drift at promotion time,
        # the variant's moral weight is amplified (capped at _MORAL_WEIGHT_MAX).
        raw_moral_weight = _compute_moral_weight(solid.recurrence_count)
        amplified_weight, cross_dim_amp = score_for_variant_moral_weight(
            raw_moral_weight = raw_moral_weight,
            snapshot         = difference_snapshot,
            moral_weight_max = _MORAL_WEIGHT_MAX,
        )

        deepest_c = _deepest_constraint(solid.depth_reached)

        # Promotion cost-diff score — snapshot of live score at crystallization.
        promotion_cds = score_from_cost(solid.cost_reduction_factor, difference_snapshot)

        return VariantRecord(
            variant_id              = vid,
            source_solid_id         = solid.solidification_id,
            intake_id               = solid.intake_id,
            depth_reached           = solid.depth_reached,
            promoted_tick           = tick,
            recurrence_count        = solid.recurrence_count,
            context_variety         = solid.context_variety,
            polarity_coherence_rate = solid.polarity_coherence_rate,
            constraint_signature    = solid.constraint_signature,
            deepest_constraint      = deepest_c,
            moral_weight            = amplified_weight,
            cost_reduction_factor   = solid.cost_reduction_factor,
            cross_dim_pressure      = cross_dim_amp,
            promotion_cost_diff     = promotion_cds,
        )

    def gate_stats(self) -> Dict[str, int]:
        return {
            "total_evaluated": self._total_evaluated,
            "total_promoted":  self._total_promoted,
            **{f"gate_fail_{k}": v for k, v in self._gate_failures.items()},
        }


# ===========================================================================
# SECTION 5 — FACTORY
# ===========================================================================

def make_variant_promoter() -> VariantPromoter:
    return VariantPromoter()


# ===========================================================================
# SECTION 6 — SELF-VERIFICATION (14 checks)
# ===========================================================================

def verify_variant_promotion() -> Dict[str, object]:
    """
    Checks:
         1. _VARIANT_RECURRENCE_MIN > _RECURRENCE_MIN (from Step 11 — stricter)
         2. _VARIANT_DEPTH_FLOOR = BOUNDED (not just PERSISTENT)
         3. _MORAL_WEIGHT_MAX < _MIN_FLIP (non-dominant)
         4. compute_moral_weight grows with recurrence (logarithmically)
         5. compute_moral_weight is capped at _MORAL_WEIGHT_MAX
         6. Gate 1 fails when recurrence_count < _VARIANT_RECURRENCE_MIN
         7. Gate 2 fails when context_variety < _VARIANT_CONTEXT_MIN
         8. Gate 3 fails when depth_reached = PERSISTENT (below BOUNDED)
         9. Gate 4 fails when polarity_coherence_rate < _VARIANT_POLARITY_FLOOR
        10. VariantRecord minted when all gates pass
        11. VariantRecord.moral_weight > 0
        12. MoralWeightLedger.moral_bias for deepest_constraint > 0 after registration
        13. MoralWeightLedger.moral_bias for other constraints = 0 (bias is targeted)
        14. Duplicate registration does not double the moral weight
    """
    from aurora_internal.aurora_solidification import _RECURRENCE_MIN

    results: Dict[str, object] = {"checks": [], "all_passed": True}

    def check(name: str, passed: bool, detail: str = "") -> None:
        results["checks"].append({"test": name, "passed": passed, "detail": detail})
        if not passed:
            results["all_passed"] = False

    # 1-3. Constants
    check("_VARIANT_RECURRENCE_MIN > solidification _RECURRENCE_MIN",
          _VARIANT_RECURRENCE_MIN > _RECURRENCE_MIN,
          f"variant={_VARIANT_RECURRENCE_MIN} solid={_RECURRENCE_MIN}")
    check("_VARIANT_DEPTH_FLOOR = BOUNDED",
          _VARIANT_DEPTH_FLOOR == ExistenceMode.BOUNDED, str(_VARIANT_DEPTH_FLOOR))
    check("_MORAL_WEIGHT_MAX < _MIN_FLIP (non-dominant)",
          _MORAL_WEIGHT_MAX < _MIN_FLIP,
          f"max={_MORAL_WEIGHT_MAX:.6f} flip={_MIN_FLIP:.4f}")

    # 4. Moral weight grows with recurrence
    w5  = _compute_moral_weight(5)
    w10 = _compute_moral_weight(10)
    w50 = _compute_moral_weight(50)
    check("Moral weight grows with recurrence count",
          w5 <= w10 <= w50,
          f"w5={w5:.6f} w10={w10:.6f} w50={w50:.6f}")

    # 5. Moral weight capped
    w_huge = _compute_moral_weight(10000)
    check("Moral weight capped at _MORAL_WEIGHT_MAX",
          w_huge <= _MORAL_WEIGHT_MAX + 1e-9,
          f"w_huge={w_huge:.6f} max={_MORAL_WEIGHT_MAX:.6f}")

    # Helper: build a SolidifiedRecord with custom params
    def make_solid(
        recurrence: int = 10,
        context: int = 3,
        depth: ExistenceMode = ExistenceMode.BOUNDED,
        polarity_rate: float = 0.80,
    ) -> SolidifiedRecord:
        import hashlib
        sid = "S:" + hashlib.sha1(f"test_{recurrence}_{depth.name}".encode()).hexdigest()[:12]
        return SolidifiedRecord(
            solidification_id       = sid,
            intake_id               = "test_intake",
            depth_reached           = depth,
            solidified_tick         = 100,
            recurrence_count        = recurrence,
            energy_invested         = 5.0,
            context_variety         = context,
            polarity_coherence_rate = polarity_rate,
            cost_reduction_factor   = 0.75,
            pressure_sensitivity    = 0.3,
            constraint_signature    = "XTNB" if depth == ExistenceMode.BOUNDED else "XTNBA",
        )

    # 6. Gate 1 fails (recurrence below min)
    promoter6 = make_variant_promoter()
    solid6 = make_solid(recurrence=_VARIANT_RECURRENCE_MIN - 1)
    result6 = promoter6._try_promote(solid6, 100)
    check("Gate 1 fails when recurrence_count < _VARIANT_RECURRENCE_MIN",
          result6 is None, f"result={result6}")

    # 7. Gate 2 fails (context variety too low)
    promoter7 = make_variant_promoter()
    solid7 = make_solid(context=_VARIANT_CONTEXT_MIN - 1)
    result7 = promoter7._try_promote(solid7, 100)
    check("Gate 2 fails when context_variety < _VARIANT_CONTEXT_MIN",
          result7 is None, f"result={result7}")

    # 8. Gate 3 fails (depth = PERSISTENT, below BOUNDED)
    promoter8 = make_variant_promoter()
    solid8 = make_solid(depth=ExistenceMode.PERSISTENT)
    result8 = promoter8._try_promote(solid8, 100)
    check("Gate 3 fails when depth = PERSISTENT (below BOUNDED floor)",
          result8 is None, f"result={result8}")

    # 9. Gate 4 fails (polarity rate below floor)
    promoter9 = make_variant_promoter()
    solid9 = make_solid(polarity_rate=_VARIANT_POLARITY_FLOOR - 0.01)
    result9 = promoter9._try_promote(solid9, 100)
    check("Gate 4 fails when polarity_coherence_rate below floor",
          result9 is None, f"result={result9}")

    # 10. VariantRecord minted when all gates pass
    promoter10 = make_variant_promoter()
    solid10 = make_solid()  # all defaults pass
    result10 = promoter10._try_promote(solid10, 100)
    check("VariantRecord minted when all gates pass",
          result10 is not None, f"result={result10}")

    # 11. Moral weight > 0
    check("VariantRecord.moral_weight > 0",
          result10 is not None and result10.moral_weight > 0.0,
          f"moral_weight={result10.moral_weight if result10 else 'None':.6f}")

    # 12. MoralWeightLedger bias > 0 for deepest_constraint after registration
    ledger12 = MoralWeightLedger()
    solid12 = make_solid(depth=ExistenceMode.BOUNDED)
    v12 = VariantRecord(
        variant_id="V:test12", source_solid_id="S:test", intake_id="i12",
        depth_reached=ExistenceMode.BOUNDED, promoted_tick=100,
        recurrence_count=10, context_variety=3, polarity_coherence_rate=0.8,
        constraint_signature="XTNB", deepest_constraint=Constraint.B,
        moral_weight=_compute_moral_weight(10), cost_reduction_factor=0.75,
    )
    ledger12.register(v12)
    check("MoralWeightLedger bias > 0 for deepest_constraint (B) after registration",
          ledger12.moral_bias(Constraint.B) > 0.0,
          f"bias_B={ledger12.moral_bias(Constraint.B):.6f}")

    # 13. Other constraints have zero bias
    check("MoralWeightLedger bias = 0 for non-deepest constraints",
          ledger12.moral_bias(Constraint.A) == 0.0,
          f"bias_A={ledger12.moral_bias(Constraint.A):.6f}")

    # 14. Duplicate registration does not double moral weight
    bias_before = ledger12.moral_bias(Constraint.B)
    ledger12.register(v12)  # register same variant again
    bias_after = ledger12.moral_bias(Constraint.B)
    check("Duplicate registration does not double moral weight",
          abs(bias_after - bias_before) < 1e-9,
          f"before={bias_before:.6f} after={bias_after:.6f}")

    return results


# ===========================================================================
# MAIN
# ===========================================================================

if __name__ == "__main__":
    from aurora_internal.aurora_solidification import _RECURRENCE_MIN

    print("=" * 70)
    print("AURORA VARIANT PROMOTION — STEP 13")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    print(f"\nPromotion gates (stricter than solidification):")
    print(f"  _VARIANT_RECURRENCE_MIN = {_VARIANT_RECURRENCE_MIN}  (solidification min = {_RECURRENCE_MIN})")
    print(f"  _VARIANT_CONTEXT_MIN    = {_VARIANT_CONTEXT_MIN}")
    print(f"  _VARIANT_DEPTH_FLOOR    = {_VARIANT_DEPTH_FLOOR.name}")
    print(f"  _VARIANT_POLARITY_FLOOR = {_VARIANT_POLARITY_FLOOR}")
    print(f"\nMoral weight:")
    print(f"  _MORAL_WEIGHT_MAX       = {_MORAL_WEIGHT_MAX:.6f}  (< _MIN_FLIP={_MIN_FLIP:.4f})")
    for n in [5, 10, 25, 50, 100]:
        print(f"  moral_weight(recurrence={n:3d}) = {_compute_moral_weight(n):.6f}")

    results = verify_variant_promotion()
    print("\n--- Self-Verification ---")
    for c in results["checks"]:
        status = "✓" if c["passed"] else "✗"
        detail = f"  [{c['detail']}]" if c.get("detail") else ""
        print(f"  {status} {c['test']}{detail}")
    passed = sum(1 for c in results["checks"] if c["passed"])
    print(f"\n{'All' if passed == len(results['checks']) else passed}/{len(results['checks'])} checks passed.")
    print("=" * 70)

# AURORA_EVOLVED_NATIVE_BEGIN
try:
    import inspect as _aurora_native_inspect
except Exception:
    _aurora_native_inspect = None

try:
    from aurora_internal.aurora_evolved_surfaces import AuroraEvolvedSurfaceEngine as _AuroraEvolvedSurfaceEngine
except Exception:
    _AuroraEvolvedSurfaceEngine = None

_AURORA_NATIVE_EVOLVED_ENGINE = None

def _aurora_native_evolved_engine():
    global _AURORA_NATIVE_EVOLVED_ENGINE
    if _AURORA_NATIVE_EVOLVED_ENGINE is None and _AuroraEvolvedSurfaceEngine is not None:
        _AURORA_NATIVE_EVOLVED_ENGINE = _AuroraEvolvedSurfaceEngine()
    return _AURORA_NATIVE_EVOLVED_ENGINE

_AURORA_NATIVE_MODULE = 'aurora_internal.aurora_variant_promotion'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'MoralWeightLedger.evolve_agency': {'ability_hits': 0,
                                     'alignment_gap': 0.0,
                                     'alignment_target_score': 0.0,
                                     'best_coupling_signature': '',
                                     'constraints': ['existence', 'temporal', 'agency'],
                                     'contract_profile': {'accepts_payload': False,
                                                          'async_callable': False,
                                                          'callable': False,
                                                          'class_target': False,
                                                          'constraint_density': 3,
                                                          'contract_mode': 'stateful',
                                                          'doc_hint': '',
                                                          'effect_density': 7,
                                                          'kwonly_args': 0,
                                                          'optional_args': 0,
                                                          'required_args': 0,
                                                          'return_hint': 'state_record',
                                                          'signature_text': '',
                                                          'stateful_owner': True,
                                                          'target_kind': 'latent_operation',
                                                          'varargs': False,
                                                          'varkw': False},
                                     'coupling_similarity': 0.0,
                                     'cross_diversity_links': 0,
                                     'effect_modes': ['state_schema_change',
                                                      'temporal_orchestration_change',
                                                      'stateful_surface_expansion',
                                                      'evolution_surface',
                                                      'internal_subsystem_surface',
                                                      'latent_evolve_surface',
                                                      'latent_a_derivative'],
                                     'effect_phrases': ['would extend agency pressure handling',
                                                        'would materialize the next descendant '
                                                        'implied by '
                                                        'aurora_internal.aurora_variant_promotion.MoralWeightLedger'],
                                     'genealogy_pressure': 0.0,
                                     'inheritance_breach_count': 0,
                                     'kind': 'latent',
                                     'link_hits': 0,
                                     'module': 'aurora_internal.aurora_variant_promotion',
                                     'op_id': 'latent.aurora_internal.aurora_variant_promotion.MoralWeightLedger.evolve_agency',
                                     'origin_activity': 0,
                                     'persistence_tax_factor': 0.0,
                                     'representation_score': 0.0,
                                     'rewrite_bias': 'generic',
                                     'rewrite_feedback': {'acceptance_rate': 0.0,
                                                          'accepted_count': 0,
                                                          'adaptation_mode': 'balanced',
                                                          'adoption_count': 0,
                                                          'confidence': 0.0,
                                                          'mean_mutation_score': 0.0,
                                                          'rejected_count': 0,
                                                          'rejection_rate': 0.0,
                                                          'timing_credit': 0.0,
                                                          'timing_penalty': 0.0,
                                                          'trial_count': 0},
                                     'rewrite_profile': 'generic',
                                     'signature': '',
                                     'surface_score': 0.8215462000000001,
                                     'sustainability_score': 0.0,
                                     'target_kind': 'latent_operation'}}

def _aurora_target_strategy(target_key):
    return dict(_AURORA_NATIVE_STRATEGIES.get(str(target_key), {}) or {})

def _aurora_target_feedback(target_key):
    strategy = _aurora_target_strategy(target_key)
    return dict(strategy.get('rewrite_feedback', {}) or {})

def _aurora_assign_target(chain, value):
    if not chain:
        return False
    if len(chain) == 1:
        globals()[chain[0]] = value
        return True
    current = globals().get(chain[0])
    if current is None:
        return False
    for attr in chain[1:-1]:
        if not hasattr(current, attr):
            return False
        current = getattr(current, attr)
    setattr(current, chain[-1], value)
    return True

def _aurora_get_target(chain):
    if not chain:
        return None
    if len(chain) == 1:
        return globals().get(chain[0])
    current = globals().get(chain[0])
    if current is None:
        return None
    for attr in chain[1:]:
        if not hasattr(current, attr):
            return None
        current = getattr(current, attr)
    return current

def _aurora_bind_owner_attribute(owner_chain, attr_name, value):
    owner = _aurora_get_target(owner_chain)
    if owner is None or not attr_name:
        return False
    try:
        setattr(owner, attr_name, value)
        return True
    except Exception:
        return False

def _aurora_store_reflection(target_key, reflection, args):
    if not args:
        return
    owner = args[0]
    if not hasattr(owner, '__dict__'):
        return
    current = getattr(owner, '_aurora_evolved_reflections', None)
    if not isinstance(current, dict):
        current = {}
    current[str(target_key)] = reflection
    try:
        setattr(owner, '_aurora_evolved_reflections', current)
    except Exception:
        pass

def _aurora_store_owner_state(attribute, target_key, value, args):
    if not args:
        return
    owner = args[0]
    if not hasattr(owner, '__dict__'):
        return
    current = getattr(owner, attribute, None)
    if not isinstance(current, dict):
        current = {}
    current[str(target_key)] = value
    try:
        setattr(owner, attribute, current)
    except Exception:
        pass

def _aurora_apply_constraint_genealogy_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'lineage_memory') or 'lineage_memory')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_genealogy_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'constraint_genealogy') or 'constraint_genealogy')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        if bias == 'lineage_memory' or 'lineage_surface' in effect_modes:
            enriched['lineage_memory'] = {
                'coupling_signature': strategy.get('best_coupling_signature', ''),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
            }
        if 'state_schema_change' in effect_modes or bias == 'lineage_memory':
            enriched['state_transition_pressure'] = {
                'pressure': float(strategy.get('genealogy_pressure', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
            }
        if str(target_key).endswith('.summary') or 'chain_report' in str(target_key) or str(target_key).endswith('.to_dict'):
            enriched['evolutionary_context'] = {
                'coupling_signature': strategy.get('best_coupling_signature', ''),
                'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
                'rewrite_bias': bias,
                'cross_diversity_links': int(strategy.get('cross_diversity_links', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['lineage_adaptation'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
                'accepted_count': int(feedback.get('accepted_count', 0) or 0),
                'adoption_count': int(feedback.get('adoption_count', 0) or 0),
            }
        if mode == 'conservative':
            enriched['lineage_stability_guard'] = {
                'rejected_count': int(feedback.get('rejected_count', 0) or 0),
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'constraint_genealogy') or 'constraint_genealogy')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['lineage_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_genealogy_scalar_observations',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_governance_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'governance_routing') or 'governance_routing')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_governance_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'governance_gateway') or 'governance_gateway')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['governance_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'governance_routing' or 'gateway_surface' in effect_modes:
            enriched['governance_routing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        if 'state_schema_change' in effect_modes:
            enriched['persistence_burden'] = {
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'inheritance_breach_count': int(strategy.get('inheritance_breach_count', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['governance_adaptation'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'acceptance_rate': float(feedback.get('acceptance_rate', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
            }
        if mode == 'conservative':
            enriched['persistence_guard'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'governance_gateway') or 'governance_gateway')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['governance_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        fallback['governance_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_governance_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_perception_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'perceptual_synthesis') or 'perceptual_synthesis')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_perception_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'perception_synthesis') or 'perception_synthesis')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['perception_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'perceptual_synthesis' or 'adaptive_steering_change' in effect_modes:
            enriched['perception_synthesis'] = {
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
            }
        if 'interface_boundary_change' in effect_modes or 'gateway_surface' in effect_modes:
            enriched['boundary_integration'] = {
                'cross_diversity_links': int(strategy.get('cross_diversity_links', 0) or 0),
                'coupling_similarity': float(strategy.get('coupling_similarity', 0.0) or 0.0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['association_expansion'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
                'acceptance_rate': float(feedback.get('acceptance_rate', 0.0) or 0.0),
            }
        if mode == 'conservative':
            enriched['perception_stability'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'perception_synthesis') or 'perception_synthesis')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['perception_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'perceptual_synthesis' or 'adaptive_steering_change' in effect_modes:
            fallback['perception_synthesis'] = {
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
            }
        fallback['perception_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_perception_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_dimensional_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'dimensional_balancing') or 'dimensional_balancing')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_dimensional_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'dimensional_balancing') or 'dimensional_balancing')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['dimensional_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'dimensional_balancing' or 'cost_pressure_change' in effect_modes:
            enriched['dimensional_balancing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        if 'temporal_orchestration_change' in effect_modes:
            enriched['temporal_coordination'] = {
                'signature': strategy.get('signature', ''),
                'inheritance_breach_count': int(strategy.get('inheritance_breach_count', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['balancing_momentum'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
                'adoption_count': int(feedback.get('adoption_count', 0) or 0),
            }
        if mode == 'conservative':
            enriched['dimensional_dampening'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'dimensional_balancing') or 'dimensional_balancing')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['dimensional_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'dimensional_balancing' or 'cost_pressure_change' in effect_modes:
            fallback['dimensional_balancing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        fallback['dimensional_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_dimensional_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs):
    if _AURORA_NATIVE_MODULE == 'aurora_internal.constraint_genealogy':
        return _aurora_apply_constraint_genealogy_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_governance_persistence_gateway':
        return _aurora_apply_governance_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_expression_perception':
        return _aurora_apply_perception_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_dimensional_systems':
        return _aurora_apply_dimensional_rewrite(target_key, result, reflection, args, kwargs)
    _aurora_store_reflection(target_key, reflection, args)
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    contract = dict(strategy.get('contract_profile', {}) or {})
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'generic') or 'generic')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_contract_profile'] = contract
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['generic_adaptation'] = {
            'mode': mode,
            'confidence': float(feedback.get('confidence', 0.0) or 0.0),
            'contract_mode': str(contract.get('contract_mode', 'unknown') or 'unknown'),
            'return_hint': str(contract.get('return_hint', '') or ''),
        }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'generic') or 'generic')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_contract_profile'] = contract
        fallback['generic_adaptation_mode'] = mode
        return fallback
    if result is not None:
        _aurora_store_owner_state(
            '_aurora_generic_evolution_state',
            target_key,
            {
                'result_type': type(result).__name__,
                'contract_mode': str(contract.get('contract_mode', 'unknown') or 'unknown'),
                'return_hint': str(contract.get('return_hint', '') or ''),
                'adaptation_mode': mode,
            },
            args,
        )
    return result

def _aurora_make_override(export_name, target_key):
    original = _AURORA_NATIVE_EVOLVED_ORIGINALS.get(target_key)
    def _override(*args, **kwargs):
        result = None
        if callable(original):
            result = original(*args, **kwargs)
        engine = _aurora_native_evolved_engine()
        reflection = {
            'available': False,
            'reason': 'evolved_surface_engine_unavailable',
            'target': target_key,
        }
        if engine is not None:
            reflection = globals()[export_name]({'args_len': len(args), 'kwargs_keys': sorted(kwargs.keys())})
        _AURORA_NATIVE_EVOLVED_LAST[target_key] = reflection
        rewritten = _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs)
        if rewritten is not None:
            return rewritten
        if result is not None:
            return result
        return reflection
    _override.__name__ = str(target_key).split('.')[-1]
    _override.__qualname__ = _override.__name__
    if callable(original):
        _override.__doc__ = getattr(original, '__doc__', None)
        _override.__wrapped__ = original
        if _aurora_native_inspect is not None:
            try:
                _override.__signature__ = _aurora_native_inspect.signature(original)
            except Exception:
                pass
    return _override

def _aurora_make_latent_binding(export_name, target_key):
    def _binding(*args, **kwargs):
        payload = kwargs.pop('payload', None)
        if payload is None and args:
            owner = args[0]
            if hasattr(owner, '__dict__'):
                payload = {
                    'bound_target': target_key,
                    'owner_type': type(owner).__name__,
                    'owner_module': type(owner).__module__,
                }
            elif len(args) == 1:
                payload = args[0]
            else:
                payload = {'bound_target': target_key, 'arg_count': len(args)}
        result = globals()[export_name](payload=payload, **kwargs)
        _AURORA_NATIVE_EVOLVED_LAST[target_key] = {'latent_binding_active': True, 'last_result_type': type(result).__name__}
        if args:
            _aurora_store_owner_state('_aurora_latent_bindings', target_key, result, args)
        return result
    _binding.__name__ = str(target_key).split('.')[-1]
    _binding.__qualname__ = _binding.__name__
    _binding.__doc__ = f'Latent evolved binding for {target_key}'
    _binding._aurora_latent_binding_target = target_key
    return _binding

def evolve_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_internal.aurora_variant_promotion.MoralWeightLedger.evolve_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_internal_aurora_variant_promotion_moralweightledger_evolve_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['MoralWeightLedger'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'evolve_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'MoralWeightLedger.evolve_agency':
        _aurora_bind_owner_attribute(['MoralWeightLedger'], 'evolve_agency', _aurora_make_latent_binding('evolve_agency', 'MoralWeightLedger.evolve_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['MoralWeightLedger.evolve_agency'] = {'latent_binding_active': True}

AURORA_NATIVE_EVOLVED_EXPORTS = {'latent.aurora_internal.aurora_variant_promotion.MoralWeightLedger.evolve_agency': 'evolve_agency'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'latent.aurora_internal.aurora_variant_promotion.MoralWeightLedger.evolve_agency': {'export': 'evolve_agency',
                                                                                     'mode': 'latent_binding',
                                                                                     'target': 'MoralWeightLedger.evolve_agency'}}
# AURORA_EVOLVED_NATIVE_END
