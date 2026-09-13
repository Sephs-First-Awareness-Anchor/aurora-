#!/usr/bin/env python3
"""Regression tests for docs/AURORA_RELATIONAL_PROMOTION_JURISDICTION_REPAIR_DIRECTIVE.md.

The defect was jurisdictional: _try_promote() judged PairStats' shadow of a
representation relation as though it were the complete candidate, while the
richer intact relation (self._representation_relations, built by
_update_representation_relation() from real observed coactivation) was
consulted/attached only after promotion succeeded. The repair threads the
already-existing relation record into _try_promote() at decision time
(narrowest existing seam: _accumulate_pairs() now captures
_update_representation_relation()'s previously-discarded return value and
passes it through).

An earlier revision of this repair additionally fed a same-signed-Difference
"consistency ratio" from the relation into Gate 2's local_support as a
reliability corroboration signal. That was removed (Sunni & Cael): Aurora's
existing Difference physics never establishes that same-signed Difference
means reliability, and DIFFERENCE_PARAMS[X] and DIFFERENCE_PARAMS[B] are
unsigned by construction (polarity_signed=False) -- a sign-consistency ratio
computed over their values is a mathematical artifact of how they happen to
be stored, not causal evidence. So: the intact relation is available to
_try_promote() at decision time and its Difference history survives
promotion intact, but no gate consults it. Difference should affect
promotion only once an existing lawful Aurora mechanism gives it that
meaning -- not yet established, so it stays inert here.

Every proof below drives the real ConstraintGenealogyLogger / PairStats /
_try_promote() machinery -- no parallel promotion path is created or
exercised.

A note on requirement 7 of the directive ("update only tests the repaired
architecture intentionally invalidates"): tests/test_genealogy_promotion_
dimension_observer.py, tests/test_genealogy_difference_shadow.py, tests/
test_genealogy_cooccurrence_observatory.py, and tests/test_genealogy_
difference_producer_observatory.py all pin invariants this repair does not
touch -- PairStats.update()'s signature (still exactly ["self", "relief",
"cost", "x_risk", "tick"], still no Dimension/NonComp-typed parameter),
PairStats' own __dict__ shape (still exactly the ten axis-keyed
accumulator fields, no difference_values field), and the literal
_accumulate_pairs(...) call inside _observe_impl() (still
"_accumulate_pairs(trace, relief, cost_total, x_risk_total)", no
difference_snapshot argument added). This repair stores the relation
separately (self._representation_relations, unchanged location) and only
threads the already-returned record through an existing internal call
(_accumulate_pairs() -> _try_promote()), so none of those four files
needed modification.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import pytest

from aurora_constraint_stack import DifferenceSnapshot
from aurora_internal.aurora_constraint_manifold_patched import Constraint
from aurora_internal.constraint_genealogy import (
    AXES,
    ConstraintGenealogyLogger,
    GenealogyConfig,
    PairStats,
    PressureVec,
    TraceItem,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _relaxed_config(**overrides):
    """A config that makes real end-to-end promotion reachable in a handful
    of ticks, mirroring the established pattern in
    tests/test_cross_generational_representational_recombination.py."""
    base = dict(
        K_MIN=6,
        RELIEF_EPS=0.000001,
        RELIEF_TOTAL_EPS=0.000001,
        RELIEF_PROMOTE_MIN=0.00001,
        POS_FRACTION_MIN=0.50,
        NET_MIN=0.00000001,
        X_RISK_MAX=1.0,
        COST_TO_RELIEF_SCALE=0.0,
        THRESHOLD_PRESSURE_ENABLED=False,
    )
    base.update(overrides)
    return GenealogyConfig(**base)


def _make_ps(pos_count_x: int, count: int, relief_per_hit: float = 0.01) -> PairStats:
    """A hand-built PairStats with an exact, controlled pos_fraction/mean_pos_relief
    on axis X, isolating Gate 2's decision from everything _accumulate_pairs()
    would otherwise compute from a real trace."""
    ps = PairStats(left_id="A:one", right_id="B:two")
    ps.count = count
    ps.last_seen_tick = count
    ps.relief_pos_sum["X"] = relief_per_hit * pos_count_x
    ps.relief_sum["X"] = relief_per_hit * pos_count_x
    ps.pos_count["X"] = pos_count_x
    return ps


def _difference_snapshot(x=0.10, t=-0.20, n=0.30, b=0.40, a=-0.50):
    values = {Constraint.X: x, Constraint.T: t, Constraint.N: n, Constraint.B: b, Constraint.A: a}
    refs = {constraint: 1.0 for constraint in values}
    return DifferenceSnapshot(tick=1, values=values, ref_magnitudes=refs)


def _positive_tick(logger, trace, snapshot=None):
    return logger.observe(
        pressure_before=PressureVec(X=1.0, T=0.8, N=0.6, B=0.4, A=0.2),
        trace=trace,
        pressure_after=PressureVec(X=0.8, T=0.7, N=0.5, B=0.3, A=0.1),
        difference_snapshot=snapshot,
    )


def _promote_via_real_observe(logger, trace, snapshot=None, max_ticks=12):
    for _ in range(max_ticks):
        _positive_tick(logger, trace, snapshot=snapshot)
        child_id = logger._links_by_parents.get((trace[0].id, trace[1].id))
        if child_id:
            return logger.links[child_id]
    return None


# ---------------------------------------------------------------------------
# Proof 1: _try_promote() receives the actual existing relation, not a copy
# ---------------------------------------------------------------------------

class TestCandidateIsTheActualObservedRelation:
    def test_try_promote_receives_the_same_object_stored_in_representation_relations(self, tmp_path):
        logger = ConstraintGenealogyLogger(run_id="identity", output_dir=str(tmp_path))
        relief = PressureVec(X=0.1, T=0.0, N=0.0, B=0.0, A=0.0)
        cost = {a: 0.0 for a in AXES}
        trace = [TraceItem(kind="ABILITY", id="A:one"), TraceItem(kind="ABILITY", id="B:two")]

        seen = {}
        original = logger._try_promote

        def spy(key, ps, relation=None):
            seen["relation"] = relation
            return original(key, ps, relation)

        logger._try_promote = spy
        logger._accumulate_pairs(trace, relief, cost, 0.0)

        key = ("A:one", "B:two")
        relation_id = logger._representation_relation_id(*key)
        stored = logger._representation_relations.get(relation_id)

        assert seen["relation"] is not None
        assert seen["relation"] is stored, (
            "_try_promote() must see the literal object "
            "_update_representation_relation() built and stored, not a "
            "newly fabricated or copied relation."
        )


# ---------------------------------------------------------------------------
# Proof 2 + 3: Difference presence alone never alters promotion -- the
# relation is available at decision time, but no gate consults its
# Difference evidence. Confirmed with a PairStats that comfortably clears
# Gate 2 on its own AND with the exact borderline PairStats that a prior,
# now-removed revision of this repair used to make Difference evidence flip.
# ---------------------------------------------------------------------------

class TestDifferencePresenceDoesNotAlterPromotion:
    def test_gate_outcome_identical_for_none_vs_empty_vs_populated_evidence_relation(self, tmp_path):
        """relation=None, relation={}, a relation with zero abs_sum evidence,
        and a relation with strong self-consistent Difference evidence must
        all produce the identical Gate 2 result on a PairStats built below
        Gate 2's regulated floor -- no gate reads relation["difference"],
        so none of these can differ from one another."""
        key = ("A:one", "B:two")
        ps = _make_ps(pos_count_x=16, count=50)  # pf(X) = 0.32, below Gate 2's floor

        logger_none = ConstraintGenealogyLogger(run_id="none", output_dir=str(tmp_path / "a"))
        link_none = logger_none._try_promote(key, ps, None)

        logger_empty = ConstraintGenealogyLogger(run_id="empty", output_dir=str(tmp_path / "b"))
        link_empty = logger_empty._try_promote(key, ps, {})

        logger_zero = ConstraintGenealogyLogger(run_id="zero", output_dir=str(tmp_path / "c"))
        zero_relation = {"difference": {"sum": {"X": 0.0}, "abs_sum": {"X": 0.0}}}
        link_zero = logger_zero._try_promote(key, ps, zero_relation)

        logger_strong = ConstraintGenealogyLogger(run_id="strong", output_dir=str(tmp_path / "d"))
        strong_relation = {"difference": {"sum": {"X": 1.0}, "abs_sum": {"X": 1.0}}}
        link_strong = logger_strong._try_promote(key, ps, strong_relation)

        assert link_none is None and link_empty is None and link_zero is None and link_strong is None, (
            "strong, self-consistent Difference evidence must not flip "
            "Gate 2 -- Difference has no causal meaning wired to any gate."
        )
        stats = [
            logger_none._promotion_stats.get("reject_reliability"),
            logger_empty._promotion_stats.get("reject_reliability"),
            logger_zero._promotion_stats.get("reject_reliability"),
            logger_strong._promotion_stats.get("reject_reliability"),
        ]
        assert stats == [1, 1, 1, 1]

    def test_gate2_outcome_unchanged_when_relief_alone_already_clears_the_floor(self, tmp_path):
        """When PairStats' own pos_fraction already comfortably clears Gate
        2's regulated floor on its own, supplying real Difference evidence
        must not change the Gate 2 decision or the resulting link's
        physics."""
        key = ("A:one", "B:two")
        ps = _make_ps(pos_count_x=35, count=50)  # pf(X) = 0.70, comfortably clears

        logger_none = ConstraintGenealogyLogger(run_id="comfortable_none", output_dir=str(tmp_path / "a"))
        link_none = logger_none._try_promote(key, ps, None)

        logger_strong = ConstraintGenealogyLogger(run_id="comfortable_strong", output_dir=str(tmp_path / "b"))
        strong_relation = {"difference": {"sum": {"X": 1.0}, "abs_sum": {"X": 1.0}}}
        link_strong = logger_strong._try_promote(key, ps, strong_relation)

        assert link_none is not None and link_strong is not None
        assert logger_none._promotion_stats.get("reject_reliability", 0) == 0
        assert logger_strong._promotion_stats.get("reject_reliability", 0) == 0
        # Same PairStats-derived physics either way -- the relation only
        # ever affects the metadata attached after promotion
        # (representation_relation/constraint_basis/semantic_identity),
        # never the promoted link's own measured relief/cost/depth/axis.
        assert link_none.mean_relief == link_strong.mean_relief
        assert link_none.mean_cost == link_strong.mean_cost
        assert link_none.dominant_relief_axis == link_strong.dominant_relief_axis
        assert link_none.depth == link_strong.depth
        assert link_none.count == link_strong.count

    def test_real_observe_driven_promotion_unaffected_by_unsigned_axis_difference(self, tmp_path):
        """DIFFERENCE_PARAMS[X] and DIFFERENCE_PARAMS[B] are unsigned by
        construction -- a real difference_snapshot carrying activity on
        those axes must not influence promotion via the relation (it may
        still influence promotion via other, pre-existing mechanisms
        unrelated to this repair, e.g. _update_gradient_memory() feeding
        Gate 5's gradient_signal -- this test isolates the relation's own
        effect via direct _try_promote() calls, not a multi-tick observe()
        timing comparison)."""
        key = ("A:one", "B:two")
        ps = _make_ps(pos_count_x=16, count=50)  # borderline, pf(X) = 0.32

        logger_x = ConstraintGenealogyLogger(run_id="unsigned_x", output_dir=str(tmp_path / "a"))
        x_relation = {"difference": {"sum": {"X": 0.9}, "abs_sum": {"X": 0.9}}}
        link_x = logger_x._try_promote(key, ps, x_relation)

        logger_b = ConstraintGenealogyLogger(run_id="unsigned_b", output_dir=str(tmp_path / "b"))
        b_relation = {"difference": {"sum": {"B": 0.9}, "abs_sum": {"B": 0.9}}}
        link_b = logger_b._try_promote(key, ps, b_relation)

        assert link_x is None and link_b is None


# ---------------------------------------------------------------------------
# Proof 4: existing relation history/parents/basis/consequence/difference
# survive promotion intact
# ---------------------------------------------------------------------------

class TestRelationHistorySurvivesPromotionIntact:
    def test_pre_promotion_accumulated_evidence_is_preserved_on_the_promoted_link(self, tmp_path):
        cfg = _relaxed_config()
        trace = [TraceItem(kind="ABILITY", id="A:one"), TraceItem(kind="ABILITY", id="B:two")]
        logger = ConstraintGenealogyLogger(run_id="survives", config=cfg, output_dir=str(tmp_path))

        snapshot = _difference_snapshot()
        child = _promote_via_real_observe(logger, trace, snapshot=snapshot)
        assert child is not None

        relation_id = logger._representation_relation_id("A:one", "B:two")
        live_rec = logger._representation_relations[relation_id]

        # The record promotion attached to the link IS the live record
        # (or a faithful snapshot of it) -- not a fresh, empty structure.
        promoted_relation = child.representation_relation
        assert promoted_relation["parent_ids"] == ["A:one", "B:two"]
        assert live_rec["parent_ids"] == ["A:one", "B:two"]
        assert live_rec["status"] == "promoted"
        assert live_rec["promoted_link_id"] == child.id

        assert promoted_relation["evidence"]["consequence_history"], (
            "consequence history must survive onto the promoted link"
        )
        assert promoted_relation["evidence"]["difference"]["observation_count"] > 0, (
            "accumulated Difference evidence must survive onto the promoted link"
        )
        assert child.constraint_basis == live_rec["constraint_basis"]


# ---------------------------------------------------------------------------
# Full self-test entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
