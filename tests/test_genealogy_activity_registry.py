#!/usr/bin/env python3
"""Regression coverage for the cross-system activity registry (Sunni & Cael):
the substrate a future consequence-derived representation profile needs to
distinguish genuine isolation from coincidental co-activation, rather than
crediting every active representation for everything that happened.

genealogy.observe() is the shared convergence point roughly a dozen
distinct subsystems funnel evidence through -- confirmed by direct grep
across the codebase (sensory citizenship, dream/code evidence, grammar
engine, dimensional systems, pipeline modulation, tool mind, evolution
chamber). Recording activity there sees cross-subsystem co-activation for
free, since one ConstraintGenealogyLogger instance is shared per process.

Stated honestly, and tested for here: this registry only sees activity
that reaches observe(). It is not omniscient about everything Aurora does.
"""
from __future__ import annotations

from aurora_internal.constraint_genealogy import (
    AbilityProfile,
    ConstraintGenealogyLogger,
    GenealogyConfig,
    PressureVec,
    TraceItem,
)


def _fresh_genealogy(tmp_path, name="activity_registry_test", maxlen=None):
    cfg = GenealogyConfig()
    if maxlen is not None:
        cfg.ACTIVITY_LOG_MAXLEN = maxlen
    return ConstraintGenealogyLogger(name, config=cfg, output_dir=str(tmp_path / name))


def _seed_ability(genealogy, aid, axis="X"):
    genealogy.abilities[aid] = AbilityProfile(
        id=aid, axis=axis, requires=(axis,),
        cost={a: 0.001 for a in ("X", "T", "N", "B", "A")},
        risk={a: 0.0 for a in ("X", "T", "N", "B", "A")},
        effect_tags=("test",), notes="test",
    )


def _observe(genealogy, *ids, relief=0.05):
    p_before = PressureVec(X=relief, T=0.0, N=0.0, B=0.0, A=0.0)
    p_after = PressureVec(X=0.0, T=0.0, N=0.0, B=0.0, A=0.0)
    trace = [TraceItem(kind="ABILITY", id=i) for i in ids]
    return genealogy.observe(pressure_before=p_before, trace=trace, pressure_after=p_after)


# ── Recording ────────────────────────────────────────────────────────────

