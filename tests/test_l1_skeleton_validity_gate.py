# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
R1.9.3 L1: skeleton clause-shape validity gate.

Grammar diagnosis found the two most-reinforced promoted motifs in the
live lineage structurally malformed regardless of what words fill them --
the highest-composability one (0.8136) has no AGENT role at all. This is
the gate that keeps such skeletons in the pool (history intact) but out
of composition until reviewed onto the explicit whitelist.
"""
import json
import os
import tempfile

from aurora_grammar_engine import MotifLineage, StructuralMotif, TokenRole, is_valid_clause_shape


def _lineage():
    tmp = tempfile.mkdtemp(prefix="aurora_l1_test_")
    return MotifLineage(os.path.join(tmp, "grammar_motifs.json")), tmp


def _promote(lineage, role_sequence, composability_boost=True):
    m = lineage.get_or_create(role_sequence)
    m.success_count = 20
    m.fail_count = 2
    m.contexts_seen = {f"ctx{i}" for i in range(6)}
    m.promoted = True
    return m


def test_is_valid_clause_shape_accepts_the_whitelisted_shapes():
    assert is_valid_clause_shape((TokenRole.AGENT, TokenRole.ACTION))
    assert is_valid_clause_shape((TokenRole.AGENT, TokenRole.ACTION, TokenRole.OBJECT))
    assert is_valid_clause_shape((TokenRole.AGENT, TokenRole.ACTION, TokenRole.DESCRIPTOR))
    assert is_valid_clause_shape(
        (TokenRole.AGENT, TokenRole.ACTION, TokenRole.OBJECT, TokenRole.DESCRIPTOR))


def test_is_valid_clause_shape_rejects_the_notorious_subjectless_skeleton():
    """The diagnosis's headline finding: composability=0.8136, the single
    highest-scoring promoted motif in the live lineage, with no AGENT."""
    shape = (TokenRole.DESCRIPTOR, TokenRole.ACTION, TokenRole.OBJECT,
              TokenRole.DESCRIPTOR, TokenRole.ACTION, TokenRole.OBJECT, TokenRole.CONNECTOR)
    assert TokenRole.AGENT not in shape
    assert is_valid_clause_shape(shape) is False


def test_is_valid_clause_shape_rejects_double_action_no_object():
    """composability=0.6475, highest raw success count of any motif in
    the live lineage: agent+action present, but order doesn't form a
    valid clause (two actions, no object, no coordination)."""
    shape = (TokenRole.AGENT, TokenRole.ACTION, TokenRole.DESCRIPTOR, TokenRole.ACTION)
    assert is_valid_clause_shape(shape) is False


def test_is_valid_clause_shape_requires_both_agent_and_action():
    assert is_valid_clause_shape((TokenRole.DESCRIPTOR,)) is False
    assert is_valid_clause_shape((TokenRole.CONTEXT,)) is False
    assert is_valid_clause_shape((TokenRole.AGENT,)) is False
    assert is_valid_clause_shape((TokenRole.ACTION, TokenRole.OBJECT)) is False


def test_best_for_pressure_never_selects_the_subjectless_top_scorer():
    """Mini-gate: the subjectless top-scorer verifiably never composes."""
    lineage, tmp = _lineage()
    bad = _promote(lineage, (
        TokenRole.DESCRIPTOR, TokenRole.ACTION, TokenRole.OBJECT,
        TokenRole.DESCRIPTOR, TokenRole.ACTION, TokenRole.OBJECT, TokenRole.CONNECTOR,
    ))
    good = _promote(lineage, (TokenRole.AGENT, TokenRole.ACTION, TokenRole.OBJECT))
    orientation = {ax: 1.0 for ax in ("X", "T", "N", "B", "A")}
    for _ in range(20):
        chosen = lineage.best_for_pressure(orientation, 1.0)
        assert chosen is not None
        assert chosen.pattern_id != bad.pattern_id
        assert is_valid_clause_shape(chosen.role_sequence)


def test_best_for_pressure_returns_none_when_no_eligible_skeletons():
    lineage, tmp = _lineage()
    _promote(lineage, (TokenRole.DESCRIPTOR, TokenRole.ACTION, TokenRole.OBJECT))
    orientation = {ax: 1.0 for ax in ("X", "T", "N", "B", "A")}
    assert lineage.best_for_pressure(orientation, 1.0) is None


def test_invalid_skeleton_keeps_promoted_flag_and_history_after_being_skipped():
    """Invalid skeletons remain in the pool with history intact -- gating
    only affects composition eligibility, never get_promoted()/counters."""
    lineage, tmp = _lineage()
    bad = _promote(lineage, (TokenRole.CONTEXT,))
    orientation = {ax: 1.0 for ax in ("X", "T", "N", "B", "A")}
    lineage.best_for_pressure(orientation, 1.0)
    still = lineage._motifs[bad.pattern_id]
    assert still.promoted is True
    assert still.success_count == 20
    assert still.fail_count == 2
    assert bad in lineage.get_promoted()


def test_skeleton_skip_is_logged():
    lineage, tmp = _lineage()
    bad = _promote(lineage, (TokenRole.CONTEXT,))
    orientation = {ax: 1.0 for ax in ("X", "T", "N", "B", "A")}
    lineage.best_for_pressure(orientation, 1.0)
    log_path = os.path.join(tmp, "skeleton_skip_log.jsonl")
    assert os.path.exists(log_path)
    with open(log_path) as f:
        lines = [json.loads(l) for l in f]
    skips = [l for l in lines if l.get("skeleton_id") == bad.pattern_id]
    assert len(skips) == 1  # logged once, not once per call
    assert skips[0]["reason"] == "not_in_valid_clause_shape_whitelist"


def test_skeleton_skip_logged_once_not_every_call():
    lineage, tmp = _lineage()
    bad = _promote(lineage, (TokenRole.CONTEXT,))
    orientation = {ax: 1.0 for ax in ("X", "T", "N", "B", "A")}
    for _ in range(10):
        lineage.best_for_pressure(orientation, 1.0)
    log_path = os.path.join(tmp, "skeleton_skip_log.jsonl")
    with open(log_path) as f:
        lines = [json.loads(l) for l in f]
    skips = [l for l in lines if l.get("skeleton_id") == bad.pattern_id]
    assert len(skips) == 1


def test_starvation_alert_logged_when_fewer_than_three_eligible():
    lineage, tmp = _lineage()
    _promote(lineage, (TokenRole.AGENT, TokenRole.ACTION))
    _promote(lineage, (TokenRole.CONTEXT,))
    orientation = {ax: 1.0 for ax in ("X", "T", "N", "B", "A")}
    lineage.best_for_pressure(orientation, 1.0)
    log_path = os.path.join(tmp, "skeleton_skip_log.jsonl")
    with open(log_path) as f:
        lines = [json.loads(l) for l in f]
    alerts = [l for l in lines if l.get("alert") == "composition_starvation"]
    assert len(alerts) == 1
    assert alerts[0]["eligible_count"] == 1
