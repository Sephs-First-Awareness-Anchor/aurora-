# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive PF1.3: motif selection conditioned on the proposition.

PF1.0's attribution run found motif diversity across 60 real probes was
exactly 1 -- every sentence used the same skeleton, because
best_for_pressure's plain max() always breaks the same way under
near-constant orientation. best_for_proposition adds a shape-fit term
(does this skeleton have room for the frame's subject/relation/obj?)
and fitness-proportional sampling over the top 4 candidates instead of
a hard max() -- the direct mechanical fix for that finding. Scoped to
this new method only: best_for_pressure (frame-absent turns) is
untouched.
"""
import os
import tempfile

from aurora_grammar_engine import MotifLineage, TokenRole, is_valid_clause_shape
from aurora_internal.aurora_proposition_frame import PropositionFrame


def _lineage():
    tmp = tempfile.mkdtemp(prefix="aurora_pf1_3_test_")
    return MotifLineage(os.path.join(tmp, "grammar_motifs.json"))


def _promote(lineage, role_sequence):
    m = lineage.get_or_create(role_sequence)
    m.success_count = 20
    m.fail_count = 2
    m.contexts_seen = {f"ctx{i}" for i in range(6)}
    m.promoted = True
    return m


_ORIENT = {ax: 1.0 for ax in ("X", "T", "N", "B", "A")}


def test_returns_none_when_no_eligible_skeletons():
    lineage = _lineage()
    frame = PropositionFrame(subject="I", relation="need", obj="water", source="thought")
    assert lineage.best_for_proposition(frame, _ORIENT, 1.0) is None


def test_only_candidate_is_always_returned():
    lineage = _lineage()
    only = _promote(lineage, (TokenRole.AGENT, TokenRole.ACTION, TokenRole.OBJECT))
    frame = PropositionFrame(subject="I", relation="need", obj="water", source="thought")
    for _ in range(10):
        chosen = lineage.best_for_proposition(frame, _ORIENT, 1.0)
        assert chosen.pattern_id == only.pattern_id


def test_never_selects_an_invalid_clause_shape():
    """Same L1 whitelist gate best_for_pressure enforces -- shape-fit
    scoring must not bypass it."""
    lineage = _lineage()
    _promote(lineage, (
        TokenRole.DESCRIPTOR, TokenRole.ACTION, TokenRole.OBJECT,
        TokenRole.DESCRIPTOR, TokenRole.ACTION, TokenRole.OBJECT, TokenRole.CONNECTOR,
    ))
    good = _promote(lineage, (TokenRole.AGENT, TokenRole.ACTION, TokenRole.OBJECT))
    frame = PropositionFrame(subject="I", relation="need", obj="water", source="thought")
    for _ in range(20):
        chosen = lineage.best_for_proposition(frame, _ORIENT, 1.0)
        assert chosen is not None
        assert is_valid_clause_shape(chosen.role_sequence)
        assert chosen.pattern_id == good.pattern_id


def test_shape_fit_favors_the_skeleton_with_room_for_the_full_triple():
    """A full subject+relation+obj frame (wants=3) should be routed to
    the AGENT-ACTION-OBJECT skeleton (capacity=3) far more often than
    the AGENT-ACTION-DESCRIPTOR one (capacity=2, no OBJECT slot at
    all) when the two are otherwise identically fit."""
    lineage = _lineage()
    has_object = _promote(lineage, (TokenRole.AGENT, TokenRole.ACTION, TokenRole.OBJECT))
    no_object = _promote(lineage, (TokenRole.AGENT, TokenRole.ACTION, TokenRole.DESCRIPTOR))
    frame = PropositionFrame(subject="I", relation="need", obj="water", source="thought")

    counts = {has_object.pattern_id: 0, no_object.pattern_id: 0}
    for _ in range(300):
        chosen = lineage.best_for_proposition(frame, _ORIENT, 1.0)
        counts[chosen.pattern_id] += 1

    assert counts[has_object.pattern_id] > counts[no_object.pattern_id]


def test_anchor_only_frame_does_not_crash_shape_fit_math():
    """source='anchor' frames have subject='self' + obj set but
    relation='' -- wants=2, still well-formed."""
    lineage = _lineage()
    _promote(lineage, (TokenRole.AGENT, TokenRole.ACTION, TokenRole.OBJECT))
    frame = PropositionFrame(subject="self", relation="", obj="guitar", source="anchor")
    chosen = lineage.best_for_proposition(frame, _ORIENT, 1.0)
    assert chosen is not None


def test_monotony_breaker_produces_more_than_one_distinct_motif():
    """The direct mechanical answer to PF1.0's diversity=1 finding:
    across enough calls with several similarly-fit promoted skeletons,
    more than one distinct motif must actually get chosen."""
    lineage = _lineage()
    shapes = [
        (TokenRole.AGENT, TokenRole.ACTION),
        (TokenRole.AGENT, TokenRole.ACTION, TokenRole.OBJECT),
        (TokenRole.AGENT, TokenRole.ACTION, TokenRole.DESCRIPTOR),
        (TokenRole.AGENT, TokenRole.ACTION, TokenRole.OBJECT, TokenRole.DESCRIPTOR),
        (TokenRole.AGENT, TokenRole.ACTION, TokenRole.DETERMINER, TokenRole.OBJECT),
    ]
    for shape in shapes:
        _promote(lineage, shape)
    frame = PropositionFrame(subject="I", relation="need", obj="water", source="thought")

    distinct = {
        lineage.best_for_proposition(frame, _ORIENT, 1.0).pattern_id
        for _ in range(200)
    }
    assert len(distinct) >= 2


def test_best_for_pressure_is_unaffected_by_this_directive():
    """Regression guard: best_for_pressure's own deterministic max()
    selection is untouched -- frame-absent turns must keep today's
    exact behavior."""
    lineage = _lineage()
    only = _promote(lineage, (TokenRole.AGENT, TokenRole.ACTION, TokenRole.OBJECT))
    for _ in range(10):
        chosen = lineage.best_for_pressure(_ORIENT, 1.0)
        assert chosen.pattern_id == only.pattern_id