def test_activity_is_recorded_on_every_observe_call_relief_or_not(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:A")

    # Zero relief (before == after) -- must NOT qualify as a relief event,
    # but activity must still be recorded: co-activation is a fact about
    # what happened, not about whether it produced measurable relief.
    p = PressureVec(X=0.0, T=0.0, N=0.0, B=0.0, A=0.0)
    result = genealogy.observe(pressure_before=p, trace=[TraceItem(kind="ABILITY", id="X:A")], pressure_after=p)
    assert result is None  # confirms this really was filtered as non-relief

    assert len(genealogy._activity_log) == 1
    tick, ids = genealogy._activity_log[-1]
    assert ids == ("X:A",)


def test_multiple_ids_in_one_trace_are_all_recorded(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:A")
    _seed_ability(genealogy, "T:B")
    _observe(genealogy, "X:A", "T:B")

    tick, ids = genealogy._activity_log[-1]
    assert set(ids) == {"X:A", "T:B"}


def test_activity_log_is_bounded(tmp_path):
    genealogy = _fresh_genealogy(tmp_path, maxlen=5)
    _seed_ability(genealogy, "X:A")
    for _ in range(20):
        _observe(genealogy, "X:A")
    assert len(genealogy._activity_log) == 5


# ── Query API ────────────────────────────────────────────────────────────

def test_activity_in_window_excludes_the_queried_id_itself(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:A")
    _observe(genealogy, "X:A")
    tick = genealogy.tick_count

    others = genealogy.activity_in_window(tick, window=3, exclude_ids=("X:A",))
    assert "X:A" not in others


def test_activity_in_window_sees_co_activity_from_other_ids(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:A")
    _seed_ability(genealogy, "N:C")
    _observe(genealogy, "X:A")
    _observe(genealogy, "N:C")
    tick = genealogy.tick_count

    others = genealogy.activity_in_window(tick, window=3, exclude_ids=("X:A",))
    assert others.get("N:C", 0) >= 1


def test_activity_in_window_does_not_see_activity_outside_the_window(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:A")
    _seed_ability(genealogy, "N:C")
    _observe(genealogy, "N:C")
    old_tick = genealogy.tick_count
    for _ in range(10):
        _observe(genealogy, "X:A")
    recent_tick = genealogy.tick_count

    others = genealogy.activity_in_window(recent_tick, window=2, exclude_ids=("X:A",))
    assert "N:C" not in others, "activity far outside the window must not count"

    # But it IS visible from close enough to when it actually happened.
    others_near_then = genealogy.activity_in_window(old_tick, window=1, exclude_ids=("X:A",))
    assert "N:C" in others_near_then


# ── Isolation confidence ─────────────────────────────────────────────────

def test_isolation_confidence_is_full_when_nothing_else_active(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:A")
    _observe(genealogy, "X:A")
    tick = genealogy.tick_count

    assert genealogy.isolation_confidence("X:A", tick, window=3) == 1.0


def test_isolation_confidence_decays_with_more_distinct_co_activity(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    for aid in ("X:A", "N:C", "B:D", "A:E"):
        _seed_ability(genealogy, aid)

    _observe(genealogy, "X:A")
    conf_alone = genealogy.isolation_confidence("X:A", genealogy.tick_count, window=3)

    _observe(genealogy, "N:C")
    conf_one_other = genealogy.isolation_confidence("X:A", genealogy.tick_count, window=3)

    _observe(genealogy, "B:D")
    _observe(genealogy, "A:E")
    conf_three_others = genealogy.isolation_confidence("X:A", genealogy.tick_count, window=5)

    assert conf_alone == 1.0
    assert conf_one_other < conf_alone
    assert conf_three_others < conf_one_other


def test_isolation_confidence_counts_distinct_ids_not_repeat_appearances(tmp_path):
    """One other representation appearing three times is still 'one other
    thing going on' -- not treated as worse than three DIFFERENT other
    representations appearing once each."""
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:A")
    _seed_ability(genealogy, "N:C")
    _observe(genealogy, "X:A")
    for _ in range(3):
        _observe(genealogy, "N:C")

    conf_one_repeated = genealogy.isolation_confidence("X:A", genealogy.tick_count, window=5)

    genealogy2 = _fresh_genealogy(tmp_path, "activity_registry_test_2")
    for aid in ("X:A", "N:C", "B:D", "A:E"):
        _seed_ability(genealogy2, aid)
    _observe(genealogy2, "X:A")
    _observe(genealogy2, "N:C")
    _observe(genealogy2, "B:D")
    _observe(genealogy2, "A:E")
    conf_three_distinct = genealogy2.isolation_confidence("X:A", genealogy2.tick_count, window=5)

    assert conf_one_repeated > conf_three_distinct


def test_isolation_confidence_is_backward_looking_only(tmp_path):
    """Judging isolation at an earlier tick must not be influenced by
    activity that hasn't happened yet at that point in the log."""
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:A")
    _seed_ability(genealogy, "N:C")
    _observe(genealogy, "X:A")
    early_tick = genealogy.tick_count
    _observe(genealogy, "N:C")  # happens AFTER early_tick

    conf_at_early_tick = genealogy.isolation_confidence("X:A", early_tick, window=5)
    assert conf_at_early_tick == 1.0, "future activity must not retroactively reduce isolation confidence"


# ── Real cross-subsystem integration: sensory citizenship ──────────────────

def test_sensory_citizen_participation_is_visible_in_the_activity_registry(tmp_path):
    """The concrete motivating case: a sensory citizen's own
    tick_citizen_participation() calls genealogy.observe() like any other
    subsystem -- this registry must see it without any sensory-specific
    code, proving the "one shared instance sees everyone" design actually
    holds for a real caller, not just synthetic TraceItems."""
    from aurora_internal.aurora_sensory_crystal import SensoryClusterFacet, SensoryNode

    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("audio", "tone")
    node = SensoryNode(node_id="n1", domain="audio", facet="tone", centroid=[0.1] * 8)
    node.stage = "promoted"
    node.fitness = 0.6
    facet._nodes[node.node_id] = node
    facet._genealogy_ref = genealogy
    facet.grant_representational_citizenship(node)

    # An unrelated subsystem's own observe() call, interleaved.
    _seed_ability(genealogy, "N:UNRELATED")
    _observe(genealogy, "N:UNRELATED")

    node.fitness = 0.75
    facet.tick_citizen_participation()

    tick, ids = genealogy._activity_log[-1]
    assert ids == (node.citizen_ability_id,)
    others = genealogy.activity_in_window(tick, window=3, exclude_ids=(node.citizen_ability_id,))
    assert "N:UNRELATED" in others
