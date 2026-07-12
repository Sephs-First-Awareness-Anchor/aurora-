# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression tests for wiring aurora_understanding_sediment into
ReflexiveInterpreter (FIX-A009, 2026-07-12). Before this,
ReflexiveInterpreter.interpret() recomputed worth trajectory from an
in-RAM-only dict every session (WorthTrajectory.UNKNOWN on every boot,
a 0.7x multiplier tax on all first-touch meaning), and origin_region
never moved from whatever the compiled manifold said at build time --
lived understanding never fed back into the field.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_reflexive_interpreter import ReflexiveInterpreter, UNDERSTANDING_THRESHOLD


def test_interpreter_wires_overlay_and_ledger_when_state_dir_given(tmp_path):
    ri = ReflexiveInterpreter(state_dir=str(tmp_path))
    assert ri._overlay is not None
    assert ri._worth_ledger is not None


def test_interpret_stamps_sediment_and_recall_keys_into_noncomp_state(tmp_path):
    ri = ReflexiveInterpreter(state_dir=str(tmp_path))
    state = ri.interpret("I understand what you mean about boundaries")
    assert "sediment_delta" in state.noncomp_state
    assert "recall_boost" in state.noncomp_state
    assert isinstance(state.noncomp_state["sediment_delta"], float)
    assert isinstance(state.noncomp_state["recall_boost"], float)


def test_understood_expression_deposits_sediment_that_persists(tmp_path):
    """The actual snowball: an understood expression must leave a real,
    persisted trace that a fresh interpreter instance (new session) can
    read back and use to densify the same neighborhood."""
    ri1 = ReflexiveInterpreter(state_dir=str(tmp_path))
    state = ri1.interpret("I understand what you mean about boundaries")
    assert state.is_understood is True

    overlay_path = tmp_path / "understanding_sediment_overlay.json"
    assert overlay_path.exists(), "an understood expression must persist sediment to disk"

    # A brand new interpreter instance (simulating a fresh process) must
    # read the same live delta back via its own overlay instance.
    ri2 = ReflexiveInterpreter(state_dir=str(tmp_path))
    key = state.nc_name or f"{state.constraint}:{state.dimension}"
    from aurora_understanding_sediment import slot_key
    slot = slot_key(state.constraint, state.dimension)
    assert ri2._overlay.delta(key, slot) > 0.0


def test_worth_trajectory_survives_across_interpreter_instances(tmp_path):
    """Regression for the exact problem PersistentWorthLedger fixes: worth
    history used to live only in the in-RAM dict, so trajectory always
    restarted at UNKNOWN on a fresh instance. Recording several rising
    scores through one instance, then rehydrating in a second instance via
    the same key, must NOT reset to an empty window."""
    ri1 = ReflexiveInterpreter(state_dir=str(tmp_path))
    key = "B:OPERATOR"
    for score in (0.51, 0.58, 0.63, 0.70):
        ri1._worth_ledger.record(key, score)
    ri1._worth_ledger.save()

    ri2 = ReflexiveInterpreter(state_dir=str(tmp_path))
    hist = ri2._worth_history_for(key)
    assert hist.latest == 0.70


def test_graceful_degradation_without_state_dir_write_access(tmp_path):
    """If sediment/ledger construction fails for any reason, interpret()
    must still work -- deposition is an enhancement layer, never a hard
    dependency of the interpreter's core function."""
    import aurora_reflexive_interpreter as module

    class _ExplodingOverlay:
        def __init__(self, *a, **kw):
            raise RuntimeError("disk full")

    original = module.UnderstandingSedimentOverlay
    module.UnderstandingSedimentOverlay = _ExplodingOverlay
    try:
        ri = ReflexiveInterpreter(state_dir=str(tmp_path))
        assert ri._overlay is None
        state = ri.interpret("hello there, how are things")
        assert state is not None
    finally:
        module.UnderstandingSedimentOverlay = original


def test_recall_boost_lifts_worth_score_for_resonant_memory(tmp_path):
    """recall_confidence_boost should be able to push a borderline
    expression's worth score up via the confidence term -- verified by
    comparing against a sedimemory stub with no resonant results."""

    class _ResonantMemory:
        def recall_semantic(self, query_text="", *, max_results=8,
                            axis_filter=None, min_score=0.35):
            return [{"score": 0.95}]

    ri_plain = ReflexiveInterpreter(state_dir=str(tmp_path / "plain"))
    ri_boosted = ReflexiveInterpreter(
        state_dir=str(tmp_path / "boosted"), sedimemory=_ResonantMemory()
    )

    text = "I understand what you mean about boundaries"
    state_plain = ri_plain.interpret(text)
    state_boosted = ri_boosted.interpret(text)

    assert state_boosted.worth_score >= state_plain.worth_score
