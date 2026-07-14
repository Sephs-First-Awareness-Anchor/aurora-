"""
tests/test_articulation_semantic_strategy.py
================================================
MTSL (Phase 5, live-wired 2026-07-14): aurora_articulation.py's
decide_articulation() actually consumes semantic_strategy/
semantic_strategy_applied now, raising the pressure-relief bar for
caution-calling strategies (abstain/clarify/contrast) -- but ONLY when
the caller marks the strategy semantic_strategy_applied=True, and
never lowering the bar for any strategy.
"""
import aurora_articulation as aa

# A draft/candidate pair hand-picked so relief (0.07) lands strictly
# between the baseline min_relief (0.035) and the abstain-bumped one
# (0.115) -- the exact case that flips accepted True -> False.
_FLIP_DRAFT = "[curious] the weather today seems quite unpredictable honestly"
_FLIP_CANDIDATE = "The weather today seems unpredictable."


def test_no_context_is_unaffected():
    d = aa.decide_articulation(_FLIP_DRAFT, _FLIP_CANDIDATE, context=None)
    assert d.metadata["semantic_strategy_relief_bump"] == 0.0
    assert d.accepted is True


def test_strategy_present_but_not_applied_is_byte_identical_to_no_context():
    baseline = aa.decide_articulation(_FLIP_DRAFT, _FLIP_CANDIDATE, context=None)
    not_applied = aa.decide_articulation(
        _FLIP_DRAFT, _FLIP_CANDIDATE,
        context={"semantic_strategy": "abstain", "semantic_strategy_applied": False},
    )
    assert not_applied.accepted == baseline.accepted
    assert not_applied.reason == baseline.reason
    assert not_applied.metadata["min_relief_used"] == baseline.metadata["min_relief_used"]
    assert not_applied.metadata["semantic_strategy_relief_bump"] == 0.0


def test_missing_applied_flag_defaults_to_not_applied():
    # semantic_strategy_applied omitted entirely -- must default to the
    # safe/inert reading (False), not silently apply the bump.
    d = aa.decide_articulation(
        _FLIP_DRAFT, _FLIP_CANDIDATE, context={"semantic_strategy": "abstain"},
    )
    assert d.metadata["semantic_strategy_relief_bump"] == 0.0
    assert d.accepted is True


def test_abstain_applied_raises_the_bar_and_flips_acceptance():
    d = aa.decide_articulation(
        _FLIP_DRAFT, _FLIP_CANDIDATE,
        context={"semantic_strategy": "abstain", "semantic_strategy_applied": True},
    )
    assert d.metadata["semantic_strategy_relief_bump"] == 0.08
    assert d.metadata["min_relief_used"] == 0.115
    assert d.accepted is False
    assert d.reason == "candidate_did_not_clear_semantic_caution_bar"
    assert d.selected == d.original  # falls back to Aurora's own literal draft


def test_clarify_applied_raises_the_bar_by_a_smaller_amount():
    d = aa.decide_articulation(
        _FLIP_DRAFT, _FLIP_CANDIDATE,
        context={"semantic_strategy": "clarify", "semantic_strategy_applied": True},
    )
    assert d.metadata["semantic_strategy_relief_bump"] == 0.05


def test_contrast_applied_raises_the_bar_by_the_smallest_amount():
    d = aa.decide_articulation(
        _FLIP_DRAFT, _FLIP_CANDIDATE,
        context={"semantic_strategy": "contrast", "semantic_strategy_applied": True},
    )
    assert d.metadata["semantic_strategy_relief_bump"] == 0.03


def test_non_caution_strategies_apply_zero_bump_even_when_applied():
    for strategy in ("explain", "reflect", "act", "observe"):
        d = aa.decide_articulation(
            _FLIP_DRAFT, _FLIP_CANDIDATE,
            context={"semantic_strategy": strategy, "semantic_strategy_applied": True},
        )
        assert d.metadata["semantic_strategy_relief_bump"] == 0.0, strategy
        assert d.accepted is True, strategy


def test_bump_is_monotonically_ordered_by_caution_strength():
    bumps = {}
    for strategy in ("contrast", "clarify", "abstain"):
        d = aa.decide_articulation(
            _FLIP_DRAFT, _FLIP_CANDIDATE,
            context={"semantic_strategy": strategy, "semantic_strategy_applied": True},
        )
        bumps[strategy] = d.metadata["semantic_strategy_relief_bump"]
    assert bumps["contrast"] < bumps["clarify"] < bumps["abstain"]


def test_semantic_strategy_applied_is_now_whitelisted_in_expression_context():
    d = aa.decide_articulation(
        _FLIP_DRAFT, _FLIP_CANDIDATE,
        context={"semantic_strategy": "abstain", "semantic_confidence": 0.7, "semantic_strategy_applied": True},
    )
    ctx = d.metadata["expression_context"]
    assert ctx["semantic_strategy"] == "abstain"
    assert ctx["semantic_confidence"] == 0.7
    assert ctx["semantic_strategy_applied"] is True


def test_unrecognized_strategy_string_is_inert():
    d = aa.decide_articulation(
        _FLIP_DRAFT, _FLIP_CANDIDATE,
        context={"semantic_strategy": "not_a_real_strategy", "semantic_strategy_applied": True},
    )
    assert d.metadata["semantic_strategy_relief_bump"] == 0.0
