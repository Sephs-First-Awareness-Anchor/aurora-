# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
PF3.4a (2026-07-21, ratified from PF3.4's characterization note).

PF3.4 re-characterized the current residue (post PF3.1-3.3) and found
the largest single sub-pattern (14/36 non-carryover records): a
multi-clause response mixing motif skeleton shapes across its OWN
clauses against the SAME PropositionFrame -- one clause gets a
content-bearing skeleton (agent_action_object or _descriptor), the
sibling clause collapses to the bare 2-role agent_action skeleton,
which has no object/descriptor role to fill in the first place
("I denied claims. I denied."). Not slot-fill starvation (directive's
hypothesis (c) -- no empty slot is left unfilled); the skeleton itself
has no slot. Root cause: best_for_proposition's own fitness-
proportional sampling (PF1.3, intentional for diversity ACROSS
responses) independently re-samples per sentence, so it can draw a
strictly thinner skeleton for a later sentence even though the frame
still has full subject/relation/obj content, demonstrated by an
earlier sentence in the same response already using it.

_motif_for_proposition_avoiding_thinning is the fix: a bounded retry
(not a hard requirement) that avoids drawing something strictly
thinner than the richest skeleton this response has already used, only
when the frame is fully populated (subject+relation+obj all present).
PF1.3's own diversity properties (fitness-proportional sampling,
skeleton variety across DIFFERENT responses) are untouched -- this
only constrains a downward move within one response's own clauses.
"""
import os
import tempfile

from aurora_expression_perception import LexicalMemory, VoiceGenome, SentenceComposer
from aurora_grammar_engine import MotifLineage, TokenRole
from aurora_internal.aurora_proposition_frame import PropositionFrame


def _lineage():
    tmp = tempfile.mkdtemp(prefix="aurora_pf3_4a_test_")
    return MotifLineage(os.path.join(tmp, "grammar_motifs.json"))


def _promote(lineage, role_sequence):
    m = lineage.get_or_create(role_sequence)
    m.success_count = 20
    m.fail_count = 2
    m.contexts_seen = {f"ctx{i}" for i in range(6)}
    m.promoted = True
    return m


def _composer():
    tmp = tempfile.mkdtemp(prefix="aurora_pf3_4a_lex_")
    return SentenceComposer(LexicalMemory(state_dir=tmp), VoiceGenome())


_ORIENT = {ax: 1.0 for ax in ("X", "T", "N", "B", "A")}
_FULL_FRAME = PropositionFrame(subject="i", relation="need", obj="water", source="thought")
_PARTIAL_FRAME = PropositionFrame(subject="self", relation="", obj="guitar", source="anchor")


def test_no_retry_when_richest_role_count_is_zero():
    """First sentence of a response (nothing to protect yet) or a
    frame that isn't fully populated -- every draw passes immediately,
    identical to calling best_for_proposition directly."""
    composer = _composer()
    lineage = _lineage()
    only = _promote(lineage, (TokenRole.AGENT, TokenRole.ACTION))
    chosen = composer._motif_for_proposition_avoiding_thinning(
        lineage, _FULL_FRAME, _ORIENT, 1.0, richest_role_count=0, max_retries=3)
    assert chosen.pattern_id == only.pattern_id


def test_retries_away_from_a_strictly_thinner_draw_when_a_richer_one_exists():
    composer = _composer()
    lineage = _lineage()
    thin = _promote(lineage, (TokenRole.AGENT, TokenRole.ACTION))
    rich = _promote(lineage, (TokenRole.AGENT, TokenRole.ACTION, TokenRole.OBJECT))
    # richest_role_count=3 (a prior sentence already used the 3-role
    # skeleton) -- a fresh draw landing on the 2-role "thin" skeleton
    # must retry toward something that meets or exceeds richness 3.
    results = set()
    for _ in range(30):
        chosen = composer._motif_for_proposition_avoiding_thinning(
            lineage, _FULL_FRAME, _ORIENT, 1.0, richest_role_count=3, max_retries=5)
        results.add(chosen.pattern_id)
    assert rich.pattern_id in results
    # The whole point: never settle for strictly-thinner when a richer
    # skeleton was reachable within the retry budget.
    assert thin.pattern_id not in results


def test_falls_back_to_thin_draw_when_no_richer_skeleton_exists():
    """Fail-quiet: if the lineage genuinely has nothing richer promoted,
    bounded retries must not spin forever or return None -- the best
    available draw still gets used."""
    composer = _composer()
    lineage = _lineage()
    only = _promote(lineage, (TokenRole.AGENT, TokenRole.ACTION))
    chosen = composer._motif_for_proposition_avoiding_thinning(
        lineage, _FULL_FRAME, _ORIENT, 1.0, richest_role_count=3, max_retries=5)
    assert chosen is not None
    assert chosen.pattern_id == only.pattern_id


def test_does_not_retry_when_draw_already_meets_richness():
    composer = _composer()
    lineage = _lineage()
    rich = _promote(lineage, (TokenRole.AGENT, TokenRole.ACTION, TokenRole.OBJECT, TokenRole.DESCRIPTOR))
    chosen = composer._motif_for_proposition_avoiding_thinning(
        lineage, _FULL_FRAME, _ORIENT, 1.0, richest_role_count=3, max_retries=5)
    assert chosen.pattern_id == rich.pattern_id


def test_degrades_gracefully_when_best_for_proposition_returns_none():
    composer = _composer()
    lineage = _lineage()  # nothing promoted at all
    chosen = composer._motif_for_proposition_avoiding_thinning(
        lineage, _FULL_FRAME, _ORIENT, 1.0, richest_role_count=3, max_retries=5)
    assert chosen is None
